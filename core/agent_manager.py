from . import Message
from .constants import start_agent_name, end_agent_name, app_name
from .plugin_manager import pluginManager
import openai
import json
import logging

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

    def __call__(self, query: str):
        """处理用户查询"""
        agent_name = self.start_agent 
        res = None
        max_trys = self.max_trys
        context = [self.__user_message(query)]
        while res is None or agent_name != "none":
            try:
                res = self.conversation(user_message=str(context), agent_name=agent_name)
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
    
    def conversation(self, user_message, agent_name: str = "entrance_agent") -> Message:
        """与指定 Agent 进行对话"""
        agent = self.agents[agent_name]
        # print(f"当前使用的Agent: {agent_name}")
        if agent_name != "entrance_agent" and (not agent or not agent.is_active):
            return f"Agent '{agent_name}' 不存在或未激活。"
        agent_prompt = agent.get_prompt()
        # print(agent_prompt)
        agent_prompt.available_agents = self.agents.to_string()
        # print(agent_prompt.string(agent_name))
        response = self.llm.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": agent_prompt.string(agent_name)},
                {"role": "user", "content": user_message}
            ],
        )
        json_response = json.loads(response.choices[0].message.content
                                   .split("<|message|>")[-1]
                                   .split("</think>")[-1]
                                   .strip())
        return agent(Message(**json_response))

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
