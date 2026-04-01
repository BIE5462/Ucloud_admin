from datetime import datetime
from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.api.auth import get_current_user
from app.schemas.schemas import (
    ResponseData,
    ContainerCreate,
    ContainerDeleteRequest,
)
from app.services.crud_service import (
    user_service,
    container_service,
    config_service,
    log_service,
)
from app.services.ucloud_service import ucloud_service
from app.models.models import User

router = APIRouter(prefix="/container", tags=["容器管理"])


def _extract_container_validation_message(exc: ValidationError) -> str:
    """提取创建容器请求的首个校验错误信息"""
    first_error = exc.errors()[0] if exc.errors() else {}
    field_name = ""
    for item in first_error.get("loc", []):
        if item != "body":
            field_name = str(item)
            break

    if field_name == "config_code":
        return "套餐编码无效，仅支持 config_1 ~ config_5"
    if field_name == "instance_name":
        return "实例名称不能为空"

    return first_error.get("msg", "请求参数错误")


def _serialize_container(container) -> dict:
    """序列化容器信息"""
    return {
        "id": container.id,
        "instance_name": container.instance_name,
        "status": container.status,
        "config_code": container.config_code,
        "config_name": container.config_name,
        "gpu_type": container.gpu_type,
        "cpu_cores": container.cpu_cores,
        "memory_gb": container.memory_gb,
        "storage_gb": container.storage_gb,
        "price_per_minute": container.price_per_minute,
        "created_at": container.created_at.isoformat()
        if container.created_at
        else None,
        "started_at": container.started_at.isoformat()
        if container.started_at
        else None,
        "stopped_at": container.stopped_at.isoformat()
        if container.stopped_at
        else None,
        "total_running_minutes": container.total_running_minutes,
        "total_cost": container.total_cost,
    }


def _serialize_pending_operation(current_user: User):
    """序列化用户当前容器操作状态"""
    if not current_user.container_operation_status:
        return None

    message_map = {
        "creating": "云电脑正在创建中，请稍候刷新",
        "deleting": "云电脑正在删除中，关闭客户端不会中断处理",
    }
    return {
        "status": current_user.container_operation_status,
        "started_at": current_user.container_operation_started_at.isoformat()
        if current_user.container_operation_started_at
        else None,
        "message": message_map.get(
            current_user.container_operation_status, "容器任务处理中"
        ),
    }


@router.get("/config-options", response_model=ResponseData)
async def get_container_config_options(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """获取用户可选套餐列表"""
    configs = await config_service.get_all_configs(db)
    return ResponseData(
        code=200,
        message="success",
        data={
            "min_balance_to_start": configs["min_balance_to_start"],
            "config_options": configs["config_options"],
        },
    )


@router.get("/my", response_model=ResponseData)
async def get_my_container(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """获取我的云电脑"""
    await db.refresh(current_user)
    await user_service.clear_stale_container_operation(db, current_user)
    container = await container_service.get_by_user_id(db, current_user.id)

    if not container:
        return ResponseData(
            code=200,
            message="success",
            data={
                "has_container": False,
                "pending_operation": _serialize_pending_operation(current_user),
            },
        )

    return ResponseData(
        code=200,
        message="success",
        data={
            "has_container": True,
            "container": _serialize_container(container),
            "pending_operation": _serialize_pending_operation(current_user),
        },
    )


@router.get("/my/status", response_model=ResponseData)
async def get_container_status(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """获取云电脑实时状态"""
    container = await container_service.get_by_user_id(db, current_user.id)

    if not container:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="云电脑不存在"
        )

    # 计算本次运行统计
    stats = await container_service.calculate_session_stats(db, container)

    # 计算剩余时间
    remaining_minutes = (
        int(current_user.balance / container.price_per_minute)
        if container.price_per_minute > 0
        else 0
    )
    hours = remaining_minutes // 60
    minutes = remaining_minutes % 60
    remaining_formatted = f"{hours}小时{minutes}分钟" if hours > 0 else f"{minutes}分钟"

    data = {
        "status": container.status,
        "current_running_minutes": stats["running_minutes"],
        "current_session_cost": stats["cost"],
        "balance": current_user.balance,
        "price_per_minute": container.price_per_minute,
        "remaining_minutes": remaining_minutes,
        "remaining_time_formatted": remaining_formatted,
    }

    if container.status == "running":
        data["connection_info"] = {
            "host": container.connection_host,
            "port": container.connection_port,
            "username": container.connection_username,
            "password": container.connection_password,
        }

    return ResponseData(code=200, message="success", data=data)


@router.post("", response_model=ResponseData)
async def create_container(
    request: Request,
    container_payload: dict = Body(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建云电脑"""
    try:
        container_data = ContainerCreate.model_validate(container_payload)
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_extract_container_validation_message(exc),
        ) from exc

    await db.refresh(current_user)
    await user_service.clear_stale_container_operation(db, current_user)

    if current_user.container_operation_status == "creating":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "已有云电脑创建任务正在处理中，请稍候刷新结果",
                "operation_in_progress": True,
                "pending_operation": _serialize_pending_operation(current_user),
            },
        )

    # 检查是否已有容器
    existing = await container_service.get_by_user_id(db, current_user.id)
    if existing:
        if existing.status == "deleting":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="旧云电脑正在删除中，请等待删除完成后再创建",
            )
        if not container_data.force:
            # 返回特定错误码，提示需要确认删除
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "message": "您已有一个云电脑实例，是否删除旧实例并创建新实例？",
                    "existing_container": {
                        "id": existing.id,
                        "instance_name": existing.instance_name,
                        "status": existing.status,
                        "gpu_type": existing.gpu_type,
                    },
                    "require_confirm": True,
                },
            )

        # 强制创建：先删除旧实例和数据库记录
        try:
            # 1. 调用 UCloud API 删除实例
            delete_result = await ucloud_service.delete_container(
                existing.ucloud_instance_id
            )
            if not delete_result["success"]:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"删除旧实例失败: {delete_result.get('error', '未知错误')}",
                )

            # 2. 物理删除数据库记录
            await container_service.hard_delete_by_user(db, current_user.id)

            # 3. 清除用户的当前容器ID
            current_user.current_container_id = None
            await db.commit()

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"删除旧实例时出错: {str(e)}",
            )

    lock_acquired = await user_service.acquire_container_operation(
        db, current_user.id, "creating"
    )
    if not lock_acquired:
        await db.refresh(current_user)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "已有云电脑创建任务正在处理中，请稍候刷新结果",
                "operation_in_progress": True,
                "pending_operation": _serialize_pending_operation(current_user),
            },
        )

    try:
        # 检查余额
        min_balance = await config_service.get_min_balance_to_start(db)
        if current_user.balance < min_balance:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"余额不足，创建云电脑至少需要{min_balance}元",
            )

        # 获取当前套餐与共享创建配置
        try:
            container_create_config = await config_service.get_container_create_config(
                db,
                container_data.config_code,
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            ) from exc

        # 调用UCloud创建实例 - 规格参数来自固定套餐，共享镜像来自后台配置
        result = await ucloud_service.create_container(
            instance_name=container_data.instance_name,
            create_config=container_create_config,
        )

        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"创建失败: {result.get('error', '未知错误')}",
            )

        # 创建容器记录 - 保存本次实际生效的系统配置快照
        container = await container_service.create(
            db,
            current_user.id,
            {
                "instance_id": result["instance_id"],
                "instance_name": container_data.instance_name,
                "config_code": container_create_config["config_code"],
                "config_name": container_create_config["config_name"],
                "gpu_type": container_create_config["gpu_type"],
                "cpu_cores": container_create_config["cpu_cores"],
                "memory_gb": container_create_config["memory_gb"],
                "storage_gb": container_create_config["storage_gb"],
                "price_per_minute": container_create_config["price_per_minute"],
                "ip": result["ip"],
                "password": result["password"],
            },
        )

        current_user.current_container_id = container.id
        current_user.container_operation_status = None
        current_user.container_operation_started_at = None
        await db.commit()

        await log_service.create_container_log(
            db,
            user_id=current_user.id,
            admin_id=current_user.admin_id,
            container_id=container.id,
            action="create",
            action_status="success",
            started_at=container.started_at,
            ip_address=request.client.host,
        )

        return ResponseData(
            code=200,
            message="云电脑创建成功，已自动启动",
            data={
                "container_id": container.id,
                "status": container.status,
                "config_code": container.config_code,
                "config_name": container.config_name,
                "started_at": container.started_at.isoformat()
                if container.started_at
                else None,
                "connection_info": {
                    "host": container.connection_host,
                    "port": container.connection_port,
                    "username": container.connection_username,
                    "password": container.connection_password,
                },
                "estimated_time": 120,
            },
        )
    finally:
        await db.rollback()
        refreshed_user = await user_service.get_by_id(db, current_user.id)
        if refreshed_user and refreshed_user.container_operation_status == "creating":
            await user_service.clear_container_operation(db, refreshed_user, "creating")


@router.post("/start", response_model=ResponseData)
async def start_container(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """启动云电脑"""
    container = await container_service.get_by_user_id(db, current_user.id)

    if not container:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="云电脑不存在"
        )

    if container.status == "running":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="云电脑已在运行中"
        )
    if container.status == "deleting":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="云电脑正在删除中，无法启动"
        )
    if container.status not in {"stopped"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"当前状态为 {container.status}，暂不支持启动",
        )

    # 检查余额
    min_balance = await config_service.get_min_balance_to_start(db)
    if current_user.balance < min_balance:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"余额不足，启动云电脑至少需要{min_balance}元",
            headers={"X-Error-Code": "INSUFFICIENT_BALANCE"},
        )

    # 调用UCloud启动实例
    result = await ucloud_service.start_container(container.ucloud_instance_id)

    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"启动失败: {result.get('error', '未知错误')}",
        )

    # 更新连接信息
    container.connection_host = result["ip"]
    container.connection_password = result["password"]

    # 更新容器状态
    await container_service.update_status(db, container, "running")

    # 记录日志
    await log_service.create_container_log(
        db,
        user_id=current_user.id,
        admin_id=current_user.admin_id,
        container_id=container.id,
        action="start",
        action_status="success",
        started_at=container.started_at,
        ip_address=request.client.host,
    )

    return ResponseData(
        code=200,
        message="启动成功",
        data={
            "container_id": container.id,
            "status": "running",
            "started_at": container.started_at.isoformat()
            if container.started_at
            else None,
            "connection_info": {
                "host": container.connection_host,
                "port": container.connection_port,
                "username": container.connection_username,
                "password": container.connection_password,
            },
        },
    )


@router.post("/stop", response_model=ResponseData)
async def stop_container(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """停止云电脑"""
    container = await container_service.get_by_user_id(db, current_user.id)

    if not container:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="云电脑不存在"
        )

    if container.status != "running":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="云电脑未在运行中"
        )

    # 调用UCloud停止实例
    result = await ucloud_service.stop_container(container.ucloud_instance_id)

    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"停止失败: {result.get('error', '未知错误')}",
        )

    # 计算本次会话统计
    stats = await container_service.calculate_session_stats(db, container)

    # 更新容器累计数据
    await container_service.add_running_time(
        db, container, stats["running_minutes"], stats["cost"]
    )

    # 更新容器状态
    await container_service.update_status(db, container, "stopped")

    # 记录日志
    await log_service.create_container_log(
        db,
        user_id=current_user.id,
        admin_id=current_user.admin_id,
        container_id=container.id,
        action="stop",
        action_status="success",
        started_at=container.started_at,
        stopped_at=container.stopped_at,
        duration_minutes=stats["running_minutes"],
        cost=stats["cost"],
        ip_address=request.client.host,
    )

    return ResponseData(
        code=200,
        message="停止成功",
        data={
            "container_id": container.id,
            "status": "stopped",
            "stopped_at": container.stopped_at.isoformat()
            if container.stopped_at
            else None,
            "this_session": stats,
            "total": {
                "running_minutes": container.total_running_minutes,
                "cost": container.total_cost,
            },
        },
    )


@router.delete("", response_model=ResponseData)
async def delete_container(
    delete_request: ContainerDeleteRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除云电脑"""
    await db.refresh(current_user)
    await user_service.clear_stale_container_operation(db, current_user)
    container = await container_service.get_by_user_id(db, current_user.id)

    if not container:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="云电脑不存在"
        )

    if not delete_request.confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="请确认删除"
        )

    if container.status == "deleting":
        return ResponseData(
            code=200,
            message="删除任务已在后台处理中",
            data={
                "status": "deleting",
                "message": "云电脑正在删除中，关闭客户端不会中断处理",
            },
        )

    if current_user.container_operation_status == "creating":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="云电脑正在创建中，暂时无法删除，请稍后重试",
        )

    # 如果正在运行，先停止
    if container.status == "running":
        # 计算本次会话统计
        stats = await container_service.calculate_session_stats(db, container)

        # 更新累计数据
        await container_service.add_running_time(
            db, container, stats["running_minutes"], stats["cost"]
        )

        # 停止UCloud实例
        stop_result = await ucloud_service.stop_container(container.ucloud_instance_id)
        if not stop_result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"停止失败: {stop_result.get('error', '未知错误')}",
            )

        container.stopped_at = datetime.utcnow()

    current_user.container_operation_status = "deleting"
    current_user.container_operation_started_at = datetime.utcnow()
    container.status = "deleting"
    container.connection_host = None
    container.connection_password = None
    await db.commit()

    # 先尝试立即删除，失败则交由后台补偿任务继续处理
    result = await ucloud_service.delete_container(container.ucloud_instance_id)

    if not result["success"]:
        await log_service.create_container_log(
            db,
            user_id=current_user.id,
            admin_id=current_user.admin_id,
            container_id=container.id,
            action="delete",
            action_status="success",
            request_data=f"{{reason: {delete_request.reason}}}",
            response_data="后台继续处理删除任务",
            ip_address=request.client.host,
        )
        return ResponseData(
            code=200,
            message="删除任务已提交，云端仍在处理中",
            data={
                "status": "deleting",
                "message": "删除任务已交由服务端继续处理，关闭客户端不会中断",
            },
        )

    # 软删除容器记录
    await container_service.delete(db, container)

    # 清空用户当前容器ID
    current_user.current_container_id = None
    await db.commit()
    await user_service.clear_container_operation(db, current_user, "deleting")

    # 记录日志
    await log_service.create_container_log(
        db,
        user_id=current_user.id,
        admin_id=current_user.admin_id,
        container_id=container.id,
        action="delete",
        action_status="success",
        request_data=f"{{reason: {delete_request.reason}}}",
        ip_address=request.client.host,
    )

    return ResponseData(
        code=200,
        message="删除成功，您可以创建新的云电脑",
        data={"deleted_at": datetime.utcnow().isoformat()},
    )
