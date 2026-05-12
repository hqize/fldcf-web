"""
推理引擎：FldcfPredictor（模型加载与 predict）。

路径 / preset / InferConfig 见 ``config.py``；HTTP 见 router，预测器缓存见 services。

FLDCF 权重从 backend/fldcf_data 加载；网络结构依赖 FLDCF 官方 ``src/``（环境变量 FLDCF_ROOT）。

LoveDA 线会在加载前将 ``model_lo.pt`` 复制为 ``model_vi.pt``（加载后按字节还原或删除临时文件）。
定位优先：FLDCF_MASK_OVERRIDE=1（默认）时，若分割篡改类像素占比 ≥ FLDCF_MASK_FAKE_MIN_RATIO（默认 0.0005），
则整图判伪造并覆盖 softmax；若原分类偏真则交换 fake/authentic 概率。

与本仓库 ``backend/src/utils`` 冲突：装载 FLDCF 前暂存并移除 ``sys.modules`` 中的 ``utils``，
装载结束后先清空当前 ``utils`` 树再恢复暂存（``finally`` 内不再错误地二次 ``pop``）。
"""

from __future__ import annotations

import base64
import io
import os
import shutil
import sys
import threading
from types import SimpleNamespace
from typing import Any

import cv2
import imageio.v2 as imageio
import numpy as np
import torch
import torch.nn.functional as F

from src.utils.exceptions import BizError

from .config import InferConfig, _is_love_branch


def _apply_max_input_side(img: np.ndarray) -> tuple[np.ndarray, int, int, bool]:
    """超限则缩小最长边，降低 OOM / 502 风险。FLDCF_MAX_INPUT_SIDE≤0 表示不缩放。"""
    oh, ow = int(img.shape[0]), int(img.shape[1])
    max_side = int(os.environ.get("FLDCF_MAX_INPUT_SIDE", "2048"))
    if max_side <= 0:
        return img, oh, ow, False
    m = max(oh, ow)
    if m <= max_side:
        return img, oh, ow, False
    scale = max_side / m
    nw = max(1, int(round(ow * scale)))
    nh = max(1, int(round(oh * scale)))
    resized = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_AREA)
    return resized, oh, ow, True


def _pop_utils_namespace() -> dict[str, Any]:
    """从 sys.modules 移除顶层 ``utils`` 及其子模块（本仓库 utils → 让给 FLDCF src/utils）。"""
    stashed: dict[str, Any] = {}
    for name in list(sys.modules):
        if name == "utils" or name.startswith("utils."):
            stashed[name] = sys.modules.pop(name)
    return stashed


def _drop_utils_modules_from_sys_modules() -> None:
    """清空 sys.modules 中的 utils 树，便于再 ``恢复`` 本仓库的 utils（丢弃 FLDCF 装入的引用）。"""
    for name in list(sys.modules):
        if name == "utils" or name.startswith("utils."):
            sys.modules.pop(name, None)


def _restore_modules(mods: dict[str, Any]) -> None:
    for key, mod in mods.items():
        sys.modules[key] = mod


# fakeL 会临时改写 model_vi.pt，多线程并行 load 需串行化
_prior_load_lock = threading.Lock()


class FldcfPredictor:
    """构造 FLDCF 时 cwd 为 weights_dir；官方代码固定加载 ./model/model_vi.pt。"""

    def __init__(self, cfg: InferConfig):
        self.cfg = cfg
        self._model = None
        self._runs_cpu = bool(cfg.cpu) or (not torch.cuda.is_available())
        self._device = torch.device("cpu" if self._runs_cpu else "cuda")

    @property
    def device(self) -> torch.device:
        return self._device

    @property
    def runs_on_cpu(self) -> bool:
        """实际是否在 CPU 上执行（无 CUDA 时即使用户期望 GPU 也可能为 True）。"""
        return self._runs_cpu

    def load(self) -> None:
        if self._model is not None:
            return

        with _prior_load_lock:
            if self._model is not None:
                return

            code_root = self.cfg.code_root.resolve()
            if not code_root.is_dir():
                raise FileNotFoundError(f"FLDCF_ROOT（源码目录）不存在: {code_root}")

            wdir = self.cfg.weights_dir.resolve()
            ckpt = self.cfg.checkpoint_path.resolve()
            if not ckpt.is_file():
                hint = {
                    "fakeV": "model_fakeV.pt",
                    "fakeL": "model_fakeL.pt",
                    "studentV": "model_studentV.pt",
                    "studentL": "model_studentL.pt",
                }.get(self.cfg.preset, "model_fakeV.pt")
                raise FileNotFoundError(
                    f"缺少 FLDCF 权重 {ckpt}，请将 {hint} 放到 {wdir}，或设置对应 FLDCF_CHECKPOINT_* 环境变量"
                )

            model_dir = wdir / "model"
            vi_path = model_dir / "model_vi.pt"
            lo_path = model_dir / "model_lo.pt"

            saved_vi_bytes: bytes | None = None
            temp_vi_from_lo_only = False

            if _is_love_branch(self.cfg.preset):
                if not lo_path.is_file():
                    raise FileNotFoundError(
                        f"{self.cfg.preset} 需要 LoveDA 先验 {lo_path}，请将 model_lo.pt 放到 backend/fldcf_data/model/"
                    )
                if vi_path.is_file():
                    saved_vi_bytes = vi_path.read_bytes()
                shutil.copy2(lo_path, vi_path)
                temp_vi_from_lo_only = saved_vi_bytes is None
            else:
                if not vi_path.is_file():
                    raise FileNotFoundError(
                        f"缺少先验权重 {vi_path}，请将 model_vi.pt 放到 backend/fldcf_data/model/"
                    )

            src = code_root / "src"
            if not src.is_dir():
                raise FileNotFoundError(f"未找到 FLDCF 源码目录: {src}")

            cwd_back = os.getcwd()
            _torch_load = torch.load

            def _torch_load_map_cpu(f, *args, **kwargs):
                kwargs.setdefault("map_location", torch.device("cpu"))
                return _torch_load(f, *args, **kwargs)

            stashed_utils = _pop_utils_namespace()
            try:
                os.chdir(str(wdir))
                if str(src) not in sys.path:
                    sys.path.insert(0, str(src))

                if self._runs_cpu:
                    torch.load = _torch_load_map_cpu  # type: ignore[method-assign]

                from data.common import np2Tensor  # noqa: WPS433
                from model import Model  # noqa: WPS433
                from utility import checkpoint  # noqa: WPS433

                self._np2Tensor = np2Tensor

                if _is_love_branch(self.cfg.preset):
                    data_train, data_train_dir = "Lovada", "fakeL"
                else:
                    data_train, data_train_dir = "Vaihingen", "fakeV"

                ckp_args = SimpleNamespace(
                    save="api_infer",
                    load="",
                    reset=False,
                    model="fldcf",
                    pre_train=str(ckpt),
                    resume=0,
                    cpu=self._runs_cpu,
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
                self._model = Model(ckp_args, ckp)
                self._model.eval()
                if not self._runs_cpu:
                    self._model = self._model.cuda()
            finally:
                torch.load = _torch_load  # type: ignore[method-assign]
                os.chdir(cwd_back)
                if saved_vi_bytes is not None:
                    vi_path.write_bytes(saved_vi_bytes)
                elif temp_vi_from_lo_only and vi_path.is_file():
                    try:
                        vi_path.unlink()
                    except OSError:
                        pass
                _drop_utils_modules_from_sys_modules()
                _restore_modules(stashed_utils)

    def unload(self) -> None:
        self._model = None

    def predict_image_bytes(self, file_bytes: bytes) -> dict:
        self.load()
        assert self._model is not None

        img = imageio.imread(io.BytesIO(file_bytes))
        if img.ndim == 2:
            img = np.stack([img, img, img], axis=-1)
        if img.shape[2] == 4:
            img = img[:, :, :3]

        img, orig_h, orig_w, was_down = _apply_max_input_side(img)
        down_note = ""
        if was_down:
            down_note = f"input_downscaled {orig_w}x{orig_h}->{img.shape[1]}x{img.shape[0]};"

        lr_tensor = self._np2Tensor(img, rgb_range=self.cfg.rgb_range)[0]
        lr = lr_tensor.unsqueeze(0)
        if not self._runs_cpu:
            lr = lr.cuda()

        try:
            with torch.no_grad():
                seg_logits, cls_logits = self._model(lr)
        except (RuntimeError, MemoryError) as e:
            err = str(e).lower()
            oom = isinstance(e, MemoryError) or "out of memory" in err
            if not oom:
                raise
            if not self._runs_cpu:
                try:
                    torch.cuda.empty_cache()
                except Exception:
                    pass
            raise BizError(
                "显存或内存不足，已中止本次推理。已自动缩小仍失败时可再调低环境变量 "
                "FLDCF_MAX_INPUT_SIDE（默认 2048；设为 0 关闭缩放但不建议）。",
                code="503",
                status_code=503,
            ) from e

        sm = F.softmax(cls_logits, dim=1)
        fake_prob = float(sm[0, 0].item())
        authentic_prob = float(sm[0, 1].item())
        cls_idx_orig = int(torch.argmax(cls_logits, dim=1)[0].item())

        pred = seg_logits[0].detach().cpu().numpy()
        mask_cls = np.argmax(pred, axis=0).astype(np.uint8)
        tamper_class = 0
        tamper_ratio = float((mask_cls == tamper_class).mean())
        min_ratio = float(os.environ.get("FLDCF_MASK_FAKE_MIN_RATIO", "0.0005"))
        override_on = os.environ.get("FLDCF_MASK_OVERRIDE", "1").strip().lower() not in (
            "0",
            "false",
            "no",
            "off",
        )
        mask_says_fake = override_on and tamper_ratio >= min_ratio
        localization_override = mask_says_fake and cls_idx_orig == 1

        if mask_says_fake:
            cls_idx = 0
            if fake_prob < authentic_prob:
                fake_prob, authentic_prob = authentic_prob, fake_prob
        else:
            cls_idx = cls_idx_orig

        vis = (1 - mask_cls).astype(np.float32)
        vis_u8 = np.round(vis * 255).clip(0, 255).astype(np.uint8)

        buf = io.BytesIO()
        imageio.imwrite(buf, vis_u8, format="png")
        b64 = base64.standard_b64encode(buf.getvalue()).decode("ascii")

        h, w = vis_u8.shape
        return {
            "inference_device": str(self._device),
            "image_class_index": cls_idx,
            "fake_probability": fake_prob,
            "authentic_probability": authentic_prob,
            "mask_tamper_ratio": tamper_ratio,
            "localization_override": localization_override,
            "mask_png_base64": b64,
            "mask_height": h,
            "mask_width": w,
            "input_height": int(img.shape[0]),
            "input_width": int(img.shape[1]),
            "input_original_height": orig_h if was_down else None,
            "input_original_width": orig_w if was_down else None,
            "input_was_downscaled": was_down,
            "detail": (
                f"{down_note}"
                f"device={self._device};preset={self.cfg.preset};"
                f"tamper_ratio={tamper_ratio:.6f};min_ratio={min_ratio};"
                f"cls_orig={cls_idx_orig};localization_override={localization_override}"
            ),
        }
