"""
easyAgent主程序入口

使用环境变量和.env文件进行配置管理
"""

import sys
from core import AgentManager
from config import get_config
import os

def main():
    """主函数"""
    import argparse

    # 解析命令行参数
    parser = argparse.ArgumentParser(description='easyAgent - 多Agent协作系统')
    parser.add_argument('query', nargs='?', help='查询内容（可选）')
    parser.add_argument('--stream', action='store_true', help='启用流式输出')
    parser.add_argument('--example', type=int, choices=[1, 2, 3],
                       help='使用预设查询示例（1-3）')

    args = parser.parse_args()

    # 加载配置
    config = get_config()

    # 设置日志
    logger = config.setup_logging()
    logger.info(f"启动 {config.settings.APP_NAME} v{config.settings.APP_VERSION}")

    # 显示配置信息（调试模式）
    if config.settings.DEBUG:
        logger.debug(f"配置信息:\n{config}")

    # 获取LLM配置
    llm_config = config.get_llm_config()
    logger.info(f"LLM服务: {llm_config['base_url']}")
    logger.info(f"LLM模型: {llm_config['model_name']}")

    # 获取Agent配置
    agent_config = config.get_agent_config()
    logger.info(f"插件目录: {agent_config['plugin_src']}")

    # 获取MCP配置
    mcp_configs = config.get_mcp_configs()
    if mcp_configs:
        logger.info(f"MCP配置: 加载了 {len(mcp_configs)} 个MCP服务器")
    elif config.settings.MCP_ENABLED:
        logger.warning("MCP已启用但未配置服务器")

    # 创建AgentManager
    try:
        agent_manager = AgentManager(
            plugin_src=agent_config['plugin_src'],
            base_url=llm_config['base_url'],
            api_key=llm_config['api_key'],
            model_name=llm_config['model_name'],
            mcp_configs=mcp_configs if mcp_configs else None
        )

        logger.info("AgentManager初始化成功")

        # 显示已加载的Agent
        agents_info = agent_manager.agents.to_json()
        active_agents = agents_info.get('available_agents', {})
        logger.info(f"已加载 {len(active_agents)} 个Agent:")

        for agent_name in active_agents.keys():
            agent = agent_manager.agents[agent_name]
            status = "✓ 活跃" if agent.is_active else "✗ 不活跃"
            logger.info(f"  - {agent_name}: {status}")

        # 预设查询示例
        query_examples = [
            "abc写了一本书，帮我查询一下这本书的出版信息",
            "圆周率精确到3位小数是多少？",
            "先帮我查一下呼啸山庄的作者是谁，然后再帮我查一下id为2的书籍的出版信息"
        ]

        # 确定查询内容
        if args.example:
            query = query_examples[args.example - 1]
            logger.info(f"使用示例查询 {args.example}: {query}")
        elif args.query:
            query = args.query
            logger.info(f"执行查询: {query}")
        else:
            query = query_examples[0]
            logger.info(f"执行默认查询: {query}")

        # 执行查询
        if args.stream:
            # 流式模式
            logger.info("="*50)
            logger.info("流式响应:")
            logger.info("="*50)

            for event in agent_manager(query, stream=True):
                event_type = event["type"]

                if event_type == "delta":
                    # 实时显示LLM生成的内容
                    content = event["data"]["content"]
                    if content:
                        print(content, end="", flush=True)

                elif event_type == "agent_start":
                    agent_name = event["data"]["agent_name"]
                    print(f"\n[Agent: {agent_name}] ", end="", flush=True)

                elif event_type == "agent_end":
                    agent_name = event["data"]["agent_name"]
                    status = event["data"]["status"]
                    print(f"\n✓ {agent_name} 完成 ({status})", flush=True)

                elif event_type == "error":
                    error_msg = event["data"]["error_message"]
                    print(f"\n✗ 错误: {error_msg}", flush=True)

                elif event_type == "metadata":
                    # 元数据（可选显示）
                    pass

            print()  # 最后换行

        else:
            # 同步模式（原有行为）
            response = agent_manager(query)

            # 输出响应
            logger.info("="*50)
            logger.info("响应:")
            for i, msg in enumerate(response):
                if msg.get("message"):
                    logger.info(f"[{i+1}] {msg['role']}: {msg['message']}")
                elif msg.get("content"):
                    logger.debug(f"[{i+1}] {msg['role']}: {msg['content'][:100]}...")

            logger.info("="*50)

    except Exception as e:
        logger.error(f"AgentManager初始化或运行失败: {e}")
        raise


if __name__ == "__main__":
    import sys
    main()
