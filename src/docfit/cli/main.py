from __future__ import annotations

from enum import Enum
from pathlib import Path
import typer

from docfit.convert.orchestrator import (
    run_template_generate_eval,
    run_template_generation_full_eval,
    run_template_gap_eval,
)
from docfit.core.io import read_json
from docfit.core.status import Status
from docfit.harness.audit import reject_golden_auto_update
from docfit.harness.reports import write_report_bundle
from docfit.harness.standards import load_standard_bundle
from docfit.harness.template_generation_standard_judge import (
    evaluate_template_generation_standard_quality_command,
    judge_template_generation_run,
)
from docfit.template_generation.agent import (
    AgentConfig,
    AgentConfigError,
    agent_config_from_env,
)
from docfit.template_generation.agent.config import (
    effective_text_provider,
    effective_vision_provider,
)
from docfit.template_generation.agent.observation_orchestrate import (
    run_live_template_observation_stage,
    run_template_observation_stage,
)

app = typer.Typer(no_args_is_help=True)
eval_app = typer.Typer(no_args_is_help=True)
template_app = typer.Typer(no_args_is_help=True)
template_stage_app = typer.Typer(no_args_is_help=True)
app.add_typer(eval_app, name="eval")
app.add_typer(template_app, name="template")
template_app.add_typer(template_stage_app, name="stage")


class AIMode(str, Enum):
    off = "off"
    live = "live"
    replay = "replay"
    bundle = "bundle"


def _root() -> Path:
    return Path.cwd()


def _template_eval_runs_root() -> Path:
    return Path("runs/eval")


def _echo_status(status: Status) -> None:
    typer.echo(f"status = {status.value}")


def _echo_compatibility_alias(canonical: str) -> None:
    typer.echo(
        f"compatibility alias: prefer `docfit {canonical}`",
        err=True,
    )


def _canonical_agent_config(
    *,
    ai: AIMode,
    llm: bool,
    replay: Path | None,
    bundle: Path | None,
    model: str | None,
    cache_dir: Path,
) -> AgentConfig:
    mode = ai.value
    if llm:
        if mode not in {"off", "live"}:
            raise typer.BadParameter("--llm is an alias for --ai live and conflicts with this --ai mode")
        mode = "live"
    if mode == "off":
        if replay is not None or bundle is not None:
            raise typer.BadParameter("--replay/--bundle require the matching --ai mode")
        return AgentConfig(enabled=False)
    if mode == "live":
        env_config = agent_config_from_env() or AgentConfig(enabled=False)
        if replay is not None or bundle is not None:
            raise typer.BadParameter("--ai live cannot consume --replay or --bundle")
        return AgentConfig(
            enabled=True,
            transport="replay",
            observation_mode="live",
            observation_t3_concurrency=4,
            observation_cache_dir=cache_dir,
            allow_live_without_render_packet=True,
            model=model or env_config.model,
            text_provider=effective_text_provider(env_config),  # type: ignore[arg-type]
            vision_provider=effective_vision_provider(env_config),  # type: ignore[arg-type]
            vision_model=env_config.vision_model,
        )
    if mode == "replay":
        if replay is None:
            raise typer.BadParameter("--ai replay requires --replay")
        if bundle is not None:
            raise typer.BadParameter("--ai replay cannot consume --bundle")
        return AgentConfig(
            enabled=True,
            transport="replay",
            observation_mode="replay",
            observation_transcript_path=replay,
            observation_t3_concurrency=4,
            model=model or "replay",
        )
    if bundle is None:
        raise typer.BadParameter("--ai bundle requires --bundle")
    if replay is not None:
        raise typer.BadParameter("--ai bundle cannot consume --replay")
    return AgentConfig(
        enabled=True,
        transport="replay",
        observation_mode="bundle",
        observation_bundle_path=bundle,
        model=model,
    )


@template_app.command("generate")
def template_generate(
    template: Path = typer.Option(..., "--template", exists=True),
    out: Path = typer.Option(..., "--out"),
    ai: AIMode = typer.Option(AIMode.off, "--ai", case_sensitive=False),
    llm: bool = typer.Option(False, "--llm", help="Compatibility alias for --ai live."),
    replay: Path | None = typer.Option(None, "--replay", exists=True),
    bundle: Path | None = typer.Option(None, "--bundle", exists=True),
    model: str | None = typer.Option(None, "--model"),
) -> None:
    """Generate a fillable template; deterministic/offline by default."""

    agent_config = _canonical_agent_config(
        ai=ai,
        llm=llm,
        replay=replay,
        bundle=bundle,
        model=model,
        cache_dir=out / "cache",
    )
    result = run_template_generate_eval(
        _root(),
        template,
        out,
        agent_config=agent_config,
        run_context={
            "entrypoint": "cli.template.generate",
            "command": "docfit template generate",
        },
    )
    _echo_status(result.status)


@template_app.command("verify")
def template_verify(
    school: str = typer.Option(..., "--school"),
    template: Path = typer.Option(..., "--template", exists=True),
    out: Path = typer.Option(..., "--out"),
    template_version: str = typer.Option("v1", "--template-version"),
    ai: AIMode = typer.Option(AIMode.off, "--ai", case_sensitive=False),
    llm: bool = typer.Option(False, "--llm", help="Compatibility alias for --ai live."),
    replay: Path | None = typer.Option(None, "--replay", exists=True),
    bundle: Path | None = typer.Option(None, "--bundle", exists=True),
    model: str | None = typer.Option(None, "--model"),
) -> None:
    """Run generation, gap, judge, route-eval, and the full summary."""

    agent_config = _canonical_agent_config(
        ai=ai,
        llm=llm,
        replay=replay,
        bundle=bundle,
        model=model,
        cache_dir=out / "cache",
    )
    result = run_template_generation_full_eval(
        _root(),
        school,
        template,
        out,
        template_version=template_version,
        agent_config=agent_config,
        run_context={
            "entrypoint": "cli.template.verify",
            "command": "docfit template verify",
        },
    )
    _echo_status(result.status)


def _template_stage_command(
    *,
    stage: str,
    run: Path | None,
    template: Path | None,
    out: Path | None,
    ai: AIMode,
    replay: Path | None,
    bundle: Path | None,
    t2_route: str,
    t2_artifact: Path | None,
    with_upstream: bool,
) -> None:
    if (run is None) == (template is None):
        raise typer.BadParameter("pass exactly one of --run or --template")
    if ai is AIMode.off:
        raise typer.BadParameter("template stage produces AI observations; use live, replay, or bundle")
    if out is None:
        out = (
            run.resolve().parent / f"{run.resolve().name}_{stage}_debug"
            if run is not None
            else Path("runs/template_stage") / str(template.stem) / stage
        )
    if run is not None and out.resolve().is_relative_to(run.resolve()):
        raise typer.BadParameter("stage --out must not write inside the source run")
    try:
        summary = run_template_observation_stage(
            source_run_dir=run,
            source_template_docx=template,
            out_dir=out,
            stage=stage,
            ai_mode=ai.value,
            replay_path=replay,
            bundle_path=bundle,
            t2_route=t2_route,
            t2_artifact_path=t2_artifact,
            with_upstream=with_upstream,
            entrypoint=f"cli.template.stage.{stage}",
        )
    except AgentConfigError as exc:
        raise typer.BadParameter(str(exc)) from exc
    typer.echo(f"stage = {summary['stage']}")
    typer.echo(f"ai_mode = {summary['ai_mode']}")
    typer.echo(f"summary = {out / 'summary.json'}")


def _stage_options(
    stage: str,
    run: Path | None,
    template: Path | None,
    out: Path | None,
    ai: AIMode,
    replay: Path | None,
    bundle: Path | None,
    t2_route: str,
    t2_artifact: Path | None,
    with_upstream: bool,
) -> None:
    _template_stage_command(
        stage=stage,
        run=run,
        template=template,
        out=out,
        ai=ai,
        replay=replay,
        bundle=bundle,
        t2_route=t2_route,
        t2_artifact=t2_artifact,
        with_upstream=with_upstream,
    )


@template_stage_app.command("t2")
def template_stage_t2(
    run: Path | None = typer.Option(None, "--run", exists=True, file_okay=False),
    template: Path | None = typer.Option(None, "--template", exists=True),
    out: Path | None = typer.Option(None, "--out"),
    ai: AIMode = typer.Option(AIMode.live, "--ai", case_sensitive=False),
    replay: Path | None = typer.Option(None, "--replay", exists=True),
    bundle: Path | None = typer.Option(None, "--bundle", exists=True),
) -> None:
    _stage_options("t2", run, template, out, ai, replay, bundle, "ai_raw", None, False)


@template_stage_app.command("t3")
def template_stage_t3(
    run: Path | None = typer.Option(None, "--run", exists=True, file_okay=False),
    template: Path | None = typer.Option(None, "--template", exists=True),
    out: Path | None = typer.Option(None, "--out"),
    ai: AIMode = typer.Option(AIMode.live, "--ai", case_sensitive=False),
    replay: Path | None = typer.Option(None, "--replay", exists=True),
    bundle: Path | None = typer.Option(None, "--bundle", exists=True),
    t2_route: str = typer.Option("ai_raw", "--t2-route"),
    t2_artifact: Path | None = typer.Option(None, "--t2-artifact", exists=True),
    with_upstream: bool = typer.Option(False, "--with-upstream"),
) -> None:
    _stage_options(
        "t3",
        run,
        template,
        out,
        ai,
        replay,
        bundle,
        t2_route,
        t2_artifact,
        with_upstream,
    )


@template_stage_app.command("t4")
def template_stage_t4(
    run: Path | None = typer.Option(None, "--run", exists=True, file_okay=False),
    template: Path | None = typer.Option(None, "--template", exists=True),
    out: Path | None = typer.Option(None, "--out"),
    ai: AIMode = typer.Option(AIMode.live, "--ai", case_sensitive=False),
    replay: Path | None = typer.Option(None, "--replay", exists=True),
    bundle: Path | None = typer.Option(None, "--bundle", exists=True),
) -> None:
    _stage_options("t4", run, template, out, ai, replay, bundle, "ai_raw", None, False)


@template_app.command("inspect")
def template_inspect(
    run: Path = typer.Option(..., "--run", exists=True, file_okay=False),
    stage: str | None = typer.Option(None, "--stage"),
) -> None:
    """Read an existing run without generating files or calling APIs."""

    run_dir = run.resolve()
    if (run_dir / "eval_runs" / "template_generate").is_dir() and stage is not None:
        run_dir = run_dir / "eval_runs" / "template_generate"
    manifest_path = run_dir / "run_manifest.json"
    summary_path = run_dir / "summary.json"
    manifest = read_json(manifest_path) if manifest_path.exists() else {}
    summary = read_json(summary_path) if summary_path.exists() else {}
    typer.echo(f"run = {run_dir}")
    typer.echo(f"status = {summary.get('status') or manifest.get('status') or 'UNKNOWN'}")
    typer.echo(f"ai_mode = {manifest.get('ai_mode') or 'unknown'}")
    typer.echo(f"source_render_hash = {manifest.get('source_render_hash') or 'missing'}")
    typer.echo(f"api_call_count = {manifest.get('api_call_count', 0)}")
    if stage is not None:
        normalized = stage.strip().lower()
        names = {
            "t1": ["01_document_facts.json"],
            "l1": [
                "01.5_l1_input_contract.json",
                "01.6_t2_l1_stage_input.json",
                "01.7_t3_l1_compatibility_input.json",
                "01.8_t4_l1_stage_input.json",
            ],
            "t2": ["02.0_t2_code_unit_map.yaml", "02.2_t2_ai_unit_observation.yaml", "02.3_t2_merged_unit_map.yaml"],
            "t3": ["03.0_t3_code_element_spec.yaml", "03.1_t3_ai_element_observation.yaml", "03.2_t3_merged_element_spec.yaml"],
            "t4": ["04.0_t4_code_global_spec.yaml", "04.1_t4_ai_layout_observation.yaml", "04.2_t4_merged_global_spec.yaml"],
            "t5": ["05_template_spec.yaml"],
            "t6": ["06.1_fillable_template.docx", "06.2_build_manifest.json"],
            "t7": ["07_verification_report.json"],
        }
        if normalized not in names:
            raise typer.BadParameter("--stage must be t1, l1, t2, t3, t4, t5, t6, or t7")
        for name in names[normalized]:
            path = run_dir / name
            typer.echo(f"{name} = {'present' if path.exists() else 'missing'}")


def _agent_config_from_cli(
    *,
    llm: bool,
    agent_replay: Path | None,
    agent_render_packet: Path | None,
    agent_observation_bundle: Path | None,
    agent_observation_replay: Path | None,
    agent_observe_live: bool,
    agent_max_rounds: int,
    agent_max_tokens: int,
    agent_temperature: float,
    agent_provider: str,
    agent_live: bool,
) -> AgentConfig | None:
    if agent_replay is not None:
        raise typer.BadParameter(
            "--agent-replay used the removed layered-submission agent path; "
            "use --agent-observation-replay for Module 1 observation replay"
        )
    if agent_provider != "replay":
        raise typer.BadParameter(
            "--agent-provider direct transports were removed; configure "
            "DOCFIT_TEMPLATE_AGENT_TEXT_PROVIDER for --agent-observe-live"
        )
    if agent_live:
        agent_observe_live = True
    if (
        agent_render_packet is not None
        and agent_observation_bundle is None
        and agent_observation_replay is None
        and not agent_observe_live
        and not llm
    ):
        raise typer.BadParameter(
            "--agent-render-packet must be combined with an observation mode "
            "(--agent-observation-bundle, --agent-observation-replay, --agent-observe-live, or --llm)"
        )
    if llm and any(
        path is not None
        for path in (
            agent_observation_bundle,
            agent_observation_replay,
        )
    ):
        raise typer.BadParameter(
            "--llm cannot be combined with replay or observation bundle inputs"
        )
    if llm:
        agent_observe_live = True

    if not any(
        [
            agent_replay is not None,
            agent_render_packet is not None,
            agent_observation_bundle is not None,
            agent_observation_replay is not None,
            agent_observe_live,
            agent_live,
        ]
    ):
        return agent_config_from_env()

    observation_mode = "off"
    if agent_observation_bundle is not None:
        observation_mode = "bundle"
    elif agent_observation_replay is not None:
        observation_mode = "replay"
    elif agent_observe_live:
        observation_mode = "live"
    return AgentConfig(
        enabled=True,
        transport="replay",
        max_rounds=agent_max_rounds,
        max_tokens=agent_max_tokens,
        temperature=agent_temperature,
        transcript_path=agent_replay,
        render_packet_path=agent_render_packet,
        observation_bundle_path=agent_observation_bundle,
        observation_mode=observation_mode,  # type: ignore[arg-type]
        observation_transcript_path=agent_observation_replay,
        observation_t3_concurrency=4 if llm else 1,
        allow_live_without_render_packet=(
            (agent_live or agent_observe_live) and agent_render_packet is None
        ),
    )


@eval_app.command("template-gap")
def eval_template_gap(
    school: str = typer.Option(..., "--school"),
    generated_template: Path = typer.Option(..., "--generated-template"),
    out: Path = typer.Option(..., "--out"),
) -> None:
    result = run_template_gap_eval(_root(), school, generated_template, out)
    _echo_status(result.status)


@eval_app.command("template-generate")
def eval_template_generate(
    template: Path = typer.Option(..., "--template", exists=True),
    out: Path = typer.Option(..., "--out"),
    llm: bool = typer.Option(
        False,
        "--llm",
        help="Call the live T2/T3 text and T4 vision APIs; default is offline.",
    ),
    agent_replay: Path | None = typer.Option(None, "--agent-replay", exists=True),
    agent_render_packet: Path | None = typer.Option(None, "--agent-render-packet", exists=True),
    agent_observation_bundle: Path | None = typer.Option(None, "--agent-observation-bundle", exists=True),
    agent_observation_replay: Path | None = typer.Option(None, "--agent-observation-replay", exists=True),
    agent_observe_live: bool = typer.Option(False, "--agent-observe-live"),
    agent_max_rounds: int = typer.Option(4, "--agent-max-rounds"),
    agent_max_tokens: int = typer.Option(4000, "--agent-max-tokens"),
    agent_temperature: float = typer.Option(1.0, "--agent-temperature"),
    agent_provider: str = typer.Option("replay", "--agent-provider"),
    agent_live: bool = typer.Option(False, "--agent-live"),
) -> None:
    _echo_compatibility_alias("template generate")
    agent_config = _agent_config_from_cli(
        llm=llm,
        agent_replay=agent_replay,
        agent_render_packet=agent_render_packet,
        agent_observation_bundle=agent_observation_bundle,
        agent_observation_replay=agent_observation_replay,
        agent_observe_live=agent_observe_live,
        agent_max_rounds=agent_max_rounds,
        agent_max_tokens=agent_max_tokens,
        agent_temperature=agent_temperature,
        agent_provider=agent_provider,
        agent_live=agent_live,
    )
    result = run_template_generate_eval(
        _root(),
        template,
        out,
        agent_config=agent_config,
    )
    _echo_status(result.status)


@eval_app.command("template-generation-full")
def eval_template_generation_full(
    school: str = typer.Option(..., "--school"),
    template: Path = typer.Option(..., "--template", exists=True),
    out: Path = typer.Option(..., "--out"),
    template_version: str = typer.Option("v1", "--template-version"),
    llm: bool = typer.Option(
        False,
        "--llm",
        help="Call the live T2/T3 text and T4 vision APIs; default is offline.",
    ),
    agent_replay: Path | None = typer.Option(None, "--agent-replay", exists=True),
    agent_render_packet: Path | None = typer.Option(None, "--agent-render-packet", exists=True),
    agent_observation_bundle: Path | None = typer.Option(None, "--agent-observation-bundle", exists=True),
    agent_observation_replay: Path | None = typer.Option(None, "--agent-observation-replay", exists=True),
    agent_observe_live: bool = typer.Option(False, "--agent-observe-live"),
    agent_max_rounds: int = typer.Option(4, "--agent-max-rounds"),
    agent_max_tokens: int = typer.Option(4000, "--agent-max-tokens"),
    agent_temperature: float = typer.Option(1.0, "--agent-temperature"),
    agent_provider: str = typer.Option("replay", "--agent-provider"),
    agent_live: bool = typer.Option(False, "--agent-live"),
) -> None:
    _echo_compatibility_alias("template verify")
    agent_config = _agent_config_from_cli(
        llm=llm,
        agent_replay=agent_replay,
        agent_render_packet=agent_render_packet,
        agent_observation_bundle=agent_observation_bundle,
        agent_observation_replay=agent_observation_replay,
        agent_observe_live=agent_observe_live,
        agent_max_rounds=agent_max_rounds,
        agent_max_tokens=agent_max_tokens,
        agent_temperature=agent_temperature,
        agent_provider=agent_provider,
        agent_live=agent_live,
    )
    result = run_template_generation_full_eval(
        _root(),
        school,
        template,
        out,
        template_version=template_version,
        agent_config=agent_config,
    )
    _echo_status(result.status)


@eval_app.command("template-observe")
def eval_template_observe(
    stage: str = typer.Option(..., "--stage", help="Live observation stage: t2, t3, or t4."),
    template: Path = typer.Option(..., "--template", exists=True),
    out: Path = typer.Option(..., "--out"),
    t2_observation: Path | None = typer.Option(
        None,
        "--t2-observation",
        exists=True,
        help="Optional AI T2 artifact for T3; otherwise T3 runs T2 live first.",
    ),
) -> None:
    _echo_compatibility_alias(f"template stage {stage.lower()}")
    try:
        summary = run_live_template_observation_stage(
            source_template_docx=template,
            out_dir=out,
            stage=stage,
            t2_observation_path=t2_observation,
        )
    except AgentConfigError as exc:
        raise typer.BadParameter(str(exc)) from exc
    typer.echo(f"stage = {summary['stage']}")
    typer.echo("llm_mode = live_api")
    typer.echo(f"summary = {out / 'summary.json'}")


@eval_app.command("template-generation-standard-quality")
def eval_template_generation_standard_quality(
    school: str | None = typer.Option(None, "--school"),
    profile: str | None = typer.Option(None, "--profile"),
    template_version: str = typer.Option("v1", "--template-version"),
    out: Path = typer.Option(..., "--out"),
) -> None:
    if bool(school) == bool(profile):
        raise typer.BadParameter("--school and --profile are mutually exclusive; pass exactly one")
    result = evaluate_template_generation_standard_quality_command(
        _root(),
        out,
        school_id=school,
        profile_id=profile,
        template_version=template_version,
    )
    _echo_status(result.status)


@eval_app.command("template-generation-judge")
def eval_template_generation_judge(
    school: str = typer.Option(..., "--school"),
    run: Path = typer.Option(..., "--run"),
    template_version: str = typer.Option("v1", "--template-version"),
    run_id: str | None = typer.Option(None, "--run-id"),
    out: Path = typer.Option(..., "--out"),
    derive_template_gap: bool = typer.Option(True, "--derive-template-gap/--no-derive-template-gap"),
) -> None:
    result = judge_template_generation_run(
        _root(),
        school,
        run,
        out,
        template_version=template_version,
        run_id=run_id,
        derive_template_gap=derive_template_gap,
    )
    _echo_status(result.status)


@eval_app.command("standards")
def eval_standards(
    school: str = typer.Option("demo-school", "--school"),
    audit: bool = typer.Option(False, "--audit"),
    out: Path = typer.Option(_template_eval_runs_root() / "standards_audit", "--out"),
) -> None:
    bundle, findings = load_standard_bundle(_root(), school, finding_stage="standards")
    status = Status.UNKNOWN if findings else Status.PASS
    artifacts = {}
    if bundle is not None:
        artifacts["signed_standard"] = str(bundle.signed_standard_path)
    if audit:
        audit_path = out / "audit_log.json"
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
    run_dir = run if run.is_dir() else _template_eval_runs_root() / str(run)
    summary = read_json(run_dir / "summary.json")
    clusters = read_json(run_dir / "issue_clusters.json")
    typer.echo(f"run_id = {summary['run_id']}")
    typer.echo(f"status = {summary['status']}")
    typer.echo(f"primary_failure_bucket = {summary['primary_failure_bucket']}")
    typer.echo(f"clusters = {len(clusters)}")


@app.command("attempt-golden-auto-update")
def attempt_golden_auto_update(path: str = typer.Option(..., "--path")) -> None:
    event = reject_golden_auto_update(_root(), path)
    typer.echo(f"allowed = {event['allowed']}")
