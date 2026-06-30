"""url_fetcher 测试：extract_text/extract_source_name 纯函数 + fetch_url 后端分流。"""
from unittest.mock import MagicMock, patch

import pytest

from mianjing.infrastructure.url_fetcher import (
    extract_source_name,
    extract_text,
    fetch_url,
)


def test_extract_text_removes_script_style() -> None:
    """去 script/style，保留正文。"""
    html = """
    <html><body>
      <script>alert('x')</script>
      <style>.a{color:red}</style>
      <p>面试官问了 Redis 持久化</p>
      <p>RDB 和 AOF 区别</p>
    </body></html>
    """
    text = extract_text(html)
    assert "alert" not in text
    assert "color" not in text
    assert "面试官问了 Redis 持久化" in text
    assert "RDB 和 AOF 区别" in text


def test_extract_text_collapses_whitespace() -> None:
    """合并多余空白。"""
    html = "<html><body><p>第一段</p><p>第二段</p></body></html>"
    text = extract_text(html)
    assert "第一段" in text
    assert "第二段" in text
    # 不应有连续多个空行
    assert "\n\n\n" not in text


def test_extract_text_empty_html() -> None:
    """空 HTML 返回空字符串。"""
    assert extract_text("") == ""
    assert extract_text("<html></html>").strip() == ""


def test_extract_source_name_from_path() -> None:
    """取 URL 路径末段。"""
    assert extract_source_name("https://nowcoder.com/discuss/12345") == "12345"


def test_extract_source_name_strips_query() -> None:
    """去 query。"""
    assert extract_source_name("https://nowcoder.com/discuss/12345?type=0&orderBy=0") == "12345"


def test_extract_source_name_no_path_fallback() -> None:
    """无末段 → url 兜底。"""
    assert extract_source_name("https://nowcoder.com/") == "url"
    assert extract_source_name("https://nowcoder.com") == "url"


def test_extract_source_name_special_chars_kept() -> None:
    """末段含特殊字符保留。"""
    assert extract_source_name("https://nowcoder.com/discuss/面经-abc") == "面经-abc"


# ========== Playwright 后端分流 ==========
@patch("mianjing.infrastructure.url_fetcher.extract_text")
@patch("mianjing.infrastructure.url_fetcher.fetch_html")
def test_fetch_url_requests_backend(mock_fetch_html, mock_extract) -> None:
    """fetch_backend=requests → 调 fetch_html（requests），不调 playwright。"""
    mock_fetch_html.return_value = "<html>requests</html>"
    mock_extract.return_value = "正文"
    config = MagicMock(fetch_backend="requests", chrome_path="x", timeout=15)

    result = fetch_url("https://example.com", config)

    mock_fetch_html.assert_called_once_with("https://example.com", 15)
    assert result == "正文"


@patch("mianjing.infrastructure.url_fetcher.extract_text")
@patch("mianjing.infrastructure.url_fetcher.fetch_html_playwright")
def test_fetch_url_playwright_backend(mock_fetch_pw, mock_extract) -> None:
    """fetch_backend=playwright → 调 fetch_html_playwright，传 chrome_path。"""
    mock_fetch_pw.return_value = "<html>pw</html>"
    mock_extract.return_value = "正文"
    config = MagicMock(
        fetch_backend="playwright",
        chrome_path="C:/chrome.exe",
        timeout=20,
    )

    result = fetch_url("https://nowcoder.com/x", config)

    mock_fetch_pw.assert_called_once_with(
        "https://nowcoder.com/x", "C:/chrome.exe", 20
    )
    assert result == "正文"


@patch("mianjing.infrastructure.url_fetcher.fetch_html_playwright")
def test_fetch_url_playwright_missing_chrome_path_raises(mock_fetch_pw) -> None:
    """fetch_backend=playwright 但 chrome_path 空 → browser_fetcher 抛错透传。"""
    config = MagicMock(fetch_backend="playwright", chrome_path="", timeout=15)
    mock_fetch_pw.side_effect = RuntimeError("未配置 chrome_path")
    with pytest.raises(RuntimeError, match="chrome_path"):
        fetch_url("https://x.com", config)
