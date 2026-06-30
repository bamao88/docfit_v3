# OpenAI Python SDK 接入 Kimi：DocFit T2/T3/T4 Agent 分阶段落地计划

本文把仓库内计划
`docs/plans/template-parse-refactor-t2t3t4-agent-proposal-plan-04-ai-code-generation-bridge.md`
（原 plan-01 已合并进该阶段唯一保留文档 plan-04，overlay-on-parse 细节见其附录 A）
细化为工程落地清单，并保留 Kimi Coding Plan 通过 OpenAI Python SDK 接入的实测参数。

当前结论：

```text
1. AI 只产结构化建议，不直接写 T1-T6 权威产物。
2. T2/T3 可以通过 overlay patch structure_candidates 后重生下游产物。
3. T4 首轮只写 hints artifact，不 patch global_spec/template_spec/plan。
4. verify_template_parse_build 仍是唯一 status 权威。
5. 默认关闭；没有 agent_config 时现有输出必须不变。
6. CI 只跑 replay/fixture，live Kimi transport 不作为 CI gate。
```

## 1. 当前基线

验证日期：2026-06-27。

当前主流程入口：

```text
src/docfit/template_generation/runner.py
  generate_template(source_template_docx, out_dir, strategy, debug_root)
```

当前还不存在：

```text
AgentConfig
agent_config 参数
template_agent_render_packet
page_text_index / page_layout_index
agent transcript / replay transport
agent_t2_overlay / agent_t3_overlay / agent_t4_hints
agent attribution
OpenAI / Kimi SDK transport
```

当前可复用基础：

```text
T1 document_facts:
  src/docfit/template_generation/source_tree.py

T2 structure_candidates:
  src/docfit/template_generation/structure_candidates.py

T2 unit_map 重生:
  src/docfit/template_generation/artifacts.py::build_unit_map()

T3 generation_model / element_spec 重生:
  src/docfit/template_generation/generation_model.py::build_template_generation_model()
  src/docfit/template_generation/artifacts.py::build_element_spec()

T4 global_spec:
  src/docfit/template_generation/artifacts.py::build_global_spec()

产物写盘:
  src/docfit/template_generation/outputs.py

权威 verifier:
  src/docfit/template_generation/verifier.py::verify_template_parse_build()

T2 signed standard audit:
  src/docfit/template_generation/t2_standard.py

Run bundle / stage verifier 初稿:
  src/docfit/harness/template_generation_run_bundle.py
  src/docfit/harness/template_generation_stage_verifiers.py
  src/docfit/harness/template_generation_standard_quality.py
```

## 2. 总体架构边界

### 2.1 AI 输入边界

AI 主输入必须来自 render 可见层 packet，而不是直接读取完整 T1 事实库或 standards。

允许输入：

```text
template_agent_render_packet.json
clean_page_images[]
annotated_page_images[]
page_text_index[]
page_layout_index[]
input_windows[]
canonical unit_id 命名参考
round0_snapshot_id
```

禁止作为主输入：

```text
T1 body_flow 全量事实
t2_derived_signals
deterministic_candidates
round-0 draft_unit_map / draft_element_spec
standards/targets/**
```

### 2.2 AI 输出边界

AI 每轮只能提交：

```text
template_agent_layered_submission_round_*.json
  layers.t2.unit_candidates[]
  layers.t2.block_candidates[]
  layers.t2.boundary_adjustments[]
  layers.t3.element_policy_candidates[]
  layers.t4.page_policy_hints[]
  layers.t4.section_profile_hints[]
  layers.t4.page_numbering_hints[]
  layers.*.open_questions[]
  abstain
```

AI 不允许直接写：

```text
document_facts
unit_map
element_spec
global_spec
template_spec
generation_plan
build_manifest
verification_report.status
standards
```

### 2.3 Reconciler 硬检查

所有 AI proposal 必须先通过 deterministic reconciler：

```text
C-SCHEMA              schema valid
C-EVIDENCE-EXIST      source_seq/render target 存在
C-TARGET-BIND         T3 target 能唯一映射到当前 candidate element
C-EXECUTABLE-ENUM     operation / policy / hint kind 属于可执行闭集
C-OVERLAY-EXEC        patch 后无 gap/overlap，不删除 body_main，不破坏顺序
```

探索期不做：

```text
confidence floor 拦截
requires_review 拦截
label 必须属于 UNIT_DEFINITIONS 闭集拦截
policy 语义合理性二审
AI status / PASS / FAIL 裁判
```

## 3. 目录与模块规划

新增轻量目录：

```text
src/docfit/template_generation/agent/
  __init__.py
  config.py
  packet.py
  schema.py
  replay.py
  tools.py
  loop.py
  reconciler.py
  overlay.py
  regenerate.py
  attribution.py
  transport.py
```

建议测试目录：

```text
tests/unit/template_generation_agent/
  test_agent_config.py
  test_agent_packet.py
  test_agent_schema.py
  test_agent_replay.py
  test_agent_reconciler.py
  test_agent_t2_overlay.py
  test_agent_t3_overlay.py
  test_agent_t4_hints.py
  test_agent_attribution.py
  test_kimi_transport_config.py

tests/contract/
  test_template_generate_agent_default_off.py
  test_template_generate_agent_replay.py
```

建议 fixture：

```text
tests/fixtures/template_generation_agent/
  packet_minimal.json
  packet_three_page.json
  transcript_single_round.json
  transcript_multi_round.json
  submission_t2_valid.json
  submission_t2_rejected.json
  submission_t3_valid.json
  submission_t3_rejected.json
  submission_t4_hints.json
```

## 4. Phase 0：render packet 前置

目标：live agent 必须有可见层 packet；没有 packet 时只能跑 replay fixture。

### 4.1 改动范围

新增：

```text
src/docfit/template_generation/agent/config.py
src/docfit/template_generation/agent/packet.py
tests/unit/template_generation_agent/test_agent_config.py
tests/unit/template_generation_agent/test_agent_packet.py
tests/fixtures/template_generation_agent/packet_minimal.json
```

最小配置对象：

```python
@dataclass(frozen=True)
class AgentConfig:
    enabled: bool = False
    transport: Literal["replay", "kimi", "minimax"] = "replay"
    max_rounds: int = 4
    transcript_path: Path | None = None
    render_packet_path: Path | None = None
    allow_live_without_render_packet: bool = False
```

render packet 最小字段：

```text
artifact_type = template_agent_render_packet
artifact_version
source_render_hash
status_authority = verify_template_parse_build
advisory_only = true
allowed_ai_tasks
forbidden_ai_tasks
render_artifacts.clean_page_images[]
render_artifacts.annotated_page_images[]
page_text_index[]
page_layout_index[]
input_windows
round0_snapshot_id
```

### 4.2 实施步骤

1. 增加 `AgentConfig`，默认 `enabled=False`。
2. 增加 `validate_agent_config(config)`：
   - disabled 时直接 PASS。
   - live transport 时必须存在 `render_packet_path`。
   - `allow_live_without_render_packet=False` 时禁止 live 空跑。
   - `max_rounds` 限制在 `1..4`。
3. 增加 `build_template_agent_render_packet(...)` 的最小实现。
4. 暂时允许 packet 使用 fixture，不强制本阶段完成 DOCX->PDF/image 渲染。
5. 在 packet 中保留 `source_seq`、`source_ref`、`page_no`、`bbox` 的字段位置。

### 4.3 验收门禁

```bash
uv run pytest tests/unit/template_generation_agent/test_agent_config.py \
  tests/unit/template_generation_agent/test_agent_packet.py -q
```

必须证明：

```text
1. 默认 AgentConfig 不改变任何 runner 行为。
2. live transport 无 render packet 会被拒绝。
3. replay transport 可只使用 fixture packet。
4. packet schema 能表达 source_seq/page/bbox 绑定。
```

## 5. Phase 1：输出 schema 与 replay

目标：先让 one-shot 成为 `max_rounds=1` transcript/replay，而不是直接改产物。

### 5.1 改动范围

新增：

```text
src/docfit/template_generation/agent/schema.py
src/docfit/template_generation/agent/replay.py
tests/unit/template_generation_agent/test_agent_schema.py
tests/unit/template_generation_agent/test_agent_replay.py
```

核心 schema：

```text
LayeredSubmission
  schema_version
  prompt_version
  source_render_hash
  round_id
  model
  layers.t2
  layers.t3
  layers.t4

AgentTranscript
  artifact_type = template_agent_transcript
  rounds[]
  tool_calls[]
  submissions[]
  stop_reason
```

proposal 统一字段：

```text
proposal_id
kind
source_seq_refs or render_target_refs
evidence
rationale
```

### 5.2 实施步骤

1. 用普通 Python dict/dataclass + 显式校验实现 schema，不新增 Pydantic 依赖。
2. 支持读取 `transcript_single_round.json`。
3. 支持读取 `transcript_multi_round.json`。
4. replay transport 输出和 live transport 同形的 `LayeredSubmission`。
5. schema 校验只保证形状、字段、闭集，不判断业务好坏。
6. 记录 rejected schema errors，但不抛出到主流程之外；由 agent result 表达。

### 5.3 验收门禁

```bash
uv run pytest tests/unit/template_generation_agent/test_agent_schema.py \
  tests/unit/template_generation_agent/test_agent_replay.py -q
```

必须证明：

```text
1. single-round fixture 可被 replay。
2. multi-round fixture 可逐轮 replay。
3. 缺少 source_render_hash / round_id / proposal_id 会 rejected。
4. one-shot 只是 transcript 的一轮，不绕过 reconciler。
```

## 6. Phase 2：T2 overlay

目标：接受通过校验的 T2 proposal，并 materialize 到 `structure_candidates.units`，随后重生 `unit_map`。

### 6.1 改动范围

新增：

```text
src/docfit/template_generation/agent/reconciler.py
src/docfit/template_generation/agent/overlay.py
src/docfit/template_generation/agent/regenerate.py
tests/unit/template_generation_agent/test_agent_reconciler.py
tests/unit/template_generation_agent/test_agent_t2_overlay.py
```

修改：

```text
src/docfit/template_generation/runner.py
```

### 6.2 支持的 T2 operation 最小集合

```text
add_unit
relabel_unit
adjust_unit_range
replace_unit_elements
```

### 6.3 关键实现要求

1. `unit_candidates[]` 可新增 canonical 或 custom unit。
2. `block_candidates[]` 不能只新增 locked range 字段；必须改写现有 unit 的：
   - `source_seq_refs`
   - `source_range`
   - `source_seq_range`
   - `source_refs`
   - `elements`
3. `boundary_adjustments[]` 必须保持 unit 顺序、无 overlap、无 gap 风险。
4. 不允许删除 `body_main`。
5. 不允许制造两个相同 `unit_id`，除非 operation 明确是 relabel 并有冲突处理。
6. `source_seq_refs` 必须全部存在于 packet/page_text_index 或 source_context。
7. patch 后调用：

```python
post_agent_unit_map = build_unit_map(document_facts, patched_structure_candidates)
```

### 6.4 决策记录

输出 artifact：

```text
agent_t2_overlay.json
agent_decisions.json
```

每个 proposal 决策包含：

```text
proposal_id
round_id
decision = accepted | rejected | open_question
checks[]
target_path
before_hash
after_hash
reason
```

### 6.5 验收门禁

```bash
uv run pytest tests/unit/template_generation_agent/test_agent_reconciler.py \
  tests/unit/template_generation_agent/test_agent_t2_overlay.py -q
```

回归：

```bash
uv run pytest tests/unit/test_t2_unit_map.py \
  tests/unit/test_t2_standard.py \
  tests/contract/test_template_generate.py -q
```

必须证明：

```text
1. accepted T2 overlay 会改变 patched_structure_candidates 并重生 unit_map。
2. invalid source_seq 被 rejected。
3. overlap/gap/body_main deletion 被 rejected。
4. block_range suggestion 已 materialize 到 unit fields，不停留在不可消费字段。
5. agent disabled 时 unit_map hash 与改动前保持一致。
```

## 7. Phase 3：T3 overlay

目标：接受通过校验的 T3 element policy proposal，并 patch `structure_candidates.units[].elements[].candidate_policy`，随后重生 `generation_model` 和 `element_spec`。

### 7.1 改动范围

继续扩展：

```text
src/docfit/template_generation/agent/reconciler.py
src/docfit/template_generation/agent/overlay.py
src/docfit/template_generation/agent/regenerate.py
tests/unit/template_generation_agent/test_agent_t3_overlay.py
```

### 7.2 T3 target bind 规则

AI 只给：

```text
source_seq_refs
render_target_refs
optional text evidence
policy suggestion
```

deterministic code 负责映射到：

```text
target_candidate_id = {unit_id}.{element_id}
```

规则：

```text
0 个候选 -> rejected(C-TARGET-AMBIGUOUS) 或 open_question
1 个候选 -> accepted target
多个候选 -> rejected(C-TARGET-AMBIGUOUS)
不做 best-effort 猜测
stable_id 只在 element_spec 重生后用于 attribution join
```

### 7.3 policy enum

接受前必须在 reconciler 拦截未知 policy，不能依赖 `build_element_spec()` 的 `_canonical_policy()` 兜底成 `fixed`。

最小闭集来自现有 ontology/代码：

```text
fixed
fill
manual_only
generated
remove
```

如现有代码不支持 `remove`，本阶段先把 `remove` proposal rejected，或先新增 executor 不消费的 candidate-only policy；不能让未知值静默通过。

### 7.4 重生路径

```python
patched_structure_candidates = apply_t3_overlay(structure_candidates, agent_t3_overlay)
post_agent_generation_model = build_template_generation_model(
    request,
    structure_candidates=patched_structure_candidates,
)
post_agent_element_spec = build_element_spec(post_agent_generation_model)
```

### 7.5 验收门禁

```bash
uv run pytest tests/unit/template_generation_agent/test_agent_t3_overlay.py \
  tests/unit/test_template_generation_artifacts.py \
  tests/contract/test_template_generate.py -q
```

必须证明：

```text
1. T3 proposal 只能 patch candidate element，不直接写 element_spec。
2. target 不能唯一绑定时 rejected/open_question。
3. 未知 policy 在 reconciler 阶段 rejected。
4. accepted policy patch 后 element_spec 重生结果可见。
5. agent disabled 时 element_spec hash 与改动前保持一致。
```

## 8. Phase 4：T4 hints

目标：T4 AI 输出只落 artifact 和 attribution，不影响生成。

### 8.1 改动范围

新增或扩展：

```text
src/docfit/template_generation/agent/reconciler.py
src/docfit/template_generation/agent/attribution.py
tests/unit/template_generation_agent/test_agent_t4_hints.py
```

输出 artifact：

```text
agent_t4_hints.json
```

支持 hint：

```text
page_policy_hints[]
section_profile_hints[]
page_numbering_hints[]
```

### 8.2 禁止行为

Phase 4 不允许修改：

```text
global_spec
template_spec
generation_plan
executor action
build_manifest
verification_report.status
```

### 8.3 验收门禁

```bash
uv run pytest tests/unit/template_generation_agent/test_agent_t4_hints.py \
  tests/contract/test_template_generate.py -q
```

必须证明：

```text
1. valid hints 被写入 agent_t4_hints.json。
2. invalid source/page binding 被 rejected。
3. 同一输入下 agent off/on 仅 T4 hints artifact 变化，T4 权威产物不变。
4. hints 可被 attribution 引用。
```

## 9. Phase 5：Agent loop

目标：把 replay、tool schema、reconciler、overlay 和 stop condition 串成多轮 harness。

### 9.1 改动范围

新增：

```text
src/docfit/template_generation/agent/tools.py
src/docfit/template_generation/agent/loop.py
tests/unit/template_generation_agent/test_agent_loop.py
```

工具接口：

```text
view_pages(page_nos, mode=clean|annotated)
query_text(source_seq_refs | page_nos | text_query)
submit_t2(unit_candidates, block_candidates, boundary_adjustments)
submit_t3(element_policy_candidates)
submit_t4(page_policy_hints, section_profile_hints, page_numbering_hints)
abstain(reason, open_questions)
```

### 9.2 默认 round 策略

```text
max_rounds = 4

Round 1:
  full-pass overview
  全书低清缩略图 + page index

Round 2:
  T2 focused-pass
  最多 12 页高清

Round 3:
  T3 focused-pass
  最多 12 页高清

Round 4:
  T4 hints 或 verifier 定向修复
  最多 12 页高清
```

### 9.3 stop condition

```text
1. round >= max_rounds
2. AI abstain 且无 open executable proposal
3. changed=False 连续一轮
4. verifier peek 没有产生 next_window_suggestions
5. replay transcript EOF
```

### 9.4 验收门禁

```bash
uv run pytest tests/unit/template_generation_agent/test_agent_loop.py \
  tests/unit/template_generation_agent/test_agent_replay.py -q
```

必须证明：

```text
1. multi-round transcript 可完整跑完。
2. accepted/rejected proposal 都进入 decisions。
3. changed=False 能停止。
4. transcript EOF 不报错。
5. one-shot 等价于 max_rounds=1 transcript。
```

## 10. Phase 6：runner / CLI / artifact 接入

目标：把 Agent Harness 接入真实 `generate_template()`，但默认关闭。

### 10.1 改动范围

修改：

```text
src/docfit/template_generation/runner.py
src/docfit/template_generation/outputs.py
src/docfit/cli/main.py
tests/contract/test_template_generate_agent_default_off.py
tests/contract/test_template_generate_agent_replay.py
```

### 10.2 runner 接口

建议改为：

```python
def generate_template(
    source_template_docx: Path,
    out_dir: Path,
    *,
    strategy: str = DEFAULT_TEMPLATE_GENERATION_STRATEGY,
    debug_root: Path | None = None,
    agent_config: AgentConfig | None = None,
) -> StageResult:
    ...
```

默认：

```text
agent_config is None -> AgentConfig(enabled=False)
```

### 10.3 主流程插入点

插入在 round-0 `structure_candidates`、`unit_map`、`generation_model`、`element_spec` 生成之后，`template_spec` 之前。

伪流程：

```text
document_facts
source_tree
structure_candidates_round0
unit_map_round0
generation_model_round0
element_spec_round0
global_spec_round0

if agent enabled:
  packet/replay/live -> layered submissions
  reconcile proposals
  patched_structure_candidates
  post_agent_unit_map
  post_agent_generation_model
  post_agent_element_spec
  agent_t4_hints
  attribution
else:
  use round0 artifacts

template_spec
plan
execution
build_manifest
verify_template_parse_build
debug snapshot
```

### 10.4 artifact 输出

debug snapshot 增加：

```text
08_agent_render_packet.json
09_agent_transcript.json
10_agent_decisions.json
11_agent_t2_overlay.json
12_agent_t3_overlay.json
13_agent_t4_hints.json
14_agent_attribution.json
```

普通 artifacts 增加：

```text
template_agent_render_packet.json
template_agent_transcript.json
template_agent_decisions.json
agent_t2_overlay.json
agent_t3_overlay.json
agent_t4_hints.json
agent_attribution.json
```

### 10.5 CLI/env 开关

建议：

```text
--agent-replay PATH
--agent-render-packet PATH
--agent-max-rounds N
--agent-provider replay|kimi|minimax
--agent-live
```

环境变量：

```text
DOCFIT_TEMPLATE_AGENT_ENABLED=1
DOCFIT_TEMPLATE_AGENT_PROVIDER=replay|kimi|minimax
DOCFIT_TEMPLATE_AGENT_TRANSCRIPT=/path/to/transcript.json
DOCFIT_TEMPLATE_AGENT_RENDER_PACKET=/path/to/packet.json
```

### 10.6 标准反馈边界

StandardBundle / signed standard 可以作为显式 report/join 输入，但不得作为生成算法输入。

本阶段只允许：

```text
1. debug/report 记录 standard probe delta。
2. verifier peek 给 loop 提供 next_window_suggestions。
3. attribution 记录 standard_probe_delta optional。
```

不允许：

```text
1. 读取 standards/targets/** 后直接指导 AI 修改。
2. 把 standard PASS/FAIL 改成主流程 status 来源。
3. 无 standard 时宣称 standard PASS。
```

### 10.7 验收门禁

```bash
uv run pytest tests/contract/test_template_generate_agent_default_off.py \
  tests/contract/test_template_generate_agent_replay.py \
  tests/contract/test_template_generate.py -q
```

完整回归：

```bash
uv run pytest tests/unit/test_t1_fact_coverage_verifier.py \
  tests/unit/test_t1_structural_facts.py \
  tests/unit/test_t2_unit_map.py \
  tests/unit/test_t2_standard.py \
  tests/unit/test_template_generation_artifacts.py \
  tests/contract/test_template_generate.py -q
```

必须证明：

```text
1. agent_config=None 时现有输出不变。
2. replay agent 可产生 agent artifacts。
3. replay accepted T2/T3 overlay 会改变 post-agent unit_map/element_spec。
4. T4 hints 不改变 global_spec/template_spec/plan。
5. verification_report.status 仍来自 verify_template_parse_build。
6. debug index 记录新增 agent artifacts 的 sha256。
```

## 11. Phase 7：Kimi live transport

目标：用 OpenAI Python SDK 接入 Kimi Coding Plan 的 OpenAI-compatible Chat Completions 接口。该阶段只做手动 eval，不进 CI gate。

### 11.1 依赖策略

`pyproject.toml` 目前没有 `openai` 依赖。建议二选一：

```text
方案 A：optional extra
  [project.optional-dependencies]
  agent-live = ["openai>=2.44.0"]

方案 B：运行时软依赖
  import openai 失败时提示安装，不影响默认测试。
```

更建议方案 B，保持默认安装轻量。

### 11.2 Kimi 实测配置

```python
import os

from openai import OpenAI

client = OpenAI(
    api_key=os.environ["KIMI_API_KEY"],
    base_url="https://api.kimi.com/coding/v1",
    timeout=120,
    default_headers={
        "User-Agent": "claude-cli/2.0.0 (external, darwin)",
        "X-Client-Type": "claude-code",
    },
)
```

固定参数：

```text
base_url = https://api.kimi.com/coding/v1
endpoint = /chat/completions
model = kimi-for-coding
api_key env = KIMI_API_KEY
temperature = 1
```

容易写错：

```text
1. base_url 不是普通 /v1。
2. 域名是 api.kimi.com，不是 api.moonshot.cn。
3. 模型名是 kimi-for-coding。
4. 必须带 User-Agent 和 X-Client-Type。
5. 实测 temperature=0.0 会失败，当前传 1。
```

### 11.3 `<think>` 清理

Kimi 可能在正文前输出 `<think>...</think>`。JSON 解析前统一清理：

```python
import re


def strip_think(content: str) -> str:
    return re.sub(r"<think>.*?</think>\s*", "", content, flags=re.DOTALL | re.I).strip()
```

### 11.4 transport.py 最小接口

```python
class AgentTransport(Protocol):
    def complete_round(
        self,
        *,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        response_format: dict[str, Any] | None,
        max_tokens: int,
    ) -> dict[str, Any]:
        ...
```

Kimi transport：

```text
KimiOpenAICompatibleTransport
  provider = kimi
  model = kimi-for-coding
  base_url = https://api.kimi.com/coding/v1
  temperature = 1
  max_tokens default = 4000
  strip_think before schema validation
```

### 11.5 Live 手动 eval

首轮只跑三校手动 eval：

```text
hunannongye
nannong-undergraduate
pku-graduate
```

每校保存：

```text
agent off run dir
agent replay run dir
agent live run dir
agent_attribution.json
verification_report.json
standard probe report optional
人工检查记录
```

### 11.6 验收门禁

单测只测配置和解析，不打网络：

```bash
uv run pytest tests/unit/template_generation_agent/test_kimi_transport_config.py -q
```

手动命令示例：

```bash
export KIMI_API_KEY="<your-kimi-api-key>"
DOCFIT_TEMPLATE_AGENT_ENABLED=1 \
DOCFIT_TEMPLATE_AGENT_PROVIDER=kimi \
DOCFIT_TEMPLATE_AGENT_RENDER_PACKET=/path/to/template_agent_render_packet.json \
uv run docfit template-generate ...
```

必须证明：

```text
1. 无 openai 包时默认测试不失败。
2. 无 KIMI_API_KEY 时 live transport 给出明确错误。
3. Kimi 返回的 <think> 被清理后再进入 schema validation。
4. live transport 输出和 replay submission 同形。
5. live eval 不修改 CI gate。
```

## 12. 分阶段提交建议

建议每个 Phase 单独提交，避免把 schema、overlay、runner 和 live SDK 混在一个 diff。

```text
Commit 1: add default-off agent config and render packet schema
Commit 2: add layered submission schema and replay transport
Commit 3: add T2 proposal reconciler and overlay regeneration
Commit 4: add T3 policy overlay and target binding
Commit 5: add T4 hints artifact and attribution join
Commit 6: add multi-round loop and tool abstractions
Commit 7: wire agent_config into runner/debug outputs/CLI
Commit 8: add Kimi OpenAI-compatible live transport
```

每个提交的最低要求：

```text
1. 新增测试覆盖本提交行为。
2. agent disabled 回归保持通过。
3. 不修改 T1 semantic boundary。
4. 不把 standards/targets/** 作为生成算法输入。
5. 不引入通用 Agent 框架依赖。
```

## 13. 全局验收矩阵

| 门禁 | 证明方式 | 负责 Phase |
|---|---|---|
| 默认关闭输出不变 | agent_config=None hash/contract test | 6 |
| 零网络 replay | transcript fixture 单测/契约测试 | 1, 5, 6 |
| T1 fact-only | 现有 T1 verifier 回归 | 0-7 |
| AI 输出边界 | schema/reconciler tests | 1-4 |
| T2/T3 只 patch structure_candidates | overlay/regenerate tests | 2-3 |
| T4 只写 hints | T4 hints artifact test | 4 |
| T3 target 唯一绑定 | ambiguous target tests | 3 |
| 未知 enum 被拒绝 | reconciler enum tests | 2-3 |
| verifier 仍是唯一 status | contract test 检查 verification_report | 6 |
| attribution 可 join | attribution diff tests | 4-6 |
| 不新增通用 Agent 框架 | pyproject/import scan | 7 |
| live 必须有 render packet | AgentConfig validation | 0, 7 |
| standards 不进入生成算法 | runner/loop tests + code review | 6 |

## 14. 推荐执行顺序

实际开发顺序不要先接 Kimi。推荐：

```text
1. Phase 0：AgentConfig + packet fixture。
2. Phase 1：schema + replay。
3. Phase 2：T2 overlay，先打通 unit_map 重生。
4. Phase 3：T3 overlay，打通 element_spec 重生。
5. Phase 4：T4 hints 和 attribution。
6. Phase 5：multi-round loop。
7. Phase 6：runner/CLI/debug 输出接入。
8. Phase 7：Kimi live transport 和三校手动 eval。
```

每轮开发前后固定运行：

```bash
git status --short
uv run pytest tests/contract/test_template_generate.py -q
```

涉及 T2/T3 overlay 后加跑：

```bash
uv run pytest tests/unit/test_t2_unit_map.py \
  tests/unit/test_t2_standard.py \
  tests/unit/test_template_generation_artifacts.py -q
```

阶段完成后跑：

```bash
uv run pytest -q
```

## 15. 未决问题

需要在实施前或对应 Phase 内收敛：

```text
Q1 T2 canonical/custom label suggestion 的 trace 字段最终命名。
Q2 agent_attribution 与 verification_report/template_gap_report 的 join 输出文件名。
Q3 产品化阶段是否恢复语义/置信 gate。
Q4 T4 hints 后续是否升级成 T4 overlay，需要另开 plan。
Q5 render packet 是本计划 Phase 0 内最小实现，还是严格依赖 T2 visual pagination 计划。
Q6 T2 operation enum 是否需要 add_unit/relabel_unit/adjust_unit_range/replace_unit_elements 以外的操作。
Q7 T3 target_candidate_id 是否固定为 unit_id.element_id，还是新增 overlay_target_id。
Q8 StandardBundle feedback 是否进入 Plan-01 主线，还是只写 attribution。
Q9 live transport 首轮是否只支持 image+tools，文本 query 工具是否延后。
```

## 16. 最小可交付定义

Plan-01 可以判定完成的最低标准：

```text
1. 默认关闭时，现有模板生成 contract tests 全部通过，输出不变。
2. replay transcript 能驱动 T2 accepted proposal，重生 unit_map。
3. replay transcript 能驱动 T3 accepted proposal，重生 element_spec。
4. replay transcript 能写 T4 hints artifact，且不改变 T4/T5/T6 权威产物。
5. 所有 accepted/rejected/open_question proposal 都有 decisions 和 attribution。
6. debug snapshot 与普通 artifacts 能找到 agent packet/transcript/overlay/hints/attribution。
7. live Kimi transport 可手动运行，但 CI 不依赖网络。
8. T1 仍保持 fact-only，AI 不进入 standards、manifest、hash、status 裁判链路。
```
