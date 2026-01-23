# ONE-DATA-STUDIO Makefile
# 简化 K8s 部署和测试流程

.PHONY: help install install-base install-infra install-apps install-all
.PHONY: status logs test clean forward unforward
.PHONY: kind-cluster docker-up docker-down helm-lint
.PHONY: logs-alldata logs-cube logs-bisheng
.PHONY: web-build web-install web-logs web-forward web-dev
.PHONY: phase2 phase2-all
.PHONY: init-db test-e2e

# 默认目标
help:
	@echo "ONE-DATA-STUDIO 部署命令:"
	@echo ""
	@echo "环境准备:"
	@echo "  make kind-cluster     - 创建 Kind 本地 K8s 集群"
	@echo "  make docker-up        - 使用 Docker Compose 启动服务"
	@echo "  make docker-down      - 停止 Docker Compose 服务"
	@echo ""
	@echo "K8s 部署:"
	@echo "  make install          - 安装所有服务"
	@echo "  make install-base     - 安装基础资源（命名空间、StorageClass）"
	@echo "  make install-infra    - 安装基础设施（MinIO、MySQL、Redis）"
	@echo "  make install-apps     - 安装应用服务（Alldata、Cube、Bisheng）"
	@echo ""
	@echo "Phase 2 Web 前端:"
	@echo "  make web-build        - 构建 Web 前端 Docker 镜像"
	@echo "  make web-install      - 部署 Web 前端到 K8s"
	@echo "  make web-logs         - 查看 Web 前端日志"
	@echo "  make web-forward      - 转发 Web 前端端口到本地"
	@echo "  make web-dev          - 启动本地开发服务器"
	@echo "  make phase2           - 部署 Phase 2（Web 前端）"
	@echo "  make phase2-all       - 部署 Phase 1 + Phase 2"
	@echo ""
	@echo "状态查看:"
	@echo "  make status           - 查看所有 Pod 状态"
	@echo "  make logs             - 查看所有服务日志"
	@echo "  make logs-alldata     - 查看 Alldata API 日志"
	@echo "  make logs-cube        - 查看 Cube 模型服务日志"
	@echo "  make logs-bisheng     - 查看 Bisheng API 日志"
	@echo ""
	@echo "测试验证:"
	@echo "  make test             - 运行快速测试"
	@echo "  make test-all         - 运行完整集成测试脚本"
	@echo "  make test-e2e         - 运行端到端测试脚本"
	@echo ""
	@echo "数据库初始化:"
	@echo "  make init-db          - 运行数据库初始化 Job"
	@echo ""
	@echo "端口转发:"
	@echo "  make forward          - 启动端口转发（后台）"
	@echo "  make unforward        - 停止端口转发"
	@echo "  make forward-interactive - 启动端口转发（前台）"
	@echo ""
	@echo "清理:"
	@echo "  make clean            - 删除所有 K8s 资源"
	@echo "  make clean-all        - 删除 K8s 资源和 Kind 集群"
	@echo ""
	@echo "Helm:"
	@echo "  make helm-lint        - 检查 Helm Charts"
	@echo "  make helm-package     - 打包 Helm Charts"
	@echo ""

# ============================================
# 环境准备
# ============================================

# 创建 Kind 集群
kind-cluster:
	@echo "==> 创建 Kind 集群..."
	@bash scripts/install-kind.sh

# Docker Compose 启动
docker-up:
	@echo "==> 使用 Docker Compose 启动服务..."
	@docker-compose up -d
	@echo "==> 服务已启动:"
	@echo "    Alldata API:  http://localhost:8080"
	@echo "    Cube API:     http://localhost:8000"
	@echo "    Bisheng API:  http://localhost:8081"
	@echo "    MinIO:        http://localhost:9001"
	@echo "    Grafana:      http://localhost:3000"

# Docker Compose 停止
docker-down:
	@echo "==> 停止 Docker Compose 服务..."
	@docker-compose down

# ============================================
# K8s 部署
# ============================================

# 安装所有服务
install: install-base install-infra install-apps
	@echo "==> 所有服务已安装"
	@$(MAKE) status

# 安装基础资源
install-base:
	@echo "==> 安装基础资源..."
	kubectl apply -f k8s/base/namespaces.yaml
	kubectl apply -f k8s/base/storage-classes.yaml

# 安装基础设施
install-infra: install-base
	@echo "==> 安装基础设施..."
	kubectl apply -f k8s/infrastructure/minio.yaml
	kubectl apply -f k8s/infrastructure/mysql.yaml
	kubectl apply -f k8s/infrastructure/redis.yaml
	@echo "==> 等待基础设施就绪..."
	kubectl wait --for=condition=ready pod -l app=minio -n one-data-infra --timeout=300s || true
	kubectl wait --for=condition=ready pod -l app=mysql -n one-data-infra --timeout=300s || true
	kubectl wait --for=condition=ready pod -l app=redis -n one-data-infra --timeout=300s || true

# 安装应用服务
install-apps: install-infra
	@echo "==> 安装应用服务..."
	kubectl apply -f k8s/applications/alldata-api-mock.yaml
	kubectl apply -f k8s/applications/vllm-serving.yaml
	kubectl apply -f k8s/applications/bisheng-api-mock.yaml
	@echo "==> 等待应用服务就绪..."
	kubectl wait --for=condition=ready pod -l app=alldata-api -n one-data-alldata --timeout=120s || true
	kubectl wait --for=condition=ready pod -l app=vllm-serving -n one-data-cube --timeout=600s || true
	kubectl wait --for=condition=ready pod -l app=bisheng-api -n one-data-bisheng --timeout=120s || true

# ============================================
# 状态查看
# ============================================

# 查看状态
status:
	@echo "==> Pod 状态:"
	@kubectl get pods -A | grep one-data || echo "  无 Pod 运行"
	@echo ""
	@echo "==> Service 状态:"
	@kubectl get svc -A | grep one-data || echo "  无 Service"

# 查看日志
logs:
	@echo "==> Alldata API 日志:"
	@kubectl logs -n one-data-alldata deployment/alldata-api --tail=20 || true
	@echo ""
	@echo "==> vLLM 服务日志:"
	@kubectl logs -n one-data-cube deployment/vllm-serving --tail=20 || true
	@echo ""
	@echo "==> Bisheng API 日志:"
	@kubectl logs -n one-data-bisheng deployment/bisheng-api --tail=20 || true

logs-alldata:
	@kubectl logs -n one-data-alldata deployment/alldata-api -f

logs-cube:
	@kubectl logs -n one-data-cube deployment/vllm-serving -f

logs-bisheng:
	@kubectl logs -n one-data-bisheng deployment/bisheng-api -f

# ============================================
# 测试
# ============================================

# 快速测试
test:
	@echo "==> 测试 Alldata API..."
	@curl -s http://localhost:8080/api/v1/health | jq . || echo "  Alldata API 未响应"
	@echo ""
	@echo "==> 测试 Cube 模型服务..."
	@curl -s http://localhost:8000/v1/models | jq . || echo "  Cube API 未响应"
	@echo ""
	@echo "==> 测试 Bisheng API..."
	@curl -s http://localhost:8081/api/v1/health | jq . || echo "  Bisheng API 未响应"
	@echo ""
	@echo "==> 测试端到端调用..."
	@curl -s -X POST http://localhost:8081/api/v1/chat \
		-H "Content-Type: application/json" \
		-d '{"message": "测试"}' | jq . || echo "  端到端调用失败"

# 完整集成测试
test-all:
	@bash scripts/test-all.sh

# 端到端测试
test-e2e:
	@echo "==> 运行端到端测试..."
	@bash scripts/test-e2e.sh

# ============================================
# 数据库初始化
# ============================================

# 运行数据库初始化 Job
init-db:
	@echo "==> 运行数据库初始化 Job..."
	kubectl apply -f k8s/jobs/alldata-init-job.yaml
	kubectl apply -f k8s/jobs/bisheng-init-job.yaml
	@echo "==> 等待初始化完成..."
	@kubectl wait --for=condition=complete job/alldata-db-init -n one-data-alldata --timeout=300s || true
	@kubectl wait --for=condition=complete job/bisheng-db-init -n one-data-bisheng --timeout=300s || true
	@echo "==> 数据库初始化完成"

# ============================================
# 端口转发
# ============================================

# 后台端口转发
forward:
	@bash scripts/port-forward.sh &

# 前台端口转发
forward-interactive:
	@bash scripts/port-forward.sh

# 停止端口转发
unforward:
	@echo "==> 停止端口转发..."
	@pkill -f "port-forward.*one-data" || true
	@rm -f /tmp/one-data-port-forward-pids.txt || true
	@echo "==> 端口转发已停止"

# ============================================
# 清理
# ============================================

# 清理 K8s 资源
clean:
	@bash scripts/clean.sh

# 清理所有资源（包括 Kind 集群）
clean-all:
	@echo "==> 删除应用服务..."
	kubectl delete -f k8s/applications/ --ignore-not-found=true
	@echo "==> 删除基础设施..."
	kubectl delete -f k8s/infrastructure/ --ignore-not-found=true
	@echo "==> 删除基础资源..."
	kubectl delete -f k8s/base/ --ignore-not-found=true
	@echo "==> 删除 Kind 集群..."
	kind delete cluster --name one-data || true
	@$(MAKE) unforward
	@echo "==> 清理完成"

# ============================================
# Helm
# ============================================

# 检查 Helm Charts
helm-lint:
	@echo "==> 检查 Helm Charts..."
	helm lint helm/charts/one-data || true

# 打包 Helm Charts
helm-package:
	@echo "==> 打包 Helm Charts..."
	helm package helm/charts/one-data

# ============================================
# Phase 2 Web 前端
# ============================================

# 构建 Web 前端 Docker 镜像
web-build:
	@echo "==> 构建 Web 前端 Docker 镜像..."
	docker build -t one-data-web:latest web/
	@echo "==> 镜像构建完成: one-data-web:latest"

# 部署 Web 前端到 K8s
web-install: web-build
	@echo "==> 加载镜像到 Kind..."
	kind load docker-image one-data-web:latest --name one-data || \
		echo "  注意: 请确保 Kind 集群名为 'one-data'"
	@echo "==> 部署 Web 前端到 K8s..."
	kubectl apply -f k8s/applications/web-frontend.yaml
	@echo "==> 等待 Web 前端就绪..."
	kubectl wait --for=condition=ready pod -l app=web-frontend -n one-data-web --timeout=120s || true
	@echo "==> Web 前端已部署"
	@echo "    使用 'make web-forward' 访问 Web UI"

# 查看 Web 前端日志
web-logs:
	@kubectl logs -n one-data-web deployment/web-frontend -f

# 转发 Web 前端端口到本地
web-forward:
	@echo "==> 转发 Web 前端端口到 localhost:3000..."
	kubectl port-forward -n one-data-web svc/web-frontend 3000:80

# 启动本地开发服务器
web-dev:
	@echo "==> 启动 Web 前端开发服务器..."
	cd web && npm install && npm run dev

# 部署 Phase 2（Web 前端）
phase2: web-install

# 部署 Phase 1 + Phase 2
phase2-all: install phase2
	@echo "==> Phase 1 + Phase 2 已全部部署"
	@$(MAKE) status

# ============================================
# 其他
# ============================================

# 重新部署
redeploy: clean install
