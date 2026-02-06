/**
 * 工作流编辑器组件
 * 支持可视化工作流编辑和 DolphinScheduler 集成
 */

import React, { useState, useCallback } from 'react';
import {
  Card,
  Button,
  Space,
  Table,
  Modal,
  Form,
  Input,
  Select,
  Tag,
  message,
  Popconfirm,
  Row,
  Col,
} from 'antd';
import {
  PlusOutlined,
  PlayCircleOutlined,
  EditOutlined,
  DeleteOutlined,
  NodeIndexOutlined,
} from '@ant-design/icons';
import { useMutation } from '@tanstack/react-query';
import { schedulerApi, WorkflowTask } from '../services/scheduler';

const { Option } = Select;
const { TextArea } = Input;

interface WorkflowEditorProps {
  className?: string;
}

/**
 * 工作流编辑器
 */
const WorkflowEditor: React.FC<WorkflowEditorProps> = ({ className }) => {
  const [tasks, setTasks] = useState<WorkflowTask[]>([]);
  const [editingTask, setEditingTask] = useState<WorkflowTask | null>(null);
  const [editModalVisible, setEditModalVisible] = useState(false);
  const [runModalVisible, setRunModalVisible] = useState(false);
  const [form] = Form.useForm();
  const [runForm] = Form.useForm();

  // 运行工作流
  const runWorkflowMutation = useMutation({
    mutationFn: ({ workflowId, params }: { workflowId: string; params?: Record<string, unknown> }) =>
      schedulerApi.runWorkflow(workflowId, params),
    onSuccess: (response: unknown) => {
      const responseData = (response as { data?: { data?: { instance_id?: string }; instance_id?: string } })?.data;
      const instanceId = responseData?.data?.instance_id || responseData?.instance_id;
      message.success(`工作流已启动，实例 ID: ${instanceId}`);
      setRunModalVisible(false);
      runForm.resetFields();
    },
    onError: (error: unknown) => {
      const errMsg = (error as { message?: string })?.message || '未知错误';
      message.error(`启动失败: ${errMsg}`);
    },
  });

  // 创建工作流
  const createWorkflowMutation = useMutation({
    mutationFn: (data: { name: string; description?: string; tasks: WorkflowTask[] }) =>
      schedulerApi.createWorkflow(data),
    onSuccess: (response: unknown) => {
      const responseData = (response as { data?: { data?: { workflow_id?: string }; workflow_id?: string } })?.data;
      const workflowId = responseData?.data?.workflow_id || responseData?.workflow_id;
      message.success(`工作流创建成功: ${workflowId}`);
      // 可以直接运行
      setRunModalVisible(true);
      runForm.setFieldsValue({ workflow_id: workflowId });
    },
    onError: (error: unknown) => {
      const errMsg = (error as { message?: string })?.message || '未知错误';
      message.error(`创建失败: ${errMsg}`);
    },
  });

  // 打开编辑弹窗
  const handleEdit = (task?: WorkflowTask) => {
    if (task) {
      setEditingTask(task);
      form.setFieldsValue(task);
    } else {
      setEditingTask(null);
      form.resetFields();
    }
    setEditModalVisible(true);
  };

  // 保存任务
  const handleSaveTask = useCallback(() => {
    form.validateFields().then((values) => {
      const newTask: WorkflowTask = {
        ...values,
        dependencies: values.dependencies || [],
      };

      if (editingTask) {
        // 更新
        setTasks(tasks.map((t) => (t.name === editingTask.name ? newTask : t)));
        message.success('任务已更新');
      } else {
        // 新增
        setTasks([...tasks, newTask]);
        message.success('任务已添加');
      }

      setEditModalVisible(false);
      form.resetFields();
      setEditingTask(null);
    });
  }, [form, editingTask, tasks]);

  // 删除任务
  const handleDelete = (taskName: string) => {
    setTasks(tasks.filter((t) => t.name !== taskName));
    message.success('任务已删除');
  };

  // 保存并运行工作流
  const handleSaveAndRun = useCallback(() => {
    if (tasks.length === 0) {
      message.warning('请先添加任务');
      return;
    }

    const workflowName = `workflow_${Date.now()}`;
    createWorkflowMutation.mutate({
      name: workflowName,
      description: '通过可视化编辑器创建的工作流',
      tasks,
    });
  }, [tasks, createWorkflowMutation]);

  // 运行工作流
  const handleRun = () => {
    runForm.validateFields().then((values) => {
      runWorkflowMutation.mutate({
        workflowId: values.workflow_id,
        params: values.params,
      });
    });
  };

  const columns = [
    {
      title: '任务名称',
      dataIndex: 'name',
      key: 'name',
      render: (text: string) => <strong>{text}</strong>,
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      render: (type: string) => {
        const colors: Record<string, string> = {
          shell: 'blue',
          sql: 'green',
          python: 'orange',
          http: 'purple',
          celery_task: 'cyan',
        };
        return <Tag color={colors[type] || 'default'}>{type}</Tag>;
      },
    },
    {
      title: '优先级',
      dataIndex: 'priority',
      key: 'priority',
      render: (priority: string) => {
        const colors: Record<string, string> = {
          critical: 'red',
          high: 'orange',
          normal: 'blue',
          low: 'default',
        };
        return <Tag color={colors[priority] || 'default'}>{priority || 'normal'}</Tag>;
      },
    },
    {
      title: '依赖',
      dataIndex: 'dependencies',
      key: 'dependencies',
      render: (deps: string[]) => (
        <>
          {deps?.map((dep) => (
            <Tag key={dep}>{dep}</Tag>
          ))}
        </>
      ),
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: '操作',
      key: 'actions',
      width: 150,
      render: (_: unknown, record: WorkflowTask) => (
        <Space>
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          >
            编辑
          </Button>
          <Popconfirm
            title="确定删除此任务？"
            onConfirm={() => handleDelete(record.name)}
            okText="确定"
            cancelText="取消"
          >
            <Button type="link" size="small" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div className={className}>
      <Card
        title={
          <Space>
            <NodeIndexOutlined />
            工作流编辑器
          </Space>
        }
        extra={
          <Space>
            <Button icon={<PlusOutlined />} type="primary" onClick={() => handleEdit()}>
              添加任务
            </Button>
            <Button
              icon={<PlayCircleOutlined />}
              type="primary"
              onClick={handleSaveAndRun}
              disabled={tasks.length === 0}
              loading={createWorkflowMutation.isPending}
            >
              保存并运行
            </Button>
          </Space>
        }
      >
        {tasks.length === 0 ? (
          <div
            style={{
              textAlign: 'center',
              padding: '40px',
              color: '#999',
            }}
          >
            <NodeIndexOutlined style={{ fontSize: 48, marginBottom: 16 }} />
            <p>暂无任务，点击"添加任务"开始创建工作流</p>
          </div>
        ) : (
          <Table
            columns={columns}
            dataSource={tasks}
            rowKey="name"
            pagination={false}
          />
        )}
      </Card>

      {/* 编辑任务弹窗 */}
      <Modal
        title={editingTask ? '编辑任务' : '添加任务'}
        open={editModalVisible}
        onOk={handleSaveTask}
        onCancel={() => {
          setEditModalVisible(false);
          form.resetFields();
          setEditingTask(null);
        }}
        width={600}
        destroyOnClose
      >
        <Form
          form={form}
          layout="vertical"
          initialValues={{
            type: 'shell',
            priority: 'normal',
            dependencies: [],
          }}
        >
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="name"
                label="任务名称"
                rules={[{ required: true, message: '请输入任务名称' }]}
              >
                <Input placeholder="任务名称" disabled={!!editingTask} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="type"
                label="任务类型"
                rules={[{ required: true, message: '请选择任务类型' }]}
              >
                <Select placeholder="选择类型">
                  <Option value="shell">Shell 脚本</Option>
                  <Option value="sql">SQL 查询</Option>
                  <Option value="python">Python 脚本</Option>
                  <Option value="http">HTTP 请求</Option>
                  <Option value="celery_task">Celery 任务</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="description"
            label="任务描述"
          >
            <Input placeholder="任务描述" />
          </Form.Item>

          <Form.Item
            noStyle
            shouldUpdate={(prev, curr) => prev.type !== curr.type}
          >
            {({ getFieldValue }) => {
              const type = getFieldValue('type');

              if (type === 'shell' || type === 'python') {
                return (
                  <Form.Item
                    name="script_content"
                    label="脚本内容"
                    rules={[{ required: true, message: '请输入脚本内容' }]}
                  >
                    <TextArea
                      rows={8}
                      placeholder={type === 'shell' ? '#!/bin/bash\n...' : '#!/usr/bin/env python\n...'}
                    />
                  </Form.Item>
                );
              }

              if (type === 'sql') {
                return (
                  <Form.Item
                    name="sql_query"
                    label="SQL 查询"
                    rules={[{ required: true, message: '请输入 SQL 查询' }]}
                  >
                    <TextArea rows={8} placeholder="SELECT * FROM table WHERE..." />
                  </Form.Item>
                );
              }

              if (type === 'http') {
                return (
                  <>
                    <Form.Item name="http_url" label="URL" rules={[{ required: true }]}>
                      <Input placeholder="https://api.example.com/endpoint" />
                    </Form.Item>
                    <Form.Item name="http_method" label="方法" initialValue="GET">
                      <Select>
                        <Option value="GET">GET</Option>
                        <Option value="POST">POST</Option>
                        <Option value="PUT">PUT</Option>
                        <Option value="DELETE">DELETE</Option>
                      </Select>
                    </Form.Item>
                  </>
                );
              }

              if (type === 'celery_task') {
                return (
                  <Form.Item
                    name="celery_task_name"
                    label="Celery 任务名称"
                    rules={[{ required: true, message: '请输入 Celery 任务名称' }]}
                  >
                    <Input placeholder="services.shared.celery_tasks.task_name" />
                  </Form.Item>
                );
              }

              return null;
            }}
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="priority"
                label="优先级"
              >
                <Select>
                  <Option value="low">低</Option>
                  <Option value="normal">普通</Option>
                  <Option value="high">高</Option>
                  <Option value="critical">紧急</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="dependencies"
                label="依赖任务"
              >
                <Select
                  mode="tags"
                  placeholder="选择依赖的任务"
                >
                  {tasks.map((t) => (
                    <Option key={t.name} value={t.name}>
                      {t.name}
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>

      {/* 运行工作流弹窗 */}
      <Modal
        title="运行工作流"
        open={runModalVisible}
        onOk={handleRun}
        onCancel={() => setRunModalVisible(false)}
        confirmLoading={runWorkflowMutation.isPending}
      >
        <Form form={runForm} layout="vertical">
          <Form.Item name="workflow_id" label="工作流 ID" hidden>
            <Input />
          </Form.Item>
          <Form.Item name="params" label="运行参数">
            <TextArea rows={4} placeholder='{"key": "value"}' />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default WorkflowEditor;
