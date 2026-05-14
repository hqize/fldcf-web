"""
应用全局配置（敏感项优先从环境变量读取）

上线时设置 ENV=production，并必须提供JWT_SECRET_KEY、DB_URL等
"""
import os
from pathlib import Path
from typing import Optional

from fastapi.security import OAuth2PasswordBearer

from src.utils.logging_manager import get_logger

_settings_log = get_logger(__name__)

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

_BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
if load_dotenv:
    # 主配置：backend/.env
    load_dotenv(_BACKEND_ROOT / ".env")
    # 可选补充：backend/src/aichat_api/.env(仅当变量尚未设置时写入，不覆盖OS已有环境变量）
    _aichat_dotenv = _BACKEND_ROOT / "src" / "aichat_api" / ".env"
    if _aichat_dotenv.is_file():
        load_dotenv(_aichat_dotenv, override=False)


def _env(key: str, default: Optional[str] = None) -> Optional[str]:
    v = os.getenv(key)
    if v is None or v == "":
        return default
    return v


ENV = (_env("ENV", "development") or "development").lower()
IS_PRODUCTION = ENV in ("production", "prod", "live")

# 日志级别（供 utils.logging_manager.setup_logging，亦读取环境变量LOG_LEVEL）
LOG_LEVEL = (_env("LOG_LEVEL", "INFO") or "INFO").upper()

# ==================== JWT 认证配置 ====================

if IS_PRODUCTION:
    JWT_SECRET_KEY = _env("JWT_SECRET_KEY")
    if not JWT_SECRET_KEY:
        raise RuntimeError(
            "生产环境必须设置环境变量 JWT_SECRET_KEY。"
            '生成：python -c "import secrets; print(secrets.token_hex(32))"'
        )
else:
    _DEV_JWT = "dev-only-not-for-production"
    JWT_SECRET_KEY = _env("JWT_SECRET_KEY") or _DEV_JWT
    if JWT_SECRET_KEY == _DEV_JWT:
        _settings_log.warning(
            "当前使用开发用默认 JWT_SECRET_KEY，切勿用于生产；"
            "请在 .env 中设置 JWT_SECRET_KEY"
        )

JWT_ALGORITHM = _env("JWT_ALGORITHM", "HS256") or "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(_env("ACCESS_TOKEN_EXPIRE_MINUTES", "1440") or "1440")

# 身份认证（tokenUrl 对应 /auth/login，供文档与 Swagger 使用）
AUTH_SCHEMA = OAuth2PasswordBearer(tokenUrl="/auth/login")

# ==================== 初始管理员（仅首次启动写入库）====================

AUTH_INIT_USERNAME = _env("AUTH_INIT_USERNAME", "admin") or "admin"

if IS_PRODUCTION:
    AUTH_INIT_PASSWORD = _env("AUTH_INIT_PASSWORD")
    if not AUTH_INIT_PASSWORD:
        raise RuntimeError(
            "生产环境必须设置 AUTH_INIT_PASSWORD（初始管理员密码，首次启动写入数据库）"
        )
    if len(AUTH_INIT_PASSWORD) < 10:
        raise RuntimeError(
            "生产环境请使用更长的 AUTH_INIT_PASSWORD（建议至少 10 位）"
        )
else:
    AUTH_INIT_PASSWORD = _env("AUTH_INIT_PASSWORD", "11111") or "11111"

# ==================== 数据库 ====================

_DEV_DB_URL = "mysql://root:123456@127.0.0.1:3306/fldcf"

if IS_PRODUCTION:
    DB_URL = _env("DB_URL")
    if not DB_URL:
        raise RuntimeError("生产环境必须设置 DB_URL（数据库连接 URL）")
else:
    DB_URL = _env("DB_URL", _DEV_DB_URL)

# Tortoise-ORM
TORTOISE_ORM = {
    "connections": {"default": DB_URL},
    "apps": {
        "models": {
            "models": ["src.auth.models", "src.detection_history.models"],
            "default_connection": "default",
        },
    },
    "timezone": "Asia/Shanghai",
}
