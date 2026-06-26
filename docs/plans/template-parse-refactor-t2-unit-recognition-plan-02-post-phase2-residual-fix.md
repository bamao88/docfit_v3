---
status: draft
owner: template-generation
stage: T2
topic: unit-recognition
plan_id: T2-UNIT-PLAN-02
plan_sequence: 2
created: 2026-06-25
last_updated: 2026-06-26
version: 0.2
source_issue:
  id: T2-UNIT-ISSUE-02
  doc: docs/plans/template-parse-refactor-t2-unit-recognition-issue-02-post-phase2-residuals.md
previous_issue:
  id: T2-UNIT-ISSUE-01
  doc: docs/plans/template-parse-refactor-t2-unit-recognition-issue-01-boundary-label.md
previous_plan:
  doc: docs/plans/template-parse-refactor-t2-open-label-unit-recognition.md
data_contract:
  doc: docs/plans/template-parse-refactor-t2-unit-recognition-data-contract.md
related_code:
  - src/docfit/template_generation/structure_candidates.py
  - src/docfit/template_generation/constants.py
  - src/docfit/template_generation/verifier.py
  - tests/unit/test_t2_unit_map.py
  - scripts/t2_metrics.py
---

# T2 单元识别 Plan 02：Post-Phase2 Residual Fix

## 0. 文档定位

这是 T2 `unit-recognition` 的执行计划，不是字段字典。

本计划只回答：

```text
1. 本轮修哪些真实残余问题。
2. 按什么顺序修。
3. 哪些门禁证明修好了。
4. 哪些问题明确不在本轮做。
```

字段流转、producer/consumer、debug vs gate、expected contract schema 单独见：

```text
docs/plans/template-parse-refactor-t2-unit-recognition-data-contract.md
```

## 1. 当前事实基线

来源 issue：

```text
docs/plans/template-parse-refactor-t2-unit-recognition-issue-02-post-phase2-residuals.md
```

当前代码已经完成上一轮 Phase 2 的主干改造：

```text
1. T2 派生信号输出。
2. TOC block segmenter 和 locked indices。
3. boundary 判定从 keyword-only 扩成 deterministic 多信号。
4. canonical title / alias。
5. custom_unit fallback。
6. form / variant 标记。
7. copy-only 默认关闭，不再作为本轮 unit-recognition 阻塞项。
```

当前真实运行结论：

```text
TOC coverage 三校均 PASS。
最终 unit_map 仍未达到可交付基线。
```

关键残余：

| 学校 | 当前残余 |
| --- | --- |
| 湖南 | `toc` 已收口，但 seq 50-64 无 owner，`abstract_cn` 缺失 |
| 南农 | `appendix` / `acknowledgement` 被前一单元吞并，`academic_achievements` 只能 custom |
| 北大 | `figure_list` / `table_list` 被当成 `toc`，正文 Heading 1 过切，后置 `references` 降成 custom |

## 2. 本轮目标

本轮目标是把 T2 从“TOC coverage 可通过”推进到“真实三校 unit_map 可交付基线”。

P0 必须完成：

| 编号 | 主题 | 成功口径 |
| --- | --- | --- |
| P0-A | expected contract / range ownership | 关键 source_seq 不再静默 unowned 或被错误单元吞并 |
| P0-B | canonical boundary hint 前移 | 带占位符、格式括注、分散字符的核心标题能形成 boundary |
| P0-C | instruction-like 上下文分类 | 核心标题不被格式说明误 veto，纯说明仍不切单元 |
| P0-D | taxonomy / list block 拆分 | `figure_list`、`table_list`、`academic_achievements`、声明类单元有稳定 label |
| P0-E | verifier / metrics 闭环 | expected source_seq mismatch 能进入 T2 finding，不只停在 debug |

P1 尽量同轮完成：

| 编号 | 主题 | 成功口径 |
| --- | --- | --- |
| P1-A | front/body/back state machine | 北大正文 Heading 1 保留在 `body_main` 内部 |
| P1-B | duplicate core contextual rule | 后置 `references` / 声明页不再被粗暴降成 custom |

## 3. 非目标

本轮不做：

```text
1. 不接入 live AI。
2. 不实现 visual page policy。
3. 不实现 DOCX render / bbox / blank_ratio pipeline。
4. 不做 T3 单元内部章节解析。
5. 不把所有学校自定义标题塞进 global core。
6. 不恢复任何 T1 semantic fields。
```

特别约束：

```text
不能在文档、日志或验收报告中声称“AI 已兜底 unknown heading / visual block / page_policy”。
```

## 4. 数据契约要求

本轮所有实现必须遵守数据契约：

```text
docs/plans/template-parse-refactor-t2-unit-recognition-data-contract.md
```

核心规则：

```text
1. T1 只产事实；T2 派生信号不能写回 document_facts。
2. 每个新增字段必须有 producer 和 consumer。
3. debug-only 字段不能作为验收依据。
4. 会影响验收的问题必须进入 unit_map.flags/open_questions 或 verifier finding。
5. scripts/t2_metrics.py、单测、verifier 必须复用同一套 expected contract 逻辑。
```

## 5. 实施顺序

### Phase 0：expected contract 先行

新增：

```text
tests/fixtures/t2_expected_units/*.yaml
tests/unit/test_t2_unit_range_contracts.py
scripts/t2_metrics.py --unit-ranges
```

要求：

```text
1. 先写失败用例，锁住当前残余。
2. contract loader 不能只给脚本用，后续 verifier 也要复用。
3. 三校关键 source_seq owner / excludes / allowed unowned range 都写入 fixture。
```

### Phase 1：canonical boundary hint + instruction class

修改：

```text
canonical_title() / canonical_label_hint()
_unit_for_boundary_text()
_boundary_vetoes()
```

目标：

```text
湖南 seq 57 -> abstract_cn
南农 seq 109 -> appendix
南农 seq 113 -> acknowledgement
纯 instruction 仍不切顶层 unit
```

### Phase 2：taxonomy 扩展 + list-like block 拆分

修改：

```text
UNIT_DEFINITIONS / alias registry
_CORE_ALIAS_EXACT
_TOC_TITLE_NORMALIZED 或替代 list title registry
list-like block segmenter
_unit_policy()
```

目标：

```text
北大 toc / figure_list / table_list 独立。
南农 academic_achievements 命名稳定。
声明类不再普通 custom。
```

### Phase 3：range audit 接入真实门禁

新增：

```text
unit_range_audit
expected_source_seq_results
critical_unowned_ranges
unit_map flags for audit FAIL/UNKNOWN
verifier T2 findings for expected mismatch
```

目标：

```text
debug 能看到的问题，verification_report 也能看到。
```

### Phase 4：front/body/back state machine

修改：

```text
preliminary anchors -> final anchors 之间新增 state pass
body_main start/end inference
body internal Heading 1 absorb rule
back_matter anchor rule
```

目标：

```text
北大 seq 50 / 92 / 221 / 302 属于 body_main。
正文 Heading 1 不再顶层过切。
```

### Phase 5：duplicate core contextual rule

修改：

```text
_label_boundaries() duplicate handling
post-body references / declaration relabeling
duplicate_core_ambiguous open_question
```

目标：

```text
北大 seq 306 -> references。
北大声明页 -> declaration taxonomy 或 expected unit。
正文说明里的 references-like 文本不误切。
```

### Phase 6：收口

更新：

```text
Issue 02 verification section
Plan 02 status
scripts/t2_metrics.py output
三校真实生成输出路径
remaining limitations
```

## 6. 验收门禁

代码门禁：

```text
uv run pytest tests/unit/test_t2_unit_map.py -q
uv run pytest tests/unit/test_t2_unit_range_contracts.py -q
uv run python scripts/t2_metrics.py
uv run python scripts/t2_metrics.py --unit-ranges
```

真实模板门禁：

| 学校 | 必须通过 |
| --- | --- |
| 湖南 | `toc` 不包含 seq 50-64；`abstract_cn` 存在；seq 57 属于 `abstract_cn` |
| 南农 | `appendix`、`academic_achievements`、`acknowledgement` 独立；references 不吞 appendix |
| 北大 | `toc` / `figure_list` / `table_list` 独立；`body_main` 从 seq 50 附近开始；后置 `references` 不 custom |

全局门禁：

```text
1. T2 不读取旧 T1 semantic fields。
2. 三校 TOC coverage 保持 PASS。
3. expected source_seq contract PASS。
4. critical_unowned_ranges = 0，或每条都有 allowed reason / open_question。
5. unit 数不暴涨。
6. custom unit 数量下降，或每个 custom 都有 raw_title / normalized_title / review reason。
```

## 7. 需要先拍板的问题

1. **湖南 seq 50-64 怎么建模？**
   - 建议：本轮不新增正式顶层 unit。
   - seq 57 必须归 `abstract_cn`。
   - 其他片段若仍 unowned，必须有 allowed reason，例如 `title_fragment_or_instruction`。

2. **`figure_list` / `table_list` 的 scope？**
   - 建议：`global_extended`。
   - 在北大 expected contract 中 required。

3. **`academic_achievements` 的 scope？**
   - 建议：`school_expected`。
   - 多校复用后再 promote。

4. **critical unowned 是否直接 FAIL？**
   - 建议：命中 expected source_seq 的直接 FAIL。
   - 非 expected 但疑似重要的先 UNKNOWN + open_question。

5. **Plan 02 是否依赖 AI merge？**
   - 建议：不依赖。
   - deterministic 三校结构门禁通过即可合并本轮。

## 8. 输出结果

本轮完成后，至少应产生：

```text
1. 更新后的 T2 unit_map。
2. 三校 expected contract fixtures。
3. range audit debug。
4. unit_map flags / open_questions 中可见的 T2 阻断原因。
5. verifier 中可见的 expected mismatch / critical unowned finding。
6. scripts/t2_metrics.py --unit-ranges 汇总。
7. Issue 02 fix verification 记录。
```
