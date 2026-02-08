#!/bin/bash
# ONE-DATA-STUDIO 本地开发环境 - 基础设施服务管理
#
# 管理运行在 Docker 中的基础设施服务：
#
# 使用方法:
#   ./infrastructure.sh start           # 启动所有基础设施服务
#   ./infrastructure.sh start dataops    # 启动 DataOps 相关服务
#   ./infrastructure.sh start auth       # 启动认证服务
#   ./infrastructure.sh stop            # 停止所有基础设施服务
#   ./infrastructure.sh status          # 查看基础设施服务状态
#   ./infrastructure.sh restart         # 重启基础设施服务
#   ./infrastructure.sh logs <service>  # 查看服务日志

set -e

# 加载共享函数
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

# ==================== 配置 ====================

COMPOSE_FILE="$DEPLOY_DIR/docker-compose.yml"

# 基础数据存储服务 (核心服务)
CORE_INFRA="mysql redis minio etcd"

# AI/ML 相关服务
AI_SERVICES="milvus"

# 认证服务
AUTH_SERVICES="keycloak"

# ETL/工作流服务
ETL_SERVICES="kettle hop-server zookeeper shardingsphere-proxy"

# 数据可视化/分析
ANALYTICS_SERVICES="elasticsearch superset superset-cache"

# 调度服务
SCHEDULER_SERVICES="dolphinscheduler-api dolphinscheduler-postgresql"

# 元数据服务
METADATA_SERVICES="openmetadata openmetadata-postgresql"

# 完整的基础设施列表
ALL_INFRA="$CORE_INFRA $AI_SERVICES $AUTH_SERVICES $ETL_SERVICES $ANALYTICS_SERVICES $SCHEDULER_SERVICES $METADATA_SERVICES"

# DataOps 相关服务组合
DATAOPS_SERVICES="$CORE_INFRA $AI_SERVICES $AUTH_SERVICES $ETL_SERVICES $ANALYTICS_SERVICES $SCHEDULER_SERVICES $METADATA_SERVICES"

# 可以通过环境变量覆盖
COMPOSE_FILES="${COMPOSE_FILES:-$COMPOSE_FILE}"

# ==================== 解析参数 ====================

ACTION="${1:-start}"
SERVICE_FILTER="$2"

# ==================== 函数 ====================

build_compose_cmd() {
    local cmd="docker-compose"

    # 支持多个 compose 文件
    if [[ "$COMPOSE_FILES" == *".yml "* ]]; then
        for file in $COMPOSE_FILES; do
            cmd="$cmd -f $file"
        done
    else
        cmd="$cmd -f $COMPOSE_FILES"
    fi

    echo "$cmd"
}

start_infra() {
    print_header "启动基础设施服务"

    if ! check_docker; then
        exit 1
    fi

    local cmd=$(build_compose_cmd)
    local services=""
    local use_profile=""

    # 根据参数选择服务
    case "$SERVICE_FILTER" in
        dataops)
            services="$DATAOPS_SERVICES"
            use_profile="--profile security"
            log_info "启动 DataOps 基础设施服务"
            ;;
        auth)
            services="$AUTH_SERVICES"
            log_info "启动认证服务"
            ;;
        etl)
            services="$ETL_SERVICES"
            use_profile="--profile security"
            log_info "启动 ETL 服务"
            ;;
        analytics)
            services="$ANALYTICS_SERVICES"
            log_info "启动数据分析服务"
            ;;
        scheduler)
            services="$SCHEDULER_SERVICES"
            log_info "启动调度服务"
            ;;
        metadata)
            services="$METADATA_SERVICES"
            log_info "启动元数据服务"
            ;;
        core|basic)
            services="$CORE_INFRA"
            log_info "启动核心基础设施服务"
            ;;
        all|"")
            services="$ALL_INFRA"
            use_profile="--profile security"
            log_info "启动所有基础设施服务"
            ;;
        *)
            # 允许直接指定服务名
            services="$SERVICE_FILTER"
            use_profile="--profile security"
            log_info "启动服务: $services"
            ;;
    esac

    # 启动服务
    $cmd $use_profile up -d $services

    # 等待服务就绪
    wait_for_infra "$services"

    print_access_info
}

stop_infra() {
    print_header "停止基础设施服务"

    local cmd=$(build_compose_cmd)
    local services=""

    if [ -n "$SERVICE_FILTER" ]; then
        services="$SERVICE_FILTER"
        log_info "停止服务: $services"
        $cmd stop $services
        $cmd rm -f $services
    else
        log_info "停止所有基础设施服务..."
        $cmd --profile security down
    fi

    log_success "基础设施服务已停止"
}

restart_infra() {
    stop_infra
    sleep 2
    start_infra
}

status_infra() {
    print_header "基础设施服务状态"

    local cmd=$(build_compose_cmd)

    echo ""
    $cmd ps
    echo ""

    # 显示健康状态
    echo -e "${BOLD}服务健康检查:${NC}"
    echo ""

    # 核心服务
    show_health mysql 3306
    show_health redis 6379
    show_health minio 9000
    show_health etcd 2379

    # AI 服务
    show_health milvus 19530

    # 认证服务
    show_health keycloak 8080

    # ETL 服务
    show_health kettle 8181
    show_health hop-server 8182
    show_health zookeeper 2181
    show_health shardingsphere-proxy 3307

    # 分析服务
    show_health elasticsearch 9200
    show_health superset 8088
    show_health superset-cache 6380

    # 调度服务
    show_health dolphinscheduler-api 12345
    show_health dolphinscheduler-postgresql 5433

    # 元数据服务
    show_health openmetadata 8585
    show_health openmetadata-postgresql 5434

    echo ""
}

show_health() {
    local service=$1
    local port=$2
    local container_name="one-data-$service"

    if docker ps --format '{{.Names}}' 2>/dev/null | grep -q "^${container_name}$"; then
        local health=$(docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}running{{end}}' "$container_name" 2>/dev/null || echo "unknown")
        if [ "$health" = "healthy" ] || [ "$health" = "running" ]; then
            echo -e "  ${GREEN}✓${NC} $service - $health (端口: $port)"
        else
            echo -e "  ${RED}✗${NC} $service - $health (端口: $port)"
        fi
    else
        echo -e "  ${YELLOW}○${NC} $service - 未运行"
    fi
}

logs_infra() {
    local service="$SERVICE_FILTER"

    if [ -z "$service" ]; then
        log_error "请指定要查看日志的服务名称"
        echo "可用服务: mysql, redis, minio, etcd, milvus, keycloak, kettle, hop-server, zookeeper, shardingsphere-proxy, elasticsearch, superset, dolphinscheduler, openmetadata"
        exit 1
    fi

    local cmd=$(build_compose_cmd)
    $cmd logs -f "$service"
}

wait_for_infra() {
    local services="$1"
    local timeout=120

    log_step "等待基础设施服务就绪..."

    for service in $services; do
        case "$service" in
            mysql)
                log_info "等待 MySQL..."
                local count=0
                while [ $count -lt $timeout ]; do
                    if docker exec one-data-mysql mysqladmin ping -h localhost -uroot -pdev123 &>/dev/null; then
                        log_success "MySQL 已就绪"
                        break
                    fi
                    sleep 2
                    count=$((count + 2))
                done
                ;;
            redis)
                log_info "等待 Redis..."
                local count=0
                while [ $count -lt $timeout ]; do
                    if docker exec one-data-redis redis-cli -a redisdev123 ping 2>&1 | grep -q PONG; then
                        log_success "Redis 已就绪"
                        break
                    fi
                    sleep 1
                    count=$((count + 1))
                done
                ;;
            minio)
                log_info "等待 MinIO..."
                wait_for_service "http://localhost:9000/minio/health/live" "MinIO" 30
                ;;
            elasticsearch)
                log_info "等待 Elasticsearch..."
                wait_for_service "http://localhost:9200/_cluster/health" "Elasticsearch" 60
                ;;
            keycloak)
                log_info "等待 Keycloak..."
                wait_for_service "http://localhost:8080" "Keycloak" 60
                ;;
            openmetadata)
                log_info "等待 OpenMetadata..."
                wait_for_service "http://localhost:8585/api/v1/system/version" "OpenMetadata" 90
                ;;
            dolphinscheduler-api)
                log_info "等待 DolphinScheduler..."
                wait_for_service "http://localhost:12345/dolphinscheduler" "DolphinScheduler" 60 || true
                ;;
            superset)
                log_info "等待 Superset..."
                wait_for_service "http://localhost:8088" "Superset" 60
                ;;
            milvus)
                log_info "等待 Milvus..."
                # Milvus 启动较慢
                sleep 5
                wait_for_service "http://localhost:9091/healthz" "Milvus" 120 || true
                ;;
        esac
    done
}

print_access_info() {
    echo ""
    echo -e "${BOLD}基础设施服务访问信息:${NC}"
    echo ""
    echo "  核心存储:"
    echo "    MySQL:          localhost:3306 (root/dev123)"
    echo "    Redis:          localhost:6379 (密码: redisdev123)"
    echo "    MinIO API:      http://localhost:9000 (minioadmin/minioadmin)"
    echo "    MinIO Console:  http://localhost:9001"
    echo "    ETCD:           localhost:2379"
    echo ""
    echo "  AI/ML 服务:"
    echo "    Milvus:         localhost:19530"
    echo ""
    echo "  认证服务:"
    echo "    Keycloak:       http://localhost:8080 (admin/admin)"
    echo ""
    echo "  ETL 服务:"
    echo "    Kettle:         http://localhost:8181 (cluster/cluster)"
    echo "    Hop Server:     http://localhost:8182"
    echo "    ShardingSphere:  localhost:3307"
    echo ""
    echo "  数据分析:"
    echo "    Elasticsearch:  http://localhost:9200"
    echo "    Superset:       http://localhost:8088 (admin/admin)"
    echo ""
    echo "  调度服务:"
    echo "    DolphinScheduler: http://localhost:12345 (dolphinscheduler/dolphinscheduler)"
    echo ""
    echo "  元数据服务:"
    echo "    OpenMetadata:   http://localhost:8585 (admin/admin)"
    echo ""
}

# ==================== 主函数 ====================

main() {
    load_env

    case "$ACTION" in
        start)
            start_infra
            ;;
        stop)
            stop_infra
            ;;
        restart)
            restart_infra
            ;;
        status)
            status_infra
            ;;
        logs)
            logs_infra
            ;;
        *)
            echo "用法: $0 {start|stop|restart|status|logs} [service|group]"
            echo ""
            echo "服务组:"
            echo "  all       - 所有基础设施服务 (默认)"
            echo "  core      - 核心存储服务 (mysql, redis, minio, etcd)"
            echo "  dataops   - DataOps 完整环境"
            echo "  auth      - 认证服务 (keycloak)"
            echo "  etl       - ETL 服务"
            echo "  analytics - 数据分析服务"
            echo "  scheduler - 调度服务"
            echo "  metadata  - 元数据服务"
            echo ""
            echo "示例:"
            echo "  $0 start              # 启动所有基础设施"
            echo "  $0 start core         # 仅启动核心服务"
            echo "  $0 start dataops      # 启动 DataOps 环境"
            echo "  $0 stop               # 停止所有基础设施"
            echo "  $0 status             # 查看状态"
            echo "  $0 logs mysql         # 查看 MySQL 日志"
            exit 1
            ;;
    esac
}

main
