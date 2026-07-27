from __future__ import annotations

from typing import Any

import pytest

from docfit.template_generation.agent.evidence import EvidenceFirewallError
from docfit.template_generation.agent.observation_multimodal import attachment_refs
from docfit.template_generation.agent.observation_prompts import (
    ObservationPromptTemplates,
    assemble_observation_messages,
    build_observation_prompt,
)
from docfit.template_generation.agent.observation_schema import open_questions_from


def clean_evidence(stage: str) -> dict[str, Any]:
    return {"scope": stage, "source_render_hash": "sha256:x", "rows": []}


def hierarchical_evidence() -> dict[str, Any]:
    return {
        "scope": "t3_hierarchical_node",
        "target": {"ref": "unit:cover", "source_kind": "unit"},
        "completeness": {
            "children_complete": True,
            "content_complete": True,
        },
        "facts": {"unit_id": "cover"},
        "children": [
            {
                "ref": "unit:cover/paragraph:p_0001",
                "source_kind": "paragraph",
            }
        ],
        "context": {},
        "visual_evidence": [],
    }


def test_t2_prompt_does_not_inject_unit_dictionary() -> None:
    prompt = build_observation_prompt(
        stage="t2",
        evidence_view=clean_evidence("t2"),
    )
    system, _ = assemble_observation_messages("t2", clean_evidence("t2"))

    assert prompt["glossary"] == ""
    assert "- cover (封面)" not in system
    assert "以页面为最小对象" in system
    assert prompt["allowed_labels"] == {}
    assert "允许标签集" in system


def test_t3_hierarchy_prompt_uses_sparse_stop_or_descend_contract() -> None:
    evidence = hierarchical_evidence()
    prompt = build_observation_prompt(
        stage="t3_hierarchy",
        evidence_view=evidence,
    )
    system, user = assemble_observation_messages("t3_hierarchy", evidence)

    assert prompt["allowed_labels"]["results"] == [
        "keep",
        "fill",
        "delete",
        "split",
    ]
    assert prompt["abstain_is_valid"] is False
    assert "inspect_child_refs" in system
    assert "必须在 child_decisions 中直接给出" in system
    assert "unit/table 只允许 keep 或 split" in system
    assert '"unit_id": "cover"' in user


def test_t3_hierarchy_prompt_rejects_policy_leak() -> None:
    evidence = hierarchical_evidence()
    evidence["facts"]["policy"] = "fixed"

    with pytest.raises(ValueError, match="leaked semantic field 'policy'"):
        build_observation_prompt(
            stage="t3_hierarchy",
            evidence_view=evidence,
        )


def test_flat_t3_prompt_stages_are_removed() -> None:
    for stage in ("t3", "t3_unit"):
        with pytest.raises(ValueError, match="unknown observation stage"):
            build_observation_prompt(
                stage=stage,
                evidence_view=clean_evidence(stage),
            )


def test_t3_hierarchy_has_one_prompt_source_file() -> None:
    from importlib import resources

    prompt_dir = resources.files(
        "docfit.template_generation.agent"
    ).joinpath("prompt_templates")

    assert prompt_dir.joinpath("t3_hierarchical_prompt.txt").is_file()
    assert not prompt_dir.joinpath("t3_prompt.txt").is_file()
    assert not prompt_dir.joinpath("t3_unit_rubric.txt").is_file()
    assert not prompt_dir.joinpath("t3_unit_output_contract.txt").is_file()


def test_build_prompt_still_firewalls_evidence() -> None:
    with pytest.raises(EvidenceFirewallError):
        build_observation_prompt(
            stage="t2",
            evidence_view={
                "rows": [
                    {"source_seq": 1, "unit_map": {"unit_id": "cover"}},
                ]
            },
        )


def test_prompt_templates_are_explicit_parameters() -> None:
    templates = ObservationPromptTemplates(
        system="SYSTEM $rubric :: $output_contract :: $allowed_labels_json",
        rubrics={"t2": "CUSTOM T2 RUBRIC"},
        output_contracts={"t2": "CUSTOM T2 CONTRACT"},
        t4_page_vision="PAGE $page_no $layout_context",
    )
    prompt = build_observation_prompt(
        stage="t2",
        evidence_view=clean_evidence("t2"),
        prompt_templates=templates,
    )
    system, user = assemble_observation_messages(
        "t2",
        clean_evidence("t2"),
        prompt_templates=templates,
    )

    assert prompt["rubric"] == "CUSTOM T2 RUBRIC"
    assert prompt["output_contract"] == "CUSTOM T2 CONTRACT"
    assert "CUSTOM T2 RUBRIC" in system
    assert "CUSTOM T2 CONTRACT" in system
    assert user.startswith("{")


def test_t2_prompt_hides_visual_attachment_paths_and_keeps_refs() -> None:
    evidence = {
        "scope": "t2_full_document",
        "source_render_hash": "sha256:x",
        "_visual_attachment_limit": 2,
        "visual_evidence": [
            {
                "visual_ref": "page:1",
                "page_no": 1,
                "_attachment_path": "/private/tmp/page-01.png",
            },
            {
                "visual_ref": "page:2",
                "page_no": 2,
                "_attachment_path": "/private/tmp/page-02.png",
            },
        ],
    }

    _, user = assemble_observation_messages("t2", evidence)

    assert "page:1" in user and "page:2" in user
    assert "_attachment_path" not in user
    assert "_visual_attachment_limit" not in user
    assert "/private/tmp" not in user
    assert attachment_refs(evidence) == ["page:1", "page:2"]


def test_open_questions_surface_contested_unknown_and_low_consistency() -> None:
    questions = open_questions_from(
        demotions=[
            {
                "item_id": "94",
                "check_id": "C-COVERAGE-CONTESTED",
                "reason": "tie",
            }
        ],
        coverage={"unknown_source_seq": [5, 6, 7, 20]},
        self_consistency={"agreement": {"16": 0.4, "17": 1.0}},
    )

    checks = {question["check_id"] for question in questions}
    assert {
        "C-COVERAGE-CONTESTED",
        "C-SELF-CONSISTENCY",
        "C-COVERAGE-UNKNOWN",
    } <= checks
