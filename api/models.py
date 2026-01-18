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
    # LLM参数（可选，如果不提供则使用环境变量配置）
    temperature: Optional[float] = Field(
        None,
        ge=0.0,
        le=2.0,
        description="温度参数（0-2）"
    )
    top_p: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="top_p参数（0-1）"
    )
    top_k: Optional[int] = Field(
        None,
        ge=1,
        description="top_k参数"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "query": "查询图书信息",
                "stream": False,
                "session_id": "optional-session-id",
                "temperature": 0.7,
                "top_p": 0.9,
                "top_k": 40
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


# ============================================================================
# 历史记录相关模型
# ============================================================================

class ConversationInfo(BaseModel):
    """会话信息模型"""
    id: int = Field(..., description="会话ID")
    title: str = Field(..., description="会话标题")
    session_id: str = Field(..., description="会话唯一标识")
    created_at: str = Field(..., description="创建时间")
    updated_at: str = Field(..., description="更新时间")
    message_count: int = Field(..., description="消息数量")
    model_name: Optional[str] = Field(None, description="使用的模型")

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "title": "查询图书信息",
                "session_id": "abc123",
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:05:00",
                "message_count": 5,
                "model_name": "openai/gpt-oss-20b"
            }
        }


class MessageDetail(BaseModel):
    """消息详情模型"""
    id: int = Field(..., description="消息ID")
    role: str = Field(..., description="消息角色")
    content: str = Field(..., description="消息内容")
    data: Optional[Dict[str, Any]] = Field(None, description="额外数据")
    events: Optional[List[Dict[str, Any]]] = Field(None, description="事件列表")
    created_at: str = Field(..., description="创建时间")

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "role": "user",
                "content": "查询图书信息",
                "data": None,
                "events": None,
                "created_at": "2024-01-01T00:00:00"
            }
        }


class ConversationDetail(BaseModel):
    """会话详情模型"""
    conversation: ConversationInfo = Field(..., description="会话信息")
    messages: List[MessageDetail] = Field(..., description="消息列表")

    class Config:
        json_schema_extra = {
            "example": {
                "conversation": {
                    "id": 1,
                    "title": "查询图书信息",
                    "session_id": "abc123",
                    "created_at": "2024-01-01T00:00:00",
                    "updated_at": "2024-01-01T00:05:00",
                    "message_count": 5,
                    "model_name": "openai/gpt-oss-20b"
                },
                "messages": [
                    {
                        "id": 1,
                        "role": "user",
                        "content": "查询图书信息",
                        "data": None,
                        "events": None,
                        "created_at": "2024-01-01T00:00:00"
                    }
                ]
            }
        }


class CreateConversationRequest(BaseModel):
    """创建会话请求"""
    title: str = Field(..., min_length=1, max_length=200, description="会话标题")
    model_name: Optional[str] = Field(None, description="使用的模型")

    class Config:
        json_schema_extra = {
            "example": {
                "title": "新对话",
                "model_name": "openai/gpt-oss-20b"
            }
        }


class UpdateConversationTitleRequest(BaseModel):
    """更新标题请求"""
    title: str = Field(..., min_length=1, max_length=200, description="新标题")

    class Config:
        json_schema_extra = {
            "example": {
                "title": "更新后的标题"
            }
        }


class ConversationsListResponse(BaseModel):
    """会话列表响应"""
    status: str = Field(..., description="响应状态")
    conversations: List[ConversationInfo] = Field(..., description="会话列表")
    total: int = Field(..., description="总数")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "conversations": [
                    {
                        "id": 1,
                        "title": "查询图书信息",
                        "session_id": "abc123",
                        "created_at": "2024-01-01T00:00:00",
                        "updated_at": "2024-01-01T00:05:00",
                        "message_count": 5,
                        "model_name": "openai/gpt-oss-20b"
                    }
                ],
                "total": 1
            }
        }


class ConversationResponse(BaseModel):
    """会话详情响应"""
    status: str = Field(..., description="响应状态")
    data: ConversationDetail = Field(..., description="会话详情")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "data": {
                    "conversation": {
                        "id": 1,
                        "title": "查询图书信息",
                        "session_id": "abc123",
                        "created_at": "2024-01-01T00:00:00",
                        "updated_at": "2024-01-01T00:05:00",
                        "message_count": 5,
                        "model_name": "openai/gpt-oss-20b"
                    },
                    "messages": []
                }
            }
        }


# ============================================================================
# 文件管理相关模型
# ============================================================================

class FileInfo(BaseModel):
    """文件信息模型"""
    file_id: str = Field(..., description="文件唯一标识")
    original_filename: str = Field(..., description="原始文件名")
    stored_filename: str = Field(..., description="存储文件名")
    file_size: int = Field(..., description="文件大小(字节)")
    content_type: str = Field(..., description="文件MIME类型")
    session_id: Optional[str] = Field(None, description="关联的会话ID")
    created_at: str = Field(..., description="上传时间")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="额外元数据")

    class Config:
        json_schema_extra = {
            "example": {
                "file_id": "uuid-123",
                "original_filename": "document.pdf",
                "stored_filename": "uuid-123.pdf",
                "file_size": 1024000,
                "content_type": "application/pdf",
                "session_id": "session-abc",
                "created_at": "2024-01-01T00:00:00",
                "metadata": {}
            }
        }


class FileUploadResponse(BaseModel):
    """文件上传响应"""
    status: str = Field(..., description="响应状态")
    message: str = Field(..., description="响应消息")
    file: FileInfo = Field(..., description="文件信息")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "message": "文件上传成功",
                "file": {
                    "file_id": "uuid-123",
                    "original_filename": "document.pdf",
                    "stored_filename": "uuid-123.pdf",
                    "file_size": 1024000,
                    "content_type": "application/pdf",
                    "session_id": "session-abc",
                    "created_at": "2024-01-01T00:00:00",
                    "metadata": {}
                }
            }
        }


class FileListResponse(BaseModel):
    """文件列表响应"""
    status: str = Field(..., description="响应状态")
    total: int = Field(..., description="文件总数")
    files: List[FileInfo] = Field(..., description="文件列表")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "total": 2,
                "files": [
                    {
                        "file_id": "uuid-123",
                        "original_filename": "document.pdf",
                        "stored_filename": "uuid-123.pdf",
                        "file_size": 1024000,
                        "content_type": "application/pdf",
                        "session_id": "session-abc",
                        "created_at": "2024-01-01T00:00:00",
                        "metadata": {}
                    }
                ]
            }
        }


class FileDeleteResponse(BaseModel):
    """文件删除响应"""
    status: str = Field(..., description="响应状态")
    message: str = Field(..., description="响应消息")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "message": "文件删除成功"
            }
        }
