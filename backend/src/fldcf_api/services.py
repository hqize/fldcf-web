"""
FLDCF 业务层：预测器缓存、路径解析、与PyTorch推理调度
"""

from __future__ import annotations

import os
from pathlib import Path

from .config import (
    InferConfig,
    default_checkpoint,
    default_code_root,
    default_weights_dir,
    resolve_preset,
)
from .inference import FldcfPredictor

MAX_UPLOAD_BYTES = int(os.environ.get("FLDCF_MAX_UPLOAD_BYTES", str(20 * 1024 * 1024)))

_weights_dir: Path = default_weights_dir()
_code_root: Path = default_code_root()
_predictors: dict[str, FldcfPredictor] = {}


def torch_cuda_available() -> bool:
    try:
        import torch

        return bool(torch.cuda.is_available())
    except Exception:
        return False


def env_wants_cpu() -> bool:
    return os.environ.get("FLDCF_CPU", "").lower() in ("1", "true", "yes")


def resolve_use_cpu_flag(use_cpu: bool | None) -> bool:
    """use_cpu=None 时沿用 FLDCF_CPU 环境变量"""
    if use_cpu is not None:
        return use_cpu
    return env_wants_cpu()


def parse_use_cpu_form_value(raw: str | None) -> bool | None:
    """multipart表单中的 use_cpu：空串或未传表示沿用默认"""
    if raw is None:
        return None
    s = str(raw).strip().lower()
    if not s:
        return None
    if s in ("1", "true", "yes", "on", "cpu"):
        return True
    if s in ("0", "false", "no", "off", "gpu"):
        return False
    raise ValueError(f"无效的 use_cpu: {raw!r}")


def get_weights_dir() -> Path:
    return _weights_dir


def get_code_root() -> Path:
    return _code_root


def _predictor_signature(preset: str, use_cpu_resolved: bool) -> str:
    ckpt = default_checkpoint(_weights_dir, preset)
    return f"{preset}|{ckpt.resolve()}|{use_cpu_resolved}|{_code_root.resolve()}|{_weights_dir.resolve()}"


def get_predictor(preset: str | None = None, use_cpu: bool | None = None) -> FldcfPredictor:
    """按preset、权重路径与CPU/GPU偏好签名缓存实例"""
    preset_resolved = resolve_preset(preset)
    use_cpu_resolved = resolve_use_cpu_flag(use_cpu)
    sig = _predictor_signature(preset_resolved, use_cpu_resolved)
    cached = _predictors.get(sig)
    if cached is not None:
        return cached
    if not (_code_root.is_dir() and (_code_root / "src").is_dir()):
        raise RuntimeError(
            "未找到 FLDCF 源码：请在 backend/.env 设置 FLDCF_ROOT 指向 FLDCF(raw) 根目录（须含 src/），"
            "或将官方仓库放到 <仓库根>/FLDCF_raw、backend/FLDCF_raw 或 backend/FLDCF(raw)"
        )
    ckpt = default_checkpoint(_weights_dir, preset_resolved)
    if not ckpt.is_file():
        raise RuntimeError(
            f"未找到权重: {ckpt}。请将 model_fakeV.pt / model_fakeL.pt 放到 {_weights_dir}，"
            "或设置 FLDCF_CHECKPOINT"
        )
    p = FldcfPredictor(
        InferConfig(
            code_root=_code_root,
            weights_dir=_weights_dir,
            checkpoint_path=ckpt,
            preset=preset_resolved,
            rgb_range=1,
            cpu=use_cpu_resolved,
        )
    )
    _predictors[sig] = p
    return p
