---
status: draft
owner: template-generation
stage: cross-stage
topic: stage-standards
plan_id: STAGE-STANDARDS-PLAN-03
created: 2026-07-25
last_updated: 2026-07-26
source_issue:
  id: STAGE-STANDARDS-ISSUE-03
  doc: docs/plans/2026-07-25-template-parse-refactor-stage-standards-issue-03-duplicated-gold-sources.md
coordinates_with:
  - id: T1L1-FACT-FOUNDATION-PLAN-15
    doc: docs/plans/2026-07-26-template-parse-refactor-t1l1-fact-foundation-plan-15-centralize-facts-and-preserve-stage-inputs.md
    relationship: Plan 15 must be verified first; until then current gold, standards, and projectors are frozen as regression oracles, and Plan 03 must not define or backfill the in-flight T1/L1 identity schema
  - id: T2-PAGE-EXCLUSIVE-PLAN-12
    doc: docs/plans/2026-07-24-template-parse-refactor-t2-page-exclusive-units-plan-12-exclusive-contiguous-page-contract.md
    relationship: Plan 12 is the canonical T2 page-range contract; its remaining three-school gold, verifier, judge, and sign-off gates are part of this delivery and must be verified before Plan 03 completes
  - topic: all-stage school gold completeness
    relationship: Plan 03 owns the remaining T1/T3/T4/T5/final-template gold review and all T1-L1-T7/POST_T6 evaluation-consumer cutover; no later plan is used to defer incomplete stages
related_status:
  - docs/status/active/template-generation-canonical-gold-projection.md
---

# 阶段标准 Plan 03：单一 School Gold 与阶段确定性投影

## 目标架构

每所学校、每个模板版本只维护一份：

```text
standards/targets/<target_id>/<version>/school_template.gold.yaml
```

`target.standard.yaml` 只登记这一个 school gold。测试与评测通过 versioned projector
在内存中构造 T1、T2、T3、T4、T5 和 POST_T6 gold views，并为没有独立学校答案
gold 的 L1、T6、T7 构造绑定同一 canonical source 的 contract/evidence views。需要排查时，
可把投影视图写入
本次 eval/run 输出目录；该文件必须带 canonical hash、projection version 和 view hash，
且禁止人工编辑或回写 `standards/`。

```text
school_template.gold.yaml
  ├─ shared source/review/unit facts
  ├─ stages.t1
  ├─ stages.t2
  ├─ stages.t3
  ├─ stages.t4
  ├─ stages.t5
  └─ final_template
          │
          └─ deterministic stage projector
                ├─ T1 gold view
                ├─ L1 contract/evidence view
                ├─ T2 gold view
                ├─ T3 gold view
                ├─ T4 gold view
                ├─ T5 gold view
                ├─ T6 contract/evidence view
                ├─ T7 contract/evidence view
                └─ final-template gap view
```

## 审查基线与本计划必须补齐的缺口

本计划以 `docs/current/template-generation-architecture.md` 和
`docs/current/template-generation-testing.md` 的长期阶段合同为目标事实源，以
2026-07-26 当前代码和真实运行报告为实现事实源。旧 plan、历史报告和现存 stage YAML
只用于迁移取证，不得反向缩小长期合同。

当前实现不能直接视为目标完成态。审查基线如下：

| 阶段 | 长期合同要求 | 2026-07-26 当前真实输出/评分 | 本计划必须补齐 |
| --- | --- | --- | --- |
| T1 | `document_facts` 学校事实 coverage，按事实类别可解释 | standard-quality 只校验文件/schema/基础防火墙；judge 没有 T1 accuracy builder | 建立事实 item 模型、actual normalizer、`fact_coverage` 和分类型 mismatch；学校 gold 不承载通用 schema |
| L1 | 完整索引、引用和无语义越界的 contract coverage | standard-quality 有合同检查；route judge 没有 primary metric | 生成绑定 canonical provenance 的 contract view，报告 `contract_coverage`；不虚构学校答案 gold |
| T2 | unit identity/name/order/page-native boundary/page ownership | judge 主要计算 unit set/order F1；boundary 仅在可取时 exact，未完整评分 name、逐页唯一归属、gap/overlap | 增加 name、boundary、page ownership 的明确分母、mismatch 和硬失败；落实 Plan 12 |
| T3 | run/span atomic Keep/Fill/Delete exact action | 已有 exact-action 主链，三校现有 standard 仍是 `PARTIAL` | 保持 scored identity/action 零语义差异，统一投影、认证和 provenance |
| T4 | section/page setup/header-footer/page numbering/numbering 的值级 `layout_accuracy` | judge 当前主指标是 `layout_contract_completeness`，字段存在但值错误仍可能被高估 | 建立 AI final 的 leaf-level 值比较、分维度准确率和 owner 归因 |
| T5 | 完整 unit-element-section-layout binding 与 merge contract | judge 当前主要是平均 unit F1 和 section-ref compliance，未证明完整合并关系 | 建立 binding item、学校 invariant、hash/availability 合同和 `merge_contract_accuracy` |
| T6 | action 被正确执行并产生可观察 effect | route 报告主要检查产物/manifest 可用性与 hash | 建立 contract/evidence view 和 `execution_effect_accuracy`；不把“manifest 存在”当效果正确 |
| T7 | 必需验证项完整执行，能定位 first bad stage/owner | route 报告主要检查 verification 产物可用性 | 建立 `verification_coverage`、required-check universe 和 UNKNOWN/FAIL 规则 |
| POST_T6 | 最终 Word 内容、样式、位置、页规则、字段、编号、页眉页脚完整签收 | `template_gap` 已直接读取 `expected.units` 并做多类检查，但没有 canonical projection 契约 | 无损迁移现有 final expected 语义，补 typed final checks、稳定 check identity、分母和新旧 parity |

已执行的基线证据必须在 Phase 0 重新生成并固化，当前观察包括：

- real-core standard-quality：三校 T1/T2/T4/T5 为结构性 `PASS`，T3 因 `gold_status`
  为 `PARTIAL` 而使总状态 `UNKNOWN`；这证明目前只有 T3 真正执行阶段认证门禁；
- 湖南农大现有 judge：T2 unit F1 可达 1.0 但 page boundary 不可评分；T4 输出
  completeness 而非 accuracy；T1/T5/T6/T7/POST_T6 没有完整、统一的 route primary metric；
- 当前 T3 三校 ledger 为湖南农大 714 items/674 raw runs、南京农大 599/574、
  北大 1465/1461；迁移不得改变这些已存在的 scored identity/action，除非另有独立批准；
- 当前 final standards 分别覆盖湖南农大 16 units/175 elements、南京农大
  11/133、北大 12/78；迁移必须证明所有现存内容、样式和最终效果检查均未丢失。
- 当前相关 standard-quality/stage-verifier/T3-eval/template-generate 合同测试共
  55 passed；该结果只证明现有实现自洽，不能替代上述长期指标和三校人工 gold 完整性。

因此 Plan 03 不是“把多个 YAML 拼成一个文件”的文件迁移。完整交付同时包含 canonical
数据模型、阶段投影、actual 归一化、指标分母、报告字段、认证门禁、消费者切流和旧源删除。

## 数据模型决定

### 1. 共享层只写一次

`shared` 至少保存：

- unit catalog、element catalog、稳定 identity、名称、唯一顺序和共同 evidence refs；
- 仅用于跨阶段 join 的身份事实，不保存任一阶段的 expected value、action 或最终 Word
  效果答案。

school/template identity、canonical source binding、review records 和 stage certifications
位于 canonical root；它们是跨阶段 provenance/control metadata，不属于 `shared` 业务答案。

### 2. 阶段答案按 owner 分区

| 分区 | 只保存什么 |
| --- | --- |
| `shared` | unit/element identity、名称、顺序和共同 evidence；不得保存 scored value |
| `stages.t1` | 学校特定的事实 items、可观察性例外；通用 T1 schema 与禁用语义字段不重复进学校 gold |
| `stages.t2` | Plan 12 的 unit page-range、顺序及页面归属 scored items |
| `stages.t3` | adaptive run/span Keep/Fill/Delete ledger、unknown/excluded；element 只作 identity binding，不拥有最终 presence |
| `stages.t4` | section boundary、page setup、header/footer、page numbering、numbering 的稳定身份和值 |
| `stages.t5` | 学校特定 expected binding 与跨阶段合并不变量；通用 merge contract 留在 versioned contract |
| `final_template` | 最终 Word 专属的 presence/content/style/position/relationship/effect checks；相同 T2/T4 值使用 `expected_ref`，不得复制 |

`artifact_under_test`、allowed labels、通用 schema、comparator 和 verifier 配置属于
versioned stage contract，不再在每校 gold 中复制。

### 3. Review 事实与阶段认证分离

canonical 文件必须包含：

```yaml
reviews:
  review_20260726:
    kind: human_standard_owner_signoff
    reviewed_by: <human-standard-owner>
    reviewed_at: '2026-07-26'
    evidence_refs: [...]

stage_certifications:
  t3:
    status: VERIFIED
    review_refs: [review_20260726]
    certified_source_sha256: sha256:...
    certified_stage_content_sha256: sha256:...
    certified_projection_contract_version: school-template-gold-projection-1.0
    change_reason: full scored universe reviewed and signed
```

审核事实只在 `reviews` 中写一次。阶段只保存自己的认证状态、引用的 review ids 和
本阶段 change reason。`review_refs` 必须全部解析；一个 review 可以被多个阶段引用，
但一个阶段的完成状态不能提升其他阶段。最终切流前，T1、T2、T3、T4、T5 和
`final_template` 必须分别满足 `VERIFIED`；迁移期间允许暂时降为 `PARTIAL`，但
`PARTIAL/MISSING` 不能作为 Plan 03 的完成状态。

每个 certification 必须绑定 `certified_source_sha256`、
`certified_stage_content_sha256` 和 `certified_projection_contract_version`。
`stage_content_sha256` 只计算当前 source binding、该阶段使用的 shared identities、
已解析的跨阶段 value refs 和 stage-owned/final payload，不包含 review/certification 自身，
避免循环。loader 每次重算；例如 T4 被签值变化时，引用该值的 final certification 也会
失效；
任一 binding/version 不一致时报告 `certification_binding_status=STALE`，effective gold status
固定为 `PARTIAL` 并阻止 PASS/cutover，直到 human standard owner 重新签署。只增加不改变
内容的 review record 不使已有签署失效；source rebind 即使文件内容“看起来相近”，也必须
通过与新 source hash 绑定的明确 rebind review 才能恢复 `VERIFIED`。scored item 数量由
绑定版本的 projector 重算并写入 view/report/review packet，不作为人工填写的冗余真值。

### 4. Hash 与签署绑定语义

所有报告和投影视图必须区分：

| Hash | 计算对象 | 用途 |
| --- | --- | --- |
| `canonical_file_sha256` | `school_template.gold.yaml` 原始 UTF-8 bytes | 文件审计、Git/传输完整性；缩进、注释变化会改变 |
| `canonical_semantic_sha256` | YAML parse + schema validation 后的 canonical JSON | 业务语义身份；mapping key 排序、array 保序、UTF-8、无额外空白；注释、anchor 写法、缩进不影响 |
| `certified_stage_content_sha256` | `{source_binding, stage_relevant_shared_identities, resolved_stage_dependencies, stage_owned_payload}` 的 canonical JSON | 把人工 certification 绑定到实际审核内容；不含 review/certification 自身 |
| `stage_view_sha256` | `{stage_id, projection_contract_version, projected_payload}` 的 canonical JSON | 当前阶段评测输入身份；不含未投影阶段，也不把 root hash 混入计算 |

stage view artifact 仍记录两个 canonical hash 作为 provenance，但
`stage_view_sha256` 不包含它们。因此只调整无关阶段 review 时，当前阶段 view hash
保持不变；只改 YAML 格式时，只有 file hash 改变。所有 view 的 `projected_payload`
都包含当前 `source.current` binding，所以 source DOCX rebind 会有意改变全部 stage view
hash；这不是把 canonical root hash 混入计算，而是阶段输入身份本身发生了变化。

canonical semantic hash 包含经过验证的全部业务字段、review records 和阶段认证状态；
不包含由 loader 计算的 hash 字段本身。

### 5. 完整目标 YAML 示例

以下结构是首版 schema 的决策基线；省略号只表示列表内容未展开，不表示字段 owner
尚未决定。

```yaml
artifact_type: school_template_gold
schema_version: school-template-gold-1.0
school_id: hunannongye
template_version: v1

source:
  current:
    docx_path: inputs/targets/hunannongye/raw/source_template.docx
    sha256: sha256:776649b4...
  rebind_history:
    - rebind_id: source_rebind_20260723
      previous_sha256: sha256:6d66a292...
      current_sha256: sha256:776649b4...
      confirmed_by: user
      confirmed_at: '2026-07-23'
      reason: previous source contained errors; current source is the manually corrected canonical version
      evidence_refs:
        - test_outputs/debug/template_generation/20260723_hunannongye_source_rebind_v1

reviews:
  review_20260615_semantic:
    kind: school_template_semantic_review
    reviewed_by: user-reviewed-source-fact-packet
    reviewed_at: '2026-06-15'
    source_refs:
      - docs/human/real-core-v0-review-packet.md#source-hunannongye
    source_hashes:
      review_packet: sha256:afd5d042...
      source_section: sha256:e3a0d411...
  review_20260723_t3_delegated:
    kind: delegated_word_visual_review
    reviewed_by: codex-delegated-review
    reviewed_at: '2026-07-23'
    evidence_refs:
      - test_outputs/debug/template_generation/phase1_packet_probe_final/hunannongye/pages
    human_confirmation_state: confirmed
  review_20260726_all_stage_signoff:
    kind: all_stage_school_gold_signoff
    reviewed_by: <human-standard-owner>
    reviewed_at: '2026-07-26'
    confirms_review_refs: [review_20260615_semantic, review_20260723_t3_delegated]
    evidence_refs:
      - <three-school-t1-t5-and-final-review-packet>

stage_certifications:
  t1:
    status: VERIFIED
    review_refs: [review_20260615_semantic, review_20260726_all_stage_signoff]
    certified_source_sha256: sha256:776649b4...
    certified_stage_content_sha256: sha256:...
    certified_projection_contract_version: school-template-gold-projection-1.0
    change_reason: complete school-specific fact universe reviewed and signed
  t2:
    status: VERIFIED
    review_refs: [review_20260615_semantic, review_20260726_all_stage_signoff]
    certified_source_sha256: sha256:776649b4...
    certified_stage_content_sha256: sha256:...
    certified_projection_contract_version: school-template-gold-projection-1.0
    change_reason: complete page-native unit ranges reviewed and signed
  t3:
    status: VERIFIED
    review_refs: [review_20260615_semantic, review_20260723_t3_delegated, review_20260726_all_stage_signoff]
    certified_source_sha256: sha256:776649b4...
    certified_stage_content_sha256: sha256:...
    certified_projection_contract_version: school-template-gold-projection-1.0
    change_reason: complete adaptive run/span universe reviewed and signed
  t4:
    status: VERIFIED
    review_refs: [review_20260615_semantic, review_20260726_all_stage_signoff]
    certified_source_sha256: sha256:776649b4...
    certified_stage_content_sha256: sha256:...
    certified_projection_contract_version: school-template-gold-projection-1.0
    change_reason: complete layout scored universe reviewed and signed
  t5:
    status: VERIFIED
    review_refs: [review_20260615_semantic, review_20260726_all_stage_signoff]
    certified_source_sha256: sha256:776649b4...
    certified_stage_content_sha256: sha256:...
    certified_projection_contract_version: school-template-gold-projection-1.0
    change_reason: complete merge expectations reviewed and signed
  final_template:
    status: VERIFIED
    review_refs: [review_20260615_semantic, review_20260726_all_stage_signoff]
    certified_source_sha256: sha256:776649b4...
    certified_stage_content_sha256: sha256:...
    certified_projection_contract_version: school-template-gold-projection-1.0
    change_reason: complete final-template checks reviewed and signed

shared:
  unit_order:
    - cover
    - integrity_statement
    - toc
  units:
    - unit_id: cover
      name: 封面
      order: 1
      evidence_refs: ['review_text:2.1']
      element_catalog:
        - element_id: e_001
          name: 学校名称
          order: 1
          evidence_refs: ['review_text:2.1']
        - element_id: e_002
          name: 论文题名
          order: 2
          evidence_refs: ['review_text:2.1']
    - unit_id: integrity_statement
      name: 诚信声明
      element_catalog: [...]

stages:
  t1:
    fact_items:
      - fact_id: fact:section/section_001/start_type
        fact_kind: section
        identity_ref: section:section_001
        field_path: start_type
        expected:
          kind: scalar
          value: newPage
        comparator: exact
        evidence_refs: ['source_ooxml:word/document.xml#sectPr-1']
      - fact_id: fact:header/default/text
        fact_kind: header_footer
        identity_ref: header:default
        field_path: visible_text
        expected:
          kind: text
          value: 湖南农业大学
        comparator: unicode_nfkc_trim_exact
        evidence_refs: [review_20260726_all_stage_signoff]
    unknown: []
    excluded: []

  t2:
    units:
      - unit_ref: unit:cover
        boundary:
          start_page: 1
          end_page: 1
      - unit_ref: unit:integrity_statement
        boundary:
          start_page: 2
          end_page: 2
    unknown: []
    excluded: []

  t3:
    identity_bindings:
      - element_ref: unit:cover/element:e_001
        evidence_refs: ['review_text:2.1']
    run_span_ledger:
      - target_kind: run
        raw_run_id: p_0001.r_001
        text: 附件
        unit_ref: unit:cover
        expected_action: delete
      - target_kind: span
        raw_run_id: p_0093.r_002
        start: 0
        end: 1
        text: ':'
        unit_ref: unit:abstract_cn
        expected_action: keep
    unknown: []
    excluded:
      - identity_ref: header:default/r_001
        reason_code: out_of_stage_owner
        reason: header_footer is outside the T3 body-flow scored universe
        owned_by_stage: T4

  t4:
    sections:
      - section_ref: section:section_001
        boundary:
          start_source_ref: paragraph:p_0001
          end_source_ref: paragraph:p_0040
        page_setup:
          width_twips: 11906
          height_twips: 16838
          orientation: portrait
          margin_top_twips: 1440
          margin_bottom_twips: 1440
          margin_left_twips: 1800
          margin_right_twips: 1440
          gutter_twips: 0
        header_footer_bindings:
          - kind: header
            variant: default
            part_ref: header:default
            display: true
            linked_to_previous: false
            applies_to: all_pages
        page_numbering:
          display: true
          format: lower_roman
          start: 1
          applies_to: section
          field_refs: ['field:page/default']
    numbering_definitions:
      - numbering_ref: numbering:heading_multilevel
        levels:
          - level: 0
            num_format: decimal
            start: 1
            text_pattern: '%1'
            style_ref: style:heading_1
    unknown: []
    excluded: []

  t5:
    expected_bindings:
      - binding_id: binding:cover/e_001/to/spec
        binding_kind: unit_element
        source_refs:
          - unit:cover
          - unit:cover/element:e_001
        target_ref: template_spec:unit/cover/element/e_001
        required: true
      - binding_id: binding:section_001/to/spec
        binding_kind: unit_section
        source_refs: ['section:section_001']
        target_ref: template_spec:global/section_001
        required: true
    school_specific_invariants:
      - invariant_id: preserve_post_body_forms_as_separate_units
        unit_refs: ['unit:design_task', 'unit:proposal']
        expected: true
    unknown: []
    excluded: []

final_template:
  units:
    - unit_ref: unit:cover
      match:
        aliases: [封面]
        anchor_texts: [湖南农业大学]
      elements:
        - element_ref: unit:cover/element:e_001
          presence_mode: fixed
          text_match:
            mode: unicode_nfkc_trim_exact
            expected_text: 湖南农业大学
          style_expectation:
            paragraph_style_ref: style:cover_school_name
          position_expectation:
            relative_to_unit: inside
        - element_ref: unit:cover/element:e_002
          presence_mode: fillable
          text_match:
            mode: placeholder_or_filled
          style_expectation:
            paragraph_style_ref: style:cover_title
      checks:
        - check_id: final:cover/keep_together
          check_kind: page_effect
          observed_path: units.cover.keep_together
          expected:
            kind: scalar
            value: true
        - check_id: final:cover/page_range
          check_kind: referenced_stage_effect
          observed_path: units.cover.page_range
          expected_ref: stage-value://t2/unit/cover/boundary
  header_footer_effects:
    - check_id: final:header/default/display
      observed_path: sections.section_001.header.default.display
      expected_ref: stage-value://t4/section/section_001/header/default/display
  field_effects:
    - check_id: final:field/page/default/updated
      observed_path: fields.field:page/default.updated
      expected:
        kind: scalar
        value: true
  numbering_effects:
    - check_id: final:numbering/heading_multilevel/applied
      observed_path: numbering.numbering:heading_multilevel.applied
      expected:
        kind: scalar
        value: true
  global_checks:
    - check_id: final:package/valid
      check_kind: package
      observed_path: package.valid
      expected:
        kind: scalar
        value: true
  unknown: []
  excluded: []
```

`shared.units` 拥有 unit/element identity、名称、唯一顺序和共同 evidence refs；
`stages.t2` 拥有 page boundary；`stages.t3` 拥有 atomic action；`stages.t4` 拥有 layout；
`stages.t5` 拥有 expected binding；`final_template` 拥有最终 Word 可观察效果。final 的
`presence_mode` 是最终文档应该出现何种内容的签收语义，不是 T3 的原子 Keep/Fill/Delete
决策，二者不得合并评分。final-template view 可联合 shared、相关 stage payload 和
`final_template` 生成；若最终检查预期与 T2/T4 值完全相同，必须使用 `expected_ref`，
不能复制 literal。最终内容、样式、字段更新和“效果已发生”属于 final owner，可以保存
自己的 literal expected。

versioned schema 必须维护以下 JSON-pointer owner 表，并由测试逐项覆盖：

| Pointer family | 唯一 owner | 可被谁引用 |
| --- | --- | --- |
| `/source/**` | canonical root provenance | 所有 view envelope |
| `/reviews/**`、`/stage_certifications/**` | canonical root control metadata | 对应阶段 view |
| `/shared/unit_order`、`/shared/units/**/(unit_id|element_id|name|order|evidence_refs)` | `shared` | T2/T3/T5/final |
| `/stages/t1/fact_items/**` | T1 | T1 |
| `/stages/t2/units/**/boundary` | T2 | T2/final reference |
| `/stages/t3/run_span_ledger/**/expected_action` | T3 | T3 |
| `/stages/t4/sections/**`、`/stages/t4/numbering_definitions/**` | T4 | T4/T5/final reference |
| `/stages/t5/expected_bindings/**`、`/stages/t5/school_specific_invariants/**` | T5 | T5 |
| `/final_template/**` | POST_T6/final | final-template view |

owner 表使用 JSON Pointer 描述 schema 字段族；跨阶段值引用不用数组下标或脆弱 JSON Pointer，
统一使用 `stage-value://<stage>/<entity-kind>/<stable-id>/<field-path>`。stable id 和每个 path
segment 使用 RFC 3986 percent-encoding；只允许引用 owner 表显式开放的 T2/T4 值，解析结果
必须唯一、类型必须与 final check comparator 相容，循环引用或引用 T1/T3/T5/final 值均为
schema error。identity 引用继续使用 `unit:<id>`、`unit:<id>/element:<id>` 等既有稳定格式。

所有分区的 `unknown[]` item 至少包含 `identity_ref`、`field_path`、`reason_code`、
`reason`、`observability=intrinsically_unobservable|tooling_unavailable` 和
`approval_review_refs`；`tooling_unavailable` 只能是中间状态，不能随阶段认证进入
`VERIFIED`。`excluded[]` 至少包含 `identity_ref`、`reason_code=out_of_stage_owner`、
`reason` 和 `owned_by_stage`。同一 identity/field 不得同时出现在 scored、unknown 和
excluded 集合。

versioned schema 维护 JSON-pointer owner 表。以下情况直接 schema error：

- `stages.t2` 重写 `shared.unit_order`；
- `stages.t3` 声明 page boundary 或 T4 layout；
- `stages.t4` 重复保存 source hash 或 review record；
- `final_template` 复制 T2/T3/T4 owned value，而不是使用 identity ref；
- `review_refs`、`unit_ref`、`element_ref` 或 source-rebind evidence 无法解析。

### 6. 投影必须是纯函数

投影输入只有 canonical gold、stage id 和 projection contract version。输出必须：

- 只包含当前阶段允许的字段；
- 在 artifact provenance 中保留 canonical path/file hash/semantic hash 和稳定 identity；
- 相同输入产生相同 canonical JSON 和 view hash；
- 不读取 actual run、AI observation、judge 结果或当前代码生成产物；
- 不补默认业务答案；迁移过程发现缺失内容时保持 `MISSING/PARTIAL/UNKNOWN` 并阻止最终
  cutover，直到对应学校、阶段的 scored universe 完成审核并晋升为 `VERIFIED`。

### 7. 统一 Stage View Envelope

所有 projector 输出同一种 envelope；学校 gold view 与 contract-only view 只在
`artifact_type`、`evaluation_basis` 和 evaluation state 上不同：

```yaml
artifact_type: school_template_stage_gold_view
view_schema_version: template-generation-stage-view-1.0
stage_id: T2
evaluation_basis: school_gold
canonical:
  target_id: hunannongye
  template_version: v1
  path: standards/targets/hunannongye/v1/school_template.gold.yaml
  file_sha256: sha256:...
  semantic_sha256: sha256:...
  source_docx_sha256: sha256:776649b4...
projection_contract_version: school-template-gold-projection-1.0
evaluation_state:
  gold_status: VERIFIED
  certification_binding_status: VALID
  review_refs: [review_20260726_all_stage_signoff]
  referenced_reviews: [...]
payload:
  source_binding:
    docx_path: inputs/targets/hunannongye/raw/source_template.docx
    sha256: sha256:776649b4...
  identity_binding:
    unit_catalog_sha256: sha256:...
  expected: ...
  unknown: []
  excluded: []
stage_view_sha256: sha256:...
```

L1/T6/T7 使用 `artifact_type=template_generation_stage_contract_view`、
`evaluation_basis=contract_only`、`evaluation_state.gold_status=MISSING`，同时给出
`contract_status=ACTIVE|INCOMPLETE|INCOMPATIBLE`。`MISSING` 在这里表示按架构没有独立
学校答案 gold，不是漏做；只有 `contract_status=ACTIVE` 且所有必需 contract items
已经实例化时才可评分。

`projected_payload` 是 `evaluation_state` 与 `payload` 的组合；它只包含当前阶段认证、
该认证直接引用的 review records 和当前阶段内容。因此：

- 修改当前阶段答案、认证或直接引用的 review 会改变该 stage view hash；
- 修改无关阶段答案或无关 review 不改变该 stage view hash；
- contract view 可以引用 shared identity/source binding，但不得吸收其他阶段的 scored value；
- 报告必须保存 envelope，不得只抄一个 hash 后丢失 projected item identity。

contract-only 阶段允许在评测开始时把 view 中的 required-check templates 对
**已声明的 isolated/cascade 输入**实例化。例如 T6 根据冻结 T5 final 的 action ids 生成
effect checks，T7 根据本次声明的 T1-T6 artifact set 生成 verification checks。实例化必须
发生在读取被测阶段输出之前，只能使用 versioned contract、projected source/identity binding
和已冻结的上游输入；不得根据输出里“实际出现了什么”缩小检查集合。实例化结果另计算
`instantiated_contract_sha256` 并写入报告，不改变 `stage_view_sha256`，也不形成学校 gold。

### 8. 通用评分语义

所有阶段先把 expected view 和 actual artifact 归一化为稳定 item，再比较；verifier 不得
直接对两份任意嵌套 YAML 做“字段存在即通过”的递归检查。每个 item 至少具有
`item_id`、`category`、`identity_ref`、`field_path`、`expected`、`comparator`、
`required` 和 `evidence_refs`。

统一规则如下：

1. gold-bearing stage 的 `scored_universe` 是投影后所有 `required=true` 且不在
   `unknown/excluded` 中的 item；contract-only stage 使用读取被测输出前已冻结的
   instantiated required checks。`denominator=|scored_universe|`，报告必须同时列出
   numerator、denominator 和 item ids。
2. expected item 在 actual 缺失时按错误计入分母，不能从分母消失；actual 因运行故障无法
   读取时阶段为 `UNKNOWN`，仍报告原始分母。
3. gold 中 `unknown` 不进入准确率分母，但必须有稳定 identity、原因、批准 review 和
   可观察性分类；“尚未审完/尚未补值”只能对应 `PARTIAL/MISSING`，不能伪装成天然 unknown。
4. `excluded` 只用于合同明确不属于本阶段 owner 的对象；必须报告数量和原因，不能用来
   排除错误预测。actual extra 按各阶段 precision/安全合同处理。
5. 学校 gold-bearing 阶段只有认证为 `VERIFIED` 才能产生 PASS/FAIL 质量结论；
   `PARTIAL/MISSING` 固定输出 `UNKNOWN`。contract-only 阶段只有 `contract_status=ACTIVE`
   才能产生 PASS/FAIL。
6. `denominator=0`、comparator 未注册、identity 无法解析、source/hash 不一致或 required
   actual 不可观察时固定为 `UNKNOWN`，不得按 1.0 或 PASS 处理。
7. mismatch 固定包含 `item_id/category/identity_ref/field_path/expected/observed/comparator/
   owner/evidence_refs`；报告的 `first_bad_stage` 只能根据这些结构化 mismatch 和运行合同
   顺序确定。
8. primary metric 的数值门槛由 versioned stage contract 固定，不存入学校 gold。
   canonical 迁移 parity、标准签署和本计划 cutover 使用 exact gate：全部 required
   identity/value/relationship item 正确且 hard gates 为真；产品评测若未来采用非 1.0
   阈值，必须仍保留逐项 mismatch。

统一 comparison report 至少使用以下形状，不能只输出一个 summary status：

```yaml
stage_id: T4
evaluation_basis: school_gold
status: FAIL
primary_metric:
  name: layout_accuracy
  value: 0.975
  numerator: 78
  denominator: 80
metrics:
  section_identity_boundary: {numerator: 12, denominator: 12, value: 1.0}
  page_setup: {numerator: 18, denominator: 20, value: 0.9}
hard_gates:
  source_hash_match: true
  required_actual_observable: true
universe:
  required: 80
  checked: 80
  unknown: 0
  excluded: 3
  extra_actual: 0
mismatches:
  - item_id: t4:section_002/page_setup/margin_top_twips
    owner: T4
    expected: 1440
    observed: 1350
    comparator: exact
provenance:
  canonical_semantic_sha256: sha256:...
  projection_contract_version: school-template-gold-projection-1.0
  stage_view_sha256: sha256:...
  actual_sha256: sha256:...
```

### 9. 阶段投影与评分合同

#### 9.1 T1：学校事实投影

- Projector 从 `stages.t1.fact_items` 生成 `expected.fact_items[]`，保持 `fact_id`、
  `fact_kind`、稳定对象身份、字段路径、typed expected、comparator 和 evidence。
- Actual normalizer 只读取 final `01_document_facts.json`，把 `body_flow/runs/indexes/data`
  中的客观事实展开为相同 key；不得把 `unit_id/policy/confidence/is_toc_entry` 等下游
  语义塞入 T1。
- 主指标：
  `fact_coverage = correct_required_fact_items / required_fact_items`。同时按 body flow、
  run、section、header/footer、field、table/image/object、source trace 分类报告
  expected/correct/missing/mismatched。
- schema、hash 可重算、identity 唯一、索引闭合和语义防火墙是 versioned T1 contract
  hard gates；它们不作为学校 gold item 重复计分。
- `unknown_objects[]` 必须与 gold 可观察性例外对账；新出现的 unknown 不从事实分母中
  删项，而是额外产生 `unexpected_unknown_object` mismatch。

#### 9.2 L1：统一事实合同投影

- 无独立学校答案。Projector 以 versioned L1 contract 加 canonical source/identity
  binding 生成 required checks：T1/render/source hash 一致、identity 唯一、引用完整、
  page/object binding 覆盖、contract hash 可重算和 firewall。
- Actual 只读取 final `01.5_l1_input_contract.json` 及其声明的 frozen inputs。
- `contract_coverage = passed_required_contract_checks / required_contract_checks`。
  visual unavailable 和 unknown 单列；任何 required binding 未检查或不可观察时为
  `UNKNOWN`，明确检查为错时为 `FAIL`。
- 报告保留 `gold_status=MISSING` 与 `contract_status=ACTIVE`，禁止用一个虚假的
  `VERIFIED` 学校 gold 掩盖合同型评测。

#### 9.3 T2：unit/page-native 投影

- Projector 联合 `shared.unit_order/shared.units` 与 `stages.t2.units`，生成：
  `expected.unit_order[]` 和
  `expected.units[{unit_id,unit_name,order,boundary.start_page,boundary.end_page}]`。
- Actual normalizer 只读取 final `02_unit_map.yaml`；AI raw、旧 source-range standard、
  candidate 或 materializer 调试产物不能作为 actual。
- unit 集合报告 precision/recall/F1；顺序报告 `order_exact_match`；名称使用
  versioned `unicode_nfkc_trim_exact` comparator，
  `name_match_accuracy = correct_expected_unit_names / expected_unit_count`；
  每个 unit 的首尾页都完全一致才算该 unit boundary correct，
  `page_boundary_exact_match = correct_expected_unit_boundaries / expected_unit_count`。
- Projector 必须把 inclusive page ranges 展开为 `expected_page_owner[page]=unit_id`；
  actual 同样展开。`page_ownership_coverage = correct_expected_page_owners /
  expected_page_count`。expected 或 actual ranges 内部 gap/overlap、页码非正数、反向 range、
  extra page 或一个页面多个 owner 均生成独立 mismatch。
- `page_policy` 按长期合同由程序从 unit 位置固定派生，只做确定性合同检查，不进入 AI gold。
  source refs/anchors 仅用于 binding evidence，不进入 accuracy。
- T2 primary metric 保持 `unit_f1` 以兼容长期报告；PASS 还必须同时满足
  `order_exact_match=true`、name/boundary/page ownership 全部为 1.0、
  `gap_count=overlap_count=0`、final availability/hash/binding hard gates 通过。不得用
  unit F1=1.0 替代页面质量通过。

#### 9.4 T3：adaptive atomic action 投影

- Projector 只把 `stages.t3.run_span_ledger` 投影为 adaptive run/span scored universe；
  `identity_bindings` 仅帮助回到 shared element/unit，不进入动作分母。
- `expected_action` 序列化值只允许 `keep|fill|delete`（报告显示 Keep/Fill/Delete）；
  通用 core-action contract
  由 projection contract 注入，不在每校文件复制。
- Actual normalizer 使用正式 T3 observation/final trace 确定性展开为同一 atomic identity。
  element 分组、停止层级、角色、fill subtype、调用次数和解释文字不进入主分母。
- 主指标和报告字段沿用长期合同：
  `exact_action_accuracy`、`action_macro_f1`、per-action precision/recall/F1、per-unit
  accuracy、coverage/conflict 和 deletion safety。
- 缺失 prediction 按错误；冲突 identity 按错误；false delete 触发
  `hard_gate_zero_false_delete=false`。unknown 不进主分母但仍受误删安全门约束。
- 迁移 parity 固定比较 raw-run count、atomic item count、item identity/text/action、
  unknown/excluded 和直接 review metadata；T3 不允许 semantic change。

#### 9.5 T4：版式值投影

- Projector 把 `stages.t4.sections` 和 `numbering_definitions` 确定性展开为 leaf items，
  形如 `{item_id, dimension, identity_ref, field_path, expected_value, comparator}`。
  dimension 固定为 `section_identity_boundary/page_setup/header_footer/page_numbering/
  numbering_definition`。
- Actual normalizer 只把 AI-only 正式 final `04_global_spec.yaml` 展开为同一 leaf shape；
  AI raw、历史 code/hint/merged 诊断产物不能作为 T4 accuracy actual。
- `layout_accuracy = correct_required_layout_leaf_items / required_layout_leaf_items`；
  同时按五个 dimension 报告 numerator/denominator/accuracy 和 mismatch samples。
- 字段存在但值错、section 绑定到错误 identity、header/footer part/ref 或 scope 错、
  page number display/format/start/scope 错，均必须降低准确率；不能再以
  `layout_contract_completeness` 作为质量主指标。
- hash/schema/source identity/render evidence/availability 属于 hard gates；视觉 evidence
  coverage 和 unknown 单列，不进入值准确率分母。canonical final 只有
  `04_global_spec.yaml`，报告不得恢复 code/AI/merged 多路线 authority。

#### 9.6 T5：合并关系投影

- Projector 生成两组 required checks：
  一组来自 versioned merge contract（final input 角色、hash、availability、保守传播、
  review flags）；另一组来自 `stages.t5.expected_bindings` 和
  `school_specific_invariants`。
- Expected binding 只保存 source refs 到 target ref 的关系，不复制 T2/T3/T4 expected
  value。Actual normalizer 只读取 final `05_template_spec.yaml`，把 unit、element、
  section/global binding 展开为稳定 relation item。
- `merge_contract_accuracy = passed_required_merge_checks / required_merge_checks`。
  同时报告 unit precision/recall/F1/order、unit-element binding、unit-section binding、
  input hash/trace、availability 和 review flags；每项都有明确 numerator/denominator。
- 相同 unit 集合但丢 element、错 section、错上游 hash、availability 被错误升级或
  required review flag 丢失时，主指标必须下降或 hard fail。当前“平均 unit F1 +
  section ref compliance”不得继续冒充完整 merge accuracy。

#### 9.7 T6：执行效果合同投影

- 无独立学校答案。Projector 从 versioned T6 contract 和 canonical identity binding
  输出 required-effect templates；评测器再根据已冻结 T5 final 的 action ids/categories
  实例化 required effect checks。不得把 T2/T3/T4 业务答案重新写成 T6 gold，也不得根据
  build manifest 实际声称执行的动作缩小 required 集合。
- Actual normalizer 同时读取 final `06.2_build_manifest.json` 和对
  `06.1_fillable_template.docx` 的本次 fresh observation，后者必须绑定最终 DOCX hash。
- 每个 required action/effect item 区分 `declared_executed`、`observed_effect` 和
  `manifest_observation_consistent`。只有 fresh Word observation 证明效果且与 manifest
  一致才算正确。
- `execution_effect_accuracy = correct_required_effect_items /
  required_effect_items`；按 delete/keep/fill/generated、page break、section break、
  keep together、page policy 分类别报告。
- manifest/action 存在、output hash 存在或 `executed=true` 不能单独计为效果正确；
  缺 fresh observation 为 `UNKNOWN`，观察到相反效果为 `FAIL`。

#### 9.8 T7：验证覆盖合同投影

- 无独立学校答案。Projector 从 versioned T7 contract 输出 T1-T6 必需检查 templates；
  评测器根据本次预先声明并冻结的 artifact set 实例化检查 universe：schema、hash、
  availability、identity/ref、action/effect 对账、最终文件绑定和 first-bad-stage/owner
  规则。
- Actual normalizer 读取 final `07_verification_report.json`，并核对它引用的本次
  L1/T5/T6/final DOCX hashes；历史 verification report 不得直接复用。
- `verification_coverage = completed_required_verification_checks /
  required_verification_checks`。`completed` 表示确实执行并产生 PASS/FAIL 观察，不表示
  检查结果为 PASS；报告另列 passed/failed/unknown/not_run。
- required check 未运行、被 summary 吞掉或证据 hash 不匹配时为 `UNKNOWN`；检查发现错误
  时为 `FAIL`。`first_bad_stage` 和 owner 必须与最早结构化失败一致，否则产生
  `misattributed_first_bad_stage`。

#### 9.9 POST_T6：最终 Word 投影

- Projector 联合 shared identity、必要的 T2/T4 `expected_ref` 与 `final_template`，展开
  稳定 `required_checks[]`。检查类别至少覆盖 unit/element presence、文本/content、
  样式、位置/关系、页规则、section、header/footer、field、numbering 和 DOCX package。
- `presence_mode=fixed|fillable|generated|optional` 必须有 versioned comparator 语义；
  optional 不进入 required denominator，但仍报告 observed。现存 final standard 的 unit
  aliases/anchors、element content/style 和全局规则都必须有无损映射，不允许只迁移 refs。
- Actual normalizer 从最终 DOCX fresh parse/render 生成 observation tree；不得读取 T3
  action 或 T6 manifest 代替最终效果。每个观察绑定最终 DOCX sha256。
- 主状态 `final_gap_status` 根据 blocking checks 得出，同时报告：
  `checked_required_checks/required_checks`、passed/failed/unchecked、分类 gap 和 item ids。
  required unchecked 导致 `UNKNOWN`，blocking mismatch 导致 `FAIL`，只有全部 required
  checked 且无 blocking mismatch 才为 `PASS`。
- 旧 `template_gap` 与新 projection 在同一 actual 上必须比较 check identity、expected、
  observed、blocking class、numerator/denominator 和最终状态；仅比较总 PASS/FAIL 不算 parity。

### 10. 当前正式产物适配边界

| 阶段 | 唯一 actual 主产物 | Normalizer 必须读取 | 明确禁止 |
| --- | --- | --- | --- |
| T1 | `01_document_facts.json` | source metadata、body_flow、runs、indexes、data、unknown objects | 下游 unit/policy 语义 |
| L1 | `01.5_l1_input_contract.json` | hashes、identity/index、render/page/object binding、coverage | 学校答案、judge 结论 |
| T2 | `02_unit_map.yaml` | final metadata、units identity/name/order/boundary/page refs | AI raw、旧 source range、candidate |
| T3 | `03_element_spec.yaml` + 正式 decision trace | source/run/span identity、final action/policy materialization、coverage | element 分组替代 atomic action |
| T4 | `04_global_spec.yaml` | section profiles、page setup、header/footer、page numbering、numbering | completeness 替代值比较 |
| T5 | `05_template_spec.yaml` | upstream refs/hashes、global、units/elements/section bindings、availability/review | 重新推断上游答案 |
| T6 | `06.2_build_manifest.json` + `06.1_fillable_template.docx` fresh observation | actions、effects、identity resolution、output hash、fresh observed effects | 只信 `executed` |
| T7 | `07_verification_report.json` + 被引用产物 | check execution、findings、hashes、first bad stage/owner | 只看 summary status |
| POST_T6 | `06.1_fillable_template.docx` fresh parse/render | typed final observations 和 final hash | T3/T6 声明代替 Word 实际效果 |

Normalizer 是评测层适配器，不修改业务产物。它们使用正式字段和版本化 alias 表；遇到未知
artifact version 或关键字段只存在于启发式路径时输出 `UNKNOWN`，不得静默猜测。

## 迁移顺序

### Phase 0：冻结当前语义与漂移清单

1. 对三校现有 `final_template.expected.yaml` 和 T1–T5 standards 建立字段 provenance
   清单：唯一内容、重复内容、冲突内容、仅 contract 内容、仅 evidence 内容。
2. 固化迁移前 T1–T5/final stage views、L1/T6/T7 contract/evidence views、
   standard-quality、isolated/cascade judge 和 template-gap 报告/hash。
3. 对所有重复字段做冲突扫描；冲突不能由迁移脚本自行选择，进入 migration approval ledger。
4. 特别冻结 T3 当前 raw-run/span identity、动作、unknown/excluded、review metadata 和
   湖南农大 source-rebind evidence。

Stop gate：存在无法判断 owner 的冲突字段时停止，不创建“取任一值”的兼容规则。

### Phase 1：建立 canonical schema 与只读 projector

1. 增加 versioned `school-template-gold` schema/validator，至少强制：
   - root/source/review/certification/shared/stage/final 字段形状和 `additionalProperties`；
   - `unit_id/element_id/fact_id/binding_id/check_id` 全局或所属域唯一；
   - `unit_order` 与 unit catalog 一一对应，order 连续且无重复；
   - 所有 review/source/unit/element/stage `expected_ref` 可解析且无循环；
   - typed expected 与 comparator 类型兼容；
   - JSON-pointer owner、防重复和 unknown/excluded reason/review 规则。
2. 建立集中式 canonical loader、semantic canonicalizer、hash 计算和 comparator registry；
   standard-quality、judge 和 template-gap 复用同一实例，不另建第二套评测框架。
3. 实现 T1/T2/T3/T4/T5/final gold projectors，以及 L1/T6/T7 的
   contract/evidence binding projectors；projector 不负责读取 actual 或计算准确率。
4. 实现各阶段 expected flattener、actual normalizer 和 metric builder，接口固定为：
   `projected view + normalized actual -> structured comparison report`。旧 stage verifier
   可以暂时包住该接口，但不能继续保留第二套评分语义。
5. stage view 带：
   - canonical gold path/hash/version；
   - stage id、evaluation basis、gold/contract status 和当前阶段 review metadata；
   - projection contract version；
   - projected scored/identity/review 字段；
   - view hash。
6. comparison report 固定带：
   - expected/actual artifact refs 和 hashes；
   - primary metric、所有 numerator/denominator；
   - checked/unknown/excluded/extra counts；
   - 结构化 mismatches、hard gates、stage status、owner 和 evidence；
   - canonical/projection/view provenance。
7. 增加 firewall 与反例测试，证明 T2 view 不含 T3 action、T3 view 不含 T4 layout、
   T4 view 不重复评分 T2 page-range、final `expected_ref` 不复制 literal，以及字段存在但值错
   不会得到满分。

此阶段使用 synthetic fixture 和内存 canonical 文档，不切换 real-core 正式读取路径。

### Phase 2：三校 canonical 数据迁移与全阶段 gold 补齐

1. 将现有 `final_template.expected.yaml` 重构为目标
   `school_template.gold.yaml`，不是复制后长期双写。
2. 合并 source/review/unit catalog/order，删除重复字段。
   迁移脚本必须输出逐字段 provenance，按下表处理，不能用目标 schema 的默认值掩盖旧内容：

   | 旧来源 | canonical 目标 | 迁移要求 |
   | --- | --- | --- |
   | 各 stage standard 的 source/review metadata | root `source/reviews/stage_certifications` | 同义去重；冲突进入 ledger，不自动选择 |
   | T1 expected facts/exception evidence | `stages.t1.fact_items/unknown/excluded` | 通用 schema/firewall 抽到 versioned contract |
   | T2 unit identity/name/order | `shared` identity + `stages.t2` 投影 join | identity 只留一份；真实 page ranges 必须人工重签 |
   | T3 unit/element refs 与 run/span ledger | `shared` refs + `stages.t3` | atomic identity/text/action 零变化 |
   | T4 layout values | `stages.t4` | 补完整 leaf universe；保留稳定 section/object identity |
   | T5 template-spec expectations | `stages.t5.expected_bindings/invariants` | literal 上游值改为 refs；通用 merge checks 抽到 contract |
   | `final_template.expected.yaml` unit/element/global rules | `shared` identity + `final_template` typed checks | content/style/presence/page/header/footer/field/numbering 全部无损，T2/T4 同值改 `expected_ref` |
3. T1 完成三校学校特定事实标准：
   - 从当前 source DOCX、sealed T1/L1 facts 和既有签署证据重建完整 scored universe；
   - 通用 schema/禁用字段迁出学校 gold，学校特定 expected facts、identity 和 evidence
     全部保留；
   - 逐校完成 source identity、事实 coverage 和异常对象复核，认证为 `VERIFIED`。
4. T2 按 Plan 12 的 page-native 契约补齐并签署：
   - 基于每校当前 canonical DOCX 的真实 Word/LibreOffice 渲染页完成人工页面区间复核；
   - 每个真实页面恰好属于一个 unit，page ranges 连续、无 gap/overlap，不能以
     `unknown` 代替未审页面；
   - 更新 verifier、route-eval、judge 和 frozen isolated input，使 page-native gold
     真正参与评分；
   - Plan 12 的剩余 gold、verifier、judge 和人工签署门禁在本交付内关闭，T2 认证为
     `VERIFIED`。
5. T3 无损迁移并完成签核：
   - 三校 adaptive run/span ledger scored identity/action 完全保持；
   - 对完整 scored universe 做最终签署，清除“仅 delegated、未确认”的完成阻塞；
   - 湖南农大使用 `776649b4…` canonical source 和 674 raw-run 投影。
6. T4 完成三校全局版式 gold：
   - 在 Word、OOXML/L1 facts 和逐页截图中复核 section、page setup、header/footer、
     page numbering 和 numbering 的完整稳定 identity/value；
   - 补齐当前骨架文件缺失的 scored items、冻结输入和视觉证据；
   - verifier、route-eval、judge 使用同一 T4 canonical view，T4 认证为 `VERIFIED`。
7. T5 完成三校合并 gold：
   - 校验 T2 unit、T3 element、T4 layout 到 template spec 的完整一一绑定和无损传递；
   - 通用 merge contract 留在代码，学校特定 expected binding/invariant 全部进入 gold；
   - 补齐 frozen direct input、独立报告与三校 expected，T5 认证为 `VERIFIED`。
8. POST_T6/final-template 完成三校最终 Word gold：
   - 合并并复核现有 `final_template.expected.yaml` 的全部签收项；
   - 补齐 stage-owned 值之外的最终 Word 专属 checks，并与 T2/T3/T4 identity 交叉引用；
   - 生成 old-check 到 new-check 的一一 mapping；old check 若被拆成多个 typed checks，ledger
     必须列出全部目标 ids 和分母变化；
   - 三校 template-gap 逐项可评分，`final_template` 认证为 `VERIFIED`。
9. L1、T6、T7 按当前契约不新增虚假的学校答案 gold，但必须补齐 contract/evidence
   projector、统一状态/report、frozen fixture 和 full-chain 消费验证。

`PARTIAL/MISSING/unknown` 只允许作为实施中的诚实中间状态。任何因“尚未审查、尚未补值”
产生的 unknown、任一学校阶段未 `VERIFIED`、或 L1/T6/T7 合同型评测未接通，都阻止
Plan 03 cutover 和完成。经完整复核后仍天然不可观察的 item 可以保留 `unknown`，但必须
有独立 identity、人工批准原因且不造成 scored-universe coverage 缺口。

### Phase 3：Shadow parity

在 real-core 正式 loader 仍读取旧文件时，同时从 canonical 文件投影 shadow views：

1. T3 要求 scored universe、identity、action、unknown/excluded 和 review metadata 完全一致；
   完成签核只能增加认证证据，不能改变动作答案。
2. T1/T5/final 当前已签事实要求无损；T2 page-native 与 T4 完整 scored universe 的新增
   或修正必须逐项绑定人工 review evidence，并进入 approved migration ledger。
3. 三校所有 gold-bearing stage certifications 必须为 `VERIFIED`，且不存在由未完成审核
   造成的 unknown。
4. 同一 actual 分别用旧 standard 和新 projected view 运行 verifier/judge，比较：
   - stage status；
   - mismatch identity/type；
   - accuracy denominator/numerator；
   - first bad stage 和 owner。
5. template-gap 旧 final standard 与新 final projection 做逐项 parity，并对新增签收项
   提供人工 approval evidence。

Shadow 只比较，不提供 fallback。任何未批准差异都阻止 cutover。

#### Migration approval ledger

每校每版本保存一份机器可校验的永久审计记录：

```text
standards/targets/<target_id>/<version>/audit/<migration_id>.gold-migration.yaml
```

ledger 至少包含：

```yaml
artifact_type: school_template_gold_migration_approval
migration_id: canonical_gold_v1_20260725
target_id: hunannongye
template_version: v1
source_files:
  - path: template_generation/t3_element_policy.standard.yaml
    file_sha256: sha256:...
candidate:
  path: school_template.gold.yaml
  canonical_file_sha256: sha256:...
  canonical_semantic_sha256: sha256:...
projection_contract_version: school-template-gold-projection-1.0
stage_diffs:
  t3:
    old_view_sha256: sha256:...
    new_view_sha256: sha256:...
    difference_class: none
  t2:
    difference_class: schema_translation
    approved_items:
      - identity_ref: unit:cover
        field: boundary
        reason: translated to approved page-native field shape
approval:
  status: approved
  approved_by: <human standard owner>
  approved_at: <timestamp>
  approval_basis: <review or plan reference>
```

允许的 difference class 只有：

- `none`；
- `relocation_only`；
- `deduplication`；
- `contract_extraction`；
- `schema_translation`；
- `approved_semantic_change`，且必须引用独立已批准 issue/plan/review。

Plan 03 的 T3 不允许 `approved_semantic_change`；T3 scored identity/action 必须零差异。
迁移工具只能生成 `approval.status=pending`，不能自行批准。批准者必须是用户或明确指定的
human standard owner。approval 与 candidate 的 file/semantic hash 绑定；candidate
发生任何语义变化后旧 approval 自动失效。

cutover 后 ledger 永久保留为 audit evidence，但它不是 gold、不能参与 stage projection，
也不能作为运行时 fallback。

### Phase 4：消费者原子切流

1. `target.standard.yaml` 改为只登记 `school_template.gold.yaml`。
2. T1、L1、T2、T3、T4、T5、T6、T7、POST_T6 的 standard-quality、stage verifier、
   judge、route-eval、run bundle 和 template-gap 全部通过 projector 获取 gold view
   或 contract/evidence binding view。
3. 报告由“stage standard path/hash”改为同时记录：
   - canonical gold path/file hash/semantic hash；
   - projection version；
   - stage view hash/status。
4. source rebind 只修改 shared source binding 和必要的 identity ledger；合同测试证明
   所有 stage views 自动获得同一 source hash。
5. 未配置 canonical gold、schema/version 不兼容、projection 失败或任一 gold-bearing
   stage status 非 `VERIFIED` 时保持 `UNKNOWN` 并阻止 cutover，禁止回读旧文件。

切流应作为一个原子变更完成；不能让部分消费者读 canonical、部分消费者继续读旧 YAML。

#### 消费者切流矩阵

| 消费者/位置 | 当前依赖 | 切流后唯一行为 | 删除或禁止 |
| --- | --- | --- | --- |
| `standards/targets/*/v*/target.standard.yaml` | final + T1-T5 多路径 registry | 只登记 canonical path/schema version | 所有 stage/final editable path |
| `src/docfit/harness/template_generation_standard_quality.py` | 分别加载 final/T1-T5，当前主要只有 T3 认证门禁 | 一次加载 canonical，验证六个认证、引用、owner、projection 和 hash，输出所有 stage views | `_load_final_template_expected` 式 fallback、单阶段认证特判 |
| `src/docfit/harness/template_generation_stage_verifiers.py` | 接受旧 stage payload/标准形状 | 接收已投影 view 和 normalized actual，输出统一 item comparison | 自行找 standard path、私有分母 |
| `src/docfit/harness/template_generation_judge_reports.py` | T1 无 accuracy builder；T4/T5 指标不完整；route 后段以 availability 为主 | T1-L1-T7/POST_T6 全部调用统一 metric builders，报告本计划规定的 primary metric/hard gates | `layout_contract_completeness` 冒充 accuracy、unit F1 冒充 T5、null primary metric |
| `src/docfit/template_generation/t2_standard.py` | 直接读取 `t2_unit_pagination.standard.yaml` | 改为从注入的 T2 projected view 构造只读标准对象 | 旧相对路径常量和 filesystem fallback |
| `src/docfit/template_generation/agent/t3_eval.py` | 读取/适配独立 T3 standard | 只消费 T3 projected atomic ledger；保留现有 T3 metric 语义 | stage file lookup、canonical 其他分区可见性 |
| `src/docfit/template_gap/gap.py` | 直接读取 `final_template.expected.yaml` 的 `expected.units` | 消费 final projected `required_checks`；必要时由唯一 adapter 生成旧内存形状，adapter 不落盘 | 旧路径默认值、直接读 canonical root、丢失 typed checks |
| `src/docfit/harness/template_generation_run_bundle.py` | bundle 声明旧 standard paths/hashes | bundle 记录 canonical hashes、projection version、各 stage view hash 和 actual refs | 旧 stage standard provenance |
| `src/docfit/harness/real_core.py` 与 harness tests | 注册/断言多份旧文件 | 只解析 canonical registry，构造各 stage views | baseline 中旧文件必需性 |
| `src/docfit/convert/orchestrator.py` 与正常 template generation | 不应由 gold 驱动业务生成 | 保持 gold-free；只汇总调用方已提供的 evaluation report refs/status，不直接加载/project gold | 运行时读取 canonical 并改变 T1-T7 业务产物 |

所有 public 入口必须最终汇合到同一 loader/projector/metric builder。允许在一个原子提交内
保留短生命周期的内存 shape adapter，禁止保留旧文件读路径、双读比较 fallback 或把
projected view 持久化到 `standards/`。

### Phase 5：删除旧事实源和兼容面

三校全阶段 gold `VERIFIED`、shadow parity 与真实 gate 通过后：

1. 删除每校：
   - `template_quality/final_template.expected.yaml`；
   - `template_generation/t1_document_facts.standard.yaml`；
   - `t2_unit_pagination.standard.yaml`；
   - `t3_element_policy.standard.yaml`；
   - `t4_global_layout.standard.yaml`；
   - `t5_template_spec.standard.yaml`。
2. 删除旧 path lookup、stage-file fallback、旧 hash 字段和双写脚本。
3. 增加残留合同测试：`standards/targets/*/v*/` 只能有一份可编辑 school gold，
   旧文件重新出现即失败。
4. 更新 canonical 架构、测试契约、standards README、目录说明、status 和历史 plan
   的迁移指针。

### Phase 6：文档、审计与完成状态收口

1. 更新 `docs/current/template-generation-architecture.md`：
   - stage gold/contract view envelope、owner 表和正式 consumer boundary；
   - 明确正常生成链 gold-free，评测层才可投影；
   - 正式产物字段若因实现发生变化，必须与本计划 normalizer 同步。
2. 更新 `docs/current/template-generation-testing.md`：
   - 每阶段 gold/contract 来源、primary metric、分母、hard gate 和报告字段；
   - isolated/cascade fixture 构成、fresh observation 和 false-green 反例。
3. 更新 standards README/target registry 说明，只把 canonical 文件列为人工编辑面；
   audit ledger 和调试 stage views 明确为只读证据。
4. 更新对应 status 文档：逐校逐阶段记录 certification、parity、consumer cutover、
   old-source deletion 和真实门禁结果；任一残留不能只写在最终回复。
5. plan frontmatter 只有在所有 Completion Signals 都满足后才能从 `draft` 进入仓库定义的
   完成状态；人工审核尚缺时记录 `implemented_in_part`，不得写成 verified。

## Execution Contract

### Target Capability

学校标准维护者只编辑一份 canonical school gold；所有阶段评测使用确定性投影视图，
共享事实无重复，阶段 owner、状态、评分边界和证据仍彼此隔离。三校 T1、T2、T3、
T4、T5、POST_T6/final-template 的完整学校 gold 均已复核并可评分；L1、T6、T7 的
合同型评测也通过同一 canonical binding 接入，不留下任何阶段给后续计划补完。

### Non-Goals

- 不让模板生成运行时读取 gold；
- 不用迁移过程重新定义 T3 action；
- 不绕过 Plan 12 决定 T2 页面模型；
- 不从当前 actual、AI 输出或 judge 结果自动生成正确答案；
- 不为当前测试契约明确为 contract/evidence-only 的 L1、T6、T7 虚构学校答案 gold；
- 不因完成文件合并就宣称任一阶段 gold 已人工 `VERIFIED`；
- 不永久保留旧文件 alias、双读 fallback 或双写维护。

### Entity Budget

- reuse：`target.standard.yaml`、现有 standard-quality loader、stage verifier/judge、
  template-gap 和 `template_generation.contract` 体系；
- remove/merge：三校 18 份旧 final/stage gold 文件及其重复 metadata/path loader；
- new：每校一份 `school_template.gold.yaml`、一个 versioned gold schema、一个集中式
  loader/projector package、一个共享 item comparison/report model；actual normalizers
  可以按阶段拆文件，但必须实现同一协议，不能各自维护第二套 envelope/hash/status 语义；
- expansion trigger：新增第二种 canonical 文件、持久 stage view、长期兼容 alias、
  自动 gold 编辑器或远程 gold 服务必须重新批准。

### Implementation Work Breakdown

实施按以下依赖顺序推进；每一项都在本计划和同一个 status tracker 中更新，不另建第二份
execution plan：

1. **Schema/control plane**
   - root/schema/owner/ref/comparator validation；
   - file/semantic/view hash；
   - review/certification 状态机和 source rebind；
   - synthetic canonical fixtures 与 hash/firewall 反例。
2. **Projection/data plane**
   - T1/T2/T3/T4/T5/final concrete projectors；
   - L1/T6/T7 contract template projectors 和 pre-output instantiation；
   - stage view serialization 仅写 eval/run 输出目录。
3. **Comparison plane**
   - 统一 item/report datamodel；
   - 九个 actual normalizers；
   - 本计划 9.1–9.9 的 metric builders、hard gates 和 mismatch owner。
4. **Three-school migration**
   - provenance inventory 与 pending approval ledgers；
   - canonical candidate；
   - T1/T2/T4/T5/final 缺失 scored universe 制作、人工 review；
   - T3 zero-diff migration 与六个 gold-bearing certifications。
5. **Shadow/adversarial validation**
   - old/new same-actual parity；
   - wrong-value/same-shape、missing-item、extra-item、unknown、hash mismatch、
     source rebind、false delete 和 stale fresh-observation 反例；
   - 三校 isolated/cascade/final Word review。
6. **Atomic consumer cutover**
   - 一次性切 registry、quality、verifier、judge、T2/T3 eval、gap、bundle 和 harness；
   - full regression 通过前不删除旧文件；切流失败只能整体回退该切流变更，不能启动 runtime
     fallback 或让部分消费者回旧源。
7. **Deletion/closure**
   - 删除 18 份旧事实源和 path adapters；
   - residual scans、full product gates、long-term docs/status 更新；
   - 只有此时才能关闭 Plan 03。

### Rollout 与回退边界

- Phase 1–3 的 canonical candidate 和 shadow report 不改变正式 loader，失败时修 candidate
  或 comparator/normalizer，不修改 actual 来“配合标准”。
- Phase 4 以一个可整体回退的原子变更切正式评测消费者；发现回归时回退整个 cutover commit，
  旧源仍保持冻结只读，不进行双写。
- Phase 5 只有在切流和全部门禁稳定后执行。删除后如发现严重问题，通过版本控制整体恢复
  上一个已审计状态并重新进入 Phase 3；禁止在运行时偷偷寻找旧文件。
- 正常 template generation 始终不读 gold，因此评测切流失败不能改变用户生成的业务产物；
  只能使质量状态诚实地成为 `UNKNOWN`。

### Completion Signals

必须同时满足：

1. 三校只剩一份可人工编辑 canonical school gold；
2. canonical validator 和所有 stage projectors 可确定性重算 hash；
3. 三校 `stage_certifications.t1/t2/t3/t4/t5/final_template` 全部为 `VERIFIED`，没有
   由未审核内容造成的 unknown 或 coverage 缺口；
4. T1 学校事实、T2 page-native ranges、T3 adaptive run/span actions、T4 layout、
   T5 merge expectations 和 final-template checks 都有完整 scored universe、稳定 identity、
   review evidence 和 human standard owner sign-off；
5. T3 scored identity/action parity 零差异；湖南农大绑定 `776649b4…` canonical source；
6. Plan 12 的三校 page-native gold、verifier、judge 和签署残留全部关闭；
7. L1/T6/T7 不新增学校答案 gold，但 frozen fixture、contract/evidence view、统一报告和
   full-chain owner 归因全部接通；
8. 所有评测消费者只读取 projected view，无旧文件 fallback；
9. 三校 standard-quality、逐阶段 isolated judge、cascade judge、template-gap、
   replay/full-chain 和最终 Word fresh observation 通过；
10. source-rebind 反例证明共享 hash 一次修改可传播到所有 stage views；
11. migration approval ledgers 与 canonical file/semantic hash 绑定并永久可审计；
12. residual scan 和文件布局合同证明旧事实源和 incomplete-stage bypass 无法重新进入。
13. 所有统一 stage reports 均有非空 primary metric：
    T1 `fact_coverage`、L1 `contract_coverage`、T2 `unit_f1`（同时强制 name/boundary/
    ownership gates）、T3 `exact_action_accuracy`、T4 `layout_accuracy`、
    T5 `merge_contract_accuracy`、T6 `execution_effect_accuracy`、
    T7 `verification_coverage`、POST_T6 `final_gap_status`；
14. 每个数值指标都能回到稳定 item ids、numerator/denominator 和 mismatch；T7 coverage
    与 POST_T6 status 也同时报告 checked/required，不存在只给 summary PASS 的阶段；
15. wrong-value/same-shape 反例证明 T4/T5 不再按 completeness 假绿，manifest-only 反例证明
    T6 不按 `executed` 假绿，required-check-not-run 反例证明 T7/POST_T6 不把未检查当 PASS。

### Anti-Degradation Rules

- 不用“新 canonical 文件存在”替代消费者切流；
- 不用 projection schema PASS 替代 scored item parity；
- 不把 `PARTIAL/MISSING` 当作任何学校、任何 gold-bearing stage 的最终可接受状态；
- 不用某个阶段 `VERIFIED` 掩盖其他阶段未完成；
- 不用自动生成的 stage view 作为新的人工编辑入口；
- 不用单校或单次 replay 替代三校和 source-rebind 反例；
- 不用 AI/delegated review 单独替代 human standard owner 的最终签署；
- 不删除旧文件，直到 shadow parity、消费者扫描和真实 product gates 全部通过。

### Verification Matrix

| Gate | Command / Evidence | Required Result |
| --- | --- | --- |
| schema/unit | `uv run pytest -q tests/unit/test_school_template_gold.py tests/unit/test_school_template_gold_projection.py tests/unit/test_template_generation_standard_quality.py` | strict schema、owner/ref/comparator、status、projection、hash、firewall、missing/unknown/incomplete-stage 反例通过 |
| report contract | 统一 report model/serializer tests | 九阶段均有 evaluation basis、primary metric、numerator/denominator 或 checked/required、hard gates、mismatch owner 和完整 provenance |
| contract | `uv run pytest -q tests/contract/test_real_core_baseline_harness.py tests/contract/test_template_generation_standard_judge.py tests/contract/test_real_core_generated_template_gap.py` | 三校只登记 canonical gold；T1-L1-T7/POST_T6 消费 projected gold 或 contract view |
| parity | 迁移脚本输出三校 T1–T5/final old-vs-projected semantic diff 和 approval ledger | T3 action 零差异；T1/T5/final 旧事实无损；T2/T4 新签内容逐项有批准证据 |
| T1 | 三校 canonical DOCX + sealed T1/L1 facts audit；删除/改错一个 section/header/field fact 反例 | 学校事实 universe、source identity、对象 coverage 完整且 `VERIFIED`；缺失/错值降低 `fact_coverage` 并指向 T1 |
| L1 | frozen T1/render/object-page binding；断开一个 ref/hash 和 visual unavailable 反例 | `contract_coverage` 分母稳定；明确错误 FAIL、必需观察不可得 UNKNOWN，无学校 gold |
| T2 | Plan 12 completion gates + 三校人工页面 review；同 unit set 但改 name/boundary、制造 gap/overlap/extra page 反例 | 每页唯一归属、range 连续；unit F1 不能遮盖 name/boundary/ownership 失败，T2 `VERIFIED` |
| T3 | 三校 frozen L1 adaptive ledger audit；漏 item、冲突 action、false delete 反例 | raw-run/span 全覆盖无重叠缺口；action/denominator 迁移不变；false delete hard fail，T3 `VERIFIED` |
| T4 | Word/OOXML/L1/page screenshot review；保留全部 key 但改 margin/header scope/page number start 反例 | 五维 leaf universe 完整；wrong-value 使 `layout_accuracy<1`，不能由 completeness 假绿，T4 `VERIFIED` |
| T5 | frozen T2/T3/T4 finals；unit 不变但删 element binding、改 section ref/hash、错误升级 availability 反例 | `merge_contract_accuracy` 和对应 binding/hard gate 失败；无丢失、重复或重推断，T5 `VERIFIED` |
| T6 | frozen T5 final + final DOCX fresh observation；manifest 标 executed 但 Word 无效果、stale observation hash 反例 | `execution_effect_accuracy` 只认 fresh effect；前者 FAIL、后者 UNKNOWN，无学校 gold |
| T7 | frozen L1/T5/T6/final artifacts；省略 required check、错 first_bad_stage/owner 反例 | coverage 降低或 UNKNOWN；归因错误结构化失败，不允许 summary PASS，无学校 gold |
| standard quality | `uv run docfit eval template-generation-standard-quality --profile real-core-v0 --out <out>` | 三校所有 gold-bearing stages 为 VERIFIED；报告记录 canonical/view hash |
| judge | 三校 isolated + cascade `docfit eval template-generation-judge` | 各阶段可独立评分，stage status、mismatch、first_bad_stage 和 owner 可解释 |
| final gap | 三校 `docfit eval template-gap` 使用 final projection；分别改 content/style/page/header/field/numbering，及令 required check 不可观察 | 完整 typed universe 可评分；各类错误落到稳定 check id；unchecked 为 UNKNOWN；新旧逐项差异有批准证据 |
| product run | 三校固定 replay 的 `docfit template verify` + final DOCX fresh observation | full-chain 消费 canonical projected views；无 hash 串线，Word 效果可观察 |
| source rebind | synthetic source-hash change + 湖南农大回放 | 共享 hash 只改一处；所有 view hash 更新且旧 hash 被拒绝 |
| hash semantics | 只改 YAML 注释/缩进、只改无关阶段、修改当前阶段三组反例 | file/semantic/view hash 分别按定义变化，不发生全阶段伪变化 |
| approval | 修改已批准 candidate 后重跑 cutover gate | hash 不一致使 approval 失效；pending/AI-approved ledger 均阻断 |
| consumer atomicity | 对 registry/loader/verifier/judge/gap/run-bundle 做 import/call-site scan，并模拟一个消费者仍请求旧 path | 所有入口汇合到同一 projector；任一旧读取使 gate 失败，不允许混合 cutover |
| residual | `rg` 扫旧文件名、fallback、stage-file registry 和重复 unit/source/review 字段 | 生产读取与 standards 旧文件为零 |
| full regression | `uv run pytest -q` | 全部通过 |

### Residual Policy

- 任一学校的 T1/T2/T3/T4/T5/final-template 未完成或未签署：Plan 03 保持
  `implemented_in_part`，不得 cutover、删除旧文件或标记 verified。
- Plan 12 未完成：同时阻止 T2 和 Plan 03 verified；不能转交给“后续再补”。
- T4 人审未完成：阻止 Plan 03 verified；本计划继续完成 T4，不另开计划卸载范围。
- L1/T6/T7 contract/evidence 评测未接通：阻止 full-chain 完成，即使它们不拥有独立
  学校答案 gold。
- shadow parity 有未批准差异：保持旧 loader，输出 `implemented_in_part`，不得删旧文件。
- 发现新的业务语义冲突：在本计划中停止并请求决定；只有经用户明确批准缩小范围时，
  才能另开后续 issue/plan，不能默认延期。

## Preflight Contract

Preflight status: DRAFT

Task source: user request + STAGE-STANDARDS-ISSUE-03

Canonical source: 本计划

Route: durable `$intuitive-flow`；其中 schema/loader/projector/consumer seam 使用
`$intuitive-refactor` 子路线，主会话监督全阶段 gold 审核和分阶段 stop gate

Goal: 把每校多份独立 gold 收敛为一份 canonical school gold，补齐并签署三校所有
gold-bearing stage 内容，同时让 T1-L1-T7/POST_T6 全部评测代码消费确定性投影视图。

Scope: canonical schema/hash/review-reference model、T1-L1-T7/POST_T6 projector/consumer、
三校 T1/T2/T3/T4/T5/final-template 完整 gold 制作与审核、shadow parity、approval ledger、
消费者原子切流、旧事实源删除。

Non-goals: 改变各阶段既定 owner 或 T2 page-native/T3 AI-only 契约；为 L1/T6/T7
虚构学校答案 gold；让正常模板生成读取 gold；保留长期双读/双写。

Acceptance:

- SUCCESS: 三校单一事实源切流、旧文件删除；T1/T2/T3/T4/T5/final-template 全部
  `VERIFIED`；L1/T6/T7 contract/evidence 评测接通；T3 零差异；
  approval/hash/isolated/cascade/最终 Word 门禁全部通过。
- BLOCKED_NEEDS_DECISION: 出现 owner 冲突或 semantic diff，但没有独立人工批准依据。
- BLOCKED_NEEDS_LOCAL_VALIDATION: 三校 Word/截图人工 review、standard-quality、isolated/cascade
  judge、template-gap、replay 或最终 Word fresh observation 无法执行。
- INTERMEDIATE_ONLY: 任一阶段 gold 未 VERIFIED、shadow loader/projector 已落地但消费者
  未原子切流，或旧文件未删除。
- No regressions: T1-T5 既定 owner、T2 page-native、T3 scored universe/action、
  final-template gap 既有语义和非 gold 业务流程不回退。

Verification: deterministic=unit/contract/full pytest；integration=三校 parity、standard-quality、
isolated/cascade judge、template-gap；product-run=三校固定 replay `docfit template verify`
与最终 Word fresh observation；local-live-manual=逐校 T1-T5/final Word/截图 review packet
和 human standard owner 全阶段签署，缺少任一项即不能完成。

To execute: `/goal execute docs/plans/2026-07-25-template-parse-refactor-stage-standards-plan-03-canonical-gold-stage-projections.md with intuitive-flow`

Approval: 用户回复 LGTM/approve/go ahead 后进入实施；对数据模型、hash、approval ledger、
兼容期或架构完成边界的修改应先修订本计划。
