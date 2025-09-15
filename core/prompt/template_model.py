from typing import Optional
from pydantic import BaseModel, Field
from string import Template
from ..constants import start_agent_name
from ..prompt.prompt_template import prompt_template_basic, template_basic

class PromptTemplate(BaseModel):
    
    system_instructions: str = Field(
        ...,
        description="系统指令，定义整体行为和目标"
    )
    available_agents: Optional[str] = Field(
        ...,
        description="可用的Agent列表，格式化为字符串"
    )
    core_instructions: str = Field(
        ...,
        description="核心指令，定义主要任务和规则"
    )
    data_fields: Optional[str] = Field(
        None,
        description="可选的数据字段，提供额外的上下文信息"
    )

    def string(self, agent_name:str) -> str:
        """将 PromptTemplate 转换为字符串表示"""

        if agent_name == start_agent_name:
            return Template(prompt_template_basic).substitute(
                system_instructions=self.system_instructions,
                available_agents=self.available_agents,
                core_instructions=self.core_instructions,
                data_fields=""
            )
        return Template(template_basic).substitute(
            system_instructions=self.system_instructions,
            available_agents=self.available_agents,
            core_instructions=self.core_instructions,
            data_fields=self.data_fields or ""
        )