"""
OpenClaw服务 - 与OpenClaw后端集成
"""

import httpx
import json
import asyncio
from typing import Optional, Dict, List, AsyncIterator
from datetime import datetime

from ..models.schemas import (
    ChatMessage, ChatRequest, ChatResponse,
    MessageRole, OpenClawConfig
)


class OpenClawService:
    """OpenClaw服务：与OpenClaw后端通信的封装"""

    def __init__(self, config: Optional[OpenClawConfig] = None):
        self.config = config or OpenClawConfig()
        self._sessions: Dict[str, List[ChatMessage]] = {}
        self._connected = False

    def _get_session(self, session_id: str) -> List[ChatMessage]:
        """获取或创建会话"""
        if session_id not in self._sessions:
            self._sessions[session_id] = []
        return self._sessions[session_id]

    async def check_connection(self) -> bool:
        """检查OpenClaw连接状态"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"{self.config.api_url}/health",
                    headers=self._get_headers()
                )
                self._connected = response.status_code == 200
                return self._connected
        except Exception as e:
            print(f"OpenClaw connection check failed: {e}")
            self._connected = False
            return False

    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        return headers

    async def send_message(self, request: ChatRequest) -> ChatResponse:
        """发送消息并获取响应"""
        session = self._get_session(request.session_id)

        # 添加用户消息到会话
        user_message = ChatMessage(
            role=MessageRole.USER,
            content=request.message,
            timestamp=datetime.now()
        )
        session.append(user_message)

        # 构建上下文
        context = request.context or session[-10:]  # 保留最近10条消息
        context_text = "\n".join([f"{msg.role}: {msg.content}" for msg in context])

        # 调用OpenClaw API
        try:
            response_content = await self._call_openclaw(
                message=request.message,
                context=context_text
            )
        except Exception as e:
            # 如果OpenClaw不可用，使用本地模拟响应
            response_content = await self._generate_fallback_response(
                message=request.message,
                context=context_text
            )

        # 创建助手消息
        assistant_message = ChatMessage(
            role=MessageRole.ASSISTANT,
            content=response_content,
            timestamp=datetime.now(),
            metadata={"model": self.config.model}
        )
        session.append(assistant_message)

        # 生成建议回复
        suggestions = self._generate_suggestions(response_content)

        return ChatResponse(
            message=assistant_message,
            session_id=request.session_id,
            suggestions=suggestions
        )

    async def _call_openclaw(self, message: str, context: str) -> str:
        """调用OpenClaw API"""
        payload = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": self._get_system_prompt()},
                {"role": "user", "content": f"上下文:\n{context}\n\n用户: {message}"}
            ],
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.config.api_url}/v1/chat/completions",
                headers=self._get_headers(),
                json=payload
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]

    def _get_system_prompt(self) -> str:
        """获取系统提示"""
        return """你是一个智能助手，可以帮助用户：
1. 回答各种问题
2. 讨论新闻和技术话题
3. 提供分析和见解
4. 帮助解决问题

请用简洁、有条理的方式回答。如果涉及新闻分析，可以引用相关新闻内容。"""

    async def _generate_fallback_response(self, message: str, context: str) -> str:
        """当OpenClaw不可用时，生成本地响应"""
        message_lower = message.lower()

        # 检测意图并生成适当响应
        if any(word in message_lower for word in ["新闻", "news", "最新"]):
            return (
                "我目前无法连接到OpenClaw服务，但您可以：\n"
                "1. 点击左侧'新闻'选项查看最新新闻\n"
                "2. 选择感兴趣的新闻查看相关思维导图\n"
                "3. 直接向我提问关于新闻内容的问题"
            )
        elif any(word in message_lower for word in ["你好", "hello", "hi", "嗨"]):
            return "你好！我是智能助手，可以帮助你查看新闻和分析内容。请问有什么可以帮助你的？"
        elif any(word in message_lower for word in ["思维导图", "mind map", "关系图"]):
            return "要查看思维导图，请先在左侧选择'新闻'，然后点击感兴趣的新闻条目，右侧将显示对应的思维导图。"
        else:
            return (
                f"收到你的消息: {message[:50]}...\n\n"
                "当前系统功能：\n"
                "- 新闻阅读：点击左侧'新闻'选项\n"
                "- 思维导图：选择新闻后自动生成\n"
                "- 智能对话：随时向我提问\n\n"
                "请问有什么可以帮助你的？"
            )

    def _generate_suggestions(self, response: str) -> List[str]:
        """从响应中提取建议回复"""
        suggestions = []

        # 基于响应内容生成建议
        if "新闻" in response:
            suggestions.append("查看最新新闻")
        if "思维导图" in response:
            suggestions.append("生成思维导图")
        if "分析" in response:
            suggestions.append("深入分析这个话题")

        # 默认建议
        if not suggestions:
            suggestions = [
                "了解更多",
                "还有别的吗",
                "详细说说"
            ]

        return suggestions[:3]

    async def stream_message(self, request: ChatRequest) -> AsyncIterator[str]:
        """流式发送消息（如果OpenClaw支持）"""
        session = self._get_session(request.session_id)
        context = request.context or session[-10:]
        context_text = "\n".join([f"{msg.role}: {msg.content}" for msg in context])

        try:
            async for chunk in self._stream_openclaw(
                message=request.message,
                context=context_text
            ):
                yield chunk
        except Exception:
            # 回退到非流式响应
            response = await self._generate_fallback_response(
                request.message,
                context_text
            )
            for char in response:
                yield char
                await asyncio.sleep(0.01)

    async def _stream_openclaw(self, message: str, context: str) -> AsyncIterator[str]:
        """流式调用OpenClaw API"""
        payload = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": self._get_system_prompt()},
                {"role": "user", "content": f"上下文:\n{context}\n\n用户: {message}"}
            ],
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "stream": True
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                "POST",
                f"{self.config.api_url}/v1/chat/completions",
                headers=self._get_headers(),
                json=payload
            ) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        chunk = json.loads(data)
                        content = chunk["choices"][0]["delta"].get("content", "")
                        if content:
                            yield content

    def clear_session(self, session_id: str):
        """清除会话历史"""
        if session_id in self._sessions:
            self._sessions[session_id] = []

    def get_session_history(self, session_id: str) -> List[ChatMessage]:
        """获取会话历史"""
        return self._get_session(session_id)

    def get_connection_status(self) -> Dict:
        """获取连接状态"""
        return {
            "connected": self._connected,
            "api_url": self.config.api_url,
            "model": self.config.model,
            "sessions_count": len(self._sessions)
        }
