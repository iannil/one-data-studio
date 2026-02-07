"""
测试数据生成器 - 基础类和工具函数

提供：
1. BaseGenerator - 所有生成器的基类
2. 工具函数 - ID生成、日期生成、敏感数据生成
3. 常量定义 - 角色类型、数据源类型等
"""

import os
import random
import string
import uuid
import json
import hashlib
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field


# ==================== 常量定义 ====================

class UserRoles:
    """用户角色常量"""
    DATA_ADMINISTRATOR = "data_administrator"
    DATA_ENGINEER = "data_engineer"
    AI_DEVELOPER = "ai_developer"
    DATA_ANALYST = "data_analyst"
    SYSTEM_ADMINISTRATOR = "system_administrator"

    ALL = [DATA_ADMINISTRATOR, DATA_ENGINEER, AI_DEVELOPER, DATA_ANALYST, SYSTEM_ADMINISTRATOR]


class DataSourceTypes:
    """数据源类型常量"""
    MYSQL = "mysql"
    POSTGRESQL = "postgresql"
    ORACLE = "oracle"
    MONGODB = "mongodb"
    HIVE = "hive"
    KAFKA = "kafka"
    REDIS = "redis"
    ELASTICSEARCH = "elasticsearch"

    ALL = [MYSQL, POSTGRESQL, ORACLE, MONGODB, HIVE, KAFKA, REDIS, ELASTICSEARCH]


class SensitivityTypes:
    """敏感数据类型常量"""
    PHONE = "phone"
    ID_CARD = "id_card"
    BANK_CARD = "bank_card"
    EMAIL = "email"
    PASSWORD = "password"
    ADDRESS = "address"
    NAME = "name"

    ALL = [PHONE, ID_CARD, BANK_CARD, EMAIL, PASSWORD, ADDRESS, NAME]


class SensitivityLevels:
    """敏感级别常量"""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"

    ALL = [PUBLIC, INTERNAL, CONFIDENTIAL, RESTRICTED]


class ETLTaskTypes:
    """ETL任务类型常量"""
    SYNC = "sync"
    EXTRACT = "extract"
    LOAD = "load"
    TRANSFORM = "transform"
    ARCHIVE = "archive"

    ALL = [SYNC, EXTRACT, LOAD, TRANSFORM, ARCHIVE]


class ETLStatus:
    """ETL任务状态常量"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    ACTIVE = "active"

    ALL = [PENDING, RUNNING, COMPLETED, FAILED, PAUSED, ACTIVE]


class AssetTypes:
    """数据资产类型常量"""
    TABLE = "table"
    VIEW = "view"
    MATERIALIZED_VIEW = "materialized_view"
    DATASET = "dataset"
    API = "api"
    FILE = "file"
    COLLECTION = "collection"

    ALL = [TABLE, VIEW, MATERIALIZED_VIEW, DATASET, API, FILE, COLLECTION]


class AssetCategories:
    """数据资产分类常量"""
    USER_DATA = "用户数据"
    TRANSACTION_DATA = "交易数据"
    PRODUCT_DATA = "产品数据"
    LOG_DATA = "日志数据"
    BEHAVIOR_DATA = "行为数据"
    FINANCE_DATA = "财务数据"
    OPERATION_DATA = "运营数据"
    RISK_DATA = "风控数据"
    PUBLIC_DATA = "公共数据"
    CONFIG_DATA = "配置数据"

    ALL = [USER_DATA, TRANSACTION_DATA, PRODUCT_DATA, LOG_DATA,
           BEHAVIOR_DATA, FINANCE_DATA, OPERATION_DATA, RISK_DATA,
           PUBLIC_DATA, CONFIG_DATA]


class MLModelTypes:
    """机器学习模型类型常量"""
    CLASSIFICATION = "classification"
    REGRESSION = "regression"
    CLUSTERING = "clustering"
    RECOMMENDATION = "recommendation"
    NLP = "nlp"
    CV = "computer_vision"
    TIME_SERIES = "time_series"

    ALL = [CLASSIFICATION, REGRESSION, CLUSTERING, RECOMMENDATION, NLP, CV, TIME_SERIES]


class BIChartTypes:
    """BI图表类型常量"""
    LINE = "line"
    BAR = "bar"
    PIE = "pie"
    TABLE = "table"
    CARD = "card"
    GAUGE = "gauge"
    FUNNEL = "funnel"
    SCATTER = "scatter"
    HEATMAP = "heatmap"
    MAP = "map"

    ALL = [LINE, BAR, PIE, TABLE, CARD, GAUGE, FUNNEL, SCATTER, HEATMAP, MAP]


# ==================== ID生成函数 ====================

def generate_id(prefix: str = "", length: int = 8) -> str:
    """
    生成带前缀的随机ID

    Args:
        prefix: ID前缀，如 'user_', 'ds_'
        length: 随机部分长度

    Returns:
        格式如: user_abc12345 或 abc1234567890
    """
    random_part = ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))
    if prefix:
        return f"{prefix}{random_part}"
    return random_part


def generate_uuid() -> str:
    """生成UUID字符串"""
    return str(uuid.uuid4())


def generate_short_uuid(prefix: str = "") -> str:
    """生成短UUID（8位）"""
    short_uuid = uuid.uuid4().hex[:8]
    if prefix:
        return f"{prefix}{short_uuid}"
    return short_uuid


# ==================== 日期时间函数 ====================

def random_date(days_ago: int = 30, hours_range: bool = True) -> datetime:
    """
    生成随机日期时间

    Args:
        days_ago: 向前推算的天数
        hours_range: 是否包含小时随机

    Returns:
        随机日期时间对象
    """
    days = random.randint(0, days_ago)
    hours = random.randint(0, 23) if hours_range else 0
    minutes = random.randint(0, 59) if hours_range else 0
    return datetime.now() - timedelta(days=days, hours=hours, minutes=minutes)


def random_date_range(start_days_ago: int = 30, end_days_ago: int = 0) -> datetime:
    """
    生成指定范围内的随机日期

    Args:
        start_days_ago: 起始天数
        end_days_ago: 结束天数

    Returns:
        随机日期时间对象
    """
    days = random.randint(end_days_ago, start_days_ago)
    return datetime.now() - timedelta(days=days, hours=random.randint(0, 23))


def date_range_days(start_date: datetime, end_date: datetime) -> List[datetime]:
    """
    生成日期范围内的所有日期列表

    Args:
        start_date: 起始日期
        end_date: 结束日期

    Returns:
        日期列表
    """
    return [start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1)]


# ==================== 敏感数据生成函数 ====================

def generate_phone() -> str:
    """生成随机手机号（中国）"""
    prefixes = ['130', '131', '132', '133', '134', '135', '136', '137', '138', '139',
                '150', '151', '152', '153', '155', '156', '157', '158', '159',
                '180', '181', '182', '183', '184', '185', '186', '187', '188', '189']
    prefix = random.choice(prefixes)
    suffix = ''.join(random.choices(string.digits, k=8))
    return f"{prefix}{suffix}"


def generate_id_card() -> str:
    """生成随机身份证号（18位）"""
    # 地区码（前6位）
    area_codes = ['110101', '310101', '440301', '500101', '610101']
    area_code = random.choice(area_codes)

    # 出生日期（8位）
    birth_year = random.randint(1970, 2000)
    birth_month = random.randint(1, 12)
    birth_day = random.randint(1, 28)
    birth_date = f"{birth_year}{birth_month:02d}{birth_day:02d}"

    # 顺序码（3位）
    sequence = ''.join(random.choices(string.digits, k=3))

    # 计算校验码
    id_17 = area_code + birth_date + sequence
    weights = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2]
    check_codes = ['1', '0', 'X', '9', '8', '7', '6', '5', '4', '3', '2']

    total = sum(int(id_17[i]) * weights[i] for i in range(17))
    check_code = check_codes[total % 11]

    return id_17 + check_code


def generate_bank_card() -> str:
    """生成随机银行卡号（16-19位）"""
    length = random.choice([16, 19])
    card = ''.join(random.choices(string.digits, k=length))
    # 简单的Luhn算法校验位计算（这里简化处理）
    return card


def generate_email(name: str = None) -> str:
    """
    生成随机邮箱地址

    Args:
        name: 可选的用户名，将用于生成邮箱

    Returns:
        邮箱地址
    """
    domains = ['qq.com', '163.com', 'gmail.com', 'outlook.com', 'company.com', 'test.com']
    if name:
        username = name.lower().replace(' ', '.')
    else:
        username = ''.join(random.choices(string.ascii_lowercase, k=random.randint(5, 10)))
    return f"{username}@{random.choice(domains)}"


def hash_password(password: str) -> str:
    """
    对密码进行SHA256哈希

    Args:
        password: 明文密码

    Returns:
        哈希后的密码
    """
    return hashlib.sha256(password.encode()).hexdigest()


def mask_phone(phone: str) -> str:
    """
    手机号脱敏 (保留前3后4)

    Args:
        phone: 原始手机号

    Returns:
        脱敏后的手机号，如: 138****1234
    """
    if len(phone) >= 11:
        return f"{phone[:3]}****{phone[-4:]}"
    return phone


def mask_id_card(id_card: str) -> str:
    """
    身份证号脱敏 (保留前6后4)

    Args:
        id_card: 原始身份证号

    Returns:
        脱敏后的身份证号，如: 110101****1234
    """
    if len(id_card) >= 18:
        return f"{id_card[:6]}****{id_card[-4:]}"
    return id_card


def mask_bank_card(card: str) -> str:
    """
    银行卡号脱敏 (保留前4后4)

    Args:
        card: 原始银行卡号

    Returns:
        脱敏后的卡号，如: 6222****1234
    """
    if len(card) >= 8:
        return f"{card[:4]}****{card[-4:]}"
    return card


def mask_email(email: str) -> str:
    """
    邮箱脱敏 (只显示首字母和域名)

    Args:
        email: 原始邮箱

    Returns:
        脱敏后的邮箱，如: t***@domain.com
    """
    if '@' in email:
        local, domain = email.split('@', 1)
        if len(local) > 1:
            return f"{local[0]}***@{domain}"
        return f"***@{domain}"
    return email


# ==================== 中文数据生成函数 ====================

def random_chinese_name() -> str:
    """生成随机中文姓名"""
    surnames = ['王', '李', '张', '刘', '陈', '杨', '黄', '赵', '周', '吴',
                '徐', '孙', '马', '朱', '胡', '郭', '何', '高', '林', '罗']
    given_names = ['伟', '芳', '娜', '敏', '静', '丽', '强', '磊', '军', '洋',
                   '勇', '艳', '杰', '娟', '涛', '明', '超', '秀英', '霞', '平']

    surname = random.choice(surnames)
    given = random.choice(given_names)
    if random.random() > 0.3:
        given += random.choice(given_names)

    return f"{surname}{given}"


def random_chinese_company() -> str:
    """生成随机中文公司名"""
    prefixes = ['北京', '上海', '深圳', '广州', '杭州', '成都']
    mids = ['科技', '信息', '数据', '网络', '软件', '互联网', '智能', '云']
    suffixes = ['有限公司', '科技有限公司', '网络技术有限公司', '数据技术有限公司']

    return f"{random.choice(prefixes)}{random.choice(mids)}{random.choice(suffixes)}"


def random_chinese_department() -> str:
    """生成随机中文部门名"""
    departments = [
        '技术部', '数据部', '产品部', '运营部', '市场部', '销售部',
        '财务部', '人力资源部', '风控部', '客服部', '研发部', '测试部'
    ]
    return random.choice(departments)


def random_chinese_description(min_words: int = 5, max_words: int = 15) -> str:
    """生成随机中文描述文本"""
    words = [
        '用户', '数据', '系统', '平台', '服务', '管理', '监控', '分析',
        '统计', '报表', '接口', '配置', '流程', '任务', '作业', '调度',
        '采集', '同步', '计算', '存储', '查询', '检索', '推送', '通知',
        '核心', '主要', '重要', '关键', '基础', '通用', '公共', '业务'
    ]

    count = random.randint(min_words, max_words)
    selected = random.sample(words, min(count, len(words)))
    return ''.join(selected) + '数据'


# ==================== 数据库相关函数 ====================

def random_sql_type() -> str:
    """生成随机SQL数据类型"""
    types = [
        'varchar(255)', 'varchar(500)', 'varchar(50)', 'text',
        'int', 'bigint', 'smallint', 'tinyint',
        'decimal(10,2)', 'decimal(18,2)', 'float', 'double',
        'datetime', 'timestamp', 'date', 'time',
        'boolean', 'bit(1)',
        'json', 'blob'
    ]
    return random.choice(types)


def infer_sensitivity_from_column(column_name: str) -> tuple:
    """
    从列名推断敏感类型

    Args:
        column_name: 列名

    Returns:
        (sensitivity_type, sensitivity_level)
    """
    column_lower = column_name.lower()

    # 手机号检测
    if any(keyword in column_lower for keyword in ['phone', 'mobile', 'tel', '手机', '电话']):
        return SensitivityTypes.PHONE, SensitivityLevels.CONFIDENTIAL

    # 身份证检测
    if any(keyword in column_lower for keyword in ['id_card', 'idcard', 'idcard', 'identity', '身份证']):
        return SensitivityTypes.ID_CARD, SensitivityLevels.RESTRICTED

    # 银行卡检测
    if any(keyword in column_lower for keyword in ['bank_card', 'card_number', 'cardno', '银行卡']):
        return SensitivityTypes.BANK_CARD, SensitivityLevels.RESTRICTED

    # 邮箱检测
    if any(keyword in column_lower for keyword in ['email', 'mail', '邮箱', '邮件']):
        return SensitivityTypes.EMAIL, SensitivityLevels.INTERNAL

    # 密码检测
    if any(keyword in column_lower for keyword in ['password', 'passwd', 'pwd', '密码']):
        return SensitivityTypes.PASSWORD, SensitivityLevels.RESTRICTED

    # 地址检测
    if any(keyword in column_lower for keyword in ['address', 'addr', '地址']):
        return SensitivityTypes.ADDRESS, SensitivityLevels.INTERNAL

    # 姓名检测
    if any(keyword in column_lower for keyword in ['name', 'realname', 'username', '姓名', '用户名']):
        return SensitivityTypes.NAME, SensitivityLevels.INTERNAL

    return None, SensitivityLevels.PUBLIC


# ==================== 配置类 ====================

@dataclass
class GeneratorConfig:
    """生成器配置类"""
    # 用户配置
    users_per_role: int = 5
    admin_count: int = 1

    # 数据源配置
    datasource_count: int = 8
    databases_per_source: int = 2
    tables_per_database: int = 10
    columns_per_table: int = 10

    # ETL配置
    etl_task_count: int = 20
    etl_log_per_task: int = 5

    # 敏感数据配置
    sensitive_scan_task_count: int = 5
    sensitive_results_per_task: int = 15

    # 资产配置
    asset_count: int = 140
    asset_category_count: int = 10

    # 血缘配置
    lineage_edge_count: int = 38

    # ML配置
    ml_model_count: int = 7
    ml_versions_per_model: int = 3
    ml_deployment_count: int = 10

    # 知识库配置
    knowledge_base_count: int = 3
    documents_per_kb: int = 5

    # BI配置
    bi_dashboard_count: int = 3
    bi_charts_per_dashboard: int = 4

    # 预警配置
    alert_rule_count: int = 7
    alert_history_per_rule: int = 10

    # 数据时间范围
    data_days_ago: int = 90

    # 并发配置
    batch_size: int = 100

    # 输出配置
    verbose: bool = True
    dry_run: bool = False


# ==================== 生成器基类 ====================

class BaseGenerator:
    """
    所有生成器的基类

    提供通用方法：
    - 状态追踪和进度报告
    - 数据存储到共享状态
    - 依赖关系管理
    """

    def __init__(self, config: GeneratorConfig = None, storage_manager = None):
        """
        初始化生成器

        Args:
            config: 生成器配置
            storage_manager: 存储管理器实例
        """
        self.config = config or GeneratorConfig()
        self.storage = storage_manager
        self._generated_data: Dict[str, List[Any]] = {}
        self._dependencies: Dict[str, Any] = {}

    def log(self, message: str, level: str = "info"):
        """
        记录日志

        Args:
            message: 日志消息
            level: 日志级别
        """
        # 检查是否应该输出（支持不同的config类型）
        verbose = True
        if hasattr(self.config, 'verbose'):
            verbose = self.config.verbose

        if verbose:
            prefix = {
                'info': '[INFO]',
                'warning': '[WARN]',
                'error': '[ERROR]',
                'success': '[OK]'
            }.get(level, '[INFO]')
            print(f"{prefix} {message}")

    def set_dependency(self, key: str, value: Any):
        """设置依赖数据"""
        self._dependencies[key] = value

    def get_dependency(self, key: str, default: Any = None) -> Any:
        """获取依赖数据"""
        return self._dependencies.get(key, default)

    def store_data(self, key: str, data: Any):
        """存储生成的数据"""
        if key not in self._generated_data:
            self._generated_data[key] = []
        if isinstance(data, list):
            self._generated_data[key].extend(data)
        else:
            self._generated_data[key].append(data)

    def get_data(self, key: str) -> List[Any]:
        """获取生成的数据"""
        return self._generated_data.get(key, [])

    def get_all_data(self) -> Dict[str, List[Any]]:
        """获取所有生成的数据"""
        return self._generated_data

    def random_item(self, items: List[Any]) -> Any:
        """从列表中随机选择一项"""
        return random.choice(items) if items else None

    def random_items(self, items: List[Any], count: int = 1) -> List[Any]:
        """从列表中随机选择多项（可重复）"""
        if not items:
            return []
        return [random.choice(items) for _ in range(count)]

    def random_sample(self, items: List[Any], count: int = 1) -> List[Any]:
        """从列表中随机抽样（不重复）"""
        if not items:
            return []
        count = min(count, len(items))
        return random.sample(items, count)

    def generate(self) -> Dict[str, List[Any]]:
        """
        生成数据的主方法（子类必须实现）

        Returns:
            生成的数据字典
        """
        raise NotImplementedError("Subclasses must implement generate()")

    def save(self):
        """保存生成的数据到存储"""
        if self.storage:
            self.log(f"Saving data for {self.__class__.__name__}...", "info")
            # 子类实现具体的保存逻辑
            self.log(f"Data saved for {self.__class__.__name__}", "success")

    def cleanup(self):
        """清理生成的数据"""
        if self.storage:
            self.log(f"Cleaning up data for {self.__class__.__name__}...", "info")
            # 子类实现具体的清理逻辑


# ==================== 工具函数 ====================

def chunk_list(lst: List[Any], chunk_size: int) -> List[List[Any]]:
    """
    将列表分块

    Args:
        lst: 原始列表
        chunk_size: 块大小

    Returns:
        分块后的列表
    """
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


def merge_dicts(*dicts: Dict[str, Any]) -> Dict[str, Any]:
    """
    合并多个字典

    Args:
        *dicts: 要合并的字典

    Returns:
        合并后的字典
    """
    result = {}
    for d in dicts:
        result.update(d)
    return result


def to_json(data: Any, indent: int = 2) -> str:
    """
    将数据转换为JSON字符串

    Args:
        data: 要转换的数据
        indent: 缩进空格数

    Returns:
        JSON字符串
    """
    def json_serializer(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, (bytes, bytearray)):
            return obj.decode('utf-8')
        raise TypeError(f"Type {type(obj)} not serializable")

    return json.dumps(data, indent=indent, default=json_serializer, ensure_ascii=False)


def get_env_default(key: str, default: Any = None) -> Any:
    """
    获取环境变量，支持类型转换

    Args:
        key: 环境变量名
        default: 默认值

    Returns:
        环境变量值或默认值
    """
    value = os.getenv(key)
    if value is None:
        return default

    # 尝试转换为整数
    if isinstance(default, int):
        try:
            return int(value)
        except ValueError:
            return default

    # 尝试转换为布尔值
    if isinstance(default, bool):
        return value.lower() in ('true', '1', 'yes', 'on')

    return value
