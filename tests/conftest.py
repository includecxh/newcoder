"""pytest 全局配置：把 src 加入 import 路径。

注：项目已 pip install -e . 可编辑安装，conftest 作为双保险，
确保即使未安装也能从 src 导入。
"""
import sys
from pathlib import Path

SRC = Path(__file__).parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
