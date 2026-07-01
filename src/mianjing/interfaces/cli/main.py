"""命令行入口：解析参数 → 编排 → 打印结果。

用法:
    python -m mianjing.interfaces.cli.main -m "面经文本"
    echo "面经文本" | python -m mianjing.interfaces.cli.main
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from mianjing.application.compile_service import compile_batch, compile_mianjing
from mianjing.application.input import read_input, read_url
from mianjing.application.setup import setup_wizard
from mianjing.config import is_configured, load_config


def main(argv: list[str] | None = None) -> int:
    """命令行入口。

    Returns:
        0 成功，非 0 失败。
    """
    # Windows 控制台默认 GBK 编码，无法打印 emoji，强制 utf-8 输出
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")

    # 首启检测：未配置 LLM_API_KEY → 交互式引导写入 .env
    if not is_configured():
        if not setup_wizard():
            return 1

    parser = argparse.ArgumentParser(
        prog="mianjing",
        description="牛客面经自动整理器：粘贴面经，自动拆问题+回答，存成 md",
    )
    parser.add_argument("-m", "--mianjing", help="面经文本（与 --input/--input-dir 互斥）")
    parser.add_argument("-i", "--input", help="单个 .txt 面经文件")
    parser.add_argument("-d", "--input-dir", help="含多个 .txt 的目录（批量）")
    parser.add_argument("--url", help="面经 URL（抓取单篇公开页）")
    parser.add_argument(
        "-o", "--output",
        default=None,
        help="md 输出目录（默认用 config.yaml 的 output_dir）",
    )
    parser.add_argument(
        "--mode",
        choices=["low", "high"],
        default=None,
        help="low=批量一次回答(快)；high=逐题调用(高质量)（默认用 config.yaml 的 default_mode）",
    )
    args = parser.parse_args(argv)

    # stdin 兜底：-m 没给但管道有输入则读 stdin（pytest 捕获下 stdin 不可读，try 兜底）
    raw_text = args.mianjing
    if not raw_text and not sys.stdin.isatty():
        try:
            raw_text = sys.stdin.read()
        except OSError:
            raw_text = ""
    args.mianjing = raw_text

    # 来源互斥校验
    sources = sum(1 for x in (args.mianjing, args.input, args.input_dir, args.url) if x)
    if sources != 1:
        print("用法: 请指定且仅指定一个输入来源：")
        print("  -m \"文本\"  |  --input 文件.txt  |  --input-dir 目录/  |  --url URL")
        print("  [--mode low|high] [-o 输出目录]")
        return 1

    try:
        config = load_config()
    except RuntimeError as e:
        print(f"❌ 错误: {e}", file=sys.stderr)
        return 1

    # 命令行未给则用 config 默认值（命令行优先于配置文件）
    output_dir = Path(args.output) if args.output else Path(config.output_dir)
    mode = args.mode if args.mode else config.default_mode

    # 分流：-m 文本 → 单篇；url → 抓取；文件/目录 → 批量
    if args.mianjing:
        return _run_single(args.mianjing, config, output_dir, mode)

    if args.url:
        try:
            items = [read_url(args.url, config)]
        except RuntimeError as e:
            print(f"❌ 错误: {e}", file=sys.stderr)
            return 1
    else:
        try:
            items = read_input(
                file=Path(args.input) if args.input else None,
                input_dir=Path(args.input_dir) if args.input_dir else None,
            )
        except (FileNotFoundError, NotADirectoryError) as e:
            print(f"❌ 错误: {e}", file=sys.stderr)
            return 1

    if not items:
        print("ℹ️ 目录下没有 .txt 文件")
        return 0

    results = compile_batch(items, config=config, output_dir=output_dir, mode=mode)
    return _print_summary(results, mode)


def _run_single(raw_text: str, config, output_dir: Path, mode: str) -> int:
    """单篇（-m 文本）处理。"""
    try:
        result_path = compile_mianjing(
            raw_text, config=config, output_dir=output_dir, mode=mode,
        )
    except RuntimeError as e:
        print(f"❌ 错误: {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"❌ 错误: {e}", file=sys.stderr)
        return 1
    print(f"✅ 已保存到 {result_path}（模式 {mode}）")
    return 0


def _print_summary(results: list, mode: str) -> int:
    """打印批量汇总，返回退出码（全失败非0）。"""
    ok = [r for r in results if r.success]
    fail = [r for r in results if not r.success]
    print(f"\n===== 汇总（模式 {mode}）=====")
    print(f"成功 {len(ok)} 篇，失败 {len(fail)} 篇，共 {len(results)} 篇")
    if ok:
        print("\n✅ 成功：")
        for r in ok:
            print(f"  {r.source_name} → {r.output_path}")
    if fail:
        print("\n❌ 失败：")
        for r in fail:
            print(f"  {r.source_name} → {r.error}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
