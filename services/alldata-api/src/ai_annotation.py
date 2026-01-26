"""
AI 元数据标注服务
Phase 1 P1: 元数据自动标注、敏感字段识别

功能：
- 自动生成列描述
- 敏感字段识别 (PII, 财务, 健康, 凭证)
- 语义标签生成
"""

import json
import logging
import os
import re
import requests
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger(__name__)

# 配置
CUBE_API_URL = os.getenv("CUBE_API_URL", "http://openai-proxy:8000")
AI_ANNOTATION_MODEL = os.getenv("AI_ANNOTATION_MODEL", "gpt-4o-mini")
AI_ANNOTATION_ENABLED = os.getenv("AI_ANNOTATION_ENABLED", "true").lower() in ("true", "1", "yes")

# 敏感字段模式 (基于规则的快速检测)
SENSITIVITY_PATTERNS = {
    "pii": {
        "patterns": [
            r"(姓名|name|full_?name|real_?name)",
            r"(身份证|id_?card|identity|ssn|social_?security)",
            r"(手机|phone|mobile|tel|telephone)",
            r"(邮箱|email|e_?mail)",
            r"(地址|address|addr|location|住址)",
            r"(生日|birthday|birth_?date|dob|出生)",
            r"(性别|gender|sex)",
            r"(民族|ethnicity|race)",
            r"(护照|passport)",
            r"(驾照|driver_?license)",
        ],
        "level": "confidential",
    },
    "financial": {
        "patterns": [
            r"(银行卡|bank_?card|card_?no|card_?number)",
            r"(账户|account|account_?no|account_?number)",
            r"(余额|balance|amount|金额)",
            r"(工资|salary|wage|income|收入)",
            r"(交易|transaction|payment|支付)",
            r"(信用卡|credit_?card)",
            r"(cvv|cvc|安全码)",
        ],
        "level": "restricted",
    },
    "health": {
        "patterns": [
            r"(病历|medical_?record|health_?record)",
            r"(诊断|diagnosis|disease|疾病)",
            r"(处方|prescription|medication|药物)",
            r"(血型|blood_?type)",
            r"(过敏|allergy|allergies)",
            r"(病史|medical_?history)",
        ],
        "level": "restricted",
    },
    "credential": {
        "patterns": [
            r"(密码|password|passwd|pwd)",
            r"(密钥|secret|key|api_?key)",
            r"(token|access_?token|refresh_?token)",
            r"(证书|certificate|cert)",
            r"(私钥|private_?key)",
        ],
        "level": "restricted",
    },
}

# 语义标签映射
SEMANTIC_TAG_KEYWORDS = {
    "identifier": ["id", "uuid", "guid", "key", "code", "no", "number", "编号", "标识"],
    "timestamp": ["time", "date", "created", "updated", "modified", "timestamp", "时间", "日期"],
    "status": ["status", "state", "flag", "is_", "has_", "状态", "标志"],
    "amount": ["amount", "price", "cost", "fee", "total", "sum", "金额", "价格", "费用"],
    "count": ["count", "num", "qty", "quantity", "数量", "计数"],
    "description": ["desc", "description", "remark", "note", "comment", "描述", "备注"],
    "name": ["name", "title", "label", "名称", "标题"],
    "category": ["type", "category", "class", "kind", "类型", "分类"],
    "foreign_key": ["_id", "ref_", "fk_", "parent_", "外键"],
}


class AIAnnotationService:
    """AI 元数据标注服务"""

    def __init__(self, api_url: str = None):
        """
        初始化服务

        Args:
            api_url: LLM API 地址
        """
        self.api_url = api_url or CUBE_API_URL
        self.model = AI_ANNOTATION_MODEL
        self.enabled = AI_ANNOTATION_ENABLED

    def annotate_column(
        self,
        column_name: str,
        column_type: str,
        table_name: str = None,
        sample_values: List[Any] = None,
        use_llm: bool = True,
    ) -> Dict[str, Any]:
        """
        标注单个列

        Args:
            column_name: 列名
            column_type: 列类型
            table_name: 表名（可选，提供更多上下文）
            sample_values: 样本值（可选，用于更准确的推断）
            use_llm: 是否使用 LLM（False 时仅使用规则）

        Returns:
            标注结果字典
        """
        result = {
            "column_name": column_name,
            "ai_description": None,
            "sensitivity_level": "public",
            "sensitivity_type": "none",
            "semantic_tags": [],
            "ai_confidence": 0,
            "annotated_at": datetime.utcnow().isoformat(),
        }

        # 1. 基于规则的敏感字段检测（快速且可靠）
        sensitivity_result = self._detect_sensitivity_by_rules(column_name)
        if sensitivity_result:
            result["sensitivity_type"] = sensitivity_result["type"]
            result["sensitivity_level"] = sensitivity_result["level"]
            result["ai_confidence"] = max(result["ai_confidence"], 80)

        # 2. 基于规则的语义标签
        semantic_tags = self._detect_semantic_tags(column_name)
        result["semantic_tags"] = semantic_tags
        if semantic_tags:
            result["ai_confidence"] = max(result["ai_confidence"], 70)

        # 3. 使用 LLM 增强（如果启用）
        if use_llm and self.enabled:
            try:
                llm_result = self._annotate_with_llm(
                    column_name, column_type, table_name, sample_values
                )
                if llm_result:
                    # 合并 LLM 结果
                    if llm_result.get("ai_description"):
                        result["ai_description"] = llm_result["ai_description"]
                    if llm_result.get("sensitivity_type") and llm_result["sensitivity_type"] != "none":
                        # LLM 检测到敏感字段，使用更高置信度的结果
                        if result["sensitivity_type"] == "none" or llm_result.get("confidence", 0) > 80:
                            result["sensitivity_type"] = llm_result["sensitivity_type"]
                            result["sensitivity_level"] = llm_result.get("sensitivity_level", "confidential")
                    if llm_result.get("semantic_tags"):
                        # 合并标签，去重
                        result["semantic_tags"] = list(set(result["semantic_tags"] + llm_result["semantic_tags"]))
                    result["ai_confidence"] = max(result["ai_confidence"], llm_result.get("confidence", 85))
            except Exception as e:
                logger.warning(f"LLM 标注失败，使用规则结果: {e}")

        # 4. 如果没有 LLM 描述，生成简单描述
        if not result["ai_description"]:
            result["ai_description"] = self._generate_simple_description(
                column_name, column_type, result["semantic_tags"]
            )

        return result

    def annotate_table(
        self,
        table_name: str,
        columns: List[Dict[str, Any]],
        sample_data: List[Dict[str, Any]] = None,
        use_llm: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        批量标注表的所有列

        Args:
            table_name: 表名
            columns: 列信息列表 [{"name": "col1", "type": "varchar"}, ...]
            sample_data: 样本数据（可选）
            use_llm: 是否使用 LLM

        Returns:
            标注结果列表
        """
        results = []
        for col in columns:
            col_name = col.get("name") or col.get("column_name")
            col_type = col.get("type") or col.get("column_type", "unknown")

            # 提取该列的样本值
            sample_values = None
            if sample_data:
                sample_values = [row.get(col_name) for row in sample_data[:5] if row.get(col_name)]

            result = self.annotate_column(
                column_name=col_name,
                column_type=col_type,
                table_name=table_name,
                sample_values=sample_values,
                use_llm=use_llm,
            )
            results.append(result)

        return results

    def _detect_sensitivity_by_rules(self, column_name: str) -> Optional[Dict[str, str]]:
        """
        基于规则检测敏感字段

        Returns:
            {"type": "pii", "level": "confidential"} or None
        """
        column_lower = column_name.lower()

        for sens_type, config in SENSITIVITY_PATTERNS.items():
            for pattern in config["patterns"]:
                if re.search(pattern, column_lower, re.IGNORECASE):
                    return {"type": sens_type, "level": config["level"]}

        return None

    def _detect_semantic_tags(self, column_name: str) -> List[str]:
        """
        基于关键词检测语义标签

        Returns:
            标签列表
        """
        tags = []
        column_lower = column_name.lower()

        for tag, keywords in SEMANTIC_TAG_KEYWORDS.items():
            for keyword in keywords:
                if keyword in column_lower:
                    tags.append(tag)
                    break

        return list(set(tags))

    def _annotate_with_llm(
        self,
        column_name: str,
        column_type: str,
        table_name: str = None,
        sample_values: List[Any] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        使用 LLM 进行标注

        Returns:
            LLM 标注结果或 None
        """
        # 构建 prompt
        context_parts = [f"列名: {column_name}", f"数据类型: {column_type}"]
        if table_name:
            context_parts.append(f"所属表: {table_name}")
        if sample_values:
            samples_str = ", ".join(str(v)[:50] for v in sample_values[:3])
            context_parts.append(f"样本值: {samples_str}")

        context = "\n".join(context_parts)

        prompt = f"""分析以下数据库列的元数据，返回 JSON 格式结果：

{context}

请分析并返回：
1. ai_description: 简短的列描述（20字以内）
2. sensitivity_type: 敏感类型，选择 pii/financial/health/credential/none
3. sensitivity_level: 敏感级别，选择 public/internal/confidential/restricted
4. semantic_tags: 语义标签数组（如 identifier, timestamp, amount 等）
5. confidence: 置信度 0-100

仅返回 JSON，不要其他文字："""

        try:
            response = requests.post(
                f"{self.api_url}/v1/chat/completions",
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": "你是数据治理专家，擅长分析数据库元数据。只返回 JSON 格式结果。"},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.1,
                    "max_tokens": 200,
                },
                timeout=10,
            )

            if response.status_code == 200:
                content = response.json()["choices"][0]["message"]["content"]
                # 解析 JSON
                # 尝试提取 JSON 块
                json_match = re.search(r'\{[\s\S]*\}', content)
                if json_match:
                    return json.loads(json_match.group())
            else:
                logger.warning(f"LLM API 返回错误: {response.status_code}")

        except json.JSONDecodeError as e:
            logger.warning(f"LLM 返回解析失败: {e}")
        except requests.exceptions.RequestException as e:
            logger.warning(f"LLM API 请求失败: {e}")
        except Exception as e:
            logger.warning(f"LLM 标注异常: {e}")

        return None

    def _generate_simple_description(
        self,
        column_name: str,
        column_type: str,
        semantic_tags: List[str],
    ) -> str:
        """
        生成简单的列描述（无 LLM 时使用）
        """
        # 清理列名
        clean_name = re.sub(r'[_\-]', ' ', column_name)

        # 基于语义标签生成描述
        tag_descriptions = {
            "identifier": "唯一标识",
            "timestamp": "时间戳",
            "status": "状态标志",
            "amount": "金额数值",
            "count": "数量计数",
            "description": "描述信息",
            "name": "名称",
            "category": "类型分类",
            "foreign_key": "外键关联",
        }

        if semantic_tags:
            tag_desc = tag_descriptions.get(semantic_tags[0], "")
            if tag_desc:
                return f"{clean_name} - {tag_desc}"

        return f"{clean_name}"

    def get_sensitivity_report(
        self,
        annotations: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        生成敏感字段报告

        Args:
            annotations: 标注结果列表

        Returns:
            敏感字段统计报告
        """
        report = {
            "total_columns": len(annotations),
            "sensitive_columns": 0,
            "by_type": {
                "pii": [],
                "financial": [],
                "health": [],
                "credential": [],
            },
            "by_level": {
                "public": 0,
                "internal": 0,
                "confidential": 0,
                "restricted": 0,
            },
            "high_risk_columns": [],
        }

        for ann in annotations:
            sens_type = ann.get("sensitivity_type", "none")
            sens_level = ann.get("sensitivity_level", "public")

            if sens_type != "none":
                report["sensitive_columns"] += 1
                if sens_type in report["by_type"]:
                    report["by_type"][sens_type].append(ann["column_name"])

            if sens_level in report["by_level"]:
                report["by_level"][sens_level] += 1

            # 高风险列（restricted 级别或 credential 类型）
            if sens_level == "restricted" or sens_type == "credential":
                report["high_risk_columns"].append({
                    "column": ann["column_name"],
                    "type": sens_type,
                    "level": sens_level,
                })

        return report


# 创建全局实例
_ai_annotation_service: Optional[AIAnnotationService] = None


def get_ai_annotation_service() -> AIAnnotationService:
    """获取 AI 标注服务单例"""
    global _ai_annotation_service
    if _ai_annotation_service is None:
        _ai_annotation_service = AIAnnotationService()
    return _ai_annotation_service
