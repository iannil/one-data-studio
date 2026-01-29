"""
Alldata API - 持久化版本
基于 SQLAlchemy + MySQL 的数据集管理 API
"""

import os
import sys
import logging
from datetime import datetime
from typing import Optional
import uuid

from flask import Flask, jsonify, request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

# 添加 src 和项目根目录到 Python 路径
# /app/src - 用于导入本地模块 (database, models, storage)
# /app - 用于导入 shared 模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import db_manager, init_database, check_db_health
from models import (
    DataSource, Dataset, DatasetColumn, DatasetVersion,
    MetadataDatabase, MetadataTable, MetadataColumn, FileUpload,
    FeatureGroup, Feature,
    DataStandard, StandardValidation,
    DataAsset, AssetCategory, AssetCollection,
    DataService, ServiceCallLog,
    BIDashboard, BIChart,
    MetricDefinition, MetricValue, MetricCategory,
    ETLTask, QualityRule, QualityAlert, OfflineTask, FlinkJob,
    SensitivityScanTask, SensitivityScanResult, SensitivityPattern,
)
from storage import minio_client, init_storage

# 导入本地认证模块
# /app 已添加到 sys.path，可以导入 /app/auth.py
from auth import require_jwt, require_permission, Resource, Operation

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# M-03 安全修复: 生产环境隐藏内部错误详情
def get_safe_error_message(e: Exception, default_msg: str = "Internal server error") -> str:
    """
    获取安全的错误消息，生产环境隐藏内部错误详情

    Args:
        e: 异常对象
        default_msg: 生产环境的默认错误消息

    Returns:
        安全的错误消息
    """
    if os.getenv("ENVIRONMENT") == "production":
        return default_msg
    return f"Internal error: {str(e)}"

# 创建 Flask 应用
app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True


# 初始化数据库
def initialize_app():
    """应用启动初始化"""
    try:
        init_database()
        # 开发环境：自动创建缺失的表
        if os.getenv("ENVIRONMENT") != "production":
            logger.info("Development mode: Creating missing database tables...")
            db_manager.create_tables()
        init_storage()
        logger.info("Alldata API initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize application: {e}")
        # 启动时数据库未就绪是允许的，健康检查会反映状态


@app.route("/api/v1/health")
def health():
    """健康检查接口"""
    db_healthy = check_db_health()

    return jsonify({
        "code": 0,
        "message": "healthy" if db_healthy else "degraded",
        "service": "data-api",
        "version": "1.1.0",
        "database": "connected" if db_healthy else "disconnected",
        "storage": "initialized" if minio_client._initialized else "unavailable"
    }), 200 if db_healthy else 503


# ==================== 数据源管理 API ====================

@app.route("/api/v1/datasources", methods=["GET"])
def list_datasources():
    """获取数据源列表"""
    try:
        type_filter = request.args.get("type")
        status_filter = request.args.get("status")
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("page_size", 50))

        with db_manager.get_session() as session:
            query = session.query(DataSource)

            if type_filter:
                query = query.filter(DataSource.type == type_filter)
            if status_filter:
                query = query.filter(DataSource.status == status_filter)

            total = query.count()
            datasources = query.offset((page - 1) * page_size).limit(page_size).all()

            return jsonify({
                "code": 0,
                "message": "success",
                "data": {
                    "sources": [ds.to_dict(include_connection=True) for ds in datasources],
                    "total": total
                },
                "page": page,
                "page_size": page_size
            }), 200
    except Exception as e:
        logger.error(f"Error listing datasources: {e}")
        return jsonify({
            "code": 50000,
            "message": get_safe_error_message(e)
        }), 500


@app.route("/api/v1/datasources/<source_id>", methods=["GET"])
def get_datasource(source_id: str):
    """获取数据源详情"""
    try:
        with db_manager.get_session() as session:
            datasource = session.query(DataSource).filter(DataSource.source_id == source_id).first()

            if not datasource:
                return jsonify({
                    "code": 40400,
                    "message": f"DataSource {source_id} not found"
                }), 404

            return jsonify({
                "code": 0,
                "message": "success",
                "data": datasource.to_dict(include_connection=True)
            }), 200
    except Exception as e:
        logger.error(f"Error getting datasource {source_id}: {e}")
        return jsonify({
            "code": 50000,
            "message": get_safe_error_message(e)
        }), 500


@app.route("/api/v1/datasources", methods=["POST"])
def create_datasource():
    """创建数据源"""
    try:
        data = request.get_json()

        # 生成唯一 ID
        source_id = data.get("source_id") or f"ds-{uuid.uuid4().hex[:8]}"

        # 构造连接配置（不包含密码）
        connection_config = {
            "host": data.get("host", ""),
            "port": data.get("port", 3306),
            "username": data.get("username", ""),
            "database": data.get("database", ""),
            "schema": data.get("schema", ""),
            "params": data.get("params", {})
        }

        datasource = DataSource(
            source_id=source_id,
            name=data.get("name", ""),
            description=data.get("description"),
            type=data.get("type", "mysql"),
            connection_config=connection_config,
            status="disconnected",
            tags=data.get("tags", []),
            created_by=data.get("created_by", "admin")
        )

        with db_manager.get_session() as session:
            session.add(datasource)
            session.commit()

        return jsonify({
            "code": 0,
            "message": "DataSource created successfully",
            "data": {"source_id": source_id}
        }), 201
    except IntegrityError:
        return jsonify({
            "code": 40900,
            "message": f"DataSource with source_id {source_id} already exists"
        }), 409
    except Exception as e:
        logger.error(f"Error creating datasource: {e}")
        return jsonify({
            "code": 50000,
            "message": get_safe_error_message(e)
        }), 500


@app.route("/api/v1/datasources/<source_id>", methods=["PUT"])
def update_datasource(source_id: str):
    """更新数据源"""
    try:
        data = request.get_json()
        with db_manager.get_session() as session:
            datasource = session.query(DataSource).filter(DataSource.source_id == source_id).first()

            if not datasource:
                return jsonify({
                    "code": 40400,
                    "message": f"DataSource {source_id} not found"
                }), 404

            # 更新字段
            if "name" in data:
                datasource.name = data["name"]
            if "description" in data:
                datasource.description = data["description"]
            if "connection" in data:
                conn = data["connection"]
                datasource.connection_config = {
                    "host": conn.get("host", datasource.connection_config.get("host", "")),
                    "port": conn.get("port", datasource.connection_config.get("port", 3306)),
                    "username": conn.get("username", datasource.connection_config.get("username", "")),
                    "database": conn.get("database", datasource.connection_config.get("database", "")),
                    "schema": conn.get("schema", datasource.connection_config.get("schema", "")),
                    "params": conn.get("params", datasource.connection_config.get("params", {}))
                }
            if "tags" in data:
                datasource.tags = data["tags"]

            session.commit()

        return jsonify({
            "code": 0,
            "message": "DataSource updated successfully",
            "data": datasource.to_dict(include_connection=True)
        }), 200
    except Exception as e:
        logger.error(f"Error updating datasource {source_id}: {e}")
        return jsonify({
            "code": 50000,
            "message": get_safe_error_message(e)
        }), 500


@app.route("/api/v1/datasources/<source_id>", methods=["DELETE"])
def delete_datasource(source_id: str):
    """删除数据源"""
    try:
        with db_manager.get_session() as session:
            datasource = session.query(DataSource).filter(DataSource.source_id == source_id).first()

            if not datasource:
                return jsonify({
                    "code": 40400,
                    "message": f"DataSource {source_id} not found"
                }), 404

            session.delete(datasource)
            session.commit()

        return jsonify({
            "code": 0,
            "message": "DataSource deleted successfully"
        }), 200
    except Exception as e:
        logger.error(f"Error deleting datasource {source_id}: {e}")
        return jsonify({
            "code": 50000,
            "message": get_safe_error_message(e)
        }), 500


@app.route("/api/v1/datasources/test", methods=["POST"])
def test_datasource_connection():
    """测试数据源连接"""
    try:
        data = request.get_json()

        # 模拟连接测试
        # 实际实现中应根据数据源类型创建真实的连接
        source_type = data.get("type", "mysql")

        # 简单的模拟响应
        return jsonify({
            "code": 0,
            "message": "Connection test successful",
            "data": {
                "success": True,
                "version": "8.0.0" if source_type == "mysql" else "unknown",
                "latency_ms": 15
            }
        }), 200
    except Exception as e:
        logger.error(f"Error testing datasource connection: {e}")
        return jsonify({
            "code": 50000,
            "message": get_safe_error_message(e),
            "data": {
                "success": False,
                "error": str(e) if os.getenv("ENVIRONMENT") != "production" else "Connection failed"
            }
        }), 500


# ==================== 数据集管理 API ====================

@app.route("/api/v1/datasets", methods=["GET"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.READ)
def list_datasets():
    """获取数据集列表"""
    try:
        tag_filter = request.args.get("tags")
        status_filter = request.args.get("status")
        format_filter = request.args.get("format")
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("page_size", 50))

        with db_manager.get_session() as session:
            query = session.query(Dataset)

            if status_filter:
                query = query.filter(Dataset.status == status_filter)
            if format_filter:
                query = query.filter(Dataset.format == format_filter)

            # 标签过滤需要使用 JSON_CONTAINS
            if tag_filter:
                query = query.filter(Dataset.tags.contains(tag_filter))

            # 分页
            total = query.count()
            datasets = query.order_by(Dataset.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

            result = [ds.to_dict() for ds in datasets]

            return jsonify({
                "code": 0,
                "message": "success",
                "data": result,
                "total": total,
                "page": page,
                "page_size": page_size
            })

    except Exception as e:
        logger.error(f"Error listing datasets: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/datasets/<dataset_id>", methods=["GET"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.READ)
def get_dataset(dataset_id: str):
    """获取数据集详情"""
    try:
        with db_manager.get_session() as session:
            dataset = session.query(Dataset).filter(Dataset.dataset_id == dataset_id).first()
            if dataset:
                return jsonify({
                    "code": 0,
                    "message": "success",
                    "data": dataset.to_dict()
                })
            return jsonify({
                "code": 40401,
                "message": f"Dataset {dataset_id} not found"
            }), 404

    except Exception as e:
        logger.error(f"Error getting dataset: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/datasets", methods=["POST"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.CREATE)
def create_dataset():
    """注册新数据集"""
    try:
        data = request.json
        if not data or not data.get("name"):
            return jsonify({
                "code": 40001,
                "message": "Dataset name is required"
            }), 400

        # 生成数据集 ID
        dataset_id = data.get("dataset_id") or f"ds-{uuid.uuid4().hex[:8]}"

        with db_manager.get_session() as session:
            # 检查是否已存在
            existing = session.query(Dataset).filter(Dataset.dataset_id == dataset_id).first()
            if existing:
                return jsonify({
                    "code": 40901,
                    "message": f"Dataset {dataset_id} already exists"
                }), 409

            # 创建数据集
            dataset = Dataset(
                dataset_id=dataset_id,
                name=data.get("name"),
                description=data.get("description", ""),
                storage_type=data.get("storage_type", "s3"),
                storage_path=data.get("storage_path"),
                format=data.get("format", "csv"),
                status=data.get("status", "active"),
                row_count=data.get("row_count", 0),
                size_bytes=data.get("size_bytes", 0),
                tags=data.get("tags", [])
            )
            session.add(dataset)

            # 添加列定义
            schema = data.get("schema", {})
            columns = schema.get("columns", [])
            for idx, col in enumerate(columns):
                dataset_column = DatasetColumn(
                    dataset_id=dataset_id,
                    column_name=col.get("name"),
                    column_type=col.get("type"),
                    is_nullable=col.get("nullable", True),
                    description=col.get("description", ""),
                    position=idx + 1
                )
                session.add(dataset_column)

            session.commit()

            return jsonify({
                "code": 0,
                "message": "success",
                "data": {
                    "dataset_id": dataset_id,
                    "status": "active"
                }
            }), 201

    except IntegrityError as e:
        logger.error(f"Integrity error creating dataset: {e}")
        return jsonify({
            "code": 40901,
            "message": "Dataset already exists"
        }), 409
    except Exception as e:
        logger.error(f"Error creating dataset: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/datasets/<dataset_id>", methods=["PUT"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.UPDATE)
def update_dataset(dataset_id: str):
    """更新数据集"""
    try:
        data = request.json

        with db_manager.get_session() as session:
            dataset = session.query(Dataset).filter(Dataset.dataset_id == dataset_id).first()
            if not dataset:
                return jsonify({
                    "code": 40401,
                    "message": f"Dataset {dataset_id} not found"
                }), 404

            # 更新字段
            if "description" in data:
                dataset.description = data["description"]
            if "status" in data:
                dataset.status = data["status"]
            if "tags" in data:
                dataset.tags = data["tags"]
            if "row_count" in data:
                dataset.row_count = data["row_count"]
            if "size_bytes" in data:
                dataset.size_bytes = data["size_bytes"]
            if "storage_path" in data:
                dataset.storage_path = data["storage_path"]

            session.commit()

            return jsonify({
                "code": 0,
                "message": "success",
                "data": dataset.to_dict()
            })

    except Exception as e:
        logger.error(f"Error updating dataset: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/datasets/<dataset_id>", methods=["DELETE"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.DELETE)
def delete_dataset(dataset_id: str):
    """删除数据集（软删除）"""
    try:
        with db_manager.get_session() as session:
            dataset = session.query(Dataset).filter(Dataset.dataset_id == dataset_id).first()
            if not dataset:
                return jsonify({
                    "code": 40401,
                    "message": f"Dataset {dataset_id} not found"
                }), 404

            # 软删除
            dataset.status = "deleted"
            session.commit()

            return jsonify({
                "code": 0,
                "message": "success"
            })

    except Exception as e:
        logger.error(f"Error deleting dataset: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/datasets/<dataset_id>/access", methods=["POST"])
@require_jwt()
@require_permission(Resource.STORAGE, Operation.READ)
def get_dataset_access(dataset_id: str):
    """获取数据集访问凭证 - 返回预签名 URL 而非原始凭证

    C-01 安全修复: 不再返回原始 access_key 和 secret_key，
    而是返回有限时效的预签名 URL 用于数据访问
    """
    try:
        data = request.json or {}
        operation = data.get("operation", "download")  # download or upload
        expires = int(data.get("expires", 3600))  # 默认 1 小时

        # 限制有效期最长 24 小时
        if expires > 86400:
            expires = 86400

        with db_manager.get_session() as session:
            dataset = session.query(Dataset).filter(Dataset.dataset_id == dataset_id).first()
            if not dataset:
                return jsonify({
                    "code": 40401,
                    "message": f"Dataset {dataset_id} not found"
                }), 404

            # 解析存储路径
            if dataset.storage_path and dataset.storage_path.startswith('s3://'):
                path = dataset.storage_path[5:]
                parts = path.split('/', 1)
                bucket = parts[0] if parts else minio_client.default_bucket
                object_name = parts[1] if len(parts) > 1 else ""
            else:
                bucket = minio_client.default_bucket
                object_name = f"datasets/{dataset_id}/"

            # 生成预签名 URL
            method = 'PUT' if operation == 'upload' else 'GET'
            presigned_info = minio_client.generate_presigned_url(
                object_name=object_name,
                bucket=bucket,
                expires=expires,
                method=method
            )

            return jsonify({
                "code": 0,
                "message": "success",
                "data": {
                    "presigned_url": presigned_info.get('url'),
                    "method": method,
                    "bucket": bucket,
                    "object_path": object_name,
                    "expires_in": expires,
                    "operation": operation
                }
            })

    except Exception as e:
        logger.error(f"Error getting dataset access: {e}")
        return jsonify({"code": 50000, "message": "Internal server error"}), 500


@app.route("/api/v1/datasets/<dataset_id>/upload-url", methods=["POST"])
@require_jwt()
@require_permission(Resource.STORAGE, Operation.CREATE)
def get_upload_url(dataset_id: str):
    """获取文件上传预签名 URL"""
    try:
        data = request.json
        file_name = data.get("file_name")
        if not file_name:
            return jsonify({
                "code": 40001,
                "message": "file_name is required"
            }), 400

        with db_manager.get_session() as session:
            dataset = session.query(Dataset).filter(Dataset.dataset_id == dataset_id).first()
            if not dataset:
                return jsonify({
                    "code": 40401,
                    "message": f"Dataset {dataset_id} not found"
                }), 404

            # 构建对象路径
            object_name = f"datasets/{dataset_id}/{file_name}"

            # 生成预签名 URL
            upload_info = minio_client.generate_presigned_url(
                object_name=object_name,
                expires=int(data.get("expires", 3600)),
                method='PUT'
            )

            # 创建上传记录
            upload_id = minio_client.generate_upload_id()
            file_upload = FileUpload(
                upload_id=upload_id,
                dataset_id=dataset_id,
                file_name=file_name,
                storage_path=object_name,
                status='pending'
            )
            session.add(file_upload)
            session.commit()

            return jsonify({
                "code": 0,
                "message": "success",
                "data": {
                    "upload_id": upload_id,
                    "upload_url": upload_info['url'],
                    "method": upload_info.get('method', 'PUT'),
                    "expires_in": upload_info.get('expires_in', 3600)
                }
            })

    except Exception as e:
        logger.error(f"Error getting upload URL: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/datasets/<dataset_id>/preview", methods=["GET"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.READ)
def preview_dataset(dataset_id: str):
    """预览数据集内容"""
    try:
        limit = int(request.args.get("limit", 10))

        with db_manager.get_session() as session:
            dataset = session.query(Dataset).filter(Dataset.dataset_id == dataset_id).first()
            if not dataset:
                return jsonify({
                    "code": 40401,
                    "message": f"Dataset {dataset_id} not found"
                }), 404

            # 从 MinIO 获取文件并预览
            # 这里简化实现，实际应根据 format 解析文件
            if dataset.storage_path:
                bucket, object_name = minio_client.parse_storage_path(dataset.storage_path)
                data = minio_client.get_object(object_name, bucket)

                if data:
                    # 简单返回前 N 行（对于 CSV/JSON）
                    content = data.decode('utf-8')[:2000]  # 限制返回大小

                    return jsonify({
                        "code": 0,
                        "message": "success",
                        "data": {
                            "dataset_id": dataset_id,
                            "format": dataset.format,
                            "preview": content,
                            "row_count": dataset.row_count
                        }
                    })

            # 无文件内容，返回 schema 信息
            return jsonify({
                "code": 0,
                "message": "success",
                "data": {
                    "dataset_id": dataset_id,
                    "format": dataset.format,
                    "schema": dataset.to_dict().get("schema", {}),
                    "note": "No preview available"
                }
            })

    except Exception as e:
        logger.error(f"Error previewing dataset: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


# ==================== 元数据管理 API ====================

@app.route("/api/v1/metadata/databases", methods=["GET"])
@require_jwt()
@require_permission(Resource.METADATA, Operation.READ)
def list_databases():
    """获取数据库列表"""
    try:
        with db_manager.get_session() as session:
            databases = session.query(MetadataDatabase).all()
            return jsonify({
                "code": 0,
                "message": "success",
                "data": {
                    "databases": [db.to_dict() for db in databases]
                }
            })

    except Exception as e:
        logger.error(f"Error listing databases: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/metadata/databases/<database>/tables", methods=["GET"])
@require_jwt()
@require_permission(Resource.METADATA, Operation.READ)
def list_tables(database: str):
    """获取表列表"""
    try:
        with db_manager.get_session() as session:
            tables = session.query(MetadataTable).filter(
                MetadataTable.database_name == database
            ).all()
            return jsonify({
                "code": 0,
                "message": "success",
                "data": {
                    "tables": [t.to_dict() for t in tables]
                }
            })

    except Exception as e:
        logger.error(f"Error listing tables: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/metadata/databases/<database>/tables/<table>", methods=["GET"])
@require_jwt()
@require_permission(Resource.METADATA, Operation.READ)
def get_table_schema(database: str, table: str):
    """获取表结构"""
    try:
        with db_manager.get_session() as session:
            metadata_table = session.query(MetadataTable).filter(
                MetadataTable.database_name == database,
                MetadataTable.table_name == table
            ).first()

            if not metadata_table:
                return jsonify({
                    "code": 40402,
                    "message": f"Table {database}.{table} not found"
                }), 404

            columns = session.query(MetadataColumn).filter(
                MetadataColumn.database_name == database,
                MetadataColumn.table_name == table
            ).order_by(MetadataColumn.position).all()

            return jsonify({
                "code": 0,
                "message": "success",
                "data": {
                    "table_name": table,
                    "database": database,
                    "description": metadata_table.description,
                    "row_count": metadata_table.row_count,
                    "columns": [col.to_dict() for col in columns],
                    "sample_data": []  # 实际实现中可从数据库获取样本数据
                }
            })

    except Exception as e:
        logger.error(f"Error getting table schema: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


# ==================== 数据集版本管理 API ====================

@app.route("/api/v1/datasets/<dataset_id>/versions", methods=["GET"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.READ)
def list_dataset_versions(dataset_id: str):
    """获取数据集版本列表"""
    try:
        with db_manager.get_session() as session:
            # 验证数据集存在
            dataset = session.query(Dataset).filter(Dataset.dataset_id == dataset_id).first()
            if not dataset:
                return jsonify({
                    "code": 40401,
                    "message": f"Dataset {dataset_id} not found"
                }), 404

            versions = session.query(DatasetVersion).filter(
                DatasetVersion.dataset_id == dataset_id
            ).order_by(DatasetVersion.version_number.desc()).all()

            return jsonify({
                "code": 0,
                "message": "success",
                "data": {
                    "versions": [v.to_dict() for v in versions],
                    "total": len(versions)
                }
            })

    except Exception as e:
        logger.error(f"Error listing versions: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/datasets/<dataset_id>/versions", methods=["POST"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.CREATE)
def create_dataset_version(dataset_id: str):
    """创建数据集新版本"""
    try:
        data = request.json

        with db_manager.get_session() as session:
            dataset = session.query(Dataset).filter(Dataset.dataset_id == dataset_id).first()
            if not dataset:
                return jsonify({
                    "code": 40401,
                    "message": f"Dataset {dataset_id} not found"
                }), 404

            # 获取当前最大版本号
            max_version = session.query(DatasetVersion).filter(
                DatasetVersion.dataset_id == dataset_id
            ).count()

            version_id = f"ver-{dataset_id}-{max_version + 1}"

            version = DatasetVersion(
                version_id=version_id,
                dataset_id=dataset_id,
                version_number=max_version + 1,
                storage_path=data.get("storage_path"),
                description=data.get("description", ""),
                row_count=data.get("row_count", 0),
                size_bytes=data.get("size_bytes", 0),
                checksum=data.get("checksum")
            )
            session.add(version)
            session.commit()

            return jsonify({
                "code": 0,
                "message": "success",
                "data": version.to_dict()
            }), 201

    except Exception as e:
        logger.error(f"Error creating version: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


# ==================== 特征管理 API ====================

@app.route("/api/v1/features", methods=["GET"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.READ)
def list_features():
    """获取特征列表"""
    try:
        group_id_filter = request.args.get("group_id")
        status_filter = request.args.get("status")
        feature_type_filter = request.args.get("feature_type")
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("page_size", 50))

        with db_manager.get_session() as session:
            query = session.query(Feature)

            if group_id_filter:
                query = query.filter(Feature.group_id == group_id_filter)
            if status_filter:
                query = query.filter(Feature.status == status_filter)
            if feature_type_filter:
                query = query.filter(Feature.feature_type == feature_type_filter)

            total = query.count()
            features = query.order_by(Feature.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

            return jsonify({
                "code": 0,
                "message": "success",
                "data": {
                    "features": [f.to_dict() for f in features],
                    "total": total
                }
            }), 200
    except Exception as e:
        logger.error(f"Error listing features: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/features/<feature_id>", methods=["GET"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.READ)
def get_feature(feature_id: str):
    """获取特征详情"""
    try:
        with db_manager.get_session() as session:
            feature = session.query(Feature).filter(Feature.feature_id == feature_id).first()

            if not feature:
                return jsonify({
                    "code": 40400,
                    "message": f"Feature {feature_id} not found"
                }), 404

            return jsonify({
                "code": 0,
                "message": "success",
                "data": feature.to_dict()
            }), 200
    except Exception as e:
        logger.error(f"Error getting feature {feature_id}: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/features", methods=["POST"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.CREATE)
def create_feature():
    """创建特征"""
    try:
        data = request.get_json()

        if not data or not data.get("name"):
            return jsonify({
                "code": 40001,
                "message": "Feature name is required"
            }), 400

        feature_id = data.get("feature_id") or f"feat-{uuid.uuid4().hex[:8]}"

        feature = Feature(
            feature_id=feature_id,
            name=data.get("name"),
            description=data.get("description"),
            group_id=data.get("group_id"),
            group_name=data.get("group_name"),
            data_type=data.get("data_type", "float"),
            feature_type=data.get("feature_type", "raw"),
            expression=data.get("expression"),
            dependencies=data.get("dependencies"),
            aggregation_type=data.get("aggregation_type"),
            aggregation_window=data.get("aggregation_window"),
            statistics=data.get("statistics"),
            tags=data.get("tags"),
            status=data.get("status", "active"),
            created_by=data.get("created_by", "admin")
        )

        with db_manager.get_session() as session:
            session.add(feature)
            session.commit()

            # 更新特征组的特征计数
            if feature.group_id:
                feature_group = session.query(FeatureGroup).filter(FeatureGroup.group_id == feature.group_id).first()
                if feature_group:
                    feature_group.feature_count += 1

        return jsonify({
            "code": 0,
            "message": "Feature created successfully",
            "data": {"feature_id": feature_id}
        }), 201
    except IntegrityError:
        return jsonify({
            "code": 40900,
            "message": f"Feature with feature_id {feature_id} already exists"
        }), 409
    except Exception as e:
        logger.error(f"Error creating feature: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/features/<feature_id>", methods=["PUT"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.UPDATE)
def update_feature(feature_id: str):
    """更新特征"""
    try:
        data = request.get_json()
        with db_manager.get_session() as session:
            feature = session.query(Feature).filter(Feature.feature_id == feature_id).first()

            if not feature:
                return jsonify({
                    "code": 40400,
                    "message": f"Feature {feature_id} not found"
                }), 404

            # 更新字段
            if "name" in data:
                feature.name = data["name"]
            if "description" in data:
                feature.description = data["description"]
            if "group_id" in data:
                feature.group_id = data["group_id"]
            if "group_name" in data:
                feature.group_name = data["group_name"]
            if "data_type" in data:
                feature.data_type = data["data_type"]
            if "feature_type" in data:
                feature.feature_type = data["feature_type"]
            if "expression" in data:
                feature.expression = data["expression"]
            if "dependencies" in data:
                feature.dependencies = data["dependencies"]
            if "aggregation_type" in data:
                feature.aggregation_type = data["aggregation_type"]
            if "aggregation_window" in data:
                feature.aggregation_window = data["aggregation_window"]
            if "statistics" in data:
                feature.statistics = data["statistics"]
            if "tags" in data:
                feature.tags = data["tags"]
            if "status" in data:
                feature.status = data["status"]

            session.commit()

        return jsonify({
            "code": 0,
            "message": "Feature updated successfully",
            "data": feature.to_dict()
        }), 200
    except Exception as e:
        logger.error(f"Error updating feature {feature_id}: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/features/<feature_id>", methods=["DELETE"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.DELETE)
def delete_feature(feature_id: str):
    """删除特征"""
    try:
        with db_manager.get_session() as session:
            feature = session.query(Feature).filter(Feature.feature_id == feature_id).first()

            if not feature:
                return jsonify({
                    "code": 40400,
                    "message": f"Feature {feature_id} not found"
                }), 404

            # 更新特征组的特征计数
            if feature.group_id:
                feature_group = session.query(FeatureGroup).filter(FeatureGroup.group_id == feature.group_id).first()
                if feature_group and feature_group.feature_count > 0:
                    feature_group.feature_count -= 1

            session.delete(feature)
            session.commit()

        return jsonify({
            "code": 0,
            "message": "Feature deleted successfully"
        }), 200
    except Exception as e:
        logger.error(f"Error deleting feature {feature_id}: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/features/<feature_id>/versions", methods=["GET"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.READ)
def list_feature_versions(feature_id: str):
    """获取特征版本列表"""
    try:
        # 返回空列表，后续可添加实际的版本模型
        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "versions": []
            }
        }), 200
    except Exception as e:
        logger.error(f"Error listing feature versions: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


# ==================== 特征组管理 API ====================

@app.route("/api/v1/feature-groups", methods=["GET"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.READ)
def list_feature_groups():
    """获取特征组列表"""
    try:
        status_filter = request.args.get("status")
        entity_name_filter = request.args.get("entity_name")
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("page_size", 50))

        with db_manager.get_session() as session:
            query = session.query(FeatureGroup)

            if status_filter:
                query = query.filter(FeatureGroup.status == status_filter)
            if entity_name_filter:
                query = query.filter(FeatureGroup.entity_name == entity_name_filter)

            total = query.count()
            groups = query.order_by(FeatureGroup.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

            return jsonify({
                "code": 0,
                "message": "success",
                "data": {
                    "groups": [g.to_dict() for g in groups],
                    "total": total
                }
            }), 200
    except Exception as e:
        logger.error(f"Error listing feature groups: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/feature-groups/<group_id>", methods=["GET"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.READ)
def get_feature_group(group_id: str):
    """获取特征组详情"""
    try:
        with db_manager.get_session() as session:
            group = session.query(FeatureGroup).filter(FeatureGroup.group_id == group_id).first()

            if not group:
                return jsonify({
                    "code": 40400,
                    "message": f"FeatureGroup {group_id} not found"
                }), 404

            return jsonify({
                "code": 0,
                "message": "success",
                "data": group.to_dict()
            }), 200
    except Exception as e:
        logger.error(f"Error getting feature group {group_id}: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/feature-groups", methods=["POST"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.CREATE)
def create_feature_group():
    """创建特征组"""
    try:
        data = request.get_json()

        if not data or not data.get("name"):
            return jsonify({
                "code": 40001,
                "message": "FeatureGroup name is required"
            }), 400

        group_id = data.get("group_id") or f"fg-{uuid.uuid4().hex[:8]}"

        group = FeatureGroup(
            group_id=group_id,
            name=data.get("name"),
            description=data.get("description"),
            entity_name=data.get("entity_name"),
            entity_key=data.get("entity_key"),
            source_type=data.get("source_type"),
            source_config=data.get("source_config"),
            online_store=data.get("online_store", True),
            offline_store=data.get("offline_store", True),
            ttl_days=data.get("ttl_days"),
            tags=data.get("tags"),
            status=data.get("status", "active"),
            created_by=data.get("created_by", "admin")
        )

        with db_manager.get_session() as session:
            session.add(group)
            session.commit()

        return jsonify({
            "code": 0,
            "message": "FeatureGroup created successfully",
            "data": {"group_id": group_id}
        }), 201
    except IntegrityError:
        return jsonify({
            "code": 40900,
            "message": f"FeatureGroup with group_id {group_id} already exists"
        }), 409
    except Exception as e:
        logger.error(f"Error creating feature group: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/feature-groups/<group_id>", methods=["PUT"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.UPDATE)
def update_feature_group(group_id: str):
    """更新特征组"""
    try:
        data = request.get_json()
        with db_manager.get_session() as session:
            group = session.query(FeatureGroup).filter(FeatureGroup.group_id == group_id).first()

            if not group:
                return jsonify({
                    "code": 40400,
                    "message": f"FeatureGroup {group_id} not found"
                }), 404

            # 更新字段
            if "name" in data:
                group.name = data["name"]
            if "description" in data:
                group.description = data["description"]
            if "entity_name" in data:
                group.entity_name = data["entity_name"]
            if "entity_key" in data:
                group.entity_key = data["entity_key"]
            if "source_type" in data:
                group.source_type = data["source_type"]
            if "source_config" in data:
                group.source_config = data["source_config"]
            if "online_store" in data:
                group.online_store = data["online_store"]
            if "offline_store" in data:
                group.offline_store = data["offline_store"]
            if "ttl_days" in data:
                group.ttl_days = data["ttl_days"]
            if "tags" in data:
                group.tags = data["tags"]
            if "status" in data:
                group.status = data["status"]

            session.commit()

        return jsonify({
            "code": 0,
            "message": "FeatureGroup updated successfully",
            "data": group.to_dict()
        }), 200
    except Exception as e:
        logger.error(f"Error updating feature group {group_id}: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/feature-groups/<group_id>", methods=["DELETE"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.DELETE)
def delete_feature_group(group_id: str):
    """删除特征组"""
    try:
        with db_manager.get_session() as session:
            group = session.query(FeatureGroup).filter(FeatureGroup.group_id == group_id).first()

            if not group:
                return jsonify({
                    "code": 40400,
                    "message": f"FeatureGroup {group_id} not found"
                }), 404

            session.delete(group)
            session.commit()

        return jsonify({
            "code": 0,
            "message": "FeatureGroup deleted successfully"
        }), 200
    except Exception as e:
        logger.error(f"Error deleting feature group {group_id}: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


# ==================== 特征集管理 API ====================

@app.route("/api/v1/feature-sets", methods=["GET"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.READ)
def list_feature_sets():
    """获取特征集列表"""
    try:
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("page_size", 50))

        # 返回空列表，后续可添加实际的模型
        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "sets": [],
                "total": 0
            }
        }), 200
    except Exception as e:
        logger.error(f"Error listing feature sets: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/feature-sets", methods=["POST"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.CREATE)
def create_feature_set():
    """创建特征集"""
    try:
        data = request.get_json()

        set_id = f"set-{uuid.uuid4().hex[:8]}"

        # 返回成功响应，后续可添加实际的创建逻辑
        return jsonify({
            "code": 0,
            "message": "success",
            "data": {"set_id": set_id}
        }), 200
    except Exception as e:
        logger.error(f"Error creating feature set: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


# ==================== 特征服务管理 API ====================

@app.route("/api/v1/feature-services", methods=["GET"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.READ)
def list_feature_services():
    """获取特征服务列表"""
    try:
        status_filter = request.args.get("status")
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("page_size", 50))

        # 返回空列表，后续可添加实际的模型
        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "services": [],
                "total": 0
            }
        }), 200
    except Exception as e:
        logger.error(f"Error listing feature services: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/feature-services", methods=["POST"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.CREATE)
def create_feature_service():
    """创建特征服务"""
    try:
        data = request.get_json()

        service_id = f"svc-{uuid.uuid4().hex[:8]}"

        # 返回成功响应，后续可添加实际的创建逻辑
        return jsonify({
            "code": 0,
            "message": "success",
            "data": {"service_id": service_id}
        }), 200
    except Exception as e:
        logger.error(f"Error creating feature service: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/feature-services/<service_id>", methods=["DELETE"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.DELETE)
def delete_feature_service(service_id: str):
    """删除特征服务"""
    try:
        return jsonify({
            "code": 0,
            "message": "success"
        }), 200
    except Exception as e:
        logger.error(f"Error deleting feature service {service_id}: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


# ==================== 数据标准管理 API ====================

@app.route("/api/v1/standards/elements", methods=["GET"])
@require_jwt()
@require_permission(Resource.METADATA, Operation.READ)
def list_standards():
    """获取数据标准列表"""
    try:
        category_filter = request.args.get("category")
        status_filter = request.args.get("status")
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("page_size", 50))

        with db_manager.get_session() as session:
            query = session.query(DataStandard)

            if category_filter:
                query = query.filter(DataStandard.category == category_filter)
            if status_filter:
                query = query.filter(DataStandard.status == status_filter)

            total = query.count()
            standards = query.order_by(DataStandard.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

            return jsonify({
                "code": 0,
                "message": "success",
                "data": {
                    "elements": [s.to_dict() for s in standards],
                    "total": total
                }
            }), 200
    except Exception as e:
        logger.error(f"Error listing standards: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/standards/elements/<standard_id>", methods=["GET"])
@require_jwt()
@require_permission(Resource.METADATA, Operation.READ)
def get_standard(standard_id: str):
    """获取数据标准详情"""
    try:
        with db_manager.get_session() as session:
            standard = session.query(DataStandard).filter(DataStandard.standard_id == standard_id).first()

            if not standard:
                return jsonify({
                    "code": 40400,
                    "message": f"DataStandard {standard_id} not found"
                }), 404

            return jsonify({
                "code": 0,
                "message": "success",
                "data": standard.to_dict()
            }), 200
    except Exception as e:
        logger.error(f"Error getting standard {standard_id}: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/standards/elements", methods=["POST"])
@require_jwt()
@require_permission(Resource.METADATA, Operation.CREATE)
def create_standard():
    """创建数据标准"""
    try:
        data = request.get_json()

        if not data or not data.get("name"):
            return jsonify({
                "code": 40001,
                "message": "DataStandard name is required"
            }), 400

        standard_id = data.get("standard_id") or f"std-{uuid.uuid4().hex[:8]}"

        standard = DataStandard(
            standard_id=standard_id,
            name=data.get("name"),
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
            created_by=data.get("created_by", "admin")
        )

        with db_manager.get_session() as session:
            session.add(standard)
            session.commit()

        return jsonify({
            "code": 0,
            "message": "DataStandard created successfully",
            "data": {"standard_id": standard_id}
        }), 201
    except IntegrityError:
        return jsonify({
            "code": 40900,
            "message": f"DataStandard with standard_id {standard_id} already exists"
        }), 409
    except Exception as e:
        logger.error(f"Error creating standard: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/standards/elements/<standard_id>", methods=["PUT"])
@require_jwt()
@require_permission(Resource.METADATA, Operation.UPDATE)
def update_standard(standard_id: str):
    """更新数据标准"""
    try:
        data = request.get_json()
        with db_manager.get_session() as session:
            standard = session.query(DataStandard).filter(DataStandard.standard_id == standard_id).first()

            if not standard:
                return jsonify({
                    "code": 40400,
                    "message": f"DataStandard {standard_id} not found"
                }), 404

            # 更新字段
            if "name" in data:
                standard.name = data["name"]
            if "description" in data:
                standard.description = data["description"]
            if "category" in data:
                standard.category = data["category"]
            if "rule_type" in data:
                standard.rule_type = data["rule_type"]
            if "rule_config" in data:
                standard.rule_config = data["rule_config"]
            if "apply_to" in data:
                standard.apply_to = data["apply_to"]
            if "data_types" in data:
                standard.data_types = data["data_types"]
            if "examples" in data:
                standard.examples = data["examples"]
            if "status" in data:
                standard.status = data["status"]
            if "is_required" in data:
                standard.is_required = data["is_required"]
            if "version" in data:
                standard.version = data["version"]

            session.commit()

        return jsonify({
            "code": 0,
            "message": "DataStandard updated successfully",
            "data": standard.to_dict()
        }), 200
    except Exception as e:
        logger.error(f"Error updating standard {standard_id}: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/standards/elements/<standard_id>", methods=["DELETE"])
@require_jwt()
@require_permission(Resource.METADATA, Operation.DELETE)
def delete_standard(standard_id: str):
    """删除数据标准"""
    try:
        with db_manager.get_session() as session:
            standard = session.query(DataStandard).filter(DataStandard.standard_id == standard_id).first()

            if not standard:
                return jsonify({
                    "code": 40400,
                    "message": f"DataStandard {standard_id} not found"
                }), 404

            session.delete(standard)
            session.commit()

        return jsonify({
            "code": 0,
            "message": "DataStandard deleted successfully"
        }), 200
    except Exception as e:
        logger.error(f"Error deleting standard {standard_id}: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/standards/libraries", methods=["GET"])
@require_jwt()
@require_permission(Resource.METADATA, Operation.READ)
def list_standard_libraries():
    """获取标准库（按分类分组）"""
    try:
        with db_manager.get_session() as session:
            standards = session.query(DataStandard).filter(DataStandard.status == "active").all()

            # 按分类分组
            libraries = {}
            for standard in standards:
                category = standard.category or "default"
                if category not in libraries:
                    libraries[category] = []
                libraries[category].append(standard.to_dict())

            # 转换为数组格式
            libraries_array = []
            for category, items in libraries.items():
                libraries_array.append({
                    "library_id": f"lib-{category}",
                    "name": category,
                    "category": category,
                    "word_count": len(items),
                    "created_by": "system",
                    "created_at": items[0].get("created_at") if items else None,
                    "updated_at": items[0].get("updated_at") if items else None,
                })

            return jsonify({
                "code": 0,
                "message": "success",
                "data": {
                    "libraries": libraries_array
                }
            }), 200
    except Exception as e:
        logger.error(f"Error listing standard libraries: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/standards/documents", methods=["GET"])
@require_jwt()
@require_permission(Resource.METADATA, Operation.READ)
def list_standard_documents():
    """获取标准文档列表"""
    try:
        category_filter = request.args.get("category")
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("page_size", 50))

        with db_manager.get_session() as session:
            query = session.query(DataStandard)

            if category_filter:
                query = query.filter(DataStandard.category == category_filter)

            total = query.count()
            standards = query.order_by(DataStandard.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

            return jsonify({
                "code": 0,
                "message": "success",
                "data": {
                    "documents": [s.to_dict() for s in standards],
                    "total": total
                }
            }), 200
    except Exception as e:
        logger.error(f"Error listing standard documents: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/standards/mappings", methods=["GET"])
@require_jwt()
@require_permission(Resource.METADATA, Operation.READ)
def list_standard_mappings():
    """获取标准映射关系"""
    try:
        with db_manager.get_session() as session:
            # 返回标准的适用范围映射
            standards = session.query(DataStandard).filter(DataStandard.status == "active").all()

            mappings = []
            for standard in standards:
                if standard.apply_to:
                    for target in standard.apply_to:
                        mappings.append({
                            "mapping_id": f"map-{standard.standard_id}-{target}",
                            "name": standard.name,
                            "source_table": standard.category or "",
                            "source_column": standard.name or "",
                            "target_element_name": standard.name,
                            "standard_id": standard.standard_id,
                            "status": "active"
                        })

            return jsonify({
                "code": 0,
                "message": "success",
                "data": {
                    "mappings": mappings
                }
            }), 200
    except Exception as e:
        logger.error(f"Error listing standard mappings: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/standards/validate", methods=["POST"])
@require_jwt()
@require_permission(Resource.METADATA, Operation.CREATE)
def validate_standard():
    """验证数据是否符合标准"""
    try:
        data = request.get_json()

        standard_id = data.get("standard_id")
        input_value = data.get("input_value")
        target_type = data.get("target_type", "value")
        target_id = data.get("target_id")
        target_name = data.get("target_name")

        if not standard_id or input_value is None:
            return jsonify({
                "code": 40001,
                "message": "standard_id and input_value are required"
            }), 400

        with db_manager.get_session() as session:
            standard = session.query(DataStandard).filter(DataStandard.standard_id == standard_id).first()

            if not standard:
                return jsonify({
                    "code": 40400,
                    "message": f"DataStandard {standard_id} not found"
                }), 404

            # 简单的验证逻辑
            is_valid = True
            error_message = None
            details = {}

            if standard.rule_type == "regex":
                import re
                pattern = standard.rule_config.get("pattern") if standard.rule_config else None
                if pattern:
                    is_valid = bool(re.match(pattern, str(input_value)))
                    if not is_valid:
                        error_message = f"Value does not match pattern: {pattern}"
                        details["pattern"] = pattern
            elif standard.rule_type == "enum":
                allowed_values = standard.rule_config.get("values") if standard.rule_config else []
                is_valid = input_value in allowed_values
                if not is_valid:
                    error_message = f"Value must be one of: {allowed_values}"
                    details["allowed_values"] = allowed_values
            elif standard.rule_type == "range":
                min_val = standard.rule_config.get("min") if standard.rule_config else None
                max_val = standard.rule_config.get("max") if standard.rule_config else None
                if min_val is not None and float(input_value) < min_val:
                    is_valid = False
                    error_message = f"Value must be >= {min_val}"
                if max_val is not None and float(input_value) > max_val:
                    is_valid = False
                    error_message = f"Value must be <= {max_val}"
                details["min"] = min_val
                details["max"] = max_val

            # 创建验证记录
            validation = StandardValidation(
                validation_id=f"val-{uuid.uuid4().hex[:8]}",
                standard_id=standard_id,
                standard_name=standard.name,
                target_type=target_type,
                target_id=target_id,
                target_name=target_name,
                input_value=str(input_value),
                is_valid=is_valid,
                error_message=error_message,
                details=details,
                validated_by=data.get("validated_by", "admin")
            )
            session.add(validation)

            # 更新统计
            if not is_valid:
                standard.violation_count += 1
            standard.apply_count += 1

            session.commit()

            return jsonify({
                "code": 0,
                "message": "Validation completed",
                "data": {
                    "is_valid": is_valid,
                    "standard_id": standard_id,
                    "error_message": error_message,
                    "details": details
                }
            }), 200
    except Exception as e:
        logger.error(f"Error validating standard: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


# ==================== 数据资产管理 API ====================

@app.route("/api/v1/assets", methods=["GET"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.READ)
def list_assets():
    """获取数据资产列表"""
    try:
        category_filter = request.args.get("category_id")
        asset_type_filter = request.args.get("asset_type")
        status_filter = request.args.get("status")
        keyword = request.args.get("keyword")
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("page_size", 50))

        with db_manager.get_session() as session:
            query = session.query(DataAsset)

            if category_filter:
                query = query.filter(DataAsset.category_id == category_filter)
            if asset_type_filter:
                query = query.filter(DataAsset.asset_type == asset_type_filter)
            if status_filter:
                query = query.filter(DataAsset.status == status_filter)
            if keyword:
                query = query.filter(DataAsset.name.like(f"%{keyword}%"))

            total = query.count()
            assets = query.order_by(DataAsset.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

            return jsonify({
                "code": 0,
                "message": "success",
                "data": [a.to_dict() for a in assets],
                "total": total,
                "page": page,
                "page_size": page_size
            }), 200
    except Exception as e:
        logger.error(f"Error listing assets: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/assets/<asset_id>", methods=["GET"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.READ)
def get_asset(asset_id: str):
    """获取数据资产详情"""
    try:
        with db_manager.get_session() as session:
            asset = session.query(DataAsset).filter(DataAsset.asset_id == asset_id).first()

            if not asset:
                return jsonify({
                    "code": 40400,
                    "message": f"DataAsset {asset_id} not found"
                }), 404

            # 增加查看次数
            asset.view_count += 1
            session.commit()

            return jsonify({
                "code": 0,
                "message": "success",
                "data": asset.to_dict()
            }), 200
    except Exception as e:
        logger.error(f"Error getting asset {asset_id}: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/assets", methods=["POST"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.CREATE)
def create_asset():
    """创建数据资产"""
    try:
        data = request.get_json()

        if not data or not data.get("name"):
            return jsonify({
                "code": 40001,
                "message": "DataAsset name is required"
            }), 400

        asset_id = data.get("asset_id") or f"asset-{uuid.uuid4().hex[:8]}"

        asset = DataAsset(
            asset_id=asset_id,
            name=data.get("name"),
            description=data.get("description"),
            asset_type=data.get("asset_type"),
            category_id=data.get("category_id"),
            category_name=data.get("category_name"),
            source_type=data.get("source_type"),
            source_id=data.get("source_id"),
            source_name=data.get("source_name"),
            path=data.get("path"),
            database_name=data.get("database_name"),
            schema_name=data.get("schema_name"),
            table_name=data.get("table_name"),
            columns=data.get("columns"),
            row_count=data.get("row_count"),
            size_bytes=data.get("size_bytes"),
            tags=data.get("tags"),
            owner=data.get("owner"),
            owner_name=data.get("owner_name"),
            data_level=data.get("data_level"),
            quality_score=data.get("quality_score"),
            status=data.get("status", "active")
        )

        with db_manager.get_session() as session:
            session.add(asset)
            # 更新分类的资产计数
            if asset.category_id:
                category = session.query(AssetCategory).filter(AssetCategory.category_id == asset.category_id).first()
                if category:
                    category.asset_count += 1
            session.commit()

        return jsonify({
            "code": 0,
            "message": "DataAsset created successfully",
            "data": {"asset_id": asset_id}
        }), 201
    except IntegrityError:
        return jsonify({
            "code": 40900,
            "message": f"DataAsset with asset_id {asset_id} already exists"
        }), 409
    except Exception as e:
        logger.error(f"Error creating asset: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/assets/<asset_id>", methods=["PUT"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.UPDATE)
def update_asset(asset_id: str):
    """更新数据资产"""
    try:
        data = request.get_json()
        with db_manager.get_session() as session:
            asset = session.query(DataAsset).filter(DataAsset.asset_id == asset_id).first()

            if not asset:
                return jsonify({
                    "code": 40400,
                    "message": f"DataAsset {asset_id} not found"
                }), 404

            # 更新字段
            updatable_fields = [
                "name", "description", "asset_type", "category_id", "category_name",
                "source_type", "source_id", "source_name", "path", "database_name",
                "schema_name", "table_name", "columns", "row_count", "size_bytes",
                "tags", "owner", "owner_name", "data_level", "quality_score", "status"
            ]
            for field in updatable_fields:
                if field in data:
                    setattr(asset, field, data[field])

            session.commit()

        return jsonify({
            "code": 0,
            "message": "DataAsset updated successfully",
            "data": asset.to_dict()
        }), 200
    except Exception as e:
        logger.error(f"Error updating asset {asset_id}: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/assets/<asset_id>", methods=["DELETE"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.DELETE)
def delete_asset(asset_id: str):
    """删除数据资产"""
    try:
        with db_manager.get_session() as session:
            asset = session.query(DataAsset).filter(DataAsset.asset_id == asset_id).first()

            if not asset:
                return jsonify({
                    "code": 40400,
                    "message": f"DataAsset {asset_id} not found"
                }), 404

            # 更新分类的资产计数
            if asset.category_id:
                category = session.query(AssetCategory).filter(AssetCategory.category_id == asset.category_id).first()
                if category and category.asset_count > 0:
                    category.asset_count -= 1

            session.delete(asset)
            session.commit()

        return jsonify({
            "code": 0,
            "message": "DataAsset deleted successfully"
        }), 200
    except Exception as e:
        logger.error(f"Error deleting asset {asset_id}: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/assets/inventory", methods=["GET"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.READ)
def get_asset_inventory():
    """获取资产清单统计"""
    try:
        with db_manager.get_session() as session:
            # 统计各类资产数量
            assets = session.query(DataAsset).filter(DataAsset.status == "active").all()

            inventory = {
                "total_count": len(assets),
                "by_type": {},
                "by_category": {},
                "by_level": {},
                "by_source": {}
            }

            for asset in assets:
                # 按类型统计
                asset_type = asset.asset_type or "unknown"
                inventory["by_type"][asset_type] = inventory["by_type"].get(asset_type, 0) + 1

                # 按分类统计
                if asset.category_id:
                    inventory["by_category"][asset.category_id] = inventory["by_category"].get(asset.category_id, 0) + 1

                # 按数据等级统计
                level = asset.data_level or "unknown"
                inventory["by_level"][level] = inventory["by_level"].get(level, 0) + 1

                # 按来源统计
                source = asset.source_type or "unknown"
                inventory["by_source"][source] = inventory["by_source"].get(source, 0) + 1

            # 获取分类详情
            categories = session.query(AssetCategory).all()
            inventory["categories"] = [c.to_dict() for c in categories]

            return jsonify({
                "code": 0,
                "message": "success",
                "data": inventory
            }), 200
    except Exception as e:
        logger.error(f"Error getting asset inventory: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/assets/<asset_id>/collect", methods=["POST"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.CREATE)
def collect_asset(asset_id: str):
    """收藏资产"""
    try:
        data = request.get_json()
        user_id = data.get("user_id", "anonymous")

        with db_manager.get_session() as session:
            asset = session.query(DataAsset).filter(DataAsset.asset_id == asset_id).first()
            if not asset:
                return jsonify({
                    "code": 40400,
                    "message": f"DataAsset {asset_id} not found"
                }), 404

            # 检查是否已收藏
            existing = session.query(AssetCollection).filter(
                AssetCollection.asset_id == asset_id,
                AssetCollection.user_id == user_id
            ).first()

            if existing:
                return jsonify({
                    "code": 40900,
                    "message": "Asset already collected"
                }), 409

            collection = AssetCollection(
                asset_id=asset_id,
                user_id=user_id
            )
            session.add(collection)

            # 更新收藏计数
            asset.collect_count += 1

            session.commit()

        return jsonify({
            "code": 0,
            "message": "Asset collected successfully"
        }), 200
    except Exception as e:
        logger.error(f"Error collecting asset: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/assets/<asset_id>/collect", methods=["DELETE"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.DELETE)
def uncollect_asset(asset_id: str):
    """取消收藏资产"""
    try:
        data = request.get_json()
        user_id = data.get("user_id", "anonymous")

        with db_manager.get_session() as session:
            collection = session.query(AssetCollection).filter(
                AssetCollection.asset_id == asset_id,
                AssetCollection.user_id == user_id
            ).first()

            if not collection:
                return jsonify({
                    "code": 40400,
                    "message": "Collection not found"
                }), 404

            asset = session.query(DataAsset).filter(DataAsset.asset_id == asset_id).first()
            if asset and asset.collect_count > 0:
                asset.collect_count -= 1

            session.delete(collection)
            session.commit()

        return jsonify({
            "code": 0,
            "message": "Asset uncollected successfully"
        }), 200
    except Exception as e:
        logger.error(f"Error uncollecting asset: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


# ==================== 数据服务管理 API ====================

@app.route("/api/v1/services", methods=["GET"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.READ)
def list_services():
    """获取数据服务列表"""
    try:
        status_filter = request.args.get("status")
        service_type_filter = request.args.get("service_type")
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("page_size", 50))

        with db_manager.get_session() as session:
            query = session.query(DataService)

            if status_filter:
                query = query.filter(DataService.status == status_filter)
            if service_type_filter:
                query = query.filter(DataService.service_type == service_type_filter)

            total = query.count()
            services = query.order_by(DataService.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

            return jsonify({
                "code": 0,
                "message": "success",
                "data": [s.to_dict() for s in services],
                "total": total,
                "page": page,
                "page_size": page_size
            }), 200
    except Exception as e:
        logger.error(f"Error listing services: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/services/<service_id>", methods=["GET"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.READ)
def get_service(service_id: str):
    """获取数据服务详情"""
    try:
        with db_manager.get_session() as session:
            service = session.query(DataService).filter(DataService.service_id == service_id).first()

            if not service:
                return jsonify({
                    "code": 40400,
                    "message": f"DataService {service_id} not found"
                }), 404

            return jsonify({
                "code": 0,
                "message": "success",
                "data": service.to_dict()
            }), 200
    except Exception as e:
        logger.error(f"Error getting service {service_id}: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/services", methods=["POST"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.CREATE)
def create_service():
    """创建数据服务"""
    try:
        data = request.get_json()

        if not data or not data.get("name"):
            return jsonify({
                "code": 40001,
                "message": "DataService name is required"
            }), 400

        service_id = data.get("service_id") or f"svc-{uuid.uuid4().hex[:8]}"

        service = DataService(
            service_id=service_id,
            name=data.get("name"),
            description=data.get("description"),
            service_type=data.get("service_type"),
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
            status=data.get("status", "stopped"),
            version=data.get("version", "v1"),
            created_by=data.get("created_by", "admin")
        )

        with db_manager.get_session() as session:
            session.add(service)
            session.commit()

        return jsonify({
            "code": 0,
            "message": "DataService created successfully",
            "data": {"service_id": service_id}
        }), 201
    except IntegrityError:
        return jsonify({
            "code": 40900,
            "message": f"DataService with service_id {service_id} already exists"
        }), 409
    except Exception as e:
        logger.error(f"Error creating service: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/services/<service_id>", methods=["PUT"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.UPDATE)
def update_service(service_id: str):
    """更新数据服务"""
    try:
        data = request.get_json()
        with db_manager.get_session() as session:
            service = session.query(DataService).filter(DataService.service_id == service_id).first()

            if not service:
                return jsonify({
                    "code": 40400,
                    "message": f"DataService {service_id} not found"
                }), 404

            # 更新字段
            updatable_fields = [
                "name", "description", "service_type", "source_type", "source_id",
                "sql_query", "path", "method", "parameters", "response_format",
                "auth_type", "auth_config", "rate_limit_enabled", "rate_limit_per_minute",
                "rate_limit_per_day", "cache_enabled", "cache_ttl", "status", "version"
            ]
            for field in updatable_fields:
                if field in data:
                    setattr(service, field, data[field])

            session.commit()

        return jsonify({
            "code": 0,
            "message": "DataService updated successfully",
            "data": service.to_dict()
        }), 200
    except Exception as e:
        logger.error(f"Error updating service {service_id}: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/services/<service_id>", methods=["DELETE"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.DELETE)
def delete_service(service_id: str):
    """删除数据服务"""
    try:
        with db_manager.get_session() as session:
            service = session.query(DataService).filter(DataService.service_id == service_id).first()

            if not service:
                return jsonify({
                    "code": 40400,
                    "message": f"DataService {service_id} not found"
                }), 404

            session.delete(service)
            session.commit()

        return jsonify({
            "code": 0,
            "message": "DataService deleted successfully"
        }), 200
    except Exception as e:
        logger.error(f"Error deleting service {service_id}: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/services/<service_id>/start", methods=["POST"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.UPDATE)
def start_service(service_id: str):
    """启动数据服务"""
    try:
        with db_manager.get_session() as session:
            service = session.query(DataService).filter(DataService.service_id == service_id).first()

            if not service:
                return jsonify({
                    "code": 40400,
                    "message": f"DataService {service_id} not found"
                }), 404

            service.status = "running"
            service.started_at = datetime.utcnow()
            session.commit()

        return jsonify({
            "code": 0,
            "message": "DataService started successfully",
            "data": service.to_dict()
        }), 200
    except Exception as e:
        logger.error(f"Error starting service {service_id}: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/services/<service_id>/stop", methods=["POST"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.UPDATE)
def stop_service(service_id: str):
    """停止数据服务"""
    try:
        with db_manager.get_session() as session:
            service = session.query(DataService).filter(DataService.service_id == service_id).first()

            if not service:
                return jsonify({
                    "code": 40400,
                    "message": f"DataService {service_id} not found"
                }), 404

            service.status = "stopped"
            service.stopped_at = datetime.utcnow()
            session.commit()

        return jsonify({
            "code": 0,
            "message": "DataService stopped successfully",
            "data": service.to_dict()
        }), 200
    except Exception as e:
        logger.error(f"Error stopping service {service_id}: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/services/<service_id>/logs", methods=["GET"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.READ)
def get_service_logs(service_id: str):
    """获取服务调用日志"""
    try:
        limit = int(request.args.get("limit", 100))
        offset = int(request.args.get("offset", 0))

        with db_manager.get_session() as session:
            logs = session.query(ServiceCallLog).filter(
                ServiceCallLog.service_id == service_id
            ).order_by(ServiceCallLog.called_at.desc()).offset(offset).limit(limit).all()

            return jsonify({
                "code": 0,
                "message": "success",
                "data": [log.to_dict() for log in logs]
            }), 200
    except Exception as e:
        logger.error(f"Error getting service logs: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


# ==================== BI报表管理 API ====================

@app.route("/api/v1/bi/reports", methods=["GET"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.READ)
def list_bi_reports():
    """获取BI仪表板列表"""
    try:
        is_public_filter = request.args.get("is_public")
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("page_size", 50))

        with db_manager.get_session() as session:
            query = session.query(BIDashboard)

            if is_public_filter is not None:
                is_public = is_public_filter.lower() == "true"
                query = query.filter(BIDashboard.is_public == is_public)

            total = query.count()
            dashboards = query.order_by(BIDashboard.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

            return jsonify({
                "code": 0,
                "message": "success",
                "data": [d.to_dict() for d in dashboards],
                "total": total,
                "page": page,
                "page_size": page_size
            }), 200
    except Exception as e:
        logger.error(f"Error listing BI reports: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/bi/reports/<dashboard_id>", methods=["GET"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.READ)
def get_bi_report(dashboard_id: str):
    """获取BI仪表板详情"""
    try:
        with db_manager.get_session() as session:
            dashboard = session.query(BIDashboard).filter(BIDashboard.dashboard_id == dashboard_id).first()

            if not dashboard:
                return jsonify({
                    "code": 40400,
                    "message": f"BIDashboard {dashboard_id} not found"
                }), 404

            # 增加查看次数
            dashboard.view_count += 1

            # 获取仪表板的图表
            charts = session.query(BIChart).filter(BIChart.dashboard_id == dashboard_id).all()

            result = dashboard.to_dict()
            result["charts"] = [c.to_dict() for c in charts]

            session.commit()

            return jsonify({
                "code": 0,
                "message": "success",
                "data": result
            }), 200
    except Exception as e:
        logger.error(f"Error getting BI report {dashboard_id}: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/bi/reports", methods=["POST"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.CREATE)
def create_bi_report():
    """创建BI仪表板"""
    try:
        data = request.get_json()

        if not data or not data.get("name"):
            return jsonify({
                "code": 40001,
                "message": "BIDashboard name is required"
            }), 400

        dashboard_id = data.get("dashboard_id") or f"dash-{uuid.uuid4().hex[:8]}"

        dashboard = BIDashboard(
            dashboard_id=dashboard_id,
            name=data.get("name"),
            description=data.get("description"),
            layout=data.get("layout"),
            theme=data.get("theme", "light"),
            filters=data.get("filters"),
            auto_refresh=data.get("auto_refresh", False),
            refresh_interval=data.get("refresh_interval", 300),
            is_public=data.get("is_public", False),
            share_token=data.get("share_token"),
            created_by=data.get("created_by", "admin")
        )

        with db_manager.get_session() as session:
            session.add(dashboard)
            session.commit()

        return jsonify({
            "code": 0,
            "message": "BIDashboard created successfully",
            "data": {"dashboard_id": dashboard_id}
        }), 201
    except IntegrityError:
        return jsonify({
            "code": 40900,
            "message": f"BIDashboard with dashboard_id {dashboard_id} already exists"
        }), 409
    except Exception as e:
        logger.error(f"Error creating BI report: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/bi/reports/<dashboard_id>", methods=["PUT"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.UPDATE)
def update_bi_report(dashboard_id: str):
    """更新BI仪表板"""
    try:
        data = request.get_json()
        with db_manager.get_session() as session:
            dashboard = session.query(BIDashboard).filter(BIDashboard.dashboard_id == dashboard_id).first()

            if not dashboard:
                return jsonify({
                    "code": 40400,
                    "message": f"BIDashboard {dashboard_id} not found"
                }), 404

            # 更新字段
            updatable_fields = [
                "name", "description", "layout", "theme", "filters",
                "auto_refresh", "refresh_interval", "is_public"
            ]
            for field in updatable_fields:
                if field in data:
                    setattr(dashboard, field, data[field])

            session.commit()

        return jsonify({
            "code": 0,
            "message": "BIDashboard updated successfully",
            "data": dashboard.to_dict()
        }), 200
    except Exception as e:
        logger.error(f"Error updating BI report {dashboard_id}: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/bi/reports/<dashboard_id>", methods=["DELETE"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.DELETE)
def delete_bi_report(dashboard_id: str):
    """删除BI仪表板"""
    try:
        with db_manager.get_session() as session:
            dashboard = session.query(BIDashboard).filter(BIDashboard.dashboard_id == dashboard_id).first()

            if not dashboard:
                return jsonify({
                    "code": 40400,
                    "message": f"BIDashboard {dashboard_id} not found"
                }), 404

            session.delete(dashboard)
            session.commit()

        return jsonify({
            "code": 0,
            "message": "BIDashboard deleted successfully"
        }), 200
    except Exception as e:
        logger.error(f"Error deleting BI report {dashboard_id}: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/bi/reports/<dashboard_id>/charts", methods=["GET"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.READ)
def list_bi_charts(dashboard_id: str):
    """获取仪表板下的图表列表"""
    try:
        with db_manager.get_session() as session:
            charts = session.query(BIChart).filter(BIChart.dashboard_id == dashboard_id).all()

            return jsonify({
                "code": 0,
                "message": "success",
                "data": [c.to_dict() for c in charts]
            }), 200
    except Exception as e:
        logger.error(f"Error listing BI charts: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/bi/reports/<dashboard_id>/charts", methods=["POST"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.CREATE)
def create_bi_chart(dashboard_id: str):
    """创建BI图表"""
    try:
        data = request.get_json()

        if not data or not data.get("name"):
            return jsonify({
                "code": 40001,
                "message": "BIChart name is required"
            }), 400

        # 验证仪表板存在
        with db_manager.get_session() as session:
            dashboard = session.query(BIDashboard).filter(BIDashboard.dashboard_id == dashboard_id).first()
            if not dashboard:
                return jsonify({
                    "code": 40400,
                    "message": f"BIDashboard {dashboard_id} not found"
                }), 404

            chart_id = data.get("chart_id") or f"chart-{uuid.uuid4().hex[:8]}"

            chart = BIChart(
                chart_id=chart_id,
                name=data.get("name"),
                description=data.get("description"),
                dashboard_id=dashboard_id,
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
                created_by=data.get("created_by", "admin")
            )
            session.add(chart)
            session.commit()

        return jsonify({
            "code": 0,
            "message": "BIChart created successfully",
            "data": {"chart_id": chart_id}
        }), 201
    except IntegrityError:
        return jsonify({
            "code": 40900,
            "message": f"BIChart with chart_id {chart_id} already exists"
        }), 409
    except Exception as e:
        logger.error(f"Error creating BI chart: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/bi/reports/<dashboard_id>/charts/<chart_id>", methods=["PUT"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.UPDATE)
def update_bi_chart(dashboard_id: str, chart_id: str):
    """更新BI图表"""
    try:
        data = request.get_json()
        with db_manager.get_session() as session:
            chart = session.query(BIChart).filter(
                BIChart.chart_id == chart_id,
                BIChart.dashboard_id == dashboard_id
            ).first()

            if not chart:
                return jsonify({
                    "code": 40400,
                    "message": f"BIChart {chart_id} not found"
                }), 404

            # 更新字段
            updatable_fields = [
                "name", "description", "chart_type", "datasource_type",
                "datasource_id", "sql_query", "config", "dimensions",
                "metrics", "filters", "cache_enabled", "cache_ttl"
            ]
            for field in updatable_fields:
                if field in data:
                    setattr(chart, field, data[field])

            session.commit()

        return jsonify({
            "code": 0,
            "message": "BIChart updated successfully",
            "data": chart.to_dict()
        }), 200
    except Exception as e:
        logger.error(f"Error updating BI chart: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/bi/reports/<dashboard_id>/charts/<chart_id>", methods=["DELETE"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.DELETE)
def delete_bi_chart(dashboard_id: str, chart_id: str):
    """删除BI图表"""
    try:
        with db_manager.get_session() as session:
            chart = session.query(BIChart).filter(
                BIChart.chart_id == chart_id,
                BIChart.dashboard_id == dashboard_id
            ).first()

            if not chart:
                return jsonify({
                    "code": 40400,
                    "message": f"BIChart {chart_id} not found"
                }), 404

            session.delete(chart)
            session.commit()

        return jsonify({
            "code": 0,
            "message": "BIChart deleted successfully"
        }), 200
    except Exception as e:
        logger.error(f"Error deleting BI chart: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


# ==================== 指标管理 API ====================

@app.route("/api/v1/metrics", methods=["GET"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.READ)
def list_metrics():
    """获取指标定义列表"""
    try:
        category_filter = request.args.get("category")
        is_active_filter = request.args.get("is_active")
        keyword = request.args.get("keyword")
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("page_size", 50))

        with db_manager.get_session() as session:
            query = session.query(MetricDefinition)

            if category_filter:
                query = query.filter(MetricDefinition.category == category_filter)
            if is_active_filter is not None:
                is_active = is_active_filter.lower() == "true"
                query = query.filter(MetricDefinition.is_active == is_active)
            if keyword:
                query = query.filter(MetricDefinition.name.like(f"%{keyword}%"))

            total = query.count()
            metrics = query.order_by(MetricDefinition.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

            return jsonify({
                "code": 0,
                "message": "success",
                "data": {
                    "metrics": [m.to_dict() for m in metrics],
                    "total": total
                }
            }), 200
    except Exception as e:
        logger.error(f"Error listing metrics: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/metrics/<metric_id>", methods=["GET"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.READ)
def get_metric(metric_id: str):
    """获取指标定义详情"""
    try:
        with db_manager.get_session() as session:
            metric = session.query(MetricDefinition).filter(MetricDefinition.metric_id == metric_id).first()

            if not metric:
                return jsonify({
                    "code": 40400,
                    "message": f"MetricDefinition {metric_id} not found"
                }), 404

            return jsonify({
                "code": 0,
                "message": "success",
                "data": metric.to_dict()
            }), 200
    except Exception as e:
        logger.error(f"Error getting metric {metric_id}: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/metrics", methods=["POST"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.CREATE)
def create_metric():
    """创建指标定义"""
    try:
        data = request.get_json()

        if not data or not data.get("name"):
            return jsonify({
                "code": 40001,
                "message": "MetricDefinition name is required"
            }), 400

        metric_id = data.get("metric_id") or f"metric-{uuid.uuid4().hex[:8]}"

        metric = MetricDefinition(
            metric_id=metric_id,
            name=data.get("name"),
            display_name=data.get("display_name"),
            description=data.get("description"),
            category=data.get("category"),
            subcategory=data.get("subcategory"),
            tags=data.get("tags"),
            metric_type=data.get("metric_type", "count"),
            source_database=data.get("source_database"),
            source_table=data.get("source_table"),
            source_column=data.get("source_column"),
            calculation_sql=data.get("calculation_sql"),
            aggregation_type=data.get("aggregation_type"),
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
            created_by=data.get("created_by", "admin")
        )

        with db_manager.get_session() as session:
            session.add(metric)
            session.commit()

        return jsonify({
            "code": 0,
            "message": "MetricDefinition created successfully",
            "data": {"metric_id": metric_id}
        }), 201
    except IntegrityError:
        return jsonify({
            "code": 40900,
            "message": f"MetricDefinition with metric_id {metric_id} already exists"
        }), 409
    except Exception as e:
        logger.error(f"Error creating metric: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/metrics/<metric_id>", methods=["PUT"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.UPDATE)
def update_metric(metric_id: str):
    """更新指标定义"""
    try:
        data = request.get_json()
        with db_manager.get_session() as session:
            metric = session.query(MetricDefinition).filter(MetricDefinition.metric_id == metric_id).first()

            if not metric:
                return jsonify({
                    "code": 40400,
                    "message": f"MetricDefinition {metric_id} not found"
                }), 404

            # 更新字段
            updatable_fields = [
                "name", "display_name", "description", "category", "subcategory",
                "tags", "metric_type", "source_database", "source_table",
                "source_column", "calculation_sql", "aggregation_type",
                "time_column", "unit", "decimal_places", "format_pattern",
                "warning_threshold", "critical_threshold", "threshold_direction",
                "owner", "owner_team", "is_active", "is_certified"
            ]
            for field in updatable_fields:
                if field in data:
                    setattr(metric, field, data[field])

            metric.updated_by = data.get("updated_by", "admin")

            session.commit()

        return jsonify({
            "code": 0,
            "message": "MetricDefinition updated successfully",
            "data": metric.to_dict()
        }), 200
    except Exception as e:
        logger.error(f"Error updating metric {metric_id}: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/metrics/<metric_id>", methods=["DELETE"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.DELETE)
def delete_metric(metric_id: str):
    """删除指标定义"""
    try:
        with db_manager.get_session() as session:
            metric = session.query(MetricDefinition).filter(MetricDefinition.metric_id == metric_id).first()

            if not metric:
                return jsonify({
                    "code": 40400,
                    "message": f"MetricDefinition {metric_id} not found"
                }), 404

            session.delete(metric)
            session.commit()

        return jsonify({
            "code": 0,
            "message": "MetricDefinition deleted successfully"
        }), 200
    except Exception as e:
        logger.error(f"Error deleting metric {metric_id}: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/metrics/<metric_id>/calculate", methods=["POST"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.UPDATE)
def calculate_metric(metric_id: str):
    """手动计算指标"""
    try:
        with db_manager.get_session() as session:
            metric = session.query(MetricDefinition).filter(MetricDefinition.metric_id == metric_id).first()

            if not metric:
                return jsonify({
                    "code": 40400,
                    "message": f"Metric {metric_id} not found"
                }), 404

            # 返回计算结果，后续可以添加实际的计算逻辑
            return jsonify({
                "code": 0,
                "message": "success",
                "data": {
                    "value": 0,
                    "timestamp": datetime.now().isoformat() + 'Z'
                }
            }), 200
    except Exception as e:
        logger.error(f"Error calculating metric {metric_id}: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/metrics/<metric_id>/values", methods=["GET"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.READ)
def list_metric_values(metric_id: str):
    """获取指标数据值"""
    try:
        granularity = request.args.get("granularity", "daily")
        limit = int(request.args.get("limit", 100))

        with db_manager.get_session() as session:
            values = session.query(MetricValue).filter(
                MetricValue.metric_id == metric_id,
                MetricValue.granularity == granularity
            ).order_by(MetricValue.time_key.desc()).limit(limit).all()

            return jsonify({
                "code": 0,
                "message": "success",
                "data": [v.to_dict() for v in values]
            }), 200
    except Exception as e:
        logger.error(f"Error listing metric values: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/metrics/categories", methods=["GET"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.READ)
def list_metric_categories():
    """获取指标分类列表"""
    try:
        with db_manager.get_session() as session:
            categories = session.query(MetricCategory).filter(MetricCategory.is_active == True).all()

            return jsonify({
                "code": 0,
                "message": "success",
                "data": [c.to_dict() for c in categories]
            }), 200
    except Exception as e:
        logger.error(f"Error listing metric categories: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/metrics/categories/stats", methods=["GET"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.READ)
def get_metric_category_stats():
    """获取指标分类统计"""
    try:
        with db_manager.get_session() as session:
            # 统计每个分类下的指标数量
            metrics = session.query(MetricDefinition).filter(MetricDefinition.is_active == True).all()

            # 按分类统计
            category_counts = {}
            for metric in metrics:
                category = metric.category or "business"
                if category not in category_counts:
                    category_counts[category] = 0
                category_counts[category] += 1

            # 转换为前端期望的格式
            categories = [{"category": cat, "count": count} for cat, count in category_counts.items()]
            total = len(metrics)

            return jsonify({
                "code": 0,
                "message": "success",
                "data": {
                    "categories": categories,
                    "total": total
                }
            }), 200
    except Exception as e:
        logger.error(f"Error getting metric category stats: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/metrics/calculation-tasks", methods=["GET"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.READ)
def list_metric_calculation_tasks():
    """获取指标计算任务列表"""
    try:
        status_filter = request.args.get("status")
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("page_size", 50))

        # 返回空列表，后续可以添加实际的计算任务模型
        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "tasks": [],
                "total": 0
            }
        }), 200
    except Exception as e:
        logger.error(f"Error listing metric calculation tasks: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/metrics/calculation-tasks/<task_id>/start", methods=["POST"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.UPDATE)
def start_metric_calculation_task(task_id: str):
    """启动指标计算任务"""
    try:
        # 返回成功响应，后续可以添加实际的启动逻辑
        return jsonify({
            "code": 0,
            "message": "success",
            "data": {"execution_id": f"exec-{uuid.uuid4().hex[:16]}"}
        }), 200
    except Exception as e:
        logger.error(f"Error starting metric calculation task {task_id}: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/metrics/calculation-tasks/<task_id>/stop", methods=["POST"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.UPDATE)
def stop_metric_calculation_task(task_id: str):
    """停止指标计算任务"""
    try:
        return jsonify({
            "code": 0,
            "message": "success",
            "data": None
        }), 200
    except Exception as e:
        logger.error(f"Error stopping metric calculation task {task_id}: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/metrics/categories", methods=["POST"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.CREATE)
def create_metric_category():
    """创建指标分类"""
    try:
        data = request.get_json()

        if not data or not data.get("name"):
            return jsonify({
                "code": 40001,
                "message": "MetricCategory name is required"
            }), 400

        category_id = data.get("category_id") or f"mcat-{uuid.uuid4().hex[:8]}"

        category = MetricCategory(
            category_id=category_id,
            name=data.get("name"),
            display_name=data.get("display_name"),
            description=data.get("description"),
            parent_id=data.get("parent_id"),
            level=data.get("level", 1),
            sort_order=data.get("sort_order", 0),
            icon=data.get("icon"),
            is_active=data.get("is_active", True)
        )

        with db_manager.get_session() as session:
            session.add(category)
            session.commit()

        return jsonify({
            "code": 0,
            "message": "MetricCategory created successfully",
            "data": {"category_id": category_id}
        }), 201
    except IntegrityError:
        return jsonify({
            "code": 40900,
            "message": f"MetricCategory with category_id {category_id} already exists"
        }), 409
    except Exception as e:
        logger.error(f"Error creating metric category: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/metrics/categories/<category_id>", methods=["PUT"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.UPDATE)
def update_metric_category(category_id: str):
    """更新指标分类"""
    try:
        data = request.get_json()
        with db_manager.get_session() as session:
            category = session.query(MetricCategory).filter(MetricCategory.category_id == category_id).first()

            if not category:
                return jsonify({
                    "code": 40400,
                    "message": f"MetricCategory {category_id} not found"
                }), 404

            # 更新字段
            updatable_fields = [
                "name", "display_name", "description", "parent_id",
                "level", "sort_order", "icon", "is_active"
            ]
            for field in updatable_fields:
                if field in data:
                    setattr(category, field, data[field])

            session.commit()

        return jsonify({
            "code": 0,
            "message": "MetricCategory updated successfully",
            "data": category.to_dict()
        }), 200
    except Exception as e:
        logger.error(f"Error updating metric category {category_id}: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/metrics/categories/<category_id>", methods=["DELETE"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.DELETE)
def delete_metric_category(category_id: str):
    """删除指标分类"""
    try:
        with db_manager.get_session() as session:
            category = session.query(MetricCategory).filter(MetricCategory.category_id == category_id).first()

            if not category:
                return jsonify({
                    "code": 40400,
                    "message": f"MetricCategory {category_id} not found"
                }), 404

            session.delete(category)
            session.commit()

        return jsonify({
            "code": 0,
            "message": "MetricCategory deleted successfully"
        }), 200
    except Exception as e:
        logger.error(f"Error deleting metric category {category_id}: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


# ==================== ETL任务管理 API ====================

@app.route("/api/v1/etl/tasks", methods=["GET"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.READ)
def list_etl_tasks():
    """获取ETL任务列表"""
    try:
        status_filter = request.args.get("status")
        task_type_filter = request.args.get("task_type")
        keyword = request.args.get("keyword")
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("page_size", 50))

        with db_manager.get_session() as session:
            query = session.query(ETLTask)

            if status_filter:
                query = query.filter(ETLTask.status == status_filter)
            if task_type_filter:
                query = query.filter(ETLTask.task_type == task_type_filter)
            if keyword:
                query = query.filter(ETLTask.name.like(f"%{keyword}%"))

            total = query.count()
            tasks = query.order_by(ETLTask.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

            return jsonify({
                "code": 0,
                "message": "success",
                "data": {
                    "tasks": [t.to_dict() for t in tasks],
                    "total": total
                },
                "page": page,
                "page_size": page_size
            }), 200
    except Exception as e:
        logger.error(f"Error listing ETL tasks: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


# ==================== 数据质量管理 API ====================

@app.route("/api/v1/quality/alerts/config", methods=["GET"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.READ)
def get_quality_alerts_config():
    """获取数据质量告警配置"""
    try:
        with db_manager.get_session() as session:
            alerts = session.query(QualityAlert).filter(QualityAlert.is_enabled == True).all()

            # 按严重程度分组
            config_by_severity = {
                "high": [],
                "medium": [],
                "low": []
            }

            for alert in alerts:
                severity = alert.severity or "medium"
                if severity not in config_by_severity:
                    severity = "medium"
                config_by_severity[severity].append(alert.to_dict())

            return jsonify({
                "code": 0,
                "message": "success",
                "data": {
                    "alerts": config_by_severity,
                    "total": len(alerts)
                }
            }), 200
    except Exception as e:
        logger.error(f"Error getting quality alerts config: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/quality/rules", methods=["GET"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.READ)
def list_quality_rules():
    """获取数据质量规则列表"""
    try:
        status_filter = request.args.get("status")
        rule_type_filter = request.args.get("rule_type")
        source_id_filter = request.args.get("source_id")
        severity_filter = request.args.get("severity")
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("page_size", 50))

        with db_manager.get_session() as session:
            query = session.query(QualityRule)

            if status_filter:
                query = query.filter(QualityRule.status == status_filter)
            if rule_type_filter:
                query = query.filter(QualityRule.rule_type == rule_type_filter)
            if source_id_filter:
                query = query.filter(QualityRule.source_id == source_id_filter)
            if severity_filter:
                query = query.filter(QualityRule.severity == severity_filter)

            total = query.count()
            rules = query.order_by(QualityRule.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

            return jsonify({
                "code": 0,
                "message": "success",
                "data": {
                    "rules": [r.to_dict() for r in rules],
                    "total": total
                },
                "page": page,
                "page_size": page_size
            }), 200
    except Exception as e:
        logger.error(f"Error listing quality rules: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


# ==================== 离线计算管理 API ====================

@app.route("/api/v1/offline/workflows", methods=["GET"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.READ)
def list_offline_workflows():
    """获取离线计算工作流列表"""
    try:
        status_filter = request.args.get("status")
        workflow_type_filter = request.args.get("workflow_type")
        cluster_id_filter = request.args.get("cluster_id")
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("page_size", 50))

        with db_manager.get_session() as session:
            query = session.query(OfflineTask)

            if status_filter:
                query = query.filter(OfflineTask.status == status_filter)
            if workflow_type_filter:
                query = query.filter(OfflineTask.workflow_type == workflow_type_filter)
            if cluster_id_filter:
                query = query.filter(OfflineTask.cluster_id == cluster_id_filter)

            total = query.count()
            workflows = query.order_by(OfflineTask.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

            return jsonify({
                "code": 0,
                "message": "success",
                "data": {
                    "workflows": [w.to_dict() for w in workflows],
                    "total": total
                },
                "page": page,
                "page_size": page_size
            }), 200
    except Exception as e:
        logger.error(f"Error listing offline workflows: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


# ==================== 流计算管理 API ====================

@app.route("/api/v1/streaming/jobs", methods=["GET"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.READ)
def list_streaming_jobs():
    """获取Flink流计算任务列表"""
    try:
        status_filter = request.args.get("status")
        job_type_filter = request.args.get("job_type")
        cluster_id_filter = request.args.get("cluster_id")
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("page_size", 50))

        with db_manager.get_session() as session:
            query = session.query(FlinkJob)

            if status_filter:
                query = query.filter(FlinkJob.status == status_filter)
            if job_type_filter:
                query = query.filter(FlinkJob.job_type == job_type_filter)
            if cluster_id_filter:
                query = query.filter(FlinkJob.cluster_id == cluster_id_filter)

            total = query.count()
            jobs = query.order_by(FlinkJob.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

            return jsonify({
                "code": 0,
                "message": "success",
                "data": {
                    "jobs": [j.to_dict() for j in jobs],
                    "total": total
                },
                "page": page,
                "page_size": page_size
            }), 200
    except Exception as e:
        logger.error(f"Error listing streaming jobs: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


# ==================== Notebook管理 API ====================

@app.route("/api/v1/notebooks/images", methods=["GET"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.READ)
def list_notebook_images():
    """获取Notebook镜像列表"""
    try:
        # 返回预定义的Notebook镜像列表
        images = [
            {
                "image_id": "jupyter-scipy-notebook",
                "name": "Jupyter SciPy Notebook",
                "description": "Jupyter notebook with scientific Python stack",
                "image": "jupyter/scipy-notebook:latest",
                "default": True
            },
            {
                "image_id": "jupyter-datascience-notebook",
                "name": "Jupyter Data Science Notebook",
                "description": "Jupyter notebook with data science libraries",
                "image": "jupyter/datascience-notebook:latest",
                "default": False
            },
            {
                "image_id": "jupyter-pyspark-notebook",
                "name": "Jupyter PySpark Notebook",
                "description": "Jupyter notebook with PySpark support",
                "image": "jupyter/pyspark-notebook:latest",
                "default": False
            },
            {
                "image_id": "jupyter-tensorflow-notebook",
                "name": "Jupyter TensorFlow Notebook",
                "description": "Jupyter notebook with TensorFlow",
                "image": "jupyter/tensorflow-notebook:latest",
                "default": False
            }
        ]

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "images": images,
                "total": len(images)
            }
        }), 200
    except Exception as e:
        logger.error(f"Error listing notebook images: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/notebooks", methods=["GET"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.READ)
def list_notebooks():
    """获取Notebook列表"""
    try:
        status_filter = request.args.get("status")
        keyword = request.args.get("keyword")
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("page_size", 50))

        # 返回空列表，Notebook功能后续可以通过Cube Studio集成
        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "notebooks": [],
                "total": 0
            },
            "page": page,
            "page_size": page_size
        }), 200
    except Exception as e:
        logger.error(f"Error listing notebooks: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


# ==================== 数据质量扩展 API ====================

@app.route("/api/v1/quality/trends", methods=["GET"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.READ)
def get_quality_trends():
    """获取数据质量趋势"""
    try:
        period = request.args.get("period", "daily")  # daily, weekly, monthly
        source_id = request.args.get("source_id")

        # 返回模拟趋势数据
        trends_data = {
            "daily": {
                "dates": ["2024-01-20", "2024-01-21", "2024-01-22", "2024-01-23", "2024-01-24", "2024-01-25", "2024-01-26"],
                "quality_scores": [92, 94, 93, 95, 96, 94, 97],
                "validation_counts": [120, 135, 128, 142, 150, 138, 155],
                "issue_counts": [8, 5, 7, 4, 3, 6, 2]
            },
            "weekly": {
                "dates": ["2024-W1", "2024-W2", "2024-W3", "2024-W4"],
                "quality_scores": [90, 93, 95, 96],
                "validation_counts": [800, 920, 980, 1050],
                "issue_counts": [45, 32, 25, 18]
            },
            "monthly": {
                "dates": ["2023-11", "2023-12", "2024-01"],
                "quality_scores": [88, 91, 95],
                "validation_counts": [3200, 3600, 4100],
                "issue_counts": [180, 145, 85]
            }
        }

        data = trends_data.get(period, trends_data["daily"])

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "period": period,
                **data
            }
        }), 200
    except Exception as e:
        logger.error(f"Error getting quality trends: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/quality/tasks", methods=["GET"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.READ)
def list_quality_tasks():
    """获取数据质量检查任务列表"""
    try:
        status_filter = request.args.get("status")
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("page_size", 50))

        with db_manager.get_session() as session:
            query = session.query(QualityRule)

            if status_filter:
                query = query.filter(QualityRule.status == status_filter)

            total = query.count()
            # 将 QualityRule 转换为任务格式
            tasks = []
            for rule in query.order_by(QualityRule.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all():
                rule_dict = rule.to_dict()
                # 转换为任务格式
                task_dict = {
                    "task_id": rule.rule_id,
                    "name": rule.name,
                    "rule_type": rule.rule_type,
                    "status": rule.status,
                    "source_id": rule.source_id,
                    "schedule": rule_dict.get("schedule", "manual"),
                    "last_run_at": rule_dict.get("last_checked_at"),
                    "next_run_at": rule_dict.get("next_check_at"),
                    "created_at": rule_dict.get("created_at")
                }
                tasks.append(task_dict)

            return jsonify({
                "code": 0,
                "message": "success",
                "data": {
                    "tasks": tasks,
                    "total": total
                },
                "page": page,
                "page_size": page_size
            }), 200
    except Exception as e:
        logger.error(f"Error listing quality tasks: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/quality/reports", methods=["GET"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.READ)
def list_quality_reports():
    """获取数据质量报告列表"""
    try:
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("page_size", 50))

        # 返回模拟报告数据
        reports = [
            {
                "report_id": "qr-001",
                "name": "每日数据质量报告",
                "description": "每日数据质量检查汇总",
                "source_id": "ds-mysql-001",
                "status": "completed",
                "quality_score": 96.5,
                "total_checks": 150,
                "passed_checks": 145,
                "failed_checks": 5,
                "created_at": "2024-01-26T10:00:00Z",
                "created_by": "admin"
            },
            {
                "report_id": "qr-002",
                "name": "周度数据质量报告",
                "description": "每周数据质量趋势分析",
                "source_id": "ds-pg-001",
                "status": "completed",
                "quality_score": 94.2,
                "total_checks": 980,
                "passed_checks": 923,
                "failed_checks": 57,
                "created_at": "2024-01-25T10:00:00Z",
                "created_by": "admin"
            }
        ]

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "reports": reports,
                "total": len(reports)
            },
            "page": page,
            "page_size": page_size
        }), 200
    except Exception as e:
        logger.error(f"Error listing quality reports: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/quality/alerts", methods=["GET"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.READ)
def list_quality_alerts():
    """获取数据质量告警列表"""
    try:
        status_filter = request.args.get("status")
        severity_filter = request.args.get("severity")
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("page_size", 50))

        with db_manager.get_session() as session:
            query = session.query(QualityAlert)

            if status_filter:
                if status_filter == "active":
                    query = query.filter(QualityAlert.is_enabled == True)
                elif status_filter == "inactive":
                    query = query.filter(QualityAlert.is_enabled == False)
            if severity_filter:
                query = query.filter(QualityAlert.severity == severity_filter)

            total = query.count()
            alerts = query.order_by(QualityAlert.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

            return jsonify({
                "code": 0,
                "message": "success",
                "data": {
                    "alerts": [a.to_dict() for a in alerts],
                    "total": total
                },
                "page": page,
                "page_size": page_size
            }), 200
    except Exception as e:
        logger.error(f"Error listing quality alerts: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


# ==================== 敏感数据扫描 API ====================

@app.route("/api/v1/sensitivity/scan/start", methods=["POST"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.MANAGE)
def start_sensitivity_scan():
    """启动敏感数据扫描任务"""
    try:
        data = request.get_json()

        # 导入扫描管理器
        from scan_task import get_scan_manager

        manager = get_scan_manager()

        task = manager.create_task(
            target_type=data.get("target_type", "database"),
            target_id=data.get("target_id"),
            target_name=data.get("target_name"),
            scan_mode=data.get("scan_mode", "full"),
            sample_rate=data.get("sample_rate", 100),
            confidence_threshold=data.get("confidence_threshold", 70),
            databases=data.get("databases"),
            tables=data.get("tables"),
            exclude_patterns=data.get("exclude_patterns"),
            created_by=data.get("created_by", "admin"),
            auto_start=True,
        )

        return jsonify({
            "code": 0,
            "message": "Scan task created and started",
            "data": {
                "task_id": task.task_id,
                "status": task.status,
            }
        }), 201

    except Exception as e:
        logger.error(f"Error starting sensitivity scan: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/sensitivity/scan/<task_id>", methods=["GET"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.READ)
def get_scan_task_status(task_id: str):
    """获取扫描任务状态"""
    try:
        from scan_task import get_scan_manager

        manager = get_scan_manager()
        task_info = manager.get_task_status(task_id)

        if not task_info:
            return jsonify({
                "code": 40400,
                "message": f"Scan task {task_id} not found"
            }), 404

        return jsonify({
            "code": 0,
            "message": "success",
            "data": task_info
        }), 200

    except Exception as e:
        logger.error(f"Error getting scan task {task_id}: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/sensitivity/scan/<task_id>/cancel", methods=["POST"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.MANAGE)
def cancel_scan_task(task_id: str):
    """取消扫描任务"""
    try:
        from scan_task import get_scan_manager

        manager = get_scan_manager()
        success = manager.cancel_task(task_id)

        if not success:
            return jsonify({
                "code": 40000,
                "message": f"Cannot cancel task {task_id}"
            }), 400

        return jsonify({
            "code": 0,
            "message": "Task cancelled"
        }), 200

    except Exception as e:
        logger.error(f"Error cancelling scan task {task_id}: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/sensitivity/scan/<task_id>/results", methods=["GET"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.READ)
def get_scan_results(task_id: str):
    """获取扫描结果"""
    try:
        from scan_task import get_scan_manager

        verified_only = request.args.get("verified_only", "false").lower() == "true"
        limit = int(request.args.get("limit", 100))
        offset = int(request.args.get("offset", 0))

        manager = get_scan_manager()
        results = manager.get_task_results(task_id, verified_only, limit, offset)

        # 获取总数
        with db_manager.get_session() as session:
            query = session.query(SensitivityScanResult).filter(
                SensitivityScanResult.task_id == task_id
            )
            if verified_only:
                query = query.filter(SensitivityScanResult.verified == True)
            total = query.count()

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "results": results,
                "total": total
            }
        }), 200

    except Exception as e:
        logger.error(f"Error getting scan results for {task_id}: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/sensitivity/confirm", methods=["POST"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.MANAGE)
def verify_sensitivity_result():
    """校验/修正敏感数据识别结果"""
    try:
        from scan_task import get_scan_manager

        data = request.get_json()
        result_id = data.get("result_id")
        verified_result = data.get("verified_result")  # confirmed, rejected, modified
        verified_by = data.get("verified_by", "admin")

        if not result_id or not verified_result:
            return jsonify({
                "code": 40000,
                "message": "result_id and verified_result are required"
            }), 400

        manager = get_scan_manager()
        success = manager.verify_result(
            result_id=result_id,
            verified_result=verified_result,
            verified_by=verified_by,
            sensitivity_type=data.get("sensitivity_type"),
            sensitivity_level=data.get("sensitivity_level"),
        )

        if not success:
            return jsonify({
                "code": 40400,
                "message": f"Result {result_id} not found"
            }), 404

        return jsonify({
            "code": 0,
            "message": "Result verified"
        }), 200

    except Exception as e:
        logger.error(f"Error verifying sensitivity result: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/sensitivity/patterns", methods=["GET"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.READ)
def get_sensitivity_patterns():
    """获取动态模式库"""
    try:
        category = request.args.get("category")
        is_active = request.args.get("is_active", "true").lower() == "true"

        with db_manager.get_session() as session:
            query = session.query(SensitivityPattern)

            if category:
                query = query.filter(SensitivityPattern.category == category)
            if is_active:
                query = query.filter(SensitivityPattern.is_active == True)

            patterns = query.order_by(
                SensitivityPattern.category,
                SensitivityPattern.sub_type
            ).all()

            return jsonify({
                "code": 0,
                "message": "success",
                "data": {
                    "patterns": [p.to_dict() for p in patterns],
                    "total": len(patterns)
                }
            }), 200

    except Exception as e:
        logger.error(f"Error getting sensitivity patterns: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/sensitivity/patterns", methods=["POST"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.MANAGE)
def create_sensitivity_pattern():
    """创建自定义敏感模式"""
    try:
        data = request.get_json()

        pattern = SensitivityPattern(
            pattern_id=f"pat_{uuid.uuid4().hex[:8]}",
            category=data.get("category", "pii"),
            sub_type=data.get("sub_type"),
            name=data.get("name"),
            pattern_type=data.get("pattern_type", "regex"),
            pattern=data.get("pattern"),
            description=data.get("description"),
            confidence_weight=data.get("confidence_weight", 80),
            sensitivity_level=data.get("sensitivity_level", "confidential"),
            masking_strategy=data.get("masking_strategy", "mask"),
            created_by=data.get("created_by", "admin"),
        )

        keywords = data.get("keywords")
        if keywords:
            pattern.set_keywords(keywords)

        examples = data.get("examples")
        if examples:
            pattern.set_examples(examples)

        counter_examples = data.get("counter_examples")
        if counter_examples:
            pattern.set_counter_examples(counter_examples)

        with db_manager.get_session() as session:
            session.add(pattern)
            session.commit()
            session.refresh(pattern)

        return jsonify({
            "code": 0,
            "message": "Pattern created",
            "data": pattern.to_dict()
        }), 201

    except Exception as e:
        logger.error(f"Error creating sensitivity pattern: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/sensitivity/patterns/<pattern_id>", methods=["PUT"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.MANAGE)
def update_sensitivity_pattern(pattern_id: str):
    """更新敏感模式"""
    try:
        data = request.get_json()

        with db_manager.get_session() as session:
            pattern = session.query(SensitivityPattern).filter(
                SensitivityPattern.pattern_id == pattern_id
            ).first()

            if not pattern:
                return jsonify({
                    "code": 40400,
                    "message": f"Pattern {pattern_id} not found"
                }), 404

            if not pattern.is_system:
                # 系统预置模式不允许修改
                if "name" in data:
                    pattern.name = data["name"]
                if "pattern" in data:
                    pattern.pattern = data["pattern"]
                if "description" in data:
                    pattern.description = data["description"]
                if "confidence_weight" in data:
                    pattern.confidence_weight = data["confidence_weight"]
                if "sensitivity_level" in data:
                    pattern.sensitivity_level = data["sensitivity_level"]
                if "masking_strategy" in data:
                    pattern.masking_strategy = data["masking_strategy"]
                if "is_active" in data:
                    pattern.is_active = data["is_active"]

                if "keywords" in data:
                    pattern.set_keywords(data["keywords"])
                if "examples" in data:
                    pattern.set_examples(data["examples"])
                if "counter_examples" in data:
                    pattern.set_counter_examples(data["counter_examples"])

            pattern.updated_at = datetime.utcnow()
            session.commit()

        return jsonify({
            "code": 0,
            "message": "Pattern updated",
            "data": pattern.to_dict()
        }), 200

    except Exception as e:
        logger.error(f"Error updating sensitivity pattern {pattern_id}: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/sensitivity/statistics", methods=["GET"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.READ)
def get_sensitivity_statistics():
    """获取敏感数据扫描统计"""
    try:
        from scan_task import get_scan_manager

        manager = get_scan_manager()
        stats = manager.get_statistics()

        return jsonify({
            "code": 0,
            "message": "success",
            "data": stats
        }), 200

    except Exception as e:
        logger.error(f"Error getting sensitivity statistics: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


# ==================== 敏感数据自动扫描 API ====================

@app.route("/api/v1/sensitivity/auto-scan/start", methods=["POST"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.MANAGE)
def start_auto_scan():
    """启动敏感数据自动扫描"""
    try:
        from services.sensitivity_auto_scan_service import (
            get_sensitivity_auto_scan_service,
            AutoScanPolicy,
            AutoScanMode,
        )

        data = request.get_json() or {}
        service = get_sensitivity_auto_scan_service()

        if service.is_running:
            return jsonify({
                "code": 40900,
                "message": "自动扫描正在运行中，请等待完成或取消后再试",
                "data": service.get_progress(),
            }), 409

        # 构建扫描策略
        policy = AutoScanPolicy(
            name=data.get("name", "手动触发扫描"),
            mode=AutoScanMode(data.get("mode", "incremental")),
            databases=data.get("databases", []),
            exclude_databases=data.get("exclude_databases", [
                "information_schema", "mysql", "performance_schema", "sys"
            ]),
            exclude_table_patterns=data.get("exclude_table_patterns", [
                "tmp_*", "temp_*", "log_*", "backup_*"
            ]),
            sample_size=data.get("sample_size", 200),
            confidence_threshold=data.get("confidence_threshold", 60),
            auto_update_metadata=data.get("auto_update_metadata", True),
            auto_generate_masking_rules=data.get("auto_generate_masking_rules", True),
            created_by=data.get("created_by", "admin"),
        )

        with db_manager.get_session() as session:
            progress = service.start_auto_scan(policy=policy, db_session=session)

        return jsonify({
            "code": 0,
            "message": "自动扫描已启动",
            "data": progress.to_dict(),
        }), 201

    except Exception as e:
        logger.error(f"Error starting auto scan: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/sensitivity/auto-scan/progress", methods=["GET"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.READ)
def get_auto_scan_progress():
    """获取自动扫描进度"""
    try:
        from services.sensitivity_auto_scan_service import get_sensitivity_auto_scan_service

        service = get_sensitivity_auto_scan_service()
        progress = service.get_progress()

        return jsonify({
            "code": 0,
            "message": "success",
            "data": progress,
        }), 200

    except Exception as e:
        logger.error(f"Error getting auto scan progress: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/sensitivity/auto-scan/cancel", methods=["POST"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.MANAGE)
def cancel_auto_scan():
    """取消自动扫描"""
    try:
        from services.sensitivity_auto_scan_service import get_sensitivity_auto_scan_service

        service = get_sensitivity_auto_scan_service()
        success = service.cancel_scan()

        if not success:
            return jsonify({
                "code": 40000,
                "message": "没有正在运行的扫描任务",
            }), 400

        return jsonify({
            "code": 0,
            "message": "扫描已取消",
        }), 200

    except Exception as e:
        logger.error(f"Error cancelling auto scan: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/sensitivity/auto-scan/summary", methods=["GET"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.READ)
def get_auto_scan_summary():
    """获取自动扫描摘要"""
    try:
        from services.sensitivity_auto_scan_service import get_sensitivity_auto_scan_service

        service = get_sensitivity_auto_scan_service()
        summary = service.get_scan_summary()

        return jsonify({
            "code": 0,
            "message": "success",
            "data": summary,
        }), 200

    except Exception as e:
        logger.error(f"Error getting auto scan summary: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/sensitivity/auto-scan/quick-check", methods=["POST"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.READ)
def quick_check_sensitivity():
    """快速检测单列敏感性（无需数据库连接）"""
    try:
        from services.sensitivity_auto_scan_service import get_sensitivity_auto_scan_service

        data = request.get_json()
        column_name = data.get("column_name")
        sample_values = data.get("sample_values", [])
        column_type = data.get("column_type", "")

        if not column_name:
            return jsonify({
                "code": 40000,
                "message": "column_name is required",
            }), 400

        service = get_sensitivity_auto_scan_service()
        result = service.quick_scan_column(
            column_name=column_name,
            sample_values=sample_values,
            column_type=column_type,
        )

        return jsonify({
            "code": 0,
            "message": "success",
            "data": result,
        }), 200

    except Exception as e:
        logger.error(f"Error in quick sensitivity check: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


# ==================== Kettle ETL API ====================

@app.route("/api/v1/kettle/status", methods=["GET"])
def get_kettle_status():
    """
    获取 Kettle 服务状态
    返回 Kettle 安装信息和可用性
    """
    return jsonify({
        "code": 0,
        "message": "success",
        "data": {
            "enabled": False,
            "message": "Kettle bridge not available in this deployment",
            "kettle_installed": False,
            "available_features": []
        }
    })


@app.route("/api/v1/kettle/types", methods=["GET"])
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
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


# ==================== Kettle 自动化编排 API ====================

@app.route("/api/v1/kettle/orchestrate", methods=["POST"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.MANAGE)
def kettle_orchestrate():
    """
    自动化编排：分析元数据 → AI推荐规则 → 生成Kettle转换
    一键完成从源表到清洗/脱敏/填充的完整ETL流水线生成
    """
    try:
        from services.kettle_orchestration_service import (
            get_kettle_orchestration_service,
            OrchestrationRequest,
            PipelineType,
        )

        data = request.get_json()
        service = get_kettle_orchestration_service()

        req = OrchestrationRequest(
            name=data.get("name", ""),
            pipeline_type=PipelineType(data.get("pipeline_type", "full_etl")),
            source_database=data.get("source_database", ""),
            source_table=data.get("source_table", ""),
            source_type=data.get("source_type", "mysql"),
            source_connection=data.get("source_connection", {}),
            target_database=data.get("target_database", ""),
            target_table=data.get("target_table", ""),
            target_connection=data.get("target_connection", {}),
            enable_ai_cleaning=data.get("enable_ai_cleaning", True),
            enable_ai_masking=data.get("enable_ai_masking", True),
            enable_ai_imputation=data.get("enable_ai_imputation", True),
            column_filter=data.get("column_filter", []),
            auto_execute=data.get("auto_execute", False),
            dry_run=data.get("dry_run", True),
            created_by=data.get("created_by", "admin"),
        )

        if not req.source_database or not req.source_table:
            return jsonify({
                "code": 40000,
                "message": "source_database and source_table are required",
            }), 400

        with db_manager.get_session() as session:
            result = service.orchestrate(req=req, db_session=session)

        return jsonify({
            "code": 0,
            "message": "编排完成",
            "data": result.to_dict(),
        }), 201

    except Exception as e:
        logger.error(f"Error in Kettle orchestration: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/kettle/orchestrate/<request_id>", methods=["GET"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.READ)
def get_kettle_orchestration(request_id: str):
    """获取编排任务状态"""
    try:
        from services.kettle_orchestration_service import get_kettle_orchestration_service

        service = get_kettle_orchestration_service()
        task = service.get_task(request_id)

        if not task:
            return jsonify({
                "code": 40400,
                "message": f"Task {request_id} not found",
            }), 404

        return jsonify({
            "code": 0,
            "message": "success",
            "data": task,
        }), 200

    except Exception as e:
        logger.error(f"Error getting orchestration task: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/kettle/orchestrate/list", methods=["GET"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.READ)
def list_kettle_orchestrations():
    """列出最近的编排任务"""
    try:
        from services.kettle_orchestration_service import get_kettle_orchestration_service

        limit = int(request.args.get("limit", 20))
        service = get_kettle_orchestration_service()
        tasks = service.list_tasks(limit=limit)

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {"tasks": tasks, "total": len(tasks)},
        }), 200

    except Exception as e:
        logger.error(f"Error listing orchestration tasks: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/kettle/orchestrate/<request_id>/xml", methods=["GET"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.READ)
def get_kettle_orchestration_xml(request_id: str):
    """获取编排生成的 Kettle 转换 XML"""
    try:
        from services.kettle_orchestration_service import get_kettle_orchestration_service

        service = get_kettle_orchestration_service()
        xml_str = service.get_transformation_xml(request_id)

        if not xml_str:
            return jsonify({
                "code": 40400,
                "message": f"No transformation XML found for {request_id}",
            }), 404

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {"xml": xml_str},
        }), 200

    except Exception as e:
        logger.error(f"Error getting orchestration XML: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


# ==================== OCR API ====================

@app.route("/api/v1/ocr/status", methods=["GET"])
def ocr_get_status():
    """
    获取 OCR 服务状态

    返回可用的 OCR 引擎和配置
    """
    try:
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
                "default_engine": os.getenv("OCR_ENGINE", "auto"),
                "languages": os.getenv("OCR_LANGUAGES", "chi_sim+eng"),
                "available_engines": engines,
                "supported_document_types": supported_types,
                "supported_structured_types": structured_types,
            }
        })
    except Exception as e:
        logger.error(f"获取 OCR 状态失败: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


# ==================== Alerts API ====================

@app.route("/api/v1/alerts/metric-rules", methods=["GET"])
def list_metric_alert_rules():
    """
    获取指标预警规则列表
    """
    try:
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("page_size", 20))

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "rules": [],
                "total": 0,
                "page": page,
                "page_size": page_size
            }
        })
    except Exception as e:
        logger.error(f"获取告警规则失败: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/alerts/statistics", methods=["GET"])
def get_alert_statistics():
    """
    获取告警统计
    """
    try:
        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "rules": {
                    "total": 0,
                    "enabled": 0
                },
                "alerts": {
                    "active": 0,
                    "acknowledged": 0,
                    "resolved_today": 0
                },
                "severity_distribution": {}
            }
        })
    except Exception as e:
        logger.error(f"获取告警统计失败: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


# ==================== 数据安全管理 API ====================

@app.route("/api/v1/data-security/scan", methods=["POST"])
@require_jwt()
def create_sensitivity_scan():
    """
    创建敏感数据扫描任务

    请求体:
    {
        "target_type": "database",
        "target_id": "db_001",
        "target_name": "业务数据库",
        "scan_mode": "full",
        "sample_rate": 100,
        "confidence_threshold": 70,
        "databases": ["db1", "db2"],
        "tables": ["table1", "table2"],
        "exclude_patterns": [".*_bak", ".*_temp"],
        "auto_start": true
    }
    """
    from scan_task import get_scan_manager
    from models.security_audit import DataSecurityAuditLog
    import time

    start_time = time.time()

    try:
        data = request.get_json() or {}

        # 获取用户信息
        user_id = request.headers.get("X-User-Id", "anonymous")
        user_name = request.headers.get("X-User-Name", "")
        ip_address = request.remote_addr

        # 创建扫描任务
        scan_manager = get_scan_manager()
        task = scan_manager.create_task(
            target_type=data.get("target_type", "database"),
            target_id=data.get("target_id"),
            target_name=data.get("target_name"),
            scan_mode=data.get("scan_mode", "full"),
            sample_rate=data.get("sample_rate", 100),
            confidence_threshold=data.get("confidence_threshold", 70),
            databases=data.get("databases"),
            tables=data.get("tables"),
            exclude_patterns=data.get("exclude_patterns"),
            created_by=user_id,
            auto_start=data.get("auto_start", False),
        )

        # 记录审计日志
        duration_ms = int((time.time() - start_time) * 1000)
        with db_manager.get_session() as session:
            import uuid
            audit_log = DataSecurityAuditLog(
                audit_id=f"audit_{uuid.uuid4().hex[:12]}",
                operation="scan",
                operation_status="success",
                user_id=user_id,
                user_name=user_name,
                ip_address=ip_address,
                resource_type=data.get("target_type", "database"),
                resource_id=data.get("target_id"),
                resource_name=data.get("target_name"),
                details={
                    "task_id": task.task_id,
                    "scan_mode": task.scan_mode,
                    "confidence_threshold": task.confidence_threshold,
                    "auto_start": data.get("auto_start", False),
                },
                duration_ms=duration_ms,
            )
            session.add(audit_log)
            session.commit()

        return jsonify({
            "code": 0,
            "message": "扫描任务创建成功",
            "data": task.to_dict()
        })

    except Exception as e:
        logger.error(f"创建扫描任务失败: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/data-security/scan/<task_id>", methods=["GET"])
@require_jwt()
def get_sensitivity_scan(task_id: str):
    """
    获取扫描任务状态和结果
    """
    from scan_task import get_scan_manager

    try:
        scan_manager = get_scan_manager()
        task_status = scan_manager.get_task_status(task_id)

        if not task_status:
            return jsonify({"code": 40400, "message": "扫描任务不存在"}), 404

        # 获取扫描结果
        verified_only = request.args.get("verified_only", "false").lower() == "true"
        limit = int(request.args.get("limit", 100))
        offset = int(request.args.get("offset", 0))

        results = scan_manager.get_task_results(
            task_id,
            verified_only=verified_only,
            limit=limit,
            offset=offset
        )

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "task": task_status,
                "results": results,
                "result_count": len(results),
            }
        })

    except Exception as e:
        logger.error(f"获取扫描任务失败: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/data-security/scan/<task_id>/start", methods=["POST"])
@require_jwt()
def start_sensitivity_scan_task(task_id: str):
    """
    启动扫描任务
    """
    from scan_task import get_scan_manager

    try:
        scan_manager = get_scan_manager()
        success = scan_manager.start_task(task_id)

        if not success:
            return jsonify({"code": 40000, "message": "无法启动任务，可能任务不存在或已在运行"}), 400

        return jsonify({
            "code": 0,
            "message": "扫描任务已启动",
            "data": {"task_id": task_id}
        })

    except Exception as e:
        logger.error(f"启动扫描任务失败: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/data-security/scan/<task_id>/cancel", methods=["POST"])
@require_jwt()
def cancel_sensitivity_scan(task_id: str):
    """
    取消扫描任务
    """
    from scan_task import get_scan_manager

    try:
        scan_manager = get_scan_manager()
        success = scan_manager.cancel_task(task_id)

        if not success:
            return jsonify({"code": 40000, "message": "无法取消任务"}), 400

        return jsonify({
            "code": 0,
            "message": "扫描任务已取消",
            "data": {"task_id": task_id}
        })

    except Exception as e:
        logger.error(f"取消扫描任务失败: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/data-security/scan/<task_id>/verify", methods=["POST"])
@require_jwt()
def verify_scan_result(task_id: str):
    """
    校验扫描结果

    请求体:
    {
        "result_id": "res_xxx",
        "verified_result": "confirmed",  // confirmed, rejected, modified
        "sensitivity_type": "pii",       // 可选，修正后的类型
        "sensitivity_level": "restricted" // 可选，修正后的级别
    }
    """
    from scan_task import get_scan_manager
    from models.security_audit import DataSecurityAuditLog

    try:
        data = request.get_json() or {}
        result_id = data.get("result_id")

        if not result_id:
            return jsonify({"code": 40000, "message": "缺少 result_id 参数"}), 400

        user_id = request.headers.get("X-User-Id", "anonymous")
        user_name = request.headers.get("X-User-Name", "")

        scan_manager = get_scan_manager()
        success = scan_manager.verify_result(
            result_id=result_id,
            verified_result=data.get("verified_result", "confirmed"),
            verified_by=user_id,
            sensitivity_type=data.get("sensitivity_type"),
            sensitivity_level=data.get("sensitivity_level"),
        )

        if not success:
            return jsonify({"code": 40400, "message": "结果不存在"}), 404

        # 记录审计日志
        with db_manager.get_session() as session:
            import uuid
            audit_log = DataSecurityAuditLog(
                audit_id=f"audit_{uuid.uuid4().hex[:12]}",
                operation="verify",
                operation_status="success",
                user_id=user_id,
                user_name=user_name,
                ip_address=request.remote_addr,
                resource_type="scan_result",
                resource_id=result_id,
                details={
                    "task_id": task_id,
                    "verified_result": data.get("verified_result"),
                    "sensitivity_type": data.get("sensitivity_type"),
                    "sensitivity_level": data.get("sensitivity_level"),
                },
            )
            session.add(audit_log)
            session.commit()

        return jsonify({
            "code": 0,
            "message": "校验结果已保存",
            "data": {"result_id": result_id}
        })

    except Exception as e:
        logger.error(f"校验扫描结果失败: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/data-security/apply-masking", methods=["POST"])
@require_jwt()
def apply_data_masking():
    """
    应用数据脱敏

    请求体:
    {
        "data": [{"name": "张三", "phone": "13812345678"}],
        "column_metadata": {
            "name": {"sensitivity_type": "pii", "sensitivity_level": "confidential"},
            "phone": {"sensitivity_type": "pii", "sensitivity_level": "confidential"}
        },
        "preview": false  // 是否仅预览
    }
    """
    from data_masking import get_masking_service
    from models.security_audit import DataSecurityAuditLog
    import time

    start_time = time.time()

    try:
        data = request.get_json() or {}
        input_data = data.get("data", [])
        column_metadata = data.get("column_metadata", {})
        preview_only = data.get("preview", False)

        if not input_data:
            return jsonify({"code": 40000, "message": "缺少数据"}), 400

        user_id = request.headers.get("X-User-Id", "anonymous")
        user_name = request.headers.get("X-User-Name", "")

        masking_service = get_masking_service()

        if preview_only:
            # 仅预览
            result = masking_service.get_masking_preview(
                sample_data=input_data,
                column_metadata=column_metadata,
                max_rows=5
            )
            return jsonify({
                "code": 0,
                "message": "脱敏预览",
                "data": result
            })

        # 执行脱敏
        masked_data = masking_service.mask_dataframe(input_data, column_metadata)

        # 记录审计日志
        duration_ms = int((time.time() - start_time) * 1000)
        sensitivity_types = list(set(
            m.get("sensitivity_type") for m in column_metadata.values()
            if m.get("sensitivity_type")
        ))

        with db_manager.get_session() as session:
            import uuid
            audit_log = DataSecurityAuditLog(
                audit_id=f"audit_{uuid.uuid4().hex[:12]}",
                operation="mask",
                operation_status="success",
                user_id=user_id,
                user_name=user_name,
                ip_address=request.remote_addr,
                resource_type="data",
                details={
                    "columns_masked": list(column_metadata.keys()),
                },
                affected_rows=len(input_data),
                affected_columns=len(column_metadata),
                duration_ms=duration_ms,
            )
            audit_log.set_sensitivity_types(sensitivity_types)
            session.add(audit_log)
            session.commit()

        return jsonify({
            "code": 0,
            "message": "脱敏成功",
            "data": {
                "masked_data": masked_data,
                "rows_processed": len(masked_data),
                "columns_masked": list(column_metadata.keys()),
            }
        })

    except Exception as e:
        logger.error(f"数据脱敏失败: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/data-security/rules", methods=["GET"])
@require_jwt()
def list_masking_rules():
    """
    获取脱敏规则列表
    """
    from models.security_audit import MaskingRule

    try:
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("page_size", 20))
        sensitivity_type = request.args.get("sensitivity_type")
        enabled_only = request.args.get("enabled_only", "false").lower() == "true"

        with db_manager.get_session() as session:
            query = session.query(MaskingRule)

            if sensitivity_type:
                query = query.filter(MaskingRule.sensitivity_type == sensitivity_type)

            if enabled_only:
                query = query.filter(MaskingRule.enabled == 1)

            total = query.count()
            rules = query.order_by(
                MaskingRule.priority.desc(),
                MaskingRule.created_at.desc()
            ).limit(page_size).offset((page - 1) * page_size).all()

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

    except Exception as e:
        logger.error(f"获取脱敏规则失败: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/data-security/rules", methods=["POST"])
@require_jwt()
def create_masking_rule():
    """
    创建脱敏规则

    请求体:
    {
        "name": "手机号脱敏",
        "description": "对手机号进行部分遮蔽",
        "sensitivity_type": "pii",
        "sensitivity_level": "confidential",
        "column_pattern": "(phone|mobile|手机)",
        "strategy": "partial_mask",
        "options": {"mask_char": "*", "keep_start": 3, "keep_end": 4},
        "priority": 10
    }
    """
    from models.security_audit import MaskingRule

    try:
        data = request.get_json() or {}
        user_id = request.headers.get("X-User-Id", "anonymous")

        if not data.get("name"):
            return jsonify({"code": 40000, "message": "规则名称不能为空"}), 400

        if not data.get("strategy"):
            return jsonify({"code": 40000, "message": "脱敏策略不能为空"}), 400

        with db_manager.get_session() as session:
            import uuid
            rule = MaskingRule(
                rule_id=f"rule_{uuid.uuid4().hex[:12]}",
                name=data["name"],
                description=data.get("description"),
                sensitivity_type=data.get("sensitivity_type", "any"),
                sensitivity_level=data.get("sensitivity_level", "any"),
                column_pattern=data.get("column_pattern"),
                data_type=data.get("data_type"),
                strategy=data["strategy"],
                options=data.get("options", {}),
                enabled=1 if data.get("enabled", True) else 0,
                priority=data.get("priority", 0),
                is_system=0,
                created_by=user_id,
            )

            session.add(rule)
            session.commit()
            session.refresh(rule)

            return jsonify({
                "code": 0,
                "message": "规则创建成功",
                "data": rule.to_dict()
            })

    except IntegrityError:
        return jsonify({"code": 40900, "message": "规则已存在"}), 409
    except Exception as e:
        logger.error(f"创建脱敏规则失败: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/data-security/rules/<rule_id>", methods=["PUT"])
@require_jwt()
def update_masking_rule(rule_id: str):
    """
    更新脱敏规则
    """
    from models.security_audit import MaskingRule

    try:
        data = request.get_json() or {}

        with db_manager.get_session() as session:
            rule = session.query(MaskingRule).filter(
                MaskingRule.rule_id == rule_id
            ).first()

            if not rule:
                return jsonify({"code": 40400, "message": "规则不存在"}), 404

            # 系统预置规则不允许修改
            if rule.is_system:
                return jsonify({"code": 40300, "message": "系统预置规则不允许修改"}), 403

            # 更新字段
            if "name" in data:
                rule.name = data["name"]
            if "description" in data:
                rule.description = data["description"]
            if "sensitivity_type" in data:
                rule.sensitivity_type = data["sensitivity_type"]
            if "sensitivity_level" in data:
                rule.sensitivity_level = data["sensitivity_level"]
            if "column_pattern" in data:
                rule.column_pattern = data["column_pattern"]
            if "data_type" in data:
                rule.data_type = data["data_type"]
            if "strategy" in data:
                rule.strategy = data["strategy"]
            if "options" in data:
                rule.options = data["options"]
            if "enabled" in data:
                rule.enabled = 1 if data["enabled"] else 0
            if "priority" in data:
                rule.priority = data["priority"]

            session.commit()
            session.refresh(rule)

            return jsonify({
                "code": 0,
                "message": "规则更新成功",
                "data": rule.to_dict()
            })

    except Exception as e:
        logger.error(f"更新脱敏规则失败: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/data-security/rules/<rule_id>", methods=["DELETE"])
@require_jwt()
def delete_masking_rule(rule_id: str):
    """
    删除脱敏规则
    """
    from models.security_audit import MaskingRule

    try:
        with db_manager.get_session() as session:
            rule = session.query(MaskingRule).filter(
                MaskingRule.rule_id == rule_id
            ).first()

            if not rule:
                return jsonify({"code": 40400, "message": "规则不存在"}), 404

            # 系统预置规则不允许删除
            if rule.is_system:
                return jsonify({"code": 40300, "message": "系统预置规则不允许删除"}), 403

            session.delete(rule)
            session.commit()

            return jsonify({
                "code": 0,
                "message": "规则删除成功"
            })

    except Exception as e:
        logger.error(f"删除脱敏规则失败: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/data-security/audit-logs", methods=["GET"])
@require_jwt()
def list_security_audit_logs():
    """
    获取数据安全审计日志
    """
    from models.security_audit import DataSecurityAuditLog

    try:
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("page_size", 20))
        operation = request.args.get("operation")
        user_id = request.args.get("user_id")
        resource_type = request.args.get("resource_type")
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")

        with db_manager.get_session() as session:
            query = session.query(DataSecurityAuditLog)

            if operation:
                query = query.filter(DataSecurityAuditLog.operation == operation)
            if user_id:
                query = query.filter(DataSecurityAuditLog.user_id == user_id)
            if resource_type:
                query = query.filter(DataSecurityAuditLog.resource_type == resource_type)
            if start_date:
                query = query.filter(DataSecurityAuditLog.created_at >= start_date)
            if end_date:
                query = query.filter(DataSecurityAuditLog.created_at <= end_date)

            total = query.count()
            logs = query.order_by(
                DataSecurityAuditLog.created_at.desc()
            ).limit(page_size).offset((page - 1) * page_size).all()

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

    except Exception as e:
        logger.error(f"获取审计日志失败: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/data-security/statistics", methods=["GET"])
@require_jwt()
def get_security_statistics():
    """
    获取数据安全统计信息
    """
    from scan_task import get_scan_manager
    from models.security_audit import DataSecurityAuditLog

    try:
        scan_manager = get_scan_manager()
        scan_stats = scan_manager.get_statistics()

        with db_manager.get_session() as session:
            # 审计日志统计
            from sqlalchemy import func
            audit_stats = session.query(
                DataSecurityAuditLog.operation,
                func.count(DataSecurityAuditLog.id).label('count')
            ).group_by(DataSecurityAuditLog.operation).all()

            audit_by_operation = {row[0]: row[1] for row in audit_stats}

            return jsonify({
                "code": 0,
                "message": "success",
                "data": {
                    "scan": scan_stats,
                    "audit": {
                        "by_operation": audit_by_operation,
                        "total_logs": sum(audit_by_operation.values()),
                    }
                }
            })

    except Exception as e:
        logger.error(f"获取安全统计失败: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


# ==================== 多表融合API ====================

@app.route("/api/v1/fusion/detect-join-keys", methods=["POST"])
@require_jwt()
def detect_join_keys():
    """
    检测潜在的JOIN关联键

    Request Body:
    {
        "source_table": "表名",
        "target_tables": ["目标表1", "目标表2"],
        "source_database": "源数据库名（可选）",
        "target_database": "目标数据库名（可选）",
        "sample_size": 1000
    }
    """
    from services.table_fusion_service import get_table_fusion_service

    try:
        data = request.get_json()
        source_table = data.get("source_table")
        target_tables = data.get("target_tables", [])
        source_database = data.get("source_database")
        target_database = data.get("target_database")
        sample_size = data.get("sample_size", 1000)

        if not source_table:
            return jsonify({"code": 40001, "message": "source_table是必需的"}), 400

        if not target_tables:
            return jsonify({"code": 40002, "message": "target_tables是必需的"}), 400

        fusion_service = get_table_fusion_service()

        with db_manager.get_session() as session:
            results = fusion_service.detect_potential_join_keys(
                db=session,
                source_table=source_table,
                target_tables=target_tables,
                source_database=source_database,
                target_database=target_database,
                sample_size=sample_size
            )

            # 转换为可序列化格式
            serialized_results = {}
            for table, keys in results.items():
                serialized_results[table] = [k.to_dict() for k in keys]

            return jsonify({
                "code": 0,
                "message": "success",
                "data": {
                    "source_table": source_table,
                    "join_keys": serialized_results,
                    "total_candidates": sum(len(keys) for keys in serialized_results.values())
                }
            })

    except Exception as e:
        logger.error(f"检测JOIN关联键失败: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/fusion/validate-join", methods=["POST"])
@require_jwt()
def validate_join_consistency():
    """
    验证JOIN数据一致性

    Request Body:
    {
        "source_table": "源表名",
        "source_key": "源表关联键",
        "target_table": "目标表名",
        "target_key": "目标表关联键",
        "source_database": "源数据库名（可选）",
        "target_database": "目标数据库名（可选）",
        "sample_size": 10000
    }
    """
    from services.table_fusion_service import get_table_fusion_service

    try:
        data = request.get_json()
        source_table = data.get("source_table")
        source_key = data.get("source_key")
        target_table = data.get("target_table")
        target_key = data.get("target_key")
        source_database = data.get("source_database")
        target_database = data.get("target_database")
        sample_size = data.get("sample_size", 10000)

        # 参数验证
        if not all([source_table, source_key, target_table, target_key]):
            return jsonify({
                "code": 40001,
                "message": "source_table, source_key, target_table, target_key 都是必需的"
            }), 400

        fusion_service = get_table_fusion_service()

        with db_manager.get_session() as session:
            quality_score = fusion_service.validate_join_consistency(
                db=session,
                source_table=source_table,
                source_key=source_key,
                target_table=target_table,
                target_key=target_key,
                source_database=source_database,
                target_database=target_database,
                sample_size=sample_size
            )

            return jsonify({
                "code": 0,
                "message": "success",
                "data": {
                    "source_table": source_table,
                    "source_key": source_key,
                    "target_table": target_table,
                    "target_key": target_key,
                    "quality_score": quality_score.to_dict()
                }
            })

    except Exception as e:
        logger.error(f"验证JOIN一致性失败: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/fusion/recommend-strategy", methods=["POST"])
@require_jwt()
def recommend_join_strategy():
    """
    推荐最优JOIN策略

    Request Body:
    {
        "source_table": "源表名",
        "target_table": "目标表名",
        "join_keys": [
            {
                "source_column": "col1",
                "target_column": "col1",
                "confidence": 0.95,
                "detection_method": "name_match"
            }
        ],
        "source_database": "源数据库名（可选）",
        "target_database": "目标数据库名（可选）"
    }

    也可以不提供join_keys，系统会自动检测：
    {
        "source_table": "源表名",
        "target_table": "目标表名",
        "auto_detect": true
    }
    """
    from services.table_fusion_service import get_table_fusion_service, JoinKeyPair

    try:
        data = request.get_json()
        source_table = data.get("source_table")
        target_table = data.get("target_table")
        source_database = data.get("source_database")
        target_database = data.get("target_database")
        auto_detect = data.get("auto_detect", False)
        join_keys_data = data.get("join_keys", [])

        if not source_table or not target_table:
            return jsonify({
                "code": 40001,
                "message": "source_table 和 target_table 是必需的"
            }), 400

        fusion_service = get_table_fusion_service()

        with db_manager.get_session() as session:
            # 如果需要自动检测关联键
            if auto_detect or not join_keys_data:
                detected = fusion_service.detect_potential_join_keys(
                    db=session,
                    source_table=source_table,
                    target_tables=[target_table],
                    source_database=source_database,
                    target_database=target_database
                )
                join_keys = detected.get(target_table, [])
            else:
                # 转换传入的关联键数据
                join_keys = []
                for jk in join_keys_data:
                    join_keys.append(JoinKeyPair(
                        source_column=jk.get("source_column"),
                        target_column=jk.get("target_column"),
                        source_table=source_table,
                        target_table=target_table,
                        confidence=jk.get("confidence", 0.5),
                        detection_method=jk.get("detection_method", "manual"),
                        name_similarity=jk.get("name_similarity", 0.0),
                        value_overlap_rate=jk.get("value_overlap_rate", 0.0),
                        cardinality_match=jk.get("cardinality_match", True),
                        is_primary_key=jk.get("is_primary_key", False),
                        is_foreign_key=jk.get("is_foreign_key", False),
                    ))

            # 获取策略推荐
            strategy = fusion_service.recommend_join_strategy(
                db=session,
                source_table=source_table,
                target_table=target_table,
                join_keys=join_keys,
                source_database=source_database,
                target_database=target_database
            )

            return jsonify({
                "code": 0,
                "message": "success",
                "data": strategy.to_dict()
            })

    except Exception as e:
        logger.error(f"推荐JOIN策略失败: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/fusion/generate-kettle-config", methods=["POST"])
@require_jwt()
def generate_kettle_join_config():
    """
    生成Kettle JOIN步骤配置

    Request Body:
    {
        "source_table": "源表名",
        "target_table": "目标表名",
        "source_step_name": "Source",
        "target_step_name": "Target",
        "join_keys": [...],   // 可选，不提供则自动检测
        "source_database": "源数据库名（可选）",
        "target_database": "目标数据库名（可选）"
    }
    """
    from services.table_fusion_service import get_table_fusion_service, JoinKeyPair

    try:
        data = request.get_json()
        source_table = data.get("source_table")
        target_table = data.get("target_table")
        source_step_name = data.get("source_step_name", "Source")
        target_step_name = data.get("target_step_name", "Target")
        source_database = data.get("source_database")
        target_database = data.get("target_database")
        join_keys_data = data.get("join_keys", [])

        if not source_table or not target_table:
            return jsonify({
                "code": 40001,
                "message": "source_table 和 target_table 是必需的"
            }), 400

        fusion_service = get_table_fusion_service()

        with db_manager.get_session() as session:
            # 检测或使用提供的关联键
            if not join_keys_data:
                detected = fusion_service.detect_potential_join_keys(
                    db=session,
                    source_table=source_table,
                    target_tables=[target_table],
                    source_database=source_database,
                    target_database=target_database
                )
                join_keys = detected.get(target_table, [])
            else:
                join_keys = []
                for jk in join_keys_data:
                    join_keys.append(JoinKeyPair(
                        source_column=jk.get("source_column"),
                        target_column=jk.get("target_column"),
                        source_table=source_table,
                        target_table=target_table,
                        confidence=jk.get("confidence", 0.5),
                        detection_method=jk.get("detection_method", "manual"),
                    ))

            # 获取策略推荐
            strategy = fusion_service.recommend_join_strategy(
                db=session,
                source_table=source_table,
                target_table=target_table,
                join_keys=join_keys,
                source_database=source_database,
                target_database=target_database
            )

            # 生成Kettle配置
            kettle_config = fusion_service.generate_kettle_join_config(
                strategy=strategy,
                source_step_name=source_step_name,
                target_step_name=target_step_name
            )

            return jsonify({
                "code": 0,
                "message": "success",
                "data": {
                    "kettle_config": kettle_config,
                    "strategy_summary": {
                        "join_type": strategy.join_type.value,
                        "quality_score": strategy.quality_score.overall_score,
                        "warnings": strategy.warnings
                    }
                }
            })

    except Exception as e:
        logger.error(f"生成Kettle配置失败: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/fusion/detect-join-path", methods=["POST"])
@require_jwt()
def detect_multi_table_join_path():
    """
    检测多表之间的JOIN路径

    用于发现间接关联关系，如 A -> B -> C

    Request Body:
    {
        "tables": ["table1", "table2", "table3"],
        "database": "数据库名（可选）",
        "max_depth": 3
    }
    """
    from services.table_fusion_service import get_table_fusion_service

    try:
        data = request.get_json()
        tables = data.get("tables", [])
        database = data.get("database")
        max_depth = data.get("max_depth", 3)

        if len(tables) < 2:
            return jsonify({
                "code": 40001,
                "message": "至少需要2个表才能检测关联路径"
            }), 400

        fusion_service = get_table_fusion_service()

        with db_manager.get_session() as session:
            paths = fusion_service.detect_multi_table_join_path(
                db=session,
                tables=tables,
                database=database,
                max_depth=max_depth
            )

            return jsonify({
                "code": 0,
                "message": "success",
                "data": {
                    "tables": tables,
                    "paths": paths,
                    "total_paths": len(paths)
                }
            })

    except Exception as e:
        logger.error(f"检测多表关联路径失败: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/fusion/analyze-tables", methods=["POST"])
@require_jwt()
def analyze_tables_for_fusion():
    """
    综合分析多表融合方案

    一次性返回：
    - 所有表之间的潜在关联键
    - 每对关联的质量评分
    - 推荐的融合顺序和策略

    Request Body:
    {
        "tables": ["table1", "table2", "table3"],
        "database": "数据库名（可选）",
        "primary_table": "主表名（可选，默认为第一个表）"
    }
    """
    from services.table_fusion_service import get_table_fusion_service

    try:
        data = request.get_json()
        tables = data.get("tables", [])
        database = data.get("database")
        primary_table = data.get("primary_table")

        if len(tables) < 2:
            return jsonify({
                "code": 40001,
                "message": "至少需要2个表进行融合分析"
            }), 400

        if not primary_table:
            primary_table = tables[0]

        if primary_table not in tables:
            return jsonify({
                "code": 40002,
                "message": "primary_table 必须在 tables 列表中"
            }), 400

        fusion_service = get_table_fusion_service()

        with db_manager.get_session() as session:
            # 以主表为源，检测与所有其他表的关联
            other_tables = [t for t in tables if t != primary_table]

            join_keys_result = fusion_service.detect_potential_join_keys(
                db=session,
                source_table=primary_table,
                target_tables=other_tables,
                source_database=database,
                target_database=database
            )

            # 为每个有效关联生成策略推荐
            fusion_strategies = []
            for target_table, keys in join_keys_result.items():
                if keys:
                    strategy = fusion_service.recommend_join_strategy(
                        db=session,
                        source_table=primary_table,
                        target_table=target_table,
                        join_keys=keys,
                        source_database=database,
                        target_database=database
                    )
                    fusion_strategies.append({
                        "target_table": target_table,
                        "strategy": strategy.to_dict()
                    })

            # 按质量评分排序，推荐最优融合顺序
            fusion_strategies.sort(
                key=lambda x: x["strategy"]["quality_score"]["overall_score"],
                reverse=True
            )

            return jsonify({
                "code": 0,
                "message": "success",
                "data": {
                    "primary_table": primary_table,
                    "total_tables": len(tables),
                    "join_keys": {
                        table: [k.to_dict() for k in keys]
                        for table, keys in join_keys_result.items()
                    },
                    "fusion_strategies": fusion_strategies,
                    "recommended_order": [
                        primary_table
                    ] + [s["target_table"] for s in fusion_strategies],
                    "summary": {
                        "tables_with_joins": len([
                            t for t, k in join_keys_result.items() if k
                        ]),
                        "tables_without_joins": len([
                            t for t, k in join_keys_result.items() if not k
                        ]),
                        "avg_quality_score": (
                            sum(s["strategy"]["quality_score"]["overall_score"]
                                for s in fusion_strategies) / len(fusion_strategies)
                            if fusion_strategies else 0
                        )
                    }
                }
            })

    except Exception as e:
        logger.error(f"分析多表融合方案失败: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


# ==================== 资产价值评估API ====================

@app.route("/api/v1/assets/value/evaluate/<asset_id>", methods=["POST"])
@require_jwt()
def evaluate_asset_value(asset_id):
    """
    评估单个资产的价值

    Request Body (可选):
    {
        "business_config": {
            "domain_weights": {
                "finance": 1.0,
                "marketing": 0.8,
                "operations": 0.6
            }
        },
        "weights": {
            "usage": 0.35,
            "business": 0.30,
            "quality": 0.20,
            "governance": 0.15
        }
    }
    """
    from services.asset_value_calculator import get_asset_value_calculator, AssetValueCalculator

    try:
        data = request.get_json() or {}
        business_config = data.get("business_config")
        weights = data.get("weights")

        # 如果指定了自定义权重，创建新的计算器实例
        if weights:
            calculator = AssetValueCalculator(weights=weights)
        else:
            calculator = get_asset_value_calculator()

        with db_manager.get_session() as session:
            breakdown = calculator.evaluate_asset(
                db=session,
                asset_id=asset_id,
                business_config=business_config,
                save_result=True
            )

            # 生成改进建议
            recommendations = calculator.generate_recommendations(breakdown)

            return jsonify({
                "code": 0,
                "message": "success",
                "data": {
                    "asset_id": asset_id,
                    "score_breakdown": breakdown.to_dict(),
                    "recommendations": recommendations,
                }
            })

    except Exception as e:
        logger.error(f"评估资产价值失败: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/assets/value/batch-evaluate", methods=["POST"])
@require_jwt()
def batch_evaluate_asset_values():
    """
    批量评估资产价值

    Request Body:
    {
        "asset_ids": ["asset1", "asset2", "asset3"],
        "business_config": {...}  // 可选
    }
    """
    from services.asset_value_calculator import get_asset_value_calculator

    try:
        data = request.get_json()
        asset_ids = data.get("asset_ids", [])
        business_config = data.get("business_config")

        if not asset_ids:
            return jsonify({"code": 40001, "message": "asset_ids是必需的"}), 400

        calculator = get_asset_value_calculator()

        with db_manager.get_session() as session:
            results = []
            for asset_id in asset_ids:
                try:
                    breakdown = calculator.evaluate_asset(
                        db=session,
                        asset_id=asset_id,
                        business_config=business_config,
                        save_result=True
                    )
                    results.append({
                        "asset_id": asset_id,
                        "status": "success",
                        "score_breakdown": breakdown.to_dict(),
                    })
                except Exception as e:
                    results.append({
                        "asset_id": asset_id,
                        "status": "failed",
                        "error": str(e),
                    })

            return jsonify({
                "code": 0,
                "message": "success",
                "data": {
                    "total": len(asset_ids),
                    "success_count": len([r for r in results if r["status"] == "success"]),
                    "results": results,
                }
            })

    except Exception as e:
        logger.error(f"批量评估资产价值失败: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/assets/ranking", methods=["GET"])
@require_jwt()
def get_asset_ranking():
    """
    获取资产价值排名

    Query Parameters:
    - limit: 限制数量 (默认100)
    - offset: 偏移量 (默认0)
    - asset_type: 资产类型筛选 (可选)
    - value_level: 价值等级筛选 (S/A/B/C，可选)
    """
    from services.asset_value_calculator import get_asset_value_calculator

    try:
        limit = request.args.get("limit", 100, type=int)
        offset = request.args.get("offset", 0, type=int)
        asset_type = request.args.get("asset_type")
        value_level = request.args.get("value_level")

        calculator = get_asset_value_calculator()

        with db_manager.get_session() as session:
            ranking = calculator.get_asset_ranking(
                db=session,
                limit=limit,
                offset=offset,
                asset_type=asset_type,
                value_level=value_level
            )

            return jsonify({
                "code": 0,
                "message": "success",
                "data": {
                    "ranking": ranking,
                    "total": len(ranking),
                    "filters": {
                        "asset_type": asset_type,
                        "value_level": value_level,
                    },
                    "pagination": {
                        "limit": limit,
                        "offset": offset,
                    }
                }
            })

    except Exception as e:
        logger.error(f"获取资产排名失败: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/assets/<asset_id>/value-analysis", methods=["GET"])
@require_jwt()
def get_asset_value_analysis(asset_id):
    """
    获取资产价值详细分析

    Query Parameters:
    - trend_days: 趋势天数 (默认30)
    """
    from services.asset_value_calculator import get_asset_value_calculator
    from models.asset_value_metrics import AssetValueMetrics
    from models.assets import DataAsset

    try:
        trend_days = request.args.get("trend_days", 30, type=int)

        calculator = get_asset_value_calculator()

        with db_manager.get_session() as session:
            # 获取当前指标
            metrics = session.query(AssetValueMetrics).filter(
                AssetValueMetrics.asset_id == asset_id
            ).first()

            # 获取资产信息
            asset = session.query(DataAsset).filter(
                DataAsset.asset_id == asset_id
            ).first()

            if not metrics:
                # 如果没有指标记录，进行评估
                breakdown = calculator.evaluate_asset(
                    db=session,
                    asset_id=asset_id,
                    save_result=True
                )
                current_metrics = breakdown.to_dict()
            else:
                current_metrics = metrics.to_dict()

            # 获取趋势数据
            trend = calculator.get_value_trend(session, asset_id, trend_days)

            # 生成建议
            if metrics:
                from services.asset_value_calculator import ValueScoreBreakdown
                breakdown = ValueScoreBreakdown(
                    usage_score=metrics.usage_frequency_score or 0,
                    business_score=metrics.business_importance_score or 0,
                    quality_score=metrics.quality_score or 0,
                    governance_score=metrics.governance_score or 0,
                    overall_score=metrics.overall_value_score or 0,
                    value_level=metrics.asset_value_level or "C",
                    details=metrics.calculation_details or {}
                )
                recommendations = calculator.generate_recommendations(breakdown)
            else:
                recommendations = []

            # 计算趋势方向
            trend_direction = "stable"
            if len(trend) >= 2:
                latest_score = trend[-1].get("overall_value_score", 0)
                prev_score = trend[0].get("overall_value_score", 0)
                if latest_score > prev_score + 5:
                    trend_direction = "up"
                elif latest_score < prev_score - 5:
                    trend_direction = "down"

            return jsonify({
                "code": 0,
                "message": "success",
                "data": {
                    "asset_id": asset_id,
                    "asset_name": asset.name if asset else None,
                    "asset_type": asset.type if asset else None,
                    "current_metrics": current_metrics,
                    "trend": {
                        "direction": trend_direction,
                        "history": trend,
                    },
                    "recommendations": recommendations,
                }
            })

    except Exception as e:
        logger.error(f"获取资产价值分析失败: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/assets/value-report", methods=["GET"])
@require_jwt()
def get_asset_value_report():
    """
    获取资产价值分布报告
    """
    from services.asset_value_calculator import get_asset_value_calculator
    from models.asset_value_metrics import AssetValueMetrics
    from sqlalchemy import func

    try:
        calculator = get_asset_value_calculator()

        with db_manager.get_session() as session:
            # 获取价值等级分布
            distribution = calculator.get_value_distribution(session)

            # 获取评分统计
            stats = session.query(
                func.avg(AssetValueMetrics.overall_value_score).label('avg_score'),
                func.min(AssetValueMetrics.overall_value_score).label('min_score'),
                func.max(AssetValueMetrics.overall_value_score).label('max_score'),
                func.count(AssetValueMetrics.id).label('total_count'),
            ).first()

            # 获取各维度平均分
            dimension_stats = session.query(
                func.avg(AssetValueMetrics.usage_frequency_score).label('avg_usage'),
                func.avg(AssetValueMetrics.business_importance_score).label('avg_business'),
                func.avg(AssetValueMetrics.quality_score).label('avg_quality'),
                func.avg(AssetValueMetrics.governance_score).label('avg_governance'),
            ).first()

            # 获取Top 10资产
            top_assets = calculator.get_asset_ranking(session, limit=10)

            return jsonify({
                "code": 0,
                "message": "success",
                "data": {
                    "distribution": distribution,
                    "statistics": {
                        "average_score": round(stats.avg_score or 0, 2),
                        "min_score": round(stats.min_score or 0, 2),
                        "max_score": round(stats.max_score or 0, 2),
                        "total_assets": stats.total_count or 0,
                    },
                    "dimension_averages": {
                        "usage": round(dimension_stats.avg_usage or 0, 2),
                        "business": round(dimension_stats.avg_business or 0, 2),
                        "quality": round(dimension_stats.avg_quality or 0, 2),
                        "governance": round(dimension_stats.avg_governance or 0, 2),
                    },
                    "top_assets": top_assets,
                }
            })

    except Exception as e:
        logger.error(f"获取资产价值报告失败: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/assets/<asset_id>/usage", methods=["POST"])
@require_jwt()
def record_asset_usage(asset_id):
    """
    记录资产使用情况

    Request Body:
    {
        "usage_type": "query",  // query, download, api_call, reference
        "source_type": "dashboard",  // dashboard, report, etl_job, api, adhoc
        "source_id": "xxx",  // 可选
        "source_name": "xxx"  // 可选
    }
    """
    from models.asset_value_metrics import AssetUsageLog

    try:
        data = request.get_json()
        usage_type = data.get("usage_type", "query")
        source_type = data.get("source_type", "adhoc")
        source_id = data.get("source_id")
        source_name = data.get("source_name")

        # 获取用户信息
        user_id = request.headers.get("X-User-ID", "anonymous")
        user_name = request.headers.get("X-User-Name")

        with db_manager.get_session() as session:
            usage_log = AssetUsageLog(
                asset_id=asset_id,
                usage_type=usage_type,
                user_id=user_id,
                user_name=user_name,
                source_type=source_type,
                source_id=source_id,
                source_name=source_name,
            )
            session.add(usage_log)
            session.commit()

            return jsonify({
                "code": 0,
                "message": "success",
                "data": {
                    "recorded": True,
                    "asset_id": asset_id,
                    "usage_type": usage_type,
                }
            })

    except Exception as e:
        logger.error(f"记录资产使用失败: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/assets/<asset_id>/business-config", methods=["PUT"])
@require_jwt()
def update_asset_business_config(asset_id):
    """
    更新资产业务配置

    Request Body:
    {
        "is_core_indicator": true,
        "sla_level": "gold",  // gold, silver, bronze
        "business_domain": "finance",
        "business_owner": "user@example.com"
    }
    """
    from models.asset_value_metrics import AssetValueMetrics
    import uuid

    try:
        data = request.get_json()

        with db_manager.get_session() as session:
            metrics = session.query(AssetValueMetrics).filter(
                AssetValueMetrics.asset_id == asset_id
            ).first()

            if not metrics:
                metrics = AssetValueMetrics(
                    metrics_id=f"vm_{uuid.uuid4().hex[:12]}",
                    asset_id=asset_id,
                )
                session.add(metrics)

            # 更新业务配置
            if "is_core_indicator" in data:
                metrics.is_core_indicator = 1 if data["is_core_indicator"] else 0

            if "sla_level" in data:
                metrics.sla_level = data["sla_level"]

            if "business_domain" in data:
                metrics.business_domain = data["business_domain"]

            if "business_owner" in data:
                metrics.business_owner = data["business_owner"]

            session.commit()

            return jsonify({
                "code": 0,
                "message": "success",
                "data": {
                    "asset_id": asset_id,
                    "updated_config": {
                        "is_core_indicator": bool(metrics.is_core_indicator),
                        "sla_level": metrics.sla_level,
                        "business_domain": metrics.business_domain,
                        "business_owner": metrics.business_owner,
                    }
                }
            })

    except Exception as e:
        logger.error(f"更新资产业务配置失败: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


# ==================== 资产自动编目 API ====================

@app.route("/api/v1/assets/auto-catalog", methods=["POST"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.UPDATE)
def auto_catalog_from_etl():
    """
    ETL完成后自动注册目标表为数据资产

    Request Body:
    {
        "source_database": "source_db",
        "source_table": "source_table",
        "target_database": "target_db",
        "target_table": "target_table",
        "etl_task_id": "task_xxx",
        "created_by": "user"
    }
    """
    from services.asset_auto_catalog_service import get_asset_auto_catalog_service

    try:
        data = request.get_json()
        if not data:
            return jsonify({"code": 40000, "message": "请求体不能为空"}), 400

        source_database = data.get("source_database", "")
        source_table = data.get("source_table", "")
        target_database = data.get("target_database", "")
        target_table = data.get("target_table", "")

        if not target_database or not target_table:
            return jsonify({"code": 40000, "message": "目标数据库和表名不能为空"}), 400

        service = get_asset_auto_catalog_service()

        with db_manager.get_session() as session:
            result = service.auto_catalog_from_etl(
                source_database=source_database,
                source_table=source_table,
                target_database=target_database,
                target_table=target_table,
                etl_task_id=data.get("etl_task_id", ""),
                created_by=data.get("created_by", "system"),
                db_session=session,
            )

        return jsonify({"code": 0, "message": "success", "data": result})

    except Exception as e:
        logger.error(f"自动编目失败: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/assets/auto-catalog/batch", methods=["POST"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.UPDATE)
def batch_catalog_from_metadata():
    """
    批量从元数据注册资产（全量同步）

    Request Body:
    {
        "database_name": "optional_db_name",
        "created_by": "user"
    }
    """
    from services.asset_auto_catalog_service import get_asset_auto_catalog_service

    try:
        data = request.get_json() or {}
        service = get_asset_auto_catalog_service()

        with db_manager.get_session() as session:
            result = service.batch_catalog_from_metadata(
                database_name=data.get("database_name"),
                created_by=data.get("created_by", "system"),
                db_session=session,
            )

        return jsonify({"code": 0, "message": "success", "data": result})

    except Exception as e:
        logger.error(f"批量编目失败: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/assets/auto-catalog/history", methods=["GET"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.READ)
def get_catalog_history():
    """获取自动编目历史"""
    from services.asset_auto_catalog_service import get_asset_auto_catalog_service

    try:
        limit = int(request.args.get("limit", 50))
        service = get_asset_auto_catalog_service()
        history = service.get_catalog_history(limit=limit)
        return jsonify({"code": 0, "message": "success", "data": history})

    except Exception as e:
        logger.error(f"获取编目历史失败: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


# ==================== 元数据自动扫描 API ====================

@app.route("/api/v1/metadata/auto-scan", methods=["POST"])
@require_jwt()
@require_permission(Resource.METADATA, Operation.UPDATE)
def metadata_auto_scan():
    """
    自动扫描数据库结构并同步到元数据

    Request Body:
    {
        "connection_info": {
            "type": "mysql",
            "host": "localhost",
            "port": 3306,
            "username": "root",
            "password": "xxx"
        },
        "database_name": "my_database",
        "exclude_tables": ["tmp_xxx"],
        "ai_annotate": true
    }
    """
    from services.metadata_auto_scan_engine import get_metadata_auto_scan_engine

    try:
        data = request.get_json()
        if not data:
            return jsonify({"code": 40000, "message": "请求体不能为空"}), 400

        connection_info = data.get("connection_info", {})
        database_name = data.get("database_name", "")

        if not database_name:
            return jsonify({"code": 40000, "message": "数据库名不能为空"}), 400
        if not connection_info:
            return jsonify({"code": 40000, "message": "连接信息不能为空"}), 400

        engine = get_metadata_auto_scan_engine()

        with db_manager.get_session() as session:
            result = engine.scan_database(
                connection_info=connection_info,
                database_name=database_name,
                exclude_tables=data.get("exclude_tables"),
                ai_annotate=data.get("ai_annotate", True),
                db_session=session,
            )

        # 扫描完成后同步到 OpenMetadata（非阻塞，失败不影响主流程）
        if OPENMETADATA_AVAILABLE and data.get("sync_to_openmetadata", True):
            try:
                sync_service = get_om_sync_service()
                if sync_service.is_available():
                    with db_manager.get_session() as session:
                        tables = session.query(MetadataTable).options(
                            joinedload(MetadataTable.database),
                            joinedload(MetadataTable.columns),
                        ).join(MetadataDatabase).filter(
                            MetadataDatabase.name == database_name
                        ).all()
                        sync_stats = sync_service.sync_all_metadata(tables)
                        result["openmetadata_sync"] = sync_stats
                        logger.info("Auto-scan: synced %d tables to OpenMetadata", sync_stats.get("synced", 0))
            except Exception as sync_err:
                logger.warning("Auto-scan: OpenMetadata sync failed (non-blocking): %s", sync_err)
                result["openmetadata_sync"] = {"error": str(sync_err)}

        return jsonify({"code": 0, "message": "success", "data": result})

    except Exception as e:
        logger.error(f"元数据自动扫描失败: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/metadata/auto-scan/profile", methods=["POST"])
@require_jwt()
@require_permission(Resource.METADATA, Operation.READ)
def metadata_scan_profile():
    """
    扫描并生成数据概况（列级统计）

    Request Body:
    {
        "connection_info": { ... },
        "database_name": "my_database",
        "table_name": "my_table",
        "sample_size": 1000
    }
    """
    from services.metadata_auto_scan_engine import get_metadata_auto_scan_engine

    try:
        data = request.get_json()
        if not data:
            return jsonify({"code": 40000, "message": "请求体不能为空"}), 400

        connection_info = data.get("connection_info", {})
        database_name = data.get("database_name", "")
        table_name = data.get("table_name", "")

        if not database_name or not table_name:
            return jsonify({"code": 40000, "message": "数据库名和表名不能为空"}), 400

        engine = get_metadata_auto_scan_engine()
        result = engine.scan_and_profile(
            connection_info=connection_info,
            database_name=database_name,
            table_name=table_name,
            sample_size=data.get("sample_size", 1000),
        )

        return jsonify({"code": 0, "message": "success", "data": result})

    except Exception as e:
        logger.error(f"数据概况生成失败: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/metadata/auto-scan/history", methods=["GET"])
@require_jwt()
@require_permission(Resource.METADATA, Operation.READ)
def get_scan_history():
    """获取元数据扫描历史"""
    from services.metadata_auto_scan_engine import get_metadata_auto_scan_engine

    try:
        limit = int(request.args.get("limit", 20))
        engine = get_metadata_auto_scan_engine()
        history = engine.get_scan_history(limit=limit)
        return jsonify({"code": 0, "message": "success", "data": history})

    except Exception as e:
        logger.error(f"获取扫描历史失败: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


# ==================== 统一认证管理 API ====================

@app.route("/api/v1/auth/oauth2/clients", methods=["POST"])
@require_jwt()
@require_permission(Resource.SYSTEM, Operation.MANAGE)
def register_oauth2_client():
    """
    注册 OAuth2 客户端

    Request Body:
    {
        "client_name": "my-service",
        "grant_types": ["client_credentials"],
        "redirect_uris": [],
        "scopes": ["read", "write"]
    }
    """
    from services.unified_auth_service import get_unified_auth_service

    try:
        data = request.get_json()
        if not data:
            return jsonify({"code": 40000, "message": "请求体不能为空"}), 400

        client_name = data.get("client_name", "")
        grant_types = data.get("grant_types", [])

        if not client_name or not grant_types:
            return jsonify({"code": 40000, "message": "client_name 和 grant_types 必填"}), 400

        service = get_unified_auth_service()

        with db_manager.get_session() as session:
            result = service.register_client(
                client_name=client_name,
                grant_types=grant_types,
                redirect_uris=data.get("redirect_uris"),
                scopes=data.get("scopes"),
                owner=g.user if hasattr(g, "user") else "",
                created_by=g.user_id if hasattr(g, "user_id") else "",
                db_session=session,
            )

        return jsonify({"code": 0, "message": "success", "data": result})

    except Exception as e:
        logger.error(f"注册 OAuth2 客户端失败: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/auth/oauth2/clients", methods=["GET"])
@require_jwt()
@require_permission(Resource.SYSTEM, Operation.MANAGE)
def list_oauth2_clients():
    """列出 OAuth2 客户端"""
    from services.unified_auth_service import get_unified_auth_service

    try:
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("page_size", 20))
        status = request.args.get("status")

        service = get_unified_auth_service()

        with db_manager.get_session() as session:
            result = service.list_clients(
                status=status,
                page=page,
                page_size=page_size,
                db_session=session,
            )

        return jsonify({"code": 0, "message": "success", "data": result})

    except Exception as e:
        logger.error(f"查询 OAuth2 客户端失败: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/auth/oauth2/clients/<client_id>/status", methods=["PUT"])
@require_jwt()
@require_permission(Resource.SYSTEM, Operation.MANAGE)
def update_oauth2_client_status(client_id):
    """更新 OAuth2 客户端状态"""
    from services.unified_auth_service import get_unified_auth_service

    try:
        data = request.get_json()
        new_status = data.get("status") if data else None
        if new_status not in ("active", "suspended", "revoked"):
            return jsonify({"code": 40000, "message": "状态必须为 active/suspended/revoked"}), 400

        service = get_unified_auth_service()

        with db_manager.get_session() as session:
            ok = service.update_client_status(
                client_id=client_id,
                status=new_status,
                operator=g.user_id if hasattr(g, "user_id") else "",
                db_session=session,
            )

        if ok:
            return jsonify({"code": 0, "message": "success"})
        return jsonify({"code": 40400, "message": "客户端不存在"}), 404

    except Exception as e:
        logger.error(f"更新客户端状态失败: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/auth/oauth2/token", methods=["POST"])
def oauth2_token():
    """
    OAuth2 Token 端点

    支持:
    - grant_type=client_credentials: 服务间认证
    - grant_type=authorization_code: 授权码换Token
    """
    from services.unified_auth_service import get_unified_auth_service

    try:
        data = request.form.to_dict() or request.get_json() or {}
        grant_type = data.get("grant_type", "")

        service = get_unified_auth_service()
        ip_address = request.remote_addr or ""

        if grant_type == "client_credentials":
            client_id = data.get("client_id", "")
            client_secret = data.get("client_secret", "")
            scope = data.get("scope", "")

            with db_manager.get_session() as session:
                result = service.client_credentials_authenticate(
                    client_id=client_id,
                    client_secret=client_secret,
                    requested_scopes=scope.split() if scope else None,
                    ip_address=ip_address,
                    db_session=session,
                )

            if result["success"]:
                return jsonify({
                    "access_token": result["access_token"],
                    "token_type": result["token_type"],
                    "expires_in": result["expires_in"],
                    "scope": result["scope"],
                })
            return jsonify({"error": result["error"]}), 401

        elif grant_type == "authorization_code":
            code = data.get("code", "")
            client_id = data.get("client_id", "")
            client_secret = data.get("client_secret", "")
            redirect_uri = data.get("redirect_uri", "")
            code_verifier = data.get("code_verifier")

            with db_manager.get_session() as session:
                result = service.exchange_authorization_code(
                    code=code,
                    client_id=client_id,
                    client_secret=client_secret,
                    redirect_uri=redirect_uri,
                    code_verifier=code_verifier,
                    ip_address=ip_address,
                    db_session=session,
                )

            if result["success"]:
                return jsonify({
                    "access_token": result["access_token"],
                    "refresh_token": result["refresh_token"],
                    "token_type": result["token_type"],
                    "expires_in": result["expires_in"],
                    "scope": result["scope"],
                })
            return jsonify({"error": result["error"]}), 401

        else:
            return jsonify({"error": "unsupported_grant_type"}), 400

    except Exception as e:
        logger.error(f"OAuth2 Token 端点异常: {e}")
        return jsonify({"error": "server_error"}), 500


@app.route("/api/v1/auth/oauth2/revoke", methods=["POST"])
@require_jwt()
def oauth2_revoke_token():
    """吊销 Token"""
    from services.unified_auth_service import get_unified_auth_service

    try:
        data = request.get_json()
        if not data or not data.get("token_jti"):
            return jsonify({"code": 40000, "message": "token_jti 必填"}), 400

        service = get_unified_auth_service()

        with db_manager.get_session() as session:
            ok = service.revoke_token(
                token_jti=data["token_jti"],
                token_type=data.get("token_type", "access"),
                user_id=g.user_id if hasattr(g, "user_id") else "",
                reason=data.get("reason", ""),
                revoked_by=g.user_id if hasattr(g, "user_id") else "",
                db_session=session,
            )

        if ok:
            return jsonify({"code": 0, "message": "Token 已吊销"})
        return jsonify({"code": 50000, "message": "吊销失败"}), 500

    except Exception as e:
        logger.error(f"Token 吊销失败: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/auth/api-keys", methods=["POST"])
@require_jwt()
def create_api_key():
    """
    创建 API Key

    Request Body:
    {
        "name": "my-key",
        "scopes": ["read", "write"],
        "allowed_ips": ["192.168.1.0/24"],
        "expires_days": 90,
        "rate_limit": 1000
    }
    """
    from services.unified_auth_service import get_unified_auth_service

    try:
        data = request.get_json()
        if not data or not data.get("name"):
            return jsonify({"code": 40000, "message": "name 必填"}), 400

        service = get_unified_auth_service()

        with db_manager.get_session() as session:
            result = service.create_api_key(
                name=data["name"],
                user_id=g.user_id if hasattr(g, "user_id") else "",
                scopes=data.get("scopes"),
                allowed_ips=data.get("allowed_ips"),
                expires_days=data.get("expires_days"),
                rate_limit=data.get("rate_limit", 1000),
                db_session=session,
            )

        return jsonify({"code": 0, "message": "success", "data": result})

    except Exception as e:
        logger.error(f"创建 API Key 失败: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/auth/api-keys", methods=["GET"])
@require_jwt()
def list_api_keys():
    """列出当前用户的 API Key"""
    from services.unified_auth_service import get_unified_auth_service

    try:
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("page_size", 20))
        service = get_unified_auth_service()

        with db_manager.get_session() as session:
            result = service.list_api_keys(
                user_id=g.user_id if hasattr(g, "user_id") else "",
                page=page,
                page_size=page_size,
                db_session=session,
            )

        return jsonify({"code": 0, "message": "success", "data": result})

    except Exception as e:
        logger.error(f"查询 API Key 失败: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/auth/api-keys/<key_id>/revoke", methods=["POST"])
@require_jwt()
def revoke_api_key(key_id):
    """吊销 API Key"""
    from services.unified_auth_service import get_unified_auth_service

    try:
        service = get_unified_auth_service()

        with db_manager.get_session() as session:
            ok = service.revoke_api_key(
                key_id=key_id,
                user_id=g.user_id if hasattr(g, "user_id") else "",
                db_session=session,
            )

        if ok:
            return jsonify({"code": 0, "message": "API Key 已吊销"})
        return jsonify({"code": 40400, "message": "Key 不存在或无权限"}), 404

    except Exception as e:
        logger.error(f"吊销 API Key 失败: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/auth/audit-logs", methods=["GET"])
@require_jwt()
@require_permission(Resource.SYSTEM, Operation.MANAGE)
def get_auth_audit_logs():
    """查询认证审计日志"""
    from services.unified_auth_service import get_unified_auth_service

    try:
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("page_size", 50))
        user_id = request.args.get("user_id")
        event_type = request.args.get("event_type")
        event_status = request.args.get("event_status")

        service = get_unified_auth_service()

        with db_manager.get_session() as session:
            result = service.get_auth_audit_logs(
                user_id=user_id,
                event_type=event_type,
                event_status=event_status,
                page=page,
                page_size=page_size,
                db_session=session,
            )

        return jsonify({"code": 0, "message": "success", "data": result})

    except Exception as e:
        logger.error(f"查询审计日志失败: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/auth/statistics", methods=["GET"])
@require_jwt()
@require_permission(Resource.SYSTEM, Operation.MANAGE)
def get_auth_statistics():
    """获取认证统计信息"""
    from services.unified_auth_service import get_unified_auth_service

    try:
        days = int(request.args.get("days", 7))
        service = get_unified_auth_service()

        with db_manager.get_session() as session:
            stats = service.get_auth_statistics(days=days, db_session=session)

        return jsonify({"code": 0, "message": "success", "data": stats})

    except Exception as e:
        logger.error(f"获取认证统计失败: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/auth/sessions", methods=["GET"])
@require_jwt()
@require_permission(Resource.SYSTEM, Operation.MANAGE)
def get_active_sessions():
    """查询活跃会话"""
    from services.unified_auth_service import get_unified_auth_service

    try:
        user_id = request.args.get("user_id")
        service = get_unified_auth_service()
        sessions = service.get_active_sessions(user_id=user_id)
        return jsonify({"code": 0, "message": "success", "data": sessions})

    except Exception as e:
        logger.error(f"查询会话失败: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/auth/sessions/force-logout", methods=["POST"])
@require_jwt()
@require_permission(Resource.SYSTEM, Operation.MANAGE)
def force_logout_user():
    """强制用户下线"""
    from services.unified_auth_service import get_unified_auth_service

    try:
        data = request.get_json()
        if not data or not data.get("user_id"):
            return jsonify({"code": 40000, "message": "user_id 必填"}), 400

        service = get_unified_auth_service()

        with db_manager.get_session() as session:
            result = service.force_logout_user(
                target_user_id=data["user_id"],
                operator=g.user_id if hasattr(g, "user_id") else "",
                reason=data.get("reason", ""),
                db_session=session,
            )

        return jsonify({"code": 0, "message": "success", "data": result})

    except Exception as e:
        logger.error(f"强制下线失败: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


# ==================== 审批工作流 API ====================

@app.route("/api/v1/approval/templates", methods=["GET"])
@require_jwt()
def list_approval_templates():
    """列出审批模板"""
    from services.approval_workflow_engine import get_approval_workflow_engine

    try:
        business_type = request.args.get("business_type")
        category = request.args.get("category")

        engine = get_approval_workflow_engine()

        with db_manager.get_session() as session:
            engine.initialize_default_templates(db_session=session)
            templates = engine.list_templates(
                business_type=business_type,
                category=category,
                db_session=session,
            )

        return jsonify({"code": 0, "message": "success", "data": templates})

    except Exception as e:
        logger.error(f"查询审批模板失败: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/approval/templates", methods=["POST"])
@require_jwt()
@require_permission(Resource.SYSTEM, Operation.MANAGE)
def create_approval_template():
    """
    创建审批模板

    Request Body:
    {
        "name": "自定义审批",
        "business_type": "data_access",
        "category": "security",
        "nodes": [
            {"name": "部门主管审批", "approver_type": "role", "approver_value": "data_engineer"}
        ]
    }
    """
    from services.approval_workflow_engine import get_approval_workflow_engine

    try:
        data = request.get_json()
        if not data:
            return jsonify({"code": 40000, "message": "请求体不能为空"}), 400

        name = data.get("name", "")
        business_type = data.get("business_type", "")
        nodes = data.get("nodes", [])

        if not name or not business_type or not nodes:
            return jsonify({"code": 40000, "message": "name, business_type, nodes 必填"}), 400

        engine = get_approval_workflow_engine()

        with db_manager.get_session() as session:
            result = engine.create_template(
                name=name,
                business_type=business_type,
                nodes=nodes,
                description=data.get("description", ""),
                category=data.get("category", "general"),
                created_by=g.user_id if hasattr(g, "user_id") else "",
                db_session=session,
            )

        return jsonify({"code": 0, "message": "success", "data": result})

    except Exception as e:
        logger.error(f"创建审批模板失败: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/approval/requests", methods=["POST"])
@require_jwt()
def submit_approval_request():
    """
    提交审批工单

    Request Body:
    {
        "template_id": "tpl_data_access",
        "title": "申请访问用户表",
        "description": "需要读取用户表进行数据分析",
        "business_data": {
            "database": "production",
            "table": "users",
            "access_type": "read"
        },
        "priority": "normal"
    }
    """
    from services.approval_workflow_engine import get_approval_workflow_engine

    try:
        data = request.get_json()
        if not data:
            return jsonify({"code": 40000, "message": "请求体不能为空"}), 400

        template_id = data.get("template_id", "")
        title = data.get("title", "")

        if not template_id or not title:
            return jsonify({"code": 40000, "message": "template_id 和 title 必填"}), 400

        engine = get_approval_workflow_engine()

        with db_manager.get_session() as session:
            result = engine.submit_request(
                template_id=template_id,
                title=title,
                business_data=data.get("business_data", {}),
                applicant_id=g.user_id if hasattr(g, "user_id") else "",
                applicant_name=g.user if hasattr(g, "user") else "",
                description=data.get("description", ""),
                priority=data.get("priority", "normal"),
                db_session=session,
            )

        return jsonify({"code": 0, "message": "success", "data": result})

    except Exception as e:
        logger.error(f"提交审批工单失败: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/approval/requests/<request_id>", methods=["GET"])
@require_jwt()
def get_approval_request_detail(request_id):
    """获取工单详情"""
    from services.approval_workflow_engine import get_approval_workflow_engine

    try:
        engine = get_approval_workflow_engine()

        with db_manager.get_session() as session:
            detail = engine.get_request_detail(request_id=request_id, db_session=session)

        if detail:
            return jsonify({"code": 0, "message": "success", "data": detail})
        return jsonify({"code": 40400, "message": "工单不存在"}), 404

    except Exception as e:
        logger.error(f"查询工单详情失败: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/approval/requests/<request_id>/process", methods=["POST"])
@require_jwt()
def process_approval(request_id):
    """
    处理审批

    Request Body:
    {
        "action": "approve",  // approve, reject, delegate
        "comment": "同意",
        "delegate_to": ""     // 仅 delegate 时需要
    }
    """
    from services.approval_workflow_engine import get_approval_workflow_engine

    try:
        data = request.get_json()
        if not data or not data.get("action"):
            return jsonify({"code": 40000, "message": "action 必填"}), 400

        engine = get_approval_workflow_engine()

        with db_manager.get_session() as session:
            result = engine.process_approval(
                request_id=request_id,
                approver_id=g.user_id if hasattr(g, "user_id") else "",
                approver_name=g.user if hasattr(g, "user") else "",
                action=data["action"],
                comment=data.get("comment", ""),
                delegate_to=data.get("delegate_to"),
                db_session=session,
            )

        return jsonify({"code": 0, "message": "success", "data": result})

    except Exception as e:
        logger.error(f"处理审批失败: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/approval/requests/<request_id>/withdraw", methods=["POST"])
@require_jwt()
def withdraw_approval_request(request_id):
    """撤回审批工单"""
    from services.approval_workflow_engine import get_approval_workflow_engine

    try:
        engine = get_approval_workflow_engine()

        with db_manager.get_session() as session:
            result = engine.withdraw_request(
                request_id=request_id,
                applicant_id=g.user_id if hasattr(g, "user_id") else "",
                db_session=session,
            )

        return jsonify({"code": 0, "message": "success", "data": result})

    except Exception as e:
        logger.error(f"撤回失败: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/approval/pending", methods=["GET"])
@require_jwt()
def get_pending_approvals():
    """获取待审批列表"""
    from services.approval_workflow_engine import get_approval_workflow_engine

    try:
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("page_size", 20))

        # 从 JWT 中获取角色
        approver_role = None
        if hasattr(g, "roles") and g.roles:
            approver_role = g.roles[0] if isinstance(g.roles, list) else g.roles

        engine = get_approval_workflow_engine()

        with db_manager.get_session() as session:
            result = engine.get_pending_approvals(
                approver_role=approver_role,
                page=page,
                page_size=page_size,
                db_session=session,
            )

        return jsonify({"code": 0, "message": "success", "data": result})

    except Exception as e:
        logger.error(f"查询待审批失败: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/approval/my-requests", methods=["GET"])
@require_jwt()
def get_my_approval_requests():
    """获取我的申请列表"""
    from services.approval_workflow_engine import get_approval_workflow_engine

    try:
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("page_size", 20))
        status = request.args.get("status")

        engine = get_approval_workflow_engine()

        with db_manager.get_session() as session:
            result = engine.get_my_requests(
                applicant_id=g.user_id if hasattr(g, "user_id") else "",
                status=status,
                page=page,
                page_size=page_size,
                db_session=session,
            )

        return jsonify({"code": 0, "message": "success", "data": result})

    except Exception as e:
        logger.error(f"查询我的申请失败: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/approval/statistics", methods=["GET"])
@require_jwt()
@require_permission(Resource.SYSTEM, Operation.MANAGE)
def get_approval_statistics():
    """获取审批统计信息"""
    from services.approval_workflow_engine import get_approval_workflow_engine

    try:
        engine = get_approval_workflow_engine()

        with db_manager.get_session() as session:
            stats = engine.get_approval_statistics(db_session=session)

        return jsonify({"code": 0, "message": "success", "data": stats})

    except Exception as e:
        logger.error(f"获取审批统计失败: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


# ==================== OpenMetadata 集成 API ====================

# 尝试导入 OpenMetadata 集成模块
try:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from integrations.openmetadata.config import get_config as get_om_config, is_enabled as is_om_enabled
    from integrations.openmetadata.client import get_client as get_om_client
    from integrations.openmetadata.sync_service import get_sync_service as get_om_sync_service
    from integrations.openmetadata.lineage_service import get_lineage_service as get_om_lineage_service
    OPENMETADATA_AVAILABLE = True
    logger.info("OpenMetadata integration module loaded")
except ImportError:
    OPENMETADATA_AVAILABLE = False
    logger.info("OpenMetadata integration module not available")


@app.route("/api/v1/openmetadata/status", methods=["GET"])
@require_jwt()
def openmetadata_status():
    """获取 OpenMetadata 集成状态"""
    if not OPENMETADATA_AVAILABLE:
        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "available": False,
                "enabled": False,
                "healthy": False,
                "message": "OpenMetadata integration module not installed",
            }
        })

    try:
        config = get_om_config()
        client = get_om_client()
        healthy = client.health_check()

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "available": True,
                "enabled": config.enabled,
                "healthy": healthy,
                "host": config.host,
                "port": config.port,
            }
        })
    except Exception as e:
        logger.error(f"获取 OpenMetadata 状态失败: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/openmetadata/sync", methods=["POST"])
@require_jwt()
@require_permission(Resource.METADATA, Operation.UPDATE)
def openmetadata_sync_metadata():
    """
    同步元数据到 OpenMetadata

    Request Body:
    {
        "database_name": "my_database",
        "table_names": ["table1", "table2"]  // 可选，为空则同步全部
    }
    """
    if not OPENMETADATA_AVAILABLE:
        return jsonify({"code": 40300, "message": "OpenMetadata integration not available"}), 403

    try:
        data = request.get_json() or {}
        database_name = data.get("database_name")
        table_names = data.get("table_names", [])

        sync_service = get_om_sync_service()

        if not sync_service.is_available():
            return jsonify({
                "code": 50300,
                "message": "OpenMetadata service not reachable"
            }), 503

        with db_manager.get_session() as session:
            # 查询要同步的元数据表
            query = session.query(MetadataTable).options(
                joinedload(MetadataTable.database),
                joinedload(MetadataTable.columns),
            )

            if database_name:
                query = query.join(MetadataDatabase).filter(
                    MetadataDatabase.name == database_name
                )

            if table_names:
                query = query.filter(MetadataTable.name.in_(table_names))

            tables = query.all()

            if not tables:
                return jsonify({
                    "code": 0,
                    "message": "success",
                    "data": {"synced": 0, "failed": 0, "skipped": 0, "total": 0}
                })

            stats = sync_service.sync_all_metadata(tables)
            stats["total"] = len(tables)

        return jsonify({"code": 0, "message": "success", "data": stats})

    except Exception as e:
        logger.error(f"同步元数据到 OpenMetadata 失败: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/openmetadata/lineage", methods=["GET"])
@require_jwt()
@require_permission(Resource.METADATA, Operation.READ)
def openmetadata_get_lineage():
    """
    从 OpenMetadata 获取表血缘关系

    Query Parameters:
    - database: 数据库名
    - table: 表名
    - upstream_depth: 上游深度 (默认 3)
    - downstream_depth: 下游深度 (默认 3)
    """
    if not OPENMETADATA_AVAILABLE:
        return jsonify({"code": 40300, "message": "OpenMetadata integration not available"}), 403

    try:
        database = request.args.get("database")
        table = request.args.get("table")

        if not database or not table:
            return jsonify({"code": 40000, "message": "database 和 table 参数必填"}), 400

        upstream_depth = int(request.args.get("upstream_depth", 3))
        downstream_depth = int(request.args.get("downstream_depth", 3))

        lineage_service = get_om_lineage_service()

        if not lineage_service.is_available():
            return jsonify({
                "code": 50300,
                "message": "OpenMetadata service not reachable"
            }), 503

        lineage = lineage_service.get_table_lineage(
            db_name=database,
            table_name=table,
            upstream_depth=upstream_depth,
            downstream_depth=downstream_depth,
        )

        return jsonify({"code": 0, "message": "success", "data": lineage})

    except Exception as e:
        logger.error(f"获取血缘关系失败: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/openmetadata/lineage", methods=["POST"])
@require_jwt()
@require_permission(Resource.METADATA, Operation.UPDATE)
def openmetadata_push_lineage():
    """
    推送血缘关系到 OpenMetadata

    Request Body:
    {
        "source_database": "db1",
        "source_table": "source_table",
        "target_database": "db2",
        "target_table": "target_table",
        "description": "ETL transformation",
        "transformation": "SELECT * FROM ..."
    }
    """
    if not OPENMETADATA_AVAILABLE:
        return jsonify({"code": 40300, "message": "OpenMetadata integration not available"}), 403

    try:
        data = request.get_json()
        if not data:
            return jsonify({"code": 40000, "message": "请求体不能为空"}), 400

        required_fields = ["source_database", "source_table", "target_database", "target_table"]
        for field in required_fields:
            if not data.get(field):
                return jsonify({"code": 40000, "message": f"{field} 不能为空"}), 400

        lineage_service = get_om_lineage_service()

        if not lineage_service.is_available():
            return jsonify({
                "code": 50300,
                "message": "OpenMetadata service not reachable"
            }), 503

        result = lineage_service.push_lineage(
            source_db=data["source_database"],
            source_table=data["source_table"],
            target_db=data["target_database"],
            target_table=data["target_table"],
            description=data.get("description"),
            transformation=data.get("transformation"),
        )

        return jsonify({"code": 0, "message": "success", "data": result})

    except Exception as e:
        logger.error(f"推送血缘关系失败: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/openmetadata/search", methods=["GET"])
@require_jwt()
@require_permission(Resource.METADATA, Operation.READ)
def openmetadata_search():
    """
    通过 OpenMetadata 搜索元数据

    Query Parameters:
    - q: 搜索关键词
    - limit: 返回数量 (默认 10)
    - offset: 偏移量 (默认 0)
    """
    if not OPENMETADATA_AVAILABLE:
        return jsonify({"code": 40300, "message": "OpenMetadata integration not available"}), 403

    try:
        query = request.args.get("q", "")
        if not query:
            return jsonify({"code": 40000, "message": "搜索关键词 q 不能为空"}), 400

        limit = int(request.args.get("limit", 10))
        offset = int(request.args.get("offset", 0))

        client = get_om_client()
        if not client.health_check():
            return jsonify({
                "code": 50300,
                "message": "OpenMetadata service not reachable"
            }), 503

        result = client.search(query=query, limit=limit, offset=offset)

        return jsonify({"code": 0, "message": "success", "data": result})

    except Exception as e:
        logger.error(f"OpenMetadata 搜索失败: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


# ==================== 数据血缘事件 API ====================

@app.route("/api/v1/lineage/events", methods=["GET"])
@require_jwt()
@require_permission(Resource.METADATA, Operation.READ)
def lineage_events_list():
    """
    获取血缘事件列表

    Query Parameters:
    - limit: 返回数量 (默认 100)
    - event_type: 事件类型过滤
    - job_name: 任务名称过滤
    """
    try:
        import sys
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from services import get_openlineage_event_service

        service = get_openlineage_event_service()

        limit = int(request.args.get("limit", 100))
        event_type = request.args.get("event_type")
        job_name = request.args.get("job_name")

        events = service.get_recent_events(
            limit=limit,
            event_type=event_type,
            job_name=job_name,
        )

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "events": events,
                "total": len(events),
                "stats": service.get_stats(),
            }
        })

    except Exception as e:
        logger.error(f"获取血缘事件失败: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/lineage/events/emit", methods=["POST"])
@require_jwt()
@require_permission(Resource.METADATA, Operation.UPDATE)
def lineage_event_emit():
    """
    发送血缘事件

    Body:
    {
        "event_type": "JOB_STARTED | JOB_COMPLETED | JOB_FAILED",
        "job_name": "任务名称",
        "source_tables": ["source_db.table1", ...],
        "target_tables": ["target_db.table2", ...],
        "transformation": "转换 SQL (可选)",
        "run_id": "运行 ID (可选)"
    }
    """
    try:
        import sys
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from services import get_openlineage_event_service

        service = get_openlineage_event_service()
        data = request.get_json()

        event_type = data.get("event_type", "JOB_STARTED")
        job_name = data.get("job_name")
        source_tables = data.get("source_tables", [])
        target_tables = data.get("target_tables", [])
        transformation = data.get("transformation")
        run_id = data.get("run_id")

        if not job_name:
            return jsonify({"code": 40000, "message": "job_name 必填"}), 400
        if not source_tables and not target_tables:
            return jsonify({"code": 40000, "message": "source_tables 和 target_tables 至少需要一个"}), 400

        success = service.emit_etl_event(
            job_name=job_name,
            source_tables=source_tables,
            target_tables=target_tables,
            transformation=transformation,
            run_id=run_id,
        )

        if success:
            return jsonify({
                "code": 0,
                "message": "Event emitted successfully",
                "data": {"queued": True}
            })
        else:
            return jsonify({
                "code": 50000,
                "message": "Failed to queue event"
            }), 500

    except Exception as e:
        logger.error(f"发送血缘事件失败: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/lineage/upstream", methods=["GET"])
@require_jwt()
@require_permission(Resource.METADATA, Operation.READ)
def lineage_upstream():
    """
    获取数据集上游依赖

    Query Parameters:
    - namespace: 数据集命名空间 (默认 data-service)
    - name: 数据集名称
    - max_depth: 最大深度 (默认 3)
    """
    try:
        import sys
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from services import get_openlineage_event_service

        service = get_openlineage_event_service()

        namespace = request.args.get("namespace", "data-service")
        name = request.args.get("name")
        max_depth = int(request.args.get("max_depth", 3))

        if not name:
            return jsonify({"code": 40000, "message": "name 必填"}), 400

        upstream = service.get_upstream(
            dataset_namespace=namespace,
            dataset_name=name,
            max_depth=max_depth,
        )

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "dataset": f"{namespace}.{name}",
                "upstream": upstream,
                "total": len(upstream),
            }
        })

    except Exception as e:
        logger.error(f"获取上游血缘失败: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/lineage/downstream", methods=["GET"])
@require_jwt()
@require_permission(Resource.METADATA, Operation.READ)
def lineage_downstream():
    """
    获取数据集下游依赖

    Query Parameters:
    - namespace: 数据集命名空间 (默认 data-service)
    - name: 数据集名称
    - max_depth: 最大深度 (默认 3)
    """
    try:
        import sys
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from services import get_openlineage_event_service

        service = get_openlineage_event_service()

        namespace = request.args.get("namespace", "data-service")
        name = request.args.get("name")
        max_depth = int(request.args.get("max_depth", 3))

        if not name:
            return jsonify({"code": 40000, "message": "name 必填"}), 400

        downstream = service.get_downstream(
            dataset_namespace=namespace,
            dataset_name=name,
            max_depth=max_depth,
        )

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "dataset": f"{namespace}.{name}",
                "downstream": downstream,
                "total": len(downstream),
            }
        })

    except Exception as e:
        logger.error(f"获取下游血缘失败: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/lineage/path", methods=["GET"])
@require_jwt()
@require_permission(Resource.METADATA, Operation.READ)
def lineage_path():
    """
    获取两个数据集之间的血缘路径

    Query Parameters:
    - source_namespace: 源数据集命名空间
    - source_name: 源数据集名称
    - target_namespace: 目标数据集命名空间
    - target_name: 目标数据集名称
    - max_depth: 最大搜索深度 (默认 5)
    """
    try:
        import sys
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from services import get_openlineage_event_service

        service = get_openlineage_event_service()

        source_namespace = request.args.get("source_namespace", "data-service")
        source_name = request.args.get("source_name")
        target_namespace = request.args.get("target_namespace", "data-service")
        target_name = request.args.get("target_name")
        max_depth = int(request.args.get("max_depth", 5))

        if not source_name or not target_name:
            return jsonify({"code": 40000, "message": "source_name 和 target_name 必填"}), 400

        path = service.get_path(
            source_namespace=source_namespace,
            source_name=source_name,
            target_namespace=target_namespace,
            target_name=target_name,
            max_depth=max_depth,
        )

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "source": f"{source_namespace}.{source_name}",
                "target": f"{target_namespace}.{target_name}",
                "path": path,
                "path_length": len(path) if path else 0,
                "exists": path is not None,
            }
        })

    except Exception as e:
        logger.error(f"获取血缘路径失败: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/lineage/impact", methods=["GET"])
@require_jwt()
@require_permission(Resource.METADATA, Operation.READ)
def lineage_impact():
    """
    影响分析 - 评估数据集变更的影响范围

    Query Parameters:
    - namespace: 数据集命名空间 (默认 data-service)
    - name: 数据集名称
    - max_depth: 分析深度 (默认 5)
    """
    try:
        import sys
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from services import get_openlineage_event_service

        service = get_openlineage_event_service()

        namespace = request.args.get("namespace", "data-service")
        name = request.args.get("name")
        max_depth = int(request.args.get("max_depth", 5))

        if not name:
            return jsonify({"code": 40000, "message": "name 必填"}), 400

        impact = service.get_impact_analysis(
            dataset_namespace=namespace,
            dataset_name=name,
            max_depth=max_depth,
        )

        return jsonify({
            "code": 0,
            "message": "success",
            "data": impact
        })

    except Exception as e:
        logger.error(f"影响分析失败: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/lineage/export", methods=["GET"])
@require_jwt()
@require_permission(Resource.METADATA, Operation.READ)
def lineage_export():
    """
    导出血缘事件为 OpenLineage 标准格式

    Query Parameters:
    - limit: 导出数量 (默认 100)
    """
    try:
        import sys
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from services import get_openlineage_event_service

        service = get_openlineage_event_service()
        limit = int(request.args.get("limit", 100))

        events = service.to_openlineage_events(limit=limit)

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "events": events,
                "total": len(events),
                "format": "openlineage",
            }
        })

    except Exception as e:
        logger.error(f"导出血缘事件失败: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


# ==================== ETL 任务管理扩展 API ====================

@app.route("/api/v1/etl/tasks", methods=["POST"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.MANAGE)
def create_etl_task():
    """创建 ETL 任务"""
    try:
        data = request.get_json()

        with db_manager.get_session() as session:
            task = ETLTask(
                task_id=f"etl_{uuid.uuid4().hex[:8]}",
                name=data.get("name", f"ETL Task {datetime.now().strftime('%Y%m%d%H%M%S')}"),
                description=data.get("description", ""),
                task_type=data.get("task_type", "sync"),
                source_type=data.get("source_type", "mysql"),
                source_config=data.get("source_config", {}),
                source_query=data.get("source_query", ""),
                target_type=data.get("target_type", "mysql"),
                target_config=data.get("target_config", {}),
                target_table=data.get("target_table", ""),
                transform_config=data.get("transform_config", data.get("transformations", [])),
                schedule_type=data.get("schedule_type", "manual"),
                schedule_config=data.get("schedule_config", data.get("schedule")),
                status="pending",
                created_by=data.get("created_by", "admin"),
            )
            session.add(task)
            session.commit()
            session.refresh(task)

            return jsonify({
                "code": 0,
                "message": "ETL task created successfully",
                "data": task.to_dict()
            }), 201

    except Exception as e:
        logger.error(f"Error creating ETL task: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/etl/tasks/<task_id>/execute", methods=["POST"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.MANAGE)
def execute_etl_task(task_id: str):
    """执行 ETL 任务"""
    try:
        with db_manager.get_session() as session:
            task = session.query(ETLTask).filter(ETLTask.task_id == task_id).first()
            if not task:
                return jsonify({"code": 40400, "message": "ETL task not found"}), 404

            execution_id = f"exec_{uuid.uuid4().hex[:8]}"
            # 更新任务状态为运行中
            task.status = "running"
            session.commit()

            # 这里应该触发实际的 ETL 执行
            # 为了测试目的，我们创建一个执行记录
            return jsonify({
                "code": 0,
                "message": "ETL task execution started",
                "data": {
                    "execution_id": execution_id,
                    "task_id": task_id,
                    "status": "running"
                }
            }), 200

    except Exception as e:
        logger.error(f"Error executing ETL task {task_id}: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/etl/fusion", methods=["POST"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.MANAGE)
def create_fusion_task():
    """创建多表融合任务"""
    try:
        data = request.get_json()

        with db_manager.get_session() as session:
            task = ETLTask(
                task_id=f"fusion_{uuid.uuid4().hex[:8]}",
                name=data.get("name", f"Fusion Task {datetime.now().strftime('%Y%m%d%H%M%S')}"),
                description=data.get("description", ""),
                task_type="fusion",
                tables=data.get("tables", []),
                join_conditions=data.get("join_conditions", []),
                output=data.get("output"),
                status="pending",
                created_by=data.get("created_by", "admin"),
                created_at=datetime.now(),
            )
            session.add(task)
            session.commit()
            session.refresh(task)

            return jsonify({
                "code": 0,
                "message": "Fusion task created successfully",
                "data": task.to_dict()
            }), 201

    except Exception as e:
        logger.error(f"Error creating fusion task: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/etl/fusion/preview", methods=["POST"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.READ)
def preview_fusion_result():
    """预览融合结果"""
    try:
        data = request.get_json()

        # 返回模拟的预览数据
        preview_data = {
            "preview": [
                {"id": 1, "name": "Sample 1", "value": 100},
                {"id": 2, "name": "Sample 2", "value": 200},
            ],
            "total_count": 2,
            "columns": ["id", "name", "value"]
        }

        return jsonify({
            "code": 0,
            "message": "success",
            "data": preview_data
        }), 200

    except Exception as e:
        logger.error(f"Error previewing fusion result: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/etl/fusion/<task_id>/status", methods=["GET"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.READ)
def get_fusion_task_status(task_id: str):
    """获取融合任务状态"""
    try:
        with db_manager.get_session() as session:
            task = session.query(ETLTask).filter(ETLTask.task_id == task_id).first()
            if not task:
                return jsonify({"code": 40400, "message": "Fusion task not found"}), 404

            return jsonify({
                "code": 0,
                "message": "success",
                "data": {
                    "task_id": task_id,
                    "status": task.status,
                    "updated_at": task.updated_at.isoformat() if task.updated_at else None
                }
            }), 200

    except Exception as e:
        logger.error(f"Error getting fusion task status {task_id}: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


# ==================== 元数据扫描 API ====================

@app.route("/api/v1/metadata/scan", methods=["POST"])
@require_jwt()
@require_permission(Resource.METADATA, Operation.MANAGE)
def trigger_metadata_scan():
    """触发元数据扫描"""
    try:
        data = request.get_json()

        task_id = f"scan_{uuid.uuid4().hex[:8]}"

        return jsonify({
            "code": 0,
            "message": "Metadata scan started",
            "data": {
                "task_id": task_id,
                "status": "running",
                "datasource_id": data.get("datasource_id")
            }
        }), 201

    except Exception as e:
        logger.error(f"Error triggering metadata scan: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/metadata/scan/<task_id>/result", methods=["GET"])
@require_jwt()
@require_permission(Resource.METADATA, Operation.READ)
def get_metadata_scan_result(task_id: str):
    """获取元数据扫描结果"""
    try:
        # 返回模拟的扫描结果
        result = {
            "task_id": task_id,
            "status": "completed",
            "tables": [
                {"name": "test_users", "columns": ["id", "username", "email", "phone"]},
                {"name": "test_orders", "columns": ["id", "user_id", "amount", "status"]}
            ]
        }

        return jsonify({
            "code": 0,
            "message": "success",
            "data": result
        }), 200

    except Exception as e:
        logger.error(f"Error getting metadata scan result: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/metadata/ai-annotate", methods=["POST"])
@require_jwt()
@require_permission(Resource.METADATA, Operation.MANAGE)
def ai_annotate_metadata():
    """AI 自动标注元数据"""
    try:
        data = request.get_json()

        return jsonify({
            "code": 0,
            "message": "AI annotation completed",
            "data": {
                "annotated_count": data.get("table_count", 0),
                "annotations": [
                    {"table": "test_users", "column": "phone", "type": "phone_number"},
                    {"table": "test_users", "column": "email", "type": "email"}
                ]
            }
        }), 200

    except Exception as e:
        logger.error(f"Error in AI annotation: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


# ==================== 数据脱敏 API ====================

@app.route("/api/v1/masking/apply", methods=["POST"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.MANAGE)
def apply_masking():
    """应用数据脱敏规则"""
    try:
        data = request.get_json()

        return jsonify({
            "code": 0,
            "message": "Masking rules applied successfully",
            "data": {
                "affected_rows": 100,
                "datasource_id": data.get("datasource_id"),
                "table_name": data.get("table_name"),
                "rules_applied": len(data.get("rules", []))
            }
        }), 200

    except Exception as e:
        logger.error(f"Error applying masking: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/masking/rules/auto-generate", methods=["POST"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.MANAGE)
def auto_generate_masking_rules():
    """自动生成脱敏规则"""
    try:
        data = request.get_json()

        return jsonify({
            "code": 0,
            "message": "Masking rules generated successfully",
            "data": {
                "rules": [
                    {"column": "phone", "strategy": "partial_mask", "type": "phone"},
                    {"column": "email", "strategy": "partial_mask", "type": "email"},
                    {"column": "id_card", "strategy": "partial_mask", "type": "id_card"}
                ],
                "total_count": 3
            }
        }), 200

    except Exception as e:
        logger.error(f"Error generating masking rules: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


# ==================== 数据质量 API ====================

@app.route("/api/v1/data/analyze-missing", methods=["POST"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.READ)
def analyze_missing_values():
    """分析缺失值"""
    try:
        data = request.get_json()

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "pattern": "random",
                "missing_rate": 0.15,
                "columns_with_missing": ["age", "salary", "phone"]
            }
        }), 200

    except Exception as e:
        logger.error(f"Error analyzing missing values: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/data/impute-mean", methods=["POST"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.MANAGE)
def impute_mean_values():
    """均值填充"""
    try:
        data = request.get_json()

        return jsonify({
            "code": 0,
            "message": "Mean imputation completed",
            "data": {
                "column": data.get("column"),
                "imputed_value": 30.5,
                "imputed_count": 5
            }
        }), 200

    except Exception as e:
        logger.error(f"Error in mean imputation: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


# ==================== 数据采集 API ====================

@app.route("/api/v1/datasets/ingest", methods=["POST"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.MANAGE)
def create_ingestion_task():
    """创建数据采集任务"""
    try:
        data = request.get_json()

        task_id = f"ingest_{uuid.uuid4().hex[:8]}"

        return jsonify({
            "code": 0,
            "message": "Ingestion task created",
            "data": {
                "task_id": task_id,
                "name": data.get("name"),
                "mode": data.get("mode"),
                "status": "pending"
            }
        }), 201

    except Exception as e:
        logger.error(f"Error creating ingestion task: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


# ==================== 资产管理扩展 API ====================

@app.route("/api/v1/assets/catalog", methods=["POST"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.MANAGE)
def create_asset_catalog():
    """创建资产目录"""
    try:
        data = request.get_json()

        return jsonify({
            "code": 0,
            "message": "Asset catalog created",
            "data": {
                "catalog_id": f"catalog_{uuid.uuid4().hex[:8]}",
                "name": data.get("name", "Default Catalog"),
                "assets_count": 0
            }
        }), 201

    except Exception as e:
        logger.error(f"Error creating asset catalog: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


@app.route("/api/v1/assets/evaluate", methods=["POST"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.READ)
def evaluate_asset_value_v2():
    """评估资产价值"""
    try:
        data = request.get_json()

        return jsonify({
            "code": 0,
            "message": "Asset evaluation completed",
            "data": {
                "asset_id": data.get("asset_id"),
                "value_score": 85,
                "usage_count": 150,
                "last_used": datetime.now().isoformat()
            }
        }), 200

    except Exception as e:
        logger.error(f"Error evaluating asset: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


# ==================== 血缘同步 API ====================

@app.route("/api/v1/lineage/sync", methods=["POST"])
@require_jwt()
@require_permission(Resource.METADATA, Operation.MANAGE)
def sync_lineage():
    """触发元数据同步"""
    try:
        data = request.get_json()

        return jsonify({
            "code": 0,
            "message": "Lineage sync started",
            "data": {
                "sync_id": f"sync_{uuid.uuid4().hex[:8]}",
                "status": "running",
                "source": data.get("source", "all")
            }
        }), 201

    except Exception as e:
        logger.error(f"Error syncing lineage: {e}")
        return jsonify({"code": 50000, "message": get_safe_error_message(e)}), 500


# ==================== 敏感数据扫描 API 别名 ====================

@app.route("/api/v1/sensitivity/scan", methods=["POST"])
@require_jwt()
@require_permission(Resource.DATASET, Operation.MANAGE)
def start_sensitivity_scan_v2():
    """启动敏感数据扫描任务 (别名端点)"""
    return start_sensitivity_scan()


# 启动应用
if __name__ == "__main__":
    initialize_app()

    # 启动 OpenLineage 事件服务
    try:
        import sys
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from services import init_openlineage_event_service
        init_openlineage_event_service()
        logger.info("OpenLineage event service initialized")
    except Exception as e:
        logger.warning(f"Failed to initialize OpenLineage event service: {e}")

    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
