"""跨模块共享的轻量模型"""
from typing import Optional

from pydantic import BaseModel


class TokenPayload(BaseModel):
    """JWT载荷（解析Token后使用）"""

    sub: Optional[str] = None
