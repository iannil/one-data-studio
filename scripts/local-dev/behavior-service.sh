#!/bin/bash
# ONE-DATA-STUDIO 本地开发环境 - 行为分析服务
#
# 使用方法:
#   ./behavior-service.sh start     # 启动行为分析服务
#   ./behavior-service.sh stop      # 停止行为分析服务
#   ./behavior-service.sh restart   # 重启行为分析服务
#   ./behavior-service.sh status    # 查看状态
#   ./behavior-service.sh logs      # 查看日志

set -e

# 加载共享函数
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

SERVICE_NAME="behavior-service"
SERVICE_DIR="$SERVICES_DIR/behavior-service"
SERVICE_PORT=$(get_service_port "behavior-service")

# ==================== 解析参数 ====================

ACTION="${1:-start}"

# ==================== 函数 ====================

check_python_dependencies() {
    log_step "检查 Python 依赖..."

    if ! check_python; then
        exit 1
    fi

    # 检查虚拟环境
    local venv_dir="$SERVICE_DIR/venv"
    if [ ! -d "$venv_dir" ]; then
        log_info "创建 Python 虚拟环境 (使用 Python 3.12)..."
        cd "$SERVICE_DIR"
        $PYTHON_CMD -m venv venv
    fi

    # 检查依赖是否需要安装
    if [ "$SERVICE_DIR/requirements.txt" -nt "$venv_dir" ] 2>/dev/null || \
       [ ! -f "$venv_dir/.installed" ]; then
        log_info "安装 Python 依赖..."
        source "$venv_dir/bin/activate"
        pip install -r "$SERVICE_DIR/requirements.txt"
        touch "$venv_dir/.installed"
    fi

    log_success "依赖检查完成"
}

start_behavior_service() {
    print_header "启动行为分析服务"

    # 检查是否已运行
    if is_service_running "$SERVICE_NAME"; then
        log_warn "行为分析服务已在运行中"
        return 0
    fi

    # 检查端口
    if ! check_port "$SERVICE_PORT" "behavior-service"; then
        log_error "端口 $SERVICE_PORT 已被占用"
        exit 1
    fi

    # 检查依赖
    check_python_dependencies

    # 加载环境变量
    load_env

    # 定义 PID_FILE 和 LOG_FILE
    local PID_FILE=$(get_pid_file "$SERVICE_NAME")
    local LOG_FILE="$LOG_DIR/behavior-service.log"

    # 设置服务特定环境变量
    export PORT="$SERVICE_PORT"
    export DATABASE_URL="${DATABASE_URL:-mysql+pymysql://onedata:dev123@localhost:3306/onedata}"
    export REDIS_URL="${REDIS_URL:-redis://:redisdev123@localhost:6379/1}"

    # 启动服务
    log_info "启动行为分析服务 (端口: $SERVICE_PORT)..."

    cd "$SERVICE_DIR"
    source "$SERVICE_DIR/venv/bin/activate"

    # 后台启动并记录 PID (FastAPI with uvicorn)
    nohup uvicorn app:app --host 0.0.0.0 --port "$SERVICE_PORT" > "$LOG_FILE" 2>&1 &
    local pid=$!
    echo "$pid" > "$PID_FILE"

    # 等待服务启动
    log_info "等待服务启动..."
    if wait_for_service "http://localhost:$SERVICE_PORT/health" "behavior-service" 30; then
        log_success "行为分析服务已启动"
        echo ""
        echo -e "${BOLD}服务地址:${NC} http://localhost:$SERVICE_PORT"
        echo -e "${BOLD}健康检查:${NC} http://localhost:$SERVICE_PORT/health"
        echo -e "${BOLD}API 文档:${NC} http://localhost:$SERVICE_PORT/docs"
        echo -e "${BOLD}日志文件:${NC} $LOG_FILE"
        echo ""
    else
        log_error "行为分析服务启动失败，请查看日志: $LOG_FILE"
        stop_behavior_service
        exit 1
    fi
}

stop_behavior_service() {
    print_header "停止行为分析服务"
    stop_service "$SERVICE_NAME"
}

restart_behavior_service() {
    stop_behavior_service
    sleep 2
    start_behavior_service
}

status_behavior_service() {
    print_header "行为分析服务状态"

    local PID_FILE=$(get_pid_file "$SERVICE_NAME")
    local LOG_FILE="$LOG_DIR/behavior-service.log"

    if is_service_running "$SERVICE_NAME"; then
        local pid=$(cat "$PID_FILE")
        echo -e "  ${GREEN}✓${NC} 行为分析服务 - 运行中"
        echo "     PID: $pid"
        echo "     端口: $SERVICE_PORT"
        echo "     API: http://localhost:$SERVICE_PORT"
        echo "     日志: $LOG_FILE"
    else
        echo -e "  ${RED}✗${NC} 行为分析服务 - 未运行"
    fi
    echo ""
}

logs_behavior_service() {
    local LOG_FILE="$LOG_DIR/behavior-service.log"
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
            start_behavior_service
            ;;
        stop)
            stop_behavior_service
            ;;
        restart)
            restart_behavior_service
            ;;
        status)
            status_behavior_service
            ;;
        logs)
            logs_behavior_service
            ;;
        *)
            echo "用法: $0 {start|stop|restart|status|logs}"
            exit 1
            ;;
    esac
}

main
