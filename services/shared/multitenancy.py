"""
多租户 Mixin 和中间件
Sprint 13: 多租户支持
Sprint 29: 租户配额强制执行

提供:
- TenantMixin: 数据模型的租户字段
- TenantContext: 请求级别的租户上下文
- TenantFilter: 自动过滤租户数据
- TenantQuota: 租户配额管理
- check_quota: 配额检查装饰器
"""

import os
import logging
from contextlib import contextmanager
from typing import Optional, Any, Dict, Callable
from functools import wraps
import threading

from sqlalchemy import Column, String, Index, event
from sqlalchemy.orm import Query

logger = logging.getLogger(__name__)


# 全局租户上下文（线程安全）
_tenant_context = threading.local()


def get_current_tenant() -> Optional[str]:
    """获取当前线程的租户 ID"""
    return getattr(_tenant_context, 'tenant_id', None)


def set_current_tenant(tenant_id: Optional[str]):
    """设置当前线程的租户 ID"""
    _tenant_context.tenant_id = tenant_id


def clear_current_tenant():
    """清除当前线程的租户 ID"""
    _tenant_context.tenant_id = None


@contextmanager
def tenant_context(tenant_id: str):
    """
    租户上下文管理器

    Usage:
        with tenant_context("tenant-123"):
            # 所有数据库查询自动带上租户过滤
            workflows = session.query(Workflow).all()
    """
    previous = get_current_tenant()
    set_current_tenant(tenant_id)
    try:
        yield
    finally:
        set_current_tenant(previous)


class TenantMixin:
    """
    多租户 Mixin

    为模型添加租户支持字段

    Usage:
        class Workflow(Base, TenantMixin):
            __tablename__ = "workflows"
            ...
    """

    # 租户 ID 字段
    tenant_id = Column(
        String(64),
        nullable=True,  # 初期允许为空以支持迁移
        index=True,
        comment='租户 ID'
    )

    @classmethod
    def __declare_last__(cls):
        """声明复合索引"""
        # 为需要的列创建复合索引
        if hasattr(cls, '__tablename__'):
            # 创建 (tenant_id, created_at) 复合索引用于常见查询
            idx_name = f"ix_{cls.__tablename__}_tenant_created"
            if hasattr(cls, 'created_at'):
                Index(idx_name, cls.tenant_id, cls.created_at)

    def set_tenant(self, tenant_id: str):
        """设置租户 ID"""
        self.tenant_id = tenant_id

    @classmethod
    def for_tenant(cls, tenant_id: str):
        """创建租户过滤条件"""
        return cls.tenant_id == tenant_id


class TenantQuery:
    """
    租户感知的查询包装器

    自动为查询添加租户过滤条件
    """

    @staticmethod
    def filter_by_tenant(query, model_class, tenant_id: Optional[str] = None):
        """
        为查询添加租户过滤

        Args:
            query: SQLAlchemy Query 对象
            model_class: 模型类
            tenant_id: 可选的租户 ID，未提供时使用上下文中的租户
        """
        tid = tenant_id or get_current_tenant()

        if tid and hasattr(model_class, 'tenant_id'):
            return query.filter(model_class.tenant_id == tid)

        return query


def with_tenant(tenant_id: str):
    """
    装饰器：在指定租户上下文中执行函数

    Usage:
        @with_tenant("tenant-123")
        def my_function():
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with tenant_context(tenant_id):
                return func(*args, **kwargs)
        return wrapper
    return decorator


class TenantMiddleware:
    """
    Flask 租户中间件

    从请求头或 JWT 中提取租户 ID
    """

    def __init__(self, app=None):
        self.app = app
        if app:
            self.init_app(app)

    def init_app(self, app):
        """初始化 Flask 应用"""
        app.before_request(self.before_request)
        app.after_request(self.after_request)

    @staticmethod
    def before_request():
        """请求前处理：提取租户 ID"""
        from flask import request, g

        # 尝试从请求头获取租户 ID
        tenant_id = request.headers.get('X-Tenant-ID')

        # 如果没有，尝试从 JWT claims 获取
        if not tenant_id and hasattr(g, 'jwt_claims'):
            tenant_id = g.jwt_claims.get('tenant_id')

        # 如果还没有，尝试从查询参数获取（开发用途）
        if not tenant_id and os.getenv('ALLOW_TENANT_QUERY_PARAM', 'false').lower() == 'true':
            tenant_id = request.args.get('tenant_id')

        # 设置到上下文
        if tenant_id:
            set_current_tenant(tenant_id)
            g.tenant_id = tenant_id

    @staticmethod
    def after_request(response):
        """请求后处理：清理租户上下文"""
        clear_current_tenant()
        return response


# 租户资源配额
class TenantQuota:
    """
    租户配额管理

    管理每个租户的资源配额限制

    Sprint 29: 增强配额管理和持久化
    """

    # 默认配额（可通过环境变量覆盖）
    DEFAULT_QUOTAS = {
        'max_workflows': int(os.getenv('TENANT_MAX_WORKFLOWS', '100')),
        'max_documents': int(os.getenv('TENANT_MAX_DOCUMENTS', '1000')),
        'max_conversations': int(os.getenv('TENANT_MAX_CONVERSATIONS', '500')),
        'max_vector_storage_mb': int(os.getenv('TENANT_MAX_VECTOR_MB', '10240')),
        'max_api_calls_per_hour': int(os.getenv('TENANT_MAX_API_CALLS', '10000')),
        'max_agents': int(os.getenv('TENANT_MAX_AGENTS', '50')),
        'max_datasets': int(os.getenv('TENANT_MAX_DATASETS', '200')),
        'max_users': int(os.getenv('TENANT_MAX_USERS', '100')),
    }

    # 资源类型到数据库表/模型的映射
    RESOURCE_MODELS = {
        'workflows': 'Workflow',
        'documents': 'IndexedDocument',
        'conversations': 'Conversation',
        'agents': 'Agent',
        'datasets': 'Dataset',
    }

    def __init__(self, tenant_id: str, custom_quotas: dict = None):
        self.tenant_id = tenant_id
        self.quotas = {**self.DEFAULT_QUOTAS, **(custom_quotas or {})}
        self._usage_cache: Dict[str, int] = {}
        self._cache_ttl = 60  # 缓存 60 秒
        self._cache_timestamps: Dict[str, float] = {}

    def check_quota(self, resource: str, current_usage: int) -> bool:
        """
        检查资源是否超配额

        Args:
            resource: 资源类型
            current_usage: 当前使用量

        Returns:
            True 如果未超配额
        """
        max_quota = self.quotas.get(f'max_{resource}', float('inf'))
        return current_usage < max_quota

    def get_quota(self, resource: str) -> int:
        """获取资源配额"""
        return self.quotas.get(f'max_{resource}', -1)

    def get_all_quotas(self) -> dict:
        """获取所有配额"""
        return self.quotas.copy()

    def get_usage(self, resource: str, session=None) -> int:
        """
        获取资源当前使用量

        Args:
            resource: 资源类型
            session: 数据库会话（可选）

        Returns:
            当前使用量
        """
        import time
        now = time.time()

        # 检查缓存
        cache_ts = self._cache_timestamps.get(resource, 0)
        if now - cache_ts < self._cache_ttl and resource in self._usage_cache:
            return self._usage_cache[resource]

        # 从数据库查询
        usage = self._query_usage(resource, session)

        # 更新缓存
        self._usage_cache[resource] = usage
        self._cache_timestamps[resource] = now

        return usage

    def _query_usage(self, resource: str, session=None) -> int:
        """从数据库查询使用量"""
        try:
            if session is None:
                # 尝试获取数据库会话
                try:
                    from models import get_db_session
                    session = get_db_session()
                    should_close = True
                except ImportError:
                    return 0
            else:
                should_close = False

            model_name = self.RESOURCE_MODELS.get(resource)
            if not model_name:
                return 0

            # 动态导入模型
            try:
                from models import get_model_by_name
                model = get_model_by_name(model_name)
                if model and hasattr(model, 'tenant_id'):
                    count = session.query(model).filter(
                        model.tenant_id == self.tenant_id
                    ).count()
                    return count
            except Exception as e:
                logger.debug(f"Failed to query usage for {resource}: {e}")
                return 0
            finally:
                if should_close and session:
                    session.close()

        except Exception as e:
            logger.error(f"Error querying usage: {e}")
            return 0

    def get_usage_summary(self, session=None) -> Dict[str, Dict[str, Any]]:
        """
        获取配额使用情况摘要

        Returns:
            {resource: {quota: int, used: int, remaining: int, percentage: float}}
        """
        summary = {}

        for quota_key in self.quotas:
            if quota_key.startswith('max_'):
                resource = quota_key[4:]  # 去掉 'max_' 前缀
                quota = self.quotas[quota_key]
                used = self.get_usage(resource, session)
                remaining = max(0, quota - used)
                percentage = (used / quota * 100) if quota > 0 else 0

                summary[resource] = {
                    'quota': quota,
                    'used': used,
                    'remaining': remaining,
                    'percentage': round(percentage, 2)
                }

        return summary

    def invalidate_cache(self, resource: str = None):
        """
        使缓存失效

        Args:
            resource: 资源类型，为 None 时清除所有缓存
        """
        if resource:
            self._usage_cache.pop(resource, None)
            self._cache_timestamps.pop(resource, None)
        else:
            self._usage_cache.clear()
            self._cache_timestamps.clear()


# 租户配额缓存
_tenant_quotas: Dict[str, TenantQuota] = {}
_quota_lock = threading.Lock()


def get_tenant_quota(tenant_id: str, custom_quotas: dict = None) -> TenantQuota:
    """
    获取租户配额实例

    Args:
        tenant_id: 租户 ID
        custom_quotas: 自定义配额

    Returns:
        TenantQuota 实例
    """
    global _tenant_quotas

    with _quota_lock:
        if tenant_id not in _tenant_quotas:
            _tenant_quotas[tenant_id] = TenantQuota(tenant_id, custom_quotas)
        return _tenant_quotas[tenant_id]


def check_quota(resource: str, increment: int = 1):
    """
    配额检查装饰器

    Sprint 29: 在资源创建端点强制执行配额检查

    Args:
        resource: 资源类型 (workflows, documents, conversations, etc.)
        increment: 预期增加的数量

    Usage:
        @app.route("/api/v1/workflows", methods=["POST"])
        @require_jwt()
        @check_quota("workflows")
        def create_workflow():
            ...

    Raises:
        返回 429 Too Many Requests 当超出配额时
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                from flask import g, jsonify
            except ImportError:
                # 非 Flask 环境，跳过检查
                return func(*args, **kwargs)

            # 获取租户 ID
            tenant_id = getattr(g, 'tenant_id', None) or get_current_tenant()

            if not tenant_id:
                # 无租户上下文，跳过检查
                return func(*args, **kwargs)

            # 获取配额
            quota = get_tenant_quota(tenant_id)

            # 获取当前使用量
            current_usage = quota.get_usage(resource)
            max_quota = quota.get_quota(resource)

            # 检查是否超配额
            if max_quota > 0 and current_usage + increment > max_quota:
                logger.warning(
                    f"Quota exceeded: tenant={tenant_id}, resource={resource}, "
                    f"current={current_usage}, max={max_quota}"
                )

                return jsonify({
                    "code": 42900,
                    "message": "Quota exceeded",
                    "error": "quota_exceeded",
                    "details": {
                        "resource": resource,
                        "current_usage": current_usage,
                        "max_quota": max_quota,
                        "requested": increment
                    }
                }), 429

            # 配额检查通过，执行原函数
            result = func(*args, **kwargs)

            # 如果创建成功，使缓存失效
            if hasattr(result, '__iter__') and len(result) >= 2:
                status_code = result[1] if isinstance(result, tuple) else 200
                if 200 <= status_code < 300:
                    quota.invalidate_cache(resource)

            return result

        return wrapper
    return decorator


class QuotaExceededError(Exception):
    """配额超限异常"""

    def __init__(self, resource: str, current: int, maximum: int, message: str = None):
        self.resource = resource
        self.current = current
        self.maximum = maximum
        self.message = message or f"Quota exceeded for {resource}: {current}/{maximum}"
        super().__init__(self.message)


def enforce_quota(tenant_id: str, resource: str, increment: int = 1) -> bool:
    """
    程序化配额检查

    在非装饰器场景使用

    Args:
        tenant_id: 租户 ID
        resource: 资源类型
        increment: 预期增加的数量

    Returns:
        True 如果配额未超限

    Raises:
        QuotaExceededError: 当超出配额时
    """
    quota = get_tenant_quota(tenant_id)
    current_usage = quota.get_usage(resource)
    max_quota = quota.get_quota(resource)

    if max_quota > 0 and current_usage + increment > max_quota:
        raise QuotaExceededError(resource, current_usage, max_quota)

    return True


# 向量集合租户隔离
def get_tenant_collection_name(base_name: str, tenant_id: Optional[str] = None) -> str:
    """
    获取租户专属的向量集合名称

    Args:
        base_name: 基础集合名称
        tenant_id: 租户 ID（可选，默认使用上下文中的租户）

    Returns:
        租户专属集合名称
    """
    tid = tenant_id or get_current_tenant()
    if tid:
        # 使用下划线分隔，确保集合名称合法
        safe_tenant = tid.replace('-', '_')[:32]
        return f"{base_name}_{safe_tenant}"
    return base_name


# SQLAlchemy 事件监听器
def setup_tenant_listeners(model_class):
    """
    设置 SQLAlchemy 事件监听器，自动设置租户 ID

    Usage:
        setup_tenant_listeners(Workflow)
    """
    @event.listens_for(model_class, 'before_insert')
    def set_tenant_on_insert(mapper, connection, target):
        """插入前自动设置租户 ID"""
        if hasattr(target, 'tenant_id') and target.tenant_id is None:
            tenant_id = get_current_tenant()
            if tenant_id:
                target.tenant_id = tenant_id
