"""
多表智能融合服务
Phase 2.0: 跨表关联键自动检测、JOIN质量评分、融合规则推荐

增强功能：
- Embedding 语义匹配
- 增强的模糊匹配（Levenshtein + Jaccard + Cosine）
- 置信度阈值自适应校准
"""

import logging
import re
import math
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)


class JoinType(str, Enum):
    """JOIN类型"""
    INNER = "inner"
    LEFT = "left"
    RIGHT = "right"
    FULL = "full"
    CROSS = "cross"


@dataclass
class JoinKeyPair:
    """JOIN关键字对"""
    source_column: str
    target_column: str
    source_table: str
    target_table: str
    confidence: float
    detection_method: str  # name_match, semantic, value_analysis
    name_similarity: float = 0.0
    value_overlap_rate: float = 0.0
    cardinality_match: bool = True
    is_primary_key: bool = False
    is_foreign_key: bool = False

    def to_dict(self) -> Dict:
        return {
            "source_column": self.source_column,
            "target_column": self.target_column,
            "source_table": self.source_table,
            "target_table": self.target_table,
            "confidence": self.confidence,
            "detection_method": self.detection_method,
            "name_similarity": self.name_similarity,
            "value_overlap_rate": self.value_overlap_rate,
            "cardinality_match": self.cardinality_match,
            "is_primary_key": self.is_primary_key,
            "is_foreign_key": self.is_foreign_key,
        }


@dataclass
class JoinQualityScore:
    """JOIN质量评分"""
    overall_score: float
    match_rate: float          # 匹配率：能关联上的记录比例
    coverage_rate: float       # 覆盖率：目标表记录被关联的比例
    skew_factor: float         # 倾斜度：关联结果分布均匀程度
    orphan_rate: float         # 孤立率：无法关联的记录比例
    null_key_rate: float       # 空键率：关联键为空的比例
    duplicate_rate: float      # 重复率：关联键重复的比例
    recommendation: str        # 推荐的JOIN类型
    issues: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "overall_score": self.overall_score,
            "match_rate": self.match_rate,
            "coverage_rate": self.coverage_rate,
            "skew_factor": self.skew_factor,
            "orphan_rate": self.orphan_rate,
            "null_key_rate": self.null_key_rate,
            "duplicate_rate": self.duplicate_rate,
            "recommendation": self.recommendation,
            "issues": self.issues,
        }


@dataclass
class JoinStrategyRecommendation:
    """JOIN策略推荐"""
    join_type: JoinType
    join_keys: List[JoinKeyPair]
    estimated_result_count: int
    quality_score: JoinQualityScore
    sql_template: str
    index_suggestions: List[Dict]
    performance_notes: List[str]
    warnings: List[str]

    def to_dict(self) -> Dict:
        return {
            "join_type": self.join_type.value,
            "join_keys": [k.to_dict() for k in self.join_keys],
            "estimated_result_count": self.estimated_result_count,
            "quality_score": self.quality_score.to_dict(),
            "sql_template": self.sql_template,
            "index_suggestions": self.index_suggestions,
            "performance_notes": self.performance_notes,
            "warnings": self.warnings,
        }


class TableFusionService:
    """多表智能融合服务"""

    # 常见ID字段模式
    ID_PATTERNS = [
        r'^id$',
        r'.*_id$',
        r'^.*id$',
        r'.*_code$',
        r'.*_key$',
        r'.*_no$',
        r'.*_number$',
    ]

    # 语义等价字段映射
    SEMANTIC_EQUIVALENTS = {
        "user_id": ["uid", "userid", "user", "customer_id", "cust_id", "member_id"],
        "customer_id": ["cust_id", "cid", "customer", "client_id"],
        "order_id": ["oid", "orderid", "order_no", "order_number", "order_code"],
        "product_id": ["pid", "productid", "sku_id", "sku", "item_id", "goods_id"],
        "account_id": ["aid", "accountid", "account", "acct_id"],
        "org_id": ["organization_id", "org_code", "company_id", "enterprise_id"],
        "dept_id": ["department_id", "dept_code", "division_id"],
        "employee_id": ["emp_id", "staff_id", "worker_id", "personnel_id"],
        "category_id": ["cat_id", "categoryid", "category_code", "class_id"],
        "region_id": ["area_id", "zone_id", "district_id", "location_id"],
        "merchant_id": ["shop_id", "store_id", "seller_id", "vendor_id"],
        "transaction_id": ["txn_id", "trans_id", "payment_id", "bill_id"],
    }

    def __init__(self):
        self._name_similarity_threshold = 0.7
        self._value_overlap_threshold = 0.3
        self._embedding_cache: Dict[str, List[float]] = {}
        self._embedding_service = None

    def _get_embedding_service(self):
        """获取 Embedding 服务"""
        if self._embedding_service is None:
            try:
                from services.embedding_service import get_embedding_service
                self._embedding_service = get_embedding_service()
            except ImportError:
                logger.warning("Embedding 服务不可用，将使用基础语义匹配")
        return self._embedding_service

    async def _get_embedding(self, text: str) -> Optional[List[float]]:
        """获取文本的 Embedding 向量"""
        # 检查缓存
        if text in self._embedding_cache:
            return self._embedding_cache[text]

        service = self._get_embedding_service()
        if service is None:
            return None

        try:
            embedding = await service.embed_text(text)
            if embedding and len(embedding) > 0:
                self._embedding_cache[text] = embedding
                return embedding
        except Exception as e:
            logger.warning(f"获取 Embedding 失败: {e}")

        return None

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """计算余弦相似度"""
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(b * b for b in vec2))

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)

    def _jaccard_similarity(self, s1: str, s2: str) -> float:
        """计算 Jaccard 相似度（基于字符 n-gram）"""
        def ngrams(s: str, n: int = 2) -> Set[str]:
            return {s[i:i+n] for i in range(len(s) - n + 1)} if len(s) >= n else set(s)

        n1, n2 = ngrams(s1.lower()), ngrams(s2.lower())
        if not n1 and not n2:
            return 1.0
        if not n1 or not n2:
            return 0.0

        intersection = len(n1 & n2)
        union = len(n1 | n2)
        return intersection / union if union > 0 else 0.0

    def _enhanced_name_similarity(self, name1: str, name2: str) -> float:
        """
        增强的名称相似度计算

        结合多种相似度算法：
        - Levenshtein 距离
        - Jaccard 相似度
        - 包含关系
        - 前缀/后缀匹配
        """
        n1, n2 = name1.lower(), name2.lower()

        # 完全相同
        if n1 == n2:
            return 1.0

        scores = []

        # 1. Levenshtein 相似度
        lev_dist = self._levenshtein_distance(n1, n2)
        max_len = max(len(n1), len(n2))
        lev_sim = 1 - (lev_dist / max_len) if max_len > 0 else 0
        scores.append(lev_sim * 0.4)  # 权重 40%

        # 2. Jaccard 相似度
        jaccard_sim = self._jaccard_similarity(n1, n2)
        scores.append(jaccard_sim * 0.2)  # 权重 20%

        # 3. 包含关系
        if n1 in n2 or n2 in n1:
            scores.append(0.25)  # 权重 25%

        # 4. 前缀/后缀匹配
        # 移除常见前缀后比较
        prefixes = ["user_", "cust_", "order_", "product_", "acct_"]
        stripped1, stripped2 = n1, n2
        for prefix in prefixes:
            if stripped1.startswith(prefix):
                stripped1 = stripped1[len(prefix):]
            if stripped2.startswith(prefix):
                stripped2 = stripped2[len(prefix):]
        if stripped1 == stripped2 and stripped1 != n1:
            scores.append(0.15)  # 权重 15%

        return min(sum(scores), 1.0)

    async def _find_embedding_semantic_matches(
        self,
        source_columns: List[Dict],
        target_columns: List[Dict],
        source_table: str,
        target_table: str,
        exclude: Set[str] = None,
        threshold: float = 0.8
    ) -> List[JoinKeyPair]:
        """
        基于 Embedding 的语义匹配

        使用向量 Embedding 计算字段名的语义相似度
        """
        matches = []
        exclude = exclude or set()

        service = self._get_embedding_service()
        if service is None:
            return []

        # 获取源列的 Embeddings
        source_embeddings = {}
        for col in source_columns:
            if col["name"] in exclude:
                continue
            embedding = await self._get_embedding(col["name"])
            if embedding:
                source_embeddings[col["name"]] = embedding

        if not source_embeddings:
            return []

        # 获取目标列的 Embeddings 并计算相似度
        for target_col in target_columns:
            if target_col["name"] in exclude:
                continue

            target_embedding = await self._get_embedding(target_col["name"])
            if not target_embedding:
                continue

            for source_name, source_embedding in source_embeddings.items():
                similarity = self._cosine_similarity(source_embedding, target_embedding)

                if similarity >= threshold:
                    # 查找源列信息
                    source_col = next((c for c in source_columns if c["name"] == source_name), None)
                    if not source_col:
                        continue

                    matches.append(JoinKeyPair(
                        source_column=source_col["name"],
                        target_column=target_col["name"],
                        source_table=source_table,
                        target_table=target_table,
                        confidence=similarity * 0.9,  # Embedding 结果权重较高
                        detection_method="embedding_semantic",
                        name_similarity=similarity,
                        is_primary_key=source_col.get("is_primary_key", False),
                        is_foreign_key=target_col.get("is_foreign_key", False),
                    ))

        return matches

    def _calibrate_confidence_threshold(
        self,
        all_matches: List[JoinKeyPair],
        source_table_size: int,
        target_table_size: int
    ) -> float:
        """
        自适应校准置信度阈值

        根据表的大小和匹配数量动态调整阈值
        """
        if not all_matches:
            return self._name_similarity_threshold

        # 表越大，阈值越低（因为可能存在更多变体）
        base_threshold = self._name_similarity_threshold
        size_factor = math.log10(max(source_table_size, target_table_size) + 1) / 3

        # 匹配数量越多，阈值越高（选择最佳匹配）
        count_factor = min(len(all_matches) / 10, 0.2)

        adjusted_threshold = base_threshold - size_factor + count_factor
        return max(0.5, min(adjusted_threshold, 0.95))

    def detect_potential_join_keys(
        self,
        db: Session,
        source_table: str,
        target_tables: List[str],
        source_database: Optional[str] = None,
        target_database: Optional[str] = None,
        sample_size: int = 1000
    ) -> Dict[str, List[JoinKeyPair]]:
        """
        检测潜在的JOIN关键字对

        Args:
            db: 数据库会话
            source_table: 源表名
            target_tables: 目标表列表
            source_database: 源数据库名
            target_database: 目标数据库名
            sample_size: 采样大小

        Returns:
            每个目标表的候选关联对字典
        """
        results = {}

        # 获取源表的ID类字段
        source_columns = self._get_table_columns(db, source_table, source_database)
        source_id_columns = self._filter_id_columns(source_columns)

        for target_table in target_tables:
            join_keys = []

            # 获取目标表的ID类字段
            target_columns = self._get_table_columns(db, target_table, target_database)
            target_id_columns = self._filter_id_columns(target_columns)

            # 1. 名称完全匹配
            exact_matches = self._find_exact_name_matches(
                source_id_columns, target_id_columns,
                source_table, target_table
            )
            join_keys.extend(exact_matches)

            # 2. 名称模糊匹配
            fuzzy_matches = self._find_fuzzy_name_matches(
                source_id_columns, target_id_columns,
                source_table, target_table,
                exclude=[k.source_column for k in exact_matches]
            )
            join_keys.extend(fuzzy_matches)

            # 3. 语义等价匹配
            semantic_matches = self._find_semantic_matches(
                source_id_columns, target_id_columns,
                source_table, target_table,
                exclude=[k.source_column for k in exact_matches + fuzzy_matches]
            )
            join_keys.extend(semantic_matches)

            # 4. 值域分析匹配（如果前面方法找不到）
            if len(join_keys) < 3:
                value_matches = self._find_value_based_matches(
                    db, source_table, target_table,
                    source_id_columns, target_id_columns,
                    source_database, target_database,
                    sample_size,
                    exclude=[k.source_column for k in join_keys]
                )
                join_keys.extend(value_matches)

            # 按置信度排序
            join_keys.sort(key=lambda x: x.confidence, reverse=True)
            results[target_table] = join_keys

        return results

    def validate_join_consistency(
        self,
        db: Session,
        source_table: str,
        source_key: str,
        target_table: str,
        target_key: str,
        source_database: Optional[str] = None,
        target_database: Optional[str] = None,
        sample_size: int = 10000
    ) -> JoinQualityScore:
        """
        验证JOIN数据一致性

        计算：
        - 匹配率：源表记录能关联上的比例
        - 覆盖率：目标表记录被关联的比例
        - 倾斜度：关联结果分布均匀程度
        - 孤立率：无法关联的记录比例
        """
        try:
            source_full = f"{source_database}.{source_table}" if source_database else source_table
            target_full = f"{target_database}.{target_table}" if target_database else target_table

            # 获取源表总数和非空键数
            source_stats = self._get_key_statistics(
                db, source_full, source_key, sample_size
            )

            # 获取目标表总数和非空键数
            target_stats = self._get_key_statistics(
                db, target_full, target_key, sample_size
            )

            # 计算匹配统计
            join_stats = self._get_join_statistics(
                db, source_full, source_key,
                target_full, target_key, sample_size
            )

            # 计算各项指标
            match_rate = join_stats["matched_count"] / source_stats["non_null_count"] \
                if source_stats["non_null_count"] > 0 else 0

            coverage_rate = join_stats["matched_distinct"] / target_stats["distinct_count"] \
                if target_stats["distinct_count"] > 0 else 0

            null_key_rate = source_stats["null_count"] / source_stats["total_count"] \
                if source_stats["total_count"] > 0 else 0

            orphan_rate = 1 - match_rate

            duplicate_rate = (source_stats["total_count"] - source_stats["distinct_count"]) / \
                             source_stats["total_count"] if source_stats["total_count"] > 0 else 0

            # 计算倾斜度（基于关联结果的分布）
            skew_factor = self._calculate_skew_factor(join_stats)

            # 计算综合评分
            overall_score = self._calculate_overall_score(
                match_rate, coverage_rate, skew_factor,
                orphan_rate, null_key_rate, duplicate_rate
            )

            # 生成问题列表
            issues = []
            if match_rate < 0.5:
                issues.append(f"匹配率较低({match_rate:.1%})，可能存在数据不一致")
            if null_key_rate > 0.1:
                issues.append(f"空键率较高({null_key_rate:.1%})，建议清洗数据")
            if skew_factor > 0.8:
                issues.append(f"数据倾斜严重({skew_factor:.2f})，可能影响JOIN性能")
            if duplicate_rate > 0.5:
                issues.append(f"重复率较高({duplicate_rate:.1%})，考虑去重处理")

            # 推荐JOIN类型
            recommendation = self._recommend_join_type(
                match_rate, coverage_rate, orphan_rate
            )

            return JoinQualityScore(
                overall_score=overall_score,
                match_rate=match_rate,
                coverage_rate=coverage_rate,
                skew_factor=skew_factor,
                orphan_rate=orphan_rate,
                null_key_rate=null_key_rate,
                duplicate_rate=duplicate_rate,
                recommendation=recommendation,
                issues=issues
            )

        except Exception as e:
            logger.error(f"验证JOIN一致性失败: {e}")
            return JoinQualityScore(
                overall_score=0,
                match_rate=0,
                coverage_rate=0,
                skew_factor=1,
                orphan_rate=1,
                null_key_rate=0,
                duplicate_rate=0,
                recommendation="unknown",
                issues=[f"验证失败: {str(e)}"]
            )

    def recommend_join_strategy(
        self,
        db: Session,
        source_table: str,
        target_table: str,
        join_keys: List[JoinKeyPair],
        source_database: Optional[str] = None,
        target_database: Optional[str] = None
    ) -> JoinStrategyRecommendation:
        """
        推荐最优JOIN策略

        返回：JOIN类型、条件、索引建议
        """
        if not join_keys:
            return JoinStrategyRecommendation(
                join_type=JoinType.CROSS,
                join_keys=[],
                estimated_result_count=0,
                quality_score=JoinQualityScore(
                    overall_score=0, match_rate=0, coverage_rate=0,
                    skew_factor=1, orphan_rate=1, null_key_rate=0,
                    duplicate_rate=0, recommendation="无法推荐",
                    issues=["未找到可用的关联键"]
                ),
                sql_template="",
                index_suggestions=[],
                performance_notes=["未检测到关联键，无法生成JOIN策略"],
                warnings=["请手动指定关联键"]
            )

        # 选择最佳关联键（置信度最高的）
        best_key = join_keys[0]

        # 验证JOIN质量
        quality_score = self.validate_join_consistency(
            db, source_table, best_key.source_column,
            target_table, best_key.target_column,
            source_database, target_database
        )

        # 估算结果数量
        estimated_count = self._estimate_join_result_count(
            db, source_table, target_table,
            best_key.source_column, best_key.target_column,
            quality_score.match_rate,
            source_database, target_database
        )

        # 确定JOIN类型
        join_type = JoinType(quality_score.recommendation) \
            if quality_score.recommendation in [e.value for e in JoinType] \
            else JoinType.LEFT

        # 生成SQL模板
        source_full = f"{source_database}.{source_table}" if source_database else source_table
        target_full = f"{target_database}.{target_table}" if target_database else target_table

        join_conditions = []
        for key in join_keys[:3]:  # 最多使用3个关联键
            join_conditions.append(
                f"s.{key.source_column} = t.{key.target_column}"
            )

        sql_template = f"""SELECT *
FROM {source_full} s
{join_type.value.upper()} JOIN {target_full} t
ON {' AND '.join(join_conditions)}"""

        # 索引建议
        index_suggestions = []
        for key in join_keys[:3]:
            if not key.is_primary_key:
                index_suggestions.append({
                    "table": source_table,
                    "column": key.source_column,
                    "type": "btree",
                    "reason": "JOIN关联键，建议添加索引以提升性能"
                })
            if not key.is_foreign_key:
                index_suggestions.append({
                    "table": target_table,
                    "column": key.target_column,
                    "type": "btree",
                    "reason": "JOIN关联键，建议添加索引以提升性能"
                })

        # 性能提示
        performance_notes = []
        if quality_score.skew_factor > 0.7:
            performance_notes.append("数据存在倾斜，考虑使用广播JOIN或salting技术")
        if estimated_count > 1000000:
            performance_notes.append("预估结果集较大，建议分批处理或增加过滤条件")
        if len(join_keys) > 1:
            performance_notes.append("存在多个候选关联键，当前选择置信度最高的")

        # 警告
        warnings = quality_score.issues.copy()
        if best_key.confidence < 0.7:
            warnings.append(f"关联键置信度较低({best_key.confidence:.2f})，建议人工确认")

        return JoinStrategyRecommendation(
            join_type=join_type,
            join_keys=join_keys[:3],
            estimated_result_count=estimated_count,
            quality_score=quality_score,
            sql_template=sql_template,
            index_suggestions=index_suggestions,
            performance_notes=performance_notes,
            warnings=warnings
        )

    def generate_kettle_join_config(
        self,
        strategy: JoinStrategyRecommendation,
        source_step_name: str = "Source",
        target_step_name: str = "Target"
    ) -> Dict:
        """
        生成Kettle JOIN步骤配置

        返回可用于Kettle转换的配置字典
        """
        # 映射JOIN类型到Kettle步骤类型
        kettle_join_types = {
            JoinType.INNER: "MergeJoin",
            JoinType.LEFT: "MergeJoin",
            JoinType.RIGHT: "MergeJoin",
            JoinType.FULL: "MergeJoin",
            JoinType.CROSS: "JoinRows",
        }

        step_type = kettle_join_types.get(strategy.join_type, "MergeJoin")

        # 构建Kettle配置
        config = {
            "step_type": step_type,
            "step_name": f"Join_{source_step_name}_{target_step_name}",
            "join_type": strategy.join_type.value.upper(),
            "keys_1": [k.source_column for k in strategy.join_keys],
            "keys_2": [k.target_column for k in strategy.join_keys],
            "input_step_1": source_step_name,
            "input_step_2": target_step_name,
            "settings": {
                "main_stream": source_step_name,
                "lookup_stream": target_step_name,
            },
            "metadata": {
                "confidence": strategy.join_keys[0].confidence if strategy.join_keys else 0,
                "quality_score": strategy.quality_score.overall_score,
                "estimated_rows": strategy.estimated_result_count,
                "warnings": strategy.warnings,
            }
        }

        # 如果是MergeJoin，需要预排序
        if step_type == "MergeJoin":
            config["pre_sort_required"] = True
            config["sort_steps"] = [
                {
                    "step_name": f"Sort_{source_step_name}",
                    "input_step": source_step_name,
                    "sort_fields": [{"name": k.source_column, "ascending": True}
                                    for k in strategy.join_keys]
                },
                {
                    "step_name": f"Sort_{target_step_name}",
                    "input_step": target_step_name,
                    "sort_fields": [{"name": k.target_column, "ascending": True}
                                    for k in strategy.join_keys]
                }
            ]

        return config

    def detect_multi_table_join_path(
        self,
        db: Session,
        tables: List[str],
        database: Optional[str] = None,
        max_depth: int = 3
    ) -> List[Dict]:
        """
        检测多表之间的JOIN路径

        用于发现间接关联关系，如 A -> B -> C
        """
        if len(tables) < 2:
            return []

        paths = []
        visited = set()

        def find_paths(current: str, target: str, path: List, depth: int):
            if depth > max_depth:
                return
            if current == target:
                paths.append(path.copy())
                return
            if current in visited:
                return

            visited.add(current)

            # 获取当前表可以关联的其他表
            for table in tables:
                if table not in visited and table != current:
                    # 检测两表之间的关联键
                    join_keys = self.detect_potential_join_keys(
                        db, current, [table], database, database
                    )

                    if join_keys.get(table):
                        best_key = join_keys[table][0]
                        if best_key.confidence >= 0.5:
                            path.append({
                                "from_table": current,
                                "to_table": table,
                                "join_key": best_key.to_dict(),
                            })
                            find_paths(table, target, path, depth + 1)
                            path.pop()

            visited.remove(current)

        # 从第一个表开始，找到所有其他表的路径
        source = tables[0]
        for target in tables[1:]:
            find_paths(source, target, [], 0)

        return paths

    # ==================== 辅助方法 ====================

    def _get_table_columns(
        self,
        db: Session,
        table_name: str,
        database_name: Optional[str] = None
    ) -> List[Dict]:
        """获取表的列信息"""
        from models.metadata import MetadataColumn

        query = db.query(MetadataColumn).filter(
            MetadataColumn.table_name == table_name
        )

        if database_name:
            query = query.filter(MetadataColumn.database_name == database_name)

        columns = query.order_by(MetadataColumn.position).all()

        return [
            {
                "name": col.column_name,
                "type": col.data_type or "varchar",
                "nullable": col.is_nullable,
                "is_primary_key": col.is_primary_key if hasattr(col, 'is_primary_key') else False,
                "is_foreign_key": col.is_foreign_key if hasattr(col, 'is_foreign_key') else False,
                "description": col.description,
            }
            for col in columns
        ]

    def _filter_id_columns(self, columns: List[Dict]) -> List[Dict]:
        """筛选出ID类字段"""
        id_columns = []

        for col in columns:
            name = col["name"].lower()
            # 检查是否匹配ID模式
            for pattern in self.ID_PATTERNS:
                if re.match(pattern, name):
                    id_columns.append(col)
                    break

        return id_columns

    def _find_exact_name_matches(
        self,
        source_columns: List[Dict],
        target_columns: List[Dict],
        source_table: str,
        target_table: str
    ) -> List[JoinKeyPair]:
        """查找名称完全匹配的字段"""
        matches = []
        target_names = {col["name"].lower(): col for col in target_columns}

        for source_col in source_columns:
            source_name = source_col["name"].lower()
            if source_name in target_names:
                target_col = target_names[source_name]
                matches.append(JoinKeyPair(
                    source_column=source_col["name"],
                    target_column=target_col["name"],
                    source_table=source_table,
                    target_table=target_table,
                    confidence=0.95,
                    detection_method="name_match",
                    name_similarity=1.0,
                    is_primary_key=source_col.get("is_primary_key", False),
                    is_foreign_key=target_col.get("is_foreign_key", False),
                ))

        return matches

    def _find_fuzzy_name_matches(
        self,
        source_columns: List[Dict],
        target_columns: List[Dict],
        source_table: str,
        target_table: str,
        exclude: List[str] = None
    ) -> List[JoinKeyPair]:
        """查找名称模糊匹配的字段（使用增强算法）"""
        matches = []
        exclude = set(exclude or [])

        for source_col in source_columns:
            if source_col["name"] in exclude:
                continue

            source_name = source_col["name"]

            for target_col in target_columns:
                target_name = target_col["name"]

                # 使用增强的相似度计算
                similarity = self._enhanced_name_similarity(source_name, target_name)

                if similarity >= self._name_similarity_threshold and similarity < 1.0:
                    matches.append(JoinKeyPair(
                        source_column=source_col["name"],
                        target_column=target_col["name"],
                        source_table=source_table,
                        target_table=target_table,
                        confidence=similarity * 0.88,  # 提高模糊匹配的置信度
                        detection_method="enhanced_fuzzy_match",
                        name_similarity=similarity,
                        is_primary_key=source_col.get("is_primary_key", False),
                        is_foreign_key=target_col.get("is_foreign_key", False),
                    ))

        return matches

    async def detect_potential_join_keys_async(
        self,
        db: Session,
        source_table: str,
        target_tables: List[str],
        source_database: Optional[str] = None,
        target_database: Optional[str] = None,
        sample_size: int = 1000,
        use_embeddings: bool = True
    ) -> Dict[str, List[JoinKeyPair]]:
        """
        异步检测潜在的JOIN关键字对（包含 Embedding 语义匹配）

        Args:
            db: 数据库会话
            source_table: 源表名
            target_tables: 目标表列表
            source_database: 源数据库名
            target_database: 目标数据库名
            sample_size: 采样大小
            use_embeddings: 是否使用 Embedding 语义匹配

        Returns:
            每个目标表的候选关联对字典
        """
        results = {}

        # 获取源表的ID类字段
        source_columns = self._get_table_columns(db, source_table, source_database)
        source_id_columns = self._filter_id_columns(source_columns)

        for target_table in target_tables:
            join_keys = []

            # 获取目标表的ID类字段
            target_columns = self._get_table_columns(db, target_table, target_database)
            target_id_columns = self._filter_id_columns(target_columns)

            # 1. 名称完全匹配
            exact_matches = self._find_exact_name_matches(
                source_id_columns, target_id_columns,
                source_table, target_table
            )
            join_keys.extend(exact_matches)

            # 2. 增强的名称模糊匹配
            fuzzy_matches = self._find_fuzzy_name_matches(
                source_id_columns, target_id_columns,
                source_table, target_table,
                exclude=[k.source_column for k in exact_matches]
            )
            join_keys.extend(fuzzy_matches)

            # 3. 语义等价匹配
            semantic_matches = self._find_semantic_matches(
                source_id_columns, target_id_columns,
                source_table, target_table,
                exclude=[k.source_column for k in exact_matches + fuzzy_matches]
            )
            join_keys.extend(semantic_matches)

            # 4. Embedding 语义匹配（如果可用）
            if use_embeddings and len(join_keys) < 5:
                embedding_matches = await self._find_embedding_semantic_matches(
                    source_id_columns, target_id_columns,
                    source_table, target_table,
                    exclude={k.source_column for k in join_keys}
                )
                join_keys.extend(embedding_matches)

            # 5. 值域分析匹配（如果前面方法找不到足够的匹配）
            if len(join_keys) < 3:
                value_matches = self._find_value_based_matches(
                    db, source_table, target_table,
                    source_id_columns, target_id_columns,
                    source_database, target_database,
                    sample_size,
                    exclude=[k.source_column for k in join_keys]
                )
                join_keys.extend(value_matches)

            # 自适应校准阈值
            source_count = self._get_table_count(db, source_table, source_database)
            target_count = self._get_table_count(db, target_table, target_database)
            threshold = self._calibrate_confidence_threshold(join_keys, source_count, target_count)

            # 过滤低置信度的匹配
            join_keys = [k for k in join_keys if k.confidence >= threshold]

            # 按置信度排序
            join_keys.sort(key=lambda x: x.confidence, reverse=True)
            results[target_table] = join_keys

        return results

    def _get_table_count(
        self,
        db: Session,
        table_name: str,
        database_name: Optional[str] = None
    ) -> int:
        """获取表的行数"""
        try:
            full_name = f"{database_name}.{table_name}" if database_name else table_name
            sql = text(f"SELECT COUNT(*) FROM {full_name}")
            return db.execute(sql).scalar() or 0
        except Exception:
            return 0

    def _find_semantic_matches(
        self,
        source_columns: List[Dict],
        target_columns: List[Dict],
        source_table: str,
        target_table: str,
        exclude: List[str] = None
    ) -> List[JoinKeyPair]:
        """查找语义等价的字段"""
        matches = []
        exclude = set(exclude or [])

        for source_col in source_columns:
            if source_col["name"] in exclude:
                continue

            source_name = source_col["name"].lower()

            # 检查是否在语义等价映射中
            for canonical, equivalents in self.SEMANTIC_EQUIVALENTS.items():
                all_names = [canonical] + equivalents

                if source_name in all_names or any(
                    source_name.endswith(f"_{n}") or source_name.startswith(f"{n}_")
                    for n in all_names
                ):
                    # 在目标列中查找等价字段
                    for target_col in target_columns:
                        target_name = target_col["name"].lower()

                        if target_name in all_names or any(
                            target_name.endswith(f"_{n}") or target_name.startswith(f"{n}_")
                            for n in all_names
                        ):
                            if source_name != target_name:  # 避免与精确匹配重复
                                matches.append(JoinKeyPair(
                                    source_column=source_col["name"],
                                    target_column=target_col["name"],
                                    source_table=source_table,
                                    target_table=target_table,
                                    confidence=0.8,
                                    detection_method="semantic",
                                    name_similarity=0.0,
                                    is_primary_key=source_col.get("is_primary_key", False),
                                    is_foreign_key=target_col.get("is_foreign_key", False),
                                ))

        return matches

    def _find_value_based_matches(
        self,
        db: Session,
        source_table: str,
        target_table: str,
        source_columns: List[Dict],
        target_columns: List[Dict],
        source_database: Optional[str],
        target_database: Optional[str],
        sample_size: int,
        exclude: List[str] = None
    ) -> List[JoinKeyPair]:
        """基于值域分析查找匹配的字段"""
        matches = []
        exclude = set(exclude or [])

        source_full = f"{source_database}.{source_table}" if source_database else source_table
        target_full = f"{target_database}.{target_table}" if target_database else target_table

        for source_col in source_columns:
            if source_col["name"] in exclude:
                continue

            for target_col in target_columns:
                try:
                    # 计算值域重叠率
                    overlap_rate = self._calculate_value_overlap(
                        db, source_full, source_col["name"],
                        target_full, target_col["name"],
                        sample_size
                    )

                    if overlap_rate >= self._value_overlap_threshold:
                        matches.append(JoinKeyPair(
                            source_column=source_col["name"],
                            target_column=target_col["name"],
                            source_table=source_table,
                            target_table=target_table,
                            confidence=overlap_rate * 0.7,
                            detection_method="value_analysis",
                            value_overlap_rate=overlap_rate,
                            is_primary_key=source_col.get("is_primary_key", False),
                            is_foreign_key=target_col.get("is_foreign_key", False),
                        ))

                except Exception as e:
                    logger.warning(f"值域分析失败 {source_col['name']} -> {target_col['name']}: {e}")
                    continue

        return matches

    def _calculate_name_similarity(self, name1: str, name2: str) -> float:
        """计算字段名相似度"""
        if name1 == name2:
            return 1.0

        # 包含关系
        if name1 in name2 or name2 in name1:
            return 0.8

        # Levenshtein距离
        distance = self._levenshtein_distance(name1, name2)
        max_len = max(len(name1), len(name2))
        if max_len == 0:
            return 0.0

        return 1 - (distance / max_len)

    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """计算Levenshtein距离"""
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)

        if len(s2) == 0:
            return len(s1)

        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row

        return previous_row[-1]

    def _calculate_value_overlap(
        self,
        db: Session,
        source_table: str,
        source_column: str,
        target_table: str,
        target_column: str,
        sample_size: int
    ) -> float:
        """计算两个字段的值域重叠率"""
        try:
            # 获取源表去重值
            source_sql = text(f"""
                SELECT DISTINCT {source_column}
                FROM {source_table}
                WHERE {source_column} IS NOT NULL
                LIMIT :sample_size
            """)
            source_values = set(
                row[0] for row in db.execute(source_sql, {"sample_size": sample_size})
            )

            if not source_values:
                return 0.0

            # 计算在目标表中存在的比例
            target_sql = text(f"""
                SELECT COUNT(DISTINCT {target_column})
                FROM {target_table}
                WHERE {target_column} IN :values
            """)
            result = db.execute(target_sql, {"values": tuple(source_values)})
            matched_count = result.scalar() or 0

            return matched_count / len(source_values)

        except Exception as e:
            logger.warning(f"计算值域重叠失败: {e}")
            return 0.0

    def _get_key_statistics(
        self,
        db: Session,
        table: str,
        key_column: str,
        sample_size: int
    ) -> Dict:
        """获取关联键的统计信息"""
        try:
            sql = text(f"""
                SELECT
                    COUNT(*) as total_count,
                    COUNT({key_column}) as non_null_count,
                    COUNT(*) - COUNT({key_column}) as null_count,
                    COUNT(DISTINCT {key_column}) as distinct_count
                FROM (
                    SELECT {key_column}
                    FROM {table}
                    LIMIT :sample_size
                ) t
            """)
            result = db.execute(sql, {"sample_size": sample_size}).fetchone()

            return {
                "total_count": result[0] or 0,
                "non_null_count": result[1] or 0,
                "null_count": result[2] or 0,
                "distinct_count": result[3] or 0,
            }

        except Exception as e:
            logger.warning(f"获取键统计失败: {e}")
            return {
                "total_count": 0,
                "non_null_count": 0,
                "null_count": 0,
                "distinct_count": 0,
            }

    def _get_join_statistics(
        self,
        db: Session,
        source_table: str,
        source_key: str,
        target_table: str,
        target_key: str,
        sample_size: int
    ) -> Dict:
        """获取JOIN操作的统计信息"""
        try:
            sql = text(f"""
                SELECT
                    COUNT(*) as matched_count,
                    COUNT(DISTINCT s.{source_key}) as matched_distinct,
                    MAX(cnt) as max_match_per_key,
                    AVG(cnt) as avg_match_per_key
                FROM (
                    SELECT s.{source_key}, COUNT(*) as cnt
                    FROM (SELECT {source_key} FROM {source_table} LIMIT :sample_size) s
                    INNER JOIN {target_table} t ON s.{source_key} = t.{target_key}
                    GROUP BY s.{source_key}
                ) stats
            """)
            result = db.execute(sql, {"sample_size": sample_size}).fetchone()

            return {
                "matched_count": result[0] or 0,
                "matched_distinct": result[1] or 0,
                "max_match_per_key": result[2] or 0,
                "avg_match_per_key": float(result[3] or 0),
            }

        except Exception as e:
            logger.warning(f"获取JOIN统计失败: {e}")
            return {
                "matched_count": 0,
                "matched_distinct": 0,
                "max_match_per_key": 0,
                "avg_match_per_key": 0,
            }

    def _calculate_skew_factor(self, join_stats: Dict) -> float:
        """计算数据倾斜因子"""
        max_match = join_stats.get("max_match_per_key", 0)
        avg_match = join_stats.get("avg_match_per_key", 0)

        if avg_match <= 0:
            return 1.0

        # 倾斜因子 = (最大匹配数 - 平均匹配数) / 最大匹配数
        skew = (max_match - avg_match) / max_match if max_match > 0 else 0
        return min(skew, 1.0)

    def _calculate_overall_score(
        self,
        match_rate: float,
        coverage_rate: float,
        skew_factor: float,
        orphan_rate: float,
        null_key_rate: float,
        duplicate_rate: float
    ) -> float:
        """计算综合质量评分"""
        # 权重配置
        weights = {
            "match_rate": 0.30,
            "coverage_rate": 0.25,
            "skew_penalty": 0.15,
            "orphan_penalty": 0.15,
            "null_penalty": 0.10,
            "duplicate_penalty": 0.05,
        }

        score = (
            match_rate * weights["match_rate"] +
            coverage_rate * weights["coverage_rate"] +
            (1 - skew_factor) * weights["skew_penalty"] +
            (1 - orphan_rate) * weights["orphan_penalty"] +
            (1 - null_key_rate) * weights["null_penalty"] +
            (1 - duplicate_rate) * weights["duplicate_penalty"]
        )

        return min(max(score, 0), 1)

    def _recommend_join_type(
        self,
        match_rate: float,
        coverage_rate: float,
        orphan_rate: float
    ) -> str:
        """推荐JOIN类型"""
        if match_rate >= 0.9 and coverage_rate >= 0.9:
            return "inner"
        elif match_rate >= 0.7:
            return "inner"
        elif orphan_rate > 0.3:
            return "left"
        else:
            return "left"

    def _estimate_join_result_count(
        self,
        db: Session,
        source_table: str,
        target_table: str,
        source_key: str,
        target_key: str,
        match_rate: float,
        source_database: Optional[str] = None,
        target_database: Optional[str] = None
    ) -> int:
        """估算JOIN结果数量"""
        try:
            source_full = f"{source_database}.{source_table}" if source_database else source_table

            sql = text(f"SELECT COUNT(*) FROM {source_full}")
            source_count = db.execute(sql).scalar() or 0

            return int(source_count * match_rate)

        except Exception as e:
            logger.warning(f"估算结果数量失败: {e}")
            return 0


    # ==================== JOIN 执行方法 ====================

    def execute_join(
        self,
        db: Session,
        source_table: str,
        target_table: str,
        join_keys: List[JoinKeyPair],
        join_type: JoinType = JoinType.LEFT,
        select_columns: Optional[Dict[str, List[str]]] = None,
        where_clause: Optional[str] = None,
        source_database: Optional[str] = None,
        target_database: Optional[str] = None,
        limit: int = 1000,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        执行 JOIN 查询并返回结果

        Args:
            db: 数据库会话
            source_table: 源表名
            target_table: 目标表名
            join_keys: 关联键列表
            join_type: JOIN 类型
            select_columns: 选择的列 {"source": [...], "target": [...]}，None 表示 SELECT *
            where_clause: 额外的 WHERE 条件
            source_database: 源数据库名
            target_database: 目标数据库名
            limit: 返回行数限制
            offset: 偏移量

        Returns:
            JOIN 查询结果
        """
        if not join_keys:
            return {
                "success": False,
                "error": "未提供关联键",
                "data": [],
                "total": 0,
            }

        source_full = f"{source_database}.{source_table}" if source_database else source_table
        target_full = f"{target_database}.{target_table}" if target_database else target_table

        # 构建 SELECT 子句
        if select_columns:
            source_cols = [f"s.{c}" for c in select_columns.get("source", ["*"])]
            target_cols = [f"t.{c}" for c in select_columns.get("target", ["*"])]
            select_clause = ", ".join(source_cols + target_cols)
        else:
            select_clause = "s.*, t.*"

        # 构建 JOIN 条件
        join_conditions = []
        for key in join_keys[:3]:
            join_conditions.append(f"s.{key.source_column} = t.{key.target_column}")
        on_clause = " AND ".join(join_conditions)

        # 构建完整 SQL
        join_type_sql = join_type.value.upper()
        sql = (
            f"SELECT {select_clause} "
            f"FROM {source_full} s "
            f"{join_type_sql} JOIN {target_full} t ON {on_clause}"
        )

        if where_clause:
            sql += f" WHERE {where_clause}"

        # 先获取总数
        count_sql = f"SELECT COUNT(*) FROM ({sql}) _count_query"
        sql += f" LIMIT {limit} OFFSET {offset}"

        try:
            # 获取总数
            total = 0
            try:
                count_result = db.execute(text(count_sql))
                total = count_result.scalar() or 0
            except Exception as e:
                logger.warning(f"获取总数失败，跳过: {e}")

            # 执行查询
            result = db.execute(text(sql))
            rows = result.fetchall()

            # 转换为字典列表
            data = []
            column_names = list(result.keys()) if hasattr(result, 'keys') else []
            for row in rows:
                if hasattr(row, '_mapping'):
                    data.append(dict(row._mapping))
                elif column_names:
                    data.append(dict(zip(column_names, row)))
                else:
                    data.append({str(i): v for i, v in enumerate(row)})

            return {
                "success": True,
                "data": data,
                "row_count": len(data),
                "total": total if total > 0 else len(data),
                "limit": limit,
                "offset": offset,
                "join_type": join_type.value,
                "join_keys": [k.to_dict() for k in join_keys[:3]],
                "sql": sql,
            }

        except Exception as e:
            logger.error(f"JOIN 执行失败: {e}")
            return {
                "success": False,
                "error": f"JOIN 执行失败: {str(e)}",
                "data": [],
                "total": 0,
                "sql": sql,
            }

    def execute_fusion(
        self,
        db: Session,
        source_table: str,
        target_table: str,
        source_database: Optional[str] = None,
        target_database: Optional[str] = None,
        output_table: Optional[str] = None,
        select_columns: Optional[Dict[str, List[str]]] = None,
        limit: int = 1000
    ) -> Dict[str, Any]:
        """
        一站式表融合：自动检测关联键、推荐策略、执行 JOIN

        Args:
            db: 数据库会话
            source_table: 源表名
            target_table: 目标表名
            source_database: 源数据库名
            target_database: 目标数据库名
            output_table: 输出表名（如提供则将结果写入该表）
            select_columns: 选择的列
            limit: 返回行数限制

        Returns:
            融合结果
        """
        # 1. 检测关联键
        join_keys_map = self.detect_potential_join_keys(
            db, source_table, [target_table],
            source_database, target_database
        )

        join_keys = join_keys_map.get(target_table, [])
        if not join_keys:
            return {
                "success": False,
                "error": f"未能在 {source_table} 和 {target_table} 之间检测到关联键",
                "phase": "detection",
            }

        # 2. 推荐策略
        strategy = self.recommend_join_strategy(
            db, source_table, target_table,
            join_keys, source_database, target_database
        )

        # 3. 执行 JOIN
        result = self.execute_join(
            db, source_table, target_table,
            strategy.join_keys,
            strategy.join_type,
            select_columns=select_columns,
            source_database=source_database,
            target_database=target_database,
            limit=limit
        )

        # 4. 如果指定了输出表，将结果写入
        if output_table and result.get("success"):
            write_result = self._write_join_result(
                db, strategy, output_table,
                source_database, target_database,
                select_columns
            )
            result["output_table"] = write_result

        # 合并策略信息
        result["strategy"] = strategy.to_dict()
        result["detected_keys"] = [k.to_dict() for k in join_keys]

        return result

    def _write_join_result(
        self,
        db: Session,
        strategy: JoinStrategyRecommendation,
        output_table: str,
        source_database: Optional[str] = None,
        target_database: Optional[str] = None,
        select_columns: Optional[Dict[str, List[str]]] = None
    ) -> Dict[str, Any]:
        """将 JOIN 结果写入输出表"""
        try:
            # 使用 CREATE TABLE ... AS SELECT 语法
            source_full = f"{source_database}.{strategy.join_keys[0].source_table}" \
                if source_database else strategy.join_keys[0].source_table
            target_full = f"{target_database}.{strategy.join_keys[0].target_table}" \
                if target_database else strategy.join_keys[0].target_table

            if select_columns:
                source_cols = [f"s.{c}" for c in select_columns.get("source", ["*"])]
                target_cols = [f"t.{c}" for c in select_columns.get("target", ["*"])]
                select_clause = ", ".join(source_cols + target_cols)
            else:
                select_clause = "s.*, t.*"

            join_conditions = []
            for key in strategy.join_keys:
                join_conditions.append(f"s.{key.source_column} = t.{key.target_column}")

            join_type_sql = strategy.join_type.value.upper()

            create_sql = (
                f"CREATE TABLE IF NOT EXISTS {output_table} AS "
                f"SELECT {select_clause} "
                f"FROM {source_full} s "
                f"{join_type_sql} JOIN {target_full} t "
                f"ON {' AND '.join(join_conditions)}"
            )

            db.execute(text(create_sql))
            db.commit()

            # 获取行数
            count_result = db.execute(text(f"SELECT COUNT(*) FROM {output_table}"))
            row_count = count_result.scalar() or 0

            return {
                "success": True,
                "output_table": output_table,
                "row_count": row_count,
                "sql": create_sql,
            }

        except Exception as e:
            db.rollback()
            logger.error(f"写入输出表失败: {e}")
            return {
                "success": False,
                "error": f"写入输出表失败: {str(e)}",
            }


# 创建全局服务实例
_table_fusion_service = None


def get_table_fusion_service() -> TableFusionService:
    """获取多表融合服务实例"""
    global _table_fusion_service
    if _table_fusion_service is None:
        _table_fusion_service = TableFusionService()
    return _table_fusion_service
