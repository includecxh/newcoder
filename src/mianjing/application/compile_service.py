"""应用层：编排两步"拆问题 → 按模式回答 → 格式化 → 存盘"。

Day2 把 Day1 的单次调用升级为两步，按 mode 分流：
- low：拆1次 + 批量答1次
- high：拆1次 + 逐题答N次
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from mianjing.config import Config
from mianjing.domain.models import Answer, CompileResult, InputItem, Question
from mianjing.infrastructure.llm_gateway import (
    answer_one,
    answer_questions_batch,
    extract_questions,
)
from mianjing.infrastructure.llm_parser import parse_questions
from mianjing.infrastructure.md_writer import write_markdown

from .formatter import build_title, format_note

VALID_MODES = ("low", "high")


def compile_mianjing(
    raw_text: str,
    config: Config,
    output_dir: Path,
    mode: str = "low",
    source_name: str | None = None,
) -> Path:
    """编排两步流程，返回写入的文件 Path。

    Args:
        raw_text: 面经原文。
        config: LLM 接入配置。
        output_dir: md 输出目录。
        mode: "low" 批量 / "high" 逐题。
        source_name: 来源名（文件名stem/inline），用于 md 命名，可选。

    Returns:
        写入的文件 Path。

    Raises:
        ValueError: 空输入、非法 mode、拆出 0 问题。
        RuntimeError: LLM 调用或 JSON 解析失败。
    """
    if not raw_text or not raw_text.strip():
        raise ValueError("面经内容为空，无内容可整理")
    if mode not in VALID_MODES:
        raise ValueError(f"非法模式 {mode}，可选 {VALID_MODES}")

    # 第一步：拆问题
    json_str = extract_questions(raw_text, config)
    questions = parse_questions(json_str)
    if not questions:
        raise ValueError("未识别到问题，请检查面经内容")

    # 第二步：按模式回答
    if mode == "low":
        markdown_body = answer_questions_batch(questions, config)
        answers = _split_batch_answers(markdown_body, questions)
    else:  # high
        answers = [answer_one(q, config) for q in questions]

    # 格式化 + 存盘
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    markdown = format_note(
        questions,
        answers,
        {
            "source_title": build_title(raw_text),
            "created_at": created_at,
            "mode": mode,
        },
    )
    return write_markdown(markdown, output_dir, source_name=source_name)


def _split_batch_answers(body: str, questions: list[Question]) -> list[Answer]:
    """low 模式：把批量返回的 markdown 按 <<<ANSWER>>> 分隔符切成多个 Answer。

    LLM 被要求每个答案前输出一行 <<<ANSWER>>>。
    兜底：若分隔符缺失，整段作为每个问题的答案（保证长度对齐）。
    """
    from mianjing.infrastructure.llm_gateway import BATCH_ANSWER_SEP

    if not questions:
        return []
    chunks = [c.strip() for c in body.split(BATCH_ANSWER_SEP) if c.strip()]
    if not chunks:
        chunks = [body]
    answers: list[Answer] = []
    for i, q in enumerate(questions):
        content = chunks[i] if i < len(chunks) else ""
        answers.append(Answer(content=content))
    return answers


def compile_batch(
    items: list[InputItem],
    config: Config,
    output_dir: Path,
    mode: str = "low",
) -> list[CompileResult]:
    """批量处理多篇，每篇失败跳过，返回结果列表。

    Args:
        items: 输入项列表。
        config: LLM 配置。
        output_dir: 输出目录。
        mode: low/high。

    Returns:
        每篇的 CompileResult（成功含 output_path，失败含 error）。
    """
    results: list[CompileResult] = []
    for item in items:
        try:
            path = compile_mianjing(
                item.raw_text, config=config, output_dir=output_dir,
                mode=mode, source_name=item.source_name,
            )
            results.append(CompileResult(
                source_name=item.source_name, success=True, output_path=path,
            ))
        except (RuntimeError, ValueError) as e:
            results.append(CompileResult(
                source_name=item.source_name, success=False, error=str(e),
            ))
    return results
