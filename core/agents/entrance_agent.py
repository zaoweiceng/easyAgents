from .. import Agent, Message
from ..prompt.entrance_template import entrance_template

class EntranceAgent(Agent):
    def __init__(self):
        super().__init__(
            name="entrance_agent",
            description="负责解析用户请求并分配给最合适的专业Agent",
            handles=["调度", "分配", "入口"],
        )
        self.is_active = False  # 入口Agent不对外直接使用
        self.prompt_template = entrance_template

    def run(self, message: Message) -> Message:
        return message