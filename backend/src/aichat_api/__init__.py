"""
AI助手模块：

- router   HTTP 路由
- services DeepSeek OpenAI 兼容客户端
- schemas  Pydantic 请求 / 响应
"""

from .router import router

__all__ = ["router"]
