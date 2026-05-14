"""
FLDCF HTTP 推理：``FldcfPredictor``
"""

from __future__ import annotations

import base64
import io
import os

import cv2
import imageio.v2 as imageio
import numpy as np
import torch
import torch.nn.functional as F

from src.utils.exceptions import BizError

from .config import InferConfig, _is_love_branch
from .fldcf_runtime import (
    PRIOR_LOAD_LOCK,
    build_fldcf_model_inside_session,
    ensure_vaihingen_prior_vi,
    fldcf_isolated_import_session,
    prepare_love_prior_vi,
    restore_prior_vi,
)


def _apply_max_input_side(img: np.ndarray) -> tuple[np.ndarray, int, int, bool]:
    """超限缩小最长边；``FLDCF_MAX_INPUT_SIDE``≤0 表示不缩放。"""
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


def _bytes_to_rgb_ndarray(file_bytes: bytes) -> np.ndarray:
    """上传字节 → HWC RGB uint8。"""
    img = imageio.imread(io.BytesIO(file_bytes))
    if img.ndim == 2:
        img = np.stack([img, img, img], axis=-1)
    if img.shape[2] == 4:
        img = img[:, :, :3]
    return img


def _postprocess_fl_outputs(
    seg_logits: torch.Tensor,
    cls_logits: torch.Tensor,
    *,
    preset: str,
    orig_hw: tuple[int, int],
    model_hw: tuple[int, int],
    was_downscaled: bool,
    device: torch.device,
) -> dict[str, object]:
    """
    输出张量 → API 字段
    ``seg_logits``: [1, C, H, W]；``cls_logits``: [1, 2] 图级 logits。
    """
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

    oh, ow = orig_hw
    mh, mw = model_hw
    down_note = ""
    if was_downscaled:
        down_note = f"input_downscaled {ow}x{oh}->{mw}x{mh};"

    return {
        "inference_device": str(device),
        "image_class_index": cls_idx,
        "fake_probability": fake_prob,
        "authentic_probability": authentic_prob,
        "mask_tamper_ratio": tamper_ratio,
        "localization_override": localization_override,
        "mask_png_base64": b64,
        "mask_height": int(vis_u8.shape[0]),
        "mask_width": int(vis_u8.shape[1]),
        "input_height": mh,
        "input_width": mw,
        "input_original_height": oh if was_downscaled else None,
        "input_original_width": ow if was_downscaled else None,
        "input_was_downscaled": was_downscaled,
        "detail": (
            f"{down_note}"
            f"device={device};preset={preset};"
            f"tamper_ratio={tamper_ratio:.6f};min_ratio={min_ratio};"
            f"cls_orig={cls_idx_orig};localization_override={localization_override}"
        ),
    }


class FldcfPredictor:
    """见模块文档「输入 / 输出」"""

    def __init__(self, cfg: InferConfig):
        self.cfg = cfg
        self._model = None
        self._np2Tensor = None
        self._runs_cpu = bool(cfg.cpu) or (not torch.cuda.is_available())
        self._device = torch.device("cpu" if self._runs_cpu else "cuda")

    @property
    def device(self) -> torch.device:
        return self._device

    @property
    def runs_on_cpu(self) -> bool:
        return self._runs_cpu

    def load(self) -> None:
        if self._model is not None:
            return

        with PRIOR_LOAD_LOCK:
            if self._model is not None:
                return

            code_root = self.cfg.code_root.resolve()
            if not code_root.is_dir():
                raise FileNotFoundError(f"FLDCF_ROOT(源码目录)不存在: {code_root}")

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
                    f"缺少 FLDCF 权重 {ckpt}，请将 {hint} 放到 {wdir}，或设置对应FLDCF_CHECKPOINT_*环境变量"
                )

            src = code_root / "src"
            if not src.is_dir():
                raise FileNotFoundError(f"未找到FLDCF源码目录: {src}")

            vi_path: object | None = None
            saved_vi: bytes | None = None
            temp_vi = False

            if _is_love_branch(self.cfg.preset):
                vi_path, saved_vi, temp_vi = prepare_love_prior_vi(wdir)
            else:
                ensure_vaihingen_prior_vi(wdir)

            try:
                with fldcf_isolated_import_session(wdir, src, runs_cpu=self._runs_cpu):
                    from data.common import np2Tensor

                    self._np2Tensor = np2Tensor
                    if _is_love_branch(self.cfg.preset):
                        dt, ddir = "Lovada", "fakeL"
                    else:
                        dt, ddir = "Vaihingen", "fakeV"
                    self._model = build_fldcf_model_inside_session(
                        ckpt,
                        data_train=dt,
                        data_train_dir=ddir,
                        runs_cpu=self._runs_cpu,
                    )
            finally:
                if vi_path is not None:
                    restore_prior_vi(vi_path, saved_vi, temp_vi)

    def unload(self) -> None:
        self._model = None
        self._np2Tensor = None

    def predict_image_bytes(self, file_bytes: bytes) -> dict:
        """
        **输入**：``file_bytes`` = 上传图像原始字节。

        **输出**：见模块顶「二、输出」表格（``dict`` 可直接 JSON 化字段由 router 封装）。
        """
        self.load()
        assert self._model is not None
        assert self._np2Tensor is not None

        img = _bytes_to_rgb_ndarray(file_bytes)
        img, orig_h, orig_w, was_down = _apply_max_input_side(img)

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
                "显存或内存不足，已中止本次推理,已自动缩小仍失败时可再调低环境变量 "
                "FLDCF_MAX_INPUT_SIDE（默认2048；设为0关闭缩放但不建议）",
                code="503",
                status_code=503,
            ) from e

        return _postprocess_fl_outputs(
            seg_logits,
            cls_logits,
            preset=self.cfg.preset,
            orig_hw=(orig_h, orig_w),
            model_hw=(int(img.shape[0]), int(img.shape[1])),
            was_downscaled=was_down,
            device=self._device,
        )
