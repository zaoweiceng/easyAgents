"""
MCP Agent - 将MCP服务器的工具包装为Agent
支持健康检查和远端服务器连接
"""

from typing import Dict, List, Any, Optional
from core import Agent, Message, PromptTemplate
from core.mcp_client import MCPClient, SyncMCPClient, MCPTransportType
import logging
import subprocess
import time

logger = logging.getLogger(__name__)


class MCPAgent(Agent):
    """
    MCP Agent - 将MCP服务器的工具包装为Agent

    支持功能：
    - 本地stdio连接
    - 远端SSE连接
    - 健康检查（自动检测并设置is_active）
    """

    def __init__(
        self,
        name: str,
        mcp_command: str = None,
        mcp_args: List[str] = None,
        mcp_env: Dict[str, str] = None,
        mcp_url: str = None,
        mcp_headers: Dict[str, str] = None,
        transport_type: str = "auto",
        description: str = None,
        auto_connect: bool = True,
        health_check: bool = True,
        timeout: int = 10
    ):
        """
        初始化MCP Agent

        Args:
            name: Agent名称（也是MCP服务器名称）
            mcp_command: 启动MCP服务器的命令（stdio模式）
            mcp_args: 命令参数
            mcp_env: 环境变量
            mcp_url: 远端服务器URL（sse模式）
            mcp_headers: HTTP请求头（sse模式）
            transport_type: 传输类型（"auto", "stdio", "sse"）
            description: Agent描述
            auto_connect: 是否自动连接
            health_check: 是否进行健康检查
            timeout: 健康检查超时时间（秒）
        """
        self.name = name
        self.health_check_enabled = health_check
        self.timeout = timeout
        self.connection_error = None  # 保存连接错误信息
        self.tools: List[Dict[str, Any]] = []

        # 自动检测传输类型
        if transport_type == "auto":
            if mcp_url:
                transport_type = "sse"
            elif mcp_command:
                transport_type = "stdio"
            else:
                raise ValueError("必须提供mcp_command或mcp_url")

        # 创建MCP客户端
        try:
            if transport_type == "sse":
                if not mcp_url:
                    raise ValueError("SSE模式需要提供mcp_url")

                self.mcp_client = MCPClient(
                    name=name,
                    url=mcp_url,
                    headers=mcp_headers or {},
                    transport_type=MCPTransportType.SSE
                )
                self.connection_type = "sse"

            else:  # stdio
                if not mcp_command:
                    raise ValueError("STDIO模式需要提供mcp_command")

                self.mcp_client = MCPClient(
                    name=name,
                    command=mcp_command,
                    args=mcp_args or [],
                    env=mcp_env or {},
                    transport_type=MCPTransportType.STDIO
                )
                self.connection_type = "stdio"

            # 创建同步包装器
            self.sync_client = SyncMCPClient(self.mcp_client)

            # 健康检查
            if health_check and auto_connect:
                if not self._perform_health_check():
                    # 健康检查失败，设置为不活跃
                    logger.warning(f"MCP Agent {name} 健康检查失败，设置为不活跃")
                    # 不要调用super().__init__()，因为Agent无法正常工作
                    self._setup_inactive_agent()
                    return

            # 自动连接
            if auto_connect:
                self.sync_client.connect()
                self.tools = self.sync_client.list_tools()
                logger.info(f"MCP Agent {name} ({self.connection_type}) 已加载 {len(self.tools)} 个工具")

        except Exception as e:
            # 初始化失败
            logger.error(f"MCP Agent {name} 初始化失败: {e}")
            self.connection_error = str(e)
            self._setup_inactive_agent()
            return

        # 生成描述
        if description is None:
            if self.connection_type == "sse":
                description = f"MCP Agent ({self.connection_type})，连接到远端服务器 {mcp_url}，提供 {len(self.tools)} 个工具"
            else:
                description = f"MCP Agent ({self.connection_type})，提供 {len(self.tools)} 个工具"

        # 构建handles列表
        handles = [tool.get("name", "") for tool in self.tools[:5]]
        handles.append("mcp_tool")

        # 生成提示词模板
        prompt_template = self._create_prompt_template()

        # 调用父类初始化
        super().__init__(
            name=name,
            description=description,
            handles=handles,
            parameters={
                "tool_name": "要调用的工具名称",
                "tool_arguments": "工具参数（JSON格式）"
            }
        )

        self.prompt_template = prompt_template

    def _setup_inactive_agent(self):
        """设置为不活跃的Agent"""
        # 手动设置必要的属性
        self._pydantic_fields_set = {
            "name", "description", "handles", "parameters", "is_active",
            "version", "prompt_template"
        }
        self.name = self.name
        self.is_active = False

        if self.connection_error:
            self.description = f"MCP Agent ({self.connection_type}) - 不可用: {self.connection_error}"
        else:
            self.description = f"MCP Agent ({self.connection_type}) - 健康检查失败，已禁用"

        self.handles = []
        self.parameters = {}
        self.version = "0.0.0"
        self.prompt_template = None

        logger.warning(f"Agent {self.name} 已设置为不活跃状态")

    def _perform_health_check(self) -> bool:
        """
        执行健康检查

        Returns:
            bool: True表示健康检查通过，False表示失败
        """
        logger.info(f"开始MCP Agent {self.name} 的健康检查...")

        # 检查1: 环境检查
        if not self._check_environment():
            logger.error(f"环境检查失败")
            return False

        # 检查2: 连接测试
        if not self._check_connection():
            logger.error(f"连接测试失败")
            return False

        logger.info(f"MCP Agent {self.name} 健康检查通过")
        return True

    def _check_environment(self) -> bool:
        """检查运行环境"""
        if self.connection_type == "stdio":
            # 检查命令是否可用
            if not self._check_command_available():
                error_msg = f"命令 '{self.mcp_client.command}' 不可用"
                self.connection_error = error_msg
                logger.error(error_msg)
                return False

        elif self.connection_type == "sse":
            # 检查aiohttp是否可用
            try:
                import aiohttp
            except ImportError:
                error_msg = "aiohttp未安装，SSE模式需要aiohttp"
                self.connection_error = error_msg
                logger.error(error_msg)
                return False

        return True

    def _check_command_available(self) -> bool:
        """检查命令是否可用"""
        try:
            # 尝试获取命令路径
            result = subprocess.run(
                ["which", self.mcp_client.command],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode != 0:
                # 尝试直接运行命令（如npx）
                result = subprocess.run(
                    [self.mcp_client.command, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )

            return result.returncode == 0

        except subprocess.TimeoutExpired:
            logger.warning(f"命令 '{self.mcp_client.command}' 响应超时")
            return False
        except FileNotFoundError:
            logger.warning(f"命令 '{self.mcp_client.command}' 不存在")
            return False
        except Exception as e:
            logger.warning(f"检查命令时出错: {e}")
            return False

    def _check_connection(self) -> bool:
        """检查MCP服务器连接"""
        try:
            # 尝试连接
            start_time = time.time()
            self.sync_client.connect()

            # 尝试列出工具
            tools = self.sync_client.list_tools()
            elapsed = time.time() - start_time

            logger.info(f"连接成功，发现 {len(tools)} 个工具 (耗时 {elapsed:.2f}秒)")

            # 关闭测试连接
            self.sync_client.close()

            return True

        except subprocess.TimeoutExpired as e:
            error_msg = f"连接超时（{self.timeout}秒）"
            self.connection_error = error_msg
            logger.error(f"{error_msg}: {e}")
            return False

        except FileNotFoundError as e:
            error_msg = f"无法启动MCP服务器: {e}"
            self.connection_error = error_msg
            logger.error(error_msg)
            return False

        except Exception as e:
            error_msg = f"连接失败: {str(e)}"
            self.connection_error = error_msg
            logger.error(f"{error_msg}")
            return False

    def _create_prompt_template(self) -> PromptTemplate:
        """创建提示词模板"""
        # 生成工具列表描述
        tools_desc = self._generate_tools_description()

        system_instructions = f"""
你是一个MCP工具调用助手，可以调用{len(self.tools)}个工具来完成任务。

# 可用工具

{tools_desc}

# 工具调用规则

1. 根据用户需求选择最合适的工具
2. 按照工具的schema正确提供参数
3. 如果需要调用多个工具，请在task_list中列出
4. 工具调用结果会在data.tool_result中返回
"""

        core_instructions = """
# 任务流程

1. 分析用户需求，选择合适的工具
2. 构建工具调用参数
3. 返回工具调用信息

# 输出格式

你必须在data字段中包含以下信息：
{
  "tool_name": "工具名称",
  "tool_arguments": {
    "参数1": "值1",
    "参数2": "值2"
  }
}
"""

        data_fields = '''
"tool_name": "string"  // 要调用的工具名称
"tool_arguments": {  // 工具参数（对象）
  "param1": "value1",
  "param2": "value2"
}
"tool_result": "any"  // 工具执行结果（在执行后填充）
'''

        return PromptTemplate(
            system_instructions=system_instructions,
            available_agents=None,
            core_instructions=core_instructions,
            data_fields=data_fields
        )

    def _generate_tools_description(self) -> str:
        """生成工具列表描述"""
        descriptions = []
        for tool in self.tools:
            name = tool.get("name", "unknown")
            desc = tool.get("description", "无描述")
            input_schema = tool.get("inputSchema", {})

            # 提取参数信息
            params = []
            properties = input_schema.get("properties", {})
            required = input_schema.get("required", [])

            for param_name, param_info in properties.items():
                param_type = param_info.get("type", "any")
                is_required = param_name in required
                param_desc = param_info.get("description", "")
                params.append(
                    f"  - {param_name} ({param_type}, {'必需' if is_required else '可选'}): {param_desc}"
                )

            descriptions.append(f"""
### {name}

{desc}

参数：
{chr(10).join(params) if params else "  无参数"}
""")

        return "\n".join(descriptions)

    def run(self, message: Message) -> Message:
        """执行MCP工具调用"""
        if not self.is_active:
            message.status = "error"
            message.message = f"MCP Agent {self.name} 不可用: {self.connection_error or '未连接'}"
            message.next_agent = "general_agent"
            return message

        tool_name = message.data.get("tool_name")
        tool_arguments = message.data.get("tool_arguments", {})

        if not tool_name:
            message.status = "error"
            message.message = "未指定工具名称"
            message.next_agent = "general_agent"
            return message

        try:
            # 调用工具
            logger.info(f"调用MCP工具: {tool_name}, 参数: {tool_arguments}")
            result = self.sync_client.call_tool(tool_name, tool_arguments)

            # 更新消息
            message.data = {
                **message.data,
                "tool_result": result
            }
            message.status = "success"
            message.message = f"工具 {tool_name} 调用成功"

            # 更新任务列表
            if message.task_list:
                message.task_list = message.task_list[1:]

            # 如果还有任务，不设置next_agent（让LLM决定）
            # 如果没有任务，交给general_agent
            if not message.task_list:
                message.next_agent = "general_agent"

        except Exception as e:
            logger.error(f"调用MCP工具失败: {e}")
            message.status = "error"
            message.message = f"工具调用失败: {str(e)}"
            message.next_agent = "general_agent"

        return message

    def get_tool_names(self) -> List[str]:
        """获取所有工具名称"""
        return [tool.get("name", "") for tool in self.tools]

    def get_tool_info(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """获取工具信息"""
        for tool in self.tools:
            if tool.get("name") == tool_name:
                return tool
        return None

    def get_health_status(self) -> Dict[str, Any]:
        """
        获取健康状态

        Returns:
            Dict: 健康状态信息
        """
        return {
            "name": self.name,
            "is_active": self.is_active,
            "connection_type": self.connection_type,
            "error": self.connection_error,
            "tools_count": len(self.tools),
            "url": getattr(self.mcp_client, 'url', None) if self.connection_type == "sse" else None,
            "command": getattr(self.mcp_client, 'command', None) if self.connection_type == "stdio" else None
        }

    def close(self):
        """关闭MCP连接"""
        try:
            if hasattr(self, 'sync_client'):
                self.sync_client.close()
                logger.info(f"MCP Agent {self.name} 已关闭")
        except Exception as e:
            logger.error(f"关闭MCP Agent时出错: {e}")

    def __del__(self):
        """析构函数，确保连接关闭"""
        try:
            self.close()
        except:
            pass


class MCPResourceAgent(Agent):
    """
    MCP资源Agent - 读取MCP服务器提供的资源
    支持健康检查
    """

    def __init__(
        self,
        name: str,
        mcp_command: str = None,
        mcp_args: List[str] = None,
        mcp_env: Dict[str, str] = None,
        mcp_url: str = None,
        mcp_headers: Dict[str, str] = None,
        transport_type: str = "auto",
        description: str = None,
        health_check: bool = True,
        timeout: int = 10
    ):
        """初始化MCP资源Agent"""
        self.name = name
        self.health_check_enabled = health_check
        self.timeout = timeout
        self.connection_error = None

        # 自动检测传输类型
        if transport_type == "auto":
            if mcp_url:
                transport_type = "sse"
            elif mcp_command:
                transport_type = "stdio"
            else:
                raise ValueError("必须提供mcp_command或mcp_url")

        try:
            if transport_type == "sse":
                self.mcp_client = MCPClient(
                    name=name,
                    url=mcp_url,
                    headers=mcp_headers or {},
                    transport_type=MCPTransportType.SSE
                )
                self.connection_type = "sse"
            else:
                self.mcp_client = MCPClient(
                    name=name,
                    command=mcp_command,
                    args=mcp_args or [],
                    env=mcp_env or {},
                    transport_type=MCPTransportType.STDIO
                )
                self.connection_type = "stdio"

            self.sync_client = SyncMCPClient(self.mcp_client)

            # 健康检查
            if health_check:
                if not self._perform_health_check():
                    logger.warning(f"MCP资源Agent {name} 健康检查失败，设置为不活跃")
                    self._setup_inactive_agent()
                    return

            # 连接并列出资源
            self.sync_client.connect()
            self.resources = self.sync_client.list_resources()
            logger.info(f"MCP资源Agent {name} ({self.connection_type}) 已加载 {len(self.resources)} 个资源")

        except Exception as e:
            logger.error(f"MCP资源Agent {name} 初始化失败: {e}")
            self.connection_error = str(e)
            self._setup_inactive_agent()
            return

        if description is None:
            if self.connection_type == "sse":
                description = f"MCP资源Agent ({self.connection_type})，访问远端服务器 {mcp_url} 的 {len(self.resources)} 个资源"
            else:
                description = f"MCP资源Agent ({self.connection_type})，访问 {len(self.resources)} 个资源"

        super().__init__(
            name=f"{name}_resource",
            description=description,
            handles=["资源", "resource", "读取资源"],
            parameters={
                "resource_uri": "资源的URI"
            }
        )

        self.prompt_template = PromptTemplate(
            system_instructions=f"""
你是一个资源访问助手，可以访问{len(self.resources)}个资源。

# 可用资源

{self._generate_resources_description()}
""",
            available_agents=None,
            core_instructions="根据用户需求选择合适的资源并读取",
            data_fields='"resource_uri": "string"  // 要读取的资源URI'
        )

    def _setup_inactive_agent(self):
        """设置为不活跃的Agent"""
        self._pydantic_fields_set = {
            "name", "description", "handles", "parameters", "is_active",
            "version", "prompt_template"
        }
        self.name = self.name
        self.is_active = False
        self.description = f"MCP资源Agent - 不可用: {self.connection_error or '连接失败'}"
        self.handles = []
        self.parameters = {}
        self.version = "0.0.0"
        self.prompt_template = None

    def _perform_health_check(self) -> bool:
        """执行健康检查"""
        logger.info(f"开始MCP资源Agent {self.name} 的健康检查...")

        try:
            self.sync_client.connect()
            resources = self.sync_client.list_resources()
            logger.info(f"连接成功，发现 {len(resources)} 个资源")
            self.sync_client.close()
            return True
        except Exception as e:
            self.connection_error = str(e)
            logger.error(f"健康检查失败: {e}")
            return False

    def _generate_resources_description(self) -> str:
        """生成资源描述"""
        descriptions = []
        for resource in self.resources:
            uri = resource.get("uri", "unknown")
            name = resource.get("name", "无名称")
            desc = resource.get("description", "无描述")
            descriptions.append(f"- **{name}** ({uri}): {desc}")

        return "\n".join(descriptions)

    def run(self, message: Message) -> Message:
        """读取资源"""
        if not self.is_active:
            message.status = "error"
            message.message = f"MCP资源Agent不可用: {self.connection_error}"
            return message

        uri = message.data.get("resource_uri")

        if not uri:
            message.status = "error"
            message.message = "未指定资源URI"
            return message

        try:
            content = self.sync_client.read_resource(uri)

            message.data = {
                **message.data,
                "resource_content": content
            }
            message.status = "success"
            message.message = f"资源 {uri} 读取成功"

        except Exception as e:
            message.status = "error"
            message.message = f"资源读取失败: {str(e)}"

        return message

    def close(self):
        """关闭连接"""
        try:
            if hasattr(self, 'sync_client'):
                self.sync_client.close()
        except Exception as e:
            logger.error(f"关闭MCP资源Agent时出错: {e}")

    def __del__(self):
        """析构函数"""
        try:
            self.close()
        except:
            pass


class MultiMCPAgent(Agent):
    """
    多MCP服务器Agent - 整合多个MCP服务器的工具
    支持健康检查和混合连接类型
    """

    def __init__(
        self,
        name: str,
        mcp_configs: List[Dict[str, Any]],
        description: str = None,
        health_check: bool = True,
        fail_on_any: bool = False
    ):
        """
        初始化多MCP Agent

        Args:
            name: Agent名称
            mcp_configs: MCP配置列表
                [
                    {
                        "name": "server1",
                        "command": "node",  # stdio模式
                        "args": ["server1.js"],
                        "env": {}
                    },
                    {
                        "name": "server2",
                        "url": "http://localhost:3000",  # sse模式
                        "headers": {}
                    }
                ]
            description: 描述
            health_check: 是否进行健康检查
            fail_on_any: 如果任一服务器失败，整个Agent是否失败
        """
        self.name = name
        self.health_check_enabled = health_check
        self.fail_on_any = fail_on_any
        self.mcp_clients: Dict[str, SyncMCPClient] = {}
        self.all_tools: Dict[str, Dict[str, Any]] = {}
        self.failed_servers: List[str] = []

        # 连接所有MCP服务器
        for config in mcp_configs:
            server_name = config.get("name", "unknown")

            try:
                # 检测配置类型
                if "url" in config:
                    # SSE模式
                    mcp_client = MCPClient(
                        name=server_name,
                        url=config["url"],
                        headers=config.get("headers", {}),
                        transport_type=MCPTransportType.SSE
                    )
                    connection_type = "sse"
                elif "command" in config:
                    # STDIO模式
                    mcp_client = MCPClient(
                        name=server_name,
                        command=config["command"],
                        args=config.get("args", []),
                        env=config.get("env", {}),
                        transport_type=MCPTransportType.STDIO
                    )
                    connection_type = "stdio"
                else:
                    raise ValueError(f"服务器 {server_name} 配置缺少url或command")

                sync_client = SyncMCPClient(mcp_client)

                # 健康检查
                if health_check:
                    if not self._check_server(sync_client, connection_type):
                        self.failed_servers.append(server_name)
                        if fail_on_any:
                            raise Exception(f"服务器 {server_name} 健康检查失败")
                        logger.warning(f"服务器 {server_name} 健康检查失败，跳过")
                        continue

                # 连接并获取工具
                sync_client.connect()
                self.mcp_clients[server_name] = sync_client

                tools = sync_client.list_tools()
                for tool in tools:
                    tool_name = tool.get("name")
                    self.all_tools[tool_name] = {
                        "server": server_name,
                        "tool": tool
                    }

                logger.info(f"✓ 已连接到MCP服务器 {server_name} ({connection_type})，加载 {len(tools)} 个工具")

            except Exception as e:
                logger.error(f"✗ 连接MCP服务器 {server_name} 失败: {e}")
                self.failed_servers.append(server_name)
                if fail_on_any:
                    self._setup_inactive_agent(str(e))
                    return

        # 检查是否至少有一个服务器连接成功
        if not self.mcp_clients:
            error_msg = f"所有MCP服务器连接失败: {', '.join(self.failed_servers)}"
            logger.error(error_msg)
            self._setup_inactive_agent(error_msg)
            return

        # 生成描述
        if description is None:
            description = f"多MCP Agent，整合了 {len(self.mcp_clients)} 个服务器的 {len(self.all_tools)} 个工具"

        super().__init__(
            name=name,
            description=description,
            handles=["mcp", "工具", "多服务器"],
            parameters={
                "tool_name": "工具名称",
                "tool_arguments": "工具参数"
            }
        )

        self.prompt_template = self._create_prompt_template()

    def _setup_inactive_agent(self, error_msg: str = None):
        """设置为不活跃的Agent"""
        self._pydantic_fields_set = {
            "name", "description", "handles", "parameters", "is_active",
            "version", "prompt_template"
        }
        self.name = self.name
        self.is_active = False
        self.description = error_msg or f"多MCP Agent - 所有服务器连接失败"
        self.handles = []
        self.parameters = {}
        self.version = "0.0.0"
        self.prompt_template = None

    def _check_server(self, sync_client: SyncMCPClient, connection_type: str) -> bool:
        """检查服务器连接"""
        try:
            sync_client.connect()
            tools = sync_client.list_tools()
            sync_client.close()
            logger.info(f"服务器健康检查通过 ({connection_type})")
            return True
        except Exception as e:
            logger.error(f"服务器健康检查失败: {e}")
            return False

    def _create_prompt_template(self) -> PromptTemplate:
        """创建提示词模板"""
        tools_desc = self._generate_all_tools_description()

        return PromptTemplate(
            system_instructions=f"""
你是一个多MCP服务器工具调用助手，可以访问{len(self.mcp_clients)}个MCP服务器的工具。

# 可用工具

{tools_desc}

# 调用规则

1. 根据工具名称选择合适的工具
2. 工具会自动路由到对应的服务器
3. 正确提供工具所需的参数
""",
            available_agents=None,
            core_instructions="分析用户需求并调用相应的工具",
            data_fields='"tool_name": "string", "tool_arguments": {}'
        )

    def _generate_all_tools_description(self) -> str:
        """生成所有工具的描述"""
        descriptions = []
        for tool_name, tool_info in self.all_tools.items():
            server = tool_info["server"]
            tool = tool_info["tool"]
            desc = tool.get("description", "无描述")
            descriptions.append(f"- **{tool_name}** (来自 {server}): {desc}")

        return "\n".join(descriptions)

    def run(self, message: Message) -> Message:
        """执行工具调用"""
        if not self.is_active:
            message.status = "error"
            message.message = f"多MCP Agent不可用"
            message.next_agent = "general_agent"
            return message

        tool_name = message.data.get("tool_name")
        tool_arguments = message.data.get("tool_arguments", {})

        if not tool_name:
            message.status = "error"
            message.message = "未指定工具名称"
            message.next_agent = "general_agent"
            return message

        # 查找工具所在的服务器
        if tool_name not in self.all_tools:
            message.status = "error"
            message.message = f"工具 {tool_name} 不存在"
            message.next_agent = "general_agent"
            return message

        server_name = self.all_tools[tool_name]["server"]
        client = self.mcp_clients.get(server_name)

        if not client:
            message.status = "error"
            message.message = f"工具 {tool_name} 所在的服务器 {server_name} 不可用"
            message.next_agent = "general_agent"
            return message

        try:
            # 调用工具
            result = client.call_tool(tool_name, tool_arguments)

            message.data = {
                **message.data,
                "tool_result": result,
                "server": server_name
            }
            message.status = "success"
            message.message = f"工具 {tool_name} 调用成功（服务器: {server_name}）"

            if message.task_list:
                message.task_list = message.task_list[1:]

            if not message.task_list:
                message.next_agent = "general_agent"

        except Exception as e:
            logger.error(f"调用工具失败: {e}")
            message.status = "error"
            message.message = f"工具调用失败: {str(e)}"
            message.next_agent = "general_agent"

        return message

    def get_status(self) -> Dict[str, Any]:
        """获取状态"""
        return {
            "name": self.name,
            "is_active": self.is_active,
            "total_servers": len(self.mcp_clients) + len(self.failed_servers),
            "connected_servers": len(self.mcp_clients),
            "failed_servers": self.failed_servers,
            "total_tools": len(self.all_tools)
        }

    def close(self):
        """关闭所有连接"""
        for client in self.mcp_clients.values():
            try:
                client.close()
            except Exception as e:
                logger.error(f"关闭MCP客户端时出错: {e}")

    def __del__(self):
        """析构函数"""
        try:
            self.close()
        except:
            pass
