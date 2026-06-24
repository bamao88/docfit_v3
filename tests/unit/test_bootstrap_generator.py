from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


def _load_generator():
    module_path = Path("scripts/create_bootstrap_fixtures.py")
    spec = importlib.util.spec_from_file_location("create_bootstrap_fixtures", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_bootstrap_generator_defaults_to_generated_output(tmp_path, monkeypatch) -> None:
    generator = _load_generator()
    monkeypatch.setattr(generator, "ROOT", tmp_path)

    generator.main([])

    assert (tmp_path / "runs/workbench/bootstrap-fixtures/inputs/targets/demo-school/raw/source_template.docx").exists()
    assert (
        tmp_path
        / "runs/workbench/bootstrap-fixtures/standards/cases/demo-school__bootstrap-demo/v1/render/feature_snapshot.expected.json"
    ).exists()
    assert not (tmp_path / "standards/targets/demo-school/v1/target.standard.yaml").exists()


def test_bootstrap_generator_requires_explicit_reviewed_asset_overwrite(tmp_path, monkeypatch) -> None:
    generator = _load_generator()
    monkeypatch.setattr(generator, "ROOT", tmp_path)

    with pytest.raises(SystemExit):
        generator.main(["--root", str(tmp_path)])

    assert not (tmp_path / "standards/targets/demo-school/v1/target.standard.yaml").exists()
