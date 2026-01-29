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


    # ==================== SQL 执行逻辑 ====================

    def generate_cleaning_sql(
        self,
        recommendation: CleaningRecommendation,
        database_name: Optional[str] = None
    ) -> Dict[str, str]:
        """
        根据清洗规则建议生成可执行的 SQL 语句

        Args:
            recommendation: 清洗规则建议
            database_name: 数据库名

        Returns:
            包含 preview_sql、execute_sql、rollback_info 的字典
        """
        config = recommendation.rule_config
        table = config.get("target_table", "")
        column = config.get("target_column", "")
        action = config.get("action", "")

        if not table or not column:
            return {"error": "缺少目标表或目标列信息"}

        full_table = f"{database_name}.{table}" if database_name else table

        # 生成预览 SQL（SELECT 查询，查看受影响的行）
        preview_sql = ""
        execute_sql = ""

        if action == "fill" or action == "replace":
            fill_strategy = config.get("fill_strategy", "default")
            default_value = config.get("default_value", "")

            if fill_strategy == "mean":
                preview_sql = (
                    f"SELECT COUNT(*) AS affected_rows, "
                    f"AVG({column}) AS fill_value "
                    f"FROM {full_table} WHERE {column} IS NULL"
                )
                execute_sql = (
                    f"UPDATE {full_table} SET {column} = ("
                    f"SELECT avg_val FROM (SELECT AVG({column}) AS avg_val FROM {full_table}) t"
                    f") WHERE {column} IS NULL"
                )
            elif fill_strategy == "mode":
                preview_sql = (
                    f"SELECT COUNT(*) AS affected_rows "
                    f"FROM {full_table} WHERE {column} IS NULL"
                )
                execute_sql = (
                    f"UPDATE {full_table} SET {column} = ("
                    f"SELECT {column} FROM {full_table} "
                    f"WHERE {column} IS NOT NULL "
                    f"GROUP BY {column} ORDER BY COUNT(*) DESC LIMIT 1"
                    f") WHERE {column} IS NULL"
                )
            elif fill_strategy == "interpolate":
                preview_sql = (
                    f"SELECT COUNT(*) AS affected_rows "
                    f"FROM {full_table} WHERE {column} IS NULL"
                )
                # 日期插值使用当前时间
                execute_sql = (
                    f"UPDATE {full_table} SET {column} = NOW() "
                    f"WHERE {column} IS NULL"
                )
            else:
                # default 策略
                escaped_val = str(default_value).replace("'", "''") if default_value else ""
                preview_sql = (
                    f"SELECT COUNT(*) AS affected_rows "
                    f"FROM {full_table} WHERE {column} IS NULL"
                )
                execute_sql = (
                    f"UPDATE {full_table} SET {column} = '{escaped_val}' "
                    f"WHERE {column} IS NULL"
                )

        elif action == "trim":
            preview_sql = (
                f"SELECT COUNT(*) AS affected_rows "
                f"FROM {full_table} WHERE {column} != TRIM({column})"
            )
            execute_sql = (
                f"UPDATE {full_table} SET {column} = TRIM({column}) "
                f"WHERE {column} != TRIM({column})"
            )

        elif action == "remove_special_chars":
            preview_sql = (
                f"SELECT COUNT(*) AS affected_rows "
                f"FROM {full_table} WHERE {column} REGEXP '[^a-zA-Z0-9\\\\s\\\\u4e00-\\\\u9fff]'"
            )
            execute_sql = (
                f"UPDATE {full_table} SET {column} = REGEXP_REPLACE({column}, "
                f"'[^a-zA-Z0-9 \\u4e00-\\u9fff]', '') "
                f"WHERE {column} REGEXP '[^a-zA-Z0-9 \\u4e00-\\u9fff]'"
            )

        elif action == "deduplicate":
            preview_sql = (
                f"SELECT {column}, COUNT(*) AS dup_count "
                f"FROM {full_table} "
                f"GROUP BY {column} HAVING COUNT(*) > 1 "
                f"ORDER BY dup_count DESC LIMIT 20"
            )
            timestamp_col = config.get("timestamp_column", "updated_at")
            execute_sql = (
                f"DELETE t1 FROM {full_table} t1 "
                f"INNER JOIN {full_table} t2 "
                f"WHERE t1.{column} = t2.{column} "
                f"AND t1.{timestamp_col} < t2.{timestamp_col}"
            )

        elif action == "keep_latest":
            timestamp_col = config.get("timestamp_column", "updated_at")
            preview_sql = (
                f"SELECT {column}, COUNT(*) AS dup_count "
                f"FROM {full_table} "
                f"GROUP BY {column} HAVING COUNT(*) > 1"
            )
            execute_sql = (
                f"DELETE t1 FROM {full_table} t1 "
                f"INNER JOIN {full_table} t2 "
                f"WHERE t1.{column} = t2.{column} "
                f"AND t1.{timestamp_col} < t2.{timestamp_col}"
            )

        elif action == "validate":
            pattern = config.get("pattern", "")
            if pattern:
                escaped_pattern = pattern.replace("'", "''")
                preview_sql = (
                    f"SELECT COUNT(*) AS invalid_count "
                    f"FROM {full_table} "
                    f"WHERE {column} IS NOT NULL "
                    f"AND {column} NOT REGEXP '{escaped_pattern}'"
                )
                execute_sql = ""  # 验证规则不执行修改

        elif action == "clip":
            min_val = config.get("min_value")
            max_val = config.get("max_value")
            conditions = []
            updates = []
            if min_val is not None:
                conditions.append(f"{column} < {min_val}")
                updates.append(f"WHEN {column} < {min_val} THEN {min_val}")
            if max_val is not None:
                conditions.append(f"{column} > {max_val}")
                updates.append(f"WHEN {column} > {max_val} THEN {max_val}")

            if conditions:
                preview_sql = (
                    f"SELECT COUNT(*) AS affected_rows "
                    f"FROM {full_table} WHERE {' OR '.join(conditions)}"
                )
                execute_sql = (
                    f"UPDATE {full_table} SET {column} = CASE "
                    f"{' '.join(updates)} ELSE {column} END "
                    f"WHERE {' OR '.join(conditions)}"
                )

        elif action == "standardize":
            standard_type = config.get("standard_type", "case")
            if standard_type == "case":
                preview_sql = (
                    f"SELECT COUNT(*) AS affected_rows "
                    f"FROM {full_table} WHERE {column} != LOWER(TRIM({column}))"
                )
                execute_sql = (
                    f"UPDATE {full_table} SET {column} = LOWER(TRIM({column})) "
                    f"WHERE {column} != LOWER(TRIM({column}))"
                )
            elif standard_type == "trim":
                preview_sql = (
                    f"SELECT COUNT(*) AS affected_rows "
                    f"FROM {full_table} WHERE {column} != TRIM({column})"
                )
                execute_sql = (
                    f"UPDATE {full_table} SET {column} = TRIM({column}) "
                    f"WHERE {column} != TRIM({column})"
                )

        elif action == "map":
            mapping_dict = config.get("mapping_dict", {})
            if mapping_dict:
                case_parts = []
                for old_val, new_val in mapping_dict.items():
                    escaped_old = str(old_val).replace("'", "''")
                    escaped_new = str(new_val).replace("'", "''")
                    case_parts.append(f"WHEN '{escaped_old}' THEN '{escaped_new}'")

                old_values = ", ".join(
                    f"'{str(v).replace(chr(39), chr(39)+chr(39))}'" for v in mapping_dict.keys()
                )
                preview_sql = (
                    f"SELECT {column}, COUNT(*) AS cnt "
                    f"FROM {full_table} WHERE {column} IN ({old_values}) "
                    f"GROUP BY {column}"
                )
                execute_sql = (
                    f"UPDATE {full_table} SET {column} = CASE {column} "
                    f"{' '.join(case_parts)} ELSE {column} END "
                    f"WHERE {column} IN ({old_values})"
                )

        elif action == "mask":
            mask_type = config.get("mask_type", "partial")
            if mask_type == "phone_mask":
                preview_sql = (
                    f"SELECT COUNT(*) AS affected_rows "
                    f"FROM {full_table} WHERE {column} IS NOT NULL AND LENGTH({column}) >= 7"
                )
                execute_sql = (
                    f"UPDATE {full_table} SET {column} = CONCAT("
                    f"LEFT({column}, 3), '****', RIGHT({column}, 4)"
                    f") WHERE {column} IS NOT NULL AND LENGTH({column}) >= 7"
                )
            elif mask_type == "email_mask":
                preview_sql = (
                    f"SELECT COUNT(*) AS affected_rows "
                    f"FROM {full_table} WHERE {column} LIKE '%@%'"
                )
                execute_sql = (
                    f"UPDATE {full_table} SET {column} = CONCAT("
                    f"LEFT({column}, 1), '***@', "
                    f"SUBSTRING_INDEX({column}, '@', -1)"
                    f") WHERE {column} LIKE '%@%'"
                )
            elif mask_type == "id_mask":
                preview_sql = (
                    f"SELECT COUNT(*) AS affected_rows "
                    f"FROM {full_table} WHERE {column} IS NOT NULL AND LENGTH({column}) >= 10"
                )
                execute_sql = (
                    f"UPDATE {full_table} SET {column} = CONCAT("
                    f"LEFT({column}, 6), '********', RIGHT({column}, 4)"
                    f") WHERE {column} IS NOT NULL AND LENGTH({column}) >= 10"
                )
            elif mask_type == "name_mask":
                preview_sql = (
                    f"SELECT COUNT(*) AS affected_rows "
                    f"FROM {full_table} WHERE {column} IS NOT NULL AND LENGTH({column}) >= 2"
                )
                execute_sql = (
                    f"UPDATE {full_table} SET {column} = CONCAT("
                    f"LEFT({column}, 1), REPEAT('*', LENGTH({column}) - 1)"
                    f") WHERE {column} IS NOT NULL AND LENGTH({column}) >= 2"
                )
            else:
                # partial mask: 保留首尾字符
                preview_sql = (
                    f"SELECT COUNT(*) AS affected_rows "
                    f"FROM {full_table} WHERE {column} IS NOT NULL AND LENGTH({column}) >= 3"
                )
                execute_sql = (
                    f"UPDATE {full_table} SET {column} = CONCAT("
                    f"LEFT({column}, 1), REPEAT('*', LENGTH({column}) - 2), RIGHT({column}, 1)"
                    f") WHERE {column} IS NOT NULL AND LENGTH({column}) >= 3"
                )

        if not preview_sql:
            return {
                "error": f"不支持的清洗动作: {action}",
                "action": action,
                "rule_type": recommendation.rule_type,
            }

        return {
            "preview_sql": preview_sql,
            "execute_sql": execute_sql,
            "action": action,
            "target_table": full_table,
            "target_column": column,
            "rule_name": recommendation.rule_name,
        }

    def preview_cleaning(
        self,
        db: Session,
        recommendation: CleaningRecommendation,
        database_name: Optional[str] = None,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        预览清洗操作将影响的数据（dry run）

        Args:
            db: 数据库会话
            recommendation: 清洗规则建议
            database_name: 数据库名
            limit: 预览行数

        Returns:
            预览结果，包含受影响行数和样本数据
        """
        sql_info = self.generate_cleaning_sql(recommendation, database_name)

        if "error" in sql_info:
            return sql_info

        preview_sql = sql_info.get("preview_sql", "")
        if not preview_sql:
            return {"error": "无法生成预览 SQL"}

        try:
            # 添加 LIMIT
            if "LIMIT" not in preview_sql.upper():
                preview_sql = f"{preview_sql} LIMIT {limit}"

            result = db.execute(text(preview_sql))
            rows = result.fetchall()
            columns = result.keys() if hasattr(result, 'keys') else []

            # 转换为字典列表
            preview_data = []
            for row in rows:
                if hasattr(row, '_mapping'):
                    preview_data.append(dict(row._mapping))
                elif hasattr(row, 'keys'):
                    preview_data.append(dict(row))
                else:
                    preview_data.append({str(i): v for i, v in enumerate(row)})

            return {
                "success": True,
                "preview_data": preview_data,
                "row_count": len(preview_data),
                "sql": preview_sql,
                "execute_sql": sql_info.get("execute_sql", ""),
                "rule_name": sql_info.get("rule_name", ""),
                "action": sql_info.get("action", ""),
                "target_table": sql_info.get("target_table", ""),
                "target_column": sql_info.get("target_column", ""),
            }

        except Exception as e:
            logger.error(f"清洗预览失败: {e}")
            return {
                "success": False,
                "error": f"预览失败: {str(e)}",
                "sql": preview_sql,
            }

    def execute_cleaning_rule(
        self,
        db: Session,
        recommendation: CleaningRecommendation,
        database_name: Optional[str] = None,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        执行清洗规则

        Args:
            db: 数据库会话
            recommendation: 清洗规则建议
            database_name: 数据库名
            dry_run: 是否仅预览不执行

        Returns:
            执行结果
        """
        if dry_run:
            return self.preview_cleaning(db, recommendation, database_name)

        sql_info = self.generate_cleaning_sql(recommendation, database_name)

        if "error" in sql_info:
            return sql_info

        execute_sql = sql_info.get("execute_sql", "")
        if not execute_sql:
            return {
                "success": True,
                "message": "此规则为验证规则，无需执行修改操作",
                "action": sql_info.get("action", ""),
            }

        try:
            # 先获取受影响行数
            preview_result = self.preview_cleaning(db, recommendation, database_name)
            affected_estimate = preview_result.get("row_count", 0) if preview_result.get("success") else 0

            # 执行清洗 SQL
            result = db.execute(text(execute_sql))
            db.commit()

            affected_rows = result.rowcount if hasattr(result, 'rowcount') else 0

            logger.info(
                f"清洗规则执行成功: {recommendation.rule_name}, "
                f"影响行数: {affected_rows}"
            )

            return {
                "success": True,
                "rule_name": sql_info.get("rule_name", ""),
                "action": sql_info.get("action", ""),
                "target_table": sql_info.get("target_table", ""),
                "target_column": sql_info.get("target_column", ""),
                "affected_rows": affected_rows,
                "affected_estimate": affected_estimate,
                "execute_sql": execute_sql,
            }

        except Exception as e:
            db.rollback()
            logger.error(f"清洗规则执行失败: {e}")
            return {
                "success": False,
                "error": f"执行失败: {str(e)}",
                "execute_sql": execute_sql,
            }

    def batch_execute_cleaning(
        self,
        db: Session,
        recommendations: List[CleaningRecommendation],
        database_name: Optional[str] = None,
        dry_run: bool = False,
        stop_on_error: bool = True
    ) -> Dict[str, Any]:
        """
        批量执行清洗规则

        Args:
            db: 数据库会话
            recommendations: 清洗规则列表
            database_name: 数据库名
            dry_run: 是否仅预览
            stop_on_error: 出错时是否停止

        Returns:
            批量执行结果
        """
        results = []
        total_affected = 0
        errors = []

        for i, rec in enumerate(recommendations):
            result = self.execute_cleaning_rule(db, rec, database_name, dry_run)
            results.append({
                "index": i,
                "rule_name": rec.rule_name,
                "priority": rec.priority,
                "result": result,
            })

            if result.get("success"):
                total_affected += result.get("affected_rows", 0)
            else:
                errors.append({
                    "index": i,
                    "rule_name": rec.rule_name,
                    "error": result.get("error", ""),
                })
                if stop_on_error:
                    break

        return {
            "success": len(errors) == 0,
            "total_rules": len(recommendations),
            "executed": len(results),
            "total_affected_rows": total_affected,
            "errors": errors,
            "results": results,
            "dry_run": dry_run,
        }


# 创建全局服务实例
_ai_cleaning_advisor = None


def get_ai_cleaning_advisor() -> AICleaningAdvisor:
    """获取 AI 清洗建议服务实例"""
    global _ai_cleaning_advisor
    if _ai_cleaning_advisor is None:
        _ai_cleaning_advisor = AICleaningAdvisor()
    return _ai_cleaning_advisor
