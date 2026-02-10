from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.database import get_db
from app.api.auth import get_current_user, get_current_admin, get_current_super_admin
from app.schemas.schemas import (
    ResponseData,
    ContainerCreate,
    ContainerInfo,
    ContainerStatus,
    ContainerDeleteRequest,
)
from app.services.crud_service import (
    user_service,
    container_service,
    config_service,
    log_service,
)
from app.services.ucloud_service import ucloud_service
from app.models.models import User, Admin, ContainerRecord

router = APIRouter(prefix="/container", tags=["容器管理"])


@router.get("/my", response_model=ResponseData)
async def get_my_container(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """获取我的云电脑"""
    container = await container_service.get_by_user_id(db, current_user.id)

    if not container:
        return ResponseData(code=200, message="success", data={"has_container": False})

    return ResponseData(
        code=200,
        message="success",
        data={
            "has_container": True,
            "container": {
                "id": container.id,
                "instance_name": container.instance_name,
                "status": container.status,
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
                "total_running_minutes": container.total_running_minutes,
                "total_cost": container.total_cost,
            },
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
    stats = await container_service.calculate_session_stats(container)

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
    container_data: ContainerCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建云电脑"""
    # 检查是否已有容器
    existing = await container_service.get_by_user_id(db, current_user.id)
    if existing:
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

    # 检查余额
    min_balance = await config_service.get_min_balance_to_start(db)
    if current_user.balance < min_balance:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"余额不足，创建云电脑至少需要{min_balance}元",
        )

    # 获取当前价格
    price_per_minute = await config_service.get_price_per_minute(db)

    # 调用UCloud创建实例 - 使用固定默认参数，仅实例名称可自定义
    result = await ucloud_service.create_container(
        instance_name=container_data.instance_name,
    )

    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建失败: {result.get('error', '未知错误')}",
        )

    # 创建容器记录 - 使用固定默认参数
    container = await container_service.create(
        db,
        current_user.id,
        {
            "instance_id": result["instance_id"],
            "instance_name": container_data.instance_name,
            "gpu_type": "3080Ti",
            "cpu_cores": 12,
            "memory_gb": 32,
            "storage_gb": 200,
            "ip": result["ip"],
            "password": result["password"],
        },
        price_per_minute,
    )

    # 更新用户当前容器ID
    current_user.current_container_id = container.id
    await db.commit()

    # 记录日志
    await log_service.create_container_log(
        db,
        current_user.id,
        container.id,
        "create",
        "success",
        ip_address=request.client.host,
    )

    return ResponseData(
        code=200,
        message="云电脑创建成功",
        data={
            "container_id": container.id,
            "status": container.status,
            "estimated_time": 120,
        },
    )


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
        current_user.id,
        container.id,
        "start",
        "success",
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
    stats = await container_service.calculate_session_stats(container)

    # 更新容器累计数据
    await container_service.add_running_time(
        db, container, stats["running_minutes"], stats["cost"]
    )

    # 更新容器状态
    await container_service.update_status(db, container, "stopped")

    # 记录日志
    await log_service.create_container_log(
        db,
        current_user.id,
        container.id,
        "stop",
        "success",
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
    container = await container_service.get_by_user_id(db, current_user.id)

    if not container:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="云电脑不存在"
        )

    if not delete_request.confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="请确认删除"
        )

    # 如果正在运行，先停止
    if container.status == "running":
        # 计算本次会话统计
        stats = await container_service.calculate_session_stats(container)

        # 更新累计数据
        await container_service.add_running_time(
            db, container, stats["running_minutes"], stats["cost"]
        )

        # 停止UCloud实例
        await ucloud_service.stop_container(container.ucloud_instance_id)

    # 删除UCloud实例
    result = await ucloud_service.delete_container(container.ucloud_instance_id)

    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除失败: {result.get('error', '未知错误')}",
        )

    # 软删除容器记录
    await container_service.delete(db, container)

    # 清空用户当前容器ID
    current_user.current_container_id = None
    await db.commit()

    # 记录日志
    await log_service.create_container_log(
        db,
        current_user.id,
        container.id,
        "delete",
        "success",
        request_data=f"{{reason: {delete_request.reason}}}",
        ip_address=request.client.host,
    )

    return ResponseData(
        code=200,
        message="删除成功，您可以创建新的云电脑",
        data={"deleted_at": datetime.utcnow().isoformat()},
    )
