"""LLM Function Calling 循环与文本协议兼容测试。"""

from types import SimpleNamespace

from app.llm.client import LLMClient, is_tool_protocol_content, parse_text_tool_calls


def _response(*, content: str | None = None, tool_name: str | None = None, index: int = 1):
    tool_calls = None
    if tool_name:
        tool_calls = [
            SimpleNamespace(
                id=f"call-{index}",
                function=SimpleNamespace(name=tool_name, arguments='{"path":"README.md"}'),
            )
        ]
    message = SimpleNamespace(content=content, tool_calls=tool_calls)
    return SimpleNamespace(
        choices=[SimpleNamespace(message=message, finish_reason="tool_calls" if tool_calls else "stop")],
        usage=None,
    )


def _client_with_responses(monkeypatch, responses):
    client = LLMClient()
    client.api_key = "test-key"
    iterator = iter(responses)
    monkeypatch.setattr(client, "_chat_completion", lambda *_args, **_kwargs: next(iterator))
    return client


def test_tool_loop_has_no_fixed_round_limit(monkeypatch):
    responses = [
        *[_response(tool_name="read_source_file", index=index) for index in range(1, 8)],
        _response(content="# 最终文档"),
    ]
    executed: list[tuple[str, dict]] = []
    monkeypatch.setattr(
        "app.llm.tools.execute_tool_call",
        lambda name, arguments: executed.append((name, arguments)) or "工具结果",
    )

    result = _client_with_responses(monkeypatch, responses).call(
        messages=[{"role": "user", "content": "生成文档"}],
        tools=[{"type": "function", "function": {"name": "read_source_file"}}],
    )

    assert result == "# 最终文档"
    assert len(executed) == 7


def test_dsml_text_tool_calls_are_executed_instead_of_returned(monkeypatch):
    dsml = """
<｜｜DSML｜｜tool_calls>
<｜｜DSML｜｜invoke name="read_source_file">
<｜｜DSML｜｜parameter name="path" string="true">server/app/models/rule.py</｜｜DSML｜｜parameter>
<｜｜DSML｜｜parameter name="start_line">20</｜｜DSML｜｜parameter>
</｜｜DSML｜｜invoke>
</｜｜DSML｜｜tool_calls>
""".strip()
    executed: list[tuple[str, dict]] = []
    monkeypatch.setattr(
        "app.llm.tools.execute_tool_call",
        lambda name, arguments: executed.append((name, arguments)) or "工具结果",
    )

    result = _client_with_responses(
        monkeypatch,
        [_response(content=dsml), _response(content="# 正常文档")],
    ).call(
        messages=[{"role": "user", "content": "生成文档"}],
        tools=[{"type": "function", "function": {"name": "read_source_file"}}],
    )

    assert result == "# 正常文档"
    assert executed == [
        ("read_source_file", {"path": "server/app/models/rule.py", "start_line": 20})
    ]


def test_unparseable_tool_protocol_is_retried(monkeypatch):
    malformed = "<｜｜DSML｜｜tool_calls><broken>"
    client = _client_with_responses(
        monkeypatch,
        [_response(content=malformed), _response(content="# 重试后的文档")],
    )

    result = client.call(
        messages=[{"role": "user", "content": "生成文档"}],
        tools=[{"type": "function", "function": {"name": "read_source_file"}}],
    )

    assert result == "# 重试后的文档"


def test_tool_protocol_detection_and_parsing():
    text = (
        '<｜｜DSML｜｜tool_calls><｜｜DSML｜｜invoke name="read_source_file">'
        '<｜｜DSML｜｜parameter name="path" string="true">README.md'
        "</｜｜DSML｜｜parameter></｜｜DSML｜｜invoke></｜｜DSML｜｜tool_calls>"
    )
    assert is_tool_protocol_content(text)
    assert parse_text_tool_calls(text) == [("read_source_file", {"path": "README.md"})]
    assert not is_tool_protocol_content("# 文档\n\n正文中可以讨论 tool_calls。")
