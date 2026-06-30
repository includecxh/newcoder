"""URL 抓取器：按 config 选后端抓 HTML（requests 或 Playwright）+ BeautifulSoup 提取正文。

- requests（默认）：轻量，普通网站够用
- playwright：绕 WAF、抓 JS 渲染（复用 chrome.exe，见 browser_fetcher）
Day4 用 requests 起步，Playwright 后端按 config.fetch_backend 切换。
"""
from __future__ import annotations

from urllib.parse import urlparse

from mianjing.infrastructure.browser_fetcher import fetch_html_playwright

DEFAULT_TIMEOUT = 15

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def extract_text(html: str) -> str:
    """用 BeautifulSoup 从 HTML 提取正文文本。

    通用规则：去 script/style/nav，取 body 文本，合并空白。
    不追求完美准确，靠 LLM 后续拆问题时容错。

    Args:
        html: HTML 字符串。

    Returns:
        正文文本（可能不完美），空 HTML 返回空串。
    """
    if not html or not html.strip():
        return ""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    # 去 non-content 标签
    for tag in soup(["script", "style", "nav", "header", "footer", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    # 合并连续空白
    lines = [line.strip() for line in text.splitlines()]
    lines = [ln for ln in lines if ln]
    return "\n".join(lines)


def extract_source_name(url: str) -> str:
    """从 URL 提取 source_name：路径末段，去 query，无则 'url' 兜底。

    Args:
        url: 完整 URL。

    Returns:
        末段字符串，或 'url'。
    """
    parsed = urlparse(url)
    path = parsed.path.rstrip("/")
    segments = path.split("/")
    last = segments[-1] if segments else ""
    if not last:
        return "url"
    return last


def fetch_html(url: str, timeout: int = DEFAULT_TIMEOUT) -> str:
    """用 requests 抓取 URL，返回 HTML 文本。

    带 User-Agent 头避免基础反爬。

    Raises:
        RuntimeError: 网络/HTTP 错误。
    """
    import requests

    headers = {"User-Agent": USER_AGENT}
    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        raise RuntimeError(f"抓取 URL 失败（{url}）: {e}") from e


def fetch_url(url: str, config) -> str:
    """按 config.fetch_backend 选后端抓 HTML，提取正文。

    Args:
        url: 目标 URL。
        config: 应用配置（取 fetch_backend/chrome_path/timeout）。

    Returns:
        正文文本。
    """
    if config.fetch_backend == "playwright":
        html = fetch_html_playwright(url, config.chrome_path, config.timeout)
    else:
        html = fetch_html(url, config.timeout)
    return extract_text(html)
