"""
聊天路由 - 处理与Agent的对话交互
支持多种后端：OpenClaw、Hermes、本地
"""

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from typing import List
import json
import asyncio

from ..models.schemas import ChatRequest, ChatResponse, ChatMessage
from ..services.openclaw_service import OpenClawService
from ..services.hermes_service import HermesService, get_hermes_service
from ..config import get_config, BackendType

router = APIRouter(prefix="/api/chat", tags=["chat"])

# 全局服务实例
openclaw_service = OpenClawService()


def get_chat_service():
    """根据配置获取合适的聊天服务"""
    config = get_config()
    
    if config.backend_type == BackendType.HERMES:
        # 获取Hermes服务实例（已使用正确配置）
        hermes_service = get_hermes_service()
        print(f"[ChatService] 使用 Hermes 服务")
        print(f"[ChatService]   API URL: {hermes_service.config.api_url}")
        print(f"[ChatService]   Model: {hermes_service.config.model}")
        print(f"[ChatService]   API Format: {hermes_service.config.api_format}")
        return hermes_service
    elif config.backend_type == BackendType.OPENCLAW:
        # 更新OpenClaw服务的配置
        openclaw_service.config.api_url = config.openclaw.api_url
        openclaw_service.config.api_key = config.openclaw.api_key
        openclaw_service.config.model = config.openclaw.model
        print(f"[ChatService] 使用 OpenClaw 服务")
        print(f"[ChatService]   API URL: {openclaw_service.config.api_url}")
        print(f"[ChatService]   Model: {openclaw_service.config.model}")
        return openclaw_service
    else:
        # 本地模式，使用OpenClaw服务的fallback机制
        print(f"[ChatService] 使用本地分析模式 (OpenClaw fallback)")
        return openclaw_service


@router.get("/status", summary="检查服务状态")
async def get_status():
    """获取聊天服务状态"""
    config = get_config()
    service = get_chat_service()
    
    if hasattr(service, 'get_connection_status'):
        return service.get_connection_status()
    else:
        return {
            "connected": True,
            "type": config.backend_type.value,
            "model": config.hermes.model if config.backend_type == BackendType.HERMES else config.openclaw.model
        }


@router.post("/message", response_model=ChatResponse, summary="发送消息")
async def send_message(request: ChatRequest):
    """发送聊天消息并获取响应"""
    try:
        config = get_config()
        service = get_chat_service()
        
        # 根据服务类型调用不同的方法
        if config.backend_type == BackendType.HERMES:
            # 使用Hermes服务
            response = await _handle_hermes_chat(request, service)
        else:
            # 使用OpenClaw服务（包含本地fallback）
            response = await service.send_message(request)
        
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"消息处理失败: {str(e)}")


async def _handle_hermes_chat(request: ChatRequest, hermes_svc: HermesService) -> ChatResponse:
    """处理Hermes聊天请求"""
    from datetime import datetime
    
    # 构建消息历史
    messages = [
        {"role": "system", "content": "你是一个智能助手，可以帮助用户回答问题、讨论新闻和技术话题。请用简洁、有条理的方式回答。"}
    ]
    
    # 添加上下文
    if request.context:
        for msg in request.context[-10:]:  # 保留最近10条
            messages.append({
                "role": "user" if msg.role.value == "user" else "assistant",
                "content": msg.content
            })
    
    # 添加当前消息
    messages.append({"role": "user", "content": request.message})
    
    # 调用Hermes API
    try:
        result = await hermes_svc.chat_openai_format(messages)
        
        # 提取响应内容
        content = ""
        if "choices" in result and len(result["choices"]) > 0:
            content = result["choices"][0]["message"]["content"]
        elif "response" in result:
            content = result["response"]
        else:
            content = str(result)
        
        # 创建响应
        assistant_message = ChatMessage(
            role="assistant",
            content=content,
            timestamp=datetime.now(),
            metadata={"model": hermes_svc.config.model}
        )
        
        # 生成建议回复
        suggestions = _generate_suggestions(content)
        
        return ChatResponse(
            message=assistant_message,
            session_id=request.session_id,
            suggestions=suggestions
        )
    except Exception as e:
        # 如果Hermes失败，返回错误信息
        error_msg = f"Hermes API调用失败: {str(e)}"
        print(error_msg)
        
        assistant_message = ChatMessage(
            role="assistant",
            content=f"抱歉，AI服务暂时不可用。请检查：\n1. Hermes服务是否正在运行\n2. API URL配置是否正确\n3. API Key是否有效\n\n错误详情：{str(e)}",
            timestamp=datetime.now(),
            metadata={"error": True}
        )
        
        return ChatResponse(
            message=assistant_message,
            session_id=request.session_id,
            suggestions=["重试", "查看帮助", "切换后端"]
        )


def _generate_suggestions(response: str) -> List[str]:
    """从响应中提取建议回复"""
    suggestions = []
    
    if "新闻" in response:
        suggestions.append("查看最新新闻")
    if "分析" in response:
        suggestions.append("深入分析这个话题")
    
    if not suggestions:
        suggestions = ["了解更多", "还有别的吗", "详细说说"]
    
    return suggestions[:3]


@router.post("/stream", summary="流式发送消息")
async def stream_message(request: ChatRequest):
    """流式发送聊天消息"""
    config = get_config()
    service = get_chat_service()
    
    async def generate():
        try:
            if config.backend_type == BackendType.HERMES:
                # Hermes流式响应
                messages = [
                    {"role": "system", "content": "你是一个智能助手。"}
                ]
                if request.context:
                    for msg in request.context[-10:]:
                        messages.append({
                            "role": "user" if msg.role.value == "user" else "assistant",
                            "content": msg.content
                        })
                messages.append({"role": "user", "content": request.message})
                
                async for chunk in service.stream_generate(
                    prompt=request.message,
                    system="你是一个智能助手，可以帮助用户回答问题、讨论新闻和技术话题。"
                ):
                    yield f"data: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"
            else:
                # OpenClaw流式响应
                async for chunk in service.stream_message(request):
                    yield f"data: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"
            
            yield f"data: {json.dumps({'done': True}, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

    from starlette.responses import StreamingResponse
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@router.get("/history/{session_id}", response_model=List[ChatMessage], summary="获取会话历史")
async def get_history(session_id: str):
    """获取指定会话的历史消息"""
    return openclaw_service.get_session_history(session_id)


@router.delete("/history/{session_id}", summary="清除会话历史")
async def clear_history(session_id: str):
    """清除指定会话的历史"""
    openclaw_service.clear_session(session_id)
    return {"message": "会话已清除"}


@router.websocket("/ws/{session_id}")
async def websocket_chat(websocket: WebSocket, session_id: str):
    """WebSocket聊天接口 - 支持多种后端"""
    await websocket.accept()
    
    config = get_config()
    service = get_chat_service()
    
    # 添加连接日志
    print(f"[WebSocket] 新连接建立: session_id={session_id}")
    print(f"[WebSocket] 当前后端类型: {config.backend_type.value}")
    print(f"[WebSocket] 使用的服务: {type(service).__name__}")

    try:
        while True:
            # 接收消息
            data = await websocket.receive_text()
            message_data = json.loads(data)

            request = ChatRequest(
                message=message_data.get("message", ""),
                session_id=session_id,
                context=message_data.get("context")
            )
            
            print(f"[WebSocket] 收到消息: {request.message[:50]}...")

            # 根据后端类型选择处理方式
            if config.backend_type == BackendType.HERMES:
                print(f"[WebSocket] 使用Hermes处理消息")
                # Hermes非流式响应（WebSocket中简化处理）
                try:
                    messages = [
                        {"role": "system", "content": "你是一个智能助手。"}
                    ]
                    if request.context:
                        for msg in request.context[-10:]:
                            messages.append({
                                "role": "user" if msg.role.value == "user" else "assistant",
                                "content": msg.content
                            })
                    messages.append({"role": "user", "content": request.message})
                    
                    print(f"[WebSocket] 调用Hermes API...")
                    result = await service.chat_openai_format(messages)
                    content = ""
                    if "choices" in result and len(result["choices"]) > 0:
                        content = result["choices"][0]["message"]["content"]
                        print(f"[WebSocket] Hermes响应成功，长度: {len(content)}")
                    
                    # 模拟流式发送
                    for i in range(0, len(content), 10):
                        chunk = content[i:i+10]
                        await websocket.send_text(json.dumps({
                            "type": "chunk",
                            "content": chunk
                        }, ensure_ascii=False))
                        await asyncio.sleep(0.05)
                    
                    response_text = content
                except Exception as e:
                    error_msg = f"Hermes API调用失败: {str(e)}"
                    print(f"[WebSocket] {error_msg}")
                    import traceback
                    traceback.print_exc()
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "error": error_msg
                    }, ensure_ascii=False))
                    continue
            else:
                print(f"[WebSocket] 使用OpenClaw/本地处理消息")
                # OpenClaw流式响应
                response_text = ""
                try:
                    async for chunk in service.stream_message(request):
                        await websocket.send_text(json.dumps({
                            "type": "chunk",
                            "content": chunk
                        }, ensure_ascii=False))
                        response_text += chunk
                    print(f"[WebSocket] OpenClaw响应成功，长度: {len(response_text)}")
                except Exception as e:
                    error_msg = f"OpenClaw API调用失败: {str(e)}"
                    print(f"[WebSocket] {error_msg}")
                    import traceback
                    traceback.print_exc()
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "error": error_msg
                    }, ensure_ascii=False))
                    continue

            # 发送完成信号
            await websocket.send_text(json.dumps({
                "type": "done",
                "content": response_text,
                "suggestions": ["查看新闻", "了解更多", "继续对话"]
            }, ensure_ascii=False))

    except WebSocketDisconnect:
        print(f"[WebSocket] 连接断开: session_id={session_id}")
    except Exception as e:
        error_msg = f"WebSocket处理异常: {str(e)}"
        print(f"[WebSocket] {error_msg}")
        import traceback
        traceback.print_exc()
        try:
            await websocket.send_text(json.dumps({
                "type": "error",
                "error": error_msg
            }, ensure_ascii=False))
        except:
            pass
