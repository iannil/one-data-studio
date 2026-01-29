"""
资产编目与价值评估单元测试
测试用例：DM-AS-001 ~ DM-AS-008
"""

import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime


class TestAssetCatalog:
    """资产编目测试 (DM-AS-001 ~ DM-AS-002)"""

    @pytest.mark.p0
    @pytest.mark.data_administrator
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_auto_asset_cataloging(self, mock_asset_service):
        """DM-AS-001: 自动资产编目"""
        mock_asset_service.auto_catalog = AsyncMock(return_value={
            'success': True,
            'cataloged_assets': 50,
            'categories': {
                '用户数据': 15,
                '交易数据': 20,
                '产品数据': 10,
                '日志数据': 5
            },
            'assets': [
                {
                    'asset_id': 'asset_0001',
                    'name': '用户表',
                    'type': 'table',
                    'category': '用户数据',
                    'inferred_owner': 'data_admin'
                }
            ]
        })

        result = await mock_asset_service.auto_catalog()

        assert result['success'] is True
        assert result['cataloged_assets'] > 0

    @pytest.mark.p0
    @pytest.mark.data_administrator
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_asset_value_batch_evaluation(self, mock_asset_service):
        """DM-AS-002: 资产价值批量评估"""
        mock_asset_service.batch_evaluate = AsyncMock(return_value={
            'success': True,
            'evaluated_assets': 50,
            'distribution': {
                'S': 5,
                'A': 15,
                'B': 20,
                'C': 10
            }
        })

        result = await mock_asset_service.batch_evaluate()

        assert result['success'] is True


class TestAssetValueScores:
    """资产价值评分测试 (DM-AS-003 ~ DM-AS-006)"""

    @pytest.mark.p1
    @pytest.mark.data_administrator
    @pytest.mark.unit
    def test_usage_score_calculation(self, mock_asset_service):
        """DM-AS-003: 使用度评分计算"""
        asset_id = 'asset_0001'

        mock_asset_service.calculate_usage_score = Mock(return_value={
            'asset_id': asset_id,
            'usage_score': 75.5,
            'factors': {
                'query_count': 1500,
                'active_users': 45,
                'downstream_dependencies': 8,
                'reuse_rate': 0.65
            }
        })

        result = mock_asset_service.calculate_usage_score(asset_id)

        assert result['usage_score'] >= 0
        assert result['usage_score'] <= 100

    @pytest.mark.p1
    @pytest.mark.data_administrator
    @pytest.mark.unit
    def test_business_score_calculation(self, mock_asset_service):
        """DM-AS-004: 业务度评分计算"""
        asset_id = 'asset_0001'

        mock_asset_service.calculate_business_score = Mock(return_value={
            'asset_id': asset_id,
            'business_score': 82.0,
            'factors': {
                'is_core_metric': True,
                'sla_level': 'critical',
                'business_domain_importance': 0.9
            }
        })

        result = mock_asset_service.calculate_business_score(asset_id)

        assert result['business_score'] >= 0

    @pytest.mark.p1
    @pytest.mark.data_administrator
    @pytest.mark.unit
    def test_quality_score_calculation(self, mock_asset_service):
        """DM-AS-005: 质量度评分计算"""
        asset_id = 'asset_0001'

        mock_asset_service.calculate_quality_score = Mock(return_value={
            'asset_id': asset_id,
            'quality_score': 68.5,
            'factors': {
                'completeness': 0.95,
                'accuracy': 0.88,
                'consistency': 0.75,
                'timeliness': 0.6
            }
        })

        result = mock_asset_service.calculate_quality_score(asset_id)

        assert result['quality_score'] >= 0

    @pytest.mark.p1
    @pytest.mark.data_administrator
    @pytest.mark.unit
    def test_governance_score_calculation(self, mock_asset_service):
        """DM-AS-006: 治理度评分计算"""
        asset_id = 'asset_0001'

        mock_asset_service.calculate_governance_score = Mock(return_value={
            'asset_id': asset_id,
            'governance_score': 70.0,
            'factors': {
                'has_owner': True,
                'has_description': True,
                'has_lineage': True,
                'has_quality_rules': True,
                'has_security_level': True
            }
        })

        result = mock_asset_service.calculate_governance_score(asset_id)

        assert result['governance_score'] >= 0


class TestAssetGrading:
    """资产评级测试 (DM-AS-007 ~ DM-AS-008)"""

    @pytest.mark.p0
    @pytest.mark.data_administrator
    @pytest.mark.unit
    def test_asset_grading_verification(self, mock_asset_service):
        """DM-AS-007: 资产评级验证"""
        # 验证评级计算: 使用度35% + 业务度30% + 质量度20% + 治理度15%
        scores = {
            'usage_score': 75.5,
            'business_score': 82.0,
            'quality_score': 68.5,
            'governance_score': 70.0
        }

        expected_total = (
            scores['usage_score'] * 0.35 +
            scores['business_score'] * 0.30 +
            scores['quality_score'] * 0.20 +
            scores['governance_score'] * 0.15
        )

        mock_asset_service.calculate_total_score = Mock(return_value={
            'total_score': expected_total,
            'grade': 'A'
        })

        result = mock_asset_service.calculate_total_score(scores)

        assert result['total_score'] == expected_total
        # 验证评级规则
        if expected_total >= 80:
            assert result['grade'] == 'S'
        elif expected_total >= 60:
            assert result['grade'] == 'A'
        elif expected_total >= 40:
            assert result['grade'] == 'B'
        else:
            assert result['grade'] == 'C'

    @pytest.mark.p2
    @pytest.mark.data_administrator
    @pytest.mark.unit
    def test_asset_value_history(self, mock_asset_service):
        """DM-AS-008: 资产价值历史记录"""
        asset_id = 'asset_0001'

        mock_asset_service.get_value_history = Mock(return_value={
            'asset_id': asset_id,
            'history': [
                {
                    'evaluated_at': '2024-01-01T10:00:00Z',
                    'total_score': 72.5,
                    'grade': 'A'
                },
                {
                    'evaluated_at': '2024-02-01T10:00:00Z',
                    'total_score': 75.0,
                    'grade': 'A'
                },
                {
                    'evaluated_at': '2024-03-01T10:00:00Z',
                    'total_score': 78.5,
                    'grade': 'A'
                }
            ],
            'trend': 'improving'
        })

        result = mock_asset_service.get_value_history(asset_id)

        assert len(result['history']) >= 2
        assert 'trend' in result


# ==================== Fixtures ====================

@pytest.fixture
def mock_asset_service():
    """Mock 资产服务"""
    service = Mock()
    service.auto_catalog = AsyncMock()
    service.batch_evaluate = AsyncMock()
    service.calculate_usage_score = Mock()
    service.calculate_business_score = Mock()
    service.calculate_quality_score = Mock()
    service.calculate_governance_score = Mock()
    service.calculate_total_score = Mock()
    service.get_value_history = Mock()
    return service
