-- OCR服务数据库初始化脚本

-- OCR任务表
CREATE TABLE IF NOT EXISTS ocr_tasks (
    id VARCHAR(36) PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL DEFAULT 'default',
    user_id VARCHAR(64) NOT NULL DEFAULT 'system',
    document_name VARCHAR(255) NOT NULL,
    document_type VARCHAR(50) NOT NULL COMMENT 'pdf, word, excel, image等',
    document_path VARCHAR(500) NOT NULL,
    file_size BIGINT DEFAULT 0,
    extraction_type VARCHAR(50) NOT NULL DEFAULT 'general' COMMENT 'general, invoice, contract, purchase_order等',
    template_id VARCHAR(36),
    extraction_config JSON,
    status ENUM('pending', 'processing', 'completed', 'failed') DEFAULT 'pending',
    progress FLOAT DEFAULT 0,
    raw_text MEDIUMTEXT,
    structured_data JSON,
    confidence_score DECIMAL(3,2),
    result_summary JSON,
    error_message TEXT,
    is_verified BOOLEAN DEFAULT FALSE,
    verified_by VARCHAR(64),
    verified_at TIMESTAMP NULL,
    started_at TIMESTAMP NULL,
    completed_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_tenant (tenant_id),
    INDEX idx_status (status),
    INDEX idx_extraction_type (extraction_type),
    INDEX idx_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='OCR任务表';

-- OCR结果详情表（分页存储）
CREATE TABLE IF NOT EXISTS ocr_results (
    id VARCHAR(36) PRIMARY KEY,
    task_id VARCHAR(36) NOT NULL,
    page_number INT NOT NULL DEFAULT 1,
    text_content MEDIUMTEXT,
    tables JSON,
    layout_info JSON COMMENT '布局分析结果',
    confidence_score DECIMAL(3,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES ocr_tasks(id) ON DELETE CASCADE,
    INDEX idx_task (task_id),
    INDEX idx_page (page_number)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='OCR识别结果详情表';

-- 表格数据表
CREATE TABLE IF NOT EXISTS ocr_tables (
    id VARCHAR(36) PRIMARY KEY,
    task_id VARCHAR(36) NOT NULL,
    table_index INT NOT NULL DEFAULT 0,
    page_number INT NOT NULL DEFAULT 1,
    table_type VARCHAR(50) DEFAULT 'general' COMMENT 'price_details, payment_schedule等',
    row_count INT NOT NULL DEFAULT 0,
    col_count INT NOT NULL DEFAULT 0,
    headers JSON,
    rows JSON,
    merged_cells JSON,
    confidence DECIMAL(3,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES ocr_tasks(id) ON DELETE CASCADE,
    INDEX idx_task (task_id),
    INDEX idx_type (table_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='表格数据表';

-- 提取模板表
CREATE TABLE IF NOT EXISTS ocr_templates (
    id VARCHAR(36) PRIMARY KEY,
    tenant_id VARCHAR(64) DEFAULT 'default',
    name VARCHAR(255) NOT NULL,
    description TEXT,
    type VARCHAR(50) NOT NULL COMMENT 'invoice, contract, purchase_order等',
    category VARCHAR(50) COMMENT 'financial, legal, procurement等',
    template_config JSON NOT NULL COMMENT '完整的模板配置',
    is_public BOOLEAN DEFAULT TRUE,
    is_active BOOLEAN DEFAULT TRUE,
    created_by VARCHAR(64),
    usage_count INT DEFAULT 0,
    last_used_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_type (type),
    INDEX idx_tenant (tenant_id),
    INDEX idx_category (category)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='提取模板表';

-- 跨字段校验结果表
CREATE TABLE IF NOT EXISTS ocr_validations (
    id VARCHAR(36) PRIMARY KEY,
    task_id VARCHAR(36) NOT NULL,
    validation_type VARCHAR(50) NOT NULL COMMENT 'amount_sum, date_logic, tax_calculation等',
    rule_name VARCHAR(100) NOT NULL,
    is_valid BOOLEAN DEFAULT FALSE,
    expected_value VARCHAR(255),
    actual_value VARCHAR(255),
    error_message TEXT,
    severity ENUM('error', 'warning', 'info') DEFAULT 'warning',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES ocr_tasks(id) ON DELETE CASCADE,
    INDEX idx_task (task_id),
    INDEX idx_type (validation_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='跨字段校验结果表';

-- 布局分析结果表
CREATE TABLE IF NOT EXISTS ocr_layouts (
    id VARCHAR(36) PRIMARY KEY,
    task_id VARCHAR(36) NOT NULL,
    page_number INT NOT NULL DEFAULT 1,
    layout_type VARCHAR(50) COMMENT 'cover, content, attachment, signature',
    regions JSON COMMENT '页面区域划分',
    signature_regions JSON COMMENT '签名区域',
    seal_regions JSON COMMENT '印章区域',
    table_regions JSON COMMENT '表格区域',
    header_text TEXT,
    footer_text TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES ocr_tasks(id) ON DELETE CASCADE,
    INDEX idx_task (task_id),
    INDEX idx_page (page_number)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='布局分析结果表';

-- 批量任务表
CREATE TABLE IF NOT EXISTS ocr_batch_tasks (
    id VARCHAR(36) PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL DEFAULT 'default',
    user_id VARCHAR(64) NOT NULL DEFAULT 'system',
    batch_name VARCHAR(255),
    status ENUM('pending', 'processing', 'completed', 'partial_failed', 'failed') DEFAULT 'pending',
    total_files INT DEFAULT 0,
    completed_files INT DEFAULT 0,
    failed_files INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP NULL,
    INDEX idx_tenant (tenant_id),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='批量任务表';

-- 批量任务关联表
CREATE TABLE IF NOT EXISTS ocr_batch_items (
    id VARCHAR(36) PRIMARY KEY,
    batch_id VARCHAR(36) NOT NULL,
    task_id VARCHAR(36) NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    status ENUM('pending', 'processing', 'completed', 'failed') DEFAULT 'pending',
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (batch_id) REFERENCES ocr_batch_tasks(id) ON DELETE CASCADE,
    FOREIGN KEY (task_id) REFERENCES ocr_tasks(id) ON DELETE CASCADE,
    INDEX idx_batch (batch_id),
    INDEX idx_task (task_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='批量任务关联表';

-- 插入默认模板
INSERT INTO ocr_templates (id, tenant_id, name, description, type, category, template_config, created_by) VALUES
('template-invoice-001', 'default', '增值税发票模板', '用于提取增值税发票的关键信息', 'invoice', 'financial', JSON_LOAD('/app/templates/invoice.json'), 'system'),
('template-contract-001', 'default', '通用合同模板', '用于提取合同的基本信息', 'contract', 'legal', JSON_LOAD('/app/templates/contract.json'), 'system')
ON DUPLICATE KEY UPDATE updated_at = CURRENT_TIMESTAMP;
