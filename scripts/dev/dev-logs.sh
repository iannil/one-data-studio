#!/bin/bash
# ONE-DATA-STUDIO 开发环境日志查看脚本
#
# 使用方法:
#   ./scripts/dev/dev-logs.sh [选项] [服务...]
#
# 示例:
#   ./scripts/dev/dev-logs.sh              # 查看所有服务日志
#   ./scripts/dev/dev-logs.sh agent-api    # 查看 Agent 服务日志
#   ./scripts/dev/dev-logs.sh -f agent data       # 持续查看 agent 和 data 日志

set -e

# 加载共享函数库
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

# ==================== 默认配置 ====================

FOLLOW=false
TAIL_LINES=100
SINCE=""
UNTIL=""
GREP_PATTERN=""
TIMESTAMPS=false
NO_COLOR=false
SPECIFIC_SERVICES=""

# ==================== 解析参数 ====================

show_logs_help() {
    show_help \
        "ONE-DATA-STUDIO 开发环境日志查看脚本" \
        "dev-logs.sh [选项] [服务...]" \
        "  -f, --follow       持续输出日志
  -t, --tail N       显示最后 N 行（默认: 100）
  --since TIME       显示指定时间之后的日志（如: 10m, 1h, 2023-01-01）
  --until TIME       显示指定时间之前的日志
  -g, --grep PATTERN 过滤包含指定模式的日志
  --timestamps       显示时间戳
  --no-color         禁用颜色输出
  -h, --help         显示帮助信息

服务别名:
  o, openai      = openai-proxy
  w, web         = web-frontend
  m, db, mysql   = mysql
  r, redis       = redis" \
        "  dev-logs.sh              # 查看所有服务最近 100 行日志
  dev-logs.sh -f           # 持续查看所有日志
  dev-logs.sh agent        # 查看 agent-api 日志
  dev-logs.sh -f agent data       # 持续查看 agent 和 data 日志
  dev-logs.sh -t 50 mysql  # 查看 MySQL 最后 50 行
  dev-logs.sh --since 10m  # 查看最近 10 分钟的日志
  dev-logs.sh -g ERROR     # 过滤包含 ERROR 的日志"
}

while [[ $# -gt 0 ]]; do
    case $1 in
        -f|--follow)
            FOLLOW=true
            shift
            ;;
        -t|--tail)
            TAIL_LINES="$2"
            shift 2
            ;;
        --since)
            SINCE="$2"
            shift 2
            ;;
        --until)
            UNTIL="$2"
            shift 2
            ;;
        -g|--grep)
            GREP_PATTERN="$2"
            shift 2
            ;;
        --timestamps)
            TIMESTAMPS=true
            shift
            ;;
        --no-color)
            NO_COLOR=true
            shift
            ;;
        -h|--help)
            show_logs_help
            exit 0
            ;;
        -*)
            log_error "未知选项: $1"
            show_logs_help
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

# ==================== 日志查看函数 ====================

# 构建 docker-compose logs 参数
build_logs_args() {
    local args=""

    if [ "$FOLLOW" = true ]; then
        args="--follow"
    fi

    if [ -n "$TAIL_LINES" ]; then
        args="$args --tail $TAIL_LINES"
    fi

    if [ -n "$SINCE" ]; then
        args="$args --since $SINCE"
    fi

    if [ -n "$UNTIL" ]; then
        args="$args --until $UNTIL"
    fi

    if [ "$TIMESTAMPS" = true ]; then
        args="$args --timestamps"
    fi

    if [ "$NO_COLOR" = true ]; then
        args="$args --no-color"
    fi

    echo "$args"
}

# 高亮日志输出
highlight_logs() {
    if [ "$NO_COLOR" = true ]; then
        cat
    else
        # 高亮 ERROR, WARN, INFO 等关键字
        sed -E \
            -e "s/(ERROR|FATAL|CRITICAL)/$(printf '\033[31m')\1$(printf '\033[0m')/g" \
            -e "s/(WARN|WARNING)/$(printf '\033[33m')\1$(printf '\033[0m')/g" \
            -e "s/(INFO)/$(printf '\033[32m')\1$(printf '\033[0m')/g" \
            -e "s/(DEBUG)/$(printf '\033[36m')\1$(printf '\033[0m')/g"
    fi
}

# 过滤日志
filter_logs() {
    if [ -n "$GREP_PATTERN" ]; then
        grep -i --color=auto "$GREP_PATTERN" || true
    else
        cat
    fi
}

# 查看日志
view_logs() {
    local services="$1"
    local logs_args=$(build_logs_args)

    # 检查 compose 文件
    if [ ! -f "$COMPOSE_FILE" ]; then
        log_error "Docker Compose 文件不存在: $COMPOSE_FILE"
        exit 1
    fi

    # 如果没有指定服务，显示服务选择提示
    if [ -z "$services" ]; then
        log_info "查看所有服务日志"
    else
        log_info "查看服务日志: $services"
    fi

    echo ""

    # 执行日志查看
    if [ -n "$services" ]; then
        if [ -n "$GREP_PATTERN" ]; then
            docker-compose -f "$COMPOSE_FILE" logs $logs_args $services 2>&1 | filter_logs | highlight_logs
        else
            docker-compose -f "$COMPOSE_FILE" logs $logs_args $services 2>&1 | highlight_logs
        fi
    else
        if [ -n "$GREP_PATTERN" ]; then
            docker-compose -f "$COMPOSE_FILE" logs $logs_args 2>&1 | filter_logs | highlight_logs
        else
            docker-compose -f "$COMPOSE_FILE" logs $logs_args 2>&1 | highlight_logs
        fi
    fi
}

# 交互式服务选择
select_service_interactive() {
    echo -e "${BOLD}请选择要查看的服务:${NC}"
    echo ""

    local i=1

    for service in $ALL_SERVICES; do
        local status=$(get_service_status "$service")
        local color=$(get_status_color "$status")
        printf "  %2d) %-20s ${color}[%s]${NC}\n" "$i" "$service" "$status"
        i=$((i + 1))
    done

    echo ""
    echo "   0) 所有服务"
    echo ""

    read -p "请输入服务编号 (多个用空格分隔): " input

    if [ "$input" = "0" ]; then
        SPECIFIC_SERVICES=""
    else
        local services_array=""
        for service in $ALL_SERVICES; do
            services_array="$services_array $service"
        done

        for num in $input; do
            if [ "$num" -ge 1 ] 2>/dev/null; then
                local selected=$(echo $services_array | cut -d' ' -f$((num + 1)))
                if [ -n "$selected" ]; then
                    if [ -z "$SPECIFIC_SERVICES" ]; then
                        SPECIFIC_SERVICES="$selected"
                    else
                        SPECIFIC_SERVICES="$SPECIFIC_SERVICES $selected"
                    fi
                fi
            fi
        done
    fi
}

# ==================== 主函数 ====================

main() {
    # 检查 Docker
    if ! check_docker; then
        exit 1
    fi

    # 查看日志
    view_logs "$SPECIFIC_SERVICES"
}

main
