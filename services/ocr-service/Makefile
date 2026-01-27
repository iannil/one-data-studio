# OCR服务Makefile
# 提供常用的开发和管理命令

.PHONY: help install test lint format build up down restart logs shell clean

# 默认目标
.DEFAULT_GOAL := help

# 变量
PYTHON := python3
PIP := pip3
DOCKER_COMPOSE := docker-compose
SERVICE_DIR := services/ocr-service
COMPOSE_FILE := deploy/local/docker-compose.yml

# 颜色
GREEN := \033[0;32m
YELLOW := \033[1;33m
NC := \033[0m

help: ## 显示帮助信息
	@echo "$(GREEN)OCR服务管理命令$(NC)"
	@echo ""
	@echo "开发命令:"
	@echo "  make install        安装依赖"
	@echo "  make test          运行测试"
	@echo "  make lint          代码检查"
	@echo "  make format        代码格式化"
	@echo "  make run           运行服务"
	@echo ""
	@echo "Docker命令:"
	@echo "  make build         构建镜像"
	@echo "  make up            启动服务"
	@echo "  make down          停止服务"
	@echo "  make restart       重启服务"
	@echo "  make logs          查看日志"
	@echo "  make shell         进入容器"
	@echo "  make clean         清理容器和镜像"
	@echo ""
	@echo "部署命令:"
	@echo "  make deploy        完整部署"
	@echo "  make health        健康检查"
	@echo "  make templates     加载模板"
	@echo ""
	@echo "测试命令:"
	@echo "  make test-unit     单元测试"
	@echo "  make test-integ    集成测试"
	@echo "  make test-perf     性能测试"
	@echo "  make test-all      所有测试"

install: ## 安装Python依赖
	@echo "$(GREEN)安装依赖...$(NC)"
	cd $(SERVICE_DIR) && $(PIP) install -r requirements.txt
	@echo "$(GREEN)依赖安装完成$(NC)"

test: ## 运行所有测试
	@echo "$(GREEN)运行测试...$(NC)"
	cd $(SERVICE_DIR) && $(PYTHON) -m pytest tests/ -v

test-unit: ## 运行单元测试
	@echo "$(GREEN)运行单元测试...$(NC)"
	cd $(SERVICE_DIR) && $(PYTHON) -m pytest tests/ -v -k "not integration"

test-integ: ## 运行集成测试
	@echo "$(GREEN)运行集成测试...$(NC)"
	cd $(SERVICE_DIR) && $(PYTHON) -m pytest tests/test_integration.py -v

test-perf: ## 运行性能测试
	@echo "$(GREEN)运行性能测试...$(NC)"
	cd $(SERVICE_DIR) && $(PYTHON) scripts/performance_test.py

lint: ## 代码检查
	@echo "$(GREEN)代码检查...$(NC)"
	cd $(SERVICE_DIR) && flake8 api/ services/ --count --select=E9,F63,F7,F82 --show-source --statistics

format: ## 代码格式化
	@echo "$(GREEN)代码格式化...$(NC)"
	cd $(SERVICE_DIR) && black api/ services/ && isort api/ services/

run: ## 运行服务（本地）
	@echo "$(GREEN)启动服务...$(NC)"
	cd $(SERVICE_DIR) && $(PYTHON) -m uvicorn app:app --host 0.0.0.0 --port 8007 --reload

build: ## 构建Docker镜像
	@echo "$(GREEN)构建镜像...$(NC)"
	$(DOCKER_COMPOSE) -f $(COMPOSE_FILE) build ocr-service

up: ## 启动服务（Docker）
	@echo "$(GREEN)启动服务...$(NC)"
	$(DOCKER_COMPOSE) -f $(COMPOSE_FILE) up -d ocr-service
	@echo "$(GREEN)服务已启动，访问 http://localhost:8007$(NC)"

down: ## 停止服务
	@echo "$(YELLOW)停止服务...$(NC)"
	$(DOCKER_COMPOSE) -f $(COMPOSE_FILE) down

restart: ## 重启服务
	@echo "$(YELLOW)重启服务...$(NC)"
	$(DOCKER_COMPOSE) -f $(COMPOSE_FILE) restart ocr-service

logs: ## 查看服务日志
	$(DOCKER_COMPOSE) -f $(COMPOSE_FILE) logs -f ocr-service

shell: ## 进入服务容器
	$(DOCKER_COMPOSE) -f $(COMPOSE_FILE) exec ocr-service bash

clean: ## 清理容器和镜像
	@echo "$(YELLOW)清理资源...$(NC)"
	$(DOCKER_COMPOSE) -f $(COMPOSE_FILE) down -v
	docker rmi onedata-ocr-service 2>/dev/null || true
	@echo "$(GREEN)清理完成$(NC)"

deploy: ## 完整部署
	@echo "$(GREEN)开始部署...$(NC)"
	@$(MAKE) build
	@$(MAKE) up
	@sleep 10
	@$(MAKE) health
	@$(MAKE) templates
	@echo "$(GREEN)部署完成！$(NC)"

health: ## 健康检查
	@echo "$(GREEN)检查服务健康状态...$(NC)"
	@curl -s http://localhost:8007/health | python3 -m json.tool || echo "服务不可用"

templates: ## 加载默认模板
	@echo "$(GREEN)加载默认模板...$(NC)"
	@curl -s -X POST http://localhost:8007/api/v1/ocr/templates/load-defaults | python3 -m json.tool

verify: ## 验证实施
	@echo "$(GREEN)验证实施...$(NC)"
	cd $(SERVICE_DIR) && $(PYTHON) scripts/verify_implementation.py

cli: ## 运行CLI工具
	cd $(SERVICE_DIR) && $(PYTHON) cli/ocr_cli.py

# 开发环境相关
dev-install: ## 安装开发依赖
	cd $(SERVICE_DIR) && $(PIP) install -r requirements.txt
	cd $(SERVICE_DIR) && $(PIP) install pytest pytest-cov black flake8 isort mypy

dev-up: ## 启动开发环境
	$(DOCKER_COMPOSE) -f $(COMPOSE_FILE) -f $(SERVICE_DIR)/docker-compose.dev.yml up -d

dev-down: ## 停止开发环境
	$(DOCKER_COMPOSE) -f $(COMPOSE_FILE) -f $(SERVICE_DIR)/docker-compose.dev.yml down

dev-logs: ## 查看开发环境日志
	$(DOCKER_COMPOSE) -f $(COMPOSE_FILE) -f $(SERVICE_DIR)/docker-compose.dev.yml logs -f

# 监控相关
monitoring-up: ## 启动监控服务
	cd $(SERVICE_DIR)/monitoring && $(DOCKER_COMPOSE) up -d

monitoring-down: ## 停止监控服务
	cd $(SERVICE_DIR)/monitoring && $(DOCKER_COMPOSE) down

monitoring-logs: ## 查看监控日志
	cd $(SERVICE_DIR)/monitoring && $(DOCKER_COMPOSE) logs -f

# 测试文档生成
gen-docs: ## 生成测试文档
	@echo "$(GREEN)生成测试文档...$(NC)"
	cd $(SERVICE_DIR) && $(PYTHON) tests/generate_documents.py

# 批量测试
batch-test: ## 批量功能测试
	@echo "$(GREEN)运行批量测试...$(NC)"
	cd $(SERVICE_DIR) && $(PYTHON) scripts/batch_test.py

# 完整测试流程
test-all: verify batch-test test
	@echo "$(GREEN)所有测试完成$(NC)"

# 数据库相关
db-migrate: ## 运行数据库迁移
	$(DOCKER_COMPOSE) -f $(COMPOSE_FILE) exec ocr-service python -c "from models.base import Base; from app import engine; Base.metadata.create_all(bind=engine)"

db-shell: ## 进入数据库Shell
	$(DOCKER_COMPOSE) -f $(COMPOSE_FILE) exec mysql mysql -uroot -p${MYSQL_PASSWORD} alldata

# Redis相关
redis-cli: ## 进入Redis CLI
	$(DOCKER_COMPOSE) -f $(COMPOSE_FILE) exec redis redis-cli

# 缓存操作
cache-clear: ## 清空Redis缓存
	$(DOCKER_COMPOSE) -f $(COMPOSE_FILE) exec redis redis-cli FLUSHALL

# 快速查看状态
status: ## 查看服务状态
	@$(DOCKER_COMPOSE) -f $(COMPOSE_FILE) ps

ps: status ## 查看服务状态（别名）

# 环境变量
check-env: ## 检查环境变量
	@echo "MYSQL_ROOT_PASSWORD=${MYSQL_ROOT_PASSWORD:-<not set>}"
	@echo "MYSQL_PASSWORD=${MYSQL_PASSWORD:-<not set>}"
	@echo "REDIS_PASSWORD=${REDIS_PASSWORD:-<not set>}"
	@echo "OPENAI_API_KEY=${OPENAI_API_KEY:+<set>}"
