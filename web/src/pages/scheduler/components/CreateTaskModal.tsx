/**
 * 创建任务弹窗组件
 */

import React from 'react';
import {
  Modal,
  Form,
  Input,
  Select,
  InputNumber,
  Switch,
  Space,
  Button,
  message,
} from 'antd';
import { useMutation } from '@tanstack/react-query';
import { schedulerApi, TaskSubmitRequest } from '../services/scheduler';

const { Option } = Select;
const { TextArea } = Input;

interface CreateTaskModalProps {
  visible: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

/**
 * 创建任务弹窗
 */
const CreateTaskModal: React.FC<CreateTaskModalProps> = ({
  visible,
  onClose,
  onSuccess,
}) => {
  const [form] = Form.useForm();

  const createMutation = useMutation({
    mutationFn: (data: TaskSubmitRequest) => schedulerApi.submitTask(data),
    onSuccess: () => {
      message.success('任务已提交');
      form.resetFields();
      onSuccess();
    },
    onError: (error: unknown) => {
      const errMsg = (error as { message?: string })?.message || '未知错误';
      message.error(`提交失败: ${errMsg}`);
    },
  });

  const handleSubmit = () => {
    form.validateFields().then((values) => {
      createMutation.mutate(values);
    });
  };

  return (
    <Modal
      title="创建任务"
      open={visible}
      onCancel={onClose}
      onOk={handleSubmit}
      confirmLoading={createMutation.isPending}
      width={700}
      destroyOnClose
    >
      <Form
        form={form}
        layout="vertical"
        initialValues={{
          type: 'celery_task',
          priority: 'normal',
          engine: 'auto',
          timeout: 3600,
          retry_count: 3,
        }}
      >
        <Form.Item
          name="name"
          label="任务名称"
          rules={[{ required: true, message: '请输入任务名称' }]}
        >
          <Input placeholder="任务名称" />
        </Form.Item>

        <Form.Item
          name="type"
          label="任务类型"
          rules={[{ required: true }]}
        >
          <Select>
            <Option value="celery_task">Celery 任务</Option>
            <Option value="shell">Shell 脚本</Option>
            <Option value="sql">SQL 查询</Option>
            <Option value="python">Python 脚本</Option>
            <Option value="http">HTTP 请求</Option>
          </Select>
        </Form.Item>

        <Form.Item noStyle shouldUpdate={(prev, curr) => prev.type !== curr.type}>
          {({ getFieldValue }) => {
            const type = getFieldValue('type');

            if (type === 'celery_task') {
              return (
                <Form.Item
                  name="celery_task_name"
                  label="Celery 任务名称"
                  rules={[{ required: true }]}
                >
                  <Input placeholder="services.shared.celery_tasks.task_name" />
                </Form.Item>
              );
            }

            if (type === 'shell' || type === 'python') {
              return (
                <Form.Item
                  name="script_content"
                  label="脚本内容"
                  rules={[{ required: true }]}
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
                <Form.Item name="sql_query" label="SQL 查询" rules={[{ required: true }]}>
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

            return null;
          }}
        </Form.Item>

        <Form.Item name="description" label="描述">
          <Input placeholder="任务描述" />
        </Form.Item>

        <Form.Item name="parameters" label="参数 (JSON)">
          <TextArea rows={3} placeholder='{"key": "value"}' />
        </Form.Item>

        <Space>
          <Form.Item name="priority" label="优先级" style={{ marginBottom: 0 }}>
            <Select style={{ width: 120 }}>
              <Option value="low">低</Option>
              <Option value="normal">普通</Option>
              <Option value="high">高</Option>
              <Option value="critical">紧急</Option>
            </Select>
          </Form.Item>

          <Form.Item name="engine" label="调度引擎" style={{ marginBottom: 0 }}>
            <Select style={{ width: 150 }}>
              <Option value="auto">自动选择</Option>
              <Option value="celery">Celery</Option>
              <Option value="dolphinscheduler">DolphinScheduler</Option>
              <Option value="smart">智能调度</Option>
            </Select>
          </Form.Item>

          <Form.Item
            name="timeout"
            label="超时(秒)"
            style={{ marginBottom: 0 }}
          >
            <InputNumber min={1} max={86400} style={{ width: 100 }} />
          </Form.Item>
        </Space>
      </Form>
    </Modal>
  );
};

export default CreateTaskModal;
