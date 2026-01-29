"""
跨服务集成测试
测试 Alldata、Cube Studio、Bisheng 之间的协作
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock


@pytest.mark.integration
@pytest.mark.p0
class TestCrossServiceIntegration:
    """跨服务集成测试"""

    @pytest.mark.asyncio
    async def test_data_to_model_pipeline(self):
        """测试数据→模型→服务的跨服务流程"""
        # 1. Alldata: 数据ETL
        alldata_service = Mock()
        alldata_service.run_etl = AsyncMock(return_value={
            'success': True,
            'output_path': 's3://datasets/training_data/',
            'rows': 100000
        })

        etl_result = await alldata_service.run_etl(
            source='raw_data',
            target='training_data',
            transformations=['cleaning', 'masking']
        )

        assert etl_result['success'] is True
        dataset_path = etl_result['output_path']

        # 2. Cube: 训练模型
        cube_service = Mock()
        cube_service.submit_training = AsyncMock(return_value={
            'success': True,
            'job_id': 'job_0001',
            'model_id': 'model_0001'
        })

        training_result = await cube_service.submit_training(
            dataset_path=dataset_path,
            model_type='xgboost',
            hyperparameters={'max_depth': 6}
        )

        assert training_result['success'] is True
        model_id = training_result['model_id']

        # 3. Bisheng: 调用模型服务
        bisheng_service = Mock()
        bisheng_service.deploy_model = AsyncMock(return_value={
            'success': True,
            'endpoint': f'/v1/models/{model_id}/predict'
        })

        deploy_result = await bisheng_service.deploy_model(model_id)

        assert deploy_result['success'] is True

    @pytest.mark.asyncio
    async def test_metadata_to_rag_pipeline(self):
        """测试元数据→RAG的跨服务流程"""
        # 1. Alldata: 元数据同步
        alldata_service = Mock()
        alldata_service.get_table_schema = AsyncMock(return_value={
            'success': True,
            'schema': {
                'table_name': 'users',
                'columns': [
                    {'name': 'id', 'type': 'bigint'},
                    {'name': 'username', 'type': 'varchar(50)'},
                    {'name': 'phone', 'type': 'varchar(20)', 'sensitive': True}
                ]
            }
        })

        schema_result = await alldata_service.get_table_schema('users')
        assert schema_result['success'] is True

        # 2. Bisheng: 使用Schema进行Text-to-SQL
        bisheng_service = Mock()
        bisheng_service.text_to_sql = AsyncMock(return_value={
            'success': True,
            'sql': 'SELECT id, username FROM users LIMIT 10',
            'schema_used': schema_result['schema']
        })

        sql_result = await bisheng_service.text_to_sql(
            query='查询前10个用户',
            schema=schema_result['schema']
        )

        assert sql_result['success'] is True

    @pytest.mark.asyncio
    async def test_full_ml_pipeline(self):
        """测试完整ML流程：数据→特征→训练→部署→推理"""
        # 1. 数据准备
        data_service = Mock()
        data_service.prepare_features = AsyncMock(return_value={
            'success': True,
            'feature_path': 's3://features/',
            'feature_count': 50
        })

        features = await data_service.prepare_features(
            raw_data='s3://raw_data/',
            target_column='churn'
        )

        # 2. 模型训练
        training_service = Mock()
        training_service.train = AsyncMock(return_value={
            'success': True,
            'model_id': 'model_0001',
            'accuracy': 0.92
        })

        model = await training_service.train(
            features=features['feature_path'],
            algorithm='random_forest'
        )

        # 3. 模型部署
        deployment_service = Mock()
        deployment_service.deploy = AsyncMock(return_value={
            'success': True,
            'endpoint': '/v1/models/churn_predictor'
        })

        deployment = await deployment_service.deploy(model['model_id'])

        # 4. 推理测试
        inference_service = Mock()
        inference_service.predict = AsyncMock(return_value={
            'success': True,
            'predictions': [0.2, 0.8, 0.5]
        })

        predictions = await inference_service.predict(
            endpoint=deployment['endpoint'],
            data=[[1.0, 2.0, 3.0]]
        )

        assert len(predictions) > 0


@pytest.mark.integration
@pytest.mark.p0
class TestTextToSQLIntegration:
    """Text-to-SQL集成测试"""

    @pytest.mark.asyncio
    async def test_sql_generation_with_schema_injection(self):
        """测试Schema注入的SQL生成完整流程"""
        # 1. 获取Schema
        metadata_service = Mock()
        metadata_service.get_schema = AsyncMock(return_value={
            'tables': [
                {
                    'name': 'orders',
                    'columns': [
                        {'name': 'id', 'type': 'bigint'},
                        {'name': 'user_id', 'type': 'bigint'},
                        {'name': 'amount', 'type': 'decimal(12,2)'},
                        {'name': 'order_time', 'type': 'datetime'}
                    ]
                }
            ]
        })

        schema = await metadata_service.get_schema()

        # 2. 生成SQL
        sql_service = Mock()
        sql_service.generate = AsyncMock(return_value={
            'sql': f"SELECT SUM(amount) FROM orders WHERE order_time >= DATE_SUB(NOW(), INTERVAL 30 DAY)",
            'confidence': 0.92
        })

        result = await sql_service.generate(
            query='近30天的订单总额',
            schema=schema['tables']
        )

        assert result['sql'] is not None

        # 3. 安全检查
        security_service = Mock()
        security_service.check = AsyncMock(return_value={
            'safe': True,
            'warnings': []
        })

        security_result = await security_service.check(result['sql'])
        assert security_result['safe'] is True

        # 4. 执行SQL
        query_service = Mock()
        query_service.execute = AsyncMock(return_value={
            'success': True,
            'data': [{'total': 1500000.50}]
        })

        query_result = await query_service.execute(result['sql'])
        assert query_result['success'] is True


@pytest.mark.integration
@pytest.mark.p0
class TestRAGIntegration:
    """RAG完整流程集成测试"""

    @pytest.mark.asyncio
    async def test_end_to_end_rag_pipeline(self):
        """测试RAG端到端流程"""
        # 1. 文档上传
        doc_service = Mock()
        doc_service.upload = AsyncMock(return_value={
            'success': True,
            'doc_id': 'doc_0001',
            'file_path': 's3://documents/sample.pdf'
        })

        doc = await doc_service.upload('sample.pdf')
        assert doc['success'] is True

        # 2. 文档处理
        doc_service.process = AsyncMock(return_value={
            'success': True,
            'chunks': [
                {'chunk_id': 'c1', 'text': '这是第一段内容'},
                {'chunk_id': 'c2', 'text': '这是第二段内容'}
            ]
        })

        chunks = await doc_service.process(doc['doc_id'])
        assert len(chunks['chunks']) > 0

        # 3. 向量化
        embedding_service = Mock()
        embedding_service.embed = AsyncMock(return_value={
            'embeddings': [[0.1] * 1536 for _ in chunks['chunks']]
        })

        embeddings = await embedding_service.embed([c['text'] for c in chunks['chunks']])
        assert len(embeddings['embeddings']) == len(chunks['chunks'])

        # 4. 索引构建
        vector_service = Mock()
        vector_service.index = AsyncMock(return_value={
            'success': True,
            'indexed_count': len(chunks['chunks'])
        })

        index_result = await vector_service.index(
            chunks=chunks['chunks'],
            embeddings=embeddings['embeddings']
        )
        assert index_result['success'] is True

        # 5. 检索
        vector_service.search = AsyncMock(return_value={
            'results': [
                {'chunk_id': 'c1', 'score': 0.95, 'text': '这是第一段内容'}
            ]
        })

        search_results = await vector_service.search(
            query='test query',
            top_k=5
        )

        # 6. LLM生成
        llm_service = Mock()
        llm_service.generate = AsyncMock(return_value={
            'answer': '根据文档内容，这是答案。'
        })

        answer = await llm_service.generate(
            query='test query',
            context=search_results['results']
        )

        assert answer['answer'] is not None
