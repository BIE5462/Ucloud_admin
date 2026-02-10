from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Float,
    ForeignKey,
    Text,
    Boolean,
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.database import Base


class User(Base):
    """用户表"""

    __tablename__ = "m_user"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    company_name = Column(String(100), nullable=False, comment="公司名称")
    contact_name = Column(String(50), nullable=False, comment="联系人姓名")
    phone = Column(String(20), nullable=False, unique=True, comment="联系电话")
    password_hash = Column(String(255), nullable=False, comment="密码哈希")
    balance = Column(Float, default=0.0, comment="账号余额")
    current_container_id = Column(
        Integer, ForeignKey("container_record.id"), nullable=True, comment="当前容器ID"
    )
    admin_id = Column(
        Integer, ForeignKey("m_admin.id"), nullable=False, comment="所属管理员ID"
    )
    created_by = Column(
        Integer, ForeignKey("m_admin.id"), nullable=False, comment="创建者管理员ID"
    )
    status = Column(Integer, default=1, comment="状态：0-禁用, 1-正常")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login_at = Column(DateTime(timezone=True), nullable=True)

    # 关系
    admin = relationship("Admin", back_populates="users", foreign_keys=[admin_id])
    creator = relationship("Admin", foreign_keys=[created_by])


class Admin(Base):
    """管理员表（代理模式）"""

    __tablename__ = "m_admin"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(50), nullable=False, unique=True, comment="管理员账号")
    password_hash = Column(String(255), nullable=False, comment="密码哈希")
    role = Column(String(20), default="admin", comment="角色：super_admin/admin")
    status = Column(Integer, default=1, comment="状态：0-禁用, 1-正常")
    created_by = Column(
        Integer, ForeignKey("m_admin.id"), nullable=True, comment="创建者ID"
    )
    # 代理相关字段
    balance = Column(Float, default=0.0, comment="代理余额(元)")
    max_users = Column(Integer, default=10, comment="可开通用户数量上限")
    company_name = Column(String(100), nullable=True, comment="公司名")
    contact_name = Column(String(50), nullable=True, comment="联系人")
    phone = Column(String(20), nullable=True, comment="手机号")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    last_login_ip = Column(String(50), nullable=True)

    # 关系
    users = relationship("User", back_populates="admin", foreign_keys="User.admin_id")


class ContainerRecord(Base):
    """容器记录表"""

    __tablename__ = "container_record"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(
        Integer,
        ForeignKey("m_user.id"),
        nullable=False,
        comment="所属用户ID",
    )
    ucloud_instance_id = Column(String(100), nullable=False, comment="UCloud实例ID")
    instance_name = Column(String(100), nullable=False, comment="实例名称")
    status = Column(String(20), default="creating", comment="状态")
    gpu_type = Column(String(50), nullable=False, comment="GPU类型")
    cpu_cores = Column(Integer, nullable=False, comment="CPU核数")
    memory_gb = Column(Integer, nullable=False, comment="内存大小GB")
    storage_gb = Column(Integer, nullable=False, comment="存储大小GB")
    price_per_minute = Column(Float, nullable=False, comment="创建时的每分钟价格")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True, comment="本次启动时间")
    stopped_at = Column(DateTime(timezone=True), nullable=True, comment="本次停止时间")
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    total_running_minutes = Column(Integer, default=0, comment="累计运行分钟数")
    total_cost = Column(Float, default=0.0, comment="累计消费金额")
    connection_host = Column(String(100), nullable=True, comment="连接地址")
    connection_port = Column(Integer, default=3389, comment="连接端口")
    connection_username = Column(String(50), nullable=True, comment="连接用户名")
    connection_password = Column(String(100), nullable=True, comment="连接密码")


class SystemConfig(Base):
    """系统配置表"""

    __tablename__ = "system_config"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    config_key = Column(String(50), nullable=False, unique=True, comment="配置项键名")
    config_value = Column(String(255), nullable=False, comment="配置项值")
    description = Column(Text, comment="配置描述")
    updated_by = Column(Integer, ForeignKey("m_admin.id"), nullable=True)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class BillingChargeRecord(Base):
    """实时扣费记录表"""

    __tablename__ = "billing_charge_record"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("m_user.id"), nullable=False)
    container_id = Column(Integer, ForeignKey("container_record.id"), nullable=False)
    charge_minute = Column(
        DateTime(timezone=True), nullable=False, comment="扣费的这一分钟"
    )
    price_per_minute = Column(Float, nullable=False, comment="当时每分钟价格")
    amount = Column(Float, nullable=False, comment="扣费金额")
    balance_before = Column(Float, nullable=False, comment="扣费前余额")
    balance_after = Column(Float, nullable=False, comment="扣费后余额")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ContainerLog(Base):
    """容器操作日志表"""

    __tablename__ = "container_log"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("m_user.id"), nullable=False, comment="用户ID")
    container_id = Column(
        Integer, ForeignKey("container_record.id"), nullable=False, comment="容器ID"
    )
    admin_id = Column(
        Integer, ForeignKey("m_admin.id"), nullable=False, comment="归属管理员ID"
    )
    action = Column(
        String(50),
        nullable=False,
        comment="操作类型: create/start/stop/delete/auto_stop",
    )
    action_status = Column(String(20), nullable=False, comment="状态: success/failed")
    started_at = Column(DateTime(timezone=True), nullable=True, comment="本次启动时间")
    stopped_at = Column(DateTime(timezone=True), nullable=True, comment="本次停止时间")
    duration_minutes = Column(Integer, nullable=True, comment="使用时长(分钟)")
    cost = Column(Float, nullable=True, comment="本次消耗费用(元)")
    request_data = Column(Text, nullable=True)
    response_data = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AdminOperationLog(Base):
    """管理员操作日志表"""

    __tablename__ = "admin_operation_log"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    admin_id = Column(Integer, ForeignKey("m_admin.id"), nullable=False)
    action = Column(String(50), nullable=False)
    target_type = Column(String(50), nullable=False)
    target_id = Column(Integer, nullable=True)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    ip_address = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
