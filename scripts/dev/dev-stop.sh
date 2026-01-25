#!/bin/bash
# ONE-DATA-STUDIO 开发环境停止脚本
#
# 使用方法:
#   ./scripts/dev/dev-stop.sh [选项] [服务...]
#
# 示例:
#   ./scripts/dev/dev-stop.sh           # 停止所有服务
#   ./scripts/dev/dev-stop.sh -v        # 停止并删除数据卷
#   ./scripts/dev/dev-stop.sh mysql     # 仅停止 MySQL

set -e

# 加载共享函数库
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

# ==================== 默认配置 ====================

REMOVE_VOLUMES=false
REMOVE_IMAGES=false
REMOVE_ORPHANS=true
INCLUDE_MONITORING=false
TIMEOUT=30
SPECIFIC_SERVICES=""

# ==================== 解析参数 ====================

show_stop_help() {
    show_help \
        "ONE-DATA-STUDIO 开发环境停止脚本" \
        "dev-stop.sh [选项] [服务...]" \
        "  -v, --volumes     删除数据卷（谨慎使用）
  -r, --rmi         删除镜像
  -m, --monitoring  包含监控服务
  -t, --timeout N   停止超时时间（默认: 30秒）
  --keep-orphans    保留孤立容器
  -h, --help        显示帮助信息" \
        "  dev-stop.sh              # 停止所有服务
  dev-stop.sh -v           # 停止并删除数据卷
  dev-stop.sh mysql redis  # 仅停止指定服务
  dev-stop.sh b a          # 使用别名（bisheng, alldata）"
}

while [[ $# -gt 0 ]]; do
    case $1 in
        -v|--volumes)
            REMOVE_VOLUMES=true
            shift
            ;;
        -r|--rmi)
            REMOVE_IMAGES=true
            shift
            ;;
        -m|--monitoring)
            INCLUDE_MONITORING=true
            shift
            ;;
        -t|--timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        --keep-orphans)
            REMOVE_ORPHANS=false
            shift
            ;;
        -h|--help)
            show_stop_help
            exit 0
            ;;
        -*)
            log_error "未知选项: $1"
            show_stop_help
            exit 1
            ;;
        *)
            local resolved=$(resolve_service_alias "$1")
            if [ -z "$SPECIFIC_SERVICES" ]; then
                SPECIFIC_SERVICES="$resolved"
            else
                SPECIFIC_SERVICES="$SPECIFIC_SERVICES $resolved"
            fi
            shift
            ;;
    esac
done

# ==================== 停止服务 ====================

stop_services() {
    print_header "停止开发环境服务"

    # 构建 compose 命令参数
    local compose_args="-f $COMPOSE_FILE"

    if [ "$INCLUDE_MONITORING" = true ] && [ -f "$COMPOSE_MONITORING_FILE" ]; then
        compose_args="$compose_args -f $COMPOSE_MONITORING_FILE"
    fi

    # 确认删除数据卷
    if [ "$REMOVE_VOLUMES" = true ]; then
        log_warn "将删除所有数据卷，数据将丢失！"
        if ! confirm "确认删除数据卷?"; then
            REMOVE_VOLUMES=false
            log_info "保留数据卷"
        fi
    fi

    # 停止指定服务或所有服务
    if [ -n "$SPECIFIC_SERVICES" ]; then
        log_info "停止服务: $SPECIFIC_SERVICES"
        docker-compose $compose_args stop -t "$TIMEOUT" $SPECIFIC_SERVICES

        # 如果需要删除容器
        docker-compose $compose_args rm -f $SPECIFIC_SERVICES
    else
        log_info "停止所有服务..."

        local down_args="-t $TIMEOUT"

        if [ "$REMOVE_VOLUMES" = true ]; then
            down_args="$down_args --volumes"
        fi

        if [ "$REMOVE_IMAGES" = true ]; then
            down_args="$down_args --rmi local"
        fi

        if [ "$REMOVE_ORPHANS" = true ]; then
            down_args="$down_args --remove-orphans"
        fi

        docker-compose $compose_args down $down_args
    fi

    log_success "服务已停止"
}

# ==================== 显示状态 ====================

show_remaining_status() {
    echo ""
    log_info "当前容器状态:"

    local running=$(docker ps --filter "name=one-data" --format "{{.Names}}" 2>/dev/null)

    if [ -n "$running" ]; then
        echo "$running" | while read name; do
            echo "  - $name (运行中)"
        done
    else
        echo "  无 one-data 相关容器运行"
    fi

    if [ "$REMOVE_VOLUMES" = false ]; then
        echo ""
        log_info "数据卷已保留，可使用 'make dev-start' 恢复服务"
    fi
}

# ==================== 主函数 ====================

main() {
    # 检查 Docker
    if ! check_docker; then
        exit 1
    fi

    # 停止服务
    stop_services

    # 显示状态
    show_remaining_status
}

main
