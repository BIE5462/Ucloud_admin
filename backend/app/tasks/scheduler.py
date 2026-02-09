from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.database import AsyncSessionLocal
from app.services.crud_service import container_service, user_service, config_service
from app.services.ucloud_service import ucloud_service
from app.models.models import (
    ContainerRecord,
    User,
    BillingChargeRecord,
    BalanceLog,
    ContainerLog,
)

scheduler = AsyncIOScheduler()


async def charge_running_containers():
    """每分钟扣费任务"""
    async with AsyncSessionLocal() as db:
        try:
            # 获取所有运行中的容器
            running_containers = await container_service.list_running_containers(db)

            for container in running_containers:
                # 获取用户信息
                user = await user_service.get_by_id(db, container.user_id)
                if not user:
                    continue

                # 检查余额是否足够
                if user.balance < container.price_per_minute:
                    # 余额不足，停止实例
                    result = await ucloud_service.stop_container(
                        container.ucloud_instance_id
                    )

                    if result["success"]:
                        # 更新容器状态
                        stats = await container_service.calculate_session_stats(
                            container
                        )
                        await container_service.add_running_time(
                            db, container, stats["running_minutes"], stats["cost"]
                        )
                        await container_service.update_status(db, container, "stopped")

                        # 记录日志
                        log = ContainerLog(
                            user_id=user.id,
                            container_id=container.id,
                            action="auto_stop",
                            action_status="success",
                            error_message="余额不足自动停止",
                        )
                        db.add(log)
                        await db.commit()

                    continue

                # 扣费
                old_balance = user.balance
                new_balance = old_balance - container.price_per_minute
                user.balance = new_balance

                # 创建扣费记录
                charge_record = BillingChargeRecord(
                    user_id=user.id,
                    container_id=container.id,
                    charge_minute=datetime.utcnow().replace(second=0, microsecond=0),
                    price_per_minute=container.price_per_minute,
                    amount=container.price_per_minute,
                    balance_before=old_balance,
                    balance_after=new_balance,
                )
                db.add(charge_record)

                # 创建余额变动记录
                balance_log = BalanceLog(
                    user_id=user.id,
                    change_type="deduct",
                    amount=-container.price_per_minute,
                    balance_before=old_balance,
                    balance_after=new_balance,
                    description="云电脑使用扣费",
                    operator_type="system",
                )
                db.add(balance_log)

                # 更新容器累计数据
                container.total_running_minutes += 1
                container.total_cost += container.price_per_minute

                await db.commit()

        except Exception as e:
            print(f"扣费任务执行失败: {e}")
            await db.rollback()


def start_scheduler():
    """启动定时任务"""
    # 每分钟执行一次扣费任务
    scheduler.add_job(
        charge_running_containers,
        trigger=IntervalTrigger(minutes=1),
        id="charge_task",
        name="每分钟扣费任务",
        replace_existing=True,
    )
    scheduler.start()
    print("定时任务已启动")


def shutdown_scheduler():
    """关闭定时任务"""
    scheduler.shutdown()
    print("定时任务已关闭")
