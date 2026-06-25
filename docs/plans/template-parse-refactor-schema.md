# 模板解析 artifact schema

Last updated: 2026-06-25

一句话结论：`document_facts.json` 是唯一事实库，`template_spec.yaml` 是模板解析阶段主产物；其他产物只引用事实 id/range，不复制 Word 事实。

## 通用字段

| 字段 | 含义 | 生产者 | 消费者 | 缺失后果 | AI 可改 |
| --- | --- | --- | --- | --- | --- |
| `artifact_type` | 产物类型闭集 | 对应阶段 | 写出器、verifier、报告 | `UNKNOWN` | 否 |
| `artifact_version` | schema 版本 | 对应阶段 | verifier | `UNKNOWN` | 否 |
| `producer.name/version` | 生产代码身份 | 对应阶段 | 审计、报告 | `UNKNOWN` | 否 |
| `created_at` | 生产时间 | 对应阶段 | 审计 | 不单独阻断 | 否 |
| `input_hashes` | 上游文件或 artifact hash | 对应阶段 | verifier、聚合报告 | `UNKNOWN` | 否 |
| `flags[]` | 不确定项或待审项 | 对应阶段 | verifier、review queue | flag 未处理为 `UNKNOWN` | AI 可建议，不能直接清除 |

## `document_facts.json`

生产者：T1 Word inspector。

消费者：T2 unit mapper、T3 element classifier、T4 global spec builder、T6 builder、T1 verifier。

关键字段：

| 字段 | 含义 | 缺失后果 | AI 可改 |
| --- | --- | --- | --- |
| `metadata.source_template_docx/hash` | 源模板路径和 hash | `UNKNOWN` | 否 |
| `body_flow[].paragraph_id` | 正文段落稳定 id | `FAIL` | 否 |
| `body_flow[].table_id/cell_id` | 表格/单元格稳定 id | 表格事实不可追溯，`FAIL` | 否 |
| `body_flow[].raw_run_ids[]` | 源 run 稳定 id | T6 不能 run 级施工，`UNKNOWN` | 否 |
| `body_flow[].logical_run_ids[]` | 合并后的逻辑 run id | 后续元素不能引用，`FAIL` | 否 |
| `runs[].raw_run_id` | 源 run id | `FAIL` | 否 |
| `runs[].logical_run_id` | 逻辑 run id | `FAIL` | 否 |
| `runs[].merged_from[]` | 逻辑 run 来源 | `UNKNOWN` | 否 |
| `runs[].text/kind` | 可见文本和对象类别 | `FAIL` | 否 |
| `runs[].effective_style` | 最终样式 | 样式 verifier 为 `UNKNOWN` | 否 |
| `runs[].style_provenance` | 样式来源层级 | 样式 verifier 为 `UNKNOWN` | 否 |
| `sections[]` | 分节、纸张、页边距、页眉页脚引用 | 页面规则为 `UNKNOWN` | 否 |
| `fields[]` | PAGE/TOC/SEQ 等 Word field | generated 判断为 `UNKNOWN` | 否 |
| `unknown_objects[]` | 可见但未建模对象 | 非空时 T1 不能 `PASS` | 否 |

## `unit_map.yaml`

生产者：T2 deterministic unit mapper。

消费者：T3 element classifier、T5 template spec merger、T2 verifier。

字段：

| 字段 | 含义 | 缺失后果 | AI 可改 |
| --- | --- | --- | --- |
| `units[].unit_id` | 单元闭集 id | `FAIL` | 否 |
| `units[].source_range` | 引用 `document_facts` 的开始/结束 id | `FAIL` | 否 |
| `units[].order` | 模板内顺序 | `FAIL` | 否 |
| `units[].page_start` | 分页/分节开始规则，或 `UNKNOWN` | 缺失为 `UNKNOWN` | 否 |
| `units[].section_profile` | 关联的 section profile id | 页面规则为 `UNKNOWN` | 否 |
| `units[].confidence` | deterministic 置信度 | 低置信未审为 `UNKNOWN` | AI 可建议，不能直接改 |
| `units[].flags[]` | 边界/顺序/证据不足 | 未处理为 `UNKNOWN` | AI 可建议，不能清除 |

## `element_spec.yaml`

生产者：T3 deterministic classifier，可附 AI 残余分类记录。

消费者：T5 template spec merger、T6 builder、T3 verifier。

字段：

| 字段 | 含义 | 缺失后果 | AI 可改 |
| --- | --- | --- | --- |
| `elements[].element_id` | 元素稳定 id | `FAIL` | 否 |
| `elements[].unit_id` | 所属单元 | `FAIL` | 否 |
| `elements[].source_refs[]` | `document_facts` id/range 引用 | `FAIL` | 否 |
| `elements[].policy` | `fixed/template_default/fill/manual_only/generated/instruction_remove` | `FAIL` | AI 只可建议残余，不能裁定 |
| `elements[].role` | 闭集角色 | `UNKNOWN` | AI 可建议 |
| `elements[].fill_source` | 学生内容、metadata、manual、generated field 等来源 | `fill` 缺失为 `FAIL` | AI 不可补造 |
| `elements[].generated.field_type` | TOC/PAGE/SEQ 等 | `generated` 缺失为 `FAIL` | 否 |
| `elements[].evidence[]` | 规则证据和 source ids | `UNKNOWN` | 否 |
| `elements[].confidence` | 分类置信度 | 低置信未审为 `UNKNOWN` | AI 可建议 |
| `elements[].ai_trace` | AI 输入、输出、模型、temperature、schema validation | AI 参与但缺失为 `UNKNOWN` | 否 |

## `global_spec.yaml`

生产者：T4 deterministic global rule builder。

消费者：T5 template spec merger、T6 builder、T4 verifier。

字段：

| 字段 | 含义 | 缺失后果 | AI 可改 |
| --- | --- | --- | --- |
| `section_profiles[]` | 纸张、页边距、页眉页脚、页码配置 | 页面构建为 `UNKNOWN` | 否 |
| `default_font` | 默认中西文字体、字号 | 样式 verifier 为 `UNKNOWN` | 否 |
| `page_numbering` | 页码体例 | 页码 verifier 为 `UNKNOWN` | 否 |
| `header_footer` | 页眉页脚规则 | 页眉页脚 verifier 为 `UNKNOWN` | 否 |
| `numbering_rules` | 标题/图表/公式编号规则 | 编号 verifier 为 `UNKNOWN` | 否 |
| `flags[]` | 证据不足或冲突 | 未处理为 `UNKNOWN` | AI 可建议 |

## `template_spec.yaml`

生产者：T5 merger。

消费者：T6 builder、template-gap、placement/render 后续接口、T5 verifier。

字段：

| 字段 | 含义 | 缺失后果 | AI 可改 |
| --- | --- | --- | --- |
| `document_facts_ref` | 唯一事实库引用和 hash | `UNKNOWN` | 否 |
| `units[]` | 合并后的单元、元素和策略 | `FAIL` | 否 |
| `global` | 全局页面/样式/编号规则 | `UNKNOWN` | 否 |
| `review_flags[]` | 未解决审核项 | 非空时不能进入 T6 自动 `PASS` | AI 不能清除 |
| `review_decisions[]` | 人工审核记录 | 低置信或冲突项缺记录为 `UNKNOWN` | 否 |

`template_artifact.json` 若继续存在，只能是 `template_spec.yaml` 的四阶段包装视图：供旧 placement/render 接口读取，不拥有独立模板语义。

## `build_manifest.json`

生产者：T6 builder。

消费者：T6 verifier、报告、人工排查。

字段：

| 字段 | 含义 | 缺失后果 | AI 可改 |
| --- | --- | --- | --- |
| `output.fillable_template_docx/hash` | 成品路径和 hash | `FAIL` | 否 |
| `actions[]` | 每个构建动作 | `FAIL` | 否 |
| `actions[].element_id/unit_id` | 动作归属 | `FAIL` | 否 |
| `actions[].source_refs/raw_run_ids` | 源事实定位 | `UNKNOWN` | 否 |
| `actions[].output_ref` | 输出 OOXML 定位 | `UNKNOWN` | 否 |
| `actions[].status` | `executed/needs_review/skipped` | `needs_review` 阻断 `PASS` | 否 |

成品 Word 必须用 SDT 内容控件承载 `fill/manual_only`，tag 为 `element_id` 或 `unit_id.element_id`，不得包含内部 `[[DOCFIT_*]]` 文本 marker。
