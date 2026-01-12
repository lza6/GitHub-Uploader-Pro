"""
GitHub Uploader Pro - 进度面板
显示上传进度
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar
)
from PyQt6.QtCore import Qt, pyqtSlot
from loguru import logger

from .glass_widgets import GlassPanel, SectionTitle
from ..theme_manager import theme_manager
from core.upload_manager import UploadProgress, UploadState


class ProgressPanel(GlassPanel):
    """
    进度面板
    显示上传进度和状态
    """
    
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
                if item.widget():
                    item.widget().deleteLater()
                    
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        
        # 标题
        title = SectionTitle("📊", "上传进度")
        layout.addWidget(title)
        
        # 进度条
        self._progress_bar = QProgressBar()
        self._progress_bar.setMinimum(0)
        self._progress_bar.setMaximum(100)
        self._progress_bar.setValue(0)
        self._progress_bar.setTextVisible(True)
        self._progress_bar.setFormat("%p%")
        self._progress_bar.setMinimumHeight(24)
        self._progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {c['bg_primary']};
                border: none;
                border-radius: 12px;
                text-align: center;
                color: {c['text_primary']};
                font-weight: bold;
            }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {c['accent']}, stop:1 {c['info']});
                border-radius: 12px;
            }}
        """)
        layout.addWidget(self._progress_bar)
        
        # 状态信息
        info_layout = QHBoxLayout()
        
        # 当前步骤
        self._step_label = QLabel("就绪")
        self._step_label.setStyleSheet(f"color: {c['text_secondary']};")
        info_layout.addWidget(self._step_label)
        
        info_layout.addStretch()
        
        # 状态图标
        self._status_icon = QLabel("⏸️")
        self._status_icon.setStyleSheet("font-size: 18px;")
        info_layout.addWidget(self._status_icon)
        
        layout.addLayout(info_layout)
    
    @pyqtSlot(UploadProgress)
    def update_progress(self, progress: UploadProgress):
        """更新进度"""
        c = theme_manager.colors
        
        # 计算百分比
        if progress.total_steps > 0:
            percent = int((progress.current_step / progress.total_steps) * 100)
        else:
            percent = 0
        
        self._progress_bar.setValue(percent)
        
        # 状态映射
        state_config = {
            UploadState.IDLE: ("就绪", "⏸️", c['text_muted']),
            UploadState.PREPARING: ("准备中...", "🔄", c['info']),
            UploadState.INITIALIZING: ("初始化Git...", "⚙️", c['info']),
            UploadState.ADDING: ("添加文件...", "📥", c['info']),
            UploadState.COMMITTING: ("提交变更...", "💾", c['info']),
            UploadState.PUSHING: ("推送中...", "🚀", c['accent']),
            UploadState.COMPLETED: ("上传完成！", "✅", c['success']),
            UploadState.FAILED: ("上传失败", "❌", c['error']),
            UploadState.CANCELLED: ("已取消", "⏹️", c['warning']),
        }
        
        text, icon, color = state_config.get(
            progress.state,
            (progress.message, "❓", c['text_secondary'])
        )
        
        # 使用消息如果存在
        if progress.message:
            text = progress.message
        
        self._step_label.setText(f"{text} ({progress.current_step}/{progress.total_steps})")
        self._step_label.setStyleSheet(f"color: {color};")
        self._status_icon.setText(icon)
        
        # 完成或失败时设置进度条颜色
        if progress.state == UploadState.COMPLETED:
            self._progress_bar.setValue(100)
            self._progress_bar.setStyleSheet(f"""
                QProgressBar {{
                    background-color: {c['bg_primary']};
                    border: none;
                    border-radius: 12px;
                    text-align: center;
                    color: white;
                    font-weight: bold;
                }}
                QProgressBar::chunk {{
                    background-color: {c['success']};
                    border-radius: 12px;
                }}
            """)
        elif progress.state == UploadState.FAILED:
            self._progress_bar.setStyleSheet(f"""
                QProgressBar {{
                    background-color: {c['bg_primary']};
                    border: none;
                    border-radius: 12px;
                    text-align: center;
                    color: white;
                    font-weight: bold;
                }}
                QProgressBar::chunk {{
                    background-color: {c['error']};
                    border-radius: 12px;
                }}
            """)
    
    def reset(self):
        """重置进度"""
        c = theme_manager.colors
        
        self._progress_bar.setValue(0)
        self._progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {c['bg_primary']};
                border: none;
                border-radius: 12px;
                text-align: center;
                color: {c['text_primary']};
                font-weight: bold;
            }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {c['accent']}, stop:1 {c['info']});
                border-radius: 12px;
            }}
        """)
        self._step_label.setText("就绪")
        self._step_label.setStyleSheet(f"color: {c['text_secondary']};")
        self._status_icon.setText("⏸️")
