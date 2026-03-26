from typing import Dict, List, Optional


FIXED_CONTAINER_CONFIGS: List[Dict[str, object]] = [
    {
        "config_code": "config_1",
        "config_name": "3080Ti12G",
        "gpu_type": "3080Ti",
        "cpu_cores": 12,
        "memory_gb": 32,
        "storage_gb": 200,
    },
    {
        "config_code": "config_2",
        "config_name": "309024G",
        "gpu_type": "3090",
        "cpu_cores": 16,
        "memory_gb": 64,
        "storage_gb": 200,
    },
    {
        "config_code": "config_3",
        "config_name": "409024G",
        "gpu_type": "4090",
        "cpu_cores": 16,
        "memory_gb": 64,
        "storage_gb": 200,
    },
    {
        "config_code": "config_4",
        "config_name": "509032G",
        "gpu_type": "5090",
        "cpu_cores": 16,
        "memory_gb": 96,
        "storage_gb": 200,
    },
    {
        "config_code": "config_5",
        "config_name": "409048G",
        "gpu_type": "4090",
        "cpu_cores": 16,
        "memory_gb": 96,
        "storage_gb": 200,
    },
]

VALID_CONTAINER_CONFIG_CODES = tuple(
    item["config_code"] for item in FIXED_CONTAINER_CONFIGS
)


def build_config_price_key(config_code: str) -> str:
    return f"{config_code}_price_per_minute"


def get_fixed_container_configs() -> List[Dict[str, object]]:
    return [item.copy() for item in FIXED_CONTAINER_CONFIGS]


def get_fixed_container_config(config_code: str) -> Optional[Dict[str, object]]:
    for item in FIXED_CONTAINER_CONFIGS:
        if item["config_code"] == config_code:
            return item.copy()
    return None
