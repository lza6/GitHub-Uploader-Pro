"""
GitHub Uploader Pro - 仓库选择器
选择或创建GitHub仓库
"""
from typing import List, Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QDialog, QLineEdit, QCheckBox, QRadioButton, QButtonGroup,
    QPushButton, QScrollArea, QTextEdit, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QThread
from loguru import logger

from .glass_widgets import GlassPanel, SectionTitle, IconButton
from ..theme_manager import theme_manager
from core.github_client import github_client, RepoInfo, CreateRepoOptions


class CreateRepoDialog(QDialog):
    """创建仓库对话框 (V4.7 增强型)"""
    
    repo_created = pyqtSignal(RepoInfo)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        theme_manager.theme_changed.connect(self._setup_ui)
        self._load_templates()
    
    def _setup_ui(self):
        """设置UI (响应式布局)"""
        c = theme_manager.colors
        
        self.setWindowTitle("创建新仓库")
        self.setMinimumSize(450, 500)
        self.resize(500, 600)
        self.setStyleSheet(f"background-color: {c['bg_primary']};")
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(f"background: transparent;")
        main_layout.addWidget(scroll)
        
        container = QWidget()
        container.setStyleSheet(f"background: transparent;")
        layout = QVBoxLayout(container)
        layout.setSpacing(15)
        layout.setContentsMargins(25, 25, 25, 25)
        scroll.setWidget(container)
        
        # 标题
        title = QLabel("📦 创建新仓库")
        title.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {c['text_primary']};")
        layout.addWidget(title)
        
        # 仓库名称
        layout.addWidget(QLabel("仓库名称 *", styleSheet=f"color: {c['text_secondary']};"))
        self._name_input = QLineEdit()
        self._name_input.setPlaceholderText("my-awesome-project")
        self._apply_input_style(self._name_input)
        layout.addWidget(self._name_input)
        
        # 描述
        layout.addWidget(QLabel("描述（可选）", styleSheet=f"color: {c['text_secondary']};"))
        self._desc_input = QTextEdit()
        self._desc_input.setPlaceholderText("简短描述您的项目...")
        self._desc_input.setMaximumHeight(80)
        self._apply_input_style(self._desc_input)
        layout.addWidget(self._desc_input)
        
        # .gitignore 模板
        layout.addWidget(QLabel(".gitignore 模板", styleSheet=f"color: {c['text_secondary']};"))
        self._gitignore_combo = QComboBox()
        self._gitignore_combo.addItem("无", None)
        self._apply_input_style(self._gitignore_combo)
        layout.addWidget(self._gitignore_combo)
        
        # License 模板
        layout.addWidget(QLabel("开源协议 (License)", styleSheet=f"color: {c['text_secondary']};"))
        self._license_combo = QComboBox()
        self._license_combo.addItem("无", None)
        self._apply_input_style(self._license_combo)
        layout.addWidget(self._license_combo)
        
        # 可见性
        layout.addWidget(QLabel("可见性", styleSheet=f"color: {c['text_secondary']};"))
        visibility_layout = QHBoxLayout()
        self._public_radio = QRadioButton("🌐 公开")
        self._public_radio.setChecked(True)
        self._public_radio.setStyleSheet(f"color: {c['text_primary']};")
        self._private_radio = QRadioButton("🔒 私有")
        self._private_radio.setStyleSheet(f"color: {c['text_primary']};")
        visibility_layout.addWidget(self._public_radio)
        visibility_layout.addWidget(self._private_radio)
        visibility_layout.addStretch()
        layout.addLayout(visibility_layout)
        
        # 自动初始化
        self._auto_init_check = QCheckBox("使用 README 初始化仓库")
        self._auto_init_check.setStyleSheet(f"color: {c['text_secondary']};")
        layout.addWidget(self._auto_init_check)
        
        layout.addStretch()
        
        # 底部按钮
        btn_layout = QHBoxLayout()
        cancel_btn = QPushButton("取消")
        self._apply_btn_style(cancel_btn, is_accent=False)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        create_btn = QPushButton("创建仓库")
        self._apply_btn_style(create_btn, is_accent=True)
        create_btn.clicked.connect(self._create_repo)
        btn_layout.addWidget(create_btn)
        layout.addLayout(btn_layout)

    def _apply_input_style(self, widget):
        c = theme_manager.colors
        widget.setStyleSheet(f"""
            background-color: {c['bg_secondary']};
            color: {c['text_primary']};
            border: 1px solid {c['border']};
            border-radius: 8px;
            padding: 8px;
        """)

    def _apply_btn_style(self, btn, is_accent=False):
        c = theme_manager.colors
        bg = c['accent'] if is_accent else c['bg_tertiary']
        hover = c['accent_hover'] if is_accent else c['border']
        text = "white" if is_accent else c['text_primary']
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg};
                color: {text};
                border: none;
                border-radius: 8px;
                padding: 10px 25px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: {hover}; }}
        """)

    def _load_templates(self):
        """异步加载模板列表"""
        def _target():
            gitignores = github_client.get_gitignore_templates()
            licenses = github_client.get_license_templates()
            return gitignores, licenses

        class Loader(QThread):
            loaded = pyqtSignal(list, list)
            def run(self):
                g, l = _target()
                self.loaded.emit(g, l)

        self._template_loader = Loader()
        self._template_loader.loaded.connect(self._on_templates_loaded)
        self._template_loader.start()

    def _on_templates_loaded(self, gitignores, licenses):
        for g in gitignores: self._gitignore_combo.addItem(g, g)
        for l in licenses: self._license_combo.addItem(l['name'], l['key'])

    def _create_repo(self):
        name = self._name_input.text().strip()
        if not name: return
        
        options = CreateRepoOptions(
            name=name,
            description=self._desc_input.toPlainText().strip(),
            private=self._private_radio.isChecked(),
            auto_init=self._auto_init_check.isChecked(),
            gitignore_template=self._gitignore_combo.currentData(),
            license_template=self._license_combo.currentData()
        )
        
        repo = github_client.create_repo(options)
        if repo:
            self.repo_created.emit(repo)
            self.accept()
class RepoLoaderThread(QThread):
    """仓库加载工作线程 - V4.5 流式增强版"""
    finished = pyqtSignal(list)
    chunk_loaded = pyqtSignal(list)  # 增量块加载信号
    error = pyqtSignal(str)

    def __init__(self, limit=500, chunk_size=50):
        super().__init__()
        self.limit = limit
        self.chunk_size = chunk_size

    def run(self):
        try:
            if not github_client.is_connected:
                github_client.reconnect()
            
            all_repos = []
            page = 1
            while len(all_repos) < self.limit:
                repos = github_client.get_repos(limit=self.chunk_size, page=page)
                if not repos: 
                    if page == 1: # 首屏没加载到，可能需要特殊处理
                        logger.warning("首屏未获取到仓库，请检查 Token 权限")
                    break
                
                all_repos.extend(repos)
                self.chunk_loaded.emit(repos)
                page += 1
                self.msleep(10)
                
            if not all_repos:
                logger.info("仓库列表为空，可能账户下尚无仓库")
            self.finished.emit(all_repos)
        except Exception as e:
            logger.error(f"流式加载仓库失败: {e}")
            self.error.emit(str(e))

class BranchLoaderThread(QThread):
    """分支加载工作线程 - 解决 UI 卡死核心组件"""
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, full_name: str):
        super().__init__()
        self.full_name = full_name

    def run(self):
        try:
            branches = github_client.get_branches(self.full_name)
            self.finished.emit(branches)
        except Exception as e:
            logger.error(f"加载分支失败: {e}")
            self.error.emit(str(e))

class RepoSelector(GlassPanel):
    """
    仓库选择器
    选择现有仓库或创建新仓库 (V4.6 性能增强版)
    """
    
    repo_selected = pyqtSignal(str)  # 选择的仓库全名
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._all_repos: List[RepoInfo] = []
        self._selected_repo: Optional[str] = None
        self._loader_thread = None
        self._branch_thread = None
        self._setup_ui()
        # 响应主题变更
        theme_manager.theme_changed.connect(self._setup_ui)
        # 自动刷新仓库列表
        self._auto_refresh()
    
    def _setup_ui(self):
        """设置UI (V4.6 引入搜索与异步链路)"""
        c = theme_manager.colors
        
        if not self.layout():
            layout = QVBoxLayout(self)
            self._main_layout = layout
        else:
            layout = self.layout()
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
                    
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 标题行
        header = QHBoxLayout()
        title = SectionTitle("📦", "目标仓库")
        header.addWidget(title)
        
        # 搜索框
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("🔍 快速搜索仓库...")
        self._search_input.setFixedWidth(180)
        self._search_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {c['bg_tertiary']};
                color: {c['text_primary']};
                border: 1px solid {c['border']};
                border-radius: 12px;
                padding: 4px 10px;
                font-size: 11px;
            }}
            QLineEdit:focus {{
                border-color: {c['accent']};
            }}
        """)
        self._search_input.textChanged.connect(self._filter_repos)
        header.addWidget(self._search_input)
        
        # 刷新按钮
        refresh_btn = IconButton("🔄", size=28)
        refresh_btn.setToolTip("快速刷新 GitHub 仓库列表")
        refresh_btn.clicked.connect(self.refresh_repos)
        header.addWidget(refresh_btn)
        
        # 新建按钮
        create_btn = IconButton("➕", size=28)
        create_btn.setToolTip("在当前账户下新建 GitHub 仓库")
        create_btn.clicked.connect(self._show_create_dialog)
        header.addWidget(create_btn)
        
        layout.addLayout(header)
        
        # 仓库下拉框
        self._combo = QComboBox()
        self._combo.setMinimumHeight(40)
        self._combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {c['bg_secondary']};
                color: {c['text_primary']};
                border: 1px solid {c['border']};
                border-radius: 8px;
                padding: 10px;
            }}
            QComboBox:hover {{
                border-color: {c['accent']};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 30px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {c['bg_secondary']};
                color: {c['text_primary']};
                border: 1px solid {c['border']};
                selection-background-color: {c['accent']};
            }}
        """)
        self._combo.currentIndexChanged.connect(self._on_selection_changed)
        layout.addWidget(self._combo)
        
        # 仓库信息
        self._info_label = QLabel("选择一个仓库或创建新仓库")
        self._info_label.setStyleSheet(f"color: {c['text_muted']}; font-size: 11px;")
        self._info_label.setWordWrap(True)
        layout.addWidget(self._info_label)
        
        # 分支选择区
        branch_container = QHBoxLayout()
        
        branch_label = QLabel("分支:")
        branch_label.setStyleSheet(f"color: {c['text_secondary']}; font-size: 12px;")
        branch_container.addWidget(branch_label)
        
        self._branch_combo = QComboBox()
        self._branch_combo.setFixedWidth(150)
        self._branch_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {c['bg_primary']};
                color: {c['text_primary']};
                border: 1px solid {c['border']};
                border-radius: 6px;
                padding: 5px 10px;
            }}
        """)
        branch_container.addWidget(self._branch_combo)
        
        # 加载中的微标
        self._branch_loading_label = QLabel("⌛")
        self._branch_loading_label.hide()
        branch_container.addWidget(self._branch_loading_label)
        
        branch_container.addStretch()
        layout.addLayout(branch_container)
    
    def _auto_refresh(self):
        """自动刷新仓库列表"""
        QTimer.singleShot(100, self.refresh_repos)
    
    def refresh_repos(self):
        """异步流式刷新仓库列表"""
        if self._loader_thread and self._loader_thread.isRunning():
            return
            
        self._info_label.setText("🌊 正在同步 GitHub 仓库 (首批)...")
        self._info_label.setStyleSheet("color: #58a6ff; font-size: 11px; font-weight: bold;")
        
        self._all_repos = []
        self._combo.clear()
        self._combo.addItem("-- 同步中... --", None)
        self._combo.setEnabled(False)
        
        self._loader_thread = RepoLoaderThread(limit=500, chunk_size=50)
        self._loader_thread.chunk_loaded.connect(self._on_chunk_loaded)
        self._loader_thread.finished.connect(self._on_repos_finished)
        self._loader_thread.error.connect(self._on_load_error)
        self._loader_thread.start()

    def _on_chunk_loaded(self, chunk: List[RepoInfo]):
        """增量块加载成功"""
        if not self._all_repos:
            self._combo.clear()
            self._combo.addItem("-- 请选择仓库 --", None)
            self._combo.setEnabled(True)

        self._all_repos.extend(chunk)
        self._refresh_combo_items(self._all_repos)
        self._info_label.setText(f"🚀 已实时同步 {len(self._all_repos)} 个仓库...")

    def _on_repos_finished(self, all_repos: List[RepoInfo]):
        """全量加载完成"""
        self._info_label.setText(f"✅ 同步完成 (共 {len(self._all_repos)} 个)")
        self._info_label.setStyleSheet(f"color: {theme_manager.colors['text_muted']}; font-size: 11px;")
        
        # 恢复选择
        if self._selected_repo:
            index = self._combo.findData(self._selected_repo)
            if index >= 0:
                self._combo.setCurrentIndex(index)

    def _on_load_error(self, error_msg):
        """加载失败"""
        self._combo.setEnabled(True)
        self._info_label.setText(f"❌ 刷新失败: {error_msg}")
        self._info_label.setStyleSheet("color: #f85149; font-size: 11px;")

    def _filter_repos(self, text):
        """根据搜索文本过滤仓库"""
        if not text:
            self._refresh_combo_items(self._all_repos)
        else:
            filtered = [r for r in self._all_repos if text.lower() in r.full_name.lower()]
            self._refresh_combo_items(filtered)

    def _refresh_combo_items(self, repos: List[RepoInfo]):
        """刷新下拉框列表项"""
        # 记住当前选择的值，以便刷新后恢复（如果搜索结果里还有它）
        current_val = self._combo.currentData()
        
        self._combo.blockSignals(True)
        self._combo.clear()
        self._combo.addItem("-- 请选择仓库 --", None)
        for repo in repos:
            icon = "🔒" if repo.private else "📂"
            self._combo.addItem(f"{icon} {repo.full_name}", repo.full_name)
        
        if current_val:
            idx = self._combo.findData(current_val)
            if idx >= 0: self._combo.setCurrentIndex(idx)
        self._combo.blockSignals(False)

    def _on_selection_changed(self, index: int):
        """选择变更 (核心：触发异步分支加载)"""
        full_name = self._combo.currentData()
        if not full_name:
            self._selected_repo = None
            self._info_label.setText("选择一个仓库或创建新仓库")
            return

        self._selected_repo = full_name
        repo = next((r for r in self._all_repos if r.full_name == full_name), None)
        if repo:
            desc = repo.description or "无描述"
            self._info_label.setText(f"ℹ️ {desc}\n🔗 {repo.html_url}")
        
        # 启动异步分支加载，防止主线程卡死
        self._async_load_branches(full_name)
        self.repo_selected.emit(full_name)

    def _async_load_branches(self, full_name: str):
        """异步加载分支"""
        # 停止旧线程
        if self._branch_thread and self._branch_thread.isRunning():
            self._branch_thread.terminate()
            self._branch_thread.wait()

        self._branch_combo.clear()
        self._branch_combo.addItem("正在加载...")
        self._branch_combo.setEnabled(False)
        self._branch_loading_label.show()

        self._branch_thread = BranchLoaderThread(full_name)
        self._branch_thread.finished.connect(self._on_branches_loaded)
        self._branch_thread.error.connect(self._on_branches_error)
        self._branch_thread.start()

    def _on_branches_loaded(self, branches: List[str]):
        """分支加载成功回调"""
        self._branch_combo.clear()
        if branches:
            self._branch_combo.addItems(branches)
        else:
            self._branch_combo.addItem("main")
        self._branch_combo.setEnabled(True)
        self._branch_loading_label.hide()

    def _on_branches_error(self, err):
        """分支加载失败回调"""
        self._branch_combo.clear()
        self._branch_combo.addItem("加载失败")
        self._branch_loading_label.hide()
        logger.error(f"UI端加载分支失败: {err}")

    def _show_create_dialog(self):
        """创建仓库对话框"""
        dialog = CreateRepoDialog(self.window())
        dialog.repo_created.connect(self._on_repo_created)
        dialog.exec()

    def _on_repo_created(self, repo: RepoInfo):
        """仓库创建完成"""
        self._all_repos.insert(0, repo)
        self._refresh_combo_items(self._all_repos)
        idx = self._combo.findData(repo.full_name)
        if idx >= 0: self._combo.setCurrentIndex(idx)

    @property
    def selected_repo(self) -> Optional[str]:
        return self._selected_repo

    @property
    def selected_branch(self) -> str:
        txt = self._branch_combo.currentText()
        return txt if txt and txt != "正在加载..." and txt != "加载失败" else "main"

