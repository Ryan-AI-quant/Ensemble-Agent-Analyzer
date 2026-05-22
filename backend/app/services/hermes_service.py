"""
Hermes 服务 - 与 Ollama (Hermes) 后端集成
"""

import httpx
import json
import asyncio
from typing import Optional, Dict, List, AsyncIterator
from datetime import datetime

from ..config import HermesConfig


class HermesService:
    """Hermes 服务：与 Ollama (Hermes) 后端通信的封装"""

    def __init__(self, config: Optional[HermesConfig] = None):
        self.config = config or HermesConfig()
        self._connected = False

    async def check_connection(self) -> bool:
        """检查 Hermes 连接状态"""
        try:
            print(f"[HermesService] 尝试连接到: {self.config.api_url}")
            print(f"[HermesService] API格式: {self.config.api_format}")
            print(f"[HermesService] 模型名称: {self.config.model}")
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                # 根据 API 格式选择不同的检查端点
                headers = self._get_headers()  # ✅ 添加认证头
                
                if self.config.api_format == "openai":
                    endpoint = f"{self.config.api_url}/v1/models"
                    print(f"[HermesService] 检查端点: {endpoint}")
                    response = await client.get(endpoint, headers=headers, timeout=10.0)
                else:
                    endpoint = f"{self.config.api_url}/api/tags"
                    print(f"[HermesService] 检查端点: {endpoint}")
                    response = await client.get(endpoint, headers=headers, timeout=10.0)
                
                if response.status_code == 200:
                    self._connected = True
                    print(f"[HermesService] ✅ 连接成功 (API 格式: {self.config.api_format})")
                    return True
                elif response.status_code == 401:
                    self._connected = False
                    print(f"[HermesService] ❌ 认证失败 (HTTP 401)")
                    print(f"[HermesService] 请检查:")
                    print(f"  1. API Key是否正确: {self.config.api_key[:8]}..." if self.config.api_key else "  1. 未配置API Key")
                    print(f"  2. Agent服务是否需要认证")
                    print(f"  3. 在.env文件中配置正确的HERMES_API_KEY")
                    return False
                else:
                    self._connected = False
                    print(f"[HermesService] ❌ 连接失败: HTTP {response.status_code}")
                    return False
        except httpx.ConnectTimeout:
            print(f"[HermesService] ❌ 连接超时: {self.config.api_url} (10秒)")
            print(f"[HermesService] 请检查:")
            print(f"  1. Agent服务是否正在运行")
            print(f"  2. 地址是否正确: {self.config.api_url}")
            print(f"  3. 防火墙是否阻止了连接")
            self._connected = False
            return False
        except httpx.ConnectError as e:
            print(f"[HermesService] ❌ 连接失败: 无法连接到 {self.config.api_url}")
            print(f"[HermesService] 错误详情: {e}")
            print(f"[HermesService] 请确保Agent服务已启动并监听 {self.config.api_url}")
            self._connected = False
            return False
        except Exception as e:
            print(f"[HermesService] ❌ 连接检查失败: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            self._connected = False
            return False

    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        return headers

    async def generate(self, prompt: str, system: str = "", context: List[int] = None) -> Dict:
        """
        调用 Ollama 生成文本

        Args:
            prompt: 用户提示
            system: 系统提示（可选）
            context: 上下文 token（用于多轮对话）

        Returns:
            生成结果字典
        """
        payload = {
            "model": self.config.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self.config.temperature,
                "num_predict": self.config.max_tokens
            }
        }

        if system:
            payload["system"] = system

        if context:
            payload["context"] = context

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.config.api_url}/api/generate",
                    headers=self._get_headers(),
                    json=payload
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            raise Exception(f"Hermes API 调用失败: {str(e)}")

    async def chat_openai_format(self, messages: List[Dict], context: List[int] = None, max_tokens: int = None) -> Dict:
        """
        使用 OpenAI 兼容格式调用 Hermes (用于兼容第三方程式如 hermes-agent)
        使用 /v1/chat/completions 端点

        Args:
            messages: 消息列表 [{"role": "user", "content": "..."}]
            context: 上下文 token (用于多轮对话)
            max_tokens: 覆盖默认的最大 token 数

        Returns:
            聊天结果
        """
        payload = {
            "model": self.config.model,
            "messages": messages,
            "stream": False,
            "max_tokens": max_tokens if max_tokens is not None else self.config.max_tokens,
            "temperature": self.config.temperature
        }

        if context:
            payload["context"] = context

        try:
            async with httpx.AsyncClient(timeout=180.0) as client:
                # 使用 OpenAI 兼容格式
                response = await client.post(
                    f"{self.config.api_url}/v1/chat/completions",
                    headers=self._get_headers(),
                    json=payload
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            raise Exception(f"Hermes OpenAI 格式 API 调用失败: {str(e)}")

    async def chat(self, messages: List[Dict], context: List[int] = None) -> Dict:
        """
        调用 Ollama Chat API

        Args:
            messages: 消息列表 [{"role": "user", "content": "..."}]
            context: 上下文 token

        Returns:
            聊天结果
        """
        # 根据配置选择 API 格式
        if self.config.api_format == "openai":
            return await self.chat_openai_format(messages, context)

        # 原生 Ollama 格式
        payload = {
            "model": self.config.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": self.config.temperature,
                "num_predict": self.config.max_tokens
            }
        }

        if context:
            payload["context"] = context

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.config.api_url}/api/chat",
                    headers=self._get_headers(),
                    json=payload
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            raise Exception(f"Hermes Chat API 调用失败: {str(e)}")

    async def stream_generate(self, prompt: str, system: str = "") -> AsyncIterator[str]:
        """
        流式调用 Ollama 生成文本

        Args:
            prompt: 用户提示
            system: 系统提示

        Yields:
            生成的文本片段
        """
        payload = {
            "model": self.config.model,
            "prompt": prompt,
            "stream": True,
            "options": {
                "temperature": self.config.temperature,
                "num_predict": self.config.max_tokens
            }
        }

        if system:
            payload["system"] = system

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream(
                    "POST",
                    f"{self.config.api_url}/api/generate",
                    headers=self._get_headers(),
                    json=payload
                ) as response:
                    async for line in response.aiter_lines():
                        if line.strip():
                            try:
                                data = json.loads(line)
                                if "response" in data:
                                    yield data["response"]
                                if data.get("done", False):
                                    break
                            except json.JSONDecodeError:
                                continue
        except Exception as e:
            raise Exception(f"Hermes 流式调用失败: {str(e)}")

    async def analyze_news(self, content: str, title: str = "") -> Dict:
        """
        使用 Hermes 分析新闻内容

        Args:
            content: 新闻内容
            title: 新闻标题

        Returns:
            分析结果
        """
        system_prompt = """你是一个专业的新闻分析师。请对以下新闻内容进行深度分析，并以 JSON 格式返回分析结果。

返回格式：
{
    "title": "新闻标题",
    "summary": "50字以内的新闻摘要",
    "key_points": ["要点1", "要点2", "要点3", "要点4", "要点5"],
    "impact_analysis": ["影响分析1", "影响分析2", "影响分析3", "影响分析4", "影响分析5"],
    "related_entities": [
        {"name": "实体名称", "type": "person/organization/location", "relation": "与新闻的关系"}
    ],
    "sentiment": "positive/negative/neutral",
    "confidence": 0.85,
    "categories": ["category1", "category2"],
    "source_analysis": {
        "credibility": "high/medium/low",
        "bias": "left/center/right",
        "originality": "original/aggregated"
    }
}

请确保返回的是有效的 JSON 格式，不要有其他内容。"""

        full_content = f"标题：{title}\n\n内容：{content}" if title else content

        try:
            # ✅ 根据API格式选择不同的调用方式
            if self.config.api_format == "openai":
                print(f"[HermesService] 使用OpenAI兼容格式调用分析API")
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"请分析以下新闻内容：\n\n{full_content}"}
                ]
                result = await self.chat_openai_format(messages)
                # 从OpenAI格式响应中提取内容
                response_text = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            else:
                print(f"[HermesService] 使用Ollama原生格式调用分析API")
                result = await self.generate(
                    prompt=f"请分析以下新闻内容：\n\n{full_content}",
                    system=system_prompt
                )
                response_text = result.get("response", "")
            
            return self._parse_analysis_response(response_text, full_content)

        except Exception as e:
            raise Exception(f"Hermes 新闻分析失败: {str(e)}")

    def _parse_analysis_response(self, response: str, original_content: str) -> Dict:
        """解析分析响应"""
        try:
            # 尝试提取 JSON
            json_str = response.strip()
            if "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0]
            elif "```" in json_str:
                json_str = json_str.split("```")[1].split("```")[0]

            data = json.loads(json_str.strip())

            # 验证并补充必要字段
            if "title" not in data:
                data["title"] = original_content[:50]

            return data

        except json.JSONDecodeError:
            # JSON 解析失败，返回简化结果
            return {
                "title": original_content[:50],
                "summary": original_content[:100],
                "key_points": ["内容分析中", "请查看完整新闻"],
                "impact_analysis": ["需要进一步分析"],
                "related_entities": [],
                "sentiment": "neutral",
                "confidence": 0.5,
                "categories": ["待分类"],
                "source_analysis": {"credibility": "medium", "bias": "center", "originality": "unknown"}
            }

    def get_available_models(self) -> List[str]:
        """获取可用的模型列表"""
        import requests
        try:
            response = requests.get(f"{self.config.api_url}/api/tags", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return [m.get("name", "") for m in data.get("models", [])]
        except:
            pass
        return [self.config.model]

    def get_connection_status(self) -> Dict:
        """获取连接状态"""
        return {
            "connected": self._connected,
            "api_url": self.config.api_url,
            "model": self.config.model,
            "type": "hermes"
        }


# 全局服务实例（延迟初始化）
_hermes_service_instance = None

def get_hermes_service() -> "HermesService":
    """获取 Hermes 服务实例（单例模式，使用配置）"""
    global _hermes_service_instance
    if _hermes_service_instance is None:
        from ..config import get_config
        config = get_config()
        _hermes_service_instance = HermesService(config.hermes)
        print(f"[HermesService] 全局实例已创建，使用配置:")
        print(f"  - URL: {config.hermes.api_url}")
        print(f"  - Model: {config.hermes.model}")
        print(f"  - Format: {config.hermes.api_format}")
    return _hermes_service_instance
