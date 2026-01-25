/**
 * NodePalette 组件单元测试
 * Sprint 9: 前端组件测试
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@/test/testUtils';
import '@testing-library/jest-dom';

// Mock reactflow
const mockAddNodes = vi.fn();
vi.mock('reactflow', () => ({
  useReactFlow: () => ({
    fitView: vi.fn(),
    zoomIn: vi.fn(),
    zoomOut: vi.fn(),
    addNodes: mockAddNodes,
    getNodes: vi.fn(() => []),
    getEdges: vi.fn(() => []),
    setNodes: vi.fn(),
    setEdges: vi.fn(),
    deleteElements: vi.fn(),
    getViewport: vi.fn(() => ({ x: 0, y: 0, zoom: 1 })),
    setViewport: vi.fn(),
    project: vi.fn((pos: any) => pos),
    screenToFlowPosition: vi.fn((pos: any) => pos),
  }),
  ReactFlowProvider: ({ children }: { children: React.ReactNode }) => children,
}));

import NodePalette, { nodeTypes } from './NodePalette';

describe('NodePalette Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should render node palette', () => {
    render(<NodePalette />);

    expect(screen.getByText('节点面板')).toBeInTheDocument();
    expect(screen.getByText('拖拽节点到画布')).toBeInTheDocument();
  });

  it('should render all node types', () => {
    render(<NodePalette />);

    expect(screen.getByText('输入')).toBeInTheDocument();
    expect(screen.getByText('输出')).toBeInTheDocument();
    expect(screen.getByText('检索')).toBeInTheDocument();
    expect(screen.getByText('大模型')).toBeInTheDocument();
    expect(screen.getByText('Agent')).toBeInTheDocument();
    expect(screen.getByText('工具')).toBeInTheDocument();
    expect(screen.getByText('思考')).toBeInTheDocument();
    expect(screen.getByText('条件')).toBeInTheDocument();
    expect(screen.getByText('循环')).toBeInTheDocument();
  });

  it('should render node descriptions', () => {
    render(<NodePalette />);

    expect(screen.getByText('接收外部输入')).toBeInTheDocument();
    expect(screen.getByText('返回最终结果')).toBeInTheDocument();
    expect(screen.getByText('向量数据库检索')).toBeInTheDocument();
    expect(screen.getByText('调用 LLM 生成文本')).toBeInTheDocument();
    expect(screen.getByText('ReAct Agent 编排')).toBeInTheDocument();
    expect(screen.getByText('单次工具调用')).toBeInTheDocument();
    expect(screen.getByText('LLM 推理')).toBeInTheDocument();
    expect(screen.getByText('条件分支')).toBeInTheDocument();
    expect(screen.getByText('循环迭代')).toBeInTheDocument();
  });

  it('should render node type legend', () => {
    render(<NodePalette />);

    expect(screen.getByText('节点类型')).toBeInTheDocument();
    expect(screen.getByText('输入/输出')).toBeInTheDocument();
    expect(screen.getByText('LLM/检索')).toBeInTheDocument();
    expect(screen.getByText('Agent/工具')).toBeInTheDocument();
    expect(screen.getByText('控制流')).toBeInTheDocument();
  });

  it('should add node when clicked', () => {
    render(<NodePalette />);

    const inputNode = screen.getByText('接收外部输入').closest('div[draggable]');
    if (inputNode) {
      fireEvent.click(inputNode);
    }

    expect(mockAddNodes).toHaveBeenCalled();
  });

  it('should call onNodeAdd callback when provided', () => {
    const onNodeAdd = vi.fn();
    render(<NodePalette onNodeAdd={onNodeAdd} />);

    const inputNode = screen.getByText('接收外部输入').closest('div[draggable]');
    if (inputNode) {
      fireEvent.click(inputNode);
    }

    expect(onNodeAdd).toHaveBeenCalledWith('input', { key: 'input' });
  });

  it('should set drag data on drag start', () => {
    render(<NodePalette />);

    const inputNode = screen.getByText('接收外部输入').closest('div[draggable]');

    if (inputNode) {
      const mockDataTransfer = {
        effectAllowed: '',
        setData: vi.fn(),
      };

      fireEvent.dragStart(inputNode, {
        dataTransfer: mockDataTransfer,
      });

      expect(mockDataTransfer.effectAllowed).toBe('move');
      expect(mockDataTransfer.setData).toHaveBeenCalledWith(
        'application/reactflow',
        expect.any(String)
      );
    }
  });

  it('should have draggable attribute on node items', () => {
    render(<NodePalette />);

    const inputNode = screen.getByText('接收外部输入').closest('div[draggable]');
    expect(inputNode).toHaveAttribute('draggable', 'true');
  });
});

describe('nodeTypes export', () => {
  it('should export 10 node types', () => {
    expect(nodeTypes).toHaveLength(10);
  });

  it('should have correct structure for each node type', () => {
    nodeTypes.forEach((nodeType) => {
      expect(nodeType).toHaveProperty('type');
      expect(nodeType).toHaveProperty('label');
      expect(nodeType).toHaveProperty('icon');
      expect(nodeType).toHaveProperty('color');
      expect(nodeType).toHaveProperty('description');
      expect(nodeType).toHaveProperty('config');
    });
  });

  it('should include input node type', () => {
    const inputType = nodeTypes.find((t) => t.type === 'input');
    expect(inputType).toBeDefined();
    expect(inputType?.label).toBe('输入');
    expect(inputType?.config).toEqual({ key: 'input' });
  });

  it('should include output node type', () => {
    const outputType = nodeTypes.find((t) => t.type === 'output');
    expect(outputType).toBeDefined();
    expect(outputType?.label).toBe('输出');
    expect(outputType?.config).toEqual({ output_key: 'result' });
  });

  it('should include llm node type', () => {
    const llmType = nodeTypes.find((t) => t.type === 'llm');
    expect(llmType).toBeDefined();
    expect(llmType?.label).toBe('大模型');
    expect(llmType?.config).toEqual({ model: 'gpt-4o-mini', temperature: 0.7 });
  });

  it('should include agent node type', () => {
    const agentType = nodeTypes.find((t) => t.type === 'agent');
    expect(agentType).toBeDefined();
    expect(agentType?.label).toBe('Agent');
    expect(agentType?.config).toEqual({ agent_type: 'react', max_iterations: 10 });
  });

  it('should include condition node type', () => {
    const conditionType = nodeTypes.find((t) => t.type === 'condition');
    expect(conditionType).toBeDefined();
    expect(conditionType?.label).toBe('条件');
  });

  it('should include loop node type', () => {
    const loopType = nodeTypes.find((t) => t.type === 'loop');
    expect(loopType).toBeDefined();
    expect(loopType?.label).toBe('循环');
    expect(loopType?.config).toEqual({ loop_over: 3, max_iterations: 10 });
  });
});
