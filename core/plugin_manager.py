import logging
import json
import os
from typing import Dict, List, Any
from .agent import AgentLoader, Agent
from .constants import app_name
from .agent_loader_util import load_class_from_file, filename_to_classname
from .agents import EntranceAgent, GeneralAgent, DemandAgent   # 导入所有内置 Agent
from .agents.mcp_agent import MCPAgent, MultiMCPAgent

logger = logging.getLogger(app_name)


class pluginManager:
    def __init__(self, src: str, mcp_configs: List[Dict[str, Any]] = None):
        """
        初始化插件管理器

        Args:
            src: 插件目录路径
            mcp_configs: MCP服务器配置列表（可选）
                [
                    {
                        "name": "mcp_server_name",
                        "command": "启动命令",
                        "args": ["参数1", "参数2"],
                        "env": {"ENV_VAR": "value"}
                    },
                    ...
                ]
        """
        self.agent_loader = AgentLoader()
        self.plugin_src = src
        self.mcp_configs = mcp_configs or []

        # 加载Python插件
        self.load_plugins()

        # 添加内置Agent
        self.agent_loader.add_agent(EntranceAgent())
        self.agent_loader.add_agent(GeneralAgent())
        self.agent_loader.add_agent(DemandAgent())

        # 加载MCP Agent
        if self.mcp_configs:
            self.load_mcp_agents()

    def load_plugins(self) -> None:
        """加载plugin目录下的所有Agent"""
        if not os.path.isdir(self.plugin_src):
            logger.warning(f"插件目录 '{self.plugin_src}' 不存在或不是一个目录")
            return

        for filename in os.listdir(self.plugin_src):
            if filename.endswith(".py") and not filename.startswith("__"):
                logger.info(f"加载 Agent 文件: {filename}")
                filepath = os.path.join(self.plugin_src, filename)
                class_name = filename_to_classname(filename)
                try:
                    cls = load_class_from_file(filepath, class_name)
                    if issubclass(cls, Agent):
                        agent_instance = cls()
                        self.agent_loader.add_agent(agent_instance)
                        logger.info(f"✓ 成功加载Agent: {agent_instance.name}")
                except (ImportError, AttributeError, ValueError) as e:
                    logger.error(f"✗ 加载插件 '{filename}' 失败: {e}")

    def reload_plugins(self) -> int:
        """
        重新加载所有插件（支持热插拔）

        Returns:
            int: 成功加载的Agent数量

        这个方法会：
        1. 清除所有已加载的插件Agent（保留内置Agent）
        2. 重新扫描plugin目录
        3. 加载所有Agent文件
        """
        logger.info("🔄 开始重新加载插件...")

        # 保存内置Agent
        builtin_agents = {}
        for agent_name in ["entrance_agent", "general_agent", "demand_agent"]:
            agent = self.agent_loader.get_agent(agent_name)
            if agent:
                builtin_agents[agent_name] = agent

        # 保存MCP Agent（通过类型判断）
        mcp_agents = {}
        for agent_name, agent in self.agent_loader.get_all_agents().items():
            # 检查是否是MCPAgent或MultiMCPAgent的实例
            from .agents.mcp_agent import MCPAgent, MultiMCPAgent
            if isinstance(agent, (MCPAgent, MultiMCPAgent)):
                mcp_agents[agent_name] = agent

        # 清空所有Agent
        self.agent_loader = AgentLoader()

        # 恢复内置Agent
        for name, agent in builtin_agents.items():
            self.agent_loader.add_agent(agent)
            logger.info(f"✓ 恢复内置Agent: {name}")

        # 恢复MCP Agent
        for name, agent in mcp_agents.items():
            self.agent_loader.add_agent(agent)
            logger.info(f"✓ 恢复MCP Agent: {name}")

        # 重新加载插件
        plugin_count = 0
        if not os.path.isdir(self.plugin_src):
            logger.warning(f"插件目录 '{self.plugin_src}' 不存在或不是一个目录")
        else:
            for filename in os.listdir(self.plugin_src):
                if filename.endswith(".py") and not filename.startswith("__"):
                    logger.info(f"加载 Agent 文件: {filename}")
                    filepath = os.path.join(self.plugin_src, filename)
                    class_name = filename_to_classname(filename)
                    try:
                        cls = load_class_from_file(filepath, class_name)
                        if issubclass(cls, Agent):
                            agent_instance = cls()
                            self.agent_loader.add_agent(agent_instance)
                            logger.info(f"✓ 成功加载Agent: {agent_instance.name}")
                            plugin_count += 1
                    except (ImportError, AttributeError, ValueError) as e:
                        logger.error(f"✗ 加载插件 '{filename}' 失败: {e}")

        logger.info(f"✅ 插件重新加载完成，共加载 {plugin_count} 个插件Agent")
        return plugin_count

    def load_mcp_agents(self) -> None:
        """加载MCP Agent"""
        if not self.mcp_configs:
            return

        logger.info(f"开始加载 {len(self.mcp_configs)} 个MCP服务器...")

        # 检查是否需要创建多MCP Agent
        if len(self.mcp_configs) > 1:
            self._load_multi_mcp_agent()
        else:
            self._load_single_mcp_agents()

    def _load_single_mcp_agents(self) -> None:
        """为每个MCP服务器创建单独的Agent"""
        for config in self.mcp_configs:
            try:
                name = config.get("name", "unknown")
                command = config.get("command")
                url = config.get("url")
                args = config.get("args", [])
                env = config.get("env", {})
                headers = config.get("headers", {})
                health_check = config.get("health_check", True)

                # 检查配置
                if not command and not url:
                    logger.error(f"MCP服务器 {name} 缺少command或url配置")
                    continue

                # 创建MCP Agent
                mcp_agent = MCPAgent(
                    name=name,
                    mcp_command=command,
                    mcp_args=args,
                    mcp_env=env,
                    mcp_url=url,
                    mcp_headers=headers,
                    health_check=health_check,
                    auto_connect=True
                )

                # 检查Agent是否活跃
                if not mcp_agent.is_active:
                    logger.warning(f"⚠ MCP Agent {name} 加载失败，设置为不活跃: {mcp_agent.connection_error}")
                else:
                    logger.info(f"✓ 成功加载MCP Agent: {name} ({mcp_agent.connection_type}, {len(mcp_agent.tools)} 个工具)")

                # 无论是否活跃，都添加到AgentLoader
                self.agent_loader.add_agent(mcp_agent)

            except Exception as e:
                logger.error(f"✗ 加载MCP Agent失败: {e}")

    def _load_multi_mcp_agent(self) -> None:
        """创建一个整合所有MCP服务器的Agent"""
        try:
            multi_mcp_agent = MultiMCPAgent(
                name="multi_mcp",
                mcp_configs=self.mcp_configs
            )

            self.agent_loader.add_agent(multi_mcp_agent)
            logger.info(f"✓ 成功加载多MCP Agent: multi_mcp ({len(multi_mcp_agent.all_tools)} 个工具)")

        except Exception as e:
            logger.error(f"✗ 加载多MCP Agent失败: {e}")

    def to_string(self) -> str:
        return json.dumps(self.agent_loader.to_json(), ensure_ascii=False)

    def __getitem__(self, agent_name: str) -> Agent:
        agent = self.agent_loader.get_agent(agent_name)
        if agent is None:
            raise KeyError(f"Agent '{agent_name}' 不存在")
        return agent
