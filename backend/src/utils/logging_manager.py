"""
统一日志：warnings → logging，basicConfig(force=True)覆盖旧配置，uvicorn子logger使用同一套格式

"""
from __future__ import annotations

import logging
import logging.config
import os
import sys
import warnings
from typing import Any, Union

DEFAULT_FORMAT = "%(asctime)s %(levelname)-7s [%(name)s] %(message)s"
DEFAULT_DATEFMT = "%Y-%m-%d %H:%M:%S"

Level = Union[int, str, None]


def parse_log_level(level: Level) -> int:
    if level is None:
        return logging.INFO
    if isinstance(level, int):
        return level
    name = str(level).strip().upper()
    return getattr(logging, name, logging.INFO)


def _level_to_dict_name(resolved: int) -> str:
    name = logging.getLevelName(resolved)
    if isinstance(name, str) and not name.startswith("Level "):
        return name
    return "INFO"


def _warn_to_log(message, category, filename, lineno, file=None, line=None):
    logging.getLogger("py.warnings").warning(
        "%s:%s: %s: %s",
        filename,
        lineno,
        category.__name__,
        message,
    )


def build_uvicorn_log_config(
    level: Level = None,
    *,
    fmt: str = DEFAULT_FORMAT,
    datefmt: str = DEFAULT_DATEFMT,
) -> dict[str, Any]:
    """供uvicorn.run(log_config=...)与 setup_logging内dictConfig共用"""
    env_level = os.getenv("LOG_LEVEL", "INFO")
    resolved = parse_log_level(level if level is not None else env_level)
    level_name = _level_to_dict_name(resolved)

    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": fmt,
                "datefmt": datefmt,
            },
        },
        "handlers": {
            "default": {
                "formatter": "default",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
            },
        },
        "loggers": {
            "uvicorn": {
                "handlers": ["default"],
                "level": level_name,
                "propagate": False,
            },
            # 须挂 handler；仅 propagate=False 且无 handler 会导致启动日志丢失
            "uvicorn.error": {
                "handlers": ["default"],
                "level": level_name,
                "propagate": False,
            },
            "uvicorn.access": {
                "handlers": ["default"],
                "level": level_name,
                "propagate": False,
            },
        },
    }


def setup_logging(
    level: Level = None,
    *,
    fmt: str = DEFAULT_FORMAT,
    datefmt: str = DEFAULT_DATEFMT,
) -> dict[str, Any]:
    """
    - 接管 warnings → logging（py.warnings）
    - basicConfig(force=True) 覆盖已有配置，输出到 stdout
    - dictConfig uvicorn 相关 logger，与业务日志同一格式
    """
    env_level = os.getenv("LOG_LEVEL", "INFO")
    resolved = parse_log_level(level if level is not None else env_level)

    warnings.showwarning = _warn_to_log

    logging.basicConfig(
        level=resolved,
        format=fmt,
        datefmt=datefmt,
        force=True,
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    cfg = build_uvicorn_log_config(level, fmt=fmt, datefmt=datefmt)
    logging.config.dictConfig(cfg)
    return cfg


def get_uvicorn_log_config(
    level: Level = None,
    *,
    fmt: str = DEFAULT_FORMAT,
    datefmt: str = DEFAULT_DATEFMT,
) -> dict[str, Any]:
    """与setup_logging内uvicorn块一致，供uvicorn.run再次套用（启动时会 dictConfig）"""
    return build_uvicorn_log_config(level, fmt=fmt, datefmt=datefmt)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
