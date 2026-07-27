from __future__ import annotations

DEFAULT_TEMPLATE_GENERATION_STRATEGY = "source_copy_scaffold"
BODY_SLOT_MARKER = "[[DOCFIT_SLOT:body]]"

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
