import { useState } from 'react';
import {
  Card,
  Button,
  Tag,
  Space,
  Modal,
  Form,
  Input,
  Select,
  message,
  Table,
  Tabs,
  Alert,
  Spin,
  Descriptions,
  Statistic,
  Row,
  Col,
  Upload,
  Typography,
  Tooltip,
  Result,
} from 'antd';
import {
  PlayCircleOutlined,
  CloudServerOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  FileOutlined,
  UploadOutlined,
  ReloadOutlined,
  CodeOutlined,
  InfoCircleOutlined,
  SettingOutlined,
  SyncOutlined,
  DatabaseOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import dayjs from 'dayjs';
import {
  getKettleStatus,
  executeKettleJob,
  executeKettleTransformation,
  validateKettleJob,
  validateKettleTransformation,
  executeETLTaskWithKettle,
  getETLTasks,
} from '@/services/alldata';
import type {
  KettleStatus,
  KettleExecutionResult,
  KettleJobRequest,
  KettleTransformationRequest,
  KettleLogLevel,
  ETLTask,
} from '@/services/alldata';

const { Option } = Select;
const { TextArea } = Input;
const { Text, Title } = Typography;

// 日志级别选项
const LOG_LEVELS: { value: KettleLogLevel; label: string; description: string }[] = [
  { value: 'Nothing', label: '无', description: '不输出日志' },
  { value: 'Error', label: '错误', description: '仅输出错误信息' },
  { value: 'Minimal', label: '最小', description: '输出最小化日志' },
  { value: 'Basic', label: '基础', description: '输出基础日志信息' },
  { value: 'Detailed', label: '详细', description: '输出详细日志' },
  { value: 'Debug', label: '调试', description: '输出调试级别日志' },
  { value: 'Rowlevel', label: '行级', description: '输出每行数据的日志' },
];

// 执行历史记录类型
interface ExecutionHistory {
  id: string;
  type: 'job' | 'transformation';
  name: string;
  result: KettleExecutionResult;
  executedAt: string;
}

function KettlePanel() {
  const queryClient = useQueryClient();

  // 状态
  const [activeTab, setActiveTab] = useState('status');
  const [isExecuteModalOpen, setIsExecuteModalOpen] = useState(false);
  const [executeType, setExecuteType] = useState<'job' | 'transformation'>('job');
  const [executionHistory, setExecutionHistory] = useState<ExecutionHistory[]>([]);
  const [selectedResult, setSelectedResult] = useState<KettleExecutionResult | null>(null);
  const [isResultModalOpen, setIsResultModalOpen] = useState(false);

  const [jobForm] = Form.useForm();
  const [transForm] = Form.useForm();

  // 获取 Kettle 状态
  const { data: statusData, isLoading: isLoadingStatus, refetch: refetchStatus } = useQuery({
    queryKey: ['kettle-status'],
    queryFn: getKettleStatus,
    refetchInterval: 30000, // 每30秒刷新一次
  });

  // 获取使用 Kettle 引擎的 ETL 任务
  const { data: kettleTasksData, isLoading: isLoadingTasks } = useQuery({
    queryKey: ['etl-tasks', 'kettle'],
    queryFn: () => getETLTasks({ page: 1, page_size: 100 }),
    select: (data) => ({
      ...data,
      data: {
        ...data.data,
        tasks: data.data.tasks.filter((task: ETLTask) =>
          // @ts-expect-error engine_type is a new field
          task.engine_type === 'kettle'
        ),
      },
    }),
  });

  // 执行 Kettle 作业
  const executeJobMutation = useMutation({
    mutationFn: executeKettleJob,
    onSuccess: (result, variables) => {
      if (result.data.success) {
        message.success('Kettle 作业执行成功');
      } else {
        message.warning('Kettle 作业执行完成，但有错误');
      }
      // 添加到执行历史
      setExecutionHistory((prev) => [
        {
          id: `job-${Date.now()}`,
          type: 'job',
          name: variables.job_path || variables.job_name || '未命名作业',
          result: result.data,
          executedAt: new Date().toISOString(),
        },
        ...prev.slice(0, 19), // 保留最近20条
      ]);
      setSelectedResult(result.data);
      setIsResultModalOpen(true);
      setIsExecuteModalOpen(false);
      jobForm.resetFields();
    },
    onError: (error) => {
      message.error(`作业执行失败: ${error instanceof Error ? error.message : '未知错误'}`);
    },
  });

  // 执行 Kettle 转换
  const executeTransMutation = useMutation({
    mutationFn: executeKettleTransformation,
    onSuccess: (result, variables) => {
      if (result.data.success) {
        message.success('Kettle 转换执行成功');
      } else {
        message.warning('Kettle 转换执行完成，但有错误');
      }
      setExecutionHistory((prev) => [
        {
          id: `trans-${Date.now()}`,
          type: 'transformation',
          name: variables.trans_path || variables.trans_name || '未命名转换',
          result: result.data,
          executedAt: new Date().toISOString(),
        },
        ...prev.slice(0, 19),
      ]);
      setSelectedResult(result.data);
      setIsResultModalOpen(true);
      setIsExecuteModalOpen(false);
      transForm.resetFields();
    },
    onError: (error) => {
      message.error(`转换执行失败: ${error instanceof Error ? error.message : '未知错误'}`);
    },
  });

  // 验证作业
  const validateJobMutation = useMutation({
    mutationFn: validateKettleJob,
    onSuccess: (result) => {
      if (result.data.is_valid) {
        message.success('作业文件验证通过');
      } else {
        message.error(`作业文件验证失败: ${result.data.error}`);
      }
    },
    onError: () => {
      message.error('作业文件验证请求失败');
    },
  });

  // 验证转换
  const validateTransMutation = useMutation({
    mutationFn: validateKettleTransformation,
    onSuccess: (result) => {
      if (result.data.is_valid) {
        message.success('转换文件验证通过');
      } else {
        message.error(`转换文件验证失败: ${result.data.error}`);
      }
    },
    onError: () => {
      message.error('转换文件验证请求失败');
    },
  });

  // 使用 Kettle 执行 ETL 任务
  const executeETLWithKettleMutation = useMutation({
    mutationFn: (taskId: string) => executeETLTaskWithKettle(taskId),
    onSuccess: (result) => {
      if (result.data.execution_result.success) {
        message.success('ETL 任务执行成功');
      } else {
        message.warning('ETL 任务执行完成，但有错误');
      }
      setSelectedResult(result.data.execution_result);
      setIsResultModalOpen(true);
      queryClient.invalidateQueries({ queryKey: ['etl-tasks'] });
    },
    onError: () => {
      message.error('ETL 任务执行失败');
    },
  });

  const kettleStatus: KettleStatus | undefined = statusData?.data;

  // 渲染状态标签
  const renderStatusTag = () => {
    if (isLoadingStatus) {
      return <Tag icon={<SyncOutlined spin />}>检测中...</Tag>;
    }
    if (!kettleStatus) {
      return <Tag color="default">未知</Tag>;
    }
    if (!kettleStatus.enabled) {
      return <Tag color="orange">未启用</Tag>;
    }
    if (!kettleStatus.kettle_installed) {
      return <Tag color="red" icon={<CloseCircleOutlined />}>未安装</Tag>;
    }
    return <Tag color="green" icon={<CheckCircleOutlined />}>正常运行</Tag>;
  };

  // 执行历史表格列
  const historyColumns = [
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      width: 100,
      render: (type: string) => (
        <Tag color={type === 'job' ? 'blue' : 'purple'}>
          {type === 'job' ? '作业' : '转换'}
        </Tag>
      ),
    },
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      ellipsis: true,
    },
    {
      title: '状态',
      key: 'status',
      width: 100,
      render: (_: unknown, record: ExecutionHistory) => (
        <Tag color={record.result.success ? 'green' : 'red'}>
          {record.result.success ? '成功' : '失败'}
        </Tag>
      ),
    },
    {
      title: '行数 (读/写/错)',
      key: 'rows',
      width: 150,
      render: (_: unknown, record: ExecutionHistory) => (
        <Space size="small">
          <Text type="secondary">{record.result.rows_read}</Text>
          <Text>/</Text>
          <Text type="success">{record.result.rows_written}</Text>
          <Text>/</Text>
          <Text type={record.result.rows_error > 0 ? 'danger' : 'secondary'}>
            {record.result.rows_error}
          </Text>
        </Space>
      ),
    },
    {
      title: '耗时',
      key: 'duration',
      width: 100,
      render: (_: unknown, record: ExecutionHistory) => (
        <Text>{record.result.duration_seconds.toFixed(2)} 秒</Text>
      ),
    },
    {
      title: '执行时间',
      dataIndex: 'executedAt',
      key: 'executedAt',
      width: 160,
      render: (date: string) => dayjs(date).format('YYYY-MM-DD HH:mm:ss'),
    },
    {
      title: '操作',
      key: 'actions',
      width: 80,
      render: (_: unknown, record: ExecutionHistory) => (
        <Button
          type="link"
          size="small"
          onClick={() => {
            setSelectedResult(record.result);
            setIsResultModalOpen(true);
          }}
        >
          详情
        </Button>
      ),
    },
  ];

  // Kettle ETL 任务表格列
  const kettleTaskColumns = [
    {
      title: '任务名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '作业/转换文件',
      key: 'kettle_file',
      render: (_: unknown, record: ETLTask) => {
        // @ts-expect-error kettle fields are new
        const path = record.kettle_job_path || record.kettle_trans_path;
        return path ? (
          <Tooltip title={path}>
            <Text ellipsis style={{ maxWidth: 200 }}>{path}</Text>
          </Tooltip>
        ) : '-';
      },
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const colors: Record<string, string> = {
          pending: 'default',
          running: 'blue',
          completed: 'green',
          failed: 'red',
        };
        return <Tag color={colors[status] || 'default'}>{status}</Tag>;
      },
    },
    {
      title: '操作',
      key: 'actions',
      render: (_: unknown, record: ETLTask) => (
        <Button
          type="primary"
          size="small"
          icon={<PlayCircleOutlined />}
          onClick={() => executeETLWithKettleMutation.mutate(record.task_id)}
          loading={executeETLWithKettleMutation.isPending}
        >
          执行
        </Button>
      ),
    },
  ];

  // 处理作业执行
  const handleExecuteJob = () => {
    jobForm.validateFields().then((values) => {
      const request: KettleJobRequest = {
        job_path: values.job_path,
        repository: values.repository,
        directory: values.directory,
        job_name: values.job_name,
        params: values.params ? JSON.parse(values.params) : undefined,
        log_level: values.log_level,
      };
      executeJobMutation.mutate(request);
    });
  };

  // 处理转换执行
  const handleExecuteTrans = () => {
    transForm.validateFields().then((values) => {
      const request: KettleTransformationRequest = {
        trans_path: values.trans_path,
        repository: values.repository,
        directory: values.directory,
        trans_name: values.trans_name,
        params: values.params ? JSON.parse(values.params) : undefined,
        log_level: values.log_level,
      };
      executeTransMutation.mutate(request);
    });
  };

  // 渲染状态面板
  const renderStatusPanel = () => (
    <Card
      title={
        <Space>
          <CloudServerOutlined />
          <span>Kettle 服务状态</span>
        </Space>
      }
      extra={
        <Button
          icon={<ReloadOutlined />}
          onClick={() => refetchStatus()}
          loading={isLoadingStatus}
        >
          刷新
        </Button>
      }
    >
      {isLoadingStatus ? (
        <div style={{ textAlign: 'center', padding: 40 }}>
          <Spin tip="正在检测 Kettle 服务状态..." />
        </div>
      ) : kettleStatus ? (
        <div>
          <Descriptions column={2} bordered>
            <Descriptions.Item label="服务状态" span={2}>
              {renderStatusTag()}
            </Descriptions.Item>
            <Descriptions.Item label="Kettle 已安装">
              {kettleStatus.kettle_installed ? (
                <Tag color="green" icon={<CheckCircleOutlined />}>是</Tag>
              ) : (
                <Tag color="red" icon={<CloseCircleOutlined />}>否</Tag>
              )}
            </Descriptions.Item>
            <Descriptions.Item label="服务已启用">
              {kettleStatus.enabled ? (
                <Tag color="green" icon={<CheckCircleOutlined />}>是</Tag>
              ) : (
                <Tag color="orange" icon={<CloseCircleOutlined />}>否</Tag>
              )}
            </Descriptions.Item>
            {kettleStatus.kettle_home && (
              <Descriptions.Item label="KETTLE_HOME" span={2}>
                <Text code>{kettleStatus.kettle_home}</Text>
              </Descriptions.Item>
            )}
            {kettleStatus.java_version && (
              <Descriptions.Item label="Java 版本" span={2}>
                <Text code>{kettleStatus.java_version}</Text>
              </Descriptions.Item>
            )}
            {kettleStatus.message && (
              <Descriptions.Item label="消息" span={2}>
                {kettleStatus.message}
              </Descriptions.Item>
            )}
          </Descriptions>

          {!kettleStatus.enabled && (
            <Alert
              type="warning"
              message="Kettle 服务未启用"
              description="请联系管理员启用 Kettle ETL 引擎服务。"
              showIcon
              style={{ marginTop: 16 }}
            />
          )}

          {kettleStatus.enabled && !kettleStatus.kettle_installed && (
            <Alert
              type="error"
              message="Kettle 未正确安装"
              description="请检查 KETTLE_HOME 环境变量配置是否正确，确保 Kitchen.sh 和 Pan.sh 可执行。"
              showIcon
              style={{ marginTop: 16 }}
            />
          )}
        </div>
      ) : (
        <Result
          status="warning"
          title="无法获取 Kettle 状态"
          subTitle="请检查后端服务是否正常运行"
          extra={
            <Button type="primary" onClick={() => refetchStatus()}>
              重试
            </Button>
          }
        />
      )}
    </Card>
  );

  // 渲染执行面板
  const renderExecutePanel = () => (
    <div>
      <Row gutter={16}>
        <Col span={12}>
          <Card
            title={
              <Space>
                <FileOutlined />
                <span>执行 Kettle 作业 (.kjb)</span>
              </Space>
            }
            extra={
              <Button
                type="primary"
                icon={<PlayCircleOutlined />}
                onClick={() => {
                  setExecuteType('job');
                  setIsExecuteModalOpen(true);
                }}
                disabled={!kettleStatus?.enabled || !kettleStatus?.kettle_installed}
              >
                执行作业
              </Button>
            }
          >
            <Text type="secondary">
              Kettle 作业（Job）用于编排多个转换或其他作业，支持顺序执行、条件判断、循环等控制流程。
            </Text>
            <div style={{ marginTop: 16 }}>
              <Space direction="vertical" style={{ width: '100%' }}>
                <Text strong>支持的执行方式：</Text>
                <ul style={{ marginBottom: 0 }}>
                  <li>从文件路径执行 (.kjb)</li>
                  <li>从 Kettle 资源库执行</li>
                  <li>支持自定义参数传递</li>
                </ul>
              </Space>
            </div>
          </Card>
        </Col>
        <Col span={12}>
          <Card
            title={
              <Space>
                <SyncOutlined />
                <span>执行 Kettle 转换 (.ktr)</span>
              </Space>
            }
            extra={
              <Button
                type="primary"
                icon={<PlayCircleOutlined />}
                onClick={() => {
                  setExecuteType('transformation');
                  setIsExecuteModalOpen(true);
                }}
                disabled={!kettleStatus?.enabled || !kettleStatus?.kettle_installed}
              >
                执行转换
              </Button>
            }
          >
            <Text type="secondary">
              Kettle 转换（Transformation）用于定义数据的 ETL 流程，包括数据抽取、清洗、转换和加载。
            </Text>
            <div style={{ marginTop: 16 }}>
              <Space direction="vertical" style={{ width: '100%' }}>
                <Text strong>支持的功能：</Text>
                <ul style={{ marginBottom: 0 }}>
                  <li>多数据源读取</li>
                  <li>数据过滤、映射、聚合</li>
                  <li>数据质量校验</li>
                </ul>
              </Space>
            </div>
          </Card>
        </Col>
      </Row>

      {/* 执行历史 */}
      <Card
        title="执行历史"
        style={{ marginTop: 16 }}
        extra={
          executionHistory.length > 0 && (
            <Button size="small" onClick={() => setExecutionHistory([])}>
              清空历史
            </Button>
          )
        }
      >
        {executionHistory.length > 0 ? (
          <Table
            columns={historyColumns}
            dataSource={executionHistory}
            rowKey="id"
            size="small"
            pagination={{ pageSize: 5 }}
          />
        ) : (
          <div style={{ textAlign: 'center', padding: 40 }}>
            <Text type="secondary">暂无执行历史</Text>
          </div>
        )}
      </Card>
    </div>
  );

  // 渲染 Kettle ETL 任务面板
  const renderKettleTasksPanel = () => (
    <Card
      title={
        <Space>
          <DatabaseOutlined />
          <span>Kettle 引擎 ETL 任务</span>
        </Space>
      }
    >
      {isLoadingTasks ? (
        <div style={{ textAlign: 'center', padding: 40 }}>
          <Spin tip="加载中..." />
        </div>
      ) : kettleTasksData?.data?.tasks && kettleTasksData.data.tasks.length > 0 ? (
        <Table
          columns={kettleTaskColumns}
          dataSource={kettleTasksData.data.tasks}
          rowKey="task_id"
          size="small"
          pagination={{ pageSize: 10 }}
        />
      ) : (
        <div style={{ textAlign: 'center', padding: 40 }}>
          <Text type="secondary">暂无使用 Kettle 引擎的 ETL 任务</Text>
          <div style={{ marginTop: 16 }}>
            <Text type="secondary">
              在创建 ETL 任务时，选择"Kettle"作为执行引擎即可。
            </Text>
          </div>
        </div>
      )}
    </Card>
  );

  return (
    <div style={{ padding: '24px' }}>
      <Card
        title={
          <Space>
            <SettingOutlined />
            <span>Kettle ETL 引擎</span>
            {renderStatusTag()}
          </Space>
        }
      >
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={[
            {
              key: 'status',
              label: (
                <span>
                  <InfoCircleOutlined />
                  服务状态
                </span>
              ),
              children: renderStatusPanel(),
            },
            {
              key: 'execute',
              label: (
                <span>
                  <PlayCircleOutlined />
                  执行作业/转换
                </span>
              ),
              children: renderExecutePanel(),
            },
            {
              key: 'tasks',
              label: (
                <span>
                  <DatabaseOutlined />
                  Kettle 任务
                </span>
              ),
              children: renderKettleTasksPanel(),
            },
          ]}
        />
      </Card>

      {/* 执行作业/转换模态框 */}
      <Modal
        title={executeType === 'job' ? '执行 Kettle 作业' : '执行 Kettle 转换'}
        open={isExecuteModalOpen}
        onOk={executeType === 'job' ? handleExecuteJob : handleExecuteTrans}
        onCancel={() => {
          setIsExecuteModalOpen(false);
          jobForm.resetFields();
          transForm.resetFields();
        }}
        confirmLoading={executeJobMutation.isPending || executeTransMutation.isPending}
        width={600}
      >
        {executeType === 'job' ? (
          <Form form={jobForm} layout="vertical">
            <Alert
              type="info"
              message="提示"
              description="可以通过文件路径执行本地作业文件，或从 Kettle 资源库执行。"
              showIcon
              style={{ marginBottom: 16 }}
            />
            <Form.Item
              label="作业文件路径"
              name="job_path"
              rules={[{ required: true, message: '请输入作业文件路径' }]}
              extra="服务器上的 .kjb 文件绝对路径"
            >
              <Input placeholder="例如: /opt/kettle/jobs/my_job.kjb" />
            </Form.Item>
            <Form.Item label="资源库名称" name="repository">
              <Input placeholder="可选：Kettle 资源库名称" />
            </Form.Item>
            <Form.Item label="目录" name="directory">
              <Input placeholder="可选：资源库中的目录路径" />
            </Form.Item>
            <Form.Item label="作业名称" name="job_name">
              <Input placeholder="可选：资源库中的作业名称" />
            </Form.Item>
            <Form.Item
              label="参数 (JSON)"
              name="params"
              extra="JSON 格式的参数，例如: {&quot;param1&quot;: &quot;value1&quot;}"
            >
              <TextArea rows={3} placeholder='{"param1": "value1", "param2": "value2"}' />
            </Form.Item>
            <Form.Item label="日志级别" name="log_level" initialValue="Basic">
              <Select>
                {LOG_LEVELS.map((level) => (
                  <Option key={level.value} value={level.value}>
                    {level.label} - {level.description}
                  </Option>
                ))}
              </Select>
            </Form.Item>
            <Form.Item>
              <Button
                icon={<CheckCircleOutlined />}
                onClick={() => {
                  const path = jobForm.getFieldValue('job_path');
                  if (path) {
                    validateJobMutation.mutate(path);
                  } else {
                    message.warning('请先输入作业文件路径');
                  }
                }}
                loading={validateJobMutation.isPending}
              >
                验证文件
              </Button>
            </Form.Item>
          </Form>
        ) : (
          <Form form={transForm} layout="vertical">
            <Alert
              type="info"
              message="提示"
              description="可以通过文件路径执行本地转换文件，或从 Kettle 资源库执行。"
              showIcon
              style={{ marginBottom: 16 }}
            />
            <Form.Item
              label="转换文件路径"
              name="trans_path"
              rules={[{ required: true, message: '请输入转换文件路径' }]}
              extra="服务器上的 .ktr 文件绝对路径"
            >
              <Input placeholder="例如: /opt/kettle/transformations/my_trans.ktr" />
            </Form.Item>
            <Form.Item label="资源库名称" name="repository">
              <Input placeholder="可选：Kettle 资源库名称" />
            </Form.Item>
            <Form.Item label="目录" name="directory">
              <Input placeholder="可选：资源库中的目录路径" />
            </Form.Item>
            <Form.Item label="转换名称" name="trans_name">
              <Input placeholder="可选：资源库中的转换名称" />
            </Form.Item>
            <Form.Item
              label="参数 (JSON)"
              name="params"
              extra="JSON 格式的参数，例如: {&quot;param1&quot;: &quot;value1&quot;}"
            >
              <TextArea rows={3} placeholder='{"param1": "value1", "param2": "value2"}' />
            </Form.Item>
            <Form.Item label="日志级别" name="log_level" initialValue="Basic">
              <Select>
                {LOG_LEVELS.map((level) => (
                  <Option key={level.value} value={level.value}>
                    {level.label} - {level.description}
                  </Option>
                ))}
              </Select>
            </Form.Item>
            <Form.Item>
              <Button
                icon={<CheckCircleOutlined />}
                onClick={() => {
                  const path = transForm.getFieldValue('trans_path');
                  if (path) {
                    validateTransMutation.mutate(path);
                  } else {
                    message.warning('请先输入转换文件路径');
                  }
                }}
                loading={validateTransMutation.isPending}
              >
                验证文件
              </Button>
            </Form.Item>
          </Form>
        )}
      </Modal>

      {/* 执行结果模态框 */}
      <Modal
        title="执行结果"
        open={isResultModalOpen}
        onCancel={() => {
          setIsResultModalOpen(false);
          setSelectedResult(null);
        }}
        footer={[
          <Button key="close" onClick={() => setIsResultModalOpen(false)}>
            关闭
          </Button>,
        ]}
        width={800}
      >
        {selectedResult && (
          <div>
            <Alert
              type={selectedResult.success ? 'success' : 'error'}
              message={selectedResult.success ? '执行成功' : '执行失败'}
              description={selectedResult.error_message}
              showIcon
              style={{ marginBottom: 16 }}
            />

            <Row gutter={16} style={{ marginBottom: 16 }}>
              <Col span={6}>
                <Statistic title="退出码" value={selectedResult.exit_code} />
              </Col>
              <Col span={6}>
                <Statistic
                  title="耗时"
                  value={selectedResult.duration_seconds.toFixed(2)}
                  suffix="秒"
                />
              </Col>
              <Col span={4}>
                <Statistic title="读取行数" value={selectedResult.rows_read} />
              </Col>
              <Col span={4}>
                <Statistic
                  title="写入行数"
                  value={selectedResult.rows_written}
                  valueStyle={{ color: '#3f8600' }}
                />
              </Col>
              <Col span={4}>
                <Statistic
                  title="错误行数"
                  value={selectedResult.rows_error}
                  valueStyle={{ color: selectedResult.rows_error > 0 ? '#cf1322' : undefined }}
                />
              </Col>
            </Row>

            <Descriptions bordered size="small">
              <Descriptions.Item label="开始时间" span={3}>
                {dayjs(selectedResult.started_at).format('YYYY-MM-DD HH:mm:ss')}
              </Descriptions.Item>
              <Descriptions.Item label="结束时间" span={3}>
                {dayjs(selectedResult.finished_at).format('YYYY-MM-DD HH:mm:ss')}
              </Descriptions.Item>
            </Descriptions>

            {selectedResult.stdout && (
              <div style={{ marginTop: 16 }}>
                <Title level={5}>标准输出</Title>
                <pre
                  style={{
                    maxHeight: 200,
                    overflow: 'auto',
                    background: '#f5f5f5',
                    padding: 12,
                    borderRadius: 4,
                    fontSize: 12,
                  }}
                >
                  {selectedResult.stdout}
                </pre>
              </div>
            )}

            {selectedResult.stderr && (
              <div style={{ marginTop: 16 }}>
                <Title level={5}>错误输出</Title>
                <pre
                  style={{
                    maxHeight: 200,
                    overflow: 'auto',
                    background: '#fff2f0',
                    padding: 12,
                    borderRadius: 4,
                    fontSize: 12,
                    color: '#cf1322',
                  }}
                >
                  {selectedResult.stderr}
                </pre>
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
}

export default KettlePanel;
