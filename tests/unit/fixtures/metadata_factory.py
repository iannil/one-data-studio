"""
元数据相关测试数据工厂
"""

import factory
from factory import fuzzy
from datetime import datetime, timedelta
from typing import Dict, Any, List


class MetadataDatabaseFactory(factory.Factory):
    """元数据数据库工厂"""
    class Meta:
        model = dict

    database_id = factory.Sequence(lambda n: f"db_{n:04d}")
    source_id = factory.Sequence(lambda n: f"ds_{n:04d}")
    database_name = factory.Faker('word')
    description = factory.Faker('sentence', locale='zh_CN')
    ai_description = factory.Faker('text', locale='zh_CN')
    table_count = fuzzy.FuzzyInteger(10, 100)
    tags = factory.LazyFunction(list)
    created_at = factory.LazyFunction(datetime.utcnow)
    updated_at = factory.LazyFunction(datetime.utcnow)
    version = 1


class MetadataTableFactory(factory.Factory):
    """元数据表工厂"""
    class Meta:
        model = dict

    table_id = factory.Sequence(lambda n: f"tbl_{n:04d}")
    database_id = factory.Sequence(lambda n: f"db_{n:04d}")
    source_id = factory.Sequence(lambda n: f"ds_{n:04d}")
    table_name = factory.Faker('word')
    table_type = fuzzy.FuzzyChoice(['table', 'view', 'materialized_view'])
    row_count = fuzzy.FuzzyInteger(1000, 1000000)
    description = factory.Faker('sentence', locale='zh_CN')
    ai_description = factory.Faker('text', locale='zh_CN')
    engine = fuzzy.FuzzyChoice(['InnoDB', 'MyISAM', 'PostgreSQL'])
    collation = 'utf8mb4_unicode_ci'
    create_time = factory.LazyFunction(lambda: datetime.utcnow() - timedelta(days=365))
    update_time = factory.LazyFunction(datetime.utcnow)
    tags = factory.LazyFunction(lambda: ['用户数据', '核心表'])
    created_at = factory.LazyFunction(datetime.utcnow)
    updated_at = factory.LazyFunction(datetime.utcnow)
    version = 1

    @classmethod
    def with_sensitive_columns(cls) -> Dict[str, Any]:
        """创建包含敏感列的表"""
        table = cls()
        table['columns'] = [
            MetadataColumnFactory(column_name='id', data_type='bigint', is_primary_key=True),
            MetadataColumnFactory(column_name='username', data_type='varchar(50)'),
            MetadataColumnFactory(column_name='phone', data_type='varchar(20)', sensitive_type='PII'),
            MetadataColumnFactory(column_name='id_card', data_type='varchar(20)', sensitive_type='PII'),
            MetadataColumnFactory(column_name='email', data_type='varchar(100)', sensitive_type='PII'),
            MetadataColumnFactory(column_name='created_at', data_type='datetime'),
        ]
        return table

    @classmethod
    def with_null_columns(cls) -> Dict[str, Any]:
        """创建包含空值的表"""
        table = cls()
        table['columns'] = [
            MetadataColumnFactory(column_name='id', data_type='bigint', is_primary_key=True),
            MetadataColumnFactory(column_name='name', data_type='varchar(50)', null_rate=0.1),
            MetadataColumnFactory(column_name='age', data_type='int', null_rate=0.3),
            MetadataColumnFactory(column_name='address', data_type='varchar(200)', null_rate=0.5),
        ]
        return table


class MetadataColumnFactory(factory.Factory):
    """元数据列工厂"""
    class Meta:
        model = dict

    column_id = factory.Sequence(lambda n: f"col_{n:04d}")
    table_id = factory.Sequence(lambda n: f"tbl_{n:04d}")
    database_id = factory.Sequence(lambda n: f"db_{n:04d}")
    column_name = factory.Faker('word')
    data_type = fuzzy.FuzzyChoice([
        'varchar', 'int', 'bigint', 'decimal', 'datetime',
        'text', 'json', 'boolean'
    ])
    is_primary_key = False
    is_nullable = True
    default_value = None
    column_comment = factory.Faker('sentence', locale='zh_CN')
    description = factory.Faker('sentence', locale='zh_CN')
    ai_description = factory.Faker('text', locale='zh_CN')

    # 敏感数据相关
    sensitive_type = None
    sensitivity_level = fuzzy.FuzzyChoice(['public', 'internal', 'confidential', 'restricted'], weights=[50, 30, 15, 5])
    confidence = fuzzy.FuzzyFloat(0, 1)

    # 数据质量相关
    null_rate = fuzzy.FuzzyFloat(0, 0.5)
    distinct_count = fuzzy.FuzzyInteger(10, 10000)
    min_value = None
    max_value = None
    avg_value = None

    created_at = factory.LazyFunction(datetime.utcnow)
    updated_at = factory.LazyFunction(datetime.utcnow)
    version = 1


class MetadataTagFactory(factory.Factory):
    """元数据标签工厂"""
    class Meta:
        model = dict

    tag_id = factory.Sequence(lambda n: f"tag_{n:04d}")
    tag_name = factory.Faker('sentence', locale='zh_CN')
    tag_type = fuzzy.FuzzyChoice(['classification', 'quality', 'security', 'business'])
    tag_color = factory.Faker('hex_color')
    description = factory.Faker('sentence', locale='zh_CN')
    created_at = factory.LazyFunction(datetime.utcnow)


class MetadataVersionFactory(factory.Factory):
    """元数据版本工厂"""
    class Meta:
        model = dict

    version_id = factory.Sequence(lambda n: f"ver_{n:04d}")
    table_id = factory.Sequence(lambda n: f"tbl_{n:04d}")
    version = fuzzy.FuzzyInteger(1, 10)
    snapshot = factory.LazyFunction(dict)
    change_summary = factory.Faker('sentence', locale='zh_CN')
    change_type = fuzzy.FuzzyChoice(['create', 'update', 'delete'])
    created_by = factory.Faker('user_name')
    created_at = factory.LazyFunction(datetime.utcnow)


class LineageEdgeFactory(factory.Factory):
    """血缘边工厂"""
    class Meta:
        model = dict

    edge_id = factory.Sequence(lambda n: f"edge_{n:04d}")
    source_table_id = factory.Sequence(lambda n: f"tbl_src_{n:04d}")
    target_table_id = factory.Sequence(lambda n: f"tbl_tgt_{n:04d}")
    transformation_type = fuzzy.FuzzyChoice(['etl', 'view', 'materialized_view'])
    transformation_sql = factory.Faker('text')
    etl_task_id = factory.Sequence(lambda n: f"etl_{n:04d}")
    created_at = factory.LazyFunction(datetime.utcnow)


class DataStandardFactory(factory.Factory):
    """数据标准工厂"""
    class Meta:
        model = dict

    standard_id = factory.Sequence(lambda n: f"std_{n:04d}")
    standard_name = factory.Faker('sentence', locale='zh_CN')
    standard_code = factory.Faker('ean8')
    domain = fuzzy.FuzzyChoice(['用户数据', '交易数据', '产品数据', '公共数据'])
    description = factory.Faker('text', locale='zh_CN')
    data_type = fuzzy.FuzzyChoice(['varchar', 'int', 'decimal', 'datetime'])
    length = fuzzy.FuzzyInteger(10, 500)
    format_pattern = factory.Faker('regex')
    value_range = None
    enum_values = factory.LazyFunction(list)
    is_mandatory = fuzzy.FuzzyChoice([True, False])
    created_at = factory.LazyFunction(datetime.utcnow)
    created_by = factory.Faker('user_name')
