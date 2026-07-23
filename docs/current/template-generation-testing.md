# 模板生成测试与评测契约

Last updated: 2026-07-23

本文是模板生成整体与 T1/L1/T2-T7/POST_T6 测试、评测和完成标准的唯一长期事实源。旧评测、阶段标准和单阶段 gold 说明中的长期规则应逐步迁入本文。

本文按测试对象组织：先定义整个模板生成流程，再依次定义 T1、L1、T2-T7 和 POST_T6。每个阶段在一张测试卡里集中说明输入、gold、route、指标、CLI 和报告。当前实现覆盖与未闭环项统一见 `docs/status/INDEX.md`。

每次运行的结果保存在 run 目录；本文只维护长期测试契约。

## 1. 公共约定

- `isolated` 使用阶段冻结输入，衡量当前阶段自身准确度；`cascade` 使用真实上游输出，观察误差传递。
- 阶段冻结输入位于 `inputs/targets/<target_id>/fixtures/template_generation/<stage_id>/`，并由 `fixture_manifest.yaml` 记录来源、版本和 hash。
- T2/T4 的 code、AI、merged 使用同一份冻结输入、同一份 gold 和同一套指标；merged 是阶段主结论。T3 只有 AI canonical route，不生成 Code/Merged 结果。

### 1.1 Gold 的职责和评分边界

Gold 只保存本阶段 canonical 最终输出的正确答案、精确身份和人工来源。Gold 不评价 code 或 AI 如何得到答案，也不评价后续阶段如何执行答案。

每个 gold 字段必须属于以下三类之一：

| 字段类别 | 用途 | 是否进入准确率 |
| --- | --- | --- |
| scored | 本阶段最终输出中需要判断正确与否的标签、边界或字段值 | 是 |
| identity/binding | 把 gold 答案唯一绑定到源 DOCX、L1 身份或上游冻结输入 | 否；绑定失败时该项不可评分 |
| review/evidence | 说明答案由谁、基于什么证据审核，以及当前可信状态 | 否 |

以下信息不属于准确率 gold：

- prompt、模型原始回答、reason、confidence 和思维过程；
- code/AI 的内部规则、调用顺序、递归层级和停止路径；
- T3 的 `split`、`inspect_child_refs`、direct/inherited/fallback/contested；
- API 调用数、最大深度、token 和成本；
- 下游 T5/T6 采用什么具体动作执行上游语义。

上述信息可以进入运行 trace、输入审计、合同检查或成本报告，但不得改变本阶段最终标签准确率。同一组最终 canonical 标签必须得到相同准确率，无论它来自粗层终局判断还是逐项下钻。

### 1.2 Gold 公共必需信息

每份学校阶段 gold/standard 至少必须声明：

| 信息 | 作用 |
| --- | --- |
| `stage_id`、`standard_id`、`artifact_under_test` | 防止拿错阶段、标准或被测产物 |
| `school_id`、模板版本 | 绑定学校和模板版本 |
| gold contract/schema version | 说明 scored item 的字段和计分语义 |
| 源 DOCX 路径与 sha256 | 绑定人工审核时看到的源模板 |
| isolated 上游输入或上游 gold 的 hash | 保证被测 route 绑定同一份已冻结输入；T2/T4 还据此保证三路可比 |
| `gold_status` | 表示 gold 内容是否已完整人工复核 |
| `review_metadata` | 审核人、审核时间、审核来源和变更原因 |
| label/value universe | 声明本阶段允许进入 scored 字段的值 |
| scored item 列表 | 保存本阶段最终正确答案 |
| unknown/excluded 列表及原因 | 显式说明哪些对象不进入主准确率 |
| `auto_update_allowed: false` | 禁止用某次运行结果自动反写 gold |

`standard_state` 只表示文件生命周期，不能代替 `gold_status`。`gold_status=VERIFIED` 必须表示声明的 scored universe 已完整复核；只复核部分样本或部分字段时必须是 `PARTIAL`。

### 1.3 Gold 计分共同规则

1. Gold 文件保存答案和评分契约，不保存某次运行计算出的 accuracy/F1 数值。
2. T2/T4 的 code_raw、ai_raw、merged 必须先归一化为该阶段同一 canonical scored item，再和同一份 gold 比较；T3 只归一化唯一 AI canonical 输出。
3. 每个 scored item 只能有一个最终 expected value；重复、重叠或互相冲突的 gold 使该项不可评分。
4. 缺失预测按错误处理；非法或无法绑定的预测按错误并单独报告 binding mismatch。
5. `unknown` 不进入主准确率分母，但必须计入 gold coverage 和 unknown 数量；不得通过大量标记 unknown 提高表面准确率。
6. 定位、trace、schema、必需字段和输入完整性可以作为独立合同门禁，但不得混入业务标签准确率。
7. T2/T4 route 报告必须分别给出 code、AI、merged 指标和 merged delta；T3 只报告 AI canonical 指标。route 不可用时明确 `NOT_AVAILABLE`，不能借用其他 route 的结果，也不能用 safe Keep 把不可用提升为可用。

Gold 内容状态统一为：

| 状态 | 含义 |
| --- | --- |
| `VERIFIED` | 已复核，可作为声明范围内的准确率基线 |
| `PARTIAL` | 只有部分维度或样本已复核 |
| `DISPUTED` | 已发现内容冲突或准确性问题 |
| `MISSING` | 当前阶段没有所需 gold |

`standard_state` 表示文件生命周期，`gold_status` 表示内容可信度。报告同时记录两者；gold_status 不是 `VERIFIED` 时，完整质量结论为 `UNKNOWN`。

阶段测试统一目标入口为：

```text
docfit template stage verify --stage <stage_id>
```

统一阶段报告为：

```text
<stage_run_root>/
  stage_test_report.json
  stage_test_report.md
  route_metrics.json
  artifacts/
```

报告公共字段为：测试模式、target/version、输入路径与 hash、gold 路径/hash/status、`run_status`、`quality_status`、route 指标、阶段指标、blockers 和 evidence。

统一阶段入口和报告目前是目标契约；当前 `docfit template stage t2|t3|t4` 只是 AI observation 调试入口。

## 2. 整个模板生成流程

| 项目 | 测试契约 |
| --- | --- |
| 目标 | 从学校源模板运行 T1、L1、T2-T7 和 POST_T6，判断最终可填 Word 是否符合学校标准，并定位最早失败阶段 |
| 输入 | `--school`、`inputs/targets/<target_id>/raw/source_template.docx`、`--template-version`、AI mode；AI 可使用 live、replay 或 bundle |
| Gold | `template_generation/t1_document_facts.standard.yaml`、`t2_unit_pagination.standard.yaml`、`t3_element_policy.standard.yaml`、`t4_global_layout.standard.yaml`、`t5_template_spec.standard.yaml`，以及 `template_quality/final_template.expected.yaml` |
| 指标 | `run_status`、`quality_status`、stage statuses、`first_bad_stage`、T2/T4 三路准确率与 merge delta、T3 AI canonical 准确率、最终 gap、证据覆盖 |
| CLI | 当前入口：`docfit template verify`；兼容入口：`docfit eval template-generation-full` |
| 报告 | `full_summary.json/.md`；包含输入和 gold 身份、各阶段 stage card、route 准确率、first bad stage、blockers、owner、evidence 和最终 gap |

当前完整命令示例：

```bash
uv run docfit template verify \
  --school hunannongye \
  --template inputs/targets/hunannongye/raw/source_template.docx \
  --template-version v1 \
  --ai off \
  --out /private/tmp/docfit_template_verify_hunannongye
```

AI 模式替换为 `--ai live`、`--ai replay --replay path/to/transcript.json` 或 `--ai bundle --bundle path/to/observation_bundle.json`。

## 3. T1：源 DOCX 事实

| 项目 | T1 测试契约 |
| --- | --- |
| 目标 | 验证源 DOCX 是否被完整、稳定地转换为可追溯的客观事实 |
| Isolated 输入 | 学校源模板 DOCX；身份为源文件 sha256 |
| Cascade 输入 | 与 isolated 相同；T1 没有业务上游 |
| 输出 | `01_document_facts.json` |
| Gold | `template_generation/t1_document_facts.standard.yaml`；记录 T1 客观事实覆盖与来源身份 |
| Route | code-only；`routes.code` |
| 指标 | 主指标 `fact_coverage`；body flow、run、section、header/footer、field、table/image/object、source trace、schema/hash/index 覆盖，以及 unknown 数量 |
| CLI | 目标入口：`docfit template stage verify --stage t1 --input-mode isolated --fixture .../t1 --routes code` |
| 报告 | `routes.code.primary_accuracy=fact_coverage`；输出各事实类别覆盖、trace、unknown、mismatches 和 hash |

## 4. L1：统一事实契约

| 项目 | L1 测试契约 |
| --- | --- |
| 目标 | 验证 T1、render、object/page binding 是否被封存为稳定、只读、可重算 hash 的统一输入 |
| Isolated 输入 | 冻结的 T1 document facts、render facts 和 object/page binding |
| Cascade 输入 | 某次 template-generate 的真实 T1/render 输出 |
| 输出 | `01.5_l1_input_contract.json` |
| Gold | 当前只有 L1 schema、identity/hash 和 coverage contract；无学校独立 gold，gold_status=`MISSING` |
| Route | code/contract-only；`routes.code` |
| 指标 | 主指标 `contract_coverage`；事实和 binding 覆盖、identity 唯一性、引用完整性、hash 可重算、visual unavailable 和 unknown 数量 |
| CLI | 目标入口：`docfit template stage verify --stage l1 --input-mode isolated --fixture .../l1 --routes code` |
| 报告 | contract coverage、identity/hash、render/page/object binding、unknown 和 evidence |

## 5. T2：单元与边界

| 项目 | T2 测试契约 |
| --- | --- |
| 目标 | 验证单元识别、顺序、边界、source_seq 归属和分页策略 |
| Isolated 输入 | 冻结的 `t2_l1_stage_input`；当前全流程对应 `01.6_t2_l1_stage_input.json` |
| Cascade 输入 | 某次 template-generate 的真实 L1/T2 stage input |
| 输出 | `02.0_t2_code_unit_map.yaml`、`02.2_t2_ai_unit_observation.yaml`、`02.3_t2_merged_unit_map.yaml` |
| Gold | `template_generation/t2_unit_pagination.standard.yaml`；只评分 unit identity/order/boundary/source attribution/page_policy 最终值 |
| Route | `code_raw`、`ai_raw`、`merged`；merged 为主结论 |
| 指标 | 主指标 `unit_f1`；precision/recall/F1、order exact match、boundary accuracy、source_seq attribution coverage、page_policy coverage/field accuracy/exact match、missing/extra units |
| Route 对比 | `code_accuracy`、`ai_accuracy`、`merged_accuracy`、`merged_vs_code_delta`、`merged_vs_ai_delta`、route availability、merge consumption |
| CLI | 目标入口：`docfit template stage verify --stage t2 --input-mode isolated --fixture .../t2 --routes code_raw,ai_raw,merged` |
| 报告 | 开头展示三路准确率和两个 delta；各 route 保存完整 T2 子指标、mismatches、gold/hash 和证据 |

### 5.1 T2 Gold 内容

T2 gold 只回答：

1. 模板中有哪些 unit；
2. unit 的顺序；
3. 每个 unit 覆盖哪些源节点；
4. 每个 unit 的 `page_policy.start/scope` 最终标签。

T2 scored 字段为：

| Gold 字段 | 含义 | 指标 |
| --- | --- | --- |
| `expected.unit_order`、`units[].unit_id` | unit 集合和顺序 | unit precision/recall/F1、order exact match |
| `units[].boundary.source_seq_range` 或 `source_ref_range` | unit 起止边界 | boundary accuracy |
| 由 boundary 推导的 source 归属 | 每个源节点属于哪个 unit | source attribution accuracy/coverage |
| `units[].page_policy.start` | unit 如何开始 | field accuracy |
| `units[].page_policy.scope` | unit 是否可与相邻内容共享页面范围 | field accuracy |

`name`、anchors、notes 和 source text 可以用于人工审核和 mismatch 定位，但不进入主准确率。T2 gold 不记录元素 Keep/Fill/Delete、T4 全局版式、T6 的 page break/section break 动作，也不记录 AI 如何发现 unit。

最小示例：

```yaml
expected:
  unit_order: [cover, toc, abstract_cn]
  units:
    - unit_id: cover
      boundary:
        source_seq_range: {start: 1, end: 16}
      page_policy:
        start: document_start
        scope: single_page_exclusive
```

## 6. T3：元素与策略

| 项目 | T3 测试契约 |
| --- | --- |
| 目标 | 验证每个最终 atomic run/span 的 keep、fill、delete 标签 |
| Isolated 输入 | 冻结的 L1/T3 facts packet，加上由 T2 gold 物化的固定 unit map；不使用某次 T2 actual |
| Cascade 输入 | 同一次完整运行的 sealed L1 加唯一 T2 最终结果；availability 随 T2 最终结果进入 T3 |
| 输出 | 输入审计 `03.0_t3_hierarchical_stage_input.json`；AI 原始证据 `03.1_t3_ai_element_observation.yaml`；稀疏自检 `03.1.5_t3_sparse_decision_trace.json`；唯一正式结果 `03_element_spec.yaml`；物化自检 `12_t3_materialization_trace.json` |
| Gold | `template_generation/t3_element_policy.standard.yaml`；atomic action gold 按动作统一的 run 或混合 run 内 span 评分 |
| Route | 仅 `ai`；`03_element_spec.yaml` 为 canonical 最终结果 |
| 指标 | 主指标 `exact_action_accuracy`；Keep/Fill/Delete precision/recall/F1、`action_macro_f1`、atomic coverage、conflict count 和 false delete |
| Route 对比 | 无 Code/Merge 对比和 merge delta；报告 `ai_accuracy`、route availability 和 canonical materialization self-check |
| CLI | 目标入口：`docfit template stage verify --stage t3 --input-mode isolated --fixture .../t3 --routes ai` |
| 报告 | AI canonical atomic action accuracy、各动作指标、run/span mismatch、gold-input audit；tree/schema/coverage/materialization trace 作为独立合同检查 |

### 6.1 T3 Gold 内容

T3 主准确率只评价最终 atomic 内容标签：

```text
keep   原样保留
fill   由学生内容或系统值替换/形成填写位置
delete 从最终模板内容中删除
```

每个 raw run 必须采用且只能采用以下一种 gold 形状：

1. 整个 run 动作统一：写一条 run scored item。
2. run 内存在不同动作：不再写整 run 的单一标签，改写为两条或更多 span scored item。

当前 `expected.run_span_ledger` 的目标粒度为 `adaptive_run_or_span`。Run item 至少包含 `target_kind=run`、`raw_run_id`、原始 text 和 `expected_action`；span item 至少包含 `target_kind=span`、`raw_run_id`、`start`、`end`、对应原始 text 和 `expected_action`。

`start/end` 使用半开区间 `[start, end)`。同一混合 run 的 span 必须：

- 坐标落在原始 run text 内；
- `text == raw_run_text[start:end]`；
- scored 字符范围无重叠；
- 完整覆盖该 run 的 scored 内容，不允许 silent gap；
- 每个 span 只有一个 `expected_action`。

示例：

```yaml
core_action_contract:
  primary_metric: exact_action_accuracy
  gold_granularity: adaptive_run_or_span
  allowed_actions: [keep, fill, delete]

expected:
  run_span_ledger:
    - target_kind: run
      raw_run_id: p_0007.r_001
      text: "姓名："
      expected_action: keep

    - target_kind: span
      raw_run_id: p_0007.r_002
      start: 0
      end: 2
      text: "张三"
      expected_action: fill

    - target_kind: span
      raw_run_id: p_0007.r_002
      start: 2
      end: 10
      text: "（请用宋体填写）"
      expected_action: delete
```

T3 AI 可以在 unit/table/row/cell/paragraph/run/span 任一合法层级产生判断，但评分前必须由程序自检并确定性展开为上述 atomic identity。Gold 不评价 `split`、停止层级、inspect child、继承路径、调用次数或 element 分组。

`unit_id`、`paragraph_id`、`source_seq`、`source_refs` 和 `logical_run_id` 可以保留为定位与绑定字段，但不进入动作准确率。`element_id`、role、fill_source、generated 字段、trace 和 required fields 属于 `element_spec` 合同检查；除非未来单独批准新的人工 gold 维度，否则不得混入 `exact_action_accuracy`。

代理可以基于与 gold hash 一致的冻结 DOCX、Word 可视页面和 sealed L1 facts 完成候选动作审查，并把结果记录在独立的 `delegated_review_metadata` 中。该证据可以消除候选队列、形成正式 run/span scored item，但不能冒充人工签核：在人工确认审核人和时间以前，`review_metadata.reviewed_at` 保持为空、`gold_status` 保持 `PARTIAL`，完整质量结论仍为 `UNKNOWN`。只有人工复核完整 scored universe 后才能晋升为 `VERIFIED`。

## 7. T4：全局版式

| 项目 | T4 测试契约 |
| --- | --- |
| 目标 | 验证页面、分节、页眉页脚、页码、编号和视觉版式规则 |
| Isolated 输入 | 冻结的 `t4_l1_stage_input`、render 页面和页面绑定；当前全流程对应 `01.8_t4_l1_stage_input.json` |
| Cascade 输入 | 某次 template-generate 的真实 L1/render 输出 |
| 输出 | 三路正式输出为 `04.0_t4_code_global_spec.yaml`、`04.1.5_t4_ai_global_spec.yaml`、`04.2_t4_merged_global_spec.yaml`，均遵守 `global_spec` 契约；`04.1_t4_ai_layout_observation.yaml` 仅保留为 AI 原始证据 |
| Gold | `template_generation/t4_global_layout.standard.yaml`；只评分 T4 拥有的 section/page setup/header-footer/page-numbering/numbering 最终值 |
| Route | `code_raw`、`ai_raw`、`merged`；merged 为主结论 |
| 指标 | 主指标 `layout_accuracy`；section detection/boundary、page setup、header/footer、page numbering 和 numbering definition 字段准确率 |
| Route 对比 | `code_accuracy`、`ai_accuracy`、`merged_accuracy`、两个 delta、route availability、merge consumption |
| CLI | 目标入口：`docfit template stage verify --stage t4 --input-mode isolated --fixture .../t4 --routes code_raw,ai_raw,merged` |
| 报告 | 三路 layout accuracy、各版式维度、两个 delta 和 mismatch samples；视觉证据覆盖、unknown 和输入完整性作为独立审计 |

### 7.1 T4 Gold 内容

T4 gold 只回答 `global_spec` 中由 T4 负责的最终版式值：

| Scored 对象 | Scored 字段 |
| --- | --- |
| section profile | section identity、边界和归属 |
| page setup | 页面尺寸、方向、上下左右边距及其他批准字段 |
| header/footer | 是否存在、适用范围、part/ref 绑定和批准的显示策略 |
| page numbering | 是否显示、格式、起始值、适用 section/range |
| numbering definition | 编号层级、格式、起始值和必要绑定 |

T4 gold 必须用 L1 中稳定的 section/source/page/header/footer/numbering 身份绑定 expected value。视觉截图、bbox、识别理由和 confidence 可以作为审核证据，但不进入 `layout_accuracy`。

T2 的 `unit_order` 和 `page_policy` 是 T4 isolated 测试的冻结上游输入，不是 T4 自身业务标签。T4 standard 可以保留它们的 hash 或 binding audit，证明使用了正确的 T2 gold，但不得把 T2 unit/page_policy 正确性重复计入 T4 主准确率。

最小示意：

```yaml
expected:
  section_profiles:
    - section_ref: section_001
      boundary:
        start_source_seq: 1
        end_source_seq: 16
      page_setup:
        orientation: portrait
        margin_top_pt: 72
        margin_bottom_pt: 72

  page_numbering:
    - section_ref: section_002
      display: true
      format: decimal
      start: 1
```

Prompt、模型选择页、视觉调用次数、推理过程，以及 T6 最终使用何种 OOXML 动作，不属于 T4 gold。

## 8. T5：主规格合并

| 项目 | T5 测试契约 |
| --- | --- |
| 目标 | 验证 T2 单元、T3 元素和 T4 版式是否被无损合并为可执行 template spec |
| Isolated 输入 | 冻结的 T2 最终 unit map、T3 唯一 AI canonical element spec、T4 最终 global spec 和 L1 identity/hash；每份输入都带 availability |
| Cascade 输入 | 同一次完整运行的真实 T2/T3/T4/L1 输出 |
| 输出 | `05_template_spec.yaml` |
| Gold | `template_generation/t5_template_spec.standard.yaml`；覆盖主规格合并契约 |
| Route | code-only；`routes.code` |
| 指标 | 主指标 `merge_contract_accuracy`；unit precision/recall/F1/order、unit-element binding、unit-section binding、输入 hash/trace、review flags 和缺失上游字段 |
| CLI | 目标入口：`docfit template stage verify --stage t5 --input-mode isolated --fixture .../t5 --routes code` |
| 报告 | code accuracy、各 binding 指标、hash/trace 完整度、mismatches 和 evidence |

## 9. T6：构建与执行

| 项目 | T6 测试契约 |
| --- | --- |
| 目标 | 验证 T5 动作是否准确作用到源 DOCX，并在最终 Word 中留下可观察效果 |
| Isolated 输入 | 源 DOCX package、冻结的 T5 template spec 和 L1 identity resolver/hash |
| Cascade 输入 | 某次完整运行的真实 T5/L1 和源 DOCX |
| 输出 | `06.1_fillable_template.docx`、`06.2_build_manifest.json` |
| Gold | 当前使用构建动作契约和最终 DOCX fresh observation；无学校独立 gold，gold_status=`MISSING` |
| Route | code-only；`routes.code` |
| 指标 | 主指标 `execution_effect_accuracy`；动作成功率、delete/keep/fill/generated 效果、分页/分节/keep 效果、manifest 与 fresh observation 一致性、未执行动作 |
| CLI | 目标入口：`docfit template stage verify --stage t6 --input-mode isolated --fixture .../t6 --routes code` |
| 报告 | execution effect accuracy、动作分类结果、fresh observation、manifest mismatch、blockers 和 evidence |

## 10. T7：运行时验证

| 项目 | T7 测试契约 |
| --- | --- |
| 目标 | 对账 T1-T6 的 schema、hash、引用、动作和最终结果，并给出可靠的最早失败阶段 |
| Isolated 输入 | 冻结的 L1、T5/T6 产物和最终 DOCX |
| Cascade 输入 | 同一次完整运行的真实 L1、T5/T6 和最终 DOCX |
| 输出 | `07_verification_report.json` |
| Gold | 当前使用 verification contract；无学校独立 gold，gold_status=`MISSING` |
| Route | code-only；`routes.code` |
| 指标 | 主指标 `verification_coverage`；T1-T6 检查覆盖、hash/identity/引用/动作对账、first_bad_stage、UNKNOWN 数量和假绿阻断 |
| CLI | 目标入口：`docfit template stage verify --stage t7 --input-mode isolated --fixture .../t7 --routes code` |
| 报告 | verification coverage、上游检查状态、first_bad_stage、未验证项、假绿阻断和 evidence |

## 11. POST_T6：最终 Word 差距检查

| 项目 | POST_T6 测试契约 |
| --- | --- |
| 目标 | 验证最终 `06.1_fillable_template.docx` 是否符合学校签收的最终模板标准 |
| Isolated 输入 | 固定的待测最终 DOCX；当前 fixture 位于 `inputs/targets/<target_id>/fixtures/template_gap/` |
| Cascade 输入 | 某次 template-generate 生成的真实最终 DOCX |
| 输出 | `generated_template_tree.json`、`template_gap_report.json/.md/.docx` |
| Gold | `template_quality/final_template.expected.yaml`；覆盖最终模板签收质量 |
| Route | code-only；`routes.code` |
| 指标 | 主指标 `final_gap_status`；blocking gap、分类 gap、checked/unchecked coverage 和 PASS/FAIL/UNKNOWN |
| CLI | 当前入口：`docfit eval template-gap --school ... --generated-template ... --out ...`；后续接入统一 stage verify |
| 报告 | 当前详细 gap 报告；统一 stage report 汇总 gold status、gap status、分类 gap、blockers 和详细报告路径 |

## 12. 维护方式

输入、gold、指标、CLI 或报告契约变化时，更新对应阶段测试卡。fixture 数据变化写入 `fixture_manifest.yaml`，gold 变化写入标准文件 `review_metadata`。

Gold contract 或 scored 字段变化还必须：

1. 提升 gold contract/schema version；
2. 重新验证源 DOCX 和上游冻结输入 hash；
3. 更新 `review_metadata.change_reason`；
4. 将受影响 gold 的 `gold_status` 暂时降为 `PARTIAL`，直至新 scored universe 完成人工复核；
5. 同步 verifier、route evaluator、标准质量检查和合同测试；
6. 禁止在 candidate 结果出来后修改 gold、计分分母或晋升阈值。

| 日期 | 变化 |
| --- | --- |
| 2026-07-20 | 按整个流程和各阶段改为单卡片结构。当前实现缺口后续迁入 `docs/status/`。 |
| 2026-07-22 | 移除测试卡中的当前缺口，统一由 `docs/status/active/template-generation-test-contract-coverage.md` 追踪。 |
| 2026-07-23 | 增加公共 Gold 契约；明确 T2/T3/T4 只评分本阶段最终 canonical 输出，T3 采用 adaptive run/span atomic action gold，不评价分层决策路径；T4 上游 T2 绑定不重复计入 T4 准确率。 |
| 2026-07-23 | 明确代理 Word 审查可以形成待人工确认的 scored item，但不能代替人工签核或把 `PARTIAL` 自动晋升为 `VERIFIED`。 |
| 2026-07-23 | T3 收敛为唯一 AI canonical route；删除 T3 Code/Merged 测试面，程序检查改为 schema/identity/coverage/materialization self-check，availability 随唯一最终输出向下传递。 |
