"""
智能图表推荐服务
Phase 1.2: 根据数据结构推荐合适的图表类型
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


logger = logging.getLogger(__name__)


class ChartType(Enum):
    """图表类型枚举"""
    # 趋势类
    LINE = "line"              # 折线图
    AREA = "area"              # 面积图
    COLUMN = "column"          # 柱状图（垂直）
    BAR = "bar"                # 条形图（水平）

    # 对比类
    GROUPED_COLUMN = "grouped_column"  # 分组柱状图
    STACKED_COLUMN = "stacked_column"  # 堆叠柱状图
    GROUPED_BAR = "grouped_bar"        # 分组条形图
    STACKED_BAR = "stacked_bar"        # 堆叠条形图

    # 占比类
    PIE = "pie"                # 饼图
    DONUT = "donut"            # 环形图
    TREEMAP = "treemap"        # 矩形树图

    # 分布类
    SCATTER = "scatter"        # 散点图
    HISTOGRAM = "histogram"    # 直方图
    BOX_PLOT = "box_plot"      # 箱线图

    # 关系类
    HEATMAP = "heatmap"        # 热力图
    BUBBLE = "bubble"          # 气泡图

    # 表格类
    TABLE = "table"            # 表格
    PIVOT_TABLE = "pivot_table"  # 透视表

    # 其他
    GAUGE = "gauge"            # 仪表盘
    FUNNEL = "funnel"          # 漏斗图
    WORD_CLOUD = "word_cloud"  # 词云


class DataType(Enum):
    """数据类型枚举"""
    NUMERIC = "numeric"        # 数值型
    CATEGORICAL = "categorical"  # 分类型
    TEMPORAL = "temporal"      # 时间型
    BOOLEAN = "boolean"        # 布尔型
    TEXT = "text"              # 文本型
    GEOGRAPHIC = "geographic"  # 地理型


@dataclass
class ColumnInfo:
    """列信息"""
    name: str
    data_type: DataType
    distinct_count: Optional[int] = None
    null_count: Optional[int] = None
    sample_values: Optional[List[Any]] = None


@dataclass
class ChartRecommendation:
    """图表推荐结果"""
    chart_type: ChartType
    chart_name: str
    confidence: float  # 0-1
    reason: str
    config: Dict[str, Any]
    dimensions: List[str]
    metrics: List[str]


class ChartRecommender:
    """智能图表推荐器"""

    def __init__(self):
        # 图表类型与数据特征的匹配规则
        self.chart_patterns = self._init_chart_patterns()

    def _init_chart_patterns(self) -> Dict[ChartType, Dict]:
        """初始化图表模式"""
        return {
            # 趋势类图表
            ChartType.LINE: {
                "name": "折线图",
                "min_dimensions": 1,
                "max_dimensions": 1,
                "min_metrics": 1,
                "max_metrics": 5,
                "requires_temporal": True,
                "best_for": ["trend", "time_series"],
                "data_pattern": "temporal_dimension_with_numeric_metrics",
            },
            ChartType.AREA: {
                "name": "面积图",
                "min_dimensions": 1,
                "max_dimensions": 1,
                "min_metrics": 1,
                "max_metrics": 3,
                "requires_temporal": True,
                "best_for": ["trend", "volume_over_time"],
                "data_pattern": "temporal_dimension_with_numeric_metrics",
            },

            # 对比类图表
            ChartType.COLUMN: {
                "name": "柱状图",
                "min_dimensions": 1,
                "max_dimensions": 2,
                "min_metrics": 1,
                "max_metrics": 3,
                "requires_temporal": False,
                "best_for": ["comparison", "ranking"],
                "data_pattern": "categorical_dimension_with_numeric_metric",
            },
            ChartType.BAR: {
                "name": "条形图",
                "min_dimensions": 1,
                "max_dimensions": 2,
                "min_metrics": 1,
                "max_metrics": 3,
                "requires_temporal": False,
                "best_for": ["comparison", "ranking", "long_labels"],
                "data_pattern": "categorical_dimension_with_numeric_metric",
            },
            ChartType.GROUPED_COLUMN: {
                "name": "分组柱状图",
                "min_dimensions": 2,
                "max_dimensions": 2,
                "min_metrics": 1,
                "max_metrics": 2,
                "requires_temporal": False,
                "best_for": ["multi_comparison", "grouped_ranking"],
                "data_pattern": "multiple_categorical_with_single_metric",
            },
            ChartType.STACKED_COLUMN: {
                "name": "堆叠柱状图",
                "min_dimensions": 2,
                "max_dimensions": 2,
                "min_metrics": 1,
                "max_metrics": 1,
                "requires_temporal": False,
                "best_for": ["composition", "part_to_whole"],
                "data_pattern": "multiple_categorical_with_single_metric",
            },

            # 占比类图表
            ChartType.PIE: {
                "name": "饼图",
                "min_dimensions": 1,
                "max_dimensions": 1,
                "min_metrics": 1,
                "max_metrics": 1,
                "requires_temporal": False,
                "best_for": ["proportion", "composition"],
                "max_categories": 10,
                "data_pattern": "single_categorical_with_single_metric",
            },
            ChartType.DONUT: {
                "name": "环形图",
                "min_dimensions": 1,
                "max_dimensions": 1,
                "min_metrics": 1,
                "max_metrics": 1,
                "requires_temporal": False,
                "best_for": ["proportion", "composition"],
                "max_categories": 10,
                "data_pattern": "single_categorical_with_single_metric",
            },

            # 分布类图表
            ChartType.SCATTER: {
                "name": "散点图",
                "min_dimensions": 1,
                "max_dimensions": 2,
                "min_metrics": 2,
                "max_metrics": 3,
                "requires_temporal": False,
                "best_for": ["correlation", "distribution", "outliers"],
                "data_pattern": "multiple_numeric_metrics",
            },
            ChartType.HISTOGRAM: {
                "name": "直方图",
                "min_dimensions": 0,
                "max_dimensions": 1,
                "min_metrics": 1,
                "max_metrics": 1,
                "requires_temporal": False,
                "best_for": ["distribution", "frequency"],
                "data_pattern": "single_numeric_metric",
            },
            ChartType.BOX_PLOT: {
                "name": "箱线图",
                "min_dimensions": 1,
                "max_dimensions": 1,
                "min_metrics": 1,
                "max_metrics": 1,
                "requires_temporal": False,
                "best_for": ["distribution", "statistics", "outliers"],
                "data_pattern": "categorical_with_numeric_metric",
            },

            # 关系类图表
            ChartType.HEATMAP: {
                "name": "热力图",
                "min_dimensions": 2,
                "max_dimensions": 2,
                "min_metrics": 1,
                "max_metrics": 1,
                "requires_temporal": False,
                "best_for": ["correlation", "intensity", "matrix"],
                "data_pattern": "two_categorical_with_numeric_metric",
            },

            # 表格类
            ChartType.TABLE: {
                "name": "表格",
                "min_dimensions": 0,
                "max_dimensions": 10,
                "min_metrics": 0,
                "max_metrics": 10,
                "requires_temporal": False,
                "best_for": ["detailed_view", "exact_values"],
                "data_pattern": "any",
            },
            ChartType.PIVOT_TABLE: {
                "name": "透视表",
                "min_dimensions": 2,
                "max_dimensions": 3,
                "min_metrics": 1,
                "max_metrics": 5,
                "requires_temporal": False,
                "best_for": ["aggregation", "multi_dimension_analysis"],
                "data_pattern": "multiple_dimensions_with_metrics",
            },

            # 其他
            ChartType.GAUGE: {
                "name": "仪表盘",
                "min_dimensions": 0,
                "max_dimensions": 0,
                "min_metrics": 1,
                "max_metrics": 1,
                "requires_temporal": False,
                "best_for": ["kpi", "target", "percentage"],
                "data_pattern": "single_numeric_metric_with_target",
            },
            ChartType.FUNNEL: {
                "name": "漏斗图",
                "min_dimensions": 1,
                "max_dimensions": 1,
                "min_metrics": 1,
                "max_metrics": 1,
                "requires_temporal": False,
                "best_for": ["conversion", "funnel", "stages"],
                "max_categories": 8,
                "data_pattern": "ordered_categorical_with_metric",
            },
        }

    def analyze_columns(
        self,
        columns: List[Dict[str, Any]],
        sample_data: Optional[List[Dict[str, Any]]] = None
    ) -> Tuple[List[ColumnInfo], List[ColumnInfo]]:
        """
        分析列，识别维度和度量

        Args:
            columns: 列定义列表
            sample_data: 样本数据

        Returns:
            (维度列表, 度量列表)
        """
        dimensions = []
        metrics = []

        for col in columns:
            col_name = col.get("name") or col.get("column_name")
            col_type = col.get("type") or col.get("column_type", "text")

            # 推断数据类型
            data_type = self._infer_data_type(col_name, col_type, col, sample_data)

            # 判断是维度还是度量
            if data_type in [DataType.NUMERIC]:
                # 数值型可能是度量，也可能是维度（如ID）
                if self._is_metric_column(col_name):
                    metrics.append(ColumnInfo(
                        name=col_name,
                        data_type=data_type,
                        distinct_count=col.get("distinct_count"),
                        null_count=col.get("null_count"),
                    ))
                else:
                    dimensions.append(ColumnInfo(
                        name=col_name,
                        data_type=DataType.CATEGORICAL,
                        distinct_count=col.get("distinct_count"),
                        null_count=col.get("null_count"),
                    ))
            elif data_type == DataType.TEMPORAL:
                dimensions.append(ColumnInfo(
                    name=col_name,
                    data_type=data_type,
                    distinct_count=col.get("distinct_count"),
                    null_count=col.get("null_count"),
                ))
            else:
                dimensions.append(ColumnInfo(
                    name=col_name,
                    data_type=data_type,
                    distinct_count=col.get("distinct_count"),
                    null_count=col.get("null_count"),
                ))

        return dimensions, metrics

    def _infer_data_type(
        self,
        col_name: str,
        col_type: str,
        col_def: Dict[str, Any],
        sample_data: Optional[List[Dict[str, Any]]] = None
    ) -> DataType:
        """推断列的数据类型"""
        col_type_lower = col_type.lower()
        col_name_lower = col_name.lower()

        # 时间类型判断
        if any(t in col_type_lower for t in ["date", "time", "timestamp"]):
            return DataType.TEMPORAL
        if any(kw in col_name_lower for kw in ["time", "date", "created", "updated"]):
            return DataType.TEMPORAL

        # 数值类型判断
        if any(t in col_type_lower for t in ["int", "decimal", "numeric", "float", "double"]):
            return DataType.NUMERIC
        if any(kw in col_name_lower for kw in ["count", "amount", "price", "quantity", "score"]):
            return DataType.NUMERIC

        # 布尔类型
        if "bool" in col_type_lower or col_name_lower.startswith("is_") or col_name_lower.startswith("has_"):
            return DataType.BOOLEAN

        # 地理类型
        if any(kw in col_name_lower for kw in ["country", "city", "province", "region", "lat", "lng", "geo"]):
            return DataType.GEOGRAPHIC

        # 默认文本类型
        return DataType.CATEGORICAL

    def _is_metric_column(self, col_name: str) -> bool:
        """判断是否是度量列"""
        metric_keywords = [
            "count", "sum", "amount", "price", "cost", "revenue", "profit",
            "quantity", "num", "total", "avg", "score", "rate", "ratio",
            "value", "balance", "volume", "weight", "size", "duration",
        ]

        col_name_lower = col_name.lower()
        return any(kw in col_name_lower for kw in metric_keywords)

    def recommend(
        self,
        dimensions: List[ColumnInfo],
        metrics: List[ColumnInfo],
        row_count: int = 0,
        user_intent: Optional[str] = None,
    ) -> List[ChartRecommendation]:
        """
        推荐图表类型

        Args:
            dimensions: 维度列表
            metrics: 度量列表
            row_count: 行数
            user_intent: 用户意图（可选）

        Returns:
            推荐结果列表，按置信度排序
        """
        recommendations = []

        # 分析数据模式
        data_pattern = self._analyze_data_pattern(dimensions, metrics)

        # 遍历所有图表类型进行匹配
        for chart_type, pattern in self.chart_patterns.items():
            score = self._calculate_match_score(
                chart_type, pattern, dimensions, metrics, data_pattern, user_intent
            )

            if score > 0:
                # 生成推荐配置
                config, dims, mets = self._generate_chart_config(
                    chart_type, dimensions, metrics
                )

                recommendation = ChartRecommendation(
                    chart_type=chart_type,
                    chart_name=pattern["name"],
                    confidence=score,
                    reason=self._generate_reason(chart_type, pattern, dimensions, metrics),
                    config=config,
                    dimensions=dims,
                    metrics=mets,
                )
                recommendations.append(recommendation)

        # 按置信度排序
        recommendations.sort(key=lambda r: r.confidence, reverse=True)

        # 只返回置信度 > 0.3 的推荐
        return [r for r in recommendations if r.confidence > 0.3][:5]

    def _analyze_data_pattern(
        self,
        dimensions: List[ColumnInfo],
        metrics: List[ColumnInfo]
    ) -> str:
        """分析数据模式"""
        has_temporal = any(d.data_type == DataType.TEMPORAL for d in dimensions)
        has_geo = any(d.data_type == DataType.GEOGRAPHIC for d in dimensions)

        num_dims = len(dimensions)
        num_metrics = len(metrics)

        if has_temporal and num_metrics >= 1:
            return "temporal_dimension_with_numeric_metrics"
        elif num_dims >= 2 and num_metrics == 1:
            return "multiple_categorical_with_single_metric"
        elif num_dims == 1 and num_metrics == 1:
            if dimensions[0].data_type == DataType.CATEGORICAL:
                if dimensions[0].distinct_count and dimensions[0].distinct_count <= 10:
                    return "single_categorical_with_single_metric"
            return "categorical_dimension_with_numeric_metric"
        elif num_metrics >= 2 and num_dims <= 1:
            return "multiple_numeric_metrics"
        elif num_dims == 2 and num_metrics == 1:
            return "two_categorical_with_numeric_metric"
        else:
            return "general"

    def _calculate_match_score(
        self,
        chart_type: ChartType,
        pattern: Dict,
        dimensions: List[ColumnInfo],
        metrics: List[ColumnInfo],
        data_pattern: str,
        user_intent: Optional[str]
    ) -> float:
        """计算匹配分数"""
        score = 0.0

        num_dims = len(dimensions)
        num_metrics = len(metrics)

        # 基本数量匹配
        if (pattern["min_dimensions"] <= num_dims <= pattern["max_dimensions"] and
            pattern["min_metrics"] <= num_metrics <= pattern["max_metrics"]):
            score += 0.4

        # 时间维度要求
        if pattern.get("requires_temporal"):
            has_temporal = any(d.data_type == DataType.TEMPORAL for d in dimensions)
            if has_temporal:
                score += 0.3
            else:
                score -= 0.2

        # 数据模式匹配
        if pattern.get("data_pattern") == data_pattern:
            score += 0.3

        # 用户意图匹配
        if user_intent:
            intent_lower = user_intent.lower()
            for best_for in pattern.get("best_for", []):
                if best_for in intent_lower:
                    score += 0.2
                    break

        # 类别数量限制
        if "max_categories" in pattern and dimensions:
            if dimensions[0].distinct_count and dimensions[0].distinct_count > pattern["max_categories"]:
                score -= 0.3

        return min(score, 1.0)

    def _generate_chart_config(
        self,
        chart_type: ChartType,
        dimensions: List[ColumnInfo],
        metrics: List[ColumnInfo]
    ) -> Tuple[Dict[str, Any], List[str], List[str]]:
        """生成图表配置"""
        config = {
            "chart_type": chart_type.value,
            "options": self._get_default_options(chart_type),
        }

        # 选择推荐使用的维度和度量
        selected_dims = []
        selected_metrics = []

        if chart_type in [ChartType.LINE, ChartType.AREA]:
            # 优先选择时间维度
            temporal_dims = [d.name for d in dimensions if d.data_type == DataType.TEMPORAL]
            if temporal_dims:
                selected_dims = [temporal_dims[0]]
            elif dimensions:
                selected_dims = [dimensions[0].name]
            selected_metrics = [m.name for m in metrics[:3]]

        elif chart_type in [ChartType.PIE, ChartType.DONUT]:
            if dimensions:
                selected_dims = [dimensions[0].name]
            if metrics:
                selected_metrics = [metrics[0].name]

        elif chart_type in [ChartType.SCATTER]:
            selected_metrics = [m.name for m in metrics[:2]]
            if dimensions:
                selected_dims = [dimensions[0].name]

        elif chart_type in [ChartType.HEATMAP]:
            selected_dims = [d.name for d in dimensions[:2]]
            if metrics:
                selected_metrics = [metrics[0].name]

        else:
            # 默认选择前几个
            selected_dims = [d.name for d in dimensions[:2]]
            selected_metrics = [m.name for m in metrics[:3]]

        config["dimensions"] = selected_dims
        config["metrics"] = selected_metrics

        return config, selected_dims, selected_metrics

    def _get_default_options(self, chart_type: ChartType) -> Dict[str, Any]:
        """获取图表默认配置"""
        base_options = {
            "legend": {"show": True},
            "tooltip": {"show": True},
        }

        specific_options = {
            ChartType.LINE: {
                "smooth": True,
                "areaStyle": {"opacity": 0.1},
            },
            ChartType.COLUMN: {
                "columnWidthRatio": 0.6,
            },
            ChartType.PIE: {
                "radius": ["40%", "70%"],
                "label": {"show": True, "formatter": "{b}: {d}%"},
            },
            ChartType.SCATTER: {
                "symbolSize": 8,
            },
        }

        return {**base_options, **specific_options.get(chart_type, {})}

    def _generate_reason(
        self,
        chart_type: ChartType,
        pattern: Dict,
        dimensions: List[ColumnInfo],
        metrics: List[ColumnInfo]
    ) -> str:
        """生成推荐理由"""
        reasons = []

        # 基于数据特征的理由
        if pattern.get("requires_temporal"):
            has_temporal = any(d.data_type == DataType.TEMPORAL for d in dimensions)
            if has_temporal:
                reasons.append("包含时间维度，适合展示趋势变化")

        # 基于用途的理由
        best_for = pattern.get("best_for", [])
        if best_for:
            use_cases = {
                "trend": "趋势分析",
                "comparison": "数据对比",
                "proportion": "占比分析",
                "distribution": "分布分析",
                "correlation": "相关性分析",
                "composition": "构成分析",
                "ranking": "排名展示",
            }
            for bf in best_for[:2]:
                if bf in use_cases:
                    reasons.append(f"适合{use_cases[bf]}")

        return "；".join(reasons) if reasons else "根据数据特征推荐"

    def recommend_from_sql_result(
        self,
        columns: List[str],
        rows: List[Dict[str, Any]],
        user_intent: Optional[str] = None
    ) -> List[ChartRecommendation]:
        """
        从SQL查询结果推荐图表

        Args:
            columns: 列名列表
            rows: 数据行
            user_intent: 用户意图

        Returns:
            推荐结果列表
        """
        # 分析列类型
        col_infos = []
        for col in columns:
            col_type = self._infer_type_from_data(col, rows)
            col_infos.append({
                "name": col,
                "type": col_type,
            })

        dimensions, metrics = self.analyze_columns(col_infos, rows)

        return self.recommend(dimensions, metrics, len(rows), user_intent)

    def _infer_type_from_data(self, col_name: str, rows: List[Dict[str, Any]]) -> str:
        """从数据推断列类型"""
        if not rows:
            return "text"

        values = [row.get(col_name) for row in rows[:100] if row.get(col_name) is not None]

        if not values:
            return "text"

        # 检查是否是数值
        numeric_count = sum(1 for v in values if isinstance(v, (int, float)))
        if numeric_count / len(values) > 0.8:
            return "numeric"

        # 检查是否是时间
        import re
        datetime_pattern = re.compile(r'\d{4}[-/]\d{1,2}[-/]\d{1,2}')
        datetime_count = sum(1 for v in values if isinstance(v, str) and datetime_pattern.search(v))
        if datetime_count / len(values) > 0.5:
            return "datetime"

        return "text"


# 全局实例
_chart_recommender: Optional[ChartRecommender] = None


def get_chart_recommender() -> ChartRecommender:
    """获取图表推荐器单例"""
    global _chart_recommender
    if _chart_recommender is None:
        _chart_recommender = ChartRecommender()
    return _chart_recommender
