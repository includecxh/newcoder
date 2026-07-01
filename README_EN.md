# Mianjing Auto-Compiler

> English | [简体中文](./README.md)

Input interview experience text from Nowcoder (via text, file, directory, or URL), automatically extract the questions, answer each one with an LLM, and compile everything into a structured Markdown note saved locally. Saves you from the repetitive chore of manually organizing interview notes and searching for answers one by one.

## Features

- **Four input methods**: text `-m`, single file `--input`, directory batch `--input-dir`, URL fetch `--url`
- **Two-step pipeline**: the LLM first extracts a question list (JSON), then answers each — the process is visible and controllable
- **Two modes**: `low` batch answer in one call (fast, cheap) / `high` answer each question separately (high quality)
- **Normalized Markdown**: auto-generated title, metadata, table of contents, and structured Q&A
- **429 rate-limit retry**: exponential backoff on rate limits; batch processing won't be interrupted
- **Skip-on-failure + summary**: a single failure won't break the whole batch
- **First-run wizard**: on first run with no config, interactively guides you to enter credentials and writes `.env`
- **Configurable**: `config.yaml` controls defaults — tune without touching code

## Installation

Requires Python 3.10+.

```bash
git clone https://github.com/includecxh/newcoder.git
cd newcoder
pip install -e .
```

## Quick Start

After installation, just run any command. On first run with no LLM credentials configured, an interactive wizard launches automatically:

```bash
mianjing -m "Q1: Why is Redis fast?"
```

The wizard asks for (API key required, the rest can use defaults via Enter):

```
👋 Welcome to Mianjing Auto-Compiler! No LLM config detected.
Enter LLM API key (required): sk-xxxx
Enter gateway URL (Enter for default https://your-llm-gateway.example.com/v1):
Enter model name (Enter for default your-model-name):
✅ Config written to .env (excluded by gitignore).
```

Config is written to the local `.env`, then the command continues automatically and won't ask again. You can also skip the wizard and fill in `.env` manually per the Configuration section below.

## Configuration

### 1. LLM credentials (.env, not committed)

Can be auto-written by the first-run wizard, or manually: copy `.env.example` to `.env` and fill in (any OpenAI-compatible gateway or provider):

```env
LLM_API_KEY=your_api_key
LLM_BASE_URL=https://your-llm-gateway.example.com/v1
LLM_MODEL=your-model-name
```

> `.env` is excluded by `.gitignore` and will never be committed. Do not hardcode keys in code.

### 2. Non-sensitive defaults (config.yaml, committable)

The `config.yaml` at the repo root controls runtime defaults — edit your local copy:

```yaml
output_dir: output       # output directory
default_mode: low        # default mode low/high
max_retries: 3           # 429 retry count
retry_backoff: [1, 2, 4] # backoff seconds
timeout: 15              # URL fetch timeout
fetch_backend: requests  # fetch backend requests | playwright
chrome_path: ""          # chrome.exe path for the playwright backend
```

> CLI flags take precedence over config.yaml (e.g., `--mode high` overrides `default_mode`).

## Usage

```bash
# Paste text
mianjing -m "Q1: Why is Redis fast? Q2: TCP three-way handshake"

# Single file
mianjing --input redis.txt --mode high

# Batch directory (one md per file, skip-on-failure + summary)
mianjing --input-dir ./mianjings/

# URL fetch
mianjing --url https://example.com/some-interview
```

Output goes to the `output/` directory, named `sourcename_timestamp.md`.

> If the `mianjing` command is not on PATH, use `python -m mianjing.interfaces.cli.main ...`, or add the Python Scripts directory to PATH.

## About URL Fetching (requests vs playwright)

- **requests backend** (default): lightweight, suitable for normal websites.
- **playwright backend**: uses a headless browser to render JS content and bypass some WAFs. Set `fetch_backend: playwright` and fill `chrome_path` in `config.yaml` (pointing to an existing chrome.exe — no extra kernel download needed).

> Fetching is intended only for the "fetch a single page by URL" scenario, triggered manually and at low frequency. Please respect the target site's robots policy and terms of service; for personal learning use only.

## Architecture

A four-layer layered architecture (dependencies flow strictly downward). See [ARCHITECTURE.md](./ARCHITECTURE.md).

```
interfaces/cli      CLI entry (arg parsing, source dispatch, summary)
application          application layer (compile_service orchestration, formatter, input)
domain               domain layer (data structures: Mianjing/Question/Answer)
infrastructure       infrastructure (llm_gateway, llm_parser, md_writer,
                     url_fetcher/browser_fetcher)
```

## Tests

```bash
pytest
```

## Tech Stack

Python 3.10+, openai (OpenAI-compatible), python-dotenv, requests, beautifulsoup4, playwright (optional), PyYAML, pytest.

## Uninstall

This tool writes nothing to system directories outside the install, so a clean uninstall is straightforward:

```bash
# 1. Remove the package and the `mianjing` command (entry script is removed too)
pip uninstall mianjing
```

Then delete the cloned project directory — this takes everything else with it (`.env`, `config.yaml`, `output/`, source, `__pycache__`, `*.egg-info`):

```bash
# 2. Delete the project directory
Remove-Item -Recurse -Force newcoder     # Windows PowerShell
rm -rf newcoder                          # macOS / Linux
```

Optional cleanup:

```bash
# 3. Clear the pip download cache (optional)
pip cache purge
```

## License & Disclaimer

- For personal learning use only.
- When using the scraping feature, please comply with the target site's rules. The author is not responsible for misuse.
- Keep your own API keys safe.
