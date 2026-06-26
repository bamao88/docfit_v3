from __future__ import annotations

DEFAULT_TEMPLATE_GENERATION_STRATEGY = "source_copy_scaffold"
BODY_SLOT_MARKER = "[[DOCFIT_SLOT:body]]"
COPY_ONLY_DEFAULT_UNIT_IDS: frozenset[str] = frozenset()
FILLABLE_CONTENT_UNIT_IDS = {
    "abstract_cn",
    "abstract_en",
    "body_main",
    "references",
    "appendix",
    "acknowledgement",
}

UNIT_DEFINITIONS = (
    ("cover", "封面", ("封面", "题名", "论文题目", "学校", "学号", "指导教师")),
    ("copyright_notice", "版权声明", ("版权声明",)),
    (
        "originality_authorization_statement",
        "原创性声明和使用授权说明",
        ("原创性声明和使用授权说明", "原创性声明使用授权说明"),
    ),
    (
        "originality_statement",
        "原创性声明",
        ("原创性声明", "论文原创性声明"),
    ),
    (
        "authorization_statement",
        "使用授权声明",
        ("使用授权声明", "使用授权说明", "授权声明"),
    ),
    ("integrity_statement", "诚信声明", ("诚信声明", "诚 信 声 明")),
    ("toc", "目录", ("目录", "目 录")),
    ("figure_list", "图目录", ("图目录", "图 目录", "插图目录", "list of figures")),
    ("table_list", "表目录", ("表目录", "表 目录", "附表目录", "list of tables")),
    ("body_title_block", "正文题名信息", ("正文题名信息", "论文题名", "学生", "指导老师")),
    ("abstract_cn", "中文摘要", ("摘要", "摘 要", "关键词")),
    ("abstract_en", "英文摘要", ("abstract", "key words", "keywords")),
    ("body_main", "正文", ("正文", "绪论", "第一章", "1 ")),
    ("references", "参考文献", ("参考文献", "references")),
    (
        "academic_achievements",
        "学术成果",
        ("相关的学术成果目录", "学术成果目录", "学术成果", "博士期间工作成果"),
    ),
    ("acknowledgement", "致谢", ("致谢", "acknowledgement")),
    ("appendix", "附录", ("附录", "appendix")),
    ("design_task", "毕业设计任务书", ("毕业设计任务书", "毕业论文任务书", "任务书")),
    ("proposal", "开题报告", ("开题报告",)),
    ("proposal_record", "开题论证记录表", ("开题论证记录表",)),
    ("defense_record", "答辩记录表", ("答辩记录表",)),
    ("topic_change_approval", "课题变更审批表", ("课题变更审批表", "选题变更审批表")),
    ("grade_form", "成绩评定表", ("成绩评定表",)),
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
