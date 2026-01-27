"""
AI 缺失值填充服务
Phase 1 P2: 基于字段类型和上下文的智能缺失值填充

功能：
- 分析缺失值模式和分布
- 多种填充策略（统计/规则/LLM）
- 生成可转换为 Kettle 步骤的填充规则
"""

import json
import logging
import math
import os
import re
import requests
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Any, Optional, Tuple, Union
from statistics import mean, median, mode, stdev

logger = logging.getLogger(__name__)

# 配置
CUBE_API_URL = os.getenv("CUBE_API_URL", "http://openai-proxy:8000")
AI_IMPUTATION_MODEL = os.getenv("AI_IMPUTATION_MODEL", "gpt-4o-mini")
AI_IMPUTATION_ENABLED = os.getenv("AI_IMPUTATION_ENABLED", "true").lower() in ("true", "1", "yes")


class ImputationStrategy(str, Enum):
    """填充策略枚举"""
    # 数值型策略
    MEAN = "mean"                    # 均值填充
    MEDIAN = "median"                # 中位数填充
    MODE = "mode"                    # 众数填充
    CONSTANT = "constant"            # 常量填充
    FORWARD_FILL = "forward_fill"    # 前向填充
    BACKWARD_FILL = "backward_fill"  # 后向填充
    INTERPOLATE = "interpolate"      # 线性插值

    # 分类型策略
    MOST_FREQUENT = "most_frequent"  # 最频繁值
    CATEGORY_DEFAULT = "category_default"  # 分类默认值

    # 日期型策略
    DATE_INTERPOLATE = "date_interpolate"  # 日期插值
    DATE_PATTERN = "date_pattern"    # 日期模式推断

    # AI 增强策略
    LLM_INFERENCE = "llm_inference"  # LLM 语义推断
    CORRELATION_BASED = "correlation_based"  # 基于关联字段推断

    # 特殊处理
    DELETE_ROW = "delete_row"        # 删除含缺失值的行
    FLAG_MISSING = "flag_missing"    # 标记为缺失（不填充）


class ColumnType(str, Enum):
    """列类型枚举"""
    NUMERIC = "numeric"
    CATEGORICAL = "categorical"
    DATETIME = "datetime"
    TEXT = "text"
    BOOLEAN = "boolean"
    UNKNOWN = "unknown"


@dataclass
class MissingAnalysis:
    """缺失值分析结果"""
    column_name: str
    column_type: ColumnType
    total_rows: int
    missing_count: int
    missing_percentage: float
    missing_pattern: str  # random, systematic, block

    # 非缺失值统计
    value_stats: Dict[str, Any] = field(default_factory=dict)
    # 样本非缺失值
    sample_values: List[Any] = field(default_factory=list)
    # 缺失位置特征
    missing_positions: List[int] = field(default_factory=list)
    # 关联字段（缺失值与其他字段的关联）
    correlated_columns: List[str] = field(default_factory=list)


@dataclass
class ImputationRule:
    """填充规则"""
    column_name: str
    strategy: ImputationStrategy
    fill_value: Any = None  # 用于常量填充
    parameters: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    reason: str = ""

    # Kettle 配置
    kettle_step_type: str = ""
    kettle_config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ImputationResult:
    """填充结果"""
    column_name: str
    original_missing_count: int
    filled_count: int
    strategy_used: ImputationStrategy
    fill_value_summary: str  # 填充值摘要
    sample_fills: List[Dict[str, Any]] = field(default_factory=list)  # 样本填充记录


# 策略到 Kettle 步骤的映射
STRATEGY_TO_KETTLE = {
    ImputationStrategy.MEAN: {
        "step_type": "IfFieldValueIsNull",
        "description": "使用均值替换空值",
    },
    ImputationStrategy.MEDIAN: {
        "step_type": "IfFieldValueIsNull",
        "description": "使用中位数替换空值",
    },
    ImputationStrategy.MODE: {
        "step_type": "IfFieldValueIsNull",
        "description": "使用众数替换空值",
    },
    ImputationStrategy.CONSTANT: {
        "step_type": "IfFieldValueIsNull",
        "description": "使用常量替换空值",
    },
    ImputationStrategy.MOST_FREQUENT: {
        "step_type": "IfFieldValueIsNull",
        "description": "使用最频繁值替换空值",
    },
    ImputationStrategy.FORWARD_FILL: {
        "step_type": "AnalyticQuery",
        "description": "使用前一个非空值填充",
    },
    ImputationStrategy.BACKWARD_FILL: {
        "step_type": "AnalyticQuery",
        "description": "使用后一个非空值填充",
    },
    ImputationStrategy.DELETE_ROW: {
        "step_type": "FilterRows",
        "description": "过滤掉含缺失值的行",
    },
    ImputationStrategy.FLAG_MISSING: {
        "step_type": "Calculator",
        "description": "添加缺失标记列",
    },
    ImputationStrategy.CORRELATION_BASED: {
        "step_type": "StreamLookup",
        "description": "基于关联字段进行流查找填充",
    },
}


class AIImputationService:
    """AI 缺失值填充服务"""

    def __init__(self, api_url: str = None):
        """
        初始化服务

        Args:
            api_url: LLM API 地址
        """
        self.api_url = api_url or CUBE_API_URL
        self.model = AI_IMPUTATION_MODEL
        self.enabled = AI_IMPUTATION_ENABLED

    def analyze_missing_patterns(
        self,
        data: List[Dict[str, Any]],
        column_name: str,
        column_type: str = None,
    ) -> MissingAnalysis:
        """
        分析缺失值模式

        Args:
            data: 数据列表（字典格式的行）
            column_name: 列名
            column_type: 列类型（可选，会自动推断）

        Returns:
            MissingAnalysis 分析结果
        """
        total_rows = len(data)
        if total_rows == 0:
            return MissingAnalysis(
                column_name=column_name,
                column_type=ColumnType.UNKNOWN,
                total_rows=0,
                missing_count=0,
                missing_percentage=0.0,
                missing_pattern="none",
            )

        # 提取列值和缺失位置
        values = []
        missing_positions = []
        non_null_values = []

        for i, row in enumerate(data):
            val = row.get(column_name)
            values.append(val)
            if val is None or val == "" or (isinstance(val, float) and str(val) == "nan"):
                missing_positions.append(i)
            else:
                non_null_values.append(val)

        missing_count = len(missing_positions)
        missing_percentage = (missing_count / total_rows) * 100 if total_rows > 0 else 0

        # 推断列类型
        inferred_type = self._infer_column_type(non_null_values, column_type)

        # 分析缺失模式
        missing_pattern = self._analyze_missing_pattern(missing_positions, total_rows)

        # 计算值统计
        value_stats = self._compute_value_stats(non_null_values, inferred_type)

        # 样本值
        sample_values = non_null_values[:10] if non_null_values else []

        return MissingAnalysis(
            column_name=column_name,
            column_type=inferred_type,
            total_rows=total_rows,
            missing_count=missing_count,
            missing_percentage=missing_percentage,
            missing_pattern=missing_pattern,
            value_stats=value_stats,
            sample_values=sample_values,
            missing_positions=missing_positions[:100],  # 只保留前100个位置
        )

    def recommend_imputation_strategy(
        self,
        analysis: MissingAnalysis,
        context: Dict[str, Any] = None,
        use_llm: bool = True,
    ) -> ImputationRule:
        """
        推荐填充策略

        Args:
            analysis: 缺失值分析结果
            context: 上下文信息（表名、业务场景等）
            use_llm: 是否使用 LLM 增强

        Returns:
            ImputationRule 填充规则
        """
        # 基于规则的策略推荐
        rule = self._recommend_by_rules(analysis)

        # 使用 LLM 增强
        if use_llm and self.enabled and analysis.missing_percentage > 5:
            try:
                llm_recommendation = self._get_llm_recommendation(analysis, context)
                if llm_recommendation:
                    # 如果 LLM 推荐更合适的策略，使用 LLM 结果
                    if llm_recommendation.get("confidence", 0) > rule.confidence:
                        strategy_str = llm_recommendation.get("strategy", "")
                        try:
                            strategy = ImputationStrategy(strategy_str)
                            rule.strategy = strategy
                            rule.reason = llm_recommendation.get("reason", rule.reason)
                            rule.confidence = llm_recommendation.get("confidence", rule.confidence)
                            if llm_recommendation.get("fill_value"):
                                rule.fill_value = llm_recommendation["fill_value"]
                        except ValueError:
                            pass  # 无效策略，保持原规则
            except Exception as e:
                logger.warning(f"LLM 推荐失败: {e}")

        # 生成 Kettle 配置
        self._generate_kettle_config(rule, analysis)

        return rule

    def impute_values(
        self,
        data: List[Dict[str, Any]],
        column_name: str,
        rule: ImputationRule,
    ) -> tuple[List[Dict[str, Any]], ImputationResult]:
        """
        执行缺失值填充

        Args:
            data: 原始数据
            column_name: 列名
            rule: 填充规则

        Returns:
            (填充后的数据, 填充结果)
        """
        filled_data = [row.copy() for row in data]
        filled_count = 0
        sample_fills = []

        # 获取填充值
        fill_value = self._get_fill_value(data, column_name, rule)

        for i, row in enumerate(filled_data):
            val = row.get(column_name)
            if val is None or val == "" or (isinstance(val, float) and str(val) == "nan"):
                if rule.strategy == ImputationStrategy.DELETE_ROW:
                    continue  # 标记为删除（实际删除在外部处理）
                elif rule.strategy == ImputationStrategy.FLAG_MISSING:
                    row[f"{column_name}_is_missing"] = True
                elif rule.strategy == ImputationStrategy.FORWARD_FILL:
                    # 前向填充
                    for j in range(i - 1, -1, -1):
                        prev_val = filled_data[j].get(column_name)
                        if prev_val is not None and prev_val != "":
                            row[column_name] = prev_val
                            filled_count += 1
                            if len(sample_fills) < 5:
                                sample_fills.append({
                                    "row_index": i,
                                    "original": None,
                                    "filled": prev_val,
                                })
                            break
                elif rule.strategy == ImputationStrategy.BACKWARD_FILL:
                    # 后向填充
                    for j in range(i + 1, len(filled_data)):
                        next_val = data[j].get(column_name)
                        if next_val is not None and next_val != "":
                            row[column_name] = next_val
                            filled_count += 1
                            if len(sample_fills) < 5:
                                sample_fills.append({
                                    "row_index": i,
                                    "original": None,
                                    "filled": next_val,
                                })
                            break
                elif rule.strategy == ImputationStrategy.CORRELATION_BASED:
                    # 关联填充在此处跳过，使用专用方法
                    pass
                else:
                    # 使用计算的填充值
                    row[column_name] = fill_value
                    filled_count += 1
                    if len(sample_fills) < 5:
                        sample_fills.append({
                            "row_index": i,
                            "original": None,
                            "filled": fill_value,
                        })

        # 处理删除行策略
        if rule.strategy == ImputationStrategy.DELETE_ROW:
            filled_data = [
                row for row in filled_data
                if row.get(column_name) is not None and row.get(column_name) != ""
            ]

        result = ImputationResult(
            column_name=column_name,
            original_missing_count=len(data) - len([
                r for r in data
                if r.get(column_name) is not None and r.get(column_name) != ""
            ]),
            filled_count=filled_count,
            strategy_used=rule.strategy,
            fill_value_summary=str(fill_value)[:100] if fill_value else "N/A",
            sample_fills=sample_fills,
        )

        return filled_data, result

    def generate_imputation_rules(
        self,
        data: List[Dict[str, Any]],
        columns: List[str] = None,
        context: Dict[str, Any] = None,
        use_llm: bool = True,
    ) -> List[ImputationRule]:
        """
        为多个列生成填充规则

        Args:
            data: 数据
            columns: 列名列表（None 表示所有列）
            context: 上下文
            use_llm: 是否使用 LLM

        Returns:
            填充规则列表
        """
        if not data:
            return []

        if columns is None:
            columns = list(data[0].keys())

        rules = []
        for col in columns:
            analysis = self.analyze_missing_patterns(data, col)
            if analysis.missing_count > 0:
                rule = self.recommend_imputation_strategy(analysis, context, use_llm)
                rules.append(rule)

        return rules

    def preview_imputation(
        self,
        data: List[Dict[str, Any]],
        column_name: str,
        rule: ImputationRule,
        preview_count: int = 10,
    ) -> Dict[str, Any]:
        """
        预览填充效果

        Args:
            data: 原始数据
            column_name: 列名
            rule: 填充规则
            preview_count: 预览行数

        Returns:
            预览结果
        """
        # 找到有缺失值的行
        missing_rows = []
        for i, row in enumerate(data):
            val = row.get(column_name)
            if val is None or val == "" or (isinstance(val, float) and str(val) == "nan"):
                missing_rows.append((i, row))
                if len(missing_rows) >= preview_count:
                    break

        # 获取填充值
        fill_value = self._get_fill_value(data, column_name, rule)

        # 生成预览
        previews = []
        for idx, row in missing_rows:
            preview_row = {
                "row_index": idx,
                "before": {k: v for k, v in row.items()},
                "after": {k: v for k, v in row.items()},
            }

            if rule.strategy == ImputationStrategy.DELETE_ROW:
                preview_row["after"] = None
                preview_row["action"] = "删除该行"
            elif rule.strategy == ImputationStrategy.FLAG_MISSING:
                preview_row["after"][f"{column_name}_is_missing"] = True
                preview_row["action"] = "标记为缺失"
            elif rule.strategy == ImputationStrategy.FORWARD_FILL:
                # 查找前向值
                for j in range(idx - 1, -1, -1):
                    prev_val = data[j].get(column_name)
                    if prev_val is not None and prev_val != "":
                        preview_row["after"][column_name] = prev_val
                        preview_row["action"] = f"使用前向值: {prev_val}"
                        break
            elif rule.strategy == ImputationStrategy.BACKWARD_FILL:
                # 查找后向值
                for j in range(idx + 1, len(data)):
                    next_val = data[j].get(column_name)
                    if next_val is not None and next_val != "":
                        preview_row["after"][column_name] = next_val
                        preview_row["action"] = f"使用后向值: {next_val}"
                        break
            else:
                preview_row["after"][column_name] = fill_value
                preview_row["action"] = f"填充为: {fill_value}"

            previews.append(preview_row)

        return {
            "column_name": column_name,
            "strategy": rule.strategy.value,
            "total_missing": len([
                r for r in data
                if r.get(column_name) is None or r.get(column_name) == ""
            ]),
            "preview_count": len(previews),
            "previews": previews,
        }

    def _infer_column_type(
        self,
        values: List[Any],
        hint: str = None,
    ) -> ColumnType:
        """推断列类型"""
        if hint:
            hint_lower = hint.lower()
            if any(t in hint_lower for t in ["int", "float", "decimal", "numeric", "double"]):
                return ColumnType.NUMERIC
            if any(t in hint_lower for t in ["date", "time", "timestamp"]):
                return ColumnType.DATETIME
            if any(t in hint_lower for t in ["bool", "boolean"]):
                return ColumnType.BOOLEAN
            if any(t in hint_lower for t in ["char", "varchar", "text", "string"]):
                return ColumnType.TEXT

        if not values:
            return ColumnType.UNKNOWN

        # 采样分析
        sample = values[:100]

        # 检查数值
        numeric_count = 0
        for v in sample:
            if isinstance(v, (int, float)):
                numeric_count += 1
            elif isinstance(v, str):
                try:
                    float(v.replace(",", ""))
                    numeric_count += 1
                except ValueError:
                    pass

        if numeric_count / len(sample) > 0.8:
            return ColumnType.NUMERIC

        # 检查日期
        date_patterns = [
            r"\d{4}[-/]\d{2}[-/]\d{2}",
            r"\d{2}[-/]\d{2}[-/]\d{4}",
            r"\d{4}年\d{1,2}月\d{1,2}日",
        ]
        date_count = 0
        for v in sample:
            if isinstance(v, str):
                for pattern in date_patterns:
                    if re.search(pattern, v):
                        date_count += 1
                        break

        if date_count / len(sample) > 0.8:
            return ColumnType.DATETIME

        # 检查布尔
        bool_values = {"true", "false", "yes", "no", "1", "0", "是", "否"}
        bool_count = sum(1 for v in sample if str(v).lower() in bool_values)
        if bool_count / len(sample) > 0.8:
            return ColumnType.BOOLEAN

        # 检查分类（唯一值比例低）
        unique_ratio = len(set(str(v) for v in sample)) / len(sample)
        if unique_ratio < 0.1:
            return ColumnType.CATEGORICAL

        return ColumnType.TEXT

    def _analyze_missing_pattern(
        self,
        missing_positions: List[int],
        total_rows: int,
    ) -> str:
        """
        分析缺失模式

        Returns:
            "random" - 随机缺失
            "systematic" - 系统性缺失（有规律）
            "block" - 块状缺失（连续）
        """
        if not missing_positions:
            return "none"

        if len(missing_positions) == 1:
            return "random"

        # 检查是否有连续缺失（块状）
        consecutive_count = 0
        max_consecutive = 0
        for i in range(1, len(missing_positions)):
            if missing_positions[i] == missing_positions[i-1] + 1:
                consecutive_count += 1
                max_consecutive = max(max_consecutive, consecutive_count)
            else:
                consecutive_count = 0

        # 如果最大连续缺失超过5或超过总缺失的30%，认为是块状缺失
        if max_consecutive >= 5 or max_consecutive / len(missing_positions) > 0.3:
            return "block"

        # 检查是否有规律性（如每隔N行缺失）
        if len(missing_positions) >= 3:
            intervals = [
                missing_positions[i] - missing_positions[i-1]
                for i in range(1, min(10, len(missing_positions)))
            ]
            # 如果间隔非常一致，认为是系统性缺失
            if len(set(intervals)) <= 2:
                return "systematic"

        return "random"

    def _compute_value_stats(
        self,
        values: List[Any],
        column_type: ColumnType,
    ) -> Dict[str, Any]:
        """计算值统计"""
        stats = {
            "count": len(values),
            "unique_count": len(set(str(v) for v in values)),
        }

        if column_type == ColumnType.NUMERIC:
            try:
                numeric_values = []
                for v in values:
                    if isinstance(v, (int, float)):
                        numeric_values.append(float(v))
                    elif isinstance(v, str):
                        try:
                            numeric_values.append(float(v.replace(",", "")))
                        except ValueError:
                            pass

                if numeric_values:
                    stats["mean"] = mean(numeric_values)
                    stats["median"] = median(numeric_values)
                    stats["min"] = min(numeric_values)
                    stats["max"] = max(numeric_values)
                    if len(numeric_values) > 1:
                        stats["std"] = stdev(numeric_values)
                    try:
                        stats["mode"] = mode(numeric_values)
                    except:
                        pass
            except Exception as e:
                logger.warning(f"数值统计计算失败: {e}")

        elif column_type in (ColumnType.CATEGORICAL, ColumnType.TEXT):
            # 计算频率分布
            freq = {}
            for v in values:
                str_v = str(v)
                freq[str_v] = freq.get(str_v, 0) + 1

            # 找出最频繁值
            sorted_freq = sorted(freq.items(), key=lambda x: x[1], reverse=True)
            stats["most_frequent"] = sorted_freq[0][0] if sorted_freq else None
            stats["frequency_distribution"] = dict(sorted_freq[:10])

        return stats

    def _recommend_by_rules(self, analysis: MissingAnalysis) -> ImputationRule:
        """基于规则推荐策略"""
        column_type = analysis.column_type
        missing_pattern = analysis.missing_pattern
        missing_pct = analysis.missing_percentage
        stats = analysis.value_stats

        # 缺失比例过高，建议删除或标记
        if missing_pct > 70:
            return ImputationRule(
                column_name=analysis.column_name,
                strategy=ImputationStrategy.FLAG_MISSING,
                confidence=80,
                reason=f"缺失比例过高({missing_pct:.1f}%)，建议标记而非填充",
            )

        # 缺失比例过高但低于删除阈值
        if missing_pct > 50:
            return ImputationRule(
                column_name=analysis.column_name,
                strategy=ImputationStrategy.DELETE_ROW,
                confidence=70,
                reason=f"缺失比例较高({missing_pct:.1f}%)，建议删除含缺失值的行",
            )

        # 如果有高相关性字段，优先推荐关联填充
        if analysis.correlated_columns:
            return ImputationRule(
                column_name=analysis.column_name,
                strategy=ImputationStrategy.CORRELATION_BASED,
                confidence=85,
                reason=f"检测到高关联字段: {analysis.correlated_columns[:3]}，使用关联推断填充",
                parameters={
                    "correlated_columns": analysis.correlated_columns[:5],
                    "k_neighbors": 5,
                },
            )

        # 数值型
        if column_type == ColumnType.NUMERIC:
            # 块状缺失用插值
            if missing_pattern == "block":
                return ImputationRule(
                    column_name=analysis.column_name,
                    strategy=ImputationStrategy.INTERPOLATE,
                    confidence=75,
                    reason="数值型字段，块状缺失，使用线性插值",
                )

            # 有异常值用中位数
            if stats.get("std") and stats.get("mean"):
                cv = stats["std"] / stats["mean"] if stats["mean"] != 0 else 0
                if cv > 1:  # 变异系数高，可能有异常值
                    return ImputationRule(
                        column_name=analysis.column_name,
                        strategy=ImputationStrategy.MEDIAN,
                        fill_value=stats.get("median"),
                        confidence=80,
                        reason="数值型字段，变异较大，使用中位数填充避免异常值影响",
                    )

            # 默认用均值
            return ImputationRule(
                column_name=analysis.column_name,
                strategy=ImputationStrategy.MEAN,
                fill_value=stats.get("mean"),
                confidence=75,
                reason="数值型字段，使用均值填充",
            )

        # 分类型
        elif column_type == ColumnType.CATEGORICAL:
            most_frequent = stats.get("most_frequent")
            return ImputationRule(
                column_name=analysis.column_name,
                strategy=ImputationStrategy.MOST_FREQUENT,
                fill_value=most_frequent,
                confidence=80,
                reason=f"分类型字段，使用最频繁值填充: {most_frequent}",
            )

        # 日期型
        elif column_type == ColumnType.DATETIME:
            if missing_pattern == "block":
                return ImputationRule(
                    column_name=analysis.column_name,
                    strategy=ImputationStrategy.DATE_INTERPOLATE,
                    confidence=70,
                    reason="日期型字段，块状缺失，使用日期插值",
                )
            return ImputationRule(
                column_name=analysis.column_name,
                strategy=ImputationStrategy.DATE_PATTERN,
                confidence=65,
                reason="日期型字段，基于模式推断填充",
            )

        # 布尔型
        elif column_type == ColumnType.BOOLEAN:
            most_frequent = stats.get("most_frequent")
            return ImputationRule(
                column_name=analysis.column_name,
                strategy=ImputationStrategy.MOST_FREQUENT,
                fill_value=most_frequent,
                confidence=75,
                reason=f"布尔型字段，使用最频繁值: {most_frequent}",
            )

        # 文本型或未知
        else:
            # 如果唯一值比例低，当作分类处理
            if stats.get("unique_count", 0) < stats.get("count", 1) * 0.1:
                return ImputationRule(
                    column_name=analysis.column_name,
                    strategy=ImputationStrategy.MOST_FREQUENT,
                    fill_value=stats.get("most_frequent"),
                    confidence=70,
                    reason="文本字段唯一值少，按分类处理，使用最频繁值",
                )

            # 使用 LLM 推断
            return ImputationRule(
                column_name=analysis.column_name,
                strategy=ImputationStrategy.LLM_INFERENCE,
                confidence=60,
                reason="文本字段，建议使用 LLM 语义推断",
            )

    def _get_llm_recommendation(
        self,
        analysis: MissingAnalysis,
        context: Dict[str, Any] = None,
    ) -> Optional[Dict[str, Any]]:
        """使用 LLM 获取填充建议"""
        # 构建 prompt
        context_info = ""
        if context:
            context_info = f"\n表名: {context.get('table_name', '未知')}"
            if context.get("business_context"):
                context_info += f"\n业务场景: {context['business_context']}"

        prompt = f"""分析以下数据列的缺失值情况，推荐最佳填充策略：

列名: {analysis.column_name}
列类型: {analysis.column_type.value}
总行数: {analysis.total_rows}
缺失数: {analysis.missing_count}
缺失比例: {analysis.missing_percentage:.1f}%
缺失模式: {analysis.missing_pattern}
{context_info}

非空值统计:
{json.dumps(analysis.value_stats, ensure_ascii=False, indent=2)}

样本值: {analysis.sample_values[:5]}

可选策略:
- mean: 均值填充（数值型）
- median: 中位数填充（数值型）
- mode: 众数填充
- constant: 常量填充
- forward_fill: 前向填充
- backward_fill: 后向填充
- most_frequent: 最频繁值填充
- delete_row: 删除含缺失值的行
- flag_missing: 标记为缺失

请返回 JSON 格式：
{{
    "strategy": "策略名",
    "fill_value": "填充值（如适用）",
    "confidence": 置信度(0-100),
    "reason": "推荐理由"
}}"""

        try:
            response = requests.post(
                f"{self.api_url}/v1/chat/completions",
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": "你是数据质量专家，擅长分析缺失值并推荐填充策略。只返回 JSON 格式结果。"},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.1,
                    "max_tokens": 300,
                },
                timeout=15,
            )

            if response.status_code == 200:
                content = response.json()["choices"][0]["message"]["content"]
                # 提取 JSON
                json_match = re.search(r'\{[\s\S]*\}', content)
                if json_match:
                    return json.loads(json_match.group())
            else:
                logger.warning(f"LLM API 返回错误: {response.status_code}")

        except json.JSONDecodeError as e:
            logger.warning(f"LLM 返回解析失败: {e}")
        except requests.exceptions.RequestException as e:
            logger.warning(f"LLM API 请求失败: {e}")
        except Exception as e:
            logger.warning(f"LLM 推荐异常: {e}")

        return None

    def _get_fill_value(
        self,
        data: List[Dict[str, Any]],
        column_name: str,
        rule: ImputationRule,
    ) -> Any:
        """获取填充值"""
        if rule.fill_value is not None:
            return rule.fill_value

        # 收集非空值
        non_null_values = []
        for row in data:
            val = row.get(column_name)
            if val is not None and val != "":
                non_null_values.append(val)

        if not non_null_values:
            return None

        strategy = rule.strategy

        if strategy == ImputationStrategy.MEAN:
            try:
                numeric_vals = [float(v) for v in non_null_values if isinstance(v, (int, float)) or (isinstance(v, str) and v.replace(".", "").replace("-", "").isdigit())]
                return mean(numeric_vals) if numeric_vals else None
            except:
                return None

        elif strategy == ImputationStrategy.MEDIAN:
            try:
                numeric_vals = [float(v) for v in non_null_values if isinstance(v, (int, float)) or (isinstance(v, str) and v.replace(".", "").replace("-", "").isdigit())]
                return median(numeric_vals) if numeric_vals else None
            except:
                return None

        elif strategy == ImputationStrategy.MODE:
            try:
                return mode(non_null_values)
            except:
                # 如果没有众数，返回第一个值
                return non_null_values[0] if non_null_values else None

        elif strategy in (ImputationStrategy.MOST_FREQUENT, ImputationStrategy.CATEGORY_DEFAULT):
            freq = {}
            for v in non_null_values:
                str_v = str(v)
                freq[str_v] = freq.get(str_v, 0) + 1
            if freq:
                return max(freq.items(), key=lambda x: x[1])[0]
            return None

        elif strategy == ImputationStrategy.CONSTANT:
            return rule.parameters.get("constant_value", 0)

        return None

    def _generate_kettle_config(
        self,
        rule: ImputationRule,
        analysis: MissingAnalysis,
    ) -> None:
        """生成 Kettle 步骤配置"""
        strategy = rule.strategy
        kettle_info = STRATEGY_TO_KETTLE.get(strategy, {})

        rule.kettle_step_type = kettle_info.get("step_type", "IfFieldValueIsNull")

        if strategy in (
            ImputationStrategy.MEAN,
            ImputationStrategy.MEDIAN,
            ImputationStrategy.MODE,
            ImputationStrategy.CONSTANT,
            ImputationStrategy.MOST_FREQUENT,
        ):
            fill_value = rule.fill_value
            if fill_value is None:
                fill_value = self._get_fill_value([], rule.column_name, rule)

            rule.kettle_config = {
                "step_name": f"填充_{analysis.column_name}",
                "field_name": analysis.column_name,
                "replace_value": str(fill_value) if fill_value is not None else "",
                "set_empty_string": "N",
            }

        elif strategy == ImputationStrategy.DELETE_ROW:
            rule.kettle_config = {
                "step_name": f"过滤空值_{analysis.column_name}",
                "condition": f"[{analysis.column_name}] IS NOT NULL AND [{analysis.column_name}] != ''",
                "send_true_to": "后续步骤",
                "send_false_to": "垃圾桶",
            }

        elif strategy == ImputationStrategy.FLAG_MISSING:
            rule.kettle_config = {
                "step_name": f"标记缺失_{analysis.column_name}",
                "calculation_type": "NVL",
                "field_a": analysis.column_name,
                "result_field": f"{analysis.column_name}_is_missing",
            }

        elif strategy in (ImputationStrategy.FORWARD_FILL, ImputationStrategy.BACKWARD_FILL):
            # Analytic Query 步骤配置
            window_type = "LAG" if strategy == ImputationStrategy.FORWARD_FILL else "LEAD"
            rule.kettle_config = {
                "step_name": f"填充_{analysis.column_name}",
                "function_type": window_type,
                "field_name": analysis.column_name,
                "result_field": f"{analysis.column_name}_filled",
                "offset": 1,
            }

        elif strategy == ImputationStrategy.CORRELATION_BASED:
            # StreamLookup 步骤配置（基于关联字段查找填充）
            correlated = analysis.correlated_columns or []
            rule.kettle_config = {
                "step_name": f"关联填充_{analysis.column_name}",
                "target_field": analysis.column_name,
                "lookup_fields": correlated[:3],  # 最多使用3个关联字段
                "result_field": analysis.column_name,
                "default_value": "",
            }

    # ===== 关联缺失值推断 (CORRELATION_BASED) =====

    def compute_column_correlations(
        self,
        data: List[Dict[str, Any]],
        target_column: str,
        candidate_columns: List[str] = None,
        method: str = "auto",
    ) -> List[Dict[str, Any]]:
        """
        计算目标列与其他列的相关性

        Args:
            data: 数据列表
            target_column: 目标列名（含缺失值的列）
            candidate_columns: 候选关联列（None 表示所有其他列）
            method: 相关性计算方法 (auto, pearson, mutual_info)

        Returns:
            相关性分析结果列表，按相关性强度降序排列
        """
        if not data:
            return []

        all_columns = list(data[0].keys())
        if candidate_columns is None:
            candidate_columns = [c for c in all_columns if c != target_column]

        # 提取有效行（目标列非空的行）
        valid_rows = [
            row for row in data
            if row.get(target_column) is not None and row.get(target_column) != ""
        ]

        if len(valid_rows) < 5:
            logger.warning(f"有效行数不足({len(valid_rows)})，无法计算相关性")
            return []

        correlations = []

        for col in candidate_columns:
            # 跳过自身和全为空的列
            col_values = [row.get(col) for row in valid_rows]
            non_null_count = sum(1 for v in col_values if v is not None and v != "")
            if non_null_count < len(valid_rows) * 0.5:
                continue

            # 判断数据类型
            target_type = self._infer_column_type(
                [row.get(target_column) for row in valid_rows if row.get(target_column)],
            )
            col_type = self._infer_column_type(
                [v for v in col_values if v is not None and v != ""],
            )

            # 选择合适的方法
            if method == "auto":
                if target_type == ColumnType.NUMERIC and col_type == ColumnType.NUMERIC:
                    chosen_method = "pearson"
                else:
                    chosen_method = "mutual_info"
            else:
                chosen_method = method

            try:
                if chosen_method == "pearson":
                    corr_value = self._pearson_correlation(
                        valid_rows, target_column, col
                    )
                else:
                    corr_value = self._mutual_information(
                        valid_rows, target_column, col
                    )

                if corr_value is not None and abs(corr_value) > 0.1:
                    correlations.append({
                        "column": col,
                        "correlation": round(corr_value, 4),
                        "abs_correlation": round(abs(corr_value), 4),
                        "method": chosen_method,
                        "target_type": target_type.value,
                        "column_type": col_type.value,
                    })
            except Exception as e:
                logger.debug(f"计算 {col} 的相关性失败: {e}")

        # 按绝对相关性排序
        correlations.sort(key=lambda x: x["abs_correlation"], reverse=True)
        return correlations

    def _pearson_correlation(
        self,
        rows: List[Dict[str, Any]],
        col_a: str,
        col_b: str,
    ) -> Optional[float]:
        """计算 Pearson 相关系数"""
        pairs = []
        for row in rows:
            va, vb = row.get(col_a), row.get(col_b)
            if va is None or vb is None or va == "" or vb == "":
                continue
            try:
                pairs.append((float(str(va).replace(",", "")),
                              float(str(vb).replace(",", ""))))
            except (ValueError, TypeError):
                continue

        if len(pairs) < 5:
            return None

        xs, ys = zip(*pairs)
        n = len(xs)
        mean_x = sum(xs) / n
        mean_y = sum(ys) / n

        cov = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
        std_x = math.sqrt(sum((x - mean_x) ** 2 for x in xs))
        std_y = math.sqrt(sum((y - mean_y) ** 2 for y in ys))

        if std_x == 0 or std_y == 0:
            return None

        return cov / (std_x * std_y)

    def _mutual_information(
        self,
        rows: List[Dict[str, Any]],
        col_a: str,
        col_b: str,
        bins: int = 10,
    ) -> Optional[float]:
        """
        计算互信息（归一化）

        对数值型数据先分箱，对分类型数据直接计算。
        返回归一化互信息 [0, 1]。
        """
        values_a = []
        values_b = []
        for row in rows:
            va, vb = row.get(col_a), row.get(col_b)
            if va is None or vb is None or va == "" or vb == "":
                continue
            values_a.append(str(va))
            values_b.append(str(vb))

        if len(values_a) < 5:
            return None

        n = len(values_a)

        # 对数值型进行分箱
        values_a = self._discretize(values_a, bins)
        values_b = self._discretize(values_b, bins)

        # 计算联合分布和边际分布
        joint_counts = Counter(zip(values_a, values_b))
        margin_a = Counter(values_a)
        margin_b = Counter(values_b)

        # 计算互信息
        mi = 0.0
        for (a, b), count in joint_counts.items():
            p_ab = count / n
            p_a = margin_a[a] / n
            p_b = margin_b[b] / n
            if p_ab > 0 and p_a > 0 and p_b > 0:
                mi += p_ab * math.log2(p_ab / (p_a * p_b))

        # 归一化: NMI = MI / sqrt(H(A) * H(B))
        h_a = -sum((c / n) * math.log2(c / n) for c in margin_a.values() if c > 0)
        h_b = -sum((c / n) * math.log2(c / n) for c in margin_b.values() if c > 0)

        if h_a == 0 or h_b == 0:
            return 0.0

        nmi = mi / math.sqrt(h_a * h_b)
        return min(nmi, 1.0)

    def _discretize(self, values: List[str], bins: int = 10) -> List[str]:
        """将数值型数据分箱，分类型数据保持不变"""
        # 尝试转为数值
        numeric_vals = []
        for v in values:
            try:
                numeric_vals.append(float(v.replace(",", "")))
            except (ValueError, TypeError):
                return values  # 不是数值型，直接返回原值

        # 分箱
        min_val = min(numeric_vals)
        max_val = max(numeric_vals)
        if min_val == max_val:
            return [str(min_val)] * len(values)

        bin_width = (max_val - min_val) / bins
        return [str(int((v - min_val) / bin_width)) for v in numeric_vals]

    def impute_correlation_based(
        self,
        data: List[Dict[str, Any]],
        target_column: str,
        k_neighbors: int = 5,
        correlation_threshold: float = 0.3,
        max_features: int = 5,
    ) -> Tuple[List[Dict[str, Any]], ImputationResult]:
        """
        基于关联字段的 KNN 缺失值推断

        使用与目标列高相关的字段作为特征，找到最相似的 K 个邻居，
        用邻居的目标列值加权平均（数值型）或投票（分类型）来填充。

        Args:
            data: 数据列表
            target_column: 目标列名
            k_neighbors: K 近邻数量
            correlation_threshold: 最低相关性阈值
            max_features: 最多使用的特征列数

        Returns:
            (填充后的数据, 填充结果)
        """
        filled_data = [row.copy() for row in data]
        filled_count = 0
        sample_fills = []

        # 1. 计算列间相关性
        correlations = self.compute_column_correlations(
            data, target_column, method="auto"
        )

        # 过滤低相关性列
        feature_cols = [
            c["column"] for c in correlations
            if c["abs_correlation"] >= correlation_threshold
        ][:max_features]

        if not feature_cols:
            logger.warning(f"未找到与 {target_column} 相关性足够高的列（阈值={correlation_threshold}）")
            return filled_data, ImputationResult(
                column_name=target_column,
                original_missing_count=sum(
                    1 for r in data
                    if r.get(target_column) is None or r.get(target_column) == ""
                ),
                filled_count=0,
                strategy_used=ImputationStrategy.CORRELATION_BASED,
                fill_value_summary=f"无高相关性列(阈值={correlation_threshold})",
            )

        logger.info(f"关联填充 [{target_column}]: 使用特征列 {feature_cols}")

        # 2. 推断目标列类型
        target_type = self._infer_column_type(
            [row.get(target_column) for row in data if row.get(target_column)]
        )

        # 3. 分离有值行和缺失行
        complete_rows = []
        missing_indices = []
        for i, row in enumerate(data):
            val = row.get(target_column)
            if val is None or val == "":
                missing_indices.append(i)
            else:
                complete_rows.append((i, row))

        if not complete_rows:
            return filled_data, ImputationResult(
                column_name=target_column,
                original_missing_count=len(missing_indices),
                filled_count=0,
                strategy_used=ImputationStrategy.CORRELATION_BASED,
                fill_value_summary="无完整行可用作参考",
            )

        # 4. 构建特征向量
        feature_encoders = self._build_feature_encoders(data, feature_cols)

        complete_vectors = []
        for idx, row in complete_rows:
            vec = self._encode_row(row, feature_cols, feature_encoders)
            if vec is not None:
                complete_vectors.append((idx, row, vec))

        if not complete_vectors:
            return filled_data, ImputationResult(
                column_name=target_column,
                original_missing_count=len(missing_indices),
                filled_count=0,
                strategy_used=ImputationStrategy.CORRELATION_BASED,
                fill_value_summary="无法构建有效特征向量",
            )

        # 5. 对每个缺失行执行 KNN 填充
        for mi in missing_indices:
            row = filled_data[mi]
            query_vec = self._encode_row(row, feature_cols, feature_encoders)
            if query_vec is None:
                continue

            # 计算距离
            distances = []
            for ci, crow, cvec in complete_vectors:
                dist = self._euclidean_distance(query_vec, cvec)
                distances.append((dist, crow))

            # 取最近的K个邻居
            distances.sort(key=lambda x: x[0])
            neighbors = distances[:k_neighbors]

            if not neighbors:
                continue

            # 计算填充值
            if target_type == ColumnType.NUMERIC:
                # 加权平均（权重 = 1 / (distance + epsilon)）
                epsilon = 1e-10
                weighted_sum = 0.0
                weight_total = 0.0
                for dist, nrow in neighbors:
                    try:
                        nval = float(str(nrow[target_column]).replace(",", ""))
                        w = 1.0 / (dist + epsilon)
                        weighted_sum += nval * w
                        weight_total += w
                    except (ValueError, TypeError):
                        continue

                if weight_total > 0:
                    fill_value = round(weighted_sum / weight_total, 4)
                    row[target_column] = fill_value
                    filled_count += 1
                    if len(sample_fills) < 5:
                        sample_fills.append({
                            "row_index": mi,
                            "original": None,
                            "filled": fill_value,
                            "neighbors_used": len(neighbors),
                        })
            else:
                # 投票法（加权投票）
                epsilon = 1e-10
                votes = defaultdict(float)
                for dist, nrow in neighbors:
                    nval = nrow.get(target_column)
                    if nval is not None and nval != "":
                        w = 1.0 / (dist + epsilon)
                        votes[str(nval)] += w

                if votes:
                    fill_value = max(votes.items(), key=lambda x: x[1])[0]
                    row[target_column] = fill_value
                    filled_count += 1
                    if len(sample_fills) < 5:
                        sample_fills.append({
                            "row_index": mi,
                            "original": None,
                            "filled": fill_value,
                            "neighbors_used": len(neighbors),
                        })

        result = ImputationResult(
            column_name=target_column,
            original_missing_count=len(missing_indices),
            filled_count=filled_count,
            strategy_used=ImputationStrategy.CORRELATION_BASED,
            fill_value_summary=f"KNN(k={k_neighbors}) 基于 {len(feature_cols)} 个关联列: {feature_cols}",
            sample_fills=sample_fills,
        )

        return filled_data, result

    def impute_via_lookup_table(
        self,
        data: List[Dict[str, Any]],
        target_column: str,
        lookup_data: List[Dict[str, Any]],
        join_keys: List[str],
        lookup_value_column: str = None,
    ) -> Tuple[List[Dict[str, Any]], ImputationResult]:
        """
        基于查找表的缺失值填充（跨表关联填充）

        从查找表中根据关联键匹配行，用查找表中对应列的值来填充缺失值。
        类似于 SQL 的 LEFT JOIN 填充或 Kettle 的 Database Lookup 步骤。

        Args:
            data: 主数据列表
            target_column: 目标填充列名
            lookup_data: 查找表数据
            join_keys: 关联键列表（主数据和查找表共有的列名）
            lookup_value_column: 查找表中的值列名（None 表示与 target_column 同名）

        Returns:
            (填充后的数据, 填充结果)
        """
        if lookup_value_column is None:
            lookup_value_column = target_column

        filled_data = [row.copy() for row in data]
        filled_count = 0
        sample_fills = []

        # 构建查找索引（多键组合）
        lookup_index: Dict[tuple, Any] = {}
        for lrow in lookup_data:
            key = tuple(str(lrow.get(k, "")) for k in join_keys)
            val = lrow.get(lookup_value_column)
            if val is not None and val != "":
                lookup_index[key] = val

        if not lookup_index:
            logger.warning(f"查找表中没有可用的 {lookup_value_column} 值")
            return filled_data, ImputationResult(
                column_name=target_column,
                original_missing_count=sum(
                    1 for r in data
                    if r.get(target_column) is None or r.get(target_column) == ""
                ),
                filled_count=0,
                strategy_used=ImputationStrategy.CORRELATION_BASED,
                fill_value_summary="查找表为空",
            )

        # 对缺失行查找填充
        missing_count = 0
        for i, row in enumerate(filled_data):
            val = row.get(target_column)
            if val is None or val == "":
                missing_count += 1
                key = tuple(str(row.get(k, "")) for k in join_keys)
                lookup_val = lookup_index.get(key)
                if lookup_val is not None:
                    row[target_column] = lookup_val
                    filled_count += 1
                    if len(sample_fills) < 5:
                        sample_fills.append({
                            "row_index": i,
                            "original": None,
                            "filled": lookup_val,
                            "join_key": dict(zip(join_keys, key)),
                        })

        result = ImputationResult(
            column_name=target_column,
            original_missing_count=missing_count,
            filled_count=filled_count,
            strategy_used=ImputationStrategy.CORRELATION_BASED,
            fill_value_summary=f"查找表关联填充（keys={join_keys}, 命中率={filled_count}/{missing_count}）",
            sample_fills=sample_fills,
        )

        return filled_data, result

    def _build_feature_encoders(
        self,
        data: List[Dict[str, Any]],
        feature_cols: List[str],
    ) -> Dict[str, Dict[str, Any]]:
        """
        为每个特征列构建编码器（数值型归一化，分类型标签编码）
        """
        encoders = {}

        for col in feature_cols:
            values = [row.get(col) for row in data if row.get(col) is not None and row.get(col) != ""]
            col_type = self._infer_column_type(values)

            if col_type == ColumnType.NUMERIC:
                numeric_vals = []
                for v in values:
                    try:
                        numeric_vals.append(float(str(v).replace(",", "")))
                    except (ValueError, TypeError):
                        continue

                if numeric_vals:
                    min_v = min(numeric_vals)
                    max_v = max(numeric_vals)
                    encoders[col] = {
                        "type": "numeric",
                        "min": min_v,
                        "max": max_v,
                        "range": max_v - min_v if max_v != min_v else 1.0,
                    }
                else:
                    encoders[col] = {"type": "skip"}
            else:
                # 标签编码
                unique_vals = sorted(set(str(v) for v in values))
                label_map = {v: i / max(len(unique_vals) - 1, 1) for i, v in enumerate(unique_vals)}
                encoders[col] = {
                    "type": "categorical",
                    "label_map": label_map,
                    "default": 0.5,
                }

        return encoders

    def _encode_row(
        self,
        row: Dict[str, Any],
        feature_cols: List[str],
        encoders: Dict[str, Dict[str, Any]],
    ) -> Optional[List[float]]:
        """将一行数据编码为特征向量"""
        vector = []
        for col in feature_cols:
            enc = encoders.get(col)
            if enc is None or enc.get("type") == "skip":
                vector.append(0.5)
                continue

            val = row.get(col)
            if val is None or val == "":
                vector.append(0.5)  # 缺失值用中间值
                continue

            if enc["type"] == "numeric":
                try:
                    num = float(str(val).replace(",", ""))
                    normalized = (num - enc["min"]) / enc["range"]
                    vector.append(max(0.0, min(1.0, normalized)))
                except (ValueError, TypeError):
                    vector.append(0.5)
            else:
                encoded = enc["label_map"].get(str(val), enc["default"])
                vector.append(encoded)

        return vector

    @staticmethod
    def _euclidean_distance(vec_a: List[float], vec_b: List[float]) -> float:
        """计算欧氏距离"""
        return math.sqrt(sum((a - b) ** 2 for a, b in zip(vec_a, vec_b)))


# 创建全局实例
_ai_imputation_service: Optional[AIImputationService] = None


def get_ai_imputation_service() -> AIImputationService:
    """获取 AI 填充服务单例"""
    global _ai_imputation_service
    if _ai_imputation_service is None:
        _ai_imputation_service = AIImputationService()
    return _ai_imputation_service
