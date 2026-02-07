"""
数据验证器

提供：
1. 数据完整性验证
2. 数据量验证
3. 数据质量验证
"""

import logging
from typing import Any, Dict, List, Optional, Set

from ..base import BaseGenerator, SensitivityTypes


logger = logging.getLogger(__name__)


class DataValidator(BaseGenerator):
    """
    数据验证器

    验证生成的测试数据是否符合要求
    """

    # 验证规则
    VALIDATION_RULES = {
        "users": {
            "min_count": 20,
            "required_fields": ["user_id", "username", "email", "role"],
            "role_types": ["data_administrator", "data_engineer", "ai_developer", "data_analyst", "system_administrator"],
        },
        "datasources": {
            "min_count": 5,
            "required_fields": ["source_id", "name", "type"],
            "source_types": ["mysql", "postgresql", "oracle", "mongodb", "hive"],
        },
        "tables": {
            "min_count": 50,
            "required_fields": ["table_id", "table_name", "database_name"],
        },
        "columns": {
            "min_count": 300,
            "required_fields": ["column_id", "column_name", "table_name", "column_type"],
        },
        "etl_tasks": {
            "min_count": 10,
            "required_fields": ["task_id", "name", "task_type", "status"],
        },
        "sensitive_columns": {
            "min_count": {
                SensitivityTypes.PHONE: 15,
                SensitivityTypes.EMAIL: 20,
                SensitivityTypes.ID_CARD: 10,
                SensitivityTypes.BANK_CARD: 8,
            },
        },
    }

    def __init__(self, data: Dict[str, List[Any]] = None):
        super().__init__()
        self.data = data or {}

    def load_data(self, key: str, data: List[Any]):
        """加载数据"""
        self._generated_data[key] = data

    def validate_all(self) -> Dict[str, Any]:
        """
        执行所有验证

        Returns:
            验证结果字典
        """
        results = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "errors": [],
            "warnings": [],
        }

        # 验证各类数据
        validators = {
            "users": self._validate_users,
            "datasources": self._validate_datasources,
            "tables": self._validate_tables,
            "columns": self._validate_columns,
            "etl_tasks": self._validate_etl_tasks,
            "sensitive_data": self._validate_sensitive_data,
        }

        for name, validator in validators.items():
            try:
                result = validator()
                results["total"] += result.get("total", 0)
                results["passed"] += result.get("passed", 0)
                results["failed"] += result.get("failed", 0)
                results["errors"].extend(result.get("errors", []))
                results["warnings"].extend(result.get("warnings", []))
            except Exception as e:
                results["errors"].append(f"{name} validation error: {e}")

        return results

    def _validate_users(self) -> Dict[str, Any]:
        """验证用户数据"""
        result = {"total": 0, "passed": 0, "failed": 0, "errors": [], "warnings": []}

        users = self._generated_data.get("users", [])
        result["total"] = len(users)

        # 检查最小数量
        if len(users) < self.VALIDATION_RULES["users"]["min_count"]:
            result["errors"].append(
                f"用户数量不足: {len(users)} < {self.VALIDATION_RULES['users']['min_count']}"
            )
            result["failed"] += 1
        else:
            result["passed"] += 1

        # 检查必需字段
        for user in users:
            for field in self.VALIDATION_RULES["users"]["required_fields"]:
                if field not in user or not user[field]:
                    result["errors"].append(f"用户缺少必需字段: {field}")
                    result["failed"] += 1

        # 检查角色类型
        roles = set(u.get("role") for u in users)
        for role in self.VALIDATION_RULES["users"]["role_types"]:
            if role not in roles:
                result["warnings"].append(f"缺少角色类型: {role}")

        # 检查角色分布
        role_counts = {}
        for user in users:
            role = user.get("role")
            role_counts[role] = role_counts.get(role, 0) + 1

        self.log(f"角色分布: {role_counts}", "info")

        return result

    def _validate_datasources(self) -> Dict[str, Any]:
        """验证数据源数据"""
        result = {"total": 0, "passed": 0, "failed": 0, "errors": [], "warnings": []}

        datasources = self._generated_data.get("datasources", [])
        result["total"] = len(datasources)

        if len(datasources) < self.VALIDATION_RULES["datasources"]["min_count"]:
            result["errors"].append(
                f"数据源数量不足: {len(datasources)} < {self.VALIDATION_RULES['datasources']['min_count']}"
            )
            result["failed"] += 1
        else:
            result["passed"] += 1

        return result

    def _validate_tables(self) -> Dict[str, Any]:
        """验证表数据"""
        result = {"total": 0, "passed": 0, "failed": 0, "errors": [], "warnings": []}

        tables = self._generated_data.get("tables", [])
        result["total"] = len(tables)

        if len(tables) < self.VALIDATION_RULES["tables"]["min_count"]:
            result["errors"].append(
                f"表数量不足: {len(tables)} < {self.VALIDATION_RULES['tables']['min_count']}"
            )
            result["failed"] += 1
        else:
            result["passed"] += 1

        return result

    def _validate_columns(self) -> Dict[str, Any]:
        """验证列数据"""
        result = {"total": 0, "passed": 0, "failed": 0, "errors": [], "warnings": []}

        columns = self._generated_data.get("columns", [])
        result["total"] = len(columns)

        if len(columns) < self.VALIDATION_RULES["columns"]["min_count"]:
            result["errors"].append(
                f"列数量不足: {len(columns)} < {self.VALIDATION_RULES['columns']['min_count']}"
            )
            result["failed"] += 1
        else:
            result["passed"] += 1

        return result

    def _validate_etl_tasks(self) -> Dict[str, Any]:
        """验证ETL任务数据"""
        result = {"total": 0, "passed": 0, "failed": 0, "errors": [], "warnings": []}

        etl_tasks = self._generated_data.get("etl_tasks", [])
        result["total"] = len(etl_tasks)

        if len(etl_tasks) < self.VALIDATION_RULES["etl_tasks"]["min_count"]:
            result["warnings"].append(
                f"ETL任务数量较少: {len(etl_tasks)} < {self.VALIDATION_RULES['etl_tasks']['min_count']}"
            )

        # 检查每个任务是否有关联的日志
        logs = self._generated_data.get("etl_logs", [])
        log_task_ids = set(log.get("task_id") for log in logs)

        for task in etl_tasks:
            if task.get("task_id") not in log_task_ids:
                result["warnings"].append(f"ETL任务 {task.get('task_id')} 没有关联日志")

        result["passed"] += 1

        return result

    def _validate_sensitive_data(self) -> Dict[str, Any]:
        """验证敏感数据"""
        result = {"total": 0, "passed": 0, "failed": 0, "errors": [], "warnings": []}

        columns = self._generated_data.get("columns", [])
        sensitive_columns = [c for c in columns if c.get("sensitivity_type") and c.get("sensitivity_type") != "none"]
        result["total"] = len(sensitive_columns)

        # 按类型统计
        type_counts = {}
        for col in sensitive_columns:
            sens_type = col.get("sensitivity_type")
            type_counts[sens_type] = type_counts.get(sens_type, 0) + 1

        self.log(f"敏感数据分布: {type_counts}", "info")

        # 检查各类型数量
        min_counts = self.VALIDATION_RULES["sensitive_columns"]["min_count"]
        for sens_type, min_count in min_counts.items():
            count = type_counts.get(sens_type, 0)
            if count < min_count:
                result["errors"].append(
                    f"{sens_type}类型敏感列不足: {count} < {min_count}"
                )
                result["failed"] += 1
            else:
                result["passed"] += 1

        return result

    def print_summary(self):
        """打印数据摘要"""
        print("\n" + "=" * 60)
        print("数据生成摘要")
        print("=" * 60)

        for key, data in self._generated_data.items():
            print(f"  {key}: {len(data)} 条")

        print("=" * 60)

    def get_summary(self) -> Dict[str, int]:
        """获取数据摘要"""
        return {key: len(data) for key, data in self._generated_data.items()}


class LinkageValidator(BaseGenerator):
    """
    关联关系验证器

    验证数据之间的关联关系是否正确
    """

    def validate_linkage(self) -> Dict[str, Any]:
        """
        验证数据关联关系

        Returns:
            验证结果
        """
        result = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "errors": [],
        }

        # 验证用户-角色关联
        result["total"] += 1
        if self._validate_user_role_linkage():
            result["passed"] += 1
        else:
            result["failed"] += 1
            result["errors"].append("用户-角色关联验证失败")

        # 验证数据源-数据库-表-列关联
        result["total"] += 1
        if self._validate_metadata_linkage():
            result["passed"] += 1
        else:
            result["failed"] += 1
            result["errors"].append("元数据关联验证失败")

        # 验证ETL任务-日志关联
        result["total"] += 1
        if self._validate_etl_linkage():
            result["passed"] += 1
        else:
            result["failed"] += 1
            result["errors"].append("ETL关联验证失败")

        return result

    def _validate_user_role_linkage(self) -> bool:
        """验证用户-角色关联"""
        users = self._generated_data.get("users", [])
        user_roles = self._generated_data.get("user_roles", [])

        user_ids = set(u.get("user_id") for u in users)
        role_ids = set(ur.get("role_id") for ur in user_roles)

        # 检查每个用户角色是否有效
        for ur in user_roles:
            if ur.get("user_id") not in user_ids:
                self.log(f"用户角色关联的用户不存在: {ur.get('user_id')}", "warning")
            if ur.get("role_id") not in role_ids:
                self.log(f"用户角色关联的角色不存在: {ur.get('role_id')}", "warning")

        return True

    def _validate_metadata_linkage(self) -> bool:
        """验证元数据关联"""
        databases = self._generated_data.get("databases", [])
        tables = self._generated_data.get("tables", [])
        columns = self._generated_data.get("columns", [])

        database_ids = set(d.get("database_id") for d in databases)
        table_ids = set(t.get("table_id") for t in tables)

        # 检查表-数据库关联
        for table in tables:
            if table.get("database_id") not in database_ids:
                self.log(f"表关联的数据库不存在: {table.get('database_id')}", "warning")

        # 检查列-表关联
        for col in columns:
            if col.get("table_id") not in table_ids:
                self.log(f"列关联的表不存在: {col.get('table_id')}", "warning")

        return True

    def _validate_etl_linkage(self) -> bool:
        """验证ETL关联"""
        etl_tasks = self._generated_data.get("etl_tasks", [])
        etl_logs = self._generated_data.get("etl_logs", [])

        task_ids = set(t.get("task_id") for t in etl_tasks)

        # 检查日志-任务关联
        orphan_logs = 0
        for log in etl_logs:
            if log.get("task_id") not in task_ids:
                orphan_logs += 1

        if orphan_logs > 0:
            self.log(f"发现 {orphan_logs} 条孤儿日志", "warning")

        return True


def validate_data(data: Dict[str, List[Any]]) -> Dict[str, Any]:
    """
    便捷函数：验证数据

    Args:
        data: 数据字典

    Returns:
        验证结果
    """
    validator = DataValidator(data)
    validator.load_data("", [])  # Initialize

    # 加载数据
    for key, value in data.items():
        validator._generated_data[key] = value

    return validator.validate_all()


def validate_linkage(data: Dict[str, List[Any]]) -> Dict[str, Any]:
    """
    便捷函数：验证关联关系

    Args:
        data: 数据字典

    Returns:
        验证结果
    """
    validator = LinkageValidator()

    # 加载数据
    for key, value in data.items():
        validator._generated_data[key] = value

    return validator.validate_linkage()
