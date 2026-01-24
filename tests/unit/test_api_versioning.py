"""
API 版本化模块单元测试
Sprint 30: P2 测试覆盖 - API 成熟度提升
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock


class TestVersionStatus:
    """版本状态测试"""

    def test_version_status_values(self):
        """测试版本状态值"""
        from services.shared.api_versioning import VersionStatus

        assert VersionStatus.CURRENT.value == "current"
        assert VersionStatus.BETA.value == "beta"
        assert VersionStatus.DEPRECATED.value == "deprecated"
        assert VersionStatus.SUNSET.value == "sunset"
        assert VersionStatus.RETIRED.value == "retired"


class TestAPIVersion:
    """API 版本测试"""

    def test_version_creation(self):
        """测试版本创建"""
        from services.shared.api_versioning import APIVersion, VersionStatus

        version = APIVersion(
            version="v1",
            status=VersionStatus.CURRENT,
            release_date=datetime(2024, 1, 1),
            description="Stable version"
        )

        assert version.version == "v1"
        assert version.status == VersionStatus.CURRENT
        assert version.is_active is True
        assert version.is_deprecated is False

    def test_version_is_active(self):
        """测试版本活跃状态"""
        from services.shared.api_versioning import APIVersion, VersionStatus

        active = APIVersion("v1", VersionStatus.CURRENT)
        retired = APIVersion("v0", VersionStatus.RETIRED)

        assert active.is_active is True
        assert retired.is_active is False

    def test_version_is_deprecated(self):
        """测试版本弃用状态"""
        from services.shared.api_versioning import APIVersion, VersionStatus

        current = APIVersion("v1", VersionStatus.CURRENT)
        deprecated = APIVersion("v0", VersionStatus.DEPRECATED)
        sunset = APIVersion("v-1", VersionStatus.SUNSET)

        assert current.is_deprecated is False
        assert deprecated.is_deprecated is True
        assert sunset.is_deprecated is True

    def test_days_until_sunset(self):
        """测试距离下线天数"""
        from services.shared.api_versioning import APIVersion, VersionStatus

        future = datetime.utcnow() + timedelta(days=30)
        version = APIVersion(
            version="v0",
            status=VersionStatus.DEPRECATED,
            sunset_date=future
        )

        days = version.days_until_sunset
        assert days is not None
        assert days >= 29  # 允许测试运行时间差

    def test_days_until_sunset_none(self):
        """测试无下线日期"""
        from services.shared.api_versioning import APIVersion, VersionStatus

        version = APIVersion("v1", VersionStatus.CURRENT)
        assert version.days_until_sunset is None


class TestAPIVersionRegistry:
    """API 版本注册表测试"""

    def test_register_version(self):
        """测试注册版本"""
        from services.shared.api_versioning import APIVersionRegistry, APIVersion, VersionStatus

        registry = APIVersionRegistry()
        version = APIVersion("v1", VersionStatus.CURRENT)

        registry.register(version)

        assert registry.get("v1") is version
        assert registry.get_current() is version

    def test_list_versions(self):
        """测试列出版本"""
        from services.shared.api_versioning import APIVersionRegistry, APIVersion, VersionStatus

        registry = APIVersionRegistry()
        registry.register(APIVersion("v1", VersionStatus.CURRENT))
        registry.register(APIVersion("v2", VersionStatus.BETA))

        versions = registry.list_versions()

        assert len(versions) == 2

    def test_list_versions_excludes_retired(self):
        """测试列出版本排除已下线"""
        from services.shared.api_versioning import APIVersionRegistry, APIVersion, VersionStatus

        registry = APIVersionRegistry()
        registry.register(APIVersion("v1", VersionStatus.CURRENT))
        registry.register(APIVersion("v0", VersionStatus.RETIRED))

        versions = registry.list_versions(include_retired=False)

        assert len(versions) == 1
        assert versions[0].version == "v1"

    def test_is_valid_version(self):
        """测试版本有效性"""
        from services.shared.api_versioning import APIVersionRegistry, APIVersion, VersionStatus

        registry = APIVersionRegistry()
        registry.register(APIVersion("v1", VersionStatus.CURRENT))
        registry.register(APIVersion("v0", VersionStatus.RETIRED))

        assert registry.is_valid_version("v1") is True
        assert registry.is_valid_version("v0") is False
        assert registry.is_valid_version("v999") is False

    def test_deprecate_version(self):
        """测试弃用版本"""
        from services.shared.api_versioning import APIVersionRegistry, APIVersion, VersionStatus

        registry = APIVersionRegistry()
        registry.register(APIVersion("v1", VersionStatus.CURRENT))

        registry.deprecate("v1", sunset_days=60)

        version = registry.get("v1")
        assert version.status == VersionStatus.DEPRECATED
        assert version.deprecation_date is not None
        assert version.sunset_date is not None

    def test_set_and_get_default(self):
        """测试设置和获取默认版本"""
        from services.shared.api_versioning import APIVersionRegistry, APIVersion, VersionStatus

        registry = APIVersionRegistry()
        registry.register(APIVersion("v1", VersionStatus.CURRENT))
        registry.register(APIVersion("v2", VersionStatus.BETA))

        registry.set_default("v2")

        assert registry.get_default() == "v2"


class TestGetVersionRegistry:
    """获取版本注册表测试"""

    def test_get_version_registry_singleton(self):
        """测试版本注册表单例"""
        from services.shared.api_versioning import get_version_registry

        registry1 = get_version_registry()
        registry2 = get_version_registry()

        assert registry1 is registry2

    def test_default_v1_registered(self):
        """测试默认注册 v1"""
        from services.shared.api_versioning import get_version_registry

        registry = get_version_registry()
        v1 = registry.get("v1")

        assert v1 is not None


class TestAPIVersionDecorator:
    """API 版本装饰器测试"""

    def test_api_version_decorator_metadata(self):
        """测试装饰器存储元数据"""
        from services.shared.api_versioning import api_version

        @api_version("v1")
        def my_endpoint():
            return "OK"

        assert my_endpoint._api_version == "v1"
        assert my_endpoint._api_deprecated is False

    def test_api_version_deprecated_metadata(self):
        """测试弃用装饰器元数据"""
        from services.shared.api_versioning import api_version
        from datetime import datetime

        sunset = datetime(2025, 1, 1)

        @api_version("v1", deprecated=True, sunset_date=sunset, alternative="/v2/new")
        def old_endpoint():
            return "OK"

        assert old_endpoint._api_deprecated is True
        assert old_endpoint._api_sunset_date == sunset
        assert old_endpoint._api_alternative == "/v2/new"


class TestRequireAPIVersion:
    """require_api_version 装饰器测试"""

    def test_require_api_version_decorator(self):
        """测试版本要求装饰器"""
        from services.shared.api_versioning import require_api_version

        @require_api_version("v2")
        def new_feature():
            return "OK"

        # 装饰器应该保留函数
        assert callable(new_feature)


class TestVersioningConfig:
    """版本化配置测试"""

    def test_default_config(self):
        """测试默认配置"""
        from services.shared.api_versioning import VersioningConfig

        config = VersioningConfig()

        assert config.default_version == "v1"
        assert "v1" in config.supported_versions
        assert config.allow_version_header is True
        assert config.deprecation_warning_days == 30

    def test_custom_config(self):
        """测试自定义配置"""
        from services.shared.api_versioning import VersioningConfig

        config = VersioningConfig(
            default_version="v2",
            supported_versions=["v1", "v2", "v3"],
            strict_versioning=True
        )

        assert config.default_version == "v2"
        assert len(config.supported_versions) == 3
        assert config.strict_versioning is True


class TestGetRequestVersion:
    """获取请求版本测试"""

    def test_get_request_version_from_path(self):
        """测试从路径获取版本"""
        from services.shared.api_versioning import _get_request_version

        mock_request = MagicMock()
        mock_request.path = '/api/v2/users'
        mock_request.headers.get.return_value = None
        mock_request.args.get.return_value = None

        with patch('services.shared.api_versioning.FLASK_AVAILABLE', True):
            with patch('services.shared.api_versioning.request', mock_request):
                version = _get_request_version()
                assert version == "v2"

    def test_get_request_version_fallback(self):
        """测试版本回退到默认值"""
        from services.shared.api_versioning import _get_request_version

        mock_request = MagicMock()
        mock_request.path = '/health'
        mock_request.headers.get.return_value = None
        mock_request.args.get.return_value = None

        with patch('services.shared.api_versioning.FLASK_AVAILABLE', True):
            with patch('services.shared.api_versioning.request', mock_request):
                version = _get_request_version()
                # 应该返回默认版本
                assert version is not None
