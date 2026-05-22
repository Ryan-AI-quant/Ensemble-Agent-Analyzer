"""
FastAPI 主应用 - Agent新闻系统后端
混合架构: OpenClaw后端 + 自研前端
"""

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import os

# 加载环境变量（确保在任何配置读取之前执行）
load_dotenv()

from .routes import chat_router, news_router, mindmap_router
from .models.schemas import HealthCheck


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    print("🚀 Agent News System Backend Starting...")

    # 检查OpenClaw连接
    from .services.openclaw_service import OpenClawService
    openclaw_service = OpenClawService()
    connected = await openclaw_service.check_connection()
    print(f"📡 OpenClaw Connection: {'✅ Connected' if connected else '⚠️ Not Connected (using fallback)'}")

    # 检查Hermes连接 - 使用全局配置的服务实例
    from .services.hermes_service import get_hermes_service
    hermes_service = get_hermes_service()
    connected = await hermes_service.check_connection()
    print(f"📡 Hermes Connection: {'✅ Connected' if connected else '⚠️ Not Connected (using fallback)'}")

    yield

    # 关闭时执行
    print("👋 Agent News System Backend Shutting Down...")


# 创建FastAPI应用
app = FastAPI(
    title="Agent News System API",
    description="""
## Agent新闻系统 - 混合架构后端

### 核心功能

- **🤖 AI对话**: 与OpenClaw Agent进行自然语言交互
- **📰 新闻聚合**: 从多个来源获取新闻并按重要性排序
- **🧠 思维导图**: 从新闻内容自动生成思维导图

### 技术架构

- **后端**: Python FastAPI
- **Agent引擎**: OpenClaw (可配置)
- **前端通信**: REST API + WebSocket

### 使用说明

1. 对话: POST `/api/chat/message`
2. 新闻: GET `/api/news/`
3. 思维导图: GET `/api/mindmap/from-news/{news_id}`
    """,
    version="1.0.0",
    lifespan=lifespan
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(chat_router)
app.include_router(news_router)
app.include_router(mindmap_router)

# 挂载静态文件目录（前端dist）
static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")


@app.get("/", tags=["root"])
async def root():
    """根路径 - 返回欢迎信息"""
    return {
        "message": "🤖 Agent News System API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health", response_model=HealthCheck, tags=["system"])
async def health_check():
    """健康检查"""
    from .services.openclaw_service import OpenClawService
    from .services.hermes_service import get_hermes_service

    openclaw_service = OpenClawService()
    hermes_service = get_hermes_service()

    openclaw_connected = await openclaw_service.check_connection()
    hermes_connected = await hermes_service.check_connection()

    return HealthCheck(
        status="healthy" if openclaw_connected or hermes_connected else "degraded",
        version="1.0.0",
        openclaw_connected=openclaw_connected,
        hermes_connected=hermes_connected,
        services={
            "api": True,
            "news": True,
            "mindmap": True,
            "openclaw": openclaw_connected,
            "hermes": hermes_connected,
        }
    )


@app.get("/api/info", tags=["system"])
async def get_api_info():
    """获取API信息"""
    return {
        "name": "Agent News System",
        "version": "1.0.0",
        "description": "混合架构AI Agent + 新闻聚合 + 思维导图系统",
        "features": [
            "AI对话交互 (基于OpenClaw)",
            "多源新闻聚合",
            "智能重要性排序",
            "自动思维导图生成",
            "WebSocket实时通信"
        ],
        "endpoints": {
            "chat": "/api/chat",
            "news": "/api/news",
            "mindmap": "/api/mindmap"
        }
    }
