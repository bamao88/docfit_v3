from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from docfit.core.io import sha256_file
from docfit.core.models import Finding, make_finding
from docfit.core.status import Status
from docfit.harness.coverage import validate_standard_coverage_requirements


REQUIRED_CONTRACT_FIELDS = {
    "contract_type",
    "contract_version",
    "owner",
    "required_invariants",
    "required_capabilities",
    "unsupported_policy",
    "coverage_requirements",
    "verifier_refs",
}


@dataclass
class StandardBundle:
    school_id: str
    template_version: str
    school_dir: Path
    signed_standard_path: Path
    signed_standard: dict[str, Any]
    contracts: dict[str, dict[str, Any]]
    contract_paths: dict[str, Path]

    @property
    def template_docx(self) -> Path:
        source = self.signed_standard["source"]["template_docx"]
        return (self.school_dir.parents[3] / source).resolve()

    @property
    def golden_feature_snapshot(self) -> Path:
        golden_ref = self.signed_standard.get("goldens", {}).get("feature_snapshot")
        if not golden_ref:
            return self.school_dir / "golden" / "feature_snapshot.json"
        return (self.school_dir / golden_ref).resolve()


def _load_yaml(path: Path) -> dict[str, Any]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    return loaded or {}


def load_standard_bundle(
    root: Path,
    school_id: str,
    template_version: str = "v1",
    *,
    finding_stage: str = "standards",
) -> tuple[StandardBundle | None, list[Finding]]:
    school_dir = root / "standards" / "targets" / school_id / template_version
    signed_standard_path = school_dir / "target.standard.yaml"
    findings: list[Finding] = []
    if not signed_standard_path.exists():
        findings.append(
            make_finding(
                1,
                finding_stage,
                Status.UNKNOWN,
                "missing_signed_standard",
                f"Signed standard is missing for {school_id}/{template_version}",
                "target.standard.yaml exists and is review-approved",
                str(signed_standard_path),
                root_cause_bucket="standard_missing",
            )
        )
        return None, findings

    signed_standard = _load_yaml(signed_standard_path)
    contracts: dict[str, dict[str, Any]] = {}
    contract_paths: dict[str, Path] = {}
    next_finding = 1
    coverage_requirements = signed_standard.get("coverage_requirements", {})
    coverage_findings = validate_standard_coverage_requirements(
        coverage_requirements.get("profile"),
        coverage_requirements.get("required_capabilities", []),
        stage=finding_stage,
        start_index=next_finding,
    )
    findings.extend(coverage_findings)
    next_finding += len(coverage_findings)
    for key, rel_path in signed_standard.get("contracts", {}).items():
        contract_path = school_dir / rel_path
        contract_paths[key] = contract_path
        if not contract_path.exists():
            next_finding += 1
            findings.append(
                make_finding(
                    next_finding,
                    finding_stage,
                    Status.UNKNOWN,
                    "missing_contract",
                    f"Contract {key} is missing",
                    "contract file exists",
                    str(contract_path),
                    root_cause_bucket="contract_missing",
                )
            )
            continue
        try:
            import json

            contract = json.loads(contract_path.read_text(encoding="utf-8"))
        except Exception as exc:  # pragma: no cover - defensive branch
            next_finding += 1
            findings.append(
                make_finding(
                    next_finding,
                    finding_stage,
                    Status.UNKNOWN,
                    "invalid_contract_json",
                    f"Contract {key} is not valid JSON",
                    "valid JSON contract",
                    repr(exc),
                    root_cause_bucket="contract_invalid",
                )
            )
            continue
        missing_fields = sorted(REQUIRED_CONTRACT_FIELDS - set(contract))
        if missing_fields:
            next_finding += 1
            findings.append(
                make_finding(
                    next_finding,
                    finding_stage,
                    Status.UNKNOWN,
                    "contract_schema_incomplete",
                    f"Contract {key} is missing required fields",
                    "all required contract fields are present",
                    ", ".join(missing_fields),
                    root_cause_bucket="contract_invalid",
                )
            )
        contracts[key] = contract

    bundle = StandardBundle(
        school_id=school_id,
        template_version=template_version,
        school_dir=school_dir,
        signed_standard_path=signed_standard_path,
        signed_standard=signed_standard,
        contracts=contracts,
        contract_paths=contract_paths,
    )
    return bundle, findings


def verify_template_hash(bundle: StandardBundle, stage: str, start_index: int = 1) -> list[Finding]:
    expected_hash = bundle.signed_standard.get("source", {}).get("template_docx_sha256")
    if not expected_hash:
        return [
            make_finding(
                start_index,
                stage,
                Status.UNKNOWN,
                "missing_template_hash",
                "Signed standard does not bind the template hash",
                "source.template_docx_sha256 is present",
                "missing",
                root_cause_bucket="standard_missing",
            )
        ]
    actual_hash = sha256_file(bundle.template_docx)
    if actual_hash != expected_hash:
        return [
            make_finding(
                start_index,
                stage,
                Status.UNKNOWN,
                "template_hash_mismatch",
                "Template hash does not match the signed standard",
                expected_hash,
                actual_hash,
                affected_ids=[bundle.school_id],
                root_cause_bucket="standard_drift",
            )
        ]
    return []
