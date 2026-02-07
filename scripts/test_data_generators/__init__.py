"""
测试数据生成器

统一的测试数据生成入口

Usage:
    from scripts.test_data_generators import generate_all_data

    data = generate_all_data()
"""

from .base import (
    BaseGenerator,
    GeneratorConfig,
    UserRoles,
    DataSourceTypes,
    SensitivityTypes,
    SensitivityLevels,
    ETLTaskTypes,
    ETLStatus,
    AssetTypes,
    AssetCategories,
    MLModelTypes,
    BIChartTypes,
    generate_id,
    random_date,
    random_chinese_name,
    generate_email,
    generate_phone,
    mask_phone,
    mask_id_card,
    mask_bank_card,
    mask_email,
)

from .config import (
    DatabaseConfig,
    RedisConfig,
    MinIOConfig,
    MilvusConfig,
    GeneratorQuantities,
    ROLE_PERMISSIONS,
    SENSITIVE_PATTERNS,
)

from .storage import (
    get_mysql_manager,
    get_minio_manager,
    get_milvus_manager,
    get_redis_manager,
)

from .generators import (
    UserGenerator,
    DatasourceGenerator,
    ETLGenerator,
    SensitiveGenerator,
    AssetGenerator,
    LineageGenerator,
    MLGenerator,
    KnowledgeGenerator,
    BIGenerator,
    AlertGenerator,
    generate_user_data,
    generate_datasource_data,
    generate_etl_data,
    generate_sensitive_data,
    generate_asset_data,
    generate_lineage_data,
    generate_ml_data,
    generate_knowledge_data,
    generate_bi_data,
    generate_alert_data,
)

from .validators import (
    DataValidator,
    LinkageValidator,
    validate_data,
    validate_linkage,
)

__all__ = [
    # Base
    "BaseGenerator",
    "GeneratorConfig",
    "UserRoles",
    "DataSourceTypes",
    "SensitivityTypes",
    "SensitivityLevels",
    "ETLTaskTypes",
    "ETLStatus",
    "AssetTypes",
    "AssetCategories",
    "MLModelTypes",
    "BIChartTypes",
    "generate_id",
    "random_date",
    "random_chinese_name",
    "generate_email",
    "generate_phone",
    "mask_phone",
    "mask_id_card",
    "mask_bank_card",
    "mask_email",
    # Config
    "DatabaseConfig",
    "RedisConfig",
    "MinIOConfig",
    "MilvusConfig",
    "GeneratorQuantities",
    "ROLE_PERMISSIONS",
    "SENSITIVE_PATTERNS",
    # Storage
    "get_mysql_manager",
    "get_minio_manager",
    "get_milvus_manager",
    "get_redis_manager",
    # Generators
    "UserGenerator",
    "DatasourceGenerator",
    "ETLGenerator",
    "SensitiveGenerator",
    "AssetGenerator",
    "LineageGenerator",
    "MLGenerator",
    "KnowledgeGenerator",
    "BIGenerator",
    "AlertGenerator",
    "generate_user_data",
    "generate_datasource_data",
    "generate_etl_data",
    "generate_sensitive_data",
    "generate_asset_data",
    "generate_lineage_data",
    "generate_ml_data",
    "generate_knowledge_data",
    "generate_bi_data",
    "generate_alert_data",
    # Validators
    "DataValidator",
    "LinkageValidator",
    "validate_data",
    "validate_linkage",
]


def generate_all_data(config: GeneratorQuantities = None, storage_managers: dict = None):
    """
    生成全部测试数据

    Args:
        config: 生成配置
        storage_managers: 存储管理器字典

    Returns:
        所有生成的数据字典
    """
    if config is None:
        config = GeneratorQuantities()

    if storage_managers is None:
        storage_managers = {
            "mysql": get_mysql_manager(mock=True),
            "minio": get_minio_manager(mock=True),
            "milvus": get_milvus_manager(mock=True),
            "redis": get_redis_manager(mock=True),
        }

    all_data = {}
    dependencies = {}

    # 1. 用户和权限
    print("生成用户和权限数据...")
    user_gen = UserGenerator(config, storage_managers["mysql"])
    user_data = user_gen.generate()
    all_data.update(user_data)
    dependencies["users"] = user_data
    dependencies["roles"] = user_data

    # 2. 数据源和元数据
    print("生成数据源和元数据...")
    ds_gen = DatasourceGenerator(config, storage_managers["mysql"])
    ds_data = ds_gen.generate()
    all_data.update(ds_data)
    dependencies["datasources"] = ds_data
    dependencies["databases"] = ds_data
    dependencies["tables"] = ds_data
    dependencies["columns"] = ds_data

    # 3. ETL任务
    print("生成ETL任务...")
    etl_gen = ETLGenerator(config, storage_managers["mysql"])
    etl_gen.set_dependency("tables", ds_data.get("tables", []))
    etl_data = etl_gen.generate()
    all_data.update(etl_data)
    dependencies["etl_tasks"] = etl_data

    # 4. 敏感数据
    print("生成敏感数据扫描...")
    sens_gen = SensitiveGenerator(config, storage_managers["mysql"])
    sens_gen.set_dependency("tables", ds_data.get("tables", []))
    sens_data = sens_gen.generate()
    all_data.update(sens_data)

    # 5. 数据资产
    print("生成数据资产...")
    asset_gen = AssetGenerator(config, storage_managers["mysql"])
    asset_gen.set_dependency("tables", ds_data.get("tables", []))
    asset_data = asset_gen.generate()
    all_data.update(asset_data)

    # 6. 数据血缘
    print("生成数据血缘...")
    lineage_gen = LineageGenerator(config, storage_managers["mysql"])
    lineage_gen.set_dependency("tables", ds_data.get("tables", []))
    lineage_gen.set_dependency("etl_tasks", etl_data.get("etl_tasks", []))
    lineage_data = lineage_gen.generate()
    all_data.update(lineage_data)

    # 7. ML模型
    print("生成ML模型...")
    ml_gen = MLGenerator(config, storage_managers["mysql"])
    ml_data = ml_gen.generate()
    all_data.update(ml_data)
    dependencies["ml_models"] = ml_data

    # 8. 知识库
    print("生成知识库...")
    kb_gen = KnowledgeGenerator(
        config,
        storage_managers["mysql"],
        storage_managers["minio"],
        storage_managers["milvus"]
    )
    kb_data = kb_gen.generate()
    all_data.update(kb_data)

    # 9. BI报表
    print("生成BI报表...")
    bi_gen = BIGenerator(config, storage_managers["mysql"])
    bi_gen.set_dependency("tables", ds_data.get("tables", []))
    bi_data = bi_gen.generate()
    all_data.update(bi_data)

    # 10. 预警规则
    print("生成预警规则...")
    alert_gen = AlertGenerator(config, storage_managers["mysql"])
    alert_gen.set_dependency("tables", ds_data.get("tables", []))
    alert_data = alert_gen.generate()
    all_data.update(alert_data)

    print("\n数据生成完成!")

    return all_data


def validate_all_data(data: dict = None):
    """
    验证全部数据

    Args:
        data: 要验证的数据字典

    Returns:
        验证结果
    """
    if data is None:
        # 从数据库读取
        mysql = get_mysql_manager()
        mysql.connect()

        data = {}
        for table in ["users", "datasources", "metadata_tables", "metadata_columns", "etl_tasks"]:
            if mysql.table_exists(table):
                data[table] = mysql.fetch_all(f"SELECT * FROM {table}")

    validator = DataValidator(data)
    return validator.validate_all()


if __name__ == "__main__":
    # 支持直接运行
    import sys
    sys.path.insert(0, ".")

    from .cli import main
    sys.exit(main())
