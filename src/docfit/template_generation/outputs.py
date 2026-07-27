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
        "01.8_t4_l1_stage_input.json",
        "t4_l1_stage_input",
        "T4 输入：只由 sealed L1 单向派生的阶段视图。",
    )
    write_step_json(
        "02.1_t2_input.json",
        "t2_input",
        "T2 AI 输入：按页排列的真实页图引用与客观 L1 事实。",
    )
    write_step_yaml(
        "02.2_t2_ai_unit_observation.yaml",
        "t2_ai_unit_observation",
        "T2 AI 观察产物：AI 决策核心只含 unit_id、unit_name 和页面边界。",
    )
    write_step_yaml(
        "02_unit_map.yaml",
        "unit_map",
        "T2 final：AI 页面组经完整覆盖校验和确定性 L1 绑定后的唯一 unit_map。",
    )
    write_step_json(
        "03.0_t3_hierarchical_stage_input.json",
        "t3_hierarchical_stage_input",
        "T3 分层输入：只基于 sealed L1 与本次运行 T2 final 的可校验节点树。",
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
        "04.1_t4_ai_layout_observation.yaml",
        "t4_ai_layout_observation",
        "T4 AI 原始布局判断：唯一语义来源，保留模型输出和校验诊断。",
    )
    write_step_yaml(
        "04_global_spec.yaml",
        "global_spec",
        "T4 final：AI 判断经身份、证据和契约校验后发布的唯一 global_spec。",
    )
    write_step_yaml(
        "05_template_spec.yaml",
        "template_spec",
        "T5 final：只合并 T2/T3/T4 final 后发布的唯一模板解析主产物。",
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
        "09.1_ai_observation_bundle.json",
        "ai_observation_bundle",
        "Agent 观察输入：同 run Module 1 AI observation bundle。",
    )
    write_step_json(
        "12_t3_materialization_trace.json",
        "t3_materialization_trace",
        "T3 物化自检：记录 AI 决策覆盖、安全 Keep 和最终 element_spec 物化摘要；不是第二条输出路线。",
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
