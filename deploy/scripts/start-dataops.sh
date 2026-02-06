#!/bin/bash
# ONE-DATA-STUDIO DataOps Stage Startup Script
#
# This script starts the DataOps stage services including:
# - Infrastructure: MySQL, Redis, MinIO, Milvus, Elasticsearch
# - Metadata: OpenMetadata
# - ETL: Kettle
# - Workflow: DolphinScheduler
# - BI: Superset
# - API: data-api
# - Auth: Keycloak
#
# Usage:
#   ./deploy/scripts/start-dataops.sh [options]
#
# Options:
#   --no-infrastructure  Skip starting shared infrastructure
#   --no-ai             Skip AI-dependent services
#   --dry-run           Show what would be started without starting
#   -v, --verbose       Enable verbose output
#   --help              Show this help message

set -e

# ==================== Configuration ====================
STAGE="dataops"
STAGE_PREFIX="81xx"
COMPOSE_FILE="deploy/local/docker-compose.dataops.yml"
SHARED_COMPOSE_FILE="deploy/local/docker-compose.shared.yml"

# Source common functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common-functions.sh"

# Parse command line arguments
SKIP_INFRASTRUCTURE=false
SKIP_AI=false
DRY_RUN=false
VERBOSE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --no-infrastructure)
            SKIP_INFRASTRUCTURE=true
            shift
            ;;
        --no-ai)
            SKIP_AI=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            set -x
            shift
            ;;
        --help)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --no-infrastructure  Skip starting shared infrastructure (mysql, redis, minio)"
            echo "  --no-ai             Skip AI-dependent services"
            echo "  --dry-run           Show what would be started without starting"
            echo "  -v, --verbose       Enable verbose output"
            echo "  --help              Show this help message"
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# ==================== Pre-flight Checks ====================
print_banner "DataOps" "Data Governance and ETL Platform"

PROJECT_ROOT="$(get_project_root)"
DEPLOY_DIR="${PROJECT_ROOT}/deploy"
LOCAL_DEPLOY_DIR="${PROJECT_ROOT}/deploy/local"

# Change to deploy directory
cd "$PROJECT_ROOT"

# Check Docker
if ! check_docker; then
    exit 1
fi

DOCKER_COMPOSE_CMD=$(get_docker_compose_cmd)
log_info "Using: $DOCKER_COMPOSE_CMD"

# Check environment variables
ENV_FILE="${LOCAL_DEPLOY_DIR}/.env"
if [ -f "$ENV_FILE" ]; then
    load_env_file "$ENV_FILE"
else
    if [ -f "${LOCAL_DEPLOY_DIR}/.env.example" ]; then
        log_warn ".env file not found, using .env.example"
        cp "${LOCAL_DEPLOY_DIR}/.env.example" "$ENV_FILE"
        load_env_file "$ENV_FILE"
        log_warn "Please edit $ENV_FILE with your actual values"
    fi
fi

# Required environment variables for DataOps
REQUIRED_VARS=(
    "MYSQL_ROOT_PASSWORD"
    "MYSQL_PASSWORD"
    "REDIS_PASSWORD"
    "MINIO_ROOT_USER"
    "MINIO_ROOT_PASSWORD"
    "KETTLE_CARTE_PASSWORD"
    "SUPERSET_SECRET_KEY"
)

if ! check_required_env_vars "${REQUIRED_VARS[@]}"; then
    log_error "请设置所有必需的环境变量后再运行"
    exit 1
fi

# Check port availability
log_step "检查端口占用情况..."
PORTS_TO_CHECK=("3306" "6379" "9000" "9200" "8585" "8180" "8188" "8101" "8123")
BLOCKED_PORTS=()

for port in "${PORTS_TO_CHECK[@]}"; do
    if ! check_port_available "$port"; then
        BLOCKED_PORTS+=("$port")
    fi
done

if [ ${#BLOCKED_PORTS[@]} -gt 0 ]; then
    log_warn "以下端口已被占用: ${BLOCKED_PORTS[*]}"
    read -p "是否继续启动? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "取消启动"
        exit 0
    fi
fi

# ==================== Start Services ====================
log_step "启动 DataOps 阶段服务..."

if [ "$DRY_RUN" = "true" ]; then
    echo ""
    echo "=== Dry Run Mode ==="
    echo "将启动以下服务:"
    echo ""
    echo "共享基础设施:"
    [ "$SKIP_INFRASTRUCTURE" = "false" ] && echo "  - MySQL (:3306)"
    [ "$SKIP_INFRASTRUCTURE" = "false" ] && echo "  - Redis (:6379)"
    [ "$SKIP_INFRASTRUCTURE" = "false" ] && echo "  - MinIO (:9000)"
    echo ""
    echo "DataOps 服务:"
    echo "  - Milvus (:19530)"
    echo "  - Elasticsearch (:9200)"
    echo "  - OpenMetadata (:8585)"
    echo "  - Kettle (:8180, :8181)"
    echo "  - Keycloak (:8180)"
    echo "  - DolphinScheduler (:8123, :8133, :8134, :8152)"
    echo "  - Superset (:8188)"
    echo "  - data-api (:8101)"
    echo ""
    echo "命令:"
    echo "  $DOCKER_COMPOSE_CMD -f $COMPOSE_FILE --profile dataops up -d"
    echo ""
    exit 0
fi

# Start shared infrastructure
if [ "$SKIP_INFRASTRUCTURE" = "false" ]; then
    log_step "启动共享基础设施..."

    # Check if already running
    if check_container_running "one-data-mysql"; then
        log_info "MySQL 已在运行，跳过启动"
    else
        log_info "启动 MySQL..."
        $DOCKER_COMPOSE_CMD -f "$SHARED_COMPOSE_FILE" up -d mysql
    fi

    if check_container_running "one-data-redis"; then
        log_info "Redis 已在运行，跳过启动"
    else
        log_info "启动 Redis..."
        $DOCKER_COMPOSE_CMD -f "$SHARED_COMPOSE_FILE" up -d redis
    fi

    if check_container_running "one-data-minio"; then
        log_info "MinIO 已在运行，跳过启动"
    else
        log_info "启动 MinIO..."
        $DOCKER_COMPOSE_CMD -f "$SHARED_COMPOSE_FILE" up -d minio
    fi

    # Wait for infrastructure
    log_info "等待基础设施启动..."
    sleep 10
fi

# Start DataOps services
log_info "启动 DataOps 核心服务..."

# Start in order: database -> metadata -> etl -> bi -> api
SERVICES_START_ORDER=(
    "etcd"
    "elasticsearch"
    "milvus"
    "zookeeper"
    "dolphinscheduler-postgresql"
    "dolphinscheduler-api"
    "superset-cache"
    "kettle"
    "keycloak"
    "openmetadata"
    "superset"
    "data-api"
)

for service in "${SERVICES_START_ORDER[@]}"; do
    log_info "启动 $service..."
    $DOCKER_COMPOSE_CMD -f "$LOCAL_DEPLOY_DIR/docker-compose.yml" \
                        -f "$COMPOSE_FILE" \
                        --profile dataops \
                        up -d "$service" 2>/dev/null || \
    $DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" \
                        --profile dataops \
                        up -d "$service"
done

# ==================== Health Checks ====================
log_step "等待服务就绪..."

# Wait for MySQL
if [ "$SKIP_INFRASTRUCTURE" = "false" ]; then
    wait_for_container_health "one-data-mysql" 60 || log_warn "MySQL 健康检查超时"
fi

# Wait for Elasticsearch
wait_for_container_health "one-data-elasticsearch-dataops" 120 || log_warn "Elasticsearch 健康检查超时"

# Wait for OpenMetadata (long startup time)
log_info "等待 OpenMetadata 启动（可能需要 2-3 分钟）..."
if health_check_http "OpenMetadata" "http://localhost:8585/api/v1/system/version" 180; then
    log_success "OpenMetadata 已就绪"
else
    log_warn "OpenMetadata 未就绪，请检查日志"
fi

# Wait for Kettle
if health_check_http "Kettle" "http://localhost:8180/spoon/spoon" 120; then
    log_success "Kettle 已就绪"
else
    log_warn "Kettle 未就绪"
fi

# Wait for data-api
if health_check_http "data-api" "http://localhost:8101/api/v1/health" 60; then
    log_success "data-api 已就绪"
else
    log_warn "data-api 未就绪"
fi

# Wait for Superset (long startup time)
log_info "等待 Superset 启动（可能需要 2-3 分钟）..."
if health_check_http "Superset" "http://localhost:8188/health" 180; then
    log_success "Superset 已就绪"
else
    log_warn "Superset 未就绪"
fi

# ==================== Print Summary ====================
print_stage_info "DataOps" "$STAGE_PREFIX"

echo "服务访问地址:"
print_service_status "MySQL" "one-data-mysql" "3306" ""
print_service_status "Redis" "one-data-redis" "6379" ""
print_service_status "MinIO Console" "one-data-minio" "9001" "/minio"
print_service_status "OpenMetadata" "one-data-openmetadata-dataops" "8585" ""
print_service_status "Kettle UI" "one-data-kettle-dataops" "8180" "/spoon"
print_service_status "Keycloak" "one-data-keycloak-dataops" "8180" ""
print_service_status "DolphinScheduler" "one-data-dolphinscheduler-dataops" "8123" ""
print_service_status "Superset" "one-data-superset-dataops" "8188" ""
print_service_status "data-api" "one-data-data-api-dataops" "8101" "/api/v1/health"

echo ""
echo "========================================"
echo "测试命令:"
echo "========================================"
echo "# 检查 OpenMetadata"
echo "curl http://localhost:8585/api/v1/system/version"
echo ""
echo "# 检查 data-api"
echo "curl http://localhost:8101/api/v1/health"
echo ""
echo "# 检查 Superset"
echo "curl http://localhost:8188/health"
echo ""
echo "# 查看日志"
echo "$DOCKER_COMPOSE_CMD -f $COMPOSE_FILE --profile dataops logs -f [service]"
echo ""
echo "# 停止服务"
echo "./deploy/scripts/stop-dataops.sh"
echo ""
echo "# 查看状态"
echo "./deploy/scripts/status-dataops.sh"
echo ""

log_success "DataOps 阶段启动完成！"
