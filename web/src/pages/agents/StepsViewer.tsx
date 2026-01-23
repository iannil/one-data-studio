import { Timeline } from 'antd';
import { ClockCircleOutlined, ToolOutlined, EyeOutlined, CheckCircleOutlined } from '@ant-design/icons';
import type { AgentStep } from '@/services/bisheng';

interface StepsViewerProps {
  steps: AgentStep[];
  loading?: boolean;
}

const stepConfig = {
  thought: {
    icon: <ClockCircleOutlined />,
    color: '#1677ff',
    label: '思考',
  },
  action: {
    icon: <ToolOutlined />,
    color: '#fa8c16',
    label: '行动',
  },
  observation: {
    icon: <EyeOutlined />,
    color: '#52c41a',
    label: '观察',
  },
  final: {
    icon: <CheckCircleOutlined />,
    color: '#722ed1',
    label: '最终',
  },
};

function StepsViewer({ steps, loading }: StepsViewerProps) {
  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '40px 0', color: '#999' }}>
        Agent 运行中...
      </div>
    );
  }

  if (steps.length === 0) {
    return (
      <div style={{ textAlign: 'center', padding: '40px 0', color: '#999' }}>
        暂无执行步骤
      </div>
    );
  }

  return (
    <Timeline
      items={steps.map((step, index) => {
        const config = stepConfig[step.type];
        return {
          dot: config.icon,
          color: config.color,
          children: (
            <div key={index} style={{ marginBottom: '12px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                <strong style={{ color: config.color }}>{config.label}</strong>
                <span style={{ fontSize: '12px', color: '#999' }}>
                  {new Date(step.timestamp).toLocaleTimeString('zh-CN')}
                </span>
              </div>
              <div
                style={{
                  padding: '8px 12px',
                  background: step.type === 'final' ? '#f9f0ff' : '#f5f5f5',
                  borderRadius: '6px',
                  fontSize: '14px',
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word',
                }}
              >
                {step.content}
              </div>
              {step.tool_output && (
                <div
                  style={{
                    marginTop: '8px',
                    padding: '8px 12px',
                    background: '#e6f7ff',
                    borderRadius: '6px',
                    fontSize: '13px',
                  }}
                >
                  <strong>工具输出:</strong>
                  <pre
                    style={{
                      margin: '4px 0 0 0',
                      whiteSpace: 'pre-wrap',
                      wordBreak: 'break-word',
                      maxHeight: '200px',
                      overflow: 'auto',
                    }}
                  >
                    {typeof step.tool_output === 'string'
                      ? step.tool_output
                      : JSON.stringify(step.tool_output, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          ),
        };
      })}
    />
  );
}

export default StepsViewer;
