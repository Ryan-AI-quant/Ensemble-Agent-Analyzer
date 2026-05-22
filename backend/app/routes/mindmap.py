"""
思维导图路由 - 处理思维导图生成
"""

from fastapi import APIRouter, HTTPException, Query, Body
from typing import Optional, List
from pydantic import BaseModel

from ..models.schemas import MindMapResponse, NewsItem
from ..services.mindmap_service import MindMapService
from ..services.news_service import NewsService
from ..services.news_analysis_service import OpenClawAnalysisService, NewsAnalysisResult, unified_analysis_service
from ..config import BackendType

router = APIRouter(prefix="/api/mindmap", tags=["mindmap"])

# 全局服务实例
mindmap_service = MindMapService()
news_service = NewsService()
analysis_service = OpenClawAnalysisService()


class AnalyzeAndGenerateRequest(BaseModel):
    """分析并生成思维导图的请求"""
    title: Optional[str] = None
    content: str
    news_id: Optional[str] = None
    backend_type: Optional[str] = None  # openclaw, hermes, local (默认使用配置的后端)


class AnalyzeAndGenerateResponse(BaseModel):
    """分析并生成思维导图的响应"""
    analysis: NewsAnalysisResult
    mindmap: MindMapResponse
    used_backend: str
    analysis_text: Optional[str] = None  # AI分析的文字内容（短中长期影响）

class UpdateSettingsRequest(BaseModel):
    """更新设置的请求"""
    backend_type: Optional[str] = None
    llm_model: Optional[str] = None


@router.get("/from-news/{news_id}", response_model=MindMapResponse, summary="从新闻生成思维导图")
async def generate_from_news(
    news_id: str,
    layout: str = Query("radial", description="布局类型: radial, horizontal, vertical"),
    use_analysis: bool = Query(False, description="是否使用 OpenClaw 分析")
):
    """根据新闻ID生成对应的思维导图"""
    try:
        # 获取新闻内容
        news = await news_service.get_news_by_id(news_id)
        if not news:
            raise HTTPException(status_code=404, detail="新闻不存在")

        # 如果启用 OpenClaw 分析
        if use_analysis:
            analysis = await analysis_service.analyze_news(
                news_content=news.content or news.summary,
                news_title=news.title
            )
            mindmap = mindmap_service.generate_from_analysis(
                analysis_result=analysis,
                news_id=news.id,
                layout=layout
            )
            return mindmap

        # 直接生成思维导图
        mindmap = mindmap_service.generate_mindmap(news, layout)
        return mindmap

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成思维导图失败: {str(e)}")


@router.post("/analyze-and-generate", response_model=AnalyzeAndGenerateResponse, summary="分析新闻并生成思维导图")
async def analyze_and_generate_mindmap(
    request: AnalyzeAndGenerateRequest = Body(...)
):
    """
    使用配置的后端（OpenClaw/Hermes/本地）分析新闻内容，然后生成对应的思维导图。

    流程：
    1. 根据 backend_type 选择分析服务
    2. 进行产业链分析（短中长期影响 + 产业链结构）
    3. 将分析结果转换为思维导图结构
    """
    try:
        print(f"[MindMap] 收到分析并生成请求:")
        print(f"  - 标题: {request.title[:50]}...")
        print(f"  - 内容长度: {len(request.content)}")
        print(f"  - backend_type: {request.backend_type}")
        
        # 生成新闻ID
        news_id = request.news_id or f"custom_{hash(abs(hash(request.content))) % 10**8}"

        # 确定使用哪个后端
        force_backend = None
        if request.backend_type:
            try:
                force_backend = BackendType(request.backend_type)
                print(f"  - force_backend: {force_backend}")
            except ValueError:
                raise HTTPException(status_code=400, detail=f"无效的后端类型: {request.backend_type}")

        backend_used = force_backend.value if force_backend else "configured"

        # ✅ 只进行产业链分析（包含文字分析和思维导图数据）
        print(f"[MindMap] 开始调用unified_analysis_service.analyze_industry_chain...")
        industry_chain_result = await unified_analysis_service.analyze_industry_chain(
            news_content=request.content,
            news_title=request.title or "",
            force_backend=force_backend
        )
        print(f"[MindMap] 产业链分析完成")
        print(f"[MindMap]   - 分析文本长度: {len(industry_chain_result.analysis_text) if industry_chain_result.analysis_text else 0}")
        print(f"[MindMap]   - 思维导图数据格式: {list(industry_chain_result.mindmap_data.keys()) if industry_chain_result.mindmap_data else 'None'}")
        print(f"[MindMap]   - 分析文本预览: {industry_chain_result.analysis_text[:100] if industry_chain_result.analysis_text else 'None'}...")

        # 从产业链分析结果生成思维导图
        mindmap = mindmap_service.generate_from_industry_chain(
            industry_chain_data=industry_chain_result.mindmap_data,
            news_id=news_id,
            analysis_text=industry_chain_result.analysis_text
        )
        print(f"[MindMap] 思维导图生成完成")
        print(f"[MindMap]   - 思维导图节点总数: {mindmap.total_nodes}")
        print(f"[MindMap]   - 返回的analysis_text长度: {len(industry_chain_result.analysis_text) if industry_chain_result.analysis_text else 0}")

        # ✅ 创建一个空的NewsAnalysisResult作为占位符（保持API兼容性）
        from datetime import datetime
        placeholder_analysis = NewsAnalysisResult(
            title=request.title or "",
            summary=request.content[:100],
            key_points=[],
            impact_analysis=[],
            related_entities=[],
            sentiment="neutral",
            confidence=0.0,
            categories=[],
            source_analysis={},
            generated_at=datetime.now().isoformat()
        )

        return AnalyzeAndGenerateResponse(
            analysis=placeholder_analysis,  # ✅ 使用占位符
            mindmap=mindmap,
            used_backend=backend_used,
            analysis_text=industry_chain_result.analysis_text
        )

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"[MindMap] 分析并生成思维导图失败:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"分析并生成思维导图失败: {str(e)}")


@router.post("/from-text", response_model=MindMapResponse, summary="从文本生成思维导图")
async def generate_from_text(
    title: str = Query(..., description="标题"),
    content: str = Query(..., description="内容"),
    layout: str = Query("radial", description="布局类型"),
    use_analysis: bool = Query(True, description="是否使用 OpenClaw 分析")
):
    """从纯文本内容生成思维导图"""
    try:
        # 如果启用 OpenClaw 分析
        if use_analysis:
            analysis = analysis_service._local_analysis(content, title)
            mindmap = mindmap_service.generate_from_analysis(
                analysis_result=analysis,
                news_id=f"text_{hash(abs(hash(content))) % 10**8}",
                layout=layout
            )
            return mindmap

        # 直接生成思维导图
        mindmap = mindmap_service.generate_from_text(title, content, layout)
        return mindmap
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成思维导图失败: {str(e)}")


@router.get("/layouts", summary="获取布局选项")
async def get_layouts():
    """获取所有可用的思维导图布局类型"""
    return mindmap_service.get_layout_options()


@router.get("/analysis-status", summary="获取分析服务状态")
async def get_analysis_status():
    """获取所有分析服务的连接状态"""
    try:
        status = await unified_analysis_service.get_status()
        return status
    except Exception as e:
        return {
            "service": "UnifiedAnalysisService",
            "available": False,
            "error": str(e)
        }


@router.post("/switch-backend", summary="切换后端")
async def switch_backend(backend_type: str = Query(..., description="后端类型: openclaw, hermes, local")):
    """
    切换分析后端

    - openclaw: 使用 OpenClaw 进行分析
    - hermes: 使用 Hermes (Ollama) 进行分析
    - local: 使用本地分析（无需外部服务）
    """
    try:
        bt = BackendType(backend_type)
        result = await unified_analysis_service.switch_backend(bt)
        return result
    except ValueError:
        raise HTTPException(status_code=400, detail=f"无效的后端类型: {backend_type}，可用值: openclaw, hermes, local")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"切换后端失败: {str(e)}")


@router.post("/update-settings", summary="更新系统设置")
async def update_settings(request: UpdateSettingsRequest = Body(...)):
    """
    更新系统设置
    
    - backend_type: 切换后端类型 (openclaw, hermes)
    - llm_model: 更新LLM模型名称
    """
    from ..config import update_backend_type, update_llm_model, get_backend_display_name, get_config, HermesConfig, OpenClawConfig, BackendType
    import os
    
    try:
        # 更新后端类型
        if request.backend_type:
            try:
                bt = BackendType(request.backend_type)
                update_backend_type(bt)
                
                # 重新加载配置
                config = get_config()
                
                # 重新加载对应后端的完整配置
                if bt == BackendType.HERMES:
                    # 重新创建Hermes配置，从环境变量读取
                    new_hermes_config = HermesConfig(
                        api_url=os.getenv("HERMES_API_URL", "http://localhost:11434"),
                        api_key=os.getenv("HERMES_API_KEY"),
                        model=os.getenv("HERMES_MODEL", "llama3"),
                        api_format=os.getenv("HERMES_API_FORMAT", "ollama"),
                        max_tokens=int(os.getenv("HERMES_MAX_TOKENS", "2000")),
                        temperature=float(os.getenv("HERMES_TEMPERATURE", "0.7"))
                    )
                    config.hermes = new_hermes_config
                    print(f"[UpdateSettings] Hermes配置已重新加载:")
                    print(f"  API URL: {config.hermes.api_url}")
                    print(f"  Model: {config.hermes.model}")
                    print(f"  API Format: {config.hermes.api_format}")
                    
                elif bt == BackendType.OPENCLAW:
                    # 重新创建OpenClaw配置
                    new_openclaw_config = OpenClawConfig(
                        api_url=os.getenv("OPENCLAW_API_URL", "http://localhost:18789"),
                        api_key=os.getenv("OPENCLAW_API_KEY"),
                        model=os.getenv("OPENCLAW_MODEL", "default"),
                        max_tokens=int(os.getenv("OPENCLAW_MAX_TOKENS", "2000")),
                        temperature=float(os.getenv("OPENCLAW_TEMPERATURE", "0.7"))
                    )
                    config.openclaw = new_openclaw_config
                    print(f"[UpdateSettings] OpenClaw配置已重新加载:")
                    print(f"  API URL: {config.openclaw.api_url}")
                    print(f"  Model: {config.openclaw.model}")
                    
            except ValueError:
                raise HTTPException(status_code=400, detail=f"无效的后端类型: {request.backend_type}")
        
        # 更新LLM模型
        if request.llm_model:
            update_llm_model(request.llm_model)
            print(f"[UpdateSettings] LLM模型已更新为: {request.llm_model}")
        
        return {
            "success": True,
            "message": "设置已更新",
            "current_backend": get_backend_display_name()
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"[UpdateSettings] 错误详情:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"更新设置失败: {str(e)}")


@router.get("/backend-config", summary="获取后端配置")
async def get_backend_config():
    """获取当前后端配置"""
    from ..config import get_config, get_backend_display_name, BackendType

    config = get_config()
    return {
        "current_backend": get_backend_display_name(),
        "backend_type": config.backend_type.value,
        "openclaw": {
            "api_url": config.openclaw.api_url,
            "model": config.openclaw.model,
            "configured": bool(config.openclaw.api_url)
        },
        "hermes": {
            "api_url": config.hermes.api_url,
            "model": config.hermes.model,
            "configured": bool(config.hermes.api_url)
        },
        "local": {
            "enabled": config.local.enable
        }
    }
