# real-core-v0 生成模板差距 harness — 测试质量审查

日期：2026-06-17
被审 commit 范围：`7971280..ea4d85b`
审查方式：仅静态审查测试代码。计划自述「11 passed」本次未独立复跑。

## 结论

测试**能证明 harness「跑得通」，但不足以证明「错的会被精确抓住」**。这是本轮审查发现的
**唯一实质性质量缺口**，集中在两点：

1. **缺「隔离变异」测试**——没有「拿一个会 PASS 的样本，只改一处（样式/删元素/删字段），
   断言恰好这一项翻成 FAIL」的测试。
2. **缺端到端 PASS 夹具**——所有 contract 测试喂的都是真实模板，而真实模板当前都预期
   FAIL，于是 **parser→checker 这条链从未被证明能走到一次干净的 PASS**。

正面看，针对真实数据的**正向断言非常扎实**，解析器读 OOXML 的能力被严格锁住。

判定：**够用以验证「实现能工作」，不足以验证「所有失败模式都能被检出」。**

## 审查范围

- `tests/contract/test_real_core_generated_template_gap.py`（11 个测试）
- `tests/unit/test_baseline_comparison.py`、`tests/unit/test_word_evidence.py`（与本 harness 间接相关）
- 对照计划阶段 3（541-548 行）要求的四个夹具

## 逐条评估（contract）

| 测试 | 断言了什么 | 强度 |
| --- | --- | --- |
| `test_real_core_template_gap_outputs_tree_and_reports_for_all_schools`（17-62） | 三校五产物齐全、`input_valid_docx`、sha256 绑定、summary 六字段、`output_docx` 检查项存在 | 🟢 强（真实 DOCX，端到端结构） |
| `test_generated_template_gap_bad_docx_does_not_pass`（65-85） | 空文档（单段「这不是…模板」）→ FAIL、blocking=FAIL、含 `unit_missing` | 🟡 够（唯一合成负样本，但样本退化，只触发 unit_missing） |
| `test_generated_template_gap_reports_ooxml_style_details`（88-114） | 字体「华文行楷」/26pt/居中被解析；存在 `style_mismatch` | 🟡 弱（证明「读得对」，非「改了样式会 FAIL」） |
| `test_generated_template_gap_resolves_ooxml_style_inheritance`（117-148） | 样式继承链 `styles.xml:style[a]`、`line_spacing=exact:20pt` 的 mismatch 精确到 `abstract_cn.e_003.style` | 🟢 强（继承链 + 精确 affected_ids） |
| `test_generated_template_gap_binds_page_rules_to_ooxml_sources`（151-177） | `cover.page.page_break` 的 match（带 `p[...]` 证据）+ `integrity_statement` 的 mismatch | 🟢 强（PASS 与 FAIL 两侧都断言） |
| `test_generated_template_gap_binds_keep_together_to_table_sources`（180-210） | 封面表格 `p[1]-p[21]`、`tbl[1]/tr[1]/cantSplit`、`keep_together` match | 🟢 强（表格 keep 精确绑定） |
| `test_generated_template_gap_binds_header_footer_rules_to_sections`（213-256） | section 的 header/footer 引用、`upperRoman/start=1`、page_number mismatch 精确到 `body_main.header_footer.page_number` | 🟢 强 |
| `test_generated_template_gap_binds_word_fields_to_units`（259-359） | TOC 指令 `TOC \o "1-3" \h \z \u`、SEQ 图/表/公式、字段精确绑定到 `p[133]/field[64]` 等 | 🟢 强（多校、真实 Word 字段） |
| `test_generated_template_gap_binds_numbering_rules_to_units`（362-416） | 编号定义 `第%1章`/`chineseCountingThousand`、ref 经 `styles.xml:style[1]/numPr` 绑定 | 🟢 强 |
| `test_generated_template_gap_missing_docx_is_unknown`（419-434） | 缺文件 → UNKNOWN、blocking=UNKNOWN、含 `output_missing` | 🟢 强（输入层语义） |
| `test_template_gap_status_combination_rules`（437-460） | `summarize_check_items` 的 PASS / PASS+UNKNOWN / FAIL / FAIL+UNKNOWN / UNKNOWN | 🟢 强，但**手搓 dict，绕过解析器与检查器** |

## 两个核心缺口（含取证）

### 缺口一：没有「隔离变异」测试

计划阶段 3（541-548 行）明确点名四个夹具：纯匹配→PASS、样式错→FAIL（指出具体
element/style）、缺来源→PASS+UNKNOWN、双错→FAIL+UNKNOWN。实际只落地了：

- 聚合规则的手搓 dict 测试（test 437-460）——**绕过 parser→checker**，只验证算术；
- 一个退化空文档负样本（test 65-85）——只能触发 `unit_missing`。

**没有任何测试**做「拿一个能匹配的样本，精确改坏一个样式 / 删一个 required element /
删一个字段，断言**恰好这一项**从 PASS 翻成 FAIL，且其余不受影响」。后果：检查器的
**判别边界**（什么算一致、什么算不一致）几乎没有回归保护。现在所有真实样本都
「整体就该 FAIL」，掩盖了单项判别是否准确。

### 缺口二：没有端到端 PASS 夹具

contract 测试里 8 处显式断言 `Status.FAIL`（test 98、131、160、190、225、273、314、376），
没有任何一条让**真实解析链**走到 `display_status == PASS`、`unknown_count == 0`。

**后果**：若检查器某天因 bug 把一切都判 FAIL，CI 仍会全绿——因为真实样本本来就预期
FAIL。`*_match`(PASS) 的逐项断言只证明「部分 PASS 检查项会被产生」，**不等于**汇总能
干净到达 PASS。计划阶段 3 第一条夹具（「纯匹配最小夹具 → display_status=PASS,
unknown_count=0, failed_count=0」）至今缺失。

## 建议补的最小测试集

按性价比排序，全部用 `python-docx` 构造夹具、走真实 `run_template_gap_eval`：

1. **纯匹配夹具 → 干净 PASS**（补缺口二，最高优先）。构造一个最小但完全符合某校
   `expected.units` 的 DOCX，断言 `display_status == "PASS"`、`unknown_count == 0`、
   `failed_count == 0`、`blocking_status == "PASS"`。这是「checker 不是恒 FAIL」的活体证明。
2. **单样式变异 → 定点 FAIL**。在夹具 1 上只改一个 run 的字号，断言新增**恰好一条**
   `template_generation_style_mismatch` 且 `affected_ids` 指向被改元素，其余项不变。
3. **删一个 required element → 定点 FAIL**，断言出现对应 `element_missing` / `unit` 项。
4. **缺来源夹具 → PASS+UNKNOWN**：构造匹配但缺某项来源证据的场景，断言
   `known_status==PASS`、`unknown_count>0`、`blocking_status==UNKNOWN`。
5. **双错夹具 → FAIL+UNKNOWN**：合并 2 与 4，断言 `display_status=="FAIL + UNKNOWN"`、
   `blocking_status=="FAIL"`。
6. （可选）对三校真实样本各打一个 `passed/failed/unknown` 计数的**快照基线**，任何
   静默漂移都会被 diff 出来。

完成 1–5 即正好补齐计划阶段 3 点名的四夹具 + 变异检出，把检查器判别边界纳入回归保护。

## 判定

| 维度 | 判定 |
| --- | --- |
| 解析器正向能力（读 OOXML） | 🟢 强，真实数据严格锁定 |
| 输入层 / 聚合规则语义 | 🟢 强 |
| 失败模式检出（变异） | 🔴 缺口，无隔离变异测试 |
| 端到端 PASS 路径 | 🔴 缺口，从未被证明 |
| 综合测试强度 | 🟡 够用以验证「能跑」，不足以验证「错的会被抓」 |

**总评**：在宣布本阶段「测试完备」前，建议至少补上上面第 1–3 项（端到端 PASS + 两类
变异检出）。这三项工作量小（每项 ~10–20 行夹具），却把当前最大的盲区——「检查器是否
真的会因为正确而 PASS、因为错误而 FAIL」——补成回归可保护。
