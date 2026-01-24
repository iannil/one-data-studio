# Alldata API - 持久化版本
# Sprint 1.1: MySQL + SQLAlchemy 实现

FROM python:3.10.14-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY services/alldata-api/requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制共享模块
COPY services/shared/ /app/shared/

# 复制应用代码
COPY services/alldata-api/src/ /app/src/

# 创建非 root 用户
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# 健康检查 - 使用 Python 标准库 (无需 requests)
HEALTHCHECK --interval=10s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8001/health', timeout=2)" || exit 1

# 暴露端口 (与 docker-compose.yml 一致)
EXPOSE 8001

# 启动命令
CMD ["python", "-u", "src/main.py"]
