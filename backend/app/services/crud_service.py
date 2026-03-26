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
    UserLoginLog,
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
            status="running",
            started_at=datetime.utcnow(),
            stopped_at=None,
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
            container.stopped_at = None
        elif status == "stopped":
            container.stopped_at = datetime.utcnow()

        await db.commit()
        await db.refresh(container)
        return container

    @staticmethod
    async def calculate_session_stats(db: AsyncSession, container: ContainerRecord) -> dict:
        """计算本次会话统计（需要传入db以确保数据最新）"""
        # 刷新容器数据以确保 started_at 是最新的
        await db.refresh(container)

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

    CONFIG_DESCRIPTIONS = {
        "price_per_minute": "云电脑每分钟价格（元）",
        "min_balance_to_start": "启动云电脑所需的最低余额（元）",
        "comp_share_image_id": "创建云电脑实例使用的镜像ID",
        "gpu_type": "创建云电脑实例使用的GPU类型",
        "cpu_cores": "创建云电脑实例使用的CPU核数",
        "memory_gb": "创建云电脑实例使用的内存大小（GB）",
        "auto_stop_threshold": "自动关机余额阈值（元）",
    }
    CONTAINER_CREATE_CONFIG_KEYS = (
        "comp_share_image_id",
        "gpu_type",
        "cpu_cores",
        "memory_gb",
    )

    @staticmethod
    async def get_config(db: AsyncSession, key: str) -> Optional[SystemConfig]:
        """获取配置项"""
        result = await db.execute(
            select(SystemConfig).where(SystemConfig.config_key == key)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def _upsert_config(
        db: AsyncSession,
        key: str,
        value: str,
        description: str = None,
        updated_by: int = None,
    ) -> None:
        """新增或更新配置项（不提交事务）"""
        config = await ConfigService.get_config(db, key)

        if config:
            config.config_value = value
            if description:
                config.description = description
            config.updated_by = updated_by
            return

        db.add(
            SystemConfig(
                config_key=key,
                config_value=value,
                description=description,
                updated_by=updated_by,
            )
        )

    @staticmethod
    async def set_config(
        db: AsyncSession,
        key: str,
        value: str,
        description: str = None,
        updated_by: int = None,
    ):
        """设置配置项"""
        await ConfigService._upsert_config(
            db,
            key,
            str(value),
            description=description or ConfigService.CONFIG_DESCRIPTIONS.get(key),
            updated_by=updated_by,
        )
        await db.commit()

    @staticmethod
    async def set_configs(
        db: AsyncSession,
        config_data: dict,
        updated_by: int = None,
    ) -> None:
        """批量设置配置项"""
        for key, value in config_data.items():
            await ConfigService._upsert_config(
                db,
                key,
                str(value),
                description=ConfigService.CONFIG_DESCRIPTIONS.get(key),
                updated_by=updated_by,
            )
        await db.commit()

    @staticmethod
    def _parse_float_value(value, default: float) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _parse_int_value(value, default: int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _parse_text_value(value, default: str) -> str:
        if value is None:
            return default

        text = str(value).strip()
        return text or default

    @staticmethod
    def normalize_configs(config_dict: dict) -> dict:
        """合并默认值并转换为可直接使用的配置"""
        return {
            "price_per_minute": ConfigService._parse_float_value(
                config_dict.get("price_per_minute"),
                settings.DEFAULT_PRICE_PER_MINUTE,
            ),
            "min_balance_to_start": ConfigService._parse_float_value(
                config_dict.get("min_balance_to_start"),
                settings.DEFAULT_MIN_BALANCE_TO_START,
            ),
            "auto_stop_threshold": ConfigService._parse_float_value(
                config_dict.get("auto_stop_threshold"),
                0.0,
            ),
            "comp_share_image_id": ConfigService._parse_text_value(
                config_dict.get("comp_share_image_id"),
                settings.DEFAULT_COMP_SHARE_IMAGE_ID,
            ),
            "gpu_type": ConfigService._parse_text_value(
                config_dict.get("gpu_type"),
                settings.DEFAULT_GPU_TYPE,
            ),
            "cpu_cores": ConfigService._parse_int_value(
                config_dict.get("cpu_cores"),
                settings.DEFAULT_CPU_CORES,
            ),
            "memory_gb": ConfigService._parse_int_value(
                config_dict.get("memory_gb"),
                settings.DEFAULT_MEMORY_GB,
            ),
        }

    @staticmethod
    async def get_price_per_minute(db: AsyncSession) -> float:
        """获取每分钟价格"""
        config = await ConfigService.get_config(db, "price_per_minute")
        if config:
            return ConfigService._parse_float_value(
                config.config_value,
                settings.DEFAULT_PRICE_PER_MINUTE,
            )
        return settings.DEFAULT_PRICE_PER_MINUTE

    @staticmethod
    async def get_min_balance_to_start(db: AsyncSession) -> float:
        """获取启动所需最低余额"""
        config = await ConfigService.get_config(db, "min_balance_to_start")
        if config:
            return ConfigService._parse_float_value(
                config.config_value,
                settings.DEFAULT_MIN_BALANCE_TO_START,
            )
        return settings.DEFAULT_MIN_BALANCE_TO_START

    @staticmethod
    async def get_all_configs(db: AsyncSession) -> dict:
        """获取所有配置"""
        result = await db.execute(select(SystemConfig))
        configs = result.scalars().all()

        config_dict = {}
        for config in configs:
            config_dict[config.config_key] = config.config_value

        return ConfigService.normalize_configs(config_dict)

    @staticmethod
    async def get_container_create_config(db: AsyncSession) -> dict:
        """获取创建容器实例所需的配置"""
        configs = await ConfigService.get_all_configs(db)
        return {
            key: configs[key]
            for key in ConfigService.CONTAINER_CREATE_CONFIG_KEYS
        }


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

    @staticmethod
    async def create_user_login_log(
        db: AsyncSession,
        phone: str,
        login_status: str,
        user_id: int = None,
        admin_id: int = None,
        failure_reason: str = None,
        ip_address: str = None,
        user_agent: str = None,
        auto_commit: bool = True,
    ):
        """创建用户登录日志"""
        log = UserLoginLog(
            user_id=user_id,
            admin_id=admin_id,
            phone=phone,
            login_status=login_status,
            failure_reason=failure_reason,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        db.add(log)
        if auto_commit:
            await db.commit()


# 导出服务
user_service = UserService()
admin_service = AdminService()
container_service = ContainerService()
config_service = ConfigService()
log_service = LogService()
