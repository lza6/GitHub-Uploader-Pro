"""
GitHub Uploader Pro - 日志系统
提供统一的日志记录功能，支持控制台和文件输出
"""
import sys
from pathlib import Path
from loguru import logger
from typing import Callable, Optional

from .config import config


class LogManager:
    """日志管理器"""
    
    _instance: Optional['LogManager'] = None
    _initialized: bool = False
    
    def __new__(cls) -> 'LogManager':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self._ui_handler_id: Optional[int] = None
        self._ui_callback: Optional[Callable] = None
        self._setup_logger()
    
    def _setup_logger(self) -> None:
        """配置日志系统"""
        # 移除默认处理器
        logger.remove()
        
        # 获取日志级别
        log_level = config.get("log_level", "INFO")
        
        # 控制台输出（带颜色）
        logger.add(
            sys.stderr,
            level=log_level,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
                   "<level>{level: <8}</level> | "
                   "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
                   "<level>{message}</level>",
            colorize=True,
        )
        
        # 文件输出
        log_dir = config.config_dir / "logs"
        log_dir.mkdir(exist_ok=True)
        
        logger.add(
            log_dir / "app_{time:YYYY-MM-DD}.log",
            level="DEBUG",
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
            rotation="00:00",  # 每天轮换
            retention="7 days",  # 保留7天
            compression="zip",  # 压缩旧日志
            encoding="utf-8",
        )
        
        logger.info("日志系统初始化完成")
    
    def set_ui_callback(self, callback: Callable[[str, str, str], None]) -> None:
        """
        设置UI日志回调
        
        Args:
            callback: 回调函数，接收 (timestamp, level, message) 参数
        """
        # 移除旧的UI处理器
        if self._ui_handler_id is not None:
            logger.remove(self._ui_handler_id)
        
        self._ui_callback = callback
        
        def ui_sink(message):
            record = message.record
            timestamp = record["time"].strftime("%H:%M:%S")
            level = record["level"].name
            text = record["message"]
            if self._ui_callback:
                self._ui_callback(timestamp, level, text)
        
        self._ui_handler_id = logger.add(
            ui_sink,
            level="INFO",
            format="{message}",
        )
    
    def remove_ui_callback(self) -> None:
        """移除UI日志回调"""
        if self._ui_handler_id is not None:
            logger.remove(self._ui_handler_id)
            self._ui_handler_id = None
            self._ui_callback = None
    
    def set_level(self, level: str) -> None:
        """设置日志级别"""
        config.set("log_level", level)
        # 重新配置日志（简化处理，实际需要更新处理器）
        logger.info(f"日志级别已设置为: {level}")


# 全局日志管理器实例
log_manager = LogManager()

# 导出logger供其他模块使用
__all__ = ['logger', 'log_manager', 'LogManager']
