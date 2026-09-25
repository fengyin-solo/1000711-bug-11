"""道路设施接口：维护道路设施，覆盖登记、修改、办理移交、标记观测、封闭设施等动作。"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.schemas import ActionResult, EntryPayload, PageResult
from app.services.road import RoadService

router = APIRouter(prefix="/api/road", tags=["道路设施"])

service = RoadService()

LIST_FIELDS = ["设施编码", "道路名称", "道路等级", "起止桩号", "路面结构", "管养单位", "建成年份", "设施状态"]
STATUSES = ["待移交", "正常养护", "重点观测", "封闭施工"]


@router.get("", response_model=PageResult[dict])
def list_entries(
    设施编码: str | None = Query(default=None, description="按设施编码检索"),
    道路名称: str | None = Query(default=None, description="按道路名称检索"),
    道路等级: str | None = Query(default=None, description="按道路等级检索；传“空”筛未填等级的记录"),
    路面结构: str | None = Query(default=None, description="按路面结构检索；传“空”筛缺路面结构的记录"),
    status: str | None = Query(default=None, description="待移交、正常养护、重点观测、封闭施工"),
    # 英文别名保留给脚本/导出等既有调用方式
    keyword: str | None = Query(default=None, description="设施编码的英文别名"),
    name: str | None = Query(default=None, description="道路名称的英文别名"),
    grade: str | None = Query(default=None, description="道路等级的英文别名"),
    pavement: str | None = Query(default=None, description="路面结构的英文别名"),
    page: int = 1,
    size: int = 20,
) -> PageResult[dict]:
    """按设施编码、道路名称、道路等级、路面结构与状态过滤道路设施。

    合计与列表来自同一次筛选；没有数据时返回空页，不报错。
    前端既有筛选框直接用中文字段名透传，英文参数名作为别名照旧可用。
    """
    if size > 200:
        raise HTTPException(status_code=400, detail="每页最多 200 条，请缩小分页范围")
    items, total, stats = service.list_entries(
        keyword=设施编码 or keyword,
        name=道路名称 or name,
        grade=道路等级 or grade,
        pavement=路面结构 or pavement,
        status=status,
        page=page,
        size=size,
    )
    return PageResult(items=items, total=total, page=page, size=size, stats=stats)


# 静态路径要排在 /{entry_id} 前面，否则 /export 会被当成编号
@router.get("/export")
def export_entries() -> dict[str, Any]:
    """导出道路设施清单：返回全量数据，口径与列表、合计一致。"""
    items, total, stats = service.list_entries(page=1, size=10000)
    return {"module": "road", "total": total, "stats": stats, "items": items}


@router.get("/stats", response_model=dict)
def get_stats() -> dict[str, Any]:
    """合计卡片：与列表同源，单独取时按全量道路设施统计。"""
    items, _total, stats = service.list_entries(page=1, size=10000)
    return stats


@router.get("/{entry_id}", response_model=dict)
def get_entry(entry_id: int) -> dict:
    """读取单条道路设施明细；不存在时给出可读的错误说明。"""
    entry = service.get_entry(entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"道路设施 {entry_id} 不存在或已归档")
    return entry


@router.post("", response_model=ActionResult)
def create_entry(payload: EntryPayload) -> ActionResult:
    """登记一条道路设施，缺必填字段时说明原因而不是静默丢弃。"""
    entry, missing = service.create_entry(payload.values)
    if missing:
        return ActionResult(ok=False, message=f"缺少必填字段：{'、'.join(missing)}")
    return ActionResult(ok=True, message="道路设施已登记", entry=entry)


@router.put("/{entry_id}", response_model=ActionResult)
def update_entry(entry_id: int, payload: EntryPayload) -> ActionResult:
    """修改道路设施字段（如管养单位）；保存后列表、详情、合计看到的都是同一份新值。"""
    if service.get_entry(entry_id) is None:
        raise HTTPException(status_code=404, detail=f"道路设施 {entry_id} 不存在或已归档")
    entry, missing = service.update_entry(entry_id, payload.values)
    if missing:
        return ActionResult(ok=False, message=f"缺少必填字段：{'、'.join(missing)}")
    return ActionResult(ok=True, message="道路设施信息已更新", entry=entry)


@router.post("/{entry_id}/actions", response_model=ActionResult)
def run_action(entry_id: int, payload: EntryPayload) -> ActionResult:
    """对单条道路设施执行办理移交、标记观测、封闭设施；不允许的动作会被拦下并说明原因。"""
    action = str(payload.values.get("action") or "").strip()
    entry, message = service.run_action(entry_id, action)
    if entry is None:
        return ActionResult(ok=False, message=message)
    return ActionResult(ok=True, message=message, entry=entry)
