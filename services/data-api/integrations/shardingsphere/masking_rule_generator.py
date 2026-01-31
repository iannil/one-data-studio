"""
ShardingSphere 脱敏规则生成器

将敏感扫描结果转换为 ShardingSphere 脱敏规则 (DistSQL 或 YAML 格式)。
"""
import logging
from typing import Dict, Any, List, Optional


logger = logging.getLogger(__name__)


class MaskingRuleGenerator:
    """
    脱敏规则生成器

    将敏感数据扫描结果转换为 ShardingSphere 支持的脱敏规则。
    """

    # 敏感类型 → ShardingSphere 脱敏算法映射
    ALGORITHM_MAP = {
        # 手机号: 保留前 3 位和后 4 位
        "phone": (
            "MASK_FIRST_N_LAST_M",
            {"first-n": "3", "last-m": "4", "replace-char": "*"}
        ),
        "mobile": (
            "MASK_FIRST_N_LAST_M",
            {"first-n": "3", "last-m": "4", "replace-char": "*"}
        ),
        # 邮箱: @ 前的字符脱敏
        "email": (
            "MASK_BEFORE_SPECIAL_CHARS",
            {"special-chars": "@", "replace-char": "*"}
        ),
        # 身份证: 保留前 6 位和后 4 位
        "id_card": (
            "MASK_FIRST_N_LAST_M",
            {"first-n": "6", "last-m": "4", "replace-char": "*"}
        ),
        "ssn": (
            "MASK_FIRST_N_LAST_M",
            {"first-n": "6", "last-m": "4", "replace-char": "*"}
        ),
        # 银行卡: 保留前 4 位和后 4 位
        "bank_card": (
            "MASK_FIRST_N_LAST_M",
            {"first-n": "4", "last-m": "4", "replace-char": "*"}
        ),
        "credit_card": (
            "MASK_FIRST_N_LAST_M",
            {"first-n": "4", "last-m": "4", "replace-char": "*"}
        ),
        # 姓名: 保留姓
        "name": (
            "MASK_FIRST_N_LAST_M",
            {"first-n": "1", "last-m": "0", "replace-char": "*"}
        ),
        "person_name": (
            "MASK_FIRST_N_LAST_M",
            {"first-n": "1", "last-m": "0", "replace-char": "*"}
        ),
        # 地址: 保留前 6 个字符
        "address": (
            "MASK_FIRST_N_LAST_M",
            {"first-n": "6", "last-m": "0", "replace-char": "*"}
        ),
        # IP 地址
        "ip_address": (
            "MASK_FIRST_N_LAST_M",
            {"first-n": "0", "last-m": "0", "replace-char": "*"}
        ),
        # 通用: 完全脱敏
        "default": (
            "MD5",
            {}
        ),
    }

    @classmethod
    def get_algorithm(cls, sensitivity_type: str) -> tuple:
        """
        根据敏感类型获取脱敏算法

        Args:
            sensitivity_type: 敏感类型

        Returns:
            (algorithm_type, props) 元组
        """
        sensitivity_type = (sensitivity_type or "").lower().replace("-", "_")
        return cls.ALGORITHM_MAP.get(sensitivity_type, cls.ALGORITHM_MAP["default"])

    @classmethod
    def from_sensitivity_results(
        cls,
        results: List[Dict[str, Any]],
    ) -> Dict[str, Dict[str, Any]]:
        """
        从敏感扫描结果批量生成脱敏规则配置

        Args:
            results: 敏感扫描结果列表，每项应包含:
                - column_name: 列名
                - sensitivity_type / sensitivity_sub_type: 敏感类型
                - sensitivity_level (可选): 敏感级别

        Returns:
            {column_name: {algorithm_type, algorithm_props}} 字典
        """
        rules = {}
        for result in results:
            column_name = result.get("column_name") or result.get("name")
            if not column_name:
                continue

            # 获取敏感类型 (优先使用 sub_type)
            sensitivity_type = (
                result.get("sensitivity_sub_type") or
                result.get("sensitivity_type") or
                result.get("type") or
                "default"
            )

            algorithm_type, algorithm_props = cls.get_algorithm(sensitivity_type)

            rules[column_name] = {
                "algorithm_type": algorithm_type,
                "algorithm_props": algorithm_props,
                "sensitivity_type": sensitivity_type,
            }

        return rules

    @classmethod
    def generate_mask_rule_sql(
        cls,
        database: str,
        table: str,
        rules: Dict[str, Dict[str, Any]],
    ) -> str:
        """
        生成 ShardingSphere 脱敏规则 DistSQL

        Args:
            database: 数据库名
            table: 表名
            rules: {column_name: {algorithm_type, algorithm_props}} 字典

        Returns:
            CREATE MASK RULE 的 DistSQL 语句
        """
        if not rules:
            return ""

        # 构建 DistSQL
        # CREATE MASK RULE table_name (
        #   column_name = (TYPE(NAME='algorithm', PROPERTIES("k1"="v1")))
        # );

        column_defs = []
        for col_name, rule in rules.items():
            alg_type = rule["algorithm_type"]
            alg_props = rule.get("algorithm_props", {})

            if alg_props:
                props_str = ", ".join([f'"{k}"="{v}"' for k, v in alg_props.items()])
                col_def = f'  {col_name} = (TYPE(NAME=\'{alg_type}\', PROPERTIES({props_str})))'
            else:
                col_def = f'  {col_name} = (TYPE(NAME=\'{alg_type}\'))'

            column_defs.append(col_def)

        columns_sql = ",\n".join(column_defs)

        sql = f"""USE {database};

CREATE MASK RULE {table} (
{columns_sql}
);"""

        return sql

    @classmethod
    def generate_drop_rule_sql(cls, database: str, table: str) -> str:
        """
        生成删除脱敏规则的 DistSQL

        Args:
            database: 数据库名
            table: 表名

        Returns:
            DROP MASK RULE 的 DistSQL 语句
        """
        return f"""USE {database};

DROP MASK RULE IF EXISTS {table};"""

    @classmethod
    def generate_show_rules_sql(cls, database: str) -> str:
        """
        生成查看脱敏规则的 DistSQL

        Args:
            database: 数据库名

        Returns:
            SHOW MASK RULES 的 DistSQL 语句
        """
        return f"""USE {database};

SHOW MASK RULES;"""

    @classmethod
    def generate_mask_rule_yaml(
        cls,
        database: str,
        table: str,
        rules: Dict[str, Dict[str, Any]],
    ) -> str:
        """
        生成 ShardingSphere 脱敏规则 YAML 配置

        Args:
            database: 数据库名
            table: 表名
            rules: {column_name: {algorithm_type, algorithm_props}} 字典

        Returns:
            YAML 格式的脱敏规则配置
        """
        if not rules:
            return ""

        # 构建 YAML
        lines = [
            f"# ShardingSphere 脱敏规则配置",
            f"# 数据库: {database}, 表: {table}",
            "",
            "rules:",
            "- !MASK",
            "  tables:",
            f"    {table}:",
            "      columns:",
        ]

        for col_name, rule in rules.items():
            alg_type = rule["algorithm_type"]
            alg_name = f"{table}_{col_name}_mask"

            lines.append(f"        {col_name}:")
            lines.append(f"          maskAlgorithm: {alg_name}")

        lines.append("")
        lines.append("  maskAlgorithms:")

        for col_name, rule in rules.items():
            alg_type = rule["algorithm_type"]
            alg_props = rule.get("algorithm_props", {})
            alg_name = f"{table}_{col_name}_mask"

            lines.append(f"    {alg_name}:")
            lines.append(f"      type: {alg_type}")
            if alg_props:
                lines.append("      props:")
                for k, v in alg_props.items():
                    lines.append(f"        {k}: '{v}'")

        return "\n".join(lines)
