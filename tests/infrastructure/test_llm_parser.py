"""llm_parser 测试：容错解析 LLM 返回的 JSON 为问题列表。"""
import pytest

from mianjing.infrastructure.llm_parser import parse_questions


def test_parse_plain_json() -> None:
    """最规整：纯 JSON 数组。"""
    raw = '[{"question": "什么是 Redis？"}, {"question": "RDB 和 AOF 区别？"}]'
    questions = parse_questions(raw)
    assert len(questions) == 2
    assert questions[0].text == "什么是 Redis？"
    assert questions[1].text == "RDB 和 AOF 区别？"
    assert questions[0].index == 1
    assert questions[1].index == 2


def test_parse_json_with_code_fence() -> None:
    """带 ```json 代码块标记。"""
    raw = '```json\n[{"question": "TCP 三次握手"}]\n```'
    questions = parse_questions(raw)
    assert len(questions) == 1
    assert questions[0].text == "TCP 三次握手"


def test_parse_json_with_extra_text() -> None:
    """LLM 在 JSON 前后加了多余文字。"""
    raw = '好的，以下是结果：\n[{"question": "B+ 树"}]\n希望对你有帮助。'
    questions = parse_questions(raw)
    assert len(questions) == 1
    assert questions[0].text == "B+ 树"


def test_parse_empty_array() -> None:
    """空数组 → 空列表（不报错，由调用方判断是否 0 问题）。"""
    questions = parse_questions("[]")
    assert questions == []


def test_parse_invalid_raises_with_context() -> None:
    """完全无法解析 → RuntimeError，含原始返回片段。"""
    raw = "这不是 JSON 也没有方括号"
    with pytest.raises(RuntimeError) as exc:
        parse_questions(raw)
    assert "无法解析" in str(exc.value) or "解析" in str(exc.value)
    assert raw in str(exc.value)


def test_parse_questions_index_starts_from_1() -> None:
    """问题序号从 1 开始递增。"""
    raw = '[{"question": "Q1"}, {"question": "Q2"}, {"question": "Q3"}]'
    questions = parse_questions(raw)
    assert [q.index for q in questions] == [1, 2, 3]
