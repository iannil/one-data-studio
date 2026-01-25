import { useState, useEffect } from 'react';
import DOMPurify from 'dompurify';
import {
  Card,
  Select,
  Input,
  Button,
  Space,
  message,
  Typography,
  Tag,
  Divider,
  Row,
  Col,
  Statistic,
  Empty,
  Spin,
  Checkbox,
} from 'antd';
import {
  SendOutlined,
  CopyOutlined,
  ClearOutlined,
  ThunderboltOutlined,
  TableOutlined,
  ClockCircleOutlined,
  StarFilled,
  StarOutlined,
  DeleteOutlined,
  PlayCircleOutlined,
  DatabaseOutlined,
  SearchOutlined,
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import alldata from '@/services/alldata';
import { text2Sql } from '@/services/bisheng';
import type { Text2SqlResponse } from '@/services/bisheng';
import { logError } from '@/services/logger';

const { TextArea } = Input;
const { Title, Text } = Typography;
const { Option } = Select;

interface QueryHistory {
  id: string;
  naturalLanguage: string;
  sql: string;
  confidence: number;
  tablesUsed: string[];
  database?: string;
  timestamp: number;
  starred?: boolean;
}

// 示例查询提示
const EXAMPLE_QUERIES = [
  '查询销售额前10的产品',
  '统计每个订单状态的数量',
  '查找最近一周注册的用户',
  '获取库存量不足100的商品',
  '分析每月的订单总金额',
];

function Text2SQLPage() {
  // 输入状态
  const [selectedDatabase, setSelectedDatabase] = useState<string>('');
  const [selectedTables, setSelectedTables] = useState<string[]>([]);
  const [tableSearchText, setTableSearchText] = useState('');
  const [naturalLanguage, setNaturalLanguage] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [isExecuting, setIsExecuting] = useState(false);

  // 结果状态
  const [sqlResult, setSqlResult] = useState<Text2SqlResponse | null>(null);
  const [executeResult, setExecuteResult] = useState<{
    rows: Record<string, unknown>[];
    columns: string[];
    row_count: number;
    execution_time_ms: number;
  } | null>(null);

  // 历史记录
  const [queryHistory, setQueryHistory] = useState<QueryHistory[]>(() => {
    const saved = localStorage.getItem('text2sql_history');
    return saved ? JSON.parse(saved) : [];
  });

  // 获取数据库列表
  const { data: databasesData } = useQuery({
    queryKey: ['databases'],
    queryFn: alldata.getDatabases,
  });

  const databases = databasesData?.data?.databases || [];

  // 获取选中数据库的表列表
  const { data: tablesData, isLoading: tablesLoading } = useQuery({
    queryKey: ['tables', selectedDatabase],
    queryFn: () => alldata.getTables(selectedDatabase),
    enabled: !!selectedDatabase,
  });

  const tables = tablesData?.data?.tables || [];

  // 过滤后的表列表
  const filteredTables = tables.filter((table) =>
    table.name.toLowerCase().includes(tableSearchText.toLowerCase()) ||
    (table.description && table.description.toLowerCase().includes(tableSearchText.toLowerCase()))
  );

  // 当数据库改变时，清空已选择的表
  useEffect(() => {
    setSelectedTables([]);
    setTableSearchText('');
  }, [selectedDatabase]);

  // 保存历史记录到 localStorage
  const saveHistory = (history: QueryHistory[]) => {
    localStorage.setItem('text2sql_history', JSON.stringify(history.slice(0, 50))); // 最多保存50条
  };

  // 生成 SQL
  const handleGenerateSQL = async (query?: string) => {
    const inputQuery = query || naturalLanguage;
    if (!inputQuery.trim()) {
      message.warning('请输入自然语言查询');
      return;
    }

    setIsGenerating(true);
    setExecuteResult(null);

    try {
      const response = await text2Sql({
        natural_language: inputQuery,
        database: selectedDatabase || undefined,
        selected_tables: selectedTables.length > 0 ? selectedTables : undefined,
      });

      if (response.data) {
        setSqlResult(response.data);

        // 添加到历史记录
        const newHistory: QueryHistory = {
          id: Date.now().toString(),
          naturalLanguage: inputQuery,
          sql: response.data.sql,
          confidence: response.data.confidence,
          tablesUsed: response.data.tables_used || [],
          database: selectedDatabase,
          timestamp: Date.now(),
        };
        const updatedHistory = [newHistory, ...queryHistory];
        setQueryHistory(updatedHistory);
        saveHistory(updatedHistory);

        message.success('SQL 生成成功');
      }
    } catch (error) {
      message.error('生成 SQL 失败，请重试');
      logError('Text2SQL error', 'Text2SQLPage', error);
    } finally {
      setIsGenerating(false);
    }
  };

  // 执行 SQL
  const handleExecuteSQL = async () => {
    if (!sqlResult?.sql || !selectedDatabase) {
      message.warning('请先生成 SQL 并选择数据库');
      return;
    }

    setIsExecuting(true);
    try {
      const response = await alldata.executeQuery({
        database: selectedDatabase,
        sql: sqlResult.sql,
      });

      if (response.data) {
        setExecuteResult({
          rows: response.data.rows || [],
          columns: response.data.columns || [],
          row_count: response.data.row_count || 0,
          execution_time_ms: response.data.execution_time_ms || 0,
        });
        message.success(`查询成功，返回 ${response.data.row_count} 条记录`);
      }
    } catch (error) {
      message.error('执行 SQL 失败，请检查 SQL 语法');
      logError('Execute SQL error', 'Text2SQLPage', error);
    } finally {
      setIsExecuting(false);
    }
  };

  // 复制 SQL
  const handleCopySQL = () => {
    if (sqlResult?.sql) {
      navigator.clipboard.writeText(sqlResult.sql);
      message.success('SQL 已复制到剪贴板');
    }
  };

  // 清空输入
  const handleClear = () => {
    setNaturalLanguage('');
    setSqlResult(null);
    setExecuteResult(null);
  };

  // 从历史记录加载
  const loadFromHistory = (item: QueryHistory) => {
    setNaturalLanguage(item.naturalLanguage);
    setSqlResult({
      sql: item.sql,
      confidence: item.confidence,
      tables_used: item.tablesUsed,
    });
    if (item.database) {
      setSelectedDatabase(item.database);
    }
    if (item.tablesUsed && item.tablesUsed.length > 0) {
      setSelectedTables(item.tablesUsed);
    }
    setExecuteResult(null);
  };

  // 删除历史记录
  const deleteHistory = (id: string) => {
    const updated = queryHistory.filter((item) => item.id !== id);
    setQueryHistory(updated);
    saveHistory(updated);
    message.success('已删除');
  };

  // 切换收藏状态
  const toggleStar = (id: string) => {
    const updated = queryHistory.map((item) =>
      item.id === id ? { ...item, starred: !item.starred } : item
    );
    setQueryHistory(updated);
    saveHistory(updated);
  };

  // 获取置信度颜色
  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'success';
    if (confidence >= 0.6) return 'warning';
    return 'error';
  };

  // 格式化时间
  const formatTimestamp = (timestamp: number) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (minutes < 1) return '刚刚';
    if (minutes < 60) return `${minutes}分钟前`;
    if (hours < 24) return `${hours}小时前`;
    if (days < 7) return `${days}天前`;
    return date.toLocaleDateString();
  };

  // SQL 语法高亮（简单实现）
  // SECURITY: Input is escaped before highlighting, and DOMPurify sanitizes the output
  const highlightSQL = (sql: string) => {
    // First, escape HTML entities to prevent XSS from the SQL content itself
    const escapeHtml = (text: string) => {
      const div = document.createElement('div');
      div.textContent = text;
      return div.innerHTML;
    };

    let highlighted = escapeHtml(sql);

    const keywords = [
      'SELECT', 'FROM', 'WHERE', 'JOIN', 'LEFT', 'RIGHT', 'INNER', 'OUTER',
      'ON', 'AND', 'OR', 'NOT', 'IN', 'LIKE', 'BETWEEN', 'ORDER BY', 'GROUP BY',
      'HAVING', 'LIMIT', 'OFFSET', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP',
      'ALTER', 'TABLE', 'INDEX', 'AS', 'DESC', 'ASC', 'DISTINCT', 'COUNT', 'SUM',
      'AVG', 'MAX', 'MIN', 'CASE', 'WHEN', 'THEN', 'ELSE', 'END', 'UNION', 'ALL'
    ];

    keywords.forEach((keyword) => {
      const regex = new RegExp(`\\b${keyword}\\b`, 'gi');
      highlighted = highlighted.replace(regex, `<span style="color: #1677ff; font-weight: bold;">${keyword}</span>`);
    });

    // 高亮字符串（already escaped, so safe)
    highlighted = highlighted.replace(/'([^']*)'/g, `<span style="color: #52c41a;">'$1'</span>`);

    // 高亮数字
    highlighted = highlighted.replace(/\b(\d+)\b/g, `<span style="color: #fa8c16;">$1</span>`);

    return highlighted;
  };

  // DOMPurify configuration for SQL display - allow only safe styling
  const sanitizeConfig = {
    ALLOWED_TAGS: ['span'],
    ALLOWED_ATTR: ['style'],
  };

  // Safe render helper for highlighted SQL
  const renderHighlightedSQL = (sql: string) => {
    return DOMPurify.sanitize(highlightSQL(sql), sanitizeConfig);
  };

  return (
    <div style={{ padding: '24px' }}>
      <Row gutter={24}>
        {/* 左侧：查询输入区 */}
        <Col span={14}>
          <Card title="自然语言查询" extra={<Text type="secondary">AI 辅助生成 SQL</Text>}>
            <Space direction="vertical" style={{ width: '100%' }} size="large">
              {/* 数据库选择 */}
              <div>
                <Text strong style={{ marginBottom: 8, display: 'block' }}>
                  选择数据库
                </Text>
                <Select
                  placeholder="请选择数据库（可选）"
                  style={{ width: '100%' }}
                  value={selectedDatabase || undefined}
                  onChange={setSelectedDatabase}
                  allowClear
                >
                  {databases.map((db) => (
                    <Option key={db.name} value={db.name}>
                      <DatabaseOutlined style={{ marginRight: 8 }} />
                      {db.name}
                      {db.description && (
                        <Text type="secondary" style={{ marginLeft: 8 }}>
                          - {db.description}
                        </Text>
                      )}
                    </Option>
                  ))}
                </Select>
              </div>

              {/* 表选择区域 - 新增 */}
              {selectedDatabase && (
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                    <Text strong>选择涉及的表（可选）</Text>
                    <Space size="small">
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        已选 {selectedTables.length} / {tables.length} 张表
                      </Text>
                      {selectedTables.length > 0 && (
                        <Button size="small" type="link" onClick={() => setSelectedTables([])}>
                          清空
                        </Button>
                      )}
                    </Space>
                  </div>

                  {/* 搜索框 */}
                  <Input
                    placeholder="搜索表名..."
                    prefix={<SearchOutlined />}
                    value={tableSearchText}
                    onChange={(e) => setTableSearchText(e.target.value)}
                    style={{ marginBottom: 8 }}
                    allowClear
                  />

                  {/* 表选择器 */}
                  <div
                    style={{
                      maxHeight: 200,
                      overflowY: 'auto',
                      border: '1px solid #d9d9d9',
                      borderRadius: 6,
                      padding: 8,
                    }}
                  >
                    {tablesLoading ? (
                      <div style={{ textAlign: 'center', padding: 16 }}>
                        <Spin size="small" />
                      </div>
                    ) : filteredTables.length === 0 ? (
                      <Empty description={tableSearchText ? '未找到匹配的表' : '该数据库暂无表'} image={Empty.PRESENTED_IMAGE_SIMPLE} />
                    ) : (
                      <Space direction="vertical" style={{ width: '100%' }} size="small">
                        {filteredTables.map((table) => (
                          <Checkbox
                            key={table.name}
                            checked={selectedTables.includes(table.name)}
                            onChange={(e) => {
                              if (e.target.checked) {
                                setSelectedTables([...selectedTables, table.name]);
                              } else {
                                setSelectedTables(selectedTables.filter((t) => t !== table.name));
                              }
                            }}
                          >
                            <Space size={4}>
                              <Text strong>{table.name}</Text>
                              {table.description && (
                                <Text type="secondary" style={{ fontSize: 12 }}>
                                  - {table.description}
                                </Text>
                              )}
                              {table.row_count !== undefined && (
                                <Tag color="default" style={{ fontSize: 11, margin: 0 }}>
                                  {table.row_count.toLocaleString()} 行
                                </Tag>
                              )}
                            </Space>
                          </Checkbox>
                        ))}
                      </Space>
                    )}
                  </div>
                  <Text type="secondary" style={{ fontSize: 12, marginTop: 4, display: 'block' }}>
                    留空则自动使用所有表生成 SQL
                  </Text>
                </div>
              )}

              {/* 示例查询 */}
              <div>
                <Text strong style={{ marginBottom: 8, display: 'block' }}>
                  示例查询
                </Text>
                <Space wrap>
                  {EXAMPLE_QUERIES.map((example, index) => (
                    <Tag
                      key={index}
                      style={{ cursor: 'pointer', padding: '4px 12px' }}
                      onClick={() => setNaturalLanguage(example)}
                    >
                      {example}
                    </Tag>
                  ))}
                </Space>
              </div>

              {/* 自然语言输入 */}
              <div>
                <Text strong style={{ marginBottom: 8, display: 'block' }}>
                  请输入您的查询需求
                </Text>
                <TextArea
                  rows={5}
                  placeholder="例如：查询销售额前10的产品及其销售额"
                  value={naturalLanguage}
                  onChange={(e) => setNaturalLanguage(e.target.value)}
                  onPressEnter={(e) => {
                    if (e.shiftKey) return;
                    e.preventDefault();
                    handleGenerateSQL();
                  }}
                />
                <Text type="secondary" style={{ fontSize: 12 }}>
                  按 Enter 键快速生成，Shift + Enter 换行
                </Text>
              </div>

              {/* 操作按钮 */}
              <Space>
                <Button
                  type="primary"
                  icon={<SendOutlined />}
                  onClick={() => handleGenerateSQL()}
                  loading={isGenerating}
                  size="large"
                >
                  生成 SQL
                </Button>
                <Button icon={<ClearOutlined />} onClick={handleClear}>
                  清空
                </Button>
              </Space>

              {/* 生成结果 */}
              {sqlResult && (
                <>
                  <Divider />
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                      <Title level={5} style={{ margin: 0 }}>
                        生成的 SQL
                      </Title>
                      <Space>
                        <Tag color={getConfidenceColor(sqlResult.confidence)} icon={<ThunderboltOutlined />}>
                          置信度: {(sqlResult.confidence * 100).toFixed(0)}%
                        </Tag>
                      </Space>
                    </div>

                    <div
                      style={{
                        backgroundColor: '#f6f8fa',
                        padding: 16,
                        borderRadius: 8,
                        overflow: 'auto',
                        maxHeight: 300,
                        border: '1px solid #e8e8e8',
                      }}
                    >
                      <pre
                        style={{
                          margin: 0,
                          fontFamily: 'Monaco, Menlo, monospace',
                          fontSize: 13,
                          lineHeight: 1.6,
                          whiteSpace: 'pre-wrap',
                          wordBreak: 'break-word',
                        }}
                        dangerouslySetInnerHTML={{ __html: renderHighlightedSQL(sqlResult.sql) }}
                      />
                    </div>

                    {sqlResult.tables_used && sqlResult.tables_used.length > 0 && (
                      <div style={{ marginTop: 12 }}>
                        <Text type="secondary">涉及表: </Text>
                        {sqlResult.tables_used.map((table) => (
                          <Tag key={table} icon={<TableOutlined />} color="blue" style={{ marginLeft: 4 }}>
                            {table}
                          </Tag>
                        ))}
                      </div>
                    )}

                    <Space style={{ marginTop: 12 }}>
                      <Button icon={<CopyOutlined />} onClick={handleCopySQL}>
                        复制 SQL
                      </Button>
                      {selectedDatabase && (
                        <Button
                          type="primary"
                          icon={<PlayCircleOutlined />}
                          onClick={handleExecuteSQL}
                          loading={isExecuting}
                        >
                          执行查询
                        </Button>
                      )}
                    </Space>
                  </div>
                </>
              )}

              {/* 执行结果 */}
              {executeResult && (
                <>
                  <Divider />
                  <div>
                    <Title level={5} style={{ marginBottom: 12 }}>
                      执行结果
                    </Title>
                    <Row gutter={16} style={{ marginBottom: 16 }}>
                      <Col span={8}>
                        <Statistic
                          title="返回行数"
                          value={executeResult.row_count}
                          suffix="条"
                        />
                      </Col>
                      <Col span={8}>
                        <Statistic
                          title="执行时间"
                          value={executeResult.execution_time_ms}
                          suffix="ms"
                        />
                      </Col>
                      <Col span={8}>
                        <Statistic
                          title="列数"
                          value={executeResult.columns.length}
                        />
                      </Col>
                    </Row>

                    {executeResult.rows.length > 0 ? (
                      <div
                        style={{
                          overflow: 'auto',
                          maxHeight: 400,
                          border: '1px solid #e8e8e8',
                          borderRadius: 8,
                        }}
                      >
                        <table
                          style={{
                            width: '100%',
                            borderCollapse: 'collapse',
                            fontSize: 13,
                          }}
                        >
                          <thead
                            style={{
                              position: 'sticky',
                              top: 0,
                              backgroundColor: '#fafafa',
                            }}
                          >
                            <tr>
                              {executeResult.columns.map((col) => (
                                <th
                                  key={col}
                                  style={{
                                    padding: '10px 16px',
                                    textAlign: 'left',
                                    borderBottom: '2px solid #e8e8e8',
                                    fontWeight: 600,
                                  }}
                                >
                                  {col}
                                </th>
                              ))}
                            </tr>
                          </thead>
                          <tbody>
                            {executeResult.rows.map((row, index) => (
                              <tr
                                key={index}
                                style={{
                                  borderBottom: '1px solid #f0f0f0',
                                  backgroundColor: index % 2 === 0 ? '#fff' : '#fafafa',
                                }}
                              >
                                {executeResult.columns.map((col) => (
                                  <td
                                    key={col}
                                    style={{
                                      padding: '8px 16px',
                                      maxWidth: 300,
                                      overflow: 'hidden',
                                      textOverflow: 'ellipsis',
                                      whiteSpace: 'nowrap',
                                    }}
                                  >
                                    {String(row[col] ?? '-')}
                                  </td>
                                ))}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    ) : (
                      <Empty description="查询结果为空" />
                    )}
                  </div>
                </>
              )}
            </Space>
          </Card>
        </Col>

        {/* 右侧：查询历史 */}
        <Col span={10}>
          <Card
            title="查询历史"
            extra={
              <Text type="secondary">
                <ClockCircleOutlined /> {queryHistory.length} 条记录
              </Text>
            }
          >
            {queryHistory.length === 0 ? (
              <Empty description="暂无查询历史" />
            ) : (
              <div style={{ maxHeight: 700, overflow: 'auto' }}>
                <Space direction="vertical" style={{ width: '100%' }} size="middle">
                  {queryHistory.map((item) => (
                    <Card
                      key={item.id}
                      size="small"
                      style={{
                        cursor: 'pointer',
                        border: item.starred ? '1px solid #faad14' : undefined,
                      }}
                      hoverable
                      onClick={() => loadFromHistory(item)}
                    >
                      <Space direction="vertical" style={{ width: '100%' }} size="small">
                        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                          <Text
                            ellipsis={{ tooltip: item.naturalLanguage }}
                            style={{ maxWidth: 280, fontWeight: 500 }}
                          >
                            {item.naturalLanguage}
                          </Text>
                          <Space size="small">
                            {item.starred ? (
                              <StarFilled style={{ color: '#faad14' }} />
                            ) : (
                              <StarOutlined style={{ color: '#d9d9d9' }} />
                            )}
                          </Space>
                        </div>

                        <div
                          style={{
                            backgroundColor: '#f6f8fa',
                            padding: '8px',
                            borderRadius: 4,
                            fontSize: 12,
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap',
                          }}
                        >
                          {item.sql}
                        </div>

                        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                          <Space size="small">
                            <Tag
                              color={getConfidenceColor(item.confidence)}
                              style={{ margin: 0, fontSize: 11 }}
                            >
                              {(item.confidence * 100).toFixed(0)}%
                            </Tag>
                            {item.database && (
                              <Tag style={{ margin: 0, fontSize: 11 }}>
                                {item.database}
                              </Tag>
                            )}
                          </Space>
                          <Text type="secondary" style={{ fontSize: 11 }}>
                            {formatTimestamp(item.timestamp)}
                          </Text>
                        </div>

                        <div style={{ display: 'flex', gap: 8 }}>
                          <Button
                            size="small"
                            type="text"
                            icon={item.starred ? <StarFilled /> : <StarOutlined />}
                            style={{ fontSize: 11 }}
                            onClick={(e) => {
                              e.stopPropagation();
                              toggleStar(item.id);
                            }}
                          >
                            {item.starred ? '已收藏' : '收藏'}
                          </Button>
                          <Button
                            size="small"
                            type="text"
                            danger
                            icon={<DeleteOutlined />}
                            style={{ fontSize: 11 }}
                            onClick={(e) => {
                              e.stopPropagation();
                              deleteHistory(item.id);
                            }}
                          >
                            删除
                          </Button>
                        </div>
                      </Space>
                    </Card>
                  ))}
                </Space>
              </div>
            )}
          </Card>
        </Col>
      </Row>
    </div>
  );
}

export default Text2SQLPage;
