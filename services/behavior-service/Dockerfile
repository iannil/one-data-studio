# 用户行为管理服务 Dockerfile

FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 复制应用代码
COPY . .

# 环境变量
ENV PYTHONPATH=/app

# 暴露端口
EXPOSE 8008

# 启动命令
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8008"]
