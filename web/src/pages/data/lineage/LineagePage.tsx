import { useState } from 'react';
import {
  Card,
  Table,
  Button,
  Tag,
  Space,
  Input,
  Select,
  Drawer,
  Descriptions,
  Tabs,
  List,
  Alert,
  Row,
  Col,
  Statistic,
  message,
  Spin,
  Tooltip,
  Progress,
  Divider,
} from 'antd';
import {
  SearchOutlined,
  NodeIndexOutlined,
  ArrowLeftOutlined,
  ArrowRightOutlined,
  RobotOutlined,
  BulbOutlined,
  WarningOutlined,
  CodeOutlined,
  ThunderboltOutlined,
  ExclamationCircleOutlined,
  CheckCircleOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation } from '@tanstack/react-query';
import data from '@/services/data';
import type { LineageNode, AIImpactAnalysis, SQLLineageResult } from '@/services/data';
import LineageGraphComponent from '@/components/LineageGraph';

const { TextArea } = Input;

const { Option } = Select;
const { Search } = Input;

function LineagePage() {
  const [activeTab, setActiveTab] = useState('graph');
  const [selectedTable, setSelectedTable] = useState<string>('');
  const [selectedNode, setSelectedNode] = useState<LineageNode | null>(null);
  const [depth, setDepth] = useState(2);
  const [impactTable, setImpactTable] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState<string>('');

  // AI 影响分析相关状态
  const [aiImpactResult, setAiImpactResult] = useState<AIImpactAnalysis | null>(null);
  const [changeType, setChangeType] = useState<'schema_change' | 'data_change' | 'deletion' | 'rename'>('schema_change');

  // SQL 血缘解析相关状态
  const [sqlInput, setSqlInput] = useState<string>('');
  const [sqlLineageResult, setSqlLineageResult] = useState<SQLLineageResult | null>(null);

  // 表级血缘
  const { data: lineageData, isLoading: isLoadingLineage, refetch: refetchLineage } = useQuery({
    queryKey: ['tableLineage', selectedTable, depth],
    queryFn: () => data.getTableLineage(selectedTable, depth),
    enabled: !!selectedTable && activeTab === 'graph',
  });

  // 影响分析
  const { data: impactData } = useQuery({
    queryKey: ['impactAnalysis', impactTable],
    queryFn: () => data.getImpactAnalysis('table', impactTable),
    enabled: !!impactTable && activeTab === 'impact',
  });

  // 搜索血缘
  const { data: searchData, isLoading: isSearching } = useQuery({
    queryKey: ['searchLineage', searchQuery],
    queryFn: () => data.searchLineage(searchQuery),
    enabled: searchQuery.length >= 2,
  });

  // 字段级血缘
  const [columnLineageParams, setColumnLineageParams] = useState<{ table: string; column: string } | null>(null);
  const { data: columnLineageData } = useQuery({
    queryKey: ['columnLineage', columnLineageParams?.table, columnLineageParams?.column],
    queryFn: () => data.getColumnLineage(columnLineageParams!.table, columnLineageParams!.column),
    enabled: !!columnLineageParams && activeTab === 'column',
  });

  // AI 影响分析 mutation
  const aiImpactMutation = useMutation({
    mutationFn: async () => {
      if (!impactTable || !impactData?.data) {
        throw new Error('请先选择表并获取基础影响分析');
      }
      const nodeInfo = {
        node_type: 'table',
        name: impactTable,
        full_name: impactTable,
      };
      const downstreamNodes = impactData.data?.impacted_nodes
        ?.filter((n) => n.node_type === 'table')
        .map((t) => ({
          node_id: t.id || t.name,
          name: t.name || t.label,
          full_name: t.full_name || t.name,
          node_type: 'table' as const,
          impact_level: 3, // Default medium impact level (number as expected by API)
        })) || [];
      return data.getAIImpactAnalysis(nodeInfo, {
        downstream_nodes: downstreamNodes,
        change_type: changeType,
      });
    },
    onSuccess: (response) => {
      if (response?.data) {
        setAiImpactResult(response.data);
        message.success('AI 影响分析完成');
      }
    },
    onError: (error: Error) => {
      message.error(`AI 影响分析失败: ${error.message}`);
    },
  });

  // SQL 血缘解析 mutation
  const sqlLineageMutation = useMutation({
    mutationFn: async () => {
      if (!sqlInput.trim()) {
        throw new Error('请输入 SQL 语句');
      }
      return data.parseSQLLineage(sqlInput, { use_ai: true });
    },
    onSuccess: (response) => {
      if (response?.data) {
        setSqlLineageResult(response.data);
        message.success('SQL 血缘解析完成');
      }
    },
    onError: (error: Error) => {
      message.error(`SQL 血缘解析失败: ${error.message}`);
    },
  });

  // 常用表列表（模拟数据）
  const commonTables = [
    'users',
    'orders',
    'order_items',
    'products',
    'categories',
    'customers',
    'inventory',
    'shipments',
    'payments',
    'reviews',
  ];

  // 获取风险级别颜色
  const getRiskLevelColor = (level: string) => {
    switch (level) {
      case 'critical': return 'red';
      case 'high': return 'orange';
      case 'medium': return 'gold';
      case 'low': return 'green';
      default: return 'default';
    }
  };

  // 获取风险级别图标
  const getRiskLevelIcon = (level: string) => {
    switch (level) {
      case 'critical': return <ExclamationCircleOutlined />;
      case 'high': return <WarningOutlined />;
      case 'medium': return <InfoCircleOutlined />;
      case 'low': return <CheckCircleOutlined />;
      default: return <InfoCircleOutlined />;
    }
  };

  // 获取变更类型文本
  const getChangeTypeText = (type: string) => {
    const texts: Record<string, string> = {
      schema_change: '结构变更',
      data_change: '数据变更',
      deletion: '删除操作',
      rename: '重命名',
    };
    return texts[type] || type;
  };

  // 获取置信度颜色
  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 80) return 'green';
    if (confidence >= 60) return 'blue';
    if (confidence >= 40) return 'orange';
    return 'red';
  };

  const handleNodeClick = (node: LineageNode) => {
    if (node.type === 'table' || node.type === 'view') {
      setSelectedTable(node.name);
      setSelectedNode(node);
    }
  };

  const impactColumns = [
    {
      title: '表名',
      dataIndex: 'table',
      key: 'table',
      render: (table: string) => (
        <Button
          type="link"
          onClick={() => {
            setSelectedTable(table);
            setImpactTable(table);
          }}
        >
          {table}
        </Button>
      ),
    },
    {
      title: '距离',
      dataIndex: 'distance',
      key: 'distance',
      width: 100,
      render: (dist: number) => <Tag color={dist === 1 ? 'red' : dist === 2 ? 'orange' : 'blue'}>{dist} 层</Tag>,
    },
    {
      title: '影响类型',
      dataIndex: 'impact_type',
      key: 'impact_type',
      width: 150,
    },
  ];

  const searchColumns = [
    {
      title: '表名',
      dataIndex: 'table',
      key: 'table',
      render: (table: string, record: { table: string }) => (
        <Button
          type="link"
          onClick={() => setSelectedTable(record.table)}
        >
          {table}
        </Button>
      ),
    },
    {
      title: '列名',
      dataIndex: 'column',
      key: 'column',
      render: (col: string) => col || '-',
    },
    {
      title: '上游数量',
      dataIndex: 'upstream_count',
      key: 'upstream_count',
      width: 100,
    },
    {
      title: '下游数量',
      dataIndex: 'downstream_count',
      key: 'downstream_count',
      width: 100,
    },
  ];

  return (
    <div style={{ padding: '24px' }}>
      <Card
        title="数据血缘管理"
        extra={
          <Space>
            <Select
              style={{ width: 200 }}
              placeholder="选择或输入表名"
              value={selectedTable || undefined}
              onChange={setSelectedTable}
              showSearch
              optionFilterProp="children"
            >
              {commonTables.map((table) => (
                <Option key={table} value={table}>
                  {table}
                </Option>
              ))}
            </Select>
            <Input.Search
              style={{ width: 250 }}
              placeholder="搜索血缘关系"
              onSearch={setSearchQuery}
              enterButton={<SearchOutlined />}
            />
          </Space>
        }
      >
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={[
            {
              key: 'graph',
              label: (
                <span>
                  <NodeIndexOutlined />
                  血缘图谱
                </span>
              ),
              children: (
                <div>
                  {!selectedTable ? (
                    <Alert
                      message="请先选择一个表查看其血缘关系"
                      type="info"
                      showIcon
                      style={{ marginBottom: 16 }}
                    />
                  ) : (
                    <>
                      <Space style={{ marginBottom: 16 }}>
                        <span>当前表: <Tag color="blue">{selectedTable}</Tag></span>
                        <Select value={depth} onChange={setDepth} style={{ width: 120 }}>
                          <Option value={1}>1 层</Option>
                          <Option value={2}>2 层</Option>
                          <Option value={3}>3 层</Option>
                          <Option value={4}>4 层</Option>
                        </Select>
                      </Space>
                      <LineageGraphComponent
                        graph={lineageData?.data || null}
                        loading={isLoadingLineage}
                        onNodeClick={handleNodeClick}
                        onRefresh={() => refetchLineage()}
                        height={500}
                      />
                    </>
                  )}
                </div>
              ),
            },
            {
              key: 'column',
              label: '字段级血缘',
              children: (
                <div>
                  <Space style={{ marginBottom: 16 }}>
                    <Select
                      style={{ width: 200 }}
                      placeholder="选择表"
                      value={columnLineageParams?.table}
                      onChange={(val) => setColumnLineageParams((prev) => ({ table: val, column: prev?.column || '' }))}
                    >
                      {commonTables.map((table) => (
                        <Option key={table} value={table}>
                          {table}
                        </Option>
                      ))}
                    </Select>
                    <Select
                      style={{ width: 200 }}
                      placeholder="选择字段"
                      value={columnLineageParams?.column}
                      onChange={(val) => setColumnLineageParams((prev) => ({ table: prev?.table || '', column: val }))}
                      disabled={!columnLineageParams?.table}
                    >
                      {['id', 'name', 'user_id', 'order_id', 'amount', 'status', 'created_at'].map((col) => (
                        <Option key={col} value={col}>
                          {col}
                        </Option>
                      ))}
                    </Select>
                  </Space>

                  {columnLineageData?.data ? (
                    <Card title={`${columnLineageData.data.table}.${columnLineageData.data.column} 的血缘关系`}>
                      <Row gutter={16}>
                        <Col span={12}>
                          <Card size="small" title="上游字段" extra={<ArrowLeftOutlined />}>
                            <List
                              size="small"
                              dataSource={columnLineageData.data.source_columns}
                              renderItem={(item) => (
                                <List.Item>
                                  <Space>
                                    <Tag>{item.table}</Tag>
                                    <span>{item.column}</span>
                                    {item.transform && (
                                      <Tag color="cyan">{item.transform}</Tag>
                                    )}
                                  </Space>
                                </List.Item>
                              )}
                            />
                          </Card>
                        </Col>
                        <Col span={12}>
                          <Card size="small" title="下游字段" extra={<ArrowRightOutlined />}>
                            <List
                              size="small"
                              dataSource={columnLineageData.data.target_columns}
                              renderItem={(item) => (
                                <List.Item>
                                  <Space>
                                    <Tag>{item.table}</Tag>
                                    <span>{item.column}</span>
                                    {item.transform && (
                                      <Tag color="cyan">{item.transform}</Tag>
                                    )}
                                  </Space>
                                </List.Item>
                              )}
                            />
                          </Card>
                        </Col>
                      </Row>
                    </Card>
                  ) : (
                    <Alert
                      message="请选择表和字段查看字段级血缘"
                      type="info"
                      showIcon
                    />
                  )}
                </div>
              ),
            },
            {
              key: 'impact',
              label: (
                <span>
                  <ThunderboltOutlined />
                  AI 影响分析
                </span>
              ),
              children: (
                <div>
                  <Space style={{ marginBottom: 16 }} wrap>
                    <Select
                      style={{ width: 200 }}
                      placeholder="选择要分析的表"
                      value={impactTable || undefined}
                      onChange={(val) => {
                        setImpactTable(val);
                        setAiImpactResult(null);
                      }}
                      showSearch
                    >
                      {commonTables.map((table) => (
                        <Option key={table} value={table}>
                          {table}
                        </Option>
                      ))}
                    </Select>
                    <Select
                      style={{ width: 150 }}
                      placeholder="变更类型"
                      value={changeType}
                      onChange={setChangeType}
                    >
                      <Option value="schema_change">结构变更</Option>
                      <Option value="data_change">数据变更</Option>
                      <Option value="deletion">删除操作</Option>
                      <Option value="rename">重命名</Option>
                    </Select>
                    <Tooltip title="使用 AI 进行深度影响分析，生成风险评估和建议措施">
                      <Button
                        type="primary"
                        icon={<RobotOutlined />}
                        loading={aiImpactMutation.isPending}
                        onClick={() => aiImpactMutation.mutate()}
                        disabled={!impactData?.data}
                      >
                        AI 深度分析
                      </Button>
                    </Tooltip>
                  </Space>

                  {impactData?.data ? (
                    <>
                      <Card style={{ marginBottom: 16 }}>
                        <Row gutter={16} style={{ marginBottom: 24 }}>
                          <Col span={6}>
                            <Statistic
                              title="影响级别"
                              value={impactData.data.impact_level}
                              valueStyle={{
                                color: impactData.data.impact_level === 'high' ? '#ff4d4f' :
                                       impactData.data.impact_level === 'medium' ? '#faad14' : '#52c41a'
                              }}
                            />
                          </Col>
                          <Col span={6}>
                            <Statistic
                              title="上游表数量"
                              value={impactData.data.upstream_count}
                              prefix={<ArrowLeftOutlined />}
                            />
                          </Col>
                          <Col span={6}>
                            <Statistic
                              title="下游表数量"
                              value={impactData.data.downstream_count}
                              prefix={<ArrowRightOutlined />}
                            />
                          </Col>
                          <Col span={6}>
                            <Statistic
                              title="影响报表数"
                              value={impactData.data.affected_reports?.length || 0}
                            />
                          </Col>
                        </Row>

                        <Card title="受影响的表" type="inner" size="small">
                          <Table
                            columns={impactColumns}
                            dataSource={impactData.data.affected_tables}
                            rowKey="table"
                            pagination={false}
                            size="small"
                          />
                        </Card>
                      </Card>

                      {/* 受影响的 ETL 任务 - 待后端实现 */}
                      {/* impactData.data.affected_etl_tasks && impactData.data.affected_etl_tasks.length > 0 && (
                        <Card title="受影响的 ETL 任务" type="inner" size="small" style={{ marginTop: 16 }}>
                          <List
                            size="small"
                            dataSource={impactData.data.affected_etl_tasks}
                            renderItem={(task: string) => (
                              <List.Item>
                                <Tag>{task}</Tag>
                              </List.Item>
                            )}
                          />
                        </Card>
                      )} */}

                      {/* AI 影响分析结果 */}
                      {aiImpactMutation.isPending && (
                        <Card>
                          <div style={{ textAlign: 'center', padding: '24px' }}>
                            <Spin size="large" />
                            <p style={{ marginTop: 16, color: '#666' }}>AI 正在分析影响范围...</p>
                          </div>
                        </Card>
                      )}

                      {aiImpactResult && (
                        <Card
                          title={
                            <Space>
                              <RobotOutlined style={{ color: '#1890ff' }} />
                              AI 影响分析报告
                            </Space>
                          }
                        >
                          {/* 风险概览 */}
                          <Row gutter={16} style={{ marginBottom: 16 }}>
                            <Col span={8}>
                              <Card size="small" bordered={false} style={{ backgroundColor: '#fafafa' }}>
                                <Statistic
                                  title="AI 风险评估"
                                  value={aiImpactResult.risk_level?.toUpperCase()}
                                  prefix={getRiskLevelIcon(aiImpactResult.risk_level)}
                                  valueStyle={{ color: aiImpactResult.risk_level === 'critical' ? '#ff4d4f' : aiImpactResult.risk_level === 'high' ? '#fa8c16' : aiImpactResult.risk_level === 'medium' ? '#faad14' : '#52c41a' }}
                                />
                              </Card>
                            </Col>
                            <Col span={8}>
                              <Card size="small" bordered={false} style={{ backgroundColor: '#fafafa' }}>
                                <Statistic
                                  title="变更类型"
                                  value={getChangeTypeText(aiImpactResult.change_type)}
                                />
                              </Card>
                            </Col>
                            <Col span={8}>
                              <Card size="small" bordered={false} style={{ backgroundColor: '#fafafa' }}>
                                <Statistic
                                  title="影响节点数"
                                  value={aiImpactResult.affected_nodes?.length || 0}
                                />
                              </Card>
                            </Col>
                          </Row>

                          {/* 影响摘要 */}
                          {aiImpactResult.impact_summary && (
                            <Alert
                              message="影响摘要"
                              description={aiImpactResult.impact_summary}
                              type={aiImpactResult.risk_level === 'high' || aiImpactResult.risk_level === 'critical' ? 'warning' : 'info'}
                              showIcon
                              icon={<BulbOutlined />}
                              style={{ marginBottom: 16 }}
                            />
                          )}

                          {/* AI 建议 */}
                          {aiImpactResult.recommendations && aiImpactResult.recommendations.length > 0 && (
                            <Card
                              title={<><BulbOutlined style={{ marginRight: 8 }} />AI 建议措施</>}
                              type="inner"
                              size="small"
                            >
                              <List
                                size="small"
                                dataSource={aiImpactResult.recommendations}
                                renderItem={(item, index) => (
                                  <List.Item>
                                    <Space>
                                      <Tag color="blue">{index + 1}</Tag>
                                      <span>{item}</span>
                                    </Space>
                                  </List.Item>
                                )}
                              />
                            </Card>
                          )}
                        </Card>
                      )}
                    </>
                  ) : (
                    <Alert
                      message="请选择一个表进行影响分析"
                      description="选择表后可查看基础影响分析，点击「AI 深度分析」获取智能风险评估和建议措施"
                      type="info"
                      showIcon
                    />
                  )}
                </div>
              ),
            },
            {
              key: 'search',
              label: '血缘搜索',
              children: (
                <div>
                  <Search
                    placeholder="搜索表名或字段名"
                    allowClear
                    enterButton={<SearchOutlined />}
                    size="large"
                    onSearch={setSearchQuery}
                    style={{ marginBottom: 16 }}
                  />
                  <Table
                    columns={searchColumns}
                    dataSource={searchData?.data?.results || []}
                    rowKey={(record: { table: string; column?: string }) => `${record.table}-${record.column || ''}`}
                    loading={isSearching}
                    pagination={false}
                  />
                </div>
              ),
            },
            {
              key: 'sql',
              label: (
                <span>
                  <CodeOutlined />
                  SQL 血缘解析
                </span>
              ),
              children: (
                <div>
                  <Alert
                    message="SQL 血缘自动解析"
                    description="输入 SQL 语句，AI 将自动识别源表、目标表及列级映射关系"
                    type="info"
                    showIcon
                    icon={<RobotOutlined />}
                    style={{ marginBottom: 16 }}
                  />

                  <Card title="SQL 输入" style={{ marginBottom: 16 }}>
                    <TextArea
                      rows={8}
                      placeholder={`输入 SQL 语句，例如：
INSERT INTO analytics.daily_sales
SELECT
    o.order_date,
    p.category,
    SUM(oi.quantity * oi.price) as total_sales
FROM orders o
JOIN order_items oi ON o.order_id = oi.order_id
JOIN products p ON oi.product_id = p.product_id
GROUP BY o.order_date, p.category`}
                      value={sqlInput}
                      onChange={(e) => setSqlInput(e.target.value)}
                      style={{ fontFamily: 'monospace' }}
                    />
                    <div style={{ marginTop: 16, textAlign: 'right' }}>
                      <Space>
                        <Button onClick={() => { setSqlInput(''); setSqlLineageResult(null); }}>
                          清空
                        </Button>
                        <Button
                          type="primary"
                          icon={<ThunderboltOutlined />}
                          loading={sqlLineageMutation.isPending}
                          onClick={() => sqlLineageMutation.mutate()}
                          disabled={!sqlInput.trim()}
                        >
                          解析血缘
                        </Button>
                      </Space>
                    </div>
                  </Card>

                  {/* SQL 解析结果 */}
                  {sqlLineageMutation.isPending && (
                    <Card>
                      <div style={{ textAlign: 'center', padding: '24px' }}>
                        <Spin size="large" />
                        <p style={{ marginTop: 16, color: '#666' }}>AI 正在解析 SQL 血缘关系...</p>
                      </div>
                    </Card>
                  )}

                  {sqlLineageResult && (
                    <Card
                      title={
                        <Space>
                          <NodeIndexOutlined style={{ color: '#1890ff' }} />
                          血缘解析结果
                          <Tag color={getConfidenceColor(sqlLineageResult.confidence)}>
                            置信度: {sqlLineageResult.confidence}%
                          </Tag>
                          <Tag color={sqlLineageResult.parse_method === 'ai_enhanced' ? 'purple' : 'default'}>
                            {sqlLineageResult.parse_method === 'ai_enhanced' ? 'AI 增强解析' : '规则解析'}
                          </Tag>
                        </Space>
                      }
                    >
                      <Row gutter={16}>
                        {/* 源表 */}
                        <Col span={12}>
                          <Card
                            title={<><ArrowRightOutlined style={{ marginRight: 8 }} />源表</>}
                            type="inner"
                            size="small"
                          >
                            {sqlLineageResult.source_tables && sqlLineageResult.source_tables.length > 0 ? (
                              <List
                                size="small"
                                dataSource={sqlLineageResult.source_tables}
                                renderItem={(table) => (
                                  <List.Item>
                                    <Button
                                      type="link"
                                      icon={<SearchOutlined />}
                                      onClick={() => {
                                        setSelectedTable(table);
                                        setActiveTab('graph');
                                      }}
                                    >
                                      {table}
                                    </Button>
                                  </List.Item>
                                )}
                              />
                            ) : (
                              <div style={{ color: '#999', padding: 8 }}>未识别到源表</div>
                            )}
                          </Card>
                        </Col>

                        {/* 目标表 */}
                        <Col span={12}>
                          <Card
                            title={<><ArrowLeftOutlined style={{ marginRight: 8 }} />目标表</>}
                            type="inner"
                            size="small"
                          >
                            {sqlLineageResult.target_table ? (
                              <List
                                size="small"
                                dataSource={[sqlLineageResult.target_table]}
                                renderItem={(table) => (
                                  <List.Item>
                                    <Button
                                      type="link"
                                      icon={<SearchOutlined />}
                                      onClick={() => {
                                        setSelectedTable(table);
                                        setActiveTab('graph');
                                      }}
                                    >
                                      {table}
                                    </Button>
                                  </List.Item>
                                )}
                              />
                            ) : (
                              <div style={{ color: '#999', padding: 8 }}>未识别到目标表（可能是 SELECT 查询）</div>
                            )}
                          </Card>
                        </Col>
                      </Row>

                      {/* 列级映射 */}
                      {sqlLineageResult.column_mappings && sqlLineageResult.column_mappings.length > 0 && (
                        <Card
                          title="列级血缘映射"
                          type="inner"
                          size="small"
                          style={{ marginTop: 16 }}
                        >
                          <Table
                            size="small"
                            dataSource={sqlLineageResult.column_mappings}
                            rowKey={(r, i) => `${r.source_column}-${r.target_column}-${i}`}
                            pagination={false}
                            columns={[
                              {
                                title: '源列',
                                dataIndex: 'source_column',
                                key: 'source_column',
                                render: (col: string) => <Tag>{col}</Tag>,
                              },
                              {
                                title: '目标列',
                                dataIndex: 'target_column',
                                key: 'target_column',
                                render: (col: string) => <Tag color="blue">{col}</Tag>,
                              },
                              {
                                title: '转换',
                                dataIndex: 'transformation',
                                key: 'transformation',
                                render: (trans: string) => trans ? <Tag color="cyan">{trans}</Tag> : '-',
                              },
                            ]}
                          />
                        </Card>
                      )}

                      {/* 血缘边 */}
                      {sqlLineageResult.lineage_edges && sqlLineageResult.lineage_edges.length > 0 && (
                        <Card
                          title="血缘关系边"
                          type="inner"
                          size="small"
                          style={{ marginTop: 16 }}
                        >
                          <Table
                            size="small"
                            dataSource={sqlLineageResult.lineage_edges}
                            rowKey={(r, i) => `${r.source}-${r.target}-${i}`}
                            pagination={false}
                            columns={[
                              {
                                title: '源',
                                dataIndex: 'source',
                                key: 'source',
                                render: (s: string) => <Tag>{s}</Tag>,
                              },
                              {
                                title: '目标',
                                dataIndex: 'target',
                                key: 'target',
                                render: (t: string) => <Tag color="blue">{t}</Tag>,
                              },
                              {
                                title: '关系类型',
                                dataIndex: 'relation_type',
                                key: 'relation_type',
                                render: (type: string) => <Tag color="green">{type}</Tag>,
                              },
                              {
                                title: '置信度',
                                dataIndex: 'confidence',
                                key: 'confidence',
                                render: (conf: number) => (
                                  <Progress
                                    percent={conf}
                                    size="small"
                                    strokeColor={getConfidenceColor(conf)}
                                    format={(p) => `${p}%`}
                                  />
                                ),
                              },
                            ]}
                          />
                        </Card>
                      )}

                      {/* 错误信息 */}
                      {sqlLineageResult.errors && sqlLineageResult.errors.length > 0 && (
                        <Alert
                          message="解析警告"
                          description={
                            <ul style={{ margin: 0, paddingLeft: 20 }}>
                              {sqlLineageResult.errors.map((err, i) => (
                                <li key={i}>{err}</li>
                              ))}
                            </ul>
                          }
                          type="warning"
                          showIcon
                          style={{ marginTop: 16 }}
                        />
                      )}
                    </Card>
                  )}
                </div>
              ),
            },
          ]}
        />
      </Card>

      {/* 节点详情抽屉 */}
      <Drawer
        title="节点详情"
        open={!!selectedNode}
        onClose={() => setSelectedNode(null)}
        width={500}
      >
        {selectedNode && (
          <Descriptions column={1} bordered>
            <Descriptions.Item label="节点类型">
              <Tag color="blue">{selectedNode.type}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="名称">{selectedNode.name}</Descriptions.Item>
            {selectedNode.database && (
              <Descriptions.Item label="数据库">{selectedNode.database}</Descriptions.Item>
            )}
            {selectedNode.schema && (
              <Descriptions.Item label="Schema">{selectedNode.schema}</Descriptions.Item>
            )}
            {selectedNode.source_type && (
              <Descriptions.Item label="来源类型">{selectedNode.source_type}</Descriptions.Item>
            )}
            {selectedNode.properties && (
              <Descriptions.Item label="属性">
                <pre style={{ margin: 0, fontSize: 12 }}>
                  {JSON.stringify(selectedNode.properties, null, 2)}
                </pre>
              </Descriptions.Item>
            )}
          </Descriptions>
        )}
      </Drawer>
    </div>
  );
}

export default LineagePage;
