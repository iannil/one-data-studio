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
    Dataset, DatasetColumn, DatasetVersion,
    MetadataDatabase, MetadataTable, MetadataColumn, FileUpload
)
from storage import minio_client, init_storage

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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


# ==================== 数据集管理 API ====================

@app.route("/api/v1/datasets", methods=["GET"])
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
        return jsonify({"code": 50000, "message": f"Internal error: {str(e)}"}), 500


@app.route("/api/v1/datasets/<dataset_id>", methods=["GET"])
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
        return jsonify({"code": 50000, "message": f"Internal error: {str(e)}"}), 500


@app.route("/api/v1/datasets", methods=["POST"])
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
        return jsonify({"code": 50000, "message": f"Internal error: {str(e)}"}), 500


@app.route("/api/v1/datasets/<dataset_id>", methods=["PUT"])
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
        return jsonify({"code": 50000, "message": f"Internal error: {str(e)}"}), 500


@app.route("/api/v1/datasets/<dataset_id>", methods=["DELETE"])
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
        return jsonify({"code": 50000, "message": f"Internal error: {str(e)}"}), 500


@app.route("/api/v1/datasets/<dataset_id>/credentials", methods=["POST"])
def get_credentials(dataset_id: str):
    """获取数据集访问凭证"""
    try:
        with db_manager.get_session() as session:
            dataset = session.query(Dataset).filter(Dataset.dataset_id == dataset_id).first()
            if not dataset:
                return jsonify({
                    "code": 40401,
                    "message": f"Dataset {dataset_id} not found"
                }), 404

            # 解析存储路径获取桶名
            if dataset.storage_path.startswith('s3://'):
                path = dataset.storage_path[5:]
                parts = path.split('/', 1)
                bucket = parts[0] if parts else minio_client.default_bucket
            else:
                bucket = minio_client.default_bucket

            # 生成预签名 URL（有效期 1 小时）
            return jsonify({
                "code": 0,
                "message": "success",
                "data": {
                    "access_key": os.getenv('MINIO_ACCESS_KEY', 'minioadmin'),
                    "secret_key": os.getenv('MINIO_SECRET_KEY', 'minioadmin'),
                    "endpoint": os.getenv('MINIO_ENDPOINT', 'minio.one-data-infra.svc.cluster.local:9000'),
                    "bucket": bucket,
                    "expires_at": (datetime.utcnow().replace(hour=23, minute=59, second=59)).isoformat() + "Z"
                }
            })

    except Exception as e:
        logger.error(f"Error getting credentials: {e}")
        return jsonify({"code": 50000, "message": f"Internal error: {str(e)}"}), 500


@app.route("/api/v1/datasets/<dataset_id>/upload-url", methods=["POST"])
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
        return jsonify({"code": 50000, "message": f"Internal error: {str(e)}"}), 500


@app.route("/api/v1/datasets/<dataset_id>/preview", methods=["GET"])
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
        return jsonify({"code": 50000, "message": f"Internal error: {str(e)}"}), 500


# ==================== 元数据管理 API ====================

@app.route("/api/v1/metadata/databases", methods=["GET"])
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
        return jsonify({"code": 50000, "message": f"Internal error: {str(e)}"}), 500


@app.route("/api/v1/metadata/databases/<database>/tables", methods=["GET"])
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
        return jsonify({"code": 50000, "message": f"Internal error: {str(e)}"}), 500


@app.route("/api/v1/metadata/databases/<database>/tables/<table>", methods=["GET"])
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
        return jsonify({"code": 50000, "message": f"Internal error: {str(e)}"}), 500


# ==================== 数据集版本管理 API ====================

@app.route("/api/v1/datasets/<dataset_id>/versions", methods=["GET"])
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
        return jsonify({"code": 50000, "message": f"Internal error: {str(e)}"}), 500


@app.route("/api/v1/datasets/<dataset_id>/versions", methods=["POST"])
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
        return jsonify({"code": 50000, "message": f"Internal error: {str(e)}"}), 500


# 启动应用
if __name__ == "__main__":
    initialize_app()
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
