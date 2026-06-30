# 架构设计

本文档面向想理解本项目设计与扩展方式的开发者，介绍分层架构、数据流和关键设计决策。

## 项目概览

「牛客面经自动整理器」是一条流水线：输入面经内容 → 拆出问题 → 逐个回答 → 整理成 Markdown → 存到本地。核心是把「整理 + 搜答案」的人工重复劳动自动化，并让每一步可见可控。

## 分层架构

采用四层分层架构，依赖**单向向下**（外层依赖内层，不反向）：

```
interfaces/cli      →  application  →  domain
                          ↘ infrastructure → domain
```

| 层 | 目录 | 职责 |
|----|------|------|
| 入口层 | `interfaces/cli/` | 命令行交互、参数解析、输入来源收敛、结果汇总 |
| 应用层 | `application/` | 流程编排（compile_service）、格式化（formatter）、输入解析（input） |
| 领域层 | `domain/` | 业务数据结构（Mianjing/Question/Answer/InputItem/CompileResult） |
| 基础设施层 | `infrastructure/` | 外部对接：调 LLM（llm_gateway）、解析 JSON（llm_parser）、写文件（md_writer）、抓取（url_fetcher/browser_fetcher） |

### 依赖铁律

- `domain` 只依赖标准库，**不依赖任何层**——业务核心最稳定。
- `infrastructure` 依赖 `domain`（用其数据结构）——允许（向下）。
- `domain` 绝不依赖 `infrastructure`——换 LLM / 换存储方式时，domain 一行不改。

## 核心数据流

以「输入文本 → 输出 md」为例，一次调用穿过的层：

```
命令行输入 (-m / --input / --input-dir / --url)
  ↓
[入口层] cli/main.py
   - 解析参数、来源互斥校验
   - 加载配置 (load_config 读 config.yaml + .env)
   - 文本来源 → 单篇；文件/目录/URL → 批量
  ↓
[应用层] compile_service
   - 两步：先拆问题，再按模式回答
   - low: 批量一次答；high: 逐题答
   - 失败跳过 + 汇总 (compile_batch)
  ↓
[基础设施层]
   - llm_gateway.extract_questions  → 调 LLM 拆问题（返回 JSON）
   - llm_parser.parse_questions     → 容错解析为 list[Question]
   - llm_gateway.answer_*           → 回答（批量或逐题）
   - formatter.format_note          → 拼装规范 md（标题/元信息/目录/问答）
   - md_writer.write_markdown       → 写文件（源名 + 时间戳命名）
  ↓
[领域层] domain/models.py
   - 定义 Mianjing/Question/Answer 等数据结构，被各层引用
```

## 关键设计决策

### 1. 两步拆分（而非一锅烩）
先调 LLM 拆出结构化问题列表（JSON），再逐个回答。相比「一次调用全干完」，问题拆分结果可见可控、可去重、可单独重试，且 Markdown 格式由代码精确控制而非依赖 LLM 守不守规矩。

### 2. JSON 容错解析
LLM 返回的 JSON 常不规范（带代码块标记、前后多余文字）。`llm_parser` 做三步容错：去 ` ```json ` 标记 → 提取首个 `[...]` 段 → `json.loads`，失败带原始返回片段便于排查。

### 3. low / high 模式（调用粒度权衡）
- `low`：批量一次回答（2 次调用，快、省）
- `high`：逐题调用（1+N 次，慢、贵，但答案质量高）
用 `--mode` 参数选择，默认走 config.yaml 的 `default_mode`。

### 4. 429 限流指数退避重试
`_chat` 底层捕获 429，按 `[1,2,4]` 秒退避重试最多 3 次，只重试可恢复错误（429）。重试逻辑放在唯一调 LLM 的底层，所有上层自动受益。等待函数可注入，便于测试不真等。

### 5. 抓取后端可切换（requests / playwright）
`fetch_url` 接口稳定，按 `config.fetch_backend` 选后端：requests（轻量、普通站）或 playwright（无头浏览器、绕 WAF、抓 JS 渲染）。Playwright 复用已有的 chrome.exe（`executable_path`），无需额外下载内核。上层（read_url/cli）零改动。

### 6. 失败隔离
批量处理时每篇用 try/except 包裹，单篇失败记入失败列表、不中断，最后汇总成功/失败清单与退出码。

### 7. 配置分工
- `config.yaml`（入库）：非敏感默认值（输出路径、模式、重试参数等）
- `.env`（不入库）：LLM 密钥

默认值有代码兜底：yaml 不存在或缺字段时用内置默认，向后兼容。命令行参数优先于配置文件。

## 扩展点

- **换 LLM**：改 `.env` 的网关地址和模型名即可（OpenAI 兼容协议），代码不动。
- **换抓取方式**：在 `infrastructure/` 加新 fetcher，`fetch_url` 按配置分流，上层不动。
- **加新输入来源**：在 `application/input.py` 加读取函数，cli 来源校验加一项。
- **加新输出格式**：在 `application/` 加新 formatter，compile_service 选用。

## 技术栈

Python 3.10+、openai（OpenAI 兼容协议）、python-dotenv、requests、beautifulsoup4、playwright（可选后端）、PyYAML、pytest。
