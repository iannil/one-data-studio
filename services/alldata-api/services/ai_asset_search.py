"""
AI 资产检索服务
支持自然语言搜索、语义检索、智能推荐
"""

import logging
import re
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, text
from datetime import datetime, timedelta

from models.assets import DataAsset, AssetCategory
from models.metadata import MetadataDatabase, MetadataTable, MetadataColumn

logger = logging.getLogger(__name__)


class AIAssetSearchService:
    """AI 资产检索服务"""

    def __init__(self, embedding_service=None):
        """
        初始化服务

        Args:
            embedding_service: 向量化服务（可选，用于语义检索）
        """
        self.embedding_service = embedding_service
        self._query_cache = {}

    # ==================== 自然语言搜索 ====================

    def natural_search(
        self,
        db: Session,
        tenant_id: str,
        query: str,
        limit: int = 20,
        filters: Optional[Dict] = None
    ) -> Dict:
        """
        自然语言搜索资产

        支持自然语言查询，例如：
        - "用户订单相关的表"
        - "包含手机号的数据"
        - "最近更新的客户表"

        Args:
            db: 数据库会话
            tenant_id: 租户ID (未使用，保留用于未来扩展)
            query: 自然语言查询
            limit: 返回数量限制
            filters: 额外的过滤条件

        Returns:
            搜索结果，包含匹配的资产和解析的意图
        """
        # 解析查询意图
        intent = self._parse_query_intent(query)

        # 构建查询
        assets_query = db.query(DataAsset)
        # 过滤活跃状态的资产（如果状态字段存在）
        if hasattr(DataAsset, 'status'):
            assets_query = assets_query.filter(DataAsset.status == "active")

        # 应用意图解析的过滤条件
        if intent["asset_types"]:
            assets_query = assets_query.filter(
                DataAsset.asset_type.in_(intent["asset_types"])
            )

        if intent["keywords"]:
            keyword_filters = []
            for keyword in intent["keywords"]:
                keyword_filters.append(DataAsset.name.like(f"%{keyword}%"))
                keyword_filters.append(DataAsset.description.like(f"%{keyword}%"))
            assets_query = assets_query.filter(or_(*keyword_filters))

        if intent["data_level"]:
            assets_query = assets_query.filter(
                DataAsset.data_level == intent["data_level"]
            )

        if intent["database"]:
            assets_query = assets_query.filter(
                DataAsset.database_name == intent["database"]
            )

        # 应用额外的过滤条件
        if filters:
            if "asset_type" in filters:
                assets_query = assets_query.filter(
                    DataAsset.asset_type == filters["asset_type"]
                )
            if "category_id" in filters:
                assets_query = assets_query.filter(
                    DataAsset.category_id == filters["category_id"]
                )
            if "data_level" in filters:
                assets_query = assets_query.filter(
                    DataAsset.data_level == filters["data_level"]
                )

        # 应用时间过滤
        if intent["time_filter"] == "recent":
            recent_date = datetime.utcnow() - timedelta(days=30)
            assets_query = assets_query.filter(
                DataAsset.updated_at >= recent_date
            )

        # 执行查询
        assets = assets_query.limit(limit).all()

        # 计算相关性评分
        results = []
        for asset in assets:
            score = self._calculate_relevance(asset, intent, query)
            results.append({
                "asset": asset.to_dict(),
                "relevance_score": score,
                "matched_fields": self._get_matched_fields(asset, intent)
            })

        # 按相关性排序
        results.sort(key=lambda x: x["relevance_score"], reverse=True)

        return {
            "query": query,
            "intent": intent,
            "results": results[:limit],
            "total": len(results)
        }

    def _parse_query_intent(self, query: str) -> Dict:
        """
        解析自然语言查询意图

        提取：
        - 资产类型（表、视图、数据集等）
        - 关键词
        - 数据级别
        - 数据库名称
        - 时间过滤
        """
        query_lower = query.lower()
        intent = {
            "asset_types": [],
            "keywords": [],
            "data_level": None,
            "database": None,
            "time_filter": None,
            "sensitive": False,
            "original_query": query
        }

        # 提取资产类型
        type_keywords = {
            "table": ["表", "表格", "table"],
            "view": ["视图", "view"],
            "dataset": ["数据集", "dataset"],
            "file": ["文件", "file"],
            "api": ["接口", "api"]
        }

        for asset_type, keywords in type_keywords.items():
            if any(kw in query_lower for kw in keywords):
                intent["asset_types"].append(asset_type)

        # 提取数据级别
        if any(kw in query_lower for kw in ["公开", "public"]):
            intent["data_level"] = "public"
        elif any(kw in query_lower for kw in ["机密", "confidential"]):
            intent["data_level"] = "confidential"
        elif any(kw in query_lower for kw in ["绝密", "restricted"]):
            intent["data_level"] = "restricted"
        elif any(kw in query_lower for kw in ["内部", "internal"]):
            intent["data_level"] = "internal"

        # 提取敏感数据关键词
        if any(kw in query_lower for kw in ["敏感", "手机", "身份证", "银行卡", "隐私"]):
            intent["sensitive"] = True

        # 提取时间过滤
        if any(kw in query_lower for kw in ["最近", "近期", "新", "recent"]):
            intent["time_filter"] = "recent"

        # 提取数据库名称（常见数据库前缀）
        db_patterns = [
            r'(\w+)\s*库',
            r'(\w+)\s*数据库',
            r'from\s+(\w+)',
        ]
        for pattern in db_patterns:
            match = re.search(pattern, query_lower)
            if match:
                intent["database"] = match.group(1)
                break

        # 提取关键词（移除已解析的类型词）
        stop_words = set([
            "的", "了", "是", "在", "有", "和", "与", "或", "但", "而", "之",
            "表", "表格", "视图", "数据集", "文件", "接口",
            "公开", "内部", "机密", "绝密",
            "最近", "近期", "新",
            "搜索", "查找", "找", "查询", "显示", "列出"
        ])

        # 提取中文和英文关键词
        words = re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z0-9_]+', query_lower)
        intent["keywords"] = [w for w in words if w not in stop_words and len(w) > 1]

        return intent

    def _calculate_relevance(self, asset: DataAsset, intent: Dict, query: str) -> float:
        """计算资产与查询的相关性评分"""
        score = 0.0

        # 名称匹配（高权重）
        asset_name_lower = (asset.name or "").lower()
        query_lower = query.lower()

        if asset_name_lower == query_lower:
            score += 100
        elif asset_name_lower in query_lower or query_lower in asset_name_lower:
            score += 50

        # 关键词匹配
        for keyword in intent["keywords"]:
            if keyword in asset_name_lower:
                score += 20
            if asset.description and keyword in asset.description.lower():
                score += 10
            if asset.table_name and keyword in asset.table_name.lower():
                score += 15

        # 标签匹配
        if asset.tags:
            for tag in asset.tags:
                for keyword in intent["keywords"]:
                    if keyword.lower() in str(tag).lower():
                        score += 10

        # 敏感数据匹配
        if intent["sensitive"] and asset.data_level and asset.data_level in ["confidential", "restricted"]:
            score += 30

        # 使用频率加权
        if asset.usage_count:
            score += min(asset.usage_count / 100, 10)

        # 质量评分加权
        if asset.quality_score:
            score += asset.quality_score / 10

        return score

    def _get_matched_fields(self, asset: DataAsset, intent: Dict) -> List[str]:
        """获取匹配的字段列表"""
        matched = []

        for keyword in intent["keywords"]:
            if keyword in (asset.name or "").lower():
                matched.append("name")
            if asset.description and keyword in asset.description.lower():
                matched.append("description")
            if asset.table_name and keyword in asset.table_name.lower():
                matched.append("table_name")

        return list(set(matched))

    # ==================== 语义检索 ====================

    def semantic_search(
        self,
        db: Session,
        tenant_id: str,
        query: str,
        limit: int = 20,
        filters: Optional[Dict] = None
    ) -> Dict:
        """
        语义搜索（基于向量相似度）

        需要 embedding_service 支持
        """
        if not self.embedding_service:
            # 降级到关键词搜索
            return self.natural_search(db, tenant_id, query, limit, filters)

        try:
            # 获取查询向量
            query_embedding = self.embedding_service.encode(query)

            # 获取所有资产
            assets_query = db.query(DataAsset)
            if hasattr(DataAsset, 'status'):
                assets_query = assets_query.filter(DataAsset.status == "active")

            if filters:
                if "asset_type" in filters:
                    assets_query = assets_query.filter(
                        DataAsset.asset_type == filters["asset_type"]
                    )

            assets = assets_query.all()

            # 计算相似度
            results = []
            for asset in assets:
                # 生成资产文本表示
                asset_text = self._asset_to_text(asset)
                asset_embedding = self.embedding_service.encode(asset_text)

                # 计算余弦相似度
                similarity = self._cosine_similarity(query_embedding, asset_embedding)

                if similarity > 0.3:  # 相似度阈值
                    results.append({
                        "asset": asset.to_dict(),
                        "similarity_score": similarity
                    })

            # 按相似度排序
            results.sort(key=lambda x: x["similarity_score"], reverse=True)

            return {
                "query": query,
                "results": results[:limit],
                "total": len(results),
                "search_type": "semantic"
            }
        except Exception as e:
            logger.error(f"语义检索失败，降级到关键词搜索: {e}")
            return self.natural_search(db, tenant_id, query, limit, filters)

    def _asset_to_text(self, asset: DataAsset) -> str:
        """将资产转换为文本表示用于向量化"""
        parts = []

        parts.append(asset.name or "")

        if asset.description:
            parts.append(asset.description)

        if asset.table_name:
            parts.append(f"表名: {asset.table_name}")

        if asset.database_name:
            parts.append(f"数据库: {asset.database_name}")

        if asset.columns:
            column_names = [col.get("name", "") for col in (asset.columns or []) if isinstance(col, dict)]
            if column_names:
                parts.append(f"字段: {', '.join(column_names[:10])}")  # 限制字段数量

        if asset.tags:
            parts.append(f"标签: {', '.join(asset.tags)}")

        return " ".join(parts)

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """计算余弦相似度"""
        import math

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    # ==================== 智能推荐 ====================

    def recommend_assets(
        self,
        db: Session,
        tenant_id: str,
        asset_id: str,
        limit: int = 10
    ) -> Dict:
        """
        基于资产推荐相关资产

        推荐逻辑：
        1. 相同数据库/模式的资产
        2. 相同分类的资产
        3. 名称相似的资产
        4. 有相同标签的资产
        """
        # 获取源资产
        source_asset = db.query(DataAsset).filter(
            DataAsset.asset_id == asset_id
        ).first()

        if not source_asset:
            return {"error": "Asset not found", "results": []}

        recommendations = []
        seen_ids = {asset_id}

        # 1. 相同数据库的资产
        if source_asset.database_name:
            same_db_assets = db.query(DataAsset).filter(
                and_(
                    DataAsset.database_name == source_asset.database_name,
                    DataAsset.asset_id != asset_id
                )
            )
            if hasattr(DataAsset, 'status'):
                same_db_assets = same_db_assets.filter(DataAsset.status == "active")
            same_db_assets = same_db_assets.limit(limit * 2).all()

            for asset in same_db_assets:
                if asset.asset_id not in seen_ids:
                    recommendations.append({
                        "asset": asset.to_dict(),
                        "reason": "same_database",
                        "reason_text": f"同属于 {source_asset.database_name} 数据库",
                        "score": 0.8
                    })
                    seen_ids.add(asset.asset_id)

        # 2. 相同分类的资产
        if source_asset.category_id:
            same_category_assets = db.query(DataAsset).filter(
                and_(
                    DataAsset.category_id == source_asset.category_id,
                    DataAsset.asset_id != asset_id
                )
            )
            if hasattr(DataAsset, 'status'):
                same_category_assets = same_category_assets.filter(DataAsset.status == "active")
            same_category_assets = same_category_assets.limit(limit * 2).all()

            for asset in same_category_assets:
                if asset.asset_id not in seen_ids:
                    recommendations.append({
                        "asset": asset.to_dict(),
                        "reason": "same_category",
                        "reason_text": f"同属于 {source_asset.category_name} 分类",
                        "score": 0.7
                    })
                    seen_ids.add(asset.asset_id)

        # 3. 名称相似的资产
        all_assets = db.query(DataAsset).filter(
            DataAsset.asset_id != asset_id
        )
        if hasattr(DataAsset, 'status'):
            all_assets = all_assets.filter(DataAsset.status == "active")
        all_assets = all_assets.all()

        source_name_parts = set(source_asset.name.lower().split('_'))

        for asset in all_assets:
            if asset.asset_id in seen_ids:
                continue

            asset_name_parts = set(asset.name.lower().split('_'))
            similarity = len(source_name_parts & asset_name_parts) / max(len(source_name_parts), 1)

            if similarity > 0.3:
                recommendations.append({
                    "asset": asset.to_dict(),
                    "reason": "name_similarity",
                    "reason_text": "名称相似",
                    "score": similarity * 0.5
                })
                seen_ids.add(asset.asset_id)

        # 4. 有相同标签的资产
        if source_asset.tags:
            for asset in all_assets:
                if asset.asset_id in seen_ids or not asset.tags:
                    continue

                common_tags = set(source_asset.tags) & set(asset.tags)
                if len(common_tags) > 0:
                    recommendations.append({
                        "asset": asset.to_dict(),
                        "reason": "common_tags",
                        "reason_text": f"共同标签: {', '.join(common_tags)}",
                        "score": len(common_tags) * 0.2
                    })
                    seen_ids.add(asset.asset_id)

        # 排序并限制结果数量
        recommendations.sort(key=lambda x: x["score"], reverse=True)

        return {
            "source_asset_id": asset_id,
            "recommendations": recommendations[:limit],
            "total": len(recommendations)
        }

    # ==================== 热门资产 ====================

    def get_trending_assets(
        self,
        db: Session,
        tenant_id: str,
        days: int = 7,
        limit: int = 10
    ) -> Dict:
        """
        获取热门资产

        基于最近访问量、收藏量、使用量综合排序
        """
        # 由于模型中没有访问日志，这里使用现有的统计字段
        # 在实际应用中，应该有专门的访问日志表

        assets = db.query(DataAsset)
        if hasattr(DataAsset, 'status'):
            assets = assets.filter(DataAsset.status == "active")

        # 构建排序
        if all(hasattr(DataAsset, field) for field in ['view_count', 'usage_count', 'collect_count']):
            assets = assets.order_by(
                (DataAsset.view_count * 1 + DataAsset.usage_count * 2 +
                 DataAsset.collect_count * 3).desc()
            )
        else:
            assets = assets.order_by(DataAsset.id.desc())

        assets = assets.limit(limit).all()

        return {
            "period_days": days,
            "assets": [asset.to_dict() for asset in assets],
            "total": len(assets)
        }

    # ==================== 智能补全 ====================

    def autocomplete(
        self,
        db: Session,
        tenant_id: str,
        prefix: str,
        limit: int = 10
    ) -> Dict:
        """
        搜索补全建议

        输入前缀，返回可能的补全项
        """
        suggestions = []

        # 资产名称补全
        name_matches = db.query(DataAsset).filter(
            DataAsset.name.like(f"{prefix}%")
        )
        if hasattr(DataAsset, 'status'):
            name_matches = name_matches.filter(DataAsset.status == "active")
        name_matches = name_matches.limit(limit).all()

        for asset in name_matches:
            suggestions.append({
                "type": "asset",
                "text": asset.name,
                "asset_id": asset.asset_id,
                "asset_type": asset.asset_type
            })

        # 表名补全
        table_matches = db.query(MetadataTable).filter(
            MetadataTable.table_name.like(f"{prefix}%")
        ).limit(limit).all()

        for table in table_matches:
            suggestions.append({
                "type": "table",
                "text": table.table_name,
                "database": table.database_name,
                "full_name": f"{table.database_name}.{table.table_name}"
            })

        # 列名补全
        column_matches = db.query(MetadataColumn).filter(
            MetadataColumn.column_name.like(f"{prefix}%")
        ).limit(limit).all()

        for col in column_matches:
            suggestions.append({
                "type": "column",
                "text": col.column_name,
                "table": col.table_name,
                "full_name": f"{col.database_name}.{col.table_name}.{col.column_name}"
            })

        return {
            "prefix": prefix,
            "suggestions": suggestions[:limit],
            "total": len(suggestions)
        }


# 创建全局服务实例
_ai_asset_search_service = None


def get_ai_asset_search_service(embedding_service=None) -> AIAssetSearchService:
    """获取 AI 资产搜索服务实例"""
    global _ai_asset_search_service
    if _ai_asset_search_service is None:
        _ai_asset_search_service = AIAssetSearchService(embedding_service)
    return _ai_asset_search_service
