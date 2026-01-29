"""
CDC API 路由
提供 CDC 任务管理、监控和配置的 REST API
"""

import logging
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
from flask import Blueprint, jsonify, request, g

# 导入 SeaTunnel 服务
try:
    from services.seatunnel_service import (
        get_seatunnel_service,
        SeaTunnelSourceType,
        SeaTunnelSinkType,
        CDCSourceConfig,
        CDCTargetConfig,
    )
except ImportError:
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
    from services.data_api.services.seatunnel_service import (
        get_seatunnel_service,
        SeaTunnelSourceType,
        SeaTunnelSinkType,
        CDCSourceConfig,
        CDCTargetConfig,
    )

logger = logging.getLogger(__name__)

# 创建 Blueprint
cdc_bp = Blueprint('cdc', __name__, url_prefix='/api/v1/cdc')


# ==================== 认证装饰器 ====================

def require_auth(f):
    """认证装饰器（简化版）"""
    def decorator(*args, **kwargs):
        g.user_id = request.headers.get('X-User-Id', 'system')
        g.username = request.headers.get('X-Username', 'admin')
        return f(*args, **kwargs)
    return decorator


# ==================== CDC 任务管理 ====================

@cdc_bp.route('/jobs', methods=['POST'])
@require_auth
def create_cdc_job():
    """
    创建 CDC 任务

    Body:
    {
        "job_name": "任务名称",
        "description": "描述",
        "source": {
            "type": "MySQL-CDC",
            "host": "localhost",
            "port": 3306,
            "username": "user",
            "password": "pass",
            "database": "db",
            "tables": ["table1", "table2"]
        },
        "sink": {
            "type": "ClickHouse",
            "host": "localhost",
            "port": 8123,
            "database": "db",
            "table": "table",
            "username": "user",
            "password": "pass"
        },
        "transforms": [...],
        "parallelism": 2
    }
    """
    try:
        data = request.get_json()

        # 解析源配置
        source_type = SeaTunnelSourceType(data['source']['type'])
        source = CDCSourceConfig(
            source_type=source_type,
            host=data['source']['host'],
            port=data['source']['port'],
            username=data['source']['username'],
            password=data['source']['password'],
            database=data['source']['database'],
            schema=data['source'].get('schema', ''),
            tables=data['source'].get('tables', []),
            server_id=data['source'].get('server_id', 5700),
        )

        # 解析目标配置
        sink_type = SeaTunnelSinkType(data['sink']['type'])
        sink = CDCTargetConfig(
            sink_type=sink_type,
            host=data['sink'].get('host', ''),
            port=data['sink'].get('port', 0),
            database=data['sink'].get('database', ''),
            table=data['sink'].get('table', ''),
            username=data['sink'].get('username', ''),
            password=data['sink'].get('password', ''),
            endpoint=data['sink'].get('endpoint', ''),
            bucket=data['sink'].get('bucket', ''),
            path=data['sink'].get('path', ''),
            access_key=data['sink'].get('access_key', ''),
            secret_key=data['sink'].get('secret_key', ''),
            primary_key=data['sink'].get('primary_key', 'id'),
        )

        # 创建任务
        service = get_seatunnel_service()
        job_id = service.create_cdc_job(
            job_name=data['job_name'],
            source=source,
            sink=sink,
            transforms=data.get('transforms', []),
            parallelism=data.get('parallelism', 2),
            description=data.get('description', ''),
        )

        if job_id:
            return jsonify({
                'code': 0,
                'data': {'job_id': job_id},
                'msg': 'success'
            })
        else:
            return jsonify({
                'code': -1,
                'msg': 'job creation failed'
            }), 500

    except Exception as e:
        logger.error(f"创建 CDC 任务失败: {e}")
        return jsonify({
            'code': -1,
            'msg': str(e)
        }), 500


@cdc_bp.route('/jobs', methods=['GET'])
@require_auth
def list_cdc_jobs():
    """
    列出 CDC 任务

    Query:
        status: 任务状态过滤
    """
    try:
        status = request.args.get('status')

        service = get_seatunnel_service()
        jobs = service.list_jobs(status=status)

        return jsonify({
            'code': 0,
            'data': {
                'jobs': jobs,
                'total': len(jobs),
            },
            'msg': 'success'
        })

    except Exception as e:
        logger.error(f"列出 CDC 任务失败: {e}")
        return jsonify({
            'code': -1,
            'msg': str(e)
        }), 500


@cdc_bp.route('/jobs/<job_id>', methods=['GET'])
@require_auth
def get_cdc_job(job_id: str):
    """获取 CDC 任务详情"""
    try:
        service = get_seatunnel_service()
        config = service.get_job_config(job_id)
        metrics = service.get_job_metrics(job_id)

        if not config:
            return jsonify({
                'code': -1,
                'msg': 'job not found'
            }), 404

        result = {
            'config': config,
            'metrics': metrics.to_dict() if metrics else None,
        }

        return jsonify({
            'code': 0,
            'data': result,
            'msg': 'success'
        })

    except Exception as e:
        logger.error(f"获取 CDC 任务失败: {e}")
        return jsonify({
            'code': -1,
            'msg': str(e)
        }), 500


@cdc_bp.route('/jobs/<job_id>/start', methods=['POST'])
@require_auth
def start_cdc_job(job_id: str):
    """启动 CDC 任务"""
    try:
        service = get_seatunnel_service()
        success = service.start_job(job_id)

        if success:
            return jsonify({
                'code': 0,
                'data': {'job_id': job_id, 'status': 'running'},
                'msg': 'success'
            })
        else:
            return jsonify({
                'code': -1,
                'msg': 'job start failed'
            }), 500

    except Exception as e:
        logger.error(f"启动 CDC 任务失败: {e}")
        return jsonify({
            'code': -1,
            'msg': str(e)
        }), 500


@cdc_bp.route('/jobs/<job_id>/stop', methods=['POST'])
@require_auth
def stop_cdc_job(job_id: str):
    """停止 CDC 任务"""
    try:
        service = get_seatunnel_service()
        success = service.stop_job(job_id)

        if success:
            return jsonify({
                'code': 0,
                'data': {'job_id': job_id, 'status': 'stopped'},
                'msg': 'success'
            })
        else:
            return jsonify({
                'code': -1,
                'msg': 'job stop failed'
            }), 500

    except Exception as e:
        logger.error(f"停止 CDC 任务失败: {e}")
        return jsonify({
            'code': -1,
            'msg': str(e)
        }), 500


@cdc_bp.route('/jobs/<job_id>', methods=['DELETE'])
@require_auth
def delete_cdc_job(job_id: str):
    """删除 CDC 任务"""
    try:
        service = get_seatunnel_service()
        success = service.remove_job(job_id)

        if success:
            return jsonify({
                'code': 0,
                'data': {'job_id': job_id},
                'msg': 'success'
            })
        else:
            return jsonify({
                'code': -1,
                'msg': 'job deletion failed'
            }), 500

    except Exception as e:
        logger.error(f"删除 CDC 任务失败: {e}")
        return jsonify({
            'code': -1,
            'msg': str(e)
        }), 500


@cdc_bp.route('/jobs/<job_id>/metrics', methods=['GET'])
@require_auth
def get_job_metrics(job_id: str):
    """获取 CDC 任务指标"""
    try:
        service = get_seatunnel_service()
        metrics = service.get_job_metrics(job_id)

        if metrics:
            return jsonify({
                'code': 0,
                'data': metrics.to_dict(),
                'msg': 'success'
            })
        else:
            return jsonify({
                'code': -1,
                'msg': 'metrics not found'
            }), 404

    except Exception as e:
        logger.error(f"获取任务指标失败: {e}")
        return jsonify({
            'code': -1,
            'msg': str(e)
        }), 500


# ==================== 预定义模板 ====================

@cdc_bp.route('/templates/mysql-minio', methods=['POST'])
@require_auth
def create_mysql_to_minio_job():
    """
    使用 MySQL 到 MinIO 模板创建 CDC 任务

    Body:
    {
        "mysql_host": "localhost",
        "mysql_port": 3306,
        "mysql_user": "user",
        "mysql_password": "pass",
        "mysql_database": "db",
        "tables": ["table1"],
        "minio_endpoint": "http://localhost:9000",
        "minio_bucket": "bucket",
        "minio_path": "path/",
        "minio_access_key": "key",
        "minio_secret_key": "secret"
    }
    """
    try:
        data = request.get_json()

        from services.data_api.services.seatunnel_service import SeaTunnelService

        job_config = SeaTunnelService.mysql_to_minio_template(
            mysql_host=data['mysql_host'],
            mysql_port=data['mysql_port'],
            mysql_user=data['mysql_user'],
            mysql_password=data['mysql_password'],
            mysql_database=data['mysql_database'],
            tables=data['tables'],
            minio_endpoint=data['minio_endpoint'],
            minio_bucket=data['minio_bucket'],
            minio_path=data['minio_path'],
            minio_access_key=data['minio_access_key'],
            minio_secret_key=data['minio_secret_key'],
        )

        service = get_seatunnel_service()
        job_id = service.create_cdc_job(
            job_name=job_config.job_name,
            source=job_config.source,
            sink=job_config.sink,
            description=job_config.description,
        )

        if job_id:
            return jsonify({
                'code': 0,
                'data': {'job_id': job_id},
                'msg': 'success'
            })
        else:
            return jsonify({
                'code': -1,
                'msg': 'job creation failed'
            }), 500

    except Exception as e:
        logger.error(f"创建 MySQL-MinIO 任务失败: {e}")
        return jsonify({
            'code': -1,
            'msg': str(e)
        }), 500


@cdc_bp.route('/templates/mysql-clickhouse', methods=['POST'])
@require_auth
def create_mysql_to_clickhouse_job():
    """
    使用 MySQL 到 ClickHouse 模板创建 CDC 任务

    Body:
    {
        "mysql_host": "localhost",
        "mysql_port": 3306,
        "mysql_user": "user",
        "mysql_password": "pass",
        "mysql_database": "db",
        "tables": ["table1"],
        "ch_host": "localhost",
        "ch_port": 8123,
        "ch_database": "db",
        "ch_user": "user",
        "ch_password": "pass"
    }
    """
    try:
        data = request.get_json()

        from services.data_api.services.seatunnel_service import SeaTunnelService

        job_config = SeaTunnelService.mysql_to_clickhouse_template(
            mysql_host=data['mysql_host'],
            mysql_port=data['mysql_port'],
            mysql_user=data['mysql_user'],
            mysql_password=data['mysql_password'],
            mysql_database=data['mysql_database'],
            tables=data['tables'],
            ch_host=data['ch_host'],
            ch_port=data['ch_port'],
            ch_database=data['ch_database'],
            ch_user=data['ch_user'],
            ch_password=data['ch_password'],
        )

        service = get_seatunnel_service()
        job_id = service.create_cdc_job(
            job_name=job_config.job_name,
            source=job_config.source,
            sink=job_config.sink,
            description=job_config.description,
        )

        if job_id:
            return jsonify({
                'code': 0,
                'data': {'job_id': job_id},
                'msg': 'success'
            })
        else:
            return jsonify({
                'code': -1,
                'msg': 'job creation failed'
            }), 500

    except Exception as e:
        logger.error(f"创建 MySQL-ClickHouse 任务失败: {e}")
        return jsonify({
            'code': -1,
            'msg': str(e)
        }), 500


# ==================== 健康检查 ====================

@cdc_bp.route('/health', methods=['GET'])
def health_check():
    """CDC 服务健康检查"""
    try:
        service = get_seatunnel_service()
        jobs = service.list_jobs()

        return jsonify({
            'status': 'healthy',
            'service': 'seatunnel',
            'url': service.seatunnel_url,
            'config_dir': str(service.config_dir),
            'total_jobs': len(jobs),
        })

    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 503


def register_cdc_bp(app):
    """注册 CDC Blueprint 到 Flask 应用"""
    app.register_blueprint(cdc_bp)
    logger.info("CDC API registered")


# 导出
__all__ = [
    'cdc_bp',
    'register_cdc_bp',
]
