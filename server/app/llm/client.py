"""LLM 客户端封装 (DeepSeek / OpenAI 兼容)。

参照 plans/06_agent_workflow.md §7 与 plans/phase1_backend.md §3。
提供重试、超时、降级与 Mock 实现。
"""

from __future__ import annotations

import json
import re
import time
from typing import Protocol

from app.core.config import settings
from app.core.logging import logger


class LLMClientProtocol(Protocol):
    """LLM 客户端接口。"""

    def call(self, prompt: str, **kwargs) -> str: ...

    def call_with_fallback(self, prompt: str, fallback_value: str | None = None) -> str: ...


class LLMClient:
    """基于 OpenAI Python SDK 的 LLM 客户端 (兼容 DeepSeek)。"""

    def __init__(self) -> None:
        self.api_key = settings.LLM_API_KEY
        self.api_base = settings.LLM_API_BASE
        self.default_model = settings.LLM_MODEL
        self.timeout = settings.LLM_TIMEOUT
        self._client = None  # 延迟初始化, 避免无 Key 时导入即失败

    def _ensure_client(self):
        if self._client is None:
            from openai import OpenAI

            self._client = OpenAI(
                api_key=self.api_key or "not-set",
                base_url=self.api_base,
                timeout=self.timeout,
            )
        return self._client

    def call(
        self,
        prompt: str,
        model: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        max_retries: int = 3,
    ) -> str:
        """调用 LLM 并返回文本。失败时按指数退避 (1s, 2s, 4s) 重试。

        Raises:
            RuntimeError: 重试耗尽后仍失败。
        """
        if not self.api_key:
            raise RuntimeError("LLM_API_KEY 未配置")

        model = model or self.default_model
        client = self._ensure_client()
        last_error: Exception | None = None

        for attempt in range(max_retries):
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                content = response.choices[0].message.content or ""
                usage = getattr(response, "usage", None)
                logger.info(f"LLM 调用成功 model={model} tokens={usage}")
                return content
            except Exception as exc:  # noqa: BLE001 - 统一重试所有调用异常
                last_error = exc
                wait = 2 ** attempt
                logger.warning(f"LLM 调用失败 (第 {attempt + 1}/{max_retries} 次): {exc}")
                if attempt < max_retries - 1:
                    time.sleep(wait)

        logger.error(f"LLM 调用在 {max_retries} 次重试后仍失败: {last_error}")
        raise RuntimeError(f"LLM 调用失败: {last_error}")

    def call_with_fallback(self, prompt: str, fallback_value: str | None = None) -> str:
        """调用 LLM, 失败时返回降级值 (而非抛异常)。"""
        try:
            return self.call(prompt)
        except Exception as exc:  # noqa: BLE001
            logger.error(f"LLM 调用失败, 使用降级输出: {exc}")
            if fallback_value is not None:
                return fallback_value
            return ""


class MockLLMClient:
    """测试用 Mock LLM 客户端, 返回预定义响应。"""

    def __init__(self, default_response: str = "", responses: dict[str, str] | None = None) -> None:
        self.default_response = default_response
        self.responses = responses or {}
        self.call_count = 0
        self.last_prompt: str | None = None

    def call(self, prompt: str, **kwargs) -> str:
        self.call_count += 1
        self.last_prompt = prompt
        for keyword, response in self.responses.items():
            if keyword in prompt:
                return response
        return self.default_response

    def call_with_fallback(self, prompt: str, fallback_value: str | None = None) -> str:
        try:
            return self.call(prompt)
        except Exception:  # noqa: BLE001
            return fallback_value or ""


def parse_llm_json_output(text: str) -> dict | list | None:
    """从 LLM 输出中提取 JSON (容忍 ```json 代码块包裹与前后噪声)。"""
    if not text:
        return None
    cleaned = text.strip()

    fence = re.search(r"```(?:json)?\s*(.+?)\s*```", cleaned, re.DOTALL)
    if fence:
        cleaned = fence.group(1).strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # 退而求其次: 截取首个 { 或 [ 到对应的末尾
    for open_ch, close_ch in (("{", "}"), ("[", "]")):
        start = cleaned.find(open_ch)
        end = cleaned.rfind(close_ch)
        if start != -1 and end > start:
            try:
                return json.loads(cleaned[start : end + 1])
            except json.JSONDecodeError:
                continue
    return None


_default_client: LLMClient | None = None


def get_llm_client() -> LLMClient:
    """获取进程级共享的 LLM 客户端。"""
    global _default_client
    if _default_client is None:
        _default_client = LLMClient()
    return _default_client
