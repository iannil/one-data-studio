import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
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
      // JSON 中应该包含 type: function
      expect(screen.getByText(/"type": "function"/)).toBeInTheDocument();
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
      expect(screen.getByRole('button', { name: /关闭/i })).toBeInTheDocument();
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
      expect(screen.getByRole('button', { name: /复制/i })).toBeInTheDocument();
    });
  });

  it('应该能够复制 Schema 到剪贴板', async () => {
    const user = userEvent.setup();
    render(
      <SchemaViewer
        schemas={mockSchemas}
        open={true}
        onClose={() => {}}
      />
    );

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /复制/i })).toBeInTheDocument();
    });

    await user.click(screen.getByRole('button', { name: /复制/i }));

    await waitFor(() => {
      expect(mockClipboard.writeText).toHaveBeenCalledWith(
        JSON.stringify(mockSchemas, null, 2)
      );
    });
  });

  it('应该能够关闭模态框', async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();

    render(
      <SchemaViewer
        schemas={mockSchemas}
        open={true}
        onClose={onClose}
      />
    );

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /关闭/i })).toBeInTheDocument();
    });

    await user.click(screen.getByRole('button', { name: /关闭/i }));

    expect(onClose).toHaveBeenCalled();
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
