"""
输入验证模块单元测试
Sprint 9: P2 测试覆盖 - 安全加固
"""

import pytest
from unittest.mock import patch, MagicMock


class TestCommonSchemas:
    """常用 Schema 测试"""

    def test_pagination_schema(self):
        """测试分页 Schema"""
        from services.shared.validation import COMMON_SCHEMAS

        schema = COMMON_SCHEMAS['pagination']

        assert schema['type'] == 'object'
        assert 'page' in schema['properties']
        assert 'page_size' in schema['properties']

    def test_chat_request_schema(self):
        """测试聊天请求 Schema"""
        from services.shared.validation import COMMON_SCHEMAS

        schema = COMMON_SCHEMAS['chat_request']

        assert 'message' in schema['required']
        assert schema['properties']['message']['maxLength'] == 10000

    def test_text2sql_request_schema(self):
        """测试 Text-to-SQL Schema"""
        from services.shared.validation import COMMON_SCHEMAS

        schema = COMMON_SCHEMAS['text2sql_request']

        assert 'natural_language' in schema['required']


class TestSQLInjectionChecker:
    """SQL 注入检测器测试"""

    def test_detect_select_injection(self):
        """测试检测 SELECT 注入"""
        from services.shared.validation import SQLInjectionChecker

        assert SQLInjectionChecker.is_sql_injection("SELECT * FROM users") is True

    def test_detect_union_injection(self):
        """测试检测 UNION 注入"""
        from services.shared.validation import SQLInjectionChecker

        assert SQLInjectionChecker.is_sql_injection("1 UNION SELECT password FROM users") is True

    def test_detect_drop_injection(self):
        """测试检测 DROP 注入"""
        from services.shared.validation import SQLInjectionChecker

        assert SQLInjectionChecker.is_sql_injection("; DROP TABLE users;") is True

    def test_detect_or_1_1(self):
        """测试检测 OR 1=1"""
        from services.shared.validation import SQLInjectionChecker

        assert SQLInjectionChecker.is_sql_injection("admin' OR 1=1 --") is True

    def test_detect_comment_injection(self):
        """测试检测注释注入"""
        from services.shared.validation import SQLInjectionChecker

        assert SQLInjectionChecker.is_sql_injection("admin'--") is True
        assert SQLInjectionChecker.is_sql_injection("admin'#") is True

    def test_safe_input(self):
        """测试安全输入"""
        from services.shared.validation import SQLInjectionChecker

        assert SQLInjectionChecker.is_sql_injection("John Doe") is False
        assert SQLInjectionChecker.is_sql_injection("user@example.com") is False

    def test_validate_identifier(self):
        """测试标识符验证"""
        from services.shared.validation import SQLInjectionChecker

        assert SQLInjectionChecker.validate_identifier("users") is True
        assert SQLInjectionChecker.validate_identifier("user_table") is True
        assert SQLInjectionChecker.validate_identifier("123invalid") is False
        assert SQLInjectionChecker.validate_identifier("user;drop") is False

    def test_validate_sql_value(self):
        """测试 SQL 值验证"""
        from services.shared.validation import SQLInjectionChecker

        assert SQLInjectionChecker.validate_sql_value("normal value") is True
        assert SQLInjectionChecker.validate_sql_value("value'") is False  # 未闭合引号


class TestXSSChecker:
    """XSS 检测器测试"""

    def test_detect_script_tag(self):
        """测试检测 script 标签"""
        from services.shared.validation import XSSChecker

        assert XSSChecker.is_xss("<script>alert('xss')</script>") is True

    def test_detect_event_handler(self):
        """测试检测事件处理器"""
        from services.shared.validation import XSSChecker

        assert XSSChecker.is_xss('<img onerror="alert(1)">') is True
        assert XSSChecker.is_xss('<div onclick="alert(1)">') is True

    def test_detect_javascript_protocol(self):
        """测试检测 javascript: 协议"""
        from services.shared.validation import XSSChecker

        assert XSSChecker.is_xss('javascript:alert(1)') is True

    def test_detect_iframe(self):
        """测试检测 iframe"""
        from services.shared.validation import XSSChecker

        assert XSSChecker.is_xss('<iframe src="evil.com">') is True

    def test_safe_input(self):
        """测试安全输入"""
        from services.shared.validation import XSSChecker

        assert XSSChecker.is_xss("Hello, World!") is False
        assert XSSChecker.is_xss("<p>Safe HTML</p>") is False

    def test_sanitize_script(self):
        """测试清理 script"""
        from services.shared.validation import XSSChecker

        result = XSSChecker.sanitize("<script>alert('xss')</script>")

        assert "<script>" not in result
        assert "alert" not in result.lower() or "&lt;" in result

    def test_sanitize_preserves_text(self):
        """测试清理保留文本"""
        from services.shared.validation import XSSChecker

        result = XSSChecker.sanitize("Hello World")

        assert result == "Hello World"

    def test_validate_html_content(self):
        """测试验证 HTML 内容"""
        from services.shared.validation import XSSChecker

        assert XSSChecker.validate_html_content("<p>Safe</p>") is True
        assert XSSChecker.validate_html_content("<script>evil</script>") is False
        assert XSSChecker.validate_html_content("<iframe>") is False
        assert XSSChecker.validate_html_content('<div onclick="evil">') is False


class TestValidationResult:
    """验证结果测试"""

    def test_valid_result(self):
        """测试有效结果"""
        from services.shared.validation import ValidationResult

        result = ValidationResult(is_valid=True, errors=[])

        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_invalid_result(self):
        """测试无效结果"""
        from services.shared.validation import ValidationResult

        result = ValidationResult(
            is_valid=False,
            errors=["Field required", "Invalid format"]
        )

        assert result.is_valid is False
        assert len(result.errors) == 2


class TestValidateString:
    """字符串验证测试"""

    def test_valid_string(self):
        """测试有效字符串"""
        from services.shared.validation import validate_string

        result = validate_string("Hello", min_length=1, max_length=100)

        assert result.is_valid is True

    def test_empty_string_not_allowed(self):
        """测试不允许空字符串"""
        from services.shared.validation import validate_string

        result = validate_string("", allow_empty=False)

        assert result.is_valid is False

    def test_empty_string_allowed(self):
        """测试允许空字符串"""
        from services.shared.validation import validate_string

        result = validate_string("", allow_empty=True)

        assert result.is_valid is True

    def test_string_too_short(self):
        """测试字符串太短"""
        from services.shared.validation import validate_string

        result = validate_string("ab", min_length=5)

        assert result.is_valid is False
        assert any("at least" in e for e in result.errors)

    def test_string_too_long(self):
        """测试字符串太长"""
        from services.shared.validation import validate_string

        result = validate_string("a" * 200, max_length=100)

        assert result.is_valid is False

    def test_string_pattern(self):
        """测试字符串模式"""
        from services.shared.validation import validate_string

        result = validate_string("abc123", pattern=r'^[a-z]+$')

        assert result.is_valid is False


class TestValidateEmail:
    """邮箱验证测试"""

    def test_valid_email(self):
        """测试有效邮箱"""
        from services.shared.validation import validate_email

        result = validate_email("user@example.com")

        assert result.is_valid is True

    def test_invalid_email(self):
        """测试无效邮箱"""
        from services.shared.validation import validate_email

        assert validate_email("invalid").is_valid is False
        assert validate_email("user@").is_valid is False
        assert validate_email("@example.com").is_valid is False


class TestValidateURL:
    """URL 验证测试"""

    def test_valid_url(self):
        """测试有效 URL"""
        from services.shared.validation import validate_url

        result = validate_url("https://example.com/path")

        assert result.is_valid is True

    def test_invalid_url(self):
        """测试无效 URL"""
        from services.shared.validation import validate_url

        assert validate_url("not-a-url").is_valid is False
        assert validate_url("").is_valid is False

    def test_url_scheme_restriction(self):
        """测试 URL 协议限制"""
        from services.shared.validation import validate_url

        result = validate_url("ftp://example.com", allowed_schemes=['http', 'https'])

        assert result.is_valid is False


class TestValidateFileType:
    """文件类型验证测试"""

    def test_allowed_extension(self):
        """测试允许的扩展名"""
        from services.shared.validation import validate_file_type

        result = validate_file_type("document.pdf", ["pdf", "doc", "docx"])

        assert result.is_valid is True

    def test_disallowed_extension(self):
        """测试不允许的扩展名"""
        from services.shared.validation import validate_file_type

        result = validate_file_type("script.exe", ["pdf", "doc"])

        assert result.is_valid is False

    def test_case_insensitive(self):
        """测试大小写不敏感"""
        from services.shared.validation import validate_file_type

        result = validate_file_type("document.PDF", ["pdf"])

        assert result.is_valid is True


class TestBatchValidate:
    """批量验证测试"""

    def test_all_valid(self):
        """测试全部有效"""
        from services.shared.validation import batch_validate, validate_string, validate_email

        validators = {
            'name': lambda x: validate_string(x, min_length=1),
            'email': validate_email
        }

        data = {'name': 'John', 'email': 'john@example.com'}
        result = batch_validate(validators, data)

        assert result.is_valid is True

    def test_some_invalid(self):
        """测试部分无效"""
        from services.shared.validation import batch_validate, validate_string, validate_email

        validators = {
            'name': lambda x: validate_string(x, min_length=1),
            'email': validate_email
        }

        data = {'name': '', 'email': 'invalid'}
        result = batch_validate(validators, data)

        assert result.is_valid is False
        assert len(result.errors) >= 2
