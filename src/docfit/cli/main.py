from __future__ import annotations

from pathlib import Path
import typer

from docfit.convert.orchestrator import (
    run_content_eval,
    run_e2e_eval,
    run_placement_eval,
    run_render_eval,
    run_template_eval,
)
from docfit.core.io import read_json, write_json
from docfit.core.status import Status
from docfit.harness.audit import reject_golden_auto_update
from docfit.harness.coverage import evaluate_bootstrap_coverage
from docfit.harness.profiles import BOOTSTRAP_PROFILE, get_eval_case, get_eval_profile
from docfit.harness.reports import write_report_bundle
from docfit.harness.standards import load_standard_bundle

app = typer.Typer(no_args_is_help=True)
eval_app = typer.Typer(no_args_is_help=True)
app.add_typer(eval_app, name="eval")


def _root() -> Path:
    return Path.cwd()


def _echo_status(status: Status) -> None:
    typer.echo(f"status = {status.value}")


@eval_app.command("template")
def eval_template(
    school: str = typer.Option(..., "--school"),
    template: Path = typer.Option(..., "--template", exists=True),
    out: Path = typer.Option(..., "--out"),
) -> None:
    result = run_template_eval(_root(), school, template, out)
    _echo_status(result.status)


@eval_app.command("content")
def eval_content(
    student: Path = typer.Option(..., "--student", exists=True),
    out: Path = typer.Option(..., "--out"),
) -> None:
    result = run_content_eval(student, out)
    _echo_status(result.status)


@eval_app.command("placement")
def eval_placement(
    school: str = typer.Option(..., "--school"),
    template_artifact: Path = typer.Option(..., "--template-artifact", exists=True),
    content_artifact: Path = typer.Option(..., "--content-artifact", exists=True),
    out: Path = typer.Option(..., "--out"),
) -> None:
    result = run_placement_eval(
        _root(),
        school,
        template_artifact,
        content_artifact,
        out,
    )
    _echo_status(result.status)


@eval_app.command("render")
def eval_render(
    school: str = typer.Option(..., "--school"),
    template_artifact: Path = typer.Option(..., "--template-artifact", exists=True),
    placement_plan: Path = typer.Option(..., "--placement-plan", exists=True),
    out: Path = typer.Option(..., "--out"),
) -> None:
    result = run_render_eval(
        _root(),
        school,
        template_artifact,
        placement_plan,
        out,
    )
    _echo_status(result.status)


@eval_app.command("e2e")
def eval_e2e(
    school: str | None = typer.Option(None, "--school"),
    student: Path | None = typer.Option(None, "--student", exists=True),
    out: Path = typer.Option(Path("reports/bootstrap_pass"), "--out"),
    case: str | None = typer.Option(None, "--case"),
) -> None:
    if case is not None:
        eval_case = get_eval_case(case)
        if eval_case is None:
            raise typer.BadParameter(f"unknown eval case: {case}")
        school = eval_case.school_id
        student = eval_case.student_docx
    if school is None or student is None:
        raise typer.BadParameter("--school and --student are required unless --case is provided")
    result = run_e2e_eval(_root(), school, student, out)
    _echo_status(result.status)


@eval_app.command("coverage")
def eval_coverage(
    profile: str = typer.Option(BOOTSTRAP_PROFILE.profile_id, "--profile"),
    out: Path = typer.Option(Path("reports/coverage_bootstrap_core"), "--out"),
) -> None:
    if get_eval_profile(profile) is None:
        report = {
            "profile": profile,
            "status": Status.UNKNOWN.value,
            "required": 0,
            "covered": 0,
            "missing": [f"unknown profile {profile}"],
        }
        findings = []
        status = Status.UNKNOWN
    else:
        report, finding_models = evaluate_bootstrap_coverage(_root())
        findings = [finding.to_dict() for finding in finding_models]
        status = Status(report["status"])
    write_json(out / "coverage_report.json", report)
    write_report_bundle(
        out,
        stage="coverage",
        status=status,
        findings=findings,
        artifacts={"coverage_report": "coverage_report.json"},
        coverage=report,
    )
    _echo_status(status)


@eval_app.command("standards")
def eval_standards(
    school: str = typer.Option("demo-school", "--school"),
    audit: bool = typer.Option(False, "--audit"),
    out: Path = typer.Option(Path("reports/standards_audit"), "--out"),
) -> None:
    bundle, findings = load_standard_bundle(_root(), school, finding_stage="standards")
    status = Status.UNKNOWN if findings else Status.PASS
    artifacts = {}
    if bundle is not None:
        artifacts["signed_standard"] = str(bundle.signed_standard_path)
    if audit:
        audit_path = _root() / "reports" / "audit_log.json"
        artifacts["audit_log"] = str(audit_path)
    write_report_bundle(
        out,
        stage="standards",
        status=status,
        findings=[finding.to_dict() for finding in findings],
        artifacts=artifacts,
    )
    _echo_status(status)


@app.command("diagnose")
def diagnose(run: Path = typer.Option(..., "--run")) -> None:
    run_dir = run if run.is_dir() else Path("reports") / str(run)
    summary = read_json(run_dir / "summary.json")
    clusters = read_json(run_dir / "issue_clusters.json")
    typer.echo(f"run_id = {summary['run_id']}")
    typer.echo(f"status = {summary['status']}")
    typer.echo(f"primary_failure_bucket = {summary['primary_failure_bucket']}")
    typer.echo(f"clusters = {len(clusters)}")


@app.command("convert")
def convert(
    school: str = typer.Option(..., "--school"),
    student: Path = typer.Option(..., "--student", exists=True),
    out: Path = typer.Option(..., "--out"),
    report: Path = typer.Option(Path("reports/run_convert_001"), "--report"),
) -> None:
    result = run_e2e_eval(_root(), school, student, report, final_copy=out)
    if result.status != Status.PASS:
        raise typer.Exit(code=1)
    _echo_status(result.status)


@app.command("attempt-golden-auto-update")
def attempt_golden_auto_update(path: str = typer.Option(..., "--path")) -> None:
    event = reject_golden_auto_update(_root(), path)
    typer.echo(f"allowed = {event['allowed']}")
