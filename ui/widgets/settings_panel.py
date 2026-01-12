"""
GitHub Uploader Pro - Settings Panel
配置设置面板，支持 AI 参数、主题和语言设置
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QFrame, QScrollArea, QCheckBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from loguru import logger

from .glass_widgets import GlassPanel, SectionTitle, Divider
from ..theme_manager import theme_manager
from utils.config import config


class SettingsPanel(GlassPanel):
    """
    设置面板
    """
    settings_changed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        theme_manager.theme_changed.connect(self._setup_ui)
        
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
                if item.widget(): item.widget().deleteLater()
                    
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(20)
        
        layout.addWidget(SectionTitle("⚙️", "系统设置"))
        
        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent; border: none;")
        
        content = QWidget()
        scroll_layout = QVBoxLayout(content)
        scroll_layout.setSpacing(15)
        
        # --- AI 助手配置 ---
        scroll_layout.addWidget(QLabel("🤖 AI Agent 配置"))
        
        self._ai_url = self._create_input("API URL", config.get("ai_url"))
        scroll_layout.addLayout(self._ai_url['layout'])
        
        self._ai_key = self._create_input("API Key", config.get("ai_key"), password=True)
        scroll_layout.addLayout(self._ai_key['layout'])
        
        self._ai_model = self._create_input("模型 (Model)", config.get("ai_model"))
        scroll_layout.addLayout(self._ai_model['layout'])
        
        scroll_layout.addWidget(Divider())
        
        # --- 基本设置 ---
        scroll_layout.addWidget(QLabel("🖥️ 界面设置"))
        
        # 主题选择
        theme_layout = QHBoxLayout()
        theme_layout.addWidget(QLabel("颜色主题:"))
        self._theme_combo = QComboBox()
        self._theme_combo.addItems(["深色 (Dark)", "浅色 (Light)"])
        self._theme_combo.setCurrentText("深色 (Dark)" if config.get("theme") == "dark" else "浅色 (Light)")
        theme_layout.addWidget(self._theme_combo)
        scroll_layout.addLayout(theme_layout)
        
        # 提交信息
        self._commit_msg = self._create_input("默认提交信息", config.get("default_commit_message"))
        scroll_layout.addLayout(self._commit_msg['layout'])
        
        # 自动纠错说明
        hint = QLabel("💡 提示: API URL 建议填写完整路径如 https://api.openai.com/v1")
        hint.setStyleSheet(f"color: {c['text_muted']}; font-size: 11px; font-style: italic;")
        scroll_layout.addWidget(hint)
        
        scroll_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)
        
        # 保存按钮
        self._save_btn = QPushButton("保存配置")
        self._save_btn.setFixedHeight(45)
        self._save_btn.setStyleSheet(f"""
            QPushButton {{
                background: {c['accent']};
                color: white;
                border: none;
                border-radius: 8px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background: {c['accent_hover']}; }}
        """)
        self._save_btn.clicked.connect(self._save_settings)
        layout.addWidget(self._save_btn)

    def _create_input(self, label, value, password=False):
        c = theme_manager.colors
        layout = QVBoxLayout()
        layout.setSpacing(5)
        
        lbl = QLabel(label)
        lbl.setStyleSheet(f"color: {c['text_secondary']}; font-size: 12px;")
        layout.addWidget(lbl)
        
        edit = QLineEdit()
        edit.setText(str(value or ""))
        if password:
            edit.setEchoMode(QLineEdit.EchoMode.Password)
        edit.setStyleSheet(f"""
            QLineEdit {{
                background: {c['bg_primary']};
                border: 1px solid {c['border']};
                border-radius: 6px;
                padding: 8px;
                color: {c['text_primary']};
            }}
        """)
        layout.addWidget(edit)
        
        return {"layout": layout, "edit": edit}

    def _save_settings(self):
        """保存配置 v4.3 [Persistence Fix]"""
        url = self._ai_url['edit'].text().strip()
        # 自动补全 /v1 后缀 (如果常见域名且缺失)
        if "api.openai.com" in url.lower() and not url.endswith("/v1") and not url.endswith("/v1/"):
            url = url.rstrip("/") + "/v1"
            self._ai_url['edit'].setText(url)

        updates = {
            "ai_url": url,
            "ai_key": self._ai_key['edit'].text().strip(),
            "ai_model": self._ai_model['edit'].text().strip(),
            "default_commit_message": self._commit_msg['edit'].text().strip(),
            "theme": "dark" if "深色" in self._theme_combo.currentText() else "light"
        }
        
        # 执行持久化存储
        config.update(updates)
        config._save_config() # 强制写入磁盘
        
        logger.info(f"配置已持久化保存: {updates.keys()}")
        
        # 给予用户反馈
        self._save_btn.setText("✅ 已保存到磁盘")
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(2000, lambda: self._save_btn.setText("保存配置"))
        
        self.settings_changed.emit()
        # 如果主题改变，立即通知全局
        if updates['theme'] != config.get("theme", "dark"):
             theme_manager.set_theme(updates['theme'])
