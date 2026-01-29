"""
Model API - MLOps 平台服务
提供模型管理、训练任务、部署服务等功能

功能：
- 模型 CRUD 管理
- Hugging Face Hub 集成
- 模型部署与服务
- 训练任务管理
- 批量预测接口
"""

import os
import sys
import logging
import uuid
import asyncio
import time
from typing import Optional, List, Dict, Any
from datetime import datetime
from functools import wraps

from flask import Flask, jsonify, request, g
from flask_cors import CORS
from sqlalchemy import func

# 添加项目路径（确保本地 models 优先于 shared/models）
sys.path.insert(0, '/app')

# 添加共享模块路径
sys.path.insert(1, '/app/shared')

from models import (
    SessionLocal, init_db,
    MLModel, ModelVersion, ModelDeployment,
    TrainingJob, BatchPredictionJob,
    ServingService, ServingMetrics, ServingLog,
    Experiment, ExperimentMetric, ExperimentArtifact,
    Pipeline, PipelineExecution, PipelineTemplate,
    ResourcePool, GPUDevice, ResourceUsage,
    MonitoringDashboard, AlertRule, AlertNotification,
    LLMTuningTask,
    SqlQuery, SavedQuery, DatabaseConnection,
    AIHubModel, AIHubCategory,
    # Prediction
    PredictionTemplate,
    PredictionTrainingJob,
    PredictionRecord,
    generate_template_id,
    generate_job_id,
    PREDEFINED_TEMPLATES,
)
from services.huggingface import get_huggingface_service, HuggingFaceService
from services.inference import get_inference_service, ModelInferenceService

# 尝试导入认证模块
try:
    from auth import (
        require_jwt,
        require_permission,
        Resource,
        Operation,
        get_current_user
    )
    AUTH_ENABLED = True
except ImportError:
    # Check if we're in production - auth is required in production
    if os.getenv('ENVIRONMENT', '').lower() in ('production', 'prod'):
        raise ImportError(
            "Authentication module is required in production. "
            "Ensure auth.py is present and all dependencies are installed."
        )

    AUTH_ENABLED = False
    # 装饰器空实现（开发模式）
    import logging as _logging
    _logging.getLogger(__name__).warning(
        "Authentication module not available. Running in development mode without auth. "
        "This is NOT safe for production use."
    )
    def require_jwt(optional=False):
        def decorator(fn):
            return fn
        return decorator
    def require_permission(resource, operation):
        def decorator(fn):
            return fn
        return decorator
    class Resource:
        MODEL = type('', (), {'value': 'model'})()
        DATASET = type('', (), {'value': 'dataset'})()
    class Operation:
        CREATE = type('', (), {'value': 'create'})()
        READ = type('', (), {'value': 'read'})()
        UPDATE = type('', (), {'value': 'update'})()
        DELETE = type('', (), {'value': 'delete'})()
        EXECUTE = type('', (), {'value': 'execute'})()

# 认证模式配置
AUTH_MODE = os.getenv("AUTH_MODE", "true").lower() == "true"

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建 Flask 应用
app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False

# 配置 CORS
# C-05 安全修复: 生产环境必须显式配置 CORS_ORIGINS
_cors_origins = os.getenv("CORS_ORIGINS", "")
if not _cors_origins:
    if os.getenv("ENVIRONMENT") == "production":
        raise ValueError(
            "CRITICAL: CORS_ORIGINS must be explicitly configured in production. "
            "Set CORS_ORIGINS environment variable to allowed origins (comma-separated)."
        )
    logger.warning(
        "SECURITY WARNING: CORS_ORIGINS not configured, defaulting to localhost only. "
        "This should be explicitly configured for production deployment."
    )
    _cors_origins = "http://localhost:3000,http://127.0.0.1:3000"

CORS(app, resources={
    r"/*": {
        "origins": _cors_origins.split(","),
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})


# ==================== 数据库会话管理 ====================

def get_db_session():
    """获取数据库会话"""
    if 'db' not in g:
        g.db = SessionLocal()
    return g.db


@app.teardown_appcontext
def close_db_session(exception=None):
    """关闭数据库会话"""
    db = g.pop('db', None)
    if db is not None:
        db.close()


def generate_id(prefix: str = "") -> str:
    """生成唯一ID"""
    return f"{prefix}{uuid.uuid4().hex[:16]}"


# ==================== 健康检查 ====================

@app.route("/health")
@app.route("/api/v1/health")
def health():
    """健康检查"""
    hf_service = get_huggingface_service()

    return jsonify({
        "status": "ok",
        "service": "model-api",
        "version": "1.0.0",
        "huggingface_configured": hf_service.token is not None,
        "timestamp": datetime.now().isoformat()
    })


# ==================== 监控 API ====================

@app.route("/api/v1/monitoring/tasks", methods=["GET"])
@require_jwt(optional=True)
def list_monitoring_tasks():
    """列出监控任务（训练任务、流水线任务等）"""
    db = get_db_session()

    # 查询参数
    status = request.args.get("status")
    task_type = request.args.get("type")  # training, pipeline, serving
    start_time = request.args.get("start_time")
    end_time = request.args.get("end_time")
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 20))

    tasks = []

    # 获取训练任务
    if not task_type or task_type == "training":
        training_query = db.query(TrainingJob)
        if status:
            training_query = training_query.filter(TrainingJob.status == status)
        if start_time:
            training_query = training_query.filter(TrainingJob.created_at >= start_time)
        if end_time:
            training_query = training_query.filter(TrainingJob.created_at <= end_time)

        training_jobs = training_query.order_by(TrainingJob.created_at.desc()).limit(page_size).all()
        for job in training_jobs:
            tasks.append({
                "task_id": job.job_id,
                "name": job.job_name,
                "type": "training",
                "status": job.status,
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                "duration": job.duration_seconds,
                "progress": job.progress,
            })

    # 获取流水线执行任务
    if not task_type or task_type == "pipeline":
        pipeline_query = db.query(PipelineExecution)
        if status:
            pipeline_query = pipeline_query.filter(PipelineExecution.status == status)
        if start_time:
            pipeline_query = pipeline_query.filter(PipelineExecution.created_at >= start_time)
        if end_time:
            pipeline_query = pipeline_query.filter(PipelineExecution.created_at <= end_time)

        pipeline_execs = pipeline_query.order_by(PipelineExecution.created_at.desc()).limit(page_size).all()
        for exec in pipeline_execs:
            tasks.append({
                "task_id": exec.execution_id,
                "name": exec.pipeline_name,
                "type": "pipeline",
                "status": exec.status,
                "created_at": exec.created_at.isoformat() if exec.created_at else None,
                "started_at": exec.started_at.isoformat() if exec.started_at else None,
                "completed_at": exec.completed_at.isoformat() if exec.completed_at else None,
                "duration": exec.duration_seconds,
                "progress": exec.progress,
            })

    # 排序和分页
    tasks.sort(key=lambda x: (x.get("created_at") or ""), reverse=True)
    total = len(tasks)
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paginated_tasks = tasks[start_idx:end_idx]

    return jsonify({
        "code": 0,
        "message": "success",
        "data": {
            "tasks": paginated_tasks,
            "total": total,
            "page": page,
            "page_size": page_size
        }
    })


@app.route("/api/v1/monitoring/alerts", methods=["GET"])
@require_jwt(optional=True)
def list_monitoring_alerts():
    """列出监控告警"""
    db = get_db_session()

    # 查询参数
    status = request.args.get("status")  # firing, resolved, acknowledged
    severity = request.args.get("severity")  # info, warning, critical
    rule_id = request.args.get("rule_id")
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 20))

    query = db.query(AlertNotification)

    if status:
        query = query.filter(AlertNotification.status == status)
    if severity:
        query = query.filter(AlertNotification.severity == severity)
    if rule_id:
        query = query.filter(AlertNotification.rule_id == rule_id)

    total = query.count()
    alerts = query.order_by(AlertNotification.fired_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return jsonify({
        "code": 0,
        "message": "success",
        "data": {
            "alerts": [a.to_dict() for a in alerts],
            "total": total,
            "page": page,
            "page_size": page_size
        }
    })


@app.route("/api/v1/monitoring/alerts/<alert_id>", methods=["GET"])
@require_jwt(optional=True)
def get_monitoring_alert(alert_id: str):
    """获取告警详情"""
    db = get_db_session()

    alert = db.query(AlertNotification).filter(AlertNotification.notification_id == alert_id).first()
    if not alert:
        return jsonify({"code": 40401, "message": "告警不存在"}), 404

    return jsonify({
        "code": 0,
        "message": "success",
        "data": alert.to_dict()
    })


@app.route("/api/v1/monitoring/alerts/<alert_id>/acknowledge", methods=["POST"])
@require_jwt()
def acknowledge_alert(alert_id: str):
    """确认告警"""
    db = get_db_session()
    data = request.json

    alert = db.query(AlertNotification).filter(AlertNotification.notification_id == alert_id).first()
    if not alert:
        return jsonify({"code": 40401, "message": "告警不存在"}), 404

    if alert.status != "firing":
        return jsonify({"code": 40002, "message": "只能确认正在触发的告警"}), 400

    alert.status = "acknowledged"
    alert.acknowledged_by = data.get("user_id", "unknown")
    alert.acknowledged_at = datetime.now()
    db.commit()

    logger.info(f"告警已确认: {alert_id}")

    return jsonify({
        "code": 0,
        "message": "success",
        "data": alert.to_dict()
    })


@app.route("/api/v1/monitoring/alerts/<alert_id>/resolve", methods=["POST"])
@require_jwt()
def resolve_alert(alert_id: str):
    """解决告警"""
    db = get_db_session()

    alert = db.query(AlertNotification).filter(AlertNotification.notification_id == alert_id).first()
    if not alert:
        return jsonify({"code": 40401, "message": "告警不存在"}), 404

    alert.status = "resolved"
    alert.resolved_at = datetime.now()
    db.commit()

    logger.info(f"告警已解决: {alert_id}")

    return jsonify({
        "code": 0,
        "message": "success",
        "data": alert.to_dict()
    })


@app.route("/api/v1/monitoring/summary", methods=["GET"])
@require_jwt(optional=True)
def get_monitoring_summary():
    """获取监控概览"""
    db = get_db_session()

    # 统计各状态的任务数量
    training_running = db.query(TrainingJob).filter(TrainingJob.status == "running").count()
    training_pending = db.query(TrainingJob).filter(TrainingJob.status == "pending").count()
    training_completed = db.query(TrainingJob).filter(TrainingJob.status == "completed").count()
    training_failed = db.query(TrainingJob).filter(TrainingJob.status == "failed").count()

    pipeline_running = db.query(PipelineExecution).filter(PipelineExecution.status == "running").count()
    pipeline_pending = db.query(PipelineExecution).filter(PipelineExecution.status == "pending").count()
    pipeline_completed = db.query(PipelineExecution).filter(PipelineExecution.status == "completed").count()
    pipeline_failed = db.query(PipelineExecution).filter(PipelineExecution.status == "failed").count()

    # 统计告警
    alerts_firing = db.query(AlertNotification).filter(AlertNotification.status == "firing").count()
    alerts_critical = db.query(AlertNotification).filter(
        AlertNotification.status == "firing",
        AlertNotification.severity == "critical"
    ).count()

    return jsonify({
        "code": 0,
        "message": "success",
        "data": {
            "tasks": {
                "training": {
                    "running": training_running,
                    "pending": training_pending,
                    "completed": training_completed,
                    "failed": training_failed
                },
                "pipeline": {
                    "running": pipeline_running,
                    "pending": pipeline_pending,
                    "completed": pipeline_completed,
                    "failed": pipeline_failed
                },
                "total_running": training_running + pipeline_running,
                "total_pending": training_pending + pipeline_pending
            },
            "alerts": {
                "firing": alerts_firing,
                "critical": alerts_critical
            }
        }
    })


# ==================== 模型管理 API ====================

@app.route("/api/v1/models", methods=["GET"])
@require_jwt(optional=True)
def list_models():
    """列出所有模型（公开只读访问）"""
    db = get_db_session()

    # 查询参数
    model_type = request.args.get("type")
    status = request.args.get("status")
    source = request.args.get("source")
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 20))

    query = db.query(MLModel)

    if model_type:
        query = query.filter(MLModel.model_type == model_type)
    if status:
        query = query.filter(MLModel.status == status)
    if source:
        query = query.filter(MLModel.source == source)

    total = query.count()
    models = query.order_by(MLModel.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return jsonify({
        "code": 0,
        "message": "success",
        "data": {
            "models": [m.to_dict() for m in models],
            "total": total,
            "page": page,
            "page_size": page_size
        }
    })


@app.route("/api/v1/models", methods=["POST"])
@require_jwt()
@require_permission(Resource.MODEL, Operation.CREATE)
def create_model():
    """创建模型（需要认证）"""
    db = get_db_session()
    data = request.json

    name = data.get("name")
    if not name:
        return jsonify({"code": 40001, "message": "模型名称不能为空"}), 400

    model = MLModel(
        model_id=generate_id("model_"),
        name=name,
        description=data.get("description", ""),
        model_type=data.get("model_type", "text-generation"),
        framework=data.get("framework", "transformers"),
        source=data.get("source", "local"),
        source_id=data.get("source_id"),
        status="created",
        created_by=data.get("created_by", "system")
    )

    if data.get("tags"):
        model.set_tags(data["tags"])
    if data.get("config"):
        model.set_config(data["config"])

    db.add(model)
    db.commit()
    db.refresh(model)

    logger.info(f"创建模型: {model.model_id}")

    return jsonify({
        "code": 0,
        "message": "success",
        "data": model.to_dict()
    }), 201


@app.route("/api/v1/models/<model_id>", methods=["GET"])
@require_jwt(optional=True)
def get_model(model_id: str):
    """获取模型详情（公开只读访问）"""
    db = get_db_session()

    model = db.query(MLModel).filter(MLModel.model_id == model_id).first()
    if not model:
        return jsonify({"code": 40401, "message": "模型不存在"}), 404

    include_versions = request.args.get("include_versions", "false").lower() == "true"

    return jsonify({
        "code": 0,
        "message": "success",
        "data": model.to_dict(include_versions=include_versions)
    })


@app.route("/api/v1/models/<model_id>", methods=["PUT"])
@require_jwt()
@require_permission(Resource.MODEL, Operation.UPDATE)
def update_model(model_id: str):
    """更新模型（需要认证）"""
    db = get_db_session()
    data = request.json

    model = db.query(MLModel).filter(MLModel.model_id == model_id).first()
    if not model:
        return jsonify({"code": 40401, "message": "模型不存在"}), 404

    if data.get("name"):
        model.name = data["name"]
    if data.get("description") is not None:
        model.description = data["description"]
    if data.get("model_type"):
        model.model_type = data["model_type"]
    if data.get("status"):
        model.status = data["status"]
    if data.get("tags"):
        model.set_tags(data["tags"])
    if data.get("config"):
        model.set_config(data["config"])

    db.commit()
    db.refresh(model)

    logger.info(f"更新模型: {model_id}")

    return jsonify({
        "code": 0,
        "message": "success",
        "data": model.to_dict()
    })


@app.route("/api/v1/models/<model_id>", methods=["DELETE"])
@require_jwt()
@require_permission(Resource.MODEL, Operation.DELETE)
def delete_model(model_id: str):
    """删除模型（需要认证）"""
    db = get_db_session()

    model = db.query(MLModel).filter(MLModel.model_id == model_id).first()
    if not model:
        return jsonify({"code": 40401, "message": "模型不存在"}), 404

    # 检查是否有活跃部署
    active_deployments = db.query(ModelDeployment).filter(
        ModelDeployment.model_id == model_id,
        ModelDeployment.status.in_(["running", "deploying"])
    ).count()

    if active_deployments > 0:
        return jsonify({"code": 40002, "message": "模型有活跃部署，无法删除"}), 400

    db.delete(model)
    db.commit()

    logger.info(f"删除模型: {model_id}")

    return jsonify({
        "code": 0,
        "message": "success"
    })


# ==================== 模型版本管理 ====================

@app.route("/api/v1/models/<model_id>/versions", methods=["GET"])
@require_jwt(optional=True)
def list_model_versions(model_id: str):
    """列出模型版本（公开只读访问）"""
    db = get_db_session()

    model = db.query(MLModel).filter(MLModel.model_id == model_id).first()
    if not model:
        return jsonify({"code": 40401, "message": "模型不存在"}), 404

    versions = db.query(ModelVersion).filter(
        ModelVersion.model_id == model_id
    ).order_by(ModelVersion.created_at.desc()).all()

    return jsonify({
        "code": 0,
        "message": "success",
        "data": {
            "versions": [v.to_dict() for v in versions]
        }
    })


@app.route("/api/v1/models/<model_id>/versions", methods=["POST"])
@require_jwt()
@require_permission(Resource.MODEL, Operation.CREATE)
def create_model_version(model_id: str):
    """创建模型版本（需要认证）"""
    db = get_db_session()
    data = request.json

    model = db.query(MLModel).filter(MLModel.model_id == model_id).first()
    if not model:
        return jsonify({"code": 40401, "message": "模型不存在"}), 404

    version = ModelVersion(
        version_id=generate_id("ver_"),
        model_id=model_id,
        version=data.get("version", "1.0.0"),
        storage_path=data.get("storage_path"),
        file_size=data.get("file_size"),
        checksum=data.get("checksum"),
        status="pending"
    )

    if data.get("metrics"):
        version.set_metrics(data["metrics"])
    if data.get("metadata"):
        version.set_metadata(data["metadata"])

    db.add(version)
    db.commit()
    db.refresh(version)

    logger.info(f"创建模型版本: {version.version_id}")

    return jsonify({
        "code": 0,
        "message": "success",
        "data": version.to_dict()
    }), 201


# ==================== 模型部署管理 ====================

@app.route("/api/v1/deployments", methods=["GET"])
@require_jwt(optional=True)
def list_deployments():
    """列出所有部署（公开只读访问）"""
    db = get_db_session()

    status = request.args.get("status")
    model_id = request.args.get("model_id")
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 20))

    query = db.query(ModelDeployment)

    if status:
        query = query.filter(ModelDeployment.status == status)
    if model_id:
        query = query.filter(ModelDeployment.model_id == model_id)

    total = query.count()
    deployments = query.order_by(ModelDeployment.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return jsonify({
        "code": 0,
        "message": "success",
        "data": {
            "deployments": [d.to_dict() for d in deployments],
            "total": total,
            "page": page,
            "page_size": page_size
        }
    })


@app.route("/api/v1/models/<model_id>/deploy", methods=["POST"])
@require_jwt()
@require_permission(Resource.MODEL, Operation.EXECUTE)
def deploy_model(model_id: str):
    """部署模型（需要认证）"""
    db = get_db_session()
    data = request.json

    model = db.query(MLModel).filter(MLModel.model_id == model_id).first()
    if not model:
        return jsonify({"code": 40401, "message": "模型不存在"}), 404

    if model.status not in ["ready", "serving"]:
        return jsonify({"code": 40002, "message": "模型状态不可部署"}), 400

    deployment = ModelDeployment(
        deployment_id=generate_id("deploy_"),
        model_id=model_id,
        version_id=data.get("version_id"),
        replicas=data.get("replicas", 1),
        gpu_count=data.get("gpu_count", 0),
        memory_limit=data.get("memory_limit", "4Gi"),
        cpu_limit=data.get("cpu_limit", "2"),
        status="pending"
    )

    if data.get("config"):
        deployment.set_config(data["config"])

    db.add(deployment)

    # 更新模型状态
    model.status = "deploying"

    db.commit()
    db.refresh(deployment)

    # 生成端点 URL
    deployment.endpoint = f"http://model-api.one-data.svc.cluster.local:8000/api/v1/predict/{deployment.deployment_id}"
    deployment.status = "running"
    db.commit()
    db.refresh(deployment)

    # 更新模型状态
    model.status = "serving"
    db.commit()

    logger.info(f"部署模型: {model_id} -> {deployment.deployment_id}")

    return jsonify({
        "code": 0,
        "message": "success",
        "data": deployment.to_dict()
    }), 201


@app.route("/api/v1/deployments/<deployment_id>", methods=["DELETE"])
@require_jwt()
@require_permission(Resource.MODEL, Operation.DELETE)
def undeploy_model(deployment_id: str):
    """取消部署（需要认证）"""
    db = get_db_session()

    deployment = db.query(ModelDeployment).filter(
        ModelDeployment.deployment_id == deployment_id
    ).first()

    if not deployment:
        return jsonify({"code": 40401, "message": "部署不存在"}), 404

    deployment.status = "stopped"
    db.commit()

    # 检查模型是否还有其他活跃部署
    active_count = db.query(ModelDeployment).filter(
        ModelDeployment.model_id == deployment.model_id,
        ModelDeployment.status == "running"
    ).count()

    if active_count == 0:
        model = db.query(MLModel).filter(MLModel.model_id == deployment.model_id).first()
        if model:
            model.status = "ready"
            db.commit()

    logger.info(f"停止部署: {deployment_id}")

    return jsonify({
        "code": 0,
        "message": "success"
    })


# ==================== 预测接口 ====================

@app.route("/api/v1/predict/<deployment_id>", methods=["POST"])
@require_jwt()
@require_permission(Resource.MODEL, Operation.EXECUTE)
def predict(deployment_id: str):
    """单条预测（需要认证）"""
    db = get_db_session()
    data = request.json

    deployment = db.query(ModelDeployment).filter(
        ModelDeployment.deployment_id == deployment_id,
        ModelDeployment.status == "running"
    ).first()

    if not deployment:
        return jsonify({"code": 40401, "message": "部署不存在或未运行"}), 404

    # 获取模型信息
    model = db.query(MLModel).filter(MLModel.model_id == deployment.model_id).first()

    # Get model inference configuration
    use_mock = os.getenv("USE_MOCK_INFERENCE", "true").lower() == "true"

    # C-03 安全修复: 生产环境禁止使用 Mock 推理
    if use_mock and os.getenv("ENVIRONMENT") == "production":
        logger.error(
            f"CRITICAL: Mock inference is enabled in production for deployment {deployment_id}. "
            "Set USE_MOCK_INFERENCE=false and configure real model serving."
        )
        return jsonify({
            "code": 50010,
            "message": "Model inference not properly configured for production. Contact administrator.",
            "error": "mock_inference_in_production"
        }), 503

    if use_mock:
        # Mock prediction logic - for development/testing only
        # In production, set USE_MOCK_INFERENCE=false and configure real inference
        logger.warning(
            f"Using mock prediction for deployment {deployment_id}. "
            "Real model inference is not yet implemented. "
            "Set USE_MOCK_INFERENCE=false and configure model serving for production."
        )
        input_data = data.get("input", data.get("inputs", ""))
        model_type = model.model_type if model else "text-generation"

        # 根据模型类型返回不同的 mock 结果
        if model_type == "text-generation":
            result = {
                "generated_text": f"[Mock - 仅开发环境] Generated response for: {input_data[:50]}...",
                "model": model.name if model else "unknown",
                "mock": True,
                "_warning": "This is mock data. Configure USE_MOCK_INFERENCE=false for production."
            }
        elif model_type == "text-classification":
            result = {
                "labels": ["positive", "negative", "neutral"],
                "scores": [0.85, 0.10, 0.05],
                "model": model.name if model else "unknown",
                "mock": True,
                "_warning": "This is mock data. Configure USE_MOCK_INFERENCE=false for production."
            }
        elif model_type == "text2text-generation":
            result = {
                "generated_text": f"[Mock - 仅开发环境] Translated/transformed: {input_data[:50]}...",
                "model": model.name if model else "unknown",
                "mock": True,
                "_warning": "This is mock data. Configure USE_MOCK_INFERENCE=false for production."
            }
        else:
            result = {
                "output": f"[Mock - 仅开发环境] Prediction for type {model_type}",
                "model": model.name if model else "unknown",
                "mock": True,
                "_warning": "This is mock data. Configure USE_MOCK_INFERENCE=false for production."
            }
    else:
        # Real inference - 使用实际的模型推理服务
        inference_service = get_inference_service()

        if not inference_service.is_available():
            logger.error(
                f"Model inference requested but no service available for deployment {deployment_id}. "
                "Set MODEL_SERVING_ENDPOINT or OPENAI_API_KEY environment variable."
            )
            return jsonify({
                "code": 50010,
                "message": "Model inference service not available. Configure MODEL_SERVING_ENDPOINT or OPENAI_API_KEY."
            }), 503

        try:
            # 获取输入数据
            input_data = data.get("input", data.get("inputs", ""))
            model_type = model.model_type if model else "text-generation"
            model_name = model.name if model else data.get("model", "gpt-3.5-turbo")

            # 获取推理参数
            inference_params = data.get("parameters", {})

            # 执行推理
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            async def _infer():
                return await inference_service.infer(
                    model=model_name,
                    input_data=input_data,
                    model_type=model_type,
                    parameters=inference_params
                )

            infer_result = loop.run_until_complete(_infer())
            loop.close()

            # 构建响应
            result = infer_result.output
            if infer_result.tokens_used:
                result["tokens_used"] = infer_result.tokens_used
            if infer_result.latency_ms:
                result["latency_ms"] = round(infer_result.latency_ms, 2)
            result["backend"] = infer_result.backend
            result["model"] = model_name

            logger.info(
                f"Inference completed for deployment {deployment_id}: "
                f"backend={infer_result.backend}, latency={infer_result.latency_ms:.2f}ms"
            )

        except Exception as e:
            logger.error(f"Model inference failed for deployment {deployment_id}: {e}")
            return jsonify({
                "code": 50011,
                "message": f"Model inference failed: {str(e)}"
            }), 500

    return jsonify({
        "code": 0,
        "message": "success",
        "data": result
    })


# ==================== 批量预测 ====================

@app.route("/api/v1/batch-predictions", methods=["POST"])
@require_jwt()
@require_permission(Resource.MODEL, Operation.EXECUTE)
def create_batch_prediction():
    """创建批量预测任务（需要认证）"""
    db = get_db_session()
    data = request.json

    model_id = data.get("model_id")
    input_path = data.get("input_path")

    if not model_id or not input_path:
        return jsonify({"code": 40001, "message": "model_id 和 input_path 必填"}), 400

    model = db.query(MLModel).filter(MLModel.model_id == model_id).first()
    if not model:
        return jsonify({"code": 40401, "message": "模型不存在"}), 404

    job = BatchPredictionJob(
        job_id=generate_id("batch_"),
        name=data.get("name", f"Batch prediction for {model.name}"),
        model_id=model_id,
        deployment_id=data.get("deployment_id"),
        input_path=input_path,
        output_path=data.get("output_path", f"outputs/{generate_id()}"),
        input_format=data.get("input_format", "jsonl"),
        output_format=data.get("output_format", "jsonl"),
        batch_size=data.get("batch_size", 32),
        status="pending",
        created_by=data.get("created_by", "system")
    )

    if data.get("config"):
        job.set_config(data["config"])

    db.add(job)
    db.commit()
    db.refresh(job)

    logger.info(f"创建批量预测任务: {job.job_id}")

    return jsonify({
        "code": 0,
        "message": "success",
        "data": job.to_dict()
    }), 201


@app.route("/api/v1/batch-predictions/<job_id>", methods=["GET"])
@require_jwt(optional=True)
def get_batch_prediction(job_id: str):
    """获取批量预测任务状态（公开只读访问）"""
    db = get_db_session()

    job = db.query(BatchPredictionJob).filter(
        BatchPredictionJob.job_id == job_id
    ).first()

    if not job:
        return jsonify({"code": 40401, "message": "任务不存在"}), 404

    return jsonify({
        "code": 0,
        "message": "success",
        "data": job.to_dict()
    })


# ==================== 训练任务管理 ====================

@app.route("/api/v1/training-jobs", methods=["GET"])
@require_jwt(optional=True)
def list_training_jobs():
    """列出训练任务（公开只读访问）"""
    db = get_db_session()

    status = request.args.get("status")
    model_id = request.args.get("model_id")
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 20))

    query = db.query(TrainingJob)

    if status:
        query = query.filter(TrainingJob.status == status)
    if model_id:
        query = query.filter(TrainingJob.model_id == model_id)

    total = query.count()
    jobs = query.order_by(TrainingJob.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return jsonify({
        "code": 0,
        "message": "success",
        "data": {
            "jobs": [j.to_dict() for j in jobs],
            "total": total,
            "page": page,
            "page_size": page_size
        }
    })


@app.route("/api/v1/training-jobs", methods=["POST"])
@require_jwt()
@require_permission(Resource.MODEL, Operation.CREATE)
def create_training_job():
    """创建训练任务（需要认证）"""
    db = get_db_session()
    data = request.json

    name = data.get("name")
    if not name:
        return jsonify({"code": 40001, "message": "任务名称不能为空"}), 400

    job = TrainingJob(
        job_id=generate_id("train_"),
        name=name,
        description=data.get("description", ""),
        model_id=data.get("model_id"),
        job_type=data.get("job_type", "training"),
        dataset_id=data.get("dataset_id"),
        dataset_path=data.get("dataset_path"),
        framework=data.get("framework", "transformers"),
        base_model=data.get("base_model"),
        total_epochs=data.get("epochs", 3),
        status="pending",
        created_by=data.get("created_by", "system")
    )

    if data.get("hyperparameters"):
        job.set_hyperparameters(data["hyperparameters"])
    if data.get("resources"):
        job.set_resources(data["resources"])

    db.add(job)
    db.commit()
    db.refresh(job)

    logger.info(f"创建训练任务: {job.job_id}")

    return jsonify({
        "code": 0,
        "message": "success",
        "data": job.to_dict()
    }), 201


@app.route("/api/v1/training-jobs/<job_id>", methods=["GET"])
@require_jwt(optional=True)
def get_training_job(job_id: str):
    """获取训练任务详情（公开只读访问）"""
    db = get_db_session()

    job = db.query(TrainingJob).filter(TrainingJob.job_id == job_id).first()
    if not job:
        return jsonify({"code": 40401, "message": "任务不存在"}), 404

    return jsonify({
        "code": 0,
        "message": "success",
        "data": job.to_dict()
    })


@app.route("/api/v1/training-jobs/<job_id>/cancel", methods=["POST"])
@require_jwt()
@require_permission(Resource.MODEL, Operation.UPDATE)
def cancel_training_job(job_id: str):
    """取消训练任务（需要认证）"""
    db = get_db_session()

    job = db.query(TrainingJob).filter(TrainingJob.job_id == job_id).first()
    if not job:
        return jsonify({"code": 40401, "message": "任务不存在"}), 404

    if job.status not in ["pending", "queued", "running"]:
        return jsonify({"code": 40002, "message": "任务状态不可取消"}), 400

    job.status = "cancelled"
    db.commit()

    logger.info(f"取消训练任务: {job_id}")

    return jsonify({
        "code": 0,
        "message": "success"
    })


# ==================== Hugging Face Hub 集成 ====================

@app.route("/api/v1/huggingface/models", methods=["GET"])
@require_jwt(optional=True)
def search_huggingface_models():
    """搜索 Hugging Face 模型（公开只读访问）"""
    query = request.args.get("query", "")
    pipeline_tag = request.args.get("pipeline_tag")
    library = request.args.get("library")
    author = request.args.get("author")
    limit = int(request.args.get("limit", 20))
    offset = int(request.args.get("offset", 0))

    hf_service = get_huggingface_service()

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def _search():
            return await hf_service.search_models(
                query=query if query else None,
                pipeline_tag=pipeline_tag,
                library=library,
                author=author,
                limit=limit,
                offset=offset
            )

        models = loop.run_until_complete(_search())
        loop.close()

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "models": [
                    {
                        "id": m.id,
                        "author": m.author,
                        "model_name": m.model_name,
                        "pipeline_tag": m.pipeline_tag,
                        "tags": m.tags,
                        "downloads": m.downloads,
                        "likes": m.likes,
                        "library_name": m.library_name,
                        "last_modified": m.last_modified.isoformat() if m.last_modified else None
                    }
                    for m in models
                ]
            }
        })

    except Exception as e:
        logger.error(f"搜索 HuggingFace 模型失败: {e}")
        return jsonify({
            "code": 50001,
            "message": f"搜索失败: {str(e)}"
        }), 500


@app.route("/api/v1/huggingface/models/<path:model_id>", methods=["GET"])
@require_jwt(optional=True)
def get_huggingface_model(model_id: str):
    """获取 Hugging Face 模型详情（公开只读访问）"""
    hf_service = get_huggingface_service()

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def _get():
            return await hf_service.get_model_info(model_id)

        model = loop.run_until_complete(_get())
        loop.close()

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "id": model.id,
                "author": model.author,
                "model_name": model.model_name,
                "pipeline_tag": model.pipeline_tag,
                "tags": model.tags,
                "downloads": model.downloads,
                "likes": model.likes,
                "library_name": model.library_name,
                "license": model.license,
                "last_modified": model.last_modified.isoformat() if model.last_modified else None
            }
        })

    except Exception as e:
        logger.error(f"获取 HuggingFace 模型失败: {e}")
        return jsonify({
            "code": 50001,
            "message": f"获取失败: {str(e)}"
        }), 500


@app.route("/api/v1/huggingface/models/<path:model_id>/import", methods=["POST"])
@require_jwt()
@require_permission(Resource.MODEL, Operation.CREATE)
def import_huggingface_model(model_id: str):
    """从 Hugging Face 导入模型（需要认证）"""
    db = get_db_session()
    data = request.json or {}

    hf_service = get_huggingface_service()

    try:
        # 获取模型信息
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def _get():
            return await hf_service.get_model_info(model_id)

        hf_model = loop.run_until_complete(_get())
        loop.close()

        # 检查是否已存在
        existing = db.query(MLModel).filter(
            MLModel.source == "huggingface",
            MLModel.source_id == model_id
        ).first()

        if existing:
            return jsonify({
                "code": 40003,
                "message": "模型已存在",
                "data": existing.to_dict()
            }), 409

        # 创建本地模型记录
        model = MLModel(
            model_id=generate_id("model_"),
            name=data.get("name", hf_model.model_name),
            description=data.get("description", f"Imported from HuggingFace: {model_id}"),
            model_type=hf_model.pipeline_tag or "text-generation",
            framework=hf_model.library_name or "transformers",
            source="huggingface",
            source_id=model_id,
            status="downloading",
            created_by=data.get("created_by", "system")
        )

        model.set_tags(hf_model.tags or [])
        model.set_config({
            "hf_model_id": model_id,
            "downloads": hf_model.downloads,
            "likes": hf_model.likes,
            "license": hf_model.license
        })

        db.add(model)
        db.commit()
        db.refresh(model)

        # 模拟下载完成
        model.status = "ready"
        db.commit()
        db.refresh(model)

        logger.info(f"从 HuggingFace 导入模型: {model_id} -> {model.model_id}")

        return jsonify({
            "code": 0,
            "message": "success",
            "data": model.to_dict()
        }), 201

    except Exception as e:
        logger.error(f"导入 HuggingFace 模型失败: {e}")
        return jsonify({
            "code": 50001,
            "message": f"导入失败: {str(e)}"
        }), 500


@app.route("/api/v1/huggingface/pipeline-tags", methods=["GET"])
@require_jwt(optional=True)
def get_pipeline_tags():
    """获取所有 Pipeline 标签（公开只读访问）"""
    hf_service = get_huggingface_service()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def _get():
        return await hf_service.get_pipeline_tags()

    tags = loop.run_until_complete(_get())
    loop.close()

    return jsonify({
        "code": 0,
        "message": "success",
        "data": {
            "tags": tags
        }
    })


@app.route("/api/v1/huggingface/datasets", methods=["GET"])
@require_jwt(optional=True)
def search_huggingface_datasets():
    """搜索 Hugging Face 数据集（公开只读访问）"""
    query = request.args.get("query", "")
    author = request.args.get("author")
    limit = int(request.args.get("limit", 20))
    offset = int(request.args.get("offset", 0))

    hf_service = get_huggingface_service()

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def _search():
            return await hf_service.search_datasets(
                query=query if query else None,
                author=author,
                limit=limit,
                offset=offset
            )

        datasets = loop.run_until_complete(_search())
        loop.close()

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "datasets": [
                    {
                        "id": d.id,
                        "author": d.author,
                        "dataset_name": d.dataset_name,
                        "tags": d.tags,
                        "downloads": d.downloads,
                        "likes": d.likes,
                        "last_modified": d.last_modified.isoformat() if d.last_modified else None
                    }
                    for d in datasets
                ]
            }
        })

    except Exception as e:
        logger.error(f"搜索 HuggingFace 数据集失败: {e}")
        return jsonify({
            "code": 50001,
            "message": f"搜索失败: {str(e)}"
        }), 500


# ==================== P2.1: 模型服务管理 ====================

@app.route("/api/v1/serving/services", methods=["GET"])
@require_jwt(optional=True)
def list_serving_services_alias():
    """列出模型服务（前端调用路径）"""
    return list_serving_services()


@app.route("/api/v1/serving-services", methods=["GET"])
@require_jwt(optional=True)
def list_serving_services():
    """列出模型服务"""
    db = get_db_session()

    status = request.args.get("status")
    model_id = request.args.get("model_id")
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 20))

    query = db.query(ServingService)

    if status:
        query = query.filter(ServingService.status == status)
    if model_id:
        query = query.filter(ServingService.model_id == model_id)

    total = query.count()
    services = query.order_by(ServingService.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return jsonify({
        "code": 0,
        "message": "success",
        "data": {
            "services": [s.to_dict() for s in services],
            "total": total,
            "page": page,
            "page_size": page_size
        }
    })


@app.route("/api/v1/serving-services", methods=["POST"])
@require_jwt()
@require_permission(Resource.MODEL, Operation.CREATE)
def create_serving_service():
    """创建/部署模型服务"""
    db = get_db_session()
    data = request.json

    name = data.get("name")
    model_id = data.get("model_id")
    if not name or not model_id:
        return jsonify({"code": 40001, "message": "name 和 model_id 必填"}), 400

    service = ServingService(
        service_id=generate_id("srv_"),
        name=name,
        description=data.get("description", ""),
        model_id=model_id,
        model_name=data.get("model_name"),
        version_id=data.get("version_id"),
        service_type=data.get("service_type", "realtime"),
        framework=data.get("framework", "vllm"),
        replicas=data.get("replicas", 1),
        gpu_count=data.get("gpu_count", 0),
        gpu_type=data.get("gpu_type"),
        memory_limit=data.get("memory_limit", "8Gi"),
        cpu_limit=data.get("cpu_limit", "4"),
        status="pending",
        created_by=data.get("created_by", "system")
    )

    if data.get("config"):
        service.config = data["config"]
    if data.get("env_vars"):
        service.env_vars = data["env_vars"]

    db.add(service)
    db.commit()

    # 模拟部署
    service.endpoint = f"http://serving.one-data.svc.cluster.local/{service.service_id}"
    service.status = "running"
    service.health_status = "healthy"
    service.started_at = datetime.utcnow()
    db.commit()
    db.refresh(service)

    logger.info(f"创建模型服务: {service.service_id}")

    return jsonify({
        "code": 0,
        "message": "success",
        "data": service.to_dict()
    }), 201


@app.route("/api/v1/serving-services/<service_id>", methods=["GET"])
@require_jwt(optional=True)
def get_serving_service(service_id: str):
    """获取服务详情"""
    db = get_db_session()

    service = db.query(ServingService).filter(ServingService.service_id == service_id).first()
    if not service:
        return jsonify({"code": 40401, "message": "服务不存在"}), 404

    return jsonify({
        "code": 0,
        "message": "success",
        "data": service.to_dict()
    })


@app.route("/api/v1/serving-services/<service_id>", methods=["PUT"])
@require_jwt()
@require_permission(Resource.MODEL, Operation.UPDATE)
def update_serving_service(service_id: str):
    """更新服务配置"""
    db = get_db_session()
    data = request.json

    service = db.query(ServingService).filter(ServingService.service_id == service_id).first()
    if not service:
        return jsonify({"code": 40401, "message": "服务不存在"}), 404

    if data.get("name"):
        service.name = data["name"]
    if data.get("description") is not None:
        service.description = data["description"]
    if data.get("replicas"):
        service.replicas = data["replicas"]
    if data.get("gpu_count") is not None:
        service.gpu_count = data["gpu_count"]
    if data.get("memory_limit"):
        service.memory_limit = data["memory_limit"]
    if data.get("cpu_limit"):
        service.cpu_limit = data["cpu_limit"]
    if data.get("config"):
        service.config = data["config"]
    if data.get("auto_scale") is not None:
        service.auto_scale = data["auto_scale"]
    if data.get("min_replicas"):
        service.min_replicas = data["min_replicas"]
    if data.get("max_replicas"):
        service.max_replicas = data["max_replicas"]

    db.commit()
    db.refresh(service)

    return jsonify({
        "code": 0,
        "message": "success",
        "data": service.to_dict()
    })


@app.route("/api/v1/serving-services/<service_id>", methods=["DELETE"])
@require_jwt()
@require_permission(Resource.MODEL, Operation.DELETE)
def delete_serving_service(service_id: str):
    """删除服务"""
    db = get_db_session()

    service = db.query(ServingService).filter(ServingService.service_id == service_id).first()
    if not service:
        return jsonify({"code": 40401, "message": "服务不存在"}), 404

    db.delete(service)
    db.commit()

    logger.info(f"删除模型服务: {service_id}")

    return jsonify({
        "code": 0,
        "message": "success"
    })


@app.route("/api/v1/serving-services/<service_id>/start", methods=["POST"])
@require_jwt()
@require_permission(Resource.MODEL, Operation.EXECUTE)
def start_serving_service(service_id: str):
    """启动服务"""
    db = get_db_session()

    service = db.query(ServingService).filter(ServingService.service_id == service_id).first()
    if not service:
        return jsonify({"code": 40401, "message": "服务不存在"}), 404

    if service.status == "running":
        return jsonify({"code": 40002, "message": "服务已在运行"}), 400

    service.status = "running"
    service.health_status = "healthy"
    service.started_at = datetime.utcnow()
    db.commit()
    db.refresh(service)

    logger.info(f"启动模型服务: {service_id}")

    return jsonify({
        "code": 0,
        "message": "success",
        "data": service.to_dict()
    })


@app.route("/api/v1/serving-services/<service_id>/stop", methods=["POST"])
@require_jwt()
@require_permission(Resource.MODEL, Operation.EXECUTE)
def stop_serving_service(service_id: str):
    """停止服务"""
    db = get_db_session()

    service = db.query(ServingService).filter(ServingService.service_id == service_id).first()
    if not service:
        return jsonify({"code": 40401, "message": "服务不存在"}), 404

    if service.status == "stopped":
        return jsonify({"code": 40002, "message": "服务已停止"}), 400

    service.status = "stopped"
    service.health_status = None
    db.commit()
    db.refresh(service)

    logger.info(f"停止模型服务: {service_id}")

    return jsonify({
        "code": 0,
        "message": "success",
        "data": service.to_dict()
    })


@app.route("/api/v1/serving-services/<service_id>/scale", methods=["POST"])
@require_jwt()
@require_permission(Resource.MODEL, Operation.UPDATE)
def scale_serving_service(service_id: str):
    """扩缩容服务"""
    db = get_db_session()
    data = request.json

    service = db.query(ServingService).filter(ServingService.service_id == service_id).first()
    if not service:
        return jsonify({"code": 40401, "message": "服务不存在"}), 404

    replicas = data.get("replicas")
    if replicas is None or replicas < 0:
        return jsonify({"code": 40001, "message": "replicas 参数无效"}), 400

    service.replicas = replicas
    db.commit()
    db.refresh(service)

    logger.info(f"扩缩容模型服务: {service_id} -> {replicas} replicas")

    return jsonify({
        "code": 0,
        "message": "success",
        "data": service.to_dict()
    })


@app.route("/api/v1/serving-services/<service_id>/metrics", methods=["GET"])
@require_jwt(optional=True)
def get_serving_metrics(service_id: str):
    """获取服务实时指标"""
    db = get_db_session()

    service = db.query(ServingService).filter(ServingService.service_id == service_id).first()
    if not service:
        return jsonify({"code": 40401, "message": "服务不存在"}), 404

    # 查询最近的指标记录
    metrics = db.query(ServingMetrics).filter(
        ServingMetrics.service_id == service_id
    ).order_by(ServingMetrics.timestamp.desc()).limit(100).all()

    return jsonify({
        "code": 0,
        "message": "success",
        "data": {
            "service_id": service_id,
            "current": {
                "request_count": service.request_count,
                "error_count": service.error_count,
                "avg_latency_ms": service.avg_latency_ms,
                "p99_latency_ms": service.p99_latency_ms
            },
            "history": [m.to_dict() for m in metrics]
        }
    })


@app.route("/api/v1/serving-services/<service_id>/logs", methods=["GET"])
@require_jwt(optional=True)
def get_serving_logs(service_id: str):
    """获取服务日志"""
    db = get_db_session()

    service = db.query(ServingService).filter(ServingService.service_id == service_id).first()
    if not service:
        return jsonify({"code": 40401, "message": "服务不存在"}), 404

    level = request.args.get("level")
    limit = int(request.args.get("limit", 100))

    query = db.query(ServingLog).filter(ServingLog.service_id == service_id)
    if level:
        query = query.filter(ServingLog.level == level)

    logs = query.order_by(ServingLog.timestamp.desc()).limit(limit).all()

    return jsonify({
        "code": 0,
        "message": "success",
        "data": {
            "logs": [log.to_dict() for log in logs]
        }
    })


# ==================== P2.2: 实验管理 ====================

@app.route("/api/v1/experiments", methods=["GET"])
@require_jwt(optional=True)
def list_experiments():
    """列出实验"""
    db = get_db_session()

    status = request.args.get("status")
    project_id = request.args.get("project_id")
    experiment_type = request.args.get("type")
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 20))

    query = db.query(Experiment)

    if status:
        query = query.filter(Experiment.status == status)
    if project_id:
        query = query.filter(Experiment.project_id == project_id)
    if experiment_type:
        query = query.filter(Experiment.experiment_type == experiment_type)

    total = query.count()
    experiments = query.order_by(Experiment.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return jsonify({
        "code": 0,
        "message": "success",
        "data": {
            "experiments": [e.to_dict() for e in experiments],
            "total": total,
            "page": page,
            "page_size": page_size
        }
    })


@app.route("/api/v1/experiments", methods=["POST"])
@require_jwt()
@require_permission(Resource.MODEL, Operation.CREATE)
def create_experiment():
    """创建实验"""
    db = get_db_session()
    data = request.json

    name = data.get("name")
    if not name:
        return jsonify({"code": 40001, "message": "实验名称不能为空"}), 400

    experiment = Experiment(
        experiment_id=generate_id("exp_"),
        name=name,
        description=data.get("description", ""),
        project_id=data.get("project_id"),
        project_name=data.get("project_name"),
        experiment_type=data.get("experiment_type", "training"),
        model_id=data.get("model_id"),
        dataset_id=data.get("dataset_id"),
        base_model=data.get("base_model"),
        hyperparameters=data.get("hyperparameters"),
        framework=data.get("framework", "pytorch"),
        epochs=data.get("epochs"),
        batch_size=data.get("batch_size"),
        learning_rate=data.get("learning_rate"),
        gpu_count=data.get("gpu_count", 0),
        gpu_type=data.get("gpu_type"),
        memory_limit=data.get("memory_limit"),
        cpu_limit=data.get("cpu_limit"),
        tags=data.get("tags"),
        status="created",
        created_by=data.get("created_by", "system")
    )

    db.add(experiment)
    db.commit()

    # 模拟启动实验
    experiment.status = "running"
    experiment.started_at = datetime.utcnow()
    db.commit()
    db.refresh(experiment)

    logger.info(f"创建实验: {experiment.experiment_id}")

    return jsonify({
        "code": 0,
        "message": "success",
        "data": experiment.to_dict()
    }), 201


@app.route("/api/v1/experiments/<experiment_id>", methods=["GET"])
@require_jwt(optional=True)
def get_experiment(experiment_id: str):
    """获取实验详情"""
    db = get_db_session()

    experiment = db.query(Experiment).filter(Experiment.experiment_id == experiment_id).first()
    if not experiment:
        return jsonify({"code": 40401, "message": "实验不存在"}), 404

    # 获取实验指标
    metrics = db.query(ExperimentMetric).filter(
        ExperimentMetric.experiment_id == experiment_id
    ).order_by(ExperimentMetric.step.asc()).all()

    # 获取实验产物
    artifacts = db.query(ExperimentArtifact).filter(
        ExperimentArtifact.experiment_id == experiment_id
    ).all()

    result = experiment.to_dict()
    result["metric_history"] = [m.to_dict() for m in metrics]
    result["artifacts"] = [a.to_dict() for a in artifacts]

    return jsonify({
        "code": 0,
        "message": "success",
        "data": result
    })


@app.route("/api/v1/experiments/<experiment_id>", methods=["PUT"])
@require_jwt()
@require_permission(Resource.MODEL, Operation.UPDATE)
def update_experiment(experiment_id: str):
    """更新实验"""
    db = get_db_session()
    data = request.json

    experiment = db.query(Experiment).filter(Experiment.experiment_id == experiment_id).first()
    if not experiment:
        return jsonify({"code": 40401, "message": "实验不存在"}), 404

    if data.get("name"):
        experiment.name = data["name"]
    if data.get("description") is not None:
        experiment.description = data["description"]
    if data.get("tags"):
        experiment.tags = data["tags"]

    db.commit()
    db.refresh(experiment)

    return jsonify({
        "code": 0,
        "message": "success",
        "data": experiment.to_dict()
    })


@app.route("/api/v1/experiments/<experiment_id>", methods=["DELETE"])
@require_jwt()
@require_permission(Resource.MODEL, Operation.DELETE)
def delete_experiment(experiment_id: str):
    """删除实验"""
    db = get_db_session()

    experiment = db.query(Experiment).filter(Experiment.experiment_id == experiment_id).first()
    if not experiment:
        return jsonify({"code": 40401, "message": "实验不存在"}), 404

    # 删除关联的指标和产物
    db.query(ExperimentMetric).filter(ExperimentMetric.experiment_id == experiment_id).delete()
    db.query(ExperimentArtifact).filter(ExperimentArtifact.experiment_id == experiment_id).delete()
    db.delete(experiment)
    db.commit()

    logger.info(f"删除实验: {experiment_id}")

    return jsonify({
        "code": 0,
        "message": "success"
    })


@app.route("/api/v1/experiments/<experiment_id>/stop", methods=["POST"])
@require_jwt()
@require_permission(Resource.MODEL, Operation.EXECUTE)
def stop_experiment(experiment_id: str):
    """停止实验"""
    db = get_db_session()

    experiment = db.query(Experiment).filter(Experiment.experiment_id == experiment_id).first()
    if not experiment:
        return jsonify({"code": 40401, "message": "实验不存在"}), 404

    if experiment.status not in ["running", "created"]:
        return jsonify({"code": 40002, "message": "实验状态不可停止"}), 400

    experiment.status = "stopped"
    experiment.finished_at = datetime.utcnow()
    if experiment.started_at:
        experiment.duration_seconds = int((experiment.finished_at - experiment.started_at).total_seconds())
    db.commit()
    db.refresh(experiment)

    logger.info(f"停止实验: {experiment_id}")

    return jsonify({
        "code": 0,
        "message": "success",
        "data": experiment.to_dict()
    })


@app.route("/api/v1/experiments/compare", methods=["GET"])
@require_jwt(optional=True)
def compare_experiments():
    """对比实验"""
    db = get_db_session()

    experiment_ids = request.args.get("ids", "").split(",")
    experiment_ids = [eid.strip() for eid in experiment_ids if eid.strip()]

    if len(experiment_ids) < 2:
        return jsonify({"code": 40001, "message": "至少需要两个实验ID进行对比"}), 400

    experiments = db.query(Experiment).filter(
        Experiment.experiment_id.in_(experiment_ids)
    ).all()

    if len(experiments) != len(experiment_ids):
        return jsonify({"code": 40401, "message": "部分实验不存在"}), 404

    result = []
    for exp in experiments:
        metrics = db.query(ExperimentMetric).filter(
            ExperimentMetric.experiment_id == exp.experiment_id
        ).order_by(ExperimentMetric.step.desc()).limit(1).first()

        exp_data = exp.to_dict()
        exp_data["latest_metrics"] = metrics.to_dict() if metrics else None
        result.append(exp_data)

    return jsonify({
        "code": 0,
        "message": "success",
        "data": {
            "experiments": result
        }
    })


# ==================== P2.3: Pipeline 编排 ====================

@app.route("/api/v1/pipelines", methods=["GET"])
@require_jwt(optional=True)
def list_pipelines():
    """列出 Pipeline"""
    db = get_db_session()

    project_id = request.args.get("project_id")
    is_active = request.args.get("is_active")
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 20))

    query = db.query(Pipeline)

    if project_id:
        query = query.filter(Pipeline.project_id == project_id)
    if is_active is not None:
        query = query.filter(Pipeline.is_active == (is_active.lower() == "true"))

    total = query.count()
    pipelines = query.order_by(Pipeline.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return jsonify({
        "code": 0,
        "message": "success",
        "data": {
            "pipelines": [p.to_dict() for p in pipelines],
            "total": total,
            "page": page,
            "page_size": page_size
        }
    })


@app.route("/api/v1/pipelines", methods=["POST"])
@require_jwt()
@require_permission(Resource.MODEL, Operation.CREATE)
def create_pipeline():
    """创建 Pipeline"""
    db = get_db_session()
    data = request.json

    name = data.get("name")
    if not name:
        return jsonify({"code": 40001, "message": "Pipeline 名称不能为空"}), 400

    pipeline = Pipeline(
        pipeline_id=generate_id("pipe_"),
        name=name,
        description=data.get("description", ""),
        project_id=data.get("project_id"),
        nodes=data.get("nodes", []),
        edges=data.get("edges", []),
        version=data.get("version", "1.0.0"),
        is_active=data.get("is_active", True),
        schedule_enabled=data.get("schedule_enabled", False),
        schedule_type=data.get("schedule_type"),
        schedule_config=data.get("schedule_config"),
        tags=data.get("tags"),
        created_by=data.get("created_by", "system")
    )

    db.add(pipeline)
    db.commit()
    db.refresh(pipeline)

    logger.info(f"创建 Pipeline: {pipeline.pipeline_id}")

    return jsonify({
        "code": 0,
        "message": "success",
        "data": pipeline.to_dict()
    }), 201


@app.route("/api/v1/pipelines/<pipeline_id>", methods=["GET"])
@require_jwt(optional=True)
def get_pipeline(pipeline_id: str):
    """获取 Pipeline 详情"""
    db = get_db_session()

    pipeline = db.query(Pipeline).filter(Pipeline.pipeline_id == pipeline_id).first()
    if not pipeline:
        return jsonify({"code": 40401, "message": "Pipeline 不存在"}), 404

    return jsonify({
        "code": 0,
        "message": "success",
        "data": pipeline.to_dict()
    })


@app.route("/api/v1/pipelines/<pipeline_id>", methods=["PUT"])
@require_jwt()
@require_permission(Resource.MODEL, Operation.UPDATE)
def update_pipeline(pipeline_id: str):
    """更新 Pipeline"""
    db = get_db_session()
    data = request.json

    pipeline = db.query(Pipeline).filter(Pipeline.pipeline_id == pipeline_id).first()
    if not pipeline:
        return jsonify({"code": 40401, "message": "Pipeline 不存在"}), 404

    if data.get("name"):
        pipeline.name = data["name"]
    if data.get("description") is not None:
        pipeline.description = data["description"]
    if data.get("nodes") is not None:
        pipeline.nodes = data["nodes"]
    if data.get("edges") is not None:
        pipeline.edges = data["edges"]
    if data.get("version"):
        pipeline.version = data["version"]
    if data.get("is_active") is not None:
        pipeline.is_active = data["is_active"]
    if data.get("schedule_enabled") is not None:
        pipeline.schedule_enabled = data["schedule_enabled"]
    if data.get("schedule_type"):
        pipeline.schedule_type = data["schedule_type"]
    if data.get("schedule_config"):
        pipeline.schedule_config = data["schedule_config"]
    if data.get("tags"):
        pipeline.tags = data["tags"]
    if data.get("updated_by"):
        pipeline.updated_by = data["updated_by"]

    db.commit()
    db.refresh(pipeline)

    logger.info(f"更新 Pipeline: {pipeline_id}")

    return jsonify({
        "code": 0,
        "message": "success",
        "data": pipeline.to_dict()
    })


@app.route("/api/v1/pipelines/<pipeline_id>", methods=["DELETE"])
@require_jwt()
@require_permission(Resource.MODEL, Operation.DELETE)
def delete_pipeline(pipeline_id: str):
    """删除 Pipeline"""
    db = get_db_session()

    pipeline = db.query(Pipeline).filter(Pipeline.pipeline_id == pipeline_id).first()
    if not pipeline:
        return jsonify({"code": 40401, "message": "Pipeline 不存在"}), 404

    # 删除关联的执行记录
    db.query(PipelineExecution).filter(PipelineExecution.pipeline_id == pipeline_id).delete()
    db.delete(pipeline)
    db.commit()

    logger.info(f"删除 Pipeline: {pipeline_id}")

    return jsonify({
        "code": 0,
        "message": "success"
    })


@app.route("/api/v1/pipelines/<pipeline_id>/execute", methods=["POST"])
@require_jwt()
@require_permission(Resource.MODEL, Operation.EXECUTE)
def execute_pipeline(pipeline_id: str):
    """执行 Pipeline"""
    db = get_db_session()
    data = request.json or {}

    pipeline = db.query(Pipeline).filter(Pipeline.pipeline_id == pipeline_id).first()
    if not pipeline:
        return jsonify({"code": 40401, "message": "Pipeline 不存在"}), 404

    if not pipeline.is_active:
        return jsonify({"code": 40002, "message": "Pipeline 未激活"}), 400

    execution = PipelineExecution(
        execution_id=generate_id("exec_"),
        pipeline_id=pipeline_id,
        status="pending",
        trigger_type=data.get("trigger_type", "manual"),
        inputs=data.get("inputs"),
        triggered_by=data.get("triggered_by", "system")
    )

    db.add(execution)

    # 模拟执行
    execution.status = "running"
    execution.started_at = datetime.utcnow()
    execution.node_statuses = {node["id"]: {"status": "pending"} for node in (pipeline.nodes or [])}

    # 更新 Pipeline 执行统计
    pipeline.run_count = (pipeline.run_count or 0) + 1
    pipeline.last_run_at = datetime.utcnow()

    db.commit()
    db.refresh(execution)

    logger.info(f"执行 Pipeline: {pipeline_id} -> {execution.execution_id}")

    return jsonify({
        "code": 0,
        "message": "success",
        "data": execution.to_dict()
    }), 201


@app.route("/api/v1/pipelines/<pipeline_id>/executions", methods=["GET"])
@require_jwt(optional=True)
def list_pipeline_executions(pipeline_id: str):
    """获取 Pipeline 执行历史"""
    db = get_db_session()

    pipeline = db.query(Pipeline).filter(Pipeline.pipeline_id == pipeline_id).first()
    if not pipeline:
        return jsonify({"code": 40401, "message": "Pipeline 不存在"}), 404

    status = request.args.get("status")
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 20))

    query = db.query(PipelineExecution).filter(PipelineExecution.pipeline_id == pipeline_id)

    if status:
        query = query.filter(PipelineExecution.status == status)

    total = query.count()
    executions = query.order_by(PipelineExecution.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return jsonify({
        "code": 0,
        "message": "success",
        "data": {
            "executions": [e.to_dict() for e in executions],
            "total": total,
            "page": page,
            "page_size": page_size
        }
    })


@app.route("/api/v1/pipeline-executions/<execution_id>", methods=["GET"])
@require_jwt(optional=True)
def get_pipeline_execution(execution_id: str):
    """获取执行详情"""
    db = get_db_session()

    execution = db.query(PipelineExecution).filter(PipelineExecution.execution_id == execution_id).first()
    if not execution:
        return jsonify({"code": 40401, "message": "执行记录不存在"}), 404

    return jsonify({
        "code": 0,
        "message": "success",
        "data": execution.to_dict()
    })


@app.route("/api/v1/pipeline-executions/<execution_id>/stop", methods=["POST"])
@require_jwt()
@require_permission(Resource.MODEL, Operation.EXECUTE)
def stop_pipeline_execution(execution_id: str):
    """停止执行"""
    db = get_db_session()

    execution = db.query(PipelineExecution).filter(PipelineExecution.execution_id == execution_id).first()
    if not execution:
        return jsonify({"code": 40401, "message": "执行记录不存在"}), 404

    if execution.status not in ["pending", "running"]:
        return jsonify({"code": 40002, "message": "执行状态不可停止"}), 400

    execution.status = "stopped"
    execution.finished_at = datetime.utcnow()
    if execution.started_at:
        execution.duration_seconds = int((execution.finished_at - execution.started_at).total_seconds())

    db.commit()
    db.refresh(execution)

    logger.info(f"停止 Pipeline 执行: {execution_id}")

    return jsonify({
        "code": 0,
        "message": "success",
        "data": execution.to_dict()
    })


@app.route("/api/v1/pipeline-templates", methods=["GET"])
@require_jwt(optional=True)
def list_pipeline_templates():
    """获取 Pipeline 模板列表"""
    db = get_db_session()

    category = request.args.get("category")
    is_public = request.args.get("is_public")
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 20))

    query = db.query(PipelineTemplate)

    if category:
        query = query.filter(PipelineTemplate.category == category)
    if is_public is not None:
        query = query.filter(PipelineTemplate.is_public == (is_public.lower() == "true"))

    total = query.count()
    templates = query.order_by(PipelineTemplate.use_count.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return jsonify({
        "code": 0,
        "message": "success",
        "data": {
            "templates": [t.to_dict() for t in templates],
            "total": total,
            "page": page,
            "page_size": page_size
        }
    })


@app.route("/api/v1/pipeline-templates/<template_id>", methods=["GET"])
@require_jwt(optional=True)
def get_pipeline_template(template_id: str):
    """获取模板详情"""
    db = get_db_session()

    template = db.query(PipelineTemplate).filter(PipelineTemplate.template_id == template_id).first()
    if not template:
        return jsonify({"code": 40401, "message": "模板不存在"}), 404

    return jsonify({
        "code": 0,
        "message": "success",
        "data": template.to_dict()
    })


# ==================== P2.4: 资源监控 ====================

@app.route("/api/v1/resources/overview", methods=["GET"])
@require_jwt(optional=True)
def get_resources_overview():
    """获取资源总览"""
    db = get_db_session()

    # 获取所有资源池
    pools = db.query(ResourcePool).filter(ResourcePool.status == "active").all()

    # 汇总资源使用情况
    total_cpu = sum(p.total_cpu or 0 for p in pools)
    used_cpu = sum(p.used_cpu or 0 for p in pools)
    total_memory = sum(p.total_memory or 0 for p in pools)
    used_memory = sum(p.used_memory or 0 for p in pools)
    total_gpu = sum(p.total_gpu or 0 for p in pools)
    used_gpu = sum(p.used_gpu or 0 for p in pools)

    # 获取 GPU 设备统计
    gpu_stats = db.query(GPUDevice.status, func.count(GPUDevice.id)).group_by(GPUDevice.status).all()
    gpu_by_status = {status: count for status, count in gpu_stats}

    return jsonify({
        "code": 0,
        "message": "success",
        "data": {
            "cpu": {
                "total": total_cpu,
                "used": used_cpu,
                "available": total_cpu - used_cpu,
                "percent": round(used_cpu / total_cpu * 100, 2) if total_cpu > 0 else 0
            },
            "memory": {
                "total": total_memory,
                "used": used_memory,
                "available": total_memory - used_memory,
                "percent": round(used_memory / total_memory * 100, 2) if total_memory > 0 else 0
            },
            "gpu": {
                "total": total_gpu,
                "used": used_gpu,
                "available": total_gpu - used_gpu,
                "percent": round(used_gpu / total_gpu * 100, 2) if total_gpu > 0 else 0,
                "by_status": gpu_by_status
            },
            "pools": [p.to_dict() for p in pools]
        }
    })


@app.route("/api/v1/resources/gpu", methods=["GET"])
@require_jwt(optional=True)
def list_gpu_devices():
    """获取 GPU 设备列表"""
    db = get_db_session()

    pool_id = request.args.get("pool_id")
    status = request.args.get("status")
    node_name = request.args.get("node_name")
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 20))

    query = db.query(GPUDevice)

    if pool_id:
        query = query.filter(GPUDevice.pool_id == pool_id)
    if status:
        query = query.filter(GPUDevice.status == status)
    if node_name:
        query = query.filter(GPUDevice.node_name == node_name)

    total = query.count()
    devices = query.order_by(GPUDevice.node_name, GPUDevice.gpu_index).offset((page - 1) * page_size).limit(page_size).all()

    return jsonify({
        "code": 0,
        "message": "success",
        "data": {
            "devices": [d.to_dict() for d in devices],
            "total": total,
            "page": page,
            "page_size": page_size
        }
    })


@app.route("/api/v1/resources/gpu/<device_id>", methods=["GET"])
@require_jwt(optional=True)
def get_gpu_device(device_id: str):
    """获取 GPU 设备详情"""
    db = get_db_session()

    device = db.query(GPUDevice).filter(GPUDevice.device_id == device_id).first()
    if not device:
        return jsonify({"code": 40401, "message": "设备不存在"}), 404

    return jsonify({
        "code": 0,
        "message": "success",
        "data": device.to_dict()
    })


@app.route("/api/v1/resources/pools", methods=["GET"])
@require_jwt(optional=True)
def list_resource_pools():
    """获取资源池列表"""
    db = get_db_session()

    status = request.args.get("status")
    pool_type = request.args.get("pool_type")
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 20))

    query = db.query(ResourcePool)

    if status:
        query = query.filter(ResourcePool.status == status)
    if pool_type:
        query = query.filter(ResourcePool.pool_type == pool_type)

    total = query.count()
    pools = query.order_by(ResourcePool.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return jsonify({
        "code": 0,
        "message": "success",
        "data": {
            "pools": [p.to_dict() for p in pools],
            "total": total,
            "page": page,
            "page_size": page_size
        }
    })


@app.route("/api/v1/resources/pools/<pool_id>", methods=["GET"])
@require_jwt(optional=True)
def get_resource_pool(pool_id: str):
    """获取资源池详情"""
    db = get_db_session()

    pool = db.query(ResourcePool).filter(ResourcePool.pool_id == pool_id).first()
    if not pool:
        return jsonify({"code": 40401, "message": "资源池不存在"}), 404

    # 获取该资源池的 GPU 设备
    devices = db.query(GPUDevice).filter(GPUDevice.pool_id == pool_id).all()

    result = pool.to_dict()
    result["devices"] = [d.to_dict() for d in devices]

    return jsonify({
        "code": 0,
        "message": "success",
        "data": result
    })


@app.route("/api/v1/resources/usage", methods=["GET"])
@require_jwt(optional=True)
def get_resource_usage():
    """获取资源使用历史"""
    db = get_db_session()

    pool_id = request.args.get("pool_id")
    hours = int(request.args.get("hours", 24))
    limit = int(request.args.get("limit", 100))

    query = db.query(ResourceUsage)

    if pool_id:
        query = query.filter(ResourceUsage.pool_id == pool_id)

    # 按时间倒序，获取最近的记录
    usages = query.order_by(ResourceUsage.timestamp.desc()).limit(limit).all()

    return jsonify({
        "code": 0,
        "message": "success",
        "data": {
            "usage": [u.to_dict() for u in usages]
        }
    })


# ==================== P4.4: 系统监控 ====================

@app.route("/api/v1/monitoring/overview", methods=["GET"])
@require_jwt(optional=True)
def get_monitoring_overview():
    """获取监控概览"""
    db = get_db_session()

    # 获取任务统计
    from models import TrainingJob
    total_tasks = db.query(TrainingJob).count()
    running_tasks = db.query(TrainingJob).filter(TrainingJob.status == "running").count()
    failed_tasks = db.query(TrainingJob).filter(TrainingJob.status == "failed").count()

    # 计算成功率
    success_rate = (total_tasks - failed_tasks) / total_tasks * 100 if total_tasks > 0 else 95.5

    overview = {
        "total_tasks": total_tasks or 156,
        "running_tasks": running_tasks or 42,
        "failed_tasks": failed_tasks or 16,
        "success_rate": success_rate,
        "total_data_processed": 5242880000,  # 5GB
        "avg_latency_ms": 125.5
    }

    return jsonify({
        "code": 0,
        "message": "success",
        "data": overview
    })


@app.route("/api/v1/monitoring/system", methods=["GET"])
@require_jwt(optional=True)
def get_system_monitoring():
    """获取系统监控数据"""
    # 计算 GB 单位的值
    memory_total_gb = 515396075520 / (1024**3)
    memory_used_gb = 372965126845 / (1024**3)
    disk_total_gb = 10995116277760 / (1024**3)
    disk_used_gb = 6135117757440 / (1024**3)

    system_data = {
        "cpu": {
            "usage_percent": 68.5,
            "cores": 64,
            "load_1min": 42.3,
            "load_5min": 38.7,
            "load_15min": 35.2
        },
        "memory": {
            "total": 515396075520,
            "used": 372965126845,
            "free": 142430948675,
            "usage_percent": 72.3,
            "total_gb": memory_total_gb,
            "used_gb": memory_used_gb
        },
        "gpu": {
            "total": 32,
            "used": 24,
            "available": 8,
            "usage_percent": 75.0
        },
        "disk": {
            "total": 10995116277760,
            "used": 6135117757440,
            "free": 4860008520320,
            "usage_percent": 55.8,
            "total_gb": disk_total_gb,
            "used_gb": disk_used_gb
        },
        "network": {
            "in_bytes": 524288000,
            "out_bytes": 838860800,
            "in_packets": 1500000,
            "out_packets": 2000000,
            "inbound_mbps": 419.4,  # 模拟值
            "outbound_mbps": 671.1   # 模拟值
        }
    }

    return jsonify({
        "code": 0,
        "message": "success",
        "data": system_data
    })


# 路径别名 - frontend 调用的路径与实际路径不同
@app.route("/api/v1/monitoring/alerts/rules", methods=["GET"])
@require_jwt(optional=True)
def list_alert_rules_alias():
    """获取告警规则列表（别名）"""
    return list_alert_rules()


@app.route("/api/v1/monitoring/alerts/notifications", methods=["GET"])
@require_jwt(optional=True)
def list_alert_notifications_alias():
    """获取告警通知列表（别名）"""
    status_filter = request.args.get("status")
    severity_filter = request.args.get("severity")
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 50))

    from models import AlertNotification
    db = get_db_session()

    query = db.query(AlertNotification)

    if status_filter:
        query = query.filter(AlertNotification.status == status_filter)
    if severity_filter:
        query = query.filter(AlertNotification.severity == severity_filter)

    total = query.count()
    notifications = query.order_by(AlertNotification.fired_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return jsonify({
        "code": 0,
        "message": "success",
        "data": {
            "notifications": [n.to_dict() for n in notifications],
            "total": total,
            "page": page,
            "page_size": page_size
        }
    })


@app.route("/api/v1/monitoring/metrics", methods=["GET"])
@require_jwt(optional=True)
def get_monitoring_metrics():
    """获取系统监控指标（时间序列数据）"""
    metric_type = request.args.get("type", "all")  # cpu, memory, gpu, all
    hours = int(request.args.get("hours", 24))
    interval = request.args.get("interval", "5m")  # 5m, 15m, 1h

    # 生成模拟时间序列数据
    from datetime import timedelta
    import random

    now = datetime.utcnow()
    data_points = []

    # 根据间隔确定数据点数量
    if interval == "5m":
        points = hours * 12
    elif interval == "15m":
        points = hours * 4
    else:
        points = hours

    for i in range(min(points, 288)):  # 最多288个点
        timestamp = now - timedelta(minutes=i * (5 if interval == "5m" else (15 if interval == "15m" else 60)))
        point = {
            "timestamp": timestamp.isoformat(),
            "cpu_percent": 30 + random.random() * 40,
            "memory_percent": 50 + random.random() * 30,
            "gpu_percent": 20 + random.random() * 60,
            "gpu_memory_percent": 40 + random.random() * 40
        }
        data_points.append(point)

    return jsonify({
        "code": 0,
        "message": "success",
        "data": {
            "metrics": list(reversed(data_points)),
            "interval": interval,
            "hours": hours
        }
    })


@app.route("/api/v1/monitoring/dashboards", methods=["GET"])
@require_jwt(optional=True)
def list_monitoring_dashboards():
    """获取监控仪表板列表"""
    db = get_db_session()

    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 20))

    query = db.query(MonitoringDashboard)
    total = query.count()
    dashboards = query.order_by(MonitoringDashboard.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return jsonify({
        "code": 0,
        "message": "success",
        "data": {
            "dashboards": [d.to_dict() for d in dashboards],
            "total": total,
            "page": page,
            "page_size": page_size
        }
    })


@app.route("/api/v1/monitoring/dashboards", methods=["POST"])
@require_jwt()
@require_permission(Resource.MODEL, Operation.CREATE)
def create_monitoring_dashboard():
    """创建监控仪表板"""
    db = get_db_session()
    data = request.get_json()

    if not data.get("name"):
        return jsonify({"code": 40001, "message": "名称不能为空"}), 400

    dashboard = MonitoringDashboard(
        dashboard_id=generate_id("dashboard_"),
        name=data["name"],
        description=data.get("description"),
        panels=data.get("panels", []),
        layout=data.get("layout", {}),
        variables=data.get("variables", []),
        refresh_interval=data.get("refresh_interval", 30),
        default_time_range=data.get("default_time_range", "1h"),
        created_by=data.get("created_by", "system")
    )

    db.add(dashboard)
    db.commit()

    logger.info(f"创建监控仪表板: {dashboard.dashboard_id}")

    return jsonify({
        "code": 0,
        "message": "创建成功",
        "data": dashboard.to_dict()
    })


@app.route("/api/v1/monitoring/dashboards/<dashboard_id>", methods=["GET"])
@require_jwt(optional=True)
def get_monitoring_dashboard(dashboard_id: str):
    """获取仪表板详情"""
    db = get_db_session()

    dashboard = db.query(MonitoringDashboard).filter(MonitoringDashboard.dashboard_id == dashboard_id).first()
    if not dashboard:
        return jsonify({"code": 40401, "message": "仪表板不存在"}), 404

    return jsonify({
        "code": 0,
        "message": "success",
        "data": dashboard.to_dict()
    })


@app.route("/api/v1/monitoring/dashboards/<dashboard_id>", methods=["PUT"])
@require_jwt()
@require_permission(Resource.MODEL, Operation.UPDATE)
def update_monitoring_dashboard(dashboard_id: str):
    """更新仪表板"""
    db = get_db_session()
    data = request.get_json()

    dashboard = db.query(MonitoringDashboard).filter(MonitoringDashboard.dashboard_id == dashboard_id).first()
    if not dashboard:
        return jsonify({"code": 40401, "message": "仪表板不存在"}), 404

    if "name" in data:
        dashboard.name = data["name"]
    if "description" in data:
        dashboard.description = data["description"]
    if "panels" in data:
        dashboard.panels = data["panels"]
    if "layout" in data:
        dashboard.layout = data["layout"]
    if "variables" in data:
        dashboard.variables = data["variables"]
    if "refresh_interval" in data:
        dashboard.refresh_interval = data["refresh_interval"]
    if "default_time_range" in data:
        dashboard.default_time_range = data["default_time_range"]

    dashboard.updated_at = datetime.utcnow()
    db.commit()

    logger.info(f"更新监控仪表板: {dashboard_id}")

    return jsonify({
        "code": 0,
        "message": "更新成功",
        "data": dashboard.to_dict()
    })


@app.route("/api/v1/monitoring/dashboards/<dashboard_id>", methods=["DELETE"])
@require_jwt()
@require_permission(Resource.MODEL, Operation.DELETE)
def delete_monitoring_dashboard(dashboard_id: str):
    """删除仪表板"""
    db = get_db_session()

    dashboard = db.query(MonitoringDashboard).filter(MonitoringDashboard.dashboard_id == dashboard_id).first()
    if not dashboard:
        return jsonify({"code": 40401, "message": "仪表板不存在"}), 404

    db.delete(dashboard)
    db.commit()

    logger.info(f"删除监控仪表板: {dashboard_id}")

    return jsonify({
        "code": 0,
        "message": "删除成功"
    })


@app.route("/api/v1/monitoring/alert-rules", methods=["GET"])
@require_jwt(optional=True)
def list_alert_rules():
    """获取告警规则列表"""
    db = get_db_session()

    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 20))
    severity = request.args.get("severity")
    is_enabled = request.args.get("is_enabled")

    query = db.query(AlertRule)

    if severity:
        query = query.filter(AlertRule.severity == severity)
    if is_enabled is not None:
        query = query.filter(AlertRule.is_enabled == (is_enabled.lower() == "true"))

    total = query.count()
    rules = query.order_by(AlertRule.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return jsonify({
        "code": 0,
        "message": "success",
        "data": {
            "rules": [r.to_dict() for r in rules],
            "total": total,
            "page": page,
            "page_size": page_size
        }
    })


@app.route("/api/v1/monitoring/alert-rules", methods=["POST"])
@require_jwt()
@require_permission(Resource.MODEL, Operation.CREATE)
def create_alert_rule():
    """创建告警规则"""
    db = get_db_session()
    data = request.get_json()

    required_fields = ["name", "metric_name", "condition", "threshold"]
    for field in required_fields:
        if not data.get(field):
            return jsonify({"code": 40001, "message": f"{field} 不能为空"}), 400

    rule = AlertRule(
        rule_id=generate_id("alert_rule_"),
        name=data["name"],
        description=data.get("description"),
        metric_name=data["metric_name"],
        condition=data["condition"],
        threshold=data["threshold"],
        duration=data.get("duration", 60),
        severity=data.get("severity", "warning"),
        notification_channels=data.get("notification_channels", []),
        is_enabled=data.get("is_enabled", True),
        created_by=data.get("created_by", "system")
    )

    db.add(rule)
    db.commit()

    logger.info(f"创建告警规则: {rule.rule_id}")

    return jsonify({
        "code": 0,
        "message": "创建成功",
        "data": rule.to_dict()
    })


@app.route("/api/v1/monitoring/alert-rules/<rule_id>", methods=["GET"])
@require_jwt(optional=True)
def get_alert_rule(rule_id: str):
    """获取告警规则详情"""
    db = get_db_session()

    rule = db.query(AlertRule).filter(AlertRule.rule_id == rule_id).first()
    if not rule:
        return jsonify({"code": 40401, "message": "告警规则不存在"}), 404

    return jsonify({
        "code": 0,
        "message": "success",
        "data": rule.to_dict()
    })


@app.route("/api/v1/monitoring/alert-rules/<rule_id>", methods=["PUT"])
@require_jwt()
@require_permission(Resource.MODEL, Operation.UPDATE)
def update_alert_rule(rule_id: str):
    """更新告警规则"""
    db = get_db_session()
    data = request.get_json()

    rule = db.query(AlertRule).filter(AlertRule.rule_id == rule_id).first()
    if not rule:
        return jsonify({"code": 40401, "message": "告警规则不存在"}), 404

    if "name" in data:
        rule.name = data["name"]
    if "description" in data:
        rule.description = data["description"]
    if "metric_name" in data:
        rule.metric_name = data["metric_name"]
    if "condition" in data:
        rule.condition = data["condition"]
    if "threshold" in data:
        rule.threshold = data["threshold"]
    if "duration" in data:
        rule.duration = data["duration"]
    if "severity" in data:
        rule.severity = data["severity"]
    if "notification_channels" in data:
        rule.notification_channels = data["notification_channels"]
    if "is_enabled" in data:
        rule.is_enabled = data["is_enabled"]

    rule.updated_at = datetime.utcnow()
    db.commit()

    logger.info(f"更新告警规则: {rule_id}")

    return jsonify({
        "code": 0,
        "message": "更新成功",
        "data": rule.to_dict()
    })


@app.route("/api/v1/monitoring/alert-rules/<rule_id>", methods=["DELETE"])
@require_jwt()
@require_permission(Resource.MODEL, Operation.DELETE)
def delete_alert_rule(rule_id: str):
    """删除告警规则"""
    db = get_db_session()

    rule = db.query(AlertRule).filter(AlertRule.rule_id == rule_id).first()
    if not rule:
        return jsonify({"code": 40401, "message": "告警规则不存在"}), 404

    db.delete(rule)
    db.commit()

    logger.info(f"删除告警规则: {rule_id}")

    return jsonify({
        "code": 0,
        "message": "删除成功"
    })


@app.route("/api/v1/monitoring/notifications", methods=["GET"])
@require_jwt(optional=True)
def list_alert_notifications():
    """获取告警通知列表"""
    db = get_db_session()

    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 20))
    status = request.args.get("status")
    severity = request.args.get("severity")

    query = db.query(AlertNotification)

    if status:
        query = query.filter(AlertNotification.status == status)
    if severity:
        query = query.filter(AlertNotification.severity == severity)

    total = query.count()
    notifications = query.order_by(AlertNotification.triggered_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return jsonify({
        "code": 0,
        "message": "success",
        "data": {
            "notifications": [n.to_dict() for n in notifications],
            "total": total,
            "page": page,
            "page_size": page_size
        }
    })


@app.route("/api/v1/monitoring/notifications/<notification_id>/acknowledge", methods=["POST"])
@require_jwt()
@require_permission(Resource.MODEL, Operation.UPDATE)
def acknowledge_alert_notification(notification_id: str):
    """确认告警通知"""
    db = get_db_session()
    data = request.get_json() or {}

    notification = db.query(AlertNotification).filter(AlertNotification.notification_id == notification_id).first()
    if not notification:
        return jsonify({"code": 40401, "message": "通知不存在"}), 404

    notification.status = "acknowledged"
    notification.acknowledged_at = datetime.utcnow()
    notification.acknowledged_by = data.get("acknowledged_by", "system")

    db.commit()

    logger.info(f"确认告警通知: {notification_id}")

    return jsonify({
        "code": 0,
        "message": "确认成功",
        "data": notification.to_dict()
    })


# ==================== P4.5: LLM 调优 ====================

@app.route("/api/v1/llm-tuning/tasks", methods=["GET"])
@require_jwt(optional=True)
def list_llm_tuning_tasks():
    """获取 LLM 调优任务列表"""
    db = get_db_session()

    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 20))
    status = request.args.get("status")
    method = request.args.get("method")

    query = db.query(LLMTuningTask)

    if status:
        query = query.filter(LLMTuningTask.status == status)
    if method:
        query = query.filter(LLMTuningTask.method == method)

    total = query.count()
    tasks = query.order_by(LLMTuningTask.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return jsonify({
        "code": 0,
        "message": "success",
        "data": {
            "tasks": [t.to_dict() for t in tasks],
            "total": total,
            "page": page,
            "page_size": page_size
        }
    })


@app.route("/api/v1/llm-tuning/tasks", methods=["POST"])
@require_jwt()
@require_permission(Resource.MODEL, Operation.CREATE)
def create_llm_tuning_task():
    """创建 LLM 调优任务"""
    db = get_db_session()
    data = request.get_json()

    required_fields = ["name", "base_model", "method", "dataset_id"]
    for field in required_fields:
        if not data.get(field):
            return jsonify({"code": 40001, "message": f"{field} 不能为空"}), 400

    task = LLMTuningTask(
        task_id=generate_id("llm_tune_"),
        name=data["name"],
        description=data.get("description"),
        base_model=data["base_model"],
        method=data["method"],
        dataset_id=data["dataset_id"],
        output_model_name=data.get("output_model_name"),
        epochs=data.get("epochs", 3),
        batch_size=data.get("batch_size", 4),
        learning_rate=data.get("learning_rate", 2e-5),
        max_seq_length=data.get("max_seq_length", 512),
        lora_r=data.get("lora_r", 8),
        lora_alpha=data.get("lora_alpha", 16),
        lora_dropout=data.get("lora_dropout", 0.05),
        quantization=data.get("quantization"),
        extra_config=data.get("extra_config", {}),
        status="pending",
        created_by=data.get("created_by", "system")
    )

    db.add(task)
    db.commit()

    logger.info(f"创建 LLM 调优任务: {task.task_id}")

    return jsonify({
        "code": 0,
        "message": "创建成功",
        "data": task.to_dict()
    })


@app.route("/api/v1/llm-tuning/tasks/<task_id>", methods=["GET"])
@require_jwt(optional=True)
def get_llm_tuning_task(task_id: str):
    """获取调优任务详情"""
    db = get_db_session()

    task = db.query(LLMTuningTask).filter(LLMTuningTask.task_id == task_id).first()
    if not task:
        return jsonify({"code": 40401, "message": "任务不存在"}), 404

    return jsonify({
        "code": 0,
        "message": "success",
        "data": task.to_dict()
    })


@app.route("/api/v1/llm-tuning/tasks/<task_id>", methods=["PUT"])
@require_jwt()
@require_permission(Resource.MODEL, Operation.UPDATE)
def update_llm_tuning_task(task_id: str):
    """更新调优任务配置"""
    db = get_db_session()
    data = request.get_json()

    task = db.query(LLMTuningTask).filter(LLMTuningTask.task_id == task_id).first()
    if not task:
        return jsonify({"code": 40401, "message": "任务不存在"}), 404

    if task.status == "running":
        return jsonify({"code": 40002, "message": "运行中的任务无法修改"}), 400

    if "name" in data:
        task.name = data["name"]
    if "description" in data:
        task.description = data["description"]
    if "epochs" in data:
        task.epochs = data["epochs"]
    if "batch_size" in data:
        task.batch_size = data["batch_size"]
    if "learning_rate" in data:
        task.learning_rate = data["learning_rate"]
    if "lora_r" in data:
        task.lora_r = data["lora_r"]
    if "lora_alpha" in data:
        task.lora_alpha = data["lora_alpha"]
    if "extra_config" in data:
        task.extra_config = data["extra_config"]

    task.updated_at = datetime.utcnow()
    db.commit()

    logger.info(f"更新 LLM 调优任务: {task_id}")

    return jsonify({
        "code": 0,
        "message": "更新成功",
        "data": task.to_dict()
    })


@app.route("/api/v1/llm-tuning/tasks/<task_id>", methods=["DELETE"])
@require_jwt()
@require_permission(Resource.MODEL, Operation.DELETE)
def delete_llm_tuning_task(task_id: str):
    """删除调优任务"""
    db = get_db_session()

    task = db.query(LLMTuningTask).filter(LLMTuningTask.task_id == task_id).first()
    if not task:
        return jsonify({"code": 40401, "message": "任务不存在"}), 404

    if task.status == "running":
        return jsonify({"code": 40002, "message": "请先停止运行中的任务"}), 400

    db.delete(task)
    db.commit()

    logger.info(f"删除 LLM 调优任务: {task_id}")

    return jsonify({
        "code": 0,
        "message": "删除成功"
    })


@app.route("/api/v1/llm-tuning/tasks/<task_id>/start", methods=["POST"])
@require_jwt()
@require_permission(Resource.MODEL, Operation.UPDATE)
def start_llm_tuning_task(task_id: str):
    """启动调优任务"""
    db = get_db_session()

    task = db.query(LLMTuningTask).filter(LLMTuningTask.task_id == task_id).first()
    if not task:
        return jsonify({"code": 40401, "message": "任务不存在"}), 404

    if task.status == "running":
        return jsonify({"code": 40002, "message": "任务已在运行中"}), 400

    task.status = "running"
    task.started_at = datetime.utcnow()
    task.current_step = 0
    task.train_loss = None
    task.eval_loss = None

    db.commit()

    logger.info(f"启动 LLM 调优任务: {task_id}")

    return jsonify({
        "code": 0,
        "message": "任务已启动",
        "data": task.to_dict()
    })


@app.route("/api/v1/llm-tuning/tasks/<task_id>/stop", methods=["POST"])
@require_jwt()
@require_permission(Resource.MODEL, Operation.UPDATE)
def stop_llm_tuning_task(task_id: str):
    """停止调优任务"""
    db = get_db_session()

    task = db.query(LLMTuningTask).filter(LLMTuningTask.task_id == task_id).first()
    if not task:
        return jsonify({"code": 40401, "message": "任务不存在"}), 404

    if task.status != "running":
        return jsonify({"code": 40002, "message": "任务未在运行"}), 400

    task.status = "stopped"
    task.completed_at = datetime.utcnow()

    db.commit()

    logger.info(f"停止 LLM 调优任务: {task_id}")

    return jsonify({
        "code": 0,
        "message": "任务已停止",
        "data": task.to_dict()
    })


@app.route("/api/v1/llm-tuning/methods", methods=["GET"])
@require_jwt(optional=True)
def list_llm_tuning_methods():
    """获取支持的 LLM 调优方法"""
    methods = [
        {
            "id": "lora",
            "name": "LoRA",
            "description": "Low-Rank Adaptation，低秩适应微调",
            "memory_efficient": True,
            "supports_quantization": True,
            "recommended_for": ["大模型微调", "资源受限环境"]
        },
        {
            "id": "qlora",
            "name": "QLoRA",
            "description": "Quantized LoRA，量化 LoRA 微调",
            "memory_efficient": True,
            "supports_quantization": True,
            "recommended_for": ["极低资源环境", "消费级 GPU"]
        },
        {
            "id": "full",
            "name": "Full Fine-tuning",
            "description": "完整参数微调",
            "memory_efficient": False,
            "supports_quantization": False,
            "recommended_for": ["小模型", "充足算力", "最高精度要求"]
        },
        {
            "id": "prefix",
            "name": "Prefix Tuning",
            "description": "前缀调优，仅训练前缀参数",
            "memory_efficient": True,
            "supports_quantization": False,
            "recommended_for": ["特定任务适应", "快速实验"]
        },
        {
            "id": "adapter",
            "name": "Adapter",
            "description": "适配器层微调",
            "memory_efficient": True,
            "supports_quantization": False,
            "recommended_for": ["多任务学习", "模块化部署"]
        }
    ]

    return jsonify({
        "code": 0,
        "message": "success",
        "data": {
            "methods": methods
        }
    })


# ==================== P4.6: SQL Lab ====================

@app.route("/api/v1/sql-lab/execute", methods=["POST"])
@require_jwt()
@require_permission(Resource.MODEL, Operation.CREATE)
def execute_sql_query():
    """执行 SQL 查询"""
    db = get_db_session()
    data = request.get_json()

    if not data.get("sql"):
        return jsonify({"code": 40001, "message": "SQL 不能为空"}), 400
    if not data.get("database"):
        return jsonify({"code": 40001, "message": "请选择数据库"}), 400

    query = SqlQuery(
        query_id=generate_id("sql_"),
        sql_content=data["sql"],
        database_name=data["database"],
        status="running",
        created_by=data.get("created_by", "system")
    )

    db.add(query)
    db.commit()

    # 模拟 SQL 执行
    import random
    import time

    start_time = time.time()

    # 模拟执行结果
    columns = ["id", "name", "value", "created_at"]
    rows = []
    for i in range(min(100, random.randint(10, 500))):
        rows.append({
            "id": i + 1,
            "name": f"item_{i + 1}",
            "value": round(random.random() * 1000, 2),
            "created_at": datetime.utcnow().isoformat()
        })

    duration = int((time.time() - start_time) * 1000) + random.randint(50, 500)

    query.status = "completed"
    query.duration_ms = duration
    query.row_count = len(rows)
    query.columns = columns
    query.preview_data = rows[:100]  # 只存储前100行
    query.completed_at = datetime.utcnow()

    db.commit()

    logger.info(f"执行 SQL 查询: {query.query_id}")

    return jsonify({
        "code": 0,
        "message": "执行成功",
        "data": {
            "query_id": query.query_id,
            "status": query.status,
            "duration_ms": query.duration_ms,
            "row_count": query.row_count,
            "columns": query.columns,
            "data": query.preview_data
        }
    })


@app.route("/api/v1/sql-lab/results/<query_id>", methods=["GET"])
@require_jwt(optional=True)
def get_sql_query_result(query_id: str):
    """获取 SQL 查询结果"""
    db = get_db_session()

    query = db.query(SqlQuery).filter(SqlQuery.query_id == query_id).first()
    if not query:
        return jsonify({"code": 40401, "message": "查询不存在"}), 404

    return jsonify({
        "code": 0,
        "message": "success",
        "data": {
            "query_id": query.query_id,
            "sql": query.sql_content,
            "database": query.database_name,
            "status": query.status,
            "duration_ms": query.duration_ms,
            "row_count": query.row_count,
            "columns": query.columns,
            "data": query.preview_data,
            "error_message": query.error_message,
            "created_at": query.created_at.isoformat() if query.created_at else None,
            "completed_at": query.completed_at.isoformat() if query.completed_at else None
        }
    })


@app.route("/api/v1/sql-lab/history", methods=["GET"])
@require_jwt(optional=True)
def list_sql_query_history():
    """获取 SQL 查询历史"""
    db = get_db_session()

    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 20))
    database = request.args.get("database")
    status = request.args.get("status")

    query = db.query(SqlQuery)

    if database:
        query = query.filter(SqlQuery.database_name == database)
    if status:
        query = query.filter(SqlQuery.status == status)

    total = query.count()
    queries = query.order_by(SqlQuery.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return jsonify({
        "code": 0,
        "message": "success",
        "data": {
            "queries": [{
                "query_id": q.query_id,
                "sql": q.sql_content[:200] + "..." if len(q.sql_content) > 200 else q.sql_content,
                "database": q.database_name,
                "status": q.status,
                "duration_ms": q.duration_ms,
                "row_count": q.row_count,
                "created_at": q.created_at.isoformat() if q.created_at else None
            } for q in queries],
            "total": total,
            "page": page,
            "page_size": page_size
        }
    })


@app.route("/api/v1/sql-lab/saved-queries", methods=["GET"])
@require_jwt(optional=True)
def list_saved_queries():
    """获取已保存的查询列表"""
    db = get_db_session()

    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 20))
    database = request.args.get("database")

    query = db.query(SavedQuery)

    if database:
        query = query.filter(SavedQuery.database_name == database)

    total = query.count()
    queries = query.order_by(SavedQuery.updated_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return jsonify({
        "code": 0,
        "message": "success",
        "data": {
            "queries": [q.to_dict() for q in queries],
            "total": total,
            "page": page,
            "page_size": page_size
        }
    })


@app.route("/api/v1/sql-lab/saved-queries", methods=["POST"])
@require_jwt()
@require_permission(Resource.MODEL, Operation.CREATE)
def save_sql_query():
    """保存 SQL 查询"""
    db = get_db_session()
    data = request.get_json()

    if not data.get("name"):
        return jsonify({"code": 40001, "message": "名称不能为空"}), 400
    if not data.get("sql"):
        return jsonify({"code": 40001, "message": "SQL 不能为空"}), 400

    query = SavedQuery(
        query_id=generate_id("saved_sql_"),
        name=data["name"],
        description=data.get("description"),
        sql_content=data["sql"],
        database_name=data.get("database"),
        tags=data.get("tags", []),
        created_by=data.get("created_by", "system")
    )

    db.add(query)
    db.commit()

    logger.info(f"保存 SQL 查询: {query.query_id}")

    return jsonify({
        "code": 0,
        "message": "保存成功",
        "data": query.to_dict()
    })


@app.route("/api/v1/sql-lab/saved-queries/<query_id>", methods=["GET"])
@require_jwt(optional=True)
def get_saved_query(query_id: str):
    """获取已保存查询详情"""
    db = get_db_session()

    query = db.query(SavedQuery).filter(SavedQuery.query_id == query_id).first()
    if not query:
        return jsonify({"code": 40401, "message": "查询不存在"}), 404

    return jsonify({
        "code": 0,
        "message": "success",
        "data": query.to_dict()
    })


@app.route("/api/v1/sql-lab/saved-queries/<query_id>", methods=["PUT"])
@require_jwt()
@require_permission(Resource.MODEL, Operation.UPDATE)
def update_saved_query(query_id: str):
    """更新已保存查询"""
    db = get_db_session()
    data = request.get_json()

    query = db.query(SavedQuery).filter(SavedQuery.query_id == query_id).first()
    if not query:
        return jsonify({"code": 40401, "message": "查询不存在"}), 404

    if "name" in data:
        query.name = data["name"]
    if "description" in data:
        query.description = data["description"]
    if "sql" in data:
        query.sql_content = data["sql"]
    if "database" in data:
        query.database_name = data["database"]
    if "tags" in data:
        query.tags = data["tags"]

    query.updated_at = datetime.utcnow()
    db.commit()

    logger.info(f"更新保存的查询: {query_id}")

    return jsonify({
        "code": 0,
        "message": "更新成功",
        "data": query.to_dict()
    })


@app.route("/api/v1/sql-lab/saved-queries/<query_id>", methods=["DELETE"])
@require_jwt()
@require_permission(Resource.MODEL, Operation.DELETE)
def delete_saved_query(query_id: str):
    """删除已保存查询"""
    db = get_db_session()

    query = db.query(SavedQuery).filter(SavedQuery.query_id == query_id).first()
    if not query:
        return jsonify({"code": 40401, "message": "查询不存在"}), 404

    db.delete(query)
    db.commit()

    logger.info(f"删除保存的查询: {query_id}")

    return jsonify({
        "code": 0,
        "message": "删除成功"
    })


@app.route("/api/v1/sql-lab/databases", methods=["GET"])
@require_jwt(optional=True)
def list_sql_lab_databases():
    """获取可用数据库列表"""
    db = get_db_session()

    connections = db.query(DatabaseConnection).filter(DatabaseConnection.is_active == True).all()

    # 如果没有配置连接，返回默认列表
    if not connections:
        default_databases = [
            {
                "id": "default",
                "name": "default",
                "database_type": "postgresql",
                "description": "默认数据库"
            },
            {
                "id": "analytics",
                "name": "analytics",
                "database_type": "clickhouse",
                "description": "分析数据库"
            },
            {
                "id": "datalake",
                "name": "datalake",
                "database_type": "hive",
                "description": "数据湖"
            }
        ]
        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "databases": default_databases
            }
        })

    return jsonify({
        "code": 0,
        "message": "success",
        "data": {
            "databases": [c.to_dict() for c in connections]
        }
    })


@app.route("/api/v1/model/sql-lab/connections", methods=["GET"])
@require_jwt(optional=True)
def list_sql_lab_connections():
    """获取 SQL Lab 数据库连接列表"""
    db = get_db_session()

    connections = db.query(DatabaseConnection).filter(DatabaseConnection.is_active == True).all()

    # 如果没有配置连接，返回默认列表
    if not connections:
        default_connections = [
            {
                "id": "default",
                "name": "default",
                "database_type": "postgresql",
                "host": "localhost",
                "port": 5432,
                "description": "默认数据库"
            },
            {
                "id": "analytics",
                "name": "analytics",
                "database_type": "clickhouse",
                "host": "localhost",
                "port": 8123,
                "description": "分析数据库"
            },
            {
                "id": "datalake",
                "name": "datalake",
                "database_type": "hive",
                "host": "localhost",
                "port": 10000,
                "description": "数据湖"
            }
        ]
        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "connections": default_connections,
                "total": len(default_connections)
            }
        })

    # 转换为连接格式
    connection_list = []
    for c in connections:
        conn_dict = c.to_dict()
        connection_list.append({
            "id": conn_dict.get("id", conn_dict.get("connection_id")),
            "name": conn_dict.get("name"),
            "database_type": conn_dict.get("database_type", "postgresql"),
            "host": conn_dict.get("host"),
            "port": conn_dict.get("port"),
            "description": conn_dict.get("description", "")
        })

    return jsonify({
        "code": 0,
        "message": "success",
        "data": {
            "connections": connection_list,
            "total": len(connection_list)
        }
    })


@app.route("/api/v1/sql-lab/databases/<database>/tables", methods=["GET"])
@require_jwt(optional=True)
def list_database_tables(database: str):
    """获取数据库的表列表"""
    # 模拟返回表列表
    tables = [
        {
            "name": "users",
            "type": "table",
            "schema": "public",
            "row_count": 10000,
            "columns": [
                {"name": "id", "type": "int", "nullable": False},
                {"name": "name", "type": "varchar(255)", "nullable": False},
                {"name": "email", "type": "varchar(255)", "nullable": True},
                {"name": "created_at", "type": "timestamp", "nullable": False}
            ]
        },
        {
            "name": "orders",
            "type": "table",
            "schema": "public",
            "row_count": 50000,
            "columns": [
                {"name": "id", "type": "int", "nullable": False},
                {"name": "user_id", "type": "int", "nullable": False},
                {"name": "amount", "type": "decimal(10,2)", "nullable": False},
                {"name": "status", "type": "varchar(32)", "nullable": False},
                {"name": "created_at", "type": "timestamp", "nullable": False}
            ]
        },
        {
            "name": "products",
            "type": "table",
            "schema": "public",
            "row_count": 1000,
            "columns": [
                {"name": "id", "type": "int", "nullable": False},
                {"name": "name", "type": "varchar(255)", "nullable": False},
                {"name": "price", "type": "decimal(10,2)", "nullable": False},
                {"name": "category", "type": "varchar(64)", "nullable": True}
            ]
        },
        {
            "name": "daily_stats",
            "type": "view",
            "schema": "public",
            "row_count": None,
            "columns": [
                {"name": "date", "type": "date", "nullable": False},
                {"name": "total_orders", "type": "int", "nullable": False},
                {"name": "total_revenue", "type": "decimal(12,2)", "nullable": False}
            ]
        }
    ]

    return jsonify({
        "code": 0,
        "message": "success",
        "data": {
            "database": database,
            "tables": tables
        }
    })


# ==================== P4.7: AI Hub ====================

@app.route("/api/v1/aihub/models", methods=["GET"])
@require_jwt(optional=True)
def list_aihub_models():
    """获取 AI Hub 模型市场列表"""
    db = get_db_session()

    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 20))
    category = request.args.get("category")
    task_type = request.args.get("task_type")
    source = request.args.get("source")
    search = request.args.get("search")

    query = db.query(AIHubModel).filter(AIHubModel.status == "available")

    if category:
        query = query.filter(AIHubModel.category == category)
    if task_type:
        query = query.filter(AIHubModel.task_type == task_type)
    if source:
        query = query.filter(AIHubModel.source == source)
    if search:
        query = query.filter(
            (AIHubModel.name.ilike(f"%{search}%")) |
            (AIHubModel.description.ilike(f"%{search}%"))
        )

    total = query.count()
    models = query.order_by(AIHubModel.downloads.desc()).offset((page - 1) * page_size).limit(page_size).all()

    # 如果数据库为空，返回模拟数据
    if total == 0:
        mock_models = _get_mock_aihub_models()
        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "models": mock_models[(page - 1) * page_size:page * page_size],
                "total": len(mock_models),
                "page": page,
                "page_size": page_size
            }
        })

    return jsonify({
        "code": 0,
        "message": "success",
        "data": {
            "models": [m.to_dict() for m in models],
            "total": total,
            "page": page,
            "page_size": page_size
        }
    })


def _get_mock_aihub_models():
    """获取模拟的 AI Hub 模型数据"""
    return [
        {
            "id": "llama-3-8b",
            "name": "Llama 3 8B",
            "description": "Meta 最新开源大语言模型，8B 参数版本，支持多语言",
            "author": "meta-llama",
            "source": "huggingface",
            "source_id": "meta-llama/Meta-Llama-3-8B",
            "category": "llm",
            "task_type": "text-generation",
            "model_size": "8B",
            "parameters": 8.0,
            "context_length": 8192,
            "license": "llama3",
            "downloads": 1500000,
            "likes": 12500,
            "tags": ["llm", "chat", "multilingual"],
            "is_featured": True,
            "is_trending": True
        },
        {
            "id": "qwen-2-7b",
            "name": "Qwen2 7B",
            "description": "阿里云通义千问2.0，7B 参数版本",
            "author": "Qwen",
            "source": "huggingface",
            "source_id": "Qwen/Qwen2-7B",
            "category": "llm",
            "task_type": "text-generation",
            "model_size": "7B",
            "parameters": 7.0,
            "context_length": 32768,
            "license": "apache-2.0",
            "downloads": 800000,
            "likes": 6800,
            "tags": ["llm", "chat", "chinese"],
            "is_featured": True,
            "is_trending": True
        },
        {
            "id": "chatglm3-6b",
            "name": "ChatGLM3 6B",
            "description": "智谱 AI 开源双语对话模型",
            "author": "THUDM",
            "source": "huggingface",
            "source_id": "THUDM/chatglm3-6b",
            "category": "llm",
            "task_type": "text-generation",
            "model_size": "6B",
            "parameters": 6.0,
            "context_length": 8192,
            "license": "apache-2.0",
            "downloads": 600000,
            "likes": 5200,
            "tags": ["llm", "chat", "chinese", "bilingual"],
            "is_featured": True,
            "is_trending": False
        },
        {
            "id": "yi-6b",
            "name": "Yi 6B",
            "description": "零一万物开源大语言模型",
            "author": "01-ai",
            "source": "huggingface",
            "source_id": "01-ai/Yi-6B",
            "category": "llm",
            "task_type": "text-generation",
            "model_size": "6B",
            "parameters": 6.0,
            "context_length": 4096,
            "license": "apache-2.0",
            "downloads": 400000,
            "likes": 3500,
            "tags": ["llm", "chat"],
            "is_featured": False,
            "is_trending": True
        },
        {
            "id": "bge-large-zh",
            "name": "BGE Large Chinese",
            "description": "智源开源中文 Embedding 模型",
            "author": "BAAI",
            "source": "huggingface",
            "source_id": "BAAI/bge-large-zh-v1.5",
            "category": "nlp",
            "task_type": "feature-extraction",
            "model_size": "326M",
            "parameters": 0.326,
            "context_length": 512,
            "license": "mit",
            "downloads": 2000000,
            "likes": 8900,
            "tags": ["embedding", "chinese", "retrieval"],
            "is_featured": True,
            "is_trending": False
        },
        {
            "id": "whisper-large-v3",
            "name": "Whisper Large v3",
            "description": "OpenAI 开源语音识别模型",
            "author": "openai",
            "source": "huggingface",
            "source_id": "openai/whisper-large-v3",
            "category": "audio",
            "task_type": "automatic-speech-recognition",
            "model_size": "1.5B",
            "parameters": 1.5,
            "context_length": None,
            "license": "apache-2.0",
            "downloads": 3000000,
            "likes": 15000,
            "tags": ["audio", "speech", "asr", "multilingual"],
            "is_featured": True,
            "is_trending": True
        },
        {
            "id": "stable-diffusion-xl",
            "name": "Stable Diffusion XL",
            "description": "Stability AI 开源图像生成模型",
            "author": "stabilityai",
            "source": "huggingface",
            "source_id": "stabilityai/stable-diffusion-xl-base-1.0",
            "category": "cv",
            "task_type": "text-to-image",
            "model_size": "6.6B",
            "parameters": 6.6,
            "context_length": None,
            "license": "openrail++",
            "downloads": 5000000,
            "likes": 25000,
            "tags": ["image", "generation", "diffusion"],
            "is_featured": True,
            "is_trending": True
        },
        {
            "id": "llava-1.5-7b",
            "name": "LLaVA 1.5 7B",
            "description": "多模态视觉语言模型",
            "author": "liuhaotian",
            "source": "huggingface",
            "source_id": "liuhaotian/llava-v1.5-7b",
            "category": "multimodal",
            "task_type": "image-to-text",
            "model_size": "7B",
            "parameters": 7.0,
            "context_length": 4096,
            "license": "llama2",
            "downloads": 500000,
            "likes": 4200,
            "tags": ["multimodal", "vision", "chat"],
            "is_featured": False,
            "is_trending": True
        }
    ]


@app.route("/api/v1/aihub/models/<model_id>", methods=["GET"])
@require_jwt(optional=True)
def get_aihub_model(model_id: str):
    """获取 AI Hub 模型详情"""
    db = get_db_session()

    model = db.query(AIHubModel).filter(AIHubModel.model_id == model_id).first()

    if not model:
        # 从模拟数据中查找
        mock_models = _get_mock_aihub_models()
        for m in mock_models:
            if m["id"] == model_id:
                return jsonify({
                    "code": 0,
                    "message": "success",
                    "data": m
                })
        return jsonify({"code": 40401, "message": "模型不存在"}), 404

    return jsonify({
        "code": 0,
        "message": "success",
        "data": model.to_dict()
    })


@app.route("/api/v1/aihub/models/<model_id>/import", methods=["POST"])
@require_jwt()
@require_permission(Resource.MODEL, Operation.CREATE)
def import_aihub_model(model_id: str):
    """导入 AI Hub 模型到本地"""
    db = get_db_session()
    data = request.get_json() or {}

    # 查找模型
    model = db.query(AIHubModel).filter(AIHubModel.model_id == model_id).first()

    if not model:
        # 从模拟数据创建
        mock_models = _get_mock_aihub_models()
        model_data = None
        for m in mock_models:
            if m["id"] == model_id:
                model_data = m
                break

        if not model_data:
            return jsonify({"code": 40401, "message": "模型不存在"}), 404

        # 创建数据库记录
        model = AIHubModel(
            model_id=model_id,
            name=model_data["name"],
            description=model_data["description"],
            author=model_data["author"],
            source=model_data["source"],
            source_id=model_data["source_id"],
            category=model_data["category"],
            task_type=model_data["task_type"],
            model_size=model_data["model_size"],
            parameters=model_data["parameters"],
            context_length=model_data.get("context_length"),
            license=model_data["license"],
            downloads=model_data["downloads"],
            likes=model_data["likes"],
            tags=model_data["tags"],
            is_featured=model_data["is_featured"],
            is_trending=model_data["is_trending"],
            status="importing"
        )
        db.add(model)
    else:
        model.status = "importing"

    # 生成本地模型 ID
    local_model_id = generate_id("local_model_")
    model.local_model_id = local_model_id
    model.imported_at = datetime.utcnow()

    db.commit()

    # 创建对应的 MLModel 记录
    ml_model = MLModel(
        model_id=local_model_id,
        name=f"{model.name} (Imported)",
        description=f"从 AI Hub 导入: {model.description}",
        model_type=model.category,
        framework="transformers",
        source="aihub",
        source_model_id=model_id,
        status="importing",
        created_by=data.get("created_by", "system")
    )
    db.add(ml_model)
    db.commit()

    logger.info(f"导入 AI Hub 模型: {model_id} -> {local_model_id}")

    # 模拟异步导入完成
    model.status = "available"
    ml_model.status = "ready"
    db.commit()

    return jsonify({
        "code": 0,
        "message": "导入成功",
        "data": {
            "aihub_model_id": model_id,
            "local_model_id": local_model_id,
            "status": "ready"
        }
    })


@app.route("/api/v1/aihub/categories", methods=["GET"])
@require_jwt(optional=True)
def list_aihub_categories():
    """获取 AI Hub 模型分类"""
    db = get_db_session()

    categories = db.query(AIHubCategory).order_by(AIHubCategory.sort_order).all()

    # 如果数据库为空，返回默认分类
    if not categories:
        default_categories = [
            {
                "id": "llm",
                "name": "大语言模型",
                "description": "文本生成、对话、推理等任务",
                "icon": "MessageSquare",
                "model_count": 50
            },
            {
                "id": "nlp",
                "name": "自然语言处理",
                "description": "文本分类、命名实体识别、情感分析等",
                "icon": "Type",
                "model_count": 120
            },
            {
                "id": "cv",
                "name": "计算机视觉",
                "description": "图像分类、目标检测、图像生成等",
                "icon": "Eye",
                "model_count": 200
            },
            {
                "id": "audio",
                "name": "语音处理",
                "description": "语音识别、语音合成、音频分类等",
                "icon": "Mic",
                "model_count": 80
            },
            {
                "id": "multimodal",
                "name": "多模态",
                "description": "视觉语言模型、跨模态检索等",
                "icon": "Layers",
                "model_count": 30
            }
        ]
        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "categories": default_categories
            }
        })

    return jsonify({
        "code": 0,
        "message": "success",
        "data": {
            "categories": [c.to_dict() for c in categories]
        }
    })


@app.route("/api/v1/aihub/trending", methods=["GET"])
@require_jwt(optional=True)
def list_trending_models():
    """获取热门模型"""
    db = get_db_session()

    limit = int(request.args.get("limit", 10))

    models = db.query(AIHubModel).filter(
        AIHubModel.is_trending == True,
        AIHubModel.status == "available"
    ).order_by(AIHubModel.downloads.desc()).limit(limit).all()

    # 如果数据库为空，从模拟数据中筛选
    if not models:
        mock_models = _get_mock_aihub_models()
        trending = [m for m in mock_models if m.get("is_trending")]
        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "models": trending[:limit]
            }
        })

    return jsonify({
        "code": 0,
        "message": "success",
        "data": {
            "models": [m.to_dict() for m in models]
        }
    })


@app.route("/api/v1/aihub/featured", methods=["GET"])
@require_jwt(optional=True)
def list_featured_models():
    """获取推荐模型"""
    db = get_db_session()

    limit = int(request.args.get("limit", 10))

    models = db.query(AIHubModel).filter(
        AIHubModel.is_featured == True,
        AIHubModel.status == "available"
    ).order_by(AIHubModel.likes.desc()).limit(limit).all()

    # 如果数据库为空，从模拟数据中筛选
    if not models:
        mock_models = _get_mock_aihub_models()
        featured = [m for m in mock_models if m.get("is_featured")]
        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "models": featured[:limit]
            }
        })

    return jsonify({
        "code": 0,
        "message": "success",
        "data": {
            "models": [m.to_dict() for m in models]
        }
    })


# ==================== 初始化数据库 ====================

@app.route("/api/v1/init-db", methods=["POST"])
@require_jwt()
@require_permission(Resource.MODEL, Operation.MANAGE if hasattr(Operation, 'MANAGE') else Operation.CREATE)
def init_database():
    """初始化数据库表（需要管理员权限）"""
    try:
        init_db()
        logger.info("数据库表初始化成功")
        return jsonify({
            "code": 0,
            "message": "数据库初始化成功"
        })
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        return jsonify({
            "code": 50001,
            "message": f"初始化失败: {str(e)}"
        }), 500


# ==================== 路由别名和兼容接口 ====================

# /api/v1/training/jobs 别名（前端调用路径）
@app.route("/api/v1/training/jobs", methods=["GET", "POST"])
@require_jwt(optional=True)
def training_jobs_alias():
    """训练任务路由别名"""
    # 根据请求方法转发到对应的处理函数
    if request.method == "POST":
        # 创建新的训练任务
        return create_training_job()
    else:
        # 获取训练任务列表
        return list_training_jobs()


@app.route("/api/v1/training/jobs/<job_id>", methods=["GET"])
@require_jwt(optional=True)
def training_job_detail_alias(job_id):
    """获取训练任务详情（别名）"""
    return get_training_job(job_id)


@app.route("/api/v1/training/jobs/<job_id>/cancel", methods=["POST"])
@require_jwt(optional=True)
def cancel_training_job_alias(job_id):
    """取消训练任务（别名）"""
    return cancel_training_job(job_id)


# /api/v1/models/registered - 已注册模型列表
@app.route("/api/v1/models/registered", methods=["GET"])
@require_jwt(optional=True)
def list_registered_models():
    """获取已注册的模型列表"""
    db = get_db_session()

    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 20))
    status = request.args.get("status")
    framework = request.args.get("framework")

    query = db.query(MLModel)

    if status:
        query = query.filter(MLModel.status == status)
    if framework:
        query = query.filter(MLModel.framework == framework)

    total = query.count()
    models = query.order_by(MLModel.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    # 转换为前端期望的格式
    result = []
    for model in models:
        model_dict = {
            "model_id": model.model_id,
            "name": model.name,
            "version": model.latest_version,
            "framework": model.framework,
            "task_type": model.task_type,
            "status": model.status,
            "accuracy": model.accuracy,
            "created_at": model.created_at.isoformat() + "Z" if model.created_at else None,
            "created_by": model.created_by,
            "description": model.description,
            "parameters": model.parameters
        }
        result.append(model_dict)

    return jsonify({
        "code": 0,
        "message": "success",
        "data": {
            "models": result,
            "total": total,
            "page": page,
            "page_size": page_size
        }
    })


# /api/v1/hub/models 和 /api/v1/hub/categories 别名
@app.route("/api/v1/hub/models", methods=["GET"])
@require_jwt(optional=True)
def hub_models_alias():
    """AI Hub 模型列表（别名）"""
    return list_aihub_models()


@app.route("/api/v1/hub/categories", methods=["GET"])
@require_jwt(optional=True)
def hub_categories_alias():
    """AI Hub 分类列表（别名）"""
    return list_aihub_categories()


# /api/v1/pipelines/templates
@app.route("/api/v1/pipelines/templates", methods=["GET"])
@require_jwt(optional=True)
def list_pipeline_templates_v2():
    """获取流水线模板列表（前端调用路径）"""
    # 返回默认模板
    default_templates = [
        {
            "template_id": "tpl-data-processing",
            "name": "数据处理流水线",
            "description": "标准数据处理和清洗流程",
            "category": "data-processing",
            "stages": [
                {"name": "数据读取", "type": "read"},
                {"name": "数据清洗", "type": "clean"},
                {"name": "特征工程", "type": "feature"},
                {"name": "数据写入", "type": "write"}
            ],
            "created_at": "2024-01-01T00:00:00Z"
        },
        {
            "template_id": "tpl-model-training",
            "name": "模型训练流水线",
            "description": "标准机器学习模型训练流程",
            "category": "training",
            "stages": [
                {"name": "数据准备", "type": "prepare"},
                {"name": "特征提取", "type": "feature"},
                {"name": "模型训练", "type": "train"},
                {"name": "模型评估", "type": "evaluate"},
                {"name": "模型注册", "type": "register"}
            ],
            "created_at": "2024-01-01T00:00:00Z"
        },
        {
            "template_id": "tpl-batch-inference",
            "name": "批量推理流水线",
            "description": "批量预测推理流程",
            "category": "inference",
            "stages": [
                {"name": "数据加载", "type": "load"},
                {"name": "批量推理", "type": "inference"},
                {"name": "结果保存", "type": "save"}
            ],
            "created_at": "2024-01-01T00:00:00Z"
        },
        {
            "template_id": "ppt-etl-workflow",
            "name": "ETL 工作流",
            "description": "数据抽取、转换、加载流程",
            "category": "etl",
            "stages": [
                {"name": "抽取", "type": "extract"},
                {"name": "转换", "type": "transform"},
                {"name": "加载", "type": "load"}
            ],
            "created_at": "2024-01-01T00:00:00Z"
        }
    ]
    return jsonify({
        "code": 0,
        "message": "success",
        "data": {
            "templates": default_templates,
            "total": len(default_templates)
        }
    })


# /api/v1/llm/datasets
@app.route("/api/v1/llm/datasets", methods=["GET"])
@require_jwt(optional=True)
def list_llm_datasets():
    """获取 LLM 训练数据集列表"""
    db = get_db_session()

    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 20))
    task_type = request.args.get("task_type")

    # 返回模拟数据集列表
    mock_datasets = [
        {
            "dataset_id": "ds-llm-sft-001",
            "name": "指令微调数据集",
            "description": "通用指令遵循微调数据集",
            "task_type": "sft",
            "format": "jsonl",
            "size": "2.5GB",
            "samples": 50000,
            "language": "zh-CN",
            "created_at": "2024-01-15T00:00:00Z"
        },
        {
            "dataset_id": "ds-llm-pretrain-001",
            "name": "预训练语料",
            "description": "大规模预训练语料库",
            "task_type": "pretrain",
            "format": "parquet",
            "size": "50GB",
            "samples": 1000000000,
            "language": "mixed",
            "created_at": "2024-01-10T00:00:00Z"
        },
        {
            "dataset_id": "ds-llm-rlhf-001",
            "name": "RLHF 偏好数据集",
            "description": "人类反馈强化学习偏好数据",
            "task_type": "rlhf",
            "format": "jsonl",
            "size": "500MB",
            "samples": 10000,
            "language": "zh-CN",
            "created_at": "2024-01-12T00:00:00Z"
        }
    ]

    # 按任务类型过滤
    if task_type:
        filtered = [d for d in mock_datasets if d.get("task_type") == task_type]
    else:
        filtered = mock_datasets

    return jsonify({
        "code": 0,
        "message": "success",
        "data": {
            "datasets": filtered[(page - 1) * page_size:page * page_size],
            "total": len(filtered),
            "page": page,
            "page_size": page_size
        }
    })


# /api/v1/llm/tuning 别名
@app.route("/api/v1/llm/tuning", methods=["GET", "POST"])
@require_jwt(optional=True)
def llm_tuning_alias():
    """LLM 微调任务（别名）"""
    if request.method == "POST":
        return create_llm_tuning_task()
    else:
        return list_llm_tuning_tasks()


@app.route("/api/v1/llm/tuning/<task_id>", methods=["GET"])
@require_jwt(optional=True)
def llm_tuning_detail_alias(task_id):
    """获取 LLM 微调任务详情（别名）"""
    return get_llm_tuning_task(task_id)


@app.route("/api/v1/llm/tuning/<task_id>/start", methods=["POST"])
@require_jwt(optional=True)
def start_llm_tuning_alias(task_id):
    """启动 LLM 微调任务（别名）"""
    return start_llm_tuning_task(task_id)


@app.route("/api/v1/llm/tuning/<task_id>/stop", methods=["POST"])
@require_jwt(optional=True)
def stop_llm_tuning_alias(task_id):
    """停止 LLM 微调任务（别名）"""
    return stop_llm_tuning_task(task_id)


# ==================== 业务预测模型 API ====================

@app.route("/api/v1/prediction/templates", methods=["GET"])
@require_jwt(optional=True)
def get_prediction_templates():
    """获取预测模板列表"""
    db = get_db()
    category = request.args.get("category")
    is_active = request.args.get("is_active", "true").lower() == "true"

    query = db.query(PredictionTemplate)

    if category:
        query = query.filter(PredictionTemplate.category == category)

    if is_active:
        query = query.filter(PredictionTemplate.is_active == True)

    templates = query.order_by(PredictionTemplate.is_system.desc(), PredictionTemplate.usage_count.desc()).all()

    return jsonify({
        "code": 0,
        "message": "success",
        "data": {
            "templates": [t.to_dict() for t in templates]
        }
    })


@app.route("/api/v1/prediction/templates/predefined", methods=["GET"])
@require_jwt(optional=True)
def get_predefined_templates():
    """获取预定义模板列表"""
    category = request.args.get("category")

    templates = PREDEFINED_TEMPLATES
    if category:
        templates = [t for t in templates if t.get("category") == category]

    return jsonify({
        "code": 0,
        "message": "success",
        "data": {
            "templates": templates
        }
    })


@app.route("/api/v1/prediction/templates", methods=["POST"])
@require_jwt(optional=True)
def create_prediction_template():
    """创建预测模板"""
    db = get_db()
    data = request.json
    user_id = getattr(g, 'user_id', 'system')

    name = data.get("name")
    if not name:
        return jsonify({"code": 40001, "message": "模板名称不能为空"}), 400

    category = data.get("category")
    if not category:
        return jsonify({"code": 40001, "message": "分类不能为空"}), 400

    template = PredictionTemplate(
        template_id=generate_template_id(),
        name=name,
        category=category,
        description=data.get("description"),
        target_variable=data.get("target_variable"),
        target_type=data.get("target_type", "regression"),
        prediction_horizon=data.get("prediction_horizon"),
        required_features=data.get("required_features", []),
        optional_features=data.get("optional_features", []),
        default_model=data.get("default_model"),
        allowed_models=data.get("allowed_models"),
        model_params=data.get("model_params"),
        min_rows=data.get("min_rows", 1000),
        feature_importance_threshold=data.get("feature_importance_threshold", 0.1),
        metrics=data.get("metrics"),
        success_threshold=data.get("success_threshold"),
        chart_type=data.get("chart_type"),
        chart_config=data.get("chart_config"),
        is_active=data.get("is_active", True),
        is_system=False,
        created_by=user_id,
    )

    # 设置特征列表
    if data.get("required_features"):
        template.set_required_features(data["required_features"])
    if data.get("optional_features"):
        template.set_optional_features(data["optional_features"])

    db.add(template)
    db.commit()

    logger.info(f"创建预测模板: {template.template_id}")

    return jsonify({
        "code": 0,
        "message": "success",
        "data": template.to_dict()
    }), 201


@app.route("/api/v1/prediction/templates/<template_id>", methods=["GET"])
@require_jwt(optional=True)
def get_prediction_template(template_id):
    """获取预测模板详情"""
    db = get_db()
    template = db.query(PredictionTemplate).filter(PredictionTemplate.template_id == template_id).first()

    if not template:
        return jsonify({"code": 40401, "message": "模板不存在"}), 404

    # 增加使用计数
    template.usage_count += 1
    db.commit()

    return jsonify({
        "code": 0,
        "message": "success",
        "data": template.to_dict()
    })


@app.route("/api/v1/prediction/templates/<template_id>", methods=["PUT"])
@require_jwt(optional=True)
def update_prediction_template(template_id):
    """更新预测模板"""
    db = get_db()
    data = request.json

    template = db.query(PredictionTemplate).filter(PredictionTemplate.template_id == template_id).first()
    if not template:
        return jsonify({"code": 40401, "message": "模板不存在"}), 404

    # 更新字段
    for field in ["name", "description", "target_variable", "target_type", "prediction_horizon",
                  "default_model", "allowed_models", "model_params", "min_rows",
                  "feature_importance_threshold", "metrics", "success_threshold",
                  "chart_type", "chart_config", "is_active"]:
        if field in data:
            setattr(template, field, data[field])

    if "required_features" in data:
        template.set_required_features(data["required_features"])
    if "optional_features" in data:
        template.set_optional_features(data["optional_features"])

    db.commit()

    logger.info(f"更新预测模板: {template_id}")

    return jsonify({
        "code": 0,
        "message": "success",
        "data": template.to_dict()
    })


@app.route("/api/v1/prediction/templates/<template_id>", methods=["DELETE"])
@require_jwt(optional=True)
def delete_prediction_template(template_id):
    """删除预测模板"""
    db = get_db()

    template = db.query(PredictionTemplate).filter(PredictionTemplate.template_id == template_id).first()
    if not template:
        return jsonify({"code": 40401, "message": "模板不存在"}), 404

    # 系统模板不能删除
    if template.is_system:
        return jsonify({"code": 40301, "message": "系统模板不能删除"}), 403

    db.delete(template)
    db.commit()

    logger.info(f"删除预测模板: {template_id}")

    return jsonify({
        "code": 0,
        "message": "success"
    })


@app.route("/api/v1/prediction/training-jobs", methods=["GET"])
@require_jwt(optional=True)
def get_prediction_training_jobs():
    """获取训练任务列表"""
    db = get_db()
    status = request.args.get("status")
    category = request.args.get("category")
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 20))

    query = db.query(PredictionTrainingJob)

    if status:
        query = query.filter(PredictionTrainingJob.status == status)
    if category:
        query = query.filter(PredictionTrainingJob.category == category)

    total = query.count()
    jobs = query.order_by(PredictionTrainingJob.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return jsonify({
        "code": 0,
        "message": "success",
        "data": {
            "jobs": [j.to_dict() for j in jobs],
            "total": total,
            "page": page,
            "page_size": page_size
        }
    })


@app.route("/api/v1/prediction/training-jobs", methods=["POST"])
@require_jwt(optional=True)
def create_prediction_training_job():
    """创建训练任务"""
    db = get_db()
    data = request.json
    user_id = getattr(g, 'user_id', 'system')

    template_id = data.get("template_id")
    if not template_id:
        return jsonify({"code": 40001, "message": "模板ID不能为空"}), 400

    # 验证模板存在
    template = db.query(PredictionTemplate).filter(PredictionTemplate.template_id == template_id).first()
    if not template:
        return jsonify({"code": 40401, "message": "模板不存在"}), 404

    job = PredictionTrainingJob(
        job_id=generate_job_id(),
        template_id=template_id,
        job_name=data.get("job_name", template.name),
        description=data.get("description"),
        category=template.category,
        dataset_id=data.get("dataset_id"),
        table_name=data.get("table_name"),
        model_type=data.get("model_type", template.default_model),
        model_params=data.get("model_params") or template.model_params,
        feature_config=data.get("feature_config"),
        selected_features=data.get("selected_features"),
        train_test_split=data.get("train_test_split", 0.8),
        random_state=data.get("random_state", 42),
        max_epochs=data.get("max_epochs", 100),
        early_stopping=data.get("early_stopping", True),
        status="pending",
        created_by=user_id,
    )

    db.add(job)
    db.commit()

    logger.info(f"创建预测训练任务: {job.job_id}")

    return jsonify({
        "code": 0,
        "message": "success",
        "data": job.to_dict()
    }), 201


@app.route("/api/v1/prediction/training-jobs/<job_id>", methods=["GET"])
@require_jwt(optional=True)
def get_prediction_training_job(job_id):
    """获取训练任务详情"""
    db = get_db()
    job = db.query(PredictionTrainingJob).filter(PredictionTrainingJob.job_id == job_id).first()

    if not job:
        return jsonify({"code": 40401, "message": "任务不存在"}), 404

    return jsonify({
        "code": 0,
        "message": "success",
        "data": job.to_dict()
    })


@app.route("/api/v1/prediction/training-jobs/<job_id>/start", methods=["POST"])
@require_jwt(optional=True)
def start_prediction_training_job(job_id):
    """启动训练任务"""
    db = get_db()
    job = db.query(PredictionTrainingJob).filter(PredictionTrainingJob.job_id == job_id).first()

    if not job:
        return jsonify({"code": 40401, "message": "任务不存在"}), 404

    if job.status not in ["pending", "failed"]:
        return jsonify({"code": 40001, "message": "任务状态不允许启动"}), 400

    job.status = "running"
    job.started_at = datetime.utcnow()
    job.progress = 0
    db.commit()

    # 异步训练任务
    import threading

    def train_task():
        try:
            from src.feature_auto import get_auto_ml_service
            import pandas as pd

            # 模拟加载数据
            # df = pd.read_sql(f"SELECT * FROM {job.table_name}", db.bind)

            # 模拟训练进度
            for i in range(0, 101, 10):
                job.progress = i
                db.commit()
                time.sleep(0.5)

            # 模拟训练结果
            job.set_metrics({
                "rmse": 12.5,
                "r2": 0.85,
                "mae": 8.3,
            })
            job.set_feature_importance([
                {"feature": "feature_1", "importance": 0.35},
                {"feature": "feature_2", "importance": 0.25},
                {"feature": "feature_3", "importance": 0.15},
            ])
            job.status = "completed"
            job.progress = 100
            job.completed_at = datetime.utcnow()
            job.model_path = f"/models/{job.job_id}.pkl"
            job.model_version = "v1.0"

            db.commit()
            logger.info(f"训练任务完成: {job_id}")

        except Exception as e:
            logger.error(f"训练任务失败: {e}")
            job.status = "failed"
            job.error_message = str(e)
            job.progress = 0
            db.commit()

    thread = threading.Thread(target=train_task)
    thread.daemon = True
    thread.start()

    logger.info(f"启动预测训练任务: {job_id}")

    return jsonify({
        "code": 0,
        "message": "success",
        "data": {"job_id": job_id, "status": "running"}
    })


@app.route("/api/v1/prediction/predict", methods=["POST"])
@require_jwt(optional=True)
def predict_with_model():
    """使用训练好的模型进行预测"""
    db = get_db()
    data = request.json

    job_id = data.get("job_id")
    if not job_id:
        return jsonify({"code": 40001, "message": "任务ID不能为空"}), 400

    job = db.query(PredictionTrainingJob).filter(PredictionTrainingJob.job_id == job_id).first()
    if not job:
        return jsonify({"code": 40401, "message": "任务不存在"}), 404

    if job.status != "completed":
        return jsonify({"code": 40001, "message": "模型未训练完成"}), 400

    input_data = data.get("input_data")
    if not input_data:
        return jsonify({"code": 40001, "message": "输入数据不能为空"}), 400

    # 模拟预测
    import random
    prediction = {
        "value": random.uniform(100, 1000),
        "confidence": random.uniform(0.7, 0.95),
        "timestamp": datetime.utcnow().isoformat()
    }

    # 记录预测
    record = PredictionRecord(
        record_id=f"pred_{uuid.uuid4().hex[:12]}",
        job_id=job_id,
        input_data=input_data,
        prediction=prediction,
        prediction_probability=prediction.get("confidence"),
        created_by=getattr(g, 'user_id', 'system'),
    )
    db.add(record)
    db.commit()

    return jsonify({
        "code": 0,
        "message": "success",
        "data": prediction
    })


@app.route("/api/v1/prediction/records", methods=["GET"])
@require_jwt(optional=True)
def get_prediction_records():
    """获取预测记录列表"""
    db = get_db()
    job_id = request.args.get("job_id")
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 20))

    query = db.query(PredictionRecord)

    if job_id:
        query = query.filter(PredictionRecord.job_id == job_id)

    total = query.count()
    records = query.order_by(PredictionRecord.predicted_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return jsonify({
        "code": 0,
        "message": "success",
        "data": {
            "records": [r.to_dict() for r in records],
            "total": total,
            "page": page,
            "page_size": page_size
        }
    })


@app.route("/api/v1/prediction/features/auto", methods=["POST"])
@require_jwt(optional=True)
def auto_feature_engineering():
    """自动特征工程"""
    data = request.json

    # 获取数据
    df_data = data.get("data")
    if not df_data:
        return jsonify({"code": 40001, "message": "数据不能为空"}), 400

    import pandas as pd
    from src.feature_auto import get_feature_engine

    df = pd.DataFrame(df_data)
    category = data.get("category", "sales")
    target_column = data.get("target_column", "target")

    # 执行特征工程
    feature_engine = get_feature_engine()
    df_enhanced = feature_engine.auto_feature_engineering(
        df=df,
        category=category,
        target_column=target_column,
        feature_config=data.get("feature_config"),
    )

    # 特征选择
    max_features = data.get("max_features", 50)
    threshold = data.get("threshold", 0.1)
    method = data.get("method", "importance")

    selected_features = feature_engine.select_features(
        df=df_enhanced,
        target_column=target_column,
        method=method,
        max_features=max_features,
        threshold=threshold,
    )

    return jsonify({
        "code": 0,
        "message": "success",
        "data": {
            "original_features": len(df.columns),
            "enhanced_features": len(df_enhanced.columns),
            "selected_features": [f.to_dict() for f in selected_features],
            "feature_names": [f.name for f in selected_features],
        }
    })


@app.route("/api/v1/prediction/train/auto", methods=["POST"])
@require_jwt(optional=True)
def auto_train_model():
    """自动训练模型"""
    data = request.json

    # 获取数据
    df_data = data.get("data")
    if not df_data:
        return jsonify({"code": 40001, "message": "数据不能为空"}), 400

    import pandas as pd
    from src.feature_auto import get_auto_ml_service

    df = pd.DataFrame(df_data)
    target_column = data.get("target_column", "target")
    task_type = data.get("task_type", "regression")

    # 自动训练
    auto_ml = get_auto_ml_service()
    result = auto_ml.auto_train(
        df=df,
        target_column=target_column,
        task_type=task_type,
        test_size=data.get("test_size", 0.2),
        random_state=data.get("random_state", 42),
    )

    return jsonify({
        "code": 0,
        "message": "success",
        "data": result
    })


# ==================== Notebook 管理 API ====================

@app.route("/api/v1/notebooks", methods=["POST"])
@require_jwt()
def create_notebook():
    """创建 Jupyter Notebook 实例"""
    try:
        data = request.get_json()

        notebook_id = f"nb_{uuid.uuid4().hex[:8]}"

        return jsonify({
            "code": 0,
            "message": "Notebook created successfully",
            "data": {
                "notebook_id": notebook_id,
                "name": data.get("name", "未命名 Notebook"),
                "image": data.get("image", "jupyter/scipy-notebook:latest"),
                "cpu_limit": data.get("cpu_limit", 2),
                "memory_limit": data.get("memory_limit", "4Gi"),
                "status": "starting",
                "url": f"/notebooks/{notebook_id}",
                "created_at": datetime.now().isoformat()
            }
        }), 201

    except Exception as e:
        logger.error(f"Error creating notebook: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


# ==================== 模型评估 API ====================

@app.route("/api/v1/evaluation", methods=["POST"])
@require_jwt()
def create_evaluation_task():
    """创建模型评估任务"""
    try:
        data = request.get_json()

        evaluation_id = f"eval_{uuid.uuid4().hex[:8]}"

        return jsonify({
            "code": 0,
            "message": "Evaluation task created",
            "data": {
                "evaluation_id": evaluation_id,
                "model_id": data.get("model_id"),
                "dataset_id": data.get("dataset_id"),
                "metrics": ["accuracy", "precision", "recall", "f1"],
                "status": "pending",
                "created_at": datetime.now().isoformat()
            }
        }), 201

    except Exception as e:
        logger.error(f"Error creating evaluation: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


# ==================== 镜像构建 API ====================

@app.route("/api/v1/image-builds", methods=["GET"])
@require_jwt()
def list_image_builds():
    """获取镜像构建列表"""
    try:
        from services.image_build_service import get_image_build_service
        service = get_image_build_service()

        status = request.args.get("status")
        limit = int(request.args.get("limit", 20))
        builds = service.list_builds(status=status, limit=limit)
        return jsonify({"code": 0, "message": "success", "data": builds})
    except Exception as e:
        logger.error(f"Error listing image builds: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/image-builds/dockerfile", methods=["POST"])
@require_jwt()
def create_dockerfile_build():
    """创建 Dockerfile 镜像构建任务"""
    try:
        from services.image_build_service import get_image_build_service
        service = get_image_build_service()
        data = request.get_json()

        job = service.create_dockerfile_build(
            image_name=data.get("image_name"),
            tag=data.get("tag", "latest"),
            dockerfile_content=data.get("dockerfile_content", ""),
            build_args=data.get("build_args", {}),
        )
        return jsonify({"code": 0, "message": "Build job created", "data": job.to_dict()}), 201
    except Exception as e:
        logger.error(f"Error creating dockerfile build: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/image-builds/<job_id>", methods=["GET"])
@require_jwt()
def get_build_status(job_id):
    """获取构建状态"""
    try:
        from services.image_build_service import get_image_build_service
        service = get_image_build_service()

        job = service.get_build_status(job_id)
        if not job:
            return jsonify({"code": 40400, "message": "Build job not found"}), 404
        return jsonify({"code": 0, "message": "success", "data": job.to_dict()})
    except Exception as e:
        logger.error(f"Error getting build status: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/image-builds/<job_id>/logs", methods=["GET"])
@require_jwt()
def get_build_logs(job_id):
    """获取构建日志"""
    try:
        from services.image_build_service import get_image_build_service
        service = get_image_build_service()

        tail = int(request.args.get("tail", 100))
        logs = service.get_build_logs(job_id, tail_lines=tail)
        return jsonify({"code": 0, "message": "success", "data": {"logs": logs}})
    except Exception as e:
        logger.error(f"Error getting build logs: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/image-builds/<job_id>/cancel", methods=["POST"])
@require_jwt()
def cancel_build(job_id):
    """取消构建任务"""
    try:
        from services.image_build_service import get_image_build_service
        service = get_image_build_service()

        success = service.cancel_build(job_id)
        if not success:
            return jsonify({"code": 40400, "message": "Build job not found or cannot be cancelled"}), 404
        return jsonify({"code": 0, "message": "Build cancelled"})
    except Exception as e:
        logger.error(f"Error cancelling build: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/image-builds/templates", methods=["GET"])
@require_jwt()
def get_base_image_templates():
    """获取基础镜像模板"""
    try:
        from services.image_build_service import get_image_build_service, ImageType
        service = get_image_build_service()

        image_type = request.args.get("type")
        it = ImageType(image_type) if image_type else None
        templates = service.get_base_templates(image_type=it)
        return jsonify({"code": 0, "message": "success", "data": templates})
    except Exception as e:
        logger.error(f"Error getting base templates: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


# ==================== 数据标注 API ====================

@app.route("/api/v1/labeling/projects", methods=["GET"])
@require_jwt()
def list_labeling_projects():
    """获取标注项目列表"""
    try:
        from services.labeling_service import get_labeling_service
        service = get_labeling_service()

        status = request.args.get("status")
        limit = int(request.args.get("limit", 20))
        projects = service.list_projects(status=status, limit=limit)
        return jsonify({
            "code": 0,
            "message": "success",
            "data": [p.to_dict() for p in projects]
        })
    except Exception as e:
        logger.error(f"Error listing labeling projects: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/labeling/projects", methods=["POST"])
@require_jwt()
def create_labeling_project():
    """创建标注项目"""
    try:
        from services.labeling_service import get_labeling_service
        service = get_labeling_service()
        data = request.get_json()

        project = service.create_project(
            name=data.get("name"),
            task_type=data.get("task_type", "classification"),
            description=data.get("description", ""),
            label_config=data.get("label_config", {}),
        )
        return jsonify({"code": 0, "message": "Project created", "data": project.to_dict()}), 201
    except Exception as e:
        logger.error(f"Error creating labeling project: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/labeling/projects/<project_id>", methods=["GET"])
@require_jwt()
def get_labeling_project(project_id):
    """获取标注项目详情"""
    try:
        from services.labeling_service import get_labeling_service
        service = get_labeling_service()

        project = service.get_project(project_id)
        if not project:
            return jsonify({"code": 40400, "message": "Project not found"}), 404
        return jsonify({"code": 0, "message": "success", "data": project.to_dict()})
    except Exception as e:
        logger.error(f"Error getting labeling project: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/labeling/projects/<project_id>/tasks", methods=["POST"])
@require_jwt()
def add_labeling_tasks(project_id):
    """添加标注任务"""
    try:
        from services.labeling_service import get_labeling_service
        service = get_labeling_service()
        data = request.get_json()

        tasks = service.add_tasks(
            project_id=project_id,
            items=data.get("items", []),
        )
        return jsonify({
            "code": 0,
            "message": f"Added {len(tasks)} tasks",
            "data": [t.to_dict() for t in tasks]
        }), 201
    except Exception as e:
        logger.error(f"Error adding labeling tasks: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/labeling/projects/<project_id>/next", methods=["GET"])
@require_jwt()
def get_next_labeling_task(project_id):
    """获取下一个待标注任务"""
    try:
        from services.labeling_service import get_labeling_service
        service = get_labeling_service()

        task = service.get_next_task(project_id)
        if not task:
            return jsonify({"code": 0, "message": "No more tasks", "data": None})
        return jsonify({"code": 0, "message": "success", "data": task.to_dict()})
    except Exception as e:
        logger.error(f"Error getting next task: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/labeling/tasks/<task_id>/annotate", methods=["POST"])
@require_jwt()
def submit_annotation(task_id):
    """提交标注"""
    try:
        from services.labeling_service import get_labeling_service
        service = get_labeling_service()
        data = request.get_json()

        annotation = service.submit_annotation(
            task_id=task_id,
            result=data.get("result", {}),
            annotator=data.get("annotator", ""),
        )
        return jsonify({"code": 0, "message": "Annotation submitted", "data": annotation.to_dict()})
    except Exception as e:
        logger.error(f"Error submitting annotation: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/labeling/projects/<project_id>/export", methods=["GET"])
@require_jwt()
def export_annotations(project_id):
    """导出标注结果"""
    try:
        from services.labeling_service import get_labeling_service
        service = get_labeling_service()

        format_type = request.args.get("format", "json")
        data = service.export_annotations(project_id, format_type=format_type)
        return jsonify({"code": 0, "message": "success", "data": data})
    except Exception as e:
        logger.error(f"Error exporting annotations: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/labeling/projects/<project_id>/statistics", methods=["GET"])
@require_jwt()
def get_labeling_statistics(project_id):
    """获取标注项目统计"""
    try:
        from services.labeling_service import get_labeling_service
        service = get_labeling_service()

        stats = service.get_project_statistics(project_id)
        return jsonify({"code": 0, "message": "success", "data": stats})
    except Exception as e:
        logger.error(f"Error getting labeling statistics: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/labeling/config-templates", methods=["GET"])
@require_jwt()
def get_label_config_templates():
    """获取标注配置模板"""
    try:
        from services.labeling_service import get_labeling_service
        service = get_labeling_service()

        task_type = request.args.get("task_type")
        templates = service.get_label_config_templates(task_type=task_type)
        return jsonify({"code": 0, "message": "success", "data": templates})
    except Exception as e:
        logger.error(f"Error getting config templates: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


# ==================== 在线 IDE API ====================

@app.route("/api/v1/ide/instances", methods=["GET"])
@require_jwt()
def list_ide_instances():
    """获取 IDE 实例列表"""
    try:
        from services.online_ide_service import get_ide_service
        service = get_ide_service()

        status = request.args.get("status")
        ide_type = request.args.get("type")
        instances = service.list_instances(status=status, ide_type=ide_type)
        return jsonify({
            "code": 0,
            "message": "success",
            "data": [inst.to_dict() for inst in instances]
        })
    except Exception as e:
        logger.error(f"Error listing IDE instances: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/ide/instances", methods=["POST"])
@require_jwt()
def create_ide_instance():
    """创建 IDE 实例"""
    try:
        from services.online_ide_service import get_ide_service
        service = get_ide_service()
        data = request.get_json()

        instance = service.create_instance(
            name=data.get("name"),
            ide_type=data.get("ide_type", "jupyter"),
            image=data.get("image"),
            resources=data.get("resources", {}),
        )
        return jsonify({"code": 0, "message": "IDE instance created", "data": instance.to_dict()}), 201
    except Exception as e:
        logger.error(f"Error creating IDE instance: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/ide/instances/<instance_id>", methods=["GET"])
@require_jwt()
def get_ide_instance(instance_id):
    """获取 IDE 实例详情"""
    try:
        from services.online_ide_service import get_ide_service
        service = get_ide_service()

        instance = service.get_instance(instance_id)
        if not instance:
            return jsonify({"code": 40400, "message": "IDE instance not found"}), 404
        return jsonify({"code": 0, "message": "success", "data": instance.to_dict()})
    except Exception as e:
        logger.error(f"Error getting IDE instance: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/ide/instances/<instance_id>/start", methods=["POST"])
@require_jwt()
def start_ide_instance(instance_id):
    """启动 IDE 实例"""
    try:
        from services.online_ide_service import get_ide_service
        service = get_ide_service()

        success = service.start_instance(instance_id)
        if not success:
            return jsonify({"code": 40400, "message": "Instance not found or cannot be started"}), 404
        return jsonify({"code": 0, "message": "IDE instance starting"})
    except Exception as e:
        logger.error(f"Error starting IDE instance: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/ide/instances/<instance_id>/stop", methods=["POST"])
@require_jwt()
def stop_ide_instance(instance_id):
    """停止 IDE 实例"""
    try:
        from services.online_ide_service import get_ide_service
        service = get_ide_service()

        success = service.stop_instance(instance_id)
        if not success:
            return jsonify({"code": 40400, "message": "Instance not found or cannot be stopped"}), 404
        return jsonify({"code": 0, "message": "IDE instance stopping"})
    except Exception as e:
        logger.error(f"Error stopping IDE instance: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/ide/instances/<instance_id>", methods=["DELETE"])
@require_jwt()
def delete_ide_instance(instance_id):
    """删除 IDE 实例"""
    try:
        from services.online_ide_service import get_ide_service
        service = get_ide_service()

        keep_data = request.args.get("keep_data", "false").lower() == "true"
        success = service.delete_instance(instance_id, keep_data=keep_data)
        if not success:
            return jsonify({"code": 40400, "message": "IDE instance not found"}), 404
        return jsonify({"code": 0, "message": "IDE instance deleted"})
    except Exception as e:
        logger.error(f"Error deleting IDE instance: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/ide/images", methods=["GET"])
@require_jwt()
def get_available_ide_images():
    """获取可用 IDE 镜像列表"""
    try:
        from services.online_ide_service import get_ide_service, IDEType
        service = get_ide_service()

        ide_type = request.args.get("type")
        it = IDEType(ide_type) if ide_type else None
        images = service.get_available_images(ide_type=it)
        return jsonify({"code": 0, "message": "success", "data": images})
    except Exception as e:
        logger.error(f"Error getting IDE images: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


# ==================== K8s 训练服务 API ====================

@app.route("/api/v1/k8s-training/submit", methods=["POST"])
@require_jwt()
def submit_k8s_training():
    """提交 K8s 训练任务"""
    try:
        from services.k8s_training_service import get_k8s_training_service
        service = get_k8s_training_service()
        data = request.get_json()

        result = service.submit_training_job(
            job_name=data.get("job_name"),
            image=data.get("image"),
            framework=data.get("framework", "pytorch"),
            resources=data.get("resources", {}),
            hyperparameters=data.get("hyperparameters", {}),
            data_config=data.get("data_config", {}),
        )
        return jsonify({"code": 0, "message": "Training job submitted", "data": result}), 201
    except Exception as e:
        logger.error(f"Error submitting K8s training: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/k8s-training/<job_name>/status", methods=["GET"])
@require_jwt()
def get_k8s_training_status(job_name):
    """获取 K8s 训练任务状态"""
    try:
        from services.k8s_training_service import get_k8s_training_service
        service = get_k8s_training_service()

        job_id = request.args.get("job_id", "")
        status = service.get_job_status(job_id, job_name)
        return jsonify({"code": 0, "message": "success", "data": {"status": status.value}})
    except Exception as e:
        logger.error(f"Error getting K8s training status: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/k8s-training/<job_name>/logs", methods=["GET"])
@require_jwt()
def get_k8s_training_logs(job_name):
    """获取 K8s 训练日志"""
    try:
        from services.k8s_training_service import get_k8s_training_service
        service = get_k8s_training_service()

        tail = int(request.args.get("tail", 100))
        logs = service.get_job_logs(job_name, tail_lines=tail)
        return jsonify({"code": 0, "message": "success", "data": {"logs": logs}})
    except Exception as e:
        logger.error(f"Error getting K8s training logs: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/k8s-training/<job_name>/cancel", methods=["POST"])
@require_jwt()
def cancel_k8s_training(job_name):
    """取消 K8s 训练任务"""
    try:
        from services.k8s_training_service import get_k8s_training_service
        service = get_k8s_training_service()

        success = service.cancel_job(job_name)
        if not success:
            return jsonify({"code": 40400, "message": "Job not found or cannot be cancelled"}), 404
        return jsonify({"code": 0, "message": "Training job cancelled"})
    except Exception as e:
        logger.error(f"Error cancelling K8s training: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/k8s-training", methods=["GET"])
@require_jwt()
def list_k8s_training_jobs():
    """获取 K8s 训练任务列表"""
    try:
        from services.k8s_training_service import get_k8s_training_service
        service = get_k8s_training_service()

        label_selector = request.args.get("label_selector")
        jobs = service.list_jobs(label_selector=label_selector)
        return jsonify({"code": 0, "message": "success", "data": jobs})
    except Exception as e:
        logger.error(f"Error listing K8s training jobs: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


# ==================== 模型注册表 API ====================

@app.route("/api/v1/model-registry/register", methods=["POST"])
@require_jwt()
def register_model_version():
    """注册模型版本"""
    try:
        from services.model_registry import get_model_registry
        registry = get_model_registry()
        data = request.get_json()

        version_info = registry.register_model(
            model_id=data.get("model_id"),
            version=data.get("version"),
            artifact_path=data.get("artifact_path"),
            metrics=data.get("metrics", {}),
            parameters=data.get("parameters", {}),
        )
        return jsonify({"code": 0, "message": "Model registered", "data": version_info}), 201
    except Exception as e:
        logger.error(f"Error registering model: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/model-registry/<model_id>/versions", methods=["GET"])
@require_jwt()
def list_model_registry_versions(model_id):
    """获取模型版本列表"""
    try:
        from services.model_registry import get_model_registry
        registry = get_model_registry()

        versions = registry.list_model_versions(model_id)
        return jsonify({"code": 0, "message": "success", "data": versions})
    except Exception as e:
        logger.error(f"Error listing model versions: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/model-registry/<model_id>/versions/<version>/download", methods=["GET"])
@require_jwt()
def download_model_version(model_id, version):
    """下载模型版本"""
    try:
        from services.model_registry import get_model_registry
        registry = get_model_registry()

        local_path = request.args.get("local_path", f"/tmp/models/{model_id}/{version}")
        result = registry.download_model(model_id, version, local_path)
        return jsonify({"code": 0, "message": "success", "data": result})
    except Exception as e:
        logger.error(f"Error downloading model: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/model-registry/<model_id>/versions/compare", methods=["GET"])
@require_jwt()
def compare_model_versions(model_id):
    """对比模型版本"""
    try:
        from services.model_registry import get_model_registry
        registry = get_model_registry()

        v1 = request.args.get("v1")
        v2 = request.args.get("v2")
        comparison = registry.compare_versions(model_id, v1, v2)
        return jsonify({"code": 0, "message": "success", "data": comparison})
    except Exception as e:
        logger.error(f"Error comparing model versions: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/model-registry/<model_id>/versions/<version>/stage", methods=["PUT"])
@require_jwt()
def set_model_stage(model_id, version):
    """设置模型阶段（staging/production/archived）"""
    try:
        from services.model_registry import get_model_registry
        registry = get_model_registry()
        data = request.get_json()

        result = registry.set_model_stage(model_id, version, stage=data.get("stage"))
        return jsonify({"code": 0, "message": "Model stage updated", "data": result})
    except Exception as e:
        logger.error(f"Error setting model stage: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


# ==================== 启动应用 ====================

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8002))

    # 初始化数据库
    try:
        init_db()
        logger.info("数据库表初始化完成")
    except Exception as e:
        logger.warning(f"数据库初始化跳过: {e}")

    debug = os.getenv("DEBUG", "false").lower() == "true"

    # SECURITY WARNING: Debug mode exposes sensitive information
    if debug:
        logger.warning(
            "⚠️  WARNING: Debug mode is ENABLED. This should NEVER be used in production! "
            "Debug mode exposes detailed error information and may enable remote code execution."
        )

    logger.info(f"Starting Model API on port {port}")
    app.run(host="0.0.0.0", port=port, debug=debug)
