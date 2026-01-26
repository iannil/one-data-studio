"""
AI 清洗规则建议服务
基于数据质量问题自动推荐清洗规则
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, text

from models.metadata import MetadataTable, MetadataColumn
from models.quality import QualityAlert

logger = logging.getLogger(__name__)


class CleaningRecommendation:
    """清洗规则推荐"""

    def __init__(
        self,
        issue_type: str,
        issue_description: str,
        rule_type: str,
        rule_name: str,
        rule_config: Dict,
        priority: str = "medium",
        estimated_improvement: float = 0.0
    ):
        self.issue_type = issue_type
        self.issue_description = issue_description
        self.rule_type = rule_type
        self.rule_name = rule_name
        self.rule_config = rule_config
        self.priority = priority
        self.estimated_improvement = estimated_improvement

    def to_dict(self) -> Dict:
        return {
            "issue_type": self.issue_type,
            "issue_description": self.issue_description,
            "rule_type": self.rule_type,
            "rule_name": self.rule_name,
            "rule_config": self.rule_config,
            "priority": self.priority,
            "estimated_improvement": self.estimated_improvement,
        }


class AICleaningAdvisor:
    """AI 清洗规则建议服务"""

    def __init__(self):
        self._rule_templates = self._init_rule_templates()
        self._pattern_detectors = self._init_pattern_detectors()

    def _init_rule_templates(self) -> Dict[str, List[Dict]]:
        """初始化规则模板"""
        return {
            "missing_values": [
                {
                    "rule_type": "completeness",
                    "rule_name": "非空检查",
                    "rule_expression": "{column} IS NOT NULL",
                    "severity": "error",
                    "config_template": {
                        "threshold": 100.0,
                        "action": "reject"
                    }
                },
                {
                    "rule_type": "completeness",
                    "rule_name": "缺失值填充",
                    "rule_expression": "COALESCE({column}, {default_value})",
                    "severity": "warning",
                    "config_template": {
                        "threshold": 95.0,
                        "action": "fill",
                        "fill_strategy": "auto"
                    }
                },
                {
                    "rule_type": "completeness",
                    "rule_name": "默认值替换",
                    "rule_expression": "CASE WHEN {column} IS NULL THEN {default_value} ELSE {column} END",
                    "severity": "info",
                    "config_template": {
                        "threshold": 90.0,
                        "action": "replace",
                        "default_value": ""
                    }
                }
            ],
            "duplicate_records": [
                {
                    "rule_type": "uniqueness",
                    "rule_name": "唯一性检查",
                    "rule_expression": "COUNT(*) OVER (PARTITION BY {column}) = 1",
                    "severity": "error",
                    "config_template": {
                        "threshold": 100.0,
                        "action": "deduplicate"
                    }
                },
                {
                    "rule_type": "uniqueness",
                    "rule_name": "保留最新记录",
                    "rule_expression": "ROW_NUMBER() OVER (PARTITION BY {column} ORDER BY {timestamp_column} DESC)",
                    "severity": "warning",
                    "config_template": {
                        "threshold": 95.0,
                        "action": "keep_latest",
                        "timestamp_column": "updated_at"
                    }
                }
            ],
            "invalid_format": [
                {
                    "rule_type": "validity",
                    "rule_name": "格式验证",
                    "rule_expression": "REGEXP_LIKE({column}, '{pattern}')",
                    "severity": "error",
                    "config_template": {
                        "threshold": 100.0,
                        "action": "reject",
                        "pattern": ""
                    }
                },
                {
                    "rule_type": "validity",
                    "rule_name": "格式清洗",
                    "rule_expression": "REGEXP_REPLACE({column}, '{pattern}', '{replacement}')",
                    "severity": "warning",
                    "config_template": {
                        "threshold": 90.0,
                        "action": "clean",
                        "pattern": "",
                        "replacement": ""
                    }
                }
            ],
            "out_of_range": [
                {
                    "rule_type": "validity",
                    "rule_name": "范围检查",
                    "rule_expression": "{column} BETWEEN {min_value} AND {max_value}",
                    "severity": "error",
                    "config_template": {
                        "threshold": 100.0,
                        "action": "reject",
                        "min_value": None,
                        "max_value": None
                    }
                },
                {
                    "rule_type": "validity",
                    "rule_name": "范围截断",
                    "rule_expression": "CASE WHEN {column} < {min_value} THEN {min_value} WHEN {column} > {max_value} THEN {max_value} ELSE {column} END",
                    "severity": "warning",
                    "config_template": {
                        "threshold": 95.0,
                        "action": "clip",
                        "min_value": None,
                        "max_value": None
                    }
                }
            ],
            "inconsistent_values": [
                {
                    "rule_type": "consistency",
                    "rule_name": "值标准化",
                    "rule_expression": "STANDARDIZE({column}, '{standard_type}')",
                    "severity": "warning",
                    "config_template": {
                        "threshold": 90.0,
                        "action": "standardize",
                        "standard_type": "case"  # case, trim, normalize
                    }
                },
                {
                    "rule_type": "consistency",
                    "rule_name": "映射替换",
                    "rule_expression": "MAPPING({column}, {mapping_dict})",
                    "severity": "info",
                    "config_template": {
                        "threshold": 85.0,
                        "action": "map",
                        "mapping_dict": {}
                    }
                }
            ],
            "dirty_data": [
                {
                    "rule_type": "accuracy",
                    "rule_name": "空格清理",
                    "rule_expression": "TRIM({column})",
                    "severity": "info",
                    "config_template": {
                        "threshold": 95.0,
                        "action": "trim"
                    }
                },
                {
                    "rule_type": "accuracy",
                    "rule_name": "特殊字符清理",
                    "rule_expression": "REGEXP_REPLACE({column}, '[^\\w\\s]', '')",
                    "severity": "warning",
                    "config_template": {
                        "threshold": 90.0,
                        "action": "remove_special_chars"
                    }
                }
            ],
            "sensitive_data": [
                {
                    "rule_type": "security",
                    "rule_name": "敏感数据脱敏",
                    "rule_expression": "MASK({column}, '{mask_type}')",
                    "severity": "critical",
                    "config_template": {
                        "threshold": 100.0,
                        "action": "mask",
                        "mask_type": "partial"  # partial, full, hash
                    }
                }
            ]
        }

    def _init_pattern_detectors(self) -> Dict[str, callable]:
        """初始化模式检测器"""
        return {
            "phone": self._detect_phone_pattern,
            "email": self._detect_email_pattern,
            "id_card": self._detect_id_card_pattern,
            "date": self._detect_date_pattern,
            "numeric": self._detect_numeric_pattern,
        }

    def analyze_table_quality_issues(
        self,
        db: Session,
        table_name: str,
        database_name: Optional[str] = None
    ) -> List[CleaningRecommendation]:
        """
        分析表的数据质量问题

        自动检测常见的数据质量问题并推荐清洗规则
        """
        recommendations = []

        # 获取表的列信息
        query = db.query(MetadataColumn).filter(
            MetadataColumn.table_name == table_name
        )

        if database_name:
            query = query.filter(MetadataColumn.database_name == database_name)

        columns = query.all()

        if not columns:
            return []

        for column in columns:
            # 分析每列的数据质量问题
            column_issues = self._analyze_column_issues(db, column)
            recommendations.extend(column_issues)

        return recommendations

    def _analyze_column_issues(
        self,
        db: Session,
        column: MetadataColumn
    ) -> List[CleaningRecommendation]:
        """分析单个列的数据质量问题"""
        issues = []
        col_name = column.column_name
        col_type = column.data_type or "varchar"

        # 1. 检查缺失值问题
        if column.is_nullable:
            issues.append(CleaningRecommendation(
                issue_type="missing_values",
                issue_description=f"列 {col_name} 允许为空，可能存在缺失值",
                rule_type="completeness",
                rule_name=f"{col_name}_非空检查",
                rule_config={
                    "target_column": col_name,
                    "threshold": 95.0,
                    "action": "fill",
                    "fill_strategy": self._recommend_fill_strategy(col_type)
                },
                priority="high" if self._is_important_column(col_name) else "medium",
                estimated_improvement=0.15
            ))

        # 2. 检查敏感数据
        if self._is_sensitive_column(col_name):
            issues.append(CleaningRecommendation(
                issue_type="sensitive_data",
                issue_description=f"列 {col_name} 可能包含敏感数据",
                rule_type="security",
                rule_name=f"{col_name}_脱敏规则",
                rule_config={
                    "target_column": col_name,
                    "action": "mask",
                    "mask_type": self._get_mask_type(col_name),
                    "threshold": 100.0
                },
                priority="critical",
                estimated_improvement=0.3
            ))

        # 3. 检查格式问题（基于列名模式）
        format_rules = self._detect_format_requirements(col_name)
        for rule in format_rules:
            issues.append(CleaningRecommendation(
                issue_type="invalid_format",
                issue_description=f"列 {col_name} 需要格式验证: {rule['pattern_description']}",
                rule_type="validity",
                rule_name=f"{col_name}_格式验证",
                rule_config={
                    "target_column": col_name,
                    "pattern": rule["pattern"],
                    "action": "validate",
                    "threshold": 100.0
                },
                priority="high",
                estimated_improvement=0.2
            ))

        # 4. 检查数据清洗需求
        if col_type.lower() in ["varchar", "text", "char"]:
            issues.append(CleaningRecommendation(
                issue_type="dirty_data",
                issue_description=f"列 {col_name} 可能包含多余的空格或特殊字符",
                rule_type="accuracy",
                rule_name=f"{col_name}_清洗规则",
                rule_config={
                    "target_column": col_name,
                    "action": "trim",
                    "threshold": 95.0
                },
                priority="low",
                estimated_improvement=0.1
            ))

        return issues

    def analyze_quality_alerts(
        self,
        alerts: List[Dict]
    ) -> List[CleaningRecommendation]:
        """
        基于质量告警生成清洗规则建议

        Args:
            alerts: 质量告警列表

        Returns:
            清洗规则建议列表
        """
        recommendations = []

        # 按告警类型分组
        alert_groups = self._group_alerts_by_type(alerts)

        for alert_type, type_alerts in alert_groups.items():
            # 为每种类型的告警生成对应的清洗规则
            templates = self._rule_templates.get(alert_type, [])

            # 如果没有直接对应的模板，尝试智能匹配
            if not templates:
                templates = self._find_matching_templates(alert_type)

            for alert in type_alerts[:3]:  # 每类最多处理3个告警
                for template in templates:
                    # 基于模板生成具体规则
                    rule_config = self._generate_rule_from_template(template, alert)

                    # 评估优先级
                    priority = self._assess_priority(alert, template)

                    # 估算改进效果
                    improvement = self._estimate_improvement(alert, template)

                    recommendations.append(CleaningRecommendation(
                        issue_type=alert_type,
                        issue_description=alert.get("message", ""),
                        rule_type=template["rule_type"],
                        rule_name=f"{alert.get('target_column', 'field')}_{template['rule_name']}",
                        rule_config=rule_config,
                        priority=priority,
                        estimated_improvement=improvement
                    ))

        # 按优先级和估算改进效果排序
        recommendations.sort(
            key=lambda r: (
                self._priority_score(r.priority),
                r.estimated_improvement
            ),
            reverse=True
        )

        return recommendations

    def recommend_rules_for_column(
        self,
        column_info: Dict
    ) -> List[CleaningRecommendation]:
        """
        为单个列推荐清洗规则

        Args:
            column_info: 列信息，包含 name, type, nullable, sample_values 等

        Returns:
            清洗规则建议列表
        """
        col_name = column_info.get("name", "")
        col_type = column_info.get("type", "varchar")
        nullable = column_info.get("nullable", True)
        sample_values = column_info.get("sample_values", [])

        recommendations = []

        # 基于数据类型推荐规则
        type_rules = self._get_rules_for_data_type(col_type)
        for rule in type_rules:
            rule_config = rule["config_template"].copy()
            rule_config["target_column"] = col_name

            recommendations.append(CleaningRecommendation(
                issue_type=rule.get("issue_type", "data_quality"),
                issue_description=f"为 {col_name} ({col_type}) 添加数据质量规则",
                rule_type=rule["rule_type"],
                rule_name=f"{col_name}_{rule['rule_name']}",
                rule_config=rule_config,
                priority="medium",
                estimated_improvement=0.1
            ))

        # 基于列名模式推荐规则
        pattern_rules = self._detect_format_requirements(col_name)
        for rule in pattern_rules:
            rule_config = {
                "target_column": col_name,
                "pattern": rule["pattern"],
                "action": "validate",
                "threshold": 100.0
            }

            recommendations.append(CleaningRecommendation(
                issue_type="invalid_format",
                issue_description=f"列 {col_name} 需要格式验证",
                rule_type="validity",
                rule_name=f"{col_name}_格式验证",
                rule_config=rule_config,
                priority="high",
                estimated_improvement=0.2
            ))

        # 基于样本数据检测异常
        if sample_values:
            anomaly_rules = self._detect_anomalies_in_samples(col_name, sample_values)
            recommendations.extend(anomaly_rules)

        return recommendations

    def generate_kettle_steps(
        self,
        recommendations: List[CleaningRecommendation]
    ) -> List[Dict]:
        """
        将清洗规则转换为 Kettle ETL 步骤配置

        Args:
            recommendations: 清洗规则建议列表

        Returns:
            Kettle 步骤配置列表
        """
        steps = []

        for rec in recommendations:
            step = self._create_kettle_step(rec)
            if step:
                steps.append(step)

        return steps

    # ==================== 辅助方法 ====================

    def _group_alerts_by_type(self, alerts: List[Dict]) -> Dict[str, List[Dict]]:
        """按类型分组告警"""
        groups = {}

        for alert in alerts:
            # 从告警中推断类型
            alert_type = self._infer_alert_type(alert)
            if alert_type not in groups:
                groups[alert_type] = []
            groups[alert_type].append(alert)

        return groups

    def _infer_alert_type(self, alert: Dict) -> str:
        """推断告警类型"""
        message = alert.get("message", "").lower()
        column = alert.get("target_column", "").lower()

        if "null" in message or "缺失" in message or "missing" in message:
            return "missing_values"
        if "duplicate" in message or "重复" in message:
            return "duplicate_records"
        if "format" in message or "格式" in message:
            return "invalid_format"
        if "range" in message or "范围" in message or "out of" in message:
            return "out_of_range"
        if "inconsistent" in message or "不一致" in message:
            return "inconsistent_values"
        if "sensitive" in message or "敏感" in message:
            return "sensitive_data"
        if "phone" in column or "mobile" in column:
            return "invalid_format"
        if "email" in column or "mail" in column:
            return "invalid_format"

        return "dirty_data"

    def _find_matching_templates(self, alert_type: str) -> List[Dict]:
        """查找匹配的规则模板"""
        # 简单的模糊匹配
        all_templates = []
        for category, templates in self._rule_templates.items():
            all_templates.extend(templates)

        # 基于关键词匹配
        keywords = {
            "missing_values": ["null", "missing", "缺失"],
            "invalid_format": ["format", "格式", "pattern"],
            "out_of_range": ["range", "范围"],
        }

        for key, kw_list in keywords.items():
            if any(kw in alert_type for kw in kw_list):
                return self._rule_templates.get(key, [])

        return all_templates[:3]  # 返回前3个模板

    def _generate_rule_from_template(self, template: Dict, alert: Dict) -> Dict:
        """从模板生成具体规则配置"""
        config = template["config_template"].copy()

        # 填充模板参数
        config["target_column"] = alert.get("target_column", "")
        config["target_table"] = alert.get("target_table", "")
        config["target_database"] = alert.get("target_database", "")

        # 从告警中提取期望值
        if "expected_value" in alert:
            config["expected_value"] = alert["expected_value"]
        if "actual_value" in alert:
            config["actual_value"] = alert["actual_value"]

        # 根据告警严重程度调整阈值
        severity = alert.get("severity", "warning")
        if severity == "critical":
            config["threshold"] = 100.0
        elif severity == "error":
            config["threshold"] = 98.0
        elif severity == "warning":
            config["threshold"] = 95.0
        else:
            config["threshold"] = 90.0

        return config

    def _assess_priority(self, alert: Dict, template: Dict) -> str:
        """评估规则优先级"""
        severity = alert.get("severity", "warning")

        if severity == "critical":
            return "critical"
        elif severity == "error":
            return "high"
        elif severity == "warning":
            return "medium"
        else:
            return "low"

    def _estimate_improvement(self, alert: Dict, template: Dict) -> float:
        """估算规则改进效果"""
        severity_scores = {
            "critical": 0.3,
            "error": 0.2,
            "warning": 0.15,
            "info": 0.1
        }

        base_score = severity_scores.get(alert.get("severity", "warning"), 0.15)

        # 根据规则类型调整
        rule_type = template.get("rule_type", "")
        if rule_type == "security":
            base_score += 0.1
        elif rule_type == "validity":
            base_score += 0.05

        return min(base_score, 0.5)

    def _priority_score(self, priority: str) -> int:
        """优先级转换为分数"""
        scores = {
            "critical": 4,
            "high": 3,
            "medium": 2,
            "low": 1
        }
        return scores.get(priority, 0)

    def _recommend_fill_strategy(self, data_type: str) -> str:
        """推荐缺失值填充策略"""
        data_type = data_type.lower()

        if "int" in data_type or "number" in data_type or "decimal" in data_type:
            return "mean"  # 数值型使用均值
        elif "date" in data_type or "time" in data_type:
            return "interpolate"  # 日期型使用插值
        elif "bool" in data_type:
            return "mode"  # 布尔型使用众数
        else:
            return "default"  # 字符串型使用默认值

    def _is_important_column(self, column_name: str) -> bool:
        """判断是否为重要列"""
        important_keywords = [
            "id", "key", "code", "name", "title",
            "status", "state", "type", "category"
        ]
        col_lower = column_name.lower()
        return any(kw in col_lower for kw in important_keywords)

    def _is_sensitive_column(self, column_name: str) -> bool:
        """判断是否为敏感列"""
        sensitive_keywords = [
            "phone", "mobile", "tel", "telephone",
            "email", "mail", "contact",
            "id_card", "identity", "ssn", "passport",
            "password", "secret", "token",
            "credit", "bank", "card",
            "address", "location", "gps"
        ]
        col_lower = column_name.lower()
        return any(kw in col_lower for kw in sensitive_keywords)

    def _get_mask_type(self, column_name: str) -> str:
        """获取脱敏类型"""
        col_lower = column_name.lower()

        if any(kw in col_lower for kw in ["phone", "mobile", "tel"]):
            return "phone_mask"  # 138****1234
        if any(kw in col_lower for kw in ["email", "mail"]):
            return "email_mask"  # a***@example.com
        if any(kw in col_lower for kw in ["id_card", "identity", "ssn"]):
            return "id_mask"  # 保留前6后4
        if any(kw in col_lower for kw in ["name", "user"]):
            return "name_mask"  # 保留姓氏
        return "partial"

    def _detect_format_requirements(self, column_name: str) -> List[Dict]:
        """检测列的格式要求"""
        rules = []
        col_lower = column_name.lower()

        # 电话号码格式
        if any(kw in col_lower for kw in ["phone", "mobile", "tel", "telephone"]):
            rules.append({
                "pattern_description": "11位手机号或区号+号码",
                "pattern": "^1[3-9]\\d{9}$|^0\\d{2,3}-?\\d{7,8}$"
            })

        # 邮箱格式
        if any(kw in col_lower for kw in ["email", "mail"]):
            rules.append({
                "pattern_description": "标准邮箱格式",
                "pattern": "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"
            })

        # 身份证格式
        if any(kw in col_lower for kw in ["id_card", "identity", "idcard"]):
            rules.append({
                "pattern_description": "18位身份证号",
                "pattern": "^[1-9]\\d{5}(18|19|20)\\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\\d|3[01])\\d{3}[0-9Xx]$"
            })

        # 日期格式
        if any(kw in col_lower for kw in ["date", "time", "created", "updated"]):
            rules.append({
                "pattern_description": "标准日期格式",
                "pattern": "^\\d{4}-\\d{2}-\\d{2}$|^\\d{4}/\\d{2}/\\d{2}$"
            })

        # URL格式
        if any(kw in col_lower for kw in ["url", "link", "href"]):
            rules.append({
                "pattern_description": "HTTP/HTTPS URL",
                "pattern": "^https?://[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}(/.*)?$"
            })

        return rules

    def _get_rules_for_data_type(self, data_type: str) -> List[Dict]:
        """根据数据类型获取推荐规则"""
        data_type = data_type.lower()
        rules = []

        if "int" in data_type or "number" in data_type or "decimal" in data_type:
            rules.append({
                "issue_type": "validity",
                "rule_type": "validity",
                "rule_name": "数值范围检查",
                "config_template": {
                    "min_value": None,
                    "max_value": None,
                    "action": "validate"
                }
            })
        elif "date" in data_type or "time" in data_type:
            rules.append({
                "issue_type": "validity",
                "rule_type": "validity",
                "rule_name": "日期格式检查",
                "config_template": {
                    "format": "YYYY-MM-DD",
                    "action": "validate"
                }
            })
        elif "bool" in data_type:
            rules.append({
                "issue_type": "validity",
                "rule_type": "validity",
                "rule_name": "布尔值检查",
                "config_template": {
                    "allowed_values": [True, False, 0, 1, "true", "false"],
                    "action": "validate"
                }
            })

        return rules

    def _detect_anomalies_in_samples(
        self,
        column_name: str,
        samples: List[Any]
    ) -> List[CleaningRecommendation]:
        """在样本数据中检测异常"""
        recommendations = []

        if not samples:
            return recommendations

        # 检测空字符串
        empty_count = sum(1 for s in samples if s == "" or s is None)
        if empty_count > len(samples) * 0.1:  # 超过10%为空
            recommendations.append(CleaningRecommendation(
                issue_type="missing_values",
                issue_description=f"列 {column_name} 有 {empty_count}/{len(samples)} 空值",
                rule_type="completeness",
                rule_name=f"{column_name}_空值处理",
                rule_config={
                    "target_column": column_name,
                    "action": "fill",
                    "fill_strategy": "default",
                    "default_value": ""
                },
                priority="medium",
                estimated_improvement=0.15
            ))

        # 检测数据类型不一致
        types = set(type(s).__name__ for s in samples if s is not None)
        if len(types) > 2:
            recommendations.append(CleaningRecommendation(
                issue_type="inconsistent_values",
                issue_description=f"列 {column_name} 数据类型不一致: {types}",
                rule_type="consistency",
                rule_name=f"{column_name}_类型标准化",
                rule_config={
                    "target_column": column_name,
                    "action": "standardize",
                    "target_type": "string"
                },
                priority="high",
                estimated_improvement=0.25
            ))

        return recommendations

    def _create_kettle_step(self, rec: CleaningRecommendation) -> Optional[Dict]:
        """创建 Kettle 步骤配置"""
        step_type = self._map_rule_to_kettle_step(rec.rule_type, rec.rule_config.get("action", ""))

        if not step_type:
            return None

        return {
            "step_type": step_type,
            "name": rec.rule_name,
            "config": rec.rule_config,
            "priority": rec.priority
        }

    def _map_rule_to_kettle_step(self, rule_type: str, action: str) -> Optional[str]:
        """将规则类型映射到 Kettle 步骤类型"""
        mapping = {
            ("completeness", "fill"): "ValueMapper",
            ("completeness", "replace"): "Calculator",
            ("validity", "validate"): "Validator",
            ("validity", "clean"): "StringOperations",
            ("consistency", "standardize"): "Normaliser",
            ("consistency", "map"): "ValueMapper",
            ("accuracy", "trim"): "StringOperations",
            ("security", "mask"): "Mask",
        }

        return mapping.get((rule_type, action))

    # ==================== 模式检测器 ====================

    def _detect_phone_pattern(self, value: str) -> bool:
        """检测是否为电话号码模式"""
        import re
        return bool(re.match(r'^1[3-9]\d{9}$', str(value)))

    def _detect_email_pattern(self, value: str) -> bool:
        """检测是否为邮箱模式"""
        import re
        return bool(re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', str(value)))

    def _detect_id_card_pattern(self, value: str) -> bool:
        """检测是否为身份证模式"""
        import re
        return bool(re.match(r'^[1-9]\d{5}(18|19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{3}[0-9Xx]$', str(value)))

    def _detect_date_pattern(self, value: str) -> bool:
        """检测是否为日期模式"""
        import re
        return bool(re.match(r'^\d{4}-\d{2}-\d{2}$', str(value)) or re.match(r'^\d{4}/\d{2}/\d{2}$', str(value)))

    def _detect_numeric_pattern(self, value: str) -> bool:
        """检测是否为数值模式"""
        try:
            float(value)
            return True
        except (ValueError, TypeError):
            return False


# 创建全局服务实例
_ai_cleaning_advisor = None


def get_ai_cleaning_advisor() -> AICleaningAdvisor:
    """获取 AI 清洗建议服务实例"""
    global _ai_cleaning_advisor
    if _ai_cleaning_advisor is None:
        _ai_cleaning_advisor = AICleaningAdvisor()
    return _ai_cleaning_advisor
