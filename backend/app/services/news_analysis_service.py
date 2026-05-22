"""
OpenClaw 新闻分析服务 - 使用 OpenClaw Skill 进行深度新闻分析
"""

import httpx
import json
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from pydantic import BaseModel


class NewsAnalysisResult(BaseModel):
    """新闻分析结果"""
    title: str
    summary: str
    key_points: List[str]
    impact_analysis: List[str]
    related_entities: List[Dict[str, str]]
    sentiment: str
    confidence: float
    categories: List[str]
    source_analysis: Dict[str, Any]
    generated_at: str


class IndustryChainAnalysisResult(BaseModel):
    """产业链分析结果（包含文字分析和思维导图数据）"""
    analysis_text: str  # 短中长期影响的文字分析
    mindmap_data: Dict[str, Any]  # 产业链的JSON格式数据


class OpenClawAnalysisService:
    """OpenClaw 分析服务：使用 OpenClaw Skill 进行新闻深度分析"""

    def __init__(self, api_url: str = "http://localhost:8080", api_key: Optional[str] = None):
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self._analysis_prompt = self._build_analysis_prompt()
        self._industry_chain_prompt = self._build_industry_chain_prompt()

    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _build_analysis_prompt(self) -> str:
        """构建新闻分析提示词"""
        return """你是一个专业的新闻分析师。请对以下新闻内容进行深度分析，并返回结构化的分析结果。

请按以下JSON格式返回分析结果（只返回JSON，不要有其他内容）：
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

新闻内容：
{content}

请确保返回的是有效的JSON格式。"""

    def _build_industry_chain_prompt(self) -> str:
        """构建产业链分析提示词"""
        return """你是一个专业的产业链分析师。请对以下新闻内容进行深度分析，并返回两部分内容：

1. 文字分析部分（analysis_text）：分析该新闻中的内容，短、中、长期分别对未来有哪些影响？请输出为详细的文字格式。

2. 产业链数据部分（mindmap_data）：分析该新闻中涉及了哪个细分行业，确定该细分行业所处的产业链，拆分越细越好，尽量达到5级以上。请按照以下JSON格式输出：

```json
{
    "name": "产业链名称",
    "children": [
        {
            "name": "上游 - 原材料/基础层",
            "children": [
                {
                    "name": "原材料供应商A",
                    "children": [
                        {"name": "具体材料1"},
                        {"name": "具体材料2"}
                    ]
                },
                {
                    "name": "零部件供应商B",
                    "children": [
                        {"name": "核心部件1"},
                        {"name": "核心部件2"}
                    ]
                }
            ]
        },
        {
            "name": "中游 - 制造/加工层",
            "children": [
                {
                    "name": "制造商C",
                    "children": [
                        {"name": "生产线1"},
                        {"name": "生产线2"}
                    ]
                }
            ]
        },
        {
            "name": "下游 - 应用/销售层",
            "children": [
                {
                    "name": "分销商D",
                    "children": [
                        {"name": "渠道1"},
                        {"name": "渠道2"}
                    ]
                },
                {
                    "name": "终端用户E",
                    "children": [
                        {"name": "应用场景1"},
                        {"name": "应用场景2"}
                    ]
                }
            ]
        }
    ]
}
```

注意：
- 产业链层级要尽可能详细，至少5级
- 每个节点都要有明确的名称
- 只返回JSON格式，不要有其他内容

新闻内容：
{content}

请确保返回的是有效的JSON格式。"""

    async def analyze_news(self, news_content: str, news_title: str = "") -> NewsAnalysisResult:
        """
        分析新闻内容

        Args:
            news_content: 新闻正文内容
            news_title: 新闻标题（可选）

        Returns:
            NewsAnalysisResult: 结构化的分析结果
        """
        # 构建完整的分析内容
        full_content = news_content
        if news_title:
            full_content = f"标题：{news_title}\n\n内容：{news_content}"

        # 策略1: 尝试通过 Chat API 调用（通用方式，不需要Skill）
        try:
            print(f"[OpenClawAnalysisService] 尝试通过Chat API分析新闻...")
            result = await self._call_openclaw_chat(full_content)
            if result:
                print(f"[OpenClawAnalysisService] ✅ Chat API分析成功")
                return result
        except Exception as e:
            print(f"[OpenClawAnalysisService] Chat API调用失败: {e}")

        # 策略2: 尝试调用 Skill 端点（需要Agent导入Skill）
        try:
            print(f"[OpenClawAnalysisService] 尝试调用Skill端点...")
            result = await self._call_openclaw_skill(full_content)
            if result:
                print(f"[OpenClawAnalysisService] ✅ Skill调用成功")
                return result
        except Exception as e:
            print(f"[OpenClawAnalysisService] Skill调用失败: {e}")

        # 策略3: 如果都失败，使用本地分析
        print(f"[OpenClawAnalysisService] ⚠️ 所有远程调用失败，使用本地分析")
        return await self._local_analysis(full_content, news_title)

    async def analyze_industry_chain(self, news_content: str, news_title: str = "") -> IndustryChainAnalysisResult:
        """
        分析新闻的产业链结构

        Args:
            news_content: 新闻正文内容
            news_title: 新闻标题（可选）

        Returns:
            IndustryChainAnalysisResult: 包含文字分析和产业链数据的结果
        """
        # 构建完整的分析内容
        full_content = news_content
        if news_title:
            full_content = f"标题：{news_title}\n\n内容：{news_content}"

        # 策略1: 尝试通过 Chat API 调用产业链分析（通用方式）
        try:
            print(f"[OpenClawAnalysisService] 尝试通过Chat API进行产业链分析...")
            result = await self._call_openclaw_industry_chain_skill(full_content)
            if result:
                print(f"[OpenClawAnalysisService] ✅ Chat API产业链分析成功")
                return result
        except Exception as e:
            print(f"[OpenClawAnalysisService] Chat API产业链分析失败: {e}")

        # 策略2: 如果失败，使用本地分析
        print(f"[OpenClawAnalysisService] ⚠️ 远程产业链分析失败，使用本地分析")
        return await self._local_industry_chain_analysis(full_content, news_title)

    async def _call_openclaw_skill(self, content: str) -> Optional[NewsAnalysisResult]:
        """调用 OpenClaw 的新闻分析 Skill"""
        # 尝试调用 OpenClaw 的 Skill 端点
        skill_endpoint = f"{self.api_url}/v1/skills/news-analyzer/execute"

        payload = {
            "input": {
                "content": content,
                "analysis_type": "comprehensive"
            },
            "parameters": {
                "depth": "detailed",
                "include_entities": True,
                "include_sentiment": True,
                "include_impact": True
            }
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    skill_endpoint,
                    headers=self._get_headers(),
                    json=payload
                )

                if response.status_code == 200:
                    data = response.json()
                    return self._parse_skill_result(data)

        except httpx.ConnectError:
            print("无法连接到 OpenClaw 服务")
        except Exception as e:
            print(f"OpenClaw Skill 调用错误: {e}")

        return None

    async def _call_openclaw_industry_chain_skill(self, content: str) -> Optional[IndustryChainAnalysisResult]:
        """调用 OpenClaw 的产业链分析 Skill"""
        # 构建提示词
        prompt = self._industry_chain_prompt.format(content=content)
        
        # 尝试通过 Chat API 调用
        try:
            result = await self._call_openclaw_chat_raw(prompt)
            if result:
                # 解析返回的JSON字符串
                return self._parse_industry_chain_result(result)
        except Exception as e:
            print(f"OpenClaw 产业链分析调用错误: {e}")

        return None

    async def _call_openclaw_chat_raw(self, prompt: str) -> Optional[str]:
        """通过 Chat API 调用 OpenClaw，返回原始文本内容"""
        payload = {
            "model": "default",
            "messages": [
                {"role": "system", "content": "你是一个专业的产业链分析师，请严格按照要求的JSON格式返回结果。"},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 3000,
            "temperature": 0.3
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.api_url}/v1/chat/completions",
                    headers=self._get_headers(),
                    json=payload
                )

                if response.status_code == 200:
                    data = response.json()
                    return data["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"OpenClaw Chat API 调用错误: {e}")

        return None

    async def _call_openclaw_chat(self, content: str) -> Optional[NewsAnalysisResult]:
        """通过 Chat API 调用 OpenClaw 进行新闻分析"""
        payload = {
            "model": "default",
            "messages": [
                {"role": "system", "content": "你是一个专业的新闻分析师。"},
                {"role": "user", "content": self._analysis_prompt.format(content=content)}
            ],
            "max_tokens": 2000,
            "temperature": 0.3
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.api_url}/v1/chat/completions",
                    headers=self._get_headers(),
                    json=payload
                )

                if response.status_code == 200:
                    data = response.json()
                    content_result = data["choices"][0]["message"]["content"]
                    return self._parse_json_response(content_result, content)

        except Exception as e:
            print(f"OpenClaw Chat API 调用错误: {e}")

        return None

    def _parse_skill_result(self, data: Dict) -> Optional[NewsAnalysisResult]:
        """解析 Skill 返回的结果"""
        try:
            if "result" in data:
                result_data = data["result"]
            else:
                result_data = data

            return NewsAnalysisResult(
                title=result_data.get("title", ""),
                summary=result_data.get("summary", ""),
                key_points=result_data.get("key_points", []),
                impact_analysis=result_data.get("impact_analysis", []),
                related_entities=result_data.get("related_entities", []),
                sentiment=result_data.get("sentiment", "neutral"),
                confidence=result_data.get("confidence", 0.5),
                categories=result_data.get("categories", []),
                source_analysis=result_data.get("source_analysis", {}),
                generated_at=datetime.now().isoformat()
            )
        except Exception as e:
            print(f"解析 Skill 结果失败: {e}")
            return None

    def _parse_json_response(self, json_str: str, original_content: str) -> Optional[NewsAnalysisResult]:
        """解析 JSON 响应"""
        try:
            # 尝试提取 JSON
            json_str = json_str.strip()
            if "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0]
            elif "```" in json_str:
                json_str = json_str.split("```")[1].split("```")[0]

            data = json.loads(json_str.strip())

            return NewsAnalysisResult(
                title=data.get("title", original_content[:50]),
                summary=data.get("summary", original_content[:100]),
                key_points=data.get("key_points", []),
                impact_analysis=data.get("impact_analysis", []),
                related_entities=data.get("related_entities", []),
                sentiment=data.get("sentiment", "neutral"),
                confidence=data.get("confidence", 0.7),
                categories=data.get("categories", []),
                source_analysis=data.get("source_analysis", {}),
                generated_at=datetime.now().isoformat()
            )
        except json.JSONDecodeError as e:
            print(f"JSON 解析失败: {e}")
            return None

    def _parse_industry_chain_result(self, json_str: str) -> Optional[IndustryChainAnalysisResult]:
        """解析产业链分析结果"""
        try:
            # 尝试提取 JSON
            json_str = json_str.strip()
            if "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0]
            elif "```" in json_str:
                json_str = json_str.split("```")[1].split("```")[0]

            data = json.loads(json_str.strip())

            # 提取文字分析和思维导图数据
            analysis_text = data.get("analysis_text", "")
            mindmap_data = data.get("mindmap_data", {})

            return IndustryChainAnalysisResult(
                analysis_text=analysis_text,
                mindmap_data=mindmap_data
            )
        except json.JSONDecodeError as e:
            print(f"产业链分析 JSON 解析失败: {e}")
            return None

    async def _local_analysis(self, content: str, title: str = "") -> NewsAnalysisResult:
        """本地新闻分析（当 OpenClaw 不可用时）"""
        # 简单的本地分析逻辑
        content_lower = content.lower()

        # 检测情感
        positive_words = ["增长", "突破", "成功", "提升", "进步", "好", "积极", "利好"]
        negative_words = ["下降", "失败", "危机", "问题", "风险", "下跌", "负面"]
        positive_count = sum(1 for word in positive_words if word in content_lower)
        negative_count = sum(1 for word in negative_words if word in content_lower)

        if positive_count > negative_count:
            sentiment = "positive"
        elif negative_count > positive_count:
            sentiment = "negative"
        else:
            sentiment = "neutral"

        # 简单提取关键词（基于常见词频）
        words_to_extract = ["人工智能", "科技", "经济", "市场", "政策", "环境", "社会", "国际",
                          "公司", "政府", "数据", "技术", "创新", "发展", "投资", "合作"]

        found_categories = [cat for cat in ["科技", "经济", "环境", "社会", "国际"] if cat in content]
        if not found_categories:
            found_categories = ["综合"]

        # 生成影响分析
        impact_points = []
        if "增长" in content or "发展" in content:
            impact_points.append("该新闻对相关领域有积极推动作用")
        if "风险" in content or "问题" in content:
            impact_points.append("存在潜在风险，需要关注后续发展")
        if "政策" in content or "政府" in content:
            impact_points.append("可能引发政策调整或监管关注")
        if not impact_points:
            impact_points.append("值得关注，持续跟踪后续发展")

        # 实体识别（简化版）
        entities = []
        org_keywords = ["公司", "企业", "集团", "机构"]
        for keyword in org_keywords:
            if keyword in content[:200]:
                entities.append({
                    "name": f"相关{keyword}",
                    "type": "organization",
                    "relation": "新闻涉及的主体"
                })
                break

        return NewsAnalysisResult(
            title=title if title else content[:50] + "...",
            summary=content[:100] + "..." if len(content) > 100 else content,
            key_points=[
                "核心事件需要进一步分析",
                "相关影响有待观察",
                "建议结合多方信息判断",
                "持续关注事态发展",
                "理性看待，避免过度解读"
            ],
            impact_analysis=impact_points[:5] if len(impact_points) >= 5 else impact_points + ["暂无详细分析"] * (5 - len(impact_points)),
            related_entities=entities if entities else [{"name": "相关信息源", "type": "organization", "relation": "信息来源"}],
            sentiment=sentiment,
            confidence=0.5,
            categories=found_categories,
            source_analysis={
                "credibility": "medium",
                "bias": "center",
                "originality": "aggregated"
            },
            generated_at=datetime.now().isoformat()
        )

    async def _local_industry_chain_analysis(self, content: str, title: str = "") -> IndustryChainAnalysisResult:
        """本地产业链分析（当 OpenClaw 不可用时）"""
        
        # 生成文字分析
        analysis_text = (
            f"[{title or '新闻'}影响分析]\n\n"
            "短期影响(1-3个月):\n"
            "- 市场可能对该消息做出即时反应\n"
            "- 相关行业股票可能出现波动\n"
            "- 投资者需关注后续政策动向\n\n"
            "中期影响(3-12个月):\n"
            "- 行业格局可能发生调整\n"
            "- 相关企业战略可能需要重新评估\n"
            "- 供应链关系可能发生变化\n\n"
            "长期影响(1年以上):\n"
            "- 可能推动行业技术升级或转型\n"
            "- 产业结构可能优化重组\n"
            "- 对经济发展产生深远影响\n\n"
            "建议: 持续关注事态发展, 结合多方信息进行判断。"
        )

        # 生成简化的产业链数据
        mindmap_data = {
            "name": title[:20] if title else "产业链分析",
            "children": [
                {
                    "name": "上游 - 基础层",
                    "children": [
                        {"name": "原材料供应"},
                        {"name": "技术支持"}
                    ]
                },
                {
                    "name": "中游 - 核心层",
                    "children": [
                        {"name": "生产制造"},
                        {"name": "服务提供"}
                    ]
                },
                {
                    "name": "下游 - 应用层",
                    "children": [
                        {"name": "终端用户"},
                        {"name": "市场渠道"}
                    ]
                }
            ]
        }

        # ✅ 添加调试日志
        print(f"[UnifiedAnalysisService] 本地产业链分析完成")
        print(f"[UnifiedAnalysisService] 分析文本长度: {len(analysis_text)}")
        print(f"[UnifiedAnalysisService] 产业链数据结构:")
        import json
        print(json.dumps(mindmap_data, ensure_ascii=False, indent=2)[:500])

        return IndustryChainAnalysisResult(
            analysis_text=analysis_text,
            mindmap_data=mindmap_data
        )

    async def batch_analyze(self, news_list: List[Dict]) -> List[NewsAnalysisResult]:
        """批量分析新闻"""
        results = []
        for news in news_list:
            try:
                result = await self.analyze_news(
                    news.get("content", news.get("summary", "")),
                    news.get("title", "")
                )
                results.append(result)
            except Exception as e:
                print(f"分析新闻失败: {news.get('title', 'Unknown')}, 错误: {e}")
                results.append(await self._local_analysis(
                    news.get("content", news.get("summary", "")),
                    news.get("title", "")
                ))
            await asyncio.sleep(0.1)  # 避免请求过快

        return results


# 全局分析服务实例
analysis_service = OpenClawAnalysisService()


# ============================================================
# 统一分析服务 - 支持多种后端 (OpenClaw/Hermes/Local)
# ============================================================

from ..config import BackendType, get_config, get_backend_display_name


class UnifiedAnalysisService:
    """统一分析服务：自动选择合适的后端进行分析"""

    def __init__(self):
        self.config = get_config()
        self._openclaw_service = None
        self._hermes_service = None

    async def _get_openclaw_service(self):
        """获取 OpenClaw 服务"""
        if self._openclaw_service is None:
            from .openclaw_service import OpenClawService
            self._openclaw_service = OpenClawService()
        return self._openclaw_service

    async def _get_hermes_service(self):
        """获取 Hermes 服务"""
        if self._hermes_service is None:
            from .hermes_service import get_hermes_service
            self._hermes_service = get_hermes_service()
        return self._hermes_service

    async def analyze_news(self, news_content: str, news_title: str = "", force_backend: BackendType = None) -> NewsAnalysisResult:
        """
        分析新闻内容，自动选择合适的后端

        Args:
            news_content: 新闻正文内容
            news_title: 新闻标题（可选）
            force_backend: 强制使用特定后端（可选）

        Returns:
            NewsAnalysisResult: 结构化的分析结果
        """
        backend_type = force_backend or self.config.backend_type
        
        # 添加调试日志
        print(f"[UnifiedAnalysisService] 分析请求:")
        print(f"  - force_backend: {force_backend}")
        print(f"  - config.backend_type: {self.config.backend_type}")
        print(f"  - 最终使用的backend_type: {backend_type}")

        # 根据后端类型选择分析方法
        if backend_type == BackendType.OPENCLAW:
            print(f"[UnifiedAnalysisService] 使用 OpenClaw 进行分析")
            return await self._analyze_with_openclaw(news_content, news_title)
        elif backend_type == BackendType.HERMES:
            print(f"[UnifiedAnalysisService] 使用 Hermes 进行分析")
            return await self._analyze_with_hermes(news_content, news_title)
        else:
            print(f"[UnifiedAnalysisService] 使用本地分析")
            return await self._local_analysis(news_content, news_title)

    async def analyze_industry_chain(self, news_content: str, news_title: str = "", force_backend: BackendType = None) -> IndustryChainAnalysisResult:
        """
        分析新闻的产业链结构，自动选择合适的后端

        Args:
            news_content: 新闻正文内容
            news_title: 新闻标题（可选）
            force_backend: 强制使用特定后端（可选）

        Returns:
            IndustryChainAnalysisResult: 包含文字分析和产业链数据的结果
        """
        backend_type = force_backend or self.config.backend_type
        
        print(f"[UnifiedAnalysisService] 产业链分析请求:")
        print(f"  - 最终使用的backend_type: {backend_type}")

        # 根据后端类型选择分析方法
        if backend_type == BackendType.OPENCLAW:
            print(f"[UnifiedAnalysisService] 使用 OpenClaw 进行产业链分析")
            return await self._analyze_industry_chain_with_openclaw(news_content, news_title)
        elif backend_type == BackendType.HERMES:
            print(f"[UnifiedAnalysisService] 使用 Hermes 进行产业链分析")
            return await self._analyze_industry_chain_with_hermes(news_content, news_title)
        else:
            print(f"[UnifiedAnalysisService] 使用本地产业链分析")
            return await self._local_industry_chain_analysis(news_content, news_title)

    async def _analyze_with_openclaw(self, content: str, title: str = "") -> NewsAnalysisResult:
        """使用 OpenClaw 分析"""
        try:
            service = await self._get_openclaw_service()
            connected = await service.check_connection()

            if connected:
                # 尝试使用 OpenClaw Chat API
                result = await self._call_openclaw_analysis(service, content, title)
                if result:
                    return result
        except Exception as e:
            print(f"OpenClaw 分析失败: {e}")

        # 回退到本地分析
        return await self._local_analysis(content, title)

    async def _analyze_industry_chain_with_openclaw(self, content: str, title: str = "") -> IndustryChainAnalysisResult:
        """使用 OpenClaw 进行产业链分析"""
        try:
            service = await self._get_openclaw_service()
            connected = await service.check_connection()

            if connected:
                # 构建产业链分析提示词
                from ..services.news_analysis_service import OpenClawAnalysisService
                analysis_service = OpenClawAnalysisService(
                    api_url=self.config.openclaw.api_url,
                    api_key=self.config.openclaw.api_key
                )
                
                result = await analysis_service.analyze_industry_chain(content, title)
                if result:
                    return result
        except Exception as e:
            print(f"OpenClaw 产业链分析失败: {e}")

        # 回退到本地分析
        return await self._local_industry_chain_analysis(content, title)

    async def _analyze_industry_chain_with_hermes(self, content: str, title: str = "") -> IndustryChainAnalysisResult:
        """使用 Hermes 进行产业链分析"""
        try:
            service = await self._get_hermes_service()
            connected = await service.check_connection()
            
            if not connected:
                print(f"[UnifiedAnalysisService] ⚠️ Hermes服务未连接，将回退到本地产业链分析")
                return await self._local_industry_chain_analysis(content, title)

            # 构建产业链分析提示词
            system_prompt = """你是一个专业的产业链分析师。请对以下新闻内容进行深度产业链分析，识别相关的上下游产业、供应商、客户等，并返回JSON格式的结果。

**重要**：mindmap_data必须反映真实的产业链结构（上游→中游→下游），不要包含时间维度（短中长期）的影响分析节点。

返回格式（必须是有效的JSON）：
{
    "analysis_text": "详细的文字分析，包括：\n1. 短期影响（1-3个月）\n2. 中期影响（3-12个月）\n3. 长期影响（1年以上）\n4. 涉及的产业链环节",
    "mindmap_data": {
        "nodes": [
            {"id": "root", "text": "新闻核心主题", "level": 0},
            {"id": "upstream", "text": "上游产业", "level": 1},
            {"id": "upstream_1", "text": "具体公司/产品名1", "level": 2},
            {"id": "upstream_2", "text": "具体公司/产品名2", "level": 2},
            {"id": "midstream", "text": "中游产业", "level": 1},
            {"id": "midstream_1", "text": "具体公司/产品名3", "level": 2},
            {"id": "midstream_2", "text": "具体公司/产品名4", "level": 2},
            {"id": "downstream", "text": "下游产业", "level": 1},
            {"id": "downstream_1", "text": "具体公司/产品名5", "level": 2},
            {"id": "downstream_2", "text": "具体公司/产品名6", "level": 2}
        ],
        "edges": [
            {"source": "root", "target": "upstream"},
            {"source": "upstream", "target": "upstream_1"},
            {"source": "upstream", "target": "upstream_2"},
            {"source": "root", "target": "midstream"},
            {"source": "midstream", "target": "midstream_1"},
            {"source": "midstream", "target": "midstream_2"},
            {"source": "root", "target": "downstream"},
            {"source": "downstream", "target": "downstream_1"},
            {"source": "downstream", "target": "downstream_2"}
        ]
    }
}

**关键要求**：
1. **纯产业链结构**：只包含上游（原材料/供应商）、中游（制造/加工）、下游（销售/应用）三个主要分支
2. **禁止时间维度**：不要在mindmap_data中包含"短期影响"、"中期影响"、"长期影响"等时间相关节点
3. **具体化**：每个环节的text字段必须填充真实的公司名称、产品名称、技术名称，**禁止使用"具体XX环节1"这类占位文字**
4. **节点数量**：至少9-12个节点，确保产业链完整
5. **文字分析独立**：短中长期的影响分析只放在analysis_text字段中，不要放入mindmap_data
6. **只返回JSON**，不要有其他内容

示例（根据实际新闻调整）：
如果新闻关于"AI芯片短缺"：
- 上游text字段：如"台积电"、"ASML光刻机"、"硅晶圆材料"
- 中游text字段：如"英伟达GPU设计"、"三星代工"、"先进封装"
- 下游text字段：如"苹果iPhone"、"特斯拉自动驾驶"、"AWS数据中心"
"""

            full_content = f"标题：{title}\n\n内容：{content}" if title else content
            
            # 截断过长的输入文本（避免超过模型上下文窗口）
            MAX_INPUT_CHARS = 3000  # 为 system prompt + 输出预留空间
            if len(full_content) > MAX_INPUT_CHARS:
                print(f"[UnifiedAnalysisService] ⚠️ 输入文本过长({len(full_content)}字符)，截断至{MAX_INPUT_CHARS}字符")
                full_content = full_content[:MAX_INPUT_CHARS] + "\n\n[内容已截断...]"

            print(f"[UnifiedAnalysisService] 调用Hermes进行产业链分析，输入{len(full_content)}字符...")
            
            # ✅ 直接使用Hermes服务的chat_openai_format方法
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"请分析以下新闻的产业链结构和影响：\n\n{full_content}"}
            ]
            
            # 产业链分析需要大量输出token，使用8000 max_tokens
            result = await service.chat_openai_format(messages, max_tokens=8000)
            
            # 从OpenAI格式响应中提取内容
            response_text = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            print(f"[UnifiedAnalysisService] Hermes产业链分析响应长度: {len(response_text)}")
            print(f"[UnifiedAnalysisService] 输入文本长度: {len(full_content)} 字符")
            
            # 如果响应为空或极短，详细记录并回退到本地分析
            if not response_text or not response_text.strip():
                print(f"[UnifiedAnalysisService] ⚠️ Hermes返回空内容")
                print(f"[UnifiedAnalysisService] 完整API返回: {json.dumps(result, ensure_ascii=False)[:1000]}")
                response_text = result.get("response", "") or result.get("text", "")
                if not response_text or not response_text.strip():
                    raise Exception("Hermes API 返回空内容，无法进行产业链分析")
            
            # 如果响应太短（可能被截断），打印完整内容便于诊断
            if len(response_text) < 100:
                print(f"[UnifiedAnalysisService] ⚠️ Hermes返回过短响应({len(response_text)}字符)")
                print(f"[UnifiedAnalysisService] 完整响应内容: {repr(response_text)}")
                print(f"[UnifiedAnalysisService] 完整API返回: {json.dumps(result, ensure_ascii=False)[:1000]}")
                print(f"[UnifiedAnalysisService] 可能原因: 模型不支持该格式、max_tokens不足、或上下文长度超限")
                print(f"[UnifiedAnalysisService] 建议: 检查输入文本是否过长({len(full_content)}字符)，或模型是否支持中文")
                raise Exception("Hermes 返回过短响应，可能是上下文长度超限或模型不支持中文")
            
            # 解析JSON响应
            json_str = response_text.strip()
            if "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0].strip()
            elif "```" in json_str:
                json_str = json_str.split("```")[1].split("```")[0].strip()
            
            json_str = json_str.strip()
            
            # 尝试找到JSON对象的起始和结束位置（处理模型返回非JSON前缀/后缀的情况）
            json_start = json_str.find('{')
            json_end = json_str.rfind('}')
            if json_start != -1 and json_end > json_start:
                json_str = json_str[json_start:json_end + 1]
                print(f"[UnifiedAnalysisService] 从响应中提取JSON片段 (位置 {json_start}-{json_end})")
            
            if not json_str or not json_str.strip():
                print(f"[UnifiedAnalysisService] ⚠️ 提取JSON后为空")
                print(f"[UnifiedAnalysisService] 原始响应 (前500字符): {response_text[:500]}")
                print(f"[UnifiedAnalysisService] 完整响应: {repr(response_text)}")
                raise Exception("无法从Hermes响应中提取有效的JSON数据")
            
            try:
                data = json.loads(json_str)
            except json.JSONDecodeError as je:
                print(f"[UnifiedAnalysisService] ⚠️ JSON解析失败: {je}")
                print(f"[UnifiedAnalysisService] 提取后的JSON (前500字符): {json_str[:500]}")
                print(f"[UnifiedAnalysisService] 提取后的JSON (完整): {repr(json_str)}")
                print(f"[UnifiedAnalysisService] 原始响应 (前500字符): {response_text[:500]}")
                raise Exception(f"Hermes返回了非JSON格式内容: {je}")
            
            analysis_text = data.get("analysis_text", "")
            mindmap_data = data.get("mindmap_data", {})
            
            print(f"[UnifiedAnalysisService] Hermes产业链分析完成")
            print(f"[UnifiedAnalysisService] 分析文本长度: {len(analysis_text)}")
            print(f"[UnifiedAnalysisService] 思维导图节点数: {len(mindmap_data.get('nodes', []))}")
            
            return IndustryChainAnalysisResult(
                analysis_text=analysis_text,
                mindmap_data=mindmap_data
            )
            
        except Exception as e:
            print(f"Hermes 产业链分析失败: {e}")
            import traceback
            traceback.print_exc()

        # 回退到本地分析
        return await self._local_industry_chain_analysis(content, title)

    async def _analyze_with_hermes(self, content: str, title: str = "") -> NewsAnalysisResult:
        """使用 Hermes (Ollama) 分析"""
        try:
            service = await self._get_hermes_service()
            connected = await service.check_connection()
            
            print(f"[UnifiedAnalysisService] Hermes连接状态: {connected}")
            print(f"[UnifiedAnalysisService] Hermes API URL: {service.config.api_url}")
            print(f"[UnifiedAnalysisService] Hermes Model: {service.config.model}")

            if not connected:
                print(f"[UnifiedAnalysisService] ⚠️ Hermes/Agent服务未连接，将回退到本地分析")
                print(f"[UnifiedAnalysisService] 如需使用Hermes/Agent，请确保:")
                print(f"  1. Agent服务已启动并监听: {service.config.api_url}")
                print(f"  2. 模型可用: {service.config.model}")
                print(f"  3. API Key配置正确 (如需要)")
                print(f"  4. 网络连接正常")
                return await self._local_analysis(content, title)

            # 使用 Hermes 分析
            print(f"[UnifiedAnalysisService] 调用Hermes分析新闻...")
            result = await service.analyze_news(content, title)
            print(f"[UnifiedAnalysisService] Hermes分析完成，返回字段: {list(result.keys())}")
            
            analysis_result = NewsAnalysisResult(
                title=result.get("title", title or content[:50]),
                summary=result.get("summary", content[:100]),
                key_points=result.get("key_points", []),
                impact_analysis=result.get("impact_analysis", []),
                related_entities=result.get("related_entities", []),
                sentiment=result.get("sentiment", "neutral"),
                confidence=result.get("confidence", 0.7),
                categories=result.get("categories", []),
                source_analysis=result.get("source_analysis", {}),
                generated_at=datetime.now().isoformat()
            )
            print(f"[UnifiedAnalysisService] 生成NewsAnalysisResult，key_points数量: {len(analysis_result.key_points)}")
            return analysis_result
        except Exception as e:
            print(f"Hermes 分析失败: {e}")
            import traceback
            traceback.print_exc()

        # 回退到本地分析
        print(f"[UnifiedAnalysisService] Hermes失败，回退到本地分析")
        return await self._local_analysis(content, title)

    async def _call_openclaw_analysis(self, service, content: str, title: str = "") -> NewsAnalysisResult:
        """调用 OpenClaw 进行新闻分析"""
        from ..models.schemas import ChatRequest

        analysis_prompt = (
            "请分析以下新闻内容, 返回 JSON 格式的分析结果:\n\n"
            f"标题: {title if title else '无'}\n"
            f"内容: {content}\n\n"
            "返回格式:\n"
            "{\n"
            '    "title": "新闻标题",\n'
            '    "summary": "50字以内的新闻摘要",\n'
            '    "key_points": ["要点1", "要点2", "要点3", "要点4", "要点5"],\n'
            '    "impact_analysis": ["影响分析1", "影响分析2", "影响分析3", "影响分析4", "影响分析5"],\n'
            '    "related_entities": [\n'
            '        {"name": "实体名称", "type": "person/organization/location", "relation": "与新闻的关系"}\n'
            '    ],\n'
            '    "sentiment": "positive/negative/neutral",\n'
            '    "confidence": 0.85,\n'
            '    "categories": ["category1", "category2"],\n'
            '    "source_analysis": {\n'
            '        "credibility": "high/medium/low",\n'
            '        "bias": "left/center/right",\n'
            '        "originality": "original/aggregated"\n'
            '    }\n'
            "}\n\n"
            "请只返回 JSON, 不要有其他内容。"
        )

        try:
            request = ChatRequest(
                session_id="analysis",
                message=analysis_prompt
            )
            response = await service.send_message(request)

            # 解析 JSON 响应
            import json
            json_str = response.message.content.strip()
            if "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0]
            elif "```" in json_str:
                json_str = json_str.split("```")[1].split("```")[0]

            data = json.loads(json_str.strip())

            return NewsAnalysisResult(
                title=data.get("title", title or content[:50]),
                summary=data.get("summary", content[:100]),
                key_points=data.get("key_points", []),
                impact_analysis=data.get("impact_analysis", []),
                related_entities=data.get("related_entities", []),
                sentiment=data.get("sentiment", "neutral"),
                confidence=data.get("confidence", 0.7),
                categories=data.get("categories", []),
                source_analysis=data.get("source_analysis", {}),
                generated_at=datetime.now().isoformat()
            )
        except Exception as e:
            print(f"OpenClaw 分析调用失败: {e}")
            return None

    async def _local_analysis(self, content: str, title: str = "") -> NewsAnalysisResult:
        """本地新闻分析"""
        import re
        content_lower = content.lower()

        # 检测情感
        positive_words = ["增长", "突破", "成功", "提升", "进步", "好", "积极", "利好", "创新", "发展"]
        negative_words = ["下降", "失败", "危机", "问题", "风险", "下跌", "负面", "衰退", "下滑"]
        positive_count = sum(1 for word in positive_words if word in content_lower)
        negative_count = sum(1 for word in negative_words if word in content_lower)

        if positive_count > negative_count:
            sentiment = "positive"
        elif negative_count > positive_count:
            sentiment = "negative"
        else:
            sentiment = "neutral"

        # 识别主题类别
        categories = []
        if re.search(r'科技|技术|ai|人工智能|量子|芯片|智能', content_lower): categories.append('科技')
        if re.search(r'经济|市场|投资|金融|股票', content_lower): categories.append('经济')
        if re.search(r'环境|气候|能源|绿色', content_lower): categories.append('环境')
        if re.search(r'政策|政府|监管|法律', content_lower): categories.append('政策')
        if not categories: categories.append('综合')

        # 提取关键词
        stop_words = ['的', '了', '是', '在', '我', '有', '和', '就', '不', '人', '都', '这', '那', '什么', '吗']
        words = [w for w in re.split(r'[,，.。!！?？、;；:：\s]+', content) if len(w) >= 2 and w not in stop_words]

        # 生成影响分析
        impact_points = []
        if re.search(r'增长|发展|提升', content_lower):
            impact_points.append('对相关领域有积极推动作用')
        if re.search(r'风险|问题|挑战', content_lower):
            impact_points.append('存在潜在风险，需要关注')
        if re.search(r'政策|政府', content_lower):
            impact_points.append('可能引发政策调整')
        if re.search(r'市场|投资', content_lower):
            impact_points.append('对市场走向有重要影响')
        if not impact_points:
            impact_points.append('值得关注，持续跟踪发展')

        return NewsAnalysisResult(
            title=title if title else content[:50] + "...",
            summary=content[:100] + "..." if len(content) > 100 else content,
            key_points=words[:5],
            impact_analysis=impact_points[:5],
            related_entities=[{"name": w, "type": "topic", "relation": "相关内容"} for w in words[5:9]],
            sentiment=sentiment,
            confidence=0.75,
            categories=categories,
            source_analysis={"credibility": "medium", "bias": "center", "originality": "aggregated"},
            generated_at=datetime.now().isoformat()
        )

    async def _local_industry_chain_analysis(self, content: str, title: str = "") -> IndustryChainAnalysisResult:
        """本地产业链分析"""
        
        # 生成文字分析
        analysis_text = (
            f"[{title or '新闻'}影响分析]\n\n"
            "短期影响(1-3个月):\n"
            "\u2022 市场可能对该消息做出即时反应\n"
            "\u2022 相关行业股票可能出现波动\n"
            "\u2022 投资者需关注后续政策动向\n\n"
            "中期影响(3-12个月):\n"
            "\u2022 行业格局可能发生调整\n"
            "\u2022 相关企业战略可能需要重新评估\n"
            "\u2022 供应链关系可能发生变化\n\n"
            "长期影响(1年以上):\n"
            "\u2022 可能推动行业技术升级或转型\n"
            "\u2022 产业结构可能优化重组\n"
            "\u2022 对经济发展产生深远影响\n\n"
            "建议: 持续关注事态发展, 结合多方信息进行判断。"
        )

        # 生成简化的产业链数据
        mindmap_data = {
            "name": title[:20] if title else "产业链分析",
            "children": [
                {
                    "name": "上游 - 基础层",
                    "children": [
                        {"name": "原材料供应"},
                        {"name": "技术支持"}
                    ]
                },
                {
                    "name": "中游 - 核心层",
                    "children": [
                        {"name": "生产制造"},
                        {"name": "服务提供"}
                    ]
                },
                {
                    "name": "下游 - 应用层",
                    "children": [
                        {"name": "终端用户"},
                        {"name": "市场渠道"}
                    ]
                }
            ]
        }

        return IndustryChainAnalysisResult(
            analysis_text=analysis_text,
            mindmap_data=mindmap_data
        )

    async def get_status(self) -> Dict:
        """获取分析服务状态"""
        status = {
            "current_backend": get_backend_display_name(),
            "backend_type": self.config.backend_type.value,
            "available_backends": []
        }

        # 检查 OpenClaw
        try:
            oc_service = await self._get_openclaw_service()
            oc_connected = await oc_service.check_connection()
            status["available_backends"].append({
                "name": "OpenClaw",
                "type": "openclaw",
                "connected": oc_connected,
                "api_url": self.config.openclaw.api_url
            })
        except Exception as e:
            status["available_backends"].append({
                "name": "OpenClaw",
                "type": "openclaw",
                "connected": False,
                "error": str(e)
            })

        # 检查 Hermes
        try:
            hermes_service = await self._get_hermes_service()
            hermes_connected = await hermes_service.check_connection()
            status["available_backends"].append({
                "name": "Hermes (Ollama)",
                "type": "hermes",
                "connected": hermes_connected,
                "api_url": self.config.hermes.api_url,
                "available_models": hermes_service.get_available_models() if hermes_connected else []
            })
        except Exception as e:
            status["available_backends"].append({
                "name": "Hermes (Ollama)",
                "type": "hermes",
                "connected": False,
                "error": str(e)
            })

        # 本地分析
        status["available_backends"].append({
            "name": "本地分析",
            "type": "local",
            "connected": True,
            "description": "无需外部服务，浏览器端完成"
        })

        return status

    async def switch_backend(self, backend_type: BackendType) -> Dict:
        """切换后端类型"""
        self.config.backend_type = backend_type
        return {
            "success": True,
            "new_backend": get_backend_display_name(),
            "backend_type": backend_type.value
        }


# 全局统一分析服务实例
unified_analysis_service = UnifiedAnalysisService()
