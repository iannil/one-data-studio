"""
审计日志数据模型单元测试
Sprint 29: P1 测试覆盖 - 企业安全强化
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock


class TestAuditLogModel:
    """审计日志模型测试"""

    def test_audit_log_default_values(self):
        """测试审计日志默认值"""
        from services.shared.models.audit import AuditLog

        # 使用显式默认值创建（SQLAlchemy 默认值只在 DB 插入时生效）
        log = AuditLog(action='login', severity='info', status='success')

        assert log.action == 'login'
        assert log.severity == 'info'
        assert log.status == 'success'

    def test_audit_log_full_creation(self):
        """测试完整审计日志创建"""
        from services.shared.models.audit import AuditLog

        log = AuditLog(
            id='log-123',
            action='user_create',
            severity='info',
            status='success',
            user_id='user-456',
            username='testuser',
            tenant_id='tenant-789',
            ip_address='192.168.1.1',
            user_agent='Mozilla/5.0',
            request_id='req-001',
            resource_type='user',
            resource_id='user-new',
            extra_metadata={'extra': 'data'}
        )

        assert log.id == 'log-123'
        assert log.action == 'user_create'
        assert log.user_id == 'user-456'
        assert log.tenant_id == 'tenant-789'
        assert log.extra_metadata == {'extra': 'data'}

    def test_audit_log_with_error(self):
        """测试带错误的审计日志"""
        from services.shared.models.audit import AuditLog

        log = AuditLog(
            action='login',
            status='failure',
            error_code='AUTH_001',
            error_message='Invalid credentials'
        )

        assert log.status == 'failure'
        assert log.error_code == 'AUTH_001'
        assert log.error_message == 'Invalid credentials'

    def test_audit_log_to_dict(self):
        """测试审计日志转字典"""
        from services.shared.models.audit import AuditLog

        log = AuditLog(
            id='log-123',
            action='data_access',
            severity='info',
            status='success',
            user_id='user-456',
            username='testuser',
            tenant_id='tenant-789',
            ip_address='192.168.1.1',
            resource_type='dataset',
            resource_id='ds-001',
            extra_metadata={'query': 'SELECT *'}
        )
        log.timestamp = datetime(2024, 1, 1, 12, 0, 0)
        log.created_at = datetime(2024, 1, 1, 12, 0, 0)

        data = log.to_dict()

        assert data['id'] == 'log-123'
        assert data['action'] == 'data_access'
        assert data['user_id'] == 'user-456'
        assert data['tenant_id'] == 'tenant-789'
        assert data['timestamp'] == '2024-01-01T12:00:00'
        assert data['extra_metadata'] == {'query': 'SELECT *'}

    def test_audit_log_to_dict_with_none_timestamps(self):
        """测试审计日志转字典处理 None 时间戳"""
        from services.shared.models.audit import AuditLog

        log = AuditLog(
            id='log-123',
            action='test'
        )
        log.timestamp = None
        log.created_at = None

        data = log.to_dict()

        assert data['timestamp'] is None
        assert data['created_at'] is None

    def test_audit_log_repr(self):
        """测试审计日志字符串表示"""
        from services.shared.models.audit import AuditLog

        log = AuditLog(
            id='log-123',
            action='login',
            user_id='user-456'
        )

        repr_str = repr(log)

        assert 'log-123' in repr_str
        assert 'login' in repr_str
        assert 'user-456' in repr_str


class TestAuditLogFromEvent:
    """从事件创建审计日志测试"""

    def test_from_event_basic(self):
        """测试从基本事件创建"""
        from services.shared.models.audit import AuditLog

        # 模拟 AuditEvent
        mock_event = MagicMock()
        mock_event.action = 'login'
        mock_event.severity = 'info'
        mock_event.status = 'success'
        mock_event.user_id = 'user-123'
        mock_event.username = 'testuser'
        mock_event.ip_address = '192.168.1.1'
        mock_event.user_agent = 'Mozilla/5.0'
        mock_event.resource_type = None
        mock_event.resource_id = None
        mock_event.error_code = None
        mock_event.error_message = None
        mock_event.metadata = {}
        mock_event.timestamp = datetime.utcnow()

        log = AuditLog.from_event(mock_event)

        assert log.action == 'login'
        assert log.user_id == 'user-123'

    def test_from_event_with_enum_values(self):
        """测试从带枚举值的事件创建"""
        from services.shared.models.audit import AuditLog
        from enum import Enum

        class MockAction(Enum):
            LOGIN = 'login'

        class MockSeverity(Enum):
            INFO = 'info'

        mock_event = MagicMock()
        mock_event.action = MockAction.LOGIN
        mock_event.severity = MockSeverity.INFO
        mock_event.status = 'success'
        mock_event.user_id = 'user-123'
        mock_event.username = None
        mock_event.ip_address = None
        mock_event.user_agent = None
        mock_event.resource_type = None
        mock_event.resource_id = None
        mock_event.error_code = None
        mock_event.error_message = None
        mock_event.metadata = None
        mock_event.timestamp = datetime.utcnow()

        log = AuditLog.from_event(mock_event)

        assert log.action == 'login'
        assert log.severity == 'info'


class TestAuditRetentionPolicy:
    """审计保留策略测试"""

    def test_default_retention_days(self):
        """测试默认保留天数"""
        from services.shared.models.audit import AuditRetentionPolicy

        assert AuditRetentionPolicy.DEFAULT_RETENTION_DAYS == 90

    def test_sensitive_retention_days(self):
        """测试敏感操作保留天数"""
        from services.shared.models.audit import AuditRetentionPolicy

        assert AuditRetentionPolicy.SENSITIVE_RETENTION_DAYS == 365

    def test_sensitive_actions_defined(self):
        """测试敏感操作已定义"""
        from services.shared.models.audit import AuditRetentionPolicy

        assert 'login' in AuditRetentionPolicy.SENSITIVE_ACTIONS
        assert 'logout' in AuditRetentionPolicy.SENSITIVE_ACTIONS
        assert 'login_failed' in AuditRetentionPolicy.SENSITIVE_ACTIONS
        assert 'password_change' in AuditRetentionPolicy.SENSITIVE_ACTIONS
        assert 'permission_change' in AuditRetentionPolicy.SENSITIVE_ACTIONS

    def test_get_retention_days_normal_action(self):
        """测试普通操作保留天数"""
        from services.shared.models.audit import AuditRetentionPolicy

        days = AuditRetentionPolicy.get_retention_days('data_read')

        assert days == AuditRetentionPolicy.DEFAULT_RETENTION_DAYS

    def test_get_retention_days_sensitive_action(self):
        """测试敏感操作保留天数"""
        from services.shared.models.audit import AuditRetentionPolicy

        days = AuditRetentionPolicy.get_retention_days('login')

        assert days == AuditRetentionPolicy.SENSITIVE_RETENTION_DAYS

    def test_get_retention_days_password_change(self):
        """测试密码更改保留天数"""
        from services.shared.models.audit import AuditRetentionPolicy

        days = AuditRetentionPolicy.get_retention_days('password_change')

        assert days == 365

    def test_get_retention_days_data_delete(self):
        """测试数据删除保留天数"""
        from services.shared.models.audit import AuditRetentionPolicy

        days = AuditRetentionPolicy.get_retention_days('data_delete')

        assert days == 365


class TestAuditLogTableStructure:
    """审计日志表结构测试"""

    def test_table_name(self):
        """测试表名"""
        from services.shared.models.audit import AuditLog

        assert AuditLog.__tablename__ == 'audit_logs'

    def test_table_args(self):
        """测试表参数"""
        from services.shared.models.audit import AuditLog

        table_args = AuditLog.__table_args__

        assert isinstance(table_args, tuple)
        # 最后一个元素应该是字典
        config = table_args[-1]
        assert config.get('mysql_engine') == 'InnoDB'
        assert config.get('mysql_charset') == 'utf8mb4'

    def test_indexes_exist(self):
        """测试索引存在"""
        from services.shared.models.audit import AuditLog

        # 检查表参数中的索引
        table_args = AuditLog.__table_args__

        # 过滤出 Index 对象
        from sqlalchemy import Index
        indexes = [arg for arg in table_args if isinstance(arg, Index)]

        # 应该有多个索引
        assert len(indexes) >= 3

        # 检查索引名称
        index_names = {idx.name for idx in indexes}
        assert 'ix_audit_logs_user_action' in index_names
        assert 'ix_audit_logs_tenant_timestamp' in index_names
        assert 'ix_audit_logs_resource' in index_names


class TestAuditLogFields:
    """审计日志字段测试"""

    def test_action_field_indexed(self):
        """测试 action 字段有索引"""
        from services.shared.models.audit import AuditLog

        action_col = AuditLog.__table__.c.action
        assert action_col.index is True

    def test_user_id_field_indexed(self):
        """测试 user_id 字段有索引"""
        from services.shared.models.audit import AuditLog

        user_id_col = AuditLog.__table__.c.user_id
        assert user_id_col.index is True

    def test_tenant_id_field_indexed(self):
        """测试 tenant_id 字段有索引"""
        from services.shared.models.audit import AuditLog

        tenant_id_col = AuditLog.__table__.c.tenant_id
        assert tenant_id_col.index is True

    def test_timestamp_field_indexed(self):
        """测试 timestamp 字段有索引"""
        from services.shared.models.audit import AuditLog

        timestamp_col = AuditLog.__table__.c.timestamp
        assert timestamp_col.index is True

    def test_metadata_is_json(self):
        """测试 metadata 字段是 JSON 类型"""
        from services.shared.models.audit import AuditLog
        from sqlalchemy import JSON

        # 实际字段名是 extra_metadata
        metadata_col = AuditLog.__table__.c.extra_metadata
        assert isinstance(metadata_col.type, JSON)


class TestAuditLogSeverityLevels:
    """审计日志严重级别测试"""

    def test_default_severity_is_info(self):
        """测试默认严重级别是 info（通过 Column 定义）"""
        from services.shared.models.audit import AuditLog

        # 检查 Column 的默认值定义
        severity_col = AuditLog.__table__.c.severity
        assert severity_col.default.arg == 'info'

    def test_custom_severity_levels(self):
        """测试自定义严重级别"""
        from services.shared.models.audit import AuditLog

        for severity in ['debug', 'info', 'warning', 'error', 'critical']:
            log = AuditLog(action='test', severity=severity)
            assert log.severity == severity


class TestAuditLogStatusValues:
    """审计日志状态值测试"""

    def test_default_status_is_success(self):
        """测试默认状态是 success（通过 Column 定义）"""
        from services.shared.models.audit import AuditLog

        # 检查 Column 的默认值定义
        status_col = AuditLog.__table__.c.status
        assert status_col.default.arg == 'success'

    def test_custom_status_values(self):
        """测试自定义状态值"""
        from services.shared.models.audit import AuditLog

        for status in ['success', 'failure', 'pending', 'skipped']:
            log = AuditLog(action='test', status=status)
            assert log.status == status
