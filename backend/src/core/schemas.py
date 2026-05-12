"""跨模块共享的轻量模型（避免 utils 反向依赖 auth）"""
from typing import Optional

from pydantic import BaseModel


class TokenPayload(BaseModel):
    """JWT 载荷（解析 Token 后使用）"""

    sub: Optional[str] = None
