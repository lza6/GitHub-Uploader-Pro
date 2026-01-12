"""
GitHub Uploader Pro - 文件夹选择器
提供文件夹选择和统计功能
"""
import os
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QMenu
)
from PyQt6.QtCore import Qt, pyqtSignal
from loguru import logger

from .glass_widgets import GlassPanel, GlassButton, SectionTitle, IconButton
from ..theme_manager import theme_manager
from utils.config import config


class FolderPicker(GlassPanel):
    """
    文件夹选择器
    允许用户选择要上传的文件夹
    """
    
    folder_selected = pyqtSignal(str)  # 选择的文件夹路径
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._folder_path: str = ""
        self._file_count: int = 0
        self._folder_size: int = 0
        self._setup_ui()
        # 响应主题变更 (V4.2 Reactive)
        theme_manager.theme_changed.connect(self._setup_ui)
        self._load_last_folder()
    
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
        
        # 标题行
        header = QHBoxLayout()
        title = SectionTitle("📁", "上传文件夹")
        header.addWidget(title)
        
        # 最近文件夹菜单
        self._recent_btn = IconButton("⏱️", size=32)
        self._recent_btn.setToolTip("查看最近上传过的文件夹历史")
        self._recent_btn.clicked.connect(self._show_recent_menu)
        header.addWidget(self._recent_btn)
        
        layout.addLayout(header)
        
        # 选择按钮
        select_btn = GlassButton("📂 选择上传目录...")
        select_btn.clicked.connect(self._select_folder)
        layout.addWidget(select_btn)
        
        # 路径显示
        self._path_label = QLabel("尚未选择目录")
        self._path_label.setStyleSheet(f"""
            color: {c['text_secondary']};
            font-size: 12px;
            padding: 8px;
            background-color: {c['bg_primary']};
            border-radius: 6px;
        """)
        self._path_label.setWordWrap(True)
        layout.addWidget(self._path_label)
        
        # 统计信息
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(20)
        
        # 文件数
        self._file_count_label = QLabel("📄 --")
        self._file_count_label.setStyleSheet(f"color: {c['text_muted']};")
        stats_layout.addWidget(self._file_count_label)
        
        # 大小
        self._size_label = QLabel("💾 --")
        self._size_label.setStyleSheet(f"color: {c['text_muted']};")
        stats_layout.addWidget(self._size_label)
        
        stats_layout.addStretch()
        layout.addLayout(stats_layout)
    
    def _select_folder(self):
        """选择文件夹"""
        # 获取初始目录
        initial_dir = self._folder_path or str(Path.home())
        
        folder = QFileDialog.getExistingDirectory(
            self.window(),
            "选择要上传的文件夹",
            initial_dir,
            QFileDialog.Option.ShowDirsOnly
        )
        
        if folder:
            self.set_folder(folder)
    
    def set_folder(self, folder_path: str):
        """设置文件夹路径"""
        if not os.path.isdir(folder_path):
            logger.warning(f"无效的文件夹路径: {folder_path}")
            return
        
        self._folder_path = folder_path
        self._update_stats()
        self._update_display()
        
        # 保存最后使用的文件夹
        config.set("last_folder", folder_path)
        config.add_recent_folder(folder_path)
        
        self.folder_selected.emit(folder_path)
        logger.info(f"已选择文件夹: {folder_path}")
    
    def _update_stats(self):
        """更新统计信息"""
        if not self._folder_path:
            self._file_count = 0
            self._folder_size = 0
            return
        
        self._file_count = 0
        self._folder_size = 0
        
        for root, dirs, files in os.walk(self._folder_path):
            # 跳过.git目录
            dirs[:] = [d for d in dirs if d != ".git"]
            
            self._file_count += len(files)
            
            for file in files:
                try:
                    self._folder_size += os.path.getsize(os.path.join(root, file))
                except OSError:
                    pass
    
    def _update_display(self):
        """更新显示"""
        c = theme_manager.colors
        
        if self._folder_path:
            # 显示缩短的路径
            display_path = self._folder_path
            if len(display_path) > 50:
                display_path = "..." + display_path[-47:]
            
            self._path_label.setText(display_path)
            self._path_label.setStyleSheet(f"""
                color: {c['text_primary']};
                font-size: 12px;
                padding: 8px;
                background-color: {c['bg_primary']};
                border-radius: 6px;
            """)
            self._path_label.setToolTip(self._folder_path)
            
            self._file_count_label.setText(f"📄 {self._file_count} 文件")
            self._size_label.setText(f"💾 {self._format_size(self._folder_size)}")
        else:
            self._path_label.setText("未选择文件夹")
            self._path_label.setStyleSheet(f"""
                color: {c['text_muted']};
                font-size: 12px;
                padding: 8px;
                background-color: {c['bg_primary']};
                border-radius: 6px;
            """)
            self._file_count_label.setText("📄 --")
            self._size_label.setText("💾 --")
        
        # 确保统计标签颜色也随之刷新
        self._file_count_label.setStyleSheet(f"color: {c['text_secondary']};")
        self._size_label.setStyleSheet(f"color: {c['text_secondary']};")
    
    def _load_last_folder(self):
        """加载上次使用的文件夹"""
        if config.get("remember_last_folder", True):
            last_folder = config.get("last_folder", "")
            if last_folder and os.path.isdir(last_folder):
                self.set_folder(last_folder)
    
    def _show_recent_menu(self):
        """显示最近文件夹菜单"""
        c = theme_manager.colors
        
        recent = config.get("recent_folders", [])
        if not recent:
            return
        
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {c['bg_secondary']};
                color: {c['text_primary']};
                border: 1px solid {c['border']};
                border-radius: 8px;
                padding: 5px;
            }}
            QMenu::item {{
                padding: 8px 20px;
                border-radius: 4px;
            }}
            QMenu::item:selected {{
                background-color: {c['accent']};
            }}
        """)
        
        for folder in recent[:10]:
            if os.path.isdir(folder):
                # 显示缩短的路径
                display = folder if len(folder) <= 40 else "..." + folder[-37:]
                action = menu.addAction(f"📁 {display}")
                action.setData(folder)
                action.triggered.connect(lambda checked, f=folder: self.set_folder(f))
        
        menu.exec(self._recent_btn.mapToGlobal(self._recent_btn.rect().bottomLeft()))
    
    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """格式化文件大小"""
        for unit in ["B", "KB", "MB", "GB"]:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"
    
    @property
    def folder_path(self) -> str:
        """获取当前选择的文件夹路径"""
        return self._folder_path
    
    @property
    def file_count(self) -> int:
        """获取文件数量"""
        return self._file_count
    
    @property
    def folder_size(self) -> int:
        """获取文件夹大小（字节）"""
        return self._folder_size
