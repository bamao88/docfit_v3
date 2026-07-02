---

## status: draft_for_discussion
owner: template-generation
stage: T2T3T4
topic: module1-observation-dataflow-alignment
doc_type: design_discussion
created: 2026-07-01
last_updated: 2026-07-01
purpose: 在改任何代码前，逐条对齐 Module 1 观察流水线每个阶段“应该拿到什么输入、产出什么、防火墙怎么保持”，把当前断点摊开，供人工确认/否决。
related:
  - docs/plans/template-parse-refactor-t2t3t4-agent-proposal-plan-04-ai-code-generation-bridge.md  # Module 1/2 契约与 A.3
  - docs/plans/2026-06-30-template-parse-refactor-t2t3t4-agent-module1-issue-05-observation-input-followups.md
related_code:
  - src/docfit/template_generation/agent/packet.py            # 渲染包 + 渲染管线(docx→pdf→png)
  - src/docfit/template_generation/agent/evidence.py          # 三 scope clean evidence + 防火墙
  - src/docfit/template_generation/agent/observation_loop.py  # 三阶段编排
  - src/docfit/template_generation/agent/observation_eval.py  # 阶段准确率评测
  - scripts/observe_live.py                                   # 端到端 runner
standards:
  - standards/targets//v1/template_generation/t2_unit_pagination.standard.yaml
  - standards/targets//v1/template_generation/t3_element_policy.standard.yaml
  - standards/targets//v1/template_generation/t4_global_layout.standard.yaml



# Module 1 观察流水线：目标数据流对齐（讨论稿）

> 本文**不是执行计划**，是把当前真实数据流的断点摊开、把目标数据流逐条列出，供你确认/否决。
> 每个「决策点 Dn」都需要你拍板；拍完板再落实施计划。



## 1. 当前真实数据流（✅ 接上 / ✗ 断的 / ⚠️ 有产出但存疑）

```
document_facts (T1 真实事实)
 ├─ page_text_index(文本+seq+page) ──→ T2 证据(全文压缩) ──→ ai_unit_observation ✅
 │                                              │
 │                        (AI 自己的 T2 单元→窗口)──→ T3 证据(单元窗口) ──→ ai_element_observation ⚠️
 │                                                              （产出了，但正确性无法验证，见 §4）
 ├─ data.sections / headers_footers / numbering ──✗── 没进 packet、没喂 T4
 ├─ 源 docx ──✗── observe_live 没传去渲染 ──✗── 无页图(projection_fallback)
 └─ ai_unit_observation ──✗── 没传给 T4
                                    ↓
                          T4 证据几乎为空 → 强制 abstain ✗ → 不可评
```

关键事实（已用代码/命令核实）：

- 渲染管线在 `packet.py._build_real_render_artifacts` 里是**完整的**（docx→pdf(soffice)→png(pdftoppm)→版面(pdftotext)），三个工具本机**全都装了**。缺的只是 `observe_live` 把源 docx + render 目录传进去。
- `build_t4_evidence` 只投 `page_layout_index`(图派生) + page_images；**不看** T1 的 sections/headers/numbering。
- packet 里**没有** sections/headers/numbering 键。
- T4 拿不到 `ai_unit_observation`（T3 拿得到，靠窗口）。

。、÷÷

## 2. 逐阶段：实际拿到 vs 应该拿到


| 阶段        | 现在拿到的输入                           | 目标输入                                                                  | 产出                     | 防火墙口径                                         |
| --------- | --------------------------------- | --------------------------------------------------------------------- | ---------------------- | --------------------------------------------- |
| **T2 单元** | page_text_index（文本+seq+page+样式事实） | 不变                                                                    | ai_unit_observation    | 只给事实，不给代码结论（现状 OK）                            |
| **T3 元素** | AI 自己 T2 单元切的窗口证据                 | 不变                                                                    | ai_element_observation | 只给窗口内事实（现状 OK）                                |
| **T4 版式** | 几乎空（图派生 index，投影回退下为空）            | ① T1 分节/页眉脚/编号/页面设置事实 ② AI 的 T2 单元（做 section↔unit 绑定） ③ 真实页图（视觉子项，可选） | ai_layout_observation  | 分节/页眉脚/编号是**确定性事实**，应可给；但需确认其中不夹带策略结论字段（见 D4） |




## 3. 三个结构缺口（对应你的三个问题）

- **G1 图接线遗漏**：渲染代码与工具都就绪，`observe_live` 没把源 docx 传进 `build_template_agent_render_packet`，所以永远走投影回退、无图。（我此前说“接图很重/易卡”不准确，特此更正。）
- **G2 T4 没拿 T1 版式事实**：sections/headers/numbering 在 T1 里有，但没进 packet、没进 T4 证据。
- **G3 T2→T4 断链**：T4 拿不到 AI 的单元，无法做 gold 要求的 `unit_page_policy_binding` / `unit_order` 对齐。



## 4. T3「元素级」缺口（你最不放心的一条）

- **没有元素级 gold**：`t3_element_policy.standard.yaml` 的 `expected` 只有**单元级** `policy_groups`，没有逐 source_seq 的 policy 标注。
- 我之前报的 `distinguishing_recall=0.875` 是**单元级代理**，**不能**回答“每个元素是否标对”。
- 实测覆盖：320 seq 中 **6 个没被任何元素认领**，244 元素、9 unknown_items——**不是每个元素都标了**。
- 结论：**当前无法验证 T3 逐元素正确性**。要能验证，必须先有元素级标准（见 D5）。



## 4b. T4 的思考链路（决策链）

T4 ~90% 是确定性事实结构化，只有 ~10% 需看图判断——模型“判断”很少，自身出错空间也小。

```
输入(白名单事实, 过 assert_firewall_clean):
  - 分节事实 w:sectPr(页边距/纸张/方向/分节类型) + source_seq 锚点
  - 页眉脚事实 headers_footers(有无/内容/首页不同/奇偶不同)
  - 页码事实(分节 pgNumType/起始 + 页码域)
  - 编号事实 numbering_definitions/refs
  - (可选)真实页图 —— 仅用于纯视觉子项

决策链:
  1. 每个 w:sectPr        → 一个 section_profile(page_setup)          [纯事实]
  2. section_boundaries   → 该节覆盖的 source_seq 起止                 [纯事实]
  3. header_footer_policy → 该节页眉/页脚有无+类型                     [纯事实]
  4. page_numbering       → 该节 pgNumType + 页码域                    [纯事实]
  5. numbering_rules      → numbering_definitions 列表编号规则          [纯事实]
  6. 首页视觉特征(居中/空行/bbox) —— 仅有真实页图时判, 否则该子项 abstain [视觉]
  7. unit↔section 绑定    → 不在 T4 内做, 事后对账(见 D3)               [不在 T4]
```

## 5. 待你拍板的决策点

> 每条给出选项与我的**倾向**（仅供参考，你否决即改）。

- **D1 是否给 observe_live 接上真实渲染？**
选项：(a) 接，`observe_live` 传源 docx + render 目录，让 T4 拿到页图；(b) 暂不接，T4 视觉子项继续 abstain。
倾向：**(a)**——工具已就绪，成本低。
- **D2 T4 是否喂 T1 确定性版式事实（sections/headers/numbering/页面设置）？**
选项：(a) 喂，扩 packet + `build_t4_evidence`；(b) 不喂。
倾向：**(a)**——这是 T4 gold 大半 scope 的来源，且不需要图。
- **D3 T4 是否接收 AI 的 T2 单元（做 section↔unit 绑定）？**
选项：(a) 接收（像 T3 那样用 AI 自己的单元，保持独立于代码）；(b) 不接收，T4 只按事实分节。
倾向：**(a)**——gold 要求 unit 绑定；用 AI 自己的单元不破坏“独立于代码结论”。
⚠️ 独立性注意：喂的是 **AI 自己的 T2 产物**，不是代码 unit_map，防火墙不破。
- **D4 防火墙边界确认**：T1 的 sections/headers/numbering 里是否夹带策略/结论字段（就像 data.paragraphs 里发现过 template_policy/final_disposition）？
行动：喂 T4 前必须**白名单投影**，只放事实字段，命中结论字段即降级。需要先核这些子结构的字段。
- **D5 T3 元素级 gold 怎么来？**（决定 T3 能不能真评）
选项：(a) 人工标注逐 source_seq 的 policy（最准，最贵）；(b) 用代码 `element_spec` 作 **silver 参考**先跑元素级一致性（快，但代码非真值）；(c) 只标注每个单元的**关键元素**（签名/日期/题名等）做点检，不做全量。
倾向：先 **(b) 建元素级一致性评测管道**打通口径，再对分歧样本做 **(c) 人工点检**，逐步逼近 (a)。
- **D6 阶段独立性 vs 级联**：Module 1 原则是每阶段独立看干净事实。T4 接 AI 的 T2 单元属“用 AI 自己上游产物”，不违背。但要确认你认可这种“AI 内部级联”（T2→T3 已经这样了）。



## 6. 不变量（无论怎么改都要守）

1. 每阶段只看**干净事实 + AI 自己的上游产物**，绝不看代码阶段结论（unit_map/element_spec/global_spec/standards/gold）。
2. 新喂给 T4 的任何事实都要过 `assert_firewall_clean` 白名单投影。
3. default-off 不变；replay 回归测试保持绿。
4. 准确率评测只对照 `standards/`（gold），不拿模型判断替代 gold（CLAUDE.md 硬约束）。



## 7. 讨论后产出

你逐条对 D1–D6 拍板 → 我据此写**实施计划**（分 T4 接线 与 T3 元素级评测 两条）→ 再动代码。