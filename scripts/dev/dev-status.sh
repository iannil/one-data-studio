#!/bin/bash
# ONE-DATA-STUDIO 开发环境状态查看脚本
#
# 使用方法:
#   ./scripts/dev/dev-status.sh [选项]
#
# 示例:
#   ./scripts/dev/dev-status.sh        # 查看所有服务状态
#   ./scripts/dev/dev-status.sh -v     # 详细模式（含资源使用）
#   ./scripts/dev/dev-status.sh -w     # 持续监控模式

set -e

# 加载共享函数库
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

# ==================== 默认配置 ====================

VERBOSE=false
WATCH_MODE=false
WATCH_INTERVAL=5
JSON_OUTPUT=false
SHOW_PORTS=true
SHOW_HEALTH=true

# ==================== 解析参数 ====================

show_status_help() {
    show_help \
        "ONE-DATA-STUDIO 开发环境状态查看脚本" \
        "dev-status.sh [选项]" \
        "  -v, --verbose     显示详细信息（CPU、内存使用）
  -w, --watch       持续监控模式
  -i, --interval N  监控间隔（默认: 5秒）
  -j, --json        JSON 格式输出
  --no-ports        不显示端口信息
  --no-health       不显示健康状态
  -h, --help        显示帮助信息" \
        "  dev-status.sh           # 查看所有服务状态
  dev-status.sh -v        # 详细模式
  dev-status.sh -w        # 持续监控
  dev-status.sh -w -i 2   # 每 2 秒刷新"
}

while [[ $# -gt 0 ]]; do
    case $1 in
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -w|--watch)
            WATCH_MODE=true
            shift
            ;;
        -i|--interval)
            WATCH_INTERVAL="$2"
            shift 2
            ;;
        -j|--json)
            JSON_OUTPUT=true
            shift
            ;;
        --no-ports)
            SHOW_PORTS=false
            shift
            ;;
        --no-health)
            SHOW_HEALTH=false
            shift
            ;;
        -h|--help)
            show_status_help
            exit 0
            ;;
        -*)
            log_error "未知选项: $1"
            show_status_help
            exit 1
            ;;
        *)
            shift
            ;;
    esac
done

# ==================== 状态显示函数 ====================

# 获取状态颜色
get_status_color() {
    local status=$1

    case $status in
        healthy|running)
            echo -e "${GREEN}"
            ;;
        unhealthy|exited|dead)
            echo -e "${RED}"
            ;;
        starting|restarting)
            echo -e "${YELLOW}"
            ;;
        *)
            echo -e "${NC}"
            ;;
    esac
}

# 获取状态图标
get_status_icon() {
    local status=$1

    case $status in
        healthy)
            echo "●"
            ;;
        running)
            echo "◐"
            ;;
        unhealthy)
            echo "✗"
            ;;
        exited|dead)
            echo "○"
            ;;
        starting|restarting)
            echo "◑"
            ;;
        not_created)
            echo "-"
            ;;
        *)
            echo "?"
            ;;
    esac
}

# 显示服务状态表格
show_status_table() {
    local all_services="$ALL_SERVICES $MONITORING_SERVICES"

    echo ""
    if [ "$VERBOSE" = true ]; then
        printf "%-20s %-12s %-8s %-10s %-10s %-10s\n" "服务" "状态" "端口" "CPU" "内存" "运行时间"
        print_separator
    else
        printf "%-20s %-12s %-8s\n" "服务" "状态" "端口"
        print_separator
    fi

    for service in $all_services; do
        local container_name=$(get_container_name "$service")
        local status=$(get_service_status "$service")
        local port=$(get_service_port "$service")
        if [ -z "$port" ]; then
            port="N/A"
        fi
        local color=$(get_status_color "$status")
        local icon=$(get_status_icon "$status")

        if [ "$VERBOSE" = true ]; then
            if [ "$status" = "running" ] || [ "$status" = "healthy" ]; then
                local stats=$(docker stats --no-stream --format "{{.CPUPerc}},{{.MemUsage}}" "$container_name" 2>/dev/null || echo "N/A,N/A")
                local cpu=$(echo "$stats" | cut -d',' -f1)
                local mem=$(echo "$stats" | cut -d',' -f2 | cut -d'/' -f1)
                local uptime=$(docker inspect --format='{{.State.StartedAt}}' "$container_name" 2>/dev/null || echo "")

                if [ -n "$uptime" ]; then
                    local start_ts=$(date -j -f "%Y-%m-%dT%H:%M:%S" "${uptime:0:19}" "+%s" 2>/dev/null || date -d "${uptime:0:19}" "+%s" 2>/dev/null || echo "0")
                    local now_ts=$(date "+%s")
                    local duration=$((now_ts - start_ts))
                    uptime=$(format_duration "$duration")
                else
                    uptime="N/A"
                fi

                printf "%-20s ${color}%-12s${NC} %-8s %-10s %-10s %-10s\n" "$service" "$icon $status" "$port" "$cpu" "$mem" "$uptime"
            else
                printf "%-20s ${color}%-12s${NC} %-8s %-10s %-10s %-10s\n" "$service" "$icon $status" "$port" "-" "-" "-"
            fi
        else
            printf "%-20s ${color}%-12s${NC} %-8s\n" "$service" "$icon $status" "$port"
        fi
    done

    echo ""
}

# 显示端口映射
show_port_mappings() {
    if [ "$SHOW_PORTS" = false ]; then
        return
    fi

    echo -e "${BOLD}端口映射:${NC}"

    local port_info=$(docker ps --filter "name=one-data" --format "{{.Names}}\t{{.Ports}}" 2>/dev/null)

    if [ -n "$port_info" ]; then
        echo "$port_info" | while IFS=$'\t' read -r name ports; do
            if [ -n "$ports" ]; then
                echo "  $name:"
                echo "$ports" | tr ',' '\n' | while read port_line; do
                    echo "    $port_line"
                done
            fi
        done
    else
        echo "  无运行中的容器"
    fi

    echo ""
}

# 显示健康检查状态
show_health_status() {
    if [ "$SHOW_HEALTH" = false ]; then
        return
    fi

    echo -e "${BOLD}健康检查:${NC}"

    local healthy=0
    local unhealthy=0
    local no_check=0

    for service in $ALL_SERVICES; do
        local status=$(get_service_status "$service")

        case $status in
            healthy)
                healthy=$((healthy + 1))
                ;;
            unhealthy)
                unhealthy=$((unhealthy + 1))
                log_warn "  $service: 不健康"
                ;;
            running)
                no_check=$((no_check + 1))
                ;;
        esac
    done

    echo "  健康: $healthy  |  不健康: $unhealthy  |  无检查: $no_check"
    echo ""
}

# 显示资源使用汇总
show_resource_summary() {
    if [ "$VERBOSE" = false ]; then
        return
    fi

    echo -e "${BOLD}资源使用汇总:${NC}"

    local total_cpu=0
    local total_mem=0

    docker stats --no-stream --format "{{.CPUPerc}}" $(docker ps --filter "name=one-data" -q 2>/dev/null) 2>/dev/null | while read cpu; do
        cpu_num=$(echo "$cpu" | tr -d '%')
        total_cpu=$(echo "$total_cpu + $cpu_num" | bc 2>/dev/null || echo "$total_cpu")
    done

    # 获取容器数量
    local container_count=$(docker ps --filter "name=one-data" -q 2>/dev/null | wc -l | tr -d ' ')

    echo "  运行容器数: $container_count"
    echo ""
}

# JSON 格式输出
show_json_status() {
    local json_output='{"services":['
    local first=true

    for service in $ALL_SERVICES; do
        local status=$(get_service_status "$service")
        local port=$(get_service_port "$service")
        if [ -z "$port" ]; then
            port="null"
        fi
        local container_name=$(get_container_name "$service")

        if [ "$first" = true ]; then
            first=false
        else
            json_output="$json_output,"
        fi

        json_output="$json_output{\"name\":\"$service\",\"status\":\"$status\",\"port\":$port,\"container\":\"$container_name\"}"
    done

    json_output="$json_output]}"
    echo "$json_output" | python3 -m json.tool 2>/dev/null || echo "$json_output"
}

# 显示所有状态
show_all_status() {
    if [ "$JSON_OUTPUT" = true ]; then
        show_json_status
        return
    fi

    clear 2>/dev/null || true

    print_header "ONE-DATA-STUDIO 开发环境状态"

    echo -e "时间: $(date '+%Y-%m-%d %H:%M:%S')"

    show_status_table
    show_health_status

    if [ "$VERBOSE" = true ]; then
        show_resource_summary
    fi

    show_port_mappings
}

# ==================== 主函数 ====================

main() {
    # 检查 Docker
    if ! check_docker; then
        exit 1
    fi

    if [ "$WATCH_MODE" = true ]; then
        log_info "进入监控模式 (Ctrl+C 退出)"
        while true; do
            show_all_status
            sleep "$WATCH_INTERVAL"
        done
    else
        show_all_status
    fi
}

main
