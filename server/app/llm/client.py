"""LLM 客户端封装 (DeepSeek / OpenAI 兼容)。

参照 plans/06_agent_workflow.md §7 与 plans/phase1_backend.md §3。
提供重试、超时、降级、Function Calling 与 Mock 实现。
"""

from __future__ import annotations

import json
import re
import time
from html import unescape
from typing import Protocol

from app.core.config import settings
from app.core.logging import logger

_DSML_INVOKE_RE = re.compile(
    r'<\|\|DSML\|\|invoke\s+name="([^"]+)">(.*?)</\|\|DSML\|\|invoke>',
    re.DOTALL | re.IGNORECASE,
)
_DSML_PARAMETER_RE = re.compile(
    r'<\|\|DSML\|\|parameter\s+name="([^"]+)"(?:\s+string="(true|false)")?'
    r">(.*?)</\|\|DSML\|\|parameter>",
    re.DOTALL | re.IGNORECASE,
)


class LLMClientProtocol(Protocol):
    """LLM 客户端接口。"""

    def call(self, prompt: str, **kwargs) -> str: ...

    def call_with_fallback(self, prompt: str, fallback_value: str | None = None) -> str: ...


class LLMClient:
    """基于 OpenAI Python SDK 的 LLM 客户端 (兼容 DeepSeek)。

    支持 Function Calling: 传入 ``tools`` 参数后自动进入 tool call 循环,
    持续执行工具并将结果回传 LLM，直到模型返回最终文本。
    """

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

    # ------------------------------------------------------------------ 底层请求
    def _chat_completion(
        self,
        messages: list[dict],
        model: str,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        tools: list[dict] | None = None,
        tool_choice: str = "auto",
    ):
        """单次非流式请求, 返回原始 API response。"""
        client = self._ensure_client()
        kwargs: dict = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = tool_choice
        return client.chat.completions.create(**kwargs)

    # ------------------------------------------------------------------ Tool Call 循环
    def call(
        self,
        prompt: str = "",
        model: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        max_retries: int = 3,
        messages: list[dict] | None = None,
        tools: list[dict] | None = None,
        tool_choice: str = "auto",
    ) -> str:
        """调用 LLM 并返回文本。

        Args:
            prompt: 单轮提示词 (当 ``messages`` 未提供时使用)。
            messages: 多轮对话消息列表，提供时优先于 ``prompt``。
            tools: OpenAI Function Calling 工具定义列表。传入后启用
                tool call 循环，直到模型返回最终文本。
            tool_choice: 工具选择策略, 默认 "auto"。

        Raises:
            RuntimeError: 重试耗尽后仍失败。
        """
        if not self.api_key:
            raise RuntimeError("LLM_API_KEY 未配置")

        model = model or self.default_model
        chat_messages: list[dict] = list(messages) if messages else [{"role": "user", "content": prompt}]

        if not tools:
            return self._call_simple(chat_messages, model, temperature, max_tokens, max_retries)

        return self._call_with_tool_loop(
            chat_messages, model, temperature, max_tokens, max_retries, tools, tool_choice,
        )

    def _call_simple(
        self,
        messages: list[dict],
        model: str,
        temperature: float,
        max_tokens: int,
        max_retries: int,
    ) -> str:
        """无工具的标准调用。"""
        last_error: Exception | None = None
        for attempt in range(max_retries):
            try:
                response = self._chat_completion(messages, model, temperature, max_tokens)
                content = response.choices[0].message.content or ""
                usage = getattr(response, "usage", None)
                logger.info(f"LLM 调用成功 model={model} tokens={usage}")
                return content
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                wait = 2 ** attempt
                logger.warning(f"LLM 调用失败 (第 {attempt + 1}/{max_retries} 次): {exc}")
                if attempt < max_retries - 1:
                    time.sleep(wait)

        logger.error(f"LLM 调用在 {max_retries} 次重试后仍失败: {last_error}")
        raise RuntimeError(f"LLM 调用失败: {last_error}")

    def _call_with_tool_loop(
        self,
        messages: list[dict],
        model: str,
        temperature: float,
        max_tokens: int,
        max_retries: int,
        tools: list[dict],
        tool_choice: str,
    ) -> str:
        """带 Function Calling 的调用, 执行工具调用循环。"""
        from app.llm.tools import execute_tool_call

        last_error: Exception | None = None

        tool_round = 0
        while True:
            tool_round += 1
            for attempt in range(max_retries):
                try:
                    response = self._chat_completion(
                        messages, model, temperature, max_tokens, tools, tool_choice,
                    )
                    break
                except Exception as exc:  # noqa: BLE001
                    last_error = exc
                    wait = 2 ** attempt
                    logger.warning(f"Tool call 请求失败 (第 {attempt + 1}/{max_retries} 次): {exc}")
                    if attempt < max_retries - 1:
                        time.sleep(wait)
            else:
                logger.error(f"Tool call 在 {max_retries} 次重试后仍失败: {last_error}")
                raise RuntimeError(f"LLM 调用失败: {last_error}")

            message = response.choices[0].message
            usage = getattr(response, "usage", None)
            logger.info(f"Tool round {tool_round} model={model} tokens={usage}")

            if message.tool_calls:
                structured_calls = [
                    (tc.id, tc.function.name, tc.function.arguments)
                    for tc in message.tool_calls
                ]
                self._append_and_execute_tool_calls(
                    messages,
                    message.content,
                    structured_calls,
                    execute_tool_call,
                )
                continue

            content = message.content or ""
            textual_calls = parse_text_tool_calls(content)
            if textual_calls:
                calls = [
                    (
                        f"text_tool_call_{tool_round}_{index}",
                        name,
                        json.dumps(arguments, ensure_ascii=False),
                    )
                    for index, (name, arguments) in enumerate(textual_calls, 1)
                ]
                logger.warning(
                    f"模型以文本协议返回 {len(calls)} 个工具调用，已转换为结构化调用"
                )
                self._append_and_execute_tool_calls(
                    messages,
                    None,
                    calls,
                    execute_tool_call,
                )
                continue

            if is_tool_protocol_content(content):
                logger.warning("模型返回了无法解析的工具协议文本，要求模型重新发起结构化调用")
                messages.append({"role": "assistant", "content": content})
                messages.append({
                    "role": "user",
                    "content": (
                        "上一条响应是未完成的工具调用协议，不能作为最终回答。"
                        "请使用已提供的结构化工具调用，或直接给出最终正文。"
                    ),
                })
                continue

            return content

    @staticmethod
    def _append_and_execute_tool_calls(
        messages: list[dict],
        assistant_content: str | None,
        calls: list[tuple[str, str, str]],
        execute_tool_call,  # noqa: ANN001
    ) -> None:
        """追加一轮结构化工具调用并执行，兼容 SDK 调用和 DSML 文本调用。"""
        messages.append({
            "role": "assistant",
            "content": assistant_content,
            "tool_calls": [
                {
                    "id": call_id,
                    "type": "function",
                    "function": {"name": name, "arguments": arguments},
                }
                for call_id, name, arguments in calls
            ],
        })
        for call_id, name, raw_arguments in calls:
            try:
                arguments = json.loads(raw_arguments)
            except (json.JSONDecodeError, TypeError):
                arguments = {}
            if not isinstance(arguments, dict):
                arguments = {}
            result = execute_tool_call(name, arguments)
            messages.append({
                "role": "tool",
                "tool_call_id": call_id,
                "content": result,
            })

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

    def call(self, prompt: str = "", **kwargs) -> str:
        self.call_count += 1
        messages = kwargs.get("messages")
        if messages:
            prompt = "\n".join(str(m.get("content", "")) for m in messages)
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


def is_tool_protocol_content(text: str) -> bool:
    """判断响应是否为模型内部工具协议，而不是可展示的最终正文。"""
    if not text:
        return False
    normalized = text.strip().replace("｜", "|")
    return bool(
        re.match(
            r"^(?:<\|\|DSML\|\|(?:tool_calls?|invoke)|<tool_calls?|<tool_call)",
            normalized,
            re.IGNORECASE,
        )
    )


def parse_text_tool_calls(text: str) -> list[tuple[str, dict]]:
    """解析 DeepSeek 偶尔写入 content 的 DSML 工具调用协议。"""
    if not is_tool_protocol_content(text):
        return []

    normalized = text.replace("｜", "|")
    calls: list[tuple[str, dict]] = []
    for invoke in _DSML_INVOKE_RE.finditer(normalized):
        arguments: dict = {}
        for parameter in _DSML_PARAMETER_RE.finditer(invoke.group(2)):
            name = parameter.group(1)
            string_flag = parameter.group(2)
            raw_value = unescape(parameter.group(3).strip())
            if string_flag == "true":
                arguments[name] = raw_value
                continue
            try:
                arguments[name] = json.loads(raw_value)
            except json.JSONDecodeError:
                arguments[name] = raw_value
        calls.append((invoke.group(1), arguments))
    return calls


_default_client: LLMClient | None = None


def get_llm_client() -> LLMClient:
    """获取进程级共享的 LLM 客户端。"""
    global _default_client
    if _default_client is None:
        _default_client = LLMClient()
    return _default_client
