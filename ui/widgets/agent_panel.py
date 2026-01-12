import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLineEdit,
    QPushButton, QLabel, QScrollArea, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, pyqtSlot, QTimer
from loguru import logger

from .glass_widgets import GlassPanel, SectionTitle, IconButton
from ..theme_manager import theme_manager
from core.llm_client import llm_client
from core.git_status_provider import GitStatusProvider


class AIWorker(QThread):
    """AI 请求工作线程 v4.6 [Streaming Support]"""
    chunk_received = pyqtSignal(str)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    
    def __init__(self, prompt: str, context: str = ""):
        super().__init__()
        self.prompt = prompt
        self.context = context
        self._is_running = True
        
    def run(self):
        import asyncio
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            messages = []
            if self.context:
                messages.append({"role": "system", "content": f"当前项目全量结构如下：\n{self.context}\n请基于此结构回答用户。"})
            messages.append({"role": "user", "content": self.prompt})
            
            full_response = ""
            
            async def process():
                nonlocal full_response
                async for chunk in llm_client.chat_stream(messages):
                    if not self._is_running: break
                    full_response += chunk
                    self.chunk_received.emit(chunk)
            
            loop.run_until_complete(process())
            self.finished.emit(full_response)
        except Exception as e:
            logger.exception(f"AIWorker 运行出错: {e}")
            self.error.emit(str(e))

    def stop(self):
        self._is_running = False


class AgentPanel(GlassPanel):
    """
    AI Agent 面板 (正式版 v4.6)
    支持流式响应、自动规则应用、状态指引
    """
    apply_ignore_rules = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._project_path = None
        self._current_ai_msg_id = None
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
                if item.widget(): item.widget().deleteLater()
                    
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        
        # 标题
        header = QHBoxLayout()
        header.addWidget(SectionTitle("🧠", "AI 智能助手 (Official)"))
        
        self._status_label = QLabel("Ready")
        self._status_label.setStyleSheet(f"color: {c['text_muted']}; font-size: 11px;")
        header.addWidget(self._status_label)
        
        self._clear_btn = IconButton("🗑️", size=24)
        self._clear_btn.clicked.connect(self._clear_chat)
        header.addStretch()
        header.addWidget(self._clear_btn)
        layout.addLayout(header)
        
        # 对话展示区
        self._chat_display = QTextEdit()
        self._chat_display.setReadOnly(True)
        self._chat_display.setStyleSheet(f"""
            QTextEdit {{
                background: {c['bg_primary']};
                border: 1px solid {c['border']};
                border-radius: 8px;
                padding: 10px;
                color: {c['text_primary']};
                line-height: 1.5;
            }}
        """)
        self._chat_display.setMinimumHeight(200)
        layout.addWidget(self._chat_display)
        
        # 快捷指令
        shortcuts = QHBoxLayout()
        self._btn_gen_ignore = QPushButton("⚡ 生成 .gitignore")
        self._btn_gen_ignore.clicked.connect(self._on_gen_ignore)
        shortcuts.addWidget(self._btn_gen_ignore)
        
        self._btn_analyze = QPushButton("🔍 分析项目")
        self._btn_analyze.clicked.connect(self._on_analyze)
        shortcuts.addWidget(self._btn_analyze)
        
        layout.addLayout(shortcuts)
        
        # 输入区
        input_layout = QHBoxLayout()
        self._input = QLineEdit()
        self._input.setPlaceholderText("在此输入指令，如：'我的项目有哪些冗余文件？'...")
        self._input.returnPressed.connect(self._send_command)
        input_layout.addWidget(self._input)
        
        self._send_btn = IconButton("🚀", size=32)
        self._send_btn.clicked.connect(self._send_command)
        input_layout.addWidget(self._send_btn)
        
        layout.addLayout(input_layout)
        
        self._append_message("系统", "你好！我是你的 AI 助手（正式版）。我支持<b>流式响应</b>，并且可以直接帮你创建 <b>.gitignore</b> 文件。")

    def set_project_path(self, path: str):
        self._project_path = path

    def _append_message(self, sender: str, msg: str, is_stream=False):
        c = theme_manager.colors
        sender_color = c['accent'] if sender == "AI" else c['info']
        if sender == "系统": sender_color = c['text_muted']
        
        br = "<br>"
        if is_stream and sender == "AI":
            # 如果是流式，我们不新开一行，而是找到最后一个 AI 消息块追加
            # 这里简单起见，使用 QTextCursor
            cursor = self._chat_display.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            self._chat_display.insertHtml(msg.replace("\n", br))
            # 自动滚动到最下方
            self._chat_display.verticalScrollBar().setValue(
                self._chat_display.verticalScrollBar().maximum()
            )
            return

        html = f"<div style='margin-top: 10px; margin-bottom: 5px;'><b style='color: {sender_color};'>{sender}:</b></div>"
        msg_html = msg.replace("\n", br)
        if sender == "AI":
            html += f"<div id='ai_msg_current' style='color: {c['text_primary']};'>{msg_html}</div>"
        else:
            html += f"<div style='color: {c['text_primary']};'>{msg_html}</div>"
            
        self._chat_display.append(html)
        self._chat_display.verticalScrollBar().setValue(
            self._chat_display.verticalScrollBar().maximum()
        )

    def _send_command(self, silent=False):
        cmd = self._input.text().strip()
        if not cmd: return
        
        # 特殊逻辑：如果用户说“是”或“应用”，且当前有待应用的规则
        if cmd.lower() in ["是", "ok", "yes", "apply", "应用", "好", "可以"] and hasattr(self, "_pending_ignore_rule"):
            if not silent: self._append_message("我", cmd)
            self._input.clear()
            self._apply_ignore_logic(self._pending_ignore_rule)
            return

        if not silent: self._append_message("我", cmd)
        self._input.clear()
        self._input.setEnabled(False)
        self._send_btn.setEnabled(False)
        self._set_status("正在思考 (Thinking)...")
        
        # 获取项目上下文
        context = self._get_project_context()
        
        self._worker = AIWorker(cmd, context)
        self._worker.chunk_received.connect(self._on_chunk_received)
        self._worker.finished.connect(self._on_ai_finished)
        self._worker.error.connect(self._on_ai_error)
        
        # 预先添加 AI 消息头
        c = theme_manager.colors
        self._chat_display.append(f"<div style='margin-top: 10px; margin-bottom: 5px;'><b style='color: {c['accent']};'>AI:</b></div>")
        self._is_first_chunk = True
        self._worker.start()

    def _set_status(self, text: str):
        self._status_label.setText(text)
        logger.debug(f"AI Status: {text}")

    @pyqtSlot(str)
    def _on_chunk_received(self, chunk: str):
        if self._is_first_chunk:
            self._set_status("正在回复 (Responding)...")
            self._is_first_chunk = False
        self._append_message("AI", chunk, is_stream=True)

    @pyqtSlot(str)
    def _on_ai_finished(self, result: str):
        self._input.setEnabled(True)
        self._send_btn.setEnabled(True)
        self._set_status("Ready")
        
        # 如果包含明显的 gitignore 规则且当前项目缺少它，则静默应用
        if "#" in result and ("ignore" in result.lower() or "venv" in result or "*" in result):
            self._auto_apply_ignore(result)

    def _auto_apply_ignore(self, result: str):
        """检测并直接应用 ignore 规则 (静默模式)"""
        # 如果项目没有 .gitignore，直接帮用户写一个
        if self._project_path and not os.path.exists(os.path.join(self._project_path, ".gitignore")):
            self._apply_ignore_logic(result, silent=True)

    @pyqtSlot(str)
    def _on_ai_error(self, error_msg: str):
        self._input.setEnabled(True)
        self._send_btn.setEnabled(True)
        self._set_status("Error")
        self._append_message("系统", f"AI 请求发生错误: {error_msg}")

    def _apply_ignore_logic(self, content: str, silent: bool = False):
        if not self._project_path: return
            
        file_path = os.path.join(self._project_path, ".gitignore")
        
        # 提取内容
        final_content = content
        import re
        code_match = re.search(r"```(?:\w+)?\n(.*?)```", content, re.DOTALL)
        if code_match:
            final_content = code_match.group(1).strip()
        else:
            # 清洗处理
            lines = [l for l in content.split("\n") if l.strip()]
            valid_lines = []
            for l in lines:
                l_s = l.strip()
                if l_s.startswith(("#", "*", "/")) or "." in l_s or "/" in l_s:
                    if "收到" in l_s or "基于" in l_s or "AI:" in l_s: continue
                    valid_lines.append(l_s)
            final_content = "\n".join(valid_lines)

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(final_content)
            
            logger.success(f"AI 助手已静默保存 .gitignore: {file_path}")
            self._append_message("系统", f"✨ <b>AI 已自动补全项目配置</b>: <code style='color: #4CAF50;'>.gitignore</code> 已就绪并应用。")
            
            # 手动刷新预览（如果连接了信号）
            self.apply_ignore_rules.emit(file_path)
            
            if not silent:
                QMessageBox.information(self, "AI 助手", "已为您自动生成并保存 .gitignore 文件，项目预览已同步刷新。")
        except Exception as e:
            logger.error(f"自动化写入 .gitignore 失败: {e}")

    def _get_project_context(self) -> str:
        """获取项目全量树上下文 v4.3"""
        if not self._project_path: return ""
        try:
            provider = GitStatusProvider(self._project_path)
            return provider.get_project_tree()
        except Exception as e:
            logger.error(f"AI 获取项目树失败: {e}")
            return ""

    def _on_gen_ignore(self):
        if not self._project_path:
            self._append_message("系统", "请先选择文件夹。")
            return
            
        self._input.setText("请根据当前项目全量结构，为我生成一个符合规范的 .gitignore 内容。只需返回规则内容，不要废话。")
        self._send_command(silent=True)
        self._append_message("我", "⚡ 正在生成 .gitignore...")

    def _on_analyze(self):
        if not self._project_path:
            self._append_message("系统", "请先选择文件夹。")
            return
            
        self._input.setText("请分析一下我这个项目的技术栈，并给出一些优化建议。")
        self._send_command(silent=True)
        self._append_message("我", "🔍 正在进行全量项目扫描与分析...")

    def _clear_chat(self):
        self._chat_display.clear()
        self._append_message("系统", "聊天记录已清空。")
