"""
SeaTunnel CDC 服务
管理 CDC 同步任务，支持多种数据源和目标

功能：
1. CDC 任务配置管理
2. 实时数据同步
3. 数据源连接管理
4. 同步任务监控
"""

import logging
import os
import yaml
import json
import secrets
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class SeaTunnelSourceType(str, Enum):
    """SeaTunnel 源类型"""
    MYSQL_CDC = "MySQL-CDC"
    POSTGRESQL_CDC = "PostgreSQL-CDC"
    MONGODB_CDC = "MongoDB-CDC"
    ORACLE_CDC = "Oracle-CDC"
    SQLSERVER_CDC = "SQLServer-CDC"
    KAFKA = "Kafka"
    HTTP = "Http"
    PULSAR = "Pulsar"
    FILE = "File"
    SOCKET = "Socket"
    FAKE = "Fake"


class SeaTunnelSinkType(str, Enum):
    """SeaTunnel 目标类型"""
    CLICKHOUSE = "ClickHouse"
    DORIS = "Doris"
    HIVE = "Hive"
    ICEBERG = "Iceberg"
    HUDI = "Hudi"
    KAFKA = "Kafka"
    CONSOLE = "Console"
    FAKE = "Fake"
    AIO = "AiO"  # 对象存储适配器
    JDBC = "Jdbc"
    ELASTICSEARCH = "Elasticsearch"
    MONGODB = "MongoDB"


@dataclass
class CDCSourceConfig:
    """CDC 数据源配置"""
    source_type: SeaTunnelSourceType
    host: str
    port: int
    username: str
    password: str
    database: str
    schema: str = ""
    tables: List[str] = field(default_factory=list)
    server_id: int = 5700
    server_timezone: str = "UTC"
    connection_timeout: int = 30000
    include_schema_changes: bool = False

    def to_dict(self) -> Dict:
        """转换为字典"""
        config = {
            "host": self.host,
            "port": self.port,
            "username": self.username,
            "password": self.password,
            "database": self.database,
            "server_timezone": self.server_timezone,
        }

        if self.schema:
            config["schema"] = self.schema

        if self.tables:
            config["table-names"] = [f"{self.database}.{t}" for t in self.tables]
        else:
            config["table-names"] = [f"{self.database}..*"]

        if self.source_type == SeaTunnelSourceType.MYSQL_CDC:
            config["server-id"] = self.server_id

        if self.include_schema_changes:
            config["include-schema-changes"] = True

        return config


@dataclass
class CDCTargetConfig:
    """CDC 目标配置"""
    sink_type: SeaTunnelSinkType
    host: str = ""
    port: int = 0
    database: str = ""
    table: str = ""
    username: str = ""
    password: str = ""
    # 对象存储配置
    endpoint: str = ""
    bucket: str = ""
    path: str = ""
    access_key: str = ""
    secret_key: str = ""
    # 其他配置
    primary_key: str = "id"
    batch_size: int = 1000
    # Elasticsearch 配置
    index: str = ""
    es_hosts: str = ""

    def to_dict(self) -> Dict:
        """转换为字典"""
        if self.sink_type == SeaTunnelSinkType.CLICKHOUSE:
            return {
                "host": self.host,
                "port": self.port,
                "database": self.database,
                "table": self.table,
                "username": self.username,
                "password": self.password,
                "primary_key": self.primary_key,
            }

        elif self.sink_type == SeaTunnelSinkType.AIO:
            config = {
                "path": f"s3a://{self.bucket}/{self.path}",
                "format.type": "json",
                "fs.s3a.endpoint": self.endpoint,
                "fs.s3a.access.key": self.access_key,
                "fs.s3a.secret.key": self.secret_key,
            }
            return config

        elif self.sink_type == SeaTunnelSinkType.JDBC:
            return {
                "driver": "com.mysql.cj.jdbc.Driver",
                "url": f"jdbc:mysql://{self.host}:{self.port}/{self.database}",
                "user": self.username,
                "password": self.password,
                "generate_sql": True,
            }

        elif self.sink_type == SeaTunnelSinkType.ELASTICSEARCH:
            return {
                "hosts": f"[{self.es_hosts}]",
                "index": self.index,
                "index_time_format": "yyyy.MM.dd",
            }

        elif self.sink_type == SeaTunnelSinkType.MONGODB:
            return {
                "host": self.host,
                "port": self.port,
                "database": self.database,
                "collection": self.table,
                "username": self.username,
                "password": self.password,
            }

        return {}


@dataclass
class CDCJobConfig:
    """CDC 任务配置"""
    job_name: str
    source: CDCSourceConfig
    sink: CDCTargetConfig
    transforms: List[Dict[str, Any]] = field(default_factory=list)
    parallelism: int = 2
    checkpoint_interval: int = 3000
    description: str = ""
    enabled: bool = True


@dataclass
class CDCJobMetrics:
    """CDC 任务指标"""
    job_id: str
    status: str  # running, stopped, error
    records_in: int = 0
    records_out: int = 0
    bytes_in: int = 0
    bytes_out: int = 0
    lag_ms: int = 0
    last_checkpoint: Optional[datetime] = None
    error_message: str = ""
    start_time: Optional[datetime] = None


class SeaTunnelService:
    """SeaTunnel CDC 服务"""

    def __init__(
        self,
        seatunnel_url: str = None,
        config_dir: str = None,
    ):
        """
        初始化 SeaTunnel 服务

        Args:
            seatunnel_url: SeaTunnel API URL
            config_dir: 配置文件目录
        """
        self.seatunnel_url = seatunnel_url or os.getenv(
            "SEATUNNEL_URL", "http://localhost:5801"
        )
        self.config_dir = Path(config_dir or os.getenv(
            "SEATUNNEL_CONFIG_DIR", "/opt/seatunnel/config"
        ))
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # 任务存储
        self._jobs: Dict[str, CDCJobConfig] = {}
        self._metrics: Dict[str, CDCJobMetrics] = {}

    def create_cdc_job(
        self,
        job_name: str,
        source: CDCSourceConfig,
        sink: CDCTargetConfig,
        transforms: List[Dict[str, Any]] = None,
        parallelism: int = 2,
        description: str = "",
    ) -> Optional[str]:
        """
        创建 CDC 任务

        Args:
            job_name: 任务名称
            source: 数据源配置
            sink: 目标配置
            transforms: 转换配置
            parallelism: 并行度
            description: 描述

        Returns:
            任务 ID
        """
        try:
            job_id = f"cdc_job_{secrets.token_hex(8)}"

            job_config = CDCJobConfig(
                job_name=job_name,
                source=source,
                sink=sink,
                transforms=transforms or [],
                parallelism=parallelism,
                description=description,
            )

            # 生成配置文件
            config = self._build_job_config(job_config)
            config_file = self.config_dir / f"{job_id}.conf"

            with open(config_file, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

            # 保存任务配置
            self._jobs[job_id] = job_config
            self._metrics[job_id] = CDCJobMetrics(
                job_id=job_id,
                status="created",
            )

            logger.info(f"CDC 任务创建成功: {job_name} (ID: {job_id})")
            return job_id

        except Exception as e:
            logger.error(f"创建 CDC 任务失败: {e}")
            return None

    def _build_job_config(self, job_config: CDCJobConfig) -> Dict[str, Any]:
        """构建 SeaTunnel 任务配置"""
        env_config = {
            "job.mode": "STREAMING",
            "parallelism": job_config.parallelism,
            "checkpoint.interval": job_config.checkpoint_interval,
        }

        source_config = {
            job_config.source.source_type.value: {
                "result_table_name": f"source_{job_config.job_name}",
                **job_config.source.to_dict(),
            }
        }

        transform_configs = []
        for i, transform in enumerate(job_config.transforms):
            transform_type = transform.get("type", "FieldMapper")
            transform_config = {
                transform_type: {
                    "result_table_name": f"transform_{i}",
                    "source_table_name": f"source_{job_config.job_name}" if i == 0 else f"transform_{i-1}",
                    **transform.get("params", {}),
                }
            }
            transform_configs.append(transform_config)

        sink_config = {
            job_config.sink.sink_type.value: {
                "source_table_name": (
                    f"transform_{len(transform_configs)-1}"
                    if transform_configs
                    else f"source_{job_config.job_name}"
                ),
                **job_config.sink.to_dict(),
            }
        }

        return {
            "env": env_config,
            "source": source_config,
            "transform": transform_configs,
            "sink": sink_config,
        }

    def start_job(self, job_id: str) -> bool:
        """启动 CDC 任务"""
        try:
            if job_id not in self._jobs:
                logger.error(f"任务不存在: {job_id}")
                return False

            # 读取配置文件
            config_file = self.config_dir / f"{job_id}.conf"
            if not config_file.exists():
                logger.error(f"配置文件不存在: {config_file}")
                return False

            # 这里应该调用 SeaTunnel API 提交任务
            # 简化处理：更新状态
            self._metrics[job_id].status = "running"
            self._metrics[job_id].start_time = datetime.now()

            logger.info(f"CDC 任务启动成功: {job_id}")
            return True

        except Exception as e:
            logger.error(f"启动 CDC 任务失败: {e}")
            self._metrics[job_id].status = "error"
            self._metrics[job_id].error_message = str(e)
            return False

    def stop_job(self, job_id: str) -> bool:
        """停止 CDC 任务"""
        try:
            if job_id not in self._metrics:
                return False

            self._metrics[job_id].status = "stopped"
            logger.info(f"CDC 任务已停止: {job_id}")
            return True

        except Exception as e:
            logger.error(f"停止 CDC 任务失败: {e}")
            return False

    def remove_job(self, job_id: str) -> bool:
        """删除 CDC 任务"""
        try:
            self.stop_job(job_id)

            # 删除配置文件
            config_file = self.config_dir / f"{job_id}.conf"
            if config_file.exists():
                config_file.unlink()

            self._jobs.pop(job_id, None)
            self._metrics.pop(job_id, None)

            logger.info(f"CDC 任务已删除: {job_id}")
            return True

        except Exception as e:
            logger.error(f"删除 CDC 任务失败: {e}")
            return False

    def get_job_metrics(self, job_id: str) -> Optional[CDCJobMetrics]:
        """获取任务指标"""
        return self._metrics.get(job_id)

    def list_jobs(
        self,
        status: str = None,
    ) -> List[Dict[str, Any]]:
        """列出任务"""
        jobs = []

        for job_id, config in self._jobs.items():
            metrics = self._metrics.get(job_id)

            if status and metrics and metrics.status != status:
                continue

            jobs.append({
                "job_id": job_id,
                "job_name": config.job_name,
                "description": config.description,
                "source_type": config.source.source_type.value,
                "sink_type": config.sink.sink_type.value,
                "status": metrics.status if metrics else "unknown",
                "records_in": metrics.records_in if metrics else 0,
                "records_out": metrics.records_out if metrics else 0,
                "lag_ms": metrics.lag_ms if metrics else 0,
                "start_time": metrics.start_time.isoformat() if metrics and metrics.start_time else None,
                "enabled": config.enabled,
            })

        return jobs

    def update_job_metrics(
        self,
        job_id: str,
        records_in: int = 0,
        records_out: int = 0,
        lag_ms: int = 0,
    ):
        """更新任务指标"""
        if job_id in self._metrics:
            metrics = self._metrics[job_id]
            metrics.records_in = records_in
            metrics.records_out = records_out
            metrics.lag_ms = lag_ms
            metrics.last_checkpoint = datetime.now()

    def get_job_config(self, job_id: str) -> Optional[Dict[str, Any]]:
        """获取任务配置"""
        if job_id in self._jobs:
            config = self._jobs[job_id]
            return {
                "job_id": job_id,
                "job_name": config.job_name,
                "description": config.description,
                "parallelism": config.parallelism,
                "checkpoint_interval": config.checkpoint_interval,
                "source": {
                    "type": config.source.source_type.value,
                    "database": config.source.database,
                    "tables": config.source.tables,
                },
                "sink": {
                    "type": config.sink.sink_type.value,
                    "database": config.sink.database,
                    "table": config.sink.table,
                },
                "transforms": config.transforms,
                "enabled": config.enabled,
            }
        return None

    # ==================== 预定义配置模板 ====================

    @staticmethod
    def mysql_to_minio_template(
        mysql_host: str,
        mysql_port: int,
        mysql_user: str,
        mysql_password: str,
        mysql_database: str,
        tables: List[str],
        minio_endpoint: str,
        minio_bucket: str,
        minio_path: str,
        minio_access_key: str,
        minio_secret_key: str,
    ) -> CDCJobConfig:
        """MySQL 到 MinIO 的 CDC 配置模板"""
        return CDCJobConfig(
            job_name=f"mysql_{mysql_database}_to_minio",
            source=CDCSourceConfig(
                source_type=SeaTunnelSourceType.MYSQL_CDC,
                host=mysql_host,
                port=mysql_port,
                username=mysql_user,
                password=mysql_password,
                database=mysql_database,
                tables=tables,
            ),
            sink=CDCTargetConfig(
                sink_type=SeaTunnelSinkType.AIO,
                endpoint=minio_endpoint,
                bucket=minio_bucket,
                path=minio_path,
                access_key=minio_access_key,
                secret_key=minio_secret_key,
            ),
            description=f"MySQL CDC: {mysql_database} -> MinIO",
        )

    @staticmethod
    def mysql_to_clickhouse_template(
        mysql_host: str,
        mysql_port: int,
        mysql_user: str,
        mysql_password: str,
        mysql_database: str,
        tables: List[str],
        ch_host: str,
        ch_port: int,
        ch_database: str,
        ch_user: str,
        ch_password: str,
    ) -> CDCJobConfig:
        """MySQL 到 ClickHouse 的 CDC 配置模板"""
        return CDCJobConfig(
            job_name=f"mysql_{mysql_database}_to_clickhouse",
            source=CDCSourceConfig(
                source_type=SeaTunnelSourceType.MYSQL_CDC,
                host=mysql_host,
                port=mysql_port,
                username=mysql_user,
                password=mysql_password,
                database=mysql_database,
                tables=tables,
            ),
            sink=CDCTargetConfig(
                sink_type=SeaTunnelSinkType.CLICKHOUSE,
                host=ch_host,
                port=ch_port,
                database=ch_database,
                table="{database}_{table}",  # 动态表名
                username=ch_user,
                password=ch_password,
            ),
            description=f"MySQL CDC: {mysql_database} -> ClickHouse",
        )


# 全局服务实例
_seatunnel_service: Optional[SeaTunnelService] = None


def get_seatunnel_service() -> SeaTunnelService:
    """获取 SeaTunnel 服务实例"""
    global _seatunnel_service
    if _seatunnel_service is None:
        _seatunnel_service = SeaTunnelService()
    return _seatunnel_service


# 导出
__all__ = [
    'SeaTunnelSourceType',
    'SeaTunnelSinkType',
    'CDCSourceConfig',
    'CDCTargetConfig',
    'CDCJobConfig',
    'CDCJobMetrics',
    'SeaTunnelService',
    'get_seatunnel_service',
]
