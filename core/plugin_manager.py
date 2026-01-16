import logging
import json
from .agent import AgentLoader, Agent
from .constants import app_name
from .agent_loader_util import load_class_from_file, filename_to_classname
import os
from .agents import EntranceAgent, GeneralAgent   # 导入所有内置 Agent

logger = logging.getLogger(app_name)
logger.setLevel(logging.WARNING)

class pluginManager:
    def __init__(self, src: str):
        self.agent_loader = AgentLoader()
        self.plugin_src = src
        self.load_plugins()
        self.agent_loader.add_agent(EntranceAgent())  # 添加入口 Agent
        self.agent_loader.add_agent(GeneralAgent())   # 添加通用 Agent

    
    def load_plugins(self) -> None:
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

    def to_string(self) -> str:
        return json.dumps(self.agent_loader.to_json(), ensure_ascii=False)
        
    def __getitem__(self, agent_name: str) -> Agent:
        agent = self.agent_loader.get_agent(agent_name)
        if agent is None:
            raise KeyError(f"Agent '{agent_name}' 不存在")
        return agent