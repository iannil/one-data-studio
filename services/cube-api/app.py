"""
Cube API - MLOps 平台服务
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
from typing import Optional, List, Dict, Any
from datetime import datetime
from functools import wraps

from flask import Flask, jsonify, request, g
from flask_cors import CORS

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
    AIHubModel, AIHubCategory
)
from services.huggingface import get_huggingface_service, HuggingFaceService

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
        "service": "cube-api",
        "version": "1.0.0",
        "huggingface_configured": hf_service.token is not None,
        "timestamp": datetime.now().isoformat()
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
    deployment.endpoint = f"http://cube-api.one-data.svc.cluster.local:8000/api/v1/predict/{deployment.deployment_id}"
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
        # Real inference - to be implemented with actual model serving
        # Options:
        # 1. Call vLLM/TGI serving endpoint
        # 2. Load model directly using transformers
        # 3. Use external inference API
        logger.error(
            f"Real model inference requested but not implemented for deployment {deployment_id}. "
            "Configure model serving endpoint or enable mock mode."
        )
        return jsonify({
            "code": 50010,
            "message": "Model inference not configured. Contact administrator."
        }), 503

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
    gpu_stats = db.query(GPUDevice.status, db.func.count(GPUDevice.id)).group_by(GPUDevice.status).all()
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

    logger.info(f"Starting Cube API on port {port}")
    app.run(host="0.0.0.0", port=port, debug=debug)
