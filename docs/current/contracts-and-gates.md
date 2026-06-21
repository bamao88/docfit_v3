# 契约和门禁规则

Last updated: 2026-06-21

一句话结论：DocFit 只能由确定性证据决定 `PASS` / `FAIL` / `UNKNOWN`；AI 可以解释和建议，不能裁判。

## 三态判定

| 状态 | 什么时候用 | 能否通过 |
| --- | --- | --- |
| `PASS` | 标准存在、检查器存在、覆盖足够、证据证明产物满足 contract | 能 |
| `FAIL` | 标准明确、检查器能运行、证据证明产物违反 contract | 不能 |
| `UNKNOWN` | 缺标准、缺字段、缺证据、缺检查器、覆盖不足或输入不可支持 | 不能 |

禁止把 `FAIL` 或 `UNKNOWN` 降成 `WARN` 来通过 gate。

## 阶段契约

| 阶段 | 主要产物 | 必须证明什么 | 常见阻断 |
| --- | --- | --- | --- |
| 模板生成 | `generated_template.docx`、`template_generation_manifest.json` | 生成阶段产物链完整、输出 Word hash 固定、过程可追溯 | 源模板缺失/无效、manifest 缺 hash、动作不可解释 |
| 模板侧 gate | `template_artifact.json`、`generated_template_tree.json`、`template_gap_report.*` | 模板或生成模板满足学校签收标准 | required unit 缺失、样式/字段/分页不符、检查器证据不足 |
| 内容提取 | `student_content_artifact.json` | 用户可见内容完整进入 ledger | 可见内容缺 `content_id`、unsupported 可见对象未登记 |
| 内容放置 | `placement_plan.json` | 每个可见内容有且只有一个明确去向 | silent drop、slot 不存在、学校特例未登记 |
| DOCX 渲染 | `final.docx`、`render_manifest.json`、`feature_snapshot.json` | renderer 忠实执行 placement plan | action 未执行、feature diff 阻断、oracle 不足 |

## 产物不能互相冒充

| 产物 | 能证明什么 | 不能证明什么 |
| --- | --- | --- |
| `template_generation_manifest.json` | 生成器尝试做了什么，输出 Word hash 是什么 | 不能证明 Word 里最终真的存在对应内容 |
| `template_artifact.json` | 系统如何理解学校源模板 | 不能替代 `generated_template.docx` 的真实结构证据 |
| `generated_template_tree.json` | 被测生成 Word 实际解析出了什么 | 不能替代学校签收标准 |
| `template_gap_report.json` | 检查器如何判定差距和阻断状态 | 不能反过来当标准，不能被 AI 改成通过 |

正确链路：

```text
manifest 记录生成动作
generated_template_tree 记录真实 Word 事实
template_gap_report 用签收标准检查真实 Word 事实
```

错误链路：

```text
manifest 说生成了标题 -> 直接判定标题存在
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
