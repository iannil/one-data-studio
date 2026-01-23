-- Bisheng API 数据库初始化脚本
-- Sprint 4.2: 数据持久化
-- Phase 6: Sprint 6.1-6.3 - 工作流执行、文档索引表

-- 创建数据库（如果不存在）
CREATE DATABASE IF NOT EXISTS one_data_bisheng
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;

USE one_data_bisheng;

-- 工作流表
CREATE TABLE IF NOT EXISTS workflows (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    workflow_id VARCHAR(64) NOT NULL UNIQUE COMMENT '工作流唯一标识',
    name VARCHAR(255) NOT NULL COMMENT '工作流名称',
    description TEXT COMMENT '工作流描述',
    type VARCHAR(32) NOT NULL DEFAULT 'rag' COMMENT '类型: rag, sql, agent',
    status VARCHAR(32) NOT NULL DEFAULT 'stopped' COMMENT '状态: running, stopped, error',
    definition TEXT COMMENT '工作流定义 (JSON)',
    created_by VARCHAR(128) COMMENT '创建者',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_type (type),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='工作流表';

-- 会话表
CREATE TABLE IF NOT EXISTS conversations (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    conversation_id VARCHAR(64) NOT NULL UNIQUE COMMENT '会话唯一标识',
    user_id VARCHAR(128) COMMENT '用户ID',
    title VARCHAR(255) COMMENT '会话标题',
    model VARCHAR(64) COMMENT '使用的模型',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_user_id (user_id),
    INDEX idx_updated_at (updated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='会话表';

-- 消息表
CREATE TABLE IF NOT EXISTS messages (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    conversation_id VARCHAR(64) NOT NULL COMMENT '所属会话ID',
    role VARCHAR(32) NOT NULL COMMENT '角色: user, assistant, system',
    content TEXT NOT NULL COMMENT '消息内容',
    tokens INT COMMENT 'Token 数量',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id) ON DELETE CASCADE,
    INDEX idx_conversation_id (conversation_id),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='消息表';

-- Phase 6: Sprint 6.1 - 工作流执行记录表
CREATE TABLE IF NOT EXISTS workflow_executions (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    execution_id VARCHAR(64) NOT NULL UNIQUE COMMENT '执行唯一标识',
    workflow_id VARCHAR(64) NOT NULL COMMENT '工作流ID',
    status VARCHAR(32) NOT NULL DEFAULT 'pending' COMMENT '状态: pending, running, completed, failed, stopped',
    inputs TEXT COMMENT '输入数据 (JSON)',
    outputs TEXT COMMENT '输出数据 (JSON)',
    node_results TEXT COMMENT '节点执行结果 (JSON)',
    error TEXT COMMENT '错误信息',
    started_at TIMESTAMP NULL COMMENT '开始时间',
    completed_at TIMESTAMP NULL COMMENT '完成时间',
    duration_ms INT COMMENT '执行时长（毫秒）',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_workflow_id (workflow_id),
    INDEX idx_status (status),
    INDEX idx_execution_id (execution_id),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='工作流执行记录表';

-- Phase 6: Sprint 6.4 - 执行日志表
CREATE TABLE IF NOT EXISTS execution_logs (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    execution_id VARCHAR(64) NOT NULL COMMENT '执行ID',
    node_id VARCHAR(64) COMMENT '节点ID',
    level VARCHAR(16) NOT NULL DEFAULT 'info' COMMENT '日志级别: info, warning, error',
    message TEXT COMMENT '日志消息',
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '时间戳',
    INDEX idx_execution_id (execution_id),
    INDEX idx_level (level),
    INDEX idx_timestamp (timestamp)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='执行日志表';

-- Phase 6: Sprint 6.3 - 已索引文档表
CREATE TABLE IF NOT EXISTS indexed_documents (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    doc_id VARCHAR(64) NOT NULL UNIQUE COMMENT '文档唯一标识',
    collection_name VARCHAR(128) NOT NULL COMMENT '向量集合名称',
    file_name VARCHAR(255) COMMENT '文件名',
    title VARCHAR(255) COMMENT '文档标题',
    content TEXT COMMENT '文档内容（预览）',
    chunk_count INT DEFAULT 0 COMMENT '文档块数量',
    metadata TEXT COMMENT '元数据 (JSON)',
    created_by VARCHAR(128) COMMENT '创建者',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_collection_name (collection_name),
    INDEX idx_doc_id (doc_id),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='已索引文档表';
