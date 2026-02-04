import React, { memo } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { Card, Typography, Space, Select, Switch, InputNumber, Tooltip, Input } from 'antd';
import { SubnodeOutlined, LinkOutlined } from '@ant-design/icons';

const { Text } = Typography;

interface SubflowNodeData {
  label: string;
  workflowId: string;
  workflowName?: string;
  inputMapping: Record<string, string>;
  outputMapping: Record<string, string>;
  timeout: number;
  asyncMode: boolean;
  inheritContext: boolean;
}

/**
 * 子工作流节点
 * Sprint 18: 工作流节点扩展
 */
const SubflowNode: React.FC<NodeProps<SubflowNodeData>> = ({ data, selected }) => {
  return (
    <Card
      size="small"
      title={
        <Space>
          <SubnodeOutlined style={{ color: '#13c2c2' }} />
          <Text strong>{data.label || '子工作流'}</Text>
        </Space>
      }
      style={{
        width: 260,
        border: selected ? '2px solid #13c2c2' : '1px solid #d9d9d9',
        borderRadius: 8,
      }}
      styles={{ body: { padding: '12px' } }}
    >
      <Handle type="target" position={Position.Top} style={{ background: '#13c2c2' }} />

      <Space direction="vertical" style={{ width: '100%' }} size="small">
        {/* 工作流选择 */}
        <div>
          <Text type="secondary" style={{ fontSize: 12 }}>引用工作流</Text>
          <Select
            size="small"
            placeholder="选择工作流"
            value={data.workflowId}
            style={{ width: '100%', marginTop: 4 }}
            options={[
              { label: data.workflowName || '选择工作流...', value: data.workflowId || '' },
            ]}
          />
        </div>

        {/* 链接提示 */}
        {data.workflowId && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <LinkOutlined style={{ color: '#13c2c2' }} />
            <Text type="secondary" style={{ fontSize: 11 }}>
              {data.workflowName || data.workflowId}
            </Text>
          </div>
        )}

        {/* 设置 */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Tooltip title="异步执行不等待子工作流完成">
            <Text type="secondary" style={{ fontSize: 12 }}>异步执行</Text>
          </Tooltip>
          <Switch size="small" checked={data.asyncMode} />
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Text type="secondary" style={{ fontSize: 12 }}>超时</Text>
          <Space.Compact size="small">
            <InputNumber
              size="small"
              min={1}
              max={3600}
              value={data.timeout || 600}
              style={{ width: 70 }}
            />
            <Input size="small" readOnly value="秒" style={{ width: 30 }} />
          </Space.Compact>
        </div>
      </Space>

      <Handle type="source" position={Position.Bottom} style={{ background: '#13c2c2' }} />
    </Card>
  );
};

export default memo(SubflowNode);
