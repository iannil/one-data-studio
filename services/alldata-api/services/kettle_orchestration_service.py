"""
Kettle 自动化编排服务
Phase 2: AI 规则驱动的完整 Kettle 转换自动生成与执行

功能：
- 从元数据自动生成完整的 Kettle 转换流水线
- 集成 AI 清洗建议 → Kettle 步骤自动注入
- 集成 AI 脱敏规则 → Kettle 脱敏步骤自动注入
- 集成 AI 填充规则 → Kettle 填充步骤自动注入
- 端到端编排：元数据分析 → 规则推荐 → Kettle生成 → 执行 → 结果回写
- 任务历史记录和执行跟踪
- ETL 完成回调：自动编目、MinIO 上传、通知
- 长时间运行任务的状态轮询
- 数据质量报告生成和导出
- 支持 Carte 远程执行和本地 CLI 执行
"""

import asyncio
import logging
import os
import uuid
import time
import threading
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

# 配置
KETTLE_OUTPUT_DIR = os.getenv("KETTLE_OUTPUT_DIR", "/tmp/kettle_output")
KETTLE_POLL_INTERVAL = int(os.getenv("KETTLE_POLL_INTERVAL", "5"))  # 轮询间隔秒数
KETTLE_POLL_TIMEOUT = int(os.getenv("KETTLE_POLL_TIMEOUT", "3600"))  # 轮询超时秒数


class OrchestrationStatus(str, Enum):
    """编排状态"""
    PENDING = "pending"
    ANALYZING = "analyzing"           # 元数据分析
    RECOMMENDING = "recommending"     # AI 推荐规则
    GENERATING = "generating"         # 生成 Kettle XML
    EXECUTING = "executing"           # 执行 Kettle 转换
    COMPLETED = "completed"
    FAILED = "failed"


class PipelineType(str, Enum):
    """流水线类型"""
    DATA_SYNC = "data_sync"           # 数据同步
    DATA_CLEANING = "data_cleaning"   # 数据清洗
    DATA_MASKING = "data_masking"     # 数据脱敏
    FULL_ETL = "full_etl"            # 完整 ETL（同步+清洗+脱敏）


@dataclass
class OrchestrationRequest:
    """编排请求"""
    request_id: str = ""
    name: str = ""
    pipeline_type: PipelineType = PipelineType.FULL_ETL
    # 数据源
    source_database: str = ""
    source_table: str = ""
    source_type: str = "mysql"
    source_connection: Dict[str, Any] = field(default_factory=dict)
    # 目标
    target_database: str = ""
    target_table: str = ""
    target_connection: Dict[str, Any] = field(default_factory=dict)
    # AI 选项
    enable_ai_cleaning: bool = True
    enable_ai_masking: bool = True
    enable_ai_imputation: bool = True
    # 过滤
    column_filter: List[str] = field(default_factory=list)  # 空表示全部列
    # 执行选项
    auto_execute: bool = False       # 生成后自动执行
    dry_run: bool = True             # 试运行（不实际执行）
    async_execute: bool = False      # 异步执行（后台轮询）
    # 回调选项
    auto_catalog: bool = True        # ETL 完成后自动编目
    export_to_minio: bool = False    # ETL 完成后上传到 MinIO
    minio_bucket: str = ""           # MinIO bucket 名称
    minio_path: str = ""             # MinIO 路径前缀
    notify_on_complete: bool = False # 完成后发送通知
    notify_channels: List[str] = field(default_factory=list)  # 通知渠道
    # 创建者
    created_by: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "name": self.name,
            "pipeline_type": self.pipeline_type.value,
            "source_database": self.source_database,
            "source_table": self.source_table,
            "target_database": self.target_database,
            "target_table": self.target_table,
            "enable_ai_cleaning": self.enable_ai_cleaning,
            "enable_ai_masking": self.enable_ai_masking,
            "enable_ai_imputation": self.enable_ai_imputation,
            "auto_execute": self.auto_execute,
            "async_execute": self.async_execute,
            "dry_run": self.dry_run,
            "auto_catalog": self.auto_catalog,
            "export_to_minio": self.export_to_minio,
            "notify_on_complete": self.notify_on_complete,
            "created_by": self.created_by,
        }


@dataclass
class OrchestrationResult:
    """编排结果"""
    request_id: str = ""
    status: OrchestrationStatus = OrchestrationStatus.PENDING
    # 分析结果
    columns_analyzed: int = 0
    cleaning_rules_generated: int = 0
    masking_rules_generated: int = 0
    imputation_rules_generated: int = 0
    # 生成结果
    transformation_xml: str = ""
    transformation_file: str = ""
    job_xml: str = ""
    # 执行结果
    execution_success: Optional[bool] = None
    rows_processed: int = 0
    execution_duration_seconds: int = 0
    # AI 推荐详情
    ai_recommendations: List[Dict[str, Any]] = field(default_factory=list)
    masking_config: Dict[str, Any] = field(default_factory=dict)
    # 时间
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: str = ""

    @property
    def duration_seconds(self) -> int:
        if not self.started_at:
            return 0
        end = self.completed_at or datetime.now()
        return int((end - self.started_at).total_seconds())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "status": self.status.value,
            "columns_analyzed": self.columns_analyzed,
            "cleaning_rules_generated": self.cleaning_rules_generated,
            "masking_rules_generated": self.masking_rules_generated,
            "imputation_rules_generated": self.imputation_rules_generated,
            "has_transformation": bool(self.transformation_xml),
            "transformation_file": self.transformation_file,
            "has_job": bool(self.job_xml),
            "execution_success": self.execution_success,
            "rows_processed": self.rows_processed,
            "execution_duration_seconds": self.execution_duration_seconds,
            "ai_recommendations_count": len(self.ai_recommendations),
            "masking_columns": list(self.masking_config.keys()),
            "duration_seconds": self.duration_seconds,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message,
        }


@dataclass
class DataQualityReport:
    """数据质量报告"""
    request_id: str = ""
    # 基本信息
    source_table: str = ""
    target_table: str = ""
    generated_at: Optional[datetime] = None
    # 行级统计
    rows_read: int = 0
    rows_written: int = 0
    rows_rejected: int = 0
    rows_error: int = 0
    # 质量指标
    error_rate: float = 0.0
    rejection_rate: float = 0.0
    success_rate: float = 1.0
    # 执行信息
    execution_duration_seconds: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    # 步骤详情
    step_details: List[Dict[str, Any]] = field(default_factory=list)
    # 质量问题
    quality_issues: List[Dict[str, Any]] = field(default_factory=list)
    # 建议措施
    recommendations: List[str] = field(default_factory=list)
    # MinIO 导出信息
    minio_path: str = ""
    minio_bucket: str = ""

    def calculate_metrics(self) -> None:
        """计算质量指标"""
        if self.rows_read > 0:
            self.error_rate = self.rows_error / self.rows_read
            self.rejection_rate = self.rows_rejected / self.rows_read
            self.success_rate = self.rows_written / self.rows_read

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "source_table": self.source_table,
            "target_table": self.target_table,
            "generated_at": self.generated_at.isoformat() if self.generated_at else None,
            "rows_read": self.rows_read,
            "rows_written": self.rows_written,
            "rows_rejected": self.rows_rejected,
            "rows_error": self.rows_error,
            "error_rate": f"{self.error_rate:.2%}",
            "rejection_rate": f"{self.rejection_rate:.2%}",
            "success_rate": f"{self.success_rate:.2%}",
            "execution_duration_seconds": self.execution_duration_seconds,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "step_count": len(self.step_details),
            "quality_issues_count": len(self.quality_issues),
            "quality_issues": self.quality_issues,
            "recommendations": self.recommendations,
            "minio_path": self.minio_path,
            "minio_bucket": self.minio_bucket,
        }

    def to_json(self) -> str:
        """导出为 JSON"""
        import json
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


class KettleOrchestrationService:
    """
    Kettle 自动化编排服务

    将元数据分析、AI 规则推荐、Kettle 配置生成和执行
    整合为一站式自动化流水线。

    流程：
    1. 分析源表元数据（列信息、数据类型、采样）
    2. 调用 AI 清洗建议器 获取清洗推荐
    3. 调用 AI 敏感扫描 获取脱敏规则
    4. 调用 KettleConfigGenerator 生成基础转换
    5. 调用 KettleAIIntegrator 注入 AI 步骤
    6. （可选）调用 KettleBridge 执行转换
    7. 记录结果并返回
    """

    def __init__(self):
        self._tasks: Dict[str, OrchestrationResult] = {}
        self._quality_reports: Dict[str, DataQualityReport] = {}
        self._lock = threading.Lock()

    def orchestrate(
        self,
        req: OrchestrationRequest,
        db_session=None,
    ) -> OrchestrationResult:
        """
        执行完整编排流程

        Args:
            req: 编排请求
            db_session: 数据库会话

        Returns:
            OrchestrationResult 编排结果
        """
        if not req.request_id:
            req.request_id = f"orch_{uuid.uuid4().hex[:12]}"

        result = OrchestrationResult(
            request_id=req.request_id,
            status=OrchestrationStatus.ANALYZING,
            started_at=datetime.now(),
        )

        with self._lock:
            self._tasks[req.request_id] = result

        try:
            # 阶段 1: 分析源表元数据
            result.status = OrchestrationStatus.ANALYZING
            columns_info = self._analyze_source_metadata(req, db_session)
            result.columns_analyzed = len(columns_info)
            logger.info(f"编排[{req.request_id}]: 分析 {len(columns_info)} 个列")

            # 阶段 2: AI 推荐
            result.status = OrchestrationStatus.RECOMMENDING
            cleaning_rules = []
            masking_rules = {}
            imputation_rules = []

            if req.enable_ai_cleaning:
                cleaning_rules = self._get_ai_cleaning_rules(columns_info, db_session)
                result.cleaning_rules_generated = len(cleaning_rules)

            if req.enable_ai_masking:
                masking_rules = self._get_ai_masking_rules(columns_info, db_session)
                result.masking_rules_generated = len(masking_rules)
                result.masking_config = masking_rules

            if req.enable_ai_imputation:
                imputation_rules = self._get_ai_imputation_rules(columns_info, req, db_session)
                result.imputation_rules_generated = len(imputation_rules)

            result.ai_recommendations = cleaning_rules + imputation_rules
            logger.info(
                f"编排[{req.request_id}]: AI推荐 "
                f"清洗={len(cleaning_rules)} 脱敏={len(masking_rules)} 填充={len(imputation_rules)}"
            )

            # 阶段 3: 生成 Kettle 转换
            result.status = OrchestrationStatus.GENERATING
            transformation_xml = self._generate_kettle_transformation(
                req, columns_info, cleaning_rules, masking_rules, imputation_rules
            )
            result.transformation_xml = transformation_xml

            # 保存文件
            if transformation_xml:
                file_path = self._save_transformation(req, transformation_xml)
                result.transformation_file = file_path

            # 生成 Job（包裹 Transformation）
            if transformation_xml and not req.dry_run:
                job_xml = self._generate_kettle_job(req, result.transformation_file)
                result.job_xml = job_xml

            logger.info(f"编排[{req.request_id}]: Kettle 转换已生成")

            # 阶段 4: 执行（可选）
            if req.auto_execute and not req.dry_run and result.transformation_file:
                result.status = OrchestrationStatus.EXECUTING
                exec_result = self._execute_transformation(result.transformation_file)
                result.execution_success = exec_result.get("success", False)
                result.rows_processed = exec_result.get("rows_written", 0)
                result.execution_duration_seconds = exec_result.get("duration_seconds", 0)

            result.status = OrchestrationStatus.COMPLETED
            result.completed_at = datetime.now()

            logger.info(
                f"编排[{req.request_id}]: 完成 "
                f"耗时={result.duration_seconds}s "
                f"规则={result.cleaning_rules_generated + result.masking_rules_generated + result.imputation_rules_generated}"
            )

        except Exception as e:
            logger.error(f"编排[{req.request_id}] 失败: {e}", exc_info=True)
            result.status = OrchestrationStatus.FAILED
            result.error_message = str(e)
            result.completed_at = datetime.now()

        return result

    def get_task(self, request_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        result = self._tasks.get(request_id)
        if result:
            return result.to_dict()
        return None

    def list_tasks(self, limit: int = 20) -> List[Dict[str, Any]]:
        """列出最近的任务"""
        tasks = sorted(
            self._tasks.values(),
            key=lambda t: t.started_at or datetime.min,
            reverse=True,
        )
        return [t.to_dict() for t in tasks[:limit]]

    def get_transformation_xml(self, request_id: str) -> Optional[str]:
        """获取生成的 Kettle 转换 XML"""
        result = self._tasks.get(request_id)
        if result:
            return result.transformation_xml
        return None

    def get_quality_report(self, request_id: str) -> Optional[Dict[str, Any]]:
        """获取数据质量报告"""
        report = self._quality_reports.get(request_id)
        if report:
            return report.to_dict()
        return None

    def list_quality_reports(self, limit: int = 20) -> List[Dict[str, Any]]:
        """列出最近的质量报告"""
        reports = sorted(
            self._quality_reports.values(),
            key=lambda r: r.generated_at or datetime.min,
            reverse=True,
        )
        return [r.to_dict() for r in reports[:limit]]

    def save_quality_report(self, report: DataQualityReport) -> None:
        """保存质量报告"""
        with self._lock:
            self._quality_reports[report.request_id] = report

    # ===== 内部方法 =====

    def _analyze_source_metadata(
        self,
        req: OrchestrationRequest,
        db_session=None,
    ) -> List[Dict[str, Any]]:
        """分析源表元数据，获取列信息"""
        columns_info = []

        if db_session is None:
            return columns_info

        try:
            from models.metadata import MetadataDatabase, MetadataTable, MetadataColumn

            # 查找源表元数据
            db = db_session.query(MetadataDatabase).filter(
                MetadataDatabase.database_name == req.source_database
            ).first()

            if not db:
                logger.warning(f"数据库 {req.source_database} 元数据不存在")
                return columns_info

            table = db_session.query(MetadataTable).filter(
                MetadataTable.database_id == db.id,
                MetadataTable.table_name == req.source_table,
            ).first()

            if not table:
                logger.warning(f"表 {req.source_table} 元数据不存在")
                return columns_info

            cols = db_session.query(MetadataColumn).filter(
                MetadataColumn.table_id == table.id
            ).all()

            for col in cols:
                # 列过滤
                if req.column_filter and col.column_name not in req.column_filter:
                    continue

                columns_info.append({
                    "column_name": col.column_name,
                    "column_type": col.column_type or "VARCHAR",
                    "is_nullable": col.is_nullable if hasattr(col, "is_nullable") else True,
                    "sensitivity_type": getattr(col, "sensitivity_type", None),
                    "sensitivity_level": getattr(col, "sensitivity_level", None),
                    "null_count": getattr(col, "null_count", 0),
                    "total_count": getattr(col, "total_count", 0),
                    "column_id": col.id,
                })

        except Exception as e:
            logger.error(f"元数据分析失败: {e}")

        return columns_info

    def _get_ai_cleaning_rules(
        self,
        columns_info: List[Dict[str, Any]],
        db_session=None,
    ) -> List[Dict[str, Any]]:
        """获取 AI 清洗推荐"""
        rules = []
        try:
            from src.ai_cleaning_advisor import get_ai_cleaning_advisor

            advisor = get_ai_cleaning_advisor()

            for col in columns_info:
                col_name = col["column_name"]
                null_count = col.get("null_count", 0)
                total_count = col.get("total_count", 0)

                # 空值处理推荐
                if null_count > 0 and total_count > 0:
                    null_rate = null_count / total_count
                    if null_rate > 0.01:
                        rules.append({
                            "column_name": col_name,
                            "cleaning_type": "NULL_HANDLING",
                            "description": f"空值率 {null_rate:.1%}，建议填充默认值",
                            "kettle_config": {
                                "replace_value": self._suggest_default_value(col),
                            },
                            "priority": "high" if null_rate > 0.1 else "medium",
                        })

                # 字符串清洗推荐
                col_type = col.get("column_type", "").upper()
                if col_type in ("VARCHAR", "TEXT", "CHAR", "STRING"):
                    rules.append({
                        "column_name": col_name,
                        "cleaning_type": "TRIM_WHITESPACE",
                        "description": f"字符串列 {col_name} 建议去除首尾空格",
                        "kettle_config": {
                            "operations": ["trim"],
                        },
                        "priority": "low",
                    })

        except Exception as e:
            logger.warning(f"AI 清洗推荐失败: {e}")

        return rules

    def _get_ai_masking_rules(
        self,
        columns_info: List[Dict[str, Any]],
        db_session=None,
    ) -> Dict[str, Dict[str, Any]]:
        """获取 AI 脱敏规则"""
        masking_rules = {}
        try:
            from src.data_masking import get_masking_service

            masking_service = get_masking_service()

            for col in columns_info:
                sensitivity_type = col.get("sensitivity_type")
                sensitivity_level = col.get("sensitivity_level")

                if sensitivity_type and sensitivity_type != "none":
                    config = masking_service.create_masking_config([{
                        "name": col["column_name"],
                        "sensitivity_type": sensitivity_type,
                        "sensitivity_level": sensitivity_level,
                    }])

                    col_config = config.get(col["column_name"], {})
                    if col_config and not col_config.get("no_masking"):
                        masking_rules[col["column_name"]] = col_config

        except Exception as e:
            logger.warning(f"AI 脱敏规则获取失败: {e}")

        return masking_rules

    def _get_ai_imputation_rules(
        self,
        columns_info: List[Dict[str, Any]],
        req: OrchestrationRequest,
        db_session=None,
    ) -> List[Dict[str, Any]]:
        """获取 AI 填充规则"""
        rules = []
        try:
            from src.ai_imputation import get_imputation_service

            service = get_imputation_service()

            # 找出有空值的数值列
            numeric_types = {"INT", "INTEGER", "BIGINT", "FLOAT", "DOUBLE", "DECIMAL", "NUMERIC"}
            for col in columns_info:
                col_type = col.get("column_type", "").upper()
                null_count = col.get("null_count", 0)

                if null_count > 0 and col_type in numeric_types:
                    rules.append({
                        "column_name": col["column_name"],
                        "cleaning_type": "IMPUTATION",
                        "description": f"数值列 {col['column_name']} 有 {null_count} 个空值，建议统计填充",
                        "strategy": "mean",
                        "kettle_config": {
                            "replace_value": "0",  # 默认值，实际由 imputation service 计算
                        },
                        "priority": "medium",
                    })

        except Exception as e:
            logger.warning(f"AI 填充规则获取失败: {e}")

        return rules

    def _generate_kettle_transformation(
        self,
        req: OrchestrationRequest,
        columns_info: List[Dict[str, Any]],
        cleaning_rules: List[Dict[str, Any]],
        masking_rules: Dict[str, Dict[str, Any]],
        imputation_rules: List[Dict[str, Any]],
    ) -> str:
        """生成完整的 Kettle 转换 XML"""
        try:
            from src.kettle_generator import (
                KettleConfigGenerator,
                TransformationConfig,
                SourceConfig,
                TargetConfig,
                ColumnMapping,
                SourceType,
            )

            generator = KettleConfigGenerator()

            # 构建列映射
            mappings = []
            for col in columns_info:
                mappings.append(ColumnMapping(
                    source_column=col["column_name"],
                    target_column=col["column_name"],
                    source_type=self._to_kettle_type(col.get("column_type", "VARCHAR")),
                    target_type=self._to_kettle_type(col.get("column_type", "VARCHAR")),
                ))

            # 构建源配置
            source_conn = req.source_connection or {}
            source = SourceConfig(
                source_type=SourceType(req.source_type),
                connection_name="source_connection",
                host=source_conn.get("host", "localhost"),
                port=source_conn.get("port", 3306),
                database=req.source_database,
                username=source_conn.get("username", ""),
                password=source_conn.get("password", ""),
                table=req.source_table,
            )

            # 构建目标配置
            target_conn = req.target_connection or {}
            target = TargetConfig(
                target_type=SourceType(req.source_type),
                connection_name="target_connection",
                host=target_conn.get("host", source_conn.get("host", "localhost")),
                port=target_conn.get("port", source_conn.get("port", 3306)),
                database=req.target_database or req.source_database,
                username=target_conn.get("username", source_conn.get("username", "")),
                password=target_conn.get("password", source_conn.get("password", "")),
                table=req.target_table or f"{req.source_table}_cleaned",
            )

            # 构建转换配置
            config = TransformationConfig(
                name=req.name or f"auto_etl_{req.source_table}",
                description=f"自动编排转换: {req.source_database}.{req.source_table}",
                source=source,
                target=target,
                column_mappings=mappings,
            )

            # 合并清洗+填充规则
            all_cleaning_rules = cleaning_rules + imputation_rules

            # 使用增强生成器
            xml_str = generator.generate_transformation_with_ai_rules(
                config=config,
                cleaning_rules=all_cleaning_rules if all_cleaning_rules else None,
                masking_rules=masking_rules if masking_rules else None,
            )

            # 如果还有 AI 步骤需要注入（如 StreamLookup 等）
            if imputation_rules:
                try:
                    from src.kettle_ai_integrator import get_kettle_ai_integrator

                    integrator = get_kettle_ai_integrator()
                    for rule in imputation_rules:
                        if rule.get("strategy") in ("forward_fill", "backward_fill", "lookup"):
                            step_xml = integrator.imputation_rule_to_kettle_step(
                                column_name=rule["column_name"],
                                strategy=rule["strategy"],
                                config=rule.get("kettle_config", {}),
                            )
                            if step_xml:
                                import xml.etree.ElementTree as ET
                                xml_str = integrator.inject_ai_steps_to_transformation(
                                    xml_str, [step_xml]
                                )
                except Exception as e:
                    logger.warning(f"AI 步骤注入失败: {e}")

            return xml_str

        except Exception as e:
            logger.error(f"Kettle 转换生成失败: {e}", exc_info=True)
            return ""

    def _generate_kettle_job(self, req: OrchestrationRequest, transformation_file: str) -> str:
        """生成 Kettle Job XML"""
        try:
            from src.kettle_generator import KettleConfigGenerator

            generator = KettleConfigGenerator()
            job_xml = generator.generate_job(
                job_name=f"job_{req.name or req.source_table}",
                transformations=[transformation_file],
                description=f"自动编排作业: {req.source_database}.{req.source_table}",
            )
            return job_xml

        except Exception as e:
            logger.error(f"Kettle Job 生成失败: {e}")
            return ""

    def _execute_transformation(self, file_path: str) -> Dict[str, Any]:
        """执行 Kettle 转换"""
        try:
            from src.kettle_bridge import get_kettle_bridge

            bridge = get_kettle_bridge()
            result = bridge.execute_transformation(file_path=file_path)
            return {
                "success": result.success,
                "rows_read": result.rows_read,
                "rows_written": result.rows_written,
                "rows_error": result.rows_error,
                "duration_seconds": result.duration_seconds,
                "exit_code": result.exit_code,
            }

        except Exception as e:
            logger.error(f"Kettle 转换执行失败: {e}")
            return {"success": False, "error": str(e)}

    def _save_transformation(self, req: OrchestrationRequest, xml_str: str) -> str:
        """保存转换 XML 到文件"""
        os.makedirs(KETTLE_OUTPUT_DIR, exist_ok=True)
        file_name = f"{req.request_id}_{req.source_table}.ktr"
        file_path = os.path.join(KETTLE_OUTPUT_DIR, file_name)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(xml_str)

        logger.info(f"转换文件已保存: {file_path}")
        return file_path

    def _suggest_default_value(self, col: Dict[str, Any]) -> str:
        """根据列类型推荐默认值"""
        col_type = col.get("column_type", "").upper()
        if col_type in ("INT", "INTEGER", "BIGINT", "SMALLINT", "TINYINT"):
            return "0"
        elif col_type in ("FLOAT", "DOUBLE", "DECIMAL", "NUMERIC"):
            return "0.0"
        elif col_type in ("DATE", "DATETIME", "TIMESTAMP"):
            return ""
        elif col_type in ("BOOLEAN", "BOOL"):
            return "false"
        return ""

    def _to_kettle_type(self, db_type: str) -> str:
        """数据库类型转 Kettle 类型"""
        type_map = {
            "VARCHAR": "String",
            "CHAR": "String",
            "TEXT": "String",
            "LONGTEXT": "String",
            "INT": "Integer",
            "INTEGER": "Integer",
            "BIGINT": "Integer",
            "SMALLINT": "Integer",
            "TINYINT": "Integer",
            "FLOAT": "Number",
            "DOUBLE": "Number",
            "DECIMAL": "BigNumber",
            "NUMERIC": "BigNumber",
            "DATE": "Date",
            "DATETIME": "Date",
            "TIMESTAMP": "Date",
            "BOOLEAN": "Boolean",
            "BOOL": "Boolean",
            "BLOB": "Binary",
            "BINARY": "Binary",
        }
        return type_map.get(db_type.upper(), "String")

    # ===== 数据质量报告 =====

    def generate_quality_report(
        self,
        req: OrchestrationRequest,
        exec_result: Dict[str, Any],
    ) -> DataQualityReport:
        """
        生成数据质量报告

        Args:
            req: 编排请求
            exec_result: 执行结果

        Returns:
            DataQualityReport
        """
        report = DataQualityReport(
            request_id=req.request_id,
            source_table=f"{req.source_database}.{req.source_table}",
            target_table=f"{req.target_database or req.source_database}.{req.target_table or req.source_table + '_cleaned'}",
            generated_at=datetime.now(),
            rows_read=exec_result.get("rows_read", 0),
            rows_written=exec_result.get("rows_written", 0),
            rows_rejected=exec_result.get("rows_rejected", 0),
            rows_error=exec_result.get("rows_error", 0),
            execution_duration_seconds=exec_result.get("duration_seconds", 0),
            start_time=datetime.now(),  # 实际应从执行上下文获取
            end_time=datetime.now(),
        )

        # 计算质量指标
        report.calculate_metrics()

        # 分析质量问题
        if report.error_rate > 0.05:  # 错误率 > 5%
            report.quality_issues.append({
                "severity": "high",
                "type": "high_error_rate",
                "message": f"错误率过高: {report.error_rate:.2%}",
                "threshold": "5%",
            })
            report.recommendations.append("检查源数据质量和转换规则配置")

        if report.rejection_rate > 0.1:  # 拒绝率 > 10%
            report.quality_issues.append({
                "severity": "medium",
                "type": "high_rejection_rate",
                "message": f"拒绝率过高: {report.rejection_rate:.2%}",
                "threshold": "10%",
            })
            report.recommendations.append("检查过滤条件是否过于严格")

        if report.success_rate < 0.9:  # 成功率 < 90%
            report.quality_issues.append({
                "severity": "low",
                "type": "low_success_rate",
                "message": f"成功率较低: {report.success_rate:.2%}",
                "threshold": "90%",
            })
            report.recommendations.append("建议审查数据转换逻辑")

        return report

    def export_quality_report_to_minio(
        self,
        report: DataQualityReport,
        bucket: str,
        path_prefix: str = "",
    ) -> bool:
        """
        导出质量报告到 MinIO

        Args:
            report: 质量报告
            bucket: MinIO bucket
            path_prefix: 路径前缀

        Returns:
            是否导出成功
        """
        try:
            from minio import Minio
            from minio.error import S3Error

            # MinIO 配置
            minio_endpoint = os.getenv("MINIO_ENDPOINT", "localhost:9000")
            minio_access_key = os.getenv("MINIO_ACCESS_KEY", "")
            minio_secret_key = os.getenv("MINIO_SECRET_KEY", "")
            minio_secure = os.getenv("MINIO_SECURE", "false").lower() == "true"

            client = Minio(
                minio_endpoint,
                access_key=minio_access_key,
                secret_key=minio_secret_key,
                secure=minio_secure,
            )

            # 确保 bucket 存在
            try:
                if not client.bucket_exists(bucket):
                    client.make_bucket(bucket)
                    logger.info(f"创建 MinIO bucket: {bucket}")
            except S3Error:
                pass  # bucket 可能已存在

            # 生成文件路径
            timestamp = datetime.now().strftime("%Y%m%d/%Y%m%d_%H%M%S")
            object_name = f"{path_prefix}/{timestamp}/quality_report_{report.request_id}.json".lstrip("/")

            # 上传报告
            from io import BytesIO
            data = BytesIO(report.to_json().encode("utf-8"))
            client.put_object(
                bucket,
                object_name,
                data,
                length=data.getbuffer().nbytes,
                content_type="application/json",
            )

            report.minio_bucket = bucket
            report.minio_path = f"minio://{bucket}/{object_name}"
            logger.info(f"质量报告已导出到 MinIO: {report.minio_path}")
            return True

        except ImportError:
            logger.warning("MinIO 客户端未安装，无法导出报告")
            return False
        except Exception as e:
            logger.error(f"导出质量报告到 MinIO 失败: {e}")
            return False

    # ===== Carte 远程执行 =====

    def execute_via_carte(
        self,
        trans_xml: str,
        trans_name: str,
        poll_timeout: int = 3600,
    ) -> Dict[str, Any]:
        """
        通过 Carte 服务器执行转换

        Args:
            trans_xml: 转换 XML 内容
            trans_name: 转换名称
            poll_timeout: 轮询超时时间（秒）

        Returns:
            执行结果
        """
        try:
            from integrations.kettle.kettle_bridge import KettleBridge

            bridge = KettleBridge()

            # 健康检查
            if not bridge.health_check():
                return {
                    "success": False,
                    "error": "Carte 服务器不可用",
                    "error_type": "carte_unavailable",
                }

            # 提交转换
            job_id = bridge.submit_transformation(trans_xml, trans_name)

            # 轮询状态
            import time
            start_time = time.time()
            last_result = None

            while time.time() - start_time < poll_timeout:
                result = bridge.get_transformation_status(job_id)

                if result.is_finished:
                    return {
                        "success": result.is_success,
                        "job_id": job_id,
                        "rows_read": result.rows_read,
                        "rows_written": result.rows_written,
                        "rows_rejected": result.rows_rejected,
                        "rows_error": result.errors,
                        "duration_seconds": int(time.time() - start_time),
                        "log_text": result.log_text,
                        "step_statuses": result.step_statuses,
                    }

                last_result = result
                time.sleep(KETTLE_POLL_INTERVAL)

            # 超时
            bridge.stop_transformation(job_id)
            return {
                "success": False,
                "error": f"执行超时（{poll_timeout}秒）",
                "error_type": "timeout",
                "job_id": job_id,
            }

        except Exception as e:
            logger.error(f"Carte 执行失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": "execution_error",
            }


# 全局实例
_orchestration_service: Optional[KettleOrchestrationService] = None


def get_kettle_orchestration_service() -> KettleOrchestrationService:
    """获取 Kettle 编排服务单例"""
    global _orchestration_service
    if _orchestration_service is None:
        _orchestration_service = KettleOrchestrationService()
    return _orchestration_service
