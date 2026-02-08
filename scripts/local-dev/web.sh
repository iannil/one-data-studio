#!/bin/bash
# ONE-DATA-STUDIO 本地开发环境 - Web 前端服务
#
# 使用方法:
#   ./web.sh start     # 启动 Web 前端
#   ./web.sh stop      # 停止 Web 前端
#   ./web.sh restart   # 重启 Web 前端
#   ./web.sh status    # 查看状态
#   ./web.sh logs      # 查看日志

set -e

# 加载共享函数
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

SERVICE_NAME="web"
SERVICE_PORT=$(get_service_port "web")
PID_FILE=$(get_pid_file "$SERVICE_NAME")
LOG_FILE="$LOG_DIR/web.log"

# ==================== 解析参数 ====================

ACTION="${1:-start}"

# ==================== 函数 ====================

check_web_dependencies() {
    log_step "检查 Web 前端依赖..."

    if ! check_node; then
        exit 1
    fi

    # 检查 node_modules
    if [ ! -d "$WEB_DIR/node_modules" ]; then
        log_info "安装 npm 依赖..."
        cd "$WEB_DIR"
        npm install
    fi

    log_success "依赖检查完成"
}

start_web() {
    print_header "启动 Web 前端"

    # 检查是否已运行
    if is_service_running "$SERVICE_NAME"; then
        log_warn "Web 前端已在运行中"
        return 0
    fi

    # 检查端口
    if ! check_port "$SERVICE_PORT" "web"; then
        log_error "端口 $SERVICE_PORT 已被占用，请先停止占用该端口的服务"
        exit 1
    fi

    # 检查依赖
    check_web_dependencies

    # 加载环境变量（在 load_env 之后重新定义 LOG_FILE）
    load_env
    local LOG_FILE="$LOG_DIR/web.log"
    local PID_FILE=$(get_pid_file "$SERVICE_NAME")

    # 启动服务
    log_info "启动 Web 前端 (端口: $SERVICE_PORT)..."

    cd "$WEB_DIR"

    # 后台启动并记录 PID
    nohup npm run dev > "$LOG_FILE" 2>&1 &
    local pid=$!
    echo "$pid" > "$PID_FILE"

    # 等待服务启动
    log_info "等待服务启动..."
    if wait_for_service "http://localhost:$SERVICE_PORT" "web" 30; then
        log_success "Web 前端已启动"
        echo ""
        echo -e "${BOLD}访问地址:${NC} http://localhost:$SERVICE_PORT"
        echo -e "${BOLD}日志文件:${NC} $LOG_FILE"
        echo ""
    else
        log_error "Web 前端启动失败，请查看日志: $LOG_FILE"
        stop_web
        exit 1
    fi
}

stop_web() {
    print_header "停止 Web 前端"
    stop_service "$SERVICE_NAME"
}

restart_web() {
    stop_web
    sleep 2
    start_web
}

status_web() {
    print_header "Web 前端状态"

    if is_service_running "$SERVICE_NAME"; then
        local pid=$(cat "$PID_FILE")
        echo -e "  ${GREEN}✓${NC} Web 前端 - 运行中"
        echo "     PID: $pid"
        echo "     端口: $SERVICE_PORT"
        echo "     访问: http://localhost:$SERVICE_PORT"
        echo "     日志: $LOG_FILE"
    else
        echo -e "  ${RED}✗${NC} Web 前端 - 未运行"
    fi
    echo ""
}

logs_web() {
    if [ -f "$LOG_FILE" ]; then
        tail -f "$LOG_FILE"
    else
        log_error "日志文件不存在: $LOG_FILE"
        exit 1
    fi
}

# ==================== 主函数 ====================

main() {
    case "$ACTION" in
        start)
            start_web
            ;;
        stop)
            stop_web
            ;;
        restart)
            restart_web
            ;;
        status)
            status_web
            ;;
        logs)
            logs_web
            ;;
        *)
            echo "用法: $0 {start|stop|restart|status|logs}"
            exit 1
            ;;
    esac
}

main
