"""md_writer 测试：验证文件确实写出来、内容正确、命名规范。"""
from pathlib import Path

from mianjing.infrastructure.md_writer import write_markdown


def test_write_markdown_creates_file_with_content(tmp_path: Path) -> None:
    """写入后，文件存在且内容与传入一致。"""
    content = "# 测试面经\n\n## Q: 问题\nA: 答案\n"
    output_path = write_markdown(content, tmp_path)

    assert output_path.exists()
    assert output_path.read_text(encoding="utf-8") == content


def test_write_markdown_filename_is_timestamp(tmp_path: Path) -> None:
    """文件名是 YYYY-MM-DD_HHmmss.md 格式。"""
    output_path = write_markdown("内容", tmp_path)

    name = output_path.name
    # 形如 2026-06-26_153045.md
    assert name.endswith(".md")
    stem = name[:-3]
    date_part, time_part = stem.split("_")
    assert len(date_part) == 10  # YYYY-MM-DD
    assert len(time_part) == 6  # HHmmss


# ========== Day3：source_name 命名 + 向后兼容 ==========
def test_write_markdown_with_source_name(tmp_path: Path) -> None:
    """有 source_name → 源名_时间戳.md。"""
    path = write_markdown("内容", tmp_path, source_name="redis")
    name = path.name
    assert name.startswith("redis_")
    assert name.endswith(".md")
    assert path.read_text(encoding="utf-8") == "内容"


def test_write_markdown_without_source_name_backward_compat(tmp_path: Path) -> None:
    """不传 source_name → 纯时间戳（Day2 兼容）。"""
    path = write_markdown("内容", tmp_path)
    name = path.name
    stem = name[:-3]
    # 纯时间戳形如 2026-06-26_153020，不含第二个下划线
    date_part, time_part = stem.split("_")
    assert len(date_part) == 10
    assert len(time_part) == 6
