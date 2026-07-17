from __future__ import annotations

import shutil
from pathlib import Path

from docfit.core.status import Status
from docfit.harness.standards import load_standard_bundle


ROOT = Path.cwd()


def test_unknown_when_standard_missing() -> None:
    bundle, findings = load_standard_bundle(ROOT, "missing-school")
    assert bundle is None
    assert findings[0].status == Status.UNKNOWN
    assert findings[0].type == "missing_signed_standard"


def test_school_standard_tree_contains_only_runnable_standards() -> None:
    version_dirs = [
        path
        for target_dir in (ROOT / "standards/targets").iterdir()
        if target_dir.is_dir()
        for path in target_dir.iterdir()
        if path.is_dir()
    ]

    assert version_dirs
    assert all((path / "target.standard.yaml").exists() for path in version_dirs)


def test_unknown_when_signed_standard_capability_profile_drifts(tmp_path) -> None:
    copied_target_root = tmp_path / "standards/targets/demo-school"
    copied_target_root.parent.mkdir(parents=True)
    shutil.copytree(ROOT / "standards/targets/demo-school", copied_target_root)
    shutil.copytree(ROOT / "standards/contracts", tmp_path / "standards/contracts")
    signed_standard = copied_target_root / "v1/target.standard.yaml"
    signed_standard.write_text(
        signed_standard.read_text(encoding="utf-8").replace(
            "  - content.visible_tables\n",
            "  - content.visible_text_blocks\n",
        ),
        encoding="utf-8",
    )

    _, findings = load_standard_bundle(tmp_path, "demo-school")

    assert any(finding.status == Status.UNKNOWN for finding in findings)
    assert any(finding.type == "coverage_requirements_drift" for finding in findings)
