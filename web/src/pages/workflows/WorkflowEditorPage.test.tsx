import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@/test/testUtils';
import userEvent from '@testing-library/user-event';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import WorkflowEditorPage from './WorkflowEditorPage';
import * as agentService from '../../services/agent-service';

// Mock 服务
vi.mock('../../services/agent-service', () => ({
  getWorkflow: vi.fn(),
  createWorkflow: vi.fn(),
  updateWorkflow: vi.fn(),
  startWorkflow: vi.fn(),
}));

// Mock react-router-dom
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => vi.fn(),
    useParams: () => ({ workflowId: 'new' }),
  };
});

// Mock workflow 组件
vi.mock('../../components/workflow/FlowCanvas', () => ({
  default: ({ nodes, edges, onNodesChange, onEdgesChange, onNodeSelect }: any) => (
    <div data-testid="flow-canvas">
      <span>节点数: {nodes?.length || 0}</span>
      <span>边数: {edges?.length || 0}</span>
    </div>
  ),
}));

vi.mock('../../components/workflow/NodePalette', () => ({
  default: ({ onNodeAdd }: any) => (
    <div data-testid="node-palette">
      <button onClick={() => onNodeAdd('llm', {})}>添加 LLM 节点</button>
    </div>
  ),
  nodeTypes: [
    { type: 'input', label: '输入' },
    { type: 'output', label: '输出' },
    { type: 'llm', label: 'LLM' },
  ],
}));

vi.mock('../../components/workflow/NodeConfigPanel', () => ({
  default: ({ node, onNodeUpdate, onClose }: any) => (
    <div data-testid="node-config-panel">
      {node ? <span>配置节点: {node.id}</span> : <span>无选中节点</span>}
    </div>
  ),
}));

vi.mock('@/components/common/ErrorBoundary', () => ({
  ErrorBoundary: ({ children }: any) => <>{children}</>,
}));



describe('WorkflowEditorPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    
  });

  it('应该正确渲染工作流编辑器', async () => {
    render(<WorkflowEditorPage />);

    await waitFor(() => {
      expect(screen.getByTestId('flow-canvas')).toBeInTheDocument();
    });
  });

  it('应该显示工具栏按钮', async () => {
    render(<WorkflowEditorPage />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /撤销/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /重做/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /保存/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /运行/i })).toBeInTheDocument();
    });
  });

  it('应该显示默认节点', async () => {
    render(<WorkflowEditorPage />);

    await waitFor(() => {
      expect(screen.getByText(/节点数: 2/)).toBeInTheDocument();
    });
  });

  it('应该显示节点面板', async () => {
    render(<WorkflowEditorPage />);

    await waitFor(() => {
      expect(screen.getByTestId('node-palette')).toBeInTheDocument();
    });
  });

  it('应该显示配置面板', async () => {
    render(<WorkflowEditorPage />);

    await waitFor(() => {
      expect(screen.getByTestId('node-config-panel')).toBeInTheDocument();
    });
  });

  it('应该显示视图菜单按钮', async () => {
    render(<WorkflowEditorPage />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /视图/i })).toBeInTheDocument();
    });
  });

  it('应该显示验证按钮', async () => {
    render(<WorkflowEditorPage />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /验证/i })).toBeInTheDocument();
    });
  });

  it('应该显示导入导出按钮', async () => {
    render(<WorkflowEditorPage />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /导出/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /导入/i })).toBeInTheDocument();
    });
  });

  it('应该显示清空按钮', async () => {
    render(<WorkflowEditorPage />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /清空/i })).toBeInTheDocument();
    });
  });

  it('撤销按钮初始应该禁用', async () => {
    render(<WorkflowEditorPage />);

    await waitFor(() => {
      const undoButton = screen.getByRole('button', { name: /撤销/i });
      expect(undoButton).toBeDisabled();
    });
  });

  it('重做按钮初始应该禁用', async () => {
    render(<WorkflowEditorPage />);

    await waitFor(() => {
      const redoButton = screen.getByRole('button', { name: /重做/i });
      expect(redoButton).toBeDisabled();
    });
  });
});

describe('WorkflowEditorPage 新建模式', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    
  });

  it('运行按钮应该禁用（新建模式）', async () => {
    render(<WorkflowEditorPage />);

    await waitFor(() => {
      const runButton = screen.getByRole('button', { name: /运行/i });
      expect(runButton).toBeDisabled();
    });
  });

  it('应该显示未命名工作流', async () => {
    render(<WorkflowEditorPage />);

    await waitFor(() => {
      expect(screen.getByText(/未命名工作流/)).toBeInTheDocument();
    });
  });
});

describe('WorkflowEditorPage 节点操作', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    
  });

  it('应该能够添加节点', async () => {
    const user = userEvent.setup();
    render(<WorkflowEditorPage />);

    await waitFor(() => {
      expect(screen.getByText('添加 LLM 节点')).toBeInTheDocument();
    });

    await user.click(screen.getByText('添加 LLM 节点'));

    await waitFor(() => {
      expect(screen.getByText(/节点数: 3/)).toBeInTheDocument();
    });
  });

  it('应该能够切换配置面板显示', async () => {
    const user = userEvent.setup();
    render(<WorkflowEditorPage />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /隐藏配置/i })).toBeInTheDocument();
    });

    await user.click(screen.getByRole('button', { name: /隐藏配置/i }));

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /显示配置/i })).toBeInTheDocument();
    });
  });
});

describe('WorkflowEditorPage 保存功能', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    

    vi.mocked(agentService.createWorkflow).mockResolvedValue({
      code: 0,
      data: { workflow_id: 'wf-new' },
    });
  });

  it('应该能够保存工作流', async () => {
    const user = userEvent.setup();
    render(<WorkflowEditorPage />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /保存/i })).toBeInTheDocument();
    });

    await user.click(screen.getByRole('button', { name: /保存/i }));

    await waitFor(() => {
      expect(agentService.createWorkflow).toHaveBeenCalled();
    });
  });
});
