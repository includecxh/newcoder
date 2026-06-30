"""llm_gateway 测试：测 prompt 构造 + Day5 的 429 重试（不测真实网络）。"""
from mianjing.domain.models import Mianjing, Question
from mianjing.infrastructure.llm_gateway import (
    answer_and_compile,
    build_batch_answer_prompt,
    build_extract_prompt,
    build_one_answer_prompt,
    build_prompt,
)


def test_build_prompt_contains_instructions() -> None:
    """Day1 prompt 应包含拆问题和回答的指令。"""
    prompt = build_prompt(Mianjing(raw_text="请讲讲 Redis 持久化"))

    assert "问题" in prompt
    assert "回答" in prompt
    assert "markdown" in prompt.lower() or "md" in prompt.lower()
    assert "请讲讲 Redis 持久化" in prompt


def test_build_extract_prompt_asks_for_json() -> None:
    """拆问题 prompt 要求返回 JSON 数组。"""
    prompt = build_extract_prompt(Mianjing(raw_text="面经内容X"))
    assert "JSON" in prompt or "json" in prompt
    assert "question" in prompt
    assert "面经内容X" in prompt


def test_build_batch_answer_prompt_includes_all_questions() -> None:
    """批量回答 prompt 含所有问题。"""
    questions = [Question(text="Q1", index=1), Question(text="Q2", index=2)]
    prompt = build_batch_answer_prompt(questions)
    assert "Q1" in prompt
    assert "Q2" in prompt


def test_build_one_answer_prompt_includes_question() -> None:
    """单题回答 prompt 含该问题。"""
    prompt = build_one_answer_prompt(Question(text="Redis 持久化", index=1))
    assert "Redis 持久化" in prompt


def test_answer_and_compile_still_importable() -> None:
    assert callable(answer_and_compile)


# ========== Day5：429 重试 ==========
import httpx
from unittest.mock import MagicMock, patch

import pytest
from openai import RateLimitError

from mianjing.infrastructure.llm_gateway import _chat, _is_rate_limit


def _make_rate_limit_error() -> RateLimitError:
    """构造一个 RateLimitError。"""
    request = httpx.Request("POST", "https://x")
    response = httpx.Response(status_code=429, request=request)
    return RateLimitError("限流", response=response, body=None)


def test_is_rate_limit_recognizes_rate_limit_error() -> None:
    """RateLimitError → True。"""
    assert _is_rate_limit(_make_rate_limit_error()) is True


def test_is_rate_limit_recognizes_status_429() -> None:
    """含 status_code=429 的异常 → True（非 SDK 类型也认）。"""
    exc = Exception("x")
    exc.status_code = 429  # type: ignore[attr-defined]
    assert _is_rate_limit(exc) is True


def test_is_rate_limit_rejects_other_errors() -> None:
    """非 429 → False。"""
    assert _is_rate_limit(Exception("普通错误")) is False
    exc = Exception("鉴权错")
    exc.status_code = 401  # type: ignore[attr-defined]
    assert _is_rate_limit(exc) is False


@patch("mianjing.infrastructure.llm_gateway.OpenAI")
def test_chat_retries_on_429_then_succeeds(mock_openai_cls) -> None:
    """第一次 429、第二次成功 → 重试 1 次后返回，sleep 被调用 1 次。"""
    ok_resp = MagicMock()
    ok_resp.choices = [MagicMock(message=MagicMock(content="答案"))]
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = [_make_rate_limit_error(), ok_resp]
    mock_openai_cls.return_value = mock_client

    config = MagicMock(max_retries=3, retry_backoff=[1, 2, 4])  # MagicMock 有任意属性，避免 object() 无 api_key
    sleeps = []
    result = _chat(config=config, prompt="p", _sleep=lambda s: sleeps.append(s))

    assert result == "答案"
    assert mock_client.chat.completions.create.call_count == 2
    assert sleeps == [1]


@patch("mianjing.infrastructure.llm_gateway.OpenAI")
def test_chat_retries_3_times_then_raises(mock_openai_cls) -> None:
    """连续 429 → 重试 3 次（共 4 次调用）后抛 RuntimeError，退避 [1,2,4]。"""
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = [_make_rate_limit_error()] * 4
    mock_openai_cls.return_value = mock_client

    config = MagicMock(max_retries=3, retry_backoff=[1, 2, 4])
    sleeps = []
    with pytest.raises(RuntimeError):
        _chat(config=config, prompt="p", _sleep=lambda s: sleeps.append(s))

    assert mock_client.chat.completions.create.call_count == 4
    assert sleeps == [1, 2, 4]


@patch("mianjing.infrastructure.llm_gateway.OpenAI")
def test_chat_no_retry_on_non_429(mock_openai_cls) -> None:
    """非 429 错误 → 不重试，直接抛 RuntimeError。"""
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = ValueError("鉴权错")
    mock_openai_cls.return_value = mock_client

    config = MagicMock(max_retries=3, retry_backoff=[1, 2, 4])
    sleeps = []
    with pytest.raises(RuntimeError):
        _chat(config=config, prompt="p", _sleep=lambda s: sleeps.append(s))

    assert mock_client.chat.completions.create.call_count == 1
    assert sleeps == []
