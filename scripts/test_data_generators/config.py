"""
测试数据生成器 - 配置定义

提供：
1. 生成器配置定义
2. 数据库连接配置
3. 敏感数据模式配置
4. 角色权限配置
"""

import os
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from enum import Enum


# ==================== 数据库配置 ====================

@dataclass
class DatabaseConfig:
    """数据库连接配置"""
    host: str = "localhost"
    port: int = 3306
    user: str = "root"
    password: str = ""
    database: str = "onedata"
    charset: str = "utf8mb4"
    pool_size: int = 5
    connect_timeout: int = 10

    @classmethod
    def from_env(cls) -> "DatabaseConfig":
        """从环境变量加载配置"""
        return cls(
            host=os.getenv("MYSQL_HOST", "localhost"),
            port=int(os.getenv("MYSQL_PORT", "3306")),
            user=os.getenv("MYSQL_USER", "root"),
            password=os.getenv("MYSQL_PASSWORD", ""),
            database=os.getenv("MYSQL_DATABASE", "onedata"),
            charset=os.getenv("MYSQL_CHARSET", "utf8mb4"),
        )

    def get_connection_string(self) -> str:
        """获取数据库连接字符串"""
        return f"mysql+pymysql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}?charset={self.charset}"

    def get_pymysql_kwargs(self) -> Dict[str, Any]:
        """获取pymysql连接参数"""
        return {
            "host": self.host,
            "port": self.port,
            "user": self.user,
            "password": self.password,
            "database": self.database,
            "charset": self.charset,
            "connect_timeout": self.connect_timeout,
        }


@dataclass
class RedisConfig:
    """Redis连接配置"""
    host: str = "localhost"
    port: int = 6379
    password: str = ""
    db: int = 0
    decode_responses: bool = True

    @classmethod
    def from_env(cls) -> "RedisConfig":
        """从环境变量加载配置"""
        return cls(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            password=os.getenv("REDIS_PASSWORD", ""),
            db=int(os.getenv("REDIS_DB", "0")),
        )


@dataclass
class MinIOConfig:
    """MinIO配置"""
    endpoint: str = "localhost:9000"
    access_key: str = "minioadmin"
    secret_key: str = "minioadmin"
    secure: bool = False
    bucket: str = "test-data"

    @classmethod
    def from_env(cls) -> "MinIOConfig":
        """从环境变量加载配置"""
        return cls(
            endpoint=os.getenv("MINIO_ENDPOINT", "localhost:9000"),
            access_key=os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
            secret_key=os.getenv("MINIO_SECRET_KEY", "minioadmin"),
            secure=os.getenv("MINIO_SECURE", "false").lower() == "true",
            bucket=os.getenv("MINIO_BUCKET", "test-data"),
        )


@dataclass
class MilvusConfig:
    """Milvus向量数据库配置"""
    host: str = "localhost"
    port: int = 19530
    user: str = ""
    password: str = ""

    @classmethod
    def from_env(cls) -> "MilvusConfig":
        """从环境变量加载配置"""
        return cls(
            host=os.getenv("MILVUS_HOST", "localhost"),
            port=int(os.getenv("MILVUS_PORT", "19530")),
            user=os.getenv("MILVUS_USER", ""),
            password=os.getenv("MILVUS_PASSWORD", ""),
        )


# ==================== 敏感数据模式配置 ====================

@dataclass
class SensitivePattern:
    """敏感数据模式定义"""
    name: str
    description: str
    column_patterns: List[str]
    sample_values: List[str]
    sensitivity_level: str
    mask_function: str
    weight: float = 1.0


SENSITIVE_PATTERNS: Dict[str, SensitivePattern] = {
    "phone": SensitivePattern(
        name="phone",
        description="手机号码",
        column_patterns=["phone", "mobile", "tel", "手机", "电话", "联系电话", "手机号"],
        sample_values=["13812345678", "15987654321", "18612345678"],
        sensitivity_level="confidential",
        mask_function="partial_mask",
        weight=1.0
    ),
    "id_card": SensitivePattern(
        name="id_card",
        description="身份证号",
        column_patterns=["id_card", "idcard", "identity", "身份证", "证件号"],
        sample_values=["110101199001011234", "310101198501011234"],
        sensitivity_level="restricted",
        mask_function="partial_mask",
        weight=1.0
    ),
    "bank_card": SensitivePattern(
        name="bank_card",
        description="银行卡号",
        column_patterns=["bank_card", "card_number", "cardno", "银行卡", "卡号"],
        sample_values=["6222021234567890123", "6228481234567890123"],
        sensitivity_level="restricted",
        mask_function="partial_mask",
        weight=1.0
    ),
    "email": SensitivePattern(
        name="email",
        description="电子邮箱",
        column_patterns=["email", "mail", "邮箱", "邮件", "电子邮箱"],
        sample_values=["user@example.com", "test@company.com"],
        sensitivity_level="internal",
        mask_function="partial_mask",
        weight=1.0
    ),
    "password": SensitivePattern(
        name="password",
        description="密码",
        column_patterns=["password", "passwd", "pwd", "密码"],
        sample_values=["password123", "admin123"],
        sensitivity_level="restricted",
        mask_function="hash",
        weight=1.0
    ),
    "address": SensitivePattern(
        name="address",
        description="地址",
        column_patterns=["address", "addr", "地址", "住址"],
        sample_values=["北京市朝阳区某某街道123号", "上海市浦东新区某某路456号"],
        sensitivity_level="internal",
        mask_function="partial_mask",
        weight=0.5
    ),
    "name": SensitivePattern(
        name="name",
        description="姓名",
        column_patterns=["name", "realname", "true_name", "姓名", "真实姓名"],
        sample_values=["张三", "李四", "王五"],
        sensitivity_level="internal",
        mask_function="partial_mask",
        weight=0.3
    ),
}


def get_sensitive_pattern(column_name: str) -> Optional[SensitivePattern]:
    """
    根据列名获取敏感数据模式

    Args:
        column_name: 列名

    Returns:
        匹配的敏感数据模式，如果不匹配则返回None
    """
    column_lower = column_name.lower()

    for pattern in SENSITIVE_PATTERNS.values():
        for pattern_str in pattern.column_patterns:
            if pattern_str.lower() in column_lower:
                return pattern

    return None


# ==================== 角色权限配置 ====================

@dataclass
class RolePermission:
    """角色权限定义"""
    role_code: str
    role_name: str
    description: str
    permissions: List[str] = field(default_factory=list)


ROLE_PERMISSIONS: Dict[str, RolePermission] = {
    "data_administrator": RolePermission(
        role_code="data_administrator",
        role_name="数据管理员",
        description="负责数据治理、元数据管理、数据质量管理",
        permissions=[
            # 数据源管理
            "datasource:create", "datasource:read", "datasource:update", "datasource:delete",
            # 元数据管理
            "metadata:read", "metadata:update", "metadata:delete",
            # 敏感数据管理
            "sensitive:read", "sensitive:update", "sensitive:scan", "sensitive:mask",
            # 脱敏规则管理
            "masking_rule:create", "masking_rule:read", "masking_rule:update", "masking_rule:delete",
            # 数据资产管理
            "asset:create", "asset:read", "asset:update", "asset:delete", "asset:approve",
            # 数据血缘管理
            "lineage:read", "lineage:update",
            # 质量规则管理
            "quality_rule:create", "quality_rule:read", "quality_rule:update", "quality_rule:delete",
            # 数据标准管理
            "standard:create", "standard:read", "standard:update", "standard:delete",
        ]
    ),
    "data_engineer": RolePermission(
        role_code="data_engineer",
        role_name="数据工程师",
        description="负责ETL任务开发、数据管道建设",
        permissions=[
            # 数据源管理（只读）
            "datasource:read",
            # 元数据管理（只读）
            "metadata:read",
            # ETL任务管理
            "etl:create", "etl:read", "etl:update", "etl:delete", "etl:execute", "etl:monitor",
            # 工作流管理
            "workflow:create", "workflow:read", "workflow:update", "workflow:delete", "workflow:execute",
            # 数据资产管理（只读）
            "asset:read",
            # 数据血缘（只读）
            "lineage:read",
            # 质量规则（执行）
            "quality_rule:read", "quality_rule:execute",
        ]
    ),
    "ai_developer": RolePermission(
        role_code="ai_developer",
        role_name="AI开发者",
        description="负责模型训练、模型部署、知识库管理",
        permissions=[
            # 数据源管理（只读）
            "datasource:read",
            # 元数据管理（只读）
            "metadata:read",
            # 数据集管理
            "dataset:create", "dataset:read", "dataset:update", "dataset:delete",
            # 模型管理
            "model:create", "model:read", "model:update", "model:delete", "model:train", "model:deploy",
            # 知识库管理
            "knowledge_base:create", "knowledge_base:read", "knowledge_base:update", "knowledge_base:delete",
            "document:create", "document:read", "document:update", "document:delete",
            # 向量管理
            "vector:create", "vector:read", "vector:delete",
            # Notebook管理
            "notebook:create", "notebook:read", "notebook:update", "notebook:delete", "notebook:execute",
            # 特征管理
            "feature:create", "feature:read", "feature:update", "feature:delete",
        ]
    ),
    "data_analyst": RolePermission(
        role_code="data_analyst",
        role_name="数据分析师",
        description="负责数据分析、BI报表制作",
        permissions=[
            # 数据源管理（只读）
            "datasource:read",
            # 元数据管理（只读）
            "metadata:read",
            # 数据资产管理（只读）
            "asset:read",
            # BI报表管理
            "dashboard:create", "dashboard:read", "dashboard:update", "dashboard:delete",
            "chart:create", "chart:read", "chart:update", "chart:delete",
            # 查询管理
            "query:create", "query:read", "query:execute",
            # 数据导出
            "data:export",
            # 知识库（只读）
            "knowledge_base:read", "document:read",
            # 质量规则（只读）
            "quality_rule:read",
        ]
    ),
    "system_administrator": RolePermission(
        role_code="system_administrator",
        role_name="系统管理员",
        description="负责系统配置、用户管理、权限管理",
        permissions=[
            # 用户管理
            "user:create", "user:read", "user:update", "user:delete",
            # 角色管理
            "role:create", "role:read", "role:update", "role:delete",
            # 权限管理
            "permission:read", "permission:grant", "permission:revoke",
            # 系统配置
            "config:read", "config:update",
            # 数据源管理（全部）
            "datasource:create", "datasource:read", "datasource:update", "datasource:delete",
            # 日志管理
            "log:read", "log:export",
            # 监控管理
            "monitor:read",
            # 告警管理
            "alert:read", "alert:update", "alert:delete",
            # 所有只读权限
            "metadata:read", "etl:read", "asset:read", "lineage:read",
            "model:read", "knowledge_base:read", "dashboard:read",
        ]
    ),
}


def get_permissions_for_role(role_code: str) -> List[str]:
    """
    获取角色的权限列表

    Args:
        role_code: 角色代码

    Returns:
        权限列表
    """
    role = ROLE_PERMISSIONS.get(role_code)
    return role.permissions if role else []


def get_all_permissions() -> List[str]:
    """获取所有唯一权限"""
    permissions = set()
    for role in ROLE_PERMISSIONS.values():
        permissions.update(role.permissions)
    return sorted(list(permissions))


# ==================== 表名和列名模式 ====================

# 用户相关表名模式
USER_TABLE_PATTERNS = [
    "users", "user", "t_user", "tb_user", "sys_user",
    "members", "member", "accounts", "account",
    "用户", "用户表", "会员", "会员表"
]

# 订单相关表名模式
ORDER_TABLE_PATTERNS = [
    "orders", "order", "t_order", "tb_order",
    "order_items", "order_detail", "order_details",
    "订单", "订单表", "订单明细"
]

# 产品相关表名模式
PRODUCT_TABLE_PATTERNS = [
    "products", "product", "t_product", "tb_product",
    "goods", "goods_info", "items", "catalog",
    "产品", "产品表", "商品", "商品表"
]

# 交易相关表名模式
TRANSACTION_TABLE_PATTERNS = [
    "transactions", "transaction", "trans",
    "payments", "payment", "trade", "trades",
    "交易", "交易表", "支付", "支付表"
]

# 日志相关表名模式
LOG_TABLE_PATTERNS = [
    "logs", "log", "t_log", "tb_log",
    "app_logs", "access_logs", "error_logs", "operation_logs",
    "audit_logs", "system_logs",
    "日志", "日志表", "操作日志"
]

# 行为相关表名模式
BEHAVIOR_TABLE_PATTERNS = [
    "events", "event", "user_events", "behavior",
    "actions", "activity", "tracking",
    "行为", "事件", "活动"
]

# 基础表名列表（用于生成测试数据）
BASE_TABLE_NAMES = (
    USER_TABLE_PATTERNS[:3] +
    ORDER_TABLE_PATTERNS[:3] +
    PRODUCT_TABLE_PATTERNS[:3] +
    TRANSACTION_TABLE_PATTERNS[:3] +
    LOG_TABLE_PATTERNS[:3] +
    BEHAVIOR_TABLE_PATTERNS[:3]
)

# 数据库名称列表
DATABASE_NAMES = [
    "production", "prod_db", "main_db", "business_db",
    "warehouse", "dw", "data_warehouse", "analytics",
    "logs_db", "log_db", "audit_db", "archive_db",
    "users_db", "customer_db", "orders_db", "finance_db"
]

# 数据源名称列表
DATASOURCE_NAMES = [
    "生产数据库MySQL", "订单系统PostgreSQL", "数仓Hive",
    "日志采集Kafka", "用户行为MongoDB", "缓存Redis",
    "搜索引擎Elasticsearch", "归档存储MinIO"
]


# ==================== 数据类型分布 ====================

COLUMN_TYPE_DISTRIBUTION = {
    "varchar": 30,  # 30% 字符串类型
    "int": 15,      # 15% 整数类型
    "bigint": 10,   # 10% 长整型
    "decimal": 10,  # 10% 小数类型
    "datetime": 10, # 10% 日期时间类型
    "timestamp": 5, # 5% 时间戳类型
    "text": 5,      # 5% 长文本类型
    "boolean": 5,   # 5% 布尔类型
    "json": 5,      # 5% JSON类型
    "date": 3,      # 3% 日期类型
    "double": 2,    # 2% 双精度浮点
}


def get_random_column_type() -> str:
    """根据分布权重获取随机列类型"""
    import random
    types, weights = zip(*COLUMN_TYPE_DISTRIBUTION.items())
    return random.choices(types, weights=weights, k=1)[0]


# ==================== 生成器数量配置 ====================

@dataclass
class GeneratorQuantities:
    """各生成器生成的数量配置"""
    # 用户
    data_administrator_count: int = 2
    data_engineer_count: int = 5
    ai_developer_count: int = 5
    data_analyst_count: int = 8
    system_administrator_count: int = 3

    # 数据源和元数据
    datasource_count: int = 8
    databases_per_source: int = 2
    tables_per_database: int = 10
    min_columns_per_table: int = 5
    max_columns_per_table: int = 15

    # ETL
    etl_task_count: int = 20
    etl_logs_per_task: int = 5

    # 敏感数据
    sensitive_scan_task_count: int = 5
    sensitive_results_per_task: int = 15
    masking_rule_count: int = 10

    # 资产
    asset_count: int = 140
    asset_category_count: int = 10
    value_history_per_asset: int = 2

    # 血缘
    lineage_edge_count: int = 38
    lineage_event_count: int = 38

    # ML
    ml_model_count: int = 7
    versions_per_model: int = 3
    ml_deployment_count: int = 10

    # 知识库
    knowledge_base_count: int = 3
    documents_per_kb: int = 5
    vectors_per_document: int = 10

    # BI
    bi_dashboard_count: int = 3
    charts_per_dashboard: int = 4

    # 预警
    alert_rule_count: int = 7
    alert_history_per_rule: int = 10

    @property
    def total_user_count(self) -> int:
        """总用户数"""
        return (self.data_administrator_count + self.data_engineer_count +
                self.ai_developer_count + self.data_analyst_count +
                self.system_administrator_count)

    @property
    def total_table_count(self) -> int:
        """总表数"""
        return self.datasource_count * self.databases_per_source * self.tables_per_database

    @property
    def total_column_count(self) -> int:
        """总列数（大约）"""
        avg_columns = (self.min_columns_per_table + self.max_columns_per_table) // 2
        return self.total_table_count * avg_columns
