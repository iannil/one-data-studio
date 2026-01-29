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

# AES-256-GCM 加密服务（延迟导入）
_encryption_service = None


def _get_encryption_service():
    """获取共享加密服务（AES-256-GCM）"""
    global _encryption_service
    if _encryption_service is None:
        try:
            from shared.security.encryption import get_encryption_service
            _encryption_service = get_encryption_service()
        except ImportError:
            logger.warning("无法导入共享加密模块，尝试直接初始化 AES-256-GCM")
            try:
                from cryptography.hazmat.primitives.ciphers.aead import AESGCM
                _encryption_service = _FallbackAESGCM()
            except ImportError:
                logger.error("cryptography 库未安装，加密功能不可用")
                _encryption_service = None
    return _encryption_service


class _FallbackAESGCM:
    """
    备用 AES-256-GCM 加密实现

    当无法导入共享加密模块时使用。
    提供与共享模块兼容的加密/解密接口。
    """
    IV_LENGTH = 12   # GCM 推荐 12 字节 nonce
    KEY_LENGTH = 32  # AES-256 需要 32 字节密钥

    def __init__(self):
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        from cryptography.hazmat.primitives import hashes

        # 从环境变量或默认密钥派生 AES 密钥
        master_key = os.getenv("ENCRYPTION_MASTER_KEY", MASKING_SECRET_KEY)
        salt = os.getenv("ENCRYPTION_KEY_SALT", "one-data-studio-salt").encode()

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=self.KEY_LENGTH,
            salt=salt,
            iterations=100_000,
        )
        self._derived_key = kdf.derive(master_key.encode())
        self._aesgcm = AESGCM(self._derived_key)

    def encrypt(self, plaintext: str) -> str:
        """加密字符串，返回 base64 编码的密文"""
        nonce = os.urandom(self.IV_LENGTH)
        ciphertext = self._aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
        # 格式: base64(nonce + ciphertext)
        payload = nonce + ciphertext
        return base64.b64encode(payload).decode("ascii")

    def decrypt(self, token: str) -> str:
        """解密 base64 编码的密文，返回明文"""
        payload = base64.b64decode(token.encode("ascii"))
        nonce = payload[:self.IV_LENGTH]
        ciphertext = payload[self.IV_LENGTH:]
        plaintext = self._aesgcm.decrypt(nonce, ciphertext, None)
        return plaintext.decode("utf-8")

    def is_encrypted(self, value: str) -> bool:
        """检查值是否为加密格式"""
        if not value or not isinstance(value, str):
            return False
        # 检查是否为有效的 base64，且解码后长度合理（至少 nonce + 1 字节密文 + 16 字节 tag）
        try:
            decoded = base64.b64decode(value)
            return len(decoded) > self.IV_LENGTH + 16
        except Exception:
            return False


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
        """可逆加密（AES-256-GCM 认证加密）"""
        str_value = str(value)

        enc_service = _get_encryption_service()
        if enc_service is not None:
            try:
                return enc_service.encrypt(str_value)
            except Exception as e:
                logger.error(f"AES-256-GCM 加密失败: {e}")
                # 加密失败时返回安全占位符而非明文
                return "***ENCRYPTION_ERROR***"

        # 如果加密服务不可用，返回安全占位符
        logger.error("加密服务不可用，无法执行加密操作")
        return "***ENCRYPTION_UNAVAILABLE***"

    def decrypt_value(self, encrypted_value: str) -> Optional[str]:
        """
        解密已加密的值（AES-256-GCM）

        Args:
            encrypted_value: 已加密的值

        Returns:
            解密后的明文，失败返回 None
        """
        enc_service = _get_encryption_service()
        if enc_service is None:
            logger.error("加密服务不可用，无法执行解密操作")
            return None

        try:
            return enc_service.decrypt(encrypted_value)
        except Exception as e:
            logger.error(f"AES-256-GCM 解密失败: {e}")
            return None

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


# ==================== 动态脱敏扩展 ====================

class RoleType(Enum):
    """用户角色类型"""
    ADMIN = "admin"                     # 管理员：无脱敏
    ANALYST = "analyst"                 # 数据分析师：部分脱敏
    REPORTER = "reporter"               # 报表查看者：强脱敏
    GUEST = "guest"                     # 访客：最强脱敏
    DATA_OWNER = "data_owner"           # 数据所有者：无脱敏
    AUDITOR = "auditor"                 # 审计员：可逆加密


@dataclass
class MaskingPolicy:
    """脱敏策略版本"""
    policy_id: str
    policy_name: str
    version: str
    description: str = ""
    role_configs: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    enabled: bool = True
    created_at: datetime = None
    updated_at: datetime = None
    created_by: str = "system"

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()


@dataclass
class MaskingAuditLog:
    """脱敏审计日志"""
    log_id: str
    timestamp: datetime
    user_id: str
    user_role: str
    table_name: str
    column_name: str
    operation: str  # mask, decrypt, preview
    sensitivity_level: str
    policy_version: str
    record_count: int = 0
    success: bool = True
    error_message: str = None


class DynamicMaskingService:
    """
    动态脱敏服务

    扩展功能：
    1. 基于用户角色的动态脱敏
    2. 脱敏策略版本管理
    3. SQL 查询结果实时脱敏
    4. 条件脱敏（基于上下文）
    5. 脱敏审计日志
    """

    # 默认角色配置
    DEFAULT_ROLE_CONFIGS = {
        RoleType.ADMIN.value: {
            "mask_level": "none",           # 不脱敏
            "allow_decrypt": True,
            "allow_export": True,
        },
        RoleType.DATA_OWNER.value: {
            "mask_level": "none",
            "allow_decrypt": True,
            "allow_export": True,
        },
        RoleType.AUDITOR.value: {
            "mask_level": "reversible",     # 可逆加密
            "allow_decrypt": True,
            "allow_export": True,
        },
        RoleType.ANALYST.value: {
            "mask_level": "partial",        # 部分脱敏
            "allow_decrypt": False,
            "allow_export": False,
            " pii_keep_chars": 2,
        },
        RoleType.REPORTER.value: {
            "mask_level": "strong",         # 强脱敏
            "allow_decrypt": False,
            "allow_export": False,
            " pii_keep_chars": 1,
        },
        RoleType.GUEST.value: {
            "mask_level": "full",           # 完全脱敏
            "allow_decrypt": False,
            "allow_export": False,
            " pii_keep_chars": 0,
        },
    }

    def __init__(self, base_service: DataMaskingService = None):
        """
        初始化动态脱敏服务

        Args:
            base_service: 基础脱敏服务
        """
        self.base_service = base_service or get_masking_service()

        # 策略版本管理
        self.policies: Dict[str, MaskingPolicy] = {}
        self.active_policy_id: Optional[str] = None

        # 审计日志
        self.audit_logs: List[MaskingAuditLog] = []
        self._max_audit_logs = 10000  # 最大日志条数

        # 条件脱敏规则
        self.conditional_rules: List[Dict[str, Any]] = []

        # 初始化默认策略
        self._init_default_policy()

    def _init_default_policy(self):
        """初始化默认脱敏策略"""
        default_policy = MaskingPolicy(
            policy_id="default",
            policy_name="默认脱敏策略",
            version="1.0.0",
            description="系统默认脱敏策略",
            role_configs=self.DEFAULT_ROLE_CONFIGS.copy(),
        )
        self.policies["default"] = default_policy
        self.active_policy_id = "default"

    # ==================== 策略管理 ====================

    def create_policy(
        self,
        policy_id: str,
        policy_name: str,
        version: str,
        role_configs: Dict[str, Dict[str, Any]],
        description: str = "",
        created_by: str = "system",
    ) -> MaskingPolicy:
        """
        创建新的脱敏策略

        Args:
            policy_id: 策略ID
            policy_name: 策略名称
            version: 版本号
            role_configs: 角色配置
            description: 描述
            created_by: 创建者

        Returns:
            创建的策略
        """
        policy = MaskingPolicy(
            policy_id=policy_id,
            policy_name=policy_name,
            version=version,
            description=description,
            role_configs=role_configs,
            created_by=created_by,
        )
        self.policies[policy_id] = policy
        return policy

    def update_policy(
        self,
        policy_id: str,
        role_configs: Dict[str, Dict[str, Any]] = None,
        description: str = None,
    ) -> Optional[MaskingPolicy]:
        """
        更新脱敏策略

        Args:
            policy_id: 策略ID
            role_configs: 新的角色配置
            description: 新的描述

        Returns:
            更新后的策略，不存在返回 None
        """
        policy = self.policies.get(policy_id)
        if not policy:
            return None

        if role_configs:
            policy.role_configs = role_configs
        if description is not None:
            policy.description = description
        policy.updated_at = datetime.now()

        return policy

    def activate_policy(self, policy_id: str) -> bool:
        """
        激活脱敏策略

        Args:
            policy_id: 策略ID

        Returns:
            是否成功激活
        """
        if policy_id not in self.policies:
            return False
        self.active_policy_id = policy_id
        return True

    def get_active_policy(self) -> Optional[MaskingPolicy]:
        """获取当前激活的策略"""
        return self.policies.get(self.active_policy_id)

    def list_policies(self) -> List[MaskingPolicy]:
        """列出所有策略"""
        return list(self.policies.values())

    # ==================== 基于角色的脱敏 ====================

    def mask_for_role(
        self,
        value: Any,
        column_name: str,
        user_role: str,
        sensitivity_level: str = "confidential",
        sensitivity_type: str = None,
        table_name: str = None,
        context: Dict[str, Any] = None,
    ) -> Any:
        """
        基于用户角色进行脱敏

        Args:
            value: 原始值
            column_name: 列名
            user_role: 用户角色
            sensitivity_level: 敏感级别
            sensitivity_type: 敏感类型
            table_name: 表名
            context: 上下文信息（用于条件脱敏）

        Returns:
            脱敏后的值
        """
        if value is None:
            return None

        policy = self.get_active_policy()
        if not policy:
            return value

        role_config = policy.role_configs.get(user_role)
        if not role_config:
            # 未知角色，使用默认（访客级别）
            role_config = self.DEFAULT_ROLE_CONFIGS.get(RoleType.GUEST.value)

        mask_level = role_config.get("mask_level", "partial")

        # 无脱敏（管理员、数据所有者）
        if mask_level == "none":
            return value

        # 完全脱敏（访客）
        if mask_level == "full":
            return self._apply_full_mask(value, column_name, sensitivity_type)

        # 可逆加密（审计员）
        if mask_level == "reversible":
            return self.base_service.mask_value(
                value, column_name, sensitivity_type, sensitivity_level,
                strategy_override=MaskingStrategy.ENCRYPT
            )

        # 部分脱敏（分析师、报表查看者）
        keep_chars = role_config.get("pii_keep_chars", 2)
        return self._apply_partial_mask(
            value, column_name, sensitivity_type, keep_chars
        )

    def mask_sql_result(
        self,
        result: List[Dict[str, Any]],
        user_role: str,
        table_metadata: Dict[str, Dict[str, Any]],
        context: Dict[str, Any] = None,
    ) -> List[Dict[str, Any]]:
        """
        对 SQL 查询结果进行实时脱敏

        Args:
            result: SQL 查询结果
            user_role: 用户角色
            table_metadata: 表元数据，格式: {
                "table_name": {
                    "columns": {
                        "column_name": {
                            "sensitivity_type": "pii",
                            "sensitivity_level": "confidential"
                        }
                    }
                }
            }
            context: 上下文信息

        Returns:
            脱敏后的结果
        """
        masked_result = []

        for row in result:
            masked_row = {}
            for col_name, value in row.items():
                # 查找列的元数据
                col_meta = self._find_column_metadata(col_name, table_metadata)

                masked_row[col_name] = self.mask_for_role(
                    value=value,
                    column_name=col_name,
                    user_role=user_role,
                    sensitivity_level=col_meta.get("sensitivity_level", "internal"),
                    sensitivity_type=col_meta.get("sensitivity_type"),
                    table_name=col_meta.get("table_name"),
                    context=context,
                )
            masked_result.append(masked_row)

        # 记录审计日志
        self._log_masking_operation(
            user_role=user_role,
            table_name=context.get("table_name", "unknown") if context else "unknown",
            operation="mask",
            record_count=len(result),
        )

        return masked_result

    def _find_column_metadata(
        self,
        column_name: str,
        table_metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """查找列元数据"""
        for table_name, table_meta in table_metadata.items():
            columns = table_meta.get("columns", {})
            if column_name in columns:
                return {
                    **columns[column_name],
                    "table_name": table_name,
                }
        return {}

    def _apply_full_mask(
        self,
        value: Any,
        column_name: str,
        sensitivity_type: str,
    ) -> str:
        """应用完全脱敏"""
        return self.base_service.mask_value(
            value, column_name, sensitivity_type, "restricted",
            strategy_override=MaskingStrategy.FULL_MASK,
        )

    def _apply_partial_mask(
        self,
        value: Any,
        column_name: str,
        sensitivity_type: str,
        keep_chars: int,
    ) -> str:
        """应用部分脱敏"""
        options = {"keep_start": keep_chars, "keep_end": 0}
        return self.base_service.mask_value(
            value, column_name, sensitivity_type, "confidential",
            strategy_override=MaskingStrategy.PARTIAL_MASK,
            options_override=options,
        )

    # ==================== 条件脱敏 ====================

    def add_conditional_rule(
        self,
        rule_id: str,
        condition: Dict[str, Any],
        masking_action: Dict[str, Any],
        priority: int = 0,
    ) -> bool:
        """
        添加条件脱敏规则

        Args:
            rule_id: 规则ID
            condition: 条件表达式，如 {
                "column": "status",
                "operator": "eq",
                "value": "active"
            }
            masking_action: 脱敏动作，如 {
                "strategy": "full_mask",
                "options": {"replacement": "***"}
            }
            priority: 优先级

        Returns:
            是否添加成功
        """
        rule = {
            "rule_id": rule_id,
            "condition": condition,
            "action": masking_action,
            "priority": priority,
            "enabled": True,
        }
        self.conditional_rules.append(rule)
        # 按优先级排序
        self.conditional_rules.sort(key=lambda r: r["priority"], reverse=True)
        return True

    def apply_conditional_masking(
        self,
        row: Dict[str, Any],
        column_name: str,
        value: Any,
    ) -> Any:
        """
        应用条件脱敏

        Args:
            row: 当前行数据
            column_name: 列名
            value: 原始值

        Returns:
            脱敏后的值（如果条件匹配）
        """
        for rule in self.conditional_rules:
            if not rule.get("enabled"):
                continue

            condition = rule["condition"]
            if self._evaluate_condition(row, condition):
                action = rule["action"]
                strategy = MaskingStrategy(action.get("strategy", "full_mask"))
                options = action.get("options", {})

                return self.base_service.mask_value(
                    value, column_name, None, None,
                    strategy_override=strategy,
                    options_override=options,
                )

        return value

    def _evaluate_condition(
        self,
        row: Dict[str, Any],
        condition: Dict[str, Any],
    ) -> bool:
        """评估条件是否满足"""
        column = condition.get("column")
        operator = condition.get("operator", "eq")
        expected_value = condition.get("value")

        if column not in row:
            return False

        actual_value = row[column]

        if operator == "eq":
            return actual_value == expected_value
        elif operator == "ne":
            return actual_value != expected_value
        elif operator == "gt":
            return actual_value > expected_value
        elif operator == "lt":
            return actual_value < expected_value
        elif operator == "gte":
            return actual_value >= expected_value
        elif operator == "lte":
            return actual_value <= expected_value
        elif operator == "in":
            return actual_value in expected_value
        elif operator == "contains":
            return expected_value in str(actual_value)
        elif operator == "regex":
            import re
            return bool(re.search(expected_value, str(actual_value)))

        return False

    # ==================== 审计日志 ====================

    def _log_masking_operation(
        self,
        user_role: str,
        table_name: str,
        operation: str,
        record_count: int = 0,
        column_name: str = None,
        sensitivity_level: str = "unknown",
        success: bool = True,
        error_message: str = None,
    ):
        """记录脱敏操作审计日志"""
        policy = self.get_active_policy()

        log = MaskingAuditLog(
            log_id=f"{datetime.now().timestamp()}",
            timestamp=datetime.now(),
            user_id="",  # 从上下文获取
            user_role=user_role,
            table_name=table_name,
            column_name=column_name or "",
            operation=operation,
            sensitivity_level=sensitivity_level,
            policy_version=policy.version if policy else "unknown",
            record_count=record_count,
            success=success,
            error_message=error_message,
        )

        self.audit_logs.append(log)

        # 限制日志数量
        if len(self.audit_logs) > self._max_audit_logs:
            self.audit_logs = self.audit_logs[-self._max_audit_logs:]

    def get_audit_logs(
        self,
        user_role: str = None,
        table_name: str = None,
        operation: str = None,
        start_time: datetime = None,
        end_time: datetime = None,
        limit: int = 100,
    ) -> List[MaskingAuditLog]:
        """
        查询审计日志

        Args:
            user_role: 用户角色过滤
            table_name: 表名过滤
            operation: 操作类型过滤
            start_time: 开始时间
            end_time: 结束时间
            limit: 返回数量限制

        Returns:
            审计日志列表
        """
        logs = self.audit_logs

        if user_role:
            logs = [log for log in logs if log.user_role == user_role]
        if table_name:
            logs = [log for log in logs if log.table_name == table_name]
        if operation:
            logs = [log for log in logs if log.operation == operation]
        if start_time:
            logs = [log for log in logs if log.timestamp >= start_time]
        if end_time:
            logs = [log for log in logs if log.timestamp <= end_time]

        return logs[-limit:]

    def get_masking_statistics(
        self,
        start_time: datetime = None,
        end_time: datetime = None,
    ) -> Dict[str, Any]:
        """
        获取脱敏统计信息

        Args:
            start_time: 开始时间
            end_time: 结束时间

        Returns:
            统计信息
        """
        logs = self.audit_logs
        if start_time:
            logs = [log for log in logs if log.timestamp >= start_time]
        if end_time:
            logs = [log for log in logs if log.timestamp <= end_time]

        stats = {
            "total_operations": len(logs),
            "operations_by_role": {},
            "operations_by_type": {},
            "total_records_masked": 0,
            "success_rate": 0,
            "active_policy": self.active_policy_id,
        }

        for log in logs:
            # 按角色统计
            if log.user_role not in stats["operations_by_role"]:
                stats["operations_by_role"][log.user_role] = 0
            stats["operations_by_role"][log.user_role] += 1

            # 按操作类型统计
            if log.operation not in stats["operations_by_type"]:
                stats["operations_by_type"][log.operation] = 0
            stats["operations_by_type"][log.operation] += 1

            # 总记录数
            stats["total_records_masked"] += log.record_count

        # 成功率
        success_count = sum(1 for log in logs if log.success)
        stats["success_rate"] = success_count / len(logs) if logs else 1.0

        return stats

    # ==================== 批量操作 ====================

    def batch_mask_for_export(
        self,
        data: List[Dict[str, Any]],
        user_role: str,
        table_metadata: Dict[str, Dict[str, Any]],
        export_format: str = "csv",
    ) -> Tuple[List[Dict[str, Any]], bool]:
        """
        批量脱敏用于导出

        Args:
            data: 原始数据
            user_role: 用户角色
            table_metadata: 表元数据
            export_format: 导出格式（csv, excel, json）

        Returns:
            (脱敏后的数据, 是否允许导出)
        """
        policy = self.get_active_policy()
        role_config = policy.role_configs.get(user_role, {}) if policy else {}

        # 检查是否允许导出
        allow_export = role_config.get("allow_export", False)

        masked_data = self.mask_sql_result(
            result=data,
            user_role=user_role,
            table_metadata=table_metadata,
            context={"operation": "export", "format": export_format},
        )

        return masked_data, allow_export

    def create_masking_preview_for_role(
        self,
        sample_data: List[Dict[str, Any]],
        user_role: str,
        table_metadata: Dict[str, Dict[str, Any]],
        max_rows: int = 5,
    ) -> Dict[str, Any]:
        """
        为特定角色创建脱敏预览

        Args:
            sample_data: 样本数据
            user_role: 用户角色
            table_metadata: 表元数据
            max_rows: 最大预览行数

        Returns:
            预览结果
        """
        sample = sample_data[:max_rows]
        masked = self.mask_sql_result(
            result=sample,
            user_role=user_role,
            table_metadata=table_metadata,
        )

        policy = self.get_active_policy()
        role_config = policy.role_configs.get(user_role, {}) if policy else {}

        return {
            "role": user_role,
            "mask_level": role_config.get("mask_level", "unknown"),
            "allow_decrypt": role_config.get("allow_decrypt", False),
            "allow_export": role_config.get("allow_export", False),
            "original": sample,
            "masked": masked,
            "policy_version": policy.version if policy else "unknown",
        }


# ==================== 全局动态脱敏服务 ====================

_dynamic_masking_service: Optional[DynamicMaskingService] = None


def get_dynamic_masking_service() -> DynamicMaskingService:
    """获取动态脱敏服务单例"""
    global _dynamic_masking_service
    if _dynamic_masking_service is None:
        _dynamic_masking_service = DynamicMaskingService()
    return _dynamic_masking_service


# ==================== 便捷函数 ====================

def mask_for_user_role(
    value: Any,
    column_name: str,
    user_role: str,
    sensitivity_level: str = "confidential",
) -> Any:
    """
    根据用户角色脱敏（便捷函数）

    Args:
        value: 原始值
        column_name: 列名
        user_role: 用户角色 (admin, analyst, reporter, guest)
        sensitivity_level: 敏感级别

    Returns:
        脱敏后的值
    """
    service = get_dynamic_masking_service()
    return service.mask_for_role(
        value, column_name, user_role, sensitivity_level
    )


def mask_query_result(
    result: List[Dict[str, Any]],
    user_role: str,
    table_metadata: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    脱敏查询结果（便捷函数）

    Args:
        result: SQL 查询结果
        user_role: 用户角色
        table_metadata: 表元数据

    Returns:
        脱敏后的结果
    """
    service = get_dynamic_masking_service()
    return service.mask_sql_result(result, user_role, table_metadata)
