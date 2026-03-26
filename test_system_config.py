import os
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
BACKEND_ROOT = PROJECT_ROOT / "backend"

os.environ["DEBUG"] = "true"

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import get_settings
from app.core.container_configs import (
    FIXED_CONTAINER_CONFIGS,
    build_config_price_key,
)
from app.services.crud_service import ConfigService
from app.services.ucloud_service import UCloudService


class ConfigServiceTestCase(unittest.TestCase):
    """系统配置聚合逻辑测试"""

    def test_normalize_configs_uses_defaults(self):
        settings = get_settings()

        configs = ConfigService.normalize_configs({})

        self.assertEqual(
            configs["comp_share_image_id"],
            settings.DEFAULT_COMP_SHARE_IMAGE_ID,
        )
        self.assertEqual(
            configs["price_per_minute"],
            settings.DEFAULT_PRICE_PER_MINUTE,
        )
        self.assertEqual(
            configs["min_balance_to_start"],
            settings.DEFAULT_MIN_BALANCE_TO_START,
        )
        self.assertEqual(configs["auto_stop_threshold"], 0.0)
        self.assertEqual(len(configs["config_options"]), len(FIXED_CONTAINER_CONFIGS))

        for expected, actual in zip(FIXED_CONTAINER_CONFIGS, configs["config_options"]):
            self.assertEqual(actual["config_code"], expected["config_code"])
            self.assertEqual(actual["config_name"], expected["config_name"])
            self.assertEqual(actual["gpu_type"], expected["gpu_type"])
            self.assertEqual(actual["cpu_cores"], expected["cpu_cores"])
            self.assertEqual(actual["memory_gb"], expected["memory_gb"])
            self.assertEqual(actual["storage_gb"], expected["storage_gb"])
            self.assertEqual(
                actual["price_per_minute"], settings.DEFAULT_PRICE_PER_MINUTE
            )

    def test_normalize_configs_casts_and_sanitizes_values(self):
        config_3_price = 1.2
        configs = ConfigService.normalize_configs(
            {
                "price_per_minute": "0.8",
                "min_balance_to_start": "5.5",
                "auto_stop_threshold": "0.6",
                "comp_share_image_id": " image-123 ",
                build_config_price_key("config_3"): str(config_3_price),
            }
        )

        self.assertEqual(configs["price_per_minute"], 0.8)
        self.assertEqual(configs["min_balance_to_start"], 5.5)
        self.assertEqual(configs["auto_stop_threshold"], 0.6)
        self.assertEqual(configs["comp_share_image_id"], "image-123")

        config_option_map = {
            item["config_code"]: item for item in configs["config_options"]
        }
        self.assertEqual(config_option_map["config_3"]["price_per_minute"], config_3_price)
        self.assertEqual(config_option_map["config_1"]["price_per_minute"], 0.8)
        self.assertEqual(config_option_map["config_5"]["price_per_minute"], 0.8)


class UCloudServiceTestCase(unittest.TestCase):
    """UCloud 请求构参测试"""

    def test_build_create_payload_uses_system_config_values(self):
        payload = UCloudService.build_create_payload(
            instance_name="测试实例",
            create_config={
                "comp_share_image_id": "compshareImage-abc123",
                "gpu_type": "4090",
                "cpu_cores": 24,
                "memory_gb": 64,
                "storage_gb": 240,
            },
        )

        self.assertEqual(payload["Zone"], "cn-wlcb-01")
        self.assertEqual(payload["MachineType"], "G")
        self.assertEqual(payload["CompShareImageId"], "compshareImage-abc123")
        self.assertEqual(payload["GpuType"], "4090")
        self.assertEqual(payload["CPU"], 24)
        self.assertEqual(payload["Memory"], 64 * 1024)
        self.assertEqual(payload["GPU"], 1)
        self.assertEqual(payload["ChargeType"], "Postpay")
        self.assertEqual(payload["Disks"][0]["Size"], 240)
        self.assertEqual(payload["Disks"][0]["Type"], "CLOUD_SSD")
        self.assertEqual(payload["Name"], "测试实例")


if __name__ == "__main__":
    unittest.main()
