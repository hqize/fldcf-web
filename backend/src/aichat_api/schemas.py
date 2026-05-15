"""
AI 对话请求 / 响应模型（与前端契约一致）
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ChatMessageIn(BaseModel):
    role: str = Field(..., description="system|user|assistant")
    content: str = Field(..., min_length=1, max_length=32000)


class AiChatRequest(BaseModel):
    messages: list[ChatMessageIn] = Field(..., min_length=1, max_length=50)
    model: str | None = Field(None, description="可选；省略则用服务器默认DEEPSEEK_MODEL")


class AiChatResponse(BaseModel):
    reply: str
    model: str


class AiChatStatusResponse(BaseModel):
    configured: bool
    default_model: str
