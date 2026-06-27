# 契约和门禁规则

Last updated: 2026-06-27

一句话结论：当前只对模板阶段启用标准、检查器和 gate；学生内容提取、内容放置和 DOCX 渲染暂缓，不能用未定义流程制作标准。

## 三态判定

| 状态 | 什么时候用 | 能否通过 |
| --- | --- | --- |
| `PASS` | 标准存在、检查器存在、覆盖足够、证据证明产物满足 contract | 能 |
| `FAIL` | 标准明确、检查器能运行、证据证明产物违反 contract | 不能 |
| `UNKNOWN` | 缺标准、缺字段、缺证据、缺检查器、覆盖不足或输入不可支持 | 不能 |

禁止把 `FAIL` 或 `UNKNOWN` 降成 `WARN` 来通过 gate。

## 当前启用范围

| 范围 | 状态 | 说明 |
| --- | --- | --- |
| 模板生成 T1-T5 | active | 标准已拆为 `t1_document_facts` 到 `t5_template_spec`，后续由标准裁判读取 |
| 可填写模板构建 / T6 | active | 输出 `fillable_template.docx`、`build_manifest.json`，由内置 verifier 和 gap 检查 |
| 模板 gap | active | 对照 `template_quality/final_template.expected.yaml` 检查被测模板 |
| 学生内容提取 | deferred | 流程、阶段产物和签收标准尚未定义清楚 |
| 内容放置 | deferred | 依赖学生内容提取结果，当前不制作标准 |
| DOCX 渲染 | deferred | 依赖放置计划，当前不制作标准 |

deferred 范围里的 historical fixture 或 expected 文件不能作为当前 gate 依据；它们只能作为后续设计时的参考材料。

## 长期产品阶段契约草图

| 阶段 | 主要产物 | 必须证明什么 | 常见阻断 |
| --- | --- | --- | --- |
| 模板解析 | `template_artifact.json` | 系统正确理解学校模板结构、样式、区域和可填写位置 | required unit 缺失、样式/字段/分页不符、检查器证据不足 |
| 内容提取 | `student_content_artifact.json` | 用户可见内容完整进入 ledger | 可见内容缺 `content_id`、unsupported 可见对象未登记 |
| 内容放置 | `placement_plan.json` | 每个可见内容有且只有一个明确去向 | silent drop、slot 不存在、学校特例未登记 |
| DOCX 渲染 | `final.docx`、`render_manifest.json`、`feature_snapshot.json` | renderer 忠实执行 placement plan | action 未执行、feature diff 阻断、oracle 不足 |

## 模板侧支撑检查

上表后三个非模板阶段是长期产品草图，不是当前验收对象。等学生内容提取流程、内容 ledger、放置计划和渲染 manifest 的真实语义明确后，才能制作对应标准。

| 支撑流程 | 主要产物 | 能证明什么 | 不能证明什么 |
| --- | --- | --- | --- |
| 模板解析/可填模板生成 | `document_facts.json`、`template_spec.yaml`、`fillable_template.docx`、`build_manifest.json`、`verification_report.json` | 源模板事实、单元/元素/全局规则、构建动作和成品 Word 可追溯 | 不能替代学校签收标准下的最终格式验收 |
| generated-template gap | `generated_template_tree.json`、`template_gap_report.*` | 被测生成模板和学校签收标准之间的差距 | 不能证明学生内容提取、放置或最终论文渲染正确 |

## 产物不能互相冒充

| 产物 | 能证明什么 | 不能证明什么 |
| --- | --- | --- |
| `document_facts.json` | 学校源 Word 里实际解析到什么 | 不能承载单元/元素策略判断 |
| `template_spec.yaml` | 系统如何理解学校源模板的单元、元素、策略和全局规则 | 不能替代 `fillable_template.docx` 的真实结构证据 |
| `build_manifest.json` | 构建器执行了什么，输出 Word hash 是什么 | 不能单独证明 Word 里最终真的存在对应内容 |
| `template_artifact.json` | 四阶段旧接口需要的包装视图 | 不能拥有独立于 `template_spec.yaml` 的模板语义 |
| `generated_template_tree.json` | 被测生成 Word 实际解析出了什么 | 不能替代学校签收标准 |
| `template_gap_report.json` | 检查器如何判定差距和阻断状态 | 不能反过来当标准，不能被 AI 改成通过 |

正确链路：

```text
template_spec 记录模板理解
build_manifest 记录构建动作
generated_template_tree 记录可填模板真实 Word 事实
template_gap_report 用签收标准检查真实 Word 事实
```

错误链路：

```text
build_manifest 说生成了标题 -> 直接判定标题存在
```

## 字段变更规则

新增、修改、删除 JSON 字段前，必须先说明：

| 必须说明 | 目的 |
| --- | --- |
| 字段含义 | 避免同名字段承载多个业务概念 |
| 生产者 | 确认唯一写入责任 |
| 消费者 | 确认字段不是无人使用的噪音 |
| 是否参与判定 | 明确是否影响 `PASS` / `FAIL` / `UNKNOWN` |
| 缺失时结果 | 缺字段时判 `FAIL`、`UNKNOWN`、`needs_review` 还是不阻断 |
| 默认值规则 | 防止靠猜默认值掩盖不确定 |
| AI 是否可改 | 防止 AI 修改标准、证据或状态 |
| 证据和测试要求 | 确保字段能被验证和回归 |

没有消费者的字段先不要加。有消费者的字段必须定义缺失后果。

## AI 边界

AI 可以总结 findings、建议根因方向、建议通用修复和测试、帮助改人读说明。

AI 禁止裁定最终状态、修改检查状态或 evidence 让报告通过、自动更新标准/golden/expected、忽略 silent drop 或 unsupported 可见对象。
