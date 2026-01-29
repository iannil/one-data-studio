import { useState } from 'react';
import {
  Table,
  Button,
  Tag,
  Space,
  Modal,
  Form,
  Input,
  Select,
  message,
  Popconfirm,
  Card,
  Drawer,
  Descriptions,
  Progress,
  Statistic,
  Row,
  Col,
  Tooltip,
} from 'antd';
import {
  PlusOutlined,
  PlayCircleOutlined,
  StopOutlined,
  DeleteOutlined,
  EyeOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  SwapRightOutlined,
  FileTextOutlined,
  ScheduleOutlined,
  ThunderboltOutlined,
  ApiOutlined,
  SettingOutlined,
  ExperimentOutlined,
  RobotOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import dayjs from 'dayjs';
import alldata from '@/services/alldata';
import type { ETLTask, CreateETLTaskRequest, ETLTaskStatus, ETLTaskType, KettleStatus } from '@/services/alldata';
import AIFieldMappingPanel from './AIFieldMappingPanel';

const { Option } = Select;
const { TextArea } = Input;

function ETLPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [typeFilter, setTypeFilter] = useState<string>('');

  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isDetailDrawerOpen, setIsDetailDrawerOpen] = useState(false);
  const [isLogsModalOpen, setIsLogsModalOpen] = useState(false);
  const [isAIFieldMappingOpen, setIsAIFieldMappingOpen] = useState(false);
  const [selectedTask, setSelectedTask] = useState<ETLTask | null>(null);
  const [taskLogs, setTaskLogs] = useState<string>('');
  const [engineType, setEngineType] = useState<string>('builtin');
  const [sourceFields, setSourceFields] = useState<Array<{ name: string; type: string; description?: string }>>([]);
  const [targetFields, setTargetFields] = useState<Array<{ name: string; type: string; description?: string }>>([]);

  const [form] = Form.useForm();

  // 获取 ETL 任务列表
  const { data: tasksData, isLoading: isLoadingList } = useQuery({
    queryKey: ['etl-tasks', page, pageSize, statusFilter, typeFilter],
    queryFn: () =>
      alldata.getETLTasks({
        page,
        page_size: pageSize,
        status: statusFilter as ETLTaskStatus || undefined,
        type: typeFilter as ETLTaskType || undefined,
      }),
  });

  // 获取数据源列表（用于选择）
  const { data: sourcesData } = useQuery({
    queryKey: ['datasources'],
    queryFn: () => alldata.getDataSources(),
  });

  // 获取 Kettle 服务状态
  const { data: kettleStatusData } = useQuery({
    queryKey: ['kettle-status'],
    queryFn: () => alldata.getKettleStatus(),
  });

  // 创建 ETL 任务
  const createMutation = useMutation({
    mutationFn: alldata.createETLTask,
    onSuccess: () => {
      message.success('ETL 任务创建成功');
      setIsCreateModalOpen(false);
      form.resetFields();
      queryClient.invalidateQueries({ queryKey: ['etl-tasks'] });
    },
    onError: () => {
      message.error('ETL 任务创建失败');
    },
  });

  // 删除 ETL 任务
  const deleteMutation = useMutation({
    mutationFn: alldata.deleteETLTask,
    onSuccess: () => {
      message.success('ETL 任务删除成功');
      setIsDetailDrawerOpen(false);
      queryClient.invalidateQueries({ queryKey: ['etl-tasks'] });
    },
    onError: () => {
      message.error('ETL 任务删除失败');
    },
  });

  // 启动 ETL 任务
  const startMutation = useMutation({
    mutationFn: alldata.startETLTask,
    onSuccess: () => {
      message.success('ETL 任务启动成功');
      queryClient.invalidateQueries({ queryKey: ['etl-tasks'] });
    },
    onError: () => {
      message.error('ETL 任务启动失败');
    },
  });

  // 停止 ETL 任务
  const stopMutation = useMutation({
    mutationFn: alldata.stopETLTask,
    onSuccess: () => {
      message.success('ETL 任务已停止');
      queryClient.invalidateQueries({ queryKey: ['etl-tasks'] });
    },
    onError: () => {
      message.error('ETL 任务停止失败');
    },
  });

  // 使用 Kettle 引擎执行 ETL 任务
  const executeKettleMutation = useMutation({
    mutationFn: (taskId: string) => alldata.executeETLTaskWithKettle(taskId),
    onSuccess: (response) => {
      if (response.data?.execution_result?.success) {
        message.success(`Kettle 任务执行成功，处理 ${response.data.execution_result.rows_written} 行`);
      } else {
        message.warning(`Kettle 任务执行完成，但有错误: ${response.data?.execution_result?.error_message || '未知错误'}`);
      }
      queryClient.invalidateQueries({ queryKey: ['etl-tasks'] });
    },
    onError: (error: Error) => {
      message.error(`Kettle 任务执行失败: ${error.message}`);
    },
  });

  const kettleStatus: KettleStatus | undefined = kettleStatusData?.data;
  const isKettleAvailable = kettleStatus?.enabled && kettleStatus?.kettle_installed;

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      pending: 'default',
      running: 'blue',
      completed: 'green',
      failed: 'red',
      stopped: 'orange',
    };
    return colors[status] || 'default';
  };

  const getStatusText = (status: string) => {
    const texts: Record<string, string> = {
      pending: '等待中',
      running: '运行中',
      completed: '已完成',
      failed: '失败',
      stopped: '已停止',
    };
    return texts[status] || status;
  };

  const getTypeColor = (type: string) => {
    const colors: Record<string, string> = {
      batch: 'green',
      streaming: 'blue',
      scheduled: 'orange',
    };
    return colors[type] || 'default';
  };

  const getTypeText = (type: string) => {
    const texts: Record<string, string> = {
      batch: '批处理',
      streaming: '流式',
      scheduled: '定时',
    };
    return texts[type] || type;
  };

  const getEngineColor = (engine: string) => {
    const colors: Record<string, string> = {
      builtin: 'default',
      kettle: 'purple',
      spark: 'orange',
      flink: 'cyan',
    };
    return colors[engine] || 'default';
  };

  const getEngineText = (engine: string) => {
    const texts: Record<string, string> = {
      builtin: '内置',
      kettle: 'Kettle',
      spark: 'Spark',
      flink: 'Flink',
    };
    return texts[engine] || engine;
  };

  const getEngineIcon = (engine: string) => {
    switch (engine) {
      case 'kettle':
        return <ThunderboltOutlined />;
      case 'spark':
        return <ExperimentOutlined />;
      case 'flink':
        return <ApiOutlined />;
      default:
        return <SettingOutlined />;
    }
  };

  const handleViewLogs = async (task: ETLTask) => {
    try {
      const result = await alldata.getETLTaskLogs(task.task_id);
      setTaskLogs(result.data.logs?.map((log) => JSON.stringify(log, null, 2)).join('\n\n') || '暂无日志');
      setIsLogsModalOpen(true);
    } catch (error) {
      message.error('获取日志失败');
    }
  };

  const columns = [
    {
      title: '任务名称',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: ETLTask) => (
        <a
          onClick={() => {
            setSelectedTask(record);
            setIsDetailDrawerOpen(true);
          }}
        >
          {name}
        </a>
      ),
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      render: (type: string) => (
        <Tag color={getTypeColor(type)}>{getTypeText(type)}</Tag>
      ),
    },
    {
      title: '引擎',
      key: 'engine',
      width: 100,
      render: (_: unknown, record: ETLTask & { engine_type?: string }) => {
        const engine = record.engine_type || 'builtin';
        return (
          <Tag color={getEngineColor(engine)} icon={getEngineIcon(engine)}>
            {getEngineText(engine)}
          </Tag>
        );
      },
    },
    {
      title: '数据流向',
      key: 'flow',
      render: (_: unknown, record: ETLTask) => (
        <Space size="small">
          <Tag>{record.source.type}</Tag>
          <SwapRightOutlined />
          <Tag>{record.target.type}</Tag>
        </Space>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => (
        <Tag color={getStatusColor(status)} icon={status === 'completed' ? <CheckCircleOutlined /> : status === 'failed' ? <CloseCircleOutlined /> : undefined}>
          {getStatusText(status)}
        </Tag>
      ),
    },
    {
      title: '调度',
      key: 'schedule',
      render: (_: unknown, record: ETLTask) => {
        if (!record.schedule) return <Tag>手动</Tag>;
        if (record.schedule.type === 'cron') {
          return <Tag icon={<ClockCircleOutlined />}>Cron: {record.schedule.expression}</Tag>;
        }
        return <Tag>{record.schedule.type}</Tag>;
      },
    },
    {
      title: '运行统计',
      key: 'statistics',
      render: (_: unknown, record: ETLTask) => {
        if (!record.statistics) return '-';
        const successRate = record.statistics.total_runs > 0
          ? Math.round((record.statistics.success_runs / record.statistics.total_runs) * 100)
          : 0;
        return (
          <Space size="small">
            <Tag>总: {record.statistics.total_runs}</Tag>
            <Tag color="green">成功: {record.statistics.success_runs}</Tag>
            {record.statistics.failed_runs > 0 && <Tag color="red">失败: {record.statistics.failed_runs}</Tag>}
            <Progress type="circle" size={24} percent={successRate} format={(p) => `${p}%`} />
          </Space>
        );
      },
    },
    {
      title: '下次运行',
      dataIndex: 'next_run',
      key: 'next_run',
      width: 160,
      render: (date: string) => (date ? dayjs(date).format('YYYY-MM-DD HH:mm') : '-'),
    },
    {
      title: '操作',
      key: 'actions',
      width: 240,
      render: (_: unknown, record: ETLTask & { engine_type?: string }) => {
        const isKettleTask = record.engine_type === 'kettle';
        return (
          <Space>
            <Button
              type="text"
              icon={<EyeOutlined />}
              onClick={() => {
                setSelectedTask(record);
                setIsDetailDrawerOpen(true);
              }}
            />
            {record.status !== 'running' && !isKettleTask && (
              <Button
                type="text"
                icon={<PlayCircleOutlined />}
                onClick={() => startMutation.mutate(record.task_id)}
                loading={startMutation.isPending}
                title="使用内置引擎执行"
              />
            )}
            {record.status !== 'running' && isKettleTask && (
              <Button
                type="text"
                icon={<ThunderboltOutlined />}
                onClick={() => executeKettleMutation.mutate(record.task_id)}
                loading={executeKettleMutation.isPending}
                disabled={!isKettleAvailable}
                title={isKettleAvailable ? '使用 Kettle 引擎执行' : 'Kettle 引擎不可用'}
                style={{ color: isKettleAvailable ? '#722ed1' : undefined }}
              />
            )}
            {record.status === 'running' && (
              <Popconfirm
                title="确定要停止这个任务吗？"
                onConfirm={() => stopMutation.mutate(record.task_id)}
                okText="确定"
                cancelText="取消"
              >
                <Button type="text" danger icon={<StopOutlined />} />
              </Popconfirm>
            )}
            <Popconfirm
              title="确定要删除这个任务吗？"
              onConfirm={() => deleteMutation.mutate(record.task_id)}
              okText="确定"
              cancelText="取消"
            >
              <Button type="text" danger icon={<DeleteOutlined />} />
            </Popconfirm>
          </Space>
        );
      },
    },
  ];

  const handleCreate = () => {
    form.validateFields().then((values) => {
      const data: CreateETLTaskRequest & {
        engine_type?: string;
        kettle_job_path?: string;
        kettle_trans_path?: string;
        kettle_repository?: string;
        kettle_directory?: string;
      } = {
        name: values.name,
        description: values.description,
        type: values.type,
        source: {
          type: values.source_type,
          source_id: values.source_id,
          table_name: values.source_table,
          query: values.source_query,
        },
        target: {
          type: values.target_type,
          target_id: values.target_id,
          table_name: values.target_table,
          mode: values.target_mode,
        },
        schedule: values.enable_schedule
          ? {
              type: values.schedule_type,
              expression: values.cron_expression,
            }
          : undefined,
        tags: values.tags,
        engine_type: values.engine_type,
        kettle_job_path: values.kettle_job_path,
        kettle_trans_path: values.kettle_trans_path,
        kettle_repository: values.kettle_repository,
        kettle_directory: values.kettle_directory,
      };
      createMutation.mutate(data);
    });
  };

  return (
    <div style={{ padding: '24px' }}>
      <Card
        title={
          <Space>
            <span>ETL 任务管理</span>
            <Tooltip title={
              kettleStatus?.enabled
                ? kettleStatus?.kettle_installed
                  ? `Kettle 已就绪 (${kettleStatus?.kettle_home || '默认路径'})`
                  : 'Kettle 未安装'
                : 'Kettle 引擎未启用'
            }>
              <Tag
                color={isKettleAvailable ? 'purple' : 'default'}
                icon={<ThunderboltOutlined />}
              >
                Kettle {isKettleAvailable ? '可用' : '不可用'}
              </Tag>
            </Tooltip>
          </Space>
        }
        extra={
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setIsCreateModalOpen(true)}>
            新建任务
          </Button>
        }
      >
        <Space style={{ marginBottom: 16 }} size="middle">
          <Select
            placeholder="状态筛选"
            allowClear
            style={{ width: 120 }}
            onChange={setStatusFilter}
            value={statusFilter || undefined}
          >
            <Option value="pending">等待中</Option>
            <Option value="running">运行中</Option>
            <Option value="completed">已完成</Option>
            <Option value="failed">失败</Option>
            <Option value="stopped">已停止</Option>
          </Select>
          <Select
            placeholder="类型筛选"
            allowClear
            style={{ width: 120 }}
            onChange={setTypeFilter}
            value={typeFilter || undefined}
          >
            <Option value="batch">批处理</Option>
            <Option value="streaming">流式</Option>
            <Option value="scheduled">定时</Option>
          </Select>
        </Space>

        <Table
          columns={columns}
          dataSource={tasksData?.data?.tasks || []}
          rowKey="task_id"
          loading={isLoadingList}
          pagination={{
            current: page,
            pageSize: pageSize,
            total: tasksData?.data?.total || 0,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 条`,
            onChange: (newPage, newPageSize) => {
              setPage(newPage);
              setPageSize(newPageSize || 10);
            },
          }}
        />
      </Card>

      {/* 创建 ETL 任务模态框 */}
      <Modal
        title="新建 ETL 任务"
        open={isCreateModalOpen}
        onOk={handleCreate}
        onCancel={() => {
          setIsCreateModalOpen(false);
          form.resetFields();
          setEngineType('builtin');
        }}
        confirmLoading={createMutation.isPending}
        width={700}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            label="任务名称"
            name="name"
            rules={[{ required: true, message: '请输入任务名称' }]}
          >
            <Input placeholder="请输入任务名称" />
          </Form.Item>
          <Form.Item label="描述" name="description">
            <TextArea rows={2} placeholder="请输入描述" />
          </Form.Item>
          <Form.Item
            label="任务类型"
            name="type"
            rules={[{ required: true, message: '请选择任务类型' }]}
            initialValue="batch"
          >
            <Select>
              <Option value="batch">批处理</Option>
              <Option value="streaming">流式</Option>
              <Option value="scheduled">定时任务</Option>
            </Select>
          </Form.Item>

          <Card size="small" title="数据源配置" style={{ marginBottom: 16 }}>
            <Form.Item
              label="源类型"
              name="source_type"
              rules={[{ required: true, message: '请选择源类型' }]}
              initialValue="database"
            >
              <Select>
                <Option value="database">数据库</Option>
                <Option value="file">文件</Option>
                <Option value="dataset">数据集</Option>
              </Select>
            </Form.Item>
            <Form.Item label="数据源" name="source_id">
              <Select placeholder="选择数据源" allowClear>
                {sourcesData?.data?.sources?.map((source) => (
                  <Option key={source.source_id} value={source.source_id}>
                    {source.name}
                  </Option>
                ))}
              </Select>
            </Form.Item>
            <Form.Item label="表名" name="source_table">
              <Input placeholder="请输入源表名" />
            </Form.Item>
            <Form.Item label="自定义 SQL" name="source_query">
              <TextArea rows={3} placeholder="可选：使用自定义 SQL 查询" />
            </Form.Item>
          </Card>

          <Card size="small" title="目标配置" style={{ marginBottom: 16 }}>
            <Form.Item
              label="目标类型"
              name="target_type"
              rules={[{ required: true, message: '请选择目标类型' }]}
              initialValue="dataset"
            >
              <Select>
                <Option value="database">数据库</Option>
                <Option value="file">文件</Option>
                <Option value="dataset">数据集</Option>
              </Select>
            </Form.Item>
            <Form.Item label="目标表名" name="target_table">
              <Input placeholder="请输入目标表名" />
            </Form.Item>
            <Form.Item
              label="写入模式"
              name="target_mode"
              initialValue="append"
            >
              <Select>
                <Option value="overwrite">覆盖</Option>
                <Option value="append">追加</Option>
                <Option value="merge">合并</Option>
              </Select>
            </Form.Item>
            <Form.Item label=" ">
              <Button
                type="dashed"
                icon={<RobotOutlined />}
                onClick={() => setIsAIFieldMappingOpen(true)}
                block
              >
                AI 字段映射助手
              </Button>
            </Form.Item>
          </Card>

          <Card size="small" title="执行引擎配置" style={{ marginBottom: 16 }}>
            <Form.Item
              label="执行引擎"
              name="engine_type"
              initialValue="builtin"
            >
              <Select onChange={(value) => setEngineType(value)}>
                <Option value="builtin">内置引擎</Option>
                <Option value="kettle" disabled={!isKettleAvailable}>
                  Kettle {!isKettleAvailable && '(不可用)'}
                </Option>
                <Option value="spark" disabled>Spark (即将推出)</Option>
                <Option value="flink" disabled>Flink (即将推出)</Option>
              </Select>
            </Form.Item>
            {engineType === 'kettle' && (
              <>
                <Form.Item
                  label="Kettle 作业路径"
                  name="kettle_job_path"
                  tooltip="Kettle 作业文件 (.kjb) 的路径"
                >
                  <Input placeholder="例如: /data/kettle/jobs/my_job.kjb" />
                </Form.Item>
                <Form.Item
                  label="Kettle 转换路径"
                  name="kettle_trans_path"
                  tooltip="Kettle 转换文件 (.ktr) 的路径"
                >
                  <Input placeholder="例如: /data/kettle/transformations/my_trans.ktr" />
                </Form.Item>
                <Form.Item
                  label="Repository"
                  name="kettle_repository"
                  tooltip="Kettle 资源库名称（可选）"
                >
                  <Input placeholder="资源库名称" />
                </Form.Item>
                <Form.Item
                  label="目录"
                  name="kettle_directory"
                  tooltip="资源库中的目录路径"
                >
                  <Input placeholder="例如: /home/admin" />
                </Form.Item>
              </>
            )}
          </Card>

          <Card size="small" title="调度配置">
            <Form.Item label="启用调度" name="enable_schedule" valuePropName="checked">
              <Select>
                <Option value={false}>否</Option>
                <Option value={true}>是</Option>
              </Select>
            </Form.Item>
            <Form.Item label="调度类型" name="schedule_type">
              <Select>
                <Option value="cron">Cron 表达式</Option>
                <Option value="interval">间隔</Option>
                <Option value="once">一次性</Option>
              </Select>
            </Form.Item>
            <Form.Item label="Cron 表达式" name="cron_expression">
              <Input placeholder="例如: 0 0 * * * (每天零点)" />
            </Form.Item>
          </Card>

          <Form.Item label="标签" name="tags">
            <Select mode="tags" placeholder="输入标签后按回车" />
          </Form.Item>
        </Form>
      </Modal>

      {/* 日志模态框 */}
      <Modal
        title="执行日志"
        open={isLogsModalOpen}
        onCancel={() => setIsLogsModalOpen(false)}
        footer={[
          <Button key="close" onClick={() => setIsLogsModalOpen(false)}>
            关闭
          </Button>,
        ]}
        width={800}
      >
        <pre style={{ maxHeight: 400, overflow: 'auto', background: '#f5f5f5', padding: 16 }}>
          {taskLogs || '暂无日志'}
        </pre>
      </Modal>

      {/* 任务详情抽屉 */}
      <Drawer
        title="ETL 任务详情"
        open={isDetailDrawerOpen}
        onClose={() => {
          setIsDetailDrawerOpen(false);
          setSelectedTask(null);
        }}
        width={700}
      >
        {selectedTask && (
          <div>
            <Descriptions column={2} bordered>
              <Descriptions.Item label="任务名称" span={2}>
                {selectedTask.name}
              </Descriptions.Item>
              <Descriptions.Item label="描述" span={2}>
                {selectedTask.description || '-'}
              </Descriptions.Item>
              <Descriptions.Item label="任务类型">
                <Tag color={getTypeColor(selectedTask.type)}>{getTypeText(selectedTask.type)}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="状态">
                <Tag color={getStatusColor(selectedTask.status)}>{getStatusText(selectedTask.status)}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="执行引擎" span={2}>
                <Tag
                  color={getEngineColor((selectedTask as ETLTask & { engine_type?: string }).engine_type || 'builtin')}
                  icon={getEngineIcon((selectedTask as ETLTask & { engine_type?: string }).engine_type || 'builtin')}
                >
                  {getEngineText((selectedTask as ETLTask & { engine_type?: string }).engine_type || 'builtin')}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="数据源" span={2}>
                <Tag>{selectedTask.source.type}</Tag>
                {selectedTask.source.source_id && <Tag>{selectedTask.source.source_id}</Tag>}
                {selectedTask.source.table_name && <Tag>{selectedTask.source.table_name}</Tag>}
              </Descriptions.Item>
              <Descriptions.Item label="目标" span={2}>
                <Tag>{selectedTask.target.type}</Tag>
                {selectedTask.target.target_id && <Tag>{selectedTask.target.target_id}</Tag>}
                {selectedTask.target.table_name && <Tag>{selectedTask.target.table_name}</Tag>}
              </Descriptions.Item>
              {selectedTask.schedule && (
                <>
                  <Descriptions.Item label="调度类型">
                    <Tag icon={<ScheduleOutlined />}>{selectedTask.schedule.type}</Tag>
                  </Descriptions.Item>
                  <Descriptions.Item label="调度表达式">
                    {selectedTask.schedule.expression || '-'}
                  </Descriptions.Item>
                </>
              )}
              {selectedTask.last_run && (
                <Descriptions.Item label="最后运行">
                  {dayjs(selectedTask.last_run).format('YYYY-MM-DD HH:mm')}
                </Descriptions.Item>
              )}
              {selectedTask.next_run && (
                <Descriptions.Item label="下次运行">
                  {dayjs(selectedTask.next_run).format('YYYY-MM-DD HH:mm')}
                </Descriptions.Item>
              )}
              <Descriptions.Item label="创建时间" span={2}>
                {dayjs(selectedTask.created_at).format('YYYY-MM-DD HH:mm')}
              </Descriptions.Item>
              <Descriptions.Item label="标签" span={2}>
                {selectedTask.tags?.map((tag) => (
                  <Tag key={tag} color="blue">
                    {tag}
                  </Tag>
                ))}
              </Descriptions.Item>
            </Descriptions>

            {selectedTask.statistics && (
              <div style={{ marginTop: 16 }}>
                <Card size="small" title="运行统计">
                  <Row gutter={16}>
                    <Col span={6}>
                      <Statistic title="总运行次数" value={selectedTask.statistics.total_runs} />
                    </Col>
                    <Col span={6}>
                      <Statistic
                        title="成功次数"
                        value={selectedTask.statistics.success_runs}
                        valueStyle={{ color: '#3f8600' }}
                      />
                    </Col>
                    <Col span={6}>
                      <Statistic
                        title="失败次数"
                        value={selectedTask.statistics.failed_runs}
                        valueStyle={{ color: selectedTask.statistics.failed_runs > 0 ? '#cf1322' : undefined }}
                      />
                    </Col>
                    <Col span={6}>
                      {selectedTask.statistics.last_duration_ms && (
                        <Statistic
                          title="上次耗时"
                          value={(selectedTask.statistics.last_duration_ms / 1000).toFixed(2)}
                          suffix="秒"
                        />
                      )}
                    </Col>
                  </Row>
                  {selectedTask.statistics.rows_processed && (
                    <Row gutter={16} style={{ marginTop: 16 }}>
                      <Col span={12}>
                        <Statistic
                          title="处理行数"
                          value={selectedTask.statistics.rows_processed}
                          formatter={(value) => `${value?.toLocaleString()}`}
                        />
                      </Col>
                      {selectedTask.statistics.bytes_processed && (
                        <Col span={12}>
                          <Statistic
                            title="处理数据量"
                            value={(selectedTask.statistics.bytes_processed / 1024 / 1024).toFixed(2)}
                            suffix="MB"
                          />
                        </Col>
                      )}
                    </Row>
                  )}
                </Card>
              </div>
            )}

            {/* Kettle 配置信息 */}
            {(selectedTask as ETLTask & { engine_type?: string; kettle_job_path?: string; kettle_trans_path?: string; kettle_repository?: string; kettle_directory?: string }).engine_type === 'kettle' && (
              <div style={{ marginTop: 16 }}>
                <Card size="small" title={<><ThunderboltOutlined style={{ marginRight: 8 }} />Kettle 配置</>}>
                  <Descriptions column={1} size="small">
                    {(selectedTask as ETLTask & { kettle_job_path?: string }).kettle_job_path && (
                      <Descriptions.Item label="作业路径">
                        <code>{(selectedTask as ETLTask & { kettle_job_path?: string }).kettle_job_path}</code>
                      </Descriptions.Item>
                    )}
                    {(selectedTask as ETLTask & { kettle_trans_path?: string }).kettle_trans_path && (
                      <Descriptions.Item label="转换路径">
                        <code>{(selectedTask as ETLTask & { kettle_trans_path?: string }).kettle_trans_path}</code>
                      </Descriptions.Item>
                    )}
                    {(selectedTask as ETLTask & { kettle_repository?: string }).kettle_repository && (
                      <Descriptions.Item label="资源库">
                        {(selectedTask as ETLTask & { kettle_repository?: string }).kettle_repository}
                      </Descriptions.Item>
                    )}
                    {(selectedTask as ETLTask & { kettle_directory?: string }).kettle_directory && (
                      <Descriptions.Item label="目录">
                        {(selectedTask as ETLTask & { kettle_directory?: string }).kettle_directory}
                      </Descriptions.Item>
                    )}
                  </Descriptions>
                </Card>
              </div>
            )}

            <div style={{ marginTop: 24, textAlign: 'right' }}>
              <Space>
                <Button
                  icon={<FileTextOutlined />}
                  onClick={() => handleViewLogs(selectedTask)}
                >
                  查看日志
                </Button>
                {selectedTask.status !== 'running' && (selectedTask as ETLTask & { engine_type?: string }).engine_type !== 'kettle' && (
                  <Button
                    type="primary"
                    icon={<PlayCircleOutlined />}
                    onClick={() => startMutation.mutate(selectedTask.task_id)}
                    loading={startMutation.isPending}
                  >
                    立即运行
                  </Button>
                )}
                {selectedTask.status !== 'running' && (selectedTask as ETLTask & { engine_type?: string }).engine_type === 'kettle' && (
                  <Button
                    type="primary"
                    icon={<ThunderboltOutlined />}
                    onClick={() => executeKettleMutation.mutate(selectedTask.task_id)}
                    loading={executeKettleMutation.isPending}
                    disabled={!isKettleAvailable}
                    style={{ backgroundColor: isKettleAvailable ? '#722ed1' : undefined, borderColor: isKettleAvailable ? '#722ed1' : undefined }}
                  >
                    Kettle 执行
                  </Button>
                )}
                {selectedTask.status === 'running' && (
                  <Popconfirm
                    title="确定要停止这个任务吗？"
                    onConfirm={() => stopMutation.mutate(selectedTask.task_id)}
                    okText="确定"
                    cancelText="取消"
                  >
                    <Button danger icon={<StopOutlined />}>
                      停止
                    </Button>
                  </Popconfirm>
                )}
                <Popconfirm
                  title="确定要删除这个任务吗？"
                  onConfirm={() => deleteMutation.mutate(selectedTask.task_id)}
                  okText="确定"
                  cancelText="取消"
                >
                  <Button danger icon={<DeleteOutlined />}>
                    删除
                  </Button>
                </Popconfirm>
              </Space>
            </div>
          </div>
        )}
      </Drawer>

      {/* AI 字段映射模态框 */}
      <AIFieldMappingPanel
        sourceFields={sourceFields}
        targetFields={targetFields}
        sourceTable={form.getFieldValue('source_table')}
        targetTable={form.getFieldValue('target_table')}
        visible={isAIFieldMappingOpen}
        onClose={() => setIsAIFieldMappingOpen(false)}
        onMappingApply={(mappings) => {
          console.log('Applied mappings:', mappings);
          // 这里可以处理映射应用逻辑
          message.success(`已应用 ${mappings.length} 个字段映射`);
        }}
      />
    </div>
  );
}

export default ETLPage;
