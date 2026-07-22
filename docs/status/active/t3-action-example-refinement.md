# T3 动作示例细化

- Status: `ACTIVE`
- Source plan: `docs/plans/2026-07-03-template-parse-refactor-t3-element-policy-plan-06-run-span-subelement-policy-ai-primary.md`
- Latest intent: 在已提交的 T3 run-level 基线上，按首轮 `fill/delete` 动作动态加载对应示例并做第二层复核，再比较准确率。
- Current slice: live T3 已增加按动作批量复核；示例以 JSON 资源加载；replay 保持单次调用兼容。
- Last proof: `tests/unit/template_generation_agent` 190 passed；两份 template-generate/replay contract 17 passed。
- Accuracy blocker: 湖南农业大学旧 run 与重新生成的 L1 都未满足 gold evaluator 所需的完整 `raw_run_facts`，门禁报告所有 source_seq 为 `raw_run_facts_missing`，因此尚无可信的前后 `exact_action_accuracy` 数字。
- Next proof: 生成或修复一份带完整原子 run 原文事实的真实 T3 fixture，然后在相同 T2 gold、模型和参数下分别运行 baseline commit 与当前实现。
- Stop condition: 同一真实 gold fixture 的 baseline/current `exact_action_accuracy`、各动作 precision/recall 和 false-delete 数量均已得到；未取得数字前不得声称准确率提升。
- No-touch scope: T2 分页迁移、T4、T5/T6 执行语义和工作区其他未提交改动。
- Parked: 正式 Prompt v3 的分层 annotations、unknown 人工确认、字符 span 与 `delete_mode` 全链迁移仍归 Plan 06 后续阶段。
