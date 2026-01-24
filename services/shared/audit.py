"""
审计日志模块
Sprint 9: 安全加固
Sprint 29: 审计日志持久化到数据库

记录系统中的敏感操作，用于安全审计和合规
"""

import json
import logging
import threading
import queue
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, List
from enum import Enum
from dataclasses import dataclass, asdict

from .config import get_config

logger = logging.getLogger(__name__)

# 数据库相关导入（延迟加载）
_db_engine = None
_db_session_factory = None
_write_queue = None
_writer_thread = None


class AuditAction(Enum):
    """审计动作类型"""

    # 认证相关
    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILED = "login_failed"
    PASSWORD_CHANGE = "password_change"
    PASSWORD_RESET = "password_reset"

    # 数据访问
    DATA_READ = "data_read"
    DATA_CREATE = "data_create"
    DATA_UPDATE = "data_update"
    DATA_DELETE = "data_delete"

    # 工作流相关
    WORKFLOW_CREATE = "workflow_create"
    WORKFLOW_UPDATE = "workflow_update"
    WORKFLOW_DELETE = "workflow_delete"
    WORKFLOW_EXECUTE = "workflow_execute"

    # 文档相关
    DOCUMENT_UPLOAD = "document_upload"
    DOCUMENT_DELETE = "document_delete"
    DOCUMENT_INDEX = "document_index"

    # 配置变更
    CONFIG_CHANGE = "config_change"
    PERMISSION_CHANGE = "permission_change"

    # API 调用
    API_CALL = "api_call"
    API_CALL_SENSITIVE = "api_call_sensitive"

    # 系统操作
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
    status: str = "success"  # success, failure, partial
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


class AuditLogger:
    """审计日志记录器"""

    # 敏感操作列表（这些操作必须记录）
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
        self.logger = logging.getLogger("audit")
        self._setup_audit_logger()

    def _setup_audit_logger(self):
        """设置审计日志"""
        config = get_config()

        # 审计日志独立文件
        audit_handler = logging.FileHandler(
            config.logging.file or "logs/audit.log"
        )
        audit_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(message)s')
        )
        self.logger.addHandler(audit_handler)
        self.logger.setLevel(logging.INFO)

    def log(self, event: AuditEvent):
        """
        记录审计事件

        Args:
            event: 审计事件
        """
        try:
            # 敏感操作额外处理
            if event.action in self.SENSITIVE_ACTIONS:
                self._handle_sensitive_event(event)

            # 写入审计日志
            self.logger.info(event.to_json())

            # 也可以写入数据库用于查询
            self._persist_to_database(event)

        except Exception as e:
            logger.error(f"Failed to log audit event: {e}")

    def _handle_sensitive_event(self, event: AuditEvent):
        """处理敏感事件（额外的安全措施）"""
        # 可以添加额外的逻辑，如：
        # - 发送告警通知
        # - 实时写入不可变存储
        # - 触发安全审查流程
        pass

    def _persist_to_database(self, event: AuditEvent):
        """
        持久化到数据库

        Sprint 29: 实现审计日志数据库存储

        使用异步批量写入减少性能影响：
        - 将事件放入队列
        - 后台线程批量写入数据库
        """
        global _write_queue, _writer_thread

        # 初始化写入队列和后台线程
        if _write_queue is None:
            _write_queue = queue.Queue(maxsize=10000)
            _writer_thread = threading.Thread(
                target=self._batch_writer,
                daemon=True,
                name="AuditLogWriter"
            )
            _writer_thread.start()

        try:
            # 非阻塞添加到队列
            _write_queue.put_nowait(event)
        except queue.Full:
            logger.warning("Audit log queue is full, event may be lost")

    def _batch_writer(self):
        """后台批量写入线程"""
        batch = []
        batch_size = 100
        flush_interval = 5.0  # 秒
        last_flush = datetime.utcnow()

        while True:
            try:
                # 尝试获取事件，最多等待 1 秒
                event = _write_queue.get(timeout=1.0)
                batch.append(event)

                # 达到批量大小或超过刷新间隔时写入
                now = datetime.utcnow()
                if len(batch) >= batch_size or (now - last_flush).total_seconds() >= flush_interval:
                    self._flush_batch(batch)
                    batch = []
                    last_flush = now

            except queue.Empty:
                # 超时，如果有待写入的数据则刷新
                if batch:
                    self._flush_batch(batch)
                    batch = []
                    last_flush = datetime.utcnow()
            except Exception as e:
                logger.error(f"Audit log writer error: {e}")

    def _flush_batch(self, batch: List[AuditEvent]):
        """将批量事件写入数据库"""
        if not batch:
            return

        try:
            session = self._get_db_session()
            if session is None:
                logger.warning("Database session not available, audit logs not persisted")
                return

            from .models.audit import AuditLog

            # 批量创建审计日志记录
            for event in batch:
                log_entry = AuditLog.from_event(event)
                session.add(log_entry)

            session.commit()
            logger.debug(f"Flushed {len(batch)} audit logs to database")

        except Exception as e:
            logger.error(f"Failed to flush audit logs to database: {e}")
            if session:
                session.rollback()
        finally:
            if session:
                session.close()

    def _get_db_session(self):
        """获取数据库会话"""
        global _db_engine, _db_session_factory

        if _db_session_factory is None:
            try:
                from sqlalchemy import create_engine
                from sqlalchemy.orm import sessionmaker
                from .models.audit import AuditLogBase

                config = get_config()
                _db_engine = create_engine(
                    config.database.url,
                    pool_size=5,
                    max_overflow=10,
                    pool_pre_ping=True
                )

                # 创建表（如果不存在）
                AuditLogBase.metadata.create_all(_db_engine)

                _db_session_factory = sessionmaker(bind=_db_engine)
            except Exception as e:
                logger.error(f"Failed to initialize audit database: {e}")
                return None

        return _db_session_factory()

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
        order_desc: bool = True
    ) -> List[Dict[str, Any]]:
        """
        查询审计日志

        Sprint 29: 实现数据库查询

        Args:
            user_id: 用户 ID
            action: 动作类型
            start_time: 开始时间
            end_time: 结束时间
            resource_type: 资源类型
            resource_id: 资源 ID
            tenant_id: 租户 ID
            severity: 严重级别
            status: 执行状态
            ip_address: IP 地址
            limit: 返回数量限制
            offset: 分页偏移
            order_by: 排序字段
            order_desc: 是否降序

        Returns:
            审计日志列表（字典格式）
        """
        try:
            session = self._get_db_session()
            if session is None:
                logger.warning("Database session not available for query")
                return []

            from .models.audit import AuditLog

            query = session.query(AuditLog)

            # 应用过滤条件
            if user_id:
                query = query.filter(AuditLog.user_id == user_id)
            if action:
                action_value = action.value if isinstance(action, AuditAction) else action
                query = query.filter(AuditLog.action == action_value)
            if start_time:
                query = query.filter(AuditLog.timestamp >= start_time)
            if end_time:
                query = query.filter(AuditLog.timestamp <= end_time)
            if resource_type:
                query = query.filter(AuditLog.resource_type == resource_type)
            if resource_id:
                query = query.filter(AuditLog.resource_id == resource_id)
            if tenant_id:
                query = query.filter(AuditLog.tenant_id == tenant_id)
            if severity:
                severity_value = severity.value if isinstance(severity, AuditSeverity) else severity
                query = query.filter(AuditLog.severity == severity_value)
            if status:
                query = query.filter(AuditLog.status == status)
            if ip_address:
                query = query.filter(AuditLog.ip_address == ip_address)

            # 排序
            order_column = getattr(AuditLog, order_by, AuditLog.timestamp)
            if order_desc:
                query = query.order_by(order_column.desc())
            else:
                query = query.order_by(order_column.asc())

            # 分页
            query = query.offset(offset).limit(limit)

            # 执行查询
            results = query.all()

            return [log.to_dict() for log in results]

        except Exception as e:
            logger.error(f"Failed to query audit logs: {e}")
            return []
        finally:
            if session:
                session.close()

    def count(
        self,
        user_id: Optional[str] = None,
        action: Optional[AuditAction] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        resource_type: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ) -> int:
        """
        统计审计日志数量

        Args:
            user_id: 用户 ID
            action: 动作类型
            start_time: 开始时间
            end_time: 结束时间
            resource_type: 资源类型
            tenant_id: 租户 ID

        Returns:
            日志数量
        """
        try:
            session = self._get_db_session()
            if session is None:
                return 0

            from sqlalchemy import func
            from .models.audit import AuditLog

            query = session.query(func.count(AuditLog.id))

            if user_id:
                query = query.filter(AuditLog.user_id == user_id)
            if action:
                action_value = action.value if isinstance(action, AuditAction) else action
                query = query.filter(AuditLog.action == action_value)
            if start_time:
                query = query.filter(AuditLog.timestamp >= start_time)
            if end_time:
                query = query.filter(AuditLog.timestamp <= end_time)
            if resource_type:
                query = query.filter(AuditLog.resource_type == resource_type)
            if tenant_id:
                query = query.filter(AuditLog.tenant_id == tenant_id)

            return query.scalar() or 0

        except Exception as e:
            logger.error(f"Failed to count audit logs: {e}")
            return 0
        finally:
            if session:
                session.close()

    def get_statistics(
        self,
        tenant_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        获取审计日志统计信息

        Args:
            tenant_id: 租户 ID
            start_time: 开始时间
            end_time: 结束时间

        Returns:
            统计信息字典
        """
        try:
            session = self._get_db_session()
            if session is None:
                return {}

            from sqlalchemy import func
            from .models.audit import AuditLog

            # 默认时间范围：最近 24 小时
            if end_time is None:
                end_time = datetime.utcnow()
            if start_time is None:
                start_time = end_time - timedelta(hours=24)

            # 基础查询
            base_query = session.query(AuditLog).filter(
                AuditLog.timestamp >= start_time,
                AuditLog.timestamp <= end_time
            )
            if tenant_id:
                base_query = base_query.filter(AuditLog.tenant_id == tenant_id)

            # 总数
            total_count = base_query.count()

            # 按动作统计
            action_stats = session.query(
                AuditLog.action,
                func.count(AuditLog.id)
            ).filter(
                AuditLog.timestamp >= start_time,
                AuditLog.timestamp <= end_time
            )
            if tenant_id:
                action_stats = action_stats.filter(AuditLog.tenant_id == tenant_id)
            action_stats = dict(action_stats.group_by(AuditLog.action).all())

            # 按严重级别统计
            severity_stats = session.query(
                AuditLog.severity,
                func.count(AuditLog.id)
            ).filter(
                AuditLog.timestamp >= start_time,
                AuditLog.timestamp <= end_time
            )
            if tenant_id:
                severity_stats = severity_stats.filter(AuditLog.tenant_id == tenant_id)
            severity_stats = dict(severity_stats.group_by(AuditLog.severity).all())

            # 按状态统计
            status_stats = session.query(
                AuditLog.status,
                func.count(AuditLog.id)
            ).filter(
                AuditLog.timestamp >= start_time,
                AuditLog.timestamp <= end_time
            )
            if tenant_id:
                status_stats = status_stats.filter(AuditLog.tenant_id == tenant_id)
            status_stats = dict(status_stats.group_by(AuditLog.status).all())

            return {
                'total_count': total_count,
                'by_action': action_stats,
                'by_severity': severity_stats,
                'by_status': status_stats,
                'time_range': {
                    'start': start_time.isoformat(),
                    'end': end_time.isoformat()
                }
            }

        except Exception as e:
            logger.error(f"Failed to get audit statistics: {e}")
            return {}
        finally:
            if session:
                session.close()

    def log_login(self, user_id: str, username: str, ip_address: str, user_agent: str, success: bool = True):
        """记录登录事件"""
        event = AuditEvent(
            action=AuditAction.LOGIN if success else AuditAction.LOGIN_FAILED,
            user_id=user_id,
            username=username,
            ip_address=ip_address,
            user_agent=user_agent,
            status="success" if success else "failure",
            severity=AuditSeverity.INFO if success else AuditSeverity.WARNING
        )
        self.log(event)

    def log_logout(self, user_id: str, username: str, ip_address: str):
        """记录登出事件"""
        event = AuditEvent(
            action=AuditAction.LOGOUT,
            user_id=user_id,
            username=username,
            ip_address=ip_address,
            severity=AuditSeverity.INFO
        )
        self.log(event)

    def log_data_access(
        self,
        action: AuditAction,
        user_id: str,
        resource_type: str,
        resource_id: str,
        ip_address: Optional[str] = None
    ):
        """记录数据访问事件"""
        event = AuditEvent(
            action=action,
            user_id=user_id,
            ip_address=ip_address,
            resource_type=resource_type,
            resource_id=resource_id,
            severity=AuditSeverity.INFO
        )
        self.log(event)

    def log_workflow_execute(
        self,
        user_id: str,
        workflow_id: str,
        workflow_name: str,
        ip_address: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None
    ):
        """记录工作流执行事件"""
        event = AuditEvent(
            action=AuditAction.WORKFLOW_EXECUTE,
            user_id=user_id,
            ip_address=ip_address,
            resource_type="workflow",
            resource_id=workflow_id,
            status="success" if success else "failure",
            error_message=error_message,
            metadata={"workflow_name": workflow_name},
            severity=AuditSeverity.INFO if success else AuditSeverity.ERROR
        )
        self.log(event)

    def log_config_change(
        self,
        user_id: str,
        config_key: str,
        old_value: Any,
        new_value: Any,
        ip_address: Optional[str] = None
    ):
        """记录配置变更事件"""
        event = AuditEvent(
            action=AuditAction.CONFIG_CHANGE,
            user_id=user_id,
            ip_address=ip_address,
            resource_type="config",
            resource_id=config_key,
            metadata={
                "old_value": str(old_value),
                "new_value": str(new_value)
            },
            severity=AuditSeverity.WARNING
        )
        self.log(event)

    def log_api_call(
        self,
        endpoint: str,
        method: str,
        user_id: Optional[str],
        ip_address: Optional[str] = None,
        status_code: int = 200,
        response_time_ms: Optional[int] = None
    ):
        """记录 API 调用事件"""
        # 判断是否为敏感 API
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
                "response_time_ms": response_time_ms
            },
            severity=AuditSeverity.INFO
        )
        self.log(event)


# 全局审计日志实例
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """获取全局审计日志实例"""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger


def audit_log(action: AuditAction, **kwargs):
    """
    审计日志装饰器

    Usage:
        @audit_log(AuditAction.DATA_DELETE)
        def delete_document(doc_id):
            ...
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # 执行函数
            result = func(*args, **kwargs)

            # 记录审计日志
            # 这里可以根据需要提取参数信息
            event = AuditEvent(action=action)
            get_audit_logger().log(event)

            return result
        return wrapper
    return decorator


# 便捷函数
def log_login(user_id: str, username: str, ip_address: str, user_agent: str, success: bool = True):
    """记录登录"""
    get_audit_logger().log_login(user_id, username, ip_address, user_agent, success)


def log_logout(user_id: str, username: str, ip_address: str):
    """记录登出"""
    get_audit_logger().log_logout(user_id, username, ip_address)


def log_workflow_execute(user_id: str, workflow_id: str, workflow_name: str, success: bool = True, error: str = None):
    """记录工作流执行"""
    get_audit_logger().log_workflow_execute(user_id, workflow_id, workflow_name, None, success, error)


def log_config_change(user_id: str, config_key: str, old_value: Any, new_value: Any):
    """记录配置变更"""
    get_audit_logger().log_config_change(user_id, config_key, old_value, new_value)
