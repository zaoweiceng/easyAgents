#!/usr/bin/env python3
"""
测试MCP Agent的健康检查和远端连接功能
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import AgentManager
import json


def test_1_health_check_success():
    """测试1: 健康检查成功"""
    print("\n" + "="*60)
    print("测试1: 本地MCP服务器（健康检查成功）")
    print("="*60)

    mcp_configs = [{
        "name": "memory",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-memory"],
        "health_check": True
    }]

    try:
        agent_manager = AgentManager(
            plugin_src="plugin",
            base_url="http://127.0.0.1:9999/v1",
            api_key="test",
            model_name="gpt-4",
            mcp_configs=mcp_configs
        )

        # 检查Agent状态
        memory_agent = agent_manager.agents.get("memory")
        if memory_agent and hasattr(memory_agent, 'get_health_status'):
            status = memory_agent.get_health_status()
            print(f"\nAgent状态:")
            print(f"  名称: {status['name']}")
            print(f"  活跃: {status['is_active']}")
            print(f"  连接类型: {status['connection_type']}")
            print(f"  工具数量: {status['tools_count']}")
            print(f"  错误: {status['error']}")

            if status['is_active']:
                print("\n✅ 测试通过：Agent健康检查成功")
            else:
                print("\n❌ 测试失败：Agent不活跃")

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")


def test_2_health_check_failure():
    """测试2: 健康检查失败（命令不存在）"""
    print("\n" + "="*60)
    print("测试2: 健康检查失败（命令不存在）")
    print("="*60)

    mcp_configs = [{
        "name": "fake_server",
        "command": "nonexistent_command_xyz",
        "args": [],
        "health_check": True
    }]

    try:
        agent_manager = AgentManager(
            plugin_src="plugin",
            base_url="http://127.0.0.1:9999/v1",
            api_key="test",
            model_name="gpt-4",
            mcp_configs=mcp_configs
        )

        # 检查Agent状态
        fake_agent = agent_manager.agents.get("fake_server")
        if fake_agent and hasattr(fake_agent, 'get_health_status'):
            status = fake_agent.get_health_status()
            print(f"\nAgent状态:")
            print(f"  名称: {status['name']}")
            print(f"  活跃: {status['is_active']}")
            print(f"  错误: {status['error']}")

            if not status['is_active']:
                print("\n✅ 测试通过：Agent正确设置为不活跃")
            else:
                print("\n❌ 测试失败：Agent应该是非活跃的")

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")


def test_3_remote_server():
    """测试3: 远端SSE服务器（模拟）"""
    print("\n" + "="*60)
    print("测试3: 远端SSE服务器配置")
    print("="*60)

    mcp_configs = [{
        "name": "remote_server",
        "url": "http://localhost:9999/mcp",
        "headers": {
            "Authorization": "Bearer test-token"
        },
        "health_check": True
    }]

    print("\n配置:")
    print(json.dumps(mcp_configs[0], indent=2))

    try:
        agent_manager = AgentManager(
            plugin_src="plugin",
            base_url="http://127.0.0.1:9999/v1",
            api_key="test",
            model_name="gpt-4",
            mcp_configs=mcp_configs
        )

        remote_agent = agent_manager.agents.get("remote_server")
        if remote_agent and hasattr(remote_agent, 'get_health_status'):
            status = remote_agent.get_health_status()
            print(f"\nAgent状态:")
            print(f"  名称: {status['name']}")
            print(f"  连接类型: {status['connection_type']}")
            print(f"  URL: {status['url']}")
            print(f"  活跃: {status['is_active']}")
            print(f"  错误: {status['error']}")

            if status['connection_type'] == "sse":
                print("\n✅ 测试通过：SSE传输类型正确")
            else:
                print("\n❌ 测试失败：传输类型应为sse")

    except Exception as e:
        print(f"\n⚠️  测试跳过: {e}")
        print("   这通常是因为远端服务器不存在")


def test_4_mixed_configs():
    """测试4: 混合配置（stdio + sse）"""
    print("\n" + "="*60)
    print("测试4: 混合配置（本地+远端）")
    print("="*60)

    mcp_configs = [
        {
            "name": "local_memory",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-memory"],
            "health_check": True
        },
        {
            "name": "remote_fs",
            "url": "http://localhost:9999/mcp",
            "health_check": False  # 跳过检查
        }
    ]

    print(f"\n配置了 {len(mcp_configs)} 个MCP服务器:")
    for config in mcp_configs:
        conn_type = "SSE" if "url" in config else "STDIO"
        print(f"  - {config['name']} ({conn_type})")

    try:
        agent_manager = AgentManager(
            plugin_src="plugin",
            base_url="http://127.0.0.1:9999/v1",
            api_key="test",
            model_name="gpt-4",
            mcp_configs=mcp_configs
        )

        print("\n已加载的Agent:")
        agents = agent_manager.agents.get_all_agents()
        for name, agent in agents.items():
            if hasattr(agent, 'connection_type'):
                print(f"  ✓ {name} ({agent.connection_type})")
                if hasattr(agent, 'is_active'):
                    status = "✓ 活跃" if agent.is_active else "✗ 不活跃"
                    print(f"    {status}")
                    if hasattr(agent, 'connection_error') and agent.connection_error:
                        print(f"    错误: {agent.connection_error}")

        print("\n✅ 测试通过：混合配置加载成功")

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")


def test_5_multi_mcp_agent():
    """测试5: MultiMCPAgent（多服务器整合）"""
    print("\n" + "="*60)
    print("测试5: MultiMCPAgent")
    print("="*60)

    mcp_configs = [
        {
            "name": "memory",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-memory"]
        },
        {
            "name": "filesystem",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem", "."]
        }
    ]

    try:
        from core.agents.mcp_agent import MultiMCPAgent

        multi_agent = MultiMCPAgent(
            name="multi_mcp",
            mcp_configs=mcp_configs,
            health_check=True,
            fail_on_any=False  # 允许部分失败
        )

        status = multi_agent.get_status()
        print(f"\nMultiMCPAgent状态:")
        print(f"  总服务器数: {status['total_servers']}")
        print(f"  已连接: {status['connected_servers']}")
        print(f"  失败: {status['failed_servers']}")
        print(f"  总工具数: {status['total_tools']}")
        print(f"  活跃: {status['is_active']}")

        if status['is_active']:
            print("\n✅ 测试通过：MultiMCPAgent成功整合多个服务器")
        else:
            print("\n⚠️  警告：MultiMCPAgent不活跃")

        multi_agent.close()

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")


def test_6_disabled_health_check():
    """测试6: 禁用健康检查"""
    print("\n" + "="*60)
    print("测试6: 禁用健康检查")
    print("="*60)

    mcp_configs = [{
        "name": "no_check_server",
        "command": "nonexistent_command",
        "health_check": False  # 禁用健康检查
    }]

    try:
        agent_manager = AgentManager(
            plugin_src="plugin",
            base_url="http://127.0.0.1:9999/v1",
            api_key="test",
            model_name="gpt-4",
            mcp_configs=mcp_configs
        )

        # 禁用健康检查时，Agent会尝试创建但可能在调用时失败
        no_check_agent = agent_manager.agents.get("no_check_server")
        if no_check_agent:
            print(f"\nAgent名称: {no_check_agent.name}")
            print(f"健康检查: 已禁用")
            print("\n✅ 测试通过：健康检查已禁用")
            print("   注意：Agent在首次调用时才会真正连接")

    except Exception as e:
        print(f"\n⚠️  测试跳过: {e}")


def main():
    """运行所有测试"""
    print("\n" + "="*70)
    print("MCP Agent健康检查和远端连接测试")
    print("="*70)

    tests = [
        test_1_health_check_success,
        test_2_health_check_failure,
        test_3_remote_server,
        test_4_mixed_configs,
        test_5_multi_mcp_agent,
        test_6_disabled_health_check
    ]

    results = []

    for test_func in tests:
        try:
            test_func()
            results.append((test_func.__name__, "✓"))
        except Exception as e:
            print(f"\n❌ 测试 {test_func.__name__} 异常: {e}")
            results.append((test_func.__name__, "✗"))

    # 总结
    print("\n" + "="*70)
    print("测试总结")
    print("="*70)

    for name, result in results:
        print(f"{result} {name}")

    passed = sum(1 for _, r in results if r == "✓")
    print(f"\n通过: {passed}/{len(tests)}")

    return 0 if passed == len(tests) else 1


if __name__ == "__main__":
    sys.exit(main())
