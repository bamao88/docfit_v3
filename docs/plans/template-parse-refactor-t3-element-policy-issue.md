---
status: draft
owner: template-generation
stage: T3
severity:
  - P0
  - P1
created: 2026-06-25
last_updated: 2026-06-25
version: 2
evidence_run:
  code_checkpoint: 22caef2
  output_root: /private/tmp/docfit_t3_inspect
  command: "uv run python -B -c 'from pathlib import Path; from docfit.convert.orchestrator import run_template_generate_eval; ...'"
related_docs:
  - docs/plans/template-parse-refactor-stage-issues.md
  - docs/plans/template-parse-refactor-t2-boundary-label-issue.md
  - docs/plans/template-parse-refactor-t2-unit-map.md
  - docs/plans/template-parse-refactor-t2-post-optimization-residual-unit-issues.md
  - docs/plans/template-parse-refactor-copy-only-policy-bug.md
related_code:
  - src/docfit/template_generation/structure_candidates.py
  - src/docfit/template_generation/generation_model.py
  - src/docfit/template_generation/artifacts.py
  - src/docfit/template_generation/verifier.py
  - src/docfit/template_generation/constants.py
---

# T3 元素策略 issue（上一轮优化后残余问题记录）

Last updated: 2026-06-25

本文只记录 T3 **上一轮优化后当前仍存在**的问题，以及每个问题的环节定位。已解决的问题（element 置信度全员硬编码 medium）不再作为待解决项记录，只放在完成度对照里。

一句话结论：T3 自身已没有结构性 FAIL，置信度噪声也已清掉。**当前 T3 残余的不确定项 100% 落在两个真问题上**：(1) copy-only 单元内部的 `fill`/`generated` 候选被静默降级成 `fixed`（学生应填字段被冻结）；(2) 弱证据的“推断 fill”缺 gold 无法精确判。另外 T5 仍把 T3 的 flag 重投影一次，让 T3 的计数在报告里翻倍。

证据来自三校当前代码重跑（输入 `inputs/targets/<school>/raw/source_template.docx`，输出 `/private/tmp/docfit_t3_inspect/<school>`）。

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
| 湖南农大 | 320 | 275 / 45 / 0 | 0 |
| 南农本科 | 103 | 93 / 10 / 0 | 0 |
| 北大研究生 | 359 | 319 / 40 / 0 | 0 |

三校 T3 仍是 `UNKNOWN`，但 UNKNOWN 不再来自全员 medium，而来自下面这批**有意义的 medium**。

### 2.2 残余 medium 的成分（精确指向两个环节）

| 学校 | 残余 medium | = role 降级（student/gen → fixed） | = 推断 fill（无显式 marker） | 其它 |
| --- | ---: | ---: | ---: | ---: |
| 湖南农大 | 45 | 31 | 14 | 0 |
| 南农本科 | 10 | 4 | 6 | 0 |
| 北大研究生 | 40 | 36 | 4 | 0 |

残余 100% 落在两类，没有第三类杂音。这两类就是下面的 ISSUE-002 和 ISSUE-004。

### 2.3 role 与 policy 不一致（ISSUE-002 的直接证据）

| 学校 | role=student_content 但 policy=fixed | role=generated_field 但 policy=fixed |
| --- | ---: | ---: |
| 湖南农大 | 31（cover + post_forms） | 0 |
| 南农本科 | 2 | 2 |
| 北大研究生 | 3 | 33 |

注意北大 33 个 `generated_field → fixed`：经核实，**真正的 `目录` 单元是受保护的**（`toc` 在 copy-only 排除集里，`copy_only=False`，图目录条目 `generated` 正常保留）。这 33 个里**大多是 `other`/`custom` 单元里含“编号/目录/公式”字样的 Word 使用说明文字**，被 `GENERATED_MARKERS` 宽匹配误判成 generated，再被 copy-only 压回 fixed——即“假阳性 generated + 反向 copy-only 默认”两个错叠加，净效果暂时无害但两步都错。详见 [copy-only-policy-bug](template-parse-refactor-copy-only-policy-bug.md)。

这些 element 的 `evidence.heuristic_policy_hint` 是 `fill`/`generated`，但最终 `policy=fixed`。三种信号（role_hint、evidence hint、final policy）互相打架。

例子（湖南农大）：

- `□□□□□□年级专业及班级：20××级×××（×）班`（role=student_content, hint=fill, policy=**fixed**）
- `□□□□□□学□□院：××××学院（学院名用全称）`
- 后置表单里大量 `□结合科研课题 课题名称：…`

这些都是学生要填的位置，现在被当成固定文字冻结。修复后这批以 `confidence=medium` 浮现，可以被看见，但 verifier 仍没有针对“降级”本身的 finding。

### 2.4 上一轮优化完成度对照

| 项目 | 上一轮后现状 | 结论 |
| --- | --- | --- |
| element 置信度全员硬编码 medium | 已改为基于最终 policy / marker / role_hint 计算 | 已解决 |
| role_hint 与 final policy 冲突可见性 | 冲突项会以 `confidence=medium` 进入 review flag | 部分解决：只暴露，未修语义 |
| copy-only 内部 fill/generated 被压成 fixed | `_final_policy_for_generation()` 仍压成 `fixed` | 未解决 |
| T3 verifier 显式识别 policy 降级 | 仍只做闭集、fill_source、manual_semantics、generated.field_type 检查 | 未解决 |
| 行内格式注释残留 | 最终 docx 仍残留 `（小二黑体加粗）`、`(二号黑体，居中)` 等 | 未解决 |
| policy/gold 级 expected | 仍没有 `element_spec.expected.yaml` | 未解决 |
| T5 重投影 T3 flag | T5 仍把 T3 confidence flag 再报一次 | 未解决 |

---

## 3. 当前未解决问题

### T3-ISSUE-002：copy-only 单元内部的 fill/generated 候选被静默降级成 fixed

> 根因层已单列为 bug：[copy-only 策略写死 + unknown 默认 copy-only](template-parse-refactor-copy-only-policy-bug.md)。本节只记录 T3 侧的症状与门禁盲区。

现象：单元被判成整单元 copy-only 后，内部所有非 `instruction_remove`/`manual_only` 的 element（含 `fill`、`generated`）被强制改成 `fixed`，学生应填字段被冻结，最终 Word 不会出现可填字段。

环节定位（按数据流顺序）：

1. **T2 单元粒度** `constants.py:5 COPY_ONLY_DEFAULT_EXCLUDED_UNIT_IDS = {abstract_cn, abstract_en, toc, body_main, references}` —— 只有这 5 个单元不走 copy-only；cover / integrity_statement / acknowledgement / appendix / **post_forms** 等默认 copy-only。
2. **生成模式** `generation_model.py:_unit_generation_mode()` —— copy-only 单元 + 有 source ref ⇒ `whole_unit_copy`。
3. **策略坍缩（根因）** `generation_model.py:141 _final_policy_for_generation()`：

   ```python
   def _final_policy_for_generation(candidate_policy, generation_mode):
       if generation_mode != "whole_unit_copy":
           return candidate_policy
       if candidate_policy in {"remove_instruction", "manual_only"}:
           return candidate_policy
       return "fixed"   # fill / generated 全部坍缩成 fixed
   ```

4. **verifier 盲区** `verifier.py:386 _verify_t3_element_spec()` —— 只检查 policy 是否在闭集、fill 是否有 fill_source、manual 是否有 semantics、generated 是否有 field_type；**不检查 role_hint / evidence hint 与 final policy 是否自洽**，所以降级没有专门 finding，只能靠 `confidence=medium` 间接暴露。

影响：湖南农大 cover 的姓名/学号/学院/日期、post_forms（任务书/开题/答辩/成绩）里的填写位，现在都成了固定文字。这正是 stage-issues 里 T2「固定 9 个 unit 粒度过粗 / 粗边界内做策略，责任混在一起」那条的实证落点。

讨论焦点：这是产品语义冲突——“整单元保形复制”和“单元内部仍有学生填写位”同时成立，`whole_unit_copy` 把两者一刀切了。环节在 **T2 copy-only 粒度 + generation_model final policy**，不在置信度本身。

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

### T3-REPORT-001：T5 把 T3 flag 重投影，T3 计数翻倍

现象：T5 读 `template_spec.review_flags` 后，把 T3 每条 `element_confidence_needs_review` 再报一次 `t5_element_confidence_needs_review`。

环节定位：`verifier.py:797 _verify_t5_template_spec()`。这是报告层问题，不是 T3 生成判定错，但它让 T3 的不确定项数量在报告里看起来翻倍（例如当前湖南 T3 45 条，T5 再报 45 条，相关 finding 看起来变成 90 条）。

---

## 4. 清完噪声后浮现的跨阶段事实（供排序参考）

T3 不再是“全员 medium”噪声后，三校瓶颈重新排序（当前 template-generate 重跑，含 T5 重投影）：

| 学校 | 总 findings | T2 类（T2 stage） | T3 类（T3 stage） | T5 重投影/自身项 | 主瓶颈 |
| --- | ---: | --- | --- | --- | --- |
| 湖南农大 | 120 | unit_confidence 9 + repeated_custom 4 + boundary_keyword_only 2 | confidence 45 | T3 confidence 45 + T2 flag 15 | T3 降级 + T2 标签/边界 |
| 南农本科 | 36 | unit_confidence 5 + repeated_custom 1 | confidence 10 | T3 confidence 10 + T2 flag 6 + cross_section 4 | T2/T3 较均衡 |
| 北大研究生 | 117 | unit_confidence 10 + repeated_custom 6 | confidence 40 | T3 confidence 40 + T2 flag 16 + cross_section 3 + T4/global 2 | T3 降级 + T2 正文/后置单元 |

结论：

- T3 自身剩 ISSUE-002（降级）+ ISSUE-004（gold）+ ISSUE-005（行内注释删不掉），ISSUE-002 现已以 medium 可见。
  注意 ISSUE-005 不进 confidence findings（这些段判成 fixed/generated 多为 high），属于“静默残留”，需专门检查或 gold 才能捕获。
- 北大 T2 过切已较旧口径下降，但 `body_main` 范围、图目录/表目录、后置声明等仍有残余问题（见 t2-post-optimization-residual-unit-issues），与 T3 降级问题互相放大。
- T5 重投影是下一个该处理的报告层问题（REPORT-001）。

---

## 5. 需要讨论的问题

1. copy-only 单元（cover / post_forms 等）内部的 fill 候选，应该：(a) 保持 `whole_unit_copy` 一律 fixed，把填写位交给后续人工；(b) 升级成 `copy_then_patch`，在保形复制基础上对 fill 候选开可填域；还是 (c) 按单元区分（cover 开洞、post_forms 保形）？
2. `_final_policy_for_generation` 把 `generated` 也坍缩成 fixed 合理吗？目录/页码这种生成域被冻结，是否会让 T6 缺 PAGE/TOC 域？
3. role/policy 不一致应该升成显式 finding（`t3_policy_downgraded_in_copy_only`）吗？是 FAIL（确定错）还是 UNKNOWN（需人工）？
4. T3 的 gold 先做内容级 expected，还是先做 policy 级 expected？先做哪一校？
5. 行内格式注释（ISSUE-005）走哪条路：(a) 段内 run 级剥离括号注释，保留真内容；(b) 把 element 切得更细，让注释单独成 element 再 remove；还是 (c) 先只扩 marker 覆盖、暂不做段内剥离？

---

## 6. 非目标

- 不在本 issue 改 T2 单元边界（见 t2-boundary-label-issue）。
- 不在本 issue 解决 T4 页码 / 分节 high confidence。
- 不在本 issue 实现完整 AI 元素分类（`ai_traces`），只决定哪些 element 类型允许走 AI。
- 不在本 issue 实现 review queue / review_decisions 闭环（跨 T3/T5，单列）。
