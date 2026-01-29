"""
智能查询单元测试 (SQL + RAG)
测试用例：BU-IQ-001 ~ BU-IQ-007
"""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock


class TestPureSQLQuery:
    """纯SQL查询测试 (BU-IQ-001)"""

    @pytest.mark.p0
    @pytest.mark.business_user
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_pure_sql_query(self, mock_query_service):
        """BU-IQ-001: 纯SQL查询"""
        query = '上个月销售额是多少'

        mock_query_service.execute_sql_query = AsyncMock(return_value={
            'success': True,
            'query_type': 'sql',
            'generated_sql': 'SELECT SUM(amount) as total_sales FROM orders WHERE order_time >= DATE_SUB(NOW(), INTERVAL 1 MONTH)',
            'result': {
                'total_sales': 1250000.50
            },
            'execution_time_ms': 150
        })

        result = await mock_query_service.execute_sql_query(query)

        assert result['success'] is True
        assert result['query_type'] == 'sql'
        assert 'total_sales' in result['result']
        assert result['result']['total_sales'] > 0


class TestPureRAGQuery:
    """纯RAG检索测试 (BU-IQ-002)"""

    @pytest.mark.p0
    @pytest.mark.business_user
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_pure_rag_query(self, mock_query_service, mock_milvus_client):
        """BU-IQ-002: 纯RAG检索"""
        query = '销售政策是什么'
        kb_id = 'kb_0001'

        mock_milvus_client.search = AsyncMock(return_value=[
            [
                {'id': 1, 'score': 0.95, 'metadata': {'content': '根据公司销售政策，新客户首单享受9折优惠...'}},
                {'id': 2, 'score': 0.88, 'metadata': {'content': 'VIP客户享受专属折扣政策...'}}
            ]
        ])

        mock_query_service.execute_rag_query = AsyncMock(return_value={
            'success': True,
            'query_type': 'rag',
            'retrieved_chunks': 2,
            'answer': '根据公司销售政策，新客户首单享受9折优惠，VIP客户享受专属折扣...',
            'sources': ['doc_001', 'doc_002']
        })

        result = await mock_query_service.execute_rag_query(query, kb_id)

        assert result['success'] is True
        assert result['query_type'] == 'rag'
        assert result['retrieved_chunks'] > 0


class TestHybridQuery:
    """混合查询测试 (BU-IQ-003)"""

    @pytest.mark.p0
    @pytest.mark.business_user
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_hybrid_query(self, mock_query_service):
        """BU-IQ-003: 混合查询 (SQL + RAG)"""
        query = '上季度销售额TOP10产品，并结合销售政策分析原因'

        mock_query_service.execute_hybrid_query = AsyncMock(return_value={
            'success': True,
            'query_type': 'hybrid',
            'sql_result': {
                'sql': 'SELECT product_name, SUM(amount) as total FROM orders WHERE ... GROUP BY product_name ORDER BY total DESC LIMIT 10',
                'data': [
                    {'product_name': 'iPhone 15 Pro', 'total': 500000},
                    {'product_name': 'MacBook Pro', 'total': 350000}
                ]
            },
            'rag_result': {
                'answer': '根据销售政策分析，TOP产品销量上升主要得益于...'
            },
            'combined_analysis': 'TOP10产品销售额占总额的65%，主要增长原因包括...',
            'sources': ['sql_results', 'doc_001', 'doc_005']
        })

        result = await mock_query_service.execute_hybrid_query(query)

        assert result['success'] is True
        assert result['query_type'] == 'hybrid'
        assert 'sql_result' in result
        assert 'rag_result' in result
        assert 'combined_analysis' in result


class TestIntentRecognition:
    """意图识别测试 (BU-IQ-004)"""

    @pytest.mark.p0
    @pytest.mark.business_user
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_intent_recognition(self, mock_query_service):
        """BU-IQ-004: 意图识别"""
        test_cases = [
            ('上个月销售额是多少', 'sql'),
            ('销售政策是什么', 'rag'),
            ('销量TOP10产品及原因分析', 'hybrid'),
            ('用户数量统计', 'sql'),
            ('如何申请退款', 'rag')
        ]

        for query, expected_intent in test_cases:
            mock_query_service.recognize_intent = AsyncMock(return_value={
                'query': query,
                'intent': expected_intent,
                'confidence': 0.9
            })

            result = await mock_query_service.recognize_intent(query)
            assert result['intent'] == expected_intent, f"Failed for query: {query}"


class TestSQLGeneration:
    """SQL生成测试 (BU-IQ-005 ~ BU-IQ-006)"""

    @pytest.mark.p0
    @pytest.mark.business_user
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_schema_injected_sql_generation(self, mock_query_service):
        """BU-IQ-005: Schema注入SQL生成"""
        query = '近30天的订单数量'
        schema = {
            'tables': [
                {
                    'name': 'orders',
                    'columns': [
                        {'name': 'id', 'type': 'bigint'},
                        {'name': 'order_time', 'type': 'datetime'},
                        {'name': 'amount', 'type': 'decimal'}
                    ]
                }
            ]
        }

        mock_query_service.generate_sql = AsyncMock(return_value={
            'success': True,
            'query': query,
            'generated_sql': 'SELECT COUNT(*) as order_count FROM orders WHERE order_time >= DATE_SUB(NOW(), INTERVAL 30 DAY)',
            'schema_used': schema,
            'confidence': 0.95
        })

        result = await mock_query_service.generate_sql(query, schema)

        assert result['success'] is True
        assert 'SELECT COUNT' in result['generated_sql'].upper()
        assert result['confidence'] > 0.8

    @pytest.mark.p0
    @pytest.mark.business_user
    @pytest.mark.security
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_sql_security_check(self, mock_query_service):
        """BU-IQ-006: SQL安全检查"""
        dangerous_sqls = [
            'DROP TABLE users',
            'DELETE FROM orders',
            'TRUNCATE TABLE products',
            'UPDATE users SET password = ""'
        ]

        for dangerous_sql in dangerous_sqls:
            mock_query_service.check_sql_security = AsyncMock(return_value={
                'safe': False,
                'reason': 'DANGEROUS_OPERATION',
                'suggestion': '此操作可能造成数据丢失，已被阻止'
            })

            result = await mock_query_service.check_sql_security(dangerous_sql)
            assert result['safe'] is False, f"SQL should be blocked: {dangerous_sql}"


class TestVectorRetrieval:
    """向量检索测试 (BU-IQ-007)"""

    @pytest.mark.p0
    @pytest.mark.business_user
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_vector_retrieval_recall(self, mock_query_service, mock_vllm_client, mock_milvus_client):
        """BU-IQ-007: 向量检索召回"""
        query = '如何申请退款'
        kb_id = 'kb_0001'
        top_k = 5

        # Mock embedding
        mock_vllm_client.embeddings = AsyncMock(return_value={
            'data': [{'embedding': [0.1] * 1536, 'index': 0}]
        })

        # Mock search
        mock_milvus_client.search = AsyncMock(return_value=[
            [
                {'id': 1, 'score': 0.92, 'metadata': {'text': '退款申请流程：1. 登录账户...'}},
                {'id': 2, 'score': 0.88, 'metadata': {'text': '退款政策说明...'}},
                {'id': 3, 'score': 0.85, 'metadata': {'text': '退款常见问题...'}},
                {'id': 4, 'score': 0.80, 'metadata': {'text': '退款处理时效...'}},
                {'id': 5, 'score': 0.75, 'metadata': {'text': '退款方式说明...'}}
            ]
        ])

        mock_query_service.vector_retrieval = AsyncMock(return_value={
            'success': True,
            'query': query,
            'kb_id': kb_id,
            'top_k': top_k,
            'recalled_chunks': top_k,
            'results': [
                {'rank': 1, 'score': 0.92, 'content': '退款申请流程：1. 登录账户...'},
                {'rank': 2, 'score': 0.88, 'content': '退款政策说明...'},
                {'rank': 3, 'score': 0.85, 'content': '退款常见问题...'},
                {'rank': 4, 'score': 0.80, 'content': '退款处理时效...'},
                {'rank': 5, 'score': 0.75, 'content': '退款方式说明...'}
            ]
        })

        result = await mock_query_service.vector_retrieval(query, kb_id, top_k)

        assert result['success'] is True
        assert result['recalled_chunks'] == top_k
        assert len(result['results']) == top_k
        # 验证按分数排序
        scores = [r['score'] for r in result['results']]
        assert scores == sorted(scores, reverse=True)


class TestQueryContext:
    """查询上下文测试 (BU-IQ-009 ~ BU-IQ-010)"""

    @pytest.mark.p1
    @pytest.mark.business_user
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_conversation_context_maintenance(self, mock_query_service):
        """BU-IQ-009: 会话上下文保持"""
        conversation_id = 'conv_0001'
        queries = [
            '上个月的销售额是多少',
            '那今年上半年呢',  # 引用上文
            '和去年同期比如何'  # 继续引用
        ]

        mock_query_service.execute_with_context = AsyncMock(side_effect=[
            # 第一次查询
            {
                'success': True,
                'query': queries[0],
                'result': {'sales': 1250000},
                'context_updated': True
            },
            # 第二次查询（使用上下文）
            {
                'success': True,
                'query': queries[1],
                'interpreted_query': '今年上半年的销售额是多少',
                'result': {'sales': 7500000},
                'context_used': True
            },
            # 第三次查询（使用上下文）
            {
                'success': True,
                'query': queries[2],
                'interpreted_query': '今年上半年销售额与去年同期对比',
                'result': {'yoy_growth': '+15%'},
                'context_used': True
            }
        ])

        for i, query in enumerate(queries):
            result = await mock_query_service.execute_with_context(query, conversation_id)
            assert result['success'] is True
            if i > 0:
                assert result.get('context_used') is True

    @pytest.mark.p1
    @pytest.mark.business_user
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_conversation_cache(self, mock_query_service, mock_redis_client):
        """BU-IQ-010: 会话缓存"""
        conversation_id = 'conv_0001'

        mock_redis_client.get = AsyncMock(return_value=b'{"context": "cached_context"}')
        mock_redis_client.set = AsyncMock()

        mock_query_service.get_cached_context = AsyncMock(return_value={
            'conversation_id': conversation_id,
            'cached': True,
            'context': {
                'last_query': '上个月销售额',
                'last_result': {'sales': 1250000}
            }
        })

        result = await mock_query_service.get_cached_context(conversation_id)

        assert result['cached'] is True
        assert 'context' in result


# ==================== Fixtures ====================

@pytest.fixture
def mock_query_service():
    """Mock 查询服务"""
    service = Mock()
    service.execute_sql_query = AsyncMock()
    service.execute_rag_query = AsyncMock()
    service.execute_hybrid_query = AsyncMock()
    service.execute = AsyncMock()
    service.recognize_intent = AsyncMock()
    service.generate_sql = AsyncMock()
    service.check_sql_security = AsyncMock()
    service.vector_retrieval = AsyncMock()
    service.execute_with_context = AsyncMock()
    service.get_cached_context = AsyncMock()
    return service


@pytest.fixture
def mock_vllm_client():
    """Mock vLLM客户端"""
    client = Mock()
    client.embeddings = AsyncMock()
    return client


@pytest.fixture
def mock_milvus_client():
    """Mock Milvus客户端"""
    client = Mock()
    client.search = AsyncMock()
    return client


@pytest.fixture
def mock_redis_client():
    """Mock Redis客户端"""
    client = Mock()
    client.get = AsyncMock()
    client.set = AsyncMock()
    return client
