# `docs/plans/` 命名约定

本目录放实施计划、阶段 issue 和优化方案。历史文件命名较乱，**新建文档统一加日期前缀**；旧文件不批量重命名。

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

非迭代类文档（总览、数据契约、一次性方案）可直接用语义化文件名，不必带 `-issue-` / `-plan-` 后缀。

其他主题同样加日期前缀，用语义化 kebab-case 即可。

索引类文件（本 README、`template-parse-refactor-issue-index.md`）不加日期前缀。

## 迭代链

若文档属于多轮 issue / plan 迭代，在 [`template-parse-refactor-issue-index.md`](./template-parse-refactor-issue-index.md) 补登记；不属于迭代链的文档无需登记。frontmatter 字段见该索引及 `AGENTS.md`。
