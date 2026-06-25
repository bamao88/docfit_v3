from __future__ import annotations

from datetime import datetime
import shutil
from pathlib import Path
from typing import Any

from docfit.core.io import now_iso, sha256_file, write_json, write_yaml
from docfit.core.models import StageResult


def _new_template_generation_debug_dir(debug_root: Path | None) -> Path | None:
    if debug_root is None:
        return None
    timestamp = datetime.now().astimezone().strftime("%Y%m%dT%H%M%S%f%z")
    debug_dir = debug_root / timestamp
    suffix = 2
    while debug_dir.exists():
        debug_dir = debug_root / f"{timestamp}_{suffix:02d}"
        suffix += 1
    debug_dir.mkdir(parents=True, exist_ok=False)
    return debug_dir


def write_template_generation_debug_snapshot(
    debug_dir: Path,
    *,
    source_template_docx: Path,
    request: dict[str, Any],
    document_facts: dict[str, Any],
    unit_map: dict[str, Any],
    element_spec: dict[str, Any],
    global_spec: dict[str, Any],
    template_spec: dict[str, Any],
    source_tree: dict[str, Any],
    structure_candidates: dict[str, Any],
    generation_model: dict[str, Any],
    plan: dict[str, Any],
    copy_source_snapshot_docx: Path | None,
    fillable_template_docx: Path,
    build_manifest: dict[str, Any],
    verification_report: dict[str, Any] | None = None,
    t2_input: dict[str, Any] | None = None,
) -> None:
    debug_dir.mkdir(parents=True, exist_ok=True)
    files: list[dict[str, Any]] = []

    def record(path: Path, description: str) -> None:
        files.append(
            {
                "name": path.name,
                "path": str(path),
                "description": description,
                "sha256": sha256_file(path) if path.exists() else None,
            }
        )

    def copy_docx(src: Path, name: str, description: str) -> Path:
        dst = debug_dir / name
        if src.resolve() != dst.resolve():
            shutil.copyfile(src, dst)
        record(dst, description)
        return dst

    def write_step_json(name: str, payload: dict[str, Any], description: str) -> Path:
        path = debug_dir / name
        write_json(path, payload)
        record(path, description)
        return path

    def write_step_yaml(name: str, payload: dict[str, Any], description: str) -> Path:
        path = debug_dir / name
        write_yaml(path, payload)
        record(path, description)
        return path

    copy_docx(
        source_template_docx,
        "00_input_source_template.docx",
        "输入：学校原始模板 Word；生成器从这里读取真实 Word 结构。",
    )
    write_step_json(
        "00_template_generation_request.json",
        request,
        "运行请求：记录源文件、输出目录和生成策略。",
    )
    write_step_json(
        "01_document_facts.json",
        document_facts,
        "T1：从学校原始 Word 解析出的 run 级事实库。",
    )
    write_step_yaml(
        "02_unit_map.yaml",
        unit_map,
        "T2：从事实库确定性切分出的模板单元边界。",
    )
    if t2_input is not None:
        write_step_json(
            "02.1_t2_input.json",
            t2_input,
            "T2：边界/标签低置信问题的确定性投影，供人工或 AI 兜底使用。",
        )
    write_step_yaml(
        "03_element_spec.yaml",
        element_spec,
        "T3：单元内部元素、策略和填充来源。",
    )
    write_step_yaml(
        "04_global_spec.yaml",
        global_spec,
        "T4：页面、分节、页眉页脚、编号和默认样式规则。",
    )
    write_step_yaml(
        "05_template_spec.yaml",
        template_spec,
        "T5：模板解析主产物，供可填模板构建和后续阶段消费。",
    )
    write_step_json(
        "legacy_01_source_template_tree.json",
        source_tree,
        "兼容调试视图：由 document_facts 派生的旧 source_template_tree。",
    )
    write_step_json(
        "legacy_02_template_structure_candidates.json",
        structure_candidates,
        "兼容调试视图：旧候选结构。",
    )
    write_step_json(
        "legacy_03_template_generation_model.json",
        generation_model,
        "兼容调试视图：旧生成模型。",
    )
    write_step_json(
        "legacy_04_template_generation_plan.json",
        plan,
        "兼容调试视图：旧 action plan。",
    )
    if copy_source_snapshot_docx is not None and copy_source_snapshot_docx.exists():
        record(
            copy_source_snapshot_docx,
            "阶段五：只执行 copy_source_docx 后的 Word；尚未插 slot、删说明、加分页或分节。",
        )
    copy_docx(
        fillable_template_docx,
        "06.1_fillable_template.docx",
        "T6：执行全部构建动作后的可填写模板 Word。",
    )
    write_step_json(
        "06.2_build_manifest.json",
        build_manifest,
        "T6：构建过程记录，包含 action、hash、SDT、分页和分节等证据。",
    )
    if verification_report is not None:
        write_step_json(
            "07_verification_report.json",
            verification_report,
            "T1-T6 聚合 verifier 报告。",
        )
    write_step_json(
        "99_template_generation_debug_index.json",
        {
            "artifact_type": "template_generation_debug_index",
            "artifact_version": "1.0",
            "created_at": now_iso(),
            "debug_dir": str(debug_dir),
            "files": files,
        },
        "非阶段文件：本调试目录里的文件索引和说明。",
    )


def write_template_generation_outputs(out_dir: Path, result: StageResult) -> None:
    json_keys = [
        "template_generation_request",
        "document_facts",
        "build_manifest",
        "verification_report",
        "template_artifact",
        "source_template_tree",
        "template_structure_candidates",
        "t2_input",
        "template_generation_model",
        "template_generation_plan",
    ]
    yaml_keys = ["unit_map", "element_spec", "global_spec", "template_spec"]
    for key in json_keys:
        artifact = result.artifacts.get(key)
        if artifact is None:
            continue
        path = out_dir / "artifacts" / f"{key}.json"
        write_json(path, artifact)
        result.artifact_paths[key] = path
    for key in yaml_keys:
        artifact = result.artifacts.get(key)
        if artifact is None:
            continue
        path = out_dir / "artifacts" / f"{key}.yaml"
        write_yaml(path, artifact)
        result.artifact_paths[key] = path
    write_template_generation_ordered_files(out_dir, result)


def write_template_generation_ordered_files(out_dir: Path, result: StageResult) -> None:
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
    write_step_yaml(
        "02_unit_map.yaml",
        "unit_map",
        "T2：从事实库确定性切分出的模板单元边界。",
    )
    write_step_json(
        "02.1_t2_input.json",
        "t2_input",
        "T2：边界/标签低置信问题的确定性投影，供人工或 AI 兜底使用。",
    )
    write_step_yaml(
        "03_element_spec.yaml",
        "element_spec",
        "T3：单元内部元素、策略和填充来源。",
    )
    write_step_yaml(
        "04_global_spec.yaml",
        "global_spec",
        "T4：页面、分节、页眉页脚、编号和默认样式规则。",
    )
    write_step_yaml(
        "05_template_spec.yaml",
        "template_spec",
        "T5：模板解析主产物，供可填模板构建和后续阶段消费。",
    )

    manifest = result.artifacts.get("build_manifest") or {}
    copy_snapshot = optional_path(
        manifest.get("debug_snapshot", {}).get("copy_source_docx")
    )
    copy_source = (
        copy_snapshot
        if copy_snapshot is not None and copy_snapshot.exists()
        else source_template
    )
    if copy_source is not None:
        copy_docx(
            copy_source,
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
