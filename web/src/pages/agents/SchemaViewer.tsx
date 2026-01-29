import { Modal, Typography, Button, message } from 'antd';
import { CopyOutlined } from '@ant-design/icons';
import type { ToolSchema } from '@/services/agent-service';

const { Paragraph, Text } = Typography;

interface SchemaViewerProps {
  schemas: ToolSchema[];
  open: boolean;
  onClose: () => void;
}

function SchemaViewer({ schemas, open, onClose }: SchemaViewerProps) {
  const handleCopy = () => {
    const json = JSON.stringify(schemas, null, 2);
    navigator.clipboard.writeText(json).then(() => {
      message.success('已复制到剪贴板');
    });
  };

  return (
    <Modal
      title="Function Calling Schema"
      open={open}
      onCancel={onClose}
      footer={[
        <Button key="close" onClick={onClose}>
          关闭
        </Button>,
        <Button key="copy" icon={<CopyOutlined />} onClick={handleCopy}>
          复制
        </Button>,
      ]}
      width={700}
    >
      <div
        style={{
          background: '#1e1e1e',
          padding: '16px',
          borderRadius: '6px',
          maxHeight: '500px',
          overflow: 'auto',
        }}
      >
        {schemas.map((schema, index) => (
          <div key={index} style={{ marginBottom: index < schemas.length - 1 ? '16px' : 0 }}>
            <Text style={{ color: '#4ec9b0', fontSize: '14px' }}>
              {schema.function.name}
            </Text>
            <Paragraph
              style={{
                color: '#9cdcfe',
                fontSize: '13px',
                margin: '4px 0 8px 0',
                fontStyle: 'italic',
              }}
            >
              {schema.function.description}
            </Paragraph>
            <pre
              style={{
                margin: 0,
                color: '#d4d4d4',
                fontSize: '12px',
                fontFamily: 'Consolas, Monaco, monospace',
              }}
            >
              {JSON.stringify(schema, null, 2)}
            </pre>
          </div>
        ))}
      </div>
    </Modal>
  );
}

export default SchemaViewer;
