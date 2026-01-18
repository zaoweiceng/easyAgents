from typing import List, Dict, Optional, Generator, Union, Any
from pydantic import BaseModel, Field
from .base_model import Message
from .prompt.template_model import PromptTemplate
import logging

logger = logging.getLogger(__name__)

# 导入文件服务（延迟导入避免循环依赖）


def get_file_service():
    """获取文件服务实例"""
    from .file_service import get_file_service as _get_file_service
    return _get_file_service()


def normalize_agent_output(
    result: Union[Message, Dict[str, Any], Any],
    input_message: Message,
    agent_name: str
) -> Message:
    """
    标准化Agent的输出为Message格式

    Args:
        result: Agent的返回结果（Message、Dict或其他类型）
        input_message: 输入的消息
        agent_name: Agent名称

    Returns:
        Message: 标准化的Message对象
    """
    # 如果已经是Message对象，直接返回
    if isinstance(result, Message):
        return result

    # 分析返回数据，决定是否需要继续处理
    data = None
    message_str = ""
    next_agent = "none"  # 默认结束

    if isinstance(result, dict):
        # 字典类型：将整个字典作为data
        data = result
        message_str = f"{agent_name}处理完成"

        # 智能决定是否继续
        # 如果字典包含复杂信息且有数据，继续让LLM处理
        has_content = any(v is not None for v in result.values())
        is_complex = len(result) > 0 and has_content

        if is_complex:
            next_agent = "general_agent"  # 继续让LLM总结和处理
        else:
            next_agent = "none"  # 无数据，结束

    elif result is None:
        # None值：表示Agent没有产生数据
        data = None
        message_str = f"{agent_name}执行完成，无返回数据"
        next_agent = "none"  # 结束

    else:
        # 其他类型：包装到data中
        data = {"result": result}
        message_str = f"{agent_name}返回: {str(result)[:100]}"

        # 简单类型直接结束
        if isinstance(result, (str, int, float, bool)):
            next_agent = "none"
        else:
            # 复杂对象继续处理
            next_agent = "general_agent"

    # 构建task_list
    if input_message.task_list:
        # 继承输入的task_list
        task_list = input_message.task_list
    else:
        # 生成默认task_list
        task_list = [f"{agent_name}执行任务"]
        if data:
            task_list.append("处理返回结果")

    # 构建标准Message
    return Message(
        status="success",
        task_list=task_list,
        data=data,
        next_agent=next_agent,
        agent_selection_reason=f"由{agent_name}处理",
        message=message_str
    )

class Agent(BaseModel):
    """Agent 定义类"""
    
    name: str = Field(
        ...,
        description="Agent 的唯一标识名称",
        min_length=1,
        max_length=50,
    )
    
    description: str = Field(
        ...,
        description="Agent 的功能描述",
        min_length=10,
        max_length=200
    )

    parameters: Optional[Dict[str, str]] = Field(
        None,
        description="Agent 所需的参数及其描述",
    )
    
    handles: List[str] = Field(
        ...,
        description="Agent 能够处理的关键词或短语列表",
        min_items=1
    )
    
    is_active: bool = Field(
        default=True,
        description="Agent 是否处于活跃状态"
    )
    
    version: str = Field(
        default="1.0.0",
        description="Agent 版本号",
    )

    prompt_template: PromptTemplate = Field(
        default=None,
        description="Agent 的提示词模板",
    )

    supports_streaming: bool = Field(
        default=False,
        description="Agent是否支持流式处理（可选实现run_stream）"
    )
    
    def get_prompt(self) -> PromptTemplate:
        """获取 Agent 的提示词模板"""
        return self.prompt_template
    
    def run(self, message: Message) -> Union[Message, Dict[str, Any], Any]:
        """
        执行 Agent 的主要逻辑

        Args:
            message: 输入消息

        Returns:
            可以返回多种类型，系统会自动封装：
            - Message对象：完全自定义返回格式（高级用法）
            - Dict: 自动封装到Message.data中
            - 其他类型: 自动包装到Message.data的{"result": 返回值}中

        Examples:
            # 方式1：返回字典（推荐）
            def run(self, message):
                return {"sql": "SELECT * FROM books", "count": 10}

            # 方式2：返回简单值
            def run(self, message):
                return "处理成功"

            # 方式3：返回Message对象（完全控制）
            def run(self, message):
                return Message(
                    status="success",
                    task_list=["查询数据"],
                    data={"result": "..."},
                    next_agent="general_agent",
                    agent_selection_reason="需要查询",
                    message="查询完成"
                )

            # 方式4：直接返回输入message（不处理数据）
            def run(self, message):
                return message
        """
        raise NotImplementedError("子类必须实现 run 方法")

    def run_stream(self, message: Message) -> Generator[Dict[str, Any], None, None]:
        """
        可选的流式处理方法

        子类可以选择实现此方法以支持流式处理

        Args:
            message: 输入消息

        Yields:
            Dict: 流式事件字典
                - {"type": "progress", "data": {"progress": 0.5, "message": "处理中..."}}
                - {"type": "delta", "data": {"content": "部分结果"}}
                - {"type": "message", "data": {"message": 最终Message对象}}

        Example:
            def run_stream(self, message: Message):
                # 1. 进度更新
                yield {"type": "progress", "data": {"progress": 0.3, "message": "连接数据库"}}

                # 2. 处理数据
                result = self._process_data(message.data)

                # 3. 增量结果
                for chunk in self._format_result(result):
                    yield {"type": "delta", "data": {"content": chunk}}

                # 4. 最终消息
                message.data["result"] = result
                yield {"type": "message", "data": {"message": message.model_dump()}}
        """
        raise NotImplementedError(
            f"Agent '{self.name}' 未实现流式处理。"
            f"如需支持流式，请实现 run_stream 方法并设置 supports_streaming=True"
        )

    def __call__(self, message: Message, stream: bool = False) -> Union[Message, Generator[Dict[str, Any], None, None]]:
        """
        处理传入的消息并返回响应

        Args:
            message: 输入消息
            stream: 是否使用流式处理（仅当Agent支持时有效）

        Returns:
            stream=False: Message对象（原有行为）
            stream=True: Generator（如果Agent支持流式）

        Note:
            - 如果stream=True但Agent不支持，会回退到同步模式
            - run方法可以返回Message、Dict或其他类型，系统会自动封装
            - 确保向后兼容性
        """
        if stream and self.supports_streaming:
            try:
                # 流式模式暂不支持自动封装，需要返回标准事件格式
                return self.run_stream(message)
            except NotImplementedError:
                # 如果未实现run_stream，回退到同步模式
                logger.warning(
                    f"Agent '{self.name}' 不支持流式处理，回退到同步模式"
                )
                result = self.run(message)
                return normalize_agent_output(result, message, self.name)
        else:
            # 同步模式：自动封装输出
            result = self.run(message)
            return normalize_agent_output(result, message, self.name)

    # ========================================================================
    # 文件操作辅助方法
    # ========================================================================

    def upload_file(
        self,
        file_path: str,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        上传文件到文件服务

        Args:
            file_path: 文件路径
            session_id: 会话ID (可选)
            metadata: 额外的元数据 (可选)

        Returns:
            文件信息字典

        Example:
            def run(self, message: Message):
                # 上传文件
                file_info = self.upload_file("/path/to/file.pdf", session_id="session-123")

                # 返回结果
                return {
                    "file_id": file_info["file_id"],
                    "message": "文件上传成功"
                }
        """
        try:
            from fastapi import UploadFile

            # 创建模拟的UploadFile对象
            import os
            filename = os.path.basename(file_path)

            # 读取文件内容
            with open(file_path, 'rb') as f:
                content = f.read()

            # 创建临时的UploadFile-like对象
            class TempUploadFile:
                def __init__(self, filename, content):
                    self.filename = filename
                    self.content_type = "application/octet-stream"
                    self._content = content

                async def read(self):
                    return self._content

            # 异步上传
            import asyncio
            import concurrent.futures
            file_service = get_file_service()

            # 定义异步函数
            async def _upload_file():
                temp_file = TempUploadFile(filename, content)
                return await file_service.upload_file(temp_file, session_id, metadata)

            # 尝试在现有事件循环中运行
            try:
                loop = asyncio.get_running_loop()
                # 有运行中的事件循环，在新线程中运行
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        lambda: asyncio.run(_upload_file())
                    )
                    file_record = future.result()
            except RuntimeError:
                # 没有运行中的事件循环，直接运行
                file_record = asyncio.run(_upload_file())

            return file_record.to_dict()

        except Exception as e:
            logger.error(f"文件上传失败: {e}")
            return {"error": str(e)}

    def create_download_file(
        self,
        content: Union[str, bytes],
        filename: str,
        content_type: str = "application/octet-stream",
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        创建可供下载的文件

        Args:
            content: 文件内容 (字符串或字节)
            filename: 文件名
            content_type: MIME类型
            session_id: 会话ID (可选)

        Returns:
            文件信息字典，包含file_id可用于下载

        Example:
            def run(self, message: Message):
                # 生成CSV内容
                csv_content = "Name,Age\\nAlice,30\\nBob,25"

                # 创建下载文件
                file_info = self.create_download_file(
                    content=csv_content,
                    filename="report.csv",
                    content_type="text/csv",
                    session_id=message.session_id
                )

                return {
                    "message": "报告已生成",
                    "download_url": f"/files/{file_info['file_id']}"
                }
        """
        try:
            import asyncio
            import concurrent.futures
            file_service = get_file_service()

            # 定义异步函数
            async def _create_file():
                return await file_service.create_download_file(
                    content=content,
                    filename=filename,
                    content_type=content_type,
                    session_id=session_id
                )

            # 尝试在现有事件循环中运行
            try:
                loop = asyncio.get_running_loop()
                # 有运行中的事件循环，在新线程中运行
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        lambda: asyncio.run(_create_file())
                    )
                    file_record = future.result()
            except RuntimeError:
                # 没有运行中的事件循环，直接运行
                file_record = asyncio.run(_create_file())

            logger.info(f"创建下载文件成功: {filename} -> {file_record.file_id}")
            return file_record.to_dict()

        except Exception as e:
            logger.error(f"创建下载文件失败: {e}")
            return {"error": str(e)}

    def get_file(self, file_id: str) -> Optional[Dict[str, Any]]:
        """
        获取文件信息

        Args:
            file_id: 文件ID

        Returns:
            文件信息字典或None
        """
        try:
            file_service = get_file_service()
            file_record = file_service.get_file(file_id)

            if file_record:
                return file_record.to_dict()
            return None

        except Exception as e:
            logger.error(f"获取文件信息失败: {e}")
            return None

    def read_file_content(self, file_path: str) -> Optional[str]:
        """
        读取文件内容（文本文件）

        Args:
            file_path: 文件路径

        Returns:
            文件内容字符串或None

        Example:
            def run(self, message: Message):
                # 读取上传的PDF文本内容
                content = self.read_file_content("/path/to/document.txt")

                if content:
                    return {"content": content}
                else:
                    return {"error": "无法读取文件"}
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"读取文件失败: {e}")
            return None

    def read_file_binary(self, file_path: str) -> Optional[bytes]:
        """
        读取文件内容（二进制）

        Args:
            file_path: 文件路径

        Returns:
            文件内容字节或None
        """
        try:
            with open(file_path, 'rb') as f:
                return f.read()
        except Exception as e:
            logger.error(f"读取文件失败: {e}")
            return None

class AgentLoader:
    """Agent 加载器类"""
    
    def __init__(self):
        self.agents: Dict[str, Agent] = {}
    
    def add_agent(self, agent: Agent) -> None:
        """添加一个 Agent"""
        if agent.name in self.agents:
            raise ValueError(f"Agent '{agent.name}' 已存在")
        self.agents[agent.name] = agent
    
    def remove_agent(self, agent_name: str) -> None:
        """移除一个 Agent"""
        if agent_name not in self.agents:
            raise ValueError(f"Agent '{agent_name}' 不存在")
        del self.agents[agent_name]
    
    def get_agent(self, agent_name: str) -> Optional[Agent]:
        """获取指定名称的 Agent"""
        return self.agents.get(agent_name)
    
    def get_all_agents(self) -> Dict[str, Agent]:
        """获取所有 Agent"""
        return self.agents.copy()
    
    def get_active_agents(self) -> Dict[str, Agent]:
        """获取所有活跃的 Agent"""
        return {name: agent for name, agent in self.agents.items() if agent.is_active}
    
    def to_json(self) -> dict:
        """转换为所需的 JSON 格式"""
        available_agents = {}
        
        for name, agent in self.get_active_agents().items():
            available_agents[name] = {
                "description": agent.description,
                "handles": agent.handles,
                "parameters": agent.parameters or {}
            }
        
        return {"available_agents": available_agents}
    
    def load_from_list(self, agents: List[Agent]) -> None:
        """从 Agent 列表加载"""
        for agent in agents:
            self.add_agent(agent)