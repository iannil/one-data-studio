"""
数据脱敏服务
Phase 1 P6: 数据安全管理 - 数据脱敏执行

功能：
- 多种脱敏策略（部分遮蔽、哈希、替换、加密等）
- 基于敏感级别的自动脱敏
- 可配置的脱敏规则
- 支持批量数据脱敏
"""

import hashlib
import json
import logging
import os
import re
import secrets
import base64
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# 加密密钥（生产环境应从安全存储获取）
MASKING_SECRET_KEY = os.getenv("MASKING_SECRET_KEY", "one-data-studio-masking-key-2024")


class MaskingStrategy(Enum):
    """脱敏策略枚举"""
    PARTIAL_MASK = "partial_mask"       # 部分遮蔽，如: 138****1234
    FULL_MASK = "full_mask"             # 完全遮蔽，如: ******
    HASH = "hash"                       # 哈希处理，如: a3f2b1...
    TRUNCATE_HASH = "truncate_hash"     # 截断哈希，如: a3f2b1
    REPLACE = "replace"                 # 固定值替换，如: [REDACTED]
    RANDOM_REPLACE = "random_replace"   # 随机值替换
    ENCRYPT = "encrypt"                 # 可逆加密
    SHUFFLE = "shuffle"                 # 打乱顺序
    NULLIFY = "nullify"                 # 置空
    DATE_SHIFT = "date_shift"           # 日期偏移
    NUMBER_RANGE = "number_range"       # 数值范围替换
    PRESERVE_FORMAT = "preserve_format" # 保留格式脱敏


@dataclass
class MaskingRule:
    """脱敏规则配置"""
    rule_id: str
    name: str
    strategy: MaskingStrategy
    sensitivity_type: str = "any"       # pii, financial, health, credential, any
    sensitivity_level: str = "any"      # public, internal, confidential, restricted, any
    column_pattern: str = None          # 列名匹配正则
    data_type: str = None               # 数据类型：string, number, date
    options: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    priority: int = 0                   # 优先级，数字越大优先级越高

    def matches(self, column_name: str, sensitivity_type: str = None,
                sensitivity_level: str = None, data_type: str = None) -> bool:
        """检查规则是否匹配列"""
        # 检查敏感类型
        if self.sensitivity_type != "any" and sensitivity_type:
            if self.sensitivity_type != sensitivity_type:
                return False

        # 检查敏感级别
        if self.sensitivity_level != "any" and sensitivity_level:
            if self.sensitivity_level != sensitivity_level:
                return False

        # 检查列名模式
        if self.column_pattern:
            if not re.search(self.column_pattern, column_name, re.IGNORECASE):
                return False

        # 检查数据类型
        if self.data_type and data_type:
            if self.data_type != data_type:
                return False

        return True


# 默认脱敏规则
DEFAULT_MASKING_RULES = [
    # PII 类型
    MaskingRule(
        rule_id="pii_phone",
        name="手机号脱敏",
        strategy=MaskingStrategy.PARTIAL_MASK,
        sensitivity_type="pii",
        column_pattern=r"(phone|mobile|手机|电话)",
        options={"mask_char": "*", "keep_start": 3, "keep_end": 4}
    ),
    MaskingRule(
        rule_id="pii_idcard",
        name="身份证脱敏",
        strategy=MaskingStrategy.PARTIAL_MASK,
        sensitivity_type="pii",
        column_pattern=r"(id_?card|身份证|identity|ssn)",
        options={"mask_char": "*", "keep_start": 6, "keep_end": 4}
    ),
    MaskingRule(
        rule_id="pii_name",
        name="姓名脱敏",
        strategy=MaskingStrategy.PARTIAL_MASK,
        sensitivity_type="pii",
        column_pattern=r"(^name$|姓名|real_?name|full_?name)",
        options={"mask_char": "*", "keep_start": 1, "keep_end": 0}
    ),
    MaskingRule(
        rule_id="pii_email",
        name="邮箱脱敏",
        strategy=MaskingStrategy.PARTIAL_MASK,
        sensitivity_type="pii",
        column_pattern=r"(email|e_?mail|邮箱)",
        options={"mask_char": "*", "email_mode": True}
    ),
    MaskingRule(
        rule_id="pii_address",
        name="地址脱敏",
        strategy=MaskingStrategy.PARTIAL_MASK,
        sensitivity_type="pii",
        column_pattern=r"(address|地址|住址)",
        options={"mask_char": "*", "keep_start": 6, "keep_end": 0}
    ),

    # 金融类型
    MaskingRule(
        rule_id="financial_card",
        name="银行卡脱敏",
        strategy=MaskingStrategy.PARTIAL_MASK,
        sensitivity_type="financial",
        column_pattern=r"(card_?no|card_?number|银行卡|账号)",
        options={"mask_char": "*", "keep_start": 4, "keep_end": 4}
    ),
    MaskingRule(
        rule_id="financial_amount",
        name="金额脱敏",
        strategy=MaskingStrategy.NUMBER_RANGE,
        sensitivity_type="financial",
        column_pattern=r"(amount|salary|wage|balance|金额|工资|余额)",
        options={"ranges": [(0, 10000, "低"), (10000, 100000, "中"), (100000, float('inf'), "高")]}
    ),

    # 凭证类型
    MaskingRule(
        rule_id="credential_password",
        name="密码脱敏",
        strategy=MaskingStrategy.FULL_MASK,
        sensitivity_type="credential",
        column_pattern=r"(password|passwd|pwd|密码)",
        options={"replacement": "********"}
    ),
    MaskingRule(
        rule_id="credential_token",
        name="令牌脱敏",
        strategy=MaskingStrategy.TRUNCATE_HASH,
        sensitivity_type="credential",
        column_pattern=r"(token|api_?key|secret|密钥)",
        options={"hash_length": 8, "prefix": "***"}
    ),

    # 健康类型
    MaskingRule(
        rule_id="health_record",
        name="病历脱敏",
        strategy=MaskingStrategy.PARTIAL_MASK,
        sensitivity_type="health",
        column_pattern=r"(medical|病历|诊断|处方)",
        options={"mask_char": "*", "keep_start": 0, "keep_end": 0, "max_visible": 0}
    ),

    # 通用高敏感级别规则
    MaskingRule(
        rule_id="restricted_default",
        name="受限数据默认脱敏",
        strategy=MaskingStrategy.HASH,
        sensitivity_level="restricted",
        priority=-10,
        options={"algorithm": "sha256", "truncate": 16}
    ),
    MaskingRule(
        rule_id="confidential_default",
        name="机密数据默认脱敏",
        strategy=MaskingStrategy.PARTIAL_MASK,
        sensitivity_level="confidential",
        priority=-10,
        options={"mask_char": "*", "keep_start": 2, "keep_end": 2}
    ),
]


class DataMaskingService:
    """数据脱敏服务"""

    def __init__(self, custom_rules: List[MaskingRule] = None):
        """
        初始化脱敏服务

        Args:
            custom_rules: 自定义脱敏规则（会与默认规则合并）
        """
        self.rules = DEFAULT_MASKING_RULES.copy()
        if custom_rules:
            self.rules.extend(custom_rules)
        # 按优先级排序
        self.rules.sort(key=lambda r: r.priority, reverse=True)

        # 脱敏策略处理器映射
        self._strategy_handlers: Dict[MaskingStrategy, Callable] = {
            MaskingStrategy.PARTIAL_MASK: self._partial_mask,
            MaskingStrategy.FULL_MASK: self._full_mask,
            MaskingStrategy.HASH: self._hash_mask,
            MaskingStrategy.TRUNCATE_HASH: self._truncate_hash,
            MaskingStrategy.REPLACE: self._replace,
            MaskingStrategy.RANDOM_REPLACE: self._random_replace,
            MaskingStrategy.ENCRYPT: self._encrypt,
            MaskingStrategy.SHUFFLE: self._shuffle,
            MaskingStrategy.NULLIFY: self._nullify,
            MaskingStrategy.DATE_SHIFT: self._date_shift,
            MaskingStrategy.NUMBER_RANGE: self._number_range,
            MaskingStrategy.PRESERVE_FORMAT: self._preserve_format,
        }

    def mask_value(
        self,
        value: Any,
        column_name: str,
        sensitivity_type: str = None,
        sensitivity_level: str = None,
        data_type: str = None,
        strategy_override: MaskingStrategy = None,
        options_override: Dict[str, Any] = None,
    ) -> Any:
        """
        对单个值进行脱敏

        Args:
            value: 原始值
            column_name: 列名
            sensitivity_type: 敏感类型
            sensitivity_level: 敏感级别
            data_type: 数据类型
            strategy_override: 强制使用的策略
            options_override: 覆盖的选项

        Returns:
            脱敏后的值
        """
        if value is None:
            return None

        # 如果指定了策略，直接使用
        if strategy_override:
            handler = self._strategy_handlers.get(strategy_override)
            if handler:
                return handler(value, options_override or {})
            return value

        # 查找匹配的规则
        rule = self._find_matching_rule(
            column_name, sensitivity_type, sensitivity_level, data_type
        )

        if not rule:
            return value

        # 执行脱敏
        handler = self._strategy_handlers.get(rule.strategy)
        if handler:
            options = {**rule.options, **(options_override or {})}
            try:
                return handler(value, options)
            except Exception as e:
                logger.warning(f"脱敏失败 [{column_name}]: {e}")
                # 失败时返回安全默认值
                return "***"

        return value

    def mask_row(
        self,
        row: Dict[str, Any],
        column_metadata: Dict[str, Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        对整行数据进行脱敏

        Args:
            row: 原始行数据
            column_metadata: 列元数据，格式: {
                "column_name": {
                    "sensitivity_type": "pii",
                    "sensitivity_level": "confidential",
                    "data_type": "string"
                }
            }

        Returns:
            脱敏后的行数据
        """
        masked_row = {}
        column_metadata = column_metadata or {}

        for col_name, value in row.items():
            meta = column_metadata.get(col_name, {})
            masked_row[col_name] = self.mask_value(
                value=value,
                column_name=col_name,
                sensitivity_type=meta.get("sensitivity_type"),
                sensitivity_level=meta.get("sensitivity_level"),
                data_type=meta.get("data_type"),
            )

        return masked_row

    def mask_dataframe(
        self,
        data: List[Dict[str, Any]],
        column_metadata: Dict[str, Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        对数据集进行批量脱敏

        Args:
            data: 原始数据列表
            column_metadata: 列元数据

        Returns:
            脱敏后的数据列表
        """
        return [self.mask_row(row, column_metadata) for row in data]

    def create_masking_config(
        self,
        columns: List[Dict[str, Any]],
    ) -> Dict[str, Dict[str, Any]]:
        """
        根据列信息创建脱敏配置

        Args:
            columns: 列信息列表，每项包含 name, sensitivity_type, sensitivity_level 等

        Returns:
            脱敏配置字典，可用于后续脱敏操作
        """
        config = {}
        for col in columns:
            col_name = col.get("name") or col.get("column_name")
            sensitivity_type = col.get("sensitivity_type")
            sensitivity_level = col.get("sensitivity_level")

            if not col_name:
                continue

            # 查找匹配规则
            rule = self._find_matching_rule(
                col_name, sensitivity_type, sensitivity_level
            )

            if rule:
                config[col_name] = {
                    "rule_id": rule.rule_id,
                    "rule_name": rule.name,
                    "strategy": rule.strategy.value,
                    "sensitivity_type": sensitivity_type,
                    "sensitivity_level": sensitivity_level,
                    "options": rule.options,
                }
            else:
                config[col_name] = {
                    "rule_id": None,
                    "strategy": None,
                    "sensitivity_type": sensitivity_type,
                    "sensitivity_level": sensitivity_level,
                    "no_masking": True,
                }

        return config

    def get_masking_preview(
        self,
        sample_data: List[Dict[str, Any]],
        column_metadata: Dict[str, Dict[str, Any]] = None,
        max_rows: int = 5,
    ) -> Dict[str, Any]:
        """
        获取脱敏预览

        Args:
            sample_data: 样本数据
            column_metadata: 列元数据
            max_rows: 最大预览行数

        Returns:
            包含原始数据和脱敏后数据的预览
        """
        sample = sample_data[:max_rows]
        masked = self.mask_dataframe(sample, column_metadata)

        return {
            "original": sample,
            "masked": masked,
            "config": self.create_masking_config(
                [{"name": k, **v} for k, v in (column_metadata or {}).items()]
            ),
        }

    def _find_matching_rule(
        self,
        column_name: str,
        sensitivity_type: str = None,
        sensitivity_level: str = None,
        data_type: str = None,
    ) -> Optional[MaskingRule]:
        """查找匹配的脱敏规则"""
        for rule in self.rules:
            if not rule.enabled:
                continue
            if rule.matches(column_name, sensitivity_type, sensitivity_level, data_type):
                return rule
        return None

    # ===== 脱敏策略实现 =====

    def _partial_mask(self, value: Any, options: Dict[str, Any]) -> str:
        """部分遮蔽"""
        str_value = str(value)
        mask_char = options.get("mask_char", "*")

        # 邮箱特殊处理
        if options.get("email_mode") and "@" in str_value:
            parts = str_value.split("@")
            local = parts[0]
            domain = parts[1] if len(parts) > 1 else ""
            if len(local) > 2:
                masked_local = local[0] + mask_char * (len(local) - 2) + local[-1]
            else:
                masked_local = mask_char * len(local)
            return f"{masked_local}@{domain}"

        keep_start = options.get("keep_start", 0)
        keep_end = options.get("keep_end", 0)
        max_visible = options.get("max_visible", None)

        total_len = len(str_value)

        if max_visible is not None and max_visible == 0:
            return mask_char * min(total_len, 8)

        if keep_start + keep_end >= total_len:
            return str_value

        mask_len = total_len - keep_start - keep_end
        return str_value[:keep_start] + mask_char * mask_len + str_value[total_len - keep_end:] if keep_end else str_value[:keep_start] + mask_char * mask_len

    def _full_mask(self, value: Any, options: Dict[str, Any]) -> str:
        """完全遮蔽"""
        replacement = options.get("replacement", "******")
        return replacement

    def _hash_mask(self, value: Any, options: Dict[str, Any]) -> str:
        """哈希处理"""
        algorithm = options.get("algorithm", "sha256")
        truncate = options.get("truncate", None)

        str_value = str(value) + MASKING_SECRET_KEY

        if algorithm == "md5":
            hash_value = hashlib.md5(str_value.encode()).hexdigest()
        else:
            hash_value = hashlib.sha256(str_value.encode()).hexdigest()

        if truncate:
            hash_value = hash_value[:truncate]

        return hash_value

    def _truncate_hash(self, value: Any, options: Dict[str, Any]) -> str:
        """截断哈希"""
        hash_length = options.get("hash_length", 8)
        prefix = options.get("prefix", "")

        str_value = str(value) + MASKING_SECRET_KEY
        hash_value = hashlib.sha256(str_value.encode()).hexdigest()[:hash_length]

        return f"{prefix}{hash_value}"

    def _replace(self, value: Any, options: Dict[str, Any]) -> str:
        """固定值替换"""
        return options.get("replacement", "[REDACTED]")

    def _random_replace(self, value: Any, options: Dict[str, Any]) -> str:
        """随机值替换"""
        value_type = options.get("value_type", "string")
        length = options.get("length", 8)

        if value_type == "number":
            return str(secrets.randbelow(10 ** length)).zfill(length)
        else:
            return secrets.token_hex(length // 2)

    def _encrypt(self, value: Any, options: Dict[str, Any]) -> str:
        """可逆加密（简单 XOR + Base64）"""
        str_value = str(value)
        key = MASKING_SECRET_KEY.encode()

        # XOR 加密
        encrypted = bytes(
            ord(c) ^ key[i % len(key)]
            for i, c in enumerate(str_value)
        )

        return base64.b64encode(encrypted).decode()

    def _shuffle(self, value: Any, options: Dict[str, Any]) -> str:
        """打乱顺序"""
        str_value = str(value)
        chars = list(str_value)

        # 使用确定性打乱（基于值本身）
        seed = int(hashlib.md5(str_value.encode()).hexdigest()[:8], 16)
        import random
        rng = random.Random(seed)
        rng.shuffle(chars)

        return "".join(chars)

    def _nullify(self, value: Any, options: Dict[str, Any]) -> None:
        """置空"""
        return None

    def _date_shift(self, value: Any, options: Dict[str, Any]) -> str:
        """日期偏移"""
        from datetime import datetime, timedelta

        # 尝试解析日期
        date_formats = ["%Y-%m-%d", "%Y/%m/%d", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y"]
        parsed_date = None
        used_format = None

        for fmt in date_formats:
            try:
                parsed_date = datetime.strptime(str(value), fmt)
                used_format = fmt
                break
            except ValueError:
                continue

        if not parsed_date:
            return str(value)

        # 偏移天数（基于值的哈希确定性偏移）
        shift_range = options.get("shift_range", 30)
        hash_val = int(hashlib.md5(str(value).encode()).hexdigest()[:8], 16)
        shift_days = (hash_val % (shift_range * 2 + 1)) - shift_range

        shifted_date = parsed_date + timedelta(days=shift_days)
        return shifted_date.strftime(used_format)

    def _number_range(self, value: Any, options: Dict[str, Any]) -> str:
        """数值范围替换"""
        try:
            num_value = float(value)
        except (ValueError, TypeError):
            return str(value)

        ranges = options.get("ranges", [(0, float('inf'), "数值")])

        for min_val, max_val, label in ranges:
            if min_val <= num_value < max_val:
                return label

        return "其他"

    def _preserve_format(self, value: Any, options: Dict[str, Any]) -> str:
        """保留格式脱敏"""
        str_value = str(value)
        mask_char = options.get("mask_char", "*")
        preserve_pattern = options.get("preserve", r"[-/@.]")  # 保留的字符

        result = []
        for char in str_value:
            if re.match(preserve_pattern, char):
                result.append(char)
            elif char.isdigit():
                result.append(secrets.choice("0123456789"))
            elif char.isalpha():
                if char.isupper():
                    result.append(secrets.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ"))
                else:
                    result.append(secrets.choice("abcdefghijklmnopqrstuvwxyz"))
            else:
                result.append(mask_char)

        return "".join(result)


# 创建全局实例
_masking_service: Optional[DataMaskingService] = None


def get_masking_service() -> DataMaskingService:
    """获取数据脱敏服务单例"""
    global _masking_service
    if _masking_service is None:
        _masking_service = DataMaskingService()
    return _masking_service


# ===== 便捷函数 =====

def mask_phone(phone: str) -> str:
    """手机号脱敏: 138****1234"""
    service = get_masking_service()
    return service.mask_value(phone, "phone", "pii", "confidential")


def mask_idcard(idcard: str) -> str:
    """身份证脱敏: 110101****1234"""
    service = get_masking_service()
    return service.mask_value(idcard, "id_card", "pii", "confidential")


def mask_email(email: str) -> str:
    """邮箱脱敏: t***t@example.com"""
    service = get_masking_service()
    return service.mask_value(email, "email", "pii", "confidential")


def mask_name(name: str) -> str:
    """姓名脱敏: 张**"""
    service = get_masking_service()
    return service.mask_value(name, "name", "pii", "confidential")


def mask_card_number(card_no: str) -> str:
    """银行卡脱敏: 6222****1234"""
    service = get_masking_service()
    return service.mask_value(card_no, "card_number", "financial", "restricted")


def mask_password(password: str) -> str:
    """密码脱敏: ********"""
    service = get_masking_service()
    return service.mask_value(password, "password", "credential", "restricted")
