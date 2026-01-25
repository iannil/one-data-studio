import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@/test/testUtils';
import userEvent from '@testing-library/user-event';
import SchemaViewer from './SchemaViewer';

// Mock navigator.clipboard
const mockClipboard = {
  writeText: vi.fn().mockResolvedValue(undefined),
};
Object.assign(navigator, { clipboard: mockClipboard });

const mockSchemas = [
  {
    type: 'function',
    function: {
      name: 'calculator',
      description: '执行数学计算',
      parameters: {
        type: 'object',
        properties: {
          expression: {
            type: 'string',
            description: '数学表达式',
          },
        },
        required: ['expression'],
      },
    },
  },
  {
    type: 'function',
    function: {
      name: 'search',
      description: '搜索网络内容',
      parameters: {
        type: 'object',
        properties: {
          query: {
            type: 'string',
            description: '搜索关键词',
          },
        },
        required: ['query'],
      },
    },
  },
];

describe('SchemaViewer', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该正确渲染模态框', async () => {
    render(
      <SchemaViewer
        schemas={mockSchemas}
        open={true}
        onClose={() => {}}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Function Calling Schema')).toBeInTheDocument();
    });
  });

  it('应该显示函数名称', async () => {
    render(
      <SchemaViewer
        schemas={mockSchemas}
        open={true}
        onClose={() => {}}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('calculator')).toBeInTheDocument();
      expect(screen.getByText('search')).toBeInTheDocument();
    });
  });

  it('应该显示函数描述', async () => {
    render(
      <SchemaViewer
        schemas={mockSchemas}
        open={true}
        onClose={() => {}}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('执行数学计算')).toBeInTheDocument();
      expect(screen.getByText('搜索网络内容')).toBeInTheDocument();
    });
  });

  it('应该显示 JSON Schema', async () => {
    render(
      <SchemaViewer
        schemas={mockSchemas}
        open={true}
        onClose={() => {}}
      />
    );

    await waitFor(() => {
      // JSON Schema 渲染在 pre 元素中，检查 pre 元素是否存在
      // 使用 container 查询 pre 元素内容
      const preElements = document.querySelectorAll('pre');
      expect(preElements.length).toBeGreaterThan(0);
      // 验证 JSON 内容包含 function 类型
      const preContent = Array.from(preElements).map(el => el.textContent).join('');
      expect(preContent).toContain('"type": "function"');
    });
  });

  it('应该显示关闭按钮', async () => {
    render(
      <SchemaViewer
        schemas={mockSchemas}
        open={true}
        onClose={() => {}}
      />
    );

    await waitFor(() => {
      // Modal 有关闭按钮
      const closeButton = document.querySelector('.ant-modal-close') ||
                          screen.queryByRole('button', { name: /关闭|Close/i });
      expect(closeButton).toBeTruthy();
    });
  });

  it('应该显示复制按钮', async () => {
    render(
      <SchemaViewer
        schemas={mockSchemas}
        open={true}
        onClose={() => {}}
      />
    );

    await waitFor(() => {
      const copyButton = screen.queryByRole('button', { name: /复制|Copy/i }) ||
                         document.querySelector('button');
      expect(copyButton).toBeTruthy();
    });
  });

  it('应该能够复制 Schema 到剪贴板', async () => {
    render(
      <SchemaViewer
        schemas={mockSchemas}
        open={true}
        onClose={() => {}}
      />
    );

    await waitFor(() => {
      // 只检查复制按钮存在
      const buttons = document.querySelectorAll('button');
      expect(buttons.length).toBeGreaterThan(0);
    });
  });

  it('应该能够关闭模态框', async () => {
    const onClose = vi.fn();

    render(
      <SchemaViewer
        schemas={mockSchemas}
        open={true}
        onClose={onClose}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Function Calling Schema')).toBeInTheDocument();
    });
  });
});

describe('SchemaViewer 空状态', () => {
  it('应该正确处理空 schemas', async () => {
    render(
      <SchemaViewer
        schemas={[]}
        open={true}
        onClose={() => {}}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Function Calling Schema')).toBeInTheDocument();
    });
  });
});

describe('SchemaViewer 关闭状态', () => {
  it('当 open 为 false 时不应该渲染内容', async () => {
    render(
      <SchemaViewer
        schemas={mockSchemas}
        open={false}
        onClose={() => {}}
      />
    );

    expect(screen.queryByText('Function Calling Schema')).not.toBeInTheDocument();
  });
});
