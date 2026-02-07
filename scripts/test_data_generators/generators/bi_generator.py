"""
BI报表生成器

生成：
- BI仪表板（3个仪表板）
- BI图表（12个图表）
"""

import random
from datetime import datetime, timedelta
from typing import Any, Dict, List

from ..base import BaseGenerator, BIChartTypes, generate_id, random_date, random_chinese_description
from ..config import GeneratorQuantities


# 仪表板名称模板
DASHBOARD_TEMPLATES = [
    "数据运营概览",
    "业务分析看板",
    "实时监控大屏",
]

# 图表名称模板
CHART_NAME_TEMPLATES = {
    BIChartTypes.LINE: [
        "日活用户趋势", "交易金额走势", "收入增长曲线",
        "用户留存趋势", "响应时间监控",
    ],
    BIChartTypes.BAR: [
        "渠道分布统计", "产品销量排行", "部门业绩对比",
        "用户来源分析", "地区销售分布",
    ],
    BIChartTypes.PIE: [
        "用户类型占比", "支付方式分布", "设备类型分布",
        "业务类型占比", "状态分布",
    ],
    BIChartTypes.TABLE: [
        "Top商品列表", "用户明细表", "订单详情表",
        "异常记录表", "数据汇总表",
    ],
    BIChartTypes.CARD: [
        "总用户数", "今日订单", "总收入", "转化率",
    ],
    BIChartTypes.GAUGE: [
        "目标完成率", "满意度评分", "健康度评分",
        "质量评分", "效率指标",
    ],
}


class BIGenerator(BaseGenerator):
    """
    BI报表生成器

    生成仪表板和图表
    """

    def __init__(self, config: GeneratorQuantities = None, storage_manager=None):
        super().__init__(config, storage_manager)
        self.quantities = config or GeneratorQuantities()

    def generate(self) -> Dict[str, List[Any]]:
        """
        生成所有BI数据

        Returns:
            包含dashboards, charts的字典
        """
        self.log("Generating BI dashboards and charts...", "info")

        # 生成仪表板
        dashboards = self._generate_dashboards()
        self.store_data("dashboards", dashboards)

        # 生成图表
        charts = self._generate_charts(dashboards)
        self.store_data("charts", charts)

        self.log(
            f"Generated {len(dashboards)} dashboards, {len(charts)} charts",
            "success"
        )

        return self.get_all_data()

    def _generate_dashboards(self) -> List[Dict[str, Any]]:
        """生成仪表板"""
        dashboards = []

        for i, name_template in enumerate(DASHBOARD_TEMPLATES):
            dashboard = {
                "dashboard_id": generate_id("dash_", 8),
                "name": name_template,
                "description": f"用于展示{name_template.replace('看板', '').replace('大屏', '')}相关指标",
                "category": random.choice(["运营分析", "业务分析", "技术监控", "财务分析"]),
                "owner": random.choice(["data-analyst-01", "data-analyst-02", "bi-team"]),
                "tags": random.sample(["实时", "日报", "核心", "监控", "预警"], k=random.randint(1, 3)),
                "layout": self._generate_layout(),
                "refresh_interval": random.choice([0, 300, 600, 1800, 3600]),
                "is_public": random.random() > 0.3,
                "status": random.choice(["published", "published", "draft", "archived"]),
                "view_count": random.randint(10, 1000),
                "created_by": random.choice(["data-analyst-01", "data-analyst-02"]),
                "created_at": random_date(90),
                "updated_at": random_date(30),
                "published_at": random_date(60) if random.random() > 0.3 else None,
            }
            dashboards.append(dashboard)

        return dashboards

    def _generate_layout(self) -> str:
        """生成布局配置JSON"""
        import json

        layout = {
            "rows": random.randint(2, 5),
            "columns": random.randint(2, 4),
            "grid": [[random.randint(1, 4) for _ in range(random.randint(2, 4))] for _ in range(random.randint(2, 5))]
        }

        return json.dumps(layout, ensure_ascii=False)

    def _generate_charts(self, dashboards: List[Dict]) -> List[Dict[str, Any]]:
        """生成图表"""
        charts = []

        for dashboard in dashboards:
            chart_count = self.quantities.charts_per_dashboard

            # 获取图表类型
            chart_types = self._get_chart_types_for_dashboard(dashboard)

            for i in range(chart_count):
                chart_type = chart_types[i % len(chart_types)]

                # 获取图表名称
                name_templates = CHART_NAME_TEMPLATES.get(
                    chart_type,
                    [f"{chart_type}_chart_{i+1}"]
                )
                chart_name = name_templates[i % len(name_templates)]

                # 获取数据源表
                tables = self._get_tables_for_bi()
                source_table = random.choice(tables) if tables else None

                chart = {
                    "chart_id": generate_id("chart_", 8),
                    "dashboard_id": dashboard["dashboard_id"],
                    "name": chart_name,
                    "chart_type": chart_type,
                    "description": f"展示{chart_name}相关数据",
                    # 数据配置
                    "source_type": random.choice(["mysql", "postgresql", "clickhouse", "api"]),
                    "source_query": self._generate_query_sql(chart_type, source_table),
                    "source_table": source_table["table_name"] if source_table else None,
                    "source_database": source_table["database_name"] if source_table else None,
                    # 显示配置
                    "position": self._generate_position(i),
                    "size": random.choice(["small", "medium", "medium", "large"]),
                    "config": self._generate_chart_config(chart_type),
                    # 轴配置（针对需要坐标轴的图表）
                    "x_axis": self._generate_axis_config("x"),
                    "y_axis": self._generate_axis_config("y"),
                    # 状态
                    "status": "active",
                    "created_by": dashboard["created_by"],
                    "created_at": random_date(60),
                    "updated_at": random_date(30),
                }
                charts.append(chart)

        return charts

    def _get_chart_types_for_dashboard(self, dashboard: Dict) -> List[str]:
        """根据仪表板确定图表类型"""
        name = dashboard["name"]

        if "趋势" in name or "实时" in name:
            return [BIChartTypes.LINE, BIChartTypes.CARD, BIChartTypes.GAUGE]
        elif "分布" in name or "分析" in name:
            return [BIChartTypes.BAR, BIChartTypes.PIE, BIChartTypes.TABLE]
        else:
            return [BIChartTypes.CARD, BIChartTypes.LINE, BIChartTypes.BAR, BIChartTypes.TABLE]

    def _get_tables_for_bi(self) -> List[Dict[str, Any]]:
        """获取用于BI的表"""
        tables = self.get_dependency("tables")
        if tables:
            return tables

        # 生成模拟表
        return [
            {"table_id": generate_id("tbl_", 8), "table_name": f"metric_table_{i}", "database_name": "bi_db"}
            for i in range(1, 11)
        ]

    def _generate_query_sql(self, chart_type: str, source_table: Dict = None) -> str:
        """生成查询SQL"""
        table = source_table["table_name"] if source_table else "metrics"

        if chart_type == BIChartTypes.LINE:
            return f"SELECT date, value FROM {table} ORDER BY date LIMIT 30"
        elif chart_type == BIChartTypes.BAR:
            return f"SELECT category, COUNT(*) as count FROM {table} GROUP BY category ORDER BY count DESC LIMIT 10"
        elif chart_type == BIChartTypes.PIE:
            return f"SELECT type, COUNT(*) as count FROM {table} GROUP BY type"
        elif chart_type == BIChartTypes.CARD:
            return f"SELECT COUNT(*) as total FROM {table}"
        else:
            return f"SELECT * FROM {table} LIMIT 100"

    def _generate_position(self, index: int) -> str:
        """生成图表位置"""
        row = index // 4
        col = index % 4
        return f"{row},{col}"

    def _generate_chart_config(self, chart_type: str) -> str:
        """生成图表配置JSON"""
        import json

        base_config = {
            "legend": {"show": True, "position": "bottom"},
            "tooltip": {"show": True},
        }

        if chart_type == BIChartTypes.LINE:
            base_config["smooth"] = True
            base_config["areaStyle"] = random.choice([True, False])
        elif chart_type == BIChartTypes.BAR:
            base_config["horizontal"] = random.choice([True, False])
        elif chart_type == BIChartTypes.PIE:
            base_config["radius"] = random.choice(["50%", "60%", "70%"])

        return json.dumps(base_config, ensure_ascii=False)

    def _generate_axis_config(self, axis: str) -> str:
        """生成坐标轴配置JSON"""
        import json

        config = {
            "show": True,
            "label": {"show": True},
        }

        if axis == "x":
            config["type"] = "category"
            config["name"] = "日期/类别"
        else:
            config["type"] = "value"
            config["name"] = "数值"

        return json.dumps(config, ensure_ascii=False)

    def save(self):
        """保存到数据库"""
        if not self.storage:
            self.log("No storage manager, skipping save", "warning")
            return

        self.log("Saving BI dashboards to database...", "info")

        # 保存仪表板
        dashboards = self.get_data("dashboards")
        if dashboards and self.storage.table_exists("bi_dashboards"):
            self.storage.batch_insert(
                "bi_dashboards",
                ["dashboard_id", "name", "description", "category", "owner", "tags",
                 "layout", "refresh_interval", "is_public", "status", "view_count",
                 "created_by", "created_at", "updated_at", "published_at"],
                dashboards,
                idempotent=True,
                idempotent_columns=["dashboard_id"]
            )
            self.log(f"Saved {len(dashboards)} dashboards", "success")

        # 保存图表
        charts = self.get_data("charts")
        if charts and self.storage.table_exists("bi_charts"):
            self.storage.batch_insert(
                "bi_charts",
                ["chart_id", "dashboard_id", "name", "chart_type", "description",
                 "source_type", "source_query", "source_table", "source_database",
                 "position", "size", "config", "x_axis", "y_axis", "status",
                 "created_by", "created_at", "updated_at"],
                charts,
                idempotent=True,
                idempotent_columns=["chart_id"]
            )
            self.log(f"Saved {len(charts)} charts", "success")

    def cleanup(self):
        """清理生成的数据"""
        if not self.storage:
            return

        self.log("Cleaning up BI data...", "info")

        if self.storage.table_exists("bi_charts"):
            self.storage.cleanup_by_prefix("bi_charts", "chart_id", "chart_")

        if self.storage.table_exists("bi_dashboards"):
            self.storage.cleanup_by_prefix("bi_dashboards", "dashboard_id", "dash_")


def generate_bi_data(config: GeneratorQuantities = None) -> Dict[str, List[Any]]:
    """
    便捷函数：生成BI数据

    Args:
        config: 生成配置

    Returns:
        BI数据字典
    """
    generator = BIGenerator(config)
    return generator.generate()
