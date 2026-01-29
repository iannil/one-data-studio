# Agent API Dockerfile
# Sprint 1.3 + Sprint 3.1: 添加 JWT 认证
# 多阶段构建 - 减少镜像体积和攻击面

# ============ 构建阶段 ============
# SECURITY: Using pinned Python version. For production, consider using image digest:
# FROM python:3.10.14-slim@sha256:<digest> AS builder
FROM python:3.10.14-slim AS builder

WORKDIR /build

# 复制依赖文件
COPY services/agent-api/requirements.txt .

# 创建虚拟环境并安装依赖
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir -r requirements.txt

# ============ 运行阶段 ============
FROM python:3.10.14-slim AS runtime

# Image labels for traceability
LABEL org.opencontainers.image.title="Agent API"
LABEL org.opencontainers.image.description="ONE-DATA-STUDIO LLMOps Application Orchestration API"
LABEL org.opencontainers.image.version="1.1.0"
LABEL org.opencontainers.image.vendor="ONE-DATA-STUDIO"
LABEL org.opencontainers.image.source="https://github.com/one-data-studio/one-data-studio"

WORKDIR /app

# 从构建阶段复制虚拟环境
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 复制共享认证模块
COPY services/shared/ /app/shared/

# 复制应用代码（包含所有模块）
COPY services/agent-api/ /app/

# 创建非 root 用户
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# 暴露端口 (与 docker-compose.yml 一致)
EXPOSE 8000

# 环境变量
ENV PYTHONUNBUFFERED=1
ENV AUTH_MODE=true

# 健康检查 - 使用 Python 而非 curl (slim 镜像无 curl)
HEALTHCHECK --interval=10s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health', timeout=2)" || exit 1

CMD ["python", "/app/app.py"]
