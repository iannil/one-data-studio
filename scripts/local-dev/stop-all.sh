#!/bin/bash
# ONE-DATA-STUDIO 本地开发环境 - 停止所有服务
#
# 此脚本停止所有本地开发服务
#
# 使用方法:
#   ./stop-all.sh              # 停止所有服务
#   ./stop-all.sh --apps-only  # 仅停止应用服务
#   ./stop-all.sh --infra-only # 仅停止基础设施

set -e

# 加载共享函数
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

# ==================== 配置 ====================

APPS_ONLY=false
INFRA_ONLY=false

# ==================== 解析参数 ====================

while [[ $# -gt 0 ]]; do
    case $1 in
        --apps-only)
            APPS_ONLY=true
            shift
            ;;
        --infra-only)
            INFRA_ONLY=true
            shift
            ;;
        -h|--help)
            echo "用法: $0 [选项]"
            echo ""
            echo "选项:"
            echo "  --apps-only     仅停止应用服务（本地）"
            echo "  --infra-only    仅停止基础设施服务（Docker）"
            echo "  -h, --help      显示帮助信息"
            echo ""
            echo "示例:"
            echo "  $0              # 停止所有服务"
            echo "  $0 --apps-only  # 仅停止 Web 和 API 服务"
            echo "  $0 --infra-only # 仅停止 MySQL, Redis 等"
            exit 0
            ;;
        *)
            log_error "未知选项: $1"
            exit 1
            ;;
    esac
done

# ==================== 函数 ====================

stop_application_services() {
    print_header "停止应用服务"

    # 按相反顺序停止服务（依赖关系）
    local services=(
        "web:Web Frontend"
        "behavior-service:Behavior Service"
        "ocr-service:OCR Service"
        "openai-proxy:OpenAI Proxy"
        "model-api:Model API"
        "admin-api:Admin API"
        "agent-api:Agent API"
        "data-api:Data API"
    )

    local stopped=0
    local failed=0

    for item in "${services[@]}"; do
        IFS=':' read -r svc name <<< "$item"

        # 检查服务是否在运行
        if [ -f "$PID_DIR/$svc.pid" ]; then
            log_info "停止 $name..."
            if "$SCRIPT_DIR/$svc.sh" stop 2>/dev/null; then
                stopped=$((stopped + 1))
            else
                # 即使脚本失败，也尝试手动清理
                local pid=$(cat "$PID_DIR/$svc.pid" 2>/dev/null || echo "")
                if [ -n "$pid" ] && ps -p "$pid" > /dev/null 2>&1; then
                    kill "$pid" 2>/dev/null || true
                    rm -f "$PID_DIR/$svc.pid" 2>/dev/null || true
                    stopped=$((stopped + 1))
                else
                    failed=$((failed + 1))
                fi
            fi
        else
            # 服务未运行，跳过
            :
        fi
    done

    echo ""
    if [ $stopped -gt 0 ]; then
        log_success "应用服务已停止 ($stopped)"
    else
        log_info "没有运行的应用服务"
    fi

    if [ $failed -gt 0 ]; then
        log_warn "部分服务停止失败 ($failed)"
    fi
}

stop_infrastructure() {
    print_header "停止基础设施服务"

    if ! check_docker; then
        log_warn "Docker 不可用，跳过基础设施服务"
        return 0
    fi

    # 检查是否有 Docker 容器在运行
    local running_containers=$(docker ps --format "{{{{.Names}}}}" 2>/dev/null | grep -c "^one-data-" || echo "0")

    if [ "$running_containers" -eq 0 ]; then
        log_info "没有运行的基础设施服务"
        return 0
    fi

    "$SCRIPT_DIR/infrastructure.sh" stop
    log_success "基础设施服务已停止"
}

# ==================== 主函数 ====================

main() {
    if [ "$INFRA_ONLY" = false ]; then
        stop_application_services
    fi

    if [ "$APPS_ONLY" = false ]; then
        stop_infrastructure
    fi

    echo ""
    log_success "本地开发环境已停止"
    echo ""
}

main
