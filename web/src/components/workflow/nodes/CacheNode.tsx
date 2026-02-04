import React, { memo } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { Card, Typography, Space, Input, InputNumber, Select, Tag } from 'antd';
import { DatabaseOutlined, ClockCircleOutlined } from '@ant-design/icons';

const { Text } = Typography;

interface CacheNodeData {
  label: string;
  cacheKey: string;
  ttl: number;
  cacheType: 'memory' | 'redis';
  namespace: string;
  skipIfExists: boolean;
}

/**
 * 缓存节点
 * Sprint 18: 工作流节点扩展
 */
const CacheNode: React.FC<NodeProps<CacheNodeData>> = ({ data, selected }) => {
  const ttlLabel = data.ttl >= 3600
    ? `${Math.floor(data.ttl / 3600)}小时`
    : data.ttl >= 60
    ? `${Math.floor(data.ttl / 60)}分钟`
    : `${data.ttl}秒`;

  return (
    <Card
      size="small"
      title={
        <Space>
          <DatabaseOutlined style={{ color: '#fa8c16' }} />
          <Text strong>{data.label || '缓存'}</Text>
        </Space>
      }
      style={{
        width: 220,
        border: selected ? '2px solid #fa8c16' : '1px solid #d9d9d9',
        borderRadius: 8,
      }}
      styles={{ body: { padding: '12px' } }}
    >
      <Handle type="target" position={Position.Top} style={{ background: '#fa8c16' }} />

      <Space direction="vertical" style={{ width: '100%' }} size="small">
        {/* 缓存键 */}
        <div>
          <Text type="secondary" style={{ fontSize: 12 }}>缓存键</Text>
          <Input
            size="small"
            value={data.cacheKey}
            placeholder="自动生成"
            style={{ marginTop: 4 }}
          />
        </div>

        {/* TTL 和类型 */}
        <div style={{ display: 'flex', gap: 8 }}>
          <div style={{ flex: 1 }}>
            <Text type="secondary" style={{ fontSize: 12 }}>过期时间</Text>
            <InputNumber
              size="small"
              min={1}
              value={data.ttl || 300}
              style={{ width: '100%', marginTop: 4 }}
            />
          </div>
          <div style={{ flex: 1 }}>
            <Text type="secondary" style={{ fontSize: 12 }}>类型</Text>
            <Select
              size="small"
              value={data.cacheType || 'memory'}
              style={{ width: '100%', marginTop: 4 }}
              options={[
                { label: '内存', value: 'memory' },
                { label: 'Redis', value: 'redis' },
              ]}
            />
          </div>
        </div>

        {/* 状态提示 */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <ClockCircleOutlined style={{ color: '#fa8c16', fontSize: 12 }} />
          <Text type="secondary" style={{ fontSize: 11 }}>
            TTL: {ttlLabel}
          </Text>
          <Tag color="orange" style={{ fontSize: 10, marginLeft: 'auto' }}>
            {data.cacheType === 'redis' ? 'Redis' : '内存'}
          </Tag>
        </div>
      </Space>

      <Handle type="source" position={Position.Bottom} style={{ background: '#fa8c16' }} />
    </Card>
  );
};

export default memo(CacheNode);
