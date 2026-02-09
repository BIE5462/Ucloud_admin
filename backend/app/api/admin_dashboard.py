from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from app.db.database import get_db
from app.api.auth import get_current_admin
from app.schemas.schemas import ResponseData, DashboardData
from app.services.crud_service import user_service, container_service, config_service
from app.models.models import User, ContainerRecord, BillingChargeRecord

router = APIRouter(prefix="/admin/dashboard", tags=["仪表盘"])


@router.get("", response_model=ResponseData)
async def get_dashboard(
    current_admin=Depends(get_current_admin), db: AsyncSession = Depends(get_db)
):
    """获取仪表盘数据"""

    # 1. 概览数据
    # 用户总数
    user_count_query = select(func.count()).select_from(User)
    total_users = await db.scalar(user_count_query) or 0

    # 容器统计
    container_stats = await container_service.count_by_status(db)
    total_containers = sum(container_stats.values())
    running_containers = container_stats.get("running", 0)
    stopped_containers = container_stats.get("stopped", 0)

    # 总余额
    balance_query = select(func.sum(User.balance))
    total_balance = await db.scalar(balance_query) or 0

    # 今日收入
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_income_query = select(func.sum(BillingChargeRecord.amount)).where(
        BillingChargeRecord.charge_minute >= today
    )
    today_income = await db.scalar(today_income_query) or 0

    # 2. 今日统计
    # 今日新用户
    today_new_users_query = (
        select(func.count()).select_from(User).where(User.created_at >= today)
    )
    today_new_users = await db.scalar(today_new_users_query) or 0

    # 今日新容器
    today_new_containers_query = (
        select(func.count())
        .select_from(ContainerRecord)
        .where(ContainerRecord.created_at >= today)
    )
    today_new_containers = await db.scalar(today_new_containers_query) or 0

    # 今日运行分钟数
    today_minutes_query = select(func.count()).where(
        BillingChargeRecord.charge_minute >= today
    )
    today_running_minutes = await db.scalar(today_minutes_query) or 0

    # 3. 本月统计
    this_month = today.replace(day=1)
    this_month_new_users_query = (
        select(func.count()).select_from(User).where(User.created_at >= this_month)
    )
    this_month_new_users = await db.scalar(this_month_new_users_query) or 0

    this_month_income_query = select(func.sum(BillingChargeRecord.amount)).where(
        BillingChargeRecord.charge_minute >= this_month
    )
    this_month_income = await db.scalar(this_month_income_query) or 0

    # 4. 图表数据
    # 近7天收入趋势
    income_trend = []
    for i in range(6, -1, -1):
        date = today - timedelta(days=i)
        next_date = date + timedelta(days=1)

        day_income_query = select(func.sum(BillingChargeRecord.amount)).where(
            and_(
                BillingChargeRecord.charge_minute >= date,
                BillingChargeRecord.charge_minute < next_date,
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
