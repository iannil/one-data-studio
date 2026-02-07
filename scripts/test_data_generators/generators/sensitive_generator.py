"""
敏感数据扫描和脱敏规则生成器

生成：
- 敏感数据扫描任务（5个任务）
- 敏感数据扫描结果（75条结果）
- 脱敏规则（10条规则）
"""

import random
from datetime import datetime, timedelta
from typing import Any, Dict, List

from ..base import (
    BaseGenerator, SensitivityTypes, SensitivityLevels,
    generate_id, random_date, mask_phone, mask_id_card,
    mask_bank_card, mask_email, hash_password
)
from ..config import GeneratorQuantities, SENSITIVE_PATTERNS


# 脱敏策略
MASKING_STRATEGIES = {
    "partial_mask": "部分掩码",
    "full_mask": "完全掩码",
    "hash": "哈希加密",
    "encrypt": "AES加密",
    "nullify": "置空",
    "fixed_value": "固定值替换",
}


class SensitiveGenerator(BaseGenerator):
    """
    敏感数据生成器

    生成敏感数据扫描任务、结果和脱敏规则
    """

    def __init__(self, config: GeneratorQuantities = None, storage_manager=None):
        super().__init__(config, storage_manager)
        self.quantities = config or GeneratorQuantities()

    def generate(self) -> Dict[str, List[Any]]:
        """
        生成所有敏感数据相关数据

        Returns:
            包含scan_tasks, scan_results, masking_rules的字典
        """
        self.log("Generating sensitive data scans and masking rules...", "info")

        # 生成敏感数据扫描任务
        scan_tasks = self._generate_scan_tasks()
        self.store_data("scan_tasks", scan_tasks)

        # 生成敏感数据扫描结果
        scan_results = self._generate_scan_results(scan_tasks)
        self.store_data("scan_results", scan_results)

        # 生成脱敏规则
        masking_rules = self._generate_masking_rules()
        self.store_data("masking_rules", masking_rules)

        self.log(
            f"Generated {len(scan_tasks)} scan tasks, {len(scan_results)} scan results, "
            f"{len(masking_rules)} masking rules",
            "success"
        )

        return self.get_all_data()

    def _generate_scan_tasks(self) -> List[Dict[str, Any]]:
        """生成敏感数据扫描任务"""
        tasks = []

        task_names = [
            "用户表敏感数据扫描",
            "订单表敏感数据扫描",
            "交易表敏感数据扫描",
            "全库敏感数据扫描",
            "日志表敏感数据扫描",
        ]

        status_choices = ["completed", "running", "completed", "completed", "pending"]

        for i, (name, status) in enumerate(zip(task_names, status_choices)):
            # 获取表数据（从依赖或生成）
            tables = self._get_tables_for_scan()
            table_count = len(tables)

            # 根据状态决定时间
            created_at = random_date(60)
            if status == "completed":
                started_at = created_at + timedelta(minutes=random.randint(1, 60))
                finished_at = started_at + timedelta(minutes=random.randint(10, 120))
            elif status == "running":
                started_at = random_date(1)
                finished_at = None
            else:
                started_at = None
                finished_at = None

            task = {
                "task_id": generate_id("scan_", 8),
                "name": name,
                "description": f"扫描数据表中的敏感字段，包括手机号、身份证、银行卡等",
                "status": status,
                "scan_scope": random.choice(["selected_tables", "all_tables", "selected_databases"]),
                "table_count": table_count,
                "column_count": table_count * random.randint(8, 15),
                "sensitive_column_count": random.randint(3, 10),
                "started_at": started_at,
                "finished_at": finished_at,
                "created_by": random.choice(["data-admin-01", "data-admin-02"]),
                "created_at": created_at,
                "updated_at": random_date(30),
            }
            tasks.append(task)

        return tasks

    def _get_tables_for_scan(self) -> List[Dict[str, Any]]:
        """获取用于扫描的表"""
        # 尝试从依赖获取
        tables = self.get_dependency("tables")
        if tables:
            return random.sample(tables, min(len(tables), 20))

        # 生成模拟表
        return [
            {"table_id": f"tbl_{i:04d}", "table_name": f"table_{i}", "database_name": "db_test"}
            for i in range(1, 21)
        ]

    def _generate_scan_results(self, tasks: List[Dict]) -> List[Dict[str, Any]]:
        """生成敏感数据扫描结果"""
        results = []

        # 敏感类型和对应的列名
        sensitive_configs = [
            (SensitivityTypes.PHONE, ["phone", "mobile", "telephone", "contact_phone"], 20),
            (SensitivityTypes.EMAIL, ["email", "mail", "email_address"], 25),
            (SensitivityTypes.ID_CARD, ["id_card", "idcard", "identity_card"], 15),
            (SensitivityTypes.BANK_CARD, ["bank_card", "card_number", "account_number"], 10),
            (SensitivityTypes.PASSWORD, ["password", "passwd", "pwd"], 5),
        ]

        tables = self._get_tables_for_scan()
        result_id = 1

        for task in tasks:
            if task["status"] != "completed":
                continue

            # 为每个任务生成扫描结果
            for sens_type, col_names, count in sensitive_configs:
                for i in range(min(count // len(tasks), 5)):
                    table = random.choice(tables)
                    col_name = random.choice(col_names)

                    # 根据类型确定敏感级别
                    if sens_type in [SensitivityTypes.ID_CARD, SensitivityTypes.BANK_CARD, SensitivityTypes.PASSWORD]:
                        sens_level = SensitivityLevels.RESTRICTED
                    elif sens_type in [SensitivityTypes.PHONE, SensitivityTypes.EMAIL]:
                        sens_level = SensitivityLevels.CONFIDENTIAL
                    else:
                        sens_level = SensitivityLevels.INTERNAL

                    result = {
                        "result_id": generate_id("sres_", 8),
                        "task_id": task["task_id"],
                        "table_id": table["table_id"],
                        "table_name": table["table_name"],
                        "database_name": table["database_name"],
                        "column_name": col_name,
                        "sensitive_type": sens_type,
                        "sensitivity_level": sens_level,
                        "confidence": random.randint(75, 100),
                        "sample_count": random.randint(100, 10000),
                        "matched_count": random.randint(50, 9000),
                        "detection_method": random.choice(["column_name", "content_sample", "ai_inference"]),
                        "suggestion": self._get_suggestion(sens_type),
                        "created_at": task["finished_at"] or random_date(30),
                    }
                    results.append(result)
                    result_id += 1

        return results

    def _get_suggestion(self, sensitive_type: str) -> str:
        """获取处理建议"""
        suggestions = {
            SensitivityTypes.PHONE: "建议使用部分掩码脱敏，保留前3后4位",
            SensitivityTypes.EMAIL: "建议使用部分掩码脱敏，保留首字母和域名",
            SensitivityTypes.ID_CARD: "必须使用AES加密或哈希脱敏",
            SensitivityTypes.BANK_CARD: "必须使用AES加密或哈希脱敏",
            SensitivityTypes.PASSWORD: "必须使用SHA-256或更强哈希算法",
            SensitivityTypes.ADDRESS: "建议部分掩码或区域化处理",
            SensitivityTypes.NAME: "建议部分掩码，仅保留姓氏",
        }
        return suggestions.get(sensitive_type, "建议根据业务需求选择合适的脱敏方式")

    def _generate_masking_rules(self) -> List[Dict[str, Any]]:
        """生成脱敏规则"""
        rules = []

        rule_configs = [
            {
                "name": "手机号脱敏规则",
                "column_pattern": "phone",
                "sensitive_type": SensitivityTypes.PHONE,
                "strategy": "partial_mask",
                "format": "3***4",
                "example": "138****1234",
            },
            {
                "name": "身份证脱敏规则",
                "column_pattern": "id_card",
                "sensitive_type": SensitivityTypes.ID_CARD,
                "strategy": "partial_mask",
                "format": "6***4",
                "example": "110101****1234",
            },
            {
                "name": "银行卡脱敏规则",
                "column_pattern": "bank_card",
                "sensitive_type": SensitivityTypes.BANK_CARD,
                "strategy": "partial_mask",
                "format": "4***4",
                "example": "6222****1234",
            },
            {
                "name": "邮箱脱敏规则",
                "column_pattern": "email",
                "sensitive_type": SensitivityTypes.EMAIL,
                "strategy": "partial_mask",
                "format": "1***@domain",
                "example": "t***@example.com",
            },
            {
                "name": "密码哈希规则",
                "column_pattern": "password",
                "sensitive_type": SensitivityTypes.PASSWORD,
                "strategy": "hash",
                "algorithm": "sha256",
                "example": "5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8",
            },
            {
                "name": "姓名脱敏规则",
                "column_pattern": "name",
                "sensitive_type": "name",
                "strategy": "partial_mask",
                "format": "1*",
                "example": "张*",
            },
            {
                "name": "地址脱敏规则",
                "column_pattern": "address",
                "sensitive_type": "address",
                "strategy": "partial_mask",
                "format": "区域",
                "example": "北京市朝阳区***",
            },
            {
                "name": "手机号加密规则",
                "column_pattern": "phone_encrypted",
                "sensitive_type": SensitivityTypes.PHONE,
                "strategy": "encrypt",
                "algorithm": "aes-256",
                "example": "encrypted_blob",
            },
            {
                "name": "通用敏感字段置空规则",
                "column_pattern": "sensitive_*",
                "sensitive_type": "other",
                "strategy": "nullify",
                "format": None,
                "example": "NULL",
            },
            {
                "name": "测试数据固定值规则",
                "column_pattern": "test_*",
                "sensitive_type": "other",
                "strategy": "fixed_value",
                "format": "********",
                "example": "********",
            },
        ]

        for i, config in enumerate(rule_configs):
            rule = {
                "rule_id": generate_id("mask_", 8),
                "rule_name": config["name"],
                "description": f"对{config['sensitive_type']}类型字段使用{config['strategy']}策略进行脱敏处理",
                "column_pattern": config["column_pattern"],
                "sensitive_type": config["sensitive_type"],
                "strategy": config["strategy"],
                "format_pattern": config.get("format"),
                "algorithm": config.get("algorithm"),
                "example_before": self._get_example_before(config["sensitive_type"]),
                "example_after": config["example"],
                "is_enabled": random.random() > 0.1,  # 90%启用
                "priority": random.randint(1, 10),
                "created_by": random.choice(["data-admin-01", "data-admin-02"]),
                "created_at": random_date(90),
                "updated_at": random_date(30),
            }
            rules.append(rule)

        return rules

    def _get_example_before(self, sensitive_type: str) -> str:
        """获取脱敏前的示例值"""
        examples = {
            SensitivityTypes.PHONE: "13812345678",
            SensitivityTypes.EMAIL: "test@example.com",
            SensitivityTypes.ID_CARD: "110101199001011234",
            SensitivityTypes.BANK_CARD: "6222021234567890123",
            SensitivityTypes.PASSWORD: "password123",
            "name": "张三",
            "address": "北京市朝阳区某某街道123号",
        }
        return examples.get(sensitive_type, "原始值")

    def get_sensitive_summary(self) -> Dict[str, int]:
        """获取敏感数据统计摘要"""
        results = self.get_data("scan_results")

        summary = {
            "total": len(results),
            "phone": 0,
            "email": 0,
            "id_card": 0,
            "bank_card": 0,
            "password": 0,
        }

        for result in results:
            sens_type = result.get("sensitive_type")
            if sens_type in summary:
                summary[sens_type] += 1

        return summary

    def save(self):
        """保存到数据库"""
        if not self.storage:
            self.log("No storage manager, skipping save", "warning")
            return

        self.log("Saving sensitive data to database...", "info")

        # 保存扫描任务
        scan_tasks = self.get_data("scan_tasks")
        if scan_tasks and self.storage.table_exists("sensitivity_scan_tasks"):
            self.storage.batch_insert(
                "sensitivity_scan_tasks",
                ["task_id", "name", "description", "status", "scan_scope", "table_count",
                 "column_count", "sensitive_column_count", "started_at", "finished_at",
                 "created_by", "created_at", "updated_at"],
                scan_tasks,
                idempotent=True,
                idempotent_columns=["task_id"]
            )
            self.log(f"Saved {len(scan_tasks)} scan tasks", "success")

        # 保存扫描结果
        scan_results = self.get_data("scan_results")
        if scan_results and self.storage.table_exists("sensitivity_scan_results"):
            self.storage.batch_insert(
                "sensitivity_scan_results",
                ["result_id", "task_id", "table_id", "table_name", "database_name",
                 "column_name", "sensitive_type", "sensitivity_level", "confidence",
                 "sample_count", "matched_count", "detection_method", "suggestion",
                 "created_at"],
                scan_results,
                idempotent=True,
                idempotent_columns=["result_id"]
            )
            self.log(f"Saved {len(scan_results)} scan results", "success")

        # 保存脱敏规则
        masking_rules = self.get_data("masking_rules")
        if masking_rules and self.storage.table_exists("masking_rules"):
            self.storage.batch_insert(
                "masking_rules",
                ["rule_id", "rule_name", "description", "column_pattern", "sensitive_type",
                 "strategy", "format_pattern", "algorithm", "example_before", "example_after",
                 "is_enabled", "priority", "created_by", "created_at", "updated_at"],
                masking_rules,
                idempotent=True,
                idempotent_columns=["rule_id"]
            )
            self.log(f"Saved {len(masking_rules)} masking rules", "success")

    def cleanup(self):
        """清理生成的数据"""
        if not self.storage:
            return

        self.log("Cleaning up sensitive data...", "info")

        for table, id_col in [
            ("sensitivity_scan_results", "result_id"),
            ("sensitivity_scan_tasks", "task_id"),
            ("masking_rules", "rule_id"),
        ]:
            if self.storage.table_exists(table):
                self.storage.cleanup_by_prefix(table, id_col, id_col[:3] + "_")


def generate_sensitive_data(config: GeneratorQuantities = None) -> Dict[str, List[Any]]:
    """
    便捷函数：生成敏感数据

    Args:
        config: 生成配置

    Returns:
        敏感数据字典
    """
    generator = SensitiveGenerator(config)
    return generator.generate()
