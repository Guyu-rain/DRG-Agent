"""自定义业务异常与错误码定义。"""

from __future__ import annotations


class ErrorCode:
    """业务错误码 (参照 plans/03_api_interfaces.md §11)。"""

    CODE_FORMAT_INVALID = 40001
    REQUIRED_FIELD_MISSING = 40002
    RULE_VERSION_INACTIVE = 40003
    CASE_NOT_FOUND = 40401
    RULE_VERSION_NOT_FOUND = 40402
    TASK_NOT_FOUND = 40403
    DOCUMENT_NOT_FOUND = 40404
    TESTCASE_NOT_FOUND = 40405
    DUPLICATE_SUBMIT = 40901
    RESOURCE_IN_USE = 40902
    RULE_ENGINE_ERROR = 50001
    LLM_CALL_FAILED = 50002
    DOCUMENT_GEN_FAILED = 50003
    LLM_API_UNREACHABLE = 50301


class AppException(Exception):
    """统一业务异常。

    Attributes:
        code: 业务错误码 (见 ErrorCode)。
        message: 面向用户的错误描述。
        http_status: 对应的 HTTP 状态码。
        detail: 可选的错误详情。
    """

    def __init__(
        self,
        code: int = 500,
        message: str = "服务器内部错误",
        http_status: int = 500,
        detail: dict | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.http_status = http_status
        self.detail = detail
        super().__init__(message)


class NotFoundException(AppException):
    def __init__(self, code: int, message: str, detail: dict | None = None) -> None:
        super().__init__(code=code, message=message, http_status=404, detail=detail)


class BadRequestException(AppException):
    def __init__(self, code: int, message: str, detail: dict | None = None) -> None:
        super().__init__(code=code, message=message, http_status=400, detail=detail)


class ConflictException(AppException):
    def __init__(self, code: int, message: str, detail: dict | None = None) -> None:
        super().__init__(code=code, message=message, http_status=409, detail=detail)
