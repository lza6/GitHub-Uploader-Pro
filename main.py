"""
GitHub Uploader Pro v1.0
现代化的GitHub文件上传工具

功能特性:
- GitHub OAuth登录（Device Flow）
- 记住登录状态
- 选择上传文件夹
- 选择/创建目标仓库
- 实时终端日志输出
- 玻璃拟态UI设计
- 深色/浅色主题切换
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from loguru import logger


def main():
    """应用程序入口"""
    # 初始化日志
    from utils.logger import log_manager
    
    logger.info("=" * 50)
    logger.info("GitHub Uploader Pro v4.0 启动")
    logger.info("=" * 50)
    
    # 设置应用属性
    app_name = "GitHub Uploader Pro"
    
    # 启用高DPI支持 (必须在创建 QApplication 实例之前)
    from PyQt6.QtCore import Qt
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    # 创建应用
    app = QApplication(sys.argv)
    app.setApplicationName(app_name)
    app.setApplicationVersion("4.0.0") # 同步更新 V4 版本号
    app.setOrganizationName("GitHub Uploader")
    
    # 设置默认字体
    
    # 创建主窗口
    from ui.main_window import MainWindow
    window = MainWindow()
    window.show()
    
    logger.info("主窗口已显示")
    
    # 运行事件循环 (V4.6: Asyncio Support via qasync)
    import asyncio
    import qasync
    
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)
    
    with loop:
        exit_code = loop.run_forever()
    
    logger.info("应用程序退出")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
