"""
GitHub Uploader Pro - 上传管理器
协调Git操作和GitHub API完成文件上传
"""
import threading
from typing import Optional, Callable, List
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from loguru import logger

from .git_operations import git_ops, GitOperations
from .github_client import github_client
from .credential_manager import credential_manager
from utils.config import config


class UploadState(Enum):
    """上传状态"""
    IDLE = "idle"
    PREPARING = "preparing"
    INITIALIZING = "initializing"
    ADDING = "adding"
    COMMITTING = "committing"
    PUSHING = "pushing"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class UploadProgress:
    """上传进度"""
    state: UploadState
    current_file: str = ""
    current_step: int = 0
    total_steps: int = 5
    message: str = ""
    error: Optional[str] = None


@dataclass
class UploadOptions:
    """上传选项"""
    folder_path: str
    repo_full_name: str
    branch: str = "main"
    commit_message: str = "Update via GitHub Uploader Pro"
    force_push: bool = False
    create_gitignore: bool = True
    gitignore_content: Optional[str] = None


class UploadManager:
    """
    上传管理器
    协调Git操作和GitHub API，提供完整的上传流程
    """
    
    # 默认.gitignore内容
    DEFAULT_GITIGNORE = """# IDE
.idea/
.vscode/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db
desktop.ini

# Build
__pycache__/
*.py[cod]
*$py.class
*.so
build/
dist/
*.egg-info/
.eggs/

# Dependencies
node_modules/
venv/
.env

# Logs
*.log
logs/

# Temporary files
*.tmp
*.temp
.cache/
"""
    
    def __init__(self):
        self._upload_thread: Optional[threading.Thread] = None
        self._cancel_event = threading.Event()
        self._on_progress: Optional[Callable[[UploadProgress], None]] = None
        self._on_log: Optional[Callable[[str], None]] = None
        self._git: Optional[GitOperations] = None
    
    def set_progress_callback(self, callback: Callable[[UploadProgress], None]) -> None:
        """设置进度回调"""
        self._on_progress = callback
    
    def set_log_callback(self, callback: Callable[[str], None]) -> None:
        """设置日志回调"""
        self._on_log = callback
    
    def _emit_progress(self, progress: UploadProgress) -> None:
        """发送进度更新"""
        if self._on_progress:
            self._on_progress(progress)
    
    def _emit_log(self, message: str) -> None:
        """发送日志"""
        if self._on_log:
            self._on_log(message)
        logger.info(message)
    
    def start_upload(self, options: UploadOptions) -> bool:
        """
        开始上传
        
        Args:
            options: 上传选项
            
        Returns:
            是否成功启动
        """
        if self._upload_thread and self._upload_thread.is_alive():
            logger.warning("上传正在进行中")
            return False
        
        self._cancel_event.clear()
        self._upload_thread = threading.Thread(
            target=self._upload_worker,
            args=(options,),
            daemon=True,
        )
        self._upload_thread.start()
        return True
    
    def cancel_upload(self) -> None:
        """取消上传"""
        self._cancel_event.set()
        if self._upload_thread and self._upload_thread.is_alive():
            self._upload_thread.join(timeout=5)
        self._emit_progress(UploadProgress(
            state=UploadState.CANCELLED,
            message="上传已取消",
        ))
    
    def _upload_worker(self, options: UploadOptions) -> None:
        """上传工作线程"""
        try:
            self._perform_upload(options)
        except Exception as e:
            logger.exception("上传失败")
            self._emit_progress(UploadProgress(
                state=UploadState.FAILED,
                error=str(e),
                message="上传失败",
            ))
    
    def _perform_upload(self, options: UploadOptions) -> None:
        """执行上传流程 v4.0 (Nebula Pipeline)"""
        # 步骤1: 深度预检与环境感知
        self._emit_progress(UploadProgress(
            state=UploadState.PREPARING,
            current_step=1,
            total_steps=6,
            message="🚀 Nebula 引擎启动，正在进行环境深度扫描...",
        ))
        
        if self._cancel_event.is_set():
            return
        
        # 验证路径
        folder_path = Path(options.folder_path)
        if not folder_path.exists():
            raise ValueError(f"CRITICAL: 文件夹不存在: {options.folder_path}")
        
        # 初始化Git操作
        self._git = GitOperations(options.folder_path)
        self._git.set_output_callback(self._emit_log)
        
        # 探测Git环境
        if not self._git.is_git_installed():
            raise RuntimeError("GIT_MISSING: 系统未探测到Git环境，请检查PATH配置")
        
        self._emit_log(f"🚀 系统就绪 | 目标仓库: {options.repo_full_name}")
        
        # 步骤2: Git 核心初始化 (支持自愈)
        self._emit_progress(UploadProgress(
            state=UploadState.INITIALIZING,
            current_step=2,
            message="正在同步Git仓库状态...",
        ))
        
        if self._cancel_event.is_set():
            return
        
        if not self._git.is_repo():
            self._emit_log("📡 正在创建全新的Git仓库实例...")
            if not self._git.init(options.branch):
                raise RuntimeError("INIT_FAILED: 无法初始化本地仓库")
        else:
            self._emit_log("📡 检测到现有Git仓库，正在验证完整性...")
        
        # 自动创建智能 .gitignore
        if options.create_gitignore and not self._git.has_gitignore():
            self._emit_log("📝 正在注入智能 .gitignore 模板...")
            content = options.gitignore_content or self.DEFAULT_GITIGNORE
            self._git.create_gitignore(content)
        
        # 动态配置远程端点
        if github_client.is_connected and github_client.user:
            # 兼容性处理
            # V4.8.7 Fix: 注入访问令牌以避免交互式提示
            token = credential_manager.get_access_token()
            if token:
                # 使用令牌构建认证URL
                remote_url = f"https://x-access-token:{token}@github.com/{options.repo_full_name}.git"
                # 日志中隐藏敏感信息
                safe_url = f"https://github.com/{options.repo_full_name}.git"
                self._emit_log(f"🔗 正在建立加密链路至: {safe_url}")
            else:
                remote_url = f"https://github.com/{options.repo_full_name}.git"
                self._emit_log(f"🔗 正在建立加密链路至: {remote_url}")
            
            self._git.set_remote(remote_url)
        
        # 步骤3: 智能文件索引
        self._emit_progress(UploadProgress(
            state=UploadState.ADDING,
            current_step=3,
            message="正在构建文件索引...",
        ))
        
        if self._cancel_event.is_set():
            return
        
        file_count = self._git.get_file_count()
        folder_size = self._git.get_folder_size()
        self._emit_log(f"📦 资产分析: {file_count} 个文件 ({self._format_size(folder_size)})")
        
        if not self._git.add():
            raise RuntimeError("INDEX_FAILED: 无法将文件添加至暂存区")
        
        # 步骤4: 原子化提交
        self._emit_progress(UploadProgress(
            state=UploadState.COMMITTING,
            current_step=4,
            message="正在固化变更快照...",
        ))
        
        if self._cancel_event.is_set():
            return
        
        self._git.set_branch(options.branch)
        if not self._git.commit(options.commit_message):
            self._emit_log("ℹ️ 状态一致: 当前工作区没有需要提交的变更")
        else:
            self._emit_log(f"✅ 快照已生成: {options.commit_message}")
        
        # 步骤5: 并发推送与同步
        self._emit_progress(UploadProgress(
            state=UploadState.PUSHING,
            current_step=5,
            message="正在执行远程同步...",
        ))
        
        if self._cancel_event.is_set():
            return
        
        # 尝试标准推送，失败时触发自愈/强制逻辑
        push_success = self._git.push(
            branch=options.branch,
            force=options.force_push,
        )
        
        if not push_success:
            if options.force_push:
                raise RuntimeError("PUSH_CRITICAL: 强制推送指令执行失败，请手动干预。")
            
            # V4 AI 自愈逻辑集成
            # V4 AI 自愈逻辑集成 (Smart Sync)
            self._emit_log("⚠️ 检测到同步冲突，启动 [Smart Sync] 智能同步引擎...")
            
            # 策略A: 尝试标准拉取合并 (Pull & Merge) - 优先策略
            self._emit_log("🔄 策略A: 正在尝试拉取合并远程变更...")
            if self._git.pull(branch=options.branch):
                self._emit_log("✅ 拉取合并成功，再次尝试推送...")
                if self._git.push(branch=options.branch, force=False):
                     self._emit_log("🎉 Smart Sync (Merge) 同步成功！")
                     push_success = True
            
            if not push_success:
                # 策略B: 尝试变基合并 (Rebase)
                self._emit_log("🔄 策略B: 正在尝试 Rebase 策略合并远程变更...")
                if self._git.rebase(branch=options.branch):
                    self._emit_log("✅ 变基合并成功，再次尝试推送...")
                    if self._git.push(branch=options.branch, force=False):
                         self._emit_log("🎉 Smart Sync (Rebase) 同步成功！")
                         push_success = True
            
            if not push_success:
                self._emit_log("⚠️ 变基失败或冲突，正在回滚并不安全模式...")
                self._git.abort_rebase()
                
                # 策略C: 强制推送 (Force Push) - 最终手段
                self._emit_log("🔮 激活 AI Nebula 终极策略: 强制覆盖 (Force Push)")
                self._emit_log("⚠️ 注意: 远程的历史记录将被本地覆盖")
                
                if not self._git.push(branch=options.branch, force=True):
                    raise RuntimeError("SYNC_ABORT: 所有自动修复策略(Merge/Rebase/Force)均已失效，请检查网络或权限。")
        
        # 步骤6: 原子化完整性校验 v4.4 (Sentinel Check)
        self._emit_progress(UploadProgress(
            state=UploadState.VERIFYING,
            current_step=6,
            total_steps=6,
            message="🛡️ 正在进行最终一致性指纹核对...",
        ))
        
        if not self._git.verify_push(options.branch):
            self._emit_log("🔴 警告: 检测到远程同步不完整，正在执行紧急断点自愈...")
            # 自动重试一遍推送
            if not self._git.push(branch=options.branch, force=options.force_push):
                 raise RuntimeError("INTEGRITY_FAILED: 完整性校验失败且自愈尝试无效")
            
            # 再次核对
            if not self._git.verify_push(options.branch):
                raise RuntimeError("SENTINEL_ABORT: 远程与本地状态持续不一致，请检查网络丢包情况")

        # 完成阶段
        self._emit_progress(UploadProgress(
            state=UploadState.COMPLETED,
            current_step=6,
            total_steps=6,
            message="🎉 所有文件已确认完整传输！任务圆满结束。",
        ))
        
        # 保存最近使用
        config.add_recent_folder(options.folder_path)
        config.add_recent_repo(options.repo_full_name)
        
        html_url = f"https://github.com/{options.repo_full_name}"
        self._emit_log(f"🎉 上传完成！访问: {html_url}")
    
    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """格式化文件大小"""
        for unit in ["B", "KB", "MB", "GB"]:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"


# 全局上传管理器实例
upload_manager = UploadManager()
