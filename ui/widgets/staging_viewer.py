"""
GitHub Uploader Pro - Staging Viewer
可视化暂存区，展示文件差异和统计信息
"""
from typing import List
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, 
    QListWidgetItem, QCheckBox, QPushButton, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from loguru import logger

from .glass_widgets import GlassPanel, SectionTitle, Divider
from ..theme_manager import theme_manager
from core.git_status_provider import FileStatus, GitStatusProvider


class StagingItem(QWidget):
    """暂存区单个文件项"""
    def __init__(self, file_status: FileStatus, parent=None):
        super().__init__(parent)
        self._status = file_status
        self._setup_ui()
        
    def _setup_ui(self):
        c = theme_manager.colors
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        
        # 状态图标
        code = self._status.status[:2].strip()
        color = c['text_primary']
        icon = "📄"
        
        if code == "??" or code == "?":
            color = c['text_muted']
            icon = "❓"
        elif "A" in code:
            color = c['success']
            icon = "➕"
        elif "M" in code:
            color = c['warning']
            icon = "✏️"
        elif "D" in code:
            color = c['error']
            icon = "🗑️"
            
        self._check = QCheckBox()
        self._check.setChecked(self._status.staged)
        layout.addWidget(self._check)
        
        status_label = QLabel(icon)
        status_label.setFixedWidth(20)
        layout.addWidget(status_label)
        
        name_label = QLabel(self._status.display_name)
        name_label.setStyleSheet(f"color: {color}; font-family: 'Consolas';")
        layout.addWidget(name_label, 1)
        
        size_kb = self._status.size / 1024
        size_label = QLabel(f"{size_kb:.1f} KB")
        size_label.setStyleSheet(f"color: {c['text_muted']}; font-size: 11px;")
        layout.addWidget(size_label)

    @property
    def is_selected(self) -> bool:
        return self._check.isChecked()
    
    @property
    def file_path(self) -> str:
        return self._status.path


class StagingViewer(GlassPanel):
    """
    可视化暂存区
    """
    status_changed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._project_path: Optional[str] = None
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
        
        # 头部
        header = QHBoxLayout()
        title = SectionTitle("📊", "文件列表 (Staging Area)")
        header.addWidget(title)
        
        self._refresh_btn = QPushButton("刷新")
        self._refresh_btn.setStyleSheet(f"color: {c['accent']}; border: none; background: transparent;")
        self._refresh_btn.clicked.connect(self.refresh)
        header.addStretch()
        header.addWidget(self._refresh_btn)
        
        layout.addLayout(header)
        
        # 统计
        self._summary_label = QLabel("正在分析项目状态...")
        self._summary_label.setStyleSheet(f"color: {c['text_secondary']}; font-size: 12px;")
        layout.addWidget(self._summary_label)
        
        # 列表
        self._list = QListWidget()
        self._list.setStyleSheet(f"""
            QListWidget {{
                background: transparent;
                border: 1px solid {c['border']};
                border-radius: 8px;
            }}
            QListWidget::item {{
                background: transparent;
                border-bottom: 1px solid {c['bg_tertiary']};
            }}
        """)
        self._list.setMinimumHeight(200)
        layout.addWidget(self._list)
        
        # 底部操作
        footer = QHBoxLayout()
        self._select_all_btn = QPushButton("全选")
        self._select_all_btn.clicked.connect(self._select_all)
        footer.addWidget(self._select_all_btn)
        
        self._deselect_all_btn = QPushButton("全取消")
        self._deselect_all_btn.clicked.connect(self._deselect_all)
        footer.addWidget(self._deselect_all_btn)
        
        footer.addStretch()
        layout.addLayout(footer)

    def set_project_path(self, path: str):
        self._provider = GitStatusProvider(path)
        self.refresh()
        
    def refresh(self):
        if not self._provider: return
        
        self._list.clear()
        files = self._provider.get_detailed_status()
        summary = self._provider.get_summary(files)
        
        for f in files:
            item = QListWidgetItem(self._list)
            widget = StagingItem(f)
            item.setSizeHint(widget.sizeHint())
            self._list.addItem(item)
            self._list.setItemWidget(item, widget)
            
        self._update_summary(summary)
        
    def _update_summary(self, s):
        def format_size(b):
            for unit in ['B', 'KB', 'MB']:
                if b < 1024: return f"{b:.1f} {unit}"
                b /= 1024
            return f"{b:.1f} GB"
            
        text = f"待推送: {s['staged_count']} 文件 ({format_size(s['staged_size'])}) | " \
               f"忽略/未跟踪: {s['unstaged_count']} 文件 ({format_size(s['unstaged_size'])})"
        self._summary_label.setText(text)

    def _select_all(self):
        for i in range(self._list.count()):
            w = self._list.itemWidget(self._list.item(i))
            w._check.setChecked(True)
            
    def _deselect_all(self):
        for i in range(self._list.count()):
            w = self._list.itemWidget(self._list.item(i))
            w._check.setChecked(False)
