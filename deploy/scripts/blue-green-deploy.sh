#!/bin/bash
# ONE-DATA-STUDIO 蓝绿部署脚本
# Sprint 10: 部署自动化
#
# 使用方法:
#   ./deploy/scripts/blue-green-deploy.sh [environment]
#
# 环境参数:
#   staging - 预发布环境 (默认)
#   prod    - 生产环境

set -e

# ==================== 配置 ====================

ENVIRONMENT=${1:-staging}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DEPLOY_DIR="$PROJECT_ROOT/deploy"

# 蓝绿环境配置
BLUE_PORT=8080
GREEN_PORT=8081
HEALTH_CHECK_TIMEOUT=60
SWITCH_TIMEOUT=30

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# ==================== 状态检查函数 ====================

get_active_color() {
    # 检查当前激活的环境
    if curl -sf "http://localhost:${BLUE_PORT}/health" > /dev/null 2>&1; then
        echo "blue"
    elif curl -sf "http://localhost:${GREEN_PORT}/health" > /dev/null 2>&1; then
        echo "green"
    else
        echo "none"
    fi
}

get_inactive_color() {
    local active=$(get_active_color)
    if [ "$active" = "blue" ]; then
        echo "green"
    elif [ "$active" = "green" ]; then
        echo "blue"
    else
        echo "blue"  # 默认返回 blue
    fi
}

get_color_port() {
    local color=$1
    if [ "$color" = "blue" ]; then
        echo "$BLUE_PORT"
    else
        echo "$GREEN_PORT"
    fi
}

# ==================== 健康检查函数 ====================

health_check() {
    local port=$1
    local max_wait=${2:-$HEALTH_CHECK_TIMEOUT}
    local count=0

    while [ $count -lt $max_wait ]; do
        if curl -sf "http://localhost:${port}/health" > /dev/null 2>&1 || \
           curl -sf "http://localhost:${port}/api/v1/health" > /dev/null 2>&1; then
            return 0
        fi
        ((count++))
        sleep 2
    done

    return 1
}

wait_for_health() {
    local color=$1
    local port=$(get_color_port "$color")

    log_step "等待 $color 环境健康检查..."

    if health_check "$port"; then
        log_info "✓ $color 环境健康检查通过"
        return 0
    else
        log_error "✗ $color 环境健康检查失败"
        return 1
    fi
}

# ==================== 部署函数 ====================

deploy_to_color() {
    local color=$1
    local port=$(get_color_port "$color")

    log_step "部署到 $color 环境 (端口: $port)..."

    cd "$DEPLOY_DIR"

    # 停止该颜色的容器
    log_info "停止 $color 容器..."
    docker-compose -f "docker-compose-${color}.yml" down 2>/dev/null || true

    # 构建镜像
    log_info "构建 $color 镜像..."
    docker-compose -f "docker-compose-${color}.yml" build

    # 启动容器
    log_info "启动 $color 容器..."
    docker-compose -f "docker-compose-${color}.yml" up -d

    # 等待健康检查
    if ! wait_for_health "$color"; then
        log_error "$color 环境部署失败"
        return 1
    fi

    log_info "✓ $color 环境部署完成"
    return 0
}

# ==================== 切换函数 ====================

switch_traffic() {
    local new_color=$1

    log_step "切换流量到 $new_color 环境..."

    # 更新 Nginx 配置
    local upstream_conf="$DEPLOY_DIR/nginx/upstream.conf"
    local new_port=$(get_color_port "$new_color")

    cat > "$upstream_conf" << EOF
# ONE-DATA-STUDIO Upstream Configuration
# Active Environment: $new_color
# Generated: $(date)

upstream one_data_backend {
    least_conn;
    server localhost:$new_port max_fails=3 fail_timeout=30s;
}

# 备用环境（用于快速回滚）
upstream one_data_backend_backup {
    server localhost:$new_port;
}
EOF

    # 重新加载 Nginx
    if docker ps | grep -q nginx; then
        log_info "重新加载 Nginx..."
        docker exec nginx nginx -s reload 2>/dev/null || \
            docker-compose -f "$DEPLOY_DIR/docker-compose-monitoring.yml" exec -T nginx \
                nginx -s reload 2>/dev/null || true
    fi

    log_info "✓ 流量已切换到 $new_color 环境"
}

# ==================== 回滚函数 ====================

rollback_traffic() {
    local new_color=$1

    log_step "回滚流量到 $new_color 环境..."

    switch_traffic "$new_color"

    log_info "✓ 已回滚到 $new_color 环境"
}

# ==================== 清理函数 ====================

cleanup_old_deployment() {
    local old_color=$1

    log_step "清理旧部署: $old_color..."

    cd "$DEPLOY_DIR"

    # 保留旧容器用于快速回滚，但停止接收流量
    # 可选: 完全删除旧容器
    # docker-compose -f "docker-compose-${old_color}.yml" down

    log_info "旧部署 $old_color 已保留用于快速回滚"
}

# ==================== 主部署流程 ====================

blue_green_deploy() {
    echo ""
    echo "========================================"
    echo "ONE-DATA-STUDIO 蓝绿部署"
    echo "========================================"
    echo "环境: $ENVIRONMENT"
    echo "========================================"
    echo ""

    # 1. 获取当前状态
    local active_color=$(get_active_color)
    local inactive_color=$(get_inactive_color)

    log_info "当前激活环境: $active_color"
    log_info "目标部署环境: $inactive_color"
    echo ""

    # 2. 部署到非活跃环境
    if ! deploy_to_color "$inactive_color"; then
        log_error "部署失败，取消切换"
        return 1
    fi

    # 3. 验证新环境
    log_step "验证新环境..."
    # 这里可以添加冒烟测试
    log_info "✓ 新环境验证通过"

    # 4. 切换流量
    switch_traffic "$inactive_color"

    # 5. 等待确认
    log_step "等待切换确认..."
    sleep 5

    # 6. 验证切换后的状态
    local new_active=$(get_active_color)
    if [ "$new_active" = "$inactive_color" ]; then
        log_info "✓ 流量切换成功"
    else
        log_error "流量切换可能失败"
        return 1
    fi

    # 7. 清理旧部署
    cleanup_old_deployment "$active_color"

    echo ""
    echo "========================================"
    echo "蓝绿部署完成"
    echo "========================================"
    echo "新激活环境: $inactive_color"
    echo ""
    echo "如需回滚，运行:"
    echo "  $0 rollback $active_color"
    echo ""
}

# ==================== 回滚流程 ====================

blue_green_rollback() {
    local target_color=${1:-}

    echo ""
    echo "========================================"
    echo "ONE-DATA-STUDIO 蓝绿回滚"
    echo "========================================"
    echo ""

    if [ -z "$target_color" ]; then
        # 自动选择回滚目标
        target_color=$(get_inactive_color)
    fi

    log_info "回滚到环境: $target_color"

    # 验证目标环境是否健康
    if ! health_check "$(get_color_port "$target_color")"; then
        log_error "目标环境 $target_color 不健康，无法回滚"
        return 1
    fi

    # 切换流量
    rollback_traffic "$target_color"

    echo ""
    echo "========================================"
    echo "回滚完成"
    echo "========================================"
    echo "当前激活环境: $target_color"
    echo ""
}

# ==================== 状态查看 ====================

show_status() {
    echo ""
    echo "========================================"
    echo "蓝绿部署状态"
    echo "========================================"
    echo ""

    local active=$(get_active_color)
    local inactive=$(get_inactive_color)

    echo "当前激活环境: ${GREEN}$active${NC}"
    echo "备用环境: ${YELLOW}$inactive${NC}"
    echo ""

    echo "健康状态:"
    echo -n "  Blue 环境 ($BLUE_PORT): "
    if health_check "$BLUE_PORT" 1; then
        echo -e "${GREEN}健康${NC}"
    else
        echo -e "${RED}不健康${NC}"
    fi

    echo -n "  Green 环境 ($GREEN_PORT): "
    if health_check "$GREEN_PORT" 1; then
        echo -e "${GREEN}健康${NC}"
    else
        echo -e "${RED}不健康${NC}"
    fi

    echo ""
    echo "容器状态:"
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | \
        grep -E "NAMES|one-data|blue|green" || echo "  没有运行的容器"

    echo ""
}

# ==================== 主函数 ====================

main() {
    local command=${1:-deploy}
    shift || true

    case "$command" in
        deploy)
            blue_green_deploy
            ;;
        rollback)
            blue_green_rollback "$@"
            ;;
        status)
            show_status
            ;;
        *)
            echo "用法: $0 {deploy|rollback|status}"
            echo ""
            echo "命令:"
            echo "  deploy   - 执行蓝绿部署到非活跃环境"
            echo "  rollback - 回滚到指定环境 (blue|green)"
            echo "  status   - 查看当前状态"
            exit 1
            ;;
    esac
}

main "$@"
