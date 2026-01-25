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
} from 'antd';
import {
  SearchOutlined,
  NodeIndexOutlined,
  ArrowLeftOutlined,
  ArrowRightOutlined,
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import alldata from '@/services/alldata';
import type { LineageNode } from '@/services/alldata';
import LineageGraphComponent from '@/components/LineageGraph';

const { Option } = Select;
const { Search } = Input;

function LineagePage() {
  const [activeTab, setActiveTab] = useState('graph');
  const [selectedTable, setSelectedTable] = useState<string>('');
  const [selectedNode, setSelectedNode] = useState<LineageNode | null>(null);
  const [depth, setDepth] = useState(2);
  const [impactTable, setImpactTable] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState<string>('');

  // 表级血缘
  const { data: lineageData, isLoading: isLoadingLineage, refetch: refetchLineage } = useQuery({
    queryKey: ['tableLineage', selectedTable, depth],
    queryFn: () => alldata.getTableLineage(selectedTable, depth),
    enabled: !!selectedTable && activeTab === 'graph',
  });

  // 影响分析
  const { data: impactData } = useQuery({
    queryKey: ['impactAnalysis', impactTable],
    queryFn: () => alldata.getImpactAnalysis(impactTable),
    enabled: !!impactTable && activeTab === 'impact',
  });

  // 搜索血缘
  const { data: searchData, isLoading: isSearching } = useQuery({
    queryKey: ['searchLineage', searchQuery],
    queryFn: () => alldata.searchLineage(searchQuery),
    enabled: searchQuery.length >= 2,
  });

  // 字段级血缘
  const [columnLineageParams, setColumnLineageParams] = useState<{ table: string; column: string } | null>(null);
  const { data: columnLineageData } = useQuery({
    queryKey: ['columnLineage', columnLineageParams?.table, columnLineageParams?.column],
    queryFn: () => alldata.getColumnLineage(columnLineageParams!.table, columnLineageParams!.column),
    enabled: !!columnLineageParams && activeTab === 'column',
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
      render: (table: string, record: any) => (
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
              label: '影响分析',
              children: (
                <div>
                  <Space style={{ marginBottom: 16 }}>
                    <Select
                      style={{ width: 200 }}
                      placeholder="选择要分析的表"
                      value={impactTable || undefined}
                      onChange={setImpactTable}
                      showSearch
                    >
                      {commonTables.map((table) => (
                        <Option key={table} value={table}>
                          {table}
                        </Option>
                      ))}
                    </Select>
                  </Space>

                  {impactData?.data ? (
                    <Card>
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

                      {impactData.data.affected_etl_tasks && impactData.data.affected_etl_tasks.length > 0 && (
                        <Card title="受影响的 ETL 任务" type="inner" size="small" style={{ marginTop: 16 }}>
                          <List
                            size="small"
                            dataSource={impactData.data.affected_etl_tasks}
                            renderItem={(task) => (
                              <List.Item>
                                <Tag>{task}</Tag>
                              </List.Item>
                            )}
                          />
                        </Card>
                      )}
                    </Card>
                  ) : (
                    <Alert
                      message="请选择一个表进行影响分析"
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
                    rowKey={(record) => `${record.table}-${record.column || ''}`}
                    loading={isSearching}
                    pagination={false}
                  />
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
