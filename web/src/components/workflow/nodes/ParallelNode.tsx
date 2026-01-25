import { memo, useState } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { Card, Typography, Space, Tag, InputNumber, Select } from 'antd';
import { BranchesOutlined, PlusOutlined } from '@ant-design/icons';

const { Text } = Typography;

interface ParallelNodeData {
  label: string;
  branches: Array<{
    id: string;
    name: string;
    nodes?: any[];
    workflowId?: string;
  }>;
  strategy: 'all' | 'any' | 'majority';
  timeout: number;
  failFast: boolean;
  maxConcurrent: number;
}

/**
 * 并行执行节点
 * Sprint 18: 工作流节点扩展
 */
const ParallelNode: React.FC<NodeProps<ParallelNodeData>> = ({ data, selected }) => {
  const [branches, setBranches] = useState(data.branches || []);

  return (
    <Card
      size="small"
      title={
        <Space>
          <BranchesOutlined style={{ color: '#722ed1' }} />
          <Text strong>{data.label || '并行执行'}</Text>
        </Space>
      }
      style={{
        width: 280,
        border: selected ? '2px solid #722ed1' : '1px solid #d9d9d9',
        borderRadius: 8,
      }}
      bodyStyle={{ padding: '12px' }}
    >
      <Handle type="target" position={Position.Top} style={{ background: '#722ed1' }} />

      <Space direction="vertical" style={{ width: '100%' }} size="small">
        {/* 策略选择 */}
        <div>
          <Text type="secondary" style={{ fontSize: 12 }}>执行策略</Text>
          <Select
            size="small"
            value={data.strategy || 'all'}
            style={{ width: '100%', marginTop: 4 }}
            options={[
              { label: '等待全部完成', value: 'all' },
              { label: '任意一个完成', value: 'any' },
              { label: '多数完成', value: 'majority' },
            ]}
          />
        </div>

        {/* 分支列表 */}
        <div>
          <Text type="secondary" style={{ fontSize: 12 }}>分支 ({branches.length})</Text>
          <div style={{ marginTop: 4 }}>
            {branches.map((branch, index) => (
              <Tag
                key={branch.id || index}
                color="purple"
                style={{ marginBottom: 4 }}
              >
                {branch.name || `分支 ${index + 1}`}
              </Tag>
            ))}
            <Tag
              style={{ cursor: 'pointer', borderStyle: 'dashed' }}
              onClick={() => setBranches([...branches, { id: `branch_${branches.length}`, name: `分支 ${branches.length + 1}` }])}
            >
              <PlusOutlined /> 添加分支
            </Tag>
          </div>
        </div>

        {/* 超时设置 */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Text type="secondary" style={{ fontSize: 12 }}>超时</Text>
          <InputNumber
            size="small"
            min={1}
            max={3600}
            value={data.timeout || 300}
            addonAfter="秒"
            style={{ width: 120 }}
          />
        </div>
      </Space>

      {/* 多个输出 Handle */}
      {branches.map((branch, index) => (
        <Handle
          key={branch.id || index}
          type="source"
          position={Position.Bottom}
          id={`branch-${index}`}
          style={{
            background: '#722ed1',
            left: `${20 + (60 / (branches.length + 1)) * (index + 1)}%`,
          }}
        />
      ))}
    </Card>
  );
};

export default memo(ParallelNode);
