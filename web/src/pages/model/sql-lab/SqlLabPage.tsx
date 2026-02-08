import { useState, useEffect, useRef } from 'react';
import {
  Card,
  Select,
  Button,
  Table,
  Space,
  Input,
  message,
  Drawer,
  Tag,
  Statistic,
  Tooltip,
  Popconfirm,
  Splitter,
  Modal,
  Form,
} from 'antd';
import {
  PlayCircleOutlined,
  SaveOutlined,
  HistoryOutlined,
  FileTextOutlined,
  StopOutlined,
  DownloadOutlined,
  FormatPainterOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  PlusOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import CodeMirror from '@uiw/react-codemirror';
import { sql } from '@codemirror/lang-sql';
import { vscodeDarkInit } from '@uiw/codemirror-theme-vscode';
import dayjs from 'dayjs';
import model from '@/services/model';
import type {
  QueryResult,
  QueryHistoryItem,
  SavedQuery,
} from '@/services/model';

const { Option } = Select;

function SqlLabPage() {
  const queryClient = useQueryClient();
  const editorRef = useRef<HTMLDivElement>(null);

  const [selectedDatabase, setSelectedDatabase] = useState<string>('');
  const [sqlQuery, setSqlQuery] = useState<string>('');
  const [queryResult, setQueryResult] = useState<QueryResult | null>(null);
  const [isQueryRunning, setIsQueryRunning] = useState(false);
  const [currentQueryId, setCurrentQueryId] = useState<string | null>(null);
  const [isHistoryDrawerOpen, setIsHistoryDrawerOpen] = useState(false);
  const [isSavedDrawerOpen, setIsSavedDrawerOpen] = useState(false);
  const [selectedTables, setSelectedTables] = useState<string[]>([]);
  const [tableSchema, setTableSchema] = useState<Record<string, Array<{ name: string; type: string }>>>({});
  const [isSaveModalOpen, setIsSaveModalOpen] = useState(false);
  const [saveQueryName, setSaveQueryName] = useState('');

  // 获取数据库连接列表
  const { data: connectionsData, isLoading: isLoadingConnections } = useQuery({
    queryKey: ['sqlLabConnections'],
    queryFn: model.getSqlLabConnections,
  });

  // 获取查询历史
  const { data: historyData } = useQuery({
    queryKey: ['queryHistory', selectedDatabase],
    queryFn: () => model.getQueryHistory({ database_id: selectedDatabase, limit: 50 }),
    enabled: isHistoryDrawerOpen,
  });

  // 获取保存的查询
  const { data: savedQueriesData } = useQuery({
    queryKey: ['savedQueries', selectedDatabase],
    queryFn: () => model.getSavedQueries({ database_id: selectedDatabase }),
    enabled: isSavedDrawerOpen,
  });

  // 执行查询
  const executeMutation = useMutation({
    mutationFn: model.executeSqlQuery,
    onSuccess: (data) => {
      setQueryResult(data.data);
      setIsQueryRunning(false);
      setCurrentQueryId(null);

      if (data.data.status === 'failed') {
        message.error(`查询失败: ${data.data.error_message}`);
      } else {
        message.success(`查询成功，返回 ${data.data.row_count} 行`);
      }
      queryClient.invalidateQueries({ queryKey: ['queryHistory'] });
    },
    onError: () => {
      setIsQueryRunning(false);
      setCurrentQueryId(null);
      message.error('查询执行失败');
    },
  });

  // 保存查询
  const saveQueryMutation = useMutation({
    mutationFn: model.saveQuery,
    onSuccess: () => {
      message.success('查询保存成功');
      setIsSaveModalOpen(false);
      setSaveQueryName('');
      queryClient.invalidateQueries({ queryKey: ['savedQueries'] });
    },
    onError: () => {
      message.error('保存失败');
    },
  });

  // 删除保存的查询
  const deleteSavedQueryMutation = useMutation({
    mutationFn: model.deleteSavedQuery,
    onSuccess: () => {
      message.success('删除成功');
      queryClient.invalidateQueries({ queryKey: ['savedQueries'] });
    },
  });

  // 获取表列表
  useEffect(() => {
    if (selectedDatabase) {
      model.getSqlLabTables(selectedDatabase).then((res) => {
        setSelectedTables(res.data.tables || []);
      });
    }
  }, [selectedDatabase]);

  // 获取表结构
  const loadTableSchema = async (tableName: string) => {
    if (selectedDatabase && !tableSchema[tableName]) {
      const res = await model.getSqlLabTableSchema(selectedDatabase, tableName);
      setTableSchema((prev) => ({ ...prev, [tableName]: res.data.columns }));
    }
  };

  // 格式化 SQL
  const handleFormatSql = async () => {
    try {
      const res = await model.formatSql(sqlQuery);
      setSqlQuery(res.data.formatted_sql);
      message.success('SQL 格式化成功');
    } catch {
      message.error('格式化失败');
    }
  };

  // 执行查询
  const handleExecuteQuery = () => {
    if (!selectedDatabase) {
      message.warning('请先选择数据库');
      return;
    }
    if (!sqlQuery.trim()) {
      message.warning('请输入 SQL 查询');
      return;
    }

    setIsQueryRunning(true);
    setQueryResult(null);

    executeMutation.mutate({
      database_id: selectedDatabase,
      sql: sqlQuery,
      limit: 1000,
    });
  };

  // 停止查询
  const handleStopQuery = async () => {
    if (currentQueryId) {
      await model.cancelQuery(currentQueryId);
      setIsQueryRunning(false);
      setCurrentQueryId(null);
      message.info('查询已取消');
    }
  };

  // 导出结果
  const handleExportResult = async (format: 'csv' | 'json' | 'excel') => {
    if (!queryResult?.query_id) return;
    try {
      const res = await model.exportQueryResult(queryResult.query_id, format);
      window.open(res.data.download_url, '_blank');
      message.success('导出成功');
    } catch {
      message.error('导出失败');
    }
  };

  // 加载保存的查询
  const handleLoadSavedQuery = (query: SavedQuery) => {
    setSqlQuery(query.sql);
    setIsSavedDrawerOpen(false);
  };

  // 加载历史查询
  const handleLoadHistoryQuery = (item: QueryHistoryItem) => {
    setSqlQuery(item.sql);
    setIsHistoryDrawerOpen(false);
  };

  // 保存查询
  const handleSaveQuery = () => {
    if (!saveQueryName.trim()) {
      message.warning('请输入查询名称');
      return;
    }
    if (!sqlQuery.trim()) {
      message.warning('没有可保存的查询');
      return;
    }
    saveQueryMutation.mutate({
      name: saveQueryName,
      database_id: selectedDatabase,
      sql: sqlQuery,
    });
  };

  const resultColumns = queryResult?.columns.map((col) => ({
    title: col,
    dataIndex: col,
    key: col,
    width: 150,
    ellipsis: true,
    render: (value: unknown) => (value === null ? <Tag color="default">NULL</Tag> : String(value)),
  })) || [];

  const historyColumns = [
    { title: 'SQL', dataIndex: 'sql', key: 'sql', ellipsis: true },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 80,
      render: (status: string) => (
        <Tag
          color={status === 'completed' ? 'green' : status === 'failed' ? 'red' : 'blue'}
          icon={status === 'completed' ? <CheckCircleOutlined /> : status === 'failed' ? <CloseCircleOutlined /> : undefined}
        >
          {status}
        </Tag>
      ),
    },
    {
      title: '耗时',
      dataIndex: 'duration_ms',
      key: 'duration_ms',
      width: 80,
      render: (ms?: number) => (ms ? `${ms}ms` : '-'),
    },
    {
      title: '行数',
      dataIndex: 'row_count',
      key: 'row_count',
      width: 80,
      render: (count?: number) => (count !== undefined ? count.toLocaleString() : '-'),
    },
    {
      title: '执行时间',
      dataIndex: 'executed_at',
      key: 'executed_at',
      width: 150,
      render: (date: string) => dayjs(date).format('MM-DD HH:mm:ss'),
    },
    {
      title: '操作',
      key: 'actions',
      width: 60,
      render: (_: unknown, record: QueryHistoryItem) => (
        <Button
          type="link"
          size="small"
          onClick={() => handleLoadHistoryQuery(record)}
        >
          加载
        </Button>
      ),
    },
  ];

  const savedQueryColumns = [
    { title: '名称', dataIndex: 'name', key: 'name', ellipsis: true },
    { title: '描述', dataIndex: 'description', key: 'description', ellipsis: true, render: (desc: string) => desc || '-' },
    {
      title: '标签',
      dataIndex: 'tags',
      key: 'tags',
      render: (tags?: string[]) => tags?.map((t) => <Tag key={t}>{t}</Tag>) || '-',
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 150,
      render: (date: string) => dayjs(date).format('YYYY-MM-DD HH:mm'),
    },
    {
      title: '操作',
      key: 'actions',
      width: 120,
      render: (_: unknown, record: SavedQuery) => (
        <Space>
          <Button type="link" size="small" onClick={() => handleLoadSavedQuery(record)}>
            加载
          </Button>
          <Popconfirm
            title="确定删除？"
            onConfirm={() => deleteSavedQueryMutation.mutate(record.saved_query_id)}
          >
            <Button type="link" size="small" danger>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const connections = connectionsData?.data?.connections || [];
  const defaultConnection = connections.find((c) => c.is_default);

  useEffect(() => {
    if (defaultConnection && !selectedDatabase) {
      setSelectedDatabase(defaultConnection.id);
    }
  }, [defaultConnection, selectedDatabase]);

  return (
    <div style={{ height: 'calc(100vh - 64px)', display: 'flex', flexDirection: 'column' }}>
      <div style={{ padding: '16px 24px', background: '#fff', borderBottom: '1px solid #f0f0f0' }}>
        <Space size="middle" style={{ width: '100%' }}>
          <Select
            placeholder="选择数据库"
            style={{ width: 200 }}
            value={selectedDatabase}
            onChange={setSelectedDatabase}
            loading={isLoadingConnections}
          >
            {connections.map((conn) => (
              <Option key={conn.id} value={conn.id}>
                <Space>
                  <Tag color={
                    conn.type === 'mysql' ? 'blue' :
                    conn.type === 'postgresql' ? 'cyan' :
                    conn.type === 'clickhouse' ? 'purple' :
                    'green'
                  }>
                    {conn.type}
                  </Tag>
                  {conn.name}
                </Space>
              </Option>
            ))}
          </Select>

          {isQueryRunning ? (
            <Button danger icon={<StopOutlined />} onClick={handleStopQuery}>
              停止查询
            </Button>
          ) : (
            <Button type="primary" icon={<PlayCircleOutlined />} onClick={handleExecuteQuery}>
              运行 (Ctrl+Enter)
            </Button>
          )}

          <Tooltip title="格式化 SQL">
            <Button icon={<FormatPainterOutlined />} onClick={handleFormatSql}>
              格式化
            </Button>
          </Tooltip>

          <Button icon={<SaveOutlined />} onClick={() => setIsSaveModalOpen(true)}>
            保存
          </Button>

          <Button icon={<HistoryOutlined />} onClick={() => setIsHistoryDrawerOpen(true)}>
            历史
          </Button>

          <Button icon={<FileTextOutlined />} onClick={() => setIsSavedDrawerOpen(true)}>
            已保存
          </Button>

          {queryResult && queryResult.status === 'completed' && (
            <Button
              icon={<DownloadOutlined />}
              onClick={() => handleExportResult('csv')}
            >
              导出
            </Button>
          )}

          <div style={{ flex: 1 }} />

          {queryResult && queryResult.status === 'completed' && (
            <Space>
              <Statistic
                title="执行时间"
                value={queryResult.execution_time_ms}
                suffix="ms"
                valueStyle={{ fontSize: 14 }}
              />
              <Statistic
                title="返回行数"
                value={queryResult.row_count}
                valueStyle={{ fontSize: 14 }}
              />
            </Space>
          )}
        </Space>
      </div>

      <Splitter style={{ flex: 1 }}>
        <Splitter.Panel size="25%" min="20%" max="40%">
          <Card
            title="数据表"
            size="small"
            styles={{ body: { padding: 8, height: 'calc(100% - 40px)', overflow: 'auto' }}
            style={{ height: '100%' }}
          >
            {selectedTables.map((table) => (
              <div key={table}>
                <div
                  style={{
                    padding: '4px 8px',
                    cursor: 'pointer',
                    borderRadius: 4,
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                  }}
                  onMouseEnter={() => loadTableSchema(table)}
                >
                  <span>{table}</span>
                  <PlusOutlined style={{ fontSize: 10, color: '#999' }} />
                </div>
                {tableSchema[table] && (
                  <div style={{ marginLeft: 16, fontSize: 12, color: '#666' }}>
                    {tableSchema[table].map((col) => (
                      <div key={col.name} style={{ padding: '2px 0' }}>
                        <span style={{ color: '#1890ff' }}>{col.name}</span>
                        <span style={{ color: '#999', marginLeft: 8 }}>{col.type}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </Card>
        </Splitter.Panel>

        <Splitter.Panel>
          <div style={{ height: '50%', borderBottom: '1px solid #f0f0f0' }}>
            <div style={{ padding: '8px 16px', background: '#f5f5f5', borderBottom: '1px solid #f0f0f0' }}>
              <span style={{ fontWeight: 500 }}>SQL 编辑器</span>
            </div>
            <div style={{ height: 'calc(100% - 37px)' }} ref={editorRef}>
              <CodeMirror
                value={sqlQuery}
                height="100%"
                extensions={[sql(), vscodeDarkInit()]}
                onChange={(value) => setSqlQuery(value)}
                basicSetup={{
                  lineNumbers: true,
                  highlightActiveLineGutter: true,
                  highlightSpecialChars: true,
                  foldGutter: true,
                  drawSelection: true,
                  dropCursor: true,
                  allowMultipleSelections: true,
                  indentOnInput: true,
                  bracketMatching: true,
                  closeBrackets: true,
                  autocompletion: true,
                  rectangularSelection: true,
                  crosshairCursor: true,
                  highlightActiveLine: true,
                  highlightSelectionMatches: true,
                  closeBracketsKeymap: true,
                  searchKeymap: true,
                  foldKeymap: true,
                  completionKeymap: true,
                  lintKeymap: true,
                }}
              />
            </div>
          </div>

          <div style={{ height: '50%', overflow: 'auto' }}>
            <div style={{ padding: '8px 16px', background: '#f5f5f5', borderBottom: '1px solid #f0f0f0' }}>
              <span style={{ fontWeight: 500 }}>查询结果</span>
            </div>
            <div style={{ padding: 16 }}>
              {queryResult ? (
                queryResult.status === 'completed' ? (
                  <Table
                    columns={resultColumns}
                    dataSource={queryResult.rows.map((row, i) => ({ ...row, _key: i }))}
                    rowKey="_key"
                    size="small"
                    scroll={{ x: 'max-content', y: 'calc(50vh - 150px)' }}
                    pagination={{
                      pageSize: 50,
                      showSizeChanger: true,
                      showTotal: (total) => `共 ${total} 条`,
                    }}
                  />
                ) : (
                  <div style={{ textAlign: 'center', padding: 40, color: '#ff4d4f' }}>
                    <CloseCircleOutlined style={{ fontSize: 48, marginBottom: 16 }} />
                    <div>{queryResult.error_message || '查询失败'}</div>
                  </div>
                )
              ) : (
                <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>
                  输入 SQL 查询并点击运行按钮执行
                </div>
              )}
            </div>
          </div>
        </Splitter.Panel>
      </Splitter>

      {/* 历史查询抽屉 */}
      <Drawer
        title="查询历史"
        open={isHistoryDrawerOpen}
        onClose={() => setIsHistoryDrawerOpen(false)}
        width={600}
      >
        <Table
          columns={historyColumns}
          dataSource={historyData?.data?.history || []}
          rowKey="query_id"
          size="small"
          pagination={{ pageSize: 20 }}
        />
      </Drawer>

      {/* 已保存查询抽屉 */}
      <Drawer
        title="已保存的查询"
        open={isSavedDrawerOpen}
        onClose={() => setIsSavedDrawerOpen(false)}
        width={600}
      >
        <Table
          columns={savedQueryColumns}
          dataSource={savedQueriesData?.data?.queries || []}
          rowKey="saved_query_id"
          size="small"
          pagination={{ pageSize: 20 }}
        />
      </Drawer>

      {/* 保存查询模态框 */}
      <Modal
        title="保存查询"
        open={isSaveModalOpen}
        onOk={handleSaveQuery}
        onCancel={() => {
          setIsSaveModalOpen(false);
          setSaveQueryName('');
        }}
        confirmLoading={saveQueryMutation.isPending}
      >
        <Form layout="vertical">
          <Form.Item label="查询名称" required>
            <Input
              value={saveQueryName}
              onChange={(e) => setSaveQueryName(e.target.value)}
              placeholder="请输入查询名称"
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}

export default SqlLabPage;
