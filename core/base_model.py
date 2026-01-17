from typing import TypeVar, Generic, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum

T = TypeVar('T')


class StreamEventType(str, Enum):
    """流式事件类型枚举"""
    DELTA = "delta"              # LLM增量内容（文本片段）
    AGENT_START = "agent_start"  # Agent开始执行
    AGENT_END = "agent_end"      # Agent结束执行
    MESSAGE = "message"          # 完整Message对象
    ERROR = "error"              # 错误信息
    METADATA = "metadata"        # 元数据信息
    STATUS = "status"            # 状态更新


class StreamEvent(BaseModel):
    """流式事件对象"""
    type: StreamEventType = Field(
        ...,
        description="事件类型"
    )
    data: Dict[str, Any] = Field(
        default_factory=dict,
        description="事件数据，内容根据type不同而变化"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="可选的元数据（如时间戳、agent名称等）"
    )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式，用于JSON序列化"""
        return {
            "type": self.type.value,
            "data": self.data,
            "metadata": self.metadata
        }

class Message(BaseModel, Generic[T]):
    """大模型响应基类"""
    
    status: Literal["success", "error"] = Field(
        ...,
        description="请求状态。成功时必须为 'success'，失败时必须为 'error'"
    )

    task_list: list[str] = Field(
        ...,
        description="任务列表。每个任务是一个字符串，描述需要完成的具体任务"
    )
    
    data: Optional[T] = Field(
        None,
        description="当 status 为 'success' 时，此字段存在，用于存放主响应内容"
    )
    
    next_agent: str = Field(
        ...,
        description="必须从available_agents中选择一个名称"
    )
    
    agent_selection_reason: str = Field(
        ...,
        description="简要说明选择该Agent的原因"
    )
    
    message: Optional[str] = Field(
        None,
        description="成功时为可选的成功消息或总结，失败时必须存在用于描述错误详情"
    )