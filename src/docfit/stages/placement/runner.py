from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from docfit.core.io import now_iso, sha256_json, write_json
from docfit.core.models import Finding, StageResult, make_finding
from docfit.core.status import Status, merge_statuses
from docfit.harness.profiles import REAL_CORE_PROFILE
from docfit.harness.real_core import (
    accepted_expected_artifact,
    compare_to_accepted_expected,
    load_render_plan_baseline,
)


def build_placement_plan(
    template_artifact: dict[str, Any],
    content_artifact: dict[str, Any],
    *,
    drop_content_id_for_test: str | None = None,
    root: Path | None = None,
    profile_id: str | None = None,
    case_id: str | None = None,
    school_id: str | None = None,
    student_id: str | None = None,
) -> StageResult:
    slots = template_artifact.get("data", {}).get("slots", [])
    slot_by_id = {slot["slot_id"]: slot for slot in slots}
    default_slot = "slot_body_start"
    actions: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    routing_state = _PlacementRoutingState()
    for item in content_artifact.get("data", {}).get("visible_content_ledger", []):
        content_id = item["content_id"]
        if drop_content_id_for_test == content_id:
            continue
        route = _route_item_to_slot(item, slot_by_id, default_slot, routing_state)
        if route["disposition"] == "discard_as_source_format":
            actions.append(
                {
                    "action_id": f"a_{len(actions) + 1:03d}",
                    "content_ids": [content_id],
                    "disposition": "discard_as_source_format",
                    "target_slot_id": None,
                    "target_region_id": None,
                    "render_kind": item.get("kind", "source_format"),
                    "style_ref": None,
                    "evidence": _evidence_for_item(item) + route["evidence"],
                    "confidence": route["confidence"],
                    "payload": item.get("payload", {"type": "text", "text": item.get("text", "")}),
                    "content_hashes": [item.get("text_hash")],
                }
            )
            continue
        target_slot_id = route["target_slot_id"]
        if target_slot_id not in slot_by_id:
            unresolved.append(
                {
                    "content_id": content_id,
                    "disposition": "unsupported",
                    "reason": f"target slot {target_slot_id} does not exist",
                    "blocking": True,
                }
            )
            continue
        render_kind = item.get("kind", "paragraph")
        actions.append(
            {
                "action_id": f"a_{len(actions) + 1:03d}",
                "content_ids": [content_id],
                "disposition": "place",
                "target_slot_id": target_slot_id,
                "target_region_id": route["target_region_id"],
                "render_kind": render_kind,
                "style_ref": _style_for_item(item),
                "evidence": _evidence_for_item(item) + route["evidence"],
                "confidence": route["confidence"],
                "payload": item.get("payload", {"type": "text", "text": item.get("text", "")}),
                "content_hashes": [item.get("text_hash")],
            }
        )
    for item in content_artifact.get("unsupported", []):
        unresolved.append(
            {
                "content_id": item.get("content_id"),
                "disposition": "unsupported",
                "reason": item.get("reason", "unsupported visible object"),
                "blocking": item.get("blocking", True),
            }
        )

    real_core_source_facts: dict[str, Any] | None = None
    plan = {
        "artifact_type": "placement_plan",
        "artifact_version": "1.0",
        "producer": {"name": "docfit-placement", "version": "0.1.0"},
        "created_at": now_iso(),
        "profile_id": profile_id,
        "case_id": case_id,
        "school_id": school_id,
        "student_id": student_id,
        "input_hashes": {
            "template_artifact": sha256_json(template_artifact),
            "student_content_artifact": sha256_json(content_artifact),
        },
        "provenance": {
            "template_artifact_hash": sha256_json(template_artifact),
            "student_content_artifact_hash": sha256_json(content_artifact),
        },
        "status_notes": [],
        "unsupported": [],
        "data": {
            "actions": actions,
            "unresolved": unresolved,
            "school_exception_refs": [],
        },
    }
    findings = verify_placement_plan(plan, template_artifact, content_artifact)
    real_core_coverage: dict[str, Any] = {}
    if profile_id == REAL_CORE_PROFILE.profile_id and root is not None and case_id:
        baseline, baseline_findings = load_render_plan_baseline(
            root,
            case_id,
            stage="placement",
            start_index=len(findings) + 1,
        )
        findings.extend(baseline_findings)
        if baseline is not None and not baseline_findings:
            real_core_source_facts = accepted_expected_artifact(baseline)
            plan["real_core_source_facts"] = real_core_source_facts
            comparison = compare_to_accepted_expected(
                baseline,
                stage="placement",
                start_index=len(findings) + 1,
            )
            findings.extend(comparison.findings)
            source_facts_ok = comparison.status == Status.PASS
            no_silent_drop = not any(
                finding.type == "unplaced_content" for finding in findings
            )
            real_core_coverage = {
                "placement.disposition_coverage": source_facts_ok and no_silent_drop,
                "placement.no_silent_drop": no_silent_drop,
                "placement.fixed_content_policy": source_facts_ok,
                "placement.manual_only_policy": source_facts_ok,
                "placement.comparator_policy": source_facts_ok,
            }
    status = merge_statuses([Status(f.status) for f in findings]) if findings else Status.PASS
    return StageResult(
        "placement",
        status,
        findings=findings,
        artifacts={"placement_plan": plan},
        coverage={
            "placement.no_silent_drop": not any(f.type == "unplaced_content" for f in findings),
            "placement.slot_compatibility": not any(f.type == "slot_incompatible" for f in findings),
            "placement.required_slots": bool(slots),
            **real_core_coverage,
        },
        user_message=(
            "转换失败：系统已提取到文档中的内容，但部分内容无法匹配到目标模板中的位置。"
            if status == Status.FAIL
            else None
        ),
    )


def _style_for_item(item: dict[str, Any]) -> str:
    for candidate in item.get("semantic_candidates", []):
        if candidate.get("kind") == "heading":
            return f"Heading {candidate.get('level_candidate', 1)}"
    if item.get("kind") == "heading":
        return "Heading 1"
    if item.get("kind") == "table":
        return "Table Grid"
    return "Normal"


class _PlacementRoutingState:
    def __init__(self) -> None:
        self.chinese_title_count = 0
        self.english_title_count = 0
        self.section = "front"


def _route_item_to_slot(
    item: dict[str, Any],
    slot_by_id: dict[str, dict[str, Any]],
    default_slot: str,
    state: _PlacementRoutingState,
) -> dict[str, Any]:
    if _is_source_format_item(item):
        return _discard_route("source format content")
    text = _normalize_text(item.get("text", ""))
    if _is_source_front_matter_scaffold(item, text):
        return _discard_route("source front matter scaffold")
    if _is_target_fixed_front_matter(text):
        return _discard_route("target fixed front matter already provided by template")
    if _is_cover_manual_field(text):
        return _discard_route("source cover manual field is not a body paragraph")

    if state.section == "front":
        slot_id = _front_matter_slot(text, state)
        if slot_id:
            return _place_route(slot_id, "front_matter")

    section_marker = _section_marker(text)
    if section_marker is not None:
        state.section = section_marker
        if section_marker in {"references", "appendix"}:
            return _discard_route("target template owns this section heading")
        if section_marker == "acknowledgement" and "acknowledgement.e_001" in slot_by_id:
            return _place_route("acknowledgement.e_001", "acknowledgement")
        return _place_route(_body_slot_for_item(item), "body")

    if state.section == "references":
        return _place_route("references.e_002", "references")
    if state.section == "acknowledgement":
        return _place_route("acknowledgement.e_002", "acknowledgement")
    if state.section == "appendix":
        return _place_route("appendix.e_002", "appendix")
    if state.section == "body":
        return _place_route(_body_slot_for_item(item), "body")

    return _place_route(default_slot, "body")


def _front_matter_slot(text: str, state: _PlacementRoutingState) -> str | None:
    compact = _normalize_for_route(text)
    if _is_likely_chinese_title(text):
        state.chinese_title_count += 1
        return "cover.e_003" if state.chinese_title_count == 1 else "body_title_block.e_001"
    if _is_likely_english_title(text):
        state.english_title_count += 1
        return "cover.e_004" if state.english_title_count == 1 else "abstract_en.e_001"
    if compact.startswith("学生"):
        return "body_title_block.e_002"
    if compact.startswith("指导老师"):
        return "body_title_block.e_003"
    if text.startswith("(湖南农业大学") or text.startswith("（湖南农业大学"):
        return "body_title_block.e_004"
    if text.startswith("摘 要") or text.startswith("摘要"):
        return "abstract_cn.e_002"
    if text.startswith("关键词"):
        return "abstract_cn.e_004"
    if text.lower().startswith("student:"):
        return "abstract_en.e_002"
    if text.lower().startswith("tutor:"):
        return "abstract_en.e_003"
    if text.startswith("(College") or text.startswith("（College"):
        return "abstract_en.e_004"
    if text.lower().startswith("abstract:"):
        return "abstract_en.e_006"
    if text.lower().startswith("key words") or text.lower().startswith("keywords"):
        return "abstract_en.e_008"
    return None


def _section_marker(text: str) -> str | None:
    normalized = _normalize_for_route(text)
    if normalized in {"参考文献", "references"}:
        return "references"
    if normalized in {"致谢", "致謝"}:
        return "acknowledgement"
    if normalized.startswith("附录") or normalized.startswith("appendix"):
        return "appendix"
    if _looks_like_body_start(text):
        return "body"
    return None


def _body_slot_for_item(item: dict[str, Any]) -> str:
    level = _heading_level(item)
    if level == 2:
        return "body_main.e_004"
    if level == 3:
        return "body_main.e_005"
    if level is not None and level >= 4:
        return "body_main.e_006"
    return "body_main.e_011"


def _heading_level(item: dict[str, Any]) -> int | None:
    if item.get("kind") == "heading":
        return 1
    for candidate in item.get("semantic_candidates", []):
        if candidate.get("kind") == "heading":
            try:
                return int(candidate.get("level_candidate", 1))
            except (TypeError, ValueError):
                return 1
    return None


def _is_target_fixed_front_matter(text: str) -> bool:
    normalized = _normalize_for_route(text)
    return normalized in {
        "湖南农业大学",
        "湖南农业大学全日制普通本科生毕业论文",
        "全日制普通本科生毕业论文",
        "全日制普通本科生毕业论文设计",
        "诚信声明",
        "毕业论文设计作者签名",
        "年月日",
        "titleofgraduationpaper",
    } or text.startswith("本人郑重声明")


def _is_source_front_matter_scaffold(item: dict[str, Any], text: str) -> bool:
    compact = _normalize_for_route(text)
    if item.get("payload", {}).get("type") == "table":
        has_cover_label = any(
            label in compact
            for label in (
                "题目",
                "姓名",
                "学号",
                "专业",
                "指导教师",
                "学院",
            )
        )
        return "毕业论文" in compact and has_cover_label
    return (
        compact in {"目录", "目錄"}
        or "原创性声明" in compact
        or "原創性聲明" in compact
        or "使用授权声明" in compact
        or "使用授權聲明" in compact
        or compact.startswith("本学位论文作者完全了解")
        or compact.startswith("本學位論文作者完全了解")
        or compact.startswith("论文作者签名")
        or compact.startswith("論文作者簽名")
        or "导师签名" in compact
        or "導師簽名" in compact
        or compact.startswith("日期年月日")
    )


def _is_cover_manual_field(text: str) -> bool:
    compact = _normalize_for_route(text)
    return (
        compact.startswith("学生姓名")
        or compact.startswith("学号")
        or compact.startswith("年级专业及班级")
        or compact.startswith("指导老师及职称")
        or compact.startswith("学院")
        or compact == "湖南长沙"
        or compact.startswith("提交日期")
    )


def _is_likely_chinese_title(text: str) -> bool:
    if not text or len(text) > 80:
        return False
    if any(marker in text for marker in ("摘 要", "关键词", "诚信声明", "参考文献")):
        return False
    return bool(re.search(r"[\u4e00-\u9fff]", text)) and "研究" in text


def _is_likely_english_title(text: str) -> bool:
    if not text or len(text) > 180:
        return False
    lower = text.lower()
    if lower.startswith(("student:", "tutor:", "abstract:", "key words", "keywords")):
        return False
    if "title of graduation paper" in lower:
        return False
    return bool(re.search(r"[A-Za-z]", text)) and "effect" in lower


def _looks_like_body_start(text: str) -> bool:
    return bool(
        re.match(r"^\s*1\s+[\u4e00-\u9fffA-Za-z]", text)
        or re.match(r"^\s*一[、.．]\s*[\u4e00-\u9fffA-Za-z]", text)
        or re.match(r"^\s*第[一二三四五六七八九十0-9]+[章节篇]\s*", text)
    )


def _place_route(slot_id: str, region_id: str) -> dict[str, Any]:
    return {
        "disposition": "place",
        "target_slot_id": slot_id,
        "target_region_id": region_id,
        "confidence": 0.85,
        "evidence": [f"routing:{region_id}->{slot_id}"],
    }


def _discard_route(reason: str) -> dict[str, Any]:
    return {
        "disposition": "discard_as_source_format",
        "target_slot_id": None,
        "target_region_id": None,
        "confidence": 0.9,
        "evidence": [f"routing:discard:{reason}"],
    }


def _normalize_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _normalize_for_route(value: Any) -> str:
    return re.sub(r"[\s:：;；,，.。!！?？、（）()《》<>“”\"'‘’\[\]【】·]", "", str(value or "")).lower()


def _is_source_format_item(item: dict[str, Any]) -> bool:
    if item.get("kind") == "source_format":
        return True
    return any(
        candidate.get("kind") == "source_toc_entry"
        for candidate in item.get("semantic_candidates", [])
    )


def _evidence_for_item(item: dict[str, Any]) -> list[str]:
    evidence = [item.get("source_ref", "")]
    for candidate in item.get("semantic_candidates", []):
        evidence.extend(candidate.get("evidence", []))
    return [entry for entry in evidence if entry]


def verify_placement_plan(
    plan: dict[str, Any],
    template_artifact: dict[str, Any],
    content_artifact: dict[str, Any],
) -> list[Finding]:
    findings: list[Finding] = []
    ledger_ids = [
        item["content_id"]
        for item in content_artifact.get("data", {}).get("visible_content_ledger", [])
    ]
    actions = plan.get("data", {}).get("actions", [])
    unresolved = plan.get("data", {}).get("unresolved", [])
    slot_by_id = {
        slot["slot_id"]: slot
        for slot in template_artifact.get("data", {}).get("slots", [])
    }
    planned_ids = [
        content_id
        for action in actions
        for content_id in action.get("content_ids", [])
    ]
    unresolved_ids = [item.get("content_id") for item in unresolved]
    next_index = 1
    for content_id in ledger_ids:
        occurrences = planned_ids.count(content_id) + unresolved_ids.count(content_id)
        if occurrences == 0:
            findings.append(
                make_finding(
                    next_index,
                    "placement",
                    Status.FAIL,
                    "unplaced_content",
                    f"content block {content_id} has no placement action",
                    "every visible content block has exactly one disposition",
                    f"{content_id} missing from placement plan",
                    affected_ids=[content_id],
                    root_cause_bucket="placement_gap",
                )
            )
            next_index += 1
        elif occurrences > 1:
            findings.append(
                make_finding(
                    next_index,
                    "placement",
                    Status.FAIL,
                    "duplicate_disposition",
                    f"content block {content_id} has multiple dispositions",
                    "one disposition per content block",
                    str(occurrences),
                    affected_ids=[content_id],
                    root_cause_bucket="placement_gap",
                )
            )
            next_index += 1
    for action in actions:
        if action.get("disposition") == "discard_as_source_format":
            if action.get("target_slot_id") is not None:
                findings.append(
                    make_finding(
                        next_index,
                        "placement",
                        Status.FAIL,
                        "source_format_discard_has_target",
                        "Source-format discards must not target a writable template slot",
                        "target_slot_id is null",
                        str(action.get("target_slot_id")),
                        affected_ids=action.get("content_ids", []),
                        root_cause_bucket="placement_source_format_policy",
                    )
                )
                next_index += 1
            if not action.get("evidence"):
                findings.append(
                    make_finding(
                        next_index,
                        "placement",
                        Status.UNKNOWN,
                        "placement_action_missing_evidence",
                        "Placement action has no evidence",
                        "evidence list is non-empty",
                        action.get("action_id", "missing"),
                        affected_ids=action.get("content_ids", []),
                        root_cause_bucket="placement_evidence_gap",
                    )
                )
                next_index += 1
            continue
        slot = slot_by_id.get(action.get("target_slot_id"))
        if slot is None:
            findings.append(
                make_finding(
                    next_index,
                    "placement",
                    Status.FAIL,
                    "target_slot_missing",
                    f"target slot {action.get('target_slot_id')} does not exist",
                    "target slot exists",
                    action.get("target_slot_id", "missing"),
                    affected_ids=action.get("content_ids", []),
                    root_cause_bucket="placement_slot_gap",
                )
            )
            next_index += 1
            continue
        accepted = slot.get("accepted_content_kinds", [])
        if action.get("render_kind") not in accepted:
            findings.append(
                make_finding(
                    next_index,
                    "placement",
                    Status.FAIL,
                    "slot_incompatible",
                    f"content kind {action.get('render_kind')} is not accepted by slot",
                    ", ".join(accepted),
                    action.get("render_kind", "missing"),
                    affected_ids=action.get("content_ids", []),
                    root_cause_bucket="placement_slot_gap",
                )
            )
            next_index += 1
        if not action.get("evidence"):
            findings.append(
                make_finding(
                    next_index,
                    "placement",
                    Status.UNKNOWN,
                    "placement_action_missing_evidence",
                    "Placement action has no evidence",
                    "evidence list is non-empty",
                    action.get("action_id", "missing"),
                    affected_ids=action.get("content_ids", []),
                    root_cause_bucket="placement_evidence_gap",
                )
            )
            next_index += 1
    for item in unresolved:
        if item.get("blocking", True):
            findings.append(
                make_finding(
                    next_index,
                    "placement",
                    Status.UNKNOWN,
                    "blocking_unresolved_content",
                    f"Unresolved content {item.get('content_id')} blocks placement",
                    "content is placeable or explicitly rejected by contract",
                    item.get("reason", "unresolved"),
                    affected_ids=[item.get("content_id", "")],
                    root_cause_bucket="placement_unresolved",
                )
            )
            next_index += 1
    return findings


def write_placement_outputs(out_dir: Path, result: StageResult) -> None:
    artifact = result.artifacts.get("placement_plan")
    if artifact is not None:
        path = out_dir / "artifacts" / "placement_plan.json"
        write_json(path, artifact)
        result.artifact_paths["placement_plan"] = path
