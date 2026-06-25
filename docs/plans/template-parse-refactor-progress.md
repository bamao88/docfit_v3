# 模板解析重构开发进度

Last updated: 2026-06-25

一句话结论：模板解析重构已经完成第一版工程闭环，`template-generate` 能从学校原始 Word 产出新 artifact 链、可填 Word、构建清单和 T1-T6 verifier 报告；但原计划里的 gold 精确比对、AI 残余分类、人工审核闭环和视觉门禁还没有全部完成。

## 当前基线

| 项 | 当前状态 |
| --- | --- |
| 最近实现提交 | `14e9ac4 feat: refactor template parse artifacts` |
| 前置 checkpoint | `844ee12 chore: checkpoint existing workspace changes` |
| 主入口 | `uv run docfit eval template-generate --template <source_template.docx> --out <out_dir>` |
| 主产物 | `document_facts.json`、`unit_map.yaml`、`element_spec.yaml`、`global_spec.yaml`、`template_spec.yaml`、`fillable_template.docx`、`build_manifest.json`、`verification_report.json` |
| 旧产物口径 | `source_template_tree`、`template_structure_candidates`、`template_generation_model`、`template_generation_plan` 只作为兼容调试视图，不再是主语义 |
| 普通生成输入 | 仍然只要求学校原始模板 Word；学校 gold/config 不作为普通 `template-generate` 必需输入 |

## 阶段进度

| 阶段 | 计划目标 | 当前进度 | 证据 |
| --- | --- | --- | --- |
| Phase 0 文档落地 | 执行计划、schema、verification 文档 | 已完成 | `docs/plans/template-parse-refactor-*.md` |
| Phase 1 统一 artifact 模型 | 替换旧 01-05 / T1-T6 双命名 | 已完成第一版 | 新主产物已落盘；旧产物只作兼容视图 |
| Phase 2 T1 facts | run 级事实层、稳定 id、unknown object | 部分完成 | 已有 `document_facts.json`、run id、logical id、style provenance；三校 gold 还未建立 |
| Phase 3 T2/T4 | 单元切分和全局规则 | 部分完成 | 已有 `unit_map.yaml`、`global_spec.yaml`；边界 IoU/gold 切片还未完成 |
| Phase 4 T3 | 元素与策略标注 | 部分完成 | 已有 `element_spec.yaml`、ontology、fill/manual/generated 策略；AI 残余分类和 review trace 未完成 |
| Phase 5 T5 | 唯一 `template_spec.yaml` 与审核闭环 | 部分完成 | 已有 `template_spec.yaml` 和 review flag 门禁；人工 review queue/promotion 未完成 |
| Phase 6 T6 | 构建稳定可填模板 | 已完成第一版 | `fillable_template.docx` 使用 SDT tag；不再写 `[[DOCFIT_*]]` 文本 marker；`build_manifest.json` 记录动作 |
| Phase 7 verifier | T1-T6 独立 `PASS/FAIL/UNKNOWN` | 已完成第一版 | `verification_report.json` 输出 status、stage status、first_bad_stage |

## 已完成的关键行为变化

- `template-generate` 主链路改为新 artifact：
  `document_facts -> unit_map -> element_spec -> global_spec -> template_spec -> fillable_template + build_manifest`。
- `document_facts.json` 成为事实库，包含可见节点、run id、logical run id、样式来源、字段、分节、表格和 unknown objects。
- `template_spec.yaml` 成为模板解析阶段主产物。
- `template_artifact.json` 只作为旧四阶段接口包装视图。
- `fillable_template.docx` 使用 Word SDT 内容控件承载 `fill/manual_only`，tag 为稳定元素 id。
- 成品 Word 不再写入内部 `[[DOCFIT_SLOT:*]]` 或 `[[DOCFIT_GENERATED:*]]` 文本 marker。
- `render` 已能按 SDT tag 写入内容，同时保留旧 marker 兼容测试。
- `template-gap` inspector 已能解析 SDT 内容控件，并把 SDT tag 当作可填区证据。
- 新增 T1-T6 deterministic verifier，聚合到 `verification_report.json`。

## 验证结果

| 验证 | 结果 |
| --- | --- |
| `uv run pytest tests/contract -q` | `75 passed` |
| `uv run python -m py_compile src/docfit/template_generation/*.py src/docfit/template_gap/*.py src/docfit/stages/render/runner.py` | 通过 |
| `git diff --check` | 通过 |
| 湖南农大真实模板 `template-generate` | `PASS`，`verification_report.first_bad_stage = null` |
| 南农本科真实模板 `template-generate` | `PASS`，`verification_report.first_bad_stage = null` |
| 北大研究生真实模板 `template-generate` | `PASS`，`verification_report.first_bad_stage = null` |

三校 probe 输出位置在本地临时目录：

```text
/tmp/docfit_template_refactor_hunannongye
/tmp/docfit_template_refactor_nannong
/tmp/docfit_template_refactor_pku
```

## 尚未完成

| 未完成项 | 当前影响 | 下一步 |
| --- | --- | --- |
| 三校 `document_facts.gold.json` | T1 还不能做三校 gold 精确比较 | 逐校人工审核并提升 gold |
| `template_spec.gold.yaml` 及切片 expected | T2/T3/T4/T5 还不能按主 gold 精确比对 | 建主 gold，再派生 `unit_map.expected.yaml`、`element_spec.expected.yaml`、`global_spec.expected.yaml` |
| 边界 IoU 评分 | 单元边界质量目前主要靠 schema/required unit 门禁 | 实现 expected range 与 actual range 的 IoU verifier |
| AI 残余分类 | 当前主要是确定性规则，没有 AI trace 工作流 | 增加 AI input/output 落盘、schema validation、低置信 review gate |
| 人工 review queue | `review_flags` 有门禁方向，但没有完整审核记录流 | 增加 review queue artifact 和 gold promotion 规则 |
| generated Word field 构建 | `generated` 目前是可定位 SDT/字段占位证据 | 后续用低层 OOXML 生成 TOC/PAGE/SEQ |
| 渲染快照视觉门禁 | 还没有截图/页边界视觉比较 | 增加字段更新后的截图和页数、分页、关键区域比较 |
| 学校最终模板质量 PASS | 本轮只证明模板解析支撑链路可验证 | 继续用 `template-gap` 检查并修学校签收差距 |

## 建议下一批工作

1. 先为湖南农大建立 `template_spec.gold.yaml` 和 `document_facts.gold.json`，跑通 gold 提升与切片 expected。
2. 实现 T2 边界 IoU verifier，把现有 TG-GAP-001/TG-GAP-004 类型问题前移到 T2/T4。
3. 把 `generated` 从 SDT 占位升级为低层 OOXML 字段构建，优先覆盖 TOC/PAGE。
4. 增加 review queue artifact，让低置信元素和规则冲突不能进入自动 `PASS`。
5. 再跑三校 `template-gap`，按 `first_bad_stage` 把最终差距回归到 T1-T6 的具体阶段。
