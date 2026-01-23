import { useState } from 'react';
import {
  Card,
  Row,
  Col,
  Select,
  Input,
  Button,
  List,
  Tag,
  Space,
  Divider,
  Empty,
  message,
  InputNumber,
  Collapse,
  Typography,
  Tabs,
  Popconfirm,
} from 'antd';
import {
  PlayCircleOutlined,
  ToolOutlined,
  CodeOutlined,
  SearchOutlined,
  ClearOutlined,
  SaveOutlined,
  DeleteOutlined,
  EditOutlined,
  AppstoreOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import bisheng, { type Tool, type AgentStep, type AgentTemplate } from '@/services/bisheng';
import StepsViewer from './StepsViewer';
import ToolExecuteModal from './ToolExecuteModal';
import SchemaViewer from './SchemaViewer';
import AgentTemplatesModal from './AgentTemplatesModal';

const { TextArea } = Input;
const { Option } = Select;
const { Text, Paragraph } = Typography;
const { Panel } = Collapse;

// 步骤类型配置
const stepConfig = {
  thought: { icon: '🧠', color: 'blue', label: '思考' },
  action: { icon: '🔧', color: 'orange', label: '行动' },
  observation: { icon: '👁', color: 'green', label: '观察' },
  final: { icon: '✅', color: 'purple', label: '最终答案' },
  plan: { icon: '📋', color: 'cyan', label: '计划' },
  error: { icon: '❌', color: 'red', label: '错误' },
};

const agentTypes = [
  { value: 'react', label: 'ReAct', description: '推理-行动-观察循环' },
  { value: 'function_calling', label: 'Function Calling', description: 'OpenAI 函数调用模式' },
  { value: 'plan_execute', label: 'Plan-Execute', description: '先规划后执行' },
];

function AgentsPage() {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState('run');

  // Agent 运行区状态
  const [agentType, setAgentType] = useState<'react' | 'function_calling' | 'plan_execute'>('react');
  const [model, setModel] = useState<string>('gpt-4o-mini');
  const [maxIterations, setMaxIterations] = useState<number>(10);
  const [query, setQuery] = useState<string>('');
  const [steps, setSteps] = useState<AgentStep[]>([]);
  const [running, setRunning] = useState(false);

  // 流式执行状态
  const [currentIteration, setCurrentIteration] = useState<number>(0);
  const [activeTool, setActiveTool] = useState<string>('');
  const [statusMessage, setStatusMessage] = useState<string>('');
  const [useStreaming, setUseStreaming] = useState(true);  // 默认使用流式执行

  // 工具相关状态
  const [selectedTool, setSelectedTool] = useState<Tool | null>(null);
  const [toolModalOpen, setToolModalOpen] = useState(false);
  const [schemaModalOpen, setSchemaModalOpen] = useState(false);
  const [searchText, setSearchText] = useState<string>('');

  // 模板管理状态
  const [templateModalOpen, setTemplateModalOpen] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState<AgentTemplate | null>(null);

  // 获取工具列表
  const { data: toolsData, isLoading: toolsLoading } = useQuery({
    queryKey: ['tools'],
    queryFn: () => bisheng.listTools(),
  });

  // 获取工具 Schema
  const { data: schemasData } = useQuery({
    queryKey: ['toolSchemas'],
    queryFn: () => bisheng.getToolSchemas(),
  });

  // 获取 Agent 模板列表
  const { data: templatesData, isLoading: templatesLoading } = useQuery({
    queryKey: ['agentTemplates'],
    queryFn: () => bisheng.listAgentTemplates(),
  });

  const tools = toolsData?.data?.tools || [];
  const schemas = schemasData?.data?.schemas || [];
  const templates = templatesData?.data?.templates || [];
  const availableToolNames = tools.map((t: Tool) => t.name);

  const filteredTools = tools.filter((tool: Tool) =>
    tool.name.toLowerCase().includes(searchText.toLowerCase()) ||
    tool.description.toLowerCase().includes(searchText.toLowerCase())
  );

  const handleRunAgent = async () => {
    if (!query.trim()) {
      message.warning('请输入查询内容');
      return;
    }

    setRunning(true);
    setSteps([]);
    setCurrentIteration(0);
    setActiveTool('');
    setStatusMessage('');

    if (useStreaming) {
      // 使用流式 API
      await bisheng.runAgentStream(
        {
          query,
          agent_type: agentType,
          model,
          max_iterations: maxIterations,
        },
        {
          onStart: (agentTypeStr) => {
            setStatusMessage(`Agent (${agentTypeStr}) 已启动`);
          },
          onStep: (step) => {
            setSteps((prev) => [...prev, step]);
          },
          onIteration: (iteration, maxIterations) => {
            setCurrentIteration(iteration);
          },
          onToolStart: (tool) => {
            setActiveTool(tool);
            setStatusMessage(`正在执行工具: ${tool}`);
          },
          onToolEnd: () => {
            setActiveTool('');
          },
          onStatus: (msg) => {
            setStatusMessage(msg);
          },
          onComplete: (result) => {
            setRunning(false);
            setActiveTool('');
            if (result.success) {
              message.success(`Agent 运行完成，迭代 ${result.iterations || 1} 次`);
            } else {
              message.error(`Agent 运行失败: ${result.error || '未知错误'}`);
            }
            setStatusMessage('');
          },
          onError: (error) => {
            message.error(`执行错误: ${error}`);
            setStatusMessage(`错误: ${error}`);
          },
        }
      );
    } else {
      // 使用非流式 API（原有逻辑）
      try {
        const response = await bisheng.runAgent({
          query,
          agent_type: agentType,
          model,
          max_iterations: maxIterations,
        });

        const result = response.data;
        if (result.success) {
          if (result.steps) {
            setSteps(result.steps);
          } else if (result.answer) {
            setSteps([
              {
                type: 'final',
                content: result.answer,
                timestamp: new Date().toISOString(),
              },
            ]);
          }
          message.success(`Agent 运行完成，迭代 ${result.iterations || 1} 次`);
        } else {
          message.error(`Agent 运行失败: ${result.error || '未知错误'}`);
          setSteps([
            {
              type: 'final',
              content: `错误: ${result.error || '未知错误'}`,
              timestamp: new Date().toISOString(),
            },
          ]);
        }
      } catch (error: any) {
        message.error(`Agent 运行失败: ${error.message || '未知错误'}`);
        setSteps([
          {
            type: 'final',
            content: `错误: ${error.message || '未知错误'}`,
            timestamp: new Date().toISOString(),
          },
        ]);
      } finally {
        setRunning(false);
      }
    }
  };

  const handleClear = () => {
    setQuery('');
    setSteps([]);
    setCurrentIteration(0);
    setActiveTool('');
    setStatusMessage('');
  };

  const handleTestTool = (tool: Tool) => {
    setSelectedTool(tool);
    setToolModalOpen(true);
  };

  // 保存当前配置为模板
  const handleSaveAsTemplate = () => {
    setEditingTemplate(null);
    setTemplateModalOpen(true);
  };

  // 编辑模板
  const handleEditTemplate = (template: AgentTemplate) => {
    setEditingTemplate(template);
    setTemplateModalOpen(true);
  };

  // 应用模板
  const handleApplyTemplate = (template: AgentTemplate) => {
    setAgentType(template.agent_type);
    setModel(template.model);
    setMaxIterations(template.max_iterations || 10);
    message.success(`已应用模板: ${template.name}`);
  };

  // 删除模板
  const deleteMutation = useMutation({
    mutationFn: (templateId: string) => bisheng.deleteAgentTemplate(templateId),
    onSuccess: () => {
      message.success('模板删除成功');
      queryClient.invalidateQueries({ queryKey: ['agentTemplates'] });
    },
    onError: (error: any) => {
      message.error(`删除失败: ${error.message || '未知错误'}`);
    },
  });

  const handleDeleteTemplate = (template: AgentTemplate) => {
    deleteMutation.mutate(template.template_id);
  };

  const handleTemplateModalClose = () => {
    setTemplateModalOpen(false);
    setEditingTemplate(null);
  };

  const getToolIcon = (toolName: string) => {
    const name = toolName.toLowerCase();
    if (name.includes('search') || name.includes('web')) return '🔍';
    if (name.includes('database') || name.includes('db') || name.includes('sql')) return '🗄️';
    if (name.includes('calc') || name.includes('math')) return '🧮';
    if (name.includes('file') || name.includes('doc')) return '📄';
    if (name.includes('http') || name.includes('api') || name.includes('request')) return '🌐';
    if (name.includes('code') || name.includes('exec')) return '💻';
    return '🔧';
  };

  const getToolColor = (toolName: string) => {
    const name = toolName.toLowerCase();
    if (name.includes('search') || name.includes('web')) return 'blue';
    if (name.includes('database') || name.includes('db') || name.includes('sql')) return 'green';
    if (name.includes('calc') || name.includes('math')) return 'orange';
    if (name.includes('file') || name.includes('doc')) return 'cyan';
    if (name.includes('http') || name.includes('api') || name.includes('request')) return 'purple';
    return 'default';
  };

  const getAgentTypeLabel = (type: string) => {
    const found = agentTypes.find((t) => t.value === type);
    return found ? found.label : type;
  };

  const getAgentTypeColor = (type: string) => {
    switch (type) {
      case 'react': return 'blue';
      case 'function_calling': return 'green';
      case 'plan_execute': return 'purple';
      default: return 'default';
    }
  };

  // Agent 运行区内容
  const renderAgentRunArea = () => (
    <Row gutter={16} style={{ height: '100%' }}>
      {/* 左侧 - Agent 运行区 */}
      <Col span={14} style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
        <Card
          title={
            <Space>
              <PlayCircleOutlined />
              <span>Agent 运行区</span>
            </Space>
          }
          extra={
            <Button
              type="primary"
              size="small"
              icon={<SaveOutlined />}
              onClick={handleSaveAsTemplate}
            >
              保存为模板
            </Button>
          }
          style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}
          bodyStyle={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}
        >
          <Space style={{ marginBottom: '16px' }} wrap>
            <div>
              <Text strong>Agent 类型:</Text>
              <Select
                value={agentType}
                onChange={setAgentType}
                style={{ width: 180, marginLeft: '8px' }}
              >
                {agentTypes.map((type) => (
                  <Option key={type.value} value={type.value}>
                    {type.label} - {type.description}
                  </Option>
                ))}
              </Select>
            </div>
            <div>
              <Text strong>模型:</Text>
              <Select
                value={model}
                onChange={setModel}
                style={{ width: 150, marginLeft: '8px' }}
              >
                <Option value="gpt-4o">GPT-4o</Option>
                <Option value="gpt-4o-mini">GPT-4o Mini</Option>
                <Option value="gpt-4-turbo">GPT-4 Turbo</Option>
                <Option value="gpt-4">GPT-4</Option>
                <Option value="gpt-3.5-turbo">GPT-3.5 Turbo</Option>
                <Option value="claude-3-opus">Claude 3 Opus</Option>
                <Option value="claude-3-sonnet">Claude 3 Sonnet</Option>
              </Select>
            </div>
            <div>
              <Text strong>最大迭代:</Text>
              <InputNumber
                value={maxIterations}
                onChange={(val) => setMaxIterations(val || 10)}
                min={1}
                max={50}
                style={{ width: 80, marginLeft: '8px' }}
              />
            </div>
          </Space>

          <Divider style={{ margin: '8px 0 16px 0' }} />

          <div style={{ marginBottom: '16px' }}>
            <TextArea
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="请输入您的问题，Agent 将使用可用工具来帮助解决问题..."
              rows={4}
              disabled={running}
              onPressEnter={(e) => {
                if (e.shiftKey) return;
                e.preventDefault();
                handleRunAgent();
              }}
            />
            <div style={{ marginTop: '8px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Space>
                <Button icon={<ClearOutlined />} onClick={handleClear} disabled={running}>
                  清空
                </Button>
                <Button
                  type="primary"
                  icon={<PlayCircleOutlined />}
                  onClick={handleRunAgent}
                  loading={running}
                >
                  {running ? '运行中...' : '运行 Agent'}
                </Button>
              </Space>
              <Space>
                <Text type="secondary" style={{ fontSize: '12px' }}>
                  流式执行
                </Text>
                <input
                  type="checkbox"
                  checked={useStreaming}
                  onChange={(e) => setUseStreaming(e.target.checked)}
                  disabled={running}
                  style={{ cursor: running ? 'not-allowed' : 'pointer' }}
                />
              </Space>
            </div>
          </div>

          <Divider style={{ margin: '8px 0 16px 0' }} />

          {/* 状态指示器 */}
          {(running || statusMessage || currentIteration > 0) && (
            <div
              style={{
                padding: '12px',
                background: '#f0f9ff',
                borderRadius: '8px',
                marginBottom: '16px',
                border: '1px solid #bae7ff',
              }}
            >
              <Space direction="vertical" style={{ width: '100%' }} size={4}>
                {statusMessage && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Text type="secondary" style={{ fontSize: '12px' }}>
                      状态:
                    </Text>
                    <Text style={{ fontSize: '13px' }}>{statusMessage}</Text>
                  </div>
                )}
                {currentIteration > 0 && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Text type="secondary" style={{ fontSize: '12px' }}>
                      迭代:
                    </Text>
                    <Tag color="blue">
                      {currentIteration} / {maxIterations}
                    </Tag>
                  </div>
                )}
                {activeTool && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontSize: '14px' }}>🔧</span>
                    <Text style={{ fontSize: '13px', color: '#fa8c16' }}>
                      正在执行: {activeTool}
                    </Text>
                  </div>
                )}
              </Space>
            </div>
          )}

          <div style={{ flex: 1, overflow: 'auto' }}>
            <Text strong style={{ fontSize: '16px' }}>
              执行步骤 ({steps.length})
            </Text>
            <div style={{ marginTop: '12px' }}>
              <StepsViewer steps={steps} loading={running && steps.length === 0} />
            </div>
          </div>
        </Card>
      </Col>

      {/* 右侧 - 工具浏览区 */}
      <Col span={10} style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
        <Card
          title={
            <Space>
              <ToolOutlined />
              <span>可用工具 ({filteredTools.length})</span>
            </Space>
          }
          extra={
            <Space>
              <Button
                size="small"
                icon={<CodeOutlined />}
                onClick={() => setSchemaModalOpen(true)}
              >
                查看 Schema
              </Button>
            </Space>
          }
          style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}
          bodyStyle={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', padding: '16px' }}
        >
          <Input
            placeholder="搜索工具..."
            prefix={<SearchOutlined />}
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            style={{ marginBottom: '16px' }}
            allowClear
          />

          <div style={{ flex: 1, overflow: 'auto' }}>
            {toolsLoading ? (
              <Empty description="加载中..." />
            ) : filteredTools.length === 0 ? (
              <Empty description={searchText ? '没有找到匹配的工具' : '暂无可用工具'} />
            ) : (
              <List
                dataSource={filteredTools}
                renderItem={(tool: Tool) => (
                  <List.Item
                    style={{
                      border: '1px solid #f0f0f0',
                      borderRadius: '8px',
                      marginBottom: '8px',
                      padding: '12px',
                    }}
                    actions={[
                      <Button
                        size="small"
                        type="link"
                        onClick={() => handleTestTool(tool)}
                      >
                        测试
                      </Button>,
                    ]}
                  >
                    <List.Item.Meta
                      avatar={
                        <span style={{ fontSize: '20px' }}>
                          {getToolIcon(tool.name)}
                        </span>
                      }
                      title={
                        <Space>
                          <Tag color={getToolColor(tool.name)}>{tool.name}</Tag>
                          <Text strong style={{ fontSize: '13px' }}>
                            {tool.name}
                          </Text>
                        </Space>
                      }
                      description={
                        <div>
                          <Paragraph
                            style={{ margin: '4px 0', fontSize: '12px' }}
                            ellipsis={{ rows: 2 }}
                          >
                            {tool.description}
                          </Paragraph>
                          <Collapse
                            ghost
                            size="small"
                            style={{ marginTop: '8px' }}
                          >
                            <Panel header={`参数 (${tool.parameters.length})`} key="params">
                              <div style={{ fontSize: '12px' }}>
                                {tool.parameters.length === 0 ? (
                                  <Text type="secondary">无参数</Text>
                                ) : (
                                  tool.parameters.map((param) => (
                                    <div
                                      key={param.name}
                                      style={{
                                        marginBottom: '4px',
                                        padding: '4px 8px',
                                        background: '#f5f5f5',
                                        borderRadius: '4px',
                                      }}
                                    >
                                      <Space size={4}>
                                        <Tag
                                          color={param.required ? 'red' : 'default'}
                                          style={{ margin: 0, fontSize: '11px' }}
                                        >
                                          {param.type}
                                        </Tag>
                                        <Text strong style={{ fontSize: '12px' }}>
                                          {param.name}
                                        </Text>
                                      </Space>
                                      {param.description && (
                                        <div style={{ color: '#666', fontSize: '11px', marginTop: '2px' }}>
                                          {param.description}
                                        </div>
                                      )}
                                    </div>
                                  ))
                                )}
                              </div>
                            </Panel>
                          </Collapse>
                        </div>
                      }
                    />
                  </List.Item>
                )}
              />
            )}
          </div>
        </Card>
      </Col>
    </Row>
  );

  // 模板管理区内容
  const renderTemplateManagement = () => (
    <div style={{ padding: '24px', height: 'calc(100vh - 64px - 48px)', overflow: 'auto' }}>
      <Card
        title={
          <Space>
            <AppstoreOutlined />
            <span>Agent 模板管理</span>
          </Space>
        }
        extra={
          <Button
            type="primary"
            icon={<SaveOutlined />}
            onClick={() => {
              setEditingTemplate(null);
              setTemplateModalOpen(true);
            }}
          >
            新建模板
          </Button>
        }
      >
        {templatesLoading ? (
          <Empty description="加载中..." />
        ) : templates.length === 0 ? (
          <Empty description="暂无模板，点击上方按钮创建">
            <Button
              type="primary"
              onClick={() => {
                setEditingTemplate(null);
                setTemplateModalOpen(true);
              }}
            >
              创建第一个模板
            </Button>
          </Empty>
        ) : (
          <List
            dataSource={templates}
            renderItem={(template: AgentTemplate) => (
              <List.Item
                style={{
                  border: '1px solid #f0f0f0',
                  borderRadius: '8px',
                  marginBottom: '12px',
                  padding: '16px',
                }}
                actions={[
                  <Button
                    key="apply"
                    type="link"
                    onClick={() => handleApplyTemplate(template)}
                  >
                    应用
                  </Button>,
                  <Button
                    key="edit"
                    type="link"
                    icon={<EditOutlined />}
                    onClick={() => handleEditTemplate(template)}
                  >
                    编辑
                  </Button>,
                  <Popconfirm
                    key="delete"
                    title="确定删除此模板?"
                    onConfirm={() => handleDeleteTemplate(template)}
                    okText="确定"
                    cancelText="取消"
                  >
                    <Button
                      type="link"
                      danger
                      icon={<DeleteOutlined />}
                    >
                      删除
                    </Button>
                  </Popconfirm>,
                ]}
              >
                <List.Item.Meta
                  title={
                    <Space>
                      <Text strong>{template.name}</Text>
                      <Tag color={getAgentTypeColor(template.agent_type)}>
                        {getAgentTypeLabel(template.agent_type)}
                      </Tag>
                      <Tag>{template.model}</Tag>
                    </Space>
                  }
                  description={
                    <div>
                      {template.description && (
                        <Paragraph style={{ margin: '4px 0', fontSize: '13px' }}>
                          {template.description}
                        </Paragraph>
                      )}
                      <Space wrap>
                        <Text type="secondary" style={{ fontSize: '12px' }}>
                          最大迭代: {template.max_iterations || 10}
                        </Text>
                        <Text type="secondary" style={{ fontSize: '12px' }}>
                          工具数: {template.selected_tools?.length || 0}
                        </Text>
                        <Text type="secondary" style={{ fontSize: '12px' }}>
                          创建时间: {new Date(template.created_at).toLocaleDateString()}
                        </Text>
                      </Space>
                      {template.selected_tools && template.selected_tools.length > 0 && (
                        <div style={{ marginTop: '8px' }}>
                          <Space wrap size={4}>
                            {template.selected_tools.slice(0, 5).map((tool) => (
                              <Tag key={tool} color="blue" style={{ fontSize: '11px' }}>
                                {tool}
                              </Tag>
                            ))}
                            {template.selected_tools.length > 5 && (
                              <Tag style={{ fontSize: '11px' }}>
                                +{template.selected_tools.length - 5}
                              </Tag>
                            )}
                          </Space>
                        </div>
                      )}
                    </div>
                  }
                />
              </List.Item>
            )}
          />
        )}
      </Card>
    </div>
  );

  return (
    <div style={{ height: 'calc(100vh - 64px)', overflow: 'hidden' }}>
      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={[
          {
            key: 'run',
            label: (
              <span>
                <PlayCircleOutlined />
                Agent 运行
              </span>
            ),
            children: renderAgentRunArea(),
          },
          {
            key: 'templates',
            label: (
              <span>
                <AppstoreOutlined />
                模板管理 ({templates.length})
              </span>
            ),
            children: renderTemplateManagement(),
          },
        ]}
      />

      {/* 工具测试弹窗 */}
      <ToolExecuteModal
        tool={selectedTool}
        open={toolModalOpen}
        onClose={() => {
          setToolModalOpen(false);
          setSelectedTool(null);
        }}
      />

      {/* Schema 查看弹窗 */}
      <SchemaViewer
        schemas={schemas}
        open={schemaModalOpen}
        onClose={() => setSchemaModalOpen(false)}
      />

      {/* 模板编辑弹窗 */}
      <AgentTemplatesModal
        open={templateModalOpen}
        onClose={handleTemplateModalClose}
        template={editingTemplate}
        availableTools={availableToolNames}
      />
    </div>
  );
}

export default AgentsPage;
