#!/bin/bash
# ONE-DATA-STUDIO 回滚脚本
# Sprint 10: 部署自动化
#
# 使用方法:
#   ./deploy/scripts/rollback.sh [version] [environment]
#
# 参数:
#   version    - 要回滚到的版本（可选，默认回滚到上一个版本）
#   environment - 环境名称 (dev|staging|prod，默认 dev)

set -e

# ==================== 配置 ====================

ENVIRONMENT=${2:-dev}
VERSION=${1:-}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BACKUP_DIR="$PROJECT_ROOT/deploy/backups"
COMPOSE_FILE="$PROJECT_ROOT/deploy/docker-compose.yml"

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

# ==================== 备份函数 ====================

create_backup() {
    local backup_name="$1"
    local backup_path="$BACKUP_DIR/$backup_name"

    log_step "创建部署备份: $backup_name"

    mkdir -p "$backup_path"

    # 备份环境配置
    if [ -f "$PROJECT_ROOT/deploy/.env.$ENVIRONMENT" ]; then
        cp "$PROJECT_ROOT/deploy/.env.$ENVIRONMENT" "$backup_path/.env"
    fi

    # 备份数据库（如果启用了）
    if docker-compose ps | grep -q mysql; then
        log_info "备份数据库..."
        docker-compose exec -T mysql mysqldump -u root -p"${MYSQL_PASSWORD}" \
            --all-databases > "$backup_path/database.sql" 2>/dev/null || true
    fi

    # 记录当前容器镜像版本
    docker-compose ps | grep -oP '(\S+)\s+\S+\s+"\K[^"]+' \
        > "$backup_path/versions.txt" 2>/dev/null || true

    log_info "✓ 备份完成: $backup_path"
}

list_backups() {
    log_step "可用的备份列表:"

    if [ ! -d "$BACKUP_DIR" ]; then
        log_warn "没有找到备份目录"
        return 1
    fi

    local backups=($(ls -t "$BACKUP_DIR" 2>/dev/null || echo ""))

    if [ ${#backups[@]} -eq 0 ]; then
        log_warn "没有可用的备份"
        return 1
    fi

    for i in "${!backups[@]}"; do
        local backup="${backups[$i]}"
        local timestamp=$(stat -c %y "$BACKUP_DIR/$backup" 2>/dev/null || echo "未知")
        printf "  [%d] %s (创建时间: %s)\n" "$i" "$backup" "$timestamp"
    done

    return 0
}

# ==================== 回滚函数 ====================

rollback_to_backup() {
    local backup_name=$1
    local backup_path="$BACKUP_DIR/$backup_name"

    log_step "回滚到备份: $backup_name"

    if [ ! -d "$backup_path" ]; then
        log_error "备份不存在: $backup_path"
        return 1
    fi

    # 恢复环境配置
    if [ -f "$backup_path/.env" ]; then
        log_info "恢复环境配置..."
        cp "$backup_path/.env" "$PROJECT_ROOT/deploy/.env.$ENVIRONMENT"
    fi

    # 恢复数据库
    if [ -f "$backup_path/database.sql" ]; then
        log_info "恢复数据库..."
        docker-compose exec -T mysql mysql -u root -p"${MYSQL_PASSWORD}" \
            < "$backup_path/database.sql" 2>/dev/null || true
    fi

    # 重启服务
    log_info "重启服务..."
    cd "$PROJECT_ROOT/deploy"
    docker-compose down
    docker-compose up -d

    # 等待服务就绪
    sleep 10

    log_info "✓ 回滚完成"
}

rollback_to_version() {
    local target_version=$1

    log_step "回滚到版本: $target_version"

    # 获取当前版本
    local current_version=$(git -C "$PROJECT_ROOT" rev-parse --short HEAD 2>/dev/null || echo "unknown")

    log_info "当前版本: $current_version"

    # 检查版本是否存在
    if ! git -C "$PROJECT_ROOT" rev-parse "$target_version" &>/dev/null; then
        log_error "版本不存在: $target_version"
        return 1
    fi

    # 创建当前状态的备份
    local backup_name="pre-rollback-$(date +%Y%m%d-%H%M%S)"
    create_backup "$backup_name"

    # 切换到目标版本
    log_info "切换代码到版本 $target_version..."
    git -C "$PROJECT_ROOT" checkout "$target_version"

    # 重新构建和部署
    log_info "重新构建和部署..."
    cd "$PROJECT_ROOT/deploy"
    docker-compose down
    docker-compose build
    docker-compose up -d

    # 等待服务就绪
    sleep 15

    log_info "✓ 已回滚到版本: $target_version"
}

rollback_to_previous() {
    log_step "回滚到上一个版本"

    # 获取上一个版本
    local previous_version=$(git -C "$PROJECT_ROOT" rev-parse --short HEAD^ 2>/dev/null || echo "")

    if [ -z "$previous_version" ]; then
        log_error "无法获取上一个版本"
        return 1
    fi

    rollback_to_version "$previous_version"
}

# ==================== 蓝绿部署回滚 ====================

blue_green_rollback() {
    local active_color=$1

    log_step "蓝绿部署回滚: 当前激活 $active_color 环境"

    # 获取另一个环境颜色
    local target_color="blue"
    if [ "$active_color" = "blue" ]; then
        target_color="green"
    fi

    log_info "切换到 $target_color 环境..."

    # 更新负载均衡器配置
    # 这里需要根据实际负载均衡器进行调整
    # 例如 Nginx、Traefik 或云负载均衡器

    log_info "✓ 已切换到 $target_color 环境"
}

# ==================== 确认函数 ====================

confirm_rollback() {
    local message=$1

    echo ""
    read -p "$(echo -e ${YELLOW}是否确认回滚? $message (y/N): ${NC})" -n 1 -r
    echo

    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "回滚已取消"
        exit 0
    fi
}

# ==================== 主函数 ====================

main() {
    echo ""
    echo "========================================"
    echo "ONE-DATA-STUDIO 回滚脚本"
    echo "========================================"
    echo "环境: $ENVIRONMENT"
    echo "========================================"
    echo ""

    # 如果没有指定版本，显示备份列表让用户选择
    if [ -z "$VERSION" ]; then
        if list_backups; then
            echo ""
            read -p "请输入要回滚到的备份编号 (或按 Ctrl+C 取消): " backup_index

            local backups=($(ls -t "$BACKUP_DIR" 2>/dev/null))
            local selected_backup="${backups[$backup_index]}"

            if [ -n "$selected_backup" ]; then
                confirm_rollback "回滚到备份: $selected_backup"
                create_backup "pre-rollback-$(date +%Y%m%d-%H%M%S)"
                rollback_to_backup "$selected_backup"
            else
                log_error "无效的备份编号"
                exit 1
            fi
        else
            # 没有备份，尝试回滚到上一个 git 版本
            confirm_rollback "回滚到上一个代码版本"
            rollback_to_previous
        fi
    elif [ "$VERSION" = "previous" ]; then
        confirm_rollback "回滚到上一个代码版本"
        rollback_to_previous
    elif [[ "$VERSION" =~ ^[a-f0-9]+$ ]]; then
        # 回滚到 git 版本
        confirm_rollback "回滚到版本: $VERSION"
        rollback_to_version "$VERSION"
    else
        # 回滚到命名备份
        confirm_rollback "回滚到备份: $VERSION"
        create_backup "pre-rollback-$(date +%Y%m%d-%H%M%S)"
        rollback_to_backup "$VERSION"
    fi

    echo ""
    echo "========================================"
    echo "回滚完成"
    echo "========================================"
    echo ""
    echo "请验证服务状态:"
    echo "  docker-compose ps"
    echo "  docker-compose logs -f [service]"
    echo ""
}

# 执行主函数
main "$@"
