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
@patch.dict("os.environ", {"LLM_API_KEY": "k"}, clear=True)
def test_load_config_default_fetch_backend(tmp_path: Path) -> None:
    """默认 fetch_backend=requests，chrome_path 空。"""
    config = load_config(tmp_path / "nope.yaml")
    assert config.fetch_backend == "requests"
    assert config.chrome_path == ""


@patch.dict("os.environ", {"LLM_API_KEY": "k"}, clear=True)
def test_load_config_reads_playwright_backend(tmp_path: Path) -> None:
    """yaml 配 fetch_backend=playwright + chrome_path（env 未设 → 读 yaml）。"""
    yaml_path = tmp_path / "config.yaml"
    _write_yaml(yaml_path, """
fetch_backend: playwright
chrome_path: "C:/some/chrome.exe"
""")
    config = load_config(yaml_path)
    assert config.fetch_backend == "playwright"
    assert config.chrome_path == "C:/some/chrome.exe"


# ========== chrome_path 优先级：env > yaml > 默认空（本机路径走 .env 不入库）==========
@patch.dict("os.environ", {"LLM_API_KEY": "k", "CHROME_PATH": "env_chrome.exe"}, clear=True)
def test_load_config_chrome_path_env_overrides_yaml(tmp_path: Path) -> None:
    """env 设 CHROME_PATH + yaml 设 chrome_path → env 胜出（本机路径优先走 .env）。"""
    yaml_path = tmp_path / "config.yaml"
    _write_yaml(yaml_path, 'chrome_path: "yaml_chrome.exe"\n')
    config = load_config(yaml_path)
    assert config.chrome_path == "env_chrome.exe"


@patch.dict("os.environ", {"LLM_API_KEY": "k"}, clear=True)
def test_load_config_chrome_path_yaml_fallback_when_env_unset(tmp_path: Path) -> None:
    """env 未设 CHROME_PATH + yaml 设 → fallback 读 yaml。"""
    yaml_path = tmp_path / "config.yaml"
    _write_yaml(yaml_path, 'chrome_path: "C:/from/yaml/chrome.exe"\n')
    config = load_config(yaml_path)
    assert config.chrome_path == "C:/from/yaml/chrome.exe"


@patch.dict("os.environ", {"LLM_API_KEY": "k"}, clear=True)
def test_load_config_chrome_path_empty_when_both_unset(tmp_path: Path) -> None:
    """env + yaml 都未设 chrome_path → 空串（playwright 后端会报缺 chrome_path）。"""
    yaml_path = tmp_path / "config.yaml"
    _write_yaml(yaml_path, "fetch_backend: requests\n")
    config = load_config(yaml_path)
    assert config.chrome_path == ""


# ========== 首启引导：is_configured ==========
from mianjing.config import is_configured


@patch.dict("os.environ", {}, clear=True)
def test_is_configured_false_when_no_key() -> None:
    """无 key → False。"""
    assert is_configured() is False


@patch.dict("os.environ", {"LLM_API_KEY": "k"}, clear=True)
def test_is_configured_true_when_key_set() -> None:
    """有 key → True。"""
    assert is_configured() is True


@patch.dict("os.environ", {"LLM_API_KEY": ""}, clear=True)
def test_is_configured_false_when_key_empty() -> None:
    """key 空 → False。"""
    assert is_configured() is False
