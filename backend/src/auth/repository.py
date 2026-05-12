"""
认证模块 - 数据访问层（Repository）
"""
from typing import Optional

from .models import User


async def get_user_by_username(username: str) -> Optional[User]:
    """根据用户名查询用户"""
    return await User.get_or_none(username=username)


async def create_user(
    username: str,
    password_hash: str,
    role: str = "user",
    avatar_url: Optional[str] = None,
) -> User:
    """创建用户（仅负责数据写入）"""
    return await User.create(
        username=username,
        password_hash=password_hash,
        role=role,
        avatar_url=avatar_url,
    )
