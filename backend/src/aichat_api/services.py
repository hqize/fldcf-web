"""
DeepSeek（OpenAI兼容接口）调用
"""

from __future__ import annotations

import asyncio
import os

from openai import OpenAI

from src.utils.exceptions import BizError
from src.utils.logging_manager import get_logger

logger = get_logger(__name__)

VALID_ROLES = frozenset({"system", "user", "assistant"})

_client: OpenAI | None = None


def default_model() -> str:
    return (os.getenv("DEEPSEEK_MODEL") or "deepseek-chat").strip()


def is_configured() -> bool:
    base = (os.getenv("DEEPSEEK_BASE_URL") or "").strip()
    key = (os.getenv("DEEPSEEK_API_KEY") or "").strip()
    return bool(base and key)


def _ensure_client() -> OpenAI:
    global _client
    if _client is None:
        base = (os.getenv("DEEPSEEK_BASE_URL") or "").strip()
        key = (os.getenv("DEEPSEEK_API_KEY") or "").strip()
        if not base or not key:
            raise BizError(
                "未配置 DeepSeek：请在服务端 .env 设置 DEEPSEEK_BASE_URL 与 DEEPSEEK_API_KEY",
                code="503",
                status_code=503,
            )
        _client = OpenAI(base_url=base.rstrip("/"), api_key=key)
    return _client


def normalize_messages(raw: list[dict[str, str]]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for m in raw:
        role = (m.get("role") or "").strip()
        content = (m.get("content") or "").strip()
        if role not in VALID_ROLES:
            raise BizError(f"非法 role: {role!r}，仅允许 system/user/assistant", code="400", status_code=400)
        if not content:
            raise BizError("消息 content 不能为空", code="400", status_code=400)
        out.append({"role": role, "content": content})
    return out


def sync_chat(messages: list[dict[str, str]], model: str) -> str:
    client = _ensure_client()
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            stream=False,
        )
    except Exception as e:
        logger.exception("DeepSeek 调用失败")
        raise BizError(str(e) or "模型调用失败", code="502", status_code=502) from e

    msg = resp.choices[0].message
    content = getattr(msg, "content", None)
    if content is None:
        return ""
    return content


async def chat_async(messages: list[dict[str, str]], model: str | None) -> tuple[str, str]:
    m = (model or "").strip() or default_model()
    normalized = normalize_messages(messages)
    text = await asyncio.to_thread(sync_chat, normalized, m)
    return text, m
