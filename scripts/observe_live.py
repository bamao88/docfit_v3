"""Module 1 真实模型端到端：在真实 document_facts 上跑独立观察，产出三份 AI 文件。

证据 = 真实 Word 事实（真实 document_facts → 防火墙干净渲染包 structure_candidates={}）；
模型 = 真实 Kimi（response_format=json_object，无 tools）。全程无手写观察数据。

凭证从环境读取（KIMI_API_KEY），脚本不碰、不打印 key。

运行（在你的会话里，key 已在 profile/.env）：

    uv run python scripts/observe_live.py --samples 1

成本提示：T2 调用 N=samples 次（自一致性）；T3 每个 AI 认出的单元各一次；T4 一次。
首跑建议 --samples 1 控成本，确认链路通后再加采样。
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from docfit.core.io import read_json
from docfit.template_generation.agent.observation_config import ObservationConfig
from docfit.template_generation.agent.observation_eval import evaluate_bundle
from docfit.template_generation.agent.observation_live import (
    LiveResponder,
    build_kimi_client,
)
from docfit.template_generation.agent.observation_loop import run_observation_pipeline
from docfit.template_generation.agent.packet import (
    build_template_agent_render_packet,
    packet_source_seq_set,
)

DEFAULT_FACTS = Path(
    "runs/template_generation/hunannongye/20260628T110047081862+0800/01_document_facts.json"
)
DEFAULT_OUT = Path("test_outputs/observation_live")


def main() -> None:
    parser = argparse.ArgumentParser(description="Module 1 live observation (real model)")
    parser.add_argument("--facts", type=Path, default=DEFAULT_FACTS, help="document_facts.json path")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="output dir")
    parser.add_argument(
        "--docx",
        type=Path,
        default=None,
        help="source template .docx to render for T4 page facts (docx->pdf->png). "
        "If omitted and --eval-school is set, infers inputs/targets/<school>/raw/source_template.docx",
    )
    parser.add_argument("--samples", type=int, default=1, help="T2 self-consistency samples")
    parser.add_argument("--t3-concurrency", type=int, default=8, help="parallel per-unit T3 calls")
    parser.add_argument("--temperature", type=float, default=0.4)
    parser.add_argument("--max-tokens", type=int, default=16000)
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=DEFAULT_OUT / ".cache",
        help="disk cache for model responses (keyed by prompt+model+temp+sample)",
    )
    parser.add_argument("--refresh", action="store_true", help="ignore cache and re-call the model")
    parser.add_argument(
        "--thinking",
        dest="thinking",
        action="store_true",
        help="enable Kimi thinking mode (higher quality on weak prompts, ~10x slower)",
    )
    parser.add_argument(
        "--no-thinking",
        dest="thinking",
        action="store_false",
        help="disable Kimi thinking mode (default; faster, forces temperature=0.6)",
    )
    parser.set_defaults(thinking=False)
    parser.add_argument(
        "--eval-school",
        default=None,
        help="school id under standards/targets/ to score each stage against gold (e.g. hunannongye)",
    )
    args = parser.parse_args()

    # thinking 开时另写一份输出，便于和默认（关）的产物并排对比。
    if args.thinking and args.out == DEFAULT_OUT:
        args.out = DEFAULT_OUT.parent / "observation_live_think"

    # T4 页事实：渲染源 docx。未显式给 --docx 时，按 --eval-school 推断标准里的源 docx。
    docx = args.docx
    if docx is None and args.eval_school:
        inferred = Path("inputs/targets") / args.eval_school / "raw" / "source_template.docx"
        if inferred.exists():
            docx = inferred

    facts = read_json(args.facts)
    packet = build_template_agent_render_packet(
        document_facts=facts,
        structure_candidates={},  # 防火墙：不喂任何代码结构结论
        source_template_docx=docx,  # 有则渲染→页图+per-seq page_no（确定性）
        render_artifacts_dir=(args.out / "render") if docx else None,
    )
    total = len(packet_source_seq_set(packet))

    client, model = build_kimi_client()
    record: list[dict] = []
    responder = LiveResponder(
        client=client,
        model=model,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
        thinking=args.thinking,
        record=record,
        cache_dir=args.cache_dir,
        refresh=args.refresh,
    )

    print(f"facts      : {args.facts}")
    print(f"source_seq : {total}")
    print(f"render     : {packet.get('render_status')}  docx={docx}")
    print(f"model      : {model}  thinking={args.thinking}")
    print(f"samples    : {args.samples}  t3_concurrency={args.t3_concurrency}  cache={args.cache_dir} refresh={args.refresh}")
    wall_start = time.monotonic()

    bundle = run_observation_pipeline(
        packet=packet,
        responder=responder,
        config=ObservationConfig(enabled=True, self_consistency_samples=args.samples, model=model),
        t3_concurrency=args.t3_concurrency,
    )

    args.out.mkdir(parents=True, exist_ok=True)
    outputs = {
        "ai_unit_observation.json": bundle["ai_unit_observation"],
        "ai_element_observation.json": bundle["ai_element_observation"],
        "ai_layout_observation.json": bundle["ai_layout_observation"],
        "quality_report.json": bundle["quality_report"],
        "bundle.json": bundle,  # 完整记录，含 timing，供评测复用
        "_raw_model_responses.json": record,  # 审计/复跑用，非产品口径
    }

    # 补齐流程：每阶段产物 vs 标准文件 → 准确率 + 耗时。
    if args.eval_school:
        evaluation = evaluate_bundle(bundle, school=args.eval_school)
        outputs["eval.json"] = evaluation
    else:
        evaluation = None

    for name, payload in outputs.items():
        (args.out / name).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    print(f"\noutput dir : {args.out}")
    for stage, key in (
        ("T2 unit", "ai_unit_observation"),
        ("T3 element", "ai_element_observation"),
        ("T4 layout", "ai_layout_observation"),
    ):
        obs = bundle[key]
        cov = obs["coverage"]
        demotions = len(obs.get("quality_report", {}).get("demotions", []))
        print(
            f"  {stage:11s}: items={len(obs['items']):3d} "
            f"owned={len(cov['owned_source_seq']):3d} unknown={len(cov['unknown_source_seq']):3d} "
            f"abstain={obs['abstain']} demotions={demotions}"
        )
    cache_hits = sum(1 for r in record if r.get("from_cache"))
    print(f"  calls: {len(record)} (cache hits: {cache_hits})  wall: {time.monotonic() - wall_start:.1f}s")

    timing = bundle.get("timing", {})
    print(
        f"  timing(s): t2={timing.get('t2_seconds')} t3={timing.get('t3_seconds')} "
        f"t4={timing.get('t4_seconds')} total={timing.get('total_seconds')}"
    )

    if evaluation is not None:
        print(f"\n=== 准确率 vs gold (school={args.eval_school}) ===")
        t2, t3, t4 = (evaluation["stages"][k] for k in ("t2", "t3", "t4"))
        print(
            f"  T2 单元: P={t2['precision']} R={t2['recall']} F1={t2['f1']} "
            f"order_exact={t2['order_exact_match']} missing={t2['missing_units']} extra={t2['extra_units']}"
        )
        print(
            f"  T3 策略: 单元主策略准确率={t3['unit_dominant_policy_accuracy']} "
            f"(评{t3['units_evaluated']}单元) 必填合规={t3['required_field_compliance']} "
            f"mismatch={[m['unit_id'] for m in t3['policy_mismatches']]}"
        )
        if t4.get("page_policy_evaluable"):
            print(
                f"  T4 版式: 页隔离准确率={t4['page_isolation_accuracy']} "
                f"(评{t4['units_evaluated']}单元, {t4['page_count']}页) "
                f"mismatch={[m['unit_id'] for m in t4['page_policy_mismatches']]}"
            )
        else:
            print(f"  T4 版式: 全局版式已产出={t4['global_profile_present']}；页策略不可评（未渲染，加 --docx）")


if __name__ == "__main__":
    main()
