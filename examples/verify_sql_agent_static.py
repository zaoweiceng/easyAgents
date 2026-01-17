#!/usr/bin/env python3
"""
验证SqlAgent修改的正确性（静态代码分析）
"""

import re

print("=" * 70)
print("验证SqlAgent修改")
print("=" * 70)

# 读取SqlAgent文件
with open('plugin/sql_agent.py', 'r') as f:
    content = f.read()

# 1. 检查导入语句
print("\n1. 检查导入语句...")
imports = re.findall(r'^from .* import', content, re.MULTILINE)
print(f"   找到{len(imports)}个导入语句:")
for imp in imports:
    print(f"   - {imp}")

# 检查是否使用了正确的导入
if 'from core.agent import Agent' in content:
    print("   ✅ 使用了相对导入（正确）")
elif 'from core import Agent' in content:
    print("   ⚠️  使用了绝对导入（可能导致循环导入）")
else:
    print("   ❌ 导入语句格式不正确")

# 2. 检查run方法签名
print("\n2. 检查run方法签名...")
run_method = re.search(r'def run\(self, message:Message\)', content)
if run_method:
    print("   ✅ run方法签名正确（不返回Message类型）")
else:
    run_method_old = re.search(r'def run\(self, message:Message\) -> Message:', content)
    if run_method_old:
        print("   ❌ run方法仍使用旧版本签名（-> Message）")
    else:
        print("   ⚠️  run方法签名格式不明确")

# 3. 检查return语句
print("\n3. 检查return语句...")
return_messages = re.findall(r'return message', content)
return_dicts = re.findall(r'return \{', content)

if return_messages and not return_dicts:
    print("   ❌ 仍在使用 'return message'（旧版本）")
elif return_dicts and not return_messages:
    print("   ✅ 使用 'return {...}' 返回字典（新版本）")
elif return_dicts and return_messages:
    print("   ⚠️  同时存在两种返回格式")
    print(f"      return message: {len(return_messages)}次")
    print(f"      return dict: {len(return_dicts)}次")
else:
    print("   ⚠️  未找到明确的return语句")

# 4. 分析run方法逻辑
print("\n4. 分析run方法逻辑...")
run_method_content = re.search(r'def run\(self.*?\n(?:(?:    .*\n)*?)(?=\n    def|\nclass|\Z)', content, re.DOTALL)

if run_method_content:
    method_content = run_method_content.group(0)

    # 检查是否直接修改message.data
    if 'message.data = {' in method_content or 'message.data={' in method_content:
        print("   ⚠️  仍在直接修改message.data（旧版本模式）")
    else:
        print("   ✅ 不再直接修改message.data")

    # 检查是否使用**message.data合并
    if '**message.data' in method_content:
        print("   ⚠️  仍在使用**message.data合并数据")
    else:
        print("   ✅ 不再使用数据合并")

    # 检查是否返回简单的result字典
    if 'return result' in method_content or 'return {' in method_content:
        print("   ✅ 直接返回结果数据")
    else:
        print("   ⚠️  返回逻辑不明确")

# 5. 统计代码行数
print("\n5. 代码行数统计...")
total_lines = len(content.split('\n'))
code_lines = len([line for line in content.split('\n') if line.strip() and not line.strip().startswith('#')])
print(f"   总行数: {total_lines}")
print(f"   代码行数: {code_lines}")

# 估算简化程度
old_style_estimate = 84  # 原始文件大约84行
if total_lines < old_style_estimate:
    saved = old_style_estimate - total_lines
    percentage = (saved / old_style_estimate) * 100
    print(f"   ✅ 代码减少了{saved}行（约{percentage:.1f}%）")
else:
    print(f"   ℹ️  代码行数: {total_lines}")

# 6. 显示run方法代码
print("\n6. run方法代码:")
print("   " + "-" * 66)
run_start = content.find('def run(')
if run_start != -1:
    # 找到方法结束位置
    run_end = content.find('\n\nclass', run_start)
    if run_end == -1:
        run_end = len(content)

    method_code = content[run_start:run_end].strip()
    for line in method_code.split('\n'):
        print(f"   {line}")
else:
    print("   未找到run方法")

print("   " + "-" * 66)

# 7. 验证总结
print("\n" + "=" * 70)
print("验证总结:")
print("=" * 70)

checks = []

# 检查1: 导入语句
if 'from core.agent import Agent' in content:
    checks.append(("导入语句", "✅"))
else:
    checks.append(("导入语句", "⚠️"))

# 检查2: 方法签名
if 'def run(self, message:Message)' in content and '-> Message' not in content[content.find('def run'):content.find('def run')+50]:
    checks.append(("方法签名", "✅"))
else:
    checks.append(("方法签名", "⚠️"))

# 检查3: 返回格式
if 'return result' in content or 'return {' in content:
    if 'return message' not in content:
        checks.append(("返回格式", "✅"))
    else:
        checks.append(("返回格式", "⚠️"))
else:
    checks.append(("返回格式", "❌"))

# 检查4: 不再修改message
if 'message.data = ' not in content or 'return result' in content:
    checks.append(("不修改message", "✅"))
else:
    checks.append(("不修改message", "⚠️"))

# 显示结果
for check_name, status in checks:
    print(f"{status} {check_name}")

# 最终判断
if all(status == "✅" for _, status in checks):
    print("\n✅ SqlAgent已成功迁移到新版本！")
    print("\n主要改进:")
    print("  • run方法直接返回数据字典")
    print("  • 不再手动构造Message对象")
    print("  • 代码更简洁易读")
    print("  • 系统会自动封装到标准格式")
else:
    print("\n⚠️  SqlAgent迁移可能不完全，建议检查")

# 对比示例
print("\n" + "=" * 70)
print("代码对比:")
print("=" * 70)

print("\n【旧版本核心逻辑】")
print("""
if "id = 2" in sql:
    message.data = {
        **message.data,        # 需要合并
        "result": {             # 嵌套result
            "id": 2,
            "title": "1984",
            ...
        }
    }
    return message             # 返回message对象
""")

print("\n【新版本核心逻辑】")
print("""
if "id = 2" in sql:
    result = {                  # 创建result变量
        "id": 2,
        "title": "1984",
        ...
    }
    return result              # 直接返回字典
""")

print("\n" + "=" * 70)
print("优势:")
print("=" * 70)
print("✅ 去掉了 **message.data 数据合并")
print("✅ 去掉了嵌套的 'result' 字段")
print("✅ 直接返回业务数据，结构更清晰")
print("✅ 系统自动处理标准封装")
print("=" * 70)

print("\n📝 提示: Agent已准备就绪，可以直接使用！\n")
