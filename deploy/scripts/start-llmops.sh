#!/bin/bash
# ONE-DATA-STUDIO LLMOps Stage Startup Script
#
# This script starts the LLMOps stage services including:
# - Infrastructure: MySQL, Redis, MinIO, Milvus (shared)
# - Agent Orchestration: agent-api
# - Data Governance: data-api
# - OpenAI Proxy: openai-proxy
# - Admin API: admin-api
# - Model API: model-api
# - Web Frontend: web-frontend
# - Auth: Keycloak
#
# Usage:
#   ./deploy/scripts/start-llmops.sh [options]
#
# Options:
#   --no-infrastructure  Skip starting shared infrastructure
#   --no-vector         Skip starting vector database (Milvus)
#   --dry-run           Show what would be started without starting
#   -v, --verbose       Enable verbose output
#   --help              Show this help message

set -e

# ==================== Configuration ====================
STAGE="llmops"
STAGE_PREFIX="83xx"
COMPOSE_FILE="deploy/local/docker-compose.llmops.yml"
SHARED_COMPOSE_FILE="deploy/local/docker-compose.shared.yml"

# Source common functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common-functions.sh"

# Parse command line arguments
SKIP_INFRASTRUCTURE=false
SKIP_VECTOR=false
DRY_RUN=false
VERBOSE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --no-infrastructure)
            SKIP_INFRASTRUCTURE=true
            shift
            ;;
        --no-vector)
            SKIP_VECTOR=true
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
            echo "  --no-vector         Skip starting vector database (milvus)"
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
print_banner "LLMOps" "Agent Orchestration and Application Platform"

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

# Required environment variables for LLMOps
REQUIRED_VARS=(
    "MYSQL_ROOT_PASSWORD"
    "MYSQL_PASSWORD"
    "REDIS_PASSWORD"
    "MINIO_ROOT_USER"
    "MINIO_ROOT_PASSWORD"
)

if ! check_required_env_vars "${REQUIRED_VARS[@]}"; then
    log_error "请设置所有必需的环境变量后再运行"
    exit 1
fi

# Check port availability
log_step "检查端口占用情况..."
PORTS_TO_CHECK=("3306" "6379" "9000" "19530" "8300" "8301" "8302" "8303" "8304" "8305" "8380")
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
log_step "启动 LLMOps 阶段服务..."

if [ "$DRY_RUN" = "true" ]; then
    echo ""
    echo "=== Dry Run Mode ==="
    echo "将启动以下服务:"
    echo ""
    echo "共享基础设施:"
    [ "$SKIP_INFRASTRUCTURE" = "false" ] && echo "  - MySQL (:3306)"
    [ "$SKIP_INFRASTRUCTURE" = "false" ] && echo "  - Redis (:6379)"
    [ "$SKIP_INFRASTRUCTURE" = "false" ] && echo "  - MinIO (:9000)"
    [ "$SKIP_VECTOR" = "false" ] && echo "  - Milvus (:19530)"
    echo ""
    echo "LLMOps 服务:"
    echo "  - agent-api (:8300)"
    echo "  - data-api (:8301)"
    echo "  - model-api (:8302)"
    echo "  - openai-proxy (:8303)"
    echo "  - admin-api (:8304)"
    echo "  - web-frontend (:8305)"
    echo "  - Keycloak (:8380)"
    echo ""
    echo "命令:"
    echo "  $DOCKER_COMPOSE_CMD -f $COMPOSE_FILE --profile llmops up -d"
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

# Start vector database
if [ "$SKIP_VECTOR" = "false" ]; then
    log_info "启动 Milvus 向量数据库..."

    $DOCKER_COMPOSE_CMD -f "$LOCAL_DEPLOY_DIR/docker-compose.yml" \
                        -f "$COMPOSE_FILE" \
                        --profile llmops \
                        up -d etcd milvus

    log_info "等待 Milvus 启动..."
    sleep 15
fi

# Start LLMOps services
log_info "启动 LLMOps 核心服务..."

# Start in order: apis -> frontend
SERVICES_START_ORDER=(
    "model-api"
    "admin-api"
    "openai-proxy"
    "data-api"
    "agent-api"
    "keycloak"
    "web-frontend"
)

for service in "${SERVICES_START_ORDER[@]}"; do
    log_info "启动 $service..."
    $DOCKER_COMPOSE_CMD -f "$LOCAL_DEPLOY_DIR/docker-compose.yml" \
                        -f "$COMPOSE_FILE" \
                        --profile llmops \
                        up -d "$service" 2>/dev/null || \
    $DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" \
                        --profile llmops \
                        up -d "$service"
done

# ==================== Health Checks ====================
log_step "等待服务就绪..."

# Wait for MySQL
if [ "$SKIP_INFRASTRUCTURE" = "false" ]; then
    wait_for_container_health "one-data-mysql" 60 || log_warn "MySQL 健康检查超时"
fi

# Wait for Milvus
if [ "$SKIP_VECTOR" = "false" ]; then
    log_info "等待 Milvus 启动..."
    if health_check_http "Milvus" "http://localhost:19530/healthz" 60; then
        log_success "Milvus 已就绪"
    else
        log_warn "Milvus 未就绪"
    fi
fi

# Wait for APIs
for api_service in "model-api:8302/api/v1/health" "admin-api:8304/api/v1/health" "openai-proxy:8303/health" "data-api:8301/api/v1/health" "agent-api:8300/api/v1/health"; do
    IFS=':' read -r name port endpoint <<< "$api_service"
    if health_check_http "$name" "http://localhost:$port$endpoint" 60; then
        log_success "$name 已就绪"
    else
        log_warn "$name 未就绪"
    fi
done

# Wait for frontend
log_info "等待前端启动..."
if health_check_http "web-frontend" "http://localhost:8305" 60; then
    log_success "web-frontend 已就绪"
else
    log_warn "web-frontend 未就绪"
fi

# ==================== Print Summary ====================
print_stage_info "LLMOps" "$STAGE_PREFIX"

echo "服务访问地址:"
print_service_status "MySQL" "one-data-mysql" "3306" ""
print_service_status "Redis" "one-data-redis" "6379" ""
print_service_status "MinIO Console" "one-data-minio" "9001" "/minio"
print_service_status "Milvus" "one-data-milvus-llmops" "19530" ""
print_service_status "agent-api" "one-data-agent-api-llmops" "8300" "/api/v1/health"
print_service_status "data-api" "one-data-data-api-llmops" "8301" "/api/v1/health"
print_service_status "model-api" "one-data-model-api-llmops" "8302" "/api/v1/health"
print_service_status "openai-proxy" "one-data-openai-proxy-llmops" "8303" "/health"
print_service_status "admin-api" "one-data-admin-api-llmops" "8304" "/api/v1/health"
print_service_status "Web Frontend" "one-data-web-llmops" "8305" ""
print_service_status "Keycloak" "one-data-keycloak-llmops" "8380" ""

echo ""
echo "========================================"
echo "测试命令:"
echo "========================================"
echo "# 检查 agent-api"
echo "curl http://localhost:8300/api/v1/health"
echo ""
echo "# 检查 openai-proxy"
echo "curl http://localhost:8303/health"
echo ""
echo "# 测试聊天接口（需要后端服务就绪）"
echo "curl -X POST http://localhost:8300/api/v1/chat/completions \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{\"messages\": [{\"role\": \"user\", \"content\": \"Hello\"}]}'"
echo ""
echo "# 查看日志"
echo "$DOCKER_COMPOSE_CMD -f $COMPOSE_FILE --profile llmops logs -f [service]"
echo ""
echo "# 停止服务"
echo "./deploy/scripts/stop-llmops.sh"
echo ""
echo "# 查看状态"
echo "./deploy/scripts/status-llmops.sh"
echo ""

log_success "LLMOps 阶段启动完成！"
