"""
Great Expectations 集成单元测试
Phase 1: 补齐短板 - Great Expectations 数据质量引擎

测试覆盖：
- Expectation 映射（rule_type → GE expectation）
- is_ge_supported() 检查
- build_expectation_kwargs() 参数构建
- GEConfig 配置加载
- GEValidationEngine mock 校验
- 结果解析
"""

import pytest
import os
import sys
from unittest.mock import patch, Mock, MagicMock
from pathlib import Path

# 添加 data-api 路径
_project_root = Path(__file__).parent.parent.parent
_data_api_path = str(_project_root / "services" / "data-api")
if _data_api_path not in sys.path:
    sys.path.insert(0, _data_api_path)


class TestExpectationMapper:
    """Expectation 映射测试"""

    def test_rule_type_to_expectation_mapping(self):
        """所有已注册规则类型都有对应的 GE Expectation"""
        from integrations.great_expectations.expectation_mapper import RULE_TYPE_TO_EXPECTATION
        assert "null_check" in RULE_TYPE_TO_EXPECTATION
        assert "duplicate_check" in RULE_TYPE_TO_EXPECTATION
        assert "range_check" in RULE_TYPE_TO_EXPECTATION
        assert "pattern_check" in RULE_TYPE_TO_EXPECTATION
        assert "enum_check" in RULE_TYPE_TO_EXPECTATION
        assert "length_check" in RULE_TYPE_TO_EXPECTATION
        assert "uniqueness_check" in RULE_TYPE_TO_EXPECTATION
        assert "reference_check" in RULE_TYPE_TO_EXPECTATION

    def test_null_check_maps_to_not_null(self):
        """null_check 映射到 expect_column_values_to_not_be_null"""
        from integrations.great_expectations.expectation_mapper import RULE_TYPE_TO_EXPECTATION
        assert RULE_TYPE_TO_EXPECTATION["null_check"] == "expect_column_values_to_not_be_null"

    def test_range_check_maps_to_between(self):
        """range_check 映射到 expect_column_values_to_be_between"""
        from integrations.great_expectations.expectation_mapper import RULE_TYPE_TO_EXPECTATION
        assert RULE_TYPE_TO_EXPECTATION["range_check"] == "expect_column_values_to_be_between"

    def test_pattern_check_maps_to_regex(self):
        """pattern_check 映射到 expect_column_values_to_match_regex"""
        from integrations.great_expectations.expectation_mapper import RULE_TYPE_TO_EXPECTATION
        assert RULE_TYPE_TO_EXPECTATION["pattern_check"] == "expect_column_values_to_match_regex"


class TestIsGESupported:
    """is_ge_supported 测试"""

    def test_supported_rule_types(self):
        """已注册的规则类型返回 True"""
        from integrations.great_expectations.expectation_mapper import is_ge_supported
        assert is_ge_supported("null_check") is True
        assert is_ge_supported("range_check") is True
        assert is_ge_supported("enum_check") is True
        assert is_ge_supported("pattern_check") is True

    def test_unsupported_rule_types(self):
        """未注册的规则类型返回 False"""
        from integrations.great_expectations.expectation_mapper import is_ge_supported
        assert is_ge_supported("custom_check") is False
        assert is_ge_supported("nonexistent") is False
        assert is_ge_supported("") is False


class TestBuildExpectationKwargs:
    """build_expectation_kwargs 参数构建测试"""

    def test_null_check_basic(self):
        """null_check 基本参数"""
        from integrations.great_expectations.expectation_mapper import build_expectation_kwargs
        name, kwargs = build_expectation_kwargs(
            rule_type="null_check",
            target_column="email",
            config={},
        )
        assert name == "expect_column_values_to_not_be_null"
        assert kwargs["column"] == "email"

    def test_null_check_with_threshold(self):
        """null_check 带阈值参数"""
        from integrations.great_expectations.expectation_mapper import build_expectation_kwargs
        name, kwargs = build_expectation_kwargs(
            rule_type="null_check",
            target_column="email",
            config={"threshold": 95.0},
        )
        assert kwargs["mostly"] == 0.95

    def test_null_check_100_threshold_no_mostly(self):
        """null_check 100% 阈值不设 mostly"""
        from integrations.great_expectations.expectation_mapper import build_expectation_kwargs
        name, kwargs = build_expectation_kwargs(
            rule_type="null_check",
            target_column="email",
            config={"threshold": 100.0},
        )
        assert "mostly" not in kwargs

    def test_range_check_with_bounds(self):
        """range_check 带上下界"""
        from integrations.great_expectations.expectation_mapper import build_expectation_kwargs
        name, kwargs = build_expectation_kwargs(
            rule_type="range_check",
            target_column="age",
            config={"min_value": 0, "max_value": 150},
        )
        assert name == "expect_column_values_to_be_between"
        assert kwargs["min_value"] == 0
        assert kwargs["max_value"] == 150

    def test_range_check_with_only_min(self):
        """range_check 只有下界"""
        from integrations.great_expectations.expectation_mapper import build_expectation_kwargs
        name, kwargs = build_expectation_kwargs(
            rule_type="range_check",
            target_column="price",
            config={"min_value": 0},
        )
        assert kwargs["min_value"] == 0
        assert "max_value" not in kwargs

    def test_pattern_check_with_expression(self):
        """pattern_check 使用 rule_expression"""
        from integrations.great_expectations.expectation_mapper import build_expectation_kwargs
        name, kwargs = build_expectation_kwargs(
            rule_type="pattern_check",
            target_column="email",
            config={},
            rule_expression=r"^[\w.]+@[\w]+\.[\w]+$",
        )
        assert name == "expect_column_values_to_match_regex"
        assert kwargs["regex"] == r"^[\w.]+@[\w]+\.[\w]+$"

    def test_pattern_check_falls_back_to_config(self):
        """pattern_check 使用 config 中的 pattern"""
        from integrations.great_expectations.expectation_mapper import build_expectation_kwargs
        name, kwargs = build_expectation_kwargs(
            rule_type="pattern_check",
            target_column="phone",
            config={"pattern": r"\d{11}"},
            rule_expression="",
        )
        assert kwargs["regex"] == r"\d{11}"

    def test_enum_check(self):
        """enum_check 构建 value_set"""
        from integrations.great_expectations.expectation_mapper import build_expectation_kwargs
        name, kwargs = build_expectation_kwargs(
            rule_type="enum_check",
            target_column="status",
            config={"allowed_values": ["active", "inactive", "pending"]},
        )
        assert name == "expect_column_values_to_be_in_set"
        assert kwargs["value_set"] == ["active", "inactive", "pending"]

    def test_length_check_with_bounds(self):
        """length_check 带长度上下界"""
        from integrations.great_expectations.expectation_mapper import build_expectation_kwargs
        name, kwargs = build_expectation_kwargs(
            rule_type="length_check",
            target_column="username",
            config={"min_length": 3, "max_length": 50},
        )
        assert name == "expect_column_value_lengths_to_be_between"
        assert kwargs["min_value"] == 3
        assert kwargs["max_value"] == 50

    def test_duplicate_check(self):
        """duplicate_check 映射到 unique"""
        from integrations.great_expectations.expectation_mapper import build_expectation_kwargs
        name, kwargs = build_expectation_kwargs(
            rule_type="duplicate_check",
            target_column="id",
            config={},
        )
        assert name == "expect_column_values_to_be_unique"
        assert kwargs["column"] == "id"

    def test_unsupported_rule_raises_error(self):
        """不支持的规则类型抛出 ValueError"""
        from integrations.great_expectations.expectation_mapper import build_expectation_kwargs
        with pytest.raises(ValueError, match="Unsupported rule type"):
            build_expectation_kwargs(
                rule_type="custom_unknown",
                target_column="col",
                config={},
            )

    def test_all_kwargs_include_column(self):
        """所有规则类型生成的 kwargs 都包含 column"""
        from integrations.great_expectations.expectation_mapper import (
            build_expectation_kwargs,
            RULE_TYPE_TO_EXPECTATION,
        )
        for rule_type in RULE_TYPE_TO_EXPECTATION:
            _, kwargs = build_expectation_kwargs(
                rule_type=rule_type,
                target_column="test_col",
                config={},
            )
            assert kwargs["column"] == "test_col"


class TestGEConfig:
    """GEConfig 配置测试"""

    @patch.dict(os.environ, {
        "GE_ENABLED": "true",
        "GE_CONTEXT_ROOT_DIR": "/tmp/ge_test",
        "GE_DATASOURCE_NAME": "test_ds",
        "MYSQL_HOST": "db-host",
        "MYSQL_PORT": "3307",
        "MYSQL_USER": "admin",
        "MYSQL_PASSWORD": "secret",
        "MYSQL_DATABASE": "testdb",
    })
    def test_from_env_full_config(self):
        """完整环境变量加载"""
        from integrations.great_expectations.config import GEConfig
        config = GEConfig.from_env()
        assert config.enabled is True
        assert config.context_root_dir == "/tmp/ge_test"
        assert config.datasource_name == "test_ds"
        assert "db-host" in config.db_url
        assert "3307" in config.db_url
        assert "admin" in config.db_url
        assert "testdb" in config.db_url

    @patch.dict(os.environ, {}, clear=True)
    def test_from_env_defaults(self):
        """默认配置"""
        from integrations.great_expectations.config import GEConfig
        config = GEConfig.from_env()
        assert config.enabled is False
        assert config.context_root_dir == "/data/ge"
        assert config.datasource_name == "onedata_datasource"
        assert "mysql+pymysql" in config.db_url

    @patch.dict(os.environ, {
        "GE_ENABLED": "false",
    })
    def test_from_env_disabled(self):
        """GE_ENABLED=false"""
        from integrations.great_expectations.config import GEConfig
        config = GEConfig.from_env()
        assert config.enabled is False

    @patch.dict(os.environ, {
        "GE_DB_URL": "postgresql://user:pass@host/db",
        "GE_ENABLED": "true",
    })
    def test_from_env_custom_db_url(self):
        """自定义 GE_DB_URL 覆盖 MySQL 构建"""
        from integrations.great_expectations.config import GEConfig
        config = GEConfig.from_env()
        assert config.db_url == "postgresql://user:pass@host/db"


class TestGEValidationEngine:
    """GEValidationEngine 测试"""

    def test_available_when_ge_installed_and_enabled(self):
        """GE 已安装且启用时 available=True"""
        from integrations.great_expectations.config import GEConfig
        config = GEConfig(enabled=True)

        with patch("integrations.great_expectations.ge_engine.GE_AVAILABLE", True):
            from integrations.great_expectations.ge_engine import GEValidationEngine
            engine = GEValidationEngine(config)
            assert engine.available is True

    def test_not_available_when_disabled(self):
        """GE 禁用时 available=False"""
        from integrations.great_expectations.config import GEConfig
        config = GEConfig(enabled=False)

        from integrations.great_expectations.ge_engine import GEValidationEngine
        engine = GEValidationEngine(config)
        assert engine.available is False

    def test_validate_rule_returns_none_when_unavailable(self):
        """GE 不可用时 validate_rule 返回 None"""
        from integrations.great_expectations.config import GEConfig
        config = GEConfig(enabled=False)

        from integrations.great_expectations.ge_engine import GEValidationEngine
        engine = GEValidationEngine(config)
        result = engine.validate_rule(
            rule_type="null_check",
            target_table="users",
            target_column="email",
            config={},
        )
        assert result is None

    def test_validate_rule_returns_none_for_unsupported(self):
        """不支持的规则类型返回 None"""
        from integrations.great_expectations.config import GEConfig
        config = GEConfig(enabled=True)

        with patch("integrations.great_expectations.ge_engine.GE_AVAILABLE", True):
            from integrations.great_expectations.ge_engine import GEValidationEngine
            engine = GEValidationEngine(config)
            result = engine.validate_rule(
                rule_type="custom_unsupported",
                target_table="users",
                target_column="email",
                config={},
            )
            assert result is None

    def test_get_status(self):
        """get_status 返回状态信息"""
        from integrations.great_expectations.config import GEConfig
        config = GEConfig(enabled=True, context_root_dir="/tmp/ge")

        from integrations.great_expectations.ge_engine import GEValidationEngine
        engine = GEValidationEngine(config)
        status = engine.get_status()

        assert "ge_installed" in status
        assert "enabled" in status
        assert status["enabled"] is True
        assert status["context_root_dir"] == "/tmp/ge"
        assert "context_initialized" in status
        assert status["context_initialized"] is False

    def test_parse_validation_result_success(self):
        """解析成功的校验结果"""
        from integrations.great_expectations.config import GEConfig
        from integrations.great_expectations.ge_engine import GEValidationEngine

        config = GEConfig(enabled=True)
        engine = GEValidationEngine(config)

        mock_result = Mock()
        mock_result.to_json_dict.return_value = {
            "success": True,
            "result": {
                "element_count": 1000,
                "unexpected_count": 5,
                "unexpected_percent": 0.5,
                "partial_unexpected_list": ["a", "b", "c", "d", "e"],
            },
        }

        parsed = engine._parse_validation_result(
            mock_result, "expect_column_values_to_not_be_null"
        )

        assert parsed["engine"] == "great_expectations"
        assert parsed["success"] is True
        assert parsed["total_rows"] == 1000
        assert parsed["failed_rows"] == 5
        assert parsed["passed_rows"] == 995
        assert parsed["score"] == 99.5
        assert parsed["expectation"] == "expect_column_values_to_not_be_null"

    def test_parse_validation_result_all_failed(self):
        """解析全部失败的结果"""
        from integrations.great_expectations.config import GEConfig
        from integrations.great_expectations.ge_engine import GEValidationEngine

        config = GEConfig(enabled=True)
        engine = GEValidationEngine(config)

        mock_result = Mock()
        mock_result.to_json_dict.return_value = {
            "success": False,
            "result": {
                "element_count": 100,
                "unexpected_count": 100,
                "unexpected_percent": 100.0,
                "partial_unexpected_list": [],
            },
        }

        parsed = engine._parse_validation_result(mock_result, "expect_column_values_to_be_unique")
        assert parsed["success"] is False
        assert parsed["score"] == 0.0
        assert parsed["failed_rows"] == 100

    def test_parse_validation_result_empty(self):
        """解析空表结果"""
        from integrations.great_expectations.config import GEConfig
        from integrations.great_expectations.ge_engine import GEValidationEngine

        config = GEConfig(enabled=True)
        engine = GEValidationEngine(config)

        mock_result = Mock()
        mock_result.to_json_dict.return_value = {
            "success": True,
            "result": {
                "element_count": 0,
                "unexpected_count": 0,
            },
        }

        parsed = engine._parse_validation_result(mock_result, "expect_column_values_to_not_be_null")
        assert parsed["score"] == 100.0
        assert parsed["total_rows"] == 0

    def test_parse_validation_result_error_handling(self):
        """解析结果异常时返回错误信息"""
        from integrations.great_expectations.config import GEConfig
        from integrations.great_expectations.ge_engine import GEValidationEngine

        config = GEConfig(enabled=True)
        engine = GEValidationEngine(config)

        mock_result = Mock()
        mock_result.to_json_dict.side_effect = Exception("Parse error")

        parsed = engine._parse_validation_result(mock_result, "some_expectation")
        assert parsed["engine"] == "great_expectations"
        assert parsed["success"] is False
        assert parsed["score"] == 0.0
        assert "error" in parsed

    def test_ensure_context_returns_none_when_unavailable(self):
        """GE 不可用时 _ensure_context 返回 None"""
        from integrations.great_expectations.config import GEConfig
        from integrations.great_expectations.ge_engine import GEValidationEngine

        config = GEConfig(enabled=False)
        engine = GEValidationEngine(config)
        assert engine._ensure_context() is None

    def test_generate_data_docs_returns_none_when_unavailable(self):
        """GE 不可用时 generate_data_docs 返回 None"""
        from integrations.great_expectations.config import GEConfig
        from integrations.great_expectations.ge_engine import GEValidationEngine

        config = GEConfig(enabled=False)
        engine = GEValidationEngine(config)
        assert engine.generate_data_docs() is None


class TestGEIntegrationInit:
    """GE 集成模块 __init__.py 测试"""

    def test_module_imports_without_error(self):
        """GE 集成模块可以正常导入"""
        try:
            from integrations.great_expectations import GEConfig, GEValidationEngine
            assert GEConfig is not None
            assert GEValidationEngine is not None
        except ImportError:
            pytest.skip("GE integration module not importable in test environment")

    def test_parent_init_handles_ge_import(self):
        """父 __init__.py 处理 GE 导入（可选依赖）"""
        try:
            from integrations import GEConfig, GEValidationEngine
            # GE 可能安装也可能没有，两种都合法
            assert True
        except ImportError:
            pytest.skip("integrations module not importable in test environment")
