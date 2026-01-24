# Cube API - MLOps 平台服务
# 提供模型管理、训练任务、部署服务等功能

FROM python:3.10-slim

WORKDIR /app

# 复制依赖文件
COPY services/cube-api/requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY services/cube-api/ /app/
COPY services/shared/ /app/shared/

# 创建非 root 用户
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# 健康检查
HEALTHCHECK --interval=10s --timeout=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8002/health', timeout=2)" || exit 1

# 暴露端口
EXPOSE 8002

# 启动命令
CMD ["python", "-u", "app.py"]
