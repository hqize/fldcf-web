"""检测历史路由"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from src.auth.models import User
from src.auth.services import get_current_user
from src.utils.exceptions import BizError
from src.utils.response import Result

from .models import DetectionRecord
from .schemas import DetectionBatchCreate, DetectionCreateItem, DetectionListOut, DetectionRecordOut

router = APIRouter()


def _to_out(rec: DetectionRecord) -> DetectionRecordOut:
    return DetectionRecordOut.model_validate(rec)


@router.post(
    "",
    response_model=Result[DetectionRecordOut],
    summary="新增一条检测记录",
)
async def create_one(
    body: DetectionCreateItem,
    current_user: User = Depends(get_current_user),
):
    rec = await DetectionRecord.create(
        user=current_user,
        **body.model_dump(),
    )
    return Result.success(_to_out(rec))


@router.post(
    "/batch",
    response_model=Result[dict],
    summary="批量写入检测记录",
)
async def create_batch(
    body: DetectionBatchCreate,
    current_user: User = Depends(get_current_user),
):
    for item in body.items:
        await DetectionRecord.create(user=current_user, **item.model_dump())
    return Result.success({"created": len(body.items)})


@router.get(
    "",
    response_model=Result[DetectionListOut],
    summary="分页查询当前用户的检测历史",
)
async def list_records(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
):
    q = DetectionRecord.filter(user=current_user).order_by("-created_at")
    total = await q.count()
    offset = (page - 1) * page_size
    rows = await q.offset(offset).limit(page_size).all()
    items = [_to_out(r) for r in rows]
    return Result.success(
        DetectionListOut(
            total=total,
            page=page,
            page_size=page_size,
            items=items,
        )
    )


@router.delete(
    "/{record_id}",
    response_model=Result[None],
    summary="删除一条检测记录",
)
async def delete_record(
    record_id: int,
    current_user: User = Depends(get_current_user),
):
    deleted = await DetectionRecord.filter(id=record_id, user=current_user).delete()
    if not deleted:
        raise BizError("记录不存在", code="404", status_code=404)
    return Result.success(msg="已删除")
