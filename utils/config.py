"""
GitHub Uploader Pro - 配置管理
提供应用程序的配置管理功能
"""
import json
import os
from pathlib import Path
from typing import Any, Optional
from loguru import logger


class Config:
    """配置管理器 - 单例模式"""
    
    _instance: Optional['Config'] = None
    
    # 应用程序基本信息
    APP_NAME = "GitHub Uploader Pro"
    APP_VERSION = "1.0.0"
    APP_AUTHOR = "GitHub Uploader Team"
    
    # GitHub OAuth配置 (Device Flow)
    # 注意：需要创建 GitHub OAuth App 并获取 Client ID
    # 创建步骤：
    # 1. 访问 https://github.com/settings/developers
    # 2. 点击 "New OAuth App"
    # 3. 填写应用信息，Callback URL 可以填 http://localhost:8080
    # 4. 创建后获取 Client ID
    # 5. 确保 OAuth App 启用了 Device Flow（默认已启用）
    GITHUB_CLIENT_ID = "Ov23liXXXXXXXXXXXXXX"  # 需要用户替换为自己的Client ID
    GITHUB_DEVICE_CODE_URL = "https://github.com/login/device/code"
    GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
    GITHUB_API_URL = "https://api.github.com"
    GITHUB_SCOPES = "repo,read:user"
    
    # 默认配置
    DEFAULT_CONFIG = {
        "theme": "dark",
        "language": "zh_CN",
        "auto_login": True,
        "remember_last_folder": True,
        "last_folder": "",
        "last_repo": "",
        "default_branch": "main",
        "default_commit_message": "✨ 使用 GitHub Uploader Pro 上传",
        "gitignore_templates": ["Python", "Node", "Rust"],
        "max_file_size_mb": 100,
        "upload_chunk_size_kb": 1024,
        "log_level": "INFO",
        "window_geometry": None,
        "recent_repos": [],
        "recent_folders": [],
        # AI Agent 配置 (v2.0)
        "ai_enabled": True,
        "ai_url": "https://api.openai.com/v1",
        "ai_key": "",
        "ai_model": "gpt-3.5-turbo",
        "ai_system_prompt": "你是一个专业的 Git 顾问。请根据提供的项目结构，生成高质量的 .gitignore 文件内容，或回答关于 Git 操作的问题。回复请始终使用中文。",
    }
    
    def __new__(cls) -> 'Config':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self._config_dir = self._get_config_dir()
        self._config_file = self._config_dir / "config.json"
        self._config: dict = {}
        self._load_config()
        logger.info(f"配置管理器初始化完成: {self._config_file}")
    
    def _get_config_dir(self) -> Path:
        """获取配置目录路径"""
        if os.name == 'nt':  # Windows
            base_dir = Path(os.environ.get('APPDATA', Path.home()))
        else:  # Linux/macOS
            base_dir = Path.home() / '.config'
        
        config_dir = base_dir / "GitHubUploaderPro"
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir
    
    def _load_config(self) -> None:
        """加载配置文件"""
        if self._config_file.exists():
            try:
                with open(self._config_file, 'r', encoding='utf-8') as f:
                    saved_config = json.load(f)
                # 合并默认配置和保存的配置
                self._config = {**self.DEFAULT_CONFIG, **saved_config}
                logger.debug("已加载配置文件")
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"配置文件加载失败，使用默认配置: {e}")
                self._config = self.DEFAULT_CONFIG.copy()
        else:
            self._config = self.DEFAULT_CONFIG.copy()
            self._save_config()
            logger.info("创建默认配置文件")
    
    def _save_config(self) -> None:
        """保存配置到文件"""
        try:
            with open(self._config_file, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, ensure_ascii=False, indent=2)
            logger.debug("配置已保存")
        except IOError as e:
            logger.error(f"配置保存失败: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        return self._config.get(key, default)
    
    def set(self, key: str, value: Any, save: bool = True) -> None:
        """设置配置值"""
        self._config[key] = value
        if save:
            self._save_config()
    
    def update(self, updates: dict, save: bool = True) -> None:
        """批量更新配置"""
        self._config.update(updates)
        if save:
            self._save_config()
    
    def reset(self) -> None:
        """重置为默认配置"""
        self._config = self.DEFAULT_CONFIG.copy()
        self._save_config()
        logger.info("配置已重置为默认值")
    
    @property
    def config_dir(self) -> Path:
        """获取配置目录"""
        return self._config_dir
    
    @property
    def all_config(self) -> dict:
        """获取所有配置"""
        return self._config.copy()
    
    def add_recent_repo(self, repo: str, max_items: int = 10) -> None:
        """添加最近使用的仓库"""
        recent: list = self._config.get("recent_repos", [])
        if repo in recent:
            recent.remove(repo)
        recent.insert(0, repo)
        self._config["recent_repos"] = recent[:max_items]
        self._save_config()
    
    def add_recent_folder(self, folder: str, max_items: int = 10) -> None:
        """添加最近使用的文件夹"""
        recent: list = self._config.get("recent_folders", [])
        if folder in recent:
            recent.remove(folder)
        recent.insert(0, folder)
        self._config["recent_folders"] = recent[:max_items]
        self._save_config()


# 全局配置实例
config = Config()
