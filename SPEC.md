# DocFit 服务规范

Status: Draft v1（Eval Harness-first，中文产品/Agent 实现版）

Purpose: 定义一个从 0 开始建设的 DocFit 服务：它把用户论文 Word 转换为符合目标学校模板的 Word 文档，但主驱动不是 `convert`，而是 Eval Harness。本文档应足够具体，使一个 AI Agent 在不知道其他私有上下文的情况下，也能实现一个符合产品方向的初始版本。

Audience: 产品经理、测试负责人、AI Coding Agent、实现工程师。

Scope: 本规范定义产品架构、阶段边界、验收语义、产物格式、CLI 行为、报告格式、测试门禁、AI 使用边界和最小可实现 Profile。它不是对当前已有代码的改造说明；它是从 0 建设 DocFit 的目标规范。

---

## 0. 规范性语言

本文档中的以下词语具有规范性含义：

- **必须 / MUST / REQUIRED**：实现必须满足；否则不能宣称符合本规范。
- **禁止 / MUST NOT**：实现不得出现；出现即为设计或流程违规。
- **应该 / SHOULD / RECOMMENDED**：默认应满足；如果不满足，必须在实现文档或报告中说明原因。
- **可以 / MAY / OPTIONAL**：可选增强，不影响核心符合性。
- **实现定义 / Implementation-defined**：本规范不指定唯一策略，但实现必须把选定策略写入文档或配置。
- **阻断 / Blocking**：该条件会阻止阶段、评测运行、发布门禁或 `docfit convert` 被视为成功。

### 0.1 核心术语

**Eval Harness**：评测与验收控制层。它负责定义怎么测、怎么判定、怎么定位问题、怎么输出 `PASS / FAIL / UNKNOWN`。Harness 是 DocFit 的主驱动。

**Stage / 阶段**：DocFit 的四个业务阶段之一：模板解析、内容提取、内容放置、DOCX 渲染。每个阶段必须可独立运行、独立验证、独立报告。

**Contract / 契约**：某个阶段输出必须满足的结构化标准。Contract 描述“产物必须证明什么”，不是“代码怎么实现”。

**Verifier / 验证器**：确定性检查程序。Verifier 根据 contract、golden、coverage、oracle 等信息输出 `PASS / FAIL / UNKNOWN`。

**Signed Standard / 已签收标准**：经过人工签收、版本化、hash 绑定、可审计的标准。初始版本不要求密码学签名，但必须具备 owner、版本、来源、变更原因和审计记录。

**Golden / 金标样本**：已签收的期望产物或期望特征快照。Golden 不能自动更新。

**Oracle / 判定器**：用于判断输出是否可信的外部或内部机制，例如 OOXML 包结构检查器、Word/LibreOffice 打开验证、feature diff、visual diff。

**Visible Content / 可见内容**：用户打开源 `.docx` 后能合理看到的内容，包括正文文本、标题、表格、图片、图表、公式、脚注、尾注、页眉页脚、文本框、题注、批注（若 contract 声明批注可见）以及其他可显示对象。

**Silent Drop / 静默丢弃**：某个用户可见内容没有进入后续产物，也没有被明确标记为 rejected、unsupported、discarded-as-source-format 或需要用户确认。Silent drop 永远是阻断失败。

**UNKNOWN / 未知**：系统不能证明正确。缺标准、缺 verifier、覆盖不足、oracle 不可信、输入不受支持、遇到未建模可见对象，均应输出 UNKNOWN。UNKNOWN 是阻断状态。

---

## 1. 问题陈述

DocFit 的目标是把用户随意写的 Word 论文转换成符合目标学校模板要求的 Word 文档。

但产品问题不只是“生成一个 `.docx` 文件”。真正的产品问题是：系统必须能够用可复现证据证明以下事项：

1. 学校 Word 模板被正确解析；
2. 用户 Word 中的可见内容被完整提取；
3. 每个用户可见内容都有明确去向或明确处置；
4. 最终 DOCX 是按已验证的放置计划渲染出来的；
5. 缺标准、缺 verifier、覆盖不足、unsupported 对象和不确定判断会被暴露为 `UNKNOWN`，不会被伪装为成功；
6. AI 只辅助根因分析，不作为最终裁判。

因此，成功的 `docfit convert` 不是系统的起点，而是一个已验证链路的终点。

DocFit 的主驱动必须是 Eval Harness。Harness 决定：

- 测什么；
- 用什么标准测；
- 怎么判定正确；
- 怎么定位失败阶段；
- 什么情况是 PASS；
- 什么情况是 FAIL；
- 什么情况是 UNKNOWN。

重要边界：

- DocFit 是一个四阶段、contract-verified 的 DOCX 转换系统。
- `docfit convert` 只编排已经通过阶段门禁的产物。
- AI 可以分析结构化失败报告和 issue cluster，但 AI 禁止直接决定最终通过/失败。
- 本规范从 0 设计。已有代码、已有 pipeline 名称、已有目录可以作为参考，但不能约束本规范。

---

## 2. 目标与非目标

### 2.1 目标

DocFit 必须：

1. 把 Eval Harness 放在业务转换代码之前。
2. 把系统拆成四个可独立执行、独立验证、独立回归的阶段：
   - 阶段 1：学校 Word 模板解析；
   - 阶段 2：用户 Word 内容提取；
   - 阶段 3：内容放置规划；
   - 阶段 4：DOCX 渲染。
3. 为每个阶段定义 contract、artifact、verifier、coverage gate 和 report。
4. 使用 `PASS`、`FAIL`、`UNKNOWN` 作为唯一阻断性终态。
5. 把 `UNKNOWN` 视为阻断。
6. 从阶段 2 到阶段 4 维护 Visible Content Ledger。
7. 禁止静默丢弃用户可见内容。
8. 默认修通用能力，不默认打学校级补丁。
9. 只有在有证据、签收、登记、配置化、测试覆盖的情况下，才允许学校特例。
10. 禁止标准漂移：不能自动更新 golden，不能自动更新 signed standard，不能把 FAIL 降成 WARN，不能把 UNKNOWN 当 PASS。
11. 生成足够小、足够结构化的报告，供 AI 做根因分析。
12. 支持一个 Bootstrap Profile，使 AI Coding Agent 可以先实现初始效果，而不需要一次性解决完整论文格式转换问题。

### 2.2 非目标

DocFit v1 禁止：

1. 把学校 PDF、图片、HTML、Markdown、纯文字格式规范作为阶段 1 的主输入。
2. 把“输出 DOCX 能打开”当作正确性的充分证明。
3. 把“视觉上差不多”当作正确性的充分证明。
4. 让 AI 直接阅读完整 Word、完整模板或巨大平铺 JSON 后给最终裁决。
5. 允许 `docfit convert` 绕过阶段 verifier。
6. 在核心逻辑中随意加入 `if school_id == ...` 的学校硬编码分支。
7. 为了让测试变绿而更新 expected、golden 或 signed standard。
8. 把 unsupported 可见内容静默丢弃。
9. 在 Stage 4 渲染阶段重新判断用户内容应该放哪里。

---

## 3. 系统总览

### 3.1 总体架构

```text
┌──────────────────────────────────────────────────────────────────────┐
│                           Eval Harness Layer                         │
│  eval cases · signed standards · contracts · verifiers · coverage     │
│  reports · issue clusters · AI RCA · release gates · audit logs       │
└──────────────────────────────────────────────────────────────────────┘
          │                    │                    │
          ▼                    ▼                    ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│ Stage 1           │  │ Stage 2           │  │ Stage 3           │
│ Template Parsing  │  │ Content Extract   │  │ Placement Plan    │
└──────────────────┘  └──────────────────┘  └──────────────────┘
          │                    │                    │
          └──────────────┬─────┴──────────────┬─────┘
                         ▼                    ▼
                 ┌────────────────────────────────┐
                 │ Stage 4                         │
                 │ DOCX Rendering                  │
                 └────────────────────────────────┘
                         │
                         ▼
                 ┌────────────────────────────────┐
                 │ docfit convert                  │
                 │ only orchestrates verified work │
                 └────────────────────────────────┘
```

Eval Harness Layer 是控制平面。四个 Stage 是被测对象。`docfit convert` 是产品入口，但不是验收裁判。

### 3.2 组件职责

| 组件 | 职责 |
|---|---|
| Eval Case Registry | 管理可复现评测样本，包括模板样本、用户文档样本、放置样本、渲染 golden |
| Standards Store | 存放 signed standards、contracts、goldens、exception registry |
| Contract Verifiers | 根据 contract 验证阶段产物 |
| Coverage Engine | 判断能力点是否被测到；覆盖不足输出 UNKNOWN |
| Stage Runners | 独立运行四个阶段 |
| Report Builder | 生成机器可读和 PM 可读报告 |
| Issue Clusterer | 把大量 finding 聚合成少量问题簇 |
| AI RCA Assistant | 读取 issue cluster，做根因分析建议，不做裁判 |
| Convert Orchestrator | 串联四个已验证阶段 |
| Release Gate | 判断某学校、某版本、某能力是否可发布 |
| Audit Log | 记录标准变更、golden 变更、exception 变更、UNKNOWN 放行尝试 |

---

## 4. 结果状态模型

所有 stage run、eval run、verifier run、release gate 必须使用以下状态：

| 状态 | 含义 | 是否允许发布 |
|---|---|---|
| `PASS` | 标准存在、verifier 存在、覆盖足够，并且产物满足 contract | 是 |
| `FAIL` | 标准明确、verifier 可运行、覆盖足够，但产物违反 contract | 否 |
| `UNKNOWN` | 无法证明正确，例如缺标准、缺 verifier、覆盖不足、oracle 不可信、输入不受支持 | 否 |

### 4.1 PASS 条件

一个阶段只有同时满足以下条件，才可以输出 `PASS`：

1. 对应 signed standard 存在；
2. 对应 contract 存在；
3. verifier 存在并运行成功；
4. coverage gate 满足要求；
5. 所有 blocking invariant 通过；
6. 没有 silent drop；
7. 没有未解释的 unsupported visible content；
8. 没有 AI-only judgment；
9. 产物包含 provenance，可追踪到输入。

### 4.2 FAIL 条件

`FAIL` 表示系统知道标准是什么，也能检查，但产物违反标准。

示例：

- 模板中必需 slot 未识别；
- 用户正文段落未进入 Student Content Model；
- 某个 `content_id` 没有 placement action；
- renderer 没有执行某个 Placement Plan item；
- 输出 DOCX 的标题样式、编号、页眉页脚与 signed golden 不一致；
- renderer 在 Stage 4 重新做了 placement 决策。

### 4.3 UNKNOWN 条件

`UNKNOWN` 表示系统不能证明正确。

以下情况必须输出 `UNKNOWN`：

- 缺 signed standard；
- 缺 contract；
- 缺 verifier；
- verifier 覆盖不足；
- 测试样本覆盖不足；
- oracle 不可信或未配置；
- 输入文件不在支持范围；
- 遇到未建模但可见的 Word 对象；
- expected/golden 是从当前错误输出自动生成的；
- AI 说“看起来没问题”，但没有 verifier 证明。

`UNKNOWN` 是 blocking。

### 4.4 WARN 的限制

`WARN` 可以作为非阻断提示存在，但不能作为最终状态。

禁止把本应 `FAIL` 或 `UNKNOWN` 的问题降级为 `WARN` 以通过 gate。

---

## 5. 仓库与文件组织规范

一个从 0 实现的 DocFit 仓库应该采用 Harness-first 的组织方式。

推荐结构：

```text
docfit/
  SPEC.md
  pyproject.toml
  README.md

  src/docfit/
    cli/
      main.py
    harness/
      cases.py
      runner.py
      status.py
      standards.py
      coverage.py
      reports.py
      issue_clusters.py
      release_gate.py
      audit.py
    contracts/
      schemas/
        template_contract.schema.json
        student_content_contract.schema.json
        placement_contract.schema.json
        render_contract.schema.json
        eval_report.schema.json
      verifier_base.py
    stages/
      template_parse/
        runner.py
        artifact.py
        verifier.py
      content_extract/
        runner.py
        artifact.py
        verifier.py
      placement/
        runner.py
        artifact.py
        verifier.py
      render/
        runner.py
        artifact.py
        verifier.py
    convert/
      orchestrator.py
    ooxml/
      package.py
      styles.py
      numbering.py
      document.py
      relationships.py
    ai_rca/
      packets.py
      prompts.py

  standards/
    eval_profiles/
      bootstrap-core/
        README.md
        expected/
          placement_plan.json
          feature_snapshot.json
    schools/
      <school_id>/
        <template_version>/
          signed_standard.yaml
          template_contract.json
          placement_contract.json
          render_contract.json
          exceptions.yaml
          golden/
            feature_snapshot.json
            expected.docx

  test_inputs/
    README.md
    template_generation/
      bootstrap-demo-school-template.docx
      school-pku-graduate-template.docx
    content_extraction/
      bootstrap-demo-student-pass.docx
      bootstrap-demo-student-unsupported-textbox.docx
      bootstrap-demo-student-silent-drop.docx
      real-student-001-source.docx
    template_gap/
      real-core-v0-pku-graduate-generated-template.docx

  test_outputs/
    .gitkeep
    eval_runs/
    debug/
    workbench/

  tests/
    unit/
    contract/
    regression/
    e2e/
```

### 5.1 一等公民目录

以下目录必须是一等公民，不能只是测试附属物：

- `standards/`
- `contracts/`
- `test_inputs/`
- `test_outputs/`
- `src/docfit/harness/`

### 5.2 禁止的组织方式

禁止把标准和 expected 混在普通代码或原始输入目录里。

禁止把仓库内评测输入、用户真实上传入口和运行输出混用。仓库随附的可复现输入放
`test_inputs/`；每次运行产生的报告、artifact、debug 快照和最终 Word 放
`test_outputs/` 或显式传入的临时输出目录。

禁止让 stage runner 内部硬编码学校规则。

禁止只有 `pipeline/`，没有 `harness/`。

禁止只保存最终 `.docx`，不保存阶段 artifact 和 verifier report。

---

## 6. Eval Harness 规范

### 6.1 Harness 是主入口

DocFit 必须提供以下 Harness 命令：

```bash
docfit eval template   --school <school_id> --template <template.docx>
docfit eval content    --student <student.docx>
docfit eval placement  --school <school_id> --template-artifact <file> --content-artifact <file>
docfit eval render     --school <school_id> --template-artifact <file> --placement-plan <file>
docfit eval e2e        --school <school_id> --student <student.docx>
docfit eval coverage   --profile <profile>
docfit eval standards  --audit
docfit diagnose        --run <run_id>
```

`docfit convert` 必须存在，但它不是首要验收入口：

```bash
docfit convert --school <school_id> --student <student.docx> --out <final.docx>
```

### 6.2 EvalCase

EvalCase 是 Harness 的最小运行单位。

示例：

```yaml
case_id: bootstrap_e2e_demo_001
stage: e2e
school_id: demo-school
inputs:
  template_docx: test_inputs/template_generation/bootstrap-demo-school-template.docx
  student_docx: test_inputs/content_extraction/bootstrap-demo-student-pass.docx
standards:
  signed_standard: standards/schools/demo-school/v1/signed_standard.yaml
  template_contract: standards/schools/demo-school/v1/template_contract.json
  placement_contract: standards/schools/demo-school/v1/placement_contract.json
  render_contract: standards/schools/demo-school/v1/render_contract.json
coverage_profile: bootstrap-core
expected_status: PASS
owner: docfit-core
```

### 6.3 EvalRun

每次 Harness 运行必须生成 EvalRun 记录。

```json
{
  "run_id": "run_2026_001",
  "case_id": "bootstrap_e2e_demo_001",
  "stage": "e2e",
  "status": "FAIL",
  "started_at": "2026-06-14T10:00:00+09:00",
  "ended_at": "2026-06-14T10:00:03+09:00",
  "input_hashes": {
    "template_docx": "sha256:...",
    "student_docx": "sha256:..."
  },
  "standards": {
    "signed_standard": "demo-school/v1",
    "template_contract": "sha256:...",
    "placement_contract": "sha256:..."
  },
  "findings": [],
  "coverage": {},
  "artifacts": {},
  "reports": {}
}
```

### 6.4 Harness 输出目录

每次运行应输出到：

```text
test_outputs/debug/template_eval_runs/<run_id>/
  summary.json
  pm_report.md
  findings.json
  issue_clusters.json
  artifacts/
    template_artifact.json
    student_content_artifact.json
    placement_plan.json
    render_manifest.json
    feature_snapshot.json
  evidence/
    snippets.json
    diffs.json
  ai/
    diagnosis_packet.json
```

### 6.5 Harness gate 规则

Harness 必须执行以下 gate：

1. 标准存在性检查；
2. contract schema 检查；
3. verifier 存在性检查；
4. 输入 hash 和 signed standard 绑定检查；
5. coverage gate；
6. stage-specific invariant 检查；
7. no silent drop 检查；
8. anti-drift 检查；
9. AI-only 判断检查；
10. school exception registry 检查。

任一 blocking gate 不通过，最终不能 PASS。

---

## 7. Signed Standard 规范

### 7.1 定义

Signed Standard 是 DocFit 的验收标准来源。它必须可版本化、可审计、可回滚。

示例：

```yaml
standard_id: demo-school-v1
school_id: demo-school
template_version: v1
status: signed
owner: product-owner
approved_at: "2026-06-14T10:00:00+09:00"
source:
  template_docx: test_inputs/template_generation/bootstrap-demo-school-template.docx
  template_docx_sha256: "sha256:..."
contracts:
  template_contract: template_contract.json
  placement_contract: placement_contract.json
  render_contract: render_contract.json
goldens:
  feature_snapshot: golden/feature_snapshot.json
  expected_docx: golden/expected.docx
coverage_requirements:
  profile: bootstrap-core
  required_capabilities:
    - template.required_slots
    - content.visible_text_blocks
    - placement.no_silent_drop
    - render.plan_coverage
change_control:
  auto_update_allowed: false
  requires_review: true
  change_reason: initial bootstrap standard
```

### 7.2 标准变更规则

Signed Standard 变更必须满足：

1. 有 owner；
2. 有 change reason；
3. 有 before/after diff；
4. 有受影响 case 列表；
5. 有新增或更新的测试；
6. 不能由失败运行自动更新；
7. 不能为了匹配当前错误输出而更新。

### 7.3 Anti-drift 检查

Harness 必须检查：

- 当前 expected 是否由当前 actual 自动生成；
- golden 是否未签收就更新；
- signed standard hash 是否改变；
- verifier 是否被关闭；
- coverage 阈值是否被降低；
- FAIL 是否被规则降级为 WARN；
- UNKNOWN 是否被放行。

发现任一问题，输出 `UNKNOWN` 或 `FAIL`，并写入 audit log。

---

## 8. Contract 与 Artifact 规范

### 8.1 通用 Artifact 字段

所有阶段 artifact 必须包含：

```json
{
  "artifact_type": "...",
  "artifact_version": "1.0",
  "producer": {
    "name": "docfit-stage-name",
    "version": "0.1.0"
  },
  "created_at": "2026-06-14T10:00:00+09:00",
  "input_hashes": {},
  "provenance": {},
  "status_notes": [],
  "unsupported": [],
  "data": {}
}
```

### 8.2 通用 Finding 字段

所有 verifier finding 必须包含：

```json
{
  "finding_id": "f_001",
  "stage": "placement",
  "severity": "blocking",
  "status": "FAIL",
  "type": "unplaced_content",
  "message": "content block c_012 has no placement action",
  "expected": "every visible content block has exactly one disposition",
  "actual": "c_012 missing from placement plan",
  "evidence_refs": ["evidence/snippets.json#c_012"],
  "affected_ids": ["c_012"],
  "root_cause_bucket": "placement_gap"
}
```

### 8.3 Contract schema 最小要求

每个 contract 必须包含：

```json
{
  "contract_type": "template|student_content|placement|render",
  "contract_version": "1.0",
  "owner": "...",
  "required_invariants": [],
  "required_capabilities": [],
  "unsupported_policy": {},
  "coverage_requirements": {},
  "verifier_refs": []
}
```

缺少任一字段，Harness 应输出 `UNKNOWN`。

---

## 9. Stage 1：学校 Word 模板解析

### 9.1 目的

Stage 1 将学校官方 `.docx` 模板解析为 Template Artifact。

Stage 1 只回答：

> 目标学校模板包含哪些结构、样式、区域、槽位、页眉页脚、编号、封面字段和不可修改内容？

Stage 1 不处理用户论文，不决定用户内容放哪里，不生成最终 DOCX。

### 9.2 输入

Stage 1 必须只接受学校官方 `.docx` 模板作为主输入。

禁止把以下内容作为 Stage 1 主输入：

- PDF；
- 图片；
- HTML；
- Markdown；
- 纯文字规范；
- 人工口述格式要求。

### 9.3 输出：Template Artifact

Template Artifact 必须描述模板的可验证结构。

#### 当前模板生成扩展：默认仅复制单元

当前实现允许在模板生成阶段采用“先整包复制源 Word，再局部 patch”的策略。仅复制单元的规范口径不是固定排除列表，而是内容责任：凡是需要机器根据学生源文档生成、填写或放置内容的区域，都不能默认仅复制；凡是学校固定正文、签名、日期、教师意见、成绩评定等只需要人工线下填写或确认的区域，可以默认仅复制。

普通目录、图目录、表目录、中文摘要、英文摘要、正文、参考文献，以及学生源文档中实际有内容或学校标准要求承载学生内容的致谢、附录等区域，应按生成/填写/放置责任处理。仅复制单元的含义是：生成阶段依赖最开始的整包复制保留该单元，不逐个分析单元内部元素是否需要填写、生成或删除，也不因为内部出现 `____`、`××`、姓名、日期等文本就自动生成 slot。这个策略必须写入 Template Artifact、生成决策、生成计划或 manifest 中的可审计证据，不能替代 Template Contract 或 `template-gap` 对最终 Word 的验收。

示例结构：

```json
{
  "artifact_type": "template_artifact",
  "artifact_version": "1.0",
  "school_id": "demo-school",
  "template_version": "v1",
  "input_hashes": {
    "template_docx": "sha256:..."
  },
  "data": {
    "page_setup": {
      "paper_size": "A4",
      "margins": {},
      "sections": []
    },
    "styles": [
      {
        "style_id": "Heading1",
        "name": "标题 1",
        "type": "paragraph",
        "outline_level": 1,
        "font": {},
        "paragraph": {}
      }
    ],
    "regions": [
      {
        "region_id": "body",
        "kind": "body",
        "required": true,
        "anchors": ["slot_body_start"]
      }
    ],
    "slots": [
      {
        "slot_id": "slot_body_start",
        "kind": "body_content",
        "writable": true,
        "required": true,
        "accepted_content_kinds": ["heading", "paragraph", "table", "figure", "formula"]
      }
    ],
    "protected_zones": [],
    "numbering": [],
    "headers_footers": [],
    "required_fields": [],
    "unsupported": []
  }
}
```

### 9.4 Template Contract

Template Contract 必须验证：

| Invariant | 失败状态 |
|---|---|
| 模板是合法 docx | FAIL |
| 模板 hash 与 signed standard 匹配 | UNKNOWN |
| 必需 region 可识别 | FAIL |
| 必需 slot 可识别 | FAIL |
| 必需样式可识别 | FAIL |
| 不可修改区域可识别 | FAIL |
| 影响布局的 unsupported 对象被登记 | UNKNOWN |
| stage 1 coverage 满足要求 | UNKNOWN |

### 9.5 Stage 1 CLI

```bash
docfit eval template \
  --school demo-school \
  --template test_inputs/template_generation/bootstrap-demo-school-template.docx \
  --out test_outputs/debug/template_eval_runs/run_template_001
```

必须生成：

```text
test_outputs/debug/template_eval_runs/run_template_001/
  summary.json
  pm_report.md
  findings.json
  artifacts/template_artifact.json
```

### 9.6 Stage 1 PASS 示例

```json
{
  "stage": "template",
  "status": "PASS",
  "summary": "Template contract satisfied",
  "coverage": {
    "required_regions": "3/3",
    "required_slots": "5/5",
    "required_styles": "8/8"
  },
  "findings": []
}
```

### 9.7 Stage 1 UNKNOWN 示例

```json
{
  "stage": "template",
  "status": "UNKNOWN",
  "findings": [
    {
      "type": "unsupported_layout_feature",
      "message": "template contains visible text box in protected cover region; parser does not model text boxes yet",
      "status": "UNKNOWN",
      "severity": "blocking"
    }
  ]
}
```

---

## 10. Stage 2：用户 Word 内容提取

### 10.1 目的

Stage 2 将用户论文 `.docx` 转换为 Student Content Artifact。

Stage 2 只回答：

> 用户文档中有哪些可见内容、对象、顺序关系和结构线索？

Stage 2 必须学校无关。它不能依赖目标学校，也不能输出“这是某学校的一级标题”。它只能输出通用内容模型和候选语义。

### 10.2 输入

Stage 2 输入：

```text
用户论文 .docx
```

禁止把学校模板作为 Stage 2 必需输入。

### 10.3 输出：Student Content Artifact

Student Content Artifact 必须包含 Visible Content Ledger。

示例：

```json
{
  "artifact_type": "student_content_artifact",
  "artifact_version": "1.0",
  "input_hashes": {
    "student_docx": "sha256:..."
  },
  "data": {
    "document_stats": {
      "paragraph_count": 42,
      "table_count": 1,
      "image_count": 2
    },
    "visible_content_ledger": [
      {
        "content_id": "c_001",
        "kind": "paragraph",
        "text": "绪论",
        "text_hash": "sha256:...",
        "reading_order": 1,
        "source_ref": "word/document.xml:p[1]",
        "style_signals": {
          "bold": true,
          "font_size": 16,
          "alignment": "center"
        },
        "semantic_candidates": [
          {
            "kind": "heading",
            "level_candidate": 1,
            "confidence": 0.82,
            "evidence": ["bold", "center", "larger_font"]
          }
        ]
      }
    ],
    "assets": [],
    "unsupported": []
  }
}
```

### 10.4 Student Content Contract

Student Content Contract 必须验证：

| Invariant | 失败状态 |
|---|---|
| 每个可见文本块都有 `content_id` | FAIL |
| 每个可见表格、图片、公式对象都有 `content_id` 或 asset id | FAIL |
| 每个内容有 provenance | UNKNOWN |
| 每个内容有 reading order | FAIL |
| 可见内容未提取 | FAIL |
| unsupported 可见对象未登记 | FAIL |
| 语义候选没有 evidence | UNKNOWN |
| Stage 2 结果依赖 school_id | FAIL |
| coverage 不足 | UNKNOWN |

### 10.5 可见内容处置原则

Stage 2 不允许丢弃任何可见内容。

遇到暂不支持对象时，必须进入 `unsupported`：

```json
{
  "content_id": "c_031",
  "kind": "unsupported_visible_object",
  "object_type": "text_box",
  "source_ref": "word/document.xml:drawing[4]",
  "reason": "text box extraction not implemented",
  "blocking": true
}
```

### 10.6 Stage 2 CLI

```bash
docfit eval content \
  --student test_inputs/content_extraction/bootstrap-demo-student-pass.docx \
  --out test_outputs/debug/template_eval_runs/run_content_001
```

必须生成：

```text
test_outputs/debug/template_eval_runs/run_content_001/
  summary.json
  pm_report.md
  findings.json
  artifacts/student_content_artifact.json
```

---

## 11. Stage 3：内容放置

### 11.1 目的

Stage 3 根据 Template Artifact 和 Student Content Artifact 生成 Placement Plan。

Stage 3 只回答：

> 每个用户可见内容应该放到目标模板哪里，以什么动作放置，为什么？

Stage 3 不写 Word 文件，不修改 OOXML，不执行字体字号操作。

### 11.2 输入

Stage 3 输入：

1. Template Artifact；
2. Template Contract；
3. Student Content Artifact；
4. Student Content Contract；
5. Placement Contract。

Stage 3 禁止重新读取完整用户 Word 来绕过 Stage 2 产物。

### 11.3 输出：Placement Plan

Placement Plan 必须为每个 `content_id` 提供且只提供一个明确处置。

允许的 disposition：

| Disposition | 含义 |
|---|---|
| `place` | 直接放到某个模板 slot |
| `transform_then_place` | 经过 contract 允许的转换后放置 |
| `merge` | 与其他内容合并后放置 |
| `split` | 拆分到多个 slot |
| `preserve_as_object` | 作为对象保留，例如图片、公式 |
| `discard_as_source_format` | 明确判定为源文档格式噪音并允许丢弃 |
| `reject` | 明确拒绝，给出原因 |
| `unsupported` | 暂不支持，导致 UNKNOWN 或 FAIL |
| `ask_user` | 需要用户补充确认，导致 UNKNOWN |

示例：

```json
{
  "artifact_type": "placement_plan",
  "artifact_version": "1.0",
  "input_hashes": {
    "template_artifact": "sha256:...",
    "student_content_artifact": "sha256:..."
  },
  "data": {
    "actions": [
      {
        "action_id": "a_001",
        "content_ids": ["c_001"],
        "disposition": "place",
        "target_slot_id": "slot_body_start",
        "target_region_id": "body",
        "render_kind": "heading",
        "style_ref": "Heading1",
        "evidence": ["heading_candidate", "first_body_heading"],
        "confidence": 0.9
      }
    ],
    "unresolved": [],
    "school_exception_refs": []
  }
}
```

### 11.4 Placement Contract

Placement Contract 必须验证：

| Invariant | 失败状态 |
|---|---|
| 每个 visible content block 有且只有一个 disposition | FAIL |
| 任一 visible content 被 silent drop | FAIL |
| target slot 不存在 | FAIL |
| target slot 不可写 | FAIL |
| 内容类型与 slot 不兼容 | FAIL |
| 必填 slot 缺内容且无允许原因 | FAIL |
| 图片/表格与题注关系断裂 | FAIL |
| 参考文献、附录、致谢等区域无法归属 | UNKNOWN 或 FAIL |
| placement action 缺 evidence | UNKNOWN |
| 使用未登记学校特例 | FAIL |
| coverage 不足 | UNKNOWN |

### 11.5 No Silent Drop Verifier

No Silent Drop Verifier 必须执行以下检查：

```text
ledger_content_ids = all content_id in Student Content Artifact.visible_content_ledger
planned_content_ids = union of all content_ids in Placement Plan.actions
unresolved_content_ids = all content_id in Placement Plan.unresolved

for each id in ledger_content_ids:
    id MUST appear in planned_content_ids or unresolved_content_ids

if any id missing:
    status = FAIL
```

如果 `unresolved` 中存在 blocking `unsupported` 或 `ask_user`，阶段结果必须是 `UNKNOWN`。

### 11.6 Stage 3 CLI

```bash
docfit eval placement \
  --school demo-school \
  --template-artifact test_outputs/debug/template_eval_runs/run_template_001/artifacts/template_artifact.json \
  --content-artifact test_outputs/debug/template_eval_runs/run_content_001/artifacts/student_content_artifact.json \
  --out test_outputs/debug/template_eval_runs/run_placement_001
```

必须生成：

```text
test_outputs/debug/template_eval_runs/run_placement_001/
  summary.json
  pm_report.md
  findings.json
  artifacts/placement_plan.json
```

---

## 12. Stage 4：DOCX 渲染

### 12.1 目的

Stage 4 根据 Template Artifact 和 Placement Plan 写出最终 `.docx`。

Stage 4 只回答：

> 是否能够忠实执行已验证的 Placement Plan，并输出符合 Render Contract 的 DOCX？

Stage 4 禁止重新判断内容该放哪里。

### 12.2 输入

Stage 4 输入：

1. Template Artifact；
2. Placement Plan；
3. Render Contract；
4. signed golden；
5. 原始模板 `.docx` 中必要 OOXML parts；
6. 用户内容 asset；
7. oracle 配置。

### 12.3 输出

Stage 4 必须输出：

| 输出 | 说明 |
|---|---|
| `final.docx` | 最终 Word 文件 |
| `render_manifest.json` | 每个 placement action 实际写入位置 |
| `feature_snapshot.json` | 输出 DOCX 的结构化特征 |
| `feature_diff.json` | 与 signed golden 的差异 |
| `oracle_report.json` | OOXML / Word / LibreOffice / visual oracle 结果 |
| `coverage_report.json` | placement 执行覆盖情况 |

### 12.4 Renderer 禁止行为

Renderer 禁止：

1. 重新识别标题层级；
2. 重新判断摘要、正文、参考文献、附录；
3. 自行丢弃内容；
4. 用 `school_id` 分支覆盖通用逻辑；
5. 自动修改 signed golden；
6. 因写不出来而跳过对象；
7. 把 Word 可打开当作 PASS 的充分条件；
8. 改变 Placement Plan 的语义。

### 12.5 Render Manifest

示例：

```json
{
  "artifact_type": "render_manifest",
  "artifact_version": "1.0",
  "output_docx": "test_outputs/debug/template_eval_runs/run_render_001/final.docx",
  "actions_executed": [
    {
      "action_id": "a_001",
      "content_ids": ["c_001"],
      "target_slot_id": "slot_body_start",
      "actual_ooxml_ref": "word/document.xml:p[12]",
      "status": "executed"
    }
  ],
  "actions_failed": []
}
```

### 12.6 Render Contract

Render Contract 必须验证：

| Invariant | 失败状态 |
|---|---|
| 输出是合法 `.docx` package | FAIL |
| 所有 Placement Plan action 被执行或明确失败 | FAIL |
| 任一计划内容缺失 | FAIL |
| renderer 改变 placement 决策 | FAIL |
| 阻断级 feature diff | FAIL |
| 缺 signed golden | UNKNOWN |
| 缺 OOXML 或 Word oracle | UNKNOWN |
| oracle 不稳定 | UNKNOWN |
| coverage 不足 | UNKNOWN |

### 12.7 Feature Diff

Feature snapshot 至少应覆盖：

- 页面设置；
- styles；
- numbering；
- sections；
- headers；
- footers；
- TOC / fields；
- headings；
- paragraphs；
- tables；
- figures；
- captions；
- references；
- footnotes/endnotes；
- content coverage hashes。

Feature diff 必须把差异分成：

| 类型 | 含义 |
|---|---|
| `expected` | contract 允许的差异 |
| `accepted_exception` | 已登记学校特例允许的差异 |
| `non_blocking` | 不影响 contract 的提示 |
| `blocking` | 违反 contract，必须 FAIL |
| `unknown` | 无法判断是否允许，必须 UNKNOWN |

### 12.8 Stage 4 CLI

```bash
docfit eval render \
  --school demo-school \
  --template-artifact test_outputs/debug/template_eval_runs/run_template_001/artifacts/template_artifact.json \
  --placement-plan test_outputs/debug/template_eval_runs/run_placement_001/artifacts/placement_plan.json \
  --out test_outputs/debug/template_eval_runs/run_render_001
```

必须生成：

```text
test_outputs/debug/template_eval_runs/run_render_001/
  summary.json
  pm_report.md
  findings.json
  final.docx
  artifacts/render_manifest.json
  artifacts/feature_snapshot.json
  artifacts/feature_diff.json
  artifacts/oracle_report.json
```

---

## 13. `docfit convert` 规范

### 13.1 职责

`docfit convert` 只是 orchestrator。它必须按顺序调用四个已定义阶段：

```text
template parse
  → content extract
  → placement plan
  → docx render
```

它不能替代任何 stage verifier。

### 13.2 Gate 行为

`docfit convert` 必须遵守：

1. 任一阶段 `FAIL`，convert 失败；
2. 任一阶段 `UNKNOWN`，convert 失败；
3. 任一阶段缺 report，convert 失败；
4. 任一阶段 report 无法解析，convert 失败；
5. 任一阶段产物 hash 与下游输入不一致，convert 失败；
6. 只有四阶段全部 PASS，convert 才能输出可信成功。

### 13.3 CLI

```bash
docfit convert \
  --school demo-school \
  --student test_inputs/content_extraction/bootstrap-demo-student-pass.docx \
  --out test_outputs/debug/template_eval_runs/run_convert_001/final.docx \
  --report test_outputs/debug/template_eval_runs/run_convert_001
```

### 13.4 成功输出

成功时必须生成：

```text
test_outputs/debug/template_eval_runs/run_convert_001/final.docx
test_outputs/debug/template_eval_runs/run_convert_001/
  summary.json
  pm_report.md
  artifacts/
    template_artifact.json
    student_content_artifact.json
    placement_plan.json
    render_manifest.json
    feature_snapshot.json
```

### 13.5 失败输出

失败时也必须生成报告。示例：

```json
{
  "stage": "convert",
  "status": "UNKNOWN",
  "blocked_at": "content_extract",
  "user_message": "文档中包含当前系统尚不能可靠提取的文本框内容，因此无法证明转换不会丢失内容。",
  "internal_message": "Stage 2 found unsupported visible text_box c_031.",
  "report_ref": "test_outputs/debug/template_eval_runs/run_convert_001/pm_report.md"
}
```

---

## 14. 报告规范

### 14.1 PM Report

每次运行必须生成 `pm_report.md`。

PM Report 必须回答：

1. 当前状态是什么：PASS / FAIL / UNKNOWN；
2. 阻断发生在哪个阶段；
3. 为什么阻断；
4. 影响哪些内容或模板槽位；
5. 属于通用能力问题、标准问题、verifier 问题、coverage 问题，还是学校特例候选；
6. 建议下一步是什么；
7. 是否涉及 silent drop；
8. 是否有 AI 参与，AI 只提供了什么建议。

### 14.2 Summary JSON

`summary.json` 必须机器可读。

```json
{
  "run_id": "run_convert_001",
  "status": "FAIL",
  "stage_statuses": {
    "template": "PASS",
    "content": "PASS",
    "placement": "FAIL"
  },
  "stage_run_states": {
    "template": "ran",
    "content": "ran",
    "placement": "ran",
    "render": "not_run"
  },
  "blocking_findings": 1,
  "unknown_findings": 0,
  "silent_drop_count": 1,
  "primary_failure_bucket": "placement_gap",
  "reports": {
    "pm_report": "pm_report.md",
    "findings": "findings.json",
    "issue_clusters": "issue_clusters.json"
  }
}
```

### 14.3 Findings

`findings.json` 必须是 finding 数组。

每个 finding 必须包含：

- `finding_id`
- `stage`
- `status`
- `severity`
- `type`
- `message`
- `expected`
- `actual`
- `evidence_refs`
- `affected_ids`
- `root_cause_bucket`

### 14.4 Issue Cluster

Issue Cluster 是给 AI 和 PM 看的小证据包。

示例：

```json
{
  "cluster_id": "cluster_placement_001",
  "stage": "placement",
  "status": "FAIL",
  "title": "Two visible paragraphs have no placement action",
  "invariant": "every visible content block must have exactly one disposition",
  "affected_content_ids": ["c_184", "c_185"],
  "affected_slots": [],
  "evidence": [
    {
      "content_id": "c_184",
      "text_preview": "[redacted preview]",
      "source_ref": "word/document.xml:p[231]"
    }
  ],
  "likely_root_cause_bucket": "placement_gap",
  "ai_allowed": true
}
```

---

## 15. AI RCA 规范

### 15.1 AI 的角色

AI 是 Root Cause Analysis Assistant，不是 judge。

AI 可以：

- 读取 issue cluster；
- 总结失败模式；
- 判断更像哪个通用能力缺口；
- 建议修复方向；
- 建议新增 regression case；
- 标记可能的学校特例候选。

AI 禁止：

- 直接裁定 PASS / FAIL / UNKNOWN；
- 直接看完整 Word 或完整模板给最终结论；
- 自动更新 golden 或 signed standard；
- 把 FAIL 降级成 WARN；
- 把 UNKNOWN 当 PASS；
- 为学校在核心代码加分支；
- 忽略 silent drop。

### 15.2 Diagnosis Packet

AI 的输入必须是小范围结构化包。

示例：

```json
{
  "packet_id": "diag_run_001",
  "run_id": "run_convert_001",
  "status": "FAIL",
  "clusters": [
    {
      "cluster_id": "cluster_placement_001",
      "stage": "placement",
      "invariant": "no silent drop",
      "expected": "all visible content ids appear in placement plan or unresolved list",
      "actual": "c_184 and c_185 are missing",
      "evidence_refs": ["evidence/snippets.json#c_184"]
    }
  ],
  "allowed_ai_tasks": [
    "summarize_root_cause",
    "suggest_generic_fix",
    "suggest_tests"
  ],
  "forbidden_ai_tasks": [
    "judge_pass_fail",
    "update_expected",
    "create_school_patch"
  ]
}
```

### 15.3 AI 输出

AI 输出必须标记为 advisory。

```json
{
  "advisory_only": true,
  "likely_root_cause": "Stage 3 placement planner does not handle bibliography paragraphs after unstyled reference heading.",
  "recommended_generic_fix": "Improve reference-section boundary detection and placement mapping.",
  "recommended_tests": [
    "Add content fixture with unstyled references section",
    "Add placement regression for bibliography paragraphs"
  ],
  "final_status": "NOT_PROVIDED_BY_AI"
}
```

Harness 禁止读取 AI 的 `advisory_only` 输出来改变 gate 结果。

---

## 16. 学校特例策略

### 16.1 默认策略

任何失败默认是通用能力不足，而不是学校特例。

默认修复顺序：

1. Template parser；
2. Student content extractor；
3. Placement planner；
4. DOCX renderer；
5. OOXML utility；
6. Verifier / oracle；
7. Eval data quality。

### 16.2 学校特例准入条件

一个学校特例必须同时满足：

1. 有证据证明是学校特有需求；
2. 有 PM 或 owner 签收；
3. 登记在 School Exception Registry；
4. 用配置表达，不写核心代码分支；
5. 有专门测试覆盖；
6. 有影响范围说明；
7. 有复审或过期机制；
8. 不降低全局标准。

### 16.3 Exception Registry 示例

```yaml
exceptions:
  - exception_id: demo-school-cover-title-table
    school_id: demo-school
    template_version: v1
    stage: template
    affected_contract: template_contract.json
    reason: "Cover page title must be written into a fixed two-cell table required by official template."
    evidence_refs:
      - "template.docx#word/document.xml:tbl[1]"
    config_refs:
      - "school_config.yaml#cover.title_table"
    test_refs:
      - "tests/regression/demo_school_cover_title_table_test.py"
    signed_by: product-owner
    approved_at: "2026-06-14T10:00:00+09:00"
    review_after: "2026-09-01"
```

### 16.4 禁止模式

禁止在核心代码中出现：

```python
if school_id == "demo-school":
    do_special_case()
```

允许模式：

```text
通用能力 + signed contract + school config + verifier coverage + exception registry
```

---

## 17. Anti-drift 策略

### 17.1 禁止行为

DocFit 禁止以下行为：

1. 自动更新 signed standard；
2. 自动更新 golden；
3. 把 FAIL 降级成 WARN；
4. 把 UNKNOWN 当 PASS；
5. 让 expected 匹配当前错误输出；
6. 删除或忽略用户可见内容；
7. 关闭 verifier 让 case 通过；
8. 降低 coverage 阈值但不走 review；
9. 用 AI 结论替代 contract；
10. 以“学校特殊”为由绕过登记。

### 17.2 标准变更流程

任何标准变更必须包含：

- 变更前后 diff；
- 变更原因；
- 影响学校；
- 影响阶段；
- 旧 hash / 新 hash；
- 签收人；
- 新增或更新测试；
- 回滚策略。

### 17.3 Audit Log

Audit log 必须记录：

```json
{
  "event_id": "audit_001",
  "event_type": "signed_standard_change_attempt",
  "actor": "agent-or-user",
  "timestamp": "2026-06-14T10:00:00+09:00",
  "allowed": false,
  "reason": "golden update attempted after failing render eval without review",
  "affected_files": ["standards/schools/demo-school/v1/golden/feature_snapshot.json"]
}
```

---

## 18. Coverage 规范

Coverage 不是代码覆盖率，而是产品能力覆盖率。

### 18.1 Capability Coverage

Coverage profile 应声明要覆盖哪些能力。

示例：

```yaml
coverage_profile: bootstrap-core
required_capabilities:
  template:
    - template.docx_openable
    - template.required_regions
    - template.required_slots
    - template.styles_inventory
  content:
    - content.visible_paragraphs
    - content.visible_tables
    - content.reading_order
    - content.stable_ids
  placement:
    - placement.no_silent_drop
    - placement.slot_compatibility
    - placement.required_slots
  render:
    - render.valid_docx_package
    - render.plan_coverage
    - render.feature_snapshot
    - render.content_hash_coverage
```

### 18.2 覆盖不足

如果 case 没有覆盖某个 required capability，Harness 必须输出 UNKNOWN。

示例：

```json
{
  "status": "UNKNOWN",
  "type": "coverage_insufficient",
  "message": "bootstrap-core requires content.visible_tables but no fixture includes a table"
}
```

### 18.3 覆盖报告

Coverage report 必须包含：

```json
{
  "profile": "bootstrap-core",
  "status": "UNKNOWN",
  "required": 12,
  "covered": 10,
  "missing": [
    "content.visible_tables",
    "render.table_rendering"
  ]
}
```

---

## 19. Bootstrap Profile：AI Agent 初始实现目标

Bootstrap Profile 是最小可实现版本。它的目标不是解决全部论文格式问题，而是让 Agent 先实现正确架构和最小闭环。

### 19.1 Bootstrap 支持范围

Bootstrap 必须支持：

1. 一个 demo school；
2. 一个 `.docx` 模板；
3. 一个 `.docx` 用户论文；
4. 标题、正文段落、一个简单表格；
5. 简单样式映射；
6. 一份 Placement Plan；
7. 输出可打开的 `.docx`；
8. no silent drop verifier；
9. PASS / FAIL / UNKNOWN；
10. PM report；
11. issue cluster；
12. signed standard 禁止自动更新。

### 19.2 Bootstrap 可以暂不支持

Bootstrap 可以暂不支持，但必须遇到时 UNKNOWN：

- 公式；
- 图片；
- 文本框；
- 图表；
- 脚注；
- 尾注；
- 复杂分节；
- 多级复杂编号；
- 自动目录更新；
- 批注和修订。

### 19.3 Bootstrap 成功标准

Bootstrap 成功不是“转换很漂亮”，而是：

1. `docfit eval e2e` 能跑通；
2. 四阶段 artifact 都生成；
3. 每阶段 verifier 都运行；
4. 至少一个 PASS case；
5. 至少一个 FAIL case，证明 verifier 能抓到错误；
6. 至少一个 UNKNOWN case，证明缺能力不会被当 PASS；
7. silent drop 被检测为 FAIL；
8. AI diagnosis packet 能生成，但不影响 gate。

### 19.4 Bootstrap 必须包含的输入 fixture

```text
test_inputs/
  template_generation/
    bootstrap-demo-school-template.docx
  content_extraction/
    bootstrap-demo-student-pass.docx
    bootstrap-demo-student-unsupported-textbox.docx
    bootstrap-demo-student-silent-drop.docx
```

Bootstrap expected 中间产物不属于原始输入，必须放在 eval profile surface：

```text
standards/eval_profiles/bootstrap-core/expected/
  placement_plan.json
  feature_snapshot.json
```

### 19.5 Bootstrap CLI 验收

以下命令必须可运行：

```bash
docfit eval e2e \
  --school demo-school \
  --student test_inputs/content_extraction/bootstrap-demo-student-pass.docx \
  --out test_outputs/debug/template_eval_runs/bootstrap_pass
```

期望：

```text
status = PASS
```

以下命令必须输出 UNKNOWN：

```bash
docfit eval content \
  --student test_inputs/content_extraction/bootstrap-demo-student-unsupported-textbox.docx \
  --out test_outputs/debug/template_eval_runs/bootstrap_unknown
```

期望：

```text
status = UNKNOWN
finding.type = unsupported_visible_object
```

以下 private pytest proof 必须输出 FAIL，证明 verifier 能抓到跳过
placement action 的错误。Failure injection 禁止作为公开 CLI 选项暴露：

```bash
pytest tests/e2e/test_bootstrap_cli.py::test_fail_when_renderer_skips_action
```

期望：

```text
status = FAIL
finding.type = unplaced_content
```

---

## 20. MVP Profile

MVP 是 Bootstrap 之后的第一个产品可用版本。

### 20.1 MVP 支持范围

MVP 应支持：

1. 至少 1 个真实学校官方 `.docx` 模板；
2. 标题层级；
3. 正文段落；
4. 表格；
5. 图片及题注；
6. 中英文摘要和关键词；
7. 目录保留或重建策略；
8. 参考文献区域；
9. 页眉页脚基础保留；
10. signed golden feature diff；
11. OOXML package oracle；
12. 真实脱敏样本回归。

### 20.2 MVP 发布门禁

MVP 不能存在 blocking UNKNOWN。

MVP 必须满足：

| Gate | 要求 |
|---|---|
| Stage 1 | 目标学校模板 Template Contract PASS |
| Stage 2 | 核心用户内容类型 visible ledger coverage 100% |
| Stage 3 | No silent drop，所有 content_id 有处置 |
| Stage 4 | Render coverage 100%，OOXML oracle PASS，feature diff 无阻断差异 |
| Standards | signed standards 无漂移 |
| AI | 只做 RCA，不做裁判 |
| Exceptions | 所有学校特例登记、签收、配置化、测试覆盖 |

---

## 21. Agent 实现顺序

一个 AI Coding Agent 应按以下顺序实现。

### Step 1：建立状态和报告基础

实现：

- `Status = PASS | FAIL | UNKNOWN`
- 内部 stage lifecycle state 与 gate status 分离，例如 `ran` / `not_run`
- `Finding`
- `EvalRun`
- `summary.json`
- `pm_report.md`
- `issue_clusters.json`

验收：

- 能生成一个空 eval run；
- 缺 standard 输出 UNKNOWN；
- finding 能聚合到 issue cluster。

### Step 2：建立标准与 anti-drift

实现：

- signed standard loader；
- hash 检查；
- golden auto-update 禁止；
- audit log。

验收：

- 修改 signed standard 未签收时输出 UNKNOWN；
- 尝试自动更新 golden 被拒绝并记录 audit。

### Step 3：实现 Stage 1 最小模板解析

实现：

- 打开 `.docx`；
- 读取 styles；
- 读取 body paragraph；
- 识别 demo slots；
- 生成 Template Artifact；
- Template Verifier。

验收：

- demo template PASS；
- 缺 required slot FAIL；
- 遇到 unsupported layout feature UNKNOWN。

### Step 4：实现 Stage 2 最小内容提取

实现：

- 读取用户 `.docx`；
- 提取可见段落；
- 提取简单表格；
- 生成稳定 `content_id`；
- 生成 reading order；
- 生成 Student Content Artifact；
- Visible Content Verifier。

验收：

- 正常样本 PASS；
- 含 text box 样本 UNKNOWN；
- 人为漏段落样本 FAIL。

### Step 5：实现 Stage 3 最小 placement

实现：

- 按简单规则把标题、正文、表格映射到 demo slots；
- 每个 `content_id` 生成 disposition；
- No Silent Drop Verifier；
- Slot Compatibility Verifier。

验收：

- 所有 content_id 都有 action；
- 删除一个 action 会 FAIL；
- slot 不存在会 FAIL。

### Step 6：实现 Stage 4 最小渲染

实现：

- 基于模板复制 docx；
- 按 Placement Plan 写入段落和表格；
- 生成 render manifest；
- 生成 feature snapshot；
- 检查 docx package；
- 检查 plan coverage。

验收：

- 输出 docx 可打开；
- render manifest 覆盖所有 action；
- 缺 action 执行 FAIL；
- 缺 golden UNKNOWN。

### Step 7：实现 `docfit convert`

实现：

- 串联四阶段；
- 任一 FAIL/UNKNOWN 阻断；
- 成功时输出 final.docx；
- 失败时输出用户可读摘要和内部报告。

验收：

- bootstrap PASS case 通过；
- bootstrap UNKNOWN case 被阻断；
- bootstrap FAIL case 被阻断。

### Step 8：实现 AI RCA packet

实现：

- 从 findings 生成 diagnosis packet；
- 明确 allowed / forbidden AI tasks；
- AI 输出只保存为 advisory。

验收：

- AI advisory 不改变 summary status。

---

## 22. 测试规范

### 22.1 测试分层

DocFit 应包含：

| 层级 | 目的 |
|---|---|
| Unit Tests | 检查小函数、schema、hash、状态合并 |
| Contract Tests | 检查 stage artifact 是否满足 contract |
| Regression Tests | 每个已修 bug 必须固化 |
| Golden Tests | 检查 signed golden 与 feature snapshot |
| E2E Harness Tests | 检查四阶段串联和 gate 行为 |
| Standards Audit Tests | 检查 anti-drift |

### 22.2 必需测试

初始实现必须包含：

1. `test_unknown_when_standard_missing`
2. `test_fail_when_template_slot_missing`
3. `test_fail_when_visible_content_missing_from_ledger`
4. `test_fail_when_content_unplaced`
5. `test_unknown_when_unsupported_visible_object`
6. `test_fail_when_renderer_skips_action`
7. `test_unknown_when_golden_missing`
8. `test_ai_advisory_does_not_change_status`
9. `test_signed_standard_cannot_auto_update`
10. `test_convert_blocks_on_unknown`

### 22.3 测试命令

```bash
pytest tests/unit
pytest tests/contract
pytest tests/regression
pytest tests/e2e
```

Harness 命令：

```bash
docfit eval e2e --case bootstrap_e2e_demo_001
```

---

## 23. 用户错误信息规范

内部报告可以详细，但用户错误信息必须清楚、可行动。

### 23.1 UNKNOWN 用户信息

```text
当前无法安全转换该文档，因为文档中包含系统尚不能可靠处理的可见内容：文本框。为避免丢失内容，本次转换已停止。
```

### 23.2 FAIL 用户信息

```text
转换失败：系统已提取到文档中的全部内容，但其中 2 个段落无法匹配到目标学校模板中的位置。请查看报告或联系维护者处理。
```

### 23.3 禁止用户信息

禁止输出：

```text
转换成功，但可能有少量内容缺失。
```

禁止输出：

```text
AI 判断结果看起来没问题，因此已通过。
```

---

## 24. 安全与隐私

DocFit 处理的是论文文档，可能包含个人信息、未发表研究内容和学校内部格式要求。

实现应该：

1. 在报告中默认使用 text preview，而不是全文；
2. 支持 redaction；
3. AI diagnosis packet 默认不包含完整论文；
4. artifact 中保留 hash 和 source ref，以便定位但减少泄露；
5. 测试 fixture 应尽量使用 synthetic 或脱敏样本；
6. 对真实用户文档的报告输出路径和保留期限进行配置。

---

## 25. 符合性要求

一个实现只有满足以下条件，才能称为符合本 SPEC 的 Bootstrap 实现：

```text
[ ] 有 Eval Harness 主入口
[ ] 有 PASS / FAIL / UNKNOWN 三态
[ ] UNKNOWN 阻断 convert
[ ] 有 signed standard loader
[ ] 有 anti-drift 检查
[ ] 有四阶段 runner
[ ] 有四阶段 artifact
[ ] 有四阶段 verifier
[ ] 有 Visible Content Ledger
[ ] 有 No Silent Drop Verifier
[ ] 有 Render Manifest
[ ] 有 PM Report
[ ] 有 Issue Cluster
[ ] 有 AI Diagnosis Packet
[ ] AI 不影响最终状态
[ ] 有 bootstrap PASS case
[ ] 有 bootstrap FAIL case
[ ] 有 bootstrap UNKNOWN case
```

一个实现只有满足以下条件，才能称为符合本 SPEC 的 MVP 实现：

```text
[ ] 至少一个真实学校官方 docx 模板通过 Stage 1
[ ] Stage 2 支持核心论文内容类型
[ ] Stage 3 对所有 visible content 有处置
[ ] Stage 4 输出通过 OOXML oracle
[ ] signed golden feature diff 无阻断差异
[ ] 所有学校特例登记、配置化、测试覆盖
[ ] 无 blocking UNKNOWN
[ ] 无 silent drop
[ ] 标准变更可审计
```

---

## 26. 最终架构原则

DocFit 的核心产品能力不是“转换 Word”，而是“可证明地转换 Word”。

因此，本系统必须遵守：

1. Harness before convert；
2. Contract before implementation；
3. Verifier before AI judgment；
4. UNKNOWN before unsafe success；
5. No silent drop；
6. Generic fix before school patch；
7. Signed standards before green tests；
8. Render executes plan, never re-decides placement。

`docfit convert` 的成功必须意味着：

> 学校模板已被验证理解，用户内容已被完整提取，每个可见内容都有明确去向，最终 DOCX 是按计划渲染并通过 oracle 检查的结果。

如果做不到这一点，DocFit 应该诚实输出 `FAIL` 或 `UNKNOWN`，而不是生成一个看似成功但不可证明的 Word 文件。
