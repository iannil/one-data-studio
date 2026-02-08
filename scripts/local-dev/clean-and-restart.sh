#!/bin/bash
# ONE-DATA-STUDIO 本地开发环境 - 清理并重启
#
# 此脚本执行完整的清理和重启流程：
# 1. 停止所有应用服务（本地）
# 2. 停止并删除所有 Docker 容器
# 3. 重新启动基础设施 Docker 服务
# 4. 启动所有应用服务
#
# 使用方法:
#   ./clean-and-restart.sh           # 完整清理并重启
#   ./clean-and-restart.sh --infra   # 仅清理基础设施
#   ./clean-and-restart.sh --apps    # 仅重启应用服务

set -e

# 加载共享函数
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

# ==================== 配置 ====================

INFRA_ONLY=false
APPS_ONLY=false

# ==================== 解析参数 ====================

while [[ $# -gt 0 ]]; do
    case $1 in
        --infra)
            INFRA_ONLY=true
            shift
            ;;
        --apps)
            APPS_ONLY=true
            shift
            ;;
        -h|--help)
            echo "用法: $0 [选项]"
            echo ""
            echo "选项:"
            echo "  --infra         仅清理并重启基础设施服务（Docker）"
            echo "  --apps          仅重启应用服务（本地）"
            echo "  -h, --help      显示帮助信息"
            echo ""
            echo "示例:"
            echo "  $0              # 完整清理并重启所有服务"
            echo "  $0 --infra      # 仅清理 Docker 容器并重启基础设施"
            echo "  $0 --apps       # 仅重启应用服务（不清理 Docker）"
            exit 0
            ;;
        *)
            log_error "未知选项: $1"
            exit 1
            ;;
    esac
done

# ==================== 函数 ====================

stop_all_apps() {
    print_header "步骤 1/4: 停止所有应用服务"
    "$SCRIPT_DIR/stop-all.sh" --apps-only
}

clean_docker() {
    print_header "步骤 2/4: 清理 Docker 容器"

    if ! check_docker; then
        log_error "Docker 不可用，跳过清理"
        return 1
    fi

    cd "$DEPLOY_DIR"

    # 停止并删除所有容器
    log_info "停止并删除所有容器..."
    docker-compose down --volumes --remove-orphans 2>/dev/null || true

    # 清理悬空镜像
    log_info "清理悬空镜像..."
    docker image prune -f 2>/dev/null || true

    log_success "Docker 容器已清理"
}

start_infrastructure() {
    print_header "步骤 3/4: 启动基础设施服务"

    if ! check_docker; then
        log_error "Docker 不可用，跳过基础设施启动"
        return 1
    fi

    "$SCRIPT_DIR/infrastructure.sh" start

    log_success "基础设施服务已启动"
}

start_all_apps() {
    print_header "步骤 4/4: 启动所有应用服务"
    "$SCRIPT_DIR/start-all.sh" --apps-only
}

print_summary() {
    print_header "清理并重启完成"

    echo -e "${BOLD}应用服务:${NC}"

    echo "  Web 前端:        http://localhost:$(get_service_port web)"
    echo "  Data API:        http://localhost:$(get_service_port data-api)/api/v1/health"
    echo "  Agent API:       http://localhost:$(get_service_port agent-api)/api/v1/health"
    echo "  Admin API:       http://localhost:$(get_service_port admin-api)/api/v1/health"
    echo "  Model API:       http://localhost:$(get_service_port model-api)/api/v1/health"
    echo "  OpenAI Proxy:    http://localhost:$(get_service_port openai-proxy)/health"
    echo "  OCR Service:     http://localhost:$(get_service_port ocr-service)/health"
    echo "  Behavior Service: http://localhost:$(get_service_port behavior-service)/health"

    echo ""
    echo -e "${BOLD}基础设施:${NC}"
    echo "  MySQL:           localhost:3306 (root/password)"
    echo "  Redis:           localhost:6379 (:password)"
    echo "  MinIO Console:   http://localhost:9001 (minioadmin/minioadmin)"
    echo "  Milvus:          localhost:19530"
    echo ""
    echo -e "${BOLD}常用命令:${NC}"
    echo "  查看所有状态:  ./status-all.sh"
    echo "  停止所有服务:  ./stop-all.sh"
    echo "  查看服务日志:  ./<service>.sh logs"
    echo ""
}

# ==================== 主函数 ====================

main() {
    if [ "$APPS_ONLY" = false ]; then
        stop_all_apps
        clean_docker
        start_infrastructure
    fi

    if [ "$INFRA_ONLY" = false ]; then
        start_all_apps
    fi

    if [ "$INFRA_ONLY" = false ]; then
        print_summary
    fi

    log_success "清理并重启完成"
}

main
