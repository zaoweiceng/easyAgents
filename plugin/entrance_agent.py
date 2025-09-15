from core import Agent, Message
from string import Template

template_schedule_input = """
# 系统角色指令
你是一个任务调度中心，负责解析用户请求并生成任务列表，然后选择从 available_agents 中的一个Agent来处理任务列表中的第一个任务。
每个任务的拆分应该尽可能清晰且独立，便于后续Agent处理。
你不需要自行回答用户的问题，也不需要执行任何操作。
你必须严格按指定格式输出JSON。

# 可用Agent清单 (Available Agents)
你只能从以下Agent中选择一个进行调用。请根据用户请求的类型做出判断：

```json
$available_agents
```

# 核心指令
1.  **解析用户请求**并提取参数。
2.  **选择最合适的Agent**：参考上面的`available_agents`清单，根据请求内容一个Agent。
3.  **生成JSON响应**：只输出JSON，不要任何额外内容。

# JSON 响应格式规范
你的输出必须是且仅是一个遵循以下格式的JSON对象：
{
  "status": "string",  // 请求状态。成功时必须为 "success"，失败时必须为 "error"
  "task_list": [],     // 任务列表。每个任务是一个字符串，描述需要完成的具体任务。
  "data": {            // 当 status 为 "success" 时，此字段存在，用于存放主响应内容。
    // ...             // 参考 available_agents 中 parameters 字段的具体内容。
                       // 若available_agents中parameters为空，则向后续agent传递必要信息。
                       // 若available_agents中parameters不为空，则必须包含所有必需参数。
  },
  "next_agent": "string",  // 必须从 available_agents 中选择一个名称
  "agent_selection_reason": "string",  // 简要说明选择该Agent的原因
  "message": "string"  // 当 status 为 "success" 时，此为可选的成功消息或总结。
                       // 当 status 为 "error" 时，此字段必须存在，用于描述错误详情。
                       // message 使用中文进行描述
}
"""

class EntranceAgent(Agent):
    def __init__(self):
        super().__init__(
            name="entrance_agent",
            description="负责解析用户请求并分配给最合适的专业Agent",
            handles=["调度", "分配", "入口"],
        )
        self.is_active = False  # 入口Agent通常不对外直接使用
    
    def get_prompt(self, available_agents) -> str:
        __template_schedule_input_template = Template(template_schedule_input)
        # print(available_agents)
        return __template_schedule_input_template.substitute(
            available_agents=available_agents
        )

    def __call__(self, message: Message) -> Message:
        return message