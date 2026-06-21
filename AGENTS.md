本仓库的讨论、计划、总结和最终回复默认使用中文；除非用户明确要求其他语言。

# AGENTS.md

DocFit v3 是一个以评测框架优先的 DOCX 转换原型。产品目标不是“做出一个
DOCX”，而是用确定性证据证明转换结果满足已签收标准。

## 写作约定

- 回消息、写计划、写总结和写文档时，优先使用普通产品语言，
  直接说明“这个文件做什么、在检查什么、失败说明什么、下一步要改哪类问题”。
- 默认先给一句人能看懂的结论，再给证据、文件、命令、验证结果和剩余未知。
  不要只说“已修改”“已优化”“已修复”；必须说明改了什么、行为变化是什么、
  用什么证明、还有什么没有证明。
- 解释系统、问题、流程或改动时，明确区分“当前真实实现”“已有设计意图”
  “建议方案”“当前假设”和 `UNKNOWN`。不能把设计、猜测或计划当成当前实现来讲。
- 先判断用户要的是只读审计、开发前对齐、实施计划、实际执行、调试还是审查。
  用户明确说“做、修、合并、整理、执行”时直接推进；用户是在问“现在到底是什么、
  有没有真的做、问题在哪、我看不懂”时，先只读审计并列证据，不要直接重构。
- 排查多步骤流程时，优先找问题第一次出现在哪一步，说明 `first_bad_stage`、
  应该改哪里、不应该改哪里，以及最小下一步。不要看到最终输出不对就直接改最终输出。
- 比较状态、字段、流程、文件、风险、验证结果时，优先用表格。用户说看不懂时，
  切换成产品负责人可读格式：一句话结论、当前真实情况、问题第一次出现在哪一步、证据、
  下一步应该改哪里、不应该改哪里、还不知道什么。
- 交付任何执行结果时，给出变更证明：修改文件、行为变化、验证命令和结果、
  剩余 `UNKNOWN`。如果没有运行验证，必须说明原因和风险，不能说成已经通过。
- 新增或修改字段、JSON 形状、报告字段、阶段产物前，先说明字段含义、生产者、
  消费者、是否影响 `PASS` / `FAIL` / `UNKNOWN`、缺失时怎么办，以及是否允许 AI 编辑。
- 不要用名词堆叠代替解释。避免把 `exposure`、`finding`、`contract`、
  `verifier`、`strategy contract`、`stage contract` 这类词当成默认表达。
- 标题、文件名、状态页和下一步目标也要说清楚具体用途，不要只写专有名词。
- 如果这些词是代码、文件名、命令输出或既有产品概念的一部分，可以保留原名，
  但必须先用中文说明它的实际用途和对应的具体检查。

## 必读文件

- `README.md`：先读短版项目说明和启动命令。
- `SPEC.md`：先读产品语义、阶段边界和门禁规则。
- 处理任何生成模板差距、`template-gap`、生成模板报告、`FAIL` / `UNKNOWN`
  诊断或相关 e2e 问题前，先读 `docs/human/template-gap-process-mainline.md`。
  这是该领域优先级最高的流程指南：先在文档中定位阶段、输入、输出和责任，
  再改代码、测试或报告。
- 修改模板生成阶段的产物字段、JSON 形状、manifest 清单、差距报告或生产者/消费者
  连接前，先读 `docs/human/template-generation-artifact-field-dictionary.md`。
  必须先定义字段含义、生产者、消费者、门禁影响、字段缺失结果、默认规则和
  AI 可编辑边界。不要新增未记录字段，不要为已签收含义猜默认值，也不要把
  `template_artifact` / `template_generation_manifest` 当成
  `generated_template.docx` 真实内容的证明。
- `docs/agents/**`：面向代理的长流程手册；根文件放不下的流程放这里。
- `standards/schools/**` 下的相关标准，以及 `tests/**` 下的相关测试。

`SPEC.md` 是完整产品规范的主来源。
`DOCFIT_EVAL_HARNESS_FIRST_SPEC_CN.md` 只是短兼容指针。

## 项目地图

- `src/docfit/cli/`：Typer CLI 和 `docfit eval ...` 入口。
- `src/docfit/convert/`：串联已验证阶段的转换编排。
- `src/docfit/stages/`：模板解析、内容提取、内容放置和 DOCX 渲染。
- `src/docfit/harness/`：状态、标准、覆盖率、报告、问题聚类和审计辅助代码。
- `standards/schools/**`：只放可运行的已签收标准、检查契约、金标和例外。
- `standards/eval_profiles/**`：评测配置的期望产物。
- `inputs/**`：原始 DOCX/DOC 输入、学生样例和人工复核证据。
- `reports/**` 和 `out/**`：生成的证据或输出；除非任务明确要求保留，否则按生成物处理。

## 核心不变量

- 门禁状态只能是 `PASS`、`FAIL` 和 `UNKNOWN`；`UNKNOWN` 会阻断通过。
- 从内容提取到渲染阶段，必须保留可见内容台账。
- 静默丢弃用户可见内容永远是阻断失败。
- `docfit convert` 不能绕过阶段检查器。
- AI 可以帮助诊断结构化报告，但不能决定通过或失败。
- 绝不自动更新金标、已签收标准、expected 快照，也不能把 `FAIL` / `UNKNOWN`
  改成成功。
- 优先修通用能力。学校专属行为必须有签收证据、注册/配置和测试。
- 除非任务明确要求，否则架构建议或重构不要以向后兼容为优化目标。相比保留迁移遗留表面，
  更应优先保持当前原型契约干净。

## 命令

安装或同步：

```bash
uv sync
```

基础验证：

```bash
uv run pytest
uv run docfit eval e2e --school demo-school --student inputs/bootstrap-demo-student-pass.docx --out reports/bootstrap_pass
```

修改检查契约、检查器、阶段、标准、输入资产或 CLI 评测行为时，运行聚焦测试，
并运行相关的 `docfit eval ...` 命令。更长的启动验证矩阵见
`docs/agents/bootstrap-eval-runbook.md`。

## 代理工作流

- 保持根指导文件简短。长的代理专用流程放到 `docs/agents/**`；
  可复用机制放到脚本或技能里。
- 开发自主规则：如果任务能由代理基于现有仓库上下文、本地工具或生成证据完成，
  就继续完成实现、验证、文档对齐和提交后再停。只有下一步确实需要用户本人复核、
  产品判断、凭据、外部材料或本地不可用能力时，才停下来找用户。停下时必须说明
  用户具体要做什么、为什么必须由用户做，以及会解锁什么。
- 宽泛或模糊任务先用 `$intuitive-preflight`；普通的有边界构建/修改任务用
  `$intuitive-flow`。
- 人类可读文档漂移用 `$intuitive-doc`，测试套件结构用 `$intuitive-tests`，
  大范围重构前用 `$intuitive-refactor`，周期性清理用 `$intuitive-reduce-entropy`。
- 目标仓库的 LSP 配置在 `pyrightconfig.json`；面向代理的 Serena/MCP 设置见
  `docs/agents/lsp-and-mcp.md`。
