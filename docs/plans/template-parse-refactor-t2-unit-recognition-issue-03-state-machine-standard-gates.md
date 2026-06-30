---
status: draft
owner: template-generation
stage: T2
topic: unit-recognition
issue_id: T2-UNIT-ISSUE-03
issue_sequence: 3
created: 2026-06-26
last_updated: 2026-06-28
version: 1
previous_issue:
  id: T2-UNIT-ISSUE-02
  doc: docs/plans/template-parse-refactor-t2-unit-recognition-issue-02-post-phase2-residuals.md
previous_optimization:
  id: T2-UNIT-PLAN-02
  doc: docs/plans/template-parse-refactor-t2-unit-recognition-plan-02-post-phase2-residual-fix.md
  summary: Plan 02 clarified post-Phase2 residual fixes and data-flow needs, but did not make standard-backed verification and the document-zone state machine the primary execution spine.
next_plan:
  id: T2-UNIT-PLAN-03
  doc: docs/plans/template-parse-refactor-t2-unit-recognition-plan-03-state-machine-standard-gates.md
  summary: standard-backed T2 gate first, then deterministic boundary/list taxonomy fixes, then front/body/back state machine.
evidence_runs:
  - label: current_t2_metrics
    code_checkpoint: 14648cc
    command: uv run python scripts/t2_metrics.py
    output: toc coverage PASS for three schools; unit/range standard gate not exercised
  - label: standard_expected_vs_current_actual_probe
    code_checkpoint: 14648cc
    command: one-off Python probe loading standards/targets/*/v1/template_generation/t2_unit_pagination.standard.yaml and current build_template_structure_candidates()
    output: all three schools mismatch expected unit_order / actual unit ids
related_standards:
  - standards/targets/hunannongye/v1/template_generation/t2_unit_pagination.standard.yaml
  - standards/targets/nannong-undergraduate/v1/template_generation/t2_unit_pagination.standard.yaml
  - standards/targets/pku-graduate/v1/template_generation/t2_unit_pagination.standard.yaml
related_docs:
  - docs/plans/template-parse-refactor-issue-index.md
  - docs/plans/template-parse-refactor-t2-unit-recognition-data-contract.md
  - docs/plans/template-parse-refactor-t2-unit-recognition-plan-02-post-phase2-residual-fix.md
---

# T2 单元识别 Issue 03：状态机与标准门禁没有闭环

## 0. 记录目的

本 issue 只澄清当前 T2 下一轮优化的事实基线：

```text
1. 当前 T2 到底还错在哪里。
2. 三校 T2 standard 文件已经存在，但为什么还没有形成验证闭环。
3. 为什么本轮需要把 front/body/back 状态机作为主线，而不是继续靠局部 keyword/boundary patch。
```

重要边界：

```text
standards/targets/** 是验收标准，不是 T2 生成算法的输入。
T2 inference 仍只能读 T1 document_facts / source_tree 中的源 DOCX 事实。
本轮引入 standard 的位置是 verifier、metrics、contract tests 和 regression gates。
```

## 1. 当前真实运行口径

代码 checkpoint：`14648cc`。

运行命令：

```text
uv run python scripts/t2_metrics.py
```

当前输出：

| 学校 | units | other | custom | toc_in/exp | leak | open_questions | gate |
| --- | ---: | ---: | ---: | --- | ---: | ---: | --- |
| hunannongye | 10 | 0 | 4 | 20/20 | 0 | 19 | PASS |
| nannong-undergraduate | 10 | 0 | 3 | 25/25 | 0 | 7 | PASS |
| pku-graduate | 21 | 0 | 12 | 17/17 | 0 | 33 | PASS |

这个 PASS 只说明 TOC 条目覆盖率和 TOC leak 没问题，不说明 T2 已经满足三校 standard。

### 1.1 2026-06-28 标准裁判复核

运行命令：

```text
rm -rf /tmp/docfit_standard_acceptance_real_core_gate_check
for school in hunannongye nannong-undergraduate pku-graduate; do
  RUN_ROOT="/tmp/docfit_standard_acceptance_real_core_gate_check/$school"
  uv run docfit eval template-generate \
    --template "inputs/targets/$school/raw/source_template.docx" \
    --out "$RUN_ROOT/eval_runs/template_generate"
  uv run docfit eval template-generation-judge \
    --school "$school" \
    --run "$RUN_ROOT/eval_runs/template_generate" \
    --out "$RUN_ROOT/eval_runs/template_generation_judge"
done
```

首次复核结果：

| 学校 | standard_acceptance_status | signoff_status | T2 audit | 主要阻断 | owner |
| --- | --- | --- | --- | --- | --- |
| hunannongye | UNKNOWN | NOT_SIGNABLE | PASS | `verifier_state=not_configured`、`gate_enabled=false` | verifier |
| nannong-undergraduate | FAIL | NOT_SIGNABLE | FAIL | `body_main` 与 `abstract_en` 顺序/边界错误，seq 50 `第一章 文献综述` 被归入 `abstract_en` | code |
| pku-graduate | FAIL | NOT_SIGNABLE | FAIL | 缺 expected units、正文/前置 custom 过切、anchor owner mismatch | code |

首次复核结论：

```text
1. 湖南 T2/T3/T4/T5 deterministic audit 已通过，但标准文件仍未配置正式门禁，所以不能签收 PASS。
2. 南农 first bad stage 是 T2：`TITLE（论文英文题目...）` 被 zone state machine 误提升为 body_main，
   导致真正正文锚点 `第一章 文献综述（三号黑体居中）` 落在 abstract_en 范围内。
3. 北大 first bad stage 仍是 T2：正文状态机、front matter 标题归属、figure/table list 与后置声明 taxonomy
   仍未满足 signed standard。
4. 这些 mismatch 来自产物生成逻辑，不是 AI/prompt，也不是标准文件本身错误；修复责任先归 code。
```

2026-06-28 修复后复核：

```text
output_root=/tmp/docfit_standard_acceptance_real_core_after_t3_fixed_fill_exception

hunannongye:
  standard_acceptance_status: PASS
  signoff_status: SIGNABLE
  stage audits: T1 PASS, T2 PASS, T3 PASS, T4 PASS, T5 PASS

nannong-undergraduate:
  standard_acceptance_status: PASS
  signoff_status: SIGNABLE
  stage audits: T1 PASS, T2 PASS, T3 PASS, T4 PASS, T5 PASS

pku-graduate:
  standard_acceptance_status: PASS
  signoff_status: SIGNABLE
  stage audits: T1 PASS, T2 PASS, T3 PASS, T4 PASS, T5 PASS
```

已解决：

```text
1. 南农 `TITLE` 不再抢占 body_main；英文题名/TITLE 并入 abstract_en，`第一章 文献综述` 归入 body_main。
2. 北大封面日期并入 cover；English Title 并入 abstract_en；主 TOC 从 T1 content_control/TOC field 合成 toc；
   声明总标题打开 originality_authorization_statement，内部“原创性声明/使用授权说明”作为同一单元内容吸收。
3. 合成 TOC 使用主 TOC field source_ref 绑定 section_005，T5 `section_profile_refs` 不再缺失。
4. real-core T1-T5 标准元数据已切换到 `verifier_state=configured`、`gate_enabled=true`。
5. T3 标准新增 `fixed_units_allow_fill_elements: [cover]`：封面仍是固定模板块，但题名、学生信息等明确填空位允许生成 fill 元素；manual_only 单元仍禁止 fill。
```

## 2. 三校 standard 当前状态

三校都已经有 T2 standard：

| 学校 | standard 文件 | artifact_under_test | verifier_state | gate_enabled |
| --- | --- | --- | --- | --- |
| hunannongye | `standards/targets/hunannongye/v1/template_generation/t2_unit_pagination.standard.yaml` | `unit_map` | `configured` | `true` |
| nannong-undergraduate | `standards/targets/nannong-undergraduate/v1/template_generation/t2_unit_pagination.standard.yaml` | `unit_map` | `configured` | `true` |
| pku-graduate | `standards/targets/pku-graduate/v1/template_generation/t2_unit_pagination.standard.yaml` | `unit_map` | `configured` | `true` |

这些文件已经给出：

```text
expected.unit_order
expected.units[].unit_id
expected.units[].anchors.title_aliases
expected.units[].boundary
expected.units[].page
```

但当前代码没有闭环：

```text
1. generate_template() 不接收 school_id 或 StandardBundle。
2. verify_template_parse_build() 只校验 unit_map 非空、body_main、page_start 和 unit_map.flags。
3. scripts/t2_metrics.py 只校验 TOC coverage / leak。
4. tests 里没有用三校 T2 standard 对 unit_map 做 expected unit_order / unit presence / anchor ownership 比对。
```

因此现在存在一个危险假象：

```text
三校 TOC gate PASS，
但三校 T2 standard gate 实际没有运行。
```

## 3. Expected vs Observed

### 3.1 湖南农大

Standard expected unit order：

```text
cover, integrity_statement, toc, body_title_block, abstract_cn, abstract_en,
body_main, references, acknowledgement, appendix, design_task, proposal,
proposal_record, defense_record, topic_change_approval, grade_form
```

当前 actual unit ids：

```text
cover, integrity_statement, toc, abstract_en, body_main, post_forms,
custom:template:开题报告:144,
custom:template:开题论证记录表:182,
custom:template:答辩记录表:213,
custom:template:成绩评定表:285
```

Observed：

```text
body_title_block 缺失。
abstract_cn 缺失。
references / acknowledgement / appendix 缺失。
多个后置表单被 post_forms 或 custom 表达，未映射到 standard unit_id。
```

### 3.2 南京农业大学本科

Standard expected unit order：

```text
cover, originality_statement, authorization_statement, toc, abstract_cn,
abstract_en, body_main, references, appendix, academic_achievements,
acknowledgement
```

当前 actual unit ids：

```text
cover, integrity_statement, toc, abstract_cn, custom:template:title:44,
abstract_en, body_main, custom:template:第章结论与展望:83,
references, custom:template:相关的学术成果目录:111
```

Observed：

```text
originality_statement / authorization_statement 没有按 standard unit_id 表达。
appendix 缺失。
academic_achievements 还是 custom。
acknowledgement 缺失。
正文内“第X章结论与展望”被过切成 custom。
```

### 3.3 北京大学研究生

Standard expected unit order：

```text
cover, copyright_notice, abstract_cn, abstract_en, toc, figure_list,
table_list, body_main, references, academic_achievements, acknowledgement,
originality_authorization_statement
```

当前 actual unit ids：

```text
cover, custom:template:二〇年月:11, integrity_statement, abstract_cn,
custom:template:englishtitleofyo:25, abstract_en, toc,
custom:template:研究背景:50, custom:template:插图公式与表格:92,
body_main, custom:template:图表编号和图表目录的更新:219,
custom:template:其他注意事项:221,
custom:template:其他而且这里顺便试试看如果标题实:243,
references, custom:template:进一步讨论而且这里顺便试试看如果:247,
custom:template:三级标题示例而且这里顺便试试看如:249,
custom:template:结论与讨论:302, custom:template:参考文献:306,
appendix, acknowledgement, custom:template:原创性声明:345
```

Observed：

```text
copyright_notice 缺失。
figure_list / table_list 缺失。
正文内部 Heading 1 被切成多个 top-level custom。
后置 references 的 duplicate core 处理错误，seq 306 变成 custom。
academic_achievements 缺失。
originality_authorization_statement 缺失。
```

## 4. 当前问题是什么

### P0-A：standard gate 断开

状态：已解决。

首次复核现象：

```text
三校 standard 文件已经存在，但 verifier_state=not_configured、gate_enabled=false。
当前 metrics PASS 只覆盖 TOC，不覆盖 expected.unit_order。
```

影响：

```text
T2 可以在真实 unit_map 明显不符合 standard 的情况下显示 PASS。
```

疑似根因：

```text
stage standards 已从旧整体模板标准拆出，但没有把 t2_unit_pagination.standard.yaml 接到 template_generation verifier / metrics。
```

### P0-B：taxonomy 与 standard unit_id 没对齐

现象：

```text
standard 已经要求 figure_list、table_list、academic_achievements、copyright_notice、originality_authorization_statement 等 unit_id。
当前 T2 仍把其中一部分降成 toc、post_forms、integrity_statement、appendix 或 custom。
```

影响：

```text
后续 T3/T4/T5 收到的是错误 unit_id，策略、分页、section binding 都会错。
```

疑似根因：

```text
UNIT_DEFINITIONS / alias registry / list-like block 类型没有覆盖三校 standard unit_id。
```

### P0-C：边界识别还缺 standard 需要的标题规范化能力

现象：

```text
湖南“摘□要（小四黑体）”不能稳定形成 abstract_cn boundary。
南农“附 录 ...”“致 谢 ...”会被格式说明类文本干扰。
```

影响：

```text
label 阶段再强也拿不到没有形成的 boundary。
```

疑似根因：

```text
canonical title / alias 已存在，但没有前移成 boundary 阶段的 canonical_label_hint。
instruction-like 还是偏布尔判断，没有区分 pure_instruction 和 title_with_format_annotation。
```

### P0-D：缺少 front/body/back 状态机

现象：

```text
北大 seq 50、92、221、302 等正文 Heading 1 被切成 top-level custom。
南农“第X章结论与展望”被切出 body_main。
真正后置区 references / declarations 又会被 duplicate 或 custom 规则误伤。
```

影响：

```text
只看单段 heading 信号，无法判断“这是正文内部章节”还是“这是模板顶层单元”。
```

疑似根因：

```text
当前 T2 是局部边界扫描，没有文档分区状态：
front_matter -> body_main -> back_matter。
```

### P0-E：range ownership 没有进入正式门禁

现象：

```text
issue-02 已记录湖南 seq 50-64、南农 seq 35-36 等 unowned residual。
当前 verifier 不知道哪些 source_seq 是 critical，standard 也没有被用来判定 owner。
```

影响：

```text
无人认领、错归属、expected unit 缺失都可能只停留在人工调试。
```

疑似根因：

```text
缺少 standard-backed unit_range_audit。
```

## 5. 上一轮已解决 / 未解决对照

| 项目 | 当前状态 | 说明 |
| --- | --- | --- |
| TOC entry coverage | 已解决 | 三校 `scripts/t2_metrics.py` 均 PASS |
| TOC block range 外溢 | 已解决 | issue-02 quick fix 后 TOC 不再吞正文段 |
| T1/T2 责任边界 | 已明确 | T1 不输出语义判断；T2 自己派生 |
| 数据流 producer/consumer 文档 | 已补 | 见 `template-parse-refactor-t2-unit-recognition-data-contract.md` |
| 三校 T2 standard 文件 | 已接入 gate | `verifier_state=configured`、`gate_enabled=true` |
| standard-backed verifier | 已解决 | real-core T2 对 `expected.unit_order`、missing/unexpected/custom unit、anchor owner 做 gate |
| taxonomy 对齐 standard | 已解决本轮签收范围 | real-core 三校 T2 audit PASS；后续新增学校仍需扩展 alias/taxonomy |
| front/body/back 状态机 | 已解决本轮签收范围 | 南农/北大正文内部 Heading 1 不再过切成 top-level custom |
| range ownership audit | 已解决本轮签收范围 | real-core 关键 anchors owner audit PASS；content control TOC 支持 source_ref owner |

## 6. 后续验收门禁

本 issue 的下一步 plan 必须提供这些门禁：

```text
1. 标准加载门禁：
   三校 t2_unit_pagination.standard.yaml 能被统一 loader 读取；
   expected.unit_order 与 expected.units[].unit_id 一致。

2. 标准差异门禁：
   当前 unit_map 和 standard expected 的 unit_id/order mismatch 能输出 T2 finding；
   gate 关闭时也要能作为 audit report 打印，不能假装 PASS。

3. taxonomy 门禁：
   figure_list、table_list、academic_achievements、copyright_notice、
   originality_authorization_statement 等 expected unit_id 不能再退化为 custom。

4. 状态机门禁：
   北大正文 Heading 1 source_seq 50 / 92 / 221 / 302 归入 body_main；
   后置 seq 306 references 归入 references；
   南农“第X章结论与展望”归入 body_main。

5. range ownership 门禁：
   expected anchors 命中的关键 source_seq 必须有 owner；
   owner unit_id 必须与 standard expected unit 一致；
   critical unowned 或 mismatch 进入 unit_map.flags / verification_report finding。

6. 非回归门禁：
   三校 TOC coverage 继续 PASS；
   T1 不恢复任何 semantic fields；
   standards/targets/** 不被自动更新。
```

## 7. 讨论结论

本轮 T2 解决方案不应再从“再补一个关键词规则”开始。

正确顺序是：

```text
standard-backed gate 先把裁判接上，
taxonomy / boundary normalization 让 expected unit_id 可被产出，
front/body/back 状态机解决正文内部标题过切，
最后用 range ownership audit 收口。
```
