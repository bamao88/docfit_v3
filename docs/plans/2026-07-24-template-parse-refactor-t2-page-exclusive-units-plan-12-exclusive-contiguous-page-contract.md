---
status: implemented_in_part
owner: template-generation
stage: T2T3T5T6T7
topic: t2-page-exclusive-units
doc_type: plan
plan_id: T2T3T4-AGENT-PLAN-12
source_issue:
  id: T2T3T4-AGENT-ISSUE-12
  doc: docs/plans/2026-07-24-template-parse-refactor-t2-page-exclusive-units-issue-12-source-boundary-model-conflict.md
previous_plan:
  id: T2T3T4-AGENT-PLAN-11
  doc: docs/plans/2026-07-03-template-parse-refactor-t2t3t4-agent-proposal-plan-11-unit-pagination-alignment.md
related_status:
  - docs/status/active/t2-page-exclusive-unit-contract.md
related_discussion:
  - docs/human/t2-ai-output-contract-discussion.md
  - docs/human/t2-ai-prompt-draft.md
created: 2026-07-24
last_updated: 2026-07-26
---

# T2 Plan 12：独占连续页面单元契约

## Plan Ledger

- Plan status: IMPLEMENTED_IN_PART
- Session scope: t2-ai-only-page-native
- Parent plan: none
- Child plans: none
- Last updated: 2026-07-26
- Current slice: AI-only 页面运行链完成代码收敛，正式/调试入口已隔离；三校付费 MiniMax live 与最终 Word fresh 分页验收已通过，正式 page-gold 评分仍未闭环
- Next action: 把本轮人工复核结果签署为三校 page-native gold，并迁移 school verifier 后重跑完整 judge
- Blocked on: 页面 gold 需要独立人工签署；当前 canonical/signed T2/T3 标准仍是旧契约
- Do not touch from this session: T3 稀疏决策重构、T4 语义、学生内容提取、无关学校原始输入和用户既有改动

Unknown-unknown scout skip reason：Issue 12、Plan 12、T2 discussion docs 和用户
2026-07-25 最新指令已经锁定产品边界、输入、输出、下游和验证矩阵；本轮剩余未知项属于代码事实侦察，不需要再开一轮产品发现。

## 结论

本轮把 T2 顶层单元固定为：

```text
一个 T2 单元拥有一段独占的连续渲染页面。
一页只能属于一个 T2 单元。
下一个 T2 单元一定从下一页开始。
```

这会让 T2 AI 的任务明显变简单：AI 只需要看页图，判断“第几页到第几页是什么单元”。分页策略不再由 AI 猜测，而由程序根据页面区间确定性生成。

T2 生产链只保留 AI 路线。原 code T2 识别、code/AI comparison、bridge、
overlay 和 merged 选择全部退出；程序只负责输入封装、schema 校验、页面区间物化、
固定分页策略和下游传递。

## Preflight

- Preflight status: `APPROVED_AND_IMPLEMENTING`
- Task source: 用户 2026-07-24 关于“独占连续页面、下一个单元一定另起页”的决定
- Canonical source: 本计划
- Route: 批准后通过 durable `intuitive-flow` 实施
- Goal: T2 以独占连续页为唯一边界模型，并让 T3/T5/T6、gold 和 judge 使用同一契约
- Reuse: 现有 sealed L1、真实 render page、page image、page-to-source binding、T2 final/T3/T5/T6 数据链
- Remove/merge: 删除页内 T2 边界、`same_page_allowed`、`shareable_flow` 和 AI 自报分页策略
- New: 只新增页面区间 schema 与确定性 page-to-source materializer；不新增第二套 T2 业务产物
- Expansion trigger: 超长模板需要分窗调用、同一 source 节点真实跨越两个候选单元、或产品重新允许同页多单元时，必须重新审批

批准后执行入口：

```text
/goal execute docs/plans/2026-07-24-template-parse-refactor-t2-page-exclusive-units-plan-12-exclusive-contiguous-page-contract.md with intuitive-flow
```

## Execution Contract

### Target Capability

完成后，系统必须具备以下能力：

1. T2 AI 按页面顺序识别单元 ID、名称和包含首尾的页面区间。
2. 每个真实渲染页恰好被一个 T2 单元认领，单元之间无页内切分、无页面 gap、无页面 overlap。
3. 程序把页面区间确定性映射为 T3 需要的 `source_seq_refs/source_refs`，不让 AI 估算 source 身份。
4. 程序确定性生成 T2 final 的分页策略：第一单元从文档开头开始，后续单元全部另起页，所有单元独占连续页面范围。
5. T3/T5/T6 只消费通过该不变量校验的 T2 final；任何旧路线都不能重新引入同页单元。
6. gold、route-eval、verifier 和 judge 能分别检查 AI 页面判断、程序绑定和最终 Word 分页效果。
7. T2 生产链只有 MiniMax AI 输出一个候选，不再生成或选择 code raw、comparison、overlay 或 merged route。

### Non-Goals

1. 不要求一个单元必须压缩在一页内，也不通过字体、间距、边距或行高压缩内容。
2. 不让 T2 判断元素 Keep/Fill/Delete、槽位、字段、页眉页脚、页码或具体 Word 动作。
3. 不把页内章节、表格小块或多个视觉块重新提升为 T2 顶层单元；这些由 T3 在单元内部处理。
4. 不改变默认 provider 方向；T2 live 继续以 MiniMax 为默认调用路线。
5. 不在本轮引入长期双 schema；旧 replay/fixture 只允许一次性迁移，不保留永久兼容分支。
6. 不在未看到真实渲染页时猜测页面边界；没有 real render 的 T2 应明确不可用。
7. 不为旧 code T2 路线保留长期兼容、fallback 或双写产物。

### Anti-Degradation Rules

1. 禁止让 AI 同时输出页面边界和 source 边界，再由程序“择优”使用。
2. 禁止让 AI 输出固定 `page_policy`，造成看似完整但实际冗余的判断字段。
3. 禁止把没有 body node 的空白页静默丢弃；它仍必须归属某个页面区间。
4. 禁止把 `start_page=end_page` 解释为内容必须永久保持一页。
5. 禁止 code route、merge overlay 或旧 replay 产生同页跨 unit 后仍发布 final。
6. 禁止只验证 JSON/schema，不检查 T3 消费、T6 动作和最终 DOCX 效果。
7. 禁止通过修改 gold 迎合一次模型输出；页面 gold 必须基于人工审核的真实 render。
8. 禁止在 AI 失败时回退到 code T2；失败必须显式标记 T2 不可用。

## 1. 输出契约怎么变

### 1.1 T2 AI 原始输出

推荐把 AI 输出收敛为：

```json
{
  "units": [
    {
      "unit_id": "cover",
      "unit_name": "封面",
      "boundary": {
        "start_page": 1,
        "end_page": 1
      }
    },
    {
      "unit_id": "abstract_cn",
      "unit_name": "中文摘要",
      "boundary": {
        "start_page": 2,
        "end_page": 3
      }
    },
    {
      "unit_id": "body_main",
      "unit_name": "正文",
      "boundary": {
        "start_page": 4,
        "end_page": 18
      }
    }
  ]
}
```

AI 每个单元只输出三个字段：

- `unit_id`：开放生成、机器可读、同一文档内唯一的语义 ID；
- `unit_name`：优先使用模板可见标题，否则给出简洁功能名称；
- `boundary.start_page/end_page`：包含首尾的 1-based 真实渲染页序号。

AI 不再输出：

- `start_source_seq/end_source_seq`；
- `source_seq_refs/source_refs`；
- `page_policy`；
- `same_page_allowed/shareable_flow`；
- `confidence/reason/evidence` 等核心契约外字段。

原因是：source 身份可以由页面绑定确定性展开；分页策略已经由产品不变量固定，不需要 AI 重复判断。

### 1.2 T2 正式 `unit_map`

正式 T2 final 仍保留用户已确认的四类核心业务信息：

```json
{
  "units": [
    {
      "unit_id": "abstract_cn",
      "unit_name": "中文摘要",
      "boundary": {
        "start_page": 2,
        "end_page": 3
      },
      "page_policy": {
        "start": "new_page",
        "scope": "page_range_exclusive"
      }
    }
  ]
}
```

其中 `page_policy` 由程序生成，不来自 AI：

| 条件 | `page_policy.start` | `page_policy.scope` |
| --- | --- | --- |
| 第一个单元 | `document_start` | `page_range_exclusive` |
| 后续任意单元 | `new_page` | `page_range_exclusive` |

`scope` 统一使用 `page_range_exclusive`，包括当前只占一页的单元。它表示“这个单元拥有自己的连续页面范围”，不是“必须固定成一页”。因此不再使用 `single_page_exclusive` 来推导强制 keep-together。

为了让 T3 和执行链继续回查 L1，materializer 可以在正式 artifact 中保留程序派生的技术绑定，例如：

- `order`；
- `page_refs`；
- `source_seq_refs`；
- `source_refs`；
- `source_seq_range`。

这些是 transport/trace 字段，不是 AI 判断，也不改变上面的四类核心业务信息。

### 1.3 退出的旧取值

T2 canonical final 不再产生：

- `page_policy.start=same_page_allowed`；
- `page_policy.start=unknown`；
- `page_policy.scope=single_page_exclusive`；
- `page_policy.scope=shareable_flow`；
- `page_policy.scope=unknown`。

语义不确定通过 `unit_id=unknown_unit` 或人工复核表达；页面所有权和起页规则不能未知。

## 2. 页面边界不变量

设真实渲染页数为 `N`，排序后的单元为 `u1...uk`：

1. `u1.start_page = 1`；
2. `uk.end_page = N`；
3. 每个单元满足 `1 <= start_page <= end_page <= N`；
4. 对所有相邻单元，`u(i+1).start_page = ui.end_page + 1`；
5. 每页恰好属于一个单元；
6. unit 数组顺序就是文档页面顺序；
7. 单元之间不能在同一页内切换；
8. 无法判断语义的连续页面仍输出 `unknown_unit`，不能丢页。

以下输出必须被 schema/materializer 拒绝，不能进入 merged/final：

- 页码越界；
- 页面 gap；
- 页面 overlap；
- 同一页开始两个单元；
- 非首单元从前一单元结束页开始；
- AI 输出 source 边界或自报 page policy；
- real render/page image 不可用。

## 3. 同页多语义块怎么处理

新的 T2 原子是“页面级工作窗口”，不是最小语义块。

例如同一页同时出现“原创性声明”和“使用授权声明”：

- 旧逻辑：两个 T2 单元，第二个可以 `same_page_allowed`；
- 新逻辑：一个组合 T2 单元，例如
  `unit_id=originality_and_authorization_statements`、
  `unit_name=原创性声明与使用授权声明`；
- T3：仍可在这个单元内部把两个标题、正文、签名区分别识别为元素。

正文中的章、节、小节同理，继续属于同一个 `body_main` 页面区间。

## 4. T2 输入契约

### 4.1 消息顺序

模型应按页面顺序接收：

```text
T2 任务说明和固定不变量
→ page 1 图片
→ page 1 客观事实
→ page 2 图片
→ page 2 客观事实
→ ...
→ 严格输出 schema
```

不再先发送一份以 `source_seq` 为主的全文 JSON，让模型先按文本块切分。

### 4.2 每页允许输入的事实

每个 page packet 只包含客观信息：

- `page_no/page_ref`；
- 页面图片及其 hash、宽高；
- 本页可见 body 节点的 `source_seq/source_ref/text/kind`；
- 节点在页内的 bbox 或阅读顺序；
- 本页是否存在真实 page/section break 的机械事实；
- render completeness 和无法绑定对象。

不得包含：

- 预判的 unit 名称、类型或边界；
- code route、merged、gold、standard 或 judge 结论；
- `page_policy`、元素 policy、role 或 fill source；
- 根据关键词生成的语义摘要。

图片负责让 AI 判断页面组；JSON 只负责补足小字可读性和页面到 L1 的客观绑定。

### 4.3 real render 前置条件

页面是本契约的权威坐标，因此：

- 只有 `real_render` 且页图与 page binding hash 一致时才能运行 T2；
- projection fallback 不得估算页号后继续发布 T2 final；
- 页图缺失、页数不一致或 binding 不完整时，T2 availability 必须明确降级。

## 5. 程序物化规则

AI 输出通过页面不变量校验后，程序执行：

```text
page range
  → 展开 page_refs
  → 读取每页 body binding
  → 按 L1 顺序去重并生成 source_seq_refs/source_refs
  → 生成 source_seq_range
  → 派生 page_policy
  → 发布 T2 final
```

边界处理：

- 页眉、页脚和重复页码不进入 unit 的 body `source_seq_refs`；
- 空白页保留页面所有权，但不伪造 source 节点；
- 同一个 body 节点跨多页时可以在同一 unit 内去重；
- 如果同一个 body 节点跨越两个候选 unit page range，materializer 必须拒绝发布或进入人工复核，不能复制给两个单元；
- page-to-source 绑定不完整时不能用相邻文本猜测。

## 6. Route 与 final 规则

1. AI raw 使用本计划的 page-native schema。
2. code raw、comparison、bridge、overlay 和 merged 选择从 T2 生产链删除。
3. 旧 replay 只允许一次性迁移为新的 AI page-native schema，不保留运行时兼容分支。
4. final 只来自通过完整页面覆盖校验的 AI 候选。
5. AI 不可用时，T2 必须明确 `NOT_AVAILABLE/PARTIAL`，不能发布 code fallback 或旧 source-granular final。

## 7. 下游迁移

### T3

- unit root 来自 T2 page range 物化后的 source bindings；
- 同一页不能产生多个 T3 unit root；
- T3 继续负责组合单元内更细的标题、表单块、说明和字段判断。

### T5

- 无损保留 T2 final 的页面区间、派生 source bindings 和固定 page policy；
- 不重新推断是否允许同页。

### T6

- 第一个单元不插入多余 page break；
- 每个后续单元都计划一个可验证的“另起页”动作；
- T4 如果要求 section break，可由 section break 满足同一边界，避免重复 page break；
- 不因源页面区间长度为 1 而自动设置 whole-unit keep-together；
- 最终 manifest 保留 unit page range、动作和 fresh DOCX effect 的对应关系。

### T7 / judge

- T2：判断页面区间和语义名称是否正确；
- materializer：判断 page-to-source 绑定是否完整、唯一；
- T5：判断是否无损传递；
- T6：判断每个非首单元是否执行另起页；
- POST_T6：判断最终 Word 是否实际出现正确单元起页效果。

## 8. Gold 与指标

T2 gold 的主坐标改为真实渲染页：

```yaml
expected:
  units:
    - unit_id: abstract_cn
      unit_name: 中文摘要
      boundary:
        start_page: 2
        end_page: 3
```

主指标：

- unit precision / recall / F1；
- unit order exact match；
- page boundary exact match；
- page boundary F1；
- page ownership coverage；
- page overlap/gap count；
- unit name/ID mismatch。

派生检查：

- page range 到 `source_seq_refs` 的绑定准确率；
- T3 unit root 与 T2 final 一致性；
- 固定 `page_policy` 派生正确性；
- T6 非首单元另起页动作与最终效果覆盖率。

`page_policy` 不再作为 AI 准确率指标，因为它没有模型判断空间；它改为确定性契约测试。

## 9. Implementation Checklist

### A. 契约和 Prompt

- [x] 更新 `docs/human/t2-ai-output-contract-discussion.md`，把 source 边界和可变 page policy 改为页面边界与程序派生策略。
- [x] 更新 `docs/human/t2-ai-prompt-draft.md`，改成页图优先、页面组判断。
- [x] 同步 `docs/current/template-generation-architecture.md` 和测试契约。

### B. T2 输入

- [x] 建立按页排序的 page packet，图片在前、客观 page facts 随后。
- [x] 增加 real render、page count、image hash、binding completeness 前置校验。
- [x] 对最终 T2 evidence 运行语义 firewall。

### C. Schema 与 materializer

- [x] 新增严格 `units[].boundary.start_page/end_page` schema。
- [x] 删除 AI 输出中的 source refs 和 page policy。
- [x] 实现页面完整覆盖、相邻、越界、重叠和 gap 校验。
- [x] 实现 page-to-source 确定性物化与跨边界节点冲突检查。
- [x] 派生固定 page policy 和现有下游所需 trace 字段。

### D. Route 与下游

- [x] 不迁移 comparison/overlay/merged 坐标，直接删除这些 T2 路线。
- [x] 删除 T2 code raw、comparison、bridge、overlay 和 merged 路由及其生产调用方。
- [x] 禁止旧 source-granular 候选或 code fallback 进入 final。
- [x] 更新 T3 hierarchical input 的 unit root 构造。
- [x] 更新 T5 传递和 T6 非首单元起页执行。
- [x] 删除 `same_page_allowed/shareable_flow/single_page_exclusive` 的 T2 生产消费分支。

### E. Gold、测试和文档

- [ ] 以人工审核 render 为三校 T2 gold 增加 page range。
- [ ] 更新 T2 standard verifier 的学校页面 gold 评分；AI route-eval、judge 路由和报告已改为单一 AI 页面边界。
- [x] 迁移 replay/fixture，不保留运行时双 schema。
- [x] 补同页多语义块、空白页、跨页节点、缺图、page gap/overlap 等反例。
- [x] 扫描生产旧字段和旁路消费者；旧学校 gold/verifier 作为待迁移项单独保留。

### 当前实现证据（2026-07-25）

- `python -m compileall`：模板生成、harness、convert 和 CLI 相关模块通过；
- `pytest -q tests/unit`：275 passed；
- T2 关键 contract 集：22 passed；
- `pytest -q tests/contract`：exit 0；
- 生产残留扫描：没有 T2 code/merged 产物、旧分页取值或旧 structure candidate 消费；仅保留 evidence firewall 中对旧字段名的拒绝规则；
- 截至 2026-07-25 尚未运行：MiniMax live、三校 page-gold judge、三校最终
  Word fresh 分页验收；下一节记录了 2026-07-26 的后续执行结果。

### 三校 live 与最终 Word 证据（2026-07-26）

- 付费 MiniMax live：三校各 1 次，共 3 次，provider 均为 `minimax`、model
  均为 `MiniMax-M3`，`cache_hit=0`、`failure=0`；
- T2 schema 不变量：三校共 56 页、26 个页面组，完整覆盖、连续、无重叠、
  unit ID 唯一；
- 人工视觉复核暂定结果：页面组区间 26/26、页面归属 56/56、相邻页切分判断
  53/53、ID/名称语义 26/26；
- 最终 Word fresh render：湖南农业大学 17→17 页、南京农业大学 12→12 页、
  北京大学 27→27 页；23 个非首单元边界全部为 `already_satisfied`，未重复
  插入分页符，也未新增空白页；
- 自动化回归：`tests/unit` 293 passed；Plan 12 相关 contract 21 passed；
  template-generation 与 harness compileall 通过；
- 详细报告：
  `test_outputs/debug/template_generation/20260726_t2_page_live_validation/validation_report.md`。

以上准确率是人工视觉复核的暂定口径，不替代正式 school gold。当前完整 judge
仍因 page-native T2 gold / verifier 和 T3 gold contract 未迁移而失败，因此本计划
继续保持 `implemented_in_part`。

### 代码收敛复查（2026-07-26）

- 完整模板生成只通过 `observation_runtime.py` 运行 T2/T3/T4 observation；
  `observation_stage.py` 只承载命名单阶段调试，二者仅共享
  `observation_providers.py` 的模型调用能力；
- T2 正式 final 统一由 `t2_ai.publish_t2_ai_final` 发布；调试入口包装普通
  `unit_map` 时明确标记 `producer_mode=debug_fixture`，正式 runtime 不导入该适配器；
- page packet 新增重复页图和页图声明 hash 校验；T2 开放 `unit_id` 后，下游目录
  判断基于单元名称，系统正文槽位归属 `document_body`，不再假装属于固定 T2 ID；
- 删除旧 T2 taxonomy、overlay/attribution、混合 T2/T4 transcript、整单元
  copy-only 分支和旧 `--agent-*` 配置入口；
- `pytest -q`：350 passed；正式/调试模块边界与 T2 关键切片：45 passed；
  `git diff --check` 与 `python -m compileall -q src tests` 均通过。

## 10. Completion Signals

必须同时满足：

1. T2 AI raw 只输出 ID、名称和页面首尾，不输出 source 边界或 page policy。
2. 三校每个真实渲染页恰好被一个 unit range 覆盖，gap/overlap 为 0。
3. T2 final 的 source bindings 全部由 page binding 派生，跨 unit 重复 source 节点为 0。
4. T2 final 只来自 AI 页面分组；不存在 code raw、comparison、overlay 或 merged 选择残留。
5. T3 unit roots 与 T2 final 页面区间一一对应，不存在同页多个 unit root。
6. T5 无损保留，T6 对每个非首单元产生已执行或有明确失败原因的起页结果。
7. replay 与 MiniMax live T2 都使用同一 schema；live 结果达到批准的页面边界门槛。
8. 三校最终 DOCX fresh observation 证明非首单元实际另起页，没有重复 break。
9. 旧字段和 code-route 残留扫描只允许历史文档或迁移 fixture，生产 schema/Prompt/消费者为 0。

## 11. Verification Matrix

| Gate | Command / Evidence | Required Result |
| --- | --- | --- |
| schema/materializer unit | `uv run pytest -q tests/unit/test_t2_ai.py` | page range 合法路径通过；gap/overlap/越界/旧字段、缺图和跨 unit source 反例失败 |
| T2 unit map | `uv run pytest -q tests/unit/test_t2_ai.py tests/unit/test_t2_standard.py` | 页面覆盖与派生 source binding 正确；学校 page-gold diff 仍待 verifier 迁移 |
| T2 route | `uv run pytest -q tests/unit/template_generation_agent/test_agent_observation_pipeline.py tests/unit/template_generation_agent/test_agent_observation_eval.py tests/contract/test_template_generate.py` | 只发布 AI final；code/merged 产物不存在 |
| T3/T5/T6 contract | `uv run pytest -q tests/unit/template_generation_agent/test_agent_t3_hierarchical_input.py tests/unit/test_template_generation_artifacts.py tests/unit/test_template_generation_stage_verifiers.py` | T3 root、T5 传递、T6 起页动作同一链路 |
| contract | `uv run pytest -q tests/contract/test_template_generate.py tests/contract/test_template_generate_agent_replay.py tests/contract/test_template_generation_standard_judge.py` | replay、artifact、judge 使用新契约 |
| static/residual | `uv run python -m compileall -q src/docfit/template_generation src/docfit/harness`；`rg` 扫描旧 T2 policy 分支 | 编译通过；生产消费残留为 0 |
| three-school replay | 三校 `template generate --ai replay` + `template-generation-judge` | 页面 gap/overlap=0，T3/T5/T6 无 silent drop |
| MiniMax live T2 | `MINIMAX_API_KEY=... uv run docfit template stage t2 --run <run> --out <out>` | 三校均产生新 schema；页面区间达到批准门槛 |
| final Word | 三校 `template verify` + fresh DOCX observation/template-gap | 所有非首单元另起页，无重复 break 或页面共享 |

MiniMax live 调用需要凭据和费用授权；它是完整完成门禁。若当前环境不能运行，只能标记
`BLOCKED_NEEDS_LOCAL_VALIDATION`，不能把实现宣称为 verified。

## 12. Residual Policy

- 任一页面未归属、重复归属或跨 unit source 冲突：`implemented_in_part`，不得发布 final。
- replay 已通过但 MiniMax live 未验证：`BLOCKED_NEEDS_LOCAL_VALIDATION`。
- 只有个别学校需要同页多单元才能表达：停止实施并回到产品决策，不增加隐藏例外。
- 超长模板超过 provider 图像/上下文上限：创建后续 issue 设计 page-window 与 overlap stitching，不在本计划中临时截断页面。
- 所有完成状态必须同步本计划、Issue 12、`docs/status/active/t2-page-exclusive-unit-contract.md` 和索引。
