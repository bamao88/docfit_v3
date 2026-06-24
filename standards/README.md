# Standards 目录结构讨论稿

一句话结论：`standards/` 只放“怎么判定正确”的签收标准；原始 Word 输入放到输入目录，实际运行输出放到输出目录。每个阶段评测都必须能说清楚：读什么输入、产出什么输出、用哪个标准检查输出。

本文是目标结构讨论稿，不表示当前仓库已经全部迁移完成。目录树里的注释统一先写状态：`已有` 表示当前仓库已经有对应内容或近似内容；`需要补充` 表示目录或文件还没有准备好，或者当前只在旧位置有近似内容。

## 管理原则

1. 原始输入、签收标准、运行输出必须分开。
   - 原始输入：学校原始模板 Word、学生原始 Word、人工 review 原文、输入 hash。
   - 签收标准：阶段输出应该满足什么、缺证据怎么判、标准来源是什么。
   - 运行输出：某次命令实际跑出来的 JSON、DOCX、manifest、报告。

2. `standards/` 不是输入目录，也不是输出目录。
   - 不把学校原始模板 Word 放进 `standards/`。
   - 不把学生原始 Word 放进 `standards/`。
   - 不把某次运行生成的 JSON/DOCX 直接放进 `standards/` 当标准。

3. 每个阶段标准都要绑定一组输入和输出。
   - 阶段输入是这个阶段 verifier 或单阶段测试要读取的 fixture。
   - 阶段输出是这个阶段真实运行产生的 artifact。
   - 阶段标准检查这个阶段输出是否满足已签收要求。

4. 上一阶段的已签收输出，可以成为下一阶段的冻结输入。
   - 例如模板生成 01 的输出 `source_template_tree.json`，经人工确认后，可以作为 02 单阶段测试的 `source_template_tree.input.json`。
   - 这个冻结输入属于输入 fixture，不属于运行输出。

5. `expected` 文件不是“当前输出复制品”。
   - `*.expected.yaml` / `*.expected.json` 表示人工签收后的期望标准。
   - 如果当前输出和 expected 不一致，应该让评测返回 `FAIL` 或 `UNKNOWN`，不能为了变绿自动改 expected。

6. 缺标准、缺输入、缺输出、缺 verifier 都不能通过。
   - 缺标准：`UNKNOWN`。
   - 缺阶段输入 fixture：单阶段评测应为 `UNKNOWN`。
   - 缺阶段运行输出：对应阶段应为 `UNKNOWN`。
   - verifier 未启用：不能写成 `PASS`。

7. 通用合同和学校/学生/case 专属标准要分开。
   - 通用合同说明某类阶段必须证明什么。
   - 学校标准说明某个目标模板应该是什么。
   - 学生标准说明某个学生源文档的可见内容是什么。
   - case 标准说明某个目标模板和某个学生组合时，内容应该怎么放、最终 Word 应该怎么渲染。

## 目标目录树

```text
docfit_v3/
├── inputs/                                                       # 需要补充：原始输入根目录；当前仓库近似内容仍在 test_inputs/
│   ├── targets/                                                  # 需要补充：目标模板输入；现在主要是学校模板，也可以扩展到期刊/会议模板
│   │   ├── pku-graduate/                                         # 需要补充：PKU 研究生目标模板输入包
│   │   │   └── template_generation/                              # 需要补充：模板生成相关输入，不放标准
│   │   │       ├── 00_pipeline/                                  # 需要补充：整条 template-generate pipeline 的输入
│   │   │       │   ├── source_template.input.docx                # 需要补充：学校原始模板 Word；整个模板生成链路的真实输入
│   │   │       │   ├── source_review.input.md                    # 需要补充：人工模板 review 原文；生成标准的证据
│   │   │       │   └── input_manifest.yaml                       # 需要补充：记录 source_template/review 的来源、hash、签收状态
│   │   │       ├── 01_source_parse/                              # 需要补充：单独测试 01 阶段时读取的输入
│   │   │       │   ├── source_template.input.docx                # 需要补充：01 输入；可引用 00_pipeline/source_template.input.docx
│   │   │       │   └── input_manifest.yaml                       # 需要补充：绑定 01 输入 hash
│   │   │       ├── 02_structure_discovery/                       # 需要补充：单独测试 02 阶段时读取的输入
│   │   │       │   ├── source_template_tree.input.json           # 需要补充：冻结后的 01 输出；作为 02 输入 fixture
│   │   │       │   └── input_manifest.yaml                       # 需要补充：说明该 input 来自哪次 01 校准输出和 hash
│   │   │       ├── 03_generation_model/                          # 需要补充：单独测试 03 阶段时读取的输入
│   │   │       │   ├── template_generation_request.input.json    # 需要补充：03 输入之一；生成请求
│   │   │       │   ├── template_structure_candidates.input.json  # 需要补充：冻结后的 02 输出；作为 03 输入 fixture
│   │   │       │   └── input_manifest.yaml                       # 需要补充：绑定 03 输入 hash
│   │   │       ├── 04_plan_build/                                # 需要补充：单独测试 04 阶段时读取的输入
│   │   │       │   ├── template_generation_model.input.json      # 需要补充：冻结后的 03 输出；作为 04 输入 fixture
│   │   │       │   └── input_manifest.yaml                       # 需要补充：绑定 04 输入 hash
│   │   │       └── 05_action_execution/                          # 需要补充：单独测试 05 阶段时读取的输入
│   │   │           ├── source_template.input.docx                # 需要补充：05 输入之一；用于整包复制源 Word
│   │   │           ├── template_generation_plan.input.json       # 需要补充：冻结后的 04 输出；作为 05 输入 fixture
│   │   │           └── input_manifest.yaml                       # 需要补充：绑定 05 输入 hash
│   │   ├── nannong-undergraduate/                                # 需要补充：南京农业本科目标模板输入包
│   │   └── hunannongye/                                          # 需要补充：湖南农业目标模板输入包
│   └── students/                                                 # 需要补充：学生源文档输入
│       ├── real-student-001/                                     # 需要补充：一个学生源文档输入包
│       │   ├── source_document.input.docx                        # 需要补充：学生原始 Word；内容提取阶段输入
│       │   ├── content_review.input.md                           # 需要补充：人工内容 review 原文；生成学生内容标准的证据
│       │   └── input_manifest.yaml                               # 需要补充：记录学生源 Word/review 的来源、hash、签收状态
│       ├── real-student-002/                                     # 需要补充：第二个学生源文档输入包
│       └── real-student-003/                                     # 需要补充：第三个学生源文档输入包
│
├── standards/                                                    # 已有：签收标准根目录；本文所在目录
│   ├── README.md                                                 # 已有：标准目录结构和管理原则说明
│   ├── shared_contracts/                                         # 需要补充：通用阶段合同；当前三校合同仍重复放在 standards/schools/*/v1/
│   │   ├── template_generation_contract.json                     # 需要补充：模板生成 01-05 通用合同；当前没有独立合同
│   │   ├── template_quality_contract.json                        # 需要补充：最终模板质量合同；当前近似内容是 template_contract.json
│   │   ├── student_content_contract.json                         # 需要补充：内容提取合同；当前近似内容是 student_content_contract.json
│   │   ├── placement_contract.json                               # 需要补充：内容放置合同；当前近似内容是 placement_contract.json
│   │   └── render_contract.json                                  # 需要补充：DOCX 渲染合同；当前近似内容是 render_contract.json
│   │
│   ├── targets/                                                  # 需要补充：目标模板标准；当前近似内容在 standards/schools/<school>/v1/
│   │   ├── pku-graduate/                                         # 需要补充：PKU 研究生目标模板标准包
│   │   │   ├── standard_index.yaml                               # 需要补充：目标标准入口；当前近似内容是 signed_standard.yaml
│   │   │   ├── template_generation/                              # 需要补充：模板生成 01-05 阶段标准；当前近似内容在 template_generation_stages/
│   │   │   │   ├── 00_pipeline.expected.yaml                     # 需要补充：整条模板生成链路标准；输入 source_template，最终输出 generated_template
│   │   │   │   ├── 01_source_parse.expected.yaml                 # 需要补充：检查 01 输出 source_template_tree.json
│   │   │   │   ├── 02_structure_discovery.expected.yaml          # 需要补充：检查 02 输出 template_structure_candidates.json
│   │   │   │   ├── 03_generation_model.expected.yaml             # 需要补充：检查 03 输出 template_generation_model.json
│   │   │   │   ├── 04_plan_build.expected.yaml                   # 需要补充：检查 04 输出 template_generation_plan.json
│   │   │   │   └── 05_action_execution.expected.yaml             # 需要补充：检查 05 输出 generated_template.docx + manifest
│   │   │   └── template_quality/                                 # 需要补充：最终生成模板质量标准
│   │   │       └── final_template.expected.yaml                  # 需要补充：检查 generated_template.docx；当前近似内容是 template_generation_final.yaml
│   │   ├── nannong-undergraduate/                                # 需要补充：南京农业本科目标模板标准包
│   │   └── hunannongye/                                          # 需要补充：湖南农业目标模板标准包
│   │
│   ├── students/                                                 # 需要补充：学生内容标准；当前近似内容在 eval_profiles/real-core-v0/expected/student_content_trees/
│   │   ├── real-student-001/                                     # 需要补充：一个学生内容标准包
│   │   │   ├── standard_index.yaml                               # 需要补充：学生内容标准入口
│   │   │   └── content_extraction.expected.yaml                  # 需要补充：检查 student_content_artifact/tree
│   │   ├── real-student-002/                                     # 需要补充：第二个学生内容标准包
│   │   └── real-student-003/                                     # 需要补充：第三个学生内容标准包
│   │
│   ├── conversion_cases/                                         # 需要补充：目标模板 × 学生文档 的组合标准
│   │   ├── pku-graduate__real-student-001/                       # 需要补充：一个完整转换 case 标准包
│   │   │   ├── case_index.yaml                                   # 需要补充：case 入口；绑定 target 标准、student 标准和输入 hash
│   │   │   ├── placement/                                        # 需要补充：内容放置阶段标准
│   │   │   │   └── placement.expected.yaml                       # 需要补充：检查 placement_plan；当前近似内容在 render_plans/
│   │   │   └── render/                                           # 需要补充：DOCX 渲染阶段标准
│   │   │       ├── render.expected.yaml                          # 需要补充：检查 final.docx + render_manifest；当前没有完整标准
│   │   │       ├── feature_snapshot.expected.json                # 需要补充：检查渲染特征；当前近似内容在 render_feature_snapshots/
│   │   │       └── word_image_evidence.expected.yaml             # 需要补充：检查 Word 视觉证据；当前缺失，所以 coverage 仍 UNKNOWN
│   │   └── ...                                                   # 需要补充：其余 8 个 real-core-v0 转换 case
│   │
│   └── eval_profiles/                                            # 已有：评测组合，不是标准本体
│       ├── real-core-v0/                                         # 已有：真实三校三学生 profile
│       │   ├── README.md                                         # 已有：profile 状态说明
│       │   ├── cases.yaml                                        # 已有：登记 3 个 target、3 个 student、9 个 conversion case
│       │   └── expected/                                         # 已有：当前临时承载部分 expected；后续应迁到 students/ 和 conversion_cases/
│       └── bootstrap-core/                                       # 已有：bootstrap demo profile
│
└── test_outputs/                                                 # 已有：运行输出根目录；可删除重跑，不能手工当标准
    └── debug/                                                    # 已有：调试和评测输出
        ├── template_generation/                                  # 已有：模板生成运行输出；包括 01-05 JSON、generated_template.docx、manifest
        └── template_eval_runs/                                   # 已有：template-gap、coverage、e2e、convert 报告
```

## 模板生成阶段的输入、输出和标准

模板生成整体只有一个真实 pipeline 输入：目标学校的原始模板 Word。为了单独测试每个阶段，还需要把上一阶段已确认的输出冻结成下一阶段输入 fixture。

| 阶段 | 阶段输入 fixture | 阶段运行输出 | 阶段标准 |
| --- | --- | --- | --- |
| 整条 pipeline | `source_template.input.docx` | `generated_template.docx`、`template_generation_manifest.json` | `00_pipeline.expected.yaml` |
| `01_source_parse` | `source_template.input.docx` | `source_template_tree.json` | `01_source_parse.expected.yaml` |
| `02_structure_discovery` | `source_template_tree.input.json` | `template_structure_candidates.json` | `02_structure_discovery.expected.yaml` |
| `03_generation_model` | `template_generation_request.input.json`、`template_structure_candidates.input.json` | `template_generation_model.json` | `03_generation_model.expected.yaml` |
| `04_plan_build` | `template_generation_model.input.json` | `template_generation_plan.json` | `04_plan_build.expected.yaml` |
| `05_action_execution` | `source_template.input.docx`、`template_generation_plan.input.json` | `generated_template.docx`、`template_generation_manifest.json` | `05_action_execution.expected.yaml` |

单阶段测试应该固定读取这一组三件套：

```text
inputs/targets/<target>/template_generation/<stage>/*.input.*
standards/targets/<target>/template_generation/<stage>.expected.*
test_outputs/debug/template_generation/<run_id>/<stage actual output>
```

这解决两个问题：

- 整条 pipeline 可以从真实学校模板 Word 开始跑。
- 任意一个中间阶段也可以用冻结 input fixture 单独测试，不需要每次从 01 重新跑到该阶段。

## 标准文件必须声明的字段

每个阶段标准至少要写清楚这些内容：

```yaml
standard_scope: template_generation_stage
stage_id: 02_structure_discovery
source_inputs:
  stage_input:
    path: inputs/targets/pku-graduate/template_generation/02_structure_discovery/source_template_tree.input.json
    sha256: sha256:...
  upstream_review:
    path: inputs/targets/pku-graduate/template_generation/00_pipeline/source_review.input.md
    sha256: sha256:...
expected_output:
  artifact_type: template_structure_candidates
  checked_by: standards/targets/pku-graduate/template_generation/02_structure_discovery.expected.yaml
actual_output:
  default_run_path: test_outputs/debug/template_generation/<run_id>/02_template_structure_candidates.json
gate_policy:
  missing_input_result: UNKNOWN
  missing_output_result: UNKNOWN
  missing_verifier_result: UNKNOWN
  not_configured_is_not_pass: true
```

字段含义：

| 字段 | 含义 |
| --- | --- |
| `standard_scope` | 说明这是哪个阶段或哪类检查的标准 |
| `stage_id` | 阶段 ID，必须和目录/文件名一致 |
| `source_inputs` | 阶段测试读取的输入 fixture 和人工证据 |
| `expected_output` | 这个阶段输出应该是什么类型，以及用哪个标准检查 |
| `actual_output` | 真实运行时输出通常在哪里产生；不能作为标准自动更新来源 |
| `gate_policy` | 缺输入、缺输出、缺 verifier 时怎么判定 |

## 命名规则

| 类型 | 命名 | 说明 |
| --- | --- | --- |
| 阶段输入 fixture | `*.input.json`、`*.input.docx`、`*.input.md` | 冻结后喂给单阶段测试 |
| 阶段期望标准 | `*.expected.yaml`、`*.expected.json` | 检查该阶段输出的签收标准 |
| 入口文件 | `standard_index.yaml`、`case_index.yaml` | 只做索引、hash 绑定和标准清单 |
| manifest | `input_manifest.yaml` | 记录原始输入或冻结输入的来源和 hash |
| 运行输出 | 保持生产代码原名 | 放在 `test_outputs/`，不放进 `standards/` |

## 当前仓库对应关系

当前仓库还没有完全按目标结构迁移。现有内容大致对应如下：

| 当前位置 | 目标位置 | 状态 |
| --- | --- | --- |
| `test_inputs/template_generation/school-*-template*.docx` | `inputs/targets/<target>/template_generation/00_pipeline/source_template.input.docx` | 需要补充：当前仍在旧输入目录 |
| `test_inputs/template_generation/*-review.*` | `inputs/targets/<target>/template_generation/00_pipeline/source_review.input.md` | 需要补充：当前仍在旧输入目录 |
| `standards/schools/<school>/v1/signed_standard.yaml` | `standards/targets/<target>/standard_index.yaml` | 需要补充：当前是旧入口名和旧层级 |
| `standards/schools/<school>/v1/template_generation_final.yaml` | `standards/targets/<target>/template_quality/final_template.expected.yaml` | 需要补充：当前是旧位置和旧命名 |
| `standards/schools/<school>/v1/template_generation_stages/*.yaml` | `standards/targets/<target>/template_generation/*.expected.yaml` | 需要补充：当前已有阶段标准，但目录和文件名还不完全清晰 |
| `standards/eval_profiles/real-core-v0/expected/student_content_trees/*.yaml` | `standards/students/<student>/content_extraction.expected.yaml` | 需要补充：当前放在 profile expected 下 |
| `standards/eval_profiles/real-core-v0/expected/render_plans/*.yaml` | `standards/conversion_cases/<target>__<student>/placement/placement.expected.yaml` | 需要补充：当前放在 profile expected 下 |
| `standards/eval_profiles/real-core-v0/expected/render_feature_snapshots/*.json` | `standards/conversion_cases/<target>__<student>/render/feature_snapshot.expected.json` | 需要补充：当前放在 profile expected 下 |
| `test_outputs/debug/template_generation/**` | `test_outputs/debug/template_generation/**` | 已有：运行输出位置保持不变 |

