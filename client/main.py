"""
云电脑客户端 - PySide6 GUI应用程序

功能：
- 用户登录
- 云电脑管理（创建、启动、停止、删除）
- 一键连接远程桌面（Windows自动RDP）
- 实时计费显示
"""

import sys
import logging
import time
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QMessageBox,
    QStackedWidget,
    QGroupBox,
    QGridLayout,
    QSpinBox,
    QComboBox,
    QDialog,
    QTextEdit,
    QTabWidget,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont

# 导入自定义模块
from config import get_config, ConfigManager
from api import api_client
from utils import start_remote_desktop, get_rdp_instructions


# 配置日志
def setup_logging():
    """配置日志系统"""
    config = get_config()

    handlers: list[logging.Handler] = [logging.StreamHandler()]

    if config.log_to_file:
        log_dir = ConfigManager.get_log_dir()
        log_file = log_dir / "client.log"
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))

    logging.basicConfig(
        level=getattr(logging, config.log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=handlers,
    )


class LoginDialog(QDialog):
    """登录对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("云电脑客户端 - 登录")
        self.setFixedSize(500, 600)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(40, 30, 40, 30)

        # 标题
        title = QLabel("云电脑容器管理系统")
        title.setFont(QFont("Microsoft YaHei", 20, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #303133; margin-bottom: 10px;")
        layout.addWidget(title)

        subtitle = QLabel("用户登录")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color: #909399; font-size: 14px; margin-bottom: 20px;")
        layout.addWidget(subtitle)

        # 手机号
        phone_label = QLabel("手机号:")
        phone_label.setStyleSheet("color: #606266; font-weight: bold;")
        layout.addWidget(phone_label)

        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("请输入手机号")
        self.phone_input.setStyleSheet("""
            QLineEdit {
                padding: 10px;
                border: 1px solid #DCDFE6;
                border-radius: 4px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 1px solid #409EFF;
            }
        """)
        layout.addWidget(self.phone_input)

        # 密码
        pwd_label = QLabel("密码:")
        pwd_label.setStyleSheet("color: #606266; font-weight: bold;")
        layout.addWidget(pwd_label)

        self.pwd_input = QLineEdit()
        self.pwd_input.setEchoMode(QLineEdit.Password)
        self.pwd_input.setPlaceholderText("请输入密码")
        self.pwd_input.setStyleSheet("""
            QLineEdit {
                padding: 10px;
                border: 1px solid #DCDFE6;
                border-radius: 4px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 1px solid #409EFF;
            }
        """)
        layout.addWidget(self.pwd_input)

        # 登录按钮
        self.login_btn = QPushButton("登 录")
        self.login_btn.setStyleSheet("""
            QPushButton {
                background-color: #409EFF;
                color: white;
                padding: 12px;
                font-size: 16px;
                font-weight: bold;
                border-radius: 4px;
                border: none;
                margin-top: 10px;
            }
            QPushButton:hover {
                background-color: #66b1ff;
            }
            QPushButton:pressed {
                background-color: #3a8ee6;
            }
        """)
        self.login_btn.clicked.connect(self.handle_login)
        layout.addWidget(self.login_btn)

        # 提示信息
        tips = QLabel("测试账号: 请联系管理员创建")
        tips.setAlignment(Qt.AlignCenter)
        tips.setStyleSheet("color: #C0C4CC; font-size: 12px; margin-top: 15px;")
        layout.addWidget(tips)

        # 配置信息
        config = get_config()
        api_label = QLabel(f"API: {config.api_base_url}")
        api_label.setAlignment(Qt.AlignCenter)
        api_label.setStyleSheet("color: #DCDFE6; font-size: 10px; margin-top: 5px;")
        layout.addWidget(api_label)

        self.setLayout(layout)

        # 设置回车键登录
        self.pwd_input.returnPressed.connect(self.handle_login)

    def handle_login(self):
        """处理登录"""
        phone = self.phone_input.text().strip()
        password = self.pwd_input.text().strip()

        if not phone:
            QMessageBox.warning(self, "提示", "请输入手机号")
            return

        if not password:
            QMessageBox.warning(self, "提示", "请输入密码")
            return

        self.login_btn.setEnabled(False)
        self.login_btn.setText("登录中...")

        try:
            result = api_client.login(phone, password)

            if result.is_ok():
                self.user_info = result.data.get("user", {})
                self.accept()
            else:
                # 显示详细错误信息
                error_msg = result.get_error_display()
                QMessageBox.critical(self, "登录失败", error_msg)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"登录时发生错误: {str(e)}")
        finally:
            self.login_btn.setEnabled(True)
            self.login_btn.setText("登 录")


class CreateContainerDialog(QDialog):
    """创建云电脑对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("创建云电脑")
        self.setFixedSize(400, 300)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 20, 30, 20)

        # 配置信息（固定参数，仅展示）
        config_group = QGroupBox("配置信息")
        config_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 14px;
                border: 1px solid #DCDFE6;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        config_layout = QGridLayout()
        config_layout.setSpacing(15)

        # 显示固定配置
        config_layout.addWidget(QLabel("GPU:"), 0, 0)
        gpu_label = QLabel("NVIDIA 3080Ti x 1")
        gpu_label.setStyleSheet("color: #606266;")
        config_layout.addWidget(gpu_label, 0, 1)

        config_layout.addWidget(QLabel("CPU:"), 1, 0)
        cpu_label = QLabel("12 核")
        cpu_label.setStyleSheet("color: #606266;")
        config_layout.addWidget(cpu_label, 1, 1)

        config_layout.addWidget(QLabel("内存:"), 2, 0)
        memory_label = QLabel("32 GB")
        memory_label.setStyleSheet("color: #606266;")
        config_layout.addWidget(memory_label, 2, 1)

        config_layout.addWidget(QLabel("存储:"), 3, 0)
        storage_label = QLabel("200 GB SSD")
        storage_label.setStyleSheet("color: #606266;")
        config_layout.addWidget(storage_label, 3, 1)

        config_group.setLayout(config_layout)
        layout.addWidget(config_group)

        # 实例名称
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("实例名称:"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("请输入实例名称")
        name_layout.addWidget(self.name_input)
        layout.addLayout(name_layout)

        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)

        self.create_btn = QPushButton("创 建")
        self.create_btn.setStyleSheet("""
            QPushButton {
                background-color: #67C23A;
                color: white;
                padding: 12px 40px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 4px;
                border: none;
            }
            QPushButton:hover {
                background-color: #85ce61;
            }
        """)
        self.create_btn.clicked.connect(self.accept)

        cancel_btn = QPushButton("取 消")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #909399;
                color: white;
                padding: 12px 40px;
                font-size: 14px;
                border-radius: 4px;
                border: none;
            }
            QPushButton:hover {
                background-color: #a6a9ad;
            }
        """)
        cancel_btn.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(self.create_btn)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addStretch()

        layout.addLayout(btn_layout)
        layout.addStretch()

        self.setLayout(layout)


class MainWindow(QMainWindow):
    """主窗口"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("云电脑客户端")
        self.config = get_config()
        self.resize(self.config.window_width, self.config.window_height)

        self.user_info = {}
        self.container_info = None
        self.current_connection_info = None  # 当前连接信息

        # 操作冷却时间跟踪 (20秒)
        self.operation_cooldown = 20
        self.last_operation_time = {
            "stop": 0.0,
            "delete": 0.0,
        }

        # 设置定时器
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_status)

        self.setup_ui()

    def setup_ui(self):
        """设置UI"""
        # 中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        central_widget.setLayout(layout)

        # 顶部信息栏
        top_layout = QHBoxLayout()

        self.company_label = QLabel("公司: -")
        self.company_label.setFont(QFont("Microsoft YaHei", 12))
        self.company_label.setStyleSheet("color: #303133;")

        self.balance_label = QLabel("余额: ¥0.00")
        self.balance_label.setFont(QFont("Microsoft YaHei", 12))
        self.balance_label.setStyleSheet("color: #67C23A; font-weight: bold;")

        top_layout.addWidget(self.company_label)
        top_layout.addStretch()
        top_layout.addWidget(self.balance_label)

        logout_btn = QPushButton("退出登录")
        logout_btn.setStyleSheet("""
            QPushButton {
                background-color: #F56C6C;
                color: white;
                padding: 6px 15px;
                border-radius: 4px;
                border: none;
            }
            QPushButton:hover {
                background-color: #f78989;
            }
        """)
        logout_btn.clicked.connect(self.logout)
        top_layout.addWidget(logout_btn)

        layout.addLayout(top_layout)

        # 主内容区
        self.content_stack = QStackedWidget()

        # 1. 无云电脑页面
        self.no_container_widget = self.create_no_container_widget()
        self.content_stack.addWidget(self.no_container_widget)

        # 2. 云电脑信息页面
        self.container_widget = self.create_container_widget()
        self.content_stack.addWidget(self.container_widget)

        layout.addWidget(self.content_stack)

        # 底部按钮
        bottom_layout = QHBoxLayout()

        self.billing_btn = QPushButton("📊 查看账单")
        self.billing_btn.setStyleSheet("padding: 8px 20px;")
        self.billing_btn.clicked.connect(self.show_billing)

        self.help_btn = QPushButton("❓ 使用帮助")
        self.help_btn.setStyleSheet("padding: 8px 20px;")
        self.help_btn.clicked.connect(self.show_help)

        bottom_layout.addWidget(self.billing_btn)
        bottom_layout.addWidget(self.help_btn)
        bottom_layout.addStretch()

        layout.addLayout(bottom_layout)

    def create_no_container_widget(self):
        """创建无云电脑页面"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(30)

        label = QLabel("您还没有云电脑")
        label.setFont(QFont("Microsoft YaHei", 24))
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("color: #909399;")

        create_btn = QPushButton("➕ 创建云电脑")
        create_btn.setStyleSheet("""
            QPushButton {
                background-color: #409EFF;
                color: white;
                padding: 15px 50px;
                font-size: 18px;
                font-weight: bold;
                border-radius: 8px;
                border: none;
            }
            QPushButton:hover {
                background-color: #66b1ff;
            }
            QPushButton:pressed {
                background-color: #3a8ee6;
            }
        """)
        create_btn.clicked.connect(self.create_container)

        layout.addWidget(label)
        layout.addWidget(create_btn, alignment=Qt.AlignCenter)
        widget.setLayout(layout)

        return widget

    def create_container_widget(self):
        """创建云电脑信息页面"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(20)

        # 状态卡片
        self.status_card = QGroupBox("云电脑状态")
        self.status_card.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 14px;
                border: 1px solid #DCDFE6;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        status_layout = QGridLayout()
        status_layout.setSpacing(10)

        self.status_label = QLabel("状态: -")
        self.status_label.setFont(QFont("Microsoft YaHei", 14, QFont.Bold))
        status_layout.addWidget(self.status_label, 0, 0)

        self.config_label = QLabel("配置: -")
        status_layout.addWidget(self.config_label, 1, 0)

        self.runtime_label = QLabel("本次运行: -")
        status_layout.addWidget(self.runtime_label, 2, 0)

        self.cost_label = QLabel("本次消费: ¥0.00")
        self.cost_label.setStyleSheet("color: #F56C6C;")
        status_layout.addWidget(self.cost_label, 3, 0)

        self.remaining_label = QLabel("剩余可用: -")
        self.remaining_label.setStyleSheet("color: #67C23A; font-weight: bold;")
        status_layout.addWidget(self.remaining_label, 4, 0)

        self.status_card.setLayout(status_layout)
        layout.addWidget(self.status_card)

        # 连接信息
        self.conn_card = QGroupBox("连接信息")
        self.conn_card.setStyleSheet(self.status_card.styleSheet())
        conn_layout = QGridLayout()
        conn_layout.setSpacing(10)

        self.host_label = QLabel("地址: -")
        conn_layout.addWidget(self.host_label, 0, 0)

        self.user_label = QLabel("用户名: -")
        conn_layout.addWidget(self.user_label, 1, 0)

        self.pass_label = QLabel("密码: -")
        conn_layout.addWidget(self.pass_label, 2, 0)

        self.uhost_label = QLabel("UHost ID: -")
        conn_layout.addWidget(self.uhost_label, 3, 0)

        self.conn_card.setLayout(conn_layout)
        self.conn_card.setVisible(False)
        layout.addWidget(self.conn_card)

        # 操作按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)

        self.start_btn = QPushButton("▶ 启动")
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #67C23A;
                color: white;
                padding: 12px 25px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 4px;
                border: none;
            }
            QPushButton:hover {
                background-color: #85ce61;
            }
        """)
        self.start_btn.clicked.connect(self.start_container)

        self.stop_btn = QPushButton("⏹ 停止")
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #E6A23C;
                color: white;
                padding: 12px 25px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 4px;
                border: none;
            }
            QPushButton:hover {
                background-color: #ebb563;
            }
        """)
        self.stop_btn.clicked.connect(self.stop_container)
        self.stop_btn.setVisible(False)

        self.connect_btn = QPushButton("🖥️ 连接远程桌面")
        self.connect_btn.setStyleSheet("""
            QPushButton {
                background-color: #409EFF;
                color: white;
                padding: 12px 25px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 4px;
                border: none;
            }
            QPushButton:hover {
                background-color: #66b1ff;
            }
        """)
        self.connect_btn.clicked.connect(self.open_remote_desktop)
        self.connect_btn.setVisible(False)

        self.delete_btn = QPushButton("🗑️ 删除")
        self.delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #F56C6C;
                color: white;
                padding: 12px 25px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 4px;
                border: none;
            }
            QPushButton:hover {
                background-color: #f78989;
            }
        """)
        self.delete_btn.clicked.connect(self.delete_container)

        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.stop_btn)
        btn_layout.addWidget(self.connect_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.delete_btn)

        layout.addLayout(btn_layout)
        layout.addStretch()

        widget.setLayout(layout)
        return widget

    def set_user_info(self, user_info):
        """设置用户信息"""
        self.user_info = user_info
        self.company_label.setText(f"公司: {user_info.get('company_name', '-')}")
        self.balance_label.setText(f"余额: ¥{user_info.get('balance', 0):.2f}")
        self.refresh_container()

    def check_operation_cooldown(self, operation):
        """检查操作是否在冷却时间内

        Args:
            operation: 操作类型 ('stop' 或 'delete')

        Returns:
            tuple: (是否允许操作, 剩余冷却秒数)
        """
        last_time = self.last_operation_time.get(operation, 0)
        elapsed = time.time() - last_time
        if elapsed < self.operation_cooldown:
            remaining = int(self.operation_cooldown - elapsed)
            return False, remaining
        return True, 0

    def refresh_container(self):
        """刷新云电脑信息"""
        try:
            result = api_client.get_my_container()
            if result.is_ok():
                data = result.data or {}
                if data.get("has_container"):
                    self.container_info = data.get("container", {})
                    self.content_stack.setCurrentIndex(1)
                    self.update_container_display()

                    # 如果正在运行，启动定时器
                    if (
                        self.container_info
                        and self.container_info.get("status") == "running"
                    ):
                        if not self.status_timer.isActive():
                            self.status_timer.start(
                                self.config.auto_refresh_interval * 1000
                            )
                    else:
                        self.status_timer.stop()
                else:
                    self.content_stack.setCurrentIndex(0)
                    self.status_timer.stop()
                    self.container_info = None
        except Exception as e:
            logging.error(f"刷新云电脑信息失败: {e}")

    def update_container_display(self):
        """更新云电脑显示"""
        if not self.container_info:
            return

        container = self.container_info

        # 状态
        status_text = container.get("status", "unknown")
        status_map = {
            "running": "运行中 🟢",
            "stopped": "已停止 🔴",
            "creating": "创建中 🟡",
        }
        status_color = {
            "running": "#67C23A",
            "stopped": "#F56C6C",
            "creating": "#E6A23C",
        }
        color = status_color.get(status_text, "#909399")
        self.status_label.setText(f"状态: {status_map.get(status_text, status_text)}")
        self.status_label.setStyleSheet(f"color: {color};")

        # 配置
        self.config_label.setText(
            f"配置: {container.get('gpu_type', '-')}, "
            f"{container.get('cpu_cores', 0)}核CPU, "
            f"{container.get('memory_gb', 0)}GB内存, "
            f"{container.get('storage_gb', 0)}GB存储"
        )

        # 按钮状态
        is_running = status_text == "running"
        self.start_btn.setVisible(not is_running)
        self.stop_btn.setVisible(is_running)
        self.connect_btn.setVisible(is_running)
        self.conn_card.setVisible(is_running)

        if is_running:
            self.update_status()

    def update_status(self):
        """更新状态（定时调用）"""
        try:
            result = api_client.get_container_status()
            if result.is_ok():
                data = result.data or {}

                self.runtime_label.setText(
                    f"本次运行: {data.get('current_running_minutes', 0)} 分钟"
                )
                self.cost_label.setText(
                    f"本次消费: ¥{data.get('current_session_cost', 0):.2f}"
                )
                self.remaining_label.setText(
                    f"剩余可用: {data.get('remaining_time_formatted', '-')}"
                )

                # 更新余额
                self.balance_label.setText(f"余额: ¥{data.get('balance', 0):.2f}")

                # 更新连接信息
                conn_info = data.get("connection_info", {})
                if conn_info:
                    host = conn_info.get("host", "-")
                    port = conn_info.get("port", 3389)
                    username = conn_info.get("username", "-")
                    password = conn_info.get("password", "-")

                    self.host_label.setText(f"地址: {host}:{port}")
                    self.user_label.setText(f"用户名: {username}")
                    self.pass_label.setText(f"密码: {password}")

                    # 保存连接信息供后续使用
                    self.current_connection_info = {
                        "host": f"{host}:{port}",
                        "username": username,
                        "password": password,
                        "uhost_id": conn_info.get("uhost_id", ""),
                    }

                    # 显示UHost ID（如果有）
                    if conn_info.get("uhost_id"):
                        self.uhost_label.setText(
                            f"UHost ID: {conn_info.get('uhost_id')}"
                        )
                    else:
                        self.uhost_label.setVisible(False)

        except Exception as e:
            logging.error(f"更新状态失败: {e}")

    def create_container(self):
        """创建云电脑"""
        dialog = CreateContainerDialog(self)
        if dialog.exec() == QDialog.Accepted:
            name = dialog.name_input.text().strip() or "我的云电脑"

            result = api_client.create_container(instance_name=name)

            if result.is_ok():
                QMessageBox.information(self, "成功", "云电脑创建成功！")
                self.refresh_container()
            else:
                QMessageBox.critical(self, "失败", result.get_error_display())

    def start_container(self):
        """启动云电脑"""
        result = api_client.start_container()
        if result.is_ok():
            QMessageBox.information(self, "成功", "云电脑启动成功！")
            self.refresh_container()
        else:
            QMessageBox.critical(self, "失败", result.get_error_display())

    def stop_container(self):
        """停止云电脑"""
        # 检查冷却时间
        can_operate, remaining = self.check_operation_cooldown("stop")
        if not can_operate:
            QMessageBox.warning(
                self,
                "操作过于频繁",
                f"请等待 {remaining} 秒后再试",
            )
            return

        reply = QMessageBox.question(
            self,
            "确认停止",
            "确定要停止云电脑吗？\n停止后将无法继续工作，但数据会保留。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            # 记录操作时间
            self.last_operation_time["stop"] = time.time()
            result = api_client.stop_container()
            if result.is_ok():
                data = result.data or {}
                session = data.get("this_session", {})
                QMessageBox.information(
                    self,
                    "已停止",
                    f"云电脑已停止\n\n"
                    f"本次运行: {session.get('running_minutes', 0)} 分钟\n"
                    f"本次消费: ¥{session.get('cost', 0):.2f}",
                )
                self.status_timer.stop()
                self.refresh_container()
            else:
                QMessageBox.critical(self, "失败", result.get_error_display())

    def open_remote_desktop(self):
        """打开远程桌面 - 一键自动连接"""
        if not self.current_connection_info:
            QMessageBox.warning(self, "警告", "连接信息不可用，请稍后再试")
            return

        conn_info = self.current_connection_info
        host = conn_info.get("host", "")
        password = conn_info.get("password", "")
        uhost_id = conn_info.get("uhost_id", "")

        if not host or not password:
            QMessageBox.warning(self, "警告", "连接信息不完整")
            return

        # 确认连接
        reply = QMessageBox.question(
            self,
            "连接远程桌面",
            f"即将连接到: {host}\n\n"
            f"系统将自动: \n"
            f"1. 保存凭据到Windows凭据管理器\n"
            f"2. 启动远程桌面客户端\n"
            f"3. 自动点击连接按钮\n\n"
            f"是否继续？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )

        if reply != QMessageBox.Yes:
            return

        # 执行远程桌面连接
        try:
            from utils.rdp_helper import RDPHelper

            # 检查是否为Windows系统
            if not RDPHelper.is_windows():
                # 非Windows系统，显示连接说明
                instructions = get_rdp_instructions(
                    host=host,
                    username=conn_info.get("username", "administrator"),
                    password=password,
                )

                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("连接说明")
                msg_box.setText(instructions)
                msg_box.setIcon(QMessageBox.Information)
                msg_box.exec()
                return

            # Windows系统：自动连接
            success, message = start_remote_desktop(
                host=host,
                password=password,
                uhost_id=uhost_id,
                auto_connect=self.config.rdp_auto_connect,
            )

            if not success:
                # 连接失败，显示手动连接信息
                QMessageBox.warning(
                    self,
                    "连接失败",
                    f"{message}\n\n"
                    f"请手动连接:\n"
                    f"主机: {host}\n"
                    f"用户名: {conn_info.get('username', 'administrator')}\n"
                    f"密码: {password}",
                )

        except Exception as e:
            logging.error(f"启动远程桌面失败: {e}")
            QMessageBox.critical(
                self,
                "错误",
                f"启动远程桌面时发生错误:\n{str(e)}\n\n"
                f"请手动连接:\n"
                f"主机: {host}\n"
                f"用户名: {conn_info.get('username', 'administrator')}\n"
                f"密码: {password}",
            )

    def delete_container(self):
        """删除云电脑"""
        # 检查实例是否在运行
        if self.container_info:
            status = self.container_info.get("status", "")
            if status == "running":
                QMessageBox.warning(
                    self,
                    "无法删除",
                    "实例正在运行中，请先停止实例后再删除。",
                )
                return

        # 检查冷却时间
        can_operate, remaining = self.check_operation_cooldown("delete")
        if not can_operate:
            QMessageBox.warning(
                self,
                "操作过于频繁",
                f"请等待 {remaining} 秒后再试",
            )
            return

        reply = QMessageBox.warning(
            self,
            "⚠️ 警告",
            "删除云电脑将清除所有数据且不可恢复！\n\n确定要删除吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            # 记录操作时间
            self.last_operation_time["delete"] = time.time()
            result = api_client.delete_container()
            if result.is_ok():
                QMessageBox.information(self, "成功", "云电脑已删除")
                self.status_timer.stop()
                self.current_connection_info = None
                self.refresh_container()
            else:
                QMessageBox.critical(self, "失败", result.get_error_display())

    def show_billing(self):
        """显示账单"""
        result = api_client.get_billing_statistics()
        if result.is_ok():
            data = result.data or {}
            msg = (
                f"💰 账单统计\n\n"
                f"━━━━━━━━━━━━━━━━\n"
                f"当前余额: ¥{data.get('balance', 0):.2f}\n"
                f"今日消费: ¥{data.get('today_cost', 0):.2f}\n"
                f"本月消费: ¥{data.get('this_month_cost', 0):.2f}\n"
                f"累计消费: ¥{data.get('total_cost', 0):.2f}\n"
                f"累计运行: {data.get('total_running_minutes', 0)} 分钟\n"
                f"━━━━━━━━━━━━━━━━"
            )
            QMessageBox.information(self, "账单统计", msg)
        else:
            QMessageBox.warning(self, "错误", result.get_error_display())

    def show_help(self):
        """显示帮助"""
        help_text = """
📖 使用说明:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1️⃣  首次使用需要创建云电脑

2️⃣  启动云电脑需要余额 >= 5分钟费用

3️⃣  云电脑按分钟计费，余额不足会自动停止

4️⃣  停止后实例数据会保留，可再次启动

5️⃣  删除实例后才能创建新的云电脑

6️⃣  远程桌面连接:
   • Windows: 点击"连接远程桌面"自动连接
   • 其他系统: 使用RDP客户端手动连接
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔧 技术支持: 请联系管理员
        """

        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("使用帮助")
        msg_box.setText(help_text)
        msg_box.setIcon(QMessageBox.Information)
        msg_box.exec()

    def logout(self):
        """退出登录"""
        self.status_timer.stop()
        api_client.clear_token()
        self.close()

        # 重新显示登录窗口
        dialog = LoginDialog()
        if dialog.exec() == QDialog.Accepted:
            main_window = MainWindow()
            main_window.set_user_info(dialog.user_info)
            main_window.show()


def main():
    """主函数"""
    # 配置日志
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("启动云电脑客户端")

    # 创建应用
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # 设置应用字体
    font = QFont("Microsoft YaHei", 10)
    app.setFont(font)

    # 显示登录窗口
    login_dialog = LoginDialog()
    if login_dialog.exec() == QDialog.Accepted:
        # 登录成功，显示主窗口
        logger.info("登录成功，显示主窗口")
        main_window = MainWindow()
        main_window.set_user_info(login_dialog.user_info)
        main_window.show()
        sys.exit(app.exec())
    else:
        logger.info("用户取消登录")


if __name__ == "__main__":
    main()
