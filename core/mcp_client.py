"""
MCP (Model Context Protocol) 客户端实现
支持连接MCP服务器并调用其工具、资源和提示词
"""

import json
import asyncio
import subprocess
from typing import Dict, List, Optional, Any
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class MCPTransportType(Enum):
    """MCP传输类型"""
    STDIO = "stdio"
    SSE = "sse"


class MCPClient:
    """MCP客户端，用于与MCP服务器通信"""

    def __init__(
        self,
        name: str,
        command: str = None,
        args: List[str] = None,
        env: Dict[str, str] = None,
        transport_type: MCPTransportType = MCPTransportType.STDIO,
        url: str = None,
        headers: Dict[str, str] = None
    ):
        """
        初始化MCP客户端

        Args:
            name: MCP服务器名称
            command: 启动MCP服务器的命令（stdio模式）
            args: 命令参数
            env: 环境变量
            transport_type: 传输类型（stdio或sse）
            url: 远端服务器URL（sse模式）
            headers: HTTP请求头（sse模式）
        """
        self.name = name
        self.command = command
        self.args = args or []
        self.env = env or {}
        self.transport_type = transport_type
        self.url = url
        self.headers = headers or {}
        self.process = None
        self.session = None  # 用于SSE的HTTP会话
        self.request_id = 0

    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出"""
        await self.close()

    async def connect(self):
        """连接到MCP服务器"""
        if self.transport_type == MCPTransportType.STDIO:
            await self._connect_stdio()
        elif self.transport_type == MCPTransportType.SSE:
            await self._connect_sse()
        else:
            raise ValueError(f"不支持的传输类型: {self.transport_type}")

    async def _connect_stdio(self):
        """通过stdio连接"""
        logger.info(f"启动MCP服务器: {self.name}")

        # 启动子进程
        self.process = await asyncio.create_subprocess_exec(
            self.command,
            *self.args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env={**self.env}
        )

        # 初始化握手
        await self._initialize()

    async def _initialize(self):
        """发送初始化请求"""
        response = await self._send_request({
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "easyAgent",
                    "version": "0.1.0"
                }
            }
        })

        # 发送initialized通知
        await self._send_notification({
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        })

        logger.info(f"MCP服务器 {self.name} 初始化成功")

    async def list_tools(self) -> List[Dict[str, Any]]:
        """列出所有可用的工具"""
        response = await self._send_request({
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "tools/list",
            "params": {}
        })

        return response.get("result", {}).get("tools", [])

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        调用工具

        Args:
            name: 工具名称
            arguments: 工具参数

        Returns:
            工具执行结果
        """
        response = await self._send_request({
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "tools/call",
            "params": {
                "name": name,
                "arguments": arguments
            }
        })

        return response.get("result", {})

    async def list_resources(self) -> List[Dict[str, Any]]:
        """列出所有可用的资源"""
        response = await self._send_request({
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "resources/list",
            "params": {}
        })

        return response.get("result", {}).get("resources", [])

    async def read_resource(self, uri: str) -> str:
        """
        读取资源

        Args:
            uri: 资源URI

        Returns:
            资源内容
        """
        response = await self._send_request({
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "resources/read",
            "params": {
                "uri": uri
            }
        })

        contents = response.get("result", {}).get("contents", [])
        if contents and len(contents) > 0:
            return contents[0].get("text", "")
        return ""

    async def list_prompts(self) -> List[Dict[str, Any]]:
        """列出所有可用的提示词"""
        response = await self._send_request({
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "prompts/list",
            "params": {}
        })

        return response.get("result", {}).get("prompts", [])

    async def get_prompt(self, name: str, arguments: Dict[str, Any] = None) -> str:
        """
        获取提示词

        Args:
            name: 提示词名称
            arguments: 提示词参数

        Returns:
            提示词内容
        """
        response = await self._send_request({
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "prompts/get",
            "params": {
                "name": name,
                "arguments": arguments or {}
            }
        })

        messages = response.get("result", {}).get("messages", [])
        if messages and len(messages) > 0:
            return messages[0].get("content", {}).get("text", "")
        return ""

    async def _send_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """发送请求并等待响应"""
        if self.transport_type == MCPTransportType.STDIO:
            return await self._send_request_stdio(request)
        elif self.transport_type == MCPTransportType.SSE:
            return await self._send_request_sse(request)
        else:
            raise RuntimeError(f"未知的传输类型: {self.transport_type}")

    async def _send_request_stdio(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """通过stdio发送请求"""
        if not self.process or self.process.stdin is None:
            raise RuntimeError("MCP客户端未连接")

        # 发送请求
        request_str = json.dumps(request) + "\n"
        self.process.stdin.write(request_str.encode())
        await self.process.stdin.drain()

        logger.debug(f"发送请求: {request_str.strip()}")

        # 读取响应
        response_line = await self.process.stdout.readline()
        if not response_line:
            raise RuntimeError("MCP服务器关闭了连接")

        response = json.loads(response_line.decode().strip())
        logger.debug(f"收到响应: {json.dumps(response, ensure_ascii=False)}")

        # 检查错误
        if "error" in response:
            error = response["error"]
            raise Exception(f"MCP错误: {error.get('message')} (code: {error.get('code')})")

        return response

    async def _send_request_sse(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """通过SSE发送请求"""
        if not self.session:
            raise RuntimeError("MCP客户端未连接")

        # 发送请求
        async with self.session.post(
            f"{self.url}/rpc",
            json=request,
            headers=self.headers
        ) as response:
            if response.status != 200:
                raise RuntimeError(f"HTTP {response.status}: {await response.text()}")

            result = await response.json()
            logger.debug(f"收到响应: {json.dumps(result, ensure_ascii=False)}")

            # 检查错误
            if "error" in result:
                error = result["error"]
                raise Exception(f"MCP错误: {error.get('message')} (code: {error.get('code')})")

            return result

    async def _send_notification(self, notification: Dict[str, Any]):
        """发送通知（不需要响应）"""
        if not self.process or self.process.stdin is None:
            raise RuntimeError("MCP客户端未连接")

        notification_str = json.dumps(notification) + "\n"
        self.process.stdin.write(notification_str.encode())
        await self.process.stdin.drain()

    def _next_id(self) -> int:
        """生成下一个请求ID"""
        self.request_id += 1
        return self.request_id

    async def _connect_sse(self):
        """通过SSE连接"""
        import aiohttp

        if not self.url:
            raise ValueError("SSE模式需要提供URL")

        logger.info(f"连接到MCP服务器: {self.name} ({self.url})")

        # 创建HTTP会话
        self.session = aiohttp.ClientSession()

        try:
            # 初始化握手
            init_response = await self.session.post(
                f"{self.url}/initialize",
                json={
                    "jsonrpc": "2.0",
                    "id": self._next_id(),
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {
                            "name": "easyAgent",
                            "version": "0.1.0"
                        }
                    }
                },
                headers=self.headers
            )

            if init_response.status != 200:
                raise Exception(f"HTTP {init_response.status}: {await init_response.text()}")

            # 发送initialized通知
            await self.session.post(
                f"{self.url}/notify",
                json={
                    "jsonrpc": "2.0",
                    "method": "notifications/initialized"
                },
                headers=self.headers
            )

            logger.info(f"MCP服务器 {self.name} (SSE) 初始化成功")

        except Exception as e:
            if self.session:
                await self.session.close()
                self.session = None
            raise

    async def close(self):
        """关闭连接"""
        if self.process:
            try:
                self.process.terminate()
                await self.process.wait()
                logger.info(f"MCP服务器 {self.name} 已关闭")
            except Exception as e:
                logger.error(f"关闭MCP服务器时出错: {e}")
            finally:
                self.process = None

        if self.session:
            try:
                await self.session.close()
                logger.info(f"MCP服务器 {self.name} (SSE) 连接已关闭")
            except Exception as e:
                logger.error(f"关闭SSE连接时出错: {e}")
            finally:
                self.session = None


class MCPClientManager:
    """MCP客户端管理器，管理多个MCP服务器连接"""

    def __init__(self):
        self.clients: Dict[str, MCPClient] = {}

    async def add_client(self, client: MCPClient):
        """添加MCP客户端"""
        await client.connect()
        self.clients[client.name] = client
        logger.info(f"MCP客户端 {client.name} 已添加")

    async def remove_client(self, name: str):
        """移除MCP客户端"""
        if name in self.clients:
            await self.clients[name].close()
            del self.clients[name]
            logger.info(f"MCP客户端 {name} 已移除")

    def get_client(self, name: str) -> Optional[MCPClient]:
        """获取MCP客户端"""
        return self.clients.get(name)

    def get_all_clients(self) -> Dict[str, MCPClient]:
        """获取所有MCP客户端"""
        return self.clients.copy()

    async def close_all(self):
        """关闭所有客户端"""
        for client in self.clients.values():
            await client.close()
        self.clients.clear()
        logger.info("所有MCP客户端已关闭")


# 同步版本的包装器（为了兼容现有的同步代码）
class SyncMCPClient:
    """同步版本的MCP客户端"""

    def __init__(self, async_client: MCPClient):
        self.async_client = async_client
        self.loop = None

    def _get_loop(self):
        """获取或创建事件循环"""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                raise RuntimeError("Event loop is closed")
            return loop
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop

    def connect(self):
        """连接"""
        loop = self._get_loop()
        loop.run_until_complete(self.async_client.connect())

    def list_tools(self) -> List[Dict[str, Any]]:
        """列出工具"""
        loop = self._get_loop()
        return loop.run_until_complete(self.async_client.list_tools())

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """调用工具"""
        loop = self._get_loop()
        return loop.run_until_complete(self.async_client.call_tool(name, arguments))

    def list_resources(self) -> List[Dict[str, Any]]:
        """列出资源"""
        loop = self._get_loop()
        return loop.run_until_complete(self.async_client.list_resources())

    def read_resource(self, uri: str) -> str:
        """读取资源"""
        loop = self._get_loop()
        return loop.run_until_complete(self.async_client.read_resource(uri))

    def list_prompts(self) -> List[Dict[str, Any]]:
        """列出提示词"""
        loop = self._get_loop()
        return loop.run_until_complete(self.async_client.list_prompts())

    def get_prompt(self, name: str, arguments: Dict[str, Any] = None) -> str:
        """获取提示词"""
        loop = self._get_loop()
        return loop.run_until_complete(self.async_client.get_prompt(name, arguments))

    def close(self):
        """关闭连接"""
        if self.loop and not self.loop.is_closed():
            self.loop.run_until_complete(self.async_client.close())
