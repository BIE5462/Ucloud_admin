"""配置管理模块"""

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
import json


@dataclass
class AppConfig:
    """应用配置"""

    # API配置
    api_base_url: str = "http://localhost:8000/api"#"http://159.75.50.37:8000/api"
    api_timeout: int = 30
    api_max_retries: int = 3
    api_retry_delay: float = 1.0

    # RDP配置
    rdp_auto_connect: bool = True
    rdp_timeout: int = 30
    rdp_default_port: int = 3389
    rdp_username: str = "administrator"

    # UI配置
    window_width: int = 1000
    window_height: int = 700
    auto_refresh_interval: int = 60  # 秒

    # 日志配置
    log_level: str = "INFO"
    log_to_file: bool = True
    log_dir: str = "logs"

    # 其他
    save_credentials: bool = False  # 是否保存凭据到本地（不安全，仅用于开发）

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "api": {
                "base_url": self.api_base_url,
                "timeout": self.api_timeout,
                "max_retries": self.api_max_retries,
                "retry_delay": self.api_retry_delay,
            },
            "rdp": {
                "auto_connect": self.rdp_auto_connect,
                "timeout": self.rdp_timeout,
                "default_port": self.rdp_default_port,
                "username": self.rdp_username,
            },
            "ui": {
                "window_width": self.window_width,
                "window_height": self.window_height,
                "auto_refresh_interval": self.auto_refresh_interval,
            },
            "log": {
                "level": self.log_level,
                "to_file": self.log_to_file,
                "dir": self.log_dir,
            },
            "other": {
                "save_credentials": self.save_credentials,
            },
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AppConfig":
        """从字典创建配置"""
        config = cls()

        if "api" in data:
            api = data["api"]
            config.api_base_url = api.get("base_url", config.api_base_url)
            config.api_timeout = api.get("timeout", config.api_timeout)
            config.api_max_retries = api.get("max_retries", config.api_max_retries)
            config.api_retry_delay = api.get("retry_delay", config.api_retry_delay)

        if "rdp" in data:
            rdp = data["rdp"]
            config.rdp_auto_connect = rdp.get("auto_connect", config.rdp_auto_connect)
            config.rdp_timeout = rdp.get("timeout", config.rdp_timeout)
            config.rdp_default_port = rdp.get("default_port", config.rdp_default_port)
            config.rdp_username = rdp.get("username", config.rdp_username)

        if "ui" in data:
            ui = data["ui"]
            config.window_width = ui.get("window_width", config.window_width)
            config.window_height = ui.get("window_height", config.window_height)
            config.auto_refresh_interval = ui.get(
                "auto_refresh_interval", config.auto_refresh_interval
            )

        if "log" in data:
            log = data["log"]
            config.log_level = log.get("level", config.log_level)
            config.log_to_file = log.get("to_file", config.log_to_file)
            config.log_dir = log.get("dir", config.log_dir)

        if "other" in data:
            other = data["other"]
            config.save_credentials = other.get(
                "save_credentials", config.save_credentials
            )

        return config


class ConfigManager:
    """配置管理器"""

    _instance: Optional["ConfigManager"] = None
    _config: Optional[AppConfig] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._config = None
        return cls._instance

    @property
    def config(self) -> AppConfig:
        """获取当前配置"""
        if self._config is None:
            self.load_config()
        return self._config  # type: ignore

    def load_config(self) -> AppConfig:
        """
        加载配置

        优先级：环境变量 > 配置文件 > 默认值
        """
        # 1. 从默认值开始
        config = AppConfig()

        # 2. 加载配置文件
        config_file = self.get_config_file_path()
        if config_file.exists():
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    config = AppConfig.from_dict(data)
            except Exception as e:
                print(f"加载配置文件失败: {e}")

        # 3. 从环境变量覆盖
        config.api_base_url = os.getenv("API_BASE_URL", config.api_base_url)
        config.api_timeout = int(os.getenv("API_TIMEOUT", config.api_timeout))
        config.log_level = os.getenv("LOG_LEVEL", config.log_level)

        # RDP配置
        rdp_auto_env = os.getenv("RDP_AUTO_CONNECT")
        if rdp_auto_env:
            config.rdp_auto_connect = rdp_auto_env.lower() == "true"

        self._config = config
        return config

    def save_config(self) -> bool:
        """保存配置到文件"""
        try:
            if self._config is None:
                return False
            config_file = self.get_config_file_path()
            config_file.parent.mkdir(parents=True, exist_ok=True)

            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(self._config.to_dict(), f, indent=2, ensure_ascii=False)

            return True
        except Exception as e:
            print(f"保存配置失败: {e}")
            return False

    @staticmethod
    def get_config_file_path() -> Path:
        """获取配置文件路径"""
        # 使用用户目录下的配置
        if os.name == "nt":  # Windows
            config_dir = Path(os.getenv("APPDATA", Path.home())) / "CloudPCClient"
        else:  # macOS/Linux
            config_dir = Path.home() / ".config" / "cloudpc-client"

        return config_dir / "config.json"

    @staticmethod
    def get_app_dir() -> Path:
        """获取应用目录"""
        return Path(__file__).parent.parent

    @staticmethod
    def get_log_dir() -> Path:
        """获取日志目录"""
        config = ConfigManager().config
        log_dir = ConfigManager.get_app_dir() / config.log_dir
        log_dir.mkdir(parents=True, exist_ok=True)
        return log_dir


# 便捷函数
def get_config() -> AppConfig:
    """获取配置"""
    return ConfigManager().config


def reload_config() -> AppConfig:
    """重新加载配置"""
    return ConfigManager().load_config()


def save_config() -> bool:
    """保存配置"""
    return ConfigManager().save_config()
