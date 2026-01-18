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
    paused = False  # 标记是否进入暂停状态

    # 保存消息到数据库的辅助函数
    def save_message_to_db():
        try:
            # 构造消息数据 - 取最后一个 message（包含最终答案或表单）
            msg_data = None
            content_to_save = full_response_content

            # 从后往前找最后一个 message
            for event in reversed(response_events):
                if event.get("type") == "message":
                    msg_data = event.get("data", {}).get("message")
                    # 安全地获取 agent_name
                    agent_name = 'Unknown'
                    if msg_data:
                        if hasattr(msg_data, 'agent_name'):
                            agent_name = msg_data.agent_name
                        elif isinstance(msg_data, dict) and 'agent_name' in msg_data:
                            agent_name = msg_data['agent_name']
                    logger.info(f"找到 message 事件，agent: {agent_name}")
                    break

            if not msg_data:
                for event in response_events:
                    if event.get("type") == "message":
                        msg_data = event.get("data", {}).get("message")
                        break

            # 如果暂停了，检查是否需要调整
            if paused and msg_data:
                # msg_data 是 Message 对象，提取 data 字段
                if hasattr(msg_data, 'data') and msg_data.data:
                    if hasattr(msg_data.data, 'form_config'):
                        # 有表单配置，保存表单配置到 data，清空 content
                        msg_data = msg_data.data
                        content_to_save = ''
                    elif hasattr(msg_data, 'model_dump'):
                        # 使用 model_dump() 转换为字典
                        msg_dict = msg_data.model_dump()
                        if msg_dict.get('data', {}).get('form_config'):
                            msg_data = msg_dict['data']
                            content_to_save = ''
                        else:
                            content_to_save = ''

            logger.info(f"保存消息到数据库 - events数量: {len(collected_events) if collected_events else 0}")
            for evt in (collected_events or []):
                logger.info(f"  保存事件: {evt.get('type')} - {evt.get('data', {}).get('agent_name', 'unknown')}")

            db.add_message(
                conversation_id=conv['id'],
                role='assistant',
                content=content_to_save,
                data=msg_data,
                events=collected_events if collected_events else None
            )
        except Exception as save_error:
            logger.error(f"保存流式消息失败: {save_error}")

    async def generate():
        """生成SSE事件流"""
        nonlocal full_response_content, response_events, collected_events, paused
        try:
            # 首先发送 session_id（如果前端还没有）
            yield f"data: {json.dumps({'type': 'metadata', 'data': {'session_id': session_id}}, ensure_ascii=False)}\n\n"

            # 流式调用AgentManager，传递session_id和context_manager
            for event in agent_manager(
                request.query,
                stream=True,
                session_id=session_id,
                context_manager=context_manager
            ):
                # 收集事件用于保存
                response_events.append(event)

                # 处理暂停事件
                if event.get("type") == "pause":
                    logger.info(f"收到暂停事件，保存上下文到数据库")
                    # 保存暂停上下文到数据库
                    pause_data = event.get("data", {})
                    db.save_paused_context(session_id, pause_data)
                    paused = True

                    # 保存消息到数据库（暂停时也要保存）
                    save_message_to_db()

                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                    # 暂停时不发送 [DONE]，直接返回
                    return

                # 收集agent_start和agent_end事件
                if event.get("type") in ["agent_start", "agent_end"]:
                    collected_events.append(event)
                    logger.info(f"收集事件: {event.get('type')} - {event.get('data', {}).get('agent_name', 'unknown')}")

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

            # 保存助手消息（正常完成时）
            save_message_to_db()

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


@app.post("/chat/stream/resume", tags=["聊天"])
async def chat_stream_resume(request: ChatRequest):
    """
    恢复流式聊天接口（SSE）

    从暂停点继续执行agent链，并以Server-Sent Events (SSE)格式流式返回响应

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

    # 验证session_id
    if not request.session_id:
        raise HTTPException(status_code=400, detail="必须提供session_id")

    session_id = request.session_id

    # 检查是否有暂停的上下文
    paused_context = db.get_paused_context(session_id)
    if not paused_context:
        raise HTTPException(status_code=404, detail="未找到暂停的上下文")

    logger.info(f"恢复会话 {session_id} 的执行")

    # 用于收集流式响应内容
    full_response_content = ""
    response_events = []
    collected_events = []
    paused = False
    last_message_id = None  # 保存最后一条消息的ID，用于更新
    conv = db.get_conversation_by_session(session_id)  # 提前获取 conv

    # 保存消息到数据库的辅助函数
    def save_resume_message_to_db():
        nonlocal last_message_id
        try:
            if not conv:
                logger.error("无法获取 conversation")
                return

            logger.info(f"准备保存/更新消息，conversation_id: {conv['id']}")

            # 在同一个数据库连接中查询和更新
            import sqlite3
            with sqlite3.connect(db.db_path) as conn:
                conn.row_factory = sqlite3.Row

                # 先查询该 conversation 有多少条消息
                count_cursor = conn.execute(
                    "SELECT COUNT(*) as count FROM messages WHERE conversation_id = ?",
                    (conv['id'],)
                )
                count_result = count_cursor.fetchone()
                msg_count = count_result['count'] if count_result else 0
                logger.info(f"当前 conversation 中有 {msg_count} 条消息")

                # 查询最后一条助手消息（不是用户消息）
                cursor = conn.execute(
                    "SELECT id, events, role FROM messages WHERE conversation_id = ? AND role = ? ORDER BY created_at DESC LIMIT 1",
                    (conv['id'], 'assistant')
                )
                last_msg = cursor.fetchone()

                if last_msg:
                    last_message_id = last_msg['id']
                    logger.info(f"找到最后一条消息 ID: {last_message_id}, role: {last_msg['role']}")
                else:
                    logger.warning("未找到任何消息")

            # 构造消息数据 - 取最后一个 message（包含最终答案）
            msg_data = None
            for event in reversed(response_events):
                if event.get("type") == "message":
                    msg_data = event.get("data", {}).get("message")
                    # 安全地获取 agent_name
                    agent_name = 'Unknown'
                    if msg_data:
                        if hasattr(msg_data, 'agent_name'):
                            agent_name = msg_data.agent_name
                        elif isinstance(msg_data, dict) and 'agent_name' in msg_data:
                            agent_name = msg_data['agent_name']
                    logger.info(f"找到 message 事件，agent: {agent_name}")
                    # 找到最后一个就停止
                    break

            # 如果没找到，尝试按顺序找
            if not msg_data:
                for event in response_events:
                    if event.get("type") == "message":
                        msg_data = event.get("data", {}).get("message")
                        logger.info(f"按顺序找到 message 事件")
                        break

            logger.info(f"提取到 msg_data: {type(msg_data)}")

            # 合并 events：之前暂停时保存的 events + 当前恢复执行的 events
            all_events = []
            if last_msg and last_msg['events']:
                try:
                    previous_events = json.loads(last_msg['events'])
                    all_events.extend(previous_events)
                    logger.info(f"合并之前的 events，数量: {len(previous_events)}")
                except Exception as e:
                    logger.error(f"解析之前的 events 失败: {e}")
            if collected_events:
                all_events.extend(collected_events)
                logger.info(f"添加当前的 events，数量: {len(collected_events)}")

            logger.info(f"总共 events 数量: {len(all_events)}")

            # 如果有最后一条消息的ID，更新它；否则插入新消息
            if last_message_id:
                # 在同一个连接中更新
                with sqlite3.connect(db.db_path) as conn:
                    # 构造更新的 SQL 和参数
                    update_sql = """
                        UPDATE messages
                        SET content = ?, data = ?, events = ?
                        WHERE id = ?
                    """

                    # 序列化 data
                    data_json = None
                    if msg_data:
                        if hasattr(msg_data, 'model_dump'):
                            data_json = json.dumps(msg_data.model_dump(), ensure_ascii=False)
                        else:
                            data_json = json.dumps(msg_data, ensure_ascii=False)

                    # 序列化 events
                    events_json = json.dumps(all_events, ensure_ascii=False) if all_events else None

                    logger.info(f"准备更新消息 {last_message_id}")
                    logger.info(f"  content 长度: {len(full_response_content)}")
                    logger.info(f"  data_json: {bool(data_json)}")
                    logger.info(f"  events_json: {len(all_events)} 个 events")

                    conn.execute(update_sql, (full_response_content, data_json, events_json, last_message_id))
                    conn.commit()
                    logger.info(f"✓ 成功更新消息 ID: {last_message_id}")
            else:
                # 插入新消息
                logger.info("未找到要更新的消息，插入新消息")
                db.add_message(
                    conversation_id=conv['id'],
                    role='assistant',
                    content=full_response_content,
                    data=msg_data,
                    events=all_events if all_events else None
                )
                logger.info("✓ 插入新消息完成")
        except Exception as save_error:
            logger.error(f"保存恢复后的消息失败: {save_error}")
            import traceback
            logger.error(traceback.format_exc())

    async def generate():
        """生成SSE事件流"""
        nonlocal full_response_content, response_events, collected_events, paused
        try:
            # 流式调用AgentManager的恢复执行方法
            for event in agent_manager(
                request.query,  # 这里是用户提交的表单数据
                stream=True,
                session_id=session_id,
                context_manager=context_manager,
                resume_data=paused_context  # 传入暂停的上下文
            ):
                # 收集事件用于保存
                response_events.append(event)

                # 处理暂停事件
                if event.get("type") == "pause":
                    logger.info(f"再次收到暂停事件，更新上下文到数据库")
                    pause_data = event.get("data", {})
                    db.save_paused_context(session_id, pause_data)
                    paused = True

                    # 保存消息到数据库（暂停时也要保存）
                    save_resume_message_to_db()

                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                    return

                # 收集agent_start和agent_end事件
                if event.get("type") in ["agent_start", "agent_end"]:
                    collected_events.append(event)
                    logger.info(f"收集事件: {event.get('type')} - {event.get('data', {}).get('agent_name', 'unknown')}")

                # 收集delta内容
                if event.get("type") == "delta":
                    full_response_content += event.get("data", {}).get("content", "")

                # 转换为SSE格式
                sse_data = f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

                # 立即yield，确保数据立即发送
                yield sse_data

                # 强制flush
                await asyncio.sleep(0)

            # 发送完成标记
            if not paused:
                yield "data: [DONE]\n\n"

            # 保存助手消息（正常完成时）
            save_resume_message_to_db()

            # 清除暂停上下文（只有在正常完成时）
            if not paused:
                db.clear_paused_context(session_id)

        except Exception as e:
            logger.error(f"恢复流式聊天处理失败: {e}")
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
            "X-Accel-Buffering": "no"
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
