"""formatter 测试：验证拼出的 md 含标题/元信息/目录/问答。"""
from mianjing.application.formatter import build_title, format_note
from mianjing.domain.models import Answer, Question


def test_build_title_truncates_long_text() -> None:
    """标题取前 20 字 + 等。"""
    long = "Redis的持久化机制RDB和AOF有什么区别还有很多字"
    title = build_title(long)
    assert len(title) <= 22  # 20 + "等" 最多21，留余量
    assert title.startswith("Redis的持久化机制RDB")
    assert title.endswith("等")


def test_build_title_short_text_no_deng() -> None:
    """短文本不加等。"""
    assert build_title("TCP 三次握手") == "TCP 三次握手"


def test_format_note_contains_meta_and_toc_and_qa() -> None:
    """拼出的 md 含元信息、目录、问答。"""
    questions = [
        Question(text="什么是 Redis", index=1),
        Question(text="RDB 和 AOF 区别", index=2),
    ]
    answers = [
        Answer(content="Redis 是内存数据库"),
        Answer(content="RDB 快照，AOF 日志"),
    ]
    md = format_note(questions, answers, {
        "mode": "high",
        "created_at": "2026-06-26 12:00:00",
        "source_title": "什么是 RedisRDB 和 AOF 区别等",
    })

    assert "# 面经整理" in md
    assert "2026-06-26 12:00:00" in md
    assert "问题数：2" in md
    assert "模式：high" in md
    assert "## 目录" in md
    assert "1. 什么是 Redis" in md
    assert "## 1. 什么是 Redis" in md
    assert "Redis 是内存数据库" in md
    assert "## 2. RDB 和 AOF 区别" in md
    assert "RDB 快照，AOF 日志" in md


def test_format_note_low_mode() -> None:
    """low 模式元信息显示 low。"""
    questions = [Question(text="Q1", index=1)]
    answers = [Answer(content="A1")]
    md = format_note(questions, answers, {"mode": "low", "created_at": "t", "source_title": "Q1等"})
    assert "模式：low" in md
