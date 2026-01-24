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

# 暴露端口 (与 docker-compose.yml 一致)
EXPOSE 8000

# 环境变量
ENV PYTHONUNBUFFERED=1
ENV AUTH_MODE=true

# 健康检查 - 使用 Python 而非 curl (slim 镜像无 curl)
HEALTHCHECK --interval=10s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=2)" || exit 1

CMD ["python", "/app/app.py"]
