import { useState, useEffect } from 'react';
import { Modal, Spin, Empty, Tag, Typography } from 'antd';
import { FileTextOutlined } from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import dayjs from 'dayjs';
import agentService, { type ExecutionLog } from '@/services/agent-service';

const { Text } = Typography;

interface ExecutionLogsModalProps {
  executionId: string | null;
  open: boolean;
  onClose: () => void;
}

// 日志级别配置
const logLevelConfig = {
  info: { color: 'blue', text: 'INFO' },
  warning: { color: 'orange', text: 'WARN' },
  error: { color: 'red', text: 'ERROR' },
};

function ExecutionLogsModal({ executionId, open, onClose }: ExecutionLogsModalProps) {
  const [autoScroll] = useState(true);

  const { data: logsData, isLoading } = useQuery({
    queryKey: ['execution-logs', executionId],
    queryFn: () => agentService.getExecutionLogs(executionId!),
    enabled: open && !!executionId,
    refetchInterval: (query) => {
      // 如果执行仍在运行，每3秒刷新一次
      const queryData = query.state.data as any;
      const hasRunningLogs = queryData?.data?.logs?.some((log: ExecutionLog) =>
        log.message.includes('running') || log.message.includes('processing')
      );
      return hasRunningLogs ? 3000 : false;
    },
  });

  const logs = logsData?.data?.logs || [];

  // 自动滚动到底部
  useEffect(() => {
    if (autoScroll && logs.length > 0) {
      const timer = setTimeout(() => {
        const logContainer = document.getElementById('log-container');
        if (logContainer) {
          logContainer.scrollTop = logContainer.scrollHeight;
        }
      }, 100);
      return () => clearTimeout(timer);
    }
  }, [logs, autoScroll]);

  return (
    <Modal
      title={
        <span>
          <FileTextOutlined style={{ marginRight: 8 }} />
          执行日志 {executionId && <Text type="secondary">({executionId.slice(0, 8)}...)</Text>}
        </span>
      }
      open={open}
      onCancel={onClose}
      width={800}
      footer={null}
    >
      <Spin spinning={isLoading}>
        {logs.length === 0 ? (
          <Empty description="暂无日志" />
        ) : (
          <div
            id="log-container"
            style={{
              height: '400px',
              overflowY: 'auto',
              background: '#1e1e1e',
              borderRadius: '6px',
              padding: '12px',
              fontFamily: 'Monaco, Consolas, monospace',
              fontSize: '12px',
            }}
          >
            {logs.map((log: ExecutionLog, index: number) => (
              <div
                key={log.id || index}
                style={{
                  marginBottom: '4px',
                  display: 'flex',
                  gap: '8px',
                  lineHeight: '1.5',
                }}
              >
                <span style={{ color: '#858585', minWidth: '140px', flexShrink: 0 }}>
                  {dayjs(log.timestamp).format('HH:mm:ss.SSS')}
                </span>
                <Tag
                  color={logLevelConfig[log.level]?.color || 'default'}
                  style={{ margin: 0, minWidth: '60px', textAlign: 'center', flexShrink: 0 }}
                >
                  {logLevelConfig[log.level]?.text || log.level.toUpperCase()}
                </Tag>
                {log.node_id && (
                  <span style={{ color: '#569cd6', minWidth: '80px', flexShrink: 0 }}>
                    [{log.node_id}]
                  </span>
                )}
                <span style={{
                  color: log.level === 'error' ? '#f48771' : log.level === 'warning' ? '#dcdcaa' : '#d4d4d4',
                  wordBreak: 'break-all',
                }}>
                  {log.message}
                </span>
              </div>
            ))}
          </div>
        )}
      </Spin>
    </Modal>
  );
}

export default ExecutionLogsModal;
