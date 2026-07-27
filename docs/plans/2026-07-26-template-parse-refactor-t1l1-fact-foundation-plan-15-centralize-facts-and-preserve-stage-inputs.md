---
status: draft
owner: template-generation
stage: T1L1
topic: fact-foundation-leaf-identity
doc_type: plan
plan_id: T1L1-FACT-FOUNDATION-PLAN-15
source_issue:
  id: T2T3T4-AGENT-ISSUE-15
  doc: docs/plans/2026-07-26-template-parse-refactor-t1l1-fact-foundation-issue-15-leaf-identity-and-split-artifacts.md
previous_plan:
  id: T1L1-INPUT-CONTRACT-PLAN-08
  doc: docs/plans/2026-07-10-template-parse-refactor-t1l1-input-contract-plan-08-l1-projection-bundle-gate.md
  status: verified
related_status:
  - docs/status/active/t1-l1-fact-foundation-and-atom-identity.md
related_discussions:
  - docs/human/t1-l1-fact-foundation-and-stage-views-discussion.md
  - docs/human/t1-l1-source-identity-and-structure-discussion.md
related_plans:
  - docs/plans/2026-07-26-template-parse-refactor-t4-skip-plan-14-remove-required-stage-and-preserve-source-layout.md
  - docs/plans/2026-07-25-template-parse-refactor-stage-standards-plan-03-canonical-gold-stage-projections.md
created: 2026-07-26
last_updated: 2026-07-26
---

# T1/L1 Plan 15：集中事实生产并保持现有阶段输入

> **顶层范围决定：T4 暂缓。本计划不讨论、不设计、不修改、不运行也不验收 T4 的语义、模型、final 或 gold；若当前代码中仍有 T4 stage-input reader，只验证兼容投影未被破坏。**

> **Gold 顺序决定：本计划期间冻结现有 gold、standard 和 projector，只把它们当作回归 oracle。Plan 15 verified 后，才允许 Stage Standards Plan 03 按最终 T1/L1 schema 迁移 gold。**

## 结论摘要

各阶段当前已经有正式输入：

- T2：`01.6_t2_l1_stage_input.json` 和 `02.1_t2_input.json`；
- T3：`03.0_t3_hierarchical_stage_input.json`；
- T4：当前兼容文件 `01.8_t4_l1_stage_input.json`，本轮暂缓；
- T5：L1 引用校验加当前 required finals；
- T6：源 DOCX、T5 final 和当前 L1 identity resolver；
- T7：T6 成品、manifest 和上游 refs。

本轮不是重新设计这些输入，而是把它们背后分散的客观事实统一收口：

```text
source DOCX ─┬─> 01.1 body facts ──────┐
             ├─> 01.2 global facts ────┼─> 01_document_facts 兼容投影
             └─> 01.3 render facts ────┘
                                             ↓
                                    01.5 sealed L1
                                             ↓
                         现有 stage-input projectors
                                             ↓
                         现有阶段输入 shape 保持不变
```

因此需要区分两类“影响”：

1. **直接修改**：T1 producer、render facts producer、L1 builder、stage-input
   projectors、ordered outputs/run manifest、对应 schema/tests/docs。
2. **兼容验证**：T2/T3 语义和模型调用、T5/T6/T7 业务逻辑。它们不应为了本轮改
   output schema 或改用 `source_atom_seq`；只需证明继续接收原来的阶段输入和 final。

下游真正切换到 atom selection、新 locator 或新 T6 resolver 是另一轮能力，不属于
Plan 15。

## Execution Contract

### Target Capability

计划完成后，系统必须具备以下能力：

1. 一次源 DOCX snapshot 稳定产出正文、全局、render 三个 T1 component；每个
   component 有清楚字段边界、source hash、content hash、coverage 和 availability。
2. 当前 `01_document_facts.json` 由三个 component 确定性生成，继续向现有兼容代码
   提供相同字段，但不再是独立事实 producer。
3. L1 把三个 component 封存为唯一 `01.5_l1_input_contract.json`，保留现有八组
   字段，并新增中立的 atom、membership、text-address、locator 四组索引。
4. `source_atom_seq` 只在 L1 增加；当前 `source_seq` 的名称、数值、顺序和粒度完全
   不变。
5. 现有 T2/T3 stage-input projectors 从新的 sealed L1 查询事实，但继续输出迁移前
   的字段、过滤、顺序、图片附件集合和 availability。
6. T5/T6/T7 不切换身份或执行逻辑，只通过完整链回归证明没有被新的 L1
   schema/hash 破坏。
7. 所有 hash 变化都明确区分为 artifact/schema 变化或业务语义变化；不得改 gold
   消除差异。

### Current Baseline

实施前以当前 producer/schema/contract tests 和新生成 artifact 冻结下表；历史运行
目录不能覆盖当前代码事实。

| 层/阶段 | 当前主要输入 | 当前正式输出或阶段输入 | 本轮处理方式 |
| --- | --- | --- | --- |
| T1 | source DOCX/OOXML | `01_document_facts.json` | 拆出三个 component，同时保持兼容投影 |
| L1 | document facts + render facts | `01.5_l1_input_contract.json` | 保留现有八组字段，增加四组中立索引 |
| T2 | sealed L1、全页图 | `01.6`、`02.1`、`02_unit_map.yaml` | projector 内部换事实来源；序列化输入和业务输出保持 |
| T3 | sealed L1、T2 final | `03.0`、`03_element_spec.yaml` | projector 内部使用 membership；序列化输入和业务输出保持 |
| T4 | sealed L1 兼容视图 | `01.8`、当前 T4 输出 | 本轮不处理；只验证兼容或确认 reader 已移除 |
| T5 | L1 ref、当前 required finals | `05_template_spec.yaml` | 不改业务代码；验证 hash/ref 可自动沿同 run 传播 |
| T6 | source DOCX、T5 final、当前 resolver | DOCX + manifest | 不切换 locator/resolver；只做回归验证 |
| T7 | T6 DOCX、manifest、upstream refs | verification report | 不增新判断；只验证完整链未回归 |

当前 L1 实际字段基线固定为：

```text
input_hashes
source_text_index
run_index
source_object_index
source_structure_index
layout_fact_index
visual_page_index
coverage
```

其中 `source_structure_index` 已存在于代码，但现行长期架构的 L1 必备字段表漏列；正式
实施时必须补回 canonical 文档。

### Canonical Artifacts and Entity Budget

本轮只新增三份 T1 component 和四组 L1 索引：

| 实体 | 角色 |
| --- | --- |
| `01.1_body_content_facts.json` | 正文内容、结构、叶子 occurrence 和正文 source order |
| `01.2_global_document_facts.json` | section、header/footer、field、numbering、styles/defaults 和 package facts |
| `01.3_source_render_facts.json` | PDF/page images、page geometry、render provenance、binding 和 availability |
| `source_atom_index` | L1 叶子身份和最小中立事实 |
| `source_membership_index` | L1 容器、结构引用和 ordered atom membership |
| `text_address_index` | L1 文字原子的 raw text、code-point 地址和 text hash |
| `locator_index` | L1 atom 到源 OOXML locator/precondition 的只读技术索引 |

复用：

- `01_document_facts.json`：兼容投影；
- `01.5_l1_input_contract.json`：唯一 sealed L1；
- 当前 T2/T3 stage-input artifact 名称和 shape；
- 当前 T5/T6/T7 final、resolver 和 verifier。

不新增第二份 L1、运行时私有增强事实源、并列身份、查询服务或下游新 output schema。

### T1 Component Contract

三个 component 的公共 envelope 至少包含：

```text
artifact_type
artifact_version
producer
created_at
source_snapshot:
  source_template_sha256
  source_package_identity
content_sha256
coverage
warnings
availability
```

Hash 口径：

- `artifact_sha256` 对实际落盘文件计算，登记在 output index、run manifest 和同 run
  lineage；
- `content_sha256` 对去除 `created_at` 和自身字段后的 versioned semantic payload
  计算，用于跨运行 parity；
- 两者均可重算，不能递归包含自身。

| Component | 必须包含 | 不得包含 |
| --- | --- | --- |
| body | body paragraph/table/row/cell、raw Run、文本/对象/控制 leaf、物理顺序、membership、unknown | unit、element、policy、confidence |
| global | sections、header/footer、fields、breaks、numbering、styles/defaults、settings、跨域引用 | T4 decision、page policy、执行动作 |
| render | PDF/page/image refs+hash、engine/version、page size/order、binding candidate、availability/error | 新 source identity、T2/T3/T4 判断 |

`01_document_facts.json`：

- 只能从三个 component 确定性生成；
- 现有字段在 shadow comparison 中保持深度等价；
- 新增 component refs/hash 和 compatibility projection version；
- 不允许独立更新或成为新增读取入口。

### L1 Field Contract

现有八组字段保留名称和既有语义。新字段固定为：

| 新字段 | 最少字段含义 |
| --- | --- |
| `source_atom_index.atoms[]` | `source_atom_seq`、atom kind、source/part/parent refs、raw text/object/control facts、兼容 refs、`locator_ref`、coverage |
| `source_membership_index` | normalized structure、parent/child、ordered atom refs、空容器、merge/nested 完整性 |
| `text_address_index` | text atom、raw text、`unicode_code_point`、半开区间、length、text hash |
| `locator_index` | atom/locator-ref 映射、source hash、part、OOXML path、parent、run/object/control address、precondition |

原子边界已经固定，不再作为实施待决项：

```text
text
inline_object
control
empty_placeholder
opaque_unknown
```

selection contract 也固定为：

```text
atom
atom_interval
atom_members
text_range
```

Phase 1 需要冻结的是完整 OOXML 类型映射、字段必填性、排序枚举、locator
序列化和错误码，不得重新改变“叶子是原子、容器不是原子、字符用原子内半开区间”的
边界。

### Stage-Input Compatibility Contract

Plan 15 的核心验收不是“下游使用了多少新字段”，而是：

```text
新的 T1/L1 事实底座
  → 现有 stage-input projector
  → 与迁移前相同的阶段输入语义
```

具体要求：

1. T2 `01.6/02.1` 的既有字段、排序、page grouping、clean image 附件集合和 hash
   引用保持；可以由新 atom/membership 索引计算兼容字段，但不把新字段暴露给模型。
2. T3 `03.0` 的 unit roots、hierarchy、source/run/span/object refs 和图片选择保持；
   projector 可以使用新的 membership 避免重建物理关系，但序列化 shape 不变。
3. T4 不新增任何输入；只在当前 reader 仍存在时确认 `01.8` 可由兼容 L1 继续构建。
4. T5/T6/T7 继续读取当前 final 和 resolver。L1 全量 artifact hash 变化可以沿当前
   same-run `input_refs` 自动传播，但不能引发业务字段、执行目标或验证结论变化。

### Non-Goals

1. 不要求 T2/T3/T5/T6/T7 输出 `source_atom_seq` 或 source selection。
2. 不切换 T6 locator/resolver，不做 dual-resolver 或执行 authority cutover。
3. 不删除现有 `source_seq`、`source_ref`、raw/logical Run ID、span/object/page 字段。
4. 不修改 T2 unit、T3 policy、T5 model、T6 动作或 T7 判定语义。
5. 不处理 T4 skip、T4 模型、T4 final、T4 gold 或 T4 准确率。
6. 不迁移 gold、standard、学校答案和 projector；Plan 03 后置。
7. 不引入 T2-B、多 T3 模式、T5 slots/effects、transaction catalog 或其他未来方案。

### Downstream Impact Matrix

| 范围 | 直接改代码 | 需要验证 | 预期业务变化 |
| --- | --- | --- | --- |
| T1 producer | 是 | 三组件完整性和兼容投影 | 无 |
| render facts producer | 是 | PDF/page/image/binding 同源和附件可读 | 无 |
| L1 builder/schema | 是 | 八组旧字段 parity、四组新索引完整性、hash | 新增事实字段；无下游语义 |
| output/run manifest | 是 | 新文件登记、artifact/content hash、lineage | 产物清单增加 |
| T2 stage-input projector | 是 | `01.6/02.1` 语义 payload 和附件集合 parity | 无 |
| T2 模型与 materializer | 否 | fixed replay 输出 parity | 无 |
| T3 stage-input projector | 是 | `03.0` hierarchy/source/run/span/object parity | 无 |
| T3 模型与 materializer | 否 | fixed replay final parity | 无 |
| T4 | 否 | 仅兼容读取或零-reader 扫描 | 无 |
| T5 | 原则上否 | L1 hash/ref 自动传播、final parity | 无 |
| T6 | 否 | 当前 resolver target/action/final DOCX 回归 | 无 |
| T7/POST_T6 | 否 | 当前 fresh verification 和 first-bad-stage 回归 | 无 |
| fixture/replay | 可能 | 只更新被 artifact hash/schema 合法影响的冻结输入 | 不改期望业务答案 |
| gold | 否，本轮冻结 | 文件零改动检查 | Plan 15 后另行迁移 |

只有出现以下情况才允许扩大直接修改范围：

- 下游硬编码拒绝 additive L1 schema/version；
- 下游没有使用 same-run ref，而是硬编码旧 L1 hash；
- stage-input projector 无法在保持现有 shape 的情况下从新 L1 构造输入。

出现时必须先记录 observed caller 和最小失败证据，再更新本 plan；不能预先假定所有下游
都要迁移。

### Implementation Phases

#### Phase 0：冻结现行输入和输出

- [ ] 登记 T1/render/L1 producer 与 stage-input projector。
- [ ] 保存三校当前 `01_document_facts`、L1 八组字段、`01.6`、`02.1`、`03.0`。
- [ ] 保存 T2/T3/T5 final、T6 action/target/DOCX、T7 report 作为兼容回归证据。
- [ ] 记录模型实际收到的 JSON 白名单、图片附件顺序和 hash。
- [ ] 区分动态字段（时间、run path、artifact hash）和业务语义字段。

Stop gate：阶段输入真实 shape 或模型附件集合尚未冻结时，不开始拆 producer。

#### Phase 1：冻结 T1/L1 schema

- [ ] 固定三组件 envelope、事实域、版本、source snapshot 和 hash 范围。
- [ ] 固定五类 atom 的完整 OOXML 映射、物理顺序和 unknown fallback。
- [ ] 固定 structure/membership、text address、selection、locator 和错误码。
- [ ] 固定 L1 现有八组字段的 compatibility projection。
- [ ] 建立禁止语义字段和 schema 正反例 fixture。
- [ ] 更新 canonical architecture/testing 中遗漏的 `source_structure_index` 和批准后的字段。

Stop gate：locator 序列化或完整 OOXML 枚举未冻结时可以阻止 producer 实施，但不能重新
打开已经确定的原子粒度。

#### Phase 2：产出三个 T1 component

- [ ] source inspector 输出 body/global component，共用一个 source snapshot。
- [ ] render pipeline 输出 render component 和正式 PDF/PNG/SVG refs/hash。
- [ ] ordered outputs、debug index、artifact paths、run manifest 登记 `01.1/01.2/01.3`。
- [ ] `01_document_facts` 改为兼容 projector，不保留第二 producer。
- [ ] 覆盖 no-render、partial binding、unknown、empty cell、field、floating object 场景。

Gate A：

- 三组件 source hash 一致；
- 旧 `document_facts` 语义投影零非预期差异；
- 所有 source leaf 被记录或显式 unknown/excluded；
- render 附件 hash 可重算，失败时 availability/error 明确。

#### Phase 3：构建 sealed L1

- [ ] L1 读取并校验三个 component source/hash。
- [ ] 生成 atom、membership、text-address、locator 四组索引。
- [ ] 生成 `source_seq ↔ ordered source_atom_seq[] ↔ current run/object/source refs` 映射。
- [ ] 保留现有八组字段的名称、结构和语义。
- [ ] 增加 eligible/atomized/unknown/unbound/duplicate/missing coverage ledger。
- [ ] 明确 artifact hash 与 content hash，不制造自引用。

Gate B：

- atom 顺序连续、确定、唯一；
- 现有 `source_seq` 不变且均有可解释 atom 映射；
- membership、text-address、locator 正反例通过；
- 八组旧字段 compatibility projection 零非预期差异；
- 相同输入的 semantic payload/content hash 稳定。

#### Phase 4：改造 projector，保持阶段输入

- [ ] T2 projector 从新的 L1 查询事实，输出迁移前等价的 `01.6/02.1`。
- [ ] 保持 T2 模型可见 JSON 和 actual image attachments 不变。
- [ ] T3 projector 使用 membership 构造现有 hierarchy，输出迁移前等价的 `03.0`。
- [ ] 保持 T3 模型可见 JSON、unit 图片选择和 materializer 输入不变。
- [ ] 当前 T4 reader 仍存在时只验证兼容构建，不做任何 T4 新设计。

Gate C：

- T2/T3 stage-input semantic diff 为零；
- 动态 path/hash 差异被单独解释；
- 模型附件数量、顺序、内容 hash 不变；
- T2/T3 fixed replay final 无非预期业务差异。

#### Phase 5：下游兼容验证，不做下游迁移

- [ ] T5 使用新 L1 same-run hash 运行，证明 units/elements/global 业务内容不变。
- [ ] T6 继续使用当前 resolver，比较 action、target、manifest 和最终 DOCX。
- [ ] T7/POST_T6 继续使用当前 verifier，比较 status、first bad stage 和 findings。
- [ ] 扫描 T5/T6/T7 是否因 additive schema/version 或硬编码旧 hash 失败。
- [ ] 只修实际暴露的兼容读取，不加入 atom/locator 切换。

Gate D：

- T5/T6/T7 不需要新 output schema；
- T6 当前 action/target/observed effect 无非预期变化；
- T7 当前 required checks 和 owner 归因无非预期变化；
- 没有为了通过迁移而修改业务规则或 gold。

#### Phase 6：真实闭环与 gold handoff

- [ ] 三校 fixed replay 完整链运行。
- [ ] 三校真实 source DOCX 完成 T1/L1/真实 render 和最终 DOCX L4 验证。
- [ ] 扫描第二 T1/L1 producer、stage projector 绕回 DOCX、未登记 component。
- [ ] 更新 canonical architecture/testing、artifact inventory 和运行说明。
- [ ] 产出旧 T1/L1 字段到新 component/index 的映射，交给 Plan 03。
- [ ] 证明本轮 gold、standard 和 projector 零改动后，解除 Plan 03 阻塞。

### Verification Matrix

本计划最低完成等级为真实 DOCX/render 的 L4。由于模型可见输入必须保持不变，正常不需要
新增 live provider 验证；如果 Gate C 发现 payload 或附件发生变化，则停止并重新审批
范围，不能把 live 差异当作本轮默认工作。

| Gate | Command / Evidence | Required Result |
| --- | --- | --- |
| static | `rg` producer/consumer/projector、禁止语义字段、旧独立 producer | 新事实只在 T1/L1；stage projector 不绕回 DOCX |
| unit | `uv run pytest tests/unit/test_template_generation_input_contract.py tests/unit/template_generation_agent -q` 加新增 T1/L1 聚焦测试 | 三组件、atom/membership/text/locator、旧字段 parity 通过 |
| contract | `uv run pytest tests/contract/test_template_generate.py tests/contract/test_template_generate_agent_replay.py tests/contract/test_template_generation_standard_judge.py -q` | 现有阶段输入/final 合同继续通过 |
| stage-input parity | 三校迁移前后 `01.6/02.1/03.0` normalized semantic diff | 业务字段、顺序、附件集合零差异 |
| downstream parity | 三校 T2/T3/T5 finals、T6 action/target/DOCX、T7 report | 无非预期业务差异；只允许已解释 hash/path 变化 |
| product run | `uv run docfit template verify --school <id> --template <source.docx> --template-version <v> --ai replay --replay <frozen.json> --out <run>` | 三组件、L1、真实 render、现有完整链均可用 |
| gold freeze | git diff/semantic hash 检查 gold、standards、projectors | 本轮零修改 |

### Completion Signals

1. `01.1/01.2/01.3` 是正式 artifact，并进入 ordered outputs/run manifest。
2. `01_document_facts` 已是确定性兼容投影，不存在第二 producer。
3. L1 保留现有八组字段并新增四组中立索引，coverage 无静默缺口。
4. 当前 `source_seq` 名称、数值、顺序和粒度不变。
5. `01.6/02.1/03.0` normalized semantic payload 和模型附件集合保持。
6. T2/T3/T5/T6/T7 当前业务 final、执行和验证无非预期变化。
7. T4 没有新增工作；gold、standard、projector 零修改。
8. 三校 fixed replay、真实 DOCX/render 和残留扫描完成。

### Anti-Degradation Rules

1. 不以新文件存在代替兼容投影、coverage 和真实 consumer 验证。
2. 不要求下游“为了证明新字段有用”而改变现有业务 output。
3. 不把 `source_seq` 改粒度或改编号。
4. 不让 stage projector 重读 DOCX 或建立第二事实源。
5. 不通过改 gold、批量接受 snapshot 或改变模型输入消除差异。
6. 不把 T6 locator 切换、T4 skip 或 T2/T3 质量优化夹带进本轮。

### Rollout and Rollback

```text
三组件 shadow write
→ 旧 document_facts 兼容投影 parity
→ L1 新索引 additive build
→ T2/T3 projector shadow parity
→ projector 切换事实来源
→ T5/T6/T7 兼容回归
→ 删除独立旧 producer
→ gold Plan 03 handoff
```

任一 Gate A–D 失败时，旧 producer/projector 继续作为权威；新 component/L1 index 只保留
为诊断产物，不扩大到下游身份或执行迁移。

### Residual Policy

1. 三组件已产出但旧独立 producer 仍是权威：`implemented_in_part`。
2. L1 新索引不完整或靠大量 unknown 吞掉：`blocked_by=fact_coverage_gap`。
3. stage-input semantic diff 非零：停止在 Gate C，修 projector；不改下游模型或 gold。
4. T5/T6/T7 出现真实兼容失败：只修该 reader 对 additive schema/hash 的读取，超出此范围
   重新审批。
5. T6 需要切 locator/resolver：创建后续 identity-consumer issue/plan，不扩写 Plan 15。
6. real render 不可用：`BLOCKED_NEEDS_LOCAL_VALIDATION`，不能标 verified。

## Approval Checklist

- [ ] 同意 Plan 15 只集中 T1/L1 事实并保持现有 stage input。
- [ ] 同意三个 T1 component 和 `01_document_facts` 兼容投影。
- [ ] 同意 L1 保留八组旧字段、增加四组新索引，但本轮不要求下游输出新 identity。
- [ ] 同意 T6 resolver/locator 切换另立后续计划。
- [ ] 同意 T4 暂缓、gold 在 Plan 15 verified 后再迁移。

