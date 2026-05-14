"""
AI 助手HTTP 入口
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from src.auth.models import User
from src.auth.services import get_current_user
from src.utils.response import Result

from .schemas import AiChatRequest, AiChatResponse, AiChatStatusResponse
from .services import chat_async, default_model, is_configured

router = APIRouter()


@router.get(
    "/status",
    response_model=Result[AiChatStatusResponse],
    summary="AI助手配置状态",
    description="是否已配置DeepSeek环境变量（不暴露密钥）；默认模型名",
)
def get_status():
    return Result.success(
        AiChatStatusResponse(
            configured=is_configured(),
            default_model=default_model(),
        )
    )


@router.post(
    "/chat",
    response_model=Result[AiChatResponse],
    summary="对话（DeepSeek）",
    description="OpenAI兼容chat completions；需在Header携带Bearer JWT",
)
async def chat(body: AiChatRequest, _: User = Depends(get_current_user)):
    msgs = [{"role": m.role, "content": m.content} for m in body.messages]
    reply, model_used = await chat_async(msgs, body.model)
    return Result.success(AiChatResponse(reply=reply, model=model_used))
