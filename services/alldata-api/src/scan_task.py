"""
敏感数据扫描任务服务
Phase 1.1: 批量扫描任务管理、异步处理、结果校验
"""

import json
import logging
import os
import re
import threading
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed

from sqlalchemy.orm import Session

from database import db_manager
from models.sensitivity import (
    SensitivityScanTask, SensitivityScanResult, SensitivityPattern,
    generate_scan_id
)
from ai_annotation import AIAnnotationService, SENSITIVITY_PATTERNS

logger = logging.getLogger(__name__)

# 扫描配置
MAX_WORKERS = int(os.getenv("SCAN_MAX_WORKERS", "4"))
BATCH_SIZE = int(os.getenv("SCAN_BATCH_SIZE", "100"))
SCAN_TIMEOUT = int(os.getenv("SCAN_TIMEOUT_SECONDS", "3600"))

# 扩展的敏感子类型定义
SENSITIVITY_SUBTYPES = {
    "pii": {
        "phone": {
            "patterns": [r"1[3-9]\d{9}", r"\+86\s*1[3-9]\d{9}"],
            "level": "confidential",
            "masking": "mask",
            "keywords": ["手机", "phone", "mobile", "tel", "联系电话"]
        },
        "email": {
            "patterns": [r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"],
            "level": "confidential",
            "masking": "mask",
            "keywords": ["邮箱", "email", "e_mail", "mail"]
        },
        "id_card": {
            "patterns": [r"\d{17}[\dXx]", r"\d{15}"],
            "level": "restricted",
            "masking": "mask",
            "keywords": ["身份证", "id_card", "identity", "ssn", "证件号"]
        },
        "passport": {
            "patterns": [r"[A-Z]{1,2}\d{6,9}"],
            "level": "restricted",
            "masking": "mask",
            "keywords": ["护照", "passport"]
        },
        "name": {
            "patterns": [],
            "level": "confidential",
            "masking": "mask",
            "keywords": ["姓名", "name", "full_name", "real_name", "user_name", "真实姓名"]
        },
        "address": {
            "patterns": [],
            "level": "confidential",
            "masking": "mask",
            "keywords": ["地址", "address", "addr", "location", "住址", "联系地址"]
        },
        "birthday": {
            "patterns": [r"\d{4}[-/年]\d{1,2}[-/月]\d{1,2}[日]?"],
            "level": "confidential",
            "masking": "mask",
            "keywords": ["生日", "birthday", "birth_date", "dob", "出生日期"]
        },
    },
    "financial": {
        "bank_card": {
            "patterns": [r"\d{16,19}"],
            "level": "restricted",
            "masking": "mask",
            "keywords": ["银行卡", "bank_card", "card_no", "card_number", "借记卡", "信用卡"]
        },
        "credit_card": {
            "patterns": [r"\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}"],
            "level": "restricted",
            "masking": "mask",
            "keywords": ["信用卡", "credit_card"]
        },
        "cvv": {
            "patterns": [r"\d{3,4}"],
            "level": "restricted",
            "masking": "redact",
            "keywords": ["cvv", "cvc", "安全码", "验证码"]
        },
        "account": {
            "patterns": [],
            "level": "confidential",
            "masking": "hash",
            "keywords": ["账户", "account", "account_no", "账号"]
        },
        "amount": {
            "patterns": [],
            "level": "internal",
            "masking": "none",
            "keywords": ["金额", "amount", "balance", "余额", "工资", "salary", "income"]
        },
    },
    "health": {
        "diagnosis": {
            "patterns": [],
            "level": "restricted",
            "masking": "encrypt",
            "keywords": ["诊断", "diagnosis", "disease", "疾病", "病症"]
        },
        "medical_record": {
            "patterns": [],
            "level": "restricted",
            "masking": "encrypt",
            "keywords": ["病历", "medical_record", "health_record", "体检"]
        },
        "prescription": {
            "patterns": [],
            "level": "restricted",
            "masking": "encrypt",
            "keywords": ["处方", "prescription", "medication", "用药"]
        },
    },
    "credential": {
        "password": {
            "patterns": [],
            "level": "restricted",
            "masking": "redact",
            "keywords": ["密码", "password", "passwd", "pwd"]
        },
        "api_key": {
            "patterns": [r"[A-Za-z0-9]{32,}"],
            "level": "restricted",
            "masking": "redact",
            "keywords": ["api_key", "apikey", "access_key", "secret_key"]
        },
        "token": {
            "patterns": [r"ey[A-Za-z0-9-]+\.[A-Za-z0-9-]+\.[A-Za-z0-9-]+"],
            "level": "restricted",
            "masking": "redact",
            "keywords": ["token", "access_token", "refresh_token", "session"]
        },
    }
}


class ScanTaskManager:
    """扫描任务管理器"""

    def __init__(self):
        self.ai_service = AIAnnotationService()
        self.executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)
        self.active_tasks: Dict[str, threading.Thread] = {}
        self.task_callbacks: Dict[str, List[Callable]] = {}

    def create_task(
        self,
        target_type: str,
        target_id: Optional[str] = None,
        target_name: Optional[str] = None,
        scan_mode: str = "full",
        sample_rate: int = 100,
        confidence_threshold: int = 70,
        databases: Optional[List[str]] = None,
        tables: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None,
        created_by: str = "admin",
        auto_start: bool = False,
    ) -> SensitivityScanTask:
        """
        创建扫描任务

        Args:
            target_type: 目标类型 (database, table, column, dataset)
            target_id: 目标ID
            target_name: 目标名称
            scan_mode: 扫描模式 (full, incremental, sampling)
            sample_rate: 采样率
            confidence_threshold: 置信度阈值
            databases: 数据库列表
            tables: 表列表
            exclude_patterns: 排除模式
            created_by: 创建者
            auto_start: 是否自动启动

        Returns:
            扫描任务对象
        """
        task_id = generate_scan_id()

        task = SensitivityScanTask(
            task_id=task_id,
            target_type=target_type,
            target_id=target_id,
            target_name=target_name,
            scan_mode=scan_mode,
            sample_rate=sample_rate,
            confidence_threshold=confidence_threshold,
            created_by=created_by,
        )

        if databases:
            task.set_databases(databases)
        if tables:
            task.set_tables(tables)
        if exclude_patterns:
            task.set_exclude_patterns(exclude_patterns)

        with db_manager.get_session() as session:
            session.add(task)
            session.commit()
            session.refresh(task)

        if auto_start:
            self.start_task(task_id)

        return task

    def start_task(self, task_id: str) -> bool:
        """
        启动扫描任务

        Args:
            task_id: 任务ID

        Returns:
            是否成功启动
        """
        with db_manager.get_session() as session:
            task = session.query(SensitivityScanTask).filter(
                SensitivityScanTask.task_id == task_id
            ).first()

            if not task:
                logger.error(f"Task {task_id} not found")
                return False

            if task.status == "running":
                logger.warning(f"Task {task_id} is already running")
                return False

            task.status = "running"
            task.started_at = datetime.utcnow()
            session.commit()

        # 在后台线程中执行扫描
        thread = threading.Thread(
            target=self._run_scan_task,
            args=(task_id,),
            daemon=True
        )
        self.active_tasks[task_id] = thread
        thread.start()

        return True

    def _run_scan_task(self, task_id: str):
        """
        执行扫描任务（后台线程）

        Args:
            task_id: 任务ID
        """
        try:
            with db_manager.get_session() as session:
                task = session.query(SensitivityScanTask).filter(
                    SensitivityScanTask.task_id == task_id
                ).first()

                if not task:
                    logger.error(f"Task {task_id} not found")
                    return

                # 获取扫描目标
                columns_to_scan = self._get_columns_to_scan(task, session)

                if not columns_to_scan:
                    task.status = "completed"
                    task.completed_at = datetime.utcnow()
                    task.progress = 100
                    session.commit()
                    return

                task.total_columns = len(columns_to_scan)
                session.commit()

                # 执行扫描
                results = []
                pii_count = 0
                financial_count = 0
                health_count = 0
                credential_count = 0

                for i, column_info in enumerate(columns_to_scan):
                    # 检查任务是否被取消
                    session.refresh(task)
                    if task.status == "cancelled":
                        return

                    # 扫描单个列
                    result = self._scan_column(
                        column_info,
                        task.confidence_threshold,
                        task.sample_rate,
                        session
                    )

                    if result:
                        results.append(result)

                        # 更新统计
                        if result["sensitivity_type"] == "pii":
                            pii_count += 1
                        elif result["sensitivity_type"] == "financial":
                            financial_count += 1
                        elif result["sensitivity_type"] == "health":
                            health_count += 1
                        elif result["sensitivity_type"] == "credential":
                            credential_count += 1

                    # 更新进度
                    if (i + 1) % BATCH_SIZE == 0 or i == len(columns_to_scan) - 1:
                        task.scanned_columns = i + 1
                        task.progress = int((i + 1) / len(columns_to_scan) * 100)
                        task.pii_count = pii_count
                        task.financial_count = financial_count
                        task.health_count = health_count
                        task.credential_count = credential_count
                        task.sensitive_found = len(results)
                        session.commit()

                # 保存结果
                for result in results:
                    scan_result = SensitivityScanResult(
                        result_id=f"res_{uuid.uuid4().hex[:12]}",
                        task_id=task_id,
                        database_name=result.get("database_name"),
                        table_name=result.get("table_name"),
                        column_name=result["column_name"],
                        sensitivity_type=result.get("sensitivity_type"),
                        sensitivity_sub_type=result.get("sensitivity_sub_type"),
                        sensitivity_level=result.get("sensitivity_level"),
                        confidence=result.get("confidence"),
                        matched_pattern=result.get("matched_pattern"),
                    )
                    scan_result.set_sample_values(result.get("sample_values", []))
                    session.add(scan_result)

                # 更新任务状态
                task.status = "completed"
                task.completed_at = datetime.utcnow()
                task.progress = 100
                session.commit()

                # 触发回调
                self._trigger_callbacks(task_id, "completed", task)

        except Exception as e:
            logger.error(f"Error running scan task {task_id}: {e}")
            with db_manager.get_session() as session:
                task = session.query(SensitivityScanTask).filter(
                    SensitivityScanTask.task_id == task_id
                ).first()
                if task:
                    task.status = "failed"
                    task.error_message = str(e)
                    task.completed_at = datetime.utcnow()
                    session.commit()
                    self._trigger_callbacks(task_id, "failed", task)

        finally:
            # 清理线程引用
            if task_id in self.active_tasks:
                del self.active_tasks[task_id]

    def _get_columns_to_scan(
        self,
        task: SensitivityScanTask,
        session: Session
    ) -> List[Dict[str, Any]]:
        """
        获取需要扫描的列列表

        Args:
            task: 扫描任务
            session: 数据库会话

        Returns:
            列信息列表
        """
        from models.metadata import MetadataColumn, MetadataTable

        columns_to_scan = []
        databases = task.get_databases()
        tables = task.get_tables()
        exclude_patterns = task.get_exclude_patterns()

        # 构建查询
        query = session.query(
            MetadataColumn.column_name,
            MetadataColumn.column_type,
            MetadataTable.table_name,
            MetadataTable.database_name,
        ).join(
            MetadataTable,
            (MetadataColumn.table_name == MetadataTable.table_name) &
            (MetadataColumn.database_name == MetadataTable.database_name)
        )

        # 应用过滤条件
        if databases:
            query = query.filter(MetadataTable.database_name.in_(databases))

        if tables:
            query = query.filter(MetadataTable.table_name.in_(tables))

        # 应用排除模式
        for pattern in exclude_patterns:
            query = query.filter(~MetadataColumn.column_name.like(pattern))

        results = query.all()

        for col_name, col_type, table_name, db_name in results:
            # 检查是否应该排除
            should_exclude = False
            for pattern in exclude_patterns:
                if re.search(pattern, col_name, re.IGNORECASE):
                    should_exclude = True
                    break

            if not should_exclude:
                columns_to_scan.append({
                    "column_name": col_name,
                    "column_type": col_type,
                    "table_name": table_name,
                    "database_name": db_name,
                })

        return columns_to_scan

    def _scan_column(
        self,
        column_info: Dict[str, Any],
        confidence_threshold: int,
        sample_rate: int,
        session: Session
    ) -> Optional[Dict[str, Any]]:
        """
        扫描单个列

        Args:
            column_info: 列信息
            confidence_threshold: 置信度阈值
            sample_rate: 采样率
            session: 数据库会话

        Returns:
            扫描结果或None
        """
        col_name = column_info["column_name"]
        col_type = column_info["column_type"]
        table_name = column_info["table_name"]
        db_name = column_info["database_name"]

        # 使用AI服务进行标注
        annotation = self.ai_service.annotate_column(
            column_name=col_name,
            column_type=col_type,
            table_name=table_name,
            use_llm=False,  # 先用规则，如需要再用LLM
        )

        # 检查是否达到阈值
        if annotation["ai_confidence"] < confidence_threshold:
            # 尝试使用LLM增强
            annotation = self.ai_service.annotate_column(
                column_name=col_name,
                column_type=col_type,
                table_name=table_name,
                use_llm=True,
            )

        if annotation["ai_confidence"] < confidence_threshold:
            return None

        # 确定敏感子类型
        sub_type = self._detect_sub_type(col_name, annotation["sensitivity_type"])

        # 如果检测到敏感数据
        if annotation["sensitivity_type"] != "none":
            return {
                "column_name": col_name,
                "database_name": db_name,
                "table_name": table_name,
                "sensitivity_type": annotation["sensitivity_type"],
                "sensitivity_sub_type": sub_type,
                "sensitivity_level": annotation["sensitivity_level"],
                "confidence": annotation["ai_confidence"],
                "matched_pattern": f"Rule-based: {annotation['sensitivity_type']}",
                "sample_values": [],
            }

        return None

    def _detect_sub_type(self, column_name: str, sensitivity_type: str) -> Optional[str]:
        """
        检测敏感子类型

        Args:
            column_name: 列名
            sensitivity_type: 敏感类型

        Returns:
            子类型或None
        """
        if sensitivity_type not in SENSITIVITY_SUBTYPES:
            return None

        col_lower = column_name.lower()

        for sub_type, config in SENSITIVITY_SUBTYPES[sensitivity_type].items():
            # 检查关键词
            for keyword in config["keywords"]:
                if keyword.lower() in col_lower:
                    return sub_type

            # 检查正则（如果列名看起来像数据样本）
            if config["patterns"]:
                for pattern in config["patterns"]:
                    if re.search(pattern, column_name, re.IGNORECASE):
                        return sub_type

        return None

    def cancel_task(self, task_id: str) -> bool:
        """
        取消扫描任务

        Args:
            task_id: 任务ID

        Returns:
            是否成功取消
        """
        with db_manager.get_session() as session:
            task = session.query(SensitivityScanTask).filter(
                SensitivityScanTask.task_id == task_id
            ).first()

            if not task:
                return False

            if task.status in ["completed", "failed", "cancelled"]:
                return False

            task.status = "cancelled"
            session.commit()
            return True

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        获取任务状态

        Args:
            task_id: 任务ID

        Returns:
            任务状态信息
        """
        with db_manager.get_session() as session:
            task = session.query(SensitivityScanTask).filter(
                SensitivityScanTask.task_id == task_id
            ).first()

            if not task:
                return None

            return task.to_dict()

    def get_task_results(
        self,
        task_id: str,
        verified_only: bool = False,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        获取任务结果

        Args:
            task_id: 任务ID
            verified_only: 仅获取已校验结果
            limit: 限制数量
            offset: 偏移量

        Returns:
            结果列表
        """
        with db_manager.get_session() as session:
            query = session.query(SensitivityScanResult).filter(
                SensitivityScanResult.task_id == task_id
            )

            if verified_only:
                query = query.filter(SensitivityScanResult.verified == True)

            results = query.order_by(
                SensitivityScanResult.created_at.desc()
            ).limit(limit).offset(offset).all()

            return [r.to_dict() for r in results]

    def verify_result(
        self,
        result_id: str,
        verified_result: str,
        verified_by: str,
        sensitivity_type: Optional[str] = None,
        sensitivity_level: Optional[str] = None,
    ) -> bool:
        """
        校验扫描结果

        Args:
            result_id: 结果ID
            verified_result: 校验结果 (confirmed, rejected, modified)
            verified_by: 校验人
            sensitivity_type: 修正后的敏感类型
            sensitivity_level: 修正后的敏感级别

        Returns:
            是否成功
        """
        with db_manager.get_session() as session:
            result = session.query(SensitivityScanResult).filter(
                SensitivityScanResult.result_id == result_id
            ).first()

            if not result:
                return False

            # 保存原始值
            if verified_result == "modified":
                result.original_type = result.sensitivity_type
                result.original_level = result.sensitivity_level
                result.original_confidence = result.confidence

                # 更新为新值
                if sensitivity_type:
                    result.sensitivity_type = sensitivity_type
                if sensitivity_level:
                    result.sensitivity_level = sensitivity_level

            result.verified = True
            result.verified_result = verified_result
            result.verified_by = verified_by
            result.verified_at = datetime.utcnow()

            session.commit()
            return True

    def register_callback(self, task_id: str, callback: Callable):
        """
        注册任务完成回调

        Args:
            task_id: 任务ID
            callback: 回调函数
        """
        if task_id not in self.task_callbacks:
            self.task_callbacks[task_id] = []
        self.task_callbacks[task_id].append(callback)

    def _trigger_callbacks(
        self,
        task_id: str,
        status: str,
        task: SensitivityScanTask
    ):
        """触发回调"""
        if task_id in self.task_callbacks:
            for callback in self.task_callbacks[task_id]:
                try:
                    callback(status, task)
                except Exception as e:
                    logger.error(f"Error in callback: {e}")
            del self.task_callbacks[task_id]

    def get_statistics(self) -> Dict[str, Any]:
        """
        获取扫描统计信息

        Returns:
            统计信息
        """
        with db_manager.get_session() as session:
            total_tasks = session.query(SensitivityScanTask).count()
            running_tasks = session.query(SensitivityScanTask).filter(
                SensitivityScanTask.status == "running"
            ).count()
            completed_tasks = session.query(SensitivityScanTask).filter(
                SensitivityScanTask.status == "completed"
            ).count()

            total_results = session.query(SensitivityScanResult).count()
            verified_results = session.query(SensitivityScanResult).filter(
                SensitivityScanResult.verified == True
            ).count()

            return {
                "total_tasks": total_tasks,
                "running_tasks": running_tasks,
                "completed_tasks": completed_tasks,
                "total_results": total_results,
                "verified_results": verified_results,
                "active_threads": len(self.active_tasks),
            }


# 全局实例
_scan_manager: Optional[ScanTaskManager] = None


def get_scan_manager() -> ScanTaskManager:
    """获取扫描管理器单例"""
    global _scan_manager
    if _scan_manager is None:
        _scan_manager = ScanTaskManager()
    return _scan_manager
