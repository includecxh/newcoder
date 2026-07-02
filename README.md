# 牛客面经自动整理器

> [English](./README_EN.md) | 简体中文

输入牛客面经文本（或文件、目录、URL），自动拆出问题、逐个调用大模型回答，整理成结构化 Markdown 笔记存到本地。省掉「手动整理面经 + 逐个搜答案」的重复劳动。

## 安装

需要 Python 3.10+。

```bash
git clone https://github.com/includecxh/newcoder.git
cd newcoder
pip install -e .
```

## 快速开始

安装后直接运行任意命令即可。首次运行时若检测到尚未配置 LLM 密钥，会自动进入交互式引导：

```bash
mianjing -m "面试官问了：1. Redis为什么快"
```

配置写入本地 `.env` 后自动继续运行，之后不再询问。也可以跳过引导，手动按下方「配置」章节填写 `.env`。

## 配置

### 1. LLM 密钥（.env，不入库）

可由首次运行的交互式引导自动写入，或手动复制 `.env.example` 为 `.env` 填入（任何 OpenAI 兼容的网关或服务方）：

```env
LLM_API_KEY=your_api_key
LLM_BASE_URL=https://your-llm-gateway.example.com/v1
LLM_MODEL=your-model-name
# playwright 后端用的 chrome.exe 路径（仅 fetch_backend=playwright 时填；留空走 config.yaml）
CHROME_PATH=
```

### 2. 非敏感默认值（config.yaml，可入库）

项目根的 `config.yaml` 管控运行默认值，可直接改本地副本：

```yaml
output_dir: output       # 输出目录
default_mode: low        # 默认模式 low/high
max_retries: 3           # 429 重试次数
retry_backoff: [1, 2, 4] # 退避秒数
timeout: 15              # URL 抓取超时
fetch_backend: requests  # 抓取后端 requests | playwright
chrome_path: ""          # playwright 后端 chrome.exe 路径（优先读 .env 的 CHROME_PATH，留空则用此处）
```

> 命令行参数优先于 config.yaml（如 `--mode high` 覆盖 `default_mode`）。

## 用法

```bash
# 粘贴文本
mianjing -m "面试官问了：1. Redis为什么快 2. TCP三次握手"

# 单文件
mianjing --input redis.txt --mode high

# 批量目录（每篇一个 md，失败跳过 + 汇总）
mianjing --input-dir ./mianjings/

# URL 抓取
mianjing --url https://example.com/some-interview
```

输出到 `output/` 目录，文件名 `源名_时间戳.md`。

> 若 `mianjing` 命令不在 PATH，用 `python -m mianjing.interfaces.cli.main ...`，或将 Python Scripts 目录加入 PATH。

## 关于 URL 抓取（requests vs playwright）

- **requests 后端**（默认）：轻量，适合普通网站。
- **playwright 后端**：用无头浏览器抓 JS 渲染内容、绕过部分 WAF。需在 `config.yaml` 设 `fetch_backend: playwright`，并填 `chrome_path`（指向已有的 chrome.exe，无需额外下载内核）。`chrome_path` 优先读 `.env` 的 `CHROME_PATH`（本机路径不入库），留空则用 config.yaml。

> 抓取仅用于「给 URL 抓单篇」场景，手动触发、低频。请遵守目标网站的 robots 协议与服务条款，仅供个人学习使用。

## 架构

采用四层分层架构（依赖单向向下），详见 [ARCHITECTURE.md](./ARCHITECTURE.md)。

```
interfaces/cli      命令行入口（参数解析、来源收敛、汇总）
application          应用层（compile_service 编排、formatter 格式化、input 输入解析）
domain               领域层（Mianjing/Question/Answer 等数据结构）
infrastructure       基础设施（llm_gateway 调 LLM、llm_parser 解析 JSON、
                     md_writer 写文件、url_fetcher/browser_fetcher 抓取）
```

## 测试

```bash
pytest
```

## 技术栈

Python 3.10+、openai（OpenAI 兼容）、python-dotenv、requests、beautifulsoup4、playwright（可选）、PyYAML、pytest。

## 卸载

本工具不会向系统目录写入额外文件，卸载可做到无残留：

```bash
# 1. 卸载包与 mianjing 命令（同时移除入口脚本）
pip uninstall mianjing
```

随后删除克隆下来的项目目录即可带走其余所有文件（`.env`、`config.yaml`、`output/`、源码、`__pycache__`、`*.egg-info`）：

```bash
# 2. 删除项目目录
Remove-Item -Recurse -Force newcoder     # Windows PowerShell
rm -rf newcoder                          # macOS / Linux
```

可选清理：

```bash
# 3. 清 pip 下载缓存（可选）
pip cache purge
```

## 许可与免责

- 仅供个人学习使用。
- 使用爬虫功能时请遵守目标网站规则，作者不对滥用行为负责。
- 请妥善保管自己的 API 密钥。
