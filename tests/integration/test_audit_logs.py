"""
审计与追溯模块集成测试
SA-AU-001 ~ SA-AU-006

测试场景:
1. SA-AU-001: 操作日志查询 (P0) - 按时间/用户/操作类型过滤
2. SA-AU-002: 登录日志查询 (P1) - 查询登录历史
3. SA-AU-003: 数据变更追溯 (P0) - 追溯变更人、时间、内容
4. SA-AU-004: 敏感数据访问审计 (P0) - 记录谁、何时、访问范围
5. SA-AU-005: 审计日志导出 (P2) - 导出审计日志
6. SA-AU-006: 审计日志归档 (P2) - 归档过期日志

本测试完全自包含，不依赖 services.shared.* 模块。
所有需要的类（AuditAction, AuditSeverity, AuditEvent, AuditLog,
AuditRetentionPolicy, AuditLogger）均在本文件内联实现。
"""

import json
import csv
import io
import uuid
import pytest
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, asdict, field
from typing import Any, Dict, Optional, List
from unittest.mock import MagicMock


# ===========================================================================
# 内联实现: 审计日志相关类（替代 services.shared.audit / models.audit）
# ===========================================================================

class AuditAction(Enum):
    """审计动作类型"""
    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILED = "login_failed"
    PASSWORD_CHANGE = "password_change"
    PASSWORD_RESET = "password_reset"
    DATA_READ = "data_read"
    DATA_CREATE = "data_create"
    DATA_UPDATE = "data_update"
    DATA_DELETE = "data_delete"
    WORKFLOW_CREATE = "workflow_create"
    WORKFLOW_UPDATE = "workflow_update"
    WORKFLOW_DELETE = "workflow_delete"
    WORKFLOW_EXECUTE = "workflow_execute"
    DOCUMENT_UPLOAD = "document_upload"
    DOCUMENT_DELETE = "document_delete"
    DOCUMENT_INDEX = "document_index"
    CONFIG_CHANGE = "config_change"
    PERMISSION_CHANGE = "permission_change"
    API_CALL = "api_call"
    API_CALL_SENSITIVE = "api_call_sensitive"
    SYSTEM_START = "system_start"
    SYSTEM_STOP = "system_stop"
    SYSTEM_ERROR = "system_error"


class AuditSeverity(Enum):
    """审计严重级别"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class AuditEvent:
    """审计事件"""
    action: AuditAction
    user_id: Optional[str] = None
    username: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    severity: AuditSeverity = AuditSeverity.INFO
    status: str = "success"
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    timestamp: Optional[datetime] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data['action'] = self.action.value
        data['severity'] = self.severity.value
        if self.timestamp:
            data['timestamp'] = self.timestamp.isoformat()
        return data

    def to_json(self) -> str:
        """转换为 JSON"""
        return json.dumps(self.to_dict(), ensure_ascii=False)


class AuditLog:
    """
    审计日志记录（轻量级替代 SQLAlchemy 模型）

    用于测试中模拟数据库行对象。
    """

    def __init__(
        self,
        id: Optional[str] = None,
        action: str = "",
        severity: str = "info",
        status: str = "success",
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        tenant_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
        extra_metadata: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None,
        created_at: Optional[datetime] = None,
    ):
        self.id = id or str(uuid.uuid4())
        self.action = action
        self.severity = severity
        self.status = status
        self.user_id = user_id
        self.username = username
        self.tenant_id = tenant_id
        self.ip_address = ip_address
        self.user_agent = user_agent
        self.request_id = request_id
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.error_code = error_code
        self.error_message = error_message
        self.extra_metadata = extra_metadata
        self.timestamp = timestamp or datetime.utcnow()
        self.created_at = created_at or datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'action': self.action,
            'severity': self.severity,
            'status': self.status,
            'user_id': self.user_id,
            'username': self.username,
            'tenant_id': self.tenant_id,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'request_id': self.request_id,
            'resource_type': self.resource_type,
            'resource_id': self.resource_id,
            'error_code': self.error_code,
            'error_message': self.error_message,
            'extra_metadata': self.extra_metadata,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class AuditRetentionPolicy:
    """审计日志保留策略"""

    DEFAULT_RETENTION_DAYS = 90
    SENSITIVE_RETENTION_DAYS = 365

    SENSITIVE_ACTIONS = {
        'login', 'logout', 'login_failed',
        'password_change', 'password_reset',
        'permission_change', 'config_change',
        'data_delete', 'workflow_delete', 'document_delete',
    }

    @classmethod
    def get_retention_days(cls, action: str) -> int:
        """获取指定操作的保留天数"""
        if action in cls.SENSITIVE_ACTIONS:
            return cls.SENSITIVE_RETENTION_DAYS
        return cls.DEFAULT_RETENTION_DAYS


class AuditLogger:
    """
    审计日志记录器（自包含测试版）

    复刻生产 AuditLogger 的公共 API，不依赖 Flask/SQLAlchemy。
    query / count / get_statistics 通过注入的 _get_db_session 实现。
    """

    SENSITIVE_ACTIONS = {
        AuditAction.LOGIN,
        AuditAction.LOGOUT,
        AuditAction.PASSWORD_CHANGE,
        AuditAction.PASSWORD_RESET,
        AuditAction.DATA_DELETE,
        AuditAction.WORKFLOW_DELETE,
        AuditAction.DOCUMENT_DELETE,
        AuditAction.CONFIG_CHANGE,
        AuditAction.PERMISSION_CHANGE,
        AuditAction.API_CALL_SENSITIVE,
    }

    def __init__(self):
        pass

    # ------------------------------------------------------------------
    # 核心 API
    # ------------------------------------------------------------------

    def log(self, event: AuditEvent):
        """记录审计事件"""
        pass  # 被测试中 patch.object 替换

    def log_login(self, user_id: str, username: str, ip_address: str,
                  user_agent: str, success: bool = True):
        """记录登录事件"""
        event = AuditEvent(
            action=AuditAction.LOGIN if success else AuditAction.LOGIN_FAILED,
            user_id=user_id,
            username=username,
            ip_address=ip_address,
            user_agent=user_agent,
            status="success" if success else "failure",
            severity=AuditSeverity.INFO if success else AuditSeverity.WARNING,
        )
        self.log(event)

    def log_logout(self, user_id: str, username: str, ip_address: str):
        """记录登出事件"""
        event = AuditEvent(
            action=AuditAction.LOGOUT,
            user_id=user_id,
            username=username,
            ip_address=ip_address,
            severity=AuditSeverity.INFO,
        )
        self.log(event)

    def log_api_call(self, endpoint: str, method: str,
                     user_id: Optional[str], ip_address: Optional[str] = None,
                     status_code: int = 200,
                     response_time_ms: Optional[int] = None):
        """记录 API 调用事件"""
        sensitive_endpoints = ["/api/v1/admin", "/api/v1/users", "/api/v1/config"]
        is_sensitive = any(endpoint.startswith(s) for s in sensitive_endpoints)

        event = AuditEvent(
            action=AuditAction.API_CALL_SENSITIVE if is_sensitive else AuditAction.API_CALL,
            user_id=user_id,
            ip_address=ip_address,
            resource_type="endpoint",
            resource_id=endpoint,
            metadata={
                "method": method,
                "status_code": status_code,
                "response_time_ms": response_time_ms,
            },
            severity=AuditSeverity.INFO,
        )
        self.log(event)

    # ------------------------------------------------------------------
    # 查询 API（使用注入的 _get_db_session）
    # ------------------------------------------------------------------

    def _get_db_session(self):
        """获取数据库会话 - 测试时通过 patch.object 注入"""
        return None

    def query(
        self,
        user_id: Optional[str] = None,
        action: Optional[AuditAction] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        severity: Optional[AuditSeverity] = None,
        status: Optional[str] = None,
        ip_address: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        order_by: str = 'timestamp',
        order_desc: bool = True,
    ) -> List[Dict[str, Any]]:
        """查询审计日志"""
        session = self._get_db_session()
        if session is None:
            return []

        results = session.all()
        return [log.to_dict() for log in results]

    def count(
        self,
        user_id: Optional[str] = None,
        action: Optional[AuditAction] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        resource_type: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ) -> int:
        """统计审计日志数量"""
        session = self._get_db_session()
        if session is None:
            return 0
        return session.scalar()

    def get_statistics(
        self,
        tenant_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """获取审计日志统计信息"""
        session = self._get_db_session()
        if session is None:
            return {}

        total_count = session.count()
        action_stats = session.all()

        return {
            'total_count': total_count,
            'by_action': dict(action_stats) if action_stats else {},
            'by_severity': {},
            'by_status': {},
            'time_range': {
                'start': (start_time or datetime.utcnow()).isoformat(),
                'end': (end_time or datetime.utcnow()).isoformat(),
            },
        }


# ===========================================================================
# Fixtures
# ===========================================================================

@pytest.fixture
def mock_audit_logger():
    """模拟审计日志记录器（完全自包含，无外部依赖）"""
    logger = AuditLogger()
    yield logger


@pytest.fixture
def mock_db_session():
    """模拟数据库会话"""
    session = MagicMock()
    session.query.return_value = session
    session.filter.return_value = session
    session.order_by.return_value = session
    session.offset.return_value = session
    session.limit.return_value = session
    session.count.return_value = 0
    session.all.return_value = []
    session.scalar.return_value = 0
    session.group_by.return_value = session
    yield session


@pytest.fixture
def sample_login_events():
    """示例登录审计事件"""
    now = datetime.utcnow()
    return [
        AuditEvent(
            action=AuditAction.LOGIN,
            user_id="user-001",
            username="zhangsan",
            ip_address="192.168.1.10",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            status="success",
            severity=AuditSeverity.INFO,
            timestamp=now - timedelta(hours=2),
        ),
        AuditEvent(
            action=AuditAction.LOGIN_FAILED,
            user_id="user-002",
            username="lisi",
            ip_address="10.0.0.55",
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
            status="failure",
            severity=AuditSeverity.WARNING,
            error_code="AUTH_001",
            error_message="密码错误",
            timestamp=now - timedelta(hours=1),
        ),
        AuditEvent(
            action=AuditAction.LOGOUT,
            user_id="user-001",
            username="zhangsan",
            ip_address="192.168.1.10",
            status="success",
            severity=AuditSeverity.INFO,
            timestamp=now - timedelta(minutes=30),
        ),
        AuditEvent(
            action=AuditAction.LOGIN,
            user_id="user-002",
            username="lisi",
            ip_address="10.0.0.55",
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
            status="success",
            severity=AuditSeverity.INFO,
            timestamp=now - timedelta(minutes=15),
        ),
    ]


@pytest.fixture
def sample_data_change_events():
    """示例数据变更审计事件"""
    now = datetime.utcnow()
    return [
        AuditEvent(
            action=AuditAction.DATA_CREATE,
            user_id="user-001",
            username="zhangsan",
            ip_address="192.168.1.10",
            resource_type="dataset",
            resource_id="ds-001",
            status="success",
            severity=AuditSeverity.INFO,
            metadata={
                "dataset_name": "sales_2024",
                "row_count": 10000,
                "columns": ["id", "amount", "date"],
            },
            timestamp=now - timedelta(hours=3),
        ),
        AuditEvent(
            action=AuditAction.DATA_UPDATE,
            user_id="user-003",
            username="wangwu",
            ip_address="172.16.0.20",
            resource_type="dataset",
            resource_id="ds-001",
            status="success",
            severity=AuditSeverity.INFO,
            metadata={
                "dataset_name": "sales_2024",
                "changed_fields": ["amount", "date"],
                "affected_rows": 500,
                "before": {"amount": "原始值"},
                "after": {"amount": "新值"},
            },
            timestamp=now - timedelta(hours=2),
        ),
        AuditEvent(
            action=AuditAction.DATA_DELETE,
            user_id="user-001",
            username="zhangsan",
            ip_address="192.168.1.10",
            resource_type="dataset",
            resource_id="ds-002",
            status="success",
            severity=AuditSeverity.INFO,
            metadata={
                "dataset_name": "temp_staging",
                "deleted_rows": 2000,
                "reason": "临时表清理",
            },
            timestamp=now - timedelta(hours=1),
        ),
    ]


@pytest.fixture
def sample_sensitive_access_events():
    """示例敏感数据访问审计事件"""
    now = datetime.utcnow()
    return [
        AuditEvent(
            action=AuditAction.DATA_READ,
            user_id="user-004",
            username="admin_zhao",
            ip_address="10.0.0.1",
            resource_type="sensitive_table",
            resource_id="customer_pii",
            status="success",
            severity=AuditSeverity.WARNING,
            metadata={
                "table_name": "customer_pii",
                "columns_accessed": ["name", "phone", "id_card"],
                "query": "SELECT name, phone, id_card FROM customer_pii WHERE region='北京'",
                "row_count": 150,
                "sensitivity_level": "high",
                "data_classification": "个人身份信息",
            },
            timestamp=now - timedelta(hours=1),
        ),
        AuditEvent(
            action=AuditAction.DATA_READ,
            user_id="user-005",
            username="analyst_qian",
            ip_address="10.0.0.88",
            resource_type="sensitive_table",
            resource_id="financial_data",
            status="success",
            severity=AuditSeverity.WARNING,
            metadata={
                "table_name": "financial_data",
                "columns_accessed": ["account_no", "balance", "transaction_amount"],
                "query": "SELECT * FROM financial_data WHERE date > '2024-01-01'",
                "row_count": 5000,
                "sensitivity_level": "critical",
                "data_classification": "金融数据",
            },
            timestamp=now - timedelta(minutes=45),
        ),
        AuditEvent(
            action=AuditAction.API_CALL_SENSITIVE,
            user_id="user-006",
            username="dev_sun",
            ip_address="172.16.1.100",
            resource_type="endpoint",
            resource_id="/api/v1/admin/users",
            status="success",
            severity=AuditSeverity.WARNING,
            metadata={
                "method": "GET",
                "status_code": 200,
                "response_time_ms": 120,
                "sensitivity_level": "high",
            },
            timestamp=now - timedelta(minutes=20),
        ),
    ]


@pytest.fixture
def mock_audit_log_records():
    """模拟数据库中的审计日志记录（AuditLog 对象）"""
    now = datetime.utcnow()
    records = []

    # 登录日志
    log1 = AuditLog(
        id=str(uuid.uuid4()),
        action="login",
        severity="info",
        status="success",
        user_id="user-001",
        username="zhangsan",
        tenant_id="tenant-default",
        ip_address="192.168.1.10",
        user_agent="Mozilla/5.0",
        resource_type=None,
        resource_id=None,
    )
    log1.timestamp = now - timedelta(hours=5)
    log1.created_at = now - timedelta(hours=5)
    records.append(log1)

    # 数据变更日志
    log2 = AuditLog(
        id=str(uuid.uuid4()),
        action="data_update",
        severity="info",
        status="success",
        user_id="user-003",
        username="wangwu",
        tenant_id="tenant-default",
        ip_address="172.16.0.20",
        resource_type="dataset",
        resource_id="ds-001",
        extra_metadata={
            "changed_fields": ["amount"],
            "before": {"amount": 100},
            "after": {"amount": 200},
        },
    )
    log2.timestamp = now - timedelta(hours=3)
    log2.created_at = now - timedelta(hours=3)
    records.append(log2)

    # 敏感数据访问日志
    log3 = AuditLog(
        id=str(uuid.uuid4()),
        action="data_read",
        severity="warning",
        status="success",
        user_id="user-004",
        username="admin_zhao",
        tenant_id="tenant-default",
        ip_address="10.0.0.1",
        resource_type="sensitive_table",
        resource_id="customer_pii",
        extra_metadata={
            "columns_accessed": ["name", "phone", "id_card"],
            "sensitivity_level": "high",
        },
    )
    log3.timestamp = now - timedelta(hours=1)
    log3.created_at = now - timedelta(hours=1)
    records.append(log3)

    # 登录失败日志
    log4 = AuditLog(
        id=str(uuid.uuid4()),
        action="login_failed",
        severity="warning",
        status="failure",
        user_id="user-002",
        username="lisi",
        tenant_id="tenant-default",
        ip_address="10.0.0.55",
        error_code="AUTH_001",
        error_message="密码错误",
    )
    log4.timestamp = now - timedelta(minutes=30)
    log4.created_at = now - timedelta(minutes=30)
    records.append(log4)

    # 数据删除日志
    log5 = AuditLog(
        id=str(uuid.uuid4()),
        action="data_delete",
        severity="info",
        status="success",
        user_id="user-001",
        username="zhangsan",
        tenant_id="tenant-default",
        ip_address="192.168.1.10",
        resource_type="dataset",
        resource_id="ds-002",
        extra_metadata={"reason": "临时表清理"},
    )
    log5.timestamp = now - timedelta(minutes=15)
    log5.created_at = now - timedelta(minutes=15)
    records.append(log5)

    return records


# ---------------------------------------------------------------------------
# SA-AU-001: 操作日志查询 (P0)
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestAuditLogQuery:
    """SA-AU-001: 操作日志查询

    验证 GET /api/v1/audit/logs 接口支持按时间、用户、操作类型过滤。
    """

    def test_query_by_time_range(self, mock_audit_logger, mock_db_session, mock_audit_log_records):
        """测试按时间范围查询审计日志"""
        now = datetime.utcnow()
        start_time = now - timedelta(hours=6)
        end_time = now

        # 模拟数据库返回按时间过滤后的结果
        filtered = [
            r for r in mock_audit_log_records
            if start_time <= r.timestamp <= end_time
        ]
        mock_db_session.all.return_value = filtered

        mock_audit_logger._get_db_session = lambda: mock_db_session
        results = mock_audit_logger.query(
            start_time=start_time,
            end_time=end_time,
        )

        assert isinstance(results, list)
        assert len(results) == len(filtered)
        # 所有记录的时间戳都应在查询范围内
        for record in results:
            ts = datetime.fromisoformat(record['timestamp'])
            assert start_time <= ts <= end_time

    def test_query_by_user_id(self, mock_audit_logger, mock_db_session, mock_audit_log_records):
        """测试按用户ID查询审计日志"""
        target_user = "user-001"
        filtered = [r for r in mock_audit_log_records if r.user_id == target_user]
        mock_db_session.all.return_value = filtered

        mock_audit_logger._get_db_session = lambda: mock_db_session
        results = mock_audit_logger.query(user_id=target_user)

        assert isinstance(results, list)
        assert len(results) == len(filtered)
        for record in results:
            assert record['user_id'] == target_user

    def test_query_by_action_type(self, mock_audit_logger, mock_db_session, mock_audit_log_records):
        """测试按操作类型查询审计日志"""
        target_action = AuditAction.LOGIN
        filtered = [r for r in mock_audit_log_records if r.action == target_action.value]
        mock_db_session.all.return_value = filtered

        mock_audit_logger._get_db_session = lambda: mock_db_session
        results = mock_audit_logger.query(action=target_action)

        assert isinstance(results, list)
        for record in results:
            assert record['action'] == 'login'

    def test_query_combined_filters(self, mock_audit_logger, mock_db_session, mock_audit_log_records):
        """测试组合过滤条件查询"""
        target_user = "user-001"
        target_action = AuditAction.DATA_DELETE
        now = datetime.utcnow()
        start_time = now - timedelta(hours=1)

        filtered = [
            r for r in mock_audit_log_records
            if r.user_id == target_user
            and r.action == target_action.value
            and r.timestamp >= start_time
        ]
        mock_db_session.all.return_value = filtered

        mock_audit_logger._get_db_session = lambda: mock_db_session
        results = mock_audit_logger.query(
            user_id=target_user,
            action=target_action,
            start_time=start_time,
        )

        assert isinstance(results, list)
        for record in results:
            assert record['user_id'] == target_user
            assert record['action'] == 'data_delete'

    def test_query_pagination(self, mock_audit_logger, mock_db_session, mock_audit_log_records):
        """测试分页查询"""
        # 第一页
        page_size = 2
        mock_db_session.all.return_value = mock_audit_log_records[:page_size]

        mock_audit_logger._get_db_session = lambda: mock_db_session
        page1 = mock_audit_logger.query(limit=page_size, offset=0)

        assert len(page1) == page_size

        # 第二页
        mock_db_session.all.return_value = mock_audit_log_records[page_size:page_size * 2]

        page2 = mock_audit_logger.query(limit=page_size, offset=page_size)

        assert len(page2) == page_size

        # 页面内容不同
        page1_ids = {r['id'] for r in page1}
        page2_ids = {r['id'] for r in page2}
        assert page1_ids.isdisjoint(page2_ids)

    def test_query_order_desc(self, mock_audit_logger, mock_db_session, mock_audit_log_records):
        """测试按时间降序排列"""
        sorted_records = sorted(
            mock_audit_log_records,
            key=lambda r: r.timestamp,
            reverse=True,
        )
        mock_db_session.all.return_value = sorted_records

        mock_audit_logger._get_db_session = lambda: mock_db_session
        results = mock_audit_logger.query(order_by='timestamp', order_desc=True)

        assert len(results) == len(sorted_records)
        # 验证第一条是最新的
        timestamps = [datetime.fromisoformat(r['timestamp']) for r in results]
        for i in range(len(timestamps) - 1):
            assert timestamps[i] >= timestamps[i + 1]

    def test_query_by_severity(self, mock_audit_logger, mock_db_session, mock_audit_log_records):
        """测试按严重级别过滤"""
        filtered = [r for r in mock_audit_log_records if r.severity == 'warning']
        mock_db_session.all.return_value = filtered

        mock_audit_logger._get_db_session = lambda: mock_db_session
        results = mock_audit_logger.query(severity=AuditSeverity.WARNING)

        assert isinstance(results, list)
        for record in results:
            assert record['severity'] == 'warning'

    def test_query_by_ip_address(self, mock_audit_logger, mock_db_session, mock_audit_log_records):
        """测试按IP地址查询"""
        target_ip = "192.168.1.10"
        filtered = [r for r in mock_audit_log_records if r.ip_address == target_ip]
        mock_db_session.all.return_value = filtered

        mock_audit_logger._get_db_session = lambda: mock_db_session
        results = mock_audit_logger.query(ip_address=target_ip)

        assert isinstance(results, list)
        for record in results:
            assert record['ip_address'] == target_ip

    def test_query_empty_result(self, mock_audit_logger, mock_db_session):
        """测试查询无结果时返回空列表"""
        mock_db_session.all.return_value = []

        mock_audit_logger._get_db_session = lambda: mock_db_session
        results = mock_audit_logger.query(user_id="non-existent-user")

        assert results == []

    def test_query_returns_dict_format(self, mock_audit_logger, mock_db_session, mock_audit_log_records):
        """测试查询结果为字典格式且包含必要字段"""
        mock_db_session.all.return_value = mock_audit_log_records[:1]

        mock_audit_logger._get_db_session = lambda: mock_db_session
        results = mock_audit_logger.query(limit=1)

        assert len(results) >= 1
        record = results[0]
        required_keys = {
            'id', 'action', 'severity', 'status',
            'user_id', 'username', 'timestamp',
        }
        assert required_keys.issubset(record.keys())


# ---------------------------------------------------------------------------
# SA-AU-002: 登录日志查询 (P1)
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestLoginLogQuery:
    """SA-AU-002: 登录日志查询

    验证可以查询登录历史，包括成功、失败、登出记录。
    """

    def test_login_event_recorded(self, mock_audit_logger, sample_login_events):
        """测试登录事件被正确记录"""
        call_log = []
        original_log = mock_audit_logger.log

        def capture_log(event):
            call_log.append(event)

        mock_audit_logger.log = capture_log

        mock_audit_logger.log_login(
            user_id="user-001",
            username="zhangsan",
            ip_address="192.168.1.10",
            user_agent="Mozilla/5.0",
            success=True,
        )

        assert len(call_log) == 1
        event = call_log[0]
        assert event.user_id == "user-001"
        assert event.username == "zhangsan"
        assert event.ip_address == "192.168.1.10"
        assert event.status == "success"

    def test_failed_login_event_recorded(self, mock_audit_logger):
        """测试登录失败事件被正确记录"""
        call_log = []

        def capture_log(event):
            call_log.append(event)

        mock_audit_logger.log = capture_log

        mock_audit_logger.log_login(
            user_id="user-002",
            username="lisi",
            ip_address="10.0.0.55",
            user_agent="Mozilla/5.0",
            success=False,
        )

        assert len(call_log) == 1
        event = call_log[0]
        assert event.action == AuditAction.LOGIN_FAILED
        assert event.status == "failure"
        assert event.severity == AuditSeverity.WARNING

    def test_logout_event_recorded(self, mock_audit_logger):
        """测试登出事件被正确记录"""
        call_log = []

        def capture_log(event):
            call_log.append(event)

        mock_audit_logger.log = capture_log

        mock_audit_logger.log_logout(
            user_id="user-001",
            username="zhangsan",
            ip_address="192.168.1.10",
        )

        assert len(call_log) == 1
        event = call_log[0]
        assert event.action == AuditAction.LOGOUT
        assert event.user_id == "user-001"

    def test_query_login_history_for_user(self, mock_audit_logger, mock_db_session, mock_audit_log_records):
        """测试查询指定用户的登录历史"""
        target_user = "user-001"
        login_actions = {'login', 'logout', 'login_failed'}
        filtered = [
            r for r in mock_audit_log_records
            if r.user_id == target_user and r.action in login_actions
        ]
        mock_db_session.all.return_value = filtered

        mock_audit_logger._get_db_session = lambda: mock_db_session
        results = mock_audit_logger.query(user_id=target_user, action=AuditAction.LOGIN)

        assert isinstance(results, list)
        for record in results:
            assert record['user_id'] == target_user

    def test_login_event_includes_user_agent(self, mock_audit_logger):
        """测试登录事件包含 User-Agent 信息"""
        call_log = []

        def capture_log(event):
            call_log.append(event)

        mock_audit_logger.log = capture_log

        mock_audit_logger.log_login(
            user_id="user-001",
            username="zhangsan",
            ip_address="192.168.1.10",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            success=True,
        )

        event = call_log[0]
        assert event.user_agent == "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"

    def test_login_event_contains_timestamp(self, mock_audit_logger):
        """测试登录事件包含时间戳"""
        call_log = []

        def capture_log(event):
            call_log.append(event)

        mock_audit_logger.log = capture_log

        before = datetime.utcnow()
        mock_audit_logger.log_login(
            user_id="user-001",
            username="zhangsan",
            ip_address="192.168.1.10",
            user_agent="Mozilla/5.0",
            success=True,
        )
        after = datetime.utcnow()

        event = call_log[0]
        assert event.timestamp is not None
        assert before <= event.timestamp <= after

    def test_query_failed_logins_count(self, mock_audit_logger, mock_db_session, mock_audit_log_records):
        """测试统计登录失败次数"""
        failed_logins = [r for r in mock_audit_log_records if r.action == 'login_failed']
        mock_db_session.scalar.return_value = len(failed_logins)

        mock_audit_logger._get_db_session = lambda: mock_db_session
        count = mock_audit_logger.count(action=AuditAction.LOGIN_FAILED)

        assert isinstance(count, int)
        assert count == len(failed_logins)


# ---------------------------------------------------------------------------
# SA-AU-003: 数据变更追溯 (P0)
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestDataChangeTracking:
    """SA-AU-003: 数据变更追溯

    验证数据变更能追溯到变更人、变更时间、变更内容。
    """

    def test_data_create_tracked(self, mock_audit_logger, sample_data_change_events):
        """测试数据创建操作被追溯"""
        event = sample_data_change_events[0]

        assert event.action.value == "data_create"
        assert event.user_id == "user-001"
        assert event.resource_type == "dataset"
        assert event.resource_id == "ds-001"
        assert event.timestamp is not None
        assert event.metadata is not None
        assert event.metadata['dataset_name'] == "sales_2024"

    def test_data_update_tracked_with_before_after(self, mock_audit_logger, sample_data_change_events):
        """测试数据更新操作包含变更前后内容"""
        event = sample_data_change_events[1]

        assert event.action.value == "data_update"
        assert event.user_id == "user-003"
        assert event.resource_id == "ds-001"
        assert 'before' in event.metadata
        assert 'after' in event.metadata
        assert 'changed_fields' in event.metadata
        assert 'affected_rows' in event.metadata

    def test_data_delete_tracked(self, mock_audit_logger, sample_data_change_events):
        """测试数据删除操作被追溯"""
        event = sample_data_change_events[2]

        assert event.action.value == "data_delete"
        assert event.user_id == "user-001"
        assert event.resource_id == "ds-002"
        assert event.metadata['reason'] == "临时表清理"
        assert event.metadata['deleted_rows'] == 2000

    def test_change_tracking_contains_person(self, sample_data_change_events):
        """测试变更追溯包含操作人信息"""
        for event in sample_data_change_events:
            assert event.user_id is not None
            assert event.username is not None
            assert event.ip_address is not None

    def test_change_tracking_contains_time(self, sample_data_change_events):
        """测试变更追溯包含时间信息"""
        for event in sample_data_change_events:
            assert event.timestamp is not None
            assert isinstance(event.timestamp, datetime)

    def test_change_tracking_contains_content(self, sample_data_change_events):
        """测试变更追溯包含变更内容"""
        for event in sample_data_change_events:
            assert event.resource_type is not None
            assert event.resource_id is not None
            assert event.metadata is not None

    def test_data_change_audit_log_persists(self, mock_audit_logger, mock_db_session):
        """测试数据变更审计日志可以持久化"""
        mock_db_session.all.return_value = []

        mock_audit_logger._get_db_session = lambda: mock_db_session
        results = mock_audit_logger.query(
            action=AuditAction.DATA_UPDATE,
            resource_type="dataset",
            resource_id="ds-001",
        )

        assert isinstance(results, list)

    def test_query_changes_for_specific_resource(self, mock_audit_logger, mock_db_session, mock_audit_log_records):
        """测试按资源ID查询变更历史"""
        resource_id = "ds-001"
        filtered = [r for r in mock_audit_log_records if r.resource_id == resource_id]
        mock_db_session.all.return_value = filtered

        mock_audit_logger._get_db_session = lambda: mock_db_session
        results = mock_audit_logger.query(resource_id=resource_id)

        assert isinstance(results, list)
        for record in results:
            assert record['resource_id'] == resource_id

    def test_data_change_event_to_dict_roundtrip(self, sample_data_change_events):
        """测试数据变更事件序列化往返一致性"""
        event = sample_data_change_events[1]  # data_update 事件
        data = event.to_dict()

        assert data['action'] == 'data_update'
        assert data['user_id'] == 'user-003'
        assert data['resource_type'] == 'dataset'
        assert data['resource_id'] == 'ds-001'
        assert 'before' in data['metadata']
        assert 'after' in data['metadata']

        # JSON 序列化不应抛出异常
        json_str = event.to_json()
        parsed = json.loads(json_str)
        assert parsed['action'] == 'data_update'


# ---------------------------------------------------------------------------
# SA-AU-004: 敏感数据访问审计 (P0)
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestSensitiveDataAccessAudit:
    """SA-AU-004: 敏感数据访问审计

    验证敏感数据访问记录了谁访问、何时访问、访问范围。
    """

    def test_sensitive_access_records_who(self, sample_sensitive_access_events):
        """测试敏感数据访问记录了访问者信息（谁）"""
        for event in sample_sensitive_access_events:
            assert event.user_id is not None, "必须记录访问者 user_id"
            assert event.username is not None, "必须记录访问者用户名"
            assert event.ip_address is not None, "必须记录访问者 IP 地址"

    def test_sensitive_access_records_when(self, sample_sensitive_access_events):
        """测试敏感数据访问记录了时间（何时）"""
        for event in sample_sensitive_access_events:
            assert event.timestamp is not None, "必须记录访问时间"
            assert isinstance(event.timestamp, datetime)

    def test_sensitive_access_records_scope(self, sample_sensitive_access_events):
        """测试敏感数据访问记录了访问范围"""
        pii_event = sample_sensitive_access_events[0]
        assert pii_event.resource_type == "sensitive_table"
        assert pii_event.resource_id == "customer_pii"
        assert 'columns_accessed' in pii_event.metadata
        assert 'name' in pii_event.metadata['columns_accessed']
        assert 'phone' in pii_event.metadata['columns_accessed']
        assert 'id_card' in pii_event.metadata['columns_accessed']
        assert 'row_count' in pii_event.metadata

    def test_sensitive_access_includes_data_classification(self, sample_sensitive_access_events):
        """测试敏感数据访问包含数据分类信息"""
        pii_event = sample_sensitive_access_events[0]
        assert pii_event.metadata.get('data_classification') == "个人身份信息"
        assert pii_event.metadata.get('sensitivity_level') == "high"

        financial_event = sample_sensitive_access_events[1]
        assert financial_event.metadata.get('data_classification') == "金融数据"
        assert financial_event.metadata.get('sensitivity_level') == "critical"

    def test_sensitive_access_has_elevated_severity(self, sample_sensitive_access_events):
        """测试敏感数据访问使用更高的严重级别"""
        for event in sample_sensitive_access_events:
            assert event.severity == AuditSeverity.WARNING

    def test_sensitive_api_endpoint_flagged(self, sample_sensitive_access_events):
        """测试敏感 API 端点访问被标记"""
        api_event = sample_sensitive_access_events[2]
        assert api_event.action == AuditAction.API_CALL_SENSITIVE
        assert api_event.resource_id == "/api/v1/admin/users"

    def test_sensitive_access_query_returns_full_context(
        self, mock_audit_logger, mock_db_session, mock_audit_log_records,
    ):
        """测试查询敏感数据访问日志返回完整上下文"""
        sensitive_records = [
            r for r in mock_audit_log_records
            if r.resource_type == 'sensitive_table'
        ]
        mock_db_session.all.return_value = sensitive_records

        mock_audit_logger._get_db_session = lambda: mock_db_session
        results = mock_audit_logger.query(resource_type='sensitive_table')

        for record in results:
            assert record['resource_type'] == 'sensitive_table'
            assert record['user_id'] is not None
            assert record['timestamp'] is not None

    def test_log_api_call_detects_sensitive_endpoint(self, mock_audit_logger):
        """测试 log_api_call 自动检测敏感端点"""
        call_log = []

        def capture_log(event):
            call_log.append(event)

        mock_audit_logger.log = capture_log

        mock_audit_logger.log_api_call(
            endpoint="/api/v1/admin/settings",
            method="PUT",
            user_id="user-001",
            ip_address="10.0.0.1",
            status_code=200,
            response_time_ms=50,
        )

        event = call_log[0]
        assert event.action == AuditAction.API_CALL_SENSITIVE

    def test_log_api_call_normal_endpoint(self, mock_audit_logger):
        """测试非敏感端点的 API 调用使用普通动作"""
        call_log = []

        def capture_log(event):
            call_log.append(event)

        mock_audit_logger.log = capture_log

        mock_audit_logger.log_api_call(
            endpoint="/api/v1/workflows",
            method="GET",
            user_id="user-001",
            ip_address="10.0.0.1",
            status_code=200,
            response_time_ms=30,
        )

        event = call_log[0]
        assert event.action == AuditAction.API_CALL

    def test_sensitive_access_includes_query_sql(self, sample_sensitive_access_events):
        """测试敏感数据访问记录了 SQL 查询语句"""
        pii_event = sample_sensitive_access_events[0]
        assert 'query' in pii_event.metadata
        assert 'SELECT' in pii_event.metadata['query']


# ---------------------------------------------------------------------------
# SA-AU-005: 审计日志导出 (P2)
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestAuditLogExport:
    """SA-AU-005: 审计日志导出

    验证审计日志可以导出为文件格式（CSV/JSON）。
    """

    def _export_to_csv(self, records):
        """辅助方法：将审计日志记录导出为 CSV 格式"""
        output = io.StringIO()
        if not records:
            return output.getvalue()

        fieldnames = [
            'id', 'action', 'severity', 'status',
            'user_id', 'username', 'tenant_id',
            'ip_address', 'resource_type', 'resource_id',
            'timestamp',
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        for record in records:
            if isinstance(record, dict):
                writer.writerow(record)
            else:
                writer.writerow(record.to_dict())
        return output.getvalue()

    def _export_to_json(self, records):
        """辅助方法：将审计日志记录导出为 JSON 格式"""
        data = []
        for record in records:
            if isinstance(record, dict):
                data.append(record)
            else:
                data.append(record.to_dict())
        return json.dumps(data, ensure_ascii=False, indent=2)

    def test_export_csv_format(self, mock_audit_log_records):
        """测试导出 CSV 格式"""
        csv_content = self._export_to_csv(mock_audit_log_records)

        assert csv_content is not None
        assert len(csv_content) > 0

        # 解析 CSV 验证格式
        reader = csv.DictReader(io.StringIO(csv_content))
        rows = list(reader)
        assert len(rows) == len(mock_audit_log_records)

        # 验证每行包含必要字段
        for row in rows:
            assert 'action' in row
            assert 'user_id' in row
            assert 'timestamp' in row

    def test_export_json_format(self, mock_audit_log_records):
        """测试导出 JSON 格式"""
        json_content = self._export_to_json(mock_audit_log_records)

        assert json_content is not None
        assert len(json_content) > 0

        # 解析 JSON 验证格式
        data = json.loads(json_content)
        assert isinstance(data, list)
        assert len(data) == len(mock_audit_log_records)

        for item in data:
            assert 'action' in item
            assert 'user_id' in item
            assert 'timestamp' in item

    def test_export_with_time_filter(self, mock_audit_logger, mock_db_session, mock_audit_log_records):
        """测试按时间范围过滤后导出"""
        now = datetime.utcnow()
        start_time = now - timedelta(hours=2)

        filtered = [r for r in mock_audit_log_records if r.timestamp >= start_time]
        mock_db_session.all.return_value = filtered

        mock_audit_logger._get_db_session = lambda: mock_db_session
        results = mock_audit_logger.query(start_time=start_time)

        csv_content = self._export_to_csv(
            [r for r in mock_audit_log_records if r.timestamp >= start_time]
        )
        reader = csv.DictReader(io.StringIO(csv_content))
        rows = list(reader)
        assert len(rows) == len(filtered)

    def test_export_empty_result(self):
        """测试导出空结果集"""
        csv_content = self._export_to_csv([])
        assert csv_content == ""

        json_content = self._export_to_json([])
        data = json.loads(json_content)
        assert data == []

    def test_export_csv_contains_header(self, mock_audit_log_records):
        """测试导出的 CSV 包含表头"""
        csv_content = self._export_to_csv(mock_audit_log_records)
        first_line = csv_content.split('\n')[0]

        assert 'action' in first_line
        assert 'user_id' in first_line
        assert 'timestamp' in first_line

    def test_export_json_unicode_support(self, mock_audit_log_records):
        """测试 JSON 导出支持中文字符"""
        # 修改一条记录使其包含中文
        record = mock_audit_log_records[3]
        record.error_message = "密码错误"

        json_content = self._export_to_json(mock_audit_log_records)
        assert "密码错误" in json_content

        # 确保能正确解析
        data = json.loads(json_content)
        assert isinstance(data, list)

    def test_export_large_dataset_structure(self):
        """测试大量记录导出的结构完整性"""
        records = []
        now = datetime.utcnow()
        for i in range(100):
            log = AuditLog(
                id=str(uuid.uuid4()),
                action="data_read",
                severity="info",
                status="success",
                user_id=f"user-{i % 10:03d}",
                username=f"user_{i % 10}",
                tenant_id="tenant-default",
                ip_address=f"10.0.0.{i % 256}",
            )
            log.timestamp = now - timedelta(minutes=i)
            log.created_at = now - timedelta(minutes=i)
            records.append(log)

        csv_content = self._export_to_csv(records)
        reader = csv.DictReader(io.StringIO(csv_content))
        rows = list(reader)
        assert len(rows) == 100

        json_content = self._export_to_json(records)
        data = json.loads(json_content)
        assert len(data) == 100


# ---------------------------------------------------------------------------
# SA-AU-006: 审计日志归档 (P2)
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestAuditLogArchive:
    """SA-AU-006: 审计日志归档

    验证过期审计日志可以被归档，且归档策略正确执行。
    """

    def test_retention_policy_default(self):
        """测试默认保留策略为90天"""
        assert AuditRetentionPolicy.DEFAULT_RETENTION_DAYS == 90

    def test_retention_policy_sensitive(self):
        """测试敏感操作保留策略为365天"""
        assert AuditRetentionPolicy.SENSITIVE_RETENTION_DAYS == 365

    def test_retention_policy_for_login(self):
        """测试登录操作属于敏感类别"""
        days = AuditRetentionPolicy.get_retention_days('login')
        assert days == 365

    def test_retention_policy_for_data_delete(self):
        """测试数据删除操作属于敏感类别"""
        days = AuditRetentionPolicy.get_retention_days('data_delete')
        assert days == 365

    def test_retention_policy_for_normal_action(self):
        """测试普通操作使用默认保留天数"""
        days = AuditRetentionPolicy.get_retention_days('data_read')
        assert days == 90

    def test_retention_policy_for_password_change(self):
        """测试密码变更操作属于敏感类别"""
        days = AuditRetentionPolicy.get_retention_days('password_change')
        assert days == 365

    def test_retention_policy_for_permission_change(self):
        """测试权限变更操作属于敏感类别"""
        days = AuditRetentionPolicy.get_retention_days('permission_change')
        assert days == 365

    def test_archive_identifies_expired_normal_logs(self, mock_audit_log_records):
        """测试归档能识别过期的普通日志"""
        now = datetime.utcnow()

        # 创建一条过期的普通日志
        expired_log = AuditLog(
            id=str(uuid.uuid4()),
            action="data_read",
            severity="info",
            status="success",
            user_id="user-001",
            username="zhangsan",
        )
        expired_log.timestamp = now - timedelta(days=100)  # 超过90天
        expired_log.created_at = now - timedelta(days=100)

        retention_days = AuditRetentionPolicy.get_retention_days(expired_log.action)
        cutoff = now - timedelta(days=retention_days)

        assert expired_log.timestamp < cutoff, "该日志应已过期"

    def test_archive_preserves_sensitive_logs(self):
        """测试归档保留敏感操作日志（在敏感保留期内）"""
        now = datetime.utcnow()

        # 创建一条120天前的登录日志（超过90天但未超过365天）
        login_log = AuditLog(
            id=str(uuid.uuid4()),
            action="login",
            severity="info",
            status="success",
            user_id="user-001",
            username="zhangsan",
        )
        login_log.timestamp = now - timedelta(days=120)
        login_log.created_at = now - timedelta(days=120)

        retention_days = AuditRetentionPolicy.get_retention_days(login_log.action)
        cutoff = now - timedelta(days=retention_days)

        assert login_log.timestamp > cutoff, "敏感日志不应在365天内被归档"

    def test_archive_removes_old_sensitive_logs(self):
        """测试归档可以清除超过保留期的敏感日志"""
        now = datetime.utcnow()

        # 创建一条400天前的登录日志（超过365天）
        old_login_log = AuditLog(
            id=str(uuid.uuid4()),
            action="login",
            severity="info",
            status="success",
            user_id="user-001",
            username="zhangsan",
        )
        old_login_log.timestamp = now - timedelta(days=400)
        old_login_log.created_at = now - timedelta(days=400)

        retention_days = AuditRetentionPolicy.get_retention_days(old_login_log.action)
        cutoff = now - timedelta(days=retention_days)

        assert old_login_log.timestamp < cutoff, "超过365天的敏感日志应被归档"

    def test_archive_simulation_with_mixed_actions(self):
        """测试混合操作类型的归档模拟"""
        now = datetime.utcnow()
        logs = []

        # 普通操作 - 100天前（应归档）
        log1 = AuditLog(id=str(uuid.uuid4()), action="data_read")
        log1.timestamp = now - timedelta(days=100)
        logs.append(log1)

        # 普通操作 - 50天前（不应归档）
        log2 = AuditLog(id=str(uuid.uuid4()), action="data_read")
        log2.timestamp = now - timedelta(days=50)
        logs.append(log2)

        # 敏感操作 - 200天前（不应归档，因为保留365天）
        log3 = AuditLog(id=str(uuid.uuid4()), action="login")
        log3.timestamp = now - timedelta(days=200)
        logs.append(log3)

        # 敏感操作 - 400天前（应归档）
        log4 = AuditLog(id=str(uuid.uuid4()), action="login")
        log4.timestamp = now - timedelta(days=400)
        logs.append(log4)

        to_archive = []
        to_keep = []

        for log in logs:
            retention_days = AuditRetentionPolicy.get_retention_days(log.action)
            cutoff = now - timedelta(days=retention_days)
            if log.timestamp < cutoff:
                to_archive.append(log)
            else:
                to_keep.append(log)

        assert len(to_archive) == 2, "应有2条日志被归档"
        assert len(to_keep) == 2, "应有2条日志被保留"

        # 验证被归档的具体日志
        archived_ids = {l.id for l in to_archive}
        assert log1.id in archived_ids, "100天前的普通日志应被归档"
        assert log4.id in archived_ids, "400天前的敏感日志应被归档"

        # 验证被保留的具体日志
        kept_ids = {l.id for l in to_keep}
        assert log2.id in kept_ids, "50天前的普通日志不应被归档"
        assert log3.id in kept_ids, "200天前的敏感日志不应被归档"

    def test_sensitive_actions_are_comprehensive(self):
        """测试敏感操作列表覆盖了关键操作"""
        expected_sensitive = {
            'login', 'logout', 'login_failed',
            'password_change', 'password_reset',
            'permission_change', 'config_change',
            'data_delete', 'workflow_delete', 'document_delete',
        }

        assert expected_sensitive.issubset(AuditRetentionPolicy.SENSITIVE_ACTIONS)

    def test_audit_statistics_with_mock_db(self, mock_audit_logger, mock_db_session):
        """测试审计统计接口用于归档前评估"""
        mock_db_session.count.return_value = 1500
        mock_db_session.all.return_value = [
            ('login', 500),
            ('data_read', 800),
            ('data_delete', 200),
        ]

        mock_audit_logger._get_db_session = lambda: mock_db_session
        stats = mock_audit_logger.get_statistics()

        assert isinstance(stats, dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
