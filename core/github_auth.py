"""
GitHub Uploader Pro - GitHub OAuth认证
使用Device Flow进行GitHub OAuth认证
或使用GitHub CLI进行认证
"""
import time
import threading
import webbrowser
import subprocess
from typing import Optional, Callable
from dataclasses import dataclass
import httpx
from loguru import logger

from .credential_manager import credential_manager, GitHubCredential
from utils.config import config


@dataclass
class DeviceCodeResponse:
    """设备码响应"""
    device_code: str
    user_code: str
    verification_uri: str
    expires_in: int
    interval: int


@dataclass
class AuthResult:
    """认证结果"""
    success: bool
    credential: Optional[GitHubCredential] = None
    error: Optional[str] = None


class GitHubAuth:
    """
    GitHub OAuth认证管理器
    使用Device Flow进行认证，适合桌面应用
    """
    
    def __init__(self):
        self._polling_thread: Optional[threading.Thread] = None
        self._stop_polling = threading.Event()
        self._on_auth_complete: Optional[Callable[[AuthResult], None]] = None
        self._on_user_code_ready: Optional[Callable[[str, str], None]] = None
        
        # HTTP客户端
        self._client = httpx.Client(
            timeout=30.0,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": f"{config.APP_NAME}/{config.APP_VERSION}"
            }
        )
    
    def __del__(self):
        self.cancel_auth()
        self._client.close()
    
    @property
    def client_id(self) -> str:
        """获取GitHub Client ID"""
        return config.GITHUB_CLIENT_ID
    
    def is_authenticated(self) -> bool:
        """检查是否已认证"""
        return credential_manager.has_credential()
    
    def get_current_user(self) -> Optional[GitHubCredential]:
        """获取当前登录用户"""
        return credential_manager.load_credential()
    
    def start_device_auth(
        self,
        on_user_code_ready: Callable[[str, str], None],
        on_complete: Callable[[AuthResult], None],
    ) -> bool:
        """
        开始设备流认证
        
        Args:
            on_user_code_ready: 用户码准备好时的回调 (user_code, verification_uri)
            on_complete: 认证完成时的回调
            
        Returns:
            是否成功开始认证流程
        """
        self._on_user_code_ready = on_user_code_ready
        self._on_auth_complete = on_complete
        self._stop_polling.clear()
        
        try:
            # 请求设备码
            device_code_response = self._request_device_code()
            if not device_code_response:
                on_complete(AuthResult(success=False, error="获取设备码失败"))
                return False
            
            # 通知UI显示用户码
            on_user_code_ready(
                device_code_response.user_code,
                device_code_response.verification_uri
            )
            
            # 在浏览器中打开验证页面
            webbrowser.open(device_code_response.verification_uri)
            logger.info(f"请在浏览器中输入代码: {device_code_response.user_code}")
            
            # 启动轮询线程
            self._polling_thread = threading.Thread(
                target=self._poll_for_token,
                args=(device_code_response,),
                daemon=True
            )
            self._polling_thread.start()
            
            return True
            
        except Exception as e:
            logger.error(f"启动认证失败: {e}")
            on_complete(AuthResult(success=False, error=str(e)))
            return False
    
    def start_gh_cli_auth(
        self,
        on_complete: Callable[[AuthResult], None],
    ) -> bool:
        """
        使用 GitHub CLI 进行认证（推荐方式）
        
        Args:
            on_complete: 认证完成时的回调
            
        Returns:
            是否成功开始认证流程
        """
        self._on_auth_complete = on_complete
        
        try:
            # 检查是否已登录
            import sys
            encoding = 'gbk' if sys.platform == 'win32' else 'utf-8'
            result = subprocess.run(
                ["gh", "auth", "status"],
                capture_output=True,
                text=True,
                encoding=encoding,
                errors='ignore',
                timeout=5
            )
            
            if result.returncode == 0:
                # 已登录，获取 token
                logger.info("检测到 GitHub CLI 已登录")
                return self._get_gh_cli_token(on_complete)
            else:
                # 未登录，返回特殊错误码，让 UI 处理
                logger.info("GitHub CLI 未登录，需要用户登录")
                on_complete(AuthResult(
                    success=False,
                    error="NOT_LOGGED_IN"  # 特殊标记，表示需要打开终端登录
                ))
                return False
                
        except FileNotFoundError:
            on_complete(AuthResult(
                success=False,
                error="未找到 GitHub CLI (gh)\n\n"
                      "请安装 GitHub CLI: https://cli.github.com/\n"
                      "或者使用其他登录方式"
            ))
            return False
        except Exception as e:
            logger.error(f"GitHub CLI 认证失败: {e}")
            on_complete(AuthResult(success=False, error=str(e)))
            return False
    
    def _get_gh_cli_token(
        self,
        on_complete: Callable[[AuthResult], None],
    ) -> bool:
        """从 GitHub CLI 获取访问令牌"""
        try:
            # 获取 token
            import sys
            encoding = 'gbk' if sys.platform == 'win32' else 'utf-8'
            result = subprocess.run(
                ["gh", "auth", "token"],
                capture_output=True,
                text=True,
                encoding=encoding,
                errors='ignore',
                timeout=10
            )
            
            if result.returncode != 0:
                on_complete(AuthResult(
                    success=False,
                    error=f"获取 GitHub CLI token 失败: {result.stderr}"
                ))
                return False
            
            access_token = result.stdout.strip()
            
            # 获取用户信息
            user_info = self._get_user_info(access_token)
            
            if not user_info:
                on_complete(AuthResult(
                    success=False,
                    error="获取用户信息失败"
                ))
                return False
            
            credential = GitHubCredential(
                access_token=access_token,
                scope="repo,read:user",
                username=user_info.get("login"),
                user_id=user_info.get("id"),
                avatar_url=user_info.get("avatar_url"),
            )
            
            # 保存凭证
            credential_manager.save_credential(credential)
            
            on_complete(AuthResult(
                success=True,
                credential=credential
            ))
            return True
            
        except Exception as e:
            logger.error(f"获取 GitHub CLI token 失败: {e}")
            on_complete(AuthResult(success=False, error=str(e)))
            return False
    
    def _request_device_code(self) -> Optional[DeviceCodeResponse]:
        """请求设备码"""
        try:
            response = self._client.post(
                config.GITHUB_DEVICE_CODE_URL,
                data={
                    "client_id": self.client_id,
                    "scope": config.GITHUB_SCOPES,
                }
            )
            
            # 检查响应状态
            if response.status_code == 404:
                logger.error(f"请求设备码失败: Client ID 无效或未启用 Device Flow")
                logger.error(f"当前 Client ID: {self.client_id}")
                logger.error(f"请检查配置文件中的 GITHUB_CLIENT_ID 是否正确")
                return None
            elif response.status_code == 400:
                logger.error(f"请求设备码失败: 请求参数错误")
                logger.error(f"响应内容: {response.text}")
                return None
            
            response.raise_for_status()
            data = response.json()
            
            return DeviceCodeResponse(
                device_code=data["device_code"],
                user_code=data["user_code"],
                verification_uri=data["verification_uri"],
                expires_in=data["expires_in"],
                interval=data["interval"],
            )
            
        except Exception as e:
            logger.error(f"请求设备码失败: {e}")
            return None
    
    def _poll_for_token(self, device_code_response: DeviceCodeResponse) -> None:
        """轮询获取访问令牌"""
        interval = device_code_response.interval
        expires_at = time.time() + device_code_response.expires_in
        
        while not self._stop_polling.is_set():
            # 检查是否过期
            if time.time() > expires_at:
                self._complete_auth(AuthResult(
                    success=False,
                    error="验证码已过期，请重新登录"
                ))
                return
            
            # 等待间隔
            if self._stop_polling.wait(interval):
                return  # 被取消
            
            # 请求令牌
            try:
                response = self._client.post(
                    config.GITHUB_TOKEN_URL,
                    data={
                        "client_id": self.client_id,
                        "device_code": device_code_response.device_code,
                        "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                    }
                )
                data = response.json()
                
                if "access_token" in data:
                    # 成功获取令牌
                    access_token = data["access_token"]
                    scope = data.get("scope", "")
                    
                    # 获取用户信息
                    user_info = self._get_user_info(access_token)
                    
                    credential = GitHubCredential(
                        access_token=access_token,
                        scope=scope,
                        username=user_info.get("login") if user_info else None,
                        user_id=user_info.get("id") if user_info else None,
                        avatar_url=user_info.get("avatar_url") if user_info else None,
                    )
                    
                    # 保存凭证
                    credential_manager.save_credential(credential)
                    
                    self._complete_auth(AuthResult(
                        success=True,
                        credential=credential
                    ))
                    return
                
                elif "error" in data:
                    error = data["error"]
                    
                    if error == "authorization_pending":
                        # 用户还未授权，继续轮询
                        continue
                    elif error == "slow_down":
                        # 轮询太快，增加间隔
                        interval += 5
                        continue
                    elif error == "expired_token":
                        self._complete_auth(AuthResult(
                            success=False,
                            error="验证码已过期"
                        ))
                        return
                    elif error == "access_denied":
                        self._complete_auth(AuthResult(
                            success=False,
                            error="用户拒绝授权"
                        ))
                        return
                    else:
                        self._complete_auth(AuthResult(
                            success=False,
                            error=f"认证错误: {error}"
                        ))
                        return
                        
            except Exception as e:
                logger.warning(f"轮询令牌失败: {e}")
                # 继续尝试
    
    def _get_user_info(self, access_token: str) -> Optional[dict]:
        """获取GitHub用户信息"""
        try:
            response = self._client.get(
                f"{config.GITHUB_API_URL}/user",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"获取用户信息失败: {e}")
            return None
    
    def _complete_auth(self, result: AuthResult) -> None:
        """完成认证流程"""
        if self._on_auth_complete:
            self._on_auth_complete(result)
    
    def cancel_auth(self) -> None:
        """取消正在进行的认证"""
        self._stop_polling.set()
        if self._polling_thread and self._polling_thread.is_alive():
            self._polling_thread.join(timeout=2)
        logger.info("认证已取消")
    
    def logout(self) -> bool:
        """登出"""
        self.cancel_auth()
        success = credential_manager.delete_credential()
        if success:
            logger.info("已登出")
        return success
    
    def refresh_user_info(self) -> Optional[GitHubCredential]:
        """刷新用户信息"""
        credential = credential_manager.load_credential()
        if not credential:
            return None
        
        user_info = self._get_user_info(credential.access_token)
        if user_info:
            credential.username = user_info.get("login")
            credential.user_id = user_info.get("id")
            credential.avatar_url = user_info.get("avatar_url")
            credential_manager.save_credential(credential)
        
        return credential


# 全局认证管理器实例
github_auth = GitHubAuth()
