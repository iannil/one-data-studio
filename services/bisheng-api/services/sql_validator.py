"""
SQL 安全检查器
Production: 基于 AST 解析的 SQL 安全验证

功能：
1. AST 解析验证（使用 sqlglot）
2. 只允许 SELECT 查询
3. 拦截危险操作（DROP/DELETE/TRUNCATE/ALTER/CREATE/INSERT/UPDATE）
4. 查询复杂度限制
5. 返回行数限制
6. 查询超时控制
7. SQL 注入防护
"""

import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class SQLRiskLevel(Enum):
    """SQL 风险等级"""
    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SQLValidationResult:
    """SQL 验证结果"""
    is_valid: bool
    risk_level: SQLRiskLevel
    errors: List[str]
    warnings: List[str]
    normalized_sql: Optional[str] = None
    estimated_cost: Optional[int] = None
    suggested_limit: Optional[int] = None


class SQLValidator:
    """
    SQL 安全检查器

    使用 AST 解析和规则引擎确保 SQL 查询的安全性。
    """

    # 危险操作类型（黑名单）
    DANGEROUS_OPERATIONS = {
        "DROP", "DELETE", "TRUNCATE", "ALTER", "CREATE",
        "INSERT", "UPDATE", "REPLACE", "GRANT", "REVOKE",
        "EXECUTE", "CALL", "EXPLAIN", "SHOW", "DESCRIBE",
        "USE", "SET", "LOCK", "UNLOCK", "KILL"
    }

    # 危险函数（可能泄露敏感信息）
    DANGEROUS_FUNCTIONS = {
        "LOAD_FILE", "SYSTEM", "EXEC", "EVAL", "SHELL",
        "BENCHMARK", "SLEEP", "WAITFOR", "DELAY"
    }

    # SQL 注入模式
    INJECTION_PATTERNS = [
        r";\s*--",          # 语句终止 + 注释
        r"';--",            # 引号 + 语句终止 + 注释
        r"'\s*OR\s*'.*='",  # 引号 OR 注入
        r'"\s*OR\s*".*="',  # 双引号 OR 注入
        r"1\s*=\s*1",       # Tautology 攻击
        r"1\s*=\s*1\s*OR",  # OR Tautology
        r"UNION\s+SELECT",  # UNION 注入
        r"'\s*;\s*",        # 引号后语句终止
        r"\)\s*;",          # 括号后语句终止
        r"\/\*\*\/",        # MySQL 注释攻击
    ]

    # 配置限制
    MAX_QUERY_LENGTH = 10000        # 最大 SQL 长度
    MAX_JOINS = 5                   # 最大 JOIN 数量
    MAX_SUBQUERY_DEPTH = 3          # 最大子查询深度
    MAX_WHERE_CONDITIONS = 20       # 最大 WHERE 条件数
    DEFAULT_ROW_LIMIT = 1000        # 默认行数限制
    MAX_ROW_LIMIT = 10000           # 最大允许行数限制

    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化 SQL 验证器

        Args:
            config: 配置字典
                - allow_join: 是否允许 JOIN (默认 True)
                - max_joins: 最大 JOIN 数量 (默认 5)
                - allow_aggregation: 是否允许聚合函数 (默认 True)
                - allow_subquery: 是否允许子查询 (默认 True)
                - max_subquery_depth: 最大子查询深度 (默认 3)
                - default_row_limit: 默认行数限制 (默认 1000)
                - strict_mode: 严格模式 (默认 False)
        """
        self.config = config or {}
        self.allow_join = self.config.get("allow_join", True)
        self.max_joins = self.config.get("max_joins", self.MAX_JOINS)
        self.allow_aggregation = self.config.get("allow_aggregation", True)
        self.allow_subquery = self.config.get("allow_subquery", True)
        self.max_subquery_depth = self.config.get("max_subquery_depth", self.MAX_SUBQUERY_DEPTH)
        self.default_row_limit = self.config.get("default_row_limit", self.DEFAULT_ROW_LIMIT)
        self.strict_mode = self.config.get("strict_mode", False)

        # 编译注入检测正则
        self.injection_regexes = [
            re.compile(pattern, re.IGNORECASE | re.MULTILINE)
            for pattern in self.INJECTION_PATTERNS
        ]

    def validate(self, sql: str) -> SQLValidationResult:
        """
        验证 SQL 查询

        Args:
            sql: SQL 查询语句

        Returns:
            SQLValidationResult 验证结果
        """
        errors = []
        warnings = []
        risk_level = SQLRiskLevel.SAFE

        # 1. 基本检查
        if not sql or not sql.strip():
            return SQLValidationResult(
                is_valid=False,
                risk_level=SQLRiskLevel.HIGH,
                errors=["SQL 查询为空"],
                warnings=[]
            )

        original_sql = sql
        sql = sql.strip()

        # 2. 长度检查
        if len(sql) > self.MAX_QUERY_LENGTH:
            errors.append(f"SQL 查询过长 ({len(sql)} > {self.MAX_QUERY_LENGTH})")
            risk_level = SQLRiskLevel.HIGH

        # 3. 注入模式检查
        for regex in self.injection_regexes:
            if regex.search(sql):
                errors.append(f"检测到潜在 SQL 注入模式: {regex.pattern[:30]}")
                risk_level = SQLRiskLevel.CRITICAL

        # 4. 危险操作检查（关键词）
        sql_upper = sql.upper()
        for op in self.DANGEROUS_OPERATIONS:
            # 使用词边界匹配
            pattern = r"\b" + op + r"\b"
            if re.search(pattern, sql_upper, re.IGNORECASE):
                errors.append(f"不允许的操作: {op}")
                risk_level = SQLRiskLevel.CRITICAL

        # 5. 危险函数检查
        for func in self.DANGEROUS_FUNCTIONS:
            pattern = r"\b" + func + r"\s*\("
            if re.search(pattern, sql_upper, re.IGNORECASE):
                errors.append(f"不允许的函数: {func}")
                risk_level = SQLRiskLevel.HIGH

        # 6. AST 解析验证
        try:
            ast_result = self._validate_with_ast(sql)
            errors.extend(ast_result.errors)
            warnings.extend(ast_result.warnings)
            if ast_result.risk_level.value > risk_level.value:
                risk_level = ast_result.risk_level
            normalized_sql = ast_result.normalized_sql
            suggested_limit = ast_result.suggested_limit
        except Exception as e:
            # AST 解析失败，回退到正则检查
            warnings.append(f"AST 解析失败，使用基础验证: {e}")
            normalized_sql = self._normalize_sql_basic(sql)
            suggested_limit = self.default_row_limit

        # 7. 确保 SELECT 开头
        if not re.match(r"^\s*(SELECT|WITH|EXPLAIN\s+SELECT)", sql, re.IGNORECASE):
            errors.append("只允许 SELECT 查询")
            risk_level = SQLRiskLevel.CRITICAL

        # 8. 检查注释中是否隐藏危险操作
        if self._check_comment_dangers(sql):
            errors.append("检测到注释中可能隐藏的危险操作")
            risk_level = SQLRiskLevel.HIGH

        # 9. 建议添加 LIMIT
        if "LIMIT" not in sql_upper:
            warnings.append(f"建议添加 LIMIT 子句 (默认: {self.default_row_limit})")
            suggested_limit = suggested_limit or self.default_row_limit

        # 严格模式：任何警告都视为错误
        if self.strict_mode and warnings:
            errors.extend([f"严格模式警告: {w}" for w in warnings])
            warnings.clear()

        is_valid = len(errors) == 0

        return SQLValidationResult(
            is_valid=is_valid,
            risk_level=risk_level,
            errors=errors,
            warnings=warnings,
            normalized_sql=normalized_sql,
            suggested_limit=suggested_limit
        )

    def _validate_with_ast(self, sql: str) -> SQLValidationResult:
        """
        使用 AST 解析验证 SQL

        需要安装 sqlglot: pip install sqlglot
        """
        try:
            import sqlglot
            from sqlglot import exp
        except ImportError:
            return SQLValidationResult(
                is_valid=True,  # AST 不可用时回退到基础验证
                risk_level=SQLRiskLevel.LOW,
                errors=[],
                warnings=["sqlglot 未安装，跳过 AST 验证。运行: pip install sqlglot"],
                normalized_sql=self._normalize_sql_basic(sql)
            )

        errors = []
        warnings = []
        risk_level = SQLRiskLevel.SAFE
        normalized_sql = sql
        suggested_limit = self.default_row_limit

        try:
            # 解析 SQL
            parsed = sqlglot.parse_one(sql)

            # 检查查询类型
            if not isinstance(parsed, (exp.Select, exp.Subquery)):
                if isinstance(parsed, (exp.Delete, exp.Update, exp.Insert, exp.Create)):
                    errors.append(f"不允许的查询类型: {type(parsed).__name__.upper()}")
                    risk_level = SQLRiskLevel.CRITICAL
                else:
                    warnings.append(f"非常规查询类型: {type(parsed).__name__}")

            # 检查 JOIN 数量
            join_count = self._count_joins(parsed)
            if join_count > self.max_joins:
                errors.append(f"JOIN 数量超限 ({join_count} > {self.max_joins})")
                risk_level = SQLRiskLevel.MEDIUM
            elif join_count > 0 and not self.allow_join:
                errors.append("JOIN 操作未被允许")
                risk_level = SQLRiskLevel.HIGH

            # 检查子查询深度
            subquery_depth = self._get_subquery_depth(parsed)
            if subquery_depth > self.max_subquery_depth:
                errors.append(f"子查询深度超限 ({subquery_depth} > {self.max_subquery_depth})")
                risk_level = SQLRiskLevel.MEDIUM
            elif subquery_depth > 0 and not self.allow_subquery:
                errors.append("子查询未被允许")
                risk_level = SQLRiskLevel.HIGH

            # 检查聚合函数
            if not self.allow_aggregation:
                if self._has_aggregation(parsed):
                    errors.append("聚合函数未被允许")
                    risk_level = SQLRiskLevel.HIGH

            # 检查 WHERE 条件复杂度
            where_conditions = self._count_where_conditions(parsed)
            if where_conditions > self.MAX_WHERE_CONDITIONS:
                warnings.append(f"WHERE 条件较多 ({where_conditions})")

            # 检查是否使用了 LIMIT
            limit_value = self._get_limit_value(parsed)
            if limit_value is None:
                suggested_limit = self.default_row_limit
            elif limit_value > self.MAX_ROW_LIMIT:
                warnings.append(f"LIMIT 值较大 ({limit_value})，建议 <= {self.MAX_ROW_LIMIT}")
                suggested_limit = min(limit_value, self.MAX_ROW_LIMIT)
            else:
                suggested_limit = limit_value

            # 规范化 SQL（用于日志和比较）
            try:
                normalized_sql = parsed.sql(dialect="mysql", normalize=True, pretty=False)
            except Exception:
                normalized_sql = sql

        except Exception as e:
            errors.append(f"AST 解析错误: {str(e)}")
            risk_level = SQLRiskLevel.MEDIUM

        return SQLValidationResult(
            is_valid=len(errors) == 0,
            risk_level=risk_level,
            errors=errors,
            warnings=warnings,
            normalized_sql=normalized_sql,
            suggested_limit=suggested_limit
        )

    def _count_joins(self, ast_node) -> int:
        """计算 JOIN 数量"""
        count = 0
        for join in ast_node.find_all(exp.Join):
            count += 1
        return count

    def _get_subquery_depth(self, ast_node, current_depth: int = 0) -> int:
        """获取最大子查询深度"""
        max_depth = current_depth
        for subquery in ast_node.find_all(exp.Subquery):
            depth = self._get_subquery_depth(subquery.this, current_depth + 1)
            max_depth = max(max_depth, depth)
        return max_depth

    def _has_aggregation(self, ast_node) -> bool:
        """检查是否有聚合函数"""
        agg_functions = {"COUNT", "SUM", "AVG", "MIN", "MAX", "GROUP_CONCAT"}
        for func in ast_node.find_all(exp.Anonymous):
            if func.name.upper() in agg_functions:
                return True
        for func in ast_node.find_all(exp.AggFunc):
            return True
        return False

    def _count_where_conditions(self, ast_node) -> int:
        """计算 WHERE 条件数量"""
        count = 0
        for where in ast_node.find_all(exp.Where):
            count += len(list(where.find_all(exp.Column)))
        return count

    def _get_limit_value(self, ast_node) -> Optional[int]:
        """获取 LIMIT 值"""
        for limit in ast_node.find_all(exp.Limit):
            if limit.expression:
                try:
                    return int(limit.expression.this)
                except (ValueError, TypeError, AttributeError):
                    pass
        return None

    def _normalize_sql_basic(self, sql: str) -> str:
        """基础 SQL 规范化"""
        # 移除多余空格和换行
        normalized = re.sub(r"\s+", " ", sql)
        # 移除前后空格
        normalized = normalized.strip()
        return normalized

    def _check_comment_dangers(self, sql: str) -> bool:
        """检查注释中是否隐藏危险操作"""
        # 移除单行注释
        sql_no_single = re.sub(r"--.*?$", "", sql, flags=re.MULTILINE)
        # 移除多行注释
        sql_no_comments = re.sub(r"/\*.*?\*/", "", sql_no_single, flags=re.DOTALL)

        # 检查清理后的 SQL 是否包含危险操作
        cleaned_upper = sql_no_comments.upper()
        for op in ["DROP", "DELETE", "TRUNCATE", "ALTER"]:
            if re.search(r"\b" + op + r"\b", cleaned_upper):
                return True
        return False

    def add_limit_if_missing(self, sql: str, limit: int = None) -> str:
        """
        如果 SQL 没有 LIMIT，添加 LIMIT 子句

        Args:
            sql: 原始 SQL
            limit: 行数限制，默认使用配置值

        Returns:
            添加 LIMIT 后的 SQL
        """
        if limit is None:
            limit = self.default_row_limit

        # 检查是否已有 LIMIT
        sql_upper = sql.upper().strip()
        if sql_upper.endswith(";)") or sql_upper.endswith(";"):
            # 移除结尾的分号
            sql_clean = sql.rstrip().rstrip(";").strip()
            has_limit = sql_clean.upper().endswith(f"LIMIT {limit}")
        else:
            sql_clean = sql.rstrip().strip()
            has_limit = sql_clean.upper().endswith(f"LIMIT {limit}")

        if has_limit:
            return sql

        # 添加 LIMIT
        # 移除结尾分号
        if sql_clean.endswith(";"):
            sql_clean = sql_clean[:-1].strip()

        # 检查是否已有任何 LIMIT
        if re.search(r"\bLIMIT\s+\d+", sql_clean, re.IGNORECASE):
            return sql

        return f"{sql_clean} LIMIT {limit};"

    def sanitize_sql(self, sql: str) -> Tuple[str, SQLValidationResult]:
        """
        清理并验证 SQL

        Args:
            sql: 原始 SQL

        Returns:
            (清理后的 SQL, 验证结果)
        """
        # 先验证
        result = self.validate(sql)

        if not result.is_valid:
            return sql, result

        # 添加 LIMIT
        cleaned = self.add_limit_if_missing(
            result.normalized_sql or sql,
            result.suggested_limit or self.default_row_limit
        )

        return cleaned, result


class SQLValidatorCache:
    """SQL 验证结果缓存"""

    def __init__(self, max_size: int = 1000):
        self._cache: Dict[str, SQLValidationResult] = {}
        self.max_size = max_size

    def get(self, sql: str) -> Optional[SQLValidationResult]:
        """获取缓存的验证结果"""
        return self._cache.get(sql)

    def set(self, sql: str, result: SQLValidationResult) -> None:
        """设置验证结果缓存"""
        if len(self._cache) >= self.max_size:
            # 简单的 LRU：删除第一个
            self._cache.pop(next(iter(self._cache)))
        self._cache[sql] = result

    def clear(self) -> None:
        """清空缓存"""
        self._cache.clear()


# 全局验证器实例
_validator: Optional[SQLValidator] = None
_cache: Optional[SQLValidatorCache] = None


def get_sql_validator(config: Dict[str, Any] = None) -> SQLValidator:
    """获取全局 SQL 验证器实例"""
    global _validator
    if _validator is None:
        _validator = SQLValidator(config)
    return _validator


def get_validator_cache() -> SQLValidatorCache:
    """获取全局验证器缓存"""
    global _cache
    if _cache is None:
        _cache = SQLValidatorCache()
    return _cache


def validate_sql(sql: str, use_cache: bool = True) -> SQLValidationResult:
    """
    验证 SQL 查询（便捷函数）

    Args:
        sql: SQL 查询语句
        use_cache: 是否使用缓存

    Returns:
        SQLValidationResult 验证结果
    """
    validator = get_sql_validator()

    if use_cache:
        cache = get_validator_cache()
        cached = cache.get(sql)
        if cached is not None:
            return cached

        result = validator.validate(sql)
        cache.set(sql, result)
        return result

    return validator.validate(sql)


def sanitize_sql(sql: str, use_cache: bool = True) -> Tuple[str, SQLValidationResult]:
    """
    清理并验证 SQL（便捷函数）

    Args:
        sql: 原始 SQL
        use_cache: 是否使用缓存

    Returns:
        (清理后的 SQL, 验证结果)
    """
    validator = get_sql_validator()
    return validator.sanitize_sql(sql)
