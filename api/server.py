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

from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Query
from fastapi.responses import StreamingResponse, JSONResponse, HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from typing import Optional

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import AgentManager
from core.context_manager import context_manager
from core.file_service import get_file_service
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
    ConversationResponse,
    FileInfo,
    FileUploadResponse,
    FileListResponse,
    FileDeleteResponse
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
# 前端静态文件服务
# ============================================================================

# 获取前端构建目录
frontend_dist = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "web",
    "dist"
)

# 挂载静态文件
if os.path.exists(frontend_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")
    logger.info(f"✓ 前端静态文件已挂载: {frontend_dist}")
else:
    logger.warning(f"⚠️  前端构建目录不存在: {frontend_dist}")
    logger.warning("请先运行: cd web && npm run build")


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


@app.post("/agents/reload", tags=["Agent"])
async def reload_agents():
    """
    重新加载所有插件Agent（支持热插拔）

    无需重启服务即可加载新添加的Agent或移除已删除的Agent。
    这个操作会：
    1. 保留所有内置Agent（entrance_agent, general_agent, demand_agent）
    2. 保留所有MCP Agent
    3. 重新扫描plugin目录并加载所有Agent文件

    Returns:
        重载结果，包括加载的Agent数量和列表
    """
    if agent_manager is None:
        raise HTTPException(status_code=503, detail="服务未初始化")

    try:
        # 调用pluginManager的reload_plugins方法
        plugin_count = agent_manager.agents.reload_plugins()

        # 获取更新后的Agent列表
        agents_info = json.loads(agent_manager.agents.to_string())
        available_agents = agents_info.get('available_agents', {})

        # 提取插件Agent名称（排除内置和MCP Agent）
        builtin_agents = {'entrance_agent', 'general_agent', 'demand_agent'}
        plugin_agent_names = [
            name for name in available_agents.keys()
            if name not in builtin_agents and not name.startswith('mcp_')
        ]

        return {
            "status": "success",
            "message": f"成功重新加载 {plugin_count} 个插件Agent",
            "plugin_count": plugin_count,
            "plugin_agents": plugin_agent_names,
            "total_agents": len(available_agents)
        }
    except Exception as e:
        logger.error(f"重载插件失败: {e}")
        raise HTTPException(status_code=500, detail=f"重载插件失败: {str(e)}")


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

    # 如果请求中包含LLM参数，设置到agent_manager
    if any([request.temperature is not None, request.top_p is not None, request.top_k is not None]):
        agent_manager.set_llm_params(
            temperature=request.temperature,
            top_p=request.top_p,
            top_k=request.top_k
        )

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

            # 生成并更新会话标题（仅在正常完成时，且标题未生成过）
            if not paused and full_response_content.strip():
                try:
                    # 检查会话是否已有正式标题
                    conv = db.get_conversation_by_session(session_id)
                    current_title = conv.get('title', '') if conv else ''

                    # 判断是否需要生成新标题：
                    # 1. 标题为空
                    # 2. 标题以"..."结尾（临时标题，截断的消息）
                    # 3. 标题为"新对话"（默认标题）
                    needs_title = (
                        not current_title or
                        current_title.endswith('...') or
                        current_title == '新对话'
                    )

                    if needs_title:
                        logger.info("正在生成会话标题...")
                        # 调用agent_manager生成标题
                        new_title = agent_manager.generate_title(
                            query=request.query,
                            response=full_response_content
                        )

                        # 如果标题为空，使用默认标题
                        if not new_title or not new_title.strip():
                            new_title = "新对话"
                            logger.info("生成的标题为空，使用默认标题: 新对话")

                        # 更新数据库中的会话标题
                        if db.update_conversation_title(session_id, new_title):
                            logger.info(f"✓ 会话标题已更新: {new_title}")

                            # 发送标题更新事件给前端
                            title_update_event = {
                                "type": "metadata",
                                "data": {
                                    "title_updated": True,
                                    "new_title": new_title,
                                    "session_id": session_id
                                },
                                "metadata": {}
                            }
                            yield f"data: {json.dumps(title_update_event, ensure_ascii=False)}\n\n"
                        else:
                            logger.warning("更新会话标题失败")
                            # 即使更新失败，也发送事件让前端使用默认标题
                            title_update_event = {
                                "type": "metadata",
                                "data": {
                                    "title_updated": True,
                                    "new_title": "新对话",
                                    "session_id": session_id
                                },
                                "metadata": {}
                            }
                            yield f"data: {json.dumps(title_update_event, ensure_ascii=False)}\n\n"
                    else:
                        logger.debug(f"会话已有正式标题，跳过生成: {current_title}")
                except Exception as title_error:
                    logger.error(f"生成标题时出错: {title_error}")
                    # 标题生成失败时，也发送事件让前端使用默认标题
                    title_update_event = {
                        "type": "metadata",
                        "data": {
                            "title_updated": True,
                            "new_title": "新对话",
                            "session_id": session_id
                        },
                        "metadata": {}
                    }
                    yield f"data: {json.dumps(title_update_event, ensure_ascii=False)}\n\n"

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

    # 如果请求中包含LLM参数，设置到agent_manager
    if any([request.temperature is not None, request.top_p is not None, request.top_k is not None]):
        agent_manager.set_llm_params(
            temperature=request.temperature,
            top_p=request.top_p,
            top_k=request.top_k
        )

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

            # 生成并更新会话标题（仅在正常完成时，且标题未生成过）
            if not paused and full_response_content.strip():
                try:
                    # 检查会话是否已有正式标题
                    conv = db.get_conversation_by_session(session_id)
                    current_title = conv.get('title', '') if conv else ''

                    # 判断是否需要生成新标题：
                    # 1. 标题为空
                    # 2. 标题以"..."结尾（临时标题，截断的消息）
                    # 3. 标题为"新对话"（默认标题）
                    needs_title = (
                        not current_title or
                        current_title.endswith('...') or
                        current_title == '新对话'
                    )

                    if needs_title:
                        logger.info("正在生成会话标题...")
                        # 从暂停的上下文中获取原始用户查询
                        original_query = "用户对话"
                        if paused_context and 'context' in paused_context:
                            # 查找原始用户消息（第一条role为user的消息）
                            for msg in paused_context['context']:
                                if isinstance(msg, dict) and msg.get('role') == 'user':
                                    original_query = msg.get('content', '用户对话')
                                    break

                        # 调用agent_manager生成标题
                        new_title = agent_manager.generate_title(
                            query=original_query,
                            response=full_response_content
                        )

                        # 如果标题为空，使用默认标题
                        if not new_title or not new_title.strip():
                            new_title = "新对话"
                            logger.info("生成的标题为空，使用默认标题: 新对话")

                        # 更新数据库中的会话标题
                        if db.update_conversation_title(session_id, new_title):
                            logger.info(f"✓ 会话标题已更新: {new_title}")

                            # 发送标题更新事件给前端
                            title_update_event = {
                                "type": "metadata",
                                "data": {
                                    "title_updated": True,
                                    "new_title": new_title,
                                    "session_id": session_id
                                },
                                "metadata": {}
                            }
                            yield f"data: {json.dumps(title_update_event, ensure_ascii=False)}\n\n"
                        else:
                            logger.warning("更新会话标题失败")
                            # 即使更新失败，也发送事件让前端使用默认标题
                            title_update_event = {
                                "type": "metadata",
                                "data": {
                                    "title_updated": True,
                                    "new_title": "新对话",
                                    "session_id": session_id
                                },
                                "metadata": {}
                            }
                            yield f"data: {json.dumps(title_update_event, ensure_ascii=False)}\n\n"
                    else:
                        logger.debug(f"会话已有正式标题，跳过生成: {current_title}")
                except Exception as title_error:
                    logger.error(f"生成标题时出错: {title_error}")
                    # 标题生成失败时，也发送事件让前端使用默认标题
                    title_update_event = {
                        "type": "metadata",
                        "data": {
                            "title_updated": True,
                            "new_title": "新对话",
                            "session_id": session_id
                        },
                        "metadata": {}
                    }
                    yield f"data: {json.dumps(title_update_event, ensure_ascii=False)}\n\n"

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


@app.get("/conversations/{session_id}/export/pdf", tags=["历史记录"])
async def export_conversation_pdf(session_id: str):
    """
    导出会话为PDF文件

    返回PDF格式的对话记录
    """
    from fastapi.responses import Response

    db = get_db()
    pdf_bytes = db.export_conversation_to_pdf(session_id)

    if not pdf_bytes:
        raise HTTPException(status_code=404, detail="会话不存在")

    # 使用固定的简单文件名
    filename = "conversation.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


@app.delete("/conversations/{session_id}/messages/{message_id}", tags=["历史记录"])
async def delete_message(session_id: str, message_id: int):
    """
    删除指定消息

    通过消息ID删除单条消息
    """
    db = get_db()

    # 获取会话
    conv = db.get_conversation_by_session(session_id)
    if not conv:
        raise HTTPException(status_code=404, detail="会话不存在")

    # 删除消息
    success = db.delete_message(message_id, conv['id'])

    if not success:
        raise HTTPException(status_code=404, detail="消息不存在")

    return {"status": "success", "message": "消息删除成功"}


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
# 根路径和API信息
# ============================================================================

@app.get("/api/info", tags=["系统"])
async def api_info():
    """
    API服务信息

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
# 模型配置管理
# ============================================================================

@app.get("/api/config/model", tags=["配置"])
async def get_model_config():
    """
    获取当前模型配置（不返回API Key）
    """
    try:
        llm_config = config.get_llm_config()
        return {
            "base_url": llm_config.get("base_url", ""),
            "model_name": llm_config.get("model_name", "")
        }
    except Exception as e:
        logger.error(f"获取模型配置失败: {e}")
        raise HTTPException(status_code=500, detail="获取配置失败")


@app.get("/api/config/llm-params", tags=["配置"])
async def get_llm_params():
    """
    获取当前LLM参数配置
    直接从config读取，确保返回最新的配置文件内容
    """
    try:
        # 直接从config读取，而不是从agent_manager读取
        # 这样即使修改了.env文件（未重启服务），也能获取最新配置
        llm_config = config.get_llm_config()
        return {
            "temperature": llm_config.get("temperature", 0.7),
            "top_p": llm_config.get("top_p", 0.9),
            "top_k": llm_config.get("top_k", 40),
            "stream_chunk_size": llm_config.get("stream_chunk_size", 10)
        }
    except Exception as e:
        logger.error(f"获取LLM参数失败: {e}")
        raise HTTPException(status_code=500, detail="获取参数失败")


@app.post("/api/config/model", tags=["配置"])
async def update_model_config(request: Request):
    """
    更新模型配置并保存到.env文件
    """
    try:
        data = await request.json()

        base_url = data.get("base_url", "").strip()
        model_name = data.get("model_name", "").strip()
        api_key = data.get("api_key", "").strip()

        if not base_url or not model_name:
            raise HTTPException(
                status_code=400,
                detail="base_url和model_name不能为空"
            )

        # 读取.env文件
        env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")

        # 如果.env文件不存在，创建默认的.env文件
        if not os.path.exists(env_path):
            default_env_content = """# easyAgent 配置文件
# 自动生成的配置文件

# LLM服务配置
LLM_BASE_URL=http://127.0.0.1:9999/v1
LLM_API_KEY=your-api-key-here
LLM_MODEL_NAME=openai/gpt-oss-20b

# LLM参数配置
LLM_TEMPERATURE=1.0
LLM_TOP_P=1.0
LLM_TOP_K=40
LLM_STREAM_CHUNK_SIZE=10

# Agent配置
PLUGIN_DIR=plugin
START_AGENT_NAME=entrance_agent
END_AGENT_NAME=general_agent
MAX_RETRIES=3

# MCP配置
MCP_ENABLED=false

# 日志配置
LOG_LEVEL=INFO

# 应用配置
APP_NAME=easyAgent
APP_VERSION=0.1.1
DEBUG=false
"""
            with open(env_path, 'w', encoding='utf-8') as f:
                f.write(default_env_content)
            logger.info(f"已创建默认的.env文件: {env_path}")

        # 读取现有内容
        with open(env_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # 更新配置
        updated_lines = []
        config_updated = False

        for line in lines:
            line = line.strip()
            if line.startswith("LLM_BASE_URL="):
                updated_lines.append(f'LLM_BASE_URL="{base_url}"\n')
                config_updated = True
            elif line.startswith("LLM_MODEL_NAME="):
                updated_lines.append(f'LLM_MODEL_NAME="{model_name}"\n')
                config_updated = True
            elif line.startswith("LLM_API_KEY="):
                if api_key:  # 只有提供了新key才更新
                    updated_lines.append(f'LLM_API_KEY="{api_key}"\n')
                else:
                    updated_lines.append(line + '\n')
                config_updated = True
            else:
                updated_lines.append(line + '\n')

        # 如果配置不存在，添加到文件末尾
        if not config_updated:
            updated_lines.append(f'LLM_BASE_URL="{base_url}"\n')
            updated_lines.append(f'LLM_MODEL_NAME="{model_name}"\n')
            if api_key:
                updated_lines.append(f'LLM_API_KEY="{api_key}"\n')

        # 写回文件
        with open(env_path, 'w', encoding='utf-8') as f:
            f.writelines(updated_lines)

        logger.info(f"模型配置已更新: base_url={base_url}, model_name={model_name}")

        return {
            "status": "success",
            "message": "配置已保存，重启服务后生效"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新模型配置失败: {e}")
        raise HTTPException(status_code=500, detail="保存配置失败")


@app.post("/api/config/llm-params", tags=["配置"])
async def update_llm_params(request: Request):
    """
    更新LLM参数并保存到.env文件
    """
    try:
        data = await request.json()

        temperature = data.get("temperature")
        top_p = data.get("top_p")
        top_k = data.get("top_k")
        stream_chunk_size = data.get("stream_chunk_size")

        # 读取.env文件
        env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")

        # 如果.env文件不存在，创建默认的.env文件
        if not os.path.exists(env_path):
            default_env_content = """# easyAgent 配置文件
# 自动生成的配置文件

# LLM服务配置
LLM_BASE_URL=http://127.0.0.1:9999/v1
LLM_API_KEY=your-api-key-here
LLM_MODEL_NAME=openai/gpt-oss-20b

# LLM参数配置
LLM_TEMPERATURE=1.0
LLM_TOP_P=1.0
LLM_TOP_K=40
LLM_STREAM_CHUNK_SIZE=10

# Agent配置
PLUGIN_DIR=plugin
START_AGENT_NAME=entrance_agent
END_AGENT_NAME=general_agent
MAX_RETRIES=3

# MCP配置
MCP_ENABLED=false

# 日志配置
LOG_LEVEL=INFO

# 应用配置
APP_NAME=easyAgent
APP_VERSION=0.1.1
DEBUG=false
"""
            with open(env_path, 'w', encoding='utf-8') as f:
                f.write(default_env_content)
            logger.info(f"已创建默认的.env文件: {env_path}")

        # 读取现有内容
        with open(env_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # 更新配置
        updated_lines = []
        params_updated = set()

        for line in lines:
            original_line = line
            stripped_line = line.strip()

            # 更新 LLM_TEMPERATURE
            if temperature is not None and stripped_line.startswith("LLM_TEMPERATURE="):
                updated_lines.append(f'LLM_TEMPERATURE={temperature}\n')
                params_updated.add("temperature")
            # 更新 LLM_TOP_P
            elif top_p is not None and stripped_line.startswith("LLM_TOP_P="):
                updated_lines.append(f'LLM_TOP_P={top_p}\n')
                params_updated.add("top_p")
            # 更新 LLM_TOP_K
            elif top_k is not None and stripped_line.startswith("LLM_TOP_K="):
                updated_lines.append(f'LLM_TOP_K={top_k}\n')
                params_updated.add("top_k")
            # 更新 LLM_STREAM_CHUNK_SIZE
            elif stream_chunk_size is not None and stripped_line.startswith("LLM_STREAM_CHUNK_SIZE="):
                updated_lines.append(f'LLM_STREAM_CHUNK_SIZE={stream_chunk_size}\n')
                params_updated.add("stream_chunk_size")
            else:
                updated_lines.append(original_line)

        # 如果某个参数不存在且需要更新，添加到文件末尾
        if temperature is not None and "temperature" not in params_updated:
            updated_lines.append(f'LLM_TEMPERATURE={temperature}\n')
        if top_p is not None and "top_p" not in params_updated:
            updated_lines.append(f'LLM_TOP_P={top_p}\n')
        if top_k is not None and "top_k" not in params_updated:
            updated_lines.append(f'LLM_TOP_K={top_k}\n')
        if stream_chunk_size is not None and "stream_chunk_size" not in params_updated:
            updated_lines.append(f'LLM_STREAM_CHUNK_SIZE={stream_chunk_size}\n')

        # 写回文件
        with open(env_path, 'w', encoding='utf-8') as f:
            f.writelines(updated_lines)

        # 同时更新agent_manager的参数（立即生效）
        if agent_manager:
            agent_manager.set_llm_params(
                temperature=temperature,
                top_p=top_p,
                top_k=top_k
            )

        logger.info(f"LLM参数已更新: temperature={temperature}, top_p={top_p}, top_k={top_k}")

        return {
            "status": "success",
            "message": "LLM参数已保存"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新LLM参数失败: {e}")
        raise HTTPException(status_code=500, detail="保存参数失败")


# ============================================================================
# 文件管理接口
# ============================================================================

@app.post("/files/upload", response_model=FileUploadResponse, tags=["文件管理"])
async def upload_file(
    file: UploadFile = File(..., description="要上传的文件"),
    session_id: Optional[str] = Query(None, description="关联的会话ID")
):
    """
    上传文件

    支持上传各种类型的文件，包括PDF、Word、Excel、图片等。
    上传的文件会关联到指定的会话（可选）。
    """
    try:
        file_service = get_file_service()

        # 上传文件
        file_record = await file_service.upload_file(
            file=file,
            session_id=session_id
        )

        logger.info(
            f"文件上传成功: {file_record.original_filename} "
            f"({file_record.file_size} bytes) -> {file_record.file_id}"
        )

        return FileUploadResponse(
            status="success",
            message="文件上传成功",
            file=FileInfo(**file_record.to_dict())
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文件上传失败: {e}")
        raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}")


@app.get("/files/{file_id}", tags=["文件管理"])
async def download_file(file_id: str):
    """
    下载文件

    通过文件ID下载对应的文件
    """
    try:
        file_service = get_file_service()

        # 获取文件路径
        file_path = file_service.get_file_path(file_id)
        if not file_path:
            raise HTTPException(status_code=404, detail="文件不存在")

        # 获取文件记录
        file_record = file_service.get_file(file_id)
        if not file_record:
            raise HTTPException(status_code=404, detail="文件记录不存在")

        logger.info(f"文件下载: {file_record.original_filename} ({file_id})")

        # 返回文件
        return FileResponse(
            path=file_path,
            filename=file_record.original_filename,
            media_type=file_record.content_type
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文件下载失败: {e}")
        raise HTTPException(status_code=500, detail=f"文件下载失败: {str(e)}")


@app.get("/files", response_model=FileListResponse, tags=["文件管理"])
async def list_files(
    session_id: Optional[str] = Query(None, description="过滤指定会话的文件"),
    limit: int = Query(100, ge=1, le=1000, description="最大返回数量")
):
    """
    获取文件列表

    返回系统中已上传的文件列表，可按会话ID过滤
    """
    try:
        file_service = get_file_service()

        files = file_service.list_files(session_id=session_id, limit=limit)

        return FileListResponse(
            status="success",
            total=len(files),
            files=[FileInfo(**f.to_dict()) for f in files]
        )

    except Exception as e:
        logger.error(f"获取文件列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取文件列表失败: {str(e)}")


@app.get("/files/{file_id}/info", response_model=FileInfo, tags=["文件管理"])
async def get_file_info(file_id: str):
    """
    获取文件信息

    通过文件ID获取文件的详细信息
    """
    try:
        file_service = get_file_service()

        file_record = file_service.get_file(file_id)
        if not file_record:
            raise HTTPException(status_code=404, detail="文件不存在")

        return FileInfo(**file_record.to_dict())

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取文件信息失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取文件信息失败: {str(e)}")


@app.delete("/files/{file_id}", response_model=FileDeleteResponse, tags=["文件管理"])
async def delete_file(file_id: str):
    """
    删除文件

    通过文件ID删除文件及其记录
    """
    try:
        file_service = get_file_service()

        success = file_service.delete_file(file_id)
        if not success:
            raise HTTPException(status_code=404, detail="文件不存在")

        logger.info(f"文件删除成功: {file_id}")

        return FileDeleteResponse(
            status="success",
            message="文件删除成功"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文件删除失败: {e}")
        raise HTTPException(status_code=500, detail=f"文件删除失败: {str(e)}")


@app.delete("/files/session/{session_id}", tags=["文件管理"])
async def delete_session_files(session_id: str):
    """
    删除会话相关文件

    删除指定会话的所有文件
    """
    try:
        file_service = get_file_service()

        count = file_service.cleanup_session_files(session_id)

        logger.info(f"会话 {session_id} 的 {count} 个文件已删除")

        return {
            "status": "success",
            "message": f"已删除 {count} 个文件",
            "count": count
        }

    except Exception as e:
        logger.error(f"删除会话文件失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除会话文件失败: {str(e)}")


# ============================================================================
# SPA前端路由支持
# ============================================================================

@app.get("/", include_in_schema=False)
async def index():
    """根路径：返回前端主页"""
    index_path = os.path.join(frontend_dist, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    else:
        return HTMLResponse(
            content="<h1>前端未构建</h1><p>请先运行: <code>cd web && npm run build</code></p>",
            status_code=503
        )


@app.get("/bot.svg", include_in_schema=False)
async def favicon():
    """返回favicon图标"""
    bot_svg_path = os.path.join(frontend_dist, "bot.svg")
    if os.path.exists(bot_svg_path):
        return FileResponse(bot_svg_path, media_type="image/svg+xml")
    return FileResponse(os.path.join(frontend_dist, "vite.svg"), media_type="image/svg+xml")


@app.api_route("/{path:path}", methods=["GET", "HEAD"], include_in_schema=False)
async def catch_all(path: str):
    """
    Catch-all路由：返回前端index.html

    支持React Router等前端路由
    """
    # 排除API路由和文档路由
    if path.startswith("api") or path.startswith("docs") or path.startswith("redoc") or path.startswith("openapi.json"):
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=404,
            content={"detail": "Not Found"}
        )

    # 返回index.html（支持React Router）
    index_path = os.path.join(frontend_dist, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    else:
        return HTMLResponse(
            content="<h1>前端未构建</h1><p>请先运行: <code>cd web && npm run build</code></p>",
            status_code=503
        )


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
    print("  - 前端界面: http://localhost:8000")
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
