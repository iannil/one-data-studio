#!/bin/bash
# ONE-DATA-STUDIO 本地开发环境 - 查看所有服务状态
#
# 使用方法:
#   ./status-all.sh         # 查看所有服务状态
#   ./status-all.sh --watch # 持续监控状态

set -e

# 加载共享函数
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

# ==================== 配置 ====================

WATCH_MODE=false

# ==================== 解析参数 ====================

while [[ $# -gt 0 ]]; do
    case $1 in
        --watch)
            WATCH_MODE=true
            shift
            ;;
        -h|--help)
            echo "用法: $0 [选项]"
            echo ""
            echo "选项:"
            echo "  --watch         持续监控服务状态（每 5 秒刷新）"
            echo "  -h, --help      显示帮助信息"
            exit 0
            ;;
        *)
            log_error "未知选项: $1"
            exit 1
            ;;
    esac
done

# ==================== 函数 ====================

print_docker_status() {
    print_header "Docker 容器服务 (基础设施)"

    if ! check_docker 2>/dev/null; then
        echo -e "  ${RED}✗${NC} Docker 不可用"
        echo ""
        return
    fi

    # 获取所有 one-data 容器
    local containers=$(docker ps --format '{{.Names}}' 2>/dev/null | grep "^one-data-" | sort)

    if [ -z "$containers" ]; then
        echo -e "  ${YELLOW}○${NC} 没有运行的基础设施服务"
        echo ""
        return
    fi

    # 分类显示
    echo -e "${BOLD}核心存储:${NC}"
    for svc in mysql redis minio etcd; do
        show_docker_service "$svc"
    done

    echo ""
    echo -e "${BOLD}AI/ML 服务:${NC}"
    show_docker_service "milvus"

    echo ""
    echo -e "${BOLD}认证服务:${NC}"
    show_docker_service "keycloak"

    echo ""
    echo -e "${BOLD}ETL 服务:${NC}"
    for svc in kettle hop-server zookeeper shardingsphere-proxy; do
        show_docker_service "$svc"
    done

    echo ""
    echo -e "${BOLD}数据分析:${NC}"
    for svc in elasticsearch superset superset-cache; do
        show_docker_service "$svc"
    done

    echo ""
    echo -e "${BOLD}调度服务:${NC}"
    for svc in dolphinscheduler-api dolphinscheduler-postgresql; do
        show_docker_service "$svc"
    done

    echo ""
    echo -e "${BOLD}元数据服务:${NC}"
    for svc in openmetadata openmetadata-postgresql; do
        show_docker_service "$svc"
    done

    echo ""
}

show_docker_service() {
    local service=$1
    local container_name="one-data-$service"
    local color="$YELLOW"
    local symbol="○"
    local status="未运行"
    local port=""

    # 获取端口
    case "$service" in
        mysql) port="3306" ;;
        redis) port="6379" ;;
        minio) port="9000" ;;
        minio-console) port="9001" ;;
        milvus) port="19530" ;;
        etcd) port="2379" ;;
        keycloak) port="8080" ;;
        kettle) port="8181" ;;
        hop-server) port="8182" ;;
        zookeeper) port="2181" ;;
        shardingsphere-proxy) port="3307" ;;
        elasticsearch) port="9200" ;;
        superset) port="8088" ;;
        superset-cache) port="6380" ;;
        dolphinscheduler-api) port="12345" ;;
        dolphinscheduler-postgresql) port="5433" ;;
        openmetadata) port="8585" ;;
        openmetadata-postgresql) port="5434" ;;
    esac

    if docker ps --format '{{.Names}}' 2>/dev/null | grep -q "^${container_name}$"; then
        local health=$(docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}running{{end}}' "$container_name" 2>/dev/null || echo "unknown")
        if [ "$health" = "healthy" ] || [ "$health" = "running" ]; then
            status="运行中"
            color="$GREEN"
            symbol="✓"
        else
            status="$health"
            color="$RED"
            symbol="!"
        fi
    fi

    # 格式化输出
    local service_name=$(echo "$service" | sed 's/-/ /g' | sed 's/\b\(.\)/\u\1/g')
    printf "  ${color}${symbol}${NC} %-24s " "${service_name}:"
    echo -e "${color}${status}${NC}"
    if [ -n "$port" ]; then
        echo "     端口: $port"
    fi
}

print_app_status() {
    print_header "本地应用服务"

    local services=(
        "web:Web 前端:3000"
        "data-api:Data API:8001"
        "agent-api:Agent API:8000"
        "admin-api:Admin API:8004"
        "model-api:Model API:8002"
        "openai-proxy:OpenAI Proxy:8003"
        "ocr-service:OCR Service:8007"
        "behavior-service:Behavior Service:8008"
    )

    for item in "${services[@]}"; do
        IFS=':' read -r svc name port <<< "$item"
        show_app_service "$svc" "$name" "$port"
    done

    echo ""
}

show_app_service() {
    local service=$1
    local name=$2
    local port=$3
    local pid_file="$PID_DIR/$service.pid"
    local color="$YELLOW"
    local symbol="○"
    local status="未运行"

    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file" 2>/dev/null || echo "")
        if [ -n "$pid" ] && ps -p "$pid" > /dev/null 2>&1; then
            status="运行中"
            color="$GREEN"
            symbol="✓"
        else
            status="已停止 (残留 PID)"
            color="$RED"
            symbol="!"
        fi
    fi

    printf "  ${color}${symbol}${NC} %-20s ${color}${status}${NC}" "${name}:"
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file" 2>/dev/null || echo "")
        [ -n "$pid" ] && echo " (PID: $pid)" || echo
    else
        echo
    fi
    echo "     端口: $port"
}

print_summary() {
    print_header "服务状态汇总"

    # 统计 Docker 容器
    local total_docker=0
    local healthy_docker=0
    if check_docker 2>/dev/null; then
        total_docker=$(docker ps --format '{{.Names}}' 2>/dev/null | grep -c "^one-data-" || echo "0")
        healthy_docker=$(docker ps --format '{{.Names}}' 2>/dev/null | grep "^one-data-" | while read name; do
            docker inspect --format='{{if .State.Health}}{{if eq .State.Health.Status "healthy"}}1{{end}}{{else}}{{if eq .State.Running true}}1{{end}}{{end}}' "$name" 2>/dev/null || echo "0"
        done | awk '{s+=$1} END {print s}')
    fi

    # 统计应用服务
    local total_apps=8
    local running_apps=0
    for svc in web data-api agent-api admin-api model-api openai-proxy ocr-service behavior-service; do
        if [ -f "$PID_DIR/$svc.pid" ]; then
            local pid=$(cat "$PID_DIR/$svc.pid" 2>/dev/null || echo "")
            if [ -n "$pid" ] && ps -p "$pid" > /dev/null 2>&1; then
                running_apps=$((running_apps + 1))
            fi
        fi
    done

    echo "  Docker 容器: ${healthy_docker}/${total_docker} 健康"
    echo "  应用服务: ${running_apps}/${total_apps} 运行中"
    echo "  总计: $((healthy_docker + running_apps))/24 服务正常"
    echo ""
}

print_quick_commands() {
    print_header "快捷命令"
    echo "  启动所有:      ./start-all.sh"
    echo "  启动核心:      ./start-all.sh --core"
    echo "  停止所有:      ./stop-all.sh"
    echo "  重启所有:      ./restart-all.sh"
    echo "  查看服务日志:  ./<service>.sh logs"
    echo ""
}

# ==================== 主函数 ====================

main() {
    if [ "$WATCH_MODE" = true ]; then
        while true; do
            clear
            echo "========================================"
            echo "ONE-DATA-STUDIO 服务状态监控"
            echo "按 Ctrl+C 退出"
            echo "========================================"
            echo ""

            print_app_status
            print_docker_status
            print_summary
            print_quick_commands

            sleep 5
        done
    else
        clear
        echo "========================================"
        echo "ONE-DATA-STUDIO 服务状态"
        echo "检查时间: $(date '+%Y-%m-%d %H:%M:%S')"
        echo "========================================"
        echo ""

        print_app_status
        print_docker_status
        print_summary
        print_quick_commands
    fi
}

main
