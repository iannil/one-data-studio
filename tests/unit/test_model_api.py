"""
Model API 单元测试
tests/unit/test_model_api.py

测试模型管理、部署、预测等 API 端点。

注意：此测试需要 model-api 完整环境。如果 import 失败，测试将被跳过。
"""

import os
import sys
import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, Mock
from datetime import datetime

# 确保 model-api 优先于其他 app 模块
_project_root = Path(__file__).parent.parent.parent
_model_api_path = str(_project_root / "services" / "model-api")
if _model_api_path not in sys.path:
    sys.path.insert(0, _model_api_path)

# 设置测试环境
os.environ.setdefault('ENVIRONMENT', 'testing')
os.environ.setdefault('USE_MOCK_INFERENCE', 'true')

# 尝试导入，失败则跳过
try:
    from app import create_app
    _IMPORT_SUCCESS = True
except ImportError as e:
    _IMPORT_SUCCESS = False
    _IMPORT_ERROR = str(e)
    create_app = MagicMock()

# 如果导入失败则跳过所有测试
pytestmark = pytest.mark.skipif(
    not _IMPORT_SUCCESS,
    reason=f"Cannot import model_api module: {_IMPORT_ERROR if not _IMPORT_SUCCESS else ''}"
)


class TestHealthEndpoint:
    """测试健康检查端点"""

    @pytest.fixture
    def app(self):
        """创建测试应用"""
        import importlib.util
        # 显式从 model-api 目录加载 app 模块
        spec = importlib.util.spec_from_file_location(
            "model_app",
            str(_project_root / "services" / "model-api" / "app.py")
        )
        model_app = importlib.util.module_from_spec(spec)
        with patch.dict(os.environ, {'DATABASE_URL': 'sqlite:///:memory:'}):
            spec.loader.exec_module(model_app)
            model_app.app.config['TESTING'] = True
            return model_app.app

    @pytest.fixture
    def client(self, app):
        """创建测试客户端"""
        return app.test_client()

    def test_health_check(self, client):
        """健康检查返回正确状态"""
        with patch('services.model_api.app.get_huggingface_service') as mock_hf:
            mock_hf_service = MagicMock()
            mock_hf_service.token = None
            mock_hf.return_value = mock_hf_service

            response = client.get('/health')

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['status'] == 'ok'
            assert data['service'] == 'model-api'
            assert data['version'] == '1.0.0'

    def test_health_check_v1(self, client):
        """v1 健康检查端点"""
        with patch('services.model_api.app.get_huggingface_service') as mock_hf:
            mock_hf_service = MagicMock()
            mock_hf_service.token = 'test-token'
            mock_hf.return_value = mock_hf_service

            response = client.get('/api/v1/health')

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['huggingface_configured'] is True


class TestModelsCRUD:
    """测试模型 CRUD 操作"""

    @pytest.fixture
    def app(self):
        """创建测试应用"""
        with patch.dict(os.environ, {'DATABASE_URL': 'sqlite:///:memory:'}):
            from app import app
            app.config['TESTING'] = True
            return app

    @pytest.fixture
    def client(self, app):
        """创建测试客户端"""
        return app.test_client()

    @pytest.fixture
    def mock_db(self):
        """Mock 数据库会话"""
        return MagicMock()

    def test_list_models_empty(self, client):
        """列出空模型列表"""
        with patch('services.model_api.app.get_db_session') as mock_get_db:
            mock_db = MagicMock()
            mock_query = MagicMock()
            mock_query.count.return_value = 0
            mock_query.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []
            mock_query.filter.return_value = mock_query
            mock_db.query.return_value = mock_query
            mock_get_db.return_value = mock_db

            response = client.get('/api/v1/models')

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['code'] == 0
            assert data['data']['models'] == []
            assert data['data']['total'] == 0

    def test_list_models_with_filters(self, client):
        """列出带过滤的模型"""
        with patch('services.model_api.app.get_db_session') as mock_get_db:
            mock_db = MagicMock()
            mock_query = MagicMock()
            mock_query.count.return_value = 0
            mock_query.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []
            mock_query.filter.return_value = mock_query
            mock_db.query.return_value = mock_query
            mock_get_db.return_value = mock_db

            response = client.get('/api/v1/models?type=text-generation&status=ready&page=2&page_size=10')

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['data']['page'] == 2
            assert data['data']['page_size'] == 10

    def test_create_model_success(self, client):
        """成功创建模型"""
        with patch('services.model_api.app.get_db_session') as mock_get_db:
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db

            # Mock 模型对象
            mock_model = MagicMock()
            mock_model.to_dict.return_value = {
                'model_id': 'model_test123',
                'name': 'Test Model',
                'status': 'created'
            }

            with patch('services.model_api.app.MLModel', return_value=mock_model):
                response = client.post('/api/v1/models',
                    data=json.dumps({
                        'name': 'Test Model',
                        'description': 'A test model',
                        'model_type': 'text-generation'
                    }),
                    content_type='application/json'
                )

            assert response.status_code == 201
            data = json.loads(response.data)
            assert data['code'] == 0
            assert data['data']['name'] == 'Test Model'

    def test_create_model_missing_name(self, client):
        """缺少名称时创建模型失败"""
        with patch('services.model_api.app.get_db_session') as mock_get_db:
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db

            response = client.post('/api/v1/models',
                data=json.dumps({
                    'description': 'No name provided'
                }),
                content_type='application/json'
            )

            assert response.status_code == 400
            data = json.loads(response.data)
            assert data['code'] == 40001

    def test_get_model_success(self, client):
        """成功获取模型"""
        with patch('services.model_api.app.get_db_session') as mock_get_db:
            mock_db = MagicMock()
            mock_model = MagicMock()
            mock_model.to_dict.return_value = {
                'model_id': 'model_test123',
                'name': 'Test Model'
            }
            mock_db.query.return_value.filter.return_value.first.return_value = mock_model
            mock_get_db.return_value = mock_db

            response = client.get('/api/v1/models/model_test123')

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['data']['model_id'] == 'model_test123'

    def test_get_model_not_found(self, client):
        """模型不存在"""
        with patch('services.model_api.app.get_db_session') as mock_get_db:
            mock_db = MagicMock()
            mock_db.query.return_value.filter.return_value.first.return_value = None
            mock_get_db.return_value = mock_db

            response = client.get('/api/v1/models/nonexistent')

            assert response.status_code == 404
            data = json.loads(response.data)
            assert data['code'] == 40401

    def test_update_model_success(self, client):
        """成功更新模型"""
        with patch('services.model_api.app.get_db_session') as mock_get_db:
            mock_db = MagicMock()
            mock_model = MagicMock()
            mock_model.to_dict.return_value = {
                'model_id': 'model_test123',
                'name': 'Updated Model',
                'status': 'ready'
            }
            mock_db.query.return_value.filter.return_value.first.return_value = mock_model
            mock_get_db.return_value = mock_db

            response = client.put('/api/v1/models/model_test123',
                data=json.dumps({
                    'name': 'Updated Model',
                    'status': 'ready'
                }),
                content_type='application/json'
            )

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['data']['name'] == 'Updated Model'

    def test_delete_model_success(self, client):
        """成功删除模型"""
        with patch('services.model_api.app.get_db_session') as mock_get_db:
            mock_db = MagicMock()
            mock_model = MagicMock()
            mock_db.query.return_value.filter.return_value.first.return_value = mock_model
            mock_db.query.return_value.filter.return_value.count.return_value = 0
            mock_get_db.return_value = mock_db

            response = client.delete('/api/v1/models/model_test123')

            assert response.status_code == 200
            mock_db.delete.assert_called_once_with(mock_model)

    def test_delete_model_with_active_deployment(self, client):
        """有活跃部署时不能删除模型"""
        with patch('services.model_api.app.get_db_session') as mock_get_db:
            mock_db = MagicMock()
            mock_model = MagicMock()

            # 第一个 query 返回模型
            # 第二个 query 返回活跃部署数量
            mock_query = MagicMock()
            mock_query.filter.return_value.first.return_value = mock_model
            mock_query.filter.return_value.count.return_value = 1  # 有活跃部署
            mock_db.query.return_value = mock_query
            mock_get_db.return_value = mock_db

            response = client.delete('/api/v1/models/model_test123')

            assert response.status_code == 400
            data = json.loads(response.data)
            assert data['code'] == 40002


class TestModelDeployment:
    """测试模型部署"""

    @pytest.fixture
    def app(self):
        """创建测试应用"""
        with patch.dict(os.environ, {'DATABASE_URL': 'sqlite:///:memory:'}):
            from app import app
            app.config['TESTING'] = True
            return app

    @pytest.fixture
    def client(self, app):
        """创建测试客户端"""
        return app.test_client()

    def test_list_deployments(self, client):
        """列出部署"""
        with patch('services.model_api.app.get_db_session') as mock_get_db:
            mock_db = MagicMock()
            mock_query = MagicMock()
            mock_query.count.return_value = 0
            mock_query.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []
            mock_query.filter.return_value = mock_query
            mock_db.query.return_value = mock_query
            mock_get_db.return_value = mock_db

            response = client.get('/api/v1/deployments')

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['code'] == 0
            assert 'deployments' in data['data']

    def test_deploy_model_success(self, client):
        """成功部署模型"""
        with patch('services.model_api.app.get_db_session') as mock_get_db:
            mock_db = MagicMock()

            mock_model = MagicMock()
            mock_model.status = 'ready'

            mock_deployment = MagicMock()
            mock_deployment.deployment_id = 'deploy_test123'
            mock_deployment.to_dict.return_value = {
                'deployment_id': 'deploy_test123',
                'status': 'running',
                'endpoint': 'http://example.com/predict'
            }

            mock_db.query.return_value.filter.return_value.first.return_value = mock_model
            mock_get_db.return_value = mock_db

            with patch('services.model_api.app.ModelDeployment', return_value=mock_deployment):
                response = client.post('/api/v1/models/model_test123/deploy',
                    data=json.dumps({
                        'replicas': 2,
                        'gpu_count': 1
                    }),
                    content_type='application/json'
                )

            assert response.status_code == 201
            data = json.loads(response.data)
            assert data['code'] == 0

    def test_deploy_model_not_ready(self, client):
        """模型未就绪时不能部署"""
        with patch('services.model_api.app.get_db_session') as mock_get_db:
            mock_db = MagicMock()
            mock_model = MagicMock()
            mock_model.status = 'created'  # 未就绪

            mock_db.query.return_value.filter.return_value.first.return_value = mock_model
            mock_get_db.return_value = mock_db

            response = client.post('/api/v1/models/model_test123/deploy',
                data=json.dumps({}),
                content_type='application/json'
            )

            assert response.status_code == 400
            data = json.loads(response.data)
            assert data['code'] == 40002

    def test_undeploy_model(self, client):
        """取消部署"""
        with patch('services.model_api.app.get_db_session') as mock_get_db:
            mock_db = MagicMock()

            mock_deployment = MagicMock()
            mock_deployment.model_id = 'model_123'

            mock_model = MagicMock()

            # 设置返回值
            query_mock = MagicMock()
            query_mock.filter.return_value.first.return_value = mock_deployment
            query_mock.filter.return_value.count.return_value = 0

            mock_db.query.return_value = query_mock
            mock_get_db.return_value = mock_db

            response = client.delete('/api/v1/deployments/deploy_test123')

            assert response.status_code == 200


class TestPrediction:
    """测试预测端点"""

    @pytest.fixture
    def app(self):
        """创建测试应用"""
        with patch.dict(os.environ, {
            'DATABASE_URL': 'sqlite:///:memory:',
            'USE_MOCK_INFERENCE': 'true'
        }):
            from app import app
            app.config['TESTING'] = True
            return app

    @pytest.fixture
    def client(self, app):
        """创建测试客户端"""
        return app.test_client()

    def test_predict_mock_text_generation(self, client):
        """Mock 模式文本生成预测"""
        with patch('services.model_api.app.get_db_session') as mock_get_db:
            mock_db = MagicMock()

            mock_deployment = MagicMock()
            mock_deployment.model_id = 'model_123'

            mock_model = MagicMock()
            mock_model.model_type = 'text-generation'
            mock_model.name = 'GPT Test'

            # 模拟查询
            def query_side_effect(cls):
                mock_query = MagicMock()
                if hasattr(cls, 'deployment_id'):
                    mock_query.filter.return_value.first.return_value = mock_deployment
                else:
                    mock_query.filter.return_value.first.return_value = mock_model
                return mock_query

            mock_db.query.side_effect = query_side_effect
            mock_get_db.return_value = mock_db

            response = client.post('/api/v1/predict/deploy_test123',
                data=json.dumps({
                    'input': 'Hello world'
                }),
                content_type='application/json'
            )

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['code'] == 0
            assert data['data']['mock'] is True

    def test_predict_deployment_not_found(self, client):
        """部署不存在时预测失败"""
        with patch('services.model_api.app.get_db_session') as mock_get_db:
            mock_db = MagicMock()
            mock_db.query.return_value.filter.return_value.first.return_value = None
            mock_get_db.return_value = mock_db

            response = client.post('/api/v1/predict/nonexistent',
                data=json.dumps({'input': 'test'}),
                content_type='application/json'
            )

            assert response.status_code == 404


class TestBatchPrediction:
    """测试批量预测"""

    @pytest.fixture
    def app(self):
        """创建测试应用"""
        with patch.dict(os.environ, {'DATABASE_URL': 'sqlite:///:memory:'}):
            from app import app
            app.config['TESTING'] = True
            return app

    @pytest.fixture
    def client(self, app):
        """创建测试客户端"""
        return app.test_client()

    def test_create_batch_prediction(self, client):
        """创建批量预测任务"""
        with patch('services.model_api.app.get_db_session') as mock_get_db:
            mock_db = MagicMock()
            mock_model = MagicMock()
            mock_model.name = 'Test Model'

            mock_job = MagicMock()
            mock_job.to_dict.return_value = {
                'job_id': 'batch_123',
                'status': 'pending'
            }

            mock_db.query.return_value.filter.return_value.first.return_value = mock_model
            mock_get_db.return_value = mock_db

            with patch('services.model_api.app.BatchPredictionJob', return_value=mock_job):
                response = client.post('/api/v1/batch-predictions',
                    data=json.dumps({
                        'model_id': 'model_123',
                        'input_path': 's3://bucket/input.jsonl'
                    }),
                    content_type='application/json'
                )

            assert response.status_code == 201
            data = json.loads(response.data)
            assert data['code'] == 0

    def test_create_batch_prediction_missing_params(self, client):
        """缺少必需参数"""
        with patch('services.model_api.app.get_db_session') as mock_get_db:
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db

            response = client.post('/api/v1/batch-predictions',
                data=json.dumps({
                    'model_id': 'model_123'
                    # 缺少 input_path
                }),
                content_type='application/json'
            )

            assert response.status_code == 400


class TestTrainingJobs:
    """测试训练任务"""

    @pytest.fixture
    def app(self):
        """创建测试应用"""
        with patch.dict(os.environ, {'DATABASE_URL': 'sqlite:///:memory:'}):
            from app import app
            app.config['TESTING'] = True
            return app

    @pytest.fixture
    def client(self, app):
        """创建测试客户端"""
        return app.test_client()

    def test_list_training_jobs(self, client):
        """列出训练任务"""
        with patch('services.model_api.app.get_db_session') as mock_get_db:
            mock_db = MagicMock()
            mock_query = MagicMock()
            mock_query.count.return_value = 0
            mock_query.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []
            mock_query.filter.return_value = mock_query
            mock_db.query.return_value = mock_query
            mock_get_db.return_value = mock_db

            response = client.get('/api/v1/training-jobs')

            assert response.status_code == 200
            data = json.loads(response.data)
            assert 'jobs' in data['data']

    def test_create_training_job(self, client):
        """创建训练任务"""
        with patch('services.model_api.app.get_db_session') as mock_get_db:
            mock_db = MagicMock()

            mock_job = MagicMock()
            mock_job.to_dict.return_value = {
                'job_id': 'train_123',
                'name': 'Training Job',
                'status': 'pending'
            }

            mock_get_db.return_value = mock_db

            with patch('services.model_api.app.TrainingJob', return_value=mock_job):
                response = client.post('/api/v1/training-jobs',
                    data=json.dumps({
                        'name': 'Training Job',
                        'base_model': 'gpt2',
                        'dataset_path': 's3://bucket/dataset'
                    }),
                    content_type='application/json'
                )

            assert response.status_code == 201

    def test_create_training_job_missing_name(self, client):
        """缺少名称"""
        with patch('services.model_api.app.get_db_session') as mock_get_db:
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db

            response = client.post('/api/v1/training-jobs',
                data=json.dumps({}),
                content_type='application/json'
            )

            assert response.status_code == 400

    def test_cancel_training_job(self, client):
        """取消训练任务"""
        with patch('services.model_api.app.get_db_session') as mock_get_db:
            mock_db = MagicMock()
            mock_job = MagicMock()
            mock_job.status = 'running'

            mock_db.query.return_value.filter.return_value.first.return_value = mock_job
            mock_get_db.return_value = mock_db

            response = client.post('/api/v1/training-jobs/train_123/cancel')

            assert response.status_code == 200
            assert mock_job.status == 'cancelled'

    def test_cancel_completed_job_fails(self, client):
        """已完成的任务不能取消"""
        with patch('services.model_api.app.get_db_session') as mock_get_db:
            mock_db = MagicMock()
            mock_job = MagicMock()
            mock_job.status = 'completed'

            mock_db.query.return_value.filter.return_value.first.return_value = mock_job
            mock_get_db.return_value = mock_db

            response = client.post('/api/v1/training-jobs/train_123/cancel')

            assert response.status_code == 400


class TestGenerateId:
    """测试 ID 生成"""

    def test_generate_id_with_prefix(self):
        """带前缀的 ID"""
        from app import generate_id

        id1 = generate_id("model_")
        id2 = generate_id("train_")

        assert id1.startswith("model_")
        assert id2.startswith("train_")
        assert len(id1) == 22  # prefix + 16 hex chars

    def test_generate_id_unique(self):
        """ID 唯一"""
        from app import generate_id

        ids = [generate_id("test_") for _ in range(100)]

        assert len(set(ids)) == 100
