"""compile_service 测试：用桩 LLM（mock gateway）验证两步编排与模式分流。"""
from pathlib import Path
from unittest.mock import patch

import pytest

from mianjing.application.compile_service import compile_mianjing
from mianjing.domain.models import Answer, Question


def _stub_questions() -> list[Question]:
    return [Question(text="Q1", index=1), Question(text="Q2", index=2)]


@patch("mianjing.application.compile_service.answer_questions_batch")
@patch("mianjing.application.compile_service.parse_questions")
@patch("mianjing.application.compile_service.extract_questions")
def test_low_mode_calls_batch_once(
    mock_extract, mock_parse, mock_batch, tmp_path: Path,
) -> None:
    """low 模式：拆1次 + 批量答1次。"""
    mock_extract.return_value = '[{"question":"Q1"}]'
    mock_parse.return_value = _stub_questions()
    # low 模式批量返回用 <<<ANSWER>>> 分隔
    mock_batch.return_value = "<<<ANSWER>>>\nA1\n<<<ANSWER>>>\nA2\n"

    result = compile_mianjing("面经", config=object(), output_dir=tmp_path, mode="low")

    mock_extract.assert_called_once()
    mock_parse.assert_called_once()
    mock_batch.assert_called_once()
    assert result.exists()
    assert "Q1" in result.read_text(encoding="utf-8")


@patch("mianjing.application.compile_service.answer_one")
@patch("mianjing.application.compile_service.parse_questions")
@patch("mianjing.application.compile_service.extract_questions")
def test_high_mode_calls_answer_per_question(
    mock_extract, mock_parse, mock_one, tmp_path: Path,
) -> None:
    """high 模式：拆1次 + 逐题答N次。"""
    mock_extract.return_value = '[{"question":"Q1"}]'
    mock_parse.return_value = _stub_questions()
    mock_one.side_effect = [Answer(content="A1"), Answer(content="A2")]

    result = compile_mianjing("面经", config=object(), output_dir=tmp_path, mode="high")

    assert mock_one.call_count == 2  # 两个问题各答一次
    assert result.exists()
    md = result.read_text(encoding="utf-8")
    assert "A1" in md and "A2" in md


@patch("mianjing.application.compile_service.extract_questions")
def test_empty_text_raises(mock_extract, tmp_path: Path) -> None:
    """空输入报错，不调 LLM。"""
    with pytest.raises(ValueError):
        compile_mianjing("", config=object(), output_dir=tmp_path, mode="low")
    mock_extract.assert_not_called()


@patch("mianjing.application.compile_service.parse_questions")
@patch("mianjing.application.compile_service.extract_questions")
def test_zero_questions_raises(mock_extract, mock_parse, tmp_path: Path) -> None:
    """拆出 0 问题 → 报错。"""
    mock_extract.return_value = "[]"
    mock_parse.return_value = []
    with pytest.raises(ValueError, match="未识别到问题"):
        compile_mianjing("面经", config=object(), output_dir=tmp_path, mode="low")


# ========== Day3：compile_batch 批量 + 失败跳过 ==========
from mianjing.application.compile_service import compile_batch
from mianjing.domain.models import InputItem


@patch("mianjing.application.compile_service.answer_questions_batch")
@patch("mianjing.application.compile_service.parse_questions")
@patch("mianjing.application.compile_service.extract_questions")
def test_compile_batch_success_and_failure(
    mock_extract, mock_parse, mock_batch, tmp_path: Path,
) -> None:
    """批量：第2篇失败跳过，1和3成功。"""
    items = [
        InputItem(raw_text="面经A", source_name="a"),
        InputItem(raw_text="面经B", source_name="b"),
        InputItem(raw_text="面经C", source_name="c"),
    ]
    mock_extract.side_effect = ['[{"question":"Q"}]'] * 3
    mock_parse.side_effect = [[Question(text="Q", index=1)]] * 3
    mock_batch.side_effect = ["A答案", RuntimeError("LLM炸了"), "C答案"]

    results = compile_batch(items, config=object(), output_dir=tmp_path, mode="low")

    assert len(results) == 3
    assert results[0].success is True
    assert results[1].success is False
    assert "LLM炸了" in results[1].error
    assert results[2].success is True
    assert results[0].output_path is not None
    assert results[0].output_path.exists()


@patch("mianjing.application.compile_service.answer_questions_batch")
@patch("mianjing.application.compile_service.parse_questions")
@patch("mianjing.application.compile_service.extract_questions")
def test_compile_batch_passes_source_name_to_filename(
    mock_extract, mock_parse, mock_batch, tmp_path: Path,
) -> None:
    """成功的项，文件名含 source_name。"""
    mock_extract.return_value = '[{"question":"Q"}]'
    mock_parse.return_value = [Question(text="Q", index=1)]
    mock_batch.return_value = "<<<ANSWER>>>\n答案\n"

    items = [InputItem(raw_text="x", source_name="redis")]
    results = compile_batch(items, config=object(), output_dir=tmp_path, mode="low")

    assert results[0].success is True
    assert results[0].output_path.name.startswith("redis_")
