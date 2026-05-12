"""
FLDCF 路由层：HTTP 入口
"""

from __future__ import annotations

import traceback

from fastapi import APIRouter, File, Form, Query, UploadFile

from src.utils.exceptions import BizError
from src.utils.logging_manager import get_logger
from src.utils.response import Result

from .exceptions import reraise_predict_as_biz
from .config import default_checkpoint, resolve_preset
from .schemas import FldcfPredictResponse, FldcfStatusResponse
from .services import (
    MAX_UPLOAD_BYTES,
    get_code_root,
    get_predictor,
    get_weights_dir,
    parse_use_cpu_form_value,
    torch_cuda_available,
)

logger = get_logger(__name__)

router = APIRouter()


@router.get(
    "/status",
    response_model=Result[FldcfStatusResponse],
    summary="推理服务状态",
    description="查看 FLDCF 是否已加载、运行设备、当前权重路径；可选 preset 会触发对应预测器加载（预热）",
)
def get_status(
        preset: str | None = Query(
            None,
            description="fakeV|fakeL|studentV|studentL；用于查看该线下的 checkpoint 并预热",
        ),
        use_cpu: bool | None = Query(
            None,
            description="true=强制 CPU；false=优先 GPU；省略则沿用服务端 FLDCF_CPU",
        ),
):
    _code_root = get_code_root()
    _weights_dir = get_weights_dir()
    code_ok = _code_root.is_dir() and (_code_root / "src").is_dir()
    loaded = False
    dev = "n/a"
    runs_cpu_val = False
    cuda_ok = torch_cuda_available()
    preset_resolved = resolve_preset(preset)
    ckpt_path = default_checkpoint(_weights_dir, preset_resolved)
    # 预热失败不抛 BizError：仍 200，由 inference_ready=false 表示（便于前端轮询状态）
    try:
        p = get_predictor(preset, use_cpu)
        p.load()
        loaded = p._model is not None
        dev = str(p.device)
        runs_cpu_val = p.runs_on_cpu
    except Exception:
        loaded = False
        logger.warning("FLDCF 预热失败:\n%s", traceback.format_exc())
    return Result.success(
        FldcfStatusResponse(
            inference_ready=loaded,
            cuda_available=cuda_ok,
            use_cpu_request=use_cpu,
            runs_on_cpu=runs_cpu_val,
            device=dev,
            fldcf_code_root=str(_code_root) if code_ok else "",
            weights_dir=str(_weights_dir),
            preset=preset_resolved,
            checkpoint=str(ckpt_path),
        )
    )


@router.post(
    "/predict",
    response_model=Result[FldcfPredictResponse],
    summary="单图伪造定位推理",
    description="上传 RGB 图像，返回整图真伪置信度与篡改区域 mask（PNG base64）",
)
async def predict(
        file: UploadFile = File(..., description="RGB 图像，png/jpg 等"),
        preset: str | None = Form(
            None,
            description="fakeV|fakeL（原）或 studentV|studentL（自训练）；省略则用 FLDCF_PRESET",
        ),
        use_cpu: str | None = Form(
            None,
            description="1/true=CPU；0/false=优先 GPU；省略则沿用 FLDCF_CPU",
        ),
):
    ct = (file.content_type or "").strip().lower()
    if ct and not ct.startswith("image/"):
        raise BizError(
            "请上传 image/* 文件（当前 Content-Type: %s）" % (file.content_type or "空"),
            code="400",
            status_code=400,
        )
    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise BizError(f"文件超过 {MAX_UPLOAD_BYTES} 字节", code="413", status_code=413)

    if len(data) == 0:
        raise BizError(
            "未收到文件内容，请检查上传表单（浏览器勿手动覆盖 multipart boundary）",
            code="400",
            status_code=400,
        )

    try:
        use_cpu_flag = parse_use_cpu_form_value(use_cpu)
    except ValueError as e:
        raise BizError(str(e), code="400", status_code=400) from e

    try:
        pred = get_predictor(preset, use_cpu_flag)
        out = pred.predict_image_bytes(data)
    except Exception as e:
        reraise_predict_as_biz(e)

    return Result.success(
        FldcfPredictResponse(
            ok=True,
            inference_device=out["inference_device"],
            image_class_index=out["image_class_index"],
            fake_probability=out["fake_probability"],
            authentic_probability=out["authentic_probability"],
            mask_tamper_ratio=out["mask_tamper_ratio"],
            localization_override=out["localization_override"],
            mask_png_base64=out["mask_png_base64"],
            mask_height=out["mask_height"],
            mask_width=out["mask_width"],
            input_height=out["input_height"],
            input_width=out["input_width"],
            input_original_height=out.get("input_original_height"),
            input_original_width=out.get("input_original_width"),
            input_was_downscaled=bool(out.get("input_was_downscaled", False)),
            detail=out.get("detail"),
        )
    )
