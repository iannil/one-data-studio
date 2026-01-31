"""
QualityRuleType → Great Expectations Expectation 映射

将平台内置的质量规则类型转换为 GE Expectation 参数。
"""

import logging
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# 规则类型 → GE Expectation 名称映射
RULE_TYPE_TO_EXPECTATION: Dict[str, str] = {
    "null_check": "expect_column_values_to_not_be_null",
    "duplicate_check": "expect_column_values_to_be_unique",
    "range_check": "expect_column_values_to_be_between",
    "pattern_check": "expect_column_values_to_match_regex",
    "enum_check": "expect_column_values_to_be_in_set",
    "length_check": "expect_column_value_lengths_to_be_between",
    "uniqueness_check": "expect_column_values_to_be_unique",
    "reference_check": "expect_column_pair_values_to_be_in_set",
}


def is_ge_supported(rule_type: str) -> bool:
    """检查规则类型是否被 GE 支持"""
    return rule_type in RULE_TYPE_TO_EXPECTATION


def build_expectation_kwargs(
    rule_type: str,
    target_column: str,
    config: Dict[str, Any],
    rule_expression: str = "",
) -> Tuple[str, Dict[str, Any]]:
    """
    从 QualityRuleDefinition 构建 GE Expectation 参数

    Args:
        rule_type: 规则类型字符串
        target_column: 目标列名
        config: 规则额外配置
        rule_expression: 规则表达式（如正则）

    Returns:
        (expectation_name, kwargs) 元组
    """
    expectation_name = RULE_TYPE_TO_EXPECTATION.get(rule_type)
    if not expectation_name:
        raise ValueError(f"Unsupported rule type for GE: {rule_type}")

    kwargs: Dict[str, Any] = {"column": target_column}

    if rule_type == "null_check":
        # expect_column_values_to_not_be_null
        mostly = config.get("threshold", 100.0) / 100.0
        if mostly < 1.0:
            kwargs["mostly"] = mostly

    elif rule_type in ("duplicate_check", "uniqueness_check"):
        # expect_column_values_to_be_unique
        pass

    elif rule_type == "range_check":
        # expect_column_values_to_be_between
        if config.get("min_value") is not None:
            kwargs["min_value"] = config["min_value"]
        if config.get("max_value") is not None:
            kwargs["max_value"] = config["max_value"]

    elif rule_type == "pattern_check":
        # expect_column_values_to_match_regex
        kwargs["regex"] = rule_expression or config.get("pattern", ".*")

    elif rule_type == "enum_check":
        # expect_column_values_to_be_in_set
        kwargs["value_set"] = config.get("allowed_values", [])

    elif rule_type == "length_check":
        # expect_column_value_lengths_to_be_between
        if config.get("min_length") is not None:
            kwargs["min_value"] = config["min_length"]
        if config.get("max_length") is not None:
            kwargs["max_value"] = config["max_length"]

    return expectation_name, kwargs
