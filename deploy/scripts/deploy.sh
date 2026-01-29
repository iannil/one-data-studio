#!/bin/bash
# ONE-DATA-STUDIO 统一部署脚本
# Sprint 10: 部署自动化
#
# 使用方法:
#   ./deploy/scripts/deploy.sh [environment]
#
# 环境参数:
#   dev     - 开发环境 (默认)
#   staging - 预发布环境
#   prod    - 生产环境

set -e

# ==================== 配置 ====================

# 获取环境参数
ENVIRONMENT=${1:-dev}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# 环境配置
declare -A ENV_CONFIG=(
    [dev]="docker-compose-dev.yml"
    [staging]="docker-compose-staging.yml"
    [prod]="docker-compose-prod.yml"
)

declare -A COMPOSE_FILES=(
    [dev]="dev"
    [staging]="staging"
    [prod]="prod"
)

# ==================== 健康检查函数 ====================

health_check() {
    local service_name=$1
    local url=$2
    local max_wait=${3:-60}
    local count=0

    log_step "检查 $service_name 健康状态..."

    while [ $count -lt $max_wait ]; do
        if curl -sf "$url/health" > /dev/null 2>&1 || \
           curl -sf "$url/api/v1/health" > /dev/null 2>&1 || \
           curl -sf "$url" > /dev/null 2>&1; then
            log_info "✓ $service_name 健康检查通过"
            return 0
        fi
        ((count++))
        sleep 2
    done

    log_error "✗ $service_name 健康检查失败（等待 ${max_wait} 秒后超时）"
    return 1
}

wait_for_service() {
    local service=$1
    local max_wait=${2:-120}

    log_step "等待服务 $service 启动..."

    if docker-compose -f "$COMPOSE_FILE" ps -q "$service" | grep -q .; then
        # 等待容器变为 healthy
        local count=0
        while [ $count -lt $max_wait ]; do
            status=$(docker inspect --format='{{.State.Health.Status}}' \
                "$(docker-compose -f "$COMPOSE_FILE" ps -q "$service")" 2>/dev/null || echo "starting")

            if [ "$status" = "healthy" ]; then
                log_info "✓ $service 已就绪"
                return 0
            fi

            if [ "$status" = "unhealthy" ]; then
                log_error "✗ $service 状态异常"
                return 1
            fi

            ((count++))
            sleep 3
        done

        log_warn "$service 健康检查超时，但继续部署"
    fi
}

# ==================== 部署前检查 ====================

pre_deploy_check() {
    log_step "执行部署前检查..."

    # 检查 Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker 未安装"
        exit 1
    fi

    # 检查 Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "Docker Compose 未安装"
        exit 1
    fi

    # 检查环境配置文件
    if [ ! -f "$PROJECT_ROOT/deploy/.env.$ENVIRONMENT" ]; then
        log_warn "环境配置文件不存在: deploy/.env.$ENVIRONMENT"
        if [ -f "$PROJECT_ROOT/deploy/.env.example" ]; then
            log_info "从示例配置创建配置文件..."
            cp "$PROJECT_ROOT/deploy/.env.example" "$PROJECT_ROOT/deploy/.env.$ENVIRONMENT"
            log_warn "请编辑 deploy/.env.$ENVIRONMENT 配置后再运行部署"
            exit 1
        fi
    fi

    # 检查是否有未提交的更改
    if [ -d "$PROJECT_ROOT/.git" ]; then
        if ! git diff-index --quiet HEAD -- 2>/dev/null; then
            log_warn "存在未提交的更改"
            read -p "是否继续部署? (y/N): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                exit 1
            fi
        fi
    fi

    log_info "✓ 部署前检查完成"
}

# ==================== 构建镜像 ====================

build_images() {
    log_step "构建 Docker 镜像..."

    cd "$PROJECT_ROOT"

    # 构建前端
    log_info "构建前端镜像..."
    docker-compose -f "$COMPOSE_FILE" build web

    # 构建后端服务
    log_info "构建后端镜像..."
    docker-compose -f "$COMPOSE_FILE" build data-api agent-api

    log_info "✓ 镜像构建完成"
}

# ==================== 启动服务 ====================

start_services() {
    log_step "启动服务..."

    cd "$PROJECT_ROOT/deploy"

    # 根据环境选择 compose 文件
    local compose_files="-f docker-compose.yml"
    if [ -f "docker-compose-${ENVIRONMENT}.yml" ]; then
        compose_files="$compose_files -f docker-compose-${ENVIRONMENT}.yml"
    fi

    # 停止现有容器
    log_info "停止现有容器..."
    docker-compose $compose_files down --remove-orphans 2>/dev/null || true

    # 创建数据卷
    log_info "创建数据卷..."
    docker volume create one-data-mysql-data 2>/dev/null || true
    docker volume create one-data-redis-data 2>/dev/null || true
    docker volume create one-data-minio-data 2>/dev/null || true

    # 启动服务
    log_info "启动服务..."
    docker-compose $compose_files up -d

    # 等待数据库启动
    log_info "等待数据库启动..."
    sleep 10

    # 运行数据库迁移
    log_info "运行数据库迁移..."
    docker-compose $compose_files exec -T data-api \
        python -c "from models import Base; from database import engine; Base.metadata.create_all(engine)" 2>/dev/null || true

    docker-compose $compose_files exec -T agent-api \
        python -c "from models import Base; from database import engine; Base.metadata.create_all(engine)" 2>/dev/null || true

    log_info "✓ 服务启动完成"
}

# ==================== 健康检查 ====================

post_deploy_check() {
    log_step "执行部署后健康检查..."

    local base_url="http://localhost"
    local checks=()

    case $ENVIRONMENT in
        dev)
            checks+=("Alldata API:${base_url}:8080/api/v1/health")
            checks+=("Bisheng API:${base_url}:8081/api/v1/health")
            checks+=("Web UI:${base_url}:3000")
            ;;
        staging|prod)
            checks+=("Alldata API:${base_url}:8080/api/v1/health")
            checks+=("Bisheng API:${base_url}:8081/api/v1/health")
            checks+=("Web UI:${base_url}:3000")
            ;;
    esac

    for check in "${checks[@]}"; do
        IFS=':' read -r name url <<< "$check"
        health_check "$name" "$url"
    done
}

# ==================== 主函数 ====================

main() {
    echo ""
    echo "========================================"
    echo "ONE-DATA-STUDIO 部署脚本"
    echo "========================================"
    echo "环境: $ENVIRONMENT"
    echo "项目目录: $PROJECT_ROOT"
    echo "========================================"
    echo ""

    # 部署流程
    pre_deploy_check
    build_images
    start_services
    post_deploy_check

    echo ""
    echo "========================================"
    echo "部署完成"
    echo "========================================"
    echo ""
    echo "服务访问地址:"
    echo "  Web UI:      http://localhost:3000"
    echo "  Alldata API: http://localhost:8080"
    echo "  Bisheng API: http://localhost:8081"
    echo "  Prometheus:  http://localhost:9090"
    echo "  Grafana:     http://localhost:3001"
    echo ""
    echo "查看日志:"
    echo "  docker-compose logs -f [service]"
    echo ""
}

# 设置全局变量
COMPOSE_FILE="$PROJECT_ROOT/deploy/docker-compose-${COMPOSE_FILES[$ENVIRONMENT]}.yml"

# 如果指定的 compose 文件不存在，使用默认的
if [ ! -f "$COMPOSE_FILE" ]; then
    COMPOSE_FILE="$PROJECT_ROOT/deploy/docker-compose.yml"
fi

# 执行主函数
main "$@"
