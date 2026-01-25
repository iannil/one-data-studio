import { useState, useEffect } from 'react';
import {
  Card,
  Input,
  Select,
  Table,
  Tag,
  Space,
  Button,
  Typography,
  Row,
  Col,
  Tabs,
  Modal,
  Descriptions,
  Spin,
  Empty,
  message,
  Tooltip,
  Badge,
} from 'antd';
import {
  SearchOutlined,
  DownloadOutlined,
  HeartOutlined,
  CloudDownloadOutlined,
  InfoCircleOutlined,
  LinkOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { ColumnsType } from 'antd/es/table';
import ReactMarkdown from 'react-markdown';
import api from '../../services/api';

const { Title, Text } = Typography;
const { Search } = Input;

interface ModelInfo {
  id: string;
  author: string;
  model_name: string;
  sha: string;
  last_modified: string;
  private: boolean;
  pipeline_tag?: string;
  tags: string[];
  downloads: number;
  likes: number;
  library_name?: string;
  language?: string[];
  license?: string;
}

interface DatasetInfo {
  id: string;
  author: string;
  dataset_name: string;
  sha: string;
  last_modified: string;
  private: boolean;
  tags: string[];
  downloads: number;
  likes: number;
}

// Pipeline 标签映射
const pipelineTags = [
  { value: 'text-generation', label: 'Text Generation' },
  { value: 'text-classification', label: 'Text Classification' },
  { value: 'text2text-generation', label: 'Text2Text Generation' },
  { value: 'token-classification', label: 'Token Classification' },
  { value: 'question-answering', label: 'Question Answering' },
  { value: 'fill-mask', label: 'Fill Mask' },
  { value: 'summarization', label: 'Summarization' },
  { value: 'translation', label: 'Translation' },
  { value: 'conversational', label: 'Conversational' },
  { value: 'feature-extraction', label: 'Feature Extraction' },
  { value: 'sentence-similarity', label: 'Sentence Similarity' },
  { value: 'image-classification', label: 'Image Classification' },
  { value: 'object-detection', label: 'Object Detection' },
  { value: 'text-to-image', label: 'Text to Image' },
  { value: 'automatic-speech-recognition', label: 'Speech Recognition' },
];

// 库过滤选项
const libraryOptions = [
  { value: 'transformers', label: 'Transformers' },
  { value: 'pytorch', label: 'PyTorch' },
  { value: 'tensorflow', label: 'TensorFlow' },
  { value: 'jax', label: 'JAX' },
  { value: 'diffusers', label: 'Diffusers' },
  { value: 'sentence-transformers', label: 'Sentence Transformers' },
];

function HuggingFaceHub() {
  const { t: _t } = useTranslation();
  const [activeTab, setActiveTab] = useState('models');
  const [loading, setLoading] = useState(false);
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [datasets, setDatasets] = useState<DatasetInfo[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [pipelineFilter, setPipelineFilter] = useState<string | undefined>();
  const [libraryFilter, setLibraryFilter] = useState<string | undefined>();
  const [selectedModel, setSelectedModel] = useState<ModelInfo | null>(null);
  const [modelCardContent, setModelCardContent] = useState<string>('');
  const [cardModalVisible, setCardModalVisible] = useState(false);
  const [cardLoading, setCardLoading] = useState(false);

  // 搜索模型
  const searchModels = async () => {
    setLoading(true);
    try {
      const response = await api.get('/api/v1/huggingface/models', {
        params: {
          query: searchQuery || undefined,
          pipeline_tag: pipelineFilter,
          library: libraryFilter,
          limit: 50,
        },
      });
      setModels(response.data || []);
    } catch (error) {
      message.error('Failed to search models');
      // 使用模拟数据
      setModels(getMockModels());
    } finally {
      setLoading(false);
    }
  };

  // 搜索数据集
  const searchDatasets = async () => {
    setLoading(true);
    try {
      const response = await api.get('/api/v1/huggingface/datasets', {
        params: {
          query: searchQuery || undefined,
          limit: 50,
        },
      });
      setDatasets(response.data || []);
    } catch (error) {
      message.error('Failed to search datasets');
      // 使用模拟数据
      setDatasets(getMockDatasets());
    } finally {
      setLoading(false);
    }
  };

  // 获取模型卡片
  const fetchModelCard = async (modelId: string) => {
    setCardLoading(true);
    try {
      const response = await api.get(`/api/v1/huggingface/models/${encodeURIComponent(modelId)}/card`);
      setModelCardContent(response.data?.content || 'No README available');
    } catch {
      setModelCardContent('Failed to load model card');
    } finally {
      setCardLoading(false);
    }
  };

  // 查看模型详情
  const handleViewModel = (model: ModelInfo) => {
    setSelectedModel(model);
    setCardModalVisible(true);
    fetchModelCard(model.id);
  };

  // 导入模型到平台
  const handleImportModel = async (modelId: string) => {
    try {
      await api.post('/api/v1/models/import', { source: 'huggingface', model_id: modelId });
      message.success(`Model ${modelId} import started`);
    } catch {
      message.error('Failed to import model');
    }
  };

  // 初始加载
  useEffect(() => {
    if (activeTab === 'models') {
      searchModels();
    } else {
      searchDatasets();
    }
  }, [activeTab]);

  // 模型表格列
  const modelColumns: ColumnsType<ModelInfo> = [
    {
      title: 'Model',
      key: 'model',
      render: (_, record) => (
        <Space direction="vertical" size={0}>
          <Text strong>
            <a
              href={`https://huggingface.co/${record.id}`}
              target="_blank"
              rel="noopener noreferrer"
            >
              {record.model_name}
            </a>
          </Text>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {record.author}
          </Text>
        </Space>
      ),
    },
    {
      title: 'Pipeline',
      dataIndex: 'pipeline_tag',
      key: 'pipeline_tag',
      render: (tag) => tag ? <Tag color="blue">{tag}</Tag> : '-',
    },
    {
      title: 'Library',
      dataIndex: 'library_name',
      key: 'library_name',
      render: (lib) => lib ? <Tag>{lib}</Tag> : '-',
    },
    {
      title: 'Stats',
      key: 'stats',
      render: (_, record) => (
        <Space>
          <Tooltip title="Downloads">
            <Badge count={formatNumber(record.downloads)} showZero color="#1677ff">
              <DownloadOutlined style={{ fontSize: 16 }} />
            </Badge>
          </Tooltip>
          <Tooltip title="Likes">
            <Badge count={formatNumber(record.likes)} showZero color="#ff4d4f">
              <HeartOutlined style={{ fontSize: 16 }} />
            </Badge>
          </Tooltip>
        </Space>
      ),
    },
    {
      title: 'License',
      dataIndex: 'license',
      key: 'license',
      render: (license) => license ? <Tag color="green">{license}</Tag> : '-',
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_, record) => (
        <Space>
          <Button
            type="link"
            icon={<InfoCircleOutlined />}
            onClick={() => handleViewModel(record)}
          >
            Details
          </Button>
          <Button
            type="primary"
            size="small"
            icon={<CloudDownloadOutlined />}
            onClick={() => handleImportModel(record.id)}
          >
            Import
          </Button>
        </Space>
      ),
    },
  ];

  // 数据集表格列
  const datasetColumns: ColumnsType<DatasetInfo> = [
    {
      title: 'Dataset',
      key: 'dataset',
      render: (_, record) => (
        <Space direction="vertical" size={0}>
          <Text strong>
            <a
              href={`https://huggingface.co/datasets/${record.id}`}
              target="_blank"
              rel="noopener noreferrer"
            >
              {record.dataset_name}
            </a>
          </Text>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {record.author}
          </Text>
        </Space>
      ),
    },
    {
      title: 'Tags',
      key: 'tags',
      render: (_, record) => (
        <Space wrap>
          {record.tags.slice(0, 3).map((tag) => (
            <Tag key={tag}>{tag}</Tag>
          ))}
          {record.tags.length > 3 && <Tag>+{record.tags.length - 3}</Tag>}
        </Space>
      ),
    },
    {
      title: 'Stats',
      key: 'stats',
      render: (_, record) => (
        <Space>
          <Tooltip title="Downloads">
            <Badge count={formatNumber(record.downloads)} showZero color="#1677ff">
              <DownloadOutlined style={{ fontSize: 16 }} />
            </Badge>
          </Tooltip>
          <Tooltip title="Likes">
            <Badge count={formatNumber(record.likes)} showZero color="#ff4d4f">
              <HeartOutlined style={{ fontSize: 16 }} />
            </Badge>
          </Tooltip>
        </Space>
      ),
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_, record) => (
        <Button
          type="link"
          icon={<LinkOutlined />}
          href={`https://huggingface.co/datasets/${record.id}`}
          target="_blank"
        >
          View
        </Button>
      ),
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <Card>
        <Row justify="space-between" align="middle" style={{ marginBottom: 24 }}>
          <Col>
            <Title level={4} style={{ margin: 0 }}>
              🤗 Hugging Face Hub
            </Title>
          </Col>
          <Col>
            <Button
              icon={<ReloadOutlined />}
              onClick={() => activeTab === 'models' ? searchModels() : searchDatasets()}
            >
              Refresh
            </Button>
          </Col>
        </Row>

        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={[
            { key: 'models', label: 'Models' },
            { key: 'datasets', label: 'Datasets' },
          ]}
        />

        {/* 搜索和过滤 */}
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col flex="auto">
            <Search
              placeholder="Search models or datasets..."
              allowClear
              enterButton={<SearchOutlined />}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onSearch={() => activeTab === 'models' ? searchModels() : searchDatasets()}
            />
          </Col>
          {activeTab === 'models' && (
            <>
              <Col>
                <Select
                  placeholder="Pipeline"
                  allowClear
                  style={{ width: 180 }}
                  options={pipelineTags}
                  value={pipelineFilter}
                  onChange={setPipelineFilter}
                />
              </Col>
              <Col>
                <Select
                  placeholder="Library"
                  allowClear
                  style={{ width: 150 }}
                  options={libraryOptions}
                  value={libraryFilter}
                  onChange={setLibraryFilter}
                />
              </Col>
            </>
          )}
        </Row>

        {/* 结果表格 */}
        {activeTab === 'models' ? (
          <Table
            columns={modelColumns}
            dataSource={models}
            rowKey="id"
            loading={loading}
            pagination={{ pageSize: 20, showSizeChanger: true }}
            locale={{ emptyText: <Empty description="No models found" /> }}
          />
        ) : (
          <Table
            columns={datasetColumns}
            dataSource={datasets}
            rowKey="id"
            loading={loading}
            pagination={{ pageSize: 20, showSizeChanger: true }}
            locale={{ emptyText: <Empty description="No datasets found" /> }}
          />
        )}
      </Card>

      {/* 模型详情 Modal */}
      <Modal
        title={selectedModel?.id}
        open={cardModalVisible}
        onCancel={() => setCardModalVisible(false)}
        footer={null}
        width={800}
      >
        {selectedModel && (
          <>
            <Descriptions bordered size="small" column={2} style={{ marginBottom: 16 }}>
              <Descriptions.Item label="Author">{selectedModel.author}</Descriptions.Item>
              <Descriptions.Item label="Pipeline">{selectedModel.pipeline_tag || '-'}</Descriptions.Item>
              <Descriptions.Item label="Library">{selectedModel.library_name || '-'}</Descriptions.Item>
              <Descriptions.Item label="License">{selectedModel.license || '-'}</Descriptions.Item>
              <Descriptions.Item label="Downloads">{formatNumber(selectedModel.downloads)}</Descriptions.Item>
              <Descriptions.Item label="Likes">{formatNumber(selectedModel.likes)}</Descriptions.Item>
            </Descriptions>

            <Title level={5}>Model Card</Title>
            {cardLoading ? (
              <div style={{ textAlign: 'center', padding: 40 }}>
                <Spin tip="Loading model card..." />
              </div>
            ) : (
              <div style={{ maxHeight: 400, overflow: 'auto', padding: 16, background: '#f5f5f5', borderRadius: 8 }}>
                <ReactMarkdown>{modelCardContent}</ReactMarkdown>
              </div>
            )}

            <div style={{ marginTop: 16, textAlign: 'right' }}>
              <Space>
                <Button
                  href={`https://huggingface.co/${selectedModel.id}`}
                  target="_blank"
                  icon={<LinkOutlined />}
                >
                  View on Hugging Face
                </Button>
                <Button
                  type="primary"
                  icon={<CloudDownloadOutlined />}
                  onClick={() => handleImportModel(selectedModel.id)}
                >
                  Import to Platform
                </Button>
              </Space>
            </div>
          </>
        )}
      </Modal>
    </div>
  );
}

// 格式化数字
function formatNumber(num: number): string {
  if (num >= 1000000) {
    return `${(num / 1000000).toFixed(1)}M`;
  }
  if (num >= 1000) {
    return `${(num / 1000).toFixed(1)}K`;
  }
  return num.toString();
}

// 模拟数据
function getMockModels(): ModelInfo[] {
  return [
    {
      id: 'meta-llama/Llama-2-7b-chat-hf',
      author: 'meta-llama',
      model_name: 'Llama-2-7b-chat-hf',
      sha: 'abc123',
      last_modified: '2024-01-15T00:00:00Z',
      private: false,
      pipeline_tag: 'text-generation',
      tags: ['llama', 'pytorch', 'text-generation'],
      downloads: 5000000,
      likes: 12000,
      library_name: 'transformers',
      license: 'llama2',
    },
    {
      id: 'BAAI/bge-large-zh-v1.5',
      author: 'BAAI',
      model_name: 'bge-large-zh-v1.5',
      sha: 'def456',
      last_modified: '2024-01-10T00:00:00Z',
      private: false,
      pipeline_tag: 'feature-extraction',
      tags: ['embedding', 'chinese', 'sentence-transformers'],
      downloads: 2000000,
      likes: 5000,
      library_name: 'sentence-transformers',
      license: 'mit',
    },
    {
      id: 'Qwen/Qwen-7B-Chat',
      author: 'Qwen',
      model_name: 'Qwen-7B-Chat',
      sha: 'ghi789',
      last_modified: '2024-01-12T00:00:00Z',
      private: false,
      pipeline_tag: 'text-generation',
      tags: ['qwen', 'chinese', 'chat'],
      downloads: 3000000,
      likes: 8000,
      library_name: 'transformers',
      license: 'tongyi-qianwen',
    },
  ];
}

function getMockDatasets(): DatasetInfo[] {
  return [
    {
      id: 'shibing624/medical',
      author: 'shibing624',
      dataset_name: 'medical',
      sha: 'abc123',
      last_modified: '2024-01-05T00:00:00Z',
      private: false,
      tags: ['chinese', 'medical', 'qa'],
      downloads: 50000,
      likes: 200,
    },
    {
      id: 'squad',
      author: 'rajpurkar',
      dataset_name: 'squad',
      sha: 'def456',
      last_modified: '2023-12-01T00:00:00Z',
      private: false,
      tags: ['question-answering', 'english'],
      downloads: 1000000,
      likes: 5000,
    },
  ];
}

export default HuggingFaceHub;
