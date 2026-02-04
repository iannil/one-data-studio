import { useState, useRef, useEffect } from 'react';
import { Card, Input, Button, Space, Avatar, Tag, Spin, message } from 'antd';
import {
  SendOutlined,
  UserOutlined,
  RobotOutlined,
  ClearOutlined,
  BarChartOutlined,
} from '@ant-design/icons';
import { useMutation } from '@tanstack/react-query';
import { text2Sql } from '@/services/agent-service';
import { logError } from '@/services/logger';
import type { Text2SqlResponse } from '@/services/agent-service';

const { TextArea } = Input;

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: number;
  sql?: string;
  chartRecommendation?: {
    chartType: string;
    chartName: string;
    confidence: number;
    reason: string;
  };
}

interface AIChatPanelProps {
  database?: string;
  tables?: string[];
  onQueryGenerated?: (sql: string, chartConfig?: { type: string; x: string; y: string } | null) => void;
  height?: number | string;
}

export function AIChatPanel({
  database,
  tables,
  onQueryGenerated,
  height = 600,
}: AIChatPanelProps) {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome',
      role: 'assistant',
      content: '您好！我是您的智能数据分析师。您可以：\n\n• 描述您想分析的数据，例如"显示最近30天的销售趋势"\n• 请求生成图表，例如"用柱状图展示各部门的费用"\n• 进行数据筛选，例如"查找金额大于10000的订单"',
      timestamp: Date.now(),
    },
  ]);
  const [inputValue, setInputValue] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const queryMutation = useMutation({
    mutationFn: text2Sql,
    onSuccess: (response) => {
      const data = response.data;
      if (!data) {
        message.error('生成失败，请重试');
        return;
      }

      // 添加助手消息
      const assistantMsg: Message = {
        id: Date.now().toString(),
        role: 'assistant',
        content: _generateResponseContent(data),
        timestamp: Date.now(),
        sql: data.sql,
      };

      setMessages((prev) => [...prev, assistantMsg]);

      // 回调通知父组件
      if (onQueryGenerated && data.sql) {
        onQueryGenerated(data.sql, data.chartRecommendation as { type: string; x: string; y: string } | undefined);
      }
    },
    onError: (error) => {
      logError('AI Chat error', 'AIChatPanel', error);
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now().toString(),
          role: 'assistant',
          content: '抱歉，生成查询时出错。请检查您的描述或稍后重试。',
          timestamp: Date.now(),
        },
      ]);
    },
    onSettled: () => {
      setIsGenerating(false);
    },
  });

  const _generateResponseContent = (data: Text2SqlResponse) => {
    let content = '';

    if (data.interpretation) {
      content += `**理解**：${data.interpretation}\n\n`;
    }

    if (data.sql) {
      content += `**生成的SQL**：\n\`\`\`sql\n${data.sql}\n\`\`\`\n\n`;
    }

    if (data.chartRecommendation) {
      const rec = data.chartRecommendation;
      content += `**推荐图表**：${rec.chartName}\n`;
      content += `- 置信度：${(rec.confidence * 100).toFixed(0)}%\n`;
      if (rec.reason) {
        content += `- 理由：${rec.reason}\n`;
      }
    }

    if (data.suggestions && data.suggestions.length > 0) {
      content += `\n**后续建议**：\n`;
      data.suggestions.forEach((s: string, i: number) => {
        content += `${i + 1}. ${s}\n`;
      });
    }

    return content || '已为您生成查询，您可以执行查看结果。';
  };

  const handleSend = () => {
    const trimmed = inputValue.trim();
    if (!trimmed || isGenerating) return;

    // 添加用户消息
    const userMsg: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: trimmed,
      timestamp: Date.now(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setInputValue('');
    setIsGenerating(true);

    // 调用AI生成
    queryMutation.mutate({
      natural_language: trimmed,
      database,
      selected_tables: tables,
      include_chartRecommendation: true,
    } as any);
  };

  const handleClear = () => {
    setMessages([
      {
        id: 'welcome',
        role: 'assistant',
        content: '对话已清空。您可以开始新的数据分析会话。',
        timestamp: Date.now(),
      },
    ]);
  };

  const handleSuggestionClick = (suggestion: string) => {
    setInputValue(suggestion);
  };

  // 快捷建议
  const suggestions = [
    '显示最近30天的销售趋势',
    '按地区统计订单数量',
    '找出销售额前10的产品',
    '分析各季度的收入变化',
  ];

  // 自动滚动到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const renderMessage = (msg: Message) => {
    const isUser = msg.role === 'user';

    return (
      <div
        key={msg.id}
        style={{
          display: 'flex',
          justifyContent: isUser ? 'flex-end' : 'flex-start',
          marginBottom: 16,
        }}
      >
        <div
          style={{
            display: 'flex',
            maxWidth: '75%',
            flexDirection: isUser ? 'row-reverse' : 'row',
            alignItems: 'flex-start',
            gap: 8,
          }}
        >
          <Avatar
            icon={isUser ? <UserOutlined /> : <RobotOutlined />}
            style={{ backgroundColor: isUser ? '#1677ff' : '#52c41a' }}
          />
          <div
            style={{
              backgroundColor: isUser ? '#1677ff' : '#f5f5f5',
              color: isUser ? '#fff' : '#000',
              padding: '12px 16px',
              borderRadius: isUser ? '8px 8px 0 8px' : '8px 8px 8px 0',
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
            }}
          >
            {msg.content}
            {msg.chartRecommendation && (
              <Tag
                icon={<BarChartOutlined />}
                color="blue"
                style={{ marginTop: 8, display: 'inline-flex', alignItems: 'center' }}
              >
                {msg.chartRecommendation.chartName} ({(msg.chartRecommendation.confidence * 100).toFixed(0)}%)
              </Tag>
            )}
          </div>
        </div>
      </div>
    );
  };

  return (
    <Card
      title={
        <Space>
          <RobotOutlined />
          智能数据分析助手
        </Space>
      }
      extra={
        <Button
          type="text"
          icon={<ClearOutlined />}
          onClick={handleClear}
          size="small"
        >
          清空
        </Button>
      }
      style={{ height }}
      styles={{ body: { display: 'flex', flexDirection: 'column', height: 'calc(100% - 60px)' } }}
    >
      {/* 消息区域 */}
      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '16px 0',
          minHeight: 300,
        }}
      >
        {messages.map(renderMessage)}
        {isGenerating && (
          <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
            <Avatar
              icon={<RobotOutlined />}
              style={{ backgroundColor: '#52c41a' }}
            />
            <div
              style={{
                backgroundColor: '#f5f5f5',
                padding: '12px 16px',
                borderRadius: '8px 8px 0 8px',
              }}
            >
              <Spin size="small" /> 正在思考...
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* 建议快捷操作 */}
      {messages.length <= 2 && (
        <div style={{ marginBottom: 12 }}>
          <div style={{ fontSize: 12, color: '#999', marginBottom: 8 }}>
            尝试以下查询：
          </div>
          <Space wrap size="small">
            {suggestions.map((s) => (
              <Tag
                key={s}
                style={{ cursor: 'pointer' }}
                onClick={() => handleSuggestionClick(s)}
              >
                {s}
              </Tag>
            ))}
          </Space>
        </div>
      )}

      {/* 输入区域 */}
      <div style={{ borderTop: '1px solid #f0f0f0', paddingTop: 12 }}>
        <Space.Compact style={{ width: '100%' }}>
          <TextArea
            rows={2}
            placeholder="描述您想分析的数据... (Shift+Enter 换行)"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onPressEnter={(e) => {
              if (!e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
            disabled={isGenerating}
          />
          <Button
            type="primary"
            icon={<SendOutlined />}
            onClick={handleSend}
            loading={isGenerating}
            style={{ height: 'auto', alignSelf: 'stretch' }}
          >
            发送
          </Button>
        </Space.Compact>
      </div>
    </Card>
  );
}

export default AIChatPanel;
