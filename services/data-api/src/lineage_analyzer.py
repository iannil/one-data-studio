"""
AI 增强数据血缘分析服务
Phase 1 P1: 智能血缘解析与影响分析

功能：
- SQL 语句血缘解析
- ETL 任务血缘推断
- AI 驱动的影响分析
- 列级血缘追踪
"""

import json
import logging
import os
import re
import requests
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Set
import uuid

logger = logging.getLogger(__name__)

# 配置
MODEL_API_URL = os.getenv("MODEL_API_URL") or os.getenv("CUBE_API_URL", "http://openai-proxy:8000")
AI_LINEAGE_MODEL = os.getenv("AI_LINEAGE_MODEL", "gpt-4o-mini")
AI_LINEAGE_ENABLED = os.getenv("AI_LINEAGE_ENABLED", "true").lower() in ("true", "1", "yes")

# SQL 关键字模式
SQL_KEYWORDS = {
    "select": r"\bSELECT\b",
    "from": r"\bFROM\b",
    "join": r"\b(?:LEFT|RIGHT|INNER|OUTER|CROSS|FULL)?\s*JOIN\b",
    "insert": r"\bINSERT\s+(?:INTO|OVERWRITE)\b",
    "create": r"\bCREATE\s+(?:TABLE|VIEW|MATERIALIZED\s+VIEW)\b",
    "with": r"\bWITH\b",
    "as": r"\bAS\b",
}

# 表名提取模式
TABLE_PATTERN = r'(?:FROM|JOIN|INTO|UPDATE|TABLE)\s+(?:`?(\w+)`?\.)?`?(\w+)`?'
# 列名提取模式（简化版）
COLUMN_PATTERN = r'(?:SELECT|SET|WHERE|ON|AND|OR|,)\s*(?:`?(\w+)`?\.)?`?(\w+)`?(?:\s+AS\s+`?(\w+)`?)?'


class LineageAnalyzer:
    """AI 增强血缘分析服务"""

    def __init__(self, api_url: str = None):
        """
        初始化服务

        Args:
            api_url: LLM API 地址
        """
        self.api_url = api_url or MODEL_API_URL
        self.model = AI_LINEAGE_MODEL
        self.enabled = AI_LINEAGE_ENABLED

    def parse_sql_lineage(
        self,
        sql: str,
        source_database: str = None,
        use_ai: bool = True,
    ) -> Dict[str, Any]:
        """
        解析 SQL 语句提取血缘关系

        Args:
            sql: SQL 语句
            source_database: 默认数据库名
            use_ai: 是否使用 AI 增强解析

        Returns:
            血缘解析结果
        """
        result = {
            "sql": sql,
            "source_tables": [],
            "target_table": None,
            "column_mappings": [],
            "lineage_edges": [],
            "confidence": 0,
            "parse_method": "rule",
            "errors": [],
        }

        # 1. 基于规则的解析
        try:
            rule_result = self._parse_sql_by_rules(sql, source_database)
            result.update(rule_result)
            result["confidence"] = 60
        except Exception as e:
            result["errors"].append(f"Rule parsing failed: {str(e)}")
            logger.warning(f"SQL 规则解析失败: {e}")

        # 2. AI 增强解析（如果启用）
        if use_ai and self.enabled:
            try:
                ai_result = self._parse_sql_with_ai(sql, source_database)
                if ai_result:
                    # 合并 AI 结果
                    result = self._merge_parse_results(result, ai_result)
                    result["parse_method"] = "ai_enhanced"
                    result["confidence"] = max(result["confidence"], ai_result.get("confidence", 85))
            except Exception as e:
                result["errors"].append(f"AI parsing failed: {str(e)}")
                logger.warning(f"SQL AI 解析失败: {e}")

        return result

    def _parse_sql_by_rules(
        self,
        sql: str,
        source_database: str = None,
    ) -> Dict[str, Any]:
        """基于规则解析 SQL"""
        result = {
            "source_tables": [],
            "target_table": None,
            "column_mappings": [],
            "lineage_edges": [],
        }

        sql_upper = sql.upper().strip()
        sql_clean = re.sub(r'--.*$', '', sql, flags=re.MULTILINE)  # 移除单行注释
        sql_clean = re.sub(r'/\*.*?\*/', '', sql_clean, flags=re.DOTALL)  # 移除多行注释

        # 提取表名
        table_matches = re.findall(TABLE_PATTERN, sql_clean, re.IGNORECASE)
        tables = set()
        for db_name, table_name in table_matches:
            if table_name.upper() not in ('SELECT', 'FROM', 'WHERE', 'AND', 'OR', 'ON', 'AS'):
                full_name = f"{db_name or source_database or 'default'}.{table_name}"
                tables.add(full_name)

        # 判断语句类型和目标表
        if sql_upper.startswith("INSERT") or sql_upper.startswith("CREATE"):
            # 提取目标表
            if "INTO" in sql_upper:
                into_match = re.search(r'INTO\s+(?:`?(\w+)`?\.)?`?(\w+)`?', sql_clean, re.IGNORECASE)
                if into_match:
                    db_name, table_name = into_match.groups()
                    result["target_table"] = f"{db_name or source_database or 'default'}.{table_name}"
                    tables.discard(result["target_table"])
            elif "TABLE" in sql_upper:
                table_match = re.search(r'TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(?:`?(\w+)`?\.)?`?(\w+)`?', sql_clean, re.IGNORECASE)
                if table_match:
                    db_name, table_name = table_match.groups()
                    result["target_table"] = f"{db_name or source_database or 'default'}.{table_name}"
                    tables.discard(result["target_table"])

        result["source_tables"] = list(tables)

        # 生成血缘边
        if result["target_table"] and result["source_tables"]:
            for source in result["source_tables"]:
                result["lineage_edges"].append({
                    "source": source,
                    "target": result["target_table"],
                    "relation_type": "derive",
                    "confidence": 60,
                })

        return result

    def _parse_sql_with_ai(
        self,
        sql: str,
        source_database: str = None,
    ) -> Optional[Dict[str, Any]]:
        """使用 AI 解析 SQL 血缘"""
        prompt = f"""分析以下 SQL 语句，提取数据血缘关系。返回 JSON 格式。

SQL:
```sql
{sql}
```

默认数据库: {source_database or 'default'}

请分析并返回：
1. source_tables: 源表列表（格式：database.table）
2. target_table: 目标表（如果是写入操作）
3. column_mappings: 列级映射关系，数组格式 [{{"source_column": "table.col", "target_column": "col", "transformation": "描述"}}]
4. relation_type: 关系类型（derive/transform/copy/aggregate）
5. confidence: 置信度 0-100

仅返回 JSON，不要其他文字："""

        try:
            response = requests.post(
                f"{self.api_url}/v1/chat/completions",
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": "你是数据血缘分析专家，擅长解析 SQL 语句并提取表和列之间的依赖关系。只返回 JSON 格式结果。"},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.1,
                    "max_tokens": 500,
                },
                timeout=15,
            )

            if response.status_code == 200:
                content = response.json()["choices"][0]["message"]["content"]
                # 提取 JSON
                json_match = re.search(r'\{[\s\S]*\}', content)
                if json_match:
                    return json.loads(json_match.group())
            else:
                logger.warning(f"AI API 返回错误: {response.status_code}")

        except json.JSONDecodeError as e:
            logger.warning(f"AI 返回解析失败: {e}")
        except requests.exceptions.RequestException as e:
            logger.warning(f"AI API 请求失败: {e}")
        except Exception as e:
            logger.warning(f"AI 解析异常: {e}")

        return None

    def _merge_parse_results(
        self,
        rule_result: Dict[str, Any],
        ai_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """合并规则解析和 AI 解析结果"""
        merged = rule_result.copy()

        # 合并源表
        ai_sources = ai_result.get("source_tables", [])
        if ai_sources:
            all_sources = set(rule_result.get("source_tables", []))
            all_sources.update(ai_sources)
            merged["source_tables"] = list(all_sources)

        # 使用 AI 的目标表（如果有）
        if ai_result.get("target_table"):
            merged["target_table"] = ai_result["target_table"]

        # 使用 AI 的列映射
        if ai_result.get("column_mappings"):
            merged["column_mappings"] = ai_result["column_mappings"]

        # 更新关系类型
        if ai_result.get("relation_type"):
            for edge in merged.get("lineage_edges", []):
                edge["relation_type"] = ai_result["relation_type"]

        return merged

    def analyze_etl_lineage(
        self,
        etl_config: Dict[str, Any],
        task_type: str = "batch",
    ) -> Dict[str, Any]:
        """
        分析 ETL 任务的血缘关系

        Args:
            etl_config: ETL 任务配置
            task_type: 任务类型

        Returns:
            血缘分析结果
        """
        result = {
            "source_nodes": [],
            "target_nodes": [],
            "lineage_edges": [],
            "confidence": 0,
        }

        # 提取源配置
        source_type = etl_config.get("source_type")
        source_config = etl_config.get("source_config", {})
        source_query = etl_config.get("source_query")

        # 提取目标配置
        target_type = etl_config.get("target_type")
        target_config = etl_config.get("target_config", {})
        target_table = etl_config.get("target_table")

        # 解析源
        if source_query:
            # 如果有 SQL 查询，解析 SQL 获取源表
            sql_result = self.parse_sql_lineage(source_query)
            for table in sql_result.get("source_tables", []):
                result["source_nodes"].append({
                    "node_type": "table",
                    "full_name": table,
                    "database_name": table.split(".")[0] if "." in table else None,
                    "table_name": table.split(".")[-1],
                })
            result["confidence"] = sql_result.get("confidence", 60)
        elif source_config:
            # 从配置中提取源信息
            if source_type in ("mysql", "postgresql", "oracle", "sqlserver"):
                source_db = source_config.get("database", "default")
                source_table = source_config.get("table")
                if source_table:
                    result["source_nodes"].append({
                        "node_type": "table",
                        "full_name": f"{source_db}.{source_table}",
                        "database_name": source_db,
                        "table_name": source_table,
                    })
                    result["confidence"] = 80

        # 解析目标
        if target_table:
            target_db = target_config.get("database", "default")
            result["target_nodes"].append({
                "node_type": "table",
                "full_name": f"{target_db}.{target_table}",
                "database_name": target_db,
                "table_name": target_table,
            })

        # 生成血缘边
        for source in result["source_nodes"]:
            for target in result["target_nodes"]:
                result["lineage_edges"].append({
                    "source": source["full_name"],
                    "source_type": source["node_type"],
                    "target": target["full_name"],
                    "target_type": target["node_type"],
                    "relation_type": "transform",
                    "job_type": "etl",
                    "confidence": result["confidence"],
                })

        return result

    def ai_impact_analysis(
        self,
        node_info: Dict[str, Any],
        downstream_nodes: List[Dict[str, Any]],
        change_type: str = "schema_change",
    ) -> Dict[str, Any]:
        """
        AI 驱动的影响分析

        Args:
            node_info: 源节点信息
            downstream_nodes: 下游节点列表
            change_type: 变更类型

        Returns:
            影响分析报告
        """
        result = {
            "source_node": node_info,
            "change_type": change_type,
            "impact_summary": None,
            "risk_level": "low",
            "recommendations": [],
            "affected_nodes": [],
        }

        if not downstream_nodes:
            result["impact_summary"] = "无下游依赖，变更影响范围有限"
            return result

        # 基本影响统计
        result["affected_nodes"] = [
            {
                "node": n,
                "impact_level": n.get("impact_level", 1),
            }
            for n in downstream_nodes
        ]

        # 计算风险等级
        total_affected = len(downstream_nodes)
        max_depth = max((n.get("impact_level", 1) for n in downstream_nodes), default=1)

        if total_affected > 10 or max_depth > 3:
            result["risk_level"] = "high"
        elif total_affected > 5 or max_depth > 2:
            result["risk_level"] = "medium"
        else:
            result["risk_level"] = "low"

        # 使用 AI 生成详细分析（如果启用）
        if self.enabled:
            try:
                ai_analysis = self._get_ai_impact_analysis(
                    node_info, downstream_nodes, change_type
                )
                if ai_analysis:
                    result["impact_summary"] = ai_analysis.get("summary")
                    result["recommendations"] = ai_analysis.get("recommendations", [])
                    if ai_analysis.get("risk_level"):
                        result["risk_level"] = ai_analysis["risk_level"]
            except Exception as e:
                logger.warning(f"AI 影响分析失败: {e}")

        # 如果没有 AI 分析，生成基本摘要
        if not result["impact_summary"]:
            result["impact_summary"] = self._generate_basic_impact_summary(
                node_info, downstream_nodes, change_type
            )

        return result

    def _get_ai_impact_analysis(
        self,
        node_info: Dict[str, Any],
        downstream_nodes: List[Dict[str, Any]],
        change_type: str,
    ) -> Optional[Dict[str, Any]]:
        """使用 AI 进行影响分析"""
        # 构建上下文
        node_desc = f"{node_info.get('node_type', 'unknown')}: {node_info.get('full_name', node_info.get('name', 'unknown'))}"
        downstream_desc = "\n".join([
            f"- {n.get('full_name', n.get('name', 'unknown'))} (类型: {n.get('node_type', 'unknown')}, 层级: {n.get('impact_level', 1)})"
            for n in downstream_nodes[:20]  # 限制数量
        ])

        if len(downstream_nodes) > 20:
            downstream_desc += f"\n... 还有 {len(downstream_nodes) - 20} 个下游节点"

        prompt = f"""分析以下数据血缘变更的影响：

源节点: {node_desc}
变更类型: {change_type}

下游依赖节点:
{downstream_desc}

请分析并返回 JSON 格式：
1. summary: 影响摘要（50字以内）
2. risk_level: 风险等级（low/medium/high/critical）
3. recommendations: 建议措施数组（最多3条）
4. key_impacts: 关键影响点数组

仅返回 JSON："""

        try:
            response = requests.post(
                f"{self.api_url}/v1/chat/completions",
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": "你是数据治理专家，擅长分析数据变更的影响范围。返回简洁的 JSON 格式分析结果。"},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.2,
                    "max_tokens": 300,
                },
                timeout=10,
            )

            if response.status_code == 200:
                content = response.json()["choices"][0]["message"]["content"]
                json_match = re.search(r'\{[\s\S]*\}', content)
                if json_match:
                    return json.loads(json_match.group())

        except Exception as e:
            logger.warning(f"AI 影响分析请求失败: {e}")

        return None

    def _generate_basic_impact_summary(
        self,
        node_info: Dict[str, Any],
        downstream_nodes: List[Dict[str, Any]],
        change_type: str,
    ) -> str:
        """生成基本的影响摘要"""
        total = len(downstream_nodes)
        node_name = node_info.get("full_name", node_info.get("name", "未知节点"))

        change_desc = {
            "schema_change": "结构变更",
            "data_change": "数据变更",
            "deletion": "删除操作",
            "rename": "重命名",
        }.get(change_type, change_type)

        return f"{node_name} 的{change_desc}将影响 {total} 个下游节点"

    def infer_column_lineage(
        self,
        sql: str,
        source_columns: Dict[str, List[str]],
        use_ai: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        推断列级血缘关系

        Args:
            sql: SQL 语句
            source_columns: 源表列信息 {\"table_name\": [\"col1\", \"col2\", ...]}
            use_ai: 是否使用 AI

        Returns:
            列级映射列表
        """
        mappings = []

        # 使用 AI 进行列级血缘推断
        if use_ai and self.enabled and source_columns:
            try:
                columns_desc = "\n".join([
                    f"表 {table}: {', '.join(cols)}"
                    for table, cols in source_columns.items()
                ])

                prompt = f"""分析以下 SQL 的列级血缘关系：

SQL:
```sql
{sql}
```

源表列信息:
{columns_desc}

请返回列级映射关系的 JSON 数组，每个元素格式：
{{"source_table": "表名", "source_column": "列名", "target_column": "目标列名", "transformation": "转换描述"}}

仅返回 JSON 数组："""

                response = requests.post(
                    f"{self.api_url}/v1/chat/completions",
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": "你是 SQL 分析专家，擅长分析列级数据流向。返回 JSON 数组格式。"},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.1,
                        "max_tokens": 500,
                    },
                    timeout=15,
                )

                if response.status_code == 200:
                    content = response.json()["choices"][0]["message"]["content"]
                    json_match = re.search(r'\[[\s\S]*\]', content)
                    if json_match:
                        mappings = json.loads(json_match.group())

            except Exception as e:
                logger.warning(f"列级血缘推断失败: {e}")

        return mappings

    def generate_lineage_nodes_and_edges(
        self,
        parse_result: Dict[str, Any],
        job_id: str = None,
        job_type: str = "sql",
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        从解析结果生成血缘节点和边

        Args:
            parse_result: SQL 解析结果
            job_id: 关联的任务 ID
            job_type: 任务类型

        Returns:
            (nodes, edges) 元组
        """
        nodes = []
        edges = []
        node_ids = {}

        def get_or_create_node(full_name: str, node_type: str = "table") -> str:
            """获取或创建节点 ID"""
            if full_name in node_ids:
                return node_ids[full_name]

            node_id = f"ln_{uuid.uuid4().hex[:12]}"
            node_ids[full_name] = node_id

            parts = full_name.split(".")
            nodes.append({
                "node_id": node_id,
                "node_type": node_type,
                "name": parts[-1],
                "full_name": full_name,
                "database_name": parts[0] if len(parts) > 1 else "default",
                "table_name": parts[-1],
                "column_name": parts[2] if len(parts) > 2 else None,
                "is_active": True,
            })

            return node_id

        # 创建源节点
        for source_table in parse_result.get("source_tables", []):
            get_or_create_node(source_table, "table")

        # 创建目标节点
        target_table = parse_result.get("target_table")
        if target_table:
            get_or_create_node(target_table, "table")

            # 创建边
            for source_table in parse_result.get("source_tables", []):
                source_node_id = node_ids.get(source_table)
                target_node_id = node_ids.get(target_table)

                if source_node_id and target_node_id:
                    edges.append({
                        "edge_id": f"le_{uuid.uuid4().hex[:12]}",
                        "source_node_id": source_node_id,
                        "source_type": "table",
                        "source_name": source_table,
                        "target_node_id": target_node_id,
                        "target_type": "table",
                        "target_name": target_table,
                        "relation_type": parse_result.get("relation_type", "derive"),
                        "transformation": parse_result.get("sql", ""),
                        "job_id": job_id,
                        "job_type": job_type,
                        "confidence": parse_result.get("confidence", 60),
                        "is_active": True,
                    })

        # 处理列级映射
        for mapping in parse_result.get("column_mappings", []):
            source_col = mapping.get("source_column")
            target_col = mapping.get("target_column")

            if source_col and target_col and target_table:
                source_full = f"{source_col}" if "." in source_col else f"unknown.{source_col}"
                target_full = f"{target_table}.{target_col}"

                source_node_id = get_or_create_node(source_full, "column")
                target_node_id = get_or_create_node(target_full, "column")

                edges.append({
                    "edge_id": f"le_{uuid.uuid4().hex[:12]}",
                    "source_node_id": source_node_id,
                    "source_type": "column",
                    "source_name": source_full,
                    "target_node_id": target_node_id,
                    "target_type": "column",
                    "target_name": target_full,
                    "relation_type": "derive",
                    "transformation": mapping.get("transformation", ""),
                    "job_id": job_id,
                    "job_type": job_type,
                    "confidence": parse_result.get("confidence", 60),
                    "is_active": True,
                })

        return nodes, edges


# 创建全局实例
_lineage_analyzer: Optional[LineageAnalyzer] = None


def get_lineage_analyzer() -> LineageAnalyzer:
    """获取血缘分析服务单例"""
    global _lineage_analyzer
    if _lineage_analyzer is None:
        _lineage_analyzer = LineageAnalyzer()
    return _lineage_analyzer
