from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, or_
from typing import Optional, List

from app.db.database import AsyncSessionLocal
from app.models.models import (
    User,
    Admin,
    ContainerRecord,
    SystemConfig,
    ContainerLog,
    AdminOperationLog,
)
from app.core.security import get_password_hash
from app.core.config import get_settings

settings = get_settings()


class UserService:
    """用户服务"""

    @staticmethod
    async def get_by_phone(db: AsyncSession, phone: str) -> Optional[User]:
        """根据手机号获取用户"""
        result = await db.execute(select(User).where(User.phone == phone))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
        """根据ID获取用户"""
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def create(db: AsyncSession, user_data: dict) -> User:
        """创建用户"""
        user = User(
            company_name=user_data["company_name"],
            contact_name=user_data["contact_name"],
            phone=user_data["phone"],
            password_hash=get_password_hash(user_data["password"]),
            balance=user_data.get("initial_balance", 0.0),
            admin_id=user_data.get("admin_id"),
            created_by=user_data.get("created_by"),
            status=1,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    @staticmethod
    async def update(db: AsyncSession, user: User, update_data: dict) -> User:
        """更新用户"""
        for key, value in update_data.items():
            if value is not None:
                setattr(user, key, value)
        await db.commit()
        await db.refresh(user)
        return user

    @staticmethod
    async def update_balance(
        db: AsyncSession,
        user: User,
        amount: float,
        change_type: str,
        description: str = None,
        operator_id: int = None,
        operator_type: str = "system",
    ):
        """更新用户余额（不提交事务，由调用方控制）"""
        new_balance = user.balance + amount
        user.balance = new_balance

    @staticmethod
    async def list_users(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 20,
        keyword: str = None,
        status: int = None,
    ) -> tuple:
        """获取用户列表"""
        query = select(User)

        if keyword:
            query = query.where(
                or_(User.company_name.contains(keyword), User.phone.contains(keyword))
            )

        if status is not None:
            query = query.where(User.status == status)

        # 获取总数
        count_query = select(func.count()).select_from(query.subquery())
        total = await db.scalar(count_query)

        # 获取分页数据
        query = query.offset(skip).limit(limit).order_by(User.created_at.desc())
        result = await db.execute(query)
        users = result.scalars().all()

        return total, users

    @staticmethod
    async def delete(db: AsyncSession, user: User) -> None:
        """删除用户"""
        await db.delete(user)
        await db.commit()

    @staticmethod
    async def list_users_with_filters(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 20,
        keyword: str = None,
        filters: dict = None,
    ) -> tuple:
        """获取用户列表（带过滤条件）"""
        from sqlalchemy.orm import joinedload

        query = select(User).options(joinedload(User.admin))

        if keyword:
            query = query.where(
                or_(User.company_name.contains(keyword), User.phone.contains(keyword))
            )

        # 应用额外过滤条件
        if filters:
            if "created_by" in filters:
                query = query.where(User.created_by == filters["created_by"])
            if "status" in filters:
                query = query.where(User.status == filters["status"])

        # 获取总数
        count_query = select(func.count()).select_from(query.subquery())
        total = await db.scalar(count_query)

        # 获取分页数据
        query = query.offset(skip).limit(limit).order_by(User.created_at.desc())
        result = await db.execute(query)
        users = result.scalars().all()

        return total, users

    @staticmethod
    async def get_count_by_creator(db: AsyncSession, admin_id: int) -> int:
        """获取某管理员创建的用户数量"""
        query = select(func.count()).where(User.created_by == admin_id)
        result = await db.execute(query)
        return result.scalar() or 0


class AdminService:
    """管理员服务"""

    @staticmethod
    async def get_by_username(db: AsyncSession, username: str) -> Optional[Admin]:
        """根据用户名获取管理员"""
        result = await db.execute(select(Admin).where(Admin.username == username))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_id(db: AsyncSession, admin_id: int) -> Optional[Admin]:
        """根据ID获取管理员"""
        result = await db.execute(select(Admin).where(Admin.id == admin_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def create(
        db: AsyncSession, admin_data: dict, created_by: int = None
    ) -> Admin:
        """创建管理员"""
        admin = Admin(
            username=admin_data["username"],
            password_hash=get_password_hash(admin_data["password"]),
            role=admin_data.get("role", "admin"),
            status=1,
            created_by=created_by,
            company_name=admin_data.get("company_name"),
            contact_name=admin_data.get("contact_name"),
            phone=admin_data.get("phone"),
            balance=admin_data.get("balance", 0.0),
            max_users=admin_data.get("max_users", 10),
        )
        db.add(admin)
        await db.commit()
        await db.refresh(admin)
        return admin

    @staticmethod
    async def list_admins(db: AsyncSession, skip: int = 0, limit: int = 20) -> tuple:
        """获取管理员列表"""
        query = select(Admin).order_by(Admin.created_at.desc())

        # 获取总数
        count_query = select(func.count()).select_from(query.subquery())
        total = await db.scalar(count_query)

        # 获取分页数据
        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        admins = result.scalars().all()

        return total, admins


class ContainerService:
    """容器服务"""

    @staticmethod
    async def get_by_user_id(
        db: AsyncSession, user_id: int
    ) -> Optional[ContainerRecord]:
        """根据用户ID获取容器"""
        result = await db.execute(
            select(ContainerRecord).where(
                and_(
                    ContainerRecord.user_id == user_id,
                    ContainerRecord.deleted_at.is_(None),
                )
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_id(
        db: AsyncSession, container_id: int
    ) -> Optional[ContainerRecord]:
        """根据ID获取容器"""
        result = await db.execute(
            select(ContainerRecord).where(ContainerRecord.id == container_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create(
        db: AsyncSession, user_id: int, container_data: dict, price_per_minute: float
    ) -> ContainerRecord:
        """创建容器记录"""
        container = ContainerRecord(
            user_id=user_id,
            ucloud_instance_id=container_data["instance_id"],
            instance_name=container_data["instance_name"],
            status="stopped",
            gpu_type=container_data["gpu_type"],
            cpu_cores=container_data["cpu_cores"],
            memory_gb=container_data["memory_gb"],
            storage_gb=container_data["storage_gb"],
            price_per_minute=price_per_minute,
            connection_host=container_data["ip"],
            connection_port=3389,
            connection_username="user",
            connection_password=container_data["password"],
        )
        db.add(container)
        await db.commit()
        await db.refresh(container)
        return container

    @staticmethod
    async def update_status(
        db: AsyncSession, container: ContainerRecord, status: str
    ) -> ContainerRecord:
        """更新容器状态"""
        container.status = status

        if status == "running":
            container.started_at = datetime.utcnow()
        elif status == "stopped":
            container.stopped_at = datetime.utcnow()

        await db.commit()
        await db.refresh(container)
        return container

    @staticmethod
    async def calculate_session_stats(container: ContainerRecord) -> dict:
        """计算本次会话统计"""
        if not container.started_at:
            return {"running_minutes": 0, "cost": 0.0}

        end_time = container.stopped_at or datetime.utcnow()
        running_seconds = (end_time - container.started_at).total_seconds()
        running_minutes = int(running_seconds / 60)
        running_minutes = max(0, running_minutes)
        cost = running_minutes * container.price_per_minute

        return {"running_minutes": running_minutes, "cost": round(cost, 2)}

    @staticmethod
    async def add_running_time(
        db: AsyncSession, container: ContainerRecord, minutes: int, cost: float
    ):
        """添加运行时间和费用"""
        container.total_running_minutes += max(0, minutes)
        container.total_cost += max(0.0, cost)
        await db.commit()

    @staticmethod
    async def delete(db: AsyncSession, container: ContainerRecord):
        """删除容器（软删除）"""
        container.deleted_at = datetime.utcnow()
        container.status = "deleted"
        await db.commit()

    @staticmethod
    async def hard_delete_by_user(
        db: AsyncSession, user_id: int
    ) -> Optional[ContainerRecord]:
        """物理删除用户的所有容器记录"""
        result = await db.execute(
            select(ContainerRecord).where(ContainerRecord.user_id == user_id)
        )
        containers = result.scalars().all()
        deleted_container = None
        for container in containers:
            deleted_container = container
            await db.delete(container)
        if containers:
            await db.commit()
        return deleted_container

    @staticmethod
    async def list_running_containers(db: AsyncSession) -> List[ContainerRecord]:
        """获取所有运行中的容器"""
        result = await db.execute(
            select(ContainerRecord).where(ContainerRecord.status == "running")
        )
        return result.scalars().all()

    @staticmethod
    async def count_by_status(db: AsyncSession) -> dict:
        """统计各状态容器数量"""
        result = await db.execute(
            select(ContainerRecord.status, func.count())
            .where(ContainerRecord.deleted_at.is_(None))
            .group_by(ContainerRecord.status)
        )
        counts = {}
        for status, count in result.all():
            counts[status] = count
        return counts


class ConfigService:
    """配置服务"""

    @staticmethod
    async def get_config(db: AsyncSession, key: str) -> Optional[SystemConfig]:
        """获取配置项"""
        result = await db.execute(
            select(SystemConfig).where(SystemConfig.config_key == key)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def set_config(
        db: AsyncSession,
        key: str,
        value: str,
        description: str = None,
        updated_by: int = None,
    ):
        """设置配置项"""
        config = await ConfigService.get_config(db, key)

        if config:
            config.config_value = value
            if description:
                config.description = description
            config.updated_by = updated_by
        else:
            config = SystemConfig(
                config_key=key,
                config_value=value,
                description=description,
                updated_by=updated_by,
            )
            db.add(config)

        await db.commit()

    @staticmethod
    async def get_price_per_minute(db: AsyncSession) -> float:
        """获取每分钟价格"""
        config = await ConfigService.get_config(db, "price_per_minute")
        if config:
            return float(config.config_value)
        return settings.DEFAULT_PRICE_PER_MINUTE

    @staticmethod
    async def get_min_balance_to_start(db: AsyncSession) -> float:
        """获取启动所需最低余额"""
        config = await ConfigService.get_config(db, "min_balance_to_start")
        if config:
            return float(config.config_value)
        return settings.DEFAULT_MIN_BALANCE_TO_START

    @staticmethod
    async def get_all_configs(db: AsyncSession) -> dict:
        """获取所有配置"""
        result = await db.execute(select(SystemConfig))
        configs = result.scalars().all()

        config_dict = {}
        for config in configs:
            config_dict[config.config_key] = config.config_value

        # 设置默认值
        if "price_per_minute" not in config_dict:
            config_dict["price_per_minute"] = settings.DEFAULT_PRICE_PER_MINUTE
        if "min_balance_to_start" not in config_dict:
            config_dict["min_balance_to_start"] = settings.DEFAULT_MIN_BALANCE_TO_START
        if "auto_stop_threshold" not in config_dict:
            config_dict["auto_stop_threshold"] = "0.0"

        return config_dict


class LogService:
    """日志服务"""

    @staticmethod
    async def create_container_log(
        db: AsyncSession,
        user_id: int,
        admin_id: int,
        container_id: int,
        action: str,
        action_status: str = "success",
        started_at: datetime = None,
        stopped_at: datetime = None,
        duration_minutes: int = None,
        cost: float = None,
        request_data: str = None,
        response_data: str = None,
        error_message: str = None,
        ip_address: str = None,
    ):
        """创建容器操作日志"""
        log = ContainerLog(
            user_id=user_id,
            admin_id=admin_id,
            container_id=container_id,
            action=action,
            action_status=action_status,
            started_at=started_at,
            stopped_at=stopped_at,
            duration_minutes=duration_minutes,
            cost=cost,
            request_data=request_data,
            response_data=response_data,
            error_message=error_message,
            ip_address=ip_address,
        )
        db.add(log)
        await db.commit()

    @staticmethod
    async def create_admin_operation_log(
        db: AsyncSession,
        admin_id: int,
        action: str,
        target_type: str,
        target_id: int = None,
        old_value: str = None,
        new_value: str = None,
        description: str = None,
        ip_address: str = None,
    ):
        """创建管理员操作日志"""
        log = AdminOperationLog(
            admin_id=admin_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            old_value=old_value,
            new_value=new_value,
            description=description,
            ip_address=ip_address,
        )
        db.add(log)
        await db.commit()


# 导出服务
user_service = UserService()
admin_service = AdminService()
container_service = ContainerService()
config_service = ConfigService()
log_service = LogService()
