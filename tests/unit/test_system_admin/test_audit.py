"""
审计与追溯单元测试
测试用例：SA-AU-001 ~ SA-AU-006
"""

import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime


class TestAuditLogs:
    """审计日志测试 (SA-AU-001 ~ SA-AU-003)"""

    @pytest.mark.p0
    @pytest.mark.system_admin
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_operation_log_query(self, mock_audit_service):
        """SA-AU-001: 操作日志查询"""
        query = {
            'start_date': '2024-01-01',
            'end_date': '2024-01-31',
            'user_id': 'user_0001',
            'action': 'create'
        }

        mock_audit_service.query_logs = AsyncMock(return_value={
            'success': True,
            'logs': [
                {
                    'log_id': 'log_0001',
                    'user_id': 'user_0001',
                    'username': 'data_admin',
                    'action': 'create',
                    'resource_type': 'datasource',
                    'resource_id': 'ds_0001',
                    'ip_address': '192.168.1.100',
                    'created_at': '2024-01-15T10:30:00Z'
                },
                {
                    'log_id': 'log_0002',
                    'user_id': 'user_0001',
                    'username': 'data_admin',
                    'action': 'create',
                    'resource_type': 'etl_task',
                    'resource_id': 'etl_0001',
                    'ip_address': '192.168.1.100',
                    'created_at': '2024-01-15T14:20:00Z'
                }
            ],
            'total_count': 2
        })

        result = await mock_audit_service.query_logs(query)

        assert result['success'] is True
        assert len(result['logs']) > 0

    @pytest.mark.p1
    @pytest.mark.system_admin
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_login_log_query(self, mock_audit_service):
        """SA-AU-002: 登录日志查询"""
        query = {
            'start_date': '2024-01-01',
            'end_date': '2024-01-31',
            'user_id': 'user_0001'
        }

        mock_audit_service.query_login_logs = AsyncMock(return_value={
            'success': True,
            'logs': [
                {
                    'log_id': 'login_0001',
                    'user_id': 'user_0001',
                    'username': 'data_admin',
                    'login_time': '2024-01-15T09:00:00Z',
                    'ip_address': '192.168.1.100',
                    'user_agent': 'Mozilla/5.0...',
                    'status': 'success'
                },
                {
                    'log_id': 'login_0002',
                    'user_id': 'user_0001',
                    'username': 'data_admin',
                    'login_time': '2024-01-15T14:00:00Z',
                    'ip_address': '192.168.1.100',
                    'user_agent': 'Mozilla/5.0...',
                    'status': 'success'
                }
            ],
            'total_count': 2
        })

        result = await mock_audit_service.query_login_logs(query)

        assert result['success'] is True

    @pytest.mark.p0
    @pytest.mark.system_admin
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_data_change_tracing(self, mock_audit_service):
        """SA-AU-003: 数据变更追溯"""
        resource_id = 'table:users'

        mock_audit_service.get_change_trail = AsyncMock(return_value={
            'success': True,
            'resource_id': resource_id,
            'trail': [
                {
                    'log_id': 'log_0001',
                    'action': 'create',
                    'user_id': 'user_0001',
                    'username': 'data_admin',
                    'timestamp': '2024-01-01T10:00:00Z',
                    'details': {
                        'columns': ['id', 'username', 'phone', 'email']
                    }
                },
                {
                    'log_id': 'log_0002',
                    'action': 'update',
                    'user_id': 'user_0002',
                    'username': 'data_engineer',
                    'timestamp': '2024-01-10T14:30:00Z',
                    'details': {
                        'added_columns': ['address'],
                        'old_values': {'description': ''},
                        'new_values': {'description': '用户信息表'}
                    }
                },
                {
                    'log_id': 'log_0003',
                    'action': 'update',
                    'user_id': 'user_0002',
                    'username': 'data_admin',
                    'timestamp': '2024-01-15T11:00:00Z',
                    'details': {
                        'change_type': 'sensitivity_tagged',
                        'added_tags': ['PII']
                    }
                }
            ]
        })

        result = await mock_audit_service.get_change_trail(resource_id)

        assert result['success'] is True
        assert len(result['trail']) >= 2


class TestSensitiveDataAudit:
    """敏感数据审计测试 (SA-AU-004)"""

    @pytest.mark.p0
    @pytest.mark.system_admin
    @pytest.mark.security
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_sensitive_data_access_audit(self, mock_audit_service):
        """SA-AU-004: 敏感数据访问审计"""
        query = {
            'start_date': '2024-01-01',
            'end_date': '2024-01-31',
            'sensitive_only': True
        }

        mock_audit_service.query_sensitive_access = AsyncMock(return_value={
            'success': True,
            'access_records': [
                {
                    'log_id': 'access_0001',
                    'user_id': 'user_0001',
                    'username': 'data_admin',
                    'resource_type': 'column',
                    'resource_id': 'users.phone',
                    'action': 'read',
                    'access_time': '2024-01-15T10:30:00Z',
                    'rows_affected': 100
                },
                {
                    'log_id': 'access_0002',
                    'user_id': 'user_0003',
                    'username': 'business_user',
                    'resource_type': 'column',
                    'resource_id': 'users.email',
                    'action': 'read',
                    'access_time': '2024-01-15T11:00:00Z',
                    'rows_affected': 50,
                    'was_masked': True
                }
            ],
            'total_count': 2
        })

        result = await mock_audit_service.query_sensitive_access(query)

        assert result['success'] is True
        assert len(result['access_records']) > 0


class TestAuditExport:
    """审计导出测试 (SA-AU-005 ~ SA-AU-006)"""

    @pytest.mark.p2
    @pytest.mark.system_admin
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_audit_log_export(self, mock_audit_service):
        """SA-AU-005: 审计日志导出"""
        query = {
            'start_date': '2024-01-01',
            'end_date': '2024-01-31'
        }

        mock_audit_service.export_logs = AsyncMock(return_value={
            'success': True,
            'export_url': 'https://storage.example.com/exports/audit_logs_202401.csv',
            'format': 'csv',
            'record_count': 1500
        })

        result = await mock_audit_service.export_logs(query, format='csv')

        assert result['success'] is True
        assert 'export_url' in result

    @pytest.mark.p2
    @pytest.mark.system_admin
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_audit_log_archive(self, mock_audit_service):
        """SA-AU-006: 审计日志归档"""
        mock_audit_service.archive_logs = AsyncMock(return_value={
            'success': True,
            'archived_before': '2024-01-01',
            'archived_count': 5000,
            'archive_location': 's3://audit-logs/archive/2024/01/'
        })

        result = await mock_audit_service.archive_logs(before_date='2024-01-01')

        assert result['success'] is True
        assert result['archived_count'] > 0


# ==================== Fixtures ====================

@pytest.fixture
def mock_audit_service():
    """Mock 审计服务"""
    service = Mock()
    service.query_logs = AsyncMock()
    service.query_login_logs = AsyncMock()
    service.get_change_trail = AsyncMock()
    service.query_sensitive_access = AsyncMock()
    service.export_logs = AsyncMock()
    service.archive_logs = AsyncMock()
    return service
