# 模板解析重构执行计划

Last updated: 2026-06-25

一句话结论：模板解析支撑流程只接受学校原始 Word，产出一条唯一的可追溯 artifact 链；学校 gold/config 只用于开发评测、已登记学校增强和验收，不是普通 `template-generate` 的必需输入。

## 范围

本计划只覆盖模板解析和可填模板生成支撑，不处理学生内容提取、内容放置和最终渲染。旧的 `source_template_tree/template_structure_candidates/template_generation_model/template_generation_plan/template_generation_manifest/generated_template.docx` 不再作为主语义产物；如仍落盘，只能作为新产物的兼容包装或调试视图。

唯一流水线：

```text
source_template.docx
  -> document_facts.json
  -> unit_map.yaml
  -> element_spec.yaml
  -> global_spec.yaml
  -> template_spec.yaml
  -> fillable_template.docx + build_manifest.json
```

## 总门禁

| 门禁 | 判定 |
| --- | --- |
| 缺输入、输入不是 DOCX | `UNKNOWN` 或 `FAIL`，取决于文件是否存在和是否可打开 |
| 缺标准、缺 verifier、缺 coverage | `UNKNOWN` |
| 可见对象未建模且未登记 | `UNKNOWN` |
| 字段缺失导致无法追溯或执行 | `FAIL` |
| 规则与 AI 分歧、低置信 AI 项未审核 | `UNKNOWN` |
| 任一阶段 `FAIL/UNKNOWN` | 不能宣称模板解析成功 |

## Phase 1：统一 artifact 模型

目标：替换现有 01-05 和外部 T1-T6 双命名，形成唯一数据流。

输入：学校原始模板 Word。

输出：`document_facts.json`、`unit_map.yaml`、`element_spec.yaml`、`global_spec.yaml`、`template_spec.yaml`、`fillable_template.docx`、`build_manifest.json`。

阻断条件：同一业务含义同时由新旧产物独立承载；字段缺少 producer/consumer/缺失后果说明。

测试命令：

```bash
uv run pytest tests/contract/test_template_generate.py -q
uv run pytest tests/contract/test_contract_gates.py -q
```

## Phase 2：T1 document facts

目标：先把 Word 读对，不做语义判断。`document_facts.json` 是唯一事实库，后续只引用稳定 id/range，不复制事实。

输入：`source_template.docx`。

输出：`document_facts.json`。

必须覆盖：正文、表格、页眉页脚、文本框、脚注、图片、字段、分页、分节、编号、未知可见对象。run 级事实必须有 `raw_run_id`、`logical_run_id`、`merged_from`、文本、kind、有效样式和样式来源。

阻断条件：可见对象丢失；`unknown_objects` 非空却返回 `PASS`；raw/logical id 不唯一。

测试命令：

```bash
uv run pytest tests/contract/test_template_generate.py -q
```

## Phase 3：T2 unit map 与 T4 global spec

目标：用确定性规则识别单元边界和全局页面规则，不接 AI。

输入：`document_facts.json`。

输出：`unit_map.yaml`、`global_spec.yaml`。

阻断条件：required unit 缺失；边界证据不足却写成确定；页面/分节规则既没有明确值也没有 `UNKNOWN`/flag。

测试命令：

```bash
uv run pytest tests/contract/test_template_generate.py -q
uv run pytest tests/contract/test_real_core_generated_template_gap.py -q
```

## Phase 4：T3 element spec

目标：把单元内部拆成可执行元素。确定性规则先覆盖占位符、下划线填空、格式说明、颜色说明、对齐空格、手打目录、PAGE/TOC/SEQ 候选；AI 只处理残余分类。

输入：`document_facts.json`、`unit_map.yaml`、`ontology.yaml`。

输出：`element_spec.yaml`。

阻断条件：`fill` 缺 `fill_source`；`manual_only` 没有人工填写语义；`generated` 没声明字段类型；可能是真内容的说明文字被删除；低置信 AI 项没有审核记录。

测试命令：

```bash
uv run pytest tests/contract/test_template_generate.py -q
```

## Phase 5：T5 template spec 与审核闭环

目标：合并 `unit_map + element_spec + global_spec` 为唯一主产物 `template_spec.yaml`，并让人工审核结果成为 gold 来源。

输入：`unit_map.yaml`、`element_spec.yaml`、`global_spec.yaml`、审核记录。

输出：`template_spec.yaml`、`review_queue.yaml`。

阻断条件：schema 非法；id 重复；引用不存在；required unit 不齐；fill/source/page profile 不可解析；AI 低置信项缺审核记录。

测试命令：

```bash
uv run pytest tests/contract/test_template_generate.py -q
```

## Phase 6：T6 fillable template build

目标：在源 DOCX 副本上做减法构建，产出稳定可填模板。

输入：`source_template.docx`、`template_spec.yaml`。

输出：`fillable_template.docx`、`build_manifest.json`。

执行规则：施工定位使用 `raw_run_id`/source ref，不用段落文本搜索；`fixed/template_default` 原样保留；`instruction_remove` 删除 run 或字符 span 并保留必要 OOXML；`fill/manual_only` 生成带 `tag=element_id` 的 SDT 内容控件；`generated` 生成 Word 字段或字段占位能力；不得再插入内部 `[[DOCFIT_*]]` 文本 marker。

阻断条件：manifest 无 action/source/output 追踪；成品不是有效 DOCX；成品残留内部 marker；fill/manual_only 不是带 tag 的 SDT；generated field 无法定位。

测试命令：

```bash
uv run pytest tests/contract/test_template_generate.py -q
uv run pytest tests/contract/test_real_core_generated_template_gap.py -q
```

## Phase 7：阶段 verifier 与聚合报告

目标：T1-T6 每一步都能独立输出 `PASS/FAIL/UNKNOWN`，并能报告 `first_bad_stage`。

输入：阶段产物、expected/gold、输入输出 hash、审核记录。

输出：`verification_report.json`、`pm_report.md`。

阻断条件：缺标准、缺 verifier、hash 不匹配、coverage 不足、阶段报告缺状态。

测试命令：

```bash
uv run pytest tests/contract -q
```

## 三校开发评测

三校 gold/config 只用于开发评测、已签收学校验收和可选配置增强。普通 `template-generate` 仍只要求：

```bash
uv run docfit eval template-generate --template <source_template.docx> --out <out_dir>
```

三校 probe 应分别运行模板解析、构建、gap 聚合入口，并把样式、页码、单元顺序、字段问题定位到 T1-T6 的首次出错阶段。
