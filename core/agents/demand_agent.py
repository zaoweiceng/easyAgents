"""
Demand Agent - 需求明确Agent
当用户需求不明确时，通过交互式表单帮助用户明确需求
"""

from typing import Dict, Any, List, Optional
from ..agent import Agent
from ..base_model import Message
from ..prompt.template_model import PromptTemplate
import logging

logger = logging.getLogger(__name__)

system_instructions = """
你是一个需求分析专家，擅长通过提问来帮助用户明确他们的需求。

当用户的需求不够明确或完整时，你需要：
1. 分析用户的原始需求
2. 识别缺失的关键信息
3. 设计一个交互式表单来收集这些信息
4. 提供清晰的选项和引导

你可以使用以下表单类型：
- 单选 (radio): 从多个选项中选择一个
- 多选 (checkbox): 从多个选项中选择多个
- 文本输入 (text): 用户输入自由文本
- 文本域 (textarea): 多行文本输入
- 数字输入 (number): 输入数字
- 表格 (table): 结构化数据输入
"""

core_instructions = """
# 任务流程

1. 分析用户需求，判断是否需要收集更多信息
2. 如果需求明确，直接返回 next_agent="none" 结束
3. 如果需求不明确，设计一个表单来收集信息

# 重要提示

你必须严格按照下面的 JSON 格式返回数据，特别是在 data 字段中包含 form_config。

# 表单设计规范

在 data 中返回表单配置，格式如下：

```json
{
  "status": "success",
  "task_list": ["收集用户需求信息"],
  "data": {
    "form_config": {
      "form_type": "survey",
      "form_title": "请完善您的需求信息",
      "form_description": "为了更好地帮助您，请填写以下信息",
      "fields": [
        {
          "field_name": "preference",
          "field_type": "radio",
          "label": "您更喜欢哪种类型？",
          "required": true,
          "options": ["选项A", "选项B", "选项C"]
        }
      ]
    }
  },
  "next_agent": "none",
  "agent_selection_reason": "需要收集更多信息以明确需求",
  "message": "请您填写以下信息，以便我更好地帮助您"
}
```

# 完整示例：旅行规划

用户说："帮我规划一次旅行"

你应该返回：

```json
{
  "status": "success",
  "task_list": ["收集旅行规划信息"],
  "data": {
    "form_config": {
      "form_type": "survey",
      "form_title": "旅行规划信息收集",
      "form_description": "请提供您的旅行需求，我们将为您规划合适的行程",
      "fields": [
        {
          "field_name": "destination_type",
          "field_type": "radio",
          "label": "您想去哪里？",
          "required": true,
          "options": ["国内游", "出境游", "周边游"]
        },
        {
          "field_name": "duration",
          "field_type": "number",
          "label": "计划旅行几天？",
          "required": true,
          "placeholder": "请输入天数"
        },
        {
          "field_name": "budget",
          "field_type": "number",
          "label": "预算范围（元）",
          "required": false,
          "placeholder": "请输入预算"
        }
      ]
    }
  },
  "next_agent": "none",
  "agent_selection_reason": "需求不明确，需要收集目的地、时间、预算等关键信息",
  "message": "请您填写以下信息，以便我更好地帮助您规划旅行"
}
```

# 完整示例：软件开发

用户说："我想开发一个软件"

你应该返回：

```json
{
  "status": "success",
  "task_list": ["收集软件开发需求"],
  "data": {
    "form_config": {
      "form_type": "survey",
      "form_title": "软件开发需求收集",
      "form_description": "为了更好地帮助您，请填写以下信息",
      "fields": [
        {
          "field_name": "software_type",
          "field_type": "radio",
          "label": "您想开发什么类型的软件？",
          "required": true,
          "options": ["Web应用", "移动应用", "桌面应用", "小程序"]
        },
        {
          "field_name": "platform",
          "field_type": "checkbox",
          "label": "目标平台（可多选）",
          "required": true,
          "options": ["iOS", "Android", "Windows", "macOS", "Linux", "Web"]
        },
        {
          "field_name": "main_features",
          "field_type": "textarea",
          "label": "请描述主要功能需求",
          "required": true,
          "placeholder": "请详细描述您希望软件实现的功能..."
        }
      ]
    }
  },
  "next_agent": "none",
  "agent_selection_reason": "需求不明确，需要了解软件类型、平台、功能等关键信息",
  "message": "请您填写以下信息，以便我更好地帮助您开发软件"
}
```

# 字段类型说明

- radio: 单选题
- checkbox: 多选题
- text: 单行文本输入
- textarea: 多行文本输入
- number: 数字输入
- select: 下拉选择
- table: 表格输入（用于结构化数据）

# 用户提交表单后的处理

当用户提交表单数据后，这些数据会在 message.data.form_values 中返回。
你需要：
1. 整合用户的原始需求和表单数据
2. 判断信息是否已足够明确
3. 如果仍需更多信息，继续返回包含 form_config 的 JSON
4. 如果信息已明确，返回包含 clarified_demand 的 JSON

# 输出格式要求

## 必须返回完整的 JSON，包含所有必要字段

## 需要收集信息时：
{
  "status": "success",
  "task_list": ["收集用户需求信息"],
  "data": {
    "form_config": { /* 表单配置，必须包含这个字段 */ }
  },
  "next_agent": "none",
  "agent_selection_reason": "需要收集更多信息以明确需求",
  "message": "请您填写以下信息，以便我更好地帮助您"
}

## 收集到足够信息后：
{
  "status": "success",
  "task_list": ["分析明确后的需求"],
  "data": {
    "clarified_demand": "整合后的明确需求描述"
  },
  "next_agent": "general_agent",
  "agent_selection_reason": "需求已明确，可以进行下一步处理",
  "message": "感谢您的信息，我已了解您的需求"
}
"""

data_fields = '''
"form_config": {  // 表单配置（需要收集信息时）
  "form_type": "string",
  "form_title": "string",
  "form_description": "string",
  "fields": [
    {
      "field_name": "string",
      "field_type": "string",  // radio, checkbox, text, textarea, number, select, table
      "label": "string",
      "required": "boolean",
      "options": ["string"],  // radio/checkbox/select 必填
      "placeholder": "string",  // text/textarea/number 可选
      "columns": [  // table 类型必填
        {"header": "string", "field": "string", "type": "string"}
      ],
      "min_rows": "number",  // table 可选
      "max_rows": "number"   // table 可选
    }
  ]
},
"clarified_demand": "string",  // 明确后的需求（信息足够时）
"form_values": {  // 用户提交的表单数据（信息足够时）
  "field_name": "value"
}
'''


class DemandAgent(Agent):
    """
    需求明确Agent - 帮助用户明确需求
    """

    def __init__(self):
        super().__init__(
            name="demand_agent",
            description="当用户需求不明确时，通过交互式表单帮助用户完善和明确需求。支持单选、多选、文本输入、表格等多种表单类型。",
            handles=["需求分析", "需求明确", "信息收集", "问卷调查"],
            parameters={
                "user_demand": "用户的原始需求描述",
                "form_values": "用户已填写的表单数据（如果有）"
            }
        )

        self.prompt_template = PromptTemplate(
            system_instructions=system_instructions,
            available_agents=None,  # 由系统动态填充
            core_instructions=core_instructions,
            data_fields=data_fields
        )

    def run(self, message: Message) -> Message:
        """
        处理需求明确请求

        Args:
            message: 包含用户需求和表单数据的消息

        Returns:
            Message: 包含表单配置或明确后的需求
        """
        try:
            # 详细日志：打印接收到的完整消息
            logger.info("="*70)
            logger.info("DemandAgent.run 被调用")
            logger.info("="*70)
            logger.info(f"接收到的 Message:")
            logger.info(f"  - status: {message.status}")
            logger.info(f"  - task_list: {message.task_list}")
            logger.info(f"  - next_agent: {message.next_agent}")
            logger.info(f"  - message: {message.message}")
            logger.info(f"  - data 类型: {type(message.data)}")

            # 打印 data 内容
            if message.data:
                if isinstance(message.data, dict):
                    logger.info(f"  - data 键: {list(message.data.keys())}")
                    logger.info(f"  - data 内容: {json.dumps(message.data, ensure_ascii=False, indent=2)[:1000]}")
                else:
                    logger.info(f"  - data: {str(message.data)[:500]}")
            else:
                logger.info(f"  - data: None")

            # 获取用户数据
            user_demand = message.data.get("user_demand", "") if message.data and isinstance(message.data, dict) else ""
            form_values = message.data.get("form_values", {}) if message.data and isinstance(message.data, dict) else {}

            logger.info(f"\n解析结果:")
            logger.info(f"  - user_demand: {user_demand[:50] if user_demand else 'None'}...")
            logger.info(f"  - form_values: {len(form_values)} 个字段")

            # 如果有表单数据，说明是用户提交表单后的回调
            if form_values:
                logger.info(f"\n→ 收到用户表单提交")
                logger.info(f"  表单数据: {form_values}")
                # 这里 LLM 已经分析了表单数据，我们只需要返回结果
                # LLM 会在 data 中返回 clarified_demand
                if message.data and message.data.get("clarified_demand"):
                    # 信息已明确，继续处理
                    message.next_agent = "general_agent"
                    message.message = f"需求已明确: {message.data['clarified_demand']}"
                    logger.info(f"  → 需求已明确，转交给 general_agent")
                else:
                    # 信息仍不足，LLM 会返回新的表单配置
                    message.next_agent = "none"
                    message.message = "需要更多信息，请继续填写"
                    logger.info(f"  → 需要更多信息")

                return message

            # 如果没有表单数据，这是首次请求
            # LLM 会判断是否需要收集信息，并在 data 中返回 form_config 或 clarified_demand
            logger.info(f"\n→ 首次请求，检查 data 内容:")

            if message.data and isinstance(message.data, dict):
                has_form_config = "form_config" in message.data
                has_clarified_demand = "clarified_demand" in message.data

                logger.info(f"  - 包含 form_config: {has_form_config}")
                logger.info(f"  - 包含 clarified_demand: {has_clarified_demand}")

                if has_form_config:
                    form_config = message.data.get("form_config")
                    logger.info(f"  - form_config 类型: {type(form_config)}")
                    if isinstance(form_config, dict):
                        logger.info(f"  - form_config 键: {list(form_config.keys())}")
                        logger.info(f"  ✓✓✓ 找到表单配置，准备返回给前端")
                    else:
                        logger.warning(f"  - form_config 不是字典: {form_config}")

                    # 需要收集信息
                    message.next_agent = "none"
                    message.message = "请您填写以下信息，以便我更好地帮助您"

                elif has_clarified_demand:
                    # 需求已经明确
                    message.next_agent = "general_agent"
                    message.message = f"需求已明确: {message.data['clarified_demand']}"
                    logger.info(f"  ✓ 需求已明确，转交给 general_agent")
                else:
                    # 未明确返回内容，默认需要收集信息
                    logger.warning(f"  ✗ data 中既没有 form_config 也没有 clarified_demand")
                    logger.warning(f"  ✗ data 的实际键: {list(message.data.keys())}")
                    message.next_agent = "none"
                    message.message = "请提供更多信息"
            else:
                logger.warning(f"  ✗ message.data 为 None 或不是字典")

            logger.info("="*70)
            return message

        except Exception as e:
            logger.error(f"DemandAgent 处理失败: {e}", exc_info=True)
            message.status = "error"
            message.message = f"需求分析失败: {str(e)}"
            message.next_agent = "general_agent"
            return message
