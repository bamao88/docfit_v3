# T2 单元切分（unit_map）：职责、问题与优化

Last updated: 2026-06-25

一句话结论：T2 负责读 T1 的原子事实，做"**这一段是不是单元边界、属于哪个单元**"的合成决策。当前 T2 的根本毛病是**逐行扫关键词、不用多信号**——于是关键词在目录条目里撞车，真实章节被错切、被吞进 catch-all；外加置信度全是硬编码 `medium`，把一切都推成 `UNKNOWN` 还没信息量。优化方向是改成"**否决项 + 多信号加权 + 阈值**"的边界检测器，关键词降级为只贴标签。

> 状态标注：**【已验证】**＝三校 `template-generate` 复现确认；**【设计】**＝待实现。

---

## 0. 职责与边界（先读）

**T2 是什么**：在 T1 的事实流上**找单元边界、切单元、贴 `unit_id` 标签、定分节/分页归属**。产物 `unit_map.units[]` 只用 `source_range` 引用 T1 的段/run，**不含内容/样式**（是索引，不是拷贝）。

**核心原则**：
- **关键词词表只做"贴标签"，不做"切边界"**。边界由结构/样式/文字属性等多信号共同决定。
- `page_start` / `section_profile` 由 `sectPr` / `pageBreakBefore` / 页码格式按**固定规则**算，**不算语义判断**。
- **run 级样式/内容 T2 不看**（那是 T3）。T2 只看段落级信号。

**责任边界（依赖上游、不越权下游）**：
- T2 **依赖 T1 产出的原子判据**：`is_toc_entry` / `is_spacing_line` / `looks_like_instruction_text` / `centered`·`bold`·`large_font`·`short_text` / 样式名 / `breaks`。这些是 **T1 职责**，T2 不重新解析 docx。
- ⬅️ **"是不是标题/边界"的合成判断属于 T2**：这正是过去错放在 T1 的 `likely_unit_heading` 应该**归位到这里**的部分（见 T1 文档 §0、§2.3）。
- run 级再切分（标题 vs 行内说明、标签 vs 填空）= **T3**，不在 T2。

---

## 1. 现状问题（均为三校复现实测）

### 1.1 逐行扫关键词、不用多信号（核心缺陷）【已验证】
**根因**：`_infer_units()` / `_unit_for_text()`（`structure_candidates.py`）只用章节词表（摘要/前言/参考文献/致谢）匹配段落文本，**不看分节、不看标题样式、不看文字属性**。

**症状（目录撞车）**——关键词在目录条目里命中，把目录切成了假章节：
- `abstract_cn` → 指向目录行 `□□摘要……1`（这是目录条目，不是摘要正文）
- `body_main` → 指向 `□□1前言……1`、`□□2一级标题……2`（全是目录条目）
- `references` → 指向 `□□参考文献……9` + 第二套目录"（文科类专业用）"
- `toc` 单元被**截断成 5 行**（只剩标题 + 格式说明 + "（农理工科类专业用）"）
- 真正的正文/摘要/参考文献（p81 之后）被吞进 `abstract_en`（横跨 33 段）和 `post_forms`（**catch-all，吞掉全部 9 个表、217 个 ref**）

**为什么多信号能解决**：目录条目有明确的反向特征——点引线/`toc N` 样式/TAB+页码（T1 已产出 `is_toc_entry`）；真实标题有正向特征——分节/标题样式/居中+大字+短。逐行扫词把这两类信号全丢了。三校信号可用性差异大（湖南无标题样式靠文字属性、南农靠 `Heading`/`toc` 样式名、北大混合），所以必须**组合**多信号，不能绑死一种。

### 1.2 置信度硬编码 `medium`【已验证】
`structure_candidates.py:148`、`:525` 把单元/元素置信度写死成 `"medium"` → 每个单元都带 `needs_review` flag → T2 整体 `UNKNOWN`。这个信号是常量、**不携带任何信息**，既挡不住真错误，又把正确单元也一并标成待审。

### 1.3 变体未识别（本轮按方案 C 处理）
湖南模板含两套并存：目录"农理工科版/文科版"、正文"农理工科用/文法经管用"（源文明写"（农、理工科类专业用）""（以下文法经管类用）"）。当前会把第二套吞进相邻单元。
**已定方案 C**：维护者后续会**手工删源模板里另一套**，因此 T2 不做变体建模；本轮只需保证变体块被归入 `other` + flag、不污染其它单元边界即可。

---

## 2. 优化建议（T2 自己的）

> **本节定位**：规划层 + **大概实现示意（伪代码为主）**，**尚未落地执行**——真正代码留到实施时再写。
>
> **是一件事，不是两件**：核心交付物是 **§2.1 的边界检测器**（它决定识别准不准）。§2.2 的 abstain（`open_question` / `t2_input.json`）**不是独立交付物、也不是可替代选项**，而是同一次打分的**副产物**——分数高=确信边界，分数中/低=顺手记成 `open_question`。所以**不存在"先单独做 abstain"这种做法**（脱离新检测器，只能给旧的瞎撞逻辑加注脚，没意义）；两者一起做、以检测器为主。

### 2.1 多信号边界检测器（替换逐行扫词）【设计】
按文档顺序遍历**可见段落**，对每段：

1. **否决（绝对，一票否决，不参与加权）**：`is_toc_entry` 或 `is_spacing_line` 或 `looks_like_instruction_text` 为真 → **不是边界**，归属上一单元。
2. **正向信号加权**（命中累加，证据写 `evidence`）：

| 信号 | 判据（取自 T1 事实） | 建议权重 |
| --- | --- | --- |
| 前置分节/分页 | 该段前有新 `sectPr` / `page_break_before` / `breaks` 落点 | 3（强） |
| 标题样式 | 样式名 ∈ {`Heading N`, `标题N`} 或每校映射的标题样式 | 3（强） |
| 文字属性像标题 | `centered AND (large_font OR bold)`（`short_text` 作加分/置信，不作硬条件） | 2（中） |
| 章节词表命中 | 文本（剥离尾部行内格式说明后）匹配词表 | 1（弱，仅佐证） |

3. **阈值 `score >= 2` 判为单元起点**：
   - 关键词单独（1）**不足以**成边界 → 即便否决漏网，也再挡一层目录撞车。
   - 文字属性单独（2）可成边界 → 覆盖湖南这种无样式无分节、靠"居中+大字/加粗"的标题（如"诚 信 声 明"）。
   - 标题样式或分节单独（3）可成边界 → 覆盖南农/北大。
4. **边界 → 单元**：相邻两边界之间为一个单元，`source_range` 记 `{start_para, end_para}`；整单元落在表格容器内（南农封面=1×1 表格）记 `{container: table#k}`。

> 实现细节：判"文字属性像标题 / 词表命中"前，先把尾部 `（…字体/字号/居中…）` 行内说明剥掉再判（如"目□□录（二号黑体，居中）"），否则 `short_text`/词表被尾注干扰。**剥离只用于判定，不改原文**（原文剥离是 T3 的活）。

**大概实现示意（伪代码，非最终实现）**——只为说明"检测与 abstain 同源、一次遍历落出"：

```python
def segment_units(facts):                          # 段落级，不看 run 级（那是 T3）
    boundaries, open_questions = [], []
    for p in visible_paragraphs(facts):
        # 1) 否决：目录条目 / 空行说明 / 格式说明 → 一票否决，绝不当章节开头
        if p.is_toc_entry or p.is_spacing_line or p.looks_like_instruction_text:
            continue                               # 归属上一单元
        # 2) 多信号加权
        score, hits = 0, []
        if preceded_by_break(p):                    score += 3; hits += ["break"]
        if heading_style(p):                        score += 3; hits += ["style"]
        if centered(p) and (large_font(p) or bold(p)):
                                                    score += 2; hits += ["textprop"]
        if keyword_section(strip_inline_note(p.text)):
                                                    score += 1; hits += ["keyword"]
        # 3) 阈值 + abstain：在同一处落出，不是另一个步骤
        if score >= 2:
            conf = "high" if strong_agree(hits) else "medium"
            boundaries.append((p, conf, hits))
            if conf != "high":                      # 中间带 → 顺手记一条 abstain
                open_questions.append(OQ("boundary", interval=around(p), signals=hits))

    units = spans_between(boundaries)               # → source_range / container(表格)
    label_units(units, open_questions)              # 词表+标题→unit_id；不中→other + OQ("label")
    check_required(units, open_questions)           # 必需单元缺失 → OQ("required_missing")
    if open_questions:                              # 有疑点才产投影
        emit("t2_input.json", projection(facts, open_questions))
    return units, open_questions
```

> 看这段就清楚：`boundaries`（识别结果）和 `open_questions`（abstain 反馈）来自**同一个循环、同一个 `score`**——abstain 只是多写的几行，不是另起的步骤。权重/阈值都是初值，待有 `unit_map.expected` 后再调。

### 2.2 兜底与 AI 入口：abstain 契约 + `t2_input.json` 投影【设计】

**（承上）abstain 就是 §2.1 打分里 `score` 落在中间带、或 required 缺失时记下的东西**，不是独立步骤；本节只把这份反馈的**形态 / 契约**写清楚。

确定性边界检测必然有信号不足、分不出来的学校。这里不是"失败就 dump 一坨反馈"，而是**让兜底从打分里自然落出**：每个非高置信判定都带 typed `open_question`，并预留**模态无关**的 AI 入口（以后可接视觉）。这块 AI 现在不实现，但入口和反馈产物现在就做（确定性、可测）。

**失败形态分四类**——给 AI 的"问题/上下文"不同，所以不能合成一种反馈：

| 形态 | 现象 | AI 任务 |
| --- | --- | --- |
| ① 找到边界、贴不上标签 | `unit_id=other` | 闭集**分类**（给这块在闭集里选 unit_id） |
| ② 漏切 / 信号不足 | 真章节开头分数没过阈值、被并进上一单元 | **边界判定**（这段区间里有没有边界、在哪）——你担心的就是这类 |
| ③ 必需单元缺失 | 某 required 单元一个边界都没检到 | **判定**：真没有 vs 漏识别 |
| ④ 多切（spurious） | 一般被否决项挡住，少见 | 边界确认 |

**abstain 分数带**（驱动它的是硬信号一致性，不是 LLM 自报 confidence）：
- 强信号（分节/标题样式，或 `score>=3`）→ 确信边界，`confidence=high`，不打扰。
- 中间带（`score==2` / 仅文字属性）→ **暂定边界 + `open_question`**，待 AI/人确认。
- 低于带 → 非边界；但若导致某 required 单元缺失 → 对**可能区间**发一个 `open_question`（形态③）。

**一物两用、AI 开没开都产出**：只要有 `open_question`，确定性阶段就产出一份投影 `t2_input.json`（沿用规范命名）。
- **AI 关**：它就是"反馈 / 诊断"产物，同时是人工审核队列的输入。
- **AI 开**：它是模型输入；AI 回 `t2_ai_response.json`；再有合并步把结果并回 `unit_map`。
- 价值：同一份投影让"**模型判错 vs 投影漏喂了信号**"能分开排查（这正是规范给投影、而不是直接丢整篇 facts 的理由）。

**投影里给 AI 的上下文**（只给可疑区间 + 框架，不给整篇 facts）：
- **可疑区间的若干段**：`text` + 样式名 + `centered/bold/large_font/short_text` + `is_toc_entry/is_spacing_line` + 前置分节/分页 + 确定性**分数与命中/否决了哪些信号** + 提议器初判；
- **框架**：required 单元清单、已确信放好的有哪些、现在还缺哪些（让 AI 知道它在找什么）；
- **一个具体问题**：`p_k` 与 `p_{k+1}` 之间有没有边界？/ 这块是哪个 `unit_id`？/ 摘要是真缺还是漏识别？
- **可选 `visual_refs`（页面截图引用），现在留空**——模态无关，以后能接视觉。注意：T2 边界/标签判定文本+样式通常就够且便宜；视觉性价比更高在 **T6 版面验证**（且 LibreOffice≈Word 只是近似），所以现在不为 T2 建渲染，但不把缝设计成排斥视觉。

**合并 / 越权规则**（rules → AI → 人工三级，照规范 §3.2）：
- 每级可向下弃权（abstain）；
- AI **只能**在闭集里选 `unit_id` 或确认/微调边界，**不能造内容、不能覆盖确信项**；
- AI ↔ 规则在确信项上冲突 → 进人工，不自动采纳；
- AI 步锁模型版本、`temperature=0`、输入输出快照落盘（§3.4）。

**字段**：复用 `unit_map` 已有的 `open_questions[]`（现为空），每条 `{question_id, kind: label|boundary|required_missing, interval: {start_source_ref, end_source_ref}, candidates?, signals_summary, status: UNKNOWN}`；`t2_input.json` 为独立产物。

**本轮可落地（确定性、不依赖 AI）**：实现 T2 时顺手把 abstain 那一侧做出来——产 `open_questions` + `t2_input.json`，**空跑也有分级反馈**；AI 与视觉以后接入，不改这份投影的形状。

### 2.3 贴标签 + 真实 confidence【设计】
- **贴标签**：对已确定的单元，用词表 + 标题文本映射到闭集 `unit_id`；映射不中 → `unit_id = other` + `flags`（后续交 AI/人工）。
- **confidence（替换硬编码）**：按信号一致性算，不依赖 LLM 自报置信——
  - `high`：≥2 个独立强信号一致（分节+标题样式、或 标题样式+词表）。
  - `medium`：仅文字属性信号成立。
  - `low` + `flags`：仅词表命中（且邻近 TOC/说明可疑）或信号冲突（词表说 references 但样式是 `toc 2`）。

### 2.4 `page_start` / `section_profile` 走固定规则【设计】
由 `sectPr` / `page_break_before` / 页码格式映射算出，不进语义判断。湖南这种 0 分节的，`page_start` 默认 `continue` + flag（显式分页体例属 T4/每校配置，T6 不臆造）。

### 2.5 输出字段（对齐规范）
`units[]`：`{unit_id, name, order, status, source_range, page_start, section_profile, keep_together, confidence, flags, evidence}`；`order` 由 `source_range` 在文档中的先后自动得出。

### 2.6 改动点（文件/函数）
- 重写 `_infer_units()`（92）、`_unit_for_text()`（713）→ 拆成"边界检测器 + 标签器"两步；词表（672–690）保留但只供标签器用。
- 单元 confidence 不再写死（`:148`、`:525`）。
- **新增 abstain 那侧**：按 §2.2 在中间带/required 缺失处写 `open_questions[]`，并产出投影 `t2_input.json`（确定性、AI 关也产出）；预留 `t2_ai_response.json` 与合并步的接口（本轮不实现 AI）。
- 确保新 confidence/flags/evidence/open_questions 透传到 `unit_map.yaml` 与下游 `verification_report.json`。

---

## 3. 验收（结构门禁，gold 建立前先用）【设计】
- **没有任何单元的 `source_range` 落在目录区**（除 `toc` 单元本身）——直接消灭"abstract_cn/body_main/references 指向目录行"。
- `toc` 单元覆盖完整目录（含全部条目），不再截断成数行。
- **不再有吞掉全部表格的巨型 catch-all**（`post_forms` 217 ref 那种）。
- 必需单元 presence 100%、顺序正确；`page_start`/`section_profile` 来自确定性规则。
- confidence 分布不再是 100% `medium`；`other`/低置信/冲突项进 `flags`。
- **每个非高置信判定都有 typed `open_question`**（label / boundary / required_missing）；只要有 `open_question` 就产出 `t2_input.json`；这两者均不依赖 AI（空跑也有分级反馈）。

待挑一所学校建 T5 主 gold 后，再切出 `unit_map.expected.yaml` 做精确比对（IoU 等）。

---

## 4. 测试命令
```bash
uv run pytest tests/contract/test_template_generate.py -q
uv run pytest tests/contract/test_real_core_generated_template_gap.py -q
uv run pytest tests/contract -q
# 三校复现，人工核对 unit_map：
for s in hunannongye nannong-undergraduate pku-graduate; do
  uv run docfit eval template-generate --template inputs/targets/$s/raw/source_template.docx \
    --out test_outputs/debug/template_generation/<run_tag>/$s
done
```

---

## 5. 依赖与状态
- **强依赖 T1** 的两个原子判据 `is_toc_entry` / `is_spacing_line`（已完成，见 T1 文档 §1.2）作为否决项。
- **下游 T3 强依赖 T1 的 run 归一化**（T1 文档 §2.1，待实现）；T2 边界判定本身对归一化弱依赖，但建议 T1 归一化先落地，给 T3 一个干净的 logical run。
- 本份所有"优化建议"均为 **【设计】待实现**；当前仅完成上游 T1 的判据补齐。
- **abstain（§2.2）是 §2.1 检测器同一次打分的副产物**，确定性、可测、不依赖 AI——**随检测器一起落地，不单独做**；落地后"信号不足分不出来"时即有分级反馈 + `t2_input.json`，AI/视觉以后再接。
