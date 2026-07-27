# T5 最终产物与 T6 动作契约（讨论稿）

> Status: discussion draft
>
> Updated: 2026-07-25
>
> Canonical target: [`../current/template-generation-architecture.md`](../current/template-generation-architecture.md) 的 T5/T6 章节，以及 [`../current/content-field-and-slot-contract.md`](../current/content-field-and-slot-contract.md) 的模板槽位章节
>
> Non-goal: 本文不直接修改正式阶段契约、运行代码、文件编号或现有标准。

## 1. 本文要决定什么

这次需要确定两个阶段边界：

1. T5 在合并 T2 单元、T3 元素策略和 T4 全局版式后，应该发布什么样的最终产物；
2. T6 可以根据 T5 产物执行哪些 Word 动作，以及哪些判断绝不能留给 T6。

建议先用一句话固定边界：

> **T5 按单元冻结内容目标，并用独立 layout contract 冻结 page/section/global 目标；T6 以单元为内容事务和保护边界，另用 layout 通道执行共享版式。**

这意味着：

- T5 不是简单拼接器，也不直接修改 Word；
- T6 可以选择具体 OOXML 实现方式，但不能新增单元、元素、槽位、字段、固定文字或版式语义；
- T6 的每个修改都必须能回指 T5 中的一项明确要求；
- T5 确认无需修改的单元，T6 不生成任何内容修改动作，只证明该单元保持不变；
- T6 无法精确定位或无法证明结果时，必须停止该项动作并报告，不能扩大修改范围。

## 2. 当前实现已经做到什么

当前链路是：

```text
T2 final unit_map
T3 final element_spec
T4 final global_spec
sealed L1 identity/hash
        │
        ▼
T5 05_template_spec.yaml
        │
        ▼
运行内 template_generation_plan
        │
        ▼
T6 06.1_fillable_template.docx
   + 06.2_build_manifest.json
```

当前 `05_template_spec.yaml` 已经包含：

- L1、T2、T3、T4 的 hash 和 final 引用；
- T4 全局版式；
- 按 T2 顺序组织的 `units[]`；
- 每个单元的 source identity、`page_policy` 和 section binding；
- 每个单元下的 T3 `elements[]`；
- review flags 和 availability。

当前 T6 已经能够执行以下动作：

| 当前动作 | 作用 |
| --- | --- |
| `copy_source_docx` | 复制源 DOCX package 作为修改底稿 |
| `preserve_whole_unit_copy` | 声明整个单元由源文件复制结果保留 |
| `remove_instruction_text` | 删除明确的说明文字、run 或字符范围 |
| `replace_span_with_slot` | 把精确示例值或占位 span 替换为 Word SDT 槽位 |
| `create_fillable_slot` | 在明确 source anchor 上创建可填写 SDT |
| `create_generated_field_placeholder` | 创建系统生成字段的占位 SDT |
| `insert_fixed_text` | 在明确位置补入固定文字 |
| `insert_synthetic_unit_title_before` | 在单元前补一个标题段落 |
| `ensure_body_slot` | 兜底创建正文入口槽位 |
| `insert_page_break_before_unit` | 在单元前设置分页边界 |
| `insert_section_break_before_unit` | 在单元前设置分节边界 |
| `set_keep_together_unit` | 用 keepLines、keepNext、cantSplit 等非侵入式属性保持单元结构 |

当前安全机制也已经具备：

- 校验源 DOCX hash 与 sealed L1；
- 通过 L1 resolver 校验 source/run/char-range 身份；
- required upstream 不可用时保守阻断相关动作；
- 在 manifest 中记录已执行和待复核动作；
- 重新打开最终 DOCX，观察分页、分节和 keep 等实际效果；
- 最终 Word 不允许残留 `[[DOCFIT_*]]` 内部 marker。

## 3. 当前边界仍然不清楚的地方

### 3.1 T6 同时承担了“编译动作”和“执行动作”

`template_generation_plan` 目前由程序在 T5 之后临时生成，但不是编号公开产物。它会把：

- T2 `page_policy` 转成分页、分节或 keep 动作；
- T3 `policy` 转成删除、槽位或 generated 动作；
- T5 中的 source identity 转成具体 action target。

这部分转换本身合理，但目前还混入了 T5 没有明确声明的业务默认值，例如：

- 无条件兜底 `ensure_body_slot`；
- 根据默认单元 ID 选择整单元复制；
- 根据 `toc` 和元素内容补 synthetic title。

这些不是单纯的 Word 写入细节。它们会改变最终模板具有什么槽位、文字和结构，因此不能只藏在 T6 代码里。

### 3.2 T5 只保留 `fill` 元素，没有发布完整 `TemplateSlot`

跨阶段字段契约已经要求模板槽位至少说明：

```yaml
slot_id: target-slot-abstract-zh
accepts_field_keys:
  - abstract.zh.body
target_style_ref: abstract-body
```

但当前 T6 manifest 中的 `slots[]` 主要记录：

- `slot_id`；
- `unit_id` / `element_id`；
- `sdt_tag`；
- `output_ref`；
- `source_seq_refs`。

它还不能完整回答：

- 这个槽位允许接收哪些学生内容字段；
- 接收单值、列表还是递归内容树；
- 是行内槽位、块级槽位还是容器槽位；
- 最终渲染应使用什么样式或格式；
- 这个槽位是 T5 明确要求的，还是 T6 自己兜底创建的。

如果不补齐，后续“内容匹配与放置”仍然无法只靠正式产物工作。

### 3.3 T5 描述上游语义，但没有逐项声明最终效果

例如：

```text
T3 policy = fill
```

还不能唯一确定：

- 替换已有示例值，还是在固定标签后新增槽位；
- 使用行内 SDT、块级 SDT，还是整个单元容器；
- 接受哪个 `field_key`；
- 是否保留原字符样式；
- 失败时允许退化为空槽位、保留原文，还是必须人工复核。

同样：

```text
T2 page_policy.start = new_page
```

表达的是目标页面边界，不应直接等同于某个固定 OOXML 操作。T6 可以根据现有分节结构选择 page break 或 section break，但必须证明最终效果满足 T5 要求。

### 3.4 availability 只有总状态还不够

T5 的总 availability 对 T2/T3/T4 做保守合并是正确的，但 T6 仍需要知道每项要求依赖哪个上游：

- 分页效果依赖 T2；
- 元素删除和槽位依赖 T3；
- section、页眉页脚和全局版式依赖 T4；
- 所有物理修改都依赖 L1 identity 和源 package hash。

当 T3 不可用而 T2 可用时，T6 可以执行分页要求，但不能执行删除或槽位要求。这个能力不应依赖 T6 临时解析 T5 的 lineage 猜测，而应由 T5 对每项要求显式声明依赖和可用性。

### 3.5 当前 action 带有 `unit_id`，但执行器还不是单元级执行

当前 action 已经记录 `unit_id`，分页结果也按 unit 汇总；但 executor 仍然遍历一条全局 action 列表：

```text
for action in plan.actions
  → 校验
  → 立即修改共享 Word
```

当前还没有：

- 单元级 execution mode；
- 单元 action allowlist；
- 未修改范围的保护指纹；
- 单元完成后的独立 postcondition；
- 单元失败后的回滚或整单元阻断。

因此，“action 上有 unit_id”只表示可以归因到单元，不等于已经以单元为执行和稳定性边界。

### 3.6 当前 T5 已经把部分 section 信息复制进 unit

实际代码和运行产物表明：

- T2 unit 不包含独立“页面样式”，只包含 `page_policy`、source binding 和 `section_profile` 引用；
- T2 page-first Stage Input 会给模型每页节点的 `style/text_facts`，但它们只是识别单元的客观证据；T2 AI final 仍只输出 `unit_id/unit_name/page boundary`，这些样式不能成为 unit 所有的版式契约；
- T4 `global_spec` 顶层保存 section profiles、page setup、页边距、页尺寸、页码、页眉页脚、numbering 和 default font；
- T5 顶层完整嵌入 T4 `global_spec`；
- T5 `units[].section_profile_refs[]` 当前还复制了 section 的 `page_numbering.declared/display` 和 header/footer inheritance；
- T5 `units[].elements[].style` 是元素自己的局部字体、字号等样式摘要，不是页面全局样式。

Word 中通常不存在一个独立、稳定、归某一页所有的“page style”对象。页面效果主要来自：

```text
section properties
+ paragraph page/break/keep properties
+ header/footer
+ styles/numbering
+ 当前内容流的渲染结果
```

一个 unit 可以跨多个 section，一个 section 也可以覆盖多个 unit。因此，section/page/header-footer/numbering 不能成为某个 unit 独占拥有的内容字段。

目标契约应收敛为：

```text
unit
  -> 只保存 content/source identity、element、slot、content effect
  -> 只引用 page/section/layout contract id

layout_contract
  -> 保存 section/page/header-footer/numbering 的目标值
  -> 声明 affected_unit_ids 和真实 OOXML scope
```

T5 unit 内不应复制完整 page setup、page numbering、header/footer 或 global style 内容。

## 4. 三种可选边界

### 方案 A：T5 只做上游拼接，T6 自己决定动作

```text
T5 = merged T2/T3/T4
T6 = 解释语义 + 生成动作 + 执行动作
```

优点：

- 最接近当前实现；
- T5 schema 改动小。

问题：

- T6 会继续积累隐藏业务规则；
- 同一个 T5 可能因 T6 版本不同而产生不同槽位和结构；
- 很难证明 T6 没有重新做 T2/T3/T4 判断；
- 内容放置阶段拿不到 T5 预先定义的槽位契约。

不建议作为目标架构。

### 方案 B：T5 直接输出低层 Word action 列表

```text
T5 = 完整 OOXML action plan
T6 = 纯 action executor
```

优点：

- T6 边界最窄；
- 每项动作都能在执行前审核。

问题：

- T5 会绑定具体 Word 库和 OOXML 实现；
- `page_policy` 这样的目标语义会过早固化成 page break 或 section break；
- 更换执行器或优化 Word 操作时必须修改 T5 契约；
- 低层动作不适合成为内容匹配阶段的业务接口。

不建议把低层 OOXML action 作为 T5 canonical final。

### 方案 C：T5 输出声明式构建契约，T6 编译并执行（建议）

```text
T5 = 目标模板蓝图 + 原子 required effects + logical slots
T6 = required effects -> concrete Word actions -> execution -> observation
```

这里的 `required effect` 表示“最终 Word 必须观察到什么”，不是“必须调用哪个函数或写哪个 XML 节点”。

例如：

```text
T5 effect:
  abstract_cn 必须从新页开始

T6 可选实现:
  已有合适 section boundary -> 复用并验证
  需要独立页码/页眉页脚 -> 插入 section break
  只需要换页 -> 设置 pageBreakBefore
```

这个边界同时满足：

- T5 完整冻结产品语义；
- T6 不重新判断上游语义；
- T6 仍可根据真实 Word 结构选择安全实现；
- 测试可以分别检查 T5 effect 是否正确、T6 effect 是否实现。

## 5. 建议的 T5 最终产物

### 5.1 只保留一个 canonical 业务输入

建议 T5 继续只发布一个 canonical 业务产物：

```text
05_template_spec.yaml
```

但将其升级为可独立驱动 T6 的声明式构建契约。T5 verifier 可以另产验证报告，但验证报告只是证据，不是 T6 的第二业务输入。

T6 的唯一语义输入仍然是：

```text
T5 final 05_template_spec.yaml
```

源 DOCX package 和 sealed L1 只提供物理对象与身份解析，不提供新的语义判断。

### 5.2 T5 final 的建议结构

```yaml
artifact_type: template_spec
artifact_version: "2.0"
stage_id: T5
result_role: final

availability:
  status: AVAILABLE
  reason: null
  components:
    t2: AVAILABLE
    t3: AVAILABLE
    t4: AVAILABLE

source_contract:
  source_template_docx_hash: sha256:...
  l1_artifact: 01.5_l1_input_contract.json
  l1_hash: sha256:...

input_refs:
  t2_final: {artifact: 02_unit_map.yaml, sha256: sha256:..., availability: AVAILABLE}
  t3_final: {artifact: 03_element_spec.yaml, sha256: sha256:..., availability: AVAILABLE}
  t4_final: {artifact: 04_global_spec.yaml, sha256: sha256:..., availability: AVAILABLE}

layout_contracts: []
boundary_contracts: []
units: []
slot_specs: []
required_effects: []
blocked_effects: []
review_flags: []
review_decisions: []
```

建议避免把完整 T2/T3/T4 final 连同各自的 producer、lineage 和诊断字段原样嵌套一遍。T5 应只保留：

- T6 必须消费的规范化字段；
- 上游 hash 和 trace；
- 审核必须看到的 flags。

这样 T5 是“链接后的中间表示”，不是三个上游文件的压缩包。

### 5.3 `units[]`

每个 unit 至少包含：

```yaml
- unit_id: abstract_cn
  order: 5
  source_binding:
    source_refs: []
    source_seq_refs: []
  layout_bindings:
    page_refs: []
    section_profile_refs:
      - section_002
    boundary_contract_refs:
      - boundary.toc.abstract_cn
  page_requirement:
    start: new_page
    scope: page_range_exclusive
  element_refs: []
  effect_refs: []
```

`units[]` 描述：

- 单元是什么；
- 它绑定哪些源对象；
- 它有哪些元素、槽位和内容 required effect；
- 它关联哪些 page、section 和 boundary contract。

它不复制 page setup、页眉页脚、页码或 global style 的完整值，也不包含具体 `insert_page_break_before_unit` 或 `set_keep_together_unit` 动作。

#### 5.3.1 每个单元必须有独立执行契约

为了让 T6 能稳定地以单元为单位执行，T5 应在每个 unit 中发布：

```yaml
- unit_id: integrity_statement
  source_binding:
    source_refs: []
    source_seq_refs: []
  layout_bindings:
    page_refs: []
    section_profile_refs:
      - section_003
  execution_contract:
    content_mode: preserve_exact
    content_effect_refs: []
    mutable_content_refs: []
    protected_content_refs:
      - unit:integrity_statement/content
      - unit:integrity_statement/objects
      - unit:integrity_statement/local-formatting
    precondition_fingerprint: sha256:...
    on_failure: block_unit
```

建议把单元内容执行模式限定为：

| `content_mode` | 含义 | T6 行为 |
| --- | --- | --- |
| `preserve_exact` | 上游判断完整，确认整个单元内容无需修改 | 不生成内容修改 action，只校验保护指纹 |
| `patch_exact` | 单元内存在少量明确 effect | 只允许修改 `mutable_content_refs`，其余范围全部保护 |
| `construct_explicit` | T5 明确要求创建源模板中不存在的新单元或结构 | 只按 T5 给出的内容、anchor 和格式构建 |
| `preserve_fallback` | 上游不可用或判断不完整，只能为安全保留 | 不修改内容，但不能把该单元标成“确认正确” |

页面和全局版式不进入 unit `execution_contract`。unit 只保存 `layout_bindings`：

```yaml
layout_bindings:
  page_refs:
    - page_004
  section_profile_refs:
    - section_003
  boundary_contract_refs:
    - boundary.abstract_cn.body_main
```

对应的真实值和动作要求在顶层 `layout_contracts[]` / `boundary_contracts[]` 中：

```yaml
boundary_contracts:
  - boundary_contract_id: boundary.abstract_cn.body_main
    previous_unit_id: abstract_cn
    next_unit_id: body_main
    required_effect: next_unit_starts_new_page
    affected_ooxml_scope:
      - word/document.xml:p[88]/pPr
```

这表示：

> unit 的文字、表格、图片、对象和局部字符格式由单元执行契约保护；页面、分节和共享样式由独立 layout/boundary contract 执行。

这样既能做到单元内容 no-op，也不会把共享 section/global 状态错误塞进某一个 unit。

#### 5.3.2 “无需修改”与“因为不知道所以不改”必须分开

以下两种情况不能使用同一状态：

```text
T3 可用且完整覆盖，单元所有内容都是 fixed/template_default，没有内容 effect
→ content_mode=preserve_exact
→ 这是经过确认的 no-op

T3 NOT_AVAILABLE，系统不知道单元内是否存在 fill/delete
→ content_mode=preserve_fallback
→ 这是安全保留，不是确认无需修改
```

否则 T6 的稳定策略会制造假绿：Word 的确没被改坏，但产品要求也可能没有完成。

#### 5.3.3 单元保护范围

T5 应为每个 unit 明确：

- `mutable_content_refs`：本单元唯一允许改变的 source/run/span/object 引用；
- `protected_content_refs`：本单元必须保持不变的内容、结构、对象和局部格式范围；
- `content_effect_refs`：允许变更的唯一业务原因；
- `precondition_fingerprint`：执行前单元事实与结构指纹；
- `on_failure`：单元失败后停止、回滚或转人工复核。

`preserve_exact` 单元必须满足：

```text
content_effect_refs 为空
mutable_content_refs 为空
T6 不为该单元生成内容 action
执行后 protected content fingerprint 不变
```

这里的“不变”优先指规范化 OOXML 内容子树、可见内容、局部格式、对象关系和关键属性不变，不强求整个 DOCX zip 的原始字节完全相同。不同 Word 库保存文件时可能重排无业务意义的 XML 或 package 字节；但任何非 T5 授权的可见内容、结构、局部格式或对象变化都必须被检测出来。

page/section/global action 改变的授权属性不进入 content fingerprint，而进入独立 layout fingerprint。两类指纹必须分开，避免合法分页动作把 `preserve_exact` 单元误判成内容被改，也避免全局样式副作用逃过检查。

### 5.4 `layout_contracts[]` 与 `boundary_contracts[]`

page、section 和 global layout 在 T5 顶层只维护一份：

```yaml
layout_contracts:
  - layout_contract_id: layout.section_003
    scope:
      kind: section
      section_profile_id: section_003
      source_ref: word/document.xml:p[87]/sectPr
    affected_unit_ids:
      - abstract_cn
      - body_main
    target:
      page_size: {}
      page_margins: {}
      orientation: portrait
      page_numbering: {}
      header_footer_refs: []
    effect_refs: []

boundary_contracts:
  - boundary_contract_id: boundary.abstract_cn.body_main
    previous_unit_id: abstract_cn
    next_unit_id: body_main
    target:
      next_unit_starts_new_page: true
    effect_refs: []
```

unit 内的引用必须保持轻量：

```yaml
layout_bindings:
  page_refs:
    - page_004
  section_profile_refs:
    - section_003
  boundary_contract_refs:
    - boundary.abstract_cn.body_main
```

禁止在每个 unit 内重复：

- `page_size/page_margins/orientation`；
- `page_numbering.declared/display`；
- header/footer part 内容；
- numbering definitions；
- global default font；
- 完整 section profile。

`page_refs` 只表示渲染页归属和证据坐标，不表示每页拥有一份可直接执行的 style。

元素自己的 `style` 可以保留在 `elements[]`，但必须标明它是 source-local observation。只有 T5 另有 `apply_format_contract` effect 或 slot `target_format_ref` 时，T6 才能修改局部格式；不能把某个 element 的 style 推广到整个 unit、页面或 section。

### 5.5 `slot_specs[]`

T5 必须把 T3 `fill` 语义和跨阶段字段契约编译成 logical slot：

```yaml
- slot_id: slot.cover.student_name
  unit_id: cover
  element_id: e_student_name
  slot_kind: inline
  accepts_field_keys:
    - metadata.student.name
  accepts_node_types:
    - person_name
  cardinality:
    min: 1
    max: 1
  required: true
  anchor:
    mode: replace_source_span
    source_ref: word/document.xml:p[12]
    raw_run_ids:
      - p_0012.r_002
    char_ranges:
      - raw_run_id: p_0012.r_002
        start: 0
        end: 2
  target_format_ref: cover.student-name
  placeholder_policy: empty
  source_trace_refs: []
  availability:
    status: AVAILABLE
    depends_on:
      - T3
```

规则：

1. `slot_id` 在 T5 确定，T6 不得另造；
2. `accepts_field_keys` 和 `accepts_node_types` 在 T5 确定，T6 原样实现；
3. `anchor` 必须能通过 L1 精确解析；
4. `target_format_ref` 指向 T4 或模板样式契约；
5. T6 只能补充真实 `sdt_tag`、`output_ref` 和执行结果；
6. T5 没有声明的 body slot、目录 slot 或元数据 slot，T6 不得静默新增。

### 5.6 `required_effects[]`

建议使用有限、声明式的 effect 枚举：

| `effect_type` | T5 表达的目标 |
| --- | --- |
| `preserve_source` | 指定源结构和可见内容必须保留 |
| `remove_source` | 指定 run/span/object 不应出现在最终模板 |
| `realize_slot` | 指定 logical slot 必须在目标 Word 中存在 |
| `realize_generated_field` | 指定目录、页码或其他系统字段必须存在 |
| `ensure_fixed_content` | 指定固定文字必须在明确位置存在 |
| `ensure_page_boundary` | 指定单元必须从文档开头、新页或允许同页开始 |
| `ensure_section_boundary` | 指定单元必须位于明确 section 边界 |
| `ensure_keep_scope` | 指定范围需要不可拆行、段落跟随或表格行不可拆分 |
| `apply_section_layout` | 指定页型、方向、边距、页眉页脚和页码等 section 目标 |
| `apply_format_contract` | 指定槽位或固定元素使用的目标样式/格式 |

单项结构建议为：

```yaml
- effect_id: effect.cover.student_name.slot
  effect_type: realize_slot
  scope_ref: slot.cover.student_name
  target_identity:
    source_ref: word/document.xml:p[12]
    raw_run_ids:
      - p_0012.r_002
  depends_on:
    - L1
    - T3
  availability: AVAILABLE
  preconditions:
    source_text_hash: sha256:...
    identity_binding: exact
  desired_result:
    slot_id: slot.cover.student_name
    source_text_absent: true
    fixed_sibling_text_preserved: true
  allowed_realizations:
    - replace_run_range_with_inline_sdt
  on_failure: needs_review
  trace_refs: []
```

T5 的 effect 必须声明：

- 目标效果；
- 精确作用范围；
- 依赖哪个上游；
- 执行前置条件；
- 允许的实现类别；
- 执行后应观察到什么；
- 失败时如何处理。

### 5.7 `blocked_effects[]`

如果上游不可用、身份不完整或 review flag 阻断，T5 仍应保留被阻断的要求：

```yaml
- effect_id: effect.abstract_cn.body.slot
  effect_type: realize_slot
  availability: NOT_AVAILABLE
  depends_on:
    - T3
  reason: T3 final is NOT_AVAILABLE
  fallback: preserve_source
```

这样 T6 可以生成安全预览，但不会把“没有动作”误解为“本来就不需要动作”。

## 6. T6 可以执行哪些动作

### 6.1 T6 的固定执行流程

```text
1. 校验 T5 final、源 DOCX hash 和 L1 hash
2. 按 T5 units[] 建立 unit execution bundles
3. 把每个单元的 required effects 编译成具体 Word action plan
4. 校验单元保护范围、每个 action 的精确身份和前置条件
5. 以单元为事务边界，在源 package 副本上执行动作
6. 检查本单元 effect postcondition 和 protected fingerprint
7. 单元验证通过后提交；失败则回滚或阻断该单元
8. 单独执行并验证 global/boundary actions
9. 保存并重新打开最终 DOCX
10. 对全部单元和 effect 做 fresh expected vs observed
11. 发布最终 Word、manifest 和 realized slot catalog
```

T6 可以生成具体 action plan，但该 plan 必须完全由 T5 effect 确定性编译，并完整写入 manifest。它不能成为一条不留痕的旁路。

#### 6.1.1 单元级事务

T6 不应直接遍历一条全局 action 列表并不断修改同一份 Word。建议先形成：

```text
unit_execution_bundles[]
├── unit_id
├── execution_contract
├── precondition_fingerprint
├── allowed_content_effects
├── planned_actions
├── protected_content_refs
└── expected_postconditions
```

执行时：

1. `preserve_exact`：不进入内容修改器，只做前后保护校验；
2. `patch_exact`：只执行该单元 allowlist 中的 action；
3. `construct_explicit`：只在 T5 指定 anchor 构建新单元；
4. `preserve_fallback`：保持复制结果，记录 unresolved requirement；
5. action 完成后立即检查本单元目标效果和非目标内容范围；
6. 任一 action 或保护检查失败，该单元不得以部分成功状态继续提交。

“事务边界”要求 T6 能在单元失败时丢弃该单元的候选修改，或恢复执行前的相关 XML parts。不能出现：

```text
单元内 5 个动作成功 3 个
→ 保存半修改 Word
→ manifest 只把另外 2 个标成 needs_review
```

首版如果还不能安全实现单元级回滚，应在执行前完成全部 precondition，并在任一风险不可控时整单元不执行。

#### 6.1.2 global 和跨单元边界不能伪装成单元内容动作

有些动作天然不只属于一个单元：

- 两个单元之间的 page/section boundary；
- 多个单元共享的 style、numbering、header/footer；
- document-level settings。

它们必须进入顶层 `layout_execution_bundles[]` 或 `boundary_execution_bundles[]`，并使用独立 scope：

```yaml
scope:
  kind: boundary
  previous_unit_id: toc
  next_unit_id: abstract_cn
```

```yaml
scope:
  kind: global
  target_ref: word/styles.xml
```

边界动作可以修改下一单元首段的 `pPr`，但不能修改该单元的文字、run、表格或对象。全局动作必须列出所有 `affected_unit_ids`。

执行后分别验证：

- 受影响 unit 的 content fingerprint 仍然不变；
- layout fingerprint 只在 T5 授权属性上发生预期变化；
- 共享 section/style/header/footer 的其他消费者没有出现未声明副作用。

### 6.2 输入和准备动作

T6 可以：

- 校验 T5 `result_role=final`、artifact type、hash 和 availability；
- 校验源 DOCX package 与 T5/L1 绑定；
- 复制完整 DOCX package；
- 建立只读 L1 identity resolver；
- 检查 effect 的 source/run/span/object precondition。

这些动作不改变业务语义。

### 6.3 内容和结构动作

当 T5 有明确 effect 且身份精确时，T6 可以：

- 原样保留段落、表格、图片、文本框、字段、页眉页脚和其他源对象；
- 删除精确字符范围、raw run、段落、表格单元格内容或明确对象；
- 保留容器结构，只删除容器内部的指定内容；
- 把已有示例值或占位范围替换为 inline/block SDT；
- 在明确 anchor 前、后或内部创建 SDT；
- 插入 T5 已声明的固定文字；
- 创建 T5 已声明类型的 generated field 或字段占位；
- 保留原 run/paragraph/table 样式，或应用 T5 指向的目标格式契约。

删除和替换必须遵循：

```text
精确 span > 精确 raw run > 精确 source object
```

无法证明较粗范围全部属于同一 effect 时，不得从 span 扩大到 run、段落、表格或整个单元。

### 6.4 页面、分节和版式动作

当 T5 有明确 layout effect 时，T6 可以：

- 复用已经满足要求的现有 page/section boundary；
- 设置 paragraph `pageBreakBefore`；
- 插入 next-page section break；
- 设置 `keepLines`、单元内部 `keepNext` 和 table row `cantSplit`；
- 应用 T5 明确的页面尺寸、方向和边距；
- 绑定或生成 T5 明确的页眉页脚；
- 设置 T5 明确的页码格式、起始值和字段；
- 应用 T5 明确的 numbering 和 style contract。

T6 不得为了“看起来保持一页”而压缩字体、间距、页边距、行高或表格尺寸。除非这些值本身就是 T5 的明确目标格式。

### 6.5 槽位动作

对于每个 T5 logical slot，T6 可以：

- 创建稳定 `w:sdt`；
- 写入稳定 `w:tag` 和 alias；
- 选择 inline、block、cell 或 container realization；
- 保留 anchor 周围的固定标签、字符样式和段落结构；
- 记录槽位真实 `output_ref`；
- 检查最终 DOCX 中 `slot_id`、tag 和位置是否唯一；
- 把 T5 的字段接受范围、cardinality 和格式引用原样带入 realized slot catalog。

T6 不可以：

- 根据标签文字猜 `accepts_field_keys`；
- 把所有槽位都标成 `body_content`；
- 因为没找到正文槽位就自行追加一个；
- 合并两个语义不同的 logical slot；
- 把一个 logical slot 拆成多个槽位而不回写明确结果。

### 6.6 收尾和观察动作

T6 可以：

- 清除内部临时 marker；
- 保存、重新打开并重新解析最终 DOCX；
- 计算最终 DOCX hash；
- 观察 SDT、field、分页、分节、keep、样式和对象结果；
- 对每个 T5 effect 输出 expected vs observed；
- 将失败项标成 `needs_review`、`precondition_failed`、`execution_failed` 或 `postcondition_failed`。

`executed` 只表示操作调用完成。只有 postcondition 在 fresh DOCX 中成立，effect 才是 `satisfied`。

## 7. T6 明确不能做什么

T6 不得：

1. 重新判断单元是什么，或修改 T2 unit 边界；
2. 重新判断元素是 `fixed/template_default/fill/generated/instruction_remove`；
3. 根据文字内容、单元名称或默认 ID 新建隐藏业务规则；
4. 猜学生内容的 `field_key` 或槽位接受范围；
5. 自行决定补目录标题、正文槽位、固定说明或学校特有字段；
6. 在身份解析失败时扩大删除、替换或格式化范围；
7. 静默删除 unknown object、未覆盖 run 或未审核 span；
8. 用 manifest 中的 `executed` 代替最终 DOCX 观察；
9. 用安全预览把 T5 `NOT_AVAILABLE` 恢复成 `AVAILABLE`；
10. 修改 T5、L1 或上游 final 来让本次执行看起来成功。

## 8. 建议的 T6 输出

建议 T6 最终发布三类产物：

```text
06.1_fillable_template.docx
06.2_build_manifest.json
06.3_template_slot_catalog.yaml
```

### 8.1 `06.1_fillable_template.docx`

真正供后续内容放置和最终渲染使用的可填写模板。

### 8.2 `06.2_build_manifest.json`

审计和诊断产物，至少包含：

```yaml
input_refs: {}
output: {}
unit_execution_results: []
actions_planned: []
action_results: []
effect_results: []
identity_resolution: {}
observed_docx_effects: {}
review_queue: []
```

每个 action result 至少包含：

- `action_id`；
- `effect_id`；
- 具体 `realization_type`；
- source identity 和 output ref；
- precondition 结果；
- before/after hash；
- execution status；
- postcondition expected/observed/status；
- 失败原因和 owner。

每个 unit execution result 至少包含：

```yaml
- unit_id: integrity_statement
  content_mode: preserve_exact
  planned_action_ids: []
  executed_action_ids: []
  precondition_fingerprint: sha256:...
  postcondition_fingerprint: sha256:...
  protected_scope_status: unchanged
  related_layout_result_refs: []
  result: preserved_exact
```

对于 `patch_exact` 单元，result 只有在以下条件同时满足时才能是 `patched_and_verified`：

- 全部 allowlisted action 已执行或已被证明 `already_satisfied`；
- 全部 effect postcondition 成立；
- 所有非目标 protected content refs 保持不变；
- 没有 unknown object、共享结构或跨单元副作用未对账。

### 8.3 `06.3_template_slot_catalog.yaml`

这是供“内容匹配与放置”直接消费的业务产物，不应要求下游从诊断 manifest 中猜槽位。

示例：

```yaml
artifact_type: template_slot_catalog
artifact_version: "1.0"
template_docx_hash: sha256:...
input_refs:
  t5_final: {artifact: 05_template_spec.yaml, sha256: sha256:...}
slots:
  - slot_id: slot.cover.student_name
    unit_id: cover
    element_id: e_student_name
    accepts_field_keys:
      - metadata.student.name
    accepts_node_types:
      - person_name
    cardinality: {min: 1, max: 1}
    target_format_ref: cover.student-name
    sdt_tag: slot.cover.student_name
    output_ref: word/document.xml:p[12]/sdt[1]
    realization_status: satisfied
```

T5 `slot_specs[]` 是“应该有什么槽位”；T6 slot catalog 是“最终 Word 里实际有什么槽位”。二者必须能按 `slot_id` 一一对账。

## 9. 当前动作的归属调整建议

| 当前动作或规则 | 建议归属 |
| --- | --- |
| `copy_source_docx` | T6 固定 bootstrap，不需要 T5 effect |
| `preserve_whole_unit_copy` | T5 `preserve_source` effect；T6 通常只验证复制结果 |
| `remove_instruction_text` | T5 `remove_source` effect；T6 精确实现 |
| `replace_span_with_slot` | T5 `realize_slot` effect；T6 选择 inline SDT 实现 |
| `create_fillable_slot` | T5 logical slot + `realize_slot` effect；T6 创建 SDT |
| `create_generated_field_placeholder` | T5 `realize_generated_field` effect；T6 实现字段 |
| `insert_fixed_text` | T5 `ensure_fixed_content` effect；T6 只执行 |
| `insert_synthetic_unit_title_before` | 取消 T6 启发式；只有 T5 明确声明标题和 anchor 时才允许 |
| `ensure_body_slot` | 取消 T6 静默兜底；改成 T5 明确 logical slot 或系统级显式 invariant |
| `insert_page_break_before_unit` | T6 对 T5 `ensure_page_boundary` 的一种 realization |
| `insert_section_break_before_unit` | T6 对 page/section/layout effect 的一种 realization |
| `set_keep_together_unit` | T6 对 T5 `ensure_keep_scope` 的 realization |

## 10. 一个完整示例

### T3 final

```yaml
element_id: e_student_name
unit_id: cover
policy: fill
fill_source: metadata.student.name
source_refs:
  - word/document.xml:p[12]
raw_run_ids:
  - p_0012.r_002
spans:
  - span_id: sample-value
    span_type: sample_value
    char_ranges:
      - raw_run_id: p_0012.r_002
        start: 0
        end: 2
```

### T5 final

```yaml
slot_specs:
  - slot_id: slot.cover.student_name
    unit_id: cover
    element_id: e_student_name
    slot_kind: inline
    accepts_field_keys:
      - metadata.student.name
    target_format_ref: cover.student-name
    anchor:
      mode: replace_source_span
      source_ref: word/document.xml:p[12]
      raw_run_ids:
        - p_0012.r_002

required_effects:
  - effect_id: effect.cover.student_name.slot
    effect_type: realize_slot
    scope_ref: slot.cover.student_name
    desired_result:
      source_text_absent: true
      fixed_sibling_text_preserved: true
      slot_present: true
```

### T6 action result

```yaml
action_id: t6.a.0012
effect_id: effect.cover.student_name.slot
realization_type: replace_run_range_with_inline_sdt
status: executed
source_ref: word/document.xml:p[12]
output_ref: word/document.xml:p[12]/sdt[1]
postcondition:
  status: satisfied
  expected:
    slot_id: slot.cover.student_name
    source_text_absent: true
  observed:
    sdt_tag: slot.cover.student_name
    source_text_absent: true
```

### T6 realized slot

```yaml
slot_id: slot.cover.student_name
accepts_field_keys:
  - metadata.student.name
target_format_ref: cover.student-name
sdt_tag: slot.cover.student_name
output_ref: word/document.xml:p[12]/sdt[1]
realization_status: satisfied
```

## 11. 建议本轮确认的决定

### D1：T5 的阶段性质

建议确认：

> T5 是声明式模板构建契约的发布者，不是简单拼接器，也不是低层 OOXML action 生成器。

### D2：T5 是否发布 logical slots

建议确认：

> 所有可供学生内容匹配的位置都必须先出现在 T5 `slot_specs[]`；T6 只能实现，不得创造。

### D3：T5 是否发布 required effects

建议确认：

> T5 把 T2/T3/T4 语义编译成逐项、可追踪、带 postcondition 的 `required_effects[]`；T6 再确定性编译成具体 Word actions。

### D4：T6 是否允许内建业务兜底

建议确认：

> 取消 T6 中按单元 ID、文字或缺失槽位触发的隐式业务兜底。确需全系统保证的正文槽位，也必须作为显式系统 invariant 进入 T5 final。

### D5：槽位是否成为独立 T6 业务产物

建议确认：

> T6 除最终 Word 和诊断 manifest 外，发布独立 `template_slot_catalog`，供内容匹配与放置直接消费。

### D6：partial availability

建议确认：

> T5 除总 availability 外，对每个 effect/slot 记录依赖与 availability；T6 只执行依赖已满足的 effect，并保守传播阶段总状态。

### D7：是否以单元为 T6 的事务和保护边界

建议确认：

> T5 为每个 unit 发布只负责内容的 `execution_contract`；T6 按单元生成、执行和验证内容 action。`preserve_exact` 单元不产生内容动作，`patch_exact` 单元只修改 allowlist，单元失败不得留下半修改结果。page/section/global layout 使用独立 contract 和执行通道。

### D8：是否禁止把完整全局版式复制进 unit

建议确认：

> unit 只保存 `page_refs/section_profile_refs/boundary_contract_refs` 等引用；page setup、页眉页脚、页码、numbering 和 global style 的真实值只保存在顶层 layout contracts。元素局部样式可以随 element 保留，但不会自动升级成全局样式动作。

## 12. 建议的验收方式

这套边界定稿并实施后，至少需要以下证明：

1. **T5 完整性**：每个 T2 unit、T3 element 和 T4 layout requirement 都进入 unit、slot、effect、blocked effect 或 review queue，不存在 silent gap；
2. **T6 唯一动作源**：删除 T5 中一个 effect 后，对应 T6 action 必须消失；修改候选 route、generation model 或 AI observation 不得改变 T6；
3. **禁止隐式动作**：T5 没有 body slot、synthetic title 或 fixed text effect 时，T6 不得创建；
4. **槽位对账**：T5 logical slots 与 T6 realized slots 按 `slot_id` 一一对应；
5. **精确身份反例**：故意破坏 raw run、char range、source hash 或 object identity 时，T6 必须停止该项动作且不扩大范围；
6. **最终效果观察**：每个 `executed` action 都必须在 fresh DOCX 中满足对应 postcondition；
7. **partial availability**：T3 不可用、T2 可用时，只允许独立分页效果和安全复制，不允许删除、替换或新增语义槽位；
8. **后续可消费性**：内容匹配阶段只使用 `StudentContentArtifact + TemplateSlotCatalog` 就能生成放置计划，不再读取 T3、T5 内部 trace 或 T6 诊断规则。
9. **单元 no-op 证明**：`preserve_exact` 单元没有内容 action，执行前后规范化 OOXML 内容、可见内容、局部格式和对象关系指纹一致；
10. **单元 allowlist 证明**：`patch_exact` 单元只有 `mutable_content_refs` 发生预期变化，故意让 action 越界时必须阻断；
11. **单元事务反例**：故意让同一单元的第二个 action 失败，最终 Word 中不能残留第一个 action 的半成品；
12. **版式隔离证明**：unit 不复制完整 section/page/global 值，只保存稳定引用；
13. **边界副作用证明**：page/section/global action 修改共享属性后，相关单元的 content fingerprint 仍保持不变，layout fingerprint 只包含授权变化。

## 13. 当前建议结论

建议采用方案 C：

```text
T2/T3/T4 final
      │
      ▼
T5 05_template_spec.yaml
   - normalized units
   - per-unit content execution_contract
   - layout/boundary contracts
   - logical slot_specs
   - required_effects
   - blocked_effects/review
      │
      ▼
T6 unit execution bundles
   - preserve_exact no-op
   - patch_exact allowlist
   - per-unit transaction/rollback
T6 layout execution bundles
   - boundary/section/global action lane
   - affected-unit side-effect checks
      │
      ▼
T6 fresh DOCX observation
   - content fingerprints
   - layout fingerprints
   - effect postconditions
      │
      ├── 06.1_fillable_template.docx
      ├── 06.2_build_manifest.json
      └── 06.3_template_slot_catalog.yaml
```

最关键的判断不是文件名，而是：

> **T5 必须完整表达最终模板的目标状态；T6 可以选择实现方式，但不能补充目标。**
