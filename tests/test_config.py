"""config 测试：load_config 读 yaml+env 合并、yaml 不存在用默认。"""
from pathlib import Path
from unittest.mock import patch

import pytest

from mianjing.config import Config, load_config


def _write_yaml(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


@patch.dict("os.environ", {
    "LLM_API_KEY": "test-key",
    "LLM_BASE_URL": "https://gw.example.com/v1",
    "LLM_MODEL": "test-model",
}, clear=False)
def test_load_config_reads_yaml(tmp_path: Path) -> None:
    """yaml 存在 → 读 yaml 填非敏感 + env 填 key。"""
    yaml_path = tmp_path / "config.yaml"
    _write_yaml(yaml_path, """
output_dir: my_out
default_mode: high
max_retries: 5
retry_backoff: [2, 4, 8]
timeout: 30
""")
    config = load_config(yaml_path)

    assert config.api_key == "test-key"
    assert config.base_url == "https://gw.example.com/v1"
    assert config.model == "test-model"
    assert config.output_dir == "my_out"
    assert config.default_mode == "high"
    assert config.max_retries == 5
    assert config.retry_backoff == [2, 4, 8]
    assert config.timeout == 30


@patch.dict("os.environ", {"LLM_API_KEY": "test-key"}, clear=False)
def test_load_config_yaml_missing_uses_defaults(tmp_path: Path) -> None:
    """yaml 不存在 → 用代码默认值（向后兼容）。"""
    config = load_config(tmp_path / "nope.yaml")

    assert config.api_key == "test-key"
    assert config.output_dir == "output"
    assert config.default_mode == "low"
    assert config.max_retries == 3
    assert config.retry_backoff == [1, 2, 4]
    assert config.timeout == 15


def test_load_config_missing_key_raises(tmp_path: Path) -> None:
    """key 未配置 → RuntimeError。"""
    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(RuntimeError):
            load_config(tmp_path / "nope.yaml")


@patch.dict("os.environ", {"LLM_API_KEY": "k"}, clear=False)
def test_load_config_partial_yaml_keeps_defaults(tmp_path: Path) -> None:
    """yaml 只配部分字段 → 缺的用默认。"""
    yaml_path = tmp_path / "config.yaml"
    _write_yaml(yaml_path, "default_mode: high\n")
    config = load_config(yaml_path)

    assert config.default_mode == "high"
    assert config.max_retries == 3  # 缺的用默认
    assert config.output_dir == "output"


def test_config_is_dataclass_with_defaults() -> None:
    """Config dataclass 有默认值。"""
    c = Config(api_key="k", base_url="u", model="m")
    assert c.output_dir == "output"
    assert c.default_mode == "low"
    assert c.max_retries == 3
    assert c.retry_backoff == [1, 2, 4]
    assert c.timeout == 15


# ========== Playwright fetcher：fetch_backend/chrome_path ==========
@patch.dict("os.environ", {"LLM_API_KEY": "k"}, clear=False)
def test_load_config_default_fetch_backend(tmp_path: Path) -> None:
    """默认 fetch_backend=requests，chrome_path 空。"""
    config = load_config(tmp_path / "nope.yaml")
    assert config.fetch_backend == "requests"
    assert config.chrome_path == ""


@patch.dict("os.environ", {"LLM_API_KEY": "k"}, clear=False)
def test_load_config_reads_playwright_backend(tmp_path: Path) -> None:
    """yaml 配 fetch_backend=playwright + chrome_path。"""
    yaml_path = tmp_path / "config.yaml"
    _write_yaml(yaml_path, """
fetch_backend: playwright
chrome_path: "C:/some/chrome.exe"
""")
    config = load_config(yaml_path)
    assert config.fetch_backend == "playwright"
    assert config.chrome_path == "C:/some/chrome.exe"
