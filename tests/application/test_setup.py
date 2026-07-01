"""setup_wizard 测试：mock input 验证收集与写 .env。"""
from pathlib import Path
from unittest.mock import patch

from mianjing.application.setup import setup_wizard


@patch("builtins.input", side_effect=["mykey", "", ""])
def test_setup_wizard_writes_env_with_defaults(mock_input, tmp_path: Path) -> None:
    """key 输入，base_url/model 回车用默认。"""
    env_path = tmp_path / ".env"
    ok = setup_wizard(env_path=env_path)
    assert ok is True
    content = env_path.read_text(encoding="utf-8")
    assert "LLM_API_KEY=mykey" in content
    assert "your-llm-gateway.example.com" in content  # 默认 base_url
    assert "your-model-name" in content  # 默认 model


@patch("builtins.input", side_effect=["", "realkey", "", ""])
def test_setup_wizard_reasks_empty_key(mock_input, tmp_path: Path) -> None:
    """key 空 → 重问。"""
    env_path = tmp_path / ".env"
    ok = setup_wizard(env_path=env_path)
    assert ok is True
    assert "LLM_API_KEY=realkey" in env_path.read_text(encoding="utf-8")


@patch("builtins.input", side_effect=["custom-key", "https://my.gw/v1", "gpt-4"])
def test_setup_wizard_uses_custom_values(mock_input, tmp_path: Path) -> None:
    """用户自定义三项。"""
    env_path = tmp_path / ".env"
    setup_wizard(env_path=env_path)
    content = env_path.read_text(encoding="utf-8")
    assert "LLM_API_KEY=custom-key" in content
    assert "LLM_BASE_URL=https://my.gw/v1" in content
    assert "LLM_MODEL=gpt-4" in content


@patch("builtins.input", side_effect=KeyboardInterrupt())
def test_setup_wizard_returns_false_on_cancel(mock_input, tmp_path: Path) -> None:
    """用户 Ctrl+C → 返回 False，不写 .env。"""
    env_path = tmp_path / ".env"
    ok = setup_wizard(env_path=env_path)
    assert ok is False
    assert not env_path.exists()
