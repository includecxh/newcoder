"""md 文件写入器：把 markdown 文本写到 output 目录。

时间戳命名，避免覆盖。"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path


def write_markdown(
    content: str,
    output_dir: Path,
    source_name: str | None = None,
) -> Path:
    """把 markdown 内容写到文件，返回文件路径。

    文件名：
    - source_name 有值：{source_name}_{YYYY-MM-DD_HHmmss}.md
    - source_name 为 None：{YYYY-MM-DD_HHmmss}.md（Day2 向后兼容）

    Args:
        content: markdown 文本。
        output_dir: 输出目录，不存在则创建。
        source_name: 来源名（文件名stem/inline），可选。

    Returns:
        写入的文件 Path。
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    if source_name:
        filename = f"{source_name}_{timestamp}.md"
    else:
        filename = f"{timestamp}.md"
    output_path = output_dir / filename
    output_path.write_text(content, encoding="utf-8")
    return output_path
