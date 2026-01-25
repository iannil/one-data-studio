"""
Cube API 数据模型
P4: 监控、LLM调优、SQL Lab、AI Hub
"""

from .base import Base, SessionLocal, engine, get_db, init_db
from .model import MLModel, ModelVersion, ModelDeployment
from .training_job import TrainingJob, BatchPredictionJob
from .serving import ServingService, ServingMetrics, ServingLog
from .experiment import Experiment, ExperimentMetric, ExperimentArtifact
from .pipeline import Pipeline, PipelineExecution, PipelineTemplate
from .resource import ResourcePool, GPUDevice, ResourceUsage
from .monitoring import MonitoringDashboard, AlertRule, AlertNotification
from .llmtuning import LLMTuningTask
from .sqllab import SqlQuery, SavedQuery, DatabaseConnection
from .aihub import AIHubModel, AIHubCategory

__all__ = [
    'Base',
    'SessionLocal',
    'engine',
    'get_db',
    'init_db',
    # Model management
    'MLModel',
    'ModelVersion',
    'ModelDeployment',
    # Training
    'TrainingJob',
    'BatchPredictionJob',
    # Serving (P2.1)
    'ServingService',
    'ServingMetrics',
    'ServingLog',
    # Experiments (P2.2)
    'Experiment',
    'ExperimentMetric',
    'ExperimentArtifact',
    # Pipelines (P2.3)
    'Pipeline',
    'PipelineExecution',
    'PipelineTemplate',
    # Resources (P2.4)
    'ResourcePool',
    'GPUDevice',
    'ResourceUsage',
    # Monitoring (P4.4)
    'MonitoringDashboard',
    'AlertRule',
    'AlertNotification',
    # LLM Tuning (P4.5)
    'LLMTuningTask',
    # SQL Lab (P4.6)
    'SqlQuery',
    'SavedQuery',
    'DatabaseConnection',
    # AI Hub (P4.7)
    'AIHubModel',
    'AIHubCategory',
]
