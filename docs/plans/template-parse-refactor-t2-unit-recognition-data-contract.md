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

这个文档只说明 T2 的数据怎么流、字段由谁生产、由谁消费。

它要防止三类断层：

```text
1. 前面步骤产了字段，但后面步骤没消费。
2. 调试信息里能看到问题，但 unit_map、验证器、指标脚本看不到。
3. 脚本和测试各写一套预期 source_seq 逻辑，结果互相不一致。
```

说明：反引号里的英文多为代码字段名、产物名（artifact）或枚举值，需要和实现保持一致；其他说明文字尽量使用中文。

## 1. 总流水线

```text
T1 document_facts
  # T1 的原始事实，只描述 DOCX 里“有什么”，不做语义判断。
  ↓ source_tree_from_document_facts()
T2 源条目（source entries）
  # T2 可处理的正文条目列表，每条有 text、style、source_seq、source_ref 等事实。
  ↓ derive_t2_entry_signals()
T2 派生条目信号（derived entry signals）
  # T2 自己派生的结构信号，例如“像目录条目”“像标题”“像说明文字”。
  ↓ segment_list_like_blocks()
已锁定的目录类块（locked list-like blocks）
  # 先锁住目录/图目录/表目录这类连续块，避免内部条目被误当成普通单元边界。
  ↓ detect_boundary_candidates()
原始边界候选 / 锚点
  # 找出可能开新单元的位置；锚点是已决定参与后续标签识别的边界点。
  ↓ label_boundary_candidates()
初步带标签锚点（preliminary labeled anchors）
  # 给边界点打初步 unit_id，例如 toc、abstract_cn、custom:template:*。
  ↓ reconcile_document_zones()
最终锚点（final anchors）
  # 用前置/正文/后置状态机修正边界，例如正文内一级标题应被 body_main 吸收。
  ↓ build_unit_spans()
template_structure_candidates.units
  # 把最终边界点扩展成单元范围，每个 unit 拥有哪些 source_seq 在这里确定。
  ↓ audit_unit_ranges_and_expected_contract()
unit_range_audit
  # 审计有没有无人认领、重叠、预期 source_seq 归属错误。
  ↓ build_unit_map()
unit_map.units + unit_map.flags + unit_map.open_questions
  # 下游正式消费的 T2 契约；阻断问题必须进入 flags/open_questions。
  ↓ 验证器 / 指标脚本 / T3 / T4
verification_report + 回归门禁 + 下游规格
  # 验证报告、回归门禁和后续 T3/T4 都从 unit_map 与审计结果继续消费。
```

逐步说明：

| 步骤 | 做什么 | 产物 | 谁消费 |
| --- | --- | --- | --- |
| T1 原始事实 | 从 DOCX 提取文本、样式、位置、表格、分页等事实 | `document_facts` | T2 源树转换 |
| T2 条目整理 | 把 T1 事实整理成 T2 顺序扫描的正文条目 | `source entries` | T2 派生信号 |
| T2 派生信号 | 基于事实判断“像目录”“像标题”“像说明”，但不写回 T1 | `derived entry signals` | 块分段、边界识别、审计 |
| 目录类块分段 | 先整体识别目录/图目录/表目录，锁住内部范围 | `locked list-like blocks` | 边界识别、单元范围生成 |
| 边界识别 | 找出哪些段落可能开始一个顶层单元 | 边界候选 / 锚点 | 标签识别 |
| 标签识别 | 把边界映射成初步 `unit_id` | `preliminary labeled anchors` | 状态机 |
| 状态机修正 | 判断前置、正文、后置区域，避免正文标题被过切 | `final anchors` | 单元范围生成 |
| 单元范围生成 | 按最终边界切出每个 unit 的 source_seq 范围 | `template_structure_candidates.units` | 范围审计、unit_map |
| 范围审计 | 检查无人认领、重叠、预期 source_seq 错归属 | `unit_range_audit` | unit_map flags、验证器、指标脚本 |
| unit_map 转换 | 生成下游正式消费的 T2 契约 | `unit_map` | 验证器、T3、T4、指标脚本 |

硬规则：

```text
1. T1 只提供事实，T2 不把派生语义写回 document_facts。
2. T2 调试字段只能用于观察。
3. 影响验收的字段必须进入 `unit_map.flags`、`open_questions` 或验证器问题记录（finding）。
4. 每个新增字段必须有生产方和消费方。
5. 指标脚本、单元测试、验证器必须复用同一套预期契约加载器。
```

## 2. T2 可以消费的 T1 字段

| 字段 | 来源 | T2 用途 |
| --- | --- | --- |
| `source_ref` | T1 OOXML 坐标 | 追踪、范围、证据 |
| `source_seq` | T1 body 顺序 | 归属审计、预期契约 |
| `node_id` / `paragraph_id` | T1 追踪信息 | 调试、entry_refs |
| `kind` / `flow_item_type` | T1 事实 | 表格单元格否决、正文流过滤 |
| `text` | T1 可见文本 | 规范化、标题/目录检测 |
| `style` / `style_details.paragraph.style_name` | T1 样式事实 | 标题级别、TOC 样式提示 |
| `style_details.paragraph.alignment` | T1 段落事实 | 居中、文本属性信号 |
| `style_details.dominant_run.font_size_pt` | T1 run 事实 | 字号信号 |
| `style_details.dominant_run.bold` | T1 run 事实 | 加粗信号 |
| `container_ref` / table refs | T1 结构事实 | 表格单元格否决、容器追踪 |
| `data.breaks` / section breaks | T1 OOXML 事实 | 分页/分节证据、状态提示 |

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

如果旧产物里有这些字段，T2 必须忽略并重新派生。

## 3. T2 派生条目信号

这些字段由 T2 从 T1 原子事实派生，不写回 T1。

| 字段 | 生产方 | 消费方 | 作用 |
| --- | --- | --- | --- |
| `toc_title_like` | 目录标题分类器 | 目录块分段器 | 主目录标题识别 |
| `toc_entry_like` | TOC 条目分类器 | block 分段器、TOC 指标 | TOC 覆盖率 |
| `list_title_type` | 规范标题分类器 | block 分段器 | 区分 `toc` / `figure_list` / `table_list` |
| `list_entry_like` | 目录条目分类器 | block 分段器 | 目录类块覆盖率 |
| `instruction_like` | 说明文字分类器 | 说明文字上下文分类器 | 不能直接决定硬否决 |
| `instruction_class` | 说明文字上下文分类器 | 边界否决、元素策略 | 区分纯说明和标题括注 |
| `spacing_line_like` | 空行/分隔行分类器 | 边界否决、审计 | 可解释无人认领段落 |
| `unit_heading_like` | 样式/文本分类器 | 边界候选、审计 | 关键无人认领判定 |
| `canonical_title` | 标题规范化器 | 标签提示、调试信息 | 标题规范化 |
| `canonical_label_hint` | 别名/分类匹配器 | 边界评分、标签识别、审计 | 核心标签提示 |

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
  边界硬否决，可作为审计中的可忽略原因。

title_with_format_annotation + canonical_label_hint:
  不 veto，增加 boundary evidence。

ambiguous_instruction_title:
  默认进入候选/open_question；若命中预期 source_seq，升级为审计项。
```

## 4. 目录类块

本轮不再把所有目录类 block 都叫 TOC。内部统一叫“目录类块”，覆盖主目录、图目录、表目录。

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

| 字段 | 消费方 | 必须效果 |
| --- | --- | --- |
| `block_type` | block anchor、标签识别、指标脚本 | 区分 `toc` / `figure_list` / `table_list` |
| `unit_id` | 目录类块 anchor | 生成对应 unit anchor |
| `start_index` / `end_index` | 锁定范围、单元范围生成器 | block unit 按 block end 收口 |
| `locked_source_seq_refs` | 边界检测器、范围审计 | block 内 entry 不参与普通边界检测 |
| `weak` | confidence/open_question | 弱 block 必须可复核 |

如果 block 字段只进入调试信息，不影响最终 unit 范围，则视为无效实现。

## 5. 边界锚点

边界锚点表示“这里可能开始一个顶层单元”。所有 boundary 来源统一成同一种数据形状：

```text
普通边界判定
目录类块锚点
关键词精确兜底
body_main 兜底
文档起点兜底
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

| 字段 | 消费方 | 说明 |
| --- | --- | --- |
| `canonical_label_hint` | 边界评分、标签识别、审计 | 要影响核心标题识别 |
| `instruction_class` | 否决规则、open_question、元素策略 | 避免纯说明误切 |
| `signals` | unit evidence、open_questions、调试信息 | 解释为什么切/不切 |
| `vetoes` | open_questions、调试信息 | 否决后保留原因 |
| `unit_id_hint` | 标签识别步骤 | 提示，不是最终标签 |
| `block_range` | 单元范围生成器 | list block 必须按 range 收口 |
| `confidence` | open_questions、unit_map flags | medium/low 必须可追踪 |

## 6. 标签和分类

标签识别步骤把边界锚点映射成初步单元标签。

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
2. `canonical_label_id` 记录闭集标签；custom 为 null。
3. `school_expected` 必须由预期契约或学校配置（profile）支撑。
4. 自定义单元必须保留 `raw_title` / `normalized_title` / `display_name` / `source_seq`。
```

## 7. 前置 / 正文 / 后置状态

状态机在初步边界之后、最终单元之前运行。它负责判断当前段落属于前置材料、正文主体，还是后置材料。

状态追踪字段：

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

状态取值：

```text
front_matter
body_main
back_matter
unknown
```

决策取值：

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
1. `absorb_into_body_main` 必须改变最终单元范围。
2. `start_back_matter_unit` 必须结束 `body_main` 范围。
3. 无法判断的状态转移进入 `open_questions`。
4. 北大 seq 50 / 92 / 221 / 302 必须可解释为 `body_main` 内部标题。
```

## 8. 单元范围

最终单元范围是 T2 对下游的主要契约。

关键字段：

| 字段 | 消费方 | 失败表现 |
| --- | --- | --- |
| `unit_id` | generation_model、T3/T4/T5、指标脚本 | 标签错导致策略错 |
| `source_seq_refs` | 范围审计、预期契约、T4/T5 binding | 缺失导致归属断层 |
| `source_seq_range` | 指标脚本、调试信息、template_spec binding | 范围错导致吞并/漏段 |
| `label_status` | unit_map flags、分类复核队列 | unknown/custom 必须可审 |
| `canonical_label_id` | 下游 known-unit policy | null 只能用于 custom/unknown |
| `raw_title` / `normalized_title` | 复核、调试信息、分类 | custom 不能丢标题 |
| `evidence` | 验证器/调试信息 | 解释切分原因 |
| `flags` | unit_map、verification_report | UNKNOWN/FAIL 必须进入报告 |

## 9. 范围审计

范围审计在单元范围生成之后运行。它负责回答“每个关键 source_seq 到底归谁”。

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
2. `critical_unowned` 非空必须生成 unit_map flag。
3. 预期 source_seq FAIL 必须生成 unit_map flag，并由验证器输出 T2 问题记录（finding）。
4. 指标脚本复用审计结果，不重新实现归属逻辑。
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

## 10. 预期契约

三校预期契约是回归测试输入，不是调试输出。

建议 YAML 结构：

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

消费方：

```text
tests/unit/test_t2_unit_range_contracts.py
scripts/t2_metrics.py --unit-ranges
验证器 T2 expected-source-seq 问题记录
```

## 11. `structure_candidates` 到 `unit_map`

转换规则：

```text
structure_candidates.units[*]
  -> unit_map.units[*]

structure_candidates.open_questions
  -> unit_map.open_questions

structure_candidates.taxonomy_review_queue
  -> unit_map.taxonomy_review_queue

structure_candidates.debug.unit_range_audit 中的关键/FAIL 项
  -> unit_map.flags
  -> verification_report.findings
```

不能只停在调试信息里的问题：

```text
预期 source_seq 归属不一致
关键无人认领范围
单元范围重叠
必需预期单元缺失
body_main 状态转移冲突
影响最终 unit_id 的 duplicate core 歧义
```

允许仅调试记录：

```text
原始派生信号图
PASS 状态的目录类块追踪
PASS 状态的状态机追踪
PASS 状态的 duplicate core 决策记录
```

## 12. 验证器 / 指标脚本分工

| 能力 | 指标脚本 | 验证器 |
| --- | --- | --- |
| TOC 覆盖率 | 必须 | 可选 |
| 预期单元 PASS/FAIL | 必须 | 必须消费 FAIL flags |
| 预期 source_seq 归属 | 必须 | 必须消费 FAIL flags |
| 关键无人认领范围 | 必须 | 必须消费 FAIL flags |
| 调试追踪打印 | 必须 | 不需要 |
| `summary.first_bad_stage` | 不负责 | 必须负责 |

状态规则：

```text
预期 source_seq 归属不一致：
  status = FAIL
  first_bad_stage = T2

关键无人认领，但没有命中预期契约：
  status = UNKNOWN
  first_bad_stage = T2，除非契约显式允许

弱目录块 / 歧义标题：
  status = UNKNOWN
  必须包含 open_question
```

## 13. 新字段检查清单

每新增一个字段，必须回答：

```text
1. 生产方是哪个函数？
2. 消费方是哪个函数、脚本、测试或产物？
3. 如果字段缺失，下游怎么失败？
4. 如果字段冲突，谁裁决？
5. 字段是仅用于调试，还是会影响 unit_map/验证器？
6. 是否需要进入预期契约？
7. 是否违反 T1 只产事实的边界？
```

没有消费方的字段不得进入正式产物。只为观察服务的字段必须放在 `debug` 下，并明确不影响产品决策。
