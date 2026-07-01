---
status: draft
owner: template-generation
stage: T2T3T4
topic: module1-observation-input-followups
doc_type: issue
issue_id: T2T3T4-AGENT-MODULE1-ISSUE-05
issue_sequence: 05
previous_issue:
  id: T2T3T4-AGENT-ISSUE-04
  doc: docs/plans/2026-06-29-template-parse-refactor-t2t3t4-agent-proposal-issue-04-code-generation-bridge-execution.md
  status: implemented
previous_optimization:
  doc: docs/plans/template-parse-refactor-t2t3t4-agent-proposal-plan-04-ai-code-generation-bridge.md
  summary: Module 1 独立同形产物契约见附录 A.3；代码侧已有 observation_loop / evidence / observation_tools（replay 核心），live 与 CLI 仍 out of scope。
next_plan: none
created: 2026-06-30
last_updated: 2026-06-30
cross_issue:
  - docs/plans/2026-06-30-template-parse-refactor-t3-element-policy-issue-03-within-paragraph-run-split.md
related_code:
  - src/docfit/template_generation/agent/evidence.py
  - src/docfit/template_generation/agent/observation_prompts.py
  - src/docfit/template_generation/agent/observation_tools.py
  - src/docfit/template_generation/agent/tools.py
  - src/docfit/template_generation/agent/observation_loop.py
upstream_plan: docs/plans/template-parse-refactor-t2t3t4-agent-proposal-plan-04-ai-code-generation-bridge.md
---

# Module 1 后续待办：阶段输入策略与工具说明

本文记录 Module 1（AI 独立同形产物）在**阶段输入设计**上的后续讨论项，并附上当前实现口径与 agent 工具人话说明，便于和产品/实现拉齐。

> 范围：Module 1 第一相（`ai_unit_observation` / `ai_element_observation` / `ai_layout_observation`）。
> 不展开 Module 2 overlay-on-parse 的 prompt 策略（除非工具层复用）。

---

## 后续 To-do（待讨论 / 待验证）

### TODO-1：T2 是否改为「页图优先 + 全文索引交叉验证」

**产品想法（2026-06-30）**

- T2 认单元时，AI 的**主输入**可能应以**视觉页图**为主：先翻页看图，形成章节/区块的粗判断。
- 看图之后，再用**整份文档的识别索引**（`page_text_index` / `query_text`）做**交叉验证**：把视觉判断绑到 `source_seq`、核对标题文字、边界是否连续。
- 动机：若首轮 prompt 直接塞全文逐段清单，token 量大，模型容易被淹没；看图对「大块结构」可能更省力。
- **尚未定论**：这是否优于现状，需要后续用 hunannongye 等样本做 A/B（vision-first vs text-first vs 混合），再写验收口径。

**当前实现（现状）**

| 维度 | 现状 |
| --- | --- |
| T2 证据主形态 | `build_t2_evidence`：以 **`rows` 全文压缩清单**为主（每 `source_seq` 一行：`text` + `style` + `page_no` + 锚点），附带 `page_thumbnails` 引用 |
| 页图角色 | **辅助**：`page_thumbnails` 在证据视图里；`observation_tools.STAGE_TOOL_POLICY` 规定 T2 为 `query_text` **必**、`view_pages` **选** |
| 交叉验证 | **未显式建模**：没有「先 vision pass → 再 text audit」的两相合同；模型可自行先调 `view_pages` 再 `query_text`，但 prompt 未强制该顺序 |
| prompt 压缩 | Module 2 live 路径曾对过大 packet 做 compact view；Module 1 replay 的 T2 evidence 目前是全量 `rows`（随文档变长） |

**建议的后续动作（讨论后再定）**

```text
1. 起草 T2 vision-first prompt 合同草案（第一轮只给页图 + 页级摘要；第二轮只允许 query_text 绑定 source_seq）。
2. 用同一 render packet 跑 text-first（现状）vs vision-first（草案）replay/live 对比：coverage、unknown 率、人工可读性。
3. 若 vision-first 采纳：更新 evidence.py / observation_prompts.py / STAGE_TOOL_POLICY，并补单测与 issue 验收门禁。
```

**验收门禁（草案）**

```text
- T2 产物仍满足 coverage 不变量（owned ∪ unknown = total）。
- 每条非 unknown item 必须有可反查的 evidence_refs（含 source_seq 或 page_no+render_target）。
- vision-first 不得降低防火墙：仍禁止代码阶段结论字段进入证据视图。
```

---

### TODO-2：T4 版面任务应带入 T2 单元识别结果

**产品想法（2026-06-30）**

- T4 判全局版面（分节、页眉脚、页码等）时，应把 **T2 已认出的单元信息**一并提供给 AI。
- 动机：版面规则常与「封面 / 摘要 / 正文 / 参考文献」等单元边界相关；只有页图 + 位置索引，缺少语义单元上下文，模型难以解释「这一节的页码从哪开始」。

**当前实现（现状）**

| 维度 | 现状 |
| --- | --- |
| T4 证据 | `build_t4_evidence`：`page_images` + `page_layout_index`（`page_no` / `bbox` / `page_top_ratio` / `render_target_id`） |
| T2 产物是否进入 T4 | **未进入**：`observation_loop` 跑完 T2/T3 后直接 `materialize_layout_observation(transcript.t4)`，T4 evidence 构建**不读取** `ai_unit_observation` |
| 计划原文 | plan-04 A.3 写 T4 = 「真实页图 + 页眉脚/sections/numbering 事实」；未明确要求注入 AI-T2 units，但与本 TODO 不冲突 |
| 防火墙 | 可带入的是 **AI 自己的** `ai_unit_observation.items`（Module 1 上游），不是代码 `unit_map` |

**建议的后续动作（讨论后再定）**

```text
1. 定义 T4 可消费的 T2 字段白名单（例如 unit_id、source_seq_refs、page_start、confidence、evidence_refs），仍走 assert_firewall_clean。
2. 扩展 build_t4_evidence(packet, ai_unit_observation=...) 或在 observation_prompts 装配层合并 unit_context 摘要。
3. 评估：T2 错误是否会误导 T4（级联风险）→ quality_report 记录 window_source / demotion 链。
4. 补 replay fixture：带单元边界的模板，验证 T4 section 边界与 T2 unit 对齐案例。
```

**验收门禁（草案）**

```text
- T4 evidence 含 ai_unit_observation 摘要时，不得含代码 structure_candidates / unit_map。
- abstain 规则不变：无 real_render 仍强制 abstain。
- 标准裁判 / 人工可核对：section 边界与 T2 unit 的 page/source_seq 是否一致或可解释。
```

---

### TODO-3：T3 段内未按 run 拆分（占位 vs 括号格式说明）— 见 T3 issue-03

**问题（2026-06-30 讨论确认）**

- 同一 `<w:p>`（一个 `source_seq`）内，模板占位与 `（小二黑体加粗）` 等格式说明已是不同 `runs[]`，但 T3 仍合成一个 `fixed` element；annotated 一框、AI `query_text` 一行。
- **不是** T1 / `source_seq` 按段落编号错了；**是** T3 未消费 `logical_run_ids` 做段内元素化（计划归位 T3，代码未接）。

**canonical issue**

- [`2026-06-30-template-parse-refactor-t3-element-policy-issue-03-within-paragraph-run-split.md`](./2026-06-30-template-parse-refactor-t3-element-policy-issue-03-within-paragraph-run-split.md)

**连带**

- Module 1 T3 evidence、annotated 红框粒度可在 T3 段内拆分落地后再评估是否细化。

---

## 附录 A：Agent 工具人话说明（Module 1 / Module 2 共用取证层）

工具不是「魔法 API」，而是**让模型按需从渲染包里取证据**，避免首轮 prompt 塞满整份文档。

实现入口：`src/docfit/template_generation/agent/tools.py`（`execute_agent_tool_call`）。
Module 1 终止工具另见 `observation_tools.py`（`submit_unit_observation` 等，与 Module 2 的 `submit_t2` **不是同一套**）。

### 1. `query_text` — 查原文索引

**干什么**：在渲染包的 `page_text_index` 里**搜索/取出**段落记录（每条 = 一个 `source_seq`）。

**模型怎么调用**（参数三选一或组合）：

```json
{
  "source_seq_refs": [3, 4, 5],
  "page_nos": [1, 2],
  "text_query": "摘要"
}
```

**返回什么**（每条 match）：

```text
source_seq, source_ref, text（完整可见文字）, page_no, bbox, render_target_id, render_binding_status
```

**限制**：最多返回 50 条（`truncated: true` 表示还有更多）。

**典型用途**

- T2：看图怀疑某页是封面后，用 `page_nos: [1]` 或 `text_query: "学校"` 拉出对应段落，再绑 `source_seq` 写进 observation。
- T3：在单元窗口内精确核对某段是下划线占位还是固定文字。

**不是什么**：不是去网上搜，不是读代码的 `unit_map`，不是改文件；只是**只读查询** packet 里 T1 已抽好的文本索引。

---

### 2. `view_pages` — 看页图引用

**干什么**：按页码取**已渲染好的页面图片**元数据（路径、sha256、宽高等），`mode` 可选 `clean`（干净截图）或 `annotated`（带标注）。

**模型怎么调用**：

```json
{
  "page_nos": [1, 2, 3],
  "mode": "clean"
}
```

**返回什么**：每页 `{ page_no, artifact, available }`；`available: false` 表示该页没有图（未 real_render 或渲染失败）。

**典型用途**

- T2（可选）：先浏览结构布局。
- T4（必）：判页眉页脚、页码位置、分节视觉边界。

**不是什么**：工具返回的是**图片文件引用**，不是把像素塞进 chat；具体多模态怎么喂模型由 transport/厂商 API 决定。无 `real_render` 时 T4 应 abstain。

---

### 3. 终止工具 — 「交卷」

| 路线 | 工具名 | 交什么 |
| --- | --- | --- |
| **Module 1** | `submit_unit_observation` / `submit_element_observation` / `submit_layout_observation` | 三份**独立同形**完整产物（镜像 unit_map / element_spec / global_spec） |
| **Module 1** | `abstain` | 本阶段弃权 + reason / open_questions |
| **Module 2** | `submit_t2` / `submit_t3` / `submit_t4` | **建议清单** layered submission（在代码结果上提改动） |
| **Module 2** | `abstain` | 同上 |

Module 2 另有 transport 层 **JSON finalizer**：模型不调 submit 工具时，可再要一轮只返回 JSON 的交卷（见 `transport.py`）。

---

### 4. 各阶段工具策略（计划 + 代码）

| 阶段 | query_text | view_pages | 终止工具 |
| --- | --- | --- | --- |
| T2（Module 1） | 必 | 选 | `submit_unit_observation` / `abstain` |
| T3（Module 1） | 必 | — | `submit_element_observation` / `abstain` |
| T4（Module 1） | — | 必 | `submit_layout_observation` / `abstain` |
| Module 2 staged | 按 prompt 建议 | T4 相关 pass 用 | `submit_t2/t3/t4` / `abstain` |

---

## 附录 B：与 plan-04 的衔接

- 本文 **不替代** `template-parse-refactor-t2t3t4-agent-proposal-plan-04-ai-code-generation-bridge.md`；仅记录 Module 1 输入策略的**开放待办**。
- TODO-1 / TODO-2 结论落地后，应回写 plan-04 附录 A.3 的「三 scope」描述，并在此文 frontmatter 更新 `status` 或链到新的 optimization plan。

---

## 变更记录

| 日期 | 说明 |
| --- | --- |
| 2026-06-30 | 初稿：记录 T2 vision-first 想法、T4 带入 T2 单元想法、现状对照、工具附录 |
| 2026-06-30 | TODO-3：交叉引用 T3 issue-03（段内 run 未拆分导致占位与格式说明绑死） |
