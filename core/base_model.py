from typing import TypeVar, Generic, Optional, Literal
from pydantic import BaseModel, Field

T = TypeVar('T')

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