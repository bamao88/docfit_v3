---
status: draft
owner: template-generation
stage: T2
topic: unit-recognition
doc_id: T2-UNIT-DATA-CONTRACT-01
created: 2026-06-26
last_updated: 2026-06-26
source_plan:
  id: T2-UNIT-PLAN-02
  doc: docs/plans/template-parse-refactor-t2-unit-recognition-plan-02-post-phase2-residual-fix.md
source_issue:
  id: T2-UNIT-ISSUE-02
  doc: docs/plans/template-parse-refactor-t2-unit-recognition-issue-02-post-phase2-residuals.md
---

# T2 单元识别数据流转说明

## 0. 怎么读这份文档

这份文档不是字段大全。它只回答三个问题：

```text
1. 当前代码里，T2 数据实际怎么流。
2. Plan 02 准备新增或修改哪些数据流转点。
3. 这些新增点影响哪里，能不能解决 Issue 02 里的真实问题。
```

状态标记：

| 标记 | 含义 |
| --- | --- |
| 当前已有 | 当前代码已经存在 |
| 计划修改 | 当前已有相近逻辑，但本轮要改变判断、字段或消费方式 |
| 计划新增 | 当前代码没有，本轮要新增 |

反引号里的英文通常是代码函数、字段、文件名或枚举值，保留英文是为了和实现对得上。

## 1. 当前真实数据流

这是当前代码已经在跑的 T2 数据流。

```text
T1 document_facts
  ↓ source_tree_from_document_facts()
source_tree
  ↓ build_template_structure_candidates()
template_structure_candidates
  ↓ build_unit_map()
unit_map
  ↓ verify_template_parse_build()
verification_report
```

展开看，当前 `build_template_structure_candidates()` 内部主要是：

```text
source_tree
  ↓ _body_entries()
entries
  ↓ _boundary_anchors()
boundary anchors
  ↓ _label_boundaries()
labeled anchors
  ↓ _infer_units() 根据 anchor 到下一个 anchor 生成 unit range
structure_candidates.units
```

当前关键步骤：

| 步骤 | 当前函数/产物 | 当前做了什么 | 当前限制 |
| --- | --- | --- | --- |
| 读取 T2 条目 | `_body_entries()` | 从 `source_tree.layers.body_flow` 取可见文本条目 | 只做过滤，不做语义判断 |
| 派生结构信号 | `_structural_signals()`、`debug.t2_derived_signals_by_source_seq` | 从 T1 原子事实派生 TOC、说明文字、空行、标题等信号 | 信号主要用于本阶段判断和 debug，缺少统一字段消费契约 |
| TOC block | `_segment_toc_blocks()`、`_toc_block_anchor()` | 先锁住主目录块，避免 TOC 条目被当正文边界 | 只按 TOC 建模，`图目录` / `表目录` 仍会混到 `toc` |
| 边界识别 | `_boundary_anchors()`、`_boundary_decision()` | 用 heading、break、text properties、keyword 等判断单元边界 | 没有独立的 `canonical_label_hint` 和 `instruction_class` |
| 标签识别 | `_label_boundaries()` | 把边界映射到 core/custom/other | duplicate core 规则偏粗，第二次 core 容易被降 custom |
| 单元范围 | `_infer_units()` | 用当前 anchor 到下一个 anchor 切 unit range，并消费 TOC block end | 没有全局 ownership audit，不知道哪些关键 source_seq 无 owner |
| unit_map 转换 | `build_unit_map()` | 把 structure candidates 转成下游正式 `unit_map` | 不消费 range audit，因为当前没有 audit |
| T2 验证 | `_verify_t2_unit_map()` | 查 `units`、`body_main`、`page_start`、flags | 不检查 expected source_seq / critical unowned |
| 指标脚本 | `scripts/t2_metrics.py` | 当前只检查三校 TOC coverage 和 TOC leak | 不检查最终 unit label/range 是否正确 |

当前可以确认：

```text
1. TOC coverage 已经能 PASS。
2. T2 派生信号和 TOC block 已经存在。
3. unit_map 已经是 T3/T4/T5 的正式输入。
4. 但 range ownership、expected source_seq、front/body/back 状态机还没有形成闭环。
```

## 2. 当前断层在哪里

Issue 02 的核心不是“前面没有生产任何东西”，而是这些地方没有闭环：

| 断层 | 当前表现 | 为什么影响交付 |
| --- | --- | --- |
| TOC 指标只覆盖目录条目 | 三校 TOC coverage PASS，但湖南 `abstract_cn` 仍缺失 | TOC PASS 不能证明最终 unit_map 正确 |
| debug 不等于 gate | debug 里能看到 TOC block 和信号，但 verifier 不看 expected source_seq | 问题可能只停在调试信息里，不影响 `first_bad_stage` |
| 没有 range audit | 湖南 seq 50-64 无 owner，南农 seq 35-36 无 owner | 关键段落无人认领时没有统一门禁 |
| 目录类 block 没拆类型 | 北大 `图目录` / `表目录` 仍在 `toc` | 下游无法按图目录/表目录生成策略处理 |
| 边界 hint 不够前置 | 湖南 `□□摘□要...`、南农 `附 录...` 不能稳定成边界 | label 阶段再强也拿不到没形成的 boundary |
| instruction 只有布尔判断 | 标题括注和纯说明文字容易混淆 | 核心标题可能被误伤，纯说明也可能被误切 |
| 没有正文状态机 | 北大正文 Heading 1 被切成多个 top-level custom | `body_main` 范围错误，后续 T3/T4 都会错 |
| duplicate core 规则过粗 | 北大后置 `参考文献` 降成 custom | 真后置单元无法按标准 unit 处理 |

## 3. Plan 02 引入的增量

下面是本轮计划新增或修改的内容。重点看“影响面”，这决定了改动会传到哪里。

| 编号 | 变更 | 状态 | 生产什么 | 谁消费 | 影响面 |
| --- | --- | --- | --- | --- | --- |
| D1 | expected contract loader | 计划新增 | 三校 expected units / expected source_seq / allowed unowned 配置 | 单测、`scripts/t2_metrics.py --unit-ranges`、验证器 | 把真实模板预期写成统一门禁 |
| D2 | `canonical_label_hint` 前移到边界阶段 | 计划修改 | 每个候选标题的标准 label hint | 边界评分、标签识别、range audit | 解决核心标题没形成 boundary 的问题 |
| D3 | `instruction_class` 替代单一 instruction bool | 计划修改 | `pure_instruction` / `title_with_format_annotation` 等分类 | 边界否决、open question、元素策略 | 区分“标题带格式说明”和“纯说明文字” |
| D4 | TOC block 扩成目录类 block | 计划修改 | `toc` / `figure_list` / `table_list` block | 边界识别、unit range、metrics | 北大图目录/表目录不再混进 `toc` |
| D5 | taxonomy 扩展 | 计划修改 | `figure_list`、`table_list`、`academic_achievements`、声明类 label | 标签识别、下游 unit policy | 减少错误 custom，给下游稳定 unit_id |
| D6 | front/body/back 状态机 | 计划新增 | final anchors、状态转移 trace | unit range builder、open_questions | 修正文正文档内部 Heading 1 过切 |
| D7 | range ownership audit | 计划新增 | `unit_range_audit`、critical unowned、expected seq results | unit_map flags、metrics、验证器 | 防止无人认领/错归属只停在 debug |
| D8 | verifier 消费 T2 range flags | 计划修改 | T2 finding | `verification_report.first_bad_stage` | 让真实生成报告能暴露 T2 结构错误 |
| D9 | duplicate core contextual rule | 计划修改 | duplicate core decision | 标签识别、状态机、open_questions | 真后置 `references` 不再被粗暴降 custom |

## 4. 目标态数据流

Plan 02 完成后，目标数据流应该变成：

```text
T1 document_facts
  # 原始 DOCX 事实，不含 T2 语义判断。
  ↓ source_tree_from_document_facts()
source_tree
  # T2 的输入树。
  ↓ _body_entries()
entries
  # T2 顺序扫描的正文条目。
  ↓ derive_t2_entry_signals()
derived entry signals
  # T2 自己计算的结构信号：TOC、标题、说明文字、canonical hint 等。
  ↓ segment_list_like_blocks()
locked list-like blocks
  # 主目录/图目录/表目录先整体锁住，避免内部条目被误切。
  ↓ detect_boundary_candidates()
raw boundary candidates / anchors
  # 找出可能开始顶层 unit 的位置。
  ↓ label_boundary_candidates()
preliminary labeled anchors
  # 初步打上 unit_id。
  ↓ reconcile_document_zones()
final anchors
  # 用前置/正文/后置状态机修正 top-level 边界。
  ↓ build_unit_spans()
structure_candidates.units
  # 每个 unit 的 source_seq 范围。
  ↓ audit_unit_ranges_and_expected_contract()
unit_range_audit
  # 检查 unowned、overlap、expected source_seq mismatch。
  ↓ build_unit_map()
unit_map.units + unit_map.flags + unit_map.open_questions
  # 下游正式契约；关键问题不能只留在 debug。
  ↓ verifier / metrics / T3 / T4
verification_report + metrics + downstream specs
```

和当前相比，新增的关键节点只有三个：

```text
1. reconcile_document_zones()
   负责正文状态机，解决正文 Heading 1 过切。

2. audit_unit_ranges_and_expected_contract()
   负责 owner / overlap / expected source_seq 审计。

3. verifier/metrics 消费 audit 结果
   负责把结构错误从 debug 推进到真实门禁。
```

## 5. 字段按状态分层

### 5.1 当前已有字段

这些字段当前已经存在，可以继续沿用：

| 字段/产物 | 当前位置 | 当前用途 |
| --- | --- | --- |
| `source_ref` | T1/T2 entries | OOXML 追踪 |
| `source_seq` | T1/T2 entries | 顺序和范围归属 |
| `structural_signals` | T2 内部兼容字段 | 当前 T2 自己重算，不应信任旧 T1 语义 |
| `debug.t2_derived_signals_by_source_seq` | `template_structure_candidates.debug` | 观测 T2 派生信号 |
| `debug.toc_blocks` | `template_structure_candidates.debug` | 观测 TOC block |
| `unit_id` | units / unit_map | 下游主键 |
| `source_seq_refs` | units / unit_map | 单元覆盖的 source_seq |
| `source_seq_range` | units / unit_map | 单元范围摘要 |
| `raw_title` / `normalized_title` | units / unit_map | 复核和 taxonomy |
| `open_questions` | structure candidates / unit_map | 不确定问题交互入口 |
| `flags` | unit_map | 当前验证器会消费部分 flags |

### 5.2 本轮计划新增或改变的字段

| 字段/产物 | 状态 | 为什么需要 | 必须被谁消费 |
| --- | --- | --- | --- |
| `canonical_label_hint` | 计划新增/修改 | 让核心标题在 boundary 阶段就有 label hint | boundary decision、labeling、audit |
| `instruction_class` | 计划新增 | 区分纯说明和标题括注 | boundary veto、open_questions |
| `list_block.block_type` | 计划新增/修改 | 区分 `toc` / `figure_list` / `table_list` | block anchor、unit label、metrics |
| `taxonomy_scope` | 计划新增 | 区分 global_core / global_extended / school_expected / custom | label review、expected contract |
| `state_machine_trace` | 计划新增 | 解释正文标题为何被 body_main 吸收 | debug、open_questions |
| `unit_range_audit` | 计划新增 | 统一记录 unowned/overlap/expected mismatch | unit_map flags、metrics、verifier |
| `expected_source_seq_results` | 计划新增 | 证明关键 source_seq 归属正确 | tests、metrics、verifier |

硬规则：

```text
新增字段如果没有消费方，就不能进入正式 artifact。
如果只是观测信息，必须放在 debug 下，并标明不会影响验收。
如果影响验收，必须进入 unit_map.flags/open_questions 或 verification_report finding。
```

## 6. 影响面地图

| 模块 | 本轮影响 | 风险 | 对应门禁 |
| --- | --- | --- | --- |
| `structure_candidates.py` | 最大。新增/修改 boundary、label、state、audit 主逻辑 | 边界误切、unit 数暴涨、正文误吞后置 | unit tests + 三校 expected source_seq |
| `constants.py` | 扩 taxonomy 和 unit policy | taxonomy 膨胀、错误 promote 学校字段 | taxonomy scope 测试 |
| `artifacts.py` | `build_unit_map()` 要消费 audit flags | debug 问题没有进 unit_map | unit_map flags 测试 |
| `verifier.py` | T2 verifier 要消费 expected mismatch / critical unowned | `first_bad_stage` 仍不暴露 T2 错误 | verification_report 测试 |
| `scripts/t2_metrics.py` | 增加 `--unit-ranges` | 脚本和测试逻辑分叉 | 复用 expected contract loader |
| `tests/fixtures/t2_expected_units/*.yaml` | 新增三校预期契约 | source_seq 写错会误导门禁 | 真实模板回归 |
| T3/T4 | 不直接改内部解析，但会收到更准确 unit_map | unit_id 变化可能影响策略 | 合同测试 + 三校生成 |

## 7. 问题到计划的映射

用这个表判断 Plan 02 是否真的覆盖 Issue 02。

| 当前问题 | 对应增量 | 为什么能解决 | 验收方式 |
| --- | --- | --- | --- |
| 湖南 `abstract_cn` 缺失，seq 57 无 owner | D2、D3、D7 | `canonical_label_hint` 让摘要标题形成边界；range audit 防止 seq 57 静默无 owner | `abstract_cn` 存在；seq 57 属于 `abstract_cn` |
| 湖南 seq 50-64 无 owner | D1、D7 | expected contract 明确哪些 gap 允许，哪些 critical unowned 必须 fail | `critical_unowned_ranges=0` 或有 allowed reason |
| 南农 appendix 被 references 吞并 | D2、D3、D5、D7 | `附 录...` 不再被说明括注误伤，taxonomy 有 `appendix` | seq 109 属于 `appendix`，不属于 `references` |
| 南农 acknowledgement 被 academic achievements 吞并 | D2、D3、D5、D7 | `致 谢...` 形成独立边界，range audit 检查 seq 113 | seq 113 属于 `acknowledgement` |
| 北大图目录/表目录都在 toc | D4、D5 | list block 拆 `block_type`，label 不再都映射 `toc` | `toc` / `figure_list` / `table_list` 三者独立 |
| 北大正文 Heading 1 过切 custom | D6 | front/body/back 状态机把正文内部 Heading 1 吸收到 `body_main` | seq 50 / 92 / 221 / 302 属于 `body_main` |
| 北大后置 references 降 custom | D6、D9 | 状态机识别后置区，duplicate core 不再一律 custom | seq 306 属于 `references` |
| debug 能看到但报告不 fail | D7、D8 | audit 结果进入 unit_map flags，再由 verifier 变成 T2 finding | verification_report 能暴露 expected mismatch |

## 8. 不在本轮解决的事

这些不要混进 Plan 02：

```text
1. 不接入 live AI。
2. 不实现 visual page policy。
3. 不做 T3 正文内部章节解析。
4. 不做 DOCX 渲染、bbox、blank ratio。
5. 不把所有学校自定义标题提升成 global core。
```

## 9. 实现前检查清单

新增或修改任意字段前，先回答：

```text
1. 这个字段是当前已有、计划修改，还是计划新增？
2. 生产方是谁？
3. 消费方是谁？
4. 如果字段缺失，下游怎么失败？
5. 如果字段冲突，谁裁决？
6. 它只是 debug，还是会影响 unit_map / verifier / metrics？
7. 它是否需要进入三校 expected contract？
8. 它是否违反 T1 只产事实的边界？
```

最重要的一条：

```text
任何影响验收的结构问题，都不能只停留在 debug。
必须进入 unit_map.flags/open_questions、metrics 或 verification_report。
```
