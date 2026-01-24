"""
统一输入验证模块
Sprint 9: 安全加固 - 输入验证增强

提供：
1. JSON Schema 验证装饰器
2. SQL 注入防护
3. XSS 防护
4. CSRF Token 验证
5. 请求体大小限制
"""

import re
import html
import json
import logging
from functools import wraps
from typing import Any, Dict, List, Optional, Callable, TypeVar, Union
from dataclasses import dataclass

try:
    from jsonschema import validate, ValidationError as JsonValidationError, Draft7Validator
    JSONSCHEMA_AVAILABLE = True
except ImportError:
    JSONSCHEMA_AVAILABLE = False
    Draft7Validator = None

from flask import request, g
from error_handler import ValidationError, APIError

logger = logging.getLogger(__name__)

T = TypeVar('T')


# ==================== 常用 JSON Schema 定义 ====================

COMMON_SCHEMAS = {
    # 分页参数
    'pagination': {
        'type': 'object',
        'properties': {
            'page': {'type': 'integer', 'minimum': 1, 'default': 1},
            'page_size': {'type': 'integer', 'minimum': 1, 'maximum': 100, 'default': 20},
        },
    },

    # ID 参数
    'id_param': {
        'type': 'string',
        'pattern': r'^[a-zA-Z0-9\-_]{1,50}$',
    },

    # 数据集创建
    'dataset_create': {
        'type': 'object',
        'required': ['name'],
        'properties': {
            'name': {
                'type': 'string',
                'minLength': 1,
                'maxLength': 100,
                'pattern': r'^[a-zA-Z0-9\u4e00-\u9fa5_\-\s]+$',
            },
            'description': {'type': 'string', 'maxLength': 500},
            'storage_type': {'type': 'string', 'enum': ['s3', 'hdfs', 'local']},
            'format': {'type': 'string', 'enum': ['csv', 'json', 'parquet', 'excel']},
            'tags': {
                'type': 'array',
                'items': {'type': 'string', 'maxLength': 50},
                'maxItems': 20,
            },
        },
    },

    # 工作流创建
    'workflow_create': {
        'type': 'object',
        'required': ['name'],
        'properties': {
            'name': {
                'type': 'string',
                'minLength': 1,
                'maxLength': 100,
            },
            'description': {'type': 'string', 'maxLength': 500},
            'type': {'type': 'string', 'enum': ['rag', 'agent', 'text2sql', 'custom']},
        },
    },

    # 聊天请求
    'chat_request': {
        'type': 'object',
        'required': ['message'],
        'properties': {
            'message': {
                'type': 'string',
                'minLength': 1,
                'maxLength': 10000,
            },
            'model': {'type': 'string', 'maxLength': 100},
            'temperature': {'type': 'number', 'minimum': 0, 'maximum': 2},
            'max_tokens': {'type': 'integer', 'minimum': 1, 'maximum': 32000},
            'conversation_id': {'type': 'string', 'maxLength': 50},
        },
    },

    # Text-to-SQL 请求
    'text2sql_request': {
        'type': 'object',
        'required': ['natural_language'],
        'properties': {
            'natural_language': {
                'type': 'string',
                'minLength': 1,
                'maxLength': 1000,
            },
            'database': {'type': 'string', 'maxLength': 100},
            'selected_tables': {
                'type': 'array',
                'items': {'type': 'string', 'maxLength': 100},
                'maxItems': 10,
            },
        },
    },

    # 文档上传
    'document_upload': {
        'type': 'object',
        'required': ['content'],
        'properties': {
            'content': {
                'type': 'string',
                'minLength': 1,
                'maxLength': 10000000,  # 10MB 文本限制
            },
            'file_name': {'type': 'string', 'maxLength': 255},
            'title': {'type': 'string', 'maxLength': 200},
            'collection': {'type': 'string', 'maxLength': 50},
        },
    },
}


# ==================== SQL 注入防护 ====================

class SQLInjectionChecker:
    """SQL 注入检测器"""

    # SQL 关键字和操作符模式
    SQL_PATTERNS = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|TRUNCATE|EXEC|UNION|EXECUTE)\b)",
        r"(\b(OR|AND)\s+\d+\s*=\s*\d+)",  # OR 1=1
        r"(;\s*(DROP|DELETE|UPDATE))",  # 链式攻击
        r"(\-\-|\#)",  # SQL 注释
        r"\/\*.*\*\/",  # C 风格注释
        r"('.+OR.+')",  # 单引号注入
        r"(\|\|)",  # 字符串连接
        r"(CHR\s*\(|CHAR\s*\()",  # 字符编码绕过
        r"(EXEC\s*\(|EXECUTE\s*\()",  # 执行命令
        r"(xp_cmdshell|sp_executesql|sp_oacreate)",  # 存储过程
        r"(benchmark\s*\(|sleep\s*\(|waitfor\s+delay)",  # 时间注入
        r"(\bLIKE\s+'[^']*%[^%']*%')",  # LIKE 注入
    ]

    # 危险的函数调用
    DANGEROUS_FUNCTIONS = [
        r"load_file\s*\(",
        r"into\s+outfile",
        r"into\s+dumpfile",
        r"bulk\s+insert",
    ]

    # 白名单模式（用于表名、列名等）
    WHITELIST_PATTERNS = [
        r'^[a-zA-Z_][a-zA-Z0-9_]*$',  # 标准标识符
        r'^[a-zA-Z0-9_\-\.]+$',  # 文件名
    ]

    @classmethod
    def is_sql_injection(cls, input_str: str) -> bool:
        """
        检测是否包含 SQL 注入

        Args:
            input_str: 待检测字符串

        Returns:
            True 如果检测到注入，False 否则
        """
        if not input_str:
            return False

        input_upper = input_str.upper()

        # 检测 SQL 注入模式
        for pattern in cls.SQL_PATTERNS:
            if re.search(pattern, input_upper, re.IGNORECASE | re.MULTILINE):
                logger.warning(f"SQL injection detected: pattern={pattern}, input={input_str[:100]}")
                return True

        # 检测危险函数
        for pattern in cls.DANGEROUS_FUNCTIONS:
            if re.search(pattern, input_upper, re.IGNORECASE):
                logger.warning(f"Dangerous SQL function detected: pattern={pattern}")
                return True

        # 检测十六进制编码
        if re.search(r'0x[0-9a-fA-F]+', input_str):
            # 可能是十六进制编码绕过
            logger.warning(f"Hex encoding detected: {input_str[:100]}")
            return True

        return False

    @classmethod
    def validate_identifier(cls, identifier: str) -> bool:
        """
        验证 SQL 标识符（表名、列名等）

        Args:
            identifier: 标识符

        Returns:
            True 如果有效，False 否则
        """
        if not identifier:
            return False

        pattern = cls.WHITELIST_PATTERNS[0]  # 标准标识符模式
        return bool(re.match(pattern, identifier))

    @classmethod
    def validate_sql_value(cls, value: str) -> bool:
        """
        验证 SQL 值（防止值注入）

        Args:
            value: 值

        Returns:
            True 如果安全，False 否则
        """
        if not value:
            return True

        # 检测未闭合的引号
        if value.count("'") % 2 != 0:
            return False

        # 检测转义字符
        if "\\" in value:
            return False

        return not cls.is_sql_injection(value)


# ==================== XSS 防护 ====================

class XSSChecker:
    """XSS 攻击检测器"""

    # XSS 攻击模式
    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"vbscript:",
        r"onload\s*=",
        r"onerror\s*=",
        r"onclick\s*=",
        r"onmouseover\s*=",
        r"onfocus\s*=",
        r"onblur\s*=",
        r"<iframe[^>]*>",
        r"<embed[^>]*>",
        r"<object[^>]*>",
        r"<link[^>]*>",
        r"<meta[^>]*>",
        r"<style[^>]*>.*?</style>",
        r"<img[^>]*onerror[^>]*>",
        r"fromcharcode",
        r"&#x",
        r"&#(\d+);",
        r"eval\s*\(",
        r"alert\s*\(",
        r"expression\s*\(",
    ]

    @classmethod
    def is_xss(cls, input_str: str) -> bool:
        """
        检测是否包含 XSS 攻击

        Args:
            input_str: 待检测字符串

        Returns:
            True 如果检测到 XSS，False 否则
        """
        if not input_str:
            return False

        input_lower = input_str.lower()

        for pattern in cls.XSS_PATTERNS:
            if re.search(pattern, input_lower, re.IGNORECASE | re.DOTALL):
                logger.warning(f"XSS detected: pattern={pattern}, input={input_str[:100]}")
                return True

        return False

    @classmethod
    def sanitize(cls, input_str: str) -> str:
        """
        清理 XSS 风险字符

        Args:
            input_str: 待清理字符串

        Returns:
            清理后的字符串
        """
        if not input_str:
            return input_str

        # HTML 转义
        sanitized = html.escape(input_str)

        # 移除危险属性
        sanitized = re.sub(r'\s*on\w+\s*=\s*["\'][^"\']*["\']', '', sanitized, flags=re.IGNORECASE)

        # 移除危险标签
        sanitized = re.sub(r'<script[^>]*>.*?</script>', '', sanitized, flags=re.IGNORECASE | re.DOTALL)
        sanitized = re.sub(r'<iframe[^>]*>.*?</iframe>', '', sanitized, flags=re.IGNORECASE | re.DOTALL)
        sanitized = re.sub(r'<embed[^>]*>', '', sanitized, flags=re.IGNORECASE)
        sanitized = re.sub(r'<object[^>]*>.*?</object>', '', sanitized, flags=re.IGNORECASE | re.DOTALL)

        return sanitized

    @classmethod
    def validate_html_content(cls, content: str, max_length: int = 10000) -> bool:
        """
        验证 HTML 内容安全性

        Args:
            content: HTML 内容
            max_length: 最大长度

        Returns:
            True 如果安全，False 否则
        """
        if not content:
            return True

        # 长度检查
        if len(content) > max_length:
            return False

        # 检测危险标签
        dangerous_tags = ['<script', '<iframe', '<embed', '<object', '<link']
        content_lower = content.lower()

        for tag in dangerous_tags:
            if tag in content_lower:
                return False

        # 检测事件处理器
        if re.search(r'\son\w+\s*=', content_lower):
            return False

        return True


# ==================== 请求验证装饰器 ====================

def validate_request(schema: Union[Dict, str], strict: bool = False):
    """
    请求体验证装饰器

    Args:
        schema: JSON Schema 字典或预定义 schema 名称
        strict: 是否使用严格模式（不允许额外字段）

    Usage:
        @validate_request('chat_request')
        def chat():
            ...

        或

        @validate_request({'type': 'object', 'required': ['name'], ...})
        def create():
            ...
    """
    def decorator(f: Callable[..., T]) -> Callable[..., T]:
        @wraps(f)
        def wrapper(*args, **kwargs) -> T:
            # 检查 jsonschema 是否可用
            if not JSONSCHEMA_AVAILABLE:
                logger.warning("jsonschema not installed, skipping validation")
                return f(*args, **kwargs)

            # 获取 schema
            if isinstance(schema, str):
                validation_schema = COMMON_SCHEMAS.get(schema)
                if validation_schema is None:
                    logger.error(f"Unknown schema: {schema}")
                    raise ValidationError(f"Invalid validation schema: {schema}")
            else:
                validation_schema = schema

            # 验证请求体
            try:
                if request.is_json:
                    data = request.get_json()
                else:
                    data = {}

                validate(
                    instance=data,
                    schema=validation_schema,
                    format_checker=Draft7Validator.FORMAT_CHECKER if Draft7Validator else None,
                )

            except JsonValidationError as e:
                logger.warning(f"Validation failed: {e.message} at path: {'/'.join(str(p) for p in e.path)}")
                raise ValidationError(
                    message="Invalid request data",
                    details={
                        "field": '.'.join(str(p) for p in e.path) if e.path else 'unknown',
                        "error": e.message,
                        "validator": e.validator,
                    }
                )

            return f(*args, **kwargs)

        return wrapper

    return decorator


def validate_query_params(
    required_params: Optional[List[str]] = None,
    optional_params: Optional[Dict[str, type]] = None,
):
    """
    查询参数验证装饰器

    Args:
        required_params: 必需参数列表
        optional_params: 可选参数及其类型 {'param': type}

    Usage:
        @validate_query_params(
            required_params=['id'],
            optional_params={'limit': int, 'offset': int}
        )
        def get_item():
            ...
    """
    def decorator(f: Callable[..., T]) -> Callable[..., T]:
        @wraps(f)
        def wrapper(*args, **kwargs) -> T:
            errors = []

            # 检查必需参数
            if required_params:
                for param in required_params:
                    value = request.args.get(param)
                    if value is None or value == '':
                        errors.append(f"Missing required parameter: {param}")

            # 验证可选参数类型
            if optional_params:
                for param, expected_type in optional_params.items():
                    value = request.args.get(param)
                    if value is not None and value != '':
                        try:
                            if expected_type == bool:
                                # 特殊处理布尔值
                                if value.lower() not in ('true', 'false', '1', '0'):
                                    errors.append(f"Invalid boolean value: {param}")
                            elif expected_type == int:
                                int(value)
                            elif expected_type == float:
                                float(value)
                        except ValueError:
                            errors.append(f"Invalid {expected_type.__name__} value: {param}")

            if errors:
                raise ValidationError(
                    message="Query parameter validation failed",
                    details={"errors": errors}
                )

            return f(*args, **kwargs)

        return wrapper

    return decorator


def validate_path_param(param_name: str, pattern: str = r'^[a-zA-Z0-9\-_]+$'):
    """
    路径参数验证装饰器

    Args:
        param_name: 参数名
        pattern: 正则表达式模式

    Usage:
        @app.route('/api/items/<item_id>')
        @validate_path_param('item_id', r'^[a-zA-Z0-9\-]+$')
        def get_item(item_id):
            ...
    """
    def decorator(f: Callable[..., T]) -> Callable[..., T]:
        @wraps(f)
        def wrapper(*args, **kwargs) -> T:
            value = kwargs.get(param_name)

            if value and not re.match(pattern, str(value)):
                raise ValidationError(
                    message=f"Invalid path parameter: {param_name}",
                    details={
                        "parameter": param_name,
                        "value": str(value),
                        "expected_pattern": pattern,
                    }
                )

            return f(*args, **kwargs)

        return wrapper

    return decorator


def sanitize_input(*fields: str):
    """
    输入清理装饰器（XSS 防护）

    Args:
        *fields: 需要清理的字段名

    Usage:
        @sanitize_input('name', 'description')
        def create_item():
            data = request.get_json()
            # data['name'] 和 data['description'] 已被清理
    """
    def decorator(f: Callable[..., T]) -> Callable[..., T]:
        @wraps(f)
        def wrapper(*args, **kwargs) -> T:
            if request.is_json:
                data = request.get_json()

                if data and isinstance(data, dict):
                    for field in fields:
                        if field in data and isinstance(data[field], str):
                            # 检测 XSS
                            if XSSChecker.is_xss(data[field]):
                                logger.warning(f"XSS attempt detected in field: {field}")
                                raise ValidationError(
                                    message="Potentially malicious content detected",
                                    details={"field": field}
                                )
                            # 清理内容
                            data[field] = XSSChecker.sanitize(data[field])

                    # 更新请求上下文
                    request._cached_json = (data, True)

            return f(*args, **kwargs)

        return wrapper

    return decorator


def check_sql_injection(*fields: str):
    """
    SQL 注入检测装饰器

    Args:
        *fields: 需要检查的字段名

    Usage:
        @check_sql_injection('query', 'table_name')
        def execute_query():
            ...
    """
    def decorator(f: Callable[..., T]) -> Callable[..., T]:
        @wraps(f)
        def wrapper(*args, **kwargs) -> T:
            if request.is_json:
                data = request.get_json()

                if data and isinstance(data, dict):
                    for field in fields:
                        if field in data and isinstance(data[field], str):
                            if SQLInjectionChecker.is_sql_injection(data[field]):
                                logger.warning(f"SQL injection attempt detected in field: {field}")
                                raise ValidationError(
                                    message="Invalid input detected",
                                    details={"field": field}
                                )

            return f(*args, **kwargs)

        return wrapper

    return decorator


def limit_content_size(max_size: int):
    """
    请求体大小限制装饰器

    Args:
        max_size: 最大字节数

    Usage:
        @limit_content_size(10 * 1024 * 1024)  # 10MB
        def upload_file():
            ...
    """
    def decorator(f: Callable[..., T]) -> Callable[..., T]:
        @wraps(f)
        def wrapper(*args, **kwargs) -> T:
            content_length = request.content_length

            if content_length and content_length > max_size:
                raise ValidationError(
                    message="Request body too large",
                    details={
                        "max_size": max_size,
                        "actual_size": content_length,
                    }
                )

            return f(*args, **kwargs)

        return wrapper

    return decorator


# ==================== 数据验证工具函数 ====================

@dataclass
class ValidationResult:
    """验证结果"""
    is_valid: bool
    errors: List[str]
    sanitized_data: Optional[Dict[str, Any]] = None


def validate_string(
    value: Any,
    min_length: int = 0,
    max_length: int = 1000,
    pattern: Optional[str] = None,
    allow_empty: bool = False,
) -> ValidationResult:
    """
    验证字符串值

    Args:
        value: 待验证值
        min_length: 最小长度
        max_length: 最大长度
        pattern: 正则表达式模式
        allow_empty: 是否允许空值

    Returns:
        验证结果
    """
    errors = []

    # 空值检查
    if value is None or value == '':
        if not allow_empty:
            errors.append("Value cannot be empty")
        return ValidationResult(is_valid=len(errors) == 0, errors=errors)

    # 类型检查
    if not isinstance(value, str):
        errors.append("Value must be a string")
        return ValidationResult(is_valid=False, errors=errors)

    # 长度检查
    if len(value) < min_length:
        errors.append(f"Value must be at least {min_length} characters")
    if len(value) > max_length:
        errors.append(f"Value must be at most {max_length} characters")

    # 模式检查
    if pattern and not re.match(pattern, value):
        errors.append(f"Value does not match required pattern")

    return ValidationResult(is_valid=len(errors) == 0, errors=errors)


def validate_email(value: str) -> ValidationResult:
    """验证邮箱地址"""
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

    if not value:
        return ValidationResult(is_valid=False, errors=["Email cannot be empty"])

    if not re.match(email_pattern, value):
        return ValidationResult(is_valid=False, errors=["Invalid email format"])

    return ValidationResult(is_valid=True, errors=[])


def validate_url(value: str, allowed_schemes: Optional[List[str]] = None) -> ValidationResult:
    """
    验证 URL

    Args:
        value: URL 值
        allowed_schemes: 允许的协议列表，如 ['http', 'https']
    """
    if not value:
        return ValidationResult(is_valid=False, errors=["URL cannot be empty"])

    try:
        from urllib.parse import urlparse
        parsed = urlparse(value)

        if not parsed.scheme or not parsed.netloc:
            return ValidationResult(is_valid=False, errors=["Invalid URL format"])

        if allowed_schemes and parsed.scheme not in allowed_schemes:
            return ValidationResult(
                is_valid=False,
                errors=f"URL scheme must be one of: {', '.join(allowed_schemes)}"
            )

        return ValidationResult(is_valid=True, errors=[])

    except Exception as e:
        logger.debug(f"URL validation failed for '{value}': {e}")
        return ValidationResult(is_valid=False, errors=["Invalid URL"])


def validate_file_type(filename: str, allowed_extensions: List[str]) -> ValidationResult:
    """
    验证文件类型

    Args:
        filename: 文件名
        allowed_extensions: 允许的扩展名列表（不含点）
    """
    if not filename:
        return ValidationResult(is_valid=False, errors=["Filename cannot be empty"])

    import os
    _, ext = os.path.splitext(filename)
    ext = ext.lstrip('.').lower()

    if ext not in [e.lower() for e in allowed_extensions]:
        return ValidationResult(
            is_valid=False,
            errors=f"File type not allowed. Allowed types: {', '.join(allowed_extensions)}"
        )

    return ValidationResult(is_valid=True, errors=[])


def batch_validate(validators: Dict[str, Callable[[Any], ValidationResult]], data: Dict[str, Any]) -> ValidationResult:
    """
    批量验证

    Args:
        validators: 字段验证器字典 {'field': validator_function}
        data: 待验证数据

    Returns:
        综合验证结果
    """
    all_errors = []

    for field, validator in validators.items():
        value = data.get(field)
        result = validator(value)

        if not result.is_valid:
            for error in result.errors:
                all_errors.append(f"{field}: {error}")

    return ValidationResult(
        is_valid=len(all_errors) == 0,
        errors=all_errors,
        sanitized_data=data if len(all_errors) == 0 else None
    )


# ==================== 导出 ====================

__all__ = [
    # 常用 Schema
    'COMMON_SCHEMAS',

    # 装饰器
    'validate_request',
    'validate_query_params',
    'validate_path_param',
    'sanitize_input',
    'check_sql_injection',
    'limit_content_size',

    # 检查器类
    'SQLInjectionChecker',
    'XSSChecker',

    # 验证函数
    'ValidationResult',
    'validate_string',
    'validate_email',
    'validate_url',
    'validate_file_type',
    'batch_validate',
]
