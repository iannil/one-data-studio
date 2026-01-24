# ==================== 开发阶段 ====================
FROM node:25-alpine AS development

# 安装 libc6-compat 用于兼容性
RUN apk add --no-cache libc6-compat

# 设置工作目录
WORKDIR /app

# 复制 package.json 和 package-lock.json
COPY package.json package-lock.json* ./

# 安装所有依赖（包括 devDependencies）
RUN npm ci

# 复制源代码
COPY . .

# 暴露 Vite 开发服务器端口
EXPOSE 5173

# 启动开发服务器（支持热重载）
CMD ["npm", "run", "dev", "--", "--host"]

# ==================== 构建阶段 ====================
FROM node:25-alpine AS builder

# 安装 libc6-compat 用于兼容性
RUN apk add --no-cache libc6-compat

# 设置工作目录
WORKDIR /app

# 复制 package.json 和 package-lock.json
COPY package.json package-lock.json* ./

# 安装依赖
RUN npm ci

# 复制源代码
COPY . .

# 构建项目（注入环境变量）
ARG VITE_API_ALLDATA_URL
ARG VITE_API_BISHENG_URL
ARG VITE_API_CUBE_URL
ARG VITE_AUTH_MODE
ENV VITE_API_ALLDATA_URL=${VITE_API_ALLDATA_URL}
ENV VITE_API_BISHENG_URL=${VITE_API_BISHENG_URL}
ENV VITE_API_CUBE_URL=${VITE_API_CUBE_URL}
ENV VITE_AUTH_MODE=${VITE_AUTH_MODE}

RUN npm run build

# ==================== 生产阶段 ====================
FROM nginx:alpine AS production

# 安装 curl 用于健康检查
RUN apk add --no-cache curl

# 从构建阶段复制构建产物
COPY --from=builder /app/dist /usr/share/nginx/html

# 复制 nginx 配置
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 创建非特权用户
RUN addgroup -g 1001 -S nodejs && \
    adduser -S nodejs -u 1001 && \
    chown -R nodejs:nodejs /usr/share/nginx/html && \
    chown -R nodejs:nodejs /var/cache/nginx && \
    chown -R nodejs:nodejs /var/log/nginx && \
    touch /var/run/nginx.pid && \
    chown -R nodejs:nodejs /var/run/nginx.pid

# 切换到非特权用户
USER nodejs

# 暴露端口
EXPOSE 80

# 健康检查
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost/health || exit 1

# 启动 nginx
CMD ["nginx", "-g", "daemon off;"]
