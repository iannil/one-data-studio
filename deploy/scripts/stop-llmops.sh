#!/bin/bash
# ONE-DATA-STUDIO LLMOps Stage Stop Script
#
# This script stops the LLMOps stage services
#
# Usage:
#   ./deploy/scripts/stop-llmops.sh [options]
#
# Options:
#   --all              Stop all services including infrastructure
#   --remove-volumes   Remove all volumes (WARNING: deletes data)
#   --force            Force stop without confirmation
#   -v, --verbose      Enable verbose output
#   --help             Show this help message

set -e

# ==================== Configuration ====================
STAGE="llmops"
COMPOSE_FILE="deploy/local/docker-compose.llmops.yml"
SHARED_COMPOSE_FILE="deploy/local/docker-compose.shared.yml"

# Source common functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common-functions.sh"

# Parse command line arguments
STOP_ALL=false
REMOVE_VOLUMES=false
FORCE=false
VERBOSE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --all)
            STOP_ALL=true
            shift
            ;;
        --remove-volumes)
            REMOVE_VOLUMES=true
            shift
            ;;
        --force)
            FORCE=true
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
            echo "  --all              Stop all services including infrastructure"
            echo "  --remove-volumes   Remove all volumes (WARNING: deletes data)"
            echo "  --force            Force stop without confirmation"
            echo "  -v, --verbose      Enable verbose output"
            echo "  --help             Show this help message"
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
print_banner "LLMOps" "Stopping Services"

PROJECT_ROOT="$(get_project_root)"
LOCAL_DEPLOY_DIR="${PROJECT_ROOT}/deploy/local"

cd "$PROJECT_ROOT"

DOCKER_COMPOSE_CMD=$(get_docker_compose_cmd)

# ==================== Stop Services ====================
log_step "停止 LLMOps 阶段服务..."

# Confirm unless force
if [ "$FORCE" = "false" ] && [ "$REMOVE_VOLUMES" = "true" ]; then
    log_warn "警告: --remove-volumes 将删除所有数据！"
    read -p "确认删除所有数据卷? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "取消操作"
        exit 0
    fi
fi

# Stop LLMOps services
log_info "停止 LLMOps 服务..."

LLMOPS_CONTAINERS=(
    "one-data-agent-api-llmops"
    "one-data-data-api-llmops"
    "one-data-model-api-llmops"
    "one-data-openai-proxy-llmops"
    "one-data-admin-api-llmops"
    "one-data-web-llmops"
    "one-data-keycloak-llmops"
    "one-data-milvus-llmops"
    "one-data-etcd-llmops"
)

for container in "${LLMOPS_CONTAINERS[@]}"; do
    if docker ps -q -f name="$container" | grep -q .; then
        log_info "停止 $container..."
        docker stop "$container" 2>/dev/null || true
    fi
done

# Stop using compose
if [ -f "$LOCAL_DEPLOY_DIR/$COMPOSE_FILE" ]; then
    if [ "$REMOVE_VOLUMES" = "true" ]; then
        $DOCKER_COMPOSE_CMD -f "$LOCAL_DEPLOY_DIR/docker-compose.yml" \
                            -f "$COMPOSE_FILE" \
                            --profile llmops \
                            down -v 2>/dev/null || true
    else
        $DOCKER_COMPOSE_CMD -f "$LOCAL_DEPLOY_DIR/docker-compose.yml" \
                            -f "$COMPOSE_FILE" \
                            --profile llmops \
                            down 2>/dev/null || true
    fi
fi

# Stop infrastructure if requested
if [ "$STOP_ALL" = "true" ]; then
    log_info "停止共享基础设施..."

    SHARED_CONTAINERS=(
        "one-data-mysql"
        "one-data-redis"
        "one-data-minio"
    )

    for container in "${SHARED_CONTAINERS[@]}"; do
        if docker ps -q -f name="$container" | grep -q .; then
            log_info "停止 $container..."
            docker stop "$container" 2>/dev/null || true
        fi
    done

    if [ -f "$LOCAL_DEPLOY_DIR/$SHARED_COMPOSE_FILE" ]; then
        if [ "$REMOVE_VOLUMES" = "true" ]; then
            $DOCKER_COMPOSE_CMD -f "$SHARED_COMPOSE_FILE" down -v 2>/dev/null || true
        else
            $DOCKER_COMPOSE_CMD -f "$SHARED_COMPOSE_FILE" down 2>/dev/null || true
        fi
    fi
fi

# Clean up stopped containers
remove_stopped_containers

# ==================== Summary ====================
echo ""
echo "========================================"
echo "LLMOps 服务已停止"
echo "========================================"
echo ""
echo "管理命令:"
echo "  重新启动: ./deploy/scripts/start-llmops.sh"
echo "  查看状态: ./deploy/scripts/status-llmops.sh"
echo ""

if [ "$REMOVE_VOLUMES" = "false" ]; then
    echo "数据卷已保留，重新启动后将恢复之前的数据"
else
    log_warn "数据卷已删除，下次启动将是全新环境"
    echo "注意: 向量数据库数据已删除，需要重新构建索引"
fi
echo ""

log_success "LLMOps 阶段停止完成！"
