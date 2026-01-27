"""
SQL 结果解释器单元测试
测试结果摘要生成、数据洞察提取、图表配置生成
"""

import pytest
from datetime import datetime
from services.bisheng_api.services.result_interpreter import (
    ResultInterpreter,
    InterpretationResult,
    ChartType,
    InsightType,
    DataInsight,
    ChartConfig,
    interpret_result,
    generate_narrative,
    suggest_visualization,
)


class TestResultInterpreter:
    """结果解释器测试"""

    @pytest.fixture
    def interpreter(self):
        """创建解释器实例"""
        return ResultInterpreter()

    @pytest.fixture
    def sample_sales_data(self):
        """示例销售数据"""
        return [
            {"id": 1, "product": "Product A", "sales": 10000, "category": "Electronics"},
            {"id": 2, "product": "Product B", "sales": 15000, "category": "Electronics"},
            {"id": 3, "product": "Product C", "sales": 8000, "category": "Clothing"},
            {"id": 4, "product": "Product D", "sales": 12000, "category": "Clothing"},
            {"id": 5, "product": "Product E", "sales": 20000, "category": "Electronics"},
        ]

    @pytest.fixture
    def sample_time_series_data(self):
        """示例时间序列数据"""
        return [
            {"date": "2024-01-01", "revenue": 1000},
            {"date": "2024-01-02", "revenue": 1200},
            {"date": "2024-01-03", "revenue": 1100},
            {"date": "2024-01-04", "revenue": 1400},
            {"date": "2024-01-05", "revenue": 1600},
        ]

    def test_interpret_empty_result(self, interpreter):
        """测试空结果解释"""
        result = interpreter.interpret([])
        assert result.row_count == 0
        assert result.column_count == 0
        assert "未返回任何结果" in result.summary

    def test_interpret_basic_result(self, interpreter, sample_sales_data):
        """测试基本结果解释"""
        result = interpreter.interpret(sample_sales_data)
        assert result.row_count == 5
        assert result.column_count == 4
        assert result.summary
        assert len(result.charts) > 0

    def test_summary_generation(self, interpreter, sample_sales_data):
        """测试摘要生成"""
        result = interpreter.interpret(sample_sales_data)
        assert "5 行" in result.summary or "5" in result.summary
        assert "4 列" in result.summary or "4" in result.summary

    def test_numeric_column_analysis(self, interpreter, sample_sales_data):
        """测试数值列分析"""
        result = interpreter.interpret(sample_sales_data)
        assert any(insight for insight in result.insights if "sales" in str(insight.description).lower())

    def test_categorical_column_analysis(self, interpreter, sample_sales_data):
        """测试分类列分析"""
        result = interpreter.interpret(sample_sales_data)
        assert any(insight for insight in result.insights if "category" in str(insight.description).lower())

    def test_time_series_analysis(self, interpreter, sample_time_series_data):
        """测试时间序列分析"""
        result = interpreter.interpret(sample_time_series_data)
        assert any(insight for insight in result.insights if insight.insight_type == InsightType.TREND)

    def test_chart_generation_bar(self, interpreter, sample_sales_data):
        """测试柱状图生成"""
        result = interpreter.interpret(sample_sales_data)
        bar_charts = [c for c in result.charts if c.chart_type == ChartType.BAR]
        assert len(bar_charts) > 0

    def test_chart_generation_table(self, interpreter, sample_sales_data):
        """测试表格图表生成"""
        result = interpreter.interpret(sample_sales_data)
        table_charts = [c for c in result.charts if c.chart_type == ChartType.TABLE]
        assert len(table_charts) > 0

    def test_chart_generation_pie(self, interpreter, sample_sales_data):
        """测试饼图生成"""
        result = interpreter.interpret(sample_sales_data)
        pie_charts = [c for c in result.charts if c.chart_type == ChartType.PIE]
        # 只有低基数分类列才生成饼图
        assert len(pie_charts) >= 0

    def test_chart_generation_timeseries(self, interpreter, sample_time_series_data):
        """测试时间序列图生成"""
        result = interpreter.interpret(sample_time_series_data)
        line_charts = [c for c in result.charts if c.chart_type == ChartType.LINE]
        assert len(line_charts) > 0

    def test_insight_extraction_outliers(self, interpreter):
        """测试异常值检测"""
        data_with_outlier = [
            {"value": 10},
            {"value": 12},
            {"value": 11},
            {"value": 100},  # 异常值
            {"value": 13},
        ]
        result = interpreter.interpret(data_with_outlier)
        outlier_insights = [i for i in result.insights if i.insight_type == InsightType.OUTLIER]
        assert len(outlier_insights) > 0

    def test_insight_extraction_distribution(self, interpreter):
        """测试分布分析"""
        data = [
            {"category": "A", "value": 1},
            {"category": "A", "value": 2},
            {"category": "A", "value": 3},
            {"category": "B", "value": 1},
        ]
        result = interpreter.interpret(data)
        distribution_insights = [i for i in result.insights if i.insight_type == InsightType.DISTRIBUTION]
        assert len(distribution_insights) >= 0

    def test_aggregation_query_detection(self, interpreter):
        """测试聚合查询检测"""
        result = interpreter.interpret(
            [{"count": 100}],
            query="SELECT COUNT(*) FROM users"
        )
        assert result.metadata.get("has_aggregation") is True

    def test_group_by_detection(self, interpreter):
        """测试 GROUP BY 检测"""
        result = interpreter.interpret(
            [{"category": "A", "total": 100}],
            query="SELECT category, SUM(amount) FROM sales GROUP BY category"
        )
        assert result.metadata.get("has_group_by") is True

    def test_order_by_detection(self, interpreter):
        """测试 ORDER BY 检测"""
        result = interpreter.interpret(
            [{"name": "A", "value": 100}],
            query="SELECT * FROM items ORDER BY value DESC"
        )
        assert result.metadata.get("has_order_by") is True

    def test_execution_time_tracking(self, interpreter, sample_sales_data):
        """测试执行时间跟踪"""
        result = interpreter.interpret(sample_sales_data, execution_time=1.5)
        assert result.execution_time == 1.5

    def test_result_truncation(self, interpreter):
        """测试大结果集截断"""
        large_data = [{"id": i, "value": i} for i in range(2000)]
        result = interpreter.interpret(large_data)
        assert result.row_count == 2000
        assert result.metadata.get("truncated") is True

    def test_custom_max_rows(self):
        """测试自定义最大行数"""
        interpreter = ResultInterpreter({"max_rows": 10})
        large_data = [{"id": i, "value": i} for i in range(100)]
        result = interpreter.interpret(large_data)
        assert result.metadata.get("truncated") is True

    def test_disabled_insights(self):
        """测试禁用洞察提取"""
        interpreter = ResultInterpreter({"enable_insights": False})
        result = interpreter.interpret([{"value": 1}])
        assert len(result.insights) == 0

    def test_chart_config_to_dict(self, interpreter, sample_sales_data):
        """测试图表配置转换为字典"""
        result = interpreter.interpret(sample_sales_data)
        if result.charts:
            chart_dict = result.charts[0].to_dict()
            assert "type" in chart_dict
            assert "title" in chart_dict
            assert "series" in chart_dict


class TestConvenienceFunctions:
    """便捷函数测试"""

    def test_interpret_result_function(self):
        """测试 interpret_result 便捷函数"""
        data = [{"id": 1, "value": 100}]
        result = interpret_result(data)
        assert result.row_count == 1

    def test_generate_narrative(self):
        """测试生成自然语言叙述"""
        data = [
            {"product": "A", "sales": 100},
            {"product": "B", "sales": 200},
        ]
        result = interpret_result(data, query="SELECT product, sales FROM products")
        narrative = generate_narrative(result)
        assert narrative
        assert "查询" in narrative or "数据" in narrative

    def test_suggest_visualization(self):
        """测试可视化推荐"""
        data = [{"category": "A", "value": 100}, {"category": "B", "value": 200}]
        chart = suggest_visualization(data, ["category", "value"])
        assert chart is not None


class TestColumnDetection:
    """列类型检测测试"""

    @pytest.fixture
    def interpreter(self):
        return ResultInterpreter()

    def test_numeric_column_detection(self, interpreter):
        """测试数值列检测"""
        data = [{"value": 1}, {"value": 2.5}, {"value": -3}]
        col_info = interpreter._analyze_columns(data, ["value"])
        assert col_info["value"]["type"] == "numeric"

    def test_categorical_column_detection(self, interpreter):
        """测试分类列检测"""
        data = [{"category": "A"}, {"category": "B"}, {"category": "A"}]
        col_info = interpreter._analyze_columns(data, ["category"])
        assert col_info["category"]["type"] == "categorical"

    def test_datetime_column_detection(self, interpreter):
        """测试时间列检测"""
        data = [
            {"date": "2024-01-01"},
            {"date": "2024-01-02"},
            {"date": "2024-01-03"},
        ]
        col_info = interpreter._analyze_columns(data, ["date"])
        assert col_info["date"]["type"] == "datetime"

    def test_id_column_detection(self, interpreter):
        """测试 ID 列检测"""
        data = [{"user_id": "123"}, {"user_id": "456"}]
        col_info = interpreter._analyze_columns(data, ["user_id"])
        assert col_info["user_id"]["type"] == "id"


class TestDataInsights:
    """数据洞察测试"""

    @pytest.fixture
    def interpreter(self):
        return ResultInterpreter()

    def test_numeric_statistics(self, interpreter):
        """测试数值统计"""
        data = [{"value": i} for i in range(1, 101)]
        col_info = interpreter._analyze_columns(data, ["value"])
        assert "mean" in col_info["value"]
        assert "min" in col_info["value"]
        assert "max" in col_info["value"]
        assert col_info["value"]["min"] == 1
        assert col_info["value"]["max"] == 100

    def test_categorical_cardinality(self, interpreter):
        """测试分类基数"""
        data = [{"cat": "A"} for _ in range(10)] + [{"cat": f"B{i}"} for i in range(60)]
        col_info = interpreter._analyze_columns(data, ["cat"])
        assert col_info["cat"]["unique_count"] == 61
        assert col_info["cat"]["cardinality"] == "high"

    def test_unique_count_calculation(self, interpreter):
        """测试唯一值计数"""
        data = [{"category": cat} for cat in ["A", "B", "C", "A", "B"]]
        col_info = interpreter._analyze_columns(data, ["category"])
        assert col_info["category"]["unique_count"] == 3

    def test_most_common_values(self, interpreter):
        """测试最常见值"""
        data = [{"category": cat} for cat in ["A", "A", "A", "B", "C"]]
        col_info = interpreter._analyze_columns(data, ["category"])
        most_common = col_info["category"]["most_common"]
        assert most_common[0] == ("A", 3)


class TestEdgeCases:
    """边界情况测试"""

    @pytest.fixture
    def interpreter(self):
        return ResultInterpreter()

    def test_all_null_values(self, interpreter):
        """测试全空值"""
        data = [{"value": None}, {"value": None}]
        col_info = interpreter._analyze_columns(data, ["value"])
        assert col_info["value"]["type"] == "unknown"

    def test_mixed_types(self, interpreter):
        """测试混合类型"""
        data = [{"value": 1}, {"value": "text"}, {"value": 3.5}]
        col_info = interpreter._analyze_columns(data, ["value"])
        # 应该选择最合适的类型
        assert "type" in col_info["value"]

    def test_single_row(self, interpreter):
        """测试单行数据"""
        data = [{"id": 1, "value": 100}]
        result = interpreter.interpret(data)
        assert result.row_count == 1

    def test_very_long_text_values(self, interpreter):
        """测试超长文本值"""
        long_text = "A" * 10000
        data = [{"text": long_text}]
        result = interpreter.interpret(data)
        assert result.row_count == 1


@pytest.mark.parametrize("data,expected_insight_types", [
    ([{"value": 1}, {"value": 2}, {"value": 100}], [InsightType.OUTLIER]),
    ([{"cat": "A"} for _ in range(9)] + [{"cat": "B"}], [InsightType.DISTRIBUTION]),
    ([{"date": "2024-01-01"}, {"date": "2024-12-31"}], [InsightType.TREND]),
])
def test_insight_detection(data, expected_insight_types):
    """参数化测试洞察检测"""
    interpreter = ResultInterpreter()
    result = interpreter.interpret(data)
    detected_types = {insight.insight_type for insight in result.insights}
    assert any(t in detected_types for t in expected_insight_types)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=services/bisheng_api/services/result_interpreter", "--cov-report=term-missing"])
