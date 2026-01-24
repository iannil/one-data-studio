import React, { memo, useState } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { Card, Typography, Space, Input, InputNumber, Button, Tooltip, message } from 'antd';
import { ApiOutlined, CopyOutlined, ClockCircleOutlined } from '@ant-design/icons';

const { Text } = Typography;

interface WebhookNodeData {
  label: string;
  webhookId: string;
  webhookUrl?: string;
  timeout: number;
  expectedMethod: 'GET' | 'POST' | 'PUT';
  secretKey: string;
  outputMapping: Record<string, string>;
}

/**
 * Webhook 节点
 * Sprint 18: 工作流节点扩展
 */
const WebhookNode: React.FC<NodeProps<WebhookNodeData>> = ({ data, selected }) => {
  const [copied, setCopied] = useState(false);

  const webhookUrl = data.webhookUrl || `/api/v1/webhooks/${data.webhookId || 'pending'}`;

  const handleCopyUrl = () => {
    navigator.clipboard.writeText(webhookUrl);
    message.success('Webhook URL 已复制');
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const timeoutLabel = data.timeout >= 3600
    ? `${Math.floor(data.timeout / 3600)}小时`
    : data.timeout >= 60
    ? `${Math.floor(data.timeout / 60)}分钟`
    : `${data.timeout}秒`;

  return (
    <Card
      size="small"
      title={
        <Space>
          <ApiOutlined style={{ color: '#52c41a' }} />
          <Text strong>{data.label || 'Webhook'}</Text>
        </Space>
      }
      style={{
        width: 280,
        border: selected ? '2px solid #52c41a' : '1px solid #d9d9d9',
        borderRadius: 8,
      }}
      bodyStyle={{ padding: '12px' }}
    >
      <Handle type="target" position={Position.Top} style={{ background: '#52c41a' }} />

      <Space direction="vertical" style={{ width: '100%' }} size="small">
        {/* Webhook URL */}
        <div>
          <Text type="secondary" style={{ fontSize: 12 }}>Webhook URL</Text>
          <Input.Group compact style={{ display: 'flex', marginTop: 4 }}>
            <Input
              size="small"
              value={webhookUrl}
              readOnly
              style={{ flex: 1 }}
            />
            <Tooltip title={copied ? '已复制' : '复制 URL'}>
              <Button
                size="small"
                icon={<CopyOutlined />}
                onClick={handleCopyUrl}
              />
            </Tooltip>
          </Input.Group>
        </div>

        {/* 超时设置 */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Text type="secondary" style={{ fontSize: 12 }}>等待超时</Text>
          <InputNumber
            size="small"
            min={60}
            max={86400}
            value={data.timeout || 3600}
            style={{ width: 100 }}
          />
        </div>

        {/* HTTP 方法 */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Text type="secondary" style={{ fontSize: 12 }}>预期方法</Text>
          <Text code>{data.expectedMethod || 'POST'}</Text>
        </div>

        {/* 状态提示 */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 4,
            padding: '4px 8px',
            background: '#f6ffed',
            borderRadius: 4,
          }}
        >
          <ClockCircleOutlined style={{ color: '#52c41a', fontSize: 12 }} />
          <Text style={{ fontSize: 11, color: '#52c41a' }}>
            等待外部回调 (超时: {timeoutLabel})
          </Text>
        </div>
      </Space>

      <Handle type="source" position={Position.Bottom} style={{ background: '#52c41a' }} />
    </Card>
  );
};

export default memo(WebhookNode);
