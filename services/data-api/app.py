"""
Data API - 数据治理与开发平台 API
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
    MetricDefinition, MetricValue, MetricCategory,
    FlinkJob, FlinkJobLog, FlinkSavedQuery,
    Feature, FeatureGroup,
    DataMonitoringRule, DataAlert,
    BIDashboard, BIChart,
    OfflineTask, OfflineTaskLog,
    DataAsset, AssetCategory, AssetCollection,
    DataStandard, StandardValidation,
    DataService, ServiceCallLog
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
    from prometheus_metrics import PrometheusMetrics, init_metrics
    PROMETHEUS_ENABLED = True
except ImportError:
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

# 导入元数据图谱构建服务
try:
    from services.metadata_graph_builder import MetadataGraphBuilder
    GRAPH_BUILDER = MetadataGraphBuilder()
    GRAPH_ENABLED = True
except ImportError:
    GRAPH_ENABLED = False
    GRAPH_BUILDER = None
    import logging
    logging.getLogger(__name__).warning(
        "Metadata graph builder not available. Graph visualization features disabled."
    )

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False
# 请求大小限制 - 防止 DoS 攻击
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

# 配置 Prometheus 指标
metrics = None
if PROMETHEUS_ENABLED:
    try:
        # 使用新的共享 PrometheusMetrics 模块
        sys.path.insert(0, '/app/shared')
        from prometheus_metrics import PrometheusMetrics, init_metrics
        metrics = init_metrics(app, service_name="data-api")
        logger = logging.getLogger(__name__)
        logger.info("Prometheus metrics initialized with shared module")
    except Exception as e:
        # 降级到旧的 prometheus_flask_exporter
        try:
            metrics = PrometheusMetrics(
                app,
                defaults_prefix='data_api',
                default_label_as_endpoint=True,
            )
            # 自定义指标
            metrics.info('data_api_info', 'Data API 信息', version='2.0.0')
            logging.getLogger(__name__).warning(f"Using legacy PrometheusMetrics: {e}")
        except Exception as e2:
            logging.getLogger(__name__).error(f"Failed to initialize Prometheus metrics: {e2}")
            metrics = None

# 配置
DATA_API_URL = os.getenv("DATA_API_URL", "http://data-api:8001")
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
        "service": "data-api",
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
# 元数据图谱可视化 API
# ============================================

@app.route("/api/v1/metadata/graph", methods=["GET"])
@require_jwt(optional=True)
def get_metadata_graph():
    """
    获取完整的元数据图谱

    返回数据库、表、列的层次结构以及它们之间的关系
    """
    if not GRAPH_ENABLED:
        return jsonify({
            "code": 50003,
            "message": "Graph visualization service not available",
        }), 503

    tenant_id = request.args.get("tenant_id", "default")
    node_types_str = request.args.get("node_types", None)
    include_lineage = request.args.get("include_lineage", "true").lower() == "true"

    node_type_list = None
    if node_types_str:
        node_type_list = [t.strip() for t in node_types_str.split(",")]

    db = get_db_session()
    try:
        graph_data = GRAPH_BUILDER.build_full_graph(
            db, tenant_id, node_type_list, include_lineage
        )
        return jsonify({
            "code": 0,
            "message": "success",
            "data": graph_data
        })
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to build metadata graph: {e}")
        return jsonify({
            "code": 50001,
            "message": f"Failed to build graph: {str(e)}"
        }), 500
    finally:
        db.close()


@app.route("/api/v1/metadata/graph/lineage/<table_name>", methods=["GET"])
@require_jwt(optional=True)
def get_table_lineage_graph(table_name):
    """
    获取单个表的数据血缘图谱

    返回该表的上游依赖和下游被依赖
    """
    if not GRAPH_ENABLED:
        return jsonify({
            "code": 50003,
            "message": "Graph visualization service not available",
        }), 503

    tenant_id = request.args.get("tenant_id", "default")
    depth = int(request.args.get("depth", 3))

    db = get_db_session()
    try:
        lineage_data = GRAPH_BUILDER.build_table_lineage_graph(
            db, tenant_id, table_name, depth
        )
        return jsonify({
            "code": 0,
            "message": "success",
            "data": lineage_data
        })
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to build table lineage graph: {e}")
        return jsonify({
            "code": 50001,
            "message": f"Failed to build lineage graph: {str(e)}"
        }), 500
    finally:
        db.close()


@app.route("/api/v1/metadata/graph/columns/<table_name>", methods=["GET"])
@require_jwt(optional=True)
def get_column_relation_graph(table_name):
    """
    获取表的列关系图

    返回表内列之间的关系（外键、关联等）
    """
    if not GRAPH_ENABLED:
        return jsonify({
            "code": 50003,
            "message": "Graph visualization service not available",
        }), 503

    tenant_id = request.args.get("tenant_id", "default")

    db = get_db_session()
    try:
        column_data = GRAPH_BUILDER.build_column_relation_graph(
            db, tenant_id, table_name
        )
        return jsonify({
            "code": 0,
            "message": "success",
            "data": column_data
        })
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to build column relation graph: {e}")
        return jsonify({
            "code": 50001,
            "message": f"Failed to build column graph: {str(e)}"
        }), 500
    finally:
        db.close()


@app.route("/api/v1/metadata/graph/search", methods=["GET"])
@require_jwt(optional=True)
def search_metadata_nodes():
    """
    搜索元数据节点

    支持按名称、描述搜索数据库、表、列
    """
    if not GRAPH_ENABLED:
        return jsonify({
            "code": 50003,
            "message": "Graph visualization service not available",
        }), 503

    query = request.args.get("query")
    if not query:
        return jsonify({
            "code": 40001,
            "message": "query parameter is required"
        }), 400

    tenant_id = request.args.get("tenant_id", "default")
    node_types_str = request.args.get("node_types", None)

    node_type_list = None
    if node_types_str:
        node_type_list = [t.strip() for t in node_types_str.split(",")]

    db = get_db_session()
    try:
        results = GRAPH_BUILDER.search_nodes(
            db, tenant_id, query, node_type_list
        )
        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "query": query,
                "total": len(results),
                "nodes": results
            }
        })
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to search metadata nodes: {e}")
        return jsonify({
            "code": 50001,
            "message": f"Search failed: {str(e)}"
        }), 500
    finally:
        db.close()


@app.route("/api/v1/metadata/graph/statistics", methods=["GET"])
@require_jwt(optional=True)
def get_graph_statistics():
    """
    获取元数据统计信息

    返回数据库、表、列的数量统计
    """
    if not GRAPH_ENABLED:
        return jsonify({
            "code": 50003,
            "message": "Graph visualization service not available",
        }), 503

    tenant_id = request.args.get("tenant_id", "default")

    db = get_db_session()
    try:
        stats = GRAPH_BUILDER.build_statistics_graph(db, tenant_id)
        return jsonify({
            "code": 0,
            "message": "success",
            "data": stats
        })
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to get graph statistics: {e}")
        return jsonify({
            "code": 50001,
            "message": f"Failed to get statistics: {str(e)}"
        }), 500
    finally:
        db.close()


@app.route("/api/v1/metadata/graph/neighbors/<node_type>/<node_id>", methods=["GET"])
@require_jwt(optional=True)
def get_node_neighbors(node_type, node_id):
    """
    获取节点的邻居

    返回指定节点的直接关联节点
    """
    if not GRAPH_ENABLED:
        return jsonify({
            "code": 50003,
            "message": "Graph visualization service not available",
        }), 503

    tenant_id = request.args.get("tenant_id", "default")
    depth = int(request.args.get("depth", 1))

    db = get_db_session()
    try:
        neighbors = GRAPH_BUILDER.get_node_neighbors(
            db, tenant_id, node_id, node_type, depth
        )
        return jsonify({
            "code": 0,
            "message": "success",
            "data": neighbors
        })
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to get node neighbors: {e}")
        return jsonify({
            "code": 50001,
            "message": f"Failed to get neighbors: {str(e)}"
        }), 500
    finally:
        db.close()


# ============================================
# Phase 1 P1: AI Metadata Enhancement APIs
# ============================================

@app.route("/api/v1/metadata/ai/annotate/column", methods=["POST"])
@require_jwt()
def ai_annotate_column():
    """
    AI 标注单个列
    使用 AI 增强能力自动生成列描述、识别敏感字段、生成语义标签
    """
    if not AI_ANNOTATION_ENABLED:
        return jsonify({
            "code": 50003,
            "message": "AI annotation service not available",
            "error": "ai_annotation_not_enabled"
        }), 503

    data = request.json or {}
    column_name = data.get("column_name")
    column_type = data.get("column_type", "varchar")
    table_name = data.get("table_name")
    database_name = data.get("database_name")
    sample_values = data.get("sample_values")
    use_llm = data.get("use_llm", True)
    save_to_db = data.get("save_to_db", False)

    if not column_name:
        return jsonify({"code": 40001, "message": "column_name is required"}), 400

    try:
        service = get_ai_annotation_service()
        result = service.annotate_column(
            column_name=column_name,
            column_type=column_type,
            table_name=table_name,
            sample_values=sample_values,
            use_llm=use_llm,
        )

        # 如果需要保存到数据库
        if save_to_db and database_name and table_name:
            db = get_db_session()
            try:
                column = db.query(MetadataColumn).filter(
                    MetadataColumn.database_name == database_name,
                    MetadataColumn.table_name == table_name,
                    MetadataColumn.column_name == column_name
                ).first()

                if column:
                    import json
                    column.ai_description = result.get("ai_description")
                    column.sensitivity_level = result.get("sensitivity_level")
                    column.sensitivity_type = result.get("sensitivity_type")
                    column.semantic_tags = json.dumps(result.get("semantic_tags", []))
                    column.ai_annotated_at = datetime.utcnow()
                    column.ai_confidence = result.get("ai_confidence")
                    db.commit()
                    result["saved_to_db"] = True
                else:
                    result["saved_to_db"] = False
                    result["save_error"] = "Column not found in database"
            except Exception as e:
                db.rollback()
                result["saved_to_db"] = False
                result["save_error"] = str(e)
            finally:
                db.close()

        return jsonify({
            "code": 0,
            "message": "success",
            "data": result
        })

    except Exception as e:
        return jsonify({
            "code": 50001,
            "message": f"AI annotation failed: {str(e)}"
        }), 500


@app.route("/api/v1/metadata/ai/annotate/table", methods=["POST"])
@require_jwt()
def ai_annotate_table():
    """
    AI 批量标注表的所有列
    为表中的所有列自动生成描述、识别敏感字段
    """
    if not AI_ANNOTATION_ENABLED:
        return jsonify({
            "code": 50003,
            "message": "AI annotation service not available",
            "error": "ai_annotation_not_enabled"
        }), 503

    data = request.json or {}
    database_name = data.get("database_name")
    table_name = data.get("table_name")
    use_llm = data.get("use_llm", True)
    save_to_db = data.get("save_to_db", False)

    if not database_name or not table_name:
        return jsonify({
            "code": 40001,
            "message": "database_name and table_name are required"
        }), 400

    db = get_db_session()
    try:
        # 获取表的列信息
        columns = db.query(MetadataColumn).filter(
            MetadataColumn.database_name == database_name,
            MetadataColumn.table_name == table_name
        ).order_by(MetadataColumn.position).all()

        if not columns:
            return jsonify({
                "code": 40401,
                "message": f"Table {database_name}.{table_name} not found or has no columns"
            }), 404

        # 准备列信息
        column_list = [
            {"name": c.column_name, "type": c.column_type}
            for c in columns
        ]

        # 调用 AI 标注服务
        service = get_ai_annotation_service()
        results = service.annotate_table(
            table_name=table_name,
            columns=column_list,
            sample_data=None,  # TODO: 可以从实际表中获取样本数据
            use_llm=use_llm,
        )

        # 如果需要保存到数据库
        saved_count = 0
        if save_to_db:
            import json
            for result in results:
                col_name = result.get("column_name")
                column = next((c for c in columns if c.column_name == col_name), None)
                if column:
                    column.ai_description = result.get("ai_description")
                    column.sensitivity_level = result.get("sensitivity_level")
                    column.sensitivity_type = result.get("sensitivity_type")
                    column.semantic_tags = json.dumps(result.get("semantic_tags", []))
                    column.ai_annotated_at = datetime.utcnow()
                    column.ai_confidence = result.get("ai_confidence")
                    saved_count += 1
            db.commit()

        # 生成敏感字段报告
        report = service.get_sensitivity_report(results)

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "table": f"{database_name}.{table_name}",
                "annotations": results,
                "sensitivity_report": report,
                "saved_count": saved_count if save_to_db else None
            }
        })

    except Exception as e:
        db.rollback()
        return jsonify({
            "code": 50001,
            "message": f"AI annotation failed: {str(e)}"
        }), 500
    finally:
        db.close()


@app.route("/api/v1/metadata/ai/sensitivity-report", methods=["GET"])
@require_jwt(optional=True)
def get_sensitivity_report():
    """
    获取敏感字段报告
    返回已标注列的敏感字段统计信息
    """
    database_name = request.args.get("database")
    table_name = request.args.get("table")

    db = get_db_session()
    try:
        query = db.query(MetadataColumn).filter(
            MetadataColumn.ai_annotated_at.isnot(None)
        )

        if database_name:
            query = query.filter(MetadataColumn.database_name == database_name)
        if table_name:
            query = query.filter(MetadataColumn.table_name == table_name)

        columns = query.all()

        if not columns:
            return jsonify({
                "code": 0,
                "message": "success",
                "data": {
                    "total_columns": 0,
                    "sensitive_columns": 0,
                    "message": "No annotated columns found"
                }
            })

        # 构建统计报告
        import json
        annotations = []
        for col in columns:
            annotations.append({
                "column_name": col.column_name,
                "table_name": col.table_name,
                "database_name": col.database_name,
                "sensitivity_type": col.sensitivity_type,
                "sensitivity_level": col.sensitivity_level,
                "semantic_tags": json.loads(col.semantic_tags) if col.semantic_tags else [],
                "ai_confidence": col.ai_confidence,
            })

        # 使用 AI 服务生成报告
        if AI_ANNOTATION_ENABLED:
            service = get_ai_annotation_service()
            report = service.get_sensitivity_report(annotations)
        else:
            # 手动生成简单报告
            report = {
                "total_columns": len(annotations),
                "sensitive_columns": sum(1 for a in annotations if a.get("sensitivity_type") != "none"),
                "by_type": {},
                "by_level": {},
            }
            for ann in annotations:
                sens_type = ann.get("sensitivity_type", "none")
                sens_level = ann.get("sensitivity_level", "public")
                if sens_type != "none":
                    if sens_type not in report["by_type"]:
                        report["by_type"][sens_type] = []
                    report["by_type"][sens_type].append(f"{ann['database_name']}.{ann['table_name']}.{ann['column_name']}")
                report["by_level"][sens_level] = report["by_level"].get(sens_level, 0) + 1

        # 添加详细的列表信息
        report["columns"] = annotations

        return jsonify({
            "code": 0,
            "message": "success",
            "data": report
        })

    finally:
        db.close()


@app.route("/api/v1/metadata/ai/batch-annotate", methods=["POST"])
@require_jwt()
def ai_batch_annotate():
    """
    批量 AI 标注多个表
    支持一次性标注多个表的所有列
    """
    if not AI_ANNOTATION_ENABLED:
        return jsonify({
            "code": 50003,
            "message": "AI annotation service not available",
            "error": "ai_annotation_not_enabled"
        }), 503

    data = request.json or {}
    tables = data.get("tables", [])  # [{"database": "db1", "table": "t1"}, ...]
    use_llm = data.get("use_llm", True)
    save_to_db = data.get("save_to_db", False)

    if not tables:
        return jsonify({
            "code": 40001,
            "message": "tables list is required"
        }), 400

    results = []
    total_columns = 0
    total_sensitive = 0
    service = get_ai_annotation_service()

    db = get_db_session()
    try:
        for table_spec in tables:
            database_name = table_spec.get("database")
            table_name = table_spec.get("table")

            if not database_name or not table_name:
                continue

            # 获取列信息
            columns = db.query(MetadataColumn).filter(
                MetadataColumn.database_name == database_name,
                MetadataColumn.table_name == table_name
            ).all()

            if not columns:
                results.append({
                    "table": f"{database_name}.{table_name}",
                    "status": "skipped",
                    "message": "Table not found or has no columns"
                })
                continue

            # 标注
            column_list = [{"name": c.column_name, "type": c.column_type} for c in columns]
            annotations = service.annotate_table(
                table_name=table_name,
                columns=column_list,
                use_llm=use_llm,
            )

            # 统计
            sensitive_count = sum(1 for a in annotations if a.get("sensitivity_type") != "none")
            total_columns += len(annotations)
            total_sensitive += sensitive_count

            # 保存到数据库
            if save_to_db:
                import json
                for ann in annotations:
                    col = next((c for c in columns if c.column_name == ann.get("column_name")), None)
                    if col:
                        col.ai_description = ann.get("ai_description")
                        col.sensitivity_level = ann.get("sensitivity_level")
                        col.sensitivity_type = ann.get("sensitivity_type")
                        col.semantic_tags = json.dumps(ann.get("semantic_tags", []))
                        col.ai_annotated_at = datetime.utcnow()
                        col.ai_confidence = ann.get("ai_confidence")

            results.append({
                "table": f"{database_name}.{table_name}",
                "status": "success",
                "columns_count": len(annotations),
                "sensitive_count": sensitive_count,
            })

        if save_to_db:
            db.commit()

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "results": results,
                "summary": {
                    "tables_processed": len([r for r in results if r.get("status") == "success"]),
                    "total_columns": total_columns,
                    "total_sensitive": total_sensitive,
                    "saved_to_db": save_to_db
                }
            }
        })

    except Exception as e:
        db.rollback()
        return jsonify({
            "code": 50001,
            "message": f"Batch annotation failed: {str(e)}"
        }), 500
    finally:
        db.close()


@app.route("/api/v1/metadata/ai/status", methods=["GET"])
@require_jwt(optional=True)
def get_ai_annotation_status():
    """
    获取 AI 标注服务状态
    返回服务配置和可用性信息
    """
    status_info = {
        "enabled": AI_ANNOTATION_ENABLED,
        "service_available": False,
        "llm_configured": False,
        "model": None,
        "api_url": None,
    }

    if AI_ANNOTATION_ENABLED:
        try:
            service = get_ai_annotation_service()
            status_info["service_available"] = True
            status_info["llm_configured"] = service.enabled
            status_info["model"] = service.model
            status_info["api_url"] = service.api_url
        except Exception as e:
            status_info["error"] = str(e)

    return jsonify({
        "code": 0,
        "message": "success",
        "data": status_info
    })


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

# Import Kettle bridge for ETL engine integration
try:
    from src.kettle_bridge import get_kettle_bridge, KettleBridge
    KETTLE_ENABLED = True
except ImportError:
    KETTLE_ENABLED = False
    import logging
    logging.getLogger(__name__).warning(
        "Kettle bridge not available. Kettle ETL features will be disabled. "
        "For Kettle support, ensure src/kettle_bridge.py is available."
    )

# Import AI annotation service for Phase 1 P1
try:
    from src.ai_annotation import get_ai_annotation_service, AIAnnotationService
    AI_ANNOTATION_ENABLED = True
except ImportError:
    AI_ANNOTATION_ENABLED = False
    import logging
    logging.getLogger(__name__).warning(
        "AI annotation service not available. AI metadata enhancement features will be disabled. "
        "For AI annotation support, ensure src/ai_annotation.py is available."
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
# Kettle ETL Engine APIs
# 基于 Data 平台原生 Kettle (Pentaho Data Integration) 能力
# ============================================

@app.route("/api/v1/kettle/status", methods=["GET"])
@require_jwt(optional=True)
def get_kettle_status():
    """
    获取 Kettle 服务状态
    返回 Kettle 安装信息和可用性
    """
    if not KETTLE_ENABLED:
        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "enabled": False,
                "message": "Kettle bridge not available",
                "kettle_installed": False
            }
        })

    try:
        kettle = get_kettle_bridge()
        status = kettle.get_status()
        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "enabled": True,
                **status
            }
        })
    except Exception as e:
        return jsonify({
            "code": 50001,
            "message": f"Failed to get Kettle status: {str(e)}"
        }), 500


# ==================== Hop Server 状态 API ====================

@app.route("/api/v1/etl/hop-status", methods=["GET"])
@require_jwt(optional=True)
def get_hop_status():
    """
    获取 Hop Server 状态
    返回 Hop 安装信息、已注册 Pipeline 和 Workflow 列表
    """
    try:
        from services.kettle_orchestration_service import get_kettle_orchestration_service
        service = get_kettle_orchestration_service()
        status = service.get_hop_status()
        return jsonify({
            "code": 0,
            "message": "success",
            "data": status
        })
    except Exception as e:
        return jsonify({
            "code": 50001,
            "message": f"Failed to get Hop status: {str(e)}"
        }), 500


@app.route("/api/v1/etl/engines", methods=["GET"])
@require_jwt(optional=True)
def get_etl_engines():
    """
    获取所有可用的 ETL 引擎及其状态
    返回 Kettle 和 Hop 引擎的可用性和健康状态
    """
    try:
        from services.kettle_orchestration_service import get_kettle_orchestration_service
        service = get_kettle_orchestration_service()
        engines = service.get_available_engines()
        return jsonify({
            "code": 0,
            "message": "success",
            "data": engines
        })
    except Exception as e:
        return jsonify({
            "code": 50001,
            "message": f"Failed to get ETL engines: {str(e)}"
        }), 500


@app.route("/api/v1/kettle/jobs/execute", methods=["POST"])
@require_jwt()
def execute_kettle_job():
    """
    执行 Kettle 作业 (.kjb)
    支持文件模式和仓库模式
    """
    if not KETTLE_ENABLED:
        return jsonify({
            "code": 50003,
            "message": "Kettle engine not available",
            "error": "kettle_not_enabled"
        }), 503

    data = request.json or {}

    # 验证参数
    job_path = data.get("job_path")
    repository = data.get("repository")
    job_name = data.get("job_name")

    if not job_path and not (repository and job_name):
        return jsonify({
            "code": 40001,
            "message": "Must provide either job_path or repository/job_name"
        }), 400

    try:
        kettle = get_kettle_bridge()

        # 如果提供了文件路径，先验证
        if job_path:
            is_valid, error = kettle.validate_job_file(job_path)
            if not is_valid:
                return jsonify({
                    "code": 40002,
                    "message": f"Invalid job file: {error}"
                }), 400

        # 执行作业
        result = kettle.execute_job(
            job_path=job_path,
            repository=repository,
            directory=data.get("directory"),
            job_name=job_name,
            params=data.get("params"),
            log_level=data.get("log_level", "Basic")
        )

        return jsonify({
            "code": 0 if result.success else 50002,
            "message": "success" if result.success else "Job execution failed",
            "data": result.to_dict()
        }), 200 if result.success else 500

    except Exception as e:
        return jsonify({
            "code": 50001,
            "message": f"Kettle job execution error: {str(e)}"
        }), 500


@app.route("/api/v1/kettle/transformations/execute", methods=["POST"])
@require_jwt()
def execute_kettle_transformation():
    """
    执行 Kettle 转换 (.ktr)
    支持文件模式和仓库模式
    """
    if not KETTLE_ENABLED:
        return jsonify({
            "code": 50003,
            "message": "Kettle engine not available",
            "error": "kettle_not_enabled"
        }), 503

    data = request.json or {}

    # 验证参数
    trans_path = data.get("trans_path")
    repository = data.get("repository")
    trans_name = data.get("trans_name")

    if not trans_path and not (repository and trans_name):
        return jsonify({
            "code": 40001,
            "message": "Must provide either trans_path or repository/trans_name"
        }), 400

    try:
        kettle = get_kettle_bridge()

        # 如果提供了文件路径，先验证
        if trans_path:
            is_valid, error = kettle.validate_transformation_file(trans_path)
            if not is_valid:
                return jsonify({
                    "code": 40002,
                    "message": f"Invalid transformation file: {error}"
                }), 400

        # 执行转换
        result = kettle.execute_transformation(
            trans_path=trans_path,
            repository=repository,
            directory=data.get("directory"),
            trans_name=trans_name,
            params=data.get("params"),
            log_level=data.get("log_level", "Basic")
        )

        return jsonify({
            "code": 0 if result.success else 50002,
            "message": "success" if result.success else "Transformation execution failed",
            "data": result.to_dict()
        }), 200 if result.success else 500

    except Exception as e:
        return jsonify({
            "code": 50001,
            "message": f"Kettle transformation execution error: {str(e)}"
        }), 500


@app.route("/api/v1/kettle/validate/job", methods=["POST"])
@require_jwt(optional=True)
def validate_kettle_job():
    """验证 Kettle 作业文件 (.kjb)"""
    if not KETTLE_ENABLED:
        return jsonify({
            "code": 50003,
            "message": "Kettle engine not available"
        }), 503

    data = request.json or {}
    job_path = data.get("job_path")

    if not job_path:
        return jsonify({
            "code": 40001,
            "message": "job_path is required"
        }), 400

    try:
        kettle = get_kettle_bridge()
        is_valid, error = kettle.validate_job_file(job_path)

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "is_valid": is_valid,
                "error": error,
                "file_path": job_path
            }
        })
    except Exception as e:
        return jsonify({
            "code": 50001,
            "message": f"Validation error: {str(e)}"
        }), 500


@app.route("/api/v1/kettle/validate/transformation", methods=["POST"])
@require_jwt(optional=True)
def validate_kettle_transformation():
    """验证 Kettle 转换文件 (.ktr)"""
    if not KETTLE_ENABLED:
        return jsonify({
            "code": 50003,
            "message": "Kettle engine not available"
        }), 503

    data = request.json or {}
    trans_path = data.get("trans_path")

    if not trans_path:
        return jsonify({
            "code": 40001,
            "message": "trans_path is required"
        }), 400

    try:
        kettle = get_kettle_bridge()
        is_valid, error = kettle.validate_transformation_file(trans_path)

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "is_valid": is_valid,
                "error": error,
                "file_path": trans_path
            }
        })
    except Exception as e:
        return jsonify({
            "code": 50001,
            "message": f"Validation error: {str(e)}"
        }), 500


@app.route("/api/v1/etl/tasks/<task_id>/execute-kettle", methods=["POST"])
@require_jwt()
def execute_etl_task_with_kettle(task_id):
    """
    使用 Kettle 引擎执行 ETL 任务
    仅适用于 engine_type='kettle' 的任务
    """
    if not KETTLE_ENABLED:
        return jsonify({
            "code": 50003,
            "message": "Kettle engine not available"
        }), 503

    db = get_db_session()
    try:
        task = db.query(ETLTask).filter(ETLTask.task_id == task_id).first()
        if not task:
            return jsonify({"code": 40401, "message": "Task not found"}), 404

        # 验证任务引擎类型
        if task.engine_type != "kettle":
            return jsonify({
                "code": 40002,
                "message": f"Task engine type is '{task.engine_type}', not 'kettle'"
            }), 400

        if task.status == "running":
            return jsonify({
                "code": 40002,
                "message": "Task is already running"
            }), 400

        # 检查 Kettle 配置
        if not task.kettle_job_path and not task.kettle_trans_path:
            if not (task.kettle_repository and (task.kettle_job_path or task.kettle_trans_path)):
                return jsonify({
                    "code": 40003,
                    "message": "Kettle job/transformation path or repository not configured"
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

        # 执行 Kettle 任务
        kettle = get_kettle_bridge()
        params = task.kettle_params or {}

        # 根据配置决定执行作业还是转换
        if task.kettle_job_path:
            result = kettle.execute_job(
                job_path=task.kettle_job_path,
                repository=task.kettle_repository,
                directory=task.kettle_directory,
                params=params,
                log_level="Basic"
            )
        elif task.kettle_trans_path:
            result = kettle.execute_transformation(
                trans_path=task.kettle_trans_path,
                repository=task.kettle_repository,
                directory=task.kettle_directory,
                params=params,
                log_level="Basic"
            )
        else:
            # 仓库模式（需要 job_name 或 trans_name 配置）
            return jsonify({
                "code": 40003,
                "message": "Repository mode requires job_name or trans_name in kettle_params"
            }), 400

        # 更新执行结果
        log.finished_at = datetime.utcnow()
        log.duration_seconds = int(result.duration_seconds)
        log.rows_read = result.rows_read
        log.rows_written = result.rows_written
        log.rows_failed = result.rows_error
        log.log_content = result.stdout[:10000] if result.stdout else None  # 限制日志长度

        if result.success:
            log.status = "completed"
            task.status = "completed"
            task.last_success_at = datetime.utcnow()
            task.success_count = (task.success_count or 0) + 1
            task.last_row_count = result.rows_written
            task.last_duration_seconds = int(result.duration_seconds)
            task.last_error = None
        else:
            log.status = "failed"
            log.error_message = result.error_message
            log.error_stack = result.stderr[:5000] if result.stderr else None
            task.status = "failed"
            task.fail_count = (task.fail_count or 0) + 1
            task.last_error = result.error_message

        db.commit()

        return jsonify({
            "code": 0 if result.success else 50002,
            "message": "success" if result.success else "Kettle execution failed",
            "data": {
                "task_id": task_id,
                "log_id": log_id,
                "status": log.status,
                "execution_result": result.to_dict()
            }
        }), 200 if result.success else 500

    except Exception as e:
        db.rollback()
        # 尝试更新任务状态为失败
        try:
            task = db.query(ETLTask).filter(ETLTask.task_id == task_id).first()
            if task:
                task.status = "failed"
                task.last_error = str(e)
                db.commit()
        except:
            pass
        return jsonify({"code": 50001, "message": str(e)}), 500
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


# ==================== 增强数据质量 API ====================

@app.route("/api/v1/quality/enhanced/execute-rule", methods=["POST"])
@require_jwt()
def execute_enhanced_quality_rule():
    """
    执行增强质量规则
    支持更多规则类型和详细结果
    """
    db = next(get_db())
    data = request.json

    try:
        from services.enhanced_quality_service import (
            get_enhanced_quality_engine,
            QualityRuleDefinition,
            QualityRuleType,
            QualitySeverity,
        )

        engine = get_enhanced_quality_engine(db)

        rule = QualityRuleDefinition(
            rule_id=data.get("rule_id", f"rule_{secrets.token_hex(8)}"),
            name=data.get("name", "质量规则"),
            rule_type=QualityRuleType(data.get("rule_type", "null_check")),
            description=data.get("description", ""),
            target_database=data.get("target_database", ""),
            target_table=data.get("target_table", ""),
            target_column=data.get("target_column", ""),
            reference_table=data.get("reference_table", ""),
            reference_column=data.get("reference_column", ""),
            rule_expression=data.get("rule_expression", ""),
            threshold=data.get("threshold", 100.0),
            severity=QualitySeverity(data.get("severity", "warning")),
            config=data.get("config", {}),
            enabled=data.get("enabled", True),
        )

        result = engine.execute_rule(rule)

        return jsonify({
            "code": 0,
            "message": "success",
            "data": result.to_dict()
        })

    except Exception as e:
        logger.error(f"执行增强质量规则失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/quality/enhanced/execute-batch", methods=["POST"])
@require_jwt()
def execute_enhanced_quality_batch():
    """
    批量执行质量规则
    """
    db = next(get_db())
    data = request.json

    try:
        from services.enhanced_quality_service import (
            get_enhanced_quality_engine,
            QualityRuleDefinition,
            QualityRuleType,
            QualitySeverity,
        )

        engine = get_enhanced_quality_engine(db)

        rules_data = data.get("rules", [])
        rules = []

        for rule_data in rules_data:
            rule = QualityRuleDefinition(
                rule_id=rule_data.get("rule_id", f"rule_{secrets.token_hex(8)}"),
                name=rule_data.get("name", "质量规则"),
                rule_type=QualityRuleType(rule_data.get("rule_type", "null_check")),
                description=rule_data.get("description", ""),
                target_database=rule_data.get("target_database", ""),
                target_table=rule_data.get("target_table", ""),
                target_column=rule_data.get("target_column", ""),
                reference_table=rule_data.get("reference_table", ""),
                reference_column=rule_data.get("reference_column", ""),
                rule_expression=rule_data.get("rule_expression", ""),
                threshold=rule_data.get("threshold", 100.0),
                severity=QualitySeverity(rule_data.get("severity", "warning")),
                config=rule_data.get("config", {}),
                enabled=rule_data.get("enabled", True),
            )
            rules.append(rule)

        results = engine.execute_rules_batch(rules)

        # 计算综合分数
        weights = data.get("weights")
        overall_score = engine.calculate_overall_score(results, weights)

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "results": [r.to_dict() for r in results],
                "overall_score": round(overall_score, 2),
                "total_rules": len(results),
                "passed_rules": sum(1 for r in results if r.passed),
                "failed_rules": sum(1 for r in results if not r.passed),
            }
        })

    except Exception as e:
        logger.error(f"批量执行质量规则失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/quality/enhanced/trends/<table_id>", methods=["GET"])
@require_jwt()
def get_quality_trends(table_id):
    """
    获取质量趋势分析
    """
    db = next(get_db())

    try:
        from services.enhanced_quality_service import get_enhanced_quality_engine

        engine = get_enhanced_quality_engine(db)

        period = request.args.get("period", "daily")
        days = int(request.args.get("days", 30))

        trend = engine.analyze_quality_trend(table_id, period, days)

        return jsonify({
            "code": 0,
            "message": "success",
            "data": trend.to_dict()
        })

    except Exception as e:
        logger.error(f"获取质量趋势失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/quality/enhanced/anomalies/detect", methods=["POST"])
@require_jwt()
def detect_quality_anomalies():
    """
    检测质量异常
    """
    db = next(get_db())
    data = request.json

    try:
        from services.enhanced_quality_service import get_enhanced_quality_engine

        engine = get_enhanced_quality_engine(db)

        table_id = data.get("table_id")
        current_score = data.get("current_score")
        historical_scores = data.get("historical_scores", [])
        threshold_std = data.get("threshold_std", 2.0)

        if not all([table_id, current_score is not None]):
            return jsonify({
                "code": 40001,
                "message": "table_id 和 current_score 不能为空"
            }), 400

        anomalies = engine.detect_quality_anomalies(
            table_id, current_score, historical_scores, threshold_std
        )

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "anomalies": [a.to_dict() for a in anomalies],
                "count": len(anomalies),
            }
        })

    except Exception as e:
        logger.error(f"检测质量异常失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/quality/enhanced/score/calculate", methods=["POST"])
@require_jwt()
def calculate_quality_score():
    """
    计算综合质量分数
    支持自定义权重
    """
    db = next(get_db())
    data = request.json

    try:
        from services.enhanced_quality_service import (
            get_enhanced_quality_engine,
            QualityRuleDefinition,
            QualityRuleType,
            QualitySeverity,
        )

        engine = get_enhanced_quality_engine(db)

        rules_data = data.get("rules", [])
        weights = data.get("weights")

        rules = []
        for rule_data in rules_data:
            rule = QualityRuleDefinition(
                rule_id=rule_data.get("rule_id", f"rule_{secrets.token_hex(8)}"),
                name=rule_data.get("name", "质量规则"),
                rule_type=QualityRuleType(rule_data.get("rule_type", "null_check")),
                description=rule_data.get("description", ""),
                target_database=rule_data.get("target_database", ""),
                target_table=rule_data.get("target_table", ""),
                target_column=rule_data.get("target_column", ""),
                reference_table=rule_data.get("reference_table", ""),
                reference_column=rule_data.get("reference_column", ""),
                rule_expression=rule_data.get("rule_expression", ""),
                threshold=rule_data.get("threshold", 100.0),
                severity=QualitySeverity(rule_data.get("severity", "warning")),
                config=rule_data.get("config", {}),
                enabled=rule_data.get("enabled", True),
            )
            rules.append(rule)

        results = engine.execute_rules_batch(rules)
        overall_score = engine.calculate_overall_score(results, weights)

        # 按类别统计
        category_scores = {}
        for result in results:
            category = engine._get_rule_category(result.rule_type)
            if category not in category_scores:
                category_scores[category] = []
            category_scores[category].append(result.score)

        category_averages = {
            cat: round(statistics.mean(scores), 2)
            for cat, scores in category_scores.items()
        }

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "overall_score": round(overall_score, 2),
                "category_scores": category_averages,
                "rule_count": len(results),
                "passed_count": sum(1 for r in results if r.passed),
            }
        })

    except Exception as e:
        logger.error(f"计算质量分数失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/quality/enhanced/rules/templates", methods=["GET"])
@require_jwt()
def get_quality_rule_templates():
    """
    获取质量规则模板
    """
    try:
        from services.enhanced_quality_service import QualityRuleType

        templates = [
            {
                "rule_type": "null_check",
                "name": "空值检查",
                "description": "检查列中的空值比例",
                "config_template": {
                    "sample_rows": {"type": "integer", "default": 10000},
                    "null_ratio": {"type": "float", "default": 0.0},
                },
            },
            {
                "rule_type": "duplicate_check",
                "name": "重复值检查",
                "description": "检查列中的重复值",
                "config_template": {
                    "sample_rows": {"type": "integer", "default": 10000},
                    "duplicate_ratio": {"type": "float", "default": 0.0},
                },
            },
            {
                "rule_type": "range_check",
                "name": "范围检查",
                "description": "检查数值是否在指定范围内",
                "config_template": {
                    "min_value": {"type": "number", "required": True},
                    "max_value": {"type": "number", "required": True},
                },
            },
            {
                "rule_type": "pattern_check",
                "name": "正则模式检查",
                "description": "检查值是否匹配正则表达式",
                "config_template": {
                    "pattern": {"type": "string", "required": True},
                },
            },
            {
                "rule_type": "enum_check",
                "name": "枚举值检查",
                "description": "检查值是否在允许的枚举列表中",
                "config_template": {
                    "allowed_values": {"type": "array", "required": True},
                },
            },
            {
                "rule_type": "reference_check",
                "name": "引用完整性检查",
                "description": "检查外键引用的有效性",
                "config_template": {
                    "reference_table": {"type": "string", "required": True},
                    "reference_column": {"type": "string", "required": True},
                },
            },
            {
                "rule_type": "cross_table",
                "name": "跨表一致性检查",
                "description": "检查两个表之间的数据一致性",
                "config_template": {
                    "reference_table": {"type": "string", "required": True},
                    "reference_column": {"type": "string", "required": True},
                },
            },
            {
                "rule_type": "statistical",
                "name": "统计异常检测",
                "description": "使用统计方法检测异常值",
                "config_template": {
                    "statistical_method": {"type": "string", "enum": ["iqr", "zscore"], "default": "iqr"},
                    "threshold": {"type": "float", "default": 3.0},
                },
            },
            {
                "rule_type": "timeliness",
                "name": "及时性检查",
                "description": "检查数据更新是否及时",
                "config_template": {
                    "max_delay_hours": {"type": "integer", "default": 24},
                },
            },
        ]

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "templates": templates,
                "total": len(templates),
            }
        })

    except Exception as e:
        logger.error(f"获取规则模板失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


# ============================================
# Great Expectations Integration APIs
# ============================================

@app.route("/api/v1/quality/enhanced/ge-status", methods=["GET"])
@require_jwt(optional=True)
def get_ge_status():
    """
    获取 Great Expectations 集成状态
    """
    try:
        from integrations.great_expectations import GEValidationEngine
        engine = GEValidationEngine()
        return jsonify({
            "code": 0,
            "message": "success",
            "data": engine.get_status()
        })
    except ImportError:
        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "ge_installed": False,
                "enabled": False,
                "context_initialized": False,
            }
        })
    except Exception as e:
        logger.error(f"获取 GE 状态失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/quality/enhanced/data-docs", methods=["POST"])
@require_jwt()
def generate_ge_data_docs():
    """
    生成 Great Expectations Data Docs（HTML 质量报告）
    """
    try:
        from integrations.great_expectations import GEValidationEngine
        engine = GEValidationEngine()

        if not engine.available:
            return jsonify({
                "code": 40003,
                "message": "Great Expectations is not enabled or not installed",
            }), 400

        docs_path = engine.generate_data_docs()

        if docs_path:
            return jsonify({
                "code": 0,
                "message": "success",
                "data": {
                    "docs_path": docs_path,
                    "status": "generated",
                }
            })
        else:
            return jsonify({
                "code": 50001,
                "message": "Failed to generate Data Docs",
            }), 500

    except ImportError:
        return jsonify({
            "code": 40003,
            "message": "Great Expectations is not installed",
        }), 400
    except Exception as e:
        logger.error(f"生成 GE Data Docs 失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


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
# P1: AI 增强血缘分析 APIs
# ============================================

@app.route("/api/v1/lineage/parse-sql", methods=["POST"])
@require_jwt(optional=True)
def parse_sql_lineage():
    """
    解析 SQL 语句提取血缘关系
    请求体:
    - sql: SQL 语句 (必需)
    - source_database: 默认数据库名 (可选)
    - use_ai: 是否使用 AI 增强解析 (可选，默认 true)
    """
    try:
        from src.lineage_analyzer import get_lineage_analyzer
    except ImportError as e:
        return jsonify({
            "code": 500,
            "message": f"血缘分析服务不可用: {str(e)}"
        }), 500

    data = request.get_json() or {}
    sql = data.get("sql")

    if not sql:
        return jsonify({
            "code": 400,
            "message": "缺少必需参数: sql"
        }), 400

    source_database = data.get("source_database")
    use_ai = data.get("use_ai", True)

    try:
        analyzer = get_lineage_analyzer()
        result = analyzer.parse_sql_lineage(sql, source_database, use_ai)

        return jsonify({
            "code": 0,
            "message": "success",
            "data": result
        })
    except Exception as e:
        return jsonify({
            "code": 500,
            "message": f"SQL 血缘解析失败: {str(e)}"
        }), 500


@app.route("/api/v1/lineage/analyze-etl", methods=["POST"])
@require_jwt(optional=True)
def analyze_etl_lineage():
    """
    分析 ETL 任务的血缘关系
    请求体:
    - etl_config: ETL 任务配置 (必需)
    - task_type: 任务类型 (可选，默认 batch)
    """
    try:
        from src.lineage_analyzer import get_lineage_analyzer
    except ImportError as e:
        return jsonify({
            "code": 500,
            "message": f"血缘分析服务不可用: {str(e)}"
        }), 500

    data = request.get_json() or {}
    etl_config = data.get("etl_config")

    if not etl_config:
        return jsonify({
            "code": 400,
            "message": "缺少必需参数: etl_config"
        }), 400

    task_type = data.get("task_type", "batch")

    try:
        analyzer = get_lineage_analyzer()
        result = analyzer.analyze_etl_lineage(etl_config, task_type)

        return jsonify({
            "code": 0,
            "message": "success",
            "data": result
        })
    except Exception as e:
        return jsonify({
            "code": 500,
            "message": f"ETL 血缘分析失败: {str(e)}"
        }), 500


@app.route("/api/v1/lineage/ai-impact-analysis", methods=["POST"])
@require_jwt(optional=True)
def ai_impact_analysis():
    """
    AI 驱动的影响分析
    请求体:
    - node_info: 源节点信息 (必需)
    - downstream_nodes: 下游节点列表 (可选，为空时自动查询)
    - change_type: 变更类型 (可选，默认 schema_change)
    """
    try:
        from src.lineage_analyzer import get_lineage_analyzer
    except ImportError as e:
        return jsonify({
            "code": 500,
            "message": f"血缘分析服务不可用: {str(e)}"
        }), 500

    data = request.get_json() or {}
    node_info = data.get("node_info")

    if not node_info:
        return jsonify({
            "code": 400,
            "message": "缺少必需参数: node_info"
        }), 400

    downstream_nodes = data.get("downstream_nodes", [])
    change_type = data.get("change_type", "schema_change")

    # 如果没有提供下游节点，自动查询
    if not downstream_nodes:
        db = get_db_session()
        try:
            full_name = node_info.get("full_name") or node_info.get("name")
            if full_name:
                # 查找所有下游节点
                edges = db.query(LineageEdge).filter(
                    LineageEdge.source_name == full_name,
                    LineageEdge.is_active == True
                ).all()

                for edge in edges:
                    target_node = db.query(LineageNode).filter(
                        LineageNode.node_id == edge.target_node_id
                    ).first()
                    if target_node:
                        downstream_nodes.append({
                            "node_id": target_node.node_id,
                            "name": target_node.name,
                            "full_name": target_node.full_name,
                            "node_type": target_node.node_type,
                            "impact_level": 1
                        })
        finally:
            db.close()

    try:
        analyzer = get_lineage_analyzer()
        result = analyzer.ai_impact_analysis(node_info, downstream_nodes, change_type)

        return jsonify({
            "code": 0,
            "message": "success",
            "data": result
        })
    except Exception as e:
        return jsonify({
            "code": 500,
            "message": f"AI 影响分析失败: {str(e)}"
        }), 500


@app.route("/api/v1/lineage/infer-columns", methods=["POST"])
@require_jwt(optional=True)
def infer_column_lineage():
    """
    推断列级血缘关系
    请求体:
    - sql: SQL 语句 (必需)
    - source_columns: 源表列信息 {"table_name": ["col1", "col2"]} (可选)
    - use_ai: 是否使用 AI (可选，默认 true)
    """
    try:
        from src.lineage_analyzer import get_lineage_analyzer
    except ImportError as e:
        return jsonify({
            "code": 500,
            "message": f"血缘分析服务不可用: {str(e)}"
        }), 500

    data = request.get_json() or {}
    sql = data.get("sql")

    if not sql:
        return jsonify({
            "code": 400,
            "message": "缺少必需参数: sql"
        }), 400

    source_columns = data.get("source_columns", {})
    use_ai = data.get("use_ai", True)

    try:
        analyzer = get_lineage_analyzer()
        mappings = analyzer.infer_column_lineage(sql, source_columns, use_ai)

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "column_mappings": mappings,
                "total": len(mappings)
            }
        })
    except Exception as e:
        return jsonify({
            "code": 500,
            "message": f"列级血缘推断失败: {str(e)}"
        }), 500


@app.route("/api/v1/lineage/generate-from-sql", methods=["POST"])
@require_jwt(optional=True)
def generate_lineage_from_sql():
    """
    从 SQL 生成并保存血缘关系
    请求体:
    - sql: SQL 语句 (必需)
    - source_database: 默认数据库名 (可选)
    - job_id: 关联的任务 ID (可选)
    - job_type: 任务类型 (可选，默认 sql)
    - save: 是否保存到数据库 (可选，默认 false)
    """
    try:
        from src.lineage_analyzer import get_lineage_analyzer
    except ImportError as e:
        return jsonify({
            "code": 500,
            "message": f"血缘分析服务不可用: {str(e)}"
        }), 500

    data = request.get_json() or {}
    sql = data.get("sql")

    if not sql:
        return jsonify({
            "code": 400,
            "message": "缺少必需参数: sql"
        }), 400

    source_database = data.get("source_database")
    job_id = data.get("job_id")
    job_type = data.get("job_type", "sql")
    save = data.get("save", False)

    try:
        analyzer = get_lineage_analyzer()

        # 解析 SQL
        parse_result = analyzer.parse_sql_lineage(sql, source_database, use_ai=True)

        # 生成节点和边
        nodes, edges = analyzer.generate_lineage_nodes_and_edges(
            parse_result, job_id, job_type
        )

        # 如果需要保存到数据库
        saved_count = {"nodes": 0, "edges": 0}
        if save and (nodes or edges):
            db = get_db_session()
            try:
                from datetime import datetime

                # 保存节点
                for node_data in nodes:
                    existing = db.query(LineageNode).filter(
                        LineageNode.full_name == node_data["full_name"]
                    ).first()

                    if existing:
                        # 更新现有节点
                        existing.updated_at = datetime.utcnow()
                    else:
                        # 创建新节点
                        node = LineageNode(
                            node_id=node_data["node_id"],
                            node_type=node_data["node_type"],
                            name=node_data["name"],
                            full_name=node_data["full_name"],
                            database_name=node_data.get("database_name"),
                            table_name=node_data.get("table_name"),
                            column_name=node_data.get("column_name"),
                            is_active=True,
                            created_at=datetime.utcnow(),
                            updated_at=datetime.utcnow()
                        )
                        db.add(node)
                        saved_count["nodes"] += 1

                # 保存边
                for edge_data in edges:
                    edge = LineageEdge(
                        edge_id=edge_data["edge_id"],
                        source_node_id=edge_data["source_node_id"],
                        source_type=edge_data["source_type"],
                        source_name=edge_data["source_name"],
                        target_node_id=edge_data["target_node_id"],
                        target_type=edge_data["target_type"],
                        target_name=edge_data["target_name"],
                        relation_type=edge_data.get("relation_type", "derive"),
                        transformation=edge_data.get("transformation"),
                        job_id=edge_data.get("job_id"),
                        job_type=edge_data.get("job_type"),
                        confidence=edge_data.get("confidence", 60),
                        is_active=True,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow()
                    )
                    db.add(edge)
                    saved_count["edges"] += 1

                db.commit()
            except Exception as e:
                db.rollback()
                return jsonify({
                    "code": 500,
                    "message": f"保存血缘数据失败: {str(e)}"
                }), 500
            finally:
                db.close()

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "parse_result": parse_result,
                "nodes": nodes,
                "edges": edges,
                "saved": saved_count if save else None
            }
        })
    except Exception as e:
        return jsonify({
            "code": 500,
            "message": f"血缘生成失败: {str(e)}"
        }), 500


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


# ==================== P4.1: Flink 作业管理 ====================

@app.route("/api/v1/flink/jobs", methods=["GET"])
@require_jwt()
def list_flink_jobs():
    """列出 Flink 作业"""
    db = next(get_db())

    try:
        status = request.args.get("status")
        job_type = request.args.get("job_type")
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("page_size", 20))

        query = db.query(FlinkJob)

        if status:
            query = query.filter(FlinkJob.status == status)
        if job_type:
            query = query.filter(FlinkJob.job_type == job_type)

        total = query.count()
        jobs = query.order_by(FlinkJob.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

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
    finally:
        db.close()


@app.route("/api/v1/flink/jobs", methods=["POST"])
@require_jwt()
def create_flink_job():
    """创建 Flink 作业"""
    db = next(get_db())
    data = request.json

    try:
        name = data.get("name")
        if not name:
            return jsonify({"code": 40001, "message": "作业名称不能为空"}), 400

        job = FlinkJob(
            job_id=generate_id("flink_"),
            name=name,
            description=data.get("description", ""),
            job_type=data.get("job_type", "sql"),
            sql_content=data.get("sql_content"),
            jar_path=data.get("jar_path"),
            main_class=data.get("main_class"),
            program_args=data.get("program_args"),
            parallelism=data.get("parallelism", 1),
            checkpoint_interval=data.get("checkpoint_interval", 60000),
            task_manager_memory=data.get("task_manager_memory", "1024m"),
            job_manager_memory=data.get("job_manager_memory", "1024m"),
            task_slots=data.get("task_slots", 1),
            tags=data.get("tags"),
            status="created",
            created_by=data.get("created_by", "system")
        )

        db.add(job)
        db.commit()
        db.refresh(job)

        return jsonify({
            "code": 0,
            "message": "success",
            "data": job.to_dict()
        }), 201
    except Exception as e:
        db.rollback()
        return jsonify({"code": 50001, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/flink/jobs/<job_id>", methods=["GET"])
@require_jwt()
def get_flink_job(job_id):
    """获取 Flink 作业详情"""
    db = next(get_db())

    try:
        job = db.query(FlinkJob).filter(FlinkJob.job_id == job_id).first()
        if not job:
            return jsonify({"code": 40401, "message": "作业不存在"}), 404

        return jsonify({
            "code": 0,
            "message": "success",
            "data": job.to_dict()
        })
    finally:
        db.close()


@app.route("/api/v1/flink/jobs/<job_id>", methods=["PUT"])
@require_jwt()
def update_flink_job(job_id):
    """更新 Flink 作业"""
    db = next(get_db())
    data = request.json

    try:
        job = db.query(FlinkJob).filter(FlinkJob.job_id == job_id).first()
        if not job:
            return jsonify({"code": 40401, "message": "作业不存在"}), 404

        if job.status == "running":
            return jsonify({"code": 40002, "message": "运行中的作业不能修改"}), 400

        if data.get("name"):
            job.name = data["name"]
        if data.get("description") is not None:
            job.description = data["description"]
        if data.get("sql_content"):
            job.sql_content = data["sql_content"]
        if data.get("parallelism"):
            job.parallelism = data["parallelism"]
        if data.get("tags"):
            job.tags = data["tags"]

        db.commit()
        db.refresh(job)

        return jsonify({
            "code": 0,
            "message": "success",
            "data": job.to_dict()
        })
    except Exception as e:
        db.rollback()
        return jsonify({"code": 50001, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/flink/jobs/<job_id>", methods=["DELETE"])
@require_jwt()
def delete_flink_job(job_id):
    """删除 Flink 作业"""
    db = next(get_db())

    try:
        job = db.query(FlinkJob).filter(FlinkJob.job_id == job_id).first()
        if not job:
            return jsonify({"code": 40401, "message": "作业不存在"}), 404

        if job.status == "running":
            return jsonify({"code": 40002, "message": "运行中的作业不能删除"}), 400

        db.query(FlinkJobLog).filter(FlinkJobLog.job_id == job_id).delete()
        db.delete(job)
        db.commit()

        return jsonify({"code": 0, "message": "success"})
    except Exception as e:
        db.rollback()
        return jsonify({"code": 50001, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/flink/jobs/<job_id>/start", methods=["POST"])
@require_jwt()
def start_flink_job(job_id):
    """启动 Flink 作业"""
    db = next(get_db())

    try:
        job = db.query(FlinkJob).filter(FlinkJob.job_id == job_id).first()
        if not job:
            return jsonify({"code": 40401, "message": "作业不存在"}), 404

        if job.status == "running":
            return jsonify({"code": 40002, "message": "作业已在运行"}), 400

        job.status = "running"
        job.started_at = datetime.utcnow()
        job.flink_job_id = generate_id("fj_")
        db.commit()
        db.refresh(job)

        return jsonify({
            "code": 0,
            "message": "success",
            "data": job.to_dict()
        })
    except Exception as e:
        db.rollback()
        return jsonify({"code": 50001, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/flink/jobs/<job_id>/stop", methods=["POST"])
@require_jwt()
def stop_flink_job(job_id):
    """停止 Flink 作业"""
    db = next(get_db())

    try:
        job = db.query(FlinkJob).filter(FlinkJob.job_id == job_id).first()
        if not job:
            return jsonify({"code": 40401, "message": "作业不存在"}), 404

        if job.status != "running":
            return jsonify({"code": 40002, "message": "作业未在运行"}), 400

        job.status = "stopped"
        job.stopped_at = datetime.utcnow()
        if job.started_at:
            job.duration_seconds = int((job.stopped_at - job.started_at).total_seconds())
        db.commit()
        db.refresh(job)

        return jsonify({
            "code": 0,
            "message": "success",
            "data": job.to_dict()
        })
    except Exception as e:
        db.rollback()
        return jsonify({"code": 50001, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/flink/jobs/<job_id>/logs", methods=["GET"])
@require_jwt()
def get_flink_job_logs(job_id):
    """获取 Flink 作业日志"""
    db = next(get_db())

    try:
        job = db.query(FlinkJob).filter(FlinkJob.job_id == job_id).first()
        if not job:
            return jsonify({"code": 40401, "message": "作业不存在"}), 404

        level = request.args.get("level")
        limit = int(request.args.get("limit", 100))

        query = db.query(FlinkJobLog).filter(FlinkJobLog.job_id == job_id)
        if level:
            query = query.filter(FlinkJobLog.level == level)

        logs = query.order_by(FlinkJobLog.timestamp.desc()).limit(limit).all()

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "logs": [log.to_dict() for log in logs]
            }
        })
    finally:
        db.close()


@app.route("/api/v1/flink/jobs/<job_id>/metrics", methods=["GET"])
@require_jwt()
def get_flink_job_metrics(job_id):
    """获取 Flink 作业指标"""
    db = next(get_db())

    try:
        job = db.query(FlinkJob).filter(FlinkJob.job_id == job_id).first()
        if not job:
            return jsonify({"code": 40401, "message": "作业不存在"}), 404

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "job_id": job_id,
                "status": job.status,
                "records_in": job.records_in,
                "records_out": job.records_out,
                "bytes_in": job.bytes_in,
                "bytes_out": job.bytes_out,
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "duration_seconds": job.duration_seconds
            }
        })
    finally:
        db.close()


# ==================== P4.2: Streaming IDE ====================

@app.route("/api/v1/flink/sql/validate", methods=["POST"])
@require_jwt()
def validate_flink_sql():
    """验证 Flink SQL 语法"""
    data = request.json
    sql = data.get("sql", "")

    if not sql.strip():
        return jsonify({"code": 40001, "message": "SQL 不能为空"}), 400

    # 模拟 SQL 验证（实际应调用 Flink 服务）
    is_valid = True
    error_message = None

    # 简单语法检查
    sql_upper = sql.upper().strip()
    if not any(sql_upper.startswith(kw) for kw in ["SELECT", "INSERT", "CREATE", "DROP", "ALTER", "WITH"]):
        is_valid = False
        error_message = "无效的 SQL 语句，必须以 SELECT/INSERT/CREATE/DROP/ALTER/WITH 开头"

    return jsonify({
        "code": 0,
        "message": "success",
        "data": {
            "is_valid": is_valid,
            "error_message": error_message
        }
    })


@app.route("/api/v1/flink/sql/execute", methods=["POST"])
@require_jwt()
def execute_flink_sql():
    """执行 Flink SQL"""
    db = next(get_db())
    data = request.json

    try:
        sql = data.get("sql", "")
        if not sql.strip():
            return jsonify({"code": 40001, "message": "SQL 不能为空"}), 400

        # 创建执行记录
        job = FlinkJob(
            job_id=generate_id("flink_"),
            name=data.get("name", "Ad-hoc SQL Query"),
            job_type="sql",
            sql_content=sql,
            parallelism=data.get("parallelism", 1),
            status="running",
            started_at=datetime.utcnow(),
            created_by=data.get("created_by", "system")
        )

        db.add(job)
        db.commit()

        # 模拟执行完成
        job.status = "finished"
        job.stopped_at = datetime.utcnow()
        job.duration_seconds = 1
        job.records_out = 100
        db.commit()
        db.refresh(job)

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "job_id": job.job_id,
                "status": job.status,
                "message": "SQL 执行完成"
            }
        })
    except Exception as e:
        db.rollback()
        return jsonify({"code": 50001, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/flink/sql/results/<job_id>", methods=["GET"])
@require_jwt()
def get_flink_sql_results(job_id):
    """获取 Flink SQL 执行结果"""
    db = next(get_db())

    try:
        job = db.query(FlinkJob).filter(FlinkJob.job_id == job_id).first()
        if not job:
            return jsonify({"code": 40401, "message": "执行记录不存在"}), 404

        # 模拟返回结果
        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "job_id": job_id,
                "status": job.status,
                "columns": [{"name": "id", "type": "INT"}, {"name": "value", "type": "STRING"}],
                "rows": [{"id": 1, "value": "sample"}, {"id": 2, "value": "data"}],
                "row_count": job.records_out
            }
        })
    finally:
        db.close()


@app.route("/api/v1/flink/sql/saved", methods=["GET"])
@require_jwt()
def list_flink_saved_queries():
    """列出已保存的 Flink SQL"""
    db = next(get_db())

    try:
        category = request.args.get("category")
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("page_size", 20))

        query = db.query(FlinkSavedQuery)

        if category:
            query = query.filter(FlinkSavedQuery.category == category)

        total = query.count()
        queries = query.order_by(FlinkSavedQuery.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

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
    finally:
        db.close()


@app.route("/api/v1/flink/sql/saved", methods=["POST"])
@require_jwt()
def save_flink_query():
    """保存 Flink SQL 查询"""
    db = next(get_db())
    data = request.json

    try:
        name = data.get("name")
        sql_content = data.get("sql_content")
        if not name or not sql_content:
            return jsonify({"code": 40001, "message": "name 和 sql_content 必填"}), 400

        query = FlinkSavedQuery(
            query_id=generate_id("fsql_"),
            name=name,
            description=data.get("description", ""),
            sql_content=sql_content,
            category=data.get("category"),
            tags=data.get("tags"),
            created_by=data.get("created_by", "system")
        )

        db.add(query)
        db.commit()
        db.refresh(query)

        return jsonify({
            "code": 0,
            "message": "success",
            "data": query.to_dict()
        }), 201
    except Exception as e:
        db.rollback()
        return jsonify({"code": 50001, "message": str(e)}), 500
    finally:
        db.close()


# ==================== P4.3: 特征存储 ====================

@app.route("/api/v1/features", methods=["GET"])
@require_jwt()
def list_features():
    """列出特征"""
    db = next(get_db())

    try:
        group_id = request.args.get("group_id")
        feature_type = request.args.get("feature_type")
        status = request.args.get("status")
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("page_size", 20))

        query = db.query(Feature)

        if group_id:
            query = query.filter(Feature.group_id == group_id)
        if feature_type:
            query = query.filter(Feature.feature_type == feature_type)
        if status:
            query = query.filter(Feature.status == status)

        total = query.count()
        features = query.order_by(Feature.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "features": [f.to_dict() for f in features],
                "total": total,
                "page": page,
                "page_size": page_size
            }
        })
    finally:
        db.close()


@app.route("/api/v1/features", methods=["POST"])
@require_jwt()
def create_feature():
    """创建特征"""
    db = next(get_db())
    data = request.json

    try:
        name = data.get("name")
        if not name:
            return jsonify({"code": 40001, "message": "特征名称不能为空"}), 400

        feature = Feature(
            feature_id=generate_id("feat_"),
            name=name,
            description=data.get("description", ""),
            group_id=data.get("group_id"),
            group_name=data.get("group_name"),
            data_type=data.get("data_type", "float"),
            feature_type=data.get("feature_type", "raw"),
            expression=data.get("expression"),
            dependencies=data.get("dependencies"),
            aggregation_type=data.get("aggregation_type"),
            aggregation_window=data.get("aggregation_window"),
            tags=data.get("tags"),
            status="active",
            created_by=data.get("created_by", "system")
        )

        db.add(feature)
        db.commit()
        db.refresh(feature)

        # 更新特征组计数
        if feature.group_id:
            group = db.query(FeatureGroup).filter(FeatureGroup.group_id == feature.group_id).first()
            if group:
                group.feature_count = (group.feature_count or 0) + 1
                db.commit()

        return jsonify({
            "code": 0,
            "message": "success",
            "data": feature.to_dict()
        }), 201
    except Exception as e:
        db.rollback()
        return jsonify({"code": 50001, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/features/<feature_id>", methods=["GET"])
@require_jwt()
def get_feature(feature_id):
    """获取特征详情"""
    db = next(get_db())

    try:
        feature = db.query(Feature).filter(Feature.feature_id == feature_id).first()
        if not feature:
            return jsonify({"code": 40401, "message": "特征不存在"}), 404

        return jsonify({
            "code": 0,
            "message": "success",
            "data": feature.to_dict()
        })
    finally:
        db.close()


@app.route("/api/v1/features/<feature_id>", methods=["PUT"])
@require_jwt()
def update_feature(feature_id):
    """更新特征"""
    db = next(get_db())
    data = request.json

    try:
        feature = db.query(Feature).filter(Feature.feature_id == feature_id).first()
        if not feature:
            return jsonify({"code": 40401, "message": "特征不存在"}), 404

        if data.get("name"):
            feature.name = data["name"]
        if data.get("description") is not None:
            feature.description = data["description"]
        if data.get("expression"):
            feature.expression = data["expression"]
        if data.get("tags"):
            feature.tags = data["tags"]
        if data.get("status"):
            feature.status = data["status"]

        db.commit()
        db.refresh(feature)

        return jsonify({
            "code": 0,
            "message": "success",
            "data": feature.to_dict()
        })
    except Exception as e:
        db.rollback()
        return jsonify({"code": 50001, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/features/<feature_id>", methods=["DELETE"])
@require_jwt()
def delete_feature(feature_id):
    """删除特征"""
    db = next(get_db())

    try:
        feature = db.query(Feature).filter(Feature.feature_id == feature_id).first()
        if not feature:
            return jsonify({"code": 40401, "message": "特征不存在"}), 404

        group_id = feature.group_id
        db.delete(feature)
        db.commit()

        # 更新特征组计数
        if group_id:
            group = db.query(FeatureGroup).filter(FeatureGroup.group_id == group_id).first()
            if group and group.feature_count:
                group.feature_count = max(0, group.feature_count - 1)
                db.commit()

        return jsonify({"code": 0, "message": "success"})
    except Exception as e:
        db.rollback()
        return jsonify({"code": 50001, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/feature-groups", methods=["GET"])
@require_jwt()
def list_feature_groups():
    """列出特征组"""
    db = next(get_db())

    try:
        status = request.args.get("status")
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("page_size", 20))

        query = db.query(FeatureGroup)

        if status:
            query = query.filter(FeatureGroup.status == status)

        total = query.count()
        groups = query.order_by(FeatureGroup.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "groups": [g.to_dict() for g in groups],
                "total": total,
                "page": page,
                "page_size": page_size
            }
        })
    finally:
        db.close()


@app.route("/api/v1/feature-groups", methods=["POST"])
@require_jwt()
def create_feature_group():
    """创建特征组"""
    db = next(get_db())
    data = request.json

    try:
        name = data.get("name")
        if not name:
            return jsonify({"code": 40001, "message": "特征组名称不能为空"}), 400

        group = FeatureGroup(
            group_id=generate_id("fgrp_"),
            name=name,
            description=data.get("description", ""),
            entity_name=data.get("entity_name"),
            entity_key=data.get("entity_key"),
            source_type=data.get("source_type"),
            source_config=data.get("source_config"),
            online_store=data.get("online_store", True),
            offline_store=data.get("offline_store", True),
            ttl_days=data.get("ttl_days"),
            tags=data.get("tags"),
            status="active",
            created_by=data.get("created_by", "system")
        )

        db.add(group)
        db.commit()
        db.refresh(group)

        return jsonify({
            "code": 0,
            "message": "success",
            "data": group.to_dict()
        }), 201
    except Exception as e:
        db.rollback()
        return jsonify({"code": 50001, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/feature-groups/<group_id>", methods=["GET"])
@require_jwt()
def get_feature_group(group_id):
    """获取特征组详情"""
    db = next(get_db())

    try:
        group = db.query(FeatureGroup).filter(FeatureGroup.group_id == group_id).first()
        if not group:
            return jsonify({"code": 40401, "message": "特征组不存在"}), 404

        # 获取该组的特征
        features = db.query(Feature).filter(Feature.group_id == group_id).all()

        result = group.to_dict()
        result["features"] = [f.to_dict() for f in features]

        return jsonify({
            "code": 0,
            "message": "success",
            "data": result
        })
    finally:
        db.close()


# ==================== P5.1: 数据监控 ====================

@app.route("/api/v1/data-monitoring/health", methods=["GET"])
@require_jwt()
def get_data_health():
    """获取数据健康度概览"""
    db = next(get_db())

    try:
        # 获取规则统计
        total_rules = db.query(DataMonitoringRule).count()
        enabled_rules = db.query(DataMonitoringRule).filter(DataMonitoringRule.is_enabled == True).count()

        # 按状态统计
        healthy_count = db.query(DataMonitoringRule).filter(DataMonitoringRule.status == "healthy").count()
        warning_count = db.query(DataMonitoringRule).filter(DataMonitoringRule.status == "warning").count()
        critical_count = db.query(DataMonitoringRule).filter(DataMonitoringRule.status == "critical").count()

        # 告警统计
        active_alerts = db.query(DataAlert).filter(DataAlert.status == "active").count()

        # 计算健康分数
        if total_rules > 0:
            health_score = round((healthy_count / total_rules) * 100, 1)
        else:
            health_score = 100.0

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "health_score": health_score,
                "total_rules": total_rules,
                "enabled_rules": enabled_rules,
                "status_breakdown": {
                    "healthy": healthy_count,
                    "warning": warning_count,
                    "critical": critical_count
                },
                "active_alerts": active_alerts
            }
        })
    finally:
        db.close()


@app.route("/api/v1/data-monitoring/rules", methods=["GET"])
@require_jwt()
def list_data_monitoring_rules():
    """获取数据监控规则列表"""
    db = next(get_db())

    try:
        status = request.args.get("status")
        rule_type = request.args.get("rule_type")
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("page_size", 20))

        query = db.query(DataMonitoringRule)

        if status:
            query = query.filter(DataMonitoringRule.status == status)
        if rule_type:
            query = query.filter(DataMonitoringRule.rule_type == rule_type)

        total = query.count()
        rules = query.order_by(DataMonitoringRule.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

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


@app.route("/api/v1/data-monitoring/rules", methods=["POST"])
@require_jwt()
def create_data_monitoring_rule():
    """创建数据监控规则"""
    db = next(get_db())
    data = request.json

    try:
        name = data.get("name")
        if not name:
            return jsonify({"code": 40001, "message": "规则名称不能为空"}), 400

        rule = DataMonitoringRule(
            rule_id=generate_id("dmon_rule_"),
            name=name,
            description=data.get("description"),
            target_type=data.get("target_type"),
            target_id=data.get("target_id"),
            target_name=data.get("target_name"),
            rule_type=data.get("rule_type"),
            condition=data.get("condition"),
            threshold=data.get("threshold"),
            threshold_min=data.get("threshold_min"),
            threshold_max=data.get("threshold_max"),
            check_interval=data.get("check_interval", 3600),
            severity=data.get("severity", "warning"),
            notification_channels=data.get("notification_channels"),
            is_enabled=data.get("is_enabled", True),
            status="healthy",
            created_by=data.get("created_by", "system")
        )

        db.add(rule)
        db.commit()
        db.refresh(rule)

        return jsonify({
            "code": 0,
            "message": "success",
            "data": rule.to_dict()
        }), 201
    except Exception as e:
        db.rollback()
        return jsonify({"code": 50001, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/data-monitoring/rules/<rule_id>", methods=["PUT"])
@require_jwt()
def update_data_monitoring_rule(rule_id):
    """更新数据监控规则"""
    db = next(get_db())
    data = request.json

    try:
        rule = db.query(DataMonitoringRule).filter(DataMonitoringRule.rule_id == rule_id).first()
        if not rule:
            return jsonify({"code": 40401, "message": "规则不存在"}), 404

        if "name" in data:
            rule.name = data["name"]
        if "description" in data:
            rule.description = data["description"]
        if "threshold" in data:
            rule.threshold = data["threshold"]
        if "severity" in data:
            rule.severity = data["severity"]
        if "is_enabled" in data:
            rule.is_enabled = data["is_enabled"]
        if "notification_channels" in data:
            rule.notification_channels = data["notification_channels"]

        rule.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(rule)

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


@app.route("/api/v1/data-monitoring/rules/<rule_id>", methods=["DELETE"])
@require_jwt()
def delete_data_monitoring_rule(rule_id):
    """删除数据监控规则"""
    db = next(get_db())

    try:
        rule = db.query(DataMonitoringRule).filter(DataMonitoringRule.rule_id == rule_id).first()
        if not rule:
            return jsonify({"code": 40401, "message": "规则不存在"}), 404

        db.delete(rule)
        db.commit()

        return jsonify({
            "code": 0,
            "message": "删除成功"
        })
    finally:
        db.close()


@app.route("/api/v1/data-monitoring/alerts", methods=["GET"])
@require_jwt()
def list_data_alerts():
    """获取数据告警列表"""
    db = next(get_db())

    try:
        status = request.args.get("status")
        severity = request.args.get("severity")
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("page_size", 20))

        query = db.query(DataAlert)

        if status:
            query = query.filter(DataAlert.status == status)
        if severity:
            query = query.filter(DataAlert.severity == severity)

        total = query.count()
        alerts = query.order_by(DataAlert.triggered_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

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


@app.route("/api/v1/data-monitoring/alerts/<alert_id>/acknowledge", methods=["POST"])
@require_jwt()
def acknowledge_data_alert(alert_id):
    """确认数据告警"""
    db = next(get_db())
    data = request.json or {}

    try:
        alert = db.query(DataAlert).filter(DataAlert.alert_id == alert_id).first()
        if not alert:
            return jsonify({"code": 40401, "message": "告警不存在"}), 404

        alert.status = "acknowledged"
        alert.acknowledged_at = datetime.utcnow()
        alert.acknowledged_by = data.get("acknowledged_by", "system")

        db.commit()
        db.refresh(alert)

        return jsonify({
            "code": 0,
            "message": "确认成功",
            "data": alert.to_dict()
        })
    except Exception as e:
        db.rollback()
        return jsonify({"code": 50001, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/data-monitoring/alerts/<alert_id>/resolve", methods=["POST"])
@require_jwt()
def resolve_data_alert(alert_id):
    """解决数据告警"""
    db = next(get_db())
    data = request.json or {}

    try:
        alert = db.query(DataAlert).filter(DataAlert.alert_id == alert_id).first()
        if not alert:
            return jsonify({"code": 40401, "message": "告警不存在"}), 404

        alert.status = "resolved"
        alert.resolved_at = datetime.utcnow()
        alert.resolved_by = data.get("resolved_by", "system")

        db.commit()
        db.refresh(alert)

        return jsonify({
            "code": 0,
            "message": "解决成功",
            "data": alert.to_dict()
        })
    except Exception as e:
        db.rollback()
        return jsonify({"code": 50001, "message": str(e)}), 500
    finally:
        db.close()


# ==================== P6.2: 智能预警推送 ====================

@app.route("/api/v1/alerts/metric-rules", methods=["GET"])
@require_jwt()
def list_metric_alert_rules():
    """获取指标预警规则列表"""
    from models.data_monitoring import MetricAlertRule
    db = next(get_db())

    try:
        is_enabled = request.args.get("is_enabled")
        metric_type = request.args.get("metric_type")
        condition_type = request.args.get("condition_type")
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("page_size", 20))

        query = db.query(MetricAlertRule)

        if is_enabled is not None:
            query = query.filter(MetricAlertRule.is_enabled == (is_enabled.lower() == 'true'))
        if metric_type:
            query = query.filter(MetricAlertRule.metric_type == metric_type)
        if condition_type:
            query = query.filter(MetricAlertRule.condition_type == condition_type)

        total = query.count()
        rules = query.order_by(MetricAlertRule.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

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


@app.route("/api/v1/alerts/metric-rules", methods=["POST"])
@require_jwt()
def create_metric_alert_rule():
    """创建指标预警规则"""
    from models.data_monitoring import MetricAlertRule
    db = next(get_db())
    data = request.json

    try:
        name = data.get("name")
        condition_type = data.get("condition_type")

        if not name:
            return jsonify({"code": 40001, "message": "规则名称不能为空"}), 400
        if not condition_type:
            return jsonify({"code": 40001, "message": "条件类型不能为空"}), 400
        if condition_type not in ["threshold", "change_rate", "anomaly"]:
            return jsonify({"code": 40001, "message": "无效的条件类型"}), 400

        rule = MetricAlertRule(
            rule_id=generate_id("mar_"),
            name=name,
            description=data.get("description"),
            metric_id=data.get("metric_id"),
            metric_name=data.get("metric_name"),
            metric_type=data.get("metric_type"),
            condition_type=condition_type,
            condition_config=data.get("condition_config"),
            severity=data.get("severity", "warning"),
            alert_title_template=data.get("alert_title_template"),
            alert_message_template=data.get("alert_message_template"),
            notification_channels=data.get("notification_channels"),
            notification_targets=data.get("notification_targets"),
            cooldown_minutes=data.get("cooldown_minutes", 30),
            is_enabled=data.get("is_enabled", True),
            created_by=data.get("created_by", "system")
        )

        db.add(rule)
        db.commit()
        db.refresh(rule)

        return jsonify({
            "code": 0,
            "message": "success",
            "data": rule.to_dict()
        }), 201
    except Exception as e:
        db.rollback()
        return jsonify({"code": 50001, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/alerts/metric-rules/<rule_id>", methods=["GET"])
@require_jwt()
def get_metric_alert_rule(rule_id):
    """获取指标预警规则详情"""
    from models.data_monitoring import MetricAlertRule
    db = next(get_db())

    try:
        rule = db.query(MetricAlertRule).filter(MetricAlertRule.rule_id == rule_id).first()
        if not rule:
            return jsonify({"code": 40401, "message": "规则不存在"}), 404

        return jsonify({
            "code": 0,
            "message": "success",
            "data": rule.to_dict()
        })
    finally:
        db.close()


@app.route("/api/v1/alerts/metric-rules/<rule_id>", methods=["PUT"])
@require_jwt()
def update_metric_alert_rule(rule_id):
    """更新指标预警规则"""
    from models.data_monitoring import MetricAlertRule
    db = next(get_db())
    data = request.json

    try:
        rule = db.query(MetricAlertRule).filter(MetricAlertRule.rule_id == rule_id).first()
        if not rule:
            return jsonify({"code": 40401, "message": "规则不存在"}), 404

        if "name" in data:
            rule.name = data["name"]
        if "description" in data:
            rule.description = data["description"]
        if "metric_id" in data:
            rule.metric_id = data["metric_id"]
        if "metric_name" in data:
            rule.metric_name = data["metric_name"]
        if "metric_type" in data:
            rule.metric_type = data["metric_type"]
        if "condition_type" in data:
            rule.condition_type = data["condition_type"]
        if "condition_config" in data:
            rule.condition_config = data["condition_config"]
        if "severity" in data:
            rule.severity = data["severity"]
        if "alert_title_template" in data:
            rule.alert_title_template = data["alert_title_template"]
        if "alert_message_template" in data:
            rule.alert_message_template = data["alert_message_template"]
        if "notification_channels" in data:
            rule.notification_channels = data["notification_channels"]
        if "notification_targets" in data:
            rule.notification_targets = data["notification_targets"]
        if "cooldown_minutes" in data:
            rule.cooldown_minutes = data["cooldown_minutes"]
        if "is_enabled" in data:
            rule.is_enabled = data["is_enabled"]

        rule.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(rule)

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


@app.route("/api/v1/alerts/metric-rules/<rule_id>", methods=["DELETE"])
@require_jwt()
def delete_metric_alert_rule(rule_id):
    """删除指标预警规则"""
    from models.data_monitoring import MetricAlertRule
    db = next(get_db())

    try:
        rule = db.query(MetricAlertRule).filter(MetricAlertRule.rule_id == rule_id).first()
        if not rule:
            return jsonify({"code": 40401, "message": "规则不存在"}), 404

        db.delete(rule)
        db.commit()

        return jsonify({
            "code": 0,
            "message": "删除成功"
        })
    finally:
        db.close()


@app.route("/api/v1/alerts/metric-rules/<rule_id>/test", methods=["POST"])
@require_jwt()
def test_metric_alert_rule(rule_id):
    """测试指标预警规则"""
    from models.data_monitoring import MetricAlertRule
    from src.alert_engine import get_alert_engine
    db = next(get_db())
    data = request.json or {}

    try:
        rule = db.query(MetricAlertRule).filter(MetricAlertRule.rule_id == rule_id).first()
        if not rule:
            return jsonify({"code": 40401, "message": "规则不存在"}), 404

        engine = get_alert_engine(db)
        current_value = data.get("current_value")

        result = engine.check_metric_rule(rule, current_value)

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "should_alert": result.should_alert,
                "current_value": result.current_value,
                "threshold_value": result.threshold_value,
                "change_rate": result.change_rate,
                "anomaly_score": result.anomaly_score,
                "message": result.message
            }
        })
    except Exception as e:
        return jsonify({"code": 50001, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/alerts/metric-rules/<rule_id>/trigger", methods=["POST"])
@require_jwt()
def trigger_metric_alert_rule(rule_id):
    """手动触发指标预警规则"""
    from models.data_monitoring import MetricAlertRule
    from src.alert_engine import get_alert_engine
    db = next(get_db())
    data = request.json or {}

    try:
        rule = db.query(MetricAlertRule).filter(MetricAlertRule.rule_id == rule_id).first()
        if not rule:
            return jsonify({"code": 40401, "message": "规则不存在"}), 404

        engine = get_alert_engine(db)
        current_value = data.get("current_value")

        result = engine.check_metric_rule(rule, current_value)

        if result.should_alert:
            alert_id = engine.trigger_alert(rule, result, notify=data.get("notify", True))
            return jsonify({
                "code": 0,
                "message": "success",
                "data": {
                    "triggered": True,
                    "alert_id": alert_id,
                    "result": result.message
                }
            })
        else:
            return jsonify({
                "code": 0,
                "message": "success",
                "data": {
                    "triggered": False,
                    "result": result.message
                }
            })
    except Exception as e:
        db.rollback()
        return jsonify({"code": 50001, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/alerts/check-all", methods=["POST"])
@require_jwt()
def check_all_metric_alert_rules():
    """检查所有启用的预警规则（供定时任务调用）"""
    from src.alert_engine import get_alert_engine
    db = next(get_db())

    try:
        engine = get_alert_engine(db)
        triggered_alerts = engine.check_all_enabled_rules()

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "triggered_count": len(triggered_alerts),
                "alert_ids": triggered_alerts
            }
        })
    except Exception as e:
        db.rollback()
        return jsonify({"code": 50001, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/alerts/history", methods=["GET"])
@require_jwt()
def list_alert_history():
    """获取告警历史记录"""
    from models.data_monitoring import AlertHistory
    db = next(get_db())

    try:
        alert_id = request.args.get("alert_id")
        rule_id = request.args.get("rule_id")
        action = request.args.get("action")
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("page_size", 20))

        query = db.query(AlertHistory)

        if alert_id:
            query = query.filter(AlertHistory.alert_id == alert_id)
        if rule_id:
            query = query.filter(AlertHistory.rule_id == rule_id)
        if action:
            query = query.filter(AlertHistory.action == action)

        total = query.count()
        history = query.order_by(AlertHistory.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "history": [h.to_dict() for h in history],
                "total": total,
                "page": page,
                "page_size": page_size
            }
        })
    finally:
        db.close()


@app.route("/api/v1/alerts/metrics", methods=["POST"])
@require_jwt()
def record_metric_value():
    """记录指标值（供外部系统推送）"""
    from models.data_monitoring import MetricValue
    db = next(get_db())
    data = request.json

    try:
        metric_id = data.get("metric_id")
        value = data.get("value")

        if not metric_id:
            return jsonify({"code": 40001, "message": "指标ID不能为空"}), 400
        if value is None:
            return jsonify({"code": 40001, "message": "指标值不能为空"}), 400

        metric = MetricValue(
            metric_id=metric_id,
            metric_name=data.get("metric_name"),
            metric_type=data.get("metric_type"),
            value=float(value),
            dimensions=data.get("dimensions")
        )

        db.add(metric)
        db.commit()

        return jsonify({
            "code": 0,
            "message": "success"
        })
    except Exception as e:
        db.rollback()
        return jsonify({"code": 50001, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/alerts/metrics/<metric_id>", methods=["GET"])
@require_jwt()
def get_metric_values(metric_id):
    """获取指标历史值"""
    from models.data_monitoring import MetricValue
    db = next(get_db())

    try:
        start_time = request.args.get("start_time")
        end_time = request.args.get("end_time")
        limit = int(request.args.get("limit", 100))

        query = db.query(MetricValue).filter(MetricValue.metric_id == metric_id)

        if start_time:
            query = query.filter(MetricValue.timestamp >= start_time)
        if end_time:
            query = query.filter(MetricValue.timestamp <= end_time)

        values = query.order_by(MetricValue.timestamp.desc()).limit(limit).all()

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "values": [v.to_dict() for v in values]
            }
        })
    finally:
        db.close()


@app.route("/api/v1/alerts/statistics", methods=["GET"])
@require_jwt()
def get_alert_statistics():
    """获取告警统计"""
    from models.data_monitoring import MetricAlertRule, AlertHistory
    from sqlalchemy import func
    db = next(get_db())

    try:
        # 规则统计
        total_rules = db.query(MetricAlertRule).count()
        enabled_rules = db.query(MetricAlertRule).filter(MetricAlertRule.is_enabled == True).count()

        # 告警统计
        active_alerts = db.query(DataAlert).filter(DataAlert.status == "active").count()
        acknowledged_alerts = db.query(DataAlert).filter(DataAlert.status == "acknowledged").count()
        resolved_today = db.query(DataAlert).filter(
            DataAlert.status == "resolved",
            DataAlert.resolved_at >= datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        ).count()

        # 按严重级别统计活跃告警
        severity_stats = db.query(
            DataAlert.severity,
            func.count(DataAlert.id).label("count")
        ).filter(DataAlert.status == "active").group_by(DataAlert.severity).all()

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "rules": {
                    "total": total_rules,
                    "enabled": enabled_rules
                },
                "alerts": {
                    "active": active_alerts,
                    "acknowledged": acknowledged_alerts,
                    "resolved_today": resolved_today
                },
                "severity_distribution": {s: c for s, c in severity_stats}
            }
        })
    finally:
        db.close()


# ==================== P5.2: BI 仪表板 ====================

@app.route("/api/v1/bi/dashboards", methods=["GET"])
@require_jwt()
def list_bi_dashboards():
    """获取 BI 仪表板列表"""
    db = next(get_db())

    try:
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("page_size", 20))
        search = request.args.get("search")

        query = db.query(BIDashboard)

        if search:
            query = query.filter(BIDashboard.name.ilike(f"%{search}%"))

        total = query.count()
        dashboards = query.order_by(BIDashboard.updated_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

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
    finally:
        db.close()


@app.route("/api/v1/bi/dashboards", methods=["POST"])
@require_jwt()
def create_bi_dashboard():
    """创建 BI 仪表板"""
    db = next(get_db())
    data = request.json

    try:
        name = data.get("name")
        if not name:
            return jsonify({"code": 40001, "message": "仪表板名称不能为空"}), 400

        dashboard = BIDashboard(
            dashboard_id=generate_id("bi_dash_"),
            name=name,
            description=data.get("description"),
            layout=data.get("layout"),
            theme=data.get("theme", "light"),
            filters=data.get("filters"),
            auto_refresh=data.get("auto_refresh", False),
            refresh_interval=data.get("refresh_interval", 300),
            is_public=data.get("is_public", False),
            created_by=data.get("created_by", "system")
        )

        db.add(dashboard)
        db.commit()
        db.refresh(dashboard)

        return jsonify({
            "code": 0,
            "message": "success",
            "data": dashboard.to_dict()
        }), 201
    except Exception as e:
        db.rollback()
        return jsonify({"code": 50001, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/bi/dashboards/<dashboard_id>", methods=["GET"])
@require_jwt()
def get_bi_dashboard(dashboard_id):
    """获取 BI 仪表板详情"""
    db = next(get_db())

    try:
        dashboard = db.query(BIDashboard).filter(BIDashboard.dashboard_id == dashboard_id).first()
        if not dashboard:
            return jsonify({"code": 40401, "message": "仪表板不存在"}), 404

        # 增加浏览次数
        dashboard.view_count = (dashboard.view_count or 0) + 1
        db.commit()

        # 获取关联的图表
        charts = db.query(BIChart).filter(BIChart.dashboard_id == dashboard_id).all()

        result = dashboard.to_dict()
        result["charts"] = [c.to_dict() for c in charts]

        return jsonify({
            "code": 0,
            "message": "success",
            "data": result
        })
    finally:
        db.close()


@app.route("/api/v1/bi/dashboards/<dashboard_id>", methods=["PUT"])
@require_jwt()
def update_bi_dashboard(dashboard_id):
    """更新 BI 仪表板"""
    db = next(get_db())
    data = request.json

    try:
        dashboard = db.query(BIDashboard).filter(BIDashboard.dashboard_id == dashboard_id).first()
        if not dashboard:
            return jsonify({"code": 40401, "message": "仪表板不存在"}), 404

        if "name" in data:
            dashboard.name = data["name"]
        if "description" in data:
            dashboard.description = data["description"]
        if "layout" in data:
            dashboard.layout = data["layout"]
        if "theme" in data:
            dashboard.theme = data["theme"]
        if "filters" in data:
            dashboard.filters = data["filters"]
        if "auto_refresh" in data:
            dashboard.auto_refresh = data["auto_refresh"]
        if "refresh_interval" in data:
            dashboard.refresh_interval = data["refresh_interval"]
        if "is_public" in data:
            dashboard.is_public = data["is_public"]

        dashboard.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(dashboard)

        return jsonify({
            "code": 0,
            "message": "success",
            "data": dashboard.to_dict()
        })
    except Exception as e:
        db.rollback()
        return jsonify({"code": 50001, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/bi/dashboards/<dashboard_id>", methods=["DELETE"])
@require_jwt()
def delete_bi_dashboard(dashboard_id):
    """删除 BI 仪表板"""
    db = next(get_db())

    try:
        dashboard = db.query(BIDashboard).filter(BIDashboard.dashboard_id == dashboard_id).first()
        if not dashboard:
            return jsonify({"code": 40401, "message": "仪表板不存在"}), 404

        # 删除关联的图表
        db.query(BIChart).filter(BIChart.dashboard_id == dashboard_id).delete()
        db.delete(dashboard)
        db.commit()

        return jsonify({
            "code": 0,
            "message": "删除成功"
        })
    finally:
        db.close()


@app.route("/api/v1/bi/charts", methods=["GET"])
@require_jwt()
def list_bi_charts():
    """获取 BI 图表列表"""
    db = next(get_db())

    try:
        dashboard_id = request.args.get("dashboard_id")
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("page_size", 20))

        query = db.query(BIChart)

        if dashboard_id:
            query = query.filter(BIChart.dashboard_id == dashboard_id)

        total = query.count()
        charts = query.order_by(BIChart.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "charts": [c.to_dict() for c in charts],
                "total": total,
                "page": page,
                "page_size": page_size
            }
        })
    finally:
        db.close()


@app.route("/api/v1/bi/charts", methods=["POST"])
@require_jwt()
def create_bi_chart():
    """创建 BI 图表"""
    db = next(get_db())
    data = request.json

    try:
        name = data.get("name")
        if not name:
            return jsonify({"code": 40001, "message": "图表名称不能为空"}), 400

        chart = BIChart(
            chart_id=generate_id("bi_chart_"),
            name=name,
            description=data.get("description"),
            dashboard_id=data.get("dashboard_id"),
            chart_type=data.get("chart_type"),
            datasource_type=data.get("datasource_type"),
            datasource_id=data.get("datasource_id"),
            sql_query=data.get("sql_query"),
            config=data.get("config"),
            dimensions=data.get("dimensions"),
            metrics=data.get("metrics"),
            filters=data.get("filters"),
            cache_enabled=data.get("cache_enabled", True),
            cache_ttl=data.get("cache_ttl", 300),
            created_by=data.get("created_by", "system")
        )

        db.add(chart)
        db.commit()
        db.refresh(chart)

        return jsonify({
            "code": 0,
            "message": "success",
            "data": chart.to_dict()
        }), 201
    except Exception as e:
        db.rollback()
        return jsonify({"code": 50001, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/bi/charts/<chart_id>", methods=["PUT"])
@require_jwt()
def update_bi_chart(chart_id):
    """更新 BI 图表"""
    db = next(get_db())
    data = request.json

    try:
        chart = db.query(BIChart).filter(BIChart.chart_id == chart_id).first()
        if not chart:
            return jsonify({"code": 40401, "message": "图表不存在"}), 404

        if "name" in data:
            chart.name = data["name"]
        if "description" in data:
            chart.description = data["description"]
        if "chart_type" in data:
            chart.chart_type = data["chart_type"]
        if "sql_query" in data:
            chart.sql_query = data["sql_query"]
        if "config" in data:
            chart.config = data["config"]
        if "dimensions" in data:
            chart.dimensions = data["dimensions"]
        if "metrics" in data:
            chart.metrics = data["metrics"]
        if "filters" in data:
            chart.filters = data["filters"]

        chart.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(chart)

        return jsonify({
            "code": 0,
            "message": "success",
            "data": chart.to_dict()
        })
    except Exception as e:
        db.rollback()
        return jsonify({"code": 50001, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/bi/charts/<chart_id>", methods=["DELETE"])
@require_jwt()
def delete_bi_chart(chart_id):
    """删除 BI 图表"""
    db = next(get_db())

    try:
        chart = db.query(BIChart).filter(BIChart.chart_id == chart_id).first()
        if not chart:
            return jsonify({"code": 40401, "message": "图表不存在"}), 404

        db.delete(chart)
        db.commit()

        return jsonify({
            "code": 0,
            "message": "删除成功"
        })
    finally:
        db.close()


@app.route("/api/v1/bi/query", methods=["POST"])
@require_jwt()
def execute_bi_query():
    """执行 BI 数据查询"""
    data = request.json

    sql = data.get("sql")
    if not sql:
        return jsonify({"code": 40001, "message": "SQL 不能为空"}), 400

    # 模拟查询结果
    import random

    columns = data.get("columns", ["date", "value", "category"])
    rows = []
    for i in range(min(100, random.randint(10, 50))):
        row = {
            "date": f"2024-01-{i + 1:02d}",
            "value": round(random.random() * 1000, 2),
            "category": random.choice(["A", "B", "C", "D"])
        }
        rows.append(row)

    return jsonify({
        "code": 0,
        "message": "success",
        "data": {
            "columns": columns,
            "rows": rows,
            "row_count": len(rows)
        }
    })


# ==================== P5.3: 离线处理 ====================

@app.route("/api/v1/offline/tasks", methods=["GET"])
@require_jwt()
def list_offline_tasks():
    """获取离线任务列表"""
    db = next(get_db())

    try:
        status = request.args.get("status")
        task_type = request.args.get("task_type")
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("page_size", 20))

        query = db.query(OfflineTask)

        if status:
            query = query.filter(OfflineTask.status == status)
        if task_type:
            query = query.filter(OfflineTask.task_type == task_type)

        total = query.count()
        tasks = query.order_by(OfflineTask.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

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


@app.route("/api/v1/offline/tasks", methods=["POST"])
@require_jwt()
def create_offline_task():
    """创建离线任务"""
    db = next(get_db())
    data = request.json

    try:
        name = data.get("name")
        if not name:
            return jsonify({"code": 40001, "message": "任务名称不能为空"}), 400

        task = OfflineTask(
            task_id=generate_id("offline_"),
            name=name,
            description=data.get("description"),
            task_type=data.get("task_type"),
            sql_content=data.get("sql_content"),
            script_path=data.get("script_path"),
            script_content=data.get("script_content"),
            parameters=data.get("parameters"),
            executor_memory=data.get("executor_memory", "2g"),
            executor_cores=data.get("executor_cores", 2),
            num_executors=data.get("num_executors", 2),
            schedule_type=data.get("schedule_type", "manual"),
            cron_expression=data.get("cron_expression"),
            dependencies=data.get("dependencies"),
            output_table=data.get("output_table"),
            output_path=data.get("output_path"),
            output_format=data.get("output_format"),
            status="idle",
            created_by=data.get("created_by", "system")
        )

        db.add(task)
        db.commit()
        db.refresh(task)

        return jsonify({
            "code": 0,
            "message": "success",
            "data": task.to_dict()
        }), 201
    except Exception as e:
        db.rollback()
        return jsonify({"code": 50001, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/offline/tasks/<task_id>", methods=["GET"])
@require_jwt()
def get_offline_task(task_id):
    """获取离线任务详情"""
    db = next(get_db())

    try:
        task = db.query(OfflineTask).filter(OfflineTask.task_id == task_id).first()
        if not task:
            return jsonify({"code": 40401, "message": "任务不存在"}), 404

        return jsonify({
            "code": 0,
            "message": "success",
            "data": task.to_dict()
        })
    finally:
        db.close()


@app.route("/api/v1/offline/tasks/<task_id>", methods=["PUT"])
@require_jwt()
def update_offline_task(task_id):
    """更新离线任务"""
    db = next(get_db())
    data = request.json

    try:
        task = db.query(OfflineTask).filter(OfflineTask.task_id == task_id).first()
        if not task:
            return jsonify({"code": 40401, "message": "任务不存在"}), 404

        if task.status == "running":
            return jsonify({"code": 40002, "message": "运行中的任务无法修改"}), 400

        if "name" in data:
            task.name = data["name"]
        if "description" in data:
            task.description = data["description"]
        if "sql_content" in data:
            task.sql_content = data["sql_content"]
        if "parameters" in data:
            task.parameters = data["parameters"]
        if "schedule_type" in data:
            task.schedule_type = data["schedule_type"]
        if "cron_expression" in data:
            task.cron_expression = data["cron_expression"]

        task.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(task)

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


@app.route("/api/v1/offline/tasks/<task_id>", methods=["DELETE"])
@require_jwt()
def delete_offline_task(task_id):
    """删除离线任务"""
    db = next(get_db())

    try:
        task = db.query(OfflineTask).filter(OfflineTask.task_id == task_id).first()
        if not task:
            return jsonify({"code": 40401, "message": "任务不存在"}), 404

        if task.status == "running":
            return jsonify({"code": 40002, "message": "请先停止运行中的任务"}), 400

        db.delete(task)
        db.commit()

        return jsonify({
            "code": 0,
            "message": "删除成功"
        })
    finally:
        db.close()


@app.route("/api/v1/offline/tasks/<task_id>/run", methods=["POST"])
@require_jwt()
def run_offline_task(task_id):
    """执行离线任务"""
    db = next(get_db())
    data = request.json or {}

    try:
        task = db.query(OfflineTask).filter(OfflineTask.task_id == task_id).first()
        if not task:
            return jsonify({"code": 40401, "message": "任务不存在"}), 404

        if task.status == "running":
            return jsonify({"code": 40002, "message": "任务已在运行中"}), 400

        # 更新任务状态
        task.status = "running"
        task.last_run_at = datetime.utcnow()
        task.run_count = (task.run_count or 0) + 1

        # 创建执行日志
        log = OfflineTaskLog(
            log_id=generate_id("offline_log_"),
            task_id=task_id,
            execution_id=generate_id("exec_"),
            status="running",
            started_at=datetime.utcnow(),
            triggered_by=data.get("triggered_by", "manual"),
            triggered_user=data.get("triggered_user", "system")
        )

        db.add(log)
        db.commit()
        db.refresh(task)
        db.refresh(log)

        return jsonify({
            "code": 0,
            "message": "任务已启动",
            "data": {
                "task": task.to_dict(),
                "execution_id": log.execution_id
            }
        })
    except Exception as e:
        db.rollback()
        return jsonify({"code": 50001, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/offline/tasks/<task_id>/logs", methods=["GET"])
@require_jwt()
def list_offline_task_logs(task_id):
    """获取离线任务执行日志"""
    db = next(get_db())

    try:
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("page_size", 20))

        query = db.query(OfflineTaskLog).filter(OfflineTaskLog.task_id == task_id)
        total = query.count()
        logs = query.order_by(OfflineTaskLog.started_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "logs": [l.to_dict() for l in logs],
                "total": total,
                "page": page,
                "page_size": page_size
            }
        })
    finally:
        db.close()


# ==================== P5.4: 数据资产目录 ====================

@app.route("/api/v1/assets", methods=["GET"])
@require_jwt()
def list_data_assets():
    """获取数据资产列表"""
    db = next(get_db())

    try:
        category_id = request.args.get("category_id")
        asset_type = request.args.get("asset_type")
        search = request.args.get("search")
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("page_size", 20))

        query = db.query(DataAsset).filter(DataAsset.status == "active")

        if category_id:
            query = query.filter(DataAsset.category_id == category_id)
        if asset_type:
            query = query.filter(DataAsset.asset_type == asset_type)
        if search:
            query = query.filter(
                (DataAsset.name.ilike(f"%{search}%")) |
                (DataAsset.description.ilike(f"%{search}%"))
            )

        total = query.count()
        assets = query.order_by(DataAsset.updated_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "assets": [a.to_dict() for a in assets],
                "total": total,
                "page": page,
                "page_size": page_size
            }
        })
    finally:
        db.close()


@app.route("/api/v1/assets/<asset_id>", methods=["GET"])
@require_jwt()
def get_data_asset(asset_id):
    """获取数据资产详情"""
    db = next(get_db())

    try:
        asset = db.query(DataAsset).filter(DataAsset.asset_id == asset_id).first()
        if not asset:
            return jsonify({"code": 40401, "message": "资产不存在"}), 404

        # 增加访问次数
        asset.view_count = (asset.view_count or 0) + 1
        db.commit()

        return jsonify({
            "code": 0,
            "message": "success",
            "data": asset.to_dict()
        })
    finally:
        db.close()


@app.route("/api/v1/assets/<asset_id>/collect", methods=["POST"])
@require_jwt()
def collect_data_asset(asset_id):
    """收藏数据资产"""
    db = next(get_db())
    data = request.json or {}

    try:
        asset = db.query(DataAsset).filter(DataAsset.asset_id == asset_id).first()
        if not asset:
            return jsonify({"code": 40401, "message": "资产不存在"}), 404

        user_id = data.get("user_id", "system")

        # 检查是否已收藏
        existing = db.query(AssetCollection).filter(
            AssetCollection.asset_id == asset_id,
            AssetCollection.user_id == user_id
        ).first()

        if existing:
            return jsonify({"code": 40002, "message": "已收藏该资产"}), 400

        collection = AssetCollection(
            asset_id=asset_id,
            user_id=user_id
        )

        db.add(collection)

        # 更新收藏计数
        asset.collect_count = (asset.collect_count or 0) + 1
        db.commit()

        return jsonify({
            "code": 0,
            "message": "收藏成功"
        })
    except Exception as e:
        db.rollback()
        return jsonify({"code": 50001, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/assets/<asset_id>/uncollect", methods=["POST"])
@require_jwt()
def uncollect_data_asset(asset_id):
    """取消收藏数据资产"""
    db = next(get_db())
    data = request.json or {}

    try:
        user_id = data.get("user_id", "system")

        collection = db.query(AssetCollection).filter(
            AssetCollection.asset_id == asset_id,
            AssetCollection.user_id == user_id
        ).first()

        if not collection:
            return jsonify({"code": 40401, "message": "未收藏该资产"}), 404

        db.delete(collection)

        # 更新收藏计数
        asset = db.query(DataAsset).filter(DataAsset.asset_id == asset_id).first()
        if asset and asset.collect_count and asset.collect_count > 0:
            asset.collect_count -= 1

        db.commit()

        return jsonify({
            "code": 0,
            "message": "取消收藏成功"
        })
    except Exception as e:
        db.rollback()
        return jsonify({"code": 50001, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/assets/categories", methods=["GET"])
@require_jwt()
def list_asset_categories():
    """获取资产分类列表"""
    db = next(get_db())

    try:
        categories = db.query(AssetCategory).order_by(AssetCategory.sort_order).all()

        # 如果没有数据，返回默认分类
        if not categories:
            default_categories = [
                {"id": "database", "name": "数据库表", "icon": "Database", "asset_count": 0},
                {"id": "file", "name": "文件数据", "icon": "File", "asset_count": 0},
                {"id": "api", "name": "API 接口", "icon": "Globe", "asset_count": 0},
                {"id": "report", "name": "报表", "icon": "BarChart", "asset_count": 0},
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
    finally:
        db.close()


# ==================== P5.5: 数据标准管理 ====================

@app.route("/api/v1/standards", methods=["GET"])
@require_jwt()
def list_data_standards():
    """获取数据标准列表"""
    db = next(get_db())

    try:
        category = request.args.get("category")
        status = request.args.get("status")
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("page_size", 20))

        query = db.query(DataStandard)

        if category:
            query = query.filter(DataStandard.category == category)
        if status:
            query = query.filter(DataStandard.status == status)

        total = query.count()
        standards = query.order_by(DataStandard.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "standards": [s.to_dict() for s in standards],
                "total": total,
                "page": page,
                "page_size": page_size
            }
        })
    finally:
        db.close()


@app.route("/api/v1/standards", methods=["POST"])
@require_jwt()
def create_data_standard():
    """创建数据标准"""
    db = next(get_db())
    data = request.json

    try:
        name = data.get("name")
        if not name:
            return jsonify({"code": 40001, "message": "标准名称不能为空"}), 400

        standard = DataStandard(
            standard_id=generate_id("std_"),
            name=name,
            description=data.get("description"),
            category=data.get("category"),
            rule_type=data.get("rule_type"),
            rule_config=data.get("rule_config"),
            apply_to=data.get("apply_to"),
            data_types=data.get("data_types"),
            examples=data.get("examples"),
            status=data.get("status", "active"),
            is_required=data.get("is_required", False),
            version=data.get("version", "1.0"),
            created_by=data.get("created_by", "system")
        )

        db.add(standard)
        db.commit()
        db.refresh(standard)

        return jsonify({
            "code": 0,
            "message": "success",
            "data": standard.to_dict()
        }), 201
    except Exception as e:
        db.rollback()
        return jsonify({"code": 50001, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/standards/<standard_id>", methods=["GET"])
@require_jwt()
def get_data_standard(standard_id):
    """获取数据标准详情"""
    db = next(get_db())

    try:
        standard = db.query(DataStandard).filter(DataStandard.standard_id == standard_id).first()
        if not standard:
            return jsonify({"code": 40401, "message": "标准不存在"}), 404

        return jsonify({
            "code": 0,
            "message": "success",
            "data": standard.to_dict()
        })
    finally:
        db.close()


@app.route("/api/v1/standards/<standard_id>", methods=["PUT"])
@require_jwt()
def update_data_standard(standard_id):
    """更新数据标准"""
    db = next(get_db())
    data = request.json

    try:
        standard = db.query(DataStandard).filter(DataStandard.standard_id == standard_id).first()
        if not standard:
            return jsonify({"code": 40401, "message": "标准不存在"}), 404

        if "name" in data:
            standard.name = data["name"]
        if "description" in data:
            standard.description = data["description"]
        if "rule_config" in data:
            standard.rule_config = data["rule_config"]
        if "apply_to" in data:
            standard.apply_to = data["apply_to"]
        if "status" in data:
            standard.status = data["status"]
        if "is_required" in data:
            standard.is_required = data["is_required"]

        standard.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(standard)

        return jsonify({
            "code": 0,
            "message": "success",
            "data": standard.to_dict()
        })
    except Exception as e:
        db.rollback()
        return jsonify({"code": 50001, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/standards/<standard_id>", methods=["DELETE"])
@require_jwt()
def delete_data_standard(standard_id):
    """删除数据标准"""
    db = next(get_db())

    try:
        standard = db.query(DataStandard).filter(DataStandard.standard_id == standard_id).first()
        if not standard:
            return jsonify({"code": 40401, "message": "标准不存在"}), 404

        db.delete(standard)
        db.commit()

        return jsonify({
            "code": 0,
            "message": "删除成功"
        })
    finally:
        db.close()


@app.route("/api/v1/standards/validate", methods=["POST"])
@require_jwt()
def validate_data_standard():
    """验证数据是否符合标准"""
    db = next(get_db())
    data = request.json

    try:
        standard_id = data.get("standard_id")
        input_value = data.get("value")

        if not standard_id:
            return jsonify({"code": 40001, "message": "标准 ID 不能为空"}), 400

        standard = db.query(DataStandard).filter(DataStandard.standard_id == standard_id).first()
        if not standard:
            return jsonify({"code": 40401, "message": "标准不存在"}), 404

        # 执行验证（模拟）
        import re
        is_valid = True
        error_message = None

        if standard.rule_type == "regex" and standard.rule_config:
            pattern = standard.rule_config.get("pattern")
            if pattern and input_value:
                try:
                    if not re.match(pattern, str(input_value)):
                        is_valid = False
                        error_message = f"值 '{input_value}' 不符合正则表达式: {pattern}"
                except re.error:
                    error_message = "无效的正则表达式"

        # 记录验证结果
        validation = StandardValidation(
            validation_id=generate_id("val_"),
            standard_id=standard_id,
            standard_name=standard.name,
            input_value=str(input_value) if input_value else None,
            is_valid=is_valid,
            error_message=error_message,
            validated_by=data.get("validated_by", "system")
        )

        db.add(validation)

        # 更新统计
        standard.apply_count = (standard.apply_count or 0) + 1
        if not is_valid:
            standard.violation_count = (standard.violation_count or 0) + 1

        db.commit()
        db.refresh(validation)

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "is_valid": is_valid,
                "error_message": error_message,
                "validation": validation.to_dict()
            }
        })
    except Exception as e:
        db.rollback()
        return jsonify({"code": 50001, "message": str(e)}), 500
    finally:
        db.close()


# ==================== P5.6: 数据服务发布 ====================

@app.route("/api/v1/data-services", methods=["GET"])
@require_jwt()
def list_data_services():
    """获取数据服务列表"""
    db = next(get_db())

    try:
        status = request.args.get("status")
        service_type = request.args.get("service_type")
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("page_size", 20))

        query = db.query(DataService)

        if status:
            query = query.filter(DataService.status == status)
        if service_type:
            query = query.filter(DataService.service_type == service_type)

        total = query.count()
        services = query.order_by(DataService.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

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
    finally:
        db.close()


@app.route("/api/v1/data-services", methods=["POST"])
@require_jwt()
def create_data_service():
    """创建数据服务"""
    db = next(get_db())
    data = request.json

    try:
        name = data.get("name")
        if not name:
            return jsonify({"code": 40001, "message": "服务名称不能为空"}), 400

        service = DataService(
            service_id=generate_id("dsvc_"),
            name=name,
            description=data.get("description"),
            service_type=data.get("service_type", "api"),
            source_type=data.get("source_type"),
            source_id=data.get("source_id"),
            sql_query=data.get("sql_query"),
            path=data.get("path"),
            method=data.get("method", "GET"),
            parameters=data.get("parameters"),
            response_format=data.get("response_format", "json"),
            auth_type=data.get("auth_type", "none"),
            auth_config=data.get("auth_config"),
            rate_limit_enabled=data.get("rate_limit_enabled", True),
            rate_limit_per_minute=data.get("rate_limit_per_minute", 60),
            rate_limit_per_day=data.get("rate_limit_per_day", 10000),
            cache_enabled=data.get("cache_enabled", True),
            cache_ttl=data.get("cache_ttl", 300),
            status="stopped",
            version=data.get("version", "v1"),
            created_by=data.get("created_by", "system")
        )

        db.add(service)
        db.commit()
        db.refresh(service)

        return jsonify({
            "code": 0,
            "message": "success",
            "data": service.to_dict()
        }), 201
    except Exception as e:
        db.rollback()
        return jsonify({"code": 50001, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/data-services/<service_id>", methods=["GET"])
@require_jwt()
def get_data_service(service_id):
    """获取数据服务详情"""
    db = next(get_db())

    try:
        service = db.query(DataService).filter(DataService.service_id == service_id).first()
        if not service:
            return jsonify({"code": 40401, "message": "服务不存在"}), 404

        return jsonify({
            "code": 0,
            "message": "success",
            "data": service.to_dict()
        })
    finally:
        db.close()


@app.route("/api/v1/data-services/<service_id>", methods=["PUT"])
@require_jwt()
def update_data_service(service_id):
    """更新数据服务"""
    db = next(get_db())
    data = request.json

    try:
        service = db.query(DataService).filter(DataService.service_id == service_id).first()
        if not service:
            return jsonify({"code": 40401, "message": "服务不存在"}), 404

        if "name" in data:
            service.name = data["name"]
        if "description" in data:
            service.description = data["description"]
        if "sql_query" in data:
            service.sql_query = data["sql_query"]
        if "path" in data:
            service.path = data["path"]
        if "parameters" in data:
            service.parameters = data["parameters"]
        if "auth_type" in data:
            service.auth_type = data["auth_type"]
        if "rate_limit_per_minute" in data:
            service.rate_limit_per_minute = data["rate_limit_per_minute"]
        if "cache_enabled" in data:
            service.cache_enabled = data["cache_enabled"]
        if "cache_ttl" in data:
            service.cache_ttl = data["cache_ttl"]

        service.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(service)

        return jsonify({
            "code": 0,
            "message": "success",
            "data": service.to_dict()
        })
    except Exception as e:
        db.rollback()
        return jsonify({"code": 50001, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/data-services/<service_id>", methods=["DELETE"])
@require_jwt()
def delete_data_service(service_id):
    """删除数据服务"""
    db = next(get_db())

    try:
        service = db.query(DataService).filter(DataService.service_id == service_id).first()
        if not service:
            return jsonify({"code": 40401, "message": "服务不存在"}), 404

        if service.status == "running":
            return jsonify({"code": 40002, "message": "请先停止运行中的服务"}), 400

        db.delete(service)
        db.commit()

        return jsonify({
            "code": 0,
            "message": "删除成功"
        })
    finally:
        db.close()


@app.route("/api/v1/data-services/<service_id>/start", methods=["POST"])
@require_jwt()
def start_data_service(service_id):
    """启动数据服务"""
    db = next(get_db())

    try:
        service = db.query(DataService).filter(DataService.service_id == service_id).first()
        if not service:
            return jsonify({"code": 40401, "message": "服务不存在"}), 404

        if service.status == "running":
            return jsonify({"code": 40002, "message": "服务已在运行中"}), 400

        service.status = "running"
        service.started_at = datetime.utcnow()
        service.stopped_at = None

        db.commit()
        db.refresh(service)

        return jsonify({
            "code": 0,
            "message": "服务已启动",
            "data": service.to_dict()
        })
    except Exception as e:
        db.rollback()
        return jsonify({"code": 50001, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/data-services/<service_id>/stop", methods=["POST"])
@require_jwt()
def stop_data_service(service_id):
    """停止数据服务"""
    db = next(get_db())

    try:
        service = db.query(DataService).filter(DataService.service_id == service_id).first()
        if not service:
            return jsonify({"code": 40401, "message": "服务不存在"}), 404

        if service.status != "running":
            return jsonify({"code": 40002, "message": "服务未在运行"}), 400

        service.status = "stopped"
        service.stopped_at = datetime.utcnow()

        db.commit()
        db.refresh(service)

        return jsonify({
            "code": 0,
            "message": "服务已停止",
            "data": service.to_dict()
        })
    except Exception as e:
        db.rollback()
        return jsonify({"code": 50001, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/data-services/<service_id>/stats", methods=["GET"])
@require_jwt()
def get_data_service_stats(service_id):
    """获取数据服务调用统计"""
    db = next(get_db())

    try:
        service = db.query(DataService).filter(DataService.service_id == service_id).first()
        if not service:
            return jsonify({"code": 40401, "message": "服务不存在"}), 404

        # 获取最近的调用日志统计
        from sqlalchemy import func

        # 今日统计
        today = datetime.utcnow().date()
        today_calls = db.query(func.count(ServiceCallLog.id)).filter(
            ServiceCallLog.service_id == service_id,
            func.date(ServiceCallLog.called_at) == today
        ).scalar() or 0

        # 错误率
        error_rate = 0
        if service.total_calls and service.total_calls > 0:
            error_rate = round((service.error_calls or 0) / service.total_calls * 100, 2)

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "service_id": service_id,
                "total_calls": service.total_calls or 0,
                "success_calls": service.success_calls or 0,
                "error_calls": service.error_calls or 0,
                "today_calls": today_calls,
                "avg_response_time_ms": service.avg_response_time_ms,
                "error_rate": error_rate
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


# ==================== 数据脱敏 API ====================

@app.route("/api/v1/masking/preview", methods=["POST"])
@require_jwt()
def masking_preview():
    """
    获取数据脱敏预览
    P6: 数据安全管理 - 数据脱敏
    """
    try:
        from src.data_masking import get_masking_service

        data = request.get_json()
        sample_data = data.get("sample_data", [])
        column_metadata = data.get("column_metadata", {})
        max_rows = min(data.get("max_rows", 5), 10)

        if not sample_data:
            return jsonify({"code": 40000, "message": "sample_data is required"}), 400

        service = get_masking_service()
        preview = service.get_masking_preview(sample_data, column_metadata, max_rows)

        return jsonify({
            "code": 0,
            "message": "success",
            "data": preview
        })
    except Exception as e:
        logger.error(f"脱敏预览失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/masking/execute", methods=["POST"])
@require_jwt()
def masking_execute():
    """
    执行数据脱敏
    P6: 数据安全管理 - 数据脱敏
    """
    try:
        from src.data_masking import get_masking_service

        data = request.get_json()
        records = data.get("data", [])
        column_metadata = data.get("column_metadata", {})

        if not records:
            return jsonify({"code": 40000, "message": "data is required"}), 400

        service = get_masking_service()
        masked_data = service.mask_dataframe(records, column_metadata)

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "masked_data": masked_data,
                "record_count": len(masked_data)
            }
        })
    except Exception as e:
        logger.error(f"数据脱敏失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/masking/config", methods=["POST"])
@require_jwt()
def masking_config():
    """
    生成脱敏配置
    P6: 数据安全管理 - 数据脱敏
    """
    try:
        from src.data_masking import get_masking_service

        data = request.get_json()
        columns = data.get("columns", [])

        if not columns:
            return jsonify({"code": 40000, "message": "columns is required"}), 400

        service = get_masking_service()
        config = service.create_masking_config(columns)

        return jsonify({
            "code": 0,
            "message": "success",
            "data": config
        })
    except Exception as e:
        logger.error(f"生成脱敏配置失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/masking/rules", methods=["GET"])
@require_jwt()
def list_masking_rules():
    """
    获取可用的脱敏规则列表
    P6: 数据安全管理 - 数据脱敏
    """
    try:
        from src.data_masking import get_masking_service, MaskingStrategy

        service = get_masking_service()

        rules = []
        for rule in service.rules:
            rules.append({
                "rule_id": rule.rule_id,
                "name": rule.name,
                "strategy": rule.strategy.value,
                "sensitivity_type": rule.sensitivity_type,
                "sensitivity_level": rule.sensitivity_level,
                "column_pattern": rule.column_pattern,
                "data_type": rule.data_type,
                "options": rule.options,
                "enabled": rule.enabled,
                "priority": rule.priority
            })

        strategies = [
            {"value": s.value, "label": s.value.replace("_", " ").title()}
            for s in MaskingStrategy
        ]

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "rules": rules,
                "strategies": strategies
            }
        })
    except Exception as e:
        logger.error(f"获取脱敏规则失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/masking/value", methods=["POST"])
@require_jwt()
def mask_single_value():
    """
    对单个值进行脱敏
    P6: 数据安全管理 - 数据脱敏
    """
    try:
        from src.data_masking import get_masking_service, MaskingStrategy

        data = request.get_json()
        value = data.get("value")
        column_name = data.get("column_name", "unknown")
        sensitivity_type = data.get("sensitivity_type")
        sensitivity_level = data.get("sensitivity_level")
        strategy = data.get("strategy")
        options = data.get("options", {})

        if value is None:
            return jsonify({"code": 40000, "message": "value is required"}), 400

        service = get_masking_service()

        strategy_enum = None
        if strategy:
            try:
                strategy_enum = MaskingStrategy(strategy)
            except ValueError:
                return jsonify({"code": 40000, "message": f"Invalid strategy: {strategy}"}), 400

        masked_value = service.mask_value(
            value=value,
            column_name=column_name,
            sensitivity_type=sensitivity_type,
            sensitivity_level=sensitivity_level,
            strategy_override=strategy_enum,
            options_override=options if options else None
        )

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "original": value,
                "masked": masked_value
            }
        })
    except Exception as e:
        logger.error(f"单值脱敏失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/masking/table/<table_id>", methods=["POST"])
@require_jwt()
def mask_table_data(table_id: str):
    """
    根据表元数据自动脱敏数据
    P6: 数据安全管理 - 数据脱敏
    """
    try:
        from src.data_masking import get_masking_service

        db = get_db()

        # 获取表的列元数据
        table = db.query(MetadataTable).filter(
            MetadataTable.table_id == table_id
        ).first()

        if not table:
            return jsonify({"code": 40400, "message": "Table not found"}), 404

        columns = db.query(MetadataColumn).filter(
            MetadataColumn.table_id == table.id
        ).all()

        # 构建列元数据
        column_metadata = {}
        for col in columns:
            column_metadata[col.column_name] = {
                "sensitivity_type": col.sensitivity_type,
                "sensitivity_level": col.sensitivity_level,
                "data_type": "string"  # 简化处理
            }

        # 获取要脱敏的数据
        data = request.get_json()
        records = data.get("data", [])

        if not records:
            return jsonify({"code": 40000, "message": "data is required"}), 400

        # 执行脱敏
        service = get_masking_service()
        masked_data = service.mask_dataframe(records, column_metadata)

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "table_id": table_id,
                "table_name": table.table_name,
                "masked_data": masked_data,
                "record_count": len(masked_data),
                "columns_with_masking": [
                    col for col, meta in column_metadata.items()
                    if meta.get("sensitivity_type") and meta["sensitivity_type"] != "none"
                ]
            }
        })
    except Exception as e:
        logger.error(f"表数据脱敏失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


# ==================== ShardingSphere 透明脱敏 API ====================

@app.route("/api/v1/masking/shardingsphere/status", methods=["GET"])
@require_jwt(optional=True)
def get_shardingsphere_status():
    """
    获取 ShardingSphere Proxy 状态
    返回连接状态和可用数据库列表
    """
    try:
        from integrations.shardingsphere import ShardingSphereConfig, ShardingSphereClient
        if ShardingSphereConfig is None:
            return jsonify({
                "code": 0,
                "message": "success",
                "data": {
                    "enabled": False,
                    "message": "ShardingSphere integration not available"
                }
            })

        config = ShardingSphereConfig.from_env()
        if not config.enabled:
            return jsonify({
                "code": 0,
                "message": "success",
                "data": {
                    "enabled": False,
                    "message": "ShardingSphere is disabled"
                }
            })

        client = ShardingSphereClient(config)
        status = client.get_status()
        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "enabled": True,
                **status
            }
        })
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"获取 ShardingSphere 状态失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/masking/shardingsphere/generate-rules", methods=["POST"])
@require_jwt()
def generate_shardingsphere_rules():
    """
    从敏感扫描结果生成 ShardingSphere 脱敏规则

    请求体:
    {
        "database": "db_name",
        "table": "table_name",
        "sensitivity_results": [
            {"column_name": "phone", "sensitivity_type": "phone"},
            {"column_name": "email", "sensitivity_type": "email"}
        ],
        "format": "sql" | "yaml" (默认 sql)
    }
    """
    try:
        from integrations.shardingsphere import MaskingRuleGenerator

        data = request.json or {}
        database = data.get("database")
        table = data.get("table")
        sensitivity_results = data.get("sensitivity_results", [])
        output_format = data.get("format", "sql")

        if not database or not table:
            return jsonify({
                "code": 40000,
                "message": "database and table are required"
            }), 400

        if not sensitivity_results:
            return jsonify({
                "code": 40000,
                "message": "sensitivity_results is required"
            }), 400

        # 生成规则配置
        rules = MaskingRuleGenerator.from_sensitivity_results(sensitivity_results)

        if output_format == "yaml":
            rule_content = MaskingRuleGenerator.generate_mask_rule_yaml(database, table, rules)
        else:
            rule_content = MaskingRuleGenerator.generate_mask_rule_sql(database, table, rules)

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "database": database,
                "table": table,
                "format": output_format,
                "rules": rules,
                "rule_content": rule_content,
            }
        })
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"生成 ShardingSphere 脱敏规则失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/masking/shardingsphere/apply-rules", methods=["POST"])
@require_jwt()
def apply_shardingsphere_rules():
    """
    将脱敏规则应用到 ShardingSphere Proxy

    请求体:
    {
        "rule_sql": "CREATE MASK RULE ..."
    }
    或
    {
        "database": "db_name",
        "table": "table_name",
        "sensitivity_results": [...]
    }
    """
    try:
        from integrations.shardingsphere import ShardingSphereConfig, ShardingSphereClient, MaskingRuleGenerator

        if ShardingSphereConfig is None:
            return jsonify({
                "code": 50003,
                "message": "ShardingSphere integration not available"
            }), 503

        config = ShardingSphereConfig.from_env()
        if not config.enabled:
            return jsonify({
                "code": 50003,
                "message": "ShardingSphere is disabled"
            }), 503

        data = request.json or {}

        # 方式1: 直接提供 SQL
        rule_sql = data.get("rule_sql")

        # 方式2: 从敏感结果生成
        if not rule_sql:
            database = data.get("database")
            table = data.get("table")
            sensitivity_results = data.get("sensitivity_results", [])

            if not database or not table or not sensitivity_results:
                return jsonify({
                    "code": 40000,
                    "message": "rule_sql or (database, table, sensitivity_results) required"
                }), 400

            rules = MaskingRuleGenerator.from_sensitivity_results(sensitivity_results)
            rule_sql = MaskingRuleGenerator.generate_mask_rule_sql(database, table, rules)

        client = ShardingSphereClient(config)
        success = client.apply_mask_rules(rule_sql)

        if success:
            return jsonify({
                "code": 0,
                "message": "脱敏规则已应用",
                "data": {
                    "applied_sql": rule_sql
                }
            })
        else:
            return jsonify({
                "code": 50002,
                "message": "应用脱敏规则失败"
            }), 500
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"应用 ShardingSphere 脱敏规则失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/masking/shardingsphere/rules/<database>", methods=["GET"])
@require_jwt()
def list_shardingsphere_rules(database):
    """
    查看指定数据库的已生效脱敏规则
    """
    try:
        from integrations.shardingsphere import ShardingSphereConfig, ShardingSphereClient

        if ShardingSphereConfig is None:
            return jsonify({
                "code": 50003,
                "message": "ShardingSphere integration not available"
            }), 503

        config = ShardingSphereConfig.from_env()
        if not config.enabled:
            return jsonify({
                "code": 50003,
                "message": "ShardingSphere is disabled"
            }), 503

        client = ShardingSphereClient(config)
        rules = client.list_mask_rules(database)

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "database": database,
                "rules": rules
            }
        })
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"获取 ShardingSphere 脱敏规则失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/masking/shardingsphere/rules/<database>/<table>", methods=["DELETE"])
@require_jwt()
def delete_shardingsphere_rules(database, table):
    """
    移除指定表的脱敏规则
    """
    try:
        from integrations.shardingsphere import ShardingSphereConfig, ShardingSphereClient

        if ShardingSphereConfig is None:
            return jsonify({
                "code": 50003,
                "message": "ShardingSphere integration not available"
            }), 503

        config = ShardingSphereConfig.from_env()
        if not config.enabled:
            return jsonify({
                "code": 50003,
                "message": "ShardingSphere is disabled"
            }), 503

        client = ShardingSphereClient(config)
        success = client.remove_mask_rules(database, table)

        if success:
            return jsonify({
                "code": 0,
                "message": f"脱敏规则已移除: {database}.{table}"
            })
        else:
            return jsonify({
                "code": 50002,
                "message": "移除脱敏规则失败"
            }), 500
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"移除 ShardingSphere 脱敏规则失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


# ==================== 非结构化文档 OCR API ====================

# OCR 服务单例
_ocr_service = None


def get_ocr_service():
    """获取 OCR 服务实例"""
    global _ocr_service
    if _ocr_service is None:
        from src.ocr_service import OCRService
        _ocr_service = OCRService()
    return _ocr_service


@app.route("/api/v1/ocr/extract", methods=["POST"])
@require_auth
def ocr_extract_document():
    """
    从文档提取内容

    支持的文档类型：
    - PDF：提取文本、表格、图片
    - 图片：OCR 识别
    - Word：提取文本和表格
    - 文本文件：直接读取
    """
    try:
        # 检查是否有上传文件
        if 'file' not in request.files:
            # 尝试从 base64 读取
            data = request.get_json()
            if not data or 'content' not in data:
                return jsonify({"code": 40000, "message": "file or content is required"}), 400

            content_base64 = data.get('content')
            filename = data.get('filename', 'document')
            content_type = data.get('content_type')
            extract_tables = data.get('extract_tables', True)
            extract_images = data.get('extract_images', False)
            ocr_images = data.get('ocr_images', True)

            # 解码 base64
            try:
                file_data = base64.b64decode(content_base64)
            except Exception as e:
                return jsonify({"code": 40000, "message": f"Invalid base64 content: {e}"}), 400

            service = get_ocr_service()
            result = service.extract_from_bytes(
                data=file_data,
                filename=filename,
                content_type=content_type,
                extract_tables=extract_tables,
                extract_images=extract_images,
                ocr_images=ocr_images,
            )
        else:
            file = request.files['file']
            if file.filename == '':
                return jsonify({"code": 40000, "message": "No file selected"}), 400

            extract_tables = request.form.get('extract_tables', 'true').lower() == 'true'
            extract_images = request.form.get('extract_images', 'false').lower() == 'true'
            ocr_images = request.form.get('ocr_images', 'true').lower() == 'true'

            # 读取文件内容
            file_data = file.read()

            service = get_ocr_service()
            result = service.extract_from_bytes(
                data=file_data,
                filename=file.filename,
                content_type=file.content_type,
                extract_tables=extract_tables,
                extract_images=extract_images,
                ocr_images=ocr_images,
            )

        return jsonify({
            "code": 0,
            "message": "success",
            "data": result.to_dict()
        })
    except Exception as e:
        logger.error(f"文档内容提取失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/ocr/image", methods=["POST"])
@require_auth
def ocr_image():
    """
    图片 OCR 识别

    支持上传文件或 base64 编码的图片
    """
    try:
        engine = None

        # 检查是否有上传文件
        if 'file' not in request.files:
            # 尝试从 base64 读取
            data = request.get_json()
            if not data or 'image' not in data:
                return jsonify({"code": 40000, "message": "file or image is required"}), 400

            image_base64 = data.get('image')
            engine = data.get('engine')

            # 解码 base64
            try:
                image_data = base64.b64decode(image_base64)
            except Exception as e:
                return jsonify({"code": 40000, "message": f"Invalid base64 image: {e}"}), 400

            service = get_ocr_service()
            results = service.ocr_image(image_data, engine=engine)
        else:
            file = request.files['file']
            if file.filename == '':
                return jsonify({"code": 40000, "message": "No file selected"}), 400

            engine = request.form.get('engine')
            image_data = file.read()

            service = get_ocr_service()
            results = service.ocr_image(image_data, engine=engine)

        # 合并文本
        full_text = " ".join([r.text for r in results])

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "text": full_text,
                "results": [
                    {
                        "text": r.text,
                        "confidence": r.confidence,
                        "bounding_box": r.bounding_box,
                        "block_type": r.block_type,
                    }
                    for r in results
                ],
                "total_items": len(results),
                "average_confidence": sum(r.confidence for r in results) / len(results) if results else 0.0,
            }
        })
    except Exception as e:
        logger.error(f"图片 OCR 识别失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/ocr/structured", methods=["POST"])
@require_auth
def ocr_extract_structured():
    """
    提取结构化数据

    支持的类型：
    - invoice: 发票信息提取
    - id_card: 身份证信息提取
    - contract: 合同关键信息提取
    """
    try:
        # 首先提取文本
        file_data = None
        filename = None
        content_type = None
        data_type = "invoice"

        if 'file' not in request.files:
            # 尝试从 base64 读取
            data = request.get_json()
            if not data or 'content' not in data:
                return jsonify({"code": 40000, "message": "file or content is required"}), 400

            content_base64 = data.get('content')
            filename = data.get('filename', 'document')
            content_type = data.get('content_type')
            data_type = data.get('data_type', 'invoice')

            try:
                file_data = base64.b64decode(content_base64)
            except Exception as e:
                return jsonify({"code": 40000, "message": f"Invalid base64 content: {e}"}), 400
        else:
            file = request.files['file']
            if file.filename == '':
                return jsonify({"code": 40000, "message": "No file selected"}), 400

            filename = file.filename
            content_type = file.content_type
            data_type = request.form.get('data_type', 'invoice')
            file_data = file.read()

        # 提取文档内容
        service = get_ocr_service()
        extraction_result = service.extract_from_bytes(
            data=file_data,
            filename=filename,
            content_type=content_type,
            extract_tables=True,
            ocr_images=True,
        )

        # 提取结构化数据
        structured_data = service.extract_structured_data(
            extraction_result.text,
            data_type=data_type,
        )

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "data_type": data_type,
                "structured_data": structured_data,
                "raw_text": extraction_result.text[:2000] if len(extraction_result.text) > 2000 else extraction_result.text,
                "full_text_length": len(extraction_result.text),
                "table_count": len(extraction_result.tables),
                "errors": extraction_result.errors,
            }
        })
    except Exception as e:
        logger.error(f"结构化数据提取失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/ocr/status", methods=["GET"])
@require_auth
def ocr_get_status():
    """
    获取 OCR 服务状态

    返回可用的 OCR 引擎和配置
    """
    try:
        import os as ocr_os

        # 检查可用的 OCR 引擎
        engines = {
            "tesseract": False,
            "paddleocr": False,
            "easyocr": False,
        }

        try:
            import pytesseract
            engines["tesseract"] = True
        except ImportError:
            pass

        try:
            from paddleocr import PaddleOCR
            engines["paddleocr"] = True
        except ImportError:
            pass

        try:
            import easyocr
            engines["easyocr"] = True
        except ImportError:
            pass

        # 支持的文档类型
        supported_types = [
            {"type": "pdf", "description": "PDF 文档", "extensions": [".pdf"]},
            {"type": "image", "description": "图片", "extensions": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp"]},
            {"type": "word", "description": "Word 文档", "extensions": [".doc", ".docx"]},
            {"type": "text", "description": "文本文件", "extensions": [".txt", ".md", ".csv"]},
        ]

        # 支持的结构化数据类型
        structured_types = [
            {"type": "invoice", "description": "发票信息提取"},
            {"type": "id_card", "description": "身份证信息提取"},
            {"type": "contract", "description": "合同关键信息提取"},
        ]

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "enabled": any(engines.values()),
                "default_engine": ocr_os.getenv("OCR_ENGINE", "auto"),
                "languages": ocr_os.getenv("OCR_LANGUAGES", "chi_sim+eng"),
                "available_engines": engines,
                "supported_document_types": supported_types,
                "supported_structured_types": structured_types,
            }
        })
    except Exception as e:
        logger.error(f"获取 OCR 状态失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/ocr/batch", methods=["POST"])
@require_auth
def ocr_batch_extract():
    """
    批量文档提取

    支持同时处理多个文档
    """
    try:
        data = request.get_json()
        if not data or 'documents' not in data:
            return jsonify({"code": 40000, "message": "documents is required"}), 400

        documents = data.get('documents', [])
        if not documents:
            return jsonify({"code": 40000, "message": "documents cannot be empty"}), 400

        if len(documents) > 10:
            return jsonify({"code": 40000, "message": "Maximum 10 documents allowed"}), 400

        extract_tables = data.get('extract_tables', True)
        ocr_images = data.get('ocr_images', True)

        service = get_ocr_service()
        results = []

        for i, doc in enumerate(documents):
            doc_result = {
                "index": i,
                "filename": doc.get('filename', f'document_{i}'),
                "success": False,
                "error": None,
                "data": None,
            }

            try:
                content_base64 = doc.get('content')
                if not content_base64:
                    doc_result["error"] = "content is required"
                    results.append(doc_result)
                    continue

                file_data = base64.b64decode(content_base64)
                extraction = service.extract_from_bytes(
                    data=file_data,
                    filename=doc.get('filename'),
                    content_type=doc.get('content_type'),
                    extract_tables=extract_tables,
                    ocr_images=ocr_images,
                )

                doc_result["success"] = True
                doc_result["data"] = extraction.to_dict()
            except Exception as e:
                doc_result["error"] = str(e)

            results.append(doc_result)

        success_count = sum(1 for r in results if r["success"])

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "total": len(results),
                "success_count": success_count,
                "failed_count": len(results) - success_count,
                "results": results,
            }
        })
    except Exception as e:
        logger.error(f"批量文档提取失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


# ==================== 元数据驱动 Kettle 配置自动生成 API ====================

# Kettle 配置生成器单例
_kettle_generator = None


def get_kettle_generator():
    """获取 Kettle 配置生成器实例"""
    global _kettle_generator
    if _kettle_generator is None:
        from src.kettle_generator import KettleConfigGenerator
        _kettle_generator = KettleConfigGenerator()
    return _kettle_generator


@app.route("/api/v1/kettle/generate/transformation", methods=["POST"])
@require_auth
def kettle_generate_transformation():
    """
    从元数据生成 Kettle 转换配置

    请求体：
    {
        "source": {
            "connection": { "type": "mysql", "host": "...", "port": 3306, ... },
            "table": "source_table",
            "schema": "source_schema",
            "columns": [{ "column_name": "...", "data_type": "..." }, ...]
        },
        "target": {
            "connection": { "type": "mysql", "host": "...", "port": 3306, ... },
            "table": "target_table",
            "schema": "target_schema",
            "columns": [{ "column_name": "...", "data_type": "..." }, ...]
        },
        "options": {
            "name": "transformation_name",
            "write_mode": "insert",
            "batch_size": 1000,
            "incremental_field": "",
            "filter_condition": "",
            "column_mappings": { "source_col": "target_col" }
        }
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"code": 40000, "message": "Request body is required"}), 400

        source = data.get("source", {})
        target = data.get("target", {})
        options = data.get("options", {})

        # 验证必要参数
        if not source.get("connection"):
            return jsonify({"code": 40000, "message": "source.connection is required"}), 400
        if not source.get("table"):
            return jsonify({"code": 40000, "message": "source.table is required"}), 400
        if not target.get("connection"):
            return jsonify({"code": 40000, "message": "target.connection is required"}), 400
        if not target.get("table"):
            return jsonify({"code": 40000, "message": "target.table is required"}), 400

        # 构建元数据
        source_meta = {
            "table_name": source.get("table"),
            "schema": source.get("schema", ""),
            "columns": source.get("columns", []),
        }
        target_meta = {
            "table_name": target.get("table"),
            "schema": target.get("schema", ""),
            "columns": target.get("columns", source.get("columns", [])),
        }

        generator = get_kettle_generator()
        transformation_name = options.get("name", f"sync_{source.get('table')}_to_{target.get('table')}")

        xml_content = generator.generate_from_metadata(
            source_table_meta=source_meta,
            target_table_meta=target_meta,
            source_connection=source.get("connection"),
            target_connection=target.get("connection"),
            transformation_name=transformation_name,
            options=options,
        )

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "name": transformation_name,
                "type": "transformation",
                "format": "ktr",
                "content": xml_content,
                "source_table": source.get("table"),
                "target_table": target.get("table"),
                "column_count": len(source.get("columns", [])),
            }
        })
    except Exception as e:
        logger.error(f"生成 Kettle 转换配置失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/kettle/generate/job", methods=["POST"])
@require_auth
def kettle_generate_job():
    """
    生成 Kettle 作业配置

    请求体：
    {
        "name": "job_name",
        "description": "job description",
        "transformations": ["/path/to/trans1.ktr", "/path/to/trans2.ktr"],
        "sequential": true
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"code": 40000, "message": "Request body is required"}), 400

        job_name = data.get("name")
        if not job_name:
            return jsonify({"code": 40000, "message": "name is required"}), 400

        transformations = data.get("transformations", [])
        if not transformations:
            return jsonify({"code": 40000, "message": "transformations is required"}), 400

        description = data.get("description", "")
        sequential = data.get("sequential", True)

        generator = get_kettle_generator()
        xml_content = generator.generate_job(
            job_name=job_name,
            transformations=transformations,
            description=description,
            sequential=sequential,
        )

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "name": job_name,
                "type": "job",
                "format": "kjb",
                "content": xml_content,
                "transformation_count": len(transformations),
                "sequential": sequential,
            }
        })
    except Exception as e:
        logger.error(f"生成 Kettle 作业配置失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/kettle/generate/from-etl-task/<task_id>", methods=["POST"])
@require_auth
def kettle_generate_from_etl_task(task_id: str):
    """
    从 ETL 任务配置生成 Kettle 转换

    基于已有的 ETL 任务配置自动生成对应的 Kettle 转换文件
    """
    try:
        db = get_db()

        # 获取 ETL 任务
        task = db.query(ETLTask).filter(ETLTask.task_id == task_id).first()
        if not task:
            return jsonify({"code": 40400, "message": "ETL task not found"}), 404

        # 解析任务配置
        source_config = task.source_config or {}
        target_config = task.target_config or {}
        options = request.get_json() or {}

        # 获取源表元数据
        source_columns = []
        if source_config.get("table"):
            # 尝试从元数据表获取列信息
            table = db.query(MetadataTable).filter(
                MetadataTable.table_name == source_config.get("table")
            ).first()
            if table:
                columns = db.query(MetadataColumn).filter(
                    MetadataColumn.table_id == table.id
                ).all()
                source_columns = [
                    {"column_name": col.column_name, "data_type": col.data_type}
                    for col in columns
                ]

        # 如果没有元数据，使用任务配置中的字段映射
        if not source_columns and task.mapping_config:
            mapping_config = task.mapping_config if isinstance(task.mapping_config, dict) else {}
            field_mappings = mapping_config.get("field_mappings", [])
            source_columns = [
                {"column_name": m.get("source_field", ""), "data_type": m.get("source_type", "string")}
                for m in field_mappings
            ]

        # 构建源连接配置
        source_connection = {
            "type": source_config.get("type", "mysql"),
            "host": source_config.get("host", "localhost"),
            "port": source_config.get("port", 3306),
            "database": source_config.get("database", ""),
            "username": source_config.get("username", ""),
            "password": source_config.get("password", ""),
            "schema": source_config.get("schema", ""),
        }

        # 构建目标连接配置
        target_connection = {
            "type": target_config.get("type", "mysql"),
            "host": target_config.get("host", "localhost"),
            "port": target_config.get("port", 3306),
            "database": target_config.get("database", ""),
            "username": target_config.get("username", ""),
            "password": target_config.get("password", ""),
            "schema": target_config.get("schema", ""),
        }

        # 构建元数据
        source_meta = {
            "table_name": source_config.get("table", "source"),
            "schema": source_config.get("schema", ""),
            "columns": source_columns,
        }
        target_meta = {
            "table_name": target_config.get("table", "target"),
            "schema": target_config.get("schema", ""),
            "columns": source_columns,  # 默认同结构
        }

        # 生成配置
        generator = get_kettle_generator()
        transformation_name = options.get("name", f"etl_task_{task_id}")

        xml_content = generator.generate_from_metadata(
            source_table_meta=source_meta,
            target_table_meta=target_meta,
            source_connection=source_connection,
            target_connection=target_connection,
            transformation_name=transformation_name,
            options={
                "write_mode": target_config.get("write_mode", "insert"),
                "batch_size": target_config.get("batch_size", 1000),
                "incremental_field": task.incremental_field or "",
                **options,
            },
        )

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "task_id": task_id,
                "task_name": task.name,
                "name": transformation_name,
                "type": "transformation",
                "format": "ktr",
                "content": xml_content,
                "source_table": source_config.get("table"),
                "target_table": target_config.get("table"),
                "column_count": len(source_columns),
            }
        })
    except Exception as e:
        logger.error(f"从 ETL 任务生成 Kettle 配置失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/kettle/generate/from-metadata", methods=["POST"])
@require_auth
def kettle_generate_from_metadata_api():
    """
    从元数据表自动生成 Kettle 转换

    请求体：
    {
        "source_table_id": "table_uuid",
        "target_table_id": "table_uuid",
        "source_connection": { "type": "mysql", "host": "...", ... },
        "target_connection": { "type": "mysql", "host": "...", ... },
        "options": { ... }
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"code": 40000, "message": "Request body is required"}), 400

        source_table_id = data.get("source_table_id")
        target_table_id = data.get("target_table_id")

        if not source_table_id:
            return jsonify({"code": 40000, "message": "source_table_id is required"}), 400
        if not target_table_id:
            return jsonify({"code": 40000, "message": "target_table_id is required"}), 400

        db = get_db()

        # 获取源表元数据
        source_table = db.query(MetadataTable).filter(
            MetadataTable.table_id == source_table_id
        ).first()
        if not source_table:
            return jsonify({"code": 40400, "message": "Source table not found"}), 404

        source_columns = db.query(MetadataColumn).filter(
            MetadataColumn.table_id == source_table.id
        ).all()

        # 获取目标表元数据
        target_table = db.query(MetadataTable).filter(
            MetadataTable.table_id == target_table_id
        ).first()
        if not target_table:
            return jsonify({"code": 40400, "message": "Target table not found"}), 404

        target_columns = db.query(MetadataColumn).filter(
            MetadataColumn.table_id == target_table.id
        ).all()

        # 构建源连接配置
        source_connection = data.get("source_connection", {})
        if not source_connection:
            # 尝试从数据源获取连接信息
            if source_table.datasource_id:
                datasource = db.query(DataSource).filter(
                    DataSource.datasource_id == source_table.datasource_id
                ).first()
                if datasource:
                    source_connection = datasource.connection_config or {}
                    source_connection["type"] = datasource.type

        target_connection = data.get("target_connection", {})
        if not target_connection:
            if target_table.datasource_id:
                datasource = db.query(DataSource).filter(
                    DataSource.datasource_id == target_table.datasource_id
                ).first()
                if datasource:
                    target_connection = datasource.connection_config or {}
                    target_connection["type"] = datasource.type

        # 构建元数据
        source_meta = {
            "table_name": source_table.table_name,
            "schema": source_table.schema_name or "",
            "columns": [
                {"column_name": col.column_name, "data_type": col.data_type}
                for col in source_columns
            ],
        }
        target_meta = {
            "table_name": target_table.table_name,
            "schema": target_table.schema_name or "",
            "columns": [
                {"column_name": col.column_name, "data_type": col.data_type}
                for col in target_columns
            ],
        }

        options = data.get("options", {})
        transformation_name = options.get("name", f"sync_{source_table.table_name}_to_{target_table.table_name}")

        generator = get_kettle_generator()
        xml_content = generator.generate_from_metadata(
            source_table_meta=source_meta,
            target_table_meta=target_meta,
            source_connection=source_connection,
            target_connection=target_connection,
            transformation_name=transformation_name,
            options=options,
        )

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "name": transformation_name,
                "type": "transformation",
                "format": "ktr",
                "content": xml_content,
                "source_table": source_table.table_name,
                "target_table": target_table.table_name,
                "source_column_count": len(source_columns),
                "target_column_count": len(target_columns),
            }
        })
    except Exception as e:
        logger.error(f"从元数据生成 Kettle 配置失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/kettle/types", methods=["GET"])
@require_auth
def kettle_get_types():
    """
    获取 Kettle 支持的类型和选项
    """
    try:
        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "source_types": [
                    {"value": "mysql", "label": "MySQL"},
                    {"value": "postgresql", "label": "PostgreSQL"},
                    {"value": "oracle", "label": "Oracle"},
                    {"value": "sqlserver", "label": "SQL Server"},
                    {"value": "hive", "label": "Hive"},
                    {"value": "csv", "label": "CSV 文件"},
                    {"value": "excel", "label": "Excel 文件"},
                    {"value": "json", "label": "JSON 文件"},
                ],
                "write_modes": [
                    {"value": "insert", "label": "插入 (INSERT)"},
                    {"value": "update", "label": "更新 (UPDATE)"},
                    {"value": "upsert", "label": "更新或插入 (UPSERT)"},
                    {"value": "truncate_insert", "label": "清空后插入 (TRUNCATE + INSERT)"},
                ],
                "data_types": [
                    {"value": "String", "label": "字符串"},
                    {"value": "Integer", "label": "整数"},
                    {"value": "Number", "label": "数值"},
                    {"value": "BigNumber", "label": "大数值"},
                    {"value": "Date", "label": "日期"},
                    {"value": "Boolean", "label": "布尔"},
                    {"value": "Binary", "label": "二进制"},
                ],
                "log_levels": [
                    {"value": "Nothing", "label": "无日志"},
                    {"value": "Error", "label": "仅错误"},
                    {"value": "Minimal", "label": "最小"},
                    {"value": "Basic", "label": "基本"},
                    {"value": "Detailed", "label": "详细"},
                    {"value": "Debug", "label": "调试"},
                    {"value": "Rowlevel", "label": "行级"},
                ],
            }
        })
    except Exception as e:
        logger.error(f"获取 Kettle 类型失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


# ==================== AI 能力增强 API ====================

@app.route("/api/v1/quality/recommend-cleaning", methods=["POST"])
@require_jwt()
def recommend_cleaning_rules():
    """
    AI 清洗规则推荐

    基于数据质量问题自动推荐清洗规则
    """
    db = get_db_session()
    data = request.json or {}

    try:
        from services.ai_cleaning_advisor import get_ai_cleaning_advisor

        advisor = get_ai_cleaning_advisor()

        # 获取质量告警（如果提供了 table_id）
        table_id = data.get("table_id")
        quality_alerts = data.get("quality_alerts", [])

        # 如果提供了表名，分析表的质量问题
        if table_id and not quality_alerts:
            recommendations = advisor.analyze_table_quality_issues(
                db=db,
                table_name=table_id,
                database_name=data.get("database_name")
            )
        else:
            # 基于告警生成建议
            recommendations = advisor.analyze_quality_alerts(quality_alerts)

        # 可选：生成 Kettle 步骤配置
        include_kettle = data.get("include_kettle_steps", False)
        kettle_steps = []
        if include_kettle and recommendations:
            kettle_steps = advisor.generate_kettle_steps(recommendations)

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "recommendations": [r.to_dict() for r in recommendations],
                "total_count": len(recommendations),
                "kettle_steps": kettle_steps if include_kettle else None,
            }
        })
    except ImportError as e:
        return jsonify({"code": 50001, "message": f"AI 清洗服务不可用: {e}"}), 500
    except Exception as e:
        logger.error(f"AI 清洗规则推荐失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/quality/analyze-table", methods=["POST"])
@require_jwt()
def analyze_table_quality():
    """
    AI 分析表的数据质量问题

    自动检测并推荐清洗规则
    """
    db = get_db_session()
    data = request.json or {}

    try:
        from services.ai_cleaning_advisor import get_ai_cleaning_advisor

        advisor = get_ai_cleaning_advisor()

        table_name = data.get("table_name")
        if not table_name:
            return jsonify({"code": 40001, "message": "table_name 不能为空"}), 400

        database_name = data.get("database_name")

        recommendations = advisor.analyze_table_quality_issues(
            db=db,
            table_name=table_name,
            database_name=database_name
        )

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "table_name": table_name,
                "database_name": database_name,
                "issues_found": len(recommendations),
                "recommendations": [r.to_dict() for r in recommendations],
            }
        })
    except ImportError as e:
        return jsonify({"code": 50001, "message": f"AI 清洗服务不可用: {e}"}), 500
    except Exception as e:
        logger.error(f"AI 表质量分析失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/quality/recommend-column-rules", methods=["POST"])
@require_jwt()
def recommend_column_rules():
    """
    为单个列推荐清洗规则

    基于列信息和样本数据推荐规则
    """
    data = request.json or {}

    try:
        from services.ai_cleaning_advisor import get_ai_cleaning_advisor

        advisor = get_ai_cleaning_advisor()

        column_info = data.get("column_info")
        if not column_info:
            return jsonify({"code": 40001, "message": "column_info 不能为空"}), 400

        recommendations = advisor.recommend_rules_for_column(column_info)

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "column_name": column_info.get("name"),
                "recommendations": [r.to_dict() for r in recommendations],
                "total_count": len(recommendations),
            }
        })
    except ImportError as e:
        return jsonify({"code": 50001, "message": f"AI 清洗服务不可用: {e}"}), 500
    except Exception as e:
        logger.error(f"AI 列规则推荐失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/quality/rule-templates", methods=["GET"])
@require_jwt()
def get_rule_templates():
    """
    获取可用的清洗规则模板

    返回预定义的规则模板供用户选择
    """
    try:
        from services.ai_cleaning_advisor import get_ai_cleaning_advisor

        advisor = get_ai_cleaning_advisor()

        templates = []
        for category, rules in advisor._rule_templates.items():
            for rule in rules:
                templates.append({
                    "category": category,
                    "rule_type": rule["rule_type"],
                    "name": rule["rule_name"],
                    "expression": rule["rule_expression"],
                    "severity": rule["severity"],
                    "config_template": rule["config_template"],
                })

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "templates": templates,
                "total": len(templates),
                "categories": list(advisor._rule_templates.keys()),
            }
        })
    except ImportError as e:
        return jsonify({"code": 50001, "message": f"AI 清洗服务不可用: {e}"}), 500
    except Exception as e:
        logger.error(f"获取规则模板失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/data/impute-missing", methods=["POST"])
@require_jwt()
def impute_missing_values():
    """
    AI 缺失值填充

    基于数据模式智能填充缺失值
    """
    data = request.json

    try:
        from src.ai_imputation import get_ai_imputation_service

        service = get_ai_imputation_service()

        # 获取参数
        column_name = data.get("column_name")
        column_type = data.get("column_type", "string")
        sample_values = data.get("sample_values", [])
        strategy = data.get("strategy")  # 可选，不指定则自动推荐
        context = data.get("context", {})

        if not column_name:
            return jsonify({"code": 40001, "message": "column_name 不能为空"}), 400

        # 分析缺失模式
        analysis = service.analyze_missing_patterns(
            data=sample_values,
            column=column_name,
            column_type=column_type,
        )

        # 推荐策略（如果未指定）
        if not strategy:
            strategy = service.recommend_imputation_strategy(analysis, context)

        # 执行填充
        result = service.impute_values(
            data=sample_values,
            column=column_name,
            strategy=strategy,
            column_type=column_type,
        )

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "analysis": analysis.to_dict() if hasattr(analysis, 'to_dict') else analysis,
                "strategy": strategy.value if hasattr(strategy, 'value') else strategy,
                "result": result.to_dict() if hasattr(result, 'to_dict') else result,
            }
        })
    except ImportError as e:
        return jsonify({"code": 50001, "message": f"AI 填充服务不可用: {e}"}), 500
    except Exception as e:
        logger.error(f"AI 缺失值填充失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/data/impute-preview", methods=["POST"])
@require_jwt()
def preview_imputation():
    """
    缺失值填充预览

    预览填充结果而不实际修改数据
    """
    data = request.json

    try:
        from src.ai_imputation import get_ai_imputation_service

        service = get_ai_imputation_service()

        column_name = data.get("column_name")
        column_type = data.get("column_type", "string")
        sample_values = data.get("sample_values", [])
        strategy = data.get("strategy")

        if not column_name:
            return jsonify({"code": 40001, "message": "column_name 不能为空"}), 400

        # 预览填充
        preview = service.preview_imputation(
            data=sample_values,
            column=column_name,
            strategy=strategy,
            column_type=column_type,
            preview_count=data.get("preview_count", 10),
        )

        return jsonify({
            "code": 0,
            "message": "success",
            "data": preview
        })
    except ImportError as e:
        return jsonify({"code": 50001, "message": f"AI 填充服务不可用: {e}"}), 500
    except Exception as e:
        logger.error(f"缺失值填充预览失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/assets/semantic-search", methods=["POST"])
@require_jwt()
def semantic_search_assets():
    """
    语义资产检索

    基于自然语言查询数据资产
    """
    data = request.json

    try:
        from src.semantic_search import get_semantic_search_service

        service = get_semantic_search_service()

        query = data.get("query")
        if not query:
            return jsonify({"code": 40001, "message": "query 不能为空"}), 400

        top_k = data.get("top_k", 10)
        filters = data.get("filters")  # {"asset_type": "table", "database": "xxx"}
        rerank = data.get("rerank", True)

        # 执行搜索
        results = service.search(
            query=query,
            top_k=top_k,
            filters=filters,
            rerank=rerank,
        )

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "query": query,
                "results": [r.to_dict() for r in results],
                "total_count": len(results),
            }
        })
    except ImportError as e:
        return jsonify({"code": 50001, "message": f"语义检索服务不可用: {e}"}), 500
    except Exception as e:
        logger.error(f"语义资产检索失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/assets/semantic-search/index", methods=["POST"])
@require_jwt()
def index_asset_for_search():
    """
    索引数据资产用于语义检索
    """
    db = next(get_db())
    data = request.json

    try:
        from src.semantic_search import get_semantic_search_service, DataAsset, AssetType

        service = get_semantic_search_service()

        # 批量索引
        if data.get("batch"):
            table_ids = data.get("table_ids", [])
            indexed_count = 0

            for table_id in table_ids:
                table = db.query(MetadataTable).filter(
                    MetadataTable.table_id == table_id
                ).first()

                if table:
                    columns = db.query(MetadataColumn).filter(
                        MetadataColumn.table_id == table.id
                    ).all()

                    asset = DataAsset(
                        id=table.table_id,
                        name=table.table_name,
                        asset_type=AssetType.TABLE,
                        database=table.database_name or "",
                        schema=table.schema_name or "",
                        description=table.description or table.ai_description or "",
                        columns=[{"name": c.column_name, "type": c.data_type} for c in columns],
                        tags=table.tags.split(",") if table.tags else [],
                        owner=table.owner or "",
                    )

                    if service.index_asset(asset):
                        indexed_count += 1

            return jsonify({
                "code": 0,
                "message": "success",
                "data": {
                    "indexed_count": indexed_count,
                    "total_requested": len(table_ids),
                }
            })

        # 单个索引
        table_id = data.get("table_id")
        if not table_id:
            return jsonify({"code": 40001, "message": "table_id 不能为空"}), 400

        table = db.query(MetadataTable).filter(
            MetadataTable.table_id == table_id
        ).first()

        if not table:
            return jsonify({"code": 40401, "message": "表不存在"}), 404

        columns = db.query(MetadataColumn).filter(
            MetadataColumn.table_id == table.id
        ).all()

        asset = DataAsset(
            id=table.table_id,
            name=table.table_name,
            asset_type=AssetType.TABLE,
            database=table.database_name or "",
            schema=table.schema_name or "",
            description=table.description or table.ai_description or "",
            columns=[{"name": c.column_name, "type": c.data_type} for c in columns],
            tags=table.tags.split(",") if table.tags else [],
            owner=table.owner or "",
        )

        success = service.index_asset(asset)

        return jsonify({
            "code": 0,
            "message": "success" if success else "索引失败",
            "data": {
                "indexed": success,
                "table_id": table_id,
            }
        })
    except ImportError as e:
        return jsonify({"code": 50001, "message": f"语义检索服务不可用: {e}"}), 500
    except Exception as e:
        logger.error(f"资产索引失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/assets/semantic-search/stats", methods=["GET"])
@require_jwt()
def get_semantic_search_stats():
    """
    获取语义检索服务状态
    """
    try:
        from src.semantic_search import get_semantic_search_service

        service = get_semantic_search_service()
        stats = service.get_stats()

        return jsonify({
            "code": 0,
            "message": "success",
            "data": stats
        })
    except ImportError as e:
        return jsonify({"code": 50001, "message": f"语义检索服务不可用: {e}"}), 500
    except Exception as e:
        logger.error(f"获取语义检索状态失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/assets/similar/<asset_id>", methods=["GET"])
@require_jwt()
def get_similar_assets(asset_id):
    """
    获取相似资产
    """
    try:
        from src.semantic_search import get_semantic_search_service

        service = get_semantic_search_service()
        top_k = request.args.get("top_k", 5, type=int)

        results = service.get_similar_assets(asset_id, top_k)

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "asset_id": asset_id,
                "similar_assets": [r.to_dict() for r in results],
            }
        })
    except ImportError as e:
        return jsonify({"code": 50001, "message": f"语义检索服务不可用: {e}"}), 500
    except Exception as e:
        logger.error(f"获取相似资产失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


# ==================== AI 资产检索增强 API ====================

@app.route("/api/v1/assets/ai/search", methods=["POST"])
@require_jwt()
def ai_search_assets():
    """
    AI 自然语言搜索资产

    支持自然语言查询，例如：
    - "用户订单相关的表"
    - "包含手机号的数据"
    - "最近更新的客户表"
    """
    data = request.json or {}

    try:
        from services.ai_asset_search import get_ai_asset_search_service

        service = get_ai_asset_search_service()

        query = data.get("query")
        if not query:
            return jsonify({"code": 40001, "message": "query 不能为空"}), 400

        limit = data.get("limit", 20)
        filters = data.get("filters")

        db = get_db_session()
        try:
            results = service.natural_search(
                db=db,
                tenant_id=data.get("tenant_id", "default"),
                query=query,
                limit=limit,
                filters=filters
            )
            return jsonify({
                "code": 0,
                "message": "success",
                "data": results
            })
        finally:
            db.close()

    except ImportError as e:
        return jsonify({"code": 50001, "message": f"AI 检索服务不可用: {e}"}), 500
    except Exception as e:
        logger.error(f"AI 搜索失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/assets/ai/semantic-search", methods=["POST"])
@require_jwt()
def ai_semantic_search_assets():
    """
    AI 语义搜索资产（基于向量相似度）
    """
    data = request.json or {}

    try:
        from services.ai_asset_search import get_ai_asset_search_service

        service = get_ai_asset_search_service()

        query = data.get("query")
        if not query:
            return jsonify({"code": 40001, "message": "query 不能为空"}), 400

        limit = data.get("limit", 20)
        filters = data.get("filters")

        db = get_db_session()
        try:
            results = service.semantic_search(
                db=db,
                tenant_id=data.get("tenant_id", "default"),
                query=query,
                limit=limit,
                filters=filters
            )
            return jsonify({
                "code": 0,
                "message": "success",
                "data": results
            })
        finally:
            db.close()

    except ImportError as e:
        return jsonify({"code": 50001, "message": f"AI 检索服务不可用: {e}"}), 500
    except Exception as e:
        logger.error(f"AI 语义搜索失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/assets/ai/recommend/<asset_id>", methods=["GET"])
@require_jwt()
def ai_recommend_assets(asset_id):
    """
    AI 推荐相关资产
    """
    try:
        from services.ai_asset_search import get_ai_asset_search_service

        service = get_ai_asset_search_service()

        limit = request.args.get("limit", 10, type=int)
        tenant_id = request.args.get("tenant_id", "default")

        db = get_db_session()
        try:
            results = service.recommend_assets(
                db=db,
                tenant_id=tenant_id,
                asset_id=asset_id,
                limit=limit
            )
            return jsonify({
                "code": 0,
                "message": "success",
                "data": results
            })
        finally:
            db.close()

    except ImportError as e:
        return jsonify({"code": 50001, "message": f"AI 检索服务不可用: {e}"}), 500
    except Exception as e:
        logger.error(f"AI 推荐失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/assets/ai/trending", methods=["GET"])
@require_jwt()
def ai_get_trending_assets():
    """
    获取热门资产
    """
    try:
        from services.ai_asset_search import get_ai_asset_search_service

        service = get_ai_asset_search_service()

        days = request.args.get("days", 7, type=int)
        limit = request.args.get("limit", 10, type=int)
        tenant_id = request.args.get("tenant_id", "default")

        db = get_db_session()
        try:
            results = service.get_trending_assets(
                db=db,
                tenant_id=tenant_id,
                days=days,
                limit=limit
            )
            return jsonify({
                "code": 0,
                "message": "success",
                "data": results
            })
        finally:
            db.close()

    except ImportError as e:
        return jsonify({"code": 50001, "message": f"AI 检索服务不可用: {e}"}), 500
    except Exception as e:
        logger.error(f"获取热门资产失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/assets/ai/autocomplete", methods=["GET"])
@require_jwt()
def ai_autocomplete_assets():
    """
    搜索补全建议
    """
    try:
        from services.ai_asset_search import get_ai_asset_search_service

        service = get_ai_asset_search_service()

        prefix = request.args.get("prefix")
        if not prefix:
            return jsonify({"code": 40001, "message": "prefix 不能为空"}), 400

        limit = request.args.get("limit", 10, type=int)
        tenant_id = request.args.get("tenant_id", "default")

        db = get_db_session()
        try:
            results = service.autocomplete(
                db=db,
                tenant_id=tenant_id,
                prefix=prefix,
                limit=limit
            )
            return jsonify({
                "code": 0,
                "message": "success",
                "data": results
            })
        finally:
            db.close()

    except ImportError as e:
        return jsonify({"code": 50001, "message": f"AI 检索服务不可用: {e}"}), 500
    except Exception as e:
        logger.error(f"补全建议失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


# ==================== AI 字段映射 API ====================

@app.route("/api/v1/mapping/suggest", methods=["POST"])
@require_jwt()
def suggest_field_mappings():
    """
    智能推荐字段映射
    """
    try:
        from services.ai_field_mapping import get_ai_field_mapping_service

        service = get_ai_field_mapping_service()

        data = request.json
        source_table = data.get("source_table")
        target_table = data.get("target_table")
        source_database = data.get("source_database")
        target_database = data.get("target_database")
        options = data.get("options", {})

        if not source_table or not target_table:
            return jsonify({"code": 40001, "message": "source_table 和 target_table 不能为空"}), 400

        db = get_db_session()
        try:
            result = service.suggest_field_mappings(
                db=db,
                source_table=source_table,
                source_database=source_database,
                target_table=target_table,
                target_database=target_database,
                options=options
            )

            if "error" in result:
                return jsonify({"code": 40002, "message": result["error"]}), 400

            return jsonify({
                "code": 0,
                "message": "success",
                "data": result
            })
        finally:
            db.close()

    except ImportError as e:
        return jsonify({"code": 50001, "message": f"字段映射服务不可用: {e}"}), 500
    except Exception as e:
        logger.error(f"字段映射推荐失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/mapping/type-conversions", methods=["POST"])
@require_jwt()
def suggest_type_conversions():
    """
    推荐数据类型转换策略
    """
    try:
        from services.ai_field_mapping import get_ai_field_mapping_service

        service = get_ai_field_mapping_service()

        data = request.json
        mappings = data.get("mappings", [])
        source_schema = data.get("source_schema", [])
        target_schema = data.get("target_schema", [])

        if not mappings:
            return jsonify({"code": 40001, "message": "mappings 不能为空"}), 400

        result = service.suggest_data_type_conversions(
            mappings=mappings,
            source_schema=source_schema,
            target_schema=target_schema
        )

        return jsonify({
            "code": 0,
            "message": "success",
            "data": result
        })

    except Exception as e:
        logger.error(f"类型转换推荐失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/mapping/generate-sql", methods=["POST"])
@require_jwt()
def generate_transformation_sql():
    """
    生成字段转换 SQL
    """
    try:
        from services.ai_field_mapping import get_ai_field_mapping_service

        service = get_ai_field_mapping_service()

        data = request.json
        mappings = data.get("mappings", [])
        source_table = data.get("source_table")
        target_table = data.get("target_table", "target_table")

        if not mappings or not source_table:
            return jsonify({"code": 40001, "message": "mappings 和 source_table 不能为空"}), 400

        result = service.generate_transformation_sql(
            mappings=mappings,
            source_table=source_table,
            target_table=target_table
        )

        return jsonify({
            "code": 0,
            "message": "success",
            "data": result
        })

    except Exception as e:
        logger.error(f"SQL 生成失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/mapping/detect-conflicts", methods=["POST"])
@require_jwt()
def detect_mapping_conflicts():
    """
    检测映射冲突
    """
    try:
        from services.ai_field_mapping import get_ai_field_mapping_service

        service = get_ai_field_mapping_service()

        data = request.json
        mappings = data.get("mappings", [])
        target_schema = data.get("target_schema", [])

        if not mappings:
            return jsonify({"code": 40001, "message": "mappings 不能为空"}), 400

        conflicts = service.detect_mapping_conflicts(
            mappings=mappings,
            target_schema=target_schema
        )

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "conflicts": conflicts,
                "conflict_count": len(conflicts)
            }
        })

    except Exception as e:
        logger.error(f"冲突检测失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/mapping/derived-fields", methods=["POST"])
@require_jwt()
def suggest_derived_fields():
    """
    推荐派生字段映射
    """
    try:
        from services.ai_field_mapping import get_ai_field_mapping_service

        service = get_ai_field_mapping_service()

        data = request.json
        source_columns = data.get("source_columns", [])
        target_columns = data.get("target_columns", [])
        context = data.get("context", {})

        if not source_columns or not target_columns:
            return jsonify({"code": 40001, "message": "source_columns 和 target_columns 不能为空"}), 400

        suggestions = service.suggest_derived_fields(
            source_columns=source_columns,
            target_columns=target_columns,
            context=context
        )

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "suggestions": [s.to_dict() for s in suggestions],
                "count": len(suggestions)
            }
        })

    except Exception as e:
        logger.error(f"派生字段推荐失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/mapping/tables/<database_name>", methods=["GET"])
@require_jwt()
def list_tables_for_mapping(database_name: str):
    """
    获取指定数据库的表列表（用于映射选择）
    """
    try:
        db = get_db_session()
        try:
            from models.metadata import MetadataTable

            tables = db.query(MetadataTable).filter(
                MetadataTable.database_name == database_name
            ).order_by(MetadataTable.table_name).all()

            return jsonify({
                "code": 0,
                "message": "success",
                "data": {
                    "tables": [
                        {
                            "table_name": t.table_name,
                            "database_name": t.database_name,
                            "table_comment": t.table_comment,
                            "column_count": t.column_count or 0
                        }
                        for t in tables
                    ],
                    "total": len(tables)
                }
            })
        finally:
            db.close()

    except Exception as e:
        logger.error(f"获取表列表失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


# ==================== ETL AI 增强 API ====================

@app.route("/api/v1/etl/ai/profiling", methods=["POST"])
@require_jwt()
def etl_ai_profiling():
    """
    AI 数据源画像分析

    自动分析数据源的模式、数据分布和特征
    """
    data = request.json

    try:
        source_connection_id = data.get("source_connection_id")
        table_name = data.get("table_name")
        sample_size = data.get("sample_size", 1000)

        if not source_connection_id:
            return jsonify({"code": 40001, "message": "source_connection_id 不能为空"}), 400

        db = get_db_session()
        try:
            from models.metadata import MetadataTable, MetadataColumn
            from sqlalchemy import text

            # 获取数据源连接信息
            from models import DataSource
            source = db.query(DataSource).filter(
                DataSource.source_id == source_connection_id
            ).first()

            if not source:
                return jsonify({"code": 40400, "message": "数据源不存在"}), 404

            # 获取表信息
            table_query = db.query(MetadataTable).filter(
                MetadataTable.table_name == table_name
            )
            if source.connection_config and source.connection_config.get("database"):
                table_query = table_query.filter(
                    MetadataTable.database_name == source.connection_config["database"]
                )

            table = table_query.first()

            # 获取列信息
            columns = db.query(MetadataColumn).filter(
                MetadataColumn.table_name == table_name
            ).all() if table else []

            # 尝试采样数据
            sample_data = []
            column_stats = {}

            if columns:
                try:
                    # 构建采样 SQL
                    col_names = [c.column_name for c in columns[:10]]
                    sql = f"SELECT {', '.join(col_names)} FROM {table_name} LIMIT {sample_size}"

                    # 这里应该使用实际的数据源连接执行查询
                    # 简化版本：使用元数据推断
                    for col in columns:
                        column_stats[col.column_name] = {
                            "type": col.column_type or "unknown",
                            "nullable": col.is_nullable,
                            "description": col.description,
                            "sensitivity_type": col.sensitivity_type,
                            "has_ai_annotation": bool(col.ai_description),
                        }

                except Exception as e:
                    logger.warning(f"数据采样失败: {e}")

            # 使用 AI 分析数据模式
            from services.ai_service import get_ai_service
            ai_service = get_ai_service()

            # 模式发现
            patterns = {
                "primary_keys": [c.column_name for c in columns if c.column_name and "id" in c.column_name.lower()],
                "timestamp_columns": [c.column_name for c in columns if c.column_name and any(t in c.column_name.lower() for t in ["time", "date", "at", "created", "updated"])],
                "status_columns": [c.column_name for c in columns if c.column_name and "status" in c.column_name.lower()],
                "sensitive_columns": [c.column_name for c in columns if c.sensitivity_type and c.sensitivity_type != "none"],
            }

            profile_result = {
                "source_connection_id": source_connection_id,
                "table_name": table_name,
                "column_count": len(columns),
                "columns": column_stats,
                "patterns": patterns,
                "data_quality_score": 0.8,  # 简化版本
                "recommendations": [
                    "建议为敏感列添加脱敏规则",
                    "建议为时间列创建索引",
                    "建议对主键列添加唯一约束"
                ]
            }

            return jsonify({
                "code": 0,
                "message": "success",
                "data": profile_result
            })
        finally:
            db.close()

    except Exception as e:
        logger.error(f"ETL AI 画像分析失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/etl/ai/transformation-suggest", methods=["POST"])
@require_jwt()
def etl_ai_transformation_suggest():
    """
    转换逻辑推荐

    基于源字段和目标字段差异推荐转换逻辑
    """
    data = request.json

    try:
        source_columns = data.get("source_columns", [])
        target_columns = data.get("target_columns", [])

        if not source_columns or not target_columns:
            return jsonify({"code": 40001, "message": "source_columns 和 target_columns 不能为空"}), 400

        from services.ai_service import get_ai_service
        ai_service = get_ai_service()

        # 构建转换建议
        transformations = []

        # 为每个目标字段找对应的源字段并推荐转换
        target_map = {c.get("name"): c for c in target_columns}

        for source_col in source_columns:
            source_name = source_col.get("name")
            source_type = source_col.get("type", "varchar")

            # 查找可能的目标字段
            possible_targets = [t for t in target_columns if t.get("name") == source_name]

            for target_col in possible_targets:
                target_type = target_col.get("type", "varchar")
                target_name = target_col.get("name")

                transformation = {
                    "source_field": source_name,
                    "target_field": target_name,
                    "source_type": source_type,
                    "target_type": target_type,
                    "needs_conversion": source_type != target_type,
                }

                # 根据类型差异推荐转换
                if source_type != target_type:
                    if "int" in source_type.lower() and "varchar" in target_type.lower():
                        transformation["sql"] = f"CAST({source_name} AS VARCHAR)"
                        transformation["description"] = "数值转字符串"
                    elif "varchar" in source_type.lower() and "int" in target_type.lower():
                        transformation["sql"] = f"CAST(NULLIF({source_name}, '') AS INTEGER)"
                        transformation["description"] = "字符串转数值"
                    elif "date" in source_type.lower() and "varchar" in target_type.lower():
                        transformation["sql"] = f"TO_CHAR({source_name}, 'YYYY-MM-DD')"
                        transformation["description"] = "日期转字符串"
                    elif "varchar" in source_type.lower() and "date" in target_type.lower():
                        transformation["sql"] = f"TO_DATE({source_name}, 'YYYY-MM-DD')"
                        transformation["description"] = "字符串转日期"
                    else:
                        transformation["sql"] = f"{source_name}"
                        transformation["description"] = "直接映射"
                else:
                    transformation["sql"] = f"{source_name}"
                    transformation["description"] = "直接映射"

                transformations.append(transformation)

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "transformations": transformations,
                "total_count": len(transformations),
            }
        })

    except Exception as e:
        logger.error(f"ETL 转换推荐失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/etl/ai/field-mapping", methods=["POST"])
@require_jwt()
def etl_ai_field_mapping():
    """
    字段映射推荐 (ETL AI 版本)

    使用 AI 进行智能字段映射，与 /api/v1/mapping/suggest 功能类似
    但针对 ETL 场景优化
    """
    try:
        from services.ai_field_mapping import get_ai_field_mapping_service

        service = get_ai_field_mapping_service()

        data = request.json
        source_fields = data.get("source_fields", [])
        target_fields = data.get("target_fields", [])

        if not source_fields or not target_fields:
            return jsonify({"code": 40001, "message": "source_fields 和 target_fields 不能为空"}), 400

        # 构建源和目标列信息
        source_columns = [{"name": f.get("name"), "type": f.get("type", "varchar")} for f in source_fields]
        target_columns = [{"name": f.get("name"), "type": f.get("type", "varchar")} for f in target_fields]

        # 使用现有服务进行映射
        mappings = []

        # 完全匹配
        for target_col in target_columns:
            target_name = target_col["name"]
            for source_col in source_columns:
                if source_col["name"] == target_name:
                    mappings.append({
                        "source_field": source_col["name"],
                        "target_field": target_name,
                        "confidence": 1.0,
                        "mapping_type": "exact",
                        "transformation": "",
                    })
                    break

        # 模糊匹配 (名称相似)
        for source_col in source_columns:
            source_name = source_col["name"]
            for target_col in target_columns:
                target_name = target_col["name"]
                # 简单相似度计算
                if source_name != target_name and source_name.lower() in target_name.lower() or target_name.lower() in source_name.lower():
                    if not any(m["source_field"] == source_name for m in mappings):
                        mappings.append({
                            "source_field": source_name,
                            "target_field": target_name,
                            "confidence": 0.8,
                            "mapping_type": "fuzzy",
                            "transformation": "",
                        })

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "mappings": mappings,
                "source_count": len(source_fields),
                "target_count": len(target_fields),
                "mapped_count": len(mappings),
                "coverage": len(mappings) / len(target_fields) if target_fields else 0,
            }
        })

    except Exception as e:
        logger.error(f"ETL AI 字段映射失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


# ==================== Assets AI 增强 API ====================

@app.route("/api/v1/assets/ai/value-assess", methods=["POST"])
@require_jwt()
def assets_ai_value_assess():
    """
    资产价值智能评估

    使用 AI 评估数据资产的综合价值
    """
    data = request.json

    try:
        asset_id = data.get("asset_id")
        metrics = data.get("metrics", {})

        if not asset_id:
            return jsonify({"code": 40001, "message": "asset_id 不能为空"}), 400

        db = get_db_session()
        try:
            from models.assets import DataAsset
            from services.asset_value_calculator import get_asset_value_calculator

            calculator = get_asset_value_calculator()

            # 获取资产信息
            asset = db.query(DataAsset).filter(
                DataAsset.asset_id == asset_id
            ).first()

            if not asset:
                return jsonify({"code": 40400, "message": "资产不存在"}), 404

            # 计算各维度评分
            lookback_days = metrics.get("lookback_days", 30)

            # 使用评分 (0-100)
            usage_score, usage_details = calculator.calculate_usage_score(
                db, asset_id, lookback_days
            )

            # 业务评分 (0-100)
            business_score, business_details = calculator.calculate_business_score(
                db, asset_id
            )

            # 质量评分 (0-100)
            quality_score, quality_details = calculator.calculate_quality_score(
                db, asset_id
            )

            # 治理评分 (0-100)
            governance_score = 0.0
            governance_details = {}
            if hasattr(calculator, 'calculate_governance_score'):
                governance_score, governance_details = calculator.calculate_governance_score(
                    db, asset_id
                )

            # 计算综合评分
            weights = calculator.weights
            overall_score = (
                usage_score * weights.get("usage", 0.35) +
                business_score * weights.get("business", 0.30) +
                quality_score * weights.get("quality", 0.20) +
                governance_score * weights.get("governance", 0.15)
            )

            # 确定价值等级
            if overall_score >= 80:
                value_level = "S"
                level_name = "战略级"
            elif overall_score >= 60:
                value_level = "A"
                level_name = "核心级"
            elif overall_score >= 40:
                value_level = "B"
                level_name = "重要级"
            else:
                value_level = "C"
                level_name = "基础级"

            # 生成建议
            recommendations = []
            if usage_score < 40:
                recommendations.append("建议加强资产推广，提升使用率")
            if quality_score < 60:
                recommendations.append("建议提升数据质量，完善质量规则")
            if governance_score < 50:
                recommendations.append("建议完善资产治理信息，补充负责人和标签")
            if business_score < 50:
                recommendations.append("建议明确资产的业务价值和应用场景")

            return jsonify({
                "code": 0,
                "message": "success",
                "data": {
                    "asset_id": asset_id,
                    "asset_name": asset.name,
                    "score_breakdown": {
                        "usage_score": round(usage_score, 2),
                        "business_score": round(business_score, 2),
                        "quality_score": round(quality_score, 2),
                        "governance_score": round(governance_score, 2),
                        "overall_score": round(overall_score, 2),
                    },
                    "value_level": value_level,
                    "level_name": level_name,
                    "details": {
                        "usage": usage_details,
                        "business": business_details,
                        "quality": quality_details,
                        "governance": governance_details,
                    },
                    "recommendations": recommendations,
                }
            })
        finally:
            db.close()

    except Exception as e:
        logger.error(f"资产价值评估失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/assets/ai/auto-tag", methods=["POST"])
@require_jwt()
def assets_ai_auto_tag():
    """
    智能标签生成

    使用 AI 自动为资产生成业务标签
    """
    data = request.json

    try:
        asset_id = data.get("asset_id")
        context = data.get("context", {})

        if not asset_id:
            return jsonify({"code": 40001, "message": "asset_id 不能为空"}), 400

        db = get_db_session()
        try:
            from models.assets import DataAsset
            from services.ai_service import get_ai_service

            ai_service = get_ai_service()

            # 获取资产信息
            asset = db.query(DataAsset).filter(
                DataAsset.asset_id == asset_id
            ).first()

            if not asset:
                return jsonify({"code": 40400, "message": "资产不存在"}), 404

            # 收集资产上下文信息
            asset_context = {
                "name": asset.name,
                "description": asset.description or "",
                "table_name": asset.table_name or "",
                "database_name": asset.database_name or "",
                "asset_type": asset.asset_type or "",
                "existing_tags": asset.tags or [],
            }

            # 添加额外上下文
            asset_context.update(context)

            # 使用 AI 生成标签
            prompt = f"""基于以下数据资产信息，生成 3-5 个业务标签。

资产名称: {asset_context['name']}
描述: {asset_context['description']}
表名: {asset_context['table_name']}
数据库名: {asset_context['database_name']}
资产类型: {asset_context['asset_type']}
已有标签: {', '.join(asset_context['existing_tags'])}

请返回 JSON 格式（只返回 JSON，不要其他内容）：
{{
    "tags": ["标签1", "标签2", "标签3"],
    "confidence": [0.9, 0.8, 0.7],
    "reasons": ["推荐理由1", "推荐理由2", "推荐理由3"]
}}"""

            try:
                messages = [{"role": "user", "content": prompt}]
                response = ai_service._chat_completion(messages, max_tokens=300, temperature=0.3)

                import json
                import re

                # 解析 JSON 响应
                content = response.strip()
                if content.startswith("```"):
                    lines = content.split("\n")
                    content = "\n".join(lines[1:-1])

                result = json.loads(content)

                return jsonify({
                    "code": 0,
                    "message": "success",
                    "data": {
                        "asset_id": asset_id,
                        "suggested_tags": result.get("tags", []),
                        "confidence": result.get("confidence", []),
                        "reasons": result.get("reasons", []),
                        "existing_tags": asset_context['existing_tags'],
                    }
                })

            except Exception as e:
                logger.warning(f"AI 标签生成失败，使用规则匹配: {e}")
                # 规则匹配后备方案
                rule_based_tags = []

                # 基于资产类型
                if asset.asset_type == "table":
                    rule_based_tags.append("数据表")
                elif asset.asset_type == "view":
                    rule_based_tags.append("视图")

                # 基于表名推断
                table_lower = (asset.table_name or "").lower()
                if "fact" in table_lower:
                    rule_based_tags.append("事实表")
                elif "dim" in table_lower or "dimension" in table_lower:
                    rule_based_tags.append("维度表")
                elif "ods" in table_lower:
                    rule_based_tags.append("ODS层")
                elif "dwd" in table_lower:
                    rule_based_tags.append("DWD层")
                elif "dws" in table_lower:
                    rule_based_tags.append("DWS层")
                elif "ads" in table_lower:
                    rule_based_tags.append("ADS层")

                # 基于数据库名
                if asset.database_name:
                    rule_based_tags.append(f"库:{asset.database_name}")

                return jsonify({
                    "code": 0,
                    "message": "success",
                    "data": {
                        "asset_id": asset_id,
                        "suggested_tags": rule_based_tags,
                        "confidence": [0.7] * len(rule_based_tags),
                        "reasons": ["基于规则推断"] * len(rule_based_tags),
                        "existing_tags": asset_context['existing_tags'],
                    }
                })

        finally:
            db.close()

    except Exception as e:
        logger.error(f"智能标签生成失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


# ==================== Quality AI 增强 API ====================

@app.route("/api/v1/quality/ai/analyze-table", methods=["POST"])
@require_jwt()
def quality_ai_analyze_table():
    """
    AI 质量分析 - 分析表的数据质量问题

    与 /api/v1/quality/analyze-table 功能类似，但使用 /api/v1/quality/ai/ 路径
    """
    db = get_db_session()
    data = request.json or {}

    try:
        from services.ai_cleaning_advisor import get_ai_cleaning_advisor

        advisor = get_ai_cleaning_advisor()

        table_name = data.get("table_name")
        if not table_name:
            return jsonify({"code": 40001, "message": "table_name 不能为空"}), 400

        database_name = data.get("database_name")

        recommendations = advisor.analyze_table_quality_issues(
            db=db,
            table_name=table_name,
            database_name=database_name
        )

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "table_name": table_name,
                "database_name": database_name,
                "issues_found": len(recommendations),
                "recommendations": [r.to_dict() for r in recommendations],
            }
        })
    except ImportError as e:
        return jsonify({"code": 50001, "message": f"AI 清洗服务不可用: {e}"}), 500
    except Exception as e:
        logger.error(f"AI 表质量分析失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/quality/ai/rule-templates", methods=["POST"])
@require_jwt()
def quality_ai_rule_templates():
    """
    AI 规则模板生成

    基于表结构生成质量规则模板
    """
    try:
        from services.ai_cleaning_advisor import get_ai_cleaning_advisor
        from services.ai_service import get_ai_service

        advisor = get_ai_cleaning_advisor()
        ai_service = get_ai_service()

        data = request.json
        table_name = data.get("table_name", "")
        columns = data.get("columns", [])

        if not columns:
            return jsonify({"code": 40001, "message": "columns 不能为空"}), 400

        # 使用 AI 生成规则模板
        cols_info = []
        for col in columns[:20]:
            cols_info.append(f"- {col.get('name', '')} ({col.get('type', 'varchar')}): {col.get('description', '')}")

        cols_str = "\n".join(cols_info)

        prompt = f"""你是一个数据质量专家。请为以下表结构推荐质量检查规则。

表名: {table_name}
列信息:
{cols_str}

请以 JSON 数组格式返回推荐规则（只返回 JSON 数组，不要其他内容）：
[
    {{
        "rule_name": "规则名称",
        "rule_type": "completeness/validity/consistency/uniqueness",
        "target_column": "列名",
        "expression": "规则表达式",
        "description": "规则描述",
        "severity": "error/warning/info",
        "priority": 1-10
    }}
]"""

        try:
            messages = [{"role": "user", "content": prompt}]
            response = ai_service._chat_completion(messages, max_tokens=1024, temperature=0.3)

            import json
            import re

            content = response.strip()
            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:-1])

            rules = json.loads(content)

            return jsonify({
                "code": 0,
                "message": "success",
                "data": {
                    "table_name": table_name,
                    "rules": rules,
                    "total": len(rules),
                }
            })

        except Exception as e:
            logger.warning(f"AI 规则生成失败，使用模板匹配: {e}")
            # 后备方案：使用预定义模板
            templates = []
            for col in columns:
                col_name = col.get("name")
                col_type = col.get("type", "varchar").lower()

                # 基于列类型推荐规则
                if "int" in col_type or "number" in col_type:
                    templates.append({
                        "rule_name": f"{col_name}_非空检查",
                        "rule_type": "completeness",
                        "target_column": col_name,
                        "expression": f"{col_name} IS NOT NULL",
                        "description": f"{col_name} 不能为空",
                        "severity": "error",
                        "priority": 8,
                    })
                    templates.append({
                        "rule_name": f"{col_name}_范围检查",
                        "rule_type": "validity",
                        "target_column": col_name,
                        "expression": f"{col_name} >= 0",
                        "description": f"{col_name} 必须非负",
                        "severity": "warning",
                        "priority": 5,
                    })
                elif "varchar" in col_type or "char" in col_type:
                    templates.append({
                        "rule_name": f"{col_name}_长度检查",
                        "rule_type": "validity",
                        "target_column": col_name,
                        "expression": f"LENGTH({col_name}) > 0",
                        "description": f"{col_name} 不能为空字符串",
                        "severity": "warning",
                        "priority": 6,
                    })
                elif "date" in col_type or "time" in col_type:
                    templates.append({
                        "rule_name": f"{col_name}_日期检查",
                        "rule_type": "validity",
                        "target_column": col_name,
                        "expression": f"{col_name} <= CURRENT_DATE",
                        "description": f"{col_name} 不能晚于当前日期",
                        "severity": "warning",
                        "priority": 4,
                    })

            return jsonify({
                "code": 0,
                "message": "success",
                "data": {
                    "table_name": table_name,
                    "rules": templates,
                    "total": len(templates),
                    "fallback": True,
                }
            })

    except Exception as e:
        logger.error(f"AI 规则模板生成失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/quality/ai/alert-rules", methods=["POST"])
@require_jwt()
def quality_ai_alert_rules():
    """
    AI 智能预警规则生成

    基于历史数据生成异常检测预警规则
    """
    data = request.json

    try:
        from services.ai_service import get_ai_service

        ai_service = get_ai_service()

        metric_name = data.get("metric_name")
        historical_data = data.get("historical_data", [])

        if not metric_name:
            return jsonify({"code": 40001, "message": "metric_name 不能为空"}), 400

        # 计算统计信息
        import statistics
        try:
            values = [float(d.get("value", 0)) for d in historical_data if d.get("value") is not None]
        except (ValueError, TypeError):
            values = []

        alert_rules = []

        if len(values) >= 10:
            mean_val = statistics.mean(values)
            stdev_val = statistics.stdev(values) if len(values) > 1 else 0

            # 生成 3-sigma 规则
            alert_rules.append({
                "rule_name": f"{metric_name}_异常检测",
                "metric_name": metric_name,
                "rule_type": "static_threshold",
                "condition": "outside_range",
                "threshold_upper": round(mean_val + 3 * stdev_val, 2),
                "threshold_lower": round(mean_val - 3 * stdev_val, 2),
                "description": f"当 {metric_name} 超出 {mean_val:.2f} ± 3σ 时告警",
                "severity": "warning",
            })

            # 生成百分比变化规则
            if len(values) >= 2:
                pct_changes = []
                for i in range(1, len(values)):
                    if values[i-1] != 0:
                        pct_changes.append(abs((values[i] - values[i-1]) / values[i-1] * 100))

                if pct_changes:
                    avg_change = statistics.mean(pct_changes)
                    alert_rules.append({
                        "rule_name": f"{metric_name}_突增检测",
                        "metric_name": metric_name,
                        "rule_type": "percent_change",
                        "condition": "increase",
                        "threshold_percent": round(avg_change * 2, 2),
                        "description": f"当 {metric_name} 突增超过 {avg_change*2:.1f}% 时告警",
                        "severity": "warning",
                    })

        # 使用 AI 生成更智能的规则
        if values and ai_service.config.enabled:
            try:
                prompt = f"""你是一个数据质量专家。请基于以下指标历史数据生成预警规则。

指标名称: {metric_name}
数据点: {values[:50]}

请返回 JSON 格式（只返回 JSON，不要其他内容）：
{{
    "rules": [
        {{
            "rule_name": "规则名称",
            "condition_type": "threshold/trend/anomaly",
            "condition": "条件描述",
            "threshold_value": 数值,
            "severity": "error/warning/info"
        }}
    ]
}}"""

                messages = [{"role": "user", "content": prompt}]
                response = ai_service._chat_completion(messages, max_tokens=512, temperature=0.3)

                import json
                import re

                content = response.strip()
                if content.startswith("```"):
                    lines = content.split("\n")
                    content = "\n".join(lines[1:-1])

                result = json.loads(content)
                alert_rules.extend(result.get("rules", []))

            except Exception as e:
                logger.debug(f"AI 预警规则生成失败: {e}")

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "metric_name": metric_name,
                "alert_rules": alert_rules,
                "total": len(alert_rules),
                "statistics": {
                    "count": len(values),
                    "mean": round(statistics.mean(values), 2) if values else 0,
                    "min": round(min(values), 2) if values else 0,
                    "max": round(max(values), 2) if values else 0,
                } if values else None,
            }
        })

    except Exception as e:
        logger.error(f"AI 预警规则生成失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


# ==================== Sensitivity AI API ====================

@app.route("/api/v1/sensitivity/ai/scan", methods=["POST"])
@require_jwt()
def sensitivity_ai_scan():
    """
    敏感数据扫描 - 扫描表/列的敏感数据

    使用 AI 识别敏感数据类型和级别
    """
    data = request.json

    try:
        from services.sensitivity_auto_scan_service import get_sensitivity_auto_scan_service
        from services.ai_service import get_ai_service

        ai_service = get_ai_service()
        scan_service = get_sensitivity_auto_scan_service(ai_service=ai_service)

        dataset_id = data.get("dataset_id")
        table_name = data.get("table_name")
        columns = data.get("columns", [])
        sample_size = data.get("sample_size", 200)

        if not table_name and not dataset_id:
            return jsonify({"code": 40001, "message": "table_name 或 dataset_id 必须提供一个"}), 400

        db = get_db_session()
        try:
            from models.metadata import MetadataTable, MetadataColumn
            from sqlalchemy import text

            # 获取表列信息
            if table_name:
                metadata_columns = db.query(MetadataColumn).filter(
                    MetadataColumn.table_name == table_name
                ).all()

                if metadata_columns:
                    columns = [{
                        "name": col.column_name,
                        "type": col.column_type or "varchar",
                    } for col in metadata_columns]

            # 扫描每列
            scan_results = []

            for col_info in columns:
                col_name = col_info.get("name")
                col_type = col_info.get("type", "varchar")

                # 获取样本数据
                sample_values = []
                try:
                    # 使用快速扫描
                    result = scan_service.quick_scan_column(
                        column_name=col_name,
                        sample_values=sample_values,
                        column_type=col_type,
                    )
                    scan_results.append(result)
                except Exception as e:
                    logger.debug(f"列 {col_name} 扫描失败: {e}")
                    scan_results.append({
                        "column_name": col_name,
                        "is_sensitive": False,
                        "sensitivity_type": "none",
                        "confidence": 0,
                        "error": str(e),
                    })

            # 统计
            sensitive_count = sum(1 for r in scan_results if r.get("is_sensitive"))
            breakdown = {}
            for r in scan_results:
                stype = r.get("sensitivity_type", "none")
                if stype != "none":
                    breakdown[stype] = breakdown.get(stype, 0) + 1

            return jsonify({
                "code": 0,
                "message": "success",
                "data": {
                    "table_name": table_name,
                    "dataset_id": dataset_id,
                    "columns_scanned": len(scan_results),
                    "sensitive_found": sensitive_count,
                    "breakdown": breakdown,
                    "results": scan_results,
                }
            })
        finally:
            db.close()

    except Exception as e:
        logger.error(f"敏感数据扫描失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/sensitivity/ai/scan-batch", methods=["POST"])
@require_jwt()
def sensitivity_ai_scan_batch():
    """
    批量扫描多个表的敏感数据

    创建批量扫描任务，返回任务 ID
    """
    data = request.json

    try:
        from services.sensitivity_auto_scan_service import (
            get_sensitivity_auto_scan_service,
            AutoScanPolicy,
            AutoScanMode
        )
        from services.ai_service import get_ai_service

        ai_service = get_ai_service()
        scan_service = get_sensitivity_auto_scan_service(ai_service=ai_service)

        tables = data.get("tables", [])
        databases = data.get("databases", [])
        options = data.get("options", {})

        if not tables and not databases:
            return jsonify({"code": 40001, "message": "tables 或 databases 不能为空"}), 400

        # 创建扫描策略
        policy = AutoScanPolicy(
            name=f"批量扫描-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            mode=AutoScanMode.TARGETED if tables else AutoScanMode.FULL,
            databases=databases,
            sample_size=options.get("sample_size", 200),
            confidence_threshold=options.get("confidence_threshold", 60),
            auto_update_metadata=options.get("auto_update_metadata", True),
            auto_generate_masking_rules=options.get("auto_generate_masking_rules", False),
        )

        # 启动扫描
        import uuid
        task_id = f"scan-{uuid.uuid4().hex[:12]}"

        # 在实际应用中，这里应该使用异步任务
        # 对于演示，我们直接执行同步扫描
        db = get_db_session()
        try:
            progress = scan_service.start_auto_scan(policy=policy, db_session=db)

            return jsonify({
                "code": 0,
                "message": "扫描任务已创建",
                "data": {
                    "task_id": task_id,
                    "status": "running",
                    "tables_count": len(tables) if tables else 0,
                    "databases_count": len(databases),
                    "progress": scan_service.get_progress(),
                }
            })
        finally:
            db.close()

    except Exception as e:
        logger.error(f"批量扫描创建失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/sensitivity/ai/scan-result/<task_id>", methods=["GET"])
@require_jwt()
def sensitivity_ai_scan_result(task_id: str):
    """
    获取扫描任务结果

    返回批量扫描任务的详细结果
    """
    try:
        from services.sensitivity_auto_scan_service import get_sensitivity_auto_scan_service

        scan_service = get_sensitivity_auto_scan_service()

        # 获取扫描进度/结果
        progress = scan_service.get_progress()

        if not progress or progress.get("status") == "idle":
            return jsonify({
                "code": 40400,
                "message": "扫描任务不存在或未开始"
            }), 404

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "task_id": task_id,
                **progress
            }
        })

    except Exception as e:
        logger.error(f"获取扫描结果失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


# ==================== 智能预警推送 API ====================

@app.route("/api/v1/alerts/detect-anomalies", methods=["POST"])
@require_jwt()
def detect_anomalies():
    """
    执行异常检测
    """
    try:
        from services.smart_alert_service import get_smart_alert_service

        service = get_smart_alert_service()

        data = request.json
        detection_types = data.get("detection_types")
        time_window_hours = data.get("time_window_hours", 24)
        tenant_id = request.args.get("tenant_id", "default")

        db = get_db_session()
        try:
            result = service.detect_anomalies(
                db=db,
                tenant_id=tenant_id,
                detection_types=detection_types,
                time_window_hours=time_window_hours,
            )

            return jsonify({
                "code": 0,
                "message": "success",
                "data": result
            })
        finally:
            db.close()

    except Exception as e:
        logger.error(f"异常检测失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/alerts/rules", methods=["GET"])
@require_jwt()
def list_alert_rules():
    """
    列出预警规则
    """
    try:
        from services.smart_alert_service import get_smart_alert_service

        service = get_smart_alert_service()

        tenant_id = request.args.get("tenant_id", "default")
        rule_type = request.args.get("rule_type")
        enabled_only = request.args.get("enabled_only", "false").lower() == "true"

        result = service.list_alert_rules(
            db=get_db_session(),
            tenant_id=tenant_id,
            rule_type=rule_type,
            enabled_only=enabled_only,
        )

        return jsonify({
            "code": 0,
            "message": "success",
            "data": result
        })

    except Exception as e:
        logger.error(f"获取预警规则失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/alerts/rules", methods=["POST"])
@require_jwt()
def create_alert_rule():
    """
    创建预警规则
    """
    try:
        from services.smart_alert_service import get_smart_alert_service

        service = get_smart_alert_service()

        data = request.json
        tenant_id = request.args.get("tenant_id", "default")
        user_id = g.user.get("user_id", "system")

        result = service.create_alert_rule(
            db=get_db_session(),
            rule=data,
            tenant_id=tenant_id,
            user_id=user_id,
        )

        return jsonify({
            "code": 0,
            "message": "success",
            "data": result
        })

    except Exception as e:
        logger.error(f"创建预警规则失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/alerts/rules/<rule_id>", methods=["PUT"])
@require_jwt()
def update_alert_rule(rule_id: str):
    """
    更新预警规则
    """
    try:
        from services.smart_alert_service import get_smart_alert_service

        service = get_smart_alert_service()

        updates = request.json

        result = service.update_alert_rule(
            db=get_db_session(),
            rule_id=rule_id,
            updates=updates,
        )

        return jsonify({
            "code": 0,
            "message": "success",
            "data": result
        })

    except Exception as e:
        logger.error(f"更新预警规则失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/alerts/rules/<rule_id>", methods=["DELETE"])
@require_jwt()
def delete_alert_rule(rule_id: str):
    """
    删除预警规则
    """
    try:
        from services.smart_alert_service import get_smart_alert_service

        service = get_smart_alert_service()

        success = service.delete_alert_rule(
            db=get_db_session(),
            rule_id=rule_id,
        )

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {"deleted": success}
        })

    except Exception as e:
        logger.error(f"删除预警规则失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/alerts/channels", methods=["GET"])
@require_jwt()
def get_alert_channels():
    """
    获取预警通道列表
    """
    try:
        from services.smart_alert_service import get_smart_alert_service

        service = get_smart_alert_service()

        include_disabled = request.args.get("include_disabled", "false").lower() == "true"

        channels = service.get_channels(include_disabled=include_disabled)

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "channels": channels,
                "total": len(channels),
            }
        })

    except Exception as e:
        logger.error(f"获取预警通道失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/alerts/channels", methods=["POST"])
@require_jwt()
def add_alert_channel():
    """
    添加预警通道
    """
    try:
        from services.smart_alert_service import get_smart_alert_service

        service = get_smart_alert_service()

        data = request.json
        channel_type = data.get("channel_type")
        name = data.get("name")
        config = data.get("config", {})

        result = service.add_channel(channel_type, name, config)

        return jsonify({
            "code": 0,
            "message": "success",
            "data": result
        })

    except Exception as e:
        logger.error(f"添加预警通道失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/alerts/channels/<channel_type>", methods=["PUT"])
@require_jwt()
def update_alert_channel(channel_type: str):
    """
    更新预警通道配置
    """
    try:
        from services.smart_alert_service import get_smart_alert_service

        service = get_smart_alert_service()

        updates = request.json

        result = service.update_channel(channel_type, updates)

        return jsonify({
            "code": 0,
            "message": "success",
            "data": result
        })

    except Exception as e:
        logger.error(f"更新预警通道失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/alerts/channels/<channel_type>", methods=["DELETE"])
@require_jwt()
def remove_alert_channel(channel_type: str):
    """
    删除预警通道
    """
    try:
        from services.smart_alert_service import get_smart_alert_service

        service = get_smart_alert_service()

        success = service.remove_channel(channel_type)

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {"removed": success}
        })

    except Exception as e:
        logger.error(f"删除预警通道失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/alerts/channels/<channel_type>/test", methods=["POST"])
@require_jwt()
def test_alert_channel(channel_type: str):
    """
    测试预警通道
    """
    try:
        from services.smart_alert_service import get_smart_alert_service

        service = get_smart_alert_service()

        data = request.json or {}
        test_message = data.get("message")

        result = service.test_channel(channel_type, test_message)

        return jsonify({
            "code": 0,
            "message": "success",
            "data": result
        })

    except Exception as e:
        logger.error(f"测试预警通道失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/alerts/send", methods=["POST"])
@require_jwt()
def send_alert():
    """
    发送预警通知
    """
    try:
        from services.smart_alert_service import get_smart_alert_service

        service = get_smart_alert_service()

        data = request.json
        alert = data.get("alert", {})
        channels = data.get("channels", ["email"])
        recipients = data.get("recipients")

        result = service.send_alert(
            db=get_db_session(),
            alert=alert,
            channels=channels,
            recipients=recipients,
        )

        return jsonify({
            "code": 0,
            "message": "success",
            "data": result
        })

    except Exception as e:
        logger.error(f"发送预警失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/alerts/history", methods=["GET"])
@require_jwt()
def get_alert_history():
    """
    获取预警历史
    """
    try:
        from services.smart_alert_service import get_smart_alert_service

        service = get_smart_alert_service()

        tenant_id = request.args.get("tenant_id", "default")
        limit = request.args.get("limit", 100, type=int)
        offset = request.args.get("offset", 0, type=int)
        severity = request.args.get("severity")

        result = service.get_alert_history(
            db=get_db_session(),
            tenant_id=tenant_id,
            limit=limit,
            offset=offset,
            severity=severity,
        )

        return jsonify({
            "code": 0,
            "message": "success",
            "data": result
        })

    except Exception as e:
        logger.error(f"获取预警历史失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/alerts/statistics", methods=["GET"])
@require_jwt()
def get_alert_statistics():
    """
    获取预警统计数据
    """
    try:
        from services.smart_alert_service import get_smart_alert_service

        service = get_smart_alert_service()

        tenant_id = request.args.get("tenant_id", "default")
        days = request.args.get("days", 30, type=int)

        result = service.get_alert_statistics(
            db=get_db_session(),
            tenant_id=tenant_id,
            days=days,
        )

        return jsonify({
            "code": 0,
            "message": "success",
            "data": result
        })

    except Exception as e:
        logger.error(f"获取预警统计失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/alerts/subscriptions", methods=["GET"])
@require_jwt()
def get_alert_subscriptions():
    """
    获取用户预警订阅列表
    """
    try:
        from services.smart_alert_service import get_smart_alert_service

        service = get_smart_alert_service()

        user_id = g.user.get("user_id", "system")

        result = service.get_user_subscriptions(
            db=get_db_session(),
            user_id=user_id,
        )

        return jsonify({
            "code": 0,
            "message": "success",
            "data": result
        })

    except Exception as e:
        logger.error(f"获取预警订阅失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/alerts/subscriptions", methods=["POST"])
@require_jwt()
def create_alert_subscription():
    """
    创建预警订阅
    """
    try:
        from services.smart_alert_service import get_smart_alert_service

        service = get_smart_alert_service()

        data = request.json
        user_id = g.user.get("user_id", "system")

        result = service.create_subscription(
            db=get_db_session(),
            user_id=user_id,
            subscription=data,
        )

        return jsonify({
            "code": 0,
            "message": "success",
            "data": result
        })

    except Exception as e:
        logger.error(f"创建预警订阅失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/alerts/subscriptions/<subscription_id>", methods=["PUT"])
@require_jwt()
def update_alert_subscription(subscription_id: str):
    """
    更新预警订阅
    """
    try:
        from services.smart_alert_service import get_smart_alert_service

        service = get_smart_alert_service()

        updates = request.json

        result = service.update_subscription(
            db=get_db_session(),
            subscription_id=subscription_id,
            updates=updates,
        )

        return jsonify({
            "code": 0,
            "message": "success",
            "data": result
        })

    except Exception as e:
        logger.error(f"更新预警订阅失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/alerts/subscriptions/<subscription_id>", methods=["DELETE"])
@require_jwt()
def delete_alert_subscription(subscription_id: str):
    """
    删除预警订阅
    """
    try:
        from services.smart_alert_service import get_smart_alert_service

        service = get_smart_alert_service()

        success = service.delete_subscription(
            db=get_db_session(),
            subscription_id=subscription_id,
        )

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {"deleted": success}
        })

    except Exception as e:
        logger.error(f"删除预警订阅失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/alerts/available-types", methods=["GET"])
@require_jwt()
def get_available_alert_types():
    """
    获取可订阅的预警类型
    """
    try:
        from services.smart_alert_service import get_smart_alert_service

        service = get_smart_alert_service()

        types = service.get_available_alert_types()

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "types": types,
                "total": len(types),
            }
        })

    except Exception as e:
        logger.error(f"获取预警类型失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


# ==================== 增强型统一 SSO API ====================

@app.route("/api/v1/sso/providers", methods=["GET"])
def list_sso_providers():
    """
    列出所有 SSO 提供商
    """
    try:
        from services.enhanced_sso_service import get_enhanced_sso_service

        service = get_enhanced_sso_service()

        include_disabled = request.args.get("include_disabled", "false").lower() == "true"

        providers = service.list_providers(include_disabled=include_disabled)

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "providers": providers,
                "total": len(providers),
            }
        })

    except Exception as e:
        logger.error(f"获取 SSO 提供商失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/sso/providers/<provider_id>", methods=["GET"])
def get_sso_provider(provider_id: str):
    """
    获取指定 SSO 提供商配置
    """
    try:
        from services.enhanced_sso_service import get_enhanced_sso_service

        service = get_enhanced_sso_service()

        provider = service.get_provider(provider_id)

        if not provider:
            return jsonify({"code": 40004, "message": "提供商不存在"}), 404

        return jsonify({
            "code": 0,
            "message": "success",
            "data": provider
        })

    except Exception as e:
        logger.error(f"获取 SSO 提供商失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/sso/providers", methods=["POST"])
@require_jwt()
def add_sso_provider():
    """
    添加新的 SSO 提供商
    """
    try:
        from services.enhanced_sso_service import get_enhanced_sso_service

        service = get_enhanced_sso_service()

        data = request.json

        provider = service.add_provider(data)

        return jsonify({
            "code": 0,
            "message": "success",
            "data": provider
        })

    except Exception as e:
        logger.error(f"添加 SSO 提供商失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/sso/providers/<provider_id>", methods=["PUT"])
@require_jwt()
def update_sso_provider(provider_id: str):
    """
    更新 SSO 提供商配置
    """
    try:
        from services.enhanced_sso_service import get_enhanced_sso_service

        service = get_enhanced_sso_service()

        updates = request.json

        provider = service.update_provider(provider_id, updates)

        if not provider:
            return jsonify({"code": 40004, "message": "提供商不存在"}), 404

        return jsonify({
            "code": 0,
            "message": "success",
            "data": provider
        })

    except Exception as e:
        logger.error(f"更新 SSO 提供商失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/sso/providers/<provider_id>", methods=["DELETE"])
@require_jwt()
def delete_sso_provider(provider_id: str):
    """
    删除 SSO 提供商
    """
    try:
        from services.enhanced_sso_service import get_enhanced_sso_service

        service = get_enhanced_sso_service()

        success = service.delete_provider(provider_id)

        if not success:
            return jsonify({"code": 40004, "message": "提供商不存在"}), 404

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {"deleted": True}
        })

    except Exception as e:
        logger.error(f"删除 SSO 提供商失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/sso/sms/send", methods=["POST"])
def send_sms_verification():
    """
    发送短信验证码
    """
    try:
        from services.enhanced_sso_service import get_enhanced_sso_service

        service = get_enhanced_sso_service()

        data = request.json
        phone = data.get("phone")
        purpose = data.get("purpose", "login")

        if not phone:
            return jsonify({"code": 40001, "message": "phone 不能为空"}), 400

        result = service.send_sms_code(phone, purpose)

        if result["success"]:
            return jsonify({
                "code": 0,
                "message": "success",
                "data": result
            })
        else:
            return jsonify({"code": 40002, "message": result["message"]}), 400

    except Exception as e:
        logger.error(f"发送短信验证码失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/sso/sms/verify", methods=["POST"])
def verify_sms_code():
    """
    验证短信验证码并登录
    """
    try:
        from services.enhanced_sso_service import get_enhanced_sso_service

        service = get_enhanced_sso_service()

        data = request.json
        phone = data.get("phone")
        code = data.get("code")
        purpose = data.get("purpose", "login")

        if not phone or not code:
            return jsonify({"code": 40001, "message": "phone 和 code 不能为空"}), 400

        result = service.verify_sms_code(phone, code, purpose)

        if result["success"]:
            # 验证成功，创建会话
            session = service.create_session(
                user_id=f"sms_{phone}",
                provider="sms",
                login_method="sms",
            )
            return jsonify({
                "code": 0,
                "message": "登录成功",
                "data": session
            })
        else:
            return jsonify({"code": 40002, "message": result["message"]}), 400

    except Exception as e:
        logger.error(f"验证短信验证码失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/sso/qrcode/create", methods=["POST"])
def create_qrcode_session():
    """
    创建扫码登录会话
    """
    try:
        from services.enhanced_sso_service import get_enhanced_sso_service

        service = get_enhanced_sso_service()

        result = service.create_qrcode_session()

        return jsonify({
            "code": 0,
            "message": "success",
            "data": result
        })

    except Exception as e:
        logger.error(f"创建二维码会话失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/sso/qrcode/status/<session_id>", methods=["GET"])
def get_qrcode_status(session_id: str):
    """
    获取二维码状态
    """
    try:
        from services.enhanced_sso_service import get_enhanced_sso_service

        service = get_enhanced_sso_service()

        result = service.get_qrcode_status(session_id)

        return jsonify({
            "code": 0,
            "message": "success",
            "data": result
        })

    except Exception as e:
        logger.error(f"获取二维码状态失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/sso/qrcode/scan", methods=["POST"])
@require_jwt()
def scan_qrcode():
    """
    扫描二维码（移动端调用）
    """
    try:
        from services.enhanced_sso_service import get_enhanced_sso_service

        service = get_enhanced_sso_service()

        data = request.json
        session_id = data.get("session_id")
        user_id = g.user.get("user_id", "")

        if not session_id:
            return jsonify({"code": 40001, "message": "session_id 不能为空"}), 400

        result = service.scan_qrcode(session_id, user_id)

        if result["success"]:
            return jsonify({
                "code": 0,
                "message": "success",
                "data": result
            })
        else:
            return jsonify({"code": 40002, "message": result["message"]}), 400

    except Exception as e:
        logger.error(f"扫码失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/sso/qrcode/confirm", methods=["POST"])
@require_jwt()
def confirm_qrcode_login():
    """
    确认扫码登录（移动端调用）
    """
    try:
        from services.enhanced_sso_service import get_enhanced_sso_service

        service = get_enhanced_sso_service()

        data = request.json
        session_id = data.get("session_id")

        if not session_id:
            return jsonify({"code": 40001, "message": "session_id 不能为空"}), 400

        result = service.confirm_qrcode_login(session_id)

        if result["success"]:
            return jsonify({
                "code": 0,
                "message": "success",
                "data": result
            })
        else:
            return jsonify({"code": 40002, "message": result["message"]}), 400

    except Exception as e:
        logger.error(f"确认扫码登录失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/sso/qrcode/cancel/<session_id>", methods=["POST"])
def cancel_qrcode_login(session_id: str):
    """
    取消扫码登录
    """
    try:
        from services.enhanced_sso_service import get_enhanced_sso_service

        service = get_enhanced_sso_service()

        service.cancel_qrcode_login(session_id)

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {"cancelled": True}
        })

    except Exception as e:
        logger.error(f"取消扫码登录失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/sso/oauth/url", methods=["GET"])
def get_oauth_url():
    """
    获取 OAuth 授权 URL
    """
    try:
        from services.enhanced_sso_service import get_enhanced_sso_service

        service = get_enhanced_sso_service()

        provider_id = request.args.get("provider_id")
        redirect_uri = request.args.get("redirect_uri", "")
        state = request.args.get("state", "")

        if not provider_id:
            return jsonify({"code": 40001, "message": "provider_id 不能为空"}), 400

        result = service.get_oauth_url(provider_id, redirect_uri, state)

        if result["success"]:
            return jsonify({
                "code": 0,
                "message": "success",
                "data": result
            })
        else:
            return jsonify({"code": 40002, "message": result["message"]}), 400

    except Exception as e:
        logger.error(f"获取授权 URL 失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/sso/oauth/callback", methods=["POST"])
def handle_oauth_callback():
    """
    处理 OAuth 回调
    """
    try:
        from services.enhanced_sso_service import get_enhanced_sso_service

        service = get_enhanced_sso_service()

        data = request.json
        provider_id = data.get("provider_id")
        code = data.get("code")
        state = data.get("state", "")

        if not provider_id or not code:
            return jsonify({"code": 40001, "message": "provider_id 和 code 不能为空"}), 400

        result = service.handle_oauth_callback(provider_id, code, state)

        if result["success"]:
            return jsonify({
                "code": 0,
                "message": "success",
                "data": result
            })
        else:
            return jsonify({"code": 40002, "message": result.get("message", "认证失败")}), 400

    except Exception as e:
        logger.error(f"处理 OAuth 回调失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/sso/sessions/<session_id>", methods=["GET"])
def get_session_info(session_id: str):
    """
    获取会话信息
    """
    try:
        from services.enhanced_sso_service import get_enhanced_sso_service

        service = get_enhanced_sso_service()

        session = service.get_session(session_id)

        if not session:
            return jsonify({"code": 40004, "message": "会话不存在或已过期"}), 404

        return jsonify({
            "code": 0,
            "message": "success",
            "data": session
        })

    except Exception as e:
        logger.error(f"获取会话信息失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/sso/sessions/user/<user_id>", methods=["GET"])
@require_jwt()
def list_user_sessions(user_id: str):
    """
    列出用户的所有活跃会话
    """
    try:
        from services.enhanced_sso_service import get_enhanced_sso_service

        service = get_enhanced_sso_service()

        sessions = service.list_user_sessions(user_id)

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "sessions": sessions,
                "total": len(sessions),
            }
        })

    except Exception as e:
        logger.error(f"获取用户会话列表失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/sso/logout", methods=["POST"])
def sso_logout():
    """
    SSO 登出

    支持:
    - 单设备登出
    - 全局登出（所有设备）
    """
    try:
        from services.enhanced_sso_service import get_enhanced_sso_service

        service = get_enhanced_sso_service()

        data = request.json or {}
        session_id = data.get("session_id") or g.user.get("session_id", "")
        global_logout = data.get("global_logout", False)

        if not session_id:
            return jsonify({"code": 40001, "message": "session_id 不能为空"}), 400

        result = service.logout(session_id, global_logout)

        return jsonify({
            "code": 0,
            "message": "success",
            "data": result
        })

    except Exception as e:
        logger.error(f"登出失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


# ==================== 数据服务接口管理 API ====================

@app.route("/api/v1/data-services", methods=["GET"])
@require_jwt()
def list_data_services():
    """
    列出数据服务
    """
    try:
        from services.data_service_manager import get_data_service_manager

        manager = get_data_service_manager()

        status = request.args.get("status")
        service_type = request.args.get("service_type")
        source_type = request.args.get("source_type")
        tags = request.args.getlist("tags")
        created_by = request.args.get("created_by")
        limit = request.args.get("limit", 100, type=int)
        offset = request.args.get("offset", 0, type=int)

        result = manager.list_services(
            status=status,
            service_type=service_type,
            source_type=source_type,
            tags=tags if tags else None,
            created_by=created_by,
            limit=limit,
            offset=offset,
        )

        return jsonify({
            "code": 0,
            "message": "success",
            "data": result
        })

    except Exception as e:
        logger.error(f"获取数据服务列表失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/data-services", methods=["POST"])
@require_jwt()
def create_data_service():
    """
    创建数据服务
    """
    try:
        from services.data_service_manager import get_data_service_manager

        manager = get_data_service_manager()

        data = request.json
        user_id = g.user.get("user_id", "system")

        result = manager.create_service(
            name=data.get("name"),
            description=data.get("description", ""),
            service_type=data.get("service_type", "rest"),
            source_type=data.get("source_type", "table"),
            source_config=data.get("source_config", {}),
            endpoint=data.get("endpoint", ""),
            method=data.get("method", "GET"),
            created_by=user_id,
            tags=data.get("tags"),
            rate_limit=data.get("rate_limit"),
        )

        return jsonify({
            "code": 0,
            "message": "success",
            "data": result
        })

    except Exception as e:
        logger.error(f"创建数据服务失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/data-services/<service_id>", methods=["GET"])
@require_jwt()
def get_data_service(service_id: str):
    """
    获取数据服务详情
    """
    try:
        from services.data_service_manager import get_data_service_manager

        manager = get_data_service_manager()

        result = manager.get_service(service_id)

        if not result:
            return jsonify({"code": 40004, "message": "服务不存在"}), 404

        return jsonify({
            "code": 0,
            "message": "success",
            "data": result
        })

    except Exception as e:
        logger.error(f"获取数据服务失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/data-services/<service_id>", methods=["PUT"])
@require_jwt()
def update_data_service(service_id: str):
    """
    更新数据服务
    """
    try:
        from services.data_service_manager import get_data_service_manager

        manager = get_data_service_manager()

        updates = request.json

        result = manager.update_service(service_id, updates)

        if not result:
            return jsonify({"code": 40004, "message": "服务不存在"}), 404

        return jsonify({
            "code": 0,
            "message": "success",
            "data": result
        })

    except Exception as e:
        logger.error(f"更新数据服务失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/data-services/<service_id>", methods=["DELETE"])
@require_jwt()
def delete_data_service(service_id: str):
    """
    删除数据服务
    """
    try:
        from services.data_service_manager import get_data_service_manager

        manager = get_data_service_manager()

        success = manager.delete_service(service_id)

        if not success:
            return jsonify({"code": 40004, "message": "服务不存在"}), 404

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {"deleted": True}
        })

    except Exception as e:
        logger.error(f"删除数据服务失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/data-services/<service_id>/publish", methods=["POST"])
@require_jwt()
def publish_data_service(service_id: str):
    """
    发布数据服务
    """
    try:
        from services.data_service_manager import get_data_service_manager

        manager = get_data_service_manager()

        result = manager.publish_service(service_id)

        if not result:
            return jsonify({"code": 40004, "message": "服务不存在"}), 404

        return jsonify({
            "code": 0,
            "message": "success",
            "data": result
        })

    except Exception as e:
        logger.error(f"发布数据服务失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/data-services/<service_id>/test", methods=["POST"])
@require_jwt()
def test_data_service(service_id: str):
    """
    测试数据服务
    """
    try:
        from services.data_service_manager import get_data_service_manager

        manager = get_data_service_manager()

        params = request.json or {}

        result = manager.test_service(service_id, params)

        return jsonify({
            "code": 0,
            "message": "success",
            "data": result
        })

    except Exception as e:
        logger.error(f"测试数据服务失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


# ==================== API Key 管理 ====================

@app.route("/api/v1/data-services/api-keys", methods=["GET"])
@require_jwt()
def list_api_keys():
    """
    列出 API Keys
    """
    try:
        from services.data_service_manager import get_data_service_manager

        manager = get_data_service_manager()

        user_id = g.user.get("user_id", "")
        include_expired = request.args.get("include_expired", "false").lower() == "true"
        include_inactive = request.args.get("include_inactive", "false").lower() == "true"

        result = manager.list_api_keys(
            user_id=user_id,
            include_expired=include_expired,
            include_inactive=include_inactive,
        )

        return jsonify({
            "code": 0,
            "message": "success",
            "data": result
        })

    except Exception as e:
        logger.error(f"获取 API Keys 列表失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/data-services/api-keys", methods=["POST"])
@require_jwt()
def create_api_key():
    """
    创建 API Key
    """
    try:
        from services.data_service_manager import get_data_service_manager

        manager = get_data_service_manager()

        data = request.json
        user_id = g.user.get("user_id", "system")

        result = manager.create_api_key(
            name=data.get("name", "API Key"),
            user_id=user_id,
            scopes=data.get("scopes", ["read"]),
            expires_days=data.get("expires_days"),
        )

        return jsonify({
            "code": 0,
            "message": "success",
            "data": result
        })

    except Exception as e:
        logger.error(f"创建 API Key 失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/data-services/api-keys/<key_id>", methods=["DELETE"])
@require_jwt()
def delete_api_key(key_id: str):
    """
    删除 API Key
    """
    try:
        from services.data_service_manager import get_data_service_manager

        manager = get_data_service_manager()

        success = manager.delete_api_key(key_id)

        if not success:
            return jsonify({"code": 40004, "message": "API Key 不存在"}), 404

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {"deleted": True}
        })

    except Exception as e:
        logger.error(f"删除 API Key 失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/data-services/api-keys/<key_id>/deactivate", methods=["POST"])
@require_jwt()
def deactivate_api_key(key_id: str):
    """
    停用 API Key
    """
    try:
        from services.data_service_manager import get_data_service_manager

        manager = get_data_service_manager()

        success = manager.deactivate_api_key(key_id)

        if not success:
            return jsonify({"code": 40004, "message": "API Key 不存在"}), 404

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {"deactivated": True}
        })

    except Exception as e:
        logger.error(f"停用 API Key 失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


# ==================== API 调用记录 ====================

@app.route("/api/v1/data-services/call-records", methods=["GET"])
@require_jwt()
def get_api_call_records():
    """
    获取 API 调用记录
    """
    try:
        from services.data_service_manager import get_data_service_manager

        manager = get_data_service_manager()

        service_id = request.args.get("service_id")
        api_key_id = request.args.get("api_key_id")
        status_code = request.args.get("status_code", type=int)
        limit = request.args.get("limit", 100, type=int)
        offset = request.args.get("offset", 0, type=int)

        result = manager.get_call_records(
            service_id=service_id,
            api_key_id=api_key_id,
            status_code=status_code,
            limit=limit,
            offset=offset,
        )

        return jsonify({
            "code": 0,
            "message": "success",
            "data": result
        })

    except Exception as e:
        logger.error(f"获取调用记录失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


# ==================== 统计分析 ====================

@app.route("/api/v1/data-services/<service_id>/statistics", methods=["GET"])
@require_jwt()
def get_service_statistics(service_id: str):
    """
    获取服务调用统计
    """
    try:
        from services.data_service_manager import get_data_service_manager

        manager = get_data_service_manager()

        time_window_hours = request.args.get("time_window_hours", 24, type=int)

        result = manager.get_service_statistics(
            service_id=service_id,
            time_window_hours=time_window_hours,
        )

        return jsonify({
            "code": 0,
            "message": "success",
            "data": result
        })

    except Exception as e:
        logger.error(f"获取服务统计失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/data-services/statistics/overall", methods=["GET"])
@require_jwt()
def get_overall_statistics():
    """
    获取整体统计
    """
    try:
        from services.data_service_manager import get_data_service_manager

        manager = get_data_service_manager()

        time_window_hours = request.args.get("time_window_hours", 24, type=int)

        result = manager.get_overall_statistics(
            time_window_hours=time_window_hours,
        )

        return jsonify({
            "code": 0,
            "message": "success",
            "data": result
        })

    except Exception as e:
        logger.error(f"获取整体统计失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


# ==================== 统一门户 Portal API ====================

@app.route("/api/v1/portal/dashboard", methods=["GET"])
@require_jwt()
def get_portal_dashboard():
    """
    获取门户仪表盘数据
    """
    try:
        from services.portal_service import get_portal_service

        service = get_portal_service()

        user_id = g.user.get("user_id", "")
        tenant_id = request.args.get("tenant_id", "default")

        db = get_db_session()
        try:
            result = service.get_dashboard_data(db, user_id, tenant_id)
            return jsonify({
                "code": 0,
                "message": "success",
                "data": result
            })
        finally:
            db.close()

    except Exception as e:
        logger.error(f"获取仪表盘数据失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/portal/quick-links", methods=["GET"])
@require_jwt()
def get_quick_links():
    """
    获取快捷入口列表
    """
    try:
        from services.portal_service import get_portal_service

        service = get_portal_service()

        user_id = g.user.get("user_id", "")
        categories = request.args.getlist("categories")

        db = get_db_session()
        try:
            result = service.get_quick_links(db, user_id, categories)
            return jsonify({
                "code": 0,
                "message": "success",
                "data": result
            })
        finally:
            db.close()

    except Exception as e:
        logger.error(f"获取快捷入口失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/portal/notifications", methods=["GET"])
@require_jwt()
def get_portal_notifications():
    """
    获取门户通知列表
    """
    try:
        from services.portal_service import get_portal_service

        service = get_portal_service()

        user_id = g.user.get("user_id", "")
        unread_only = request.args.get("unread_only", "false").lower() == "true"
        limit = request.args.get("limit", 20, type=int)

        db = get_db_session()
        try:
            result = service.get_notifications(db, user_id, unread_only, limit)
            return jsonify({
                "code": 0,
                "message": "success",
                "data": result
            })
        finally:
            db.close()

    except Exception as e:
        logger.error(f"获取通知列表失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/portal/notifications/<notification_id>/read", methods=["POST"])
@require_jwt()
def mark_notification_read():
    """
    标记通知为已读
    """
    try:
        from services.portal_service import get_portal_service

        service = get_portal_service()

        notification_id = request.view_args.get("notification_id", "")
        user_id = g.user.get("user_id", "")

        db = get_db_session()
        try:
            success = service.mark_notification_read(db, notification_id, user_id)
            return jsonify({
                "code": 0,
                "message": "success",
                "data": {"read": success}
            })
        finally:
            db.close()

    except Exception as e:
        logger.error(f"标记通知已读失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/portal/notifications/read-all", methods=["POST"])
@require_jwt()
def mark_all_notifications_read():
    """
    标记所有通知为已读
    """
    try:
        from services.portal_service import get_portal_service

        service = get_portal_service()

        user_id = g.user.get("user_id", "")

        db = get_db_session()
        try:
            count = service.mark_all_notifications_read(db, user_id)
            return jsonify({
                "code": 0,
                "message": "success",
                "data": {"count": count}
            })
        finally:
            db.close()

    except Exception as e:
        logger.error(f"标记全部已读失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/portal/notifications/<notification_id>", methods=["DELETE"])
@require_jwt()
def delete_portal_notification():
    """
    删除通知
    """
    try:
        from services.portal_service import get_portal_service

        service = get_portal_service()

        notification_id = request.view_args.get("notification_id", "")
        user_id = g.user.get("user_id", "")

        db = get_db_session()
        try:
            success = service.delete_notification(db, notification_id, user_id)
            return jsonify({
                "code": 0,
                "message": "success",
                "data": {"deleted": success}
            })
        finally:
            db.close()

    except Exception as e:
        logger.error(f"删除通知失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/portal/todos", methods=["GET"])
@require_jwt()
def get_portal_todos():
    """
    获取待办事项列表
    """
    try:
        from services.portal_service import get_portal_service

        service = get_portal_service()

        user_id = g.user.get("user_id", "")
        status = request.args.get("status", "pending")
        source = request.args.get("source")
        limit = request.args.get("limit", 20, type=int)

        db = get_db_session()
        try:
            result = service.get_todos(db, user_id, status, source, limit)
            return jsonify({
                "code": 0,
                "message": "success",
                "data": result
            })
        finally:
            db.close()

    except Exception as e:
        logger.error(f"获取待办事项失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/portal/todos/<todo_id>/complete", methods=["POST"])
@require_jwt()
def complete_portal_todo():
    """
    完成待办事项
    """
    try:
        from services.portal_service import get_portal_service

        service = get_portal_service()

        todo_id = request.view_args.get("todo_id", "")
        user_id = g.user.get("user_id", "")

        db = get_db_session()
        try:
            success = service.complete_todo(db, todo_id, user_id)
            return jsonify({
                "code": 0,
                "message": "success",
                "data": {"completed": success}
            })
        finally:
            db.close()

    except Exception as e:
        logger.error(f"完成待办事项失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/portal/layout", methods=["GET"])
@require_jwt()
def get_user_portal_layout():
    """
    获取用户门户布局配置
    """
    try:
        from services.portal_service import get_portal_service

        service = get_portal_service()

        user_id = g.user.get("user_id", "")

        db = get_db_session()
        try:
            result = service.get_user_layout(db, user_id)
            return jsonify({
                "code": 0,
                "message": "success",
                "data": result
            })
        finally:
            db.close()

    except Exception as e:
        logger.error(f"获取用户布局失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/portal/layout", methods=["PUT"])
@require_jwt()
def update_user_portal_layout():
    """
    更新用户门户布局
    """
    try:
        from services.portal_service import get_portal_service

        service = get_portal_service()

        user_id = g.user.get("user_id", "")
        layout = request.json

        db = get_db_session()
        try:
            result = service.update_user_layout(db, user_id, layout)
            return jsonify({
                "code": 0,
                "message": "success",
                "data": result
            })
        finally:
            db.close()

    except Exception as e:
        logger.error(f"更新用户布局失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/portal/search", methods=["GET"])
@require_jwt()
def portal_global_search():
    """
    全局搜索
    """
    try:
        from services.portal_service import get_portal_service

        service = get_portal_service()

        user_id = g.user.get("user_id", "")
        query = request.args.get("query", "")
        categories = request.args.getlist("categories")
        limit = request.args.get("limit", 20, type=int)

        if not query:
            return jsonify({"code": 40001, "message": "query 不能为空"}), 400

        db = get_db_session()
        try:
            result = service.global_search(db, user_id, query, categories, limit)
            return jsonify({
                "code": 0,
                "message": "success",
                "data": result
            })
        finally:
            db.close()

    except Exception as e:
        logger.error(f"全局搜索失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/portal/system-status", methods=["GET"])
@require_jwt()
def get_system_status():
    """
    获取系统状态
    """
    try:
        from services.portal_service import get_portal_service

        service = get_portal_service()

        tenant_id = request.args.get("tenant_id", "default")

        db = get_db_session()
        try:
            result = service.get_system_status(db, tenant_id)
            return jsonify({
                "code": 0,
                "message": "success",
                "data": result
            })
        finally:
            db.close()

    except Exception as e:
        logger.error(f"获取系统状态失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


# ==================== 统一通知管理 API ====================

@app.route("/api/v1/notifications/channels", methods=["GET"])
@require_jwt()
def get_notification_channels():
    """
    获取已注册的通知渠道列表
    """
    try:
        from services.notification_service import get_notification_service

        service = get_notification_service()

        channels = service.list_channels()

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "channels": channels,
                "total": len(channels)
            }
        })

    except Exception as e:
        logger.error(f"获取通知渠道失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/notifications/templates", methods=["GET"])
@require_jwt()
def get_notification_templates():
    """
    获取通知模板列表
    """
    try:
        from services.notification_service import get_notification_service

        service = get_notification_service()

        templates = service.list_templates()

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "templates": [
                    {
                        "template_id": t.template_id,
                        "name": t.name,
                        "description": t.description,
                        "type": t.type,
                        "supported_channels": t.supported_channels,
                        "variables": t.variables,
                        "enabled": t.enabled,
                    }
                    for t in templates
                ],
                "total": len(templates)
            }
        })

    except Exception as e:
        logger.error(f"获取通知模板失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/notifications/templates/<template_id>", methods=["GET"])
@require_jwt()
def get_notification_template(template_id: str):
    """
    获取通知模板详情
    """
    try:
        from services.notification_service import get_notification_service

        service = get_notification_service()

        template = service.get_template(template_id)
        if not template:
            return jsonify({"code": 40401, "message": "模板不存在"}), 404

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "template_id": template.template_id,
                "name": template.name,
                "description": template.description,
                "subject_template": template.subject_template,
                "body_template": template.body_template,
                "type": template.type,
                "supported_channels": template.supported_channels,
                "variables": template.variables,
                "enabled": template.enabled,
            }
        })

    except Exception as e:
        logger.error(f"获取通知模板详情失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/notifications/templates", methods=["POST"])
@require_jwt()
def create_notification_template():
    """
    创建通知模板
    """
    data = request.json

    try:
        from services.notification_service import get_notification_service

        service = get_notification_service()

        template = service.create_template(
            template_id=data.get("template_id") or f"tpl_{secrets.token_hex(8)}",
            name=data.get("name"),
            description=data.get("description", ""),
            subject_template=data.get("subject_template"),
            body_template=data.get("body_template"),
            type=data.get("type", "info"),
            supported_channels=data.get("supported_channels", ["inapp"]),
            variables=data.get("variables", []),
        )

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {"template_id": template.template_id}
        })

    except Exception as e:
        logger.error(f"创建通知模板失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/notifications/templates/<template_id>", methods=["PUT"])
@require_jwt()
def update_notification_template(template_id: str):
    """
    更新通知模板
    """
    data = request.json

    try:
        from services.notification_service import get_notification_service

        service = get_notification_service()

        template = service.update_template(template_id, **data)
        if not template:
            return jsonify({"code": 40401, "message": "模板不存在"}), 404

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {"template_id": template.template_id}
        })

    except Exception as e:
        logger.error(f"更新通知模板失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/notifications/templates/<template_id>", methods=["DELETE"])
@require_jwt()
def delete_notification_template(template_id: str):
    """
    删除通知模板
    """
    try:
        from services.notification_service import get_notification_service

        service = get_notification_service()

        success = service.delete_template(template_id)
        if not success:
            return jsonify({"code": 40401, "message": "模板不存在"}), 404

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {"deleted": True}
        })

    except Exception as e:
        logger.error(f"删除通知模板失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/notifications/rules", methods=["GET"])
@require_jwt()
def get_notification_rules():
    """
    获取通知规则列表
    """
    try:
        from services.notification_service import get_notification_service

        service = get_notification_service()

        rules = service.list_rules()

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "rules": [
                    {
                        "rule_id": r.rule_id,
                        "name": r.name,
                        "description": r.description,
                        "event_type": r.event_type,
                        "conditions": r.conditions,
                        "template_id": r.template_id,
                        "channels": r.channels,
                        "recipients": r.recipients,
                        "enabled": r.enabled,
                        "throttle_minutes": r.throttle_minutes,
                    }
                    for r in rules
                ],
                "total": len(rules)
            }
        })

    except Exception as e:
        logger.error(f"获取通知规则失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/notifications/rules/<rule_id>", methods=["GET"])
@require_jwt()
def get_notification_rule(rule_id: str):
    """
    获取通知规则详情
    """
    try:
        from services.notification_service import get_notification_service

        service = get_notification_service()

        rule = service.get_rule(rule_id)
        if not rule:
            return jsonify({"code": 40401, "message": "规则不存在"}), 404

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "rule_id": rule.rule_id,
                "name": rule.name,
                "description": rule.description,
                "event_type": rule.event_type,
                "conditions": rule.conditions,
                "template_id": rule.template_id,
                "channels": rule.channels,
                "recipients": rule.recipients,
                "enabled": rule.enabled,
                "throttle_minutes": rule.throttle_minutes,
            }
        })

    except Exception as e:
        logger.error(f"获取通知规则详情失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/notifications/rules", methods=["POST"])
@require_jwt()
def create_notification_rule():
    """
    创建通知规则
    """
    data = request.json

    try:
        from services.notification_service import get_notification_service

        service = get_notification_service()

        rule = service.create_rule(
            rule_id=data.get("rule_id") or f"rule_{secrets.token_hex(8)}",
            name=data.get("name"),
            description=data.get("description", ""),
            event_type=data.get("event_type"),
            conditions=data.get("conditions", {}),
            template_id=data.get("template_id"),
            channels=data.get("channels", ["inapp"]),
            recipients=data.get("recipients", []),
            throttle_minutes=data.get("throttle_minutes", 60),
        )

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {"rule_id": rule.rule_id}
        })

    except Exception as e:
        logger.error(f"创建通知规则失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/notifications/rules/<rule_id>", methods=["PUT"])
@require_jwt()
def update_notification_rule(rule_id: str):
    """
    更新通知规则
    """
    data = request.json

    try:
        from services.notification_service import get_notification_service

        service = get_notification_service()

        rule = service.update_rule(rule_id, **data)
        if not rule:
            return jsonify({"code": 40401, "message": "规则不存在"}), 404

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {"rule_id": rule.rule_id}
        })

    except Exception as e:
        logger.error(f"更新通知规则失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/notifications/rules/<rule_id>", methods=["DELETE"])
@require_jwt()
def delete_notification_rule(rule_id: str):
    """
    删除通知规则
    """
    try:
        from services.notification_service import get_notification_service

        service = get_notification_service()

        success = service.delete_rule(rule_id)
        if not success:
            return jsonify({"code": 40401, "message": "规则不存在"}), 404

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {"deleted": True}
        })

    except Exception as e:
        logger.error(f"删除通知规则失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/notifications/rules/<rule_id>/enable", methods=["POST"])
@require_jwt()
def enable_notification_rule(rule_id: str):
    """
    启用通知规则
    """
    try:
        from services.notification_service import get_notification_service

        service = get_notification_service()

        success = service.enable_rule(rule_id)
        if not success:
            return jsonify({"code": 40401, "message": "规则不存在"}), 404

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {"enabled": True}
        })

    except Exception as e:
        logger.error(f"启用通知规则失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/notifications/rules/<rule_id>/disable", methods=["POST"])
@require_jwt()
def disable_notification_rule(rule_id: str):
    """
    禁用通知规则
    """
    try:
        from services.notification_service import get_notification_service

        service = get_notification_service()

        success = service.disable_rule(rule_id)
        if not success:
            return jsonify({"code": 40401, "message": "规则不存在"}), 404

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {"enabled": False}
        })

    except Exception as e:
        logger.error(f"禁用通知规则失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/notifications/send", methods=["POST"])
@require_jwt()
def send_notification():
    """
    发送通知
    """
    data = request.json

    try:
        from services.notification_service import get_notification_service

        service = get_notification_service()

        # 如果提供了 template_id，使用模板发送
        if data.get("template_id"):
            message_ids = service.send_by_template(
                template_id=data["template_id"],
                variables=data.get("variables", {}),
                recipients=data.get("recipients", []),
                channels=data.get("channels", ["inapp"]),
                action_url=data.get("action_url"),
            )
        else:
            # 直接发送
            message_ids = service.send(
                recipients=data.get("recipients", []),
                subject=data.get("subject", ""),
                body=data.get("body", ""),
                channels=data.get("channels", ["inapp"]),
                title=data.get("title"),
                type=data.get("type", "info"),
                priority=data.get("priority", "normal"),
                action_url=data.get("action_url"),
                data=data.get("data"),
            )

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "message_ids": message_ids,
                "sent_count": len(message_ids)
            }
        })

    except Exception as e:
        logger.error(f"发送通知失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/notifications/trigger", methods=["POST"])
@require_jwt()
def trigger_notification_event():
    """
    触发通知事件
    """
    data = request.json

    try:
        from services.notification_service import get_notification_service

        service = get_notification_service()

        message_ids = service.trigger_event(
            event_type=data.get("event_type"),
            event_data=data.get("event_data", {}),
        )

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "message_ids": message_ids,
                "sent_count": len(message_ids)
            }
        })

    except Exception as e:
        logger.error(f"触发通知事件失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/notifications/history", methods=["GET"])
@require_jwt()
def get_notification_history():
    """
    获取通知历史
    """
    try:
        from services.notification_service import get_notification_service

        service = get_notification_service()

        recipient = request.args.get("recipient")
        channel = request.args.get("channel")
        status = request.args.get("status")
        limit = int(request.args.get("limit", 100))

        history = service.get_history(
            recipient=recipient,
            channel=channel,
            status=status,
            limit=limit,
        )

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "history": [
                    {
                        "history_id": h.history_id,
                        "message_id": h.message_id,
                        "recipient": h.recipient,
                        "channel": h.channel,
                        "status": h.status,
                        "error_message": h.error_message,
                        "sent_at": h.sent_at.isoformat() if h.sent_at else None,
                        "retry_count": h.retry_count,
                    }
                    for h in history
                ],
                "total": len(history)
            }
        })

    except Exception as e:
        logger.error(f"获取通知历史失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/notifications/statistics", methods=["GET"])
@require_jwt()
def get_notification_statistics():
    """
    获取通知统计
    """
    try:
        from services.notification_service import get_notification_service

        service = get_notification_service()

        days = int(request.args.get("days", 30))
        stats = service.get_statistics(days)

        return jsonify({
            "code": 0,
            "message": "success",
            "data": stats
        })

    except Exception as e:
        logger.error(f"获取通知统计失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


# ==================== 统一内容管理 API ====================

@app.route("/api/v1/content/articles", methods=["GET"])
@require_jwt()
def get_content_articles():
    """
    获取内容文章列表
    """
    try:
        from services.content_service import get_content_service

        service = get_content_service()

        content_type = request.args.get("content_type")
        status = request.args.get("status")
        category_id = request.args.get("category_id")
        tag_id = request.args.get("tag_id")
        author_id = request.args.get("author_id")
        featured = request.args.get("featured")
        keyword = request.args.get("keyword")
        limit = int(request.args.get("limit", 20))
        offset = int(request.args.get("offset", 0))

        articles, total = service.list_articles(
            content_type=content_type,
            status=status,
            category_id=category_id,
            tag_id=tag_id,
            author_id=author_id,
            featured=featured == "true" if featured else None,
            keyword=keyword,
            limit=limit,
            offset=offset,
        )

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "articles": [a.to_dict() for a in articles],
                "total": total,
                "limit": limit,
                "offset": offset,
            }
        })

    except Exception as e:
        logger.error(f"获取文章列表失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/content/articles/<content_id>", methods=["GET"])
def get_content_article(content_id: str):
    """
    获取文章详情
    """
    try:
        from services.content_service import get_content_service

        service = get_content_service()

        # 增加阅读数
        service.increment_view_count(content_id)

        article = service.get_article(content_id)
        if not article:
            return jsonify({"code": 40401, "message": "文章不存在"}), 404

        return jsonify({
            "code": 0,
            "message": "success",
            "data": article.to_dict()
        })

    except Exception as e:
        logger.error(f"获取文章详情失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/content/articles", methods=["POST"])
@require_jwt()
def create_content_article():
    """
    创建文章
    """
    data = request.json

    try:
        from services.content_service import get_content_service

        service = get_content_service()

        article = service.create_article(
            title=data.get("title"),
            content=data.get("content"),
            content_type=data.get("content_type", "article"),
            author_id=data.get("author_id", ""),
            author_name=data.get("author_name", ""),
            summary=data.get("summary", ""),
            category_id=data.get("category_id"),
            tags=data.get("tags", []),
            cover_image=data.get("cover_image", ""),
            featured=data.get("featured", False),
            allow_comment=data.get("allow_comment", True),
            status=data.get("status", "draft"),
            metadata=data.get("metadata", {}),
        )

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {"content_id": article.content_id}
        })

    except Exception as e:
        logger.error(f"创建文章失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/content/articles/<content_id>", methods=["PUT"])
@require_jwt()
def update_content_article(content_id: str):
    """
    更新文章
    """
    data = request.json

    try:
        from services.content_service import get_content_service

        service = get_content_service()

        article = service.update_article(content_id, **data)
        if not article:
            return jsonify({"code": 40401, "message": "文章不存在"}), 404

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {"content_id": article.content_id}
        })

    except Exception as e:
        logger.error(f"更新文章失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/content/articles/<content_id>", methods=["DELETE"])
@require_jwt()
def delete_content_article(content_id: str):
    """
    删除文章
    """
    try:
        from services.content_service import get_content_service

        service = get_content_service()

        success = service.delete_article(content_id)
        if not success:
            return jsonify({"code": 40401, "message": "文章不存在"}), 404

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {"deleted": True}
        })

    except Exception as e:
        logger.error(f"删除文章失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/content/articles/<content_id>/publish", methods=["POST"])
@require_jwt()
def publish_content_article(content_id: str):
    """
    发布文章
    """
    try:
        from services.content_service import get_content_service

        service = get_content_service()

        article = service.publish_article(content_id)
        if not article:
            return jsonify({"code": 40401, "message": "文章不存在"}), 404

        return jsonify({
            "code": 0,
            "message": "success",
            "data": article.to_dict()
        })

    except Exception as e:
        logger.error(f"发布文章失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/content/articles/<content_id>/like", methods=["POST"])
@require_jwt()
def like_content_article(content_id: str):
    """
    点赞文章
    """
    try:
        from services.content_service import get_content_service

        service = get_content_service()
        user_id = request.headers.get("X-User-Id", "anonymous")

        success = service.toggle_like(content_id, user_id)
        if not success:
            return jsonify({"code": 40401, "message": "文章不存在"}), 404

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {"liked": True}
        })

    except Exception as e:
        logger.error(f"点赞文章失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/content/categories", methods=["GET"])
def get_content_categories():
    """
    获取内容分类列表
    """
    try:
        from services.content_service import get_content_service

        service = get_content_service()

        enabled_only = request.args.get("enabled_only", "false") == "true"
        categories = service.list_categories(enabled_only=enabled_only)

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "categories": [
                    {
                        "category_id": c.category_id,
                        "name": c.name,
                        "description": c.description,
                        "parent_id": c.parent_id,
                        "icon": c.icon,
                        "sort_order": c.sort_order,
                        "enabled": c.enabled,
                    }
                    for c in categories
                ],
                "total": len(categories)
            }
        })

    except Exception as e:
        logger.error(f"获取分类列表失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/content/categories", methods=["POST"])
@require_jwt()
def create_content_category():
    """
    创建分类
    """
    data = request.json

    try:
        from services.content_service import get_content_service

        service = get_content_service()

        category = service.create_category(
            name=data.get("name"),
            description=data.get("description", ""),
            parent_id=data.get("parent_id"),
            icon=data.get("icon", ""),
            sort_order=data.get("sort_order", 0),
        )

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {"category_id": category.category_id}
        })

    except Exception as e:
        logger.error(f"创建分类失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/content/tags", methods=["GET"])
def get_content_tags():
    """
    获取内容标签列表
    """
    try:
        from services.content_service import get_content_service

        service = get_content_service()

        tags = service.list_tags()

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "tags": [
                    {
                        "tag_id": t.tag_id,
                        "name": t.name,
                        "color": t.color,
                        "usage_count": t.usage_count,
                    }
                    for t in tags
                ],
                "total": len(tags)
            }
        })

    except Exception as e:
        logger.error(f"获取标签列表失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/content/tags", methods=["POST"])
@require_jwt()
def create_content_tag():
    """
    创建标签
    """
    data = request.json

    try:
        from services.content_service import get_content_service

        service = get_content_service()

        tag = service.create_tag(
            name=data.get("name"),
            color=data.get("color", "#1890ff"),
        )

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {"tag_id": tag.tag_id}
        })

    except Exception as e:
        logger.error(f"创建标签失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/content/articles/<content_id>/comments", methods=["GET"])
def get_content_comments(content_id: str):
    """
    获取文章评论列表
    """
    try:
        from services.content_service import get_content_service

        service = get_content_service()

        status = request.args.get("status", "approved")
        limit = int(request.args.get("limit", 50))

        comments = service.list_comments(
            content_id=content_id,
            status=status,
            limit=limit,
        )

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "comments": [c.to_dict() for c in comments],
                "total": len(comments)
            }
        })

    except Exception as e:
        logger.error(f"获取评论列表失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/content/comments", methods=["POST"])
@require_jwt()
def create_content_comment():
    """
    创建评论
    """
    data = request.json

    try:
        from services.content_service import get_content_service

        service = get_content_service()

        comment = service.create_comment(
            content_id=data.get("content_id"),
            user_id=data.get("user_id", ""),
            user_name=data.get("user_name", ""),
            content=data.get("content", ""),
            parent_id=data.get("parent_id"),
            user_avatar=data.get("user_avatar", ""),
        )

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {"comment_id": comment.comment_id}
        })

    except Exception as e:
        logger.error(f"创建评论失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/content/comments/<comment_id>/approve", methods=["POST"])
@require_jwt()
def approve_content_comment(comment_id: str):
    """
    审核通过评论
    """
    try:
        from services.content_service import get_content_service

        service = get_content_service()

        success = service.approve_comment(comment_id)
        if not success:
            return jsonify({"code": 40401, "message": "评论不存在"}), 404

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {"approved": True}
        })

    except Exception as e:
        logger.error(f"审核评论失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/content/comments/<comment_id>", methods=["DELETE"])
@require_jwt()
def delete_content_comment(comment_id: str):
    """
    删除评论
    """
    try:
        from services.content_service import get_content_service

        service = get_content_service()

        success = service.delete_comment(comment_id)
        if not success:
            return jsonify({"code": 40401, "message": "评论不存在"}), 404

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {"deleted": True}
        })

    except Exception as e:
        logger.error(f"删除评论失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/content/search", methods=["GET"])
def search_content():
    """
    全文搜索内容
    """
    try:
        from services.content_service import get_content_service

        service = get_content_service()

        query = request.args.get("q", "")
        content_type = request.args.get("content_type")
        limit = int(request.args.get("limit", 20))

        if not query:
            return jsonify({"code": 40001, "message": "搜索关键词不能为空"}), 400

        articles = service.search(
            query=query,
            content_type=content_type,
            limit=limit,
        )

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "results": [a.to_dict() for a in articles],
                "total": len(articles)
            }
        })

    except Exception as e:
        logger.error(f"搜索内容失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/content/statistics", methods=["GET"])
@require_jwt()
def get_content_statistics():
    """
    获取内容统计
    """
    try:
        from services.content_service import get_content_service

        service = get_content_service()

        stats = service.get_statistics()

        return jsonify({
            "code": 0,
            "message": "success",
            "data": stats
        })

    except Exception as e:
        logger.error(f"获取内容统计失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


# ==================== 元数据版本对比 API ====================

@app.route("/api/v1/metadata/snapshots", methods=["GET"])
@require_jwt()
def get_metadata_snapshots():
    """
    获取元数据快照列表
    """
    try:
        from services.metadata_version_service import get_metadata_version_service

        service = get_metadata_version_service()

        database = request.args.get("database")
        limit = int(request.args.get("limit", 50))

        snapshots = service.list_snapshots(database=database, limit=limit)

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "snapshots": [s.to_dict() for s in snapshots],
                "total": len(snapshots)
            }
        })

    except Exception as e:
        logger.error(f"获取快照列表失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/metadata/snapshots/<snapshot_id>", methods=["GET"])
@require_jwt()
def get_metadata_snapshot(snapshot_id: str):
    """
    获取元数据快照详情
    """
    try:
        from services.metadata_version_service import get_metadata_version_service

        service = get_metadata_version_service()

        snapshot = service.get_snapshot(snapshot_id)
        if not snapshot:
            return jsonify({"code": 40401, "message": "快照不存在"}), 404

        return jsonify({
            "code": 0,
            "message": "success",
            "data": snapshot.to_dict()
        })

    except Exception as e:
        logger.error(f"获取快照详情失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/metadata/snapshots", methods=["POST"])
@require_jwt()
def create_metadata_snapshot():
    """
    创建元数据快照
    """
    data = request.json

    try:
        from services.metadata_version_service import get_metadata_version_service

        service = get_metadata_version_service()

        # 简化处理，实际应该从数据库读取当前元数据
        snapshot = service.create_snapshot(
            version=data.get("version"),
            database=data.get("database", "default"),
            tables={},  # 实际应从数据库读取
            created_by=data.get("created_by", "user"),
            description=data.get("description", ""),
            tags=data.get("tags", []),
        )

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {"snapshot_id": snapshot.snapshot_id}
        })

    except Exception as e:
        logger.error(f"创建快照失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/metadata/snapshots/<snapshot_id>", methods=["DELETE"])
@require_jwt()
def delete_metadata_snapshot(snapshot_id: str):
    """
    删除元数据快照
    """
    try:
        from services.metadata_version_service import get_metadata_version_service

        service = get_metadata_version_service()

        success = service.delete_snapshot(snapshot_id)
        if not success:
            return jsonify({"code": 40401, "message": "快照不存在"}), 404

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {"deleted": True}
        })

    except Exception as e:
        logger.error(f"删除快照失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/metadata/compare", methods=["POST"])
@require_jwt()
def compare_metadata_snapshots():
    """
    对比两个元数据快照
    """
    data = request.json

    try:
        from services.metadata_version_service import get_metadata_version_service

        service = get_metadata_version_service()

        from_snapshot_id = data.get("from_snapshot_id")
        to_snapshot_id = data.get("to_snapshot_id")

        if not from_snapshot_id or not to_snapshot_id:
            return jsonify({"code": 40001, "message": "from_snapshot_id 和 to_snapshot_id 不能为空"}), 400

        diff = service.compare_snapshots(from_snapshot_id, to_snapshot_id)

        return jsonify({
            "code": 0,
            "message": "success",
            "data": diff
        })

    except ValueError as e:
        return jsonify({"code": 40401, "message": str(e)}), 404
    except Exception as e:
        logger.error(f"对比快照失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/metadata/compare/<from_id>/<to_id>/sql", methods=["GET"])
@require_jwt()
def get_migration_sql(from_id: str, to_id: str):
    """
    获取迁移 SQL
    """
    try:
        from services.metadata_version_service import get_metadata_version_service

        service = get_metadata_version_service()

        sql_statements = service.generate_migration_sql(from_id, to_id)

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "sql_statements": sql_statements,
                "summary": f"共 {len(sql_statements)} 个表需要迁移"
            }
        })

    except Exception as e:
        logger.error(f"生成迁移 SQL 失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/metadata/history", methods=["GET"])
@require_jwt()
def get_metadata_version_history():
    """
    获取元数据版本历史
    """
    try:
        from services.metadata_version_service import get_metadata_version_service

        service = get_metadata_version_service()

        database = request.args.get("database")
        table_name = request.args.get("table_name")
        limit = int(request.args.get("limit", 20))

        history = service.get_version_history(
            database=database,
            table_name=table_name,
            limit=limit,
        )

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "history": history,
                "total": len(history)
            }
        })

    except Exception as e:
        logger.error(f"获取版本历史失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


# ==================== 智能任务调度 API ====================

@app.route("/api/v1/scheduler/tasks", methods=["GET"])
@require_jwt()
def get_scheduled_tasks():
    """
    获取调度任务列表
    """
    try:
        from services.smart_scheduler_service import get_smart_scheduler_service

        service = get_smart_scheduler_service()

        status = request.args.get("status")
        priority = request.args.get("priority")
        task_type = request.args.get("task_type")
        limit = int(request.args.get("limit", 100))

        tasks = service.list_tasks(
            status=TaskStatus(status) if status else None,
            priority=TaskPriority(priority) if priority else None,
            task_type=task_type,
            limit=limit,
        )

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "tasks": [t.to_dict() for t in tasks],
                "total": len(tasks)
            }
        })

    except Exception as e:
        logger.error(f"获取任务列表失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/scheduler/tasks/<task_id>", methods=["GET"])
@require_jwt()
def get_scheduled_task(task_id: str):
    """
    获取调度任务详情
    """
    try:
        from services.smart_scheduler_service import get_smart_scheduler_service

        service = get_smart_scheduler_service()

        task = service.get_task(task_id)
        if not task:
            return jsonify({"code": 40401, "message": "任务不存在"}), 404

        return jsonify({
            "code": 0,
            "message": "success",
            "data": task.to_dict()
        })

    except Exception as e:
        logger.error(f"获取任务详情失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/scheduler/tasks", methods=["POST"])
@require_jwt()
def create_scheduled_task():
    """
    创建调度任务
    """
    data = request.json

    try:
        from services.smart_scheduler_service import get_smart_scheduler_service

        service = get_smart_scheduler_service()

        task = service.create_task(
            name=data.get("name"),
            task_type=data.get("task_type", "etl"),
            priority=TaskPriority(data.get("priority", "normal")),
            description=data.get("description", ""),
            dependencies=data.get("dependencies", []),
            resource_requirement=data.get("resource_requirement", {}),
            estimated_duration_ms=data.get("estimated_duration_ms", 60000),
            deadline=datetime.fromisoformat(data["deadline"]) if data.get("deadline") else None,
            created_by=data.get("created_by", "user"),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
        )

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {"task_id": task.task_id}
        })

    except Exception as e:
        logger.error(f"创建任务失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/scheduler/tasks/<task_id>", methods=["PUT"])
@require_jwt()
def update_scheduled_task(task_id: str):
    """
    更新调度任务
    """
    data = request.json

    try:
        from services.smart_scheduler_service import get_smart_scheduler_service

        service = get_smart_scheduler_service()

        task = service.update_task(task_id, **data)
        if not task:
            return jsonify({"code": 40401, "message": "任务不存在"}), 404

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {"task_id": task.task_id}
        })

    except Exception as e:
        logger.error(f"更新任务失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/scheduler/tasks/<task_id>", methods=["DELETE"])
@require_jwt()
def delete_scheduled_task(task_id: str):
    """
    删除调度任务
    """
    try:
        from services.smart_scheduler_service import get_smart_scheduler_service

        service = get_smart_scheduler_service()

        success = service.delete_task(task_id)
        if not success:
            return jsonify({"code": 40401, "message": "任务不存在"}), 404

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {"deleted": True}
        })

    except Exception as e:
        logger.error(f"删除任务失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/scheduler/optimize", methods=["POST"])
@require_jwt()
def optimize_schedule():
    """
    优化调度顺序
    """
    try:
        from services.smart_scheduler_service import get_smart_scheduler_service

        service = get_smart_scheduler_service()

        result = service.optimize_schedule()

        return jsonify({
            "code": 0,
            "message": "success",
            "data": result
        })

    except Exception as e:
        logger.error(f"优化调度失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/scheduler/resource-demand", methods=["GET"])
@require_jwt()
def get_resource_demand():
    """
    获取资源需求预测
    """
    try:
        from services.smart_scheduler_service import get_smart_scheduler_service

        service = get_smart_scheduler_service()

        window_minutes = int(request.args.get("window_minutes", 60))
        demand = service.predict_resource_demand(window_minutes)

        return jsonify({
            "code": 0,
            "message": "success",
            "data": demand
        })

    except Exception as e:
        logger.error(f"获取资源需求失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/scheduler/statistics", methods=["GET"])
@require_jwt()
def get_scheduler_statistics():
    """
    获取调度统计
    """
    try:
        from services.smart_scheduler_service import get_smart_scheduler_service

        service = get_smart_scheduler_service()

        stats = service.get_statistics()

        return jsonify({
            "code": 0,
            "message": "success",
            "data": stats
        })

    except Exception as e:
        logger.error(f"获取调度统计失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/scheduler/next-task", methods=["POST"])
@require_jwt()
def get_next_task():
    """
    获取下一个可执行任务
    """
    try:
        from services.smart_scheduler_service import get_smart_scheduler_service

        service = get_smart_scheduler_service()

        task = service.get_next_task()
        if not task:
            return jsonify({
                "code": 0,
                "message": "No pending tasks",
                "data": None
            })

        # 开始执行任务
        service.start_task(task.task_id)

        return jsonify({
            "code": 0,
            "message": "success",
            "data": task.to_dict()
        })

    except Exception as e:
        logger.error(f"获取下一个任务失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/scheduler/tasks/<task_id>/complete", methods=["POST"])
@require_jwt()
def complete_scheduled_task(task_id: str):
    """
    完成任务
    """
    data = request.json

    try:
        from services.smart_scheduler_service import get_smart_scheduler_service

        service = get_smart_scheduler_service()

        task = service.complete_task(
            task_id=task_id,
            success=data.get("success", True),
            error_message=data.get("error_message", ""),
            execution_time_ms=data.get("execution_time_ms"),
        )

        if not task:
            return jsonify({"code": 40401, "message": "任务不存在"}), 404

        return jsonify({
            "code": 0,
            "message": "success",
            "data": task.to_dict()
        })

    except Exception as e:
        logger.error(f"完成任务失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


# ==================== AI 调度增强 API ====================

@app.route("/api/v1/scheduler/ai/calculate-priority", methods=["POST"])
@require_jwt()
def calculate_ai_priority():
    """
    计算任务的 AI 优先级分数
    """
    db = next(get_db())
    data = request.json

    try:
        from services.ai_scheduler_enhancement import get_ai_scheduler_enhancer
        from services.smart_scheduler_service import get_smart_scheduler_service

        scheduler_service = get_smart_scheduler_service()
        enhancer = get_ai_scheduler_enhancer()

        task_ids = data.get("task_ids", [])

        if not task_ids:
            return jsonify({"code": 40001, "message": "task_ids 不能为空"}), 400

        results = []
        for task_id in task_ids:
            task = scheduler_service.get_task(task_id)
            if task:
                score = enhancer.calculate_priority_score(task)
                results.append(score.to_dict())

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "scores": results,
                "total": len(results),
            }
        })

    except Exception as e:
        logger.error(f"计算 AI 优先级失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/scheduler/ai/predict-execution-time", methods=["POST"])
@require_jwt()
def predict_execution_time():
    """
    预测任务执行时间
    """
    db = next(get_db())
    data = request.json

    try:
        from services.ai_scheduler_enhancement import get_ai_scheduler_enhancer
        from services.smart_scheduler_service import get_smart_scheduler_service

        scheduler_service = get_smart_scheduler_service()
        enhancer = get_ai_scheduler_enhancer()

        task_ids = data.get("task_ids", [])

        if not task_ids:
            return jsonify({"code": 40001, "message": "task_ids 不能为空"}), 400

        results = []
        for task_id in task_ids:
            task = scheduler_service.get_task(task_id)
            if task:
                prediction = enhancer.predict_execution_time(task)
                results.append(prediction.to_dict())

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "predictions": results,
                "total": len(results),
            }
        })

    except Exception as e:
        logger.error(f"预测执行时间失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/scheduler/ai/recommend-resources", methods=["POST"])
@require_jwt()
def recommend_task_resources():
    """
    推荐任务资源分配
    """
    db = next(get_db())
    data = request.json

    try:
        from services.ai_scheduler_enhancement import get_ai_scheduler_enhancer
        from services.smart_scheduler_service import get_smart_scheduler_service

        scheduler_service = get_smart_scheduler_service()
        enhancer = get_ai_scheduler_enhancer()

        task_ids = data.get("task_ids", [])
        available_resources = data.get("available_resources", {
            "cpu_cores": 16.0,
            "memory_mb": 32768,
            "gpu_count": 4,
        })

        if not task_ids:
            return jsonify({"code": 40001, "message": "task_ids 不能为空"}), 400

        results = []
        for task_id in task_ids:
            task = scheduler_service.get_task(task_id)
            if task:
                recommendation = enhancer.recommend_resource_allocation(task, available_resources)
                results.append(recommendation.to_dict())

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "recommendations": results,
                "total": len(results),
            }
        })

    except Exception as e:
        logger.error(f"推荐资源分配失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/scheduler/ai/optimize-order", methods=["POST"])
@require_jwt()
def optimize_schedule_order_ai():
    """
    AI 优化调度顺序
    """
    db = next(get_db())
    data = request.json

    try:
        from services.ai_scheduler_enhancement import get_ai_scheduler_enhancer
        from services.smart_scheduler_service import get_smart_scheduler_service

        scheduler_service = get_smart_scheduler_service()
        enhancer = get_ai_scheduler_enhancer()

        task_ids = data.get("task_ids", [])
        resource_constraints = data.get("resource_constraints")

        if not task_ids:
            return jsonify({"code": 40001, "message": "task_ids 不能为空"}), 400

        tasks = []
        for task_id in task_ids:
            task = scheduler_service.get_task(task_id)
            if task:
                tasks.append(task)

        if not tasks:
            return jsonify({"code": 40401, "message": "未找到有效任务"}), 404

        result = enhancer.optimize_schedule_order(tasks, resource_constraints)

        return jsonify({
            "code": 0,
            "message": "success",
            "data": result
        })

    except Exception as e:
        logger.error(f"AI 优化调度顺序失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/scheduler/ai/batch-analyze", methods=["POST"])
@require_jwt()
def batch_analyze_tasks():
    """
    批量分析任务（优先级、执行时间、资源推荐）
    """
    db = next(get_db())
    data = request.json

    try:
        from services.ai_scheduler_enhancement import get_ai_scheduler_enhancer
        from services.smart_scheduler_service import get_smart_scheduler_service

        scheduler_service = get_smart_scheduler_service()
        enhancer = get_ai_scheduler_enhancer()

        task_ids = data.get("task_ids", [])
        available_resources = data.get("available_resources", {
            "cpu_cores": 16.0,
            "memory_mb": 32768,
            "gpu_count": 4,
        })

        if not task_ids:
            return jsonify({"code": 40001, "message": "task_ids 不能为空"}), 400

        results = []
        for task_id in task_ids:
            task = scheduler_service.get_task(task_id)
            if not task:
                continue

            priority_score = enhancer.calculate_priority_score(task)
            execution_time = enhancer.predict_execution_time(task)
            resource_recommendation = enhancer.recommend_resource_allocation(task, available_resources)

            results.append({
                "task_id": task_id,
                "task_name": task.name,
                "priority_score": priority_score.to_dict(),
                "execution_time": execution_time.to_dict(),
                "resource_recommendation": resource_recommendation.to_dict(),
            })

        # 按优先级排序
        results.sort(key=lambda x: x["priority_score"]["final_score"], reverse=True)

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "analysis": results,
                "total": len(results),
            }
        })

    except Exception as e:
        logger.error(f"批量分析任务失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/scheduler/ai/business-impact/update", methods=["PUT"])
@require_jwt()
def update_task_business_impact():
    """
    更新任务业务影响等级
    """
    db = next(get_db())
    data = request.json

    try:
        from services.smart_scheduler_service import get_smart_scheduler_service

        service = get_smart_scheduler_service()

        task_id = data.get("task_id")
        business_impact = data.get("business_impact")
        data_freshness = data.get("data_freshness")

        if not task_id:
            return jsonify({"code": 40001, "message": "task_id 不能为空"}), 400

        task = service.get_task(task_id)
        if not task:
            return jsonify({"code": 40401, "message": "任务不存在"}), 404

        # 更新元数据
        if business_impact:
            task.metadata["business_impact"] = business_impact
        if data_freshness:
            task.metadata["data_freshness"] = data_freshness

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "task_id": task_id,
                "metadata": task.metadata,
            }
        })

    except Exception as e:
        logger.error(f"更新业务影响失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


# ==================== Kettle AI 集成 API ====================

@app.route("/api/v1/etl/inject-ai-rules", methods=["POST"])
@require_jwt()
def inject_ai_rules_to_kettle():
    """
    注入 AI 规则到 Kettle 转换

    将 AI 清洗/填充规则自动转换为 Kettle 步骤
    """
    data = request.json

    try:
        from src.kettle_ai_integrator import get_kettle_ai_integrator

        integrator = get_kettle_ai_integrator()

        trans_xml = data.get("transformation_xml")
        if not trans_xml:
            return jsonify({"code": 40001, "message": "transformation_xml 不能为空"}), 400

        cleaning_rules = data.get("cleaning_rules", [])
        imputation_rules = data.get("imputation_rules", [])

        # 注入 AI 步骤
        modified_xml = integrator.inject_ai_steps_to_transformation(
            trans_xml=trans_xml,
            cleaning_rules=cleaning_rules,
            imputation_rules=imputation_rules,
        )

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "modified_xml": modified_xml,
                "injected_cleaning_rules": len(cleaning_rules),
                "injected_imputation_rules": len(imputation_rules),
            }
        })
    except ImportError as e:
        return jsonify({"code": 50001, "message": f"Kettle AI 集成服务不可用: {e}"}), 500
    except Exception as e:
        logger.error(f"注入 AI 规则失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/etl/inject-masking", methods=["POST"])
@require_jwt()
def inject_masking_rules_to_kettle():
    """
    注入脱敏规则到 Kettle 转换

    基于敏感字段标注自动注入脱敏步骤
    """
    db = next(get_db())
    data = request.json

    try:
        from src.kettle_ai_integrator import get_kettle_ai_integrator

        integrator = get_kettle_ai_integrator()

        trans_xml = data.get("transformation_xml")
        if not trans_xml:
            return jsonify({"code": 40001, "message": "transformation_xml 不能为空"}), 400

        masking_rules = data.get("masking_rules", {})

        # 如果未提供脱敏规则，尝试从表的敏感字段标注获取
        if not masking_rules and data.get("table_id"):
            table_id = data.get("table_id")
            table = db.query(MetadataTable).filter(
                MetadataTable.table_id == table_id
            ).first()

            if table:
                columns = db.query(MetadataColumn).filter(
                    MetadataColumn.table_id == table.id,
                    MetadataColumn.sensitivity_level.in_(["confidential", "restricted"])
                ).all()

                for col in columns:
                    sens_type = col.sensitivity_type or "pii"
                    # 根据敏感类型选择脱敏策略
                    strategy = "partial_mask"
                    if sens_type == "credential":
                        strategy = "full_mask"
                    elif sens_type in ["pii", "phone"]:
                        strategy = "phone_mask" if "phone" in col.column_name.lower() else "partial_mask"
                    elif sens_type == "email":
                        strategy = "email_mask"
                    elif sens_type == "financial":
                        strategy = "hash"

                    masking_rules[col.column_name] = {
                        "strategy": strategy,
                        "sensitivity_type": sens_type,
                    }

        if not masking_rules:
            return jsonify({
                "code": 0,
                "message": "无需脱敏",
                "data": {
                    "modified_xml": trans_xml,
                    "masked_columns": [],
                }
            })

        # 注入脱敏规则
        modified_xml = integrator.inject_masking_rules(
            trans_xml=trans_xml,
            masking_config=masking_rules,
        )

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "modified_xml": modified_xml,
                "masked_columns": list(masking_rules.keys()),
            }
        })
    except ImportError as e:
        return jsonify({"code": 50001, "message": f"Kettle AI 集成服务不可用: {e}"}), 500
    except Exception as e:
        logger.error(f"注入脱敏规则失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


# ==================== 元数据版本 API ====================

@app.route("/api/v1/metadata/versions/<table_id>", methods=["GET"])
@require_jwt()
def get_metadata_versions(table_id):
    """
    获取元数据版本历史
    """
    db = next(get_db())

    try:
        from models.metadata_version import MetadataVersionModel

        page = request.args.get("page", 1, type=int)
        page_size = request.args.get("page_size", 20, type=int)
        change_type = request.args.get("change_type")

        query = db.query(MetadataVersionModel).filter(
            MetadataVersionModel.table_id == table_id
        )

        if change_type:
            query = query.filter(MetadataVersionModel.change_type == change_type)

        total = query.count()
        versions = query.order_by(
            MetadataVersionModel.created_at.desc()
        ).offset((page - 1) * page_size).limit(page_size).all()

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "versions": [v.to_dict() for v in versions],
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total": total,
                    "total_pages": (total + page_size - 1) // page_size,
                }
            }
        })
    except ImportError as e:
        return jsonify({"code": 50001, "message": f"元数据版本服务不可用: {e}"}), 500
    except Exception as e:
        logger.error(f"获取元数据版本失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/metadata/versions/<table_id>/<version_id>", methods=["GET"])
@require_jwt()
def get_metadata_version_detail(table_id, version_id):
    """
    获取元数据版本详情
    """
    db = next(get_db())

    try:
        from models.metadata_version import MetadataVersionModel

        version = db.query(MetadataVersionModel).filter(
            MetadataVersionModel.id == version_id,
            MetadataVersionModel.table_id == table_id
        ).first()

        if not version:
            return jsonify({"code": 40401, "message": "版本不存在"}), 404

        return jsonify({
            "code": 0,
            "message": "success",
            "data": version.to_dict()
        })
    except ImportError as e:
        return jsonify({"code": 50001, "message": f"元数据版本服务不可用: {e}"}), 500
    except Exception as e:
        logger.error(f"获取元数据版本详情失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/metadata/versions/<table_id>/compare", methods=["POST"])
@require_jwt()
def compare_metadata_versions(table_id):
    """
    比较两个元数据版本
    """
    db = next(get_db())
    data = request.json

    try:
        from src.metadata_sync import get_metadata_sync_service

        service = get_metadata_sync_service()

        version_id_1 = data.get("version_id_1")
        version_id_2 = data.get("version_id_2")

        if not version_id_1 or not version_id_2:
            return jsonify({"code": 40001, "message": "需要提供两个版本 ID"}), 400

        diff = service.compare_versions(db, version_id_1, version_id_2)

        return jsonify({
            "code": 0,
            "message": "success",
            "data": diff
        })
    except ImportError as e:
        return jsonify({"code": 50001, "message": f"元数据同步服务不可用: {e}"}), 500
    except Exception as e:
        logger.error(f"比较元数据版本失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/metadata/versions/<table_id>/rollback", methods=["POST"])
@require_jwt()
def rollback_metadata_version(table_id):
    """
    回滚到指定元数据版本
    """
    db = next(get_db())
    data = request.json

    try:
        from src.metadata_sync import get_metadata_sync_service

        service = get_metadata_sync_service()

        version_id = data.get("version_id")
        if not version_id:
            return jsonify({"code": 40001, "message": "version_id 不能为空"}), 400

        success = service.rollback_to_version(db, table_id, version_id)

        if success:
            return jsonify({
                "code": 0,
                "message": "回滚成功",
                "data": {
                    "table_id": table_id,
                    "rolled_back_to": version_id,
                }
            })
        else:
            return jsonify({"code": 50002, "message": "回滚失败"}), 500
    except ImportError as e:
        return jsonify({"code": 50001, "message": f"元数据同步服务不可用: {e}"}), 500
    except Exception as e:
        logger.error(f"元数据版本回滚失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/metadata/versions/<table_id>/rollback/preview", methods=["POST"])
@require_jwt()
def preview_metadata_rollback(table_id):
    """
    预览元数据版本回滚操作
    返回将要执行的操作、SQL 语句和警告信息
    """
    db = next(get_db())
    data = request.json

    try:
        from services.metadata_rollback_service import get_metadata_rollback_service

        service = get_metadata_rollback_service(db)

        target_version_id = data.get("target_version_id")
        if not target_version_id:
            return jsonify({"code": 40001, "message": "target_version_id 不能为空"}), 400

        plan = service.preview_rollback(table_id, target_version_id)

        return jsonify({
            "code": 0,
            "message": "success",
            "data": plan.to_dict()
        })

    except ValueError as e:
        return jsonify({"code": 40002, "message": str(e)}), 400
    except Exception as e:
        logger.error(f"预览回滚失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/metadata/versions/<table_id>/rollback/execute", methods=["POST"])
@require_jwt()
def execute_metadata_rollback(table_id):
    """
    执行元数据版本回滚操作
    支持备份和数据库执行选项
    """
    db = next(get_db())
    data = request.json

    try:
        from services.metadata_rollback_service import get_metadata_rollback_service

        service = get_metadata_rollback_service(db)

        target_version_id = data.get("target_version_id")
        if not target_version_id:
            return jsonify({"code": 40001, "message": "target_version_id 不能为空"}), 400

        create_backup = data.get("create_backup", True)
        execute_on_database = data.get("execute_on_database", False)

        # 获取当前用户
        changed_by = "system"
        if AUTH_ENABLED:
            try:
                current_user = get_current_user()
                if current_user:
                    changed_by = current_user.get("username", "unknown")
            except:
                pass

        result = service.execute_rollback(
            table_id=table_id,
            target_version_id=target_version_id,
            create_backup=create_backup,
            execute_on_database=execute_on_database,
            changed_by=changed_by,
        )

        if result.success:
            return jsonify({
                "code": 0,
                "message": "回滚成功",
                "data": result.to_dict()
            })
        else:
            return jsonify({
                "code": 50002,
                "message": result.error_message or "回滚失败"
            }), 500

    except Exception as e:
        logger.error(f"执行回滚失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/metadata/versions/migration/generate", methods=["POST"])
@require_jwt()
def generate_migration_script():
    """
    生成版本迁移 SQL 脚本
    支持多种数据库方言
    """
    db = next(get_db())
    data = request.json

    try:
        from services.metadata_rollback_service import get_metadata_rollback_service

        service = get_metadata_rollback_service(db)

        table_id = data.get("table_id")
        from_version_id = data.get("from_version_id")
        to_version_id = data.get("to_version_id")
        dialect = data.get("dialect", "mysql")

        if not all([table_id, from_version_id, to_version_id]):
            return jsonify({
                "code": 40001,
                "message": "table_id, from_version_id, to_version_id 不能为空"
            }), 400

        if dialect not in ["mysql", "postgresql", "oracle", "sqlserver"]:
            return jsonify({
                "code": 40002,
                "message": f"不支持的数据库方言: {dialect}"
            }), 400

        script = service.generate_migration_script(
            table_id=table_id,
            from_version_id=from_version_id,
            to_version_id=to_version_id,
            dialect=dialect,
        )

        if "error" in script:
            return jsonify({"code": 50002, "message": script["error"]}), 500

        return jsonify({
            "code": 0,
            "message": "success",
            "data": script
        })

    except Exception as e:
        logger.error(f"生成迁移脚本失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/metadata/versions/diff/visualize", methods=["POST"])
@require_jwt()
def visualize_version_diff():
    """
    可视化版本差异对比
    返回用于前端展示的差异数据
    """
    db = next(get_db())
    data = request.json

    try:
        from services.metadata_version_service import get_metadata_version_service

        service = get_metadata_version_service()

        from_snapshot_id = data.get("from_snapshot_id")
        to_snapshot_id = data.get("to_snapshot_id")

        if not all([from_snapshot_id, to_snapshot_id]):
            return jsonify({
                "code": 40001,
                "message": "from_snapshot_id 和 to_snapshot_id 不能为空"
            }), 400

        diff = service.compare_snapshots(from_snapshot_id, to_snapshot_id)

        # 添加可视化友好的格式
        diff["visualization"] = {
            "added_tables_count": len(diff.get("added_tables", [])),
            "removed_tables_count": len(diff.get("removed_tables", [])),
            "modified_tables_count": len(diff.get("modified_tables", [])),
            "total_changes": (
                len(diff.get("added_tables", [])) +
                len(diff.get("removed_tables", [])) +
                len(diff.get("modified_tables", []))
            ),
        }

        return jsonify({
            "code": 0,
            "message": "success",
            "data": diff
        })

    except Exception as e:
        logger.error(f"可视化差异失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


# ==================== Kafka 流式数据 API ====================

@app.route("/api/v1/streaming/kafka/test-connection", methods=["POST"])
@require_jwt()
def test_kafka_connection():
    """
    测试 Kafka 连接
    """
    db = next(get_db())
    data = request.json

    try:
        from services.kafka_stream_service import get_kafka_stream_service

        service = get_kafka_stream_service()

        bootstrap_servers = data.get("bootstrap_servers")
        if not bootstrap_servers:
            return jsonify({"code": 40001, "message": "bootstrap_servers 不能为空"}), 400

        result = service.validate_connection(bootstrap_servers)

        return jsonify({
            "code": 0 if result["success"] else 50001,
            "message": "连接成功" if result["success"] else "连接失败",
            "data": result,
        })

    except Exception as e:
        logger.error(f"测试 Kafka 连接失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/streaming/kafka/consumers", methods=["POST"])
@require_jwt()
def create_kafka_consumer():
    """
    创建 Kafka 消费者
    """
    db = next(get_db())
    data = request.json

    try:
        from services.kafka_stream_service import (
            get_kafka_stream_service,
            KafkaConsumerConfig,
            OffsetReset,
        )

        service = get_kafka_stream_service()

        consumer_id = data.get("consumer_id") or f"kafka_{secrets.token_hex(8)}"
        bootstrap_servers = data.get("bootstrap_servers")
        group_id = data.get("group_id")
        topics = data.get("topics", [])

        if not all([bootstrap_servers, group_id, topics]):
            return jsonify({
                "code": 40001,
                "message": "bootstrap_servers, group_id, topics 不能为空"
            }), 400

        config = KafkaConsumerConfig(
            bootstrap_servers=bootstrap_servers,
            group_id=group_id,
            topics=topics,
            auto_offset_reset=OffsetReset(data.get("auto_offset_reset", "latest")),
            enable_auto_commit=data.get("enable_auto_commit", True),
            auto_commit_interval_ms=data.get("auto_commit_interval_ms", 5000),
            max_poll_records=data.get("max_poll_records", 500),
            additional_config=data.get("additional_config", {}),
        )

        consumer = service.create_consumer(consumer_id, config)

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "consumer_id": consumer_id,
                "config": config.to_dict(),
            }
        })

    except Exception as e:
        logger.error(f"创建 Kafka 消费者失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/streaming/kafka/consumers/<consumer_id>/start", methods=["POST"])
@require_jwt()
def start_kafka_consumer(consumer_id):
    """
    启动 Kafka 消费者
    """
    db = next(get_db())

    try:
        from services.kafka_stream_service import get_kafka_stream_service

        service = get_kafka_stream_service()

        success = service.start_consumer(consumer_id)

        if success:
            return jsonify({
                "code": 0,
                "message": "消费者启动成功",
                "data": {"consumer_id": consumer_id}
            })
        else:
            return jsonify({
                "code": 50002,
                "message": "消费者启动失败"
            }), 500

    except Exception as e:
        logger.error(f"启动 Kafka 消费者失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/streaming/kafka/consumers/<consumer_id>/stop", methods=["POST"])
@require_jwt()
def stop_kafka_consumer(consumer_id):
    """
    停止 Kafka 消费者
    """
    db = next(get_db())

    try:
        from services.kafka_stream_service import get_kafka_stream_service

        service = get_kafka_stream_service()
        service.stop_consumer(consumer_id)

        return jsonify({
            "code": 0,
            "message": "消费者已停止",
            "data": {"consumer_id": consumer_id}
        })

    except Exception as e:
        logger.error(f"停止 Kafka 消费者失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/streaming/kafka/consumers/<consumer_id>/pause", methods=["POST"])
@require_jwt()
def pause_kafka_consumer(consumer_id):
    """
    暂停 Kafka 消费者
    """
    db = next(get_db())

    try:
        from services.kafka_stream_service import get_kafka_stream_service

        service = get_kafka_stream_service()
        consumer = service._consumers.get(consumer_id)

        if consumer:
            consumer.pause()
            return jsonify({
                "code": 0,
                "message": "消费者已暂停",
                "data": {"consumer_id": consumer_id}
            })
        else:
            return jsonify({"code": 40401, "message": "消费者不存在"}), 404

    except Exception as e:
        logger.error(f"暂停 Kafka 消费者失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/streaming/kafka/consumers/<consumer_id>/resume", methods=["POST"])
@require_jwt()
def resume_kafka_consumer(consumer_id):
    """
    恢复 Kafka 消费者
    """
    db = next(get_db())

    try:
        from services.kafka_stream_service import get_kafka_stream_service

        service = get_kafka_stream_service()
        consumer = service._consumers.get(consumer_id)

        if consumer:
            consumer.resume()
            return jsonify({
                "code": 0,
                "message": "消费者已恢复",
                "data": {"consumer_id": consumer_id}
            })
        else:
            return jsonify({"code": 40401, "message": "消费者不存在"}), 404

    except Exception as e:
        logger.error(f"恢复 Kafka 消费者失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/streaming/kafka/consumers", methods=["GET"])
@require_jwt()
def list_kafka_consumers():
    """
    列出所有 Kafka 消费者及其指标
    """
    db = next(get_db())

    try:
        from services.kafka_stream_service import get_kafka_stream_service

        service = get_kafka_stream_service()
        metrics = service.get_all_metrics()

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "consumers": [m.to_dict() for m in metrics.values()],
                "total": len(metrics),
            }
        })

    except Exception as e:
        logger.error(f"获取 Kafka 消费者列表失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/streaming/kafka/consumers/<consumer_id>/metrics", methods=["GET"])
@require_jwt()
def get_kafka_consumer_metrics(consumer_id):
    """
    获取单个 Kafka 消费者指标
    """
    db = next(get_db())

    try:
        from services.kafka_stream_service import get_kafka_stream_service

        service = get_kafka_stream_service()
        metrics = service.get_consumer_metrics(consumer_id)

        if metrics:
            return jsonify({
                "code": 0,
                "message": "success",
                "data": metrics.to_dict()
            })
        else:
            return jsonify({"code": 40401, "message": "消费者不存在"}), 404

    except Exception as e:
        logger.error(f"获取 Kafka 消费者指标失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/streaming/kafka/topics/<topic>/messages", methods=["GET"])
@require_jwt()
def get_kafka_messages(topic):
    """
    获取缓冲的 Kafka 消息
    """
    db = next(get_db())

    try:
        from services.kafka_stream_service import get_kafka_stream_service

        service = get_kafka_stream_service()

        limit = request.args.get("limit", 100, type=int)
        clear = request.args.get("clear", "false").lower() == "true"

        messages = service.get_buffered_messages(topic, limit=limit, clear=clear)

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "topic": topic,
                "messages": messages,
                "count": len(messages),
            }
        })

    except Exception as e:
        logger.error(f"获取 Kafka 消息失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/streaming/kafka/consumers/<consumer_id>/seek", methods=["POST"])
@require_jwt()
def seek_kafka_offset(consumer_id):
    """
    跳转到指定偏移量
    """
    db = next(get_db())
    data = request.json

    try:
        from services.kafka_stream_service import get_kafka_stream_service

        service = get_kafka_stream_service()
        consumer = service._consumers.get(consumer_id)

        if not consumer:
            return jsonify({"code": 40401, "message": "消费者不存在"}), 404

        topic = data.get("topic")
        partition = data.get("partition", 0)
        offset = data.get("offset")

        if not all([topic, offset is not None]):
            return jsonify({"code": 40001, "message": "topic, offset 不能为空"}), 400

        success = consumer.seek_to_offset(topic, partition, offset)

        if success:
            return jsonify({
                "code": 0,
                "message": "偏移量跳转成功",
                "data": {
                    "consumer_id": consumer_id,
                    "topic": topic,
                    "partition": partition,
                    "offset": offset,
                }
            })
        else:
            return jsonify({"code": 50002, "message": "偏移量跳转失败"}), 500

    except Exception as e:
        logger.error(f"跳转 Kafka 偏移量失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/streaming/kafka/consumers/<consumer_id>/remove", methods=["DELETE"])
@require_jwt()
def remove_kafka_consumer(consumer_id):
    """
    移除 Kafka 消费者
    """
    db = next(get_db())

    try:
        from services.kafka_stream_service import get_kafka_stream_service

        service = get_kafka_stream_service()
        service.remove_consumer(consumer_id)

        return jsonify({
            "code": 0,
            "message": "消费者已移除",
            "data": {"consumer_id": consumer_id}
        })

    except Exception as e:
        logger.error(f"移除 Kafka 消费者失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


# ==================== 审批工作流 API ====================

@app.route("/api/v1/approval/templates", methods=["GET"])
@require_jwt()
def list_approval_templates():
    """获取审批模板列表"""
    db = next(get_db())
    try:
        from services.approval_workflow_engine import get_approval_workflow_engine
        engine = get_approval_workflow_engine()
        templates = engine.list_templates(db_session=db)
        return jsonify({
            "code": 0,
            "data": [t.to_dict() if hasattr(t, 'to_dict') else t for t in templates]
        })
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"获取审批模板失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/approval/templates", methods=["POST"])
@require_jwt()
def create_approval_template():
    """创建审批模板"""
    db = next(get_db())
    data = request.json
    try:
        from services.approval_workflow_engine import get_approval_workflow_engine
        engine = get_approval_workflow_engine()
        template = engine.create_template(data, db_session=db)
        return jsonify({
            "code": 0,
            "message": "审批模板创建成功",
            "data": template.to_dict() if hasattr(template, 'to_dict') else template
        })
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"创建审批模板失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/approval/requests", methods=["POST"])
@require_jwt()
def submit_approval_request():
    """提交审批请求"""
    db = next(get_db())
    data = request.json
    try:
        from services.approval_workflow_engine import get_approval_workflow_engine
        engine = get_approval_workflow_engine()
        req = engine.submit_request(data, db_session=db)
        return jsonify({
            "code": 0,
            "message": "审批请求已提交",
            "data": req.to_dict() if hasattr(req, 'to_dict') else req
        })
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"提交审批请求失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/approval/requests/<request_id>", methods=["GET"])
@require_jwt()
def get_approval_request(request_id):
    """获取审批请求详情"""
    db = next(get_db())
    try:
        from services.approval_workflow_engine import get_approval_workflow_engine
        engine = get_approval_workflow_engine()
        req = engine.get_request_detail(request_id, db_session=db)
        if not req:
            return jsonify({"code": 40400, "message": "审批请求不存在"}), 404
        return jsonify({
            "code": 0,
            "data": req.to_dict() if hasattr(req, 'to_dict') else req
        })
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"获取审批请求失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/approval/requests/<request_id>/approve", methods=["POST"])
@require_jwt()
def process_approval(request_id):
    """处理审批（批准/拒绝）"""
    db = next(get_db())
    data = request.json or {}
    data["request_id"] = request_id
    try:
        from services.approval_workflow_engine import get_approval_workflow_engine
        engine = get_approval_workflow_engine()
        result = engine.process_approval(request_id, data, db_session=db)
        return jsonify({
            "code": 0,
            "message": "审批处理成功",
            "data": {"success": result}
        })
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"处理审批失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/approval/pending", methods=["GET"])
@require_jwt()
def get_pending_approvals():
    """获取待审批列表"""
    db = next(get_db())
    user_id = request.args.get("user_id", "")
    try:
        from services.approval_workflow_engine import get_approval_workflow_engine
        engine = get_approval_workflow_engine()
        pending = engine.get_pending_approvals(user_id, db_session=db)
        return jsonify({
            "code": 0,
            "data": [p.to_dict() if hasattr(p, 'to_dict') else p for p in pending]
        })
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"获取待审批列表失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/approval/statistics", methods=["GET"])
@require_jwt()
def get_approval_statistics():
    """获取审批统计"""
    db = next(get_db())
    try:
        from services.approval_workflow_engine import get_approval_workflow_engine
        engine = get_approval_workflow_engine()
        stats = engine.get_approval_statistics(db_session=db)
        return jsonify({"code": 0, "data": stats})
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"获取审批统计失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


# ==================== CDC 变更数据捕获 API ====================

@app.route("/api/v1/cdc/tasks", methods=["POST"])
@require_jwt()
def create_cdc_task():
    """创建 CDC 采集任务"""
    db = next(get_db())
    data = request.json
    try:
        from services.cdc_service import get_cdc_service, CDCConfig
        service = get_cdc_service()
        import secrets
        cdc_id = data.get("cdc_id") or f"cdc_{secrets.token_hex(8)}"
        config = CDCConfig(
            source_type=data.get("source_type", "mysql"),
            host=data.get("host", "localhost"),
            port=data.get("port", 3306),
            database=data.get("database", ""),
            username=data.get("username", ""),
            password=data.get("password", ""),
            tables=data.get("tables", []),
        )
        result = service.create_cdc_task(cdc_id, config)
        return jsonify({
            "code": 0,
            "message": "CDC 任务创建成功",
            "data": {"cdc_id": cdc_id, "success": result}
        })
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"创建 CDC 任务失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/cdc/tasks/<cdc_id>/start", methods=["POST"])
@require_jwt()
def start_cdc_task(cdc_id):
    """启动 CDC 任务"""
    db = next(get_db())
    try:
        from services.cdc_service import get_cdc_service
        service = get_cdc_service()
        result = service.start_cdc_task(cdc_id)
        return jsonify({
            "code": 0,
            "message": "CDC 任务已启动",
            "data": {"cdc_id": cdc_id, "success": result}
        })
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"启动 CDC 任务失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/cdc/tasks/<cdc_id>/stop", methods=["POST"])
@require_jwt()
def stop_cdc_task(cdc_id):
    """停止 CDC 任务"""
    db = next(get_db())
    try:
        from services.cdc_service import get_cdc_service
        service = get_cdc_service()
        service.stop_cdc_task(cdc_id)
        return jsonify({
            "code": 0,
            "message": "CDC 任务已停止",
            "data": {"cdc_id": cdc_id}
        })
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"停止 CDC 任务失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/cdc/tasks/<cdc_id>/metrics", methods=["GET"])
@require_jwt()
def get_cdc_metrics(cdc_id):
    """获取 CDC 任务指标"""
    db = next(get_db())
    try:
        from services.cdc_service import get_cdc_service
        service = get_cdc_service()
        metrics_data = service.get_metrics(cdc_id)
        if not metrics_data:
            return jsonify({"code": 40400, "message": "CDC 任务不存在"}), 404
        return jsonify({
            "code": 0,
            "data": metrics_data.to_dict() if hasattr(metrics_data, 'to_dict') else metrics_data
        })
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"获取 CDC 指标失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/cdc/metrics", methods=["GET"])
@require_jwt()
def get_all_cdc_metrics():
    """获取所有 CDC 任务指标"""
    db = next(get_db())
    try:
        from services.cdc_service import get_cdc_service
        service = get_cdc_service()
        all_metrics = service.get_all_metrics()
        return jsonify({
            "code": 0,
            "data": {k: v.to_dict() if hasattr(v, 'to_dict') else v for k, v in all_metrics.items()}
        })
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"获取所有 CDC 指标失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/cdc/tasks/<cdc_id>/events", methods=["GET"])
@require_jwt()
def get_cdc_events(cdc_id):
    """获取 CDC 缓冲事件"""
    db = next(get_db())
    limit = request.args.get("limit", 100, type=int)
    clear = request.args.get("clear", "false").lower() == "true"
    try:
        from services.cdc_service import get_cdc_service
        service = get_cdc_service()
        events = service.get_buffered_events(cdc_id, limit=limit, clear=clear)
        return jsonify({"code": 0, "data": events})
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"获取 CDC 事件失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/cdc/tasks/<cdc_id>", methods=["DELETE"])
@require_jwt()
def remove_cdc_task(cdc_id):
    """删除 CDC 任务"""
    db = next(get_db())
    try:
        from services.cdc_service import get_cdc_service
        service = get_cdc_service()
        service.remove_cdc_task(cdc_id)
        return jsonify({"code": 0, "message": "CDC 任务已删除"})
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"删除 CDC 任务失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


# ==================== 表融合推荐 API ====================

@app.route("/api/v1/table-fusion/join-keys", methods=["POST"])
@require_jwt()
def detect_join_keys():
    """检测潜在 JOIN 键"""
    db = next(get_db())
    data = request.json
    try:
        from services.table_fusion_service import get_table_fusion_service
        service = get_table_fusion_service()
        table1 = data.get("table1")
        table2 = data.get("table2")
        threshold = data.get("similarity_threshold", 0.6)
        if not table1 or not table2:
            return jsonify({"code": 40001, "message": "table1 和 table2 不能为空"}), 400
        keys = service.detect_potential_join_keys(table1, table2, threshold, db_session=db)
        return jsonify({
            "code": 0,
            "data": [k.to_dict() if hasattr(k, 'to_dict') else k for k in keys]
        })
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"检测 JOIN 键失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/table-fusion/join-quality", methods=["POST"])
@require_jwt()
def validate_join_quality():
    """验证 JOIN 一致性"""
    db = next(get_db())
    data = request.json
    try:
        from services.table_fusion_service import get_table_fusion_service
        service = get_table_fusion_service()
        table1 = data.get("table1")
        table2 = data.get("table2")
        join_keys = data.get("join_keys", [])
        if not table1 or not table2 or not join_keys:
            return jsonify({"code": 40001, "message": "table1, table2, join_keys 不能为空"}), 400
        score = service.validate_join_consistency(table1, table2, join_keys, db_session=db)
        return jsonify({
            "code": 0,
            "data": score.to_dict() if hasattr(score, 'to_dict') else score
        })
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"验证 JOIN 一致性失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/table-fusion/recommend", methods=["POST"])
@require_jwt()
def recommend_join_strategy():
    """推荐 JOIN 策略"""
    db = next(get_db())
    data = request.json
    try:
        from services.table_fusion_service import get_table_fusion_service
        service = get_table_fusion_service()
        table1 = data.get("table1")
        table2 = data.get("table2")
        if not table1 or not table2:
            return jsonify({"code": 40001, "message": "table1 和 table2 不能为空"}), 400
        rec = service.recommend_join_strategy(table1, table2, db_session=db)
        return jsonify({
            "code": 0,
            "data": rec.to_dict() if hasattr(rec, 'to_dict') else rec
        })
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"推荐 JOIN 策略失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/table-fusion/multi-path", methods=["POST"])
@require_jwt()
def detect_multi_table_join_path():
    """检测多表 JOIN 路径"""
    db = next(get_db())
    data = request.json
    try:
        from services.table_fusion_service import get_table_fusion_service
        service = get_table_fusion_service()
        tables = data.get("tables", [])
        if len(tables) < 2:
            return jsonify({"code": 40001, "message": "至少需要两个表"}), 400
        path = service.detect_multi_table_join_path(tables, db_session=db)
        return jsonify({"code": 0, "data": path})
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"检测多表 JOIN 路径失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/table-fusion/kettle-config", methods=["POST"])
@require_jwt()
def generate_kettle_join_config():
    """生成 Kettle JOIN 配置"""
    db = next(get_db())
    data = request.json
    try:
        from services.table_fusion_service import get_table_fusion_service
        service = get_table_fusion_service()
        table1 = data.get("table1")
        table2 = data.get("table2")
        join_keys = data.get("join_keys", [])
        if not table1 or not table2 or not join_keys:
            return jsonify({"code": 40001, "message": "table1, table2, join_keys 不能为空"}), 400
        config_xml = service.generate_kettle_join_config(table1, table2, join_keys, db_session=db)
        return jsonify({"code": 0, "data": {"xml": config_xml}})
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"生成 Kettle JOIN 配置失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


# ==================== 元数据自动扫描 API ====================

@app.route("/api/v1/metadata/auto-scan", methods=["POST"])
@require_jwt()
def trigger_metadata_scan():
    """触发元数据自动扫描"""
    db = next(get_db())
    data = request.json or {}
    try:
        from services.metadata_auto_scan_engine import get_metadata_auto_scan_engine
        engine = get_metadata_auto_scan_engine()
        database = data.get("database", "")
        schema = data.get("schema", "public")
        if not database:
            return jsonify({"code": 40001, "message": "database 不能为空"}), 400
        result = engine.scan_database(database, schema, db_session=db)
        return jsonify({"code": 0, "message": "扫描完成", "data": result})
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"元数据扫描失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/metadata/auto-scan/history", methods=["GET"])
@require_jwt()
def get_scan_history():
    """获取扫描历史"""
    db = next(get_db())
    database = request.args.get("database", "")
    limit = request.args.get("limit", 20, type=int)
    try:
        from services.metadata_auto_scan_engine import get_metadata_auto_scan_engine
        engine = get_metadata_auto_scan_engine()
        history = engine.get_scan_history(database, limit=limit, db_session=db)
        return jsonify({"code": 0, "data": history})
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"获取扫描历史失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/metadata/auto-scan/changes", methods=["POST"])
@require_jwt()
def detect_metadata_changes():
    """检测元数据变更"""
    db = next(get_db())
    data = request.json or {}
    try:
        from services.metadata_auto_scan_engine import get_metadata_auto_scan_engine
        engine = get_metadata_auto_scan_engine()
        database = data.get("database", "")
        schema = data.get("schema", "public")
        if not database:
            return jsonify({"code": 40001, "message": "database 不能为空"}), 400
        report = engine.detect_changes(database, schema, db_session=db)
        return jsonify({
            "code": 0,
            "data": report.to_dict() if hasattr(report, 'to_dict') else report
        })
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"检测元数据变更失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/metadata/auto-scan/profile", methods=["POST"])
@require_jwt()
def scan_and_profile():
    """扫描并生成 Profile"""
    db = next(get_db())
    data = request.json or {}
    try:
        from services.metadata_auto_scan_engine import get_metadata_auto_scan_engine
        engine = get_metadata_auto_scan_engine()
        database = data.get("database", "")
        schema = data.get("schema", "public")
        tables = data.get("tables", [])
        if not database:
            return jsonify({"code": 40001, "message": "database 不能为空"}), 400
        result = engine.scan_and_profile(database, schema, tables=tables, db_session=db)
        return jsonify({"code": 0, "data": result})
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"扫描 Profile 失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


# ==================== 元数据 Schema 提供 API ====================

@app.route("/api/v1/metadata/schema-selection", methods=["POST"])
@require_jwt()
def get_schema_for_question():
    """为自然语言问题选择相关 Schema"""
    db = next(get_db())
    data = request.json or {}
    try:
        from services.metadata_schema_provider import get_schema_provider
        provider = get_schema_provider()
        question = data.get("question", "")
        limit = data.get("limit", 5)
        if not question:
            return jsonify({"code": 40001, "message": "question 不能为空"}), 400
        result = provider.get_schema_for_question(question, limit=limit, db_session=db)
        return jsonify({
            "code": 0,
            "data": result.to_dict() if hasattr(result, 'to_dict') else result
        })
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Schema 选择失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/metadata/table-suggestions", methods=["GET"])
@require_jwt()
def get_table_suggestions():
    """获取表建议"""
    db = next(get_db())
    question = request.args.get("question", "")
    top_k = request.args.get("top_k", 5, type=int)
    try:
        from services.metadata_schema_provider import get_schema_provider
        provider = get_schema_provider()
        if not question:
            return jsonify({"code": 40001, "message": "question 不能为空"}), 400
        suggestions = provider.get_table_suggestions(question, top_k=top_k, db_session=db)
        return jsonify({
            "code": 0,
            "data": [s.to_dict() if hasattr(s, 'to_dict') else s for s in suggestions]
        })
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"获取表建议失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


# ==================== OpenLineage 事件 API ====================

@app.route("/api/v1/lineage/events", methods=["POST"])
@require_jwt()
def emit_lineage_event():
    """发送血缘事件"""
    db = next(get_db())
    data = request.json
    try:
        from services.openlineage_event_service import get_openlineage_event_service
        service = get_openlineage_event_service()
        result = service.emit_event(data)
        return jsonify({
            "code": 0,
            "message": "事件已发送",
            "data": {"success": result}
        })
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"发送血缘事件失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/lineage/events/batch", methods=["POST"])
@require_jwt()
def emit_lineage_events_batch():
    """批量发送血缘事件"""
    db = next(get_db())
    data = request.json
    try:
        from services.openlineage_event_service import get_openlineage_event_service
        service = get_openlineage_event_service()
        events = data.get("events", [])
        result = service.emit_batch(events)
        return jsonify({
            "code": 0,
            "message": "批量事件已发送",
            "data": {"success": result}
        })
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"批量发送血缘事件失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/lineage/upstream/<path:dataset>", methods=["GET"])
@require_jwt()
def get_lineage_upstream(dataset):
    """获取上游血缘"""
    db = next(get_db())
    try:
        from services.openlineage_event_service import get_openlineage_event_service
        service = get_openlineage_event_service()
        upstream = service.get_upstream(dataset)
        return jsonify({"code": 0, "data": upstream})
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"获取上游血缘失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/lineage/downstream/<path:dataset>", methods=["GET"])
@require_jwt()
def get_lineage_downstream(dataset):
    """获取下游血缘"""
    db = next(get_db())
    try:
        from services.openlineage_event_service import get_openlineage_event_service
        service = get_openlineage_event_service()
        downstream = service.get_downstream(dataset)
        return jsonify({"code": 0, "data": downstream})
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"获取下游血缘失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/lineage/impact/<path:dataset>", methods=["GET"])
@require_jwt()
def get_lineage_impact(dataset):
    """获取影响分析"""
    db = next(get_db())
    try:
        from services.openlineage_event_service import get_openlineage_event_service
        service = get_openlineage_event_service()
        impact = service.get_impact_analysis(dataset)
        return jsonify({"code": 0, "data": impact})
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"获取影响分析失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/lineage/events/recent", methods=["GET"])
@require_jwt()
def get_recent_lineage_events():
    """获取最近血缘事件"""
    db = next(get_db())
    limit = request.args.get("limit", 50, type=int)
    try:
        from services.openlineage_event_service import get_openlineage_event_service
        service = get_openlineage_event_service()
        events = service.get_recent_events(limit=limit)
        return jsonify({"code": 0, "data": events})
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"获取最近血缘事件失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/lineage/service/health", methods=["GET"])
@require_jwt()
def get_lineage_service_health():
    """获取血缘服务健康状态"""
    db = next(get_db())
    try:
        from services.openlineage_event_service import get_openlineage_event_service
        service = get_openlineage_event_service()
        health = service.health_check()
        return jsonify({"code": 0, "data": health})
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"获取血缘服务健康状态失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


# ==================== 扫描调度器 API ====================

@app.route("/api/v1/scan-scheduler/jobs", methods=["POST"])
@require_jwt()
def register_scan_job():
    """注册扫描任务"""
    db = next(get_db())
    data = request.json
    try:
        from services.scan_scheduler import get_scan_scheduler
        scheduler = get_scan_scheduler()
        database = data.get("database", "")
        schema = data.get("schema", "public")
        cron_expr = data.get("cron_expression", "0 2 * * *")
        if not database:
            return jsonify({"code": 40001, "message": "database 不能为空"}), 400
        job_id = scheduler.register_scan_job(database, schema, cron_expr)
        return jsonify({
            "code": 0,
            "message": "扫描任务已注册",
            "data": {"job_id": job_id}
        })
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"注册扫描任务失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/scan-scheduler/jobs", methods=["GET"])
@require_jwt()
def list_scan_jobs():
    """获取已注册的扫描任务"""
    db = next(get_db())
    try:
        from services.scan_scheduler import get_scan_scheduler
        scheduler = get_scan_scheduler()
        jobs = scheduler.get_registered_jobs()
        return jsonify({"code": 0, "data": jobs})
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"获取扫描任务列表失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/scan-scheduler/jobs/<job_id>", methods=["GET"])
@require_jwt()
def get_scan_job_status(job_id):
    """获取扫描任务状态"""
    db = next(get_db())
    try:
        from services.scan_scheduler import get_scan_scheduler
        scheduler = get_scan_scheduler()
        status = scheduler.get_job_status(job_id)
        if not status:
            return jsonify({"code": 40400, "message": "任务不存在"}), 404
        return jsonify({"code": 0, "data": status})
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"获取扫描任务状态失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/scan-scheduler/jobs/<job_id>/trigger", methods=["POST"])
@require_jwt()
def trigger_scan_job(job_id):
    """立即触发扫描任务"""
    db = next(get_db())
    try:
        from services.scan_scheduler import get_scan_scheduler
        scheduler = get_scan_scheduler()
        result = scheduler.trigger_scan_now(job_id)
        return jsonify({
            "code": 0,
            "message": "扫描任务已触发",
            "data": {"success": result}
        })
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"触发扫描任务失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/scan-scheduler/jobs/<job_id>", methods=["DELETE"])
@require_jwt()
def remove_scan_job(job_id):
    """删除扫描任务"""
    db = next(get_db())
    try:
        from services.scan_scheduler import get_scan_scheduler
        scheduler = get_scan_scheduler()
        result = scheduler.remove_scan_job(job_id)
        return jsonify({"code": 0, "message": "扫描任务已删除", "data": {"success": result}})
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"删除扫描任务失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


# ==================== AI 预测服务 API ====================

@app.route("/api/v1/prediction/models", methods=["GET"])
@require_jwt()
def list_prediction_models():
    """获取预测模型列表"""
    db = next(get_db())
    try:
        from services.ai_prediction_service import get_ai_prediction_service
        service = get_ai_prediction_service()
        models = service.list_models()
        return jsonify({
            "code": 0,
            "data": [m.to_dict() if hasattr(m, 'to_dict') else m for m in models]
        })
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"获取预测模型列表失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/prediction/models", methods=["POST"])
@require_jwt()
def create_prediction_model():
    """创建预测模型"""
    db = next(get_db())
    data = request.json
    try:
        from services.ai_prediction_service import get_ai_prediction_service
        service = get_ai_prediction_service()
        model = service.create_model(data)
        return jsonify({
            "code": 0,
            "message": "预测模型创建成功",
            "data": model.to_dict() if hasattr(model, 'to_dict') else model
        })
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"创建预测模型失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/prediction/models/<model_id>", methods=["GET"])
@require_jwt()
def get_prediction_model(model_id):
    """获取预测模型详情"""
    db = next(get_db())
    try:
        from services.ai_prediction_service import get_ai_prediction_service
        service = get_ai_prediction_service()
        model = service.get_model(model_id)
        if not model:
            return jsonify({"code": 40400, "message": "模型不存在"}), 404
        return jsonify({
            "code": 0,
            "data": model.to_dict() if hasattr(model, 'to_dict') else model
        })
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"获取预测模型失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/prediction/models/<model_id>/train", methods=["POST"])
@require_jwt()
def train_prediction_model(model_id):
    """训练预测模型"""
    db = next(get_db())
    data = request.json or {}
    try:
        from services.ai_prediction_service import get_ai_prediction_service
        service = get_ai_prediction_service()
        result = service.train_model(model_id, data)
        return jsonify({
            "code": 0,
            "message": "模型训练已启动",
            "data": {"success": result}
        })
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"训练预测模型失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/prediction/models/<model_id>/predict", methods=["POST"])
@require_jwt()
def run_prediction(model_id):
    """执行预测"""
    db = next(get_db())
    data = request.json
    try:
        from services.ai_prediction_service import get_ai_prediction_service
        service = get_ai_prediction_service()
        result = service.predict(model_id, data)
        return jsonify({
            "code": 0,
            "data": result.to_dict() if hasattr(result, 'to_dict') else result
        })
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"执行预测失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/prediction/models/<model_id>/deploy", methods=["POST"])
@require_jwt()
def deploy_prediction_model(model_id):
    """部署预测模型"""
    db = next(get_db())
    try:
        from services.ai_prediction_service import get_ai_prediction_service
        service = get_ai_prediction_service()
        result = service.deploy_model(model_id)
        return jsonify({
            "code": 0,
            "message": "模型部署成功",
            "data": {"success": result}
        })
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"部署预测模型失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/prediction/models/<model_id>/statistics", methods=["GET"])
@require_jwt()
def get_prediction_statistics(model_id):
    """获取预测模型统计"""
    db = next(get_db())
    try:
        from services.ai_prediction_service import get_ai_prediction_service
        service = get_ai_prediction_service()
        stats = service.get_statistics(model_id)
        return jsonify({"code": 0, "data": stats})
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"获取预测统计失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


# ==================== 采集调度器 API ====================

@app.route("/api/v1/collection/tasks", methods=["POST"])
@require_jwt()
def create_collection_task():
    """创建采集任务"""
    db = next(get_db())
    data = request.json
    try:
        from services.collection_scheduler_service import get_collection_scheduler
        scheduler = get_collection_scheduler()
        task_id = scheduler.create_task(data)
        return jsonify({
            "code": 0,
            "message": "采集任务创建成功",
            "data": {"task_id": task_id}
        })
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"创建采集任务失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/collection/tasks", methods=["GET"])
@require_jwt()
def list_collection_tasks():
    """获取采集任务列表"""
    db = next(get_db())
    try:
        from services.collection_scheduler_service import get_collection_scheduler
        scheduler = get_collection_scheduler()
        tasks = scheduler.list_tasks()
        return jsonify({
            "code": 0,
            "data": [t.to_dict() if hasattr(t, 'to_dict') else t for t in tasks]
        })
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"获取采集任务列表失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/collection/tasks/<task_id>", methods=["GET"])
@require_jwt()
def get_collection_task(task_id):
    """获取采集任务详情"""
    db = next(get_db())
    try:
        from services.collection_scheduler_service import get_collection_scheduler
        scheduler = get_collection_scheduler()
        task = scheduler.get_task(task_id)
        if not task:
            return jsonify({"code": 40400, "message": "任务不存在"}), 404
        return jsonify({
            "code": 0,
            "data": task.to_dict() if hasattr(task, 'to_dict') else task
        })
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"获取采集任务失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/collection/tasks/<task_id>", methods=["PUT"])
@require_jwt()
def update_collection_task(task_id):
    """更新采集任务"""
    db = next(get_db())
    data = request.json
    try:
        from services.collection_scheduler_service import get_collection_scheduler
        scheduler = get_collection_scheduler()
        result = scheduler.update_task(task_id, data)
        return jsonify({
            "code": 0,
            "message": "采集任务更新成功",
            "data": {"success": result}
        })
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"更新采集任务失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/collection/tasks/<task_id>", methods=["DELETE"])
@require_jwt()
def delete_collection_task(task_id):
    """删除采集任务"""
    db = next(get_db())
    try:
        from services.collection_scheduler_service import get_collection_scheduler
        scheduler = get_collection_scheduler()
        result = scheduler.delete_task(task_id)
        return jsonify({"code": 0, "message": "采集任务已删除", "data": {"success": result}})
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"删除采集任务失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/collection/tasks/<task_id>/trigger", methods=["POST"])
@require_jwt()
def trigger_collection_task(task_id):
    """立即触发采集任务"""
    db = next(get_db())
    try:
        from services.collection_scheduler_service import get_collection_scheduler
        scheduler = get_collection_scheduler()
        result = scheduler.trigger_task(task_id)
        return jsonify({
            "code": 0,
            "message": "采集任务已触发",
            "data": {"success": result}
        })
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"触发采集任务失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/collection/tasks/<task_id>/history", methods=["GET"])
@require_jwt()
def get_collection_history(task_id):
    """获取采集执行历史"""
    db = next(get_db())
    limit = request.args.get("limit", 20, type=int)
    try:
        from services.collection_scheduler_service import get_collection_scheduler
        scheduler = get_collection_scheduler()
        history = scheduler.get_execution_history(task_id, limit=limit)
        return jsonify({
            "code": 0,
            "data": [h.to_dict() if hasattr(h, 'to_dict') else h for h in history]
        })
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"获取采集执行历史失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/collection/statistics", methods=["GET"])
@require_jwt()
def get_collection_statistics():
    """获取采集统计"""
    db = next(get_db())
    try:
        from services.collection_scheduler_service import get_collection_scheduler
        scheduler = get_collection_scheduler()
        stats = scheduler.get_statistics()
        return jsonify({"code": 0, "data": stats})
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"获取采集统计失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


# ==================== IM 机器人通知 API ====================

@app.route("/api/v1/im-robots", methods=["GET"])
@require_jwt()
def list_im_robots():
    """获取 IM 机器人列表"""
    db = next(get_db())
    try:
        from services.im_robot_service import get_im_robot_service
        service = get_im_robot_service()
        robots = service.list_robots()
        return jsonify({"code": 0, "data": robots})
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"获取 IM 机器人列表失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/im-robots", methods=["POST"])
@require_jwt()
def create_im_robot():
    """创建 IM 机器人"""
    db = next(get_db())
    data = request.json
    try:
        from services.im_robot_service import get_im_robot_service
        service = get_im_robot_service()
        robot = service.create_robot(data)
        return jsonify({
            "code": 0,
            "message": "IM 机器人创建成功",
            "data": robot
        })
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"创建 IM 机器人失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/im-robots/<robot_id>", methods=["GET"])
@require_jwt()
def get_im_robot(robot_id):
    """获取 IM 机器人详情"""
    db = next(get_db())
    try:
        from services.im_robot_service import get_im_robot_service
        service = get_im_robot_service()
        robot = service.get_robot(robot_id)
        if not robot:
            return jsonify({"code": 40400, "message": "机器人不存在"}), 404
        return jsonify({"code": 0, "data": robot})
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"获取 IM 机器人失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/im-robots/<robot_id>", methods=["PUT"])
@require_jwt()
def update_im_robot(robot_id):
    """更新 IM 机器人"""
    db = next(get_db())
    data = request.json
    try:
        from services.im_robot_service import get_im_robot_service
        service = get_im_robot_service()
        result = service.update_robot(robot_id, data)
        return jsonify({
            "code": 0,
            "message": "IM 机器人更新成功",
            "data": {"success": result}
        })
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"更新 IM 机器人失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/im-robots/<robot_id>", methods=["DELETE"])
@require_jwt()
def delete_im_robot(robot_id):
    """删除 IM 机器人"""
    db = next(get_db())
    try:
        from services.im_robot_service import get_im_robot_service
        service = get_im_robot_service()
        result = service.delete_robot(robot_id)
        return jsonify({"code": 0, "message": "IM 机器人已删除", "data": {"success": result}})
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"删除 IM 机器人失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/im-robots/<robot_id>/enable", methods=["POST"])
@require_jwt()
def enable_im_robot(robot_id):
    """启用 IM 机器人"""
    db = next(get_db())
    try:
        from services.im_robot_service import get_im_robot_service
        service = get_im_robot_service()
        result = service.enable_robot(robot_id)
        return jsonify({"code": 0, "message": "机器人已启用", "data": {"success": result}})
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"启用 IM 机器人失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/im-robots/<robot_id>/disable", methods=["POST"])
@require_jwt()
def disable_im_robot(robot_id):
    """禁用 IM 机器人"""
    db = next(get_db())
    try:
        from services.im_robot_service import get_im_robot_service
        service = get_im_robot_service()
        result = service.disable_robot(robot_id)
        return jsonify({"code": 0, "message": "机器人已禁用", "data": {"success": result}})
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"禁用 IM 机器人失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/im-robots/<robot_id>/send", methods=["POST"])
@require_jwt()
def send_im_notification(robot_id):
    """通过 IM 机器人发送通知"""
    db = next(get_db())
    data = request.json
    try:
        from services.im_robot_service import get_im_robot_service
        service = get_im_robot_service()
        result = service.send_notification(robot_id, data)
        return jsonify({
            "code": 0,
            "message": "通知已发送",
            "data": {"success": result}
        })
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"发送 IM 通知失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/im-robots/broadcast", methods=["POST"])
@require_jwt()
def broadcast_im_notification():
    """广播通知到所有 IM 机器人"""
    db = next(get_db())
    data = request.json
    try:
        from services.im_robot_service import get_im_robot_service
        service = get_im_robot_service()
        result = service.send_to_all(data)
        return jsonify({
            "code": 0,
            "message": "广播通知已发送",
            "data": {"success": result}
        })
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"广播通知失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/im-robots/<robot_id>/records", methods=["GET"])
@require_jwt()
def get_im_records(robot_id):
    """获取 IM 发送记录"""
    db = next(get_db())
    limit = request.args.get("limit", 50, type=int)
    try:
        from services.im_robot_service import get_im_robot_service
        service = get_im_robot_service()
        records = service.get_records(robot_id, limit=limit)
        return jsonify({
            "code": 0,
            "data": [r.to_dict() if hasattr(r, 'to_dict') else r for r in records]
        })
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"获取 IM 发送记录失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/im-robots/statistics", methods=["GET"])
@require_jwt()
def get_im_statistics():
    """获取 IM 机器人统计"""
    db = next(get_db())
    try:
        from services.im_robot_service import get_im_robot_service
        service = get_im_robot_service()
        stats = service.get_statistics()
        return jsonify({"code": 0, "data": stats})
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"获取 IM 统计失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/im-robots/callback", methods=["POST"])
def handle_im_callback():
    """处理 IM 平台回调"""
    data = request.json or {}
    try:
        from services.im_robot_service import get_im_robot_service
        service = get_im_robot_service()
        result = service.handle_callback(data)
        return jsonify({"code": 0, "data": result})
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"处理 IM 回调失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


# ==================== Kettle 编排 API ====================

@app.route("/api/v1/kettle/orchestrate", methods=["POST"])
@require_jwt()
def kettle_orchestrate():
    """执行 Kettle 编排"""
    db = next(get_db())
    data = request.json
    try:
        from services.kettle_orchestration_service import get_kettle_orchestration_service
        service = get_kettle_orchestration_service()
        result = service.orchestrate(data)
        return jsonify({
            "code": 0,
            "message": "编排任务已提交",
            "data": result.to_dict() if hasattr(result, 'to_dict') else result
        })
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Kettle 编排失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/kettle/tasks", methods=["GET"])
@require_jwt()
def list_kettle_tasks():
    """获取 Kettle 编排任务列表"""
    db = next(get_db())
    try:
        from services.kettle_orchestration_service import get_kettle_orchestration_service
        service = get_kettle_orchestration_service()
        tasks = service.list_tasks()
        return jsonify({
            "code": 0,
            "data": [t.to_dict() if hasattr(t, 'to_dict') else t for t in tasks]
        })
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"获取 Kettle 任务列表失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/kettle/tasks/<task_id>", methods=["GET"])
@require_jwt()
def get_kettle_task(task_id):
    """获取 Kettle 任务详情"""
    db = next(get_db())
    try:
        from services.kettle_orchestration_service import get_kettle_orchestration_service
        service = get_kettle_orchestration_service()
        task = service.get_task(task_id)
        if not task:
            return jsonify({"code": 40400, "message": "任务不存在"}), 404
        return jsonify({
            "code": 0,
            "data": task.to_dict() if hasattr(task, 'to_dict') else task
        })
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"获取 Kettle 任务失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/kettle/tasks/<task_id>/xml", methods=["GET"])
@require_jwt()
def get_kettle_xml(task_id):
    """获取 Kettle 转换 XML"""
    db = next(get_db())
    try:
        from services.kettle_orchestration_service import get_kettle_orchestration_service
        service = get_kettle_orchestration_service()
        xml = service.get_transformation_xml(task_id)
        if not xml:
            return jsonify({"code": 40400, "message": "XML 不存在"}), 404
        return jsonify({"code": 0, "data": {"xml": xml}})
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"获取 Kettle XML 失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/kettle/quality-reports", methods=["GET"])
@require_jwt()
def list_kettle_quality_reports():
    """获取 Kettle 数据质量报告列表"""
    db = next(get_db())
    try:
        from services.kettle_orchestration_service import get_kettle_orchestration_service
        service = get_kettle_orchestration_service()
        reports = service.list_quality_reports()
        return jsonify({
            "code": 0,
            "data": [r.to_dict() if hasattr(r, 'to_dict') else r for r in reports]
        })
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"获取质量报告列表失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/kettle/tasks/<task_id>/quality-report", methods=["GET"])
@require_jwt()
def get_kettle_quality_report(task_id):
    """获取 Kettle 任务的质量报告"""
    db = next(get_db())
    try:
        from services.kettle_orchestration_service import get_kettle_orchestration_service
        service = get_kettle_orchestration_service()
        report = service.get_quality_report(task_id)
        if not report:
            return jsonify({"code": 40400, "message": "报告不存在"}), 404
        return jsonify({
            "code": 0,
            "data": report.to_dict() if hasattr(report, 'to_dict') else report
        })
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"获取质量报告失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


# ==================== 统一认证 API ====================

@app.route("/api/v1/auth/clients", methods=["GET"])
@require_jwt()
def list_auth_clients():
    """获取认证客户端列表"""
    db = next(get_db())
    try:
        from services.unified_auth_service import get_unified_auth_service
        service = get_unified_auth_service()
        clients = service.list_clients(db_session=db)
        return jsonify({"code": 0, "data": clients})
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"获取认证客户端列表失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/auth/clients", methods=["POST"])
@require_jwt()
def register_auth_client():
    """注册认证客户端"""
    db = next(get_db())
    data = request.json
    try:
        from services.unified_auth_service import get_unified_auth_service
        service = get_unified_auth_service()
        result = service.register_client(data, db_session=db)
        return jsonify({
            "code": 0,
            "message": "客户端注册成功",
            "data": result
        })
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"注册认证客户端失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/auth/api-keys", methods=["POST"])
@require_jwt()
def create_api_key():
    """创建 API Key"""
    db = next(get_db())
    data = request.json
    try:
        from services.unified_auth_service import get_unified_auth_service
        service = get_unified_auth_service()
        user_id = data.get("user_id", "")
        api_key = service.create_api_key(user_id, data, db_session=db)
        return jsonify({
            "code": 0,
            "message": "API Key 创建成功",
            "data": {"api_key": api_key}
        })
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"创建 API Key 失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/auth/api-keys", methods=["GET"])
@require_jwt()
def list_api_keys_auth():
    """获取 API Key 列表"""
    db = next(get_db())
    user_id = request.args.get("user_id", "")
    try:
        from services.unified_auth_service import get_unified_auth_service
        service = get_unified_auth_service()
        keys = service.list_api_keys(user_id, db_session=db)
        return jsonify({"code": 0, "data": keys})
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"获取 API Key 列表失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/auth/api-keys/validate", methods=["POST"])
def validate_api_key():
    """验证 API Key"""
    data = request.json
    try:
        from services.unified_auth_service import get_unified_auth_service
        service = get_unified_auth_service()
        api_key = data.get("api_key", "")
        result = service.validate_api_key(api_key)
        if not result:
            return jsonify({"code": 40100, "message": "API Key 无效"}), 401
        return jsonify({"code": 0, "data": result})
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"验证 API Key 失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500


@app.route("/api/v1/auth/api-keys/revoke", methods=["POST"])
@require_jwt()
def revoke_api_key():
    """撤销 API Key"""
    db = next(get_db())
    data = request.json
    try:
        from services.unified_auth_service import get_unified_auth_service
        service = get_unified_auth_service()
        api_key = data.get("api_key", "")
        result = service.revoke_api_key(api_key, db_session=db)
        return jsonify({
            "code": 0,
            "message": "API Key 已撤销",
            "data": {"success": result}
        })
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"撤销 API Key 失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/auth/statistics", methods=["GET"])
@require_jwt()
def get_auth_statistics():
    """获取认证统计"""
    db = next(get_db())
    try:
        from services.unified_auth_service import get_unified_auth_service
        service = get_unified_auth_service()
        stats = service.get_auth_statistics(db_session=db)
        return jsonify({"code": 0, "data": stats})
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"获取认证统计失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/auth/audit-logs", methods=["GET"])
@require_jwt()
def get_auth_audit_logs():
    """获取认证审计日志"""
    db = next(get_db())
    limit = request.args.get("limit", 100, type=int)
    try:
        from services.unified_auth_service import get_unified_auth_service
        service = get_unified_auth_service()
        logs = service.get_auth_audit_logs(limit=limit, db_session=db)
        return jsonify({"code": 0, "data": logs})
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"获取认证审计日志失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/auth/sessions", methods=["GET"])
@require_jwt()
def get_active_sessions():
    """获取活跃会话"""
    db = next(get_db())
    try:
        from services.unified_auth_service import get_unified_auth_service
        service = get_unified_auth_service()
        sessions = service.get_active_sessions(db_session=db)
        return jsonify({"code": 0, "data": sessions})
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"获取活跃会话失败: {e}")
        return jsonify({"code": 50000, "message": str(e)}), 500
    finally:
        db.close()


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
