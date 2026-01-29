"""
元数据 Schema 提供器
Production: 智能选择和注入 Schema 到 Text-to-SQL Prompt

功能：
1. 根据问题关键词智能选择相关表
2. 列级过滤（只选择相关列减少 Prompt 大小）
3. Schema 缓存机制
4. 关联表推荐
5. 示例数据注入
"""

import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


@dataclass
class ColumnInfo:
    """列信息"""
    name: str
    type: str
    nullable: bool
    description: str = ""
    is_primary: bool = False
    is_foreign: bool = False
    ref_table: Optional[str] = None
    ref_column: Optional[str] = None
    sample_values: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.type,
            "nullable": self.nullable,
            "description": self.description,
            "is_primary": self.is_primary,
            "is_foreign": self.is_foreign,
            "ref_table": self.ref_table,
            "ref_column": self.ref_column,
            "sample_values": self.sample_values
        }


@dataclass
class TableInfo:
    """表信息"""
    database: str
    name: str
    description: str = ""
    columns: List[ColumnInfo] = field(default_factory=list)
    relations: List[Dict[str, str]] = field(default_factory=list)
    row_count: int = 0
    sample_data: List[Dict[str, Any]] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)

    @property
    def full_name(self) -> str:
        return f"{self.database}.{self.name}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "database": self.database,
            "name": self.name,
            "full_name": self.full_name,
            "description": self.description,
            "columns": [c.to_dict() for c in self.columns],
            "relations": self.relations,
            "row_count": self.row_count,
            "sample_data": self.sample_data,
            "tags": self.tags
        }


@dataclass
class SchemaSelectionResult:
    """Schema 选择结果"""
    tables: List[TableInfo]
    selected_columns: Dict[str, List[str]]  # table_name -> [column_names]
    relevance_scores: Dict[str, float]  # table_name -> score
    suggested_joins: List[Dict[str, str]]  # join suggestions
    total_tokens: int = 0

    def to_prompt_context(self, max_tokens: int = 4000) -> str:
        """转换为 Prompt 上下文"""
        parts = []

        # 按相关性排序
        sorted_tables = sorted(
            self.tables,
            key=lambda t: self.relevance_scores.get(t.full_name, 0),
            reverse=True
        )

        for table in sorted_tables:
            tokens_used = self.total_tokens - sum(
                len(t.name) + len(t.description) +
                sum(len(c.name) + len(c.description) for c in t.columns) * 2
                for t in self.tables[self.tables.index(table) + 1:]
            )

            if tokens_used > max_tokens:
                parts.append(f"\n### 表: {table.full_name} (详情省略，仅关键字段)")
            else:
                parts.append(f"\n### 表: {table.full_name}")
                if table.description:
                    parts.append(f"描述: {table.description}")

                # 只显示选中的列
                selected_cols = self.selected_columns.get(table.full_name, [])
                columns_to_show = [
                    c for c in table.columns
                    if not selected_cols or c.name in selected_cols
                ]

                if columns_to_show:
                    parts.append("字段:")
                    for col in columns_to_show:
                        col_desc = f"  - {col.name} ({col.type}"
                        if not col.nullable:
                            col_desc += ", NOT NULL"
                        if col.is_primary:
                            col_desc += ", PRIMARY KEY"
                        if col.is_foreign and col.ref_table:
                            col_desc += f", FK -> {col.ref_table}.{col.ref_column}"
                        col_desc += ")"
                        if col.description:
                            col_desc += f" -- {col.description}"
                        parts.append(col_desc)

                # 添加关联
                if table.relations:
                    parts.append("关联关系:")
                    for rel in table.relations:
                        parts.append(f"  - {rel.get('type', 'UNKNOWN')}: {rel.get('to_table', '')}")

        return "\n".join(parts)


class SchemaRelevanceScorer:
    """Schema 相关性评分器"""

    # 业务领域关键词映射
    DOMAIN_KEYWORDS = {
        "sales": ["销售", "销售额", "营收", "订单", "order", "sales", "revenue"],
        "customer": ["客户", "用户", "customer", "user", "买家"],
        "product": ["产品", "商品", "product", "item", "sku"],
        "inventory": ["库存", "仓库", "inventory", "stock", "仓储"],
        "finance": ["财务", "金额", "费用", "finance", "payment", "billing"],
        "time": ["时间", "日期", "time", "date", "day", "month", "year", "when"],
        "employee": ["员工", "职员", "employee", "staff", "worker"],
        "department": ["部门", "科室", "department", "unit", "division"],
    }

    # 列名模式映射
    COLUMN_PATTERNS = {
        "id": r".*(_id|id|_id)$",
        "name": r".*(name|title|label)$",
        "amount": r".*(amount|price|cost|fee|money|total|sum)$",
        "date": r".*(date|time|at|on)$",
        "status": r".*(status|state|stage)$",
        "quantity": r".*(qty|quantity|count|num|number)$",
        "user": r".*(user|customer|client|buyer)$",
    }

    def score_table(
        self,
        table: TableInfo,
        question: str,
        question_keywords: Set[str]
    ) -> float:
        """
        评估表与问题的相关性

        Args:
            table: 表信息
            question: 原始问题
            question_keywords: 问题中的关键词

        Returns:
            相关性得分 (0-1)
        """
        score = 0.0

        table_name_lower = table.name.lower()
        table_desc_lower = table.description.lower()
        question_lower = question.lower()

        # 1. 表名匹配 (权重: 0.4)
        for domain, keywords in self.DOMAIN_KEYWORDS.items():
            if any(kw in table_name_lower for kw in keywords):
                if any(kw in question_lower for kw in keywords):
                    score += 0.4
                    break

        # 2. 表描述匹配 (权重: 0.2)
        if table_desc_lower:
            for kw in question_keywords:
                if kw in table_desc_lower:
                    score += 0.1
                    if len(kw) > 2:  # 长词权重更高
                        score += 0.1

        # 3. 列名匹配 (权重: 0.3)
        column_names = [c.name.lower() for c in table.columns]
        matched_columns = 0
        for kw in question_keywords:
            for col_name in column_names:
                if kw in col_name or col_name in kw:
                    matched_columns += 1
                    break

        if table.columns:
            column_match_ratio = matched_columns / len(table.columns)
            score += column_match_ratio * 0.3

        # 4. 标签匹配 (权重: 0.1)
        for tag in table.tags:
            if tag.lower() in question_lower:
                score += 0.1

        return min(score, 1.0)

    def score_column(
        self,
        column: ColumnInfo,
        question: str,
        question_keywords: Set[str]
    ) -> float:
        """
        评估列与问题的相关性

        Args:
            column: 列信息
            question: 原始问题
            question_keywords: 问题中的关键词

        Returns:
            相关性得分 (0-1)
        """
        score = 0.0

        col_name_lower = column.name.lower()
        col_desc_lower = column.description.lower()
        question_lower = question.lower()

        # 1. 列名直接匹配
        for kw in question_keywords:
            if kw in col_name_lower:
                score += 0.5
                break

        # 2. 模式匹配
        for pattern_name, pattern in self.COLUMN_PATTERNS.items():
            if re.match(pattern, col_name_lower):
                # 检查问题是否涉及该模式
                pattern_keywords = self.DOMAIN_KEYWORDS.get(pattern_name, [])
                if any(kw in question_lower for kw in pattern_keywords):
                    score += 0.3
                break

        # 3. 描述匹配
        if col_desc_lower:
            for kw in question_keywords:
                if kw in col_desc_lower:
                    score += 0.2
                    break

        # 4. 主键/外键额外加分
        if column.is_primary and ("id" in question_lower or "标识" in question_lower):
            score += 0.1
        if column.is_foreign and "关联" in question_lower:
            score += 0.1

        return min(score, 1.0)


class SchemaProvider:
    """
    元数据 Schema 提供器

    从 data 元数据服务获取智能筛选的 Schema，
    用于 Text-to-SQL Prompt 注入。
    """

    def __init__(
        self,
        metadata_service=None,
        max_tables: int = 5,
        max_columns_per_table: int = 20,
        cache_ttl: int = 3600
    ):
        """
        初始化 Schema 提供器

        Args:
            metadata_service: 元数据服务实例
            max_tables: 最大返回表数
            max_columns_per_table: 每表最大返回列数
            cache_ttl: 缓存生存时间（秒）
        """
        # 延迟导入避免循环依赖
        if metadata_service is None:
            try:
                from services.metadata_integration import MetadataService
                self.metadata = MetadataService()
            except ImportError:
                # 如果没有独立的元数据服务，使用本地实现
                self.metadata = None
        else:
            self.metadata = metadata_service

        self.max_tables = max_tables
        self.max_columns_per_table = max_columns_per_table
        self.cache_ttl = cache_ttl

        self.scorer = SchemaRelevanceScorer()
        self._cache: Dict[str, Tuple[SchemaSelectionResult, float]] = {}

    def _make_cache_key(self, question: str, database: str) -> str:
        """生成缓存键"""
        return f"{database}:{hash(question.lower())}"

    async def get_schema_for_question(
        self,
        question: str,
        database: str = "sales_dw",
        max_tokens: int = 4000
    ) -> SchemaSelectionResult:
        """
        根据问题获取相关 Schema

        Args:
            question: 自然语言问题
            database: 数据库名称
            max_tokens: 最大 Prompt token 数

        Returns:
            Schema 选择结果
        """
        # 检查缓存
        cache_key = self._make_cache_key(question, database)
        if cache_key in self._cache:
            cached_result, timestamp = self._cache[cache_key]
            if datetime.now().timestamp() - timestamp < self.cache_ttl:
                logger.debug(f"Schema cache hit for question: {question[:50]}")
                return cached_result

        # 提取问题关键词
        keywords = self._extract_keywords(question)

        # 搜索相关表
        tables = await self._search_relevant_tables(question, keywords, database)

        if not tables:
            logger.warning(f"No tables found for question: {question[:100]}")
            return SchemaSelectionResult(
                tables=[],
                selected_columns={},
                relevance_scores={}
            )

        # 获取表结构详情
        detailed_tables = await self._get_table_details(tables, database)

        # 评分并排序
        scored_tables = self._score_tables(detailed_tables, question, keywords)

        # 选择 Top N 表
        selected_tables = scored_tables[:self.max_tables]

        # 选择相关列
        selected_columns, suggested_joins = await self._select_columns_and_joins(
            selected_tables, question, keywords
        )

        # 计算预估 token 数
        total_tokens = self._estimate_tokens(selected_tables, selected_columns)

        result = SchemaSelectionResult(
            tables=selected_tables,
            selected_columns=selected_columns,
            relevance_scores={t.full_name: self.scorer.score_table(t, question, keywords) for t in selected_tables},
            suggested_joins=suggested_joins,
            total_tokens=total_tokens
        )

        # 缓存结果
        self._cache[cache_key] = (result, datetime.now().timestamp())

        return result

    def _extract_keywords(self, question: str) -> Set[str]:
        """从问题中提取关键词"""
        import re

        # 移除标点符号
        cleaned = re.sub(r'[^\w\s\u4e00-\u9fff]', ' ', question)

        # 分词（中文和英文）
        words = re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z]+', cleaned.lower())

        # 过滤停用词
        stopwords = {
            "的", "了", "是", "在", "有", "和", "与", "或", "但", "而", "对",
            "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
            "have", "has", "had", "do", "does", "did", "will", "would", "could",
            "what", "how", "when", "where", "who", "which", "that", "this"
        }

        keywords = {w for w in words if len(w) > 1 and w not in stopwords}

        # 添加数字
        numbers = re.findall(r'\d+', question)
        keywords.update(numbers)

        return keywords

    async def _search_relevant_tables(
        self,
        question: str,
        keywords: Set[str],
        database: str
    ) -> List[Dict[str, Any]]:
        """搜索相关表"""
        try:
            # 构建搜索关键词（使用中英文组合）
            search_terms = list(keywords)[:10]  # 限制关键词数量
            search_query = " ".join(search_terms)

            tables = await self.metadata.search_tables(
                keywords=search_query,
                database=database,
                limit=self.max_tables * 2  # 多获取一些用于评分
            )

            return tables

        except Exception as e:
            logger.error(f"Failed to search tables: {e}")
            return []

    async def _get_table_details(
        self,
        tables: List[Dict[str, Any]],
        database: str
    ) -> List[TableInfo]:
        """获取表结构详情"""
        detailed_tables = []

        for table_info in tables:
            try:
                table_name = table_info.get("table", table_info.get("name", ""))
                db_name = table_info.get("database", database)

                schema = await self.metadata.get_table_schema(
                    database=db_name,
                    table=table_name,
                    include_sample_data=True
                )

                if schema:
                    detailed_tables.append(self._parse_table_info(schema, db_name))

            except Exception as e:
                logger.warning(f"Failed to get details for table {table_info}: {e}")
                continue

        return detailed_tables

    def _parse_table_info(self, schema: Dict, database: str) -> TableInfo:
        """解析表信息"""
        columns = []
        for col in schema.get("columns", []):
            columns.append(ColumnInfo(
                name=col.get("name", ""),
                type=col.get("type", ""),
                nullable=col.get("nullable", True),
                description=col.get("comment", col.get("description", "")),
                is_primary=col.get("is_primary", col.get("isPrimaryKey", False)),
                is_foreign=col.get("is_foreign", False),
                ref_table=col.get("ref_table"),
                ref_column=col.get("ref_column"),
                sample_values=col.get("sample_values", [])
            ))

        return TableInfo(
            database=database,
            name=schema.get("table", schema.get("name", "")),
            description=schema.get("description", ""),
            columns=columns,
            relations=schema.get("relations", []),
            row_count=schema.get("row_count", 0),
            sample_data=schema.get("sample_data", []),
            tags=schema.get("tags", [])
        )

    def _score_tables(
        self,
        tables: List[TableInfo],
        question: str,
        keywords: Set[str]
    ) -> List[TableInfo]:
        """对表进行评分并排序"""
        scored = [
            (table, self.scorer.score_table(table, question, keywords))
            for table in tables
        ]

        # 过滤掉得分过低的表
        scored = [(t, s) for t, s in scored if s > 0.1]

        # 按得分排序
        scored.sort(key=lambda x: x[1], reverse=True)

        return [t for t, _ in scored]

    async def _select_columns_and_joins(
        self,
        tables: List[TableInfo],
        question: str,
        keywords: Set[str]
    ) -> Tuple[Dict[str, List[str]], List[Dict[str, str]]]:
        """选择相关列和推荐 JOIN"""
        selected_columns = {}
        suggested_joins = []

        question_lower = question.lower()

        for table in tables:
            # 对列进行评分
            scored_columns = [
                (col, self.scorer.score_column(col, question, keywords))
                for col in table.columns
            ]

            # 总是包含主键
            for col in table.columns:
                if col.is_primary and not any(c == col for c, _ in scored_columns):
                    scored_columns.append((col, 0.5))

            # 按得分排序
            scored_columns.sort(key=lambda x: x[1], reverse=True)

            # 选择 Top N 列
            top_columns = scored_columns[:self.max_columns_per_table]

            # 过滤掉得分过低的列
            threshold = 0.1
            selected = [c.name for c, s in top_columns if s > threshold]

            if not selected:
                # 如果没有列被选中，至少返回前 5 列
                selected = [c.name for c, _ in top_columns[:5]]

            selected_columns[table.full_name] = selected

        # 推荐 JOIN
        suggested_joins = self._suggest_joins(tables, question_lower)

        return selected_columns, suggested_joins

    def _suggest_joins(
        self,
        tables: List[TableInfo],
        question_lower: str
    ) -> List[Dict[str, str]]:
        """推荐 JOIN 关系"""
        joins = []

        # 检查表之间的外键关系
        for table in tables:
            for col in table.columns:
                if col.is_foreign and col.ref_table:
                    # 检查引用的表是否在当前表列表中
                    ref_table_full = f"{table.database}.{col.ref_table}"
                    if any(t.full_name == ref_table_full for t in tables):
                        joins.append({
                            "from_table": table.full_name,
                            "from_column": col.name,
                            "to_table": ref_table_full,
                            "to_column": col.ref_column or "id",
                            "type": "LEFT JOIN"
                        })

        # 如果问题中包含关联关键词，增加 JOIN 建议权重
        if any(kw in question_lower for kw in ["关联", "相关", "联合", "join", "combine"]):
            pass  # 可以添加更多智能推荐逻辑

        return joins

    def _estimate_tokens(
        self,
        tables: List[TableInfo],
        selected_columns: Dict[str, List[str]]
    ) -> int:
        """估算 Prompt token 数量"""
        total_chars = 0

        for table in tables:
            total_chars += len(table.name) + len(table.description)
            for col in table.columns:
                if table.full_name in selected_columns:
                    if col.name in selected_columns[table.full_name]:
                        total_chars += len(col.name) + len(col.type) + len(col.description) + 10

        # 粗略估算：1 token ≈ 4 字符（中文）或 0.25 token ≈ 1 字符
        return int(total_chars / 3)

    def invalidate_cache(self, database: str = None) -> None:
        """使缓存失效"""
        if database:
            keys_to_remove = [k for k in self._cache.keys() if k.startswith(f"{database}:")]
            for key in keys_to_remove:
                del self._cache[key]
        else:
            self._cache.clear()

    async def get_table_suggestions(
        self,
        partial_name: str,
        database: str = "sales_dw",
        limit: int = 10
    ) -> List[Dict[str, str]]:
        """
        获取表名建议（自动完成）

        Args:
            partial_name: 部分表名
            database: 数据库名称
            limit: 返回数量

        Returns:
            建议表列表
        """
        try:
            tables = await self.metadata.search_tables(
                keywords=partial_name,
                database=database,
                limit=limit
            )

            return [
                {
                    "name": t.get("table", ""),
                    "database": t.get("database", database),
                    "description": t.get("description", "")
                }
                for t in tables
            ]

        except Exception as e:
            logger.error(f"Failed to get table suggestions: {e}")
            return []

    async def get_column_suggestions(
        self,
        table: str,
        partial_column: str,
        database: str = "sales_dw",
        limit: int = 10
    ) -> List[Dict[str, str]]:
        """
        获取列名建议（自动完成）

        Args:
            table: 表名
            partial_column: 部分列名
            database: 数据库名称
            limit: 返回数量

        Returns:
            建议列列表
        """
        try:
            schema = await self.metadata.get_table_schema(
                database=database,
                table=table,
                include_sample_data=False
            )

            if not schema:
                return []

            columns = schema.get("columns", [])

            # 过滤匹配的列
            matched = [
                col for col in columns
                if partial_column.lower() in col.get("name", "").lower()
            ]

            return [
                {
                    "name": col.get("name", ""),
                    "type": col.get("type", ""),
                    "description": col.get("comment", "")
                }
                for col in matched[:limit]
            ]

        except Exception as e:
            logger.error(f"Failed to get column suggestions: {e}")
            return []


# 全局实例
_provider: Optional[SchemaProvider] = None


def get_schema_provider(**kwargs) -> SchemaProvider:
    """获取全局 Schema 提供器实例"""
    global _provider
    if _provider is None:
        _provider = SchemaProvider(**kwargs)
    return _provider


async def get_schema_for_sql(question: str, database: str = "sales_dw") -> str:
    """
    获取用于 Text-to-SQL 的 Schema 字符串（便捷函数）

    Args:
        question: 自然语言问题
        database: 数据库名称

    Returns:
        Schema 上下文字符串
    """
    provider = get_schema_provider()
    result = await provider.get_schema_for_question(question, database)
    return result.to_prompt_context()
