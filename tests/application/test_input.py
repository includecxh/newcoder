"""input 测试：读单文件/目录/空目录/不存在。"""
from pathlib import Path

import pytest

from mianjing.application.input import (
    read_input,
    read_input_dir,
    read_single_file,
)


def test_read_single_file(tmp_path: Path) -> None:
    f = tmp_path / "redis.txt"
    f.write_text("Redis 面经内容", encoding="utf-8")
    item = read_single_file(f)
    assert item.raw_text == "Redis 面经内容"
    assert item.source_name == "redis"


def test_read_single_file_not_found(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        read_single_file(tmp_path / "nope.txt")


def test_read_input_dir(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("A", encoding="utf-8")
    (tmp_path / "b.txt").write_text("B", encoding="utf-8")
    (tmp_path / "c.md").write_text("C", encoding="utf-8")  # 非 txt，应忽略
    items = read_input_dir(tmp_path)
    names = sorted(i.source_name for i in items)
    assert names == ["a", "b"]
    assert all(i.raw_text in ("A", "B") for i in items)


def test_read_input_dir_empty(tmp_path: Path) -> None:
    """空目录返回空列表。"""
    assert read_input_dir(tmp_path) == []


def test_read_input_dir_not_a_directory(tmp_path: Path) -> None:
    f = tmp_path / "x.txt"
    f.write_text("x", encoding="utf-8")
    with pytest.raises(NotADirectoryError):
        read_input_dir(f)


def test_read_input_file_path(tmp_path: Path) -> None:
    """read_input 给 file → 单项。"""
    f = tmp_path / "redis.txt"
    f.write_text("R", encoding="utf-8")
    items = read_input(file=f, input_dir=None)
    assert len(items) == 1
    assert items[0].source_name == "redis"


def test_read_input_dir_path(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("A", encoding="utf-8")
    items = read_input(file=None, input_dir=tmp_path)
    assert len(items) == 1
    assert items[0].source_name == "a"


def test_read_input_none_returns_empty() -> None:
    """都不给 → 空列表（cli 走 -m 路径）。"""
    assert read_input(file=None, input_dir=None) == []


# ========== Day4：read_url ==========
from unittest.mock import patch

from mianjing.application.input import read_url


@patch("mianjing.application.input.fetch_url")
def test_read_url_builds_input_item(mock_fetch) -> None:
    """read_url 抓正文，构造 InputItem，source_name 取末段，传 config。"""
    from unittest.mock import MagicMock

    config = MagicMock(timeout=15)
    mock_fetch.return_value = "面试官问了 Redis"
    item = read_url("https://nowcoder.com/discuss/12345", config)
    assert item.raw_text == "面试官问了 Redis"
    assert item.source_name == "12345"
    mock_fetch.assert_called_once_with("https://nowcoder.com/discuss/12345", config)


@patch("mianjing.application.input.fetch_url")
def test_read_url_no_path_source_name_url(mock_fetch) -> None:
    """URL 无末段 → source_name=url。"""
    from unittest.mock import MagicMock

    config = MagicMock(timeout=20)
    mock_fetch.return_value = "正文"
    item = read_url("https://nowcoder.com/", config)
    assert item.source_name == "url"


# ========== Day5：剥 BOM ==========
def test_read_single_file_strips_bom(tmp_path: Path) -> None:
    """带 UTF-8 BOM 的文件，读出来正文不应含 BOM。"""
    f = tmp_path / "bom.txt"
    # 写带 BOM 的内容（﻿ 是 BOM）
    f.write_bytes("﻿面试官问了 Redis".encode("utf-8"))
    item = read_single_file(f)
    assert not item.raw_text.startswith("﻿")
    assert item.raw_text == "面试官问了 Redis"


def test_read_input_dir_strips_bom(tmp_path: Path) -> None:
    """目录读文件也剥 BOM。"""
    f = tmp_path / "b.txt"
    f.write_bytes("﻿内容".encode("utf-8"))
    items = read_input_dir(tmp_path)
    assert items[0].raw_text == "内容"
