"""道路设施业务规则：状态流转、字段校验与筛选口径都收在这里。

列表、详情、合计都读写 store 里的同一份记录：筛选与统计在一次调用里完成，
设施状态由内部 status 派生，不单独存一份，避免两处数据对不上。
"""
from __future__ import annotations

from typing import Any

from app.store import store

MODULE = "road"
REQUIRED_FIELDS = ["设施编码", "道路名称", "道路等级"]
FILTER_FIELDS = ["设施编码", "道路名称", "道路等级"]
EDITABLE_FIELDS = ["道路名称", "道路等级", "起止桩号", "路面结构", "管养单位", "建成年份"]
STATUS_ORDER = ["待移交", "正常养护", "重点观测", "封闭施工"]
ACTION_RULES = {"办理移交": "正常养护", "标记观测": "重点观测", "封闭设施": "封闭施工"}
NEGATIVE_ACTIONS: list[str] = []


class RoadService:
    def list_entries(
        self,
        *,
        keyword: str | None = None,
        status: str | None = None,
        filters: dict[str, Any] | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[dict[str, Any]], int, dict[str, int]]:
        rows = store.rows(MODULE)
        if keyword:
            rows = [row for row in rows if keyword in str(row.get("设施编码") or "")]
        if status:
            rows = [row for row in rows if row.get("status") == status]
        for field, value in (filters or {}).items():
            if field not in FILTER_FIELDS:
                continue
            needle = str(value or "").strip()
            if not needle:
                # 空条件不参与过滤：缺字段的记录在清空条件后必须还在列表里
                continue
            rows = [row for row in rows if needle in str(row.get(field) or "")]
        total = len(rows)
        stats = self.summarize(rows)
        start = max(page - 1, 0) * size
        items = [self._serialize(row) for row in rows[start:start + size]]
        return items, total, stats

    def summarize(self, rows: list[dict[str, Any]]) -> dict[str, int]:
        """合计口径与列表完全一致：统计的就是过滤后的这一批记录。"""
        return {
            "设施总数": len(rows),
            "在养道路": sum(1 for row in rows if row.get("status") == "正常养护"),
            "重点观测道路": sum(1 for row in rows if row.get("status") == "重点观测"),
        }

    def get_entry(self, entry_id: int) -> dict[str, Any] | None:
        entry = store.find(MODULE, entry_id)
        if entry is None:
            return None
        return self._serialize(entry)

    def create_entry(self, values: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
        missing = [field for field in REQUIRED_FIELDS if not str(values.get(field) or "").strip()]
        if missing:
            return None, missing
        rows = store.rows(MODULE)
        entry = {"id": max((int(row.get("id", 0)) for row in rows), default=0) + 1}
        entry.update({field: values.get(field) for field in REQUIRED_FIELDS})
        entry["status"] = STATUS_ORDER[0]
        entry["pending"] = True
        entry["abnormal"] = False
        rows.append(entry)
        return self._serialize(entry), []

    def update_entry(self, entry_id: int, values: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
        entry = store.find(MODULE, entry_id)
        if entry is None:
            return None, f"道路设施 {entry_id} 不存在或已归档"
        changed = [field for field in EDITABLE_FIELDS if field in values]
        if not changed:
            return None, f"没有可更新的字段，仅支持修改：{'、'.join(EDITABLE_FIELDS)}"
        for field in changed:
            text = str(values.get(field) or "").strip()
            if text:
                entry[field] = text
            else:
                # 清空即视为缺字段，记录本身保留，筛选时按空值处理
                entry.pop(field, None)
        return self._serialize(entry), "道路设施已更新"

    def run_action(self, entry_id: int, action: str) -> tuple[dict[str, Any] | None, str]:
        entry = store.find(MODULE, entry_id)
        if entry is None:
            return None, f"道路设施 {entry_id} 不存在或已归档"
        if action not in ACTION_RULES:
            return None, f"动作「{action}」不属于道路设施可执行范围"
        target = ACTION_RULES[action]
        if target not in STATUS_ORDER:
            return None, f"目标状态「{target}」不在允许的状态序列里"
        entry["status"] = target
        entry["pending"] = target != STATUS_ORDER[-1]
        entry["abnormal"] = action in NEGATIVE_ACTIONS
        return self._serialize(entry), f"道路设施已{action}"

    def _serialize(self, row: dict[str, Any]) -> dict[str, Any]:
        """对外结构：设施状态直接由 status 派生，保证列表、详情、合计看到的是同一个值。"""
        data = dict(row)
        data["设施状态"] = row.get("status", STATUS_ORDER[0])
        return data
