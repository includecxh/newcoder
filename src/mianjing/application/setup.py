"""首次启动交互式引导：收集 LLM 配置写入 .env。

当检测到 LLM_API_KEY 未配置时，引导用户在 CLI 输入 key 和必需配置，
写入本地 .env（已被 .gitignore 排除）。
"""
from __future__ import annotations

from pathlib import Path

from mianjing.config import DEFAULT_BASE_URL, DEFAULT_MODEL


def _ask(prompt: str, default: str | None = None) -> str:
    """问一个问题。

    Args:
        prompt: 提示语。
        default: 给默认值时回车用默认（可空）；None 表示必填，空则重问。

    Returns:
        用户输入值（去掉首尾空白）。
    """
    if default is not None:
        raw = input(f"{prompt}（回车用默认 {default}）：")
        return raw.strip() or default
    while True:
        raw = input(f"{prompt}（必填）：")
        v = raw.strip()
        if v:
            return v
        print("  ⚠️ 不能为空，请重新输入")


def setup_wizard(env_path: Path | str = ".env") -> bool:
    """交互式收集 LLM 配置并写入 .env。

    Args:
        env_path: .env 文件路径，默认项目根 .env。

    Returns:
        True 配置完成可继续；False 用户取消（Ctrl+C）。
    """
    env_path = Path(env_path)
    print("\n👋 欢迎使用牛客面经自动整理器！检测到尚未配置 LLM。")
    print("请准备你的 LLM 服务信息（任何 OpenAI 兼容的网关或服务方）。\n")
    try:
        api_key = _ask("请输入 LLM API key")
        base_url = _ask("请输入网关地址", DEFAULT_BASE_URL)
        model = _ask("请输入模型名", DEFAULT_MODEL)
    except (KeyboardInterrupt, EOFError):
        print("\n已取消配置。")
        return False

    content = (
        f"LLM_API_KEY={api_key}\n"
        f"LLM_BASE_URL={base_url}\n"
        f"LLM_MODEL={model}\n"
    )
    env_path.write_text(content, encoding="utf-8")
    print(f"\n✅ 配置已写入 {env_path}（已被 gitignore，不会提交）。")
    print("继续运行...\n")
    return True
