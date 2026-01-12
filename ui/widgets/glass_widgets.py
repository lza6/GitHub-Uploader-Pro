"""
GitHub Uploader Pro - 玻璃拟态组件
提供具有玻璃效果的自定义UI组件
"""
from PyQt6.QtWidgets import (
    QWidget, QFrame, QPushButton, QLabel, QVBoxLayout, QHBoxLayout,
    QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QSequentialAnimationGroup
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QLinearGradient, QBrush

from ..theme_manager import theme_manager


class GlassPanel(QFrame):
    """
    玻璃拟态面板 v3.0
    具有超强模糊、细腻边框和深度阴影的容器
    """
    
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self._setup_style()
        # 监听主题变更信号 (V4.2 Reactive)
        theme_manager.theme_changed.connect(self._setup_style)
    
    def _setup_style(self):
        """设置 Nebula V4 风格 (支持多层玻璃折射)"""
        c = theme_manager.colors
        self.setStyleSheet(f"""
            GlassPanel {{
                background-color: {c['bg_glass']};
                border: 1px solid {c['glass_border']};
                border-top: 1px solid {theme_manager.get_dynamic_color('glass_border', l_offset=0.1)};
                border-radius: 28px;
            }}
        """)
        
        # 添加增强型 GPU 阴影
        # shadow = QGraphicsDropShadowEffect(self)
        # shadow.setBlurRadius(60)
        # shadow.setColor(QColor(0, 0, 0, 180))
        # shadow.setOffset(0, 12)
        # self.setGraphicsEffect(shadow)


class GlassButton(QPushButton):
    """
    超感知玻璃按钮 v3.0
    具有动态辉光、细腻渐变和极致交互反馈
    """
    
    def __init__(self, text: str = "", parent: QWidget = None, primary: bool = False, 
                 icon: str = "", style: str = "default"):
        super().__init__(text, parent)
        self._primary = primary
        self._icon = icon
        self._style = style
        self._setup_style()
        # 监听主题变更信号 (V4.2 Reactive)
        theme_manager.theme_changed.connect(self._setup_style)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
    
    def _setup_style(self):
        """设置 Nebula V4 交互式样式 (支持物理反馈)"""
        c = theme_manager.colors
        radius = "18px"
        padding = "15px 32px"
        font_size = "15px"
        
        if self._primary:
            # V4 主按钮: 深度渐变 + 脉冲辉光
            self.setStyleSheet(f"""
                GlassButton {{
                    background: {c['gradient_primary']};
                    color: white;
                    border: none;
                    border-radius: {radius};
                    padding: {padding};
                    font-weight: 800;
                    font-size: {font_size};
                    letter-spacing: 0.8px;
                }}
                GlassButton:hover {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 {c['accent_hover']}, stop:1 {c['accent_secondary']});
                }}
            """)
            
            # V4 动态辉光 (已禁用以防止 Crash)
            # self.shadow = QGraphicsDropShadowEffect(self)
            # self.shadow.setBlurRadius(30)
            # self.shadow.setColor(QColor(88, 166, 255, 150)) 
            # self.shadow.setOffset(0, 5)
            # self.setGraphicsEffect(self.shadow)
        else:
            # V4 次级按钮: 动态折射玻璃
            border_top = theme_manager.get_dynamic_color('border', l_offset=0.05)
            self.setStyleSheet(f"""
                GlassButton {{
                    background-color: {c['bg_glass']};
                    color: {c['text_primary']};
                    border: 1px solid {c['border']};
                    border-top: 1px solid {border_top};
                    border-radius: {radius};
                    padding: {padding};
                    font-size: {font_size};
                    font-weight: 600;
                }}
                GlassButton:hover {{
                    background-color: {c['bg_tertiary']};
                    border-color: {c['accent']};
                    color: {c['accent']};
                }}
            """)
            
            # self.shadow = QGraphicsDropShadowEffect(self)
            # self.shadow.setBlurRadius(20)
            # self.shadow.setColor(QColor(0, 0, 0, 100))
            # self.shadow.setOffset(0, 4)
            # self.setGraphicsEffect(self.shadow)

    def enterEvent(self, event):
        """鼠标滑入：触发 Nebula 辉光增长与 Spring 缩放"""
        if self._primary:
            self.animate_glow(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        """鼠标滑出：恢复标准状态"""
        if self._primary:
            self.animate_glow(False)
        super().leaveEvent(event)

    def animate_glow(self, active: bool):
        """执行辉光呼吸动效"""
        pass
        # if hasattr(self, 'shadow'):
        #     self.anim = QPropertyAnimation(self.shadow, b"blurRadius")
        #     self.anim.setDuration(400)
        #     self.anim.setStartValue(self.shadow.blurRadius())
        #     self.anim.setEndValue(50 if active else 30)
        #     self.anim.setEasingCurve(QEasingCurve.Type.OutQuint)
        #     self.anim.start()


class IconButton(QPushButton):
    """
    图标按钮
    圆形按钮，只显示图标或emoji
    """
    
    def __init__(self, icon_text: str = "", parent: QWidget = None, size: int = 40, color: str = None):
        super().__init__(icon_text, parent)
        self._size = size
        self._icon_color = color
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._setup_style()
        # 监听主题变更信号 (V4.2 Reactive)
        theme_manager.theme_changed.connect(self._setup_style)
    
    def _setup_style(self):
        """设置样式 v4.2.3 [High Density & Contrast]"""
        c = theme_manager.colors
        icon_color = self._icon_color if self._icon_color else c['text_primary']
        
        self.setFixedSize(self._size, self._size)
        # 为 IconButton 显式指定样式，确保 Emoji 渲染，并增加发光效果
        # v4.2.3: 移除类名选择器以增强兼容性，设置 padding: 0 防止裁剪
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {c['bg_glass']};
                color: {icon_color};
                border: 1px solid {c['border']};
                border-top: 1px solid {theme_manager.get_dynamic_color('border', l_offset=0.15)};
                border-radius: {self._size // 2}px;
                font-family: 'Segoe UI Emoji', 'Segoe UI Symbol', 'Apple Color Emoji', 'Noto Color Emoji', 'Microsoft YaHei', sans-serif;
                font-size: {int(self._size * 0.5)}px;
                font-weight: 800;
                padding: 0px;
                margin: 0px;
                text-align: center;
            }}
            QPushButton:hover {{
                background-color: {c['accent_glow']};
                border-color: {c['accent']};
                color: {c['accent']};
            }}
            QPushButton:pressed {{
                background-color: {c['accent']};
                color: white;
            }}
        """)


class StatusIndicator(QWidget):
    """
    状态指示器
    带有颜色圆点的状态显示组件
    """
    
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self._status = "idle"  # idle, success, warning, error, loading
        self._text = ""
        self._setup_ui()
    
    def _setup_ui(self):
        """设置UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # 状态圆点
        self._dot = QLabel("●")
        self._dot.setFixedWidth(16)
        layout.addWidget(self._dot)
        
        # 状态文本
        self._label = QLabel()
        layout.addWidget(self._label)
        
        self._update_style()
    
    def set_status(self, status: str, text: str = "") -> None:
        """设置状态"""
        self._status = status
        self._text = text
        self._update_style()
    
    def _update_style(self):
        """更新样式"""
        c = theme_manager.colors
        
        color_map = {
            "idle": c['text_muted'],
            "success": c['success'],
            "warning": c['warning'],
            "error": c['error'],
            "loading": c['info'],
        }
        
        color = color_map.get(self._status, c['text_muted'])
        
        self._dot.setStyleSheet(f"color: {color}; font-size: 12px;")
        self._label.setText(self._text)
        self._label.setStyleSheet(f"color: {c['text_secondary']};")


class SectionTitle(QWidget):
    """
    分区标题
    带图标的分区标题组件
    """
    
    def __init__(self, icon: str, title: str, parent: QWidget = None):
        super().__init__(parent)
        self._icon = icon
        self._title = title
        self._setup_ui()
    
    def _setup_ui(self):
        """设置UI"""
        c = theme_manager.colors
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 8)
        layout.setSpacing(8)
        
        # 图标
        icon_label = QLabel(self._icon)
        icon_label.setStyleSheet("font-size: 18px;")
        layout.addWidget(icon_label)
        
        # 标题
        title_label = QLabel(self._title)
        title_label.setStyleSheet(f"""
            font-size: 16px;
            font-weight: bold;
            color: {c['text_primary']};
        """)
        layout.addWidget(title_label)
        
        layout.addStretch()


class Card(QFrame):
    """
    卡片组件
    用于包装内容的卡片样式容器
    """
    
    clicked = pyqtSignal()
    
    def __init__(self, parent: QWidget = None, clickable: bool = False):
        super().__init__(parent)
        self._clickable = clickable
        self._setup_style()
    
    def _setup_style(self):
        """设置样式"""
        c = theme_manager.colors
        
        base_style = f"""
            Card {{
                background-color: {c['bg_secondary']};
                border: 1px solid {c['border']};
                border-radius: 12px;
                padding: 16px;
            }}
        """
        
        if self._clickable:
            base_style += f"""
                Card:hover {{
                    background-color: {c['bg_tertiary']};
                    border-color: {c['accent']};
                }}
            """
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self.setStyleSheet(base_style)
    
    def mousePressEvent(self, event):
        """鼠标点击事件"""
        if self._clickable:
            self.clicked.emit()
        super().mousePressEvent(event)


class Divider(QFrame):
    """
    分割线组件
    """
    
    def __init__(self, parent: QWidget = None, vertical: bool = False):
        super().__init__(parent)
        
        if vertical:
            self.setFrameShape(QFrame.Shape.VLine)
            self.setFixedWidth(1)
        else:
            self.setFrameShape(QFrame.Shape.HLine)
            self.setFixedHeight(1)
        
        c = theme_manager.colors
        self.setStyleSheet(f"background-color: {c['border']};")
