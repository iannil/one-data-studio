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

import os
import sys
import json
import asyncio
import requests
import uuid
from datetime import datetime
from flask import Flask, jsonify, request, g, Response

# 添加共享模块路径
sys.path.insert(0, '/app/shared')

# 导入模型
from models import get_db, Workflow, Conversation, Message, WorkflowExecution, ExecutionLog, IndexedDocument

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
    AUTH_ENABLED = False
    # 装饰器空实现（开发模式）
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

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False

# 配置
ALDATA_API_URL = os.getenv("ALDATA_API_URL", "http://alldata-api:8080")
CUBE_API_URL = os.getenv("CUBE_API_URL", "http://vllm-serving:8000")
KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://keycloak.one-data-system.svc.cluster.local:80")
AUTH_MODE = os.getenv("AUTH_MODE", "true").lower() == "true"


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
    """健康检查（无需认证）"""
    health_status = {
        "code": 0,
        "message": "healthy",
        "service": "bisheng-api",
        "version": "2.0.0",
        "auth_enabled": AUTH_ENABLED and AUTH_MODE,
        "connections": {
            "alldata_api": ALDATA_API_URL,
            "cube_api": CUBE_API_URL
        }
    }

    # 测试数据库连接
    try:
        db = get_db_session()
        db.execute("SELECT 1")
        db.close()
        health_status["database"] = "connected"
    except Exception as e:
        health_status["database"] = f"disconnected: {str(e)}"

    return jsonify(health_status)


@app.route("/api/v1/chat", methods=["POST"])
@require_jwt()
@require_permission(Resource.CHAT, Operation.EXECUTE)
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
    """列出工作流"""
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
            print(f"获取表列表失败: {tables_response.status_code}")
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
        print(f"获取元数据失败: {e}")
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
            print(f"警告: 向量删除失败，但继续删除数据库记录: doc_id={doc_id}")

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
        print(f"删除文档失败: {e}")
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
                print(f"删除文档失败 {doc_id}: {e}")
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
    """列出可用工具"""
    if not TOOLS_AVAILABLE:
        return jsonify({
            "code": 50003,
            "message": "Tools module not available"
        }), 503

    try:
        registry = get_tool_registry()
        tools = registry.list_tools()

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "tools": tools,
                "total": len(tools)
            }
        })
    except Exception as e:
        return jsonify({"code": 50001, "message": str(e)}), 500


@app.route("/api/v1/tools/schemas", methods=["GET"])
@require_jwt(optional=True)
def get_tool_schemas():
    """获取工具的 Function Calling 格式 schema"""
    if not TOOLS_AVAILABLE:
        return jsonify({
            "code": 50003,
            "message": "Tools module not available"
        }), 503

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
            print(f"Scheduler registration failed: {e}")

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
            print(f"Scheduler removal failed: {e}")

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
            print(f"Failed to pause schedule in scheduler: {e}")

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
            print(f"Failed to resume schedule in scheduler: {e}")

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
            print(f"Failed to get tracker statistics: {e}")
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
    """刷新访问 Token"""
    data = request.json
    refresh_token_value = data.get("refresh_token")

    if not refresh_token_value:
        return jsonify({"code": 40001, "message": "refresh_token is required"}), 400

    try:
        # 使用 auth 模块刷新 token
        if AUTH_ENABLED:
            from auth import refresh_token as do_refresh
            result = do_refresh(refresh_token_value)
            if result:
                return jsonify({
                    "code": 0,
                    "message": "success",
                    "data": {
                        "access_token": result.get("access_token"),
                        "refresh_token": result.get("refresh_token"),
                        "expires_in": result.get("expires_in"),
                        "token_type": result.get("token_type", "Bearer")
                    }
                })
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


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8081))
    debug = os.getenv("DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
