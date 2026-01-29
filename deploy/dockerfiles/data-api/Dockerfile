# Data API - 持久化版本
# Sprint 1.1: MySQL + SQLAlchemy 实现
# 多阶段构建 - 减少镜像体积和攻击面

# ============ 构建阶段 ============
# SECURITY: Using pinned Python version. For production, consider using image digest:
# FROM python:3.10.14-slim@sha256:<digest> AS builder
FROM python:3.10.14-slim AS builder

WORKDIR /build

# 安装系统构建依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY services/data-api/requirements.txt .

# 创建虚拟环境并安装依赖
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir -r requirements.txt

# ============ 运行阶段 ============
FROM python:3.10.14-slim AS runtime

# Image labels for traceability
LABEL org.opencontainers.image.title="Data API"
LABEL org.opencontainers.image.description="ONE-DATA-STUDIO Data Governance API"
LABEL org.opencontainers.image.version="2.0.0"
LABEL org.opencontainers.image.vendor="ONE-DATA-STUDIO"
LABEL org.opencontainers.image.source="https://github.com/one-data-studio/one-data-studio"

WORKDIR /app

# 仅安装运行时必需的系统库（不含构建工具）
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmariadb3 \
    && rm -rf /var/lib/apt/lists/*

# 从构建阶段复制虚拟环境
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 复制共享模块
COPY services/shared/ /app/shared/

# 复制应用代码（完整目录结构）
COPY services/data-api/ /app/

# 创建非 root 用户
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# 健康检查 - 使用 Python 标准库 (无需 requests)
HEALTHCHECK --interval=10s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8001/api/v1/health', timeout=2)" || exit 1

# 暴露端口 (与 docker-compose.yml 一致)
EXPOSE 8001

# 启动命令
CMD ["python", "-u", "src/main.py"]
