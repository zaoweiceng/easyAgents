from .. import Agent, Message
from ..prompt.general_template import general_template

class GeneralAgent(Agent):
    def __init__(self):
        super().__init__(
            name="general_agent",
            description="处理一般性问答，如常识问题、建议等，或总结性回答",
            handles=["通用问题", "其他查询", "总结性回答", "综合性问题"],
        )
        self.is_active = True
        self.prompt_template = general_template
    
    def __call__(self, message: Message) -> Message:
        return message