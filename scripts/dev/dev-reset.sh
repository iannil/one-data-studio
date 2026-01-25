#!/bin/bash
# ONE-DATA-STUDIO 开发环境重置脚本
#
# 使用方法:
#   ./scripts/dev/dev-reset.sh [选项]
#
# 此脚本会完全重置开发环境，包括：
# - 停止并删除所有容器
# - 删除数据卷（默认）
# - 删除本地镜像（可选）
# - 重新构建并启动服务

set -e

# 加载共享函数库
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

# ==================== 默认配置 ====================

KEEP_IMAGES=false
KEEP_VOLUMES=false
SKIP_REBUILD=false
INCLUDE_MONITORING=false
FORCE=false

# ==================== 解析参数 ====================

show_reset_help() {
    show_help \
        "ONE-DATA-STUDIO 开发环境重置脚本" \
        "dev-reset.sh [选项]" \
        "  --keep-images     保留本地 Docker 镜像
  --keep-volumes    保留数据卷（不删除数据）
  --skip-rebuild    重置后不重新构建启动
  -m, --monitoring  包含监控服务
  -f, --force       跳过确认提示
  -h, --help        显示帮助信息

注意: 此操作具有破坏性，将删除所有容器和数据！" \
        "  dev-reset.sh              # 完全重置环境
  dev-reset.sh --keep-volumes  # 保留数据
  dev-reset.sh --keep-images   # 保留镜像
  dev-reset.sh --skip-rebuild  # 只清理不重建"
}

while [[ $# -gt 0 ]]; do
    case $1 in
        --keep-images)
            KEEP_IMAGES=true
            shift
            ;;
        --keep-volumes)
            KEEP_VOLUMES=true
            shift
            ;;
        --skip-rebuild)
            SKIP_REBUILD=true
            shift
            ;;
        -m|--monitoring)
            INCLUDE_MONITORING=true
            shift
            ;;
        -f|--force)
            FORCE=true
            shift
            ;;
        -h|--help)
            show_reset_help
            exit 0
            ;;
        -*)
            log_error "未知选项: $1"
            show_reset_help
            exit 1
            ;;
        *)
            shift
            ;;
    esac
done

# ==================== 重置函数 ====================

# 显示将要执行的操作
show_reset_preview() {
    print_header "开发环境重置预览"

    echo -e "${RED}${BOLD}警告: 此操作将执行以下破坏性操作:${NC}"
    echo ""

    echo "  1. 停止所有 one-data 相关容器"
    echo "  2. 删除所有 one-data 相关容器"

    if [ "$KEEP_VOLUMES" = false ]; then
        echo -e "  3. ${RED}删除所有数据卷（数据将丢失！）${NC}"
    else
        echo "  3. 保留数据卷"
    fi

    if [ "$KEEP_IMAGES" = false ]; then
        echo "  4. 删除本地构建的镜像"
    else
        echo "  4. 保留镜像"
    fi

    if [ "$SKIP_REBUILD" = false ]; then
        echo "  5. 重新构建并启动所有服务"
    else
        echo "  5. 不重新启动服务"
    fi

    echo ""

    # 显示当前运行的容器
    local running=$(docker ps --filter "name=one-data" --format "{{.Names}}" 2>/dev/null)
    if [ -n "$running" ]; then
        echo -e "${BOLD}当前运行的容器:${NC}"
        echo "$running" | while read name; do
            echo "  - $name"
        done
        echo ""
    fi

    # 显示数据卷
    if [ "$KEEP_VOLUMES" = false ]; then
        local volumes=$(docker volume ls --filter "name=one-data\|mysql_data\|redis_data\|minio_data\|milvus_data\|etcd_data" -q 2>/dev/null)
        if [ -n "$volumes" ]; then
            echo -e "${BOLD}将删除的数据卷:${NC}"
            echo "$volumes" | while read vol; do
                local size=$(docker system df -v 2>/dev/null | grep "$vol" | awk '{print $3}' || echo "unknown")
                echo "  - $vol"
            done
            echo ""
        fi
    fi
}

# 确认重置
confirm_reset() {
    if [ "$FORCE" = true ]; then
        return 0
    fi

    echo -e "${RED}${BOLD}此操作不可撤销！${NC}"
    echo ""

    if ! confirm_dangerous "重置开发环境" "RESET"; then
        log_info "操作已取消"
        exit 0
    fi
}

# 停止并删除容器
cleanup_containers() {
    log_step "停止并删除容器..."

    local compose_args=("-f" "$COMPOSE_FILE")

    if [ "$INCLUDE_MONITORING" = true ] && [ -f "$COMPOSE_MONITORING_FILE" ]; then
        compose_args+=("-f" "$COMPOSE_MONITORING_FILE")
    fi

    # 停止服务
    docker-compose "${compose_args[@]}" down --remove-orphans 2>/dev/null || true

    # 强制删除任何残留的容器
    local containers=$(docker ps -a --filter "name=one-data" -q 2>/dev/null)
    if [ -n "$containers" ]; then
        log_info "清理残留容器..."
        echo "$containers" | xargs -r docker rm -f 2>/dev/null || true
    fi

    log_success "容器已清理"
}

# 删除数据卷
cleanup_volumes() {
    if [ "$KEEP_VOLUMES" = true ]; then
        log_info "保留数据卷"
        return
    fi

    log_step "删除数据卷..."

    # 从 compose 文件定义的卷
    local compose_volumes=(
        "mysql_data"
        "redis_data"
        "minio_data"
        "milvus_data"
        "etcd_data"
        "prometheus_data"
        "grafana_data"
    )

    for vol in "${compose_volumes[@]}"; do
        # 检查带前缀的卷名
        local full_vol_name=$(docker volume ls -q 2>/dev/null | grep -E "(local_)?${vol}$" | head -1)
        if [ -n "$full_vol_name" ]; then
            docker volume rm "$full_vol_name" 2>/dev/null && \
                log_info "已删除卷: $full_vol_name" || true
        fi
    done

    # 清理其他 one-data 相关的卷
    local other_volumes=$(docker volume ls -q 2>/dev/null | grep "one-data" || true)
    if [ -n "$other_volumes" ]; then
        echo "$other_volumes" | xargs -r docker volume rm 2>/dev/null || true
    fi

    log_success "数据卷已清理"
}

# 删除镜像
cleanup_images() {
    if [ "$KEEP_IMAGES" = true ]; then
        log_info "保留镜像"
        return
    fi

    log_step "删除本地镜像..."

    # 删除项目构建的镜像
    local images=$(docker images --filter "reference=one-data*" -q 2>/dev/null)
    if [ -n "$images" ]; then
        echo "$images" | xargs -r docker rmi -f 2>/dev/null || true
    fi

    # 删除 local_ 前缀的镜像（docker-compose 构建的）
    local compose_images=$(docker images --filter "reference=local_*" -q 2>/dev/null)
    if [ -n "$compose_images" ]; then
        echo "$compose_images" | xargs -r docker rmi -f 2>/dev/null || true
    fi

    # 清理悬挂镜像
    docker image prune -f 2>/dev/null || true

    log_success "镜像已清理"
}

# 清理网络
cleanup_networks() {
    log_step "清理网络..."

    # 删除 one-data 网络
    docker network rm one-data-network 2>/dev/null || true

    # 清理未使用的网络
    docker network prune -f 2>/dev/null || true

    log_success "网络已清理"
}

# 重新构建并启动
rebuild_and_start() {
    if [ "$SKIP_REBUILD" = true ]; then
        log_info "跳过重新构建"
        return
    fi

    log_step "重新构建并启动服务..."

    # 使用 dev-start 脚本启动
    local start_args=("--build")

    if [ "$INCLUDE_MONITORING" = true ]; then
        start_args+=("--monitoring")
    fi

    "$SCRIPT_DIR/dev-start.sh" "${start_args[@]}"
}

# ==================== 主函数 ====================

main() {
    # 检查 Docker
    if ! check_docker; then
        exit 1
    fi

    # 显示预览
    show_reset_preview

    # 确认操作
    confirm_reset

    print_header "开始重置环境"

    # 执行清理
    cleanup_containers
    cleanup_volumes
    cleanup_images
    cleanup_networks

    echo ""
    log_success "环境清理完成"

    # 重新构建
    if [ "$SKIP_REBUILD" = false ]; then
        echo ""
        rebuild_and_start
    else
        echo ""
        log_info "环境已重置，使用 'make dev-start' 重新启动服务"
    fi
}

main
