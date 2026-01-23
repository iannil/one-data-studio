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
} from 'antd';
import {
  PlayCircleOutlined,
  ToolOutlined,
  CodeOutlined,
  SearchOutlined,
  ClearOutlined,
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import bisheng, { type Tool, type AgentStep } from '@/services/bisheng';
import StepsViewer from './StepsViewer';
import ToolExecuteModal from './ToolExecuteModal';
import SchemaViewer from './SchemaViewer';

const { TextArea } = Input;
const { Option } = Select;
const { Text, Paragraph } = Typography;
const { Panel } = Collapse;

const agentTypes = [
  { value: 'react', label: 'ReAct', description: '推理-行动-观察循环' },
  { value: 'function_calling', label: 'Function Calling', description: 'OpenAI 函数调用模式' },
  { value: 'plan_execute', label: 'Plan-Execute', description: '先规划后执行' },
];

function AgentsPage() {
  const [agentType, setAgentType] = useState<'react' | 'function_calling' | 'plan_execute'>('react');
  const [model, setModel] = useState<string>('gpt-4');
  const [maxIterations, setMaxIterations] = useState<number>(10);
  const [query, setQuery] = useState<string>('');
  const [steps, setSteps] = useState<AgentStep[]>([]);
  const [running, setRunning] = useState(false);
  const [selectedTool, setSelectedTool] = useState<Tool | null>(null);
  const [toolModalOpen, setToolModalOpen] = useState(false);
  const [schemaModalOpen, setSchemaModalOpen] = useState(false);
  const [searchText, setSearchText] = useState<string>('');

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

  const tools = toolsData?.data?.tools || [];
  const schemas = schemasData?.data?.schemas || [];

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
  };

  const handleClear = () => {
    setQuery('');
    setSteps([]);
  };

  const handleTestTool = (tool: Tool) => {
    setSelectedTool(tool);
    setToolModalOpen(true);
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

  return (
    <div style={{ padding: '24px', height: 'calc(100vh - 64px)', overflow: 'hidden' }}>
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
              <div style={{ marginTop: '8px', textAlign: 'right' }}>
                <Button icon={<ClearOutlined />} onClick={handleClear} disabled={running}>
                  清空
                </Button>
                <Button
                  type="primary"
                  icon={<PlayCircleOutlined />}
                  onClick={handleRunAgent}
                  loading={running}
                  style={{ marginLeft: '8px' }}
                >
                  {running ? '运行中...' : '运行 Agent'}
                </Button>
              </div>
            </div>

            <Divider style={{ margin: '8px 0 16px 0' }} />

            <div style={{ flex: 1, overflow: 'auto' }}>
              <Text strong style={{ fontSize: '16px' }}>
                执行步骤
              </Text>
              <div style={{ marginTop: '12px' }}>
                <StepsViewer steps={steps} loading={running} />
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
    </div>
  );
}

export default AgentsPage;
