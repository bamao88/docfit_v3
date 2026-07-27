---
status: impact_confirmed
owner: template-generation
stage: T1L1
topic: fact-foundation-leaf-identity
doc_type: issue
issue_id: T2T3T4-AGENT-ISSUE-15
issue_sequence: 15
previous_issue:
  id: T2T3T4-AGENT-ISSUE-08
  doc: docs/plans/2026-07-03-template-parse-refactor-t2t3t4-agent-proposal-issue-08-t1-l1-input-contract.md
  status: closed
previous_optimization:
  doc: docs/plans/2026-07-10-template-parse-refactor-t1l1-input-contract-plan-08-l1-projection-bundle-gate.md
  summary: Plan 08 已完成 sealed L1、run/object/page identity、shared hash 和旧输入退出，但没有定义三组件 T1、叶子级 source_atom_seq、统一成员关系与 locator/text-address 契约。
next_plan: docs/plans/2026-07-26-template-parse-refactor-t1l1-fact-foundation-plan-15-centralize-facts-and-preserve-stage-inputs.md
created: 2026-07-26
last_updated: 2026-07-26
related_status:
  - docs/status/active/t1-l1-fact-foundation-and-atom-identity.md
related_discussions:
  - docs/human/t1-l1-fact-foundation-and-stage-views-discussion.md
  - docs/human/t1-l1-source-identity-and-structure-discussion.md
related_code:
  - src/docfit/template_generation/source_tree.py
  - src/docfit/template_generation/agent/packet.py
  - src/docfit/template_generation/input_contract.py
  - src/docfit/template_generation/stage_inputs.py
  - src/docfit/template_generation/identity_resolver.py
  - src/docfit/template_generation/executor.py
  - src/docfit/template_generation/verifier.py
---

# T1/L1 Issue 15：事实分域、叶子身份和执行定位仍未形成完整底座

> **范围覆盖：T4 本轮暂缓。本 issue 不要求设计、修改或验收 T4 语义和输出；只要求 T1/L1 改动不破坏执行时仍存在的兼容读取。gold 只作为迁移回归基线，必须在 T1/L1、stage-input compatibility 和下游不变验证完成后另由 Stage Standards Plan 03 迁移。**

## 发生了什么

Plan 08 已经解决“所有阶段读取同一份 sealed L1”的问题，但当前 sealed L1 仍建立在一个较粗的 T1 事实包和多套定位字段上：

- T1 正式只写 `01_document_facts.json`，正文、全局事实和 render/page 事实没有形成三个稳定 component；
- 当前 `source_seq` 是可见正文流条目的稳定身份，粒度高于需要独立追踪的文字、对象、控制节点和空占位；
- raw/logical Run、object、field、span、source ref 和 page binding 可以回查，但尚无一套覆盖所有叶子内容的统一身份；
- T6 依赖 `source_seq + raw_run_id + char_range + source_ref` 等组合定位，缺少统一、可验证、带 source precondition 的 locator map；
- 当前 L1 已有 `source_structure_index`，但长期架构的 L1 必备内容表漏列该字段，完整阶段输入 shape 也仍需以代码、schema、测试和当次 artifact 为准。

这意味着当前链路能运行，但还不能稳定回答以下问题：

1. 源 Word 中最底层、可独立选择和执行的内容究竟是哪一个对象；
2. 正文、全局 part、图片、字段、分页控制和 unknown 是否使用同一套叶子身份；
3. 下游一个选择如何从业务身份确定性展开到 OOXML locator 和 page/bbox；
4. T1/L1 schema 升级后，怎样让现有阶段输入字段保持不变，并区分需要修改的 projector
   与只需要兼容验证的下游业务代码。

## Expected vs observed

### Expected

1. T1 的 canonical 事实由三个稳定 component 组成：
   - `01.1_body_content_facts.json`：正文内容流、结构成员和正文内叶子事实；
   - `01.2_global_document_facts.json`：section、header/footer、field、numbering、style/default 和 package 级事实；
   - `01.3_source_render_facts.json`：同源 PDF、页面图、page/bbox、render engine/version、binding 和 availability；PDF/PNG/SVG 是被该 JSON 以 hash 引用的二进制 artifact。
2. 现有 `01_document_facts.json` 在迁移期继续存在，但只能是由三个 component 确定性生成的兼容投影，不得成为第四份独立事实源。
3. L1 继续只发布一份 sealed `01.5_l1_input_contract.json`，保留当前字段名称和语义，并新增：
   - `source_atom_index`
   - `source_membership_index`
   - `text_address_index`
   - `locator_index`
4. 叶子级身份固定为 `source_atom_seq`。现有 `source_seq` 的名称、数值、排序和粒度全部保持不变；L1 保存 `source_seq ↔ ordered source_atom_seq[]` 映射。
5. 原子边界固定为可独立引用、选择、验证和执行的 OOXML 叶子 occurrence，类型至少覆盖 `text`、`inline_object`、`control`、`empty_placeholder` 和 `opaque_unknown`。
6. paragraph、table、row、cell、header/footer、text box、content control 等容器通过结构引用和有序 membership 表达，不与 `source_atom_seq` 竞争业务身份。
7. 单原子、连续区间、非连续成员和文字原子内半开字符区间使用统一 selection contract；字符单位固定为 Unicode code point，并绑定源文字 hash。
8. 每个可执行原子通过唯一 `locator_ref` 解析到 source hash、part、OOXML path、父容器、run/object/control 地址和执行前置条件；page/bbox/render target 只表示视觉位置。
9. T2/T3 继续读取现有稳定阶段输入文件；这些文件由 sealed L1 的 projector
   确定性生成，运行时对象不能形成未落盘的第二事实源。
10. 本轮只替换分散事实的 producer 和 stage-input projector，不要求
    T2/T3/T5/T6/T7 改用 `source_atom_seq`、selection 或新 locator。

### Observed

1. 当前 T1 `document_facts` 同时承载 `body_flow`、`runs`、`data.*`、`indexes` 和 warnings，没有三个 component 的独立 schema/hash。
2. render facts 主要封装在 agent/render packet 和 L1 `visual_page_index` 中，不是与正文/全局事实并列的 T1 component。
3. 当前 L1 artifact version 为 `2.0`，正式字段为：
   - `input_hashes`
   - `source_text_index`
   - `run_index`
   - `source_object_index`
   - `source_structure_index`
   - `layout_fact_index`
   - `visual_page_index`
   - `coverage`
4. 当前 L1 不生产 `source_atom_seq`、统一 selection、membership、text address 或 locator index。
5. T2/T3 已有稳定阶段输入和 projector；T5–T7 已按 same-run L1 hash/final refs
   工作，因此原则上不需要改业务 schema。
6. 给 L1 正式增加字段会改变完整 artifact hash，并沿 T2–T7 `input_refs`、lineage 和
   run manifest 自动传播；这主要影响冻结 fixture/hash 对比，不等于下游业务逻辑都要迁移。

## 疑似根因

1. Plan 08 的目标是统一现有事实输入，没有把“源内容最小可执行叶子”作为独立 schema 问题处理。
2. 当前模型以正文流和 Run 为主要入口，物理容器、语义选择和执行定位的边界仍部分重叠。
3. render、结构和执行 resolver 在不同模块中逐步补齐，尚未由一个 component/hash/identity 契约统一约束。
4. 现有 gold、fixture 和 replay 已绑定旧 L1/T1 shape，使直接替换 schema 容易制造假回归或诱导自动改写 gold。

## 影响确认

| 范围 | 影响等级 | 已确认影响 |
| --- | --- | --- |
| T1 producer / ordered outputs | 极高 | 需要新增三个 component、独立 schema/hash、兼容 bundle 和输出索引 |
| render packet | 高 | 要成为 `01.3` 的 producer/兼容投影来源，二进制引用和同源 hash 必须稳定 |
| L1 builder | 极高 | schema/version/hash 改变；新增四组索引并保持八组现行字段语义 |
| T2 stage-input projector | 中 | 改为从新 L1 构造现有 `01.6/02.1`；序列化语义和模型附件保持 |
| T2 业务逻辑 | 兼容验证 | 不修改模型、materializer 或 final schema；fixed replay 证明不变 |
| T3 stage-input projector | 中 | 可用新 membership 构造现有 `03.0`；序列化语义保持 |
| T3 业务逻辑 | 兼容验证 | 不修改模型、materializer 或 final schema；fixed replay 证明不变 |
| T4 | 兼容边界 | 不做语义修改、live、gold 或验收；只防止当前 reader 因共享 schema 改动而崩溃 |
| T5 | 兼容验证 | same-run L1 hash/ref 自动传播；不改变 unit/element/global 业务语义 |
| T6 | 兼容验证 | 继续使用当前 resolver；不切新 locator，只验证 action/target/DOCX 不变 |
| T7 / POST_T6 | 兼容验证 | 继续使用当前 verifier，证明 status/findings/owner 不回归 |
| tests/replay/run bundle | 高 | schema fixture、snapshot、input hash 和 artifact inventory 均需更新 |
| gold | 延后 | 本轮冻结为旧行为回归 oracle，不修改答案或 projector；待本轮 verified 后由 Plan 03 迁移 |

## 验收门禁

1. 三个 T1 component 与旧 `01_document_facts.json` 兼容投影在三校真实源 DOCX 上可重算、同源且无事实丢失。
2. 每个 eligible 叶子恰好映射一个 `source_atom_seq`；unknown/unbound 明确计数和原因，不能静默遗漏。
3. 现有 `source_seq` 兼容投影逐字段等价，不重新编号，不改变下游既有业务输出。
4. 四类 selection 均能确定性展开并经过空选择、重复成员、跨 source、越界和 text hash 反例。
5. T2 `01.6/02.1`、T3 `03.0` 的 normalized semantic payload 和真实图片附件集合保持不变。
6. T2/T3/T5/T6/T7 的现行业务 final、T6 action/target/DOCX 和 T7 report
   在固定 replay 下无非预期差异；hash/lineage 变化必须被解释为 schema 升级。
7. T4 只做兼容读检查，不进入本轮完成质量统计。
8. 当前 gold 文件和答案零改动；只有本 issue 对应 plan 验证完成后，Stage Standards Plan 03 才能开始 schema/projector/gold 切流。
