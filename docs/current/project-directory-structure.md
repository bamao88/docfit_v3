# DocFit v3 项目结构总纲（当前唯一权威）

> Status: 当前维护版 / Single Source of Truth
> 本文是新增输入、标准、运行输出、测试 fixture、文档和代码模块时的唯一目录规则正文。
> 根目录 `DIRECTORY_STRUCTURE.md` 和 `docs/human/project-directory-structure.md` 只保留入口指针，不再维护第二份目录表。
> 历史文档里出现的 `test_inputs/`、`test_outputs/`、`standards/schools/`、`standards/eval_profiles/**/expected/` 等旧路径只作为历史上下文，不代表当前新增文件规则。

---

## 0. 已收敛的文档口径

目录结构约定现在只有一份正文：本文。

| 文档 | 当前身份 | 维护规则 |
| --- | --- | --- |
| `docs/current/project-directory-structure.md` | 唯一权威正文 | 修改目录放置规则只改这里 |
| `DIRECTORY_STRUCTURE.md` | 根目录短入口 | 只指向本文，不新增目录表 |
| `docs/human/project-directory-structure.md` | 历史迁移指针 | 只指向本文，不新增目录表 |
| `docs/human/**`、`docs/plans/**` 中的旧路径 | 历史记录或当时计划 | 可引用作背景，不能当当前放置规则 |

新增文件时只按本文判断。若历史文档、旧命令或旧计划中仍出现 `test_inputs/`、`test_outputs/`、`standards/schools/` 等路径，默认按 §5 的历史路径对照翻译到当前目录。

本文保留两类历史信息：

1. §4 记录当初讨论稿之间的裁决，避免同一个问题反复争论。
2. §5 记录旧路径到当前路径的映射，方便读旧 review packet、旧 plan 和旧运行证据。

---

## 1. 一句话顶层原则

> **能力放 `src/`，输入放 `inputs/`，标准放 `standards/`，组合放 `eval_profiles/`，结果放 `runs/`，代码测试放 `tests/`，说明放 `docs/`。**

七个顶层目录，每个只回答一个问题：

| 目录 | 回答的问题 |
| --- | --- |
| `src/docfit/` | 用什么能力做 |
| `inputs/` | 拿什么输入做（可复现、不可程序改写） |
| `standards/` | 怎样算做对了（人工签收，不可程序改写） |
| `eval_profiles/` | 这次要跑哪些组合 |
| `runs/` | 这次实际跑出了什么（可删、可重跑） |
| `tests/` | 代码本身对不对 |
| `docs/` | 这套东西怎么回事 |

当前 active 边界：只推进模板阶段，包括模板解析、模板生成 T1-T6、模板 gap 和模板标准裁判。学生内容提取、内容放置和最终 DOCX 渲染保留为长期产品方向；在流程和阶段产物未定义清楚前，不制作对应标准。

---

## 2. 顶层目录树（裁定版）

仅展开到能说明职责的层级；叶子文件命名见 §10，逐阶段三件套见架构稿/命名稿正文。
目录已按仓库实际资产对齐：4 个 target（demo-school / pku-graduate / nannong-undergraduate / hunannongye）、3 个真实学生（real-student-001/002/003）。

```text
docfit_v3/
├── README.md / SPEC.md / STATUS.md
├── DIRECTORY_STRUCTURE.md          # 短入口，正文指向 docs/current/project-directory-structure.md
├── pyproject.toml / uv.lock
│
├── docs/                           # 只放说明，不放可执行标准、不放运行输出
│   ├── current/                    # 长期维护的当前正文（本文住这里）
│   ├── plans/                      # 计划、阶段拆解、历史方案
│   ├── human/                      # 人工 review、讨论材料、过程记录
│   └── agents/                     # agent 操作手册
│
├── src/docfit/                     # 生产代码（详见 §6）
│   ├── cli/                        # 入口，只做参数解析与命令分发
│   ├── harness/                    # 控制平面：决定测什么、用什么标准、判 PASS/FAIL/UNKNOWN
│   │   ├── template_generation_standard_judge.py      # 模板生成标准裁判主入口
│   │   ├── template_generation_standard_quality.py    # T1-T5 阶段标准本身的质量检查
│   │   ├── template_generation_run_bundle.py          # 绑定某次 template-generate run 的产物和 hash
│   │   ├── template_generation_stage_verifiers.py     # T1-T5 阶段标准 verifier
│   │   └── template_generation_judge_reports.py       # 聚合报告与 Markdown/JSON 输出
│   ├── core/                       # 跨切面：io / models / status
│   ├── contracts/                  # 契约 schema 与 verifier 基类（不放具体学校标准）
│   ├── stages/                     # 业务阶段代码；当前 active 只有模板侧
│   │   ├── template_parse/         # active
│   │   ├── content_extract/        # reserved，流程未清晰前不做标准
│   │   ├── placement/              # reserved，依赖 content_extract
│   │   └── render/                 # reserved，依赖 placement
│   ├── template_generation/        # 模板侧支撑流程（非业务阶段）
│   ├── template_gap/               # 模板质量差距检查（非业务阶段）
│   ├── template_model/             # 模板结构共享模型，不做门禁裁判
│   ├── convert/                    # 长期产品转换编排；当前不作为 active 标准制作入口
│   ├── ooxml/                      # Word / OOXML 底层能力
│   ├── ai_rca/                     # AI 只做根因分析建议，不做裁判
│   └── utils/
│
├── inputs/                         # 可复现输入；不放 expected、不放运行输出
│   ├── targets/<target_id>/
│   │   ├── input_manifest.yaml
│   │   ├── raw/                    # 不可变原始证据（原始文件名不带 .input）
│   │   └── fixtures/              # 为单阶段测试冻结的上游输出（文件名带 .input）
│   │       ├── template_generation/<NN_stage>/
│   │       └── template_gap/
│   └── students/<student_id>/       # reserved for later student-content work
│       ├── input_manifest.yaml
│       └── raw/
│
├── standards/                      # 签收标准；只放"怎么判定正确"
│   ├── contracts/                  # 通用合同，全项目共用一份（不再每校复制）
│   │   ├── template.contract.json
│   │   ├── student_content.contract.json
│   │   ├── placement.contract.json
│   │   ├── render.contract.json
│   │   ├── template_generation.contract.json
│   │   └── template_quality.contract.json
│   ├── targets/<target_id>/<version>/
│   │   ├── target.standard.yaml    # 入口：owner、版本、输入 hash、合同、golden、exceptions
│   │   ├── template_parse/
│   │   ├── template_generation/t1_document_facts.standard.yaml
│   │   ├── template_generation/t2_unit_pagination.standard.yaml
│   │   ├── template_generation/t3_element_policy.standard.yaml
│   │   ├── template_generation/t4_global_layout.standard.yaml
│   │   ├── template_generation/t5_template_spec.standard.yaml
│   │   ├── template_quality/final_template.expected.yaml
│   │   ├── golden/
│   │   └── exceptions.yaml
│   ├── students/<student_id>/<version>/      # reserved until content extraction flow is defined
│   │   ├── student.standard.yaml
│   │   └── content_extract/student_content_artifact.expected.yaml
│   └── cases/<target_id>__<student_id>/<version>/  # reserved until placement/render flows are defined
│       ├── case.standard.yaml
│       ├── placement/placement_plan.expected.yaml
│       └── render/{render_manifest,feature_snapshot,word_image_evidence}.expected.*
│
├── eval_profiles/                  # 评测组合；只组合 case 与 coverage gate，不承载标准本体
│   ├── bootstrap-core/{profile.yaml, README.md}
│   └── real-core-v0/{profile.yaml, README.md}
│
├── runs/                           # 运行输出；可删除、可重跑、不能当标准
│   ├── template_generation/<run_id>/
│   ├── eval/<run_id>/              # harness 门禁运行（coverage / e2e / 各阶段证据）
│   ├── eval/template_generation_standard_quality/<scope>/  # T1-T5 标准质量报告
│   ├── eval/template_generation_judge/<target_id>/<source_run_id>/  # 标准裁判读取某次 template-generate run 后的报告
│   ├── convert/<run_id>/           # 产品转换运行（final.docx）
│   └── workbench/                  # 本地实验，不进标准、不进门禁
│
├── tests/                          # 代码级测试；不放业务输入资产、不放长期运行输出
│   ├── unit/ │ contract/ │ regression/ │ e2e/
│   └── fixtures/                   # 小型代码测试 fixture，不与 inputs/ 混用
│
└── scripts/                        # 迁移、检查、维护脚本
```

---

## 3. 七个顶层目录职责

| 目录 | 放什么 | 禁止放什么 |
| --- | --- | --- |
| `src/docfit/` | 生产代码、Runner、Verifier、OOXML、CLI | 原始 Word、expected、运行结果 |
| `inputs/` | 学校模板、学生文档、人工 review、冻结 fixture、输入 hash | expected、golden、actual output |
| `standards/` | 签收标准、通用合同、golden、exception | 原始 Word、某次运行输出 |
| `eval_profiles/` | case 列表、coverage gate、profile 预期状态 | 具体 expected / golden 本体 |
| `runs/` | 每次命令产生的 artifact、报告、final.docx | 人工签收标准 |
| `tests/` | pytest 代码级测试 | 业务输入资产、长期运行输出 |
| `docs/` | 说明、决策、迁移记录 | 可执行标准、运行输出 |

---

## 4. 已裁定口径

这一节保留当初目录讨论稿之间的裁决记录。它不是第二套规则；后续新增文件直接按“裁定”列执行。

裁定原则：**① 与当前仓库实际资产一致；② 命名后缀体系自洽（`.input` / `.expected` / `.contract` / `.standard`）；③ 不丢能力**。

| # | 已裁定问题 | 曾出现过的口径 A | 曾出现过的口径 B | 当前规则 | 理由 |
| --- | --- | --- | --- | --- | --- |
| 1 | 通用合同目录 | `standards/shared_contracts/` | `standards/contracts/` | **`standards/contracts/`** | 更短；当前仓库已收敛为顶层一份通用合同 |
| 2 | 合同文件名 | `template_contract.json`（前缀） | `template.contract.json`（后缀） | **`*.contract.json`（后缀）** | 与 `.expected.*` / `.standard.yaml` 后缀体系一致；按后缀即可判文件角色 |
| 3 | target 是否带版本层 | 带 `<version>/` | 不带 | **带 `<version>/`** | 当前标准在 `standards/targets/<target_id>/v1/`；重新签收旧标准需要并存版本 |
| 4 | 学生 id 格式 | `real-student-001` | `real-001` | **`real-student-001`** | 仓库实际就是 `real-student-001`，改短反而要动一批文件名 |
| 5 | raw 原始文件是否带 `.input` | 带（`source_template.input.docx`） | 不带 | **不带** | `.input` 只标记"冻结给下游读的 fixture"；原始证据不是 fixture |
| 6 | 标准入口名 | `case_standard.yaml`（下划线） | `case.standard.yaml`（点） | **`*.standard.yaml`（后缀）** | 同 #2，后缀体系自洽 |
| 7 | `runs/` 子目录 | `eval/` + `convert/` + `template_generation/` + `workbench/` | `template_generation/` + `conversion/` + `reports/` | **`template_generation/` + `eval/` + `convert/` + `workbench/`** | 与 CLI 动词（`docfit eval` / `docfit convert`）对齐；`reports/` 实为 eval 输出的子集 |
| 8 | src 模块视图 | 给出完整模块树 | 未展开 | **采用架构稿，并按 §6 对齐现状** | 架构稿更完整 |
| 9 | 当前启用阶段边界 | 四阶段 + 支撑模块分离 | 模板侧先行 | **当前 active 只有模板侧**；学生/放置/render 保留为长期方向 | 学生内容流程和标准尚未定义清楚，不能提前当作当前 gate |

---

## 5. 历史路径对照

这一节只用于阅读旧文档、旧 review packet、旧计划和旧运行记录。新文件不要写到“历史路径”列。

### 5.1 输入：历史 `test_inputs/` → 当前 `inputs/`

| 历史路径 | 当前路径 |
| --- | --- |
| `test_inputs/template_generation/school-<x>-template.docx` | `inputs/targets/<x>/raw/source_template.docx` |
| `test_inputs/template_generation/school-<x>-template-review.txt` | `inputs/targets/<x>/raw/source_review.md` |
| `test_inputs/template_generation/school-hunannongye-requirement*.{doc,docx}` | `inputs/targets/hunannongye/raw/`（额外格式要求源） |
| `test_inputs/content_extraction/real-student-00N-source.docx` | `inputs/students/real-student-00N/raw/source_document.docx` |
| `test_inputs/content_extraction/real-student-00N-content-review.md` | `inputs/students/real-student-00N/raw/content_review.md` |
| `test_inputs/content_extraction/bootstrap-demo-student-*.docx` | `inputs/students/bootstrap-demo-*/raw/source_document.docx` |
| `test_inputs/template_gap/real-core-v0-<x>-generated-template.docx` | `inputs/targets/<x>/fixtures/template_gap/generated_template.input.docx`（被测 = 冻结 fixture） |
| `test_inputs/template_generation/unit_copy_test_0N.docx` | bootstrap/单测夹具 → `tests/fixtures/` 或 `inputs/targets/.../fixtures/` |

### 5.2 标准：历史 `standards/schools/` + `standards/eval_profiles/.../expected/` → 当前 `standards/{contracts,targets,students,cases}/`

| 历史路径 | 当前路径 |
| --- | --- |
| `standards/schools/<x>/v1/{template,student_content,placement,render}_contract.json`（**每校重复**） | 去重后只留一份 → `standards/contracts/*.contract.json` |
| `standards/schools/<x>/v1/signed_standard.yaml` | `standards/targets/<x>/v1/target.standard.yaml` |
| `standards/schools/<x>/v1/template_generation_stages/0N_*.yaml` | T1/T2/T3/T4/T5 专用标准：`t1_document_facts.standard.yaml`、`t2_unit_pagination.standard.yaml`、`t3_element_policy.standard.yaml`、`t4_global_layout.standard.yaml`、`t5_template_spec.standard.yaml` |
| `standards/schools/<x>/v1/template_generation_final.yaml` | `standards/targets/<x>/v1/template_quality/final_template.expected.yaml` |
| `standards/schools/demo-school/v1/golden/*` 、 `exceptions.yaml` | `standards/targets/demo-school/v1/golden/*` 、 `exceptions.yaml` |
| `standards/eval_profiles/real-core-v0/expected/student_content_trees/real-student-00N.yaml` | 未来如需启用，再整理到 `standards/students/real-student-00N/v1/content_extract/student_content_artifact.expected.yaml`；当前不新增 |
| `standards/eval_profiles/real-core-v0/expected/render_plans/real_core_v0_<x>_real-student-00N.yaml` | 未来如需启用，再整理到 `standards/cases/<x>__real-student-00N/v1/placement/placement_plan.expected.yaml`；当前不新增 |
| `standards/eval_profiles/real-core-v0/expected/render_feature_snapshots/*.json` | 未来如需启用，再整理到 `standards/cases/<x>__real-student-00N/v1/render/feature_snapshot.expected.json`；当前不新增 |
| `standards/eval_profiles/bootstrap-core/expected/{feature_snapshot,placement_plan}.json` | 历史 bootstrap fixture；当前模板阶段不新增这类标准 |

### 5.3 组合：历史 `standards/eval_profiles/` → 当前顶层 `eval_profiles/`

| 历史路径 | 当前路径 |
| --- | --- |
| `standards/eval_profiles/<profile>/cases.yaml` | `eval_profiles/<profile>/profile.yaml`（只引用标准路径，不再存 expected 本体） |
| `standards/eval_profiles/<profile>/README.md` | `eval_profiles/<profile>/README.md` |

### 5.4 输出：历史 `test_outputs/` → 当前 `runs/`

| 历史路径 | 当前路径 |
| --- | --- |
| `test_outputs/debug/template_generation/**` | `runs/template_generation/<run_id>/**` |
| `test_outputs/debug/template_eval_runs/**` | `runs/eval/<run_id>/**` |
| `test_outputs/debug/{template_parsing,content_extraction,content_placement,docx_rendering}/**` | 折叠进 `runs/eval/<run_id>/artifacts/**` |
| `test_outputs/workbench/**` | `runs/workbench/**` |

---

## 6. 代码侧当前状态

`src/docfit/` 已按“模板侧 active + 后续阶段 reserved + harness 控制平面”收敛：

| 模块 | 当前身份 | 规则 |
| --- | --- | --- |
| `src/docfit/stages/template_parse/` | active | 当前模板解析业务入口 |
| `src/docfit/stages/content_extract/` | reserved | 学生内容提取流程未定义清楚前，不制作标准 |
| `src/docfit/stages/placement/` | reserved | 内容放置依赖学生内容产物，不制作标准 |
| `src/docfit/stages/render/` | reserved | 渲染依赖放置计划，不制作标准 |
| `src/docfit/template_generation/` | 模板侧支撑流程 | 生成 `fillable_template.docx` 和 T1-T6 调试产物，不是第五业务阶段 |
| `src/docfit/template_gap/` | 模板质量差距检查 | 读取被测模板和最终标准，输出 gap 报告 |
| `src/docfit/harness/` | 控制平面 | 加载标准、绑定运行产物、判 `PASS/FAIL/UNKNOWN` |
| `src/docfit/core/` | 跨切面基础设施 | `io` / `models` / `status` 等保留在这里 |

后续新增的模板生成标准裁判能力放在 `src/docfit/harness/`：

```text
template_generation_standard_judge.py
template_generation_standard_quality.py
template_generation_run_bundle.py
template_generation_stage_verifiers.py
template_generation_judge_reports.py
```

历史 plan 中如果仍提到把 `template_generate` 从 `stages/` 移出、把 `template_gap` 从 harness 抽出、或把通用合同从每校目录去重，均按“历史已处理事项”理解，不再作为当前目录规则。

---

## 7. 文档治理规则

| 文档 | 当前处理 |
| --- | --- |
| `docs/current/project-directory-structure.md` | 唯一维护正文 |
| `DIRECTORY_STRUCTURE.md` | 根目录短入口，只指向本文 |
| `docs/human/project-directory-structure.md` | 迁移指针，只指向本文 |
| `docs/human/**` | 人工 review、讨论材料、历史过程，可保留旧路径上下文 |
| `docs/plans/**` | 当时的计划和执行记录，可保留旧路径上下文 |
| 外部讨论稿 | 已并入本文；不再作为当前目录规则引用 |

原则：

```text
1. 结构约定只有本文一份正文。
2. 修改目录放置规则只改本文。
3. 其他文档可以链接本文，但不要新增目录判断表。
4. 历史文档中的旧路径不批量改写，避免破坏当时证据；读取时按 §5 翻译。
5. 新 plan / 新 docs / 新代码注释不得把旧路径写成默认入口。
```

---

## 8. 后续维护清单

当前目录结构已经按本文收敛。后续维护只做这几类事：

| 场景 | 怎么做 |
| --- | --- |
| 新增目录规则 | 先改本文，再改代码或其它文档引用 |
| 读旧文档里的旧路径 | 按 §5 翻译，不把旧路径复制到新文档 |
| 新增标准 | 放 `standards/targets`、`standards/students` 或 `standards/cases`，不要放 `eval_profiles/` |
| 新增学生/placement/render 标准 | 当前不要新增；先定义流程、产物和验收口径 |
| 新增运行证据 | 放 `runs/`，不要放 `standards/` 或 `inputs/` |
| 新增小型代码 fixture | 放 `tests/fixtures/`；业务级冻结输入放 `inputs/**/fixtures/` |
| 新增 profile | 放 `eval_profiles/<profile>/profile.yaml`，只组合 case 和 coverage gate |
| 新增模板生成标准裁判输出 | 放 `runs/eval/template_generation_judge/<target_id>/<source_run_id>/` |

如果确实要执行新的结构迁移，先写 `docs/plans/...`，再配套 `scripts/check_directory_policy.py` 或同等检查，避免重新出现多份目录规则。

---

## 9. 判定规则（不可变量，保留）

无论结构怎么迁，门禁规则不变：

| 情况 | 结果 |
| --- | --- |
| 缺输入 fixture / 缺原始证据或 hash | `UNKNOWN` |
| 缺 expected 标准 / 缺运行输出 | `UNKNOWN` |
| 缺 verifier 或 verifier 未启用 | `UNKNOWN` |
| 输出与 expected 不一致 | `FAIL` |
| 输出满足 expected 且 verifier 已启用 | `PASS` |

两条铁律：

- **`.expected.*` 只能由人工签收流程更新**，禁止为了刷绿评测从当前 actual 自动复制生成。
- **`runs/` 不能反向覆盖 `inputs/` 或 `standards/`**，除非经人工签收并显式冻结。

---

## 10. 命名速查

| 角色 | 规则 | 示例 |
| --- | --- | --- |
| target id | 小写 kebab-case | `pku-graduate` |
| student id | 小写 kebab-case（与仓库一致） | `real-student-001` |
| case id | `<target>__<student>`（双下划线） | `pku-graduate__real-student-001` |
| stage id | 阶段语义名；模板生成标准使用 T 编号 + snake_case | `t1_document_facts` |
| 原始输入 | 语义名，**不带** `.input` | `source_template.docx` |
| 冻结 fixture | `<artifact>.input.<ext>` | `document_facts.input.json` |
| 签收标准 | `<stage_or_artifact>.expected.<ext>` | `placement_plan.expected.yaml` |
| 通用合同 | `<domain>.contract.json` | `render.contract.json` |
| 标准入口 | `<domain>.standard.yaml` | `target.standard.yaml` / `case.standard.yaml` |
| manifest | `*_manifest.{yaml,json}` | `input_manifest.yaml` |
| 运行输出 | 生产产物原名，可带阶段序号，不带 `.expected` | `template_artifact.json` |
| 标准质量输出 | `template_generation_stage_standard_quality_report.{json,md}` | `template_generation_stage_standard_quality_report.json` |
| 标准裁判 run 绑定输出 | `template_generation_run_bundle.json` | `template_generation_run_bundle.json` |
| 标准裁判阶段输出 | `template_generation_stage_checks.json` | `template_generation_stage_checks.json` |
| 标准裁判聚合输出 | `template_generation_judge_report.{json,md}` | `template_generation_judge_report.md` |
| 标准裁判输出目录 | `runs/eval/template_generation_judge/<target_id>/<source_run_id>/` | `runs/eval/template_generation_judge/hunannongye/template_generate/` |

判文件角色只看后缀：`.input.*`=冻结输入；`.expected.*`=签收标准；`.contract.*`=通用合同；`.standard.yaml`=标准包入口；`*_manifest.*`=来源/hash/运行信息。**任何能删除重跑的东西都不该在 `standards/`。**
