#!/usr/bin/env python3
"""
RDP连接测试脚本
参考客户端连接远程的方式测试连接过程

连接信息：
- 主机: 117.50.176.121:3389
- 用户名: Administrator
- 密码: h6034g9q1dpWZ7A2
"""

import subprocess
import time
import logging
from typing import Tuple

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 连接配置
RDP_HOST = "117.50.176.121:3389"
RDP_USERNAME = "Administrator"
RDP_PASSWORD = "h6034g9q1dpWZ7A2"


def parse_host(host_str: str) -> Tuple[str, int]:
    """解析主机地址和端口"""
    if ":" in host_str:
        parts = host_str.rsplit(":", 1)
        try:
            return parts[0], int(parts[1])
        except ValueError:
            return host_str, 3389
    return host_str, 3389


def test_save_credentials(hostname: str, username: str, password: str) -> bool:
    """
    测试保存凭据到Windows凭据管理器

    参考: client/utils/rdp_helper.py:44-98
    """
    target = f"TERMSRV/{hostname}"

    logger.info(f"测试目标: {target}")
    logger.info(f"测试用户名: {username}")
    logger.info(f"测试密码: {'*' * len(password)}")

    try:
        # 步骤1: 先删除旧的凭据（如果存在）
        logger.info("步骤1: 删除旧凭据...")
        delete_result = subprocess.run(
            f"cmdkey /delete:{target}",
            shell=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
        logger.info(f"删除旧凭据结果: {delete_result.returncode}")
        if delete_result.stderr:
            logger.info(f"删除输出: {delete_result.stderr.strip()}")

        # 步骤2: 保存新凭据
        logger.info("步骤2: 保存新凭据...")
        save_cmd = f'cmdkey /generic:{target} /user:{username} /pass:"{password}"'
        logger.info(f"执行命令: cmdkey /generic:{target} /user:{username} /pass:****")

        result = subprocess.run(
            save_cmd, shell=True, capture_output=True, text=True, timeout=5
        )

        logger.info(f"保存凭据返回码: {result.returncode}")
        logger.info(f"保存凭据输出: {result.stdout.strip() if result.stdout else '无'}")

        if result.stderr:
            logger.warning(f"保存凭据错误输出: {result.stderr.strip()}")

        if result.returncode == 0:
            logger.info("✅ 凭据保存成功")
            return True
        else:
            # 尝试备选方法（不带引号）
            logger.info("尝试备选方法（不带引号）...")
            save_cmd_alt = f"cmdkey /generic:{target} /user:{username} /pass:{password}"
            result = subprocess.run(
                save_cmd_alt, shell=True, capture_output=True, text=True, timeout=5
            )

            if result.returncode == 0:
                logger.info("✅ 凭据保存成功（备选方法）")
                return True
            else:
                logger.error(f"❌ 凭据保存失败: {result.stderr}")
                return False

    except subprocess.TimeoutExpired:
        logger.error("❌ 凭据保存超时")
        return False
    except Exception as e:
        logger.error(f"❌ 保存凭据时出错: {e}")
        return False


def test_list_credentials():
    """测试列出已保存的凭据"""
    logger.info("\n" + "=" * 50)
    logger.info("列出当前保存的凭据...")
    logger.info("=" * 50)

    try:
        result = subprocess.run(
            "cmdkey /list", shell=True, capture_output=True, text=True, timeout=5
        )

        if result.returncode == 0:
            # 过滤显示与TERMSRV相关的凭据
            lines = result.stdout.strip().split("\n")
            termsrv_creds = [line for line in lines if "TERMSRV" in line]

            if termsrv_creds:
                logger.info("已保存的远程桌面凭据:")
                for cred in termsrv_creds:
                    logger.info(f"  {cred.strip()}")
            else:
                logger.info("未找到远程桌面凭据")
        else:
            logger.error(f"列出凭据失败: {result.stderr}")

    except Exception as e:
        logger.error(f"列出凭据时出错: {e}")


def test_rdp_connection():
    """
    测试RDP连接

    参考: client/utils/rdp_helper.py:133-235
    """
    logger.info("\n" + "=" * 50)
    logger.info("开始RDP连接测试")
    logger.info("=" * 50)

    # 解析主机和端口
    hostname, port = parse_host(RDP_HOST)
    host_with_port = f"{hostname}:{port}"

    logger.info(f"主机地址: {hostname}")
    logger.info(f"端口: {port}")
    logger.info(f"完整地址: {host_with_port}")
    logger.info(f"用户名: {RDP_USERNAME}")

    # 步骤1: 保存凭据
    logger.info("\n" + "-" * 50)
    logger.info("步骤1: 保存凭据到Windows凭据管理器")
    logger.info("-" * 50)

    credentials_saved = test_save_credentials(hostname, RDP_USERNAME, RDP_PASSWORD)

    # 列出凭据验证
    test_list_credentials()

    # 步骤2: 启动远程桌面连接
    logger.info("\n" + "-" * 50)
    logger.info("步骤2: 启动远程桌面连接")
    logger.info("-" * 50)

    connect_cmd = f"mstsc /v:{host_with_port}"
    logger.info(f"执行命令: {connect_cmd}")

    try:
        # 启动mstsc进程
        process = subprocess.Popen(
            connect_cmd, shell=True, creationflags=subprocess.CREATE_NEW_CONSOLE
        )

        logger.info(f"✅ 远程桌面进程已启动 (PID: {process.pid})")
        logger.info("等待连接窗口出现...")
        time.sleep(2)

        # 可选：自动点击连接按钮
        logger.info("\n" + "-" * 50)
        logger.info("步骤3: 自动点击连接按钮")
        logger.info("-" * 50)

        try:
            import ctypes

            # 发送Tab键聚焦到连接按钮
            logger.info("发送Tab键...")
            ctypes.windll.user32.keybd_event(0x09, 0, 0, 0)  # Tab down
            time.sleep(0.1)
            ctypes.windll.user32.keybd_event(0x09, 0, 0x0002, 0)  # Tab up

            time.sleep(0.5)

            # 发送回车键点击连接
            logger.info("发送回车键...")
            ctypes.windll.user32.keybd_event(0x0D, 0, 0, 0)  # Enter down
            time.sleep(0.1)
            ctypes.windll.user32.keybd_event(0x0D, 0, 0x0002, 0)  # Enter up

            logger.info("✅ 已尝试自动点击连接按钮")

        except Exception as e:
            logger.warning(f"⚠️ 自动点击失败: {e}")
            logger.info("请手动点击连接按钮")

        # 总结
        logger.info("\n" + "=" * 50)
        logger.info("连接测试完成")
        logger.info("=" * 50)
        logger.info(f"主机: {host_with_port}")
        logger.info(f"用户名: {RDP_USERNAME}")
        logger.info(f"密码: {'已自动配置' if credentials_saved else RDP_PASSWORD}")
        logger.info("\n远程桌面窗口应该已经打开，请检查连接状态。")

        return True

    except Exception as e:
        logger.error(f"❌ 启动远程桌面连接失败: {e}")
        return False


def test_delete_credentials():
    """测试删除凭据"""
    logger.info("\n" + "=" * 50)
    logger.info("清理测试凭据")
    logger.info("=" * 50)

    hostname, _ = parse_host(RDP_HOST)
    target = f"TERMSRV/{hostname}"

    try:
        result = subprocess.run(
            f"cmdkey /delete:{target}",
            shell=True,
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode == 0:
            logger.info(f"✅ 凭据已删除: {target}")
        else:
            logger.info(f"凭据删除结果: {result.stderr.strip()}")

    except Exception as e:
        logger.error(f"删除凭据时出错: {e}")


def main():
    """主函数"""
    logger.info("=" * 50)
    logger.info("RDP连接测试脚本")
    logger.info("=" * 50)
    logger.info(f"目标主机: {RDP_HOST}")
    logger.info(f"用户名: {RDP_USERNAME}")
    logger.info("")
    logger.info("此脚本将：")
    logger.info("1. 保存凭据到Windows凭据管理器")
    logger.info("2. 启动mstsc远程桌面连接")
    logger.info("3. 尝试自动点击连接按钮")
    logger.info("")

    try:
        # 执行连接测试
        success = test_rdp_connection()

        if success:
            logger.info("\n✅ 测试完成！请检查远程桌面窗口。")

            # 等待用户确认后再清理
            input("\n按Enter键清理测试凭据并退出...")
            test_delete_credentials()
        else:
            logger.error("\n❌ 测试失败！")

    except KeyboardInterrupt:
        logger.info("\n\n用户中断，正在清理...")
        test_delete_credentials()


if __name__ == "__main__":
    main()
