"""
文档和知识库相关测试数据工厂
"""

import factory
from factory import fuzzy
from datetime import datetime, timedelta
from typing import Dict, Any, List


class DocumentFactory(factory.Factory):
    """文档工厂"""
    class Meta:
        model = dict

    doc_id = factory.Sequence(lambda n: f"doc_{n:04d}")
    file_name = factory.Faker('file_name', extension='pdf')
    file_type = fuzzy.FuzzyChoice(['pdf', 'docx', 'txt', 'xlsx', 'jpg', 'png'])
    file_size = fuzzy.FuzzyInteger(1024, 10485760)
    file_path = factory.Faker('file_path')
    title = factory.Faker('sentence', locale='zh_CN')
    content = factory.Faker('text', locale='zh_CN')

    # OCR 结果
    ocr_text = factory.Faker('text', locale='zh_CN')
    ocr_confidence = fuzzy.FuzzyFloat(0.7, 1.0)

    # 关键信息提取
    extracted_info = factory.LazyFunction(dict)

    status = fuzzy.FuzzyChoice(['uploaded', 'processing', 'completed', 'failed'])
    uploaded_by = factory.Faker('user_name')
    uploaded_at = factory.LazyFunction(datetime.utcnow)
    processed_at = factory.LazyFunction(lambda: datetime.utcnow() + timedelta(minutes=5))

    @classmethod
    def contract_doc(cls) -> Dict[str, Any]:
        """创建合同文档"""
        doc = cls(file_type='pdf', title='销售合同')
        doc['extracted_info'] = {
            'party_a': '甲方公司',
            'party_b': '乙方公司',
            'amount': 1000000,
            'start_date': '2024-01-01',
            'end_date': '2024-12-31',
            'contract_type': '销售合同'
        }
        return doc

    @classmethod
    def invoice_doc(cls) -> Dict[str, Any]:
        """创建发票文档"""
        doc = cls(file_type='pdf', title='增值税发票')
        doc['extracted_info'] = {
            'invoice_number': '12345678',
            'invoice_date': '2024-01-15',
            'amount': 50000,
            'tax_amount': 6500,
            'seller': '销售方公司',
            'buyer': '购买方公司'
        }
        return doc


class KnowledgeBaseFactory(factory.Factory):
    """知识库工厂"""
    class Meta:
        model = dict

    kb_id = factory.Sequence(lambda n: f"kb_{n:04d}")
    kb_name = factory.Faker('sentence', locale='zh_CN')
    description = factory.Faker('text', locale='zh_CN')
    kb_type = fuzzy.FuzzyChoice(['general', 'legal', 'technical', 'business'])
    embedding_model = fuzzy.FuzzyChoice(['text-embedding-ada-002', 'bge-large-zh'])
    dimension = fuzzy.FuzzyChoice([768, 1536])

    # 向量索引配置
    index_type = fuzzy.FuzzyChoice(['IVF_FLAT', 'IVF_PQ', 'HNSW'])
    metric_type = fuzzy.FuzzyChoice(['L2', 'IP', 'COSINE'])

    # 统计信息
    document_count = fuzzy.FuzzyInteger(10, 1000)
    chunk_count = fuzzy.FuzzyInteger(100, 10000)

    status = fuzzy.FuzzyChoice(['active', 'inactive', 'indexing'])
    created_by = factory.Faker('user_name')
    created_at = factory.LazyFunction(datetime.utcnow)
    updated_at = factory.LazyFunction(datetime.utcnow)


class IndexedDocumentFactory(factory.Factory):
    """已索引文档工厂"""
    class Meta:
        model = dict

    indexed_id = factory.Sequence(lambda n: f"idx_{n:04d}")
    doc_id = factory.SubFactory(DocumentFactory)
    kb_id = factory.SubFactory(KnowledgeBaseFactory)

    # 分块信息
    chunk_index = fuzzy.FuzzyInteger(0, 100)
    chunk_text = factory.Faker('text', locale='zh_CN')
    chunk_metadata = factory.LazyFunction(dict)

    # 向量信息
    embedding = factory.LazyFunction(lambda: [0.1] * 1536)
    vector_id = factory.Sequence(lambda n: f"vec_{n:04d}")

    # 检索统计
    retrieval_count = fuzzy.FuzzyInteger(0, 1000)
    last_retrieved_at = factory.LazyFunction(lambda: datetime.utcnow() - timedelta(days=1))

    indexed_at = factory.LazyFunction(datetime.utcnow)


class DocumentChunkFactory(factory.Factory):
    """文档分块工厂"""
    class Meta:
        model = dict

    chunk_id = factory.Sequence(lambda n: f"chunk_{n:04d}")
    doc_id = factory.Sequence(lambda n: f"doc_{n:04d}")
    chunk_index = fuzzy.FuzzyInteger(0, 100)
    content = factory.Faker('text', locale='zh_CN')
    metadata = factory.LazyFunction(lambda: {
        'page': fuzzy.FuzzyInteger(1, 50).evaluate(None, None, None),
        'start_pos': fuzzy.FuzzyInteger(0, 1000).evaluate(None, None, None),
        'end_pos': fuzzy.FuzzyInteger(1000, 5000).evaluate(None, None, None),
    })

    # 分块策略
    splitter_type = fuzzy.FuzzyChoice([
        'RecursiveCharacterTextSplitter',
        'CharacterTextSplitter',
        'SemanticSplitter'
    ])
    chunk_size = fuzzy.FuzzyInteger(500, 2000)
    chunk_overlap = fuzzy.FuzzyInteger(50, 200)

    created_at = factory.LazyFunction(datetime.utcnow)


class VectorSearchResultFactory(factory.Factory):
    """向量搜索结果工厂"""
    class Meta:
        model = dict

    chunk_id = factory.Sequence(lambda n: f"chunk_{n:04d}")
    doc_id = factory.Sequence(lambda n: f"doc_{n:04d}")
    content = factory.Faker('text', locale='zh_CN')
    score = fuzzy.FuzzyFloat(0.5, 1.0)
    metadata = factory.LazyFunction(dict)


class RAGQueryFactory(factory.Factory):
    """RAG 查询工厂"""
    class Meta:
        model = dict

    query_id = factory.Sequence(lambda n: f"query_{n:04d}")
    kb_id = factory.Sequence(lambda n: f"kb_{n:04d}")
    query_text = factory.Faker('sentence', locale='zh_CN')
    query_embedding = factory.LazyFunction(lambda: [0.1] * 1536)
    top_k = fuzzy.FuzzyInteger(3, 10)

    # 查询结果
    retrieved_chunks = factory.LazyFunction(list)
    answer = factory.Faker('text', locale='zh_CN')
    sources = factory.LazyFunction(list)

    # 性能指标
    retrieval_time_ms = fuzzy.FuzzyInteger(50, 500)
    generation_time_ms = fuzzy.FuzzyInteger(500, 3000)
    total_time_ms = fuzzy.FuzzyInteger(550, 3500)

    created_by = factory.Faker('user_name')
    created_at = factory.LazyFunction(datetime.utcnow)


class AlertRuleFactory(factory.Factory):
    """预警规则工厂"""
    class Meta:
        model = dict

    rule_id = factory.Sequence(lambda n: f"alert_{n:04d}")
    rule_name = factory.Faker('sentence', locale='zh_CN')
    description = factory.Faker('text', locale='zh_CN')
    metric_name = factory.Faker('word')
    condition_type = fuzzy.FuzzyChoice(['gt', 'lt', 'eq', 'gte', 'lte', 'change_rate'])
    threshold = fuzzy.FuzzyFloat(0, 100)
    time_window = fuzzy.FuzzyInteger(1, 60)
    severity = fuzzy.FuzzyChoice(['info', 'warning', 'critical'])

    # 通知配置
    notification_channels = factory.LazyFunction(lambda: ['email', 'sms', 'in_app'])
    recipients = factory.LazyFunction(lambda: ['user1@example.com', 'user2@example.com'])

    status = fuzzy.FuzzyChoice(['active', 'inactive', 'triggered'])
    created_by = factory.Faker('user_name')
    created_at = factory.LazyFunction(datetime.utcnow)
    updated_at = factory.LazyFunction(datetime.utcnow)


class AlertHistoryFactory(factory.Factory):
    """预警历史工厂"""
    class Meta:
        model = dict

    alert_id = factory.Sequence(lambda n: f"alert_hist_{n:04d}")
    rule_id = factory.Sequence(lambda n: f"alert_{n:04d}")
    metric_value = fuzzy.FuzzyFloat(0, 100)
    threshold_value = fuzzy.FuzzyFloat(0, 100)
    severity = fuzzy.FuzzyChoice(['info', 'warning', 'critical'])
    message = factory.Faker('sentence', locale='zh_CN')

    # 通知状态
    notification_sent = fuzzy.FuzzyChoice([True, False])
    notification_channels = factory.LazyFunction(list)
    notification_status = fuzzy.FuzzyChoice(['pending', 'sent', 'failed'])

    triggered_at = factory.LazyFunction(datetime.utcnow)
    resolved_at = factory.LazyFunction(lambda: datetime.utcnow() + timedelta(minutes=30))
