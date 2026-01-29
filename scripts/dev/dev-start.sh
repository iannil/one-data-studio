#!/bin/bash
# ONE-DATA-STUDIO 开发环境启动脚本
#
# 使用方法:
#   ./scripts/dev/dev-start.sh [选项] [服务...]
#
# 示例:
#   ./scripts/dev/dev-start.sh              # 启动所有服务
#   ./scripts/dev/dev-start.sh -i           # 仅启动基础设施
#   ./scripts/dev/dev-start.sh -a           # 仅启动应用服务
#   ./scripts/dev/dev-start.sh -m           # 包含监控服务
#   ./scripts/dev/dev-start.sh mysql redis  # 启动指定服务

set -e

# 加载共享函数库
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

# ==================== 默认配置 ====================

START_MODE="all"          # all, infra, apps
INCLUDE_MONITORING=false
FORCE_BUILD=false
TIMEOUT=120
DETACH=true
VERBOSE=false
SPECIFIC_SERVICES=""
SEED_DATA=false           # 是否导入种子数据

# ==================== 解析参数 ====================

show_start_help() {
    show_help \
        "ONE-DATA-STUDIO 开发环境启动脚本" \
        "dev-start.sh [选项] [服务...]" \
        "  -i, --infra       仅启动基础设施服务（mysql, redis, minio, etcd, milvus）
  -a, --apps        仅启动应用服务（agent-api, data-api, model-api, openai-proxy, web）
  -m, --monitoring  包含监控服务（prometheus, grafana, jaeger）
  -b, --build       强制重新构建镜像
  -s, --seed        启动后导入种子数据（初始化数据）
  -t, --timeout N   等待服务就绪的超时时间（默认: 120秒）
  -f, --foreground  前台运行（不使用 -d）
  -v, --verbose     显示详细输出
  -h, --help        显示帮助信息" \
        "  dev-start.sh              # 启动所有服务
  dev-start.sh -i           # 仅启动基础设施
  dev-start.sh -a           # 仅启动应用服务
  dev-start.sh -m           # 包含监控栈
  dev-start.sh --build      # 强制重建镜像
  dev-start.sh --seed       # 启动并导入种子数据
  dev-start.sh mysql redis  # 启动指定服务
  dev-start.sh agent data   # 启动指定 API 服务"
}

while [[ $# -gt 0 ]]; do
    case $1 in
        -i|--infra)
            START_MODE="infra"
            shift
            ;;
        -a|--apps)
            START_MODE="apps"
            shift
            ;;
        -m|--monitoring)
            INCLUDE_MONITORING=true
            shift
            ;;
        -b|--build)
            FORCE_BUILD=true
            shift
            ;;
        -s|--seed)
            SEED_DATA=true
            shift
            ;;
        -t|--timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        -f|--foreground)
            DETACH=false
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            export DEBUG=1
            shift
            ;;
        -h|--help)
            show_start_help
            exit 0
            ;;
        -*)
            log_error "未知选项: $1"
            show_start_help
            exit 1
            ;;
        *)
            # 解析服务别名
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

# ==================== 前置检查 ====================

pre_start_check() {
    log_step "执行启动前检查..."

    # 检查 Docker
    if ! check_docker; then
        exit 1
    fi

    # 检查 Docker Compose
    if ! check_docker_compose; then
        exit 1
    fi

    # 检查 compose 文件
    if [ ! -f "$COMPOSE_FILE" ]; then
        log_error "Docker Compose 文件不存在: $COMPOSE_FILE"
        exit 1
    fi

    # 加载环境变量
    load_env || log_warn "未加载环境变量文件，将使用默认值或 Docker Compose 默认配置"

    # 确定要启动的服务
    local services_to_check=""

    if [ -n "$SPECIFIC_SERVICES" ]; then
        services_to_check="$SPECIFIC_SERVICES"
    else
        case $START_MODE in
            infra)
                services_to_check="$INFRA_SERVICES"
                ;;
            apps)
                services_to_check="$APP_SERVICES"
                ;;
            all)
                services_to_check="$ALL_SERVICES"
                ;;
        esac
    fi

    # 检查端口冲突
    local port_conflicts=0
    for service in $services_to_check; do
        local port=$(get_service_port "$service")
        if [ -n "$port" ] && ! is_service_running "$service"; then
            if ! check_port "$port" "$service"; then
                port_conflicts=$((port_conflicts + 1))
            fi
        fi
    done

    if [ $port_conflicts -gt 0 ]; then
        log_warn "发现 $port_conflicts 个端口冲突"
        if ! confirm "是否继续启动?"; then
            exit 1
        fi
    fi

    log_success "启动前检查完成"
}

# ==================== 启动服务 ====================

start_services() {
    local services="$1"
    local compose_args=""

    print_header "启动开发环境服务"

    # 构建 compose 命令参数
    compose_args="-f $COMPOSE_FILE"

    if [ "$INCLUDE_MONITORING" = true ]; then
        if [ -f "$COMPOSE_MONITORING_FILE" ]; then
            compose_args="$compose_args -f $COMPOSE_MONITORING_FILE"
            log_info "包含监控服务"
        else
            log_warn "监控配置文件不存在: $COMPOSE_MONITORING_FILE"
        fi
    fi

    # 确定要启动的服务
    local target_services=""

    if [ -n "$services" ]; then
        target_services="$services"
    else
        case $START_MODE in
            infra)
                target_services="$INFRA_SERVICES"
                ;;
            apps)
                target_services="$APP_SERVICES"
                ;;
            all)
                # 不指定服务，启动所有
                ;;
        esac
    fi

    # 显示启动信息
    if [ -n "$target_services" ]; then
        log_info "启动服务: $target_services"
    else
        log_info "启动所有服务"
    fi

    # 构建镜像（如果需要）
    if [ "$FORCE_BUILD" = true ]; then
        log_step "构建 Docker 镜像..."
        if [ -n "$target_services" ]; then
            docker-compose $compose_args build $target_services
        else
            docker-compose $compose_args build
        fi
    fi

    # 启动服务
    log_step "启动容器..."
    local up_args=""

    if [ "$DETACH" = true ]; then
        up_args="-d"
    fi

    if [ "$FORCE_BUILD" = true ]; then
        up_args="$up_args --build"
    fi

    up_args="$up_args --remove-orphans"

    if [ -n "$target_services" ]; then
        docker-compose $compose_args up $up_args $target_services
    else
        docker-compose $compose_args up $up_args
    fi

    # 如果是前台模式，不需要等待
    if [ "$DETACH" = false ]; then
        return 0
    fi

    # 等待服务就绪
    wait_for_services "$target_services"
}

# ==================== 等待服务就绪 ====================

wait_for_services() {
    local services="$1"

    log_step "等待服务就绪..."

    # 如果没有指定服务，获取所有运行中的服务
    if [ -z "$services" ]; then
        services="$ALL_SERVICES"
        if [ "$INCLUDE_MONITORING" = true ]; then
            services="$services $MONITORING_SERVICES"
        fi
    fi

    local failed_services=""

    for service in $services; do
        # 检查服务是否在 compose 中定义
        if ! docker-compose -f "$COMPOSE_FILE" config --services 2>/dev/null | grep -q "^${service}$"; then
            log_debug "跳过未定义的服务: $service"
            continue
        fi

        if ! wait_for_health "$service" "$TIMEOUT" 3; then
            if [ -z "$failed_services" ]; then
                failed_services="$service"
            else
                failed_services="$failed_services $service"
            fi
        fi
    done

    if [ -n "$failed_services" ]; then
        log_warn "以下服务可能未完全就绪: $failed_services"
    fi
}

# ==================== 显示访问信息 ====================

print_access_info() {
    print_header "服务访问信息"

    echo -e "${BOLD}应用服务:${NC}"
    echo "  Web 前端:        http://localhost:$(get_service_port web-frontend)"
    echo "  Agent API:       http://localhost:$(get_service_port agent-api)"
    echo "  Data API:        http://localhost:$(get_service_port data-api)"
    echo "  Model API:       http://localhost:$(get_service_port model-api)"
    echo "  OpenAI Proxy:    http://localhost:$(get_service_port openai-proxy)"
    echo ""
    echo -e "${BOLD}基础设施:${NC}"
    echo "  MySQL:           localhost:$(get_service_port mysql)"
    echo "  Redis:           localhost:$(get_service_port redis)"
    echo "  MinIO Console:   http://localhost:$(get_service_port minio-console)"
    echo "  Milvus:          localhost:$(get_service_port milvus)"

    if [ "$INCLUDE_MONITORING" = true ]; then
        echo ""
        echo -e "${BOLD}监控服务:${NC}"
        echo "  Prometheus:      http://localhost:$(get_service_port prometheus)"
        echo "  Grafana:         http://localhost:$(get_service_port grafana) (admin/admin)"
        echo "  Jaeger:          http://localhost:$(get_service_port jaeger)"
    fi

    echo ""
    echo -e "${BOLD}常用命令:${NC}"
    echo "  查看状态:  make dev-status"
    echo "  查看日志:  make dev-logs [服务]"
    echo "  停止服务:  make dev-stop"
    echo ""
}

# ==================== 种子数据导入 ====================

import_seed_data() {
    # 检查是否需要导入种子数据
    if [ "$SEED_DATA" = true ] || [ "${SEED_DATA}" = "true" ]; then
        log_step "导入种子数据..."

        # 检查 seed.py 脚本是否存在
        local seed_script="$PROJECT_ROOT/scripts/seed.py"
        if [ ! -f "$seed_script" ]; then
            log_error "种子数据脚本不存在: $seed_script"
            return 1
        fi

        # 等待数据库服务就绪
        log_info "等待数据库服务就绪..."
        sleep 5

        # 执行种子数据导入
        if python3 "$seed_script"; then
            log_success "种子数据导入完成"
        else
            log_warn "种子数据导入失败，可手动执行: python3 scripts/seed.py"
        fi
    fi
}

# ==================== 主函数 ====================

main() {
    # 前置检查
    pre_start_check

    # 启动服务
    start_services "$SPECIFIC_SERVICES"

    # 显示访问信息（仅在后台模式）
    if [ "$DETACH" = true ]; then
        print_access_info

        # 导入种子数据（如果需要）
        import_seed_data

        log_success "开发环境已启动"
    fi
}

main
