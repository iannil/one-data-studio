"""
统一错误处理模块
Sprint 6: 统一错误处理模式

提供一致的错误响应格式和处理逻辑
"""

import logging
import traceback
from typing import Any, Dict, Optional, Tuple
from functools import wraps
from flask import jsonify, Response
from werkzeug.exceptions import HTTPException

logger = logging.getLogger(__name__)


class ErrorCode:
    """错误码定义"""
    # 通用错误 (1xxxx)
    SUCCESS = 0
    UNKNOWN_ERROR = 10001
    INVALID_REQUEST = 10002
    MISSING_PARAMETER = 10003
    INVALID_PARAMETER = 10004
    RATE_LIMIT_EXCEEDED = 10005

    # 认证授权错误 (2xxxx)
    UNAUTHORIZED = 20001
    TOKEN_EXPIRED = 20002
    TOKEN_INVALID = 20003
    INSUFFICIENT_PERMISSIONS = 20003
    USER_NOT_FOUND = 20004
    ACCOUNT_DISABLED = 20005

    # 资源错误 (3xxxx)
    RESOURCE_NOT_FOUND = 30001
    RESOURCE_ALREADY_EXISTS = 30002
    RESOURCE_CONFLICT = 30003
    RESOURCE_LOCKED = 30004

    # 服务错误 (4xxxx)
    DATABASE_ERROR = 40001
    STORAGE_ERROR = 40002
    VECTOR_DB_ERROR = 40003
    EXTERNAL_API_ERROR = 40004
    TIMEOUT_ERROR = 40005

    # 工作流错误 (5xxxx)
    WORKFLOW_NOT_FOUND = 50001
    WORKFLOW_EXECUTION_FAILED = 50002
    WORKFLOW_VALIDATION_FAILED = 50003
    NODE_EXECUTION_FAILED = 50004
    SCHEDULE_ERROR = 50005

    # 文档错误 (6xxxx)
    DOCUMENT_NOT_FOUND = 60001
    DOCUMENT_INDEXING_FAILED = 60002
    DOCUMENT_UPLOAD_FAILED = 60003


class APIError(Exception):
    """API 错误基类"""

    def __init__(
        self,
        code: int = ErrorCode.UNKNOWN_ERROR,
        message: str = "An unknown error occurred",
        details: Optional[Dict[str, Any]] = None,
        http_status: int = 500
    ):
        self.code = code
        self.message = message
        self.details = details or {}
        self.http_status = http_status
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {
            "code": self.code,
            "message": self.message
        }
        if self.details:
            result["details"] = self.details
        return result

    def to_response(self) -> Tuple[Dict[str, Any], int]:
        """转换为 Flask 响应"""
        return self.to_dict(), self.http_status


class ValidationError(APIError):
    """验证错误"""

    def __init__(self, message: str, field: Optional[str] = None, details: Optional[Dict] = None):
        details = details or {}
        if field:
            details["field"] = field
        super().__init__(
            code=ErrorCode.INVALID_PARAMETER,
            message=message,
            details=details,
            http_status=400
        )


class NotFoundError(APIError):
    """资源未找到错误"""

    def __init__(self, resource: str, identifier: Optional[str] = None):
        message = f"{resource} not found"
        if identifier:
            message += f": {identifier}"
        details = {"resource": resource}
        if identifier:
            details["identifier"] = identifier
        super().__init__(
            code=ErrorCode.RESOURCE_NOT_FOUND,
            message=message,
            details=details,
            http_status=404
        )


class UnauthorizedError(APIError):
    """未授权错误"""

    def __init__(self, message: str = "Unauthorized", details: Optional[Dict] = None):
        super().__init__(
            code=ErrorCode.UNAUTHORIZED,
            message=message,
            details=details,
            http_status=401
        )


class ForbiddenError(APIError):
    """禁止访问错误"""

    def __init__(self, message: str = "Forbidden", details: Optional[Dict] = None):
        super().__init__(
            code=ErrorCode.INSUFFICIENT_PERMISSIONS,
            message=message,
            details=details,
            http_status=403
        )


class ConflictError(APIError):
    """冲突错误"""

    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(
            code=ErrorCode.RESOURCE_CONFLICT,
            message=message,
            details=details,
            http_status=409
        )


class DatabaseError(APIError):
    """数据库错误"""

    def __init__(self, message: str = "Database error occurred", details: Optional[Dict] = None):
        super().__init__(
            code=ErrorCode.DATABASE_ERROR,
            message=message,
            details=details,
            http_status=500
        )


class ExternalAPIError(APIError):
    """外部 API 错误"""

    def __init__(self, service: str, message: str, details: Optional[Dict] = None):
        details = details or {}
        details["service"] = service
        super().__init__(
            code=ErrorCode.EXTERNAL_API_ERROR,
            message=f"{service} error: {message}",
            details=details,
            http_status=503
        )


def success_response(data: Any = None, message: str = "success") -> Dict[str, Any]:
    """
    成功响应格式

    Args:
        data: 响应数据
        message: 响应消息

    Returns:
        标准响应字典
    """
    result = {
        "code": ErrorCode.SUCCESS,
        "message": message
    }
    if data is not None:
        result["data"] = data
    return result


def error_response(
    code: int = ErrorCode.UNKNOWN_ERROR,
    message: str = "An error occurred",
    details: Optional[Dict] = None,
    http_status: int = 500
) -> Tuple[Dict[str, Any], int]:
    """
    错误响应格式

    Args:
        code: 错误码
        message: 错误消息
        details: 错误详情
        http_status: HTTP 状态码

    Returns:
        Flask 响应元组
    """
    response = {
        "code": code,
        "message": message
    }
    if details:
        response["details"] = details
    return response, http_status


def handle_exception(e: Exception, include_traceback: bool = False) -> Tuple[Dict[str, Any], int]:
    """
    统一异常处理

    Args:
        e: 异常对象
        include_traceback: 是否包含堆栈跟踪（仅开发环境）

    Returns:
        Flask 响应元组
    """
    # APIError 子类
    if isinstance(e, APIError):
        logger.warning(f"API Error: {e.code} - {e.message}")
        return e.to_response()

    # HTTP 异常
    if isinstance(e, HTTPException):
        logger.warning(f"HTTP Error: {e.code} - {e.description}")
        return {
            "code": e.code,
            "message": str(e.description)
        }, e.code

    # 其他异常
    logger.error(f"Unhandled exception: {type(e).__name__} - {str(e)}")
    logger.debug(traceback.format_exc())

    response = {
        "code": ErrorCode.UNKNOWN_ERROR,
        "message": "An internal error occurred"
    }

    if include_traceback:
        response["traceback"] = traceback.format_exc()
        response["type"] = type(e).__name__

    return response, 500


def catch_errors(f=None, *, include_traceback: bool = False):
    """
    错误捕获装饰器

    Args:
        include_traceback: 是否包含堆栈跟踪

    Usage:
        @catch_errors
        def my_function():
            ...

        或

        @catch_errors(include_traceback=True)
        def my_function():
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except APIError:
                raise  # APIError 直接抛出
            except Exception as e:
                return handle_exception(e, include_traceback)
        return wrapper

    if f is None:
        return decorator
    return decorator(f)


def validate_required(data: Dict[str, Any], *fields: str) -> None:
    """
    验证必需字段

    Args:
        data: 请求数据
        *fields: 必需字段列表

    Raises:
        ValidationError: 当缺少必需字段时
    """
    missing = [f for f in fields if f not in data or data[f] is None or data[f] == ""]
    if missing:
        raise ValidationError(
            message=f"Missing required fields: {', '.join(missing)}",
            details={"missing_fields": missing}
        )


def validate_field(data: Dict[str, Any], field: str, condition, error_message: str) -> None:
    """
    验证单个字段

    Args:
        data: 请求数据
        field: 字段名
        condition: 验证条件（可调用对象）
        error_message: 错误消息

    Raises:
        ValidationError: 当验证失败时
    """
    if field in data:
        try:
            if not condition(data[field]):
                raise ValidationError(
                    message=error_message,
                    field=field
                )
        except Exception:
            raise ValidationError(
                message=f"Invalid value for field: {field}",
                field=field
            )


# Flask 错误处理器注册器

def register_error_handlers(app, include_traceback: bool = False):
    """
    注册 Flask 错误处理器

    Args:
        app: Flask 应用实例
        include_traceback: 是否在生产环境包含堆栈跟踪
    """

    @app.errorhandler(APIError)
    def handle_api_error(e):
        return jsonify(e.to_dict()), e.http_status

    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({"code": ErrorCode.INVALID_REQUEST, "message": str(e)}), 400

    @app.errorhandler(401)
    def unauthorized(e):
        return jsonify({
            "code": ErrorCode.UNAUTHORIZED,
            "message": "Unauthorized",
            "error": "authentication_required"
        }), 401

    @app.errorhandler(403)
    def forbidden(e):
        return jsonify({
            "code": ErrorCode.INSUFFICIENT_PERMISSIONS,
            "message": "Forbidden",
            "error": "insufficient_permissions"
        }), 403

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"code": ErrorCode.RESOURCE_NOT_FOUND, "message": "Resource not found"}), 404

    @app.errorhandler(409)
    def conflict(e):
        return jsonify({
            "code": ErrorCode.RESOURCE_CONFLICT,
            "message": "Resource conflict"
        }), 409

    @app.errorhandler(500)
    def internal_server_error(e):
        logger.error(f"Internal server error: {str(e)}")
        return jsonify({
            "code": ErrorCode.UNKNOWN_ERROR,
            "message": "Internal server error"
        }), 500

    @app.errorhandler(Exception)
    def handle_exception_error(e):
        return handle_exception(e, include_traceback)
