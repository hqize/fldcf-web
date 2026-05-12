"""
AI 助手模块（与 auth / fldcf_api 同级）：

- router   HTTP 路由
- services DeepSeek OpenAI 兼容客户端
- schemas  Pydantic 请求 / 响应
"""

from .router import router

__all__ = ["router"]
