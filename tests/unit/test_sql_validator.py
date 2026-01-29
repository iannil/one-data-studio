"""
SQL 安全检查器单元测试
测试 SQL 注入防护、危险操作拦截、AST 解析验证
"""

import pytest
from services.sql_validator import (
    SQLValidator,
    SQLValidationResult,
    SQLRiskLevel,
    SQLValidatorCache,
    validate_sql,
    sanitize_sql,
)


class TestSQLValidator:
    """SQL 验证器测试"""

    @pytest.fixture
    def validator(self):
        """创建验证器实例"""
        return SQLValidator()

    def test_safe_select_query(self, validator):
        """测试安全的 SELECT 查询"""
        result = validator.validate("SELECT * FROM users LIMIT 10")
        assert result.is_valid
        assert result.risk_level == SQLRiskLevel.SAFE

    def test_select_without_limit(self, validator):
        """测试没有 LIMIT 的 SELECT（应有警告）"""
        result = validator.validate("SELECT * FROM users")
        assert result.is_valid
        assert len(result.warnings) > 0
        assert "LIMIT" in result.warnings[0]

    def test_drop_operation_blocked(self, validator):
        """测试 DROP 操作被拦截"""
        result = validator.validate("DROP TABLE users")
        assert not result.is_valid
        assert result.risk_level == SQLRiskLevel.CRITICAL
        assert any("DROP" in e for e in result.errors)

    def test_delete_operation_blocked(self, validator):
        """测试 DELETE 操作被拦截"""
        result = validator.validate("DELETE FROM users WHERE id = 1")
        assert not result.is_valid
        assert any("DELETE" in e for e in result.errors)

    def test_insert_operation_blocked(self, validator):
        """测试 INSERT 操作被拦截"""
        result = validator.validate("INSERT INTO users (name) VALUES ('test')")
        assert not result.is_valid
        assert any("INSERT" in e for e in result.errors)

    def test_update_operation_blocked(self, validator):
        """测试 UPDATE 操作被拦截"""
        result = validator.validate("UPDATE users SET name = 'test' WHERE id = 1")
        assert not result.is_valid
        assert any("UPDATE" in e for e in result.errors)

    def test_truncate_operation_blocked(self, validator):
        """测试 TRUNCATE 操作被拦截"""
        result = validator.validate("TRUNCATE TABLE users")
        assert not result.is_valid
        assert any("TRUNCATE" in e for e in result.errors)

    def test_alter_operation_blocked(self, validator):
        """测试 ALTER 操作被拦截"""
        result = validator.validate("ALTER TABLE users ADD COLUMN age INT")
        assert not result.is_valid
        assert any("ALTER" in e for e in result.errors)

    def test_create_operation_blocked(self, validator):
        """测试 CREATE 操作被拦截"""
        result = validator.validate("CREATE TABLE test (id INT)")
        assert not result.is_valid
        assert any("CREATE" in e for e in result.errors)

    def test_sql_injection_union_select(self, validator):
        """测试 UNION SELECT 注入"""
        result = validator.validate("SELECT * FROM users WHERE id = 1 UNION SELECT * FROM passwords")
        assert not result.is_valid
        assert result.risk_level == SQLRiskLevel.CRITICAL

    def test_sql_injection_tautology(self, validator):
        """测试 Tautology 注入 (1=1)"""
        result = validator.validate("SELECT * FROM users WHERE id = 1 OR 1=1")
        assert not result.is_valid
        assert result.risk_level in (SQLRiskLevel.CRITICAL, SQLRiskLevel.HIGH)

    def test_sql_injection_comment_termination(self, validator):
        """测试注释终止注入"""
        result = validator.validate("SELECT * FROM users WHERE id = 1; --")
        assert not result.is_valid

    def test_sql_injection_quote_or(self, validator):
        """测试引号 OR 注入"""
        result = validator.validate("SELECT * FROM users WHERE name = 'admin' OR '1'='1'")
        assert not result.is_valid

    def test_dangerous_function_benchmark(self, validator):
        """测试危险函数 BENCHMARK"""
        result = validator.validate("SELECT * FROM users WHERE id = 1 AND BENCHMARK(1000000, MD5(1))")
        assert not result.is_valid
        assert any("BENCHMARK" in e for e in result.errors)

    def test_dangerous_function_sleep(self, validator):
        """测试危险函数 SLEEP"""
        result = validator.validate("SELECT SLEEP(10)")
        assert not result.is_valid
        assert any("SLEEP" in e for e in result.errors)

    def test_empty_query(self, validator):
        """测试空查询"""
        result = validator.validate("")
        assert not result.is_valid
        assert result.risk_level == SQLRiskLevel.HIGH

    def test_query_too_long(self, validator):
        """测试过长查询"""
        long_query = "SELECT * FROM users WHERE " + "a=" * 10000
        result = validator.validate(long_query)
        assert not result.is_valid
        assert "过长" in result.errors[0]

    def test_join_count_limit(self, validator):
        """测试 JOIN 数量限制"""
        # 6 个 JOIN，超过默认限制 5
        query = """
        SELECT * FROM t1
        JOIN t2 ON t1.id = t2.id
        JOIN t3 ON t2.id = t3.id
        JOIN t4 ON t3.id = t4.id
        JOIN t5 ON t4.id = t5.id
        JOIN t6 ON t5.id = t6.id
        """
        result = validator.validate(query)
        assert not result.is_valid
        assert any("JOIN" in e for e in result.errors)

    def test_add_limit_if_missing(self, validator):
        """测试自动添加 LIMIT"""
        query = "SELECT * FROM users"
        result = validator.add_limit_if_missing(query, 100)
        assert "LIMIT 100" in result.upper()
        assert result.endswith(";")

    def test_add_limit_already_has_limit(self, validator):
        """测试已有 LIMIT 不重复添加"""
        query = "SELECT * FROM users LIMIT 50"
        result = validator.add_limit_if_missing(query, 100)
        assert result == query

    def test_sanitize_sql(self, validator):
        """测试 SQL 清理"""
        query = "SELECT * FROM users"
        cleaned, result = validator.sanitize_sql(query)
        assert "LIMIT" in cleaned.upper()
        assert result.is_valid

    def test_subquery_depth_limit(self, validator):
        """测试子查询深度限制"""
        # 4 层子查询，超过默认限制 3
        query = """
        SELECT * FROM (SELECT * FROM (SELECT * FROM (SELECT * FROM t1) AS t1) AS t2) AS t3
        """
        result = validator.validate(query)
        assert not result.is_valid
        assert any("子查询" in e or "subquery" in e.lower() for e in result.errors)

    def test_strict_mode_warnings_as_errors(self):
        """测试严格模式下警告视为错误"""
        validator = SQLValidator({"strict_mode": True})
        result = validator.validate("SELECT * FROM users")
        assert not result.is_valid
        assert any("严格模式" in e for e in result.errors)

    def test_custom_max_joins(self):
        """测试自定义最大 JOIN 数"""
        validator = SQLValidator({"max_joins": 2})
        query = "SELECT * FROM t1 JOIN t2 ON t1.id = t2.id JOIN t3 ON t2.id = t3.id"
        result = validator.validate(query)
        assert not result.is_valid
        assert any("JOIN" in e for e in result.errors)

    def test_custom_row_limit(self):
        """测试自定义行数限制"""
        validator = SQLValidator({"default_row_limit": 100})
        query = "SELECT * FROM users"
        cleaned = validator.add_limit_if_missing(query)
        assert "LIMIT 100" in cleaned.upper()

    def test_disable_aggregation(self):
        """测试禁用聚合函数"""
        validator = SQLValidator({"allow_aggregation": False})
        result = validator.validate("SELECT COUNT(*) FROM users")
        assert not result.is_valid
        assert any("聚合" in e or "aggregation" in e.lower() for e in result.errors)

    def test_disable_subquery(self):
        """测试禁用子查询"""
        validator = SQLValidator({"allow_subquery": False})
        result = validator.validate("SELECT * FROM (SELECT * FROM users) AS t")
        assert not result.is_valid
        assert any("子查询" in e or "subquery" in e.lower() for e in result.errors)

    def test_with_clause_allowed(self, validator):
        """测试 WITH (CTE) 语句允许"""
        result = validator.validate("WITH cte AS (SELECT * FROM users) SELECT * FROM cte")
        assert result.is_valid

    def test_comment_danger_hidden(self, validator):
        """测试注释中隐藏的危险操作"""
        query = "SELECT * FROM users /* DROP TABLE users */"
        result = validator.validate(query)
        assert not result.is_valid
        assert any("注释" in e or "comment" in e.lower() for e in result.errors)


class TestSQLValidatorCache:
    """SQL 验证器缓存测试"""

    @pytest.fixture
    def cache(self):
        """创建缓存实例"""
        return SQLValidatorCache(max_size=3)

    def test_cache_set_get(self, cache):
        """测试缓存设置和获取"""
        result = SQLValidationResult(
            is_valid=True,
            risk_level=SQLRiskLevel.SAFE,
            errors=[],
            warnings=[]
        )
        cache.set("SELECT 1", result)
        retrieved = cache.get("SELECT 1")
        assert retrieved is not None
        assert retrieved.is_valid

    def test_cache_miss(self, cache):
        """测试缓存未命中"""
        result = cache.get("NONEXISTENT")
        assert result is None

    def test_cache_lru_eviction(self, cache):
        """测试 LRU 淘汰"""
        results = [
            SQLValidationResult(True, SQLRiskLevel.SAFE, [], [], f"query{i}")
            for i in range(4)
        ]
        cache.set("query1", results[0])
        cache.set("query2", results[1])
        cache.set("query3", results[2])
        # 缓存已满
        cache.set("query4", results[3])
        # 第一个应该被淘汰
        assert cache.get("query1") is None
        assert cache.get("query2") is not None
        assert cache.get("query4") is not None

    def test_cache_clear(self, cache):
        """测试清空缓存"""
        result = SQLValidationResult(True, SQLRiskLevel.SAFE, [], [])
        cache.set("SELECT 1", result)
        cache.clear()
        assert cache.get("SELECT 1") is None


class TestConvenienceFunctions:
    """便捷函数测试"""

    def test_validate_sql_function(self):
        """测试 validate_sql 便捷函数"""
        result = validate_sql("SELECT * FROM users")
        assert result.is_valid

    def test_sanitize_sql_function(self):
        """测试 sanitize_sql 便捷函数"""
        cleaned, result = sanitize_sql("SELECT * FROM users")
        assert "LIMIT" in cleaned.upper()
        assert result.is_valid

    def test_validate_sql_with_cache(self):
        """测试带缓存的验证"""
        # 第一次调用
        result1 = validate_sql("SELECT * FROM users", use_cache=True)
        # 第二次调用应从缓存获取
        result2 = validate_sql("SELECT * FROM users", use_cache=True)
        assert result1.is_valid == result2.is_valid


class TestEdgeCases:
    """边界情况测试"""

    @pytest.fixture
    def validator(self):
        return SQLValidator()

    def test_null_bytes_in_query(self, validator):
        """测试包含空字节的查询"""
        result = validator.validate("SELECT * FROM users WHERE name = '\x00'")
        # 不应该崩溃
        assert isinstance(result, SQLValidationResult)

    def test_unicode_in_query(self, validator):
        """测试包含 Unicode 的查询"""
        result = validator.validate("SELECT * FROM users WHERE name = '测试'")
        assert result.is_valid

    def test_very_long_column_name(self, validator):
        """测试非常长的列名"""
        long_col = "a" * 1000
        result = validator.validate(f"SELECT {long_col} FROM users")
        assert isinstance(result, SQLValidationResult)

    def test_case_insensitive_keywords(self, validator):
        """测试关键字大小写不敏感"""
        variations = [
            "select * from users",
            "SELECT * FROM users",
            "SeLeCt * FrOm users",
        ]
        for query in variations:
            result = validator.validate(query)
            assert result.is_valid

    def test_multiple_semicolons(self, validator):
        """测试多个分号"""
        result = validator.validate("SELECT * FROM users;;")
        assert result.is_valid

    def test_comment_danger_multi_line(self, validator):
        """测试多行注释中隐藏的危险操作"""
        query = """
        SELECT * FROM users
        /* DROP TABLE users;
           DELETE FROM users;
        */
        """
        result = validator.validate(query)
        assert not result.is_valid


class TestNormalization:
    """SQL 规范化测试"""

    @pytest.fixture
    def validator(self):
        return SQLValidator()

    def test_normalize_sql_basic(self, validator):
        """测试基础 SQL 规范化"""
        normalized = validator._normalize_sql_basic(
            "SELECT  *  FROM   users  WHERE  id  =  1"
        )
        # 多个空格应被压缩
        assert "  " not in normalized

    def test_normalized_sql_in_result(self, validator):
        """测试结果中的规范化 SQL"""
        result = validator.validate("SELECT  *  FROM   users")
        assert result.normalized_sql is not None
        assert "  " not in result.normalized_sql


@pytest.mark.parametrize("query,expected_valid", [
    ("SELECT * FROM users LIMIT 10", True),
    ("DROP TABLE users", False),
    ("DELETE FROM users", False),
    ("SELECT * FROM users; DROP TABLE users; --", False),
    ("SELECT * FROM users WHERE 1=1", False),
    ("SELECT * FROM users WHERE name = 'test' OR '1'='1'", False),
    ("SELECT * FROM users UNION SELECT * FROM admin", False),
    ("INSERT INTO users VALUES (1, 'test')", False),
    ("UPDATE users SET name='test' WHERE id=1", False),
    ("TRUNCATE TABLE users", False),
    ("ALTER TABLE users ADD COLUMN age INT", False),
    ("CREATE TABLE test (id INT)", False),
])
def test_security_rules(query, expected_valid):
    """参数化测试安全规则"""
    validator = SQLValidator()
    result = validator.validate(query)
    assert result.is_valid == expected_valid


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=services/agent_api/services/sql_validator", "--cov-report=term-missing"])
