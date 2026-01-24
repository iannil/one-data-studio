-- Alldata API 数据库初始化脚本
-- 用于 Sprint 1.1 持久化改造

-- 创建数据库（如果不存在）
CREATE DATABASE IF NOT EXISTS one_data_alldata
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;

USE one_data_alldata;

-- 数据集表
CREATE TABLE IF NOT EXISTS datasets (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    dataset_id VARCHAR(64) NOT NULL UNIQUE COMMENT '数据集唯一标识',
    name VARCHAR(255) NOT NULL COMMENT '数据集名称',
    description TEXT COMMENT '数据集描述',
    storage_type VARCHAR(32) NOT NULL DEFAULT 's3' COMMENT '存储类型: s3, hdfs, local',
    storage_path VARCHAR(512) NOT NULL COMMENT '存储路径',
    format VARCHAR(32) NOT NULL DEFAULT 'csv' COMMENT '文件格式: csv, parquet, json, jsonl',
    status VARCHAR(32) NOT NULL DEFAULT 'active' COMMENT '状态: active, archived, deleted',
    row_count BIGINT DEFAULT 0 COMMENT '记录数',
    size_bytes BIGINT DEFAULT 0 COMMENT '文件大小(字节)',
    tags JSON COMMENT '标签列表',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_name (name),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='数据集表';

-- 数据集版本表
CREATE TABLE IF NOT EXISTS dataset_versions (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    version_id VARCHAR(64) NOT NULL UNIQUE COMMENT '版本唯一标识',
    dataset_id VARCHAR(64) NOT NULL COMMENT '所属数据集ID',
    version_number INT NOT NULL COMMENT '版本号',
    storage_path VARCHAR(512) NOT NULL COMMENT '版本存储路径',
    description TEXT COMMENT '版本描述',
    row_count BIGINT DEFAULT 0 COMMENT '记录数',
    size_bytes BIGINT DEFAULT 0 COMMENT '文件大小(字节)',
    checksum VARCHAR(64) COMMENT '文件校验和',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    FOREIGN KEY (dataset_id) REFERENCES datasets(dataset_id) ON DELETE CASCADE,
    INDEX idx_dataset_id (dataset_id),
    INDEX idx_version_number (version_number)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='数据集版本表';

-- 数据集 Schema 表（列定义）
CREATE TABLE IF NOT EXISTS dataset_columns (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    dataset_id VARCHAR(64) NOT NULL COMMENT '所属数据集ID',
    column_name VARCHAR(128) NOT NULL COMMENT '列名',
    column_type VARCHAR(64) NOT NULL COMMENT '数据类型',
    is_nullable BOOLEAN DEFAULT TRUE COMMENT '是否可空',
    description TEXT COMMENT '列描述',
    position INT NOT NULL COMMENT '列位置',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    FOREIGN KEY (dataset_id) REFERENCES datasets(dataset_id) ON DELETE CASCADE,
    INDEX idx_dataset_id (dataset_id),
    UNIQUE KEY uk_dataset_column (dataset_id, column_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='数据集列定义表';

-- 元数据 - 数据库列表
CREATE TABLE IF NOT EXISTS metadata_databases (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    database_name VARCHAR(128) NOT NULL UNIQUE COMMENT '数据库名',
    description TEXT COMMENT '描述',
    owner VARCHAR(128) COMMENT '所有者',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='元数据库表';

-- 元数据 - 表列表
CREATE TABLE IF NOT EXISTS metadata_tables (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    table_name VARCHAR(128) NOT NULL COMMENT '表名',
    database_name VARCHAR(128) NOT NULL COMMENT '所属数据库',
    description TEXT COMMENT '表描述',
    row_count BIGINT DEFAULT 0 COMMENT '行数',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    FOREIGN KEY (database_name) REFERENCES metadata_databases(database_name) ON DELETE CASCADE,
    INDEX idx_database_name (database_name),
    UNIQUE KEY uk_db_table (database_name, table_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='元数据表';

-- 元数据 - 列定义
CREATE TABLE IF NOT EXISTS metadata_columns (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    table_name VARCHAR(128) NOT NULL COMMENT '表名',
    database_name VARCHAR(128) NOT NULL COMMENT '数据库名',
    column_name VARCHAR(128) NOT NULL COMMENT '列名',
    column_type VARCHAR(64) NOT NULL COMMENT '数据类型',
    is_nullable BOOLEAN DEFAULT TRUE COMMENT '是否可空',
    description TEXT COMMENT '列描述',
    position INT NOT NULL COMMENT '列位置',
    FOREIGN KEY (database_name) REFERENCES metadata_databases(database_name) ON DELETE CASCADE,
    FOREIGN KEY (table_name, database_name) REFERENCES metadata_tables(table_name, database_name) ON DELETE CASCADE,
    INDEX idx_table (table_name, database_name),
    UNIQUE KEY uk_table_column (table_name, database_name, column_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='元数据列定义表';

-- 文件上传记录表
CREATE TABLE IF NOT EXISTS file_uploads (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    upload_id VARCHAR(64) NOT NULL UNIQUE COMMENT '上传ID',
    dataset_id VARCHAR(64) COMMENT '关联数据集ID',
    file_name VARCHAR(512) NOT NULL COMMENT '文件名',
    file_size BIGINT DEFAULT 0 COMMENT '文件大小',
    content_type VARCHAR(128) COMMENT '内容类型',
    storage_path VARCHAR(512) NOT NULL COMMENT 'MinIO 存储路径',
    status VARCHAR(32) NOT NULL DEFAULT 'pending' COMMENT '状态: pending, completed, failed',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    completed_at TIMESTAMP NULL COMMENT '完成时间',
    FOREIGN KEY (dataset_id) REFERENCES datasets(dataset_id) ON DELETE SET NULL,
    INDEX idx_dataset_id (dataset_id),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='文件上传记录表';

-- 插入示例数据
INSERT INTO metadata_databases (database_name, description, owner) VALUES
    ('sales_dw', '销售数据仓库', 'data_team'),
    ('user_dw', '用户数据仓库', 'data_team')
ON DUPLICATE KEY UPDATE description=VALUES(description);

INSERT INTO metadata_tables (table_name, database_name, description, row_count) VALUES
    ('orders', 'sales_dw', '订单表', 10000000),
    ('customers', 'sales_dw', '客户表', 1000000),
    ('user_profile', 'user_dw', '用户画像表', 5000000)
ON DUPLICATE KEY UPDATE description=VALUES(description);

INSERT INTO metadata_columns (table_name, database_name, column_name, column_type, is_nullable, description, position) VALUES
    ('orders', 'sales_dw', 'id', 'BIGINT', FALSE, '主键ID', 1),
    ('orders', 'sales_dw', 'customer_id', 'BIGINT', FALSE, '客户ID', 2),
    ('orders', 'sales_dw', 'amount', 'DECIMAL(10,2)', FALSE, '金额', 3),
    ('orders', 'sales_dw', 'created_at', 'TIMESTAMP', FALSE, '创建时间', 4),
    ('customers', 'sales_dw', 'id', 'BIGINT', FALSE, '主键ID', 1),
    ('customers', 'sales_dw', 'name', 'VARCHAR(128)', FALSE, '客户名称', 2),
    ('customers', 'sales_dw', 'email', 'VARCHAR(256)', TRUE, '邮箱', 3)
ON DUPLICATE KEY UPDATE description=VALUES(description);

-- 插入示例数据集
INSERT INTO datasets (dataset_id, name, description, storage_type, storage_path, format, status, row_count, size_bytes, tags) VALUES
    ('ds-001', 'sales_data_v1.0', '销售数据清洗结果', 's3', 's3://etl-output/sales/2024-01/', 'parquet', 'active', 1000000, 52428800, '["sales", "cleansed", "2024q1"]')
ON DUPLICATE KEY UPDATE description=VALUES(description);

-- 插入示例数据集列
INSERT INTO dataset_columns (dataset_id, column_name, column_type, is_nullable, description, position) VALUES
    ('ds-001', 'id', 'INT64', FALSE, '记录ID', 1),
    ('ds-001', 'customer_id', 'INT64', FALSE, '客户ID', 2),
    ('ds-001', 'amount', 'DECIMAL(10,2)', FALSE, '金额', 3),
    ('ds-001', 'created_at', 'TIMESTAMP', FALSE, '创建时间', 4)
ON DUPLICATE KEY UPDATE description=VALUES(description);
