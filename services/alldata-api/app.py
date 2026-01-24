"""
Alldata API - 数据治理与开发平台 API
Sprint 4.4: 真实 MySQL 数据持久化

功能：
- 数据集 CRUD 操作
- 元数据管理
- MinIO 文件存储集成
- JWT 认证授权
- Prometheus 指标埋点
"""

import os
import sys
from datetime import datetime

from flask import Flask, jsonify, request, g

# 添加共享模块路径
sys.path.insert(0, '/app/shared')

# 导入模型
from models import (
    get_db, Dataset, DatasetColumn, DatasetVersion,
    MetadataDatabase, MetadataTable, MetadataColumn
)
from sqlalchemy.orm import joinedload

# 尝试导入认证模块
try:
    from auth import (
        require_jwt,
        require_permission,
        Resource,
        Operation,
        is_health_check_endpoint,
        get_current_user
    )
    AUTH_ENABLED = True
except ImportError:
    AUTH_ENABLED = False
    # 装饰器空实现（开发模式）
    def require_jwt(optional=False):
        def decorator(fn):
            return fn
        return decorator
    def require_permission(resource, operation):
        def decorator(fn):
            return fn
        return decorator
    class Resource:
        DATASET = type('', (), {'value': 'dataset'})()
    class Operation:
        CREATE = type('', (), {'value': 'create'})()
        UPDATE = type('', (), {'value': 'update'})()
        DELETE = type('', (), {'value': 'delete'})()

# 尝试导入验证模块
try:
    from shared.validation import (
        validate_request, validate_query_params, sanitize_input,
        check_sql_injection, limit_content_size, COMMON_SCHEMAS
    )
    VALIDATION_ENABLED = True
except ImportError:
    VALIDATION_ENABLED = False
    # 装饰器空实现
    def validate_request(*args, **kwargs):
        def decorator(fn):
            return fn
        return decorator
    def sanitize_input(*args, **kwargs):
        def decorator(fn):
            return fn
        return decorator
    def check_sql_injection(*args, **kwargs):
        def decorator(fn):
            return fn
        return decorator
    def limit_content_size(*args, **kwargs):
        def decorator(fn):
            return fn
        return decorator
    def validate_query_params(*args, **kwargs):
        def decorator(fn):
            return fn
        return decorator

# 尝试导入 Prometheus 指标
try:
    from prometheus_flask_exporter import PrometheusMetrics
    PROMETHEUS_ENABLED = True
except ImportError:
    PROMETHEUS_ENABLED = False

# 尝试导入 MinIO 存储
try:
    from storage import get_storage
    MINIO_ENABLED = True
except ImportError:
    MINIO_ENABLED = False

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False

# 配置 Prometheus 指标
if PROMETHEUS_ENABLED:
    metrics = PrometheusMetrics(
        app,
        defaults_prefix='alldata_api',
        default_label_as_endpoint=True,
    )
    # 自定义指标
    metrics.info('alldata_api_info', 'Alldata API 信息', version='2.0.0')

# 配置
ALDATA_API_URL = os.getenv("ALDATA_API_URL", "http://alldata-api:8080")
KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://keycloak.one-data-system.svc.cluster.local:80")
AUTH_MODE = os.getenv("AUTH_MODE", "true").lower() == "true"


@app.before_request
def check_auth_skip():
    """跳过健康检查的认证"""
    if not AUTH_MODE or not AUTH_ENABLED:
        return None
    return None


def get_db_session():
    """获取数据库会话"""
    from models import SessionLocal
    return SessionLocal()


@app.route("/api/v1/health")
def health():
    """健康检查（无需认证）"""
    health_status = {
        "code": 0,
        "message": "healthy",
        "service": "alldata-api",
        "version": "2.0.0",
        "auth_enabled": AUTH_ENABLED and AUTH_MODE,
        "prometheus_enabled": PROMETHEUS_ENABLED,
        "minio_enabled": MINIO_ENABLED,
        "checks": {}
    }

    all_healthy = True

    # 测试数据库连接
    try:
        db = get_db_session()
        db.execute("SELECT 1")
        db.close()
        health_status["checks"]["database"] = {"status": "healthy", "latency_ms": 0}
    except Exception as e:
        health_status["checks"]["database"] = {"status": "unhealthy", "error": str(e)}
        all_healthy = False

    # 测试 MinIO 连接
    if MINIO_ENABLED:
        try:
            import time
            start = time.time()
            storage = get_storage()
            buckets = storage.client.list_buckets()
            latency = (time.time() - start) * 1000
            health_status["checks"]["minio"] = {
                "status": "healthy",
                "latency_ms": round(latency, 2),
                "bucket_count": len(buckets)
            }
        except Exception as e:
            health_status["checks"]["minio"] = {"status": "unhealthy", "error": str(e)}
            all_healthy = False

    # 测试 Redis 连接（如果配置）
    try:
        import redis
        redis_host = os.getenv('REDIS_HOST', 'localhost')
        redis_port = int(os.getenv('REDIS_PORT', '6379'))
        redis_client = redis.Redis(host=redis_host, port=redis_port, socket_timeout=2)
        import time
        start = time.time()
        redis_client.ping()
        latency = (time.time() - start) * 1000
        health_status["checks"]["redis"] = {
            "status": "healthy",
            "latency_ms": round(latency, 2)
        }
    except ImportError:
        health_status["checks"]["redis"] = {"status": "not_configured", "message": "redis package not installed"}
    except Exception as e:
        health_status["checks"]["redis"] = {"status": "unhealthy", "error": str(e)}
        # Redis 不影响整体健康状态（可选依赖）

    # 设置整体状态
    if not all_healthy:
        health_status["code"] = 1
        health_status["message"] = "degraded"

    return jsonify(health_status), 200 if all_healthy else 503


@app.route("/metrics")
def metrics():
    """Prometheus 指标端点"""
    if PROMETHEUS_ENABLED:
        from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
        from flask import Response
        return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)
    return jsonify({"error": "Prometheus not enabled"}), 404


@app.route("/api/v1/datasets", methods=["GET"])
@require_jwt(optional=True)
def list_datasets():
    """列出所有数据集"""
    db = get_db_session()
    try:
        query = db.query(Dataset).order_by(Dataset.created_at.desc())

        # 过滤条件
        status_filter = request.args.get("status")
        if status_filter:
            query = query.filter(Dataset.status == status_filter)

        datasets = query.all()
        result = [ds.to_dict(include_columns=False) for ds in datasets]

        # 如果已认证，返回用户信息
        response_data = {"code": 0, "message": "success", "data": result}
        if AUTH_ENABLED and AUTH_MODE:
            user = get_current_user()
            if user:
                response_data["_user"] = user

        return jsonify(response_data)
    finally:
        db.close()


@app.route("/api/v1/datasets/<dataset_id>", methods=["GET"])
@require_jwt(optional=True)
def get_dataset(dataset_id):
    """获取单个数据集详情"""
    db = get_db_session()
    try:
        ds = db.query(Dataset).filter(
            (Dataset.dataset_id == dataset_id) | (Dataset.id == dataset_id)
        ).options(joinedload(Dataset.columns)).first()

        if ds:
            return jsonify({"code": 0, "message": "success", "data": ds.to_dict(include_columns=True)})
        return jsonify({"code": 40401, "message": "Dataset not found"}), 404
    finally:
        db.close()


@app.route("/api/v1/datasets", methods=["POST"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.CREATE)
@validate_request('dataset_create')
@sanitize_input('name', 'description')
def create_dataset():
    """创建数据集（需要认证）"""
    data = request.json
    if not data or not data.get("name"):
        return jsonify({"code": 40001, "message": "Dataset name is required"}), 400

    db = get_db_session()
    try:
        # 生成 dataset_id
        import uuid
        dataset_id = f"ds-{uuid.uuid4().hex[:8]}"

        dataset = Dataset(
            dataset_id=dataset_id,
            name=data.get("name"),
            description=data.get("description", ""),
            storage_type=data.get("storage_type", "s3"),
            storage_path=data.get("storage_path", ""),
            format=data.get("format", "csv"),
            status=data.get("status", "active"),
            tags=data.get("tags", []),
            row_count=data.get("row_count", 0),
            size_bytes=data.get("size_bytes", 0),
        )

        db.add(dataset)
        db.flush()

        # 添加列定义
        columns = data.get("schema", {}).get("columns", [])
        for idx, col in enumerate(columns):
            db.add(DatasetColumn(
                dataset_id=dataset_id,
                column_name=col.get("name"),
                column_type=col.get("type"),
                is_nullable=col.get("nullable", True),
                description=col.get("description", ""),
                position=idx + 1
            ))

        db.commit()
        return jsonify({"code": 0, "message": "success", "data": {"dataset_id": dataset_id}}), 201
    except Exception as e:
        db.rollback()
        return jsonify({"code": 50001, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/datasets/<dataset_id>", methods=["PUT"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.UPDATE)
def update_dataset(dataset_id):
    """更新数据集（需要认证）"""
    db = get_db_session()
    try:
        ds = db.query(Dataset).filter(
            (Dataset.dataset_id == dataset_id) | (Dataset.id == dataset_id)
        ).first()

        if not ds:
            return jsonify({"code": 40401, "message": "Dataset not found"}), 404

        data = request.json

        # 更新允许的字段
        if "name" in data:
            ds.name = data["name"]
        if "description" in data:
            ds.description = data["description"]
        if "tags" in data:
            ds.tags = data["tags"]
        if "status" in data:
            ds.status = data["status"]
        if "storage_path" in data:
            ds.storage_path = data["storage_path"]
        if "row_count" in data:
            ds.row_count = data["row_count"]
        if "size_bytes" in data:
            ds.size_bytes = data["size_bytes"]

        db.commit()
        return jsonify({"code": 0, "message": "success", "data": ds.to_dict()})
    except Exception as e:
        db.rollback()
        return jsonify({"code": 50001, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/datasets/<dataset_id>", methods=["DELETE"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.DELETE)
def delete_dataset(dataset_id):
    """删除数据集（需要认证）"""
    db = get_db_session()
    try:
        ds = db.query(Dataset).filter(
            (Dataset.dataset_id == dataset_id) | (Dataset.id == dataset_id)
        ).first()

        if ds:
            db.delete(ds)  # 级联删除会自动删除关联的 columns
            db.commit()
            return jsonify({"code": 0, "message": "success"})
        return jsonify({"code": 40401, "message": "Dataset not found"}), 404
    except Exception as e:
        db.rollback()
        return jsonify({"code": 50001, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/metadata/databases", methods=["GET"])
@require_jwt(optional=True)
def list_databases():
    """列出数据库"""
    db = get_db_session()
    try:
        databases = db.query(MetadataDatabase).all()
        result = [db_obj.to_dict() for db_obj in databases]
        return jsonify({
            "code": 0,
            "message": "success",
            "data": {"databases": result}
        })
    finally:
        db.close()


@app.route("/api/v1/metadata/databases/<database>/tables", methods=["GET"])
@require_jwt(optional=True)
def list_tables(database):
    """列出数据库中的表"""
    db = get_db_session()
    try:
        tables = db.query(MetadataTable).filter(
            MetadataTable.database_name == database
        ).all()
        result = [t.to_dict() for t in tables]
        return jsonify({
            "code": 0,
            "message": "success",
            "data": {"tables": result}
        })
    finally:
        db.close()


@app.route("/api/v1/metadata/databases/<database>/tables/<table>/columns", methods=["GET"])
@require_jwt(optional=True)
def list_columns(database, table):
    """列出表的列信息"""
    db = get_db_session()
    try:
        columns = db.query(MetadataColumn).filter(
            MetadataColumn.database_name == database,
            MetadataColumn.table_name == table
        ).order_by(MetadataColumn.position).all()
        result = [c.to_dict() for c in columns]
        return jsonify({
            "code": 0,
            "message": "success",
            "data": {"columns": result}
        })
    finally:
        db.close()


@app.errorhandler(401)
def unauthorized(error):
    """未授权响应"""
    return jsonify({
        "code": 40100,
        "message": "Unauthorized",
        "error": "authentication_required"
    }), 401


@app.errorhandler(403)
def forbidden(error):
    """禁止访问响应"""
    return jsonify({
        "code": 40300,
        "message": "Forbidden",
        "error": "insufficient_permissions"
    }), 403


@app.errorhandler(404)
def not_found(error):
    """未找到响应"""
    return jsonify({
        "code": 40400,
        "message": "Resource not found"
    }), 404


@app.errorhandler(500)
def internal_error(error):
    """服务器错误响应"""
    return jsonify({
        "code": 50000,
        "message": "Internal server error"
    }), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    debug = os.getenv("DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
