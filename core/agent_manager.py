from . import Message
from .constants import start_agent_name, end_agent_name, app_name
from .plugin_manager import pluginManager
from .agent import normalize_agent_output
import openai
import json
import logging
from typing import Generator, Dict, Any, Union, List
from datetime import datetime
import time

logger = logging.getLogger(app_name)
logger.setLevel(logging.INFO)  # 改为INFO级别以查看流式日志


class AgentManager:
    def __init__(self, plugin_src: str,
                 base_url: str,
                 api_key: str,
                 model_name: str,
                 mcp_configs: list = None
                 ):
        """
        初始化Agent管理器

        Args:
            plugin_src: 插件目录路径
            base_url: LLM服务地址
            api_key: LLM API密钥
            model_name: 模型名称
            mcp_configs: MCP服务器配置列表（可选）
        """
        self.plugin_src = plugin_src
        self.mcp_configs = mcp_configs
        self.agents = pluginManager(src=self.plugin_src, mcp_configs=mcp_configs)
        self.llm = openai.OpenAI(
            base_url=base_url,
            api_key=api_key
        )
        self.model_name = model_name
        self.start_agent = start_agent_name
        self.end_agent = end_agent_name
        self.max_trys = 3

    def __call__(self, query: str, stream: bool = False, session_id: str = None, context_manager=None, resume_data: Dict = None) -> Union[list, Generator[Dict[str, Any], None, None]]:
        """
        处理用户查询

        Args:
            query: 用户查询文本
            stream: 是否启用流式响应（默认False）
            session_id: 会话ID（用于获取历史上下文）
            context_manager: 上下文管理器（可选）
            resume_data: 恢复执行的数据（可选），包含暂停的上下文信息

        Returns:
            stream=False: 返回list（原有行为）
            stream=True: 返回Generator[Dict]，yield流式事件
        """
        # 如果提供了 resume_data，从暂停点恢复执行
        if resume_data:
            if stream:
                return self._stream_call_resume(query, resume_data, session_id, context_manager)
            else:
                return self._sync_call_resume(query, resume_data, session_id, context_manager)

        # 获取历史上下文
        history_context = []
        if session_id and context_manager:
            ctx = context_manager.get_or_create_context(session_id)
            history_context = ctx.get_context_for_llm()

        if stream:
            return self._stream_call(query, history_context, session_id, context_manager)
        else:
            return self._sync_call(query, history_context, session_id, context_manager)

    def _sync_call(self, query: str, history_context: List[Dict] = None, session_id: str = None, context_manager=None) -> list:
        """
        同步调用逻辑

        Args:
            query: 用户查询
            history_context: 历史上下文（简化版）
            session_id: 会话ID
            context_manager: 上下文管理器
        """
        agent_name = self.start_agent
        res = None
        max_trys = self.max_trys

        # 保存原始用户查询（用于后续保存到上下文管理器）
        original_query = query

        # 构建初始context：历史上下文 + 当前用户消息
        context = []

        # 添加历史上下文
        if history_context:
            context.extend(history_context)

        # 添加当前用户消息
        context.append(self.__user_message(query))

        # 用于收集完整的响应（用于前端显示和保存）
        full_response_content = ""
        thinking_steps = []

        while res is None or agent_name != "none":
            try:
                res = self._conversation(user_message=str(context), agent_name=agent_name, stream=False)
                print(res)
            except Exception as e:
                logger.error(f"调用 Agent '{agent_name}' 失败: {e}")
                max_trys -= 1
                if max_trys <= 0:
                    context.append(self.__error_message(agent_name, message=str(e)))
                    return context
                continue

            if res.status != "success":
                logger.error(f"Agent '{agent_name}' 返回错误状态: {res.message}")
                context.append(self.__error_message(agent_name, message=res.message))
                return context

            # 收集完整响应（用于前端显示）
            full_response_content += f"## {agent_name}\n"
            full_response_content += f"Reason: {res.agent_selection_reason}\n"
            if res.message:
                full_response_content += f"Message: {res.message}\n"
            # 安全地访问data.answer
            if res.data:
                if hasattr(res.data, 'answer') and res.data.answer:
                    full_response_content += f"Answer: {res.data.answer}\n"
                elif isinstance(res.data, dict) and res.data.get('answer'):
                    full_response_content += f"Answer: {res.data['answer']}\n"
            full_response_content += "\n"

            # 收集thinking steps
            if agent_name != "entrance_agent" and agent_name != "general_agent":
                thinking_steps.append({
                    "agent_name": agent_name,
                    "reason": res.agent_selection_reason,
                    "task": res.task_list[0] if res.task_list else None
                })

            # 构建下一轮查询
            query = {
                "task_list": res.task_list,
                "data": res.data
            }
            context.append(self.__system_message(
                content=json.dumps(query, ensure_ascii=False),
                message=res.message
            ))
            agent_name = res.next_agent
            max_trys = self.max_trys
            logger.info(f"切换到 Agent: {agent_name}, 响应消息: {res.message}")

        # 保存到上下文管理器
        if session_id and context_manager:
            ctx = context_manager.get_or_create_context(session_id)
            # 提取general_agent的最终答案
            final_answer = ""
            for msg in reversed(context):
                if msg.get("role") == "system" and msg.get("content"):
                    try:
                        content_obj = json.loads(msg["content"])
                        data = content_obj.get("data")
                        if data:
                            # 处理AgentData对象和dict两种情况
                            if hasattr(data, 'answer') and data.answer:
                                final_answer = data.answer
                                break
                            elif isinstance(data, dict) and data.get('answer'):
                                final_answer = data['answer']
                                break
                    except:
                        pass

            ctx.add_user_message(original_query)  # 使用原始查询
            ctx.add_assistant_message(
                full_response=full_response_content,
                final_answer=final_answer,
                thinking_steps=thinking_steps
            )

        return context

    def _stream_call(self, query: str, history_context: List[Dict] = None, session_id: str = None, context_manager=None) -> Generator[Dict[str, Any], None, None]:
        """
        流式响应逻辑

        Args:
            query: 用户查询
            history_context: 历史上下文（简化版）
            session_id: 会话ID
            context_manager: 上下文管理器

        Yields:
            Dict: 流式事件字典
        """
        agent_name = self.start_agent
        max_trys = self.max_trys

        # 保存原始用户查询（用于后续保存到上下文管理器）
        original_query = query

        # 构建初始context：历史上下文 + 当前用户消息
        context = []

        # 添加历史上下文
        if history_context:
            context.extend(history_context)

        # 添加当前用户消息
        context.append(self.__user_message(query))

        # 用于收集完整的响应（用于前端显示和保存）
        full_response_content = ""
        thinking_steps = []

        # 初始元数据事件
        yield {
            "type": "metadata",
            "data": {"query": query, "start_agent": agent_name, "has_history": len(history_context) > 0},
            "metadata": {"stage": "init"}
        }

        while True:
            # 检查是否需要暂停等待用户输入
            if agent_name == "wait_for_user_input":
                yield {
                    "type": "pause",
                    "data": {
                        "status": "waiting_for_input",
                        "reason": "Agent需要等待用户输入",
                        "context": context,  # 保存当前上下文
                        "agent_history": thinking_steps  # 保存已执行的agent历史
                    },
                    "metadata": {"timestamp": self._get_timestamp()}
                }
                break

            # 检查是否结束
            if agent_name == "none":
                yield {
                    "type": "metadata",
                    "data": {"status": "completed"},
                    "metadata": {"stage": "end"}
                }
                break

            try:
                # Agent开始事件 - 立即yield
                logger.info(f"[STREAM] Yielding agent_start for {agent_name}")
                yield {
                    "type": "agent_start",
                    "data": {
                        "agent_name": agent_name,
                        "agent_description": self.agents[agent_name].description,
                        "agent_status": "processing"
                    },
                    "metadata": {"timestamp": self._get_timestamp()}
                }

                # 流式conversation
                res = None
                event_count = 0
                for event in self._conversation(
                    user_message=str(context),
                    agent_name=agent_name,
                    stream=True
                ):
                    event_count += 1
                    # 转发LLM的delta事件
                    if event["type"] == "delta":
                        if event_count % 10 == 1:  # 每10个delta记录一次
                            logger.info(f"[STREAM] Yielding delta #{event_count} for {agent_name}")
                        yield event
                    elif event["type"] == "message":
                        # 收到完整Message
                        logger.info(f"[STREAM] Received complete message for {agent_name}")
                        res = Message(**event["data"]["message"])
                    elif event["type"] == "metadata":
                        # 转发元数据（如token使用）
                        yield event
                    elif event["type"] == "error":
                        # 转发错误
                        yield event
                        res = Message(
                            status="error",
                            task_list=[],
                            data=None,
                            next_agent="none",
                            agent_selection_reason="错误",
                            message=event["data"].get("error_message", "未知错误")
                        )
                        break

                if res is None:
                    raise Exception("未收到完整响应")

                # Agent结束事件
                yield {
                    "type": "agent_end",
                    "data": {
                        "agent_name": agent_name,
                        "status": res.status,
                        "next_agent": res.next_agent,
                        "agent_selection_reason": res.agent_selection_reason,
                        "task_list": res.task_list
                    },
                    "metadata": {"timestamp": self._get_timestamp()}
                }

                # 收集完整响应（用于前端显示）
                full_response_content += f"## {agent_name}\n"
                full_response_content += f"Reason: {res.agent_selection_reason}\n"
                if res.message:
                    full_response_content += f"Message: {res.message}\n"
                # 安全地访问data.answer
                if res.data:
                    if hasattr(res.data, 'answer') and res.data.answer:
                        full_response_content += f"Answer: {res.data.answer}\n"
                    elif isinstance(res.data, dict) and res.data.get('answer'):
                        full_response_content += f"Answer: {res.data['answer']}\n"
                full_response_content += "\n"

                # 收集thinking steps
                if agent_name != "entrance_agent" and agent_name != "general_agent":
                    thinking_steps.append({
                        "agent_name": agent_name,
                        "reason": res.agent_selection_reason,
                        "task": res.task_list[0] if res.task_list else None
                    })

                # 完整Message事件
                yield {
                    "type": "message",
                    "data": {"message": res.model_dump()},
                    "metadata": {"agent_name": agent_name}
                }

                if res.status != "success":
                    logger.error(f"Agent '{agent_name}' 返回错误状态: {res.message}")
                    break

                # 更新context
                query_data = {
                    "task_list": res.task_list,
                    "data": res.data
                }
                context.append(self.__system_message(
                    content=json.dumps(query_data, ensure_ascii=False),
                    message=res.message
                ))
                agent_name = res.next_agent
                max_trys = self.max_trys

            except Exception as e:
                logger.error(f"调用 Agent '{agent_name}' 失败: {e}")
                yield {
                    "type": "error",
                    "data": {
                        "error_message": str(e),
                        "agent_name": agent_name,
                        "recoverable": True
                    }
                }
                max_trys -= 1
                if max_trys <= 0:
                    break
                continue

        # 保存到上下文管理器（流式调用完成后）
        if session_id and context_manager:
            ctx = context_manager.get_or_create_context(session_id)
            # 提取general_agent的最终答案（从最后一个消息中）
            final_answer = ""
            for msg in reversed(context):
                if msg.get("role") == "system" and msg.get("content"):
                    try:
                        content_obj = json.loads(msg["content"])
                        data = content_obj.get("data")
                        if data:
                            # 处理AgentData对象和dict两种情况
                            if hasattr(data, 'answer') and data.answer:
                                final_answer = data.answer
                                break
                            elif isinstance(data, dict) and data.get('answer'):
                                final_answer = data['answer']
                                break
                    except:
                        pass

            ctx.add_user_message(original_query)  # 使用原始查询
            ctx.add_assistant_message(
                full_response=full_response_content,
                final_answer=final_answer,
                thinking_steps=thinking_steps
            )

    def _conversation(
        self,
        user_message,
        agent_name: str = "entrance_agent",
        stream: bool = False
    ) -> Union[Message, Generator[Dict[str, Any], None, None]]:
        """
        与指定 Agent 进行对话（内部方法）

        Args:
            user_message: 用户消息
            agent_name: Agent名称
            stream: 是否流式响应

        Returns:
            stream=False: Message对象
            stream=True: Generator，yield流式事件
        """
        agent = self.agents[agent_name]

        if agent_name != "entrance_agent" and (not agent or not agent.is_active):
            error_msg = f"Agent '{agent_name}' 不存在或未激活。"
            if stream:
                yield {"type": "error", "data": {"error_message": error_msg}}
                return
            return error_msg

        agent_prompt = agent.get_prompt()
        agent_prompt.available_agents = self.agents.to_string()

        if stream:
            # 流式模式
            yield from self._stream_llm_call(
                system_prompt=agent_prompt.string(agent_name),
                user_message=user_message,
                agent_name=agent_name,
                agent=agent
            )
        else:
            # 同步模式（原有逻辑）
            response = self.llm.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": agent_prompt.string(agent_name)},
                    {"role": "user", "content": user_message}
                ],
            )
            json_response = json.loads(response.choices[0].message.content
                                       .split("<|message|>")[-1]
                                       .split("``")[-1]
                                       .strip())
            return agent(Message(**json_response))

    def _stream_llm_call(
        self,
        system_prompt: str,
        user_message: str,
        agent_name: str,
        agent
    ) -> Generator[Dict[str, Any], None, None]:
        """
        流式LLM调用核心逻辑

        Yields:
            Dict: 流式事件（delta、metadata、message）
        """
        full_content = []
        start_time = time.time()

        try:
            # 调用OpenAI流式API
            stream_response = self.llm.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                stream=True  # 启用流式
            )

            # 收集增量内容
            for chunk in stream_response:
                # 提取delta内容
                delta = chunk.choices[0].delta

                # 检查是否有content
                if hasattr(delta, 'content') and delta.content:
                    full_content.append(delta.content)

                    # Yield delta事件
                    # 判断是否是最终输出（general_agent的输出）
                    is_final_output = (agent_name == "general_agent")

                    yield {
                        "type": "delta",
                        "data": {
                            "content": delta.content,
                            "finish_reason": None,
                            "is_final_output": is_final_output
                        },
                        "metadata": {
                            "agent_name": agent_name,
                            "timestamp": self._get_timestamp()
                        }
                    }

                # 检查是否完成
                finish_reason = chunk.choices[0].finish_reason
                if finish_reason:
                    is_final_output = (agent_name == "general_agent")
                    yield {
                        "type": "delta",
                        "data": {
                            "content": "",
                            "finish_reason": finish_reason,
                            "is_final_output": is_final_output
                        },
                        "metadata": {"agent_name": agent_name}
                    }
                    break

            # 组合完整内容
            complete_content = "".join(full_content)

            # 提取JSON响应
            # 首先移除markdown代码块标记
            json_str = complete_content.strip()

            # 移除 ```json 和 ``` 标记
            if "```" in json_str:
                # 提取两个```之间的内容
                parts = json_str.split("```")
                for i, part in enumerate(parts):
                    if i % 2 == 1:  # 奇数索引是代码块内容
                        json_str = part.strip()
                        if json_str.startswith("json"):
                            json_str = json_str[4:].strip()
                        break
                else:
                    # 如果没找到代码块，取最后一部分
                    json_str = parts[-1].strip()

            # 查找 <|message|> 标签之后的内容
            if "<|message|>" in json_str:
                json_str = json_str.split("<|message|>")[-1].strip()

            # 记录调试信息
            logger.debug(f"Agent {agent_name} - 提取的JSON字符串前300字符: {json_str[:300]}")

            try:
                json_response = json.loads(json_str)
            except json.JSONDecodeError as e:
                logger.error(f"JSON解析失败: {e}")
                logger.error(f"完整内容: {complete_content}")
                logger.error(f"提取的JSON字符串: {json_str}")
                raise

            # 调用Agent处理
            message = Message(**json_response)
            processed_message = agent(message)

            # Yield元数据（token使用情况）
            duration = time.time() - start_time
            yield {
                "type": "metadata",
                "data": {
                    "duration_ms": int(duration * 1000),
                    "content_length": len(complete_content)
                },
                "metadata": {"agent_name": agent_name}
            }

            # Yield完整Message
            yield {
                "type": "message",
                "data": {"message": processed_message.model_dump()},
                "metadata": {"agent_name": agent_name}
            }

        except json.JSONDecodeError as e:
            # JSON解析错误已经被上面处理过了，这里只是为了完整性
            logger.error(f"JSON解析错误未被捕获: {e}")
            yield {
                "type": "error",
                "data": {
                    "error_message": f"LLM响应解析失败: {str(e)}",
                    "error_type": "JSONDecodeError",
                    "agent_name": agent_name
                }
            }
        except Exception as e:
            logger.error(f"LLM流式调用失败: {e}")
            yield {
                "type": "error",
                "data": {
                    "error_message": str(e),
                    "error_type": type(e).__name__,
                    "agent_name": agent_name,
                    "recoverable": False
                }
            }

    def _get_timestamp(self) -> str:
        """获取ISO格式时间戳"""
        return datetime.utcnow().isoformat() + "Z"

    def generate_title(self, query: str, response: str) -> str:
        """
        基于用户查询和回复生成对话标题

        Args:
            query: 用户的原始查询
            response: AI助手的最终回复

        Returns:
            str: 生成的标题（最多30个字符）
        """
        try:
            # 构建生成标题的提示词
            title_prompt = """你是一个专业的对话标题生成助手。请根据用户的查询和AI的回复，生成一个简短、准确的对话标题。

要求：
1. 标题应该简洁明了，概括对话的核心内容
2. 标题长度控制在15-25个汉字之间
3. 不要使用标点符号或特殊字符
4. 直接返回标题文本，不要任何解释或额外内容

用户查询：{query}

AI回复：{response}

请生成标题："""

            # 调用LLM生成标题
            title_response = self.llm.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "user", "content": title_prompt.format(query=query, response=response[:500])}
                ],
                temperature=0.7,
                max_tokens=50,
                # 关闭推理
                reasoning_effort='none'
            )

            # 提取标题文本
            title = title_response.choices[0].message.content.strip()

            # 清理可能的引号和多余空格
            title = title.strip('"').strip("'").strip()

            # 如果生成的标题太长，截断它
            if len(title) > 30:
                title = title[:30]

            logger.info(f"生成对话标题: {title}")
            return title

        except Exception as e:
            logger.error(f"生成标题失败: {e}")
            # 如果生成失败，返回查询的前30个字符作为后备
            fallback_title = query[:30]
            if len(query) > 30:
                fallback_title += "..."
            return fallback_title

    # 保持向后兼容的公共方法
    def conversation(self, user_message, agent_name: str = "entrance_agent") -> Message:
        """与指定 Agent 进行对话（向后兼容的公共方法）"""
        return self._conversation(user_message, agent_name, stream=False)

    def __user_message(self, query: str):
        return {
            "role": "user",
            "content": query,
            "message": None
        }

    def __system_message(self, content: str, message: str = None):
        return {
            "role": "system",
            "content": content,
            "message": message
        }

    def __error_message(self, agent_name: str, message: str = None):
        return {
            "role": "error",
            "content": f"Agent '{agent_name}' 调用失败，终止处理。",
            "message": f"错误信息: {message}"
        }

    def _stream_call_resume(self, query: str, resume_data: Dict, session_id: str = None, context_manager=None) -> Generator[Dict[str, Any], None, None]:
        """
        从暂停点恢复流式执行

        Args:
            query: 用户输入（表单数据）
            resume_data: 恢复数据，包含暂停的上下文
            session_id: 会话ID
            context_manager: 上下文管理器

        Yields:
            Dict: 流式事件字典
        """
        max_trys = self.max_trys

        # 从 resume_data 中恢复状态
        context = resume_data.get("context", [])
        thinking_steps = resume_data.get("agent_history", [])

        # 重新开始上一个agent，这次带上用户的表单数据
        # 找到上一个执行的agent名称（从thinking_steps中获取）
        if thinking_steps:
            last_agent_name = thinking_steps[-1]["agent_name"]
        else:
            last_agent_name = self.start_agent

        agent_name = last_agent_name

        logger.info(f"[RESUME] 从暂停点恢复执行，上一个agent: {agent_name}")

        # 通知客户端开始恢复执行
        yield {
            "type": "metadata",
            "data": {"status": "resuming", "agent_name": agent_name},
            "metadata": {"stage": "resume"}
        }

        # 添加用户消息（表单提交）到上下文
        context.append(self.__user_message(query))

        # 用于收集完整的响应
        full_response_content = ""

        try:
            # 重新执行上一个agent，这次使用表单数据
            logger.info(f"[RESUME] 重新执行 agent: {agent_name}")

            yield {
                "type": "agent_start",
                "data": {
                    "agent_name": agent_name,
                    "agent_description": self.agents[agent_name].description,
                    "agent_status": "processing"
                },
                "metadata": {"timestamp": self._get_timestamp()}
            }

            # 调用agent
            res = None
            for event in self._conversation(
                user_message=str(context),
                agent_name=agent_name,
                stream=True
            ):
                if event["type"] == "delta":
                    yield event
                elif event["type"] == "message":
                    res = Message(**event["data"]["message"])
                elif event["type"] == "metadata":
                    yield event
                elif event["type"] == "error":
                    yield event
                    res = Message(
                        status="error",
                        task_list=[],
                        data=None,
                        next_agent="none",
                        agent_selection_reason="错误",
                        message=event["data"].get("error_message", "未知错误")
                    )
                    break

            if res is None:
                raise Exception("未收到完整响应")

            # Agent结束事件
            yield {
                "type": "agent_end",
                "data": {
                    "agent_name": agent_name,
                    "status": res.status,
                    "next_agent": res.next_agent,
                    "agent_selection_reason": res.agent_selection_reason,
                    "task_list": res.task_list
                },
                "metadata": {"timestamp": self._get_timestamp()}
            }

            # 收集完整响应
            full_response_content += f"## {agent_name}\n"
            full_response_content += f"Reason: {res.agent_selection_reason}\n"
            if res.message:
                full_response_content += f"Message: {res.message}\n"
            if res.data:
                if hasattr(res.data, 'answer') and res.data.answer:
                    full_response_content += f"Answer: {res.data.answer}\n"
                elif isinstance(res.data, dict) and res.data.get('answer'):
                    full_response_content += f"Answer: {res.data['answer']}\n"
            full_response_content += "\n"

            # 更新thinking steps（替换最后一个）
            if agent_name != "entrance_agent" and agent_name != "general_agent":
                thinking_steps[-1] = {
                    "agent_name": agent_name,
                    "reason": res.agent_selection_reason,
                    "task": res.task_list[0] if res.task_list else None
                }

            # 完整Message事件
            yield {
                "type": "message",
                "data": {"message": res.model_dump()},
                "metadata": {"agent_name": agent_name}
            }

            if res.status != "success":
                logger.error(f"Agent '{agent_name}' 返回错误状态: {res.message}")
                # 保存到上下文管理器
                if session_id and context_manager:
                    self._save_to_context_manager(session_id, context_manager, context, full_response_content, thinking_steps)
                return

            # 更新context，继续agent链
            query_data = {
                "task_list": res.task_list,
                "data": res.data
            }
            context.append(self.__system_message(
                content=json.dumps(query_data, ensure_ascii=False),
                message=res.message
            ))
            agent_name = res.next_agent

            # 继续执行剩余的agent链
            while True:
                # 检查是否需要暂停
                if agent_name == "wait_for_user_input":
                    yield {
                        "type": "pause",
                        "data": {
                            "status": "waiting_for_input",
                            "reason": "Agent需要等待用户输入",
                            "context": context,
                            "agent_history": thinking_steps
                        },
                        "metadata": {"timestamp": self._get_timestamp()}
                    }
                    break

                # 检查是否结束
                if agent_name == "none":
                    yield {
                        "type": "metadata",
                        "data": {"status": "completed"},
                        "metadata": {"stage": "end"}
                    }
                    break

                try:
                    # Agent开始事件
                    logger.info(f"[STREAM] Yielding agent_start for {agent_name}")
                    yield {
                        "type": "agent_start",
                        "data": {
                            "agent_name": agent_name,
                            "agent_description": self.agents[agent_name].description,
                            "agent_status": "processing"
                        },
                        "metadata": {"timestamp": self._get_timestamp()}
                    }

                    # 流式conversation
                    res = None
                    for event in self._conversation(
                        user_message=str(context),
                        agent_name=agent_name,
                        stream=True
                    ):
                        if event["type"] == "delta":
                            yield event
                        elif event["type"] == "message":
                            res = Message(**event["data"]["message"])
                        elif event["type"] == "metadata":
                            yield event
                        elif event["type"] == "error":
                            yield event
                            res = Message(
                                status="error",
                                task_list=[],
                                data=None,
                                next_agent="none",
                                agent_selection_reason="错误",
                                message=event["data"].get("error_message", "未知错误")
                            )
                            break

                    if res is None:
                        raise Exception("未收到完整响应")

                    # Agent结束事件
                    yield {
                        "type": "agent_end",
                        "data": {
                            "agent_name": agent_name,
                            "status": res.status,
                            "next_agent": res.next_agent,
                            "agent_selection_reason": res.agent_selection_reason,
                            "task_list": res.task_list
                        },
                        "metadata": {"timestamp": self._get_timestamp()}
                    }

                    # 收集完整响应
                    full_response_content += f"## {agent_name}\n"
                    full_response_content += f"Reason: {res.agent_selection_reason}\n"
                    if res.message:
                        full_response_content += f"Message: {res.message}\n"
                    if res.data:
                        if hasattr(res.data, 'answer') and res.data.answer:
                            full_response_content += f"Answer: {res.data.answer}\n"
                        elif isinstance(res.data, dict) and res.data.get('answer'):
                            full_response_content += f"Answer: {res.data['answer']}\n"
                    full_response_content += "\n"

                    # 收集thinking steps
                    if agent_name != "entrance_agent" and agent_name != "general_agent":
                        thinking_steps.append({
                            "agent_name": agent_name,
                            "reason": res.agent_selection_reason,
                            "task": res.task_list[0] if res.task_list else None
                        })

                    # 完整Message事件
                    yield {
                        "type": "message",
                        "data": {"message": res.model_dump()},
                        "metadata": {"agent_name": agent_name}
                    }

                    if res.status != "success":
                        logger.error(f"Agent '{agent_name}' 返回错误状态: {res.message}")
                        break

                    # 更新context
                    query_data = {
                        "task_list": res.task_list,
                        "data": res.data
                    }
                    context.append(self.__system_message(
                        content=json.dumps(query_data, ensure_ascii=False),
                        message=res.message
                    ))
                    agent_name = res.next_agent
                    max_trys = self.max_trys

                except Exception as e:
                    logger.error(f"调用 Agent '{agent_name}' 失败: {e}")
                    yield {
                        "type": "error",
                        "data": {
                            "error_message": str(e),
                            "agent_name": agent_name,
                            "recoverable": True
                        }
                    }
                    max_trys -= 1
                    if max_trys <= 0:
                        break
                    continue

            # 保存到上下文管理器
            if session_id and context_manager:
                self._save_to_context_manager(session_id, context_manager, context, full_response_content, thinking_steps)

        except Exception as e:
            logger.error(f"恢复执行失败: {e}")
            yield {
                "type": "error",
                "data": {
                    "error_message": str(e),
                    "agent_name": agent_name,
                    "recoverable": False
                }
            }

    def _save_to_context_manager(self, session_id: str, context_manager, context: List, full_response: str, thinking_steps: list):
        """保存到上下文管理器的辅助方法"""
        ctx = context_manager.get_or_create_context(session_id)
        # 提取general_agent的最终答案
        final_answer = ""
        for msg in reversed(context):
            if msg.get("role") == "system" and msg.get("content"):
                try:
                    content_obj = json.loads(msg["content"])
                    data = content_obj.get("data")
                    if data:
                        if hasattr(data, 'answer') and data.answer:
                            final_answer = data.answer
                            break
                        elif isinstance(data, dict) and data.get('answer'):
                            final_answer = data['answer']
                            break
                except:
                    pass

        # 保存用户消息（从context中提取最后一个用户消息）
        for msg in reversed(context):
            if msg.get("role") == "user":
                ctx.add_user_message(msg["content"])
                break

        ctx.add_assistant_message(
            full_response=full_response,
            final_answer=final_answer,
            thinking_steps=thinking_steps
        )
