from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from docfit.core.io import now_iso, sha256_file, write_json, write_yaml
from docfit.core.models import StageResult


def write_template_generation_outputs(out_dir: Path, result: StageResult) -> None:
    files: list[dict[str, Any]] = []

    def optional_path(value: Any) -> Path | None:
        if value is None:
            return None
        text = str(value)
        if not text:
            return None
        return Path(text)

    def record(path: Path, description: str) -> None:
        files.append(
            {
                "name": path.name,
                "path": str(path),
                "description": description,
                "sha256": sha256_file(path) if path.exists() else None,
            }
        )

    def copy_docx(src: Path, name: str, description: str) -> Path | None:
        if not src.exists():
            return None
        dst = out_dir / name
        if src.resolve() != dst.resolve():
            shutil.copyfile(src, dst)
        record(dst, description)
        return dst

    def write_step_json(name: str, key: str, description: str) -> Path | None:
        payload = result.artifacts.get(key)
        if payload is None:
            return None
        path = out_dir / name
        write_json(path, payload)
        record(path, description)
        result.artifact_paths[f"ordered.{key}"] = path
        return path

    def write_step_yaml(name: str, key: str, description: str) -> Path | None:
        payload = result.artifacts.get(key)
        if payload is None:
            return None
        path = out_dir / name
        write_yaml(path, payload)
        record(path, description)
        result.artifact_paths[f"ordered.{key}"] = path
        return path

    request = result.artifacts.get("template_generation_request") or {}
    source_template = optional_path(request.get("source_template_docx"))
    if source_template is not None:
        copy_docx(
            source_template,
            "00_input_source_template.docx",
            "输入：学校原始模板 Word；生成器从这里读取真实 Word 结构。",
        )
    write_step_json(
        "00_template_generation_request.json",
        "template_generation_request",
        "运行请求：记录源文件、输出目录和生成策略。",
    )
    write_step_json(
        "01_document_facts.json",
        "document_facts",
        "T1：从学校原始 Word 解析出的 run 级事实库。",
    )
    write_step_json(
        "01.5_l1_input_contract.json",
        "template_generation_l1_input_contract",
        "L1：T1 与 render/page/object/run 客观事实封存后的唯一事实输入契约。",
    )
    write_step_json(
        "01.6_t2_l1_stage_input.json",
        "t2_l1_stage_input",
        "T2 输入：只由 sealed L1 单向派生的阶段视图。",
    )
    write_step_json(
        "01.7_t3_l1_compatibility_input.json",
        "t3_l1_compatibility_input",
        "T3 兼容输入：只由 sealed L1 单向派生，等待 Plan 06 替换。",
    )
    write_step_json(
        "01.8_t4_l1_stage_input.json",
        "t4_l1_stage_input",
        "T4 输入：只由 sealed L1 单向派生的阶段视图。",
    )
    write_step_yaml(
        "02.0_t2_code_unit_map.yaml",
        "t2_code_unit_map",
        "T2/code_raw：agent 合并前由确定性代码直接生成的单元边界。",
    )
    write_step_json(
        "02.1_t2_input.json",
        "t2_input",
        "T2：边界/标签低置信问题的确定性投影，供人工或 AI 兜底使用。",
    )
    write_step_yaml(
        "02.2_t2_ai_unit_observation.yaml",
        "t2_ai_unit_observation",
        "T2/ai_raw：Module 1 AI 独立生成的单元观察；未提供 AI 时标记 NOT_AVAILABLE。",
    )
    write_step_yaml(
        "02.3_t2_merged_unit_map.yaml",
        "t2_merged_unit_map",
        "T2/merged：AI/code bridge 与 reconciler 后进入 T3/T5/T6 的最终单元边界。",
    )
    write_step_yaml(
        "02_unit_map.yaml",
        "unit_map",
        "T2 兼容别名：当前主链路消费的最终 merged unit_map。",
    )
    write_step_json(
        "03.0_t3_hierarchical_stage_input.json",
        "t3_hierarchical_stage_input",
        "T3 分层输入：基于 sealed L1 与对应 T2 route 的可校验节点树。",
    )
    write_step_yaml(
        "03.1_t3_ai_element_observation.yaml",
        "t3_ai_element_observation",
        "T3 AI 原始分层判断；未提供 AI 时标记 NOT_AVAILABLE。",
    )
    write_step_json(
        "03.1.5_t3_sparse_decision_trace.json",
        "t3_sparse_decision_trace",
        "T3 稀疏决策：保留停止层级、递归调用和完整 atomic coverage ledger。",
    )
    write_step_yaml(
        "03_element_spec.yaml",
        "element_spec",
        "T3 canonical：AI 判断经身份校验、继承展开和安全 Keep 后的元素策略。",
    )
    write_step_yaml(
        "04.0_t4_code_global_spec.yaml",
        "t4_code_global_spec",
        "T4/code_raw：agent 合并前由确定性代码直接生成的全局布局规则。",
    )
    write_step_yaml(
        "04.1_t4_ai_layout_observation.yaml",
        "t4_ai_layout_observation",
        "T4/ai_raw：Module 1 AI 独立生成的布局观察；未提供 AI 时标记 NOT_AVAILABLE。",
    )
    write_step_yaml(
        "04.2_t4_merged_global_spec.yaml",
        "t4_merged_global_spec",
        "T4/merged：当前进入 T5/T6 的最终全局布局规则。",
    )
    write_step_yaml(
        "04_global_spec.yaml",
        "global_spec",
        "T4 兼容别名：当前主链路消费的最终 merged global_spec。",
    )
    write_step_yaml(
        "05_template_spec.yaml",
        "template_spec",
        "T5：模板解析主产物，供可填模板构建和后续阶段消费。",
    )

    if source_template is not None:
        copy_docx(
            source_template,
            "06.0_copy_source_docx.docx",
            "T6 中间态：只执行 copy_source_docx，尚未做减法构建。",
        )
    fillable_template = result.artifact_paths.get("fillable_template_docx")
    if fillable_template is not None:
        ordered_fillable = copy_docx(
            fillable_template,
            "06.1_fillable_template.docx",
            "T6 成品：执行全部构建动作后的可填写模板 Word。",
        )
        if ordered_fillable is not None:
            result.artifact_paths["ordered.fillable_template_docx"] = ordered_fillable
    write_step_json(
        "06.2_build_manifest.json",
        "build_manifest",
        "T6：构建过程记录，包含 action、hash、SDT、分页和分节等证据。",
    )
    write_step_json(
        "07_verification_report.json",
        "verification_report",
        "T1-T6 聚合 verifier 报告。",
    )
    write_step_json(
        "08.5_agent_pass_plan.json",
        "template_agent_pass_plan",
        "Agent 编排：每个 pass 的阶段、窗口和允许输出层。",
    )
    write_step_json(
        "08.6_agent_post_t2_checkpoint.json",
        "template_agent_post_t2_checkpoint",
        "Agent 编排：T2 pass 后的结构与 unit_map checkpoint。",
    )
    write_step_json(
        "08.65_agent_post_t2_input.json",
        "template_agent_post_t2_input",
        "Agent 编排：T2 overlay 后的 source_seq ownership 与 unit input 视图。",
    )
    write_step_json(
        "08.7_agent_unit_windows.json",
        "template_agent_unit_windows",
        "Agent 编排：基于 post-T2 结构生成的 T3 unit windows。",
    )
    write_step_json(
        "09_agent_transcript.json",
        "template_agent_transcript",
        "Agent replay/live transcript。",
    )
    write_step_json(
        "09.1_ai_observation_bundle.json",
        "ai_observation_bundle",
        "Agent 观察输入：同 run Module 1 AI observation bundle。",
    )
    write_step_json(
        "09.25_agent_observation_bridge.json",
        "template_agent_observation_bridge",
        "Agent 观察桥接：AI observation bundle 到 executable proposal/manual review 的映射。",
    )
    write_step_json(
        "09.5_agent_submission_comparison.json",
        "template_agent_submission_comparison",
        "Agent 对账：AI submission 与 deterministic 当前结果的 compatible/conflict/missing/unknown 关系。",
    )
    write_step_json(
        "10_agent_decisions.json",
        "template_agent_decisions",
        "Agent deterministic reconciler 的 accepted/rejected 决策。",
    )
    write_step_json(
        "10.5_agent_manual_review_items.json",
        "template_agent_manual_review_items",
        "Agent 人工待决：open_questions、comparison conflicts、validation failures 和高风险项。",
    )
    write_step_json(
        "11_agent_t2_overlay.json",
        "agent_t2_overlay",
        "T2 Agent overlay：只 patch structure_candidates 后重生 unit_map。",
    )
    write_step_json(
        "12_agent_t3_overlay.json",
        "agent_t3_overlay",
        "T3 Agent overlay：只 patch candidate_policy 后重生 element_spec。",
    )
    write_step_json(
        "13_agent_t4_hints.json",
        "agent_t4_hints",
        "T4 Agent hints：T4 全局布局诊断/佐证 artifact，只包含 section profile 与 page numbering hint。",
    )
    write_step_json(
        "14_agent_attribution.json",
        "agent_attribution",
        "Agent attribution：round0/post-agent diff 与 proposal 归因。",
    )
    index_path = out_dir / "99_template_generation_debug_index.json"
    write_json(
        index_path,
        {
            "artifact_type": "template_generation_debug_index",
            "artifact_version": "1.0",
            "created_at": now_iso(),
            "debug_dir": str(out_dir),
            "files": files,
        },
    )
    result.artifact_paths["ordered.template_generation_debug_index"] = index_path
