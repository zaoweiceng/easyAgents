from . import Message
from .constants import start_agent_name, end_agent_name, app_name
from .plugin_manager import pluginManager
from .agent import normalize_agent_output
import openai
import json
import logging
from typing import Generator, Dict, Any, Union
from datetime import datetime
import time

logger = logging.getLogger(app_name)
logger.setLevel(logging.WARNING)


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

    def __call__(self, query: str, stream: bool = False) -> Union[list, Generator[Dict[str, Any], None, None]]:
        """
        处理用户查询

        Args:
            query: 用户查询文本
            stream: 是否启用流式响应（默认False）

        Returns:
            stream=False: 返回list（原有行为）
            stream=True: 返回Generator[Dict]，yield流式事件
        """
        if stream:
            return self._stream_call(query)
        else:
            return self._sync_call(query)

    def _sync_call(self, query: str) -> list:
        """原有同步逻辑（保持向后兼容）"""
        agent_name = self.start_agent
        res = None
        max_trys = self.max_trys
        context = [self.__user_message(query)]
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
            # query = [res.task_list, res.data]
            query = {
                "task_list": res.task_list,
                "data": res.data
            }
            context.append(self.__system_message(content=query
                                                 if isinstance(query, str)
                                                 else json.dumps(query, ensure_ascii=False),
                                                 message=res.message))
            agent_name = res.next_agent
            max_trys = self.max_trys
            logger.info(f"切换到 Agent: {agent_name}, 响应消息: {res.message}")
        return context

    def _stream_call(self, query: str) -> Generator[Dict[str, Any], None, None]:
        """
        流式响应逻辑

        Yields:
            Dict: 流式事件字典
        """
        agent_name = self.start_agent
        max_trys = self.max_trys
        context = [self.__user_message(query)]

        # 初始元数据事件
        yield {
            "type": "metadata",
            "data": {"query": query, "start_agent": agent_name},
            "metadata": {"stage": "init"}
        }

        while True:
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
                yield {
                    "type": "agent_start",
                    "data": {
                        "agent_name": agent_name,
                        "agent_description": self.agents[agent_name].description
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
                    # 转发LLM的delta事件
                    if event["type"] == "delta":
                        yield event
                    elif event["type"] == "message":
                        # 收到完整Message
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
                        "next_agent": res.next_agent
                    },
                    "metadata": {"timestamp": self._get_timestamp()}
                }

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
                    yield {
                        "type": "delta",
                        "data": {
                            "content": delta.content,
                            "finish_reason": None
                        },
                        "metadata": {
                            "agent_name": agent_name,
                            "timestamp": self._get_timestamp()
                        }
                    }

                # 检查是否完成
                finish_reason = chunk.choices[0].finish_reason
                if finish_reason:
                    yield {
                        "type": "delta",
                        "data": {
                            "content": "",
                            "finish_reason": finish_reason
                        },
                        "metadata": {"agent_name": agent_name}
                    }
                    break

            # 组合完整内容
            complete_content = "".join(full_content)

            # 提取JSON响应
            json_str = (
                complete_content
                .split("<|message|>")[-1]
                .split("``")[-1]
                .strip()
            )
            json_response = json.loads(json_str)

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
            logger.error(f"JSON解析失败: {e}, 内容: {complete_content[-200:]}")
            yield {
                "type": "error",
                "data": {
                    "error_message": f"LLM响应解析失败: {str(e)}",
                    "error_type": "JSONDecodeError",
                    "agent_name": agent_name,
                    "recoverable": False
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
