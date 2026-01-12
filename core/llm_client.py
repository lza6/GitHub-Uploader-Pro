"""
GitHub Uploader Pro - LLM Client
OpenAI 兼容的 AI 客户端，用于智能辅助功能
"""
import httpx
from typing import List, Dict, Optional, Any
from loguru import logger
from utils.config import config


class LLMClient:
    """
    OpenAI 兼容的 AI 客户端
    提供对话和规则生成能力
    """
    
    def __init__(self):
        self._timeout = 60.0 # 增加超时时间以应对复杂生成
    
    async def chat(self, messages: List[Dict[str, str]]) -> Optional[str]:
        """
        发送聊天请求 (非流式)
        """
        api_url = config.get("ai_url", "https://api.openai.com/v1").rstrip("/")
        api_key = config.get("ai_key", "")
        model = config.get("ai_model", "gpt-3.5-turbo")
        
        if not api_key:
            logger.warning("AI API Key 未设置，无法调用智能助手")
            return "错误: 请在设置中配置 AI API Key"
        
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {
            "model": model, 
            "messages": [{"role": "system", "content": config.get("ai_system_prompt", "你是一个专业的助手。")}, *messages],
            "temperature": 0.7,
            "stream": False
        }
        
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(f"{api_url}/chat/completions", headers=headers, json=payload)
                if response.status_code == 200:
                    data = response.json()
                    content = data['choices'][0]['message']['content']
                    logger.info(f"AI 请求成功 | 响应长度: {len(content)}")
                    return content
                else:
                    error_msg = f"AI 请求失败: {response.status_code} - {response.text}"
                    logger.error(error_msg)
                    return f"API 错误: {response.status_code}"
        except Exception as e:
            logger.exception(f"调用 AI 出错: {e}")
            return f"网络异常: {str(e)}"

    async def chat_stream(self, messages: List[Dict[str, str]]):
        """
        发送聊天请求 (流式生成器)
        """
        api_url = config.get("ai_url", "https://api.openai.com/v1").rstrip("/")
        api_key = config.get("ai_key", "")
        model = config.get("ai_model", "gpt-3.5-turbo")
        
        if not api_key:
            logger.warning("AI API Key 未设置，无法调用智能助手")
            yield "错误: 请在设置中配置 AI API Key"
            return
        
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {
            "model": model, 
            "messages": [{"role": "system", "content": config.get("ai_system_prompt", "你是一个专业的助手。")}, *messages],
            "temperature": 0.7,
            "stream": True
        }
        
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                async with client.stream("POST", f"{api_url}/chat/completions", headers=headers, json=payload) as response:
                    if response.status_code != 200:
                        err = f"API 错误: {response.status_code}"
                        logger.error(f"{err} - {await response.aread()}")
                        yield err
                        return
                    
                    import json
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:].strip()
                            if data_str == "[DONE]": break
                            try:
                                chunk = json.loads(data_str)
                                choices = chunk.get('choices', [])
                                if choices:
                                    content = choices[0].get('delta', {}).get('content', '')
                                    if content: yield content
                            except Exception as e:
                                logger.error(f"解析流式响应块失败: {e}")
        except Exception as e:
            logger.exception(f"流式请求出错: {e}")
            yield f"网络异常: {str(e)}"

    async def analyze_git_error(self, error_msg: str, context: Optional[str] = None) -> Dict[str, Any]:
        """
        V4 Nebula 专属：Git 错误自愈分析引擎
        返回修复建议和自动化指令执行建议
        """
        system_prompt = """你是一个专业的 Git 顾问。
你的任务是分析 Git 错误日志，并给出：
1. 问题本质原因 (Cause)
2. 修复建议 (Recommendation)
3. 是否可以安全地执行 'force push' (SafeForcePush: true/false)
4. 具体的修复命令序列 (Commands)
请以 JSON 格式返回。"""
        
        prompt = f"Git 错误日志: \n{error_msg}\n\n环境上下文: {context or '未知'}\n\n请按要求的 JSON 格式分析。"
        messages = [{"role": "user", "content": prompt}]
        
        # 强制设置系统提示词
        api_url = config.get("ai_url", "https://api.openai.com/v1").rstrip("/")
        api_key = config.get("ai_key", "")
        model = config.get("ai_model", "gpt-3.5-turbo")
        
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                *messages
            ],
            "response_format": {"type": "json_object"}
        }

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(f"{api_url}/chat/completions", headers=headers, json=payload)
                if response.status_code == 200:
                    import json
                    return json.loads(response.json()['choices'][0]['message']['content'])
        except Exception as e:
            logger.error(f"AI 自愈分析失败: {e}")
        
        return {"error": "AI 分析引擎暂不可用"}

    def generate_gitignore(self, project_structure: str) -> Optional[str]:
        """
        根据项目结构生成 .gitignore 内容 (同步调用封装)
        """
        import asyncio
        
        prompt = f"请根据以下项目目录结构，为我生成一份专业的 .gitignore 文件内容。只需返回文件内容本身，不要有其他解释：\n\n{project_structure}"
        messages = [{"role": "user", "content": prompt}]
        
        # 对于同步环境调用异步，使用特殊处理
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 如果已经在运行，返回错误或使用特殊方案
                return "错误: AI 请求正在处理中"
            return loop.run_until_complete(self.chat(messages))
        except Exception:
            # 备选方案：新建临时 loop
            return asyncio.run(self.chat(messages))


# 单例
llm_client = LLMClient()
