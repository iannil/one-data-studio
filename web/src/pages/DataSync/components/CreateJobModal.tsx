/**
 * 创建 CDC 任务弹窗组件
 */

import React from 'react';
import {
  Modal,
  Form,
  Input,
  Select,
  InputNumber,
  Steps,
  Button,
  Space,
  message,
  Card,
} from 'antd';
import { useMutation } from '@tanstack/react-query';
import { cdcApi, CreateCDCJobRequest } from '../services/cdc';

const { Option } = Select;
const { TextArea } = Input;

interface CreateJobModalProps {
  visible: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

/**
 * 创建任务弹窗
 */
const CreateJobModal: React.FC<CreateJobModalProps> = ({ visible, onClose, onSuccess }) => {
  const [form] = Form.useForm();
  const [currentStep, setCurrentStep] = React.useState(0);

  const createMutation = useMutation({
    mutationFn: (data: CreateCDCJobRequest) => cdcApi.createJob(data),
    onSuccess: () => {
      message.success('CDC 任务创建成功');
      form.resetFields();
      setCurrentStep(0);
      onSuccess();
    },
    onError: (error: unknown) => {
      const errMsg = (error as { message?: string })?.message || '未知错误';
      message.error(`创建失败: ${errMsg}`);
    },
  });

  const handleNext = async () => {
    try {
      await form.validateFields();
      setCurrentStep(currentStep + 1);
    } catch (error) {
      // Validation failed
    }
  };

  const handlePrev = () => {
    setCurrentStep(currentStep - 1);
  };

  const handleSubmit = () => {
    form.validateFields().then((values) => {
      createMutation.mutate(values);
    });
  };

  const steps = [
    {
      title: '基本信息',
      content: (
        <>
          <Form.Item name="job_name" label="任务名称" rules={[{ required: true }]}>
            <Input placeholder="cdc_mysql_to_minio" />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <TextArea rows={3} placeholder="任务描述" />
          </Form.Item>
        </>
      ),
    },
    {
      title: '数据源配置',
      content: (
        <>
          <Form.Item
            name={['source', 'type']}
            label="源类型"
            rules={[{ required: true }]}
            initialValue="MySQL-CDC"
          >
            <Select>
              <Option value="MySQL-CDC">MySQL CDC</Option>
              <Option value="PostgreSQL-CDC">PostgreSQL CDC</Option>
              <Option value="MongoDB-CDC">MongoDB CDC</Option>
              <Option value="Oracle-CDC">Oracle CDC</Option>
            </Select>
          </Form.Item>

          <Form.Item noStyle shouldUpdate={(prev, curr) => prev.source?.type !== curr.source?.type}>
            {({ getFieldValue }) => {
              const sourceType = getFieldValue(['source', 'type']);
              if (sourceType === 'MySQL-CDC') {
                return (
                  <>
                    <Form.Item name={['source', 'host']} label="主机" rules={[{ required: true }]}>
                      <Input placeholder="localhost" />
                    </Form.Item>
                    <Form.Item name={['source', 'port']} label="端口" rules={[{ required: true }]} initialValue={3306}>
                      <InputNumber style={{ width: '100%' }} />
                    </Form.Item>
                    <Form.Item name={['source', 'username']} label="用户名" rules={[{ required: true }]}>
                      <Input placeholder="root" />
                    </Form.Item>
                    <Form.Item name={['source', 'password']} label="密码" rules={[{ required: true }]}>
                      <Input.Password />
                    </Form.Item>
                    <Form.Item name={['source', 'database']} label="数据库" rules={[{ required: true }]}>
                      <Input placeholder="onedata" />
                    </Form.Item>
                    <Form.Item name={['source', 'tables']} label="表名" rules={[{ required: true }]}>
                      <Select mode="tags" placeholder="输入表名，如 users, orders" />
                    </Form.Item>
                  </>
                );
              }
              return null;
            }}
          </Form.Item>
        </>
      ),
    },
    {
      title: '目标配置',
      content: (
        <>
          <Form.Item
            name={['sink', 'type']}
            label="目标类型"
            rules={[{ required: true }]}
            initialValue="AiO"
          >
            <Select>
              <Option value="AiO">MinIO/S3 对象存储</Option>
              <Option value="ClickHouse">ClickHouse</Option>
              <Option value="Kafka">Kafka</Option>
              <Option value="Elasticsearch">Elasticsearch</Option>
              <Option value="Jdbc">JDBC (MySQL/PostgreSQL)</Option>
              <Option value="MongoDB">MongoDB</Option>
            </Select>
          </Form.Item>

          <Form.Item noStyle shouldUpdate={(prev, curr) => prev.sink?.type !== curr.sink?.type}>
            {({ getFieldValue }) => {
              const sinkType = getFieldValue(['sink', 'type']);
              if (sinkType === 'AiO') {
                return (
                  <>
                    <Form.Item name={['sink', 'endpoint']} label="端点" rules={[{ required: true }]}>
                      <Input placeholder="http://localhost:9000" />
                    </Form.Item>
                    <Form.Item name={['sink', 'bucket']} label="存储桶" rules={[{ required: true }]}>
                      <Input placeholder="one-data-lake" />
                    </Form.Item>
                    <Form.Item name={['sink', 'path']} label="路径" rules={[{ required: true }]}>
                      <Input placeholder="cdc/mysql/" />
                    </Form.Item>
                    <Form.Item name={['sink', 'access_key']} label="Access Key" rules={[{ required: true }]}>
                      <Input />
                    </Form.Item>
                    <Form.Item name={['sink', 'secret_key']} label="Secret Key" rules={[{ required: true }]}>
                      <Input.Password />
                    </Form.Item>
                  </>
                );
              }
              if (sinkType === 'ClickHouse') {
                return (
                  <>
                    <Form.Item name={['sink', 'host']} label="主机" rules={[{ required: true }]}>
                      <Input placeholder="localhost" />
                    </Form.Item>
                    <Form.Item name={['sink', 'port']} label="端口" rules={[{ required: true }]} initialValue={8123}>
                      <InputNumber style={{ width: '100%' }} />
                    </Form.Item>
                    <Form.Item name={['sink', 'database']} label="数据库" rules={[{ required: true }]}>
                      <Input placeholder="analytics" />
                    </Form.Item>
                    <Form.Item name={['sink', 'table']} label="表名" rules={[{ required: true }]}>
                      <Input placeholder="${database}_${table}" />
                    </Form.Item>
                    <Form.Item name={['sink', 'username']} label="用户名">
                      <Input placeholder="default" />
                    </Form.Item>
                    <Form.Item name={['sink', 'password']} label="密码">
                      <Input.Password />
                    </Form.Item>
                  </>
                );
              }
              return null;
            }}
          </Form.Item>
        </>
      ),
    },
    {
      title: '高级配置',
      content: (
        <>
          <Form.Item name="parallelism" label="并行度" initialValue={2}>
            <InputNumber min={1} max={10} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="transforms" label="数据转换">
            <TextArea
              rows={6}
              placeholder='[{"type": "FieldMapper", "params": {"field_mapper": {"old_name": "new_name"}}}]'
            />
          </Form.Item>
        </>
      ),
    },
  ];

  return (
    <Modal
      title="创建 CDC 同步任务"
      open={visible}
      onCancel={onClose}
      width={700}
      footer={null}
      destroyOnClose
    >
      <Steps current={currentStep} style={{ marginBottom: 24 }}>
        {steps.map((step, index) => (
          <Steps.Step key={index} title={step.title} />
        ))}
      </Steps>

      <div style={{ minHeight: 300 }}>
        <Form form={form} layout="vertical">
          {steps[currentStep].content}
        </Form>
      </div>

      <div style={{ marginTop: 24, textAlign: 'right' }}>
        <Space>
          {currentStep > 0 && (
            <Button onClick={handlePrev}>上一步</Button>
          )}
          {currentStep < steps.length - 1 && (
            <Button type="primary" onClick={handleNext}>
              下一步
            </Button>
          )}
          {currentStep === steps.length - 1 && (
            <Button
              type="primary"
              onClick={handleSubmit}
              loading={createMutation.isPending}
            >
              创建任务
            </Button>
          )}
        </Space>
      </div>
    </Modal>
  );
};

export default CreateJobModal;
