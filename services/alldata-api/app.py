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
    # Check if we're in production - auth is required in production
    import os
    if os.getenv('ENVIRONMENT', '').lower() in ('production', 'prod'):
        raise ImportError(
            "Authentication module is required in production. "
            "Ensure auth.py is present and all dependencies are installed."
        )

    AUTH_ENABLED = False
    # 装饰器空实现（开发模式）
    import logging
    logging.getLogger(__name__).warning(
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
# 请求大小限制 - 防止 DoS 攻击
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

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


# ============================================
# Sprint 7: Query Execution APIs
# ============================================

@app.route("/api/v1/query/execute", methods=["POST"])
@require_jwt()
@check_sql_injection('sql')
def execute_query():
    """
    执行 SQL 查询
    Sprint 7: 前端期望的查询执行接口
    """
    data = request.json
    if not data or not data.get("sql"):
        return jsonify({"code": 40001, "message": "SQL query is required"}), 400

    sql = data.get("sql", "").strip()
    database = data.get("database", "default")
    limit = min(data.get("limit", 100), 1000)  # 最大1000行
    timeout = min(data.get("timeout", 30), 60)  # 最大60秒

    # 安全检查：只允许 SELECT 语句
    sql_upper = sql.upper().strip()
    if not sql_upper.startswith("SELECT"):
        return jsonify({
            "code": 40003,
            "message": "Only SELECT queries are allowed",
            "error": "invalid_query_type"
        }), 400

    db = get_db_session()
    try:
        import time
        start_time = time.time()

        # 添加 LIMIT 如果没有
        if "LIMIT" not in sql_upper:
            sql = f"{sql} LIMIT {limit}"

        # 执行查询
        result = db.execute(sql)
        rows = result.fetchall()
        columns = list(result.keys()) if result.keys() else []

        execution_time = time.time() - start_time

        # 转换结果为字典列表
        data_rows = []
        for row in rows:
            data_rows.append(dict(zip(columns, row)))

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "columns": columns,
                "rows": data_rows,
                "row_count": len(data_rows),
                "execution_time_ms": round(execution_time * 1000, 2),
                "truncated": len(data_rows) >= limit
            }
        })
    except Exception as e:
        return jsonify({
            "code": 50002,
            "message": f"Query execution failed: {str(e)}",
            "error": "query_execution_error"
        }), 500
    finally:
        db.close()


@app.route("/api/v1/query/validate", methods=["POST"])
@require_jwt(optional=True)
def validate_query():
    """
    验证 SQL 查询语法
    Sprint 7: SQL 验证接口
    """
    data = request.json
    if not data or not data.get("sql"):
        return jsonify({"code": 40001, "message": "SQL query is required"}), 400

    sql = data.get("sql", "").strip()

    # 基本语法检查
    errors = []
    warnings = []

    # 检查是否为空
    if not sql:
        errors.append({"type": "syntax", "message": "Query cannot be empty"})
        return jsonify({
            "code": 0,
            "message": "validation_failed",
            "data": {"valid": False, "errors": errors, "warnings": warnings}
        })

    sql_upper = sql.upper()

    # 检查危险操作
    dangerous_keywords = ["DROP", "DELETE", "TRUNCATE", "ALTER", "CREATE", "INSERT", "UPDATE"]
    for keyword in dangerous_keywords:
        if keyword in sql_upper:
            if keyword in ["DELETE", "UPDATE", "INSERT"]:
                warnings.append({
                    "type": "security",
                    "message": f"{keyword} statement detected - requires elevated permissions"
                })
            else:
                errors.append({
                    "type": "security",
                    "message": f"{keyword} statement is not allowed"
                })

    # 检查基本语法
    if not any(sql_upper.startswith(kw) for kw in ["SELECT", "WITH", "EXPLAIN", "SHOW", "DESCRIBE"]):
        errors.append({
            "type": "syntax",
            "message": "Query must start with SELECT, WITH, EXPLAIN, SHOW, or DESCRIBE"
        })

    # 检查括号匹配
    if sql.count("(") != sql.count(")"):
        errors.append({"type": "syntax", "message": "Unmatched parentheses"})

    # 检查引号匹配
    single_quotes = sql.count("'") - sql.count("\\'")
    if single_quotes % 2 != 0:
        errors.append({"type": "syntax", "message": "Unmatched single quotes"})

    is_valid = len(errors) == 0

    return jsonify({
        "code": 0,
        "message": "success",
        "data": {
            "valid": is_valid,
            "errors": errors,
            "warnings": warnings
        }
    })


@app.route("/api/v1/metadata/tables/search", methods=["POST"])
@require_jwt(optional=True)
def search_tables():
    """
    智能表搜索
    Sprint 7: 支持模糊搜索表名和列名
    """
    data = request.json or {}
    query = data.get("query", "").strip()
    database = data.get("database")
    limit = min(data.get("limit", 20), 100)

    db = get_db_session()
    try:
        # 构建查询
        tables_query = db.query(MetadataTable)

        if database:
            tables_query = tables_query.filter(MetadataTable.database_name == database)

        if query:
            # 模糊搜索表名和描述
            search_pattern = f"%{query}%"
            tables_query = tables_query.filter(
                (MetadataTable.table_name.ilike(search_pattern)) |
                (MetadataTable.description.ilike(search_pattern))
            )

        tables = tables_query.limit(limit).all()

        # 同时搜索列名
        columns_query = db.query(MetadataColumn)
        if query:
            columns_query = columns_query.filter(
                MetadataColumn.column_name.ilike(f"%{query}%")
            )
        matching_columns = columns_query.limit(limit).all()

        # 收集包含匹配列的表
        column_table_matches = set()
        for col in matching_columns:
            column_table_matches.add((col.database_name, col.table_name))

        result = {
            "tables": [t.to_dict() for t in tables],
            "column_matches": [
                {"database": db_name, "table": tbl_name}
                for db_name, tbl_name in column_table_matches
            ],
            "total_tables": len(tables),
            "total_column_matches": len(column_table_matches)
        }

        return jsonify({"code": 0, "message": "success", "data": result})
    finally:
        db.close()


# ============================================
# Sprint 7: Dataset Extended APIs
# ============================================

@app.route("/api/v1/datasets/<dataset_id>/upload-url", methods=["POST"])
@require_jwt()
def get_dataset_upload_url(dataset_id):
    """
    获取数据集上传预签名 URL
    Sprint 7: MinIO 预签名 URL 生成
    """
    if not MINIO_ENABLED:
        return jsonify({
            "code": 50003,
            "message": "MinIO storage not enabled",
            "error": "storage_not_configured"
        }), 503

    data = request.json or {}
    filename = data.get("filename", "data.csv")
    content_type = data.get("content_type", "application/octet-stream")
    expires = min(data.get("expires", 3600), 86400)  # 最大24小时

    db = get_db_session()
    try:
        # 验证数据集存在
        ds = db.query(Dataset).filter(
            (Dataset.dataset_id == dataset_id) | (Dataset.id == dataset_id)
        ).first()

        if not ds:
            return jsonify({"code": 40401, "message": "Dataset not found"}), 404

        # 生成存储路径
        import uuid
        file_key = f"datasets/{dataset_id}/{uuid.uuid4().hex[:8]}_{filename}"

        # 获取预签名 URL
        storage = get_storage()
        upload_url = storage.get_presigned_upload_url(
            bucket="datasets",
            object_name=file_key,
            expires=expires,
            content_type=content_type
        )

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "upload_url": upload_url,
                "file_key": file_key,
                "expires_in": expires,
                "method": "PUT"
            }
        })
    except Exception as e:
        return jsonify({
            "code": 50001,
            "message": f"Failed to generate upload URL: {str(e)}"
        }), 500
    finally:
        db.close()


@app.route("/api/v1/datasets/<dataset_id>/preview", methods=["GET"])
@require_jwt(optional=True)
def preview_dataset(dataset_id):
    """
    预览数据集内容
    Sprint 7: 数据集预览接口
    """
    limit = min(int(request.args.get("limit", 100)), 1000)
    offset = int(request.args.get("offset", 0))

    db = get_db_session()
    try:
        ds = db.query(Dataset).filter(
            (Dataset.dataset_id == dataset_id) | (Dataset.id == dataset_id)
        ).options(joinedload(Dataset.columns)).first()

        if not ds:
            return jsonify({"code": 40401, "message": "Dataset not found"}), 404

        # 尝试从存储中读取预览数据
        preview_data = {
            "columns": [col.to_dict() for col in ds.columns] if ds.columns else [],
            "rows": [],
            "total_rows": ds.row_count or 0,
            "sample_size": 0
        }

        if MINIO_ENABLED and ds.storage_path:
            try:
                storage = get_storage()
                # 读取数据预览（支持 CSV、Parquet 等格式）
                sample_data = storage.read_preview(
                    bucket="datasets",
                    object_name=ds.storage_path,
                    limit=limit,
                    offset=offset,
                    format=ds.format or "csv"
                )
                if sample_data:
                    preview_data["rows"] = sample_data.get("rows", [])
                    preview_data["sample_size"] = len(preview_data["rows"])
            except Exception as e:
                preview_data["preview_error"] = str(e)

        return jsonify({"code": 0, "message": "success", "data": preview_data})
    finally:
        db.close()


@app.route("/api/v1/datasets/<dataset_id>/versions", methods=["GET"])
@require_jwt(optional=True)
def list_dataset_versions(dataset_id):
    """
    列出数据集版本历史
    Sprint 7: 数据集版本管理
    """
    db = get_db_session()
    try:
        # 验证数据集存在
        ds = db.query(Dataset).filter(
            (Dataset.dataset_id == dataset_id) | (Dataset.id == dataset_id)
        ).first()

        if not ds:
            return jsonify({"code": 40401, "message": "Dataset not found"}), 404

        # 获取版本列表
        versions = db.query(DatasetVersion).filter(
            DatasetVersion.dataset_id == ds.dataset_id
        ).order_by(DatasetVersion.version.desc()).all()

        result = []
        for v in versions:
            result.append({
                "version": v.version,
                "created_at": v.created_at.isoformat() if v.created_at else None,
                "storage_path": v.storage_path,
                "row_count": v.row_count,
                "size_bytes": v.size_bytes,
                "description": v.description,
                "is_current": v.version == ds.current_version if hasattr(ds, 'current_version') else False
            })

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "dataset_id": ds.dataset_id,
                "versions": result,
                "total": len(result)
            }
        })
    finally:
        db.close()


@app.route("/api/v1/datasets/<dataset_id>/versions", methods=["POST"])
@require_jwt()
def create_dataset_version(dataset_id):
    """
    创建数据集新版本
    Sprint 7: 版本创建接口
    """
    data = request.json or {}

    db = get_db_session()
    try:
        ds = db.query(Dataset).filter(
            (Dataset.dataset_id == dataset_id) | (Dataset.id == dataset_id)
        ).first()

        if not ds:
            return jsonify({"code": 40401, "message": "Dataset not found"}), 404

        # 获取最新版本号
        latest = db.query(DatasetVersion).filter(
            DatasetVersion.dataset_id == ds.dataset_id
        ).order_by(DatasetVersion.version.desc()).first()

        new_version = (latest.version + 1) if latest else 1

        # 创建新版本
        version = DatasetVersion(
            dataset_id=ds.dataset_id,
            version=new_version,
            storage_path=data.get("storage_path", ""),
            row_count=data.get("row_count", 0),
            size_bytes=data.get("size_bytes", 0),
            description=data.get("description", f"Version {new_version}")
        )

        db.add(version)
        db.commit()

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "version": new_version,
                "dataset_id": ds.dataset_id
            }
        }), 201
    except Exception as e:
        db.rollback()
        return jsonify({"code": 50001, "message": str(e)}), 500
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
