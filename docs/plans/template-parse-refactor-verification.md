# 模板解析 verifier 设计

Last updated: 2026-06-25

一句话结论：模板解析每个阶段都必须能独立给出 `PASS/FAIL/UNKNOWN`；最终 `template-gap` 只能补充质量检查，不能替代阶段 verifier。

## 三态规则

| 状态 | 条件 |
| --- | --- |
| `PASS` | gold/expected/verifier 都存在，输入 hash 匹配，coverage 足够，所有硬门禁通过，没有待审 flag |
| `FAIL` | 标准明确且 verifier 能运行，产物违反 schema、id、引用、策略或构建结果 |
| `UNKNOWN` | 缺标准、缺 verifier、缺证据、hash 不匹配、coverage 不足、遇到未建模可见对象、AI/低置信项未审核 |

## T1 verifier：document facts

输入：`document_facts.json`、可选 `document_facts.gold.json`。

检查：

| 检查 | 失败状态 |
| --- | --- |
| artifact/schema/hash 存在 | 缺失 `UNKNOWN` |
| paragraph/table/cell/section/raw_run/logical_run id 唯一 | 不唯一 `FAIL` |
| run 有 text/kind/effective_style/style_provenance | 缺可追溯字段 `UNKNOWN` |
| 字段、图片、文本框、脚注、页眉页脚、编号对象进入事实库或 unknown | 丢失 `FAIL` |
| `unknown_objects` 非空 | `UNKNOWN` |
| gold 存在时精确比较段落/run/表格/字段/section/numbering/unknown_objects | 不一致 `FAIL` |

gold 规则：湖南农大、南农、北大各维护独立 `document_facts.gold.json`。gold 只由人工审核提升，不能从当前输出自动覆盖。

## T2 verifier：unit map

输入：`unit_map.yaml`、从 `template_spec.gold.yaml` 切片得到的 `unit_map.expected.yaml`。

检查：

| 检查 | 失败状态 |
| --- | --- |
| required unit presence 100% | `FAIL` |
| 单元顺序与 expected 一致 | `FAIL` |
| 边界 IoU 达阈值 | 不达阈值 `FAIL` |
| `page_start` 明确或写 `UNKNOWN` | 缺失 `UNKNOWN` |
| `flags/open_questions` 未清空 | `UNKNOWN` |

默认边界 IoU 阈值：开发期三校 required unit `>= 0.8`；若 expected 缺失，阶段状态为 `UNKNOWN`。

## T3 verifier：element spec

输入：`element_spec.yaml`、从 `template_spec.gold.yaml` 切片得到的 `element_spec.expected.yaml`、`ontology.yaml`。

检查：

| 检查 | 失败状态 |
| --- | --- |
| `policy/role/fill_source` 属于闭集 | `FAIL` |
| `fill` 必须有 `fill_source` | `FAIL` |
| `manual_only` 必须有人填语义 | `FAIL` |
| `generated` 必须声明字段类型 | `FAIL` |
| 误删可能是真内容 | 阻断 `FAIL` |
| 规则与 AI 分歧、低置信 AI 项无审核 | `UNKNOWN` |
| AI 原始输入/输出、模型、temperature、schema validation 缺失 | `UNKNOWN` |

评分：policy、role、fill_source 按权重比较；误删真内容优先级最高，直接阻断。

## T4 verifier：global spec

输入：`global_spec.yaml`、从 `template_spec.gold.yaml` 切片得到的 `global_spec.expected.yaml`。

检查：

| 检查 | 失败状态 |
| --- | --- |
| section profiles 引用存在 | `FAIL` |
| 页码体例、页眉页脚、默认字体、编号规则可解析 | 缺证据 `UNKNOWN` |
| expected 存在时字段精确比较 | 不一致 `FAIL` |
| 规则冲突未审 | `UNKNOWN` |

TG-GAP-004 类型分页/分节问题必须能定位到 T2/T4；不能只在最终 gap 暴露。

## T5 verifier：template spec

输入：`template_spec.yaml`、`template_spec.gold.yaml`、review queue。

检查：

| 检查 | 失败状态 |
| --- | --- |
| schema 合法、id 唯一、引用存在 | `FAIL` |
| required unit 齐 | `FAIL` |
| 每个 fill 有 source | `FAIL` |
| 每个 page profile 可解析 | `UNKNOWN` |
| 切片后再合并等于主 gold | 不一致 `FAIL` |
| `review_flags` 非空 | `UNKNOWN` |
| AI 低置信项缺审核记录 | `UNKNOWN` |

只有 `review_flags` 为空且硬门禁全过，才允许进入 T6 自动构建。

## T6 verifier：fillable template

输入：`fillable_template.docx`、`build_manifest.json`、`template_spec.yaml`、重新跑 T1 得到的成品 facts。

检查：

| 检查 | 失败状态 |
| --- | --- |
| 成品是有效 DOCX | `FAIL` |
| manifest action 有 source/run/output/status | 缺失 `UNKNOWN` |
| 无内部 `[[DOCFIT_*]]` 文本 marker | 有残留 `FAIL` |
| `fill/manual_only` 都是带 tag 的 SDT | 缺失 `FAIL` |
| generated field 可定位 | 缺失 `UNKNOWN` |
| instruction_remove 无残留说明文字 | 残留 `FAIL` |
| 重新 T1 后编辑区 facts 能复现 `template_spec` 决定 | 不一致 `FAIL` |

## 聚合报告

输出 `verification_report.json`：

```json
{
  "status": "FAIL",
  "first_bad_stage": "T3",
  "stages": [
    {"stage": "T1", "status": "PASS", "input_hash": "...", "output_hash": "..."},
    {"stage": "T2", "status": "UNKNOWN", "findings": ["..."]}
  ]
}
```

规则：

- 缺标准、缺 verifier、hash 不匹配、coverage 不足一律 `UNKNOWN`。
- 任一阶段 `FAIL/UNKNOWN`，聚合状态不能是 `PASS`。
- `template-gap` 继续检查生成模板与学校签收标准差距，但不能替代 T1-T6 verifier。
- 渲染快照只作为模板质量补充门禁，用于比较页数、页边界、单元分页和关键文字区域。

## 测试命令

核心回归：

```bash
uv run pytest tests/contract/test_template_generate.py -q
uv run pytest tests/contract/test_real_core_generated_template_gap.py -q
uv run pytest tests/contract -q
```

新增合同测试必须覆盖：缺 gold、缺 verifier、AI 低置信未审核、unknown visible object、内部 marker 残留、SDT tag 缺失、hash 不匹配均阻断。
