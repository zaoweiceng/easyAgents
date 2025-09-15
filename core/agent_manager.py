from . import Agent, AgentLoader, Message
import openai
import json
import logging

logger = logging.getLogger('easyAgent')
logger.setLevel(logging.WARNING)


class AgentManager:
    def __init__(self, plugin_src: str, 
                 base_url: str, 
                 api_key: str, 
                 model_name: str,
                 start_agent_name: str,
                 end_agent_name: str):
        self.plugin_src = plugin_src
        self.agent_loader = AgentLoader()
        self.load_plugins()
        self.llm = openai.OpenAI(
            base_url=base_url,
            api_key=api_key
        )
        self.model_name = model_name
        self.start_agent = start_agent_name
        self.end_agent = end_agent_name
        self.max_trys = 3

    def load_plugins(self) -> None:
        """加载插件目录中的所有 Agent"""
        import os
        from .agent_loader_util import load_class_from_file, filename_to_classname

        if not os.path.isdir(self.plugin_src):
            raise ValueError(f"插件目录 '{self.plugin_src}' 不存在或不是一个目录")

        for filename in os.listdir(self.plugin_src):
            if filename.endswith(".py") and not filename.startswith("__"):
                logger.info(f"加载 Agent 文件: {filename}")
                filepath = os.path.join(self.plugin_src, filename)
                class_name = filename_to_classname(filename)
                try:
                    cls = load_class_from_file(filepath, class_name)
                    if issubclass(cls, Agent):
                        agent_instance = cls()
                        self.agent_loader.add_agent(agent_instance)
                except (ImportError, AttributeError, ValueError) as e:
                    logger.error(f"加载插件 '{filename}' 失败: {e}")

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
        agent = self.agent_loader.get_agent(agent_name)
        if agent_name != "entrance_agent" and (not agent or not agent.is_active):
            return f"Agent '{agent_name}' 不存在或未激活。"
        agent_prompt = agent.get_prompt(available_agents=
                                        json.dumps(self.agent_loader.to_json(), ensure_ascii=False))

        response = self.llm.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": agent_prompt},
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
