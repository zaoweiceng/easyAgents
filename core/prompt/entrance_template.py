from .template_model import PromptTemplate

system_instructions = \
"""
你是一个任务调度中心，负责解析用户请求并生成任务列表。
"""

core_instructions = \
"""
1. 解析用户请求并生成任务列表。
2. 每个任务的拆分应该尽可能清晰且独立，便于后续Agent处理。
3. 从 available_agents 中的一个Agent来处理任务列表中的第一个任务。
4. 你不需要自行回答用户的问题，也不需要执行任何额外操作。
"""

data_fields = \
"""
"""

entrance_template = PromptTemplate(
    system_instructions=system_instructions,
    available_agents=None,
    core_instructions=core_instructions,
    data_fields=data_fields
)

# entrance_template = Template(prompt_template_basic).substitute(
#     system_instructions=system_instructions,
#     available_agents="$available_agents",
#     core_instructions=core_instructions,
#     data_fields=data_fields
# )