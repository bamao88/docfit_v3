from __future__ import annotations

import ast
from pathlib import Path

from docfit.template_generation.agent import loop, observation_runtime, observation_stage


def _imports(module_path: Path) -> set[str]:
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    direct_imports = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    from_imports = {
        name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
        for name in {
            str(node.module or ""),
            ".".join(filter(None, (node.module, alias.name))),
            alias.name,
        }
    }
    return direct_imports | from_imports


def test_production_runtime_does_not_import_standalone_stage_debug() -> None:
    production_imports = _imports(Path(loop.__file__)) | _imports(
        Path(observation_runtime.__file__)
    )

    assert not any(name.endswith("observation_stage") for name in production_imports)


def test_t3_debug_fixture_is_marked_as_debug_only(tmp_path) -> None:
    result = observation_stage._publish_debug_t2_final(
        {
            "artifact_type": "unit_map",
            "units": [{"unit_id": "operator_selected_pages"}],
        },
        packet={"input_contract_hash": "sha256:l1"},
        source=tmp_path / "fixture.yaml",
    )

    assert result.payload["result_role"] == "final"
    assert result.payload["lineage"]["producer_mode"] == "debug_fixture"
