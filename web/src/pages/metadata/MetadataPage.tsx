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
} from 'antd';
import {
  DatabaseOutlined,
  TableOutlined,
  SearchOutlined,
  CopyOutlined,
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import type { DataNode } from 'antd/es/tree';
import alldata from '@/services/alldata';
import type { ColumnInfo } from '@/services/alldata';

const { Search } = Input;
const { TextArea } = Input;

function MetadataPage() {
  const [selectedDatabase, setSelectedDatabase] = useState<string>('');
  const [selectedTable, setSelectedTable] = useState<string>('');
  const [searchText, setSearchText] = useState('');

  const [sqlModalOpen, setSqlModalOpen] = useState(false);
  const [generatedSql, setGeneratedSql] = useState('');
  const [naturalLanguage, setNaturalLanguage] = useState('');

  // 获取数据库列表
  const { data: databasesData } = useQuery({
    queryKey: ['databases'],
    queryFn: alldata.getDatabases,
  });

  // 获取表列表
  const { data: tablesData, isLoading: isLoadingTables } = useQuery({
    queryKey: ['tables', selectedDatabase],
    queryFn: () => alldata.getTables(selectedDatabase),
    enabled: !!selectedDatabase,
  });

  // 获取表详情
  const { data: tableDetail, isLoading: isLoadingDetail } = useQuery({
    queryKey: ['tableDetail', selectedDatabase, selectedTable],
    queryFn: () => alldata.getTableDetail(selectedDatabase, selectedTable),
    enabled: !!(selectedDatabase && selectedTable),
  });

  // 智能表搜索
  const { data: searchResults, isLoading: isSearching } = useQuery({
    queryKey: ['tableSearch', searchText],
    queryFn: () => alldata.searchTables(searchText),
    enabled: searchText.length > 1,
  });

  // Text-to-SQL
  const handleText2Sql = async () => {
    if (!naturalLanguage.trim()) {
      message.warning('请输入自然语言描述');
      return;
    }

    try {
      // 调用 Bisheng Text2SQL API
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
      render: (desc?: string) => desc || '-',
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

                <h3>列信息</h3>
                <Table
                  size="small"
                  dataSource={tableDetail.data.columns}
                  rowKey="name"
                  columns={tableColumns}
                  pagination={false}
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
                      rowKey={(r, i) => `sample-${i}`}
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
    </div>
  );
}

export default MetadataPage;
