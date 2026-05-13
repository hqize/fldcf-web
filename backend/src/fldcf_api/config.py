"""
FLDCF 路径与 preset、环境变量解析；与具体 PyTorch 加载解耦，供 router / services / inference 共用
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

# backend/src/fldcf_api/config.py → 上溯三级为 backend/（权重 fldcf_data 与可选 FLDCF_raw 放于此树下）
BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
FLDCF_DATA_DIR = BACKEND_ROOT / "fldcf_data"

_PRESET_L_ALIASES = frozenset(
    ("fakel", "fake-l", "loveda", "fake_love", "lovel", "l")
)


def _parse_preset_token(raw: str) -> str:
    """归一化为 fakeV | fakeL | studentV | studentL"""
    r = raw.strip().lower().replace("-", "").replace("_", "")
    if r in ("studentv", "minev", "myv", "trainv", "selfv"):
        return "studentV"
    if r in ("studentl", "minel", "myl", "trainl", "selfl"):
        return "studentL"
    if r in _PRESET_L_ALIASES or r == "fakel":
        return "fakeL"
    if r in ("fakev", "vaihingen", "v"):
        return "fakeV"
    return "fakeV"


def _is_love_branch(preset: str) -> bool:
    return preset in ("fakeL", "studentL")


def normalize_preset() -> str:
    """FLDCF_PRESET：fakeV（默认）、fakeL、studentV、studentL。"""
    return _parse_preset_token(os.environ.get("FLDCF_PRESET", "fakeV"))


def resolve_preset(override: str | None) -> str:
    """请求参数 preset 优先；空则沿用 FLDCF_PRESET 环境变量。"""
    if override is None:
        return normalize_preset()
    s = str(override).strip()
    if not s:
        return normalize_preset()
    return _parse_preset_token(s)


@dataclass
class InferConfig:
    """code_root: FLDCF(raw) 根目录；weights_dir: backend/fldcf_data；preset: fakeV|fakeL|studentV|studentL。"""

    code_root: Path
    weights_dir: Path
    checkpoint_path: Path
    preset: str = "fakeV"
    rgb_range: int = 1
    cpu: bool = False


def default_weights_dir() -> Path:
    return Path(os.environ.get("FLDCF_WEIGHTS_DIR", FLDCF_DATA_DIR)).expanduser()


def default_checkpoint(weights_dir: Path, preset: str) -> Path:
    """解析顺序：preset 专用 env → FLDCF_CHECKPOINT → fldcf_data 下默认文件名。"""
    env_keys = {
        "fakeV": ("FLDCF_CHECKPOINT_FAKEV",),
        "fakeL": ("FLDCF_CHECKPOINT_FAKEL", "FLDCF_CHECKPOINT_LOVE"),
        "studentV": ("FLDCF_CHECKPOINT_STUDENT_V", "FLDCF_CHECKPOINT_STUDENT_FAKEV"),
        "studentL": ("FLDCF_CHECKPOINT_STUDENT_L", "FLDCF_CHECKPOINT_STUDENT_FAKEL"),
    }
    for key in env_keys.get(preset, env_keys["fakeV"]):
        raw = os.environ.get(key)
        if raw:
            return Path(raw).expanduser()

    env_ckpt = os.environ.get("FLDCF_CHECKPOINT")
    if env_ckpt:
        return Path(env_ckpt).expanduser()
    fname = {
        "fakeV": "model_fakeV.pt",
        "fakeL": "model_fakeL.pt",
        "studentV": "model_studentV.pt",
        "studentL": "model_studentL.pt",
    }.get(preset, "model_fakeV.pt")
    return weights_dir / fname


def default_code_root() -> Path:
    """FLDCF仓库根目录（需含子目录 src/）

    优先读环境变量 FLDCF_ROOT。若未设置，勿使用空 Path：在 Windows 下会解析为 cwd，误找 backend/src。
    未设置时探测：仓库根目录 FLDCF_raw（与 backend、gp-front 同级，内仅须含官方 src/）、
    backend/FLDCF_raw、backend/FLDCF(raw)。
    """
    raw = os.environ.get("FLDCF_ROOT", "").strip()
    if raw:
        return Path(raw).expanduser().resolve()

    repo_root = BACKEND_ROOT.parent
    candidates = (
        repo_root / "FLDCF_raw",
        BACKEND_ROOT / "FLDCF_raw",
        BACKEND_ROOT / "FLDCF(raw)",
    )
    for c in candidates:
        if (c / "src").is_dir():
            return c.resolve()

    return (repo_root / "FLDCF_raw").resolve()
