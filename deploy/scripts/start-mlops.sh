#!/bin/bash
# ONE-DATA-STUDIO MLOps Stage Startup Script
#
# This script starts the MLOps stage services including:
# - Infrastructure: MySQL, Redis, MinIO (shared)
# - Model Management: model-api
# - Data Labeling: Label Studio
# - AI Services: vLLM Chat, vLLM Embed, Ollama
# - OCR: ocr-service
# - Behavior Analysis: behavior-service
#
# Usage:
#   ./deploy/scripts/start-mlops.sh [options]
#
# Options:
#   --no-infrastructure  Skip starting shared infrastructure
#   --no-gpu            Start without GPU services (use CPU)
#   --dry-run           Show what would be started without starting
#   -v, --verbose       Enable verbose output
#   --help              Show this help message

set -e

# ==================== Configuration ====================
STAGE="mlops"
STAGE_PREFIX="82xx"
COMPOSE_FILE="deploy/local/docker-compose.mlops.yml"
SHARED_COMPOSE_FILE="deploy/local/docker-compose.shared.yml"

# Source common functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common-functions.sh"

# Parse command line arguments
SKIP_INFRASTRUCTURE=false
SKIP_GPU=false
DRY_RUN=false
VERBOSE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --no-infrastructure)
            SKIP_INFRASTRUCTURE=true
            shift
            ;;
        --no-gpu)
            SKIP_GPU=true
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
            echo "  --no-gpu            Start without GPU services (use CPU only)"
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
print_banner "MLOps" "Model Training and Deployment Platform"

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

# Required environment variables for MLOps
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

# Check for GPU
if [ "$SKIP_GPU" = "false" ]; then
    if command -v nvidia-smi &> /dev/null; then
        log_info "检测到 NVIDIA GPU"
        nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader 2>/dev/null || true
    else
        log_warn "未检测到 NVIDIA GPU，AI 服务将以 CPU 模式运行"
        log_warn "建议使用 Ollama 替代 vLLM 以获得更好的 CPU 性能"
    fi
fi

# Check port availability
log_step "检查端口占用情况..."
PORTS_TO_CHECK=("3306" "6379" "9000" "8202" "8209" "8210" "8211" "8134" "8207" "8208")
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
log_step "启动 MLOps 阶段服务..."

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
    echo "MLOps 服务:"
    echo "  - model-api (:8202)"
    echo "  - Label Studio (:8209)"
    echo "  - vLLM Chat (:8210)"
    echo "  - vLLM Embed (:8211)"
    echo "  - Ollama (:8134)"
    echo "  - OCR Service (:8207)"
    echo "  - Behavior Service (:8208)"
    echo ""
    echo "命令:"
    echo "  $DOCKER_COMPOSE_CMD -f $COMPOSE_FILE --profile mlops up -d"
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

# Start MLOps services
log_info "启动 MLOps 核心服务..."

# Start in order: database -> ml platform -> ai services -> extensions
SERVICES_START_ORDER=(
    "label-studio-postgresql"
    "label-studio"
    "model-api"
    "ollama"
    "vllm-chat"
    "vllm-embed"
    "ocr-service"
    "behavior-service"
)

for service in "${SERVICES_START_ORDER[@]}"; do
    # Skip vLLM services if no GPU and not explicitly enabled
    if [[ "$service" == vllm-* ]] && [ "$SKIP_GPU" = "true" ] && ! command -v nvidia-smi &> /dev/null; then
        log_info "跳过 $service (无 GPU)"
        continue
    fi

    log_info "启动 $service..."
    $DOCKER_COMPOSE_CMD -f "$LOCAL_DEPLOY_DIR/docker-compose.yml" \
                        -f "$COMPOSE_FILE" \
                        --profile mlops \
                        up -d "$service" 2>/dev/null || \
    $DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" \
                        --profile mlops \
                        up -d "$service"
done

# ==================== Health Checks ====================
log_step "等待服务就绪..."

# Wait for MySQL
if [ "$SKIP_INFRASTRUCTURE" = "false" ]; then
    wait_for_container_health "one-data-mysql" 60 || log_warn "MySQL 健康检查超时"
fi

# Wait for Label Studio
log_info "等待 Label Studio 启动..."
if health_check_http "Label Studio" "http://localhost:8209/health" 90; then
    log_success "Label Studio 已就绪"
else
    log_warn "Label Studio 未就绪"
fi

# Wait for model-api
if health_check_http "model-api" "http://localhost:8202/api/v1/health" 60; then
    log_success "model-api 已就绪"
else
    log_warn "model-api 未就绪"
fi

# Wait for Ollama
log_info "等待 Ollama 启动..."
if health_check_http "Ollama" "http://localhost:8134/api/tags" 60; then
    log_success "Ollama 已就绪"
else
    log_warn "Ollama 未就绪"
fi

# Wait for vLLM services (may take 3-5 minutes for model loading)
if [ "$SKIP_GPU" = "false" ] && command -v nvidia-smi &> /dev/null; then
    log_info "等待 vLLM Chat 启动（模型加载可能需要 3-5 分钟）..."
    log_warn "vLLM 服务加载大模型需要较长时间，请耐心等待"

    # Just warn, don't wait for full timeout in script
    if health_check_http "vLLM Chat" "http://localhost:8210/health" 300; then
        log_success "vLLM Chat 已就绪"
    else
        log_warn "vLLM Chat 未就绪，可能仍在加载模型"
        log_info "检查模型加载进度:"
        log_info "  docker logs one-data-vllm-chat-mlops -f"
    fi
fi

# Wait for OCR service
if health_check_http "OCR Service" "http://localhost:8207/health" 60; then
    log_success "OCR Service 已就绪"
else
    log_warn "OCR Service 未就绪"
fi

# Wait for Behavior service
if health_check_http "Behavior Service" "http://localhost:8208/health" 60; then
    log_success "Behavior Service 已就绪"
else
    log_warn "Behavior Service 未就绪"
fi

# ==================== Print Summary ====================
print_stage_info "MLOps" "$STAGE_PREFIX"

echo "服务访问地址:"
print_service_status "MySQL" "one-data-mysql" "3306" ""
print_service_status "Redis" "one-data-redis" "6379" ""
print_service_status "MinIO Console" "one-data-minio" "9001" "/minio"
print_service_status "model-api" "one-data-model-api-mlops" "8202" "/api/v1/health"
print_service_status "Label Studio" "one-data-label-studio-mlops" "8209" ""
print_service_status "vLLM Chat" "one-data-vllm-chat-mlops" "8210" "/health"
print_service_status "vLLM Embed" "one-data-vllm-embed-mlops" "8211" "/health"
print_service_status "Ollama" "one-data-ollama-mlops" "8134" "/api/tags"
print_service_status "OCR Service" "one-data-ocr-service-mlops" "8207" "/health"
print_service_status "Behavior Service" "one-data-behavior-service-mlops" "8208" "/health"

echo ""
echo "========================================"
echo "测试命令:"
echo "========================================"
echo "# 检查 model-api"
echo "curl http://localhost:8202/api/v1/health"
echo ""
echo "# 检查 Label Studio"
echo "curl http://localhost:8209/health"
echo ""
echo "# 测试 vLLM Chat (如果可用)"
echo "curl http://localhost:8210/v1/models"
echo ""
echo "# 测试 Ollama"
echo "curl http://localhost:8134/api/tags"
echo ""
echo "# 拉取 Ollama 模型"
echo "docker exec one-data-ollama-mlops ollama pull qwen2.5:1.5b"
echo ""
echo "# 查看日志"
echo "$DOCKER_COMPOSE_CMD -f $COMPOSE_FILE --profile mlops logs -f [service]"
echo ""
echo "# 停止服务"
echo "./deploy/scripts/stop-mlops.sh"
echo ""
echo "# 查看状态"
echo "./deploy/scripts/status-mlops.sh"
echo ""

log_success "MLOps 阶段启动完成！"
