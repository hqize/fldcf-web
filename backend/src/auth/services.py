"""
认证模块 - 业务逻辑层
"""
from __future__ import annotations

import uuid
from pathlib import Path
from typing import Optional

from fastapi import Depends
from src.core.settings import AUTH_SCHEMA, AUTH_INIT_USERNAME, AUTH_INIT_PASSWORD
from .models import User
from .schemas import UserUpdate
from .repository import (
    get_user_by_username,
    create_user as repo_create_user,
)
from src.utils.security import (
    hash_password,
    verify_password,
    decode_access_token,
)
from src.utils.exceptions import BizError
from src.utils.logging_manager import get_logger

logger = get_logger(__name__)

# ---------- 头像文件（存 static/uploads/avatars，avatar_url 存 /static/... 路径）----------

MAX_AVATAR_BYTES = 2 * 1024 * 1024
_AVATAR_CT_EXT = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
}


def avatar_upload_dir() -> Path:
    d = Path(__file__).resolve().parent.parent / "static" / "uploads" / "avatars"
    d.mkdir(parents=True, exist_ok=True)
    return d


def unlink_managed_avatar_file(url: str | None) -> None:
    """删除本地上传的旧头像（路径形如 /static/uploads/avatars/xxx）"""
    if not url:
        return
    u = url.strip()
    prefix = "/static/uploads/avatars/"
    if not u.startswith(prefix):
        return
    name = u[len(prefix) :].strip("/")
    if not name or ".." in name or "/" in name:
        return
    base = avatar_upload_dir().resolve()
    path = (base / name).resolve()
    try:
        path.relative_to(base)
    except ValueError:
        return
    if path.is_file():
        try:
            path.unlink()
        except OSError:
            pass


async def replace_user_avatar_from_upload(user: User, data: bytes, content_type: str) -> User:
    raw_ct = (content_type or "").split(";")[0].strip().lower()
    if raw_ct not in _AVATAR_CT_EXT:
        raise BizError(
            "仅支持JPG、PNG、GIF、WebP图片",
            code="400",
            status_code=400,
        )
    if len(data) == 0:
        raise BizError("文件为空", code="400", status_code=400)
    if len(data) > MAX_AVATAR_BYTES:
        raise BizError("头像图片不超过2MB", code="413", status_code=413)

    unlink_managed_avatar_file(user.avatar_url)
    ext = _AVATAR_CT_EXT[raw_ct]
    fname = f"{user.id}_{uuid.uuid4().hex[:16]}{ext}"
    path = avatar_upload_dir() / fname
    path.write_bytes(data)
    user.avatar_url = f"/static/uploads/avatars/{fname}"
    await user.save()
    return user


async def authenticate_user(username: str, password: str) -> Optional[User]:
    """验证用户名密码，成功返回用户对象"""
    user = await get_user_by_username(username)
    if not user or not verify_password(password, user.password_hash):
        return None
    return user


async def register_user(
    username: str,
    password: str,
    role: str = "user",
    avatar_url: Optional[str] = None,
) -> User:
    """注册新用户（校验重名 + 哈希密码 + 创建用户）"""
    existing = await get_user_by_username(username)
    if existing:
        raise BizError("用户名已存在", code="400", status_code=400)

    hashed = hash_password(password)
    return await repo_create_user(
        username=username,
        password_hash=hashed,
        role=role,
        avatar_url=avatar_url,
    )


async def update_user_profile(user: User, data: UserUpdate) -> User:
    """更新当前用户资料（密码、头像等）"""
    payload = data.model_dump(exclude_unset=True)
    if "password" in payload and payload["password"]:
        user.password_hash = hash_password(payload["password"])
    if "avatar_url" in payload:
        new_val = payload["avatar_url"]
        if user.avatar_url != new_val:
            unlink_managed_avatar_file(user.avatar_url)
        user.avatar_url = new_val if new_val else None
    if payload:
        await user.save()
    return user


async def is_username_available(username: str) -> bool:
    """检查用户名是否可用（未被占用）"""
    existing = await get_user_by_username(username)
    return existing is None


# ==================== 初始化管理员 ====================

async def init_admin_user():
    """启动时创建默认管理员"""
    admin = await get_user_by_username(AUTH_INIT_USERNAME)
    if not admin:
        await register_user(
            username=AUTH_INIT_USERNAME,
            password=AUTH_INIT_PASSWORD,
            role="admin",
        )
        logger.info("初始管理员已创建：%s", AUTH_INIT_USERNAME)
    else:
        logger.info("管理员账号已存在：%s", AUTH_INIT_USERNAME)


# ==================== 获取当前用户的依赖 ====================

async def get_current_user(token: str = Depends(AUTH_SCHEMA)) -> User:
    """从 Token 解析当前登录用户"""
    token_data = decode_access_token(token)
    if token_data is None or token_data.sub is None:
        raise BizError.unauthorized()

    user = await get_user_by_username(token_data.sub)
    if user is None:
        raise BizError.unauthorized("用户不存在")
    return user


async def get_current_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """获取当前管理员用户，非管理员抛403"""
    if current_user.role != "admin":
        raise BizError.forbidden()
    return current_user