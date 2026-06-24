from __future__ import annotations

DEFAULT_TEMPLATE_GENERATION_STRATEGY = "source_copy_scaffold"
BODY_SLOT_MARKER = "[[DOCFIT_SLOT:body]]"
COPY_ONLY_DEFAULT_EXCLUDED_UNIT_IDS = {
    "abstract_cn",
    "abstract_en",
    "toc",
    "body_main",
    "references",
}
FILLABLE_CONTENT_UNIT_IDS = {
    "abstract_cn",
    "abstract_en",
    "body_main",
    "references",
}

UNIT_DEFINITIONS = (
    ("cover", "封面", ("封面", "题名", "论文题目", "学校", "学号", "指导教师")),
    ("integrity_statement", "诚信声明", ("诚信声明", "原创性声明", "授权书")),
    ("toc", "目录", ("目录", "目 录")),
    ("abstract_cn", "中文摘要", ("摘要", "摘 要", "关键词")),
    ("abstract_en", "英文摘要", ("abstract", "key words", "keywords")),
    ("body_main", "正文", ("正文", "绪论", "第一章", "1 ")),
    ("references", "参考文献", ("参考文献", "references")),
    ("acknowledgement", "致谢", ("致谢", "acknowledgement")),
    ("appendix", "附录", ("附录", "appendix")),
    ("post_forms", "后置固定表单", ("任务书", "开题", "评审", "答辩", "成绩评定")),
)

FILLABLE_MARKERS = ("××", "□□", "____", "——", "：", ":")
FILLABLE_LABELS = (
    "题名",
    "题目",
    "姓名",
    "学号",
    "学院",
    "专业",
    "班级",
    "教师",
    "日期",
    "摘要正文",
    "关键词",
)
MANUAL_ONLY_MARKERS = ("签名", "年月日", "年  月  日", "意见", "成绩", "评定")
GENERATED_MARKERS = ("目录", "页码", "编号", "图目录", "表目录", "公式")
INSTRUCTION_MARKERS = (
    "格式",
    "要求",
    "说明",
    "模板",
    "几号",
    "号字",
    "空一行",
    "倍行距",
    "页边距",
    "附件",
)

UNIT_DEFINITION_NAMES = {unit_id: name for unit_id, name, _ in UNIT_DEFINITIONS}
