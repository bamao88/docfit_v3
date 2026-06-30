# `docs/plans/` 命名约定

本目录放实施计划、阶段 issue 和优化方案。历史文件命名较乱，**新建文档统一加日期前缀**；旧文件不批量重命名。

## 新建文件

文件名以创建日开头：

```text
YYYY-MM-DD-{name}.md
```

模板解析重构相关，优先：

```text
YYYY-MM-DD-template-parse-refactor-{stage}-{topic}-issue-{NN}-{short-name}.md   # 可选：多轮迭代中的问题记录
YYYY-MM-DD-template-parse-refactor-{stage}-{topic}-plan-{NN}-{short-name}.md    # 可选：实施方案 / 设计说明
```

文档层次和深度按主题自定，不强制 issue → plan 配对。`issue` / `plan` 只是迭代链里常用的命名后缀；单次方案、总览、数据契约等可直接用语义化文件名。

其他主题同样加日期前缀，用语义化 kebab-case 即可。

索引类文件（本 README、`template-parse-refactor-issue-index.md`）不加日期前缀。

## 迭代链

若文档属于多轮 issue / plan 迭代，在 [`template-parse-refactor-issue-index.md`](./template-parse-refactor-issue-index.md) 补登记；不属于迭代链的文档无需登记。frontmatter 字段见该索引及 `AGENTS.md`。
