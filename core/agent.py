from typing import List, Dict, Optional
from pydantic import BaseModel, Field
from enum import Enum

class Agent(BaseModel):
    """Agent 定义类"""
    
    name: str = Field(
        ...,
        description="Agent 的唯一标识名称",
        min_length=1,
        max_length=50,
    )
    
    description: str = Field(
        ...,
        description="Agent 的功能描述",
        min_length=10,
        max_length=200
    )

    parameters: Optional[Dict[str, str]] = Field(
        None,
        description="Agent 所需的参数及其描述",
    )
    
    handles: List[str] = Field(
        ...,
        description="Agent 能够处理的关键词或短语列表",
        min_items=1
    )
    
    is_active: bool = Field(
        default=True,
        description="Agent 是否处于活跃状态"
    )
    
    version: str = Field(
        default="1.0.0",
        description="Agent 版本号",
    )

class AgentLoader:
    """Agent 加载器类"""
    
    def __init__(self):
        self.agents: Dict[str, Agent] = {}
    
    def add_agent(self, agent: Agent) -> None:
        """添加一个 Agent"""
        if agent.name in self.agents:
            raise ValueError(f"Agent '{agent.name}' 已存在")
        self.agents[agent.name] = agent
    
    def remove_agent(self, agent_name: str) -> None:
        """移除一个 Agent"""
        if agent_name not in self.agents:
            raise ValueError(f"Agent '{agent_name}' 不存在")
        del self.agents[agent_name]
    
    def get_agent(self, agent_name: str) -> Optional[Agent]:
        """获取指定名称的 Agent"""
        return self.agents.get(agent_name)
    
    def get_all_agents(self) -> Dict[str, Agent]:
        """获取所有 Agent"""
        return self.agents.copy()
    
    def get_active_agents(self) -> Dict[str, Agent]:
        """获取所有活跃的 Agent"""
        return {name: agent for name, agent in self.agents.items() if agent.is_active}
    
    def to_json(self) -> dict:
        """转换为所需的 JSON 格式"""
        available_agents = {}
        
        for name, agent in self.get_active_agents().items():
            available_agents[name] = {
                "description": agent.description,
                "handles": agent.handles,
                "parameters": agent.parameters or {}
            }
        
        return {"available_agents": available_agents}
    
    def load_from_list(self, agents: List[Agent]) -> None:
        """从 Agent 列表加载"""
        for agent in agents:
            self.add_agent(agent)