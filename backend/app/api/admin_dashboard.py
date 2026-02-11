from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from app.db.database import get_db
from app.api.auth import get_current_admin
from app.schemas.schemas import ResponseData
from app.models.models import User, ContainerRecord, BillingChargeRecord

router = APIRouter(prefix="/admin/dashboard", tags=["仪表盘"])


@router.get("", response_model=ResponseData)
async def get_dashboard(
    current_admin=Depends(get_current_admin), db: AsyncSession = Depends(get_db)
):
    """获取仪表盘数据（仅当前管理员）"""

    admin_id = current_admin.id

    # 1. 概览数据
    # 用户总数（仅当前管理员创建的用户）
    user_count_query = (
        select(func.count()).select_from(User).where(User.created_by == admin_id)
    )
    total_users = await db.scalar(user_count_query) or 0

    # 容器统计（仅当前管理员用户的容器）
    container_stats_query = (
        select(ContainerRecord.status, func.count())
        .join(User, ContainerRecord.user_id == User.id)
        .where(and_(User.created_by == admin_id, ContainerRecord.deleted_at.is_(None)))
        .group_by(ContainerRecord.status)
    )
    container_stats_result = await db.execute(container_stats_query)
    container_stats = {}
    for status, count in container_stats_result.all():
        container_stats[status] = count

    total_containers = sum(container_stats.values())
    running_containers = container_stats.get("running", 0)
    stopped_containers = container_stats.get("stopped", 0)

    # 总余额（当前管理员的余额）
    total_balance = current_admin.balance or 0

    # 剩余可开通用户数
    max_users = current_admin.max_users or 10
    remaining_users = max(0, max_users - total_users)

    # 今日收入（仅当前管理员用户的消费）
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_income_query = (
        select(func.sum(BillingChargeRecord.amount))
        .join(User, BillingChargeRecord.user_id == User.id)
        .where(
            and_(
                User.created_by == admin_id, BillingChargeRecord.charge_minute >= today
            )
        )
    )
    today_income = await db.scalar(today_income_query) or 0

    # 2. 今日统计
    # 今日新用户（仅当前管理员创建的）
    today_new_users_query = (
        select(func.count())
        .select_from(User)
        .where(and_(User.created_by == admin_id, User.created_at >= today))
    )
    today_new_users = await db.scalar(today_new_users_query) or 0

    # 今日新容器（仅当前管理员用户的容器）
    today_new_containers_query = (
        select(func.count())
        .select_from(ContainerRecord)
        .join(User, ContainerRecord.user_id == User.id)
        .where(and_(User.created_by == admin_id, ContainerRecord.created_at >= today))
    )
    today_new_containers = await db.scalar(today_new_containers_query) or 0

    # 今日运行分钟数（仅当前管理员用户的消费记录）
    today_minutes_query = (
        select(func.count())
        .select_from(BillingChargeRecord)
        .join(User, BillingChargeRecord.user_id == User.id)
        .where(
            and_(
                User.created_by == admin_id, BillingChargeRecord.charge_minute >= today
            )
        )
    )
    today_running_minutes = await db.scalar(today_minutes_query) or 0

    # 3. 本月统计
    this_month = today.replace(day=1)
    this_month_new_users_query = (
        select(func.count())
        .select_from(User)
        .where(and_(User.created_by == admin_id, User.created_at >= this_month))
    )
    this_month_new_users = await db.scalar(this_month_new_users_query) or 0

    this_month_income_query = (
        select(func.sum(BillingChargeRecord.amount))
        .join(User, BillingChargeRecord.user_id == User.id)
        .where(
            and_(
                User.created_by == admin_id,
                BillingChargeRecord.charge_minute >= this_month,
            )
        )
    )
    this_month_income = await db.scalar(this_month_income_query) or 0

    # 4. 图表数据
    # 近7天收入趋势（仅当前管理员用户的消费）
    income_trend = []
    for i in range(6, -1, -1):
        date = today - timedelta(days=i)
        next_date = date + timedelta(days=1)

        day_income_query = (
            select(func.sum(BillingChargeRecord.amount))
            .join(User, BillingChargeRecord.user_id == User.id)
            .where(
                and_(
                    User.created_by == admin_id,
                    BillingChargeRecord.charge_minute >= date,
                    BillingChargeRecord.charge_minute < next_date,
                )
            )
        )
        day_income = await db.scalar(day_income_query) or 0

        income_trend.append(
            {"date": date.strftime("%Y-%m-%d"), "amount": round(day_income, 2)}
        )

    return ResponseData(
        code=200,
        message="success",
        data={
            "overview": {
                "total_users": total_users,
                "total_containers": total_containers,
                "running_containers": running_containers,
                "stopped_containers": stopped_containers,
                "total_balance": round(total_balance, 2),
                "today_income": round(today_income, 2),
                "remaining_users": remaining_users,
            },
            "statistics": {
                "today_new_users": today_new_users,
                "today_new_containers": today_new_containers,
                "today_running_minutes": today_running_minutes,
                "today_income": round(today_income, 2),
                "this_month_new_users": this_month_new_users,
                "this_month_income": round(this_month_income, 2),
            },
            "charts": {
                "income_trend": income_trend,
                "container_status": {
                    "running": running_containers,
                    "stopped": stopped_containers,
                },
            },
        },
    )
