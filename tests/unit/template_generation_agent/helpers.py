from __future__ import annotations

from pathlib import Path
from typing import Any

from docfit.template_generation.agent.packet import build_template_agent_render_packet
from docfit.template_generation.artifacts import source_tree_from_document_facts
from docfit.template_generation.generation_model import build_template_generation_model
from docfit.template_generation.artifacts import build_element_spec


def document_facts() -> dict[str, Any]:
    body_flow = [
        _entry(1, "封面"),
        _entry(2, "承诺书"),
        _entry(3, "学生姓名：____"),
        _entry(4, "正文"),
    ]
    return {
        "artifact_type": "document_facts",
        "metadata": {"source_template_hash": "sha256:test-template"},
        "body_flow": body_flow,
        "runs": [],
        "unknown_objects": [],
        "indexes": {
            "by_source_seq": {
                str(item["source_seq"]): item for item in body_flow
            }
        },
        "data": {
            "paragraphs": [
                {
                    "index": item["source_seq"],
                    "text": item["text"],
                    "style": item["style"],
                }
                for item in body_flow
            ],
            "sections": [],
            "headers_footers": [],
            "numbering_definitions": [],
            "numbering_refs": [],
        },
    }


def request(tmp_path: Path) -> dict[str, Any]:
    return {
        "source_template_docx": str(tmp_path / "template.docx"),
        "source_template_hash": "sha256:test-template",
        "out_dir": str(tmp_path),
        "strategy": "source_copy_scaffold",
    }


def structure_candidates() -> dict[str, Any]:
    facts = document_facts()
    entries = facts["body_flow"]
    return {
        "artifact_type": "template_structure_candidates",
        "artifact_version": "1.1",
        "source_context": {
            "body_flow": entries,
            "paragraphs": facts["data"]["paragraphs"],
            "section_rules": [],
            "header_footer": [],
            "unknown_objects": [],
            "style_inventory": [],
        },
        "units": [
            _unit("cover", "封面", [entries[0]], order=10),
            _unit("body_main", "正文", entries[1:], order=20),
        ],
        "unknowns": [],
        "open_questions": [],
    }


def packet() -> dict[str, Any]:
    facts = document_facts()
    return build_template_agent_render_packet(
        document_facts=facts,
    )


def round0_artifacts(tmp_path: Path) -> dict[str, Any]:
    facts = document_facts()
    candidates = structure_candidates()
    req = request(tmp_path)
    unit_map = {
        "artifact_type": "unit_map",
        "units": [
            {
                "unit_id": "cover",
                "unit_name": "封面",
                "order": 1,
                "source_seq_refs": [1],
                "source_refs": ["word/document.xml:p[1]"],
                "boundary": {"start_page": 1, "end_page": 1},
                "page_policy": {
                    "start": "document_start",
                    "scope": "page_range_exclusive",
                },
            },
            {
                "unit_id": "body_main",
                "unit_name": "正文",
                "order": 2,
                "source_seq_refs": [2, 3, 4],
                "source_refs": [
                    "word/document.xml:p[2]",
                    "word/document.xml:p[3]",
                    "word/document.xml:p[4]",
                ],
                "boundary": {"start_page": 2, "end_page": 2},
                "page_policy": {
                    "start": "new_page",
                    "scope": "page_range_exclusive",
                },
            },
        ],
        "flags": [],
    }
    generation_model = build_template_generation_model(req, candidates)
    element_spec = build_element_spec(generation_model)
    return {
        "request": req,
        "document_facts": facts,
        "source_tree": source_tree_from_document_facts(facts),
        "structure_candidates": candidates,
        "unit_map": unit_map,
        "generation_model": generation_model,
        "element_spec": element_spec,
        "packet": build_template_agent_render_packet(
            document_facts=facts,
        ),
    }


def layered_submission(source_render_hash: str, *, layers: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "template-agent-layered-submission-1.0",
        "prompt_version": "template-agent-prompt-1.0",
        "source_render_hash": source_render_hash,
        "round_id": "round_001",
        "model": "fixture",
        "layers": {
            "t4": {
                "section_profile_hints": [],
                "page_numbering_hints": [],
                "open_questions": [],
                **layers.get("t4", {}),
            },
        },
    }


def _entry(index: int, text: str) -> dict[str, Any]:
    return {
        "node_id": f"body_{index:04d}",
        "structure_layer": "body_flow",
        "flow_item_type": "paragraph",
        "kind": "paragraph",
        "source_ref": f"word/document.xml:p[{index}]",
        "part_name": "word/document.xml",
        "order": index,
        "paragraph_id": f"p_{index:04d}",
        "visible": True,
        "text": text,
        "style": "Normal",
        "source_seq": index,
    }


def _unit(unit_id: str, name: str, entries: list[dict[str, Any]], *, order: int) -> dict[str, Any]:
    seqs = [entry["source_seq"] for entry in entries]
    refs = [entry["source_ref"] for entry in entries]
    return {
        "unit_id": unit_id,
        "name": name,
        "order": order,
        "status": "required",
        "candidate_policy": "fill",
        "source_refs": refs,
        "source_seq_refs": seqs,
        "source_range": {
            "start_source_ref": refs[0],
            "end_source_ref": refs[-1],
            "source_refs": refs,
        },
        "source_seq_range": {"start": seqs[0], "end": seqs[-1], "source_seq_refs": seqs},
        "anchors": [
            {
                "source_ref": refs[0],
                "source_seq": seqs[0],
                "text": entries[0]["text"],
                "confidence": "medium",
            }
        ],
        "responsibility_evidence": [],
        "conflicts": [],
        "confidence": "medium",
        "flags": [],
        "evidence": [],
        "elements": [
            {
                "element_id": f"e_{index:03d}",
                "name": entry["text"],
                "order": index,
                "candidate_policy": "fixed",
                "role_hint": "fixed_text_candidate",
                "relationship": "source_paragraph",
                "content": entry["text"],
                "style": "Normal",
                "source_refs": [entry["source_ref"]],
                "source_seq_refs": [entry["source_seq"]],
                "entry_refs": [entry["node_id"]],
                "evidence": [],
            }
            for index, entry in enumerate(entries, start=1)
        ],
    }
