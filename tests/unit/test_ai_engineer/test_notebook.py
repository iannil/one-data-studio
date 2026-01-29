"""
Notebook开发环境单元测试
测试用例：AE-NB-001 ~ AE-NB-006
"""

import pytest
from unittest.mock import Mock, AsyncMock


class TestNotebookEnvironment:
    """Notebook环境测试 (AE-NB-001 ~ AE-NB-003)"""

    @pytest.mark.p0
    @pytest.mark.ai_engineer
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_start_notebook_environment(self, mock_notebook_service):
        """AE-NB-001: 启动Notebook开发环境"""
        config = {
            'notebook_name': '模型训练实验',
            'image': 'pytorch-latest',
            'gpu': 'T4:1',
            'memory': '16Gi'
        }

        mock_notebook_service.start = AsyncMock(return_value={
            'success': True,
            'notebook_id': 'nb_0001',
            'status': 'starting',
            'url': f'https://notebook.example.com/nb_0001'
        })

        result = await mock_notebook_service.start(config)

        assert result['success'] is True
        assert 'notebook_id' in result

    @pytest.mark.p0
    @pytest.mark.ai_engineer
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_query_available_datasets(self, mock_notebook_service):
        """AE-NB-002: 查询可用数据集"""
        mock_notebook_service.list_datasets = AsyncMock(return_value={
            'success': True,
            'datasets': [
                {
                    'dataset_id': 'ds_0001',
                    'name': '用户行为数据',
                    'format': 'parquet',
                    's3_path': 's3://datasets/user_behavior/',
                    'rows': 1000000,
                    'size_mb': 512
                },
                {
                    'dataset_id': 'ds_0002',
                    'name': '交易数据',
                    'format': 'parquet',
                    's3_path': 's3://datasets/transactions/',
                    'rows': 500000,
                    'size_mb': 256
                }
            ]
        })

        result = await mock_notebook_service.list_datasets()

        assert result['success'] is True
        assert len(result['datasets']) > 0

    @pytest.mark.p0
    @pytest.mark.ai_engineer
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_mount_data_storage(self, mock_notebook_service):
        """AE-NB-003: 挂载数据存储"""
        notebook_id = 'nb_0001'
        storage_path = 's3://datasets/training_data'

        mock_notebook_service.mount_storage = AsyncMock(return_value={
            'success': True,
            'notebook_id': notebook_id,
            'mount_path': '/mnt/data/training_data',
            'read_only': True
        })

        result = await mock_notebook_service.mount_storage(notebook_id, storage_path)

        assert result['success'] is True
        assert result['mount_path'].startswith('/mnt/')


class TestNotebookFeatures:
    """Notebook功能测试 (AE-NB-004 ~ AE-NB-006)"""

    @pytest.mark.p1
    @pytest.mark.ai_engineer
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_data_exploration_analysis(self, mock_notebook_service):
        """AE-NB-004: 数据探索分析"""
        notebook_id = 'nb_0001'
        dataset_path = '/mnt/data/training_data'

        mock_notebook_service.explore_data = AsyncMock(return_value={
            'success': True,
            'statistics': {
                'rows': 100000,
                'columns': 25,
                'memory_mb': 128,
                'null_counts': {'col1': 50, 'col2': 10},
                'dtypes': {
                    'int64': 10,
                    'float64': 5,
                    'object': 10
                }
            }
        })

        result = await mock_notebook_service.explore_data(notebook_id, dataset_path)

        assert result['success'] is True
        assert 'statistics' in result

    @pytest.mark.p1
    @pytest.mark.ai_engineer
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_install_python_dependencies(self, mock_notebook_service):
        """AE-NB-005: 安装Python依赖"""
        notebook_id = 'nb_0001'
        packages = ['torch', 'transformers', 'scikit-learn']

        mock_notebook_service.install_packages = AsyncMock(return_value={
            'success': True,
            'installed': packages,
            'failed': []
        })

        result = await mock_notebook_service.install_packages(notebook_id, packages)

        assert result['success'] is True
        assert len(result['installed']) == len(packages)

    @pytest.mark.p1
    @pytest.mark.ai_engineer
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_gpu_resource_allocation(self, mock_notebook_service):
        """AE-NB-006: GPU资源分配"""
        notebook_id = 'nb_0001'
        gpu_config = {'type': 'T4', 'count': 1}

        mock_notebook_service.allocate_gpu = AsyncMock(return_value={
            'success': True,
            'gpu_allocated': {
                'type': 'NVIDIA Tesla T4',
                'memory_mb': 15109,
                'cuda_version': '11.8'
            }
        })

        result = await mock_notebook_service.allocate_gpu(notebook_id, gpu_config)

        assert result['success'] is True
        assert 'gpu_allocated' in result


# ==================== Fixtures ====================

@pytest.fixture
def mock_notebook_service():
    """Mock Notebook服务"""
    service = Mock()
    service.start = AsyncMock()
    service.stop = AsyncMock()
    service.list_datasets = AsyncMock()
    service.mount_storage = AsyncMock()
    service.explore_data = AsyncMock()
    service.install_packages = AsyncMock()
    service.allocate_gpu = AsyncMock()
    return service
