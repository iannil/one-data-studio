"""
数据验证器
验证提取的数据质量和准确性
"""

import re
import logging
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime
from decimal import Decimal

logger = logging.getLogger(__name__)


class DataValidator:
    """数据验证器"""

    # 常用验证正则表达式
    PATTERNS = {
        # 中国身份证号 (18位)
        "id_card_cn": r"^[1-9]\d{5}(18|19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{3}[\dXx]$",
        # 手机号
        "phone_cn": r"^1[3-9]\d{9}$",
        # 邮箱
        "email": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
        # 统一社会信用代码
        "credit_code": r"^[0-9A-HJ-NPQRTUWXY]{2}\d{6}[0-9A-HJ-NPQRTUWXY]{10}$",
        # 银行卡号
        "bank_card": r"^\d{16,19}$",
        # 发票号码
        "invoice_number": r"^\d{8,20}$",
        # 日期 YYYY-MM-DD
        "date": r"^\d{4}-\d{2}-\d{2}$",
        # 金额 (支持小数)
        "amount": r"^\d+(\.\d{1,2})?$",
    }

    def __init__(self):
        self._compiled_patterns = {
            key: re.compile(pattern) for key, pattern in self.PATTERNS.items()
        }

    def validate_field(self, field_name: str, value: Any, validation_rules: Dict) -> Tuple[bool, str, Any]:
        """
        验证单个字段

        返回: (是否有效, 错误信息, 标准化后的值)
        """
        if value is None:
            if validation_rules.get("required", False):
                return False, f"{field_name}不能为空", None
            return True, "", None

        value_type = validation_rules.get("type", "string")

        # 类型验证
        if value_type == "string":
            return self._validate_string(field_name, value, validation_rules)
        elif value_type == "number":
            return self._validate_number(field_name, value, validation_rules)
        elif value_type == "date":
            return self._validate_date(field_name, value, validation_rules)
        elif value_type == "email":
            return self._validate_email(field_name, value, validation_rules)
        elif value_type == "phone":
            return self._validate_phone(field_name, value, validation_rules)
        elif value_type == "id_card":
            return self._validate_id_card(field_name, value, validation_rules)
        elif value_type == "credit_code":
            return self._validate_credit_code(field_name, value, validation_rules)
        elif value_type == "invoice_number":
            return self._validate_invoice_number(field_name, value, validation_rules)
        else:
            return True, "", value

    def _validate_string(self, field_name: str, value: Any, rules: Dict) -> Tuple[bool, str, Any]:
        """验证字符串类型"""
        value_str = str(value).strip()

        # 长度验证
        min_length = rules.get("min_length")
        max_length = rules.get("max_length")

        if min_length and len(value_str) < min_length:
            return False, f"{field_name}长度不能少于{min_length}个字符", value_str
        if max_length and len(value_str) > max_length:
            return False, f"{field_name}长度不能超过{max_length}个字符", value_str

        # 正则验证
        pattern = rules.get("pattern")
        if pattern:
            if not re.match(pattern, value_str):
                return False, f"{field_name}格式不正确", value_str

        return True, "", value_str

    def _validate_number(self, field_name: str, value: Any, rules: Dict) -> Tuple[bool, str, Any]:
        """验证数字类型"""
        try:
            # 清理金额格式
            if isinstance(value, str):
                # 移除千分位逗号和货币符号
                value_str = value.replace(",", "").replace("¥", "").replace("$", "").strip()
                num_value = Decimal(value_str)
            else:
                num_value = Decimal(str(value))

            # 范围验证
            min_value = rules.get("min_value")
            max_value = rules.get("max_value")

            if min_value is not None and num_value < Decimal(str(min_value)):
                return False, f"{field_name}不能小于{min_value}", float(num_value)
            if max_value is not None and num_value > Decimal(str(max_value)):
                return False, f"{field_name}不能大于{max_value}", float(num_value)

            return True, "", float(num_value)

        except (ValueError, TypeError):
            return False, f"{field_name}必须是有效数字", value

    def _validate_date(self, field_name: str, value: Any, rules: Dict) -> Tuple[bool, str, Any]:
        """验证日期类型"""
        value_str = str(value).strip()

        # 尝试多种日期格式
        date_formats = rules.get("formats", ["%Y-%m-%d", "%Y/%m/%d", "%Y年%m月%d日", "%Y%m%d"])

        for fmt in date_formats:
            try:
                parsed_date = datetime.strptime(value_str, fmt)
                # 标准化为 YYYY-MM-DD 格式
                return True, "", parsed_date.strftime("%Y-%m-%d")
            except ValueError:
                continue

        return False, f"{field_name}日期格式不正确", value_str

    def _validate_email(self, field_name: str, value: Any, rules: Dict) -> Tuple[bool, str, Any]:
        """验证邮箱"""
        value_str = str(value).strip()

        if not self._compiled_patterns["email"].match(value_str):
            return False, f"{field_name}邮箱格式不正确", value_str

        return True, "", value_str.lower()

    def _validate_phone(self, field_name: str, value: Any, rules: Dict) -> Tuple[bool, str, Any]:
        """验证手机号"""
        value_str = str(value).strip()

        # 清理可能的分隔符
        value_str = value_str.replace("-", "").replace(" ", "")

        if not self._compiled_patterns["phone_cn"].match(value_str):
            return False, f"{field_name}手机号格式不正确", value_str

        return True, "", value_str

    def _validate_id_card(self, field_name: str, value: Any, rules: Dict) -> Tuple[bool, str, Any]:
        """验证身份证号"""
        value_str = str(value).strip()

        if not self._compiled_patterns["id_card_cn"].match(value_str):
            return False, f"{field_name}身份证号格式不正确", value_str

        # 验证校验码
        if not self._validate_id_card_checksum(value_str):
            return False, f"{field_name}身份证号校验码不正确", value_str

        return True, "", value_str.upper()

    def _validate_id_card_checksum(self, id_card: str) -> bool:
        """验证18位身份证校验码"""
        if len(id_card) != 18:
            return False

        # 权重因子
        weights = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2]
        # 校验码对应值
        checksum_map = "10X98765432"

        total = 0
        for i in range(17):
            total += int(id_card[i]) * weights[i]

        checksum = checksum_map[total % 11]
        return id_card[-1].upper() == checksum

    def _validate_credit_code(self, field_name: str, value: Any, rules: Dict) -> Tuple[bool, str, Any]:
        """验证统一社会信用代码"""
        value_str = str(value).strip().upper()

        if not self._compiled_patterns["credit_code"].match(value_str):
            return False, f"{field_name}统一社会信用代码格式不正确", value_str

        # TODO: 可以添加校验码验证

        return True, "", value_str

    def _validate_invoice_number(self, field_name: str, value: Any, rules: Dict) -> Tuple[bool, str, Any]:
        """验证发票号码"""
        value_str = str(value).strip()

        if not self._compiled_patterns["invoice_number"].match(value_str):
            return False, f"{field_name}发票号码格式不正确", value_str

        return True, "", value_str

    def validate_extraction_result(
        self,
        extracted_data: Dict[str, Any],
        template: Dict
    ) -> Tuple[bool, List[Dict], float]:
        """
        验证完整的提取结果

        返回: (是否有效, 验证问题列表, 总体置信度)
        """
        issues = []
        total_confidence = 0.0
        field_count = 0

        fields = template.get("fields", [])

        for field_def in fields:
            field_key = field_def.get("key")
            field_name = field_def.get("name", field_key)

            if not field_key:
                continue

            value = extracted_data.get(field_key)
            validation_rules = field_def.get("validation", {})

            # 如果没有定义validation规则，使用类型推断
            if not validation_rules:
                validation_rules = self._infer_validation_rules(field_def, value)

            is_valid, error_msg, normalized_value = self.validate_field(
                field_name, value, validation_rules
            )

            if not is_valid:
                issues.append({
                    "field": field_name,
                    "key": field_key,
                    "error": error_msg,
                    "value": value,
                    "severity": "error" if field_def.get("required", False) else "warning"
                })
            elif normalized_value != value and normalized_value is not None:
                # 记录标准化变化
                issues.append({
                    "field": field_name,
                    "key": field_key,
                    "type": "normalized",
                    "original": value,
                    "normalized": normalized_value
                })
                extracted_data[field_key] = normalized_value

            # 计算置信度
            if value is not None:
                field_confidence = field_def.get("confidence", 0.8)
                total_confidence += field_confidence
                field_count += 1
            elif field_def.get("required", False):
                # 缺少必填字段，降低置信度
                total_confidence += 0.0
                field_count += 1

        overall_confidence = total_confidence / field_count if field_count > 0 else 0.0

        return len(issues) == 0, issues, overall_confidence

    def _infer_validation_rules(self, field_def: Dict, value: Any) -> Dict:
        """根据字段定义和值推断验证规则"""
        rules = {}

        field_name = field_def.get("name", "").lower()
        field_key = field_def.get("key", "").lower()

        # 根据字段名推断类型
        if any(kw in field_name or kw in field_key for kw in ["日期", "date", "时间"]):
            rules["type"] = "date"
        elif any(kw in field_name or kw in field_key for kw in ["金额", "amount", "价格", "price", "数量", "quantity"]):
            rules["type"] = "number"
        elif any(kw in field_name or kw in field_key for kw in ["邮箱", "email", "邮件"]):
            rules["type"] = "email"
        elif any(kw in field_name or kw in field_key for kw in ["手机", "电话", "phone", "mobile"]):
            rules["type"] = "phone"
        elif any(kw in field_name or kw in field_key for kw in ["身份证", "id_card"]):
            rules["type"] = "id_card"
        elif any(kw in field_name or kw in field_key for kw in ["税号", "信用代码", "credit_code"]):
            rules["type"] = "credit_code"
        elif any(kw in field_name or kw in field_key for kw in ["发票号", "invoice_number"]):
            rules["type"] = "invoice_number"
        else:
            rules["type"] = "string"

        # 添加必填规则
        if field_def.get("required", False):
            rules["required"] = True

        return rules

    def calculate_confidence_score(
        self,
        extracted_data: Dict[str, Any],
        validation_issues: List[Dict],
        ocr_confidence: float = 0.9
    ) -> float:
        """
        计算总体置信度分数

        考虑因素:
        - OCR识别置信度
        - 验证问题数量和严重程度
        - 缺失必填字段数量
        """
        base_score = ocr_confidence

        # 每个错误扣分
        for issue in validation_issues:
            if issue.get("severity") == "error":
                base_score -= 0.15
            elif issue.get("severity") == "warning":
                base_score -= 0.05

        return max(0.0, min(1.0, base_score))

    def suggest_corrections(self, issues: List[Dict]) -> List[Dict]:
        """
        根据验证问题提供修正建议
        """
        suggestions = []

        for issue in issues:
            if issue.get("severity") in ["error", "warning"]:
                suggestion = {
                    "field": issue.get("field"),
                    "key": issue.get("key"),
                    "error": issue.get("error"),
                    "suggestion": self._get_correction_suggestion(issue)
                }
                suggestions.append(suggestion)

        return suggestions

    def _get_correction_suggestion(self, issue: Dict) -> str:
        """获取修正建议"""
        error = issue.get("error", "")

        if "格式不正确" in error:
            return "请检查字段值是否符合预期格式"
        elif "不能为空" in error:
            return "请填写该字段"
        elif "不能少于" in error:
            return "请增加字段内容长度"
        elif "不能超过" in error:
            return "请缩短字段内容"
        elif "必须" in error and "数字" in error:
            return "请输入有效的数字"
        else:
            return "请检查并修正该字段"
