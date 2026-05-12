"""
统一 API 响应模型
"""
from __future__ import annotations

from typing import Any, Generic, TypeVar

from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel

T = TypeVar("T")


class Result(BaseModel, Generic[T]):
    """统一响应体：code + msg + data（与 OpenAPI、前端契约一致）"""

    code: str
    msg: str
    data: T | None = None

    @staticmethod
    def success(data: Any | None = None, msg: str = "请求成功") -> Result[Any]:
        json_data = jsonable_encoder(data) if data is not None else None
        return Result(code="200", msg=msg, data=json_data)

    @staticmethod
    def error(msg: str = "请求失败", code: str = "500") -> Result[Any]:
        return Result(code=code, msg=msg, data=None)
