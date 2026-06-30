"""领域模型：面经、问题、答案、整理结果。

遵循分层架构，domain 层只依赖标准库，不依赖 infrastructure。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Mianjing:
    """面经原文。"""

    raw_text: str


@dataclass
class Question:
    """从面经中拆出的单个问题。"""

    text: str
    index: int = 0  # 问题序号，从1开始；0表示未编号


@dataclass
class Answer:
    """对单个问题的回答。"""

    content: str


@dataclass
class CompiledNote:
    """整理结果：含问题答案对的 markdown 文档。"""

    title: str
    markdown: str
    qa_pairs: list[tuple[Question, Answer]] = field(default_factory=list)
    # Day2 元信息
    mode: str = "low"
    question_count: int = 0
    created_at: str = ""  # 生成时间，由调用方传入


@dataclass
class InputItem:
    """一个待处理的面经输入项。"""

    raw_text: str
    source_name: str  # 来源名（文件名stem/inline），用于 md 命名


@dataclass
class CompileResult:
    """单篇处理结果（用于批量汇总）。"""

    source_name: str
    success: bool
    output_path: Path | None = None
    error: str | None = None
