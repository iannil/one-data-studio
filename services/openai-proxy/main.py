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
import requests
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

# ==================== Prometheus 指标 ====================

# 尝试导入共享 Prometheus 指标模块
try:
    sys.path.insert(0, '/app/shared')
    from prometheus_metrics import PrometheusMetrics, init_metrics, track_ai_call
    metrics = init_metrics(app, service_name="openai-proxy")
    PROMETHEUS_ENABLED = True
    logger.info("Prometheus metrics initialized")
except ImportError:
    PROMETHEUS_ENABLED = False
    metrics = None
    # 创建装饰器占位符
    def track_ai_call(m, s, mo):
        def decorator(f):
            return f
        return decorator
    logger.warning("Prometheus metrics not available")

# ==================== vLLM 集成 ====================

# vLLM 服务端点配置
VLLM_CHAT_URL = os.getenv("VLLM_CHAT_URL", "http://vllm-chat:8000")
VLLM_EMBED_URL = os.getenv("VLLM_EMBED_URL", "http://vllm-embed:8000")
VLLM_HEALTH_CHECK_TIMEOUT = int(os.getenv("VLLM_HEALTH_CHECK_TIMEOUT", "5"))

# vLLM 健康状态缓存
_vllm_chat_healthy = None
_vllm_embed_healthy = None
_vllm_last_check = 0
VLLM_HEALTH_CACHE_TTL = 30  # 健康检查缓存30秒

# ==================== Ollama 集成 ====================

# Ollama 服务端点配置
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")
OLLAMA_HEALTH_CHECK_TIMEOUT = int(os.getenv("OLLAMA_HEALTH_CHECK_TIMEOUT", "5"))

# LLM 后端优先级: auto (vLLM→Ollama→OpenAI), vllm, ollama, openai
LLM_BACKEND = os.getenv("LLM_BACKEND", "auto")

# Ollama 健康状态缓存
_ollama_healthy = None
_ollama_last_check = 0


def _check_vllm_health(url: str) -> bool:
    """检查 vLLM 服务健康状态"""
    global _vllm_last_check, _vllm_chat_healthy, _vllm_embed_healthy
    try:
        import time
        current_time = time.time()

        # 使用缓存避免频繁检查
        if current_time - _vllm_last_check < VLLM_HEALTH_CACHE_TTL:
            if url == VLLM_CHAT_URL:
                return _vllm_chat_healthy if _vllm_chat_healthy is not None else False
            elif url == VLLM_EMBED_URL:
                return _vllm_embed_healthy if _vllm_embed_healthy is not None else False

        response = requests.get(
            f"{url}/health",
            timeout=VLLM_HEALTH_CHECK_TIMEOUT
        )
        is_healthy = response.status_code == 200

        # 更新缓存
        _vllm_last_check = current_time
        if url == VLLM_CHAT_URL:
            _vllm_chat_healthy = is_healthy
        elif url == VLLM_EMBED_URL:
            _vllm_embed_healthy = is_healthy

        return is_healthy
    except Exception as e:
        logger.debug(f"vLLM health check failed for {url}: {e}")
        return False


def is_vllm_chat_available() -> bool:
    """检查 vLLM Chat 服务是否可用"""
    return _check_vllm_health(VLLM_CHAT_URL)


def is_vllm_embed_available() -> bool:
    """检查 vLLM Embedding 服务是否可用"""
    return _check_vllm_health(VLLM_EMBED_URL)


# ==================== Ollama 健康检查与客户端 ====================

def _check_ollama_health() -> bool:
    """检查 Ollama 服务健康状态"""
    global _ollama_last_check, _ollama_healthy
    try:
        import time
        current_time = time.time()

        # 使用缓存避免频繁检查
        if current_time - _ollama_last_check < VLLM_HEALTH_CACHE_TTL:
            return _ollama_healthy if _ollama_healthy is not None else False

        response = requests.get(
            f"{OLLAMA_URL}/api/tags",
            timeout=OLLAMA_HEALTH_CHECK_TIMEOUT
        )
        is_healthy = response.status_code == 200

        # 更新缓存
        _ollama_last_check = current_time
        _ollama_healthy = is_healthy

        return is_healthy
    except Exception as e:
        logger.debug(f"Ollama health check failed: {e}")
        _ollama_healthy = False
        return False


def is_ollama_available() -> bool:
    """检查 Ollama 服务是否可用"""
    return _check_ollama_health()


_ollama_client = None


def get_ollama_client():
    """获取 Ollama 客户端（兼容 OpenAI 的 /v1 端点）"""
    global _ollama_client

    if not OPENAI_AVAILABLE:
        logger.warning("OpenAI library not available")
        return None

    if is_ollama_available():
        if _ollama_client is None:
            _ollama_client = AsyncOpenAI(
                api_key="ollama",  # Ollama 不需要真实 API key
                base_url=f"{OLLAMA_URL}/v1"
            )
            logger.info(f"Ollama client initialized: {OLLAMA_URL}/v1")
        return _ollama_client

    return None


# OpenAI 客户端（外部API备用）
_openai_client = None
_vllm_chat_client = None
_vllm_embed_client = None


def get_vllm_chat_client():
    """获取 vLLM Chat 客户端（优先）"""
    global _vllm_chat_client

    if not OPENAI_AVAILABLE:
        logger.warning("OpenAI library not available")
        return None

    if is_vllm_chat_available():
        if _vllm_chat_client is None:
            _vllm_chat_client = AsyncOpenAI(
                api_key="dummy",  # vLLM不需要真实API key
                base_url=VLLM_CHAT_URL
            )
            logger.info(f"vLLM Chat client initialized: {VLLM_CHAT_URL}")
        return _vllm_chat_client

    return None


def get_vllm_embed_client():
    """获取 vLLM Embedding 客户端（优先）"""
    global _vllm_embed_client

    if not OPENAI_AVAILABLE:
        logger.warning("OpenAI library not available")
        return None

    if is_vllm_embed_available():
        if _vllm_embed_client is None:
            _vllm_embed_client = AsyncOpenAI(
                api_key="dummy",
                base_url=VLLM_EMBED_URL
            )
            logger.info(f"vLLM Embed client initialized: {VLLM_EMBED_URL}")
        return _vllm_embed_client

    return None


def get_openai_client():
    """获取 OpenAI 客户端（备用）"""
    global _openai_client
    if _openai_client is None:
        if not OPENAI_AVAILABLE:
            logger.warning("OpenAI library not available")
            return None

        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            logger.warning("OPENAI_API_KEY not set")
            return None

        base_url = os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1')
        _openai_client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url
        )
        logger.info(f"OpenAI client initialized: {base_url}")
    return _openai_client


def get_chat_client():
    """获取聊天客户端（优先级: vLLM → Ollama → OpenAI, 可通过 LLM_BACKEND 强制指定）"""
    # 强制指定后端
    if LLM_BACKEND == "vllm":
        client = get_vllm_chat_client()
        if client:
            return client, "vllm"
        return None, None
    elif LLM_BACKEND == "ollama":
        client = get_ollama_client()
        if client:
            return client, "ollama"
        return None, None
    elif LLM_BACKEND == "openai":
        client = get_openai_client()
        if client:
            return client, "openai"
        return None, None

    # auto 模式: vLLM → Ollama → OpenAI
    client = get_vllm_chat_client()
    if client:
        return client, "vllm"

    client = get_ollama_client()
    if client:
        return client, "ollama"

    client = get_openai_client()
    if client:
        return client, "openai"

    return None, None


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
    # 检查vLLM服务
    vllm_chat_ok = is_vllm_chat_available()
    vllm_embed_ok = is_vllm_embed_available()

    # 检查Ollama服务
    ollama_ok = is_ollama_available()

    # 检查OpenAI配置
    openai_client = get_openai_client()
    openai_configured = openai_client is not None and os.getenv('OPENAI_API_KEY')

    # 确定使用哪个服务
    if vllm_chat_ok:
        backend = "vllm"
        backend_status = "ok"
    elif ollama_ok:
        backend = "ollama"
        backend_status = "ok"
    elif openai_configured:
        backend = "openai"
        backend_status = "ok"
    else:
        backend = "none"
        backend_status = "unavailable"

    return jsonify({
        "status": "ok" if backend_status == "ok" else "degraded",
        "service": "openai-proxy",
        "version": "1.0.0",
        "backend": backend,
        "llm_backend_mode": LLM_BACKEND,
        "vllm": {
            "chat_available": vllm_chat_ok,
            "chat_url": VLLM_CHAT_URL,
            "embed_available": vllm_embed_ok,
            "embed_url": VLLM_EMBED_URL
        },
        "ollama": {
            "available": ollama_ok,
            "url": OLLAMA_URL
        },
        "openai": {
            "configured": openai_configured,
            "base_url": os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1')
        }
    })


@app.route("/v1/models")
@require_jwt(optional=True)
def list_models():
    """列出可用模型"""
    client, backend = get_chat_client()

    if not client:
        # C-03 安全修复: 生产环境必须配置 LLM 服务
        if os.getenv("ENVIRONMENT") == "production":
            logger.error("No LLM client available in production for /v1/models")
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
                    "id": os.getenv("VLLM_CHAT_MODEL", "Qwen/Qwen2.5-1.5B-Instruct"),
                    "object": "model",
                    "created": 1234567890,
                    "owned_by": "vllm"
                }
            ],
            "_warning": "This is mock data. Configure VLLM_CHAT_URL or OPENAI_API_KEY for real model list."
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

        # 添加后端信息
        if isinstance(models_data, dict) and "data" in models_data:
            models_data["backend"] = backend

        # 合并 Ollama 模型列表（如果当前后端不是 Ollama 且 Ollama 可用）
        if backend != "ollama" and is_ollama_available():
            try:
                ollama_resp = requests.get(
                    f"{OLLAMA_URL}/api/tags",
                    timeout=OLLAMA_HEALTH_CHECK_TIMEOUT
                )
                if ollama_resp.status_code == 200:
                    ollama_models = ollama_resp.json().get("models", [])
                    for m in ollama_models:
                        models_data.setdefault("data", []).append({
                            "id": m.get("name", "unknown"),
                            "object": "model",
                            "created": int(datetime.fromisoformat(
                                m["modified_at"].replace("Z", "+00:00")
                            ).timestamp()) if m.get("modified_at") else 0,
                            "owned_by": "ollama"
                        })
            except Exception as e:
                logger.debug(f"Failed to fetch Ollama models: {e}")

        return jsonify(models_data)

    except Exception as e:
        logger.error(f"Error listing models: {e}")
        # 返回默认模型列表
        return jsonify({
            "object": "list",
            "data": [
                {
                    "id": os.getenv("VLLM_CHAT_MODEL", "Qwen/Qwen2.5-1.5B-Instruct"),
                    "object": "model",
                    "created": 1234567890,
                    "owned_by": backend or "unknown"
                }
            ],
            "backend": backend
        })


# ==================== Chat Completions ====================

@app.route("/v1/chat/completions", methods=["POST"])
@require_jwt()
def chat_completions():
    """OpenAI 兼容的聊天补全接口（优先vLLM，降级OpenAI）"""
    data = request.json

    # 获取参数
    model = data.get("model", os.getenv("VLLM_CHAT_MODEL", "gpt-4o-mini"))
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

    # 获取聊天客户端（优先vLLM，降级OpenAI）
    client, backend = get_chat_client()

    if not client:
        # C-03 安全修复: 生产环境必须配置 LLM 服务
        if os.getenv("ENVIRONMENT") == "production":
            logger.error(
                "CRITICAL: No LLM client available in production. "
                "Configure VLLM_CHAT_URL or OPENAI_API_KEY."
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
            "No LLM client available, returning mock response. "
            "Configure VLLM_CHAT_URL or OPENAI_API_KEY for production use. "
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
            "_warning": "This is a mock response. Configure VLLM_CHAT_URL or OPENAI_API_KEY for real responses."
        })

    # 真实 LLM 调用（vLLM 或 OpenAI）
    import time
    start_time = time.time()
    status = "success"
    prompt_tokens = 0
    completion_tokens = 0

    try:
        import asyncio

        if stream:
            # 流式响应
            async def generate_stream():
                nonlocal status
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
                    status = "error"
                    logger.error(f"{backend} stream error: {e}")
                    error_data = {
                        "error": {"message": str(e), "type": f"{backend}_error"}
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

            # 添加后端信息
            result["backend"] = backend

            # 提取 token 使用情况
            usage = result.get('usage', {})
            prompt_tokens = usage.get('prompt_tokens', 0)
            completion_tokens = usage.get('completion_tokens', 0)

            # 记录日志
            logger.info(f"Chat completion: backend={backend}, model={model}, tokens={usage.get('total_tokens', 0)}")

            return jsonify(result)

    except OpenAIError as e:
        status = "error"
        logger.error(f"{backend} API error: {e}")
        return jsonify({
            "error": {
                "message": str(e),
                "type": f"{backend}_error",
                "code": f"{backend}_error"
            }
        }), 500
    finally:
        # 记录 AI 服务调用指标
        duration = time.time() - start_time
        if PROMETHEUS_ENABLED and metrics:
            metrics.record_ai_request(
                service=backend,
                model=model,
                status=status,
                duration=duration,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens
            )


# ==================== Embeddings ====================

@app.route("/v1/embeddings", methods=["POST"])
@require_jwt()
def embeddings():
    """OpenAI 兼容的嵌入接口（优先vLLM，降级OpenAI）"""
    data = request.json

    # 获取参数
    model = data.get("model", os.getenv("VLLM_EMBED_MODEL", "BAAI/bge-base-zh-v1.5"))
    input_text = data.get("input", [])
    encoding_format = data.get("encoding_format", "float")

    # 支持 single string 或 array
    if isinstance(input_text, str):
        inputs = [input_text]
    else:
        inputs = input_text

    # 获取 embedding 客户端（优先vLLM → Ollama → OpenAI）
    client = get_vllm_embed_client()
    backend = "vllm" if client else None

    if not client:
        client = get_ollama_client()
        backend = "ollama" if client else None

    if not client:
        client = get_openai_client()
        backend = "openai" if client else None

    if not client:
        # C-03 安全修复: 生产环境必须配置 LLM 服务
        if os.getenv("ENVIRONMENT") == "production":
            logger.error(
                "CRITICAL: No Embedding client available in production. "
                "Configure VLLM_EMBED_URL or OPENAI_API_KEY."
            )
            return jsonify({
                "error": {
                    "message": "Embedding service not configured. Contact administrator.",
                    "type": "service_unavailable",
                    "code": "embedding_not_configured"
                }
            }), 503

        # Mock 响应（仅用于开发/测试）
        logger.warning(
            "No Embedding client available, returning mock response. "
            "Configure VLLM_EMBED_URL or OPENAI_API_KEY for production use."
        )

        import numpy as np
        mock_embeddings = [np.random.rand(768).tolist() for _ in inputs]

        return jsonify({
            "object": "list",
            "data": [
                {
                    "object": "embedding",
                    "embedding": emb,
                    "index": i
                }
                for i, emb in enumerate(mock_embeddings)
            ],
            "model": model,
            "usage": {
                "prompt_tokens": sum(len(text) for text in inputs),
                "total_tokens": sum(len(text) for text in inputs)
            },
            "_warning": "This is a mock response. Configure VLLM_EMBED_URL or OPENAI_API_KEY for real embeddings."
        })

    # 真实 Embedding 调用
    import time
    start_time = time.time()
    status = "success"

    try:
        import asyncio

        async def _create_embeddings():
            # 批量处理（vLLM/OpenAI都支持）
            response = await client.embeddings.create(
                model=model,
                input=inputs
            )
            return response.model_dump()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(_create_embeddings())
        finally:
            loop.close()

        # 添加后端信息
        result["backend"] = backend

        # 记录日志
        logger.info(f"Embeddings: backend={backend}, model={model}, count={len(inputs)}")

        return jsonify(result)

    except OpenAIError as e:
        status = "error"
        logger.error(f"{backend} Embedding API error: {e}")
        return jsonify({
            "error": {
                "message": str(e),
                "type": f"{backend}_error",
                "code": f"{backend}_error"
            }
        }), 500
    finally:
        # 记录 AI 服务调用指标
        duration = time.time() - start_time
        if PROMETHEUS_ENABLED and metrics:
            metrics.record_ai_request(
                service=f"{backend}_embedding",
                model=model,
                status=status,
                duration=duration,
                prompt_tokens=sum(len(text) for text in inputs),
                completion_tokens=0
            )


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
