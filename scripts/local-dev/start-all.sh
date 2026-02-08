#!/bin/bash
# ONE-DATA-STUDIO 本地开发环境 - 启动所有服务
#
# 此脚本启动所有本地开发服务
#
# 使用方法:
#   ./start-all.sh              # 启动所有服务（基础设施 + 应用）
#   ./start-all.sh --infra-only # 仅启动基础设施（Docker）
#   ./start-all.sh --apps-only  # 仅启动应用服务（本地）
#   ./start-all.sh --core       # 启动核心服务（快速启动）
#   ./start-all.sh --skip <service>  # 跳过指定服务

set -e

# 加载共享函数
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

# ==================== 配置 ====================

INFRA_ONLY=false
APPS_ONLY=false
CORE_ONLY=false
SKIP_SERVICES=""
INFRA_GROUP="all"

# ==================== 解析参数 ====================

while [[ $# -gt 0 ]]; do
    case $1 in
        --infra-only)
            INFRA_ONLY=true
            shift
            ;;
        --apps-only)
            APPS_ONLY=true
            shift
            ;;
        --core)
            CORE_ONLY=true
            shift
            ;;
        --dataops)
            INFRA_GROUP="dataops"
            shift
            ;;
        --skip)
            SKIP_SERVICES="$2"
            shift 2
            ;;
        -h|--help)
            echo "用法: $0 [选项]"
            echo ""
            echo "选项:"
            echo "  --infra-only    仅启动基础设施服务（Docker）"
            echo "  --apps-only     仅启动应用服务（本地）"
            echo "  --core          启动核心服务（快速启动）"
            echo "  --dataops       启动完整 DataOps 环境"
            echo "  --skip <srv>    跳过指定服务（逗号分隔）"
            echo "  -h, --help      显示帮助信息"
            echo ""
            echo "示例:"
            echo "  $0                  # 启动所有服务"
            echo "  $0 --infra-only     # 仅启动基础设施"
            echo "  $0 --apps-only      # 仅启动应用服务"
            echo "  $0 --core           # 启动核心服务（MySQL, Redis, Web, APIs）"
            echo "  $0 --skip web,model # 跳过 web 和 model-api"
            exit 0
            ;;
        *)
            log_error "未知选项: $1"
            exit 1
            ;;
    esac
done

# ==================== 函数 ====================

should_skip_service() {
    local service=$1
    if [ -n "$SKIP_SERVICES" ]; then
        echo "$SKIP_SERVICES" | grep -q "\(^\|,\)$service\(,\|$\)" && return 0 || return 1
    fi
    return 1
}

start_infrastructure() {
    print_header "启动基础设施服务"

    if ! check_docker; then
        log_error "Docker 不可用，跳过基础设施服务"
        return 1
    fi

    # 根据模式选择启动的服务组
    local group="$INFRA_GROUP"
    if [ "$CORE_ONLY" = true ]; then
        group="core"
    fi

    # 构建跳过列表
    local skip_list=""
    local all_infra_services="mysql redis minio etcd milvus keycloak kettle hop-server zookeeper shardingsphere-proxy elasticsearch superset superset-cache dolphinscheduler-api dolphinscheduler-postgresql openmetadata openmetadata-postgresql"

    for svc in $all_infra_services; do
        if should_skip_service "$svc"; then
            if [ -z "$skip_list" ]; then
                skip_list="$svc"
            else
                skip_list="$skip_list $svc"
            fi
        fi
    done

    # 启动基础设施
    if [ -n "$skip_list" ]; then
        log_info "启动基础设施服务（组: $group，跳过: $skip_list）..."
    else
        log_info "启动基础设施服务（组: $group）..."
    fi

    "$SCRIPT_DIR/infrastructure.sh" start "$group"

    log_success "基础设施服务已启动"
}

start_application_services() {
    print_header "启动应用服务"

    local services=(
        "data-api:Data API"
        "agent-api:Agent API"
        "admin-api:Admin API"
        "model-api:Model API"
        "openai-proxy:OpenAI Proxy"
        "ocr-service:OCR Service"
        "behavior-service:Behavior Service"
        "web:Web Frontend"
    )

    # 核心模式：只启动必要的 API 服务
    if [ "$CORE_ONLY" = true ]; then
        services=(
            "data-api:Data API"
            "agent-api:Agent API"
            "web:Web Frontend"
        )
    fi

    local started=0
    local failed=0
    local skipped=0

    for item in "${services[@]}"; do
        IFS=':' read -r svc name <<< "$item"

        if should_skip_service "$svc"; then
            log_info "跳过 $name"
            skipped=$((skipped + 1))
            continue
        fi

        echo ""
        log_step "启动 $name..."

        if "$SCRIPT_DIR/$svc.sh" start 2>&1 | grep -q "启动成功\|started\|已启动"; then
            started=$((started + 1))
            log_success "$name 已启动"
        else
            # 检查服务是否实际在运行
            if [ -f "$PID_DIR/$svc.pid" ]; then
                local pid=$(cat "$PID_DIR/$svc.pid")
                if ps -p "$pid" > /dev/null 2>&1; then
                    started=$((started + 1))
                    log_success "$name 已启动 (PID: $pid)"
                else
                    log_error "$name 启动失败"
                    failed=$((failed + 1))
                fi
            else
                log_error "$name 启动失败"
                failed=$((failed + 1))
            fi
        fi
    done

    echo ""
    print_header "应用服务启动总结"
    echo "  已启动: $started"
    echo "  已跳过: $skipped"
    echo "  失败:   $failed"
    echo ""

    if [ $failed -gt 0 ]; then
        log_error "部分服务启动失败，请检查日志"
        return 1
    fi
}

print_summary() {
    print_header "本地开发环境已启动"

    echo -e "${BOLD}应用服务 (本地):${NC}"

    if ! should_skip_service "web"; then
        local web_pid=$(cat "$PID_DIR/web.pid" 2>/dev/null || echo "")
        [ -n "$web_pid" ] && echo "  ✓ Web 前端:        http://localhost:$(get_service_port web) (PID: $web_pid)"
    fi

    if ! should_skip_service "data-api"; then
        local api_pid=$(cat "$PID_DIR/data-api.pid" 2>/dev/null || echo "")
        [ -n "$api_pid" ] && echo "  ✓ Data API:        http://localhost:$(get_service_port data-api) (PID: $api_pid)"
    fi

    if ! should_skip_service "agent-api"; then
        local api_pid=$(cat "$PID_DIR/agent-api.pid" 2>/dev/null || echo "")
        [ -n "$api_pid" ] && echo "  ✓ Agent API:       http://localhost:$(get_service_port agent-api) (PID: $api_pid)"
    fi

    if ! should_skip_service "admin-api"; then
        local api_pid=$(cat "$PID_DIR/admin-api.pid" 2>/dev/null || echo "")
        [ -n "$api_pid" ] && echo "  ✓ Admin API:       http://localhost:$(get_service_port admin-api) (PID: $api_pid)"
    fi

    if ! should_skip_service "model-api"; then
        local api_pid=$(cat "$PID_DIR/model-api.pid" 2>/dev/null || echo "")
        [ -n "$api_pid" ] && echo "  ✓ Model API:       http://localhost:$(get_service_port model-api) (PID: $api_pid)"
    fi

    if ! should_skip_service "openai-proxy"; then
        local api_pid=$(cat "$PID_DIR/openai-proxy.pid" 2>/dev/null || echo "")
        [ -n "$api_pid" ] && echo "  ✓ OpenAI Proxy:    http://localhost:$(get_service_port openai-proxy) (PID: $api_pid)"
    fi

    if ! should_skip_service "ocr-service" && [ "$CORE_ONLY" != true ]; then
        local api_pid=$(cat "$PID_DIR/ocr-service.pid" 2>/dev/null || echo "")
        [ -n "$api_pid" ] && echo "  ✓ OCR Service:     http://localhost:$(get_service_port ocr-service) (PID: $api_pid)"
    fi

    if ! should_skip_service "behavior-service" && [ "$CORE_ONLY" != true ]; then
        local api_pid=$(cat "$PID_DIR/behavior-service.pid" 2>/dev/null || echo "")
        [ -n "$api_pid" ] && echo "  ✓ Behavior Service: http://localhost:$(get_service_port behavior-service) (PID: $api_pid)"
    fi

    echo ""
    echo -e "${BOLD}基础设施服务 (Docker):${NC}"
    echo "  核心存储:"
    echo "    MySQL:          localhost:3306 (root/dev123)"
    echo "    Redis:          localhost:6379 (密码: redisdev123)"
    echo "    MinIO API:      http://localhost:9000"
    echo "    MinIO Console:  http://localhost:9001"
    echo "    ETCD:           localhost:2379"

    if [ "$CORE_ONLY" != true ]; then
        echo ""
        echo "  AI/ML 服务:"
        echo "    Milvus:         localhost:19530"
        echo ""
        echo "  认证服务:"
        echo "    Keycloak:       http://localhost:8080 (admin/admin)"
        echo ""
        echo "  ETL 服务:"
        echo "    Kettle:         http://localhost:8181"
        echo "    Hop Server:     http://localhost:8182"
        echo ""
        echo "  数据分析:"
        echo "    Elasticsearch:  http://localhost:9200"
        echo "    Superset:       http://localhost:8088 (admin/admin)"
        echo ""
        echo "  调度服务:"
        echo "    DolphinScheduler: http://localhost:12345"
        echo ""
        echo "  元数据服务:"
        echo "    OpenMetadata:   http://localhost:8585 (admin/admin)"
    fi

    echo ""
    echo -e "${BOLD}常用命令:${NC}"
    echo "  查看所有状态:  ./status-all.sh"
    echo "  停止所有服务:  ./stop-all.sh"
    echo "  重启所有服务:  ./restart-all.sh"
    echo "  查看服务日志:  ./<service>.sh logs"
    echo ""
}

# ==================== 主函数 ====================

main() {
    load_env

    if [ "$APPS_ONLY" = false ]; then
        start_infrastructure
    fi

    if [ "$INFRA_ONLY" = false ]; then
        start_application_services
    fi

    if [ "$INFRA_ONLY" = false ]; then
        print_summary
    fi

    log_success "本地开发环境启动完成"
}

main
