# 模板差距检测引擎优化计划（阅读版）

Status: Planned
Created: 2026-06-17
Based on: [template-gap-engine-layering-refactor.md](./template-gap-engine-layering-refactor.md)

本文档在 Codex 可执行计划基础上重写：**前半部分给非研发读者**，说明背景、目标和你会看到的变化；**后半部分给研发读者**，保留逐步执行的改动与验证命令。

---

## 2026-06-17 复盘修订：先用现有上下文框定区域，不做搜索小补丁

这一节是对原计划的修订。原计划里的 C3/C4 把重点放在“搜索去噪”“限定单元范围”上，
这个方向只能解决一部分误报；如果继续在搜索规则上加细节，会把检查器变成一堆脆弱的
例外判断。当前更根本的问题是：系统已经有很多结构化输入，但 gap 检查器没有先把这些
上下文合成稳定的“文档区域地图”，而是过早把 Word 内容压平成可见文本列表再全文搜索。

### 当前已经有哪些输入和上下文

| 来源 | 已有内容 | 应该怎么用 |
|------|----------|------------|
| `template_unit_contract.yaml` | `expected.units`、单元顺序、`status`、`policy`、`page`、`header_footer`、`element_order`、`layout_relation`、每个元素的 `policy/content/style/source_refs`、全量审查文本 hash | 这是“应该有哪些单元和检查项”的标准，不是搜索词仓库 |
| `generated_template.docx` | 被测业务生成模板；当前三校为模拟业务生成模板 | 这是唯一被测 Word |
| `generated_template_tree.json` | 从 Word/OOXML 解析出的段落、表格、页眉页脚、域、分节、编号、未知可见对象 | 这是“实际生成内容”的结构化证据，应先建立文档坐标和区域 |
| `template_artifact.json`（e2e 中已有） | 解析原始模板得到的 `units / regions / protected_zones / required_fields / slots` | 在 e2e 模式下可作为额外上下文，验证生成结果是否保留了预期区域和槽位 |
| `placement_plan.json`（e2e 中已有） | 学生内容被计划投放到哪个 `target_region_id / target_slot_id` | 用来解释生成结果应该在哪些区域出现学生内容，避免 gap checker 重复猜 |
| `student_content_artifact.json`（e2e 中已有） | 学生源文档的可见内容账本、reading order、语义候选 | 用来验证内容是否进入正确区域，但不能替代模板结构检查 |
| `render_manifest.json / feature_snapshot.json`（e2e 中已有） | 渲染动作和最终 Word 的特征快照 | 用来交叉检查“生成阶段是否真的执行了计划” |

### 当前误报和 UNKNOWN 高的具体原因

1. **文档坐标不统一。**
   `generated_template_inspector.py` 里普通段落来自 `python-docx` 顶层段落序号，
   表格单元格范围来自 OOXML 全文段落序号。两套序号混进同一个 `order` 后，
   “上一单元到下一单元之间”这个范围本身就不稳定。

2. **页眉页脚被混进正文搜索。**
   `iter_visible_text_entries()` 把正文段落、表格单元格、页眉页脚放进同一个列表。
   北大报告里 `figure_list`、`acknowledgement` 曾定位到 `word/header*.xml`，
   说明搜索空间已经污染。

3. **单元定位是弱搜索结果，不是上游事实。**
   `_locate_units()` 取每个单元前 3 个 fixed/manual 元素作为锚点，按标准顺序从全文找第一个命中。
   一旦前面某个单元命中了后文，后续单元都会被游标挤到错误区域。
   北大 `cover` 被定位到正文后段 `p[168]`，就是这个问题。

4. **表格和固定表单没有作为区域处理。**
   湖南农业的设计任务书、开题报告、评审记录等本质是表格块。
   当前检查器却把表格单元格拆成普通文本去抢锚点，导致 `design_task`、`proposal`
   这类单元互相串台。

5. **全局规则混进单元元素。**
   南农 `acknowledgement` 下面有 98 个元素，其中大量是纸张、页边距、页眉、section、页码等全局规则。
   这不是搜索策略能修好的问题；这些内容应该被分流到全局页面/样式/页眉页脚检查，
   而不是当“致谢章节里的可见元素”去找。

6. **报告没有把区域定位作为一等证据。**
   当前 `template_gap_report.json` 有每个单元的 `located`，但没有独立的 `region_map`
   和候选区域解释。人工只能从元素失败倒推检查器圈了哪里，导致 `UNKNOWN` 比例高时很难判断
   是模板真缺、检查器不会查，还是标准项归属错。

### 修订后的最佳方案

主线改为：**先构建稳定的生成 Word 上下文，再做单元/元素检查。**

```text
generated_template.docx
  → OOXML 全文结构解析
  → 统一 DocumentCoordinate（正文、表格、页眉页脚、域、分节都用同一坐标系）
  → GeneratedTemplateContext（节点索引、表格块、section、field、numbering、header/footer 分区）
  → UnitRegionMap（每个标准单元对应哪些实际区域，以及证据/置信度/失败原因）
  → 在 region 内检查元素、样式、分页、页眉页脚、字段、编号
  → 报告区分：模板真差距 / 检查器证据不足 / 标准项归属问题
```

具体执行顺序建议替换原 C3/C4：

| 步骤 | 做什么 | 产出 |
|------|--------|------|
| R1 | 重建 Word 结构索引，统一所有节点的文档坐标；正文、表格、页眉页脚分通道保存 | `generated_template_context` 内部对象；树里每个节点有稳定坐标 |
| R2 | 基于标准单元顺序、标题/样式/表格块/section/field/header-footer 建 `UnitRegionMap`；不要用“第一个全文命中”作为事实 | 报告新增 `region_map`，每个单元列出候选区域、采用区域、拒绝原因 |
| R3 | 元素、样式、字段、编号、分页检查只在已确认 region 内运行；单元未定位时下级检查保持 `UNKNOWN` | UNKNOWN 更可解释，FAIL 只代表有证据的不符合 |
| R4 | 把标准项分流：单元可见内容、全局页面样式、页眉页脚/页码规则、审查备注；污染项不再当元素搜 | 南农这类全局规则不再制造致谢元素缺失 |
| R5 | e2e 模式额外读取 `template_artifact / placement_plan / student_content_artifact / render_manifest`，做交叉验证；单独 `template-gap` 仍只依赖 Word + 标准 | 独立检查和完整流水线都能解释自己用了哪些上下文 |
| R6 | 报告按“区域定位 → 元素检查 → 样式/页面维度”展示，并新增检查器问题分组 | 人能先判断区域是否圈对，再看元素是否真缺 |

### 不推荐的方案

- 不推荐继续在 `_match_query_for_element()` 里堆学校词表、括号清洗、特殊符号替换。
- 不推荐把页眉页脚简单从搜索列表里删掉就结束；页眉页脚仍要作为独立通道被检查。
- 不推荐把 `UNKNOWN` 批量降级或升级；应先知道 UNKNOWN 来自“单元没定位”“节点没建模”
  还是“标准项归属不对”。
- 不推荐让 e2e 的 `template_artifact` 替代 `generated_template_tree`；
  `template_artifact` 说明“我们理解原始模板应是什么”，`generated_template_tree`
  才说明“业务生成 Word 实际是什么”。

### 验证方式

新增一组面向区域地图的测试，而不是只测搜索命中：

- 北大：`cover` 应落在封面区域，`abstract_en` 应能落到 `ABSTRACT` 附近；
  `figure_list / acknowledgement` 不能定位到 `word/header*.xml`。
- 湖南农业：设计任务书、开题报告、评审记录等表格单元应以表格块为区域，
  不允许表格内部某个普通单元格抢占下一单元锚点。
- 南农：致谢只检查致谢标题和正文；纸张、页边距、页眉、section、页码规则进入全局维度。
- 最小 PASS 夹具仍必须 PASS；删一个固定元素只影响该元素；改一个样式只影响该元素。

建议命令：

```bash
uv run pytest tests/contract/test_real_core_generated_template_gap.py -q

uv run docfit eval template-gap --school pku-graduate \
  --generated-template test_test_inputs/template_gap/real-core-v0-pku-graduate-generated-template.docx \
  --out /tmp/docfit_gap_pku_region_map
```

---

# 第一部分：非研发阅读指南

## 1. 这份计划在解决什么问题

我们有一套**自动检查 Word 模板是否符合作业标准**的系统（`template-gap`）。它会拿**验收标准**（YAML 大纲）对照**业务生成模板** `generated_template.docx`，输出差距报告。

**现状：**

| 现象 | 说明 |
|------|------|
| 管道能跑通、能拦住不合格结果 | 测试全绿，三校评测都是 FAIL/UNKNOWN，门禁没有被绕过 |
| 报告还不能当「开发排期清单」 | 失败项平铺刷屏，很难按「封面 / 目录 / 摘要」分章看 |
| 大量「元素缺失」不可信 | 湖南农业 121 条 `element_missing` 里，至少约 **54 条**不是可靠证据 |
| 测试不能证明「检查器会对」 | 没有「全对样卷必须 PASS」的测试；检查器退化成「永远 FAIL」测试仍可能全绿 |

**本计划的目标不是「让三校模板变绿」。** 三校模板现在本来就有真差距。我们要的是：把验收逻辑改到能可靠回答——

```text
被测 Word 在不在
  → 每一章能不能定位
  → 每一章里的元素在不在
  → 样式、分页、页眉页脚、字段、编号有没有证据
  → 失败是真差距、系统查不了、还是检查器自己判错了
```

---

## 2. 被测对象边界（必读）

本计划里，gap 检查**只承认一种被测 Word**：

```text
generated_template.docx  —— 业务生成模板（当前阶段：模拟输入）
```

### 三份模拟的业务生成模板

业务侧的「模板生成」代码**尚未跑通**。在此之前，我们登记了**三份模拟的业务生成模板**，在开发和验证 `template-gap` 时**扮演** `generated_template.docx` 的角色：

| 学校 | 模拟业务生成模板 |
|------|------------------|
| 湖南农业 | `test_test_inputs/template_gap/real-core-v0-hunannongye-generated-template.docx` |
| 南农本科 | `test_test_inputs/template_gap/real-core-v0-nannong-undergraduate-generated-template.docx` |
| 北大研究生 | `test_test_inputs/template_gap/real-core-v0-pku-graduate-generated-template.docx` |

这三份文件在系统中的**唯一产品身份**是：**模拟的业务生成结果**。

文档、报告、评审和排期里，请统一使用上述称呼。**不要说**「用学校原始模板做 gap 测试」或「拿 `school-*.docx` 当生成模板测」——即便文件内容在准备阶段可能参考过学校材料，一旦登记进 `simulated-generated-templates/`，就只按「模拟业务生成模板」理解和引用，避免业务代码上线后概念漂移。

### 和验收标准、来源材料的分工

```text
template_unit_contract.yaml     验收标准（人工审查后的大纲：应该长什么样）
generated_template.docx         被测对象（业务应吐出的 Word：实际长什么样）
test_test_inputs/template_generation/school-*.docx 等         标准编制时的来源材料，不进入 gap 被测入口
```

未来模板生成器跑通后：**被测入口仍是 `generated_template.docx`，eval 链路不变**，只是文件从「模拟夹具目录」改为「生成器输出」。验收逻辑不因生产来源切换而改口径。

---

## 3. 用生活类比理解整套系统

| 系统说法 | 通俗理解 |
|----------|----------|
| 验收标准 YAML（`template_unit_contract.yaml`） | 阅卷大纲：每章该有什么、什么格式 |
| `generated_template.docx` | 学生交的作业（**业务应生成的 Word 模板**） |
| 三份模拟业务生成模板 | 生成器还没做好之前，用来测阅卷逻辑的**三份模拟作业** |
| 差距检测引擎 | 自动阅卷老师 |
| 单元（unit） | 一章，如封面、目录、中文摘要 |
| 元素（element） | 章里的具体内容，如学校名、学号标签 |
| PASS / FAIL / UNKNOWN | 合格 / 不合格 / **无法判断**（不等于学生过错） |

**阅卷方式简述：** 不是两份 Word 逐字对比。而是先把**被测作业**拆成结构化清单（段落、表格、样式、字段等），再按**大纲**逐项核对。大纲和被测作业是两种东西，不能混。

---

## 4. 三类结论分别代表什么

读报告时，请先分清这三种状态——这是本计划最重要的产品语义：

| 状态 | 含义 | 你该怎么理解 |
|------|------|--------------|
| **PASS** | 有证据，且符合标准 | 这一项可以认为过关 |
| **FAIL** | 有证据，确实不符合标准 | **真差距**，需要修模板或生成逻辑 |
| **UNKNOWN** | 检查器证据不足，无法判定 | **不能算模板过错**；可能是解析能力不足，或暂时查不了 |

**本次要修的一个核心问题：** 很多本该是 UNKNOWN（查不动）的项，被错误标成了 FAIL（缺失）。

---

## 5. 当前两大问题（为什么要改）

### 问题 A：报告像「不分章节的错题本」

- 标准和大纲是按「章 → 元素 → 样式」写的。
- 检查过程也按章走。
- **输出**却把所有结果压成一条长清单（`check_items`），只靠 `cover.e_005.style` 这类编码猜归属。

**后果：** 200 条平铺难读；更严重的是，匹配时容易**全文乱搜**，把 A 章的文字当成 B 章的。

### 问题 B：检查规则本身产生误报

湖南农业实跑数据（约 54 条不可信 missing）可拆成两类：

| 类型 | 数量（约） | 原因（通俗） |
|------|-----------|--------------|
| 无搜索词却判 FAIL | 37 | 标准里只有描述性名字（如「学生中文摘要」），系统不知道用什么词去搜，却直接判「缺失」 |
| 内容其实在但搜法太糙 | 17 | 标准里有 `□`、`×××`、括号格式说明；Word 成品没有这些符号，子串搜索失败 |

此外还有：**跨章节串台**（全文第一次搜到就算）、**样式绑错段落**等问题。

---

## 6. 改造后你会看到什么变化

### 6.1 被测对象口径统一为「业务生成模板」

被测对象**始终是** `generated_template.docx`，语义固定为**业务生成模板**。

当前阶段：三校各有一份**模拟的业务生成模板**，路径在 `test_test_inputs/template_gap/real-core-v0-<school_id>-generated-template.docx`。

C0 要修的历史问题：real-core 链路曾错误地把 `bundle.template_docx`（标准来源侧的 `school-*.docx`）送进 gap 检查。改完后：

- 报告里的 `generated_template.path` 必须指向 `simulated-generated-templates/.../generated_template.docx`（或开发者 CLI 显式传入的任意 `generated_template.docx`）
- **不得**再出现「gap 在测学校原始模板 / 要求文档」这种口径

验收标准 YAML 仍是「大纲」，不是被测 Word；`school-*.docx` 是编标准时的来源材料，不是 gap 被测入口。

### 6.2 报告按章节组织

改前：一张 200+ 条的长清单。

改后：树状结构，例如——

```text
报告
├── 输入检查（Word 有没有、能不能读）
├── 各章节（封面、目录、摘要……）
│   ├── 本章定位了吗？在第几段？
│   ├── 本章总评 + 通过/失败/查不了统计
│   ├── 各元素：在不在、样式对不对
│   └── 本章其他：分页、页眉页脚、字段、编号
├── 标准没定义但文档里出现的内容
└── 总摘要（含每章一行小结）
```

### 6.3 误报型「元素缺失」明显减少

| 改什么 | 效果 |
|--------|------|
| 搜索前去掉 `□`、`×××`、格式批注等噪音 | `学□□号` 能对上 `学号` |
| 复合字段拆开搜（姓名、学号、班级…） | 不必整段一字不差 |
| 搜不了的 fixed 元素 → UNKNOWN | 「查不动」不再算「不合格」 |
| 先划定每章范围，再在本章内搜 | 减少张冠李戴 |

### 6.4 测试能证明「检查器会对也会拦」

新增「全对样卷必须 PASS」「只改一处样式只 FAIL 那一处」等测试，避免改坏了却不知道。

---

## 7. 五步走总览（执行顺序）

研发按 C0 → C5 实施。非研发只需知道每步解决什么：

| 步骤 | 做什么 | 解决什么痛点 |
|------|--------|--------------|
| **C0** | 被测对象固定为 `generated_template.docx`；三校走模拟业务生成模板路径 | 不再把 `school-*.docx` 误当「生成模板」去测 |
| **C1** | 建立最小全对样卷，必须能 PASS | 证明检查器「会对」，而不只是「会拦」 |
| **C2** | 报告改成分层树，按章输出 | 人能读、能按章排期 |
| **C3** | 搜索去噪 + 查不了改 UNKNOWN | 减少误报型 missing（湖南农大约 54 条的主因） |
| **C4** | 章节范围内匹配 + 样式绑对本章 | 减少串台、样式张冠李戴 |
| **C5** | coverage / e2e 全量回归 | 整条流水线不被改坏 |

**关键顺序：** C1 必须先于大重构。没有「能 PASS」的底线测试，后续改动无法证明改对改错。

---

## 8. 本计划明确不做什么

- 不实现真正的模板生成器（只优化验收逻辑）。
- 不把模拟业务生成模板签成 golden，不自动改 signed standard。
- 不把 gap 检查包装成「学校原始模板检查」；被测对象始终是业务生成模板这一产品概念。
- 不为了减少 FAIL 而把明确违反标准的项降成 UNKNOWN。
- 不修内容抽取、内容放置、最终 Word 渲染。

---

## 9. 完成标准（怎么判断计划做完了）

同时满足以下各项：

- [ ] 三校 gap 检查的被测输入均为 `test_test_inputs/template_gap/real-core-v0-<school_id>-generated-template.docx`（模拟业务生成模板），而非 `school-*.docx`
- [ ] 报告以分层树为主结构，不再公开平铺 `check_items`
- [ ] 最小全对样卷能让整条链路得到 `blocking_status == PASS`
- [ ] 「改一处样式 / 删必填 / 搜不了 / 两章同名」四类场景都能定点证明结果
- [ ] 湖南农业和南农的误报型 `element_missing` 明显减少；真差距仍 FAIL
- [ ] coverage / e2e 仍按 `summary.blocking_status` 正确阻断

---

## 10. 验收逻辑是怎么工作的（补充说明）

非研发常问：「是不是把标准内容放到 Word 里搜索？」——**部分是的，但不全是。**

| 检查类型 | 做法（通俗） |
|----------|--------------|
| 元素在不在 | 从标准抽关键词，在 Word 可见文字里搜（类似 Ctrl+F） |
| 样式对不对 | 读命中段落的格式属性，与标准 `style` 比对 |
| 目录/页码等字段 | 查 Word 里有没有 TOC、PAGE 等域代码 |
| 页眉页脚 / 分页 | 在本章对应位置做规则判断 |
| 章节顺序 | 根据各章定位位置比较先后 |

本次改造让「元素在不在」这一步更聪明（去噪、拆字段、限定本章范围），并严格区分 FAIL 与 UNKNOWN。

---

# 第二部分：研发执行指南

> 以下保留可执行细节。实施时请严格按 **C0 → C5** 顺序推进。  
> **口径提醒：** 文中凡出现 `generated_template.docx`，均指业务生成模板；当前三校使用 `simulated-generated-templates/` 下的模拟文件，**不是** `school-*.docx`。

## 11. Scope 与实跑证据

**Scope：** 只优化生成模板验收逻辑，不实现真正的模板生成器，不更新 signed standard、golden 或 expected snapshot。

**实跑证据：**

- `uv run pytest tests/unit tests/contract tests/e2e -q` 能通过
- 三校 `docfit eval template-gap` 都是 `FAIL + UNKNOWN`
- 湖南农业 121 条 `template_generation_element_missing` 里，至少约 54 条不可靠：37 条无 needle 自动 FAIL，17 条 token 实际存在但匹配器看不懂
- contract 测试没有干净 PASS 夹具，也没有隔离变异测试

---

## 12. C0：统一被测对象为业务生成模板

不要再引入「官方模板检查」或「学校原始模板检查」概念。所有代码、报告、测试只面对：

```text
generated_template.docx   # 产品语义：业务生成模板
```

**当前阶段：** 业务生成器未跑通，三校使用登记在 `simulated-generated-templates/` 下的**模拟业务生成模板**充当该输入。它们是被测对象，不是标准来源，也不是 `school-*.docx` 的别名。

**C0 要消除的技术债：** `orchestrator` 曾把 `bundle.template_docx`（`test_test_inputs/template_generation/school-*.docx`，标准编制侧材料）传入 `evaluate_generated_template_gap()`。这会在报告路径和概念上把「标准来源」和「被测生成物」混在一起。改后 gap **只**读 `generated_template_docx` 配置项。

### 12.1 三份模拟业务生成模板（夹具目录）

```text
test_test_inputs/template_gap/
├── hunannongye/generated_template.docx
├── nannong-undergraduate/generated_template.docx
└── pku-graduate/generated_template.docx
```

### 12.2 文件改动

| 文件 | 改动 |
|------|------|
| `test_test_inputs/README.md` | 新增「模拟业务生成模板输入」一节：说明三份文件是 gap 被测对象，不是学校原始模板 |
| `standards/eval_profiles/real-core-v0/cases.yaml` | 每校增加 `generated_template_docx` |
| `src/docfit/harness/profiles.py` | `EvalCase` 增加 `generated_template_docx`；`REAL_CORE_SCHOOLS` 同步 |
| `src/docfit/convert/orchestrator.py` | real-core gap 检查改用 `generated_template_docx` |

`orchestrator.py` 核心替换：

```python
# 改前
evaluate_generated_template_gap(bundle, bundle.template_docx, out_dir)

# 改后
evaluate_generated_template_gap(bundle, generated_template_docx, out_dir)
```

- `run_template_eval()`：gap 用 `generated_template_docx`；`template_docx` 仅用于模板解析等其他阶段，**不**进入 gap 被测入口
- `run_template_gap_eval()`：保持 `--generated-template` 显式输入不变

完成后，`template_gap_report` 里的 `generated_template.path` / `source_path` 必须指向模拟业务生成模板路径（或 CLI 显式传入的 `generated_template.docx`），**不得**再指向 `test_test_inputs/template_generation/school-*.docx`。

### 12.3 验证

```bash
uv run pytest tests/contract/test_real_core_generated_template_gap.py::test_real_core_template_gap_outputs_tree_and_reports_for_all_schools -q

uv run docfit eval template-gap --school hunannongye \
  --generated-template test_test_inputs/template_gap/real-core-v0-hunannongye-generated-template.docx \
  --out /tmp/docfit_gap_hna
```

---

## 13. C1：建立最小 PASS 夹具

**必须先做。** 否则后续重构只能证明「会失败」，不能证明「正确时会通过」。

### 13.1 新增测试 helper（`tests/contract/test_real_core_generated_template_gap.py`）

```python
def unit_by_id(report, unit_id): ...
def element_by_id(unit, element_id): ...
def collect_checks(report, *, type=None, category=None, status=None): ...
def write_minimal_gap_standard(root, school_id, expected_units): ...
def write_docx(path, paragraphs): ...
```

### 13.2 新增测试 `test_template_gap_minimal_fixture_can_pass_cleanly`

- 在 `tmp_path` 创建最小 school standard + 完全匹配的 `generated_template.docx`
- 跑 `run_template_gap_eval(tmp_root, school_id, generated_template, out_dir)`
- 断言：

```python
result.status == Status.PASS
report["summary"]["blocking_status"] == "PASS"
report["summary"]["failed_count"] == 0
report["summary"]["unknown_count"] == 0
unit_by_id(report, "cover")["verdict"] == "PASS"
```

### 13.3 验证

```bash
uv run pytest tests/contract/test_real_core_generated_template_gap.py::test_template_gap_minimal_fixture_can_pass_cleanly -q
```

---

## 14. C2：分层结果树替代平铺 `check_items`

不保留旧 `check_items` 兼容层。

### 14.1 新报告结构（`template_gap_report.json` v2.0）

```python
{
    "artifact_type": "template_gap_report",
    "artifact_version": "2.0",
    "school_id": "...",
    "generated_template": {
        "path": ".../generated_template.docx",
        "source_path": "...",
        "sha256": "...",
        "input_role": "generated_template"
    },
    "input": CheckResult,
    "units": [
        {
            "unit_id": "cover",
            "name": "封面",
            "order": 10,
            "status": "required",
            "located": {
                "found": True,
                "source_ref": "word/document.xml:p[1]",
                "order_range": [1, 23]
            },
            "presence": CheckResult,
            "elements": [
                {
                    "element_id": "e_001",
                    "name": "学校名称",
                    "policy": "fixed",
                    "order": 1,
                    "presence": CheckResult,
                    "style": CheckResult,
                    "verdict": "PASS"
                }
            ],
            "dimensions": {
                "page": [CheckResult],
                "header_footer": [CheckResult],
                "fields": [CheckResult],
                "numbering": [CheckResult]
            },
            "counts": {"passed": 0, "failed": 0, "unknown": 0},
            "verdict": "FAIL"
        }
    ],
    "unmodeled_objects": [CheckResult],
    "summary": {
        "known_status": "FAIL",
        "display_status": "FAIL + UNKNOWN",
        "blocking_status": "FAIL",
        "passed_count": 0,
        "failed_count": 0,
        "unknown_count": 0,
        "per_unit": [
            {"unit_id": "cover", "verdict": "FAIL", "counts": {...}}
        ]
    },
    "coverage": {...}
}
```

### 14.2 `CheckResult` 字段

```python
{
    "check_id": "template_generation.element_match",
    "status": "PASS|FAIL|UNKNOWN",
    "type": "template_generation_element_found",
    "message": "...",
    "expected": "...",
    "actual": "...",
    "category": "element|style|page_rule|...",
    "path": ["units", "cover", "elements", "e_001", "presence"],
    "evidence_refs": ["word/document.xml:p[1]"],
    "next_step": "..."
}
```

`path` 替代 `affected_ids` 作为报告内部定位。生成 `Finding` 时从 `path` 派生 `affected_ids`，如 `["cover.e_001.presence"]`。

### 14.3 `generated_template_gap.py` 改动

1. `_check()` 包一层 `_check_result(path=...)`，强制写入 `path`
2. `build_template_gap_report()` 输出 `input`、`units`、`unmodeled_objects`、`summary`；不再创建 `check_items`
3. `summarize_check_items()` → `summarize_template_gap_report()`（或前者仅测试兼容）
4. `findings_from_template_gap_report()` 递归遍历树
5. `render_template_gap_markdown()` / `write_template_gap_docx()` 按单元分组
6. `template_generation_coverage()` → `template_generation_coverage_from_report()`

### 14.4 旧测试改写

- `report["check_items"]` → `collect_checks(report, ...)` 或具体 unit/element 路径
- `test_template_gap_status_combination_rules` → 测 `summarize_template_gap_report()`

### 14.5 验证

```bash
uv run pytest tests/contract/test_real_core_generated_template_gap.py -q
```

---

## 15. C3：匹配去噪和 UNKNOWN 分类

### 15.1 新增函数

```python
def _normalize_for_match(value: Any) -> str: ...
def _strip_format_annotations(text: str) -> str: ...
def _split_match_tokens(text: str) -> list[str]: ...
```

**规则：**

- `_normalize_text()` 继续用于报告展示
- `_normalize_for_match()` 仅用于匹配：删 `□`、`×`/`×××`、点引线、格式批注括号（含黑体/宋体/pt/居中等词）；保留语义括号如 `毕业论文(设计)`
- `_candidate_needles()` 返回 query dict：

```python
{
    "full": ["目 录"],
    "tokens": ["学生姓名", "学号", "年级专业及班级"],
    "min_tokens": 2
}
```

- `_find_best_match()`：full 命中任一即 PASS；tokens 命中 `>= min_tokens` 即 PASS
- 无有效 query 的 fixed/manual_only → `UNKNOWN template_generation_element_uncheckable`

### 15.2 必须覆盖的回归例子

- `目 录` → `目□□录   (二号黑体，居中)`
- `摘 要：` → `□□摘要……………………………………………………………………………1`（不误判正文摘要内容已存在）
- `学生姓名：；学号：；年级专业及班级：` → 分散字段标签
- 无 needle 的 fixed/manual_only → UNKNOWN 而非 FAIL

### 15.3 新增测试

- `test_template_gap_unsearchable_fixed_element_is_unknown_not_fail`
- `test_template_gap_normalizes_template_noise`

### 15.4 验证

```bash
uv run pytest tests/contract/test_real_core_generated_template_gap.py \
  -k "normalizes_template_noise or unsearchable_fixed_element" -q

uv run docfit eval template-gap --school hunannongye \
  --generated-template test_test_inputs/template_gap/real-core-v0-hunannongye-generated-template.docx \
  --out /tmp/docfit_gap_hna_after_match
```

检查 `template_generation_element_missing` 明显下降；无 needle 项转 UNKNOWN。

---

## 16. C4：单元范围内匹配和样式绑定

### 16.1 新增 helper

```python
def _visible_entries_by_order(tree) -> list[dict[str, Any]]: ...
def _match_query_for_element(element) -> MatchQuery: ...
def _find_best_match(entries, query, order_range=None) -> dict[str, Any] | None: ...
def _locate_units(expected_units, entries) -> dict[str, UnitLocation]: ...
def _entries_in_range(entries, order_range) -> list[dict[str, Any]]: ...
```

可用普通 dict 实现 `MatchQuery` / `UnitLocation`。

### 16.2 单元定位规则

1. 锚点：前 3 个 `fixed`/`manual_only` 且能生成有效 needle 的元素；否则试 unit name
2. 全局搜锚点一次，得 `anchor_order`
3. 范围：`[本单元 anchor_order, 下一单元 anchor_order)`；最后一单元到 `+infinity`
4. required 单元无锚点 → unit FAIL；下级元素 `UNKNOWN template_generation_element_unit_unlocated`，不全文搜
5. optional 单元无定位 → unit UNKNOWN；下级不全文搜

### 16.3 元素匹配规则

```python
match = _find_best_match(entries, query, unit["located"]["order_range"])
```

- 命中 → presence PASS；style 用同一 `match`
- 未命中：有 query 的 fixed/manual → FAIL missing；无 query → UNKNOWN uncheckable

### 16.4 样式绑定纠偏

1. `_style_check()` 的 `match` 必须来自本单元 `_find_best_match()`
2. `iter_visible_text_entries()` 对 table cell 补 `style_details`
3. `_actual_style_properties()` 回退：`dominant_run` → `paragraph_run_properties` → `style_inheritance.run` → UNKNOWN
4. `_expected_style_requirements()` 去掉 4 字体白名单，通用抽取字体名

### 16.5 新增测试

- `test_template_gap_single_style_mutation_fails_only_that_element`
- `test_template_gap_missing_required_element_is_presence_fail`
- `test_template_gap_matches_repeated_text_inside_unit_range`

### 16.6 验证

```bash
uv run pytest tests/contract/test_real_core_generated_template_gap.py \
  -k "repeated_text_inside_unit_range or single_style_mutation" -q
```

---

## 17. C5：coverage 与 e2e 回归

### 17.1 `coverage.py`

`_real_core_template_gap_findings()` 继续检查：

```text
generated_template.docx
generated_template_tree.json
template_gap_report.json
template_gap_report.md
template_gap_report.docx
```

不变：hash 绑定 `generated_template.docx`；`blocking_status in {FAIL, UNKNOWN}` 仍阻断。

改动：`summary` 须含 `per_unit`；不再要求 `check_items`。

### 17.2 `template_generation_coverage_from_report(report, tree)`

| 能力点 | 判断来源 |
|--------|----------|
| `output_docx` | `report["input"].status == PASS` |
| `actual_tree` | `tree.input_valid_docx` 且 entry 有 `source_ref` |
| `unit_match` | 存在 unit presence check |
| `element_match` | 存在 element presence check |
| `style_match` | 存在 element style check |
| `header_footer_match` | 任一 unit `dimensions.header_footer` 非空 |
| `page_rule_match` | 任一 unit `dimensions.page` 非空 |
| `field_match` | 任一 unit `dimensions.fields` 非空 |
| `numbering_match` | 任一 unit `dimensions.numbering` 非空 |
| `report` | 有 `summary` 且有 `units` |

### 17.3 新增测试

- `test_real_core_gap_uses_simulated_generated_template_fixture`

### 17.4 验证

```bash
uv run pytest tests/contract/test_real_core_generated_template_gap.py \
  tests/contract/test_contract_gates.py \
  tests/e2e/test_bootstrap_cli.py -q

uv run docfit eval coverage --profile real-core-v0 --out /tmp/docfit_real_core_coverage
```

---

## 18. 关键文件索引

| 文件 | 职责 |
|------|------|
| `src/docfit/harness/generated_template_gap.py` | 主战场：结果树、匹配、汇总、报告渲染 |
| `src/docfit/harness/generated_template_inspector.py` | 解析树、`order`、`style_details` |
| `src/docfit/harness/coverage.py` | 能力点派生、blocking 校验 |
| `src/docfit/harness/profiles.py` | `generated_template_docx` 配置 |
| `src/docfit/convert/orchestrator.py` | eval 入口切换被测对象 |
| `tests/contract/test_real_core_generated_template_gap.py` | contract 测试主文件 |

复用：`merge_statuses`（`core/status.py`）；`inspect_generated_template_docx` 解析树主体不动。

---

## 19. 完整测试清单

| 测试 | 证明什么 |
|------|----------|
| `test_template_gap_minimal_fixture_can_pass_cleanly` | 全对样卷 → PASS |
| `test_template_gap_single_style_mutation_fails_only_that_element` | 定点样式 FAIL |
| `test_template_gap_missing_required_element_is_presence_fail` | 删必填 → presence FAIL |
| `test_template_gap_unsearchable_fixed_element_is_unknown_not_fail` | 无 needle → UNKNOWN |
| `test_template_gap_matches_repeated_text_inside_unit_range` | 跨单元同文不串台 |
| `test_template_gap_normalizes_template_noise` | 去噪匹配 |
| `test_real_core_gap_uses_simulated_generated_template_fixture` | 被测对象路径正确 |

---

## 20. 执行顺序速查

```text
C0 固定被测对象 → 三校 gap 只读 simulated 业务生成模板，报告 path 不得指向 school-*.docx
C1 最小 PASS 夹具 → 必须先绿
C2 分层结果树 → contract 全绿
C3 匹配去噪 + UNKNOWN → 湖南农大 missing 下降
C4 单元范围匹配 + 样式 → 串台/样式定点测试
C5 coverage + e2e → 全量回归
```

---

## 21. 与原始 Codex 计划的关系

- **技术内容与** [template-gap-engine-layering-refactor.md](./template-gap-engine-layering-refactor.md) **一致**，本阅读版仅重组结构、补充非研发说明。
- 实施以本文 **Stop condition（第 8 节）** 与 **第二部分 C0–C5** 为准。
- 原始 Codex 文档可保留作 diff 对照；后续若 Codex 计划有更新，应同步修订本文第二部分。
