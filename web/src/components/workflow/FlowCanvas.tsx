/**
 * 流程图画布组件
 * Phase 7: Sprint 7.3
 *
 * 基于 React Flow 实现可拖拽流程图编辑器
 */

import React, { useCallback, useEffect, useMemo } from 'react';
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

interface FlowCanvasProps {
  nodes?: Node[];
  edges?: Edge[];
  onNodesChange?: (nodes: Node[]) => void;
  onEdgesChange?: (edges: Edge[]) => void;
  onNodeSelect?: (node: Node | null) => void;
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

function FlowCanvas({
  nodes: initialNodes = [],
  edges: initialEdges = [],
  onNodesChange,
  onEdgesChange,
  onNodeSelect,
  readonly = false,
  minimap = true,
}: FlowCanvasProps) {
  const [nodes, setNodes, onNodesChangeInternal] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChangeInternal] = useEdgesState(initialEdges);

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

  // 处理连接
  const onConnect = useCallback(
    (connection: Connection) => {
      const edge = {
        ...connection,
        markerEnd: {
          type: MarkerType.ArrowClosed,
        },
      };
      setEdges((eds) => addEdge(edge, eds));
    },
    [setEdges]
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
      console.log('Deleted nodes:', deletedNodes);
    },
    []
  );

  // 删除边
  const onEdgesDelete = useCallback(
    (deletedEdges: Edge[]) => {
      console.log('Deleted edges:', deletedEdges);
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
}

// 包装组件以提供 Provider
export default function FlowCanvasWithProvider(props: FlowCanvasProps) {
  return (
    <ReactFlowProvider>
      <FlowCanvas {...props} />
    </ReactFlowProvider>
  );
}

// 导出类型
export type { Node, Edge, Connection };
