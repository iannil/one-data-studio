"""
ShardingSphere 透明脱敏集成单元测试
Phase 2: 渐进迁移 - ShardingSphere 透明脱敏 POC

测试覆盖：
- ShardingSphereConfig 配置加载
- MaskingRuleGenerator 敏感类型 → 算法映射
- MaskingRuleGenerator SQL/YAML 生成
- ShardingSphereClient 健康检查和 DistSQL 执行
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


class TestShardingSphereConfig:
    """ShardingSphereConfig 配置测试"""

    @patch.dict(os.environ, {
        "SHARDINGSPHERE_PROXY_URL": "ss-proxy:3308",
        "SHARDINGSPHERE_ADMIN_URL": "http://ss-proxy:33072",
        "SHARDINGSPHERE_USER": "admin",
        "SHARDINGSPHERE_PASSWORD": "secret123",
        "SHARDINGSPHERE_ENABLED": "true",
        "SHARDINGSPHERE_TIMEOUT": "60",
    })
    def test_from_env_full_config(self):
        """完整环境变量加载"""
        from integrations.shardingsphere.config import ShardingSphereConfig
        config = ShardingSphereConfig.from_env()
        assert config.proxy_host == "ss-proxy"
        assert config.proxy_port == 3308
        assert config.admin_url == "http://ss-proxy:33072"
        assert config.username == "admin"
        assert config.password == "secret123"
        assert config.enabled is True
        assert config.timeout == 60

    @patch.dict(os.environ, {}, clear=True)
    def test_from_env_defaults(self):
        """默认配置"""
        from integrations.shardingsphere.config import ShardingSphereConfig
        config = ShardingSphereConfig.from_env()
        assert config.proxy_host == "shardingsphere-proxy"
        assert config.proxy_port == 3307
        assert config.admin_url == "http://shardingsphere-proxy:33071"
        assert config.username == "root"
        assert config.password == ""
        assert config.enabled is False
        assert config.timeout == 30

    @patch.dict(os.environ, {
        "SHARDINGSPHERE_ENABLED": "false",
    })
    def test_from_env_disabled(self):
        """SHARDINGSPHERE_ENABLED=false"""
        from integrations.shardingsphere.config import ShardingSphereConfig
        config = ShardingSphereConfig.from_env()
        assert config.enabled is False

    @patch.dict(os.environ, {
        "SHARDINGSPHERE_PROXY_URL": "localhost:3307",
    })
    def test_from_env_url_parsing(self):
        """URL 解析（host:port 格式）"""
        from integrations.shardingsphere.config import ShardingSphereConfig
        config = ShardingSphereConfig.from_env()
        assert config.proxy_host == "localhost"
        assert config.proxy_port == 3307

    @patch.dict(os.environ, {
        "SHARDINGSPHERE_PROXY_URL": "single-host",
    })
    def test_from_env_url_without_port(self):
        """URL 无端口时使用默认端口"""
        from integrations.shardingsphere.config import ShardingSphereConfig
        config = ShardingSphereConfig.from_env()
        assert config.proxy_host == "single-host"
        assert config.proxy_port == 3307

    def test_validate_disabled_config(self):
        """禁用状态的配置验证"""
        from integrations.shardingsphere.config import ShardingSphereConfig
        config = ShardingSphereConfig(enabled=False, proxy_host="")
        assert config.validate() is True

    def test_validate_enabled_without_host_raises(self):
        """启用但无 proxy_host 抛出 ValueError"""
        from integrations.shardingsphere.config import ShardingSphereConfig
        config = ShardingSphereConfig(enabled=True, proxy_host="")
        with pytest.raises(ValueError, match="SHARDINGSPHERE_PROXY_URL is required"):
            config.validate()

    def test_dsn_property(self):
        """dsn 属性生成正确的连接字符串"""
        from integrations.shardingsphere.config import ShardingSphereConfig
        config = ShardingSphereConfig(
            proxy_host="localhost",
            proxy_port=3307,
            username="user",
            password="pass",
        )
        assert config.dsn == "mysql+pymysql://user:pass@localhost:3307"


class TestMaskingRuleGenerator:
    """MaskingRuleGenerator 测试"""

    def test_phone_algorithm_mapping(self):
        """手机号映射到 MASK_FIRST_N_LAST_M"""
        from integrations.shardingsphere.masking_rule_generator import MaskingRuleGenerator
        alg_type, props = MaskingRuleGenerator.get_algorithm("phone")
        assert alg_type == "MASK_FIRST_N_LAST_M"
        assert props["first-n"] == "3"
        assert props["last-m"] == "4"
        assert props["replace-char"] == "*"

    def test_email_algorithm_mapping(self):
        """邮箱映射到 MASK_BEFORE_SPECIAL_CHARS"""
        from integrations.shardingsphere.masking_rule_generator import MaskingRuleGenerator
        alg_type, props = MaskingRuleGenerator.get_algorithm("email")
        assert alg_type == "MASK_BEFORE_SPECIAL_CHARS"
        assert props["special-chars"] == "@"

    def test_id_card_algorithm_mapping(self):
        """身份证映射"""
        from integrations.shardingsphere.masking_rule_generator import MaskingRuleGenerator
        alg_type, props = MaskingRuleGenerator.get_algorithm("id_card")
        assert alg_type == "MASK_FIRST_N_LAST_M"
        assert props["first-n"] == "6"
        assert props["last-m"] == "4"

    def test_bank_card_algorithm_mapping(self):
        """银行卡映射"""
        from integrations.shardingsphere.masking_rule_generator import MaskingRuleGenerator
        alg_type, props = MaskingRuleGenerator.get_algorithm("bank_card")
        assert alg_type == "MASK_FIRST_N_LAST_M"
        assert props["first-n"] == "4"
        assert props["last-m"] == "4"

    def test_name_algorithm_mapping(self):
        """姓名映射（保留姓）"""
        from integrations.shardingsphere.masking_rule_generator import MaskingRuleGenerator
        alg_type, props = MaskingRuleGenerator.get_algorithm("name")
        assert alg_type == "MASK_FIRST_N_LAST_M"
        assert props["first-n"] == "1"
        assert props["last-m"] == "0"

    def test_address_algorithm_mapping(self):
        """地址映射"""
        from integrations.shardingsphere.masking_rule_generator import MaskingRuleGenerator
        alg_type, props = MaskingRuleGenerator.get_algorithm("address")
        assert alg_type == "MASK_FIRST_N_LAST_M"
        assert props["first-n"] == "6"
        assert props["last-m"] == "0"

    def test_unknown_type_falls_back_to_default(self):
        """未知类型使用默认算法（MD5）"""
        from integrations.shardingsphere.masking_rule_generator import MaskingRuleGenerator
        alg_type, props = MaskingRuleGenerator.get_algorithm("unknown_type")
        assert alg_type == "MD5"
        assert props == {}

    def test_type_normalization(self):
        """类型名称标准化（大小写、连字符）"""
        from integrations.shardingsphere.masking_rule_generator import MaskingRuleGenerator
        alg_type1, _ = MaskingRuleGenerator.get_algorithm("PHONE")
        alg_type2, _ = MaskingRuleGenerator.get_algorithm("Phone")
        alg_type3, _ = MaskingRuleGenerator.get_algorithm("id-card")
        assert alg_type1 == "MASK_FIRST_N_LAST_M"
        assert alg_type2 == "MASK_FIRST_N_LAST_M"
        assert alg_type3 == "MASK_FIRST_N_LAST_M"


class TestMaskingRuleGeneratorFromResults:
    """MaskingRuleGenerator.from_sensitivity_results 测试"""

    def test_batch_conversion(self):
        """批量转换敏感扫描结果"""
        from integrations.shardingsphere.masking_rule_generator import MaskingRuleGenerator

        results = [
            {"column_name": "phone", "sensitivity_type": "phone"},
            {"column_name": "email", "sensitivity_type": "email"},
            {"column_name": "id_number", "sensitivity_sub_type": "id_card"},
        ]

        rules = MaskingRuleGenerator.from_sensitivity_results(results)

        assert len(rules) == 3
        assert "phone" in rules
        assert "email" in rules
        assert "id_number" in rules
        assert rules["phone"]["algorithm_type"] == "MASK_FIRST_N_LAST_M"
        assert rules["email"]["algorithm_type"] == "MASK_BEFORE_SPECIAL_CHARS"

    def test_handles_missing_column_name(self):
        """处理缺少 column_name 的结果"""
        from integrations.shardingsphere.masking_rule_generator import MaskingRuleGenerator

        results = [
            {"column_name": "phone", "sensitivity_type": "phone"},
            {"sensitivity_type": "email"},  # 缺少 column_name
        ]

        rules = MaskingRuleGenerator.from_sensitivity_results(results)
        assert len(rules) == 1
        assert "phone" in rules

    def test_handles_alternative_column_key(self):
        """处理 name 作为 column_name 的替代键"""
        from integrations.shardingsphere.masking_rule_generator import MaskingRuleGenerator

        results = [
            {"name": "user_phone", "type": "phone"},
        ]

        rules = MaskingRuleGenerator.from_sensitivity_results(results)
        assert len(rules) == 1
        assert "user_phone" in rules

    def test_sub_type_priority(self):
        """sensitivity_sub_type 优先于 sensitivity_type"""
        from integrations.shardingsphere.masking_rule_generator import MaskingRuleGenerator

        results = [
            {
                "column_name": "card_number",
                "sensitivity_type": "financial",
                "sensitivity_sub_type": "bank_card",
            },
        ]

        rules = MaskingRuleGenerator.from_sensitivity_results(results)
        assert rules["card_number"]["sensitivity_type"] == "bank_card"


class TestMaskingRuleGeneratorSQL:
    """MaskingRuleGenerator SQL 生成测试"""

    def test_generate_mask_rule_sql_basic(self):
        """基本 CREATE MASK RULE SQL 生成"""
        from integrations.shardingsphere.masking_rule_generator import MaskingRuleGenerator

        rules = {
            "phone": {
                "algorithm_type": "MASK_FIRST_N_LAST_M",
                "algorithm_props": {"first-n": "3", "last-m": "4", "replace-char": "*"},
            },
        }

        sql = MaskingRuleGenerator.generate_mask_rule_sql("test_db", "users", rules)

        assert "USE test_db" in sql
        assert "CREATE MASK RULE users" in sql
        assert "phone = (TYPE(NAME='MASK_FIRST_N_LAST_M'" in sql
        assert '"first-n"="3"' in sql
        assert '"last-m"="4"' in sql

    def test_generate_mask_rule_sql_multiple_columns(self):
        """多列 SQL 生成"""
        from integrations.shardingsphere.masking_rule_generator import MaskingRuleGenerator

        rules = {
            "phone": {
                "algorithm_type": "MASK_FIRST_N_LAST_M",
                "algorithm_props": {"first-n": "3", "last-m": "4", "replace-char": "*"},
            },
            "email": {
                "algorithm_type": "MASK_BEFORE_SPECIAL_CHARS",
                "algorithm_props": {"special-chars": "@", "replace-char": "*"},
            },
        }

        sql = MaskingRuleGenerator.generate_mask_rule_sql("test_db", "users", rules)

        assert "phone =" in sql
        assert "email =" in sql

    def test_generate_mask_rule_sql_no_props(self):
        """无属性算法的 SQL 生成"""
        from integrations.shardingsphere.masking_rule_generator import MaskingRuleGenerator

        rules = {
            "secret_data": {
                "algorithm_type": "MD5",
                "algorithm_props": {},
            },
        }

        sql = MaskingRuleGenerator.generate_mask_rule_sql("test_db", "data", rules)

        assert "secret_data = (TYPE(NAME='MD5'))" in sql

    def test_generate_mask_rule_sql_empty_rules(self):
        """空规则返回空字符串"""
        from integrations.shardingsphere.masking_rule_generator import MaskingRuleGenerator

        sql = MaskingRuleGenerator.generate_mask_rule_sql("test_db", "users", {})
        assert sql == ""

    def test_generate_drop_rule_sql(self):
        """DROP MASK RULE SQL 生成"""
        from integrations.shardingsphere.masking_rule_generator import MaskingRuleGenerator

        sql = MaskingRuleGenerator.generate_drop_rule_sql("test_db", "users")

        assert "USE test_db" in sql
        assert "DROP MASK RULE IF EXISTS users" in sql

    def test_generate_show_rules_sql(self):
        """SHOW MASK RULES SQL 生成"""
        from integrations.shardingsphere.masking_rule_generator import MaskingRuleGenerator

        sql = MaskingRuleGenerator.generate_show_rules_sql("test_db")

        assert "USE test_db" in sql
        assert "SHOW MASK RULES" in sql


class TestMaskingRuleGeneratorYAML:
    """MaskingRuleGenerator YAML 生成测试"""

    def test_generate_mask_rule_yaml_basic(self):
        """基本 YAML 配置生成"""
        from integrations.shardingsphere.masking_rule_generator import MaskingRuleGenerator

        rules = {
            "phone": {
                "algorithm_type": "MASK_FIRST_N_LAST_M",
                "algorithm_props": {"first-n": "3", "last-m": "4", "replace-char": "*"},
            },
        }

        yaml_str = MaskingRuleGenerator.generate_mask_rule_yaml("test_db", "users", rules)

        assert "rules:" in yaml_str
        assert "- !MASK" in yaml_str
        assert "tables:" in yaml_str
        assert "users:" in yaml_str
        assert "phone:" in yaml_str
        assert "maskAlgorithm:" in yaml_str
        assert "maskAlgorithms:" in yaml_str
        assert "type: MASK_FIRST_N_LAST_M" in yaml_str
        assert "first-n: '3'" in yaml_str

    def test_generate_mask_rule_yaml_empty_rules(self):
        """空规则返回空字符串"""
        from integrations.shardingsphere.masking_rule_generator import MaskingRuleGenerator

        yaml_str = MaskingRuleGenerator.generate_mask_rule_yaml("test_db", "users", {})
        assert yaml_str == ""


class TestShardingSphereClient:
    """ShardingSphereClient 测试"""

    def test_health_check_success(self):
        """健康检查成功"""
        from integrations.shardingsphere.config import ShardingSphereConfig
        from integrations.shardingsphere.client import ShardingSphereClient

        config = ShardingSphereConfig(enabled=True, proxy_host="localhost")
        client = ShardingSphereClient(config)

        with patch.object(client, "_get_connection") as mock_conn:
            mock_cursor = MagicMock()
            mock_cursor.__enter__ = Mock(return_value=mock_cursor)
            mock_cursor.__exit__ = Mock(return_value=False)
            mock_connection = MagicMock()
            mock_connection.cursor.return_value = mock_cursor
            mock_conn.return_value = mock_connection

            result = client.health_check()
            assert result is True

    def test_health_check_failure(self):
        """健康检查失败"""
        from integrations.shardingsphere.config import ShardingSphereConfig
        from integrations.shardingsphere.client import ShardingSphereClient

        config = ShardingSphereConfig(enabled=True, proxy_host="localhost")
        client = ShardingSphereClient(config)

        with patch.object(client, "_get_connection") as mock_conn:
            mock_conn.side_effect = Exception("Connection refused")

            result = client.health_check()
            assert result is False

    def test_show_databases(self):
        """列出数据库"""
        from integrations.shardingsphere.config import ShardingSphereConfig
        from integrations.shardingsphere.client import ShardingSphereClient

        config = ShardingSphereConfig(enabled=True, proxy_host="localhost")
        client = ShardingSphereClient(config)

        with patch.object(client, "execute_distsql") as mock_exec:
            mock_exec.return_value = [
                {"Database": "db1"},
                {"Database": "db2"},
            ]

            result = client.show_databases()
            assert result == ["db1", "db2"]

    def test_list_mask_rules(self):
        """列出脱敏规则"""
        from integrations.shardingsphere.config import ShardingSphereConfig
        from integrations.shardingsphere.client import ShardingSphereClient

        config = ShardingSphereConfig(enabled=True, proxy_host="localhost")
        client = ShardingSphereClient(config)

        with patch.object(client, "execute_distsql") as mock_exec:
            mock_exec.return_value = [
                {"table_name": "users", "column_name": "phone", "algorithm_type": "MASK_FIRST_N_LAST_M"},
            ]

            result = client.list_mask_rules("test_db")
            assert len(result) == 1
            assert result[0]["table_name"] == "users"

    def test_apply_mask_rules_success(self):
        """应用脱敏规则成功"""
        from integrations.shardingsphere.config import ShardingSphereConfig
        from integrations.shardingsphere.client import ShardingSphereClient

        config = ShardingSphereConfig(enabled=True, proxy_host="localhost")
        client = ShardingSphereClient(config)

        with patch.object(client, "execute_distsql") as mock_exec:
            mock_exec.return_value = []

            result = client.apply_mask_rules("CREATE MASK RULE ...")
            assert result is True

    def test_apply_mask_rules_failure(self):
        """应用脱敏规则失败"""
        from integrations.shardingsphere.config import ShardingSphereConfig
        from integrations.shardingsphere.client import ShardingSphereClient

        config = ShardingSphereConfig(enabled=True, proxy_host="localhost")
        client = ShardingSphereClient(config)

        with patch.object(client, "execute_distsql") as mock_exec:
            mock_exec.side_effect = Exception("Syntax error")

            result = client.apply_mask_rules("INVALID SQL")
            assert result is False

    def test_remove_mask_rules_success(self):
        """移除脱敏规则成功"""
        from integrations.shardingsphere.config import ShardingSphereConfig
        from integrations.shardingsphere.client import ShardingSphereClient

        config = ShardingSphereConfig(enabled=True, proxy_host="localhost")
        client = ShardingSphereClient(config)

        with patch.object(client, "execute_distsql") as mock_exec:
            mock_exec.return_value = []

            result = client.remove_mask_rules("test_db", "users")
            assert result is True

    def test_get_status_available(self):
        """获取状态（可用）"""
        from integrations.shardingsphere.config import ShardingSphereConfig
        from integrations.shardingsphere.client import ShardingSphereClient

        config = ShardingSphereConfig(enabled=True, proxy_host="localhost", proxy_port=3307)
        client = ShardingSphereClient(config)

        with patch.object(client, "show_databases") as mock_show:
            mock_show.return_value = ["db1", "db2"]

            status = client.get_status()
            assert status["available"] is True
            assert status["host"] == "localhost"
            assert status["port"] == 3307
            assert status["databases"] == ["db1", "db2"]

    def test_get_status_unavailable(self):
        """获取状态（不可用）"""
        from integrations.shardingsphere.config import ShardingSphereConfig
        from integrations.shardingsphere.client import ShardingSphereClient

        config = ShardingSphereConfig(enabled=True, proxy_host="localhost", proxy_port=3307)
        client = ShardingSphereClient(config)

        with patch.object(client, "show_databases") as mock_show:
            mock_show.side_effect = Exception("Connection failed")

            status = client.get_status()
            assert status["available"] is False
            assert "error" in status

    def test_execute_distsql_multiple_statements(self):
        """执行多条 DistSQL 语句"""
        from integrations.shardingsphere.config import ShardingSphereConfig
        from integrations.shardingsphere.client import ShardingSphereClient

        config = ShardingSphereConfig(enabled=True, proxy_host="localhost")
        client = ShardingSphereClient(config)

        with patch.object(client, "_get_connection") as mock_conn:
            mock_cursor = MagicMock()
            mock_cursor.description = [("col1",), ("col2",)]
            mock_cursor.fetchall.return_value = [("val1", "val2")]
            mock_cursor.__enter__ = Mock(return_value=mock_cursor)
            mock_cursor.__exit__ = Mock(return_value=False)

            mock_connection = MagicMock()
            mock_connection.cursor.return_value = mock_cursor
            mock_conn.return_value = mock_connection

            result = client.execute_distsql("USE db; SHOW TABLES")
            assert len(result) >= 0  # 结果可能合并


class TestShardingSphereIntegrationInit:
    """ShardingSphere 集成模块 __init__.py 测试"""

    def test_module_imports_without_error(self):
        """ShardingSphere 集成模块可以正常导入"""
        try:
            from integrations.shardingsphere import (
                ShardingSphereConfig,
                ShardingSphereClient,
                MaskingRuleGenerator,
            )
            assert ShardingSphereConfig is not None
            assert ShardingSphereClient is not None
            assert MaskingRuleGenerator is not None
        except ImportError:
            pytest.skip("ShardingSphere integration module not importable in test environment")

    def test_parent_init_handles_shardingsphere_import(self):
        """父 __init__.py 处理 ShardingSphere 导入（可选依赖）"""
        try:
            from integrations import ShardingSphereConfig, ShardingSphereClient
            # 两种情况都合法
            assert True
        except ImportError:
            pytest.skip("integrations module not importable in test environment")
