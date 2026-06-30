"""cli 测试：用桩 LLM 验证命令行链路与 --mode。"""
from pathlib import Path
from unittest.mock import MagicMock, patch

from mianjing.interfaces.cli.main import main


def _mock_config(**overrides) -> MagicMock:
    """构造带默认属性的 mock config（cli 从 config 读 output_dir/default_mode 等）。"""
    cfg = MagicMock()
    cfg.output_dir = "output"
    cfg.default_mode = "low"
    cfg.max_retries = 3
    cfg.retry_backoff = [1, 2, 4]
    cfg.timeout = 15
    for k, v in overrides.items():
        setattr(cfg, k, v)
    return cfg


@patch("mianjing.interfaces.cli.main.compile_mianjing")
@patch("mianjing.interfaces.cli.main.load_config")
def test_main_low_mode_writes_file(mock_cfg, mock_compile, tmp_path: Path) -> None:
    """--mode low（默认）→ 调 compile_mianjing。"""
    mock_cfg.return_value = _mock_config()
    fake_path = tmp_path / "result.md"
    fake_path.write_text("# x", encoding="utf-8")
    mock_compile.return_value = fake_path

    exit_code = main(["-m", "面经文本", "-o", str(tmp_path)])

    assert exit_code == 0
    args, kwargs = mock_compile.call_args
    mode = kwargs.get("mode", args[3] if len(args) > 3 else "low")
    assert mode == "low"


@patch("mianjing.interfaces.cli.main.compile_mianjing")
@patch("mianjing.interfaces.cli.main.load_config")
def test_main_high_mode_passes_mode(mock_cfg, mock_compile, tmp_path: Path) -> None:
    """--mode high → 传 mode=high。"""
    mock_cfg.return_value = _mock_config()
    fake_path = tmp_path / "result.md"
    fake_path.write_text("# x", encoding="utf-8")
    mock_compile.return_value = fake_path

    exit_code = main(["-m", "面经", "-o", str(tmp_path), "--mode", "high"])

    assert exit_code == 0
    args, kwargs = mock_compile.call_args
    mode = kwargs.get("mode", args[3] if len(args) > 3 else None)
    assert mode == "high"


@patch("sys.stdin.isatty", return_value=True)
def test_main_no_input_prints_usage(_mock, capsys) -> None:
    """无输入 → 打印用法、退出码非 0。"""
    exit_code = main([])
    captured = capsys.readouterr()
    assert exit_code != 0
    assert "用法" in captured.out or "usage" in captured.out.lower()


# ========== Day3：--input / --input-dir + 汇总 ==========
@patch("mianjing.interfaces.cli.main.compile_batch")
@patch("mianjing.interfaces.cli.main.load_config")
def test_main_input_dir_calls_batch_and_prints_summary(
    mock_cfg, mock_batch, tmp_path: Path, capsys,
) -> None:
    """--input-dir → 调 compile_batch，打印汇总。"""
    mock_cfg.return_value = _mock_config()
    d = tmp_path / "src"
    d.mkdir()
    (d / "a.txt").write_text("A", encoding="utf-8")

    from mianjing.domain.models import CompileResult
    mock_batch.return_value = [
        CompileResult(source_name="a", success=True, output_path=tmp_path / "a_x.md"),
    ]

    exit_code = main(["--input-dir", str(d), "-o", str(tmp_path)])

    assert exit_code == 0
    mock_batch.assert_called_once()
    out = capsys.readouterr().out
    assert "成功" in out or "汇总" in out


@patch("mianjing.interfaces.cli.main.compile_batch")
@patch("mianjing.interfaces.cli.main.load_config")
def test_main_input_dir_all_failed_returns_nonzero(
    mock_cfg, mock_batch, tmp_path: Path,
) -> None:
    """批量全失败 → 退出码非 0。"""
    mock_cfg.return_value = _mock_config()
    d = tmp_path / "src"
    d.mkdir()
    (d / "a.txt").write_text("A", encoding="utf-8")

    from mianjing.domain.models import CompileResult
    mock_batch.return_value = [
        CompileResult(source_name="a", success=False, error="LLM失败"),
    ]

    exit_code = main(["--input-dir", str(d), "-o", str(tmp_path)])
    assert exit_code != 0


@patch("mianjing.interfaces.cli.main.compile_batch")
@patch("mianjing.interfaces.cli.main.load_config")
def test_main_multiple_sources_error(mock_cfg, mock_batch, tmp_path: Path, capsys) -> None:
    """同时给 -m 和 --input → 报错。"""
    f = tmp_path / "a.txt"
    f.write_text("A", encoding="utf-8")
    exit_code = main(["-m", "文本", "--input", str(f)])
    assert exit_code != 0
    mock_batch.assert_not_called()


# ========== Day4：--url ==========
@patch("mianjing.interfaces.cli.main.read_url")
@patch("mianjing.interfaces.cli.main.compile_batch")
@patch("mianjing.interfaces.cli.main.load_config")
def test_main_url_calls_batch(mock_cfg, mock_batch, mock_read_url, tmp_path: Path, capsys) -> None:
    """--url → 调 compile_batch，打印汇总。"""
    mock_cfg.return_value = _mock_config()
    from mianjing.domain.models import CompileResult, InputItem
    mock_read_url.return_value = InputItem(raw_text="正文", source_name="12345")
    mock_batch.return_value = [
        CompileResult(source_name="12345", success=True, output_path=tmp_path / "x.md"),
    ]

    exit_code = main(["--url", "https://nowcoder.com/discuss/12345", "-o", str(tmp_path)])

    assert exit_code == 0
    mock_batch.assert_called_once()
    args, kwargs = mock_batch.call_args
    items = args[0] if args else kwargs["items"]
    assert items[0].source_name == "12345"


@patch("mianjing.interfaces.cli.main.compile_batch")
@patch("mianjing.interfaces.cli.main.load_config")
def test_main_url_and_input_mutually_exclusive(mock_cfg, mock_batch, tmp_path: Path) -> None:
    """--url 和 --input 同时给 → 报错。"""
    f = tmp_path / "a.txt"
    f.write_text("A", encoding="utf-8")
    exit_code = main(["--url", "https://x.com/1", "--input", str(f)])
    assert exit_code != 0
    mock_batch.assert_not_called()
