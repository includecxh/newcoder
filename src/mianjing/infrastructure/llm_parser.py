"""LLM 返回 JSON 的容错解析器。

LLM 返回的 JSON 常见不规范：带 ```json 代码块标记、前后多余文字。
本模块做容错提取，解析为 list[Question]。
"""
from __future__ import annotations

import json
import re

from mianjing.domain.models import Question


def parse_questions(raw: str) -> list[Question]:
    """容错解析 LLM 返回的文本为问题列表。

    处理顺序：
    1. 去除 ```json ... ``` 代码块标记
    2. 提取首个 [...] 段（剥离前后多余文字）
    3. json.loads
    4. 逐项取 "question" 字段，编号从 1 开始

    Args:
        raw: LLM 返回的原始文本。

    Returns:
        问题列表（可能为空）。

    Raises:
        RuntimeError: 当完全无法解析时，含原始返回前 200 字。
    """
    text = raw.strip()

    # 1. 去 ```json ... ``` 标记
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()

    # 2. 提取首个 [...] 段
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1 or end < start:
        preview = raw[:200]
        raise RuntimeError(f"无法解析问题列表（未找到 JSON 数组）: {preview}")
    json_str = text[start : end + 1]

    # 3. 解析
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        preview = raw[:200]
        raise RuntimeError(f"JSON 解析失败: {e}；原始返回: {preview}") from e

    if not isinstance(data, list):
        raise RuntimeError(f"期望 JSON 数组，得到 {type(data).__name__}: {raw[:200]}")

    # 4. 转 Question，编号从 1 开始
    questions: list[Question] = []
    for i, item in enumerate(data, start=1):
        if isinstance(item, dict) and "question" in item:
            questions.append(Question(text=str(item["question"]).strip(), index=i))
        elif isinstance(item, str):
            questions.append(Question(text=item.strip(), index=i))
    return questions
