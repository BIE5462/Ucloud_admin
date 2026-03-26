from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


# ==================== 响应基类 ====================
class ResponseBase(BaseModel):
    code: int = 200
    message: str = "success"


class ResponseData(ResponseBase):
    data: Optional[dict] = None


# ==================== 用户相关 ====================
class UserLogin(BaseModel):
    phone: str
    password: str


class UserCreate(BaseModel):
    company_name: str
    contact_name: str
    phone: str
    password: str
    initial_balance: float = 0.0


class UserUpdate(BaseModel):
    company_name: Optional[str] = None
    contact_name: Optional[str] = None
    status: Optional[int] = None


class UserInfo(BaseModel):
    id: int
    company_name: str
    contact_name: str
    phone: str
    balance: float
    current_container_id: Optional[int] = None
    status: int
    created_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserChangePassword(BaseModel):
    old_password: str
    new_password: str


class UserResetPassword(BaseModel):
    new_password: str


# ==================== 管理员相关 ====================
class AdminLogin(BaseModel):
    username: str
    password: str


class AdminCreate(BaseModel):
    username: str
    password: str
    role: str = "admin"  # admin / super_admin
    company_name: Optional[str] = None
    contact_name: Optional[str] = None
    phone: Optional[str] = None
    initial_balance: Optional[float] = 0.0
    max_users: Optional[int] = 10


class AdminUpdate(BaseModel):
    status: Optional[int] = None
    role: Optional[str] = None
    max_users: Optional[int] = None
    company_name: Optional[str] = None
    contact_name: Optional[str] = None
    phone: Optional[str] = None


class AdminRecharge(BaseModel):
    type: str  # recharge / deduct
    amount: float
    description: Optional[str] = None


class UserBalanceChange(BaseModel):
    type: str  # recharge / deduct
    amount: float
    description: Optional[str] = None


class AdminInfo(BaseModel):
    id: int
    username: str
    role: str
    status: int
    created_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ==================== 容器相关 ====================
class ContainerCreate(BaseModel):
    instance_name: str = Field(min_length=1)
    force: bool = False  # 强制创建，删除已有实例

    @field_validator("instance_name")
    @classmethod
    def validate_instance_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("实例名称不能为空")
        return value


class ContainerInfo(BaseModel):
    id: int
    instance_name: str
    status: str
    gpu_type: str
    cpu_cores: int
    memory_gb: int
    storage_gb: int
    price_per_minute: float
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    stopped_at: Optional[datetime] = None
    total_running_minutes: int
    total_cost: float

    class Config:
        from_attributes = True


class ContainerStatus(BaseModel):
    status: str
    current_running_minutes: int
    current_session_cost: float
    balance: float
    price_per_minute: float
    remaining_minutes: int
    remaining_time_formatted: str
    connection_info: Optional[dict] = None


class ContainerConnectionInfo(BaseModel):
    host: str
    port: int
    username: str
    password: str


class ContainerDeleteRequest(BaseModel):
    confirm: bool = True
    reason: Optional[str] = None


# ==================== 系统配置相关 ====================
class SystemConfigUpdate(BaseModel):
    price_per_minute: float = Field(gt=0)
    min_balance_to_start: float = Field(ge=0)
    comp_share_image_id: str = Field(min_length=1)
    gpu_type: str = Field(min_length=1)
    cpu_cores: int = Field(gt=0)
    memory_gb: int = Field(gt=0)

    @field_validator("comp_share_image_id", "gpu_type")
    @classmethod
    def validate_non_empty_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("配置项不能为空")
        return value


class SystemConfigInfo(BaseModel):
    price_per_minute: float
    min_balance_to_start: float
    auto_stop_threshold: float = 0.0
    comp_share_image_id: str
    gpu_type: str
    cpu_cores: int
    memory_gb: int


# ==================== 扣费记录相关 ====================
class BillingChargeInfo(BaseModel):
    id: int
    charge_minute: datetime
    price_per_minute: float
    amount: float
    balance_before: float
    balance_after: float
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ==================== 日志相关 ====================
class ContainerLogInfo(BaseModel):
    id: int
    user_name: str
    admin_name: str
    action: str
    action_status: str
    started_at: Optional[datetime] = None
    stopped_at: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    cost: Optional[float] = None
    ip_address: Optional[str] = None
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AdminOperationLogInfo(BaseModel):
    id: int
    admin_username: str
    action: str
    target_type: str
    target_id: Optional[int] = None
    description: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ==================== 统计相关 ====================
class DashboardOverview(BaseModel):
    total_users: int
    total_containers: int
    running_containers: int
    stopped_containers: int
    total_balance: float
    today_income: float


class DashboardStatistics(BaseModel):
    today_new_users: int
    today_new_containers: int
    today_running_minutes: int
    today_income: float
    this_month_new_users: int
    this_month_income: float


class DashboardCharts(BaseModel):
    income_trend: List[dict]
    container_status: dict


class DashboardData(BaseModel):
    overview: DashboardOverview
    statistics: DashboardStatistics
    charts: DashboardCharts


# ==================== 分页相关 ====================
class PaginationParams(BaseModel):
    page: int = 1
    page_size: int = 20


class PaginationResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[dict]
