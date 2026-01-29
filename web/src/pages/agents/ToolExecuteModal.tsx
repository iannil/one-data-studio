import { useState } from 'react';
import { Modal, Form, Input, Button, message, Spin, Alert } from 'antd';
import { PlayCircleOutlined } from '@ant-design/icons';
import type { Tool } from '@/services/agent-service';
import agentService from '@/services/agent-service';

const { TextArea } = Input;

interface ToolExecuteModalProps {
  tool: Tool | null;
  open: boolean;
  onClose: () => void;
}

// 工具执行结果类型
interface ToolExecuteResult {
  output?: unknown;
  error?: string;
  [key: string]: unknown;
}

function ToolExecuteModal({ tool, open, onClose }: ToolExecuteModalProps) {
  const [form] = Form.useForm();
  const [result, setResult] = useState<ToolExecuteResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [hasExecuted, setHasExecuted] = useState(false);

  const handleExecute = async () => {
    if (!tool) return;

    try {
      await form.validateFields();
    } catch {
      return;
    }

    const values = form.getFieldsValue();
    setLoading(true);
    setResult(null);

    try {
      const response = await agentService.executeTool(tool.name, values);
      setResult(response.data as ToolExecuteResult);
      setHasExecuted(true);
      message.success('工具执行成功');
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : '未知错误';
      message.error(`工具执行失败: ${errorMessage}`);
      setResult({ error: errorMessage });
      setHasExecuted(true);
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    form.resetFields();
    setResult(null);
    setHasExecuted(false);
    onClose();
  };

  return (
    <Modal
      title={`测试工具: ${tool?.name || ''}`}
      open={open}
      onCancel={handleClose}
      footer={[
        <Button key="close" onClick={handleClose}>
          关闭
        </Button>,
        <Button
          key="execute"
          type="primary"
          icon={<PlayCircleOutlined />}
          loading={loading}
          onClick={handleExecute}
        >
          执行
        </Button>,
      ]}
      width={600}
    >
      {tool && (
        <div>
          <Alert
            message={tool.description}
            type="info"
            style={{ marginBottom: '16px' }}
          />

          <Form form={form} layout="vertical">
            {tool.parameters.map((param) => (
              <Form.Item
                key={param.name}
                label={
                  <span>
                    {param.name}
                    <span style={{ color: '#999', marginLeft: '8px', fontSize: '12px' }}>
                      ({param.type})
                    </span>
                  </span>
                }
                name={param.name}
                initialValue={param.default}
                rules={[{ required: param.required, message: `请输入 ${param.name}` }]}
                tooltip={param.description}
              >
                {param.type === 'string' && param.name.toLowerCase().includes('content') ? (
                  <TextArea
                    rows={4}
                    placeholder={param.description || `请输入 ${param.name}`}
                  />
                ) : (
                  <Input
                    placeholder={param.description || `请输入 ${param.name}`}
                    type={param.type === 'number' ? 'number' : 'text'}
                  />
                )}
              </Form.Item>
            ))}
          </Form>

          {hasExecuted && (
            <div style={{ marginTop: '16px' }}>
              <strong>执行结果:</strong>
              <div
                style={{
                  marginTop: '8px',
                  padding: '12px',
                  background: result?.error ? '#fff2f0' : '#f6ffed',
                  borderRadius: '6px',
                  border: `1px solid ${result?.error ? '#ffccc7' : '#b7eb8f'}`,
                }}
              >
                {loading ? (
                  <Spin />
                ) : (
                  <pre
                    style={{
                      margin: 0,
                      whiteSpace: 'pre-wrap',
                      wordBreak: 'break-word',
                      maxHeight: '300px',
                      overflow: 'auto',
                      fontSize: '13px',
                    }}
                  >
                    {typeof result === 'string'
                      ? result
                      : JSON.stringify(result, null, 2)}
                  </pre>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </Modal>
  );
}

export default ToolExecuteModal;
