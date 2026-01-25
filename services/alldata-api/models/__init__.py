"""
Alldata API 模型
Sprint 4.1: SQLAlchemy 数据模型
"""

from .base import Base, engine, SessionLocal, get_db
from .dataset import Dataset, DatasetColumn, DatasetVersion
from .metadata import MetadataDatabase, MetadataTable, MetadataColumn
from .file_upload import FileUpload
from .etl import ETLTask, ETLTaskLog
from .quality import QualityRule, QualityTask, QualityReport, QualityAlert
from .lineage import LineageNode, LineageEdge, LineageSnapshot
from .metrics import MetricDefinition, MetricValue, MetricCategory

__all__ = [
    # Base
    "Base",
    "engine",
    "SessionLocal",
    "get_db",
    # Dataset models
    "Dataset",
    "DatasetColumn",
    "DatasetVersion",
    # Metadata models
    "MetadataDatabase",
    "MetadataTable",
    "MetadataColumn",
    # File upload model
    "FileUpload",
    # ETL models
    "ETLTask",
    "ETLTaskLog",
    # Quality models
    "QualityRule",
    "QualityTask",
    "QualityReport",
    "QualityAlert",
    # Lineage models
    "LineageNode",
    "LineageEdge",
    "LineageSnapshot",
    # Metrics models
    "MetricDefinition",
    "MetricValue",
    "MetricCategory",
]
