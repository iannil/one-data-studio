import { useState, useEffect } from 'react';
import {
  Modal,
  Form,
  Input,
  Select,
  InputNumber,
  Button,
  Space,
  message,
  Tag,
} from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import bisheng, { type AgentTemplate, type CreateAgentTemplateRequest } from '@/services/bisheng';

const { TextArea } = Input;
const { Option } = Select;

interface AgentTemplatesModalProps {
  open: boolean;
  onClose: () => void;
  template?: AgentTemplate | null;
  availableTools: string[];
}

interface FormValues {
  name: string;
  description?: string;
  agent_type: 'react' | 'function_calling' | 'plan_execute';
  model: string;
  max_iterations?: number;
  system_prompt?: string;
  selected_tools?: string[];
}

const agentTypes = [
  { value: 'react', label: 'ReAct', description: '推理-行动-观察循环' },
  { value: 'function_calling', label: 'Function Calling', description: 'OpenAI 函数调用模式' },
  { value: 'plan_execute', label: 'Plan-Execute', description: '先规划后执行' },
];

const models = [
  'gpt-4o',
  'gpt-4o-mini',
  'gpt-4-turbo',
  'gpt-4',
  'gpt-3.5-turbo',
  'claude-3-opus',
  'claude-3-sonnet',
  'claude-3-haiku',
];

function AgentTemplatesModal({
  open,
  onClose,
  template,
  availableTools,
}: AgentTemplatesModalProps) {
  const [form] = Form.useForm<FormValues>();
  const queryClient = useQueryClient();
  const [selectedTools, setSelectedTools] = useState<string[]>([]);

  const isEditing = !!template;

  // 创建模板
  const createMutation = useMutation({
    mutationFn: (data: CreateAgentTemplateRequest) =>
      bisheng.createAgentTemplate(data),
    onSuccess: () => {
      message.success('模板创建成功');
      queryClient.invalidateQueries({ queryKey: ['agentTemplates'] });
      handleClose();
    },
    onError: (error: Error) => {
      message.error(`创建失败: ${error.message || '未知错误'}`);
    },
  });

  // 更新模板
  const updateMutation = useMutation({
    mutationFn: ({ templateId, data }: { templateId: string; data: Partial<CreateAgentTemplateRequest> }) =>
      bisheng.updateAgentTemplate(templateId, data),
    onSuccess: () => {
      message.success('模板更新成功');
      queryClient.invalidateQueries({ queryKey: ['agentTemplates'] });
      handleClose();
    },
    onError: (error: Error) => {
      message.error(`更新失败: ${error.message || '未知错误'}`);
    },
  });

  useEffect(() => {
    if (open && template) {
      // 编辑模式：填充表单
      form.setFieldsValue({
        name: template.name,
        description: template.description,
        agent_type: template.agent_type,
        model: template.model,
        max_iterations: template.max_iterations,
        system_prompt: template.system_prompt,
      });
      setSelectedTools(template.selected_tools || []);
    } else if (open) {
      // 创建模式：重置表单
      form.resetFields();
      form.setFieldsValue({
        agent_type: 'react',
        model: 'gpt-4o-mini',
        max_iterations: 10,
      });
      setSelectedTools([]);
    }
  }, [open, template, form]);

  const handleClose = () => {
    form.resetFields();
    setSelectedTools([]);
    onClose();
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      const data: CreateAgentTemplateRequest = {
        ...values,
        selected_tools: selectedTools,
      };

      if (isEditing && template) {
        updateMutation.mutate({ templateId: template.template_id, data });
      } else {
        createMutation.mutate(data);
      }
    } catch (error) {
      // 表单验证失败
    }
  };

  const handleToolToggle = (toolName: string) => {
    setSelectedTools((prev) => {
      if (prev.includes(toolName)) {
        return prev.filter((t) => t !== toolName);
      } else {
        return [...prev, toolName];
      }
    });
  };

  return (
    <Modal
      title={isEditing ? '编辑 Agent 模板' : '创建 Agent 模板'}
      open={open}
      onCancel={handleClose}
      onOk={handleSubmit}
      confirmLoading={createMutation.isPending || updateMutation.isPending}
      width={600}
      destroyOnClose
    >
      <Form
        form={form}
        layout="vertical"
        initialValues={{
          agent_type: 'react',
          model: 'gpt-4o-mini',
          max_iterations: 10,
        }}
      >
        <Form.Item
          label="模板名称"
          name="name"
          rules={[{ required: true, message: '请输入模板名称' }]}
        >
          <Input placeholder="例如: RAG 数据分析师" />
        </Form.Item>

        <Form.Item
          label="描述"
          name="description"
        >
          <TextArea
            placeholder="简要描述这个模板的用途..."
            rows={2}
            maxLength={200}
            showCount
          />
        </Form.Item>

        <Space style={{ width: '100%' }} size="large" wrap>
          <Form.Item
            label="Agent 类型"
            name="agent_type"
            style={{ marginBottom: 0 }}
          >
            <Select style={{ width: 180 }}>
              {agentTypes.map((type) => (
                <Option key={type.value} value={type.value}>
                  {type.label}
                </Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item
            label="模型"
            name="model"
            style={{ marginBottom: 0 }}
          >
            <Select style={{ width: 180 }} showSearch>
              {models.map((model) => (
                <Option key={model} value={model}>
                  {model}
                </Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item
            label="最大迭代"
            name="max_iterations"
            style={{ marginBottom: 0 }}
          >
            <InputNumber min={1} max={50} style={{ width: 100 }} />
          </Form.Item>
        </Space>

        <Form.Item
          label="系统 Prompt"
          name="system_prompt"
        >
          <TextArea
            placeholder="可选：为 Agent 设置自定义系统提示词..."
            rows={3}
            maxLength={1000}
            showCount
          />
        </Form.Item>

        <Form.Item label="选用工具">
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
            {availableTools.map((tool) => {
              const isSelected = selectedTools.includes(tool);
              return (
                <Tag
                  key={tool}
                  color={isSelected ? 'blue' : 'default'}
                  style={{ cursor: 'pointer' }}
                  onClick={() => handleToolToggle(tool)}
                >
                  {isSelected ? <PlusOutlined style={{ marginRight: 4 }} /> : null}
                  {tool}
                </Tag>
              );
            })}
            {selectedTools.length > 0 && (
              <Button
                size="small"
                type="link"
                onClick={() => setSelectedTools([])}
                style={{ padding: 0 }}
              >
                清空
              </Button>
            )}
          </div>
          <div style={{ marginTop: 8, color: '#999', fontSize: 12 }}>
            已选择 {selectedTools.length} 个工具
          </div>
        </Form.Item>
      </Form>
    </Modal>
  );
}

export default AgentTemplatesModal;
