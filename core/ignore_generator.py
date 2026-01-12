"""
GitHub Uploader Pro - 智能忽略文件生成器
支持 AI 生成与本地全量模板兜底，实现零交互自动补全
"""
import os
import asyncio
from typing import Optional, List
from loguru import logger
from .llm_client import llm_client

class IgnoreGenerator:
    """.gitignore 生成专家"""
    
    # 内置硬核模版 (Fallback)
    TEMPLATES = {
        "python": """# Python 核心忽略规则
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST
.env
.venv
venv/
env/
.idea/
.vscode/
*.swp
*.log
""",
        "web": """# Web/Node 核心忽略规则
node_modules/
dist/
build/
.next/
.nuxt/
.cache/
*.log
.env
.env.local
.vscode/
.idea/
.DS_Store
""",
        "generic": """# 通用忽略规则
.DS_Store
Thumbs.db
Desktop.ini
*.log
.idea/
.vscode/
*.swp
venv/
node_modules/
"""
    }

    @classmethod
    async def generate_and_save(cls, folder_path: str, force_ai: bool = False) -> bool:
        """
        生成并保存 .gitignore。
        如果 AI 响应快则用 AI，否则或失败则用内置模版。
        """
        ignore_path = os.path.join(folder_path, ".gitignore")
        if os.path.exists(ignore_path):
            return True # 已存在，跳过

        logger.info(f"检测到缺失 .gitignore，启动自动补全程序: {folder_path}")
        
        content = None
        
        # 1. 尝试分析项目类型
        project_type = cls._detect_project_type(folder_path)
        
        # 2. 尝试 AI 生成 (带超时和异常保护)
        try:
            context = cls._get_folder_structure_summary(folder_path)
            prompt = [
                {"role": "user", "content": f"请为以下项目结构生成一个最专业的 .gitignore。只需返回规则内容本身，不要任何废话。内容建议包含核心忽略项。项目结构预览：\n{context}"}
            ]
            # 这里的 chat 是非流式的，方便直接获取
            logger.debug(f"尝试 AI 自动辅助生成规则 (Project: {project_type})...")
            ai_content = await asyncio.wait_for(llm_client.chat(prompt), timeout=8.0)
            if ai_content and ("ignore" in ai_content or "*" in ai_content or "/" in ai_content):
                # 清洗可能的 Markdown 标记
                import re
                code_match = re.search(r"```(?:\w+)?\n(.*?)```", ai_content, re.DOTALL)
                content = code_match.group(1).strip() if code_match else ai_content.strip()
                logger.info("AI 自动规则生成成功")
        except Exception as e:
            logger.warning(f"AI 自动生成规则失败或超时，将切换至本地内置模版: {e}")

        # 3. 兜底逻辑：使用内置模版
        if not content:
            content = cls.TEMPLATES.get(project_type, cls.TEMPLATES["generic"])
            logger.info(f"使用本地内置 [{project_type}] 模版完成生成")

        # 4. 物理写入
        try:
            with open(ignore_path, "w", encoding="utf-8") as f:
                f.write(content)
            return True
        except Exception as e:
            logger.error(f"静默保存 .gitignore 失败: {e}")
            return False

    @classmethod
    def _detect_project_type(cls, folder_path: str) -> str:
        """识别项目主要语言/框架"""
        try:
            files = os.listdir(folder_path)
            if any(f.endswith(".py") or f == "requirements.txt" for f in files):
                return "python"
            if "package.json" in files or "node_modules" in files:
                return "web"
        except:
            pass
        return "generic"

    @classmethod
    def _get_folder_structure_summary(cls, folder_path: str) -> str:
        """获取简单的目录摘要"""
        try:
            items = os.listdir(folder_path)[:20] # 仅截取前20个方便 AI 参考
            return "\n".join(items)
        except:
            return "Unknown Structure"

ignore_generator = IgnoreGenerator()
