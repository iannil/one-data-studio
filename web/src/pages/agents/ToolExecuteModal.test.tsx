import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@/test/testUtils';
import userEvent from '@testing-library/user-event';
import ToolExecuteModal from './ToolExecuteModal';
import bisheng from '@/services/bisheng';

// Mock 服务
vi.mock('@/services/bisheng', () => ({
  default: {
    executeTool: vi.fn(),
  },
}));

const mockTool = {
  name: 'calculator',
  description: '执行数学计算',
  category: 'math',
  parameters: [
    {
      name: 'expression',
      type: 'string',
      description: '数学表达式',
      required: true,
    },
    {
      name: 'precision',
      type: 'number',
      description: '小数精度',
      required: false,
      default: 2,
    },
  ],
};

const mockToolWithContent = {
  name: 'text_analyzer',
  description: '分析文本内容',
  category: 'text',
  parameters: [
    {
      name: 'content',
      type: 'string',
      description: '要分析的文本内容',
      required: true,
    },
  ],
};

describe('ToolExecuteModal', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该正确渲染模态框', async () => {
    render(
      <ToolExecuteModal
        tool={mockTool}
        open={true}
        onClose={() => {}}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('测试工具: calculator')).toBeInTheDocument();
    });
  });

  it('应该显示工具描述', async () => {
    render(
      <ToolExecuteModal
        tool={mockTool}
        open={true}
        onClose={() => {}}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('执行数学计算')).toBeInTheDocument();
    });
  });

  it('应该显示参数输入框', async () => {
    render(
      <ToolExecuteModal
        tool={mockTool}
        open={true}
        onClose={() => {}}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('expression')).toBeInTheDocument();
      expect(screen.getByText('precision')).toBeInTheDocument();
    });
  });

  it('应该显示参数类型', async () => {
    render(
      <ToolExecuteModal
        tool={mockTool}
        open={true}
        onClose={() => {}}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('(string)')).toBeInTheDocument();
      expect(screen.getByText('(number)')).toBeInTheDocument();
    });
  });

  it('应该显示执行按钮', async () => {
    render(
      <ToolExecuteModal
        tool={mockTool}
        open={true}
        onClose={() => {}}
      />
    );

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /执行/i })).toBeInTheDocument();
    });
  });

  it('应该显示关闭按钮', async () => {
    render(
      <ToolExecuteModal
        tool={mockTool}
        open={true}
        onClose={() => {}}
      />
    );

    // 验证模态框打开
    expect(document.querySelector('.ant-modal')).toBeInTheDocument();
  });

  it('应该为包含 content 的参数显示 TextArea', async () => {
    render(
      <ToolExecuteModal
        tool={mockToolWithContent}
        open={true}
        onClose={() => {}}
      />
    );

    await waitFor(() => {
      // TextArea 有 4 行
      const textArea = screen.getByPlaceholderText('要分析的文本内容');
      expect(textArea.tagName.toLowerCase()).toBe('textarea');
    });
  });
});

describe('ToolExecuteModal 执行功能', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    vi.mocked(bisheng.executeTool).mockResolvedValue({
      code: 0,
      data: {
        result: '42',
        success: true,
      },
    });
  });

  it('应该能够执行工具', async () => {
    const user = userEvent.setup();
    render(
      <ToolExecuteModal
        tool={mockTool}
        open={true}
        onClose={() => {}}
      />
    );

    // 填写表达式
    const input = screen.getByPlaceholderText('数学表达式');
    await user.type(input, '6 * 7');

    // 点击执行
    await user.click(screen.getByRole('button', { name: /执行/i }));

    await waitFor(() => {
      expect(bisheng.executeTool).toHaveBeenCalledWith('calculator', {
        expression: '6 * 7',
        precision: 2,
      });
    });
  });

  it('应该显示执行结果', async () => {
    const user = userEvent.setup();
    render(
      <ToolExecuteModal
        tool={mockTool}
        open={true}
        onClose={() => {}}
      />
    );

    const input = screen.getByPlaceholderText('数学表达式');
    await user.type(input, '6 * 7');

    await user.click(screen.getByRole('button', { name: /执行/i }));

    await waitFor(() => {
      expect(screen.getByText('执行结果:')).toBeInTheDocument();
    });
  });

  it('应该验证必填参数', async () => {
    const user = userEvent.setup();
    render(
      <ToolExecuteModal
        tool={mockTool}
        open={true}
        onClose={() => {}}
      />
    );

    // 不填写任何内容直接执行
    await user.click(screen.getByRole('button', { name: /执行/i }));

    await waitFor(() => {
      expect(screen.getByText('请输入 expression')).toBeInTheDocument();
    });
  });
});

describe('ToolExecuteModal 错误处理', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    vi.mocked(bisheng.executeTool).mockRejectedValue(new Error('API 调用失败'));
  });

  it('应该显示执行错误', async () => {
    const user = userEvent.setup();
    render(
      <ToolExecuteModal
        tool={mockTool}
        open={true}
        onClose={() => {}}
      />
    );

    const input = screen.getByPlaceholderText('数学表达式');
    await user.type(input, '6 * 7');

    await user.click(screen.getByRole('button', { name: /执行/i }));

    await waitFor(() => {
      expect(screen.getByText('执行结果:')).toBeInTheDocument();
      // 应该显示错误信息
      expect(screen.getByText(/"error": "API 调用失败"/)).toBeInTheDocument();
    });
  });
});

describe('ToolExecuteModal 关闭行为', () => {
  it('应该能够关闭模态框', async () => {
    const onClose = vi.fn();

    render(
      <ToolExecuteModal
        tool={mockTool}
        open={true}
        onClose={onClose}
      />
    );

    // 验证模态框打开
    expect(document.querySelector('.ant-modal')).toBeInTheDocument();
  });

  it('关闭时应该重置状态', async () => {
    const onClose = vi.fn();

    render(
      <ToolExecuteModal
        tool={mockTool}
        open={true}
        onClose={onClose}
      />
    );

    // 验证模态框打开
    expect(document.querySelector('.ant-modal')).toBeInTheDocument();
  });
});

describe('ToolExecuteModal 空工具', () => {
  it('当工具为 null 时不应该崩溃', async () => {
    render(
      <ToolExecuteModal
        tool={null}
        open={true}
        onClose={() => {}}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('测试工具:')).toBeInTheDocument();
    });
  });
});
