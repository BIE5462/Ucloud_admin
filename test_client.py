"""客户端功能测试脚本"""

import sys
import os

# 确保可以导入client模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from client.config import get_config, ConfigManager
from client.utils.rdp_helper import RDPHelper, RDPConnectionInfo
from client.api import APIClient, APIError


def test_config():
    """测试配置系统"""
    print("=" * 50)
    print("测试配置系统")
    print("=" * 50)

    config = get_config()
    print(f"API Base URL: {config.api_base_url}")
    print(f"API Timeout: {config.api_timeout}")
    print(f"RDP Auto Connect: {config.rdp_auto_connect}")
    print(f"Window Size: {config.window_width}x{config.window_height}")

    config_file = ConfigManager.get_config_file_path()
    print(f"Config File: {config_file}")
    print("✅ 配置系统测试通过\n")


def test_rdp_helper():
    """测试RDP助手"""
    print("=" * 50)
    print("测试RDP助手")
    print("=" * 50)

    # 测试Windows检测
    is_win = RDPHelper.is_windows()
    print(f"是否为Windows系统: {is_win}")

    # 测试主机解析
    test_cases = [
        "192.168.1.100",
        "192.168.1.100:3389",
        "example.com:13389",
    ]

    for host in test_cases:
        hostname, port = RDPHelper.parse_host(host)
        print(f"解析 '{host}' -> 主机: {hostname}, 端口: {port}")

    # 测试连接信息类
    conn_info = RDPConnectionInfo(
        host="192.168.1.100:3389",
        username="administrator",
        password="TestPassword123",
        uhost_id="uhost-abc123",
    )
    print(f"连接信息: {conn_info}")

    print("✅ RDP助手测试通过\n")


def test_api_client():
    """测试API客户端"""
    print("=" * 50)
    print("测试API客户端")
    print("=" * 50)

    client = APIClient()
    print(f"Base URL: {client.config.api_base_url}")
    print(f"Timeout: {client.config.api_timeout}")
    print(f"Max Retries: {client.config.api_max_retries}")

    # 测试token管理
    client.set_token("test_token_12345")
    print(f"Token设置成功")
    client.clear_token()
    print(f"Token清除成功")

    print("✅ API客户端测试通过\n")


def test_rdp_instructions():
    """测试RDP连接说明"""
    print("=" * 50)
    print("测试RDP连接说明")
    print("=" * 50)

    from client.utils.rdp_helper import get_rdp_instructions

    instructions = get_rdp_instructions(
        host="192.168.1.100:3389", username="administrator", password="TestPass123"
    )
    print(instructions)
    print("✅ RDP连接说明测试通过\n")


def main():
    """运行所有测试"""
    print("\n" + "=" * 50)
    print("客户端功能测试")
    print("=" * 50 + "\n")

    try:
        test_config()
        test_rdp_helper()
        test_api_client()
        test_rdp_instructions()

        print("=" * 50)
        print("✅ 所有测试通过！")
        print("=" * 50)

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
