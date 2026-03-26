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
    QButtonGroup,
    QSpinBox,
    QComboBox,
    QDialog,
    QRadioButton,
    QTextEdit,
    QTabWidget,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QClipboard

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
        phone_label = QLabel("手机号-账号:")
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
        self.config_options = []
        self.config_option_group = QButtonGroup(self)
        self.config_option_group.setExclusive(True)
        self.setWindowTitle("创建云电脑")
        self.setFixedSize(560, 460)
        self.setup_ui()
        self.load_config_options()

    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 20, 30, 20)
        layout.setSpacing(16)

        # 套餐选择
        config_group = QGroupBox("选择套餐")
        config_group.setStyleSheet(
            """
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
"""
        )
        self.config_layout = QVBoxLayout()
        self.config_layout.setSpacing(8)
        self.config_status_label = QLabel("正在加载套餐信息...")
        self.config_status_label.setStyleSheet("color: #909399;")
        self.config_layout.addWidget(self.config_status_label)
        config_group.setLayout(self.config_layout)
        layout.addWidget(config_group)

        self.balance_tip_label = QLabel("创建/启动最低余额: --")
        self.balance_tip_label.setStyleSheet("color: #E6A23C; font-size: 12px;")
        layout.addWidget(self.balance_tip_label)

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
"""
        )
        self.create_btn.clicked.connect(self.accept)
        self.create_btn.setEnabled(False)

        cancel_btn = QPushButton("取 消")
        cancel_btn.setStyleSheet(
            """
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
"""
        )
        cancel_btn.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(self.create_btn)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addStretch()

        layout.addLayout(btn_layout)
        layout.addStretch()

        self.setLayout(layout)

    def load_config_options(self):
        """加载用户可选套餐"""
        for button in self.config_option_group.buttons():
            self.config_option_group.removeButton(button)

        while self.config_layout.count():
            item = self.config_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        result = api_client.get_container_config_options()
        if not result.is_ok():
            error_label = QLabel(f"套餐信息加载失败：{result.message or '请稍后重试'}")
            error_label.setStyleSheet("color: #F56C6C;")
            error_label.setWordWrap(True)
            self.config_layout.addWidget(error_label)
            self.balance_tip_label.setText("创建/启动最低余额: --")
            self.create_btn.setEnabled(False)
            return

        data = result.data or {}
        self.config_options = data.get("config_options", [])
        min_balance = float(data.get("min_balance_to_start", 0))
        self.balance_tip_label.setText(
            f"创建/启动最低余额: ¥{min_balance:.2f}"
        )

        if not self.config_options:
            empty_label = QLabel("当前没有可用套餐，请联系管理员。")
            empty_label.setStyleSheet("color: #F56C6C;")
            self.config_layout.addWidget(empty_label)
            self.create_btn.setEnabled(False)
            return

        for index, option in enumerate(self.config_options):
            radio = QRadioButton(self.format_option_text(option))
            radio.config_code = option.get("config_code")
            radio.setStyleSheet(
                """
QRadioButton {
    padding: 8px 10px;
    border: 1px solid #EBEEF5;
    border-radius: 6px;
    color: #303133;
}
QRadioButton:hover {
    background-color: #F5F7FA;
}
"""
            )
            radio.setChecked(index == 0)
            self.config_option_group.addButton(radio, index)
            self.config_layout.addWidget(radio)

        self.create_btn.setEnabled(True)

    @staticmethod
    def format_option_text(option):
        """格式化套餐显示文本"""
        price = float(option.get("price_per_minute", 0))
        return (
            f"{option.get('config_name', '-')}"
            f" | {option.get('gpu_type', '-')}"
            f" | {option.get('cpu_cores', 0)}核CPU"
            f" | {option.get('memory_gb', 0)}GB内存"
            f" | {option.get('storage_gb', 0)}GB存储"
            f" | ¥{price:.2f}/分钟"
        )

    def get_selected_config_code(self):
        """获取当前选中的套餐编码"""
        checked_button = self.config_option_group.checkedButton()
        if not checked_button:
            return None
        return getattr(checked_button, "config_code", None)


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

        # 停止并删除的重试机制
        self.delete_retry_timer = QTimer()
        self.delete_retry_timer.timeout.connect(self.try_delete_with_retry)
        self.delete_attempts = 0
        self.max_delete_attempts = 6  # 最多6次尝试，每次间隔10秒，共60秒

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

        # 连接信息 - 只占一半宽度
        conn_wrapper = QWidget()
        conn_wrapper.setMaximumWidth(500)
        conn_layout_main = QVBoxLayout()
        conn_layout_main.setContentsMargins(0, 0, 0, 0)

        self.conn_card = QGroupBox("连接信息")
        self.conn_card.setStyleSheet(self.status_card.styleSheet())
        conn_layout = QGridLayout()
        conn_layout.setSpacing(10)

        # 地址
        host_layout = QHBoxLayout()
        self.host_label = QLabel("地址: -")
        self.host_label.setMinimumWidth(250)
        self.copy_host_btn = QPushButton("复制")
        self.copy_host_btn.setStyleSheet("padding: 4px 10px;")
        self.copy_host_btn.clicked.connect(lambda: self.copy_to_clipboard("host"))
        host_layout.addWidget(self.host_label)
        host_layout.addWidget(self.copy_host_btn)
        conn_layout.addLayout(host_layout, 0, 0)

        # 用户名
        user_layout = QHBoxLayout()
        self.user_label = QLabel("用户名: -")
        self.user_label.setMinimumWidth(250)
        self.copy_user_btn = QPushButton("复制")
        self.copy_user_btn.setStyleSheet("padding: 4px 10px;")
        self.copy_user_btn.clicked.connect(lambda: self.copy_to_clipboard("user"))
        user_layout.addWidget(self.user_label)
        user_layout.addWidget(self.copy_user_btn)
        conn_layout.addLayout(user_layout, 1, 0)

        # 密码
        pass_layout = QHBoxLayout()
        self.pass_label = QLabel("密码: -")
        self.pass_label.setMinimumWidth(250)
        self.copy_pass_btn = QPushButton("复制")
        self.copy_pass_btn.setStyleSheet("padding: 4px 10px;")
        self.copy_pass_btn.clicked.connect(lambda: self.copy_to_clipboard("pass"))
        pass_layout.addWidget(self.pass_label)
        pass_layout.addWidget(self.copy_pass_btn)
        conn_layout.addLayout(pass_layout, 2, 0)

        # UHost ID
        uhost_layout = QHBoxLayout()
        self.uhost_label = QLabel("UHost ID: -")
        self.uhost_label.setMinimumWidth(250)
        self.copy_uhost_btn = QPushButton("复制")
        self.copy_uhost_btn.setStyleSheet("padding: 4px 10px;")
        self.copy_uhost_btn.clicked.connect(lambda: self.copy_to_clipboard("uhost"))
        uhost_layout.addWidget(self.uhost_label)
        uhost_layout.addWidget(self.copy_uhost_btn)
        conn_layout.addLayout(uhost_layout, 3, 0)

        self.conn_card.setLayout(conn_layout)
        self.conn_card.setVisible(False)

        # 将连接信息卡片添加到包装器中
        conn_layout_main.addWidget(self.conn_card)
        conn_wrapper.setLayout(conn_layout_main)
        layout.addWidget(conn_wrapper)

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

        self.stop_and_delete_btn = QPushButton("⏹ 停止并删除")
        self.stop_and_delete_btn.setStyleSheet("""
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
        self.stop_and_delete_btn.clicked.connect(self.stop_and_delete_container)
        self.stop_and_delete_btn.setVisible(False)

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

        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.stop_and_delete_btn)
        btn_layout.addWidget(self.connect_btn)
        btn_layout.addStretch()

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
        config_name = container.get("config_name")
        if config_name:
            self.config_label.setText(
                f"套餐: {config_name} | "
                f"{container.get('gpu_type', '-')}, "
                f"{container.get('cpu_cores', 0)}核CPU, "
                f"{container.get('memory_gb', 0)}GB内存, "
                f"{container.get('storage_gb', 0)}GB存储"
            )
        else:
            self.config_label.setText(
                f"配置: {container.get('gpu_type', '-')}, "
                f"{container.get('cpu_cores', 0)}核CPU, "
                f"{container.get('memory_gb', 0)}GB内存, "
                f"{container.get('storage_gb', 0)}GB存储"
            )

        # 按钮状态
        is_running = status_text == "running"
        self.start_btn.setVisible(not is_running)
        self.stop_and_delete_btn.setVisible(is_running)
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

                running_minutes = max(0, data.get("current_running_minutes", 0))
                session_cost = max(0.0, data.get("current_session_cost", 0))
                balance = max(0.0, data.get("balance", 0))

                self.runtime_label.setText(f"本次运行: {running_minutes} 分钟")
                self.cost_label.setText(f"本次消费: ¥{session_cost:.2f}")
                self.remaining_label.setText(
                    f"剩余可用: {data.get('remaining_time_formatted', '-')}"
                )

                # 更新余额
                self.balance_label.setText(f"余额: ¥{balance:.2f}")

                # 更新连接信息
                conn_info = data.get("connection_info", {})
                if conn_info:
                    host = conn_info.get("host", "-")
                    port = conn_info.get("port", 3389)
                    username = conn_info.get("username", "-")
                    password = conn_info.get("password", "-")

                    self.host_label.setText(f"地址: {host}:{port}")
                    self.user_label.setText(f"用户名: Administrator")
                    self.pass_label.setText(f"密码: {password}")

                    # 保存连接信息供后续使用
                    self.current_connection_info = {
                        "host": f"{host}:{port}",
                        "username": "Administrator",
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
            config_code = dialog.get_selected_config_code()

            if not config_code:
                QMessageBox.warning(self, "提示", "请选择一个套餐后再创建")
                return

            result = api_client.create_container(
                instance_name=name,
                config_code=config_code,
            )

            if result.is_ok():
                QMessageBox.information(self, "成功", "云电脑创建成功！")
                self.refresh_container()
                return

            error_detail = (
                result.error_detail if isinstance(result.error_detail, dict) else {}
            )
            if result.code == 409 and error_detail.get("require_confirm"):
                existing_container = error_detail.get("existing_container", {})
                existing_name = existing_container.get("instance_name", "旧实例")
                existing_status = existing_container.get("status", "-")
                existing_gpu = existing_container.get("gpu_type", "-")
                reply = QMessageBox.question(
                    self,
                    "确认替换实例",
                    "您已有一个云电脑实例。\n"
                    f"当前实例: {existing_name}\n"
                    f"状态: {existing_status}\n"
                    f"GPU: {existing_gpu}\n\n"
                    "是否删除旧实例并按所选套餐创建新实例？",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No,
                )
                if reply == QMessageBox.Yes:
                    force_result = api_client.create_container(
                        instance_name=name,
                        config_code=config_code,
                        force=True,
                    )
                    if force_result.is_ok():
                        QMessageBox.information(self, "成功", "云电脑创建成功！")
                        self.refresh_container()
                    else:
                        QMessageBox.critical(
                            self,
                            "失败",
                            force_result.get_error_display(),
                        )
                return

            QMessageBox.critical(self, "失败", result.get_error_display())

    def start_container(self):
        """启动云电脑"""
        result = api_client.start_container()
        if result.is_ok():
            QMessageBox.information(self, "成功", "云电脑启动成功！")
            self.refresh_container()
        else:
            QMessageBox.critical(self, "失败", result.get_error_display())

    def stop_and_delete_container(self):
        """停止云电脑并在关机完成后自动删除"""
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
            "确认停止并删除",
            "确定要停止云电脑并在关机完成后自动删除吗？\n"
            "⚠️ 删除后数据将不可恢复！\n\n"
            "系统将在关机完成后自动删除实例（最多等待60秒）。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            # 记录操作时间
            self.last_operation_time["stop"] = time.time()

            # 发送停止指令
            result = api_client.stop_container()
            if not result.is_ok():
                QMessageBox.critical(self, "停止失败", result.get_error_display())
                return

            # 停止状态更新定时器
            self.status_timer.stop()

            # 创建倒计时对话框
            self.processing_dialog = QDialog(self)
            self.processing_dialog.setWindowTitle("正在处理")
            self.processing_dialog.setFixedSize(350, 150)
            self.processing_dialog.setModal(True)

            dialog_layout = QVBoxLayout()
            dialog_layout.setSpacing(15)
            dialog_layout.setContentsMargins(20, 20, 20, 20)

            # 提示文本
            self.processing_label = QLabel(
                "实例正在关机，关机完成后将自动删除...\n请勿关闭客户端。"
            )
            self.processing_label.setAlignment(Qt.AlignCenter)
            dialog_layout.addWidget(self.processing_label)

            # 倒计时显示
            self.countdown_label = QLabel("倒计时: 60 秒")
            self.countdown_label.setAlignment(Qt.AlignCenter)
            self.countdown_label.setStyleSheet(
                "font-size: 18px; font-weight: bold; color: #F56C6C;"
            )
            dialog_layout.addWidget(self.countdown_label)

            self.processing_dialog.setLayout(dialog_layout)
            self.processing_dialog.show()

            # 启动倒计时定时器（每秒更新一次）
            self.countdown_value = 60
            self.countdown_timer = QTimer()
            self.countdown_timer.timeout.connect(self.update_countdown)
            self.countdown_timer.start(1000)

            # 初始化重试机制
            self.delete_attempts = 0
            # 10秒后开始首次尝试删除
            self.delete_retry_timer.start(10000)

    def update_countdown(self):
        """更新倒计时显示"""
        self.countdown_value -= 1
        if hasattr(self, "countdown_label"):
            self.countdown_label.setText(f"倒计时: {self.countdown_value} 秒")

    def try_delete_with_retry(self):
        """尝试删除实例，失败则重试"""
        self.delete_attempts += 1

        result = api_client.delete_container()

        if result.is_ok():
            # 删除成功
            self.delete_retry_timer.stop()
            self.countdown_timer.stop()
            if hasattr(self, "processing_dialog"):
                self.processing_dialog.close()
            QMessageBox.information(self, "完成", "云电脑已停止并自动删除成功")
            self.current_connection_info = None
            self.refresh_container()
            return

        # 删除失败，检查是否达到最大重试次数
        if self.delete_attempts >= self.max_delete_attempts:
            # 超过60秒，停止重试
            self.delete_retry_timer.stop()
            self.countdown_timer.stop()
            if hasattr(self, "processing_dialog"):
                self.processing_dialog.close()
            QMessageBox.warning(
                self,
                "删除超时",
                "等待已超过60秒，实例可能仍在关机中。\n请稍后手动刷新并删除实例。",
            )
            self.refresh_container()
        # 否则继续等待，timer会在10秒后再次触发

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
                    username=conn_info.get("username", "Administrator"),
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
                    f"用户名: {conn_info.get('username', 'Administrator')}\n"
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
                f"用户名: {conn_info.get('username', 'Administrator')}\n"
                f"密码: {password}",
            )

    def show_billing(self):
        """显示账单"""
        result = api_client.get_billing_statistics()
        if result.is_ok():
            data = result.data or {}
            balance = max(0.0, data.get("balance", 0))
            today_cost = max(0.0, data.get("today_cost", 0))
            this_month_cost = max(0.0, data.get("this_month_cost", 0))
            total_cost = max(0.0, data.get("total_cost", 0))
            total_running_minutes = max(0, data.get("total_running_minutes", 0))
            msg = (
                f"💰 账单统计\n\n"
                f"━━━━━━━━━━━━━━━━\n"
                f"当前余额: ¥{balance:.2f}\n"
                f"今日消费: ¥{today_cost:.2f}\n"
                f"本月消费: ¥{this_month_cost:.2f}\n"
                f"累计消费: ¥{total_cost:.2f}\n"
                f"累计运行: {total_running_minutes} 分钟\n"
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

4️⃣  点击"停止并删除"停止实例并自动删除
   ⚠️ 停止后数据将被删除，不可恢复！

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

    def copy_to_clipboard(self, data_type):
        """复制数据到剪贴板

        Args:
            data_type: 数据类型 ('host', 'user', 'pass', 'uhost')
        """
        clipboard = QApplication.clipboard()

        if data_type == "host":
            if self.current_connection_info:
                host = self.current_connection_info.get("host", "")
                clipboard.setText(host)
                QMessageBox.information(self, "复制成功", f"地址已复制到剪贴板")
        elif data_type == "user":
            clipboard.setText("Administrator")
            QMessageBox.information(self, "复制成功", f"用户名已复制到剪贴板")
        elif data_type == "pass":
            if self.current_connection_info:
                password = self.current_connection_info.get("password", "")
                clipboard.setText(password)
                QMessageBox.information(self, "复制成功", f"密码已复制到剪贴板")
        elif data_type == "uhost":
            if self.current_connection_info:
                uhost_id = self.current_connection_info.get("uhost_id", "")
                clipboard.setText(uhost_id)
                QMessageBox.information(self, "复制成功", f"UHost ID已复制到剪贴板")

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
