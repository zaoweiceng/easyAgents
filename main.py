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

        # 执行查询
        query_examples = [
            "abc写了一本书，帮我查询一下这本书的出版信息",
            "圆周率精确到3位小数是多少？",
            "先帮我查一下呼啸山庄的作者是谁，然后再帮我查一下id为2的书籍的出版信息"
        ]

        # 使用第一个查询作为示例
        if len(sys.argv) > 1:
            # 使用命令行参数作为查询
            query = " ".join(sys.argv[1:])
            logger.info(f"执行查询: {query}")
        else:
            # 使用默认查询
            query = query_examples[0]
            logger.info(f"执行默认查询: {query}")

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
