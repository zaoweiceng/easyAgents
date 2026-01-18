"""
easyAgent主程序入口

支持两种运行模式：
1. 命令行模式：直接运行Agent查询
2. API服务模式：启动FastAPI Web服务器
"""

import sys
from core import AgentManager
from config import get_config
import os

def run_api_server(mode='production', host='0.0.0.0', port=8000):
    """
    启动API服务器

    Args:
        mode: 运行模式 ('production', 'development', 'custom')
        host: 主机地址
        port: 端口号
    """
    import uvicorn

    print("=" * 70)
    print("easyAgent API服务启动")
    print("=" * 70)

    # 检查环境
    try:
        import fastapi
        print(f"\n✓ FastAPI版本: {fastapi.__version__}")
        print(f"✓ Uvicorn版本: {uvicorn.__version__}")
    except ImportError as e:
        print(f"\n✗ 缺少依赖: {e}")
        print("\n请先安装依赖:")
        print("  pip install -r requirements_api.txt")
        return 1

    # 根据模式设置参数
    if mode == 'development':
        # 开发模式（自动重载）
        reload = True
        print(f"\n🚀 启动开发模式: http://{host}:{port}")
        print("📚 API文档: http://localhost:8000/docs")
        print("\n⚡ 自动重载已启用")
        print("按 Ctrl+C 停止服务器\n")

    elif mode == 'production':
        # 生产模式（默认）- 使用单进程
        reload = False
        print(f"\n🚀 启动生产模式: http://{host}:{port}")
        print(f"📚 API文档: http://localhost:8000/docs")
        print("\n⚙️  使用单进程模式（稳定可靠）")
        print("按 Ctrl+C 停止服务器\n")

    else:  # custom
        # 自定义模式
        reload = False
        print(f"\n🚀 启动自定义配置: http://{host}:{port}")
        print(f"📚 API文档: http://localhost:{port}/docs")
        print("\n按 Ctrl+C 停止服务器\n")

    print("=" * 70)

    try:
        # 统一使用单进程模式（稳定可靠）
        if mode == 'development':
            # 开发模式：单进程 + 自动重载
            uvicorn.run(
                "api.server:app",
                host=host,
                port=port,
                reload=True,
                log_level="info",
                access_log=True
            )
        else:
            # 生产模式/自定义：单进程，无重载
            uvicorn.run(
                "api.server:app",
                host=host,
                port=port,
                reload=False,
                log_level="info",
                access_log=True
            )
    except KeyboardInterrupt:
        # 用户主动停止，不做任何处理
        pass
    except OSError as e:
        # 端口占用等系统错误
        if e.errno == 48:  # Address already in use
            print(f"\n⚠️  端口 {port} 已被占用")
            print(f"提示：使用 'lsof -ti:{port} | xargs kill -9' 清理端口")
        else:
            print(f"\n❌ 系统错误: {e}")
        return 1
    except Exception as e:
        # 其他未知错误
        print(f"\n❌ 运行错误: {e}")
        return 1
    finally:
        # 显示退出信息
        print("\n" + "=" * 70)
        print("✅ 服务已停止")
        print("👋 感谢使用 easyAgent！")
        print("=" * 70)

    return 0


def run_cli_mode(args):
    """运行命令行模式"""
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


def main():
    """主函数"""
    import argparse

    # 解析命令行参数
    parser = argparse.ArgumentParser(
        description='easyAgent - 多Agent协作系统',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
运行模式:
  python main.py                    运行默认查询示例
  python main.py "你的问题"          运行指定查询
  python main.py --api              启动API服务器（生产模式）
  python main.py --api --dev        启动API服务器（开发模式）
  python main.py --api --port 9000  启动API服务器（自定义端口）
  python main.py --stream           启用流式输出
  python main.py --example 2        使用预设示例2

示例:
  python main.py --api                      启动生产模式（推荐）
  python main.py --api --dev                启动开发模式（自动重载）
  python main.py --api --host 127.0.0.1     自定义主机地址
  python main.py "帮我查询天气"              直接查询
  python main.py --stream "abc"             流式输出查询
        """
    )

    parser.add_argument('--api', action='store_true',
                       help='启动API服务器模式')
    parser.add_argument('--dev', action='store_true',
                       help='使用开发模式（自动重载，仅与--api配合使用）')
    parser.add_argument('--host', default='0.0.0.0',
                       help='API服务器主机地址（默认: 0.0.0.0）')
    parser.add_argument('--port', type=int, default=8000,
                       help='API服务器端口（默认: 8000）')
    parser.add_argument('query', nargs='?', help='查询内容（CLI模式）')
    parser.add_argument('--stream', action='store_true',
                       help='启用流式输出（CLI模式）')
    parser.add_argument('--example', type=int, choices=[1, 2, 3],
                       help='使用预设查询示例（CLI模式，1-3）')

    args = parser.parse_args()

    # 根据参数选择运行模式
    if args.api:
        # API服务模式
        if args.dev:
            # 开发模式
            return run_api_server(mode='development', host=args.host, port=args.port)
        else:
            # 生产模式（默认）
            return run_api_server(mode='production', host=args.host, port=args.port)
    else:
        # 命令行模式
        run_cli_mode(args)


if __name__ == "__main__":
    import sys
    sys.exit(main())
