"""
用户相关测试数据工厂
使用 factory-boy 生成测试数据
"""

import factory
from factory import fuzzy
from datetime import datetime, timedelta
from typing import Dict, Any, List


class DataSourceFactory(factory.Factory):
    """数据源工厂"""
    class Meta:
        model = dict

    source_id = factory.Sequence(lambda n: f"ds_{n:04d}")
    name = factory.Faker('company')
    type = fuzzy.FuzzyChoice(['mysql', 'postgresql', 'oracle', 'mongodb', 'hive'])
    host = factory.Faker('ipv4')
    port = 3306
    database = factory.Faker('word')
    username = factory.Faker('user_name')
    password = factory.Faker('password')
    status = fuzzy.FuzzyChoice(['active', 'inactive', 'error'])
    created_at = factory.LazyFunction(datetime.utcnow)
    updated_at = factory.LazyFunction(datetime.utcnow)
    description = factory.Faker('sentence', locale='zh_CN')

    @classmethod
    def _adjust_kwargs(cls, **kwargs):
        """允许覆盖默认值"""
        return kwargs


class UserFactory(factory.Factory):
    """用户工厂"""
    class Meta:
        model = dict

    user_id = factory.Sequence(lambda n: f"user_{n:04d}")
    username = factory.Faker('user_name')
    email = factory.Faker('email')
    full_name = factory.Faker('name', locale='zh_CN')
    phone = factory.Sequence(lambda n: f"138{n:08d}")
    role = fuzzy.FuzzyChoice([
        'data_administrator',
        'data_engineer',
        'ai_engineer',
        'business_user',
        'system_administrator'
    ])
    status = fuzzy.FuzzyChoice(['active', 'inactive', 'locked'])
    department = factory.Faker('company_suffix', locale='zh_CN')
    created_at = factory.LazyFunction(datetime.utcnow)
    last_login = factory.LazyFunction(lambda: datetime.utcnow() - timedelta(days=1))

    @classmethod
    def with_role(cls, role: str) -> Dict[str, Any]:
        """创建指定角色的用户"""
        return cls(role=role)

    @classmethod
    def data_administrator(cls) -> Dict[str, Any]:
        """创建数据管理员用户"""
        return cls(role='data_administrator')

    @classmethod
    def data_engineer(cls) -> Dict[str, Any]:
        """创建数据工程师用户"""
        return cls(role='data_engineer')

    @classmethod
    def ai_engineer(cls) -> Dict[str, Any]:
        """创建算法工程师用户"""
        return cls(role='ai_engineer')

    @classmethod
    def business_user(cls) -> Dict[str, Any]:
        """创建业务用户"""
        return cls(role='business_user')

    @classmethod
    def system_administrator(cls) -> Dict[str, Any]:
        """创建系统管理员用户"""
        return cls(role='system_administrator')

    @classmethod
    def batch(cls, count: int, role: str = None) -> List[Dict[str, Any]]:
        """批量创建用户"""
        if role:
            return [cls(role=role) for _ in range(count)]
        return [cls() for _ in range(count)]


class MetadataFactory(factory.Factory):
    """元数据工厂"""
    class Meta:
        model = dict

    metadata_id = factory.Sequence(lambda n: f"meta_{n:04d}")
    source_id = factory.SubFactory(DataSourceFactory)
    database_name = factory.Faker('word')
    table_name = factory.Faker('word')
    column_name = factory.Faker('word')
    data_type = fuzzy.FuzzyChoice(['varchar', 'int', 'decimal', 'datetime', 'text'])
    is_primary_key = False
    is_nullable = True
    description = factory.Faker('sentence', locale='zh_CN')
    ai_description = factory.Faker('text', locale='zh_CN')
    tags = factory.LazyFunction(list)
    created_at = factory.LazyFunction(datetime.utcnow)
    version = 1


class DataAssetFactory(factory.Factory):
    """数据资产工厂"""
    class Meta:
        model = dict

    asset_id = factory.Sequence(lambda n: f"asset_{n:04d}")
    name = factory.Faker('sentence', locale='zh_CN')
    type = fuzzy.FuzzyChoice(['table', 'view', 'dataset', 'api', 'file'])
    source_id = factory.SubFactory(DataSourceFactory)
    database_name = factory.Faker('word')
    table_name = factory.Faker('word')
    category = fuzzy.FuzzyChoice([
        '用户数据', '交易数据', '产品数据', '日志数据', '配置数据'
    ])
    description = factory.Faker('text', locale='zh_CN')
    owner = factory.Faker('name', locale='zh_CN')
    department = factory.Faker('company_suffix', locale='zh_CN')
    status = fuzzy.FuzzyChoice(['active', 'deprecated', 'draft'])
    tags = factory.LazyFunction(lambda: ['标签1', '标签2'])
    created_at = factory.LazyFunction(datetime.utcnow)
    updated_at = factory.LazyFunction(datetime.utcnow)

    # 价值评分字段
    usage_score = fuzzy.FuzzyFloat(0, 100)
    business_score = fuzzy.FuzzyFloat(0, 100)
    quality_score = fuzzy.FuzzyFloat(0, 100)
    governance_score = fuzzy.FuzzyFloat(0, 100)
    total_score = fuzzy.FuzzyFloat(0, 100)
    grade = fuzzy.FuzzyChoice(['S', 'A', 'B', 'C'])


class SensitiveDataFactory(factory.Factory):
    """敏感数据工厂"""
    class Meta:
        model = dict

    sensitive_id = factory.Sequence(lambda n: f"sen_{n:04d}")
    source_id = factory.SubFactory(DataSourceFactory)
    database_name = factory.Faker('word')
    table_name = factory.Faker('word')
    column_name = factory.Faker('word')
    sensitive_type = fuzzy.FuzzyChoice([
        'PII', 'FINANCIAL', 'CREDENTIAL', 'OTHER'
    ])
    sub_type = fuzzy.FuzzyChoice([
        'phone', 'id_card', 'bank_card', 'email', 'password'
    ])
    confidence = fuzzy.FuzzyFloat(0.5, 1.0)
    detection_method = fuzzy.FuzzyChoice(['column_name', 'content_sample', 'ai_inference'])
    masking_rule = factory.Faker('word')
    created_at = factory.LazyFunction(datetime.utcnow)


class MaskingRuleFactory(factory.Factory):
    """脱敏规则工厂"""
    class Meta:
        model = dict

    rule_id = factory.Sequence(lambda n: f"mask_rule_{n:04d}")
    rule_name = factory.Faker('sentence', locale='zh_CN')
    column_id = factory.Sequence(lambda n: f"col_{n:04d}")
    strategy = fuzzy.FuzzyChoice([
        'partial_mask', 'hash', 'encrypt', 'nullify', 'fixed_value'
    ])
    format_pattern = fuzzy.FuzzyChoice(['3***4', '6***4', 't***@domain'])
    created_at = factory.LazyFunction(datetime.utcnow)
    created_by = factory.Faker('user_name')


class PermissionFactory(factory.Factory):
    """权限工厂"""
    class Meta:
        model = dict

    permission_id = factory.Sequence(lambda n: f"perm_{n:04d}")
    user_id = factory.SubFactory(UserFactory)
    resource_type = fuzzy.FuzzyChoice(['datasource', 'table', 'column', 'asset'])
    resource_id = factory.Sequence(lambda n: f"res_{n:04d}")
    action = fuzzy.FuzzyChoice(['read', 'write', 'delete', 'admin'])
    granted = True
    created_at = factory.LazyFunction(datetime.utcnow)


class RoleFactory(factory.Factory):
    """角色工厂"""
    class Meta:
        model = dict

    role_id = factory.Sequence(lambda n: f"role_{n:04d}")
    role_name = factory.Faker('sentence', locale='zh_CN')
    role_code = fuzzy.FuzzyChoice([
        'data_administrator', 'data_engineer', 'ai_engineer',
        'business_user', 'system_administrator'
    ])
    description = factory.Faker('text', locale='zh_CN')
    permissions = factory.LazyFunction(list)
    created_at = factory.LazyFunction(datetime.utcnow)


class SystemConfigFactory(factory.Factory):
    """系统配置工厂"""
    class Meta:
        model = dict

    config_id = factory.Sequence(lambda n: f"config_{n:04d}")
    config_key = factory.Faker('word')
    config_value = factory.Faker('sentence')
    config_type = fuzzy.FuzzyChoice(['string', 'int', 'bool', 'json'])
    description = factory.Faker('sentence', locale='zh_CN')
    is_encrypted = False
    created_at = factory.LazyFunction(datetime.utcnow)
    updated_at = factory.LazyFunction(datetime.utcnow)
