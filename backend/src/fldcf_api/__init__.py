"""
FLDCF 模块（与 auth 包同级结构）：

- router   HTTP 路由
- services 预测器缓存与推理调度
- config     preset / 路径 / InferConfig
- inference  PyTorch 模型加载与逐图预测
- schemas  Pydantic 响应
"""

from .router import router

__all__ = ["router"]
