"""
Demo Agent - 示例Agent

这是一个完整的Agent示例，展示了如何创建自定义Agent。
该Agent实现了简单的数学计算功能，演示了Agent的基本结构。

你可以将此文件复制到 plugin/ 目录下，系统会自动加载该Agent。
"""

from core.agent import Agent
from core.base_model import Message
from core.prompt.template_model import PromptTemplate
import logging

logger = logging.getLogger(__name__)

# ================================
# 第一步：定义提示词模板
# ================================

# 系统指令：定义Agent的角色和行为
system_instructions = """
你是一位数学计算专家，擅长理解和执行各种数学计算任务。

你需要：
1. 理解用户的计算需求
2. 识别计算类型（基础运算、复杂表达式等）
3. 提取必要的参数（数字、运算符等）
"""

# 核心指令：具体的任务执行指南
core_instructions = """
# 任务流程

1. 分析用户的计算需求
2. 提取计算类型和参数
3. 在data字段中返回结构化的计算信息

# 返回格式

在 data 字段中包含以下信息：
- operation: 运算类型（add, subtract, multiply, divide等）
- operand1: 第一个操作数
- operand2: 第二个操作数（如果需要）
- expression: 完整的表达式

# 示例

用户说："计算 123 加 456"

你应该返回：
```json
{
  "status": "success",
  "task_list": ["执行加法计算"],
  "data": {
    "operation": "add",
    "operand1": 123,
    "operand2": 456,
    "expression": "123 + 456"
  },
  "next_agent": "none",
  "agent_selection_reason": "执行数学计算",
  "message": "正在计算..."
}
```
"""

# 数据字段：描述data字段的结构
data_fields = """
{
  "operation": "string      // 运算类型",
  "operand1": "number       // 第一个操作数",
  "operand2": "number       // 第二个操作数",
  "expression": "string     // 完整表达式"
}
"""

# ================================
# 第二步：创建Agent类
# ================================

class DemoAgent(Agent):
    """
    Demo Agent - 数学计算Agent

    这个Agent展示了如何创建一个功能完整的自定义Agent：
    1. 继承Agent基类
    2. 在__init__中配置Agent信息
    3. 实现run方法处理具体逻辑
    4. 返回处理结果
    """

    def __init__(self):
        # 初始化Agent基类，配置基本属性
        super().__init__(
            name="demo_agent",                    # Agent名称（唯一标识）
            description="执行数学计算，包括加减乘除等基础运算",  # 功能描述
            handles=[                             # 处理的关键词列表
                "计算", "加", "减", "乘", "除",
                "数学", "运算", "求和"
            ],
            parameters={                          # 参数说明
                "expression": "需要计算的表达式"
            }
        )

        # 创建提示词模板
        self.prompt_template = PromptTemplate(
            system_instructions=system_instructions,
            available_agents=None,                # 不需要知道其他Agent
            core_instructions=core_instructions,
            data_fields=data_fields
        )

        logger.info(f"✓ {self.name} 初始化成功")

    def run(self, message: Message) -> Message:
        """
        Agent的核心处理逻辑

        Args:
            message: 输入消息，包含：
                - message.data: LLM解析后的数据
                - message.task_list: 任务列表
                - 等其他字段...

        Returns:
            Message: 处理结果消息

        注意：
            1. 你可以返回Message对象（完全自定义）
            2. 或返回Dict对象（系统自动封装）
            3. 或返回其他类型（系统包装到data中）
        """

        # 从LLM解析的数据中提取信息
        data = message.data or {}
        operation = data.get("operation", "")
        operand1 = data.get("operand1", 0)
        operand2 = data.get("operand2", 0)
        expression = data.get("expression", "")

        logger.info(f"{self.name} 执行计算: {expression}")

        # 执行计算逻辑
        result = 0
        try:
            if operation == "add":
                result = operand1 + operand2
            elif operation == "subtract":
                result = operand1 - operand2
            elif operation == "multiply":
                result = operand1 * operand2
            elif operation == "divide":
                if operand2 != 0:
                    result = operand1 / operand2
                else:
                    raise ValueError("除数不能为零")
            else:
                result = "未知运算类型"
        except Exception as e:
            logger.error(f"计算错误: {e}")
            return Message(
                status="error",
                task_list=message.task_list or ["执行计算"],
                data={"error": str(e)},
                next_agent="none",
                agent_selection_reason="计算失败",
                message=f"计算错误: {e}"
            )

        # 构建返回结果
        # 方式1：返回完整的Message对象（完全控制）
        return Message(
            status="success",
            task_list=["执行计算", "返回结果"],
            data={
                "operation": operation,
                "expression": expression,
                "result": result,
                "formatted": f"{expression} = {result}"
            },
            next_agent="none",  # 计算完成，结束流程
            agent_selection_reason="计算已完成",
            message=f"计算完成：{expression} = {result}"
        )

        # 方式2：返回字典（系统自动封装）
        # return {
        #     "operation": operation,
        #     "expression": expression,
        #     "result": result,
        #     "formatted": f"{expression} = {result}"
        # }

        # 方式3：返回简单值（系统包装）
        # return result


# ================================
# 最佳实践提示
# ================================

"""
📝 创建自定义Agent的建议：

1. **命名规范**
   - 文件名：xxx_agent.py（如math_agent.py）
   - 类名：XxxAgent（如MathAgent）
   - Agent名称：xxx_agent（如math_agent）

2. **提示词设计**
   - system_instructions：定义角色和行为准则
   - core_instructions：具体的任务执行步骤
   - data_fields：明确说明返回数据的结构

3. **错误处理**
   - 在run方法中使用try-except捕获异常
   - 返回status="error"的Message表示失败
   - 在message字段中提供清晰的错误信息

4. **数据返回**
   - 简单场景：返回字典或基本类型
   - 复杂场景：返回完整的Message对象
   - 系统会自动标准化你的返回值

5. **Agent协作**
   - 如果需要继续处理，设置next_agent="general_agent"
   - 如果任务完成，设置next_agent="none"
   - 可以指定其他Agent名称进行任务传递

6. **日志记录**
   - 使用logger记录关键操作
   - 便于调试和问题追踪
   - 在生产环境查看运行状态

7. **参数验证**
   - 验证输入数据的完整性
   - 处理边界情况（如除零）
   - 提供友好的错误提示

8. **测试建议**
   - 先在CLI模式测试：python main.py "你的问题"
   - 查看日志输出验证逻辑
   - 使用Web界面测试交互效果
"""
