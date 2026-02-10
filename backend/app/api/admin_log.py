from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional

from app.db.database import get_db
from app.api.auth import get_current_admin
from app.schemas.schemas import ResponseData
from app.models.models import ContainerLog, User, Admin

router = APIRouter(prefix="/admin/logs", tags=["日志管理"])


@router.get("/container", response_model=ResponseData)
async def get_container_logs(
    page: int = 1,
    page_size: int = 20,
    user_id: Optional[int] = None,
    admin_id: Optional[int] = None,
    action: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """获取容器操作日志列表"""
    # 构建基础查询，关联用户表和管理员表
    query = (
        select(ContainerLog, User.company_name, Admin.username)
        .join(User, ContainerLog.user_id == User.id)
        .join(Admin, ContainerLog.admin_id == Admin.id)
    )

    # 超级管理员可以看到所有日志，普通管理员只能看到自己用户的日志
    if current_admin.role != "super_admin":
        query = query.where(ContainerLog.admin_id == current_admin.id)
    elif admin_id:
        # 超级管理员可以按归属管理员筛选
        query = query.where(ContainerLog.admin_id == admin_id)

    # 用户筛选
    if user_id:
        query = query.where(ContainerLog.user_id == user_id)

    # 操作类型筛选
    if action:
        query = query.where(ContainerLog.action == action)

    # 日期筛选
    if start_date:
        start_dt = datetime.fromisoformat(start_date)
        query = query.where(ContainerLog.created_at >= start_dt)

    if end_date:
        end_dt = datetime.fromisoformat(end_date)
        query = query.where(ContainerLog.created_at <= end_dt)

    # 获取总数
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    # 获取分页数据
    query = query.order_by(ContainerLog.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    rows = result.all()

    # 组装返回数据
    items = []
    for log, user_name, admin_name in rows:
        items.append(
            {
                "id": log.id,
                "user_name": user_name,
                "admin_name": admin_name,
                "action": log.action,
                "action_status": log.action_status,
                "started_at": log.started_at.isoformat() if log.started_at else None,
                "stopped_at": log.stopped_at.isoformat() if log.stopped_at else None,
                "duration_minutes": log.duration_minutes,
                "cost": log.cost,
                "ip_address": log.ip_address,
                "error_message": log.error_message,
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
