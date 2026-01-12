"""
GitHub Uploader Pro - 主题管理器 v4.0 (Nebula)
提供动态 HSL 调色引擎、GPU 加速动效样式
支持跨代视觉特效：动态辉光、折射玻璃态
"""
import colorsys
from typing import Optional, Tuple
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPalette, QColor
from PyQt6.QtCore import QObject, pyqtSignal
from loguru import logger

from utils.config import config


class ThemeManager(QObject):
    """
    主题管理器 v4.2 [Reactive Nebula Core]
    管理应用全局样式和暗黑模式切换，支持信号广播
    """
    
    theme_changed = pyqtSignal(str)  # 主题变更信号
    
    # V4 Nebula 深色主题 - 极致深邃与霓虹
    DARK_COLORS = {
        "bg_primary": "#05070a",      
        "bg_secondary": "#0c0f14",     
        "bg_tertiary": "#161b22",      
        "bg_glass": "rgba(12, 15, 20, 0.72)",  
        "bg_glass_strong": "rgba(5, 7, 10, 0.90)",  
        
        "text_primary": "#ffffff",     
        "text_secondary": "#a1b0be",   
        "text_muted": "#6e7681",       
        "text_disabled": "#30363d",    
        
        "accent": "#58a6ff",           
        "accent_hover": "#79c0ff",     
        "accent_secondary": "#bc8cff", 
        "accent_tertiary": "#3fb950",  
        "accent_glow": "rgba(88, 166, 255, 0.40)", 
        
        # V4 新增高阶特效
        "nebula_glow": "qradialgradient(cx:0.5, cy:0.5, radius:0.8, fx:0.5, fy:0.5, stop:0 rgba(88, 166, 255, 0.15), stop:1 rgba(0, 0, 0, 0))",
        "glass_border": "rgba(255, 255, 255, 0.12)",
        "glass_refraction": "rgba(255, 255, 255, 0.03)",
        
        "gradient_primary": "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #58a6ff, stop:1 #bc8cff)",
        "gradient_success": "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #2ea043, stop:1 #3fb950)",
        "gradient_warning": "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #d29922, stop:1 #e3b341)",
        "gradient_error": "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #f85149, stop:1 #ff7b72)",
        
        "success": "#3fb950",          
        "warning": "#e3b341",          
        "error": "#f85149",            
        "info": "#58a6ff",             
        
        "border": "rgba(255, 255, 255, 0.1)", 
        "border_light": "rgba(255, 255, 255, 0.05)",
        "border_accent": "rgba(88, 166, 255, 0.4)",
        "shadow": "rgba(0, 0, 0, 0.6)",
        "shadow_strong": "rgba(0, 0, 0, 0.8)",
        "glass_blur": "40px",
    }
    
    # 浅色主题颜色配置 - Modern Clean v3.0 (Paper White)
    LIGHT_COLORS = {
        # 背景色
        "bg_primary": "#f0f2f5",      
        "bg_secondary": "#ffffff",     
        "bg_tertiary": "#e1e4e8",      
        "bg_glass": "rgba(255, 255, 255, 0.80)",  
        "bg_glass_strong": "rgba(255, 255, 255, 0.98)",  
        
        # 文字色
        "text_primary": "#1a1e23",     
        "text_secondary": "#586069",   
        "text_muted": "#959da5",       
        "text_disabled": "#d1d5da",    
        
        # 强调色
        "accent": "#0366d6",           
        "accent_hover": "#0576f3",     
        "accent_secondary": "#6f42c1", 
        "accent_tertiary": "#28a745",  
        "accent_glow": "rgba(3, 102, 214, 0.2)",
        
        # 渐变色
        "gradient_primary": "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #0366d6, stop:1 #6f42c1)",
        "gradient_success": "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #28a745, stop:1 #34d058)",
        "gradient_warning": "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #f9c513, stop:1 #ffd33d)",
        "gradient_error": "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #cb2431, stop:1 #f85149)",
        "gradient_info": "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #05264c, stop:1 #0366d6)",
        "gradient_surface": "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ffffff, stop:1 #f6f8fa)",
        
        # 状态色
        "success": "#28a745",          
        "warning": "#ffd33d",          
        "error": "#d73a49",            
        "info": "#0366d6",             
        
        # 边框与光影
        "border": "rgba(27, 31, 35, 0.12)",
        "border_light": "rgba(27, 31, 35, 0.05)",
        "border_accent": "rgba(3, 102, 214, 0.4)",
        
        # 阴影
        "shadow": "rgba(0, 0, 0, 0.08)",
        "shadow_light": "rgba(0, 0, 0, 0.04)",
        "shadow_strong": "rgba(0, 0, 0, 0.15)",
        "shadow_glow": "rgba(3, 102, 214, 0.1)",
        
        # 玻璃态
        "glass_blur": "30px",
        "glass_border": "rgba(0, 0, 0, 0.08)",
    }
    
    _instance: Optional['ThemeManager'] = None
    
    def __new__(cls) -> 'ThemeManager':
        if cls._instance is None:
            # 注意：super().__new__(cls) 必须在 QObject 之前处理
            cls._instance = super(ThemeManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        super().__init__()
        self._initialized = True
        self._current_theme = config.get("theme", "dark")
        self._colors = self.DARK_COLORS if self._current_theme == "dark" else self.LIGHT_COLORS
    
    @property
    def current_theme(self) -> str:
        """获取当前主题"""
        return self._current_theme
    
    @property
    def colors(self) -> dict:
        """获取当前主题颜色"""
        return self._colors
    
    def set_theme(self, theme: str) -> None:
        """设置主题并广播变更 v4.2"""
        if theme not in ("dark", "light"):
            logger.warning(f"未知主题: {theme}")
            return
        
        self._current_theme = theme
        self._colors = self.DARK_COLORS if theme == "dark" else self.LIGHT_COLORS
        config.set("theme", theme)
        logger.info(f"主题已切换为: {theme}")
        
        # 广播变更
        self.theme_changed.emit(theme)
    
    def toggle_theme(self) -> str:
        """切换主题"""
        new_theme = "light" if self._current_theme == "dark" else "dark"
        self.set_theme(new_theme)
        return new_theme
    
    def get_color(self, key: str) -> str:
        """获取 hex 颜色字符串"""
        return self.colors.get(key, "#FFFFFF")

    def get_color_obj(self, key: str) -> QColor:
        """获取 QColor 对象 v4.3"""
        return QColor(self.get_color(key))
    
    @staticmethod
    def hex_to_hsl(hex_color: str) -> Tuple[float, float, float]:
        """将 Hex 转换为 HSL (0-1)"""
        hex_color = hex_color.lstrip('#')
        rgb = tuple(int(hex_color[i:i+2], 16)/255.0 for i in (0, 2, 4))
        return colorsys.rgb_to_hls(*rgb)

    @staticmethod
    def hsl_to_hex(h: float, l: float, s: float) -> str:
        """将 HSL 转换为 Hex"""
        rgb = colorsys.hls_to_rgb(h, l, s)
        return '#{:02x}{:02x}{:02x}'.format(
            int(rgb[0]*255), int(rgb[1]*255), int(rgb[2]*255)
        )

    def get_dynamic_color(self, base_color_name: str, l_offset: float = 0.0, s_offset: float = 0.0) -> str:
        """基于 HSL 的动态调色引擎"""
        base_hex = self.get_color(base_color_name)
        if not base_hex.startswith('#'): return base_hex
        
        h, l, s = self.hex_to_hsl(base_hex)
        return self.hsl_to_hex(h, max(0, min(1, l + l_offset)), max(0, min(1, s + s_offset)))

    def get_stylesheet(self) -> str:
        """获取完整样式表 v4.0 (Nebula)"""
        c = self._colors
        
        # 动态计算一些高级色阶
        btn_hover = self.get_dynamic_color("bg_secondary", l_offset=0.05)
        btn_pressed = self.get_dynamic_color("accent", l_offset=-0.1)
        
        return f"""
        /* ==================== V4 Nebula 全局样式 ==================== */
        QWidget {{
            font-family: 'Inter', 'Outfit', 'Microsoft YaHei UI', sans-serif;
            font-size: 14px;
            color: {c['text_primary']};
            selection-background-color: {c['accent']};
            selection-color: white;
            outline: none;
        }}
        
        QMainWindow {{
            background-color: {c['bg_primary']};
        }}
        
        /* ==================== 滚动条 ==================== */
        QScrollBar:vertical {{
            background: transparent;
            width: 8px;
            margin: 0px;
        }}
        
        QScrollBar::handle:vertical {{
            background: {c['border']};
            border-radius: 4px;
            min-height: 30px;
        }}
        
        QScrollBar::handle:vertical:hover {{
            background: {c['accent']};
        }}
        
        QScrollBar::add-line:vertical,
        QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
        
        QScrollBar:horizontal {{
            background: transparent;
            height: 8px;
        }}
        
        QScrollBar::handle:horizontal {{
            background: {c['border']};
            border-radius: 4px;
            min-width: 30px;
        }}
        
        QScrollBar::handle:horizontal:hover {{
            background: {c['accent']};
        }}
        
        /* ==================== 按钮 ==================== */
        QPushButton {{
            background-color: {c['bg_secondary']};
            color: {c['text_primary']};
            border: 1px solid {c['border']};
            border-radius: 10px;
            padding: 12px 24px;
            font-weight: 600;
            font-size: 14px;
        }}
        
        QPushButton:hover {{
            background-color: {c['bg_tertiary']};
            border-color: {c['accent']};
            color: {c['text_primary']};
        }}
        
        QPushButton:pressed {{
            background-color: {c['accent']};
            color: white;
            border-color: {c['accent']};
        }}
        
        QPushButton:disabled {{
            background-color: {c['bg_tertiary']};
            color: {c['text_disabled']};
            border-color: {c['border']};
        }}
        
        QPushButton#primaryButton {{
            background: {c['gradient_primary']};
            color: white;
            border: none;
            box-shadow: 0 4px 15px {c['shadow']};
        }}
        
        QPushButton#primaryButton:hover {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {c['accent_hover']}, stop:1 {c['accent_secondary']});
            box-shadow: 0 6px 20px {c['shadow_strong']};
        }}
        
        QPushButton#primaryButton:pressed {{
            box-shadow: 0 2px 10px {c['shadow']};
        }}
        
        QPushButton#successButton {{
            background: {c['gradient_success']};
            color: white;
            border: none;
        }}
        
        QPushButton#dangerButton {{
            background: {c['gradient_error']};
            color: white;
            border: none;
        }}
        
        QPushButton#ghostButton {{
            background-color: transparent;
            color: {c['text_primary']};
            border: 1px solid {c['border']};
        }}
        
        QPushButton#ghostButton:hover {{
            background-color: {c['bg_tertiary']};
            border-color: {c['accent']};
        }}
        
        /* ==================== 输入框 ==================== */
        QLineEdit, QTextEdit, QPlainTextEdit {{
            background-color: {c['bg_secondary']};
            color: {c['text_primary']};
            border: 2px solid {c['border']};
            border-radius: 12px;
            padding: 12px 18px;
            selection-background-color: {c['accent']};
            selection-color: white;
        }}
        
        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
            border-color: {c['accent']};
            background-color: {c['bg_secondary']};
        }}
        
        QLineEdit:hover, QTextEdit:hover, QPlainTextEdit:hover {{
            border-color: {c['border_accent'] if 'border_accent' in c else c['accent']};
        }}
        
        QLineEdit:disabled, QTextEdit:disabled, QPlainTextEdit:disabled {{
            background-color: {c['bg_tertiary']};
            color: {c['text_disabled']};
            border-color: {c['border']};
        }}
        
        /* ==================== 下拉框 ==================== */
        QComboBox {{
            background-color: {c['bg_secondary']};
            color: {c['text_primary']};
            border: 2px solid {c['border']};
            border-radius: 10px;
            padding: 12px 16px;
            min-width: 100px;
            min-height: 20px;
            font-size: 14px;
        }}
        
        QComboBox:hover {{
            border-color: {c['border_accent'] if 'border_accent' in c else c['accent']};
        }}
        
        QComboBox:focus {{
            border-color: {c['accent']};
        }}
        
        QComboBox::drop-down {{
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 30px;
            border: none;
        }}
        
        QComboBox::down-arrow {{
            width: 12px;
            height: 12px;
            image: none;
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 6px solid {c['text_secondary']};
        }}
        
        QComboBox QAbstractItemView {{
            background-color: {c['bg_secondary']};
            color: {c['text_primary']};
            border: 2px solid {c['border']};
            border-radius: 10px;
            selection-background-color: {c['accent']};
            selection-color: white;
            padding: 4px;
        }}
        
        QComboBox QAbstractItemView::item {{
            padding: 8px 12px;
            border-radius: 6px;
            margin: 2px;
        }}
        
        QComboBox QAbstractItemView::item:hover {{
            background-color: {c['bg_tertiary']};
        }}
        
        QComboBox QAbstractItemView::item:selected {{
            background-color: {c['accent']};
            color: white;
        }}
        
        /* ==================== 标签 ==================== */
        QLabel {{
            color: {c['text_primary']};
        }}
        
        QLabel#titleLabel {{
            font-size: 24px;
            font-weight: 700;
            letter-spacing: -0.5px;
        }}
        
        QLabel#subtitleLabel {{
            color: {c['text_secondary']};
            font-size: 14px;
        }}
        
        QLabel#mutedLabel {{
            color: {c['text_muted']};
            font-size: 13px;
        }}
        
        /* ==================== 分组框 ==================== */
        QGroupBox {{
            background-color: {c['bg_secondary']};
            border: 2px solid {c['border']};
            border-radius: 12px;
            margin-top: 20px;
            padding: 20px;
            font-weight: 600;
            font-size: 14px;
        }}
        
        QGroupBox:hover {{
            border-color: {c['border_accent']};
        }}
        
        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            left: 20px;
            padding: 0 12px;
            color: {c['text_primary']};
        }}
        
        /* ==================== 进度条 ==================== */
        QProgressBar {{
            background-color: {c['bg_tertiary']};
            border: none;
            border-radius: 10px;
            height: 12px;
            text-align: center;
            color: {c['text_primary']};
            font-weight: 600;
        }}
        
        QProgressBar::chunk {{
            background: {c['gradient_primary']};
            border-radius: 10px;
        }}
        
        /* ==================== 分割线 ==================== */
        QFrame[frameShape="4"], /* HLine */
        QFrame[frameShape="5"]  /* VLine */ {{
            color: {c['border']};
            background-color: {c['border']};
        }}
        
        /* ==================== 工具提示 ==================== */
        QToolTip {{
            background-color: {c['bg_glass_strong']};
            color: {c['text_primary']};
            border: 1px solid {c['border']};
            border-radius: 8px;
            padding: 10px 14px;
            font-size: 13px;
        }}
        
        /* ==================== 复选框和单选框 ==================== */
        QCheckBox, QRadioButton {{
            color: {c['text_primary']};
            spacing: 10px;
            font-size: 14px;
        }}
        
        QCheckBox::indicator, QRadioButton::indicator {{
            width: 20px;
            height: 20px;
            border-radius: 4px;
            border: 2px solid {c['border']};
            background-color: {c['bg_secondary']};
        }}
        
        QCheckBox::indicator:hover {{
            border-color: {c['accent']};
        }}
        
        QCheckBox::indicator:checked {{
            background-color: {c['accent']};
            border-color: {c['accent']};
            image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAiIGhlaWdodD0iMjAiIHZpZXdCb3g9IjAgMCAyMCAyMCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTE2LjUgNi41TDcuNSAxNS41TDMuNSAxMS41IiBzdHJva2U9IndoaXRlIiBzdHJva2Utd2lkdGg9IjIiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCIvPgo8L3N2Zz4K);
            border-radius: 4px;
        }}
        
        QCheckBox::indicator:unchecked {{
            background-color: {c['bg_secondary']};
            border-color: {c['border']};
            border-radius: 4px;
        }}
        
        QRadioButton::indicator {{
            border-radius: 10px;
        }}
        
        QRadioButton::indicator:checked {{
            background-color: {c['accent']};
            border-color: {c['accent']};
            image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAiIGhlaWdodD0iMjAiIHZpZXdCb3g9IjAgMCAyMCAyMCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPGNpcmNsZSBjeD0iMTAiIGN5PSIxMCIgcj0iNCIgZmlsbD0id2hpdGUiLz4KPC9zdmc+C);
        }}
        
        QRadioButton::indicator:unchecked {{
            background-color: {c['bg_secondary']};
            border-color: {c['border']};
        }}
        
        QRadioButton::indicator:hover {{
            border-color: {c['accent']};
        }}
        
            QWidget {{
                background-color: transparent;
                color: {c['text_primary']};
            }}
            
            QMainWindow, QDialog, GlassPanel {{
                background-color: {c['bg_primary']};
            }}

            QScrollArea, QScrollArea QWidget#qt_scrollarea_viewport {{
                background-color: transparent;
                border: none;
            }}
            
            QLabel {{
                background-color: transparent;
                color: {c['text_primary']};
            }}

            QComboBox QAbstractItemView {{
                background-color: {c['bg_secondary']};
                color: {c['text_primary']};
                border: 1px solid {c['border']};
                selection-background-color: {c['accent']};
                outline: none;
                border-radius: 8px;
            }}
            
            QTreeWidget {{
                background-color: {c['bg_secondary']};
                border: 1px solid {c['border']};
                border-radius: 8px;
                color: {c['text_primary']};
            }}
            
            QTreeWidget::item {{
                height: 36px;
                border-radius: 6px;
                margin: 2px 5px;
            }}
            
            QTreeWidget::item:hover {{
                background-color: {c['bg_tertiary']};
            }}
            
            QTreeWidget::item:selected {{
                background-color: {c['accent_glow']};
                color: {c['accent']};
                font-weight: bold;
            }}
            
            QHeaderView::section {{
                background-color: {c['bg_tertiary']};
                color: {c['text_muted']};
                padding: 10px;
                border: none;
                border-bottom: 1px solid {c['border']};
                font-weight: bold;
            }}

            QSplitter::handle {{
                background-color: {c['border']};
            }}
            
            QCheckBox {{
                spacing: 8px;
                color: {c['text_primary']};
                font-size: 13px;
            }}
            QCheckBox::indicator {{
                width: 20px;
                height: 20px;
                background-color: {c['bg_tertiary']};
                border: 1px solid {c['border']};
                border-radius: 5px;
            }}
            QCheckBox::indicator:hover {{
                border-color: {c['accent']};
                background-color: {c['accent_glow']};
            }}
            QCheckBox::indicator:checked {{
                background-color: {c['accent']};
                border-color: {c['accent']};
                image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTQiIGhlaWdodD0iMTQiIHZpZXdCb3g9IjAgMCAxNCAxNCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTIuNSA3TDYuNSAxMEwxMS41IDQiIHN0cm9rZT0id2hpdGUiIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIi8+Cjwvc3ZnPg==);
            }}
            QCheckBox::indicator:disabled {{
                background-color: {c['bg_secondary']};
                border-color: {c['bg_tertiary']};
            }}
        """


# 全局主题管理器实例
theme_manager = ThemeManager()
