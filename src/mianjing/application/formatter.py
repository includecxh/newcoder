"""md 格式化器：把问题+答案列表拼成规范 markdown。

含标题、元信息（时间/问题数/模式）、目录、结构化问答。
"""
from __future__ import annotations

from mianjing.domain.models import Answer, Question

TITLE_MAX = 20  # 标题最大字符数


def build_title(source_text: str) -> str:
    """从面经文本生成标题：前 TITLE_MAX 字，超出加"等"。

    Args:
        source_text: 面经原文（或其截取）。

    Returns:
        标题字符串。
    """
    text = source_text.strip().replace("\n", " ")
    if len(text) <= TITLE_MAX:
        return text
    return text[:TITLE_MAX] + "等"


def format_note(
    questions: list[Question],
    answers: list[Answer],
    meta: dict,
) -> str:
    """拼装规范 md：标题 + 元信息 + 目录 + 问答。

    Args:
        questions: 问题列表（带 index）。
        answers: 答案列表，与 questions 一一对应。
        meta: 含 source_title / created_at / mode。

    Returns:
        完整 markdown 字符串。
    """
    title = build_title(meta.get("source_title", "面经整理"))
    mode = meta.get("mode", "low")
    created_at = meta.get("created_at", "")
    count = len(questions)

    lines: list[str] = []
    lines.append(f"# 面经整理：{title}")
    lines.append("")
    lines.append(f"> 生成时间：{created_at}  ")
    lines.append(f"> 问题数：{count}  ")
    lines.append(f"> 模式：{mode}")
    lines.append("")

    if questions:
        lines.append("## 目录")
        for q in questions:
            lines.append(f"{q.index}. {q.text}")
        lines.append("")
        lines.append("---")
        lines.append("")

    for q, a in zip(questions, answers):
        lines.append(f"## {q.index}. {q.text}")
        lines.append("")
        lines.append("### 参考回答")
        lines.append("")
        lines.append(a.content)
        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)
