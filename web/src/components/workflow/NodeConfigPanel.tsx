/**
 * 节点配置面板组件
 * Phase 7: Sprint 7.3
 *
 * 用于配置选中节点的属性
 */

import React, { useEffect, useState } from 'react';
import { Node } from 'reactflow';
import { Form, Input, InputNumber, Select, Slider, Switch, Button, Space, Tag } from 'antd';

const { TextArea } = Input;
const { Option } = Select;

interface NodeConfigPanelProps {
  node: Node | null;
  onNodeUpdate?: (nodeId: string, config: Record<string, any>) => void;
  onClose?: () => void;
}

// 节点类型配置定义
const nodeConfigSchemas: Record<string, any> = {
  input: {
    label: '输入节点配置',
    fields: [
      {
        name: 'key',
        label: '输入键名',
        type: 'string',
        default: 'input',
        description: '接收输入的键名',
      },
    ],
  },
  output: {
    label: '输出节点配置',
    fields: [
      {
        name: 'output_key',
        label: '输出键名',
        type: 'string',
        default: 'result',
        description: '返回结果的键名',
      },
      {
        name: 'input_from',
        label: '输入来源',
        type: 'string',
        default: 'llm',
        description: '从哪个节点获取输出',
      },
    ],
  },
  retriever: {
    label: '检索节点配置',
    fields: [
      {
        name: 'collection',
        label: '集合名称',
        type: 'string',
        default: 'default',
      },
      {
        name: 'top_k',
        label: '返回数量',
        type: 'number',
        default: 5,
        min: 1,
        max: 20,
      },
      {
        name: 'query_from',
        label: '查询来源',
        type: 'string',
        default: 'input',
      },
    ],
  },
  llm: {
    label: 'LLM 节点配置',
    fields: [
      {
        name: 'model',
        label: '模型',
        type: 'select',
        default: 'gpt-4o-mini',
        options: ['gpt-4o-mini', 'gpt-4o', 'gpt-3.5-turbo', 'claude-3-haiku'],
      },
      {
        name: 'temperature',
        label: '温度',
        type: 'slider',
        default: 0.7,
        min: 0,
        max: 2,
        step: 0.1,
      },
      {
        name: 'max_tokens',
        label: '最大 Token 数',
        type: 'number',
        default: 2000,
        min: 100,
        max: 32000,
      },
      {
        name: 'system_prompt',
        label: '系统提示',
        type: 'textarea',
        default: '你是一个有用的AI助手。',
      },
      {
        name: 'input_from',
        label: '输入来源',
        type: 'string',
        default: 'input',
      },
    ],
  },
  agent: {
    label: 'Agent 节点配置',
    fields: [
      {
        name: 'agent_type',
        label: 'Agent 类型',
        type: 'select',
        default: 'react',
        options: ['react', 'function_calling', 'plan_execute'],
      },
      {
        name: 'model',
        label: '模型',
        type: 'select',
        default: 'gpt-4o-mini',
        options: ['gpt-4o-mini', 'gpt-4o', 'claude-3-haiku'],
      },
      {
        name: 'max_iterations',
        label: '最大迭代次数',
        type: 'number',
        default: 10,
        min: 1,
        max: 30,
      },
      {
        name: 'input_from',
        label: '输入来源',
        type: 'string',
        default: 'input',
      },
    ],
  },
  tool_call: {
    label: '工具调用配置',
    fields: [
      {
        name: 'tool_name',
        label: '工具名称',
        type: 'select',
        default: 'calculator',
        options: [
          'vector_search',
          'sql_query',
          'http_request',
          'calculator',
          'text_to_sql',
          'datetime',
          'data_analysis',
        ],
      },
      {
        name: 'input_from',
        label: '输入来源',
        type: 'string',
        default: 'input',
      },
    ],
  },
  think: {
    label: '思考节点配置',
    fields: [
      {
        name: 'prompt',
        label: '提示模板',
        type: 'textarea',
        default: '请分析以下内容：{{ input }}',
      },
      {
        name: 'model',
        label: '模型',
        type: 'select',
        default: 'gpt-4o-mini',
        options: ['gpt-4o-mini', 'gpt-4o', 'gpt-3.5-turbo'],
      },
      {
        name: 'temperature',
        label: '温度',
        type: 'slider',
        default: 0.7,
        min: 0,
        max: 2,
        step: 0.1,
      },
    ],
  },
  condition: {
    label: '条件分支配置',
    fields: [
      {
        name: 'condition',
        label: '条件表达式',
        type: 'textarea',
        default: '{{ inputs.score > 0.8 }}',
        description: '支持变量引用，如 {{ inputs.xxx }}',
      },
      {
        name: 'true_branch',
        label: 'True 分支节点',
        type: 'tags',
        default: [],
        description: '条件为真时执行的节点 ID 列表',
      },
      {
        name: 'false_branch',
        label: 'False 分支节点',
        type: 'tags',
        default: [],
        description: '条件为假时执行的节点 ID 列表',
      },
    ],
  },
  loop: {
    label: '循环节点配置',
    fields: [
      {
        name: 'loop_over',
        label: '循环次数/数组',
        type: 'string',
        default: '3',
        description: '固定次数或变量引用',
      },
      {
        name: 'max_iterations',
        label: '最大迭代次数',
        type: 'number',
        default: 10,
        min: 1,
        max: 100,
      },
      {
        name: 'output_mode',
        label: '输出模式',
        type: 'select',
        default: 'last',
        options: ['last', 'all', 'concat'],
      },
    ],
  },
};

export default function NodeConfigPanel({ node, onNodeUpdate, onClose }: NodeConfigPanelProps) {
  const [form] = Form.useForm();
  const [config, setConfig] = useState<Record<string, any>>({});

  useEffect(() => {
    if (node) {
      const nodeConfig = node.data?.config || {};
      setConfig(nodeConfig);
      form.setFieldsValue(nodeConfig);
    }
  }, [node, form]);

  const handleSave = () => {
    form.validateFields().then((values) => {
      if (node && onNodeUpdate) {
        onNodeUpdate(node.id, values);
      }
    });
  };

  const handleValuesChange = (changedValues: any) => {
    setConfig({ ...config, ...changedValues });
  };

  if (!node) {
    return (
      <div className="w-72 bg-gray-50 border-l border-gray-200 p-4">
        <div className="text-center text-gray-400 py-8">
          <p>选择一个节点以配置</p>
        </div>
      </div>
    );
  }

  const schema = nodeConfigSchemas[node.type || ''] || null;

  return (
    <div className="w-72 bg-gray-50 border-l border-gray-200 overflow-y-auto">
      <div className="p-4 border-b border-gray-200 flex items-center justify-between">
        <h3 className="font-semibold text-gray-700">{schema?.label || '节点配置'}</h3>
        {onClose && (
          <Button type="text" size="small" onClick={onClose}>
            ✕
          </Button>
        )}
      </div>

      <div className="p-4">
        <div className="mb-4 p-3 bg-white rounded border">
          <div className="text-sm font-medium text-gray-700">节点信息</div>
          <div className="text-xs text-gray-500 mt-1">ID: {node.id}</div>
          <div className="text-xs text-gray-500">类型: {node.type}</div>
        </div>

        {schema ? (
          <Form
            form={form}
            layout="vertical"
            size="small"
            onValuesChange={handleValuesChange}
          >
            {schema.fields.map((field: any) => (
              <Form.Item
                key={field.name}
                name={field.name}
                label={field.label}
                extra={field.description}
              >
                {field.type === 'string' && <Input />}
                {field.type === 'number' && (
                  <InputNumber min={field.min} max={field.max} className="w-full" />
                )}
                {field.type === 'slider' && (
                  <Slider min={field.min} max={field.max} step={field.step} />
                )}
                {field.type === 'select' && (
                  <Select>
                    {field.options.map((opt: string) => (
                      <Option key={opt} value={opt}>
                        {opt}
                      </Option>
                    ))}
                  </Select>
                )}
                {field.type === 'textarea' && <TextArea rows={4} />}
                {field.type === 'boolean' && <Switch />}
                {field.type === 'tags' && (
                  <Select mode="tags" tokenSeparators={[',', ' ']} />
                )}
              </Form.Item>
            ))}
          </Form>
        ) : (
          <div className="text-sm text-gray-500">
            该节点类型暂无可配置项
          </div>
        )}

        <div className="mt-6 space-y-2">
          <Button type="primary" block onClick={handleSave}>
            保存配置
          </Button>
          {onClose && (
            <Button block onClick={onClose}>
              关闭
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
