"""
ETL 相关测试数据工厂
"""

import factory
from factory import fuzzy
from datetime import datetime, timedelta
from typing import Dict, Any, List


class ETLTaskFactory(factory.Factory):
    """ETL任务工厂"""
    class Meta:
        model = dict

    task_id = factory.Sequence(lambda n: f"etl_{n:04d}")
    task_name = factory.Faker('sentence', locale='zh_CN')
    description = factory.Faker('text', locale='zh_CN')
    source_datasource_id = factory.Sequence(lambda n: f"ds_src_{n:04d}")
    source_tables = factory.LazyFunction(lambda: ['users', 'orders'])
    target_datasource_id = factory.Sequence(lambda n: f"ds_tgt_{n:04d}")
    target_table = factory.Faker('word')
    task_type = fuzzy.FuzzyChoice(['batch', 'streaming', 'scheduled'])
    status = fuzzy.FuzzyChoice(['draft', 'running', 'completed', 'failed', 'paused'])
    schedule = "0 2 * * *"

    # 分析结果
    analysis_result = factory.LazyFunction(dict)

    # Kettle 配置
    kettle_xml = factory.Faker('text')

    # 执行统计
    total_rows = fuzzy.FuzzyInteger(1000, 1000000)
    success_rows = fuzzy.FuzzyInteger(900, 999000)
    failed_rows = fuzzy.FuzzyInteger(0, 1000)
    duration_seconds = fuzzy.FuzzyInteger(60, 3600)

    created_by = factory.Faker('user_name')
    created_at = factory.LazyFunction(datetime.utcnow)
    updated_at = factory.LazyFunction(datetime.utcnow)
    last_executed_at = factory.LazyFunction(lambda: datetime.utcnow() - timedelta(hours=1))


class ETLStepFactory(factory.Factory):
    """ETL步骤工厂"""
    class Meta:
        model = dict

    step_id = factory.Sequence(lambda n: f"step_{n:04d}")
    task_id = factory.Sequence(lambda n: f"etl_{n:04d}")
    step_name = factory.Faker('sentence', locale='zh_CN')
    step_type = fuzzy.FuzzyChoice([
        'input', 'output', 'transform', 'filter',
        'join', 'aggregate', 'cleaning', 'masking'
    ])
    step_order = fuzzy.FuzzyInteger(1, 10)
    config = factory.LazyFunction(dict)
    enabled = True
    created_at = factory.LazyFunction(datetime.utcnow)

    @classmethod
    def cleaning_step(cls) -> Dict[str, Any]:
        """创建清洗步骤"""
        return cls(
            step_type='cleaning',
            config={
                'null_handling': 'remove',
                'deduplicate': True,
                'format_standardization': True,
                'outlier_detection': True
            }
        )

    @classmethod
    def masking_step(cls) -> Dict[str, Any]:
        """创建脱敏步骤"""
        return cls(
            step_type='masking',
            config={
                'columns': ['phone', 'id_card', 'email'],
                'strategy': 'partial_mask'
            }
        )

    @classmethod
    def join_step(cls) -> Dict[str, Any]:
        """创建JOIN步骤"""
        return cls(
            step_type='join',
            config={
                'join_type': 'left',
                'join_keys': ['user_id'],
                'source_tables': ['users', 'orders']
            }
        )


class DataCleaningRuleFactory(factory.Factory):
    """数据清洗规则工厂"""
    class Meta:
        model = dict

    rule_id = factory.Sequence(lambda n: f"clean_rule_{n:04d}")
    rule_name = factory.Faker('sentence', locale='zh_CN')
    rule_type = fuzzy.FuzzyChoice([
        'null_handling', 'deduplication', 'format_standardization',
        'outlier_detection', 'validation'
    ])
    column_name = factory.Faker('word')
    condition = factory.Faker('regex')
    action = fuzzy.FuzzyChoice(['remove', 'replace', 'flag', 'fill_default'])
    default_value = None
    priority = fuzzy.FuzzyInteger(1, 10)
    is_active = True
    created_at = factory.LazyFunction(datetime.utcnow)


class DataCollectionTaskFactory(factory.Factory):
    """数据采集任务工厂"""
    class Meta:
        model = dict

    collection_id = factory.Sequence(lambda n: f"coll_{n:04d}")
    task_name = factory.Faker('sentence', locale='zh_CN')
    description = factory.Faker('text', locale='zh_CN')
    source_type = fuzzy.FuzzyChoice(['database', 'api', 'file', 'log', 'json'])
    source_config = factory.LazyFunction(dict)
    collection_mode = fuzzy.FuzzyChoice(['full', 'incremental', 'realtime'])
    schedule = "0 * * * *"
    status = fuzzy.FuzzyChoice(['pending', 'running', 'completed', 'failed', 'paused'])

    # 增量采集配置
    incremental_column = factory.Faker('word')
    incremental_value = factory.Faker('date')

    # 统计信息
    total_collected = fuzzy.FuzzyInteger(1000, 1000000)
    last_collection_time = factory.LazyFunction(lambda: datetime.utcnow() - timedelta(hours=1))
    next_collection_time = factory.LazyFunction(lambda: datetime.utcnow() + timedelta(hours=1))

    created_by = factory.Faker('user_name')
    created_at = factory.LazyFunction(datetime.utcnow)
    updated_at = factory.LazyFunction(datetime.utcnow)


class ImputationConfigFactory(factory.Factory):
    """缺失值填充配置工厂"""
    class Meta:
        model = dict

    config_id = factory.Sequence(lambda n: f"imp_{n:04d}")
    table_id = factory.Sequence(lambda n: f"tbl_{n:04d}")
    column_name = factory.Faker('word')
    strategy = fuzzy.FuzzyChoice([
        'mean', 'median', 'mode', 'knn', 'forward_fill', 'backward_fill', 'ai_predict'
    ])
    missing_pattern = fuzzy.FuzzyChoice(['random', 'block', 'systematic'])
    null_rate = fuzzy.FuzzyFloat(0, 0.8)
    fill_value = None
    created_at = factory.LazyFunction(datetime.utcnow)


class FusionConfigFactory(factory.Factory):
    """多表融合配置工厂"""
    class Meta:
        model = dict

    fusion_id = factory.Sequence(lambda n: f"fusion_{n:04d}")
    fusion_name = factory.Faker('sentence', locale='zh_CN')
    source_tables = factory.LazyFunction(lambda: ['table_a', 'table_b', 'table_c'])
    join_keys = factory.LazyFunction(lambda: ['user_id'])
    join_type = fuzzy.FuzzyChoice(['inner', 'left', 'right', 'full'])
    quality_threshold = fuzzy.FuzzyFloat(0.5, 1.0)

    # JOIN 质量指标
    match_rate = fuzzy.FuzzyFloat(0.5, 1.0)
    coverage = fuzzy.FuzzyFloat(0.5, 1.0)
    skew_ratio = fuzzy.FuzzyFloat(0, 0.5)
    orphan_rate = fuzzy.FuzzyFloat(0, 0.3)

    status = fuzzy.FuzzyChoice(['draft', 'analyzing', 'ready', 'executing', 'completed'])
    created_by = factory.Faker('user_name')
    created_at = factory.LazyFunction(datetime.utcnow)
