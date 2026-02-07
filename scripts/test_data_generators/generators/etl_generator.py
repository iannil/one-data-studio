"""
ETL任务生成器

生成：
- ETL任务（20个任务）
- ETL任务日志（60+条日志）
"""

import random
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from ..base import (
    BaseGenerator, ETLTaskTypes, ETLStatus, DataSourceTypes,
    generate_id, random_date, random_date_range
)
from ..config import GeneratorQuantities


# ETL任务名称模板
ETL_NAME_TEMPLATES = {
    "sync": [
        "用户数据同步", "订单数据同步", "产品信息同步",
        "会员数据同步", "库存数据同步", "交易数据同步",
    ],
    "extract": [
        "日志数据抽取", "行为数据抽取", "埋点数据抽取",
        "交易流水抽取", "支付数据抽取",
    ],
    "load": [
        "数据加载-ODS层", "数据加载-DWD层", "数据加载-DWS层",
        "维表加载", "事实表加载",
    ],
    "transform": [
        "用户指标计算", "销售指标计算", "日结汇总处理",
        "宽表生成", "聚合计算任务",
    ],
    "archive": [
        "日志归档任务", "历史数据归档", "冷数据迁移",
        "备份任务", "清理归档",
    ],
}


class ETLGenerator(BaseGenerator):
    """
    ETL任务生成器

    生成ETL任务和执行日志
    """

    def __init__(self, config: GeneratorQuantities = None, storage_manager=None):
        super().__init__(config, storage_manager)
        self.quantities = config or GeneratorQuantities()

    def generate(self) -> Dict[str, List[Any]]:
        """
        生成所有ETL数据

        Returns:
            包含etl_tasks, etl_logs的字典
        """
        self.log("Generating ETL tasks and logs...", "info")

        # 生成ETL任务
        etl_tasks = self._generate_etl_tasks()
        self.store_data("etl_tasks", etl_tasks)

        # 生成ETL任务日志
        etl_logs = self._generate_etl_logs(etl_tasks)
        self.store_data("etl_logs", etl_logs)

        self.log(f"Generated {len(etl_tasks)} ETL tasks, {len(etl_logs)} log entries", "success")

        return self.get_all_data()

    def _generate_etl_tasks(self) -> List[Dict[str, Any]]:
        """生成ETL任务"""
        tasks = []

        # 任务类型分布
        type_distribution = [
            (ETLTaskTypes.SYNC, 6),
            (ETLTaskTypes.EXTRACT, 4),
            (ETLTaskTypes.LOAD, 4),
            (ETLTaskTypes.TRANSFORM, 4),
            (ETLTaskTypes.ARCHIVE, 2),
        ]

        task_index = 0

        for task_type, count in type_distribution:
            name_templates = ETL_NAME_TEMPLATES.get(task_type, ETL_NAME_TEMPLATES["sync"])

            for i in range(count):
                # 获取源/目标表（从依赖数据获取）
                source_table, target_table = self._get_source_target_tables(task_type)

                # 决定状态
                status_weights = [ETLStatus.ACTIVE, ETLStatus.PAUSED, ETLStatus.FAILED]
                status = random.choices(
                    status_weights,
                    weights=[0.7, 0.2, 0.1]
                )[0]

                # 生成统计信息
                run_count = random.randint(10, 500) if status == ETLStatus.ACTIVE else random.randint(0, 50)
                success_count = int(run_count * random.uniform(0.85, 0.98))
                fail_count = run_count - success_count

                task = {
                    "task_id": generate_id("etl_", 8),
                    "name": f"{name_templates[i % len(name_templates)]}_{task_index+1:02d}",
                    "description": f"从{source_table}同步/处理数据到{target_table}",
                    "task_type": task_type,
                    "engine_type": random.choice(["builtin", "kettle", "spark", "flink"]),
                    "status": status,
                    # 源配置
                    "source_type": random.choice([DataSourceTypes.MYSQL, DataSourceTypes.POSTGRESQL, "api", "kafka"]),
                    "source_config": self._generate_source_config(task_type),
                    "source_query": source_table,
                    # 目标配置
                    "target_type": random.choice([DataSourceTypes.MYSQL, "minio", "hive"]),
                    "target_config": self._generate_target_config(task_type),
                    "target_table": target_table,
                    # 转换配置
                    "transform_config": self._generate_transform_config(task_type),
                    # 调度配置
                    "schedule_type": random.choice(["manual", "cron", "interval", "realtime"]),
                    "schedule_config": self._generate_schedule_config(),
                    # Kettle配置（如果使用）
                    "kettle_job_path": f"/etl/jobs/task_{task_index}.kjb" if random.random() > 0.5 else None,
                    "kettle_trans_path": f"/etl/trans/task_{task_index}.ktr" if random.random() > 0.5 else None,
                    # 执行统计
                    "last_run_at": random_date(1) if status == ETLStatus.ACTIVE else None,
                    "last_success_at": random_date(7) if status == ETLStatus.ACTIVE else None,
                    "next_run_at": random_date(0) if status == ETLStatus.ACTIVE else None,
                    "run_count": run_count,
                    "success_count": success_count,
                    "fail_count": fail_count,
                    "last_row_count": random.randint(100, 100000) if success_count > 0 else 0,
                    "last_duration_seconds": random.randint(30, 3600) if success_count > 0 else 0,
                    "last_error": None if status == ETLStatus.ACTIVE else "Connection timeout",
                    # 创建信息
                    "created_by": random.choice(["admin", "data-engineer-01", "data-engineer-02"]),
                    "created_at": random_date(90),
                    "updated_at": random_date(30),
                }
                tasks.append(task)
                task_index += 1

        return tasks

    def _get_source_target_tables(self, task_type: str) -> tuple:
        """获取源表和目标表名"""
        # 尝试从依赖数据获取表
        tables = self.get_dependency("tables")

        if tables and len(tables) >= 2:
            source = random.choice(tables)["table_name"]
            target = random.choice(tables)["table_name"]
            return source, target

        # 默认表名
        source_tables = ["users", "orders", "products", "logs", "events"]
        target_tables = ["dw_users", "dw_orders", "dw_products", "ods_logs", "dwd_events"]

        return random.choice(source_tables), random.choice(target_tables)

    def _generate_source_config(self, task_type: str) -> str:
        """生成源配置JSON"""
        config = {
            "host": "source-db.example.com",
            "port": 3306,
            "database": "source_db",
        }

        if task_type == ETLTaskTypes.EXTRACT:
            config.update({
                "batch_size": random.randint(1000, 10000),
                "parallel": random.choice([1, 2, 4]),
            })

        return json.dumps(config, ensure_ascii=False)

    def _generate_target_config(self, task_type: str) -> str:
        """生成目标配置JSON"""
        config = {
            "host": "target-db.example.com",
            "port": 3306,
            "database": "target_db",
        }

        if task_type in [ETLTaskTypes.LOAD, ETLTaskTypes.ARCHIVE]:
            config.update({
                "write_mode": random.choice(["insert", "upsert", "replace"]),
                "batch_size": random.randint(1000, 5000),
            })

        return json.dumps(config, ensure_ascii=False)

    def _generate_transform_config(self, task_type: str) -> str:
        """生成转换配置JSON"""
        if task_type == ETLTaskTypes.TRANSFORM:
            config = {
                "transformations": [
                    {"type": "filter", "condition": "status = 'active'"},
                    {"type": "aggregate", "fields": ["user_id", "count(*)"]},
                ]
            }
        elif task_type == ETLTaskTypes.SYNC:
            config = {
                "mappings": {
                    "id": "user_id",
                    "name": "username",
                    "created": "created_at",
                }
            }
        else:
            config = {}

        return json.dumps(config, ensure_ascii=False)

    def _generate_schedule_config(self) -> str:
        """生成调度配置JSON"""
        schedule_types = [
            {"expression": "0 */2 * * *", "timezone": "Asia/Shanghai"},
            {"expression": "0 1 * * *", "timezone": "Asia/Shanghai"},
            {"expression": "0 */4 * * *", "timezone": "Asia/Shanghai"},
            {"expression": "0 0 * * *", "timezone": "Asia/Shanghai"},
            {"interval": 300, "unit": "seconds"},
        ]

        return json.dumps(random.choice(schedule_types), ensure_ascii=False)

    def _generate_etl_logs(self, tasks: List[Dict]) -> List[Dict[str, Any]]:
        """生成ETL任务日志"""
        logs = []

        for task in tasks:
            # 根据任务状态决定日志数量
            if task["status"] == ETLStatus.ACTIVE:
                log_count = random.randint(5, 10)
            else:
                log_count = random.randint(0, 3)

            # 状态权重
            status_weights = [
                ETLStatus.COMPLETED,
                ETLStatus.COMPLETED,
                ETLStatus.COMPLETED,
                ETLStatus.FAILED,
                ETLStatus.RUNNING,
            ]

            for i in range(log_count):
                status = random.choice(status_weights)

                # 生成时间（越新的越靠前）
                days_ago = log_count - i + random.randint(0, 2)
                started_at = random_date(days_ago)

                # 根据状态计算结束时间和持续时间
                if status == ETLStatus.RUNNING:
                    finished_at = None
                    duration = None
                elif status == ETLStatus.FAILED:
                    duration = random.randint(10, 300)
                    finished_at = started_at + timedelta(seconds=duration)
                else:
                    duration = random.randint(60, 1800)
                    finished_at = started_at + timedelta(seconds=duration)

                # 统计数据
                if status == ETLStatus.COMPLETED:
                    rows_read = random.randint(1000, 100000)
                    rows_written = int(rows_read * random.uniform(0.95, 1.0))
                    rows_failed = 0
                    error_message = None
                elif status == ETLStatus.FAILED:
                    rows_read = random.randint(100, 10000)
                    rows_written = 0
                    rows_failed = rows_read
                    error_message = random.choice([
                        "Connection timeout",
                        "Duplicate key error",
                        "Data format error",
                        "Out of memory",
                        "Table not found",
                    ])
                else:
                    rows_read = random.randint(100, 5000)
                    rows_written = 0
                    rows_failed = 0
                    error_message = None

                log = {
                    "log_id": generate_id("log_", 8),
                    "task_id": task["task_id"],
                    "status": status,
                    "started_at": started_at,
                    "finished_at": finished_at,
                    "duration_seconds": duration,
                    "rows_read": rows_read,
                    "rows_written": rows_written,
                    "rows_failed": rows_failed,
                    "bytes_read": rows_read * random.randint(100, 500) if rows_read else 0,
                    "bytes_written": rows_written * random.randint(100, 500) if rows_written else 0,
                    "error_message": error_message,
                    "trigger_type": random.choice(["manual", "scheduled", "api"]),
                    "triggered_by": task["created_by"],
                    "created_at": started_at,
                }
                logs.append(log)

        # 按时间排序
        logs.sort(key=lambda x: x["started_at"], reverse=True)

        return logs

    def save(self):
        """保存到数据库"""
        if not self.storage:
            self.log("No storage manager, skipping save", "warning")
            return

        self.log("Saving ETL tasks to database...", "info")

        # 保存ETL任务
        etl_tasks = self.get_data("etl_tasks")
        if etl_tasks and self.storage.table_exists("etl_tasks"):
            self.storage.batch_insert(
                "etl_tasks",
                ["task_id", "name", "description", "task_type", "engine_type", "status",
                 "source_type", "source_config", "source_query", "target_type", "target_config",
                 "target_table", "transform_config", "schedule_type", "schedule_config",
                 "kettle_job_path", "kettle_trans_path", "last_run_at", "last_success_at",
                 "next_run_at", "run_count", "success_count", "fail_count", "last_row_count",
                 "last_duration_seconds", "last_error", "created_by", "created_at", "updated_at"],
                etl_tasks,
                idempotent=True,
                idempotent_columns=["task_id"]
            )
            self.log(f"Saved {len(etl_tasks)} ETL tasks", "success")

        # 保存ETL日志
        etl_logs = self.get_data("etl_logs")
        if etl_logs and self.storage.table_exists("etl_task_logs"):
            self.storage.batch_insert(
                "etl_task_logs",
                ["log_id", "task_id", "status", "started_at", "finished_at", "duration_seconds",
                 "rows_read", "rows_written", "rows_failed", "bytes_read", "bytes_written",
                 "error_message", "trigger_type", "triggered_by", "created_at"],
                etl_logs,
                idempotent=True,
                idempotent_columns=["log_id"]
            )
            self.log(f"Saved {len(etl_logs)} ETL logs", "success")

    def cleanup(self):
        """清理生成的数据"""
        if not self.storage:
            return

        self.log("Cleaning up ETL data...", "info")

        if self.storage.table_exists("etl_task_logs"):
            self.storage.cleanup_by_prefix("etl_task_logs", "log_id", "log_")

        if self.storage.table_exists("etl_tasks"):
            self.storage.cleanup_by_prefix("etl_tasks", "task_id", "etl_")


def generate_etl_data(config: GeneratorQuantities = None) -> Dict[str, List[Any]]:
    """
    便捷函数：生成ETL数据

    Args:
        config: 生成配置

    Returns:
        ETL数据字典
    """
    generator = ETLGenerator(config)
    return generator.generate()
