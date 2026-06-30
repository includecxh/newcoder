"""浏览器抓取器：用 Playwright 无头浏览器抓 JS 渲染后的 HTML。

绕过 requests 遇到的 WAF（Day4 实测坑，可行性探查已验证可绕）。
复用 chrome_path 指向的 chrome.exe，省去下载 playwright 自带内核（约 150MB）。
"""
from __future__ import annotations


def fetch_html_playwright(url: str, chrome_path: str, timeout: int = 15) -> str:
    """用 Playwright 无头浏览器抓 URL，返回渲染后 HTML。

    Args:
        url: 目标 URL。
        chrome_path: chrome.exe 路径（复用系统已有浏览器内核）。
        timeout: 页面加载超时秒数。

    Returns:
        渲染后的 HTML 字符串。

    Raises:
        RuntimeError: chrome_path 空、浏览器启动失败、页面错误。
    """
    if not chrome_path:
        raise RuntimeError(
            "fetch_backend=playwright 但未配置 chrome_path，请在 config.yaml 设置"
        )
    from playwright.sync_api import sync_playwright

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, executable_path=chrome_path)
            page = browser.new_page()
            try:
                page.goto(url, wait_until="networkidle", timeout=timeout * 1000)
                page.wait_for_timeout(3000)  # 等 JS 渲染
                return page.content()
            finally:
                browser.close()
    except RuntimeError:
        raise
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(f"Playwright 抓取失败（{url}）: {e}") from e
