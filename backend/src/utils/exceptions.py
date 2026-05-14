"""
统一异常：BizError + 全局注册到 FastAPI

"""
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from src.utils.logging_manager import get_logger
from src.utils.response import Result

logger = get_logger(__name__)


class BizError(Exception):
    """业务与鉴权错误：由全局处理器转为Result"""

    def __init__(
        self,
        msg: str,
        *,
        code: str = "400",
        status_code: int = 400,
        headers: dict[str, str] | None = None,
    ):
        super().__init__(msg)
        self.msg = msg
        self.code = code
        self.status_code = status_code
        self.headers = headers

    @classmethod
    def unauthorized(cls, msg: str = "无效的认证凭据") -> "BizError":
        """401 + Bearer（OAuth2密码流/JWT依赖约定）"""
        return cls(
            msg,
            code="401",
            status_code=401,
            headers={"WWW-Authenticate": "Bearer"},
        )

    @classmethod
    def forbidden(cls, msg: str = "权限不足，仅管理员可操作") -> "BizError":
        return cls(msg, code="403", status_code=403)


def _detail_to_msg(detail: Any) -> str:
    if isinstance(detail, str):
        return detail
    if isinstance(detail, list):
        parts: list[str] = []
        for item in detail:
            if isinstance(item, dict):
                loc = item.get("loc", ())
                msg = item.get("msg", "")
                parts.append(f"{'.'.join(str(x) for x in loc)}: {msg}")
            else:
                parts.append(str(item))
        return "; ".join(parts)
    return str(detail)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(BizError)
    async def biz_error_handler(_: Request, exc: BizError) -> JSONResponse:
        body = Result(code=exc.code, msg=exc.msg, data=None)
        return JSONResponse(
            status_code=exc.status_code,
            content=jsonable_encoder(body),
            headers=exc.headers,
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
        code = str(exc.status_code)
        msg = _detail_to_msg(exc.detail)
        body = Result(code=code, msg=msg, data=None)
        return JSONResponse(
            status_code=exc.status_code,
            content=jsonable_encoder(body),
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        _: Request, exc: RequestValidationError
    ) -> JSONResponse:
        raw = exc.errors()
        msg = _detail_to_msg(raw)
        body = Result(code="422", msg=msg, data=jsonable_encoder(raw))
        return JSONResponse(status_code=422, content=jsonable_encoder(body))

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
        logger.error("未处理的异常", exc_info=exc)
        body = Result(code="500", msg="服务器内部错误", data=None)
        return JSONResponse(status_code=500, content=jsonable_encoder(body))
