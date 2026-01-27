"""
共享模块包
Sprint 6-10: 统一配置、错误处理、缓存、限流、审计
"""

from .config import Config, get_config, reload_config
from .error_handler import (
    ErrorCode,
    APIError,
    ValidationError,
    NotFoundError,
    UnauthorizedError,
    ForbiddenError,
    ConflictError,
    DatabaseError,
    ExternalAPIError,
    success_response,
    error_response,
    handle_exception,
    catch_errors,
    validate_required,
    validate_field,
    register_error_handlers,
)

# Initialize __all__ with base exports
__all__ = [
    # Config
    "Config",
    "get_config",
    "reload_config",
    # Error Handling
    "ErrorCode",
    "APIError",
    "ValidationError",
    "NotFoundError",
    "UnauthorizedError",
    "ForbiddenError",
    "ConflictError",
    "DatabaseError",
    "ExternalAPIError",
    "success_response",
    "error_response",
    "handle_exception",
    "catch_errors",
    "validate_required",
    "validate_field",
    "register_error_handlers",
]

# Sprint 8: 缓存
try:
    from .cache import (
        CacheBackend,
        RedisCache,
        get_cache,
        cached,
        cached_metadata,
        cached_model_list,
        cached_workflow,
        cached_search_result,
        clear_cache_pattern,
    )
    __all__ += [
        "CacheBackend",
        "RedisCache",
        "get_cache",
        "cached",
        "cached_metadata",
        "cached_model_list",
        "cached_workflow",
        "cached_search_result",
        "clear_cache_pattern",
    ]
except ImportError:
    pass

# Sprint 9: 限流
try:
    from .rate_limit import (
        RateLimitConfig,
        get_limiter,
        init_rate_limit,
        rate_limit,
        limit_strict,
        limit_read_only,
        limit_default,
        limit_hourly,
        limit_ip,
    )
    __all__ += [
        "RateLimitConfig",
        "get_limiter",
        "init_rate_limit",
        "rate_limit",
        "limit_strict",
        "limit_read_only",
        "limit_default",
        "limit_hourly",
        "limit_ip",
    ]
except ImportError:
    pass

# Sprint 9: 审计日志
try:
    from .audit import (
        AuditAction,
        AuditSeverity,
        AuditEvent,
        AuditLogger,
        get_audit_logger,
        audit_log,
        log_login,
        log_logout,
        log_workflow_execute,
        log_config_change,
    )
    __all__ += [
        "AuditAction",
        "AuditSeverity",
        "AuditEvent",
        "AuditLogger",
        "get_audit_logger",
        "audit_log",
        "log_login",
        "log_logout",
        "log_workflow_execute",
        "log_config_change",
    ]
except ImportError:
    pass

# Sprint 24: Prometheus 指标
try:
    from .prometheus_metrics import (
        PrometheusMetrics,
        get_metrics,
        init_metrics,
        track_operation,
        track_ai_call,
    )
    __all__ += [
        "PrometheusMetrics",
        "get_metrics",
        "init_metrics",
        "track_operation",
        "track_ai_call",
    ]
except ImportError:
    pass
