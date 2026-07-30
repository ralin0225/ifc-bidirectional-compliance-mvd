from __future__ import annotations

import re
from collections import Counter
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .engine import STATUSES, ComplianceEngine

Intent = Literal["find_results", "explain_element", "summarize_results"]
Locale = Literal["zh-CN", "en"]
Projection = Literal["element", "rule", "status", "evidence"]

GUID_PATTERN = re.compile(r"(?<![0-9A-Za-z_$])([0-9A-Za-z_$]{22})(?![0-9A-Za-z_$])")


class QueryFilters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rule_ids: list[str] = Field(default_factory=list, max_length=20)
    element_guids: list[str] = Field(default_factory=list, max_length=100)
    statuses: list[str] = Field(default_factory=list, max_length=10)
    ifc_classes: list[str] = Field(default_factory=list, max_length=20)
    storeys: list[str] = Field(default_factory=list, max_length=20)


class QueryDSL(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intent: Intent = "find_results"
    filters: QueryFilters = Field(default_factory=QueryFilters)
    projection: list[Projection] = Field(
        default_factory=lambda: ["element", "rule", "status", "evidence"],
        min_length=1,
    )
    limit: int = Field(default=100, ge=1, le=200)


class QueryContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rule_id: str | None = Field(default=None, max_length=120)
    element_guid: str | None = Field(default=None, max_length=64)


class NaturalLanguageQueryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    utterance: str = Field(min_length=1, max_length=500)
    locale: Locale | None = None
    context: QueryContext = Field(default_factory=QueryContext)


class ParsedQuery(BaseModel):
    original_utterance: str
    locale: Locale
    dsl: QueryDSL
    warnings: list[str]
    executable: bool


class QueryResultRow(BaseModel):
    rule_id: str
    rule_title: str
    clause: str
    element_guid: str
    element_name: str
    ifc_class: str
    status: str
    measured_value: float | None
    required_value: float
    unit: str
    reason: str
    evidence_source: str | None
    evidence_details: dict


class QueryExecutionResponse(BaseModel):
    query_id: str | None = None
    parsed: ParsedQuery
    total: int
    returned: int
    truncated: bool
    status_counts: dict[str, int]
    rows: list[QueryResultRow]
    explanation: str


def _locale_for(request: NaturalLanguageQueryRequest) -> Locale:
    if request.locale:
        return request.locale
    return "zh-CN" if re.search(r"[\u3400-\u9fff]", request.utterance) else "en"


def _contains(text: str, *phrases: str) -> bool:
    return any(phrase in text for phrase in phrases)


def _has_word(text: str, *words: str) -> bool:
    return any(re.search(rf"\b{re.escape(word)}\b", text) for word in words)


def parse_natural_language(
    request: NaturalLanguageQueryRequest,
    engine: ComplianceEngine,
) -> ParsedQuery:
    original = request.utterance.strip()
    text = original.casefold()
    locale = _locale_for(request)
    warnings: list[str] = []
    filters = QueryFilters()

    guid_matches = GUID_PATTERN.findall(original)
    uses_element_context = _contains(
        text,
        "这个构件",
        "该构件",
        "当前构件",
        "this element",
        "selected element",
    )
    if request.context.element_guid and uses_element_context:
        guid_matches.append(request.context.element_guid)
    filters.element_guids = list(dict.fromkeys(guid_matches))

    if _contains(text, "净宽", "clear width", "opening width"):
        filters.rule_ids.append("IBC2021-1010.1.1-WIDTH")
    if _contains(text, "门净高", "门的净高", "door clear height", "door height"):
        filters.rule_ids.append("IBC2021-1010.1.1-HEIGHT")
    if _contains(
        text,
        "空间净高",
        "疏散净高",
        "顶棚高度",
        "ceiling height",
        "egress height",
        "space clear height",
    ):
        filters.rule_ids.append("IBC2021-1003.2-EGRESS-HEIGHT")
    negative_pass = _contains(
        text,
        "未通过",
        "没有通过",
        "不合规",
    ) or _has_word(text, "fail", "failed")
    if _contains(text, "不可检查", "无法检查", "not checkable", "missing information"):
        filters.statuses.append("NOT_CHECKABLE")
    if _contains(text, "不适用", "not applicable"):
        filters.statuses.append("NOT_APPLICABLE")
    if _contains(text, "人工复核", "人工审查", "manual review"):
        filters.statuses.append("MANUAL_REVIEW_REQUIRED")
    if negative_pass:
        filters.statuses.append("FAIL")
    elif _contains(text, "通过") or _has_word(text, "pass", "passed"):
        filters.statuses.append("PASS")

    if _contains(text, "门") or _has_word(text, "door", "doors"):
        filters.ifc_classes.append("IfcDoor")
    if _contains(text, "空间") or _has_word(text, "space", "spaces"):
        filters.ifc_classes.append("IfcSpace")

    intent: Intent = "find_results"
    if _contains(text, "为什么", "原因", "why", "explain"):
        intent = "explain_element"
        if not filters.statuses:
            filters.statuses.append("FAIL")
    elif _contains(text, "汇总", "统计", "多少", "summary", "summarize", "count"):
        intent = "summarize_results"
    if intent == "explain_element" and request.context.rule_id and not filters.rule_ids:
        filters.rule_ids.append(request.context.rule_id)

    filters.rule_ids = list(dict.fromkeys(filters.rule_ids))
    filters.statuses = list(dict.fromkeys(filters.statuses))
    filters.ifc_classes = list(dict.fromkeys(filters.ifc_classes))

    unknown_rules = [rule_id for rule_id in filters.rule_ids if rule_id not in engine.rules]
    if unknown_rules:
        warnings.append("UNKNOWN_RULE_CONTEXT")
    unknown_elements = [
        guid for guid in filters.element_guids if guid not in engine.elements
    ]
    if unknown_elements:
        warnings.append("UNKNOWN_ELEMENT_CONTEXT")
    if intent == "explain_element" and not filters.element_guids:
        warnings.append("ELEMENT_CONTEXT_REQUIRED")
    if not any(
        (
            filters.rule_ids,
            filters.element_guids,
            filters.statuses,
            filters.ifc_classes,
            filters.storeys,
        )
    ):
        warnings.append("NO_STRUCTURED_FILTERS")

    executable = not any(
        warning
        in {
            "UNKNOWN_RULE_CONTEXT",
            "UNKNOWN_ELEMENT_CONTEXT",
            "ELEMENT_CONTEXT_REQUIRED",
            "NO_STRUCTURED_FILTERS",
        }
        for warning in warnings
    )
    return ParsedQuery(
        original_utterance=original,
        locale=locale,
        dsl=QueryDSL(intent=intent, filters=filters),
        warnings=warnings,
        executable=executable,
    )


def execute_query(parsed: ParsedQuery, engine: ComplianceEngine) -> QueryExecutionResponse:
    if not parsed.executable:
        return QueryExecutionResponse(
            parsed=parsed,
            total=0,
            returned=0,
            truncated=False,
            status_counts={},
            rows=[],
            explanation=_explanation(parsed, 0, False),
        )

    filters = parsed.dsl.filters
    matched = []
    for result in engine.ensure_results():
        if filters.rule_ids and result["rule_id"] not in filters.rule_ids:
            continue
        if filters.element_guids and result["element_guid"] not in filters.element_guids:
            continue
        if filters.statuses and result["status"] not in filters.statuses:
            continue
        if filters.ifc_classes and result["ifc_class"] not in filters.ifc_classes:
            continue
        matched.append(result)

    total = len(matched)
    limited = matched[: parsed.dsl.limit]
    rows = [
        QueryResultRow(
            rule_id=result["rule_id"],
            rule_title=engine.rules[result["rule_id"]]["title"],
            clause=result["clause"],
            element_guid=result["element_guid"],
            element_name=result["element_name"],
            ifc_class=result["ifc_class"],
            status=result["status"],
            measured_value=result["measured_value"],
            required_value=float(result["required_value"]),
            unit=result["unit"],
            reason=result["reason"],
            evidence_source=result["evidence_source"],
            evidence_details=result["evidence_details"],
        )
        for result in limited
    ]
    return QueryExecutionResponse(
        parsed=parsed,
        total=total,
        returned=len(rows),
        truncated=total > len(rows),
        status_counts=dict(sorted(Counter(row.status for row in rows).items())),
        rows=rows,
        explanation=_explanation(parsed, total, total > len(rows)),
    )


def _explanation(parsed: ParsedQuery, total: int, truncated: bool) -> str:
    if not parsed.executable:
        return (
            "查询没有执行：请补充明确的规则、构件、状态或类别。"
            if parsed.locale == "zh-CN"
            else "The query was not executed. Add a specific rule, element, status, or class."
        )
    suffix = "；结果已截断。" if truncated else "。"
    if parsed.locale == "zh-CN":
        return f"确定性查询命中 {total} 条结果{suffix}"
    suffix_en = " Results were truncated." if truncated else "."
    return f"The deterministic query matched {total} results{suffix_en}"


def validate_dsl(dsl: QueryDSL, engine: ComplianceEngine) -> ParsedQuery:
    warnings = []
    if any(rule_id not in engine.rules for rule_id in dsl.filters.rule_ids):
        warnings.append("UNKNOWN_RULE_CONTEXT")
    if any(guid not in engine.elements for guid in dsl.filters.element_guids):
        warnings.append("UNKNOWN_ELEMENT_CONTEXT")
    if any(status not in STATUSES for status in dsl.filters.statuses):
        warnings.append("UNKNOWN_STATUS")
    return ParsedQuery(
        original_utterance="[structured query]",
        locale="en",
        dsl=dsl,
        warnings=warnings,
        executable=not warnings,
    )
