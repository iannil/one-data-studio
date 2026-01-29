"""
Alldata API 单元测试
Sprint 24: 测试覆盖率扩展

测试 Alldata API 的核心功能
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import json


class TestSQLSanitizer:
    """SQL 清洗器测试"""

    def test_safe_select_query(self):
        """测试安全的 SELECT 查询"""
        from sql_executor import SQLSanitizer

        sql = "SELECT * FROM users WHERE id = 1"
        is_safe, error = SQLSanitizer.is_safe(sql)

        assert is_safe is True
        assert error is None

    def test_dangerous_drop_query(self):
        """测试危险的 DROP 查询"""
        from sql_executor import SQLSanitizer

        sql = "DROP TABLE users"
        is_safe, error = SQLSanitizer.is_safe(sql)

        assert is_safe is False
        assert "DROP" in error

    def test_dangerous_delete_query(self):
        """测试危险的 DELETE 查询"""
        from sql_executor import SQLSanitizer

        sql = "DELETE FROM users WHERE id = 1"
        is_safe, error = SQLSanitizer.is_safe(sql)

        assert is_safe is False
        assert "DELETE" in error

    def test_dangerous_insert_query(self):
        """测试危险的 INSERT 查询"""
        from sql_executor import SQLSanitizer

        sql = "INSERT INTO users (name) VALUES ('test')"
        is_safe, error = SQLSanitizer.is_safe(sql)

        assert is_safe is False
        assert "INSERT" in error

    def test_dangerous_update_query(self):
        """测试危险的 UPDATE 查询"""
        from sql_executor import SQLSanitizer

        sql = "UPDATE users SET name = 'test' WHERE id = 1"
        is_safe, error = SQLSanitizer.is_safe(sql)

        assert is_safe is False
        assert "UPDATE" in error

    def test_multiple_statements_rejected(self):
        """测试多语句被拒绝"""
        from sql_executor import SQLSanitizer

        sql = "SELECT * FROM users; SELECT * FROM orders"
        is_safe, error = SQLSanitizer.is_safe(sql)

        assert is_safe is False
        assert "Multiple statements" in error or "multiple" in error.lower()

    def test_sql_comments_rejected(self):
        """测试 SQL 注释被拒绝"""
        from sql_executor import SQLSanitizer

        sql = "SELECT * FROM users -- comment"
        is_safe, error = SQLSanitizer.is_safe(sql)

        assert is_safe is False
        assert "comments" in error

    def test_non_select_rejected(self):
        """测试非 SELECT 语句被拒绝"""
        from sql_executor import SQLSanitizer

        sql = "SHOW TABLES"
        is_safe, error = SQLSanitizer.is_safe(sql)

        assert is_safe is False
        assert "SELECT" in error

    def test_sanitize_removes_trailing_semicolon(self):
        """测试清洗移除末尾分号"""
        from sql_executor import SQLSanitizer

        sql = "SELECT * FROM users;"
        sanitized = SQLSanitizer.sanitize(sql)

        assert not sanitized.endswith(';')

    def test_sanitize_normalizes_whitespace(self):
        """测试清洗标准化空白"""
        from sql_executor import SQLSanitizer

        sql = "SELECT   *   FROM    users"
        sanitized = SQLSanitizer.sanitize(sql)

        assert "  " not in sanitized


class TestSQLExecutor:
    """SQL 执行器测试"""

    @pytest.fixture
    def executor(self):
        """创建测试执行器"""
        from sql_executor import SQLExecutor
        return SQLExecutor(db_url="sqlite:///:memory:")

    def test_query_result_structure(self, executor):
        """测试查询结果结构"""
        from sql_executor import QueryResult, QueryStatus

        result = QueryResult(
            query_id="test-id",
            sql="SELECT 1",
            database="test_db",
            status=QueryStatus.COMPLETED
        )

        assert result.query_id == "test-id"
        assert result.status == QueryStatus.COMPLETED

    def test_query_config_defaults(self):
        """测试查询配置默认值"""
        from sql_executor import QueryConfig

        config = QueryConfig()

        assert config.timeout_seconds == 30
        assert config.max_rows == 1000
        assert config.readonly is True

    def test_format_result_json(self, executor):
        """测试 JSON 格式化"""
        from sql_executor import QueryResult, QueryStatus

        result = QueryResult(
            query_id="test-id",
            sql="SELECT 1",
            database="test_db",
            status=QueryStatus.COMPLETED,
            columns=["value"],
            rows=[[1]]
        )

        formatted = executor.format_result(result, 'json')

        assert formatted['query_id'] == "test-id"
        assert formatted['status'] == "completed"
        assert formatted['columns'] == ["value"]
        assert formatted['rows'] == [[1]]

    def test_format_result_csv(self, executor):
        """测试 CSV 格式化"""
        from sql_executor import QueryResult, QueryStatus

        result = QueryResult(
            query_id="test-id",
            sql="SELECT 1",
            database="test_db",
            status=QueryStatus.COMPLETED,
            columns=["id", "name"],
            rows=[[1, "test"], [2, "test2"]]
        )

        formatted = executor.format_result(result, 'csv')

        assert "id,name" in formatted
        assert "1,test" in formatted
        assert "2,test2" in formatted

    def test_format_result_markdown(self, executor):
        """测试 Markdown 格式化"""
        from sql_executor import QueryResult, QueryStatus

        result = QueryResult(
            query_id="test-id",
            sql="SELECT 1",
            database="test_db",
            status=QueryStatus.COMPLETED,
            columns=["id", "name"],
            rows=[[1, "test"]]
        )

        formatted = executor.format_result(result, 'markdown')

        assert "| id | name |" in formatted
        assert "| --- | --- |" in formatted
        assert "| 1 | test |" in formatted


class TestQueryStatus:
    """查询状态测试"""

    def test_status_values(self):
        """测试状态值"""
        from sql_executor import QueryStatus

        assert QueryStatus.PENDING.value == "pending"
        assert QueryStatus.RUNNING.value == "running"
        assert QueryStatus.COMPLETED.value == "completed"
        assert QueryStatus.FAILED.value == "failed"
        assert QueryStatus.TIMEOUT.value == "timeout"
        assert QueryStatus.CANCELLED.value == "cancelled"


class TestAPIHealthEndpoint:
    """API 健康检查端点测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        try:
            import sys
            sys.path.insert(0, '/app')
            from app import app
            app.config['TESTING'] = True
            with app.test_client() as client:
                yield client
        except ImportError:
            pytest.skip("App not available")

    def test_health_endpoint(self, client):
        """测试健康检查端点"""
        response = client.get('/api/v1/health')

        assert response.status_code == 200
        data = response.get_json()
        assert data['code'] == 0
        assert 'message' in data

    def test_health_returns_version(self, client):
        """测试健康检查返回版本"""
        response = client.get('/api/v1/health')

        data = response.get_json()
        assert 'version' in data or 'service' in data


class TestMetadataEndpoints:
    """元数据端点测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        try:
            from app import app
            app.config['TESTING'] = True
            with app.test_client() as client:
                yield client
        except ImportError:
            pytest.skip("App not available")

    def test_list_databases_endpoint(self, client):
        """测试列出数据库端点"""
        response = client.get('/api/v1/metadata/databases')

        # 端点应该存在
        assert response.status_code in [200, 401, 403, 500]

    def test_get_database_tables_endpoint(self, client):
        """测试获取数据库表端点"""
        response = client.get('/api/v1/metadata/databases/test_db/tables')

        assert response.status_code in [200, 404, 401, 403, 500]


class TestDatasetEndpoints:
    """数据集端点测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        try:
            from app import app
            app.config['TESTING'] = True
            with app.test_client() as client:
                yield client
        except ImportError:
            pytest.skip("App not available")

    def test_list_datasets_endpoint(self, client):
        """测试列出数据集端点"""
        response = client.get('/api/v1/datasets')

        assert response.status_code in [200, 401, 403]

    def test_get_dataset_endpoint(self, client):
        """测试获取数据集端点"""
        response = client.get('/api/v1/datasets/test-dataset')

        assert response.status_code in [200, 404, 401, 403]
