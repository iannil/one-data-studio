"""
API 版本化模块
Sprint 30: API 成熟度提升

提供:
- API 版本路由
- 版本弃用机制
- 向后兼容支持
"""

import logging
import warnings
from datetime import datetime, timedelta
from typing import Optional, Callable, Dict, Any, List, Set
from functools import wraps
from dataclasses import dataclass, field
from enum import Enum

try:
    from flask import request, jsonify, g, Blueprint
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False
    Blueprint = None

logger = logging.getLogger(__name__)


class VersionStatus(Enum):
    """API 版本状态"""
    CURRENT = "current"          # 当前稳定版本
    BETA = "beta"                # Beta 版本
    DEPRECATED = "deprecated"    # 已弃用
    SUNSET = "sunset"            # 即将下线
    RETIRED = "retired"          # 已下线


@dataclass
class APIVersion:
    """API 版本定义"""
    version: str                               # 版本号，如 "v1", "v2"
    status: VersionStatus                      # 版本状态
    release_date: Optional[datetime] = None    # 发布日期
    deprecation_date: Optional[datetime] = None  # 弃用日期
    sunset_date: Optional[datetime] = None     # 下线日期
    description: str = ""                      # 版本描述
    breaking_changes: List[str] = field(default_factory=list)  # 破坏性变更列表

    @property
    def is_active(self) -> bool:
        """版本是否活跃"""
        return self.status not in [VersionStatus.RETIRED]

    @property
    def is_deprecated(self) -> bool:
        """版本是否已弃用"""
        return self.status in [VersionStatus.DEPRECATED, VersionStatus.SUNSET]

    @property
    def days_until_sunset(self) -> Optional[int]:
        """距离下线的天数"""
        if self.sunset_date:
            delta = self.sunset_date - datetime.utcnow()
            return max(0, delta.days)
        return None


class APIVersionRegistry:
    """
    API 版本注册表

    管理所有 API 版本及其状态
    """

    def __init__(self):
        self._versions: Dict[str, APIVersion] = {}
        self._current_version: Optional[str] = None
        self._default_version: Optional[str] = None

    def register(self, version: APIVersion):
        """
        注册 API 版本

        Args:
            version: API 版本定义
        """
        self._versions[version.version] = version

        # 设置当前版本
        if version.status == VersionStatus.CURRENT:
            self._current_version = version.version
            if self._default_version is None:
                self._default_version = version.version

        logger.info(f"Registered API version: {version.version} ({version.status.value})")

    def get(self, version: str) -> Optional[APIVersion]:
        """获取版本信息"""
        return self._versions.get(version)

    def get_current(self) -> Optional[APIVersion]:
        """获取当前版本"""
        if self._current_version:
            return self._versions.get(self._current_version)
        return None

    def get_default(self) -> Optional[str]:
        """获取默认版本"""
        return self._default_version

    def set_default(self, version: str):
        """设置默认版本"""
        if version in self._versions:
            self._default_version = version

    def list_versions(self, include_retired: bool = False) -> List[APIVersion]:
        """列出所有版本"""
        versions = list(self._versions.values())
        if not include_retired:
            versions = [v for v in versions if v.status != VersionStatus.RETIRED]
        return sorted(versions, key=lambda v: v.version, reverse=True)

    def is_valid_version(self, version: str) -> bool:
        """检查版本是否有效"""
        v = self._versions.get(version)
        return v is not None and v.is_active

    def deprecate(
        self,
        version: str,
        sunset_date: Optional[datetime] = None,
        sunset_days: int = 90
    ):
        """
        弃用版本

        Args:
            version: 版本号
            sunset_date: 下线日期
            sunset_days: 下线倒计时天数（如果未指定 sunset_date）
        """
        v = self._versions.get(version)
        if v:
            v.status = VersionStatus.DEPRECATED
            v.deprecation_date = datetime.utcnow()
            v.sunset_date = sunset_date or (datetime.utcnow() + timedelta(days=sunset_days))
            logger.warning(
                f"API version {version} deprecated. "
                f"Sunset date: {v.sunset_date.isoformat()}"
            )


# 全局版本注册表
_version_registry: Optional[APIVersionRegistry] = None


def get_version_registry() -> APIVersionRegistry:
    """获取全局版本注册表"""
    global _version_registry
    if _version_registry is None:
        _version_registry = APIVersionRegistry()

        # 注册默认版本
        _version_registry.register(APIVersion(
            version="v1",
            status=VersionStatus.CURRENT,
            release_date=datetime(2024, 1, 1),
            description="Stable API version 1.0"
        ))

    return _version_registry


def api_version(
    version: str,
    deprecated: bool = False,
    sunset_date: Optional[datetime] = None,
    alternative: Optional[str] = None
):
    """
    API 版本装饰器

    标记端点的版本信息，并在响应中添加版本头

    Args:
        version: API 版本
        deprecated: 是否已弃用
        sunset_date: 下线日期
        alternative: 替代端点

    Usage:
        @app.route("/api/v1/users")
        @api_version("v1")
        def get_users_v1():
            ...

        @app.route("/api/v1/old-endpoint")
        @api_version("v1", deprecated=True, sunset_date=datetime(2024, 6, 1), alternative="/api/v2/new-endpoint")
        def old_endpoint():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 添加版本信息到上下文
            if FLASK_AVAILABLE:
                g.api_version = version
                g.api_deprecated = deprecated

            # 执行原函数
            result = func(*args, **kwargs)

            # 添加版本响应头
            if FLASK_AVAILABLE and hasattr(result, 'headers'):
                result.headers['X-API-Version'] = version

                if deprecated:
                    result.headers['X-API-Deprecated'] = 'true'

                    if sunset_date:
                        result.headers['X-API-Sunset'] = sunset_date.isoformat()

                    if alternative:
                        result.headers['X-API-Alternative'] = alternative

                    # 添加 Deprecation 头（标准头）
                    result.headers['Deprecation'] = 'true'

                    # 日志警告
                    logger.warning(
                        f"Deprecated API called: {request.method} {request.path} "
                        f"(version: {version})"
                    )

            return result

        # 存储元数据
        wrapper._api_version = version
        wrapper._api_deprecated = deprecated
        wrapper._api_sunset_date = sunset_date
        wrapper._api_alternative = alternative

        return wrapper
    return decorator


def require_api_version(min_version: str = "v1", max_version: Optional[str] = None):
    """
    要求特定 API 版本的装饰器

    Args:
        min_version: 最低版本要求
        max_version: 最高版本要求（可选）

    Usage:
        @app.route("/api/feature")
        @require_api_version("v2")  # 需要 v2 或更高版本
        def new_feature():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not FLASK_AVAILABLE:
                return func(*args, **kwargs)

            # 从请求获取版本
            requested_version = _get_request_version()

            # 版本比较（简单字符串比较，假设 v1 < v2 < v3）
            if requested_version < min_version:
                return jsonify({
                    "code": 40000,
                    "message": f"This endpoint requires API version {min_version} or higher",
                    "error": "version_too_low",
                    "required_version": min_version,
                    "current_version": requested_version
                }), 400

            if max_version and requested_version > max_version:
                return jsonify({
                    "code": 40000,
                    "message": f"This endpoint is not available in API version {requested_version}",
                    "error": "version_not_supported",
                    "max_version": max_version,
                    "current_version": requested_version
                }), 400

            return func(*args, **kwargs)

        return wrapper
    return decorator


def _get_request_version() -> str:
    """
    从请求中获取 API 版本

    优先级:
    1. URL 路径 (/api/v1/...)
    2. 请求头 (X-API-Version)
    3. 查询参数 (api_version)
    4. 默认版本
    """
    if not FLASK_AVAILABLE:
        return "v1"

    # 从 URL 路径提取
    path = request.path
    if '/api/' in path:
        parts = path.split('/')
        for i, part in enumerate(parts):
            if part == 'api' and i + 1 < len(parts):
                version = parts[i + 1]
                if version.startswith('v') and version[1:].isdigit():
                    return version

    # 从请求头获取
    header_version = request.headers.get('X-API-Version')
    if header_version:
        return header_version

    # 从查询参数获取
    query_version = request.args.get('api_version')
    if query_version:
        return query_version

    # 返回默认版本
    registry = get_version_registry()
    return registry.get_default() or "v1"


def version_router(app, prefix: str = "/api"):
    """
    版本路由中间件

    自动处理版本路由和弃用警告

    Args:
        app: Flask 应用
        prefix: API 路径前缀

    Usage:
        app = Flask(__name__)
        version_router(app)
    """
    if not FLASK_AVAILABLE:
        return app

    registry = get_version_registry()

    @app.before_request
    def check_api_version():
        """检查 API 版本"""
        if not request.path.startswith(prefix):
            return None

        version = _get_request_version()
        g.api_version = version

        # 检查版本是否有效
        api_ver = registry.get(version)

        if api_ver is None:
            return jsonify({
                "code": 40000,
                "message": f"API version '{version}' is not supported",
                "error": "unsupported_version",
                "available_versions": [v.version for v in registry.list_versions()]
            }), 400

        if not api_ver.is_active:
            return jsonify({
                "code": 41000,
                "message": f"API version '{version}' has been retired",
                "error": "version_retired",
                "available_versions": [v.version for v in registry.list_versions()]
            }), 410

        # 添加弃用警告到上下文
        if api_ver.is_deprecated:
            g.api_deprecated = True
            g.api_sunset_date = api_ver.sunset_date
            g.api_days_until_sunset = api_ver.days_until_sunset

        return None

    @app.after_request
    def add_version_headers(response):
        """添加版本响应头"""
        if not request.path.startswith(prefix):
            return response

        version = getattr(g, 'api_version', 'v1')
        response.headers['X-API-Version'] = version

        # 弃用警告
        if getattr(g, 'api_deprecated', False):
            response.headers['X-API-Deprecated'] = 'true'
            response.headers['Deprecation'] = 'true'

            sunset_date = getattr(g, 'api_sunset_date', None)
            if sunset_date:
                response.headers['X-API-Sunset'] = sunset_date.isoformat()
                response.headers['Sunset'] = sunset_date.strftime('%a, %d %b %Y %H:%M:%S GMT')

            days = getattr(g, 'api_days_until_sunset', None)
            if days is not None:
                response.headers['Warning'] = (
                    f'299 - "API version {version} is deprecated. '
                    f'Will be retired in {days} days."'
                )

        return response

    return app


# API 版本信息端点
def create_version_info_blueprint() -> 'Blueprint':
    """
    创建版本信息 Blueprint

    提供 /api/versions 端点用于查询支持的版本

    Usage:
        app.register_blueprint(create_version_info_blueprint())
    """
    if not FLASK_AVAILABLE:
        return None

    bp = Blueprint('api_versions', __name__)

    @bp.route('/api/versions')
    def list_versions():
        """列出所有支持的 API 版本"""
        registry = get_version_registry()
        versions = registry.list_versions()

        return jsonify({
            "versions": [
                {
                    "version": v.version,
                    "status": v.status.value,
                    "release_date": v.release_date.isoformat() if v.release_date else None,
                    "deprecation_date": v.deprecation_date.isoformat() if v.deprecation_date else None,
                    "sunset_date": v.sunset_date.isoformat() if v.sunset_date else None,
                    "description": v.description,
                }
                for v in versions
            ],
            "current_version": registry.get_current().version if registry.get_current() else None,
            "default_version": registry.get_default()
        })

    @bp.route('/api/versions/<version>')
    def get_version_info(version: str):
        """获取特定版本信息"""
        registry = get_version_registry()
        v = registry.get(version)

        if v is None:
            return jsonify({
                "code": 40400,
                "message": f"Version '{version}' not found",
                "error": "version_not_found"
            }), 404

        return jsonify({
            "version": v.version,
            "status": v.status.value,
            "is_active": v.is_active,
            "is_deprecated": v.is_deprecated,
            "release_date": v.release_date.isoformat() if v.release_date else None,
            "deprecation_date": v.deprecation_date.isoformat() if v.deprecation_date else None,
            "sunset_date": v.sunset_date.isoformat() if v.sunset_date else None,
            "days_until_sunset": v.days_until_sunset,
            "description": v.description,
            "breaking_changes": v.breaking_changes
        })

    return bp


# 版本化配置
@dataclass
class VersioningConfig:
    """API 版本化配置"""
    default_version: str = "v1"
    supported_versions: List[str] = field(default_factory=lambda: ["v1"])
    allow_version_header: bool = True
    allow_version_query_param: bool = True
    strict_versioning: bool = False  # 是否严格要求版本
    deprecation_warning_days: int = 30  # 弃用警告提前天数


def configure_versioning(app, config: Optional[VersioningConfig] = None):
    """
    配置 API 版本化

    Args:
        app: Flask 应用
        config: 版本化配置

    Usage:
        app = Flask(__name__)
        configure_versioning(app, VersioningConfig(
            default_version="v1",
            supported_versions=["v1", "v2"]
        ))
    """
    config = config or VersioningConfig()

    registry = get_version_registry()
    registry.set_default(config.default_version)

    # 注册支持的版本
    for version in config.supported_versions:
        if registry.get(version) is None:
            registry.register(APIVersion(
                version=version,
                status=VersionStatus.CURRENT if version == config.default_version else VersionStatus.BETA
            ))

    # 应用版本路由中间件
    version_router(app)

    return app
