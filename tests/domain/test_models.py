"""领域模型测试：验证 Day2 扩展字段。"""
from pathlib import Path

from mianjing.domain.models import Answer, CompiledNote, Question


def test_question_has_index_default_zero() -> None:
    q = Question(text="什么是 Redis？")
    assert q.index == 0


def test_question_with_index() -> None:
    q = Question(text="什么是 Redis？", index=1)
    assert q.index == 1


def test_compiled_note_has_meta_fields() -> None:
    note = CompiledNote(
        title="面经整理",
        markdown="# x",
        qa_pairs=[],
        mode="high",
        question_count=3,
        created_at="2026-06-26 12:00:00",
    )
    assert note.mode == "high"
    assert note.question_count == 3
    assert note.created_at == "2026-06-26 12:00:00"


# ========== Day3：InputItem + CompileResult ==========
from mianjing.domain.models import CompileResult, InputItem


def test_input_item() -> None:
    item = InputItem(raw_text="面经", source_name="redis")
    assert item.raw_text == "面经"
    assert item.source_name == "redis"


def test_compile_result_success() -> None:
    r = CompileResult(source_name="redis", success=True, output_path=Path("/o/x.md"))
    assert r.success is True
    assert r.error is None


def test_compile_result_failure() -> None:
    r = CompileResult(source_name="redis", success=False, error="LLM失败")
    assert r.success is False
    assert r.output_path is None
    assert r.error == "LLM失败"
