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
    MetadataDatabase, MetadataTable, MetadataColumn,
    ETLTask, ETLTaskLog,
    QualityRule, QualityTask, QualityReport, QualityAlert,
    LineageNode, LineageEdge, LineageSnapshot,
    MetricDefinition, MetricValue, MetricCategory
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
    # Check if we're in production - validation is required in production
    if os.getenv('ENVIRONMENT', '').lower() in ('production', 'prod'):
        raise ImportError(
            "Validation module is required in production. "
            "Ensure shared/validation.py is present and all dependencies are installed."
        )

    VALIDATION_ENABLED = False
    import logging
    logging.getLogger(__name__).warning(
        "Validation module not available. Running without input validation. "
        "This is NOT safe for production use."
    )
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


# Import resilience utilities for production reliability
try:
    from shared.resilience import (
        get_db_session_with_retry,
        RetryConfig,
        redis_with_circuit_breaker,
        get_redis_circuit_breaker
    )
    RESILIENCE_ENABLED = True
except ImportError:
    RESILIENCE_ENABLED = False
    import logging
    logging.getLogger(__name__).warning(
        "Resilience module not available. Running without retry/circuit breaker support."
    )


def get_db_session():
    """获取数据库会话（生产环境带重试）"""
    from models import SessionLocal

    if RESILIENCE_ENABLED:
        # 使用带重试的会话获取
        retry_config = RetryConfig(
            max_retries=3,
            base_delay=1.0,
            max_delay=10.0
        )
        return get_db_session_with_retry(SessionLocal, retry_config)
    else:
        # 回退到简单的会话获取
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

# Import SQL sanitizer for secure query execution
try:
    from src.sql_executor import SQLSanitizer
    SQL_SANITIZER_AVAILABLE = True
except ImportError:
    SQL_SANITIZER_AVAILABLE = False
    import logging
    logging.getLogger(__name__).warning(
        "SQLSanitizer not available. Using basic SQL validation. "
        "For production, ensure src/sql_executor.py is available."
    )


@app.route("/api/v1/query/execute", methods=["POST"])
@require_jwt()
@check_sql_injection('sql')
def execute_query():
    """
    执行 SQL 查询
    Sprint 7: 前端期望的查询执行接口
    使用 SQLSanitizer 进行完整安全检查
    """
    data = request.json
    if not data or not data.get("sql"):
        return jsonify({"code": 40001, "message": "SQL query is required"}), 400

    sql = data.get("sql", "").strip()
    database = data.get("database", "default")
    limit = min(data.get("limit", 100), 1000)  # 最大1000行
    timeout = min(data.get("timeout", 30), 60)  # 最大60秒

    # 使用 SQLSanitizer 进行完整安全检查
    if SQL_SANITIZER_AVAILABLE:
        # 完整安全检查
        is_safe, error_msg = SQLSanitizer.is_safe(sql)
        if not is_safe:
            return jsonify({
                "code": 40003,
                "message": f"SQL validation failed: {error_msg}",
                "error": "invalid_query"
            }), 400

        # 清洗 SQL
        sql = SQLSanitizer.sanitize(sql)
    else:
        # 回退到基本检查（仅用于开发环境）
        sql_upper = sql.upper().strip()
        if not sql_upper.startswith("SELECT"):
            return jsonify({
                "code": 40003,
                "message": "Only SELECT queries are allowed",
                "error": "invalid_query_type"
            }), 400

        # 基本危险关键字检查
        dangerous_keywords = ['DROP', 'DELETE', 'TRUNCATE', 'ALTER', 'CREATE', 'INSERT', 'UPDATE']
        for keyword in dangerous_keywords:
            if f' {keyword} ' in f' {sql_upper} ' or sql_upper.startswith(keyword):
                return jsonify({
                    "code": 40003,
                    "message": f"Dangerous keyword detected: {keyword}",
                    "error": "invalid_query"
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


# ============================================
# P1.1: ETL Task Management APIs
# ============================================

def generate_id(prefix: str) -> str:
    """生成带前缀的唯一 ID"""
    import uuid
    return f"{prefix}{uuid.uuid4().hex[:12]}"


@app.route("/api/v1/etl/tasks", methods=["GET"])
@require_jwt(optional=True)
def list_etl_tasks():
    """
    列出 ETL 任务
    支持分页和状态/类型筛选
    """
    page = int(request.args.get("page", 1))
    page_size = min(int(request.args.get("page_size", 20)), 100)
    status_filter = request.args.get("status")
    type_filter = request.args.get("type")
    search = request.args.get("search")

    db = get_db_session()
    try:
        query = db.query(ETLTask).order_by(ETLTask.created_at.desc())

        # 过滤条件
        if status_filter:
            query = query.filter(ETLTask.status == status_filter)
        if type_filter:
            query = query.filter(ETLTask.task_type == type_filter)
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                (ETLTask.name.ilike(search_pattern)) |
                (ETLTask.description.ilike(search_pattern))
            )

        # 总数
        total = query.count()

        # 分页
        offset = (page - 1) * page_size
        tasks = query.offset(offset).limit(page_size).all()

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
    finally:
        db.close()


@app.route("/api/v1/etl/tasks", methods=["POST"])
@require_jwt()
def create_etl_task():
    """创建 ETL 任务"""
    data = request.json
    if not data or not data.get("name"):
        return jsonify({"code": 40001, "message": "Task name is required"}), 400

    db = get_db_session()
    try:
        task_id = generate_id("etl_")

        task = ETLTask(
            task_id=task_id,
            name=data.get("name"),
            description=data.get("description", ""),
            task_type=data.get("task_type", "batch"),
            status="pending",
            source_type=data.get("source_type"),
            source_config=data.get("source_config"),
            source_query=data.get("source_query"),
            target_type=data.get("target_type"),
            target_config=data.get("target_config"),
            target_table=data.get("target_table"),
            transform_config=data.get("transform_config"),
            schedule_type=data.get("schedule_type", "manual"),
            schedule_config=data.get("schedule_config"),
            created_by=data.get("created_by"),
        )

        db.add(task)
        db.commit()

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {"task_id": task_id}
        }), 201
    except Exception as e:
        db.rollback()
        return jsonify({"code": 50001, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/etl/tasks/<task_id>", methods=["GET"])
@require_jwt(optional=True)
def get_etl_task(task_id):
    """获取 ETL 任务详情"""
    db = get_db_session()
    try:
        task = db.query(ETLTask).filter(ETLTask.task_id == task_id).first()
        if not task:
            return jsonify({"code": 40401, "message": "Task not found"}), 404

        return jsonify({
            "code": 0,
            "message": "success",
            "data": task.to_dict()
        })
    finally:
        db.close()


@app.route("/api/v1/etl/tasks/<task_id>", methods=["PUT"])
@require_jwt()
def update_etl_task(task_id):
    """更新 ETL 任务配置"""
    db = get_db_session()
    try:
        task = db.query(ETLTask).filter(ETLTask.task_id == task_id).first()
        if not task:
            return jsonify({"code": 40401, "message": "Task not found"}), 404

        data = request.json or {}

        # 可更新字段
        updatable_fields = [
            "name", "description", "task_type",
            "source_type", "source_config", "source_query",
            "target_type", "target_config", "target_table",
            "transform_config", "schedule_type", "schedule_config"
        ]

        for field in updatable_fields:
            if field in data:
                setattr(task, field, data[field])

        if "updated_by" in data:
            task.updated_by = data["updated_by"]

        db.commit()

        return jsonify({
            "code": 0,
            "message": "success",
            "data": task.to_dict()
        })
    except Exception as e:
        db.rollback()
        return jsonify({"code": 50001, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/etl/tasks/<task_id>", methods=["DELETE"])
@require_jwt()
def delete_etl_task(task_id):
    """删除 ETL 任务"""
    db = get_db_session()
    try:
        task = db.query(ETLTask).filter(ETLTask.task_id == task_id).first()
        if not task:
            return jsonify({"code": 40401, "message": "Task not found"}), 404

        # 检查任务是否正在运行
        if task.status == "running":
            return jsonify({
                "code": 40002,
                "message": "Cannot delete running task. Stop it first."
            }), 400

        db.delete(task)
        db.commit()

        return jsonify({"code": 0, "message": "success"})
    except Exception as e:
        db.rollback()
        return jsonify({"code": 50001, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/etl/tasks/<task_id>/start", methods=["POST"])
@require_jwt()
def start_etl_task(task_id):
    """启动 ETL 任务"""
    db = get_db_session()
    try:
        task = db.query(ETLTask).filter(ETLTask.task_id == task_id).first()
        if not task:
            return jsonify({"code": 40401, "message": "Task not found"}), 404

        if task.status == "running":
            return jsonify({
                "code": 40002,
                "message": "Task is already running"
            }), 400

        # 更新任务状态
        task.status = "running"
        task.last_run_at = datetime.utcnow()
        task.run_count = (task.run_count or 0) + 1

        # 创建执行日志
        log_id = generate_id("etl_log_")
        log = ETLTaskLog(
            log_id=log_id,
            task_id=task_id,
            status="running",
            trigger_type=request.json.get("trigger_type", "manual") if request.json else "manual",
            triggered_by=request.json.get("triggered_by") if request.json else None,
        )
        db.add(log)
        db.commit()

        # 实际执行逻辑应该放在异步任务队列中
        # 这里仅更新状态，模拟启动

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "task_id": task_id,
                "log_id": log_id,
                "status": "running"
            }
        })
    except Exception as e:
        db.rollback()
        return jsonify({"code": 50001, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/etl/tasks/<task_id>/stop", methods=["POST"])
@require_jwt()
def stop_etl_task(task_id):
    """停止 ETL 任务"""
    db = get_db_session()
    try:
        task = db.query(ETLTask).filter(ETLTask.task_id == task_id).first()
        if not task:
            return jsonify({"code": 40401, "message": "Task not found"}), 404

        if task.status != "running":
            return jsonify({
                "code": 40002,
                "message": "Task is not running"
            }), 400

        # 更新任务状态
        task.status = "stopped"

        # 更新最近的执行日志
        log = db.query(ETLTaskLog).filter(
            ETLTaskLog.task_id == task_id,
            ETLTaskLog.status == "running"
        ).order_by(ETLTaskLog.started_at.desc()).first()

        if log:
            log.status = "stopped"
            log.finished_at = datetime.utcnow()
            if log.started_at:
                log.duration_seconds = int((log.finished_at - log.started_at).total_seconds())

        db.commit()

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {"task_id": task_id, "status": "stopped"}
        })
    except Exception as e:
        db.rollback()
        return jsonify({"code": 50001, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/etl/tasks/<task_id>/logs", methods=["GET"])
@require_jwt(optional=True)
def get_etl_task_logs(task_id):
    """获取 ETL 任务执行日志"""
    page = int(request.args.get("page", 1))
    page_size = min(int(request.args.get("page_size", 20)), 100)

    db = get_db_session()
    try:
        # 验证任务存在
        task = db.query(ETLTask).filter(ETLTask.task_id == task_id).first()
        if not task:
            return jsonify({"code": 40401, "message": "Task not found"}), 404

        query = db.query(ETLTaskLog).filter(
            ETLTaskLog.task_id == task_id
        ).order_by(ETLTaskLog.started_at.desc())

        total = query.count()
        offset = (page - 1) * page_size
        logs = query.offset(offset).limit(page_size).all()

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "logs": [log.to_dict() for log in logs],
                "total": total,
                "page": page,
                "page_size": page_size
            }
        })
    finally:
        db.close()


# ============================================
# P1.2: Data Quality Management APIs
# ============================================

# ---------- Quality Rules ----------

@app.route("/api/v1/quality/rules", methods=["GET"])
@require_jwt(optional=True)
def list_quality_rules():
    """获取质量规则列表"""
    page = int(request.args.get("page", 1))
    page_size = min(int(request.args.get("page_size", 20)), 100)
    rule_type = request.args.get("type")
    is_active = request.args.get("is_active")

    db = get_db_session()
    try:
        query = db.query(QualityRule).order_by(QualityRule.created_at.desc())

        if rule_type:
            query = query.filter(QualityRule.rule_type == rule_type)
        if is_active is not None:
            query = query.filter(QualityRule.is_active == (is_active.lower() == "true"))

        total = query.count()
        offset = (page - 1) * page_size
        rules = query.offset(offset).limit(page_size).all()

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
    finally:
        db.close()


@app.route("/api/v1/quality/rules", methods=["POST"])
@require_jwt()
def create_quality_rule():
    """创建质量规则"""
    data = request.json
    if not data or not data.get("name") or not data.get("rule_type"):
        return jsonify({"code": 40001, "message": "Name and rule_type are required"}), 400

    db = get_db_session()
    try:
        rule_id = generate_id("qr_")

        rule = QualityRule(
            rule_id=rule_id,
            name=data.get("name"),
            description=data.get("description", ""),
            rule_type=data.get("rule_type"),
            target_database=data.get("target_database"),
            target_table=data.get("target_table"),
            target_column=data.get("target_column"),
            rule_expression=data.get("rule_expression"),
            threshold=data.get("threshold", 100.0),
            severity=data.get("severity", "warning"),
            is_active=data.get("is_active", True),
            created_by=data.get("created_by"),
        )

        db.add(rule)
        db.commit()

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {"rule_id": rule_id}
        }), 201
    except Exception as e:
        db.rollback()
        return jsonify({"code": 50001, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/quality/rules/<rule_id>", methods=["GET"])
@require_jwt(optional=True)
def get_quality_rule(rule_id):
    """获取质量规则详情"""
    db = get_db_session()
    try:
        rule = db.query(QualityRule).filter(QualityRule.rule_id == rule_id).first()
        if not rule:
            return jsonify({"code": 40401, "message": "Rule not found"}), 404

        return jsonify({
            "code": 0,
            "message": "success",
            "data": rule.to_dict()
        })
    finally:
        db.close()


@app.route("/api/v1/quality/rules/<rule_id>", methods=["PUT"])
@require_jwt()
def update_quality_rule(rule_id):
    """更新质量规则"""
    db = get_db_session()
    try:
        rule = db.query(QualityRule).filter(QualityRule.rule_id == rule_id).first()
        if not rule:
            return jsonify({"code": 40401, "message": "Rule not found"}), 404

        data = request.json or {}
        updatable_fields = [
            "name", "description", "rule_type", "target_database",
            "target_table", "target_column", "rule_expression",
            "threshold", "severity", "is_active"
        ]

        for field in updatable_fields:
            if field in data:
                setattr(rule, field, data[field])

        if "updated_by" in data:
            rule.updated_by = data["updated_by"]

        db.commit()

        return jsonify({
            "code": 0,
            "message": "success",
            "data": rule.to_dict()
        })
    except Exception as e:
        db.rollback()
        return jsonify({"code": 50001, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/quality/rules/<rule_id>", methods=["DELETE"])
@require_jwt()
def delete_quality_rule(rule_id):
    """删除质量规则"""
    db = get_db_session()
    try:
        rule = db.query(QualityRule).filter(QualityRule.rule_id == rule_id).first()
        if not rule:
            return jsonify({"code": 40401, "message": "Rule not found"}), 404

        db.delete(rule)
        db.commit()

        return jsonify({"code": 0, "message": "success"})
    except Exception as e:
        db.rollback()
        return jsonify({"code": 50001, "message": str(e)}), 500
    finally:
        db.close()


# ---------- Quality Tasks ----------

@app.route("/api/v1/quality/tasks", methods=["GET"])
@require_jwt(optional=True)
def list_quality_tasks():
    """获取质量检查任务列表"""
    page = int(request.args.get("page", 1))
    page_size = min(int(request.args.get("page_size", 20)), 100)
    status = request.args.get("status")

    db = get_db_session()
    try:
        query = db.query(QualityTask).order_by(QualityTask.created_at.desc())

        if status:
            query = query.filter(QualityTask.status == status)

        total = query.count()
        offset = (page - 1) * page_size
        tasks = query.offset(offset).limit(page_size).all()

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
    finally:
        db.close()


@app.route("/api/v1/quality/tasks", methods=["POST"])
@require_jwt()
def create_quality_task():
    """创建质量检查任务"""
    data = request.json
    if not data or not data.get("name"):
        return jsonify({"code": 40001, "message": "Task name is required"}), 400

    db = get_db_session()
    try:
        task_id = generate_id("qt_")

        task = QualityTask(
            task_id=task_id,
            name=data.get("name"),
            description=data.get("description", ""),
            rule_ids=data.get("rule_ids", []),
            schedule_type=data.get("schedule_type", "manual"),
            schedule_config=data.get("schedule_config"),
            is_active=data.get("is_active", True),
            created_by=data.get("created_by"),
        )

        db.add(task)
        db.commit()

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {"task_id": task_id}
        }), 201
    except Exception as e:
        db.rollback()
        return jsonify({"code": 50001, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/quality/tasks/<task_id>/run", methods=["POST"])
@require_jwt()
def run_quality_task(task_id):
    """执行质量检查任务"""
    db = get_db_session()
    try:
        task = db.query(QualityTask).filter(QualityTask.task_id == task_id).first()
        if not task:
            return jsonify({"code": 40401, "message": "Task not found"}), 404

        if task.status == "running":
            return jsonify({
                "code": 40002,
                "message": "Task is already running"
            }), 400

        # 更新任务状态
        task.status = "running"
        task.last_run_at = datetime.utcnow()
        task.run_count = (task.run_count or 0) + 1

        # 创建报告
        report_id = generate_id("qrpt_")
        report = QualityReport(
            report_id=report_id,
            task_id=task_id,
            status="running",
            total_rules=len(task.rule_ids) if task.rule_ids else 0,
        )
        db.add(report)
        db.commit()

        # 实际检查逻辑应放在异步任务队列中
        # 这里仅创建报告和更新状态

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "task_id": task_id,
                "report_id": report_id,
                "status": "running"
            }
        })
    except Exception as e:
        db.rollback()
        return jsonify({"code": 50001, "message": str(e)}), 500
    finally:
        db.close()


# ---------- Quality Reports ----------

@app.route("/api/v1/quality/reports", methods=["GET"])
@require_jwt(optional=True)
def list_quality_reports():
    """获取质量报告列表"""
    page = int(request.args.get("page", 1))
    page_size = min(int(request.args.get("page_size", 20)), 100)
    task_id = request.args.get("task_id")
    status = request.args.get("status")

    db = get_db_session()
    try:
        query = db.query(QualityReport).order_by(QualityReport.created_at.desc())

        if task_id:
            query = query.filter(QualityReport.task_id == task_id)
        if status:
            query = query.filter(QualityReport.status == status)

        total = query.count()
        offset = (page - 1) * page_size
        reports = query.offset(offset).limit(page_size).all()

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "reports": [r.to_dict() for r in reports],
                "total": total,
                "page": page,
                "page_size": page_size
            }
        })
    finally:
        db.close()


@app.route("/api/v1/quality/reports/<report_id>", methods=["GET"])
@require_jwt(optional=True)
def get_quality_report(report_id):
    """获取质量报告详情"""
    db = get_db_session()
    try:
        report = db.query(QualityReport).filter(QualityReport.report_id == report_id).first()
        if not report:
            return jsonify({"code": 40401, "message": "Report not found"}), 404

        return jsonify({
            "code": 0,
            "message": "success",
            "data": report.to_dict()
        })
    finally:
        db.close()


# ---------- Quality Alerts ----------

@app.route("/api/v1/quality/alerts", methods=["GET"])
@require_jwt(optional=True)
def list_quality_alerts():
    """获取质量告警列表"""
    page = int(request.args.get("page", 1))
    page_size = min(int(request.args.get("page_size", 20)), 100)
    status = request.args.get("status")
    severity = request.args.get("severity")

    db = get_db_session()
    try:
        query = db.query(QualityAlert).order_by(QualityAlert.created_at.desc())

        if status:
            query = query.filter(QualityAlert.status == status)
        if severity:
            query = query.filter(QualityAlert.severity == severity)

        total = query.count()
        offset = (page - 1) * page_size
        alerts = query.offset(offset).limit(page_size).all()

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
    finally:
        db.close()


@app.route("/api/v1/quality/alerts/<alert_id>/acknowledge", methods=["PUT"])
@require_jwt()
def acknowledge_quality_alert(alert_id):
    """确认质量告警"""
    db = get_db_session()
    try:
        alert = db.query(QualityAlert).filter(QualityAlert.alert_id == alert_id).first()
        if not alert:
            return jsonify({"code": 40401, "message": "Alert not found"}), 404

        data = request.json or {}

        alert.status = "acknowledged"
        alert.acknowledged_by = data.get("acknowledged_by")
        alert.acknowledged_at = datetime.utcnow()

        db.commit()

        return jsonify({
            "code": 0,
            "message": "success",
            "data": alert.to_dict()
        })
    except Exception as e:
        db.rollback()
        return jsonify({"code": 50001, "message": str(e)}), 500
    finally:
        db.close()


# ============================================
# P1.3: Data Lineage APIs
# ============================================

@app.route("/api/v1/lineage/table/<table_name>", methods=["GET"])
@require_jwt(optional=True)
def get_table_lineage(table_name):
    """
    获取表级血缘图
    参数:
    - database: 数据库名（可选）
    - depth: 血缘深度（默认3）
    - direction: upstream/downstream/both（默认both）
    """
    database = request.args.get("database")
    depth = min(int(request.args.get("depth", 3)), 10)
    direction = request.args.get("direction", "both")

    db = get_db_session()
    try:
        # 查找目标表节点
        query = db.query(LineageNode).filter(
            LineageNode.table_name == table_name,
            LineageNode.node_type == "table"
        )
        if database:
            query = query.filter(LineageNode.database_name == database)

        target_node = query.first()
        if not target_node:
            return jsonify({"code": 40401, "message": "Table not found in lineage"}), 404

        # 收集节点和边
        nodes = {target_node.node_id: target_node.to_dict()}
        edges = []
        visited = {target_node.node_id}

        def collect_lineage(node_id, current_depth, go_upstream, go_downstream):
            if current_depth >= depth:
                return

            # 上游（数据来源）
            if go_upstream:
                upstream_edges = db.query(LineageEdge).filter(
                    LineageEdge.target_node_id == node_id,
                    LineageEdge.is_active == True
                ).all()

                for edge in upstream_edges:
                    if edge.edge_id not in [e["id"] for e in edges]:
                        edges.append(edge.to_dict())

                    if edge.source_node_id not in visited:
                        visited.add(edge.source_node_id)
                        source_node = db.query(LineageNode).filter(
                            LineageNode.node_id == edge.source_node_id
                        ).first()
                        if source_node:
                            nodes[source_node.node_id] = source_node.to_dict()
                            collect_lineage(source_node.node_id, current_depth + 1, True, False)

            # 下游（数据去向）
            if go_downstream:
                downstream_edges = db.query(LineageEdge).filter(
                    LineageEdge.source_node_id == node_id,
                    LineageEdge.is_active == True
                ).all()

                for edge in downstream_edges:
                    if edge.edge_id not in [e["id"] for e in edges]:
                        edges.append(edge.to_dict())

                    if edge.target_node_id not in visited:
                        visited.add(edge.target_node_id)
                        target_node = db.query(LineageNode).filter(
                            LineageNode.node_id == edge.target_node_id
                        ).first()
                        if target_node:
                            nodes[target_node.node_id] = target_node.to_dict()
                            collect_lineage(target_node.node_id, current_depth + 1, False, True)

        # 根据方向收集血缘
        go_upstream = direction in ("upstream", "both")
        go_downstream = direction in ("downstream", "both")
        collect_lineage(target_node.node_id, 0, go_upstream, go_downstream)

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "target": target_node.to_dict(),
                "nodes": list(nodes.values()),
                "edges": edges,
                "depth": depth,
                "direction": direction
            }
        })
    finally:
        db.close()


@app.route("/api/v1/lineage/column/<table>/<column>", methods=["GET"])
@require_jwt(optional=True)
def get_column_lineage(table, column):
    """
    获取列级血缘
    参数:
    - database: 数据库名（可选）
    - depth: 血缘深度（默认3）
    """
    database = request.args.get("database")
    depth = min(int(request.args.get("depth", 3)), 10)

    db = get_db_session()
    try:
        # 查找目标列节点
        query = db.query(LineageNode).filter(
            LineageNode.table_name == table,
            LineageNode.column_name == column,
            LineageNode.node_type == "column"
        )
        if database:
            query = query.filter(LineageNode.database_name == database)

        target_node = query.first()
        if not target_node:
            return jsonify({"code": 40401, "message": "Column not found in lineage"}), 404

        # 收集血缘（简化版，只收集直接关联）
        nodes = {target_node.node_id: target_node.to_dict()}
        edges = []

        # 上游
        upstream_edges = db.query(LineageEdge).filter(
            LineageEdge.target_node_id == target_node.node_id,
            LineageEdge.is_active == True
        ).all()

        for edge in upstream_edges:
            edges.append(edge.to_dict())
            source_node = db.query(LineageNode).filter(
                LineageNode.node_id == edge.source_node_id
            ).first()
            if source_node:
                nodes[source_node.node_id] = source_node.to_dict()

        # 下游
        downstream_edges = db.query(LineageEdge).filter(
            LineageEdge.source_node_id == target_node.node_id,
            LineageEdge.is_active == True
        ).all()

        for edge in downstream_edges:
            edges.append(edge.to_dict())
            target = db.query(LineageNode).filter(
                LineageNode.node_id == edge.target_node_id
            ).first()
            if target:
                nodes[target.node_id] = target.to_dict()

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "target": target_node.to_dict(),
                "nodes": list(nodes.values()),
                "edges": edges
            }
        })
    finally:
        db.close()


@app.route("/api/v1/lineage/impact-analysis", methods=["POST"])
@require_jwt()
def lineage_impact_analysis():
    """
    影响分析 - 分析某个节点变更会影响哪些下游节点
    """
    data = request.json or {}
    node_id = data.get("node_id")
    table_name = data.get("table_name")
    column_name = data.get("column_name")
    database = data.get("database")

    if not node_id and not table_name:
        return jsonify({"code": 40001, "message": "node_id or table_name is required"}), 400

    db = get_db_session()
    try:
        # 查找源节点
        if node_id:
            source_node = db.query(LineageNode).filter(
                LineageNode.node_id == node_id
            ).first()
        else:
            query = db.query(LineageNode).filter(LineageNode.table_name == table_name)
            if column_name:
                query = query.filter(LineageNode.column_name == column_name)
            if database:
                query = query.filter(LineageNode.database_name == database)
            source_node = query.first()

        if not source_node:
            return jsonify({"code": 40401, "message": "Source node not found"}), 404

        # 收集所有下游影响
        impacted_nodes = []
        impacted_edges = []
        visited = {source_node.node_id}

        def collect_downstream(current_node_id, level):
            if level > 10:  # 最大深度限制
                return

            downstream_edges = db.query(LineageEdge).filter(
                LineageEdge.source_node_id == current_node_id,
                LineageEdge.is_active == True
            ).all()

            for edge in downstream_edges:
                impacted_edges.append({
                    **edge.to_dict(),
                    "impact_level": level
                })

                if edge.target_node_id not in visited:
                    visited.add(edge.target_node_id)
                    target_node = db.query(LineageNode).filter(
                        LineageNode.node_id == edge.target_node_id
                    ).first()
                    if target_node:
                        impacted_nodes.append({
                            **target_node.to_dict(),
                            "impact_level": level
                        })
                        collect_downstream(target_node.node_id, level + 1)

        collect_downstream(source_node.node_id, 1)

        # 统计影响
        impact_summary = {
            "total_impacted": len(impacted_nodes),
            "by_type": {},
            "by_level": {}
        }

        for node in impacted_nodes:
            node_type = node.get("node_type", "unknown")
            level = node.get("impact_level", 0)

            impact_summary["by_type"][node_type] = impact_summary["by_type"].get(node_type, 0) + 1
            impact_summary["by_level"][str(level)] = impact_summary["by_level"].get(str(level), 0) + 1

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "source": source_node.to_dict(),
                "impacted_nodes": impacted_nodes,
                "impacted_edges": impacted_edges,
                "summary": impact_summary
            }
        })
    finally:
        db.close()


@app.route("/api/v1/lineage/search", methods=["GET"])
@require_jwt(optional=True)
def search_lineage():
    """
    搜索血缘节点
    参数:
    - query: 搜索关键字
    - node_type: 节点类型筛选
    - database: 数据库筛选
    """
    query_str = request.args.get("query", "")
    node_type = request.args.get("node_type")
    database = request.args.get("database")
    limit = min(int(request.args.get("limit", 50)), 200)

    db = get_db_session()
    try:
        query = db.query(LineageNode).filter(LineageNode.is_active == True)

        if query_str:
            search_pattern = f"%{query_str}%"
            query = query.filter(
                (LineageNode.name.ilike(search_pattern)) |
                (LineageNode.full_name.ilike(search_pattern)) |
                (LineageNode.table_name.ilike(search_pattern)) |
                (LineageNode.column_name.ilike(search_pattern))
            )

        if node_type:
            query = query.filter(LineageNode.node_type == node_type)
        if database:
            query = query.filter(LineageNode.database_name == database)

        nodes = query.limit(limit).all()

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "nodes": [n.to_dict() for n in nodes],
                "total": len(nodes)
            }
        })
    finally:
        db.close()


# ============================================
# P1.4: Metrics Management APIs
# ============================================

@app.route("/api/v1/metrics/definitions", methods=["GET"])
@require_jwt(optional=True)
def list_metric_definitions():
    """获取指标定义列表"""
    page = int(request.args.get("page", 1))
    page_size = min(int(request.args.get("page_size", 20)), 100)
    category = request.args.get("category")
    is_active = request.args.get("is_active")
    is_certified = request.args.get("is_certified")
    search = request.args.get("search")

    db = get_db_session()
    try:
        query = db.query(MetricDefinition).order_by(MetricDefinition.created_at.desc())

        if category:
            query = query.filter(MetricDefinition.category == category)
        if is_active is not None:
            query = query.filter(MetricDefinition.is_active == (is_active.lower() == "true"))
        if is_certified is not None:
            query = query.filter(MetricDefinition.is_certified == (is_certified.lower() == "true"))
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                (MetricDefinition.name.ilike(search_pattern)) |
                (MetricDefinition.display_name.ilike(search_pattern)) |
                (MetricDefinition.description.ilike(search_pattern))
            )

        total = query.count()
        offset = (page - 1) * page_size
        metrics = query.offset(offset).limit(page_size).all()

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "metrics": [m.to_dict() for m in metrics],
                "total": total,
                "page": page,
                "page_size": page_size
            }
        })
    finally:
        db.close()


@app.route("/api/v1/metrics/definitions", methods=["POST"])
@require_jwt()
def create_metric_definition():
    """创建指标定义"""
    data = request.json
    if not data or not data.get("name"):
        return jsonify({"code": 40001, "message": "Metric name is required"}), 400

    db = get_db_session()
    try:
        metric_id = generate_id("metric_")

        metric = MetricDefinition(
            metric_id=metric_id,
            name=data.get("name"),
            display_name=data.get("display_name", data.get("name")),
            description=data.get("description", ""),
            category=data.get("category"),
            subcategory=data.get("subcategory"),
            tags=data.get("tags"),
            metric_type=data.get("metric_type", "count"),
            source_database=data.get("source_database"),
            source_table=data.get("source_table"),
            source_column=data.get("source_column"),
            calculation_sql=data.get("calculation_sql"),
            aggregation_type=data.get("aggregation_type", "daily"),
            time_column=data.get("time_column"),
            unit=data.get("unit"),
            decimal_places=data.get("decimal_places", 2),
            format_pattern=data.get("format_pattern"),
            warning_threshold=data.get("warning_threshold"),
            critical_threshold=data.get("critical_threshold"),
            threshold_direction=data.get("threshold_direction", "above"),
            owner=data.get("owner"),
            owner_team=data.get("owner_team"),
            is_active=data.get("is_active", True),
            is_certified=data.get("is_certified", False),
            created_by=data.get("created_by"),
        )

        db.add(metric)
        db.commit()

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {"metric_id": metric_id}
        }), 201
    except Exception as e:
        db.rollback()
        return jsonify({"code": 50001, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/metrics/definitions/<metric_id>", methods=["GET"])
@require_jwt(optional=True)
def get_metric_definition(metric_id):
    """获取指标定义详情"""
    db = get_db_session()
    try:
        metric = db.query(MetricDefinition).filter(
            MetricDefinition.metric_id == metric_id
        ).first()
        if not metric:
            return jsonify({"code": 40401, "message": "Metric not found"}), 404

        return jsonify({
            "code": 0,
            "message": "success",
            "data": metric.to_dict()
        })
    finally:
        db.close()


@app.route("/api/v1/metrics/definitions/<metric_id>", methods=["PUT"])
@require_jwt()
def update_metric_definition(metric_id):
    """更新指标定义"""
    db = get_db_session()
    try:
        metric = db.query(MetricDefinition).filter(
            MetricDefinition.metric_id == metric_id
        ).first()
        if not metric:
            return jsonify({"code": 40401, "message": "Metric not found"}), 404

        data = request.json or {}
        updatable_fields = [
            "name", "display_name", "description", "category", "subcategory",
            "tags", "metric_type", "source_database", "source_table",
            "source_column", "calculation_sql", "aggregation_type", "time_column",
            "unit", "decimal_places", "format_pattern", "warning_threshold",
            "critical_threshold", "threshold_direction", "owner", "owner_team",
            "is_active", "is_certified"
        ]

        for field in updatable_fields:
            if field in data:
                setattr(metric, field, data[field])

        if "updated_by" in data:
            metric.updated_by = data["updated_by"]

        db.commit()

        return jsonify({
            "code": 0,
            "message": "success",
            "data": metric.to_dict()
        })
    except Exception as e:
        db.rollback()
        return jsonify({"code": 50001, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/metrics/definitions/<metric_id>", methods=["DELETE"])
@require_jwt()
def delete_metric_definition(metric_id):
    """删除指标定义"""
    db = get_db_session()
    try:
        metric = db.query(MetricDefinition).filter(
            MetricDefinition.metric_id == metric_id
        ).first()
        if not metric:
            return jsonify({"code": 40401, "message": "Metric not found"}), 404

        db.delete(metric)
        db.commit()

        return jsonify({"code": 0, "message": "success"})
    except Exception as e:
        db.rollback()
        return jsonify({"code": 50001, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/metrics/data", methods=["GET"])
@require_jwt(optional=True)
def query_metric_data():
    """
    查询指标数据
    参数:
    - metric_id: 指标ID（必须）
    - start_time: 开始时间
    - end_time: 结束时间
    - granularity: 粒度（hourly, daily, weekly, monthly）
    - dimensions: 维度筛选（JSON格式）
    """
    metric_id = request.args.get("metric_id")
    if not metric_id:
        return jsonify({"code": 40001, "message": "metric_id is required"}), 400

    start_time = request.args.get("start_time")
    end_time = request.args.get("end_time")
    granularity = request.args.get("granularity")
    limit = min(int(request.args.get("limit", 100)), 1000)

    db = get_db_session()
    try:
        # 验证指标存在
        metric = db.query(MetricDefinition).filter(
            MetricDefinition.metric_id == metric_id
        ).first()
        if not metric:
            return jsonify({"code": 40401, "message": "Metric not found"}), 404

        # 查询数据
        query = db.query(MetricValue).filter(
            MetricValue.metric_id == metric_id
        ).order_by(MetricValue.time_key.desc())

        if start_time:
            query = query.filter(MetricValue.time_key >= start_time)
        if end_time:
            query = query.filter(MetricValue.time_key <= end_time)
        if granularity:
            query = query.filter(MetricValue.granularity == granularity)

        values = query.limit(limit).all()

        # 计算统计
        if values:
            all_values = [v.value for v in values if v.value is not None]
            stats = {
                "count": len(all_values),
                "min": min(all_values) if all_values else None,
                "max": max(all_values) if all_values else None,
                "avg": sum(all_values) / len(all_values) if all_values else None,
                "latest": values[0].value if values else None
            }
        else:
            stats = {"count": 0, "min": None, "max": None, "avg": None, "latest": None}

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "metric": metric.to_dict(),
                "values": [v.to_dict() for v in values],
                "stats": stats
            }
        })
    finally:
        db.close()


@app.route("/api/v1/metrics/categories", methods=["GET"])
@require_jwt(optional=True)
def list_metric_categories():
    """获取指标分类列表"""
    db = get_db_session()
    try:
        categories = db.query(MetricCategory).filter(
            MetricCategory.is_active == True
        ).order_by(MetricCategory.level, MetricCategory.sort_order).all()

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "categories": [c.to_dict() for c in categories]
            }
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
    environment = os.getenv("ENVIRONMENT", "").lower()
    is_production = environment in ("production", "prod")

    # SECURITY: Block debug mode in production
    if debug and is_production:
        import logging
        logging.error(
            "❌ FATAL: Debug mode is enabled in production environment. "
            "This is a critical security risk. Set DEBUG=false or unset ENVIRONMENT=production."
        )
        import sys
        sys.exit(1)

    # SECURITY: Enforce AUTH_MODE in production
    if is_production and not AUTH_MODE:
        import logging
        logging.error(
            "❌ FATAL: AUTH_MODE is disabled in production environment. "
            "Authentication must be enabled in production. Set AUTH_MODE=true."
        )
        import sys
        sys.exit(1)

    # SECURITY WARNING: Debug mode exposes sensitive information
    if debug:
        import logging
        logging.warning(
            "⚠️  WARNING: Debug mode is ENABLED. This should NEVER be used in production! "
            "Debug mode exposes detailed error information and may enable remote code execution."
        )

    app.run(host="0.0.0.0", port=port, debug=debug)
