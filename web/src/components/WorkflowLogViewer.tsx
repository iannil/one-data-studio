import { useState } from 'react';
import { Card, Select, Space, Tag, Empty } from 'antd';
import type { ExecutionLog } from '@/services/bisheng';

const { Option } = Select;

interface WorkflowLogViewerProps {
  logs: ExecutionLog[];
  height?: number | string;
}

function WorkflowLogViewer({ logs, height = 400 }: WorkflowLogViewerProps) {
  const [levelFilter, setLevelFilter] = useState<string>('all');

  const filteredLogs = logs.filter((log) => {
    if (levelFilter === 'all') return true;
    return log.level === levelFilter;
  });

  const getLevelTag = (level: ExecutionLog['level']) => {
    const config = {
      info: { color: 'blue', text: 'INFO' },
      warning: { color: 'orange', text: 'WARN' },
      error: { color: 'red', text: 'ERROR' },
    };
    const c = config[level] || config.info;
    return <Tag color={c.color}>{c.text}</Tag>;
  };

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('zh-CN', { hour12: false }) + '.' +
           String(date.getMilliseconds()).padStart(3, '0');
  };

  return (
    <Card
      size="small"
      title={
        <Space>
          <span>日志</span>
          <Select
            size="small"
            value={levelFilter}
            onChange={setLevelFilter}
            style={{ width: 120 }}
          >
            <Option value="all">全部</Option>
            <Option value="info">信息</Option>
            <Option value="warning">警告</Option>
            <Option value="error">错误</Option>
          </Select>
          <span style={{ fontSize: 12, color: '#999' }}>
            共 {filteredLogs.length} 条
          </span>
        </Space>
      }
    >
      <div
        style={{
          height: typeof height === 'number' ? `${height}px` : height,
          overflow: 'auto',
          backgroundColor: '#1e1e1e',
          borderRadius: 4,
          padding: 12,
          fontFamily: 'Monaco, Consolas, monospace',
          fontSize: 12,
        }}
      >
        {filteredLogs.length === 0 ? (
          <Empty
            description="暂无日志"
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            style={{ color: '#999' }}
          />
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            {filteredLogs.map((log) => (
              <div
                key={log.id}
                style={{
                  display: 'flex',
                  gap: 8,
                  color: log.level === 'error' ? '#ff6b6b' :
                         log.level === 'warning' ? '#ffa940' : '#d4d4d4',
                }}
              >
                <span style={{ color: '#858585', minWidth: 100 }}>
                  {formatTime(log.timestamp)}
                </span>
                {getLevelTag(log.level)}
                {log.node_id && (
                  <span style={{ color: '#4ec9b0' }}>[{log.node_id}]</span>
                )}
                <span style={{ flex: 1, wordBreak: 'break-all' }}>
                  {log.message}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </Card>
  );
}

export default WorkflowLogViewer;
