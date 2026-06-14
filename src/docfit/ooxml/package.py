from __future__ import annotations

from pathlib import Path
from zipfile import BadZipFile, ZipFile


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
