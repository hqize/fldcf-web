from typing import Optional

from pydantic import BaseModel, Field

from src.core.schemas import TokenPayload  # noqa: F401 对外兼容


# ==================== 认证相关 ====================

class Token(BaseModel):
    """登录成功后返回的Token"""
    access_token: str
    token_type: str = "bearer"


# ==================== 用户相关 ====================

class UserBase(BaseModel):
    """用户公共字段"""
    username: str = Field(..., min_length=2, max_length=50)


class UserCreate(UserBase):
    """公开注册（默认角色 user；管理员仅能通过初始化或后续后台流程创建）"""
    password: str = Field(..., min_length=4, max_length=20)
    avatar_url: Optional[str] = Field(None, max_length=512)


class UserUpdate(BaseModel):
    """更新用户信息（字段均可选，仅提交需要修改的项）"""
    password: Optional[str] = Field(None, min_length=4, max_length=20)
    avatar_url: Optional[str] = Field(None, max_length=512)


class UserOut(UserBase):
    """返回给前端的用户信息（不含密码）"""
    id: int
    role: str
    avatar_url: Optional[str] = None

    class Config:
        # Pydantic v2 写法，允许从 Tortoise ORM 对象直接转换
        from_attributes = True


class UsernameAvailability(BaseModel):
    """用户名可用性检查返回"""
    username: str
    available: bool