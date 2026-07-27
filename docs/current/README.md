# DocFit 当前文档入口

Last updated: 2026-07-22

本文是 `docs/current/` 的文档路由和收敛规则。它只回答：DocFit 包含哪些业务阶段，每个阶段的长期事实应写进哪份文档，以及现有文档将如何逐步归并。

具体启用范围和门禁以 [`contracts-and-gates.md`](./contracts-and-gates.md) 为准；具体目录规则以 [`project-directory-structure.md`](./project-directory-structure.md) 为准。

## 1. 业务阶段

DocFit 的产品流程按以下阶段理解：

```text
学校模板 -> 模板生成 ───────────────────────────────┐
                                                     ├-> 内容匹配与放置 -> 最终 Word 渲染 -> 端到端验收
学生论文 -> 学生论文内容提取 ───────────────────────┘

每个业务阶段 -> 本阶段测试与评测
```

| 范围 | 负责什么 | 不负责什么 |
| --- | --- | --- |
| 全系统 | 业务阶段、依赖关系、跨阶段数据流和共同边界 | 某一阶段内部实现 |
| 模板生成 | 理解学校模板并生成可填写模板及过程证据 | 提取具体学生论文内容 |
| 学生论文内容提取 | 把学生源 Word 转成可追踪的内容产物 | 决定内容进入哪个模板位置 |
| 内容匹配与放置 | 把学生内容映射到模板槽位或明确去向 | 直接修改最终 Word |
| 最终 Word 渲染 | 忠实执行放置计划并生成最终 Word 和执行证据 | 重新推断上游语义 |
| 测试与评测 | 检查整个系统和各阶段的输入、输出与质量 | 代替业务阶段修正数据 |

当前处理哪个阶段，以用户本轮目标为准。不要因为某个阶段文档较多，就默认它是本轮工作范围。

## 2. 目标文档

长期文档最终收敛为“全系统两份 + 每个业务阶段两份”：一份架构与数据契约，一份测试与评测契约。

| 范围 | 架构与数据契约 | 测试与评测契约 | 当前状态 |
| --- | --- | --- | --- |
| 全系统 | `system-architecture.md` | `system-testing.md` | 尚未创建；现有跨阶段内容暂见 `contracts-and-gates.md` 和本 README |
| 模板生成 | `template-generation-architecture.md` | `template-generation-testing.md` | 已建立，作为 canonical 长期事实源 |
| 学生论文内容提取 | `student-content-extraction-architecture.md` | `student-content-extraction-testing.md` | 尚未建立；共享字段契约不能代替阶段架构 |
| 内容匹配与放置 | `content-placement-architecture.md` | `content-placement-testing.md` | 尚未创建 |
| 最终 Word 渲染 | `document-rendering-architecture.md` | `document-rendering-testing.md` | 尚未创建 |

跨阶段共享契约独立于上述阶段文档：

| 文档 | 覆盖范围 | 职责 |
| --- | --- | --- |
| `content-field-and-slot-contract.md` | 内容提取、模板生成、内容放置、最终渲染 | 定义内容字段、内容节点、模板槽位、字段匹配和目标样式引用的责任边界 |

“尚未创建”表示名称和职责已经预留，但不能据此假定阶段契约已经定义。只有用户开始推进该阶段，并且事实源足够时，才创建正文。

### 架构与数据契约应包含什么

每份 `*-architecture.md` 维护该范围长期有效的：

- 目标、边界和非目标；
- 阶段划分、职责和依赖；
- canonical 输入、输出和数据流；
- 字段语义、生产者和消费者；
- 身份、引用、证据和不变量；
- 与上下游阶段的接口；
- 当前有效入口和公开产物。

它不维护 bug、待办、优化顺序、实施步骤、临时验证结果或某次运行进展。

### 测试与评测契约应包含什么

每份 `*-testing.md` 维护该范围长期有效的：

- 总体测试入口和各子阶段测试入口；
- isolated 与 cascade 输入；
- gold、标准和 fixture 的职责；
- 指标、判定规则和完成标准；
- verifier、judge、报告和证据结构；
- 反例、残留检查和端到端验收边界。

它不维护当前 bug、实现计划、短期缺口或一次性测试结果。

## 3. 现有文档迁移表

迁移期间，目标文档已经建立的范围只允许向目标文档新增长期事实。目标文档尚未建立时，表中标记为临时 canonical 的现有文档仍是事实源。其余旧文档不得继续扩展新的长期事实。

| 现有文档 | 对应范围 | 当前职责 | 迁移结论 |
| --- | --- | --- | --- |
| `contracts-and-gates.md` | 全系统 | 启用范围、三态判定、阶段边界和共同门禁 | 临时 canonical；后续稳定内容迁入 `system-architecture.md` 和 `system-testing.md` |
| `template-generation-architecture.md` | 模板生成 T1-T7 | 阶段职责、输入输出、身份、依赖和 route 契约 | canonical；后续模板生成架构变化只写这里 |
| `template-generation.md` | 模板生成 | 当前运行入口、公开产物、构建规则和运行验证 | 迁移中；稳定内容迁入 `template-generation-architecture.md`，不再新增事实 |
| `template-generation-stage-contracts.md` | 模板生成 T1-T7 | 旧文件名兼容指针 | 已淘汰；不再新增事实 |
| `template-generation-testing.md` | 模板生成及 T1-T7/POST_T6 | 整体和单阶段输入、gold、指标、CLI、报告与完成标准 | canonical；后续模板生成测试变化只写这里 |
| `template-generation-testing-framework.md` | 模板生成测试 | 旧文件名兼容指针 | 已淘汰；不再新增事实 |
| `template-generation-evaluation.md` | 模板生成评测 | 已实现评测结构、阶段检查和聚合规则 | 逐步淘汰；长期内容迁入 `template-generation-testing.md` |
| `template-generation-stage-standards.md` | 模板生成评测 | 阶段标准的准备、使用和 verify 区别 | 逐步淘汰；长期内容迁入 `template-generation-testing.md` |
| `template-generation-stage-standard-quality.md` | 模板生成评测 | 标准质量、调用和补全顺序 | 逐步淘汰；契约迁入 `template-generation-testing.md`，补全工作迁入 status/plan |
| `template-generation-t2-gold.md` | 模板生成 T2 测试 | T2 gold 字段、指标和示例 | 逐步淘汰；长期内容迁入 `template-generation-testing.md` 的 T2 章节或测试参考附录 |
| `template-generation-stage-optimization.md` | 模板生成 | 阶段优化地图、工作包和验证记录 | 移出 current；后续变化进入 status，具体方案进入 plan |
| `template-generation-open-gaps.md` | 模板生成 | 当前缺口和核实顺序 | 移出 current；迁入 `docs/status/`，具体方案进入 plan |
| `content-field-and-slot-contract.md` | 跨阶段 | 内容字段、内容节点、模板槽位匹配和目标样式引用 | draft canonical；共享语义变化只写这里 |
| `student-content-extraction-architecture.md` | 学生论文内容提取 | 尚未建立提示和共享契约入口 | 阶段架构尚未定义，不能由共享字段契约代替 |
| `student-content-extraction-field-contract.md` | 学生论文内容提取 | 旧文件名兼容指针 | 已淘汰；不再新增事实 |
| `project-directory-structure.md` | 全仓库 | 文件和目录放置规则 | 保留为独立治理文档，不并入业务架构 |

## 4. 迁移期维护规则

从本规则生效后：

1. 新增长期架构、输入输出、字段或上下游契约，只写入第 2 节指定的 `*-architecture.md`。
2. 新增长期测试入口、gold、指标、裁判或完成标准，只写入对应的 `*-testing.md`。
3. 目标文档尚未创建时，先按第 3 节的临时 canonical 文档维护；不要新建第三种同类文档。
4. 旧文档只允许迁出内容、修正错误、补充迁移提示或删除重复内容，不再承载新的长期事实。
5. 当前变化、bug、上下游影响和未闭环事项进入 `docs/status/`；具体修改方案进入 `docs/plans/`。
6. 旧文档只有在内容已迁移、引用已替换、残留已扫描后才能删除。

目标文档建立后，应在对应旧文档开头标记迁移目标，并把本表状态改为“迁移中”或“已淘汰”。

## 5. 按任务进入

| 要做什么 | 先读什么 |
| --- | --- |
| 理解整个 DocFit 流程或修改跨阶段关系 | 本 README，再读全系统架构临时或目标文档 |
| 修改某阶段职责、输入输出、字段或消费者 | 本 README，再读该阶段架构与数据契约 |
| 修改某阶段测试、gold、指标、裁判或报告 | 本 README，再读该阶段测试与评测契约 |
| 查看当前启用范围和 gate | `contracts-and-gates.md` |
| 发现变化、bug、下游未迁移或评测问题 | `docs/status/README.md`，并检查 `docs/status/INDEX.md` |
| 制定或执行修改计划 | `docs/plans/README.md` |
| 新增或移动文件 | `project-directory-structure.md` |

目录规则只回答“文件放哪里”；架构文档回答“系统应该怎样工作”；测试文档回答“怎样证明它正确”；status 和 plan 分别回答“现在有什么问题”和“具体怎样修改”。
