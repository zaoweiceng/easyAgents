#!/usr/bin/env python3
"""
验证SqlAgent修改的正确性
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 使用importlib直接加载，避免循环导入
import importlib.util

def load_module_directly(module_name, file_path):
    """直接从文件加载模块，避免循环导入"""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

print("=" * 70)
print("验证SqlAgent修改")
print("=" * 70)

# 1. 加载必要的依赖
print("\n1. 加载依赖模块...")
base_model = load_module_directly('base_model', 'core/base_model.py')
agent_module = load_module_directly('agent_module', 'core/agent.py')
Message = base_model.Message
print("   ✅ 依赖加载成功")

# 2. 加载SqlAgent
print("\n2. 加载SqlAgent...")
sql_agent_module = load_module_directly('sql_agent', 'plugin/sql_agent.py')
SqlAgent = sql_agent_module.SqlAgent
print("   ✅ SqlAgent加载成功")

# 3. 创建Agent实例
print("\n3. 创建Agent实例...")
agent = SqlAgent()
print(f"   Agent名称: {agent.name}")
print(f"   Agent描述: {agent.description}")
print(f"   Agent处理关键词: {agent.handles}")
print("   ✅ Agent创建成功")

# 4. 测试run方法
print("\n4. 测试run方法...")

# 创建测试消息
test_message = Message(
    status="success",
    task_list=["查询图书"],
    data={"sql": "SELECT * FROM books WHERE id = 2"},
    next_agent="sql_agent",
    agent_selection_reason="测试"
)

# 调用run方法
result = agent.run(test_message)

print(f"   返回类型: {type(result).__name__}")
print(f"   返回内容: {result}")
print(f"   图书名: {result.get('title', 'N/A')}")
print(f"   作者: {result.get('author', 'N/A')}")

# 验证返回值
assert isinstance(result, dict), "run方法应该返回字典"
assert result["title"] == "1984", "书名应该是1984"
assert "author" in result, "应该包含作者字段"
print("   ✅ run方法返回正确")

# 5. 验证自动封装
print("\n5. 验证自动封装功能...")
from agent_module import normalize_agent_output

normalized = normalize_agent_output(result, test_message, agent.name)
print(f"   封装后类型: {type(normalized).__name__}")
print(f"   status: {normalized.status}")
print(f"   task_list: {normalized.task_list}")
print(f"   data: {normalized.data}")
print(f"   next_agent: {normalized.next_agent}")
print(f"   message: {normalized.message}")

assert isinstance(normalized, Message), "应该封装为Message"
assert normalized.status == "success", "状态应该是success"
assert normalized.data["title"] == "1984", "数据应该保持"
assert normalized.next_agent == "general_agent", "有数据应该继续处理"
print("   ✅ 自动封装正确")

# 6. 测试不同查询
print("\n6. 测试不同查询场景...")

test_cases = [
    ("SELECT * FROM books WHERE id = 2", "1984", "乔治·奥威尔"),
    ("SELECT * FROM books WHERE title LIKE '%呼啸山庄%'", "呼啸山庄", "abc"),
    ("SELECT * FROM books WHERE title = '未知'", "未知", "未知"),
]

for i, (sql, expected_title, expected_author) in enumerate(test_cases, 1):
    msg = Message(
        status="success",
        task_list=[],
        data={"sql": sql},
        next_agent="sql_agent",
        agent_selection_reason="测试"
    )
    result = agent.run(msg)

    print(f"   测试{i}: {sql[:40]}...")
    print(f"      返回: {result.get('title')} - {result.get('author')}")
    assert result.get("title") == expected_title, f"测试{i}失败"
    print(f"      ✅ 通过")

print("\n" + "=" * 70)
print("✅ 所有验证通过！")
print("=" * 70)

# 对比展示
print("\n" + "=" * 70)
print("修改对比:")
print("=" * 70)

print("\n【修改前】返回Message对象:")
print("""
def run(self, message: Message) -> Message:
    sql = message.data.get("sql", "")

    if "id = 2" in sql:
        message.data = {
            **message.data,  # 需要合并原有数据
            "result": {...}   # 嵌套result字段
        }
        return message  # 返回整个message对象
""")

print("\n【修改后】直接返回数据:")
print("""
def run(self, message: Message):
    sql = message.data.get("sql", "")

    if "id = 2" in sql:
        return {  # 直接返回结果字典
            "id": 2,
            "title": "1984",
            "author": "乔治·奥威尔",
            ...
        }  # 系统自动封装到Message.data中
""")

print("\n" + "=" * 70)
print("改进效果:")
print("=" * 70)
print("✅ 代码更简洁：减少约50%代码")
print("✅ 逻辑更清晰：直接返回业务数据")
print("✅ 更易维护：不需要处理Message构造")
print("✅ 自动封装：系统自动处理标准格式")
print("✅ 智能决策：自动判断是否继续处理")
print("=" * 70)

print("\n🎉 SqlAgent成功迁移到新版本！\n")
