from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from typing import Optional

from app.db.database import get_db
from app.api.auth import get_current_admin
from app.schemas.schemas import ResponseData
from app.models.models import BalanceLog, User, Admin

router = APIRouter(prefix="/admin/balance-logs", tags=["余额日志管理"])


@router.get("", response_model=ResponseData)
async def get_balance_logs(
    page: int = 1,
    page_size: int = 20,
    account_type: Optional[str] = None,
    change_type: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """获取余额变动日志列表"""
    # 获取所有超级管理员的ID
    super_admin_result = await db.execute(
        select(Admin.id).where(Admin.role == "super_admin")
    )
    super_admin_ids = [row[0] for row in super_admin_result.all()]

    # 构建基础查询，排除超级管理员的扣费日志
    query = select(BalanceLog).where(
        or_(
            BalanceLog.account_type != "admin",
            (BalanceLog.account_type == "admin")
            & (BalanceLog.account_id.notin_(super_admin_ids)),
        )
    )

    # 超级管理员可以看到所有账户的日志，普通管理员只能看到自己用户和管理员的日志
    if current_admin.role != "super_admin":
        # 获取该管理员创建的所有用户ID列表
        user_result = await db.execute(
            select(User.id).where(User.created_by == current_admin.id)
        )
        created_user_ids = [row[0] for row in user_result.all()]

        # 普通管理员只能看到：
        # 1. 自己的余额变动
        # 2. 自己创建的用户的余额变动
        query = query.where(
            or_(
                (BalanceLog.account_type == "admin")
                & (BalanceLog.account_id == current_admin.id),
                (BalanceLog.account_type == "user")
                & (BalanceLog.account_id.in_(created_user_ids)),
            )
        )

    # 账户类型筛选
    if account_type:
        query = query.where(BalanceLog.account_type == account_type)

    # 变动类型筛选
    if change_type:
        query = query.where(BalanceLog.change_type == change_type)

    # 日期筛选
    if start_date:
        start_dt = datetime.fromisoformat(start_date)
        query = query.where(BalanceLog.created_at >= start_dt)

    if end_date:
        end_dt = datetime.fromisoformat(end_date)
        query = query.where(BalanceLog.created_at <= end_dt)

    # 获取总数
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    # 获取分页数据
    query = query.order_by(BalanceLog.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    logs = result.scalars().all()

    # 批量获取关联的用户和管理员信息
    admin_ids = [log.account_id for log in logs if log.account_type == "admin"]
    user_ids = [log.account_id for log in logs if log.account_type == "user"]
    operator_ids = [log.operator_id for log in logs if log.operator_id]

    admins_map = {}
    if admin_ids + operator_ids:
        admin_result = await db.execute(
            select(Admin.id, Admin.username).where(
                or_(Admin.id.in_(admin_ids), Admin.id.in_(operator_ids))
            )
        )
        for admin_id, username in admin_result.all():
            admins_map[admin_id] = username

    users_map = {}
    if user_ids:
        user_result = await db.execute(
            select(User.id, User.company_name).where(User.id.in_(user_ids))
        )
        for user_id, company_name in user_result.all():
            users_map[user_id] = company_name

    # 组装返回数据
    items = []
    for log in logs:
        if log.account_type == "admin":
            account_name = admins_map.get(log.account_id, f"管理员{log.account_id}")
        else:
            account_name = users_map.get(log.account_id, f"用户{log.account_id}")

        operator_name = admins_map.get(log.operator_id, None)

        items.append(
            {
                "id": log.id,
                "account_type": log.account_type,
                "account_id": log.account_id,
                "account_name": account_name,
                "change_type": log.change_type,
                "amount": log.amount,
                "balance_before": log.balance_before,
                "balance_after": log.balance_after,
                "source": log.source,
                "related_id": log.related_id,
                "remark": log.remark,
                "operator_name": operator_name,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
        )

    return ResponseData(
        code=200,
        message="success",
        data={
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": items,
        },
    )
