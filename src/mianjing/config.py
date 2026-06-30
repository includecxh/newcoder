"""配置：读 config.yaml（非敏感）+ .env（key）合并为 Config。

分工：config.yaml 入库放非敏感默认值；.env 不入库放 LLM_API_KEY。
遵循 PROJECT_CONVENTIONS.md 5.4：密钥绝不入库。
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# 代码内置默认值（yaml 不存在/缺字段时用）
DEFAULT_OUTPUT_DIR = "output"
DEFAULT_MODE = "low"
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_BACKOFF = [1, 2, 4]
DEFAULT_TIMEOUT = 15


@dataclass
class Config:
    """应用配置。"""

    api_key: str
    base_url: str
    model: str
    output_dir: str = DEFAULT_OUTPUT_DIR
    default_mode: str = DEFAULT_MODE
    max_retries: int = DEFAULT_MAX_RETRIES
    retry_backoff: list[int] = field(default_factory=lambda: list(DEFAULT_RETRY_BACKOFF))
    timeout: int = DEFAULT_TIMEOUT
    fetch_backend: str = "requests"  # requests | playwright
    chrome_path: str = ""  # playwright 后端用的 chrome.exe 路径


def _read_yaml(yaml_path: Path) -> dict:
    """读 yaml 为 dict，不存在返回空 dict。"""
    if not yaml_path.exists():
        return {}
    import yaml

    with open(yaml_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data or {}


def load_config(yaml_path: Path | str | None = None) -> Config:
    """读 yaml（非敏感）+ env（key）合并为 Config。

    Args:
        yaml_path: config.yaml 路径，None 则用项目根默认 config.yaml。

    Returns:
        Config 实例。

    Raises:
        RuntimeError: LLM_API_KEY 未配置。
    """
    if yaml_path is None:
        yaml_path = Path("config.yaml")
    yaml_path = Path(yaml_path)
    cfg = _read_yaml(yaml_path)

    api_key = os.environ.get("LLM_API_KEY", "")
    if not api_key:
        raise RuntimeError(
            "未配置 LLM_API_KEY，请在 .env 文件中设置（参考 .env.example）"
        )
    base_url = os.environ.get("LLM_BASE_URL", "https://your-llm-gateway.example.com/v1")
    model = os.environ.get("LLM_MODEL", "your-model-name")

    return Config(
        api_key=api_key,
        base_url=base_url,
        model=model,
        output_dir=cfg.get("output_dir", DEFAULT_OUTPUT_DIR),
        default_mode=cfg.get("default_mode", DEFAULT_MODE),
        max_retries=cfg.get("max_retries", DEFAULT_MAX_RETRIES),
        retry_backoff=cfg.get("retry_backoff", list(DEFAULT_RETRY_BACKOFF)),
        timeout=cfg.get("timeout", DEFAULT_TIMEOUT),
        fetch_backend=cfg.get("fetch_backend", "requests"),
        chrome_path=cfg.get("chrome_path", ""),
    )


def mask_key(key: str) -> str:
    """脱敏密钥（遵循 5.3 红线：绝不打印完整 key）。"""
    if len(key) <= 8:
        return "***"
    return f"{key[:4]}...{key[-4:]}"
