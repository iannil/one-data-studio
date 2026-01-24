"""
数据库初始化脚本
Sprint 4.1: 创建表并加载示例数据
"""

import os
import sys

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(__file__))

from models import Base, engine, SessionLocal, Dataset, DatasetColumn, MetadataDatabase, MetadataTable, MetadataColumn


def init_database():
    """初始化数据库：创建表和加载示例数据"""
    print("开始初始化数据库...")

    # 创建所有表
    print("创建数据库表...")
    Base.metadata.create_all(bind=engine)
    print("数据库表创建完成")

    # 加载示例数据
    print("加载示例数据...")
    db = SessionLocal()
    try:
        # 检查是否已有数据
        existing_db = db.query(MetadataDatabase).first()
        if existing_db:
            print("数据库已有数据，跳过示例数据加载")
            return

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

        # 创建元数据列
        columns = [
            # orders 表列
            MetadataColumn(
                table_name="orders",
                database_name="sales_dw",
                column_name="id",
                column_type="BIGINT",
                is_nullable=False,
                description="主键ID",
                position=1
            ),
            MetadataColumn(
                table_name="orders",
                database_name="sales_dw",
                column_name="customer_id",
                column_type="BIGINT",
                is_nullable=False,
                description="客户ID",
                position=2
            ),
            MetadataColumn(
                table_name="orders",
                database_name="sales_dw",
                column_name="amount",
                column_type="DECIMAL(10,2)",
                is_nullable=False,
                description="金额",
                position=3
            ),
            MetadataColumn(
                table_name="orders",
                database_name="sales_dw",
                column_name="created_at",
                column_type="TIMESTAMP",
                is_nullable=False,
                description="创建时间",
                position=4
            ),
            # customers 表列
            MetadataColumn(
                table_name="customers",
                database_name="sales_dw",
                column_name="id",
                column_type="BIGINT",
                is_nullable=False,
                description="主键ID",
                position=1
            ),
            MetadataColumn(
                table_name="customers",
                database_name="sales_dw",
                column_name="name",
                column_type="VARCHAR(128)",
                is_nullable=False,
                description="客户名称",
                position=2
            ),
            MetadataColumn(
                table_name="customers",
                database_name="sales_dw",
                column_name="email",
                column_type="VARCHAR(256)",
                is_nullable=True,
                description="邮箱",
                position=3
            ),
        ]
        db.add_all(columns)

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

        db.commit()
        print("示例数据加载完成")

    except Exception as e:
        db.rollback()
        print(f"初始化失败: {e}")
        raise
    finally:
        db.close()

    print("数据库初始化完成!")


if __name__ == "__main__":
    init_database()
