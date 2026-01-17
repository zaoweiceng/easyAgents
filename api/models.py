"""
API请求和响应模型
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class ChatRequest(BaseModel):
    """聊天请求模型"""
    query: str = Field(
        ...,
        description="用户查询内容",
        min_length=1,
        max_length=5000
    )
    stream: bool = Field(
        default=False,
        description="是否使用流式响应"
    )
    session_id: Optional[str] = Field(
        None,
        description="会话ID，用于多轮对话（可选）"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "query": "查询图书信息",
                "stream": False,
                "session_id": "optional-session-id"
            }
        }


class ChatResponse(BaseModel):
    """聊天响应模型（同步模式）"""
    status: str = Field(..., description="响应状态")
    response: List[Dict[str, Any]] = Field(..., description="响应消息列表")
    session_id: Optional[str] = Field(None, description="会话ID")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "response": [
                    {
                        "role": "user",
                        "content": "查询图书信息",
                        "message": None
                    },
                    {
                        "role": "system",
                        "content": "查询结果...",
                        "message": "查询完成"
                    }
                ],
                "session_id": "session-123"
            }
        }


class AgentInfo(BaseModel):
    """Agent信息模型"""
    name: str = Field(..., description="Agent名称")
    description: str = Field(..., description="Agent描述")
    handles: List[str] = Field(..., description="Agent处理的关键词")
    is_active: bool = Field(..., description="Agent是否活跃")
    version: str = Field(..., description="Agent版本")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "sql_agent",
                "description": "专门用于查询图书数据库",
                "handles": ["图书信息查询", "书籍查询"],
                "is_active": True,
                "version": "1.0.0"
            }
        }


class AgentsListResponse(BaseModel):
    """Agent列表响应模型"""
    status: str = Field(..., description="响应状态")
    count: int = Field(..., description="Agent数量")
    agents: List[AgentInfo] = Field(..., description="Agent信息列表")


class HealthResponse(BaseModel):
    """健康检查响应模型"""
    status: str = Field(..., description="服务状态")
    service: str = Field(..., description="服务名称")
    version: str = Field(..., description="服务版本")
    agents_loaded: int = Field(..., description="已加载的Agent数量")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "ok",
                "service": "easyAgent API",
                "version": "0.2.0",
                "agents_loaded": 3
            }
        }


class ErrorResponse(BaseModel):
    """错误响应模型"""
    error: str = Field(..., description="错误类型")
    message: str = Field(..., description="错误消息")
    detail: Optional[str] = Field(None, description="详细错误信息")

    class Config:
        json_schema_extra = {
            "example": {
                "error": "ValidationError",
                "message": "请求参数错误",
                "detail": "query字段不能为空"
            }
        }
