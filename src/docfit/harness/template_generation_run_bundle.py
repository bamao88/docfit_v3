from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from docfit.core.io import read_json, read_yaml, sha256_file
from docfit.core.models import Finding, make_finding
from docfit.core.status import Status, merge_statuses
from docfit.harness.template_generation_standard_quality import (
    TemplateGenerationStandardSet,
)
from docfit.template_generation.verifier import verify_t6_build_artifact


@dataclass(frozen=True)
class RunArtifactSpec:
    artifact_key: str
    stage_key: str | None
    stage_id: str | None
    top_level_name: str
    payload_type: str


RUN_ARTIFACT_SPECS = [
    RunArtifactSpec(
        "template_generation_request",
        None,
        None,
        "00_template_generation_request.json",
        "json",
    ),
    RunArtifactSpec(
        "document_facts",
        "t1_document_facts",
        "T1",
        "01_document_facts.json",
        "json",
    ),
    RunArtifactSpec(
        "template_generation_l1_input_contract",
        None,
        "L1",
        "01.5_l1_input_contract.json",
        "json",
    ),
    RunArtifactSpec(
        "unit_map",
        "t2_unit_pagination",
        "T2",
        "02_unit_map.yaml",
        "yaml",
    ),
    RunArtifactSpec(
        "element_spec",
        "t3_element_policy",
        "T3",
        "03_element_spec.yaml",
        "yaml",
    ),
    RunArtifactSpec(
        "global_spec",
        "t4_global_layout",
        "T4",
        "04_global_spec.yaml",
        "yaml",
    ),
    RunArtifactSpec(
        "template_spec",
        "t5_template_spec",
        "T5",
        "05_template_spec.yaml",
        "yaml",
    ),
    RunArtifactSpec(
        "fillable_template_docx",
        None,
        "T6",
        "06.1_fillable_template.docx",
        "binary",
    ),
    RunArtifactSpec(
        "build_manifest",
        None,
        "T6",
        "06.2_build_manifest.json",
        "json",
    ),
    RunArtifactSpec(
        "verification_report",
        None,
        "T7",
        "07_verification_report.json",
        "json",
    ),
]

STAGE_ARTIFACT_KEY = {
    spec.stage_key: spec.artifact_key
    for spec in RUN_ARTIFACT_SPECS
    if spec.stage_key is not None
}


@dataclass
class BoundArtifact:
    artifact_key: str
    stage_key: str | None
    stage_id: str | None
    path: Path | None
    sha256: str | None
    declared_sha256: str | None
    source_kind: str
    status: Status
    payload: dict[str, Any] | None = None
    hash_match: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_key": self.artifact_key,
            "stage_key": self.stage_key,
            "stage_id": self.stage_id,
            "path": str(self.path) if self.path is not None else None,
            "sha256": self.sha256,
            "declared_sha256": self.declared_sha256,
            "hash_match": self.hash_match,
            "source_kind": self.source_kind,
            "status": self.status.value,
        }


@dataclass
class TemplateGenerationRunBundle:
    source_run_id: str
    source_run_dir: Path
    source_run_dir_name: str
    status: Status
    manifest_source: str
    artifacts: dict[str, BoundArtifact] = field(default_factory=dict)
    findings: list[Finding] = field(default_factory=list)
    observed_t6_findings: list[Finding] = field(default_factory=list)

    def artifact_for_stage(self, stage_key: str) -> BoundArtifact | None:
        artifact_key = STAGE_ARTIFACT_KEY.get(stage_key)
        if artifact_key is None:
            return None
        return self.artifacts.get(artifact_key)

    def payload(self, artifact_key: str) -> dict[str, Any] | None:
        artifact = self.artifacts.get(artifact_key)
        return artifact.payload if artifact is not None else None

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_type": "template_generation_run_bundle",
            "artifact_version": "1.0",
            "source_run_id": self.source_run_id,
            "source_run_dir": str(self.source_run_dir),
            "source_run_dir_name": self.source_run_dir_name,
            "status": self.status.value,
            "manifest_source": self.manifest_source,
            "artifacts": {
                key: artifact.to_dict()
                for key, artifact in self.artifacts.items()
            },
            "findings": [finding.to_dict() for finding in self.findings],
            "observed_t6_findings": [
                finding.to_dict() for finding in self.observed_t6_findings
            ],
        }


def bind_template_generation_run_bundle(
    run_dir: Path,
    *,
    standard_set: TemplateGenerationStandardSet,
    source_run_id: str | None = None,
) -> TemplateGenerationRunBundle:
    run_dir = run_dir.resolve()
    findings: list[Finding] = []
    source_run_id = source_run_id or run_dir.name
    bundle = TemplateGenerationRunBundle(
        source_run_id=source_run_id,
        source_run_dir=run_dir,
        source_run_dir_name=run_dir.name,
        status=Status.UNKNOWN,
        manifest_source="filesystem_scan",
        findings=findings,
    )
    if not run_dir.is_dir():
        findings.append(
            _bundle_finding(
                len(findings) + 1,
                Status.UNKNOWN,
                "template_generation_run_dir_missing",
                "--run must point at an existing template-generate run directory",
                "existing directory",
                str(run_dir),
                bucket="run_bundle_missing",
            )
        )
        return bundle

    debug_index, declared_hashes, manifest_source = _load_declared_manifest(
        run_dir,
        findings,
    )
    bundle.manifest_source = manifest_source
    for spec in RUN_ARTIFACT_SPECS:
        artifact = _bind_artifact(run_dir, spec, declared_hashes, findings)
        bundle.artifacts[spec.artifact_key] = artifact

    _check_source_template_hash(bundle, standard_set, findings)
    _check_fillable_template_hash(bundle, findings)
    _check_observed_t6_effects(bundle, bundle.observed_t6_findings)
    blocking_statuses = [
        finding.status for finding in findings if finding.severity == "blocking"
    ]
    artifact_statuses = [artifact.status for artifact in bundle.artifacts.values()]
    bundle.status = merge_statuses(artifact_statuses + blocking_statuses)
    if debug_index is not None:
        bundle.manifest_source = "debug_index"
    return bundle


def _load_declared_manifest(
    run_dir: Path,
    findings: list[Finding],
) -> tuple[dict[str, Any] | None, dict[str, str], str]:
    index_path = run_dir / "99_template_generation_debug_index.json"
    if not index_path.exists():
        findings.append(
            _bundle_finding(
                len(findings) + 1,
                Status.UNKNOWN,
                "template_generation_run_bundle_missing_debug_index",
                "Run bundle has no debug index; falling back to filesystem scan",
                "99_template_generation_debug_index.json",
                "missing",
                bucket="run_bundle_manifest",
            )
        )
        return None, {}, "filesystem_scan"
    try:
        debug_index = read_json(index_path)
    except Exception as exc:
        findings.append(
            _bundle_finding(
                len(findings) + 1,
                Status.UNKNOWN,
                "template_generation_run_bundle_invalid_debug_index",
                "Run bundle debug index is not valid JSON",
                "valid JSON debug index",
                repr(exc),
                bucket="run_bundle_manifest",
            )
        )
        return None, {}, "filesystem_scan"

    declared_hashes: dict[str, str] = {}
    files = debug_index.get("files")
    if isinstance(files, list):
        for item in files:
            if not isinstance(item, dict):
                continue
            sha256 = item.get("sha256")
            name = item.get("name")
            path = item.get("path")
            if isinstance(sha256, str):
                if name:
                    declared_hashes[str(name)] = sha256
                if path:
                    declared_hashes[str(Path(str(path)).name)] = sha256
                    declared_hashes[str(path)] = sha256
    return debug_index, declared_hashes, "debug_index"


def _bind_artifact(
    run_dir: Path,
    spec: RunArtifactSpec,
    declared_hashes: dict[str, str],
    findings: list[Finding],
) -> BoundArtifact:
    top_level_path = run_dir / spec.top_level_name
    path: Path | None = None
    source_kind = "missing"
    if top_level_path.exists():
        path = top_level_path
        source_kind = "ordered_top_level"

    if path is None:
        findings.append(
            _bundle_finding(
                len(findings) + 1,
                Status.UNKNOWN,
                "template_generation_run_bundle_missing_artifact",
                f"Required run artifact {spec.artifact_key} is missing",
                spec.top_level_name,
                str(top_level_path),
                affected_ids=[spec.artifact_key],
                bucket="run_bundle_missing",
            )
        )
        return BoundArtifact(
            artifact_key=spec.artifact_key,
            stage_key=spec.stage_key,
            stage_id=spec.stage_id,
            path=None,
            sha256=None,
            declared_sha256=None,
            source_kind=source_kind,
            status=Status.UNKNOWN,
            payload=None,
            hash_match=None,
        )

    actual_sha256 = sha256_file(path)
    declared_sha256 = _declared_sha256_for(path, declared_hashes)
    hash_match = declared_sha256 is not None and declared_sha256 == actual_sha256
    status = Status.PASS if hash_match else Status.UNKNOWN
    if declared_sha256 is None:
        findings.append(
            _bundle_finding(
                len(findings) + 1,
                Status.UNKNOWN,
                "template_generation_run_bundle_declared_hash_missing",
                f"Required artifact {spec.artifact_key} has no declared hash",
                "sha256 declared in 99_template_generation_debug_index.json",
                "missing",
                evidence_refs=[str(path)],
                affected_ids=[spec.artifact_key],
                bucket="run_bundle_hash",
            )
        )
    elif not hash_match:
        findings.append(
            _bundle_finding(
                len(findings) + 1,
                Status.UNKNOWN,
                "template_generation_run_bundle_hash_mismatch",
                f"Declared hash for {spec.artifact_key} does not match actual file",
                declared_sha256,
                actual_sha256,
                evidence_refs=[str(path)],
                affected_ids=[spec.artifact_key],
                bucket="run_bundle_hash",
            )
        )

    payload: dict[str, Any] | None = None
    if spec.payload_type != "binary":
        try:
            loaded = read_json(path) if spec.payload_type == "json" else read_yaml(path)
            payload = loaded if isinstance(loaded, dict) else {}
        except Exception as exc:
            status = Status.UNKNOWN
            findings.append(
                _bundle_finding(
                    len(findings) + 1,
                    Status.UNKNOWN,
                    "template_generation_run_bundle_artifact_unreadable",
                    f"Run artifact {spec.artifact_key} cannot be parsed",
                    f"valid {spec.payload_type}",
                    repr(exc),
                    evidence_refs=[str(path)],
                    affected_ids=[spec.artifact_key],
                    bucket="run_bundle_invalid",
                )
            )

    return BoundArtifact(
        artifact_key=spec.artifact_key,
        stage_key=spec.stage_key,
        stage_id=spec.stage_id,
        path=path,
        sha256=actual_sha256,
        declared_sha256=declared_sha256,
        source_kind=source_kind,
        status=status,
        payload=payload,
        hash_match=hash_match,
    )


def _declared_sha256_for(path: Path, declared_hashes: dict[str, str]) -> str | None:
    return (
        declared_hashes.get(path.name)
        or declared_hashes.get(str(path))
        or declared_hashes.get(path.as_posix())
    )


def _check_observed_t6_effects(
    bundle: TemplateGenerationRunBundle,
    findings: list[Finding],
) -> None:
    template_spec = bundle.payload("template_spec")
    build_manifest = bundle.payload("build_manifest")
    fillable = bundle.artifacts.get("fillable_template_docx")
    if (
        not isinstance(template_spec, dict)
        or not isinstance(build_manifest, dict)
        or fillable is None
        or fillable.path is None
    ):
        return
    observed_findings = verify_t6_build_artifact(
        template_spec,
        build_manifest,
        fillable.path,
        start_index=len(findings) + 1,
    )
    findings.extend(observed_findings)


def _check_source_template_hash(
    bundle: TemplateGenerationRunBundle,
    standard_set: TemplateGenerationStandardSet,
    findings: list[Finding],
) -> None:
    request = bundle.payload("template_generation_request")
    if request is None:
        return
    actual = request.get("source_template_hash")
    expected = standard_set.source_template_docx_sha256
    if not expected:
        findings.append(
            _bundle_finding(
                len(findings) + 1,
                Status.UNKNOWN,
                "template_generation_run_bundle_standard_source_hash_missing",
                "Standard set does not expose a source template hash for run binding",
                "source.template_docx_sha256",
                "missing",
                bucket="standard_missing",
            )
        )
        return
    if actual != expected:
        findings.append(
            _bundle_finding(
                len(findings) + 1,
                Status.UNKNOWN,
                "template_generation_run_bundle_source_hash_mismatch",
                "Run request source hash does not match the standard source hash",
                expected,
                str(actual),
                affected_ids=[standard_set.school_id],
                bucket="run_bundle_source",
            )
        )


def _check_fillable_template_hash(
    bundle: TemplateGenerationRunBundle,
    findings: list[Finding],
) -> None:
    manifest = bundle.payload("build_manifest")
    fillable = bundle.artifacts.get("fillable_template_docx")
    if manifest is None or fillable is None or fillable.sha256 is None:
        return
    expected = manifest.get("output", {}).get("fillable_template_docx_hash")
    if not expected:
        findings.append(
            _bundle_finding(
                len(findings) + 1,
                Status.UNKNOWN,
                "template_generation_run_bundle_fillable_hash_missing",
                "Build manifest does not bind the fillable template hash",
                "output.fillable_template_docx_hash",
                "missing",
                evidence_refs=[str(fillable.path)] if fillable.path else [],
                bucket="run_bundle_hash",
            )
        )
        return
    if expected != fillable.sha256:
        findings.append(
            _bundle_finding(
                len(findings) + 1,
                Status.UNKNOWN,
                "template_generation_run_bundle_fillable_hash_mismatch",
                "Build manifest fillable hash does not match 06.1_fillable_template.docx",
                str(expected),
                fillable.sha256,
                evidence_refs=[str(fillable.path)] if fillable.path else [],
                affected_ids=["fillable_template_docx"],
                bucket="run_bundle_hash",
            )
        )


def _bundle_finding(
    index: int,
    status: Status,
    type_: str,
    message: str,
    expected: Any,
    actual: Any,
    *,
    evidence_refs: list[str] | None = None,
    affected_ids: list[str] | None = None,
    bucket: str,
    severity: str = "blocking",
) -> Finding:
    return make_finding(
        index,
        "template_generation_run_bundle",
        status,
        type_,
        message,
        _stringify(expected),
        _stringify(actual),
        evidence_refs=evidence_refs,
        affected_ids=affected_ids,
        root_cause_bucket=bucket,
        severity=severity,
    )


def _stringify(value: Any) -> str:
    if isinstance(value, str):
        return value
    return repr(value)
