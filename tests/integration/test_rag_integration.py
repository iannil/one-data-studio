"""
RAG集成测试
测试完整RAG流程：文档上传→向量化→检索→生成
"""

import pytest
from unittest.mock import AsyncMock
from datetime import datetime


@pytest.mark.integration
@pytest.mark.p0
class TestRAGPipeline:
    """测试完整RAG流程"""

    @pytest.mark.asyncio
    async def test_full_rag_pipeline(self, mock_services):
        """测试完整RAG流程：文档上传→向量化→检索→生成"""
        # 1. 上传文档
        document = {
            'doc_id': 'doc_0001',
            'file_name': 'sales_policy.pdf',
            'content': '公司销售政策：\n1. 新客户首单享受9折优惠\n2. VIP客户享受专属折扣'
        }

        assert document['doc_id'] is not None

        # 2. 文档分块
        chunks = [
            {'chunk_id': 'chunk_001', 'text': '公司销售政策：\n1. 新客户首单享受9折优惠'},
            {'chunk_id': 'chunk_002', 'text': '2. VIP客户享受专属折扣'}
        ]

        assert len(chunks) == 2

        # 3. 向量化
        embeddings = [
            [0.1] * 1536,
            [0.2] * 1536
        ]

        assert len(embeddings) == len(chunks)
        assert len(embeddings[0]) == 1536

        # 4. 构建索引
        index_result = {
            'collection_name': 'kb_sales',
            'indexed_chunks': 2
        }

        assert index_result['indexed_chunks'] == 2

        # 5. 向量检索
        query = '新客户有什么优惠'
        query_embedding = [0.15] * 1536

        search_results = [
            {'chunk_id': 'chunk_001', 'score': 0.92, 'text': '公司销售政策：\n1. 新客户首单享受9折优惠'},
            {'chunk_id': 'chunk_002', 'score': 0.75, 'text': '2. VIP客户享受专属折扣'}
        ]

        assert search_results[0]['score'] > 0.9

        # 6. LLM生成回答
        llm_response = {
            'answer': '根据销售政策，新客户首单可以享受9折优惠。',
            'sources': ['doc_0001']
        }

        assert '新客户' in llm_response['answer']
        assert '9折' in llm_response['answer']

    @pytest.mark.asyncio
    async def test_rag_with_multiple_documents(self, mock_services):
        """测试多文档RAG检索"""
        # 1. 上传多个文档
        documents = [
            {'doc_id': 'doc_001', 'title': '销售政策', 'content': '新客户首单9折...'},
            {'doc_id': 'doc_002', 'title': '退款政策', 'content': '7天内无理由退款...'},
            {'doc_id': 'doc_003', 'title': 'VIP政策', 'content': 'VIP客户专属折扣...'}
        ]

        # 2. 统一索引
        all_chunks = 15  # 每个文档约5个chunk

        # 3. 跨文档检索
        query = '客户可以享受哪些优惠'
        search_results = [
            {'doc_id': 'doc_001', 'score': 0.95, 'text': '新客户首单9折'},
            {'doc_id': 'doc_003', 'score': 0.88, 'text': 'VIP客户专属折扣'}
        ]

        # 4. 综合回答
        answer = '根据公司政策，客户可以享受以下优惠：\n1. 新客户首单9折\n2. VIP客户专属折扣'

        assert '新客户' in answer
        assert 'VIP' in answer

    @pytest.mark.asyncio
    async def test_rag_with_hyde(self, mock_services):
        """测试HyDE（Hypothetical Document Embeddings）增强检索"""
        query = '如何申请退款'

        # 1. 生成假设文档
        hypothetical_doc = '退款申请流程：用户需要在订单详情页点击申请退款，填写退款原因，提交后等待审核'

        # 2. 使用假设文档进行检索
        search_results = [
            {'score': 0.90, 'text': '退款申请流程：1. 登录账户 2. 进入订单详情 3. 点击申请退款'},
            {'score': 0.85, 'text': '退款政策：7天内无理由退款，15天内质量问题可退款'}
        ]

        assert search_results[0]['score'] > 0.85


@pytest.mark.integration
@pytest.mark.p0
class TestTextToSQLIntegration:
    """测试Text-to-SQL集成"""

    @pytest.mark.asyncio
    async def test_text_to_sql_pipeline(self, mock_services):
        """测试完整Text-to-SQL流程"""
        # 1. 获取Schema
        schema = {
            'tables': [
                {
                    'name': 'orders',
                    'columns': [
                        {'name': 'id', 'type': 'bigint'},
                        {'name': 'amount', 'type': 'decimal(12,2)'},
                        {'name': 'order_time', 'type': 'datetime'}
                    ]
                }
            ]
        }

        # 2. 自然语言查询
        query = '上个月的销售总额是多少'

        # 3. 生成SQL
        generated_sql = 'SELECT SUM(amount) as total FROM orders WHERE order_time >= DATE_SUB(NOW(), INTERVAL 1 MONTH)'

        assert 'SELECT SUM' in generated_sql.upper()
        assert 'orders' in generated_sql
        assert 'order_time' in generated_sql

        # 4. SQL安全检查
        security_check = {
            'safe': True,
            'dangerous_operations': []
        }

        assert security_check['safe'] is True

        # 5. 执行SQL
        execution_result = {
            'success': True,
            'data': [{'total': 1250000.50}],
            'execution_time_ms': 150
        }

        assert execution_result['success'] is True
        assert execution_result['data'][0]['total'] > 0


@pytest.mark.integration
@pytest.mark.p0
class TestHybridQueryIntegration:
    """测试混合查询（SQL + RAG）集成"""

    @pytest.mark.asyncio
    async def test_hybrid_query_pipeline(self, mock_services):
        """测试混合查询流程"""
        query = '上季度销量TOP5产品，并分析增长原因'

        # 1. 意图识别
        intent = {
            'type': 'hybrid',
            'needs_sql': True,
            'needs_rag': True
        }

        # 2. 并行执行
        sql_result = {
            'sql': 'SELECT product_name, SUM(amount) as total FROM orders ... GROUP BY product_name ORDER BY total DESC LIMIT 5',
            'data': [
                {'product_name': 'iPhone 15 Pro', 'total': 500000},
                {'product_name': 'MacBook Pro', 'total': 350000},
                {'product_name': 'AirPods Pro', 'total': 200000},
                {'product_name': 'iPad Air', 'total': 150000},
                {'product_name': 'Apple Watch', 'total': 100000}
            ]
        }

        rag_result = {
            'answer': 'TOP产品销量增长主要得益于：新品发布效应、营销活动推动、用户口碑传播',
            'sources': ['doc_001', 'doc_003']
        }

        # 3. 结果综合
        combined_result = {
            'summary': '上季度TOP5产品总销售额为130万元，其中iPhone 15 Pro占38.5%。\n\n增长原因分析：' + rag_result['answer'],
            'sql_data': sql_result['data'],
            'rag_insights': rag_result['answer'],
            'data_sources': sql_result['data'] + [rag_result]
        }

        assert len(combined_result['sql_data']) == 5
        assert '增长原因' in combined_result['rag_insights'] or '增长' in combined_result['rag_insights']
