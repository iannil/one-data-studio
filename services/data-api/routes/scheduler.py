"""
DolphinScheduler 调度器 API 路由
提供工作流管理、任务执行和监控的 REST API
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from flask import Blueprint, jsonify, request, g

# 导入调度器服务
try:
    from services.scheduler_wrapper import (
        get_unified_scheduler,
        UnifiedTaskDefinition,
        SchedulerEngine,
        TaskDefinitionType,
        TaskPriority,
    )
    from services.smart_scheduler_service import get_smart_scheduler_service
except ImportError:
    # 添加路径
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
    from services.data_api.services.scheduler_wrapper import (
        get_unified_scheduler,
        UnifiedTaskDefinition,
        SchedulerEngine,
        TaskDefinitionType,
        TaskPriority,
    )
    from services.data_api.services.smart_scheduler_service import get_smart_scheduler_service

logger = logging.getLogger(__name__)

# 创建 Blueprint
scheduler_bp = Blueprint('scheduler', __name__, url_prefix='/api/v1/scheduler')


# ==================== 认证装饰器 ====================

def require_auth(f):
    """认证装饰器（简化版）"""
    def decorator(*args, **kwargs):
        # 实际应从 JWT token 获取用户信息
        g.user_id = request.headers.get('X-User-Id', 'system')
        g.username = request.headers.get('X-Username', 'admin')
        return f(*args, **kwargs)
    return decorator


# ==================== 统计信息 ====================

@scheduler_bp.route('/stats', methods=['GET'])
@require_auth
def get_scheduler_stats():
    """获取调度器统计信息"""
    try:
        scheduler = get_unified_scheduler()
        stats = scheduler.get_statistics()

        # 添加 DolphinScheduler 状态
        ds_enabled = os.getenv('DOLPHINSCHEDULER_ENABLED', 'true').lower() == 'true'
        stats['dolphinscheduler'] = {
            'enabled': ds_enabled,
            'url': os.getenv('DOLPHINSCHEDULER_URL', 'http://localhost:12345'),
        }

        return jsonify({
            'code': 0,
            'data': stats,
            'msg': 'success'
        })
    except Exception as e:
        logger.error(f"获取统计信息失败: {e}")
        return jsonify({
            'code': -1,
            'msg': str(e)
        }), 500


# ==================== 任务管理 ====================

@scheduler_bp.route('/tasks', methods=['POST'])
@require_auth
def submit_task():
    """
    提交任务

    Body:
    {
        "name": "任务名称",
        "type": "celery_task|shell|sql|python|http|workflow",
        "description": "任务描述",
        "celery_task_name": "services.shared.celery_tasks.xxx",
        "script": "脚本内容",
        "sql_query": "SQL 查询",
        "parameters": {},
        "dependencies": [],
        "priority": "normal|high|critical",
        "engine": "auto|celery|dolphinscheduler|smart",
        "timeout": 3600,
        "args": [],
        "kwargs": {}
    }
    """
    try:
        data = request.get_json()

        # 解析优先级
        priority = TaskPriority.NORMAL
        if data.get('priority'):
            priority_str = data['priority'].lower()
            if priority_str == 'critical':
                priority = TaskPriority.CRITICAL
            elif priority_str == 'high':
                priority = TaskPriority.HIGH
            elif priority_str == 'low':
                priority = TaskPriority.LOW

        # 解析引擎
        engine = SchedulerEngine.AUTO
        if data.get('engine'):
            engine = SchedulerEngine(data['engine'].lower())

        # 创建任务定义
        task_def = UnifiedTaskDefinition(
            name=data.get('name', 'unnamed_task'),
            task_type=TaskDefinitionType(data.get('type', 'celery_task')),
            description=data.get('description', ''),
            celery_task_name=data.get('celery_task_name', ''),
            script=data.get('script', ''),
            script_content=data.get('script_content', ''),
            sql_query=data.get('sql_query', ''),
            http_url=data.get('http_url', ''),
            http_method=data.get('http_method', 'GET'),
            http_headers=data.get('http_headers', {}),
            http_body=data.get('http_body', ''),
            parameters=data.get('parameters', {}),
            dependencies=data.get('dependencies', []),
            priority=priority,
            engine=engine,
            timeout=data.get('timeout', 3600),
        )

        # 提交任务
        scheduler = get_unified_scheduler()
        result = scheduler.submit_task(
            task_def,
            args=data.get('args', []),
            kwargs=data.get('kwargs', {}),
        )

        return jsonify({
            'code': 0,
            'data': {
                'task_id': result.task_id,
                'engine': result.engine.value,
                'status': result.status,
                'started_at': result.started_at.isoformat() if result.started_at else None,
            },
            'msg': 'success'
        })

    except Exception as e:
        logger.error(f"提交任务失败: {e}")
        return jsonify({
            'code': -1,
            'msg': str(e)
        }), 500


@scheduler_bp.route('/tasks/<task_id>', methods=['GET'])
@require_auth
def get_task_status(task_id: str):
    """获取任务状态"""
    try:
        engine = None
        if request.args.get('engine'):
            engine = SchedulerEngine(request.args.get('engine'))

        scheduler = get_unified_scheduler()
        status = scheduler.get_task_status(task_id, engine)

        return jsonify({
            'code': 0,
            'data': status,
            'msg': 'success'
        })

    except Exception as e:
        logger.error(f"获取任务状态失败: {e}")
        return jsonify({
            'code': -1,
            'msg': str(e)
        }), 500


@scheduler_bp.route('/tasks', methods=['GET'])
@require_auth
def list_tasks():
    """
    列出任务

    Query:
        status: 任务状态过滤
        engine: 调度引擎过滤
        limit: 返回数量限制
    """
    try:
        status = request.args.get('status')
        engine = None
        if request.args.get('engine'):
            engine = SchedulerEngine(request.args.get('engine'))
        limit = int(request.args.get('limit', 100))

        scheduler = get_unified_scheduler()
        tasks = scheduler.list_tasks(status=status, engine=engine, limit=limit)

        return jsonify({
            'code': 0,
            'data': {
                'tasks': tasks,
                'total': len(tasks),
            },
            'msg': 'success'
        })

    except Exception as e:
        logger.error(f"列出任务失败: {e}")
        return jsonify({
            'code': -1,
            'msg': str(e)
        }), 500


@scheduler_bp.route('/tasks/<task_id>/cancel', methods=['POST'])
@require_auth
def cancel_task(task_id: str):
    """取消任务"""
    try:
        engine = None
        if request.args.get('engine'):
            engine = SchedulerEngine(request.args.get('engine'))

        scheduler = get_unified_scheduler()
        success = scheduler.cancel_task(task_id, engine)

        return jsonify({
            'code': 0 if success else -1,
            'data': {'cancelled': success},
            'msg': 'success' if success else 'cancel failed'
        })

    except Exception as e:
        logger.error(f"取消任务失败: {e}")
        return jsonify({
            'code': -1,
            'msg': str(e)
        }), 500


@scheduler_bp.route('/tasks/<task_id>/retry', methods=['POST'])
@require_auth
def retry_task(task_id: str):
    """重试任务"""
    try:
        engine = None
        if request.args.get('engine'):
            engine = SchedulerEngine(request.args.get('engine'))

        scheduler = get_unified_scheduler()
        new_task_id = scheduler.retry_task(task_id, engine)

        if new_task_id:
            return jsonify({
                'code': 0,
                'data': {'new_task_id': new_task_id},
                'msg': 'success'
            })
        else:
            return jsonify({
                'code': -1,
                'msg': 'retry failed'
            }), 500

    except Exception as e:
        logger.error(f"重试任务失败: {e}")
        return jsonify({
            'code': -1,
            'msg': str(e)
        }), 500


# ==================== 工作流管理 ====================

@scheduler_bp.route('/workflows', methods=['POST'])
@require_auth
def create_workflow():
    """
    创建工作流

    Body:
    {
        "name": "工作流名称",
        "description": "描述",
        "tasks": [
            {
                "name": "任务1",
                "type": "shell",
                "script": "...",
                "dependencies": []
            }
        ],
        "engine": "dolphinscheduler"
    }
    """
    try:
        data = request.get_json()

        # 解析任务定义
        task_defs = []
        for task_data in data.get('tasks', []):
            priority = TaskPriority.NORMAL
            if task_data.get('priority'):
                priority_str = task_data['priority'].lower()
                if priority_str == 'critical':
                    priority = TaskPriority.CRITICAL
                elif priority_str == 'high':
                    priority = TaskPriority.HIGH
                elif priority_str == 'low':
                    priority = TaskPriority.LOW

            task_def = UnifiedTaskDefinition(
                name=task_data['name'],
                task_type=TaskDefinitionType(task_data.get('type', 'shell')),
                description=task_data.get('description', ''),
                script=task_data.get('script', ''),
                script_content=task_data.get('script_content', ''),
                sql_query=task_data.get('sql_query', ''),
                parameters=task_data.get('parameters', {}),
                dependencies=task_data.get('dependencies', []),
                priority=priority,
            )
            task_defs.append(task_def)

        # 选择引擎
        engine = SchedulerEngine.DOLPHINSCHEDULER
        if data.get('engine'):
            engine = SchedulerEngine(data['engine'].lower())

        # 创建工作流
        scheduler = get_unified_scheduler()
        workflow_id = scheduler.create_workflow(
            name=data['name'],
            tasks=task_defs,
            description=data.get('description', ''),
            engine=engine,
        )

        if workflow_id:
            return jsonify({
                'code': 0,
                'data': {'workflow_id': workflow_id},
                'msg': 'success'
            })
        else:
            return jsonify({
                'code': -1,
                'msg': 'workflow creation failed'
            }), 500

    except Exception as e:
        logger.error(f"创建工作流失败: {e}")
        return jsonify({
            'code': -1,
            'msg': str(e)
        }), 500


@scheduler_bp.route('/workflows/<workflow_id>/run', methods=['POST'])
@require_auth
def run_workflow(workflow_id: str):
    """
    运行工作流

    Body:
    {
        "params": {}
    }
    """
    try:
        data = request.get_json() or {}
        params = data.get('params', {})

        scheduler = get_unified_scheduler()
        instance_id = scheduler.run_workflow(workflow_id, params)

        if instance_id:
            return jsonify({
                'code': 0,
                'data': {'instance_id': instance_id},
                'msg': 'success'
            })
        else:
            return jsonify({
                'code': -1,
                'msg': 'workflow run failed'
            }), 500

    except Exception as e:
        logger.error(f"运行工作流失败: {e}")
        return jsonify({
            'code': -1,
            'msg': str(e)
        }), 500


# ==================== 定时任务 ====================

@scheduler_bp.route('/cron', methods=['POST'])
@require_auth
def create_cron_task():
    """
    创建定时任务

    Body:
    {
        "name": "任务名称",
        "cron_expression": "0 0 * * *",
        "task": {
            "name": "...",
            "type": "...",
            ...
        },
        "description": "描述"
    }
    """
    try:
        data = request.get_json()

        # 构建任务定义
        task_data = data.get('task', {})
        task_def = UnifiedTaskDefinition(
            name=task_data.get('name', data['name']),
            task_type=TaskDefinitionType(task_data.get('type', 'celery_task')),
            description=task_data.get('description', ''),
            celery_task_name=task_data.get('celery_task_name', ''),
            script=task_data.get('script', ''),
            script_content=task_data.get('script_content', ''),
            sql_query=task_data.get('sql_query', ''),
            parameters=task_data.get('parameters', {}),
        )

        scheduler = get_unified_scheduler()
        cron_id = scheduler.schedule_cron_task(
            task_def=task_def,
            cron_expression=data['cron_expression'],
            description=data.get('description', ''),
        )

        if cron_id:
            return jsonify({
                'code': 0,
                'data': {'cron_id': cron_id},
                'msg': 'success'
            })
        else:
            return jsonify({
                'code': -1,
                'msg': 'cron task creation failed'
            }), 500

    except Exception as e:
        logger.error(f"创建定时任务失败: {e}")
        return jsonify({
            'code': -1,
            'msg': str(e)
        }), 500


# ==================== DolphinScheduler 专用接口 ====================

@scheduler_bp.route('/ds/projects', methods=['GET'])
@require_auth
def list_ds_projects():
    """列出 DolphinScheduler 项目"""
    try:
        from services.shared.ds_celery_bridge import get_ds_celery_bridge

        bridge = get_ds_celery_bridge()
        projects = bridge.ds._request(
            'GET',
            '/projects/query-project-list-by-user',
        )

        return jsonify({
            'code': 0,
            'data': projects or [],
            'msg': 'success'
        })

    except Exception as e:
        logger.error(f"列出项目失败: {e}")
        return jsonify({
            'code': -1,
            'msg': str(e)
        }), 500


@scheduler_bp.route('/ds/process-instances', methods=['GET'])
@require_auth
def list_ds_process_instances():
    """
    列出 DolphinScheduler 流程实例

    Query:
        project_id: 项目 ID
        page: 页码
        size: 每页数量
    """
    try:
        project_id = request.args.get('project_id')
        page = int(request.args.get('page', 1))
        size = int(request.args.get('size', 10))

        from services.shared.ds_celery_bridge import get_ds_celery_bridge

        bridge = get_ds_celery_bridge()
        instances = bridge.ds._request(
            'GET',
            '/executors/list',
            params={
                'projectCode': project_id,
                'pageNo': page,
                'pageSize': size,
            },
        )

        return jsonify({
            'code': 0,
            'data': instances or [],
            'msg': 'success'
        })

    except Exception as e:
        logger.error(f"列出流程实例失败: {e}")
        return jsonify({
            'code': -1,
            'msg': str(e)
        }), 500


# ==================== 智能调度器接口 ====================

@scheduler_bp.route('/smart/tasks', methods=['GET'])
@require_auth
def list_smart_tasks():
    """
    列出智能调度器任务

    Query:
        status: 任务状态
        priority: 优先级
        type: 任务类型
        limit: 返回数量
    """
    try:
        from services.data_api.services.smart_scheduler_service import (
            TaskStatus, TaskPriority
        )

        smart_scheduler = get_smart_scheduler_service()

        # 解析过滤参数
        status = None
        if request.args.get('status'):
            status = TaskStatus(request.args.get('status'))

        priority = None
        if request.args.get('priority'):
            priority = TaskPriority(request.args.get('priority'))

        task_type = request.args.get('type')
        limit = int(request.args.get('limit', 100))

        tasks = smart_scheduler.list_tasks(
            status=status,
            priority=priority,
            task_type=task_type,
            limit=limit,
        )

        return jsonify({
            'code': 0,
            'data': {
                'tasks': [t.to_dict() for t in tasks],
                'total': len(tasks),
            },
            'msg': 'success'
        })

    except Exception as e:
        logger.error(f"列出智能任务失败: {e}")
        return jsonify({
            'code': -1,
            'msg': str(e)
        }), 500


@scheduler_bp.route('/smart/optimize', methods=['POST'])
@require_auth
def optimize_schedule():
    """
    优化调度顺序

    Body:
    {
        "task_ids": ["task1", "task2", ...]
    }
    """
    try:
        data = request.get_json() or {}

        smart_scheduler = get_smart_scheduler_service()
        result = smart_scheduler.optimize_schedule()

        return jsonify({
            'code': 0,
            'data': result,
            'msg': 'success'
        })

    except Exception as e:
        logger.error(f"优化调度失败: {e}")
        return jsonify({
            'code': -1,
            'msg': str(e)
        }), 500


@scheduler_bp.route('/smart/resource-demand', methods=['GET'])
@require_auth
def predict_resource_demand():
    """
    预测资源需求

    Query:
        window_minutes: 预测窗口（分钟）
    """
    try:
        window = int(request.args.get('window_minutes', 60))

        smart_scheduler = get_smart_scheduler_service()
        prediction = smart_scheduler.predict_resource_demand(window)

        return jsonify({
            'code': 0,
            'data': prediction,
            'msg': 'success'
        })

    except Exception as e:
        logger.error(f"预测资源需求失败: {e}")
        return jsonify({
            'code': -1,
            'msg': str(e)
        }), 500


# ==================== 健康检查 ====================

@scheduler_bp.route('/health', methods=['GET'])
def health_check():
    """调度器健康检查"""
    health_status = {
        'celery': False,
        'dolphinscheduler': False,
        'smart_scheduler': False,
    }

    # 检查 Celery
    try:
        from services.shared.celery_app import get_task_manager
        tm = get_task_manager()
        stats = tm.get_worker_stats()
        health_status['celery'] = bool(stats.get('workers'))
    except Exception as e:
        logger.debug(f"健康检查 Celery 失败: {e}")

    # 检查 DolphinScheduler
    try:
        from services.shared.ds_celery_bridge import get_ds_celery_bridge
        bridge = get_ds_celery_bridge()
        health_status['dolphinscheduler'] = bridge.ds.login()
    except Exception as e:
        logger.debug(f"健康检查 DolphinScheduler 失败: {e}")

    # 检查智能调度器
    try:
        from services.data_api.services.smart_scheduler_service import get_smart_scheduler_service
        smart_scheduler = get_smart_scheduler_service()
        stats = smart_scheduler.get_statistics()
        health_status['smart_scheduler'] = stats.get('total_tasks', 0) >= 0
    except Exception as e:
        logger.debug(f"健康检查智能调度器失败: {e}")

    all_healthy = all(health_status.values())

    return jsonify({
        'status': 'healthy' if all_healthy else 'degraded',
        'components': health_status,
    }), 200 if all_healthy else 503


def register_scheduler_bp(app):
    """注册调度器 Blueprint 到 Flask 应用"""
    app.register_blueprint(scheduler_bp)
    logger.info("Scheduler API registered")


# 导出
__all__ = [
    'scheduler_bp',
    'register_scheduler_bp',
]
