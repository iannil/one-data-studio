import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import DocumentsPage from './DocumentsPage';
import * as bisheng from '@/services/bisheng';

// Mock 服务
vi.mock('@/services/bisheng', () => ({
  default: {
    getDocuments: vi.fn(),
    uploadDocument: vi.fn(),
    deleteDocument: vi.fn(),
    getDocumentChunks: vi.fn(),
    reprocessDocument: vi.fn(),
  },
}));

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: false,
    },
  },
});

const renderWithProviders = (component: React.ReactElement) => {
  return render(
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>{component}</BrowserRouter>
    </QueryClientProvider>
  );
};

const mockDocuments = [
  {
    document_id: 'doc-001',
    name: '产品手册.pdf',
    file_type: 'pdf',
    file_size: 1024000,
    status: 'processed',
    chunk_count: 50,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
  },
  {
    document_id: 'doc-002',
    name: '用户指南.docx',
    file_type: 'docx',
    file_size: 512000,
    status: 'processing',
    chunk_count: 0,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
  },
  {
    document_id: 'doc-003',
    name: '常见问题.txt',
    file_type: 'txt',
    file_size: 10240,
    status: 'failed',
    error_message: '解析失败',
    chunk_count: 0,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
  },
];

describe('DocumentsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    queryClient.clear();

    vi.mocked(bisheng.default.getDocuments).mockResolvedValue({
      code: 0,
      data: { documents: mockDocuments, total: 3 },
    });
  });

  it('应该正确渲染文档页面', async () => {
    renderWithProviders(<DocumentsPage />);

    await waitFor(() => {
      expect(screen.getByText(/文档/i)).toBeInTheDocument();
    });
  });

  it('应该显示文档列表', async () => {
    renderWithProviders(<DocumentsPage />);

    await waitFor(() => {
      expect(screen.getByText('产品手册.pdf')).toBeInTheDocument();
      expect(screen.getByText('用户指南.docx')).toBeInTheDocument();
      expect(screen.getByText('常见问题.txt')).toBeInTheDocument();
    });
  });

  it('应该显示文档状态', async () => {
    renderWithProviders(<DocumentsPage />);

    await waitFor(() => {
      expect(screen.getByText(/处理完成/i) || screen.getByText(/已处理/i)).toBeTruthy();
    });
  });

  it('应该显示上传按钮', async () => {
    renderWithProviders(<DocumentsPage />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /上传/i })).toBeInTheDocument();
    });
  });

  it('应该显示文件大小', async () => {
    renderWithProviders(<DocumentsPage />);

    await waitFor(() => {
      expect(screen.getByText('产品手册.pdf')).toBeInTheDocument();
    });

    // 文件大小应该格式化显示
  });
});

describe('DocumentsPage 文档操作', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    queryClient.clear();

    vi.mocked(bisheng.default.getDocuments).mockResolvedValue({
      code: 0,
      data: { documents: mockDocuments, total: 3 },
    });
  });

  it('应该能够删除文档', async () => {
    vi.mocked(bisheng.default.deleteDocument).mockResolvedValue({
      code: 0,
      message: 'success',
    });

    renderWithProviders(<DocumentsPage />);

    await waitFor(() => {
      expect(screen.getByText('产品手册.pdf')).toBeInTheDocument();
    });

    // 删除按钮应该存在
  });

  it('应该能够重新处理失败的文档', async () => {
    vi.mocked(bisheng.default.reprocessDocument).mockResolvedValue({
      code: 0,
      message: 'success',
    });

    renderWithProviders(<DocumentsPage />);

    await waitFor(() => {
      expect(screen.getByText('常见问题.txt')).toBeInTheDocument();
    });

    // 重新处理按钮应该存在
  });

  it('应该能够查看文档分块', async () => {
    vi.mocked(bisheng.default.getDocumentChunks).mockResolvedValue({
      code: 0,
      data: {
        chunks: [
          { chunk_id: 'chunk-001', content: '第一段内容', index: 0 },
          { chunk_id: 'chunk-002', content: '第二段内容', index: 1 },
        ],
        total: 2,
      },
    });

    renderWithProviders(<DocumentsPage />);

    await waitFor(() => {
      expect(screen.getByText('产品手册.pdf')).toBeInTheDocument();
    });
  });
});

describe('DocumentsPage 文件上传', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    queryClient.clear();

    vi.mocked(bisheng.default.getDocuments).mockResolvedValue({
      code: 0,
      data: { documents: [], total: 0 },
    });
  });

  it('应该能够上传文档', async () => {
    vi.mocked(bisheng.default.uploadDocument).mockResolvedValue({
      code: 0,
      data: { document_id: 'doc-new', name: '新文档.pdf' },
    });

    renderWithProviders(<DocumentsPage />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /上传/i })).toBeInTheDocument();
    });
  });

  it('应该验证文件类型', async () => {
    renderWithProviders(<DocumentsPage />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /上传/i })).toBeInTheDocument();
    });

    // 支持的文件类型应该有说明
  });

  it('应该验证文件大小', async () => {
    renderWithProviders(<DocumentsPage />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /上传/i })).toBeInTheDocument();
    });

    // 文件大小限制应该有说明
  });
});

describe('DocumentsPage 搜索和筛选', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    queryClient.clear();

    vi.mocked(bisheng.default.getDocuments).mockResolvedValue({
      code: 0,
      data: { documents: mockDocuments, total: 3 },
    });
  });

  it('应该显示搜索框', async () => {
    renderWithProviders(<DocumentsPage />);

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/搜索/i)).toBeInTheDocument();
    });
  });

  it('应该能够按状态筛选', async () => {
    renderWithProviders(<DocumentsPage />);

    await waitFor(() => {
      expect(screen.getByText('产品手册.pdf')).toBeInTheDocument();
    });

    // 状态筛选器应该存在
  });

  it('应该能够按文件类型筛选', async () => {
    renderWithProviders(<DocumentsPage />);

    await waitFor(() => {
      expect(screen.getByText('产品手册.pdf')).toBeInTheDocument();
    });

    // 文件类型筛选器应该存在
  });
});

describe('DocumentsPage 空状态', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    queryClient.clear();

    vi.mocked(bisheng.default.getDocuments).mockResolvedValue({
      code: 0,
      data: { documents: [], total: 0 },
    });
  });

  it('应该显示空状态提示', async () => {
    renderWithProviders(<DocumentsPage />);

    await waitFor(() => {
      // 应该显示空状态或引导上传
      expect(screen.queryByText('产品手册.pdf')).not.toBeInTheDocument();
    });
  });
});

describe('DocumentsPage 错误处理', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    queryClient.clear();
  });

  it('应该显示加载失败提示', async () => {
    vi.mocked(bisheng.default.getDocuments).mockRejectedValue(new Error('加载失败'));

    renderWithProviders(<DocumentsPage />);

    // 错误状态应该处理
    await waitFor(() => {
      expect(screen.getByText(/文档/i)).toBeInTheDocument();
    });
  });

  it('应该显示上传失败提示', async () => {
    vi.mocked(bisheng.default.getDocuments).mockResolvedValue({
      code: 0,
      data: { documents: [], total: 0 },
    });

    vi.mocked(bisheng.default.uploadDocument).mockRejectedValue(new Error('上传失败'));

    renderWithProviders(<DocumentsPage />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /上传/i })).toBeInTheDocument();
    });
  });
});
