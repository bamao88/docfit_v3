# T4 global_spec 优化讨论稿

Last updated: 2026-06-25

Status: Partially implemented on 2026-06-25.

本轮已经落地 Step 1、Step 2 和 Step 3 的主体：

- `global_spec.yaml` 升级到 `artifact_version: "1.1"`，`section_profiles[]` 现在包含 `boundary`、per-section `page_numbering.declared/fields/display` 和 `header_footer.effective_references/parts`。
- 顶层 `global_spec.page_numbering` 改为 summary，能区分 `single`、`mixed`、`none`、`UNKNOWN`，不再把已检查无 PAGE 字段粗暴报成 `page_numbering_unknown`。
- `template_spec.yaml` 升级到 `artifact_version: "1.1"`，`units[]` 新增 `section_profile_refs[]`；`section_profile` 保留为 primary profile 兼容字段。
- T4 verifier 已检查 section id、boundary、页码 evidence、header/footer part 引用；T5 verifier 已检查 unit-section 引用存在和 range 相交。
- T5 不再逐条复制 T4 flags 到 `template_spec.review_flags`。

验证证据：

- `uv run pytest`：130 passed。
- 三校 probe：
  - 湖南农大：1 个 section profile，1/1 有 boundary，19/19 units 绑定 section refs，状态 `UNKNOWN`。
  - 南农本科：11 个 section profiles，11/11 有 boundary，16/16 units 绑定 section refs，primary profiles 分散到 `section_001` 到 `section_008`，状态 `UNKNOWN`。
  - 北大研究生：17 个 section profiles，17/17 有 boundary，76/76 units 绑定 section refs，primary profiles 分散到 `section_001` 到 `section_009`，状态 `UNKNOWN`。

剩余未做：

- T6 仍未消费 `section_profile_refs[]` 来构建真实分页、分节、页眉页脚和 PAGE 字段。
- 空 section 没有可见正文 `source_seq` 时，boundary 只有 paragraph/sectPr 证据，`start_source_seq/end_source_seq` 仍可能为空。
- 三校 template-gap 仍会因为样式、页眉页脚、页码、单元顺序和页面证据不足返回业务质量问题；本计划只把 T4/T5 事实与绑定提前暴露。

本文用于讨论模板解析重构里 T4 的优化方案。它只讨论 `global_spec.yaml` 及其和 T2/T5 的边界，不讨论学生内容提取、placement、最终 render。

相关文档：

- `docs/plans/template-parse-refactor-execution.md`
- `docs/plans/template-parse-refactor-schema.md`
- `docs/plans/template-parse-refactor-stage-issues.md`
- `docs/plans/template-parse-refactor-verification.md`

## 一句话结论

T4 不应该自己识别“封面、摘要、正文”，但 T4 必须把 Word section、页眉页脚、页码字段、页码体例整理成可映射、可验证的物理规则。T2/T5 再用 unit 的 source range 去绑定这些 section profiles，才能回答“这个单元应该用什么页码/页眉/分节规则”。

当前最大缺口不是 T4 完全没读到 section，而是：

1. `global_spec.section_profiles[]` 缺少清晰的 source range / source_seq range。
2. `unit_map.units[].section_profile` 现在是占位逻辑，有 sections 就一律 `section_001`。
3. 顶层 `global_spec.page_numbering` 只扫 PAGE 字段，忽略了 section 里的 `pgNumType` 和页眉页脚字段归属。
4. T4 verifier 只查 section_profiles 是否存在和 flags，没有验证 page numbering、header/footer、section range 是否可解释。

## 讨论目标

本轮讨论要定四件事：

| 议题 | 要定什么 |
| --- | --- |
| T4 职责边界 | T4 只产物理 section facts，还是也产 unit 绑定 |
| `global_spec.yaml` schema | section profile 需要哪些字段，哪些字段是硬门禁 |
| 页码判定 | PAGE 字段、`pgNumType`、页脚文本、无页码如何组合成 `PASS/UNKNOWN` |
| verifier | T4 和 T5 分别应该拦哪些错误 |

## 非目标

- 不让 T4 使用 AI 判断学校语义。
- 不让 T4 自己决定 `cover`、`abstract_cn`、`body_main` 这类 unit。
- 不在 T4 里改 Word。构建仍由 T6 执行。
- 不用学校 gold/config 作为普通 `template-generate` 的必需输入。gold 只用于开发评测和已登记学校验收。

## 当前实现事实

### 生产侧

当前 `src/docfit/template_generation/artifacts.py` 的 `build_global_spec()` 基本是把 T1 facts 搬到 T4：

```text
document_facts.data.sections[]
  -> global_spec.section_profiles[]

document_facts.data.headers_footers[]
  -> global_spec.header_footer

document_facts.data.numbering_definitions / numbering_refs
  -> global_spec.numbering_rules

document_facts.data.fields 中 field_code 以 PAGE 开头的字段
  -> global_spec.page_numbering.field_refs
```

当前 `_page_numbering_from_facts()` 只看 `document_facts.data.fields`：

```text
有 PAGE field -> status=detected
没有 PAGE field -> status=UNKNOWN
```

这会误伤两类情况：

- section 已经有 `page_setup.page_numbering.format/start`，但顶层仍是 `UNKNOWN`。
- 源模板可能确实没有页码字段，应该表达为“已检查，无页码字段”，而不是笼统 `UNKNOWN`。

### T2 联结侧

当前 `_section_profile_for_unit()` 是占位：

```text
没有 sections -> section_unknown
有 sections -> section_001
```

本次三校输出证明了这个问题：

| 学校 | T4 section profiles | T2 unit 数 | T2 unit section_profile |
| --- | ---: | ---: | --- |
| 湖南农大 | 1 | 9 | 全部 `section_001` |
| 南农本科 | 11 | 9 | 全部 `section_001` |
| 北大研究生 | 17 | 9 | 全部 `section_001` |

南农和北大已经从 T1/T4 读出了多个 section，但 T2/T5 没有把 unit 范围映射过去。

### verifier 侧

当前 `_verify_t4_global_spec()` 只做两件事：

1. `section_profiles` 非空。
2. 把 `global_spec.flags[]` 转 findings。

它还没有检查：

- section profile id 是否唯一。
- 每个 section profile 是否有可映射的 source range。
- page numbering 是否有明确状态。
- header/footer reference 是否能对应到 `header_footer` parts。
- 顶层 page numbering 是否和 per-section page numbering 一致。
- T5 里的 unit `section_profile` 是否引用存在且与 unit source range 相交。

## 正确分层

T4 和 unit 的关系应该这样分：

```text
T1 document_facts
  sections[] / fields[] / headers_footers[] / body_flow[]
        |
        v
T4 global_spec
  section_profiles[]：物理分节、页眉页脚、页码字段、页码格式、边界范围
        |
        v
T5 template_spec
  units[] + global
  unit source range 与 section profile range 做联结
```

T4 输出的是“某个 section 的物理规则”。T5 才能回答“某个 unit 用哪套规则”，因为 T5 同时拿得到 T2 的 unit range 和 T4 的 section range。

推荐结论：

- T4 不直接写 `cover -> section_001` 这种语义绑定。
- T4 必须输出足够精确的 section range，让 T5 可以 deterministic join。
- T2 可以继续保留 `section_profile` 字段，但应改成由 range 映射得到，不能再固定 `section_001`。
- 如果一个 unit 跨多个 section，T5 要显式记录多段绑定，而不是丢信息。

## 目标 artifact 形状

下面是建议的 `global_spec.yaml` 结构。字段名可以再讨论，但信息必须覆盖。

```yaml
artifact_type: global_spec
artifact_version: "1.1"

section_profiles:
  - section_profile_id: section_001
    source_ref: word/document.xml:p[45]/sectPr
    boundary:
      start_paragraph_index: 23
      end_paragraph_index: 45
      start_source_seq: 9
      end_source_seq: 27
      end_reason: sectPr
      confidence: high
      evidence_refs:
        - word/document.xml:p[45]/sectPr
    page_setup:
      page_size: {}
      page_margins: {}
      raw_section: {}
    header_footer:
      effective_references:
        - kind: header
          type: default
          part_name: word/header2.xml
          source_ref: word/document.xml:p[45]/sectPr/headerReference[2]
      parts:
        - part_name: word/header2.xml
          kind: header
          text_hash: sha256:...
          source_ref: word/header2.xml
    page_numbering:
      declared:
        format: upperRoman
        start: 1
        source_ref: word/document.xml:p[45]/sectPr/pgNumType
        status: detected
      fields:
        - field_type: PAGE
          part_name: word/footer4.xml
          source_ref: word/footer4.xml:p[1]/field[1]
      display:
        status: detected
        has_page_field: true
        inferred_format: upperRoman
        confidence: high
      flags: []

page_numbering:
  status: mixed
  summary:
    section_count: 11
    sections_with_page_field: 2
    sections_without_page_field: 9
    formats:
      - upperRoman
      - decimal

flags: []
```

关键点：

- `section_profiles[].boundary` 是 T4 优化的核心。没有它，T5 无法把 unit range 映射到 section。
- `page_numbering` 要下沉到 section profile。顶层只能做 summary，不能代替 per-section 判断。
- `header_footer.effective_references` 要保留继承后的引用，便于判定“本 section 实际用哪个页眉页脚 part”。
- `fields[]` 必须绑定到 part 或 body range，不能只在顶层列 PAGE 字段。

## section range 怎么算

T1 inspector 已经给 section 提供：

- `sections[].paragraph_index`
- `sections[].source_ref`
- `sections[].references`
- `sections[].effective_references`
- `sections[].page_numbering`
- `sections[].page_size`
- `sections[].page_margins`

T1 `body_flow[]` 已经给正文元素提供：

- `source_seq`
- `source_ref`
- `order`
- `paragraph_id`
- `kind`

推荐算法：

1. 从 `body_flow[].source_ref` 提取正文 paragraph index，例如 `word/document.xml:p[45]`。
2. 建 `paragraph_index -> source_seq` 的索引。
3. 按 `sections[].paragraph_index` 升序排序。
4. 每个 section 覆盖上一个 section 结束后的正文范围，到当前 `paragraph_index` 为止。
5. `body/sectPr` 对应最后一个 section，范围从上一个 section 结束后到文档末尾。
6. 对 table/cell 这类没有 paragraph index 的 flow item，按 `source_seq` 顺序落入最近的 section range。
7. 如果无法确定 start/end，就写 `boundary.status=UNKNOWN` 并进入 `flags[]`。

南农例子：

```text
section_001: end paragraph p[22]
section_002: end paragraph p[45]
section_003: end paragraph p[74]
...
```

T2 `toc` 的 `source_seq_range` 如果覆盖 p[25] 到 p[45]，T5 就应把它映射到 `section_002`，而不是默认 `section_001`。

## 页码规则怎么判

页码不能只看 PAGE 字段，也不能只看 `pgNumType`。建议拆成三个维度：

| 维度 | 来源 | 含义 |
| --- | --- | --- |
| declared | section `pgNumType` | Word 声明的页码格式和起始值 |
| field evidence | header/footer/body fields | 页面上是否有 PAGE/NUMPAGES 等字段 |
| display policy | section + header/footer 综合 | 该 section 是否应该显示页码，以及显示格式 |

### 状态建议

| 状态 | 条件 | gate |
| --- | --- | --- |
| `detected` | 有 PAGE 字段，且能绑定到 section 的 effective header/footer 或 body range | 可 PASS |
| `declared_only` | 有 `pgNumType`，但没有 PAGE 字段 | 通常 UNKNOWN，除非学校规则允许“仅声明、不显示” |
| `no_page_field` | 已检查 effective header/footer 和 body range，确认无 PAGE 字段 | 可作为事实 PASS，但单元规则是否 PASS 要看学校 expected |
| `ambiguous` | footer/header 有文本或 field，但无法分类为 PAGE/非 PAGE | UNKNOWN |
| `missing_evidence` | 无法检查 header/footer/body fields | UNKNOWN |

### 重要区别

`no_page_field` 不等于 `UNKNOWN`。

如果系统已经检查了 section 的 effective footer/header parts 和正文范围，确认没有 PAGE 字段，那么 T4 事实层可以说“这个 section 没有页码字段”。后续如果学校规则要求页码，T5/template-gap 再报 mismatch。

当前顶层 `page_numbering.status=UNKNOWN` 把“没检查到”和“检查后没有”混在一起，需要拆开。

## T2/T5 联结方案

有两个可选方案。

### 方案 A：T2 写最终 `section_profile`

T2 在生成 `unit_map.yaml` 时用 T1 sections 直接映射：

```yaml
units:
  - unit_id: toc
    source_seq_range: {start: 9, end: 27}
    section_profile: section_002
```

优点：

- `unit_map.yaml` 独立可读。
- T2 verifier 可以直接检查 `section_profile`。

缺点：

- T2 需要理解 T4 的 section profile 命名规则。
- 如果 T4 schema 改了，T2 容易跟着变。
- unit 跨多个 section 时，一个字符串不够表达。

### 方案 B：T5 做 deterministic join

T2 只保留 unit source range；T4 只保留 section source range；T5 合并时生成绑定：

```yaml
units:
  - unit_id: toc
    source_seq_range: {start: 9, end: 27}
    section_profile_refs:
      - section_profile_id: section_002
        overlap_source_seq_range: {start: 9, end: 27}
        page_numbering: {inherited_from: section_002}
```

优点：

- T2/T4 分工干净。
- 支持一个 unit 跨多个 section。
- T5 verifier 可以完整检查引用存在、range 相交、冲突。

缺点：

- `unit_map.yaml` 单独看时没有最终页码语义。
- T5 schema 会比现在更复杂。

推荐：采用方案 B，兼容保留 `units[].section_profile` 作为 primary profile，但新增 `section_profile_refs[]` 表达真实绑定。这样不会让 T2 变成 T4 的消费者，也能支持复杂模板。

## verifier 应该怎么改

### T4 verifier

T4 verifier 只验证 `global_spec` 本身，不验证 unit 语义。

建议新增检查：

| 检查 | 失败状态 |
| --- | --- |
| `artifact_type == global_spec` | `UNKNOWN` |
| `section_profile_id` 唯一 | `FAIL` |
| 每个 profile 有 `boundary` 或明确 `boundary.status=UNKNOWN` | `UNKNOWN` |
| 每个 profile 的 `source_ref` 能追溯到 T1 section | `UNKNOWN` |
| `page_numbering.display.status` 不得缺失 | `UNKNOWN` |
| `detected` 页码必须有 PAGE field evidence | `FAIL` |
| `no_page_field` 必须有检查范围 evidence | `UNKNOWN` |
| header/footer part_name 必须能在 `header_footer` 找到 | `UNKNOWN` |
| profile flags 未审核 | `UNKNOWN` |

### T5 verifier

T5 verifier 负责 unit 与 section 的联结。

建议新增检查：

| 检查 | 失败状态 |
| --- | --- |
| 每个 unit 至少能映射到一个 section profile | `UNKNOWN` |
| `section_profile_refs[].section_profile_id` 存在 | `FAIL` |
| unit source range 与 section boundary 有交集 | `FAIL` |
| unit 跨多个 section 但只写了单 profile | `UNKNOWN` |
| `page_start` 与 section boundary 冲突 | `UNKNOWN` |
| 学校 expected 存在时，unit page profile 精确比较 | `FAIL` |

## 和 T6 的关系

T6 不应该再靠源模板空行或文本搜索决定分页/页码。T6 应只消费 T5 已合并好的规格：

```text
unit.section_profile_refs[]
  -> 是否插入 section break
  -> 使用哪套 header/footer refs
  -> 是否需要 PAGE 字段
  -> PAGE 字段格式和起始值
```

如果 T5 仍有 page/section UNKNOWN，T6 可以继续构建调试 Word，但聚合报告不能宣称模板解析成功。

## 实施拆分

### Step 1：增强 T4 artifact，不改 T6 行为

目标：让 `04_global_spec.yaml` 能表达每个 section 的边界、页眉页脚、页码字段证据。

改动：

- 在 `build_global_spec()` 中生成 `section_profiles[].boundary`。
- 把 `sections[].page_numbering` 标准化到 `section_profiles[].page_numbering.declared`。
- 把 PAGE fields 按 part/range 绑定到 section profile。
- 顶层 `page_numbering` 改成 summary，不再只有 `detected/UNKNOWN`。

验收：

- 南农 11 个 section profile 都有 boundary。
- 北大 17 个 section profile 都有 boundary。
- 湖南农大 1 个 body section 也能表达全篇范围。
- 没有 PAGE 字段时能区分 `no_page_field` 和 `missing_evidence`。

### Step 2：实现 unit -> section join

目标：T5 能根据 T2 unit range 和 T4 section range 生成真实绑定。

改动：

- 新增合并函数，例如 `bind_units_to_section_profiles(unit_map, global_spec)`。
- `template_spec.units[]` 增加 `section_profile_refs[]`。
- `units[].section_profile` 保留为 primary profile，便于旧视图阅读，但不作为唯一事实。
- unit 跨 section 时生成多个 refs，并加 flag 说明是否需要人工审核。

验收：

- 南农 `toc` 不再默认 `section_001`，而是按 source range 落到对应 section。
- 所有 unit 的 section refs 都能在 `global.section_profiles[]` 找到。
- 如果 unit/source range 无法映射，T5 进入 `UNKNOWN`。

### Step 3：补 verifier 和报告

目标：页码/分节问题在 T4/T5 暴露，不等 template-gap。

改动：

- T4 verifier 加 section id、boundary、page evidence、header/footer refs 检查。
- T5 verifier 加 unit-section 引用和 range intersection 检查。
- finding 增加 `verification_stage` 或明确 `stage=T4/T5`，便于报告筛选。
- T5 不再逐条重复 T4 flags，改成聚合或带 `origin_stage` 去重。

验收：

- 缺 section boundary -> T4 UNKNOWN。
- unit 引用不存在的 section -> T5 FAIL。
- unit 无法映射 section -> T5 UNKNOWN。
- PAGE 字段缺失但已确认无页码字段，不再粗暴报 `page_numbering_unknown`。

### Step 4：测试与三校验证

新增测试：

- T4 section boundary：段落中 `sectPr`、body `sectPr`、连续 section、table-before-first-section。
- T4 page numbering：`pgNumType upperRoman`、`pgNumType decimal`、无 PAGE field、footer PAGE field、body PAGE field。
- T4 header/footer：default/even/first refs、继承 refs、part 缺失。
- T5 join：unit 完全落在一个 section、跨多个 section、无法映射、引用不存在。
- 三校 probe：湖南农大、南农、北大重新跑 `template-generate`，对比 `04_global_spec.yaml` 和 `05_template_spec.yaml`。

可复用现有测试事实：

- `tests/contract/test_real_core_generated_template_gap.py::test_generated_template_gap_binds_header_footer_rules_to_sections` 已证明 template-gap 能按 section 检查南农 p[45] 的 header/footer 和 `upperRoman` 页码。
- 这套能力应前移到 T4/T5 verifier，而不是只在最终 gap 阶段暴露。

## 需要讨论的决策

1. T4 是否只输出 section profile，还是也输出 `unit_section_bindings`？
   - 建议：只输出 section profile。unit binding 放 T5。

2. `unit_map.yaml` 是否继续保留单值 `section_profile`？
   - 建议：保留 primary profile 作为可读字段，但 T5 主语义使用 `section_profile_refs[]`。

3. “没有 PAGE 字段”应算 T4 PASS 还是 UNKNOWN？
   - 建议：如果检查范围完整，T4 事实层可 PASS 为 `no_page_field`；如果学校规则要求页码，T5/template-gap 再 FAIL。

4. 是否要给 `body_flow[]` 显式增加 `paragraph_index`？
   - 建议：加。虽然现在可以从 `source_ref` 解析，但显式字段更稳定，也减少后续字符串解析。

5. section profile 边界用 `paragraph_index` 还是 `source_seq`？
   - 建议：两者都写。`paragraph_index` 对应 OOXML section，`source_seq` 对应 T2 unit range。

6. unit 跨多个 section 怎么处理？
   - 建议：T5 允许多 refs；如果该 unit 本应单一 profile，则 verifier 依据 expected 或规则报 `UNKNOWN`。

7. 顶层 `global_spec.page_numbering.status` 是否保留？
   - 建议：保留为 summary，状态可为 `single`、`mixed`、`none`、`UNKNOWN`，不再作为唯一页码真相。

## 推荐推进顺序

1. 先做 T4 `section_profiles[].boundary` 和 per-section page numbering evidence。
2. 再做 T5 unit-section join，不急着让 T2 直接依赖 T4。
3. 补 T4/T5 verifier，让错误定位提前。
4. 最后让 T6 按 `section_profile_refs[]` 构建分页、分节、PAGE 字段。

这样做的好处是：先把事实层和规格层接起来，避免直接在 T6 里补页码逻辑。否则 T6 会继续靠猜测施工，template-gap 仍然只能在最后发现问题。
