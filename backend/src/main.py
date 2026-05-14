"""FastAPI 应用入口（业务包位于同级的 `auth`、`fldcf_api` 等模块下）。"""
import os
from contextlib import asynccontextmanager
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from tortoise import Tortoise

from src.utils.logging_manager import get_uvicorn_log_config, setup_logging

# -----------------------------------------------------------------------------
# 进程初始化（须在import src.core.settings之前）
#   1. 加载backend/.env（及可选 src/aichat_api/.env），写入os.environ
#   2. 先用环境变量里的 LOG_LEVEL 配日志，保证随后加载 settings时JWT等日志格式一致
#   3. 再import settings，并用settings.LOG_LEVEL同步一次（与 .env 规范化结果一致）
# -----------------------------------------------------------------------------

_BACKEND_ROOT = Path(__file__).resolve().parent.parent

if load_dotenv:
    load_dotenv(_BACKEND_ROOT / ".env")
    _aichat_env = _BACKEND_ROOT / "src" / "aichat_api" / ".env"
    if _aichat_env.is_file():
        load_dotenv(_aichat_env, override=False)

setup_logging(level=os.getenv("LOG_LEVEL", "INFO"))

from src.core.settings import LOG_LEVEL, TORTOISE_ORM

setup_logging(level=LOG_LEVEL)

from src.auth import router as auth_router, init_admin_user
from src.aichat_api import router as aichat_router
from src.detection_history import router as detection_router
from src.fldcf_api import router as fldcf_router
from src.utils.exceptions import register_exception_handlers


# ==================== 生命周期 ====================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动：数据库 / 建表 / 初始管理员；关闭：断开 Tortoise"""
    await Tortoise.init(config=TORTOISE_ORM)
    await Tortoise.generate_schemas(safe=True)
    await init_admin_user()
    yield
    await Tortoise.close_connections()


# ==================== 应用实例 ====================
app = FastAPI(
    title="遥感图像伪造定位可视化",
    description="主服务：用户认证 + FLDCF 推理（/fldcf）+ AI 助手（/aichat）",
    lifespan=lifespan,
)
register_exception_handlers(app)


# ==================== CORS ====================
# Docker/Nginx同域前端：设置CORS_ALLOW_ORIGINS="http://localhost,http://127.0.0.1" 等
_cors_env = os.getenv(
    "CORS_ALLOW_ORIGINS",
    "http://localhost:8000,http://localhost:5173,http://localhost,http://127.0.0.1",
)
_cors_origins = [x.strip() for x in _cors_env.split(",") if x.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== 路由注册 ====================
for router, prefix, tag in (
    (auth_router, "/auth", "登录认证模块"),
    (fldcf_router, "/fldcf", "FLDCF 伪造定位"),
    (aichat_router, "/aichat", "AI 助手"),
    (detection_router, "/detections", "检测历史"),
):
    app.include_router(router, prefix=prefix, tags=[tag])


# ==================== 静态文件 ====================
_static = _BACKEND_ROOT / "static"
if _static.is_dir():
    app.mount("/static", StaticFiles(directory=str(_static)), name="static")


# ==================== 根路由 ====================
@app.get("/", tags=["根路由"], summary="测试页面", description="简单的 html 测试页")
async def toweb():
    return RedirectResponse("/static/index.html")


# ==================== 脚本入口 ====================
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_config=get_uvicorn_log_config(LOG_LEVEL),
    )
