"""
OpenAI 代理服务
Sprint 1.2: 真实 OpenAI API 调用代理

功能：
- OpenAI 兼容 API 接口
- API Key 管理（通过 K8s Secret）
- 请求/响应日志
- 流式输出支持（SSE）
- Prompt 模板管理
- JWT 认证保护
"""

import os
import sys
import logging
import json
import functools
from typing import AsyncGenerator, Optional
from datetime import datetime

try:
    from openai import AsyncOpenAI, OpenAIError
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    AsyncOpenAI = None
    OpenAIError = Exception

from flask import Flask, jsonify, request, Response, stream_with_context, g

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 认证模式配置
AUTH_MODE = os.getenv("AUTH_MODE", "true").lower() == "true"

# C-02 安全修复: 生产环境强制认证
if not AUTH_MODE:
    if os.getenv("ENVIRONMENT") == "production":
        raise ValueError(
            "CRITICAL: AUTH_MODE cannot be disabled in production environment. "
            "Remove AUTH_MODE=false or set ENVIRONMENT to a non-production value."
        )
    logger.warning(
        "SECURITY WARNING: AUTH_MODE is disabled. All requests will bypass authentication. "
        "This should ONLY be used for local development."
    )

# 尝试导入共享 JWT 中间件
try:
    sys.path.insert(0, '/app/shared')
    from auth.jwt_middleware import (
        decode_jwt_token,
        extract_token_from_request,
        get_user_roles
    )
    JWT_SHARED_AVAILABLE = True
except ImportError:
    JWT_SHARED_AVAILABLE = False

    # C-02 安全修复: 共享 JWT 模块不可用时的安全处理
    # 生产环境必须有共享 JWT 模块
    if os.getenv("ENVIRONMENT") == "production":
        raise ImportError(
            "CRITICAL: Shared JWT authentication module is required in production. "
            "Ensure /app/shared/auth/jwt_middleware.py is available and all dependencies are installed."
        )

    logger.warning(
        "SECURITY WARNING: Shared JWT module not available. "
        "Using secure fallback that rejects all authenticated requests. "
        "This should only occur in development/testing environments."
    )

    def extract_token_from_request(request_obj):
        auth_header = request_obj.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return auth_header[7:]
        return None

    def get_user_roles(payload):
        roles = []
        resource_access = payload.get("resource_access", {})
        for client, client_data in resource_access.items():
            roles.extend(client_data.get("roles", []))
        realm_access = payload.get("realm_access", {})
        roles.extend(realm_access.get("roles", []))
        return roles

    def decode_jwt_token(token):
        # C-02 安全修复: 拒绝所有 Token 验证请求，而不是使用不安全的 Base64 解码
        # 这比返回伪造数据更安全，因为它会强制请求失败而不是授权未验证的用户
        logger.error(
            "JWT token validation requested but shared JWT module is not available. "
            "Rejecting token for security. Configure proper JWT validation in production."
        )
        return None


def require_jwt(optional: bool = False):
    """
    JWT 认证装饰器

    C-02 安全修复: 为 OpenAI Proxy 添加认证保护

    Args:
        optional: 是否可选认证
    """
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            # 跳过认证检查（仅开发环境）
            if not AUTH_MODE:
                g.user = "dev_user"
                g.roles = ["admin"]
                g.payload = {}
                return fn(*args, **kwargs)

            # 提取 Token
            token = extract_token_from_request(request)

            if not token:
                if optional:
                    g.user = None
                    g.roles = []
                    g.payload = None
                    return fn(*args, **kwargs)
                return jsonify({
                    "error": {
                        "message": "Missing authentication token",
                        "type": "authentication_error",
                        "code": "unauthorized"
                    }
                }), 401

            # 验证 Token
            payload = decode_jwt_token(token)

            if not payload:
                if optional:
                    g.user = None
                    g.roles = []
                    g.payload = None
                    return fn(*args, **kwargs)
                return jsonify({
                    "error": {
                        "message": "Invalid or expired token",
                        "type": "authentication_error",
                        "code": "invalid_token"
                    }
                }), 401

            # 存储用户信息到 Flask g 对象
            g.payload = payload
            g.user = payload.get("preferred_username") or payload.get("email") or payload.get("sub", "unknown")
            g.user_id = payload.get("sub")
            g.roles = get_user_roles(payload)

            return fn(*args, **kwargs)

        return wrapper
    return decorator

# 创建 Flask 应用
app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False

# OpenAI 客户端
_client = None


def get_openai_client():
    """获取 OpenAI 客户端"""
    global _client
    if _client is None:
        if not OPENAI_AVAILABLE:
            logger.warning("OpenAI library not available")
            return None

        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            logger.warning("OPENAI_API_KEY not set")
            return None

        base_url = os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1')
        _client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url
        )
        logger.info(f"OpenAI client initialized: {base_url}")
    return _client


# ==================== Prompt 模板管理 ====================

PROMPT_TEMPLATES = {
    "default": "你是一个智能助手，请根据用户的问题提供准确、有帮助的回答。",
    "rag": """你是一个基于检索增强生成（RAG）的智能助手。
请根据以下上下文信息回答用户问题：

{context}

如果上下文中没有相关信息，请明确告知用户。

用户问题：{question}""",
    "sql": """你是一个数据分析师助手。请根据以下数据库元数据生成 SQL 查询：

数据库：{database}
表结构：
{schema}

用户查询需求：{question}

请只返回 SQL 语句，不要包含任何解释。""",
    "chat": "你是一个友好的聊天助手，请用简洁、自然的语言回答用户问题。"
}


def get_prompt_template(template_name: str, **kwargs) -> str:
    """获取 Prompt 模板并填充变量"""
    template = PROMPT_TEMPLATES.get(template_name, PROMPT_TEMPLATES["default"])
    return template.format(**kwargs)


# ==================== 健康检查 ====================

@app.route("/health")
def health():
    """健康检查"""
    client = get_openai_client()
    api_configured = client is not None and os.getenv('OPENAI_API_KEY')

    return jsonify({
        "status": "ok",
        "service": "openai-proxy",
        "version": "1.0.0",
        "openai_configured": api_configured,
        "base_url": os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1')
    })


@app.route("/v1/models")
@require_jwt(optional=True)
def list_models():
    """列出可用模型"""
    client = get_openai_client()

    if not client:
        # C-03 安全修复: 生产环境必须配置 OpenAI API
        if os.getenv("ENVIRONMENT") == "production":
            logger.error("OpenAI client not available in production for /v1/models")
            return jsonify({
                "error": {
                    "message": "LLM service not configured. Contact administrator.",
                    "type": "service_unavailable",
                    "code": "llm_not_configured"
                }
            }), 503

        # Mock 响应（仅用于开发/测试）
        return jsonify({
            "object": "list",
            "data": [
                {
                    "id": "gpt-4o-mini",
                    "object": "model",
                    "created": 1234567890,
                    "owned_by": "openai"
                },
                {
                    "id": "gpt-4o",
                    "object": "model",
                    "created": 1234567890,
                    "owned_by": "openai"
                },
                {
                    "id": "gpt-4-turbo",
                    "object": "model",
                    "created": 1234567890,
                    "owned_by": "openai"
                },
                {
                    "id": "gpt-3.5-turbo",
                    "object": "model",
                    "created": 1234567890,
                    "owned_by": "openai"
                }
            ],
            "_warning": "This is mock data. Configure OPENAI_API_KEY for real model list."
        })

    try:
        # 使用同步方式请求模型列表
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def _list():
            models = await client.models.list()
            return models.model_dump()

        models_data = loop.run_until_complete(_list())
        loop.close()

        return jsonify(models_data)

    except Exception as e:
        logger.error(f"Error listing models: {e}")
        # 返回默认模型列表
        return jsonify({
            "object": "list",
            "data": [
                {"id": "gpt-4o-mini", "object": "model", "created": 1234567890, "owned_by": "openai"},
                {"id": "gpt-4o", "object": "model", "created": 1234567890, "owned_by": "openai"}
            ]
        })


# ==================== Chat Completions ====================

@app.route("/v1/chat/completions", methods=["POST"])
@require_jwt()
def chat_completions():
    """OpenAI 兼容的聊天补全接口"""
    data = request.json

    # 获取参数
    model = data.get("model", "gpt-4o-mini")
    messages = data.get("messages", [])
    stream = data.get("stream", False)
    temperature = data.get("temperature", 0.7)
    max_tokens = data.get("max_tokens", 2000)

    # 检查是否有 Prompt 模板
    prompt_template = data.get("prompt_template")
    if prompt_template:
        context = data.get("context", {})
        system_message = get_prompt_template(prompt_template, **context)
        # 更新或添加 system 消息
        if messages and messages[0].get("role") == "system":
            messages[0]["content"] = system_message
        else:
            messages.insert(0, {"role": "system", "content": system_message})

    client = get_openai_client()

    if not client:
        # C-03 安全修复: 生产环境必须配置 OpenAI API
        if os.getenv("ENVIRONMENT") == "production":
            logger.error(
                "CRITICAL: OpenAI client not available in production. "
                "Set OPENAI_API_KEY environment variable."
            )
            return jsonify({
                "error": {
                    "message": "LLM service not configured. Contact administrator.",
                    "type": "service_unavailable",
                    "code": "llm_not_configured"
                }
            }), 503

        # Mock 响应（仅用于开发/测试）
        logger.warning(
            "OpenAI client not available, returning mock response. "
            "Set OPENAI_API_KEY environment variable for production use. "
            "Mock responses are for development/testing only."
        )
        user_message = ""
        for msg in messages:
            if msg.get("role") == "user":
                user_message = msg.get("content", "")
                break

        if stream:
            def generate():
                response_text = f"[Mock 响应 - 仅开发环境] 您好！我收到了您的问题：{user_message}"
                for char in response_text:
                    chunk = {
                        "id": "chatcmpl-mock",
                        "object": "chat.completion.chunk",
                        "created": 1234567890,
                        "model": model,
                        "choices": [{
                            "index": 0,
                            "delta": {"content": char},
                            "finish_reason": None
                        }]
                    }
                    yield f"data: {json.dumps(chunk)}\n\n"
                # 结束 chunk
                final_chunk = {
                    "id": "chatcmpl-mock",
                    "object": "chat.completion.chunk",
                    "created": 1234567890,
                    "model": model,
                    "choices": [{
                        "index": 0,
                        "delta": {},
                        "finish_reason": "stop"
                    }]
                }
                yield f"data: {json.dumps(final_chunk)}\n\n"
                yield "data: [DONE]\n\n"

            return Response(stream_with_context(generate()), content_type="text/event-stream")

        return jsonify({
            "id": "chatcmpl-mock",
            "object": "chat.completion",
            "created": 1234567890,
            "model": model,
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": f"[Mock 响应 - 仅开发环境] 您好！我收到了您的问题：{user_message}"
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": sum(len(m.get("content", "")) for m in messages),
                "completion_tokens": 50,
                "total_tokens": sum(len(m.get("content", "")) for m in messages) + 50
            },
            "_warning": "This is a mock response. Configure OPENAI_API_KEY for real responses."
        })

    # 真实 OpenAI 调用
    try:
        import asyncio

        if stream:
            # 流式响应
            async def generate_stream():
                try:
                    stream_response = await client.chat.completions.create(
                        model=model,
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        stream=True
                    )

                    async for chunk in stream_response:
                        chunk_data = chunk.model_dump()
                        yield f"data: {json.dumps(chunk_data)}\n\n"

                    yield "data: [DONE]\n\n"

                except OpenAIError as e:
                    logger.error(f"OpenAI stream error: {e}")
                    error_data = {
                        "error": {"message": str(e), "type": "openai_error"}
                    }
                    yield f"data: {json.dumps(error_data)}\n\n"

            def sync_generate():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    for chunk in loop.run_until_complete(generate_stream()):
                        yield chunk
                finally:
                    loop.close()

            return Response(stream_with_context(sync_generate()), content_type="text/event-stream")

        else:
            # 非流式响应
            async def _create():
                response = await client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                return response.model_dump()

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(_create())
            finally:
                loop.close()

            # 记录日志
            logger.info(f"Chat completion: model={model}, tokens={result.get('usage', {}).get('total_tokens', 0)}")

            return jsonify(result)

    except OpenAIError as e:
        logger.error(f"OpenAI API error: {e}")
        return jsonify({
            "error": {
                "message": str(e),
                "type": "openai_error",
                "code": "openai_error"
            }
        }), 500


# ==================== Prompt 模板管理 API ====================

@app.route("/api/v1/templates", methods=["GET"])
@require_jwt()
def list_templates():
    """列出所有 Prompt 模板"""
    return jsonify({
        "code": 0,
        "message": "success",
        "data": {
            "templates": list(PROMPT_TEMPLATES.keys())
        }
    })


@app.route("/api/v1/templates/<template_name>", methods=["GET"])
@require_jwt()
def get_template(template_name: str):
    """获取 Prompt 模板内容"""
    template = PROMPT_TEMPLATES.get(template_name)
    if template:
        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "name": template_name,
                "template": template
            }
        })
    return jsonify({
        "code": 40401,
        "message": f"Template {template_name} not found"
    }), 404


@app.route("/api/v1/templates", methods=["POST"])
@require_jwt()
def create_template():
    """创建新的 Prompt 模板"""
    data = request.json
    name = data.get("name")
    template = data.get("template")

    if not name or not template:
        return jsonify({
            "code": 40001,
            "message": "name and template are required"
        }), 400

    PROMPT_TEMPLATES[name] = template
    return jsonify({
        "code": 0,
        "message": "success",
        "data": {"name": name}
    }), 201


# ==================== 使用统计 ====================

@app.route("/api/v1/stats", methods=["GET"])
@require_jwt()
def get_stats():
    """获取使用统计"""
    # 实际实现中应从数据库或缓存中获取
    return jsonify({
        "code": 0,
        "message": "success",
        "data": {
            "total_requests": 0,
            "total_tokens": 0,
            "models": ["gpt-4o-mini", "gpt-4o"]
        }
    })


# 启动应用
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    logger.info(f"Starting OpenAI Proxy on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False)
