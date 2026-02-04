import React, { memo } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { Card, Typography, Space, InputNumber, Switch, Tooltip, Input } from 'antd';
import { ReloadOutlined, ClockCircleOutlined } from '@ant-design/icons';

const { Text } = Typography;

interface RetryNodeData {
  label: string;
  maxRetries: number;
  initialDelay: number;
  maxDelay: number;
  exponentialBase: number;
  jitter: boolean;
  retryOnExceptions: string[];
}

/**
 * 重试节点
 * Sprint 18: 工作流节点扩展
 */
const RetryNode: React.FC<NodeProps<RetryNodeData>> = ({ data, selected }) => {
  return (
    <Card
      size="small"
      title={
        <Space>
          <ReloadOutlined style={{ color: '#eb2f96' }} />
          <Text strong>{data.label || '重试'}</Text>
        </Space>
      }
      style={{
        width: 220,
        border: selected ? '2px solid #eb2f96' : '1px solid #d9d9d9',
        borderRadius: 8,
      }}
      styles={{ body: { padding: '12px' } }}
    >
      <Handle type="target" position={Position.Top} style={{ background: '#eb2f96' }} />

      <Space direction="vertical" style={{ width: '100%' }} size="small">
        {/* 最大重试次数 */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Text type="secondary" style={{ fontSize: 12 }}>最大重试</Text>
          <InputNumber
            size="small"
            min={1}
            max={10}
            value={data.maxRetries || 3}
            style={{ width: 80 }}
          />
        </div>

        {/* 初始延迟 */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Tooltip title="第一次重试前的等待时间">
            <Text type="secondary" style={{ fontSize: 12 }}>初始延迟</Text>
          </Tooltip>
          <Space.Compact size="small">
            <InputNumber
              size="small"
              min={0.1}
              step={0.5}
              value={data.initialDelay || 1}
              style={{ width: 70 }}
            />
            <Input size="small" readOnly value="秒" style={{ width: 30 }} />
          </Space.Compact>
        </div>

        {/* 指数退避 */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Tooltip title="每次重试延迟增长的倍数">
            <Text type="secondary" style={{ fontSize: 12 }}>退避基数</Text>
          </Tooltip>
          <InputNumber
            size="small"
            min={1}
            max={5}
            step={0.5}
            value={data.exponentialBase || 2}
            style={{ width: 80 }}
          />
        </div>

        {/* 随机抖动 */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Tooltip title="添加随机延迟避免雪崩">
            <Text type="secondary" style={{ fontSize: 12 }}>随机抖动</Text>
          </Tooltip>
          <Switch size="small" checked={data.jitter !== false} />
        </div>

        {/* 策略提示 */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginTop: 4 }}>
          <ClockCircleOutlined style={{ color: '#eb2f96', fontSize: 12 }} />
          <Text type="secondary" style={{ fontSize: 10 }}>
            延迟: {data.initialDelay || 1}s → {Math.min((data.initialDelay || 1) * Math.pow(data.exponentialBase || 2, (data.maxRetries || 3) - 1), data.maxDelay || 60)}s
          </Text>
        </div>
      </Space>

      <Handle type="source" position={Position.Bottom} style={{ background: '#eb2f96' }} />
    </Card>
  );
};

export default memo(RetryNode);
