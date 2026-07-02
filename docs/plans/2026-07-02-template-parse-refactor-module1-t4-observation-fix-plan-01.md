---
status: done
owner: template-generation
stage: T4
topic: module1-t4-observation-fix
doc_type: plan
plan_id: MODULE1-T4-FIX-01
created: 2026-07-02
last_updated: 2026-07-02
source_issue:
  doc: docs/plans/2026-07-01-template-parse-refactor-module1-observation-dataflow-alignment.md
  summary: T4 被饿死（无图/无 T1 版式事实/无 T2 单元）→ abstain → 不可评；核实发现每单元分页在源事实里不存在，只在渲染后出现。
related_code:
  - src/docfit/template_generation/agent/packet.py
  - src/docfit/template_generation/agent/evidence.py
  - src/docfit/template_generation/agent/observation_materialize.py
  - src/docfit/template_generation/agent/observation_loop.py
  - src/docfit/template_generation/agent/observation_eval.py
  - scripts/observe_live.py
---

# 修复计划：Module 1 T4 观察补齐（Track A/B/C）

## 锁定的决策（来自讨论）

- **D1 = 接页图**：observe_live 传源 docx + render 目录，复用 packet.py 已有渲染管线（soffice/pdftoppm/pdftotext 已就绪）。
- **D2 = 喂 T1 确定性版式事实**：page_setup / page_numbering / header-footer 引用。
- **D3 = T4 不吃 T2 单元**：unit↔section 绑定放事后对账，分歧→open_question（避免误差放大）。
- **D8 = (a) Track A 走确定性代码，不问模型**：margins 等是事实，模型不该“重新发明”。LLM 只用于 Track B（读图）。

## 核实到的硬事实（不可假设）

- 整份 320 段**只有 1 个 Word 分节**；`page_break_before` 全 false；无 run 级分页；fields=0。**每单元分页只在渲染后存在。**
- section 事实字段：`page_margins / page_size / page_numbering / references(header1/footer1)`（全是事实，可白名单）。
- header/footer **内容为空**；numbering_definitions=0。→ Track A 产出**薄但确定**。

## Phase 1 — Track A：确定性全局版式（无图、无模型）

目标：T4 从 abstain 变成“至少产出并可评全局页面设置”。

改动：
1. `packet.py`：build 时新增白名单块 `packet["global_layout_facts"]`，从 `document_facts.data.sections[*]` 投影
   `{page_margins, page_size, page_numbering, references:[{kind,type,part_name}]}`；跑 `assert_firewall_clean`。
2. `evidence.py build_t4_evidence`：把 `packet["global_layout_facts"]` 纳入证据视图。
3. `observation_materialize.py materialize_layout_observation`：
   - 从 `global_layout_facts` **确定性**构造一个全局 `section_profile`（page_setup+numbering+header_footer），进 items，标 `source="deterministic_facts"`。
   - 无真实页图时：不再整体 abstain；只对**每单元视觉分页**子项标 `visual_abstained=true`，全局 profile 照常产出。
4. `observation_loop.py`：T4 阶段在无图时**不调用模型**（Track A 是确定性）；有图时才走模型（留给 P2）。

门禁：
- 无图跑 hunannongye：`ai_layout_observation` 含 1 个全局 section_profile；`abstain=false`；`visual_abstained=true`。
- 防火墙：`assert_firewall_clean(t4_evidence)` 通过；global_layout_facts 无策略字段。
- 单测：global_layout_facts 投影只含白名单字段；materialize 全局 profile 字段正确。
- 回归：`uv run pytest tests/unit/template_generation_agent`（当前全绿保持）。

## Phase 2 — Track B：接页图（D1）+ 视觉分页

目标：让 T4 拿到真实页图，模型判每单元分页/首页视觉。

改动：
1. `scripts/observe_live.py`：`build_template_agent_render_packet(document_facts, structure_candidates={}, source_template_docx=<school raw docx>, render_artifacts_dir=<out>/render)`。
   源 docx 路径来自标准 `accepted_source_facts.template_docx`（hunannongye: `inputs/targets/hunannongye/raw/source_template.docx`）。
2. 验证渲染真能出 PNG（soffice→pdf→pdftoppm）。**若本环境渲染失败**：如实记录，Track B 标记为 blocked，不伪造；P1 成果保留。
3. 有图时 T4 模型只判视觉子项（每单元页起始/隔离），必填/枚举过物化闸门。

门禁：
- 渲染成功 → `render_status=real_render`、`clean_page_images>0`。
- 有图跑 → 视觉子项不再 abstain；产出每单元 page 起始。
- 渲染不可用 → 明确报 blocked，不 silent。

## Phase 3 — Track C + 评测补齐

目标：T4 可对 gold 打分；绑定分歧显性化。

改动：
1. `observation_eval.py evaluate_layout_stage`：不再只报 abstain。对 gold `t4_global_layout.standard.yaml` 的
   `page_setup / page_numbering / header_footer_policy` 做字段级对比，产 T4 准确率（全局版式部分）。
2. unit↔section 绑定对账：比较独立的 T2 单元与 T4 section，分歧→`open_questions`（复用 `open_questions_from` 模式）。
3. `observe_live.py --eval-school` 报告加 T4 全局版式准确率。

门禁：
- eval.json 出 T4 全局版式准确率（不再是“不可评”）。
- 单测覆盖 evaluate_layout_stage 的字段对比。

## 完成定义

- 无图：T4 产出 + 可评全局版式；视觉子项显式 abstain。
- 有图（若环境支持）：T4 视觉分页产出 + 可评。
- 全程防火墙不破、default-off 不变、replay 回归绿、准确率只对 gold。
- 每 Phase 一次提交，逐条对齐门禁。

## 执行纪律

严格按 Phase 1→2→3 顺序；每 Phase 跑门禁 + 提交后再进下一步；渲染等外部依赖失败**如实标 blocked，不绕过、不伪造**。

## 执行结果（2026-07-02）

- **Phase 1** `64d3f46`：T4 产出确定性全局 section_profile（页边距/纸张/页码），不再整体 abstain。
- **Phase 2** `1c9be8e`：渲染在本环境**成功**（hunannongye→22 页 PNG）。**偏差（已记录，更稳）**：计划本想让模型判视觉，但 LiveResponder 是文本通道（无多模态），且渲染已给出确定性 per-seq page_no（pdftotext 版面）——改用确定性页结构，可验证、不幻觉；模型视觉留后续。
- **Phase 3** `f01aaba`：T4 页隔离对 gold 打分 + 冲突→open_questions。
- **真实结果（hunannongye, 渲染后）**：T2 单元 1.0；T3 必填合规 1.0；**T4 页隔离 0.6875(11/16)**，21 页；5 个 mismatch 出成 open_questions，其中如 proposal_record 页码=[1,2,11,15] 暴露 T2-seq/渲染绑定的真实问题，供人工复核（安全阀生效）。
- 108 个 agent 测试通过；改动文件 0 pyright 错误；default-off 不变；防火墙不破。
- 遗留待查（新 issue）：部分后置表单 source_seq→page 映射异常（跨页 1,2,11…），疑似 render binding 或 T2 边界，另开诊断。
