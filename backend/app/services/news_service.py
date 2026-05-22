"""
新闻服务 - 新闻获取与重要性排序
"""

import httpx
import feedparser
import asyncio
import json
import os
from typing import List, Optional, Dict, Tuple
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from dataclasses import dataclass
import hashlib
import re

from ..models.schemas import NewsItem, ImportanceScore


@dataclass
class SourceConfig:
    """新闻源配置"""
    name: str
    url: str
    type: str  # rss, html
    weight: float  # 来源权威度权重
    categories: List[str]
    parser_type: Optional[str] = None  # 特殊解析器类型（如 wscn_api）


class NewsService:
    """新闻服务：负责从多个来源获取新闻并计算重要性分数"""

    def __init__(self):
        self.sources = self._load_sources_from_config()
        self._news_cache: Dict[str, List[NewsItem]] = {}
        self._cache_time: Optional[datetime] = None
        self._cache_ttl = timedelta(minutes=15)

    def _load_sources_from_config(self) -> List[SourceConfig]:
        """从配置文件加载新闻源"""
        config_path = os.path.join(os.path.dirname(__file__), "..", "..", "news_sources.json")
        
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                sources = []
                
                # 加载RSS源
                for source in config.get("rss_sources", []):
                    sources.append(SourceConfig(
                        name=source["name"],
                        url=source["url"],
                        type="rss",
                        weight=source.get("weight", 0.9),
                        categories=source.get("categories", ["general"])
                    ))
                
                # 加载HTML源
                for source in config.get("html_sources", []):
                    sources.append(SourceConfig(
                        name=source["name"],
                        url=source["url"],
                        type="html",
                        weight=source.get("weight", 0.9),
                        categories=source.get("categories", ["general"]),
                        parser_type=source.get("parser_type")
                    ))
                
                print(f"[NewsService] 从配置文件加载 {len(sources)} 个新闻源")
                return sources
            else:
                print(f"[NewsService] 配置文件不存在，使用默认源")
                return self._get_default_sources()
                
        except Exception as e:
            print(f"[NewsService] 加载配置文件失败: {e}，使用默认源")
            return self._get_default_sources()
    
    def _get_default_sources(self) -> List[SourceConfig]:
        """获取默认新闻源（后备方案）"""
        return [
            SourceConfig(
                name="CNBC News",
                url="https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114",
                type="rss",
                weight=0.9,
                categories=["world", "technology", "business"]
            ),
        ]

    # 高权重关键词（科技/AI领域）
    HIGH_PRIORITY_KEYWORDS = [
        "ai", "artificial intelligence", "machine learning", "deep learning",
        "llm", "gpt", "chatgpt", "openai", "anthropic", "claude",
        "breakthrough", "launch", "announce", "release", "新品发布",
        "突破", "人工智能", "大模型", "技术革新", "开源", "发布"
    ]

    # 中等权重关键词
    MEDIUM_PRIORITY_KEYWORDS = [
        "trend", "report", "study", "research", "analysis",
        "company", "startup", "funding", "market",
        "趋势", "报告", "研究", "分析", "公司", "融资"
    ]

    def _generate_id(self, title: str, source: str, url: str = "") -> str:
        """生成唯一ID"""
        # 使用title、source和url组合生成唯一ID
        content = f"{title}:{source}:{url}"
        return hashlib.md5(content.encode()).hexdigest()[:12]

    def _parse_rss_feed(self, source: SourceConfig) -> List[Dict]:
        """解析RSS源"""
        try:
            feed = feedparser.parse(source.url)
            items = []
            for entry in feed.entries[:20]:  # 限制每源20条
                items.append({
                    "title": entry.get("title", ""),
                    "summary": entry.get("summary", "")[:500],
                    "content": entry.get("content", [{}])[0].get("value", ""),
                    "url": entry.get("link", ""),
                    "published": entry.get("published_parsed"),
                    "source": source.name,
                })
            return items
        except Exception as e:
            print(f"Error parsing RSS {source.name}: {e}")
            return []

    async def _fetch_all_sources(self) -> List[NewsItem]:
        """并发获取所有新闻源"""
        print(f"[NewsService] 开始并发抓取 {len(self.sources)} 个新闻源")
        
        # 使用较短的超时时间，避免单个源卡住整个请求
        async with httpx.AsyncClient(timeout=15.0) as client:
            tasks = []
            for source in self.sources:
                task = asyncio.create_task(self._fetch_source_with_client(client, source))
                tasks.append((source.name, task))
            
            all_news = []
            for source_name, task in tasks:
                try:
                    result = await asyncio.wait_for(task, timeout=10.0)
                    if isinstance(result, list):
                        all_news.extend(result)
                        print(f"[NewsService] ✅ {source_name}: 获取 {len(result)} 条新闻")
                    else:
                        print(f"[NewsService] ⚠️ {source_name}: 返回非列表结果")
                except asyncio.TimeoutError:
                    print(f"[NewsService] ❌ {source_name}: 超时（10秒）")
                except Exception as e:
                    print(f"[NewsService] ❌ {source_name}: 错误 - {e}")

        print(f"[NewsService] 所有源抓取完成，共 {len(all_news)} 条新闻")
        return all_news

    async def _fetch_source_with_client(self, client: httpx.AsyncClient, source: SourceConfig) -> List[NewsItem]:
        """使用指定client获取单个源"""
        if source.type == "rss":
            items = self._parse_rss_feed(source)
            return [self._create_news_item(item, source) for item in items]
        elif source.type == "html":
            return await self._parse_html_source(client, source)
        return []

    async def _parse_html_source(self, client: httpx.AsyncClient, source: SourceConfig) -> List[NewsItem]:
        """解析HTML/API新闻源"""
        try:
            # 根据parser_type选择不同的解析器
            if source.parser_type == "wscn_api":
                return await self._parse_wscn_api(client, source)
            else:
                # 默认HTML解析（通用）
                return await self._parse_generic_html(client, source)
        except Exception as e:
            print(f"[NewsService] 解析HTML源 {source.name} 失败: {e}")
            return []


    async def _parse_generic_html(self, client: httpx.AsyncClient, source: SourceConfig) -> List[NewsItem]:
        """
        通用HTML页面解析（备用方案）
        使用BeautifulSoup解析HTML内容
        """
        try:
            response = await client.get(source.url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            items = []
            
            # 尝试查找文章标题和链接（需要根据具体网站结构调整）
            # 这里提供一个通用的实现框架
            articles = soup.find_all('article') or soup.find_all('div', class_=re.compile(r'article|news|post'))
            
            for article in articles[:50]:
                title_elem = article.find('h1') or article.find('h2') or article.find('h3')
                link_elem = article.find('a')
                
                if title_elem and link_elem:
                    item = {
                        "title": title_elem.get_text(strip=True),
                        "summary": article.get_text(strip=True)[:500],
                        "content": "",
                        "url": link_elem.get('href', ''),
                        "published": None,
                        "source": source.name,
                    }
                    items.append(item)
            
            print(f"[NewsService] 从 {source.name} (HTML) 获取 {len(items)} 条新闻")
            return [self._create_news_item(item, source) for item in items]
            
        except Exception as e:
            print(f"[NewsService] HTML解析失败 {source.name}: {e}")
            return []

    def _create_news_item(self, raw_item: Dict, source: SourceConfig) -> NewsItem:
        """创建新闻条目并计算重要性分数"""
        # 提取发布时间
        published_at = datetime.now()
        if raw_item.get("published"):
            try:
                import time
                t = raw_item["published"]
                if isinstance(t, tuple):
                    published_at = datetime(*t[:6])
                else:
                    published_at = datetime.fromtimestamp(time.mktime(t))
            except:
                pass

        # 计算重要性分数
        importance = self._calculate_importance(
            title=raw_item["title"],
            summary=raw_item["summary"],
            source=source,
            published_at=published_at
        )

        # 提取关键词
        keywords = self._extract_keywords(raw_item["title"] + " " + raw_item["summary"])

        # 清理摘要
        summary = self._clean_html(raw_item["summary"])

        return NewsItem(
            id=self._generate_id(raw_item["title"], source.name, raw_item.get("url", "")),
            title=raw_item["title"],
            summary=summary[:300],
            source=raw_item["source"],
            url=raw_item["url"],
            published_at=published_at,
            importance_score=importance,
            category=source.categories[0] if source.categories else "general",
            keywords=keywords[:10],
        )

    def _calculate_importance(
        self,
        title: str,
        summary: str,
        source: SourceConfig,
        published_at: datetime
    ) -> ImportanceScore:
        """计算新闻重要性分数"""
        text = (title + " " + summary).lower()

        # 1. 来源权重分 (0-30分)
        source_weight = source.weight * 30

        # 2. 关键词匹配分 (0-40分)
        keyword_score = 0
        high_keyword_count = sum(1 for kw in self.HIGH_PRIORITY_KEYWORDS if kw.lower() in text)
        medium_keyword_count = sum(1 for kw in self.MEDIUM_PRIORITY_KEYWORDS if kw.lower() in text)
        keyword_score = min(high_keyword_count * 5 + medium_keyword_count * 2, 40)

        # 3. 时效性分 (0-20分)
        hours_old = (datetime.now() - published_at).total_seconds() / 3600
        if hours_old < 1:
            recency_weight = 20
        elif hours_old < 6:
            recency_weight = 18 - (hours_old - 1) * 0.5
        elif hours_old < 24:
            recency_weight = 15 - (hours_old - 6) * 0.3
        else:
            recency_weight = max(5 - (hours_old - 24) * 0.1, 0)

        # 4. 情感权重分 (0-10分)
        sentiment_score = 0
        positive_words = ["great", "amazing", "best", "breakthrough", "success", "突破", "成功", "领先"]
        negative_words = ["fail", "problem", "crisis", "risk", "danger", "失败", "问题", "危机"]
        sentiment_score = sum(5 for w in positive_words if w in text)

        total = source_weight + keyword_score + recency_weight + sentiment_score

        return ImportanceScore(
            total=round(total, 2),
            source_weight=round(source_weight, 2),
            keyword_weight=round(keyword_score, 2),
            recency_weight=round(recency_weight, 2),
            sentiment_weight=round(sentiment_score, 2)
        )

    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词"""
        # 简单提取：去除停用词，提取有意义的词
        stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
                     "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
                     "being", "have", "has", "had", "do", "does", "did", "will", "would",
                     "could", "should", "may", "might", "must", "shall", "can", "this",
                     "that", "these", "those", "i", "you", "he", "she", "it", "we", "they",
                     "what", "which", "who", "whom", "when", "where", "why", "how", "的",
                     "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一", "一个"}

        words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
        keywords = [w for w in words if len(w) > 3 and w not in stop_words]

        # 统计词频
        from collections import Counter
        counter = Counter(keywords)
        return [word for word, _ in counter.most_common(10)]

    def _clean_html(self, html_content: str) -> str:
        """清理HTML标签"""
        soup = BeautifulSoup(html_content, 'html.parser')
        return soup.get_text(separator=' ', strip=True)

    async def get_news(
        self,
        category: Optional[str] = None,
        page: int = 1,
        page_size: int = 30,
        force_refresh: bool = False,
        sort_by: str = "importance"  # "importance" 或 "time"
    ) -> tuple[List[NewsItem], List[str]]:
        """获取新闻列表（支持按重要性或时间排序）"""
        print(f"[NewsService] get_news调用: category={category}, page={page}, page_size={page_size}, force_refresh={force_refresh}, sort_by={sort_by}")
        
        # 检查缓存
        if not force_refresh and self._cache_time:
            if datetime.now() - self._cache_time < self._cache_ttl:
                print(f"[NewsService] 使用缓存数据")
                news = self._news_cache.get("all", [])
                if category:
                    news = [n for n in news if n.category == category]
                
                # 根据排序方式排序
                if sort_by == "time":
                    news.sort(key=lambda x: x.published_at, reverse=True)
                else:  # importance
                    news.sort(key=lambda x: x.importance_score.total, reverse=True)
                
                result = self._paginate(news, page, page_size)
                print(f"[NewsService] 返回 {len(result)} 条新闻（从缓存）")
                return result, self._get_categories(news)

        # 获取所有新闻
        print(f"[NewsService] 开始抓取新闻源...")
        all_news = await self._fetch_all_sources()
        print(f"[NewsService] 抓取完成，共 {len(all_news)} 条新闻")

        # 更新缓存
        self._news_cache = {"all": all_news}
        self._cache_time = datetime.now()

        # 过滤分类
        if category:
            all_news = [n for n in all_news if n.category == category]

        # 根据排序方式排序
        if sort_by == "time":
            all_news.sort(key=lambda x: x.published_at, reverse=True)
        else:  # importance (默认)
            all_news.sort(key=lambda x: x.importance_score.total, reverse=True)

        result = self._paginate(all_news, page, page_size)
        print(f"[NewsService] 返回 {len(result)} 条新闻")
        return result, self._get_categories(self._news_cache["all"])

    def _paginate(self, items: List[NewsItem], page: int, page_size: int) -> List[NewsItem]:
        """分页"""
        start = (page - 1) * page_size
        end = start + page_size
        return items[start:end]

    def _get_categories(self, items: List[NewsItem]) -> List[str]:
        """获取所有分类"""
        return list(set(item.category for item in items))

    async def get_news_by_id(self, news_id: str) -> Optional[NewsItem]:
        """根据ID获取新闻详情"""
        if "all" not in self._news_cache:
            await self.get_news()

        for news in self._news_cache["all"]:
            if news.id == news_id:
                return news
        return None

    async def search_news(self, query: str, limit: int = 100) -> List[NewsItem]:
        """搜索新闻"""
        if "all" not in self._news_cache:
            await self.get_news()

        query_lower = query.lower()
        results = [
            news for news in self._news_cache["all"]
            if query_lower in news.title.lower() or query_lower in news.summary.lower()
        ]

        return results[:limit]

    def get_top_sources(self) -> List[str]:
        """获取高权重新闻源"""
        return [s.name for s in sorted(self.sources, key=lambda x: x.weight, reverse=True)[:5]]

    async def rate_news_with_agent(self, news_list: List[NewsItem], backend_type: str = "hermes") -> List[Tuple[NewsItem, float]]:
        """
        使用Agent对新闻进行重要性评分
        
        Args:
            news_list: 新闻列表
            backend_type: 使用的后端类型 (hermes/openclaw)
            
        Returns:
            List[Tuple[NewsItem, float]]: 新闻和对应的Agent评分（1-100）
        """
        if not news_list:
            return []
        
        print(f"[NewsService] 开始使用Agent对 {len(news_list)} 条新闻进行重要性评分...")
        
        # 准备新闻标题列表
        news_titles = []
        for i, news in enumerate(news_list):
            news_titles.append({
                "id": i,
                "title": news.title,
                "source": news.source,
                "summary": news.summary[:100]  # 只取前100字符
            })
        
        # 构建提示词
        system_prompt = """你是一个专业的新闻分析师。请根据以下新闻标题，评估每条新闻对相关产业或企业的影响程度。

评分标准（1-100分）：
- 90-100: 重大突破/危机，对整个行业有深远影响
- 70-89: 重要事件，对多个企业或子行业有显著影响
- 50-69: 一般重要，对特定企业或小范围有影响
- 30-49: 轻微影响，关注度较低
- 1-29: 几乎无影响，常规新闻

请返回JSON格式：
{
    "scores": [
        {"id": 0, "score": 85, "reason": "简短说明"},
        {"id": 1, "score": 72, "reason": "简短说明"}
    ]
}

只返回JSON，不要有其他内容。"""

        user_content = f"请评估以下{len(news_titles)}条新闻的重要性：\n\n"
        for item in news_titles:
            user_content += f"[{item['id']}] {item['title']} ({item['source']})\n"
        
        try:
            # 调用Hermes服务
            from .hermes_service import get_hermes_service
            
            hermes = get_hermes_service()
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ]
            
            result = await hermes.chat_openai_format(messages)
            response_text = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            print(f"[NewsService] Agent响应长度: {len(response_text)}")
            
            # 解析JSON
            json_str = response_text.strip()
            if "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0]
            elif "```" in json_str:
                json_str = json_str.split("```")[1].split("```")[0]
            
            data = json.loads(json_str.strip())
            scores_data = data.get("scores", [])
            
            # 创建ID到分数的映射
            score_map = {item["id"]: item["score"] for item in scores_data}
            
            # 将分数应用到新闻
            scored_news = []
            for news in news_list:
                # 找到对应的分数（通过索引）
                idx = news_list.index(news)
                agent_score = score_map.get(idx, 50)  # 默认50分
                
                # 确保分数在1-100范围内
                agent_score = max(1, min(100, agent_score))
                
                scored_news.append((news, agent_score))
                print(f"[NewsService] 新闻 '{news.title[:30]}...' 评分: {agent_score}")
            
            print(f"[NewsService] Agent评分完成，共 {len(scored_news)} 条新闻")
            return scored_news
            
        except Exception as e:
            print(f"[NewsService] Agent评分失败: {e}")
            import traceback
            traceback.print_exc()
            
            # 失败时返回原始新闻和默认分数
            return [(news, 50.0) for news in news_list]

    async def update_news_scores_with_agent(self, category: Optional[str] = None, backend_type: str = "hermes") -> List[NewsItem]:
        """
        使用Agent更新新闻的重要性评分
        
        Args:
            category: 新闻分类（可选）
            backend_type: 使用的后端类型
            
        Returns:
            更新后的新闻列表
        """
        # ✅ 获取新闻（使用正确的参数名 force_refresh）
        news_list, _ = await self.get_news(category=category, page=1, page_size=100, force_refresh=False)
        
        if not news_list:
            return []
        
        print(f"[NewsService] 开始用Agent重新评分 {len(news_list)} 条新闻...")
        
        # 使用Agent评分
        scored_news = await self.rate_news_with_agent(news_list, backend_type)
        
        # 更新新闻的重要性分数
        updated_news = []
        for news, agent_score in scored_news:
            # 创建新的ImportanceScore，使用Agent分数作为总分
            # 保留原有的细分项用于参考
            new_importance = ImportanceScore(
                total=agent_score,  # Agent评分作为总分
                source_weight=news.importance_score.source_weight,
                keyword_weight=news.importance_score.keyword_weight,
                recency_weight=news.importance_score.recency_weight,
                sentiment_weight=news.importance_score.sentiment_weight
            )
            
            # 创建新的NewsItem（因为NewsItem是不可变的）
            updated_news_item = NewsItem(
                id=news.id,
                title=news.title,
                summary=news.summary,
                content=news.content,
                source=news.source,
                url=news.url,
                published_at=news.published_at,
                importance_score=new_importance,
                image_url=news.image_url,
                category=news.category,
                keywords=news.keywords,
                sentiment=news.sentiment
            )
            
            updated_news.append(updated_news_item)
        
        # 按Agent评分排序
        updated_news.sort(key=lambda x: x.importance_score.total, reverse=True)
        
        print(f"[NewsService] Agent评分完成，最高分: {updated_news[0].importance_score.total if updated_news else 0}")
        
        return updated_news
