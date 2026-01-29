"""
SQL 结果解释器
Production: 将 SQL 查询结果转换为自然语言描述和可视化配置

功能：
1. 结果摘要生成（自然语言）
2. 数据洞察提取（趋势、异常值、极值）
3. 图表配置生成（ECharts/Highcharts）
4. 数据分布分析
5. 时间序列分析
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import statistics
from collections import Counter

logger = logging.getLogger(__name__)


class ChartType(Enum):
    """图表类型"""
    TABLE = "table"
    BAR = "bar"
    LINE = "line"
    PIE = "pie"
    AREA = "area"
    SCATTER = "scatter"
    HEATMAP = "heatmap"
    GAUGE = "gauge"
    FUNNEL = "funnel"


class InsightType(Enum):
    """洞察类型"""
    SUMMARY = "summary"
    TREND = "trend"
    OUTLIER = "outlier"
    CORRELATION = "correlation"
    DISTRIBUTION = "distribution"
    COMPARISON = "comparison"


@dataclass
class DataInsight:
    """数据洞察"""
    insight_type: InsightType
    title: str
    description: str
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ChartConfig:
    """图表配置"""
    chart_type: ChartType
    title: str
    x_axis: Optional[str] = None
    y_axis: Optional[List[str]] = None
    series: List[Dict[str, Any]] = field(default_factory=list)
    options: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "type": self.chart_type.value,
            "title": self.title,
            "xAxis": self.x_axis,
            "yAxis": self.y_axis,
            "series": self.series,
            "options": self.options,
        }


@dataclass
class InterpretationResult:
    """解释结果"""
    summary: str                       # 自然语言摘要
    insights: List[DataInsight]        # 数据洞察列表
    charts: List[ChartConfig]          # 图表配置列表
    row_count: int                     # 行数
    column_count: int                  # 列数
    execution_time: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class ResultInterpreter:
    """
    SQL 结果解释器

    功能：
    - 结果摘要生成
    - 数据洞察提取
    - 图表配置生成
    """

    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化解释器

        Args:
            config: 配置字典
                - max_rows: 分析的最大行数（默认1000）
                - max_chart_series: 最大图表系列数（默认10）
                - enable_insights: 是否启用洞察提取（默认True）
                - language: 摘要语言（默认"zh"）
        """
        self.config = config or {}
        self.max_rows = self.config.get("max_rows", 1000)
        self.max_chart_series = self.config.get("max_chart_series", 10)
        self.enable_insights = self.config.get("enable_insights", True)
        self.language = self.config.get("language", "zh")

        # 数值列模式
        self.numeric_pattern = re.compile(r'^-?\d+\.?\d*$')

        # 时间列模式
        self.datetime_patterns = [
            re.compile(r'\d{4}-\d{2}-\d{2}'),  # YYYY-MM-DD
            re.compile(r'\d{4}/\d{2}/\d{2}'),  # YYYY/MM/DD
            re.compile(r'\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}'),  # ISO datetime
        ]

        # 聚合关键词
        self.aggregate_keywords = {
            "count", "sum", "avg", "average", "mean", "max", "min",
            "总数", "求和", "平均", "最大", "最小", "计数"
        }

    def interpret(
        self,
        result: List[Dict[str, Any]],
        query: Optional[str] = None,
        execution_time: Optional[float] = None,
    ) -> InterpretationResult:
        """
        解释 SQL 查询结果

        Args:
            result: 查询结果列表
            query: 原始 SQL 查询（可选）
            execution_time: 执行时间（秒）

        Returns:
            InterpretationResult 解释结果
        """
        if not result:
            return InterpretationResult(
                summary="查询未返回任何结果",
                insights=[],
                charts=[],
                row_count=0,
                column_count=0,
                execution_time=execution_time,
            )

        # 限制分析行数
        analyzed_result = result[:self.max_rows]

        # 分析列信息
        columns = list(analyzed_result[0].keys()) if analyzed_result else []
        column_info = self._analyze_columns(analyzed_result, columns)

        # 生成摘要
        summary = self._generate_summary(
            analyzed_result, columns, column_info, query
        )

        # 提取洞察
        insights = []
        if self.enable_insights:
            insights = self._extract_insights(
                analyzed_result, columns, column_info, query
            )

        # 生成图表配置
        charts = self._generate_charts(
            analyzed_result, columns, column_info, query
        )

        return InterpretationResult(
            summary=summary,
            insights=insights,
            charts=charts,
            row_count=len(result),
            column_count=len(columns),
            execution_time=execution_time,
            metadata={
                "has_aggregation": self._has_aggregation(query),
                "has_group_by": self._has_group_by(query),
                "has_order_by": self._has_order_by(query),
                "truncated": len(result) > self.max_rows,
            }
        )

    def _analyze_columns(
        self,
        result: List[Dict[str, Any]],
        columns: List[str],
    ) -> Dict[str, Dict[str, Any]]:
        """分析每列的数据类型和统计信息"""
        column_info = {}

        for col in columns:
            values = [row.get(col) for row in result if row.get(col) is not None]

            if not values:
                column_info[col] = {"type": "unknown", "nullable": True}
                continue

            # 检测数据类型
            col_type = self._detect_column_type(col, values)

            info = {
                "type": col_type,
                "nullable": len(values) < len(result),
                "sample_values": values[:5],
            }

            if col_type == "numeric":
                numeric_values = [v for v in values if isinstance(v, (int, float))]
                if numeric_values:
                    info.update({
                        "min": min(numeric_values),
                        "max": max(numeric_values),
                        "mean": statistics.mean(numeric_values),
                        "median": statistics.median(numeric_values),
                    })
                    if len(numeric_values) > 1:
                        info["std"] = statistics.stdev(numeric_values)

            elif col_type == "categorical":
                unique_count = len(set(values))
                value_counts = Counter(values)
                info.update({
                    "unique_count": unique_count,
                    "most_common": value_counts.most_common(3),
                    "cardinality": "high" if unique_count > 50 else "low",
                })

            elif col_type == "datetime":
                # 尝试解析时间值
                datetimes = self._parse_datetimes(values)
                if datetimes:
                    info.update({
                        "min_date": min(datetimes),
                        "max_date": max(datetimes),
                        "time_range_days": (max(datetimes) - min(datetimes)).days,
                    })

            column_info[col] = info

        return column_info

    def _detect_column_type(self, col_name: str, values: List[Any]) -> str:
        """检测列数据类型"""
        # 检查列名提示
        col_lower = col_name.lower()
        if any(kw in col_lower for kw in ["date", "time", "created", "updated"]):
            return "datetime"
        if any(kw in col_lower for kw in ["id", "key", "code"]):
            return "id"

        # 基于值检测
        sample = values[:min(100, len(values))]

        # 检查数值类型
        numeric_count = sum(1 for v in sample if isinstance(v, (int, float)) and not isinstance(v, bool))
        if numeric_count / len(sample) > 0.8:
            return "numeric"

        # 检查时间类型
        datetime_count = 0
        for v in sample:
            if isinstance(v, str):
                for pattern in self.datetime_patterns:
                    if pattern.search(v):
                        datetime_count += 1
                        break
        if datetime_count / len(sample) > 0.5:
            return "datetime"

        # 检查低基数分类
        unique_ratio = len(set(str(v) for v in sample)) / len(sample)
        if unique_ratio < 0.5:
            return "categorical"

        return "text"

    def _parse_datetimes(self, values: List[Any]) -> List[datetime]:
        """尝试解析时间值"""
        datetimes = []
        for v in values[:100]:
            try:
                if isinstance(v, datetime):
                    datetimes.append(v)
                elif isinstance(v, str):
                    # 尝试多种格式
                    for fmt in [
                        "%Y-%m-%d %H:%M:%S",
                        "%Y-%m-%d",
                        "%Y/%m/%d",
                        "%Y-%m-%dT%H:%M:%S",
                        "%Y-%m-%dT%H:%M:%S.%f",
                    ]:
                        try:
                            datetimes.append(datetime.strptime(v, fmt))
                            break
                        except ValueError:
                            continue
            except Exception:
                continue
        return datetimes

    def _generate_summary(
        self,
        result: List[Dict[str, Any]],
        columns: List[str],
        column_info: Dict[str, Dict[str, Any]],
        query: Optional[str],
    ) -> str:
        """生成结果摘要"""
        if not result:
            return "查询未返回结果"

        lines = [f"查询返回 {len(result)} 行数据，包含 {len(columns)} 列。"]

        # 分析查询类型
        if query and self._has_aggregation(query):
            lines.append("这是一个聚合查询。")

        # 描述关键列
        numeric_cols = [c for c, info in column_info.items() if info["type"] == "numeric"]
        categorical_cols = [c for c, info in column_info.items() if info["type"] == "categorical"]
        datetime_cols = [c for c, info in column_info.items() if info["type"] == "datetime"]

        if numeric_cols:
            main_col = numeric_cols[0]
            info = column_info[main_col]
            if "mean" in info:
                lines.append(
                    f"数值列「{main_col}」的平均值为 {info['mean']:.2f}，"
                    f"范围从 {info['min']} 到 {info['max']}。"
                )

        if categorical_cols:
            main_col = categorical_cols[0]
            info = column_info[main_col]
            lines.append(
                f"分类列「{main_col}」包含 {info['unique_count']} 个唯一值。"
            )

        if datetime_cols:
            main_col = datetime_cols[0]
            info = column_info[main_col]
            if "time_range_days" in info:
                lines.append(
                    f"时间列「{main_col}」跨度 {info['time_range_days']} 天。"
                )

        return " ".join(lines)

    def _extract_insights(
        self,
        result: List[Dict[str, Any]],
        columns: List[str],
        column_info: Dict[str, Dict[str, Any]],
        query: Optional[str],
    ) -> List[DataInsight]:
        """提取数据洞察"""
        insights = []

        # 1. 数值列统计洞察
        for col, info in column_info.items():
            if info["type"] == "numeric" and "mean" in info:
                # 检测偏度
                if "median" in info and "mean" in info:
                    skew = info["mean"] - info["median"]
                    if abs(skew) / abs(info["median"]) > 0.2:
                        direction = "右偏" if skew > 0 else "左偏"
                        insights.append(DataInsight(
                            insight_type=InsightType.DISTRIBUTION,
                            title=f"「{col}」分布{direction}",
                            description=f"平均值 ({info['mean']:.2f}) 与中位数 ({info['median']:.2f}) 差异较大",
                            metadata={"skew": skew, "mean": info["mean"], "median": info["median"]},
                        ))

                # 检测异常值
                if "std" in info and "mean" in info:
                    values = [row.get(col) for row in result if isinstance(row.get(col), (int, float))]
                    outliers = [v for v in values if abs(v - info["mean"]) > 2 * info["std"]]
                    if outliers:
                        insights.append(DataInsight(
                            insight_type=InsightType.OUTLIER,
                            title=f"「{col}」发现 {len(outliers)} 个潜在异常值",
                            description=f"约 {len(outliers)/len(values)*100:.1f}% 的值偏离平均值超过 2 个标准差",
                            metadata={"outlier_count": len(outliers), "total": len(values)},
                        ))

        # 2. 分类列洞察
        for col, info in column_info.items():
            if info["type"] == "categorical" and "most_common" in info:
                most_common = info["most_common"]
                if most_common:
                    top_value, top_count = most_common[0]
                    total = sum(row.get(col) is not None for row in result)
                    if total > 0:
                        ratio = top_count / total
                        if ratio > 0.5:
                            insights.append(DataInsight(
                                insight_type=InsightType.DISTRIBUTION,
                                title=f"「{col}」高度集中",
                                description=f"最常见值「{top_value}」占比 {ratio*100:.1f}%",
                                metadata={"value": top_value, "ratio": ratio},
                            ))

        # 3. 时间序列洞察
        for col, info in column_info.items():
            if info["type"] == "datetime" and "min_date" in info:
                days = info["time_range_days"]
                if days > 0:
                    insights.append(DataInsight(
                        insight_type=InsightType.TREND,
                        title=f"「{col}」时间跨度 {days} 天",
                        description=f"数据时间范围从 {info['min_date'].date()} 到 {info['max_date'].date()}",
                        metadata={"days": days, "start": str(info["min_date"]), "end": str(info["max_date"])},
                    ))

        # 4. Top-N 洞察（针对聚合查询）
        if query and self._has_aggregation(query) and self._has_order_by(query):
            # 获取排序列
            for col, info in column_info.items():
                if info["type"] == "numeric":
                    # 找到最大值
                    sorted_result = sorted(result, key=lambda r: r.get(col, 0), reverse=True)
                    if len(sorted_result) >= 3:
                        top_3 = sorted_result[:3]
                        insights.append(DataInsight(
                            insight_type=InsightType.COMPARISON,
                            title=f"「{col}」Top 3",
                            description=self._format_top_values(top_3, col, columns),
                            metadata={"top_values": top_3},
                        ))
                    break

        return insights[:10]  # 限制洞察数量

    def _format_top_values(
        self,
        top_rows: List[Dict[str, Any]],
        value_col: str,
        all_columns: List[str],
    ) -> str:
        """格式化 Top 值"""
        # 找到标签列（非数值列）
        label_col = None
        for col in all_columns:
            if col != value_col and col not in column_info:
                # 假设这是标签列
                label_col = col
                break

        parts = []
        for i, row in enumerate(top_rows, 1):
            if label_col and label_col in row:
                parts.append(f"第{i}名：{row[label_col]}（{row[value_col]}）")
            else:
                parts.append(f"第{i}名：{row[value_col]}")

        return "；".join(parts)

    def _generate_charts(
        self,
        result: List[Dict[str, Any]],
        columns: List[str],
        column_info: Dict[str, Dict[str, Any]],
        query: Optional[str],
    ) -> List[ChartConfig]:
        """生成图表配置"""
        charts = []

        if not result:
            return charts

        # 1. 表格图表（默认）
        if len(result) <= 100:
            charts.append(self._create_table_chart(result, columns))

        # 2. 柱状图/折线图（分类-数值）
        categorical_cols = [c for c, info in column_info.items() if info["type"] == "categorical"]
        numeric_cols = [c for c, info in column_info.items() if info["type"] == "numeric"]

        if categorical_cols and numeric_cols and len(result) <= 50:
            cat_col = categorical_cols[0]
            num_col = numeric_cols[0]

            # 判断图表类型
            chart_type = ChartType.BAR
            if query and any(kw in query.lower() for kw in ["trend", "时间", "date", "time"]):
                chart_type = ChartType.LINE

            charts.append(self._create_xy_chart(
                result, cat_col, num_col, chart_type
            ))

        # 3. 饼图（单分类分布）
        if categorical_cols and len(result) <= 20:
            cat_col = categorical_cols[0]
            if column_info[cat_col].get("unique_count", 20) <= 10:
                # 找到数值列作为计数
                count_col = None
                for col in numeric_cols:
                    if "count" in col.lower() or "数量" in col:
                        count_col = col
                        break

                if count_col:
                    charts.append(self._create_pie_chart(result, cat_col, count_col))

        # 4. 时间序列图
        datetime_cols = [c for c, info in column_info.items() if info["type"] == "datetime"]
        if datetime_cols and numeric_cols:
            charts.append(self._create_timeseries_chart(
                result, datetime_cols[0], numeric_cols[0]
            ))

        # 5. 多列对比图
        if len(numeric_cols) >= 2 and len(result) <= 20:
            charts.append(self._create_multi_series_chart(
                result, categorical_cols[0] if categorical_cols else columns[0],
                numeric_cols[:3]
            ))

        return charts[:5]  # 限制图表数量

    def _create_table_chart(
        self,
        result: List[Dict[str, Any]],
        columns: List[str],
    ) -> ChartConfig:
        """创建表格图表"""
        return ChartConfig(
            chart_type=ChartType.TABLE,
            title="数据表格",
            x_axis=columns[0] if columns else None,
            series=[{
                "type": "table",
                "data": result[:100],
                "columns": columns,
            }],
            options={
                "pagination": len(result) > 50,
                "pageSize": 20,
            }
        )

    def _create_xy_chart(
        self,
        result: List[Dict[str, Any]],
        x_col: str,
        y_col: str,
        chart_type: ChartType,
    ) -> ChartConfig:
        """创建 X-Y 图表"""
        return ChartConfig(
            chart_type=chart_type,
            title=f"{x_col} vs {y_col}",
            x_axis=x_col,
            y_axis=[y_col],
            series=[{
                "name": y_col,
                "data": [[r.get(x_col), r.get(y_col)] for r in result if r.get(y_col) is not None],
                "type": chart_type.value,
            }],
            options={
                "smooth": chart_type == ChartType.LINE,
                "dataZoom": len(result) > 20,
            }
        )

    def _create_pie_chart(
        self,
        result: List[Dict[str, Any]],
        label_col: str,
        value_col: str,
    ) -> ChartConfig:
        """创建饼图"""
        return ChartConfig(
            chart_type=ChartType.PIE,
            title=f"{label_col} 分布",
            series=[{
                "name": value_col,
                "data": [
                    {"name": r.get(label_col), "value": r.get(value_col)}
                    for r in result
                    if r.get(value_col) is not None
                ],
                "type": "pie",
            }],
            options={
                "radius": "70%",
                "label": {"show": True},
            }
        )

    def _create_timeseries_chart(
        self,
        result: List[Dict[str, Any]],
        time_col: str,
        value_col: str,
    ) -> ChartConfig:
        """创建时间序列图"""
        return ChartConfig(
            chart_type=ChartType.LINE,
            title=f"{value_col} 趋势",
            x_axis=time_col,
            y_axis=[value_col],
            series=[{
                "name": value_col,
                "data": [[r.get(time_col), r.get(value_col)] for r in result],
                "type": "line",
                "smooth": True,
            }],
            options={
                "dataZoom": [{"type": "slider"}, {"type": "inside"}],
            }
        )

    def _create_multi_series_chart(
        self,
        result: List[Dict[str, Any]],
        x_col: str,
        y_cols: List[str],
    ) -> ChartConfig:
        """创建多系列图表"""
        series = []
        for y_col in y_cols:
            series.append({
                "name": y_col,
                "data": [r.get(y_col) for r in result],
                "type": "bar",
            })

        return ChartConfig(
            chart_type=ChartType.BAR,
            title="多指标对比",
            x_axis=x_col,
            y_axis=y_cols,
            series=series,
            options={
                "legend": {"show": True},
                "tooltip": {"trigger": "axis"},
            }
        )

    def _has_aggregation(self, query: Optional[str]) -> bool:
        """检查是否为聚合查询"""
        if not query:
            return False
        query_upper = query.upper()
        return any(kw in query_upper for kw in ["COUNT(", "SUM(", "AVG(", "MAX(", "MIN(", "GROUP BY"])

    def _has_group_by(self, query: Optional[str]) -> bool:
        """检查是否有 GROUP BY"""
        return query and "GROUP BY" in query.upper()

    def _has_order_by(self, query: Optional[str]) -> bool:
        """检查是否有 ORDER BY"""
        return query and "ORDER BY" in query.upper()


# ==================== 全局实例 ====================

_interpreter: Optional[ResultInterpreter] = None


def get_result_interpreter(config: Dict[str, Any] = None) -> ResultInterpreter:
    """获取全局解释器实例"""
    global _interpreter
    if _interpreter is None:
        _interpreter = ResultInterpreter(config)
    return _interpreter


# ==================== 便捷函数 ====================

def interpret_result(
    result: List[Dict[str, Any]],
    query: Optional[str] = None,
    execution_time: Optional[float] = None,
) -> InterpretationResult:
    """
    解释 SQL 查询结果（便捷函数）

    Args:
        result: 查询结果列表
        query: 原始 SQL 查询
        execution_time: 执行时间（秒）

    Returns:
        InterpretationResult 解释结果
    """
    interpreter = get_result_interpreter()
    return interpreter.interpret(result, query, execution_time)


def generate_narrative(
    result: InterpretationResult,
    language: str = "zh",
) -> str:
    """
    生成自然语言叙述

    Args:
        result: 解释结果
        language: 语言（"zh" 或 "en"）

    Returns:
        自然语言叙述
    """
    narrative = [result.summary]

    if result.insights:
        narrative.append("\n关键洞察：")
        for insight in result.insights:
            narrative.append(f"• {insight.title}: {insight.description}")

    if result.charts:
        narrative.append(f"\n生成了 {len(result.charts)} 个可视化图表。")

    return "\n".join(narrative)


def suggest_visualization(
    result: List[Dict[str, Any]],
    columns: List[str],
) -> Optional[ChartConfig]:
    """
    建议最合适的可视化方式（便捷函数）

    Args:
        result: 查询结果
        columns: 列名列表

    Returns:
        推荐的图表配置
    """
    interpreter = get_result_interpreter()
    column_info = interpreter._analyze_columns(result, columns)
    charts = interpreter._generate_charts(result, columns, column_info, None)
    return charts[0] if charts else None
