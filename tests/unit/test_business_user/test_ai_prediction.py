"""
AI预测分析单元测试
测试用例：BU-AI-001 ~ BU-AI-004
"""

import pytest
from unittest.mock import Mock, AsyncMock


class TestAIPrediction:
    """AI预测分析测试 (BU-AI-001 ~ BU-AI-004)"""

    @pytest.mark.p1
    @pytest.mark.business_user
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_sales_prediction(self, mock_prediction_service):
        """BU-AI-001: 销量预测"""
        prediction_config = {
            'model_id': 'sales_forecast_model',
            'horizon': 30,  # 预测未来30天
            'granularity': 'daily'
        }

        mock_prediction_service.predict_sales = AsyncMock(return_value={
            'success': True,
            'predictions': [
                {'date': '2024-02-01', 'predicted': 15200, 'lower': 14500, 'upper': 15900},
                {'date': '2024-02-02', 'predicted': 14800, 'lower': 14100, 'upper': 15500}
            ],
            'model_info': {
                'model_type': 'Prophet',
                'accuracy': 0.87
            }
        })

        result = await mock_prediction_service.predict_sales(prediction_config)

        assert result['success'] is True
        assert len(result['predictions']) > 0

    @pytest.mark.p1
    @pytest.mark.business_user
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_customer_segmentation(self, mock_prediction_service):
        """BU-AI-002: 客户分群"""
        segmentation_config = {
            'features': ['rfm_score', 'purchase_frequency', 'avg_order_value'],
            'n_clusters': 4,
            'algorithm': 'kmeans'
        }

        mock_prediction_service.segment_customers = AsyncMock(return_value={
            'success': True,
            'segments': [
                {
                    'segment_id': 1,
                    'name': '高价值客户',
                    'count': 5000,
                    'characteristics': {'high_rfm': True, 'frequent_buyer': True}
                },
                {
                    'segment_id': 2,
                    'name': '潜力客户',
                    'count': 8000,
                    'characteristics': {'medium_rfm': True, 'new_customer': True}
                }
            ]
        })

        result = await mock_prediction_service.segment_customers(segmentation_config)

        assert result['success'] is True
        assert len(result['segments']) > 0

    @pytest.mark.p2
    @pytest.mark.business_user
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_user_behavior_prediction(self, mock_prediction_service):
        """BU-AI-003: 用户行为预测"""
        user_id = 'user_0001'

        mock_prediction_service.predict_behavior = AsyncMock(return_value={
            'success': True,
            'user_id': user_id,
            'predictions': {
                'churn_probability': 0.15,
                'next_purchase_probability': 0.72,
                'estimated_lifetime_value': 2500,
                'predicted_next_category': 'electronics'
            }
        })

        result = await mock_prediction_service.predict_behavior(user_id)

        assert result['success'] is True
        assert 0 <= result['predictions']['churn_probability'] <= 1

    @pytest.mark.p1
    @pytest.mark.business_user
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_anomaly_detection(self, mock_prediction_service):
        """BU-AI-004: 异常检测"""
        metric = 'daily_revenue'
        data_points = [10000, 10500, 9800, 10200, 10300, 9500, 10100, 10400, 9900, 3000]

        mock_prediction_service.detect_anomalies = AsyncMock(return_value={
            'success': True,
            'anomalies': [
                {
                    'index': 9,
                    'value': 3000,
                    'expected_range': [9500, 10500],
                    'anomaly_score': 3.5,
                    'type': 'dip'
                }
            ],
            'method': 'isolation_forest'
        })

        result = await mock_prediction_service.detect_anomalies(metric, data_points)

        assert result['success'] is True
        assert len(result['anomalies']) > 0


# ==================== Fixtures ====================

@pytest.fixture
def mock_prediction_service():
    """Mock 预测服务"""
    service = Mock()
    service.predict_sales = AsyncMock()
    service.segment_customers = AsyncMock()
    service.predict_behavior = AsyncMock()
    service.detect_anomalies = AsyncMock()
    return service
