# ONE-DATA-STUDIO Makefile
# 简化 K8s 部署和测试流程

.PHONY: help install install-base install-infra install-apps install-all
.PHONY: status logs test clean forward unforward
.PHONY: kind-cluster docker-up docker-down helm-lint
.PHONY: logs-data logs-model logs-agent
.PHONY: web-build web-install web-logs web-forward web-dev
.PHONY: phase2 phase2-all
.PHONY: init-db test-e2e
# 开发环境运维脚本
.PHONY: dev-start dev-stop dev-status dev-logs dev-db dev-clean dev-reset dev-shell dev-check
.PHONY: dev up down
# 种子数据
.PHONY: seed seed-dry-run seed-force dev-seed

# 默认目标
help:
	@echo "ONE-DATA-STUDIO 部署命令:"
	@echo ""
	@echo "开发环境（推荐）:"
	@echo "  make dev              - 启动开发环境（等同于 dev-start）"
	@echo "  make up               - 启动开发环境（别名）"
	@echo "  make down             - 停止开发环境（别名）"
	@echo "  make dev-start        - 启动开发环境服务"
	@echo "  make dev-stop         - 停止开发环境服务"
	@echo "  make dev-status       - 查看服务状态"
	@echo "  make dev-logs         - 查看服务日志"
	@echo "  make dev-db           - 数据库操作"
	@echo "  make dev-clean        - 清理临时文件和资源"
	@echo "  make dev-reset        - 重置开发环境"
	@echo "  make dev-shell        - 进入容器 Shell"
	@echo "  make dev-check        - 健康检查"
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
	@echo "  make install-apps     - 安装应用服务（Data、Model、Agent）"
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
	@echo "  make logs-data        - 查看 Data API 日志"
	@echo "  make logs-model       - 查看 Model 模型服务日志"
	@echo "  make logs-agent       - 查看 Agent API 日志"
	@echo ""
	@echo "测试验证:"
	@echo "  make test             - 运行快速测试"
	@echo "  make test-all         - 运行完整集成测试脚本"
	@echo "  make test-e2e         - 运行端到端测试脚本"
	@echo ""
	@echo "数据库初始化:"
	@echo "  make init-db          - 运行数据库初始化 Job"
	@echo "  make seed             - 导入种子数据（初始化数据）"
	@echo "  make seed-dry-run     - 预览种子数据导入（不实际写入）"
	@echo "  make seed-force       - 强制导入种子数据（覆盖已有）"
	@echo "  make dev-seed         - 启动开发环境并导入种子数据"
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
	@bash deploy/scripts/install-kind.sh

# Docker Compose 启动
docker-up:
	@echo "==> 使用 Docker Compose 启动服务..."
	@docker-compose -f deploy/local/docker-compose.yml up -d
	@echo "==> 服务已启动:"
	@echo "    Agent API:    http://localhost:8000"
	@echo "    Data API:    http://localhost:8001"
	@echo "    Model API:   http://localhost:8002"
	@echo "    OpenAI Proxy: http://localhost:8003"
	@echo "    MinIO:        http://localhost:9001"
	@echo "    Web Frontend: http://localhost:3000"

# Docker Compose 停止
docker-down:
	@echo "==> 停止 Docker Compose 服务..."
	@docker-compose -f deploy/local/docker-compose.yml down

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
	kubectl apply -f deploy/kubernetes/base/namespaces.yaml
	kubectl apply -f deploy/kubernetes/base/storage-classes.yaml

# 安装基础设施
install-infra: install-base
	@echo "==> 安装基础设施..."
	kubectl apply -f deploy/kubernetes/infrastructure/databases/minio.yaml
	kubectl apply -f deploy/kubernetes/infrastructure/databases/mysql/standalone.yaml
	kubectl apply -f deploy/kubernetes/infrastructure/databases/redis/standalone.yaml
	@echo "==> 等待基础设施就绪..."
	kubectl wait --for=condition=ready pod -l app=minio -n one-data-infra --timeout=300s || true
	kubectl wait --for=condition=ready pod -l app=mysql -n one-data-infra --timeout=300s || true
	kubectl wait --for=condition=ready pod -l app=redis -n one-data-infra --timeout=300s || true

# 安装应用服务
install-apps: install-infra
	@echo "==> 安装应用服务..."
	kubectl apply -f deploy/kubernetes/applications/data-api/deployment.yaml
	kubectl apply -f deploy/kubernetes/applications/vllm-serving/deployment.yaml
	kubectl apply -f deploy/kubernetes/applications/agent-api/deployment.yaml
	@echo "==> 等待应用服务就绪..."
	kubectl wait --for=condition=ready pod -l app=data-api -n one-data-data --timeout=120s || true
	kubectl wait --for=condition=ready pod -l app=vllm-serving -n one-data-model --timeout=600s || true
	kubectl wait --for=condition=ready pod -l app=agent-api -n one-data-agent --timeout=120s || true

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
	@echo "==> Data API 日志:"
	@kubectl logs -n one-data-data deployment/data-api --tail=20 || true
	@echo ""
	@echo "==> vLLM 服务日志:"
	@kubectl logs -n one-data-model deployment/vllm-serving --tail=20 || true
	@echo ""
	@echo "==> Agent API 日志:"
	@kubectl logs -n one-data-agent deployment/agent-api --tail=20 || true

logs-data:
	@kubectl logs -n one-data-data deployment/data-api -f

logs-model:
	@kubectl logs -n one-data-model deployment/vllm-serving -f

logs-agent:
	@kubectl logs -n one-data-agent deployment/agent-api -f

# ============================================
# 测试
# ============================================

# 快速测试
test:
	@echo "==> 测试 Agent API..."
	@curl -s http://localhost:8000/api/v1/health | jq . || echo "  Agent API 未响应"
	@echo ""
	@echo "==> 测试 Data API..."
	@curl -s http://localhost:8001/api/v1/health | jq . || echo "  Data API 未响应"
	@echo ""
	@echo "==> 测试 Model API..."
	@curl -s http://localhost:8002/api/v1/health | jq . || echo "  Model API 未响应"
	@echo ""
	@echo "==> 测试端到端调用..."
	@curl -s -X POST http://localhost:8000/api/v1/chat \
		-H "Content-Type: application/json" \
		-d '{"message": "测试"}' | jq . || echo "  端到端调用失败"

# 完整集成测试
test-all:
	@bash deploy/scripts/test-all.sh

# 端到端测试
test-e2e:
	@echo "==> 运行端到端测试..."
	@bash deploy/scripts/test-e2e.sh

# ============================================
# 测试计划执行 (基于 user-lifecycle-test-cases.md)
# ============================================

# 单元测试 - 全部
test-unit:
	@echo "==> 运行所有单元测试..."
	@pytest tests/unit/ -v --tb=short --cov=services --cov-report=html:reports/coverage

# 单元测试 - P0 优先级
test-unit-p0:
	@echo "==> 运行 P0 单元测试..."
	@pytest tests/unit/ -v -m "unit and not slow" --tb=short

# 单元测试 - 按模块
test-unit-data:
	@echo "==> 运行 Data 模块单元测试..."
	@pytest tests/unit/test_data*.py tests/unit/test_datasource*.py tests/unit/test_metadata*.py tests/unit/test_sensitive*.py tests/unit/test_masking*.py tests/unit/test_data_standard.py -v

test-unit-agent:
	@echo "==> 运行 Agent 模块单元测试..."
	@pytest tests/unit/test_agent*.py tests/unit/test_hybrid*.py tests/unit/test_sql*.py tests/unit/test_document*.py tests/unit/test_agents.py -v

test-unit-model:
	@echo "==> 运行 Model 模块单元测试..."
	@pytest tests/unit/test_model*.py tests/unit/test_models*.py tests/unit/test_workflow*.py -v

test-unit-shared:
	@echo "==> 运行共享模块单元测试..."
	@pytest tests/unit/test_auth*.py tests/unit/test_jwt*.py tests/unit/test_csrf*.py tests/unit/test_security*.py tests/unit/test_cache*.py tests/unit/test_config*.py -v

# 单元测试 - 按角色 (新增)
test-data-administrator:
	@echo "==> 运行数据管理员单元测试..."
	@pytest tests/unit/test_data_administrator/ -v

test-data-engineer:
	@echo "==> 运行数据工程师单元测试..."
	@pytest tests/unit/test_data_engineer/ -v

test-ai-engineer:
	@echo "==> 运行算法工程师单元测试..."
	@pytest tests/unit/test_ai_engineer/ -v

test-business-user:
	@echo "==> 运行业务用户单元测试..."
	@pytest tests/unit/test_business_user/ -v

test-system-admin:
	@echo "==> 运行系统管理员单元测试..."
	@pytest tests/unit/test_system_admin/ -v

# 按角色运行 P0 测试
test-p0-data-administrator:
	@echo "==> 运行数据管理员 P0 测试..."
	@pytest tests/unit/test_data_administrator/ -m p0 -v

test-p0-data-engineer:
	@echo "==> 运行数据工程师 P0 测试..."
	@pytest tests/unit/test_data_engineer/ -m p0 -v

test-p0-ai-engineer:
	@echo "==> 运行算法工程师 P0 测试..."
	@pytest tests/unit/test_ai_engineer/ -m p0 -v

test-p0-business-user:
	@echo "==> 运行业务用户 P0 测试..."
	@pytest tests/unit/test_business_user/ -m p0 -v

test-p0-system-admin:
	@echo "==> 运行系统管理员 P0 测试..."
	@pytest tests/unit/test_system_admin/ -m p0 -v

test-p0-all:
	@echo "==> 运行所有 P0 单元测试..."
	@pytest tests/unit/test_data_administrator/ tests/unit/test_data_engineer/ tests/unit/test_ai_engineer/ tests/unit/test_business_user/ tests/unit/test_system_admin/ -m p0 -v

# 按角色运行集成测试
test-integration-dm:
	@echo "==> 运行数据管理员集成测试..."
	@pytest tests/integration/test_data_pipeline_integration.py -v --with-db

test-integration-de:
	@echo "==> 运行数据工程师集成测试..."
	@pytest tests/integration/test_data_pipeline_integration.py -v --with-db

test-integration-ae:
	@echo "==> 运行算法工程师集成测试..."
	@pytest tests/integration/test_model_lifecycle_integration.py -v --with-db 2>/dev/null || echo "  模型集成测试文件不存在"

test-integration-bu:
	@echo "==> 运行业务用户集成测试..."
	@pytest tests/integration/test_rag_integration.py -v --with-milvus

test-integration-cross:
	@echo "==> 运行跨服务集成测试..."
	@pytest tests/integration/test_cross_service_integration.py -v

# E2E 测试 - 按角色
test-e2e-data-administrator:
	@echo "==> 运行数据管理员 E2E 测试..."
	cd tests/e2e && npx playwright test data-administrator.spec.ts

test-e2e-data-engineer:
	@echo "==> 运行数据工程师 E2E 测试..."
	cd tests/e2e && npx playwright test data-engineer.spec.ts

test-e2e-ai-engineer:
	@echo "==> 运行算法工程师 E2E 测试..."
	cd tests/e2e && npx playwright test ai-engineer.spec.ts

test-e2e-business-user:
	@echo "==> 运行业务用户 E2E 测试..."
	cd tests/e2e && npx playwright test business-user.spec.ts

test-e2e-system-admin:
	@echo "==> 运行系统管理员 E2E 测试..."
	cd tests/e2e && npx playwright test system-admin.spec.ts

test-e2e-cross-role:
	@echo "==> 运行跨角色工作流 E2E 测试..."
	cd tests/e2e && npx playwright test cross-role-workflow.spec.ts

# 性能测试
test-perf:
	@echo "==> 运行性能测试..."
	@pytest tests/performance/ -v --benchmark

test-security:
	@echo "==> 运行安全测试..."
	@pytest tests/ -m "security" -v

# 测试报告查看
test-report:
	@echo "==> 生成测试报告..."
	@pytest tests/unit/ tests/integration/ -v --html=reports/html/index.html --self-contained-html --cov=services --cov-report=html:htmlcov --cov-report=xml:reports/coverage.xml
	@echo "==> 覆盖率报告: htmlcov/index.html"
	@echo "==> HTML测试报告: reports/html/index.html"
	@open reports/html/index.html 2>/dev/null || xdg-open reports/html/index.html 2>/dev/null || echo "请手动打开报告文件"

# 集成测试 - 全部
test-integration:
	@echo "==> 运行所有集成测试..."
	@pytest tests/integration/ -v --tb=short --with-db

# 集成测试 - 按阶段 (对应测试计划)
test-integration-dm:
	@echo "==> 运行数据管理员模块集成测试..."
	@pytest tests/integration/test_metadata*.py tests/integration/test_sensitivity*.py tests/integration/test_asset*.py tests/integration/test_lineage*.py -v --with-db

test-integration-de:
	@echo "==> 运行数据工程师模块集成测试..."
	@pytest tests/integration/test_etl*.py tests/integration/test_table_fusion*.py -v --with-db

test-integration-ae:
	@echo "==> 运行算法工程师模块集成测试..."
	@pytest tests/integration/test_model*.py -v --with-db

test-integration-bu:
	@echo "==> 运行业务用户模块集成测试..."
	@pytest tests/integration/test_knowledge*.py tests/integration/test_intelligent*.py tests/integration/test_text_to_sql*.py -v --with-db --with-milvus

test-integration-sa:
	@echo "==> 运行系统管理员模块集成测试..."
	@pytest tests/integration/test_user*.py tests/integration/test_audit*.py -v --with-db

# 前端测试
test-frontend:
	@echo "==> 运行前端单元测试..."
	@cd web && npm run test -- --run

test-frontend-coverage:
	@echo "==> 运行前端测试并生成覆盖率..."
	@cd web && npm run test:coverage

# E2E 测试 - 按项目
test-e2e-core:
	@echo "==> 运行核心页面 E2E 测试..."
	@cd tests/e2e && npx playwright test --project=chromium-fast core-pages*.spec.ts

test-e2e-data:
	@echo "==> 运行 Data 深度 E2E 测试..."
	@cd tests/e2e && npx playwright test --project=chromium-acceptance data-deep.spec.ts

test-e2e-agent:
	@echo "==> 运行 Agent 深度 E2E 测试..."
	@cd tests/e2e && npx playwright test --project=chromium-acceptance agent-deep.spec.ts

test-e2e-model:
	@echo "==> 运行 Model 深度 E2E 测试..."
	@cd tests/e2e && npx playwright test --project=chromium-acceptance model-deep.spec.ts

test-e2e-lifecycle:
	@echo "==> 运行用户生命周期 E2E 测试..."
	@cd tests/e2e && npx playwright test --project=user-lifecycle

# 专项测试
test-performance:
	@echo "==> 运行性能测试..."
	@pytest tests/performance/ -v --benchmark

test-security:
	@echo "==> 运行安全测试..."
	@pytest tests/ -m "security" -v

# 测试计划执行脚本
test-plan:
	@echo "==> 使用测试计划脚本..."
	@python3 tests/run_tests.py --help

test-plan-phase2:
	@echo "==> 执行测试计划第二阶段（单元测试）..."
	@python3 tests/run_tests.py --phase 2

test-plan-phase3:
	@echo "==> 执行测试计划第三阶段（集成测试）..."
	@python3 tests/run_tests.py --phase 3

test-plan-phase4:
	@echo "==> 执行测试计划第四阶段（E2E测试）..."
	@python3 tests/run_tests.py --phase 4

test-plan-all:
	@echo "==> 执行完整测试计划..."
	@python3 tests/run_tests.py --all

# 快速回归测试 (P0 用例)
test-regression:
	@echo "==> 运行回归测试 (P0 用例)..."
	@pytest tests/unit/ tests/integration/ -m "not slow" -v --tb=short
	@cd tests/e2e && npx playwright test --project=chromium-fast

# 测试报告
test-report:
	@echo "==> 查看测试报告..."
	@echo "  覆盖率报告: reports/coverage/index.html"
	@echo "  E2E 报告: tests/e2e/playwright-report/index.html"
	@open reports/coverage/index.html 2>/dev/null || xdg-open reports/coverage/index.html 2>/dev/null || echo "请手动打开报告文件"

# ============================================
# 数据库初始化
# ============================================

# 运行数据库初始化 Job
init-db:
	@echo "==> 运行数据库初始化 Job..."
	kubectl apply -f deploy/kubernetes/jobs/data-init-job.yaml
	kubectl apply -f deploy/kubernetes/jobs/agent-init-job.yaml
	@echo "==> 等待初始化完成..."
	@kubectl wait --for=condition=complete job/data-db-init -n one-data-data --timeout=300s || true
	@kubectl wait --for=condition=complete job/agent-db-init -n one-data-agent --timeout=300s || true
	@echo "==> 数据库初始化完成"

# ============================================
# 端口转发
# ============================================

# 后台端口转发
forward:
	@bash deploy/scripts/port-forward.sh &

# 前台端口转发
forward-interactive:
	@bash deploy/scripts/port-forward.sh

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
	@bash deploy/scripts/clean.sh

# 清理所有资源（包括 Kind 集群）
clean-all:
	@echo "==> 删除应用服务..."
	kubectl delete -f deploy/kubernetes/applications/ --ignore-not-found=true --recursive
	@echo "==> 删除基础设施..."
	kubectl delete -f deploy/kubernetes/infrastructure/ --ignore-not-found=true --recursive
	@echo "==> 删除基础资源..."
	kubectl delete -f deploy/kubernetes/base/ --ignore-not-found=true
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
	helm lint deploy/helm/charts/one-data || true

# 打包 Helm Charts
helm-package:
	@echo "==> 打包 Helm Charts..."
	helm package deploy/helm/charts/one-data

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
	kubectl apply -f deploy/kubernetes/applications/web-frontend/deployment.yaml
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

# ============================================
# 开发环境运维脚本
# ============================================

# 启动开发环境
dev-start:
	@bash scripts/dev/dev-start.sh $(ARGS)

# 停止开发环境
dev-stop:
	@bash scripts/dev/dev-stop.sh $(ARGS)

# 查看服务状态
dev-status:
	@bash scripts/dev/dev-status.sh $(ARGS)

# 查看日志
dev-logs:
	@bash scripts/dev/dev-logs.sh $(ARGS)

# 数据库操作
dev-db:
	@bash scripts/dev/dev-db.sh $(ARGS)

# 清理操作
dev-clean:
	@bash scripts/dev/dev-clean.sh $(ARGS)

# 重置环境
dev-reset:
	@bash scripts/dev/dev-reset.sh $(ARGS)

# 进入容器
dev-shell:
	@bash scripts/dev/dev-shell.sh $(ARGS)

# 健康检查
dev-check:
	@bash scripts/dev/dev-check.sh $(ARGS)

# 快捷别名
dev: dev-start
up: dev-start
down: dev-stop

# ============================================
# 种子数据（初始化数据）
# ============================================

# 导入种子数据
seed:
	@echo "==> 导入种子数据..."
	@python3 scripts/seed.py

# 预览种子数据导入
seed-dry-run:
	@echo "==> 预览种子数据导入（不实际写入）..."
	@python3 scripts/seed.py --dry-run

# 强制导入种子数据（覆盖已有）
seed-force:
	@echo "==> 强制导入种子数据..."
	@python3 scripts/seed.py --force

# 启动开发环境并导入种子数据
dev-seed:
	@echo "==> 启动开发环境并导入种子数据..."
	@bash scripts/dev/dev-start.sh --seed
