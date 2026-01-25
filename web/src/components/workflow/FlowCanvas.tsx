/**
 * 流程图画布组件
 * Phase 7: Sprint 7.3
 * Sprint 4: 添加缩放控制和连接验证
 *
 * 基于 React Flow 实现可拖拽流程图编辑器
 */

import React, { useCallback, useEffect, useImperativeHandle, forwardRef } from 'react';
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
  NodeChange,
  EdgeChange,
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
  onNodeAdd?: (nodeType: string, config: Record<string, unknown>) => void;
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
    onNodeAdd,
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

  // 处理拖拽放置
  const onDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();

      if (readonly) return;

      const dataStr = event.dataTransfer.getData('application/reactflow');
      if (!dataStr) return;

      try {
        const { type, config } = JSON.parse(dataStr);

        // 计算放置位置
        const position = reactFlowInstance.screenToFlowPosition({
          x: event.clientX,
          y: event.clientY,
        });

        // 如果有外部添加回调，使用它
        if (onNodeAdd) {
          onNodeAdd(type, config);
          return;
        }

        // 否则直接添加节点
        const nodeLabels: Record<string, string> = {
          input: '输入',
          output: '输出',
          retriever: '检索',
          llm: '大模型',
          agent: 'Agent',
          tool_call: '工具',
          think: '思考',
          condition: '条件',
          loop: '循环',
          human_task: '人工审批',
        };

        const newNode: Node = {
          id: `${type}-${Date.now()}`,
          type,
          position,
          data: {
            label: nodeLabels[type] || type,
            config: config || {},
          },
        };

        setNodes((nds) => {
          const updated = [...nds, newNode];
          if (onNodesChange) {
            onNodesChange(updated);
          }
          return updated;
        });
      } catch (e) {
        // Ignore invalid drop data
      }
    },
    [reactFlowInstance, readonly, onNodeAdd, onNodesChange, setNodes]
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
      setEdges((eds) => {
        const updated = addEdge(edge, eds);
        if (onEdgesChange) {
          onEdgesChange(updated);
        }
        return updated;
      });
    },
    [setEdges, isValidConnection, onEdgesChange]
  );

  // 处理节点变化
  const handleNodesChange = useCallback(
    (changes: NodeChange[]) => {
      onNodesChangeInternal(changes);
      // 使用 setNodes 获取最新状态并通知父组件
      setNodes((currentNodes) => {
        if (onNodesChange) {
          // 使用 setTimeout 确保状态已更新
          setTimeout(() => onNodesChange(currentNodes), 0);
        }
        return currentNodes;
      });
    },
    [onNodesChangeInternal, onNodesChange, setNodes]
  );

  // 处理边变化
  const handleEdgesChange = useCallback(
    (changes: EdgeChange[]) => {
      onEdgesChangeInternal(changes);
      // 使用 setEdges 获取最新状态并通知父组件
      setEdges((currentEdges) => {
        if (onEdgesChange) {
          // 使用 setTimeout 确保状态已更新
          setTimeout(() => onEdgesChange(currentEdges), 0);
        }
        return currentEdges;
      });
    },
    [onEdgesChangeInternal, onEdgesChange, setEdges]
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
    (_deletedNodes: Node[]) => {
      // 节点删除后的处理逻辑
    },
    []
  );

  // 删除边
  const onEdgesDelete = useCallback(
    (_deletedEdges: Edge[]) => {
      // 边删除后的处理逻辑
    },
    []
  );

  return (
    <div className="w-full h-full" onDragOver={onDragOver} onDrop={onDrop}>
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

// Re-export types from reactflow for convenience
export type { Node, Edge, Connection } from 'reactflow';

// Export component types
export type { FlowCanvasProps };
