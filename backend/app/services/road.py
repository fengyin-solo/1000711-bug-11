"""道路设施业务规则：状态流转、字段校验与筛选口径都收在这里。

列表、详情、合计都只从 store 里的同一份数据出发：内部只保留一个权威状态字段
``status``，展示用的「设施状态」由它派生；可选字段缺失时记为 ``None``，
筛选时既不会把这些记录静默丢掉，也能用「空」把它们单独筛出来。
"""
from __future__ import annotations

import re
from typing import Any

from app.store import store

MODULE = "road"
REQUIRED_FIELDS = ["设施编码", "道路名称", "道路等级"]
# 登记时可一并填写的非必填字段
OPTIONAL_FIELDS = ["起止桩号", "路面结构", "管养单位", "建成年份"]
# 列表与详情共用的展示列，顺序即表格列顺序
PRESENT_FIELDS = REQUIRED_FIELDS + OPTIONAL_FIELDS + ["设施状态"]
STATUS_ORDER = ["待移交", "正常养护", "重点观测", "封闭施工"]
ACTION_RULES = {"办理移交": "正常养护", "标记观测": "重点观测", "封闭设施": "封闭施工"}
NEGATIVE_ACTIONS = []
# 可选字段筛「空」时的约定值：筛字段缺失或空白的记录
EMPTY_MARKER = "空"

_STAKE_RE = re.compile(r"K?\s*(\d+(?:\.\d+)?)\s*[-—~～]\s*K?\s*(\d+(?:\.\d+)?)", re.IGNORECASE)


def _text(value: Any) -> str:
    """把任意字段值转成可展示、可匹配的文本；缺失值统一为空串。"""
    if value is None:
        return ""
    return str(value).strip()


def _is_blank(value: Any) -> bool:
    return _text(value) == ""


def _matches(row: dict[str, Any], field: str, keyword: str) -> bool:
    """单字段包含匹配；「空」专门匹配字段缺失/空白的记录，缺字段记录不会报错。"""
    if keyword == EMPTY_MARKER:
        return _is_blank(row.get(field))
    return keyword in _text(row.get(field))


def _stake_length(value: Any) -> float:
    """从起止桩号（如 K3.0-K5.2）解析里程公里数；解析不了按 0 计。"""
    match = _STAKE_RE.search(_text(value))
    if match is None:
        return 0.0
    start, end = float(match.group(1)), float(match.group(2))
    return round(max(end - start, 0.0), 3)


class RoadService:
    def list_entries(
        self,
        *,
        keyword: str | None = None,
        name: str | None = None,
        grade: str | None = None,
        pavement: str | None = None,
        status: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[dict[str, Any]], int, dict[str, Any]]:
        """按条件筛选道路设施，返回当前页、总数与合计卡片。

        合计与列表基于同一份筛选结果计算，保证过滤后条数变了合计也跟着变；
        字段缺失的记录始终保留在数据集中，只有显式条件才会筛掉它们。
        """
        rows = store.rows(MODULE)
        conditions = [
            ("设施编码", keyword),
            ("道路名称", name),
            ("道路等级", grade),
            ("路面结构", pavement),
        ]
        for field, value in conditions:
            value = _text(value)
            if value:
                rows = [row for row in rows if _matches(row, field, value)]
        status = _text(status)
        if status:
            rows = [row for row in rows if row.get("status") == status]

        total = len(rows)
        stats = self._build_stats(rows)
        start = max(page - 1, 0) * size
        items = [self.present(row) for row in rows[start:start + size]]
        return items, total, stats

    def _build_stats(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        """合计卡片与列表同源：在养/重点观测按权威状态计，里程由起止桩号汇总。"""
        in_care = sum(1 for row in rows if row.get("status") == "正常养护")
        watched = sum(1 for row in rows if row.get("status") == "重点观测")
        mileage = round(sum(_stake_length(row.get("起止桩号")) for row in rows), 1)
        return {"在养道路": in_care, "重点观测道路": watched, "管养里程": mileage}

    def present(self, row: dict[str, Any]) -> dict[str, Any]:
        """把内部记录转成列表/详情一致的展示结构：设施状态始终派生自 status。"""
        item = {field: row.get(field) for field in REQUIRED_FIELDS + OPTIONAL_FIELDS}
        item["设施状态"] = row.get("status")
        item["id"] = row.get("id")
        return item

    def get_entry(self, entry_id: int) -> dict[str, Any] | None:
        row = store.find(MODULE, entry_id)
        return self.present(row) if row is not None else None

    def create_entry(self, values: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
        missing = [field for field in REQUIRED_FIELDS if not _text(values.get(field))]
        if missing:
            return None, missing
        rows = store.rows(MODULE)
        entry: dict[str, Any] = {"id": max((int(row.get("id", 0)) for row in rows), default=0) + 1}
        for field in REQUIRED_FIELDS + OPTIONAL_FIELDS:
            entry[field] = _text(values.get(field)) or None
        entry["status"] = STATUS_ORDER[0]
        entry["pending"] = True
        entry["abnormal"] = False
        rows.append(entry)
        return self.present(entry), []

    def update_entry(
        self, entry_id: int, values: dict[str, Any]
    ) -> tuple[dict[str, Any] | None, list[str]]:
        """修改道路设施业务字段（局部更新，只改提交的字段）。

        必填字段改空会被拦下并说明缺哪些；可选字段（含路面结构、管养单位）
        允许清空，清成 ``None`` 后列表与详情立刻一致，不用刷新。
        """
        entry = store.find(MODULE, entry_id)
        if entry is None:
            return None, []
        # 先把提交值合并到原记录上，再校验必填项：只改单个可选字段时
        # 不会因为没带必填字段而被误判为缺失。
        merged = {field: entry.get(field) for field in REQUIRED_FIELDS}
        merged.update({field: values.get(field) for field in values if field in REQUIRED_FIELDS})
        missing = [field for field in REQUIRED_FIELDS if not _text(merged.get(field))]
        if missing:
            return None, missing
        for field in REQUIRED_FIELDS + OPTIONAL_FIELDS:
            if field in values:
                entry[field] = _text(values.get(field)) or None
        return self.present(entry), []

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
        return self.present(entry), f"道路设施已{action}"
