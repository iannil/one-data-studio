#!/bin/bash
# ONE-DATA-STUDIO 开发环境容器 Shell 访问脚本
#
# 使用方法:
#   ./scripts/dev/dev-shell.sh [选项] <服务>
#
# 示例:
#   ./scripts/dev/dev-shell.sh bisheng    # 进入 bisheng-api 容器
#   ./scripts/dev/dev-shell.sh b          # 使用别名
#   ./scripts/dev/dev-shell.sh -s python b # 使用 Python shell

set -e

# 加载共享函数库
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

# ==================== 默认配置 ====================

SERVICE=""
SHELL_CMD=""
USER=""
WORKDIR=""

# ==================== 解析参数 ====================

show_shell_help() {
    show_help \
        "ONE-DATA-STUDIO 开发环境容器 Shell 访问脚本" \
        "dev-shell.sh [选项] <服务>" \
        "  -s, --shell CMD   指定 shell 类型（bash, sh, python, ipython, node）
  -u, --user USER   指定用户
  -w, --workdir DIR 指定工作目录
  -h, --help        显示帮助信息

服务别名:
  b, bisheng     = bisheng-api
  a, alldata     = alldata-api
  c, cube        = cube-api
  o, openai      = openai-proxy
  w, web         = web-frontend
  m, db, mysql   = mysql
  r, redis       = redis" \
        "  dev-shell.sh bisheng         # 进入 bisheng-api（bash）
  dev-shell.sh b               # 使用别名
  dev-shell.sh -s python b     # 进入 Python shell
  dev-shell.sh -s ipython b    # 进入 IPython shell
  dev-shell.sh mysql           # 进入 MySQL 容器
  dev-shell.sh -u root mysql   # 以 root 用户进入"
}

while [[ $# -gt 0 ]]; do
    case $1 in
        -s|--shell)
            SHELL_CMD="$2"
            shift 2
            ;;
        -u|--user)
            USER="$2"
            shift 2
            ;;
        -w|--workdir)
            WORKDIR="$2"
            shift 2
            ;;
        -h|--help)
            show_shell_help
            exit 0
            ;;
        -*)
            log_error "未知选项: $1"
            show_shell_help
            exit 1
            ;;
        *)
            if [ -z "$SERVICE" ]; then
                SERVICE=$(resolve_service_alias "$1")
            fi
            shift
            ;;
    esac
done

# ==================== Shell 访问函数 ====================

# 检测容器可用的 shell
detect_shell() {
    local container=$1

    # 尝试 bash
    if docker exec "$container" which bash &>/dev/null; then
        echo "bash"
        return
    fi

    # 尝试 sh
    if docker exec "$container" which sh &>/dev/null; then
        echo "sh"
        return
    fi

    log_error "无法检测到可用的 shell"
    exit 1
}

# 获取特定 shell 命令
get_shell_command() {
    local shell_type=$1

    case $shell_type in
        bash|sh)
            echo "$shell_type"
            ;;
        python|python3)
            echo "python3"
            ;;
        ipython)
            echo "ipython"
            ;;
        node)
            echo "node"
            ;;
        mysql)
            load_env 2>/dev/null || true
            echo "mysql -u${MYSQL_USER:-onedata} -p${MYSQL_PASSWORD:-}"
            ;;
        redis)
            load_env 2>/dev/null || true
            if [ -n "${REDIS_PASSWORD:-}" ]; then
                echo "redis-cli -a $REDIS_PASSWORD"
            else
                echo "redis-cli"
            fi
            ;;
        *)
            echo "$shell_type"
            ;;
    esac
}

# 进入容器 shell
enter_shell() {
    local service=$1
    local container_name=$(get_container_name "$service")

    # 检查服务是否运行
    if ! is_service_running "$service"; then
        log_error "服务 $service 未运行"
        log_info "使用 'make dev-start $service' 启动服务"
        exit 1
    fi

    # 确定 shell 命令
    local shell_cmd
    if [ -n "$SHELL_CMD" ]; then
        shell_cmd=$(get_shell_command "$SHELL_CMD")
    else
        # 根据服务类型选择默认 shell
        case $service in
            mysql)
                shell_cmd=$(get_shell_command "mysql")
                ;;
            redis)
                shell_cmd=$(get_shell_command "redis")
                ;;
            *)
                shell_cmd=$(detect_shell "$container_name")
                ;;
        esac
    fi

    # 构建 docker exec 参数
    local exec_args="-it"

    if [ -n "$USER" ]; then
        exec_args="$exec_args -u $USER"
    fi

    if [ -n "$WORKDIR" ]; then
        exec_args="$exec_args -w $WORKDIR"
    fi

    log_info "进入 $service 容器 ($container_name)"
    log_info "Shell: $shell_cmd"
    echo ""

    # 执行
    docker exec $exec_args "$container_name" $shell_cmd
}

# 显示服务选择菜单
select_service() {
    echo -e "${BOLD}请选择要进入的服务:${NC}"
    echo ""

    local running_services=""
    local i=1

    for service in $ALL_SERVICES; do
        if is_service_running "$service"; then
            running_services="$running_services $service"
            printf "  %2d) %s\n" "$i" "$service"
            i=$((i + 1))
        fi
    done

    local service_count=$((i - 1))

    if [ $service_count -eq 0 ]; then
        log_error "没有运行中的服务"
        log_info "使用 'make dev-start' 启动服务"
        exit 1
    fi

    echo ""
    read -p "请输入服务编号: " num

    if [ "$num" -ge 1 ] 2>/dev/null && [ "$num" -le "$service_count" ]; then
        SERVICE=$(echo $running_services | cut -d' ' -f$((num + 1)))
    else
        log_error "无效的选择"
        exit 1
    fi
}

# ==================== 主函数 ====================

main() {
    # 检查 Docker
    if ! check_docker; then
        exit 1
    fi

    # 如果没有指定服务，显示选择菜单
    if [ -z "$SERVICE" ]; then
        select_service
    fi

    # 进入 shell
    enter_shell "$SERVICE"
}

main
