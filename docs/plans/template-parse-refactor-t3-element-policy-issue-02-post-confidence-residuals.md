---
status: draft
owner: template-generation
stage: T3
topic: element-policy
issue_id: T3-ELEMENT-ISSUE-02
issue_sequence: 2
severity:
  - P0
  - P1
created: 2026-06-25
last_updated: 2026-06-25
version: 3
previous_issue:
  id: T3-ELEMENT-ISSUE-01
  doc: docs/plans/template-parse-refactor-t3-element-policy-issue-01-confidence-noise.md
previous_optimization:
  doc: docs/plans/template-parse-refactor-t2-copy-only-policy-issue-02-disable-copy-only.md
  summary: "default copy-only disabled; whole_unit_copy / preserve_whole_unit_copy / fill-generated-to-fixed collapse are all zero in current three-school rerun"
next_plan: TBD
evidence_run:
  code_checkpoint: 750bbf3
  output_root: /private/tmp/docfit_copy_only_verify
  command: "uv run python -B -c 'from pathlib import Path; from docfit.convert.orchestrator import run_template_generate_eval; ...'"
related_docs:
  - docs/plans/template-parse-refactor-issue-index.md
  - docs/plans/template-parse-refactor-t3-element-policy-issue-01-confidence-noise.md
  - docs/plans/template-parse-refactor-t2-copy-only-policy-issue-02-disable-copy-only.md
  - docs/plans/template-parse-refactor-stage-issues.md
  - docs/plans/template-parse-refactor-t2-unit-recognition-issue-01-boundary-label.md
  - docs/plans/template-parse-refactor-t2-unit-map.md
  - docs/plans/template-parse-refactor-t2-unit-recognition-issue-02-post-phase2-residuals.md
  - docs/plans/template-parse-refactor-copy-only-policy-bug.md
related_code:
  - src/docfit/template_generation/structure_candidates.py
  - src/docfit/template_generation/generation_model.py
  - src/docfit/template_generation/artifacts.py
  - src/docfit/template_generation/verifier.py
  - src/docfit/template_generation/constants.py
---

# T3 元素策略 Issue 02：confidence 优化后残余问题

Last updated: 2026-06-25

本文只记录 T3 **上一轮优化后当前仍存在**的问题，以及每个问题的环节定位。已解决的问题（element 置信度全员硬编码 medium、默认 copy-only 导致的 fill/generated 降级）不再作为当前待解决项记录，只放在完成度对照里。

一句话结论：默认 copy-only 已关闭，三校 `whole_unit_copy=0`、`preserve_whole_unit_copy=0`、`fill/generated -> fixed` 降级=0。**当前 T3 残余问题不再是 copy-only 冻结，而是 T3 自身的元素策略标准过粗**：弱证据“推断 fill”缺 gold 无法精确判；行内格式说明无法段内剥离；`fixed/generated/instruction_remove/fill` 的视觉与 run 级边界没有门禁。另外 T5 仍把 T3 的 flag 重投影一次，让 T3 的计数在报告里翻倍。

证据来自三校当前代码重跑（输入 `inputs/targets/<school>/raw/source_template.docx`，输出 `/private/tmp/docfit_copy_only_verify/<school>`）。

主产物：`03_element_spec.yaml`

---

## 0. 记录目的与流程约定

本文件是后续讨论 T3 优化的事实基线。讨论解法前，先用本文件确认：

1. 上一轮 T3 优化到底解决了什么。
2. 当前真实运行还剩哪些问题。
3. 哪些问题本应由上一轮解决但仍未解决。
4. 后续每个修复必须补什么验证门禁。

阶段优化流程约定：

- 讨论某阶段优化前，先新增或更新对应 `docs/plans/*issue*.md`。
- issue 文档必须记录真实运行命令/输出、expected vs observed、疑似根因、上一轮已解决/未解决对照、验收门禁。
- 方案讨论必须围绕 issue 文档进行，不能把“计划要解决”当成“已经解决”。

### 0.1 迭代链与命名

本轮 T3 元素策略文档链：

| 顺序 | 类型 | 文档 | 状态 | 用途 |
| --- | --- | --- | --- | --- |
| 01 | issue | `docs/plans/template-parse-refactor-t3-element-policy-issue-01-confidence-noise.md` | resolved | 上一轮：element confidence 全员 medium 噪声 |
| 01 | optimization reference | `docs/current/template-generation-stage-optimization.md` | implemented in part | 上一轮：confidence 分级与 copy-only 责任边界优化背景 |
| 02 | upstream fix | `docs/plans/template-parse-refactor-t2-copy-only-policy-issue-02-disable-copy-only.md` | implemented | 默认关闭 copy-only，排除上游冻结干扰 |
| 02 | issue | `docs/plans/template-parse-refactor-t3-element-policy-issue-02-post-confidence-residuals.md` | draft | 本文档：copy-only 排除后仍存在的 T3 元素策略问题 |
| 02 | optimization plan | TBD | pending | 后续针对本文档讨论出的下一轮修复方案 |

命名约定见 `docs/plans/template-parse-refactor-issue-index.md`。

---

## 1. 阶段边界（定位问题用）

T3 的“生成判定”分布在三个文件，讨论环节时必须区分：

```text
document_facts
  -> structure_candidates._element_policy / _element_from_entries   # 候选 policy（marker 分类）
  -> generation_model._final_policy_for_generation                  # 最终 policy（可能坍缩）
  -> artifacts.build_element_spec                                    # 落 element_spec + flag + confidence
  -> verifier._verify_t3_element_spec                               # 门禁判定
```

| 判定类型 | 谁做 | 产出 |
| --- | --- | --- |
| 生成判定 | `_element_policy` → `_final_policy_for_generation` | element 的 `policy`、`role`、`confidence`、`evidence` |
| 门禁判定 | `_verify_t3_element_spec` | `t3_element_*` finding、T3 `PASS/UNKNOWN/FAIL` |

一个 element 被写成 `fixed`，只是生成判定；verifier 是否放行是另一回事。当前问题恰恰是**生成判定有错、门禁判定看不见**。

---

## 2. 当前数据

口径：run 起点 `inputs/targets/<school>/raw/source_template.docx`，工作树重跑。

### 2.1 T3 置信度现状（噪声已清）

| 学校 | element 总数 | high / medium / low | T3 结构性 FAIL |
| --- | ---: | --- | ---: |
| 湖南农大 | 298 | 284 / 14 / 0 | 0 |
| 南农本科 | 96 | 90 / 6 / 0 | 0 |
| 北大研究生 | 343 | 339 / 4 / 0 | 0 |

三校 T3 仍是 `UNKNOWN`，但 UNKNOWN 不再来自全员 medium，而来自下面这批**有意义的 medium**。

### 2.2 残余 medium 的成分（copy-only 排除后）

| 学校 | 残余 medium | = role 降级（student/gen → fixed） | = 推断 fill（无显式 marker） | 其它 |
| --- | ---: | ---: | ---: | ---: |
| 湖南农大 | 14 | 0 | 14 | 0 |
| 南农本科 | 6 | 0 | 6 | 0 |
| 北大研究生 | 4 | 0 | 4 | 0 |

残余 medium 现在 100% 是“推断 fill”（没有显式 marker + label 组合），copy-only 降级类已经归零。这些 medium 主要暴露 ISSUE-004：缺少 gold expected，无法判断弱证据 fill 是正确学生内容、模板示例内容，还是应该保留/删除的说明。

### 2.3 copy-only 降级复核（已归零）

| 学校 | `whole_unit_copy` strategies | `preserve_whole_unit_copy` actions | `fill/generated -> fixed` 降级 |
| --- | ---: | ---: | ---: |
| 湖南农大 | 0 | 0 | 0 |
| 南农本科 | 0 | 0 | 0 |
| 北大研究生 | 0 | 0 | 0 |

结论：当前 T3 讨论不再把 copy-only 作为主因。后续如果再次出现 role/evidence/final policy 打架，应先检查是否来自显式学校配置、旧产物或手工恢复 copy-only，而不是默认策略。

### 2.4 当前 policy 分布

| 学校 | fixed | fill | generated | manual_only | instruction_remove |
| --- | ---: | ---: | ---: | ---: | ---: |
| 湖南农大 | 153 | 45 | 27 | 41 | 32 |
| 南农本科 | 32 | 9 | 29 | 2 | 24 |
| 北大研究生 | 252 | 8 | 56 | 2 | 25 |

注意：`fixed/generated/instruction_remove` 多数都是 `confidence=high`。这不代表视觉上一定正确，只代表当前规则认为它们足够确定。行内格式说明残留和 generated 假阳性，很多不会进入 `element_confidence_needs_review`，需要单独 gold 或视觉/run 级门禁。

### 2.5 上一轮优化完成度对照

| 项目 | 上一轮后现状 | 结论 |
| --- | --- | --- |
| element 置信度全员硬编码 medium | 已改为基于最终 policy / marker / role_hint 计算 | 已解决 |
| 默认 copy-only 导致 fill/generated 被压成 fixed | 三校 `whole_unit_copy=0`、降级=0 | 已解决/已从当前 T3 主因排除 |
| role_hint 与 final policy 冲突可见性 | 当前三校冲突=0；若未来恢复 copy-only 仍需显式 finding | 暂不作为当前 T3 主问题 |
| 行内格式注释残留 | 最终 docx 仍残留 `（小二黑体加粗）`、`(二号黑体，居中)` 等 | 未解决 |
| 元素 policy 打标标准 | 仍是段落文本规则 + unit_id，没有视觉/run 级 gold 门禁 | 未解决 |
| policy/gold 级 expected | 仍没有 `element_spec.expected.yaml` | 未解决 |
| T5 重投影 T3 flag | T5 仍把 T3 confidence flag 再报一次 | 未解决 |

### 2.6 当前 T3 打标流程与标准

当前 T3 打标不使用视觉渲染结果，也不做 run 级切分；它只基于 T2 分出的 unit、T1 文本/样式事实、以及 `_element_policy()` 的规则顺序。

流程：

```text
T1 body_flow entries
  -> T2 unit range
  -> T3 _logical_entry_groups() 合并 entry
  -> _element_policy(unit_id, text, first_entry) 产出 candidate_policy
  -> generation_model materialize 成最终 policy
  -> element_spec 写 role / fill_source / generated.field_type / confidence
```

当前 `_element_policy()` 判定顺序：

| 顺序 | policy | 当前标准 | 主要风险 |
| --- | --- | --- | --- |
| 1 | `instruction_remove` | `_looks_like_instruction(text)` 命中说明文字 marker 或括号字体/字号正则 | 粒度是整段；真内容+行内说明会被整段保留，无法只删括号说明 |
| 2 | `generated` | unit 是 `toc`，或文本含 `目录/页码/编号/图目录/表目录/公式` | 说明文字里出现这些词会误判 generated，且常被 high confidence 放行 |
| 3 | `manual_only` | 文本含 `签名/年月日/年  月  日/意见/成绩/评定` | 表单说明与真实人工填写区边界粗糙 |
| 4 | 显式 `fill` | 同时命中占位符 marker（`××/□□/____/——/：/:`）和 label（`题名/题目/姓名/学号/学院/...`） | label/marker 表窄，漏掉复杂表格和段内字段 |
| 5 | 推断 `fill` | unit 属于 `abstract_cn/abstract_en/body_main/references` 且 entry 不是 heading | 这是当前全部 medium 来源，缺 gold 无法判断对错 |
| 6 | `fixed` | 以上都不命中 | 视觉残留、行内说明、误分类内容可能被 high confidence 静默保留 |

---

## 3. 当前未解决问题（不含 copy-only）

### T3-ISSUE-002：copy-only 降级类问题已从当前 T3 主线排除

状态：当前三校重跑中，默认 copy-only 已关闭，`whole_unit_copy=0`、`preserve_whole_unit_copy=0`、`fill/generated -> fixed` 降级=0。

后续处理：

- 本 issue 后续讨论不再把 copy-only 当作 T3 残余主因。
- copy-only 的历史问题和未来恢复条件见 `template-parse-refactor-t2-copy-only-policy-issue-02-disable-copy-only.md`。
- 如果未来重新接入学校级 copy-only 配置，必须补 `t3_policy_downgraded_in_copy_only` 或等价门禁，防止内部 fill/generated 再次被静默冻结。

### T3-ISSUE-004：误删/误填的边界没有 gold 验证

现象：`instruction_remove` 有基础 marker 规则（`INSTRUCTION_MARKERS`），但没有 `element_spec.expected.yaml`，无法证明“格式说明被删、真实正文括号内容被保留”的边界是对的。弱证据的“推断 fill”（`_element_policy` 里“内容单元且非标题 ⇒ fill”分支，无显式占位 marker）也只能保留 medium，无法判对错。`ai_traces` 为空，计划里的 AI 残余分类未落地。

环节定位：

- 推断 fill 的判定环节在 `structure_candidates.py:_element_policy()`。
- 误删判定环节在 `_looks_like_instruction()` + `INSTRUCTION_MARKERS`。
- 两者都缺 `element_spec.expected.yaml` 做精确比对，所以 T3 现在只能做 schema/policy 闭集门禁，不能做内容级比对；误删真内容这种 P0 风险无法被门禁捕获。

### T3-ISSUE-005：行内格式注释删不掉（识别粒度是段落级，注释是行内级）

现象：湖南农大最终 docx 里残留大量格式说明文字，且“该删的没删”。核实是 **T3 识别没打删除 tag**，不是执行没做。

执行侧已排除：湖南 `build_manifest` 里 `remove_instruction_text` **executed=43、requiring_review=0**——凡是打了 `instruction_remove` 的（39 个 element + 表格单元格）最终都删掉了。

识别侧才是问题。把每个 element 还原成源文字后，看起来像说明文字的段落分布：

| policy | 数量 | 结局 |
| --- | ---: | --- |
| `instruction_remove` | 39 | 删 ✅ |
| `fixed` | 21 | 保留 ❌ |
| `generated` | 5 | 保留 ❌ |
| 其它 | 6 | 保留 |

其中 25 条确认仍出现在最终 docx。把这些样例丢回 `_looks_like_instruction()` 全部返回 `False`，两个原因：

1. **行内注释和真内容混在同一段，被故意整段保留**：

   ```python
   # structure_candidates.py  _looks_like_instruction()
   if _has_substantive_template_text(text) and re.search(
           r'[（(].*(宋体|黑体|楷体|居中|行距|字号|号字|pt).*[）)]', text):
       return False   # 有真内容 + 字体注释 ⇒ 判"不是说明"，整段保留
   ```

   意图是不把真标题/目录/摘要 label 连注释一起删掉。副作用：行内 `（小二黑体加粗）` 跟着留下。例：`毕业论文（设计）中文题目（小二黑体加粗）`、`目□□录(二号黑体，居中)`、`□□摘□要（小四黑体）：…（五号宋体）`、参考文献示例 `[1]…(五号宋体)`。

2. **注释用词超出 marker 表，连兜底正则都没命中**：`（一号华文行楷加粗）`（“华文行楷/加粗”不在 `宋体|黑体|楷体|居中|行距|字号|号字|pt`）、`（学院名用全称）`（“用全称”无字体词）。

环节定位：`structure_candidates.py:_looks_like_instruction()` + `INSTRUCTION_MARKERS` / 字体注释正则。**根本是粒度错配**：T3 的 element 和 `remove_instruction_text` action 都是段落级，但这些说明文字是段内行内级（真内容 + 括号注释同段），段落级“删/不删”二选一处理不了，现在选了“留”。

与 ISSUE-004 的区别：ISSUE-004 担心“删多了”（误删真内容），本 issue 是“该删的没删/删不干净”。两者方向相反，但都源于同一处缺口——缺段内剥离能力 + 缺 gold 验证。

修复方向（待讨论，勿直接整段标 remove，否则会删掉真标题/目录/摘要）：

- **段内/run 级剥离**：保留真内容，只删括号里的格式注释 `（…字体…）`。
- **扩 marker 覆盖**：补 `华文行楷`、`加粗`、`用全称`、`居中` 等漏词。

### T3-ISSUE-006：元素 policy 打标标准过粗，视觉残留不进门禁

现象：当前 T3 的 confidence finding 已经降到湖南 14 / 南农 6 / 北大 4，但从最终 Word 视觉检查看，残留问题仍明显。这说明 T3 的主要风险已经不在 `medium` 数量，而在**错误 high confidence**：

- 行内说明文字被保成 `fixed high`。
- 含“目录/编号/公式”的说明段可能被标成 `generated high`。
- 内容单元里的示例文字、模板提示、正文样例可能被推断为 `fill medium`，但没有 gold 能判断应填、应删还是应保留。
- `fixed` 的标准只是“其它都不命中”，非空即 high，缺少“这是否是可见目标模板内容”的验证。

环节定位：

- 候选 policy：`structure_candidates.py:_element_policy()`。
- confidence：`artifacts.py:_element_confidence()`。
- 门禁：`verifier.py:_verify_t3_element_spec()` 只做 schema/policy 闭集检查，不做视觉残留、run 级注释、policy/gold 对比。

为什么这是当前主问题：copy-only 排除后，`role_hint` 与 final policy 的冲突归零；但 `fixed/generated/instruction_remove` 大量 high confidence 仍可能是错的。仅看 T3 finding 数，会低估视觉质量问题。

修复方向：

- 建 `element_spec.expected.yaml`，先做 policy 级 expected，再扩内容级 expected。
- 引入 run/inline 级 instruction span，不能只做段落级 `instruction_remove`。
- `generated` marker 从宽匹配改为字段上下文/TOC unit/OOXML field 证据优先。
- `fixed high` 需要 gold 或更强证据，不能把“不认识”直接当“确定固定模板内容”。

### T3-REPORT-001：T5 把 T3 flag 重投影，T3 计数翻倍

现象：T5 读 `template_spec.review_flags` 后，把 T3 每条 `element_confidence_needs_review` 再报一次 `t5_element_confidence_needs_review`。

环节定位：`verifier.py:797 _verify_t5_template_spec()`。这是报告层问题，不是 T3 生成判定错，但它让 T3 的不确定项数量在报告里看起来翻倍（例如当前湖南 T3 14 条，T5 再报 14 条，相关 finding 看起来变成 28 条）。

---

## 4. 清完噪声后浮现的跨阶段事实（供排序参考）

T3 不再是“全员 medium”噪声后，三校瓶颈重新排序（当前 template-generate 重跑，含 T5 重投影）：

| 学校 | 总 findings | T2 类（T2 stage） | T3 类（T3 stage） | T5 重投影/自身项 | 主瓶颈 |
| --- | ---: | --- | --- | --- | --- |
| 湖南农大 | 58 | unit_confidence 9 + repeated_custom 4 + boundary_keyword_only 2 | confidence 14 | T3 confidence 14 + T2 flag 15 | T3 policy/gold + T2 标签/边界 |
| 南农本科 | 27 | unit_confidence 5 + repeated_custom 1 | confidence 6 | T3 confidence 6 + T2 flag 6 + cross_section 3 | T2/T3 较均衡 |
| 北大研究生 | 45 | unit_confidence 10 + repeated_custom 6 | confidence 4 | T3 confidence 4 + T2 flag 16 + cross_section 3 + T4/global 2 | T2 正文/后置单元 + T3 high-confidence 静默风险 |

结论：

- T3 自身当前主问题是 ISSUE-004（gold）、ISSUE-005（行内注释删不掉）、ISSUE-006（打标标准过粗，错误 high confidence 静默放行）。
  注意 ISSUE-005/006 不一定进入 confidence findings，需专门检查或 gold 才能捕获。
- 北大 T2 过切已较旧口径下降，但 `body_main` 范围、图目录/表目录、后置声明等仍有残余问题（见 `template-parse-refactor-t2-unit-recognition-issue-02-post-phase2-residuals.md`），会继续放大 T3 policy/gold 判断难度。
- T5 重投影是下一个该处理的报告层问题（REPORT-001）。

---

## 5. 需要讨论的问题

1. T3 的 gold 先做 policy 级 expected，还是内容级 expected？先做哪一校？
2. 行内格式注释（ISSUE-005）走哪条路：(a) 段内 run 级剥离括号注释，保留真内容；(b) 把 element 切得更细，让注释单独成 element 再 remove；还是 (c) 先只扩 marker 覆盖、暂不做段内剥离？
3. `generated` 是否必须要求更强证据：TOC unit、OOXML field、明确页码/编号字段上下文，而不是文本宽匹配？
4. `fixed high` 的放行标准是否要收紧：哪些固定文本可以 high，哪些“其它都不命中”的内容应进入 review？
5. 推断 fill 是否应继续允许 references/body_main 全内容单元默认 fill，还是必须有更明确的学生内容槽位证据？

---

## 6. 非目标

- 不在本 issue 改 T2 单元边界（见 t2-unit-recognition issue 链）。
- 不在本 issue 解决 T4 页码 / 分节 high confidence。
- 不在本 issue 实现完整 AI 元素分类（`ai_traces`），只决定哪些 element 类型允许走 AI。
- 不在本 issue 实现 review queue / review_decisions 闭环（跨 T3/T5，单列）。
