# T3 动作示例细化

- Status: `ACTIVE`
- Source plan: `docs/plans/2026-07-03-template-parse-refactor-t3-element-policy-plan-06-run-span-subelement-policy-ai-primary.md`
- Latest intent: 在已提交的 T3 run-level 基线上，按首轮 `fill/delete` 动作动态加载对应示例并做第二层复核，再比较准确率。
- Current slice: live T3 已增加按动作批量复核；示例以 JSON 资源加载；正式 T3 prompt 已统一 raw-run 边界、字段下钻与动作排除测试；replay 保持单次调用兼容。
- Last proof: MiniMax 生产 responder 与 quota fallback 均已接通动作精判能力；prompt 装配、生产 responder 与观察流水线聚焦测试 49 passed。
- Accuracy evidence: 项目 `.env` 中的 MiniMax 配置可用。湖南农业大学真实 gold 上，用相同 L1、T2 gold 与缓存首轮结果做开关 A/B：关闭和开启动作示例精判均为 `exact_action_accuracy=0.2782`、`action_macro_f1=0.248`、false delete `0`；delete precision `1.0`、recall `0.0644`，fill precision `0.8308`、recall `0.2517`。本样本未证明准确率提升。
- Next proof: 用本轮 prompt 在至少三个学校 gold 上重新做固定输入 A/B，重点观察 fill/delete recall 与 false delete；当前只证明提示词已进入正式运行链，尚未证明质量提升。
- Stop condition: 多学校受控 A/B 显示核心动作准确率或 macro-F1 有稳定提升，同时 false delete 不恶化；在此之前不得声称动作示例提高了准确率。
- No-touch scope: T2 分页迁移、T4、T5/T6 执行语义和工作区其他未提交改动。
- Parked: 正式 Prompt v3 的分层 annotations、unknown 人工确认、字符 span 与 `delete_mode` 全链迁移仍归 Plan 06 后续阶段。
