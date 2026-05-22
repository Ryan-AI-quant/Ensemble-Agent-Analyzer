"""
API路由模块
"""

from .chat import router as chat_router
from .news import router as news_router
from .mindmap import router as mindmap_router

__all__ = ["chat_router", "news_router", "mindmap_router"]
