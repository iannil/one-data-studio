"""
跨字段校验服务
- 数值计算校验（税额、合计）
- 日期逻辑校验
- 业务规则校验
"""

import logging
import re
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime
from decimal import Decimal

logger = logging.getLogger(__name__)


class CrossFieldValidator:
    """跨字段校验器"""

    def __init__(self):
        """初始化校验器"""
        self.tolerance = 0.01  # 浮点数比较容差

    def validate(
        self,
        data: Dict,
        template: Dict,
        validation_rules: Optional[List[Dict]] = None
    ) -> Dict:
        """
        执行跨字段校验

        Args:
            data: 提取的数据
            template: 模板配置
            validation_rules: 自定义校验规则（可选，优先使用模板中的规则）

        Returns:
            校验结果
        """
        result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "info": []
        }

        # 获取校验规则
        if validation_rules is None:
            validation_rules = template.get("cross_field_validation", [])

        for rule in validation_rules:
            try:
                rule_result = self._apply_rule(data, rule)
                severity = rule.get("severity", "warning")

                if not rule_result["valid"]:
                    result["valid"] = False
                    rule_result["severity"] = severity

                    if severity == "error":
                        result["errors"].append(rule_result)
                    elif severity == "warning":
                        result["warnings"].append(rule_result)
                    else:
                        result["info"].append(rule_result)
                elif rule_result.get("warning"):
                    result["warnings"].append(rule_result)

            except Exception as e:
                logger.warning(f"Validation rule '{rule.get('rule', 'unknown')}' failed: {e}")
                result["warnings"].append({
                    "valid": False,
                    "rule": rule.get("rule", "unknown"),
                    "description": rule.get("description", ""),
                    "error": f"校验规则执行失败: {str(e)}",
                    "severity": "warning"
                })

        return result

    def _apply_rule(self, data: Dict, rule: Dict) -> Dict:
        """应用单个校验规则"""
        rule_type = rule.get("rule", "")

        rule_handlers = {
            "amount_sum_check": self._validate_amount_sum,
            "date_logic_check": self._validate_date_logic,
            "payment_sum_check": self._validate_payment_sum,
            "tax_calculation_check": self._validate_tax_calculation,
            "delivery_receive_check": self._validate_delivery_receive_qty,
            "total_amount_check": self._validate_total_amount,
            "validity_check": self._validate_date_range,
            "signing_before_effective_check": self._validate_signing_before_effective,
            "payment_amount_sum_check": self._validate_payment_amount_sum,
            "amount_check": self._validate_amount_chinese
        }

        handler = rule_handlers.get(rule_type)
        if handler:
            return handler(data, rule)
        else:
            logger.warning(f"Unknown validation rule type: {rule_type}")
            return {"valid": True}

    def _get_nested_value(self, data: Dict, key: str) -> Any:
        """获取嵌套字段的值"""
        keys = key.split(".")
        value = data

        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            elif isinstance(value, list) and k.isdigit():
                index = int(k)
                if 0 <= index < len(value):
                    value = value[index]
                else:
                    return None
            else:
                return None

        return value

    def _parse_number(self, value: Any) -> Optional[float]:
        """解析数字值"""
        if value is None:
            return None

        if isinstance(value, (int, float)):
            return float(value)

        if isinstance(value, str):
            # 移除千分位逗号、货币符号和空格
            value = value.replace(",", "").replace("¥", "").replace("$", "").replace("￥", "").strip()

            # 处理百分数
            if value.endswith("%"):
                return float(value.rstrip("%")) / 100

            try:
                return float(value)
            except ValueError:
                pass

        return None

    def _parse_date(self, date_str: Any) -> Optional[datetime]:
        """解析多种日期格式"""
        if date_str is None:
            return None

        if isinstance(date_str, datetime):
            return date_str

        if isinstance(date_str, str):
            date_str = date_str.strip()
            formats = [
                "%Y-%m-%d",
                "%Y/%m/%d",
                "%Y.%m.%d",
                "%Y年%m月%d日",
                "%Y%m%d",
                "%Y-%m-%d %H:%M:%S",
                "%d/%m/%Y",
                "%m/%d/%Y"
            ]

            for fmt in formats:
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue

        return None

    def _validate_amount_sum(self, data: Dict, rule: Dict) -> Dict:
        """校验金额合计"""
        fields = rule.get("fields", [])
        if len(fields) < 2:
            return {"valid": True, "warning": "校验规则配置不完整"}

        total_field = fields[0]
        table_key = fields[1]

        total_amount = self._parse_number(self._get_nested_value(data, total_field))
        table_data = self._get_nested_value(data, table_key)

        if total_amount is None or table_data is None:
            return {"valid": True, "warning": f"缺少字段: {table_key} 或 {total_field}"}

        if not isinstance(table_data, list):
            return {"valid": True, "warning": f"{table_key} 不是表格数据"}

        calculated_sum = 0.0
        for row in table_data:
            if isinstance(row, dict):
                row_amount = self._parse_number(row.get("amount"))
                if row_amount is not None:
                    calculated_sum += row_amount

        is_valid = abs(calculated_sum - total_amount) <= self.tolerance

        return {
            "valid": is_valid,
            "rule": rule.get("description", "金额合计校验"),
            "expected": round(calculated_sum, 2),
            "actual": round(total_amount, 2),
            "difference": round(abs(calculated_sum - total_amount), 2)
        }

    def _validate_date_logic(self, data: Dict, rule: Dict) -> Dict:
        """校验日期逻辑"""
        fields = rule.get("fields", [])
        if len(fields) < 2:
            return {"valid": True, "warning": "校验规则配置不完整"}

        field1, field2 = fields[0], fields[1]

        date1 = self._parse_date(self._get_nested_value(data, field1))
        date2 = self._parse_date(self._get_nested_value(data, field2))

        if date1 is None or date2 is None:
            return {"valid": True, "warning": f"日期字段解析失败: {field1} 或 {field2}"}

        is_valid = date1 <= date2

        return {
            "valid": is_valid,
            "rule": rule.get("description", "日期逻辑校验"),
            "date1": field1,
            "date1_value": date1.strftime("%Y-%m-%d") if date1 else None,
            "date2": field2,
            "date2_value": date2.strftime("%Y-%m-%d") if date2 else None
        }

    def _validate_payment_sum(self, data: Dict, rule: Dict) -> Dict:
        """校验付款计划合计比例"""
        table_key = rule.get("fields", ["payment_schedule"])[0]
        table_data = self._get_nested_value(data, table_key)

        if table_data is None or not isinstance(table_data, list):
            return {"valid": True, "warning": f"缺少付款计划数据: {table_key}"}

        total_percentage = 0.0
        for row in table_data:
            if isinstance(row, dict):
                percentage = self._parse_number(row.get("percentage"))
                if percentage is not None:
                    total_percentage += percentage

        # 检查是否等于100%（允许小误差）
        is_valid = abs(total_percentage - 100.0) <= 1.0

        return {
            "valid": is_valid,
            "rule": rule.get("description", "付款计划合计校验"),
            "expected": 100.0,
            "actual": round(total_percentage, 2),
            "difference": round(abs(total_percentage - 100.0), 2)
        }

    def _validate_tax_calculation(self, data: Dict, rule: Dict) -> Dict:
        """校验税额计算"""
        amount = self._parse_number(self._get_nested_value(data, "contract_amount") or
                                   self._get_nested_value(data, "total_amount") or
                                   self._get_nested_value(data, "amount"))
        tax_rate = self._parse_number(self._get_nested_value(data, "tax_rate"))
        tax_amount = self._parse_number(self._get_nested_value(data, "tax_amount"))

        if amount is None or tax_rate is None or tax_amount is None:
            return {"valid": True, "warning": "税额计算字段不完整"}

        # 计算期望税额
        # 如果是不含税金额：税额 = 金额 × 税率
        # 如果是含税金额：税额 = 金额 × 税率 / (1 + 税率)
        tax_included = self._get_nested_value(data, "tax_included")

        if tax_included == "true" or tax_included is True:
            expected_tax = amount * tax_rate / (1 + tax_rate)
        else:
            expected_tax = amount * tax_rate

        is_valid = abs(expected_tax - tax_amount) <= max(self.tolerance, amount * 0.01)

        return {
            "valid": is_valid,
            "rule": rule.get("description", "税额计算校验"),
            "expected": round(expected_tax, 2),
            "actual": round(tax_amount, 2),
            "difference": round(abs(expected_tax - tax_amount), 2)
        }

    def _validate_delivery_receive_qty(self, data: Dict, rule: Dict) -> Dict:
        """校验送货数量与实收数量"""
        items = self._get_nested_value(data, "items")

        if items is None or not isinstance(items, list):
            return {"valid": True, "warning": "缺少明细数据"}

        issues = []
        for i, item in enumerate(items):
            if isinstance(item, dict):
                delivered = self._parse_number(item.get("delivered_qty"))
                received = self._parse_number(item.get("received_qty"))

                if delivered is not None and received is not None:
                    if received > delivered:
                        issues.append({
                            "row": i + 1,
                            "item": item.get("item_name", ""),
                            "delivered": delivered,
                            "received": received
                        })

        is_valid = len(issues) == 0

        return {
            "valid": is_valid,
            "rule": rule.get("description", "实收数量校验"),
            "issues": issues,
            "issue_count": len(issues)
        }

    def _validate_total_amount(self, data: Dict, rule: Dict) -> Dict:
        """校验总金额等于明细合计"""
        total_amount = self._parse_number(self._get_nested_value(data, "total_amount"))
        items = self._get_nested_value(data, "items")

        if total_amount is None or items is None:
            return {"valid": True, "warning": "总金额或明细数据缺失"}

        if not isinstance(items, list):
            return {"valid": True, "warning": "明细数据格式不正确"}

        calculated_sum = 0.0
        for item in items:
            if isinstance(item, dict):
                amount = self._parse_number(item.get("amount"))
                if amount is not None:
                    calculated_sum += amount

        is_valid = abs(calculated_sum - total_amount) <= self.tolerance

        return {
            "valid": is_valid,
            "rule": rule.get("description", "总金额校验"),
            "expected": round(calculated_sum, 2),
            "actual": round(total_amount, 2),
            "difference": round(abs(calculated_sum - total_amount), 2)
        }

    def _validate_date_range(self, data: Dict, rule: Dict) -> Dict:
        """校验日期范围（报价单有效期等）"""
        fields = rule.get("fields", [])
        if len(fields) < 2:
            return {"valid": True, "warning": "校验规则配置不完整"}

        start_date = self._parse_date(self._get_nested_value(data, fields[0]))
        end_date = self._parse_date(self._get_nested_value(data, fields[1]))

        if start_date is None or end_date is None:
            return {"valid": True, "warning": "日期字段解析失败"}

        is_valid = start_date < end_date

        return {
            "valid": is_valid,
            "rule": rule.get("description", "日期范围校验"),
            "start_date": start_date.strftime("%Y-%m-%d") if start_date else None,
            "end_date": end_date.strftime("%Y-%m-%d") if end_date else None
        }

    def _validate_signing_before_effective(self, data: Dict, rule: Dict) -> Dict:
        """校验签订日期早于生效日期"""
        signing_date = self._parse_date(self._get_nested_value(data, "signing_date"))
        effective_date = self._parse_date(self._get_nested_value(data, "effective_date"))

        if signing_date is None or effective_date is None:
            return {"valid": True, "warning": "日期字段解析失败"}

        is_valid = signing_date <= effective_date

        return {
            "valid": is_valid,
            "rule": rule.get("description", "签订日期校验"),
            "signing_date": signing_date.strftime("%Y-%m-%d") if signing_date else None,
            "effective_date": effective_date.strftime("%Y-%m-%d") if effective_date else None
        }

    def _validate_payment_amount_sum(self, data: Dict, rule: Dict) -> Dict:
        """校验付款计划合计金额等于合同金额"""
        contract_amount = self._parse_number(self._get_nested_value(data, "contract_amount"))
        payment_schedule = self._get_nested_value(data, "payment_schedule")

        if contract_amount is None or payment_schedule is None:
            return {"valid": True, "warning": "合同金额或付款计划数据缺失"}

        if not isinstance(payment_schedule, list):
            return {"valid": True, "warning": "付款计划数据格式不正确"}

        total_payment = 0.0
        for item in payment_schedule:
            if isinstance(item, dict):
                amount = self._parse_number(item.get("amount"))
                if amount is not None:
                    total_payment += amount

        is_valid = abs(total_payment - contract_amount) <= self.tolerance

        return {
            "valid": is_valid,
            "rule": rule.get("description", "付款金额合计校验"),
            "expected": round(contract_amount, 2),
            "actual": round(total_payment, 2),
            "difference": round(abs(total_payment - contract_amount), 2)
        }

    def _validate_amount_chinese(self, data: Dict) -> Dict:
        """校验金额大小写一致"""
        amount = self._parse_number(self._get_nested_value(data, "amount"))
        amount_cn = self._get_nested_value(data, "amount_cn")

        if amount is None or amount_cn is None:
            return {"valid": True}

        # 转换为中文大写
        expected_cn = self._number_to_chinese(amount)

        # 简化比较：只比较主要部分
        is_valid = self._compare_chinese_amount(amount_cn, expected_cn)

        return {
            "valid": is_valid,
            "rule": "金额大小写校验",
            "numeric": amount,
            "chinese": amount_cn,
            "expected_chinese": expected_cn
        }

    def _number_to_chinese(self, num: float) -> str:
        """将数字转换为中文大写金额"""
        # 数字大写映射
        digits = ["零", "壹", "贰", "叁", "肆", "伍", "陆", "柒", "捌", "玖"]
        units = ["", "拾", "佰", "仟", "万", "拾", "佰", "仟", "亿"]

        # 分离整数和小数
        integer_part = int(num)
        decimal_part = round((num - integer_part) * 100)

        # 转换整数部分
        if integer_part == 0:
            chinese = "零"
        else:
            chinese = ""
            str_num = str(integer_part)
            for i, digit in enumerate(str_num):
                pos = len(str_num) - i - 1
                if digit != '0':
                    chinese += digits[int(digit)] + units[pos]
                else:
                    # 处理连续的零
                    if not chinese.endswith("零") and i < len(str_num) - 1:
                        chinese += "零"

        chinese += "元"

        # 转换小数部分
        if decimal_part > 0:
            jiao = decimal_part // 10
            fen = decimal_part % 10
            if jiao > 0:
                chinese += digits[jiao] + "角"
            if fen > 0:
                chinese += digits[fen] + "分"
        else:
            chinese += "整"

        return chinese

    def _compare_chinese_amount(self, actual: str, expected: str) -> bool:
        """比较中文金额（容错处理）"""
        # 去除空格
        actual = actual.replace(" ", "")
        expected = expected.replace(" ", "")

        # 简化比较：检查主要数字是否一致
        # 这里可以添加更复杂的匹配逻辑
        return actual == expected

    def validate_template_completeness(
        self,
        data: Dict,
        template: Dict
    ) -> Dict:
        """
        校验模板完整性

        Args:
            data: 提取的数据
            template: 模板配置

        Returns:
            完整性校验结果
        """
        result = {
            "valid": True,
            "missing_required": [],
            "missing_optional": [],
            "completeness_rate": 0.0
        }

        fields = template.get("fields", [])
        total_fields = len(fields)
        filled_fields = 0

        for field in fields:
            key = field.get("key")
            required = field.get("required", False)
            value = self._get_nested_value(data, key)

            if value is None or value == "":
                if required:
                    result["missing_required"].append({
                        "key": key,
                        "name": field.get("name", key)
                    })
                else:
                    result["missing_optional"].append({
                        "key": key,
                        "name": field.get("name", key)
                    })
            else:
                filled_fields += 1

        # 检查表格
        tables = template.get("tables", [])
        for table in tables:
            key = table.get("key")
            required = table.get("required", False)
            value = self._get_nested_value(data, key)

            if value is None or (isinstance(value, list) and len(value) == 0):
                if required:
                    result["missing_required"].append({
                        "key": key,
                        "name": table.get("name", key),
                        "type": "table"
                    })
            else:
                filled_fields += 1

        result["valid"] = len(result["missing_required"]) == 0
        result["completeness_rate"] = round(
            filled_fields / max(total_fields + len(tables), 1) * 100,
            2
        )

        return result


# 便捷函数
def validate_cross_fields(data: Dict, template: Dict) -> Dict:
    """
    跨字段校验便捷函数

    Args:
        data: 提取的数据
        template: 模板配置

    Returns:
        校验结果
    """
    validator = CrossFieldValidator()
    return validator.validate(data, template)
