"""
数据源和元数据生成器

生成：
- 数据源（8个数据源）
- 元数据库（14个数据库）
- 元数据表（140个表）
- 元数据列（1200+列，包含敏感字段标注）
"""

import random
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from ..base import (
    BaseGenerator, DataSourceTypes, SensitivityTypes, SensitivityLevels,
    generate_id, random_date, random_chinese_company, random_chinese_description,
    infer_sensitivity_from_column
)
from ..config import (
    GeneratorQuantities, DATABASE_NAMES, DATASOURCE_NAMES,
    BASE_TABLE_NAMES, COLUMN_TYPE_DISTRIBUTION, get_sensitive_pattern
)


# 表名模板（按业务领域分类）
TABLE_TEMPLATES = {
    "user": ["users", "user_info", "user_profiles", "members", "accounts"],
    "order": ["orders", "order_items", "order_details", "order_payments", "order_shipments"],
    "product": ["products", "product_categories", "product_inventory", "product_prices", "skus"],
    "transaction": ["transactions", "payments", "refunds", "settlements", "financial_records"],
    "log": ["app_logs", "access_logs", "error_logs", "audit_logs", "operation_logs"],
    "behavior": ["user_events", "page_views", "clicks", "user_sessions", "behavior_tracking"],
    "config": ["system_config", "app_config", "feature_flags", "settings", "preferences"],
    "analytics": ["daily_metrics", "statistics", "analytics_events", "reports", "summaries"],
}


# 列名模板（按类型分类）
COLUMN_TEMPLATES = {
    "id": ["id", "user_id", "order_id", "product_id", "transaction_id", "table_id"],
    "user": ["username", "nickname", "real_name", "full_name", "display_name"],
    "contact": ["phone", "mobile", "telephone", "email", "contact", "emergency_contact"],
    "identity": ["id_card", "idcard", "identity_card", "passport", "ssn", "tax_id"],
    "financial": ["bank_card", "card_number", "account_number", "credit_card", "debit_card"],
    "address": ["address", "province", "city", "district", "zip_code", "postal_code"],
    "password": ["password", "passwd", "pwd", "password_hash", "encrypted_password"],
    "status": ["status", "state", "is_active", "is_deleted", "enabled"],
    "time": ["created_at", "updated_at", "deleted_at", "published_at", "last_login"],
    "amount": ["amount", "price", "total", "subtotal", "discount", "fee"],
    "count": ["count", "quantity", "num", "total_count", "row_count"],
    "description": ["description", "desc", "remark", "note", "comments", "details"],
    "metadata": ["metadata", "meta", "attributes", "properties", "extras", "options"],
}


class DatasourceGenerator(BaseGenerator):
    """
    数据源和元数据生成器

    生成数据源、数据库、表、列的完整元数据
    """

    def __init__(self, config: GeneratorQuantities = None, storage_manager=None):
        super().__init__(config, storage_manager)
        self.quantities = config or GeneratorQuantities()
        self._datasource_tables: Dict[str, List[str]] = {}

    def generate(self) -> Dict[str, List[Any]]:
        """
        生成所有数据源和元数据

        Returns:
            包含datasources, databases, tables, columns的字典
        """
        self.log("Generating datasources and metadata...", "info")

        # 生成数据源
        datasources = self._generate_datasources()
        self.store_data("datasources", datasources)
        self.set_dependency("datasources", datasources)

        # 生成元数据库
        databases = self._generate_databases(datasources)
        self.store_data("databases", databases)
        self.set_dependency("databases", databases)

        # 生成元数据表
        tables = self._generate_tables(databases)
        self.store_data("tables", tables)
        self.set_dependency("tables", tables)

        # 生成元数据列
        columns = self._generate_columns(tables)
        self.store_data("columns", columns)

        # 统计敏感列
        sensitive_count = sum(1 for c in columns if c.get("sensitivity_type") and c.get("sensitivity_type") != "none")

        self.log(
            f"Generated {len(datasources)} datasources, {len(databases)} databases, "
            f"{len(tables)} tables, {len(columns)} columns ({sensitive_count} sensitive)",
            "success"
        )

        return self.get_all_data()

    def _generate_datasources(self) -> List[Dict[str, Any]]:
        """生成数据源"""
        datasources = []

        ds_types = [
            (DataSourceTypes.MYSQL, 3),
            (DataSourceTypes.POSTGRESQL, 2),
            (DataSourceTypes.ORACLE, 1),
            (DataSourceTypes.MONGODB, 1),
            (DataSourceTypes.HIVE, 1),
        ]

        ds_index = 0
        for ds_type, count in ds_types:
            for i in range(count):
                is_active = random.random() > 0.2
                datasource = {
                    "source_id": generate_id("ds_", 8),
                    "name": DATASOURCE_NAMES[ds_index % len(DATASOURCE_NAMES)],
                    "description": f"{ds_type.upper()}数据源，用于{random.choice(['生产环境', '测试环境', '开发环境', '数据仓库'])}",
                    "type": ds_type,
                    "host": f"{random.choice(['192.168.1.', '10.0.0.', '172.16.0.'])}{random.randint(1, 254)}",
                    "port": self._get_default_port(ds_type),
                    "database": f"db_{ds_type}_{i+1}",
                    "username": f"{ds_type}_user",
                    "password": "******",  # 不存储真实密码
                    "status": "active" if is_active else "inactive",
                    "last_connected": random_date(7) if is_active else None,
                    "connection_config": self._generate_connection_config(ds_type),
                    "tags": random.sample(["生产", "测试", "核心", "备份", "只读", "读写"], k=random.randint(1, 3)),
                    "created_by": "admin",
                    "created_at": random_date(90),
                    "updated_at": random_date(30),
                }
                datasources.append(datasource)
                ds_index += 1

        return datasources

    def _get_default_port(self, ds_type: str) -> int:
        """获取数据源的默认端口"""
        ports = {
            DataSourceTypes.MYSQL: 3306,
            DataSourceTypes.POSTGRESQL: 5432,
            DataSourceTypes.ORACLE: 1521,
            DataSourceTypes.MONGODB: 27017,
            DataSourceTypes.HIVE: 10000,
            DataSourceTypes.KAFKA: 9092,
            DataSourceTypes.REDIS: 6379,
        }
        return ports.get(ds_type, 3306)

    def _generate_connection_config(self, ds_type: str) -> str:
        """生成连接配置JSON"""
        import json

        config = {
            "host": f"{ds_type}-example.com",
            "port": self._get_default_port(ds_type),
            "charset": "utf8mb4",
            "timeout": 30,
        }

        if ds_type == DataSourceTypes.MYSQL:
            config.update({
                "useSSL": False,
                "allowPublicKeyRetrieval": True,
            })
        elif ds_type == DataSourceTypes.MONGODB:
            config.update({
                "authSource": "admin",
                "replicaSet": "rs0",
            })

        return json.dumps(config, ensure_ascii=False)

    def _generate_databases(self, datasources: List[Dict]) -> List[Dict[str, Any]]:
        """生成元数据库"""
        databases = []

        for ds in datasources:
            db_count = random.randint(1, self.quantities.databases_per_source + 1)
            for i in range(db_count):
                db_name = DATABASE_NAMES[len(databases) % len(DATABASE_NAMES)]
                # 添加后缀避免重复
                if databases:
                    db_name = f"{db_name}_{len(databases)//len(DATASOURCE_NAMES)+1}" if any(d["database_name"] == db_name for d in databases) else db_name

                database = {
                    "database_id": generate_id("db_", 8),
                    "source_id": ds["source_id"],
                    "database_name": db_name,
                    "description": random_chinese_description(3, 8),
                    "owner": random.choice(["data-team", "bi-team", "ops-team", "admin"]),
                    "table_count": random.randint(5, 20),
                    "created_at": random_date(90),
                    "updated_at": random_date(30),
                }
                databases.append(database)

        return databases

    def _generate_tables(self, databases: List[Dict]) -> List[Dict[str, Any]]:
        """生成元数据表"""
        tables = []

        for db in databases:
            table_count = random.randint(
                self.quantities.tables_per_database - 3,
                self.quantities.tables_per_database + 3
            )

            # 获取业务领域（根据数据库名推测）
            domain = self._infer_domain_from_db_name(db["database_name"])
            table_names = TABLE_TEMPLATES.get(domain, TABLE_TEMPLATES["config"])

            for i in range(table_count):
                table_name = table_names[i % len(table_names)]
                # 添加表名后缀避免重复
                if i >= len(table_names):
                    table_name = f"{table_name}_{i+1}"

                # 确保表名唯一
                full_table_name = f"{db['database_name']}.{table_name}"

                table = {
                    "table_id": generate_id("tbl_", 8),
                    "database_id": db["database_id"],
                    "source_id": db["source_id"],
                    "table_name": table_name,
                    "database_name": db["database_name"],
                    "full_name": full_table_name,
                    "table_type": random.choice(["table", "view", "materialized_view"]),
                    "row_count": random.randint(1000, 10000000),
                    "description": random_chinese_description(5, 12),
                    "engine": random.choice(["InnoDB", "MyISAM", "PostgreSQL", "WiredTiger"]),
                    "collation": "utf8mb4_unicode_ci",
                    "create_time": random_date(365),
                    "update_time": random_date(30),
                    "tags": random.sample(
                        ["核心表", "维度表", "事实表", "临时表", "分区表", "大表"],
                        k=random.randint(0, 2)
                    ),
                    "created_at": random_date(90),
                    "updated_at": random_date(30),
                }
                tables.append(table)

                # 记录数据源的表
                if db["source_id"] not in self._datasource_tables:
                    self._datasource_tables[db["source_id"]] = []
                self._datasource_tables[db["source_id"]].append(table["table_id"])

        return tables

    def _infer_domain_from_db_name(self, db_name: str) -> str:
        """根据数据库名推断业务领域"""
        db_lower = db_name.lower()

        if any(keyword in db_lower for keyword in ["user", "customer", "member"]):
            return "user"
        elif any(keyword in db_lower for keyword in ["order", "trade", "transaction"]):
            return "order"
        elif any(keyword in db_lower for keyword in ["product", "goods", "item"]):
            return "product"
        elif any(keyword in db_lower for keyword in ["log", "audit", "track"]):
            return "log"
        elif any(keyword in db_lower for keyword in ["event", "behavior", "action"]):
            return "behavior"
        elif any(keyword in db_lower for keyword in ["metric", "stat", "analytics"]):
            return "analytics"
        else:
            return "config"

    def _generate_columns(self, tables: List[Dict]) -> List[Dict[str, Any]]:
        """生成元数据列"""
        columns = []

        for table in tables:
            column_count = random.randint(
                self.quantities.min_columns_per_table,
                self.quantities.max_columns_per_table
            )

            # 根据表名确定列的模板
            column_categories = self._get_column_categories_for_table(table["table_name"])

            for i in range(column_count):
                # 决定列的类别
                if i < len(column_categories):
                    category = column_categories[i]
                else:
                    category = random.choice(list(COLUMN_TEMPLATES.keys()))

                column_name = self._get_column_name(category, i)
                column_type = self._get_column_type_for_category(category)

                # 推断敏感类型
                sensitivity_type, sensitivity_level = infer_sensitivity_from_column(column_name)
                if sensitivity_type:
                    ai_confidence = random.randint(70, 100)
                else:
                    sensitivity_type = "none"
                    sensitivity_level = SensitivityLevels.PUBLIC
                    ai_confidence = 0

                column = {
                    "column_id": generate_id("col_", 8),
                    "table_id": table["table_id"],
                    "database_id": table["database_id"],
                    "table_name": table["table_name"],
                    "database_name": table["database_name"],
                    "column_name": column_name,
                    "column_type": column_type,
                    "is_nullable": category not in ["id"] and random.random() > 0.3,
                    "is_primary_key": category == "id" and i == 0,
                    "default_value": None if category != "status" else "'active'",
                    "position": i + 1,
                    "description": f"{column_name}字段",
                    "ai_description": f"AI识别的{column_name}字段，用于存储{'用户' if 'user' in column_name else ''}相关数据",
                    "sensitivity_level": sensitivity_level,
                    "sensitivity_type": sensitivity_type,
                    "semantic_tags": self._generate_semantic_tags(column_name, sensitivity_type),
                    "ai_annotated_at": random_date(60) if sensitivity_type != "none" else None,
                    "ai_confidence": ai_confidence,
                    "created_at": random_date(90),
                    "updated_at": random_date(30),
                }
                columns.append(column)

        return columns

    def _get_column_categories_for_table(self, table_name: str) -> List[str]:
        """根据表名返回列类别顺序"""
        table_lower = table_name.lower()

        if "user" in table_lower or "member" in table_lower:
            return ["id", "user", "contact", "identity", "financial", "address", "password",
                    "status", "time", "description"]
        elif "order" in table_lower:
            return ["id", "user", "id", "amount", "amount", "count", "status", "time"]
        elif "product" in table_lower:
            return ["id", "description", "description", "amount", "count", "status", "time"]
        elif "transaction" in table_lower or "payment" in table_lower:
            return ["id", "id", "amount", "amount", "status", "time", "description"]
        elif "log" in table_lower:
            return ["id", "user", "description", "time", "metadata"]
        elif "event" in table_lower or "behavior" in table_lower:
            return ["id", "user", "id", "time", "metadata"]
        else:
            return ["id", "description", "status", "time"]

    def _get_column_name(self, category: str, index: int) -> str:
        """获取列名"""
        names = COLUMN_TEMPLATES.get(category, ["col_" + str(index)])
        return names[index % len(names)]

    def _get_column_type_for_category(self, category: str) -> str:
        """根据类别获取数据类型"""
        type_map = {
            "id": "bigint",
            "user": "varchar(100)",
            "contact": "varchar(50)",
            "identity": "varchar(50)",
            "financial": "varchar(50)",
            "address": "varchar(500)",
            "password": "varchar(255)",
            "status": "varchar(20)",
            "time": "datetime",
            "amount": "decimal(18,2)",
            "count": "int",
            "description": "text",
            "metadata": "json",
        }
        return type_map.get(category, "varchar(255)")

    def _generate_semantic_tags(self, column_name: str, sensitivity_type: str) -> Optional[str]:
        """生成语义标签（JSON数组格式）"""
        import json

        tags = []

        col_lower = column_name.lower()

        # 基础标签
        if "id" in col_lower:
            tags.append("identifier")
        if "name" in col_lower or "title" in col_lower:
            tags.append("name")
        if "time" in col_lower or col_lower.endswith("_at") or col_lower.endswith("_date"):
            tags.append("timestamp")
        if "amount" in col_lower or "price" in col_lower or "total" in col_lower:
            tags.append("monetary")

        # 敏感标签
        if sensitivity_type == SensitivityTypes.PHONE:
            tags.extend(["phone", "contact", "pii"])
        elif sensitivity_type == SensitivityTypes.EMAIL:
            tags.extend(["email", "contact", "pii"])
        elif sensitivity_type == SensitivityTypes.ID_CARD:
            tags.extend(["id_card", "identity", "pii", "restricted"])
        elif sensitivity_type == SensitivityTypes.BANK_CARD:
            tags.extend(["bank_card", "financial", "pii", "restricted"])
        elif sensitivity_type == SensitivityTypes.PASSWORD:
            tags.extend(["password", "credential", "restricted"])

        return json.dumps(tags, ensure_ascii=False) if tags else None

    def get_sensitive_columns(self) -> List[Dict[str, Any]]:
        """获取所有敏感列"""
        columns = self.get_data("columns")
        return [c for c in columns if c.get("sensitivity_type") and c.get("sensitivity_type") != "none"]

    def get_sensitive_columns_by_type(self, sensitivity_type: str) -> List[Dict[str, Any]]:
        """按类型获取敏感列"""
        columns = self.get_data("columns")
        return [c for c in columns if c.get("sensitivity_type") == sensitivity_type]

    def save(self):
        """保存到数据库"""
        if not self.storage:
            self.log("No storage manager, skipping save", "warning")
            return

        self.log("Saving datasource and metadata to database...", "info")

        # 保存数据源
        datasources = self.get_data("datasources")
        if datasources and self.storage.table_exists("datasources"):
            self.storage.batch_insert(
                "datasources",
                ["source_id", "name", "description", "type", "host", "port", "database",
                 "username", "password", "status", "last_connected", "connection_config",
                 "tags", "created_by", "created_at", "updated_at"],
                datasources,
                idempotent=True,
                idempotent_columns=["source_id"]
            )
            self.log(f"Saved {len(datasources)} datasources", "success")

        # 保存元数据库
        databases = self.get_data("databases")
        if databases and self.storage.table_exists("metadata_databases"):
            self.storage.batch_insert(
                "metadata_databases",
                ["database_id", "source_id", "database_name", "description", "owner",
                 "table_count", "created_at", "updated_at"],
                databases,
                idempotent=True,
                idempotent_columns=["database_name"]
            )
            self.log(f"Saved {len(databases)} databases", "success")

        # 保存元数据表
        tables = self.get_data("tables")
        if tables and self.storage.table_exists("metadata_tables"):
            self.storage.batch_insert(
                "metadata_tables",
                ["table_id", "database_id", "source_id", "table_name", "database_name",
                 "full_name", "table_type", "row_count", "description", "engine",
                 "collation", "create_time", "update_time", "tags", "created_at", "updated_at"],
                tables,
                idempotent=True,
                idempotent_columns=["table_name", "database_name"]
            )
            self.log(f"Saved {len(tables)} tables", "success")

        # 保存元数据列
        columns = self.get_data("columns")
        if columns and self.storage.table_exists("metadata_columns"):
            self.storage.batch_insert(
                "metadata_columns",
                ["column_id", "table_id", "database_id", "table_name", "database_name",
                 "column_name", "column_type", "is_nullable", "is_primary_key", "default_value",
                 "position", "description", "ai_description", "sensitivity_level",
                 "sensitivity_type", "semantic_tags", "ai_annotated_at", "ai_confidence",
                 "created_at", "updated_at"],
                columns,
                idempotent=True,
                idempotent_columns=["column_name", "table_name", "database_name"]
            )
            self.log(f"Saved {len(columns)} columns", "success")

    def cleanup(self):
        """清理生成的数据"""
        if not self.storage:
            return

        self.log("Cleaning up datasource and metadata...", "info")

        for prefix in ["col_", "tbl_", "db_", "ds_"]:
            for table, id_col in [
                ("metadata_columns", "column_id"),
                ("metadata_tables", "table_id"),
                ("metadata_databases", "database_id"),
                ("datasources", "source_id"),
            ]:
                if self.storage.table_exists(table):
                    self.storage.cleanup_by_prefix(table, id_col, prefix)


def generate_datasource_data(config: GeneratorQuantities = None) -> Dict[str, List[Any]]:
    """
    便捷函数：生成数据源数据

    Args:
        config: 生成配置

    Returns:
        数据源数据字典
    """
    generator = DatasourceGenerator(config)
    return generator.generate()
