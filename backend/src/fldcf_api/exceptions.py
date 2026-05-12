"""
FLDCF 领域：推理链异常 → BizError（仅供 fldcf_api 使用）。

统一响应信封见 utils.exceptions；具体 HTTP 状态与业务含义按本模块约定转换。
"""

from __future__ import annotations

from src.utils.logging_manager import get_logger

from src.utils.exceptions import BizError

logger = get_logger(__name__)


def reraise_predict_as_biz(exc: BaseException) -> None:
    """将 /predict 推理链中的异常转为 BizError 并抛出（恒不返回）。"""
    if isinstance(exc, BizError):
        raise exc
    if isinstance(exc, FileNotFoundError):
        raise BizError(str(exc), code="500", status_code=500) from exc
    if isinstance(exc, RuntimeError):
        raise BizError(str(exc), code="503", status_code=503) from exc
    logger.exception("FLDCF /predict 推理异常")
    raise BizError(str(exc), code="500", status_code=500) from exc
