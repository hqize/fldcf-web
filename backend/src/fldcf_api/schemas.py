"""Pydantic：最小预测响应形状（与前端约定字段）"""

from typing import Optional

from pydantic import BaseModel, Field


class FldcfPredictResponse(BaseModel):
    """单次推理返回"""

    ok: bool = Field(True, description="推理是否完成（无异常即为True）")
    inference_device: str = Field(
        ...,
        description="本次推理实际使用的设备，如 cpu、cuda:0",
    )
    image_class_index: int = Field(
        ...,
        description="最终整图类别：0=伪造，1=真实；若分割定位到篡改像素占比超阈值则固定为0（覆盖全局softmax）",
    )
    fake_probability: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="伪造类置信度：默认来自整图softmax；若启用定位覆盖且原分类偏真，会与authentic对调以与最终标签一致",
    )
    authentic_probability: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="真实类置信度；可能与原始softmax对调（见 localization_override）",
    )
    mask_tamper_ratio: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="分割图中被判为篡改类（通道0）的像素占比",
    )
    localization_override: bool = Field(
        ...,
        description="True 表示定位_mask 满足阈值且原整图分类为真实，已按定位改为伪造",
    )
    mask_png_base64: str = Field(
        ...,
        description="定位 PNG（灰度）base64：黑≈真实区域，亮白≈篡改区域",
    )
    mask_height: int = Field(..., description="mask 高度（像素）")
    mask_width: int = Field(..., description="mask 宽度（像素）")
    input_height: int = Field(..., description="输入张量对应的空间高度")
    input_width: int = Field(..., description="输入张量对应的空间宽度")
    input_original_height: Optional[int] = Field(
        None, description="上传原图高度；若做过边长限制缩放则与 input_height 不同"
    )
    input_original_width: Optional[int] = Field(
        None, description="上传原图宽度；若做过边长限制缩放则与 input_width 不同"
    )
    input_was_downscaled: bool = Field(
        False, description="True表示因超过FLDCF_MAX_INPUT_SIDE已按比例缩小后再推理"
    )
    detail: Optional[str] = Field(
        None, description="可选说明（如降采样、设备CPU/GPU）"
    )


class FldcfStatusResponse(BaseModel):
    """GET /status：当前部署与模型是否就绪。"""

    inference_ready: bool = Field(
        ..., description="FLDCF是否已成功加载到内存（避免字段名model_*触发Pydantic保留命名空间告警）"
    )
    cuda_available: bool = Field(
        ...,
        description="当前进程内PyTorch是否检测到可用CUDA（与驱动/安装有关）",
    )
    use_cpu_request: Optional[bool] = Field(
        None,
        description="查询参数use_cpu：true=强制 CPU，false=优先GPU；未传则为null（沿用FLDCF_CPU）",
    )
    runs_on_cpu: bool = Field(
        ...,
        description="本次预热实例实际是否在CPU上推理（无GPU时即使用户选GPU也可能为True）",
    )
    device: str = Field(..., description="推理设备，如cpu/cuda:0")
    fldcf_code_root: str = Field("", description="FLDCF 源码目录（含 src/）")
    weights_dir: str = Field("", description="backend/fldcf_data，存放 .pt 权重")
    preset: str = Field(
        "fakeV",
        description="当前解析的preset；可用查询参数preset覆盖，未传则用FLDCF_PRESET",
    )
    checkpoint: str = Field(
        "",
        description="当前preset对应的整网.pt绝对路径",
    )
