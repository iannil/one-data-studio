#!/bin/bash
# ONE-DATA-STUDIO 测试环境一键启动脚本
# 用途：启动完整的测试环境，包括所有依赖服务

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
ENV_FILE="$SCRIPT_DIR/.env.test"
COMPOSE_FILE="$PROJECT_ROOT/deploy/local/docker-compose.yml"

log_info "ONE-DATA-STUDIO 测试环境启动脚本"
log_info "======================================"

# 步骤 1: 检查依赖
log_info "步骤 1/6: 检查依赖..."

# 检查 Docker
if ! command -v docker &> /dev/null; then
    log_error "Docker 未安装，请先安装 Docker"
    exit 1
fi
log_info "✓ Docker 已安装: $(docker --version | cut -d' ' -f3)"

# 检查 Docker Compose
if ! docker compose version &> /dev/null && ! docker-compose version &> /dev/null; then
    log_error "Docker Compose 未安装，请先安装 Docker Compose"
    exit 1
fi
log_info "✓ Docker Compose 已安装"

# 检查 Node.js (用于运行前端)
if ! command -v node &> /dev/null; then
    log_warn "Node.js 未安装，前端开发服务器无法启动"
else
    log_info "✓ Node.js 已安装: $(node --version)"
fi

# 步骤 2: 创建测试环境配置
log_info "步骤 2/6: 创建测试环境配置..."

if [ ! -f "$ENV_FILE" ]; then
    log_info "创建 .env.test 配置文件..."
    cat > "$ENV_FILE" << 'EOF'
# ONE-DATA-STUDIO 测试环境配置
# 此配置用于 E2E 测试环境

# MySQL 配置
MYSQL_ROOT_PASSWORD=test_root_password_123
MYSQL_DATABASE=onedata_test
MYSQL_USER=onedata_test
MYSQL_PASSWORD=test_password_123

# Redis 配置
REDIS_PASSWORD=test_redis_password_123

# MinIO 配置
MINIO_ROOT_USER=minio_admin
MINIO_ROOT_PASSWORD=test_minio_password_123

# Keycloak 配置
KEYCLOAK_ADMIN=admin
KEYCLOAK_ADMIN_PASSWORD=admin

# 测试用户凭证
TEST_USER_USERNAME=testuser
TEST_USER_PASSWORD=Test1234!
TEST_USER_EMAIL=testuser@example.com

# 测试管理员凭证
TEST_ADMIN_USERNAME=testadmin
TEST_ADMIN_PASSWORD=Admin1234!
TEST_ADMIN_EMAIL=testadmin@example.com

# 服务端口
WEB_PORT=3000
AGENT_API_PORT=8000
DATA_API_PORT=8001
MODEL_API_PORT=8002
OPENAI_PROXY_PORT=8003
KEYCLOAK_PORT=8080

# 测试超时设置
TEST_TIMEOUT=60000
HEALTH_CHECK_TIMEOUT=120000
EOF
    log_info "✓ 配置文件已创建: $ENV_FILE"
else
    log_info "✓ 配置文件已存在: $ENV_FILE"
fi

# 加载环境变量
set -a
source "$ENV_FILE"
set +a

# 步骤 3: 停止并清理旧容器
log_info "步骤 3/6: 清理旧容器..."

cd "$PROJECT_ROOT"
if docker compose -f "$COMPOSE_FILE" ps | grep -q "Up"; then
    log_info "停止现有容器..."
    docker compose -f "$COMPOSE_FILE" -p onedata-test down -v
    log_info "✓ 旧容器已停止"
else
    log_info "✓ 无需清理"
fi

# 步骤 4: 启动所有服务
log_info "步骤 4/6: 启动测试服务..."

# 导出环境变量供 docker-compose 使用
export MYSQL_ROOT_PASSWORD MYSQL_DATABASE MYSQL_USER MYSQL_PASSWORD
export REDIS_PASSWORD MINIO_ROOT_USER MINIO_ROOT_PASSWORD
export KEYCLOAK_ADMIN KEYCLOAK_ADMIN_PASSWORD

log_info "启动 Docker Compose 服务..."
docker compose -f "$COMPOSE_FILE" -p onedata-test up -d

log_info "✓ 服务启动命令已执行"

# 步骤 5: 等待服务健康检查
log_info "步骤 5/6: 等待服务健康检查..."

# 等待 MySQL
log_info "等待 MySQL 启动..."
timeout=60
elapsed=0
while [ $elapsed -lt $timeout ]; do
    if docker exec onedata-test-mysql mysqladmin ping -h localhost -u root -p${MYSQL_ROOT_PASSWORD} &> /dev/null; then
        log_info "✓ MySQL 已就绪"
        break
    fi
    sleep 2
    elapsed=$((elapsed + 2))
done
if [ $elapsed -ge $timeout ]; then
    log_error "MySQL 启动超时"
    exit 1
fi

# 等待 Redis
log_info "等待 Redis 启动..."
timeout=30
elapsed=0
while [ $elapsed -lt $timeout ]; do
    if docker exec onedata-test-redis redis-cli -a ${REDIS_PASSWORD} ping &> /dev/null; then
        log_info "✓ Redis 已就绪"
        break
    fi
    sleep 1
    elapsed=$((elapsed + 1))
done

# 等待 MinIO
log_info "等待 MinIO 启动..."
timeout=30
elapsed=0
while [ $elapsed -lt $timeout ]; do
    if curl -sf http://localhost:9001/minio/health/live &> /dev/null; then
        log_info "✓ MinIO 已就绪"
        break
    fi
    sleep 2
    elapsed=$((elapsed + 2))
done

# 等待 Keycloak
log_info "等待 Keycloak 启动..."
timeout=120
elapsed=0
while [ $elapsed -lt $timeout ]; do
    if curl -sf http://localhost:8080/health/ready &> /dev/null; then
        log_info "✓ Keycloak 已就绪"
        break
    fi
    sleep 3
    elapsed=$((elapsed + 3))
done

# 等待 API 服务
log_info "等待 API 服务启动..."

# Agent API
timeout=60
elapsed=0
while [ $elapsed -lt $timeout ]; do
    if curl -sf http://localhost:8000/api/v1/health &> /dev/null; then
        log_info "✓ Agent API 已就绪"
        break
    fi
    sleep 2
    elapsed=$((elapsed + 2))
done

# Data API
timeout=60
elapsed=0
while [ $elapsed -lt $timeout ]; do
    if curl -sf http://localhost:8001/api/v1/health &> /dev/null; then
        log_info "✓ Data API 已就绪"
        break
    fi
    sleep 2
    elapsed=$((elapsed + 2))
done

# Model API
timeout=60
elapsed=0
while [ $elapsed -lt $timeout ]; do
    if curl -sf http://localhost:8002/api/v1/health &> /dev/null; then
        log_info "✓ Model API 已就绪"
        break
    fi
    sleep 2
    elapsed=$((elapsed + 2))
done

# OpenAI Proxy
timeout=60
elapsed=0
while [ $elapsed -lt $timeout ]; do
    if curl -sf http://localhost:8003/health &> /dev/null; then
        log_info "✓ OpenAI Proxy 已就绪"
        break
    fi
    sleep 2
    elapsed=$((elapsed + 2))
done

# 步骤 6: 初始化测试数据
log_info "步骤 6/6: 初始化测试数据..."

if [ -f "$SCRIPT_DIR/setup/seed-data.py" ]; then
    log_info "运行测试数据初始化脚本..."
    python3 "$SCRIPT_DIR/setup/seed-data.py" || log_warn "测试数据初始化失败，但不影响测试运行"
else
    log_warn "未找到测试数据初始化脚本，跳过"
fi

# 输出测试环境访问地址
log_info ""
log_info "======================================"
log_info "测试环境启动完成！"
log_info "======================================"
log_info ""
log_info "服务访问地址："
log_info "  - 前端应用:     http://localhost:3000"
log_info "  - Agent API:    http://localhost:8000"
log_info "  - Data API:     http://localhost:8001"
log_info "  - Model API:    http://localhost:8002"
log_info "  - OpenAI Proxy: http://localhost:8003"
log_info "  - Keycloak:     http://localhost:8080"
log_info "  - MinIO 控制台: http://localhost:9001"
log_info ""
log_info "测试用户凭证："
log_info "  - 管理员: admin / admin"
log_info "  - 测试用户: testuser / Test1234!"
log_info ""
log_info "运行测试："
log_info "  cd $SCRIPT_DIR"
log_info "  ./run-acceptance.sh"
log_info ""
log_info "查看日志："
log_info "  docker compose -f $COMPOSE_FILE -p onedata-test logs -f"
log_info ""
log_info "停止环境："
log_info "  docker compose -f $COMPOSE_FILE -p onedata-test down -v"
log_info ""
