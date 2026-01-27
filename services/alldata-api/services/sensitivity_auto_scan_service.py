"""
敏感数据自动扫描服务
Phase 2: 数据安全管理增强 - 自动化敏感数据识别与脱敏

功能：
- 自动发现数据库表并扫描敏感字段
- 基于采样数据进行敏感类型识别（正则 + AI）
- LLM 深度分析提升识别准确率
- 扫描结果自动回写到元数据列（sensitivity_level, sensitivity_type）
- 自动为识别到的敏感列生成脱敏规则
- 与 SmartSchedulerService 集成支持定期扫描
- 变更检测：只扫描新增或变更的表/列
"""

import logging
import os
import re
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from services.ai_service import get_ai_service, AIService

logger = logging.getLogger(__name__)

# 配置
AUTO_SCAN_SAMPLE_SIZE = int(os.getenv("AUTO_SCAN_SAMPLE_SIZE", "200"))
AUTO_SCAN_CONFIDENCE_THRESHOLD = int(os.getenv("AUTO_SCAN_CONFIDENCE_THRESHOLD", "60"))
AUTO_SCAN_BATCH_SIZE = int(os.getenv("AUTO_SCAN_BATCH_SIZE", "50"))


class AutoScanMode(str, Enum):
    """自动扫描模式"""
    FULL = "full"                   # 全量扫描所有表和列
    INCREMENTAL = "incremental"     # 仅扫描新增/变更的表和列
    TARGETED = "targeted"           # 指定数据库/表扫描


class AutoScanStatus(str, Enum):
    """自动扫描状态"""
    IDLE = "idle"
    DISCOVERING = "discovering"     # 发现表结构
    SCANNING = "scanning"           # 扫描敏感数据
    UPDATING = "updating"           # 更新元数据
    GENERATING_RULES = "generating_rules"  # 生成脱敏规则
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class AutoScanPolicy:
    """自动扫描策略配置"""
    policy_id: str = ""
    name: str = "默认扫描策略"
    mode: AutoScanMode = AutoScanMode.INCREMENTAL
    # 扫描范围
    databases: List[str] = field(default_factory=list)  # 空表示全部
    exclude_databases: List[str] = field(default_factory=lambda: ["information_schema", "mysql", "performance_schema", "sys"])
    exclude_table_patterns: List[str] = field(default_factory=lambda: ["tmp_*", "temp_*", "log_*", "backup_*"])
    # 扫描参数
    sample_size: int = AUTO_SCAN_SAMPLE_SIZE
    confidence_threshold: int = AUTO_SCAN_CONFIDENCE_THRESHOLD
    # 自动化行为
    auto_update_metadata: bool = True       # 自动更新元数据列的敏感信息
    auto_generate_masking_rules: bool = True  # 自动生成脱敏规则
    auto_notify: bool = True                # 发现敏感数据时通知
    # 调度
    schedule_cron: str = ""                 # cron 表达式（空表示不定期扫描）
    schedule_interval_hours: int = 0        # 间隔小时数（0表示不定期）
    # 所有者
    created_by: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "name": self.name,
            "mode": self.mode.value,
            "databases": self.databases,
            "exclude_databases": self.exclude_databases,
            "exclude_table_patterns": self.exclude_table_patterns,
            "sample_size": self.sample_size,
            "confidence_threshold": self.confidence_threshold,
            "auto_update_metadata": self.auto_update_metadata,
            "auto_generate_masking_rules": self.auto_generate_masking_rules,
            "auto_notify": self.auto_notify,
            "schedule_cron": self.schedule_cron,
            "schedule_interval_hours": self.schedule_interval_hours,
            "created_by": self.created_by,
        }


@dataclass
class AutoScanProgress:
    """自动扫描进度"""
    status: AutoScanStatus = AutoScanStatus.IDLE
    # 发现阶段
    total_databases: int = 0
    total_tables: int = 0
    total_columns: int = 0
    # 扫描阶段
    scanned_columns: int = 0
    sensitive_found: int = 0
    # 细分
    pii_count: int = 0
    financial_count: int = 0
    health_count: int = 0
    credential_count: int = 0
    # 更新阶段
    metadata_updated: int = 0
    masking_rules_created: int = 0
    # 时间
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: str = ""
    # 详细结果
    sensitive_columns: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def progress_percent(self) -> int:
        if self.total_columns == 0:
            return 0
        return min(100, int(self.scanned_columns / self.total_columns * 100))

    @property
    def duration_seconds(self) -> int:
        if not self.started_at:
            return 0
        end = self.completed_at or datetime.now()
        return int((end - self.started_at).total_seconds())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "progress_percent": self.progress_percent,
            "total_databases": self.total_databases,
            "total_tables": self.total_tables,
            "total_columns": self.total_columns,
            "scanned_columns": self.scanned_columns,
            "sensitive_found": self.sensitive_found,
            "breakdown": {
                "pii": self.pii_count,
                "financial": self.financial_count,
                "health": self.health_count,
                "credential": self.credential_count,
            },
            "metadata_updated": self.metadata_updated,
            "masking_rules_created": self.masking_rules_created,
            "duration_seconds": self.duration_seconds,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message,
            "sensitive_columns": self.sensitive_columns[:50],  # 限制返回数量
        }


# 列名敏感性推断规则（快速预筛选）
COLUMN_NAME_SENSITIVITY_HINTS = {
    "pii": {
        "phone": [r"phone", r"mobile", r"手机", r"电话", r"tel"],
        "email": [r"email", r"e_?mail", r"邮箱", r"邮件"],
        "id_card": [r"id_?card", r"身份证", r"identity", r"ssn", r"证件"],
        "name": [r"^name$", r"real_?name", r"full_?name", r"姓名", r"用户名"],
        "address": [r"address", r"地址", r"住址", r"addr"],
        "birthday": [r"birth", r"生日", r"出生"],
        "passport": [r"passport", r"护照"],
    },
    "financial": {
        "bank_card": [r"card_?no", r"card_?num", r"银行卡", r"账号"],
        "amount": [r"salary", r"wage", r"工资", r"收入", r"balance", r"余额"],
        "credit_card": [r"credit", r"信用卡"],
    },
    "health": {
        "medical": [r"medical", r"病历", r"诊断", r"处方", r"prescription"],
    },
    "credential": {
        "password": [r"password", r"passwd", r"pwd", r"密码"],
        "token": [r"token", r"secret", r"api_?key", r"密钥", r"access_key"],
    },
}

# 敏感级别映射
SENSITIVITY_LEVEL_MAP = {
    "pii": "confidential",
    "financial": "restricted",
    "health": "restricted",
    "credential": "restricted",
}

# 默认脱敏策略映射
DEFAULT_MASKING_STRATEGY = {
    "phone": "partial_mask",
    "email": "partial_mask",
    "id_card": "partial_mask",
    "name": "partial_mask",
    "address": "partial_mask",
    "birthday": "date_shift",
    "passport": "partial_mask",
    "bank_card": "partial_mask",
    "amount": "number_range",
    "credit_card": "partial_mask",
    "medical": "full_mask",
    "password": "full_mask",
    "token": "truncate_hash",
}


class SensitivityAutoScanService:
    """
    敏感数据自动扫描服务

    自动发现数据库表结构，扫描数据内容识别敏感字段，
    并将识别结果回写到元数据系统和脱敏规则库。

    扫描流程：
    1. 发现阶段：连接数据库获取所有表/列信息
    2. 预筛选：通过列名规则快速识别可能敏感的列
    3. 数据扫描：对候选列采样数据并用正则/AI进行内容分析
    4. LLM 深度分析：使用大语言模型深度分析复杂敏感数据
    5. 回写阶段：更新 MetadataColumn 的 sensitivity_* 字段
    6. 规则生成：为敏感列自动创建脱敏规则
    """

    def __init__(self, ai_service: Optional[AIService] = None):
        self._current_progress: Optional[AutoScanProgress] = None
        self._running = False
        self._lock = threading.Lock()
        self._ai_service = ai_service
        self._ai_available = False  # 缓存 AI 可用性状态

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def current_progress(self) -> Optional[AutoScanProgress]:
        return self._current_progress

    def start_auto_scan(
        self,
        policy: AutoScanPolicy = None,
        db_session=None,
    ) -> AutoScanProgress:
        """
        启动自动扫描

        Args:
            policy: 扫描策略配置
            db_session: 数据库会话（用于读取元数据和回写）

        Returns:
            AutoScanProgress 扫描进度对象
        """
        with self._lock:
            if self._running:
                logger.warning("自动扫描已在运行中")
                return self._current_progress

            if policy is None:
                policy = AutoScanPolicy()

            self._current_progress = AutoScanProgress(
                status=AutoScanStatus.DISCOVERING,
                started_at=datetime.now(),
            )
            self._running = True

        # 后台线程执行
        thread = threading.Thread(
            target=self._execute_auto_scan,
            args=(policy, db_session),
            daemon=True,
        )
        thread.start()

        return self._current_progress

    def get_progress(self) -> Dict[str, Any]:
        """获取当前扫描进度"""
        if self._current_progress is None:
            return {"status": "idle", "message": "尚未执行过自动扫描"}
        return self._current_progress.to_dict()

    def cancel_scan(self) -> bool:
        """取消正在运行的扫描"""
        if not self._running:
            return False
        self._running = False
        if self._current_progress:
            self._current_progress.status = AutoScanStatus.FAILED
            self._current_progress.error_message = "用户取消"
            self._current_progress.completed_at = datetime.now()
        return True

    def quick_scan_column(
        self,
        column_name: str,
        sample_values: List[Any],
        column_type: str = "",
    ) -> Dict[str, Any]:
        """
        快速单列敏感检测（无需数据库连接，用于实时检测）

        Args:
            column_name: 列名
            sample_values: 样本值列表
            column_type: 数据类型

        Returns:
            检测结果字典
        """
        result = {
            "column_name": column_name,
            "is_sensitive": False,
            "sensitivity_type": None,
            "sensitivity_sub_type": None,
            "sensitivity_level": None,
            "confidence": 0,
            "matched_by": None,
            "masking_strategy": None,
        }

        # 1. 列名规则匹配
        name_match = self._match_column_name(column_name)
        if name_match:
            result.update({
                "is_sensitive": True,
                "sensitivity_type": name_match["type"],
                "sensitivity_sub_type": name_match["sub_type"],
                "sensitivity_level": SENSITIVITY_LEVEL_MAP.get(name_match["type"], "internal"),
                "confidence": 70,
                "matched_by": "column_name",
                "masking_strategy": DEFAULT_MASKING_STRATEGY.get(name_match["sub_type"], "partial_mask"),
            })

        # 2. 数据内容扫描（提升置信度或发现新敏感列）
        if sample_values:
            content_match = self._scan_sample_values(sample_values)
            if content_match:
                if content_match["confidence"] > result.get("confidence", 0):
                    result.update({
                        "is_sensitive": True,
                        "sensitivity_type": content_match["type"],
                        "sensitivity_sub_type": content_match["sub_type"],
                        "sensitivity_level": SENSITIVITY_LEVEL_MAP.get(content_match["type"], "internal"),
                        "confidence": content_match["confidence"],
                        "matched_by": content_match["matched_by"],
                        "masking_strategy": DEFAULT_MASKING_STRATEGY.get(content_match["sub_type"], "partial_mask"),
                    })
                elif result.get("is_sensitive") and content_match["type"] == result.get("sensitivity_type"):
                    # 列名和内容都匹配，提升置信度
                    result["confidence"] = min(95, result["confidence"] + 15)
                    result["matched_by"] = "column_name+content"

        return result

    # ===== 内部执行方法 =====

    def _execute_auto_scan(self, policy: AutoScanPolicy, db_session=None):
        """执行自动扫描（后台线程）"""
        progress = self._current_progress
        try:
            # 检查 AI 服务可用性
            try:
                ai_service = self._ai_service or get_ai_service()
                self._ai_available = ai_service.config.enabled and ai_service.health_check()
                if self._ai_available:
                    logger.info("自动扫描: AI 深度分析已启用")
                else:
                    logger.info("自动扫描: AI 服务不可用，使用规则匹配")
            except Exception as e:
                logger.warning(f"自动扫描: AI 服务检查失败，使用规则匹配: {e}")
                self._ai_available = False

            # 阶段1: 发现表结构
            progress.status = AutoScanStatus.DISCOVERING
            columns_to_scan = self._discover_columns(policy, db_session)
            progress.total_columns = len(columns_to_scan)
            logger.info(f"自动扫描: 发现 {progress.total_databases} 个数据库, "
                        f"{progress.total_tables} 个表, {progress.total_columns} 个列")

            if not columns_to_scan:
                progress.status = AutoScanStatus.COMPLETED
                progress.completed_at = datetime.now()
                self._running = False
                return

            # 阶段2: 扫描敏感数据
            progress.status = AutoScanStatus.SCANNING
            sensitive_results = []

            for col_info in columns_to_scan:
                if not self._running:
                    break

                result = self._scan_single_column(col_info, policy, db_session)
                progress.scanned_columns += 1

                if result and result.get("is_sensitive"):
                    sensitive_results.append(result)
                    progress.sensitive_found += 1

                    # 更新分类计数
                    stype = result.get("sensitivity_type", "")
                    if stype == "pii":
                        progress.pii_count += 1
                    elif stype == "financial":
                        progress.financial_count += 1
                    elif stype == "health":
                        progress.health_count += 1
                    elif stype == "credential":
                        progress.credential_count += 1

                    progress.sensitive_columns.append({
                        "database": result.get("database", ""),
                        "table": result.get("table", ""),
                        "column": result.get("column", ""),
                        "type": stype,
                        "sub_type": result.get("sensitivity_sub_type", ""),
                        "level": result.get("sensitivity_level", ""),
                        "confidence": result.get("confidence", 0),
                    })

            if not self._running:
                progress.status = AutoScanStatus.FAILED
                progress.error_message = "扫描被取消"
                progress.completed_at = datetime.now()
                return

            # 阶段3: 更新元数据
            if policy.auto_update_metadata and db_session and sensitive_results:
                progress.status = AutoScanStatus.UPDATING
                progress.metadata_updated = self._update_metadata(
                    sensitive_results, db_session
                )

            # 阶段4: 生成脱敏规则
            if policy.auto_generate_masking_rules and db_session and sensitive_results:
                progress.status = AutoScanStatus.GENERATING_RULES
                progress.masking_rules_created = self._generate_masking_rules(
                    sensitive_results, db_session
                )

            progress.status = AutoScanStatus.COMPLETED
            progress.completed_at = datetime.now()

            logger.info(
                f"自动扫描完成: 扫描 {progress.scanned_columns} 列, "
                f"发现敏感列 {progress.sensitive_found}, "
                f"更新元数据 {progress.metadata_updated}, "
                f"生成规则 {progress.masking_rules_created}, "
                f"耗时 {progress.duration_seconds}s"
            )

        except Exception as e:
            logger.error(f"自动扫描失败: {e}", exc_info=True)
            progress.status = AutoScanStatus.FAILED
            progress.error_message = str(e)
            progress.completed_at = datetime.now()
        finally:
            self._running = False

    def _discover_columns(
        self,
        policy: AutoScanPolicy,
        db_session=None,
    ) -> List[Dict[str, Any]]:
        """发现需要扫描的列"""
        columns = []

        if db_session is None:
            logger.warning("无数据库会话，尝试从元数据表获取列信息")
            return columns

        try:
            from models.metadata import MetadataDatabase, MetadataTable, MetadataColumn

            # 查询元数据库
            query = db_session.query(MetadataDatabase)
            if policy.databases:
                query = query.filter(MetadataDatabase.database_name.in_(policy.databases))

            databases = query.all()
            self._current_progress.total_databases = len(databases)

            for db in databases:
                db_name = db.database_name
                if db_name in policy.exclude_databases:
                    continue

                # 查询表
                tables = db_session.query(MetadataTable).filter_by(
                    database_id=db.id
                ).all()

                for table in tables:
                    table_name = table.table_name

                    # 检查排除模式
                    excluded = False
                    for pattern in policy.exclude_table_patterns:
                        regex_pattern = pattern.replace("*", ".*")
                        if re.match(regex_pattern, table_name, re.IGNORECASE):
                            excluded = True
                            break
                    if excluded:
                        continue

                    self._current_progress.total_tables += 1

                    # 查询列
                    cols = db_session.query(MetadataColumn).filter_by(
                        table_id=table.id
                    ).all()

                    for col in cols:
                        # 增量模式：跳过已标注的列
                        if policy.mode == AutoScanMode.INCREMENTAL:
                            if col.sensitivity_type and col.sensitivity_type != "none":
                                if col.ai_confidence and col.ai_confidence >= policy.confidence_threshold:
                                    continue

                        columns.append({
                            "database": db_name,
                            "table": table_name,
                            "column": col.column_name,
                            "column_id": col.id,
                            "column_type": col.column_type or "",
                            "table_id": table.id,
                            "database_id": db.id,
                        })

        except Exception as e:
            logger.error(f"发现列信息失败: {e}", exc_info=True)

        return columns

    def _scan_single_column(
        self,
        col_info: Dict[str, Any],
        policy: AutoScanPolicy,
        db_session=None,
    ) -> Optional[Dict[str, Any]]:
        """扫描单个列"""
        column_name = col_info["column"]
        column_type = col_info.get("column_type", "")

        # 1. 列名快速预筛选
        name_match = self._match_column_name(column_name)

        # 2. 尝试获取样本数据
        sample_values = []
        if db_session:
            sample_values = self._fetch_sample_data(
                col_info["database"],
                col_info["table"],
                column_name,
                policy.sample_size,
                db_session,
            )

        # 3. 正则表达式内容分析
        content_match = None
        if sample_values:
            content_match = self._scan_sample_values(sample_values)

        # 4. LLM 深度分析（当正则匹配置信度不足或需要验证时）
        ai_match = None
        if sample_values and self._ai_available:
            # 使用 AI 分析的情况:
            # - 列名匹配但正则没匹配（需要验证）
            # - 正则匹配但置信度较低
            # - 都没匹配但样本数据看起来像敏感数据（通过 AI 兜底检测）
            should_use_ai = (
                (name_match and not content_match) or
                (content_match and content_match.get("confidence", 0) < 80) or
                (not name_match and not content_match)  # AI 兜底
            )
            if should_use_ai:
                ai_match = self._ai_analyze_sensitivity(
                    column_name, column_type, sample_values
                )

        # 5. 综合判断 - 优先级: AI > 正则+列名 > 正则 > 列名
        best_match = None

        # AI 结果优先（如果置信度足够高）
        if ai_match and ai_match.get("is_sensitive") and ai_match.get("confidence", 0) >= 70:
            best_match = {
                "type": ai_match["sensitivity_type"],
                "sub_type": ai_match.get("sensitivity_type", ""),
                "confidence": ai_match["confidence"],
                "matched_by": "ai_analysis",
                "ai_reason": ai_match.get("reason", ""),
                "suggested_masking": ai_match.get("suggested_masking", ""),
            }
            # 如果 AI 和正则/列名都匹配，提升置信度
            if (content_match and content_match.get("type") == ai_match["sensitivity_type"]) or \
               (name_match and name_match.get("type") == ai_match["sensitivity_type"]):
                best_match["confidence"] = min(98, best_match["confidence"] + 10)
                best_match["matched_by"] = "ai_analysis+regex" if content_match else "ai_analysis+column_name"

        # 正则+列名组合
        elif name_match and content_match:
            if content_match["confidence"] >= name_match.get("confidence", 70):
                best_match = content_match
                best_match["confidence"] = min(95, best_match["confidence"] + 10)
                best_match["matched_by"] = "column_name+content"
            else:
                best_match = {
                    "type": name_match["type"],
                    "sub_type": name_match["sub_type"],
                    "confidence": min(95, name_match.get("confidence", 70) + 10),
                    "matched_by": "column_name+content",
                }
        elif content_match:
            best_match = content_match
        elif name_match:
            best_match = {
                "type": name_match["type"],
                "sub_type": name_match["sub_type"],
                "confidence": name_match.get("confidence", 70),
                "matched_by": "column_name",
            }

        if best_match and best_match["confidence"] >= policy.confidence_threshold:
            return {
                "database": col_info["database"],
                "table": col_info["table"],
                "column": column_name,
                "column_id": col_info.get("column_id"),
                "is_sensitive": True,
                "sensitivity_type": best_match["type"],
                "sensitivity_sub_type": best_match.get("sub_type", ""),
                "sensitivity_level": SENSITIVITY_LEVEL_MAP.get(best_match["type"], "internal"),
                "confidence": best_match["confidence"],
                "matched_by": best_match.get("matched_by", "unknown"),
                "masking_strategy": best_match.get("suggested_masking") or \
                    DEFAULT_MASKING_STRATEGY.get(best_match.get("sub_type", ""), "partial_mask"),
                "sample_count": len(sample_values),
                "ai_reason": best_match.get("ai_reason", ""),
            }

        return None

    def _ai_analyze_sensitivity(
        self,
        column_name: str,
        column_type: str,
        sample_values: List[Any],
    ) -> Optional[Dict[str, Any]]:
        """
        使用 LLM 深度分析列数据的敏感性

        Args:
            column_name: 列名
            column_type: 数据类型
            sample_values: 样本值列表

        Returns:
            AI 分析结果，包含敏感性判断、类型、置信度和理由
        """
        try:
            ai_service = self._ai_service or get_ai_service()

            # 转换样本值为字符串
            str_values = [str(v)[:100] for v in sample_values[:10] if v is not None]

            if not str_values:
                return None

            result = ai_service.analyze_sensitivity(
                column_name=column_name,
                data_type=column_type,
                sample_values=str_values,
            )

            # 转换 AI 服务返回的结果格式
            if result.get("is_sensitive"):
                # 将 AI 的 confidence (0-1) 转换为我们的格式 (0-100)
                confidence = result.get("confidence", 0.5)
                if isinstance(confidence, float) and confidence <= 1:
                    confidence = int(confidence * 100)

                return {
                    "is_sensitive": True,
                    "sensitivity_type": result.get("sensitivity_type", "pii"),
                    "sensitivity_level": result.get("sensitivity_level", "confidential"),
                    "confidence": confidence,
                    "reason": result.get("reason", ""),
                    "suggested_masking": result.get("suggested_masking", "partial_mask"),
                }

            return {
                "is_sensitive": False,
                "confidence": 0,
            }

        except Exception as e:
            logger.debug(f"AI 敏感性分析失败 [{column_name}]: {e}")
            return None

    def _match_column_name(self, column_name: str) -> Optional[Dict[str, Any]]:
        """通过列名规则匹配敏感类型"""
        col_lower = column_name.lower()
        for sensitivity_type, sub_types in COLUMN_NAME_SENSITIVITY_HINTS.items():
            for sub_type, patterns in sub_types.items():
                for pattern in patterns:
                    if re.search(pattern, col_lower, re.IGNORECASE):
                        return {
                            "type": sensitivity_type,
                            "sub_type": sub_type,
                            "confidence": 70,
                        }
        return None

    def _scan_sample_values(self, values: List[Any]) -> Optional[Dict[str, Any]]:
        """扫描样本值识别敏感类型"""
        if not values:
            return None

        # 将值转为字符串
        str_values = [str(v) for v in values if v is not None and str(v).strip()]
        if not str_values:
            return None

        # 敏感数据正则模式
        content_patterns = {
            ("pii", "phone"): [
                r"^1[3-9]\d{9}$",
                r"^(?:\+86)?1[3-9]\d{9}$",
            ],
            ("pii", "email"): [
                r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$",
            ],
            ("pii", "id_card"): [
                r"^\d{17}[\dXx]$",
                r"^\d{15}$",
            ],
            ("financial", "bank_card"): [
                r"^\d{16,19}$",
            ],
            ("credential", "password"): [
                # 不太适合正则检测，跳过
            ],
            ("pii", "address"): [
                r".*(?:省|市|区|县|镇|村|路|街|号|栋|单元|室).*",
            ],
        }

        # 检查每种模式的匹配率
        best_match = None
        best_rate = 0

        for (stype, sub_type), patterns in content_patterns.items():
            if not patterns:
                continue
            matched = 0
            sample = str_values[:100]
            for val in sample:
                for pat in patterns:
                    if re.match(pat, val.strip()):
                        matched += 1
                        break

            match_rate = matched / len(sample) if sample else 0

            if match_rate > 0.3 and match_rate > best_rate:
                best_rate = match_rate
                confidence = int(min(95, 60 + match_rate * 30))
                best_match = {
                    "type": stype,
                    "sub_type": sub_type,
                    "confidence": confidence,
                    "match_rate": round(match_rate, 3),
                    "matched_by": "content_regex",
                }

        return best_match

    def _fetch_sample_data(
        self,
        database: str,
        table: str,
        column: str,
        sample_size: int,
        db_session,
    ) -> List[Any]:
        """从数据库获取样本数据"""
        try:
            from sqlalchemy import text
            # 使用 LIMIT 采样（简单方式）
            sql = text(f"SELECT `{column}` FROM `{database}`.`{table}` "
                       f"WHERE `{column}` IS NOT NULL AND `{column}` != '' "
                       f"LIMIT :limit")
            result = db_session.execute(sql, {"limit": sample_size})
            return [row[0] for row in result]
        except Exception as e:
            logger.debug(f"采样数据获取失败 [{database}.{table}.{column}]: {e}")
            return []

    def _update_metadata(
        self,
        results: List[Dict[str, Any]],
        db_session,
    ) -> int:
        """将扫描结果回写到元数据列"""
        updated = 0
        try:
            from models.metadata import MetadataColumn

            for res in results:
                col_id = res.get("column_id")
                if not col_id:
                    continue

                col = db_session.query(MetadataColumn).get(col_id)
                if col is None:
                    continue

                col.sensitivity_type = res["sensitivity_type"]
                col.sensitivity_level = res["sensitivity_level"]
                col.ai_confidence = res["confidence"]
                col.ai_annotated_at = datetime.now()

                updated += 1

            if updated > 0:
                db_session.commit()
                logger.info(f"自动扫描: 更新 {updated} 个列的敏感信息")

        except Exception as e:
            logger.error(f"更新元数据失败: {e}")
            try:
                db_session.rollback()
            except Exception:
                pass

        return updated

    def _generate_masking_rules(
        self,
        results: List[Dict[str, Any]],
        db_session,
    ) -> int:
        """为识别到的敏感列自动生成脱敏规则"""
        created = 0
        try:
            from models.security_audit import MaskingRule

            for res in results:
                col_name = res["column"]
                stype = res["sensitivity_type"]
                sub_type = res.get("sensitivity_sub_type", "")
                strategy = res.get("masking_strategy", "partial_mask")

                # 检查是否已有规则
                existing = db_session.query(MaskingRule).filter(
                    MaskingRule.column_pattern.isnot(None),
                    MaskingRule.sensitivity_type == stype,
                ).all()

                # 检查是否已有匹配该列的规则
                already_matched = False
                for rule in existing:
                    if rule.column_pattern and re.search(rule.column_pattern, col_name, re.IGNORECASE):
                        already_matched = True
                        break

                if already_matched:
                    continue

                # 创建新规则
                rule = MaskingRule(
                    name=f"自动生成-{sub_type}-{col_name}",
                    sensitivity_type=stype,
                    sensitivity_level=res.get("sensitivity_level", "confidential"),
                    column_pattern=re.escape(col_name),
                    strategy=strategy,
                    priority=0,
                    is_active=True,
                    is_system=False,
                    description=f"自动扫描识别 [{res['database']}.{res['table']}.{col_name}] 为 {stype}/{sub_type}",
                )
                db_session.add(rule)
                created += 1

            if created > 0:
                db_session.commit()
                logger.info(f"自动扫描: 生成 {created} 条脱敏规则")

        except Exception as e:
            logger.error(f"生成脱敏规则失败: {e}")
            try:
                db_session.rollback()
            except Exception:
                pass

        return created

    def get_scan_summary(self) -> Dict[str, Any]:
        """获取最近一次扫描的摘要"""
        if not self._current_progress:
            return {"has_scan": False}

        progress = self._current_progress
        return {
            "has_scan": True,
            "status": progress.status.value,
            "total_scanned": progress.scanned_columns,
            "sensitive_found": progress.sensitive_found,
            "breakdown": {
                "pii": progress.pii_count,
                "financial": progress.financial_count,
                "health": progress.health_count,
                "credential": progress.credential_count,
            },
            "metadata_updated": progress.metadata_updated,
            "rules_created": progress.masking_rules_created,
            "duration_seconds": progress.duration_seconds,
            "last_completed": progress.completed_at.isoformat() if progress.completed_at else None,
        }


# 全局实例
_auto_scan_service: Optional[SensitivityAutoScanService] = None


def get_sensitivity_auto_scan_service(
    ai_service: Optional[AIService] = None,
) -> SensitivityAutoScanService:
    """
    获取敏感数据自动扫描服务单例

    Args:
        ai_service: AI 服务实例，如果为 None 则使用默认实例
    """
    global _auto_scan_service
    if _auto_scan_service is None:
        _auto_scan_service = SensitivityAutoScanService(ai_service=ai_service)
    return _auto_scan_service
