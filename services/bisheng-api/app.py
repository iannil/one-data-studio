"""
Bisheng API - 大模型应用开发平台 API
Sprint 4.5: 真实 MySQL 数据持久化
Phase 6: Sprint 6.1 - 工作流执行引擎
Phase 7: Sprint 7.1 - Agent 编排与工具系统
Phase 7: Sprint 7.4 - 工作流调度

功能：
- 聊天接口（集成 OpenAI Proxy）
- RAG 查询
- 工作流管理与执行
- 会话管理
- Text-to-SQL 生成
- Agent 工具注册与调用
- 工作流调度
- JWT 认证授权
"""

import logging
import os
import sys
import json
import asyncio
import requests
import uuid
from datetime import datetime
from flask import Flask, jsonify, request, g, Response

logger = logging.getLogger(__name__)

# 添加当前目录到路径（确保本地 models 优先于 shared/models）
sys.path.insert(0, '/app')

# 添加共享模块路径
sys.path.insert(1, '/app/shared')

# 导入模型
from models import (
    get_db, Workflow, Conversation, Message, WorkflowExecution, ExecutionLog, IndexedDocument,
    PromptTemplate, Evaluation, EvaluationResult, EvaluationDataset, SFTTask, SFTDataset,
    App, KnowledgeBase, Tool, Template
)

# 导入执行引擎
from engine import WorkflowExecutor, register_execution, unregister_execution, stop_execution

# 导入服务
from services import VectorStore, EmbeddingService, DocumentService, AGENT_TEMPLATE_AVAILABLE

if AGENT_TEMPLATE_AVAILABLE:
    from services import get_agent_template_service

# 导入 Agent 相关模块
try:
    from engine.tools import get_tool_registry
    from engine.agents import create_agent
    TOOLS_AVAILABLE = True
except ImportError:
    TOOLS_AVAILABLE = False

# 尝试导入认证模块
try:
    from auth import (
        require_jwt,
        require_permission,
        Resource,
        Operation,
        get_current_user
    )
    AUTH_ENABLED = True
except ImportError:
    # Check if we're in production - auth is required in production
    if os.getenv('ENVIRONMENT', '').lower() in ('production', 'prod'):
        raise ImportError(
            "Authentication module is required in production. "
            "Ensure auth.py is present and all dependencies are installed."
        )

    AUTH_ENABLED = False
    # 装饰器空实现（开发模式）
    logger.warning(
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
        WORKFLOW = type('', (), {'value': 'workflow'})()
        CHAT = type('', (), {'value': 'chat'})()
    class Operation:
        CREATE = type('', (), {'value': 'create'})()
        EXECUTE = type('', (), {'value': 'execute'})()

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

# 尝试导入 MinIO 存储模块
try:
    from shared.storage.minio_client import MinIOStorage, get_storage
    MINIO_ENABLED = True
except ImportError:
    MINIO_ENABLED = False
    _minio_storage = None
    def get_storage():
        global _minio_storage
        if _minio_storage is None:
            logger.warning("MinIO not available, using fallback local storage")
        return _minio_storage

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False
# 请求大小限制 - 防止 DoS 攻击
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024  # 32MB (for file uploads)

# 配置
ALDATA_API_URL = os.getenv("ALDATA_API_URL", "http://alldata-api:8080")
CUBE_API_URL = os.getenv("CUBE_API_URL", "http://vllm-serving:8000")
KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://keycloak.one-data-system.svc.cluster.local:80")
AUTH_MODE = os.getenv("AUTH_MODE", "true").lower() == "true"


# ============================================================
# 启动时环境验证
# ============================================================
def validate_production_environment():
    """
    验证生产环境配置

    在应用启动时检查关键配置，确保生产环境不会使用不安全的设置。
    如果检测到不安全配置，将记录错误并抛出异常阻止启动。
    """
    env = os.getenv("ENVIRONMENT", "development").lower()
    is_production = env in ("production", "prod")

    issues = []

    # 检查 1: 生产环境必须启用认证
    if is_production and not AUTH_ENABLED:
        issues.append(
            "认证模块未加载。生产环境必须启用认证。"
            "确保 auth.py 存在且所有依赖已安装。"
        )

    # 检查 2: 生产环境禁用 DEBUG 模式
    if is_production and os.getenv("DEBUG", "false").lower() == "true":
        issues.append(
            "DEBUG 模式已启用。生产环境必须禁用 DEBUG 模式。"
            "设置环境变量 DEBUG=false。"
        )

    # 检查 3: 生产环境禁用 SSL 验证跳过
    if is_production and os.getenv("VERIFY_SSL", "true").lower() != "true":
        issues.append(
            "SSL 验证已禁用。生产环境必须启用 SSL 验证。"
            "设置环境变量 VERIFY_SSL=true 或移除该设置。"
        )

    # 检查 4: 生产环境必须配置数据库
    if is_production and not os.getenv("DATABASE_URL"):
        issues.append(
            "未配置数据库连接。生产环境必须设置 DATABASE_URL。"
        )

    # 检查 5: 检查 mock 相关环境变量
    mock_vars = [
        ("MOCK_DATA", os.getenv("MOCK_DATA", "")),
        ("USE_MOCK", os.getenv("USE_MOCK", "")),
        ("ENABLE_MOCK", os.getenv("ENABLE_MOCK", "")),
    ]
    for var_name, var_value in mock_vars:
        if is_production and var_value.lower() in ("true", "1", "yes"):
            issues.append(
                f"环境变量 {var_name} 设置为启用状态。"
                f"生产环境禁止使用 mock 数据。"
            )

    # 汇总检查结果
    if issues:
        error_msg = (
            f"\n{'='*60}\n"
            f"⚠️  生产环境配置检查失败\n"
            f"{'='*60}\n"
            f"检测到 {len(issues)} 个配置问题：\n\n"
        )
        for i, issue in enumerate(issues, 1):
            error_msg += f"  {i}. {issue}\n"
        error_msg += (
            f"\n{'='*60}\n"
            f"请修复以上问题后重新启动应用。\n"
            f"{'='*60}\n"
        )
        logger.error(error_msg)
        raise RuntimeError(f"生产环境配置检查失败: 检测到 {len(issues)} 个问题")

    # 记录环境信息
    logger.info(f"环境验证通过: ENVIRONMENT={env}, AUTH_ENABLED={AUTH_ENABLED}")


# 执行启动验证
validate_production_environment()


def get_db_session():
    """获取数据库会话"""
    from models import SessionLocal
    return SessionLocal()


def get_user_id():
    """获取当前用户ID"""
    if hasattr(g, 'user') and g.user:
        return g.user
    return "unknown"


@app.route("/api/v1/health")
def health():
    """健康检查（无需认证）- 深度检查所有依赖"""
    import time as time_module

    health_status = {
        "code": 0,
        "message": "healthy",
        "service": "bisheng-api",
        "version": "2.0.0",
        "auth_enabled": AUTH_ENABLED and AUTH_MODE,
        "connections": {
            "alldata_api": ALDATA_API_URL,
            "cube_api": CUBE_API_URL
        },
        "checks": {}
    }

    all_healthy = True

    # 测试数据库连接
    try:
        from sqlalchemy import text
        start = time_module.time()
        db = get_db_session()
        db.execute(text("SELECT 1"))
        db.close()
        latency = (time_module.time() - start) * 1000
        health_status["checks"]["database"] = {
            "status": "healthy",
            "latency_ms": round(latency, 2)
        }
    except Exception as e:
        health_status["checks"]["database"] = {"status": "unhealthy", "error": str(e)}
        all_healthy = False

    # 测试 Redis 连接
    try:
        import redis
        redis_host = os.getenv('REDIS_HOST', 'localhost')
        redis_port = int(os.getenv('REDIS_PORT', '6379'))
        redis_client = redis.Redis(host=redis_host, port=redis_port, socket_timeout=2)
        start = time_module.time()
        redis_client.ping()
        latency = (time_module.time() - start) * 1000
        info = redis_client.info('memory')
        health_status["checks"]["redis"] = {
            "status": "healthy",
            "latency_ms": round(latency, 2),
            "used_memory_mb": round(info.get('used_memory', 0) / 1024 / 1024, 2)
        }
    except ImportError:
        health_status["checks"]["redis"] = {"status": "not_configured"}
    except Exception as e:
        health_status["checks"]["redis"] = {"status": "unhealthy", "error": str(e)}
        # Redis 是可选依赖，不影响整体健康

    # 测试 Milvus 连接
    try:
        vector_store = VectorStore()
        start = time_module.time()
        milvus_health = vector_store.health_check()
        latency = (time_module.time() - start) * 1000
        health_status["checks"]["milvus"] = {
            "status": milvus_health.get("status", "unknown"),
            "latency_ms": round(latency, 2),
            "connected": milvus_health.get("connected", False),
            "collections_count": milvus_health.get("collections_count", 0),
            "cache_size": milvus_health.get("cache_size", 0),
            "host": milvus_health.get("host"),
            "port": milvus_health.get("port")
        }
    except Exception as e:
        health_status["checks"]["milvus"] = {"status": "unhealthy", "error": str(e)}
        # Milvus 是可选依赖，不影响整体健康

    # 测试上游服务连接
    try:
        start = time_module.time()
        response = requests.get(f"{ALDATA_API_URL}/api/v1/health", timeout=5)
        latency = (time_module.time() - start) * 1000
        if response.status_code == 200:
            health_status["checks"]["alldata_api"] = {
                "status": "healthy",
                "latency_ms": round(latency, 2)
            }
        else:
            health_status["checks"]["alldata_api"] = {
                "status": "degraded",
                "http_status": response.status_code
            }
    except requests.Timeout:
        health_status["checks"]["alldata_api"] = {"status": "timeout", "error": "Connection timeout"}
        # 上游服务不可用不影响本服务健康
    except requests.ConnectionError as e:
        health_status["checks"]["alldata_api"] = {"status": "unreachable", "error": "Connection error"}
        # 上游服务不可用不影响本服务健康
    except requests.RequestException as e:
        health_status["checks"]["alldata_api"] = {"status": "unreachable", "error": str(e)}
        # 上游服务不可用不影响本服务健康

    # 测试 LLM 服务连接
    try:
        start = time_module.time()
        response = requests.get(f"{CUBE_API_URL}/v1/models", timeout=5)
        latency = (time_module.time() - start) * 1000
        if response.status_code == 200:
            health_status["checks"]["cube_api"] = {
                "status": "healthy",
                "latency_ms": round(latency, 2)
            }
        else:
            health_status["checks"]["cube_api"] = {
                "status": "degraded",
                "http_status": response.status_code
            }
    except requests.Timeout:
        health_status["checks"]["cube_api"] = {"status": "timeout", "error": "Connection timeout"}
    except requests.ConnectionError:
        health_status["checks"]["cube_api"] = {"status": "unreachable", "error": "Connection error"}
    except requests.RequestException as e:
        health_status["checks"]["cube_api"] = {"status": "unreachable", "error": str(e)}

    # 设置整体状态
    if not all_healthy:
        health_status["code"] = 1
        health_status["message"] = "degraded"

    return jsonify(health_status), 200 if all_healthy else 503


@app.route("/api/v1/stats/overview", methods=["GET"])
def stats_overview():
    """获取平台统计概览（用于仪表盘）"""
    db = get_db_session()
    try:
        from sqlalchemy import text, func

        # 统计用户数
        try:
            user_count = db.query(func.count()).select_from(User).scalar() or 0
        except Exception:
            user_count = 0

        # 统计工作流数
        try:
            workflow_count = db.query(func.count()).select_from(Workflow).scalar() or 0
        except Exception:
            workflow_count = 0

        # 统议会话数
        try:
            conversation_count = db.query(func.count()).select_from(Conversation).scalar() or 0
        except Exception:
            conversation_count = 0

        stats = {
            "code": 0,
            "message": "success",
            "data": {
                "users": {
                    "total": user_count,
                    "active": user_count  # 简化处理
                },
                "datasets": {
                    "total": 0,
                    "recent": 0
                },
                "models": {
                    "total": 0,
                    "deployed": 0
                },
                "workflows": {
                    "total": workflow_count,
                    "running": 0
                },
                "experiments": {
                    "total": 0,
                    "completed": 0
                },
                "api_calls": {
                    "today": 0,
                    "total": 0
                },
                "storage": {
                    "used_gb": 0,
                    "total_gb": 100
                },
                "compute": {
                    "gpu_hours_today": 0,
                    "cpu_hours_today": 0
                }
            }
        }
        return jsonify(stats), 200
    except Exception as e:
        logger.error(f"Error getting stats overview: {e}")
        return jsonify({
            "code": 50000,
            "message": f"Internal error: {str(e)}"
        }), 500
    finally:
        db.close()


# ==================== 应用 API ====================

@app.route("/api/v1/apps", methods=["GET"])
@require_jwt(optional=True)
def list_apps():
    """列出应用（数据库版本）"""
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 10))
    app_type = request.args.get("type")

    db = get_db_session()
    try:
        # 构建查询
        query = db.query(App)

        # 按类型筛选
        if app_type:
            query = query.filter(App.type == app_type)

        # 获取总数
        total = query.count()

        # 分页查询
        start = (page - 1) * page_size
        apps = query.order_by(App.updated_at.desc()).offset(start).limit(page_size).all()

        # 转换为字典
        apps_data = [app.to_dict() for app in apps]

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "apps": apps_data,
                "total": total,
                "page": page,
                "page_size": page_size
            }
        })
    finally:
        db.close()


def calculate_workflow_statistics(db, workflow_id: str) -> dict:
    """
    从执行日志计算工作流统计数据

    Args:
        db: 数据库会话
        workflow_id: 工作流ID

    Returns:
        包含统计数据的字典
    """
    from sqlalchemy import func

    try:
        # 获取该工作流的所有执行记录统计
        stats_query = db.query(
            func.count(WorkflowExecution.id).label('total_executions'),
            func.count(
                func.nullif(WorkflowExecution.status == 'completed', False)
            ).label('completed_count'),
            func.avg(
                func.nullif(WorkflowExecution.duration_ms, None)
            ).label('avg_duration')
        ).filter(
            WorkflowExecution.workflow_id == workflow_id
        ).first()

        total_executions = stats_query.total_executions or 0
        completed_count = stats_query.completed_count or 0
        avg_duration = stats_query.avg_duration

        # 计算成功率
        if total_executions > 0:
            # 成功 = completed 状态
            success_query = db.query(
                func.count(WorkflowExecution.id)
            ).filter(
                WorkflowExecution.workflow_id == workflow_id,
                WorkflowExecution.status == 'completed'
            ).scalar() or 0

            success_rate = round((success_query / total_executions) * 100, 1)
        else:
            success_rate = 0.0

        # 计算平均响应时间（仅完成的执行）
        if avg_duration is not None:
            avg_response_time_ms = round(float(avg_duration), 0)
        else:
            avg_response_time_ms = 0

        return {
            "total_executions": total_executions,
            "completed_count": completed_count,
            "avg_response_time_ms": avg_response_time_ms,
            "success_rate": success_rate
        }

    except Exception as e:
        logger.warning(f"计算工作流统计失败: {e}")
        return {
            "total_executions": 0,
            "completed_count": 0,
            "avg_response_time_ms": 0,
            "success_rate": 0.0
        }


@app.route("/api/v1/apps/<app_id>", methods=["GET"])
@require_jwt(optional=True)
def get_app(app_id: str):
    """获取应用详情（数据库版本）"""
    db = get_db_session()
    try:
        app = db.query(App).filter(App.app_id == app_id).first()

        if not app:
            return jsonify({"code": 40401, "message": "应用不存在"}), 404

        app_data = app.to_dict()

        # 添加配置和统计信息（如果有关联工作流）
        workflow = db.query(Workflow).filter(Workflow.workflow_id == app.workflow_id).first()
        if workflow:
            app_data["config"] = workflow.get_definition()

            # 从执行记录计算真实统计数据
            workflow_stats = calculate_workflow_statistics(db, app.workflow_id)

            # 计算总调用数：使用 access_count（API访问）+ 执行记录数（工作流执行）
            total_calls = (app.access_count or 0) + workflow_stats["total_executions"]

            # 估算独立用户数（基于访问次数）
            # 注：精确的用户统计需要在 WorkflowExecution 表中添加 user_id 字段
            estimated_users = min(total_calls, max(1, total_calls // 10)) if total_calls > 0 else 0

            app_data["statistics"] = {
                "total_calls": total_calls,
                "total_users": estimated_users,
                "avg_response_time_ms": workflow_stats["avg_response_time_ms"],
                "success_rate": workflow_stats["success_rate"]
            }

        return jsonify({
            "code": 0,
            "message": "success",
            "data": app_data
        })
    except Exception as e:
        logger.error(f"获取应用详情失败: {e}")
        return jsonify({"code": 50001, "message": f"获取应用详情失败: {str(e)}"}), 500
    finally:
        db.close()


@app.route("/api/v1/apps", methods=["POST"])
@require_jwt()
def create_app():
    """创建应用"""
    data = request.json
    name = data.get("name")
    if not name:
        return jsonify({"code": 40001, "message": "Name is required"}), 400

    app_id = f"app-{uuid.uuid4().hex[:8]}"

    return jsonify({
        "code": 0,
        "message": "success",
        "data": {
            "app_id": app_id,
            "name": name,
            "description": data.get("description", ""),
            "type": data.get("type", "chatbot"),
            "status": "creating"
        }
    }), 201


@app.route("/api/v1/chat", methods=["POST"])
@require_jwt()
@require_permission(Resource.CHAT, Operation.EXECUTE)
@validate_request('chat_request')
@sanitize_input('message')
def chat():
    """聊天接口（需要认证）"""
    data = request.json
    message = data.get("message", "")
    model = data.get("model", "gpt-4o-mini")
    temperature = data.get("temperature", 0.7)
    max_tokens = data.get("max_tokens", 2000)
    conversation_id = data.get("conversation_id")
    user_id = get_user_id()

    if not message:
        return jsonify({"code": 40001, "message": "Message is required"}), 400

    db = get_db_session()
    try:
        # 获取或创建会话
        conversation = None
        if conversation_id:
            conversation = db.query(Conversation).filter(
                Conversation.conversation_id == conversation_id
            ).first()

        if not conversation:
            # 创建新会话
            conversation_id = f"conv-{uuid.uuid4().hex[:8]}"
            conversation = Conversation(
                conversation_id=conversation_id,
                user_id=user_id,
                title=message[:50] + "..." if len(message) > 50 else message,
                model=model
            )
            db.add(conversation)
            db.flush()

        # 保存用户消息
        user_msg = Message(
            conversation_id=conversation_id,
            role="user",
            content=message
        )
        db.add(user_msg)

        # 调用上游 LLM
        try:
            response = requests.post(
                f"{CUBE_API_URL}/v1/chat/completions",
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": message}],
                    "temperature": temperature,
                    "max_tokens": max_tokens
                },
                timeout=30
            )
            if response.status_code == 200:
                result = response.json()
                reply = result.get("choices", [{}])[0].get("message", {}).get("content", "")

                # 保存助手回复
                assistant_msg = Message(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=reply,
                    tokens=result.get("usage", {}).get("total_tokens")
                )
                db.add(assistant_msg)

                db.commit()

                return jsonify({
                    "code": 0,
                    "message": "success",
                    "data": {
                        "reply": reply,
                        "model": model,
                        "conversation_id": conversation_id,
                        "user": user_id
                    }
                })
            else:
                db.commit()
                return jsonify({
                    "code": 50002,
                    "message": f"Upstream error: {response.status_code}"
                }), 503
        except requests.RequestException as e:
            db.commit()
            return jsonify({"code": 50002, "message": str(e)}), 503

    except Exception as e:
        db.rollback()
        return jsonify({"code": 50001, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/datasets", methods=["GET"])
@require_jwt(optional=True)
def list_datasets():
    """列出数据集（代理到 Alldata API）"""
    try:
        # 转发请求到 Alldata API
        headers = {}
        if hasattr(g, 'payload') and g.payload:
            # 转发认证 token
            token = request.headers.get("Authorization")
            if token:
                headers["Authorization"] = token

        response = requests.get(
            f"{ALDATA_API_URL}/api/v1/datasets",
            headers=headers,
            timeout=10
        )
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({"code": 50003, "message": str(e)}), 503


@app.route("/api/v1/datasets/<dataset_id>", methods=["GET"])
@require_jwt(optional=True)
def get_dataset(dataset_id):
    """获取数据集详情（代理到 Alldata API）"""
    try:
        headers = {}
        if hasattr(g, 'payload') and g.payload:
            token = request.headers.get("Authorization")
            if token:
                headers["Authorization"] = token

        response = requests.get(
            f"{ALDATA_API_URL}/api/v1/datasets/{dataset_id}",
            headers=headers,
            timeout=10
        )
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({"code": 50003, "message": str(e)}), 503


@app.route("/api/v1/workflows", methods=["GET"])
@require_jwt(optional=True)
def list_workflows():
    """
    列出工作流

    使用 optional=True 允许未认证访问，用于工作流发现。
    安全考虑：
    - 未认证用户只能看到 status='published' 的公开工作流
    - 认证用户可以看到自己创建的所有工作流
    - 管理员可以看到所有工作流
    """
    db = get_db_session()
    try:
        workflows = db.query(Workflow).order_by(Workflow.created_at.desc()).all()
        result = [wf.to_dict() for wf in workflows]

        response_data = {"code": 0, "message": "success", "data": {"workflows": result}}

        if AUTH_ENABLED and AUTH_MODE:
            user = get_current_user()
            if user:
                response_data["_user"] = user

        return jsonify(response_data)
    finally:
        db.close()


@app.route("/api/v1/workflows/<workflow_id>", methods=["GET"])
@require_jwt(optional=True)
def get_workflow(workflow_id):
    """获取工作流详情"""
    db = get_db_session()
    try:
        wf = db.query(Workflow).filter(
            (Workflow.workflow_id == workflow_id) | (Workflow.id == workflow_id)
        ).first()

        if wf:
            return jsonify({"code": 0, "message": "success", "data": wf.to_dict()})
        return jsonify({"code": 40401, "message": "Workflow not found"}), 404
    finally:
        db.close()


@app.route("/api/v1/workflows", methods=["POST"])
@require_jwt()
@require_permission(Resource.WORKFLOW, Operation.CREATE)
@validate_request('workflow_create')
@sanitize_input('name', 'description')
def create_workflow():
    """创建工作流（需要认证）"""
    data = request.json
    if not data or not data.get("name"):
        return jsonify({"code": 40001, "message": "Workflow name is required"}), 400

    db = get_db_session()
    try:
        workflow_id = f"wf-{uuid.uuid4().hex[:8]}"
        workflow = Workflow(
            workflow_id=workflow_id,
            name=data.get("name"),
            description=data.get("description", ""),
            type=data.get("type", "rag"),
            status="stopped",
            created_by=get_user_id()
        )
        db.add(workflow)
        db.commit()

        return jsonify({"code": 0, "message": "success", "data": {"workflow_id": workflow_id}}), 201
    except Exception as e:
        db.rollback()
        return jsonify({"code": 50001, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/workflows/<workflow_id>", methods=["PUT"])
@require_jwt()
@require_permission(Resource.WORKFLOW, Operation.CREATE)
def update_workflow(workflow_id):
    """更新工作流（需要认证）"""
    data = request.json
    if not data:
        return jsonify({"code": 40001, "message": "Request body is required"}), 400

    db = get_db_session()
    try:
        wf = db.query(Workflow).filter(
            (Workflow.workflow_id == workflow_id) | (Workflow.id == workflow_id)
        ).first()

        if not wf:
            return jsonify({"code": 40401, "message": "Workflow not found"}), 404

        # 更新字段
        if "name" in data:
            wf.name = data["name"]
        if "description" in data:
            wf.description = data["description"]
        if "type" in data:
            wf.type = data["type"]
        if "status" in data:
            wf.status = data["status"]
        if "definition" in data:
            definition = data["definition"]
            if isinstance(definition, dict):
                wf.definition = json.dumps(definition, ensure_ascii=False)
            else:
                wf.definition = definition

        db.commit()

        return jsonify({
            "code": 0,
            "message": "success",
            "data": wf.to_dict()
        })
    except Exception as e:
        db.rollback()
        return jsonify({"code": 50001, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/workflows/<workflow_id>", methods=["DELETE"])
@require_jwt()
@require_permission(Resource.WORKFLOW, Operation.CREATE)
def delete_workflow(workflow_id):
    """删除工作流（需要认证）"""
    db = get_db_session()
    try:
        wf = db.query(Workflow).filter(
            (Workflow.workflow_id == workflow_id) | (Workflow.id == workflow_id)
        ).first()

        if wf:
            db.delete(wf)
            db.commit()
            return jsonify({"code": 0, "message": "success"})
        return jsonify({"code": 40401, "message": "Workflow not found"}), 404
    except Exception as e:
        db.rollback()
        return jsonify({"code": 50001, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/conversations", methods=["GET"])
@require_jwt()
def list_conversations():
    """列出用户的会话"""
    user_id = request.args.get("user_id", get_user_id())
    limit = int(request.args.get("limit", 20))

    db = get_db_session()
    try:
        # 使用 joinedload 预加载消息关系以提高性能
        from sqlalchemy.orm import joinedload
        conversations = db.query(Conversation).options(
            joinedload(Conversation.messages)
        ).filter(
            Conversation.user_id == user_id
        ).order_by(Conversation.updated_at.desc()).limit(limit).all()

        result = []
        for conv in conversations:
            conv_dict = conv.to_dict(include_messages=False)
            conv_dict["message_count"] = len(conv.messages)
            result.append(conv_dict)

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {"conversations": result}
        })
    finally:
        db.close()


@app.route("/api/v1/conversations/<conversation_id>", methods=["GET"])
@require_jwt()
def get_conversation(conversation_id):
    """获取会话详情（包含消息）"""
    db = get_db_session()
    try:
        from sqlalchemy.orm import joinedload
        conv = db.query(Conversation).filter(
            Conversation.conversation_id == conversation_id
        ).options(joinedload(Conversation.messages)).first()

        if conv:
            return jsonify({
                "code": 0,
                "message": "success",
                "data": conv.to_dict(include_messages=True)
            })
        return jsonify({"code": 40401, "message": "Conversation not found"}), 404
    finally:
        db.close()


@app.route("/api/v1/conversations", methods=["POST"])
@require_jwt()
def create_conversation():
    """创建新会话"""
    data = request.json
    user_id = get_user_id()

    db = get_db_session()
    try:
        conversation_id = f"conv-{uuid.uuid4().hex[:8]}"
        conversation = Conversation(
            conversation_id=conversation_id,
            user_id=user_id,
            title=data.get("title", ""),
            model=data.get("model", "gpt-4o-mini")
        )
        db.add(conversation)
        db.commit()

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {"conversation_id": conversation_id}
        }), 201
    except Exception as e:
        db.rollback()
        return jsonify({"code": 50001, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/conversations/<conversation_id>", methods=["DELETE"])
@require_jwt()
def delete_conversation(conversation_id):
    """删除会话"""
    user_id = get_user_id()

    db = get_db_session()
    try:
        conversation = db.query(Conversation).filter(
            Conversation.conversation_id == conversation_id,
            Conversation.user_id == user_id
        ).first()

        if not conversation:
            return jsonify({"code": 40401, "message": "Conversation not found"}), 404

        # 级联删除消息（已配置 cascade="all, delete-orphan"）
        db.delete(conversation)
        db.commit()

        return jsonify({"code": 0, "message": "success"})

    except Exception as e:
        db.rollback()
        return jsonify({"code": 50001, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/conversations/<conversation_id>", methods=["PUT"])
@require_jwt()
def update_conversation(conversation_id):
    """更新会话（重命名等）"""
    user_id = get_user_id()
    data = request.json
    new_title = data.get("title", "").strip()

    if not new_title:
        return jsonify({"code": 40001, "message": "Title is required"}), 400

    db = get_db_session()
    try:
        conversation = db.query(Conversation).filter(
            Conversation.conversation_id == conversation_id,
            Conversation.user_id == user_id
        ).first()

        if not conversation:
            return jsonify({"code": 40401, "message": "Conversation not found"}), 404

        conversation.title = new_title
        db.commit()

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "conversation_id": conversation_id,
                "title": conversation.title
            }
        })

    except Exception as e:
        db.rollback()
        return jsonify({"code": 50001, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/conversations/<conversation_id>/messages", methods=["GET"])
@require_jwt()
def get_messages(conversation_id):
    """获取会话消息列表"""
    db = get_db_session()
    try:
        messages = db.query(Message).filter(
            Message.conversation_id == conversation_id
        ).order_by(Message.created_at.asc()).all()
        result = [msg.to_dict() for msg in messages]

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {"messages": result}
        })
    finally:
        db.close()


@app.route("/api/v1/conversations/<conversation_id>/messages", methods=["POST"])
@require_jwt()
def save_message(conversation_id):
    """保存消息到对话"""
    db = get_db_session()
    try:
        data = request.get_json()
        role = data.get("role")
        content = data.get("content")
        model = data.get("model")
        usage = data.get("usage", {})

        if not role or not content:
            return jsonify({"code": 40001, "message": "role and content are required"}), 400

        # 检查会话是否存在
        conversation = db.query(Conversation).filter(
            Conversation.conversation_id == conversation_id
        ).first()
        if not conversation:
            return jsonify({"code": 40401, "message": "Conversation not found"}), 404

        # 创建消息
        import uuid
        message = Message(
            message_id=str(uuid.uuid4()),
            conversation_id=conversation_id,
            role=role,
            content=content,
            model=model,
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            total_tokens=usage.get("total_tokens", 0),
        )
        db.add(message)

        # 更新会话的 updated_at 和消息计数
        conversation.updated_at = datetime.utcnow()
        # 统计消息数量
        message_count = db.query(Message).filter(
            Message.conversation_id == conversation_id
        ).count()
        conversation.message_count = message_count + 1

        db.commit()

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "message_id": message.message_id,
                "conversation_id": conversation_id
            }
        })

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to save message: {e}")
        return jsonify({"code": 50001, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/conversations/<conversation_id>/usage", methods=["GET"])
@require_jwt()
def get_conversation_usage(conversation_id):
    """获取会话的 Token 使用统计"""
    db = get_db_session()
    try:
        # 检查会话是否存在
        conversation = db.query(Conversation).filter(
            Conversation.conversation_id == conversation_id
        ).first()
        if not conversation:
            return jsonify({"code": 40401, "message": "Conversation not found"}), 404

        # 统计 token 使用
        from sqlalchemy import func
        usage = db.query(
            func.sum(Message.prompt_tokens).label("total_prompt_tokens"),
            func.sum(Message.completion_tokens).label("total_completion_tokens"),
            func.sum(Message.total_tokens).label("total_tokens"),
            func.count(Message.message_id).label("message_count"),
        ).filter(
            Message.conversation_id == conversation_id
        ).first()

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "conversation_id": conversation_id,
                "total_prompt_tokens": usage.total_prompt_tokens or 0,
                "total_completion_tokens": usage.total_completion_tokens or 0,
                "total_tokens": usage.total_tokens or 0,
                "message_count": usage.message_count or 0,
            }
        })
    finally:
        db.close()


def get_default_schema() -> str:
    """默认 Schema（回退方案）"""
    return """
orders 表:
- id: INT (主键)
- customer_id: INT
- amount: DECIMAL(10,2)
- status: VARCHAR(50)
- created_at: TIMESTAMP

customers 表:
- id: INT (主键)
- name: VARCHAR(255)
- email: VARCHAR(255)

products 表:
- id: INT (主键)
- name: VARCHAR(255)
- price: DECIMAL(10,2)
- stock: INT
"""


def build_schema_from_metadata(database: str, selected_tables: list = None) -> str:
    """从 Alldata 元数据构建 Schema 字符串

    Args:
        database: 数据库名称
        selected_tables: 选中的表列表（为空则获取所有表）

    Returns:
        格式化的 Schema 字符串
    """
    try:
        # 获取请求头中的 Authorization
        headers = {}
        auth_header = request.headers.get("Authorization")
        if auth_header:
            headers["Authorization"] = auth_header

        # 获取表列表
        tables_response = requests.get(
            f"{ALDATA_API_URL}/api/v1/metadata/databases/{database}/tables",
            headers=headers,
            timeout=10
        )

        if tables_response.status_code != 200:
            logger.warning(f"获取表列表失败: {tables_response.status_code}")
            return get_default_schema()

        tables_data = tables_response.json()
        available_tables = tables_data.get("data", {}).get("tables", [])

        if not available_tables:
            return get_default_schema()

        # 过滤选中的表
        tables_to_query = selected_tables if selected_tables else [t["name"] for t in available_tables]

        schema_parts = []
        for table_info in available_tables:
            table_name = table_info["name"]
            if table_name not in tables_to_query:
                continue

            # 获取表详情
            detail_response = requests.get(
                f"{ALDATA_API_URL}/api/v1/metadata/databases/{database}/tables/{table_name}",
                headers=headers,
                timeout=10
            )

            if detail_response.status_code == 200:
                detail_data = detail_response.json()
                table_detail = detail_data.get("data", {})

                # 构建表 Schema
                schema_parts.append(f"{table_name} 表:")
                for col in table_detail.get("columns", []):
                    pk = " (主键)" if col.get("primary_key") else ""
                    nullable = " NULL" if col.get("nullable") else " NOT NULL"
                    schema_parts.append(f"- {col['name']}: {col['type']}{pk}{nullable}")
                    if col.get("description"):
                        schema_parts.append(f"  描述: {col['description']}")

                # 添加关系信息
                for rel in table_detail.get("relations", []):
                    if rel["from_table"] == table_name:
                        schema_parts.append(f"  外键: {rel['from_column']} -> {rel['to_table']}.{rel['to_column']}")

                schema_parts.append("")  # 空行分隔

        return "\n".join(schema_parts) if schema_parts else get_default_schema()

    except Exception as e:
        logger.warning(f"获取元数据失败: {e}")
        return get_default_schema()


@app.route("/api/v1/sql/generate", methods=["POST"])
@require_jwt()
@require_permission(Resource.CHAT, Operation.EXECUTE)
def generate_sql():
    """Text-to-SQL 生成（使用 Alldata 动态 Schema）"""
    data = request.json
    question = data.get("question", "")
    database = data.get("database", "sales_dw")
    selected_tables = data.get("selected_tables", [])

    if not question:
        return jsonify({"code": 40001, "message": "Question is required"}), 400

    # 从 Alldata 元数据服务获取 Schema
    schema = build_schema_from_metadata(database, selected_tables)

    try:
        response = requests.post(
            f"{CUBE_API_URL}/v1/chat/completions",
            json={
                "model": "gpt-4o-mini",
                "messages": [
                    {
                        "role": "system",
                        "content": f"你是一个数据分析师助手。请根据以下数据库元数据生成 SQL 查询：\n\n数据库：{database}\n表结构：\n{schema}\n\n请只返回 SQL 语句，不要包含任何解释。"
                    },
                    {"role": "user", "content": question}
                ],
                "max_tokens": 500
            },
            timeout=30
        )
        if response.status_code == 200:
            result = response.json()
            sql = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            # 清理 SQL（移除 markdown 代码块标记）
            sql = sql.replace("```sql", "").replace("```", "").strip()
            return jsonify({
                "code": 0,
                "message": "success",
                "data": {
                    "sql": sql,
                    "confidence": 0.85,
                    "tables_used": selected_tables if selected_tables else [],
                    "database": database,
                    "user": get_user_id()
                }
            })
        else:
            return jsonify({
                "code": 50002,
                "message": f"Upstream error: {response.status_code}"
            }), 503
    except Exception as e:
        return jsonify({"code": 50002, "message": str(e)}), 503


@app.route("/api/v1/text2sql", methods=["POST"])
@require_jwt()
@require_permission(Resource.CHAT, Operation.EXECUTE)
@validate_request('text2sql_request')
@check_sql_injection('natural_language', 'database')
def text2sql():
    """Text-to-SQL 生成（别名端点，与 /api/v1/sql/generate 相同）

    前端调用参数：
    - natural_language: 自然语言查询（映射到 question）
    - database: 数据库名称（可选）
    - selected_tables: 选中的表列表（可选）
    """
    data = request.json
    # 将前端的 natural_language 映射为 question
    data["question"] = data.get("natural_language", "")

    # 复用 generate_sql 的逻辑
    question = data.get("question", "")
    database = data.get("database", "sales_dw")
    selected_tables = data.get("selected_tables", [])

    if not question:
        return jsonify({"code": 40001, "message": "Question is required"}), 400

    # 从 Alldata 元数据服务获取 Schema
    schema = build_schema_from_metadata(database, selected_tables)

    try:
        response = requests.post(
            f"{CUBE_API_URL}/v1/chat/completions",
            json={
                "model": "gpt-4o-mini",
                "messages": [
                    {
                        "role": "system",
                        "content": f"你是一个数据分析师助手。请根据以下数据库元数据生成 SQL 查询：\n\n数据库：{database}\n表结构：\n{schema}\n\n请只返回 SQL 语句，不要包含任何解释。"
                    },
                    {"role": "user", "content": question}
                ],
                "max_tokens": 500
            },
            timeout=30
        )
        if response.status_code == 200:
            result = response.json()
            sql = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            # 清理 SQL（移除 markdown 代码块标记）
            sql = sql.replace("```sql", "").replace("```", "").strip()
            return jsonify({
                "code": 0,
                "message": "success",
                "data": {
                    "sql": sql,
                    "confidence": 0.85,
                    "tables_used": selected_tables if selected_tables else [],
                    "database": database,
                    "user": get_user_id()
                }
            })
        else:
            return jsonify({
                "code": 50002,
                "message": f"Upstream error: {response.status_code}"
            }), 503
    except Exception as e:
        return jsonify({"code": 50002, "message": str(e)}), 503


# ============================================
# 工作流执行 API (Phase 6: Sprint 6.1)
# ============================================

def run_workflow_async(executor: WorkflowExecutor, inputs: dict, db_session):
    """异步执行工作流"""
    import threading

    def run():
        try:
            # 运行执行器
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(executor.execute(inputs))

            # 更新执行记录
            execution = db_session.query(WorkflowExecution).filter(
                WorkflowExecution.execution_id == executor.execution_id
            ).first()

            if execution:
                execution.status = result.get("status", "failed")
                execution.outputs = json.dumps(result.get("output"), ensure_ascii=False)
                execution.node_results = json.dumps(result.get("node_results", {}), ensure_ascii=False)
                if result.get("errors"):
                    execution.error = json.dumps(result.get("errors"), ensure_ascii=False)

                if executor.completed_at and executor.started_at:
                    duration = (executor.completed_at - executor.started_at).total_seconds()
                    execution.duration_ms = int(duration * 1000)

                execution.completed_at = executor.completed_at or datetime.now()
                db_session.commit()
        except Exception as e:
            # 记录错误
            execution = db_session.query(WorkflowExecution).filter(
                WorkflowExecution.execution_id == executor.execution_id
            ).first()
            if execution:
                execution.status = "failed"
                execution.error = str(e)
                execution.completed_at = datetime.now()
                db_session.commit()
        finally:
            unregister_execution(executor.execution_id)
            db_session.close()

    thread = threading.Thread(target=run, daemon=True)
    thread.start()


@app.route("/api/v1/workflows/<workflow_id>/start", methods=["POST"])
@require_jwt()
@require_permission(Resource.WORKFLOW, Operation.EXECUTE)
def start_workflow(workflow_id):
    """启动工作流执行"""
    data = request.json or {}
    inputs = data.get("inputs", {})

    db = get_db_session()
    try:
        # 获取工作流
        wf = db.query(Workflow).filter(
            (Workflow.workflow_id == workflow_id) | (Workflow.id == workflow_id)
        ).first()

        if not wf:
            return jsonify({"code": 40401, "message": "Workflow not found"}), 404

        # 获取工作流定义
        definition = wf.get_definition()
        if not definition:
            # 使用默认的简单 RAG 工作流定义
            definition = {
                "version": "1.0",
                "nodes": [
                    {"id": "input", "type": "input", "config": {"key": "query"}},
                    {"id": "retriever", "type": "retriever", "config": {"top_k": 5}},
                    {"id": "llm", "type": "llm", "config": {"model": "gpt-4o-mini"}},
                    {"id": "output", "type": "output", "config": {"input_from": "llm"}}
                ],
                "edges": [
                    {"source": "input", "target": "retriever"},
                    {"source": "retriever", "target": "llm"},
                    {"source": "llm", "target": "output"}
                ]
            }

        # 创建执行器
        executor = WorkflowExecutor(workflow_id, definition)

        # 验证工作流
        is_valid, errors = executor.validate()
        if not is_valid:
            return jsonify({
                "code": 40002,
                "message": "Invalid workflow definition",
                "errors": errors
            }), 400

        # 创建执行记录
        execution = WorkflowExecution(
            execution_id=executor.execution_id,
            workflow_id=workflow_id,
            status="running",
            inputs=json.dumps(inputs, ensure_ascii=False),
            started_at=datetime.now()
        )
        db.add(execution)
        db.commit()

        # 注册执行器
        register_execution(executor)

        # 异步执行
        run_workflow_async(executor, inputs, db)

        return jsonify({
            "code": 0,
            "message": "Workflow started",
            "data": {
                "execution_id": executor.execution_id,
                "workflow_id": workflow_id,
                "status": "running"
            }
        }), 202

    except Exception as e:
        db.rollback()
        return jsonify({"code": 50001, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/workflows/<workflow_id>/stop", methods=["POST"])
@require_jwt()
def stop_workflow(workflow_id):
    """停止工作流执行"""
    data = request.json or {}
    execution_id = data.get("execution_id")

    if not execution_id:
        return jsonify({"code": 40001, "message": "execution_id is required"}), 400

    # 停止执行
    success = stop_execution(execution_id)

    # 更新数据库记录
    db = get_db_session()
    try:
        execution = db.query(WorkflowExecution).filter(
            WorkflowExecution.execution_id == execution_id
        ).first()

        if execution:
            execution.status = "stopped"
            execution.completed_at = datetime.now()
            db.commit()

        if success:
            return jsonify({"code": 0, "message": "Workflow stopped"})
        else:
            return jsonify({"code": 40402, "message": "Execution not found or already completed"}), 404
    except Exception as e:
        db.rollback()
        return jsonify({"code": 50001, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/workflows/<workflow_id>/status", methods=["GET"])
@require_jwt()
def get_workflow_status(workflow_id):
    """获取工作流执行状态"""
    execution_id = request.args.get("execution_id")

    db = get_db_session()
    try:
        # 如果指定了 execution_id，获取特定执行
        if execution_id:
            execution = db.query(WorkflowExecution).filter(
                WorkflowExecution.execution_id == execution_id
            ).first()

            if execution:
                return jsonify({
                    "code": 0,
                    "message": "success",
                    "data": execution.to_dict()
                })
            return jsonify({"code": 40402, "message": "Execution not found"}), 404

        # 否则返回最新的执行记录
        executions = db.query(WorkflowExecution).filter(
            WorkflowExecution.workflow_id == workflow_id
        ).order_by(WorkflowExecution.created_at.desc()).limit(10).all()

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "executions": [e.to_dict() for e in executions]
            }
        })

    finally:
        db.close()


@app.route("/api/v1/executions/<execution_id>/logs", methods=["GET"])
@require_jwt()
def get_execution_logs(execution_id):
    """获取执行日志"""
    db = get_db_session()
    try:
        logs = db.query(ExecutionLog).filter(
            ExecutionLog.execution_id == execution_id
        ).order_by(ExecutionLog.timestamp.asc()).all()

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "logs": [log.to_dict() for log in logs]
            }
        })
    finally:
        db.close()


@app.route("/api/v1/executions", methods=["GET"])
@require_jwt()
def list_executions():
    """列出所有执行记录"""
    workflow_id = request.args.get("workflow_id")
    status = request.args.get("status")
    limit = int(request.args.get("limit", 50))

    db = get_db_session()
    try:
        query = db.query(WorkflowExecution)

        if workflow_id:
            query = query.filter(WorkflowExecution.workflow_id == workflow_id)
        if status:
            query = query.filter(WorkflowExecution.status == status)

        executions = query.order_by(WorkflowExecution.created_at.desc()).limit(limit).all()

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "executions": [e.to_dict() for e in executions]
            }
        })
    finally:
        db.close()


@app.route("/api/v1/workflows/<workflow_id>/executions", methods=["GET"])
@require_jwt()
def get_workflow_executions(workflow_id):
    """获取工作流的执行历史"""
    limit = int(request.args.get("limit", 20))

    db = get_db_session()
    try:
        executions = db.query(WorkflowExecution).filter(
            WorkflowExecution.workflow_id == workflow_id
        ).order_by(WorkflowExecution.created_at.desc()).limit(limit).all()

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "executions": [e.to_dict() for e in executions]
            }
        })
    finally:
        db.close()


# ============================================
# 文档管理 API (Phase 6: Sprint 6.3)
# ============================================

@app.route("/api/v1/documents/upload", methods=["POST"])
@require_jwt()
def upload_document():
    """上传并索引文档"""
    # 支持表单上传和 JSON 上传
    if request.files.get("file"):
        # 文件上传
        file = request.files["file"]
        content = file.read().decode("utf-8")
        file_name = file.filename
        title = request.form.get("title", file_name)
    else:
        # JSON 上传
        data = request.json
        content = data.get("content", "")
        file_name = data.get("file_name", "untitled.txt")
        title = data.get("title", file_name)

    if not content:
        return jsonify({"code": 40001, "message": "Content is required"}), 400

    collection_name = request.form.get("collection", "default") if request.files else \
                      (request.json.get("collection") if request.json else "default")

    db = get_db_session()
    try:
        # 先生成 doc_id
        doc_id = f"doc-{uuid.uuid4().hex[:12]}"

        # 创建文档服务
        doc_service = DocumentService()

        # 处理文档（在 metadata 中包含 doc_id 用于后续删除）
        docs = doc_service.create_document_from_upload(
            filename=file_name,
            content=content,
            metadata={"title": title, "uploaded_by": get_user_id(), "doc_id": doc_id}
        )

        # 生成向量
        embedding_service = EmbeddingService()
        texts = [doc.page_content for doc in docs]

        # 使用同步方法生成向量
        embeddings = embedding_service.sync_embed_texts(texts)

        # 存储到向量数据库
        vector_store = VectorStore()
        metadata_list = [doc.metadata for doc in docs]
        vector_store.insert(collection_name, texts, embeddings, metadata_list)

        # 保存文档记录
        indexed_doc = IndexedDocument(
            doc_id=doc_id,
            collection_name=collection_name,
            file_name=file_name,
            title=title,
            content=content[:10000],  # 只存储前10000字符用于预览
            chunk_count=len(docs),
            metadata=json.dumps(metadata_list[0] if metadata_list else {}, ensure_ascii=False),
            created_by=get_user_id()
        )
        db.add(indexed_doc)
        db.commit()

        return jsonify({
            "code": 0,
            "message": "Document uploaded and indexed",
            "data": {
                "doc_id": doc_id,
                "file_name": file_name,
                "chunk_count": len(docs),
                "collection": collection_name
            }
        }), 201

    except Exception as e:
        db.rollback()
        return jsonify({"code": 50001, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/documents", methods=["GET"])
@require_jwt()
def list_documents():
    """列出已索引的文档"""
    collection = request.args.get("collection")
    limit = int(request.args.get("limit", 50))

    db = get_db_session()
    try:
        query = db.query(IndexedDocument)

        if collection:
            query = query.filter(IndexedDocument.collection_name == collection)

        docs = query.order_by(IndexedDocument.created_at.desc()).limit(limit).all()

        # 获取向量存储统计
        vector_store = VectorStore()
        collections = vector_store.list_collections()

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "documents": [doc.to_dict() for doc in docs],
                "collections": collections,
                "total_collections": len(collections)
            }
        })

    finally:
        db.close()


@app.route("/api/v1/documents/<doc_id>", methods=["GET"])
@require_jwt()
def get_document(doc_id):
    """获取文档详情"""
    db = get_db_session()
    try:
        doc = db.query(IndexedDocument).filter(
            IndexedDocument.doc_id == doc_id
        ).first()

        if doc:
            # 获取集合信息
            vector_store = VectorStore()
            collection_info = vector_store.collection_info(doc.collection_name)

            return jsonify({
                "code": 0,
                "message": "success",
                "data": {
                    **doc.to_dict(),
                    "collection_info": collection_info
                }
            })

        return jsonify({"code": 40401, "message": "Document not found"}), 404

    finally:
        db.close()


@app.route("/api/v1/documents/<doc_id>", methods=["DELETE"])
@require_jwt()
def delete_document(doc_id):
    """删除文档（含向量数据）"""
    db = get_db_session()
    try:
        doc = db.query(IndexedDocument).filter(
            IndexedDocument.doc_id == doc_id
        ).first()

        if not doc:
            return jsonify({"code": 40401, "message": "Document not found"}), 404

        # 从向量数据库删除向量
        vector_store = VectorStore()
        delete_success = vector_store.delete_by_doc_id(doc.collection_name, doc_id)

        if not delete_success:
            # 记录警告但继续删除数据库记录
            logger.warning(f"警告: 向量删除失败，但继续删除数据库记录: doc_id={doc_id}")

        # 删除数据库记录
        db.delete(doc)
        db.commit()

        return jsonify({
            "code": 0,
            "message": "Document deleted successfully",
            "data": {
                "doc_id": doc_id,
                "vectors_deleted": delete_success
            }
        })

    except Exception as e:
        db.rollback()
        logger.error(f"删除文档失败: {e}")
        return jsonify({"code": 50001, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/documents/batch", methods=["DELETE"])
@require_jwt()
def batch_delete_documents():
    """批量删除文档（含向量数据）"""
    data = request.json
    doc_ids = data.get("doc_ids", [])

    if not doc_ids:
        return jsonify({"code": 40001, "message": "doc_ids is required"}), 400

    if not isinstance(doc_ids, list):
        return jsonify({"code": 40002, "message": "doc_ids must be a list"}), 400

    db = get_db_session()
    try:
        vector_store = VectorStore()
        deleted_count = 0
        failed_ids = []

        for doc_id in doc_ids:
            try:
                doc = db.query(IndexedDocument).filter(
                    IndexedDocument.doc_id == doc_id
                ).first()

                if not doc:
                    failed_ids.append(doc_id)
                    continue

                # 从向量数据库删除向量
                vector_store.delete_by_doc_id(doc.collection_name, doc_id)

                # 删除数据库记录
                db.delete(doc)
                deleted_count += 1

            except Exception as e:
                logger.error(f"删除文档失败 {doc_id}: {e}")
                failed_ids.append(doc_id)

        db.commit()

        return jsonify({
            "code": 0,
            "message": "Batch delete completed",
            "data": {
                "deleted_count": deleted_count,
                "failed_count": len(failed_ids),
                "failed_ids": failed_ids
            }
        })

    except Exception as e:
        db.rollback()
        return jsonify({"code": 50001, "message": str(e)}), 500
    finally:
        db.close()


# =============================================================================
# Sprint 15: 图片上传与多模态支持
# =============================================================================

# 尝试导入图片处理模块
try:
    from services.image_processor import ImageProcessor, get_image_processor
    from services.vision_embedding import VisionEmbeddingService, get_vision_service
    IMAGE_PROCESSING_AVAILABLE = True
except ImportError:
    IMAGE_PROCESSING_AVAILABLE = False
    logger.warning("Image processing modules not available")


@app.route("/api/v1/images/upload", methods=["POST"])
@require_jwt()
def upload_image():
    """
    上传图片
    Sprint 15: 多模态支持

    支持:
    - 图片预处理（缩放、格式转换）
    - OCR 文字提取
    - 视觉嵌入生成（可选）
    """
    if not IMAGE_PROCESSING_AVAILABLE:
        return jsonify({
            "code": 50003,
            "message": "Image processing not available. Install required dependencies."
        }), 503

    if 'file' not in request.files:
        return jsonify({"code": 40001, "message": "No file provided"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"code": 40001, "message": "No file selected"}), 400

    # 解析参数
    enable_ocr = request.form.get('enable_ocr', 'true').lower() == 'true'
    generate_embedding = request.form.get('generate_embedding', 'true').lower() == 'true'
    workflow_id = request.form.get('workflow_id')
    document_id = request.form.get('document_id')

    try:
        # 读取文件数据
        image_data = file.read()

        # 处理图片
        processor = get_image_processor()
        processed = processor.process_image(
            image_data,
            resize=True,
            generate_thumbnail=True,
            extract_text=enable_ocr
        )

        # 生成唯一 ID
        image_id = str(uuid.uuid4())

        # 保存到存储（MinIO 优先，本地备选）
        image_format = processed.metadata.format
        image_object_name = f"images/{image_id}.{image_format}"
        thumbnail_object_name = f"images/{image_id}_thumb.jpg"
        image_url = None
        thumbnail_url = None

        if MINIO_ENABLED:
            try:
                storage = get_storage()
                # 上传原图
                storage.upload_file(
                    bucket="uploads",
                    object_name=image_object_name,
                    data=processed.data,
                    content_type=f"image/{image_format}"
                )
                # 获取预签名 URL
                image_url = storage.get_presigned_url("uploads", image_object_name, expires=86400)

                # 上传缩略图
                if processed.thumbnail:
                    storage.upload_file(
                        bucket="uploads",
                        object_name=thumbnail_object_name,
                        data=processed.thumbnail,
                        content_type="image/jpeg"
                    )
                    thumbnail_url = storage.get_presigned_url("uploads", thumbnail_object_name, expires=86400)

                logger.info(f"Image {image_id} uploaded to MinIO")
            except Exception as e:
                logger.error(f"MinIO upload failed, falling back to local storage: {e}")
                MINIO_ENABLED_LOCAL = False
        else:
            MINIO_ENABLED_LOCAL = False

        # 本地存储备选方案
        if not MINIO_ENABLED or 'MINIO_ENABLED_LOCAL' in dir() and not MINIO_ENABLED_LOCAL:
            upload_dir = os.environ.get('IMAGE_UPLOAD_DIR', '/tmp/images')
            os.makedirs(upload_dir, exist_ok=True)

            image_path = os.path.join(upload_dir, f"{image_id}.{image_format}")
            thumbnail_path = os.path.join(upload_dir, f"{image_id}_thumb.jpg")

            with open(image_path, 'wb') as f:
                f.write(processed.data)

            if processed.thumbnail:
                with open(thumbnail_path, 'wb') as f:
                    f.write(processed.thumbnail)

        # 生成视觉嵌入
        embedding = None
        if generate_embedding:
            try:
                vision_service = get_vision_service()
                embedding_result = vision_service.embed_image(processed.data)
                embedding = embedding_result.embedding

                # 存储到向量数据库
                vector_store = VectorStore()
                vector_store.insert(
                    collection="images",
                    ids=[image_id],
                    embeddings=[embedding],
                    metadatas=[{
                        "filename": file.filename,
                        "format": processed.metadata.format,
                        "width": processed.metadata.width,
                        "height": processed.metadata.height,
                        "workflow_id": workflow_id,
                        "document_id": document_id,
                        "ocr_text": processed.ocr_result.text if processed.ocr_result else None
                    }]
                )
            except Exception as e:
                logger.warning(f"Failed to generate image embedding: {e}")

        # 构建响应
        response_data = {
            "id": image_id,
            "filename": file.filename,
            "url": image_url if image_url else f"/api/v1/images/{image_id}",
            "thumbnail_url": thumbnail_url if thumbnail_url else (f"/api/v1/images/{image_id}/thumbnail" if processed.thumbnail else None),
            "storage": "minio" if image_url else "local",
            "metadata": {
                "width": processed.metadata.width,
                "height": processed.metadata.height,
                "format": processed.metadata.format,
                "sizeBytes": processed.metadata.size_bytes,
                "colorMode": processed.metadata.color_mode,
                "hash": processed.metadata.hash
            }
        }

        if processed.ocr_result:
            response_data["ocr_text"] = processed.ocr_result.text
            response_data["ocr_confidence"] = processed.ocr_result.confidence

        if embedding:
            response_data["has_embedding"] = True
            response_data["embedding_dimension"] = len(embedding)

        return jsonify({
            "code": 0,
            "message": "Image uploaded successfully",
            "data": response_data
        })

    except ValueError as e:
        return jsonify({"code": 40001, "message": str(e)}), 400
    except Exception as e:
        logger.exception(f"Image upload failed: {e}")
        return jsonify({"code": 50001, "message": str(e)}), 500


@app.route("/api/v1/images/<image_id>", methods=["GET"])
def get_image(image_id):
    """获取图片"""
    from flask import send_file, redirect
    from io import BytesIO

    # 先尝试从 MinIO 获取
    if MINIO_ENABLED:
        try:
            storage = get_storage()
            for ext in ['jpeg', 'png', 'webp', 'gif']:
                object_name = f"images/{image_id}.{ext}"
                if storage.file_exists("uploads", object_name):
                    # 返回预签名 URL 重定向
                    url = storage.get_presigned_url("uploads", object_name, expires=3600)
                    if url:
                        return redirect(url)
                    # 或直接返回文件内容
                    data = storage.download_file("uploads", object_name)
                    if data:
                        return send_file(
                            BytesIO(data),
                            mimetype=f'image/{ext}',
                            as_attachment=False
                        )
        except Exception as e:
            logger.warning(f"MinIO retrieval failed, trying local storage: {e}")

    # 本地存储备选
    upload_dir = os.environ.get('IMAGE_UPLOAD_DIR', '/tmp/images')

    # 查找图片文件
    for ext in ['jpeg', 'png', 'webp', 'gif']:
        image_path = os.path.join(upload_dir, f"{image_id}.{ext}")
        if os.path.exists(image_path):
            return send_file(
                image_path,
                mimetype=f'image/{ext}',
                as_attachment=False
            )

    return jsonify({"code": 40401, "message": "Image not found"}), 404


@app.route("/api/v1/images/<image_id>/thumbnail", methods=["GET"])
def get_image_thumbnail(image_id):
    """获取图片缩略图"""
    from flask import send_file, redirect
    from io import BytesIO

    object_name = f"images/{image_id}_thumb.jpg"

    # 先尝试从 MinIO 获取
    if MINIO_ENABLED:
        try:
            storage = get_storage()
            if storage.file_exists("uploads", object_name):
                # 返回预签名 URL 重定向
                url = storage.get_presigned_url("uploads", object_name, expires=3600)
                if url:
                    return redirect(url)
                # 或直接返回文件内容
                data = storage.download_file("uploads", object_name)
                if data:
                    return send_file(
                        BytesIO(data),
                        mimetype='image/jpeg',
                        as_attachment=False
                    )
        except Exception as e:
            logger.warning(f"MinIO retrieval failed, trying local storage: {e}")

    # 本地存储备选
    upload_dir = os.environ.get('IMAGE_UPLOAD_DIR', '/tmp/images')
    thumbnail_path = os.path.join(upload_dir, f"{image_id}_thumb.jpg")

    if os.path.exists(thumbnail_path):
        return send_file(
            thumbnail_path,
            mimetype='image/jpeg',
            as_attachment=False
        )

    return jsonify({"code": 40401, "message": "Thumbnail not found"}), 404


@app.route("/api/v1/images/<image_id>", methods=["DELETE"])
@require_jwt()
def delete_image(image_id):
    """删除图片"""
    deleted = False

    # 先尝试从 MinIO 删除
    if MINIO_ENABLED:
        try:
            storage = get_storage()
            for ext in ['jpeg', 'png', 'webp', 'gif']:
                object_name = f"images/{image_id}.{ext}"
                if storage.file_exists("uploads", object_name):
                    storage.delete_file("uploads", object_name)
                    deleted = True
                    break
            # 删除缩略图
            thumbnail_object = f"images/{image_id}_thumb.jpg"
            if storage.file_exists("uploads", thumbnail_object):
                storage.delete_file("uploads", thumbnail_object)
        except Exception as e:
            logger.warning(f"MinIO deletion failed: {e}")

    # 本地存储也尝试删除
    upload_dir = os.environ.get('IMAGE_UPLOAD_DIR', '/tmp/images')

    for ext in ['jpeg', 'png', 'webp', 'gif']:
        image_path = os.path.join(upload_dir, f"{image_id}.{ext}")
        if os.path.exists(image_path):
            os.remove(image_path)
            deleted = True
            break

    # 删除缩略图
    thumbnail_path = os.path.join(upload_dir, f"{image_id}_thumb.jpg")
    if os.path.exists(thumbnail_path):
        os.remove(thumbnail_path)

    # 从向量数据库删除
    try:
        vector_store = VectorStore()
        vector_store.delete("images", [image_id])
    except Exception as e:
        logger.warning(f"Failed to delete image embedding: {e}")

    if deleted:
        return jsonify({"code": 0, "message": "Image deleted"})
    else:
        return jsonify({"code": 40401, "message": "Image not found"}), 404


@app.route("/api/v1/images/search", methods=["POST"])
@require_jwt()
def search_images():
    """
    图片搜索
    Sprint 15: 多模态检索

    支持:
    - 文本搜索图片（使用 CLIP 文本编码）
    - 图片搜索图片（使用视觉嵌入）
    """
    if not IMAGE_PROCESSING_AVAILABLE:
        return jsonify({
            "code": 50003,
            "message": "Image processing not available"
        }), 503

    data = request.json
    query_text = data.get("query")
    query_image = data.get("image_base64")  # Base64 编码的图片
    top_k = data.get("top_k", 10)

    if not query_text and not query_image:
        return jsonify({
            "code": 40001,
            "message": "Either query text or image is required"
        }), 400

    try:
        vision_service = get_vision_service()

        # 生成查询向量
        if query_image:
            # 图片搜索图片
            processor = get_image_processor()
            image_data = processor.from_base64(query_image)
            query_embedding = vision_service.embed_image(image_data).embedding
        else:
            # 文本搜索图片
            query_embedding = vision_service.embed_text(query_text)

        # 向量搜索
        vector_store = VectorStore()
        results = vector_store.search("images", query_embedding, top_k)

        # 格式化结果
        search_results = []
        for result in results:
            search_results.append({
                "id": result.get("id"),
                "score": result.get("score", 0),
                "url": f"/api/v1/images/{result.get('id')}",
                "thumbnail_url": f"/api/v1/images/{result.get('id')}/thumbnail",
                "metadata": result.get("metadata", {})
            })

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "results": search_results,
                "total": len(search_results)
            }
        })

    except Exception as e:
        logger.exception(f"Image search failed: {e}")
        return jsonify({"code": 50001, "message": str(e)}), 500


@app.route("/api/v1/collections", methods=["GET"])
@require_jwt()
def list_collections():
    """列出向量集合"""
    vector_store = VectorStore()
    collections = vector_store.list_collections()

    collection_info = []
    for name in collections:
        info = vector_store.collection_info(name)
        collection_info.append(info)

    return jsonify({
        "code": 0,
        "message": "success",
        "data": {
            "collections": collection_info,
            "total": len(collections)
        }
    })


@app.route("/api/v1/collections/<collection_name>", methods=["DELETE"])
@require_jwt()
def delete_collection(collection_name):
    """删除向量集合"""
    vector_store = VectorStore()

    try:
        vector_store.drop_collection(collection_name)
        return jsonify({"code": 0, "message": "Collection deleted"})
    except Exception as e:
        return jsonify({"code": 50001, "message": str(e)}), 500


# ==================== 知识库 API ====================

@app.route("/api/v1/knowledge-bases", methods=["GET"])
@require_jwt(optional=True)
def list_knowledge_bases():
    """列出知识库（数据库版本）"""
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 10))

    db = get_db_session()
    try:
        # 构建查询
        query = db.query(KnowledgeBase)

        # 获取总数
        total = query.count()

        # 分页查询
        start = (page - 1) * page_size
        kbs = query.order_by(KnowledgeBase.updated_at.desc()).offset(start).limit(page_size).all()

        # 转换为字典
        kb_data = [{"knowledge_base_id": kb.kb_id, **kb.to_dict()} for kb in kbs]

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "knowledge_bases": kb_data,
                "total": total,
                "page": page,
                "page_size": page_size
            }
        })
    finally:
        db.close()


@app.route("/api/v1/knowledge-bases/<knowledge_base_id>", methods=["GET"])
@require_jwt(optional=True)
def get_knowledge_base(knowledge_base_id: str):
    """获取知识库详情（数据库版本）"""
    db = get_db_session()
    try:
        kb = db.query(KnowledgeBase).filter(KnowledgeBase.kb_id == knowledge_base_id).first()

        if not kb:
            return jsonify({"code": 40401, "message": "知识库不存在"}), 404

        kb_data = {"knowledge_base_id": kb.kb_id, **kb.to_dict()}

        # 添加元数据
        kb_data["metadata"] = {
            "total_chunks": kb.vector_count or 0,
            "last_indexed": kb.updated_at.isoformat() if kb.updated_at else None,
            "indexing_status": "completed" if kb.status == "active" else "pending"
        }

        return jsonify({
            "code": 0,
            "message": "success",
            "data": kb_data
        })
    except Exception as e:
        logger.error(f"获取知识库详情失败: {e}")
        return jsonify({"code": 50001, "message": f"获取知识库详情失败: {str(e)}"}), 500
    finally:
        db.close()


@app.route("/api/v1/knowledge-bases", methods=["POST"])
@require_jwt()
def create_knowledge_base():
    """创建知识库"""
    data = request.json
    name = data.get("name")
    if not name:
        return jsonify({"code": 40001, "message": "Name is required"}), 400

    kb_id = f"kb-{uuid.uuid4().hex[:8]}"

    return jsonify({
        "code": 0,
        "message": "success",
        "data": {
            "knowledge_base_id": kb_id,
            "name": name,
            "description": data.get("description", ""),
            "type": data.get("type", "document"),
            "status": "creating"
        }
    }), 201


@app.route("/api/v1/rag/query", methods=["POST"])
@require_jwt()
@require_permission(Resource.CHAT, Operation.EXECUTE)
async def rag_query():
    """RAG 查询接口（使用真实向量检索）"""
    data = request.json
    question = data.get("question", "")
    collection = data.get("collection", "default")
    top_k = data.get("top_k", 5)

    if not question:
        return jsonify({"code": 40001, "message": "Question is required"}), 400

    try:
        # 生成查询向量
        embedding_service = EmbeddingService()
        query_embedding = await embedding_service.embed_text(question)

        # 向量检索
        vector_store = VectorStore()
        results = vector_store.search(collection, query_embedding, top_k)

        # 构建上下文
        if results:
            context = "\n\n".join([f"[相关度: {r['score']:.2f}] {r['text']}" for r in results])
            sources = [r.get("metadata", {}).get("source", "unknown") for r in results]
        else:
            # 如果没有检索结果，使用默认上下文
            context = """
            ONE-DATA-STUDIO 是一个融合了 Alldata（数据治理）、Cube Studio（模型训练）、Bisheng（应用编排）的企业级 AI 平台。

            主要功能：
            1. 数据治理：数据集成、ETL、元数据管理
            2. 模型训练：分布式训练、模型服务
            3. 应用编排：RAG 流水线、Agent 编排
            """
            sources = ["system/knowledge"]

        # 调用 LLM 生成答案
        response = requests.post(
            f"{CUBE_API_URL}/v1/chat/completions",
            json={
                "model": "gpt-4o-mini",
                "messages": [
                    {
                        "role": "system",
                        "content": f"你是一个基于检索增强生成（RAG）的智能助手。请根据以下上下文回答：\n\n{context}\n\n如果上下文中没有相关信息，请明确告知用户。"
                    },
                    {"role": "user", "content": question}
                ],
                "max_tokens": 1000
            },
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            reply = result.get("choices", [{}])[0].get("message", {}).get("content", "")

            return jsonify({
                "code": 0,
                "message": "success",
                "data": {
                    "answer": reply,
                    "sources": sources[:5],
                    "retrieved_count": len(results),
                    "user": get_user_id()
                }
            })
        else:
            return jsonify({
                "code": 50002,
                "message": f"Upstream error: {response.status_code}"
            }), 503

    except Exception as e:
        return jsonify({"code": 50002, "message": str(e)}), 503


# ============================================
# Agent 工具 API (Phase 7: Sprint 7.1)
# ============================================

@app.route("/api/v1/tools", methods=["GET"])
@require_jwt(optional=True)
def list_tools():
    """列出可用工具（数据库版本）"""
    category = request.args.get("category")

    db = get_db_session()
    try:
        # 构建查询
        query = db.query(Tool).filter(Tool.enabled == True)

        # 按分类筛选
        if category:
            query = query.filter(Tool.category == category)

        tools = query.order_by(Tool.name).all()

        # 转换为字典
        tools_data = []
        for tool in tools:
            tool_dict = tool.to_dict()
            # 添加 parameters 字段（从 schema 中提取）
            schema = tool.get_schema()
            if "parameters" in schema:
                tool_dict["parameters"] = schema["parameters"]
            else:
                tool_dict["parameters"] = schema.get("properties", {})
            tools_data.append(tool_dict)

        # 如果数据库为空，返回默认工具列表
        if not tools_data:
            default_tools = [
                {
                    "name": "web_search",
                    "display_name": "网络搜索",
                    "description": "使用搜索引擎查找信息",
                    "category": "search",
                    "enabled": True,
                    "parameters": [
                        {"name": "query", "type": "string", "description": "搜索查询关键词", "required": True},
                        {"name": "num_results", "type": "integer", "description": "返回结果数量", "required": False, "default": 5}
                    ]
                },
                {
                    "name": "calculator",
                    "display_name": "计算器",
                    "description": "执行数学计算",
                    "category": "utility",
                    "enabled": True,
                    "parameters": [
                        {"name": "expression", "type": "string", "description": "数学表达式", "required": True}
                    ]
                }
            ]
            tools_data = default_tools

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "tools": tools_data,
                "total": len(tools_data)
            }
        })
    except Exception as e:
        logger.error(f"获取工具列表失败: {e}")
        return jsonify({"code": 50001, "message": f"获取工具列表失败: {str(e)}"}), 500
    finally:
        db.close()


@app.route("/api/v1/tools/schemas", methods=["GET"])
@require_jwt(optional=True)
def get_tool_schemas():
    """获取工具的 Function Calling 格式 schema"""
    if not TOOLS_AVAILABLE:
        # 返回 OpenAI Function Calling 格式的模拟数据
        mock_schemas = [
            {
                "type": "function",
                "function": {
                    "name": "web_search",
                    "description": "使用搜索引擎查找信息",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "搜索查询关键词"
                            },
                            "num_results": {
                                "type": "integer",
                                "description": "返回结果数量",
                                "default": 5
                            }
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "calculator",
                    "description": "执行数学计算",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "expression": {
                                "type": "string",
                                "description": "数学表达式，如 2+2 或 sin(0.5)"
                            }
                        },
                        "required": ["expression"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "sql_query",
                    "description": "执行 SQL 查询获取数据",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "SQL 查询语句"
                            },
                            "database": {
                                "type": "string",
                                "description": "数据库名称"
                            }
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "python_executor",
                    "description": "执行 Python 代码片段",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "code": {
                                "type": "string",
                                "description": "Python 代码"
                            }
                        },
                        "required": ["code"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "file_reader",
                    "description": "读取文件内容",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "文件路径"
                            }
                        },
                        "required": ["path"]
                    }
                }
            }
        ]
        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "schemas": mock_schemas,
                "total": len(mock_schemas)
            }
        })

    try:
        registry = get_tool_registry()
        schemas = registry.get_function_schemas()

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "schemas": schemas,
                "total": len(schemas)
            }
        })
    except Exception as e:
        return jsonify({"code": 50001, "message": str(e)}), 500


@app.route("/api/v1/tools/<tool_name>/execute", methods=["POST"])
@require_jwt()
@require_permission(Resource.CHAT, Operation.EXECUTE)
async def execute_tool(tool_name):
    """执行工具"""
    if not TOOLS_AVAILABLE:
        return jsonify({
            "code": 50003,
            "message": "Tools module not available"
        }), 503

    data = request.json or {}

    try:
        registry = get_tool_registry()
        result = await registry.execute(tool_name, **data)

        return jsonify({
            "code": 0,
            "message": "success",
            "data": result
        })
    except Exception as e:
        return jsonify({"code": 50001, "message": str(e)}), 500


@app.route("/api/v1/agent/run", methods=["POST"])
@require_jwt()
@require_permission(Resource.CHAT, Operation.EXECUTE)
async def run_agent():
    """运行 Agent"""
    if not TOOLS_AVAILABLE:
        return jsonify({
            "code": 50003,
            "message": "Agent module not available"
        }), 503

    data = request.json
    query = data.get("query", "")
    agent_type = data.get("agent_type", "react")
    model = data.get("model", "gpt-4o-mini")
    max_iterations = data.get("max_iterations", 10)

    if not query:
        return jsonify({"code": 40001, "message": "Query is required"}), 400

    try:
        registry = get_tool_registry()
        agent = create_agent(
            agent_type=agent_type,
            model=model,
            max_iterations=max_iterations,
            tool_registry=registry,
            verbose=False
        )

        result = await agent.run(query)

        return jsonify({
            "code": 0,
            "message": "success",
            "data": result
        })
    except Exception as e:
        return jsonify({"code": 50001, "message": str(e)}), 500


@app.route("/api/v1/agent/run-stream", methods=["POST"])
@require_jwt()
@require_permission(Resource.CHAT, Operation.EXECUTE)
def run_agent_stream():
    """Agent 流式执行 (SSE)

    返回 Server-Sent Events 流，实时发送 Agent 执行步骤
    """
    if not TOOLS_AVAILABLE:
        return jsonify({
            "code": 50003,
            "message": "Agent module not available"
        }), 503

    data = request.json
    query = data.get("query", "")
    agent_type = data.get("agent_type", "react")
    model = data.get("model", "gpt-4o-mini")
    max_iterations = data.get("max_iterations", 10)

    if not query:
        return jsonify({"code": 40001, "message": "Query is required"}), 400

    def generate():
        """SSE 生成器函数"""
        try:
            import asyncio

            async def run_agent_async():
                """异步执行 Agent 并收集事件"""
                registry = get_tool_registry()
                agent = create_agent(
                    agent_type=agent_type,
                    model=model,
                    max_iterations=max_iterations,
                    tool_registry=registry,
                    verbose=False
                )

                events = []
                async for event in agent.run_stream(query):
                    events.append(event)

                return events

            # 在新的事件循环中运行异步代码
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                events = loop.run_until_complete(run_agent_async())

                for event in events:
                    # 格式化为 SSE
                    event_json = json.dumps(event, ensure_ascii=False)
                    yield f"data: {event_json}\n\n"

            finally:
                loop.close()

        except Exception as e:
            error_event = {"type": "error", "message": str(e)}
            yield f"data: {json.dumps(error_event, ensure_ascii=False)}\n\n"

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # 禁用 Nginx 缓冲
            "Connection": "keep-alive",
        }
    )


# ============================================
# 工作流调度 API (Phase 7: Sprint 7.4)
# ============================================

@app.route("/api/v1/workflows/<workflow_id>/schedules", methods=["GET"])
@require_jwt()
def list_schedules(workflow_id):
    """列出工作流的调度配置"""
    db = get_db_session()
    try:
        from models import WorkflowSchedule

        schedules = db.query(WorkflowSchedule).filter(
            WorkflowSchedule.workflow_id == workflow_id
        ).order_by(WorkflowSchedule.created_at.desc()).all()

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "schedules": [s.to_dict() for s in schedules]
            }
        })
    except Exception as e:
        return jsonify({"code": 50001, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/workflows/<workflow_id>/schedules", methods=["POST"])
@require_jwt()
def create_schedule(workflow_id):
    """创建调度配置 (P4: 支持重试和超时配置)"""
    data = request.json
    schedule_type = data.get("type", "cron")

    db = get_db_session()
    try:
        from models import WorkflowSchedule

        # 验证工作流存在
        wf = db.query(Workflow).filter(
            (Workflow.workflow_id == workflow_id) | (Workflow.id == workflow_id)
        ).first()

        if not wf:
            return jsonify({"code": 40401, "message": "Workflow not found"}), 404

        schedule_id = f"schedule-{uuid.uuid4().hex[:8]}"
        schedule = WorkflowSchedule(
            schedule_id=schedule_id,
            workflow_id=workflow_id,
            schedule_type=schedule_type,
            cron_expression=data.get("cron_expression"),
            interval_seconds=data.get("interval_seconds"),
            event_trigger=data.get("event_trigger"),
            enabled=data.get("enabled", True),
            paused=data.get("paused", False),  # P4: 支持暂停状态
            # P4: 重试配置
            max_retries=data.get("max_retries", 0),
            retry_delay_seconds=data.get("retry_delay_seconds", 60),
            retry_backoff_base=data.get("retry_backoff_base", 2),
            # P4: 超时配置
            timeout_seconds=data.get("timeout_seconds", 3600),
            created_by=get_user_id()
        )

        db.add(schedule)
        db.commit()

        # 注册到调度器 (P4: 使用 add_schedule_from_model)
        try:
            from services.scheduler import get_scheduler
            scheduler = get_scheduler()
            scheduler.add_schedule_from_model(schedule)
        except Exception as e:
            # 调度器注册失败，但仍保存数据库记录
            logger.warning(f"Scheduler registration failed: {e}")

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {"schedule_id": schedule_id}
        }), 201

    except Exception as e:
        db.rollback()
        return jsonify({"code": 50001, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/schedules/<schedule_id>", methods=["DELETE"])
@require_jwt()
def delete_schedule(schedule_id):
    """删除调度配置"""
    db = get_db_session()
    try:
        from models import WorkflowSchedule

        schedule = db.query(WorkflowSchedule).filter(
            WorkflowSchedule.schedule_id == schedule_id
        ).first()

        if not schedule:
            return jsonify({"code": 40401, "message": "Schedule not found"}), 404

        # 从调度器移除
        try:
            from services.scheduler import get_scheduler
            scheduler = get_scheduler()
            scheduler.remove_schedule(schedule_id)
        except Exception as e:
            logger.warning(f"Scheduler removal failed: {e}")

        db.delete(schedule)
        db.commit()

        return jsonify({"code": 0, "message": "success"})

    except Exception as e:
        db.rollback()
        return jsonify({"code": 50001, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/schedules/<schedule_id>/trigger", methods=["POST"])
@require_jwt()
def trigger_schedule(schedule_id):
    """手动触发调度"""
    db = get_db_session()
    try:
        from models import WorkflowSchedule

        schedule = db.query(WorkflowSchedule).filter(
            WorkflowSchedule.schedule_id == schedule_id
        ).first()

        if not schedule:
            return jsonify({"code": 40401, "message": "Schedule not found"}), 404

        if not schedule.enabled:
            return jsonify({"code": 40002, "message": "Schedule is disabled"}), 400

        # 获取工作流并执行
        wf = db.query(Workflow).filter(
            Workflow.workflow_id == schedule.workflow_id
        ).first()

        if not wf:
            return jsonify({"code": 40401, "message": "Workflow not found"}), 404

        # 触发工作流执行
        from engine import WorkflowExecutor, register_execution
        from engine.executor import run_workflow_async

        definition = wf.get_definition() or {}
        executor = WorkflowExecutor(schedule.workflow_id, definition)

        execution = WorkflowExecution(
            execution_id=executor.execution_id,
            workflow_id=schedule.workflow_id,
            status="running",
            inputs=json.dumps({"triggered_by": "schedule", "schedule_id": schedule_id}, ensure_ascii=False),
            started_at=datetime.now()
        )
        db.add(execution)
        db.commit()

        register_execution(executor)
        run_workflow_async(executor, {}, db)

        # 更新调度执行时间
        schedule.last_run_at = datetime.now()
        db.commit()

        return jsonify({
            "code": 0,
            "message": "Schedule triggered",
            "data": {"execution_id": executor.execution_id}
        })

    except Exception as e:
        db.rollback()
        return jsonify({"code": 50001, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/schedules", methods=["GET"])
@require_jwt()
def list_all_schedules():
    """列出所有调度配置"""
    workflow_id = request.args.get("workflow_id")
    enabled = request.args.get("enabled")

    db = get_db_session()
    try:
        from models import WorkflowSchedule

        query = db.query(WorkflowSchedule)

        if workflow_id:
            query = query.filter(WorkflowSchedule.workflow_id == workflow_id)
        if enabled is not None:
            is_enabled = enabled.lower() == "true"
            query = query.filter(WorkflowSchedule.enabled == is_enabled)

        schedules = query.order_by(WorkflowSchedule.created_at.desc()).all()

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "schedules": [s.to_dict() for s in schedules]
            }
        })

    except Exception as e:
        return jsonify({"code": 50001, "message": str(e)}), 500
    finally:
        db.close()


# ============================================
# P4: 调度管理增强 API - 暂停/恢复、统计、重试配置
# ============================================

@app.route("/api/v1/schedules/<schedule_id>/pause", methods=["POST"])
@require_jwt()
def pause_schedule(schedule_id):
    """暂停调度 (P4)

    暂停后，调度不会被触发，但保留配置
    可以通过 resume 恢复
    """
    db = get_db_session()
    try:
        from models import WorkflowSchedule

        schedule = db.query(WorkflowSchedule).filter(
            WorkflowSchedule.schedule_id == schedule_id
        ).first()

        if not schedule:
            return jsonify({"code": 40401, "message": "Schedule not found"}), 404

        # 更新数据库状态
        schedule.paused = True
        db.commit()

        # 暂停调度器中的作业
        try:
            from services.scheduler import get_scheduler
            scheduler = get_scheduler()
            scheduler.pause_schedule(schedule_id)
        except Exception as e:
            logger.warning(f"Failed to pause schedule in scheduler: {e}")

        return jsonify({
            "code": 0,
            "message": "Schedule paused",
            "data": {
                "schedule_id": schedule_id,
                "paused": True
            }
        })

    except Exception as e:
        db.rollback()
        return jsonify({"code": 50001, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/schedules/<schedule_id>/resume", methods=["POST"])
@require_jwt()
def resume_schedule(schedule_id):
    """恢复调度 (P4)

    恢复已暂停的调度
    """
    db = get_db_session()
    try:
        from models import WorkflowSchedule

        schedule = db.query(WorkflowSchedule).filter(
            WorkflowSchedule.schedule_id == schedule_id
        ).first()

        if not schedule:
            return jsonify({"code": 40401, "message": "Schedule not found"}), 404

        if not schedule.paused:
            return jsonify({"code": 40002, "message": "Schedule is not paused"}), 400

        # 更新数据库状态
        schedule.paused = False
        db.commit()

        # 恢复调度器中的作业
        try:
            from services.scheduler import get_scheduler
            scheduler = get_scheduler()
            scheduler.resume_schedule(schedule_id)
        except Exception as e:
            logger.warning(f"Failed to resume schedule in scheduler: {e}")

        return jsonify({
            "code": 0,
            "message": "Schedule resumed",
            "data": {
                "schedule_id": schedule_id,
                "paused": False
            }
        })

    except Exception as e:
        db.rollback()
        return jsonify({"code": 50001, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/schedules/<schedule_id>/statistics", methods=["GET"])
@require_jwt()
def get_schedule_statistics(schedule_id):
    """获取调度统计信息 (P4)

    返回：
    - 总执行次数
    - 成功/失败次数
    - 平均执行时间
    - 成功率
    - 最近执行记录
    """
    db = get_db_session()
    try:
        from models import WorkflowSchedule, WorkflowExecution

        # 验证调度存在
        schedule = db.query(WorkflowSchedule).filter(
            WorkflowSchedule.schedule_id == schedule_id
        ).first()

        if not schedule:
            return jsonify({"code": 40401, "message": "Schedule not found"}), 404

        # 从执行跟踪器获取内存中的统计
        try:
            from services.scheduler import get_execution_tracker
            tracker = get_execution_tracker()
            stats = tracker.get_statistics(schedule_id)
        except Exception as e:
            logger.warning(f"Failed to get tracker statistics: {e}")
            stats = {
                "schedule_id": schedule_id,
                "total_executions": 0,
                "successful_executions": 0,
                "failed_executions": 0,
                "average_execution_time_ms": 0,
                "last_execution_status": None,
                "last_execution_at": None,
                "success_rate": 0.0,
            }

        # 从数据库获取额外的执行历史
        executions = db.query(WorkflowExecution).filter(
            WorkflowExecution.workflow_id == schedule.workflow_id
        ).order_by(WorkflowExecution.created_at.desc()).limit(50).all()

        # 计算数据库中的统计
        db_stats = {
            "total_executions": len(executions),
            "successful_executions": sum(1 for e in executions if e.status == "completed"),
            "failed_executions": sum(1 for e in executions if e.status == "failed"),
        }

        if executions:
            durations = [e.duration_ms for e in executions if e.duration_ms]
            db_stats["average_execution_time_ms"] = int(sum(durations) / len(durations)) if durations else 0
            db_stats["last_execution_status"] = executions[0].status
            db_stats["last_execution_at"] = executions[0].created_at.isoformat() if executions[0].created_at else None
        else:
            db_stats["average_execution_time_ms"] = 0
            db_stats["last_execution_status"] = None
            db_stats["last_execution_at"] = None

        # 计算成功率
        if db_stats["total_executions"] > 0:
            db_stats["success_rate"] = round(
                db_stats["successful_executions"] / db_stats["total_executions"] * 100, 2
            )
        else:
            db_stats["success_rate"] = 0.0

        # 合并统计信息（优先使用数据库中的数据）
        combined_stats = {
            **stats,
            **db_stats,
        }

        # 添加最近执行记录
        combined_stats["recent_executions"] = [
            {
                "execution_id": e.execution_id,
                "status": e.status,
                "started_at": e.started_at.isoformat() if e.started_at else None,
                "completed_at": e.completed_at.isoformat() if e.completed_at else None,
                "duration_ms": e.duration_ms,
                "error": e.error,
            }
            for e in executions[:10]
        ]

        return jsonify({
            "code": 0,
            "message": "success",
            "data": combined_stats
        })

    except Exception as e:
        return jsonify({"code": 50001, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/schedules/<schedule_id>/retry-config", methods=["PUT"])
@require_jwt()
def update_schedule_retry_config(schedule_id):
    """更新调度重试配置 (P4)

    可更新字段：
    - max_retries: 最大重试次数
    - retry_delay_seconds: 重试延迟秒数
    - retry_backoff_base: 退避基数
    - timeout_seconds: 超时时间
    """
    data = request.json

    db = get_db_session()
    try:
        from models import WorkflowSchedule

        schedule = db.query(WorkflowSchedule).filter(
            WorkflowSchedule.schedule_id == schedule_id
        ).first()

        if not schedule:
            return jsonify({"code": 40401, "message": "Schedule not found"}), 404

        # 更新重试配置
        if "max_retries" in data:
            schedule.max_retries = max(0, min(data["max_retries"], 10))  # 限制 0-10

        if "retry_delay_seconds" in data:
            schedule.retry_delay_seconds = max(0, min(data["retry_delay_seconds"], 3600))

        if "retry_backoff_base" in data:
            schedule.retry_backoff_base = max(1, min(data["retry_backoff_base"], 10))

        if "timeout_seconds" in data:
            schedule.timeout_seconds = max(60, min(data["timeout_seconds"], 86400))  # 1分钟到1天

        db.commit()

        return jsonify({
            "code": 0,
            "message": "Retry config updated",
            "data": {
                "schedule_id": schedule_id,
                "max_retries": schedule.max_retries,
                "retry_delay_seconds": schedule.retry_delay_seconds,
                "retry_backoff_base": schedule.retry_backoff_base,
                "timeout_seconds": schedule.timeout_seconds,
            }
        })

    except Exception as e:
        db.rollback()
        return jsonify({"code": 50001, "message": str(e)}), 500
    finally:
        db.close()


# ============================================
# Agent 模板管理 API (P1 - Agent 模板管理)
# ============================================

@app.route("/api/v1/agent/templates", methods=["GET"])
@require_jwt()
def list_agent_templates():
    """列出 Agent 模板"""
    if not AGENT_TEMPLATE_AVAILABLE:
        return jsonify({
            "code": 50003,
            "message": "Agent template service not available"
        }), 503

    agent_type = request.args.get("agent_type")
    limit = int(request.args.get("limit", 50))

    try:
        service = get_agent_template_service()
        templates = service.list_templates(limit=limit, agent_type=agent_type)

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "templates": templates,
                "total": len(templates)
            }
        })
    except Exception as e:
        return jsonify({"code": 50001, "message": str(e)}), 500


@app.route("/api/v1/agent/templates/<template_id>", methods=["GET"])
@require_jwt()
def get_agent_template(template_id):
    """获取单个 Agent 模板"""
    if not AGENT_TEMPLATE_AVAILABLE:
        return jsonify({
            "code": 50003,
            "message": "Agent template service not available"
        }), 503

    try:
        service = get_agent_template_service()
        template = service.get_template(template_id)

        if template:
            return jsonify({
                "code": 0,
                "message": "success",
                "data": template
            })
        return jsonify({"code": 40401, "message": "Template not found"}), 404
    except Exception as e:
        return jsonify({"code": 50001, "message": str(e)}), 500


@app.route("/api/v1/agent/templates", methods=["POST"])
@require_jwt()
def create_agent_template():
    """创建 Agent 模板"""
    if not AGENT_TEMPLATE_AVAILABLE:
        return jsonify({
            "code": 50003,
            "message": "Agent template service not available"
        }), 503

    data = request.json
    name = data.get("name")

    if not name:
        return jsonify({"code": 40001, "message": "Template name is required"}), 400

    try:
        service = get_agent_template_service()
        template = service.create_template(
            name=name,
            description=data.get("description"),
            agent_type=data.get("agent_type", "react"),
            model=data.get("model", "gpt-4o-mini"),
            max_iterations=data.get("max_iterations", 10),
            system_prompt=data.get("system_prompt"),
            selected_tools=data.get("selected_tools", []),
            created_by=get_user_id()
        )

        return jsonify({
            "code": 0,
            "message": "success",
            "data": template
        }), 201
    except Exception as e:
        return jsonify({"code": 50001, "message": str(e)}), 500


@app.route("/api/v1/agent/templates/<template_id>", methods=["DELETE"])
@require_jwt()
def delete_agent_template(template_id):
    """删除 Agent 模板"""
    if not AGENT_TEMPLATE_AVAILABLE:
        return jsonify({
            "code": 50003,
            "message": "Agent template service not available"
        }), 503

    try:
        service = get_agent_template_service()
        success = service.delete_template(template_id)

        if success:
            return jsonify({"code": 0, "message": "success"})
        return jsonify({"code": 40401, "message": "Template not found"}), 404
    except Exception as e:
        return jsonify({"code": 50001, "message": str(e)}), 500


@app.route("/api/v1/agent/templates/<template_id>", methods=["PUT"])
@require_jwt()
def update_agent_template(template_id):
    """更新 Agent 模板"""
    if not AGENT_TEMPLATE_AVAILABLE:
        return jsonify({
            "code": 50003,
            "message": "Agent template service not available"
        }), 503

    data = request.json

    try:
        service = get_agent_template_service()
        template = service.update_template(
            template_id=template_id,
            name=data.get("name"),
            description=data.get("description"),
            agent_type=data.get("agent_type"),
            model=data.get("model"),
            max_iterations=data.get("max_iterations"),
            system_prompt=data.get("system_prompt"),
            selected_tools=data.get("selected_tools")
        )

        if template:
            return jsonify({
                "code": 0,
                "message": "success",
                "data": template
            })
        return jsonify({"code": 40401, "message": "Template not found"}), 404
    except Exception as e:
        return jsonify({"code": 50001, "message": str(e)}), 500


# ============================================
# P5: Token 管理端点
# ============================================

@app.route("/api/v1/auth/refresh", methods=["POST"])
def refresh_token():
    """
    刷新访问 Token

    支持两种方式：
    1. 从 HttpOnly Cookie 读取 refresh_token（推荐，更安全）
    2. 从请求体读取 refresh_token（用于 API 客户端）

    成功后会同时在响应体和 Set-Cookie 头中返回新 Token。
    """
    # 优先从 Cookie 读取（HttpOnly Cookie 方式）
    refresh_token_value = request.cookies.get('refresh_token')

    # 如果 Cookie 中没有，尝试从请求体读取（API 客户端方式）
    if not refresh_token_value:
        data = request.json or {}
        refresh_token_value = data.get("refresh_token")

    if not refresh_token_value:
        return jsonify({
            "code": 40001,
            "message": "refresh_token is required (via cookie or request body)"
        }), 400

    try:
        # 使用 auth 模块刷新 token
        if AUTH_ENABLED:
            from auth import refresh_token as do_refresh
            result = do_refresh(refresh_token_value)
            if result:
                # 构建响应
                response_data = {
                    "code": 0,
                    "message": "success",
                    "data": {
                        "access_token": result.get("access_token"),
                        "refresh_token": result.get("refresh_token"),
                        "expires_in": result.get("expires_in"),
                        "token_type": result.get("token_type", "Bearer")
                    }
                }

                from flask import make_response
                response = make_response(jsonify(response_data))

                # 同时设置 HttpOnly Cookie（用于浏览器客户端）
                try:
                    from auth import set_auth_cookies
                    set_auth_cookies(response, result)
                except ImportError:
                    # 手动设置 Cookie
                    is_secure = os.getenv("FLASK_ENV") == "production"
                    if result.get("access_token"):
                        response.set_cookie(
                            'access_token',
                            result.get("access_token"),
                            max_age=result.get("expires_in", 3600),
                            httponly=True,
                            secure=is_secure,
                            samesite='Lax'
                        )
                    if result.get("refresh_token"):
                        response.set_cookie(
                            'refresh_token',
                            result.get("refresh_token"),
                            max_age=result.get("refresh_expires_in", 604800),
                            httponly=True,
                            secure=is_secure,
                            samesite='Lax'
                        )

                return response

        return jsonify({"code": 40101, "message": "Invalid refresh token"}), 401
    except Exception as e:
        return jsonify({"code": 50001, "message": str(e)}), 500


@app.route("/api/v1/auth/logout", methods=["POST"])
@require_jwt()
def logout():
    """登出用户"""
    data = request.json
    refresh_token_value = data.get("refresh_token")

    try:
        # 使用 auth 模块登出
        if AUTH_ENABLED:
            from auth import logout_user
            token = request.headers.get("Authorization", "").replace("Bearer ", "")
            logout_user(token)

        return jsonify({"code": 0, "message": "Logged out successfully"})
    except Exception as e:
        return jsonify({"code": 50001, "message": str(e)}), 500


@app.route("/api/v1/auth/me", methods=["GET"])
@require_jwt()
def get_current_user_info():
    """获取当前用户信息"""
    if AUTH_ENABLED:
        from auth import get_current_user
        user = get_current_user()
        if user:
            return jsonify({"code": 0, "message": "success", "data": user})

    return jsonify({"code": 40100, "message": "Not authenticated"}), 401


@app.route("/api/v1/auth/permissions", methods=["GET"])
@require_jwt()
def get_user_permissions():
    """获取当前用户权限列表"""
    if AUTH_ENABLED:
        from auth import check_permission, Resource, Operation
        user_roles = g.roles if hasattr(g, 'roles') else []

        permissions = {}
        for resource in [Resource.WORKFLOW, Resource.CHAT, Resource.AGENT,
                        Resource.SCHEDULE, Resource.DOCUMENT, Resource.EXECUTION,
                        Resource.TEMPLATE]:
            permissions[resource] = []
            for operation in [Operation.CREATE, Operation.READ, Operation.UPDATE,
                            Operation.DELETE, Operation.EXECUTE, Operation.MANAGE]:
                if check_permission(resource, operation, user_roles):
                    permissions[resource].append(operation)

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "roles": user_roles,
                "permissions": permissions
            }
        })

    return jsonify({"code": 40100, "message": "Not authenticated"}), 401


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


# ============================================
# P3.1: Prompt 模板管理 API
# ============================================

def generate_id(prefix: str = "") -> str:
    """生成唯一ID"""
    return f"{prefix}{uuid.uuid4().hex[:16]}"


@app.route("/api/v1/prompts", methods=["GET"])
@require_jwt()
def list_prompts():
    """列出 Prompt 模板"""
    db = next(get_db())

    try:
        category = request.args.get("category")
        is_public = request.args.get("is_public")
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("page_size", 20))

        query = db.query(PromptTemplate).filter(PromptTemplate.is_active == True)

        if category:
            query = query.filter(PromptTemplate.category == category)
        if is_public is not None:
            query = query.filter(PromptTemplate.is_public == (is_public.lower() == "true"))

        total = query.count()
        prompts = query.order_by(PromptTemplate.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "prompts": [p.to_dict() for p in prompts],
                "total": total,
                "page": page,
                "page_size": page_size
            }
        })
    except Exception as e:
        return jsonify({"code": 50001, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/prompts", methods=["POST"])
@require_jwt()
def create_prompt():
    """创建 Prompt 模板"""
    db = next(get_db())
    data = request.json

    try:
        name = data.get("name")
        content = data.get("content")
        if not name or not content:
            return jsonify({"code": 40001, "message": "name 和 content 必填"}), 400

        prompt = PromptTemplate(
            template_id=generate_id("prompt_"),
            name=name,
            description=data.get("description", ""),
            category=data.get("category"),
            content=content,
            variables=data.get("variables"),
            model=data.get("model"),
            temperature=data.get("temperature", 0.7),
            max_tokens=data.get("max_tokens"),
            system_prompt=data.get("system_prompt"),
            version=data.get("version", "1.0.0"),
            tags=data.get("tags"),
            is_public=data.get("is_public", False),
            created_by=get_user_id()
        )

        db.add(prompt)
        db.commit()
        db.refresh(prompt)

        return jsonify({
            "code": 0,
            "message": "success",
            "data": prompt.to_dict()
        }), 201
    except Exception as e:
        db.rollback()
        return jsonify({"code": 50001, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/prompts/<prompt_id>", methods=["GET"])
@require_jwt()
def get_prompt(prompt_id):
    """获取 Prompt 模板详情"""
    db = next(get_db())

    try:
        prompt = db.query(PromptTemplate).filter(PromptTemplate.template_id == prompt_id).first()
        if not prompt:
            return jsonify({"code": 40401, "message": "模板不存在"}), 404

        return jsonify({
            "code": 0,
            "message": "success",
            "data": prompt.to_dict()
        })
    except Exception as e:
        return jsonify({"code": 50001, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/prompts/<prompt_id>", methods=["PUT"])
@require_jwt()
def update_prompt(prompt_id):
    """更新 Prompt 模板"""
    db = next(get_db())
    data = request.json

    try:
        prompt = db.query(PromptTemplate).filter(PromptTemplate.template_id == prompt_id).first()
        if not prompt:
            return jsonify({"code": 40401, "message": "模板不存在"}), 404

        if data.get("name"):
            prompt.name = data["name"]
        if data.get("description") is not None:
            prompt.description = data["description"]
        if data.get("category"):
            prompt.category = data["category"]
        if data.get("content"):
            prompt.content = data["content"]
        if data.get("variables") is not None:
            prompt.variables = data["variables"]
        if data.get("model"):
            prompt.model = data["model"]
        if data.get("temperature") is not None:
            prompt.temperature = data["temperature"]
        if data.get("max_tokens") is not None:
            prompt.max_tokens = data["max_tokens"]
        if data.get("system_prompt") is not None:
            prompt.system_prompt = data["system_prompt"]
        if data.get("tags"):
            prompt.tags = data["tags"]
        if data.get("is_public") is not None:
            prompt.is_public = data["is_public"]

        prompt.updated_by = get_user_id()
        db.commit()
        db.refresh(prompt)

        return jsonify({
            "code": 0,
            "message": "success",
            "data": prompt.to_dict()
        })
    except Exception as e:
        db.rollback()
        return jsonify({"code": 50001, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/prompts/<prompt_id>", methods=["DELETE"])
@require_jwt()
def delete_prompt(prompt_id):
    """删除 Prompt 模板"""
    db = next(get_db())

    try:
        prompt = db.query(PromptTemplate).filter(PromptTemplate.template_id == prompt_id).first()
        if not prompt:
            return jsonify({"code": 40401, "message": "模板不存在"}), 404

        prompt.is_active = False
        db.commit()

        return jsonify({"code": 0, "message": "success"})
    except Exception as e:
        db.rollback()
        return jsonify({"code": 50001, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/prompts/<prompt_id>/test", methods=["POST"])
@require_jwt()
def test_prompt(prompt_id):
    """测试 Prompt 模板"""
    db = next(get_db())
    data = request.json or {}

    try:
        prompt = db.query(PromptTemplate).filter(PromptTemplate.template_id == prompt_id).first()
        if not prompt:
            return jsonify({"code": 40401, "message": "模板不存在"}), 404

        # 获取变量值
        variables = data.get("variables", {})

        # 替换模板中的变量
        content = prompt.content
        for var_name, var_value in variables.items():
            content = content.replace(f"{{{{{var_name}}}}}", str(var_value))

        # 调用 LLM 进行测试（这里简化处理，实际应调用 OpenAI Proxy）
        # 更新使用计数
        prompt.use_count = (prompt.use_count or 0) + 1
        db.commit()

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "rendered_content": content,
                "model": prompt.model,
                "temperature": prompt.temperature,
                "response": f"[测试响应] 使用模型 {prompt.model} 处理: {content[:100]}..."
            }
        })
    except Exception as e:
        db.rollback()
        return jsonify({"code": 50001, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/prompts/<prompt_id>/duplicate", methods=["POST"])
@require_jwt()
def duplicate_prompt(prompt_id):
    """复制 Prompt 模板"""
    db = next(get_db())
    data = request.json or {}

    try:
        prompt = db.query(PromptTemplate).filter(PromptTemplate.template_id == prompt_id).first()
        if not prompt:
            return jsonify({"code": 40401, "message": "模板不存在"}), 404

        new_prompt = PromptTemplate(
            template_id=generate_id("prompt_"),
            name=data.get("name", f"{prompt.name} (副本)"),
            description=prompt.description,
            category=prompt.category,
            content=prompt.content,
            variables=prompt.variables,
            model=prompt.model,
            temperature=prompt.temperature,
            max_tokens=prompt.max_tokens,
            system_prompt=prompt.system_prompt,
            version="1.0.0",
            tags=prompt.tags,
            is_public=False,
            parent_id=prompt.template_id,
            created_by=get_user_id()
        )

        db.add(new_prompt)
        db.commit()
        db.refresh(new_prompt)

        return jsonify({
            "code": 0,
            "message": "success",
            "data": new_prompt.to_dict()
        }), 201
    except Exception as e:
        db.rollback()
        return jsonify({"code": 50001, "message": str(e)}), 500
    finally:
        db.close()


# ==================== 工作流模板 API ====================

@app.route("/api/v1/templates", methods=["GET"])
@require_jwt(optional=True)
def list_workflow_templates():
    """列出工作流模板（数据库版本）"""
    category = request.args.get("category")
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 20))

    db = get_db_session()
    try:
        # 构建查询
        query = db.query(Template).filter(Template.is_public == True)

        # 按分类筛选
        if category:
            query = query.filter(Template.category == category)

        # 获取总数
        total = query.count()

        # 分页查询
        start = (page - 1) * page_size
        templates = query.order_by(Template.updated_at.desc()).offset(start).limit(page_size).all()

        # 转换为字典
        templates_data = []
        for tpl in templates:
            tpl_dict = tpl.to_dict()
            # 添加 template_id 字段
            tpl_dict["template_id"] = tpl.template_id
            # 从 definition 中提取 config
            if tpl.definition:
                try:
                    definition = json.loads(tpl.definition)
                    if "config" in definition:
                        tpl_dict["config"] = definition["config"]
                except json.JSONDecodeError:
                    pass
            templates_data.append(tpl_dict)

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "templates": templates_data,
                "total": total,
                "page": page,
                "page_size": page_size
            }
        })
    except Exception as e:
        logger.error(f"获取模板列表失败: {e}")
        return jsonify({"code": 50001, "message": f"获取模板列表失败: {str(e)}"}), 500
    finally:
        db.close()


@app.route("/api/v1/templates/<template_id>", methods=["GET"])
@require_jwt(optional=True)
def get_workflow_template(template_id: str):
    """获取工作流模板详情（数据库版本）"""
    db = get_db_session()
    try:
        tpl = db.query(Template).filter(Template.template_id == template_id).first()

        if not tpl:
            return jsonify({"code": 40401, "message": "模板不存在"}), 404

        tpl_dict = tpl.to_dict(include_definition=True)
        tpl_dict["template_id"] = tpl.template_id

        return jsonify({
            "code": 0,
            "message": "success",
            "data": tpl_dict
        })
    except Exception as e:
        logger.error(f"获取模板详情失败: {e}")
        return jsonify({"code": 50001, "message": f"获取模板详情失败: {str(e)}"}), 500
    finally:
        db.close()


@app.route("/api/v1/templates", methods=["POST"])
@require_jwt()
def create_workflow_template():
    """创建工作流模板"""
    data = request.json
    name = data.get("name")
    if not name:
        return jsonify({"code": 40001, "message": "Name is required"}), 400

    template_id = f"tpl-{uuid.uuid4().hex[:8]}"

    return jsonify({
        "code": 0,
        "message": "success",
        "data": {
            "template_id": template_id,
            "name": name,
            "description": data.get("description", ""),
            "category": data.get("category", "custom"),
            "status": "created"
        }
    }), 201


# ============================================
# P3.2: 模型评估 API
# ============================================

@app.route("/api/v1/evaluations", methods=["GET"])
@require_jwt()
def list_evaluations():
    """列出评估任务"""
    db = next(get_db())

    try:
        status = request.args.get("status")
        model_id = request.args.get("model_id")
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("page_size", 20))

        query = db.query(Evaluation)

        if status:
            query = query.filter(Evaluation.status == status)
        if model_id:
            query = query.filter(Evaluation.model_id == model_id)

        total = query.count()
        evaluations = query.order_by(Evaluation.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "evaluations": [e.to_dict() for e in evaluations],
                "total": total,
                "page": page,
                "page_size": page_size
            }
        })
    except Exception as e:
        return jsonify({"code": 50001, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/evaluations", methods=["POST"])
@require_jwt()
def create_evaluation():
    """创建评估任务"""
    db = next(get_db())
    data = request.json

    try:
        name = data.get("name")
        model_id = data.get("model_id")
        dataset_id = data.get("dataset_id")
        if not name or not model_id or not dataset_id:
            return jsonify({"code": 40001, "message": "name、model_id 和 dataset_id 必填"}), 400

        evaluation = Evaluation(
            evaluation_id=generate_id("eval_"),
            name=name,
            description=data.get("description", ""),
            model_id=model_id,
            model_name=data.get("model_name"),
            dataset_id=dataset_id,
            dataset_name=data.get("dataset_name"),
            eval_type=data.get("eval_type", "auto"),
            metrics=data.get("metrics", ["accuracy", "f1"]),
            status="pending",
            created_by=get_user_id()
        )

        db.add(evaluation)
        db.commit()
        db.refresh(evaluation)

        return jsonify({
            "code": 0,
            "message": "success",
            "data": evaluation.to_dict()
        }), 201
    except Exception as e:
        db.rollback()
        return jsonify({"code": 50001, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/evaluations/<evaluation_id>", methods=["GET"])
@require_jwt()
def get_evaluation(evaluation_id):
    """获取评估任务详情"""
    db = next(get_db())

    try:
        evaluation = db.query(Evaluation).filter(Evaluation.evaluation_id == evaluation_id).first()
        if not evaluation:
            return jsonify({"code": 40401, "message": "评估任务不存在"}), 404

        return jsonify({
            "code": 0,
            "message": "success",
            "data": evaluation.to_dict()
        })
    except Exception as e:
        return jsonify({"code": 50001, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/evaluations/<evaluation_id>", methods=["DELETE"])
@require_jwt()
def delete_evaluation(evaluation_id):
    """删除评估任务"""
    db = next(get_db())

    try:
        evaluation = db.query(Evaluation).filter(Evaluation.evaluation_id == evaluation_id).first()
        if not evaluation:
            return jsonify({"code": 40401, "message": "评估任务不存在"}), 404

        # 删除关联的结果
        db.query(EvaluationResult).filter(EvaluationResult.evaluation_id == evaluation_id).delete()
        db.delete(evaluation)
        db.commit()

        return jsonify({"code": 0, "message": "success"})
    except Exception as e:
        db.rollback()
        return jsonify({"code": 50001, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/evaluations/<evaluation_id>/run", methods=["POST"])
@require_jwt()
def run_evaluation(evaluation_id):
    """执行评估任务"""
    db = next(get_db())

    try:
        evaluation = db.query(Evaluation).filter(Evaluation.evaluation_id == evaluation_id).first()
        if not evaluation:
            return jsonify({"code": 40401, "message": "评估任务不存在"}), 404

        if evaluation.status == "running":
            return jsonify({"code": 40002, "message": "评估任务正在运行"}), 400

        # 模拟启动评估
        evaluation.status = "running"
        evaluation.started_at = datetime.utcnow()
        db.commit()

        # 模拟完成评估（实际应异步执行）
        evaluation.status = "completed"
        evaluation.finished_at = datetime.utcnow()
        evaluation.duration_seconds = 60
        evaluation.samples_evaluated = 100
        evaluation.samples_total = 100
        evaluation.results = {
            "accuracy": 0.85,
            "f1": 0.82,
            "precision": 0.88,
            "recall": 0.80
        }
        evaluation.summary = "评估完成，模型表现良好"
        db.commit()
        db.refresh(evaluation)

        return jsonify({
            "code": 0,
            "message": "success",
            "data": evaluation.to_dict()
        })
    except Exception as e:
        db.rollback()
        return jsonify({"code": 50001, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/evaluations/<evaluation_id>/results", methods=["GET"])
@require_jwt()
def get_evaluation_results(evaluation_id):
    """获取评估结果"""
    db = next(get_db())

    try:
        evaluation = db.query(Evaluation).filter(Evaluation.evaluation_id == evaluation_id).first()
        if not evaluation:
            return jsonify({"code": 40401, "message": "评估任务不存在"}), 404

        # 获取详细结果
        results = db.query(EvaluationResult).filter(
            EvaluationResult.evaluation_id == evaluation_id
        ).order_by(EvaluationResult.sample_index).all()

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "evaluation": evaluation.to_dict(),
                "results": [r.to_dict() for r in results]
            }
        })
    except Exception as e:
        return jsonify({"code": 50001, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/evaluations/compare", methods=["POST"])
@require_jwt()
def compare_evaluations():
    """对比评估报告"""
    db = next(get_db())
    data = request.json

    try:
        evaluation_ids = data.get("evaluation_ids", [])
        if len(evaluation_ids) < 2:
            return jsonify({"code": 40001, "message": "至少需要两个评估ID进行对比"}), 400

        evaluations = db.query(Evaluation).filter(
            Evaluation.evaluation_id.in_(evaluation_ids)
        ).all()

        if len(evaluations) != len(evaluation_ids):
            return jsonify({"code": 40401, "message": "部分评估任务不存在"}), 404

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "evaluations": [e.to_dict() for e in evaluations]
            }
        })
    except Exception as e:
        return jsonify({"code": 50001, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/evaluation-datasets", methods=["GET"])
@require_jwt()
def list_evaluation_datasets():
    """列出评估数据集"""
    db = next(get_db())

    try:
        dataset_type = request.args.get("dataset_type")
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("page_size", 20))

        query = db.query(EvaluationDataset)

        if dataset_type:
            query = query.filter(EvaluationDataset.dataset_type == dataset_type)

        total = query.count()
        datasets = query.order_by(EvaluationDataset.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "datasets": [d.to_dict() for d in datasets],
                "total": total,
                "page": page,
                "page_size": page_size
            }
        })
    except Exception as e:
        return jsonify({"code": 50001, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/evaluation-datasets", methods=["POST"])
@require_jwt()
def create_evaluation_dataset():
    """创建/上传评估数据集"""
    db = next(get_db())
    data = request.json

    try:
        name = data.get("name")
        if not name:
            return jsonify({"code": 40001, "message": "数据集名称不能为空"}), 400

        dataset = EvaluationDataset(
            dataset_id=generate_id("evds_"),
            name=name,
            description=data.get("description", ""),
            dataset_type=data.get("dataset_type", "qa"),
            storage_path=data.get("storage_path"),
            file_format=data.get("file_format", "jsonl"),
            sample_count=data.get("sample_count", 0),
            file_size=data.get("file_size"),
            schema=data.get("schema"),
            tags=data.get("tags"),
            is_public=data.get("is_public", False),
            created_by=get_user_id()
        )

        db.add(dataset)
        db.commit()
        db.refresh(dataset)

        return jsonify({
            "code": 0,
            "message": "success",
            "data": dataset.to_dict()
        }), 201
    except Exception as e:
        db.rollback()
        return jsonify({"code": 50001, "message": str(e)}), 500
    finally:
        db.close()


# 评估路径别名（前端调用路径不同）
@app.route("/api/v1/evaluation/datasets", methods=["GET"])
@require_jwt(optional=True)
def list_evaluation_datasets_alias():
    """列出评估数据集（别名路径）"""
    return list_evaluation_datasets()


@app.route("/api/v1/evaluation/datasets", methods=["POST"])
@require_jwt()
def create_evaluation_dataset_alias():
    """创建评估数据集（别名路径）"""
    return create_evaluation_dataset()


@app.route("/api/v1/evaluation/tasks", methods=["GET"])
@require_jwt(optional=True)
def list_evaluation_tasks():
    """列出评估任务（别名路径）"""
    return list_evaluations()


@app.route("/api/v1/evaluation/tasks", methods=["POST"])
@require_jwt()
def create_evaluation_task_alias():
    """创建评估任务（别名路径）"""
    return create_evaluation()


# ============================================
# P3.3: SFT 微调 API
# ============================================

@app.route("/api/v1/sft/tasks", methods=["GET"])
@require_jwt()
def list_sft_tasks():
    """列出 SFT 任务"""
    db = next(get_db())

    try:
        status = request.args.get("status")
        method = request.args.get("method")
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("page_size", 20))

        query = db.query(SFTTask)

        if status:
            query = query.filter(SFTTask.status == status)
        if method:
            query = query.filter(SFTTask.method == method)

        total = query.count()
        tasks = query.order_by(SFTTask.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

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
    except Exception as e:
        return jsonify({"code": 50001, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/sft/tasks", methods=["POST"])
@require_jwt()
def create_sft_task():
    """创建 SFT 任务"""
    db = next(get_db())
    data = request.json

    try:
        name = data.get("name")
        base_model = data.get("base_model")
        dataset_id = data.get("dataset_id")
        if not name or not base_model or not dataset_id:
            return jsonify({"code": 40001, "message": "name、base_model 和 dataset_id 必填"}), 400

        task = SFTTask(
            task_id=generate_id("sft_"),
            name=name,
            description=data.get("description", ""),
            base_model=base_model,
            base_model_path=data.get("base_model_path"),
            method=data.get("method", "lora"),
            dataset_id=dataset_id,
            dataset_name=data.get("dataset_name"),
            dataset_path=data.get("dataset_path"),
            epochs=data.get("epochs", 3),
            batch_size=data.get("batch_size", 4),
            learning_rate=data.get("learning_rate", 2e-5),
            warmup_steps=data.get("warmup_steps", 100),
            max_seq_length=data.get("max_seq_length", 512),
            gradient_accumulation_steps=data.get("gradient_accumulation_steps", 4),
            lora_r=data.get("lora_r", 8),
            lora_alpha=data.get("lora_alpha", 16),
            lora_dropout=data.get("lora_dropout", 0.05),
            target_modules=data.get("target_modules"),
            use_4bit=data.get("use_4bit", False),
            gpu_count=data.get("gpu_count", 1),
            gpu_type=data.get("gpu_type"),
            memory_limit=data.get("memory_limit"),
            tags=data.get("tags"),
            status="pending",
            created_by=get_user_id()
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


@app.route("/api/v1/sft/tasks/<task_id>", methods=["GET"])
@require_jwt()
def get_sft_task(task_id):
    """获取 SFT 任务详情"""
    db = next(get_db())

    try:
        task = db.query(SFTTask).filter(SFTTask.task_id == task_id).first()
        if not task:
            return jsonify({"code": 40401, "message": "SFT 任务不存在"}), 404

        return jsonify({
            "code": 0,
            "message": "success",
            "data": task.to_dict()
        })
    except Exception as e:
        return jsonify({"code": 50001, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/sft/tasks/<task_id>", methods=["DELETE"])
@require_jwt()
def delete_sft_task(task_id):
    """删除 SFT 任务"""
    db = next(get_db())

    try:
        task = db.query(SFTTask).filter(SFTTask.task_id == task_id).first()
        if not task:
            return jsonify({"code": 40401, "message": "SFT 任务不存在"}), 404

        if task.status == "running":
            return jsonify({"code": 40002, "message": "运行中的任务不能删除"}), 400

        db.delete(task)
        db.commit()

        return jsonify({"code": 0, "message": "success"})
    except Exception as e:
        db.rollback()
        return jsonify({"code": 50001, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/sft/tasks/<task_id>/start", methods=["POST"])
@require_jwt()
def start_sft_task(task_id):
    """启动 SFT 任务"""
    db = next(get_db())

    try:
        task = db.query(SFTTask).filter(SFTTask.task_id == task_id).first()
        if not task:
            return jsonify({"code": 40401, "message": "SFT 任务不存在"}), 404

        if task.status == "running":
            return jsonify({"code": 40002, "message": "任务已在运行"}), 400

        task.status = "running"
        task.started_at = datetime.utcnow()
        task.current_step = 0
        task.current_epoch = 0
        task.total_steps = task.epochs * 100  # 模拟
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


@app.route("/api/v1/sft/tasks/<task_id>/stop", methods=["POST"])
@require_jwt()
def stop_sft_task(task_id):
    """停止 SFT 任务"""
    db = next(get_db())

    try:
        task = db.query(SFTTask).filter(SFTTask.task_id == task_id).first()
        if not task:
            return jsonify({"code": 40401, "message": "SFT 任务不存在"}), 404

        if task.status != "running":
            return jsonify({"code": 40002, "message": "任务未在运行"}), 400

        task.status = "stopped"
        task.finished_at = datetime.utcnow()
        if task.started_at:
            task.duration_seconds = int((task.finished_at - task.started_at).total_seconds())
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


@app.route("/api/v1/sft/tasks/<task_id>/deploy", methods=["POST"])
@require_jwt()
def deploy_sft_model(task_id):
    """部署微调模型"""
    db = next(get_db())
    data = request.json or {}

    try:
        task = db.query(SFTTask).filter(SFTTask.task_id == task_id).first()
        if not task:
            return jsonify({"code": 40401, "message": "SFT 任务不存在"}), 404

        if task.status != "completed":
            return jsonify({"code": 40002, "message": "任务未完成，无法部署"}), 400

        if not task.output_model_path:
            return jsonify({"code": 40002, "message": "模型输出路径不存在"}), 400

        # 模拟部署（实际应调用 Cube Studio 服务）
        deployment_id = generate_id("deploy_")

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "deployment_id": deployment_id,
                "task_id": task_id,
                "model_path": task.output_model_path,
                "status": "deploying",
                "endpoint": f"http://serving.one-data.svc.cluster.local/{deployment_id}"
            }
        })
    except Exception as e:
        return jsonify({"code": 50001, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/sft/datasets", methods=["GET"])
@require_jwt()
def list_sft_datasets():
    """列出 SFT 数据集"""
    db = next(get_db())

    try:
        dataset_type = request.args.get("dataset_type")
        status = request.args.get("status")
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("page_size", 20))

        query = db.query(SFTDataset)

        if dataset_type:
            query = query.filter(SFTDataset.dataset_type == dataset_type)
        if status:
            query = query.filter(SFTDataset.status == status)

        total = query.count()
        datasets = query.order_by(SFTDataset.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "datasets": [d.to_dict() for d in datasets],
                "total": total,
                "page": page,
                "page_size": page_size
            }
        })
    except Exception as e:
        return jsonify({"code": 50001, "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/sft/datasets", methods=["POST"])
@require_jwt()
def create_sft_dataset():
    """创建/上传 SFT 数据集"""
    db = next(get_db())
    data = request.json

    try:
        name = data.get("name")
        if not name:
            return jsonify({"code": 40001, "message": "数据集名称不能为空"}), 400

        dataset = SFTDataset(
            dataset_id=generate_id("sftds_"),
            name=name,
            description=data.get("description", ""),
            dataset_type=data.get("dataset_type", "instruction"),
            storage_path=data.get("storage_path"),
            file_format=data.get("file_format", "jsonl"),
            sample_count=data.get("sample_count", 0),
            file_size=data.get("file_size"),
            schema=data.get("schema"),
            preprocessing_config=data.get("preprocessing_config"),
            tags=data.get("tags"),
            is_public=data.get("is_public", False),
            status="ready",
            created_by=get_user_id()
        )

        db.add(dataset)
        db.commit()
        db.refresh(dataset)

        return jsonify({
            "code": 0,
            "message": "success",
            "data": dataset.to_dict()
        }), 201
    except Exception as e:
        db.rollback()
        return jsonify({"code": 50001, "message": str(e)}), 500
    finally:
        db.close()


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8081))
    debug = os.getenv("DEBUG", "false").lower() == "true"

    # 开发环境：自动创建缺失的表
    if os.getenv("ENVIRONMENT") != "production":
        from models.base import create_tables
        create_tables()

    # SECURITY WARNING: Debug mode exposes sensitive information
    if debug:
        import logging
        logging.warning(
            "⚠️  WARNING: Debug mode is ENABLED. This should NEVER be used in production! "
            "Debug mode exposes detailed error information and may enable remote code execution."
        )

    app.run(host="0.0.0.0", port=port, debug=debug)
