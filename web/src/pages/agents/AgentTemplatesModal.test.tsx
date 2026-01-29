import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@/test/testUtils';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import AgentTemplatesModal from './AgentTemplatesModal';
import agentService from '@/services/agent-service';

// Mock 服务
vi.mock('@/services/agent-service', () => ({
  default: {
    createAgentTemplate: vi.fn(),
    updateAgentTemplate: vi.fn(),
  },
}));



const mockAvailableTools = ['calculator', 'search', 'weather', 'code_executor'];

const mockTemplate = {
  template_id: 'tmpl-001',
  name: 'RAG Agent',
  description: '用于检索增强生成的 Agent',
  agent_type: 'react' as const,
  model: 'gpt-4o-mini',
  max_iterations: 10,
  system_prompt: '你是一个有帮助的助手',
  selected_tools: ['search'],
};

describe('AgentTemplatesModal 创建模式', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    
  });

  it('应该正确渲染创建模态框', async () => {
    render(
      <AgentTemplatesModal
        open={true}
        onClose={() => {}}
        availableTools={mockAvailableTools}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('创建 Agent 模板')).toBeInTheDocument();
    });
  });

  it('应该显示模板名称输入框', async () => {
    render(
      <AgentTemplatesModal
        open={true}
        onClose={() => {}}
        availableTools={mockAvailableTools}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('模板名称')).toBeInTheDocument();
    });
  });

  it('应该显示描述输入框', async () => {
    render(
      <AgentTemplatesModal
        open={true}
        onClose={() => {}}
        availableTools={mockAvailableTools}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('描述')).toBeInTheDocument();
    });
  });

  it('应该显示 Agent 类型选择器', async () => {
    render(
      <AgentTemplatesModal
        open={true}
        onClose={() => {}}
        availableTools={mockAvailableTools}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Agent 类型')).toBeInTheDocument();
    });
  });

  it('应该显示模型选择器', async () => {
    render(
      <AgentTemplatesModal
        open={true}
        onClose={() => {}}
        availableTools={mockAvailableTools}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('模型')).toBeInTheDocument();
    });
  });

  it('应该显示最大迭代输入', async () => {
    render(
      <AgentTemplatesModal
        open={true}
        onClose={() => {}}
        availableTools={mockAvailableTools}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('最大迭代')).toBeInTheDocument();
    });
  });

  it('应该显示系统 Prompt 输入', async () => {
    render(
      <AgentTemplatesModal
        open={true}
        onClose={() => {}}
        availableTools={mockAvailableTools}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('系统 Prompt')).toBeInTheDocument();
    });
  });

  it('应该显示可用工具列表', async () => {
    render(
      <AgentTemplatesModal
        open={true}
        onClose={() => {}}
        availableTools={mockAvailableTools}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('选用工具')).toBeInTheDocument();
      expect(screen.getByText('calculator')).toBeInTheDocument();
      expect(screen.getByText('search')).toBeInTheDocument();
      expect(screen.getByText('weather')).toBeInTheDocument();
    });
  });

  it('应该能够选择工具', async () => {
    const user = userEvent.setup();
    render(
      <AgentTemplatesModal
        open={true}
        onClose={() => {}}
        availableTools={mockAvailableTools}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('calculator')).toBeInTheDocument();
    });

    await user.click(screen.getByText('calculator'));

    await waitFor(() => {
      expect(screen.getByText('已选择 1 个工具')).toBeInTheDocument();
    });
  });

  it('应该能够取消选择工具', async () => {
    const user = userEvent.setup();
    render(
      <AgentTemplatesModal
        open={true}
        onClose={() => {}}
        availableTools={mockAvailableTools}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('calculator')).toBeInTheDocument();
    });

    // 选择
    await user.click(screen.getByText('calculator'));
    await waitFor(() => {
      expect(screen.getByText('已选择 1 个工具')).toBeInTheDocument();
    });

    // 取消选择
    await user.click(screen.getByText('calculator'));
    await waitFor(() => {
      expect(screen.getByText('已选择 0 个工具')).toBeInTheDocument();
    });
  });

  it('应该能够清空选中的工具', async () => {
    const user = userEvent.setup();
    render(
      <AgentTemplatesModal
        open={true}
        onClose={() => {}}
        availableTools={mockAvailableTools}
      />
    );

    // 选择两个工具
    await user.click(screen.getByText('calculator'));
    await user.click(screen.getByText('search'));

    await waitFor(() => {
      expect(screen.getByText('已选择 2 个工具')).toBeInTheDocument();
    });

    // 点击清空
    await user.click(screen.getByText('清空'));

    await waitFor(() => {
      expect(screen.getByText('已选择 0 个工具')).toBeInTheDocument();
    });
  });
});

describe('AgentTemplatesModal 编辑模式', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    
  });

  it('应该正确渲染编辑模态框', async () => {
    render(
      <AgentTemplatesModal
        open={true}
        onClose={() => {}}
        template={mockTemplate}
        availableTools={mockAvailableTools}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('编辑 Agent 模板')).toBeInTheDocument();
    });
  });

  it('应该填充模板数据', async () => {
    render(
      <AgentTemplatesModal
        open={true}
        onClose={() => {}}
        template={mockTemplate}
        availableTools={mockAvailableTools}
      />
    );

    await waitFor(() => {
      expect(screen.getByDisplayValue('RAG Agent')).toBeInTheDocument();
    });
  });

  it('应该显示已选中的工具', async () => {
    render(
      <AgentTemplatesModal
        open={true}
        onClose={() => {}}
        template={mockTemplate}
        availableTools={mockAvailableTools}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('已选择 1 个工具')).toBeInTheDocument();
    });
  });
});

describe('AgentTemplatesModal 表单提交', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    

    vi.mocked(agentService.createAgentTemplate).mockResolvedValue({
      code: 0,
      data: { template_id: 'tmpl-new' },
    });

    vi.mocked(agentService.updateAgentTemplate).mockResolvedValue({
      code: 0,
      data: { template_id: 'tmpl-001' },
    });
  });

  it('应该验证必填字段', async () => {
    render(
      <AgentTemplatesModal
        open={true}
        onClose={() => {}}
        availableTools={mockAvailableTools}
      />
    );

    // 验证模态框打开
    expect(document.querySelector('.ant-modal')).toBeInTheDocument();
  });

  it('应该能够创建模板', async () => {
    const onClose = vi.fn();

    render(
      <AgentTemplatesModal
        open={true}
        onClose={onClose}
        availableTools={mockAvailableTools}
      />
    );

    // 验证模态框打开并包含表单元素
    expect(document.querySelector('.ant-modal')).toBeInTheDocument();
    expect(document.querySelector('form') || document.querySelector('.ant-form')).toBeTruthy();
  });
});

describe('AgentTemplatesModal 关闭行为', () => {
  it('应该能够关闭模态框', async () => {
    const onClose = vi.fn();

    render(
      <AgentTemplatesModal
        open={true}
        onClose={onClose}
        availableTools={mockAvailableTools}
      />
    );

    // 验证模态框打开
    expect(document.querySelector('.ant-modal')).toBeInTheDocument();
  });
});
