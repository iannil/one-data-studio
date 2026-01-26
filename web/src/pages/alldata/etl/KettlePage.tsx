import React, { useState, useEffect, useCallback } from 'react';
import {
  Card,
  Button,
  Tabs,
  Form,
  Input,
  Select,
  Table,
  Space,
  message,
  Spin,
  Typography,
  Tag,
  Row,
  Col,
  Divider,
  Alert,
  InputNumber,
  Empty,
  Tooltip,
  Modal,
} from 'antd';
import {
  SettingOutlined,
  FileOutlined,
  DatabaseOutlined,
  DownloadOutlined,
  CopyOutlined,
  PlusOutlined,
  DeleteOutlined,
  CodeOutlined,
  SyncOutlined,
  InfoCircleOutlined,
  RocketOutlined,
  LinkOutlined,
} from '@ant-design/icons';
import {
  generateKettleTransformation,
  generateKettleJob,
  generateKettleFromETLTask,
  generateKettleFromMetadata,
  getKettleTypes,
  downloadKettleConfig,
  getETLTasks,
  getDatabases,
  getTables,
  KettleGenerationResult,
  KettleTypesConfig,
  KettleConnectionConfig,
  KettleColumnConfig,
  ETLTask,
  Database,
  TableInfo,
} from '../../../services/alldata';

const { Title, Text, Paragraph } = Typography;
const { TabPane } = Tabs;
const { TextArea } = Input;

const KettlePage: React.FC = () => {
  const [activeTab, setActiveTab] = useState('manual');
  const [loading, setLoading] = useState(false);
  const [typesConfig, setTypesConfig] = useState<KettleTypesConfig | null>(null);
  const [generatedResult, setGeneratedResult] = useState<KettleGenerationResult | null>(null);
  const [etlTasks, setEtlTasks] = useState<ETLTask[]>([]);
  const [databases, setDatabases] = useState<Database[]>([]);
  const [sourceTables, setSourceTables] = useState<TableInfo[]>([]);
  const [targetTables, setTargetTables] = useState<TableInfo[]>([]);
  const [selectedSourceDb, setSelectedSourceDb] = useState<string>('');
  const [selectedTargetDb, setSelectedTargetDb] = useState<string>('');
  const [xmlPreviewVisible, setXmlPreviewVisible] = useState(false);

  // Forms
  const [manualForm] = Form.useForm();
  const [etlTaskForm] = Form.useForm();
  const [metadataForm] = Form.useForm();
  const [jobForm] = Form.useForm();

  // 源表和目标表列配置
  const [sourceColumns, setSourceColumns] = useState<KettleColumnConfig[]>([
    { column_name: '', data_type: 'VARCHAR' },
  ]);
  const [targetColumns, setTargetColumns] = useState<KettleColumnConfig[]>([]);
  const [transformationList, setTransformationList] = useState<string[]>(['']);

  // 加载类型配置
  const loadTypesConfig = useCallback(async () => {
    try {
      const response = await getKettleTypes();
      if (response.code === 0) {
        setTypesConfig(response.data);
      }
    } catch (error) {
      console.error('Failed to load Kettle types:', error);
    }
  }, []);

  // 加载 ETL 任务列表
  const loadETLTasks = useCallback(async () => {
    try {
      const response = await getETLTasks({ page: 1, page_size: 100 });
      if (response.code === 0) {
        setEtlTasks(response.data.tasks || []);
      }
    } catch (error) {
      console.error('Failed to load ETL tasks:', error);
    }
  }, []);

  // 加载数据库列表
  const loadDatabases = useCallback(async () => {
    try {
      const response = await getDatabases();
      if (response.code === 0) {
        setDatabases(response.data.databases || []);
      }
    } catch (error) {
      console.error('Failed to load databases:', error);
    }
  }, []);

  // 加载源表列表
  const loadSourceTables = useCallback(async (database: string) => {
    if (!database) {
      setSourceTables([]);
      return;
    }
    try {
      const response = await getTables(database);
      if (response.code === 0) {
        setSourceTables(response.data.tables || []);
      }
    } catch (error) {
      console.error('Failed to load source tables:', error);
    }
  }, []);

  // 加载目标表列表
  const loadTargetTables = useCallback(async (database: string) => {
    if (!database) {
      setTargetTables([]);
      return;
    }
    try {
      const response = await getTables(database);
      if (response.code === 0) {
        setTargetTables(response.data.tables || []);
      }
    } catch (error) {
      console.error('Failed to load target tables:', error);
    }
  }, []);

  useEffect(() => {
    loadTypesConfig();
    loadETLTasks();
    loadDatabases();
  }, [loadTypesConfig, loadETLTasks, loadDatabases]);

  // 当源数据库变化时加载表
  useEffect(() => {
    loadSourceTables(selectedSourceDb);
  }, [selectedSourceDb, loadSourceTables]);

  // 当目标数据库变化时加载表
  useEffect(() => {
    loadTargetTables(selectedTargetDb);
  }, [selectedTargetDb, loadTargetTables]);

  // 手动配置生成
  const handleManualGenerate = async (values: any) => {
    setLoading(true);
    try {
      const sourceConnection: KettleConnectionConfig = {
        type: values.source_type,
        host: values.source_host,
        port: values.source_port,
        database: values.source_database,
        username: values.source_username,
        password: values.source_password,
        schema: values.source_schema,
      };

      const targetConnection: KettleConnectionConfig = {
        type: values.target_type,
        host: values.target_host,
        port: values.target_port,
        database: values.target_database,
        username: values.target_username,
        password: values.target_password,
        schema: values.target_schema,
      };

      const response = await generateKettleTransformation({
        source: {
          connection: sourceConnection,
          table: values.source_table,
          schema: values.source_schema,
          columns: sourceColumns.filter(c => c.column_name),
        },
        target: {
          connection: targetConnection,
          table: values.target_table,
          schema: values.target_schema,
          columns: targetColumns.filter(c => c.column_name),
        },
        options: {
          name: values.transformation_name,
          write_mode: values.write_mode,
          batch_size: values.batch_size,
          commit_size: values.commit_size,
          incremental_field: values.incremental_field,
          filter_condition: values.filter_condition,
          primary_keys: values.primary_keys?.split(',').map((k: string) => k.trim()),
        },
      });

      if (response.code === 0) {
        setGeneratedResult(response.data);
        message.success('Kettle 转换配置生成成功');
      } else {
        message.error(response.message || '生成失败');
      }
    } catch (error) {
      message.error('生成 Kettle 配置失败');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  // 从 ETL 任务生成
  const handleETLTaskGenerate = async (values: any) => {
    setLoading(true);
    try {
      const response = await generateKettleFromETLTask(values.task_id, {
        name: values.name,
        write_mode: values.write_mode,
        batch_size: values.batch_size,
      });

      if (response.code === 0) {
        setGeneratedResult(response.data);
        message.success('从 ETL 任务生成 Kettle 配置成功');
      } else {
        message.error(response.message || '生成失败');
      }
    } catch (error) {
      message.error('生成失败');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  // 从元数据生成
  const handleMetadataGenerate = async (values: any) => {
    setLoading(true);
    try {
      // 构建表标识符：database.table 格式
      const sourceTableId = `${selectedSourceDb}.${values.source_table}`;
      const targetTableId = `${selectedTargetDb}.${values.target_table}`;

      const response = await generateKettleFromMetadata({
        source_table_id: sourceTableId,
        target_table_id: targetTableId,
        options: {
          name: values.name,
          write_mode: values.write_mode,
          batch_size: values.batch_size,
        },
      });

      if (response.code === 0) {
        setGeneratedResult(response.data);
        message.success('从元数据生成 Kettle 配置成功');
      } else {
        message.error(response.message || '生成失败');
      }
    } catch (error) {
      message.error('生成失败');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  // 生成作业配置
  const handleJobGenerate = async (values: any) => {
    setLoading(true);
    try {
      const response = await generateKettleJob({
        name: values.name,
        description: values.description,
        transformations: transformationList.filter(t => t.trim()),
        sequential: values.sequential !== false,
      });

      if (response.code === 0) {
        setGeneratedResult(response.data);
        message.success('Kettle 作业配置生成成功');
      } else {
        message.error(response.message || '生成失败');
      }
    } catch (error) {
      message.error('生成失败');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  // 复制配置内容
  const handleCopyContent = () => {
    if (generatedResult?.content) {
      navigator.clipboard.writeText(generatedResult.content);
      message.success('配置内容已复制到剪贴板');
    }
  };

  // 下载配置文件
  const handleDownload = () => {
    if (generatedResult) {
      downloadKettleConfig(
        generatedResult.content,
        `${generatedResult.name}.${generatedResult.format}`,
        generatedResult.format
      );
      message.success('配置文件下载成功');
    }
  };

  // 添加源列
  const handleAddSourceColumn = () => {
    setSourceColumns([...sourceColumns, { column_name: '', data_type: 'VARCHAR' }]);
  };

  // 删除源列
  const handleRemoveSourceColumn = (index: number) => {
    setSourceColumns(sourceColumns.filter((_, i) => i !== index));
  };

  // 更新源列
  const handleUpdateSourceColumn = (index: number, field: keyof KettleColumnConfig, value: string) => {
    const newColumns = [...sourceColumns];
    newColumns[index] = { ...newColumns[index], [field]: value };
    setSourceColumns(newColumns);
  };

  // 添加转换路径
  const handleAddTransformation = () => {
    setTransformationList([...transformationList, '']);
  };

  // 删除转换路径
  const handleRemoveTransformation = (index: number) => {
    setTransformationList(transformationList.filter((_, i) => i !== index));
  };

  // 更新转换路径
  const handleUpdateTransformation = (index: number, value: string) => {
    const newList = [...transformationList];
    newList[index] = value;
    setTransformationList(newList);
  };

  // 渲染连接配置表单项
  const renderConnectionFields = (prefix: string, label: string) => (
    <>
      <Divider orientation="left">{label}连接配置</Divider>
      <Row gutter={16}>
        <Col span={8}>
          <Form.Item name={`${prefix}_type`} label="数据源类型" rules={[{ required: true }]}>
            <Select placeholder="选择数据源类型">
              {typesConfig?.source_types.map(t => (
                <Select.Option key={t.value} value={t.value}>
                  {t.label}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item name={`${prefix}_host`} label="主机地址" rules={[{ required: true }]}>
            <Input placeholder="localhost" />
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item name={`${prefix}_port`} label="端口">
            <InputNumber style={{ width: '100%' }} placeholder="3306" />
          </Form.Item>
        </Col>
      </Row>
      <Row gutter={16}>
        <Col span={8}>
          <Form.Item name={`${prefix}_database`} label="数据库名" rules={[{ required: true }]}>
            <Input placeholder="database" />
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item name={`${prefix}_username`} label="用户名">
            <Input placeholder="username" />
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item name={`${prefix}_password`} label="密码">
            <Input.Password placeholder="password" />
          </Form.Item>
        </Col>
      </Row>
      <Row gutter={16}>
        <Col span={8}>
          <Form.Item name={`${prefix}_schema`} label="Schema">
            <Input placeholder="public" />
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item name={`${prefix}_table`} label="表名" rules={[{ required: true }]}>
            <Input placeholder="table_name" />
          </Form.Item>
        </Col>
      </Row>
    </>
  );

  // 渲染列配置表格
  const renderColumnsTable = () => (
    <div style={{ marginBottom: 16 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
        <Text strong>源表列配置</Text>
        <Button type="dashed" size="small" icon={<PlusOutlined />} onClick={handleAddSourceColumn}>
          添加列
        </Button>
      </div>
      <Table
        dataSource={sourceColumns.map((col, index) => ({ ...col, key: index }))}
        columns={[
          {
            title: '列名',
            dataIndex: 'column_name',
            key: 'column_name',
            render: (_, record, index) => (
              <Input
                value={record.column_name}
                onChange={e => handleUpdateSourceColumn(index, 'column_name', e.target.value)}
                placeholder="column_name"
              />
            ),
          },
          {
            title: '数据类型',
            dataIndex: 'data_type',
            key: 'data_type',
            width: 150,
            render: (_, record, index) => (
              <Select
                value={record.data_type}
                onChange={value => handleUpdateSourceColumn(index, 'data_type', value)}
                style={{ width: '100%' }}
              >
                {typesConfig?.data_types.map(t => (
                  <Select.Option key={t.value} value={t.value}>
                    {t.label}
                  </Select.Option>
                ))}
              </Select>
            ),
          },
          {
            title: '操作',
            key: 'action',
            width: 60,
            render: (_, __, index) => (
              <Button
                type="text"
                danger
                size="small"
                icon={<DeleteOutlined />}
                onClick={() => handleRemoveSourceColumn(index)}
                disabled={sourceColumns.length <= 1}
              />
            ),
          },
        ]}
        pagination={false}
        size="small"
      />
    </div>
  );

  // 渲染生成结果
  const renderResult = () => {
    if (!generatedResult) {
      return (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description='配置表单信息并点击"生成配置"查看结果'
        />
      );
    }

    return (
      <div>
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={6}>
            <Card size="small">
              <Text type="secondary">配置名称</Text>
              <div>
                <Text strong>{generatedResult.name}</Text>
              </div>
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small">
              <Text type="secondary">配置类型</Text>
              <div>
                <Tag color={generatedResult.type === 'transformation' ? 'blue' : 'green'}>
                  {generatedResult.type === 'transformation' ? '转换 (.ktr)' : '作业 (.kjb)'}
                </Tag>
              </div>
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small">
              <Text type="secondary">字段数量</Text>
              <div>
                <Text strong>{generatedResult.column_count || generatedResult.transformation_count || '-'}</Text>
              </div>
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small">
              <Text type="secondary">配置大小</Text>
              <div>
                <Text strong>{(generatedResult.content.length / 1024).toFixed(2)} KB</Text>
              </div>
            </Card>
          </Col>
        </Row>

        {generatedResult.source_table && (
          <Alert
            message={
              <Space>
                <DatabaseOutlined />
                <Text>
                  数据流向: <Tag>{generatedResult.source_table}</Tag>
                  <span style={{ margin: '0 8px' }}>→</span>
                  <Tag color="green">{generatedResult.target_table}</Tag>
                </Text>
              </Space>
            }
            type="info"
            style={{ marginBottom: 16 }}
          />
        )}

        <Divider orientation="left">配置预览</Divider>
        <div
          style={{
            maxHeight: 300,
            overflow: 'auto',
            backgroundColor: '#f5f5f5',
            padding: 12,
            borderRadius: 4,
            fontFamily: 'monospace',
            fontSize: 12,
          }}
        >
          <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
            {generatedResult.content.substring(0, 2000)}
            {generatedResult.content.length > 2000 && '\n... (点击"查看完整配置"查看全部)'}
          </pre>
        </div>

        <div style={{ marginTop: 16 }}>
          <Space>
            <Button icon={<CopyOutlined />} onClick={handleCopyContent}>
              复制配置
            </Button>
            <Button type="primary" icon={<DownloadOutlined />} onClick={handleDownload}>
              下载 {generatedResult.format.toUpperCase()} 文件
            </Button>
            <Button icon={<CodeOutlined />} onClick={() => setXmlPreviewVisible(true)}>
              查看完整配置
            </Button>
          </Space>
        </div>
      </div>
    );
  };

  return (
    <div style={{ padding: 24 }}>
      <Title level={4}>
        <SettingOutlined /> Kettle 配置生成器
      </Title>
      <Paragraph type="secondary">
        基于元数据自动生成 Pentaho Kettle ETL 配置文件（.ktr 转换 / .kjb 作业）
      </Paragraph>

      <Row gutter={24}>
        {/* 左侧：配置表单 */}
        <Col span={12}>
          <Card>
            <Tabs activeKey={activeTab} onChange={setActiveTab}>
              {/* 手动配置 */}
              <TabPane
                tab={
                  <span>
                    <SettingOutlined /> 手动配置
                  </span>
                }
                key="manual"
              >
                <Form
                  form={manualForm}
                  layout="vertical"
                  onFinish={handleManualGenerate}
                  initialValues={{
                    write_mode: 'insert',
                    batch_size: 1000,
                    commit_size: 1000,
                  }}
                >
                  <Form.Item name="transformation_name" label="转换名称">
                    <Input placeholder="my_transformation" />
                  </Form.Item>

                  {renderConnectionFields('source', '源')}
                  {renderColumnsTable()}
                  {renderConnectionFields('target', '目标')}

                  <Divider orientation="left">转换选项</Divider>
                  <Row gutter={16}>
                    <Col span={8}>
                      <Form.Item name="write_mode" label="写入模式">
                        <Select>
                          {typesConfig?.write_modes.map(m => (
                            <Select.Option key={m.value} value={m.value}>
                              {m.label}
                            </Select.Option>
                          ))}
                        </Select>
                      </Form.Item>
                    </Col>
                    <Col span={8}>
                      <Form.Item name="batch_size" label="批次大小">
                        <InputNumber style={{ width: '100%' }} min={1} />
                      </Form.Item>
                    </Col>
                    <Col span={8}>
                      <Form.Item name="commit_size" label="提交大小">
                        <InputNumber style={{ width: '100%' }} min={1} />
                      </Form.Item>
                    </Col>
                  </Row>
                  <Row gutter={16}>
                    <Col span={12}>
                      <Form.Item
                        name="incremental_field"
                        label={
                          <span>
                            增量字段{' '}
                            <Tooltip title="用于增量同步的时间戳或自增 ID 字段">
                              <InfoCircleOutlined />
                            </Tooltip>
                          </span>
                        }
                      >
                        <Input placeholder="updated_at" />
                      </Form.Item>
                    </Col>
                    <Col span={12}>
                      <Form.Item name="primary_keys" label="主键字段（逗号分隔）">
                        <Input placeholder="id, code" />
                      </Form.Item>
                    </Col>
                  </Row>
                  <Form.Item name="filter_condition" label="过滤条件">
                    <Input placeholder="status = 'active'" />
                  </Form.Item>

                  <Button type="primary" htmlType="submit" loading={loading} icon={<RocketOutlined />} block>
                    生成配置
                  </Button>
                </Form>
              </TabPane>

              {/* 从 ETL 任务生成 */}
              <TabPane
                tab={
                  <span>
                    <SyncOutlined /> 从 ETL 任务
                  </span>
                }
                key="etl-task"
              >
                <Alert
                  message="从已有的 ETL 任务配置自动生成 Kettle 转换文件"
                  type="info"
                  showIcon
                  style={{ marginBottom: 16 }}
                />
                <Form form={etlTaskForm} layout="vertical" onFinish={handleETLTaskGenerate}>
                  <Form.Item name="task_id" label="选择 ETL 任务" rules={[{ required: true }]}>
                    <Select placeholder="选择一个 ETL 任务" showSearch optionFilterProp="children">
                      {etlTasks.map(task => (
                        <Select.Option key={task.task_id} value={task.task_id}>
                          {task.name} ({task.source?.table_name || '未知'} → {task.target?.table_name || '未知'})
                        </Select.Option>
                      ))}
                    </Select>
                  </Form.Item>
                  <Form.Item name="name" label="配置名称（可选）">
                    <Input placeholder="留空则自动生成" />
                  </Form.Item>
                  <Row gutter={16}>
                    <Col span={12}>
                      <Form.Item name="write_mode" label="写入模式">
                        <Select placeholder="使用任务默认配置">
                          {typesConfig?.write_modes.map(m => (
                            <Select.Option key={m.value} value={m.value}>
                              {m.label}
                            </Select.Option>
                          ))}
                        </Select>
                      </Form.Item>
                    </Col>
                    <Col span={12}>
                      <Form.Item name="batch_size" label="批次大小">
                        <InputNumber style={{ width: '100%' }} min={1} placeholder="1000" />
                      </Form.Item>
                    </Col>
                  </Row>
                  <Button type="primary" htmlType="submit" loading={loading} icon={<RocketOutlined />} block>
                    生成配置
                  </Button>
                </Form>
              </TabPane>

              {/* 从元数据生成 */}
              <TabPane
                tab={
                  <span>
                    <DatabaseOutlined /> 从元数据
                  </span>
                }
                key="metadata"
              >
                <Alert
                  message="从元数据中的表定义自动生成 Kettle 转换配置"
                  type="info"
                  showIcon
                  style={{ marginBottom: 16 }}
                />
                <Form form={metadataForm} layout="vertical" onFinish={handleMetadataGenerate}>
                  <Row gutter={16}>
                    <Col span={12}>
                      <Form.Item label="源数据库" rules={[{ required: true }]}>
                        <Select
                          placeholder="选择源数据库"
                          value={selectedSourceDb}
                          onChange={(value) => setSelectedSourceDb(value)}
                        >
                          {databases.map(db => (
                            <Select.Option key={db.name} value={db.name}>
                              {db.name}
                            </Select.Option>
                          ))}
                        </Select>
                      </Form.Item>
                    </Col>
                    <Col span={12}>
                      <Form.Item name="source_table" label="源表" rules={[{ required: true }]}>
                        <Select placeholder="选择源表" showSearch optionFilterProp="children" disabled={!selectedSourceDb}>
                          {sourceTables.map(table => (
                            <Select.Option key={table.name} value={table.name}>
                              {table.name}
                            </Select.Option>
                          ))}
                        </Select>
                      </Form.Item>
                    </Col>
                  </Row>
                  <Row gutter={16}>
                    <Col span={12}>
                      <Form.Item label="目标数据库" rules={[{ required: true }]}>
                        <Select
                          placeholder="选择目标数据库"
                          value={selectedTargetDb}
                          onChange={(value) => setSelectedTargetDb(value)}
                        >
                          {databases.map(db => (
                            <Select.Option key={db.name} value={db.name}>
                              {db.name}
                            </Select.Option>
                          ))}
                        </Select>
                      </Form.Item>
                    </Col>
                    <Col span={12}>
                      <Form.Item name="target_table" label="目标表" rules={[{ required: true }]}>
                        <Select placeholder="选择目标表" showSearch optionFilterProp="children" disabled={!selectedTargetDb}>
                          {targetTables.map(table => (
                            <Select.Option key={table.name} value={table.name}>
                              {table.name}
                            </Select.Option>
                          ))}
                        </Select>
                      </Form.Item>
                    </Col>
                  </Row>
                  <Form.Item name="name" label="配置名称（可选）">
                    <Input placeholder="留空则自动生成" />
                  </Form.Item>
                  <Row gutter={16}>
                    <Col span={12}>
                      <Form.Item name="write_mode" label="写入模式">
                        <Select defaultValue="insert">
                          {typesConfig?.write_modes.map(m => (
                            <Select.Option key={m.value} value={m.value}>
                              {m.label}
                            </Select.Option>
                          ))}
                        </Select>
                      </Form.Item>
                    </Col>
                    <Col span={12}>
                      <Form.Item name="batch_size" label="批次大小">
                        <InputNumber style={{ width: '100%' }} min={1} defaultValue={1000} />
                      </Form.Item>
                    </Col>
                  </Row>
                  <Button type="primary" htmlType="submit" loading={loading} icon={<RocketOutlined />} block>
                    生成配置
                  </Button>
                </Form>
              </TabPane>

              {/* 生成作业 */}
              <TabPane
                tab={
                  <span>
                    <LinkOutlined /> 生成作业
                  </span>
                }
                key="job"
              >
                <Alert
                  message="将多个 Kettle 转换组合成一个作业文件"
                  type="info"
                  showIcon
                  style={{ marginBottom: 16 }}
                />
                <Form form={jobForm} layout="vertical" onFinish={handleJobGenerate}>
                  <Form.Item name="name" label="作业名称" rules={[{ required: true }]}>
                    <Input placeholder="my_job" />
                  </Form.Item>
                  <Form.Item name="description" label="作业描述">
                    <TextArea rows={2} placeholder="作业描述信息" />
                  </Form.Item>
                  <Form.Item name="sequential" label="执行顺序">
                    <Select defaultValue={true}>
                      <Select.Option value={true}>顺序执行</Select.Option>
                      <Select.Option value={false}>并行执行</Select.Option>
                    </Select>
                  </Form.Item>

                  <div style={{ marginBottom: 16 }}>
                    <div
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        marginBottom: 8,
                      }}
                    >
                      <Text strong>转换文件路径列表</Text>
                      <Button type="dashed" size="small" icon={<PlusOutlined />} onClick={handleAddTransformation}>
                        添加转换
                      </Button>
                    </div>
                    {transformationList.map((path, index) => (
                      <div key={index} style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
                        <Input
                          value={path}
                          onChange={e => handleUpdateTransformation(index, e.target.value)}
                          placeholder={`/path/to/transformation_${index + 1}.ktr`}
                          prefix={<FileOutlined />}
                        />
                        <Button
                          type="text"
                          danger
                          icon={<DeleteOutlined />}
                          onClick={() => handleRemoveTransformation(index)}
                          disabled={transformationList.length <= 1}
                        />
                      </div>
                    ))}
                  </div>

                  <Button type="primary" htmlType="submit" loading={loading} icon={<RocketOutlined />} block>
                    生成作业配置
                  </Button>
                </Form>
              </TabPane>
            </Tabs>
          </Card>
        </Col>

        {/* 右侧：结果展示 */}
        <Col span={12}>
          <Card title="生成结果" style={{ minHeight: 600 }}>
            <Spin spinning={loading}>{renderResult()}</Spin>
          </Card>
        </Col>
      </Row>

      {/* XML 完整预览弹窗 */}
      <Modal
        title={`${generatedResult?.name}.${generatedResult?.format} - 完整配置`}
        open={xmlPreviewVisible}
        onCancel={() => setXmlPreviewVisible(false)}
        width={900}
        footer={[
          <Button key="copy" icon={<CopyOutlined />} onClick={handleCopyContent}>
            复制
          </Button>,
          <Button key="download" type="primary" icon={<DownloadOutlined />} onClick={handleDownload}>
            下载
          </Button>,
          <Button key="close" onClick={() => setXmlPreviewVisible(false)}>
            关闭
          </Button>,
        ]}
      >
        <div
          style={{
            maxHeight: '60vh',
            overflow: 'auto',
            backgroundColor: '#1e1e1e',
            color: '#d4d4d4',
            padding: 16,
            borderRadius: 4,
            fontFamily: 'Consolas, Monaco, monospace',
            fontSize: 12,
          }}
        >
          <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
            {generatedResult?.content}
          </pre>
        </div>
      </Modal>
    </div>
  );
};

export default KettlePage;
