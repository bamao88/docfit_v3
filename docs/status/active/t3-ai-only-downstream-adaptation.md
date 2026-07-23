---
status: impact_confirmed
owner: template-generation
stage: T3/T5/T6/T7/POST_T6
created: 2026-07-23
last_updated: 2026-07-23
plan: T3-HIERARCHICAL-AI-PLAN-07
---

# T3 AI-only 对下游的影响与适配

## 当前结论

T3 已收敛为一条 AI canonical 路线：输入为 sealed L1 加本次运行唯一 T2 最终结果，最终输出只有 `03_element_spec.yaml`。`03.1` observation、`03.1.5` sparse trace 和 `12_t3_materialization_trace.json` 都是自检证据，不是平行结果。

本次只完成 T3 内部清理和长期契约更新；T5/T6/T7、route replay、judge 与历史 run 的实现适配不在本次修改范围。本状态项记录它们目前受到的具体影响和后续完成信号。

## 新的单链契约

一次完整运行只能形成下面一条顺序链：

```text
sealed L1
  -> T2 final unit_map + availability
  -> T3 final element_spec + availability
  -> T4 final global_spec + availability
  -> T5 final template_spec + availability
  -> T6 final DOCX/build_manifest + availability
  -> T7/POST_T6
```

每个阶段可以在内部保留候选、原始观察或比较证据，但下一阶段只能读取该阶段已选择的一个最终结果。任何 required upstream 为 `NOT_AVAILABLE`，下游不得因为文件存在、safe Keep 可执行或 schema 完整而自动恢复为 `AVAILABLE`。

## 契约变化

| 接口 | 旧假设 | 当前 T3 契约 | 下游适配 |
| --- | --- | --- | --- |
| T3 输入 | L1 兼容输入或某条并行 T2 route | `03.0_t3_hierarchical_stage_input.json`，绑定 L1 与唯一 T2 final | T5 之前的编排必须证明 T3 input 的 T2 hash 等于本次 T2 final hash |
| T3 route | `code_raw` / `ai_raw` / `merged` | 只有 `ai` | evaluator、judge、报告删除 T3 Code/Merge 卡片和 merge delta |
| T3 最终结果 | Code、AI、Merged 多份 element spec | 只有 `03_element_spec.yaml` | 所有消费者只解析这一个文件 |
| T3 availability | 可由 merged 或 fallback 隐式补齐 | `03_element_spec.yaml#/route/availability` 是唯一权威 | T5 原样记录；T6/T7 按 required-upstream 规则阻断或降级 |
| T3 程序产物 | proposal、decision、overlay 可被当成执行结果 | observation/sparse/materialization trace 只作自检 | 不允许从 trace 重新生成第二份策略结果 |
| T3 失败行为 | 回退 Code policy | safe Keep，route 仍为 `NOT_AVAILABLE` | 下游可生成审阅预览，但不得宣称 T3 可用或质量通过 |

## 当前已确认的下游缺口

### T5：template_spec 合并

当前 `build_template_spec` 会复制 T3 elements 并记录 `element_spec` hash，但没有保存 T2/T3/T4 各自的 `route_id`、availability 和 reason。它因此无法证明 `template_spec` 的 availability 是三个唯一最终上游结果的保守合并。

需要适配：

1. 在 `template_spec` 增加结构化 `upstream_results`，至少记录 T2/T3/T4 artifact hash、route id、availability 和 reason。
2. `template_spec.route.availability` 使用 required upstream 的保守合并；T3 `NOT_AVAILABLE` 时 T5 不得标成 `AVAILABLE`。
3. T5 verifier 校验记录的 T3 hash 等于实际 `03_element_spec.yaml`，且 route id 只能为 `ai`。
4. T5 不读取 `t3_materialization_trace` 生成或覆盖 element policy；trace 只用于诊断。

### T6：Word 动作计划与执行

当前动作计划的大部分元素动作仍从运行内 `generation_model.unit_strategies` 生成，只有分页优先读取 `template_spec`。这会让 T3 canonical element policy 与实际 Word 动作之间缺少单一权威消费证明。

需要适配：

1. T3 相关的 Keep/Fill/Delete/Generated 动作只从 T5 `template_spec.units[].elements[]` 构造。
2. 每条动作保留 `element_id`、run/span identities、T3 decision trace ref 和 T3 input hash。
3. T3 availability 为 `NOT_AVAILABLE` 时，只允许 copy、安全 Keep 和明确的非 T3 动作；禁止扩大删除、替换或生成字段。
4. build manifest 记录 action 的 upstream stage、artifact hash、availability 和执行前置条件。
5. T6 fresh observation 验证最终 DOCX 效果，不能用“action 已执行”代替效果证据。

### T7：运行验证

当前 T3 verifier 检查 policy 枚举和必需字段，T5 verifier 检查合并后的元素字段，但没有验证 availability 从 T3 到 T5/T6 的连续传递。

需要适配：

1. 增加 availability chain 检查：T3 → T5 → T6 不得从 `NOT_AVAILABLE` 升为 `AVAILABLE`。
2. 校验 T3 final 的 L1 hash、T2 final hash和 T5 记录的 T3 artifact hash。
3. 自检 trace 中有 unmatched claim、conflict、unmaterialized object 或 fallback 时，报告具体 owner；不把 trace 计作第二条 route。
4. first-bad-stage 在 T3 不可用或 hash 不一致时停在 T3/T5 边界，不归因给最终 Word 渲染。

### Route replay、judge 和报告

当前 route replay 的 `code_raw` T5 会同时读取 Code T2/T4 与 canonical AI-only T3，再把结果命名为 `code_raw`；judge 的通用查找仍允许 T3 `code_raw` / `ai_raw`。这不是 T3 内部残留，但会让报告误读为“完整 Code 路线包含一个 Code T3”。

需要适配：

1. T2/T4 route replay 把 T3 表达为共享的 canonical upstream，不再生成或展示 T3 Code/Merge route。
2. 路线名称表达真实组合，例如 T2/T4 route tuple + `t3=ai`，或者只展示每阶段最终结果链；不能把混合来源简写成全链 `code_raw`。
3. T3 stage card 只允许 route id `ai`，不计算 merge consumption 和 merge delta。
4. T3 `NOT_AVAILABLE` 时所有依赖它的 T5/T6 replay 明确 `NOT_AVAILABLE`。

### 历史产物与兼容读取

历史 `test_outputs/` 中的 T3 Code/Merged、comparison、`01.7` 或 overlay 文件保留为历史证据，不作为当前实现残留，也不能被新 run 自动发现为正式输入。读取旧 run 时应显式标记 legacy artifact，并只映射到报告，不映射回当前业务链。

## 适配顺序

1. 先给 T5 增加 `upstream_results` 和 availability 保守合并。
2. 再让 T6 的 T3 动作完全从 T5 canonical elements 生成。
3. 补 T7 hash/availability/first-bad-stage 验证。
4. 最后收敛 route replay、judge、报告和旧 run reader。

这个顺序可以先建立业务数据链，再修展示和历史兼容，避免报告先变而执行仍消费旧权威。

## 完成信号

- 同一 run 中 T3 stage input 的 T2 hash 与 T2 final hash 完全一致。
- T5 只记录一个 T3 final，并保存其 hash、`route_id=ai` 和 availability。
- T3 `NOT_AVAILABLE` 反例中，T5/T6/T7 不会恢复为 `AVAILABLE`，且不会产生 T3 删除/替换动作。
- T6 manifest 的每个 T3 动作都能追溯到 `03_element_spec.yaml` 的唯一 element/run/span identity。
- T3 stage card 只有 AI canonical 指标，无 Code/Merged route 和 merge delta。
- 新 run 不写入、不读取 `01.7_t3_l1_compatibility_input.json`、`03.0_t3_unit_windows.json`、observation bundle `unit_windows`、T3 layered proposal、`agent_t3_overlay` 或 T3 Code/Merged element spec。

## 本次边界

- 已完成：T3 兼容输入、proposal/schema、flat pipeline、overlay 清理；T3 materialization self-check；长期文档同步。
- 未完成：上述 T5/T6/T7/route replay/judge 代码适配和端到端 availability 反例。
- 不在本项修改：T2/T4 自身的 Code/AI/Merged 设计与质量。
