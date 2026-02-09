from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # 应用配置
    APP_NAME: str = "云电脑容器管理系统"
    DEBUG: bool = True

    # 数据库
    DATABASE_URL: str = "sqlite+aiosqlite:///./cloud_pc.db"

    # JWT配置
    SECRET_KEY: str = "yXjiBi7GCQubdwBNL8axQSuRqILofUIbXZ022yCRzrE"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_DAYS: int = 1

    # UCloud配置
    UCLOUD_REGION: str = "cn-wlcb"
    UCLOUD_ZONE: str = "cn-wlcb-01"
    UCLOUD_BASE_URL: str = "https://api.compshare.cn"
    UCLOUD_PUBLIC_KEY: str = "4eZCt9GH5fS1XEutXeyTtv6A0QReFzqW5"
    UCLOUD_PRIVATE_KEY: str = "9W5iDOdYn7cJxUaEgsYhMVCvhYR71fraGHpkmmJjuWmU"
    UCLOUD_IMAGE_ID: str = "compshareImage-1mnqn08rd1xz"

    # 默认价格配置
    DEFAULT_PRICE_PER_MINUTE: float = 0.5
    DEFAULT_MIN_BALANCE_TO_START: float = 2.5

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings():
    return Settings()
