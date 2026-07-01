"""pytest 全局配置：把 src 加入 import 路径 + 默认 mock 已配置状态。

注：项目已 pip install -e . 可编辑安装，conftest 作为双保险，
确保即使未安装也能从 src 导入。
"""
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

SRC = Path(__file__).parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


@pytest.fixture(autouse=True)
def _mock_configured():
    """默认让 is_configured 返回 True，使现有 cli 测试跳过首启引导。

    首启专用测试可在此 fixture 之上再 patch is_configured 为 False。
    """
    with patch("mianjing.interfaces.cli.main.is_configured", return_value=True):
        yield
