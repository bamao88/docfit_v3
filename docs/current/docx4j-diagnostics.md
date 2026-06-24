# docx4j 旁路诊断

一句话结论：docx4j 现在只作为可选只读诊断工具，用来比较 Java/docx4j 和当前 Python inspector 分别看到了哪些 Word / OOXML 证据；它不参与 `PASS` / `FAIL` 裁判，也不替换 DocFit 四阶段主链路。

## 这个工具做什么

当前真实实现仍以 Python 阶段产物为准：

| 项 | 当前边界 |
| --- | --- |
| 主链路 | 模板解析、内容提取、内容放置、DOCX 渲染仍由现有 Python 代码执行 |
| docx4j 用途 | 旁路读取同一份 `.docx`，补充诊断证据 |
| 是否改 Word | 不改；Java 工具只读输入 DOCX 并写 JSON |
| 是否判门禁 | 不判；报告明确 `decides_pass_fail = false` |
| Java 不可用时 | 报告 `tool.status = unavailable` 或 `failed`，DocFit 主链路继续运行 |

这个能力的第一目标不是生成更好的 Word，而是回答一个排查问题：当前 Python inspector 是否漏掉了 docx4j 能稳定看到的可见对象或 OOXML 结构。

## 命令

默认命令：

```bash
uv run docfit inspect-docx4j \
  --docx inputs/targets/hunannongye/raw/source_template.docx \
  --out runs/workbench/docx4j_hunannongye_template
```

如果要指定自定义 Java 命令：

```bash
uv run docfit inspect-docx4j \
  --docx inputs/targets/hunannongye/raw/source_template.docx \
  --out runs/workbench/docx4j_hunannongye_template \
  --docx4j-command 'java -jar /path/to/docx4j-inspector.jar {input_docx} --out {output_json}'
```

默认 Java 工具在 `scripts/docx4j-inspector/`，通过 Maven 运行。首次运行可能需要下载 Maven 依赖；没有 Java、Maven 或网络时，命令仍会产出 Python inspector 和诊断报告，只是 `comparison_status = not_run`。

## 产物

| 产物 | 含义 |
| --- | --- |
| `artifacts/python_inspection.json` | 当前 Python inspector 对同一 DOCX 的观察结果 |
| `artifacts/docx4j_inspection.json` | docx4j 旁路工具的观察结果；工具不可用时不会生成 |
| `docx4j_comparison_report.json` | 机器可读对比报告 |
| `docx4j_comparison_report.md` | 人可读对比摘要 |

对比报告主要看三类信息：

| 字段 | 用途 |
| --- | --- |
| `tool.status` | Java/docx4j 工具是否可用 |
| `comparison_status` | 是否真的完成了两边对比 |
| `data.count_differences[]` | 哪些对象类别数量不同，例如 text box、footnote、image、section |
| `data.visible_text_differences` | 哪些可见文本只被其中一边看到 |

## 门禁边界

docx4j 报告不能把任何阶段结果改成 `PASS`。如果 docx4j 比当前 Python inspector 多看到文本框、脚注、图片或字段，这只能说明“当前证据可能不足，需要继续建模或维持 UNKNOWN”，不能说明转换已经正确。

如果后续要把 docx4j 输出纳入正式阶段产物，必须先补一份字段说明，至少写清：

| 项 | 需要明确 |
| --- | --- |
| 字段含义 | 这个字段代表哪类 Word / OOXML 事实 |
| 生产者 | Java docx4j 工具、Python wrapper，还是正式阶段代码 |
| 消费者 | 哪个阶段、检查器或报告读取 |
| 门禁影响 | 是否影响 `PASS` / `FAIL` / `UNKNOWN` |
| 缺失结果 | Java 不可用或字段缺失时是 `UNKNOWN`、诊断缺口，还是不阻断 |
| AI 边界 | AI 只能解释报告，不能补造证据或改状态 |
| 测试 | 需要哪些 fixture 和回归样例证明字段稳定 |

## 当前建议用法

| 场景 | 是否适合 |
| --- | --- |
| 真实模板 gap 大面积 UNKNOWN，怀疑 Python inspector 漏了对象 | 适合 |
| 学生内容提取怀疑漏掉脚注、文本框、图片 | 适合 |
| 想证明最终转换通过 | 不适合 |
| 想替换渲染器 | 暂不适合 |
| 想自动更新 golden 或标准 | 禁止 |
