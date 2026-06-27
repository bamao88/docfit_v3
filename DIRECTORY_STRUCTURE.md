# DocFit 目录入口

一句话结论：完整目录结构规则已经合并到
`docs/current/project-directory-structure.md`；这个文件只保留根目录短入口，避免两份目录表同时维护。
历史文档里出现的旧路径按该文档的历史路径对照表理解，不作为当前新增文件规则。

## 该看哪里

| 你要判断什么 | 看哪里 |
| --- | --- |
| 新增输入、输出、标准、测试或文档应该放哪 | `docs/current/project-directory-structure.md` |
| 当前项目文档从哪里开始读 | `docs/current/README.md` |
| 模板生成阶段的输入、输出、字段和 gap 检查 | `docs/current/template-generation.md` |

## 维护规则

- 修改目录放置规则时，只改 `docs/current/project-directory-structure.md`。
- 本文件可以保留入口链接，但不要新增目录判断表、debug/eval 输出细则或标准边界正文。
- 不在本文件维护第二份目录树；如果需要新增规则，去改唯一权威正文。
- README、AGENTS 或人工操作可以继续从这个根目录短入口跳到完整正文。
