import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Card,
  Button,
  Table,
  Tag,
  Space,
  Modal,
  Form,
  Input,
  Select,
  message,
  Popconfirm,
} from 'antd';
import {
  PlusOutlined,
  PlayCircleOutlined,
  StopOutlined,
  EditOutlined,
  DeleteOutlined,
  EyeOutlined,
  HistoryOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import dayjs from 'dayjs';
import agentService from '@/services/agent-service';
import type { Workflow } from '@/services/agent-service';

const { Option } = Select;
const { TextArea } = Input;

function WorkflowsPage() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [selectedWorkflow, setSelectedWorkflow] = useState<Workflow | null>(null);
  const [isDetailModalOpen, setIsDetailModalOpen] = useState(false);

  const [form] = Form.useForm();

  // 获取工作流列表
  const { data: workflowsData, isLoading } = useQuery({
    queryKey: ['workflows'],
    queryFn: agentService.getWorkflows,
  });

  // 创建工作流
  const createMutation = useMutation({
    mutationFn: agentService.createWorkflow,
    onSuccess: () => {
      message.success('工作流创建成功');
      setIsCreateModalOpen(false);
      form.resetFields();
      queryClient.invalidateQueries({ queryKey: ['workflows'] });
    },
    onError: () => {
      message.error('工作流创建失败');
    },
  });

  // 启动工作流
  const startMutation = useMutation({
    mutationFn: (workflowId: string) => agentService.startWorkflow(workflowId),
    onSuccess: () => {
      message.success('工作流已启动');
      queryClient.invalidateQueries({ queryKey: ['workflows'] });
    },
    onError: () => {
      message.error('启动工作流失败');
    },
  });

  // 停止工作流
  const stopMutation = useMutation({
    mutationFn: (workflowId: string) => agentService.stopWorkflow(workflowId, { execution_id: '' }),
    onSuccess: () => {
      message.success('工作流已停止');
      queryClient.invalidateQueries({ queryKey: ['workflows'] });
    },
    onError: () => {
      message.error('停止工作流失败');
    },
  });

  // 删除工作流
  const deleteMutation = useMutation({
    mutationFn: agentService.deleteWorkflow,
    onSuccess: () => {
      message.success('工作流删除成功');
      setIsDetailModalOpen(false);
      queryClient.invalidateQueries({ queryKey: ['workflows'] });
    },
  });

  const handleCreate = () => {
    // 直接跳转到可视化编辑器
    navigate('/workflows/new');
  };

  const handleEdit = (workflowId: string) => {
    navigate(`/workflows/${workflowId}/edit`);
  };

  const getStatusTag = (status: Workflow['status']) => {
    const statusConfig = {
      running: { color: 'green', text: '运行中' },
      stopped: { color: 'default', text: '已停止' },
      error: { color: 'red', text: '错误' },
      pending: { color: 'orange', text: '等待中' },
    };
    const config = statusConfig[status] || { color: 'default', text: status };
    return <Tag color={config.color}>{config.text}</Tag>;
  };

  const getTypeTag = (type: Workflow['type']) => {
    const typeConfig = {
      rag: { color: 'blue', text: 'RAG' },
      text2sql: { color: 'purple', text: 'Text2SQL' },
      custom: { color: 'cyan', text: '自定义' },
    };
    const config = typeConfig[type] || { color: 'default', text: type };
    return <Tag color={config.color}>{config.text}</Tag>;
  };

  const columns = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: Workflow) => (
        <a
          onClick={() => {
            setSelectedWorkflow(record);
            setIsDetailModalOpen(true);
          }}
        >
          {name}
        </a>
      ),
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
      render: (desc: string) => desc || '-',
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      width: 120,
      render: (type: Workflow['type']) => getTypeTag(type),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (status: Workflow['status']) => getStatusTag(status),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (date: string) => dayjs(date).format('YYYY-MM-DD HH:mm'),
    },
    {
      title: '操作',
      key: 'actions',
      width: 250,
      render: (_: unknown, record: Workflow) => (
        <Space>
          <Button
            type="text"
            icon={<EyeOutlined />}
            onClick={() => {
              setSelectedWorkflow(record);
              setIsDetailModalOpen(true);
            }}
          />
          <Button
            type="text"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record.workflow_id)}
            title="编辑"
          >
            编辑
          </Button>
          <Button
            type="text"
            icon={<HistoryOutlined />}
            onClick={() => navigate(`/workflows/${record.workflow_id}/executions`)}
            title="执行历史"
          >
            执行
          </Button>
          {record.status === 'running' || record.status === 'pending' ? (
            <Popconfirm
              title="确定要停止这个工作流吗？"
              onConfirm={() => stopMutation.mutate(record.workflow_id)}
              okText="确定"
              cancelText="取消"
            >
              <Button type="text" icon={<StopOutlined />} danger />
            </Popconfirm>
          ) : (
            <Popconfirm
              title="确定要启动这个工作流吗？"
              onConfirm={() => startMutation.mutate(record.workflow_id)}
              okText="确定"
              cancelText="取消"
            >
              <Button type="text" icon={<PlayCircleOutlined />} />
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: '24px' }}>
      <Card
        title="工作流管理"
        extra={
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setIsCreateModalOpen(true)}>
            新建工作流
          </Button>
        }
      >
        <Table
          columns={columns}
          dataSource={workflowsData?.data?.workflows || []}
          rowKey="workflow_id"
          loading={isLoading}
          pagination={{
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 条`,
          }}
        />
      </Card>

      {/* 创建工作流模态框 */}
      <Modal
        title="新建工作流"
        open={isCreateModalOpen}
        onOk={handleCreate}
        onCancel={() => {
          setIsCreateModalOpen(false);
          form.resetFields();
        }}
        confirmLoading={createMutation.isPending}
        width={600}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            label="工作流名称"
            name="name"
            rules={[{ required: true, message: '请输入工作流名称' }]}
          >
            <Input placeholder="请输入工作流名称" />
          </Form.Item>
          <Form.Item label="描述" name="description">
            <TextArea rows={3} placeholder="请输入描述" />
          </Form.Item>
          <Form.Item
            label="工作流类型"
            name="type"
            rules={[{ required: true, message: '请选择工作流类型' }]}
          >
            <Select placeholder="请选择工作流类型">
              <Option value="rag">RAG - 检索增强生成</Option>
              <Option value="text2sql">Text2SQL - 自然语言转 SQL</Option>
              <Option value="custom">自定义</Option>
            </Select>
          </Form.Item>
        </Form>
      </Modal>

      {/* 工作流详情模态框 */}
      <Modal
        title="工作流详情"
        open={isDetailModalOpen}
        onCancel={() => {
          setIsDetailModalOpen(false);
          setSelectedWorkflow(null);
        }}
        footer={[
          <Button
            key="executions"
            icon={<HistoryOutlined />}
            onClick={() => {
              setIsDetailModalOpen(false);
              navigate(`/workflows/${selectedWorkflow?.workflow_id}/executions`);
            }}
          >
            执行历史
          </Button>,
          selectedWorkflow?.status === 'running' || selectedWorkflow?.status === 'pending' ? (
            <Popconfirm
              key="stop"
              title="确定要停止这个工作流吗？"
              onConfirm={() => selectedWorkflow?.workflow_id && stopMutation.mutate(selectedWorkflow.workflow_id)}
              okText="确定"
              cancelText="取消"
            >
              <Button danger icon={<StopOutlined />}>
                停止
              </Button>
            </Popconfirm>
          ) : (
            <Popconfirm
              key="start"
              title="确定要启动这个工作流吗？"
              onConfirm={() => selectedWorkflow?.workflow_id && startMutation.mutate(selectedWorkflow.workflow_id)}
              okText="确定"
              cancelText="取消"
            >
              <Button type="primary" icon={<PlayCircleOutlined />}>
                启动
              </Button>
            </Popconfirm>
          ),
          <Popconfirm
            key="delete"
            title="确定要删除这个工作流吗？"
            onConfirm={() => selectedWorkflow?.workflow_id && deleteMutation.mutate(selectedWorkflow.workflow_id)}
            okText="确定"
            cancelText="取消"
          >
            <Button danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>,
          <Button key="close" onClick={() => setIsDetailModalOpen(false)}>
            关闭
          </Button>,
        ]}
        width={600}
      >
        {selectedWorkflow && (
          <div>
            <p>
              <strong>名称：</strong>
              {selectedWorkflow.name}
            </p>
            <p>
              <strong>描述：</strong>
              {selectedWorkflow.description || '-'}
            </p>
            <p>
              <strong>类型：</strong>
              {getTypeTag(selectedWorkflow.type)}
            </p>
            <p>
              <strong>状态：</strong>
              {getStatusTag(selectedWorkflow.status)}
            </p>
            <p>
              <strong>创建时间：</strong>
              {dayjs(selectedWorkflow.created_at).format('YYYY-MM-DD HH:mm:ss')}
            </p>
            <p>
              <strong>更新时间：</strong>
              {dayjs(selectedWorkflow.updated_at).format('YYYY-MM-DD HH:mm:ss')}
            </p>
          </div>
        )}
      </Modal>
    </div>
  );
}

export default WorkflowsPage;
