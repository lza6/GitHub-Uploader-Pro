"""
GitHub Uploader Pro - 加载动画组件 v2.0
提供多种加载动画效果
"""
from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt6.QtGui import QPainter, QColor, QFont, QPen
from typing import Optional
from ..theme_manager import theme_manager


class LoadingSpinner(QWidget):
    """
    圆形加载动画
    """
    
    def __init__(self, size: int = 40, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._size = size
        self._angle = 0
        self._animation_speed = 10
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._rotate)
        self._setup_ui()
    
    def _setup_ui(self):
        """设置UI"""
        self.setFixedSize(self._size, self._size)
    
    def start(self):
        """开始动画"""
        self._timer.start(self._animation_speed)
    
    def stop(self):
        """停止动画"""
        self._timer.stop()
        self._angle = 0
        self.update()
    
    def _rotate(self):
        """旋转"""
        self._angle = (self._angle + 10) % 360
        self.update()
    
    def paintEvent(self, event):
        """绘制事件"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        c = theme_manager.colors
        
        # 绘制背景圆环
        painter.setPen(QPen(QColor(c['border']), 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(2, 2, self._size - 4, self._size - 4)
        
        # 绘制进度圆弧
        painter.setPen(QPen(QColor(c['accent']), 3))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawArc(2, 2, self._size - 4, self._size - 4, 
                       self._angle * 16, 270 * 16)


class DotsLoader(QWidget):
    """
    点状加载动画
    """
    
    def __init__(self, dot_size: int = 8, spacing: int = 4, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._dot_size = dot_size
        self._spacing = spacing
        self._current_dot = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate)
        self._setup_ui()
    
    def _setup_ui(self):
        """设置UI"""
        width = self._dot_size * 3 + self._spacing * 2
        height = self._dot_size
        self.setFixedSize(width, height)
    
    def start(self):
        """开始动画"""
        self._timer.start(200)
    
    def stop(self):
        """停止动画"""
        self._timer.stop()
        self._current_dot = 0
        self.update()
    
    def _animate(self):
        """动画"""
        self._current_dot = (self._current_dot + 1) % 3
        self.update()
    
    def paintEvent(self, event):
        """绘制事件"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        c = theme_manager.colors
        
        for i in range(3):
            x = i * (self._dot_size + self._spacing)
            y = (self.height() - self._dot_size) // 2
            
            if i == self._current_dot:
                painter.setBrush(QColor(c['accent']))
            else:
                painter.setBrush(QColor(c['border']))
            
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(x, y, self._dot_size, self._dot_size)


class LoadingOverlay(QWidget):
    """
    加载遮罩层
    显示加载动画和提示文字
    """
    
    def __init__(self, text: str = "加载中...", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._text = text
        self._setup_ui()
    
    def _setup_ui(self):
        """设置UI"""
        c = theme_manager.colors
        
        self.setStyleSheet(f"""
            LoadingOverlay {{
                background-color: {c['bg_glass_strong']};
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # 加载动画
        self._spinner = LoadingSpinner(size=50)
        layout.addWidget(self._spinner, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # 提示文字
        self._label = QLabel(self._text)
        self._label.setStyleSheet(f"""
            font-size: 16px;
            font-weight: 600;
            color: {c['text_primary']};
            margin-top: 20px;
        """)
        layout.addWidget(self._label, alignment=Qt.AlignmentFlag.AlignCenter)
    
    def set_text(self, text: str):
        """设置提示文字"""
        self._label.setText(text)
    
    def start(self):
        """开始动画"""
        self._spinner.start()
        self.show()
    
    def stop(self):
        """停止动画"""
        self._spinner.stop()
        self.hide()
    
    def show(self):
        """显示"""
        if self.parent():
            self.setGeometry(self.parent().rect())
        super().show()
        self.raise_()