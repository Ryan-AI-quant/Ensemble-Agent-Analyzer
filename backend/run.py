#!/usr/bin/env python3
"""
Agent新闻系统 - 启动脚本
"""

import os
import sys
import uvicorn
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 配置
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 8000))
RELOAD = os.getenv("RELOAD", "true").lower() == "true"
LOG_LEVEL = os.getenv("LOG_LEVEL", "info")


def main():
    """启动服务器"""
    print("=" * 60)
    print("🤖 Agent News System - Backend Server")
    print("=" * 60)
    print(f"📡 Server: http://{HOST}:{PORT}")
    print(f"📚 API Docs: http://{HOST}:{PORT}/docs")
    print(f"🔧 Log Level: {LOG_LEVEL}")
    print("=" * 60)

    uvicorn.run(
        "app.main:app",
        host=HOST,
        port=PORT,
        reload=RELOAD,
        log_level=LOG_LEVEL,
        access_log=True
    )


if __name__ == "__main__":
    main()
