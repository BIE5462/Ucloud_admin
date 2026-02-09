"""远程桌面连接工具 - 支持Windows自动RDP连接"""

import os
import platform
import subprocess
import time
import logging
from typing import Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class RDPConnectionInfo:
    """RDP连接信息"""

    host: str
    port: int = 3389
    username: str = "administrator"
    password: str = ""
    uhost_id: str = ""  # UHost ID，用于日志和调试


class RDPHelper:
    """远程桌面连接助手"""

    @staticmethod
    def is_windows() -> bool:
        """检查是否为Windows系统"""
        return platform.system() == "Windows"

    @staticmethod
    def parse_host(host_str: str) -> Tuple[str, int]:
        """解析主机地址和端口"""
        if ":" in host_str:
            parts = host_str.rsplit(":", 1)
            try:
                return parts[0], int(parts[1])
            except ValueError:
                return host_str, 3389
        return host_str, 3389

    @staticmethod
    def save_credentials(hostname: str, username: str, password: str) -> bool:
        """
        保存凭据到Windows凭据管理器

        Args:
            hostname: 主机名
            username: 用户名
            password: 密码

        Returns:
            bool: 是否保存成功
        """
        try:
            # 使用cmdkey命令保存凭据
            target = f"TERMSRV/{hostname}"

            # 先删除旧的凭据（如果存在）
            subprocess.run(
                f"cmdkey /delete:{target}", shell=True, capture_output=True, timeout=5
            )

            # 保存新凭据
            save_cmd = f'cmdkey /generic:{target} /user:{username} /pass:"{password}"'
            result = subprocess.run(
                save_cmd, shell=True, capture_output=True, text=True, timeout=5
            )

            if result.returncode == 0:
                logger.info(f"凭据已保存到Windows凭据管理器: {target}")
                return True
            else:
                # 尝试不带引号的密码
                save_cmd_alt = (
                    f"cmdkey /generic:{target} /user:{username} /pass:{password}"
                )
                result = subprocess.run(
                    save_cmd_alt, shell=True, capture_output=True, text=True, timeout=5
                )

                if result.returncode == 0:
                    logger.info(f"凭据已保存（备选方法）: {target}")
                    return True
                else:
                    logger.warning(f"凭据保存失败: {result.stderr}")
                    return False

        except subprocess.TimeoutExpired:
            logger.warning("凭据保存超时")
            return False
        except Exception as e:
            logger.error(f"保存凭据时出错: {e}")
            return False

    @staticmethod
    def auto_click_connect() -> bool:
        """
        自动点击远程桌面连接按钮

        发送Tab键聚焦到连接按钮，然后发送回车键

        Returns:
            bool: 是否成功发送按键
        """
        try:
            import ctypes

            # 发送Tab键
            ctypes.windll.user32.keybd_event(0x09, 0, 0, 0)  # Tab down
            time.sleep(0.1)
            ctypes.windll.user32.keybd_event(0x09, 0, 0x0002, 0)  # Tab up
            logger.debug("已发送Tab键")

            time.sleep(0.3)  # 等待焦点切换

            # 发送回车键
            ctypes.windll.user32.keybd_event(0x0D, 0, 0, 0)  # Enter down
            time.sleep(0.1)
            ctypes.windll.user32.keybd_event(0x0D, 0, 0x0002, 0)  # Enter up
            logger.debug("已发送回车键")

            return True

        except Exception as e:
            logger.error(f"自动按键失败: {e}")
            return False

    @classmethod
    def start_remote_desktop(
        cls, conn_info: RDPConnectionInfo, auto_connect: bool = True
    ) -> Tuple[bool, str]:
        """
        启动Windows远程桌面连接

        Args:
            conn_info: RDP连接信息
            auto_connect: 是否自动点击连接按钮

        Returns:
            Tuple[bool, str]: (是否成功, 状态消息)
        """
        # 检查Windows系统
        if not cls.is_windows():
            return False, "❌ 当前不是Windows系统，无法启动远程桌面连接"

        try:
            logger.info(f"正在启动远程桌面连接到: {conn_info.host}")

            # 解析主机名和端口
            hostname, port = cls.parse_host(conn_info.host)
            host_with_port = f"{hostname}:{port}"

            # 步骤1: 保存凭据
            logger.info("步骤1: 正在保存凭据到Windows凭据管理器...")
            credentials_saved = cls.save_credentials(
                hostname, conn_info.username, conn_info.password
            )

            if not credentials_saved:
                logger.warning("凭据保存失败，将尝试直接连接（可能需要手动输入密码）")

            # 步骤2: 启动远程桌面连接
            logger.info("步骤2: 正在启动远程桌面连接...")
            connect_cmd = f"mstsc /v:{host_with_port}"

            # 启动mstsc进程
            process = subprocess.Popen(
                connect_cmd,
                shell=True,
                creationflags=subprocess.CREATE_NEW_CONSOLE
                if hasattr(subprocess, "CREATE_NEW_CONSOLE")
                else 0,
            )

            # 步骤3: 自动点击连接（可选）
            auto_clicked = False
            if auto_connect:
                logger.info("等待连接窗口出现...")
                time.sleep(0.8)  # 等待窗口加载

                logger.info("尝试自动点击连接按钮...")
                auto_clicked = cls.auto_click_connect()

                if auto_clicked:
                    logger.info("✅ 已尝试自动点击连接按钮")
                else:
                    logger.warning("⚠️ 自动点击失败，请手动点击'连接'按钮")

            # 构建成功消息
            msg_parts = [
                f"✅ 远程桌面连接已成功启动",
                f"",
                f"📋 连接信息:",
                f"   主机: {host_with_port}",
                f"   用户名: {conn_info.username}",
            ]

            if credentials_saved:
                msg_parts.append(f"   密码: 已自动配置")
            else:
                msg_parts.append(f"   密码: {conn_info.password}")

            if auto_connect:
                if auto_clicked:
                    msg_parts.append(f"   自动连接: ✅ 已尝试自动点击")
                else:
                    msg_parts.append(f"   自动连接: ⚠️ 需要手动点击")

            return True, "\n".join(msg_parts)

        except subprocess.TimeoutExpired:
            logger.warning("远程桌面启动超时")
            return False, "⚠️ 远程桌面连接启动超时"

        except Exception as e:
            logger.error(f"启动远程桌面连接失败: {e}")

            # 最后尝试：直接启动mstsc
            try:
                logger.info("尝试最后的方法: 直接启动远程桌面...")
                os.system(f"start mstsc /v:{conn_info.host}")

                return True, (
                    f"✅ 远程桌面已启动（备用方式）\n\n"
                    f"请手动输入:\n"
                    f"用户名: {conn_info.username}\n"
                    f"密码: {conn_info.password}"
                )
            except:
                return False, f"❌ 启动远程桌面连接失败: {str(e)}"

    @classmethod
    def quick_connect(
        cls, host: str, password: str, uhost_id: str = "", auto_connect: bool = True
    ) -> Tuple[bool, str]:
        """
        快速连接方法 - 直接使用IP和密码

        Args:
            host: 主机地址（IP或IP:端口）
            password: 密码
            uhost_id: UHost ID（可选，用于日志）
            auto_connect: 是否自动点击连接

        Returns:
            Tuple[bool, str]: (是否成功, 状态消息)
        """
        conn_info = RDPConnectionInfo(host=host, password=password, uhost_id=uhost_id)
        return cls.start_remote_desktop(conn_info, auto_connect)


def start_remote_desktop(
    host: str, password: str, uhost_id: str = "", auto_connect: bool = True
) -> Tuple[bool, str]:
    """
    便捷函数 - 启动Windows远程桌面连接

    Args:
        host: 主机地址
        password: 密码
        uhost_id: UHost ID（可选）
        auto_connect: 是否自动点击连接按钮

    Returns:
        Tuple[bool, str]: (是否成功, 状态消息)
    """
    return RDPHelper.quick_connect(host, password, uhost_id, auto_connect)


# 非Windows系统的替代方案
class NonWindowsRDPHelper:
    """非Windows系统的RDP连接帮助类"""

    @staticmethod
    def get_connection_instructions(host: str, username: str, password: str) -> str:
        """
        获取连接说明

        Args:
            host: 主机地址
            username: 用户名
            password: 密码

        Returns:
            str: 连接说明文本
        """
        system = platform.system()

        if system == "Darwin":  # macOS
            return f"""
请在macOS上使用以下方式连接:

1. 使用Microsoft Remote Desktop应用:
   - 从App Store下载 Microsoft Remote Desktop
   - 添加PC，输入: {host}
   - 用户名: {username}
   - 密码: {password}

2. 或使用命令行:
   open "rdp://{username}@{host}"
"""
        elif system == "Linux":
            return f"""
请在Linux上使用以下方式连接:

1. 使用Remmina:
   - 安装: sudo apt install remmina
   - 启动: remmina
   - 输入: rdp://{username}@{host}

2. 使用xfreerdp:
   xfreerdp3 /v:{host} /u:{username} /p:'{password}'

3. 使用rdesktop:
   rdesktop -u {username} -p '{password}' {host}
"""
        else:
            return f"""
请使用远程桌面客户端连接:

主机: {host}
用户名: {username}
密码: {password}
"""


def get_rdp_instructions(
    host: str, username: str = "administrator", password: str = ""
) -> str:
    """
    获取当前系统的RDP连接说明

    Args:
        host: 主机地址
        username: 用户名
        password: 密码

    Returns:
        str: 连接说明
    """
    if RDPHelper.is_windows():
        return f"""
Windows远程桌面连接信息:

主机: {host}
用户名: {username}
密码: {password}

点击"连接远程桌面"按钮可自动启动连接。
"""
    else:
        helper = NonWindowsRDPHelper()
        return helper.get_connection_instructions(host, username, password)
