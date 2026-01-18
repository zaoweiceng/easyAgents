from .. import Agent, Message
from ..prompt.general_template import general_template
import logging

logger = logging.getLogger(__name__)

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
        # 确保general_agent完成后不会循环调用自己或其他agent
        # 如果next_agent不是"none"或"wait_for_user_input"，强制设置为"none"
        if message.next_agent not in ["none", "wait_for_user_input"]:
            logger.warning(f"general_agent返回了next_agent='{message.next_agent}'，已强制设置为'none'以防止循环调用")
            message.next_agent = "none"
        return message