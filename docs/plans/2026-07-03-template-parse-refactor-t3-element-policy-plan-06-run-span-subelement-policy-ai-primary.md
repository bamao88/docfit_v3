---
status: draft
owner: template-generation
stage: T3
topic: element-policy
doc_type: plan
plan_id: T3-ELEMENT-PLAN-06
source_issue:
  id: T3-ELEMENT-ISSUE-06
  doc: docs/plans/2026-07-02-template-parse-refactor-t3-element-policy-issue-06-placeholder-span-granularity.md
also_resolves:
  id: T3-ELEMENT-ISSUE-05
  doc: docs/plans/2026-07-01-template-parse-refactor-t3-element-policy-issue-05-inline-style-instruction-fixed-merge.md
previous_plan:
  id: T3-ELEMENT-PLAN-04
  doc: docs/plans/2026-07-01-template-parse-refactor-t3-element-policy-plan-04-instruction-manual-confusion.md
related_direction:
  doc: docs/plans/2026-07-03-template-parse-refactor-ai-primary-staged-migration-proposal.md
created: 2026-07-03
last_updated: 2026-07-03
---

# T3 元素策略 Plan 06：run/span 子元素模型 + AI 为主的元素识别（综合解决 issue-05 / issue-06）

## Summary

issue-05（行内括号格式说明并入非 instruction 元素，8 处残留）与 issue-06（□/××/……
placeholder 缺子 span 粒度，66 个非删除元素）共享同一根因：**T3 没有子元素 span 模型，
policy 只能整 element 赋值**。按 AGENTS.md 最高优先级纪律，本 plan 不做逐症状补丁，
直接落 run/span 级能力，并按迁移提案把 T3 转「AI 为主、确定性校验兜底」。

验收口径：

```text
T3 span 能力成立 = 元素内部可表达 {label 保留、layout spacer 删除、
sample value 替换为槽、inline instruction 删除}；issue-05 的 8 处与
issue-06 的代表性残留在最终 DOCX 拼接文本中清零；反例不误删；
AI span 观察可执行并进入 merged。
```

## Implementation Plan

### Phase 1：span 数据模型

```text
src/docfit/template_generation/artifacts.py (build_element_spec)
src/docfit/template_generation/generation_model.py

改动：
  - element 新增 spans[]：{span_id, span_type, policy, text, raw_run_ids,
    char_range(在 run 内的字符区间，跨 run 时逐 run 切分), origin, confidence}
  - span_type 枚举：label / layout_spacer / sample_value / input_slot /
    inline_instruction / content
  - 依据：T1 已有 raw_run_ids/logical_run_ids/text_facts.parenthesized_segments
    （issue-05 证据：p_0003 的 r[2] 标题与 r[3] 格式说明本就是不同 run）。
  - element 级 policy 保留（向后兼容），spans 为空时行为与现状一致。
```

完成信号：

```text
element_spec schema 含 spans[]；存量单测不回归。
```

### Phase 2：确定性 field-line parser（校验方 + 兜底）

```text
src/docfit/template_generation/generation_model.py

改动：
  - 新增字段行解析：按 run 事实 + 字符模式切分
    [leading □+ | label(含内部 □ spacing 归一) | ：| sample(××/20×+/……) ]
    与尾随括号格式说明（复用 parenthesized_segments + 字体/字号突变证据）。
  - 输出确定性 spans[]，origin=deterministic_parser。
  - 反例防护：论文（设计）、卷（期）、百分制、真实校名等业务括号
    与正文内容不产生 inline_instruction/sample span。
```

完成信号：

```text
issue-06 代表样本 □□□□□□学□□号：20×××××××××× 解析为
[layout_spacer, label(学号：), sample_value]；
issue-05 代表样本 湖 南 农 业 大 学（一号华文行楷加粗）解析为
[content, inline_instruction]；反例样本零误切。
```

### Phase 3：AI 为主的 span 观察与 bridge 升级

```text
src/docfit/template_generation/agent/observation_loop.py
src/docfit/template_generation/agent/observation_bridge.py
src/docfit/template_generation/agent/overlay.py

改动：
  - T3 AI prompt/schema 升级为 span 粒度观察（evidence 已含
    raw_run_ids/style_details，输入具备）；观察项含 span_type + 处置。
  - bridge 在 plan-09 Phase 2（policy 映射、低置信不硬阻断、
    source_seq_refs 绑定）基础上，接受 span 级 proposal 并 patch
    element.spans[]，origin=ai_observation。
  - 与确定性 parser 逐 span 比对：一致 -> confirmed；分歧 ->
    conflict/manual_review，该 span 回退 deterministic 结果（迁移提案回退语义）。
```

完成信号：

```text
hunannongye replay：T3 span proposal > 0 且有 accepted；
03.2_t3_merged_element_spec.yaml 出现 origin=ai_observation 的 span；
分歧样本进 manual_review 且数量可审计。
```

### Phase 4：T6 执行契约

```text
src/docfit/template_generation/plan.py
src/docfit/template_generation/executor.py

改动：
  - spans 驱动动作：layout_spacer/inline_instruction -> 既有
    remove_instruction_text run/span 级删除（plan-03 已具备 run 级基础）；
    sample_value -> 新增 replace_span_with_slot 动作（删除示例文本并在原位
    创建 SDT 填写槽），label -> 保留并归一（学□□号： -> 学号：）。
  - 动作携带 raw_run_ids + char_range，executor 精确执行。
```

完成信号：

```text
build_manifest 出现 replace_span_with_slot；cover 学号行最终 DOCX 中
无 □ 残留、无示例学号、有可填写槽。
```

### Phase 5：门禁与全量扫描

```text
1. issue-05 门禁：8 处格式说明残留在最终 DOCX 拼接文本清零；
   反例（论文（设计）/卷（期）/百分制/固定标题校名）保留。
2. issue-06 门禁：代表性 cover 字段无 □/×× 残留；66 元素扫描口径复跑，
   非删除 placeholder-like 元素清零或逐条给出保留理由。
3. 对照三校 element_expectations / run_span_ledger 标准
   （stage-standards plan-02 已实现）验证 span 处置。
4. 三路线评测：T3 code_raw vs ai_raw vs merged 的 span 级 diff 可解释；
   ai_raw ≥ code_raw 后才按迁移提案晋升 AI 为主默认开启。
5. 验收含全量/代表性扫描 + 反例验证，不以 PASS/SIGNABLE 为完成证据
   （AGENTS.md 纪律）。
```

## Out of Scope

```text
1. T4 明点与单元分页 —— 归 plan-10 / plan-11。
2. T2 单元边界 —— 保持 merge。
3. 表格单元格内部的 span 化（若扫描发现表格残留，另立 issue）。
```

## 变更记录

| 日期 | 说明 |
| --- | --- |
| 2026-07-03 | 初稿：五阶段落地 run/span 子元素模型与 AI 为主 T3——span schema、确定性 parser、AI span 观察、T6 替换契约、全量门禁；综合解决 issue-05/06 |
