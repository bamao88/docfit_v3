from __future__ import annotations

from datetime import datetime
import shutil
from pathlib import Path
from typing import Any

from docfit.core.io import now_iso, sha256_file, write_json
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
    source_tree: dict[str, Any],
    structure_candidates: dict[str, Any],
    generation_model: dict[str, Any],
    plan: dict[str, Any],
    copy_source_snapshot_docx: Path | None,
    generated_template_docx: Path,
    manifest: dict[str, Any],
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
        "01_source_template_tree.json",
        source_tree,
        "阶段一：从学校原始 Word 解析出的真实结构树。",
    )
    write_step_json(
        "02_template_structure_candidates.json",
        structure_candidates,
        "阶段二：系统从源 Word 推断出的候选结构和证据。",
    )
    write_step_json(
        "03_template_generation_model.json",
        generation_model,
        "阶段三：生成模板模型与处理策略。",
    )
    write_step_json(
        "04_template_generation_plan.json",
        plan,
        "阶段四：真正会被执行的生成动作列表。",
    )
    if copy_source_snapshot_docx is not None and copy_source_snapshot_docx.exists():
        record(
            copy_source_snapshot_docx,
            "阶段五：只执行 copy_source_docx 后的 Word；尚未插 slot、删说明、加分页或分节。",
        )
    copy_docx(
        generated_template_docx,
        "05.1_generated_template.docx",
        "阶段五：执行全部生成动作后的可填写模板 Word。",
    )
    write_step_json(
        "05.2_template_generation_manifest.json",
        manifest,
        "阶段五：生成过程记录，包含 action、hash、slot、分页和分节等证据。",
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
    for key in [
        "template_generation_request",
        "source_template_tree",
        "template_structure_candidates",
        "template_generation_model",
        "template_generation_plan",
        "template_generation_manifest",
    ]:
        artifact = result.artifacts.get(key)
        if artifact is None:
            continue
        path = out_dir / "artifacts" / f"{key}.json"
        write_json(path, artifact)
        result.artifact_paths[key] = path
