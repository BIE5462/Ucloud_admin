from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from typing import Optional

from app.db.database import get_db
from app.api.auth import get_current_user, get_current_admin
from app.schemas.schemas import ResponseData, BalanceLogInfo, BillingChargeInfo
from app.services.crud_service import container_service
from app.models.models import BillingChargeRecord, BalanceLog

router = APIRouter(prefix="/billing", tags=["账单管理"])


@router.get("/charges", response_model=ResponseData)
async def get_charge_records(
    page: int = 1,
    page_size: int = 20,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取扣费记录"""
    query = select(BillingChargeRecord).where(
        BillingChargeRecord.user_id == current_user.id
    )

    # 日期筛选
    if start_date:
        start_dt = datetime.fromisoformat(start_date)
        query = query.where(BillingChargeRecord.charge_minute >= start_dt)

    if end_date:
        end_dt = datetime.fromisoformat(end_date)
        query = query.where(BillingChargeRecord.charge_minute <= end_dt)

    # 获取总数
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    # 获取分页数据
    query = query.order_by(BillingChargeRecord.charge_minute.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    records = result.scalars().all()

    # 统计总金额
    sum_query = select(func.sum(BillingChargeRecord.amount)).where(
        BillingChargeRecord.user_id == current_user.id
    )
    total_amount = await db.scalar(sum_query) or 0

    sum_minutes_query = select(func.count()).where(
        BillingChargeRecord.user_id == current_user.id
    )
    total_minutes = await db.scalar(sum_minutes_query) or 0

    return ResponseData(
        code=200,
        message="success",
        data={
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": [
                {
                    "id": r.id,
                    "charge_minute": r.charge_minute.isoformat()
                    if r.charge_minute
                    else None,
                    "price_per_minute": r.price_per_minute,
                    "amount": r.amount,
                    "balance_before": r.balance_before,
                    "balance_after": r.balance_after,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in records
            ],
            "summary": {"total_amount": total_amount, "total_minutes": total_minutes},
        },
    )


@router.get("/balance-logs", response_model=ResponseData)
async def get_balance_logs(
    page: int = 1,
    page_size: int = 20,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取余额变动记录"""
    query = select(BalanceLog).where(BalanceLog.user_id == current_user.id)

    # 获取总数
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    # 获取分页数据
    query = query.order_by(BalanceLog.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    logs = result.scalars().all()

    # 获取操作人信息
    items = []
    for log in logs:
        operator_name = None
        if log.operator_id:
            from app.services.crud_service import admin_service

            admin = await admin_service.get_by_id(db, log.operator_id)
            operator_name = admin.username if admin else None

        items.append(
            {
                "id": log.id,
                "change_type": log.change_type,
                "amount": log.amount,
                "balance_before": log.balance_before,
                "balance_after": log.balance_after,
                "description": log.description,
                "operator_name": operator_name,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
        )

    return ResponseData(
        code=200,
        message="success",
        data={"total": total, "page": page, "page_size": page_size, "items": items},
    )


@router.get("/statistics", response_model=ResponseData)
async def get_statistics(
    current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """获取消费统计"""
    container = await container_service.get_by_user_id(db, current_user.id)

    # 今日消费
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_query = select(func.sum(BillingChargeRecord.amount)).where(
        and_(
            BillingChargeRecord.user_id == current_user.id,
            BillingChargeRecord.charge_minute >= today,
        )
    )
    today_cost = await db.scalar(today_query) or 0

    # 本月消费
    this_month = today.replace(day=1)
    month_query = select(func.sum(BillingChargeRecord.amount)).where(
        and_(
            BillingChargeRecord.user_id == current_user.id,
            BillingChargeRecord.charge_minute >= this_month,
        )
    )
    this_month_cost = await db.scalar(month_query) or 0

    # 累计消费
    total_query = select(func.sum(BillingChargeRecord.amount)).where(
        BillingChargeRecord.user_id == current_user.id
    )
    total_cost = await db.scalar(total_query) or 0

    # 累计运行分钟数
    total_minutes_query = select(func.count()).where(
        BillingChargeRecord.user_id == current_user.id
    )
    total_running_minutes = await db.scalar(total_minutes_query) or 0

    return ResponseData(
        code=200,
        message="success",
        data={
            "balance": current_user.balance,
            "total_cost": total_cost,
            "total_running_minutes": total_running_minutes,
            "today_cost": today_cost,
            "this_month_cost": this_month_cost,
            "container_total_cost": container.total_cost if container else 0,
            "container_total_minutes": container.total_running_minutes
            if container
            else 0,
        },
    )
