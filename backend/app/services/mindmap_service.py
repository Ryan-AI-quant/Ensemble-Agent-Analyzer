"""
思维导图服务 - 从新闻内容生成思维导图
"""

import re
import hashlib
from typing import List, Dict, Optional, Set
from collections import defaultdict
import networkx as nx

from ..models.schemas import MindMapNode, MindMapResponse, NewsItem


class MindMapService:
    """思维导图服务：从新闻内容提取结构并生成思维导图"""

    # 关系词映射
    RELATION_PATTERNS = {
        "原因": ["因为", "由于", "导致", "造成", "引起", "because", "due to", "cause", "lead to"],
        "结果": ["所以", "因此", "导致", "使得", "结果是", "therefore", "thus", "result", "consequently"],
        "对比": ["但是", "然而", "不过", "相反", "而", "however", "but", "whereas", "while", "contrast"],
        "举例": ["比如", "例如", "比如", "包括", "如", "for example", "such as", "including", "e.g."],
        "时间": ["首先", "然后", "接着", "最后", "首先", "其次", "finally", "then", "next", "first"],
        "强调": ["重要的是", "关键", "特别", "尤其", "特别是", "importantly", "key", "especially", "particularly"],
    }

    # 实体类型关键词
    ENTITY_KEYWORDS = {
        "人物": ["CEO", "CTO", "创始人", "总裁", "总监", "教授", "博士", "专家", "president", "founder", "CEO", "expert"],
        "公司": ["公司", "企业", "集团", "厂商", "企业", "company", "firm", "corporation", "enterprise"],
        "产品": ["产品", "服务", "平台", "系统", "工具", "software", "platform", "system", "service"],
        "技术": ["技术", "算法", "模型", "框架", "架构", "technology", "algorithm", "model", "framework"],
        "事件": ["发布", "收购", "合作", "融资", "推出", "launch", "acquire", "partner", "funding"],
    }

    def __init__(self):
        self._mindmap_cache: Dict[str, MindMapResponse] = {}

    def _generate_id(self, text: str) -> str:
        """生成唯一ID（使用完整16字符MD5，避免截断碰撞）"""
        return hashlib.md5(text.encode()).hexdigest()[:16]

    def generate_mindmap(self, news: NewsItem, layout: str = "radial") -> MindMapResponse:
        """从新闻生成思维导图"""
        # 检查缓存
        cache_key = f"{news.id}_{layout}"
        if cache_key in self._mindmap_cache:
            return self._mindmap_cache[cache_key]

        # 构建文本内容
        content = news.title + " " + news.summary
        if news.content:
            content += " " + news.content

        # 创建根节点
        root = MindMapNode(
            id="root",
            text=self._truncate_text(news.title, 50),
            expand=True,
            color="#4F46E5",
            font_size=16,
            level=0
        )

        # 提取主要概念
        concepts = self._extract_main_concepts(content)
        root.children = []

        # 添加分类子节点
        if concepts["categories"]:
            cat_node = MindMapNode(
                id=self._generate_id("categories"),
                text="核心主题",
                expand=True,
                color="#10B981",
                font_size=14,
                level=1
            )
            cat_node.children = [
                MindMapNode(
                    id=self._generate_id(cat),
                    text=cat,
                    expand=True,
                    color="#10B981",
                    font_size=12,
                    level=2
                ) for cat in concepts["categories"][:5]
            ]
            root.children.append(cat_node)

        # 添加关键实体子节点
        if concepts["entities"]:
            entity_node = MindMapNode(
                id=self._generate_id("entities"),
                text="关键实体",
                expand=True,
                color="#F59E0B",
                font_size=14,
                level=1
            )
            entity_node.children = [
                MindMapNode(
                    id=self._generate_id(f"{ent_type}_{ent}"),
                    text=f"{ent_type}: {ent}",
                    expand=True,
                    color="#F59E0B",
                    font_size=12,
                    level=2
                ) for ent_type, entities in list(concepts["entities"].items())[:3]
                for ent in entities[:3]
            ]
            root.children.append(entity_node)

        # 添加关系子节点
        if concepts["relations"]:
            rel_node = MindMapNode(
                id=self._generate_id("relations"),
                text="逻辑关系",
                expand=True,
                color="#EF4444",
                font_size=14,
                level=1
            )
            rel_node.children = [
                MindMapNode(
                    id=self._generate_id(f"relation_{rel}"),
                    text=rel,
                    expand=True,
                    color="#EF4444",
                    font_size=12,
                    level=2
                ) for rel in concepts["relations"]
            ]
            root.children.append(rel_node)

        # 添加关键词子节点
        if news.keywords:
            kw_node = MindMapNode(
                id=self._generate_id("keywords"),
                text="关键词",
                expand=True,
                color="#8B5CF6",
                font_size=14,
                level=1
            )
            kw_node.children = [
                MindMapNode(
                    id=self._generate_id(f"kw_{kw}"),
                    text=kw,
                    expand=True,
                    color="#8B5CF6",
                    font_size=11,
                    level=2
                ) for kw in news.keywords[:8]
            ]
            root.children.append(kw_node)

        # 添加摘要子节点
        summary_node = MindMapNode(
            id=self._generate_id("summary"),
            text="内容摘要",
            expand=True,
            color="#6366F1",
            font_size=14,
            level=1
        )
        summary_sentences = self._split_into_sentences(news.summary)
        summary_node.children = [
            MindMapNode(
                id=self._generate_id(f"sent_{i}"),
                text=self._truncate_text(sent, 60),
                expand=True,
                color="#6366F1",
                font_size=11,
                level=2
            ) for i, sent in enumerate(summary_sentences[:4])
        ]
        root.children.append(summary_node)

        # 计算总节点数
        total_nodes = self._count_nodes(root)

        response = MindMapResponse(
            news_id=news.id,
            root=root,
            layout=layout,
            total_nodes=total_nodes
        )

        # 缓存结果
        self._mindmap_cache[cache_key] = response

        return response

    def _truncate_text(self, text: str, max_length: int) -> str:
        """截断文本"""
        if len(text) <= max_length:
            return text
        return text[:max_length-3] + "..."

    def _count_nodes(self, node: MindMapNode) -> int:
        """递归计算节点数"""
        count = 1
        for child in node.children:
            count += self._count_nodes(child)
        return count

    def _extract_main_concepts(self, content: str) -> Dict:
        """提取主要概念"""
        concepts = {
            "categories": [],
            "entities": defaultdict(list),
            "relations": []
        }

        # 提取关键词中的主题词
        words = re.findall(r'\b[a-zA-Z\u4e00-\u9fa5]{2,}\b', content.lower())
        word_freq = defaultdict(int)
        for word in words:
            word_freq[word] += 1

        # 识别主题类别
        themes = {
            "AI/人工智能": ["ai", "artificial", "intelligence", "人工智能", "机器学习", "深度学习", "大模型"],
            "科技": ["tech", "technology", "科技", "技术", "数字", "digital"],
            "商业": ["business", "company", "market", "商业", "公司", "市场", "企业"],
            "金融": ["finance", "investment", "funding", "金融", "投资", "融资", "资本"],
            "政策": ["policy", "government", "regulation", "政策", "政府", "监管", "法规"],
        }

        for theme, keywords in themes.items():
            if any(kw in content.lower() for kw in keywords):
                concepts["categories"].append(theme)

        # 如果没有识别到主题，添加"综合新闻"
        if not concepts["categories"]:
            concepts["categories"].append("综合新闻")

        # 提取实体
        for ent_type, keywords in self.ENTITY_KEYWORDS.items():
            for keyword in keywords:
                pattern = rf'{keyword}[\s:：]+([^\s，,。.；;！!？?]+)'
                matches = re.findall(pattern, content)
                concepts["entities"][ent_type].extend(matches[:2])

        # 提取关系
        for rel_type, patterns in self.RELATION_PATTERNS.items():
            for pattern in patterns:
                if pattern in content.lower():
                    if rel_type not in concepts["relations"]:
                        concepts["relations"].append(rel_type)
                    break

        # 去重
        for key in concepts["entities"]:
            concepts["entities"][key] = list(set(concepts["entities"][key]))

        return concepts

    def _split_into_sentences(self, text: str) -> List[str]:
        """将文本分割成句子"""
        # 中英文句子分隔符
        sentences = re.split(r'[。.！!？?；;]', text)
        return [s.strip() for s in sentences if s.strip()]

    def generate_from_text(self, title: str, content: str, layout: str = "radial") -> MindMapResponse:
        """从纯文本生成思维导图"""
        # 创建一个临时的NewsItem
        news = NewsItem(
            id=self._generate_id(title),
            title=title,
            summary=content[:500],
            source="user_input",
            url="",
            published_at=datetime.now(),
            importance_score=None,
            category="general",
            keywords=[]
        )

        # 计算importance_score
        from ..models.schemas import ImportanceScore
        news.importance_score = ImportanceScore(
            total=50.0,
            source_weight=15.0,
            keyword_weight=15.0,
            recency_weight=10.0,
            sentiment_weight=10.0
        )

        return self.generate_mindmap(news, layout)

    def generate_from_analysis(self, analysis_result, news_id: str = "analysis", layout: str = "radial") -> MindMapResponse:
        """
        从 OpenClaw 分析结果生成思维导图

        Args:
            analysis_result: OpenClawAnalysisResult 分析结果
            news_id: 新闻ID
            layout: 布局类型

        Returns:
            MindMapResponse: 思维导图响应
        """
        # 创建根节点
        root = MindMapNode(
            id="root",
            text=self._truncate_text(analysis_result.title, 50),
            expand=True,
            color="#4F46E5",  # 主色
            font_size=16,
            level=0
        )
        root.children = []

        # 1. 添加摘要节点
        summary_node = MindMapNode(
            id=self._generate_id("summary"),
            text="📋 新闻摘要",
            expand=True,
            color="#6366F1",
            font_size=14,
            level=1
        )
        summary_node.children = [
            MindMapNode(
                id=self._generate_id(f"summary_text"),
                text=self._truncate_text(analysis_result.summary, 80),
                expand=False,
                color="#818CF8",
                font_size=12,
                level=2
            )
        ]
        root.children.append(summary_node)

        # 2. 添加核心要点节点
        if analysis_result.key_points:
            key_points_node = MindMapNode(
                id=self._generate_id("key_points"),
                text="🔑 核心要点",
                expand=True,
                color="#10B981",  # 绿色
                font_size=14,
                level=1
            )
            key_points_node.children = [
                MindMapNode(
                    id=self._generate_id(f"kp_{i}"),
                    text=self._truncate_text(point, 50),
                    expand=False,
                    color="#34D399",
                    font_size=12,
                    level=2
                ) for i, point in enumerate(analysis_result.key_points[:5])
            ]
            root.children.append(key_points_node)

        # 3. 添加影响分析节点
        if analysis_result.impact_analysis:
            impact_node = MindMapNode(
                id=self._generate_id("impact_analysis"),
                text="📊 影响分析",
                expand=True,
                color="#F59E0B",  # 橙色
                font_size=14,
                level=1
            )
            impact_node.children = [
                MindMapNode(
                    id=self._generate_id(f"impact_{i}"),
                    text=self._truncate_text(impact, 50),
                    expand=False,
                    color="#FBBF24",
                    font_size=12,
                    level=2
                ) for i, impact in enumerate(analysis_result.impact_analysis[:5])
            ]
            root.children.append(impact_node)

        # 4. 添加相关实体节点
        if analysis_result.related_entities:
            entities_node = MindMapNode(
                id=self._generate_id("entities"),
                text="👥 相关实体",
                expand=True,
                color="#EC4899",  # 粉色
                font_size=14,
                level=1
            )
            entities_node.children = [
                MindMapNode(
                    id=self._generate_id(f"entity_{i}"),
                    text=f"{entity.get('name', 'Unknown')} ({entity.get('type', 'unknown')})",
                    expand=False,
                    color="#F472B6",
                    font_size=11,
                    level=2
                ) for i, entity in enumerate(analysis_result.related_entities[:5])
            ]
            root.children.append(entities_node)

        # 5. 添加情感分析节点
        sentiment_colors = {
            "positive": "#10B981",  # 绿色
            "negative": "#EF4444",   # 红色
            "neutral": "#6B7280"     # 灰色
        }
        sentiment_node = MindMapNode(
            id=self._generate_id("sentiment"),
            text=f"💭 情感分析: {analysis_result.sentiment}",
            expand=True,
            color=sentiment_colors.get(analysis_result.sentiment, "#6B7280"),
            font_size=14,
            level=1
        )
        sentiment_node.children = [
            MindMapNode(
                id=self._generate_id("confidence"),
                text=f"置信度: {analysis_result.confidence:.0%}",
                expand=False,
                color=sentiment_colors.get(analysis_result.sentiment, "#6B7280"),
                font_size=12,
                level=2
            )
        ]
        root.children.append(sentiment_node)

        # 6. 添加分类标签节点
        if analysis_result.categories:
            categories_node = MindMapNode(
                id=self._generate_id("categories"),
                text="🏷️ 分类标签",
                expand=True,
                color="#8B5CF6",  # 紫色
                font_size=14,
                level=1
            )
            categories_node.children = [
                MindMapNode(
                    id=self._generate_id(f"cat_{cat}"),
                    text=cat,
                    expand=False,
                    color="#A78BFA",
                    font_size=12,
                    level=2
                ) for cat in analysis_result.categories[:4]
            ]
            root.children.append(categories_node)

        # 7. 添加来源分析节点
        if analysis_result.source_analysis:
            source_node = MindMapNode(
                id=self._generate_id("source"),
                text="📰 来源分析",
                expand=True,
                color="#0EA5E9",  # 蓝色
                font_size=14,
                level=1
            )
            source_data = analysis_result.source_analysis
            source_node.children = [
                MindMapNode(
                    id=self._generate_id(f"source_{key}"),
                    text=f"{key}: {value}",
                    expand=False,
                    color="#38BDF8",
                    font_size=11,
                    level=2
                ) for key, value in source_data.items()
            ]
            root.children.append(source_node)

        # 计算总节点数
        total_nodes = self._count_nodes(root)

        return MindMapResponse(
            news_id=news_id,
            root=root,
            layout=layout,
            total_nodes=total_nodes
        )

    def _convert_graph_to_tree(self, graph_data: Dict) -> Dict:
        """
        将图结构（nodes/edges）转换为树形结构（name/children）
        
        Args:
            graph_data: {"nodes": [...], "edges": [...]}
            
        Returns:
            {"name": "...", "children": [...]}
        """
        nodes = graph_data.get("nodes", [])
        edges = graph_data.get("edges", [])
        
        if not nodes:
            return {"name": "产业链分析", "children": []}
        
        # 找到根节点（没有父节点的节点，或者第一个节点）
        node_map = {node.get("id"): node for node in nodes}
        child_ids = set()
        
        # 收集所有作为目标的节点ID
        for edge in edges:
            target = edge.get("target") or edge.get("to")
            if target:
                child_ids.add(target)
        
        # 找到根节点（不在child_ids中的节点）
        root_node = None
        for node in nodes:
            node_id = node.get("id")
            if node_id not in child_ids:
                root_node = node
                break
        
        # 如果没找到根节点，使用第一个节点
        if not root_node and nodes:
            root_node = nodes[0]
        
        if not root_node:
            return {"name": "产业链分析", "children": []}
        
        # 递归构建树
        def build_tree(node_id: str, visited: set = None) -> Dict:
            if visited is None:
                visited = set()
            
            if node_id in visited:
                # 避免循环引用
                return {"name": node_map.get(node_id, {}).get("text", "未知节点"), "children": []}
            
            visited.add(node_id)
            
            node_info = node_map.get(node_id, {})
            node_name = (node_info.get("text") or node_info.get("name") or 
                        node_info.get("label") or node_info.get("title") or 
                        node_info.get("description") or "未知节点")
            print(f"[MindMapService] _convert_graph_to_tree: node_id={node_id}, extracted_name={node_name[:50] if node_name else '(empty)'}")
            
            # 找到所有以当前节点为源的边
            children = []
            for edge in edges:
                source = edge.get("source") or edge.get("from")
                target = edge.get("target") or edge.get("to")
                
                if source == node_id and target in node_map:
                    child_tree = build_tree(target, visited.copy())
                    children.append(child_tree)
            
            return {
                "name": node_name,
                "children": children
            }
        
        return build_tree(root_node.get("id"))

    def generate_from_industry_chain(self, industry_chain_data: Dict, news_id: str = "industry", 
                                      analysis_text: str = "", layout: str = "radial") -> MindMapResponse:
        """
        从产业链数据生成思维导图

        Args:
            industry_chain_data: 产业链JSON数据（支持两种格式）
                - 树形结构: {"name": "...", "children": [...]}
                - 图结构: {"nodes": [...], "edges": [...]}
            news_id: 新闻ID
            analysis_text: AI分析的文字内容（短中长期影响）
            layout: 布局类型

        Returns:
            MindMapResponse: 思维导图响应
        """
        print(f"[MindMapService] generate_from_industry_chain 被调用:")
        print(f"  - industry_chain_data keys: {list(industry_chain_data.keys()) if industry_chain_data else 'None'}")
        print(f"  - analysis_text length: {len(analysis_text) if analysis_text else 0}")
        
        # ✅ 检测数据格式并转换
        if "nodes" in industry_chain_data and "edges" in industry_chain_data:
            # 图结构格式，需要转换为树形结构
            print(f"[MindMapService] 检测到图结构格式 (nodes/edges)，正在转换为树形结构...")
            industry_chain_data = self._convert_graph_to_tree(industry_chain_data)
            print(f"[MindMapService] 转换完成: name={industry_chain_data.get('name')}, children_count={len(industry_chain_data.get('children', []))}")
        
        # 创建根节点
        root = MindMapNode(
            id="root",
            text=self._truncate_text(industry_chain_data.get("name", "产业链分析"), 50),
            expand=True,
            color="#4F46E5",
            font_size=16,
            level=0
        )
        root.children = []

        # 递归构建产业链节点
        def build_chain_nodes(data: Dict, parent_level: int = 0) -> List[MindMapNode]:
            """递归构建产业链节点树"""
            nodes = []
            children = data.get("children", [])
            
            print(f"[MindMapService] build_chain_nodes: level={parent_level}, children_count={len(children)}")
            
            # 颜色映射（根据层级）
            colors = [
                "#6366F1",  # 第1层 - 紫色
                "#8B5CF6",  # 第2层 - 深紫
                "#A78BFA",  # 第3层 - 浅紫
                "#C4B5FD",  # 第4层 - 更浅
                "#DDD6FE",  # 第5层 - 最浅
            ]
            
            for idx, child in enumerate(children):
                level = parent_level + 1
                color_idx = min(level - 1, len(colors) - 1)
                
                # 使用父节点名称确保不同分支下的同级节点ID不重复
                parent_name = data.get("name", "root")
                node_id_str = f"chain_{parent_name}_{level}_{idx}"
                node_id = self._generate_id(node_id_str)
                node = MindMapNode(
                    id=node_id,
                    text=self._truncate_text(child.get("name") or "未命名", 40),
                    expand=True if level < 3 else False,  # 前两层默认展开
                    color=colors[color_idx],
                    font_size=max(14 - level, 10),  # 层级越深字体越小
                    level=level
                )
                print(f"[MindMapService] build_chain_nodes: id={node_id} (from '{node_id_str}'), text={child.get('name', '?')[:30]}")
                
                # 递归处理子节点
                if child.get("children"):
                    node.children = build_chain_nodes(child, level)
                
                nodes.append(node)
            
            return nodes

        # 构建产业链节点树
        root.children = build_chain_nodes(industry_chain_data)

        # 计算总节点数
        total_nodes = self._count_nodes(root)

        print(f"[MindMapService] generate_from_industry_chain 完成:")
        print(f"  - 根节点文本: {root.text}")
        print(f"  - 子节点数量: {len(root.children)}")
        print(f"  - 总节点数: {total_nodes}")
        print(f"  - analysis_text长度: {len(analysis_text) if analysis_text else 0}")

        return MindMapResponse(
            news_id=news_id,
            root=root,
            layout=layout,
            total_nodes=total_nodes,
            analysis_text=analysis_text  # ✅ 添加分析文本
        )

    def get_layout_options(self) -> List[Dict]:
        """获取可选的布局类型"""
        return [
            {"id": "radial", "name": "放射状布局", "description": "从中心向四周发散，适合展示主题与概念的关系"},
            {"id": "horizontal", "name": "水平布局", "description": "从左到右水平展开，适合时间线或流程展示"},
            {"id": "vertical", "name": "垂直布局", "description": "从上到下垂直展开，适合层次结构"},
        ]


# 需要导入datetime
from datetime import datetime
