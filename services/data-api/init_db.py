"""
数据库初始化脚本
Sprint 4.1: 创建表并加载示例数据
"""

import logging
import os
import sys

# 添加 src 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from models import Base, DataSource, Dataset, DatasetColumn, MetadataDatabase, MetadataTable, MetadataColumn
from database import db_manager

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def init_database():
    """初始化数据库：创建表和加载示例数据"""
    logger.info("开始初始化数据库...")

    # 确保数据库已初始化
    db_manager.init_db()

    # 删除所有表（慎用！）
    logger.info("删除旧表...")
    Base.metadata.drop_all(bind=db_manager.engine)

    # 创建所有表
    logger.info("创建数据库表...")
    Base.metadata.create_all(bind=db_manager.engine)
    logger.info("数据库表创建完成")

    # 加载示例数据
    logger.info("加载示例数据...")
    db = db_manager.SessionLocal()
    try:
        # 检查是否已有数据
        existing_ds = db.query(DataSource).first()
        if existing_ds:
            logger.info("数据库已有数据，跳过示例数据加载")
            return

        # 创建示例数据源
        mysql_source = DataSource(
            source_id="ds-mysql-001",
            name="生产 MySQL",
            description="生产环境 MySQL 数据库",
            type="mysql",
            connection_config={
                "host": "prod-mysql.example.com",
                "port": 3306,
                "username": "readonly_user",
                "database": "production_db"
            },
            status="connected",
            source_metadata={"version": "8.0.32", "tables_count": 156},
            tags=["production", "mysql"],
            created_by="admin"
        )
        pg_source = DataSource(
            source_id="ds-pg-001",
            name="分析 PostgreSQL",
            description="分析环境 PostgreSQL 数据库",
            type="postgresql",
            connection_config={
                "host": "analytics-pg.example.com",
                "port": 5432,
                "username": "analyst",
                "database": "analytics_dw"
            },
            status="connected",
            source_metadata={"version": "15.2", "tables_count": 42},
            tags=["analytics", "postgresql"],
            created_by="admin"
        )
        db.add_all([mysql_source, pg_source])
        db.flush()

        # 创建示例数据集
        dataset = Dataset(
            dataset_id="ds-001",
            name="sales_data_v1.0",
            description="销售数据清洗结果",
            storage_type="s3",
            storage_path="s3://etl-output/sales/2024-01/",
            format="parquet",
            status="active",
            row_count=1000000,
            size_bytes=52428800,
            tags=["sales", "cleansed", "2024q1"]
        )
        db.add(dataset)
        db.flush()

        # 创建数据集列
        dataset_columns = [
            DatasetColumn(
                dataset_id="ds-001",
                column_name="id",
                column_type="INT64",
                is_nullable=False,
                description="记录ID",
                position=1
            ),
            DatasetColumn(
                dataset_id="ds-001",
                column_name="customer_id",
                column_type="INT64",
                is_nullable=False,
                description="客户ID",
                position=2
            ),
            DatasetColumn(
                dataset_id="ds-001",
                column_name="amount",
                column_type="DECIMAL(10,2)",
                is_nullable=False,
                description="金额",
                position=3
            ),
            DatasetColumn(
                dataset_id="ds-001",
                column_name="created_at",
                column_type="TIMESTAMP",
                is_nullable=False,
                description="创建时间",
                position=4
            ),
        ]
        db.add_all(dataset_columns)

        # 创建元数据库
        sales_dw = MetadataDatabase(
            database_name="sales_dw",
            description="销售数据仓库",
            owner="data_team"
        )
        user_dw = MetadataDatabase(
            database_name="analytics_db",
            description="分析数据库",
            owner="data_team"
        )
        db.add_all([sales_dw, user_dw])
        db.flush()

        # 创建元数据表
        orders_table = MetadataTable(
            table_name="orders",
            database_name="sales_dw",
            description="订单表",
            row_count=10000000
        )
        customers_table = MetadataTable(
            table_name="customers",
            database_name="sales_dw",
            description="客户表",
            row_count=1000000
        )
        db.add_all([orders_table, customers_table])
        db.flush()

        db.commit()
        logger.info("示例数据加载完成")

    except Exception as e:
        db.rollback()
        logger.error(f"初始化失败: {e}")
        raise
    finally:
        db.close()

    logger.info("数据库初始化完成!")


if __name__ == "__main__":
    init_database()
