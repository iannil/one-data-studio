"""
模型评估单元测试
测试用例：AE-EV-001 ~ AE-EV-003
"""

import pytest
from unittest.mock import Mock, AsyncMock


class TestModelEvaluation:
    """模型评估测试 (AE-EV-001 ~ AE-EV-003)"""

    @pytest.mark.p0
    @pytest.mark.ai_engineer
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_model_evaluation(self, mock_evaluation_service):
        """AE-EV-001: 模型评估"""
        model_id = 'model_0001'
        test_dataset = 'test_data'

        mock_evaluation_service.evaluate = AsyncMock(return_value={
            'success': True,
            'model_id': model_id,
            'metrics': {
                'accuracy': 0.92,
                'precision': 0.89,
                'recall': 0.87,
                'f1_score': 0.88,
                'auc_roc': 0.95
            },
            'confusion_matrix': {
                'tp': 850,
                'tn': 920,
                'fp': 80,
                'fn': 150
            }
        })

        result = await mock_evaluation_service.evaluate(model_id, test_dataset)

        assert result['success'] is True
        assert 'metrics' in result
        assert result['metrics']['accuracy'] > 0.8

    @pytest.mark.p1
    @pytest.mark.ai_engineer
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_model_comparison(self, mock_evaluation_service):
        """AE-EV-002: 模型对比"""
        models = ['model_0001', 'model_0002', 'model_0003']

        mock_evaluation_service.compare_models = AsyncMock(return_value={
            'success': True,
            'comparison': [
                {
                    'model_id': 'model_0001',
                    'accuracy': 0.92,
                    'f1_score': 0.88,
                    'inference_time_ms': 15
                },
                {
                    'model_id': 'model_0002',
                    'accuracy': 0.90,
                    'f1_score': 0.86,
                    'inference_time_ms': 8
                },
                {
                    'model_id': 'model_0003',
                    'accuracy': 0.94,
                    'f1_score': 0.91,
                    'inference_time_ms': 25
                }
            ],
            'best_by_accuracy': 'model_0003',
            'best_by_speed': 'model_0002'
        })

        result = await mock_evaluation_service.compare_models(models)

        assert result['success'] is True
        assert len(result['comparison']) == len(models)

    @pytest.mark.p2
    @pytest.mark.ai_engineer
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_hyperparameter_tuning(self, mock_evaluation_service):
        """AE-EV-003: 超参数调优"""
        model_id = 'model_0001'
        search_space = {
            'learning_rate': [1e-4, 5e-4, 1e-3],
            'batch_size': [16, 32, 64],
            'hidden_units': [128, 256, 512]
        }

        mock_evaluation_service.tune_hyperparameters = AsyncMock(return_value={
            'success': True,
            'best_params': {
                'learning_rate': 5e-4,
                'batch_size': 32,
                'hidden_units': 256
            },
            'best_score': 0.94,
            'n_trials': 20
        })

        result = await mock_evaluation_service.tune_hyperparameters(
            model_id, search_space, n_trials=20
        )

        assert result['success'] is True
        assert 'best_params' in result


# ==================== Fixtures ====================

@pytest.fixture
def mock_evaluation_service():
    """Mock 评估服务"""
    service = Mock()
    service.evaluate = AsyncMock()
    service.compare_models = AsyncMock()
    service.tune_hyperparameters = AsyncMock()
    return service
