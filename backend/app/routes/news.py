"""
新闻路由 - 处理新闻获取和搜索
"""

from fastapi import APIRouter, HTTPException, Query, Body
from typing import Optional, List
from pydantic import BaseModel

from ..models.schemas import NewsListResponse, NewsItem
from ..services.news_service import NewsService

router = APIRouter(prefix="/api/news", tags=["news"])

# 全局新闻服务实例
news_service = NewsService()


class AgentRatingRequest(BaseModel):
    """Agent评分请求"""
    category: Optional[str] = None
    backend_type: str = "hermes"


@router.get("/", response_model=NewsListResponse, summary="获取新闻列表")
async def get_news(
    category: Optional[str] = Query(None, description="新闻分类过滤"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=50, description="每页数量"),
    refresh: bool = Query(False, description="强制刷新"),
    sort_by: str = Query("importance", description="排序方式: importance(重要性) 或 time(时间)")
):
    """
    获取新闻列表，支持按重要性或时间排序

    - **category**: 可选，新闻分类（如 technology, business, world）
    - **page**: 页码，从1开始
    - **page_size**: 每页数量，最大50
    - **refresh**: 是否强制刷新缓存
    - **sort_by**: 排序方式，"importance"(默认，按重要性) 或 "time"(按时间)
    """
    try:
        items, categories = await news_service.get_news(
            category=category,
            page=page,
            page_size=page_size,
            force_refresh=refresh,
            sort_by=sort_by
        )

        return NewsListResponse(
            items=items,
            total=len(items),
            page=page,
            page_size=page_size,
            categories=categories
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取新闻失败: {str(e)}")


@router.get("/{news_id}", response_model=NewsItem, summary="获取新闻详情")
async def get_news_detail(news_id: str):
    """根据ID获取单条新闻详情"""
    news = await news_service.get_news_by_id(news_id)
    if not news:
        raise HTTPException(status_code=404, detail="新闻不存在")
    return news


@router.get("/search/", response_model=List[NewsItem], summary="搜索新闻")
async def search_news(
    q: str = Query(..., min_length=1, description="搜索关键词"),
    limit: int = Query(10, ge=1, le=50, description="返回数量")
):
    """搜索新闻"""
    try:
        results = await news_service.search_news(q, limit)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")


@router.get("/meta/categories", response_model=List[str], summary="获取新闻分类")
async def get_categories():
    """获取所有可用的新闻分类"""
    try:
        # 确保已加载新闻
        _, categories = await news_service.get_news()
        return categories
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取分类失败: {str(e)}")


@router.get("/meta/sources", response_model=List[str], summary="获取高权重新闻源")
async def get_top_sources():
    """获取高权重新闻源列表"""
    return news_service.get_top_sources()


@router.post("/rate-with-agent", response_model=NewsListResponse, summary="使用Agent重新评分新闻")
async def rate_news_with_agent(
    request: AgentRatingRequest = Body(...)
):
    """
    使用AI Agent对新闻进行重要性评分
    
    - **category**: 可选，新闻分类
    - **backend_type**: 使用的后端类型 (hermes/openclaw)
    
    注意：此操作会调用AI服务，可能需要较长时间（30-60秒）
    """
    try:
        print(f"[NewsRoute] 收到Agent评分请求: category={request.category}, backend={request.backend_type}")
        
        # 使用Agent重新评分
        updated_news = await news_service.update_news_scores_with_agent(
            category=request.category,
            backend_type=request.backend_type
        )
        
        print(f"[NewsRoute] Agent评分完成，返回 {len(updated_news)} 条新闻")
        
        # 获取分类
        _, categories = await news_service.get_news(category=request.category)
        
        return NewsListResponse(
            items=updated_news,
            total=len(updated_news),
            page=1,
            page_size=len(updated_news),
            categories=categories
        )
    except Exception as e:
        import traceback
        print(f"[NewsRoute] Agent评分失败: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Agent评分失败: {str(e)}")
