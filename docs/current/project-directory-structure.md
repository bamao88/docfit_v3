# DocFit v3 项目结构总纲（顶层单一事实来源）

> Status: 顶层裁定版 / Single Source of Truth
> 本文合并了两份讨论稿（`DIRECTORY_STRUCTURE_architecture.md` 架构稿、`README_optimized.md` 命名规范稿），并已对齐当前仓库实际状态（`bamao88/docfit_v3@main`）。
> 落位建议：放到 `docs/current/project-directory-structure.md`，替换旧版；根目录 `DIRECTORY_STRUCTURE.md` 只保留一句话短入口指向本文。

---

## 0. 这份文档要解决的"乱"

当前仓库的混乱不在于代码，而在于**结构约定有多份、且互相打架**：

1. 仓库里同时存在三份目录结构文档：根 `DIRECTORY_STRUCTURE.md`（短入口）、`docs/current/project-directory-structure.md`（旧权威，仍写 `test_inputs/` / `test_outputs/`）、`docs/human/project-directory-structure.md`（已标记迁移）。
2. 刚讨论完的两份稿（架构稿、命名稿）描述的是**新结构**（`inputs/` / `runs/` / `standards/targets/` / 顶层 `eval_profiles/`），与旧权威文档直接冲突。
3. 两份新稿**彼此之间**也有约 7 处口径不一致（合同命名、版本层、`runs/` 子目录、学生 id、raw 是否带 `.input` 等，见 §4）。
4. 仓库实物里有两处"反例"：通用合同被复制进每个学校目录；`template_generate` 被放进了业务阶段 `stages/`。

本文是顶层裁定：**确立一套结构、逐条裁掉冲突、给出迁移映射**。其余结构文档一律降级为参考或退役（见 §7）。

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

核心边界：业务永远只有四个阶段——**模板解析、内容提取、内容放置、DOCX 渲染**。`template_generation` 和 `template_gap` 是模板侧支撑流程，**不是第五个业务阶段**。

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
│   ├── core/                       # 跨切面：io / models / status
│   ├── contracts/                  # 契约 schema 与 verifier 基类（不放具体学校标准）
│   ├── stages/                     # ✅ 只放四个业务阶段
│   │   ├── template_parse/
│   │   ├── content_extract/
│   │   ├── placement/
│   │   └── render/
│   ├── template_generation/        # 模板侧支撑流程（非业务阶段）
│   ├── template_gap/               # 模板质量差距检查（非业务阶段）
│   ├── template_model/             # 模板结构共享模型，不做门禁裁判
│   ├── convert/                    # 产品转换编排，只串联已验证四阶段
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
│   └── students/<student_id>/
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
│   │   ├── template_generation/<NN_stage>.expected.yaml
│   │   ├── template_quality/final_template.expected.yaml
│   │   ├── golden/
│   │   └── exceptions.yaml
│   ├── students/<student_id>/<version>/
│   │   ├── student.standard.yaml
│   │   └── content_extract/student_content_artifact.expected.yaml
│   └── cases/<target_id>__<student_id>/<version>/
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

## 4. 两份讨论稿口径裁决 ⭐

两份新稿在以下 9 点不一致。裁定原则：**① 与仓库实际资产一致；② 命名后缀体系自洽（`.input` / `.expected` / `.contract` / `.standard`）；③ 不丢能力**。每条都可由你推翻。

| # | 争议点 | 架构稿 | 命名稿 | ✅ 裁定 | 理由 |
| --- | --- | --- | --- | --- | --- |
| 1 | 通用合同目录 | `standards/shared_contracts/` | `standards/contracts/` | **`standards/contracts/`** | 更短；且仓库现在把合同**重复复制进每个学校**（反例），必须收敛成一份 |
| 2 | 合同文件名 | `template_contract.json`（前缀） | `template.contract.json`（后缀） | **`*.contract.json`（后缀）** | 与 `.expected.*` / `.standard.yaml` 后缀体系一致；按后缀即可判文件角色 |
| 3 | target 是否带版本层 | 带 `<version>/` | 不带 | **带 `<version>/`** | 仓库现在已经是 `schools/<x>/v1/`；重新签收旧标准需要并存版本 |
| 4 | 学生 id 格式 | `real-student-001` | `real-001` | **`real-student-001`** | 仓库实际就是 `real-student-001`，改短反而要动一批文件名 |
| 5 | raw 原始文件是否带 `.input` | 带（`source_template.input.docx`） | 不带 | **不带** | `.input` 只标记"冻结给下游读的 fixture"；原始证据不是 fixture |
| 6 | 标准入口名 | `case_standard.yaml`（下划线） | `case.standard.yaml`（点） | **`*.standard.yaml`（后缀）** | 同 #2，后缀体系自洽 |
| 7 | `runs/` 子目录 | `eval/` + `convert/` + `template_generation/` + `workbench/` | `template_generation/` + `conversion/` + `reports/` | **`template_generation/` + `eval/` + `convert/` + `workbench/`** | 与 CLI 动词（`docfit eval` / `docfit convert`）对齐；`reports/` 实为 eval 输出的子集 |
| 8 | src 模块视图 | 给出完整模块树 | 未展开 | **采用架构稿，并按 §6 对齐现状** | 架构稿更完整 |
| 9 | 业务阶段边界 | 四阶段 + 支撑模块分离 | 同 | **四阶段固定**；`template_generation`/`template_gap` 为支撑模块 | 两稿一致，作为不可动摇约束 |

---

## 5. 现状 → 目标 迁移映射 ⭐

下表路径均来自当前仓库实物（已核对）。

### 5.1 输入：`test_inputs/` → `inputs/`

| 当前 | 目标 |
| --- | --- |
| `test_inputs/template_generation/school-<x>-template.docx` | `inputs/targets/<x>/raw/source_template.docx` |
| `test_inputs/template_generation/school-<x>-template-review.txt` | `inputs/targets/<x>/raw/source_review.md` |
| `test_inputs/template_generation/school-hunannongye-requirement*.{doc,docx}` | `inputs/targets/hunannongye/raw/`（额外格式要求源） |
| `test_inputs/content_extraction/real-student-00N-source.docx` | `inputs/students/real-student-00N/raw/source_document.docx` |
| `test_inputs/content_extraction/real-student-00N-content-review.md` | `inputs/students/real-student-00N/raw/content_review.md` |
| `test_inputs/content_extraction/bootstrap-demo-student-*.docx` | `inputs/students/bootstrap-demo-*/raw/source_document.docx` |
| `test_inputs/template_gap/real-core-v0-<x>-generated-template.docx` | `inputs/targets/<x>/fixtures/template_gap/generated_template.input.docx`（被测 = 冻结 fixture） |
| `test_inputs/template_generation/unit_copy_test_0N.docx` | bootstrap/单测夹具 → `tests/fixtures/` 或 `inputs/targets/.../fixtures/` |

### 5.2 标准：`standards/schools/` + `standards/eval_profiles/.../expected/` → `standards/{contracts,targets,students,cases}/`

| 当前 | 目标 |
| --- | --- |
| `standards/schools/<x>/v1/{template,student_content,placement,render}_contract.json`（**每校重复**） | 去重后只留一份 → `standards/contracts/*.contract.json` |
| `standards/schools/<x>/v1/signed_standard.yaml` | `standards/targets/<x>/v1/target.standard.yaml` |
| `standards/schools/<x>/v1/template_generation_stages/0N_*.yaml` | `standards/targets/<x>/v1/template_generation/*.expected.yaml`；T2 单元/分页标准为 `template_generation/t2_unit_pagination.standard.yaml` |
| `standards/schools/<x>/v1/template_generation_final.yaml` | `standards/targets/<x>/v1/template_quality/final_template.expected.yaml` |
| `standards/schools/demo-school/v1/golden/*` 、 `exceptions.yaml` | `standards/targets/demo-school/v1/golden/*` 、 `exceptions.yaml` |
| `standards/eval_profiles/real-core-v0/expected/student_content_trees/real-student-00N.yaml` | `standards/students/real-student-00N/v1/content_extract/student_content_artifact.expected.yaml` |
| `standards/eval_profiles/real-core-v0/expected/render_plans/real_core_v0_<x>_real-student-00N.yaml` | `standards/cases/<x>__real-student-00N/v1/placement/placement_plan.expected.yaml` |
| `standards/eval_profiles/real-core-v0/expected/render_feature_snapshots/*.json` | `standards/cases/<x>__real-student-00N/v1/render/feature_snapshot.expected.json` |
| `standards/eval_profiles/bootstrap-core/expected/{feature_snapshot,placement_plan}.json` | `standards/cases/demo-school__bootstrap-demo/v1/render|placement/*.expected.*` |

### 5.3 组合：`standards/eval_profiles/` → 顶层 `eval_profiles/`

| 当前 | 目标 |
| --- | --- |
| `standards/eval_profiles/<profile>/cases.yaml` | `eval_profiles/<profile>/profile.yaml`（只引用标准路径，不再存 expected 本体） |
| `standards/eval_profiles/<profile>/README.md` | `eval_profiles/<profile>/README.md` |

### 5.4 输出：`test_outputs/` → `runs/`

| 当前 | 目标 |
| --- | --- |
| `test_outputs/debug/template_generation/**` | `runs/template_generation/<run_id>/**` |
| `test_outputs/debug/template_eval_runs/**` | `runs/eval/<run_id>/**` |
| `test_outputs/debug/{template_parsing,content_extraction,content_placement,docx_rendering}/**` | 折叠进 `runs/eval/<run_id>/artifacts/**` |
| `test_outputs/workbench/**` | `runs/workbench/**` |

---

## 6. 代码侧需要跟着改的点

结构迁移之外，`src/docfit/` 有三处与"四阶段 + 支撑模块"模型不符，建议一并收敛（均有对应 plan 文档）：

1. **`template_generate` 当前在 `stages/` 里** → 移到 `src/docfit/template_generation/`。它是模板侧支撑流程，不是第五业务阶段。（参考 `docs/plans/template-generate-runner-split.md`）
2. **`template_gap` 当前只是 `harness/generated_template_gap.py` 一个文件** → 抽成独立 `src/docfit/template_gap/`（runner / verifier / report）。（参考 `docs/plans/template-gap-engine-layering-refactor.md`）
3. **通用合同被复制进每个学校目录** → 见 §5.2，收敛到 `standards/contracts/` 一份，各 target 用引用而非复制。

`src/docfit/core/`（io / models / status）保留——它是跨切面基础设施，不必并入 utils。

---

## 7. 需要退役 / 降级的旧文档

| 文档 | 处理 |
| --- | --- |
| `docs/current/project-directory-structure.md`（旧权威，写 `test_inputs/`/`test_outputs/`） | **用本文替换** |
| `docs/human/project-directory-structure.md` | 已是迁移指针，保持 |
| 上传的 `DIRECTORY_STRUCTURE_architecture.md` | 已并入本文，降级为参考；§4 已记录其被覆盖的条目 |
| 上传的 `README_optimized.md` | 已并入本文，降级为参考；详细逐阶段三件套与字段表可保留为附录引用 |
| 根 `DIRECTORY_STRUCTURE.md` | 保留为短入口，正文指针指向本文 |

原则：**结构约定只有本文一份正文**。改放置规则只改本文，其余文件不再新增目录判断表。

---

## 8. 落地顺序

1. 建新目录空壳：`inputs/`、`standards/contracts/`、`standards/{targets,students,cases}/`、顶层 `eval_profiles/`、`runs/{template_generation,eval,convert,workbench}/`。
2. 迁原始输入：`test_inputs/` → `inputs/**/raw/`，并补 `input_manifest.yaml`（含 sha256）。
3. 去重通用合同：各校重复合同抽到 `standards/contracts/*.contract.json`。
4. 收敛 target 标准：`standards/schools/<x>/v1/` → `standards/targets/<x>/v1/`。
5. 迁 student / case expected：从 `standards/eval_profiles/**/expected/` 迁到 `standards/students/` 与 `standards/cases/`。
6. 瘦身 profile：`eval_profiles/<p>/profile.yaml` 只引用标准路径，不再保存 expected 本体。
7. 最后迁运行输出：`test_outputs/debug/` → `runs/`。
8. 兼容期：CLI 可临时双路径支持，报告中把旧路径标记为 legacy；新文档/新标准/新 fixture 只写目标路径。

每步可配一个 `scripts/migrate_*.py` + `scripts/check_directory_policy.py` 做校验。

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
| stage id | 两位序号 + snake_case | `01_source_parse` |
| 原始输入 | 语义名，**不带** `.input` | `source_template.docx` |
| 冻结 fixture | `<artifact>.input.<ext>` | `source_template_tree.input.json` |
| 签收标准 | `<stage_or_artifact>.expected.<ext>` | `placement_plan.expected.yaml` |
| 通用合同 | `<domain>.contract.json` | `render.contract.json` |
| 标准入口 | `<domain>.standard.yaml` | `target.standard.yaml` / `case.standard.yaml` |
| manifest | `*_manifest.{yaml,json}` | `input_manifest.yaml` |
| 运行输出 | 生产产物原名，可带阶段序号，不带 `.expected` | `template_artifact.json` |

判文件角色只看后缀：`.input.*`=冻结输入；`.expected.*`=签收标准；`.contract.*`=通用合同；`.standard.yaml`=标准包入口；`*_manifest.*`=来源/hash/运行信息。**任何能删除重跑的东西都不该在 `standards/`。**
