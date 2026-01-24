import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import HuggingFaceHub from './HuggingFaceHub';
import api from '../../services/api';

// Mock API
vi.mock('../../services/api', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

// Mock antd message
vi.mock('antd', async () => {
  const actual = await vi.importActual('antd');
  return {
    ...actual,
    message: {
      error: vi.fn(),
      success: vi.fn(),
    },
  };
});

// Mock react-i18next
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

// Mock ReactMarkdown
vi.mock('react-markdown', () => ({
  default: ({ children }: { children: string }) => <div>{children}</div>,
}));

const mockModels = [
  {
    id: 'meta-llama/Llama-2-7b-chat-hf',
    author: 'meta-llama',
    model_name: 'Llama-2-7b-chat-hf',
    sha: 'abc123',
    last_modified: '2024-01-15T00:00:00Z',
    private: false,
    pipeline_tag: 'text-generation',
    tags: ['llama', 'pytorch'],
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
    tags: ['embedding', 'chinese'],
    downloads: 2000000,
    likes: 5000,
    library_name: 'sentence-transformers',
    license: 'mit',
  },
];

const mockDatasets = [
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
];

describe('HuggingFaceHub', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    vi.mocked(api.get).mockImplementation((url: string) => {
      if (url.includes('/models')) {
        return Promise.resolve({ data: mockModels });
      }
      if (url.includes('/datasets')) {
        return Promise.resolve({ data: mockDatasets });
      }
      return Promise.resolve({ data: {} });
    });
  });

  it('应该正确渲染页面标题', async () => {
    render(<HuggingFaceHub />);

    await waitFor(() => {
      expect(screen.getByText(/Hugging Face Hub/)).toBeInTheDocument();
    });
  });

  it('应该显示 Models 标签页', async () => {
    render(<HuggingFaceHub />);

    await waitFor(() => {
      expect(screen.getByRole('tab', { name: 'Models' })).toBeInTheDocument();
    });
  });

  it('应该显示 Datasets 标签页', async () => {
    render(<HuggingFaceHub />);

    await waitFor(() => {
      expect(screen.getByRole('tab', { name: 'Datasets' })).toBeInTheDocument();
    });
  });

  it('应该显示刷新按钮', async () => {
    render(<HuggingFaceHub />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Refresh/i })).toBeInTheDocument();
    });
  });
});

describe('HuggingFaceHub 搜索功能', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    vi.mocked(api.get).mockResolvedValue({ data: mockModels });
  });

  it('应该显示搜索框', async () => {
    render(<HuggingFaceHub />);

    await waitFor(() => {
      expect(
        screen.getByPlaceholderText('Search models or datasets...')
      ).toBeInTheDocument();
    });
  });

  it('应该能够输入搜索内容', async () => {
    const user = userEvent.setup();
    render(<HuggingFaceHub />);

    await waitFor(() => {
      expect(
        screen.getByPlaceholderText('Search models or datasets...')
      ).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText('Search models or datasets...');
    await user.type(searchInput, 'llama');

    expect(searchInput).toHaveValue('llama');
  });
});

describe('HuggingFaceHub 过滤器', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    vi.mocked(api.get).mockResolvedValue({ data: mockModels });
  });

  it('应该显示 Pipeline 过滤器', async () => {
    render(<HuggingFaceHub />);

    await waitFor(() => {
      expect(screen.getByText('Pipeline')).toBeInTheDocument();
    });
  });

  it('应该显示 Library 过滤器', async () => {
    render(<HuggingFaceHub />);

    await waitFor(() => {
      expect(screen.getByText('Library')).toBeInTheDocument();
    });
  });
});

describe('HuggingFaceHub 模型列表', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    vi.mocked(api.get).mockResolvedValue({ data: mockModels });
  });

  it('应该显示模型名称', async () => {
    render(<HuggingFaceHub />);

    await waitFor(() => {
      expect(screen.getByText('Llama-2-7b-chat-hf')).toBeInTheDocument();
      expect(screen.getByText('bge-large-zh-v1.5')).toBeInTheDocument();
    });
  });

  it('应该显示模型作者', async () => {
    render(<HuggingFaceHub />);

    await waitFor(() => {
      expect(screen.getByText('meta-llama')).toBeInTheDocument();
      expect(screen.getByText('BAAI')).toBeInTheDocument();
    });
  });

  it('应该显示 Pipeline 标签', async () => {
    render(<HuggingFaceHub />);

    await waitFor(() => {
      expect(screen.getByText('text-generation')).toBeInTheDocument();
      expect(screen.getByText('feature-extraction')).toBeInTheDocument();
    });
  });

  it('应该显示 Library 标签', async () => {
    render(<HuggingFaceHub />);

    await waitFor(() => {
      expect(screen.getByText('transformers')).toBeInTheDocument();
      expect(screen.getByText('sentence-transformers')).toBeInTheDocument();
    });
  });

  it('应该显示 License 标签', async () => {
    render(<HuggingFaceHub />);

    await waitFor(() => {
      expect(screen.getByText('llama2')).toBeInTheDocument();
      expect(screen.getByText('mit')).toBeInTheDocument();
    });
  });

  it('应该显示下载数', async () => {
    render(<HuggingFaceHub />);

    await waitFor(() => {
      expect(screen.getByText('5.0M')).toBeInTheDocument(); // 5000000
      expect(screen.getByText('2.0M')).toBeInTheDocument(); // 2000000
    });
  });

  it('应该显示点赞数', async () => {
    render(<HuggingFaceHub />);

    await waitFor(() => {
      expect(screen.getByText('12.0K')).toBeInTheDocument(); // 12000
      expect(screen.getByText('5.0K')).toBeInTheDocument(); // 5000
    });
  });
});

describe('HuggingFaceHub 模型操作', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    vi.mocked(api.get).mockResolvedValue({ data: mockModels });
  });

  it('应该显示 Details 按钮', async () => {
    render(<HuggingFaceHub />);

    await waitFor(() => {
      const detailButtons = screen.getAllByRole('button', { name: /Details/i });
      expect(detailButtons.length).toBeGreaterThan(0);
    });
  });

  it('应该显示 Import 按钮', async () => {
    render(<HuggingFaceHub />);

    await waitFor(() => {
      const importButtons = screen.getAllByRole('button', { name: /Import/i });
      expect(importButtons.length).toBeGreaterThan(0);
    });
  });

  it('点击 Details 应该打开模态框', async () => {
    const user = userEvent.setup();

    vi.mocked(api.get).mockImplementation((url: string) => {
      if (url.includes('/card')) {
        return Promise.resolve({ data: { content: '# Model Card\n\nTest content' } });
      }
      return Promise.resolve({ data: mockModels });
    });

    render(<HuggingFaceHub />);

    await waitFor(() => {
      expect(screen.getByText('Llama-2-7b-chat-hf')).toBeInTheDocument();
    });

    const detailButtons = screen.getAllByRole('button', { name: /Details/i });
    await user.click(detailButtons[0]);

    await waitFor(() => {
      expect(screen.getByText('Model Card')).toBeInTheDocument();
    });
  });

  it('点击 Import 应该调用导入 API', async () => {
    const user = userEvent.setup();
    vi.mocked(api.post).mockResolvedValue({ data: {} });

    render(<HuggingFaceHub />);

    await waitFor(() => {
      expect(screen.getByText('Llama-2-7b-chat-hf')).toBeInTheDocument();
    });

    const importButtons = screen.getAllByRole('button', { name: /Import/i });
    await user.click(importButtons[0]);

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith('/api/v1/models/import', {
        source: 'huggingface',
        model_id: 'meta-llama/Llama-2-7b-chat-hf',
      });
    });
  });
});

describe('HuggingFaceHub Datasets 标签页', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    vi.mocked(api.get).mockImplementation((url: string) => {
      if (url.includes('/models')) {
        return Promise.resolve({ data: mockModels });
      }
      if (url.includes('/datasets')) {
        return Promise.resolve({ data: mockDatasets });
      }
      return Promise.resolve({ data: {} });
    });
  });

  it('切换到 Datasets 标签页应该显示数据集', async () => {
    const user = userEvent.setup();
    render(<HuggingFaceHub />);

    await waitFor(() => {
      expect(screen.getByRole('tab', { name: 'Datasets' })).toBeInTheDocument();
    });

    await user.click(screen.getByRole('tab', { name: 'Datasets' }));

    await waitFor(() => {
      expect(screen.getByText('medical')).toBeInTheDocument();
      expect(screen.getByText('shibing624')).toBeInTheDocument();
    });
  });

  it('Datasets 标签页应该隐藏 Pipeline 和 Library 过滤器', async () => {
    const user = userEvent.setup();
    render(<HuggingFaceHub />);

    await waitFor(() => {
      expect(screen.getByRole('tab', { name: 'Datasets' })).toBeInTheDocument();
    });

    await user.click(screen.getByRole('tab', { name: 'Datasets' }));

    await waitFor(() => {
      // Pipeline 和 Library 过滤器不应该在 Datasets 标签页显示
      const pipelineSelects = document.querySelectorAll('[placeholder="Pipeline"]');
      expect(pipelineSelects.length).toBe(0);
    });
  });
});

describe('HuggingFaceHub 刷新功能', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    vi.mocked(api.get).mockResolvedValue({ data: mockModels });
  });

  it('点击刷新按钮应该重新加载数据', async () => {
    const user = userEvent.setup();
    render(<HuggingFaceHub />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Refresh/i })).toBeInTheDocument();
    });

    vi.clearAllMocks();
    vi.mocked(api.get).mockResolvedValue({ data: mockModels });

    await user.click(screen.getByRole('button', { name: /Refresh/i }));

    await waitFor(() => {
      expect(api.get).toHaveBeenCalled();
    });
  });
});

describe('HuggingFaceHub 加载状态', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('加载时应该显示表格 loading 状态', async () => {
    vi.mocked(api.get).mockImplementation(
      () => new Promise(() => {}) // 永不解析
    );

    render(<HuggingFaceHub />);

    expect(document.querySelector('.ant-spin')).toBeInTheDocument();
  });
});

describe('HuggingFaceHub 错误处理', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('API 错误应该使用模拟数据', async () => {
    vi.mocked(api.get).mockRejectedValue(new Error('Network error'));

    render(<HuggingFaceHub />);

    // 使用模拟数据后应该显示模型
    await waitFor(() => {
      expect(screen.getByText('Llama-2-7b-chat-hf')).toBeInTheDocument();
    });
  });
});

describe('HuggingFaceHub 分页', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    vi.mocked(api.get).mockResolvedValue({ data: mockModels });
  });

  it('应该显示分页组件', async () => {
    render(<HuggingFaceHub />);

    await waitFor(() => {
      expect(document.querySelector('.ant-pagination')).toBeInTheDocument();
    });
  });
});

describe('HuggingFaceHub 模型详情弹窗', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    vi.mocked(api.get).mockImplementation((url: string) => {
      if (url.includes('/card')) {
        return Promise.resolve({ data: { content: '# Model Card' } });
      }
      return Promise.resolve({ data: mockModels });
    });
  });

  it('模型详情弹窗应该显示模型信息', async () => {
    const user = userEvent.setup();
    render(<HuggingFaceHub />);

    await waitFor(() => {
      expect(screen.getByText('Llama-2-7b-chat-hf')).toBeInTheDocument();
    });

    const detailButtons = screen.getAllByRole('button', { name: /Details/i });
    await user.click(detailButtons[0]);

    await waitFor(() => {
      expect(screen.getByText('Author')).toBeInTheDocument();
      expect(screen.getByText('Pipeline')).toBeInTheDocument();
      expect(screen.getByText('Downloads')).toBeInTheDocument();
      expect(screen.getByText('Likes')).toBeInTheDocument();
    });
  });

  it('模型详情弹窗应该有 View on Hugging Face 链接', async () => {
    const user = userEvent.setup();
    render(<HuggingFaceHub />);

    await waitFor(() => {
      expect(screen.getByText('Llama-2-7b-chat-hf')).toBeInTheDocument();
    });

    const detailButtons = screen.getAllByRole('button', { name: /Details/i });
    await user.click(detailButtons[0]);

    await waitFor(() => {
      expect(screen.getByText('View on Hugging Face')).toBeInTheDocument();
    });
  });
});
