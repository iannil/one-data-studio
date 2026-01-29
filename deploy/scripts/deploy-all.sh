#!/usr/bin/env bash
#
# ONE-DATA-STUDIO 一键部署脚本
# Sprint 10: 部署自动化
#
# 功能：
# - 环境检查和依赖验证
# - 基础设施服务部署
# - 应用服务部署
# - 健康检查验证
# - 监控系统配置
#
# 使用方法:
#   ./deploy-all.sh [环境] [选项]
#
# 环境:
#   local     - 本地 Docker Compose 部署
#   k8s       - Kubernetes 部署
#   kind      - Kind 集群部署（开发/测试）
#
# 选项:
#   --skip-infra    跳过基础设施部署
#   --skip-app      跳过应用部署
#   --skip-monitor  跳过监控配置
#   --dry-run       仅打印命令，不执行
#   --force         强制部署（忽略健康检查失败）
#   --verbose       详细输出
#

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DEPLOY_DIR="$PROJECT_ROOT/deploy"
K8S_DIR="$PROJECT_ROOT/k8s"
DOCKER_COMPOSE_FILE="$PROJECT_ROOT/docker-compose.yml"

# 默认值
ENVIRONMENT="${1:-local}"
SKIP_INFRA=false
SKIP_APP=false
SKIP_MONITOR=false
DRY_RUN=false
FORCE=false
VERBOSE=false

# 解析参数
shift || true
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-infra)   SKIP_INFRA=true; shift ;;
        --skip-app)     SKIP_APP=true; shift ;;
        --skip-monitor) SKIP_MONITOR=true; shift ;;
        --dry-run)      DRY_RUN=true; shift ;;
        --force)        FORCE=true; shift ;;
        --verbose)      VERBOSE=true; shift ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

# 日志函数
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step() { echo -e "\n${GREEN}==> $1${NC}"; }

# 执行命令（支持 dry-run）
run_cmd() {
    if [ "$DRY_RUN" = true ]; then
        echo "[DRY-RUN] $*"
    else
        if [ "$VERBOSE" = true ]; then
            "$@"
        else
            "$@" > /dev/null 2>&1
        fi
    fi
}

# 检查命令是否存在
check_command() {
    if ! command -v "$1" &> /dev/null; then
        log_error "Required command not found: $1"
        return 1
    fi
    return 0
}

# 等待服务健康
wait_for_health() {
    local url=$1
    local max_attempts=${2:-30}
    local interval=${3:-5}

    log_info "Waiting for $url to be healthy..."

    for i in $(seq 1 $max_attempts); do
        if curl -sf "$url" > /dev/null 2>&1; then
            log_success "Service is healthy: $url"
            return 0
        fi
        sleep $interval
    done

    log_error "Service failed to become healthy: $url"
    return 1
}

# ==================================================
# 环境检查
# ==================================================
check_environment() {
    log_step "Step 1: Checking environment requirements"

    case $ENVIRONMENT in
        local)
            check_command docker || exit 1
            check_command docker-compose || check_command "docker compose" || exit 1
            log_success "Docker environment ready"
            ;;
        k8s|kind)
            check_command kubectl || exit 1
            check_command helm || exit 1

            # 检查 kubectl 连接
            if ! kubectl cluster-info > /dev/null 2>&1; then
                log_error "Cannot connect to Kubernetes cluster"
                exit 1
            fi
            log_success "Kubernetes environment ready"

            if [ "$ENVIRONMENT" = "kind" ]; then
                check_command kind || exit 1
                # 检查 Kind 集群
                if ! kind get clusters | grep -q "one-data"; then
                    log_warning "Kind cluster 'one-data' not found, creating..."
                    run_cmd kind create cluster --name one-data --config "$K8S_DIR/kind-config.yaml"
                fi
            fi
            ;;
        *)
            log_error "Unknown environment: $ENVIRONMENT"
            exit 1
            ;;
    esac
}

# ==================================================
# 基础设施部署
# ==================================================
deploy_infrastructure() {
    if [ "$SKIP_INFRA" = true ]; then
        log_info "Skipping infrastructure deployment"
        return
    fi

    log_step "Step 2: Deploying infrastructure services"

    case $ENVIRONMENT in
        local)
            log_info "Starting infrastructure services with Docker Compose..."
            run_cmd docker-compose -f "$DOCKER_COMPOSE_FILE" up -d mysql redis minio milvus etcd

            # 等待服务就绪
            sleep 10
            log_info "Waiting for MySQL..."
            for i in {1..30}; do
                if docker-compose -f "$DOCKER_COMPOSE_FILE" exec -T mysql mysqladmin ping -h localhost -u root -proot &> /dev/null; then
                    log_success "MySQL is ready"
                    break
                fi
                sleep 2
            done

            log_info "Waiting for Redis..."
            for i in {1..30}; do
                if docker-compose -f "$DOCKER_COMPOSE_FILE" exec -T redis redis-cli ping &> /dev/null; then
                    log_success "Redis is ready"
                    break
                fi
                sleep 2
            done
            ;;
        k8s|kind)
            log_info "Deploying infrastructure to Kubernetes..."

            # 创建命名空间
            run_cmd kubectl apply -f "$K8S_DIR/base/namespace.yaml"

            # 部署基础设施
            run_cmd kubectl apply -f "$K8S_DIR/infra/mysql/"
            run_cmd kubectl apply -f "$K8S_DIR/infra/redis/"
            run_cmd kubectl apply -f "$K8S_DIR/infra/minio/"
            run_cmd kubectl apply -f "$K8S_DIR/infra/milvus/"

            # 等待 Pod 就绪
            log_info "Waiting for infrastructure pods..."
            run_cmd kubectl wait --for=condition=ready pod -l app=mysql -n one-data-system --timeout=300s
            run_cmd kubectl wait --for=condition=ready pod -l app=redis -n one-data-system --timeout=300s
            run_cmd kubectl wait --for=condition=ready pod -l app=minio -n one-data-system --timeout=300s
            ;;
    esac

    log_success "Infrastructure deployment completed"
}

# ==================================================
# 应用部署
# ==================================================
deploy_applications() {
    if [ "$SKIP_APP" = true ]; then
        log_info "Skipping application deployment"
        return
    fi

    log_step "Step 3: Deploying application services"

    case $ENVIRONMENT in
        local)
            log_info "Building and starting application containers..."

            # 构建镜像
            run_cmd docker-compose -f "$DOCKER_COMPOSE_FILE" build data-api agent-api web

            # 启动服务
            run_cmd docker-compose -f "$DOCKER_COMPOSE_FILE" up -d data-api agent-api web

            # 健康检查
            sleep 10
            if [ "$FORCE" = false ]; then
                wait_for_health "http://localhost:8080/api/v1/health" 30 5 || exit 1
                wait_for_health "http://localhost:8081/api/v1/health" 30 5 || exit 1
            fi
            ;;
        k8s|kind)
            log_info "Deploying applications to Kubernetes..."

            # 部署应用
            run_cmd kubectl apply -f "$K8S_DIR/apps/data-api/"
            run_cmd kubectl apply -f "$K8S_DIR/apps/agent-api/"
            run_cmd kubectl apply -f "$K8S_DIR/apps/web/"

            # 等待 Pod 就绪
            log_info "Waiting for application pods..."
            run_cmd kubectl wait --for=condition=ready pod -l app=data-api -n one-data-system --timeout=300s
            run_cmd kubectl wait --for=condition=ready pod -l app=agent-api -n one-data-system --timeout=300s
            run_cmd kubectl wait --for=condition=ready pod -l app=web -n one-data-system --timeout=300s

            # 应用 HPA
            log_info "Configuring auto-scaling..."
            run_cmd kubectl apply -f "$K8S_DIR/hpa/"
            ;;
    esac

    log_success "Application deployment completed"
}

# ==================================================
# 监控配置
# ==================================================
deploy_monitoring() {
    if [ "$SKIP_MONITOR" = true ]; then
        log_info "Skipping monitoring configuration"
        return
    fi

    log_step "Step 4: Configuring monitoring and observability"

    case $ENVIRONMENT in
        local)
            log_info "Starting monitoring services..."
            run_cmd docker-compose -f "$DOCKER_COMPOSE_FILE" up -d prometheus grafana loki promtail

            log_info "Monitoring services started"
            log_info "  - Prometheus: http://localhost:9090"
            log_info "  - Grafana: http://localhost:3000 (admin/admin)"
            ;;
        k8s|kind)
            log_info "Deploying monitoring stack..."

            # 部署 Prometheus
            run_cmd kubectl apply -f "$K8S_DIR/infra/prometheus/"

            # 部署 Grafana
            run_cmd kubectl apply -f "$K8S_DIR/infra/grafana/"

            # 部署 Loki + Promtail
            run_cmd kubectl apply -f "$K8S_DIR/infra/loki/"

            # 部署服务监控
            run_cmd kubectl apply -f "$K8S_DIR/service-monitors/"

            # 等待监控 Pod 就绪
            run_cmd kubectl wait --for=condition=ready pod -l app=prometheus -n one-data-system --timeout=300s
            run_cmd kubectl wait --for=condition=ready pod -l app=grafana -n one-data-system --timeout=300s
            ;;
    esac

    log_success "Monitoring configuration completed"
}

# ==================================================
# 部署后验证
# ==================================================
verify_deployment() {
    log_step "Step 5: Verifying deployment"

    local all_healthy=true

    case $ENVIRONMENT in
        local)
            # 检查服务健康状态
            log_info "Checking service health..."

            if curl -sf "http://localhost:8080/api/v1/health" > /dev/null 2>&1; then
                log_success "data API: healthy"
            else
                log_error "data API: unhealthy"
                all_healthy=false
            fi

            if curl -sf "http://localhost:8081/api/v1/health" > /dev/null 2>&1; then
                log_success "agent API: healthy"
            else
                log_error "agent API: unhealthy"
                all_healthy=false
            fi

            if curl -sf "http://localhost:3000" > /dev/null 2>&1; then
                log_success "Web Frontend: healthy"
            else
                log_warning "Web Frontend: not responding (may still be starting)"
            fi
            ;;
        k8s|kind)
            # 检查 Pod 状态
            log_info "Checking pod status..."

            local pods_status=$(kubectl get pods -n one-data-system -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.status.phase}{"\n"}{end}')
            echo "$pods_status"

            if echo "$pods_status" | grep -v "Running\|Succeeded" | grep -v "^$"; then
                log_warning "Some pods are not running"
                all_healthy=false
            else
                log_success "All pods are running"
            fi
            ;;
    esac

    if [ "$all_healthy" = true ]; then
        log_success "Deployment verification passed"
    else
        if [ "$FORCE" = true ]; then
            log_warning "Deployment verification failed but --force was specified"
        else
            log_error "Deployment verification failed"
            exit 1
        fi
    fi
}

# ==================================================
# 打印部署信息
# ==================================================
print_deployment_info() {
    log_step "Deployment Complete!"

    echo ""
    echo "=========================================="
    echo "  ONE-DATA-STUDIO Deployment Summary"
    echo "=========================================="
    echo ""

    case $ENVIRONMENT in
        local)
            echo "Services:"
            echo "  - Web UI:        http://localhost:3000"
            echo "  - data API:   http://localhost:8080"
            echo "  - agent API:   http://localhost:8081"
            echo ""
            echo "Monitoring:"
            echo "  - Prometheus:    http://localhost:9090"
            echo "  - Grafana:       http://localhost:3001"
            echo ""
            echo "Infrastructure:"
            echo "  - MySQL:         localhost:3306"
            echo "  - Redis:         localhost:6379"
            echo "  - MinIO Console: http://localhost:9001"
            echo "  - Milvus:        localhost:19530"
            ;;
        k8s|kind)
            echo "Use 'kubectl port-forward' to access services:"
            echo ""
            echo "  kubectl port-forward svc/web 3000:80 -n one-data-system"
            echo "  kubectl port-forward svc/data-api 8080:8080 -n one-data-system"
            echo "  kubectl port-forward svc/agent-api 8081:8081 -n one-data-system"
            echo ""
            echo "Or use the provided port-forward script:"
            echo "  ./scripts/port-forward.sh"
            ;;
    esac

    echo ""
    echo "Documentation:"
    echo "  - API Docs:     docs/02-integration/api-reference.md"
    echo "  - Operations:   docs/06-operations/"
    echo ""
    echo "=========================================="
}

# ==================================================
# 主函数
# ==================================================
main() {
    echo ""
    echo "=========================================="
    echo "  ONE-DATA-STUDIO Deployment"
    echo "  Environment: $ENVIRONMENT"
    echo "=========================================="
    echo ""

    if [ "$DRY_RUN" = true ]; then
        log_warning "DRY-RUN mode enabled - no changes will be made"
    fi

    check_environment
    deploy_infrastructure
    deploy_applications
    deploy_monitoring
    verify_deployment
    print_deployment_info
}

# 运行主函数
main
