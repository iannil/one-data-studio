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

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import (
    SessionLocal, init_db,
    MLModel, ModelVersion, ModelDeployment,
    TrainingJob, BatchPredictionJob
)
from services.huggingface import get_huggingface_service, HuggingFaceService

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
CORS(app, resources={
    r"/*": {
        "origins": os.getenv("CORS_ORIGINS", "*").split(","),
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
def list_models():
    """列出所有模型"""
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
def create_model():
    """创建模型"""
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
def get_model(model_id: str):
    """获取模型详情"""
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
def update_model(model_id: str):
    """更新模型"""
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
def delete_model(model_id: str):
    """删除模型"""
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
def list_model_versions(model_id: str):
    """列出模型版本"""
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
def create_model_version(model_id: str):
    """创建模型版本"""
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
def list_deployments():
    """列出所有部署"""
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
def deploy_model(model_id: str):
    """部署模型"""
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
def undeploy_model(deployment_id: str):
    """取消部署"""
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
def predict(deployment_id: str):
    """单条预测"""
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
                "generated_text": f"[Mock] Generated response for: {input_data[:50]}...",
                "model": model.name if model else "unknown",
                "mock": True
            }
        elif model_type == "text-classification":
            result = {
                "labels": ["positive", "negative", "neutral"],
                "scores": [0.85, 0.10, 0.05],
                "model": model.name if model else "unknown",
                "mock": True
            }
        elif model_type == "text2text-generation":
            result = {
                "generated_text": f"[Mock] Translated/transformed: {input_data[:50]}...",
                "model": model.name if model else "unknown",
                "mock": True
            }
        else:
            result = {
                "output": f"[Mock] Prediction for type {model_type}",
                "model": model.name if model else "unknown",
                "mock": True
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
def create_batch_prediction():
    """创建批量预测任务"""
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
def get_batch_prediction(job_id: str):
    """获取批量预测任务状态"""
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
def list_training_jobs():
    """列出训练任务"""
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
def create_training_job():
    """创建训练任务"""
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
def get_training_job(job_id: str):
    """获取训练任务详情"""
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
def cancel_training_job(job_id: str):
    """取消训练任务"""
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
def search_huggingface_models():
    """搜索 Hugging Face 模型"""
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
def get_huggingface_model(model_id: str):
    """获取 Hugging Face 模型详情"""
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
def import_huggingface_model(model_id: str):
    """从 Hugging Face 导入模型"""
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
def get_pipeline_tags():
    """获取所有 Pipeline 标签"""
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
def search_huggingface_datasets():
    """搜索 Hugging Face 数据集"""
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


# ==================== 初始化数据库 ====================

@app.route("/api/v1/init-db", methods=["POST"])
def init_database():
    """初始化数据库表"""
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

    logger.info(f"Starting Cube API on port {port}")
    app.run(host="0.0.0.0", port=port, debug=os.getenv("DEBUG", "false").lower() == "true")
