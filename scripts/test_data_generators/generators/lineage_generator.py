"""
数据血缘生成器

生成：
- 数据血缘边（38条边）
- 数据血缘事件（38条事件）
"""

import random
from datetime import datetime, timedelta
from typing import Any, Dict, List, Tuple

from ..base import BaseGenerator, generate_id, random_date
from ..config import GeneratorQuantities


class LineageGenerator(BaseGenerator):
    """
    数据血缘生成器

    生成数据血缘边和事件
    """

    # 转换类型
    TRANSFORMATION_TYPES = [
        "etl", "view", "materialized_view", "sql_join",
        "aggregation", "filter", "union", "lookup"
    ]

    # 事件类型
    EVENT_TYPES = [
        "create", "update", "delete", "schema_change",
        "relation_add", "relation_remove", "dependency_change"
    ]

    def __init__(self, config: GeneratorQuantities = None, storage_manager=None):
        super().__init__(config, storage_manager)
        self.quantities = config or GeneratorQuantities()

    def generate(self) -> Dict[str, List[Any]]:
        """
        生成所有数据血缘

        Returns:
            包含lineage_edges, lineage_events的字典
        """
        self.log("Generating data lineage...", "info")

        # 生成血缘边
        edges = self._generate_edges()
        self.store_data("edges", edges)

        # 生成血缘事件
        events = self._generate_events(edges)
        self.store_data("events", events)

        self.log(f"Generated {len(edges)} lineage edges, {len(events)} events", "success")

        return self.get_all_data()

    def _get_tables_for_lineage(self) -> List[Dict[str, Any]]:
        """获取用于血缘的表"""
        tables = self.get_dependency("tables")
        if tables:
            return tables

        # 生成模拟表
        return [
            {"table_id": generate_id("tbl_", 8), "table_name": f"source_{i}", "database_name": "source_db"}
            for i in range(1, 21)
        ] + [
            {"table_id": generate_id("tbl_", 8), "table_name": f"target_{i}", "database_name": "target_db"}
            for i in range(1, 21)
        ]

    def _generate_edges(self) -> List[Dict[str, Any]]:
        """生成血缘边"""
        edges = []
        tables = self._get_tables_for_lineage()

        # 确保有足够的表
        if len(tables) < 2:
            tables = [
                {"table_id": f"tbl_{i:04d}", "table_name": f"table_{i}", "database_name": "db"}
                for i in range(1, 50)
            ]

        # 分离源表和目标表
        source_tables = tables[:len(tables) // 2]
        target_tables = tables[len(tables) // 2:]

        edge_count = self.quantities.lineage_edge_count

        for i in range(edge_count):
            source_table = random.choice(source_tables)
            target_table = random.choice(target_tables)

            # 关联ETL任务
            etl_tasks = self.get_dependency("etl_tasks")
            etl_task_id = None
            if etl_tasks:
                etl_task_id = random.choice(etl_tasks)["task_id"]

            edge = {
                "edge_id": generate_id("edge_", 8),
                "source_table_id": source_table["table_id"],
                "source_table_name": source_table["table_name"],
                "source_database": source_table["database_name"],
                "target_table_id": target_table["table_id"],
                "target_table_name": target_table["table_name"],
                "target_database": target_table["database_name"],
                "transformation_type": random.choice(self.TRANSFORMATION_TYPES),
                "transformation_sql": self._generate_transformation_sql(),
                "etl_task_id": etl_task_id,
                "description": f"从{source_table['table_name']}到{target_table['table_name']}的数据流转",
                "created_at": random_date(90),
            }
            edges.append(edge)

        return edges

    def _generate_transformation_sql(self) -> str:
        """生成转换SQL"""
        templates = [
            "SELECT * FROM {source}",
            "SELECT id, name, created_at FROM {source} WHERE status = 'active'",
            "SELECT user_id, COUNT(*) as cnt FROM {source} GROUP BY user_id",
            "SELECT a.*, b.name FROM {source} a JOIN dim_table b ON a.id = b.id",
            "INSERT INTO {target} SELECT * FROM {source}",
        ]
        return random.choice(templates)

    def _generate_events(self, edges: List[Dict]) -> List[Dict[str, Any]]:
        """生成血缘事件"""
        events = []

        for edge in edges:
            # 为每条边生成1-2个事件
            event_count = random.randint(1, 2)

            for i in range(event_count):
                event = {
                    "event_id": generate_id("levt_", 8),
                    "edge_id": edge["edge_id"],
                    "event_type": random.choice(self.EVENT_TYPES),
                    "event_data": {
                        "source": edge["source_table_name"],
                        "target": edge["target_table_name"],
                        "change": "schema update" if random.random() > 0.5 else "relation change"
                    },
                    "operator": random.choice(["system", "admin", "data-engineer-01"]),
                    "description": f"血缘边{edge['edge_id']}发生{random.choice(self.EVENT_TYPES)}事件",
                    "created_at": random_date(60),
                }
                events.append(event)

        return events

    def save(self):
        """保存到数据库"""
        if not self.storage:
            self.log("No storage manager, skipping save", "warning")
            return

        self.log("Saving lineage to database...", "info")

        # 保存血缘边
        edges = self.get_data("edges")
        if edges and self.storage.table_exists("data_lineage"):
            self.storage.batch_insert(
                "data_lineage",
                ["edge_id", "source_table_id", "source_table_name", "source_database",
                 "target_table_id", "target_table_name", "target_database",
                 "transformation_type", "transformation_sql", "etl_task_id",
                 "description", "created_at"],
                edges,
                idempotent=True,
                idempotent_columns=["edge_id"]
            )
            self.log(f"Saved {len(edges)} lineage edges", "success")

        # 保存血缘事件
        events = self.get_data("events")
        if events and self.storage.table_exists("data_lineage_events"):
            import json
            events_copy = []
            for e in events:
                e_copy = e.copy()
                e_copy["event_data"] = json.dumps(e["event_data"], ensure_ascii=False)
                events_copy.append(e_copy)

            self.storage.batch_insert(
                "data_lineage_events",
                ["event_id", "edge_id", "event_type", "event_data",
                 "operator", "description", "created_at"],
                events_copy,
                idempotent=True,
                idempotent_columns=["event_id"]
            )
            self.log(f"Saved {len(events)} lineage events", "success")

    def cleanup(self):
        """清理生成的数据"""
        if not self.storage:
            return

        self.log("Cleaning up lineage data...", "info")

        if self.storage.table_exists("data_lineage_events"):
            self.storage.cleanup_by_prefix("data_lineage_events", "event_id", "levt_")

        if self.storage.table_exists("data_lineage"):
            self.storage.cleanup_by_prefix("data_lineage", "edge_id", "edge_")


def generate_lineage_data(config: GeneratorQuantities = None) -> Dict[str, List[Any]]:
    """
    便捷函数：生成血缘数据

    Args:
        config: 生成配置

    Returns:
        血缘数据字典
    """
    generator = LineageGenerator(config)
    return generator.generate()
