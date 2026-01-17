"""
easyAgent MCP集成使用示例
演示如何配置和使用MCP协议支持的Agent
"""

import os
import json
from core import AgentManager


def example_1_single_mcp_server():
    """示例1: 使用单个MCP服务器"""
    print("\n" + "="*50)
    print("示例1: 使用单个MCP服务器（文件系统）")
    print("="*50)

    # 配置MCP服务器
    mcp_configs = [
        {
            "name": "filesystem",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem", os.getcwd()],
            "env": {},
            "description": "文件系统访问"
        }
    ]

    # 创建AgentManager
    agent_manager = AgentManager(
        plugin_src="plugin",
        base_url="http://127.0.0.1:9999/v1",
        api_key="None",
        model_name="openai/gpt-oss-20b",
        mcp_configs=mcp_configs
    )

    # 查看已加载的Agent
    print("\n已加载的Agent:")
    print(json.dumps(agent_manager.agents.to_json(), indent=2, ensure_ascii=False))

    # 使用MCP工具
    query = "帮我列出当前目录的所有Python文件"
    print(f"\n用户查询: {query}")

    response = agent_manager(query)

    print("\n响应:")
    for msg in response:
        if msg.get("message"):
            print(f"{msg['role']}: {msg['message']}")


def example_2_multiple_mcp_servers():
    """示例2: 使用多个MCP服务器"""
    print("\n" + "="*50)
    print("示例2: 使用多个MCP服务器")
    print("="*50)

    # 配置多个MCP服务器
    mcp_configs = [
        {
            "name": "filesystem",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem", os.getcwd()],
            "env": {}
        },
        {
            "name": "memory",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-memory"],
            "env": {}
        }
    ]

    # 创建AgentManager
    agent_manager = AgentManager(
        plugin_src="plugin",
        base_url="http://127.0.0.1:9999/v1",
        api_key="None",
        model_name="openai/gpt-oss-20b",
        mcp_configs=mcp_configs
    )

    print("\n已加载的Agent（整合多个MCP服务器）:")
    print(json.dumps(agent_manager.agents.to_json(), indent=2, ensure_ascii=False))

    # 使用多个MCP工具
    query = "帮我查看main.py文件的内容，并保存到记忆中"
    print(f"\n用户查询: {query}")

    response = agent_manager(query)

    print("\n响应:")
    for msg in response:
        if msg.get("message"):
            print(f"{msg['role']}: {msg['message']}")


def example_3_mcp_with_github():
    """示例3: 使用GitHub MCP服务器"""
    print("\n" + "="*50)
    print("示例3: 使用GitHub MCP服务器")
    print("="*50)

    # 注意：需要设置GITHUB_TOKEN环境变量
    github_token = os.getenv("GITHUB_TOKEN")

    if not github_token:
        print("\n⚠️  警告: 未设置GITHUB_TOKEN环境变量")
        print("请先设置: export GITHUB_TOKEN=your-token")
        return

    mcp_configs = [
        {
            "name": "github",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-github"],
            "env": {
                "GITHUB_TOKEN": github_token
            }
        }
    ]

    agent_manager = AgentManager(
        plugin_src="plugin",
        base_url="http://127.0.0.1:9999/v1",
        api_key="None",
        model_name="openai/gpt-oss-20b",
        mcp_configs=mcp_configs
    )

    query = "帮我查看anthropic/claude-code仓库的最新issue"
    print(f"\n用户查询: {query}")

    response = agent_manager(query)

    print("\n响应:")
    for msg in response:
        if msg.get("message"):
            print(f"{msg['role']}: {msg['message']}")


def example_4_load_config_from_file():
    """示例4: 从配置文件加载MCP配置"""
    print("\n" + "="*50)
    print("示例4: 从配置文件加载MCP配置")
    print("="*50)

    config_file = "mcp_config.json"

    if not os.path.exists(config_file):
        print(f"\n⚠️  配置文件 {config_file} 不存在")
        print(f"请从 mcp_config.example.json 复制并修改")
        return

    # 加载配置
    with open(config_file, 'r') as f:
        config = json.load(f)

    mcp_configs = config.get("mcp_servers", [])

    print(f"\n从配置文件加载了 {len(mcp_configs)} 个MCP服务器")

    # 创建AgentManager
    agent_manager = AgentManager(
        plugin_src="plugin",
        base_url="http://127.0.0.1:9999/v1",
        api_key="None",
        model_name="openai/gpt-oss-20b",
        mcp_configs=mcp_configs
    )

    # 使用MCP工具
    query = "你好，请介绍一下你有哪些能力？"
    print(f"\n用户查询: {query}")

    response = agent_manager(query)

    print("\n响应:")
    for msg in response:
        if msg.get("message"):
            print(f"{msg['role']}: {msg['message']}")


def example_5_programmatic_mcp_agent():
    """示例5: 编程方式创建MCP Agent"""
    print("\n" + "="*50)
    print("示例5: 编程方式创建MCP Agent")
    print("="*50)

    from core.agents.mcp_agent import MCPAgent

    # 直接创建MCP Agent
    mcp_agent = MCPAgent(
        name="filesystem",
        mcp_command="npx",
        mcp_args=["-y", "@modelcontextprotocol/server-filesystem", os.getcwd()],
        description="我的文件系统Agent",
        auto_connect=True
    )

    print(f"\nAgent名称: {mcp_agent.name}")
    print(f"Agent描述: {mcp_agent.description}")
    print(f"可用工具数量: {len(mcp_agent.tools)}")
    print(f"\n可用工具:")
    for tool in mcp_agent.tools[:5]:  # 显示前5个工具
        print(f"  - {tool.get('name')}: {tool.get('description', '无描述')}")

    # 可以手动调用工具
    print("\n直接调用工具示例:")
    try:
        result = mcp_agent.sync_client.call_tool(
            "read_file",
            {
                "path": "README.md"
            }
        )
        print(f"read_file结果: {json.dumps(result, indent=2, ensure_ascii=False)[:200]}...")
    except Exception as e:
        print(f"调用失败: {e}")

    # 关闭连接
    mcp_agent.close()


def example_6_custom_mcp_server():
    """示例6: 使用自定义MCP服务器"""
    print("\n" + "="*50)
    print("示例6: 使用自定义MCP服务器")
    print("="*50)

    # 假设你有一个自定义的Python MCP服务器
    mcp_configs = [
        {
            "name": "my_custom_server",
            "command": "python",
            "args": ["examples/custom_mcp_server.py"],
            "env": {
                "CUSTOM_DATA": "/path/to/data"
            }
        }
    ]

    print("\n注意: 需要先创建 custom_mcp_server.py")
    print("请参考 MCP 文档创建自定义服务器")


def main():
    """主函数"""
    print("\n" + "="*60)
    print("easyAgent MCP集成使用示例")
    print("="*60)

    import sys

    if len(sys.argv) > 1:
        example_num = sys.argv[1]
        examples = {
            "1": example_1_single_mcp_server,
            "2": example_2_multiple_mcp_servers,
            "3": example_3_mcp_with_github,
            "4": example_4_load_config_from_file,
            "5": example_5_programmatic_mcp_agent,
            "6": example_6_custom_mcp_server
        }

        if example_num in examples:
            examples[example_num]()
        else:
            print(f"\n未知示例: {example_num}")
            print("可用示例: 1-6")
    else:
        print("\n用法: python mcp_example.py <示例编号>")
        print("\n可用示例:")
        print("  1 - 使用单个MCP服务器（文件系统）")
        print("  2 - 使用多个MCP服务器")
        print("  3 - 使用GitHub MCP服务器")
        print("  4 - 从配置文件加载MCP配置")
        print("  5 - 编程方式创建MCP Agent")
        print("  6 - 使用自定义MCP服务器")

        # 默认运行示例1
        print("\n运行示例1...")
        example_1_single_mcp_server()


if __name__ == "__main__":
    main()
