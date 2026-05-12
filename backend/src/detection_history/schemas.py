"""检测历史 API 模型"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class DetectionCreateItem(BaseModel):
    mode: Literal["single", "batch"]
    preset: str = Field(..., max_length=32)
    source_filename: str = Field(..., max_length=512)
    ok: bool = True
    error_message: str | None = Field(None, max_length=1024)

    image_class_index: int | None = None
    fake_probability: float | None = None
    authentic_probability: float | None = None
    mask_tamper_ratio: float | None = None
    localization_override: bool = False
    input_height: int | None = None
    input_width: int | None = None
    mask_height: int | None = None
    mask_width: int | None = None


class DetectionBatchCreate(BaseModel):
    items: list[DetectionCreateItem] = Field(..., max_length=200)


class DetectionRecordOut(BaseModel):
    id: int
    created_at: datetime
    mode: str
    preset: str
    source_filename: str
    ok: bool
    error_message: str | None = None
    image_class_index: int | None = None
    fake_probability: float | None = None
    authentic_probability: float | None = None
    mask_tamper_ratio: float | None = None
    localization_override: bool = False
    input_height: int | None = None
    input_width: int | None = None
    mask_height: int | None = None
    mask_width: int | None = None

    class Config:
        from_attributes = True


class DetectionListOut(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[DetectionRecordOut]
