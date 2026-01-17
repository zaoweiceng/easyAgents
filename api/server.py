"""
easyAgent FastAPI服务器

提供HTTP API接口，支持同步和流式（SSE）两种模式
"""

import sys
import os
import json
import logging
import uuid
import asyncio
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import AgentManager
from core.context_manager import context_manager
from config import get_config
from api.database import get_db
from api.models import (
    ChatRequest,
    ChatResponse,
    AgentsListResponse,
    AgentInfo,
    HealthResponse,
    ErrorResponse,
    ConversationInfo,
    MessageDetail,
    ConversationDetail,
    CreateConversationRequest,
    UpdateConversationTitleRequest,
    ConversationsListResponse,
    ConversationResponse
)

# 配置日志
config = get_config()
logger = config.setup_logging()

# 全局AgentManager实例
agent_manager: AgentManager = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global agent_manager

    # 启动时初始化
    logger.info("=" * 70)
    logger.info("easyAgent API服务启动中...")
    logger.info("=" * 70)

    try:
        # 使用全局配置
        logger.info(f"配置加载成功: {config.settings.APP_NAME} v{config.settings.APP_VERSION}")

        # 初始化数据库服务
        db = get_db()
        logger.info("数据库服务初始化成功")

        # 设置数据库服务到context_manager
        context_manager.set_db_service(db)
        logger.info("上下文管理器已连接数据库")

        # 初始化AgentManager
        agent_manager = AgentManager(
            plugin_src=config.get_agent_config()['plugin_src'],
            base_url=config.get_llm_config()['base_url'],
            api_key=config.get_llm_config()['api_key'],
            model_name=config.get_llm_config()['model_name'],
            mcp_configs=config.get_mcp_configs()
        )

        logger.info("AgentManager初始化成功")

        # 显示已加载的Agent
        agents_info = json.loads(agent_manager.agents.to_string())
        active_agents = agents_info.get('available_agents', {})
        logger.info(f"已加载 {len(active_agents)} 个Agent:")
        for agent_name in active_agents.keys():
            agent = agent_manager.agents[agent_name]
            status = "✓ 活跃" if agent.is_active else "✗ 不活跃"
            logger.info(f"  - {agent_name}: {status}")

        logger.info("=" * 70)
        logger.info("✅ easyAgent API服务启动完成")
        logger.info("=" * 70)

        yield

    except Exception as e:
        logger.error(f"初始化失败: {e}")
        raise

    # 关闭时清理
    logger.info("easyAgent API服务关闭中...")
    logger.info("清理完成")


# 创建FastAPI应用
app = FastAPI(
    title="easyAgent API",
    description="easyAgent多Agent协作系统HTTP接口",
    version="0.2.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有源，开发环境
    allow_credentials=False,  # 不允许携带凭证
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# 健康检查接口
# ============================================================================

@app.get("/health", response_model=HealthResponse, tags=["系统"])
async def health_check():
    """
    健康检查接口

    检查服务是否正常运行
    """
    if agent_manager is None:
        raise HTTPException(status_code=503, detail="服务未初始化")

    agents_info = json.loads(agent_manager.agents.to_string())
    active_agents = agents_info.get('available_agents', {})

    return HealthResponse(
        status="ok",
        service="easyAgent API",
        version="0.2.0",
        agents_loaded=len(active_agents)
    )


# ============================================================================
# Agent管理接口
# ============================================================================

@app.get("/agents", response_model=AgentsListResponse, tags=["Agent"])
async def list_agents():
    """
    获取所有可用的Agent列表

    返回系统中所有已加载的Agent信息（不包括内置Agent）
    """
    if agent_manager is None:
        raise HTTPException(status_code=503, detail="服务未初始化")

    agents_info = json.loads(agent_manager.agents.to_string())
    available_agents = agents_info.get('available_agents', {})

    # 内置Agent列表，不对外显示
    builtin_agents = {'entrance_agent', 'general_agent'}

    agents = []
    for name, info in available_agents.items():
        # 跳过内置Agent
        if name in builtin_agents:
            continue

        agent = agent_manager.agents[name]
        agents.append(AgentInfo(
            name=agent.name,
            description=agent.description,
            handles=agent.handles,
            is_active=agent.is_active,
            version=agent.version
        ))

    return AgentsListResponse(
        status="success",
        count=len(agents),
        agents=agents
    )


@app.get("/agents/{agent_name}", tags=["Agent"])
async def get_agent_info(agent_name: str):
    """
    获取特定Agent的详细信息

    返回指定Agent的完整信息（不包括内置Agent）
    """
    if agent_manager is None:
        raise HTTPException(status_code=503, detail="服务未初始化")

    # 内置Agent列表，不对外显示
    builtin_agents = {'entrance_agent', 'general_agent'}

    # 检查是否是内置Agent
    if agent_name in builtin_agents:
        raise HTTPException(
            status_code=404,
            detail=f"Agent '{agent_name}' 不存在或不可访问"
        )

    # 使用下标访问，pluginManager实现了__getitem__方法
    try:
        agent = agent_manager.agents[agent_name]
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' 不存在")

    return {
        "status": "success",
        "agent": {
            "name": agent.name,
            "description": agent.description,
            "handles": agent.handles,
            "parameters": agent.parameters or {},
            "is_active": agent.is_active,
            "version": agent.version,
            "supports_streaming": getattr(agent, 'supports_streaming', False)
        }
    }


# ============================================================================
# 聊天接口
# ============================================================================

@app.post("/chat", response_model=ChatResponse, tags=["聊天"])
async def chat(request: ChatRequest):
    """
    同步聊天接口

    处理用户查询并返回完整响应（非流式）
    """
    if agent_manager is None:
        raise HTTPException(status_code=503, detail="服务未初始化")

    db = get_db()

    # 如果没有 session_id，创建新会话
    if not request.session_id:
        session_id = str(uuid.uuid4())
        # 使用第一条消息作为标题（前50字符）
        title = request.query[:50] + "..." if len(request.query) > 50 else request.query
        db.create_conversation(title, session_id)
    else:
        session_id = request.session_id

    # 保存用户消息
    conv = db.get_conversation_by_session(session_id)
    db.add_message(
        conversation_id=conv['id'],
        role='user',
        content=request.query
    )

    try:
        # 同步调用AgentManager，传递session_id和context_manager
        response = agent_manager(
            request.query,
            stream=False,
            session_id=session_id,
            context_manager=context_manager
        )

        # 保存助手消息
        for msg in response:
            db.add_message(
                conversation_id=conv['id'],
                role=msg.role,
                content=msg.content or msg.message or '',
                data=msg.data if hasattr(msg, 'data') else None
            )

        return ChatResponse(
            status="success",
            response=response,
            session_id=session_id
        )

    except Exception as e:
        logger.error(f"聊天处理失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat/stream", tags=["聊天"])
async def chat_stream(request: ChatRequest):
    """
    流式聊天接口（SSE）

    处理用户查询并以Server-Sent Events (SSE)格式流式返回响应

    事件类型：
    - metadata: 元数据信息
    - agent_start: Agent开始处理
    - delta: LLM增量内容
    - agent_end: Agent结束处理
    - message: 完整Message对象
    - error: 错误信息
    """
    if agent_manager is None:
        raise HTTPException(status_code=503, detail="服务未初始化")

    db = get_db()

    # 如果没有 session_id，创建新会话
    if not request.session_id:
        session_id = str(uuid.uuid4())
        # 使用第一条消息作为标题（前50字符）
        title = request.query[:50] + "..." if len(request.query) > 50 else request.query
        db.create_conversation(title, session_id)
    else:
        session_id = request.session_id

    # 保存用户消息
    conv = db.get_conversation_by_session(session_id)
    db.add_message(
        conversation_id=conv['id'],
        role='user',
        content=request.query
    )

    # 用于收集流式响应内容
    full_response_content = ""
    response_events = []
    collected_events = []  # 收集所有事件用于保存到数据库

    async def generate():
        """生成SSE事件流"""
        nonlocal full_response_content, response_events, collected_events
        try:
            # 流式调用AgentManager，传递session_id和context_manager
            for event in agent_manager(
                request.query,
                stream=True,
                session_id=session_id,
                context_manager=context_manager
            ):
                # 收集事件用于保存
                response_events.append(event)

                # 收集agent_start和agent_end事件
                if event.get("type") in ["agent_start", "agent_end"]:
                    collected_events.append(event)

                # 收集delta内容
                if event.get("type") == "delta":
                    full_response_content += event.get("data", {}).get("content", "")

                # 转换为SSE格式
                sse_data = f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

                # 立即yield，确保数据立即发送
                yield sse_data

                # 强制flush（在async生成器中，yield会自动触发flush）
                # 但我们可以通过异步await来确保事件循环切换
                await asyncio.sleep(0)  # 让出控制权，确保数据发送

            # 发送完成标记
            yield "data: [DONE]\n\n"

            # 保存助手消息（在流结束后）
            try:
                # 构造消息数据
                msg_data = None
                for event in response_events:
                    if event.get("type") == "message":
                        msg_data = event.get("data", {}).get("message")
                        break

                db.add_message(
                    conversation_id=conv['id'],
                    role='assistant',
                    content=full_response_content,
                    data=msg_data,
                    events=collected_events if collected_events else None
                )
            except Exception as save_error:
                logger.error(f"保存流式消息失败: {save_error}")

        except Exception as e:
            logger.error(f"流式聊天处理失败: {e}")
            # 发送错误事件
            error_event = {
                "type": "error",
                "data": {
                    "error_message": str(e),
                    "error_type": type(e).__name__
                },
                "metadata": {}
            }
            yield f"data: {json.dumps(error_event, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # 禁用nginx缓冲
        }
    )


# ============================================================================
# 历史记录接口
# ============================================================================

@app.post("/conversations", response_model=ConversationResponse, tags=["历史记录"])
async def create_conversation(request: CreateConversationRequest):
    """
    创建新会话
    """
    db = get_db()
    session_id = str(uuid.uuid4())

    conv_id = db.create_conversation(
        title=request.title,
        session_id=session_id,
        model_name=request.model_name
    )

    conv = db.get_conversation_by_session(session_id)

    return ConversationResponse(
        status="success",
        data=ConversationDetail(
            conversation=conv,
            messages=[]
        )
    )


@app.get("/conversations", response_model=ConversationsListResponse, tags=["历史记录"])
async def list_conversations(limit: int = 50, offset: int = 0):
    """
    获取会话列表

    按更新时间降序排列
    """
    db = get_db()
    conversations = db.list_conversations(limit=limit, offset=offset)

    return ConversationsListResponse(
        status="success",
        conversations=conversations,
        total=len(conversations)
    )


@app.get("/conversations/{session_id}", response_model=ConversationResponse, tags=["历史记录"])
async def get_conversation(session_id: str):
    """
    获取会话详情（包括所有消息）
    """
    db = get_db()
    conv = db.get_conversation_by_session(session_id)

    if not conv:
        raise HTTPException(status_code=404, detail="会话不存在")

    messages = db.get_messages(conv['id'])

    return ConversationResponse(
        status="success",
        data=ConversationDetail(
            conversation=conv,
            messages=messages
        )
    )


@app.put("/conversations/{session_id}/title", tags=["历史记录"])
async def update_conversation_title(
    session_id: str,
    request: UpdateConversationTitleRequest
):
    """
    更新会话标题
    """
    db = get_db()
    success = db.update_conversation_title(session_id, request.title)

    if not success:
        raise HTTPException(status_code=404, detail="会话不存在")

    return {"status": "success", "message": "标题更新成功"}


@app.delete("/conversations/{session_id}", tags=["历史记录"])
async def delete_conversation(session_id: str):
    """
    删除会话（包括所有消息）
    """
    db = get_db()
    success = db.delete_conversation(session_id)

    if not success:
        raise HTTPException(status_code=404, detail="会话不存在")

    return {"status": "success", "message": "会话删除成功"}


@app.get("/conversations/search/{query}", tags=["历史记录"])
async def search_conversations(query: str, limit: int = 20):
    """
    搜索会话

    搜索标题和消息内容
    """
    db = get_db()
    conversations = db.search_conversations(query, limit)

    return ConversationsListResponse(
        status="success",
        conversations=conversations,
        total=len(conversations)
    )


@app.get("/conversations/{session_id}/export", tags=["历史记录"])
async def export_conversation(session_id: str):
    """
    导出会话（JSON格式）
    """
    db = get_db()
    data = db.export_conversation(session_id)

    if not data:
        raise HTTPException(status_code=404, detail="会话不存在")

    return data


# ============================================================================
# 错误处理
# ============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """HTTP异常处理"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail.__class__.__name__,
            "message": str(exc.detail),
            "detail": None
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """通用异常处理"""
    logger.error(f"未捕获的异常: {exc}", exc_info=True)

    return JSONResponse(
        status_code=500,
        content={
            "error": "InternalServerError",
            "message": "服务器内部错误",
            "detail": str(exc) if logger.isEnabledFor(logging.DEBUG) else None
        }
    )


# ============================================================================
# 根路径
# ============================================================================

@app.get("/", tags=["系统"])
async def root():
    """
    根路径

    返回API服务的基本信息
    """
    return {
        "service": "easyAgent API",
        "version": "0.2.0",
        "status": "running",
        "docs": "/docs",
        "health": "/health",
        "endpoints": {
            "聊天": {
                "同步": "/chat",
                "流式": "/chat/stream"
            },
            "Agent": {
                "列表": "/agents",
                "详情": "/agents/{name}"
            },
            "系统": {
                "健康检查": "/health",
                "文档": "/docs"
            }
        }
    }


# ============================================================================
# 启动服务器
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    print("=" * 70)
    print("easyAgent FastAPI服务器")
    print("=" * 70)
    print("\n启动服务器...")
    print("\n访问地址:")
    print("  - API文档: http://localhost:8000/docs")
    print("  - API文档(ReDoc): http://localhost:8000/redoc")
    print("  - 健康检查: http://localhost:8000/health")
    print("\n按 Ctrl+C 停止服务器\n")
    print("=" * 70)

    uvicorn.run(
        "api.server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # 开发模式，代码改动自动重载
        log_level="info"
    )
