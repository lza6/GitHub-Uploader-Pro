"""
GitHub Uploader Pro - 主窗口
应用程序主界面
"""
import sys
import os
import asyncio
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QFrame, QScrollArea, QSpacerItem,
    QSizePolicy, QCheckBox, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot, QThread, QObject
from PyQt6.QtGui import QIcon, QFont
from loguru import logger

from .theme_manager import theme_manager
from .widgets.glass_widgets import GlassPanel, GlassButton, SectionTitle, Divider
from .widgets.login_panel import LoginPanel
from .widgets.folder_picker import FolderPicker
from .widgets.repo_selector import RepoSelector
from .widgets.log_console import LogConsole
from .widgets.progress_panel import ProgressPanel
from core.upload_manager import upload_manager, UploadOptions, UploadProgress, UploadState
from core.github_client import github_client
from utils.config import config


class UploadWorker(QObject):
    """上传工作线程对象"""
    progress_updated = pyqtSignal(UploadProgress)
    log_message = pyqtSignal(str)
    finished = pyqtSignal()
    
    def __init__(self, options: UploadOptions):
        super().__init__()
        self._options = options
    
    def run(self):
        """执行上传"""
        upload_manager.set_progress_callback(self._on_progress)
        upload_manager.set_log_callback(self._on_log)
        upload_manager.start_upload(self._options)
    
    def _on_progress(self, progress: UploadProgress):
        self.progress_updated.emit(progress)
        if progress.state in (UploadState.COMPLETED, UploadState.FAILED, UploadState.CANCELLED):
            self.finished.emit()
    
    def _on_log(self, message: str):
        self.log_message.emit(message)


class MainWindow(QMainWindow):
    """
    主窗口
    GitHub Uploader Pro 的主界面
    """
    
    def __init__(self):
        super().__init__()
        self._upload_thread: QThread = None
        self._upload_worker: UploadWorker = None
        self._is_uploading = False
        
        self._setup_window()
        self._setup_ui()
        
        # V4.5: 零延迟启动 - 将重型初始化放到主循环开始后
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(100, self._deferred_init)

    def _deferred_init(self):
        """延迟初始化：确保窗口先显示，再同步数据 v4.5"""
        from utils.logger import log_manager
        log_manager.set_ui_callback(self._log_console.append_log)
        
        self._connect_signals()
        # 初始应用主题并建立响应式链路 (V4.2 Reactive)
        self._apply_theme()
        theme_manager.theme_changed.connect(lambda: self._apply_theme())
        
        # 确保初始文件夹触发必要的检测逻辑
        if self._folder_picker.folder_path:
            self._on_folder_selected(self._folder_picker.folder_path)
    
    def _setup_window(self):
        """设置窗口属性 (V4.5 Stream & Reactive)"""
        self.setWindowTitle("GitHub Uploader Pro v4.5 (Stream & Reactive)")
        self.setMinimumSize(1000, 800)
        self.resize(1350, 920)
        
        # 应用跨代主题
        self.setStyleSheet(theme_manager.get_stylesheet())
        
        # 恢复窗口位置
        geometry = config.get("window_geometry")
        if geometry:
            try:
                self.restoreGeometry(bytes.fromhex(geometry))
            except Exception:
                pass
    
    def _setup_ui(self):
        """设置UI v2.0 深度汉化版"""
        c = theme_manager.colors
        
        central = QWidget()
        self.setCentralWidget(central)
        
        # 全局水平布局 (侧边栏 + 内容区 + 预览面板)
        main_h_layout = QHBoxLayout(central)
        main_h_layout.setContentsMargins(0, 0, 0, 0)
        main_h_layout.setSpacing(0)
        
        # --- 侧边栏 (Sidebar) ---
        self._sidebar = QFrame()
        self._sidebar.setFixedWidth(70)
        sidebar_layout = QVBoxLayout(self._sidebar)
        sidebar_layout.setContentsMargins(10, 30, 10, 30)
        sidebar_layout.setSpacing(20)
        
        from .widgets.glass_widgets import IconButton
        # V4.2 明确指定侧边栏图标色，并采用 emoji 增强方案
        self._nav_home = IconButton("🏡", size=48); self._nav_home.setToolTip("首页")
        self._nav_staging = IconButton("📁", size=48); self._nav_staging.setToolTip("暂存区")
        self._nav_agent = IconButton("🤖", size=48); self._nav_agent.setToolTip("AI 助手")
        self._nav_settings = IconButton("🛠️", size=48); self._nav_settings.setToolTip("设置")
        
        sidebar_layout.addWidget(self._nav_home)
        sidebar_layout.addWidget(self._nav_staging)
        sidebar_layout.addWidget(self._nav_agent)
        sidebar_layout.addStretch()
        sidebar_layout.addWidget(self._nav_settings)
        
        main_h_layout.addWidget(self._sidebar)
        
        # --- 主内容区 + 预览面板 (使用分割器) ---
        from PyQt6.QtWidgets import QSplitter
        content_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # --- 内容区 (Stacked Content) ---
        self._content_stack = QWidget()
        self._stack_layout = QVBoxLayout(self._content_stack)
        self._stack_layout.setContentsMargins(30, 25, 30, 30)
        
        # 顶部标题栏
        top_bar = QHBoxLayout()
        self._page_title = QLabel("首页")
        self._page_title.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {c['text_primary']}; margin-bottom: 5px;")
        top_bar.addWidget(self._page_title)
        top_bar.addStretch()
        
        self._theme_btn = QPushButton("🌙" if theme_manager.current_theme == "dark" else "☀️")
        self._theme_btn.setFixedSize(40, 40)
        self._theme_btn.setStyleSheet(f"background: {c['bg_tertiary']}; border-radius: 20px; font-size: 18px;")
        self._theme_btn.clicked.connect(self._toggle_theme)
        top_bar.addWidget(self._theme_btn)
        
        self._stack_layout.addLayout(top_bar)
        self._stack_layout.addSpacing(10)
        
        # 各个面板容器
        from PyQt6.QtWidgets import QStackedWidget
        self._pages = QStackedWidget()
        
        # 1. 首页 (登录 + 文件夹 + 仓库)
        home_page = QScrollArea()
        home_page.setWidgetResizable(True)
        home_page.setStyleSheet("background: transparent; border: none;")
        home_content = QWidget()
        home_layout = QVBoxLayout(home_content)
        home_layout.setContentsMargins(0, 0, 10, 0)
        home_layout.setSpacing(25)
        
        self._login_panel = LoginPanel()
        home_layout.addWidget(self._login_panel)
        
        self._folder_picker = FolderPicker()
        home_layout.addWidget(self._folder_picker)
        
        self._repo_selector = RepoSelector()
        home_layout.addWidget(self._repo_selector)
        
        # 提交消息输入框
        commit_layout = QHBoxLayout()
        commit_label = QLabel("提交消息:")
        commit_label.setStyleSheet(f"color: {c['text_primary']}; font-weight: bold;")
        commit_layout.addWidget(commit_label)
        
        self._commit_input = QLineEdit()
        self._commit_input.setPlaceholderText("输入提交消息（可选）")
        self._commit_input.setStyleSheet(f"background: {c['bg_tertiary']}; border: 1px solid {c['border']}; border-radius: 6px; padding: 8px; color: {c['text_primary']};")
        commit_layout.addWidget(self._commit_input)
        home_layout.addLayout(commit_layout)
        
        # 选项复选框
        options_layout = QHBoxLayout()
        self._force_push_check = QCheckBox("强制推送")
        self._force_push_check.setStyleSheet(f"color: {c['text_primary']};")
        self._gitignore_check = QCheckBox("创建 .gitignore")
        self._gitignore_check.setChecked(True)
        self._gitignore_check.setStyleSheet(f"color: {c['text_primary']};")
        options_layout.addWidget(self._force_push_check)
        options_layout.addWidget(self._gitignore_check)
        home_layout.addLayout(options_layout)
        
        # 进度面板
        self._progress_panel = ProgressPanel()
        home_layout.addWidget(self._progress_panel)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        self._upload_btn = GlassButton("🚀 开始上传", primary=True)
        self._upload_btn.setMinimumHeight(50)
        self._upload_btn.clicked.connect(self._start_upload)
        button_layout.addWidget(self._upload_btn)
        
        self._cancel_btn = GlassButton("取消上传", primary=False)
        self._cancel_btn.setMinimumHeight(50)
        self._cancel_btn.setEnabled(False)
        self._cancel_btn.clicked.connect(self._cancel_upload)
        button_layout.addWidget(self._cancel_btn)
        
        home_layout.addLayout(button_layout)
        
        home_page.setWidget(home_content)
        self._pages.addWidget(home_page)
        
        # 2. 暂存区详情
        from .widgets.staging_viewer import StagingViewer
        self._staging_viewer = StagingViewer()
        self._pages.addWidget(self._staging_viewer)
        
        # 3. AI Agent
        from .widgets.agent_panel import AgentPanel
        self._agent_panel = AgentPanel()
        self._pages.addWidget(self._agent_panel)
        
        # 4. 设置
        from .widgets.settings_panel import SettingsPanel
        self._settings_panel = SettingsPanel()
        self._pages.addWidget(self._settings_panel)
        
        self._stack_layout.addWidget(self._pages)
        
        # 底部日志 (全局显示)
        self._log_console = LogConsole()
        self._log_console.setFixedHeight(220)
        self._stack_layout.addWidget(self._log_console)

        # 联动 AI Agent 信号到日志
        self._agent_panel.apply_ignore_rules.connect(self._on_ai_ignore_applied)
        
        # 将内容区添加到分割器
        content_splitter.addWidget(self._content_stack)
        
        # --- 预览面板 (右侧) ---
        from .widgets.preview_panel import PreviewPanel
        self._preview_panel = PreviewPanel()
        self._preview_panel.setFixedWidth(400)
        content_splitter.addWidget(self._preview_panel)
        
        # 设置分割器比例
        content_splitter.setStretchFactor(0, 2)
        content_splitter.setStretchFactor(1, 1)
        
        # 将分割器添加到主布局
        main_h_layout.addWidget(content_splitter)

    def _apply_theme(self):
        """执行全量主题应用 v4.2 (Nebula Reactive)"""
        c = theme_manager.colors
        
        # 1. 应用全局 QSS
        self.setStyleSheet(theme_manager.get_stylesheet())
        
        # 2. 刷新硬编码容器样式 (侧边栏背景与边框)
        self._sidebar.setStyleSheet(f"""
            QFrame {{
                background-color: {c['bg_secondary']}; 
                border-right: 1px solid {c['border']};
            }}
        """)
        
        # 3. 刷新特殊组件 (由于 QSS 优先级问题，对动态生成的 QSS 进行显式重置)
        self._page_title.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {c['text_primary']};")
        self._theme_btn.setStyleSheet(f"background: {c['bg_tertiary']}; border-radius: 20px; font-size: 18px; color: {c['text_primary']};")
        self._theme_btn.setText("🌙" if theme_manager.current_theme == "dark" else "☀️")
        self._theme_btn.setToolTip("切换日间/夜间模式")
        
        logger.debug("🎨 [THEME] 系统全量重绘完成")

    def _switch_page(self, index, title):
        self._pages.setCurrentIndex(index)
        self._page_title.setText(title)
        if index == 1: # 暂存区刷新
            self._staging_viewer.set_project_path(self._folder_picker.folder_path)
        elif index == 2: # AI Agent 路径同步
            self._agent_panel.set_project_path(self._folder_picker.folder_path)
    
    def _connect_signals(self):
        """连接信号 v4.2.3 [Interaction Fix]"""
        # 侧边栏导航
        self._nav_home.clicked.connect(lambda: self._switch_page(0, "首页"))
        self._nav_staging.clicked.connect(lambda: self._switch_page(1, "暂存区管理"))
        self._nav_agent.clicked.connect(lambda: self._switch_page(2, "AI 助手（测试版）"))
        self._nav_settings.clicked.connect(lambda: self._switch_page(3, "系统偏好设置"))
        
        # 登录状态变更
        self._login_panel.login_state_changed.connect(self._on_login_state_changed)
        
        # 文件夹选择
        self._folder_picker.folder_selected.connect(self._on_folder_selected)
        
        # 仓库选择
        self._repo_selector.repo_selected.connect(self._on_repo_selected)
        
        # 联动 AI 状态到日志
        self._agent_panel._status_label.windowTitleChanged.connect( # Using title as a proxy call or just direct logging
            lambda: self._log_console.log_debug(f"AI 状态变更: {self._agent_panel._status_label.text()}")
        )
    
    def _toggle_theme(self):
        """切换主题 v4.2 (通过 ThemeManager 广播)"""
        # 仅触发底层切换，UI 会通过信号自动刷新
        theme_manager.toggle_theme()
    
    @pyqtSlot(bool)
    def _on_login_state_changed(self, logged_in: bool):
        """登录状态变更"""
        if logged_in:
            self._repo_selector.refresh_repos()
            self._log_console.log_success(f"已登录: {self._login_panel.credential.username}")
        else:
            self._log_console.log_info("已登出")
    
    @pyqtSlot(str)
    def _on_folder_selected(self, path: str):
        """文件夹选择 (V4.8: 智能检测 .gitignore)"""
        self._log_console.log_info(f"已选择文件夹: {path}")
        
        # 智能检测 .gitignore
        ignore_file = os.path.join(path, ".gitignore")
        if os.path.exists(ignore_file):
            self._gitignore_check.setChecked(False)
            self._log_console.log_info("检测到已存在 .gitignore，已自动取消勾选创建选项")
        else:
            self._gitignore_check.setChecked(True)
            
        # 更新预览面板
        self._preview_panel.set_folder_path(path)
    
    @pyqtSlot(str)
    def _on_repo_selected(self, repo_name: str):
        """仓库选择回调 (联动预览面板)"""
        self._log_console.log_info(f"已选择仓库: {repo_name}")
        
        # 1. 立即更新预览面板的基础名称
        self._preview_panel.set_repo(repo_name, None)
        
        # 2. 异步获取详细信息以填充统计数据
        def _fetch_detail():
            try:
                repo = github_client.get_repo(repo_name)
                if repo:
                    return {
                        'description': repo.description,
                        'html_url': repo.html_url,
                        'created_at': repo.created_at.isoformat() if repo.created_at else "",
                        'updated_at': repo.updated_at.isoformat() if repo.updated_at else "",
                        'private': repo.private,
                        'size': repo.size,
                    }
            except Exception as e:
                logger.error(f"无法获取仓库详情: {e}")
            return None

        class DetailLoader(QThread):
            loaded = pyqtSignal(dict)
            def run(self):
                d = _fetch_detail()
                if d: self.loaded.emit(d)
        
        self._detail_loader = DetailLoader()
        self._detail_loader.loaded.connect(lambda info: self._preview_panel.set_repo(repo_name, info))
        self._detail_loader.start()
    
    @pyqtSlot(str)
    def _on_ai_ignore_applied(self, path: str):
        """AI 应用了新的 ignore 规则"""
        self._log_console.log_success(f"AI 助手已更新项目 .gitignore 规则")
        # 触发全量同步预览
        if self._folder_picker.folder_path:
            self._preview_panel.set_folder_path(self._folder_picker.folder_path)

    async def _verify_upload(self) -> bool:
        """上传前置校验 & 二次确认 (正式版功能)"""
        folder = self._folder_picker.folder_path
        ignore_file = os.path.join(folder, ".gitignore")
        
        # [V2 PRO] 全自动补全：如果缺失，则静默调用 AI/本地 补全
        if not os.path.exists(ignore_file):
            self._log_console.log_info("检测到项目缺失 .gitignore，正在由 AI 助手为您生成最佳配置...")
            from core.ignore_generator import ignore_generator
            success = await ignore_generator.generate_and_save(folder)
            if success:
                self._log_console.log_success("项目忽略文件已自动补全 (AI + 模板)")
                # 重新刷预览
                self._preview_panel.set_folder_path(folder)

        has_ignore = os.path.exists(ignore_file)
        
        self._log_console.log_info("⏳ 正在计算上传文件清单，请稍候...")
        
        # 将耗时计算移至线程池
        try:
            result = await asyncio.to_thread(self._calculate_upload_stats, folder)
        except Exception as e:
            self._log_console.log_error(f"计算文件清单失败: {e}")
            return False

        all_files, ignored_count, upload_size, total_files = result
        
        # 弹出确认窗口
        msg = f"<b>即将开始上传！</b><br><br>"
        msg += f"项目路径: <code style='color: #2196F3;'>{folder}</code><br>"
        msg += f"目标仓库: <code style='color: #4CAF50;'>{self._repo_selector.selected_repo}</code><br><br>"
        
        if has_ignore:
            msg += f"<span style='color: #FF9800;'>检测到 .gitignore 文件，已自动应用排除规则：</span><br>"
            if ignored_count >= 0:
                msg += f"- 排除文件数: <b>{ignored_count}</b> 个<br>"
            else:
                msg += f"- 排除文件数: <b>已自动跳过</b> (极速模式)<br>"
        else:
            msg += f"<span style='color: #f44336;'>未检测到 .gitignore，将上传所有非 .git 文件。</span><br>"
            
        msg += f"- 本次变更文件: <b>{len(all_files)}</b> 个 <span style='color:#666; font-size: small;'>(仅显示新增/修改)</span><br>"
        msg += f"- 仓库总文件数: <b>{total_files}</b> 个 <span style='color:#666; font-size: small;'>(预计同步后)</span><br>"
        msg += f"- 拟上传大小: <b>{upload_size/1024/1024:.2f} MB</b> (压缩后更小)<br>"
        msg += f"<span style='color: #888; font-size: small; font-style: italic;'>* 未变更的文件已在仓库中，无需重复上传</span><br><br>"
        msg += "是否确认执行上传？"
        
        reply = QMessageBox.question(
            self, "上传确认 (Official Preview)", msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )
        
        return reply == QMessageBox.StandardButton.Yes

    def _calculate_upload_stats(self, folder: str):
        """计算上传统计数据 (运行在工作线程)"""
        # V4.8 Optimization: Use GitStatusProvider instead of raw os.walk
        from core.git_status_provider import GitStatusProvider
        provider = GitStatusProvider(folder)
        
        logger.info(f"⚡ 开始快速扫描文件 (Git Mode): {folder}")
        
        # 1. 获取变更文件（Git Status）
        files_status = provider.get_detailed_status()
        
        # 2. 获取已追踪文件总数 (Git ls-files)
        tracked_count = provider.get_tracked_count()
        
        all_files = []
        upload_size = 0
        new_files_count = 0
        
        for f in files_status:
            all_files.append(f.display_name)
            upload_size += f.size
            if f.status == "??" or f.status == "A ": # Untracked or Added
                new_files_count += 1
            
        ignored_count = -1 
        
        # 估算项目总文件数 = 已追踪 + 新增 (简单估算, 不处理删除的情况)
        total_project_files = tracked_count + new_files_count
        
        return all_files, ignored_count, upload_size, total_project_files

    def _start_upload(self):
        """开始上传 (V2 Pro 异步增强)"""
        import asyncio
        asyncio.create_task(self._async_start_upload())

    async def _async_start_upload(self):
        """异步开始上传流程"""
        # 验证
        if not self._login_panel.is_logged_in:
            QMessageBox.warning(self, "提示", "请先登录 GitHub")
            return
        
        folder = self._folder_picker.folder_path
        if not folder:
            QMessageBox.warning(self, "提示", "请选择要上传的文件夹")
            return
        
        repo = self._repo_selector.selected_repo
        if not repo:
            QMessageBox.warning(self, "提示", "请选择目标仓库")
            return
        
        # 执行二次确认 (现在支持 AI 自动补全)
        if not await self._verify_upload():
            self._log_console.log_info("用户取消了上传确认")
            return

        commit_msg = self._commit_input.text().strip()
        if not commit_msg:
            commit_msg = "Update via GitHub Uploader Pro"
        
        # 准备上传选项
        options = UploadOptions(
            folder_path=folder,
            repo_full_name=repo,
            branch=self._repo_selector.selected_branch,
            commit_message=commit_msg,
            force_push=self._force_push_check.isChecked(),
            create_gitignore=self._gitignore_check.isChecked(),
        )
        
        # 更新UI状态
        self._is_uploading = True
        self._upload_btn.setEnabled(False)
        self._cancel_btn.setEnabled(True)
        self._progress_panel.reset()
        
        # 创建工作线程
        self._upload_thread = QThread()
        self._upload_worker = UploadWorker(options)
        self._upload_worker.moveToThread(self._upload_thread)
        
        # 连接信号
        self._upload_thread.started.connect(self._upload_worker.run)
        self._upload_worker.progress_updated.connect(self._on_upload_progress)
        self._upload_worker.log_message.connect(self._on_upload_log)
        self._upload_worker.finished.connect(self._on_upload_finished)
        
        # 启动线程
        self._upload_thread.start()
        
        self._log_console.log_info("开始上传...")
    
    def _cancel_upload(self):
        """取消上传"""
        upload_manager.cancel_upload()
        self._log_console.log_warning("上传已取消")
    
    @pyqtSlot(UploadProgress)
    def _on_upload_progress(self, progress: UploadProgress):
        """上传进度更新"""
        self._progress_panel.update_progress(progress)
        
        if progress.state == UploadState.COMPLETED:
            self._log_console.log_success("上传完成！")
            # V4.7.1: 上传成功后联动预览面板刷新状态
            self._preview_panel.refresh_after_upload()
        elif progress.state == UploadState.FAILED:
            self._log_console.log_error(f"上传失败: {progress.error}")
    
    @pyqtSlot(str)
    def _on_upload_log(self, message: str):
        """上传日志"""
        # 解析日志级别
        if message.startswith("✓") or "成功" in message or "完成" in message:
            self._log_console.log_success(message)
        elif message.startswith("⚠️") or "警告" in message:
            self._log_console.log_warning(message)
        elif message.startswith("❌") or "失败" in message or "错误" in message:
            self._log_console.log_error(message)
        elif message.startswith("$"):
            self._log_console.log_debug(message)
        else:
            self._log_console.log_info(message)
    
    @pyqtSlot()
    def _on_upload_finished(self):
        """上传完成"""
        self._is_uploading = False
        self._upload_btn.setEnabled(True)
        self._cancel_btn.setEnabled(False)
        
        # 清理线程
        if self._upload_thread:
            self._upload_thread.quit()
            self._upload_thread.wait()
            self._upload_thread = None
            self._upload_worker = None
    
    def closeEvent(self, event):
        """窗口关闭事件"""
        # 保存窗口位置
        config.set("window_geometry", self.saveGeometry().toHex().data().decode())
        
        # 取消正在进行的上传
        if self._is_uploading:
            upload_manager.cancel_upload()
        
        event.accept()
