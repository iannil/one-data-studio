"""
Superset 集成 API 路由
提供 Superset 数据源同步、仪表板嵌入等功能
"""

import logging
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
from flask import Blueprint, jsonify, request, g

# 导入 Superset 同步服务
try:
    from services.superset_sync_service import get_superset_sync_service
except ImportError:
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
    from services.data_api.services.superset_sync_service import get_superset_sync_service

# 导入模型
try:
    from models import get_db, BIDashboard, BIChart, MetadataDatabase, Dataset
except ImportError:
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))
    from models import get_db, BIDashboard, BIChart, MetadataDatabase, Dataset

logger = logging.getLogger(__name__)

# 创建 Blueprint
superset_bp = Blueprint('superset', __name__, url_prefix='/api/v1/superset')


# ==================== 认证装饰器 ====================

def require_auth(f):
    """认证装饰器（简化版）"""
    def decorator(*args, **kwargs):
        g.user_id = request.headers.get('X-User-Id', 'system')
        g.username = request.headers.get('X-Username', 'admin')
        return f(*args, **kwargs)
    return decorator


# ==================== 连接管理 ====================

@superset_bp.route('/health', methods=['GET'])
def health_check():
    """Superset 连接健康检查"""
    try:
        service = get_superset_sync_service()
        is_healthy = service.client.login()

        return jsonify({
            'status': 'healthy' if is_healthy else 'unhealthy',
            'url': service.client.base_url,
        }), 200 if is_healthy else 503

    except Exception as e:
        logger.error(f"Superset 健康检查失败: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500


# ==================== 数据库同步 ====================

@superset_bp.route('/databases/sync', methods=['POST'])
@require_auth
def sync_database():
    """
    同步数据库到 Superset

    Body:
    {
        "name": "数据库名称",
        "host": "主机地址",
        "port": 3306,
        "username": "用户名",
        "password": "密码",
        "database": "数据库名"
    }
    """
    try:
        data = request.get_json()

        service = get_superset_sync_service()
        db_id = service.sync_database(
            name=data['name'],
            host=data['host'],
            port=data.get('port', 3306),
            username=data['username'],
            password=data['password'],
            database=data['database'],
        )

        if db_id:
            return jsonify({
                'code': 0,
                'data': {'database_id': db_id},
                'msg': 'success'
            })
        else:
            return jsonify({
                'code': -1,
                'msg': 'sync failed'
            }), 500

    except Exception as e:
        logger.error(f"同步数据库失败: {e}")
        return jsonify({
            'code': -1,
            'msg': str(e)
        }), 500


@superset_bp.route('/databases', methods=['GET'])
@require_auth
def list_databases():
    """列出 Superset 中的数据库"""
    try:
        service = get_superset_sync_service()
        databases = service.client.list_databases()

        return jsonify({
            'code': 0,
            'data': {
                'databases': databases,
                'total': len(databases),
            },
            'msg': 'success'
        })

    except Exception as e:
        logger.error(f"列出数据库失败: {e}")
        return jsonify({
            'code': -1,
            'msg': str(e)
        }), 500


# ==================== 数据集同步 ====================

@superset_bp.route('/datasets/sync', methods=['POST'])
@require_auth
def sync_dataset():
    """
    同步数据集到 Superset

    Body:
    {
        "database_id": 1,
        "schema": "数据库名",
        "table_name": "表名",
        "dataset_name": "数据集名称"
    }
    """
    try:
        data = request.get_json()

        service = get_superset_sync_service()
        dataset_id = service.sync_dataset(
            db_id=data['database_id'],
            schema=data['schema'],
            table_name=data['table_name'],
            dataset_name=data.get('dataset_name'),
        )

        if dataset_id:
            return jsonify({
                'code': 0,
                'data': {'dataset_id': dataset_id},
                'msg': 'success'
            })
        else:
            return jsonify({
                'code': -1,
                'msg': 'sync failed'
            }), 500

    except Exception as e:
        logger.error(f"同步数据集失败: {e}")
        return jsonify({
            'code': -1,
            'msg': str(e)
        }), 500


@superset_bp.route('/datasets', methods=['GET'])
@require_auth
def list_datasets():
    """
    列出 Superset 中的数据集

    Query:
        database_id: 数据库 ID
    """
    try:
        database_id = request.args.get('database_id', type=int)

        service = get_superset_sync_service()
        datasets = service.client.list_datasets(database_id)

        return jsonify({
            'code': 0,
            'data': {
                'datasets': datasets,
                'total': len(datasets),
            },
            'msg': 'success'
        })

    except Exception as e:
        logger.error(f"列出数据集失败: {e}")
        return jsonify({
            'code': -1,
            'msg': str(e)
        }), 500


# ==================== 图表同步 ====================

@superset_bp.route('/charts/sync', methods=['POST'])
@require_auth
def sync_chart():
    """
    从 BIChart 创建 Superset 图表

    Body:
    {
        "chart_id": "bi_chart_id",
        "dataset_id": 1
    }
    """
    try:
        data = request.get_json()
        session = get_db()

        # 获取 BIChart
        bi_chart = session.query(BIChart).filter(
            BIChart.chart_id == data['chart_id']
        ).first()

        if not bi_chart:
            return jsonify({
                'code': -1,
                'msg': 'BI chart not found'
            }), 404

        # 同步到 Superset
        service = get_superset_sync_service()
        chart_id = service.create_chart_from_bi_chart(
            bi_chart=bi_chart,
            dataset_id=data['dataset_id'],
        )

        if chart_id:
            return jsonify({
                'code': 0,
                'data': {'chart_id': chart_id},
                'msg': 'success'
            })
        else:
            return jsonify({
                'code': -1,
                'msg': 'sync failed'
            }), 500

    except Exception as e:
        logger.error(f"同步图表失败: {e}")
        return jsonify({
            'code': -1,
            'msg': str(e)
        }), 500


@superset_bp.route('/charts', methods=['GET'])
@require_auth
def list_charts():
    """
    列出 Superset 中的图表

    Query:
        dataset_id: 数据集 ID
    """
    try:
        dataset_id = request.args.get('dataset_id', type=int)

        service = get_superset_sync_service()
        charts = service.client.list_charts(dataset_id)

        return jsonify({
            'code': 0,
            'data': {
                'charts': charts,
                'total': len(charts),
            },
            'msg': 'success'
        })

    except Exception as e:
        logger.error(f"列出图表失败: {e}")
        return jsonify({
            'code': -1,
            'msg': str(e)
        }), 500


# ==================== 仪表板同步 ====================

@superset_bp.route('/dashboards/sync', methods=['POST'])
@require_auth
def sync_dashboard():
    """
    从 BIDashboard 创建 Superset 仪表板

    Body:
    {
        "dashboard_id": "bi_dashboard_id",
        "chart_map": {"chart_name": superset_chart_id, ...}
    }
    """
    try:
        data = request.get_json()
        session = get_db()

        # 获取 BIDashboard
        bi_dashboard = session.query(BIDashboard).filter(
            BIDashboard.dashboard_id == data['dashboard_id']
        ).first()

        if not bi_dashboard:
            return jsonify({
                'code': -1,
                'msg': 'BI dashboard not found'
            }), 404

        # 同步到 Superset
        service = get_superset_sync_service()
        dashboard_id = service.create_dashboard_from_bi_dashboard(
            bi_dashboard=bi_dashboard,
            chart_map=data.get('chart_map', {}),
        )

        if dashboard_id:
            return jsonify({
                'code': 0,
                'data': {'dashboard_id': dashboard_id},
                'msg': 'success'
            })
        else:
            return jsonify({
                'code': -1,
                'msg': 'sync failed'
            }), 500

    except Exception as e:
        logger.error(f"同步仪表板失败: {e}")
        return jsonify({
            'code': -1,
            'msg': str(e)
        }), 500


@superset_bp.route('/dashboards', methods=['GET'])
@require_auth
def list_dashboards():
    """列出 Superset 中的仪表板"""
    try:
        service = get_superset_sync_service()
        dashboards = service.client.list_dashboards()

        return jsonify({
            'code': 0,
            'data': {
                'dashboards': dashboards,
                'total': len(dashboards),
            },
            'msg': 'success'
        })

    except Exception as e:
        logger.error(f"列出仪表板失败: {e}")
        return jsonify({
            'code': -1,
            'msg': str(e)
        }), 500


# ==================== 嵌入令牌 ====================

@superset_bp.route('/guest-token', methods=['POST'])
@require_auth
def create_guest_token():
    """
    创建 Guest Token 用于嵌入式访问

    Body:
    {
        "dashboard_id": 1,
        "user": {
            "username": "guest_user",
            "first_name": "Guest",
            "last_name": "User"
        },
        "rls": [{"dataset": 1, "clause": "column='value'"}]
    }
    """
    try:
        data = request.get_json()
        service = get_superset_sync_service()

        # 使用 Superset API 创建 guest token
        # 注意：需要 Superset 配置 ENABLE_GUEST_TOKEN = True
        result = service.client._request(
            'POST',
            '/security/guest_token/',
            data={
                'resources': [{
                    'type': 'dashboard',
                    'id': data['dashboard_id'],
                }],
                'user': data.get('user', {
                    'username': 'guest',
                    'first_name': 'Guest',
                    'last_name': 'User',
                }),
                'rls': data.get('rls', []),
            },
        )

        if result:
            return jsonify({
                'code': 0,
                'data': {'token': result.get('token')},
                'msg': 'success'
            })
        else:
            return jsonify({
                'code': -1,
                'msg': 'token creation failed'
            }), 500

    except Exception as e:
        logger.error(f"创建 Guest Token 失败: {e}")
        return jsonify({
            'code': -1,
            'msg': str(e)
        }), 500


# ==================== 批量同步 ====================

@superset_bp.route('/sync/bi', methods=['POST'])
@require_auth
def sync_bi_to_superset():
    """
    批量同步 BI 仪表板到 Superset

    Body:
    {
        "database_config": {...},
        "dashboard_ids": ["dashboard_id1", ...]
    }
    """
    try:
        data = request.get_json()
        session = get_db()

        service = get_superset_sync_service()

        # 同步数据库
        db_config = data.get('database_config', {})
        db_id = service.sync_database(
            name=db_config.get('name', 'onedata'),
            host=db_config.get('host', 'mysql'),
            port=db_config.get('port', 3306),
            username=db_config.get('username', 'onedata'),
            password=db_config.get('password', ''),
            database=db_config.get('database', 'onedata'),
        )

        if not db_id:
            return jsonify({
                'code': -1,
                'msg': 'database sync failed'
            }), 500

        # 获取要同步的仪表板
        query = session.query(BIDashboard)
        if data.get('dashboard_ids'):
            query = query.filter(BIDashboard.dashboard_id.in_(data['dashboard_ids']))

        dashboards = query.all()
        results = []

        for bi_dashboard in dashboards:
            # 获取仪表板下的图表
            charts = session.query(BIChart).filter(
                BIChart.dashboard_id == bi_dashboard.dashboard_id
            ).all()

            chart_map = {}
            for chart in charts:
                # 同步数据集
                dataset_id = service.sync_dataset(
                    db_id=db_id,
                    schema=chart.datasource_type or 'onedata',
                    table_name=chart.datasource_id or f"table_{chart.chart_id}",
                    dataset_name=f"ds_{chart.chart_id}",
                )

                if dataset_id:
                    # 同步图表
                    superset_chart_id = service.create_chart_from_bi_chart(
                        bi_chart=chart,
                        dataset_id=dataset_id,
                    )
                    if superset_chart_id:
                        chart_map[chart.name] = superset_chart_id

            # 创建仪表板
            if chart_map:
                superset_dashboard_id = service.create_dashboard_from_bi_dashboard(
                    bi_dashboard=bi_dashboard,
                    chart_map=chart_map,
                )
                results.append({
                    'bi_dashboard_id': bi_dashboard.dashboard_id,
                    'superset_dashboard_id': superset_dashboard_id,
                    'charts_count': len(chart_map),
                })

        return jsonify({
            'code': 0,
            'data': {
                'synced': results,
                'total': len(results),
            },
            'msg': 'success'
        })

    except Exception as e:
        logger.error(f"批量同步失败: {e}")
        return jsonify({
            'code': -1,
            'msg': str(e)
        }), 500


def register_superset_bp(app):
    """注册 Superset Blueprint 到 Flask 应用"""
    app.register_blueprint(superset_bp)
    logger.info("Superset API registered")


# 导出
__all__ = [
    'superset_bp',
    'register_superset_bp',
]
