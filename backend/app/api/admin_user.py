from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from typing import Optional

from app.db.database import get_db
from app.api.auth import get_current_admin, get_current_super_admin
from app.schemas.schemas import (
    ResponseData,
    UserCreate,
    UserUpdate,
    UserResetPassword,
)
from app.services.crud_service import (
    user_service,
    container_service,
    log_service,
)
from app.core.security import get_password_hash
from app.models.models import BillingChargeRecord

router = APIRouter(prefix="/admin/users", tags=["用户管理"])


@router.get("", response_model=ResponseData)
async def list_users(
    page: int = 1,
    page_size: int = 20,
    keyword: Optional[str] = None,
    status: Optional[int] = None,
    admin_id: Optional[int] = None,
    current_admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """获取用户列表

    普通管理员：只能看到自己创建的用户
    超级管理员：可以看到所有用户，并可按管理员筛选
    """
    skip = (page - 1) * page_size

    # 构建查询条件
    is_super = current_admin.role == "super_admin"

    if not is_super:
        # 普通管理员只能看自己创建的用户
        filters = {"created_by": current_admin.id}
    else:
        # 超级管理员可以按管理员筛选
        filters = {}
        if admin_id:
            filters["created_by"] = admin_id

    if status is not None:
        filters["status"] = status

    total, users = await user_service.list_users_with_filters(
        db, skip, page_size, keyword, filters
    )

    # 获取容器状态信息
    items = []
    for user in users:
        container = await container_service.get_by_user_id(db, user.id)

        # 获取归属管理员信息（仅超级管理员显示）
        belongs_to_admin = None
        if is_super and user.admin:
            belongs_to_admin = user.admin.username

        items.append(
            {
                "id": user.id,
                "company_name": user.company_name,
                "contact_name": user.contact_name,
                "phone": user.phone,
                "balance": user.balance,
                "status": user.status,
                "has_container": container is not None,
                "container_status": container.status if container else None,
                "created_at": user.created_at.strftime("%Y-%m-%d %H:%M")
                if user.created_at
                else None,
                "last_login_at": user.last_login_at.strftime("%Y-%m-%d %H:%M")
                if user.last_login_at
                else None,
                "belongs_to_admin": belongs_to_admin,  # 仅超级管理员可见
            }
        )

    return ResponseData(
        code=200,
        message="success",
        data={"total": total, "page": page, "page_size": page_size, "items": items},
    )


@router.post("", response_model=ResponseData)
async def create_user(
    user_data: UserCreate,
    current_admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """创建用户

    普通管理员创建用户：
    1. 检查用户数量上限
    2. 检查代理余额（如有初始充值）
    3. 从代理余额扣除初始金额
    4. 用户归属该管理员
    """
    # 检查手机号是否已存在
    existing = await user_service.get_by_phone(db, user_data.phone)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="手机号已存在"
        )

    # 1. 检查用户数量上限（仅普通管理员）
    if current_admin.role != "super_admin":
        user_count = await user_service.get_count_by_creator(db, current_admin.id)
        if user_count >= current_admin.max_users:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"已达到可开通用户数量上限({current_admin.max_users}个)",
            )

    # 2. 检查并扣除代理余额（如有初始充值且不是超级管理员）
    initial_balance = user_data.initial_balance or 0
    if initial_balance > 0 and current_admin.role != "super_admin":
        if current_admin.balance < initial_balance:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"代理余额不足，当前余额: ¥{current_admin.balance:.2f}",
            )
        # 扣除代理余额
        current_admin.balance -= initial_balance

    # 3. 创建用户
    user = await user_service.create(
        db,
        {
            "company_name": user_data.company_name,
            "contact_name": user_data.contact_name,
            "phone": user_data.phone,
            "password": user_data.password,
            "initial_balance": initial_balance,
            "admin_id": current_admin.id,  # 用户归属该管理员
            "created_by": current_admin.id,  # 记录创建者
        },
    )

    # 记录日志
    await log_service.create_admin_operation_log(
        db,
        current_admin.id,
        "create_user",
        "user",
        user.id,
        new_value=f"{{phone: {user.phone}, company: {user.company_name}, balance: {initial_balance}}}",
        description=f"创建用户: {user.company_name}, 初始余额: ¥{initial_balance:.2f}",
    )

    return ResponseData(
        code=200,
        message="创建成功",
        data={"id": user.id, "phone": user.phone, "balance": user.balance},
    )


@router.get("/{user_id}", response_model=ResponseData)
async def get_user_detail(
    user_id: int,
    current_admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """获取用户详情"""
    user = await user_service.get_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    container = await container_service.get_by_user_id(db, user_id)

    # 统计信息
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_query = select(func.sum(BillingChargeRecord.amount)).where(
        and_(
            BillingChargeRecord.user_id == user_id,
            BillingChargeRecord.charge_minute >= today,
        )
    )
    today_cost = await db.scalar(today_query) or 0

    this_month = today.replace(day=1)
    month_query = select(func.sum(BillingChargeRecord.amount)).where(
        and_(
            BillingChargeRecord.user_id == user_id,
            BillingChargeRecord.charge_minute >= this_month,
        )
    )
    this_month_cost = await db.scalar(month_query) or 0

    return ResponseData(
        code=200,
        message="success",
        data={
            "user": {
                "id": user.id,
                "company_name": user.company_name,
                "contact_name": user.contact_name,
                "phone": user.phone,
                "balance": user.balance,
                "status": user.status,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "updated_at": user.updated_at.isoformat() if user.updated_at else None,
                "last_login_at": user.last_login_at.isoformat()
                if user.last_login_at
                else None,
            },
            "container": {
                "id": container.id,
                "status": container.status,
                "total_cost": container.total_cost,
                "total_running_minutes": container.total_running_minutes,
            }
            if container
            else None,
            "statistics": {
                "today_cost": today_cost,
                "this_month_cost": this_month_cost,
                "total_cost": container.total_cost if container else 0,
            },
        },
    )


@router.put("/{user_id}", response_model=ResponseData)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    current_admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """更新用户信息"""
    user = await user_service.get_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    old_value = f"{{company_name: {user.company_name}, contact_name: {user.contact_name}, status: {user.status}}}"

    user = await user_service.update(
        db,
        user,
        {
            "company_name": user_update.company_name,
            "contact_name": user_update.contact_name,
            "status": user_update.status,
        },
    )

    new_value = f"{{company_name: {user.company_name}, contact_name: {user.contact_name}, status: {user.status}}}"

    # 记录日志
    await log_service.create_admin_operation_log(
        db,
        current_admin.id,
        "update_user",
        "user",
        user_id,
        old_value=old_value,
        new_value=new_value,
        description=f"更新用户信息",
    )

    return ResponseData(code=200, message="更新成功")


@router.post("/{user_id}/reset-password", response_model=ResponseData)
async def reset_user_password(
    user_id: int,
    reset_data: UserResetPassword,
    current_admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """重置用户密码"""
    user = await user_service.get_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    user.password_hash = get_password_hash(reset_data.new_password)
    await db.commit()

    # 记录日志
    await log_service.create_admin_operation_log(
        db,
        current_admin.id,
        "reset_password",
        "user",
        user_id,
        description="重置用户密码",
    )

    return ResponseData(code=200, message="密码重置成功")


class BalanceChangeRequest:
    def __init__(self, type: str, amount: float, description: Optional[str] = None):
        self.type = type
        self.amount = amount
        self.description = description


@router.post("/{user_id}/balance", response_model=ResponseData)
async def change_user_balance(
    user_id: int,
    type: str,
    amount: float,
    description: Optional[str] = None,
    current_admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """充值/扣减用户余额"""
    user = await user_service.get_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    if type not in ["recharge", "deduct"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="无效的操作类型"
        )

    if type == "deduct":
        change_amount = -abs(amount)
        if user.balance < abs(change_amount):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="扣减金额不能超过用户余额",
            )
    else:
        change_amount = abs(amount)

    balance_before = user.balance

    # 更新余额
    await user_service.update_balance(
        db,
        user,
        change_amount,
        change_type=type,
        description=description
        or ("管理员充值" if type == "recharge" else "管理员扣减"),
        operator_id=current_admin.id,
        operator_type="admin",
    )

    # 记录日志
    await log_service.create_admin_operation_log(
        db,
        current_admin.id,
        f"{type}_balance",
        "user",
        user_id,
        old_value=f"{{balance: {balance_before}}}",
        new_value=f"{{balance: {user.balance}}}",
        description=f"{'充值' if type == 'recharge' else '扣减'} {abs(change_amount)} 元",
    )

    return ResponseData(
        code=200,
        message="操作成功",
        data={
            "user_id": user_id,
            "balance_before": balance_before,
            "balance_after": user.balance,
            "change_amount": change_amount,
        },
    )


@router.delete("/{user_id}", response_model=ResponseData)
async def delete_user(
    user_id: int,
    current_admin=Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """删除用户"""
    user = await user_service.get_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    # 检查用户是否有云电脑
    container = await container_service.get_by_user_id(db, user_id)
    if container:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该用户存在云电脑，请先删除云电脑后再删除用户",
        )

    # 记录日志
    await log_service.create_admin_operation_log(
        db,
        current_admin.id,
        "delete_user",
        "user",
        user_id,
        old_value=f"{{phone: {user.phone}, company: {user.company_name}}}",
        description=f"删除用户: {user.company_name}",
    )

    await user_service.delete(db, user)

    return ResponseData(code=200, message="删除成功")
