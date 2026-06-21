# real-core-v0 生成模板差距 harness — 真实运行测试报告

日期：2026-06-17
运行机器：darwin / 本仓库 HEAD `ea4d85b`
方式：**本次为真实运行**（实际执行 pytest 与 `docfit eval`，读取真实产物），非静态推断。
所有数字均来自本次实跑，命令见文末附录。

## 摘要

管道本身**确实跑得通、且阻断正确**——62 个测试通过，三校差距检查都 FAIL，e2e 在
模板阶段阻断、coverage FAIL，计划自述的 `103/148/43` 被精确复现。

但「跑通且阻断」**不等于报告内容可信**。真实跑完后发现两个会直接影响结论可用性的问题：

1. **被测对象不是「代码生成的模板」，而是学校自己的原始要求/规范 Word**（满是
   `□□`、`×××`、字体批注）。当前根本没有生成模板这一步。
2. **元素匹配器是「仅压缩空格的子串匹配」，无法跨越批注/占位噪声**，导致大量
   `element_missing` 是**误报**——文档里明明有「目录 / 摘要 / 学生姓名」，却被判为缺失。

结论：**FAIL 数（hunannongye 148）严重高估了真实差距**，当前的差距报告还不能当作
「哪些元素真的缺了」的清单来读。

## 一、确实正常的部分（实跑验证）

| 项目 | 实跑结果 |
| --- | --- |
| `pytest tests/unit tests/contract tests/e2e -q` | **62 passed in 12.96s** |
| `template-gap` × 三校 | 三校 `status = FAIL`（均 `display_status = FAIL + UNKNOWN`，`blocking = FAIL`） |
| e2e（hunannongye / real-student-003） | `status = FAIL`，`blocked_at = template`，stage = `{content: UNKNOWN, placement: UNKNOWN, render: FAIL, template: FAIL}` |
| coverage（real-core-v0） | `status = FAIL` |
| 计数复现（hunannongye） | `passed/failed/unknown = 103 / 148 / 43` — 与计划自述完全一致 |

阻断语义如设计：real_core 在模板 FAIL 后**继续**产出 content/placement/render 诊断
产物，但 `blocked_at: template` 保留，没有被下游 PASS 稀释。这部分**没有问题**。

三校真实差距计数：

| 学校 | display | passed | failed | unknown | 被测文件 |
| --- | --- | --- | --- | --- | --- |
| hunannongye | FAIL + UNKNOWN | 103 | 148 | 43 | `test_inputs/template_generation/school-hunannongye-requirement.docx` |
| nannong-undergraduate | FAIL + UNKNOWN | 46 | 131 | 26 | `test_inputs/template_generation/school-nannong-undergraduate-template.docx` |
| pku-graduate | FAIL + UNKNOWN | 61 | 62 | 43 | `test_inputs/template_generation/school-pku-graduate-template.docx` |

各校 FAIL 的头号类型都是 `template_generation_element_missing`（121 / 98 / 22）。
下面就是问题所在。

## 二、真实运行暴露的问题（按影响排序）

### P1 — 被测对象根本不是「生成的模板」，而是学校原始规范 Word 🔴

`bundle.template_docx` 指向学校自己的输入文件：
- `src/docfit/harness/profiles.py:141` → `test_inputs/template_generation/school-hunannongye-requirement.docx`
- `standards/schools/hunannongye/v1/signed_standard.yaml:8` → 同一文件
- e2e 里 `evaluate_generated_template_gap(bundle, bundle.template_docx, out_dir)`
  （`orchestrator.py:330`）直接把它当被测「生成模板」。

而这个文件的真实内容（实跑解析出的段落）是**带批注的规范文本**，例如：

```
目□□录   (二号黑体，居中)
□□摘要……………………………………………………………………………1
□□□□□□学生姓名（三号黑体加粗）：×××（或×□×） （三号楷体加粗）
目录基本格式：1.5倍行距；上下页边距2.54厘米…“□” 表示占1个字宽的空格。
```

**后果**：当前 harness 实际测的是「学校规范 Word vs 从该规范编译出的 contract」，
是一种自洽性代理检查，**不是**「代码生成的模板 vs 学校标准」。计划 149-151 行其实
承认了这点（"本切片只是把生成模板 Word 作为被测输入"），但实跑后才看清：所有 148 条
FAIL 谈的都是这份带批注的规范文档，而不是任何生成产物。在有真正的
`generated_template.docx` 生成步骤之前，这些数字不能解读为「生成模板的质量」。

### P2 — 元素匹配器误报，`element_missing` 数被夸大 🔴

匹配逻辑（`generated_template_gap.py`）：

- `_find_matches`：`needle in entry_text`，只做子串匹配；
- `_normalize_text`：**只压缩空白**，不去除 `□`、`×`、`（…批注）`。

所以 contract 里规范化的 `"目 录"` 永远无法命中文档里的 `"目□□录 (二号黑体，居中)"`。
实跑确认以下元素**文档里明明有、却被判 `element_missing`**：

| 检查项 | contract 期望 | 文档实际（已解析到） |
| --- | --- | --- |
| `toc.e_001` | `目 录` | `目□□录 (二号黑体，居中)` |
| `abstract_cn.e_001` | `摘 要：` | `□□摘要……1` |
| `cover.e_005` | `学生姓名：；学号：；年级专业及班级：…` | `…学生姓名（三号黑体加粗）：×××`、`年级专业及班级`… |

定量（实跑统计，hunannongye 的 121 条 `element_missing`）：

| 类别 | 数量 | 含义 |
| --- | --- | --- |
| 完全没有搜索 needle（content 被判为「描述性」）→ **无论文档如何都自动 FAIL** | **37** | 见 P3 |
| content 的全部 token 都能在文档里找到 → **明显误报** | **17** | 元素其实存在 |
| 部分 token 能找到 | 25 | 模糊/部分匹配 |
| 没有 token 命中 | ~42 | 可能是真实缺失 |

也就是说 hunannongye 的 121 条 `element_missing` 里，**至少 ~54 条（37+17，约 45%）
不是可靠的「元素缺失」证据**。nannong 同口径约 33/98（约 34%）。pku 因为喂的是较干净
的真实模板 docx，几乎没有 no-needle、token 命中也极少（≈0），它的 22 条多为真实差距
——这反过来印证了问题集中在带批注的规范文档上。

### P3 — 「描述性」内容的元素会无条件判缺失 🟠

`_candidate_needles` 对 `_looks_like_descriptor(content)` 为真的元素**不产生任何
needle**；随后 `_find_matches` 必空，fixed/manual_only 策略直接落 `element_missing`
（`generated_template_gap.py:500-513`）。实跑统计：hunannongye 37 条、nannong 31 条
`element_missing` 属于这种「无 needle 自动失败」——它们与文档实际内容无关，是检查器
表达能力的边界，而非真实缺失。

### P4 — 因为全是 FAIL，无法区分「真差距」与「匹配噪声」🟠

这正好坐实了测试质量审查的担忧（见
`real-core-v0-generated-template-gap-test-quality-review.md`）：没有端到端 PASS 夹具、
没有隔离变异测试，于是当真实样本「整体就该 FAIL」时，**没有任何信号能告诉我们 148 条
FAIL 里哪些是检查器正确发现、哪些是匹配器误报**。本次真实运行把这个抽象担忧变成了
具体证据——误报已经实际发生且占比可观。

## 三、这意味着什么

- harness 的**管道与阻断是可信的**，可以继续作为 gate 骨架。
- 但 harness 当前的**核心用途（"发现生成模板和标准之间的差距"）尚未真正达成**：
  既没有生成模板可测（P1），匹配器又对带批注/占位的文本大量误报（P2/P3）。
- 现在把 `FAIL 148` 报给人看，会让 review 者把「匹配器看不懂的批注文本」误读成
  「生成模板缺了 148 个元素」，是误导性的。

## 四、建议（按性价比）

1. **先修匹配器的归一化**（最高性价比）：`_normalize_text` 去掉 `□`、`×`、半/全角
   括号批注与点引线后再做子串匹配；并允许按 contract 字段 token 分别命中。仅此一项
   就能消掉上面量化到的 ~37%–45% 误报。
2. **明确区分两类 FAIL**：把「无 needle 自动失败」单列为
   `template_generation_element_uncheckable`(UNKNOWN) 而非 FAIL——它本质是「检查器无法
   判定」，应进 UNKNOWN 而不是 FAIL，符合计划的状态语义。
3. **补端到端 PASS 夹具 + 三条隔离变异测试**（见测试质量审查第 1–3 项）。修完匹配器后，
   用一个干净夹具断言 `display_status == PASS`，否则 P2/P4 会再次悄悄回归。
4. **澄清 P1**：在产出真正的 `generated_template.docx` 生成步骤前，报告/文档应显式标注
   「被测对象=学校规范 Word（占位）」，避免把自洽性检查误读成生成质量结论。

## 附录：实跑命令与原始输出

```bash
uv run pytest tests/unit tests/contract tests/e2e -q
# 62 passed in 12.96s

uv run docfit eval template-gap --school hunannongye         --generated-template test_inputs/template_generation/school-hunannongye-requirement.docx        --out /tmp/gap_review_20260617/hunannongye   # FAIL
uv run docfit eval template-gap --school nannong-undergraduate --generated-template test_inputs/template_generation/school-nannong-undergraduate-template.docx --out /tmp/gap_review_20260617/nannong       # FAIL
uv run docfit eval template-gap --school pku-graduate         --generated-template test_inputs/template_generation/school-pku-graduate-template.docx         --out /tmp/gap_review_20260617/pku           # FAIL

uv run docfit eval e2e --school hunannongye --student test_inputs/content_extraction/real-student-003-source.docx --out /tmp/gap_review_20260617/e2e
# status = FAIL | blocked_at = template | {content:UNKNOWN, placement:UNKNOWN, render:FAIL, template:FAIL}

uv run docfit eval coverage --profile real-core-v0 --out /tmp/gap_review_20260617/coverage   # FAIL
```

误报量化脚本：对每条 `element_missing`，去除 `□/×/括号批注/标点/空白` 后，统计其
content token 在解析出的段落+表格单元格文本中的命中情况；并用
`generated_template_gap._candidate_needles` 重算 needle 是否为空。原始计数：

```
hunannongye  missing=121 | no-needle(auto-fail)=37  all-tokens-present=17  some=25  none=42(≈)
nannong      missing= 98 | no-needle(auto-fail)=31  all-tokens-present= 2  some=25  none=71(≈)
pku          missing= 22 | no-needle(auto-fail)= 0  all-tokens-present= 3  some= 0  none=19
```
