"""
认证模块 - 路由层
"""
from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.security import OAuth2PasswordRequestForm
from src.utils.security import create_access_token

from .services import (
    authenticate_user,
    register_user,
    get_current_user,
    is_username_available,
    replace_user_avatar_from_upload,
    update_user_profile,
)
from .models import User
from .schemas import Token, UserCreate, UserOut, UserUpdate, UsernameAvailability
from src.utils.exceptions import BizError
from src.utils.response import Result

router = APIRouter()


@router.post("/login", response_model=Result[Token], summary="登录")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    ***登录接口***
    - 用 form-data 格式提交 username 和 password
    - 返回 JWT Token
    """
    user = await authenticate_user(form_data.username, form_data.password)
    if not user:
        raise BizError("用户名或密码错误", code="401", status_code=401)

    access_token = create_access_token(data={"sub": user.username})
    return Result.success({"access_token": access_token, "token_type": "bearer"})


@router.post("/register", response_model=Result[UserOut], summary="注册")
async def register(user_in: UserCreate):
    """
    ***注册接口（公开）***
    - 创建新用户，默认角色为 user。
    """
    user = await register_user(
        username=user_in.username,
        password=user_in.password,
        avatar_url=user_in.avatar_url,
    )
    return Result.success(user)


@router.patch("/me", response_model=Result[UserOut], summary="更新当前用户资料")
async def patch_me(body: UserUpdate, current_user: User = Depends(get_current_user)):
    """更新密码、头像 URL 等（仅提交需要修改的字段）"""
    user = await update_user_profile(current_user, body)
    return Result.success(user)


@router.post(
    "/me/avatar",
    response_model=Result[UserOut],
    summary="上传头像图片",
    description="multipart 字段名 file；JPG/PNG/GIF/WebP，最大 2MB；保存至 static 并更新 avatar_url",
)
async def upload_my_avatar(
    file: UploadFile = File(..., description="头像图片"),
    current_user: User = Depends(get_current_user),
):
    data = await file.read()
    user = await replace_user_avatar_from_upload(current_user, data, file.content_type or "")
    return Result.success(user)


@router.get("/me", response_model=Result[UserOut])
async def get_me(current_user: User = Depends(get_current_user)):
    """
    ***查询本账号(已登录时)***
    """
    return Result.success(current_user)


@router.get("/check-username", response_model=Result[UsernameAvailability], summary="检查用户名可用性")
async def check_username(username: str):
    """注册前检查用户名是否可用"""
    available = await is_username_available(username)
    return Result.success({"username": username, "available": available})