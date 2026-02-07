"""
预警规则生成器

生成：
- 预警规则（7条规则）
- 预警历史（70+条历史）
"""

import random
from datetime import datetime, timedelta
from typing import Any, Dict, List

from ..base import BaseGenerator, generate_id, random_date, random_chinese_description
from ..config import GeneratorQuantities


# 预警类型
ALERT_TYPES = [
    "data_quality",      # 数据质量
    "etl_failure",       # ETL失败
    "data_anomaly",      # 数据异常
    "performance",       # 性能
    "storage",           # 存储
    "permission",        # 权限
    "system",            # 系统
]

# 预警级别
ALERT_LEVELS = [
    "critical",  # 严重
    "warning",   # 警告
    "info",      # 信息
]

# 预警规则模板
ALERT_RULE_TEMPLATES = {
    "data_quality": [
        {"name": "空值率检测", "condition": "null_rate > 0.5", "description": "检测字段空值率超过阈值"},
        {"name": "数据一致性检查", "condition": "count_mismatch > 100", "description": "源表和目标表行数不一致"},
        {"name": "数据新鲜度检测", "condition": "update_delay > 3600", "description": "数据更新延迟超过阈值"},
    ],
    "etl_failure": [
        {"name": "ETL任务失败告警", "condition": "task_status = 'failed'", "description": "ETL任务执行失败"},
        {"name": "ETL超时告警", "condition": "duration > 7200", "description": "ETL任务执行超过2小时"},
    ],
    "data_anomaly": [
        {"name": "数据量异常检测", "condition": "row_count < expected * 0.5", "description": "数据量突降告警"},
        {"name": "数值异常检测", "condition": "value > mean + 3*std", "description": "检测数值异常点"},
    ],
    "performance": [
        {"name": "查询慢告警", "condition": "query_time > 60", "description": "查询执行时间超过阈值"},
        {"name": "连接数告警", "condition": "connections > 1000", "description": "数据库连接数过多"},
    ],
    "storage": [
        {"name": "磁盘空间告警", "condition": "disk_usage > 0.8", "description": "磁盘使用率超过80%"},
    ],
    "permission": [
        {"name": "权限变更告警", "condition": "permission_changed = true", "description": "检测到权限变更"},
    ],
    "system": [
        {"name": "服务可用性告警", "condition": "service_down = true", "description": "检测服务不可用"},
        {"name": "API错误率告警", "condition": "error_rate > 0.05", "description": "API错误率超过5%"},
    ],
}


class AlertGenerator(BaseGenerator):
    """
    预警规则生成器

    生成预警规则和历史记录
    """

    def __init__(self, config: GeneratorQuantities = None, storage_manager=None):
        super().__init__(config, storage_manager)
        self.quantities = config or GeneratorQuantities()

    def generate(self) -> Dict[str, List[Any]]:
        """
        生成所有预警数据

        Returns:
            包含alert_rules, alert_history的字典
        """
        self.log("Generating alert rules and history...", "info")

        # 生成预警规则
        alert_rules = self._generate_alert_rules()
        self.store_data("alert_rules", alert_rules)

        # 生成预警历史
        alert_history = self._generate_alert_history(alert_rules)
        self.store_data("alert_history", alert_history)

        self.log(
            f"Generated {len(alert_rules)} alert rules, {len(alert_history)} history records",
            "success"
        )

        return self.get_all_data()

    def _generate_alert_rules(self) -> List[Dict[str, Any]]:
        """生成预警规则"""
        rules = []

        # 选择7种不同类型的预警
        selected_types = random.sample(ALERT_TYPES, min(len(ALERT_TYPES), 7))

        for i, alert_type in enumerate(selected_types):
            templates = ALERT_RULE_TEMPLATES.get(alert_type, [{}])
            template = templates[0] if templates else {}

            # 预警级别权重
            level_weights = ["warning", "critical", "info"]
            level = random.choices(level_weights, weights=[0.5, 0.3, 0.2])[0]

            # 获取监控对象
            tables = self._get_tables_for_alert()
            table = random.choice(tables) if tables else None

            rule = {
                "rule_id": generate_id("rule_", 8),
                "rule_name": template.get("name", f"{alert_type}_rule_{i+1}"),
                "rule_code": f"RULE_{i+1:03d}",
                "alert_type": alert_type,
                "alert_level": level,
                "description": template.get("description", f"{alert_type}预警规则"),
                # 监控配置
                "target_type": random.choice(["table", "column", "etl_task", "system", "api"]),
                "target_id": table["table_id"] if table else None,
                "target_name": table["table_name"] if table else "system",
                "condition": template.get("condition", "value > threshold"),
                "threshold": random.randint(50, 100),
                "check_interval": random.choice([300, 600, 1800, 3600]),
                # 通知配置
                "notification_channels": random.sample([
                    "email", "sms", "webhook", "dingtalk", "slack"
                ], k=random.randint(1, 3)),
                "notification_users": random.choice([
                    "admin", "data-team", "ops-team", "on-call"
                ]),
                # 状态
                "is_enabled": random.random() > 0.1,  # 90%启用
                "status": random.choice(["active", "paused", "testing"]),
                # 统计
                "trigger_count": random.randint(0, 100),
                "last_triggered_at": random_date(7) if random.random() > 0.3 else None,
                # 创建信息
                "created_by": random.choice(["admin", "ops-engineer-01", "data-admin-01"]),
                "created_at": random_date(90),
                "updated_at": random_date(30),
            }
            rules.append(rule)

        return rules

    def _get_tables_for_alert(self) -> List[Dict[str, Any]]:
        """获取用于预警的表"""
        tables = self.get_dependency("tables")
        if tables:
            return tables

        # 生成模拟表
        return [
            {"table_id": generate_id("tbl_", 8), "table_name": f"table_{i}", "database_name": "db"}
            for i in range(1, 11)
        ]

    def _generate_alert_history(self, rules: List[Dict]) -> List[Dict[str, Any]]:
        """生成预警历史"""
        history = []

        for rule in rules:
            # 根据触发次数生成历史
            trigger_count = rule.get("trigger_count", random.randint(5, 20))

            for i in range(trigger_count):
                # 根据预警级别决定处理状态
                if rule["alert_level"] == "critical":
                    status_weights = ["resolved", "resolved", "pending", "acknowledged"]
                else:
                    status_weights = ["resolved", "resolved", "resolved", "pending"]

                status = random.choice(status_weights)

                # 生成时间（越近的越多）
                days_ago = random.randint(0, 60)
                triggered_at = random_date(days_ago)

                # 根据状态计算结束时间
                if status == "resolved":
                    resolved_at = triggered_at + timedelta(
                        minutes=random.randint(5, 120)
                    )
                else:
                    resolved_at = None

                # 生成告警详情
                detail = self._generate_alert_detail(rule)

                record = {
                    "history_id": generate_id("alert_", 8),
                    "rule_id": rule["rule_id"],
                    "alert_type": rule["alert_type"],
                    "alert_level": rule["alert_level"],
                    "status": status,
                    # 触发信息
                    "triggered_at": triggered_at,
                    "resolved_at": resolved_at,
                    "duration_minutes": (
                        int((resolved_at - triggered_at).total_seconds() / 60)
                        if resolved_at else None
                    ),
                    # 详情
                    "message": detail["message"],
                    "value": detail["value"],
                    "threshold": rule["threshold"],
                    # 处理信息
                    "handled_by": random.choice(["admin", "ops-engineer-01", None]) if status == "resolved" else None,
                    "handle_note": random.choice([
                        "已修复配置",
                        "误报，已调整阈值",
                        "已忽略",
                        "已通知相关团队",
                        None,
                    ]) if status == "resolved" else None,
                    # 通知信息
                    "notified": random.random() > 0.2,  # 80%已通知
                    "notification_sent_at": triggered_at + timedelta(seconds=30) if random.random() > 0.2 else None,
                }
                history.append(record)

        # 按时间排序
        history.sort(key=lambda x: x["triggered_at"], reverse=True)

        return history

    def _generate_alert_detail(self, rule: Dict) -> Dict[str, Any]:
        """生成告警详情"""
        alert_type = rule["alert_type"]

        if alert_type == "data_quality":
            return {
                "message": f"表 {rule['target_name']} 空值率超过阈值 {rule['threshold']}%",
                "value": round(rule['threshold'] + random.uniform(5, 30), 2),
            }
        elif alert_type == "etl_failure":
            return {
                "message": f"ETL任务 {rule['target_name']} 执行失败",
                "value": 1,
            }
        elif alert_type == "data_anomaly":
            return {
                "message": f"表 {rule['target_name']} 数据量异常下降",
                "value": round(random.uniform(30, 50), 2),
            }
        elif alert_type == "performance":
            return {
                "message": f"查询执行时间 {random.randint(60, 300)}秒超过阈值",
                "value": random.randint(60, 300),
            }
        elif alert_type == "storage":
            return {
                "message": f"磁盘使用率 {round(random.uniform(80, 95), 2)}% 超过阈值",
                "value": round(random.uniform(80, 95), 2),
            }
        else:
            return {
                "message": f"{rule['rule_name']} 触发告警",
                "value": round(rule['threshold'] + random.uniform(5, 20), 2),
            }

    def get_alert_summary(self) -> Dict[str, int]:
        """获取告警统计摘要"""
        history = self.get_data("alert_history")

        summary = {
            "total": len(history),
            "critical": 0,
            "warning": 0,
            "info": 0,
            "resolved": 0,
            "pending": 0,
        }

        for record in history:
            level = record.get("alert_level")
            status = record.get("status")

            if level in summary:
                summary[level] += 1
            if status == "resolved":
                summary["resolved"] += 1
            elif status == "pending":
                summary["pending"] += 1

        return summary

    def save(self):
        """保存到数据库"""
        if not self.storage:
            self.log("No storage manager, skipping save", "warning")
            return

        self.log("Saving alert rules to database...", "info")

        # 保存预警规则
        alert_rules = self.get_data("alert_rules")
        if alert_rules and self.storage.table_exists("alert_rules"):
            self.storage.batch_insert(
                "alert_rules",
                ["rule_id", "rule_name", "rule_code", "alert_type", "alert_level",
                 "description", "target_type", "target_id", "target_name", "condition",
                 "threshold", "check_interval", "notification_channels", "notification_users",
                 "is_enabled", "status", "trigger_count", "last_triggered_at",
                 "created_by", "created_at", "updated_at"],
                alert_rules,
                idempotent=True,
                idempotent_columns=["rule_id"]
            )
            self.log(f"Saved {len(alert_rules)} alert rules", "success")

        # 保存预警历史
        alert_history = self.get_data("alert_history")
        if alert_history and self.storage.table_exists("alert_history"):
            self.storage.batch_insert(
                "alert_history",
                ["history_id", "rule_id", "alert_type", "alert_level", "status",
                 "triggered_at", "resolved_at", "duration_minutes", "message", "value",
                 "threshold", "handled_by", "handle_note", "notified", "notification_sent_at"],
                alert_history,
                idempotent=True,
                idempotent_columns=["history_id"]
            )
            self.log(f"Saved {len(alert_history)} alert history records", "success")

    def cleanup(self):
        """清理生成的数据"""
        if not self.storage:
            return

        self.log("Cleaning up alert data...", "info")

        if self.storage.table_exists("alert_history"):
            self.storage.cleanup_by_prefix("alert_history", "history_id", "alert_")

        if self.storage.table_exists("alert_rules"):
            self.storage.cleanup_by_prefix("alert_rules", "rule_id", "rule_")


def generate_alert_data(config: GeneratorQuantities = None) -> Dict[str, List[Any]]:
    """
    便捷函数：生成预警数据

    Args:
        config: 生成配置

    Returns:
        预警数据字典
    """
    generator = AlertGenerator(config)
    return generator.generate()
