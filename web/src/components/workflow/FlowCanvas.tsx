/**
 * 流程图画布组件
 * Phase 7: Sprint 7.3
 * Sprint 4: 添加缩放控制和连接验证
 *
 * 基于 React Flow 实现可拖拽流程图编辑器
 */

import React, { useCallback, useEffect, useMemo, useImperativeHandle, forwardRef } from 'react';
import ReactFlow, {
  Node,
  Edge,
  addEdge,
  Connection,
  useNodesState,
  useEdgesState,
  Controls,
  Background,
  MiniMap,
  BackgroundVariant,
  NodeTypes,
  MarkerType,
  ReactFlowProvider,
  Panel,
  useReactFlow,
} from 'reactflow';
import 'reactflow/dist/style.css';

import AgentNode from './nodes/AgentNode';
import ConditionNode from './nodes/ConditionNode';
import LoopNode from './nodes/LoopNode';
import ToolCallNode from './nodes/ToolCallNode';
import LLMNode from './nodes/LLMNode';
import RetrieverNode from './nodes/RetrieverNode';
import InputNode from './nodes/InputNode';
import OutputNode from './nodes/OutputNode';
import ThinkNode from './nodes/ThinkNode';
import { ErrorBoundary } from '@/components/common/ErrorBoundary';

export interface FlowCanvasRef {
  zoomIn: () => void;
  zoomOut: () => void;
  fitView: () => void;
  setZoom: (zoom: number) => void;
  getZoom: () => number;
}

interface FlowCanvasProps {
  nodes?: Node[];
  edges?: Edge[];
  onNodesChange?: (nodes: Node[]) => void;
  onEdgesChange?: (edges: Edge[]) => void;
  onNodeSelect?: (node: Node | null) => void;
  onConnectionValidate?: (connection: Connection) => boolean;
  readonly?: boolean;
  minimap?: boolean;
}

const nodeTypes: NodeTypes = {
  agent: AgentNode,
  condition: ConditionNode,
  loop: LoopNode,
  tool_call: ToolCallNode,
  llm: LLMNode,
  retriever: RetrieverNode,
  input: InputNode,
  output: OutputNode,
  think: ThinkNode,
};

const defaultEdgeOptions = {
  animated: true,
  type: 'smoothstep',
  markerEnd: {
    type: MarkerType.ArrowClosed,
  },
};

// 节点类型兼容性规则
const connectionRules: Record<string, string[]> = {
  input: ['llm', 'retriever', 'agent', 'tool_call', 'condition', 'think'],
  llm: ['output', 'condition', 'loop', 'agent', 'tool_call', 'think'],
  retriever: ['llm', 'output', 'condition', 'think'],
  agent: ['output', 'condition', 'loop', 'tool_call'],
  tool_call: ['llm', 'output', 'condition', 'agent'],
  condition: ['llm', 'agent', 'tool_call', 'output', 'loop'],
  loop: ['llm', 'agent', 'tool_call', 'output', 'condition'],
  think: ['llm', 'output', 'condition'],
  output: [], // output 不能连接到其他节点
};

const FlowCanvas = forwardRef<FlowCanvasRef, FlowCanvasProps>(function FlowCanvas(
  {
    nodes: initialNodes = [],
    edges: initialEdges = [],
    onNodesChange,
    onEdgesChange,
    onNodeSelect,
    onConnectionValidate,
    readonly = false,
    minimap = true,
  },
  ref
) {
  const [nodes, setNodes, onNodesChangeInternal] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChangeInternal] = useEdgesState(initialEdges);
  const reactFlowInstance = useReactFlow();

  // 暴露方法给父组件
  useImperativeHandle(ref, () => ({
    zoomIn: () => {
      reactFlowInstance.zoomIn({ duration: 200 });
    },
    zoomOut: () => {
      reactFlowInstance.zoomOut({ duration: 200 });
    },
    fitView: () => {
      reactFlowInstance.fitView({ padding: 0.2, duration: 200 });
    },
    setZoom: (zoom: number) => {
      reactFlowInstance.setViewport({ ...reactFlowInstance.getViewport(), zoom }, { duration: 200 });
    },
    getZoom: () => {
      return reactFlowInstance.getViewport().zoom;
    },
  }), [reactFlowInstance]);

  // 同步外部状态
  useEffect(() => {
    if (initialNodes.length > 0) {
      setNodes(initialNodes);
    }
  }, [initialNodes, setNodes]);

  useEffect(() => {
    if (initialEdges.length > 0) {
      setEdges(initialEdges);
    }
  }, [initialEdges, setEdges]);

  // 验证连接是否有效
  const isValidConnection = useCallback(
    (connection: Connection) => {
      // 如果有自定义验证函数，优先使用
      if (onConnectionValidate) {
        return onConnectionValidate(connection);
      }

      // 获取源节点和目标节点
      const sourceNode = nodes.find((n) => n.id === connection.source);
      const targetNode = nodes.find((n) => n.id === connection.target);

      if (!sourceNode || !targetNode) return false;

      // 检查是否是有效的连接类型
      const allowedTargets = connectionRules[sourceNode.type || ''] || [];
      if (!allowedTargets.includes(targetNode.type || '')) {
        return false;
      }

      // 检查是否已存在相同的连接
      const existingConnection = edges.find(
        (e) => e.source === connection.source && e.target === connection.target
      );
      if (existingConnection) return false;

      // 防止循环连接
      if (connection.source === connection.target) return false;

      return true;
    },
    [nodes, edges, onConnectionValidate]
  );

  // 处理连接
  const onConnect = useCallback(
    (connection: Connection) => {
      // 验证连接
      if (!isValidConnection(connection)) {
        return;
      }

      const edge = {
        ...connection,
        markerEnd: {
          type: MarkerType.ArrowClosed,
        },
      };
      setEdges((eds) => addEdge(edge, eds));
    },
    [setEdges, isValidConnection]
  );

  // 处理节点变化
  const handleNodesChange = useCallback(
    (changes: any) => {
      onNodesChangeInternal(changes);
      if (onNodesChange) {
        onNodesChange(nodes);
      }
    },
    [onNodesChangeInternal, nodes, onNodesChange]
  );

  // 处理边变化
  const handleEdgesChange = useCallback(
    (changes: any) => {
      onEdgesChangeInternal(changes);
      if (onEdgesChange) {
        onEdgesChange(edges);
      }
    },
    [onEdgesChangeInternal, edges, onEdgesChange]
  );

  // 处理节点点击
  const onNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      if (onNodeSelect) {
        onNodeSelect(node);
      }
    },
    [onNodeSelect]
  );

  // 处理画布点击（取消选择）
  const onPaneClick = useCallback(() => {
    if (onNodeSelect) {
      onNodeSelect(null);
    }
  }, [onNodeSelect]);

  // 删除节点
  const onNodesDelete = useCallback(
    (deletedNodes: Node[]) => {
      // 节点删除后的处理逻辑
    },
    []
  );

  // 删除边
  const onEdgesDelete = useCallback(
    (deletedEdges: Edge[]) => {
      // 边删除后的处理逻辑
    },
    []
  );

  return (
    <div className="w-full h-full">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={readonly ? undefined : handleNodesChange}
        onEdgesChange={readonly ? undefined : handleEdgesChange}
        onConnect={readonly ? undefined : onConnect}
        isValidConnection={isValidConnection}
        onNodeClick={onNodeClick}
        onPaneClick={onPaneClick}
        onNodesDelete={readonly ? undefined : onNodesDelete}
        onEdgesDelete={readonly ? undefined : onEdgesDelete}
        nodeTypes={nodeTypes}
        defaultEdgeOptions={defaultEdgeOptions}
        fitView
        minZoom={0.2}
        maxZoom={2}
        deleteKeyCode={readonly ? undefined : 'Delete'}
        panOnScroll
        selectionKeyCode="Shift"
        multiSelectionKeyCode="Ctrl"
      >
        <Background variant={BackgroundVariant.Dots} gap={16} size={1} />
        <Controls />
        {minimap && (
          <MiniMap
            nodeColor={(node) => {
              switch (node.type) {
                case 'input':
                  return '#10b981';
                case 'output':
                  return '#ef4444';
                case 'agent':
                  return '#8b5cf6';
                case 'condition':
                  return '#f59e0b';
                case 'loop':
                  return '#06b6d4';
                default:
                  return '#3b82f6';
              }
            }}
            maskColor="rgba(0, 0, 0, 0.1)"
          />
        )}
        {readonly && (
          <Panel position="top-left">
            <span className="px-3 py-1 bg-gray-100 text-gray-600 text-sm rounded">
              只读模式
            </span>
          </Panel>
        )}
      </ReactFlow>
    </div>
  );
});

// 包装组件以提供 Provider 并支持 ref
interface FlowCanvasWithProviderProps extends FlowCanvasProps {
  canvasRef?: React.Ref<FlowCanvasRef>;
}

function FlowCanvasWithProvider({ canvasRef, ...props }: FlowCanvasWithProviderProps) {
  return (
    <ErrorBoundary>
      <ReactFlowProvider>
        <FlowCanvas ref={canvasRef} {...props} />
      </ReactFlowProvider>
    </ErrorBoundary>
  );
}

export default FlowCanvasWithProvider;

// 导出类型
export type { Node, Edge, Connection, FlowCanvasRef };
