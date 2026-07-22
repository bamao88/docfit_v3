# T3 AI 分层输出原则（讨论稿）

> Status: discussion draft  
> Scope: 模板生成 T3 AI 判断输出；只定义 AI 输出的语义、递归原则、继承、校验和消费边界  
> Canonical target: `docs/current/template-generation-architecture.md` 的 T3 章节  
> Related input discussion: [`t3-stage-input-hierarchical-structure-discussion.md`](./t3-stage-input-hierarchical-structure-discussion.md)  
> Non-goal: 本文不规定 T3 Stage Input 的具体节点树、字段、投影、prompt 文案、JSON parser、类名、函数名、artifact 文件名或实施步骤。

> Discussion state: 本文只记录当前讨论中的候选结论和未决问题。除明确标为“已形成共识”的原则外，节点动作矩阵、输出字段和失败处理仍需继续讨论；在这些问题定稿前，不迁入 canonical 长期文档，也不据此宣称正式能力已经实现。

## 1. 这份文档回答什么

本文用于讨论 T3 AI 应该输出哪些判断，以及这些判断在系统结构中的含义。

本文先确定原则，再分别讨论：

1. prompt 应如何引导模型；
2. 如何校验、解析和物化模型输出；
3. code、AI、merged 和下游执行如何消费这些判断。

为了支持这里定义的分层输出，T3 Stage Input 必须提供可引用的节点、父子关系和完整性信息；但具体提供哪些节点类型、如何从当前输入迁移、如何组织表格/段落/run/source object，统一在关联输入讨论稿中讨论。本文只把“输出契约对输入的最低依赖”写成不变量，不在这里设计输入 schema。

本文不假设 T3 必须把所有内容判断到 run 层。T3 应在能够安全、统一判断的最粗层级结束；只有当前范围包含不同动作时才继续下钻。

当前已形成的核心共识是：

1. T3 的默认路径是 `unit → object/paragraph → 必要时才继续到 row/cell/run/span`，不是 `unit → run`。
2. 表格、段落或其他对象可以获得整体终局 Keep；此时后代由程序继承 Keep，不要求 AI 重复枚举。
3. “对象结构必须保留”不等于“对象内全部内容都是 Keep”。对象结构需要保留但内部含 Fill/Delete 时，语义结果必须是 `split`，再检查必要子节点。
4. 完整覆盖由程序确定性展开；AI 只输出稀疏决策树和真正需要下钻的例外。

## 2. 目标能力

T3 AI 接收 T2 单元及 L1 中已有的结构和事实身份，自上而下判断模板内容应当：

- `keep`：原样保留；
- `fill`：由学生内容替换或形成填写位置；
- `delete`：精确删除不属于最终模板内容的说明；
- `split`：当前范围包含不同动作，不能统一判断，需要继续检查子节点。

AI 只输出决策边界和需要继续检查的例外。完整的 run/span 覆盖台账由程序根据父子关系和继承规则确定性生成，不要求 AI 枚举所有 run。

这里的动作判断只描述内容语义，不直接描述容器结构编辑。尤其对于 table、row、cell、paragraph 等容器，需要区分两个问题：

- 结构是否保留：表格骨架、行列关系、段落容器是否继续存在；
- 后代内容是否能采用同一动作：容器内部所有内容能否统一 Keep/Fill/Delete。

首版原则倾向于默认保留已有容器结构。容器节点只有在所有后代内容也能采用同一动作时，才能输出终局动作；“保留表格结构但检查部分字段”应表达为 `split`，不能表达为终局 `keep`。

## 3. 输出契约对输入的最低依赖

本节只规定 AI 输出能够成立所依赖的输入能力，不决定 T3 Stage Input 的具体结构。完整输入设计见 [`t3-stage-input-hierarchical-structure-discussion.md`](./t3-stage-input-hierarchical-structure-discussion.md)。

T3 AI 不负责发现或创造 Word 结构身份。输入必须提供系统已经观察到的节点，以及节点之间的父子关系。

概念上的范围树可以是：

```text
unit
├── paragraph
├── table
│   ├── row
│   │   └── cell
│   │       └── paragraph
│   │           └── run
│   └── ...
└── source_object
    └── 系统能够可靠表达的子节点
```

这不是要求所有 Word 内容必须拥有完全相同的固定层级。不同节点可以有不同的直接子节点：

- 普通文本可以是 `unit → paragraph → run → span`；
- 表格可以是 `unit → table → row → cell → paragraph → run → span`；
- 图片、公式、文本框、内容控件或暂未细分对象可以先统一表达为 `source_object`；
- 系统没有稳定身份的层级不得由 AI 补造，可以跳过或停止自动下钻。

输入节点至少需要表达：

```jsonc
{
  "ref": "table:student_info",
  // 节点的稳定引用；AI 输出时只能引用这个身份，不能自造

  "source_kind": "table",
  // 上游观察到的 Word 对象类型；类型由系统提供，不由 AI 判断

  "child_refs": [
    "table:student_info/row:01",
    "table:student_info/row:02"
  ]
  // 当前节点的直接子节点；AI 输出 split 后，编排器只能沿这些身份下钻
}
```

输入还必须让系统判断当前节点的直接子节点、内容事实和必要视觉证据是否完整，是否发生截断，以及是否存在未绑定成员。具体字段名留给输入讨论稿确定。

如果成员或证据不完整，AI 不应据此产生覆盖全部后代的高置信终局判断。此时应选择安全 Keep、受限 Split 或人工复核中的哪一种，仍需在输出失败与不确定性规则中定稿。

## 4. 核心递归原则

对于每个实际访问的节点，T3 AI 必须在两类结果中选择一种。

### 4.1 终局判断

如果当前节点覆盖的全部内容可以安全采用同一动作，输出 `keep`、`fill` 或 `delete`，并在该节点结束。

```text
result ∈ {keep, fill, delete}
→ 当前节点结束
→ 不再调用 AI 检查子节点
→ 后代成员由程序继承该动作
```

### 4.2 继续拆分

如果当前节点包含不同动作，输出 `split`，并指出真正需要继续检查的直接子节点。

```text
result = split
→ 当前节点本身不产生统一动作
→ 未列为例外的直接子节点采用安全默认结果
→ 只对 inspect_child_refs 继续调用 AI
```

`split` 表示“确定存在多种动作”，不是“模型不知道答案”。模型置信度低、证据不足或系统没有可靠子节点时，应走安全保留或人工复核规则，不能用无边界的 `split` 掩盖不确定性。

### 4.3 结构保留不等于终局 Keep

以下两种判断必须区分：

```text
整张签字表只用于打印后人工填写
→ table result = keep
→ 全部后代继承 Keep
→ 停止下钻

学生信息表的表格骨架必须保留，但示例姓名需要系统替换
→ table structure = preserve（系统默认结构约束，不是内容终局动作）
→ table result = split
→ 只检查包含示例值或其他例外的直接子节点
→ 未检查子节点默认 Keep
```

因此，模型不能仅因为“表格结构要保留”就对 table 输出终局 Keep。终局 Keep 的含义必须严格限定为：当前节点覆盖的所有后代内容都采用 Keep。

### 4.4 人工填写与系统 Fill

`fill` 只用于 DocFit 后续需要自动替换、生成槽位或绑定学生内容的范围。打印后手写、签字、盖章、勾选、评审意见等人工工作区，即使视觉上存在空白，也不自动等于 Fill。

候选区分原则：

- 有明确学生内容字段或系统生成来源，并且当前节点边界可独立替换：可以 Fill；
- 签字、盖章、手写意见、人工勾选和无法确认自动内容来源的空白区：倾向 Keep；
- 固定标签与示例值属于不同子节点：标签 Keep，示例值可 Fill；
- 固定标签与待填内容混在不可拆分节点中：当前节点保守 Keep 或人工复核。

哪些 `fill.source/field` 必须在 T3 确认、哪些可留给后续内容匹配阶段，仍需继续讨论。

## 5. 哪些层面必须输出

### 5.1 单元层

每一个 T2 单元必须获得一个 T3 AI 顶层结果：

- 终局动作；或
- `split`，并指出需要继续检查的直接子节点。

没有顶层结果的单元属于未覆盖，不能静默进入下游。

### 5.2 单元以下

只有被父节点列入 `inspect_child_refs` 的节点需要继续输出。某个节点得到终局动作后，其全部后代不再要求 AI 单独输出。

因此，T3 AI 输出形成的是一棵稀疏决策树，而不是完整 Word 节点树的逐项标签。

### 5.3 Run 和 Span

run 级输出是局部混合问题的精细判断层，不是默认输出层：

- paragraph/cell 可以整体结束时，不进入 run；
- 只有更粗节点包含不同动作时才进入相关 run；
- 只有单个 run 内仍包含不同动作，并且系统支持可校验字符范围时才进入 span；
- 如果 run 内混合但当前不能安全表达或执行 span，整个 run 保守 `keep` 并留下原因。

## 6. 最小输出契约

### 6.1 终局结果

```jsonc
{
  "target_ref": "table:signature",
  // AI 正在判断的节点；必须来自当前输入

  "result": "keep",
  // 终局动作；内部全部成员继承 Keep，不再下钻

  "confidence": "high",
  // AI 对该判断的把握；不替代动作和安全门禁

  "reason": "整张表格用于打印后人工签字"
  // 判断依据，供审计、比较和人工复核
}
```

最小必需字段是 `target_ref` 和 `result`。`confidence`、`reason` 是否成为强制字段，应结合评测、审计和 token 成本继续讨论。

### 6.2 稀疏拆分结果

```jsonc
{
  "target_ref": "unit:proposal",
  // 当前判断的是整个开题报告单元

  "result": "split",
  // 单元内存在不同动作，不能给整个单元一个终局标签

  "default_child_result": "keep",
  // 未列出的直接子节点统一采用安全默认 Keep

  "inspect_child_refs": [
    "table:student_info",
    "table:topic_info"
  ],
  // 只有这两个输入中已有的直接子节点需要继续分析

  "confidence": "high",
  // 对“这个单元确实需要局部拆分”的把握

  "reason": "其他内容固定保留，只有两张表包含系统需要替换的字段"
  // 为什么选择这些例外节点继续下钻
}
```

`default_child_result` 的首版安全默认原则：

- 通用拆分默认只允许 `keep`；
- 不允许用默认 `delete` 批量删除未逐项确认的子节点；
- 是否允许特定、已有权威语义的生成对象默认 `fill/generated`，留待后续讨论；
- `inspect_child_refs` 必须是 `target_ref` 的直接子节点，不得跨层或跨单元引用。

`split` 的递归执行还必须有明确终止条件：

- 只能沿输入声明的直接子节点继续；
- 每次递归必须降低结构层级，不能形成环；
- 达到最细可执行节点、最大深度或调用预算后必须结束；
- 子调用失败、缺失、非法或只返回部分结果时，未完成子树不得静默当作正常继承。

### 6.3 Fill 的条件语义

```jsonc
{
  "target_ref": "table:student_info/row:02/cell:02",
  // 被替换的已有节点

  "result": "fill",
  // 当前节点由学生内容替换或形成填写位置

  "fill": {
    "source": "student_content",
    // 填充值来自学生内容阶段

    "field": "student_name"
    // 业务字段；字段无法在 T3 确认时是否允许省略，需要另行讨论
  },

  "reason": "该单元格是示例学生姓名"
  // 为什么它不是固定模板内容
}
```

### 6.4 Delete 的条件语义

```jsonc
{
  "target_ref": "run:p_0021.r_004",
  // 被删除的精确已有 run 或可执行 span

  "result": "delete",
  // 精确删除当前范围

  "confidence": "high",
  // Delete 是高风险动作，必须高置信

  "delete": {
    "reason": "独立 run 只描述字体和字号"
    // 删除依据；必须能证明删除后不损失业务内容或学校要求
  }
}
```

对象、单元、整段或其他宽泛范围是否允许直接 `delete`，应由节点类型动作矩阵明确限制。原则上 Delete 必须采用系统可以精确校验和执行的最小安全范围。

### 6.5 Run 内 Span

```jsonc
{
  "target": {
    "kind": "span",
    // 当前目标是一个 run 内的字符范围

    "run_ref": "run:p_0018.r_001",
    // span 所属的已有 raw run

    "start": 5,
    // 起始字符位置，包含该位置

    "end": 7
    // 结束字符位置，不包含该位置，即 [5, 7)
  },

  "result": "fill",
  // 只替换该字符范围

  "fill": {
    "source": "student_content",
    "field": "year"
  }
}
```

span 必须通过 `run_ref + start + end` 等可校验坐标定位，不能只返回一段可能重复出现的自由文本。span 身份最终由系统校验并确定性物化，AI 不自造权威 `span_id`。

## 7. 继承与覆盖

AI 输出终局结果后，程序负责展开完整覆盖台账。例如整张签字表格整体 Keep：

```jsonc
{
  "member_ref": "run:p_0100.r_001",
  // 最终被覆盖的源成员

  "resolved_result": "keep",
  // 该成员最终采用的动作

  "resolution": "inherited",
  // 结果来自上层节点继承，不是 AI 对这个 run 的直接判断

  "inherited_from": "table:signature",
  // 继承自哪个终局对象判断

  "decision_ref": "decision:t3_object_015"
  // 对应哪一条原始 T3 判断，便于审计和 route 比较
}
```

这类台账是程序产物，不是 AI 输出。它必须区分：

- `direct`：AI 直接判断当前节点；
- `inherited`：成员继承上层终局判断；
- `fallback`：模型失败、缺失或不安全时触发保守回退；
- `contested`：code/AI 或多次判断冲突，等待合并或人工复核。

这些来源即使最终都是 Keep，也不能在审计证据中混为一谈。

完整台账至少需要同时保留：

- 原始稀疏 decision；
- 展开后的 atomic member action；
- 继承路径和最近终局祖先；
- 输入树/hash 与 decision contract version；
- fallback、失败或冲突原因；
- 是否因为深度、预算、截断或身份不可用而停止下钻。

物化时不应仅因为对象整体 Keep 就强制生成大量彼此独立的业务 element。atomic coverage ledger 用于完整对账；最终 element 如何按相邻性、角色和执行语义合并，应由确定性 materialization 规则决定。

## 8. 动作与节点类型边界

同一套递归契约不表示每一种节点都允许所有动作。需要单独定义节点类型动作矩阵，至少遵守：

| 节点范围 | Keep | Fill | Delete | Split |
| --- | --- | --- | --- | --- |
| unit | 允许整体继承 | 是否允许待讨论 | 默认禁止 | 允许 |
| table / paragraph / source_object | 允许整体继承 | 仅在整体替换语义明确时允许 | 默认禁止宽泛删除 | 允许 |
| row / cell | 允许整体继承 | 结构和目标语义明确时允许 | 谨慎限制 | 允许 |
| run | 允许 | 允许 | 满足精确删除门禁时允许 | 支持 span 时允许 |
| span | 允许 | 允许 | 满足精确删除门禁时允许 | 不再继续拆分或进入人工复核 |

这张表只表达原则方向，不是已经批准的最终枚举。尤其是 unit/table 整体 Fill、对象级 Delete 和 span 末端行为，需要结合 T5/T6 执行能力单独确认。

首版讨论倾向如下，但尚未批准为最终矩阵：

- unit/table 的终局 Delete 禁止；
- table 的终局 Fill 默认禁止，避免把“填表”误解为替换整张表；
- row/cell/paragraph 只有在整体替换边界和字段语义明确时才允许 Fill；
- run/span 的 Delete 继续执行高置信、精确身份和纯格式说明门禁；
- 所有容器都可 Split，但前提是存在完整、稳定的直接子节点。

### 8.1 非正常结果不是第四种内容动作

`unknown`、`manual_review`、`failed`、`contested` 不应与 Keep/Fill/Delete 混成同一套内容动作。候选建模方向是：

- `result ∈ {keep, fill, delete, split}` 表达语义或递归决策；
- `decision_status ∈ {accepted, fallback, manual_review, failed, contested}` 表达判断是否可消费；
- 不确定或失败时的执行安全结果通常为 Keep，但审计状态仍必须保留原始原因。

这一分层是否采用上述具体枚举，仍需定稿。

## 9. 必须成立的不变量

1. AI 只能引用输入中已有的 unit/object/row/cell/paragraph/run 身份。
2. AI 不能创造父子关系，也不能把不属于当前节点的成员列为例外。
3. 终局结果覆盖当前节点全部后代，并停止该分支的进一步 AI 调用。
4. `split` 必须提供安全默认和需要继续检查的直接子节点，不能要求 AI 枚举大量重复 Keep。
5. 未列入 `inspect_child_refs` 的直接子节点必须可确定性继承默认结果。
6. 通用默认结果不得是 Delete；不确定性不能扩大删除范围。
7. run/span 只在更粗节点无法统一判断时使用，不作为所有内容的默认输出粒度。
8. span 必须有可验证坐标；不能安全拆分的混合 run 保守 Keep 或进入人工复核。
9. 完整覆盖由程序展开和校验，AI 不负责重复列出所有 run。
10. 直接判断、继承、fallback 和冲突必须保留不同 origin/trace。
11. T3 输出表达语义动作和结构决策，不直接编写 Word 编辑命令。
12. 下游无法消费的判断不能只停留在 prompt 或 side artifact 中并被宣称为正式能力。
13. “保留容器结构”不得被当作“全部后代内容 Keep”的证据；只有后代动作统一时才能终局 Keep。
14. 上层终局判断只有在成员和证据完整性满足契约时才能覆盖全部后代。
15. 递归调用失败或部分缺失产生的是 fallback，不得伪装为正常 inherited Keep。
16. 相同 atomic member 只能有一个最终 resolved action；祖先与后代决策重叠时必须按合法递归路径归一化并检测冲突。

## 10. T3 AI 输出与正式 T3 产物的关系

T3 AI 分层输出是判断和编排输入，不等同于最终 `element_spec`：

```text
T3 AI sparse decisions
  → identity / parent-child / action validation
  → stop-or-descend orchestration
  → deterministic inheritance and coverage expansion
  → code / AI comparison and merged decisions
  → element/span materialization
  → canonical T3 element_spec
```

AI 不输出权威 `element_id`，也不改写 L1 authoritative content。最终 element/span 身份、内容、完整 coverage 和 origin trace 由系统根据 L1、T2 及已校验判断确定性物化。

### 10.1 Code、AI 与 merged 的跨层比较

code 和 AI 可能在不同层级停止，例如 code 对整张表输出 Keep，AI 对表格输出 Split 并对一个 cell 输出 Fill。不能直接按原始 decision 数量或 target 层级比较。

候选比较流程是：

```text
code sparse decisions ─┐
                       ├→ 分别展开到同一 atomic identity ledger
AI sparse decisions ───┘
                              ↓
                    比较 resolved atomic actions
                              ↓
            保留各自原始停止层级、继承路径和证据
                              ↓
                  生成 merged sparse/element decisions
```

需要进一步定稿的冲突包括：

- 祖先终局 Keep 与后代 Fill/Delete 冲突如何归因；
- 一条 route 在父节点停止、另一条 route 正确下钻时如何比较层级质量；
- merged 选择更细决策时如何证明不是无依据地覆盖安全祖先决策；
- contested 子树如何进入人工复核且不扩大执行范围。

### 10.2 分层输出评测

展开后的 atomic action accuracy 仍是核心质量指标，但不足以评价分层决策。候选指标还应包括：

- terminal decision accuracy：终局节点动作是否正确；
- correct-stop rate：能够整体判断时是否正确停止；
- correct-descend rate：存在混合动作时是否正确 Split；
- inherited coverage accuracy：后代继承是否正确完整；
- object-level false Keep：本应包含 Fill/Delete 的对象是否被错误整体 Keep；
- unnecessary descent：本应整体 Keep 的对象是否被无意义地下钻；
- direct/inherited/fallback/contested 分布；
- AI 调用数、最大深度和 token/cost；
- Delete false positive 与宽泛删除继续作为硬安全指标。

Gold 可以继续以 atomic run/span 动作为最终对账底座，但还需要对象树、允许停止层级或等价层级判断证据，才能评价“是否在正确层级停止或下钻”。具体 gold 形状仍需讨论。

## 11. 当前待讨论问题

以下问题在本讨论稿中有意保持开放，不能提前固化到 prompt 或代码：

1. unit/table/paragraph 是否允许整体 Fill，还是 Fill 只能从 row/cell/run/span 开始？
2. `confidence` 和 `reason` 是否每条必填；如何控制 token 成本？
3. `split` 是否必须显式输出 `default_child_result=keep`，还是把 Keep 作为协议固定默认？
4. 无稳定子节点、无法继续拆分但仍混合的范围，应输出 Keep、unknown 还是 manual review？
5. code route 是否采用同一稀疏决策形状，以便 AI/code/merged 在同一节点身份上比较？
6. 最终 route-eval 既要评估终局动作准确率，也要如何评价“是否在正确层级停止或下钻”？
7. T5/T6 需要保留对象级判断本身，还是只消费已展开 element/span，同时把对象判断留作 trace？
8. 容器结构保留是固定系统不变量，还是需要在 T3 输出中显式表达独立字段？
9. 首版节点动作矩阵是否明确禁止 unit/table Fill 和所有对象级 Delete？
10. 子调用失败、超时、达到深度/预算上限时，Keep fallback 与 manual review 的边界是什么？
11. inherited coverage ledger 的 atomic identity 首版统一落在 raw run、atomic span，还是按对象类型选择不同叶节点？
12. sparse decision 和展开 ledger 如何版本化、hash 绑定并支持 replay/cache 失效？
13. gold 如何同时评价最终 atomic action 与正确停止/下钻层级，而不强迫只有一种合法树形？
14. 对象整体 Keep 最终应物化为一个 element、多个按语义合并的 element，还是只进入 coverage trace？

## 12. 后续定稿顺序

本原则稿讨论确认后，按以下顺序推进：

1. 把批准的长期原则迁入 `docs/current/template-generation-architecture.md` 的 T3 契约；
2. 在对应 status 中登记当前实现与目标契约的差距；
3. 如需实施，更新现有 T3 plan 或在目标/根因变化时建立下一轮 issue/plan；
4. 再设计 T3 Stage Input、AI 输出 schema、prompt、parser、orchestrator 和 materializer；
5. 用单元、对象、run、span、混合反例和真实学校样本证明能力闭环。
