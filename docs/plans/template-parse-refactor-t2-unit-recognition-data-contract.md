---
status: draft
owner: template-generation
stage: T2
topic: unit-recognition
doc_id: T2-UNIT-DATA-CONTRACT-01
created: 2026-06-26
source_plan:
  id: T2-UNIT-PLAN-02
  doc: docs/plans/template-parse-refactor-t2-unit-recognition-plan-02-post-phase2-residual-fix.md
source_issue:
  id: T2-UNIT-ISSUE-02
  doc: docs/plans/template-parse-refactor-t2-unit-recognition-issue-02-post-phase2-residuals.md
---

# T2 单元识别数据转换契约

## 0. 目的

这个文档只说明 T2 的数据怎么流、字段谁生产、谁消费。

它要防止三类断层：

```text
1. producer 产了字段，但 downstream 没消费。
2. debug 里能看到问题，但 unit_map / verifier / metrics 看不到。
3. 脚本和测试各写一套 expected source_seq 逻辑，结果互相不一致。
```

## 1. 总流水线

```text
T1 document_facts
  ↓ source_tree_from_document_facts()
T2 source entries
  ↓ derive_t2_entry_signals()
T2 derived entry signals
  ↓ segment_list_like_blocks()
locked list-like blocks
  ↓ detect_boundary_candidates()
raw boundary candidates / anchors
  ↓ label_boundary_candidates()
preliminary labeled anchors
  ↓ reconcile_document_zones()
final anchors
  ↓ build_unit_spans()
template_structure_candidates.units
  ↓ audit_unit_ranges_and_expected_contract()
unit_range_audit
  ↓ build_unit_map()
unit_map.units + unit_map.flags + unit_map.open_questions
  ↓ verifier / metrics / T3 / T4
verification_report + regression gates + downstream specs
```

硬规则：

```text
1. T1 只提供事实，T2 不把派生语义写回 document_facts。
2. T2 debug 字段只能用于观察。
3. 影响验收的字段必须进入 unit_map.flags/open_questions 或 verifier finding。
4. 每个新增字段必须有 producer 和 consumer。
5. metrics、unit tests、verifier 必须复用同一套 expected contract loader。
```

## 2. T2 可以消费的 T1 字段

| 字段 | 来源 | T2 用途 |
| --- | --- | --- |
| `source_ref` | T1 OOXML 坐标 | trace、range、evidence |
| `source_seq` | T1 body 顺序 | ownership、expected contract |
| `node_id` / `paragraph_id` | T1 trace | debug、entry_refs |
| `kind` / `flow_item_type` | T1 fact | table cell veto、body flow filter |
| `text` | T1 visible text | normalization、title/list detection |
| `style` / `style_details.paragraph.style_name` | T1 style fact | heading level、TOC style hint |
| `style_details.paragraph.alignment` | T1 paragraph fact | centered/text_properties signal |
| `style_details.dominant_run.font_size_pt` | T1 run fact | large_font signal |
| `style_details.dominant_run.bold` | T1 run fact | bold/text_properties signal |
| `container_ref` / table refs | T1 structural fact | table cell veto、container trace |
| `data.breaks` / section breaks | T1 OOXML fact | break evidence、state hint |

T2 禁止消费旧 T1 语义字段：

```text
is_toc_entry
is_spacing_line
looks_like_instruction_text
likely_unit_heading
large_font
short_text
unit_id
policy
confidence
```

如果旧 artifact 里有这些字段，T2 必须忽略并重新派生。

## 3. Derived Entry Signals

这些字段由 T2 从 T1 原子事实派生，不写回 T1。

| 字段 | producer | consumer | 作用 |
| --- | --- | --- | --- |
| `toc_title_like` | list title classifier | list block segmenter | 主目录标题识别 |
| `toc_entry_like` | TOC entry classifier | block segmenter、TOC metric | TOC coverage |
| `list_title_type` | canonical title classifier | block segmenter | `toc` / `figure_list` / `table_list` |
| `list_entry_like` | list entry classifier | block segmenter | list block coverage |
| `instruction_like` | instruction classifier | instruction class resolver | 不能直接决定 hard veto |
| `instruction_class` | instruction class resolver | boundary veto、element policy | 区分纯说明和标题括注 |
| `spacing_line_like` | spacing classifier | boundary veto、audit | 可解释 unowned |
| `unit_heading_like` | style/text classifier | boundary candidate、audit | critical unowned 判定 |
| `canonical_title` | title normalizer | label hint、debug | 标题规范化 |
| `canonical_label_hint` | alias/taxonomy matcher | boundary score、labeling、audit | 核心 label hint |

`canonical_label_hint` 建议形状：

```json
{
  "unit_id": "abstract_cn",
  "scope": "global_core",
  "match_type": "exact_canonical_title",
  "confidence": "high",
  "normalized_title": "摘要"
}
```

`instruction_class` 可取值：

```text
not_instruction
pure_instruction
title_with_format_annotation
ambiguous_instruction_title
```

消费规则：

```text
pure_instruction:
  boundary hard veto，可作为 audit ignorable reason。

title_with_format_annotation + canonical_label_hint:
  不 veto，增加 boundary evidence。

ambiguous_instruction_title:
  默认 candidate/open_question；若命中 expected source_seq，升级为 audit item。
```

## 4. List-Like Block

本轮不再把所有目录类 block 都叫 TOC。内部统一叫 list-like block。

建议字段：

```json
{
  "block_id": "list-block-0003",
  "block_type": "figure_list",
  "unit_id": "figure_list",
  "start_index": 31,
  "end_index": 45,
  "start_source_seq": 31,
  "end_source_seq": 45,
  "title_source_seq": 31,
  "entries_count": 14,
  "title_led": true,
  "weak": false,
  "locked_source_seq_refs": [31, 32, 33]
}
```

字段消费关系：

| 字段 | consumer | 必须效果 |
| --- | --- | --- |
| `block_type` | block anchor、labeling、metrics | 区分 `toc` / `figure_list` / `table_list` |
| `unit_id` | list block anchor | 生成对应 unit anchor |
| `start_index` / `end_index` | locked range、unit span builder | block unit 按 block end 收口 |
| `locked_source_seq_refs` | boundary detector、range audit | block 内 entry 不参与 generic boundary |
| `weak` | confidence/open_question | 弱 block 必须可 review |

如果 block 字段只进入 debug，不影响最终 unit range，则视为无效实现。

## 5. Boundary Anchor

所有 boundary 来源统一成同一 shape：

```text
generic boundary decision
list-like block anchor
keyword exact fallback
body_main fallback
document start fallback
```

建议字段：

```json
{
  "entry_index": 57,
  "source_ref": "word/document.xml:p[57]",
  "source_seq": 57,
  "text": "□□摘□要（小四黑体）：...",
  "normalized_text": "摘要",
  "canonical_label_hint": {
    "unit_id": "abstract_cn",
    "scope": "global_core",
    "match_type": "exact_canonical_title",
    "confidence": "high"
  },
  "instruction_class": "title_with_format_annotation",
  "score": 4,
  "signals": [
    {"kind": "canonical_label_hint", "weight": 2, "unit_id": "abstract_cn"},
    {"kind": "instruction_annotation", "weight": 0}
  ],
  "vetoes": [],
  "unit_id_hint": "abstract_cn",
  "name_hint": "中文摘要",
  "is_boundary": true,
  "is_candidate": false,
  "confidence": "high",
  "block_range": null
}
```

字段消费关系：

| 字段 | consumer | 说明 |
| --- | --- | --- |
| `canonical_label_hint` | boundary score、labeling、audit | 要影响核心标题识别 |
| `instruction_class` | veto、open_question、element policy | 避免纯说明误切 |
| `signals` | unit evidence、open_questions、debug | 解释为什么切/不切 |
| `vetoes` | open_questions、debug | veto 后保留原因 |
| `unit_id_hint` | label pass | hint，不是最终 label |
| `block_range` | unit span builder | list block 必须按 range 收口 |
| `confidence` | open_questions、unit_map flags | medium/low 必须可追踪 |

## 6. Label / Taxonomy

label pass 把 boundary anchor 映射成 preliminary unit label。

建议字段：

```json
{
  "unit_id": "figure_list",
  "name": "图目录",
  "label_status": "alias_matched",
  "canonical_label_id": "figure_list",
  "taxonomy_scope": "global_extended",
  "raw_title": "图目录",
  "normalized_title": "图目录",
  "display_name": "图目录",
  "flags": []
}
```

`label_status`：

```text
core_matched
alias_matched
school_expected_matched
custom_detected
candidate_only
unmapped
duplicate_held
```

`taxonomy_scope`：

```text
global_core
global_extended
school_expected
template_optional
custom
unknown
```

消费规则：

```text
1. `unit_id` 是下游 T3/T4/T5 主键。
2. `canonical_label_id` 记录 closed-set label；custom 为 null。
3. `school_expected` 必须由 expected contract 或学校 profile 支撑。
4. custom unit 必须保留 raw_title / normalized_title / display_name / source_seq。
```

## 7. Front / Body / Back State

状态机在 preliminary anchors 之后、final units 之前运行。

trace 字段：

```json
{
  "source_seq": 92,
  "from_state": "body_main",
  "to_state": "body_main",
  "anchor_unit_id": "custom:template:插图公式与表格:92",
  "decision": "absorb_into_body_main",
  "reason": "heading1_inside_body_without_back_matter_label",
  "result_unit_id": "body_main"
}
```

state：

```text
front_matter
body_main
back_matter
unknown
```

decision：

```text
keep_top_level_unit
start_body_main
absorb_into_body_main
start_back_matter_unit
hold_as_custom
open_question
```

消费规则：

```text
1. `absorb_into_body_main` 必须改变 final unit spans。
2. `start_back_matter_unit` 必须结束 body_main range。
3. 无法判断的 transition 进入 open_questions。
4. 北大 seq 50 / 92 / 221 / 302 必须可解释为 body_main 内部 heading。
```

## 8. Unit Span

final unit 是 T2 对下游的主要契约。

关键字段：

| 字段 | consumer | 失败表现 |
| --- | --- | --- |
| `unit_id` | generation_model、T3/T4/T5、metrics | label 错导致策略错 |
| `source_seq_refs` | range audit、expected contract、T4/T5 binding | 缺失导致 ownership gap |
| `source_seq_range` | metrics、debug、template_spec binding | range 错导致吞并/漏段 |
| `label_status` | unit_map flags、taxonomy review | unknown/custom 必须可审 |
| `canonical_label_id` | downstream known-unit policy | null 只能用于 custom/unknown |
| `raw_title` / `normalized_title` | review/debug/taxonomy | custom 不能丢标题 |
| `evidence` | verifier/debug | 解释切分原因 |
| `flags` | unit_map、verification_report | UNKNOWN/FAIL 必须进入报告 |

## 9. Range Audit

range audit 在 unit span 之后运行。

建议字段：

```json
{
  "unit_range_audit": {
    "unowned_ranges": [],
    "overlaps": [],
    "critical_unowned_ranges": [],
    "expected_source_seq_results": [
      {
        "school": "hunannongye",
        "source_seq": 57,
        "expected_unit_ids": ["abstract_cn"],
        "actual_unit_id": "abstract_cn",
        "status": "PASS"
      }
    ]
  }
}
```

消费规则：

```text
1. 明细进入 template_structure_candidates.debug。
2. critical_unowned 非空必须生成 unit_map flag。
3. expected source_seq FAIL 必须生成 unit_map flag，并由 verifier 输出 T2 finding。
4. metrics 复用 audit 结果，不重新实现归属逻辑。
```

flag 建议形状：

```json
{
  "type": "unit_range_expected_source_seq_mismatch",
  "status": "FAIL",
  "source_seq": 57,
  "expected": "abstract_cn",
  "actual": null,
  "reason": "expected source_seq is unowned",
  "affected_ids": ["abstract_cn"]
}
```

## 10. Expected Contract

三校 expected contract 是 regression 输入，不是 debug 输出。

建议 YAML schema：

```yaml
school: hunannongye
source_template: inputs/targets/hunannongye/raw/source_template.docx
expected_units:
  - unit_id: toc
    required: true
    source_seq_contains_any: [24, 27, 49]
    source_seq_excludes: [50, 57, 64]
  - unit_id: abstract_cn
    required: true
    source_seq_contains_any: [57]
critical_unowned_forbidden:
  - [57, 57]
allowed_unowned_ranges:
  - range: [50, 56]
    reason: title_fragment_or_instruction
```

consumer：

```text
tests/unit/test_t2_unit_range_contracts.py
scripts/t2_metrics.py --unit-ranges
verifier T2 expected-source-seq findings
```

## 11. structure_candidates -> unit_map

转换规则：

```text
structure_candidates.units[*]
  -> unit_map.units[*]

structure_candidates.open_questions
  -> unit_map.open_questions

structure_candidates.taxonomy_review_queue
  -> unit_map.taxonomy_review_queue

structure_candidates.debug.unit_range_audit critical/FAIL items
  -> unit_map.flags
  -> verification_report.findings
```

不能只停在 debug 的问题：

```text
expected source_seq mismatch
critical unowned range
unit overlap
required expected unit missing
body_main 状态转移冲突
duplicate core ambiguity that affects final unit_id
```

允许 debug-only：

```text
raw derived signal map
PASS 状态的 list block trace
PASS 状态的 state_machine_trace
PASS 状态的 duplicate_core_decisions
```

## 12. Verifier / Metrics 分工

| 能力 | metrics | verifier |
| --- | --- | --- |
| TOC coverage | 必须 | 可选 |
| expected units PASS/FAIL | 必须 | 必须消费 FAIL flags |
| expected source_seq owner | 必须 | 必须消费 FAIL flags |
| critical unowned | 必须 | 必须消费 FAIL flags |
| debug trace 打印 | 必须 | 不需要 |
| `summary.first_bad_stage` | 不负责 | 必须负责 |

状态规则：

```text
expected source_seq mismatch:
  status = FAIL
  first_bad_stage = T2

critical unowned but not in expected contract:
  status = UNKNOWN
  first_bad_stage = T2 unless manually allowed

weak block / ambiguous title:
  status = UNKNOWN
  must include open_question
```

## 13. 新字段检查清单

每新增一个字段，必须回答：

```text
1. Producer 是哪个函数？
2. Consumer 是哪个函数、脚本、测试或 artifact？
3. 如果字段缺失，下游怎么 fail？
4. 如果字段冲突，谁裁决？
5. 字段是 debug-only，还是影响 unit_map/verifier？
6. 是否需要进入 expected contract？
7. 是否违反 T1 fact-only 边界？
```

没有 consumer 的字段不得进入正式 artifact。只为观察服务的字段必须放在 `debug` 下，并明确不影响产品决策。
