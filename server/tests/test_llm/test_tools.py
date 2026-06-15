"""LLM 源码工具参数兼容测试。"""

from app.llm.tools import execute_read_source_file, execute_tool_call


def test_read_source_file_supports_start_line():
    result = execute_read_source_file("README.md", start_line=2, max_lines=2)

    assert "   2|" in result
    assert "   3|" in result
    assert "   1|" not in result


def test_tool_dispatch_ignores_unknown_arguments():
    result = execute_tool_call(
        "read_source_file",
        {"path": "README.md", "max_lines": 1, "unknown_argument": "ignored"},
    )

    assert "文件 README.md" in result
    assert "[工具异常]" not in result
