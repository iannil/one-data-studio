"""
资产自动编目服务
Phase 2: 数据资产管理增强

功能：
- ETL/Kettle 输出表自动注册为数据资产
- 元数据变更自动同步资产目录
- 基于元数据自动推断资产分类和标签
- 资产血缘自动追踪（源表 → ETL → 目标表）
- 与 KettleBridge 回调集成，ETL 完成后自动编目
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class AssetAutoCatalogService:
    """
    数据资产自动编目服务

    在 ETL 任务完成后，自动将输出表注册到数据资产目录，
    并关联元数据、血缘关系和质量信息。
    """

    def __init__(self):
        self._catalog_history: List[Dict[str, Any]] = []

    def auto_catalog_from_etl(
        self,
        source_database: str,
        source_table: str,
        target_database: str,
        target_table: str,
        etl_task_id: str = "",
        created_by: str = "system",
        db_session=None,
    ) -> Dict[str, Any]:
        """
        ETL 完成后自动注册目标表为数据资产

        Args:
            source_database: 源数据库
            source_table: 源表
            target_database: 目标数据库
            target_table: 目标表
            etl_task_id: ETL 任务 ID
            created_by: 创建者
            db_session: 数据库会话

        Returns:
            编目结果
        """
        result = {
            "success": False,
            "asset_id": None,
            "action": None,  # created, updated, skipped
            "message": "",
        }

        if db_session is None:
            result["message"] = "无数据库会话"
            return result

        try:
            from models.assets import DataAsset

            # 检查是否已存在
            existing = db_session.query(DataAsset).filter(
                DataAsset.database_name == target_database,
                DataAsset.table_name == target_table,
            ).first()

            if existing:
                # 更新现有资产
                existing.updated_at = datetime.utcnow()
                existing.last_sync_at = datetime.utcnow()

                # 更新列信息
                columns = self._fetch_column_info(target_database, target_table, db_session)
                if columns:
                    existing.columns = columns

                # 更新行数
                row_count = self._get_table_row_count(target_database, target_table, db_session)
                if row_count is not None:
                    existing.row_count = row_count

                db_session.commit()
                result["success"] = True
                result["asset_id"] = existing.asset_id
                result["action"] = "updated"
                result["message"] = f"更新已有资产 {existing.asset_id}"
            else:
                # 创建新资产
                asset_id = f"asset_{uuid.uuid4().hex[:12]}"

                # 获取列信息
                columns = self._fetch_column_info(target_database, target_table, db_session)

                # 推断分类和标签
                category = self._infer_category(target_table, columns)
                tags = self._infer_tags(source_table, target_table, etl_task_id)

                # 推断数据等级
                data_level = self._infer_data_level(columns, db_session)

                asset = DataAsset(
                    asset_id=asset_id,
                    name=f"{target_database}.{target_table}",
                    description=f"由 ETL 任务自动编目（源: {source_database}.{source_table}）",
                    asset_type="table",
                    category_name=category,
                    source_type="database",
                    source_name=f"ETL-{etl_task_id}" if etl_task_id else "ETL-AUTO",
                    path=f"{target_database}/{target_table}",
                    database_name=target_database,
                    table_name=target_table,
                    columns=columns,
                    tags=tags,
                    owner=created_by,
                    data_level=data_level,
                    status="active",
                    last_sync_at=datetime.utcnow(),
                )

                db_session.add(asset)
                db_session.commit()

                result["success"] = True
                result["asset_id"] = asset_id
                result["action"] = "created"
                result["message"] = f"创建新资产 {asset_id}"

            # 记录编目历史
            self._catalog_history.append({
                "timestamp": datetime.utcnow().isoformat(),
                "source": f"{source_database}.{source_table}",
                "target": f"{target_database}.{target_table}",
                "asset_id": result["asset_id"],
                "action": result["action"],
                "etl_task_id": etl_task_id,
            })

            logger.info(
                f"自动编目: {result['action']} 资产 {result['asset_id']} "
                f"({target_database}.{target_table})"
            )

        except Exception as e:
            logger.error(f"自动编目失败: {e}", exc_info=True)
            result["message"] = str(e)
            try:
                db_session.rollback()
            except Exception:
                pass

        return result

    def batch_catalog_from_metadata(
        self,
        database_name: str = None,
        created_by: str = "system",
        db_session=None,
    ) -> Dict[str, Any]:
        """
        批量从元数据注册资产（全量同步）

        Args:
            database_name: 指定数据库（空表示全部）
            created_by: 创建者
            db_session: 数据库会话

        Returns:
            批量编目结果
        """
        summary = {
            "total_tables": 0,
            "created": 0,
            "updated": 0,
            "skipped": 0,
            "errors": 0,
        }

        if db_session is None:
            return summary

        try:
            from models.metadata import MetadataDatabase, MetadataTable
            from models.assets import DataAsset

            query = db_session.query(MetadataDatabase)
            if database_name:
                query = query.filter(MetadataDatabase.database_name == database_name)

            databases = query.all()

            for db in databases:
                db_name = db.database_name
                # 跳过系统数据库
                if db_name in ("information_schema", "mysql", "performance_schema", "sys"):
                    continue

                tables = db_session.query(MetadataTable).filter_by(
                    database_id=db.id
                ).all()

                for table in tables:
                    summary["total_tables"] += 1

                    result = self.auto_catalog_from_etl(
                        source_database=db_name,
                        source_table=table.table_name,
                        target_database=db_name,
                        target_table=table.table_name,
                        created_by=created_by,
                        db_session=db_session,
                    )

                    if result["success"]:
                        if result["action"] == "created":
                            summary["created"] += 1
                        elif result["action"] == "updated":
                            summary["updated"] += 1
                        else:
                            summary["skipped"] += 1
                    else:
                        summary["errors"] += 1

        except Exception as e:
            logger.error(f"批量编目失败: {e}", exc_info=True)

        return summary

    def get_catalog_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取编目历史"""
        return self._catalog_history[-limit:]

    # ===== 内部方法 =====

    def _fetch_column_info(
        self,
        database: str,
        table: str,
        db_session,
    ) -> List[Dict[str, Any]]:
        """获取表的列信息"""
        try:
            from models.metadata import MetadataDatabase, MetadataTable, MetadataColumn

            db = db_session.query(MetadataDatabase).filter(
                MetadataDatabase.database_name == database
            ).first()
            if not db:
                return []

            tbl = db_session.query(MetadataTable).filter(
                MetadataTable.database_id == db.id,
                MetadataTable.table_name == table,
            ).first()
            if not tbl:
                return []

            cols = db_session.query(MetadataColumn).filter(
                MetadataColumn.table_id == tbl.id
            ).all()

            return [
                {
                    "name": col.column_name,
                    "type": col.column_type,
                    "sensitivity_type": getattr(col, "sensitivity_type", None),
                    "sensitivity_level": getattr(col, "sensitivity_level", None),
                }
                for col in cols
            ]

        except Exception as e:
            logger.debug(f"获取列信息失败: {e}")
            return []

    def _get_table_row_count(
        self,
        database: str,
        table: str,
        db_session,
    ) -> Optional[int]:
        """获取表行数"""
        try:
            from sqlalchemy import text
            result = db_session.execute(
                text(f"SELECT COUNT(*) FROM `{database}`.`{table}`")
            )
            return result.scalar()
        except Exception:
            return None

    def _infer_category(
        self,
        table_name: str,
        columns: List[Dict[str, Any]],
    ) -> str:
        """根据表名和列信息推断资产分类"""
        name_lower = table_name.lower()

        category_keywords = {
            "用户数据": ["user", "member", "customer", "account", "用户", "会员"],
            "交易数据": ["order", "trade", "transaction", "payment", "订单", "交易", "支付"],
            "产品数据": ["product", "item", "goods", "sku", "产品", "商品"],
            "日志数据": ["log", "event", "track", "audit", "日志", "事件"],
            "配置数据": ["config", "setting", "dict", "param", "配置", "字典"],
            "统计数据": ["stat", "report", "summary", "agg", "统计", "报表"],
        }

        for category, keywords in category_keywords.items():
            for kw in keywords:
                if kw in name_lower:
                    return category

        return "其他"

    def _infer_tags(
        self,
        source_table: str,
        target_table: str,
        etl_task_id: str,
    ) -> List[str]:
        """推断资产标签"""
        tags = ["自动编目"]

        if etl_task_id:
            tags.append("ETL输出")

        if source_table != target_table:
            tags.append("衍生表")

        name_lower = target_table.lower()
        if "dim_" in name_lower or "维度" in name_lower:
            tags.append("维度表")
        elif "fact_" in name_lower or "事实" in name_lower:
            tags.append("事实表")
        elif "dwd_" in name_lower:
            tags.append("明细层")
        elif "dws_" in name_lower:
            tags.append("汇总层")
        elif "ads_" in name_lower:
            tags.append("应用层")
        elif "ods_" in name_lower:
            tags.append("原始层")

        return tags

    def _infer_data_level(
        self,
        columns: List[Dict[str, Any]],
        db_session,
    ) -> str:
        """根据列敏感度推断数据等级"""
        level_priority = {
            "restricted": 4,
            "confidential": 3,
            "internal": 2,
            "public": 1,
        }

        max_level = "public"
        max_priority = 0

        for col in columns:
            sensitivity_level = col.get("sensitivity_level")
            if sensitivity_level and sensitivity_level in level_priority:
                if level_priority[sensitivity_level] > max_priority:
                    max_priority = level_priority[sensitivity_level]
                    max_level = sensitivity_level

        return max_level


# 全局实例
_auto_catalog_service: Optional[AssetAutoCatalogService] = None


def get_asset_auto_catalog_service() -> AssetAutoCatalogService:
    """获取资产自动编目服务单例"""
    global _auto_catalog_service
    if _auto_catalog_service is None:
        _auto_catalog_service = AssetAutoCatalogService()
    return _auto_catalog_service
