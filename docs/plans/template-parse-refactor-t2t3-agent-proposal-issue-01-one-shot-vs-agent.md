---
status: draft
owner: template-generation
stage: T2T3
topic: agent-proposal
issue_id: T2T3-AGENT-ISSUE-01
issue_sequence: 1
created: 2026-06-27
last_updated: 2026-06-27
version: 1
previous_issue: none
previous_optimization: none
next_plan:
  id: T2T3-AGENT-PLAN-01
  doc: docs/plans/template-parse-refactor-t2t3-agent-proposal-plan-01-current-code-ai-overlay.md
  summary: Implement a default-off in-repo Agent Harness with replay, structured submit tools, deterministic overlay, regeneration, verifier feedback, and attribution. Treat one-shot structured output only as max_rounds=1 transcript.
related_issues:
  - docs/plans/template-parse-refactor-t2-unit-recognition-issue-03-state-machine-standard-gates.md
  - docs/plans/template-parse-refactor-t3-element-policy-issue-02-post-confidence-residuals.md
related_code:
  - src/docfit/template_generation/runner.py
  - src/docfit/template_generation/t2_standard.py
  - src/docfit/template_generation/verifier.py
  - src/docfit/template_generation/artifacts.py
  - src/docfit/template_generation/structure_candidates.py
---

# T2/T3 Agent Proposal Issue 01：单次 LLM 调用不足以作为最终架构

## 0. 记录目的

本文记录对当前项目的验证结论：单次 LLM structured output 是否能满足 T2/T3 模板生成修复需求，以及是否需要 Plan-01 所描述的 Agent Harness。

结论：

```text
当前代码没有任何 live LLM / one-shot / agent 接口。
单次 LLM 调用可以作为最小 single-round fixture/transcript。
单次 LLM 调用不能作为最终架构。
需要仓库内自研薄 Agent Harness；不需要引入 LangChain / LangGraph / CrewAI 作为主路径。
```

## 1. 当前真实运行口径

验证日期：2026-06-27。

代码基线：

```text
HEAD: 141c0e9 docs: clarify t2t3 agent runtime selection
```

静态代码检查：

```text
rg -n "AgentConfig|agent_config|template_agent|agent_|LLM|llm|OpenAI|openai|Anthropic|anthropic|messages\.create|chat\.completions|responses|tool_use|structured|overlay|transcript|replay|Fixture|Transport" src tests docs/current docs/plans -S
```

Observed：

```text
src/ 中没有 OpenAI / Anthropic / LLM transport。
src/ 中没有 AgentConfig / agent_config。
src/ 中没有 template_agent artifact、transcript、replay、overlay 或 transport 实现。
pyproject.toml 只有 python-docx、pyyaml、typer；没有 LLM SDK 或通用 agent 框架依赖。
```

真实 T2 metrics：

```text
uv run python scripts/t2_metrics.py
```

输出：

```text
school                   units other custom   cat_in/exp  leak  toc?   oq gate
------------------------------------------------------------------------------
hunannongye                 14     0      0        20/20     0  True   28  PASS
nannong-undergraduate       11     0      0        25/25     0  True   11  PASS
pku-graduate                13     0      2        17/17     0 False   32  PASS
```

真实 T2 signed standard audit：

```text
uv run python scripts/t2_metrics.py --standard-gate
```

输出：

```text
school                   units custom missing unexpected  owner  order?   audit          gate
---------------------------------------------------------------------------------------------
hunannongye                 14      0       2          0      3   False    FAIL    AUDIT_FAIL
  missing: body_title_block, topic_change_approval
  owner: body_title_block@12->cover, body_title_block@54->None, topic_change_approval@260->defense_record
nannong-undergraduate       11      0       0          0      1   False    FAIL    AUDIT_FAIL
  owner: body_main@50->abstract_en
pku-graduate                13      2       1          2      4   False    FAIL    AUDIT_FAIL
  missing: toc
  unexpected: custom:template:二〇年月:11, custom:template:englishtitleofyo:25
  owner: toc@None->None, references@244->body_main, references@245->body_main, originality_authorization_statement@344->acknowledgement
```

目标测试：

```text
uv run pytest tests/unit/test_t2_standard.py tests/contract/test_template_generate.py -q
```

输出：

```text
19 passed in 2.04s
```

T3 标准状态：

```text
standards/targets/*/v1/template_generation/t3_element_policy.standard.yaml
  standard_state: signed_pending_verifier
  verifier_state: not_configured
  gate_enabled: false
```

## 2. Expected vs Observed

### 2.1 One-shot 最小可行形态

Expected：

```text
单次 structured output 至少必须能：
1. 绑定 page_text_index / source_seq。
2. 输出 schema-valid layered submission。
3. 经 deterministic reconciler 转成 overlay proposals。
4. patch structure_candidates 后重生 unit_map / generation_model / element_spec。
5. 记录 transcript、accepted/rejected proposal、round0 vs post-agent diff。
6. 零网络 replay。
```

Observed：

```text
当前项目没有上述任何 runtime 入口。
现有 generate_template() 参数只有 source_template_docx、out_dir、strategy、debug_root。
verify_template_parse_build() 只收 T1-T6 artifact，不收 agent submission、transcript、overlay 或 standard bundle。
```

判断：

```text
one-shot 现在不是已存在能力。
即使实现 one-shot，也必须包进 Agent Harness 的 max_rounds=1 transcript，而不是直接让 LLM JSON 改中间产物。
```

### 2.2 T2 当前需求

Expected：

```text
三校 T2 unit_order、unit_id、anchor ownership 应匹配 signed T2 standard。
```

Observed：

```text
TOC 局部 metrics PASS。
signed standard audit 三校仍全部 FAIL/AUDIT_FAIL。
```

判断：

```text
T2 的关键缺口不是“让模型一次猜一个 JSON”。
关键缺口是：模型建议必须经过 source_seq 绑定、目标归属校验、overlay 可执行性校验、重生和 standard/verifier feedback。
```

### 2.3 T3 当前需求

Expected：

```text
T3 应按 signed t3_element_policy.standard.yaml 检查 unit_order、policy group、fill_source、manual_semantics、generated.field_type、instruction cleanup 和 source trace。
```

Observed：

```text
三校 T3 standard 文件存在，但 verifier_state=not_configured、gate_enabled=false。
src/docfit/template_generation/ 没有 t3_standard.py 或 judge_t3_element_policy。
当前 _verify_t3_element_spec() 只检查 policy 闭集、fill_source、manual_semantics、generated.field_type 和 flags。
element_spec.ai_traces 仍为空。
```

判断：

```text
T3 缺的是可验证的标准闭环和更细粒度 source/run/inline 证据。
one-shot 没有 verifier feedback 和 target rebind 时，无法可靠处理错误 high confidence、行内说明残留、generated 假阳性等问题。
```

## 3. 疑似根因

```text
1. 当前 runner 没有 school_id / StandardBundle / agent_config 参数，所以 T2/T3 标准和 agent 建议都不能进入主 verifier。
2. T2 standard audit 已存在，但仍是脚本侧能力，没有接到 verify_template_parse_build() 的权威 status。
3. T3 standard 已签收但 verifier 尚未实现，缺少 element_spec.expected/gold 级精确比对。
4. 当前没有 render packet、annotated source_seq、tool schema、transcript、replay、overlay、attribution 等 agent 必要边界。
5. 单次 LLM 没有 rejected proposal 后的 focused retry，也没有 changed=False / verifier peek stop 条件。
```

## 4. 上一轮已解决 / 未解决对照

已解决或已有基础：

```text
1. T1 verifier 已检查 semantic judgment fields，fact-only 边界已有硬门禁。
2. T2/T3 可重生 seam 清楚：patch structure_candidates 后可重跑 build_unit_map()、build_template_generation_model()、build_element_spec()。
3. T2 custom 单元数量比旧 issue 记录明显下降，说明确定性主干仍在改善。
4. T2 standard audit 有独立实现和单测。
5. Plan-01 已明确默认关闭、replay-first、AI advisory-only、不引入通用 agent 框架。
```

仍未解决：

```text
1. T2 standard audit 三校仍 FAIL/AUDIT_FAIL。
2. T2 standard audit 未接入 generate_template() / verify_template_parse_build()。
3. T3 standard verifier 未实现，gate 未开启。
4. 无 AgentConfig、render packet、submit tools、transcript replay、overlay reconciler、attribution artifacts。
5. 无 round-0 vs post-agent 对照，无法把 mismatch 归因为原有问题、AI 改善或 AI 引入。
```

## 5. 后续验收门禁

Plan-01 落地时必须至少满足：

```text
1. 默认关闭：不传 agent_config 时，现有输出和测试保持不变。
2. 零网络：single-round 与 multi-round transcript replay 可在 CI 跑通。
3. one-shot 限位：单次 LLM 只作为 max_rounds=1 transcript，不直接改 artifact。
4. source 绑定：AI 输出的 source_seq_refs 必须存在于 render packet / page_text_index。
5. target 绑定：T3 source_seq/render target 必须能唯一映射到当前 structure_candidates 的 unit/element，否则 rejected/open_question。
6. overlay 可执行：patch 后不得制造 gap/overlap，不得移除 body_main，不得绕过 candidate_policy enum。
7. 重生闭环：接受 T2/T3 overlay 后必须重跑 unit_map、generation_model、element_spec。
8. verifier feedback：reconciler / verifier peek 必须能产生 accepted/rejected proposal 和 next_window_suggestions。
9. T4 边界：首轮只落 hints，不 patch global_spec/template_spec/plan。
10. 归因：必须能比较 agent off/on，并把 field diff 绑定到 round_id / proposal_id。
```

## 6. 决策建议

```text
采用 Plan-01 的仓库内薄 Agent Harness。
不要把单次 LLM 调用当最终方案。
不要引入 LangChain / LangGraph / CrewAI 作为主架构。
先实现 default-off harness + replay + schema + overlay hard checks，再接 live SDK。
```
