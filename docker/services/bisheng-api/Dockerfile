# Bisheng API Dockerfile
# Sprint 1.3 + Sprint 3.1: 添加 JWT 认证
FROM python:3.10-slim

WORKDIR /app

# 安装依赖
COPY services/bisheng-api/requirements.txt /app/
RUN pip install --no-cache-dir -r /app/requirements.txt

# 复制共享认证模块
COPY services/shared/ /app/shared/

# 复制应用代码
COPY services/bisheng-api/app.py /app/

EXPOSE 8081

# 环境变量
ENV PYTHONUNBUFFERED=1
ENV AUTH_MODE=true

# 健康检查
HEALTHCHECK --interval=10s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8081/api/v1/health || exit 1

CMD ["python", "/app/app.py"]
