# OpenAI 代理服务
# Sprint 1.2: 真实 OpenAI API 调用

FROM python:3.10.14-slim

WORKDIR /app

# 复制依赖文件
COPY services/openai-proxy/requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY services/openai-proxy/main.py /app/

# 创建非 root 用户
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# 健康检查 - 使用 Python 标准库 (无需 requests)
HEALTHCHECK --interval=10s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=2)" || exit 1

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["python", "-u", "main.py"]
