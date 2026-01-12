"""
GitHub Uploader Pro - 登录面板
GitHub OAuth登录组件
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QFrame, QFileDialog, QDialog, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot, QThread, QTimer
from PyQt6.QtGui import QPixmap, QFont
import httpx
from loguru import logger

from .glass_widgets import GlassPanel, GlassButton, SectionTitle
from ..theme_manager import theme_manager
from core.github_auth import github_auth, GitHubCredential, AuthResult


class DeviceCodeDialog(QDialog):
    """
    设备码对话框
    显示用户码并等待授权
    """
    
    auth_completed = pyqtSignal(AuthResult)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        theme_manager.theme_changed.connect(self._setup_ui)
    
    def _setup_ui(self):
        """设置UI"""
        c = theme_manager.colors
        
        self.setWindowTitle("GitHub 登录")
        self.setFixedSize(400, 300)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {c['bg_primary']};
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # 标题
        title = QLabel("🔐 GitHub 授权")
        title.setStyleSheet(f"""
            font-size: 20px;
            font-weight: bold;
            color: {c['text_primary']};
        """)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # 说明
        desc = QLabel("请在浏览器中输入以下代码完成授权：")
        desc.setStyleSheet(f"color: {c['text_secondary']};")
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(desc)
        
        # 用户码
        self._code_label = QLabel("--------")
        self._code_label.setStyleSheet(f"""
            font-size: 32px;
            font-weight: bold;
            font-family: 'Consolas', 'Courier New', monospace;
            color: {c['accent']};
            background-color: {c['bg_secondary']};
            border: 2px solid {c['accent']};
            border-radius: 12px;
            padding: 20px;
        """)
        self._code_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._code_label)
        
        # 链接提示
        self._link_label = QLabel("正在打开浏览器...")
        self._link_label.setStyleSheet(f"color: {c['text_muted']}; font-size: 12px;")
        self._link_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._link_label)
        
        # 状态
        self._status_label = QLabel("⏳ 等待授权...")
        self._status_label.setStyleSheet(f"color: {c['info']};")
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._status_label)
        
        # 取消按钮
        cancel_btn = QPushButton("取消")
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {c['bg_tertiary']};
                color: {c['text_primary']};
                border: none;
                border-radius: 8px;
                padding: 10px 30px;
            }}
            QPushButton:hover {{
                background-color: {c['error']};
                color: white;
            }}
        """)
        cancel_btn.clicked.connect(self._on_cancel)
        layout.addWidget(cancel_btn, alignment=Qt.AlignmentFlag.AlignCenter)
    
    def show_code(self, user_code: str, verification_uri: str):
        """显示用户码"""
        self._code_label.setText(user_code)
        self._link_label.setText(f"请访问: {verification_uri}")
    
    def show_success(self, username: str):
        """显示成功"""
        c = theme_manager.colors
        self._status_label.setText(f"✅ 授权成功！欢迎，{username}")
        self._status_label.setStyleSheet(f"color: {c['success']};")
        
        # 1秒后关闭
        QTimer.singleShot(1000, self.accept)
    
    def show_error(self, error: str):
        """显示错误"""
        c = theme_manager.colors
        self._status_label.setText(f"❌ {error}")
        self._status_label.setStyleSheet(f"color: {c['error']};")
    
    def _on_cancel(self):
        """取消授权"""
        github_auth.cancel_auth()
        self.reject()


class AuthCheckThread(QThread):
    """登录状态检查工作线程"""
    finished = pyqtSignal(object)

    def run(self):
        credential = github_auth.get_current_user()
        self.finished.emit(credential)


class LoginPanel(GlassPanel):
    """
    登录面板
    显示登录状态和用户信息
    """
    
    login_state_changed = pyqtSignal(bool)  # True = 已登录
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._credential: GitHubCredential = None
        self._check_thread = None
        self._setup_ui()
        # 响应主题变更 (V4.2 Reactive)
        theme_manager.theme_changed.connect(self._setup_ui)
        
        # V4.5: 错峰加载，避免与 MainWindow 初始化竞争
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(500, self._check_login_state)
    
    def _setup_ui(self):
        """设置UI (V4.5.1 布局自愈)"""
        c = theme_manager.colors
        
        if not self.layout():
            layout = QVBoxLayout(self)
            self._main_layout = layout
        else:
            layout = self._main_layout
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
                    
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 标题
        title = SectionTitle("👤", "GitHub 账户")
        layout.addWidget(title)
        
        # 未登录视图
        self._login_widget = QWidget()
        login_layout = QVBoxLayout(self._login_widget)
        login_layout.setContentsMargins(0, 0, 0, 0)
        
        login_desc = QLabel("请先使用命令行运行 'gh auth login' 登录 GitHub")
        login_desc.setStyleSheet(f"color: {c['text_secondary']};")
        login_layout.addWidget(login_desc)
        
        login_btn = GlassButton("🔗 使用 GitHub CLI 登录", primary=True)
        login_btn.clicked.connect(self._start_login)
        login_layout.addWidget(login_btn)
        
        layout.addWidget(self._login_widget)
        
        # 已登录视图
        self._user_widget = QWidget()
        self._user_widget.setVisible(False)
        user_layout = QHBoxLayout(self._user_widget)
        user_layout.setContentsMargins(0, 0, 0, 0)
        user_layout.setSpacing(15)
        
        # 头像
        self._avatar_label = QLabel()
        self._avatar_label.setFixedSize(50, 50)
        self._avatar_label.setStyleSheet(f"""
            border-radius: 25px;
            background-color: {c['bg_tertiary']};
        """)
        user_layout.addWidget(self._avatar_label)
        
        # 用户信息
        info_layout = QVBoxLayout()
        
        self._username_label = QLabel("用户名")
        self._username_label.setStyleSheet(f"""
            font-size: 16px;
            font-weight: bold;
            color: {c['text_primary']};
        """)
        info_layout.addWidget(self._username_label)
        
        self._status_label = QLabel("✅ 已登录")
        self._status_label.setStyleSheet(f"color: {c['success']}; font-size: 12px;")
        info_layout.addWidget(self._status_label)
        
        user_layout.addLayout(info_layout)
        user_layout.addStretch()
        
        # 登出按钮
        logout_btn = QPushButton("登出")
        logout_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {c['text_muted']};
                border: 1px solid {c['border']};
                border-radius: 6px;
                padding: 8px 16px;
            }}
            QPushButton:hover {{
                background-color: {c['error']};
                color: white;
                border-color: {c['error']};
            }}
        """)
        logout_btn.clicked.connect(self._logout)
        user_layout.addWidget(logout_btn)
        
        layout.addWidget(self._user_widget)
    
    def _check_login_state(self):
        """异步检查登录状态 v4.2.4"""
        if self._check_thread and self._check_thread.isRunning():
            return
            
        self._login_widget.setEnabled(False)
        self._user_widget.hide()
        
        self._check_thread = AuthCheckThread()
        self._check_thread.finished.connect(self._on_auth_checked)
        self._check_thread.start()

    def _on_auth_checked(self, credential):
        """状态检查完成回调"""
        self._login_widget.setEnabled(True)
        if credential:
            self._show_logged_in(credential)
            self.login_state_changed.emit(True)
        else:
            self._show_logged_out()
            self.login_state_changed.emit(False)
    
    def _start_login(self):
        """开始登录流程 - 使用 GitHub CLI"""
        def on_complete(result: AuthResult):
            if result.success and result.credential:
                self._show_logged_in(result.credential)
            elif result.error == "NOT_LOGGED_IN":
                # GitHub CLI 未登录，自动打开终端执行登录命令
                self._open_terminal_for_login()
            else:
                # 其他错误
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(
                    self.window(),
                    "登录失败",
                    result.error or "认证失败，请重试"
                )
        
        # 尝试 GitHub CLI 认证
        github_auth.start_gh_cli_auth(on_complete=on_complete)
    
    def _open_terminal_for_login(self):
        """打开终端执行 GitHub CLI 登录命令"""
        import os
        import subprocess
        
        try:
            # Windows 下使用 cmd 执行 gh auth login
            cmd = 'gh auth login'
            
            if os.name == 'nt':  # Windows
                # 使用 cmd /k 保持窗口打开
                subprocess.Popen(
                    ['cmd', '/k', cmd],
                    creationflags=subprocess.CREATE_NEW_CONSOLE
                )
            else:  # Linux/macOS
                subprocess.Popen(
                    ['gnome-terminal', '--', 'bash', '-c', f'{cmd}; exec bash'],
                    shell=False
                )
            
            # 显示提示对话框
            from PyQt6.QtWidgets import QMessageBox
            msg_box = QMessageBox(self.window())
            msg_box.setWindowTitle("等待登录")
            msg_box.setText("请在打开的终端窗口中完成 GitHub 登录授权")
            msg_box.setInformativeText("登录完成后，点击下方按钮继续")
            msg_box.setIcon(QMessageBox.Icon.Information)
            
            # 添加"重新检测"按钮
            retry_btn = msg_box.addButton("重新检测登录状态", QMessageBox.ButtonRole.ActionRole)
            cancel_btn = msg_box.addButton(QMessageBox.StandardButton.Cancel)
            
            msg_box.exec()
            
            # 如果用户点击了"重新检测"
            if msg_box.clickedButton() == retry_btn:
                self._start_login()
            
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(
                self.window(),
                "错误",
                f"无法打开终端: {str(e)}\n\n"
                "请手动在命令行中运行: gh auth login"
            )
    
    def _show_logged_in(self, credential: GitHubCredential):
        """显示已登录状态"""
        self._credential = credential
        self._login_widget.setVisible(False)
        self._user_widget.setVisible(True)
        
        self._username_label.setText(credential.username or "GitHub User")
        
        # 加载头像
        if credential.avatar_url:
            self._load_avatar(credential.avatar_url)
        
        self.login_state_changed.emit(True)
        logger.info(f"用户已登录: {credential.username}")
    
    def _show_logged_out(self):
        """显示未登录状态"""
        self._credential = None
        self._login_widget.setVisible(True)
        self._user_widget.setVisible(False)
        
        self.login_state_changed.emit(False)
    
    def _load_avatar(self, url: str):
        """加载用户头像"""
        try:
            response = httpx.get(url, timeout=10)
            if response.status_code == 200:
                pixmap = QPixmap()
                pixmap.loadFromData(response.content)
                
                # 缩放并设置圆形遮罩
                scaled = pixmap.scaled(
                    50, 50,
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation
                )
                self._avatar_label.setPixmap(scaled)
        except Exception as e:
            logger.warning(f"加载头像失败: {e}")
    
    def _logout(self):
        """登出"""
        github_auth.logout()
        self._show_logged_out()
        logger.info("用户已登出")
    
    @property
    def is_logged_in(self) -> bool:
        """是否已登录"""
        return self._credential is not None
    
    @property
    def credential(self) -> GitHubCredential:
        """获取当前凭证"""
        return self._credential
