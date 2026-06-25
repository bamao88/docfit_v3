---
status: mitigated_by_disable
type: bug
owner: template-generation
stage: T2/T3
severity:
  - P1
created: 2026-06-25
last_updated: 2026-06-25
related_docs:
  - docs/plans/template-parse-refactor-t2-copy-only-policy-issue-01-default-freeze.md
  - docs/plans/template-parse-refactor-t2-copy-only-policy-issue-02-disable-copy-only.md
  - docs/plans/template-parse-refactor-t3-element-policy-issue-02-post-confidence-residuals.md
  - docs/plans/template-parse-refactor-t2-unit-recognition-issue-01-boundary-label.md
  - docs/plans/template-parse-refactor-t2-unit-recognition-issue-02-post-phase2-residuals.md
  - docs/plans/template-parse-refactor-stage-issues.md
related_code:
  - src/docfit/template_generation/constants.py
  - src/docfit/template_generation/structure_candidates.py
  - src/docfit/template_generation/generation_model.py
---

# BUG：copy-only 策略写死，且“未识别单元默认 copy-only”方向是反的

Last updated: 2026-06-25

一句话：copy-only 原本是**写死的 unit_id 黑名单**——“除了 5 个已知单元，其它一律 copy-only”。它有两个问题：(1) **不可按学校扩展**，学校特有的必填表单没有进入 copy-only 的正路；(2) **默认方向反了**——T2 没认出来的 `other` / `custom` 单元被默认当成 copy-only（“不认识就原样冻结”）。

2026-06-25 更新：默认方向先在 [T2-COPY-ONLY-ISSUE-01](template-parse-refactor-t2-copy-only-policy-issue-01-default-freeze.md) 中改为正向白名单，随后在 [T2-COPY-ONLY-ISSUE-02](template-parse-refactor-t2-copy-only-policy-issue-02-disable-copy-only.md) 中默认关闭 copy-only。当前 `COPY_ONLY_DEFAULT_UNIT_IDS` 为空，默认不再产生 `whole_unit_copy`。仍未解决的是 school/config/request 级 copy-only 扩展入口，以及未来若恢复 copy-only 时的内部开洞策略。

---

## 1. 原始实现（已替换的写死黑名单）

```python
# constants.py:5  —— 模块级 frozenset，无任何 school/config/request 覆盖入口
COPY_ONLY_DEFAULT_EXCLUDED_UNIT_IDS = {
    "abstract_cn", "abstract_en", "toc", "body_main", "references",
}

# structure_candidates.py:989  —— 黑名单语义：不在排除集里 = copy-only
def _unit_is_copy_only_by_default(unit_id):
    return bool(unit_id) and unit_id not in COPY_ONLY_DEFAULT_EXCLUDED_UNIT_IDS
```

含义：**“copy-only = 标签不是这 5 个已知‘活’单元的，全都是。”**

这个判断同时被 T2 候选（`structure_candidates.py:185`，决定单元是否走 `_copy_only_unit_elements`）和 generation_model（`generation_model.py:262 _unit_generation_mode` → `whole_unit_copy` → `_final_policy_for_generation` 把内部 fill/generated 压成 fixed）使用。

现状：代码已改成 `COPY_ONLY_DEFAULT_UNIT_IDS`，且当前集合为空；仍然**没有 school / config / request 级别的覆盖路径**。

---

## 2. 为什么这是 bug

### 2.1 不可按学校扩展

学校特有的 copy-only 内容（例如湖南农大的后置必填表单：任务书、开题报告、答辩记录表、成绩评定表）**没有进入 copy-only 的正路**。现在它们能不能被当成 copy-only，完全取决于 T2 能不能把它们贴上某个标签，再看那个标签碰巧是否落在“非排除集”里：

- 标成 `post_forms` → 不在排除集 → 恰好 copy-only（但这是“碰巧”，不是“因为它是 copy-only 才这样判”）。
- 标不上、落成 `other` → 也不在排除集 → 也 copy-only（见 2.2，这是反向默认在兜底）。

也就是说，现在“学校特有表单是 copy-only”这件事是**靠黑名单兜底碰对的**，不是按学校事实判定的。换一个学校、换一种表单标题，没有任何配置能表达“这个学校的这部分是 copy-only”。

### 2.2 默认方向反了：未识别单元 = copy-only

`other` 是 T2 **没认出来**的单元。当前它默认 copy-only，等于把“我不知道这是什么”当成“一定可以原样冻结”。这是反的：未识别恰恰是最不该擅自冻结内部填写位/生成域的情况。

实测证据（pku 工作树）：T2 过切产生了 60+ 个 `unit_id="other"` 单元（单字母 A–H、表格单元格、`Stage 1 (>7.1 μm)` 重复等），全部 `copy_only=True`。其中混入的 fill/generated 候选被 `whole_unit_copy` 压成 fixed。

> 说明：本轮三校里，这些 `other` 冻到的**主要是 Word 使用说明文字**（被 `GENERATED_MARKERS` 误判成 generated 的假阳性），所以净危害暂时有限。但机制是错的：一旦某学校真有填写位/真目录落进 `other`，会被无声冻结，且 verifier 没有针对降级的 finding（见 t3-element-policy-issue T3-ISSUE-002）。

### 2.3 与 `_unit_policy` 两套并行标签表，口径不一致

```python
def _unit_policy(unit_id):
    if unit_id in {body_main, abstract_cn, abstract_en}: return "fill"
    if unit_id in {toc}: return "generated"
    return "fixed"
```

`_unit_policy`（fill/generated/fixed）和 `COPY_ONLY_DEFAULT_EXCLUDED_UNIT_IDS`（copy-only 与否）是两张**各自写死、口径不完全一致**的标签表（例如 `references` 在排除集里=非 copy-only，但 `_unit_policy` 给它判 `fixed`）。copy-only 该不该成立，缺少单一事实来源。

---

## 3. 期望设计（基线 + 按学校扩展，其余不默认 copy-only）

把“黑名单 + unknown 默认 copy-only”改成“**白名单基线 + 学校扩展 + 默认非 copy-only**”：

1. **copy-only 基线（默认）**：明确列出默认 copy-only 的单元类型，例如封面 `cover`、原创性声明 `integrity_statement`、致谢 `acknowledgement` 等“整单元保形、学生手填”的部分。这部分是产品已确认保留的（学生手填工作量不大，且自动适配反而易错）。
2. **按学校扩展**：允许某学校声明额外 copy-only 单元（如湖南农大的后置必填表单 `post_forms`/任务书/答辩记录表/成绩评定表）。来源可以是学校 profile / request 参数 / 学校 gold，不是改全局常量。
3. **默认非 copy-only**：未在基线或学校扩展中被正向判定为 copy-only 的单元（尤其是 `other` 未识别单元），**默认 `copy_then_patch`**，让内部 fill/generated 能保留；判不准时交由 T3 分类 + 审核，而不是擅自整单元冻结。

要点：copy-only 应该是**正向判定（这是一个保形表单）**，不是**反向兜底（不在已知活单元里就冻）**。

---

## 4. 环节定位

| 步骤 | 位置 | 现状 | 改动方向 |
| --- | --- | --- | --- |
| copy-only 定义 | `constants.py:5` + `structure_candidates.py:989` | 当前正向集合为空 | 后续若恢复，先补学校扩展入口 |
| 应用（T2 候选） | `structure_candidates.py:185` | 默认不再命中 `_copy_only_unit_elements` | 后续接 school/request 配置后再启用 |
| 应用（生成） | `generation_model.py:262 / 141` | 默认不再产生 `whole_unit_copy` | copy-only 内部开洞另议 |
| 学校扩展入口 | 无 | 不存在 | 新增（profile / request / gold） |

---

## 5. 待讨论

1. copy-only 基线集应包含哪些单元？`cover` / `integrity_statement` 已确认；`acknowledgement` / `appendix` 算不算？
2. 学校扩展从哪来：学校 profile 配置、request 参数、还是从该校 gold 派生？
3. `other`（未识别）默认改成 `copy_then_patch` 后，内部 fill/generated 是否要先压低置信度 / 进审核，避免 T3 假阳性（如 `GENERATED_MARKERS` 宽匹配）被直接放出来？
4. 是否顺便把 `_unit_policy` 和 copy-only 两张标签表合并成单一“单元策略事实”来源？

---

## 6. 关联

- 本 bug 是 t3-element-policy-issue **T3-ISSUE-002（fill/generated 被静默降级成 fixed）** 的根因层。
- `other` 泛滥来自 t2-boundary-label-issue 的过切问题；两者叠加放大本 bug 的影响面。
