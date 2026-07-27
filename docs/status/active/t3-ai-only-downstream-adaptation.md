---
status: implemented
owner: template-generation
stage: T1/L1/T2/T3/T4/T5/T6/T7
created: 2026-07-23
last_updated: 2026-07-24
plan: T3-HIERARCHICAL-AI-PLAN-07
---

# 模板生成单一 Final 结果链

## 当前结论

模板生成业务链已经改为统一 Final Publisher 边界：T2/T3/T4 只保留 AI observation 和一个带 `result_role=final` 的 canonical 结果，下一阶段不再识别或选择 Code/Merge 路线。

这次修改把原来的“T3 AI-only 下游适配”提升为所有模板生成阶段共同规则。业务含义是：以后 T2 从 merged 改为 AI-only 或 Code-only，只需要修改 T2 内部 publisher；T3 仍只读取稳定的 `02_unit_map.yaml`。

## Expected vs Observed

### Expected

```text
stage internal candidates
  -> schema / identity / availability validation
  -> Final Publisher
  -> one canonical final
  -> downstream consumer
```

跨阶段输入必须满足：

- `stage_id`、`result_role=final` 和 `artifact_type` 正确；
- availability 是 `AVAILABLE` 或 `NOT_AVAILABLE`；
- L1 和直接上游 hash 与本次运行一致；
- consumer 不按 `route_id`、`producer_mode`、AI/Code/Merge 分支；
- required upstream 不可用时，availability 不得在下游自动恢复。

### 变更前 observed

- T3 可以直接接收 `ai_unit_observation`；
- T6 元素动作主要从运行内 `generation_model.unit_strategies` 生成，而不是只从 T5；
- `02.3_t2_merged_unit_map.yaml`、`04.2_t4_merged_global_spec.yaml` 既像候选证据又像业务输入；
- T5/T6 虽记录若干 hash，但没有统一强类型 final 边界；
- AI observation、普通 dict 和 canonical final 在接口上难以区分，误传时可能静默运行。

## 已实施

### 统一 final 契约

新增 `FinalStageResult` 和 Final Publisher。canonical payload 统一写入：

```yaml
stage_id: T2
result_role: final
artifact_type: unit_map
availability:
  status: AVAILABLE
  reason: null
input_refs: {}
lineage:
  producer_mode: merged
  selected_from: []
```

消费者边界会拒绝候选 observation、缺少 final metadata 的普通 dict、错误 artifact type、错误阶段或不匹配的 L1 hash。

### 业务消费链

| Consumer | 唯一业务输入 |
| --- | --- |
| T3 | T2 final `02_unit_map.yaml` + sealed L1 facts |
| T5 | T2 final + T3 final + T4 final；L1 仅做 hash/identity 校验 |
| T6 plan/manifest | T5 final `05_template_spec.yaml`；L1 仅做物理身份解析 |
| T7 final | T6 final，并记录 T5/T6 hash refs |

T3/T4 仍按真实 DAG 工作：T3 依赖 T2 final，T4 可与 T3 并行，T5 汇合三个 final。这里的“唯一输入”指每条业务边只有一个 canonical final，不是强行把并行阶段改成假串行。

### 稳定产物与 hash 链

稳定 canonical 文件为：

```text
01_document_facts.json
01.5_l1_input_contract.json
02_unit_map.yaml
03_element_spec.yaml
04_global_spec.yaml
05_template_spec.yaml
06.1_fillable_template.docx + 06.2_build_manifest.json
07_verification_report.json
```

当前 hash 链为：

```text
T2 final
  -> T3 Stage Input
  -> T3 final
T2/T3/T4 final
  -> T5 final
T5 final
  -> T6 build manifest final
T5/T6 final
  -> T7 final
```

T2/T3/T4 的 Code/AI/Merge 编号候选已经退出；仅保留各阶段 AI raw 证据和稳定 canonical final。

### availability

- T5 对 T2/T3/T4 final 做保守合并；
- T6 和 T7 继续传播 T5/T6 availability；
- `NOT_AVAILABLE` 时仍可复制源文件、创建产品固定 body slot 或输出安全预览，但不能据此宣称上游语义可用，也不能生成依赖不可用 T3 policy 的删除、替换或字段动作。

## 验证证据

- final contract、候选拒绝、hash ref、availability 单测；
- T3 hierarchical/sparse/observation pipeline 聚焦测试；
- 反例：AI unit observation 与 T2 final 故意不同，T3 unit roots 只使用 final；
- T5/T6 计划与 manifest 测试，证明动作从 T5 elements 生成；
- T7 反例：直接上游 hash 不一致或 availability 被升级时，输出结构化 finding 并影响 stage status/first bad stage；
- 完整 template-generate 契约测试，校验 canonical 文件、availability 和 T5→T6 hash。
- 湖南农大真实模板 AI-off 全链：`/private/tmp/docfit_final_chain_20260724`。run manifest 中 T1/L1/T2/T4 为 `AVAILABLE`，T3/T5/T6/T7 保守保持 `NOT_AVAILABLE`，直接上游 hash 全部可重算；整体 `quality_status=FAIL` 和 `first_bad_stage=T2` 属于既有学校质量结果，不是 final 链断裂。

本状态记录的是本轮实现落地，不代表 T3 真实准确率、三校 gold 或最终学校质量已经 verified。

## Remaining

以下属于诊断和质量闭环残留，不再阻塞业务链使用 final：

1. 历史 run reader 仍需显式标记 legacy candidate，不把旧 `02.3`/`04.2` 自动映射为当前 final。
2. 三校真实运行、T3/T4 accuracy 和最终 Word 质量仍按 Plan 07、Plan 13 及其他 active status 验收。

## 完成信号

本项进入 `verified` 前还需：

- route/judge/report 残留扫描证明没有候选被重新接回业务链；
- 关联 Plan 07、状态索引和长期架构/测试文档保持一致。
