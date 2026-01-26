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
import os
import re
import requests
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Any, Optional, Union
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


# 创建全局实例
_ai_imputation_service: Optional[AIImputationService] = None


def get_ai_imputation_service() -> AIImputationService:
    """获取 AI 填充服务单例"""
    global _ai_imputation_service
    if _ai_imputation_service is None:
        _ai_imputation_service = AIImputationService()
    return _ai_imputation_service
