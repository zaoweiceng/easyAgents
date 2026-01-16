from string import Template

prompt_template_basic = \
"""
# 系统角色指令
$system_instructions
你必须严格按指定格式输出JSON。

# 可用Agent清单 (Available Agents)
你只能从以下Agent中选择一个进行调用。请根据用户请求的类型做出判断：
(如果已经完成所有任务，请交给general_agent进行整合输出而不是返回none)

```json
$available_agents
```

# 核心指令
$core_instructions

# JSON 响应格式规范
你的输出必须是且仅是一个遵循以下格式的JSON对象：
{
  "status": "string",  // 请求状态。成功时必须为 "success"，失败时必须为 "error"
  "task_list": [],     // 任务列表。每个任务是一个字符串，描述需要完成的具体任务。
  "data": {            // 当 status 为 "success" 时，此字段存在，用于存放主响应内容。
    $data_fields
    // ...  // 参考 available_agents 中 parameters 字段的具体内容。
            // 若available_agents中parameters为空，则向后续agent传递必要信息。
            // 若available_agents中parameters不为空，则必须包含所有必需参数。
  },
  "next_agent": "string",  // 必须从 available_agents 中选择一个名称，若已经完成所有任务，请交给general_agent（只有general_agent可以填写 "none"）
  "agent_selection_reason": "string",  // 简要说明选择该Agent的原因
  "message": "string"  // 当 status 为 "success" 时，此为可选的成功消息或总结。
                       // 当 status 为 "error" 时，此字段必须存在，用于描述错误详情。
                       // message 使用中文进行描述
}
"""

template_basic = Template(prompt_template_basic).substitute(
    system_instructions=\
            """
                $system_instructions
                你需要选择task_list中的第一个任务，完成后将其从task_list中移除。
            """,
    available_agents="$available_agents",
    core_instructions="$core_instructions",
    data_fields="$data_fields"
)