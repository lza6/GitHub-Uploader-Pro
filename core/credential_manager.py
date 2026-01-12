"""
GitHub Uploader Pro - 凭证管理器
使用keyring安全存储GitHub访问令牌
"""
import keyring
from typing import Optional
from dataclasses import dataclass
from loguru import logger


@dataclass
class GitHubCredential:
    """GitHub凭证数据类"""
    access_token: str
    token_type: str = "bearer"
    scope: str = ""
    username: Optional[str] = None
    user_id: Optional[int] = None
    avatar_url: Optional[str] = None


class CredentialManager:
    """
    凭证管理器
    使用系统级keyring安全存储敏感信息
    Windows: Windows Credential Manager
    macOS: Keychain
    Linux: Secret Service / KWallet
    """
    
    SERVICE_NAME = "GitHubUploaderPro"
    TOKEN_KEY = "github_access_token"
    USERNAME_KEY = "github_username"
    USER_ID_KEY = "github_user_id"
    AVATAR_KEY = "github_avatar_url"
    SCOPE_KEY = "github_scope"
    
    def __init__(self):
        logger.debug("凭证管理器初始化")
    
    def save_credential(self, credential: GitHubCredential) -> bool:
        """
        保存GitHub凭证
        
        Args:
            credential: GitHub凭证对象
            
        Returns:
            是否保存成功
        """
        try:
            # 存储访问令牌（主要凭证）
            keyring.set_password(
                self.SERVICE_NAME,
                self.TOKEN_KEY,
                credential.access_token
            )
            
            # 存储用户名
            if credential.username:
                keyring.set_password(
                    self.SERVICE_NAME,
                    self.USERNAME_KEY,
                    credential.username
                )
            
            # 存储用户ID
            if credential.user_id is not None:
                keyring.set_password(
                    self.SERVICE_NAME,
                    self.USER_ID_KEY,
                    str(credential.user_id)
                )
            
            # 存储头像URL
            if credential.avatar_url:
                keyring.set_password(
                    self.SERVICE_NAME,
                    self.AVATAR_KEY,
                    credential.avatar_url
                )
            
            # 存储scope
            if credential.scope:
                keyring.set_password(
                    self.SERVICE_NAME,
                    self.SCOPE_KEY,
                    credential.scope
                )
            
            logger.info(f"凭证已安全存储: {credential.username or 'unknown'}")
            return True
            
        except Exception as e:
            logger.error(f"保存凭证失败: {e}")
            return False
    
    def load_credential(self) -> Optional[GitHubCredential]:
        """
        加载已保存的GitHub凭证
        
        Returns:
            GitHubCredential对象，如果不存在则返回None
        """
        try:
            # 获取访问令牌
            access_token = keyring.get_password(self.SERVICE_NAME, self.TOKEN_KEY)
            
            if not access_token:
                logger.debug("未找到已保存的凭证")
                return None
            
            # 获取其他信息
            username = keyring.get_password(self.SERVICE_NAME, self.USERNAME_KEY)
            user_id_str = keyring.get_password(self.SERVICE_NAME, self.USER_ID_KEY)
            avatar_url = keyring.get_password(self.SERVICE_NAME, self.AVATAR_KEY)
            scope = keyring.get_password(self.SERVICE_NAME, self.SCOPE_KEY) or ""
            
            user_id = int(user_id_str) if user_id_str else None
            
            credential = GitHubCredential(
                access_token=access_token,
                username=username,
                user_id=user_id,
                avatar_url=avatar_url,
                scope=scope,
            )
            
            logger.info(f"已加载凭证: {credential.username or 'unknown'}")
            return credential
            
        except Exception as e:
            logger.error(f"加载凭证失败: {e}")
            return None
    
    def delete_credential(self) -> bool:
        """
        删除保存的GitHub凭证
        
        Returns:
            是否删除成功
        """
        try:
            keys = [
                self.TOKEN_KEY,
                self.USERNAME_KEY,
                self.USER_ID_KEY,
                self.AVATAR_KEY,
                self.SCOPE_KEY,
            ]
            
            for key in keys:
                try:
                    keyring.delete_password(self.SERVICE_NAME, key)
                except keyring.errors.PasswordDeleteError:
                    # 密码不存在，忽略
                    pass
            
            logger.info("凭证已删除")
            return True
            
        except Exception as e:
            logger.error(f"删除凭证失败: {e}")
            return False
    
    def has_credential(self) -> bool:
        """
        检查是否存在已保存的凭证
        
        Returns:
            是否存在凭证
        """
        try:
            token = keyring.get_password(self.SERVICE_NAME, self.TOKEN_KEY)
            return token is not None
        except Exception:
            return False
    
    def get_access_token(self) -> Optional[str]:
        """
        获取访问令牌
        
        Returns:
            访问令牌字符串，如果不存在则返回None
        """
        try:
            return keyring.get_password(self.SERVICE_NAME, self.TOKEN_KEY)
        except Exception as e:
            logger.error(f"获取访问令牌失败: {e}")
            return None


# 全局凭证管理器实例
credential_manager = CredentialManager()
