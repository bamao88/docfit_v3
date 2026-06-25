# 模板解析重构阶段问题清单

Last updated: 2026-06-25

本文是后续讨论用的问题台账。它只记录当前模板解析和可填模板生成支撑链路的问题，不讨论学生内容提取、placement、最终 render 的业务质量。

当前证据来自本地三校 run：

```text
test_outputs/debug/template_generation/template_parse_refactor_20260625T110707+0800/hunannongye
test_outputs/debug/template_generation/template_parse_refactor_20260625T110707+0800/nannong-undergraduate
test_outputs/debug/template_generation/template_parse_refactor_20260625T110707+0800/pku-graduate
```

## 术语先说清楚

这些词不是给用户看的产品文案，而是模板解析内部用来判断“能不能自动放行”的工程信号。

### `confidence`

`confidence` 表示系统对某个判断的证据强度。它不是学校标准里的概念，也不是最终质量分。


| 值        | 具体意思                           | 当前门禁含义                      |
| -------- | ------------------------------ | --------------------------- |
| `high`   | 规则证据足够强，系统认为可以自动放行             | 可以 `PASS`，不需要人工审核           |
| `medium` | 有证据，但证据还不够强；系统能猜出一个结果，但不应该假装确定 | 进入 `UNKNOWN`，需要规则增强或人工审核    |
| `low`    | 证据不足，系统只是保底生成了一个结果             | 进入 `UNKNOWN`，通常需要人工审核或补解析规则 |


例子：

- T2 里一个 unit 被识别成 `cover`，如果只是因为某段文字像封面，就可能是 `medium`。
- 如果它同时满足标题词命中、位置在文档开头、source range 连续、边界清晰，后续可以讨论是否升成 `high`。
- T3 里一个元素被识别成 `instruction_remove`，如果它明确包含“格式说明”“字体要求”等说明词，可能可以是 `high`。
- 如果它只是括号里的短文本，例如“(设计)”这种可能是真内容，就不应该轻易 `high`。

当前实现的问题是：很多 unit/element 的 `confidence` 还没有真正分级，基本默认写成 `medium`。所以报告里出现大量 `confidence=medium requires review`，更像是在提醒“置信度规则还没建好”，不是说这些位置一定错了。

### `UNKNOWN`

`UNKNOWN` 表示系统不能确定当前判断是否正确。

它不是失败，不等于 Word 不能生成；它的含义是：

```text
我能产出一个结果，但没有足够证据自动宣称这个结果正确。
```

在当前门禁里，只要 T1-T6 任一阶段是 `UNKNOWN`，整体就不能宣称模板解析成功。三校现在都是这种情况：T6 Word 构建过了，但 T2/T3/T4/T5 还有未审核不确定项。

### `PASS`

`PASS` 表示这个阶段的 deterministic verifier 没发现阻断项。

注意：某个阶段 `PASS` 不代表全链路成功。例如当前 T6 是 `PASS`，只说明：

- `06.1_fillable_template.docx` 是有效 DOCX。
- SDT tag、manifest hash 等构建证据过了。
- 没有残留内部 `[[DOCFIT_*]]` 文本 marker。

它不代表 T2/T3/T4 的解析判断一定正确。

### `FAIL`

`FAIL` 表示系统已经确定违反硬规则。

例子：

- required unit 缺失。
- `fill` 元素没有 `fill_source`。
- 输出 docx 无效。
- 需要的 SDT tag 缺失。

`FAIL` 和 `UNKNOWN` 的区别是：`FAIL` 是确定错；`UNKNOWN` 是无法证明对。

### `flags`

`flags` 是各阶段 artifact 里记录“不确定或需要审核”的原始桶。

常见位置：


| 阶段  | 字段                                        |
| --- | ----------------------------------------- |
| T2  | `unit_map.flags`、`units[].flags`          |
| T3  | `element_spec.flags`、`elements[].flags`   |
| T4  | `global_spec.flags`                       |
| T5  | `template_spec.review_flags`              |
| T6  | `build_manifest.actions_requiring_review` |


verifier 会读取这些字段，把它们转成 `verification_report.json` 里的 findings。

### `review_flags`

`review_flags` 是 T5 `template_spec.yaml` 里的审核汇总字段。

它现在的作用是把 T2/T3/T4 的 flags 汇总到主 spec，方便后续做人工审核。但当前实现有一个问题：verifier 在 T2/T3/T4 已经报过这些 flags，到了 T5 又逐条再报一次，所以数量会翻倍。

### `finding`

`finding` 是 verifier 输出的一条问题记录。

它通常包含：

- `type`：问题类型，例如 `t3_element_confidence_needs_review`。
- `status`：`PASS` / `FAIL` / `UNKNOWN` 里的阻断状态。
- `actual`：实际看到的情况。
- `affected_ids`：影响到的 unit 或 element。

finding 是报告层概念，不是源 Word 里的对象。

### `issue_clusters`

`issue_clusters.json` 是把 findings 按类型和原因聚合后的报告。

它适合快速看“有几类问题”，不适合看每个元素细节。比如湖南农大现在 650 个 findings 聚成 4 个 clusters，说明它们主要是 4 类问题，而不是 650 类问题。

### `first_bad_stage`

`first_bad_stage` 表示第一个不是 `PASS` 的阶段。

当前三校都是 `T2`，意思是：

```text
问题第一次出现在单元切分/单元判断阶段。
```

这不代表 T2 是唯一问题。T3/T4/T5 也有问题，只是排查顺序应该先从 T2 开始。

### `gold` / `expected`

`gold` 是人工审核确认过的标准答案，`expected` 是从 gold 切片出来给单阶段 verifier 用的预期结果。

当前还缺：

- `document_facts.gold.json`
- `template_spec.gold.yaml`
- `unit_map.expected.yaml`
- `element_spec.expected.yaml`
- `global_spec.expected.yaml`

所以现在很多判断只能靠 schema、flags 和 confidence gate，不能做精确比对。

## 分层视角

现在这条链路可以按四层事实/语义/规格/门禁，加一层构建来看：

```text
L0 输入层       source_template.docx
L1 事实层       document_facts.json                         T1
L2 语义解析层   unit_map.yaml + element_spec.yaml + global_spec.yaml   T2/T3/T4
L3 主规格层     template_spec.yaml                           T5
L4 门禁报告层   verification_report.json / issue_clusters.json
L5 构建层       fillable_template.docx + build_manifest.json T6
```

数据从 L0 往 L5 流，门禁从 L4 回看每一层。L1 只回答“Word 里有什么”；L2 回答“这些事实代表什么单元、什么元素、什么页面规则”；L3 把语义合成唯一主规格；L5 按主规格改 Word；L4 判断能不能宣称成功。

这里要区分两种“判定”：

| 判定类型 | 谁做 | 产出 |
| --- | --- | --- |
| 生成判定 | 各阶段 `build_*` / 推断代码 | artifact 里的字段、`confidence`、`policy`、`flags` |
| 门禁判定 | deterministic verifier | `finding`、阶段 `PASS/FAIL/UNKNOWN`、整体 gate |

因此，一个 unit 被生成器写成 `cover`，只是“生成判定”；只有 verifier 能基于 flags、gold、硬规则判断它是否可自动放行。

## T2 candidate 与默认 medium

`structure_candidates.py` 是当前 L2 的核心推断引擎，不只服务 T2：

```text
document_facts
  -> structure_candidates   # unit 边界 + element 策略的候选推断
  -> unit_map.yaml          # T2 正式 artifact
  -> generation_model
  -> element_spec.yaml      # T3 正式 artifact
```

所以“candidate”更准确地说是 T2/T3 共用的中间推断结果；`unit_map.yaml` 和 `element_spec.yaml` 才是进入 verifier 的正式产物。

当前 `default medium` 的核心问题是置信度没有校准：

- T2 `_unit_confidence()`：只要有 `source_refs` 就返回 `medium`，否则 `low`，没有 `high` 路径。
- T3 `_element_from_entries()`：新建 element 时直接写 `confidence: medium`。
- artifact flag 规则：只有空值或 `high` 不贴 flag；`medium` / `low` 都会进入 `UNKNOWN`。

这导致“识别结果可能还可以，但系统仍不能自动宣称它正确”。例如湖南农大的 9 个 unit 和 315 个 element 不等于 324 个内容都错了，而是这些判断缺少可放行的 `high` 证据或人工审核记录。

## T4 页码与 unit 的关系

你的质疑是对的：产品语义上，页码体例通常和单元相关。封面可能无页码，摘要/目录可能用罗马数字，正文通常用阿拉伯数字并从 1 开始。

但 Word 的物理事实不是按“封面/摘要/正文”存的，而是按 section（`sectPr`）存的。因此正确模型应该是两套坐标在 T5 汇合：

| 坐标 | 含义 | 负责阶段 | 关键字段 |
| --- | --- | --- | --- |
| unit | 封面、摘要、正文等语义单元 | T2 | `unit_id`、`source_range`、`page_start` |
| section | OOXML 物理分节、页眉页脚、`pgNumType` | T1/T4 | `global_spec.section_profiles[]` |
| 联结 | 某个 unit 使用哪套 section 规则 | T2/T5 | `units[].section_profile` -> `global.section_profiles[id]` |

所以更准确的说法是：T4 不负责识别“这是封面还是摘要”，但 T4 也不能单独解决页码体例；必须由 T2 把 unit 范围映射到 T4 的 section profile，T5 合并后才能得到“cover 无页码、abstract upperRoman、body decimal”这类可执行规格。

当前实现的缺口已经核实：

- `build_global_spec()` 会从 `document_facts.data.sections` 生成 `section_profiles[]`，并用 `_page_numbering_from_facts()` 全局扫描 PAGE 字段。
- `_section_profile_for_unit()` 现在是占位逻辑：只要有 sections，就返回 `section_001`。
- 本次输出里南农 `04_global_spec.yaml` 有 11 个 `section_profile`，北大有 17 个，但三校 `02_unit_map.yaml` 的 9 个 unit 全部都是 `section_profile: section_001`。
- 三校顶层 `global_spec.page_numbering.status` 仍是 `UNKNOWN`，因为当前全局页码判定主要看 `fields` 里的 PAGE 字段引用。

结论：当前不是“T4 已经能按单元判定页码”，而是“section 事实已有一部分，unit 到 section/page numbering 的联结还没做实”。这会让页码问题滞后到 template-gap 或人工打开 Word 时才暴露。

## 先看结论

当前不是 Word 构建失败。三校都是：


| 学校    | 总状态     | first_bad_stage | T1   | T2      | T3      | T4      | T5      | T6   |
| ----- | ------- | --------------- | ---- | ------- | ------- | ------- | ------- | ---- |
| 湖南农大  | UNKNOWN | T2              | PASS | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | PASS |
| 南农本科  | UNKNOWN | T2              | PASS | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | PASS |
| 北大研究生 | UNKNOWN | T2              | PASS | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | PASS |


也就是说：

- T1 源 Word facts 当前 verifier 过了。
- T6 可填 Word 构建当前 verifier 过了。
- 阻断来自 T2/T3/T4/T5 的未审核不确定性。
- 当前 finding 数量不能直接理解为“模板有这么多个独立问题”，因为 T5 会把 T2/T3/T4 的 flags 重新投影一次。

## 数量为什么被放大

以湖南农大为例：


| 来源  | 数量  | 含义                                       |
| --- | --- | ---------------------------------------- |
| T2  | 9   | 9 个 unit 是 `confidence=medium`，需要审核      |
| T3  | 315 | 315 个 element 是 `confidence=medium`，需要审核 |
| T4  | 1   | `page_numbering.status=UNKNOWN`          |
| T5  | 325 | T2/T3/T4 的 325 个 review flags 被逐条重报      |
| 合计  | 650 | 325 个真实不确定项 + 325 个 T5 重复投影              |


三校当前 finding 分布：


| 学校    | T2 unit confidence | T3 element confidence | T4 page numbering | T5 重报 | 总 findings |
| ----- | ------------------ | --------------------- | ----------------- | ----- | ---------- |
| 湖南农大  | 9                  | 315                   | 1                 | 325   | 650        |
| 南农本科  | 9                  | 101                   | 1                 | 111   | 222        |
| 北大研究生 | 9                  | 346                   | 1                 | 356   | 712        |


当前真正要讨论的是这些机制问题：

1. 哪些 `confidence=medium` 应该自动升为 `high`。
2. 哪些 `confidence=medium` 应进入人工审核。
3. T5 是否应该逐条重报 T2/T3/T4 的 flags。
4. 页码 UNKNOWN 是 T1 facts 没读到，还是 T4 规则没有解释。

## T1 document_facts

主产物：`01_document_facts.json`

当前状态：

- 三校 T1 都是 `PASS`。
- 当前报告没有 `unknown_objects` findings。

当前问题：


| 问题                               | 证据                                                                          | 影响                                          | 建议讨论                                     |
| -------------------------------- | --------------------------------------------------------------------------- | ------------------------------------------- | ---------------------------------------- |
| 还没有三校 `document_facts.gold.json` | 计划要求三校独立 gold，但仓库里还没有对应 gold 文件                                             | T1 只能证明当前 schema 和基本追踪过了，不能证明源 Word 被完整解析   | 先选一校人工审核 T1 facts，建立第一份 gold             |
| 页码字段未被 facts 证明                  | 三校 `04_global_spec.yaml` 都是 `page_numbering.field_refs=[]`、`status=UNKNOWN` | 可能是源 Word 没有 PAGE 字段，也可能是 T1 没解析页眉页脚/字段里的页码 | 对源模板人工看一次页码位置，再决定修 T1 inspector 还是 T4 规则 |
| unknown_objects 为空不等于所有复杂对象都已验证  | 当前没有 gold/视觉核对证明文本框、drawing、页眉页脚字段都完整                                       | 可能漏掉可见对象但仍 T1 PASS                          | gold 建立前不要把 T1 PASS 解释成完整解析无风险           |


## T2 unit_map

主产物：`02_unit_map.yaml`

当前状态：

- 三校 T2 都是 `UNKNOWN`。
- 每校都有 9 个 `t2_unit_confidence_needs_review`。

当前问题：


| 问题                           | 证据                                                         | 影响                           | 建议讨论                                                                |
| ---------------------------- | ---------------------------------------------------------- | ---------------------------- | ------------------------------------------------------------------- |
| unit 置信度没有 `high` 路径         | `_unit_confidence()` 当前有 source refs 就返回 `medium`，否则 `low` | 所有识别到的 unit 都会被挡成 UNKNOWN    | 定义 high confidence 条件，例如标题词命中、source range 连续、顺序合法、required unit 齐全 |
| `section_profile` 映射是占位       | `_section_profile_for_unit()` 有 sections 时一律返回 `section_001`；三校每校 9 个 unit 都指向 `section_001` | 无法按 cover/abstract/body 判定页码体例和分节规则 | 用 unit 的 `source_seq_range` 映射到 `document_facts.sections[]`，允许一个 unit 关联一个或多个 section profile |
| 单元边界质量没有 IoU verifier        | 没有 `unit_map.expected.yaml` 和边界 IoU 比对                     | 现在只能知道“识别到了 unit”，不能知道边界是否正确 | 从 `template_spec.gold.yaml` 派生 expected 后再做 IoU                     |
| 固定 9 个 unit 可能粒度过粗           | 湖南农大后置表单可能需要更细 unit，例如开题、答辩、成绩等                            | 后续 T3/T6 会在粗边界内做策略，导致责任混在一起  | 先讨论湖南农大是否应拆后置表单 unit                                                |
| `open_questions` 只从 flags 派生 | 当前主要是 confidence flags，没有更具体的问题文本                          | 人工审核不知道该判断边界、责任还是顺序          | 给 T2 flags 加结构化原因：anchor 弱、边界弱、缺 expected、顺序疑似异常                    |


## T3 element_spec

主产物：`03_element_spec.yaml`

当前状态：

- 三校 T3 都是 `UNKNOWN`。
- 湖南农大 315 个 element confidence findings，南农 101 个，北大 346 个。

当前问题：


| 问题                         | 证据                                                             | 影响                                                   | 建议讨论                                                             |
| -------------------------- | -------------------------------------------------------------- | ---------------------------------------------------- | ---------------------------------------------------------------- |
| element 置信度基本硬编码为 `medium` | `_element_from_entries()` 当前写 `confidence: medium`             | 每个元素都会进入 UNKNOWN，报告噪声很大                              | 定义按规则来源分级的 confidence：明确占位符/下划线/格式说明可 high，正文歧义保留 medium         |
| 低/中置信只有阻断，没有审核闭环           | `review_flags` 有了，但没有 `review_queue.yaml` 和 `review_decisions` | 状态会一直 UNKNOWN，无法通过人工决策清除                             | 先实现 review queue artifact，记录 reviewer、decision、reason、input hash |
| AI trace 还没有               | `element_spec.ai_traces` 为空                                    | 计划里的 AI 残余分类、模型版本、temperature、schema validation 都没落地 | 先决定哪些 element 类型允许 AI 分类，哪些必须确定性规则处理                             |
| 误删真内容的门禁还不够具体              | 当前 instruction_remove 有基础规则，但没有 gold 验证                        | “格式说明”删除和“真实正文括号内容”保留的边界还没充分证明                       | 增加 T3 聚焦测试和 gold expected                                        |


## T4 global_spec

主产物：`04_global_spec.yaml`

当前状态：

- 三校 T4 都是 `UNKNOWN`。
- 每校都有 1 个 `t4_page_numbering_unknown`。

当前问题：


| 问题                | 证据                                                             | 影响                                   | 建议讨论                                                 |
| ----------------- | -------------------------------------------------------------- | ------------------------------------ | ---------------------------------------------------- |
| 页码体例 UNKNOWN      | 三校 `page_numbering.field_refs=[]`、`status=UNKNOWN`             | 页码规则不能证明，后续 template-gap 的页码问题无法提前定位 | 人工确认源模板页码是否存在；若存在，优先修 T1/T4 页码解析                     |
| section 事实未形成单元语义 | 南农有 11 个 section profile、北大有 17 个，但 T2 unit 仍全指向 `section_001` | 即使 T4 读到了多个物理分节，也不能回答“摘要/正文分别用什么页码” | 在 T5 verifier 校验每个 unit 的 `section_profile` 是否存在且与 source range 相交 |
| 分节/分页 action 仍弱   | 当前 T6 `page_breaks/section_breaks` 主要看已有执行证据，三校最终 gap 仍可能有页面问题 | 页面规则可能到最终 gap 才暴露                    | T4 需要把 page_start/section profile 变成可执行规则或明确 UNKNOWN |
| global flags 粒度较粗 | 目前页码 UNKNOWN 是单个 global flag                                   | 不知道是没字段、字段在页脚没读、还是字段类型没解释            | flag 里应带 source search evidence 和检查范围                |


## T5 template_spec

主产物：`05_template_spec.yaml`

当前状态：

- 三校 T5 都是 `UNKNOWN`。
- T5 当前把 T2/T3/T4 的 flags 合并到 `review_flags`，verifier 又逐条生成 findings。

当前问题：


| 问题                           | 证据                                          | 影响                                                                 | 建议讨论                                                      |
| ---------------------------- | ------------------------------------------- | ------------------------------------------------------------------ | --------------------------------------------------------- |
| T5 findings 重复放大             | 湖南农大 T2/T3/T4 是 325 个真实不确定项，T5 又报 325 个     | `summary.unknown_findings`、`blocking_findings`、issue cluster 数量被放大 | T5 改成一个聚合 finding，或按 `flag_id + origin_stage` 去重          |
| review_flags 没有 origin_stage | T5 重报后 type 变成 `t5_*`，原始阶段只能从 type/reason 猜 | 报告读者容易以为 T5 自己产生了新问题                                               | flag 增加 `origin_stage`、`origin_artifact`、`source_flag_id` |
| review_decisions 为空          | `template_spec.review_decisions=[]`         | 无法证明哪些不确定项已人工确认                                                    | 和 `review_queue.yaml` 一起设计                                |
| 缺主 gold 精确比对                 | 没有 `template_spec.gold.yaml`                | T5 只能做 schema/id/flags 门禁，不能证明 spec 内容正确                           | 建立一校主 gold，再切片出 T2/T3/T4 expected                         |


## T6 fillable_template/build_manifest

主产物：

- `06.0_copy_source_docx.docx`
- `06.1_fillable_template.docx`
- `06.2_build_manifest.json`

当前状态：

- 三校 T6 都是 `PASS`。
- 这说明当前生成出的可填 Word 是有效 DOCX，SDT tag 和 manifest hash 过了。

当前问题：


| 问题                      | 证据                                          | 影响                                  | 建议讨论                     |
| ----------------------- | ------------------------------------------- | ----------------------------------- | ------------------------ |
| T6 PASS 不代表模板解析成功       | overall 是 UNKNOWN，first_bad_stage 是 T2      | Word 能构建出来，但不能宣称模板解析正确              | 报告里继续明确 T6 PASS 只是构建层通过  |
| generated fields 仍是占位能力 | 计划要求 TOC/PAGE/SEQ 优先低层 OOXML 字段             | 目录、页码、编号最终质量仍可能不达标                  | 先补 PAGE/TOC 的低层 OOXML 构建 |
| 缺成品再跑 T1 的复核链           | 计划要求对成品再跑 T1，编辑区 facts 能复现 template_spec 决定 | 目前 T6 主要看 manifest、SDT、hash         | 增加成品 facts verifier      |
| 缺视觉/分页快照门禁              | 没有字段更新后截图、页数、页边界比较                          | 分页错可能只在 template-gap 或人工打开 Word 时发现 | 后续接渲染快照或 Word 更新字段流程     |


## Report 层问题

这些不是某个模板阶段的业务判断，而是报告表达问题。


| 问题                                        | 当前表现                                   | 影响                    | 建议                                                   |
| ----------------------------------------- | -------------------------------------- | --------------------- | ---------------------------------------------------- |
| T5 重复投影导致计数翻倍                             | T2/T3/T4 的 flags 在 T5 又逐条报             | 数量看起来比真实问题多一倍         | T5 聚合或去重                                             |
| findings 的 `stage` 仍是 `template_generate` | issue cluster 里 stage 不是 T2/T3/T4      | 读报告时不能直接按阶段筛选         | finding 增加 `verification_stage`，或把 stage 写成 T2/T3/T4 |
| issue cluster 标题太泛                        | 标题是 `T2 has unresolved flag`           | 看 cluster 不知道具体要审核什么  | cluster title 用 flag type 和样例 affected_ids           |
| blocking_findings 与 UNKNOWN 混在一起          | UNKNOWN finding 默认 severity 是 blocking | 技术上符合阻断，但 PM 读起来像失败缺陷 | 可以增加 `gate_blocking=true` 和 `known_failure=false` 区分 |


## 文档口径问题


| 文件                                               | 问题                                                     | 建议                                             |
| ------------------------------------------------ | ------------------------------------------------------ | ---------------------------------------------- |
| `docs/current/template-generation-open-gaps.md`  | 仍有一句“当前模板生成能生成 `generated_template.docx` 和 00-05 阶段证据” | 改成历史口径，或更新为 `fillable_template.docx` 和 `00-07` |
| `docs/current/template-generation-evaluation.md` | 仍大量使用旧 `generated_template.docx` / 00-05 评测口径          | 后续统一迁移到新 artifact 链，或明确标注历史文档                  |
| `docs/human/*template-generation*`               | 多数是历史审计和旧主线                                            | 保留可以，但需要索引说明“旧文档，不作为当前门禁”                      |


## 建议讨论顺序

1. 先修报告计数：T5 不再逐条重复报 T2/T3/T4 flags。
2. 定义 T2/T3 的 high/medium/low 规则，让“正常确定项”不再全部 UNKNOWN。
3. 决定 review queue schema，让 medium 项能被人工确认或驳回。
4. 修 T2/T4 的 unit -> section_profile 联结，让页码/分节能按单元解释。
5. 针对 T4 页码 UNKNOWN 查源 Word，判断是 T1 漏解析、T4 漏解释，还是源模板确实没有 PAGE 字段。
6. 建湖南农大 gold，先让一校从“全靠 confidence gate”进入“gold 精确比对”。

## 当前可讨论的关键问题

这些问题需要产品和工程一起定：

1. 有 source refs、标题词命中、source range 连续的 unit，是否可以直接 `confidence=high`？
2. 明确格式说明、颜色说明、下划线占位符等元素，是否可以直接 `confidence=high`？
3. copy-only 单元内部拆出的 fill candidate，是应该默认保守 medium，还是只作为辅助证据不进入阻断？
4. T5 的 `review_flags` 是“主审核入口”，还是只做汇总索引？
5. 页码如果源模板没有真实 PAGE 字段，是 T4 UNKNOWN，还是 T6 应生成 PAGE 字段占位？
6. unit 到 section 的映射应该由 T2 直接写死，还是由 T5 根据 T2 source range 与 T4 section range 合并推导？
