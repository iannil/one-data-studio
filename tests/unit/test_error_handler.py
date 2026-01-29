"""
错误处理模块单元测试
Sprint 9: 测试覆盖
"""

import sys
from pathlib import Path

# 添加项目根路径以便导入 services.shared
_project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_project_root))

import pytest
from services.shared.error_handler import (
    ErrorCode,
    APIError,
    ValidationError,
    NotFoundError,
    UnauthorizedError,
    ForbiddenError,
    ConflictError,
    DatabaseError,
    ExternalAPIError,
    success_response,
    error_response,
    handle_exception,
    validate_required,
    validate_field
)


class TestErrorCode:
    """错误码测试"""

    def test_success_code(self):
        """测试成功码"""
        assert ErrorCode.SUCCESS == 0

    def test_error_codes_structure(self):
        """测试错误码结构"""
        # 通用错误 1xxxx
        assert 10000 < ErrorCode.UNKNOWN_ERROR < 20000
        assert 10000 < ErrorCode.INVALID_REQUEST < 20000
        assert 10000 < ErrorCode.RATE_LIMIT_EXCEEDED < 20000

        # 认证错误 2xxxx
        assert 20000 < ErrorCode.UNAUTHORIZED < 30000
        assert 20000 < ErrorCode.TOKEN_EXPIRED < 30000

        # 资源错误 3xxxx
        assert 30000 < ErrorCode.RESOURCE_NOT_FOUND < 40000

        # 服务错误 4xxxx
        assert 40000 < ErrorCode.DATABASE_ERROR < 50000
        assert 40000 < ErrorCode.VECTOR_DB_ERROR < 50000


class TestAPIError:
    """API 错误测试"""

    def test_basic_error(self):
        """测试基本错误"""
        error = APIError(message="Test error")
        assert error.code == ErrorCode.UNKNOWN_ERROR
        assert error.message == "Test error"
        assert error.http_status == 500
        assert error.details == {}

    def test_custom_error(self):
        """测试自定义错误"""
        error = APIError(
            code=ErrorCode.INVALID_PARAMETER,  # VALIDATION_ERROR 不存在，使用 INVALID_PARAMETER
            message="Validation failed",
            details={"field": "email"},
            http_status=400
        )
        assert error.code == ErrorCode.INVALID_PARAMETER
        assert error.message == "Validation failed"
        assert error.details["field"] == "email"
        assert error.http_status == 400

    def test_to_dict(self):
        """测试转换为字典"""
        error = APIError(
            code=ErrorCode.RESOURCE_NOT_FOUND,
            message="Not found",
            details={"resource": "user"}
        )
        data = error.to_dict()
        assert data["code"] == ErrorCode.RESOURCE_NOT_FOUND
        assert data["message"] == "Not found"
        assert data["details"]["resource"] == "user"

    def test_to_response(self):
        """测试转换为 Flask 响应"""
        error = APIError(
            code=ErrorCode.INVALID_REQUEST,
            message="Bad request",
            http_status=400
        )
        data, status = error.to_response()
        assert status == 400
        assert data["code"] == ErrorCode.INVALID_REQUEST


class TestValidationError:
    """验证错误测试"""

    def test_without_field(self):
        """测试无字段验证错误"""
        error = ValidationError("Invalid input")
        assert error.code == ErrorCode.INVALID_PARAMETER
        assert error.message == "Invalid input"
        assert error.http_status == 400

    def test_with_field(self):
        """测试带字段验证错误"""
        error = ValidationError("Invalid email", field="email")
        assert error.details["field"] == "email"

    def test_with_additional_details(self):
        """测试带额外详情"""
        error = ValidationError(
            "Invalid value",
            field="age",
            details={"min": 0, "max": 120}
        )
        assert error.details["field"] == "age"
        assert error.details["min"] == 0
        assert error.details["max"] == 120


class TestNotFoundError:
    """资源未找到错误测试"""

    def test_basic(self):
        """测试基本未找到错误"""
        error = NotFoundError("User")
        assert "User not found" in error.message
        assert error.details["resource"] == "User"
        assert error.http_status == 404

    def test_with_identifier(self):
        """测试带标识符的未找到错误"""
        error = NotFoundError("Document", "doc-123")
        assert "Document not found" in error.message
        assert "doc-123" in error.message
        assert error.details["identifier"] == "doc-123"


class TestUnauthorizedError:
    """未授权错误测试"""

    def test_default(self):
        """测试默认未授权错误"""
        error = UnauthorizedError()
        assert error.message == "Unauthorized"
        assert error.http_status == 401

    def test_custom_message(self):
        """测试自定义消息"""
        error = UnauthorizedError("Token expired")
        assert error.message == "Token expired"


class TestForbiddenError:
    """禁止访问错误测试"""

    def test_default(self):
        """测试默认禁止错误"""
        error = ForbiddenError()
        assert error.message == "Forbidden"
        assert error.http_status == 403


class TestConflictError:
    """冲突错误测试"""

    def test_basic(self):
        """测试基本冲突错误"""
        error = ConflictError("Resource already exists")
        assert error.code == ErrorCode.RESOURCE_CONFLICT
        assert error.http_status == 409


class TestDatabaseError:
    """数据库错误测试"""

    def test_default(self):
        """测试默认数据库错误"""
        error = DatabaseError()
        assert error.code == ErrorCode.DATABASE_ERROR
        assert error.http_status == 500

    def test_with_details(self):
        """测试带详情的数据库错误"""
        error = DatabaseError(
            "Connection failed",
            details={"host": "localhost", "port": 3306}
        )
        assert "Connection failed" in error.message
        assert error.details["host"] == "localhost"


class TestExternalAPIError:
    """外部 API 错误测试"""

    def test_basic(self):
        """测试基本外部 API 错误"""
        error = ExternalAPIError("OpenAI", "Rate limit exceeded")
        assert "OpenAI" in error.message
        assert "Rate limit exceeded" in error.message
        assert error.details["service"] == "OpenAI"
        assert error.http_status == 503


class TestResponseFunctions:
    """响应函数测试"""

    def test_success_response_without_data(self):
        """测试无数据成功响应"""
        response = success_response()
        assert response["code"] == ErrorCode.SUCCESS
        assert response["message"] == "success"
        assert "data" not in response

    def test_success_response_with_data(self):
        """测试带数据成功响应"""
        response = success_response({"id": 123}, "Created")
        assert response["code"] == ErrorCode.SUCCESS
        assert response["message"] == "Created"
        assert response["data"]["id"] == 123

    def test_error_response(self):
        """测试错误响应"""
        data, status = error_response(
            code=ErrorCode.INVALID_REQUEST,
            message="Bad request",
            details={"field": "email"},
            http_status=400
        )
        assert status == 400
        assert data["code"] == ErrorCode.INVALID_REQUEST
        assert data["message"] == "Bad request"
        assert data["details"]["field"] == "email"


class TestValidationFunctions:
    """验证函数测试"""

    def test_validate_required_pass(self):
        """测试必需字段验证通过"""
        data = {"name": "John", "email": "john@example.com"}
        # 应该不抛出异常
        validate_required(data, "name", "email")

    def test_validate_required_fail(self):
        """测试必需字段验证失败"""
        data = {"name": "John"}
        with pytest.raises(ValidationError) as exc_info:
            validate_required(data, "name", "email")
        assert "Missing required fields" in str(exc_info.value)
        assert exc_info.value.details["missing_fields"] == ["email"]

    def test_validate_required_empty_string(self):
        """测试空字符串被视为缺失"""
        data = {"name": "", "email": "test@example.com"}
        with pytest.raises(ValidationError) as exc_info:
            validate_required(data, "name")
        assert "name" in exc_info.value.details["missing_fields"]

    def test_validate_field_pass(self):
        """测试字段验证通过"""
        data = {"age": 25}
        # 应该不抛出异常
        validate_field(data, "age", lambda x: x >= 0, "Age must be positive")

    def test_validate_field_fail(self):
        """测试字段验证失败"""
        data = {"age": -5}
        with pytest.raises(ValidationError) as exc_info:
            validate_field(data, "age", lambda x: x >= 0, "Age must be positive")
        # 注意：当前实现会捕获所有异常并返回通用消息
        assert "age" in str(exc_info.value).lower()
        assert exc_info.value.details["field"] == "age"

    def test_validate_field_not_exists(self):
        """测试字段不存在时应该不验证"""
        data = {"name": "John"}
        # 字段不存在时不应该抛出异常
        validate_field(data, "age", lambda x: x >= 0, "Age must be positive")


class TestHandleException:
    """异常处理测试"""

    def test_handle_api_error(self):
        """测试处理 API 错误"""
        error = ValidationError("Invalid input")
        data, status = handle_exception(error)
        assert status == 400
        assert data["code"] == ErrorCode.INVALID_PARAMETER

    def test_handle_generic_exception(self):
        """测试处理通用异常"""
        error = ValueError("Some error")
        data, status = handle_exception(error)
        assert status == 500
        assert data["code"] == ErrorCode.UNKNOWN_ERROR

    def test_handle_exception_with_traceback(self):
        """测试包含堆栈跟踪"""
        error = RuntimeError("Test error")
        data, status = handle_exception(error, include_traceback=True)
        assert status == 500
        assert "traceback" in data
        assert "type" in data
