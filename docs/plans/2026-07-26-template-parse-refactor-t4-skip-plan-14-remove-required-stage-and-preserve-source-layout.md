---
status: approved
owner: template-generation
stage: T4T5T6T7POST_T6
topic: t4-production-skip
doc_type: plan
plan_id: T2T3T4-AGENT-PLAN-14
source_issue:
  id: T2T3T4-AGENT-ISSUE-14
  doc: docs/plans/2026-07-26-template-parse-refactor-t4-skip-issue-14-copy-first-stage-has-no-execution-effect.md
previous_plan:
  id: T2T3T4-AGENT-PLAN-13
  doc: docs/plans/2026-07-26-template-parse-refactor-t4-ai-only-plan-13-single-ai-final.md
related_status:
  - docs/status/active/t4-production-skip.md
created: 2026-07-26
last_updated: 2026-07-26
---

# T4 Plan 14：跳过 required stage，保护源 Word 全局版式

## Execution Contract

### Target Capability

完整模板生成跳过 T4。系统以 L1 作为源全局版式事实和身份基线，以 T2/T3 作为唯一 AI
业务判断，T5 机械绑定单元、元素和源 section，T6 复制并保护源 DOCX 全局版式，T7
从最终 DOCX fresh observation 证明没有意外破坏。

### Non-Goals

- 不重编号 T5/T6/T7；T4 编号保留为未来能力槽位。
- 不在本轮实现从空白 DOCX 重建或自动修复全局版式。
- 不把 T4 AI 逻辑迁成隐藏的 T5/T6 启发式。
- 不用“复制成功”代替最终 section/page/header/footer/numbering preservation 验证。

### 上下游修改清单

#### 1. L1：补齐可绑定的源 section 基线

- 确认 `layout_fact_index.sections` 每个 section 有稳定 `source_ref/section identity`。
- 若 L1 尚无 section source range，基于 `sectPr` 位置和统一 source index 确定性派生
  section span；该派生只表达 OOXML 位置事实，不判断单元语义。
- 保存页面设置、页眉页脚 relationship、PAGE field、styles 和 numbering 的源基线及
  coverage，供 T5 绑定和 T7 对账。

#### 2. 生产编排：停止 T4

- 从完整 observation pipeline、live/replay/bundle runtime 和 provider 调用中删除 T4。
- 删除 T4 prompt、evidence、materializer、publisher 及只为 T4 服务的 provider 分支；
  共享视觉/provider 代码仅在 T2/T3 仍使用时保留。
- T4 跳过不产生 `NOT_AVAILABLE`，也不占用模型调用、缓存或额度熔断状态。

#### 3. 产物和 Final 链

- 停止写入 `01.8_t4_l1_stage_input.json`、
  `04.1_t4_ai_layout_observation.yaml` 和 `04_global_spec.yaml`。
- 从 run manifest、debug index、inspect 列表和 artifact schemas 删除 T4 required 槽位。
- 历史文件只读归档；生产代码不得兼容读取。

#### 4. T5：改为 L1 + T2 + T3

- `build_template_spec` 只接收 L1、T2 final、T3 final。
- availability 只保守合并 T2/T3。
- 移除 `template_spec.global` 的 T4 final 副本和 `section_profile_refs` 语义。
- 用 T2 `source_seq_refs/source_refs` 与 L1 section span 求交，生成命名明确的源
  section binding trace；未绑定或跨 section 时保留结构化 review flag。
- section binding 只说明源 Word 归属，不生成新的版式决策。

#### 5. T6：copy-first 版式保护

- `copy_source_docx` 保持第一步，并把源 package/L1 hash 写入前置条件。
- 删除说明、替换 span、插入 slot 或分页时，禁止静默删除携带 `sectPr` 的结构。
- 没有明确未来版式变换合同的情况下，不生成 page setup、header/footer、page
  numbering 或 numbering 重建动作。
- manifest 记录源版式 preservation 基线和最终 observation 引用。

#### 6. T7 / POST_T6：承接原 T4 质量责任

- 重新解析最终 DOCX，并与 L1 对账 section count/identity、页面尺寸/边距、
  header/footer relationship、PAGE field、styles 和 numbering。
- 区分“业务动作明确改变”与“意外漂移”；意外漂移归因 T6。
- POST_T6 继续按学校标准验证最终视觉版式；只有确定性证据不足时才允许附加视觉 AI
  诊断，不能把诊断反写业务产物。

#### 7. CLI、judge、gold 和报告

- 正式/调试 CLI 去掉 T4 AI 模式；兼容入口应删除或明确返回阶段暂停。
- route-eval、stage cards、first_bad_stage、required ledger 不再期待 T4 artifact；
  需要展示阶段拓扑时标为 `SKIPPED/RESERVED`。
- 三校 `t4_global_layout.standard.yaml` 退出 required stage gold；其中仍有价值的最终
  版式期望迁入 POST_T6 canonical school gold，源事实完整性检查迁入 L1。
- 删除 T4 route accuracy、hint consumption 和旧 artifact residual。

### Implementation Order

1. 先补 L1 section identity/range 和 preservation 基线合同及测试。
2. 改 T5 签名、binding 和 availability，建立 L1+T2+T3 的唯一合并链。
3. 从 runtime、runner、outputs、CLI 和 manifest 删除 T4。
4. 把版式保护检查接入 T6/T7 和 POST_T6 报告。
5. 迁移 judge/gold/fixtures/tests，删除 T4 生产代码和残留。
6. 用三校真实 Word 跑完整生成、fresh observation 和最终 gap。

### Completion Signals

- 完整生成 API trace 中没有 T4 调用，输出树没有 `01.8` 或 `04_*`。
- T5 input refs/availability 只包含 L1、T2、T3。
- T2 单元能绑定到 L1 section；跨 section 和未绑定反例可诊断。
- 删除/插槽/分页动作不会丢失源 `sectPr`、header/footer、PAGE、styles、numbering。
- T4 历史 artifact 放入 run 也不会被生产消费者读取。
- 三校最终 Word preservation 对账和 POST_T6 质量报告有真实证据。

### Anti-Degradation Rules

- 禁止把 T4 改名后藏进 T5/T6。
- 禁止用 L1 事实推断学校应该采用的新布局；L1 只描述源 Word。
- 禁止把 T4 缺失报告成失败或 `NOT_AVAILABLE`。
- 禁止只验证文件存在、section count 或 manifest `executed`，必须检查最终 OOXML 和必要
  render 效果。
- 禁止因移除 T4 而删除对页眉页脚、页码、styles、numbering 的最终质量检查。

### Verification Matrix

| Gate | Command / Evidence | Required Result |
| --- | --- | --- |
| unit | L1 section range、T5 binding、availability、T6 sectPr 保护 | 正反例覆盖，T4 不参与 |
| contract | template-generate、bundle/replay、manifest、inspect | 无 T4 输入、调用、产物和 required ref |
| residual | `rg` 扫 T4 prompt/publisher/artifact/route/standard consumer | 生产引用为 0；历史文档可保留 |
| real sample | 三校完整生成 + final DOCX fresh observation | 源全局版式无意外漂移 |
| final quality | 三校 POST_T6 gap/judge | 版式质量仍被评分，T4 显示 skipped/reserved |

### Residual Policy

若 L1 尚不能可靠派生 section span，计划保持 `implementing/implemented_in_part`，不得用
空 binding 或固定 `section_unknown` 代替。若未来需要主动修改全局版式，必须新建 issue/
plan 定义可执行 OOXML 动作和最终效果验收，不恢复本计划删除的 observation-only T4。
