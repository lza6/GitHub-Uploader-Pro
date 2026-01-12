"""
GitHub Uploader Pro - 日志控制台
实时显示终端日志输出
"""
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton,
    QScrollBar
)
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot, QTimer
from PyQt6.QtGui import QTextCursor, QColor, QTextCharFormat, QFont
from loguru import logger

from .glass_widgets import GlassPanel, SectionTitle, IconButton
from ..theme_manager import theme_manager


class LogConsole(GlassPanel):
    """
    日志控制台
    复刻终端风格的日志输出组件
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._auto_scroll = True
        self._max_lines = 1000
        self._log_buffer = [] # 日志缓冲
        self._setup_ui()
        theme_manager.theme_changed.connect(self._setup_ui)
        
        # V4.8.5 Fix: 使用定时器批量刷新日志，防止 UI 线程阻塞/递归重绘崩溃
        self._flush_timer = QTimer(self)
        self._flush_timer.setInterval(100) # 100ms 刷新一次
        self._flush_timer.timeout.connect(self._flush_logs)
        self._flush_timer.start()
    
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
                    
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        _layout = layout
        
        # 标题行
        header = QHBoxLayout()
        title = SectionTitle("🖥️", "终端日志")
        header.addWidget(title)
        header.addStretch()
        
        # 自动滚动按钮
        self._scroll_btn = IconButton("⬇️", size=28)
        self._scroll_btn.setToolTip("开启/关闭自动滚动")
        self._scroll_btn.setCheckable(True)
        self._scroll_btn.setChecked(True)
        self._scroll_btn.clicked.connect(self._toggle_auto_scroll)
        header.addWidget(self._scroll_btn)
        
        # 清空按钮
        clear_btn = IconButton("🗑️", size=28)
        clear_btn.setToolTip("清空当前终端日志")
        clear_btn.clicked.connect(self.clear)
        header.addWidget(clear_btn)
        
        layout.addLayout(header)
        
        # 日志文本区
        self._text_edit = QTextEdit()
        self._text_edit.setReadOnly(True)
        self._text_edit.setFont(QFont("Consolas", 11))
        self._text_edit.setStyleSheet(f"""
            QTextEdit {{
                background-color: {c['bg_primary']};
                color: {c['text_primary']};
                border: 1px solid {c['border']};
                border-radius: 8px;
                padding: 10px;
                selection-background-color: {c['accent']};
            }}
        """)
        self._text_edit.setMinimumHeight(150)
        layout.addWidget(self._text_edit)
        
        # 连接滚动条事件
        self._text_edit.verticalScrollBar().valueChanged.connect(self._on_scroll)
    
    def _toggle_auto_scroll(self):
        """切换自动滚动"""
        self._auto_scroll = self._scroll_btn.isChecked()
    
    def _on_scroll(self, value: int):
        """滚动事件"""
        scrollbar = self._text_edit.verticalScrollBar()
        # 如果用户手动滚动到非底部，关闭自动滚动
        if value < scrollbar.maximum() - 10:
            if self._auto_scroll:
                self._auto_scroll = False
                self._scroll_btn.setChecked(False)

    @pyqtSlot(str, str, str)
    def append_log(self, timestamp: str, level: str, message: str):
        """
        添加日志条目 (缓冲模式)
        """
        # 将日志压入缓冲区，等待定时器刷新
        self._log_buffer.append((timestamp, level, message))
        
    def _flush_logs(self):
        """批量刷新日志缓冲区"""
        if not self._log_buffer:
            return
            
        c = theme_manager.colors
        
        # 颜色映射
        level_colors = {
            "INFO": c['info'],
            "WARNING": c['warning'],
            "ERROR": c['error'],
            "DEBUG": c['text_muted'],
            "SUCCESS": c['success'],
        }
        
        level_icons = {
            "INFO": "ℹ️",
            "WARNING": "⚠️",
            "ERROR": "❌",
            "DEBUG": "🔍",
            "SUCCESS": "✅",
        }
        
        html_chunks = []
        
        # 一次性处理所有缓冲的日志
        # 限制每次处理的数量，防止卡顿
        batch_size = min(len(self._log_buffer), 50) 
        current_batch = self._log_buffer[:batch_size]
        self._log_buffer = self._log_buffer[batch_size:]
        
        for timestamp, level, message in current_batch:
            color = level_colors.get(level.upper(), c['text_primary'])
            icon = level_icons.get(level.upper(), "•")
            
            # 构建HTML格式的日志
            html = f"""
            <div style="margin: 2px 0;">
                <span style="color: {c['text_muted']};">[{timestamp}]</span>
                <span style="color: {color};">{icon}</span>
                <span style="color: {c['text_primary']};">{self._escape_html(message)}</span>
            </div>
            """
            html_chunks.append(html)
            
        if not html_chunks:
            return

        cursor = self._text_edit.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertHtml("".join(html_chunks))
        
        # 限制行数
        self._trim_lines()
        
        # 自动滚动
        if self._auto_scroll:
            self._text_edit.verticalScrollBar().setValue(
                self._text_edit.verticalScrollBar().maximum()
            )
    
    def log(self, message: str, level: str = "INFO"):
        """
        简化的日志方法
        
        Args:
            message: 日志消息
            level: 日志级别
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.append_log(timestamp, level, message)
    
    def log_info(self, message: str):
        """记录信息日志"""
        self.log(message, "INFO")
    
    def log_success(self, message: str):
        """记录成功日志"""
        self.log(message, "SUCCESS")
    
    def log_warning(self, message: str):
        """记录警告日志"""
        self.log(message, "WARNING")
    
    def log_error(self, message: str):
        """记录错误日志"""
        self.log(message, "ERROR")
    
    def log_debug(self, message: str):
        """记录调试日志"""
        self.log(message, "DEBUG")
    
    def _trim_lines(self):
        """限制日志行数"""
        document = self._text_edit.document()
        while document.blockCount() > self._max_lines:
            cursor = QTextCursor(document.firstBlock())
            cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
            cursor.removeSelectedText()
            cursor.deleteChar()  # 删除换行
    
    @staticmethod
    def _escape_html(text: str) -> str:
        """转义HTML特殊字符"""
        return (
            text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#39;")
        )
    
    def clear(self):
        """清空日志"""
        self._text_edit.clear()
    
    def get_log_text(self) -> str:
        """获取纯文本日志"""
        return self._text_edit.toPlainText()
