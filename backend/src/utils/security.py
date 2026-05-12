"""
通用安全工具：密码哈希、JWT 签发与验证
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import ValidationError

from src.core.settings import (
    JWT_SECRET_KEY,
    JWT_ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)
from src.core.schemas import TokenPayload


# —————— 密码工具 ——————
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """明文 → bcrypt 哈希"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证明文与哈希是否匹配"""
    return pwd_context.verify(plain_password, hashed_password)


# —————— JWT 工具 ——————
def create_access_token(data: dict) -> str:
    """签发 JWT Token，自动追加过期时间"""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[TokenPayload]:
    """解析 Token，返回载荷；失败或过期返回 None"""
    try:
        payload = jwt.decode(
            token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM]
        )
        return TokenPayload(**payload)
    except (JWTError, ValidationError):
        return None