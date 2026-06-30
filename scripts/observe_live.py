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
from pathlib import Path

from docfit.core.io import read_json
from docfit.template_generation.agent.observation_config import ObservationConfig
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
    parser.add_argument("--samples", type=int, default=1, help="T2 self-consistency samples")
    parser.add_argument("--t3-concurrency", type=int, default=3, help="parallel per-unit T3 calls")
    parser.add_argument("--temperature", type=float, default=0.4)
    parser.add_argument("--max-tokens", type=int, default=8000)
    args = parser.parse_args()

    facts = read_json(args.facts)
    packet = build_template_agent_render_packet(
        document_facts=facts,
        structure_candidates={},  # 防火墙：不喂任何代码结构结论
    )
    total = len(packet_source_seq_set(packet))

    client, model = build_kimi_client()
    record: list[dict] = []
    responder = LiveResponder(
        client=client,
        model=model,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
        record=record,
    )

    print(f"facts      : {args.facts}")
    print(f"source_seq : {total}")
    print(f"model      : {model}")
    print(f"samples    : {args.samples}  (calling real model — this will take a while)")

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
        "_raw_model_responses.json": record,  # 审计/复跑用，非产品口径
    }
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
    print(f"  model calls: {len(record)}")


if __name__ == "__main__":
    main()
