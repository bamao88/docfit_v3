from __future__ import annotations

from pathlib import Path
from posixpath import normpath
import xml.etree.ElementTree as ET
from zipfile import BadZipFile, ZipFile

from docfit.core.io import sha256_bytes


REL_NS = "{http://schemas.openxmlformats.org/package/2006/relationships}"
R_NS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
A_NS = "{http://schemas.openxmlformats.org/drawingml/2006/main}"


def is_valid_docx(path: Path) -> bool:
    try:
        with ZipFile(path) as package:
            names = set(package.namelist())
    except (BadZipFile, FileNotFoundError):
        return False
    return "[Content_Types].xml" in names and "word/document.xml" in names


def read_document_xml(path: Path) -> str:
    with ZipFile(path) as package:
        return package.read("word/document.xml").decode("utf-8", errors="replace")


def read_document_relationships(path: Path) -> dict[str, str]:
    try:
        with ZipFile(path) as package:
            raw = package.read("word/_rels/document.xml.rels")
    except KeyError:
        return {}
    root = ET.fromstring(raw)
    relationships: dict[str, str] = {}
    for relationship in root.findall(f"{REL_NS}Relationship"):
        rel_id = relationship.attrib.get("Id")
        target = relationship.attrib.get("Target")
        if rel_id and target:
            relationships[rel_id] = _word_target_path(target)
    return relationships


def image_refs_for_xml_element(
    element,
    relationships: dict[str, str],
) -> list[dict[str, str]]:
    refs: list[dict[str, str]] = []
    for index, blip in enumerate(element.iter(f"{A_NS}blip"), start=1):
        rel_id = blip.attrib.get(f"{R_NS}embed") or blip.attrib.get(f"{R_NS}link")
        if not rel_id:
            continue
        target = relationships.get(rel_id)
        if not target:
            continue
        refs.append(
            {
                "relationship_id": rel_id,
                "target": target,
                "source_ref": f"word/document.xml:drawing[{index}]",
            }
        )
    return refs


def read_docx_part(path: Path, part_name: str) -> bytes:
    with ZipFile(path) as package:
        return package.read(part_name)


def docx_part_sha256(path: Path, part_name: str) -> str:
    return sha256_bytes(read_docx_part(path, part_name))


def detect_unsupported_visible_objects(path: Path) -> list[dict[str, str]]:
    xml = read_document_xml(path)
    unsupported: list[dict[str, str]] = []
    if "txbxContent" in xml or "<v:textbox" in xml or "wps:txbx" in xml:
        unsupported.append(
            {
                "content_id": "u_textbox_001",
                "kind": "unsupported_visible_object",
                "object_type": "text_box",
                "source_ref": "word/document.xml:textbox[1]",
                "reason": "text box extraction not implemented",
                "blocking": True,
            }
        )
    if "w:footnoteReference" in xml:
        unsupported.append(
            {
                "content_id": "u_footnote_001",
                "kind": "unsupported_visible_object",
                "object_type": "footnote",
                "source_ref": "word/document.xml:footnoteReference[1]",
                "reason": "footnote extraction not implemented",
                "blocking": True,
            }
        )
    if "pic:pic" in xml or "<a:blip" in xml:
        unsupported.append(
            {
                "content_id": "u_image_001",
                "kind": "unsupported_visible_object",
                "object_type": "image",
                "source_ref": "word/document.xml:drawing[1]",
                "reason": "image extraction not implemented in bootstrap",
                "blocking": True,
            }
        )
    return unsupported


def _word_target_path(target: str) -> str:
    if target.startswith("/"):
        return normpath(target.lstrip("/"))
    return normpath("word/" + target)
