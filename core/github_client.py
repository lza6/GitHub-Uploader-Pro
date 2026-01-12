"""
GitHub Uploader Pro - GitHub API客户端
提供GitHub仓库管理和文件上传功能
"""
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from github import Github, GithubException
from github.Repository import Repository
from github.AuthenticatedUser import AuthenticatedUser
from loguru import logger

from .credential_manager import credential_manager


@dataclass
class RepoInfo:
    """仓库信息"""
    name: str
    full_name: str
    description: Optional[str]
    private: bool
    default_branch: str
    html_url: str
    clone_url: str
    ssh_url: str
    created_at: str
    updated_at: str
    size: int  # KB


@dataclass
class CreateRepoOptions:
    """创建仓库选项"""
    name: str
    description: str = ""
    private: bool = False
    auto_init: bool = False  # 自动初始化README
    gitignore_template: Optional[str] = None
    license_template: Optional[str] = None


class GitHubClient:
    """
    GitHub API客户端
    封装PyGithub，提供仓库管理和文件操作功能
    """
    
    def __init__(self):
        self._github: Optional[Github] = None
        self._user: Optional[AuthenticatedUser] = None
        self._repo_cache: Dict[str, List[RepoInfo]] = {}  # 缓存仓库列表
        self._connect()
    
    def _connect(self) -> bool:
        """
        连接GitHub API v3.0 [Optimized Connector]
        优化认证链路与资源完整性校验
        """
        token = credential_manager.get_access_token()
        if not token:
            logger.debug("OAUTH_MISSING: 未检测到有效的访问令牌")
            return False
        
        try:
            # 初始化全局实例
            self._github = Github(token, timeout=30, retry=3)
            self._user = self._github.get_user()
            
            # API 状态热校验
            login = self._user.login
            logger.info(f"GITHUB_NODE_READY: 身份验证成功 | 实体: {login}")
            
            # 记录初始速率限制状态 (兼容性修复)
            try:
                rl = self._github.get_rate_limit()
                # 兼容不同版本的 PyGithub: 优先尝试 .core (RateLimit), 其次尝试 .rate (RateLimitOverview)
                rate = getattr(rl, 'core', getattr(rl, 'rate', None))
                if rate:
                    logger.debug(f"RATE_LIMIT: {rate.remaining}/{rate.limit} (重置时间: {rate.reset})")
            except Exception as re:
                logger.warning(f"无法获取速率限制状态: {re}")
            
            return True
        except GithubException as e:
            logger.error(f"AUTH_SESSION_FAILED: {e}")
            self._github = None
            self._user = None
            return False
    
    def reconnect(self) -> bool:
        """重新连接"""
        return self._connect()
    
    @property
    def is_connected(self) -> bool:
        """是否已连接"""
        return self._github is not None and self._user is not None
    
    @property
    def user(self) -> Optional[AuthenticatedUser]:
        """获取当前用户"""
        return self._user
    
    def get_repos(self, sort: str = "updated", limit: Optional[int] = 50, page: int = 1) -> List[RepoInfo]:
        """
        获取当前用户的仓库列表 (V4.5 支持分页)
        
        Args:
            sort: 排序方式
            limit: 获取数量 (每页上限)
            page: 页码
        
        Returns:
            仓库信息列表
        """
        if not self.is_connected:
            logger.warning("未连接GitHub API")
            return []
        
        try:
            # 使用 PyGithub 的 get_page 方法 (如果支持) 或手动切片
            repos_data = self._user.get_repos(sort=sort)
            total_count = repos_data.totalCount
            
            start_idx = (page - 1) * limit
            if start_idx >= total_count:
                logger.debug(f"分页超出范围: {start_idx} >= {total_count}")
                return []
                
            # 切片模式
            paged_data = repos_data[start_idx : start_idx + limit]
            
            repos = []
            for repo in paged_data:
                repos.append(RepoInfo(
                    name=repo.name,
                    full_name=repo.full_name,
                    description=repo.description,
                    private=repo.private,
                    default_branch=repo.default_branch,
                    html_url=repo.html_url,
                    clone_url=repo.clone_url,
                    ssh_url=repo.ssh_url,
                    created_at=repo.created_at.isoformat() if repo.created_at else "",
                    updated_at=repo.updated_at.isoformat() if repo.updated_at else "",
                    size=repo.size,
                ))
                if limit and len(repos) >= limit:
                    break
            
            # 分页加载日志优化
            if page == 1:
                logger.info(f"开始加载仓库列表 (第 {page} 页)...")
            else:
                logger.debug(f"继续加载仓库列表 (第 {page} 页)...")

            return repos
            
        except GithubException as e:
            logger.error(f"获取仓库列表失败: {e}")
            return []
    
    def clear_cache(self):
        """清除缓存"""
        self._repo_cache.clear()
    
    def get_repo(self, full_name: str) -> Optional[Repository]:
        """
        获取指定仓库
        
        Args:
            full_name: 仓库全名 (owner/repo)
            
        Returns:
            Repository对象
        """
        if not self.is_connected:
            return None
        
        try:
            return self._github.get_repo(full_name)
        except GithubException as e:
            logger.error(f"获取仓库失败: {e}")
            return None
    
    def create_repo(self, options: CreateRepoOptions) -> Optional[RepoInfo]:
        """
        创建新仓库
        
        Args:
            options: 创建选项
            
        Returns:
            创建的仓库信息
        """
        if not self.is_connected:
            logger.error("未连接GitHub API")
            return None
        
        try:
            # V4.8.2 Fix: PyGithub 不接受 None 值，需使用 kwargs 动态传参
            kwargs = {
                "name": options.name,
                "description": options.description or "", # Ensure string
                "private": options.private,
                "auto_init": options.auto_init,
            }
            
            if options.gitignore_template:
                kwargs["gitignore_template"] = options.gitignore_template
            
            if options.license_template:
                kwargs["license_template"] = options.license_template

            repo = self._user.create_repo(**kwargs)
            
            logger.info(f"创建仓库成功: {repo.full_name}")
            
            return RepoInfo(
                name=repo.name,
                full_name=repo.full_name,
                description=repo.description,
                private=repo.private,
                default_branch=repo.default_branch,
                html_url=repo.html_url,
                clone_url=repo.clone_url,
                ssh_url=repo.ssh_url,
                created_at=repo.created_at.isoformat() if repo.created_at else "",
                updated_at=repo.updated_at.isoformat() if repo.updated_at else "",
                size=repo.size,
            )
            
        except GithubException as e:
            logger.error(f"创建仓库失败: {e}")
            return None
    
    def delete_repo(self, full_name: str) -> bool:
        """
        删除仓库
        
        Args:
            full_name: 仓库全名
            
        Returns:
            是否删除成功
        """
        if not self.is_connected:
            return False
        
        try:
            repo = self._github.get_repo(full_name)
            repo.delete()
            logger.info(f"删除仓库成功: {full_name}")
            return True
        except GithubException as e:
            logger.error(f"删除仓库失败: {e}")
            return False
    
    def get_branches(self, full_name: str) -> List[str]:
        """
        获取仓库的分支列表
        
        Args:
            full_name: 仓库全名
            
        Returns:
            分支名称列表
        """
        if not self.is_connected:
            return []
        
        try:
            repo = self._github.get_repo(full_name)
            return [branch.name for branch in repo.get_branches()]
        except GithubException as e:
            logger.error(f"获取分支列表失败: {e}")
            return []
    
    def create_or_update_file(
        self,
        full_name: str,
        path: str,
        content: bytes,
        message: str,
        branch: str = "main",
    ) -> bool:
        """
        创建或更新文件
        
        Args:
            full_name: 仓库全名
            path: 文件在仓库中的路径
            content: 文件内容（字节）
            message: 提交信息
            branch: 分支名
            
        Returns:
            是否成功
        """
        if not self.is_connected:
            return False
        
        try:
            repo = self._github.get_repo(full_name)
            
            # 尝试获取现有文件
            try:
                existing = repo.get_contents(path, ref=branch)
                # 文件存在，更新
                repo.update_file(
                    path=path,
                    message=message,
                    content=content,
                    sha=existing.sha,
                    branch=branch,
                )
                logger.debug(f"更新文件: {path}")
            except GithubException:
                # 文件不存在，创建
                repo.create_file(
                    path=path,
                    message=message,
                    content=content,
                    branch=branch,
                )
                logger.debug(f"创建文件: {path}")
            
            return True
            
        except GithubException as e:
            logger.error(f"创建/更新文件失败: {e}")
            return False
    
    def get_gitignore_templates(self) -> List[str]:
        """获取可用的.gitignore模板列表"""
        if not self.is_connected:
            return []
        
        try:
            return self._github.get_gitignore_templates()
        except GithubException as e:
            logger.error(f"获取.gitignore模板失败: {e}")
            return []
    
    def get_license_templates(self) -> List[Dict[str, str]]:
        """获取可用的许可证模板列表"""
        if not self.is_connected:
            return []
        
        try:
            licenses = self._github.get_licenses()
            return [{"key": lic.key, "name": lic.name} for lic in licenses]
        except GithubException as e:
            logger.error(f"获取许可证模板失败: {e}")
            return []


# 全局GitHub客户端实例
github_client = GitHubClient()
