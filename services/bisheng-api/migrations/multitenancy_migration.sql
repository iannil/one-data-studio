-- ONE-DATA-STUDIO 多租户迁移脚本
-- Sprint 13: 添加 tenant_id 字段到所有业务表
-- 运行方式: mysql -u root -p one_data_bisheng < multitenancy_migration.sql

-- 1. 为 workflows 表添加 tenant_id
ALTER TABLE workflows
ADD COLUMN tenant_id VARCHAR(64) DEFAULT NULL COMMENT '租户 ID' AFTER id;

CREATE INDEX ix_workflows_tenant ON workflows(tenant_id);
CREATE INDEX ix_workflows_tenant_created ON workflows(tenant_id, created_at);

-- 2. 为 conversations 表添加 tenant_id
ALTER TABLE conversations
ADD COLUMN tenant_id VARCHAR(64) DEFAULT NULL COMMENT '租户 ID' AFTER id;

CREATE INDEX ix_conversations_tenant ON conversations(tenant_id);
CREATE INDEX ix_conversations_tenant_created ON conversations(tenant_id, created_at);

-- 3. 为 workflow_executions 表添加 tenant_id
ALTER TABLE workflow_executions
ADD COLUMN tenant_id VARCHAR(64) DEFAULT NULL COMMENT '租户 ID' AFTER id;

CREATE INDEX ix_workflow_executions_tenant ON workflow_executions(tenant_id);
CREATE INDEX ix_workflow_executions_tenant_status ON workflow_executions(tenant_id, status);

-- 4. 为 indexed_documents 表添加 tenant_id
ALTER TABLE indexed_documents
ADD COLUMN tenant_id VARCHAR(64) DEFAULT NULL COMMENT '租户 ID' AFTER id;

CREATE INDEX ix_indexed_documents_tenant ON indexed_documents(tenant_id);
CREATE INDEX ix_indexed_documents_tenant_collection ON indexed_documents(tenant_id, collection_name);

-- 5. 为 workflow_schedules 表添加 tenant_id
ALTER TABLE workflow_schedules
ADD COLUMN tenant_id VARCHAR(64) DEFAULT NULL COMMENT '租户 ID' AFTER id;

CREATE INDEX ix_workflow_schedules_tenant ON workflow_schedules(tenant_id);

-- 6. 为 agent_templates 表添加 tenant_id
ALTER TABLE agent_templates
ADD COLUMN tenant_id VARCHAR(64) DEFAULT NULL COMMENT '租户 ID' AFTER id;

CREATE INDEX ix_agent_templates_tenant ON agent_templates(tenant_id);

-- 7. 创建租户配额表
CREATE TABLE IF NOT EXISTS tenant_quotas (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL UNIQUE COMMENT '租户 ID',
    max_workflows INT DEFAULT 100 COMMENT '最大工作流数',
    max_documents INT DEFAULT 1000 COMMENT '最大文档数',
    max_conversations INT DEFAULT 500 COMMENT '最大会话数',
    max_vector_storage_mb INT DEFAULT 10240 COMMENT '最大向量存储(MB)',
    max_api_calls_per_hour INT DEFAULT 10000 COMMENT '每小时最大 API 调用数',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX ix_tenant_quotas_tenant (tenant_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 8. 创建租户使用统计表
CREATE TABLE IF NOT EXISTS tenant_usage (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL COMMENT '租户 ID',
    resource_type VARCHAR(32) NOT NULL COMMENT '资源类型',
    usage_count INT DEFAULT 0 COMMENT '使用量',
    usage_date DATE NOT NULL COMMENT '统计日期',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_tenant_resource_date (tenant_id, resource_type, usage_date),
    INDEX ix_tenant_usage_tenant (tenant_id),
    INDEX ix_tenant_usage_date (usage_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 9. 更新现有数据的 tenant_id（可选，设置默认租户）
-- UPDATE workflows SET tenant_id = 'default' WHERE tenant_id IS NULL;
-- UPDATE conversations SET tenant_id = 'default' WHERE tenant_id IS NULL;
-- UPDATE workflow_executions SET tenant_id = 'default' WHERE tenant_id IS NULL;
-- UPDATE indexed_documents SET tenant_id = 'default' WHERE tenant_id IS NULL;
-- UPDATE workflow_schedules SET tenant_id = 'default' WHERE tenant_id IS NULL;
-- UPDATE agent_templates SET tenant_id = 'default' WHERE tenant_id IS NULL;

-- 完成提示
SELECT 'Multi-tenancy migration completed successfully!' AS status;
