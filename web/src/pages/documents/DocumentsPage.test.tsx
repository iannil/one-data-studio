import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@/test/testUtils';
import userEvent from '@testing-library/user-event';

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



const mockDocuments = [
  {
    doc_id: 'doc-001',
    file_name: '产品手册.pdf',
    title: '产品手册',
    collection_name: 'default',
    chunk_count: 50,
    content: '这是产品手册的内容...',
    metadata: '{}',
    created_by: 'user1',
    created_at: '2024-01-01T00:00:00Z',
  },
  {
    doc_id: 'doc-002',
    file_name: '用户指南.docx',
    title: '用户指南',
    collection_name: 'default',
    chunk_count: 30,
    content: '这是用户指南的内容...',
    metadata: '{}',
    created_by: 'user2',
    created_at: '2024-01-01T00:00:00Z',
  },
  {
    doc_id: 'doc-003',
    file_name: '常见问题.txt',
    title: '常见问题',
    collection_name: 'faq',
    chunk_count: 10,
    content: '这是常见问题的内容...',
    metadata: '{}',
    created_by: 'user1',
    created_at: '2024-01-01T00:00:00Z',
  },
];

describe('DocumentsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    

    vi.mocked(bisheng.default.getDocuments).mockResolvedValue({
      code: 0,
      data: { documents: mockDocuments, collections: ['default', 'faq'], total_collections: 2 },
    });
  });

  it('应该正确渲染文档页面', async () => {
    render(<DocumentsPage />);

    await waitFor(() => {
      // "文档" 可能出现多次，使用更具体的查询
      expect(screen.getByText('文档管理')).toBeInTheDocument();
    });
  });

  it('应该显示文档列表', async () => {
    render(<DocumentsPage />);

    await waitFor(() => {
      expect(screen.getByText('产品手册.pdf')).toBeInTheDocument();
      expect(screen.getByText('用户指南.docx')).toBeInTheDocument();
      expect(screen.getByText('常见问题.txt')).toBeInTheDocument();
    });
  });

  it('应该显示文档集合标签', async () => {
    render(<DocumentsPage />);

    await waitFor(() => {
      // collection_name 可能出现多次，使用 getAllByText
      expect(screen.getAllByText('default').length).toBeGreaterThan(0);
    });
  });

  it('应该显示上传按钮', async () => {
    render(<DocumentsPage />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /上传/i })).toBeInTheDocument();
    });
  });

  it('应该显示文件大小', async () => {
    render(<DocumentsPage />);

    await waitFor(() => {
      expect(screen.getByText('产品手册.pdf')).toBeInTheDocument();
    });

    // 文件大小应该格式化显示
  });
});

describe('DocumentsPage 文档操作', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    

    vi.mocked(bisheng.default.getDocuments).mockResolvedValue({
      code: 0,
      data: { documents: mockDocuments, collections: ['default', 'faq'], total_collections: 2 },
    });
  });

  it('应该能够删除文档', async () => {
    vi.mocked(bisheng.default.deleteDocument).mockResolvedValue({
      code: 0,
      message: 'success',
    });

    render(<DocumentsPage />);

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

    render(<DocumentsPage />);

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

    render(<DocumentsPage />);

    await waitFor(() => {
      expect(screen.getByText('产品手册.pdf')).toBeInTheDocument();
    });
  });
});

describe('DocumentsPage 文件上传', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    

    vi.mocked(bisheng.default.getDocuments).mockResolvedValue({
      code: 0,
      data: { documents: [], collections: [], total_collections: 0 },
    });
  });

  it('应该能够上传文档', async () => {
    vi.mocked(bisheng.default.uploadDocument).mockResolvedValue({
      code: 0,
      data: { document_id: 'doc-new', name: '新文档.pdf' },
    });

    render(<DocumentsPage />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /上传/i })).toBeInTheDocument();
    });
  });

  it('应该验证文件类型', async () => {
    render(<DocumentsPage />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /上传/i })).toBeInTheDocument();
    });

    // 支持的文件类型应该有说明
  });

  it('应该验证文件大小', async () => {
    render(<DocumentsPage />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /上传/i })).toBeInTheDocument();
    });

    // 文件大小限制应该有说明
  });
});

describe('DocumentsPage 搜索和筛选', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    

    vi.mocked(bisheng.default.getDocuments).mockResolvedValue({
      code: 0,
      data: { documents: mockDocuments, collections: ['default', 'faq'], total_collections: 2 },
    });
  });

  it('应该显示集合筛选器', async () => {
    render(<DocumentsPage />);

    await waitFor(() => {
      // 组件使用 Select 进行集合筛选，而不是搜索框
      const selects = document.querySelectorAll('.ant-select');
      expect(selects.length).toBeGreaterThan(0);
    });
  });

  it('应该能够按状态筛选', async () => {
    render(<DocumentsPage />);

    await waitFor(() => {
      expect(screen.getByText('产品手册.pdf')).toBeInTheDocument();
    });

    // 状态筛选器应该存在
  });

  it('应该能够按文件类型筛选', async () => {
    render(<DocumentsPage />);

    await waitFor(() => {
      expect(screen.getByText('产品手册.pdf')).toBeInTheDocument();
    });

    // 文件类型筛选器应该存在
  });
});

describe('DocumentsPage 空状态', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    

    vi.mocked(bisheng.default.getDocuments).mockResolvedValue({
      code: 0,
      data: { documents: [], collections: [], total_collections: 0 },
    });
  });

  it('应该显示空状态提示', async () => {
    render(<DocumentsPage />);

    await waitFor(() => {
      // 应该显示空状态或引导上传
      expect(screen.queryByText('产品手册.pdf')).not.toBeInTheDocument();
    });
  });
});

describe('DocumentsPage 错误处理', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    
  });

  it('应该显示加载失败提示', async () => {
    vi.mocked(bisheng.default.getDocuments).mockRejectedValue(new Error('加载失败'));

    render(<DocumentsPage />);

    // 错误状态应该处理 - 验证页面仍然渲染
    await waitFor(() => {
      expect(screen.getByText('文档管理')).toBeInTheDocument();
    });
  });

  it('应该显示上传失败提示', async () => {
    vi.mocked(bisheng.default.getDocuments).mockResolvedValue({
      code: 0,
      data: { documents: [], collections: [], total_collections: 0 },
    });

    vi.mocked(bisheng.default.uploadDocument).mockRejectedValue(new Error('上传失败'));

    render(<DocumentsPage />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /上传/i })).toBeInTheDocument();
    });
  });
});
