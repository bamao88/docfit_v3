# `docs/status/` 维护规则

本目录是 DocFit 当前变化、缺陷、影响范围和闭环状态的唯一事实源。它适用于模板生成、学生论文内容提取、内容匹配与放置、最终 Word 渲染以及跨阶段问题。

## 什么时候进入这里

发现以下事项时，先更新状态记录，再决定是否需要 issue 或 plan：

- 阶段输入、输出、字段或语义发生变化；
- 上下游仍使用旧字段、旧分类或旧行为；
- 代码与 `docs/current/` 的当前契约不一致；
- 实现 bug、评测维度错误、假绿、假红或错误归因；
- 已有实现但真实样本、反例、裁判或残留尚未闭环；
- 实施中发现超出原 plan 范围的新影响。

## 目录职责

```text
docs/status/
├── README.md       # 本规则
├── INDEX.md        # 所有当前状态的统一入口
├── active/         # 尚未 verified/closed 的状态项
└── closed/         # 已 verified/closed 或被替代的状态项
```

`active/` 不能存放 `DONE`、`COMPLETE` 或已经 verified 的记录。完成后移动到 `closed/`，并同步 `INDEX.md`。

## 状态项最少回答什么

每个状态项必须说明：

- 发生了什么，以及 expected 与 observed；
- 什么时候发现、属于哪个业务阶段；
- 影响哪些上游、下游、产物、标准、测试和报告；
- 是否已有对应 issue/plan；
- 修改是否已实施；
- 用什么证据验证，仍有什么残留。

详细实施步骤不写在 status 中；它们属于 `docs/plans/`。长期有效的阶段契约和测试规则不写在 status 中；它们属于 `docs/current/`。

## 统一状态

```text
discovered
impact_confirmed
planned
implementing
implemented
verified
closed
blocked
superseded
wont_fix
```

`implemented` 只表示修改已经落地，不等于质量闭环。完成约定的测试、真实样本、反例、裁判和残留检查后，才能进入 `verified` 或 `closed`。

旧 capsule 暂时允许保留原字段，后续更新时逐步对齐统一状态；不要为了格式统一而丢失已有证据。

## 与 current、issue 和 plan 的关系

```text
current 契约
  -> 发现变化或缺陷
  -> status 记录影响与闭环
  -> issue 记录问题事实（需要独立问题文档时）
  -> plan 记录具体修改方案
  -> 实施与验证
  -> 更新 current
  -> 关闭 status
```

- `docs/current/`：系统现在应该怎样工作、怎样验证。
- `docs/status/`：现在发生了什么、影响哪里、是否闭环。
- `docs/plans/`：具体怎样修改。

同一问题不能同时在 open-gaps、progress、capsule、plan index 和根 `STATUS.md` 中维护多份当前状态。迁移期以本目录 `INDEX.md` 为当前状态入口，其他文件只保留历史或兼容说明。
