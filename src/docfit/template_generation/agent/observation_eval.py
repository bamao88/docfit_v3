"""Module 1 阶段准确率评测：AI 产物 vs 人工标注标准文件（gold）。

补齐流程缺口：每个阶段产物都要和 ``standards/targets/<school>/v1/template_generation/``
下的标准文件对比，算该阶段准确率，再和耗时合成整体质量。

标准文件是人工评审 gold（``standard_state: signed_active``）：
- T2 `t2_unit_pagination.standard.yaml` → `expected.unit_order`（正确单元与顺序）
- T3 `t3_element_policy.standard.yaml`   → `expected.policy_groups`（每单元的应然主策略）
- T4 `t4_global_layout.standard.yaml`    → 版式（无真实页图时 AI abstain，不可评）

准确率是**对照 gold 的正确性**，区别于覆盖率（完整性）和 demotions（合规性）。
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from docfit.core.io import read_yaml

STANDARDS_ROOT = Path("standards/targets")

# gold policy_groups 的组名 → 该组单元的应然主策略。
_GROUP_TO_POLICY = {
    "fixed_units": "fixed",
    "manual_only_units": "manual_only",
    "fill_units": "fill",
    "generated_units": "generated",
    "template_default_optional_units": "template_default",
}


def stage_standard_path(school: str, stage: str, *, root: Path = STANDARDS_ROOT) -> Path:
    name = {
        "t2": "t2_unit_pagination.standard.yaml",
        "t3": "t3_element_policy.standard.yaml",
        "t4": "t4_global_layout.standard.yaml",
    }[stage]
    return root / school / "v1" / "template_generation" / name


def load_stage_standard(school: str, stage: str, *, root: Path = STANDARDS_ROOT) -> dict[str, Any]:
    return read_yaml(stage_standard_path(school, stage, root=root)) or {}


def evaluate_unit_stage(
    ai_unit_observation: dict[str, Any],
    t2_standard: dict[str, Any],
) -> dict[str, Any]:
    """T2：AI 单元集合/顺序 vs gold expected.unit_order。"""

    gold_order = [str(u) for u in t2_standard.get("expected", {}).get("unit_order", [])]
    gold_set = set(gold_order)
    ai_order = [
        str(item.get("unit_id"))
        for item in ai_unit_observation.get("items", [])
        if item.get("unit_id") and item.get("unit_id") != "unknown_unit"
    ]
    ai_seen: list[str] = []
    for uid in ai_order:  # 去重保序
        if uid not in ai_seen:
            ai_seen.append(uid)
    ai_set = set(ai_seen)

    hit = ai_set & gold_set
    precision = len(hit) / len(ai_set) if ai_set else 0.0
    recall = len(hit) / len(gold_set) if gold_set else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return {
        "stage": "t2_units",
        "gold_units": len(gold_set),
        "ai_units": len(ai_set),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "order_exact_match": ai_seen == gold_order,
        "missing_units": sorted(gold_set - ai_set),
        "extra_units": sorted(ai_set - gold_set),
    }


def evaluate_element_stage(
    ai_element_observation: dict[str, Any],
    t3_standard: dict[str, Any],
) -> dict[str, Any]:
    """T3：AI 每单元的主策略 vs gold policy_groups；外加必填合规率。"""

    groups = t3_standard.get("expected", {}).get("policy_groups", {}) or {}
    expected_policy: dict[str, str] = {}
    for group_name, policy in _GROUP_TO_POLICY.items():
        for unit_id in groups.get(group_name, []) or []:
            expected_policy[str(unit_id)] = policy

    # AI 每单元用到的 policy 集合 + 众数。
    by_unit: dict[str, list[str]] = {}
    for item in ai_element_observation.get("items", []):
        unit_id = str(item.get("unit_id") or "")
        policy = str(item.get("policy") or "")
        if unit_id and policy:
            by_unit.setdefault(unit_id, []).append(policy)
    ai_dominant = {u: Counter(ps).most_common(1)[0][0] for u, ps in by_unit.items()}
    ai_policy_set = {u: set(ps) for u, ps in by_unit.items()}

    evaluated = [u for u in expected_policy if u in ai_dominant]
    # 两个口径：
    # 1) dominant：AI 众数策略 == gold 主策略（严格但对混合单元偏苛）。
    # 2) present（更公允）：gold 的定性策略在该单元的 AI 元素里**出现过**——
    #    即 AI 是否抓到了这个单元的定性策略（如 grade_form 里有没有 manual_only）。
    dominant_hits = [u for u in evaluated if ai_dominant[u] == expected_policy[u]]
    present_hits = [u for u in evaluated if expected_policy[u] in ai_policy_set[u]]
    mismatches = [
        {
            "unit_id": u,
            "expected": expected_policy[u],
            "ai_dominant": ai_dominant[u],
            "expected_present": expected_policy[u] in ai_policy_set[u],
        }
        for u in evaluated
        if ai_dominant[u] != expected_policy[u]
    ]

    demotions = ai_element_observation.get("quality_report", {}).get("demotions", [])
    required_field_fails = sum(1 for d in demotions if d.get("check_id") == "C-REQUIRED-FIELD")
    total_items = len(ai_element_observation.get("items", [])) + required_field_fails

    return {
        "stage": "t3_element_policy",
        "units_evaluated": len(evaluated),
        "unit_dominant_policy_accuracy": round(len(dominant_hits) / len(evaluated), 4) if evaluated else 0.0,
        "distinguishing_policy_recall": round(len(present_hits) / len(evaluated), 4) if evaluated else 0.0,
        "policy_mismatches": mismatches,
        "required_field_compliance": (
            round(1 - required_field_fails / total_items, 4) if total_items else 1.0
        ),
        "note": (
            "gold policy_groups 是单元级定性策略（非逐元素）。dominant=AI 众数是否等于 gold 主策略"
            "（对混合单元偏苛）；distinguishing_recall=gold 主策略是否在该单元 AI 元素里出现过（更公允）。"
            "逐元素准确率需元素级 gold，当前标准不提供。"
        ),
    }


def evaluate_layout_stage(
    ai_layout_observation: dict[str, Any],
    ai_unit_observation: dict[str, Any],
    t4_standard: dict[str, Any],
) -> dict[str, Any]:
    """T4：用确定性 page_map + AI 单元算每单元页隔离，对照 gold layout_policy。

    gold.layout_policy 把单元分 standalone(独立页) / flowing(可连续流动)。渲染后
    page_map(seq→page) 是确定性事实，据此判每单元是否独占页，与 gold 比即页策略准确率。
    无渲染时只有全局版式，页策略不可评。
    """

    global_profile_present = any(
        it.get("source") == "deterministic_facts" for it in ai_layout_observation.get("items", [])
    )
    page_map_raw = ai_layout_observation.get("page_map") or {}
    if not page_map_raw:
        return {
            "stage": "t4_layout",
            "global_profile_present": global_profile_present,
            "page_policy_evaluable": False,
            "note": "无渲染页图 → 只产出全局版式，每单元页隔离策略不可评（需 --docx 渲染）。",
        }

    page_map = {int(k): int(v) for k, v in page_map_raw.items()}
    policy = t4_standard.get("expected", {}).get("layout_policy", {}) or {}
    gold_standalone = set(policy.get("standalone_units", []) or [])
    gold_flowing = set(policy.get("flowing_units", []) or [])

    # 每单元 → 覆盖的页；每页 → 覆盖的单元。
    unit_pages: dict[str, set[int]] = {}
    for item in ai_unit_observation.get("items", []):
        unit_id = str(item.get("unit_id") or "")
        if not unit_id or unit_id == "unknown_unit":
            continue
        pages = {page_map[s] for s in item.get("source_seq_refs", []) if s in page_map}
        if pages:
            unit_pages.setdefault(unit_id, set()).update(pages)
    page_units: dict[int, set[str]] = {}
    for unit_id, pages in unit_pages.items():
        for page in pages:
            page_units.setdefault(page, set()).add(unit_id)

    # standalone = 该单元**独占至少一整页**（存在只有它的页）；否则 flowing。
    # 用“独占某页”而非“任何页不共享”，避免相邻单元在边界页共享导致的误判。
    predicted = {
        u: ("standalone" if any(page_units[p] == {u} for p in ps) else "flowing")
        for u, ps in unit_pages.items()
    }

    def gold_policy(unit_id: str) -> str | None:
        if unit_id in gold_standalone:
            return "standalone"
        if unit_id in gold_flowing:
            return "flowing"
        return None

    evaluated = [u for u in predicted if gold_policy(u) is not None]
    matches = [u for u in evaluated if predicted[u] == gold_policy(u)]
    mismatches = [
        {
            "unit_id": u,
            "expected": gold_policy(u),
            "predicted": predicted[u],
            "pages": sorted(unit_pages[u]),
        }
        for u in evaluated
        if predicted[u] != gold_policy(u)
    ]
    open_questions = [
        {
            "question_id": f"q_page_policy_{m['unit_id']}",
            "blocking_level": "non_blocking",
            "check_id": "C-LAYOUT-PAGE-POLICY",
            "affected_unit": m["unit_id"],
            "reason": f"页隔离策略与 gold 不符：gold={m['expected']} 实测={m['predicted']} 页={m['pages']}",
        }
        for m in mismatches
    ]
    return {
        "stage": "t4_layout",
        "global_profile_present": global_profile_present,
        "page_policy_evaluable": True,
        "page_count": ai_layout_observation.get("page_count"),
        "units_evaluated": len(evaluated),
        "page_isolation_accuracy": round(len(matches) / len(evaluated), 4) if evaluated else 0.0,
        "page_policy_mismatches": mismatches,
        "open_questions": open_questions,
    }


def evaluate_bundle(bundle: dict[str, Any], *, school: str, root: Path = STANDARDS_ROOT) -> dict[str, Any]:
    """对一个 observation bundle 做三阶段准确率 + 耗时评测。"""

    t2 = evaluate_unit_stage(bundle["ai_unit_observation"], load_stage_standard(school, "t2", root=root))
    t3 = evaluate_element_stage(
        bundle["ai_element_observation"], load_stage_standard(school, "t3", root=root)
    )
    t4 = evaluate_layout_stage(
        bundle["ai_layout_observation"],
        bundle["ai_unit_observation"],
        load_stage_standard(school, "t4", root=root),
    )
    return {
        "artifact_type": "ai_observation_eval",
        "school": school,
        "model": bundle.get("model"),
        "thinking_note": "见 bundle.model / 运行参数",
        "timing": bundle.get("timing", {}),
        "stages": {"t2": t2, "t3": t3, "t4": t4},
    }
