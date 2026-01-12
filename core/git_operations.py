"""
GitHub Uploader Pro - Git操作封装
提供本地Git仓库操作功能
"""
import os
import re
import subprocess
from pathlib import Path
from typing import Optional, List, Tuple, Callable
from dataclasses import dataclass
from enum import Enum
from loguru import logger


class FileStatus(Enum):
    """文件状态枚举"""
    ADDED = "A"
    MODIFIED = "M"
    DELETED = "D"
    RENAMED = "R"
    COPIED = "C"
    UNTRACKED = "?"
    IGNORED = "!"


@dataclass
class FileChange:
    """文件变更信息"""
    path: str
    status: FileStatus
    old_path: Optional[str] = None  # 重命名时的原路径


@dataclass
class GitStatus:
    """Git仓库状态"""
    is_repo: bool
    branch: str
    remote_url: Optional[str]
    changes: List[FileChange]
    ahead: int = 0
    behind: int = 0


class GitOperations:
    """
    Git操作封装类
    使用subprocess调用git命令，提供本地仓库操作功能
    """
    
    def __init__(self, repo_path: Optional[str] = None):
        self._repo_path: Optional[Path] = Path(repo_path) if repo_path else None
        self._on_output: Optional[Callable[[str], None]] = None
    
    def set_repo_path(self, path: str) -> bool:
        """设置仓库路径"""
        self._repo_path = Path(path)
        return self._repo_path.exists()
    
    def set_output_callback(self, callback: Callable[[str], None]) -> None:
        """设置输出回调"""
        self._on_output = callback
    
    def _sanitize_log(self, text: str) -> str:
        """
        脱敏日志中的敏感信息
        隐藏 URL 中的 token (x-access-token:...)
        """
        # Regex to match: x-access-token:TOKEN@
        # We replace it with x-access-token:******@
        if not text:
            return ""
        return re.sub(r'(x-access-token:)([^@]+)(@)', r'\1******\3', text)
    
    def _run_git(
        self,
        args: List[str],
        check: bool = True,
        capture_output: bool = True, # Deprecated but kept for signature compatibility
        timeout: int = 120,
        retries: int = 3
    ) -> Tuple[bool, str, str]:
        """
        运行git命令 v4.5 (Real-time Stream)
        使用 Popen 实现实时日志流输出，保留重试与锁自愈机制
        """
        if not self._repo_path:
            return False, "", "ERR_PATH: 仓库路径未定义"
        
        cmd = ["git"] + args
        cmd_str = self._sanitize_log(" ".join(cmd))
        
        # 环境变量设置：强制 flush，禁用交互
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["GIT_FLUSH"] = "1"
        env["GIT_FLUSH"] = "1"
        env["GIT_TERMINAL_PROMPT"] = "0"
        env["GCM_INTERACTIVE"] = "never" # V4.8.6 Fix: 彻底禁用 GCM 弹窗
        
        for attempt in range(retries + 1):
            if attempt > 0:
                logger.warning(f"🔄 正在重试 ({attempt}/{retries})...")
            
            # 使用 Popen 启动进程
            full_stdout = []
            full_stderr = []
            
            try:
                import time
                start_time = time.perf_counter()
                
                # 合并 stdout 和 stderr 以便按序显示
                process = subprocess.Popen(
                    cmd,
                    cwd=self._repo_path,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    env=env,
                    bufsize=1 # Line buffered
                )
                
                # 定义读取线程
                def reader(stream, list_collector, is_stderr=False):
                    for line in iter(stream.readline, ''):
                        line = line.strip()
                        if not line: continue
                        
                        list_collector.append(line)
                        
                        # V4.8.1 Fix: 过滤海量刷屏日志以防止 UI 线程崩溃
                        # 1. create mode 100... (7000+ lines during init)
                        # 2. LF will be replaced... (warning flood)
                        is_spam = "create mode 100" in line or "LF will be replaced by CRLF" in line
                        
                        if self._on_output and not is_spam:
                            # 标记错误流
                            prefix = "🔴 " if is_stderr and check else ""
                            # V4.8.8 Fix: 日志脱敏
                            safe_line = self._sanitize_log(line)
                            self._on_output(f"{prefix}{safe_line}")
                    stream.close()
                
                import threading
                t_out = threading.Thread(target=reader, args=(process.stdout, full_stdout, False))
                t_err = threading.Thread(target=reader, args=(process.stderr, full_stderr, True))
                
                t_out.start()
                t_err.start()
                
                try:
                    process.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                    raise subprocess.TimeoutExpired(cmd, timeout)
                
                t_out.join()
                t_err.join()
                
                duration = time.perf_counter() - start_time
                stdout_str = "\n".join(full_stdout)
                stderr_str = "\n".join(full_stderr)
                
                if process.returncode == 0:
                    if duration > 5:
                        logger.warning(f"🐢 慢指令: {cmd_str} ({duration:.2f}s)")
                    return True, stdout_str, stderr_str
                
                # --- 错误处理与重试逻辑 ---
                last_error = stderr_str or stdout_str
                
                # 锁自愈
                if "index.lock" in last_error or ".git/refs/heads/" in last_error:
                    logger.warning(f"🔒 触发锁自愈... ({attempt})")
                    lock_path = self._repo_path / ".git" / "index.lock"
                    if lock_path.exists():
                        try: lock_path.unlink()
                        except: pass
                    time.sleep(0.5 * (attempt + 1))
                    continue
                
                if check:
                    logger.warning(f"Process Failed [{process.returncode}]: {self._sanitize_log(last_error)}")
                
                return False, stdout_str, stderr_str

            except subprocess.TimeoutExpired:
                logger.error(f"⏳ 命令超时: {timeout}s")
                continue
            except Exception as e:
                return False, "", self._sanitize_log(str(e))
        
        return False, "", f"V4_ABORT_AFTER_RETRIES: {self._sanitize_log(last_error)}"

    def get_head_oid(self, branch: str = "HEAD") -> Optional[str]:
        """获取指定引用的 OID (SHA-1) v4.4"""
        success, stdout, _ = self._run_git(["rev-parse", branch], check=False)
        return stdout if success else None

    def verify_push(self, branch: str, remote: str = "origin") -> bool:
        """验证推送完整性 v4.4 (Atomic Check)"""
        local_oid = self.get_head_oid(branch)
        if not local_oid:
            return False
            
        # 获取远程 OID
        success, stdout, _ = self._run_git(["ls-remote", remote, f"refs/heads/{branch}"], check=False)
        if not success or not stdout:
            return False
            
        remote_oid = stdout.split()[0]
        is_synced = local_oid == remote_oid
        
        if is_synced:
            logger.info(f"✅ 完整性验证通过: 本地 {branch} 与远程同步 [OID: {local_oid[:8]}]")
        else:
            logger.warning(f"❌ 完整性验证失败: 本地({local_oid[:8]}) != 远程({remote_oid[:8]})")
            
        return is_synced
    
    def is_git_installed(self) -> bool:
        """检查Git是否安装"""
        try:
            result = subprocess.run(
                ["git", "--version"],
                capture_output=True,
                text=True,
            )
            return result.returncode == 0
        except FileNotFoundError:
            return False
    
    def is_repo(self) -> bool:
        """检查当前目录是否是Git仓库"""
        if not self._repo_path:
            return False
        
        git_dir = self._repo_path / ".git"
        return git_dir.exists() and git_dir.is_dir()
    
    def init(self, initial_branch: str = "main") -> bool:
        """初始化Git仓库"""
        if self.is_repo():
            logger.info("已是Git仓库")
            return True
        
        success, _, _ = self._run_git(["init", "-b", initial_branch])
        if success:
            logger.info("Git仓库初始化成功")
        return success
    
    def get_status(self) -> GitStatus:
        """获取仓库状态"""
        if not self.is_repo():
            return GitStatus(
                is_repo=False,
                branch="",
                remote_url=None,
                changes=[],
            )
        
        # 获取当前分支
        success, branch, _ = self._run_git(
            ["rev-parse", "--abbrev-ref", "HEAD"],
            check=False,
        )
        branch = branch if success else "main"
        
        # 获取远程URL
        success, remote_url, _ = self._run_git(
            ["remote", "get-url", "origin"],
            check=False,
        )
        remote_url = remote_url if success else None
        
        # 获取文件变更
        changes = []
        success, output, _ = self._run_git(
            ["status", "--porcelain"],
            check=False,
        )
        
        if success and output:
            for line in output.split("\n"):
                if len(line) >= 3:
                    status_code = line[0:2].strip()
                    file_path = line[3:]
                    
                    # 处理重命名
                    old_path = None
                    if " -> " in file_path:
                        old_path, file_path = file_path.split(" -> ")
                    
                    status = self._parse_status(status_code)
                    if status:
                        changes.append(FileChange(
                            path=file_path,
                            status=status,
                            old_path=old_path,
                        ))
        
        return GitStatus(
            is_repo=True,
            branch=branch,
            remote_url=remote_url,
            changes=changes,
        )
    
    def _parse_status(self, code: str) -> Optional[FileStatus]:
        """解析状态码"""
        status_map = {
            "A": FileStatus.ADDED,
            "M": FileStatus.MODIFIED,
            "D": FileStatus.DELETED,
            "R": FileStatus.RENAMED,
            "C": FileStatus.COPIED,
            "?": FileStatus.UNTRACKED,
            "!": FileStatus.IGNORED,
        }
        
        # 取第一个非空字符
        for char in code:
            if char in status_map:
                return status_map[char]
        
        return FileStatus.MODIFIED if code.strip() else None
    
    def add(self, paths: Optional[List[str]] = None) -> bool:
        """添加文件到暂存区"""
        if paths:
            success, _, _ = self._run_git(["add"] + paths)
        else:
            success, _, _ = self._run_git(["add", "-A"])
        
        return success
    
    def commit(self, message: str) -> bool:
        """提交变更"""
        success, _, _ = self._run_git(["commit", "-m", message])
        return success
    
    def set_remote(self, url: str, name: str = "origin") -> bool:
        """设置远程仓库"""
        # 检查是否已有远程
        success, _, _ = self._run_git(
            ["remote", "get-url", name],
            check=False,
        )
        
        if success:
            # 更新远程URL
            success, _, _ = self._run_git(["remote", "set-url", name, url])
        else:
            # 添加新远程
            success, _, _ = self._run_git(["remote", "add", name, url])
        
        return success
    
    def push(
        self,
        branch: str = "main",
        remote: str = "origin",
        force: bool = False,
        set_upstream: bool = True,
    ) -> bool:
        """
        推送到远程 v4.0 (Resilient Push)
        支持冲突前验与强制推送二次确认
        """
        args = ["push"]
        
        # 针对 V4 增加冲突前验逻辑
        if not force:
            success, _, stderr = self._run_git(["push", "--dry-run", remote, branch], check=False)
            if not success and "rejected" in stderr:
                logger.warning("🔴 检测到远程分支领先，常规推送拒绝。")
        
        if set_upstream:
            args.extend(["-u", remote, branch])
        else:
            args.extend([remote, branch])
        
        if force:
            args.append("--force")
        
        success, _, _ = self._run_git(args)
        return success
    
    def pull(self, branch: str = "main", remote: str = "origin") -> bool:
        """拉取远程变更"""
        success, _, _ = self._run_git(["pull", remote, branch])
        return success
    
    def rebase(self, branch: str = "main", remote: str = "origin") -> bool:
        """
        变基合并 (Smart Sync Core)
        尝试 git pull --rebase origin main
        """
        # git pull --rebase <remote> <branch>
        success, _, _ = self._run_git(["pull", "--rebase", remote, branch])
        return success

    def abort_rebase(self) -> bool:
        """放弃变基"""
        success, _, _ = self._run_git(["rebase", "--abort"], check=False)
        return success
    
    def set_branch(self, branch: str) -> bool:
        """设置/切换分支"""
        # 尝试切换分支
        success, _, _ = self._run_git(["checkout", branch], check=False)
        
        if not success:
            # 分支不存在，创建新分支
            success, _, _ = self._run_git(["checkout", "-b", branch])
        
        return success
    
    def get_file_count(self) -> int:
        """获取仓库中的文件数量"""
        if not self._repo_path:
            return 0
        
        count = 0
        for root, dirs, files in os.walk(self._repo_path):
            # 跳过.git目录
            dirs[:] = [d for d in dirs if d != ".git"]
            count += len(files)
        
        return count
    
    def get_folder_size(self) -> int:
        """获取文件夹大小（字节）"""
        if not self._repo_path:
            return 0
        
        total_size = 0
        for root, dirs, files in os.walk(self._repo_path):
            # 跳过.git目录
            dirs[:] = [d for d in dirs if d != ".git"]
            for file in files:
                file_path = Path(root) / file
                try:
                    total_size += file_path.stat().st_size
                except OSError:
                    pass
        
        return total_size
    
    def create_gitignore(self, content: str) -> bool:
        """创建.gitignore文件"""
        if not self._repo_path:
            return False
        
        gitignore_path = self._repo_path / ".gitignore"
        try:
            with open(gitignore_path, "w", encoding="utf-8") as f:
                f.write(content)
            logger.info("已创建.gitignore")
            return True
        except IOError as e:
            logger.error(f"创建.gitignore失败: {e}")
            return False
    
    def has_gitignore(self) -> bool:
        """检查是否存在.gitignore"""
        if not self._repo_path:
            return False
        return (self._repo_path / ".gitignore").exists()


# 全局实例
git_ops = GitOperations()
