"""
多租户模块单元测试
Sprint 13 & 29: P1 测试覆盖 - 多租户支持与配额强制执行
"""

import pytest
import os
import threading
import time
from unittest.mock import patch, MagicMock


class TestTenantContext:
    """租户上下文测试"""

    def test_get_current_tenant_initial_none(self):
        """测试初始租户 ID 为 None"""
        from services.shared.multitenancy import get_current_tenant, clear_current_tenant

        clear_current_tenant()
        assert get_current_tenant() is None

    def test_set_and_get_tenant(self):
        """测试设置和获取租户 ID"""
        from services.shared.multitenancy import (
            set_current_tenant, get_current_tenant, clear_current_tenant
        )

        set_current_tenant('tenant-123')
        assert get_current_tenant() == 'tenant-123'

        clear_current_tenant()

    def test_clear_tenant(self):
        """测试清除租户 ID"""
        from services.shared.multitenancy import (
            set_current_tenant, get_current_tenant, clear_current_tenant
        )

        set_current_tenant('tenant-123')
        clear_current_tenant()
        assert get_current_tenant() is None

    def test_tenant_context_manager(self):
        """测试租户上下文管理器"""
        from services.shared.multitenancy import (
            tenant_context, get_current_tenant, clear_current_tenant
        )

        clear_current_tenant()

        with tenant_context('tenant-456'):
            assert get_current_tenant() == 'tenant-456'

        assert get_current_tenant() is None

    def test_tenant_context_restores_previous(self):
        """测试上下文管理器恢复之前的租户"""
        from services.shared.multitenancy import (
            tenant_context, get_current_tenant, set_current_tenant, clear_current_tenant
        )

        set_current_tenant('tenant-original')

        with tenant_context('tenant-new'):
            assert get_current_tenant() == 'tenant-new'

        assert get_current_tenant() == 'tenant-original'
        clear_current_tenant()

    def test_tenant_context_thread_isolation(self):
        """测试租户上下文线程隔离"""
        from services.shared.multitenancy import (
            set_current_tenant, get_current_tenant, clear_current_tenant
        )

        results = {}

        def thread_func(tenant_id, key):
            set_current_tenant(tenant_id)
            time.sleep(0.01)  # 小延迟确保并发
            results[key] = get_current_tenant()

        t1 = threading.Thread(target=thread_func, args=('tenant-1', 't1'))
        t2 = threading.Thread(target=thread_func, args=('tenant-2', 't2'))

        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert results['t1'] == 'tenant-1'
        assert results['t2'] == 'tenant-2'


class TestWithTenantDecorator:
    """with_tenant 装饰器测试"""

    def test_with_tenant_sets_context(self):
        """测试装饰器设置租户上下文"""
        from services.shared.multitenancy import (
            with_tenant, get_current_tenant, clear_current_tenant
        )

        @with_tenant('tenant-decorated')
        def my_func():
            return get_current_tenant()

        result = my_func()
        assert result == 'tenant-decorated'

    def test_with_tenant_restores_context(self):
        """测试装饰器恢复上下文"""
        from services.shared.multitenancy import (
            with_tenant, get_current_tenant, set_current_tenant, clear_current_tenant
        )

        set_current_tenant('tenant-original')

        @with_tenant('tenant-decorated')
        def my_func():
            return get_current_tenant()

        my_func()
        assert get_current_tenant() == 'tenant-original'
        clear_current_tenant()


class TestTenantMixin:
    """TenantMixin 测试"""

    def test_mixin_has_tenant_id_column(self):
        """测试 Mixin 有 tenant_id 列"""
        from services.shared.multitenancy import TenantMixin

        assert hasattr(TenantMixin, 'tenant_id')

    def test_set_tenant_method(self):
        """测试 set_tenant 方法"""
        from services.shared.multitenancy import TenantMixin

        class MockModel(TenantMixin):
            pass

        model = MockModel()
        model.set_tenant('tenant-123')
        assert model.tenant_id == 'tenant-123'

    def test_for_tenant_class_method(self):
        """测试 for_tenant 类方法"""
        from services.shared.multitenancy import TenantMixin

        class MockModel(TenantMixin):
            pass

        # for_tenant 返回一个 SQLAlchemy 条件表达式
        condition = MockModel.for_tenant('tenant-123')
        # 验证条件存在
        assert condition is not None


class TestTenantQuery:
    """TenantQuery 测试"""

    def test_filter_by_tenant_with_context(self):
        """测试使用上下文过滤"""
        from services.shared.multitenancy import (
            TenantQuery, set_current_tenant, clear_current_tenant
        )

        set_current_tenant('tenant-123')

        mock_query = MagicMock()
        mock_model = MagicMock()
        mock_model.tenant_id = 'tenant_id_column'

        TenantQuery.filter_by_tenant(mock_query, mock_model)

        mock_query.filter.assert_called_once()
        clear_current_tenant()

    def test_filter_by_tenant_with_explicit_id(self):
        """测试使用显式租户 ID 过滤"""
        from services.shared.multitenancy import TenantQuery, clear_current_tenant

        clear_current_tenant()

        mock_query = MagicMock()
        mock_model = MagicMock()
        mock_model.tenant_id = 'tenant_id_column'

        TenantQuery.filter_by_tenant(mock_query, mock_model, tenant_id='tenant-456')

        mock_query.filter.assert_called_once()

    def test_filter_by_tenant_no_tenant_passthrough(self):
        """测试无租户时直接返回"""
        from services.shared.multitenancy import TenantQuery, clear_current_tenant

        clear_current_tenant()

        mock_query = MagicMock()
        mock_model = MagicMock()
        mock_model.tenant_id = 'tenant_id_column'

        result = TenantQuery.filter_by_tenant(mock_query, mock_model)

        assert result == mock_query


class TestTenantQuota:
    """租户配额测试"""

    def test_default_quotas(self):
        """测试默认配额"""
        from services.shared.multitenancy import TenantQuota

        quota = TenantQuota('tenant-123')

        assert quota.get_quota('workflows') > 0
        assert quota.get_quota('documents') > 0
        assert quota.get_quota('conversations') > 0

    def test_custom_quotas(self):
        """测试自定义配额"""
        from services.shared.multitenancy import TenantQuota

        custom = {'max_workflows': 50, 'max_documents': 500}
        quota = TenantQuota('tenant-123', custom_quotas=custom)

        assert quota.get_quota('workflows') == 50
        assert quota.get_quota('documents') == 500

    def test_check_quota_under_limit(self):
        """测试配额未超限"""
        from services.shared.multitenancy import TenantQuota

        quota = TenantQuota('tenant-123', custom_quotas={'max_workflows': 100})

        assert quota.check_quota('workflows', 50) is True

    def test_check_quota_at_limit(self):
        """测试配额到达限制"""
        from services.shared.multitenancy import TenantQuota

        quota = TenantQuota('tenant-123', custom_quotas={'max_workflows': 100})

        # 已使用 100，不能再增加
        assert quota.check_quota('workflows', 100) is False

    def test_check_quota_over_limit(self):
        """测试配额超限"""
        from services.shared.multitenancy import TenantQuota

        quota = TenantQuota('tenant-123', custom_quotas={'max_workflows': 100})

        assert quota.check_quota('workflows', 150) is False

    def test_get_all_quotas(self):
        """测试获取所有配额"""
        from services.shared.multitenancy import TenantQuota

        quota = TenantQuota('tenant-123')
        all_quotas = quota.get_all_quotas()

        assert 'max_workflows' in all_quotas
        assert 'max_documents' in all_quotas

    def test_invalidate_cache(self):
        """测试缓存失效"""
        from services.shared.multitenancy import TenantQuota

        quota = TenantQuota('tenant-123')
        quota._usage_cache['workflows'] = 50
        quota._cache_timestamps['workflows'] = time.time()

        quota.invalidate_cache('workflows')

        assert 'workflows' not in quota._usage_cache
        assert 'workflows' not in quota._cache_timestamps

    def test_invalidate_all_cache(self):
        """测试清除所有缓存"""
        from services.shared.multitenancy import TenantQuota

        quota = TenantQuota('tenant-123')
        quota._usage_cache = {'a': 1, 'b': 2}
        quota._cache_timestamps = {'a': time.time(), 'b': time.time()}

        quota.invalidate_cache()

        assert len(quota._usage_cache) == 0
        assert len(quota._cache_timestamps) == 0


class TestGetTenantQuota:
    """获取租户配额函数测试"""

    def test_get_tenant_quota_creates_new(self):
        """测试获取新租户配额"""
        from services.shared.multitenancy import get_tenant_quota, _tenant_quotas

        # 清理测试租户
        _tenant_quotas.pop('test-new-tenant', None)

        quota = get_tenant_quota('test-new-tenant')

        assert quota is not None
        assert quota.tenant_id == 'test-new-tenant'

    def test_get_tenant_quota_returns_cached(self):
        """测试获取缓存的租户配额"""
        from services.shared.multitenancy import get_tenant_quota

        quota1 = get_tenant_quota('test-cached-tenant')
        quota2 = get_tenant_quota('test-cached-tenant')

        assert quota1 is quota2


class TestCheckQuotaDecorator:
    """check_quota 装饰器测试"""

    def test_check_quota_passes_under_limit(self):
        """测试配额内通过"""
        from services.shared.multitenancy import (
            check_quota, set_current_tenant, clear_current_tenant, get_tenant_quota
        )

        set_current_tenant('test-quota-tenant')

        @check_quota('workflows')
        def create_workflow():
            return {'id': 'workflow-1'}, 201

        # Mock get_usage to return 0
        quota = get_tenant_quota('test-quota-tenant')
        quota._usage_cache['workflows'] = 0
        quota._cache_timestamps['workflows'] = time.time()

        with patch('flask.g', MagicMock(tenant_id='test-quota-tenant')):
            with patch('flask.jsonify', MagicMock(return_value=MagicMock())):
                result = create_workflow()
                assert result[1] == 201

        clear_current_tenant()

    def test_check_quota_no_tenant_passthrough(self):
        """测试无租户时通过"""
        from services.shared.multitenancy import check_quota, clear_current_tenant

        clear_current_tenant()

        @check_quota('workflows')
        def create_workflow():
            return {'id': 'workflow-1'}, 201

        with patch('flask.g', MagicMock(tenant_id=None)):
            result = create_workflow()
            assert result[1] == 201


class TestEnforceQuota:
    """enforce_quota 函数测试"""

    def test_enforce_quota_passes(self):
        """测试配额检查通过"""
        from services.shared.multitenancy import enforce_quota, get_tenant_quota

        quota = get_tenant_quota('test-enforce-tenant')
        quota._usage_cache['workflows'] = 0
        quota._cache_timestamps['workflows'] = time.time()

        result = enforce_quota('test-enforce-tenant', 'workflows')
        assert result is True

    def test_enforce_quota_raises_on_exceeded(self):
        """测试配额超限抛出异常"""
        from services.shared.multitenancy import (
            enforce_quota, get_tenant_quota, QuotaExceededError
        )

        quota = get_tenant_quota('test-exceed-tenant')
        quota.quotas['max_workflows'] = 10
        quota._usage_cache['workflows'] = 10
        quota._cache_timestamps['workflows'] = time.time()

        with pytest.raises(QuotaExceededError) as exc_info:
            enforce_quota('test-exceed-tenant', 'workflows')

        assert exc_info.value.resource == 'workflows'
        assert exc_info.value.current == 10
        assert exc_info.value.maximum == 10


class TestQuotaExceededError:
    """配额超限异常测试"""

    def test_exception_attributes(self):
        """测试异常属性"""
        from services.shared.multitenancy import QuotaExceededError

        error = QuotaExceededError('workflows', 100, 100)

        assert error.resource == 'workflows'
        assert error.current == 100
        assert error.maximum == 100
        assert 'workflows' in str(error)

    def test_exception_custom_message(self):
        """测试自定义异常消息"""
        from services.shared.multitenancy import QuotaExceededError

        error = QuotaExceededError('workflows', 100, 100, message="Custom message")

        assert error.message == "Custom message"


class TestGetTenantCollectionName:
    """获取租户集合名称测试"""

    def test_with_tenant_context(self):
        """测试使用租户上下文"""
        from services.shared.multitenancy import (
            get_tenant_collection_name, set_current_tenant, clear_current_tenant
        )

        set_current_tenant('tenant-123')

        name = get_tenant_collection_name('documents')

        assert 'documents' in name
        assert 'tenant' in name

        clear_current_tenant()

    def test_with_explicit_tenant(self):
        """测试使用显式租户 ID"""
        from services.shared.multitenancy import get_tenant_collection_name

        name = get_tenant_collection_name('documents', tenant_id='tenant-456')

        assert 'documents' in name
        assert '456' in name

    def test_without_tenant(self):
        """测试无租户返回原名"""
        from services.shared.multitenancy import (
            get_tenant_collection_name, clear_current_tenant
        )

        clear_current_tenant()

        name = get_tenant_collection_name('documents')

        assert name == 'documents'

    def test_sanitizes_tenant_id(self):
        """测试租户 ID 清理"""
        from services.shared.multitenancy import get_tenant_collection_name

        name = get_tenant_collection_name('docs', tenant_id='tenant-with-dashes')

        assert '-' not in name.split('_')[-1]  # 最后部分不应有破折号


class TestTenantMiddleware:
    """租户中间件测试"""

    def test_middleware_initialization(self):
        """测试中间件初始化"""
        from services.shared.multitenancy import TenantMiddleware

        mock_app = MagicMock()
        middleware = TenantMiddleware(mock_app)

        assert mock_app.before_request.called
        assert mock_app.after_request.called

    def test_before_request_extracts_header(self):
        """测试请求前从 Header 提取租户 ID"""
        from services.shared.multitenancy import TenantMiddleware, get_current_tenant

        mock_request = MagicMock()
        mock_request.headers.get.return_value = 'tenant-from-header'
        mock_request.args.get.return_value = None

        mock_g = MagicMock()
        mock_g.jwt_claims = {}

        with patch('flask.request', mock_request):
            with patch('flask.g', mock_g):
                TenantMiddleware.before_request()

                assert get_current_tenant() == 'tenant-from-header'

    def test_after_request_clears_context(self):
        """测试请求后清除上下文"""
        from services.shared.multitenancy import (
            TenantMiddleware, set_current_tenant, get_current_tenant
        )

        set_current_tenant('tenant-123')
        mock_response = MagicMock()

        result = TenantMiddleware.after_request(mock_response)

        assert get_current_tenant() is None
        assert result == mock_response


class TestTenantQuotaUsageSummary:
    """租户配额使用摘要测试"""

    def test_get_usage_summary(self):
        """测试获取使用摘要"""
        from services.shared.multitenancy import TenantQuota

        quota = TenantQuota('test-summary-tenant', custom_quotas={
            'max_workflows': 100,
            'max_documents': 1000
        })

        # Mock usage
        quota._usage_cache = {'workflows': 50, 'documents': 200}
        quota._cache_timestamps = {
            'workflows': time.time(),
            'documents': time.time()
        }

        summary = quota.get_usage_summary()

        assert 'workflows' in summary
        assert summary['workflows']['quota'] == 100
        assert summary['workflows']['used'] == 50
        assert summary['workflows']['remaining'] == 50
        assert summary['workflows']['percentage'] == 50.0
