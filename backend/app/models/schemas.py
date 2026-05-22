"""
Pydantic 数据模型定义
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


class ImportanceScore(BaseModel):
    """新闻重要性评分"""
    total: float = Field(..., description="总分")
    source_weight: float = Field(..., description="来源权重分")
    keyword_weight: float = Field(..., description="关键词匹配分")
    recency_weight: float = Field(..., description="时效性分")
    sentiment_weight: float = Field(..., description="情感权重分")


class NewsItem(BaseModel):
    """新闻条目模型"""
    id: str = Field(..., description="唯一标识")
    title: str = Field(..., description="新闻标题")
    summary: str = Field(..., description="新闻摘要")
    content: Optional[str] = Field(None, description="完整内容")
    source: str = Field(..., description="新闻来源")
    url: str = Field(..., description="原始链接")
    published_at: datetime = Field(..., description="发布时间")
    importance_score: ImportanceScore = Field(..., description="重要性评分")
    image_url: Optional[str] = Field(None, description="配图URL")
    category: str = Field(..., description="新闻类别")
    keywords: List[str] = Field(default_factory=list, description="关键词列表")
    sentiment: str = Field(default="neutral", description="情感倾向: positive/negative/neutral")


class NewsListResponse(BaseModel):
    """新闻列表响应"""
    items: List[NewsItem] = Field(..., description="新闻列表")
    total: int = Field(..., description="总数")
    page: int = Field(..., description="当前页")
    page_size: int = Field(..., description="每页数量")
    categories: List[str] = Field(..., description="可用类别")


class MindMapNode(BaseModel):
    """思维导图节点"""
    id: str = Field(..., description="节点ID")
    text: str = Field(..., description="节点文本")
    children: List["MindMapNode"] = Field(default_factory=list, description="子节点")
    expand: bool = Field(default=True, description="是否展开")
    color: Optional[str] = Field(None, description="节点颜色")
    font_size: Optional[int] = Field(None, description="字体大小")
    level: int = Field(default=0, description="层级深度")


class MindMapResponse(BaseModel):
    """思维导图响应"""
    news_id: str = Field(..., description="关联的新闻ID")
    root: MindMapNode = Field(..., description="根节点")
    layout: str = Field(default="radial", description="布局类型: radial/horizontal/vertical")
    total_nodes: int = Field(..., description="节点总数")
    analysis_text: Optional[str] = Field(None, description="AI分析的文字内容（短中长期影响）")


class MessageRole(str, Enum):
    """消息角色"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ChatMessage(BaseModel):
    """聊天消息"""
    role: MessageRole = Field(..., description="角色")
    content: str = Field(..., description="消息内容")
    timestamp: datetime = Field(default_factory=datetime.now, description="时间戳")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")


class ChatRequest(BaseModel):
    """聊天请求"""
    message: str = Field(..., description="用户消息")
    session_id: str = Field(default="default", description="会话ID")
    context: Optional[List[ChatMessage]] = Field(None, description="上下文")


class ChatResponse(BaseModel):
    """聊天响应"""
    message: ChatMessage = Field(..., description="助手消息")
    session_id: str = Field(..., description="会话ID")
    suggestions: List[str] = Field(default_factory=list, description="建议回复")


class OpenClawConfig(BaseModel):
    """OpenClaw配置"""
    api_url: str = Field(default="http://localhost:18789", description="OpenClaw API地址")
    api_key: Optional[str] = Field(None, description="API密钥")
    model: str = Field(default="gpt-4", description="使用的模型")
    max_tokens: int = Field(default=2000, description="最大输出token")
    temperature: float = Field(default=0.7, description="温度参数")


class HealthCheck(BaseModel):
    """健康检查响应"""
    status: str = Field(..., description="服务状态")
    version: str = Field(..., description="版本号")
    openclaw_connected: bool = Field(..., description="OpenClaw连接状态")
    services: Dict[str, bool] = Field(..., description="各服务状态")
