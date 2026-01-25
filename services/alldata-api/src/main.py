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

# 添加 src 目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

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
    ETLTask, QualityRule, QualityAlert, OfflineTask, FlinkJob
)
from storage import minio_client, init_storage

# 添加父目录以导入 auth 模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
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
        "service": "alldata-api",
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


# 启动应用
if __name__ == "__main__":
    initialize_app()
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
