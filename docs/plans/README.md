# `docs/plans/` 实施计划维护规则

本目录放问题事实、实施计划和历史优化方案。当前变化、缺陷、影响范围和闭环状态统一由 `docs/status/` 管理；本目录不再承担全局状态看板职责。历史文件命名较乱，**新建文档统一加日期前缀**；旧文件不批量重命名。

进入本目录前先检查：

- `docs/current/README.md`：当前系统或阶段契约的事实源；
- `docs/status/README.md` 和 `docs/status/INDEX.md`：问题是否已经登记、影响哪些阶段、当前是否闭环；
- 本 README：是否需要独立 issue/plan，以及具体文档怎样维护。

关系是：status 追踪影响与闭环，issue 记录问题事实，plan 承载具体执行契约。不要用 plan index、progress 文档或最终回复代替 status。

## 新建文件

文件名以创建日开头：

```text
YYYY-MM-DD-{name}.md
```

模板解析重构相关，优先：

```text
YYYY-MM-DD-template-parse-refactor-{stage}-{topic}-issue-{NN}-{short-name}.md   # 问题记录（只写问题，不写解法）
YYYY-MM-DD-template-parse-refactor-{stage}-{topic}-plan-{NN}-{short-name}.md    # 解决计划（必须标明 source_issue）
```

## Issue 与 Plan 分离（硬约束）

| 文档类型 | 写什么 | 不写什么 |
| --- | --- | --- |
| **issue** | expected vs observed、疑似根因、上一轮已解决/未解决、验收门禁 | 实施步骤、代码改动方案、任务拆解 |
| **plan** | 针对哪个 issue（`source_issue`）、怎么修、实施顺序、完成信号 | 重复堆砌 issue 全文；应链接 issue 而非复制 |

一轮迭代通常 **issue NN → plan NN** 配对，但必须是两个文件。小范围 hotfix 可跳过 plan（issue 的 `next_plan` 写 `skipped` 并说明原因）。

## 执行契约（Plan 必须承载）

Plan 是同一轮工作的唯一执行契约。不要为同一个 issue/plan 再创建第二份 `execution plan`、`执行计划`、`task breakdown` 或类似文档；如果 plan 太上层，应该直接更新原 plan，而不是另起事实源。

每个进入实施的 plan 应包含以下章节或等价内容：

```markdown
## Execution Contract

### Target Capability

本计划完成后，系统必须具备什么能力。

### Non-Goals

本轮明确不解决什么，避免范围漂移。

### Completion Signals

必须同时满足的完成信号，例如代码路径、artifact、真实样本、反例、残留扫描、裁判报告和 route-eval。

### Anti-Degradation Rules

禁止用单个 fixture、artifact 存在、PASS/SIGNABLE、某次 replay 成功或只传字段但下游不消费来替代完成。

### Verification Matrix

| Gate | Command / Evidence | Required Result |
| --- | --- | --- |
| unit | ... | ... |
| contract | ... | ... |
| real sample | ... | ... |
| residual scan | ... | ... |
| judge / route-eval | ... | ... |

### Residual Policy

未完成能力必须明确标成 `implemented_in_part`、`blocked_by`、`remaining_gap` 或创建下一轮 issue/plan。
```

如果实施过程中发现 plan 缺少细节，只允许做以下两类动作：

- **补原 plan**：在原 plan 中补 `Execution Contract`、`Implementation Checklist`、验收矩阵或残留处理。
- **开新 issue/plan**：当目标、范围或根因发生实质变化时，创建下一轮 issue/plan，并在索引里串起链路。

禁止把新写的执行文档作为事实源绕过原 plan。

## 状态与 Git 追踪

这里的状态描述单个 issue/plan 的执行状态；项目当前问题和跨阶段影响仍以 `docs/status/INDEX.md` 为入口。issue/plan 状态变化时，应同步关联状态项，避免出现 plan 已完成但影响未验证，或状态已关闭但 plan 仍显示 implementing。

推荐状态：

```text
draft
approved
implementing
implemented_in_part
verified
closed
superseded
```

状态含义：

- `draft`：问题或计划仍在整理，不能作为执行完成依据。
- `approved`：plan 已确认，可进入实施。
- `implementing`：正在实施。
- `implemented_in_part`：已有代码或文档落地，但真实样本、反例、裁判或残留门禁尚未闭环。
- `verified`：完成信号全部满足，包含真实样本和必要裁判证据。
- `closed`：issue 的 expected vs observed 已经消失，索引和关联 plan 均已更新。
- `superseded`：被后续 issue/plan 替代。

提交建议按以下顺序维护：

```text
1. 创建/更新 issue
2. 创建/批准 plan
3. 提交文档基线
4. 实施代码
5. 跑验证
6. 更新 plan / issue index 状态和残留
7. 提交实现与追踪更新
```

commit message 或正文应能追溯对应 issue/plan，并记录关键验证证据。示例：

```text
feat: add full template generation route eval

Issue: T2T3T4-AGENT-ISSUE-08
Plan: T1L1-INPUT-CONTRACT-PLAN-08
Verified:
- uv run pytest -q
- hunannongye real template-generate
- template-generation-judge route eval
Residual:
- T5/T6 ai_raw replay not materialized
```

非迭代类文档（总览、数据契约、一次性方案）可直接用语义化文件名，不必带 `-issue-` / `-plan-` 后缀。

其他主题同样加日期前缀，用语义化 kebab-case 即可。

索引类文件（本 README、`template-parse-refactor-issue-index.md`）不加日期前缀。`template-parse-refactor-issue-index.md` 只保存模板解析历史迭代链，不作为当前状态总入口。

## 迭代链

若文档属于多轮 issue / plan 迭代，在 [`template-parse-refactor-issue-index.md`](./template-parse-refactor-issue-index.md) 补登记；不属于迭代链的文档无需登记。frontmatter 字段见该索引及 `AGENTS.md`。
