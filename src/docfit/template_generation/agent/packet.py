from __future__ import annotations

from collections import defaultdict
import html
from pathlib import Path
import re
import shutil
import struct
import subprocess
import xml.etree.ElementTree as ET
from typing import Any

from docfit.core.io import now_iso, read_json, sha256_file, sha256_json
from docfit.template_generation.constants import UNIT_DEFINITIONS


def load_render_packet(path: Path) -> dict[str, Any]:
    packet = read_json(path)
    if not isinstance(packet, dict):
        raise ValueError(f"agent render packet must be a JSON object: {path}")
    return packet


def build_template_agent_render_packet(
    *,
    document_facts: dict[str, Any],
    structure_candidates: dict[str, Any],
    source_template_docx: Path | None = None,
    render_artifacts_dir: Path | None = None,
) -> dict[str, Any]:
    render = _build_real_render_artifacts(
        source_template_docx=source_template_docx,
        render_artifacts_dir=render_artifacts_dir,
        document_facts=document_facts,
    )
    page_text_index = _page_text_index(document_facts, render=render)
    page_layout_index = _page_layout_index(page_text_index)
    page_summary = _page_index_summary(page_text_index)
    render_hash = sha256_json(
        {
            "source_template_hash": document_facts.get("metadata", {}).get(
                "source_template_hash"
            ),
            "render_status": render["render_status"],
            "render_artifacts": render["render_artifacts"],
            "page_text_index": page_text_index,
            "page_layout_index": page_layout_index,
        }
    )
    render_artifacts = {
        **render["render_artifacts"],
        "render_hash": render_hash,
    }
    return {
        "artifact_type": "template_agent_render_packet",
        "artifact_version": "1.0",
        "created_at": now_iso(),
        "source_template_docx": str(source_template_docx) if source_template_docx else None,
        "render_status": render["render_status"],
        "source_render_hash": render_hash,
        "status_authority": "verify_template_parse_build",
        "advisory_only": True,
        "allowed_ai_tasks": [
            "submit_t2_structure_proposals",
            "submit_t3_element_policy_proposals",
            "submit_t4_layout_hints",
            "abstain",
        ],
        "forbidden_ai_tasks": [
            "write_document_facts",
            "write_unit_map",
            "write_element_spec",
            "write_global_spec",
            "write_template_spec",
            "write_generation_plan",
            "write_build_manifest",
            "set_verification_status",
            "read_standards_targets",
        ],
        "render_artifacts": render_artifacts,
        "page_text_index": page_text_index,
        "page_layout_index": page_layout_index,
        "input_windows": {
            "full_pass": {
                "page_thumbnails": render_artifacts.get("clean_page_images", []),
                "page_index_summary": page_summary,
            },
            "focused_pass": [],
        },
        "optional_reference": {
            "canonical_unit_ids": [
                {"unit_id": unit_id, "name": name}
                for unit_id, name, _aliases in UNIT_DEFINITIONS
            ],
            "non_binding": True,
        },
        "global_layout_facts": _global_layout_facts(document_facts),
        "round0_snapshot_id": sha256_json(
            {
                "template_structure_candidates": sha256_json(structure_candidates),
            }
        ),
    }


# T4 确定性全局版式事实（白名单投影，仅事实字段，供 Track A）。
_SECTION_FACT_FIELDS = ("page_margins", "page_size", "page_numbering")
_HEADER_FOOTER_REF_FIELDS = ("kind", "type", "part_name", "source_ref")
_FIELD_FACT_FIELDS = (
    "index",
    "kind",
    "field_type",
    "instruction",
    "part_name",
    "paragraph_index",
    "end_paragraph_index",
    "source_ref",
)
_BREAK_FACT_FIELDS = ("index", "kind", "paragraph_index", "type", "source_ref")


def _global_layout_facts(document_facts: dict[str, Any]) -> dict[str, Any]:
    data = document_facts.get("data", {}) or {}
    sections = []
    for section in data.get("sections", []) or []:
        if not isinstance(section, dict):
            continue
        projected: dict[str, Any] = {
            field: section.get(field) for field in _SECTION_FACT_FIELDS if section.get(field) is not None
        }
        projected["index"] = section.get("index")
        projected["references"] = [
            {field: ref.get(field) for field in _HEADER_FOOTER_REF_FIELDS if ref.get(field) is not None}
            for ref in section.get("references", []) or []
            if isinstance(ref, dict)
        ]
        projected["effective_references"] = [
            {field: ref.get(field) for field in _HEADER_FOOTER_REF_FIELDS if ref.get(field) is not None}
            for ref in section.get("effective_references", []) or []
            if isinstance(ref, dict)
        ]
        sections.append(projected)
    header_footer = [
        {
            "kind": hf.get("kind"),
            "part_name": hf.get("part_name"),
            "has_content": bool((hf.get("text") or "").strip() or hf.get("paragraphs")),
            "text": hf.get("text") or "",
            "paragraphs": [
                {
                    "index": paragraph.get("index"),
                    "text": paragraph.get("text") or "",
                    "source_ref": paragraph.get("source_ref"),
                }
                for paragraph in hf.get("paragraphs", []) or []
                if isinstance(paragraph, dict)
            ],
            "source_ref": hf.get("source_ref"),
        }
        for hf in data.get("headers_footers", []) or []
        if isinstance(hf, dict)
    ]
    fields = [
        {
            field: item.get(field)
            for field in _FIELD_FACT_FIELDS
            if item.get(field) is not None
        }
        for item in data.get("fields", []) or []
        if isinstance(item, dict)
    ]
    breaks = [
        {
            field: item.get(field)
            for field in _BREAK_FACT_FIELDS
            if item.get(field) is not None
        }
        for item in data.get("breaks", []) or []
        if isinstance(item, dict)
    ]
    return {
        "sections": sections,
        "header_footer": header_footer,
        "fields": fields,
        "breaks": breaks,
        "numbering_definition_count": len(data.get("numbering_definitions", []) or []),
    }


def packet_source_seq_set(packet: dict[str, Any]) -> set[int]:
    values: set[int] = set()
    for item in packet.get("page_text_index", []):
        source_seq = _int_or_none(item.get("source_seq"))
        if source_seq is not None:
            values.add(source_seq)
    return values


def packet_render_target_set(packet: dict[str, Any]) -> set[str]:
    targets: set[str] = set()
    for collection_name in ("page_text_index", "page_layout_index"):
        for item in packet.get(collection_name, []):
            target = str(item.get("render_target_id") or "")
            if target:
                targets.add(target)
    return targets


def packet_page_set(packet: dict[str, Any]) -> set[int]:
    pages: set[int] = set()
    for item in packet.get("page_text_index", []):
        page_no = _int_or_none(item.get("page_no"))
        if page_no is not None:
            pages.add(page_no)
    return pages or {1}


def _page_text_index(
    document_facts: dict[str, Any],
    *,
    render: dict[str, Any],
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    bindings = render.get("source_bindings", {})
    for index, entry in enumerate(document_facts.get("body_flow", []), start=1):
        source_seq = _int_or_none(entry.get("source_seq"))
        if source_seq is None:
            continue
        binding = bindings.get(source_seq, {})
        page_no = (
            _int_or_none(binding.get("page_no"))
            or _int_or_none(entry.get("page_no"))
            or 1
        )
        source_ref = str(entry.get("source_ref") or "")
        items.append(
            {
                "source_seq": source_seq,
                "source_ref": source_ref,
                "node_id": entry.get("node_id"),
                "part_name": entry.get("part_name"),
                "order": entry.get("order", index),
                "flow_item_type": entry.get("flow_item_type"),
                "kind": entry.get("kind"),
                "paragraph_id": entry.get("paragraph_id"),
                "table_id": entry.get("table_id"),
                "cell_id": entry.get("cell_id"),
                "container_ref": entry.get("container_ref"),
                "text": entry.get("text", ""),
                "style": entry.get("style"),
                "style_details": entry.get("style_details", {}),
                "text_facts": entry.get("text_facts", {}),
                "raw_run_ids": entry.get("raw_run_ids", []),
                "logical_run_ids": entry.get("logical_run_ids", []),
                "page_no": page_no,
                "bbox": binding.get("bbox") or entry.get("bbox"),
                "render_binding_status": binding.get(
                    "binding_status",
                    "projection_fallback",
                ),
                "render_target_id": f"source_seq:{source_seq}",
            }
        )
    return sorted(items, key=lambda item: int(item["source_seq"]))


def _page_layout_index(page_text_index: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_page_position: dict[int, int] = defaultdict(int)
    result: list[dict[str, Any]] = []
    for item in page_text_index:
        page_no = int(item.get("page_no") or 1)
        by_page_position[page_no] += 1
        result.append(
            {
                "page_no": page_no,
                "source_seq": item.get("source_seq"),
                "source_ref": item.get("source_ref"),
                "bbox": item.get("bbox"),
                "page_top_ratio": _page_top_ratio(item.get("bbox")),
                "tier": by_page_position[page_no],
                "render_target_id": item.get("render_target_id"),
                "render_binding_status": item.get("render_binding_status"),
            }
        )
    return result


def _page_index_summary(page_text_index: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts: dict[int, int] = defaultdict(int)
    for item in page_text_index:
        counts[int(item.get("page_no") or 1)] += 1
    return [
        {"page_no": page_no, "text_items": counts[page_no]}
        for page_no in sorted(counts)
    ]


def _int_or_none(value: Any) -> int | None:
    try:
        if value is None or value == "":
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _build_real_render_artifacts(
    *,
    source_template_docx: Path | None,
    render_artifacts_dir: Path | None,
    document_facts: dict[str, Any],
) -> dict[str, Any]:
    fallback = _projection_render_artifacts()
    if source_template_docx is None or render_artifacts_dir is None:
        return fallback
    if not source_template_docx.exists():
        return {
            **fallback,
            "render_artifacts": {
                **fallback["render_artifacts"],
                "render_error": f"source template does not exist: {source_template_docx}",
            },
        }
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    pdftoppm = shutil.which("pdftoppm")
    pdftotext = shutil.which("pdftotext")
    if soffice is None or pdftoppm is None or pdftotext is None:
        missing = [
            name
            for name, path in (
                ("soffice", soffice),
                ("pdftoppm", pdftoppm),
                ("pdftotext", pdftotext),
            )
            if path is None
        ]
        return {
            **fallback,
            "render_artifacts": {
                **fallback["render_artifacts"],
                "render_error": "missing render command(s): " + ", ".join(missing),
            },
        }

    render_artifacts_dir.mkdir(parents=True, exist_ok=True)
    pdf_dir = render_artifacts_dir / "pdf"
    image_dir = render_artifacts_dir / "pages"
    annotated_dir = render_artifacts_dir / "annotated"
    pdf_dir.mkdir(parents=True, exist_ok=True)
    image_dir.mkdir(parents=True, exist_ok=True)
    annotated_dir.mkdir(parents=True, exist_ok=True)
    for path in [*image_dir.glob("page-*.png"), *annotated_dir.glob("page-*.svg")]:
        path.unlink()

    try:
        pdf_path = _convert_docx_to_pdf(source_template_docx, pdf_dir, soffice=soffice)
        clean_images = _render_pdf_pages(pdf_path, image_dir, pdftoppm=pdftoppm)
        pdf_layout = _extract_pdf_layout(pdf_path, pdftotext=pdftotext)
        source_bindings = _bind_source_entries_to_pdf_layout(
            document_facts=document_facts,
            pdf_layout=pdf_layout,
        )
        annotated_images = _write_annotated_page_svgs(
            clean_images=clean_images,
            annotated_dir=annotated_dir,
            pdf_layout=pdf_layout,
            source_bindings=source_bindings,
        )
    except (OSError, RuntimeError, subprocess.SubprocessError, ET.ParseError) as exc:
        return {
            **fallback,
            "render_artifacts": {
                **fallback["render_artifacts"],
                "render_error": f"{type(exc).__name__}: {exc}",
            },
        }

    binding_counts = defaultdict(int)
    for binding in source_bindings.values():
        binding_counts[str(binding.get("binding_status") or "unknown")] += 1
    return {
        "render_status": "real_render",
        "source_bindings": source_bindings,
        "render_artifacts": {
            "render_status": "real_render",
            "clean_page_images": clean_images,
            "annotated_page_images": annotated_images,
            "render_engine": "libreoffice-pdf-poppler",
            "render_version": "1.0",
            "pdf_path": str(pdf_path),
            "pdf_sha256": sha256_file(pdf_path),
            "page_count": len(clean_images),
            "text_binding_summary": dict(sorted(binding_counts.items())),
        },
    }


def _projection_render_artifacts() -> dict[str, Any]:
    return {
        "render_status": "projection_fallback",
        "source_bindings": {},
        "render_artifacts": {
            "render_status": "projection_fallback",
            "clean_page_images": [],
            "annotated_page_images": [],
            "render_engine": "docfit-source-facts-projection",
            "render_version": "1.0",
        },
    }


def _convert_docx_to_pdf(source_template_docx: Path, pdf_dir: Path, *, soffice: str) -> Path:
    pdf_path = pdf_dir / f"{source_template_docx.stem}.pdf"
    pdf_path.unlink(missing_ok=True)
    subprocess.run(
        [
            soffice,
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            str(pdf_dir),
            str(source_template_docx),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=90,
    )
    if not pdf_path.exists():
        produced = sorted(pdf_dir.glob("*.pdf"))
        if len(produced) == 1:
            return produced[0]
        raise RuntimeError(f"LibreOffice did not produce expected PDF: {pdf_path}")
    return pdf_path


def _render_pdf_pages(pdf_path: Path, image_dir: Path, *, pdftoppm: str) -> list[dict[str, Any]]:
    subprocess.run(
        [
            pdftoppm,
            "-png",
            "-r",
            "110",
            str(pdf_path),
            str(image_dir / "page"),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=90,
    )
    image_paths = sorted(
        image_dir.glob("page-*.png"),
        key=lambda path: int(path.stem.rsplit("-", 1)[1]),
    )
    if not image_paths:
        raise RuntimeError(f"pdftoppm produced no images for {pdf_path}")
    images: list[dict[str, Any]] = []
    for page_no, path in enumerate(image_paths, start=1):
        width, height = _png_size(path)
        images.append(
            {
                "page_no": page_no,
                "path": str(path),
                "sha256": sha256_file(path),
                "width_px": width,
                "height_px": height,
                "image_type": "png",
            }
        )
    return images


def _extract_pdf_layout(pdf_path: Path, *, pdftotext: str) -> dict[str, Any]:
    bbox_path = pdf_path.with_suffix(".bbox.html")
    bbox_path.unlink(missing_ok=True)
    subprocess.run(
        [
            pdftotext,
            "-bbox-layout",
            "-enc",
            "UTF-8",
            str(pdf_path),
            str(bbox_path),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=90,
    )
    root = ET.fromstring(bbox_path.read_text(encoding="utf-8"))
    pages: list[dict[str, Any]] = []
    global_chars: list[str] = []
    global_words: list[dict[str, Any]] = []
    for page_no, page in enumerate(root.findall(".//{*}page"), start=1):
        width = float(page.attrib.get("width") or 0)
        height = float(page.attrib.get("height") or 0)
        page_chars: list[str] = []
        page_words: list[dict[str, Any]] = []
        for word in page.findall(".//{*}word"):
            text = _normalize_render_text(word.text or "")
            if not text:
                continue
            start = len(global_chars)
            page_start = len(page_chars)
            global_chars.extend(text)
            page_chars.extend(text)
            bbox = {
                "x_min": float(word.attrib.get("xMin") or 0),
                "y_min": float(word.attrib.get("yMin") or 0),
                "x_max": float(word.attrib.get("xMax") or 0),
                "y_max": float(word.attrib.get("yMax") or 0),
                "page_width": width,
                "page_height": height,
                "unit": "pt",
            }
            item = {
                "page_no": page_no,
                "text": text,
                "start": start,
                "end": start + len(text),
                "page_start": page_start,
                "page_end": page_start + len(text),
                "bbox": bbox,
            }
            global_words.append(item)
            page_words.append(item)
        pages.append(
            {
                "page_no": page_no,
                "width": width,
                "height": height,
                "text": "".join(page_chars),
                "words": page_words,
            }
        )
    return {
        "pages": pages,
        "text": "".join(global_chars),
        "words": global_words,
    }


def _bind_source_entries_to_pdf_layout(
    *,
    document_facts: dict[str, Any],
    pdf_layout: dict[str, Any],
) -> dict[int, dict[str, Any]]:
    bindings: dict[int, dict[str, Any]] = {}
    cursor = 0
    for entry in document_facts.get("body_flow", []):
        source_seq = _int_or_none(entry.get("source_seq"))
        if source_seq is None:
            continue
        text = _normalize_render_text(str(entry.get("text") or ""))
        if not text:
            bindings[source_seq] = {"binding_status": "empty_text"}
            continue
        match = _find_entry_match(pdf_layout, text, cursor)
        if match is None:
            bindings[source_seq] = {"binding_status": "ambiguous"}
            continue
        cursor = max(cursor, int(match["end"]))
        bindings[source_seq] = {
            "binding_status": match["binding_status"],
            "page_no": match["page_no"],
            "bbox": match["bbox"],
        }
    return bindings


def _find_entry_match(
    pdf_layout: dict[str, Any],
    text: str,
    cursor: int,
) -> dict[str, Any] | None:
    full_text = str(pdf_layout.get("text") or "")
    needles = [(text, "exact")]
    if len(text) > 40:
        needles.append((text[:40], "prefix"))
    if len(text) > 24:
        needles.append((text[:24], "prefix"))
    for needle, status in needles:
        if len(needle) < 2:
            continue
        index = full_text.find(needle, cursor)
        if index < 0 and status == "exact":
            index = full_text.find(needle)
        if index < 0:
            continue
        end = index + len(needle)
        bbox_words = [
            word
            for word in pdf_layout.get("words", [])
            if int(word.get("start", 0)) < end and int(word.get("end", 0)) > index
        ]
        if not bbox_words:
            continue
        page_no = int(bbox_words[0]["page_no"])
        page_words = [word for word in bbox_words if int(word["page_no"]) == page_no]
        return {
            "binding_status": status,
            "page_no": page_no,
            "bbox": _union_bbox([word["bbox"] for word in page_words]),
            "start": index,
            "end": end,
        }
    return None


def _write_annotated_page_svgs(
    *,
    clean_images: list[dict[str, Any]],
    annotated_dir: Path,
    pdf_layout: dict[str, Any],
    source_bindings: dict[int, dict[str, Any]],
) -> list[dict[str, Any]]:
    by_page: dict[int, list[tuple[int, dict[str, Any]]]] = defaultdict(list)
    for source_seq, binding in source_bindings.items():
        bbox = binding.get("bbox")
        page_no = _int_or_none(binding.get("page_no"))
        if page_no is not None and isinstance(bbox, dict):
            by_page[page_no].append((source_seq, bbox))
    pages = {int(page["page_no"]): page for page in pdf_layout.get("pages", [])}
    annotated: list[dict[str, Any]] = []
    for image in clean_images:
        page_no = int(image["page_no"])
        page = pages.get(page_no, {})
        page_width = float(page.get("width") or 1)
        page_height = float(page.get("height") or 1)
        width_px = int(image.get("width_px") or 1)
        height_px = int(image.get("height_px") or 1)
        image_path = str(image["path"])
        svg_path = annotated_dir / f"page-{page_no}.svg"
        overlays = []
        for source_seq, bbox in by_page.get(page_no, [])[:200]:
            x = float(bbox["x_min"]) / page_width * width_px
            y = float(bbox["y_min"]) / page_height * height_px
            w = max(1.0, (float(bbox["x_max"]) - float(bbox["x_min"])) / page_width * width_px)
            h = max(1.0, (float(bbox["y_max"]) - float(bbox["y_min"])) / page_height * height_px)
            overlays.append(
                f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" '
                'fill="none" stroke="#d12d2d" stroke-width="1.2"/>'
            )
            overlays.append(
                f'<text x="{x:.2f}" y="{max(10, y - 3):.2f}" '
                'font-size="9" fill="#d12d2d">'
                f'{html.escape(str(source_seq))}</text>'
            )
        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width_px}" height="{height_px}" '
            f'viewBox="0 0 {width_px} {height_px}">\n'
            f'  <image href="{html.escape(image_path)}" x="0" y="0" '
            f'width="{width_px}" height="{height_px}"/>\n'
            + "\n".join(f"  {item}" for item in overlays)
            + "\n</svg>\n"
        )
        svg_path.write_text(svg, encoding="utf-8")
        annotated.append(
            {
                "page_no": page_no,
                "path": str(svg_path),
                "sha256": sha256_file(svg_path),
                "width_px": width_px,
                "height_px": height_px,
                "image_type": "svg",
                "annotation": "source_seq_bbox_overlay",
            }
        )
    return annotated


def _normalize_render_text(text: str) -> str:
    return re.sub(r"\s+", "", text or "")


def _union_bbox(values: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "x_min": min(float(value["x_min"]) for value in values),
        "y_min": min(float(value["y_min"]) for value in values),
        "x_max": max(float(value["x_max"]) for value in values),
        "y_max": max(float(value["y_max"]) for value in values),
        "page_width": float(values[0].get("page_width") or 0),
        "page_height": float(values[0].get("page_height") or 0),
        "unit": values[0].get("unit") or "pt",
    }


def _page_top_ratio(bbox: Any) -> float | None:
    if not isinstance(bbox, dict):
        return None
    page_height = float(bbox.get("page_height") or 0)
    if page_height <= 0:
        return None
    return float(bbox.get("y_min") or 0) / page_height


def _png_size(path: Path) -> tuple[int, int]:
    with path.open("rb") as handle:
        header = handle.read(24)
    if len(header) < 24 or header[:8] != b"\x89PNG\r\n\x1a\n":
        return 0, 0
    return struct.unpack(">II", header[16:24])
