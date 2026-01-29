"""
审计日志服务模块单元测试
Sprint 9 & 29: P2 测试覆盖 - 安全加固与审计持久化
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime


# 全局 fixture 阻止 AuditLogger 创建文件处理器
@pytest.fixture(autouse=True)
def mock_audit_logger_setup():
    """阻止 AuditLogger 创建日志文件"""
    with patch("services.shared.audit.AuditLogger._setup_audit_logger"):
        yield


class TestAuditAction:
    """审计动作类型测试"""

    def test_authentication_actions(self):
        """测试认证相关动作"""
        from services.shared.audit import AuditAction

        assert AuditAction.LOGIN.value == "login"
        assert AuditAction.LOGOUT.value == "logout"
        assert AuditAction.LOGIN_FAILED.value == "login_failed"
        assert AuditAction.PASSWORD_CHANGE.value == "password_change"

    def test_data_actions(self):
        """测试数据相关动作"""
        from services.shared.audit import AuditAction

        assert AuditAction.DATA_READ.value == "data_read"
        assert AuditAction.DATA_CREATE.value == "data_create"
        assert AuditAction.DATA_UPDATE.value == "data_update"
        assert AuditAction.DATA_DELETE.value == "data_delete"

    def test_workflow_actions(self):
        """测试工作流相关动作"""
        from services.shared.audit import AuditAction

        assert AuditAction.WORKFLOW_CREATE.value == "workflow_create"
        assert AuditAction.WORKFLOW_EXECUTE.value == "workflow_execute"
        assert AuditAction.WORKFLOW_DELETE.value == "workflow_delete"


class TestAuditSeverity:
    """审计严重级别测试"""

    def test_severity_levels(self):
        """测试严重级别"""
        from services.shared.audit import AuditSeverity

        assert AuditSeverity.INFO.value == "info"
        assert AuditSeverity.WARNING.value == "warning"
        assert AuditSeverity.ERROR.value == "error"
        assert AuditSeverity.CRITICAL.value == "critical"


class TestAuditEvent:
    """审计事件测试"""

    def test_event_creation(self):
        """测试事件创建"""
        from services.shared.audit import AuditEvent, AuditAction, AuditSeverity

        event = AuditEvent(
            action=AuditAction.LOGIN,
            user_id="user-123",
            username="testuser",
            ip_address="192.168.1.1"
        )

        assert event.action == AuditAction.LOGIN
        assert event.user_id == "user-123"
        assert event.severity == AuditSeverity.INFO
        assert event.status == "success"
        assert event.timestamp is not None

    def test_event_to_dict(self):
        """测试事件转字典"""
        from services.shared.audit import AuditEvent, AuditAction

        event = AuditEvent(
            action=AuditAction.LOGIN,
            user_id="user-123"
        )

        data = event.to_dict()

        assert data['action'] == 'login'
        assert data['user_id'] == 'user-123'
        assert 'timestamp' in data

    def test_event_to_json(self):
        """测试事件转 JSON"""
        from services.shared.audit import AuditEvent, AuditAction
        import json

        event = AuditEvent(
            action=AuditAction.LOGIN,
            user_id="user-123"
        )

        json_str = event.to_json()
        parsed = json.loads(json_str)

        assert parsed['action'] == 'login'


class TestAuditLogger:
    """审计日志记录器测试"""

    def test_sensitive_actions_defined(self):
        """测试敏感操作已定义"""
        from services.shared.audit import AuditLogger, AuditAction

        assert AuditAction.LOGIN in AuditLogger.SENSITIVE_ACTIONS
        assert AuditAction.PASSWORD_CHANGE in AuditLogger.SENSITIVE_ACTIONS
        assert AuditAction.PERMISSION_CHANGE in AuditLogger.SENSITIVE_ACTIONS

    def test_log_login(self):
        """测试记录登录"""
        from services.shared.audit import AuditLogger

        logger = AuditLogger()

        with patch.object(logger, 'log') as mock_log:
            logger.log_login(
                user_id="user-123",
                username="testuser",
                ip_address="192.168.1.1",
                user_agent="Mozilla/5.0",
                success=True
            )

            mock_log.assert_called_once()
            event = mock_log.call_args[0][0]
            assert event.user_id == "user-123"

    def test_log_logout(self):
        """测试记录登出"""
        from services.shared.audit import AuditLogger

        logger = AuditLogger()

        with patch.object(logger, 'log') as mock_log:
            logger.log_logout(
                user_id="user-123",
                username="testuser",
                ip_address="192.168.1.1"
            )

            mock_log.assert_called_once()

    def test_log_workflow_execute(self):
        """测试记录工作流执行"""
        from services.shared.audit import AuditLogger

        logger = AuditLogger()

        with patch.object(logger, 'log') as mock_log:
            logger.log_workflow_execute(
                user_id="user-123",
                workflow_id="wf-456",
                workflow_name="Test Workflow",
                success=True
            )

            mock_log.assert_called_once()
            event = mock_log.call_args[0][0]
            assert event.resource_id == "wf-456"

    def test_log_config_change(self):
        """测试记录配置变更"""
        from services.shared.audit import AuditLogger

        logger = AuditLogger()

        with patch.object(logger, 'log') as mock_log:
            logger.log_config_change(
                user_id="admin",
                config_key="max_users",
                old_value=100,
                new_value=200
            )

            mock_log.assert_called_once()
            event = mock_log.call_args[0][0]
            assert event.metadata['old_value'] == '100'
            assert event.metadata['new_value'] == '200'

    def test_log_api_call(self):
        """测试记录 API 调用"""
        from services.shared.audit import AuditLogger, AuditAction

        logger = AuditLogger()

        with patch.object(logger, 'log') as mock_log:
            logger.log_api_call(
                endpoint="/api/v1/users",
                method="GET",
                user_id="user-123",
                status_code=200,
                response_time_ms=50
            )

            mock_log.assert_called_once()
            event = mock_log.call_args[0][0]
            # /api/v1/users 是敏感端点
            assert event.action == AuditAction.API_CALL_SENSITIVE


class TestGetAuditLogger:
    """获取审计日志器测试"""

    def test_get_audit_logger_singleton(self):
        """测试审计日志器单例"""
        from services.shared.audit import get_audit_logger

        logger1 = get_audit_logger()
        logger2 = get_audit_logger()

        assert logger1 is logger2


class TestConvenienceFunctions:
    """便捷函数测试"""

    def test_log_login_function(self):
        """测试 log_login 便捷函数"""
        from services.shared.audit import log_login, get_audit_logger

        with patch.object(get_audit_logger(), 'log_login') as mock:
            log_login("user-1", "testuser", "192.168.1.1", "Mozilla", True)
            mock.assert_called_once()

    def test_log_logout_function(self):
        """测试 log_logout 便捷函数"""
        from services.shared.audit import log_logout, get_audit_logger

        with patch.object(get_audit_logger(), 'log_logout') as mock:
            log_logout("user-1", "testuser", "192.168.1.1")
            mock.assert_called_once()

    def test_log_workflow_execute_function(self):
        """测试 log_workflow_execute 便捷函数"""
        from services.shared.audit import log_workflow_execute, get_audit_logger

        with patch.object(get_audit_logger(), 'log_workflow_execute') as mock:
            log_workflow_execute("user-1", "wf-1", "Test WF", True)
            mock.assert_called_once()


class TestAuditLogDecorator:
    """审计日志装饰器测试"""

    def test_audit_log_decorator(self):
        """测试审计日志装饰器"""
        from services.shared.audit import audit_log, AuditAction, get_audit_logger

        @audit_log(AuditAction.DATA_DELETE)
        def delete_item(item_id):
            return f"Deleted {item_id}"

        with patch.object(get_audit_logger(), 'log') as mock_log:
            result = delete_item("item-123")

            assert result == "Deleted item-123"
            mock_log.assert_called_once()
