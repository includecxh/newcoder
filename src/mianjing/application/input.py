"""输入来源解析：把文件/目录来源收敛成 list[InputItem]。

统一三种入口（-m文本/--input文件/--input-dir目录）为输入项列表，
其中文本项由 cli 直接构造，文件/目录项由本模块读取。
"""
from __future__ import annotations

from pathlib import Path

from mianjing.domain.models import InputItem
from mianjing.infrastructure.url_fetcher import extract_source_name, fetch_url


def read_single_file(file: Path) -> InputItem:
    """读单个 .txt 文件为输入项。

    source_name 取文件名 stem（去扩展名）。

    Raises:
        FileNotFoundError: 文件不存在。
    """
    if not file.exists():
        raise FileNotFoundError(f"文件不存在: {file}")
    raw_text = file.read_text(encoding="utf-8-sig")
    return InputItem(raw_text=raw_text, source_name=file.stem)


def read_input_dir(input_dir: Path) -> list[InputItem]:
    """列目录读所有 .txt（一层，不递归）。

    Raises:
        NotADirectoryError: 路径不是目录。
    """
    if not input_dir.is_dir():
        raise NotADirectoryError(f"不是目录: {input_dir}")
    items: list[InputItem] = []
    for f in sorted(input_dir.iterdir()):
        if f.is_file() and f.suffix == ".txt":
            items.append(InputItem(raw_text=f.read_text(encoding="utf-8-sig"), source_name=f.stem))
    return items


def read_input(file: Path | None, input_dir: Path | None) -> list[InputItem]:
    """根据来源解析为输入项列表。

    - file 给定：读单文件 → 1 项
    - input_dir 给定：列目录 → N 项
    - 都不给：返回空（cli 走 -m 文本路径）

    Raises:
        FileNotFoundError / NotADirectoryError: 由子函数透传。
    """
    if file is not None:
        return [read_single_file(file)]
    if input_dir is not None:
        return read_input_dir(input_dir)
    return []


def read_url(url: str, config) -> InputItem:
    """抓取 URL，返回 InputItem。

    source_name 取 URL 路径末段（无末段则 'url'）。
    抓取后端由 config.fetch_backend 决定（requests/playwright）。

    Args:
        url: 目标 URL。
        config: 应用配置（传给 fetch_url 选后端）。

    Raises:
        RuntimeError: 由 fetcher 透传。
    """
    raw_text = fetch_url(url, config)
    source_name = extract_source_name(url)
    return InputItem(raw_text=raw_text, source_name=source_name)
