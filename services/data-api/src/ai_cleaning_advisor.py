"""
AI 数据清洗规则推荐服务
Phase 2: AI 能力增强 - 清洗规则推荐

功能：
- 基于数据质量问题自动推荐清洗规则
- 分析字段模式和值分布，生成针对性清洗建议
- 支持的清洗类型：空值处理、格式标准化、异常值修正、重复去重
- 生成可直接用于 Kettle 的清洗步骤配置
"""

import json
import logging
import os
import re
import requests
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# 配置
MODEL_API_URL = os.getenv("MODEL_API_URL") or os.getenv("CUBE_API_URL", "http://openai-proxy:8000")
AI_CLEANING_MODEL = os.getenv("AI_CLEANING_MODEL", "gpt-4o-mini")
AI_CLEANING_ENABLED = os.getenv("AI_CLEANING_ENABLED", "true").lower() in ("true", "1", "yes")


class CleaningType(Enum):
    """清洗类型"""
    NULL_HANDLING = "null_handling"           # 空值处理
    FORMAT_STANDARDIZATION = "format_std"     # 格式标准化
    OUTLIER_CORRECTION = "outlier_correction" # 异常值修正
    DEDUPLICATION = "deduplication"           # 去重
    VALUE_MAPPING = "value_mapping"           # 值映射/替换
    TYPE_CONVERSION = "type_conversion"       # 类型转换
    TRIM_WHITESPACE = "trim_whitespace"       # 去除空白
    CASE_NORMALIZATION = "case_normalization" # 大小写标准化
    PATTERN_EXTRACTION = "pattern_extraction" # 模式提取
    DATE_FORMATTING = "date_formatting"       # 日期格式化


class CleaningPriority(Enum):
    """清洗优先级"""
    CRITICAL = "critical"   # 必须修复
    HIGH = "high"           # 高优先级
    MEDIUM = "medium"       # 中优先级
    LOW = "low"             # 低优先级


@dataclass
class ColumnStatistics:
    """列统计信息"""
    column_name: str
    column_type: str
    total_count: int = 0
    null_count: int = 0
    distinct_count: int = 0
    min_value: Optional[Any] = None
    max_value: Optional[Any] = None
    avg_value: Optional[float] = None
    std_value: Optional[float] = None
    sample_values: List[Any] = field(default_factory=list)
    value_distribution: Dict[str, int] = field(default_factory=dict)
    pattern_distribution: Dict[str, int] = field(default_factory=dict)

    @property
    def null_ratio(self) -> float:
        """空值比例"""
        return self.null_count / self.total_count if self.total_count > 0 else 0

    @property
    def cardinality_ratio(self) -> float:
        """基数比例（唯一值/总数）"""
        return self.distinct_count / self.total_count if self.total_count > 0 else 0


@dataclass
class QualityIssue:
    """数据质量问题"""
    issue_id: str
    column_name: str
    issue_type: str          # completeness, validity, consistency, accuracy, uniqueness
    severity: str            # critical, high, medium, low
    description: str
    affected_rows: int = 0
    sample_bad_values: List[Any] = field(default_factory=list)
    expected_pattern: Optional[str] = None
    actual_pattern: Optional[str] = None


@dataclass
class CleaningRecommendation:
    """清洗推荐"""
    recommendation_id: str
    column_name: str
    cleaning_type: CleaningType
    priority: CleaningPriority
    description: str
    action: str                           # 具体操作描述
    confidence: int = 0                   # 置信度 0-100
    estimated_impact: int = 0             # 预计影响的行数
    # Kettle 步骤配置
    kettle_step_type: Optional[str] = None
    kettle_config: Dict[str, Any] = field(default_factory=dict)
    # 关联的质量问题
    related_issues: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "recommendation_id": self.recommendation_id,
            "column_name": self.column_name,
            "cleaning_type": self.cleaning_type.value,
            "priority": self.priority.value,
            "description": self.description,
            "action": self.action,
            "confidence": self.confidence,
            "estimated_impact": self.estimated_impact,
            "kettle_step_type": self.kettle_step_type,
            "kettle_config": self.kettle_config,
            "related_issues": self.related_issues,
        }


# 常见数据模式
DATA_PATTERNS = {
    "phone_cn": r"^1[3-9]\d{9}$",
    "email": r"^[\w\.-]+@[\w\.-]+\.\w+$",
    "id_card_cn": r"^\d{17}[\dXx]$",
    "date_iso": r"^\d{4}-\d{2}-\d{2}$",
    "date_cn": r"^\d{4}年\d{1,2}月\d{1,2}日$",
    "datetime_iso": r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}",
    "ip_v4": r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$",
    "url": r"^https?://[\w\.-]+",
    "number_only": r"^\d+$",
    "decimal": r"^\d+\.\d+$",
    "percentage": r"^\d+\.?\d*%$",
}


class AICleaningAdvisor:
    """AI 数据清洗规则推荐服务"""

    def __init__(self, api_url: str = None):
        """初始化服务"""
        self.api_url = api_url or MODEL_API_URL
        self.model = AI_CLEANING_MODEL
        self.enabled = AI_CLEANING_ENABLED
        self._recommendation_counter = 0

    def _generate_recommendation_id(self) -> str:
        """生成推荐 ID"""
        self._recommendation_counter += 1
        return f"rec_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{self._recommendation_counter:04d}"

    def analyze_quality_issues(
        self,
        quality_issues: List[QualityIssue],
        column_stats: Dict[str, ColumnStatistics] = None,
    ) -> List[CleaningRecommendation]:
        """
        基于数据质量问题分析并推荐清洗规则

        Args:
            quality_issues: 质量问题列表
            column_stats: 列统计信息（可选，用于更准确的推荐）

        Returns:
            清洗推荐列表
        """
        recommendations = []
        column_stats = column_stats or {}

        for issue in quality_issues:
            issue_recs = self._analyze_single_issue(issue, column_stats.get(issue.column_name))
            recommendations.extend(issue_recs)

        # 去重和合并相同列的推荐
        recommendations = self._merge_recommendations(recommendations)

        # 按优先级排序
        priority_order = {
            CleaningPriority.CRITICAL: 0,
            CleaningPriority.HIGH: 1,
            CleaningPriority.MEDIUM: 2,
            CleaningPriority.LOW: 3,
        }
        recommendations.sort(key=lambda r: (priority_order.get(r.priority, 99), -r.confidence))

        return recommendations

    def _analyze_single_issue(
        self,
        issue: QualityIssue,
        stats: Optional[ColumnStatistics],
    ) -> List[CleaningRecommendation]:
        """分析单个质量问题"""
        recommendations = []

        # 根据问题类型生成推荐
        if issue.issue_type == "completeness":
            recs = self._recommend_for_completeness(issue, stats)
            recommendations.extend(recs)

        elif issue.issue_type == "validity":
            recs = self._recommend_for_validity(issue, stats)
            recommendations.extend(recs)

        elif issue.issue_type == "consistency":
            recs = self._recommend_for_consistency(issue, stats)
            recommendations.extend(recs)

        elif issue.issue_type == "uniqueness":
            recs = self._recommend_for_uniqueness(issue, stats)
            recommendations.extend(recs)

        elif issue.issue_type == "accuracy":
            recs = self._recommend_for_accuracy(issue, stats)
            recommendations.extend(recs)

        # 关联问题 ID
        for rec in recommendations:
            rec.related_issues.append(issue.issue_id)

        return recommendations

    def _recommend_for_completeness(
        self,
        issue: QualityIssue,
        stats: Optional[ColumnStatistics],
    ) -> List[CleaningRecommendation]:
        """针对完整性问题的推荐"""
        recommendations = []

        null_ratio = stats.null_ratio if stats else 0
        priority = CleaningPriority.CRITICAL if null_ratio > 0.3 else CleaningPriority.HIGH

        # 推荐 1：空值处理
        rec = CleaningRecommendation(
            recommendation_id=self._generate_recommendation_id(),
            column_name=issue.column_name,
            cleaning_type=CleaningType.NULL_HANDLING,
            priority=priority,
            description=f"列 {issue.column_name} 存在 {issue.affected_rows} 条空值记录",
            action="填充空值或删除空值行",
            confidence=90,
            estimated_impact=issue.affected_rows,
            kettle_step_type="IfFieldValueIsNull",
            kettle_config={
                "field_name": issue.column_name,
                "replace_type": "default_value",  # 或 delete_row
                "default_value": self._suggest_default_value(issue.column_name, stats),
            }
        )
        recommendations.append(rec)

        return recommendations

    def _recommend_for_validity(
        self,
        issue: QualityIssue,
        stats: Optional[ColumnStatistics],
    ) -> List[CleaningRecommendation]:
        """针对有效性问题的推荐"""
        recommendations = []

        # 推荐 1：格式标准化
        if issue.expected_pattern:
            rec = CleaningRecommendation(
                recommendation_id=self._generate_recommendation_id(),
                column_name=issue.column_name,
                cleaning_type=CleaningType.FORMAT_STANDARDIZATION,
                priority=CleaningPriority.HIGH,
                description=f"列 {issue.column_name} 存在 {issue.affected_rows} 条格式不符记录",
                action=f"将数据格式标准化为: {issue.expected_pattern}",
                confidence=85,
                estimated_impact=issue.affected_rows,
                kettle_step_type="RegexEvaluation",
                kettle_config={
                    "field_name": issue.column_name,
                    "regex_pattern": issue.expected_pattern,
                    "allow_capture_groups": True,
                }
            )
            recommendations.append(rec)

        # 推荐 2：去除空白字符
        if issue.sample_bad_values:
            has_whitespace = any(
                isinstance(v, str) and (v != v.strip())
                for v in issue.sample_bad_values
            )
            if has_whitespace:
                rec = CleaningRecommendation(
                    recommendation_id=self._generate_recommendation_id(),
                    column_name=issue.column_name,
                    cleaning_type=CleaningType.TRIM_WHITESPACE,
                    priority=CleaningPriority.MEDIUM,
                    description=f"列 {issue.column_name} 存在前后空白字符",
                    action="去除字段前后空白字符",
                    confidence=95,
                    estimated_impact=issue.affected_rows,
                    kettle_step_type="StringOperations",
                    kettle_config={
                        "field_name": issue.column_name,
                        "operation": "trim",
                        "trim_type": "both",
                    }
                )
                recommendations.append(rec)

        return recommendations

    def _recommend_for_consistency(
        self,
        issue: QualityIssue,
        stats: Optional[ColumnStatistics],
    ) -> List[CleaningRecommendation]:
        """针对一致性问题的推荐"""
        recommendations = []

        # 推荐 1：值映射/替换
        if stats and stats.value_distribution:
            # 分析值分布，找出可能需要合并的值
            similar_values = self._find_similar_values(stats.value_distribution)
            if similar_values:
                rec = CleaningRecommendation(
                    recommendation_id=self._generate_recommendation_id(),
                    column_name=issue.column_name,
                    cleaning_type=CleaningType.VALUE_MAPPING,
                    priority=CleaningPriority.MEDIUM,
                    description=f"列 {issue.column_name} 存在相似但不一致的值",
                    action=f"统一相似值: {similar_values}",
                    confidence=75,
                    estimated_impact=issue.affected_rows,
                    kettle_step_type="ValueMapper",
                    kettle_config={
                        "field_name": issue.column_name,
                        "mappings": similar_values,
                    }
                )
                recommendations.append(rec)

        # 推荐 2：大小写标准化
        if stats and stats.sample_values:
            has_case_inconsistency = self._detect_case_inconsistency(stats.sample_values)
            if has_case_inconsistency:
                rec = CleaningRecommendation(
                    recommendation_id=self._generate_recommendation_id(),
                    column_name=issue.column_name,
                    cleaning_type=CleaningType.CASE_NORMALIZATION,
                    priority=CleaningPriority.LOW,
                    description=f"列 {issue.column_name} 存在大小写不一致",
                    action="统一转换为小写/大写",
                    confidence=80,
                    estimated_impact=issue.affected_rows,
                    kettle_step_type="StringOperations",
                    kettle_config={
                        "field_name": issue.column_name,
                        "operation": "lower",  # 或 upper
                    }
                )
                recommendations.append(rec)

        return recommendations

    def _recommend_for_uniqueness(
        self,
        issue: QualityIssue,
        stats: Optional[ColumnStatistics],
    ) -> List[CleaningRecommendation]:
        """针对唯一性问题的推荐"""
        recommendations = []

        rec = CleaningRecommendation(
            recommendation_id=self._generate_recommendation_id(),
            column_name=issue.column_name,
            cleaning_type=CleaningType.DEDUPLICATION,
            priority=CleaningPriority.HIGH,
            description=f"列 {issue.column_name} 存在 {issue.affected_rows} 条重复记录",
            action="去除重复记录，保留最新/第一条",
            confidence=90,
            estimated_impact=issue.affected_rows,
            kettle_step_type="Unique",
            kettle_config={
                "compare_fields": [issue.column_name],
                "error_handling": "skip",
            }
        )
        recommendations.append(rec)

        return recommendations

    def _recommend_for_accuracy(
        self,
        issue: QualityIssue,
        stats: Optional[ColumnStatistics],
    ) -> List[CleaningRecommendation]:
        """针对准确性问题的推荐"""
        recommendations = []

        # 异常值检测和修正
        if stats and stats.avg_value is not None and stats.std_value is not None:
            rec = CleaningRecommendation(
                recommendation_id=self._generate_recommendation_id(),
                column_name=issue.column_name,
                cleaning_type=CleaningType.OUTLIER_CORRECTION,
                priority=CleaningPriority.MEDIUM,
                description=f"列 {issue.column_name} 存在异常值",
                action=f"将异常值替换为均值 {stats.avg_value:.2f} 或删除",
                confidence=70,
                estimated_impact=issue.affected_rows,
                kettle_step_type="FilterRows",
                kettle_config={
                    "field_name": issue.column_name,
                    "condition": f"ABS(value - {stats.avg_value}) > {3 * stats.std_value}",
                    "action": "replace_with_mean",
                    "mean_value": stats.avg_value,
                }
            )
            recommendations.append(rec)

        return recommendations

    def recommend_from_column_analysis(
        self,
        stats: ColumnStatistics,
        use_llm: bool = True,
    ) -> List[CleaningRecommendation]:
        """
        基于列统计分析推荐清洗规则

        Args:
            stats: 列统计信息
            use_llm: 是否使用 LLM 增强推荐

        Returns:
            清洗推荐列表
        """
        recommendations = []

        # 1. 空值检查
        if stats.null_ratio > 0.01:  # 超过 1% 空值
            priority = (
                CleaningPriority.CRITICAL if stats.null_ratio > 0.3 else
                CleaningPriority.HIGH if stats.null_ratio > 0.1 else
                CleaningPriority.MEDIUM
            )
            rec = CleaningRecommendation(
                recommendation_id=self._generate_recommendation_id(),
                column_name=stats.column_name,
                cleaning_type=CleaningType.NULL_HANDLING,
                priority=priority,
                description=f"空值比例 {stats.null_ratio:.1%}",
                action="处理空值",
                confidence=95,
                estimated_impact=stats.null_count,
                kettle_step_type="IfFieldValueIsNull",
                kettle_config={
                    "field_name": stats.column_name,
                    "replace_type": "default_value",
                    "default_value": self._suggest_default_value(stats.column_name, stats),
                }
            )
            recommendations.append(rec)

        # 2. 模式分析
        if stats.sample_values:
            pattern_issues = self._analyze_patterns(stats)
            recommendations.extend(pattern_issues)

        # 3. 值分布分析
        if stats.value_distribution:
            distribution_issues = self._analyze_distribution(stats)
            recommendations.extend(distribution_issues)

        # 4. LLM 增强（如果启用）
        if use_llm and self.enabled:
            llm_recs = self._get_llm_recommendations(stats)
            recommendations.extend(llm_recs)

        return recommendations

    def _suggest_default_value(
        self,
        column_name: str,
        stats: Optional[ColumnStatistics],
    ) -> str:
        """建议默认填充值"""
        column_lower = column_name.lower()

        # 基于列名推断
        if any(k in column_lower for k in ["name", "title", "label", "名称", "标题"]):
            return "未知"
        elif any(k in column_lower for k in ["count", "num", "qty", "数量", "计数"]):
            return "0"
        elif any(k in column_lower for k in ["amount", "price", "fee", "金额", "价格"]):
            return "0.00"
        elif any(k in column_lower for k in ["date", "time", "日期", "时间"]):
            return "1970-01-01"
        elif any(k in column_lower for k in ["status", "state", "flag", "状态"]):
            return "unknown"
        elif any(k in column_lower for k in ["desc", "remark", "note", "描述", "备注"]):
            return ""

        # 基于统计信息推断
        if stats:
            if stats.avg_value is not None:
                return str(round(stats.avg_value, 2))
            elif stats.value_distribution:
                # 使用众数
                most_common = max(stats.value_distribution.items(), key=lambda x: x[1])
                return str(most_common[0])

        return ""

    def _find_similar_values(self, value_distribution: Dict[str, int]) -> List[Dict[str, str]]:
        """查找相似值并建议映射"""
        mappings = []
        values = list(value_distribution.keys())

        # 简单的相似性检测（大小写、空格差异）
        for i, v1 in enumerate(values):
            if not isinstance(v1, str):
                continue
            for v2 in values[i+1:]:
                if not isinstance(v2, str):
                    continue
                # 检查是否仅大小写不同
                if v1.lower() == v2.lower() and v1 != v2:
                    # 选择出现次数多的作为标准
                    standard = v1 if value_distribution[v1] >= value_distribution[v2] else v2
                    non_standard = v2 if standard == v1 else v1
                    mappings.append({"from": non_standard, "to": standard})
                # 检查是否仅空格差异
                elif v1.strip() == v2.strip() and v1 != v2:
                    standard = v1.strip()
                    mappings.append({"from": v1, "to": standard})
                    mappings.append({"from": v2, "to": standard})

        return mappings

    def _detect_case_inconsistency(self, sample_values: List[Any]) -> bool:
        """检测大小写不一致"""
        string_values = [v for v in sample_values if isinstance(v, str)]
        if len(string_values) < 2:
            return False

        # 检查是否有相同内容但大小写不同的值
        lower_values = [v.lower() for v in string_values]
        return len(set(lower_values)) < len(set(string_values))

    def _analyze_patterns(self, stats: ColumnStatistics) -> List[CleaningRecommendation]:
        """分析数据模式"""
        recommendations = []
        sample_values = [v for v in stats.sample_values if v is not None and isinstance(v, str)]

        if not sample_values:
            return recommendations

        # 检测主要模式
        detected_patterns = {}
        for pattern_name, pattern_regex in DATA_PATTERNS.items():
            matches = sum(1 for v in sample_values if re.match(pattern_regex, str(v)))
            if matches > 0:
                detected_patterns[pattern_name] = matches / len(sample_values)

        # 如果有主导模式但不是 100%，建议格式标准化
        for pattern_name, ratio in detected_patterns.items():
            if 0.5 < ratio < 0.95:
                non_matching = int((1 - ratio) * stats.total_count)
                rec = CleaningRecommendation(
                    recommendation_id=self._generate_recommendation_id(),
                    column_name=stats.column_name,
                    cleaning_type=CleaningType.FORMAT_STANDARDIZATION,
                    priority=CleaningPriority.MEDIUM,
                    description=f"检测到 {pattern_name} 模式，但有 {1-ratio:.1%} 不符合",
                    action=f"标准化为 {pattern_name} 格式",
                    confidence=int(ratio * 100),
                    estimated_impact=non_matching,
                    kettle_step_type="RegexEvaluation",
                    kettle_config={
                        "field_name": stats.column_name,
                        "pattern_name": pattern_name,
                        "regex_pattern": DATA_PATTERNS[pattern_name],
                    }
                )
                recommendations.append(rec)
                break

        return recommendations

    def _analyze_distribution(self, stats: ColumnStatistics) -> List[CleaningRecommendation]:
        """分析值分布"""
        recommendations = []

        # 检测低频异常值
        total = sum(stats.value_distribution.values())
        for value, count in stats.value_distribution.items():
            ratio = count / total
            # 低于 0.1% 且只出现少数次的可能是异常值
            if ratio < 0.001 and count < 5:
                rec = CleaningRecommendation(
                    recommendation_id=self._generate_recommendation_id(),
                    column_name=stats.column_name,
                    cleaning_type=CleaningType.OUTLIER_CORRECTION,
                    priority=CleaningPriority.LOW,
                    description=f"检测到可能的异常值: {value} (出现 {count} 次)",
                    action=f"检查并可能删除或修正异常值",
                    confidence=60,
                    estimated_impact=count,
                    kettle_step_type="FilterRows",
                    kettle_config={
                        "field_name": stats.column_name,
                        "filter_value": value,
                        "action": "review",
                    }
                )
                recommendations.append(rec)

        return recommendations

    def _get_llm_recommendations(self, stats: ColumnStatistics) -> List[CleaningRecommendation]:
        """使用 LLM 获取智能推荐"""
        recommendations = []

        if not self.enabled:
            return recommendations

        try:
            # 构建 prompt
            prompt = f"""分析以下列的统计信息，推荐数据清洗规则：

列名: {stats.column_name}
数据类型: {stats.column_type}
总行数: {stats.total_count}
空值数: {stats.null_count} ({stats.null_ratio:.1%})
唯一值数: {stats.distinct_count}
样本值: {stats.sample_values[:5]}

请返回 JSON 数组格式的清洗建议，每项包含：
- cleaning_type: 清洗类型（null_handling/format_std/value_mapping/trim_whitespace/case_normalization）
- priority: 优先级（critical/high/medium/low）
- description: 问题描述
- action: 建议操作

仅返回 JSON 数组，不要其他文字："""

            response = requests.post(
                f"{self.api_url}/v1/chat/completions",
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": "你是数据质量专家，擅长分析数据问题并给出清洗建议。只返回 JSON 格式结果。"},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.2,
                    "max_tokens": 500,
                },
                timeout=15,
            )

            if response.status_code == 200:
                content = response.json()["choices"][0]["message"]["content"]
                # 解析 JSON
                json_match = re.search(r'\[[\s\S]*\]', content)
                if json_match:
                    llm_recs = json.loads(json_match.group())
                    for rec_data in llm_recs:
                        try:
                            cleaning_type = CleaningType(rec_data.get("cleaning_type", "null_handling"))
                            priority = CleaningPriority(rec_data.get("priority", "medium"))
                            rec = CleaningRecommendation(
                                recommendation_id=self._generate_recommendation_id(),
                                column_name=stats.column_name,
                                cleaning_type=cleaning_type,
                                priority=priority,
                                description=rec_data.get("description", ""),
                                action=rec_data.get("action", ""),
                                confidence=75,  # LLM 推荐置信度
                                estimated_impact=0,
                            )
                            recommendations.append(rec)
                        except (KeyError, ValueError) as e:
                            logger.debug(f"解析 LLM 推荐失败: {e}")
                            continue

        except Exception as e:
            logger.warning(f"LLM 推荐获取失败: {e}")

        return recommendations

    def _merge_recommendations(
        self,
        recommendations: List[CleaningRecommendation],
    ) -> List[CleaningRecommendation]:
        """合并同一列的相同类型推荐"""
        merged = {}

        for rec in recommendations:
            key = (rec.column_name, rec.cleaning_type)
            if key not in merged:
                merged[key] = rec
            else:
                # 合并：保留置信度更高的
                existing = merged[key]
                if rec.confidence > existing.confidence:
                    rec.related_issues.extend(existing.related_issues)
                    merged[key] = rec
                else:
                    existing.related_issues.extend(rec.related_issues)
                    existing.estimated_impact = max(existing.estimated_impact, rec.estimated_impact)

        return list(merged.values())


# 创建全局实例
_cleaning_advisor: Optional[AICleaningAdvisor] = None


def get_cleaning_advisor() -> AICleaningAdvisor:
    """获取 AI 清洗顾问服务单例"""
    global _cleaning_advisor
    if _cleaning_advisor is None:
        _cleaning_advisor = AICleaningAdvisor()
    return _cleaning_advisor
