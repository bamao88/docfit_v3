from __future__ import annotations

import argparse
import platform
import subprocess
import sys
import tempfile
from pathlib import Path

from docfit.core.io import write_json
from docfit.harness.profiles import REAL_CORE_PROFILE, get_eval_cases_for_profile
from docfit.harness.word_evidence import build_word_image_evidence_manifest


WORD_EXPORT_SCRIPT = """
on run argv
set inputPath to item 1 of argv
set outputPath to item 2 of argv
set timeoutSeconds to (item 3 of argv) as integer
with timeout of timeoutSeconds seconds
 tell application "Microsoft Word"
  open file name inputPath
  set docRef to active document
  save as docRef file name outputPath file format format PDF
  close docRef saving no
 end tell
end timeout
end run
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Export real-core-v0 rendered DOCX files to Word image evidence."
    )
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--reports-root", type=Path, default=Path("reports/real-core-v0"))
    parser.add_argument("--case", action="append", dest="case_ids", default=[])
    parser.add_argument("--dpi", type=int, default=150)
    parser.add_argument("--word-timeout", type=int, default=600)
    parser.add_argument("--keep-pdf", action="store_true")
    args = parser.parse_args(argv)

    root = args.root.resolve()
    reports_root = _resolve(root, args.reports_root)
    cases = [
        case
        for case in get_eval_cases_for_profile(REAL_CORE_PROFILE.profile_id)
        if case.stage == "e2e"
    ]
    if args.case_ids:
        requested = set(args.case_ids)
        cases = [case for case in cases if case.case_id in requested]
        unknown = sorted(requested - {case.case_id for case in cases})
        if unknown:
            print("unknown case id(s): " + ", ".join(unknown), file=sys.stderr)
            return 2

    missing = [
        reports_root / case.case_id / "final.docx"
        for case in cases
        if not (reports_root / case.case_id / "final.docx").exists()
    ]
    if missing:
        print("missing rendered final.docx files:", file=sys.stderr)
        for path in missing:
            print(f"- {path}", file=sys.stderr)
        return 2

    word_version = _word_version()
    exported: list[Path] = []
    with tempfile.TemporaryDirectory(prefix="docfit-word-evidence-") as temp_dir:
        temp_root = Path(temp_dir)
        for case in cases:
            final_docx = reports_root / case.case_id / "final.docx"
            evidence_dir = reports_root / case.case_id / "evidence"
            evidence_dir.mkdir(parents=True, exist_ok=True)
            pdf_path = temp_root / f"{case.case_id}.word.pdf"
            _clean_previous_exports(evidence_dir, keep_pdf=args.keep_pdf)
            _export_pdf_with_word(final_docx, pdf_path, timeout_seconds=args.word_timeout)
            if args.keep_pdf:
                kept_pdf = evidence_dir / "final.word.pdf"
                kept_pdf.write_bytes(pdf_path.read_bytes())
            image_paths = _render_pdf_pages(pdf_path, evidence_dir, dpi=args.dpi)
            manifest = build_word_image_evidence_manifest(
                case_id=case.case_id,
                school_id=case.school_id,
                student_id=case.student_id or "",
                final_docx=final_docx,
                image_paths=image_paths,
                word_application="Microsoft Word",
                word_version=word_version,
                platform=platform.platform(),
                export_method=(
                    "Microsoft Word SaveAs PDF via AppleScript; "
                    f"pdftoppm PNG render at {args.dpi} DPI"
                ),
                open_repair_warnings=[],
            )
            manifest_path = evidence_dir / "word_image_evidence.json"
            write_json(manifest_path, manifest)
            exported.append(manifest_path)
            print(f"exported {case.case_id}: {len(image_paths)} page image(s)")

    print(f"wrote {len(exported)} Word image evidence manifest(s)")
    return 0


def _resolve(root: Path, path: Path) -> Path:
    return path if path.is_absolute() else root / path


def _word_version() -> str:
    completed = subprocess.run(
        ["osascript", "-e", 'tell application "Microsoft Word" to get version'],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _clean_previous_exports(evidence_dir: Path, *, keep_pdf: bool) -> None:
    for path in evidence_dir.glob("page-*.png"):
        path.unlink()
    manifest = evidence_dir / "word_image_evidence.json"
    manifest.unlink(missing_ok=True)
    if not keep_pdf:
        (evidence_dir / "final.word.pdf").unlink(missing_ok=True)


def _export_pdf_with_word(final_docx: Path, pdf_path: Path, *, timeout_seconds: int) -> None:
    subprocess.run(
        [
            "osascript",
            "-e",
            WORD_EXPORT_SCRIPT,
            str(final_docx.resolve()),
            str(pdf_path.resolve()),
            str(timeout_seconds),
        ],
        check=True,
        timeout=timeout_seconds + 30,
    )


def _render_pdf_pages(pdf_path: Path, evidence_dir: Path, *, dpi: int) -> list[Path]:
    output_prefix = evidence_dir / "page"
    subprocess.run(
        [
            "pdftoppm",
            "-png",
            "-r",
            str(dpi),
            str(pdf_path),
            str(output_prefix),
        ],
        check=True,
    )
    image_paths = sorted(
        evidence_dir.glob("page-*.png"),
        key=lambda path: int(path.stem.rsplit("-", 1)[1]),
    )
    if not image_paths:
        raise RuntimeError(f"pdftoppm produced no images for {pdf_path}")
    return image_paths


if __name__ == "__main__":
    raise SystemExit(main())
