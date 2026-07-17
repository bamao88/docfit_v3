---
status: draft
owner: template-generation
stage: full-chain
topic: remaining-capability-closure
doc_type: issue
issue_id: TEMPLATE-GENERATION-FULL-CHAIN-ISSUE-01
issue_sequence: 01
previous_issue:
  id: none
  doc: none
  summary: 首个跨阶段能力缺口汇总 issue；用于把 T1/L1、T2/T3/T4、standard-judge、template-gap 和 full-chain 编排的剩余未实现能力集中记录。
previous_optimization:
  doc: docs/plans/2026-07-10-template-parse-refactor-t1l1-input-contract-plan-08-l1-projection-bundle-gate.md
  summary: 已落地 L1 输入投影 artifact、run bundle 绑定和 route-eval 全链路可见性；真实三校验证证明输入输出契约可用，但仍有自动编排、隔离重放、真实 render/object binding 和 AI-primary 晋升等能力未闭环。
next_plan: docs/plans/2026-07-11-template-parse-refactor-full-chain-capability-plan-01-end-to-end-closure.md
created: 2026-07-11
last_updated: 2026-07-11
related_docs:
  - docs/plans/2026-07-01-template-parse-refactor-standard-judge-route-eval-plan-03-full-chain-three-route-evaluator.md
  - docs/plans/2026-07-03-template-parse-refactor-t2t3t4-agent-proposal-issue-08-t1-l1-input-contract.md
  - docs/plans/2026-07-10-template-parse-refactor-t1l1-input-contract-plan-08-l1-projection-bundle-gate.md
  - docs/plans/2026-07-03-template-parse-refactor-t2t3t4-agent-proposal-plan-10-t4-ai-primary-layout-consumption.md
  - docs/plans/2026-07-03-template-parse-refactor-t3-element-policy-plan-06-run-span-subelement-policy-ai-primary.md
---

# 模板生成全流程未实现能力 Issue 01：端到端闭环剩余缺口

## 真实运行口径

最近一次真实回归采用三校真实模板和标准：

```text
schools:
  - hunannongye
  - nannong-undergraduate
  - pku-graduate

flow:
  1. docfit eval template-generation-full
  2. 验证同一 run root 下的 eval_runs/template_generate
  3. 验证同一 run root 下的 eval_runs/template_gap
  4. 验证同一 run root 下的 eval_runs/template_generation_judge
  5. 验证根目录 full_summary.json/md

output_root:
  /private/tmp/docfit_template_generation_full_hunannongye
  /private/tmp/docfit_template_generation_full_nannong_undergraduate
  /private/tmp/docfit_template_generation_full_pku_graduate
```

已确认的当前能力：

```text
1. 三校 template-generation-full 均能一次产出 eval_runs/template_generate、
   eval_runs/template_gap、eval_runs/template_generation_judge 和 full_summary.json/md。
2. 三校 template-generate 均能产出完整编号 artifact 链。
3. 三校均写出 01.5_l1_input_contract.json 和 artifacts/template_generation_l1_input_contract.json。
4. 三校 template-gap 均能产出 artifacts/template_gap_report.json。
5. 三校 template-generation-judge 均能输出 template_generation_route_eval_report.json。
6. full_summary.json 包含 artifact_type、school_id、template_version、status、
   stage_statuses、first_bad_stage、final_gap、route_eval、owner_summary、
   next_verification、gates 和 artifacts。
7. route-eval 覆盖 T1/L1/T2/T3/T4/T5/T6/T7/POST_T6，route candidates = 23。
8. full-chain 跑完后，POST_T6.merged 能绑定真实 template_gap_report 证据。
9. T1/L1 禁止语义字段扫描通过；未发现 unit_id/policy/confidence/is_toc_entry 等越界字段。
```

当前状态不能解读为“模板生成完全闭环”。`UNKNOWN` / `FAIL` 是阶段质量和标准差异结果；本 issue 只记录能力层面的未实现或未闭环项。

## Expected vs observed

| 编号 | 能力 | Expected | Observed |
| --- | --- | --- | --- |
| 01 | 一行全流程编排入口 | 一条命令从真实模板生成到 gap、judge、route-eval、总汇总全部产出，且目录结构稳定。 | 已落地 `docfit eval template-generation-full`；三校真实模板均产出 `eval_runs/template_generate`、`eval_runs/template_gap`、`eval_runs/template_generation_judge` 和根目录 `full_summary.json/md`。当前状态仍为质量门禁 `FAIL`，first_bad_stage=T3。 |
| 02 | judge 自动派生或绑定 post-T6 gap | `template-generation-judge` 能在同一 run root 下自动发现或派生 template-gap，并让 `POST_T6.merged` 有证据。 | 已支持默认派生/绑定 post-T6 gap；full-chain 三校 `POST_T6.merged` 绑定真实 `template_gap_report.json`。剩余问题是最终 gap 内容仍暴露质量失败。 |
| 03 | T5/T6/T7/post-T6 三路线隔离重放 | `code_raw`、`ai_raw`、`merged` 三条路线都能隔离生成 T5/T6/T7/post-T6 证据并横向比较。 | 已不再全部用 `NOT_EVALUABLE` 占位；可物化路线会写 route replay/gap 证据，默认未配置 AI observation 时 `ai_raw` 仍为 `NOT_AVAILABLE`，三路线隔离重放尚未完全闭环。 |
| 04 | 真实 render/page/object 绑定 | L1 `visual_page_index` 来自真实 render；文本和对象有 page/bbox 绑定或可审计的不绑定理由。 | 当前 full-chain 会生成 render/L1 证据；真实三校仍暴露质量问题：湖南农大可出现 render fallback，南农/北大仍有 object binding gap。 |
| 05 | L1 作为唯一输入投影 | T2/T3/T4 code 与 AI 都只消费同一个 L1 projection，避免各阶段各自解释 T1/render 事实。 | L1 已生成并进入裁判，但下游没有被强制改成只读 L1；当前 L1 主要是统一审计层和诊断证据。 |
| 06 | T4 section/page-numbering hint 一等消费 | accepted `section_profile_hint`、`page_numbering_hint` 变成 `global_spec/template_spec/build_manifest` 的一等字段和执行证据。 | `page_policy_hint` 已有消费链路；section profile 和 page numbering 已有 recorded / explicit noop 证据，但仍需证明对最终 DOCX 的有效执行级消费。 |
| 07 | 默认真实 run 自动生成 AI observation | 配置开启后，一次真实 run 能稳定得到 T2/T3/T4 `ai_raw`，并进入 bridge / route-eval。 | 完整 `template-generate` / `template-generation-full` 仍默认 deterministic，显式 `--llm` 可开启 T2/T3 文本 API 与 T4 视觉 API；新增 `template-observe --stage t2|t3|t4` 单阶段 live 入口。尚未用真实 API 跑完三校并证明 `ai_raw` 稳定可用。 |
| 08 | AI-primary 晋升开关 | 当 `ai_raw >= code_raw` 且 `merged >= 两者` 时，可按阶段把 T4/T3 切到 AI-primary 默认权威。 | 已有 AI-primary gate 诊断和默认关闭/回退证据；默认晋升仍未打开，因未配置 AI observation 时 `ai_raw_not_available` 按预期阻断。 |
| 09 | T3 run/span 真实残留门禁 | issue-05 的 8 处行内格式说明残留清零；issue-06 的 66 个 placeholder-like 非删除元素清零或逐条有保留理由。 | T3 residual gate 已接入 route-eval/full_summary，但真实三校仍未清零；当前 full_summary 均为 `FAIL`，`first_bad_stage=T3`。 |
| 10 | 产品化 full summary | 全流程结束后有统一 `full_summary.json/md`，明确生成状态、最终 gap、first_bad_stage、route 缺口、owner 和 next verification。 | 已落地 `full_summary.json/md`。三校 summary 均保留 `status=FAIL`、`first_bad_stage=T3`，并记录 T3 residual、L1 object/render、AI raw unavailable、POST_T6 gap 等后续优化信号。 |

## 疑似根因

```text
1. 产品入口和验收入口边界被刻意拆开：
   template-generate 不接收 school、不读取学校标准；template-gap/judge 需要 school 和标准。

2. standard judge 已从只读已有 run bundle 演进为可默认派生 post-T6 gap：
   post-T6 证据已能自动绑定；剩余问题是 gap 内容仍指向真实模板质量失败。

3. route-eval 已补“可见性和诊断”，并开始物化后段可用路线：
   但未配置 AI observation 时 ai_raw 仍不可用，T5/T6/T7/post-T6 的三路线比较尚未成为完整质量闭环。

4. render/L1 已进入默认诊断底座：
   但真实 render fallback、object binding gap 仍会让 L1 质量报告阻断。

5. AI observation 在完整生成中默认关闭：
   当前默认 run 仍优先保证 deterministic 路径可复现；常用启用方式已收敛为
   `--llm`。T2/T3/T4 单阶段调试则默认 live，不再要求手工组合多个 agent 参数。

6. T4 部分布局 hint 尚无 Word 执行契约：
   section profile 和 page numbering 的观测可以保存，但还缺“如何改变最终 DOCX”的一等字段与动作证据。

7. T3 span 能力的代码面和真实残留门禁没有完全合一：
   已有局部能力和测试，但 8/66 真实残留清零尚未成为固定回归口径。
```

## 上一轮已解决 / 未解决对照

已解决：

```text
1. L1 输入契约 artifact 已落地，且进入 ordered debug output、artifacts 兼容视图和 run bundle。
2. route-eval 已从 T2/T3/T4 扩展到 T1/L1/T2/T3/T4/T5/T6/T7/POST_T6。
3. route-eval 已能输出 23 个 route candidates，并保留 path/hash/availability。
4. POST_T6 在存在 template_gap_report.json 时可绑定为 AVAILABLE。
5. L1 能诊断 render 缺失、object binding gap 和 bundle gate invalid stage。
6. T1/L1 禁止语义字段边界在真实三校回归中通过扫描。
7. 已新增 `docfit eval template-generation-full` 一行全流程入口。
8. 已新增产品化 `full_summary.json/md`，并在三校真实模板上验证固定目录结构。
9. `template-generation-judge` 已支持默认派生 post-T6 template-gap；full-chain 可自动产出 POST_T6 gap 证据。
```

未解决：

```text
1. T5/T6/T7/post-T6 的 code_raw/ai_raw 隔离重放仍未完全闭环；
   当前可物化路线已有证据，不可用路线仍暴露 NOT_AVAILABLE / out-of-scope reason。
2. 默认真实 run 仍存在真实 render/page/object binding 缺口：
   湖南农大可出现 render fallback；南农/北大仍暴露 object binding gap。
3. 下游阶段尚未强制只消费 L1 projection。
4. 默认真实 run 没有自动生成 AI observation；未配置时 ai_raw_not_available 仍按预期阻断 AI-primary。
5. T4 section profile / page numbering hint 仍需证明对最终 DOCX 的有效执行级消费。
6. AI-primary 晋升门禁和默认开关未实现；当前保持关闭并记录回退证据。
7. T3 真实残留仍未清零；三校 full_summary 当前均为 FAIL，first_bad_stage=T3。
```

## 后续验收门禁

这些门禁用于判断“能力真的闭环”，不能用单测、单个 artifact 存在或 `PASS/SIGNABLE` 替代：

```text
1. 一行命令可在三校真实模板上产出 template_generate、template_gap、template_generation_judge 和 full_summary。
2. full_summary 能明确说明生成是否完成、最终模板是否合格、首个失败阶段、route-eval 缺口、owner 和下一步验证。
3. 未手动先跑 template-gap 时，full-chain 或 judge 仍能让 POST_T6.merged 绑定真实 gap 证据。
4. T5/T6/T7/post-T6 的 code_raw、ai_raw、merged 不再仅靠 NOT_EVALUABLE 占位；若某路线不可评，必须有阶段契约级 out-of-scope 理由。
5. 三校真实 run 的 L1 render_status 不再是 not_available，或每个 not_available 都有可追责的环境/依赖理由。
6. source_object_index 中对象 binding gap 清零，或逐项有可审计保留理由。
7. T2/T3/T4 的 code 与 AI 使用同一 L1 projection 作为输入事实。
8. 配置开启 AI observation 后，三校真实 run 的 T2/T3/T4 ai_raw 均为 AVAILABLE 或 explicit_noop_with_reason。
9. T4 section_profile_hint 和 page_numbering_hint 在最终 template_spec/build_manifest/DOCX 中有有效消费证据。
10. T3 issue-05 的 8 处行内格式说明残留清零；issue-06 的 66 个 placeholder-like 非删除元素清零或逐条有保留理由；反例不误删。
11. AI-primary 开关只能在 route-eval 证明 ai_raw ≥ code_raw 且 merged ≥ 两者后打开，并保留回退证据。
```

当前已通过的验收门禁：

```text
1. 一行命令可在三校真实模板上产出 template_generate、template_gap、
   template_generation_judge 和 full_summary。
2. full_summary 已能说明生成状态、最终 gap、first_bad_stage、route-eval
   缺口、owner 和下一步验证。
3. full-chain / judge 已能让 POST_T6.merged 绑定真实 gap 证据。
```

## 不算完成的信号

```text
1. 只新增一个 wrapper 但不产出 full_summary，不算全流程闭环；当前已不适用，
   因 full-chain 已产出 full_summary.json/md。
2. 只让 POST_T6.merged 不报 NOT_AVAILABLE，但没有真实 gap 报告，不算 post-T6 闭环。
3. 只把 T5/T6 code_raw/ai_raw 标成 NOT_EVALUABLE，不算隔离重放闭环。
4. 只生成 L1 artifact，但下游继续各读各的 T1/render 字段，不算输入契约闭环。
5. 只把 AI hint 写到 ai_observations，不改变 template_spec/build_manifest/DOCX，不算 T4 消费闭环。
6. 只跑合成 fixture 或单个学校样本，不算 T3 真实残留门禁闭环。
```
