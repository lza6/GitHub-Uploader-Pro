"""
GitHub Uploader Pro - 实时预览面板 v2.0
预渲染仓库样式和文件结构
"""
from typing import List, Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
    QFrame, QPushButton, QTreeWidget, QTreeWidgetItem, QSplitter
)
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot, QFileSystemWatcher, QTimer
from PyQt6.QtGui import QFont, QColor, QDesktopServices
from PyQt6.QtCore import QUrl
import os
from pathlib import Path
from loguru import logger
from core.github_client import github_client
from PyQt6.QtCore import QThread, pyqtSlot, pyqtSignal

from .glass_widgets import GlassPanel, GlassButton, SectionTitle, Card
from ..theme_manager import theme_manager
from core.git_status_provider import GitStatusProvider


class PreviewWorker(QThread):
    """文件同步预览工作线程 v4.7.2 [Recursive & Comprehensive]"""
    item_detected = pyqtSignal(dict)  # 发射单个条目信息
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, repo_full_name: str, folder_path: str):
        super().__init__()
        self.repo_full_name = repo_full_name
        self.folder_path = folder_path

    def run(self):
        try:
            # 1. 获取远程文件列表 (平铺)
            remote_contents = {}
            if self.repo_full_name:
                try:
                    repo = github_client.get_repo(self.repo_full_name)
                    # 递归获取远程内容可能很慢，这里暂时只对比顶层或常用的
                    remote_contents = {c.path: c for c in repo.get_contents("")}
                except Exception as re:
                    logger.warning(f"无法获取远程内容: {re}")

            # 2. 递归获取本地文件列表
            local_items = {}
            ignore_provider = None
            if self.folder_path and os.path.exists(self.folder_path):
                ignore_provider = GitStatusProvider(self.folder_path)
                
                # V4.8.1 Perf Fix: 使用 topdown=True 进行目录剪枝，避免遍历 venv/node_modules
                for root, dirs, filenames in os.walk(self.folder_path, topdown=True):
                    # 1. 快速排除常见大目录 (硬编码加速)
                    for ignore_dir in ['.git', '__pycache__', 'venv', 'env', 'node_modules', 'dist', 'build', '.idea', '.vscode']:
                        if ignore_dir in dirs:
                            dirs.remove(ignore_dir)
                    
                    # 2. 使用 git check-ignore 进一步剪枝剩余目录
                    # 注意：为了性能，我们只对第一层或少量目录做这个检查，避免每个子目录都 spawn 进程
                    # 这里做一个简单的优化：如果目录深度太深，就不检查目录本身的 ignore 了，反正文件名也会检查
                    # 或者，只对非隐藏目录且不在硬编码列表里的目录做检查
                    
                    # V4.8.1: 安全起见，我们先只用硬编码排除。
                    # 如果需要更精准的目录排除，应该批量调用 git check-ignore，但现在先解决卡死问题。
                    # 为了完全解决问题，我们遍历 dirs copy
                    for d in list(dirs):
                         d_path = os.path.join(root, d)
                         rel_d_path = os.path.relpath(d_path, self.folder_path).replace("\\", "/")
                         if ignore_provider.is_ignored(rel_d_path + "/"):
                             dirs.remove(d)

                    for name in dirs + filenames:
                        abs_path = os.path.join(root, name)
                        rel_path = os.path.relpath(abs_path, self.folder_path).replace("\\", "/")
                        
                        # 文件级别的检查
                        # V4.8.1: 如果父目录已经被排除（上面的逻辑），这里就不会进来了
                        # 但对于 filenames，我们需要检查
                        if name in filenames:
                            is_ignored = ignore_provider.is_ignored(rel_path)
                            if is_ignored: continue # 如果忽略，直接跳过，不在列表中显示（或者显示为忽略状态，看设计）
                            # 根据旧逻辑，似乎是想要显示并标记为忽略？
                            # 原代码: local_items[...] = { ... "is_ignored": is_ignored }
                            # 如果我们想要显示 "Ignored" 状态的文件，就不能 continue
                            # 但是为了性能，对于 venv 这种巨大的文件夹，我们必须在 dirs 级别就 prune 掉，否则几十万个文件即使只是 loop 也会卡
                            # 所以：被 prune 的文件夹里的文件根本不会出现在这里 -> 正确
                            # 对于由于规则忽略的单个文件（非文件夹排除），我们保留显示
                            
                            local_items[rel_path] = {
                                "type": 'dir' if os.path.isdir(abs_path) else 'file',
                                "size": os.path.getsize(abs_path) if os.path.isfile(abs_path) else 0,
                                "rel_path": rel_path,
                                "is_ignored": is_ignored
                            }
                        else:
                             # 目录（未被 prune 的）
                             local_items[rel_path] = {
                                "type": 'dir',
                                "size": 0,
                                "rel_path": rel_path,
                                "is_ignored": False
                            }

            # 3. 合并逻辑
            all_paths = sorted(list(set(remote_contents.keys()) | local_items.keys()), key=lambda x: x.lower())
            
            for path in all_paths:
                is_remote = path in remote_contents
                is_local = path in local_items
                
                name = os.path.basename(path)
                res = {"name": name, "path": path, "is_remote": is_remote, "is_local": is_local}
                
                if is_local:
                    res.update(local_items[path])
                elif is_remote:
                    obj = remote_contents[path]
                    res.update({
                        "type": obj.type,
                        "size": obj.size if obj.type == 'file' else 0,
                        "remote_obj": obj
                    })
                
                self.item_detected.emit(res)
                self.msleep(2)
                
            self.finished.emit()
        except Exception as e:
            logger.exception("预览线程崩溃")
            self.error.emit(str(e))

class FileTreeWidget(QTreeWidget):
    """
    文件树组件
    展示上传文件的目录结构
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._items_cache = {} # path -> item
        self._watcher = QFileSystemWatcher()
        self._watcher.directoryChanged.connect(self._on_local_change)
        self._watcher.fileChanged.connect(self._on_local_change)
        self._last_folder = None
        
        self._setup_ui()
        theme_manager.theme_changed.connect(self._setup_ui)
    
    def _setup_ui(self):
        """设置UI (V4.8: 布局优化与视觉增强)"""
        c = theme_manager.colors
        
        self.setHeaderLabels(["文件名", "大小", "状态 (Local vs Remote)"])
        self.setAlternatingRowColors(True)
        self.setIndentation(24) # 增加缩进，层次更鲜明
        self.setAnimated(True)
        
        # 设置列宽和自适应模式
        header = self.header()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, header.ResizeMode.ResizeToContents) # 文件名自适应内容，确保不截断
        header.setSectionResizeMode(1, header.ResizeMode.Fixed)   # 大小固定
        header.setSectionResizeMode(2, header.ResizeMode.Fixed)   # 状态固定
        
        self.setColumnWidth(1, 100)
        self.setColumnWidth(2, 220) # 增加宽度以容纳更长的状态文本
        
        self.setStyleSheet(f"""
            QTreeWidget {{
                background-color: {c['bg_secondary']};
                color: {c['text_primary']};
                border: 1px solid {c['border']};
                border-radius: 12px;
                font-size: 14px;
                outline: none;
            }}
            QTreeWidget::item {{
                padding: 10px;
                border-radius: 6px;
                margin: 2px 5px;
            }}
            QTreeWidget::item:hover {{
                background-color: {c['bg_tertiary']};
            }}
            QTreeWidget::item:selected {{
                background-color: {c['accent']}40; /* 选中的柔和背景 */
                color: {c['accent']};
                font-weight: 500;
            }}
            QTreeWidget::header {{
                background-color: {c['bg_tertiary']};
                color: {c['text_secondary']};
                border: none;
                border-bottom: 2px solid {c['border']};
                padding: 10px;
                font-weight: bold;
                font-size: 13px;
                text-transform: uppercase;
            }}
            QTreeWidget::branch {{
                background-color: transparent;
            }}
            /* 自定义滚动条样式 */
            QScrollBar:vertical {{
                background: transparent;
                width: 8px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: {c['border']};
                min-height: 20px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {c['text_muted']};
            }}
        """)
    
    def load_folder(self, folder_path: str):
        """加载文件夹"""
        self.clear()
        self._items_cache = {}
        
        if not folder_path or not os.path.exists(folder_path):
            return
        
        try:
            self._add_items(None, Path(folder_path))
            self.expandAll()
        except Exception as e:
            logger.error(f"加载文件夹失败: {e}")

    def load_remote_repo(self, repo_full_name: str, path: str = ""):
        """加载远程仓库内容 v4.1"""
        self.clear()
        self._items_cache = {}
        if not repo_full_name:
            return
            
        try:
            repo = github_client.get_repo(repo_full_name)
            if not repo: return
            
            contents = repo.get_contents(path)
            # 排序：文件夹在前
            items = sorted(contents, key=lambda x: (x.type != 'dir', x.name.lower()))
            
            for content in items:
                item = QTreeWidgetItem(self)
                icon = "📁" if content.type == 'dir' else self._get_file_icon(content.name)
                size = self._format_size(content.size) if content.type == 'file' else "-"
                
                item.setText(0, f"{icon} {content.name}")
                item.setText(1, size)
                item.setText(2, "文件夹" if content.type == 'dir' else self._get_file_type(content.name))
                item.setData(0, Qt.ItemDataRole.UserRole, content)
                
            logger.info(f"远程内容加载完成: {repo_full_name}/{path}")
        except Exception as e:
            logger.error(f"加载远程仓库失败: {e}")
            item = QTreeWidgetItem(self)
            item.setText(0, "⚠️ 无法获取远程内容")
    
    @pyqtSlot(str, str)
    def sync_preview(self, repo_full_name: str, folder_path: str):
        """异步 V4.7.2: 递归流水同步 [Recursive Support]"""
        if hasattr(self, "_worker") and self._worker.isRunning():
            self._worker.terminate()
            self._worker.wait()
            
        self.clear()
        self._items_cache = {}
        
        # V4.5.1: 添加加载动态占位符
        loading_item = QTreeWidgetItem(self)
        loading_item.setText(0, "⌛ 正在拉取文件架构...")
        loading_item.setForeground(0, theme_manager.get_color_obj('accent'))
        
        self._worker = PreviewWorker(repo_full_name, folder_path)
        self._worker.item_detected.connect(self._on_item_detected)
        self._worker.finished.connect(self._on_sync_finished)
        self._worker.start()

    def _on_sync_finished(self):
        """同步完成清理"""
        if self.topLevelItemCount() > 0:
            first = self.topLevelItem(0)
            if first and "正在拉取" in first.text(0):
                self.takeTopLevelItem(0)
                
        # 自动展开一级目录
        for i in range(self.topLevelItemCount()):
            it = self.topLevelItem(i)
            if it.text(0).startswith("📁"):
                it.setExpanded(True)

        logger.info(f"预览同步完成")

    def _on_item_detected(self, data: dict):
        """流式条目渲染 (支持递归层级 v4.7.2)"""
        full_path = data.get("path", "")
        name = data.get("name", "Unknown")
        parent_path = os.path.dirname(full_path).replace("\\", "/")
        
        # 查找或创建父节点
        parent_item = self if not parent_path else self._items_cache.get(parent_path)
        if not parent_item and parent_path:
            parent_item = self

        item = QTreeWidgetItem(parent_item)
        self._items_cache[full_path] = item
        
        accent_green = QColor(63, 185, 80) # GitHub 风格绿色
        
        icon = "📁" if data.get("type") == 'dir' else self._get_file_icon(name)
        item.setText(0, f"{icon} {name}")
        item.setText(1, self._format_size(data.get("size", 0)) if data.get("type") == 'file' else "-")
        
        is_just_uploaded = data.get("is_just_uploaded", False)
        is_remote = data.get("is_remote", False)
        is_local = data.get("is_local", False)
        is_ignored = data.get("is_ignored", False)
        
        if is_just_uploaded:
            item.setText(2, "✅ 上传完成 (已同步)")
            item.setForeground(0, accent_green)
            item.setForeground(2, accent_green)
        elif is_ignored:
            item.setText(2, "🚫 [已忽略] .gitignore 规则匹配")
            red_color = QColor(255, 68, 68) # 鲜艳的红色
            item.setForeground(0, red_color)
            item.setForeground(1, red_color)
            item.setForeground(2, red_color)
            
            # 设置斜体
            font = item.font(0)
            font.setItalic(True)
            item.setFont(0, font)
            item.setFont(2, font)
        elif is_remote and is_local:
            item.setText(2, "🔄 [本地/远程] 已同步")
            item.setForeground(2, theme_manager.get_color_obj('text_muted'))
        elif is_remote:
            item.setText(2, "🌐 [仅远程] 保持原样")
            item.setForeground(2, theme_manager.get_color_obj('text_secondary'))
        else: # 只有本地有 -> 待上传
            item.setText(2, "✨ [本地] 准备上传")
            item.setForeground(0, accent_green)
            item.setForeground(2, accent_green)
            font = item.font(0)
            font.setBold(True)
            item.setFont(0, font)
            item.setFont(2, font)
        
        # 优化对齐
        item.setTextAlignment(1, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        item.setTextAlignment(2, Qt.AlignmentFlag.AlignCenter)

    def mark_all_synced(self):
        """手动将所有待上传项标记为已同步 (UI 优化)"""
        for i in range(self.topLevelItemCount()):
            self._mark_item_synced_recursive(self.topLevelItem(i))

    def _mark_item_synced_recursive(self, item: QTreeWidgetItem):
        if "准备上传" in item.text(2):
            item.setText(2, "✅ 上传完成 (已同步)")
            font = item.font(0)
            font.setBold(False)
            item.setFont(0, font)
            item.setFont(2, font)
        
        for i in range(item.childCount()):
            self._mark_item_synced_recursive(item.child(i))

    
    def _add_items(self, parent_item: Optional[QTreeWidgetItem], path: Path):
        """递归添加文件和文件夹"""
        try:
            # 先添加文件夹
            folders = sorted([p for p in path.iterdir() if p.is_dir()], key=lambda x: x.name.lower())
            for folder in folders:
                item = QTreeWidgetItem(parent_item)
                item.setText(0, f"📁 {folder.name}")
                item.setText(1, "-")
                item.setText(2, "文件夹")
                item.setData(0, Qt.ItemDataRole.UserRole, folder)
                
                # 递归添加子项
                self._add_items(item, folder)
            
            # 再添加文件
            files = sorted([p for p in path.iterdir() if p.is_file()], key=lambda x: x.name.lower())
            for file in files:
                item = QTreeWidgetItem(parent_item)
                
                # 根据文件类型选择图标
                icon = self._get_file_icon(file.name)
                size = self._format_size(file.stat().st_size)
                file_type = self._get_file_type(file.name)
                
                item.setText(0, f"{icon} {file.name}")
                item.setText(1, size)
                item.setText(2, file_type)
                item.setData(0, Qt.ItemDataRole.UserRole, file)
                
                if parent_item is None:
                    self.addTopLevelItem(item)
                else:
                    parent_item.addChild(item)
        
        except PermissionError:
            pass
    
    def _get_file_icon(self, filename: str) -> str:
        """获取文件图标"""
        ext = os.path.splitext(filename)[1].lower()
        
        icon_map = {
            '.py': '🐍',
            '.js': '📜',
            '.ts': '📘',
            '.html': '🌐',
            '.css': '🎨',
            '.json': '📋',
            '.md': '📝',
            '.txt': '📄',
            '.png': '🖼️',
            '.jpg': '🖼️',
            '.jpeg': '🖼️',
            '.gif': '🎬',
            '.svg': '🎨',
            '.pdf': '📕',
            '.zip': '📦',
            '.rar': '📦',
            '.7z': '📦',
            '.tar': '📦',
            '.git': '🔧',
            '.yml': '⚙️',
            '.yaml': '⚙️',
            '.xml': '📄',
            '.toml': '⚙️',
            '.ini': '⚙️',
            '.bat': '🔧',
            '.sh': '🔧',
            '.dockerfile': '🐳',
            '.env': '🔐',
        }
        
        return icon_map.get(ext, '📄')
    
    def _get_file_type(self, filename: str) -> str:
        """获取文件类型"""
        ext = os.path.splitext(filename)[1].lower()
        
        type_map = {
            '.py': 'Python',
            '.js': 'JavaScript',
            '.ts': 'TypeScript',
            '.html': 'HTML',
            '.css': 'CSS',
            '.json': 'JSON',
            '.md': 'Markdown',
            '.txt': '文本',
            '.png': '图片',
            '.jpg': '图片',
            '.jpeg': '图片',
            '.gif': '图片',
            '.svg': 'SVG',
            '.pdf': 'PDF',
            '.zip': '压缩',
            '.rar': '压缩',
            '.7z': '压缩',
            '.tar': '压缩',
        }
        
        return type_map.get(ext, ext[1:].upper() if ext else '文件')
    
    def _on_local_change(self, path):
        """本地文件变动回调 (V4.8 Fix: 稳定性增强)"""
        # 忽略 .git 和 __pycache__ 等
        if ".git" in path or "__pycache__" in path:
            return
            
        logger.debug(f"检测到本地变动: {path}")
        # 简单起见，延迟全量刷新，防止高频触发
        if not hasattr(self, "_refresh_timer"):
            self._refresh_timer = QTimer()
            self._refresh_timer.setSingleShot(True)
            self._refresh_timer.timeout.connect(self._do_deferred_refresh)
        self._refresh_timer.start(800) # 稍微增加延迟，确保文件系统操作完成

    def _do_deferred_refresh(self):
        """执行延迟刷新 (V4.8 Fix: 传递当前路径)"""
        if self._last_folder:
            repo_name = getattr(self, "_current_repo", None)
            self.sync_preview(repo_name, self._last_folder)

    def set_watcher_path(self, folder_path: str):
        """设置监听路径"""
        if self._last_folder:
            try:
                self._watcher.removePath(self._last_folder)
            except: pass
            
        self._last_folder = folder_path
        if folder_path and os.path.exists(folder_path):
            self._watcher.addPath(folder_path)
            # 同时也递归监听子目录 (由于 QFileSystemWatcher 不支持递归，我们需要手动添加)
            # 这里只监听一级或有限层级以平衡性能
            for root, dirs, files in os.walk(folder_path):
                if '.git' in dirs: dirs.remove('.git')
                try:
                    self._watcher.addPath(root)
                except: pass

    def _format_size(self, size: int) -> str:
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"


class RepoPreviewCard(Card):
    """
    仓库预览卡片
    展示仓库的基本信息和样式预览
    """
    
    def __init__(self, parent=None):
        super().__init__(parent, clickable=False)
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
                if item.widget():
                    item.widget().deleteLater()
                    
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 仓库信息
        info_layout = QVBoxLayout()
        
        self._repo_name = QLabel("📦 未选择仓库")
        self._repo_name.setStyleSheet(f"""
            font-size: 20px;
            font-weight: bold;
            color: {c['text_primary']};
        """)
        info_layout.addWidget(self._repo_name)
        
        self._repo_desc = QLabel("请选择一个仓库以查看预览")
        self._repo_desc.setStyleSheet(f"""
            font-size: 14px;
            color: {c['text_secondary']};
        """)
        self._repo_desc.setWordWrap(True)
        info_layout.addWidget(self._repo_desc)
        
        # 仓库统计
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(20)
        
        self._stars_label = QLabel("⭐ 0")
        self._stars_label.setStyleSheet(f"color: {c['text_secondary']}; font-size: 13px;")
        stats_layout.addWidget(self._stars_label)
        
        self._forks_label = QLabel("🔱 0")
        self._forks_label.setStyleSheet(f"color: {c['text_secondary']}; font-size: 13px;")
        stats_layout.addWidget(self._forks_label)
        
        self._issues_label = QLabel("🐛 0")
        self._issues_label.setStyleSheet(f"color: {c['text_secondary']}; font-size: 13px;")
        stats_layout.addWidget(self._issues_label)
        
        info_layout.addLayout(stats_layout)
        layout.addLayout(info_layout)
        
        # 仓库链接
        self._repo_link = QLabel("🔗 无链接")
        self._repo_link.setStyleSheet(f"""
            font-size: 13px;
            color: {c['accent']};
        """)
        self._repo_link.setWordWrap(True)
        layout.addWidget(self._repo_link)
        
        # 分割线
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet(f"background-color: {c['border']};")
        layout.addWidget(divider)
        
        # 预览说明
        preview_label = QLabel("👀 仓库预览")
        preview_label.setStyleSheet(f"""
            font-size: 16px;
            font-weight: bold;
            color: {c['text_primary']};
        """)
        layout.addWidget(preview_label)
        
        self._preview_content = QLabel("选择仓库后，这里将显示仓库的样式预览")
        self._preview_content.setStyleSheet(f"""
            font-size: 13px;
            color: {c['text_muted']};
        """)
        self._preview_content.setWordWrap(True)
        layout.addWidget(self._preview_content)
    
    def update_repo(self, repo_name: str, repo_info: Optional[dict] = None):
        """更新仓库信息"""
        c = theme_manager.colors
        
        if repo_name:
            self._repo_name.setText(f"📦 {repo_name}")
            
            if repo_info:
                self._repo_desc.setText(repo_info.get('description', '无描述'))
                self._stars_label.setText(f"📦 {repo_info.get('size', 0)} KB")
                self._forks_label.setText(f"🔄 {repo_info.get('updated_at', '未知')[:10]}")
                self._issues_label.setText(f"👁️ {'私有' if repo_info.get('private') else '公开'}")
                self._repo_link.setText(f"🔗 {repo_info.get('html_url', '')}")
                
                # 生成预览内容
                preview_text = self._generate_preview(repo_info)
                self._preview_content.setText(preview_text)
                self._preview_content.setStyleSheet(f"""
                    font-size: 13px;
                    color: {c['text_secondary']};
                """)
        else:
            self._repo_name.setText("📦 未选择仓库")
            self._repo_desc.setText("请选择一个仓库以查看预览")
            self._stars_label.setText("⭐ 0")
            self._forks_label.setText("🔱 0")
            self._issues_label.setText("🐛 0")
            self._repo_link.setText("🔗 无链接")
            self._preview_content.setText("选择仓库后，这里将显示仓库的样式预览")
            self._preview_content.setStyleSheet(f"""
                font-size: 13px;
                color: {c['text_muted']};
            """)
    
    def _generate_preview(self, repo_info: dict) -> str:
        """生成预览内容"""
        lines = [
            f"📅 创建于: {repo_info.get('created_at', '未知')[:10]}",
            f"🔄 更新于: {repo_info.get('updated_at', '未知')[:10]}",
            f"👁️ 可见性: {'私有' if repo_info.get('private') else '公开'}",
            f"📦 大小: {repo_info.get('size', 0)} KB",
        ]
        
        return "\n".join(lines)


class PreviewPanel(GlassPanel):
    """
    实时预览面板
    显示仓库预览和文件结构
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._folder_path: Optional[str] = None
        self._repo_name: Optional[str] = None
        self._repo_info: Optional[str] = None
        self._setup_ui()
        theme_manager.theme_changed.connect(self._setup_ui)
    
    def _setup_ui(self):
        """设置UI (V4.8: 增加 Web 实时预览)"""
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
                    
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)
        
        # 头部 (标题 + 操作)
        header = QHBoxLayout()
        title = SectionTitle("👁️", "实时预览")
        header.addWidget(title)
        header.addStretch()
        
        self._open_browser_btn = GlassButton("🌐 浏览器打开", primary=False)
        self._open_browser_btn.setFixedWidth(120)
        self._open_browser_btn.clicked.connect(self._open_in_external_browser)
        header.addWidget(self._open_browser_btn)
        layout.addLayout(header)
        
        # 创建主分割器 (仓库详情 vs Web/文件树)
        self._main_splitter = QSplitter(Qt.Orientation.Vertical)
        
        # 1. 仓库预览卡片 (顶部)
        self._repo_preview = RepoPreviewCard()
        self._main_splitter.addWidget(self._repo_preview)
        
        # 2. 底部 Tab 容器 (文件结构 vs 网页实时)
        from PyQt6.QtWidgets import QTabWidget
        self._tabs = QTabWidget()
        self._tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid {c['border']};
                background: transparent;
                border-radius: 8px;
            }}
            QTabBar::tab {{
                background: {c['bg_tertiary']};
                color: {c['text_secondary']};
                padding: 8px 15px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{
                background: {c['accent']};
                color: white;
            }}
        """)
        
        # --- Tab 1: 文件结构 ---
        file_tree_container = QWidget()
        file_tree_layout = QVBoxLayout(file_tree_container)
        file_tree_layout.setContentsMargins(5, 5, 5, 5)
        
        self._file_tree = FileTreeWidget()
        file_tree_layout.addWidget(self._file_tree)
        self._tabs.addTab(file_tree_container, "📁 本地文件结构")
        
        # --- Tab 2: 网页实时 (QWebEngineView) ---
        self._web_view_container = QWidget()
        web_layout = QVBoxLayout(self._web_view_container)
        web_layout.setContentsMargins(0, 0, 0, 0)
        web_layout.setSpacing(0)
        
        try:
            from PyQt6.QtWebEngineWidgets import QWebEngineView
            self._web_view = QWebEngineView()
            # 设置页面背景透明或匹配主题
            self._web_view.setStyleSheet("background: transparent;")
            web_layout.addWidget(self._web_view)
            self._has_web_engine = True
        except ImportError:
            # Fallback if WebEngine is not installed
            accent_color = c['accent']
            fallback = QLabel(f"🌐 当前环境未安装 PyQt6-WebEngine<br>启用实时网页预览需要此组件。<br><br>可以使用底部指令安装：<br><code style='color:{accent_color}'>pip install PyQt6-WebEngine</code>")
            fallback.setAlignment(Qt.AlignmentFlag.AlignCenter)
            fallback.setStyleSheet(f"color: {c['text_muted']}; font-style: italic;")
            web_layout.addWidget(fallback)
            self._web_view = None
            self._has_web_engine = False
            
        self._tabs.addTab(self._web_view_container, "🌍 GitHub 实时网页")
        
        self._main_splitter.addWidget(self._tabs)
        
        # 设置分割器比例
        self._main_splitter.setStretchFactor(0, 1)
        self._main_splitter.setStretchFactor(1, 3)
        
        layout.addWidget(self._main_splitter)
        
        # 提示信息
        self._hint_label = QLabel("💡 选择文件夹和仓库后，这里将显示实时预览")
        self._hint_label.setStyleSheet(f"""
            font-size: 12px;
            color: {c['text_muted']};
            padding: 10px;
            background-color: {c['bg_tertiary']};
            border-radius: 6px;
        """)
        layout.addWidget(self._hint_label)

    def _open_in_external_browser(self):
        """外部浏览器打开"""
        if self._repo_info and isinstance(self._repo_info, dict):
            url = self._repo_info.get('html_url')
            if url:
                QDesktopServices.openUrl(QUrl(url))
        elif self._repo_name:
            QDesktopServices.openUrl(QUrl(f"https://github.com/{self._repo_name}"))

    def set_folder_path(self, path: str):
        """设置文件夹路径 v4.8 Update: 联动 Watcher"""
        self._folder_path = path
        self._file_tree.set_watcher_path(path)
        self._sync_all()
        self._update_hint()
    
    def set_repo(self, repo_name: str, repo_info: Optional[dict] = None):
        """设置仓库信息 v4.8 Update: 联动 Web预览"""
        self._repo_name = repo_name
        self._repo_info = repo_info
        self._repo_preview.update_repo(repo_name, repo_info)
        
        # 更新网页面板
        if repo_info and self._web_view and self._has_web_engine:
            url = repo_info.get('html_url')
            if url:
                self._web_view.setUrl(QUrl(url))
                
        self._sync_all()
        self._update_hint()

    def _sync_all(self):
        """触发全量同步预览"""
        # 为了让 Watcher 刷新时能拿到仓库名，存一下
        self._file_tree._current_repo = self._repo_name
        self._file_tree.sync_preview(self._repo_name, self._folder_path)

    def refresh_after_upload(self):
        """上传完成后刷新 (带成功标记)"""
        # 第一步：先立即改变当前 UI 的状态显示，给用户即时反馈
        self._file_tree.mark_all_synced()
        
        # 第二步：刷新网页预览
        if self._web_view and self._has_web_engine:
            self._web_view.reload()
        
        # 第三步：延迟 1.5 秒后从远程重新拉取一次
        QTimer.singleShot(1500, self._sync_all)

    
    def _update_hint(self):
        """更新提示信息"""
        hints = []
        if self._folder_path:
            hints.append(f"📁 文件夹: {os.path.basename(self._folder_path)}")
        if self._repo_name:
            hints.append(f"📦 仓库: {self._repo_name}")
        
        if hints:
            self._hint_label.setText(" | ".join(hints))
        else:
            self._hint_label.setText("💡 选择文件夹和仓库后，这里将显示实时预览")
    
    def clear(self):
        """清空预览"""
        self._folder_path = None
        self._repo_name = None
        self._repo_info = None
        self._file_tree.clear()
        self._repo_preview.update_repo(None)
        self._update_hint()
