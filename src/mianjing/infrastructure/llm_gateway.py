"""LLM 网关：封装对 GLM（金山云网关，OpenAI 兼容）的调用。

密钥从 Config 读取，绝不硬编码（遵循 PROJECT_CONVENTIONS.md 5.3/5.4）。
"""
from __future__ import annotations

import time

from openai import OpenAI, RateLimitError

from mianjing.config import Config, mask_key
from mianjing.domain.models import Answer, Mianjing, Question

# Day5：429 限流重试配置
MAX_RETRIES = 3
RETRY_BACKOFF = [1, 2, 4]  # 指数退避秒数

PROMPT_TEMPLATE = """\
你是一位资深技术面试官。下面是一段面试面经，请：

1. 从中提取出所有的面试问题
2. 对每个问题给出专业、有条理的回答（答案分点）
3. 把所有问题和答案整理成一个 markdown 文档输出

格式要求：
- 用二级标题分隔每个问题
- 每个问题下用 "### 问题" 和 "### 参考回答" 两段
- 只输出 markdown 内容，不要额外解释

面经内容：
{raw_text}
"""


def build_prompt(mianjing: Mianjing) -> str:
    """构造 LLM prompt。"""
    return PROMPT_TEMPLATE.format(raw_text=mianjing.raw_text)


def answer_and_compile(raw_text: str, config: Config) -> str:
    """调 LLM 拆问题并回答，返回 markdown 文本。

    Args:
        raw_text: 面经原文。
        config: LLM 接入配置。

    Returns:
        LLM 生成的 markdown 文本。

    Raises:
        RuntimeError: 当 LLM 调用失败时（报错中 key 已脱敏）。
    """
    from openai import OpenAI  # 延迟导入，避免无 key 时模块导入失败

    prompt = build_prompt(Mianjing(raw_text=raw_text))
    client = OpenAI(api_key=config.api_key, base_url=config.base_url)

    try:
        response = client.chat.completions.create(
            model=config.model,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content or ""
    except Exception as e:  # noqa: BLE001 - 网关错误统一包装
        raise RuntimeError(
            f"LLM 调用失败（key={mask_key(config.api_key)}）: {e}"
        ) from e


# ========== Day2：两步拆分相关 prompt 与函数 ==========

EXTRACT_PROMPT_TEMPLATE = """\
你是一位资深技术面试官。下面是一段面试面经，请从中提取出所有的面试问题。

要求：
- 只提取明确的"问题"，忽略叙述性内容
- 返回纯 JSON 数组，格式：[{{"question": "问题1"}}, {{"question": "问题2"}}]
- 不要输出任何解释、前后缀文字、不要用 markdown 代码块
- 如果没有识别到问题，返回 []

面经内容：
{raw_text}
"""

BATCH_ANSWER_PROMPT_TEMPLATE = """\
你是一位资深技术面试官。请逐一回答以下面试问题，每个回答专业、有条理、分点。

问题列表：
{questions_block}

输出要求（严格遵守，避免与格式化器重复）：
- 每个问题的回答以一行 <<<ANSWER>>> 开头作为分隔标记
- 标记后直接给答案正文，不要重复问题、不要写"### 参考回答"等标题（标题由程序统一加）
- 答案用 markdown 无序列表（- ）分点
- 例如：
<<<ANSWER>>>
- 第一点...
- 第二点...

<<<ANSWER>>>
- ...
"""

BATCH_ANSWER_SEP = "<<<ANSWER>>>"

ONE_ANSWER_PROMPT_TEMPLATE = """\
你是一位资深技术面试官。请专业、有条理、分点地回答下面这个面试问题。

问题：{question}

输出要求：
- 直接给出分点回答，不要重复问题
- 用 markdown 无序列表（- ）分点
- 只输出回答内容
"""


def build_extract_prompt(mianjing: Mianjing) -> str:
    """构造拆问题 prompt。"""
    return EXTRACT_PROMPT_TEMPLATE.format(raw_text=mianjing.raw_text)


def build_batch_answer_prompt(questions: list[Question]) -> str:
    """构造批量回答 prompt。"""
    block = "\n".join(f"{q.index}. {q.text}" for q in questions)
    return BATCH_ANSWER_PROMPT_TEMPLATE.format(questions_block=block)


def build_one_answer_prompt(question: Question) -> str:
    """构造单题回答 prompt。"""
    return ONE_ANSWER_PROMPT_TEMPLATE.format(question=question.text)


def _is_rate_limit(exc: Exception) -> bool:
    """判断异常是否 429 限流（可重试）。

    双保险：openai RateLimitError 类型，或 status_code == 429。
    """
    if isinstance(exc, RateLimitError):
        return True
    return getattr(exc, "status_code", None) == 429


def _chat(
    config: Config,
    prompt: str,
    _sleep=time.sleep,
) -> str:
    """底层调用 LLM，429 限流指数退避重试。

    Args:
        config: LLM 配置。
        prompt: 提示词。
        _sleep: 等待函数（测试注入 mock，避免真等）。

    Raises:
        RuntimeError: 调用失败（含 key 脱敏）。
    """
    client = OpenAI(api_key=config.api_key, base_url=config.base_url)
    last_exc: Exception | None = None
    max_retries = config.max_retries
    for attempt in range(max_retries + 1):  # 初试 + 最多 max_retries 次重试
        try:
            response = client.chat.completions.create(
                model=config.model,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.choices[0].message.content or ""
        except Exception as e:  # noqa: BLE001
            last_exc = e
            if _is_rate_limit(e) and attempt < max_retries:
                _sleep(config.retry_backoff[attempt])  # 退避后重试
                continue
            break  # 非 429 或已达上限
    raise RuntimeError(
        f"LLM 调用失败（key={mask_key(config.api_key)}）: {last_exc}"
    ) from last_exc


def extract_questions(raw_text: str, config: Config) -> str:
    """调 LLM 拆问题，返回 JSON 字符串（未解析）。"""
    return _chat(config, build_extract_prompt(Mianjing(raw_text=raw_text)))


def answer_questions_batch(questions: list[Question], config: Config) -> str:
    """low 模式：一次性回答所有问题，返回 markdown 片段。"""
    return _chat(config, build_batch_answer_prompt(questions))


def answer_one(question: Question, config: Config) -> Answer:
    """high 模式：回答单个问题。"""
    content = _chat(config, build_one_answer_prompt(question))
    return Answer(content=content)
