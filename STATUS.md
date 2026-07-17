# DocFit Status

Last updated: 2026-07-11

一句话结论：模板生成 L1 输入迁移已验证完成；三校真实 API 无明显回退报告与最终代码固定 replay 均为 `PASS`。T3 Plan 06 现在可恢复，但本轮没有执行其 span/policy/prompt/AI-primary 改造。

## Current Focus

本轮已完成范围：

```text
三校 source_template.docx
  -> 迁移前 `template-generation-full --llm` baseline
  -> Plan 08: T1/render -> seal L1
  -> T2/T4 code + AI 统一事实输入；T3 仅兼容迁移
  -> T5/T6/T7 受限 L1 身份、执行和验证消费
  -> 旧事实链与重复 mapper 清零
  -> 迁移后三校同配置真实 API
  -> live 质量对比 + 固定 observation replay 等价对比
  -> Plan 08 verified / issue-08 closed
```

当前不做：

```text
T3 Plan 06 的 span/policy/prompt/AI-primary 改造
学生内容提取标准
内容放置标准
最终 DOCX 渲染标准
完整学生论文转换 gate
```

原因：学生内容提取的流程、阶段边界、产物模型和验收口径尚未实现清楚。现在制作学生或 case 标准会把历史 fixture 当成事实来源，风险太高。

## Current State

- `template-generation-full`、post-T6 gap、standard judge、route-eval 和三校标准入口已经存在。
- L1 现在在 T2/T3/T4 之前封存，只包含 T1/render 客观事实、run/object/page identity、coverage 和稳定 hash。
- T2/T4 code+AI 与 T3 compatibility 只通过 L1 Stage Input 读取事实；T5/T6/T7 绑定同一 canonical L1 hash。
- T6 使用 sealed L1 resolver 校验源 package、source/run/char-range identity；失败结构化返回，不扩大动作范围。
- 旧 `08_agent_render_packet.json` artifact 和 run-backed legacy fallback 已删除；render packet builder 只保留为 L1 前置 render facts 实现。
- Plan 08 为 `verified`，issue-08 为 `closed`；三校最终报告见 `test_outputs/debug/template_generation/20260711_l1_migration_live_api_candidate_v1/migration_quality_comparison.json`。
- 当前工作区包含大量用户既有未提交改动，本 session 只修改 Plan 08 直接范围并保护其他改动。

## Next Action

1. 以 Plan 08 已验证的 sealed L1 为前置，恢复 T3 Plan 06 的 run/span/policy 质量工作。
2. 保持 T3 compatibility Adapter 的退出条件：新 T3 Stage Input 和完整 merged/T6 精确消费通过后再删除。
3. 继续把三校当前真实 `FAIL` 归因到既有 T2/T3/T4/最终 Word 质量 gap，不回退 L1 输入契约。

## Deferred

这些目录和历史材料可以保留，但当前不作为标准制作入口：

- `standards/students/**`
- `standards/cases/**/placement/**`
- `standards/cases/**/render/**`
- `inputs/students/**`
- 历史 real-core 学生/case fixture

启用这些范围前，必须先明确：

- 学生内容提取阶段的输入、输出和字段语义；
- 内容 ledger 的最小标准；
- 放置计划如何表达每段学生内容的去向；
- 渲染 manifest 如何证明最终 Word 忠实执行放置计划；
- 哪些内容属于学校模板，哪些内容属于学生源文档。

## Verification

当前模板阶段常用命令：

```bash
uv run docfit template generate \
  --template inputs/targets/hunannongye/raw/source_template.docx \
  --out runs/template_generation/hunannongye/eval_runs/template_generate
```

```bash
uv run docfit eval template-gap \
  --school hunannongye \
  --generated-template runs/template_generation/hunannongye/eval_runs/template_generate/fillable_template.docx \
  --out runs/eval/template_gap/hunannongye/template_generate
```

标准裁判实现后，期望命令：

```bash
uv run docfit eval template-generation-judge \
  --school hunannongye \
  --run runs/template_generation/hunannongye/eval_runs/template_generate \
  --out runs/eval/template_generation_judge/hunannongye/template_generate
```
