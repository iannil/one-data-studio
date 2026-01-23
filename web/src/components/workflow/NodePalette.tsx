/**
 * 节点面板组件
 * Phase 7: Sprint 7.3
 *
 * 可拖拽的节点面板
 */

import React, { useCallback } from 'react';
import { useReactFlow } from 'reactflow';
import {
  InputOutlined,
  OutputOutlined,
  SearchOutlined,
  RobotOutlined,
  ApiOutlined,
  ToolOutlined,
  BulbOutlined,
  BranchesOutlined,
  SyncOutlined,
} from '@ant-design/icons';

interface NodeType {
  type: string;
  label: string;
  icon: React.ReactNode;
  color: string;
  description: string;
  config: Record<string, any>;
}

const nodeTypes: NodeType[] = [
  {
    type: 'input',
    label: '输入',
    icon: <InputOutlined />,
    color: 'emerald',
    description: '接收外部输入',
    config: { key: 'input' },
  },
  {
    type: 'output',
    label: '输出',
    icon: <OutputOutlined />,
    color: 'red',
    description: '返回最终结果',
    config: { output_key: 'result' },
  },
  {
    type: 'retriever',
    label: '检索',
    icon: <SearchOutlined />,
    color: 'teal',
    description: '向量数据库检索',
    config: { collection: 'default', top_k: 5 },
  },
  {
    type: 'llm',
    label: '大模型',
    icon: <RobotOutlined />,
    color: 'blue',
    description: '调用 LLM 生成文本',
    config: { model: 'gpt-4o-mini', temperature: 0.7 },
  },
  {
    type: 'agent',
    label: 'Agent',
    icon: <ApiOutlined />,
    color: 'purple',
    description: 'ReAct Agent 编排',
    config: { agent_type: 'react', max_iterations: 10 },
  },
  {
    type: 'tool_call',
    label: '工具',
    icon: <ToolOutlined />,
    color: 'indigo',
    description: '单次工具调用',
    config: { tool_name: 'calculator' },
  },
  {
    type: 'think',
    label: '思考',
    icon: <BulbOutlined />,
    color: 'yellow',
    description: 'LLM 推理',
    config: { model: 'gpt-4o-mini' },
  },
  {
    type: 'condition',
    label: '条件',
    icon: <BranchesOutlined />,
    color: 'amber',
    description: '条件分支',
    config: { condition: '', true_branch: [], false_branch: [] },
  },
  {
    type: 'loop',
    label: '循环',
    icon: <SyncOutlined />,
    color: 'cyan',
    description: '循环迭代',
    config: { loop_over: 3, max_iterations: 10 },
  },
];

interface NodePaletteProps {
  onNodeAdd?: (nodeType: string, config: Record<string, any>) => void;
}

export default function NodePalette({ onNodeAdd }: NodePaletteProps) {
  const reactFlowInstance = useReactFlow();

  // 拖拽开始
  const onDragStart = useCallback(
    (event: React.DragEvent, nodeType: string, config: Record<string, any>) => {
      event.dataTransfer.effectAllowed = 'move';
      event.dataTransfer.setData('application/reactflow', JSON.stringify({ type: nodeType, config }));
    },
    []
  );

  // 点击添加节点
  const handleAddNode = useCallback(
    (nodeType: string, config: Record<string, any>) => {
      if (onNodeAdd) {
        onNodeAdd(nodeType, config);
        return;
      }

      // 默认行为：在画布中心添加节点
      const { viewport, project } = reactFlowInstance;
      const centerX = (viewport.width || 800) / 2 - viewport.x;
      const centerY = (viewport.height || 600) / 2 - viewport.y;

      const newNode = {
        id: `${nodeType}-${Date.now()}`,
        type: nodeType,
        position: project({ x: centerX, y: centerY }),
        data: {
          label: nodeTypes.find((t) => t.type === nodeType)?.label || nodeType,
          config,
        },
      };

      reactFlowInstance.addNodes([newNode]);
    },
    [reactFlowInstance, onNodeAdd]
  );

  return (
    <div className="w-56 bg-gray-50 border-l border-gray-200 overflow-y-auto">
      <div className="p-4 border-b border-gray-200">
        <h3 className="font-semibold text-gray-700">节点面板</h3>
        <p className="text-xs text-gray-500 mt-1">拖拽节点到画布</p>
      </div>

      <div className="p-3 space-y-2">
        {nodeTypes.map((nodeType) => (
          <div
            key={nodeType.type}
            draggable
            onDragStart={(e) => onDragStart(e, nodeType.type, nodeType.config)}
            onClick={() => handleAddNode(nodeType.type, nodeType.config)}
            className={`
              flex items-center gap-3 p-3 rounded-lg border-2 border-transparent
              bg-white hover:border-${nodeType.color}-300 hover:shadow-md
              cursor-grab active:cursor-grabbing transition-all
            `}
            style={{ '--tw-border-opacity': 1 } as React.CSSProperties}
          >
            <div
              className={`w-10 h-10 rounded-full bg-${nodeType.color}-100 flex items-center justify-center flex-shrink-0`}
            >
              <div className={`text-${nodeType.color}-600`}>{nodeType.icon}</div>
            </div>
            <div className="flex-1 min-w-0">
              <div className="font-medium text-sm text-gray-800">{nodeType.label}</div>
              <div className="text-xs text-gray-500 truncate">{nodeType.description}</div>
            </div>
          </div>
        ))}
      </div>

      {/* 节点类型说明 */}
      <div className="p-4 border-t border-gray-200">
        <h4 className="text-xs font-semibold text-gray-600 mb-2">节点类型</h4>
        <div className="space-y-1 text-xs text-gray-500">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-emerald-500"></div>
            <span>输入/输出</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-blue-500"></div>
            <span>LLM/检索</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-purple-500"></div>
            <span>Agent/工具</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-amber-500"></div>
            <span>控制流</span>
          </div>
        </div>
      </div>
    </div>
  );
}

// 导出节点类型配置供其他组件使用
export { nodeTypes };
