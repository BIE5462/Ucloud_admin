from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.api.auth import get_current_super_admin
from app.schemas.schemas import (
    ResponseData,
    AdminCreate,
    AdminUpdate,
    UserResetPassword,
    AdminRecharge,
)
from app.services.crud_service import admin_service, log_service
from app.core.security import get_password_hash

router = APIRouter(prefix="/admin/admins", tags=["管理员管理"])


@router.get("", response_model=ResponseData)
async def list_admins(
    page: int = 1,
    page_size: int = 20,
    current_admin=Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """获取管理员列表（仅超级管理员）"""
    from app.services.crud_service import user_service

    skip = (page - 1) * page_size
    total, admins = await admin_service.list_admins(db, skip, page_size)

    items = []
    for admin in admins:
        creator_name = None
        if admin.created_by:
            creator = await admin_service.get_by_id(db, admin.created_by)
            creator_name = creator.username if creator else None

        # 获取该管理员已开通的用户数量
        user_count = await user_service.get_count_by_creator(db, admin.id)

        items.append(
            {
                "id": admin.id,
                "username": admin.username,
                "role": admin.role,
                "status": admin.status,
                "balance": admin.balance,
                "max_users": admin.max_users,
                "user_count": user_count,
                "company_name": admin.company_name,
                "contact_name": admin.contact_name,
                "phone": admin.phone,
                "created_at": admin.created_at.strftime("%Y-%m-%d %H:%M")
                if admin.created_at
                else None,
                "last_login_at": admin.last_login_at.strftime("%Y-%m-%d %H:%M")
                if admin.last_login_at
                else None,
                "created_by": creator_name,
            }
        )

    return ResponseData(
        code=200,
        message="success",
        data={"total": total, "page": page, "page_size": page_size, "items": items},
    )


@router.post("", response_model=ResponseData)
async def create_admin(
    admin_data: AdminCreate,
    current_admin=Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """创建管理员（仅超级管理员）"""
    # 检查用户名是否已存在
    existing = await admin_service.get_by_username(db, admin_data.username)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="用户名已存在"
        )

    admin = await admin_service.create(
        db,
        {
            "username": admin_data.username,
            "password": admin_data.password,
            "role": admin_data.role,
            "company_name": admin_data.company_name,
            "contact_name": admin_data.contact_name,
            "phone": admin_data.phone,
            "balance": admin_data.initial_balance or 0.0,
            "max_users": admin_data.max_users or 10,
        },
        created_by=current_admin.id,
    )

    # 记录日志
    await log_service.create_admin_operation_log(
        db,
        current_admin.id,
        "create_admin",
        "admin",
        admin.id,
        new_value=f"{{username: {admin.username}, role: {admin.role}, company: {admin.company_name}}}",
        description=f"创建管理员: {admin.username}",
    )

    return ResponseData(
        code=200, message="创建成功", data={"id": admin.id, "username": admin.username}
    )


@router.put("/{admin_id}", response_model=ResponseData)
async def update_admin(
    admin_id: int,
    admin_update: AdminUpdate,
    current_admin=Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """更新管理员（仅超级管理员）"""
    # 不能修改自己
    if admin_id == current_admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="不能修改自己的信息"
        )

    admin = await admin_service.get_by_id(db, admin_id)
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="管理员不存在"
        )

    old_value = f"{{status: {admin.status}, role: {admin.role}, max_users: {admin.max_users}, balance: {admin.balance}}}"

    if admin_update.status is not None:
        admin.status = admin_update.status
    if admin_update.role is not None:
        admin.role = admin_update.role
    if admin_update.max_users is not None:
        admin.max_users = admin_update.max_users
    if admin_update.company_name is not None:
        admin.company_name = admin_update.company_name
    if admin_update.contact_name is not None:
        admin.contact_name = admin_update.contact_name
    if admin_update.phone is not None:
        admin.phone = admin_update.phone

    await db.commit()

    new_value = f"{{status: {admin.status}, role: {admin.role}, max_users: {admin.max_users}, balance: {admin.balance}}}"

    # 记录日志
    await log_service.create_admin_operation_log(
        db,
        current_admin.id,
        "update_admin",
        "admin",
        admin_id,
        old_value=old_value,
        new_value=new_value,
        description=f"更新管理员信息",
    )

    return ResponseData(code=200, message="更新成功")


@router.delete("/{admin_id}", response_model=ResponseData)
async def delete_admin(
    admin_id: int,
    current_admin=Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """删除管理员（仅超级管理员）"""
    # 不能删除自己
    if admin_id == current_admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="不能删除自己"
        )

    admin = await admin_service.get_by_id(db, admin_id)
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="管理员不存在"
        )

    # 软删除（禁用）
    admin.status = 0
    await db.commit()

    # 记录日志
    await log_service.create_admin_operation_log(
        db,
        current_admin.id,
        "delete_admin",
        "admin",
        admin_id,
        description=f"删除管理员: {admin.username}",
    )

    return ResponseData(code=200, message="删除成功")


@router.post("/{admin_id}/reset-password", response_model=ResponseData)
async def reset_admin_password(
    admin_id: int,
    reset_data: UserResetPassword,
    current_admin=Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """重置管理员密码（仅超级管理员）"""
    admin = await admin_service.get_by_id(db, admin_id)
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="管理员不存在"
        )

    admin.password_hash = get_password_hash(reset_data.new_password)
    await db.commit()

    # 记录日志
    await log_service.create_admin_operation_log(
        db,
        current_admin.id,
        "reset_admin_password",
        "admin",
        admin_id,
        description="重置管理员密码",
    )

    return ResponseData(code=200, message="密码重置成功")


@router.post("/{admin_id}/balance", response_model=ResponseData)
async def recharge_admin_balance(
    admin_id: int,
    recharge_data: AdminRecharge,
    current_admin=Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """超级管理员给代理充值/扣减余额"""
    if admin_id == current_admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="不能给自己充值"
        )

    target_admin = await admin_service.get_by_id(db, admin_id)
    if not target_admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="管理员不存在"
        )

    if recharge_data.type not in ["recharge", "deduct"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="无效的操作类型"
        )

    balance_before = target_admin.balance

    if recharge_data.type == "recharge":
        amount = abs(recharge_data.amount)
        target_admin.balance += amount
    else:
        amount = -abs(recharge_data.amount)
        if target_admin.balance < abs(amount):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"扣减金额不能超过代理余额，当前余额: ¥{target_admin.balance:.2f}",
            )
        target_admin.balance += amount

    await db.commit()

    # 记录日志
    await log_service.create_admin_operation_log(
        db,
        current_admin.id,
        f"{recharge_data.type}_admin_balance",
        "admin",
        admin_id,
        old_value=f"{{balance: {balance_before}}}",
        new_value=f"{{balance: {target_admin.balance}}}",
        description=f"{'充值' if recharge_data.type == 'recharge' else '扣减'} ¥{abs(amount):.2f}",
    )

    return ResponseData(
        code=200,
        message="操作成功",
        data={
            "admin_id": admin_id,
            "balance_before": balance_before,
            "balance_after": target_admin.balance,
            "change_amount": amount,
        },
    )
