"""道路设施接口：维护道路设施，覆盖办理移交、标记观测、封闭设施等动作。"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import Field

from app.schemas import ActionResult, EntryPayload, PageResult
from app.services.road import RoadService

router = APIRouter(prefix="/api/road", tags=["道路设施"])

service = RoadService()

LIST_FIELDS = ["设施编码", "道路名称", "道路等级", "起止桩号", "路面结构", "管养单位", "建成年份", "设施状态"]
STATUSES = ["待移交", "正常养护", "重点观测", "封闭施工"]


class RoadPageResult(PageResult[dict]):
    """道路设施列表页：合计与列表来自同一次过滤，保证面板数字和条数一致。"""

    stats: dict[str, int] = Field(default_factory=dict)


@router.get("", response_model=RoadPageResult)
def list_entries(
    keyword: str | None = Query(default=None, description="按设施编码检索"),
    status: str | None = Query(default=None, description="待移交、正常养护、重点观测、封闭施工"),
    code: str | None = Query(default=None, alias="设施编码", description="按设施编码模糊过滤"),
    name: str | None = Query(default=None, alias="道路名称", description="按道路名称模糊过滤"),
    grade: str | None = Query(default=None, alias="道路等级", description="按道路等级模糊过滤"),
    page: int = 1,
    size: int = 20,
) -> RoadPageResult:
    """按设施编码、道路名称、道路等级与状态过滤道路设施列表；没有数据时返回空页，不报错。"""
    if size > 200:
        raise HTTPException(status_code=400, detail="每页最多 200 条，请缩小分页范围")
    filters = {"设施编码": code, "道路名称": name, "道路等级": grade}
    items, total, stats = service.list_entries(
        keyword=keyword, status=status, filters=filters, page=page, size=size
    )
    return RoadPageResult(items=items, total=total, page=page, size=size, stats=stats)


@router.get("/export")
def export_entries() -> dict[str, Any]:
    """导出道路设施清单：返回当前过滤条件下的全量数据。"""
    items, total, _ = service.list_entries(page=1, size=10000)
    return {"module": "road", "total": total, "items": items}


@router.get("/{entry_id}", response_model=dict)
def get_entry(entry_id: int) -> dict:
    """读取单条道路设施明细；与列表取同一份数据，不存在时给出可读的错误说明。"""
    entry = service.get_entry(entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"道路设施 {entry_id} 不存在或已归档")
    return entry


@router.post("", response_model=ActionResult)
def create_entry(payload: EntryPayload) -> ActionResult:
    """登记一条道路设施，缺字段时说明原因而不是静默丢弃。"""
    entry, missing = service.create_entry(payload.values)
    if missing:
        return ActionResult(ok=False, message=f"缺少必填字段：{'、'.join(missing)}")
    return ActionResult(ok=True, message="道路设施已登记", entry=entry)


@router.put("/{entry_id}", response_model=ActionResult)
def update_entry(entry_id: int, payload: EntryPayload) -> ActionResult:
    """修改道路设施的可维护字段（如管养单位）；写回同一份数据，列表与合计随即同步。"""
    entry, message = service.update_entry(entry_id, payload.values)
    if entry is None:
        return ActionResult(ok=False, message=message)
    return ActionResult(ok=True, message=message, entry=entry)


@router.post("/{entry_id}/actions", response_model=ActionResult)
def run_action(entry_id: int, payload: EntryPayload) -> ActionResult:
    """对单条道路设施执行办理移交、标记观测、封闭设施；不允许的动作会被拦下并说明原因。"""
    action = str(payload.values.get("action") or "").strip()
    entry, message = service.run_action(entry_id, action)
    if entry is None:
        return ActionResult(ok=False, message=message)
    return ActionResult(ok=True, message=message, entry=entry)
