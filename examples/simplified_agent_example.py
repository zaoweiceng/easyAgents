#!/usr/bin/env python3
"""
简化的Agent实现示例

演示如何使用新的自动封装功能，让Agent的实现更加简洁
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.agent import Agent
from core.base_model import Message
from config import get_config


# ============================================================================
# 示例1: 最简单的Agent - 返回字典
# ============================================================================

class SimpleSqlAgent(Agent):
    """简单的SQL查询Agent - 返回字典格式"""

    def __init__(self):
        super().__init__(
            name="simple_sql_agent",
            description="执行SQL查询并返回结果",
            handles=["SQL查询", "数据库查询", "执行SQL"]
        )

    def run(self, message: Message):
        """
        直接返回字典，系统会自动封装成Message

        返回的字典会被自动放到Message.data中
        """
        # 模拟SQL查询
        sql = message.data.get("sql", "SELECT * FROM books LIMIT 10")

        # 模拟查询结果
        result = {
            "sql": sql,
            "rows": [
                {"id": 1, "title": "Python编程", "author": "张三"},
                {"id": 2, "title": "机器学习", "author": "李四"}
            ],
            "count": 2
        }

        # 直接返回字典 - 系统会自动封装！
        return result


# ============================================================================
# 示例2: 返回简单值的Agent
# ============================================================================

class CalculatorAgent(Agent):
    """计算器Agent - 返回简单值"""

    def __init__(self):
        super().__init__(
            name="calculator_agent",
            description="执行数学计算",
            handles=["计算", "数学运算"]
        )

    def run(self, message: Message):
        """
        返回简单值，系统会自动包装到{"result": 返回值}
        """
        # 获取计算表达式
        expression = message.data.get("expression", "2 + 2")

        try:
            # 简单计算（仅演示，生产环境需要更安全的实现）
            result = eval(expression)
            # 直接返回数值
            return result
        except Exception as e:
            return f"计算错误: {str(e)}"


# ============================================================================
# 示例3: 返回None的Agent
# ============================================================================

class LogAgent(Agent):
    """日志记录Agent - 返回None"""

    def __init__(self):
        super().__init__(
            name="log_agent",
            description="记录日志信息",
            handles=["记录日志", "保存日志"]
        )

    def run(self, message: Message):
        """
        返回None，系统会自动设置next_agent="none"结束流程
        """
        log_data = message.data.get("log", "")

        # 模拟写入日志
        print(f"[LOG] {log_data}")

        # 返回None表示完成，不需要进一步处理
        return None


# ============================================================================
# 示例4: 完全控制的高级Agent
# ============================================================================

class AdvancedAgent(Agent):
    """高级Agent - 完全控制返回格式"""

    def __init__(self):
        super().__init__(
            name="advanced_agent",
            description="完全自定义返回格式的Agent",
            handles=["高级处理"]
        )

    def run(self, message: Message):
        """
        返回Message对象，完全自定义返回格式
        """
        # 执行复杂逻辑
        result = self._complex_operation(message.data)

        # 完全自定义Message格式
        return Message(
            status="success",
            task_list=["任务1", "任务2", "任务3"],
            data={"processed_data": result},
            next_agent="another_agent",  # 指定下一个Agent
            agent_selection_reason="需要继续处理",
            message="高级处理完成"
        )

    def _complex_operation(self, data):
        """复杂操作逻辑"""
        return {"key": "value"}


# ============================================================================
# 对比：旧的实现方式 vs 新的简化方式
# ============================================================================

class OldStyleAgent(Agent):
    """旧式Agent实现 - 需要手动构造Message"""

    def __init__(self):
        super().__init__(
            name="old_style_agent",
            description="旧式实现",
            handles=["旧式"]
        )

    def run(self, message: Message):
        """需要手动构造完整的Message对象"""
        result = {"data": "some result"}

        # 必须手动构造Message - 繁琐！
        return Message(
            status="success",
            task_list=message.task_list or ["任务"],
            data=result,
            next_agent="general_agent",
            agent_selection_reason="处理完成",
            message="旧式Agent处理完成"
        )


class NewStyleAgent(Agent):
    """新式Agent实现 - 自动封装"""

    def __init__(self):
        super().__init__(
            name="new_style_agent",
            description="新式简化实现",
            handles=["新式"]
        )

    def run(self, message: Message):
        """只需要返回数据，系统自动封装"""
        result = {"data": "some result"}

        # 直接返回数据 - 简洁！
        return result


# ============================================================================
# 测试代码
# ============================================================================

def test_agents():
    """测试各种Agent实现"""

    print("=" * 70)
    print("简化的Agent实现示例")
    print("=" * 70)

    # 创建测试消息
    test_message = Message(
        status="success",
        task_list=["测试任务"],
        data={"test": "data"},
        next_agent="test_agent",
        agent_selection_reason="测试"
    )

    # 测试1: 简单的字典返回
    print("\n1. 测试SimpleSqlAgent（返回字典）:")
    sql_agent = SimpleSqlAgent()
    result1 = sql_agent(test_message)
    print(f"   status: {result1.status}")
    print(f"   task_list: {result1.task_list}")
    print(f"   data: {result1.data}")
    print(f"   next_agent: {result1.next_agent}")
    print(f"   message: {result1.message}")

    # 测试2: 简单值返回
    print("\n2. 测试CalculatorAgent（返回简单值）:")
    calc_agent = CalculatorAgent()
    test_message2 = Message(
        status="success",
        task_list=[],
        data={"expression": "100 + 200"},
        next_agent="calculator_agent",
        agent_selection_reason="测试"
    )
    result2 = calc_agent(test_message2)
    print(f"   status: {result2.status}")
    print(f"   data: {result2.data}")
    print(f"   next_agent: {result2.next_agent}")

    # 测试3: None返回
    print("\n3. 测试LogAgent（返回None）:")
    log_agent = LogAgent()
    test_message3 = Message(
        status="success",
        task_list=[],
        data={"log": "这是一条测试日志"},
        next_agent="log_agent",
        agent_selection_reason="测试"
    )
    result3 = log_agent(test_message3)
    print(f"   status: {result3.status}")
    print(f"   data: {result3.data}")
    print(f"   next_agent: {result3.next_agent}")
    print(f"   message: {result3.message}")

    # 测试4: 完全自定义
    print("\n4. 测试AdvancedAgent（完全自定义）:")
    adv_agent = AdvancedAgent()
    result4 = adv_agent(test_message)
    print(f"   task_list: {result4.task_list}")
    print(f"   next_agent: {result4.next_agent}")

    print("\n" + "=" * 70)
    print("✅ 所有测试完成！")
    print("=" * 70)


# ============================================================================
# 集成测试 - 与AgentManager一起使用
# ============================================================================

def test_with_agent_manager():
    """测试与AgentManager的集成"""

    print("\n" + "=" * 70)
    print("与AgentManager集成说明")
    print("=" * 70)

    # 注意：这只是演示，实际使用时需要确保Agent已注册到plugin目录
    print("\n提示：将简化后的Agent放到plugin/agents/目录下即可使用")
    print("系统会自动封装返回数据到标准Message格式")

    # 示例：plugin/agents/simple_sql_agent.py
    example_code = '''
# plugin/agents/simple_sql_agent.py

from core.agent import Agent
from core.base_model import Message

class SimpleSqlAgent(Agent):
    def __init__(self):
        super().__init__(
            name="simple_sql_agent",
            description="SQL查询Agent",
            handles=["SQL查询", "数据库查询"]
        )

    def run(self, message: Message):
        """只需要返回数据即可！"""
        sql = message.data.get("sql", "SELECT * FROM books")

        # 模拟查询
        result = {
            "sql": sql,
            "rows": [{"id": 1, "name": "Book 1"}],
            "count": 1
        }

        # 直接返回 - 系统自动封装
        return result
'''

    print("\n示例代码:")
    print(example_code)


if __name__ == "__main__":
    test_agents()
    test_with_agent_manager()

    print("\n" + "=" * 70)
    print("总结:")
    print("=" * 70)
    print("✅ 返回字典：自动封装到data，有内容时继续处理")
    print("✅ 返回简单值：自动包装到{'result': value}，直接结束")
    print("✅ 返回None：设置data=None，直接结束")
    print("✅ 返回Message：完全自定义（高级用法）")
    print("\n推荐使用：返回字典或简单值，让系统自动处理！")
    print("=" * 70)
