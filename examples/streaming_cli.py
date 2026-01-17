#!/usr/bin/env python3
"""
easyAgent CLI流式输出示例

演示如何使用流式响应功能实时显示Agent处理过程
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import AgentManager
from config import get_config


def main():
    """主函数"""
    # 加载配置
    config = get_config()

    # 创建AgentManager
    agent_manager = AgentManager(
        plugin_src=config.get_agent_config()['plugin_src'],
        base_url=config.get_llm_config()['base_url'],
        api_key=config.get_llm_config()['api_key'],
        model_name=config.get_llm_config()['model_name']
    )

    # 获取查询
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        query = "abc写了一本书，帮我查询一下这本书的出版信息"

    print("=" * 70)
    print(f"查询: {query}")
    print("=" * 70)

    # 流式输出
    current_agent = None
    full_content = []

    for event in agent_manager(query, stream=True):
        event_type = event["type"]

        if event_type == "delta":
            # 实时显示LLM生成的内容
            content = event["data"]["content"]
            finish_reason = event["data"]["finish_reason"]

            if content:
                print(content, end="", flush=True)
                full_content.append(content)

            if finish_reason:
                print()  # 换行

        elif event_type == "agent_start":
            current_agent = event["data"]["agent_name"]
            agent_desc = event["data"]["agent_description"]
            print(f"\n▶ [{current_agent}] {agent_desc}")

        elif event_type == "agent_end":
            agent_name = event["data"]["agent_name"]
            status = event["data"]["status"]
            next_agent = event["data"]["next_agent"]
            print(f"  ✓ {agent_name} 完成 (状态: {status})")
            if next_agent != "none":
                print(f"  → 下一步: {next_agent}")

        elif event_type == "message":
            # 完整消息（可用于调试或保存）
            pass

        elif event_type == "error":
            error_msg = event["data"]["error_message"]
            recoverable = event["data"].get("recoverable", False)
            print(f"\n✗ 错误: {error_msg}")
            if not recoverable:
                print("  (致命错误，终止处理)")
                break

        elif event_type == "metadata":
            # 元数据信息
            stage = event["metadata"].get("stage", "")
            if stage == "init":
                print(f"\n开始处理查询...")
            elif stage == "end":
                print(f"\n处理完成!")
            elif "duration_ms" in event["data"]:
                duration = event["data"]["duration_ms"]
                print(f"  ⏱ 耗时: {duration}ms")

    print("\n" + "=" * 70)
    print("完整内容:")
    print("".join(full_content))
    print("=" * 70)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n用户中断，退出...")
        sys.exit(0)
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
