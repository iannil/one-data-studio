"""
AI 字段转换智能映射服务
支持源表到目标表的智能字段映射推荐
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from models.metadata import MetadataTable, MetadataColumn
from models.quality import QualityRule

logger = logging.getLogger(__name__)


class FieldMappingSuggestion:
    """字段映射建议"""

    def __init__(
        self,
        source_field: str,
        target_field: str,
        confidence: float,
        mapping_type: str,
        transformation: str = "",
        data_type_conversion: Dict = None,
        quality_score: float = 0.0
    ):
        self.source_field = source_field
        self.target_field = target_field
        self.confidence = confidence
        self.mapping_type = mapping_type  # exact, fuzzy, semantic, derived
        self.transformation = transformation
        self.data_type_conversion = data_type_conversion or {}
        self.quality_score = quality_score

    def to_dict(self) -> Dict:
        return {
            "source_field": self.source_field,
            "target_field": self.target_field,
            "confidence": self.confidence,
            "mapping_type": self.mapping_type,
            "transformation": self.transformation,
            "data_type_conversion": self.data_type_conversion,
            "quality_score": self.quality_score,
        }


class AIFieldMappingService:
    """AI 字段映射服务"""

    def __init__(self):
        self._type_mapping_rules = self._init_type_mapping_rules()
        self._name_similarity_threshold = 0.6
        self._semantic_mapping_rules = self._init_semantic_rules()

    def _init_type_mapping_rules(self) -> Dict[str, List[Dict]]:
        """初始化数据类型映射规则"""
        return {
            # 字符串类型映射
            "string": [
                {"target_types": ["varchar", "text", "char"], "conversion": "direct", "cost": 0},
                {"target_types": ["int", "bigint"], "conversion": "cast_numeric", "cost": 1},
                {"target_types": ["decimal", "numeric"], "conversion": "cast_decimal", "cost": 1},
                {"target_types": ["date", "datetime"], "conversion": "parse_date", "cost": 2},
                {"target_types": ["boolean"], "conversion": "cast_boolean", "cost": 1},
            ],
            # 整数类型映射
            "integer": [
                {"target_types": ["bigint", "smallint"], "conversion": "resize", "cost": 0},
                {"target_types": ["varchar", "text"], "conversion": "to_string", "cost": 0},
                {"target_types": ["decimal", "numeric"], "conversion": "to_decimal", "cost": 1},
                {"target_types": ["float", "double"], "conversion": "to_float", "cost": 1},
            ],
            # 小数类型映射
            "decimal": [
                {"target_types": ["float", "double"], "conversion": "to_float", "cost": 1},
                {"target_types": ["varchar", "text"], "conversion": "to_string", "cost": 1},
                {"target_types": ["int", "bigint"], "conversion": "truncate", "cost": 2},
            ],
            # 日期类型映射
            "date": [
                {"target_types": ["datetime", "timestamp"], "conversion": "to_timestamp", "cost": 0},
                {"target_types": ["varchar", "text"], "conversion": "format_string", "cost": 1},
                {"target_types": ["int", "bigint"], "conversion": "to_unix_timestamp", "cost": 2},
            ],
            # 布尔类型映射
            "boolean": [
                {"target_types": ["int", "smallint"], "conversion": "to_int", "cost": 0},
                {"target_types": ["varchar", "text"], "conversion": "to_yes_no", "cost": 0},
            ],
            # 二进制/大对象
            "binary": [
                {"target_types": ["varchar", "text"], "conversion": "encode_base64", "cost": 2},
                {"target_types": ["blob"], "conversion": "direct", "cost": 0},
            ],
        }

    def _init_semantic_rules(self) -> List[Dict]:
        """初始化语义映射规则"""
        return [
            # 用户相关字段
            {
                "patterns": ["user_id", "userid", "uid", "user"],
                "target_patterns": ["user_id", "userid", "uid", "user"],
                "confidence": 0.95,
            },
            {
                "patterns": ["username", "user_name", "uname"],
                "target_patterns": ["username", "user_name", "name"],
                "confidence": 0.9,
            },
            # 时间相关字段
            {
                "patterns": ["created_at", "create_time", "ctime", "created"],
                "target_patterns": ["created_at", "create_time", "ctime"],
                "confidence": 0.95,
            },
            {
                "patterns": ["updated_at", "update_time", "utime", "modified", "updated"],
                "target_patterns": ["updated_at", "update_time", "utime", "modified"],
                "confidence": 0.95,
            },
            # 状态字段
            {
                "patterns": ["status", "state", "stat"],
                "target_patterns": ["status", "state", "stat"],
                "confidence": 0.85,
            },
            {
                "patterns": ["is_active", "active", "enabled"],
                "target_patterns": ["is_active", "active", "enabled"],
                "confidence": 0.9,
            },
            # ID相关
            {
                "patterns": ["id", "_id"],
                "target_patterns": ["id", "_id"],
                "confidence": 0.8,
            },
            # 描述字段
            {
                "patterns": ["desc", "description", "remark", "comment"],
                "target_patterns": ["desc", "description", "remark", "comment"],
                "confidence": 0.9,
            },
            # 邮箱相关
            {
                "patterns": ["email", "mail", "email_address"],
                "target_patterns": ["email", "mail", "email_address"],
                "confidence": 0.95,
            },
            # 手机号相关
            {
                "patterns": ["phone", "mobile", "tel", "contact"],
                "target_patterns": ["phone", "mobile", "tel", "contact"],
                "confidence": 0.9,
            },
        ]

    def suggest_field_mappings(
        self,
        db: Session,
        source_table: str,
        source_database: Optional[str],
        target_table: str,
        target_database: Optional[str] = None,
        options: Optional[Dict] = None
    ) -> Dict:
        """
        智能推荐源表到目标表的字段映射

        Args:
            db: 数据库会话
            source_table: 源表名
            source_database: 源数据库名（可选）
            target_table: 目标表名
            target_database: 目标数据库名（可选）
            options: 额外配置

        Returns:
            映射建议结果
        """
        options = options or {}

        # 获取源表和目标表的列信息
        source_columns = self._get_table_columns(db, source_table, source_database)
        target_columns = self._get_table_columns(db, target_table, target_database)

        if not source_columns:
            return {"error": f"源表 {source_table} 不存在或无列信息"}
        if not target_columns:
            return {"error": f"目标表 {target_table} 不存在或无列信息"}

        # 生成映射建议
        suggestions = []

        # 1. 完全匹配（字段名完全相同）
        exact_matches = self._find_exact_matches(source_columns, target_columns)
        suggestions.extend(exact_matches)

        # 2. 模糊匹配（字段名相似）
        fuzzy_matches = self._find_fuzzy_matches(
            source_columns,
            target_columns,
            exclude_matched=[s.source_field for s in exact_matches]
        )
        suggestions.extend(fuzzy_matches)

        # 3. 语义匹配（基于语义规则）
        semantic_matches = self._find_semantic_matches(
            source_columns,
            target_columns,
            exclude_matched=[s.source_field for s in exact_matches + fuzzy_matches]
        )
        suggestions.extend(semantic_matches)

        # 4. 类型推断匹配（基于数据类型和位置）
        inferred_matches = self._infer_type_based_matches(
            source_columns,
            target_columns,
            exclude_mapped=[s.source_field for s in exact_matches + fuzzy_matches + semantic_matches]
        )
        suggestions.extend(inferred_matches)

        # 计算映射质量得分
        for suggestion in suggestions:
            suggestion.quality_score = self._calculate_mapping_quality(
                suggestion,
                source_columns,
                target_columns
            )

        # 按置信度和质量得分排序
        suggestions.sort(key=lambda s: (s.confidence, s.quality_score), reverse=True)

        # 生成映射报告
        return self._generate_mapping_report(
            source_table,
            target_table,
            source_columns,
            target_columns,
            suggestions
        )

    def suggest_data_type_conversions(
        self,
        mappings: List[Dict],
        source_schema: List[Dict],
        target_schema: List[Dict]
    ) -> List[Dict]:
        """
        推荐数据类型转换策略

        Args:
            mappings: 字段映射列表
            source_schema: 源表结构
            target_schema: 目标表结构

        Returns:
            包含转换建议的映射列表
        """
        enhanced_mappings = []

        for mapping in mappings:
            source_field = next((f for f in source_schema if f["name"] == mapping["source_field"]), None)
            target_field = next((f for f in target_schema if f["name"] == mapping["target_field"]), None)

            if not source_field or not target_field:
                enhanced_mappings.append(mapping)
                continue

            source_type = source_field.get("type", "varchar").lower()
            target_type = target_field.get("type", "varchar").lower()

            # 获取类型转换建议
            conversion = self._get_type_conversion(source_type, target_type)

            enhanced_mapping = {
                **mapping,
                "data_type_conversion": conversion,
                "requires_casting": conversion["conversion"] != "direct",
                "conversion_risk": self._assess_conversion_risk(source_type, target_type),
            }

            enhanced_mappings.append(enhanced_mapping)

        return enhanced_mappings

    def generate_transformation_sql(
        self,
        mappings: List[Dict],
        source_table: str,
        target_table: str
    ) -> Dict:
        """
        生成字段转换的 SQL 语句

        Returns:
            SQL 语句和相关配置
        """
        select_clauses = []
        where_clauses = []

        for mapping in mappings:
            source_col = mapping["source_field"]
            target_col = mapping["target_field"]
            conversion = mapping.get("data_type_conversion", {})

            # 构建转换表达式
            if conversion["conversion"] == "direct":
                expr = source_col
            elif conversion["conversion"] == "to_string":
                expr = f"CAST({source_col} AS VARCHAR)"
            elif conversion["conversion"] == "cast_numeric":
                expr = f"CAST(NULLIF({source_col}, '') AS NUMERIC)"
            elif conversion["conversion"] == "cast_decimal":
                precision = conversion.get("precision", 10)
                scale = conversion.get("scale", 2)
                expr = f"CAST({source_col} AS DECIMAL({precision}, {scale}))"
            elif conversion["conversion"] == "to_timestamp":
                expr = f"TO_TIMESTAMP({source_col})"
            elif conversion["conversion"] == "to_unix_timestamp":
                expr = f"UNIX_TIMESTAMP({source_col})"
            elif conversion["conversion"] == "to_int":
                expr = f"CASE WHEN {source_col} THEN 1 ELSE 0 END"
            elif conversion["conversion"] == "to_yes_no":
                expr = f"CASE WHEN {source_col} THEN 'yes' ELSE 'no' END"
            elif conversion["conversion"] == "to_float":
                expr = f"CAST({source_col} AS DOUBLE PRECISION)"
            elif conversion["conversion"] == "format_string":
                expr = f"TO_CHAR({source_col}, 'YYYY-MM-DD')"
            elif conversion["conversion"] == "encode_base64":
                expr = f"BASE64_ENCODE({source_col})"
            elif mapping.get("transformation"):
                expr = mapping["transformation"].format(field=source_col)
            else:
                expr = source_col

            select_clauses.append(f"    {expr} AS {target_col}")

            # 添加转换条件检查（高风险转换）
            if conversion.get("conversion_risk") == "high":
                where_clauses.append(f"({source_col} IS NOT NULL OR {target_col} IS NULL)")

        # 生成完整的 SELECT 语句
        select_sql = "SELECT\n" + ",\n".join(select_clauses) + f"\nFROM {source_table}"

        if where_clauses:
            select_sql += "\nWHERE " + " OR ".join(where_clauses)

        return {
            "select_sql": select_sql,
            "mappings": mappings,
            "conversion_count": sum(1 for m in mappings if m.get("requires_casting", False)),
            "high_risk_count": sum(1 for m in mappings if m.get("conversion_risk") == "high"),
        }

    def detect_mapping_conflicts(
        self,
        mappings: List[Dict],
        target_schema: List[Dict]
    ) -> List[Dict]:
        """
        检测映射冲突

        检查：
        1. 多源字段映射到同一目标字段
        2. 目标字段约束冲突
        3. 数据长度不兼容
        """
        conflicts = []

        # 检查多对一映射
        target_field_counts = {}
        for mapping in mappings:
            target = mapping["target_field"]
            target_field_counts[target] = target_field_counts.get(target, 0) + 1

        for target, count in target_field_counts.items():
            if count > 1:
                sources = [m["source_field"] for m in mappings if m["target_field"] == target]
                conflicts.append({
                    "type": "multiple_sources",
                    "target_field": target,
                    "source_fields": sources,
                    "severity": "error",
                    "message": f"多个源字段映射到目标字段 {target}",
                })

        # 检查数据类型兼容性
        for mapping in mappings:
            conversion = mapping.get("data_type_conversion", {})
            if conversion.get("conversion_risk") == "high":
                conflicts.append({
                    "type": "type_incompatible",
                    "source_field": mapping["source_field"],
                    "target_field": mapping["target_field"],
                    "source_type": conversion.get("source_type"),
                    "target_type": conversion.get("target_type"),
                    "severity": "warning",
                    "message": f"数据类型转换可能存在精度丢失",
                })

        # 检查长度限制
        target_schema_dict = {f["name"]: f for f in target_schema}
        for mapping in mappings:
            target_field = target_schema_dict.get(mapping["target_field"])
            if target_field and "length" in target_field:
                source_field = next(
                    (f for f in target_schema if f["name"] == mapping["source_field"]),
                    None
                )
                if source_field and source_field.get("length", 0) > target_field.get("length", 0):
                    conflicts.append({
                        "type": "length_exceeded",
                        "source_field": mapping["source_field"],
                        "target_field": mapping["target_field"],
                        "source_length": source_field.get("length", 0),
                        "target_length": target_field.get("length", 0),
                        "severity": "warning",
                        "message": f"源字段长度可能超过目标字段长度",
                    })

        return conflicts

    def suggest_derived_fields(
        self,
        source_columns: List[Dict],
        target_columns: List[Dict],
        context: Optional[Dict] = None
    ) -> List[FieldMappingSuggestion]:
        """
        推荐派生字段映射

        基于源字段组合生成新字段的建议
        """
        suggestions = []

        # 检测常见组合模式
        # 1. 全名 = 名 + 姓
        if self._has_fields(source_columns, ["first_name", "last_name"]) and \
           self._has_field(target_columns, "full_name"):
            suggestions.append(FieldMappingSuggestion(
                source_field="CONCAT(first_name, ' ', last_name)",
                target_field="full_name",
                confidence=0.9,
                mapping_type="derived",
                transformation="CONCAT(first_name, ' ', last_name)",
                data_type_conversion={"conversion": "direct"},
                quality_score=0.8
            ))

        # 2. 全名 = 姓 + 中间名 + 名
        if self._has_fields(source_columns, ["last_name", "first_name", "middle_name"]) and \
           self._has_field(target_columns, "full_name"):
            suggestions.append(FieldMappingSuggestion(
                source_field="CONCAT(last_name, ' ', first_name)",
                target_field="full_name",
                confidence=0.85,
                mapping_type="derived",
                transformation="CONCAT_WS(' ', last_name, first_name, middle_name)",
                data_type_conversion={"conversion": "direct"},
                quality_score=0.8
            ))

        # 3. 完整地址 = 省 + 市 + 区 + 详细地址
        if self._has_fields(source_columns, ["province", "city", "district", "address"]) and \
           self._has_field(target_columns, "full_address"):
            suggestions.append(FieldMappingSuggestion(
                source_field="CONCAT(province, City, District, Address)",
                target_field="full_address",
                confidence=0.85,
                mapping_type="derived",
                transformation="CONCAT_WS(' ', province, city, district, address)",
                data_type_conversion={"conversion": "direct"},
                quality_score=0.75
            ))

        # 4. 年龄 = 出生日期计算
        if self._has_fields(source_columns, ["birth_date", "birthday", "dob"]) and \
           self._has_field(target_columns, ["age", "user_age"]):
            suggestions.append(FieldMappingSuggestion(
                source_field="birth_date",
                target_field="age",
                confidence=0.95,
                mapping_type="derived",
                transformation="TIMESTAMPDIFF(YEAR, CURDATE(), birth_date)",
                data_type_conversion={"conversion": "direct", "target_type": "int"},
                quality_score=0.9
            ))

        # 5. 性别 = 从身份证号提取
        if self._has_field(source_columns, ["id_card", "id_card_no", "identity_card"]) and \
           self._has_field(target_columns, ["gender", "sex"]):
            suggestions.append(FieldMappingSuggestion(
                source_field="id_card",
                target_field="gender",
                confidence=0.95,
                mapping_type="derived",
                transformation="CASE SUBSTRING(id_card, 17, 1) WHEN '1' THEN 'male' WHEN '2' THEN 'female' END",
                data_type_conversion={"conversion": "direct", "target_type": "varchar"},
                quality_score=0.85
            ))

        return suggestions

    # ==================== 辅助方法 ====================

    def _get_table_columns(
        self,
        db: Session,
        table_name: str,
        database_name: Optional[str] = None
    ) -> List[Dict]:
        """获取表的列信息"""
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
                "position": col.position or 0,
                "length": self._extract_type_length(col.data_type),
                "description": col.description,
                "comment": col.ai_description,
            }
            for col in columns
        ]

    def _extract_type_length(self, data_type: Optional[str]) -> int:
        """从数据类型中提取长度"""
        if not data_type:
            return 0

        import re
        match = re.search(r'varchar\((\d+)\)', data_type)
        if match:
            return int(match.group(1))

        match = re.search(r'char\((\d+)\)', data_type)
        if match:
            return int(match.group(1))

        match = re.search(r'decimal\((\d+),\s*(\d+)\)', data_type)
        if match:
            return int(match.group(1))

        return 0

    def _find_exact_matches(
        self,
        source_columns: List[Dict],
        target_columns: List[Dict]
    ) -> List[FieldMappingSuggestion]:
        """查找完全匹配的字段"""
        matches = []
        source_names = {col["name"] for col in source_columns}

        for target_col in target_columns:
            if target_col["name"] in source_names:
                source_col = next(c for c in source_columns if c["name"] == target_col["name"])
                matches.append(FieldMappingSuggestion(
                    source_field=target_col["name"],
                    target_field=target_col["name"],
                    confidence=1.0,
                    mapping_type="exact",
                    transformation="",
                    data_type_conversion=self._get_type_conversion(
                        source_col["type"],
                        target_col["type"]
                    ),
                    quality_score=1.0
                ))

        return matches

    def _find_fuzzy_matches(
        self,
        source_columns: List[Dict],
        target_columns: List[Dict],
        exclude_matched: List[str] = None
    ) -> List[FieldMappingSuggestion]:
        """查找模糊匹配的字段（名称相似）"""
        matches = []
        exclude = set(exclude_matched or [])

        for source_col in source_columns:
            if source_col["name"] in exclude:
                continue

            for target_col in target_columns:
                if target_col["name"] in exclude:
                    continue

                similarity = self._calculate_name_similarity(
                    source_col["name"],
                    target_col["name"]
                )

                if similarity >= self._name_similarity_threshold:
                    matches.append(FieldMappingSuggestion(
                        source_field=source_col["name"],
                        target_field=target_col["name"],
                        confidence=similarity * 0.9,  # 模糊匹配置信度稍低
                        mapping_type="fuzzy",
                        transformation="",
                        data_type_conversion=self._get_type_conversion(
                            source_col["type"],
                            target_col["type"]
                        ),
                        quality_score=similarity
                    ))

        return matches

    def _find_semantic_matches(
        self,
        source_columns: List[Dict],
        target_columns: List[Dict],
        exclude_matched: List[str] = None
    ) -> List[FieldMappingSuggestion]:
        """查找语义匹配的字段"""
        matches = []
        exclude = set(exclude_matched or [])

        for source_col in source_columns:
            if source_col["name"] in exclude:
                continue

            source_name = source_col["name"].lower()

            for rule in self._semantic_mapping_rules:
                # 检查源字段是否匹配规则模式
                source_matched = any(
                    any(p in source_name for p in rule["patterns"])
                    for rule in self._semantic_mapping_rules
                )

                if not source_matched:
                    continue

                for target_col in target_columns:
                    if target_col["name"] in exclude:
                        continue

                    target_name = target_col["name"].lower()

                    # 检查目标字段是否匹配
                    target_matched = any(
                        any(p in target_name for p in rule["target_patterns"])
                        for rule in self._semantic_mapping_rules
                    )

                    if target_matched:
                        matches.append(FieldMappingSuggestion(
                            source_field=source_col["name"],
                            target_field=target_col["name"],
                            confidence=rule["confidence"],
                            mapping_type="semantic",
                            transformation="",
                            data_type_conversion=self._get_type_conversion(
                                source_col["type"],
                                target_col["type"]
                            ),
                            quality_score=rule["confidence"]
                        ))

        return matches

    def _infer_type_based_matches(
        self,
        source_columns: List[Dict],
        target_columns: List[Dict],
        exclude_mapped: List[str] = None
    ) -> List[FieldMappingSuggestion]:
        """基于数据类型和位置推断映射"""
        matches = []
        exclude = set(exclude_mapped or [])

        # 获取未映射的源和目标列
        unmapped_source = [c for c in source_columns if c["name"] not in exclude]
        unmapped_target = [c for c in target_columns if c["name"] not in exclude]

        # 按位置映射（当其他方法无效时的最后手段）
        for i, (source_col, target_col) in enumerate(zip(unmapped_source, unmapped_target)):
            if i >= len(unmapped_target):
                break

            # 只有当类型兼容或可以转换时才推荐
            conversion = self._get_type_conversion(source_col["type"], target_col["type"])
            if conversion["conversion_risk"] != "critical":
                matches.append(FieldMappingSuggestion(
                    source_field=source_col["name"],
                    target_field=target_col["name"],
                    confidence=0.3,  # 低置信度
                    mapping_type="inferred",
                    transformation="",
                    data_type_conversion=conversion,
                    quality_score=0.3
                ))

        return matches

    def _calculate_name_similarity(self, name1: str, name2: str) -> float:
        """计算字段名相似度（多种算法组合）"""
        name1_lower = name1.lower()
        name2_lower = name2.lower()

        # 完全相同
        if name1_lower == name2_lower:
            return 1.0

        # 包含关系
        if name1_lower in name2_lower or name2_lower in name1_lower:
            return 0.8

        # Levenshtein 距离
        levenshtein = self._levenshtein_distance(name1_lower, name2_lower)
        max_len = max(len(name1_lower), len(name2_lower))
        if max_len == 0:
            return 0.0
        levenshtein_sim = 1 - (levenshtein / max_len)

        # Jaccard 相似度（字符集）
        set1 = set(name1_lower)
        set2 = set(name2_lower)
        jaccard = len(set1 & set2) / len(set1 | set2) if (set1 | set2) else 0

        # 组合得分
        return levenshtein_sim * 0.6 + jaccard * 0.4

    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """计算 Levenshtein 距离"""
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

    def _get_type_conversion(
        self,
        source_type: str,
        target_type: str
    ) -> Dict:
        """获取类型转换配置"""
        source_type_norm = source_type.lower().split("(")[0].strip()
        target_type_norm = target_type.lower().split("(")[0].strip()

        # 归一化类型名称
        type_aliases = {
            "varchar": "string",
            "char": "string",
            "text": "string",
            "int": "integer",
            "tinyint": "integer",
            "smallint": "integer",
            "bigint": "integer",
            "decimal": "decimal",
            "numeric": "decimal",
            "double": "float",
            "float": "float",
            "bool": "boolean",
            "datetime": "date",
            "timestamp": "date",
            "blob": "binary",
        }

        source_type_alias = type_aliases.get(source_type_norm, source_type_norm)
        target_type_alias = type_aliases.get(target_type_norm, target_type_norm)

        # 查找匹配的转换规则
        rules = self._type_mapping_rules.get(source_type_alias, [])
        for rule in rules:
            if target_type_alias in rule["target_types"]:
                return {
                    "source_type": source_type,
                    "target_type": target_type,
                    "conversion": rule["conversion"],
                    "cost": rule["cost"],
                    "conversion_risk": self._assess_type_conversion_risk(
                        source_type_alias,
                        target_type_alias
                    ),
                }

        # 默认：尝试直接转换
        return {
            "source_type": source_type,
            "target_type": target_type,
            "conversion": "direct",
            "cost": 0,
            "conversion_risk": self._assess_type_conversion_risk(
                source_type_alias,
                target_type_alias
            ),
        }

    def _assess_type_conversion_risk(self, source_type: str, target_type: str) -> str:
        """评估类型转换风险"""
        risk_matrix = {
            ("string", "integer"): "medium",
            ("string", "decimal"): "medium",
            ("string", "float"): "medium",
            ("integer", "string"): "low",
            ("integer", "decimal"): "low",
            ("integer", "float"): "low",
            ("decimal", "string"): "high",
            ("decimal", "integer"): "high",
            ("date", "string"): "low",
            ("date", "integer"): "medium",
            ("boolean", "integer"): "low",
        }

        return risk_matrix.get((source_type, target_type), "low")

    def _calculate_mapping_quality(
        self,
        suggestion: FieldMappingSuggestion,
        source_columns: List[Dict],
        target_columns: List[Dict]
    ) -> float:
        """计算映射质量得分"""
        score = 0.0

        # 基础分：置信度
        score += suggestion.confidence * 0.5

        # 类型兼容性加分
        conversion = suggestion.data_type_conversion
        if conversion["conversion_risk"] == "low":
            score += 0.2
        elif conversion["conversion_risk"] == "medium":
            score += 0.1

        # 源和目标字段都存在描述加分
        source_col = next((c for c in source_columns if c["name"] == suggestion.source_field), None)
        target_col = next((c for c in target_columns if c["name"] == suggestion.target_field), None)

        if source_col and source_col.get("description"):
            score += 0.1
        if target_col and target_col.get("description"):
            score += 0.1

        # 语义匹配加分
        if suggestion.mapping_type == "semantic":
            score += 0.15

        return min(score, 1.0)

    def _generate_mapping_report(
        self,
        source_table: str,
        target_table: str,
        source_columns: List[Dict],
        target_columns: List[Dict],
        suggestions: List[FieldMappingSuggestion]
    ) -> Dict:
        """生成映射报告"""
        # 统计映射覆盖率
        source_mapped = len(set(s.source_field for s in suggestions))
        target_mapped = len(set(s.target_field for s in suggestions))

        source_coverage = source_mapped / len(source_columns) if source_columns else 0
        target_coverage = target_mapped / len(target_columns) if target_columns else 0

        # 按映射类型分组
        type_counts = {}
        for s in suggestions:
            type_counts[s.mapping_type] = type_counts.get(s.mapping_type, 0) + 1

        # 评估映射质量
        avg_confidence = sum(s.confidence for s in suggestions) / len(suggestions) if suggestions else 0
        avg_quality = sum(s.quality_score for s in suggestions) / len(suggestions) if suggestions else 0

        return {
            "source_table": source_table,
            "target_table": target_table,
            "source_columns_count": len(source_columns),
            "target_columns_count": len(target_columns),
            "suggestions": [s.to_dict() for s in suggestions],
            "summary": {
                "total_suggestions": len(suggestions),
                "source_coverage": source_coverage,
                "target_coverage": target_coverage,
                "avg_confidence": avg_confidence,
                "avg_quality": avg_quality,
                "mapping_types": type_counts,
            },
            "unmapped_source": [c["name"] for c in source_columns
                                 if c["name"] not in set(s.source_field for s in suggestions)],
            "unmapped_target": [c["name"] for c in target_columns
                                 if c["name"] not in set(s.target_field for s in suggestions)],
        }

    def _has_fields(self, columns: List[Dict], field_names: List[str]) -> bool:
        """检查是否包含指定字段"""
        column_names = {c["name"].lower() for c in columns}
        return all(name.lower() in column_names for name in field_names)

    def _has_field(self, columns: List[Dict], field_name: str) -> bool:
        """检查是否包含单个字段"""
        return any(c["name"].lower() == field_name.lower() for c in columns)


# 创建全局服务实例
_ai_field_mapping_service = None


def get_ai_field_mapping_service() -> AIFieldMappingService:
    """获取 AI 字段映射服务实例"""
    global _ai_field_mapping_service
    if _ai_field_mapping_service is None:
        _ai_field_mapping_service = AIFieldMappingService()
    return _ai_field_mapping_service
