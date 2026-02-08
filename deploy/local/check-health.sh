#!/usr/bin/env bash
# ONE-DATA-STUDIO 健康检查脚本
# 检查所有 Docker 容器的健康状态

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 服务端点定义
declare -A SERVICES=(
    # 基础设施服务
    ["mysql"]="one-data-mysql:3306"
    ["redis"]="one-data-redis:6379"
    ["minio"]="one-data-minio:9000"
    ["etcd"]="one-data-etcd:2379"
    ["elasticsearch"]="one-data-elasticsearch:9200"

    # 元数据服务
    ["openmetadata"]="one-data-openmetadata:8585"

    # ETL 服务
    ["kettle"]="one-data-kettle:8080"
    ["hop-server"]="one-data-hop-server:8182"

    # 认证服务
    ["keycloak"]="one-data-keycloak:8080"

    # AI 服务
    ["vllm-chat"]="one-data-vllm-chat:8000"
    ["vllm-embed"]="one-data-vllm-embed:8000"
    ["ollama"]="one-data-ollama:11434"

    # 标注服务
    ["label-studio"]="one-data-label-studio:8080"
    ["label-studio-pg"]="one-data-label-studio-pg:5432"

    # 应用服务
    ["agent-api"]="one-data-agent-api:8000"
    ["data-api"]="one-data-data-api:8001"
    ["model-api"]="one-data-model-api:8002"
    ["openai-proxy"]="one-data-openai-proxy:8000"
    ["admin-api"]="one-data-admin-api:8004"
    ["ocr-service"]="one-data-ocr-service:8007"
    ["behavior-service"]="one-data-behavior-service:8008"

    # Web 前端
    ["web-frontend"]="one-data-web:80"

    # 工作流调度
    ["zookeeper"]="one-data-zookeeper:2181"
    ["dolphinscheduler-pg"]="one-data-dolphinscheduler-postgresql:5432"
    ["dolphinscheduler"]="one-data-dolphinscheduler:12345"

    # BI 分析
    ["superset-cache"]="one-data-superset-cache:6379"
    ["superset"]="one-data-superset:8088"

    # 数据集成
    ["seatunnel-zk"]="one-data-seatunnel-zk:2181"
    ["seatunnel"]="one-data-seatunnel:5801"
)

# HTTP 健康检查端点
declare -A HTTP_ENDPOINTS=(
    ["openmetadata"]="http://localhost:8585/api/v1/system/version"
    ["kettle"]="http://localhost:8080/spoon/spoon"
    ["hop-server"]="http://localhost:8182/hop/status"
    ["vllm-chat"]="http://localhost:8010/health"
    ["vllm-embed"]="http://localhost:8011/health"
    ["ollama"]="http://localhost:11434/api/tags"
    ["label-studio"]="http://localhost:8009/health"
    ["agent-api"]="http://localhost:8000/api/v1/health"
    ["data-api"]="http://localhost:8001/api/v1/health"
    ["model-api"]="http://localhost:8002/health"
    ["openai-proxy"]="http://localhost:8003/health"
    ["admin-api"]="http://localhost:8004/health"
    ["ocr-service"]="http://localhost:8007/health"
    ["behavior-service"]="http://localhost:8008/health"
    ["web-frontend"]="http://localhost:3000"
    ["dolphinscheduler"]="http://localhost:12345/dolphinscheduler/auth/login"
    ["superset"]="http://localhost:8088/health"
    ["seatunnel"]="http://localhost:5801"
)

# 打印标题
print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

# 检查容器是否存在
check_container_exists() {
    local container=$1
    docker ps -a --format '{{.Names}}' | grep -q "^${container}$"
}

# 检查容器状态
check_container_status() {
    local container=$1
    local status=$(docker inspect -f '{{.State.Status}}' "$container" 2>/dev/null || echo "not_found")

    if [ "$status" = "running" ]; then
        local health=$(docker inspect -f '{{.State.Health.Status}}' "$container" 2>/dev/null || echo "no_healthcheck")
        case $health in
            "healthy")
                echo -e "${GREEN}✓${NC} $container: ${GREEN}Healthy${NC}"
                return 0
                ;;
            "unhealthy")
                echo -e "${RED}✗${NC} $container: ${RED}Unhealthy${NC}"
                return 1
                ;;
            "starting")
                echo -e "${YELLOW}○${NC} $container: ${YELLOW}Starting...${NC}"
                return 2
                ;;
            *)
                echo -e "${GREEN}✓${NC} $container: ${GREEN}Running (no healthcheck)${NC}"
                return 0
                ;;
        esac
    else
        echo -e "${RED}✗${NC} $container: ${RED}Not running${NC}"
        return 1
    fi
}

# HTTP 健康检查
check_http_endpoint() {
    local name=$1
    local url=$2
    local response=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$url" 2>/dev/null || echo "000")

    if [ "$response" = "000" ]; then
        echo -e "${RED}✗${NC} $name: ${RED}Connection failed${NC} ($url)"
        return 1
    elif [ "$response" -ge 200 ] && [ "$response" -lt 400 ]; then
        echo -e "${GREEN}✓${NC} $name: ${GREEN}HTTP $response${NC} ($url)"
        return 0
    else
        echo -e "${YELLOW}○${NC} $name: ${YELLOW}HTTP $response${NC} ($url)"
        return 2
    fi
}

# 主函数
main() {
    print_header "ONE-DATA-STUDIO 健康检查"
    echo ""

    local total=0
    local healthy=0
    local unhealthy=0
    local starting=0

    echo -e "${BLUE}[1/2] 检查容器状态...${NC}"
    echo ""

    for service in "${!SERVICES[@]}"; do
        container="${SERVICES[$service]%%:*}"
        if check_container_exists "$container"; then
            total=$((total + 1))
            check_container_status "$container"
            case $? in
                0) healthy=$((healthy + 1)) ;;
                1) unhealthy=$((unhealthy + 1)) ;;
                2) starting=$((starting + 1)) ;;
            esac
        fi
    done

    echo ""
    echo -e "${BLUE}[2/2] 检查 HTTP 端点...${NC}"
    echo ""

    for endpoint in "${!HTTP_ENDPOINTS[@]}"; do
        check_http_endpoint "$endpoint" "${HTTP_ENDPOINTS[$endpoint]}"
    done

    echo ""
    print_header "健康检查汇总"
    echo -e "总计: $total 个服务"
    echo -e "${GREEN}健康: $healthy${NC}"
    echo -e "${YELLOW}启动中: $starting${NC}"
    echo -e "${RED}不健康: $unhealthy${NC}"
    echo ""

    if [ $unhealthy -eq 0 ] && [ $starting -eq 0 ]; then
        echo -e "${GREEN}所有服务运行正常！${NC}"
        return 0
    elif [ $unhealthy -eq 0 ]; then
        echo -e "${YELLOW}部分服务正在启动中...${NC}"
        return 0
    else
        echo -e "${RED}部分服务不健康，请检查日志${NC}"
        return 1
    fi
}

# 执行主函数
main
