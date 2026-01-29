import { useState } from 'react';
import {
  Card,
  Tree,
  Table,
  Input,
  Button,
  Space,
  Descriptions,
  Tag,
  message,
  Tabs,
  Modal,
  Tooltip,
  Progress,
  Alert,
  Spin,
} from 'antd';
import {
  DatabaseOutlined,
  TableOutlined,
  SearchOutlined,
  CopyOutlined,
  RobotOutlined,
  SafetyOutlined,
  TagsOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { DataNode } from 'antd/es/tree';
import data from '@/services/data';
import type { AIAnnotation, SensitivityReport } from '@/services/data';
import AISensitivityScanPanel from '@/pages/data/metadata/AISensitivityScanPanel';

const { Search } = Input;
const { TextArea } = Input;

function MetadataPage() {
  const [selectedDatabase, setSelectedDatabase] = useState<string>('');
  const [selectedTable, setSelectedTable] = useState<string>('');
  const [searchText, setSearchText] = useState('');

  const [sqlModalOpen, setSqlModalOpen] = useState(false);
  const [generatedSql, setGeneratedSql] = useState('');
  const [naturalLanguage, setNaturalLanguage] = useState('');

  // AI 标注相关状态
  const [annotationModalOpen, setAnnotationModalOpen] = useState(false);
  const [annotations, setAnnotations] = useState<AIAnnotation[]>([]);
  const [sensitivityReport, setSensitivityReport] = useState<SensitivityReport | null>(null);

  // AI 扫描相关状态
  const [aiScanModalOpen, setAiScanModalOpen] = useState(false);

  const queryClient = useQueryClient();

  // 获取数据库列表
  const { data: databasesData } = useQuery({
    queryKey: ['databases'],
    queryFn: data.getDatabases,
  });

  // 获取表列表
  const { data: tablesData } = useQuery({
    queryKey: ['tables', selectedDatabase],
    queryFn: () => data.getTables(selectedDatabase),
    enabled: !!selectedDatabase,
  });

  // 获取表详情
  const { data: tableDetail, isLoading: isLoadingDetail } = useQuery({
    queryKey: ['tableDetail', selectedDatabase, selectedTable],
    queryFn: () => data.getTableDetail(selectedDatabase, selectedTable),
    enabled: !!(selectedDatabase && selectedTable),
  });

  // 智能表搜索
  const { data: searchResults, isLoading: isSearching } = useQuery({
    queryKey: ['tableSearch', searchText],
    queryFn: () => data.searchTables(searchText),
    enabled: searchText.length > 1,
  });

  // AI 标注 mutation
  const annotateMutation = useMutation({
    mutationFn: async () => {
      if (!selectedDatabase || !selectedTable) {
        throw new Error('请先选择表');
      }
      return data.annotateTable(selectedDatabase, selectedTable, {
        use_llm: true,
        save: true,
      });
    },
    onSuccess: (response) => {
      if (response?.data?.annotations) {
        setAnnotations(response.data.annotations);
        message.success('AI 标注完成');
        // 刷新表详情
        queryClient.invalidateQueries({ queryKey: ['tableDetail', selectedDatabase, selectedTable] });
      }
    },
    onError: (error: Error) => {
      message.error(`AI 标注失败: ${error.message}`);
    },
  });

  // 敏感字段报告 mutation
  const sensitivityMutation = useMutation({
    mutationFn: async () => {
      if (!selectedDatabase || !selectedTable) {
        throw new Error('请先选择表');
      }
      return data.getSensitivityReport(selectedDatabase, selectedTable);
    },
    onSuccess: (response) => {
      if (response?.data) {
        setSensitivityReport(response.data);
        setAnnotationModalOpen(true);
      }
    },
    onError: (error: Error) => {
      message.error(`获取敏感字段报告失败: ${error.message}`);
    },
  });

  // 执行 AI 标注
  const handleAIAnnotate = () => {
    if (!selectedDatabase || !selectedTable) {
      message.warning('请先选择表');
      return;
    }
    annotateMutation.mutate();
  };

  // 查看敏感字段报告
  const handleViewSensitivityReport = () => {
    if (!selectedDatabase || !selectedTable) {
      message.warning('请先选择表');
      return;
    }
    sensitivityMutation.mutate();
  };

  // Text-to-SQL
  const handleText2Sql = async () => {
    if (!naturalLanguage.trim()) {
      message.warning('请输入自然语言描述');
      return;
    }

    try {
      // 调用 agent Text2SQL API
      const response = await fetch('/api/v1/text2sql', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          natural_language: naturalLanguage,
          database: selectedDatabase || undefined,
        }),
      });

      if (!response.ok) {
        throw new Error('请求失败');
      }

      const data = await response.json();
      setGeneratedSql(data.data?.sql || '');
      setSqlModalOpen(true);
    } catch (error) {
      message.error('生成 SQL 失败');
    }
  };

  // 构建树形数据
  const buildTreeData = (): DataNode[] => {
    if (!databasesData?.data?.databases) return [];

    return databasesData.data.databases.map((db) => ({
      title: (
        <span>
          <DatabaseOutlined style={{ marginRight: 8 }} />
          {db.name}
        </span>
      ),
      key: `db-${db.name}`,
      selectable: false,
      children:
        tablesData?.data?.tables.map((table) => ({
          title: (
            <span>
              <TableOutlined style={{ marginRight: 8 }} />
              {table.name}
            </span>
          ),
          key: `${db.name}.${table.name}`,
          isLeaf: true,
        })) || [],
    }));
  };

  const handleTreeSelect = (selectedKeys: React.Key[]) => {
    const key = selectedKeys[0] as string;
    if (key && key.includes('.')) {
      const [db, table] = key.split('.');
      setSelectedDatabase(db);
      setSelectedTable(table);
    } else if (key?.startsWith('db-')) {
      const db = key.replace('db-', '');
      setSelectedDatabase(db);
      setSelectedTable('');
    }
  };

  const handleCopySql = () => {
    navigator.clipboard.writeText(generatedSql);
    message.success('SQL 已复制到剪贴板');
  };

  // 获取敏感级别颜色
  const getSensitivityLevelColor = (level?: string) => {
    switch (level) {
      case 'restricted': return 'red';
      case 'confidential': return 'orange';
      case 'internal': return 'blue';
      case 'public': return 'green';
      default: return 'default';
    }
  };

  // 获取敏感类型标签颜色
  const getSensitivityTypeColor = (type?: string) => {
    switch (type) {
      case 'pii': return 'red';
      case 'financial': return 'orange';
      case 'health': return 'purple';
      case 'credential': return 'volcano';
      default: return 'default';
    }
  };

  const tableColumns = [
    {
      title: '列名',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      render: (type: string) => <Tag>{type}</Tag>,
    },
    {
      title: '可空',
      dataIndex: 'nullable',
      key: 'nullable',
      width: 80,
      render: (nullable: boolean) => (nullable ? '是' : '否'),
    },
    {
      title: '主键',
      dataIndex: 'primary_key',
      key: 'primary_key',
      width: 80,
      render: (pk?: boolean) => (pk ? <Tag color="gold">是</Tag> : '-'),
    },
    {
      title: '外键',
      dataIndex: 'foreign_key',
      key: 'foreign_key',
      render: (fk?: { table: string; column: string }) =>
        fk ? (
          <Tag color="blue">
            {fk.table}.{fk.column}
          </Tag>
        ) : (
          '-'
        ),
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
      render: (desc?: string, record?: { ai_description?: string }) => (
        <Tooltip title={record?.ai_description ? `AI 描述: ${record.ai_description}` : undefined}>
          <span>
            {desc || record?.ai_description || '-'}
            {record?.ai_description && !desc && (
              <RobotOutlined style={{ marginLeft: 4, color: '#1890ff' }} />
            )}
          </span>
        </Tooltip>
      ),
    },
    {
      title: '敏感级别',
      dataIndex: 'sensitivity_level',
      key: 'sensitivity_level',
      width: 100,
      render: (level?: string) => level && level !== 'public' ? (
        <Tag color={getSensitivityLevelColor(level)} icon={<SafetyOutlined />}>
          {level}
        </Tag>
      ) : '-',
    },
    {
      title: '语义标签',
      dataIndex: 'semantic_tags',
      key: 'semantic_tags',
      width: 150,
      render: (tags?: string[]) => tags && tags.length > 0 ? (
        <Space size={[0, 4]} wrap>
          {tags.slice(0, 2).map((tag) => (
            <Tag key={tag} icon={<TagsOutlined />} color="geekblue">
              {tag}
            </Tag>
          ))}
          {tags.length > 2 && (
            <Tooltip title={tags.slice(2).join(', ')}>
              <Tag>+{tags.length - 2}</Tag>
            </Tooltip>
          )}
        </Space>
      ) : '-',
    },
  ];

  const searchColumns = [
    {
      title: '数据库',
      dataIndex: 'database',
      key: 'database',
    },
    {
      title: '表名',
      dataIndex: 'table',
      key: 'table',
    },
    {
      title: '相关度',
      dataIndex: 'relevance_score',
      key: 'relevance_score',
      render: (score: number) => (
        <Tag color={score > 0.8 ? 'green' : score > 0.5 ? 'blue' : 'default'}>
          {(score * 100).toFixed(0)}%
        </Tag>
      ),
    },
    {
      title: '匹配列',
      dataIndex: 'matched_columns',
      key: 'matched_columns',
      render: (cols: string[]) => cols.map((c) => <Tag key={c}>{c}</Tag>),
    },
  ];

  const tabItems = [
    {
      key: 'browse',
      label: '浏览',
      children: (
        <div style={{ display: 'flex', height: 500 }}>
          {/* 左侧数据库树 */}
          <Card
            title="数据库"
            style={{ width: 300, marginRight: 16 }}
            bodyStyle={{ padding: '8px', overflow: 'auto', height: 440 }}
          >
            <Tree
              treeData={buildTreeData()}
              onSelect={handleTreeSelect}
              showLine
              expandedKeys={selectedDatabase ? [`db-${selectedDatabase}`] : []}
              selectedKeys={
                selectedDatabase && selectedTable
                  ? [`${selectedDatabase}.${selectedTable}`]
                  : []
              }
            />
          </Card>

          {/* 右侧表详情 */}
          <Card
            title={selectedTable ? `表: ${selectedTable}` : '请选择表'}
            style={{ flex: 1 }}
            loading={isLoadingDetail}
            extra={selectedTable && (
              <Space>
                <Tooltip title="使用 AI 自动标注列的描述、敏感级别和语义标签">
                  <Button
                    icon={<RobotOutlined />}
                    loading={annotateMutation.isPending}
                    onClick={handleAIAnnotate}
                  >
                    AI 标注
                  </Button>
                </Tooltip>
                <Tooltip title="查看敏感字段分析报告">
                  <Button
                    icon={<SafetyOutlined />}
                    loading={sensitivityMutation.isPending}
                    onClick={handleViewSensitivityReport}
                  >
                    敏感报告
                  </Button>
                </Tooltip>
                <Tooltip title="AI 智能扫描敏感数据">
                  <Button
                    type="primary"
                    icon={<SafetyOutlined />}
                    onClick={() => setAiScanModalOpen(true)}
                  >
                    AI 扫描
                  </Button>
                </Tooltip>
              </Space>
            )}
          >
            {tableDetail?.data ? (
              <>
                <Descriptions column={2} bordered style={{ marginBottom: 16 }}>
                  <Descriptions.Item label="表名" span={2}>
                    {tableDetail.data.table_name}
                  </Descriptions.Item>
                  <Descriptions.Item label="数据库">
                    {tableDetail.data.database}
                  </Descriptions.Item>
                  <Descriptions.Item label="描述">
                    {tableDetail.data.description || '-'}
                  </Descriptions.Item>
                </Descriptions>

                {annotateMutation.isPending && (
                  <Alert
                    type="info"
                    showIcon
                    icon={<Spin size="small" />}
                    message="AI 正在分析表结构并生成标注..."
                    style={{ marginBottom: 16 }}
                  />
                )}

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                  <h3 style={{ margin: 0 }}>列信息</h3>
                </div>
                <Table
                  size="small"
                  dataSource={tableDetail.data.columns}
                  rowKey="name"
                  columns={tableColumns}
                  pagination={false}
                  scroll={{ x: 900 }}
                />

                {tableDetail.data.relations && tableDetail.data.relations.length > 0 && (
                  <>
                    <h3 style={{ marginTop: 16 }}>关系</h3>
                    <Table
                      size="small"
                      dataSource={tableDetail.data.relations}
                      rowKey={(r) => `${r.from_table}.${r.from_column}`}
                      pagination={false}
                      columns={[
                        { title: '类型', dataIndex: 'type', key: 'type' },
                        { title: '来源表', dataIndex: 'from_table', key: 'from_table' },
                        { title: '来源列', dataIndex: 'from_column', key: 'from_column' },
                        { title: '目标表', dataIndex: 'to_table', key: 'to_table' },
                        { title: '目标列', dataIndex: 'to_column', key: 'to_column' },
                      ]}
                    />
                  </>
                )}

                {tableDetail.data.sample_data && tableDetail.data.sample_data.length > 0 && (
                  <>
                    <h3 style={{ marginTop: 16 }}>示例数据</h3>
                    <Table
                      size="small"
                      dataSource={tableDetail.data.sample_data}
                      rowKey={(_r, i) => `sample-${i}`}
                      pagination={false}
                      columns={tableDetail.data.columns.map((col) => ({
                        title: col.name,
                        dataIndex: col.name,
                        key: col.name,
                        ellipsis: true,
                      }))}
                    />
                  </>
                )}
              </>
            ) : (
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  height: 400,
                  color: '#999',
                }}
              >
                {selectedTable ? '加载中...' : '请从左侧选择表'}
              </div>
            )}
          </Card>
        </div>
      ),
    },
    {
      key: 'search',
      label: '搜索',
      children: (
        <div style={{ padding: '16px 0' }}>
          <Space style={{ marginBottom: 16, width: '100%' }} direction="vertical">
            <Search
              placeholder="搜索表名或列名，例如：订单、客户、金额..."
              allowClear
              enterButton={<SearchOutlined />}
              size="large"
              loading={isSearching}
              onSearch={setSearchText}
              style={{ width: '100%' }}
            />
          </Space>

          {searchText && (
            <Table
              columns={searchColumns}
              dataSource={searchResults?.data?.results || []}
              rowKey={(r) => `${r.database}.${r.table}`}
              loading={isSearching}
              pagination={false}
              onRow={(record) => ({
                onClick: () => {
                  setSelectedDatabase(record.database);
                  setSelectedTable(record.table);
                },
                style: { cursor: 'pointer' },
              })}
            />
          )}
        </div>
      ),
    },
    {
      key: 'text2sql',
      label: 'Text-to-SQL',
      children: (
        <div style={{ padding: '16px 0' }}>
          <Space direction="vertical" style={{ width: '100%' }} size="large">
            <div>
              <h3>自然语言转 SQL</h3>
              <p style={{ color: '#666' }}>
                用自然语言描述你的查询需求，AI 会自动生成 SQL 语句
              </p>
            </div>

            <div>
              <div style={{ marginBottom: 8 }}>
                <strong>数据库：</strong>
                <span style={{ marginLeft: 8 }}>
                  {selectedDatabase || (
                    <span style={{ color: '#999' }}>(未选择，将使用默认数据库)</span>
                  )}
                </span>
              </div>
            </div>

            <div>
              <div style={{ marginBottom: 8 }}>自然语言描述：</div>
              <TextArea
                rows={4}
                placeholder="例如：查询最近一个月订单金额大于1000的订单数量"
                value={naturalLanguage}
                onChange={(e) => setNaturalLanguage(e.target.value)}
              />
            </div>

            <Button type="primary" size="large" onClick={handleText2Sql}>
              生成 SQL
            </Button>
          </Space>
        </div>
      ),
    },
  ];

  return (
    <div style={{ padding: '24px' }}>
      <Card title="元数据浏览">
        <Tabs items={tabItems} />
      </Card>

      {/* SQL 结果模态框 */}
      <Modal
        title="生成的 SQL"
        open={sqlModalOpen}
        onCancel={() => setSqlModalOpen(false)}
        footer={[
          <Button key="copy" icon={<CopyOutlined />} onClick={handleCopySql}>
            复制
          </Button>,
          <Button key="close" onClick={() => setSqlModalOpen(false)}>
            关闭
          </Button>,
        ]}
        width={700}
      >
        <pre
          style={{
            backgroundColor: '#f6f8fa',
            padding: 16,
            borderRadius: 6,
            overflow: 'auto',
            maxHeight: 400,
          }}
        >
          {generatedSql || '// SQL 生成中...'}
        </pre>
      </Modal>

      {/* 敏感字段报告模态框 */}
      <Modal
        title={
          <Space>
            <SafetyOutlined />
            <span>敏感字段分析报告</span>
          </Space>
        }
        open={annotationModalOpen}
        onCancel={() => setAnnotationModalOpen(false)}
        footer={[
          <Button key="close" onClick={() => setAnnotationModalOpen(false)}>
            关闭
          </Button>,
        ]}
        width={700}
      >
        {sensitivityReport && (
          <div>
            {/* 总体统计 */}
            <Descriptions column={2} bordered style={{ marginBottom: 16 }}>
              <Descriptions.Item label="总列数">
                {sensitivityReport.total_columns}
              </Descriptions.Item>
              <Descriptions.Item label="敏感列数">
                <Tag color={sensitivityReport.sensitive_columns > 0 ? 'orange' : 'green'}>
                  {sensitivityReport.sensitive_columns}
                </Tag>
              </Descriptions.Item>
            </Descriptions>

            {/* 按敏感级别分布 */}
            <h4>按敏感级别分布</h4>
            <div style={{ display: 'flex', gap: 16, marginBottom: 16 }}>
              {Object.entries(sensitivityReport.by_level).map(([level, count]) => (
                <div key={level} style={{ textAlign: 'center' }}>
                  <Progress
                    type="circle"
                    percent={Math.round((count / sensitivityReport.total_columns) * 100)}
                    size={60}
                    strokeColor={getSensitivityLevelColor(level)}
                  />
                  <div style={{ marginTop: 4 }}>
                    <Tag color={getSensitivityLevelColor(level)}>{level}</Tag>
                    <span style={{ marginLeft: 4 }}>{count}</span>
                  </div>
                </div>
              ))}
            </div>

            {/* 按敏感类型分布 */}
            <h4>按敏感类型分布</h4>
            <div style={{ marginBottom: 16 }}>
              {Object.entries(sensitivityReport.by_type).map(([type, columns]) => (
                columns.length > 0 && (
                  <div key={type} style={{ marginBottom: 8 }}>
                    <Tag color={getSensitivityTypeColor(type)} style={{ width: 80 }}>
                      {type.toUpperCase()}
                    </Tag>
                    <span style={{ marginLeft: 8 }}>
                      {columns.map((col) => (
                        <Tag key={col}>{col}</Tag>
                      ))}
                    </span>
                  </div>
                )
              ))}
              {Object.values(sensitivityReport.by_type).every((cols) => cols.length === 0) && (
                <Alert message="未发现敏感字段" type="success" showIcon />
              )}
            </div>

            {/* 高风险列 */}
            {sensitivityReport.high_risk_columns.length > 0 && (
              <>
                <h4>
                  <ExclamationCircleOutlined style={{ color: 'red', marginRight: 8 }} />
                  高风险字段
                </h4>
                <Alert
                  type="error"
                  message="以下字段包含高度敏感数据，需要特别保护"
                  style={{ marginBottom: 8 }}
                />
                <Table
                  size="small"
                  dataSource={sensitivityReport.high_risk_columns}
                  rowKey="column"
                  pagination={false}
                  columns={[
                    { title: '列名', dataIndex: 'column', key: 'column' },
                    {
                      title: '敏感类型',
                      dataIndex: 'type',
                      key: 'type',
                      render: (type: string) => (
                        <Tag color={getSensitivityTypeColor(type)}>{type}</Tag>
                      ),
                    },
                    {
                      title: '敏感级别',
                      dataIndex: 'level',
                      key: 'level',
                      render: (level: string) => (
                        <Tag color={getSensitivityLevelColor(level)}>{level}</Tag>
                      ),
                    },
                  ]}
                />
              </>
            )}
          </div>
        )}
      </Modal>

      {/* AI 敏感数据扫描模态框 */}
      <AISensitivityScanPanel
        datasetId={`${selectedDatabase}.${selectedTable}`}
        tableName={selectedTable}
        databaseName={selectedDatabase}
        columns={tableDetail?.data?.columns?.map((col: any) => ({
          name: col.name,
          type: col.type,
          description: col.description,
        })) || []}
        visible={aiScanModalOpen}
        onClose={() => setAiScanModalOpen(false)}
        onMaskingApply={() => queryClient.invalidateQueries({ queryKey: ['tableDetail', selectedDatabase, selectedTable] })}
      />
    </div>
  );
}

export default MetadataPage;
