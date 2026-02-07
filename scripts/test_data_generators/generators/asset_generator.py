"""
数据资产生成器

生成：
- 数据资产（140个资产）
- 资产分类（10个分类）
- 资产价值历史（280条历史记录）
"""

import random
from datetime import datetime, timedelta
from typing import Any, Dict, List, Tuple

from ..base import (
    BaseGenerator, AssetTypes, AssetCategories,
    generate_id, random_date, random_chinese_description
)
from ..config import GeneratorQuantities


# 资产名称模板
ASSET_NAME_TEMPLATES = {
    AssetCategories.USER_DATA: [
        "用户基础信息表", "用户扩展信息表", "会员信息表", "用户画像表",
        "用户标签表", "用户等级表", "用户积分表", "用户关系表",
    ],
    AssetCategories.TRANSACTION_DATA: [
        "订单主表", "订单明细表", "支付记录表", "退款记录表",
        "交易流水表", "结算记录表", "对账记录表",
    ],
    AssetCategories.PRODUCT_DATA: [
        "商品信息表", "商品分类表", "商品属性表", "库存表",
        "价格表", "SKU表", "商品标签表",
    ],
    AssetCategories.LOG_DATA: [
        "应用日志表", "访问日志表", "错误日志表", "操作日志表",
        "审计日志表", "系统日志表", "安全日志表",
    ],
    AssetCategories.BEHAVIOR_DATA: [
        "用户行为事件表", "页面访问表", "点击事件表", "浏览记录表",
        "搜索记录表", "用户会话表",
    ],
    AssetCategories.FINANCE_DATA: [
        "财务科目表", "财务凭证表", "财务报表表", "预算表",
        "费用表", "收入表", "资产负债表",
    ],
    AssetCategories.OPERATION_DATA: [
        "营销活动表", "优惠券表", "推广记录表", "渠道数据表",
        "广告投放表", "效果统计表",
    ],
    AssetCategories.RISK_DATA: [
        "风控规则表", "风控事件表", "黑名单表", "灰名单表",
        "风险评估表", "反欺诈记录表",
    ],
    AssetCategories.PUBLIC_DATA: [
        "地区信息表", "行业分类表", "公共配置表", "字典表",
        "枚举值表", "系统参数表",
    ],
    AssetCategories.CONFIG_DATA: [
        "系统配置表", "功能开关表", "权限配置表", "菜单配置表",
        "接口配置表", "定时任务配置表",
    ],
}


class AssetGenerator(BaseGenerator):
    """
    数据资产生成器

    生成数据资产、分类和价值历史
    """

    def __init__(self, config: GeneratorQuantities = None, storage_manager=None):
        super().__init__(config, storage_manager)
        self.quantities = config or GeneratorQuantities()

    def generate(self) -> Dict[str, List[Any]]:
        """
        生成所有数据资产

        Returns:
            包含assets, categories, value_history的字典
        """
        self.log("Generating data assets...", "info")

        # 生成资产分类
        categories = self._generate_categories()
        self.store_data("categories", categories)

        # 生成数据资产
        assets = self._generate_assets(categories)
        self.store_data("assets", assets)

        # 生成资产价值历史
        value_history = self._generate_value_history(assets)
        self.store_data("value_history", value_history)

        self.log(
            f"Generated {len(assets)} assets, {len(categories)} categories, "
            f"{len(value_history)} value history records",
            "success"
        )

        return self.get_all_data()

    def _generate_categories(self) -> List[Dict[str, Any]]:
        """生成资产分类"""
        categories = []

        for i, category in enumerate(AssetCategories.ALL):
            cat = {
                "category_id": generate_id("cat_", 8),
                "category_name": category,
                "category_code": f"cat_{i+1:02d}",
                "description": f"{category}相关资产分类",
                "parent_id": None,
                "sort_order": i,
                "icon": random.choice([
                    "database", "table", "chart", "document",
                    "user", "settings", "lock", "shield"
                ]),
                "color": random.choice([
                    "#1890ff", "#52c41a", "#faad14", "#f5222d",
                    "#722ed1", "#13c2c2", "#eb2f96", "#fa8c16"
                ]),
                "created_at": random_date(90),
            }
            categories.append(cat)

        return categories

    def _generate_assets(self, categories: List[Dict]) -> List[Dict[str, Any]]:
        """生成数据资产"""
        assets = []

        # 获取表数据（从依赖或生成）
        tables = self._get_tables_for_assets()

        # 为每个分类生成资产
        for category in categories:
            category_name = category["category_name"]
            asset_count = self.quantities.asset_count // len(categories)

            name_templates = ASSET_NAME_TEMPLATES.get(
                category_name,
                [f"{category_name}资产_{i}" for i in range(1, asset_count + 1)]
            )

            for i in range(asset_count):
                # 尝试关联表
                if tables and i < len(tables):
                    table = tables[i % len(tables)]
                    table_id = table.get("table_id", "")
                    table_name = table.get("table_name", f"table_{i}")
                    database_name = table.get("database_name", "db_default")
                else:
                    table_id = generate_id("tbl_", 8)
                    table_name = f"table_{i}"
                    database_name = "db_default"

                # 生成资产信息
                asset_type = random.choice(AssetTypes.ALL)
                source_type = random.choice(["mysql", "postgresql", "hive", "mongodb"])

                # 计算价值评分
                usage_score = random.randint(20, 100)
                business_score = random.randint(30, 100)
                quality_score = random.randint(40, 100)
                governance_score = random.randint(50, 100)

                # 计算总分（加权平均）
                total_score = int(
                    usage_score * 0.3 +
                    business_score * 0.3 +
                    quality_score * 0.25 +
                    governance_score * 0.15
                )

                # 计算等级
                if total_score >= 90:
                    grade = "S"
                elif total_score >= 80:
                    grade = "A"
                elif total_score >= 60:
                    grade = "B"
                else:
                    grade = "C"

                # 选择所有者
                owner = random.choice([
                    "data-team", "bi-team", "product-team",
                    "operation-team", "admin"
                ])

                asset = {
                    "asset_id": generate_id("asset_", 8),
                    "asset_name": name_templates[i % len(name_templates)],
                    "asset_code": f"ASSET_{category['category_code'].upper()}_{i+1:04d}",
                    "asset_type": asset_type,
                    "category_id": category["category_id"],
                    "category_name": category_name,
                    "description": random_chinese_description(5, 15),
                    # 来源信息
                    "source_type": source_type,
                    "source_id": generate_id("ds_", 8),
                    "database_name": database_name,
                    "table_name": table_name,
                    "table_id": table_id,
                    # 统计信息
                    "row_count": random.randint(1000, 10000000),
                    "size_mb": random.randint(1, 10000),
                    "last_update_time": random_date(7),
                    # 价值评分
                    "usage_score": usage_score,
                    "business_score": business_score,
                    "quality_score": quality_score,
                    "governance_score": governance_score,
                    "total_score": total_score,
                    "grade": grade,
                    # 所有者信息
                    "owner": owner,
                    "department": f"{owner.split('-')[0].title()} Department",
                    "tags": random.sample([
                        "核心数据", "高频使用", "质量优良", "敏感数据",
                        "生产数据", "数仓数据", "临时数据", "归档数据"
                    ], k=random.randint(0, 3)),
                    # 状态
                    "status": random.choice(["active", "active", "active", "deprecated", "draft"]),
                    # 时间
                    "created_at": random_date(90),
                    "updated_at": random_date(30),
                    "certified_at": random_date(60) if grade in ["S", "A"] else None,
                }
                assets.append(asset)

        return assets

    def _get_tables_for_assets(self) -> List[Dict[str, Any]]:
        """获取用于资产的表"""
        tables = self.get_dependency("tables")
        if tables:
            return tables[:self.quantities.asset_count]

        # 生成模拟表
        return [
            {
                "table_id": generate_id("tbl_", 8),
                "table_name": f"table_{i}",
                "database_name": f"db_{(i // 10) + 1}"
            }
            for i in range(1, self.quantities.asset_count + 1)
        ]

    def _generate_value_history(self, assets: List[Dict]) -> List[Dict[str, Any]]:
        """生成资产价值历史"""
        history = []

        # 为每个资产生成历史记录
        for asset in assets:
            # 生成2条历史记录
            for i in range(self.quantities.value_history_per_asset):
                # 历史分数略微变化
                change = random.randint(-10, 10)
                history_score = max(0, min(100, asset["total_score"] + change))

                # 计算历史等级
                if history_score >= 90:
                    history_grade = "S"
                elif history_score >= 80:
                    history_grade = "A"
                elif history_score >= 60:
                    history_grade = "B"
                else:
                    history_grade = "C"

                # 时间（按顺序）
                if i == 0:
                    recorded_at = random_date(60)
                else:
                    recorded_at = random_date(30)

                record = {
                    "history_id": generate_id("hist_", 8),
                    "asset_id": asset["asset_id"],
                    "score": history_score,
                    "grade": history_grade,
                    "usage_score": max(0, min(100, asset["usage_score"] + change)),
                    "business_score": max(0, min(100, asset["business_score"] + change)),
                    "quality_score": max(0, min(100, asset["quality_score"] + change)),
                    "governance_score": max(0, min(100, asset["governance_score"] + change)),
                    "change_reason": random.choice([
                        "定期评估", "质量提升", "使用频率变化", "数据治理改进",
                        "标准更新", "规则调整"
                    ]),
                    "recorded_by": random.choice(["system", "data-admin-01"]),
                    "recorded_at": recorded_at,
                }
                history.append(record)

        return history

    def get_assets_by_grade(self, grade: str) -> List[Dict[str, Any]]:
        """按等级获取资产"""
        assets = self.get_data("assets")
        return [a for a in assets if a.get("grade") == grade]

    def get_assets_by_category(self, category: str) -> List[Dict[str, Any]]:
        """按分类获取资产"""
        assets = self.get_data("assets")
        return [a for a in assets if a.get("category_name") == category]

    def get_grade_summary(self) -> Dict[str, int]:
        """获取等级统计"""
        assets = self.get_data("assets")
        summary = {"S": 0, "A": 0, "B": 0, "C": 0}
        for asset in assets:
            grade = asset.get("grade", "C")
            summary[grade] = summary.get(grade, 0) + 1
        return summary

    def save(self):
        """保存到数据库"""
        if not self.storage:
            self.log("No storage manager, skipping save", "warning")
            return

        self.log("Saving assets to database...", "info")

        # 保存分类
        categories = self.get_data("categories")
        if categories and self.storage.table_exists("asset_categories"):
            self.storage.batch_insert(
                "asset_categories",
                ["category_id", "category_name", "category_code", "description",
                 "parent_id", "sort_order", "icon", "color", "created_at"],
                categories,
                idempotent=True,
                idempotent_columns=["category_code"]
            )
            self.log(f"Saved {len(categories)} categories", "success")

        # 保存资产
        assets = self.get_data("assets")
        if assets and self.storage.table_exists("data_assets"):
            self.storage.batch_insert(
                "data_assets",
                ["asset_id", "asset_name", "asset_code", "asset_type", "category_id",
                 "category_name", "description", "source_type", "source_id", "database_name",
                 "table_name", "table_id", "row_count", "size_mb", "last_update_time",
                 "usage_score", "business_score", "quality_score", "governance_score",
                 "total_score", "grade", "owner", "department", "tags", "status",
                 "created_at", "updated_at", "certified_at"],
                assets,
                idempotent=True,
                idempotent_columns=["asset_id"]
            )
            self.log(f"Saved {len(assets)} assets", "success")

        # 保存价值历史
        value_history = self.get_data("value_history")
        if value_history and self.storage.table_exists("asset_value_history"):
            self.storage.batch_insert(
                "asset_value_history",
                ["history_id", "asset_id", "score", "grade", "usage_score",
                 "business_score", "quality_score", "governance_score",
                 "change_reason", "recorded_by", "recorded_at"],
                value_history,
                idempotent=True,
                idempotent_columns=["history_id"]
            )
            self.log(f"Saved {len(value_history)} value history records", "success")

    def cleanup(self):
        """清理生成的数据"""
        if not self.storage:
            return

        self.log("Cleaning up asset data...", "info")

        for table, id_col in [
            ("asset_value_history", "history_id"),
            ("data_assets", "asset_id"),
            ("asset_categories", "category_id"),
        ]:
            if self.storage.table_exists(table):
                for prefix in ["hist_", "asset_", "cat_"]:
                    self.storage.cleanup_by_prefix(table, id_col, prefix)


def generate_asset_data(config: GeneratorQuantities = None) -> Dict[str, List[Any]]:
    """
    便捷函数：生成资产数据

    Args:
        config: 生成配置

    Returns:
        资产数据字典
    """
    generator = AssetGenerator(config)
    return generator.generate()
