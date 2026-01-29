#!/bin/bash
# ONE-DATA-STUDIO 开发环境数据库操作脚本
#
# 使用方法:
#   ./scripts/dev/dev-db.sh <命令> [选项]
#
# 命令:
#   mysql    - 连接 MySQL 数据库
#   redis    - 连接 Redis 数据库
#   backup   - 备份数据库
#   restore  - 恢复数据库
#   migrate  - 运行数据库迁移
#   reset    - 重置数据库
#   status   - 显示数据库状态

set -e

# 加载共享函数库
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

# ==================== 默认配置 ====================

COMMAND=""
SQL_QUERY=""
SQL_FILE=""
BACKUP_FILE=""
DATABASE_NAME="${MYSQL_DATABASE:-onedata}"
REDIS_DB=0

# ==================== 解析参数 ====================

show_db_help() {
    show_help \
        "ONE-DATA-STUDIO 开发环境数据库操作脚本" \
        "dev-db.sh <命令> [选项]" \
        "命令:
  mysql              连接 MySQL 交互式 Shell
  redis              连接 Redis 交互式 Shell
  backup             备份数据库
  restore            恢复数据库
  migrate            运行数据库迁移
  reset              重置数据库（危险）
  status             显示数据库状态

MySQL 选项:
  -e, --execute SQL  执行 SQL 语句
  -f, --file FILE    执行 SQL 文件
  -d, --database DB  指定数据库（默认: onedata）

Redis 选项:
  -n, --db N         指定 Redis 数据库编号（默认: 0）

备份/恢复选项:
  -o, --output FILE  备份输出文件
  -i, --input FILE   恢复输入文件
  --compress         压缩备份文件" \
        "  dev-db.sh mysql                    # 连接 MySQL
  dev-db.sh mysql -e 'SHOW TABLES'   # 执行 SQL
  dev-db.sh mysql -f init.sql        # 执行 SQL 文件
  dev-db.sh redis                    # 连接 Redis
  dev-db.sh backup                   # 备份数据库
  dev-db.sh backup -o mybackup.sql   # 指定备份文件
  dev-db.sh restore -i backup.sql    # 恢复数据库
  dev-db.sh status                   # 显示状态
  dev-db.sh reset                    # 重置数据库"
}

# 获取命令
if [ $# -gt 0 ]; then
    COMMAND=$1
    shift
fi

# 解析命令特定参数
while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--execute)
            SQL_QUERY="$2"
            shift 2
            ;;
        -f|--file)
            SQL_FILE="$2"
            shift 2
            ;;
        -d|--database)
            DATABASE_NAME="$2"
            shift 2
            ;;
        -n|--db)
            REDIS_DB="$2"
            shift 2
            ;;
        -o|--output)
            BACKUP_FILE="$2"
            shift 2
            ;;
        -i|--input)
            BACKUP_FILE="$2"
            shift 2
            ;;
        --compress)
            COMPRESS=true
            shift
            ;;
        -h|--help)
            show_db_help
            exit 0
            ;;
        -*)
            log_error "未知选项: $1"
            show_db_help
            exit 1
            ;;
        *)
            shift
            ;;
    esac
done

# ==================== MySQL 操作 ====================

# 获取 MySQL 连接参数
get_mysql_env() {
    load_env 2>/dev/null || true

    MYSQL_HOST=${MYSQL_HOST:-localhost}
    MYSQL_PORT=${MYSQL_PORT:-3306}
    MYSQL_USER=${MYSQL_USER:-onedata}
    MYSQL_PASSWORD=${MYSQL_PASSWORD:-}
    MYSQL_ROOT_PASSWORD=${MYSQL_ROOT_PASSWORD:-}
}

# 连接 MySQL
mysql_connect() {
    get_mysql_env

    local container_name=$(get_container_name "mysql")

    if ! is_service_running "mysql"; then
        log_error "MySQL 服务未运行"
        exit 1
    fi

    if [ -n "$SQL_QUERY" ]; then
        log_info "执行 SQL: $SQL_QUERY"
        docker exec -i "$container_name" mysql -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" "$DATABASE_NAME" -e "$SQL_QUERY"
    elif [ -n "$SQL_FILE" ]; then
        if [ ! -f "$SQL_FILE" ]; then
            log_error "SQL 文件不存在: $SQL_FILE"
            exit 1
        fi
        log_info "执行 SQL 文件: $SQL_FILE"
        docker exec -i "$container_name" mysql -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" "$DATABASE_NAME" < "$SQL_FILE"
    else
        log_info "连接 MySQL ($DATABASE_NAME)..."
        docker exec -it "$container_name" mysql -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" "$DATABASE_NAME"
    fi
}

# ==================== Redis 操作 ====================

# 连接 Redis
redis_connect() {
    load_env 2>/dev/null || true

    local container_name=$(get_container_name "redis")
    local redis_password="${REDIS_PASSWORD:-}"

    if ! is_service_running "redis"; then
        log_error "Redis 服务未运行"
        exit 1
    fi

    log_info "连接 Redis (DB: $REDIS_DB)..."

    if [ -n "$redis_password" ]; then
        docker exec -it "$container_name" redis-cli -a "$redis_password" -n "$REDIS_DB"
    else
        docker exec -it "$container_name" redis-cli -n "$REDIS_DB"
    fi
}

# ==================== 备份操作 ====================

# 备份数据库
backup_database() {
    get_mysql_env

    local container_name=$(get_container_name "mysql")
    local timestamp=$(date '+%Y%m%d_%H%M%S')

    # 创建备份目录
    mkdir -p "$BACKUP_DIR"

    # 设置备份文件名
    if [ -z "$BACKUP_FILE" ]; then
        BACKUP_FILE="$BACKUP_DIR/mysql_${DATABASE_NAME}_${timestamp}.sql"
    fi

    if ! is_service_running "mysql"; then
        log_error "MySQL 服务未运行"
        exit 1
    fi

    log_step "备份数据库 $DATABASE_NAME..."

    docker exec "$container_name" mysqldump \
        -u"$MYSQL_USER" \
        -p"$MYSQL_PASSWORD" \
        --single-transaction \
        --routines \
        --triggers \
        "$DATABASE_NAME" > "$BACKUP_FILE"

    # 压缩（如果需要）
    if [ "${COMPRESS:-false}" = true ]; then
        gzip "$BACKUP_FILE"
        BACKUP_FILE="${BACKUP_FILE}.gz"
    fi

    local size=$(ls -lh "$BACKUP_FILE" | awk '{print $5}')
    log_success "备份完成: $BACKUP_FILE ($size)"
}

# 恢复数据库
restore_database() {
    get_mysql_env

    local container_name=$(get_container_name "mysql")

    if [ -z "$BACKUP_FILE" ]; then
        log_error "请指定备份文件: -i <file>"
        exit 1
    fi

    if [ ! -f "$BACKUP_FILE" ]; then
        log_error "备份文件不存在: $BACKUP_FILE"
        exit 1
    fi

    if ! is_service_running "mysql"; then
        log_error "MySQL 服务未运行"
        exit 1
    fi

    log_warn "将恢复数据库 $DATABASE_NAME，现有数据将被覆盖！"

    if ! confirm "确认恢复?"; then
        log_info "取消恢复"
        exit 0
    fi

    log_step "恢复数据库 $DATABASE_NAME..."

    # 处理压缩文件
    if [[ "$BACKUP_FILE" == *.gz ]]; then
        gunzip -c "$BACKUP_FILE" | docker exec -i "$container_name" mysql -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" "$DATABASE_NAME"
    else
        docker exec -i "$container_name" mysql -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" "$DATABASE_NAME" < "$BACKUP_FILE"
    fi

    log_success "恢复完成"
}

# ==================== 迁移操作 ====================

# 运行数据库迁移
run_migrations() {
    log_step "运行数据库迁移..."

    # 对各服务执行迁移
    local services="agent-api data-api model-api"

    for service in $services; do
        local container_name=$(get_container_name "$service")

        if is_service_running "$service"; then
            log_info "运行 $service 迁移..."

            docker exec "$container_name" python -c \
                "from models import Base; from database import engine; Base.metadata.create_all(engine)" 2>/dev/null || \
                log_warn "$service 迁移跳过（可能已完成或不需要）"
        else
            log_warn "$service 未运行，跳过迁移"
        fi
    done

    log_success "迁移完成"
}

# ==================== 重置操作 ====================

# 重置数据库
reset_database() {
    get_mysql_env

    local container_name=$(get_container_name "mysql")

    log_warn "此操作将删除数据库 $DATABASE_NAME 中的所有数据！"

    if ! confirm_dangerous "重置数据库" "RESET"; then
        log_info "取消重置"
        exit 0
    fi

    if ! is_service_running "mysql"; then
        log_error "MySQL 服务未运行"
        exit 1
    fi

    log_step "重置数据库..."

    # 删除并重建数据库
    docker exec "$container_name" mysql -u"root" -p"$MYSQL_ROOT_PASSWORD" -e \
        "DROP DATABASE IF EXISTS $DATABASE_NAME; CREATE DATABASE $DATABASE_NAME CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

    # 重新授权
    docker exec "$container_name" mysql -u"root" -p"$MYSQL_ROOT_PASSWORD" -e \
        "GRANT ALL PRIVILEGES ON $DATABASE_NAME.* TO '$MYSQL_USER'@'%'; FLUSH PRIVILEGES;"

    log_success "数据库已重置"

    # 询问是否运行迁移
    if confirm "是否运行数据库迁移?"; then
        run_migrations
    fi
}

# ==================== 状态显示 ====================

# 显示数据库状态
show_db_status() {
    print_header "数据库状态"

    # MySQL 状态
    echo -e "${BOLD}MySQL:${NC}"
    if is_service_running "mysql"; then
        local container_name=$(get_container_name "mysql")
        get_mysql_env

        echo "  状态: $(get_status_color "healthy")运行中${NC}"
        echo "  端口: $(get_service_port mysql)"

        # 获取数据库列表
        local databases=$(docker exec "$container_name" mysql -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" -N -e "SHOW DATABASES" 2>/dev/null | grep -v "information_schema\|performance_schema\|mysql\|sys")
        echo "  数据库:"
        echo "$databases" | while read db; do
            local tables=$(docker exec "$container_name" mysql -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" -N -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='$db'" 2>/dev/null)
            echo "    - $db ($tables 张表)"
        done

        # 获取连接数
        local connections=$(docker exec "$container_name" mysql -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" -N -e "SHOW STATUS LIKE 'Threads_connected'" 2>/dev/null | awk '{print $2}')
        echo "  当前连接: $connections"
    else
        echo "  状态: $(get_status_color "exited")未运行${NC}"
    fi

    echo ""

    # Redis 状态
    echo -e "${BOLD}Redis:${NC}"
    if is_service_running "redis"; then
        local container_name=$(get_container_name "redis")
        load_env 2>/dev/null || true
        local redis_password="${REDIS_PASSWORD:-}"

        echo "  状态: $(get_status_color "healthy")运行中${NC}"
        echo "  端口: $(get_service_port redis)"

        # 获取 Redis 信息
        local redis_info
        if [ -n "$redis_password" ]; then
            redis_info=$(docker exec "$container_name" redis-cli -a "$redis_password" INFO server 2>/dev/null | grep -E "redis_version|used_memory_human|connected_clients")
        else
            redis_info=$(docker exec "$container_name" redis-cli INFO server 2>/dev/null | grep -E "redis_version|used_memory_human|connected_clients")
        fi

        echo "  版本: $(echo "$redis_info" | grep redis_version | cut -d: -f2 | tr -d '\r')"
        echo "  内存: $(echo "$redis_info" | grep used_memory_human | cut -d: -f2 | tr -d '\r')"
        echo "  客户端: $(echo "$redis_info" | grep connected_clients | cut -d: -f2 | tr -d '\r')"
    else
        echo "  状态: $(get_status_color "exited")未运行${NC}"
    fi

    echo ""

    # Milvus 状态
    echo -e "${BOLD}Milvus (向量数据库):${NC}"
    if is_service_running "milvus"; then
        echo "  状态: $(get_status_color "healthy")运行中${NC}"
        echo "  端口: $(get_service_port milvus)"
    else
        echo "  状态: $(get_status_color "exited")未运行${NC}"
    fi

    echo ""

    # 备份信息
    echo -e "${BOLD}备份目录:${NC}"
    if [ -d "$BACKUP_DIR" ]; then
        local backup_count=$(ls -1 "$BACKUP_DIR"/*.sql* 2>/dev/null | wc -l | tr -d ' ')
        echo "  路径: $BACKUP_DIR"
        echo "  备份数: $backup_count"
        if [ "$backup_count" -gt 0 ]; then
            echo "  最新备份:"
            ls -lt "$BACKUP_DIR"/*.sql* 2>/dev/null | head -3 | while read line; do
                echo "    $line"
            done
        fi
    else
        echo "  路径: $BACKUP_DIR (不存在)"
    fi

    echo ""
}

# ==================== 主函数 ====================

main() {
    # 检查 Docker
    if ! check_docker; then
        exit 1
    fi

    case $COMMAND in
        mysql)
            mysql_connect
            ;;
        redis)
            redis_connect
            ;;
        backup)
            backup_database
            ;;
        restore)
            restore_database
            ;;
        migrate)
            run_migrations
            ;;
        reset)
            reset_database
            ;;
        status)
            show_db_status
            ;;
        "")
            show_db_help
            exit 0
            ;;
        *)
            log_error "未知命令: $COMMAND"
            show_db_help
            exit 1
            ;;
    esac
}

main
