---
status: impact_confirmed
owner: template-generation
stage: T4T5T6T7POST_T6
topic: t4-production-skip
doc_type: issue
issue_id: T2T3T4-AGENT-ISSUE-14
issue_sequence: 14
severity:
  - P1
previous_issue:
  id: T2T3T4-AGENT-ISSUE-13
  doc: docs/plans/2026-07-26-template-parse-refactor-t4-ai-only-issue-13-multi-route-authority-conflict.md
previous_optimization:
  doc: docs/plans/2026-07-26-template-parse-refactor-t4-ai-only-plan-13-single-ai-final.md
  summary: Plan 13 已把 T4 收敛为唯一 AI final，但该 final 没有形成 Word 版式动作。
next_plan: docs/plans/2026-07-26-template-parse-refactor-t4-skip-plan-14-remove-required-stage-and-preserve-source-layout.md
created: 2026-07-26
last_updated: 2026-07-26
related_status:
  - docs/status/active/t4-production-skip.md
---

# T4 Issue 14：copy-first 路线中的 T4 没有执行效果

## 问题摘要

当前可填写模板从学校源 DOCX 整包复制后做局部减法和插槽构建。源 package 已包含
section、页面设置、页眉页脚、页码、styles 和 numbering；T4 AI 虽发布
`04_global_spec.yaml`，但 T6 plan/executor 不从中生成版式动作。

## Expected vs Observed

Expected：

1. 生产阶段只有在其输出被下游消费并改变或约束业务结果时才是 required stage。
2. copy-first 路线默认保留源 DOCX 全局版式；源版式事实和身份由 T1/L1 记录。
3. T2 单元与源 Word section 的绑定可以由共同的 source identity/range 确定性完成。
4. 最终 Word 必须重新观察并证明源版式没有被局部编辑意外破坏。

Observed：

1. T4 AI raw/final 被生成、验证并参与 T5 availability。
2. T5 保存 `global_spec` 和 unit-section profile refs，但 T6 不消费这些字段产生
   page setup、header/footer、page numbering 或 numbering OOXML 动作。
3. T4 失败可以阻塞 T5/T6，即使源 DOCX 已被正确复制且全局版式无需重建。
4. 逐页视觉观察和三校 T4 gold 不能证明最终 Word 实际消费了 T4。

## 根因

T4 的原始目标来自“识别后重建全局版式”的假设，而当前产品选择的是“复制可信源模板并
保护其版式”。阶段目标与执行架构不一致，导致 T4 成为无因果执行效果的 required gate。

## 影响范围

- 生产编排和 AI provider 仍执行 T4 文本/视觉调用。
- 输出树、run manifest、CLI/inspect 仍声明 `01.8` 和 `04_*` 产物。
- T5 签名、availability 和 unit-section binding 仍依赖 T4 final。
- verifier、judge、route-eval、stage cards 和标准仍把 T4 视为 required stage。
- 三校 `t4_global_layout.standard.yaml` 仍作为阶段标准存在。
- T6/T7 缺少以 L1 为基线的源版式 preservation 对账。

## 验收门禁

1. 完整生成不调用 T4 AI，不写 T4 生产产物，T4 不参与 availability。
2. T5 只依赖 L1、T2 final 和 T3 final；unit-section binding 使用 L1 稳定身份/range。
3. T6 明确整包复制并保护源 section/page/header/footer/PAGE/styles/numbering。
4. T7 对最终 DOCX fresh observation 做源版式 preservation 对账。
5. CLI、judge、gold、manifest、测试和文档不再把 T4 缺失当成失败。
6. 历史 T4 artifact 不能被任何生产消费者读取。
