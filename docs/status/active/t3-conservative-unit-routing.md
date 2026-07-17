# T3 Conservative Unit Routing Active Capsule

- Capsule status: `COMPLETE`
- Source contract: 当前对话批准的 T3 单元整体路由、保守删除与 gold 上游评测契约；关联 `docs/plans/2026-07-03-template-parse-refactor-t3-element-policy-plan-06-run-span-subelement-policy-ai-primary.md`
- Latest intent: 只修改 T3，并以同一份人工确认 T2 gold 重测当前基线和新方案准确率。
- Current slice: 已完成整单元路由、表格预处理、条件式深入、保守删除门禁与 gold-upstream 评测校验；旧的对象级二次规划、平铺 T3 回退、对应 prompt stage 和独立脚本入口已删除，所有 replay 也必须经过同一单元路由与删除门禁。
- Blocker fingerprint: none。
- Last proven evidence: 湖南农大 signed-active T2/T3 standard；同一 320 source_seq / 708 raw-run ledger、MiniMax-M3、temperature=0、source_render_hash `sha256:40dccdda243790861dc96c2008e7e20b702e57b1518b26cbbbe416a62c3ea62e`。基线 `/private/tmp/docfit_t3_gold_baseline_v1/report.json`：accuracy 0.3446、coverage 0.7797、false delete 66、API 82。最终候选 `/private/tmp/docfit_t3_gold_candidate_v3/report.json`：accuracy 0.5876、coverage 1.0、false delete 0、API 30。
- Next action: 无；等待人工 review 或扩展更多学校的 signed run-ledger 标准。
- Next proof: 已通过 `uv run pytest -q` 全量回归；聚焦 T3 agent 单测及 template-generate / agent / standard-judge 合同测试均通过。
- Stop condition: gold 输入校验通过；单测/契约通过；误删为硬门禁；准确率报告可复现。
- No-touch scope: L1、T2/T4 质量、CLI/route 重构、并行 entropy cleanup 与当前工作区其他未提交改动。
- Parked work: 扩展到至少三校 signed run-span ledger；提升 instruction_remove 召回（当前 6.93%），但必须继续满足零误删硬门。

## Gold A/B

| 指标 | 当前代码基线 | 最终方案 | 差异 |
|---|---:|---:|---:|
| run 级精确策略准确率 | 34.46% | 58.76% | +24.30pp |
| run 覆盖率 | 77.97% | 100.00% | +22.03pp |
| 错误删除 run | 66 | 0 | -66 |
| 删除精确率 | 66.67% | 100.00% | +33.33pp |
| 删除召回率 | 65.35% | 6.93% | -58.42pp |
| 保留内容召回率 | 86.96% | 100.00% | +13.04pp |
| API 调用 | 82 | 30 | -52 (-63.4%) |
| API 最终错误 | 5 | 1 | -4 |

解释：本轮按产品优先级把误删设为硬门，因此主动牺牲了删除召回；漏删进入后续复核，不再用误删换取表面清理率。
