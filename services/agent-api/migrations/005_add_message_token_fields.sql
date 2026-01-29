-- Sprint 5: 添加消息持久化和 Token 统计字段
-- 运行此脚本以更新现有数据库 schema

-- 为 conversations 表添加 message_count 字段
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS message_count INT DEFAULT 0 COMMENT '消息数量';

-- 为 messages 表添加新字段
ALTER TABLE messages ADD COLUMN IF NOT EXISTS message_id VARCHAR(64) COMMENT '消息唯一标识';
ALTER TABLE messages ADD COLUMN IF NOT EXISTS model VARCHAR(64) COMMENT '使用的模型';
ALTER TABLE messages ADD COLUMN IF NOT EXISTS prompt_tokens INT DEFAULT 0 COMMENT '输入 Token 数量';
ALTER TABLE messages ADD COLUMN IF NOT EXISTS completion_tokens INT DEFAULT 0 COMMENT '输出 Token 数量';
ALTER TABLE messages ADD COLUMN IF NOT EXISTS total_tokens INT DEFAULT 0 COMMENT '总 Token 数量';

-- 为现有消息生成 message_id
UPDATE messages SET message_id = CONCAT('msg-', id) WHERE message_id IS NULL;

-- 添加唯一约束（如果不存在）
-- 注意：MySQL 语法，其他数据库可能需要调整
ALTER TABLE messages ADD UNIQUE INDEX IF NOT EXISTS idx_messages_message_id (message_id);

-- 更新 conversations 的 message_count
UPDATE conversations c
SET message_count = (SELECT COUNT(*) FROM messages m WHERE m.conversation_id = c.conversation_id);
