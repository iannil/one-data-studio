#!/bin/bash
# Phase 1 部署脚本
# 用于部署 Sprint 1.1 和 Sprint 1.2 的功能

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查 Kind 集群状态
check_cluster() {
    log_info "检查 Kind 集群状态..."
    if ! kind get clusters | grep -q "one-data"; then
        log_error "Kind 集群 'one-data' 不存在，请先运行 scripts/install-kind.sh"
        exit 1
    fi
    log_info "Kind 集群正常"
}

# 构建镜像
build_images() {
    log_info "开始构建 Docker 镜像..."

    log_info "构建 Alldata API 镜像..."
    docker build -t alldata-api:latest -f docker/services/alldata-api/Dockerfile .

    log_info "构建 OpenAI Proxy 镜像..."
    docker build -t openai-proxy:latest -f docker/services/openai-proxy/Dockerfile .

    # 加载镜像到 Kind 集群
    log_info "加载镜像到 Kind 集群..."
    kind load docker-image alldata-api:latest --name one-data
    kind load docker-image openai-proxy:latest --name one-data

    log_info "镜像构建完成"
}

# 初始化数据库
init_database() {
    log_info "初始化数据库..."

    # 等待 MySQL 就绪
    log_info "等待 MySQL 就绪..."
    kubectl wait --for=condition=ready pod -l app=mysql -n one-data-infra --timeout=120s

    # 执行初始化 SQL
    log_info "执行数据库初始化脚本..."
    kubectl exec -n one-data-infra mysql-0 -- mysql -uone_data -pOneDataPassword123! < services/alldata-api/migrations/init_schema.sql || true

    log_info "数据库初始化完成"
}

# 部署服务
deploy_services() {
    log_info "部署 Phase 1 服务..."

    # 部署 Alldata API (持久化版本)
    log_info "部署 Alldata API..."
    kubectl apply -f k8s/applications/alldata-api.yaml

    # 部署 OpenAI Proxy
    log_info "部署 OpenAI Proxy..."
    kubectl apply -f k8s/applications/openai-proxy.yaml

    # 更新 Bisheng API
    log_info "更新 Bisheng API..."
    kubectl apply -f k8s/applications/bisheng-api.yaml

    log_info "服务部署完成"
}

# 等待服务就绪
wait_for_ready() {
    log_info "等待服务就绪..."

    log_info "等待 Alldata API..."
    kubectl wait --for=condition=ready pod -l app=alldata-api -n one-data-alldata --timeout=120s

    log_info "等待 OpenAI Proxy..."
    kubectl wait --for=condition=ready pod -l app=openai-proxy -n one-data-cube --timeout=120s

    log_info "等待 Bisheng API..."
    kubectl wait --for=condition=ready pod -l app=bisheng-api -n one-data-bisheng --timeout=120s

    log_info "所有服务已就绪"
}

# 健康检查
health_check() {
    log_info "执行健康检查..."

    echo ""
    echo "=== Alldata API ==="
    kubectl exec -n one-data-alldata deploy/alldata-api -- curl -s http://localhost:8080/api/v1/health | jq . || echo "检查失败"

    echo ""
    echo "=== OpenAI Proxy ==="
    kubectl exec -n one-data-cube deploy/openai-proxy -- curl -s http://localhost:8000/health | jq . || echo "检查失败"

    echo ""
    echo "=== Bisheng API ==="
    kubectl exec -n one-data-bisheng deploy/bisheng-api -- curl -s http://localhost:8080/api/v1/health | jq . || echo "检查失败"

    echo ""
}

# 配置 OpenAI API Key
configure_openai() {
    log_warn "请设置您的 OpenAI API Key："
    log_warn "kubectl edit secret openai-secret -n one-data-cube"
    log_warn "将 api-key 的值替换为您的真实 API Key"
}

# 显示部署状态
show_status() {
    log_info "Phase 1 部署状态："
    echo ""
    kubectl get pods -n one-data-alldata -l app=alldata-api
    kubectl get pods -n one-data-cube -l app=openai-proxy
    kubectl get pods -n one-data-bisheng -l app=bisheng-api
}

# 主函数
main() {
    log_info "开始 Phase 1 部署..."

    check_cluster

    # 解析命令行参数
    SKIP_BUILD=${SKIP_BUILD:-false}
    SKIP_DB_INIT=${SKIP_DB_INIT:-false}

    if [ "$SKIP_BUILD" != "true" ]; then
        build_images
    else
        log_warn "跳过镜像构建"
    fi

    if [ "$SKIP_DB_INIT" != "true" ]; then
        init_database
    else
        log_warn "跳过数据库初始化"
    fi

    deploy_services
    wait_for_ready
    health_check
    show_status

    log_info "Phase 1 部署完成！"
    echo ""
    configure_openai
    echo ""
    log_info "使用以下命令测试 API："
    echo "  kubectl port-forward -n one-data-alldata svc/alldata-api 8080:8080"
    echo "  kubectl port-forward -n one-data-cube svc/openai-proxy 8000:8000"
    echo "  kubectl port-forward -n one-data-bisheng svc/bisheng-api 8081:8080"
}

# 运行主函数
main "$@"
