"""
SQL 沙箱模块单元测试
Sprint 24: P1 测试覆盖 - Text-to-SQL 安全增强
"""

import pytest
import os
import tempfile
import json
from unittest.mock import patch, MagicMock
from datetime import datetime


class TestSandboxConfig:
    """沙箱配置测试"""

    def test_default_config(self):
        """测试默认配置"""
        from services.shared.sql_sandbox import SandboxConfig

        config = SandboxConfig()
        assert config.max_memory_mb == 256
        assert config.max_execution_time_seconds == 30
        assert config.max_result_rows == 1000
        assert config.max_result_size_bytes == 10 * 1024 * 1024
        assert config.enable_audit is True

    def test_custom_config(self):
        """测试自定义配置"""
        from services.shared.sql_sandbox import SandboxConfig

        config = SandboxConfig(
            max_memory_mb=512,
            max_execution_time_seconds=60,
            max_result_rows=500,
            allowed_databases=['db1', 'db2'],
            denied_tables=['sensitive_table']
        )

        assert config.max_memory_mb == 512
        assert config.max_execution_time_seconds == 60
        assert config.max_result_rows == 500
        assert 'db1' in config.allowed_databases
        assert 'sensitive_table' in config.denied_tables

    def test_default_denied_databases(self):
        """测试默认拒绝的数据库"""
        from services.shared.sql_sandbox import SandboxConfig

        config = SandboxConfig()
        assert 'mysql' in config.denied_databases
        assert 'information_schema' in config.denied_databases
        assert 'performance_schema' in config.denied_databases
        assert 'sys' in config.denied_databases


class TestSQLSandbox:
    """SQL 沙箱测试"""

    @pytest.fixture
    def sandbox(self):
        """创建测试用沙箱实例"""
        from services.shared.sql_sandbox import SQLSandbox, SandboxConfig

        config = SandboxConfig(
            allowed_databases=['test_db', 'analytics'],
            denied_tables=['passwords', 'secrets'],
            enable_audit=False
        )
        return SQLSandbox(config)

    @pytest.fixture
    def sandbox_with_audit(self, tmp_path):
        """创建带审计的沙箱实例"""
        from services.shared.sql_sandbox import SQLSandbox, SandboxConfig

        audit_path = tmp_path / "audit.log"
        config = SandboxConfig(
            enable_audit=True,
            audit_log_path=str(audit_path)
        )
        return SQLSandbox(config)

    def test_check_database_permission_allowed(self, sandbox):
        """测试允许的数据库"""
        assert sandbox.check_database_permission('test_db') is True
        assert sandbox.check_database_permission('analytics') is True

    def test_check_database_permission_denied(self, sandbox):
        """测试拒绝的数据库"""
        assert sandbox.check_database_permission('mysql') is False
        assert sandbox.check_database_permission('information_schema') is False

    def test_check_database_permission_case_insensitive(self, sandbox):
        """测试数据库权限检查不区分大小写"""
        assert sandbox.check_database_permission('TEST_DB') is True
        assert sandbox.check_database_permission('MYSQL') is False

    def test_check_table_permission_allowed(self, sandbox):
        """测试允许的表"""
        assert sandbox.check_table_permission('users') is True
        assert sandbox.check_table_permission('orders') is True

    def test_check_table_permission_denied(self, sandbox):
        """测试拒绝的表"""
        assert sandbox.check_table_permission('passwords') is False
        assert sandbox.check_table_permission('secrets') is False

    def test_check_table_permission_case_insensitive(self, sandbox):
        """测试表权限检查不区分大小写"""
        assert sandbox.check_table_permission('PASSWORDS') is False
        assert sandbox.check_table_permission('Secrets') is False


class TestTableExtraction:
    """表名提取测试"""

    @pytest.fixture
    def sandbox(self):
        """创建测试用沙箱实例"""
        from services.shared.sql_sandbox import SQLSandbox, SandboxConfig

        config = SandboxConfig(enable_audit=False)
        return SQLSandbox(config)

    def test_extract_simple_from(self, sandbox):
        """测试简单 FROM 子句提取"""
        sql = "SELECT * FROM users"
        tables = sandbox.extract_tables_from_sql(sql)
        assert 'users' in tables

    def test_extract_multiple_tables(self, sandbox):
        """测试多表提取"""
        sql = "SELECT * FROM users JOIN orders ON users.id = orders.user_id"
        tables = sandbox.extract_tables_from_sql(sql)
        assert 'users' in tables
        assert 'orders' in tables

    def test_extract_quoted_table(self, sandbox):
        """测试引号包裹的表名"""
        sql = 'SELECT * FROM `user_data`'
        tables = sandbox.extract_tables_from_sql(sql)
        assert 'user_data' in tables

    def test_extract_schema_qualified_table(self, sandbox):
        """测试带 schema 的表名"""
        sql = "SELECT * FROM db.users"
        tables = sandbox.extract_tables_from_sql(sql)
        assert 'db.users' in tables

    def test_extract_from_subquery(self, sandbox):
        """测试子查询中的表名"""
        sql = "SELECT * FROM users WHERE id IN (SELECT user_id FROM orders)"
        tables = sandbox.extract_tables_from_sql(sql)
        assert 'users' in tables
        assert 'orders' in tables


class TestQueryValidation:
    """查询验证测试"""

    @pytest.fixture
    def sandbox(self):
        """创建测试用沙箱实例"""
        from services.shared.sql_sandbox import SQLSandbox, SandboxConfig

        config = SandboxConfig(
            allowed_databases=['test_db'],
            denied_tables=['sensitive'],
            max_result_rows=100,
            enable_audit=False
        )
        return SQLSandbox(config)

    def test_validate_query_allowed(self, sandbox):
        """测试允许的查询"""
        valid, error = sandbox.validate_query(
            "SELECT * FROM users LIMIT 50",
            "test_db"
        )
        assert valid is True
        assert error is None

    def test_validate_query_denied_database(self, sandbox):
        """测试拒绝的数据库"""
        valid, error = sandbox.validate_query(
            "SELECT * FROM users",
            "mysql"
        )
        assert valid is False
        assert "Access denied to database" in error

    def test_validate_query_denied_table(self, sandbox):
        """测试拒绝的表"""
        valid, error = sandbox.validate_query(
            "SELECT * FROM sensitive",
            "test_db"
        )
        assert valid is False
        assert "Access denied to table" in error

    def test_validate_query_limit_exceeded(self, sandbox):
        """测试超出 LIMIT 限制"""
        valid, error = sandbox.validate_query(
            "SELECT * FROM users LIMIT 1000",
            "test_db"
        )
        assert valid is False
        assert "LIMIT exceeds maximum" in error


class TestAuditLogging:
    """审计日志测试"""

    @pytest.fixture
    def sandbox_with_audit(self, tmp_path):
        """创建带审计的沙箱实例"""
        from services.shared.sql_sandbox import SQLSandbox, SandboxConfig

        audit_path = tmp_path / "audit.log"
        config = SandboxConfig(
            enable_audit=True,
            audit_log_path=str(audit_path)
        )
        return SQLSandbox(config), audit_path

    def test_audit_records_query(self, sandbox_with_audit):
        """测试审计记录查询"""
        sandbox, audit_path = sandbox_with_audit

        sandbox.audit(
            user_id="user-123",
            query_id="query-456",
            database="test_db",
            sql="SELECT * FROM users",
            status="completed",
            execution_time_ms=100,
            rows_returned=50
        )

        records = sandbox.get_audit_records(user_id="user-123")
        assert len(records) == 1
        assert records[0].user_id == "user-123"
        assert records[0].status == "completed"

    def test_audit_writes_to_file(self, sandbox_with_audit):
        """测试审计写入文件"""
        sandbox, audit_path = sandbox_with_audit

        sandbox.audit(
            user_id="user-123",
            query_id="query-456",
            database="test_db",
            sql="SELECT * FROM users",
            status="completed",
            execution_time_ms=100,
            rows_returned=50
        )

        # 检查文件是否写入
        assert audit_path.exists()

        # 读取并验证日志内容
        with open(audit_path) as f:
            log_entry = json.loads(f.readline())
            assert log_entry['user_id'] == "user-123"
            assert log_entry['status'] == "completed"

    def test_audit_disabled_no_records(self):
        """测试禁用审计不记录"""
        from services.shared.sql_sandbox import SQLSandbox, SandboxConfig

        config = SandboxConfig(enable_audit=False)
        sandbox = SQLSandbox(config)

        sandbox.audit(
            user_id="user-123",
            query_id="query-456",
            database="test_db",
            sql="SELECT * FROM users",
            status="completed"
        )

        records = sandbox.get_audit_records()
        assert len(records) == 0

    def test_audit_records_limit(self, sandbox_with_audit):
        """测试审计记录数量限制"""
        sandbox, _ = sandbox_with_audit

        # 添加大量记录测试内存限制
        for i in range(100):
            sandbox.audit(
                user_id=f"user-{i}",
                query_id=f"query-{i}",
                database="test_db",
                sql=f"SELECT {i}",
                status="completed"
            )

        # 使用 limit 参数
        records = sandbox.get_audit_records(limit=10)
        assert len(records) == 10


class TestUserStatistics:
    """用户统计测试"""

    @pytest.fixture
    def sandbox_with_records(self):
        """创建带审计记录的沙箱"""
        from services.shared.sql_sandbox import SQLSandbox, SandboxConfig

        config = SandboxConfig(enable_audit=True)
        sandbox = SQLSandbox(config)

        # 添加测试记录
        sandbox.audit("user-1", "q1", "db", "SELECT 1", "completed", 100, 10)
        sandbox.audit("user-1", "q2", "db", "SELECT 2", "completed", 200, 20)
        sandbox.audit("user-1", "q3", "db", "SELECT 3", "failed", 50, 0, error="timeout")
        sandbox.audit("user-2", "q4", "db", "SELECT 4", "completed", 150, 15)

        return sandbox

    def test_get_user_statistics(self, sandbox_with_records):
        """测试获取用户统计"""
        stats = sandbox_with_records.get_user_statistics("user-1")

        assert stats['user_id'] == "user-1"
        assert stats['total_queries'] == 3
        assert stats['successful_queries'] == 2
        assert stats['failed_queries'] == 1
        assert stats['total_rows_returned'] == 30
        assert stats['avg_execution_time_ms'] > 0

    def test_get_user_statistics_no_records(self):
        """测试无记录用户统计"""
        from services.shared.sql_sandbox import SQLSandbox, SandboxConfig

        config = SandboxConfig(enable_audit=True)
        sandbox = SQLSandbox(config)

        stats = sandbox.get_user_statistics("nonexistent-user")

        assert stats['total_queries'] == 0
        assert stats['successful_queries'] == 0
        assert stats['avg_execution_time_ms'] == 0


class TestAuditRecordFiltering:
    """审计记录过滤测试"""

    @pytest.fixture
    def sandbox_with_records(self):
        """创建带审计记录的沙箱"""
        from services.shared.sql_sandbox import SQLSandbox, SandboxConfig

        config = SandboxConfig(enable_audit=True)
        sandbox = SQLSandbox(config)

        sandbox.audit("user-1", "q1", "db1", "SELECT 1", "completed")
        sandbox.audit("user-1", "q2", "db2", "SELECT 2", "failed")
        sandbox.audit("user-2", "q3", "db1", "SELECT 3", "completed")

        return sandbox

    def test_filter_by_user(self, sandbox_with_records):
        """测试按用户过滤"""
        records = sandbox_with_records.get_audit_records(user_id="user-1")
        assert len(records) == 2
        assert all(r.user_id == "user-1" for r in records)

    def test_filter_by_database(self, sandbox_with_records):
        """测试按数据库过滤"""
        records = sandbox_with_records.get_audit_records(database="db1")
        assert len(records) == 2
        assert all(r.database == "db1" for r in records)

    def test_filter_by_status(self, sandbox_with_records):
        """测试按状态过滤"""
        records = sandbox_with_records.get_audit_records(status="completed")
        assert len(records) == 2
        assert all(r.status == "completed" for r in records)


class TestGlobalFunctions:
    """全局函数测试"""

    def test_get_sql_sandbox_singleton(self):
        """测试获取全局沙箱实例"""
        from services.shared.sql_sandbox import get_sql_sandbox

        sandbox1 = get_sql_sandbox()
        sandbox2 = get_sql_sandbox()

        assert sandbox1 is sandbox2

    def test_configure_sandbox(self):
        """测试配置全局沙箱"""
        from services.shared.sql_sandbox import configure_sandbox, get_sql_sandbox, SandboxConfig

        config = SandboxConfig(max_result_rows=500)
        configure_sandbox(config)

        sandbox = get_sql_sandbox()
        assert sandbox.config.max_result_rows == 500


class TestAuditRecord:
    """审计记录数据类测试"""

    def test_audit_record_creation(self):
        """测试审计记录创建"""
        from services.shared.sql_sandbox import AuditRecord

        record = AuditRecord(
            timestamp=datetime.now(),
            user_id="user-123",
            query_id="query-456",
            database="test_db",
            sql="SELECT * FROM users",
            status="completed",
            execution_time_ms=100,
            rows_returned=50,
            ip_address="192.168.1.1"
        )

        assert record.user_id == "user-123"
        assert record.status == "completed"
        assert record.ip_address == "192.168.1.1"
        assert record.error is None
