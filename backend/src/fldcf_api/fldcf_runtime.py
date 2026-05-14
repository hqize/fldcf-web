"""
FLDCF 与 FastAPI 同进程加载时的「运行环境」

"""

from __future__ import annotations

import os
import shutil
import sys
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import torch

PRIOR_LOAD_LOCK = threading.Lock()


def prepare_love_prior_vi(weights_dir: Path) -> tuple[Path, bytes | None, bool]:
    """
    LoveDA：将``model_lo.pt``拷到``model_vi.pt``以满足官方加载路径。

    返回``(vi_path, saved_original_vi_bytes_or_none, temp_vi_from_lo_only)``，
    供``finally``调用``restore_prior_vi``
    """
    model_dir = weights_dir / "model"
    vi_path = model_dir / "model_vi.pt"
    lo_path = model_dir / "model_lo.pt"
    if not lo_path.is_file():
        raise FileNotFoundError(
            f"LoveDA 需要先验 {lo_path}，请将 model_lo.pt 放到 {model_dir}/"
        )
    saved: bytes | None = None
    if vi_path.is_file():
        saved = vi_path.read_bytes()
    shutil.copy2(lo_path, vi_path)
    temp_only = saved is None
    return vi_path, saved, temp_only


def restore_prior_vi(vi_path: Path, saved: bytes | None, temp_only: bool) -> None:
    if saved is not None:
        vi_path.write_bytes(saved)
    elif temp_only and vi_path.is_file():
        try:
            vi_path.unlink()
        except OSError:
            pass


def ensure_vaihingen_prior_vi(weights_dir: Path) -> None:
    vi_path = weights_dir / "model" / "model_vi.pt"
    if not vi_path.is_file():
        raise FileNotFoundError(
            f"缺少先验权重{vi_path}，请将model_vi.pt放到{weights_dir}/model/"
        )


@contextmanager
def fldcf_isolated_import_session(
    weights_dir: Path,
    fldcf_src: Path,
    *,
    runs_cpu: bool,
) -> Iterator[None]:
    """
    进入：暂存``utils``、``chdir(weights_dir)``、把``fldcf_src``插入``sys.path``首位；
    退出：还原 `torch.load``、``cwd``、先验文件以外的 **utils / path**状态
    调用方须在``with``块内完成``from model import Model``等import
    """
    cwd_back = os.getcwd()
    _torch_load = torch.load
    src_str = str(fldcf_src.resolve())

    def _torch_load_map_cpu(f: Any, *args: Any, **kwargs: Any) -> Any:
        kwargs.setdefault("map_location", torch.device("cpu"))
        return _torch_load(f, *args, **kwargs)

    stashed_utils: dict[str, Any] = {}
    for name in list(sys.modules):
        if name == "utils" or name.startswith("utils."):
            stashed_utils[name] = sys.modules.pop(name)

    path_inserted = False
    try:
        os.chdir(str(weights_dir.resolve()))
        if src_str not in sys.path:
            sys.path.insert(0, src_str)
            path_inserted = True
        if runs_cpu:
            torch.load = _torch_load_map_cpu  # type: ignore[method-assign]
        yield
    finally:
        torch.load = _torch_load  # type: ignore[method-assign]
        os.chdir(cwd_back)
        if path_inserted:
            try:
                sys.path.remove(src_str)
            except ValueError:
                pass
        for name in list(sys.modules):
            if name == "utils" or name.startswith("utils."):
                sys.modules.pop(name, None)
        for key, mod in stashed_utils.items():
            sys.modules[key] = mod


def build_fldcf_model_inside_session(
    ckpt_path: Path,
    *,
    data_train: str,
    data_train_dir: str,
    runs_cpu: bool,
) -> Any:
    """须在``fldcf_isolated_import_session``内调用；返回fldcf的``Model``实例"""
    from types import SimpleNamespace

    from model import Model  # noqa: WPS433
    from utility import checkpoint  # noqa: WPS433

    ckp_args = SimpleNamespace(
        save="api_infer",
        load="",
        reset=False,
        model="fldcf",
        pre_train=str(ckpt_path),
        resume=0,
        cpu=runs_cpu,
        precision="single",
        self_ensemble=False,
        chop=False,
        n_GPUs=1,
        save_models=True,
        data_train=data_train,
        data_train_dir=data_train_dir,
        scale=4,
        save_results=False,
    )
    ckp = checkpoint(ckp_args)
    model = Model(ckp_args, ckp)
    model.eval()
    if not runs_cpu:
        model = model.cuda()
    return model
