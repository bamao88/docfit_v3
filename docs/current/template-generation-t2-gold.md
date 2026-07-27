# T2 页面单元标准

> 迁移状态：T2 的测试入口、指标和完成门禁统一维护在
> [`template-generation-testing.md`](template-generation-testing.md) 的 T2 章节。
> 本文只保留 T2 gold 的业务口径，避免把运行路线或实现细节写进学校标准。

一句话结论：T2 gold 以真实渲染页为坐标，签收“哪些连续页面属于哪个顶层单元”；它不签收 T3 元素策略、T4 全局版式、T6 Word 动作或最终学校质量。

## 1. 标准位置

每个学校目标的 T2 标准位于：

```text
standards/targets/<target_id>/v1/template_generation/t2_unit_pagination.standard.yaml
```

它是人工审核真实模板渲染结果后形成的阶段标准，不是某次模型输出，也不能作为 T2 AI 输入。

T2 运行时只有一份 AI 判断和一份正式结果：

| 产物 | 含义 |
| --- | --- |
| `02.1_t2_input.json` | 按页组织的客观输入审计；每页图像后跟该页事实 |
| `02.2_t2_ai_unit_observation.yaml` | AI 原始页面分组，只含 ID、名称和页面边界 |
| `02_unit_map.yaml` | 通过完整覆盖校验并完成 L1 绑定后的唯一 T2 final |

不存在 T2 code、comparison、overlay 或 merged 业务路线。AI 不可用、真实渲染不可用或输出不满足页面不变量时，T2 明确失败，不发布代码兜底结果。

## 2. T2 gold 回答什么

T2 gold 只回答四件事：

1. 页面组的 `unit_id`；
2. 页面组的 `unit_name`；
3. 页面组包含的 `start_page`；
4. 页面组包含的 `end_page`。

最小示例：

```yaml
expected:
  unit_order:
    - cover_and_title_information
    - toc
    - body_main
  units:
    - unit_id: cover_and_title_information
      unit_name: 封面及题名信息
      boundary:
        start_page: 1
        end_page: 2
    - unit_id: toc
      unit_name: 目录
      boundary:
        start_page: 3
        end_page: 4
    - unit_id: body_main
      unit_name: 正文
      boundary:
        start_page: 5
        end_page: 18
```

`unit_id` 是开放的机器可读名称，使用小写英文 `snake_case`。常见 ID 只是示例，学校特有页面组可以按实际功能生成新 ID，不能维护一份封闭枚举。

`unit_name` 是人可读名称。有明确总标题时优先使用模板原文；多个标题共同组成一套功能材料时，应概括整个页面组，而不是只取其中一个局部标题。

## 3. 页面不变量

设真实渲染共有 `N` 页，按顺序输出 `u1...uk`：

1. `u1.start_page = 1`；
2. `uk.end_page = N`；
3. 每个单元满足 `1 <= start_page <= end_page <= N`；
4. 相邻单元满足 `u(i+1).start_page = ui.end_page + 1`；
5. 每一页恰好属于一个单元；
6. 单元数组顺序就是页面顺序；
7. 空白页也必须有页面所有权；
8. 语义无法可靠判断时可以使用 `unknown_unit`，但不能漏页。

任何页面 gap、overlap、越界、顺序错误、重复 `unit_id` 或不完整真实渲染都会阻止 T2 final 发布。

## 4. 程序派生字段

AI 只输出 `unit_id`、`unit_name` 和 `boundary`。程序在校验后根据页面与 L1 的确定性绑定派生：

- `page_refs`；
- `source_seq_refs`；
- `source_refs`；
- `source_seq_range`；
- `order`；
- `page_policy`。

正式 `page_policy` 固定为：

| 单元位置 | `page_policy.start` | `page_policy.scope` |
| --- | --- | --- |
| 第一个单元 | `document_start` | `page_range_exclusive` |
| 后续任意单元 | `new_page` | `page_range_exclusive` |

`page_range_exclusive` 表示一个单元拥有自己的连续页面范围，不表示内容必须永久保持当前页数，也不触发“整单元必须压在一页”的约束。

## 5. T2 指标

T2 的主指标是：

- unit precision / recall / F1；
- unit order exact match；
- page boundary exact match；
- page ownership coverage；
- page gap / overlap count；
- unit ID / name mismatch。

页面到 `source_seq_refs/source_refs` 的映射准确性属于确定性 materializer 检查。固定 `page_policy` 属于契约测试，不作为 AI 准确率指标。

## 6. 不属于 T2 gold 的内容

- 段落、标题、表单和字段的 Keep/Fill/Delete，属于 T3；
- 页边距、页眉页脚、页码和编号体系，属于 T4；
- page break 或 section break 的具体执行动作，属于 T6；
- 最终 Word 是否符合学校要求，属于 POST_T6；
- 模型置信度、推理过程、代码路线或裁判结论。
