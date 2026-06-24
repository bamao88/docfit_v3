from __future__ import annotations

import shlex
import subprocess
from pathlib import Path
from typing import Any

from docfit.core.io import (
    ensure_dir,
    now_iso,
    read_json,
    sha256_file,
    sha256_text,
    write_json,
    write_text,
)
from docfit.template_gap.inspector import inspect_generated_template_docx


INSPECTION_KEYS = [
    "paragraphs",
    "tables",
    "headers_footers",
    "fields",
    "footnotes",
    "text_boxes",
    "images",
    "breaks",
    "sections",
    "numbering_refs",
    "numbering_definitions",
    "unknown_visible_objects",
]

IMPACT_BY_KEY = {
    "paragraphs": "可能影响模板可见文本、学生内容台账或正文顺序证据",
    "tables": "可能影响表格内容台账、模板单元定位或渲染证据",
    "headers_footers": "可能影响页眉页脚证据、模板 gap 或最终渲染验收",
    "fields": "可能影响目录、页码、交叉引用等 Word 字段证据",
    "footnotes": "可能影响可见内容完整性；缺失时应维持 UNKNOWN",
    "text_boxes": "可能影响可见内容完整性；缺失时应维持 UNKNOWN",
    "images": "可能影响图片关系、媒体 hash 和内容台账证据",
    "breaks": "可能影响分页、分节或页面布局证据",
    "sections": "可能影响页面规则、页边距、纸张和分节证据",
    "numbering_refs": "可能影响标题编号、列表编号和顺序证据",
    "numbering_definitions": "可能影响编号规则和样式证据",
    "unknown_visible_objects": "可能暴露当前 inspector 未建模的可见对象",
}


def write_docx4j_comparison_outputs(
    docx_path: Path,
    out_dir: Path,
    *,
    command: list[str] | None = None,
    timeout_seconds: int = 120,
    root: Path | None = None,
) -> dict[str, Any]:
    """Run the Python inspector plus optional docx4j inspector and write reports."""

    ensure_dir(out_dir)
    artifact_dir = ensure_dir(out_dir / "artifacts")
    python_inspection = inspect_generated_template_docx(docx_path)
    python_inspection_path = artifact_dir / "python_inspection.json"
    write_json(python_inspection_path, python_inspection)

    docx4j_inspection_path = artifact_dir / "docx4j_inspection.json"
    tool_result = run_docx4j_inspector(
        docx_path,
        docx4j_inspection_path,
        command=command,
        timeout_seconds=timeout_seconds,
        root=root,
    )
    docx4j_inspection = tool_result.get("inspection")
    if docx4j_inspection is None and docx4j_inspection_path.exists():
        try:
            docx4j_inspection = read_json(docx4j_inspection_path)
        except Exception:
            docx4j_inspection = None

    report = build_docx4j_comparison_report(
        docx_path,
        python_inspection,
        docx4j_inspection,
        tool_result=tool_result,
    )
    report["artifact_paths"] = {
        "python_inspection": str(python_inspection_path),
        **(
            {"docx4j_inspection": str(docx4j_inspection_path)}
            if docx4j_inspection_path.exists()
            else {}
        ),
        "docx4j_comparison_report": str(out_dir / "docx4j_comparison_report.json"),
        "docx4j_comparison_report_md": str(out_dir / "docx4j_comparison_report.md"),
    }
    write_json(out_dir / "docx4j_comparison_report.json", report)
    write_text(out_dir / "docx4j_comparison_report.md", render_docx4j_comparison_markdown(report))
    return report


def run_docx4j_inspector(
    docx_path: Path,
    output_json: Path,
    *,
    command: list[str] | None = None,
    timeout_seconds: int = 120,
    root: Path | None = None,
) -> dict[str, Any]:
    """Run the optional Java inspector.

    This function never raises for missing Java/Maven/tooling. A missing tool is
    diagnostic evidence only and must not block the four-stage DocFit pipeline.
    """

    ensure_dir(output_json.parent)
    invocation = _materialize_command(
        docx_path,
        output_json,
        command=command,
        root=root,
    )
    started_at = now_iso()
    try:
        completed = subprocess.run(
            invocation,
            cwd=root or Path.cwd(),
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except FileNotFoundError as exc:
        return _tool_result(
            "unavailable",
            invocation,
            started_at=started_at,
            error=f"tool command not found: {exc.filename}",
        )
    except subprocess.TimeoutExpired as exc:
        return _tool_result(
            "failed",
            invocation,
            started_at=started_at,
            error=f"docx4j inspector timed out after {timeout_seconds}s",
            stdout=exc.stdout or "",
            stderr=exc.stderr or "",
        )

    if completed.returncode != 0:
        return _tool_result(
            "failed",
            invocation,
            started_at=started_at,
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )
    if not output_json.exists():
        return _tool_result(
            "failed",
            invocation,
            started_at=started_at,
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            error="docx4j inspector exited successfully but did not write JSON output",
        )
    try:
        inspection = read_json(output_json)
    except Exception as exc:
        return _tool_result(
            "failed",
            invocation,
            started_at=started_at,
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            error=f"docx4j output JSON could not be read: {exc!r}",
        )
    return _tool_result(
        "available",
        invocation,
        started_at=started_at,
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
        inspection=inspection,
    )


def build_docx4j_comparison_report(
    docx_path: Path,
    python_inspection: dict[str, Any],
    docx4j_inspection: dict[str, Any] | None,
    *,
    tool_result: dict[str, Any],
) -> dict[str, Any]:
    python_summary = summarize_inspection(python_inspection)
    docx4j_summary = summarize_inspection(docx4j_inspection or {})
    count_diffs = (
        _count_differences(python_summary, docx4j_summary)
        if docx4j_inspection is not None
        else []
    )
    text_diffs = (
        _visible_text_differences(python_inspection, docx4j_inspection)
        if docx4j_inspection is not None
        else {"docx4j_only": [], "python_only": []}
    )
    comparison_status = "compared" if docx4j_inspection is not None else "not_run"
    return {
        "artifact_type": "docx4j_comparison_report",
        "artifact_version": "1.0",
        "producer": {"name": "docfit-docx4j-diagnostics", "version": "0.1.0"},
        "created_at": now_iso(),
        "input_docx": str(docx_path),
        "input_hashes": {
            "docx": sha256_file(docx_path) if docx_path.exists() else None,
            "python_inspection": sha256_text(repr(python_summary)),
            **(
                {"docx4j_inspection": sha256_text(repr(docx4j_summary))}
                if docx4j_inspection is not None
                else {}
            ),
        },
        "purpose": (
            "旁路比较 docx4j 和当前 Python inspector 看到了哪些 Word / OOXML 证据；"
            "该报告只用于诊断，不参与 PASS/FAIL 裁判。"
        ),
        "gate_policy": {
            "decides_pass_fail": False,
            "may_create_unknown_evidence_candidate": True,
            "missing_tool_behavior": "报告 tool_status=unavailable/failed，DocFit 主链路继续运行",
        },
        "tool": {
            key: value
            for key, value in tool_result.items()
            if key not in {"inspection"}
        },
        "comparison_status": comparison_status,
        "data": {
            "python_summary": python_summary,
            "docx4j_summary": docx4j_summary,
            "count_differences": count_diffs,
            "visible_text_differences": text_diffs,
        },
    }


def summarize_inspection(inspection: dict[str, Any]) -> dict[str, int]:
    data = inspection.get("data", {}) if inspection else {}
    summary: dict[str, int] = {}
    for key in INSPECTION_KEYS:
        value = data.get(key, [])
        summary[key] = len(value) if isinstance(value, list) else 0
    return summary


def render_docx4j_comparison_markdown(report: dict[str, Any]) -> str:
    tool = report.get("tool", {})
    data = report.get("data", {})
    count_diffs = data.get("count_differences", [])
    text_diffs = data.get("visible_text_differences", {})
    lines = [
        "# docx4j 旁路诊断报告",
        "",
        "一句话结论：这个报告只比较 docx4j 和当前 Python inspector 看到了什么；它不决定 DocFit 的 `PASS` / `FAIL`。",
        "",
        "## 工具状态",
        "",
        f"- 输入文件：`{report.get('input_docx')}`",
        f"- docx4j 工具状态：`{tool.get('status')}`",
        f"- 对比状态：`{report.get('comparison_status')}`",
        f"- 缺失工具时的处理：{report.get('gate_policy', {}).get('missing_tool_behavior')}",
        "",
        "## 对象数量摘要",
        "",
    ]
    if report.get("comparison_status") == "not_run":
        lines.extend(
            [
                "docx4j 工具未完成运行；下表中 docx4j 列为 0 只表示没有旁路结果，不代表 docx4j 实际没看到对象。",
                "",
            ]
        )
    lines.extend(
        [
            "| 对象 | 当前 Python | docx4j | 诊断含义 |",
            "| --- | ---: | ---: | --- |",
        ]
    )
    python_summary = data.get("python_summary", {})
    docx4j_summary = data.get("docx4j_summary", {})
    for key in INSPECTION_KEYS:
        lines.append(
            "| "
            + key
            + f" | {python_summary.get(key, 0)} | {docx4j_summary.get(key, 0)} | "
            + IMPACT_BY_KEY.get(key, "")
            + " |"
        )
    lines.extend(["", "## 需要关注的差异", ""])
    if report.get("comparison_status") == "not_run":
        lines.append("- docx4j 工具没有完成运行，本报告只保留当前 Python inspector 结果，不生成两边差异结论。")
    elif not count_diffs and not text_diffs.get("docx4j_only") and not text_diffs.get("python_only"):
        lines.append("- 当前没有数量或可见文本差异。")
    for diff in count_diffs:
        lines.append(
            "- "
            + f"`{diff['kind']}`：`{diff['category']}` 当前 Python={diff['python_count']}，"
            + f"docx4j={diff['docx4j_count']}。{diff['possible_gate_impact']}"
        )
    for diff in text_diffs.get("docx4j_only", []):
        lines.append(
            "- `docx4j_only_visible_text`：docx4j 看到当前 Python 未看到的文本，"
            + f"来源 `{diff.get('source_ref')}`，摘要：{diff.get('text_preview')}"
        )
    for diff in text_diffs.get("python_only", []):
        lines.append(
            "- `python_only_visible_text`：当前 Python 看到 docx4j 未看到的文本，"
            + f"来源 `{diff.get('source_ref')}`，摘要：{diff.get('text_preview')}"
        )
    lines.extend(
        [
            "",
            "## 门禁边界",
            "",
            "- 这个报告不能把 `UNKNOWN` 改成 `PASS`。",
            "- 如果 docx4j 看到更多可见对象，只能作为缺证据或待建模对象的诊断线索。",
            "- 要把任何 docx4j 字段纳入正式阶段产物，必须另行定义字段含义、生产者、消费者、缺失后果和测试。",
            "",
        ]
    )
    return "\n".join(lines)


def _count_differences(
    python_summary: dict[str, int],
    docx4j_summary: dict[str, int],
) -> list[dict[str, Any]]:
    diffs: list[dict[str, Any]] = []
    for key in INSPECTION_KEYS:
        python_count = python_summary.get(key, 0)
        docx4j_count = docx4j_summary.get(key, 0)
        if python_count == docx4j_count:
            continue
        kind = (
            "python_missing_docx4j_seen"
            if docx4j_count > python_count
            else "docx4j_missing_python_seen"
        )
        diffs.append(
            {
                "kind": kind,
                "category": key,
                "python_count": python_count,
                "docx4j_count": docx4j_count,
                "possible_gate_impact": IMPACT_BY_KEY.get(key, "需要人工判断影响范围"),
            }
        )
    return diffs


def _visible_text_differences(
    python_inspection: dict[str, Any],
    docx4j_inspection: dict[str, Any] | None,
) -> dict[str, list[dict[str, Any]]]:
    python_entries = _visible_text_entries(python_inspection)
    docx4j_entries = _visible_text_entries(docx4j_inspection or {})
    python_hashes = {entry["text_hash"] for entry in python_entries}
    docx4j_hashes = {entry["text_hash"] for entry in docx4j_entries}
    return {
        "docx4j_only": [
            _text_diff_entry(entry)
            for entry in docx4j_entries
            if entry["text_hash"] not in python_hashes
        ],
        "python_only": [
            _text_diff_entry(entry)
            for entry in python_entries
            if entry["text_hash"] not in docx4j_hashes
        ],
    }


def _visible_text_entries(inspection: dict[str, Any]) -> list[dict[str, Any]]:
    data = inspection.get("data", {}) if inspection else {}
    entries: list[dict[str, Any]] = []
    for key in ["paragraphs", "headers_footers", "footnotes", "text_boxes"]:
        for item in data.get(key, []):
            text = _normalized_text(item.get("text", ""))
            if text:
                entries.append(
                    {
                        "kind": key,
                        "text": text,
                        "text_hash": sha256_text(text),
                        "source_ref": item.get("source_ref", ""),
                    }
                )
    for table in data.get("tables", []):
        for cell in table.get("cells", []):
            text = _normalized_text(cell.get("text", ""))
            if text:
                entries.append(
                    {
                        "kind": "table_cell",
                        "text": text,
                        "text_hash": sha256_text(text),
                        "source_ref": cell.get("source_ref", table.get("source_ref", "")),
                    }
                )
    return entries


def _text_diff_entry(entry: dict[str, Any]) -> dict[str, Any]:
    text = entry.get("text", "")
    return {
        "kind": entry.get("kind"),
        "source_ref": entry.get("source_ref", ""),
        "text_hash": entry.get("text_hash"),
        "text_preview": text[:120],
    }


def _normalized_text(text: Any) -> str:
    return " ".join(str(text or "").split())


def _materialize_command(
    docx_path: Path,
    output_json: Path,
    *,
    command: list[str] | None,
    root: Path | None,
) -> list[str]:
    if command:
        replacements = {
            "{input_docx}": str(docx_path),
            "{output_json}": str(output_json),
        }
        if any(any(token in part for token in replacements) for part in command):
            return [
                _replace_tokens(part, replacements)
                for part in command
            ]
        return [*command, str(docx_path), "--out", str(output_json)]
    project_root = root or Path.cwd()
    script = project_root / "scripts" / "docx4j-inspector" / "run.sh"
    return ["bash", str(script), str(docx_path), "--out", str(output_json)]


def parse_command_option(command: str | None) -> list[str] | None:
    if command is None or not command.strip():
        return None
    return shlex.split(command)


def _replace_tokens(part: str, replacements: dict[str, str]) -> str:
    value = part
    for token, replacement in replacements.items():
        value = value.replace(token, replacement)
    return value


def _tool_result(
    status: str,
    invocation: list[str],
    *,
    started_at: str,
    returncode: int | None = None,
    stdout: str = "",
    stderr: str = "",
    error: str | None = None,
    inspection: dict[str, Any] | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "status": status,
        "command": invocation,
        "started_at": started_at,
        "finished_at": now_iso(),
        "returncode": returncode,
        "stdout_excerpt": stdout[-2000:] if stdout else "",
        "stderr_excerpt": stderr[-2000:] if stderr else "",
    }
    if error:
        result["error"] = error
    if inspection is not None:
        result["inspection"] = inspection
    return result
