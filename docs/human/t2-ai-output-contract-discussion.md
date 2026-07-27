# T2 AI 页面单元输出契约（讨论稿）

> Status: accepted contract; runtime implemented, school page-gold validation pending  
> Updated: 2026-07-25  
> Plan source: [`../plans/2026-07-24-template-parse-refactor-t2-page-exclusive-units-plan-12-exclusive-contiguous-page-contract.md`](../plans/2026-07-24-template-parse-refactor-t2-page-exclusive-units-plan-12-exclusive-contiguous-page-contract.md)  
> Related prompt: [`t2-ai-prompt-draft.md`](t2-ai-prompt-draft.md)  
> Runtime source: `src/docfit/template_generation/t2_ai.py`

## 1. T2 单元

一个 T2 单元拥有一段独占的连续渲染页面。

- 页面是最小切分对象；
- 一个单元可以包含一页或连续多页；
- 一页只能属于一个单元；
- 每一页都必须有归属；
- 下一个单元从下一页开始。

T2 AI 只需要回答：

```text
第几页到第几页是什么单元？
```

## 2. AI 原始输出

```json
{
  "units": [
    {
      "unit_id": "cover_and_title_information",
      "unit_name": "封面及题名信息",
      "boundary": {
        "start_page": 1,
        "end_page": 2
      }
    },
    {
      "unit_id": "body_main",
      "unit_name": "正文",
      "boundary": {
        "start_page": 3,
        "end_page": 18
      }
    }
  ]
}
```

AI 每个单元只输出三个字段：

1. `unit_id`；
2. `unit_name`；
3. `boundary`。

分页策略、source 绑定、证据和诊断信息不属于 AI 原始输出。

## 3. 字段定义

### 3.1 `units`

- 类型：数组；
- 是否必填：是；
- 含义：按页面顺序排列的全部 T2 单元；
- 顺序：必须与真实渲染页顺序一致；
- 覆盖：必须完整覆盖从第一页到最后一页。

### 3.2 `unit_id`

- 类型：字符串；
- 是否必填：是；
- 含义：页面组的机器可读语义 ID；
- 格式：小写英文 `snake_case`；
- 取值范围：开放，不使用穷举白名单；
- 唯一性：同一份文档内必须唯一；
- 常见单元：优先使用稳定通用 ID；
- 学校特有单元：根据实际功能生成新的 ID；
- 无法判断：使用 `unknown_unit`，但不能因此丢失页面。

以下只是示例，不是允许值全集：

- `cover`：封面；
- `cover_and_title_information`：封面及题名信息；
- `toc`：目录；
- `abstract_cn`：中文摘要；
- `body_main`：正文；
- `references`：参考文献；
- `graduation_process_and_review_forms`：毕业论文过程与评审表格；
- `unknown_unit`：页面范围明确但语义无法可靠判断。

### 3.3 `unit_name`

- 类型：字符串；
- 是否必填：是；
- 含义：页面组给人阅读的名称；
- 有明确总标题：优先使用文档中的实际标题；
- 有多个标题但属于一个功能整体：概括共同用途；
- 没有明确总标题：根据页面内容生成简洁、准确的功能名称；
- 命名范围：必须覆盖整个页面组，不能只描述其中一个局部标题。

例如，连续页面中包含任务安排、过程记录、答辩记录和成绩评定等多张表格，并共同组成一套毕业论文过程材料时，可以输出：

```json
{
  "unit_id": "graduation_process_and_review_forms",
  "unit_name": "毕业论文过程与评审表格"
}
```

### 3.4 `boundary`

`boundary` 只包含：

```json
{
  "start_page": 20,
  "end_page": 28
}
```

#### `start_page`

- 类型：整数；
- 是否必填：是；
- 含义：单元包含的第一页；
- 坐标：1-based 真实渲染页码；
- 包含关系：开始页属于当前单元。

#### `end_page`

- 类型：整数；
- 是否必填：是；
- 含义：单元包含的最后一页；
- 坐标：1-based 真实渲染页码；
- 包含关系：结束页属于当前单元。

## 4. T2 输入

MiniMax 按页面顺序接收：

```text
T2 任务说明
→ 第 1 页图片
→ 第 1 页客观事实
→ 第 2 页图片
→ 第 2 页客观事实
→ ...
→ 输出 schema
```

每页可以提供：

- `page_no/page_ref`；
- 页面图片及其 hash、宽高；
- 本页可见 body 节点的 `source_seq/source_ref/text/kind`；
- 节点在页内的 bbox 或阅读顺序；
- 真实 page break 或 section break 的机械事实；
- render completeness；
- 无法绑定的对象。

输入只包含客观事实，不包含预判的单元名称、边界、分页策略、code route、gold 或 judge 结论。

页面是权威坐标，因此 T2 运行前必须有可用的真实渲染页、页图和页面绑定。

## 5. 页面边界不变量

设真实渲染页数为 `N`，排序后的单元为 `u1...uk`：

1. `u1.start_page = 1`；
2. `uk.end_page = N`；
3. 每个单元满足 `1 <= start_page <= end_page <= N`；
4. 相邻单元满足 `u(i+1).start_page = ui.end_page + 1`；
5. 每一页恰好属于一个单元；
6. 单元数组顺序就是页面顺序；
7. 无法判断语义的页面仍必须归入某个连续范围。

以下输出不能进入 T2 final：

- 页码越界；
- 页面 gap；
- 页面 overlap；
- 单元顺序错误；
- 缺失第一页或最后一页；
- 同一 `unit_id` 重复；
- AI 输出 schema 之外的字段；
- 真实渲染页、页图或页面绑定不可用。

## 6. 程序生成正式 T2 final

AI 页面区间通过校验后，程序负责：

```text
page range
  → 展开 page_refs
  → 读取每页 body binding
  → 生成 source_seq_refs/source_refs
  → 生成 source_seq_range
  → 生成固定 page_policy
  → 发布 T2 final
```

正式 `unit_map` 中的分页策略由程序确定：

| 单元位置 | `page_policy.start` | `page_policy.scope` |
| --- | --- | --- |
| 第一个单元 | `document_start` | `page_range_exclusive` |
| 后续任意单元 | `new_page` | `page_range_exclusive` |

`page_range_exclusive` 表示单元拥有自己的连续页面范围，不表示这个单元必须永久保持当前页数，也不要求单页单元整体 keep-together。

规范化后的单元示例：

```json
{
  "unit_id": "body_main",
  "unit_name": "正文",
  "boundary": {
    "start_page": 3,
    "end_page": 18
  },
  "page_policy": {
    "start": "new_page",
    "scope": "page_range_exclusive"
  },
  "page_refs": [],
  "source_seq_refs": [],
  "source_refs": []
}
```

这里除 `unit_id`、`unit_name` 和页面边界外，其余字段均由程序生成。

## 7. 页面到 L1 的映射

- 页眉、页脚和重复页码不进入 body `source_seq_refs`；
- 空白页保留页面所有权，但不伪造 source 节点；
- 同一个 body 节点跨越同一单元的多页时去重；
- 同一个 body 节点跨越两个候选单元时拒绝发布或进入人工复核；
- 页面绑定不完整时不能用相邻文本猜测。

## 8. 下游消费

```text
按页组织的 sealed T1 facts
  → MiniMax T2 页面分组
  → AI raw：unit_id + unit_name + page boundary
  → 页面完整覆盖校验
  → page range 映射为 source bindings
  → 程序生成固定 page_policy
  → canonical unit_map
  → T3/T5/T6
```

T3 在 T2 页面窗口内部继续识别标题、表单块、说明和字段。T5 无损传递页面范围。T6 负责让每个非首单元实际另起页。
