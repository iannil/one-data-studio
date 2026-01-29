/**
 * 工作流编辑页面
 * Phase 7: Sprint 7.3
 * Sprint 4: 添加撤销/重做和缩放功能
 *
 * 可视化工作流编辑器，支持：
 * - 拖拽创建节点
 * - 连接节点
 * - 配置节点属性
 * - 保存和运行工作流
 * - 撤销/重做操作
 * - 视图缩放
 * - 连接验证
 */

import React, { useCallback, useEffect, useState, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Button,
  message,
  Modal,
  Space,
  Dropdown,
  Tooltip,
  Badge,
} from 'antd';
import {
  SaveOutlined,
  PlayCircleOutlined,
  UndoOutlined,
  RedoOutlined,
  ZoomInOutlined,
  ZoomOutOutlined,
  ExpandOutlined,
  DownloadOutlined,
  UploadOutlined,
  ClearOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons';
import { logError } from '@/services/logger';
import type { MenuProps } from 'antd';

import FlowCanvas, { Node, Edge, FlowCanvasRef } from '../../components/workflow/FlowCanvas';
import NodePalette, { nodeTypes } from '../../components/workflow/NodePalette';
import NodeConfigPanel from '../../components/workflow/NodeConfigPanel';
import * as agentService from '../../services/agent-service';
import { ErrorBoundary } from '@/components/common/ErrorBoundary';

interface WorkflowDefinition {
  version?: string;
  nodes: unknown[];
  edges: unknown[];
}

// 历史记录项
interface HistoryItem {
  nodes: Node[];
  edges: Edge[];
}

// 最大历史记录数量
const MAX_HISTORY_SIZE = 50;

function WorkflowEditorPage() {
  const { workflowId } = useParams();
  const navigate = useNavigate();
  const flowCanvasRef = useRef<FlowCanvasRef>(null);

  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);
  const [workflowName, setWorkflowName] = useState('');
  const [workflowDescription, setWorkflowDescription] = useState('');
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [hasChanges, setHasChanges] = useState(false);
  const [showConfig, setShowConfig] = useState(true);

  // 历史记录状态（撤销/重做）
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [historyIndex, setHistoryIndex] = useState(-1);
  const isHistoryAction = useRef(false);

  // 初始化历史记录
  const initHistory = useCallback((initialNodes: Node[], initialEdges: Edge[]) => {
    setHistory([{ nodes: initialNodes, edges: initialEdges }]);
    setHistoryIndex(0);
  }, []);

  // 添加历史记录
  const pushHistory = useCallback((newNodes: Node[], newEdges: Edge[]) => {
    if (isHistoryAction.current) {
      isHistoryAction.current = false;
      return;
    }

    setHistory((prev) => {
      // 如果当前不是最新状态，裁剪后续历史
      const newHistory = prev.slice(0, historyIndex + 1);
      newHistory.push({ nodes: newNodes, edges: newEdges });

      // 限制历史记录大小
      if (newHistory.length > MAX_HISTORY_SIZE) {
        newHistory.shift();
      }

      return newHistory;
    });
    setHistoryIndex((prev) => Math.min(prev + 1, MAX_HISTORY_SIZE - 1));
  }, [historyIndex]);

  // 撤销操作
  const handleUndo = useCallback(() => {
    if (historyIndex <= 0) return;

    isHistoryAction.current = true;
    const prevIndex = historyIndex - 1;
    const prevState = history[prevIndex];

    setNodes(prevState.nodes);
    setEdges(prevState.edges);
    setHistoryIndex(prevIndex);
    setHasChanges(true);
  }, [history, historyIndex]);

  // 重做操作
  const handleRedo = useCallback(() => {
    if (historyIndex >= history.length - 1) return;

    isHistoryAction.current = true;
    const nextIndex = historyIndex + 1;
    const nextState = history[nextIndex];

    setNodes(nextState.nodes);
    setEdges(nextState.edges);
    setHistoryIndex(nextIndex);
    setHasChanges(true);
  }, [history, historyIndex]);

  // 键盘快捷键支持
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'z') {
        if (e.shiftKey) {
          handleRedo();
        } else {
          handleUndo();
        }
        e.preventDefault();
      }
      if ((e.ctrlKey || e.metaKey) && e.key === 'y') {
        handleRedo();
        e.preventDefault();
      }
      if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        handleSave();
        e.preventDefault();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleUndo, handleRedo]);

  // 加载工作流定义
  useEffect(() => {
    if (workflowId && workflowId !== 'new') {
      loadWorkflow(workflowId);
    } else {
      // 新建工作流，添加默认节点
      const defaultNodes: Node[] = [
        {
          id: 'input-1',
          type: 'input',
          position: { x: 100, y: 100 },
          data: { label: '输入', config: { key: 'input' } },
        },
        {
          id: 'output-1',
          type: 'output',
          position: { x: 100, y: 300 },
          data: { label: '输出', config: { output_key: 'result' } },
        },
      ];
      setNodes(defaultNodes);
      initHistory(defaultNodes, []);
    }
  }, [workflowId, initHistory]);

  // 加载工作流
  const loadWorkflow = async (id: string) => {
    setLoading(true);
    try {
      const response = await agentService.getWorkflow(id);
      if (response.code === 0 && response.data) {
        const wf = response.data;
        setWorkflowName(wf.name || '');
        setWorkflowDescription(wf.description || '');

        // 解析工作流定义
        if (wf.definition) {
          let definition: WorkflowDefinition;
          try {
            if (typeof wf.definition === 'string') {
              definition = JSON.parse(wf.definition);
            } else {
              definition = wf.definition;
            }

            const loadedNodes = (definition.nodes || []) as Node[];
            const loadedEdges = (definition.edges || []) as Edge[];

            setNodes(loadedNodes);
            setEdges(loadedEdges);
            initHistory(loadedNodes, loadedEdges);
          } catch (parseError) {
            message.error('工作流定义格式错误，无法解析');
            logError('Failed to parse workflow definition', 'WorkflowEditorPage', parseError);
          }
        }
      }
    } catch (error) {
      message.error('加载工作流失败');
    } finally {
      setLoading(false);
    }
  };

  // 保存工作流
  const handleSave = async () => {
    setSaving(true);
    try {
      const definition: WorkflowDefinition = {
        version: '1.0',
        nodes: nodes.map((n) => ({
          id: n.id,
          type: n.type,
          position: n.position,
          data: n.data,
        })),
        edges: edges.map((e) => ({
          id: e.id,
          source: e.source,
          target: e.target,
          sourceHandle: e.sourceHandle,
          targetHandle: e.targetHandle,
        })),
      };

      const isCreateMode = workflowId === 'new';

      if (isCreateMode) {
        // 创建新工作流
        const response = await agentService.createWorkflow({
          name: workflowName || '未命名工作流',
          description: workflowDescription,
          type: 'custom',
          definition,
        });
        if (response.code === 0) {
          message.success('工作流创建成功');
          setHasChanges(false);
          navigate(`/workflows/${response.data.workflow_id}/edit`, { replace: true });
        }
      } else {
        // 更新现有工作流
        const response = await agentService.updateWorkflow(workflowId ?? '', {
          name: workflowName || '未命名工作流',
          description: workflowDescription,
          type: 'custom',
          definition,
        } as any);
        if (response.code === 0) {
          message.success('工作流更新成功');
          setHasChanges(false);
        }
      }
    } catch (error) {
      message.error('保存失败');
    } finally {
      setSaving(false);
    }
  };

  // 运行工作流
  const handleRun = async () => {
    if (workflowId === 'new') {
      message.warning('请先保存工作流');
      return;
    }

    try {
      const response = await agentService.startWorkflow(workflowId ?? '', {
        inputs: { query: '测试查询' },
      });
      if (response.code === 0) {
        message.success(`工作流已启动，执行ID: ${response.data.execution_id}`);
        navigate(`/workflows/${workflowId}/executions`);
      }
    } catch (error) {
      message.error('启动失败');
    }
  };

  // 处理节点变化
  const handleNodesChange = useCallback((newNodes: Node[]) => {
    setNodes(newNodes);
    setHasChanges(true);
    pushHistory(newNodes, edges);
  }, [edges, pushHistory]);

  // 处理边变化
  const handleEdgesChange = useCallback((newEdges: Edge[]) => {
    setEdges(newEdges);
    setHasChanges(true);
    pushHistory(nodes, newEdges);
  }, [nodes, pushHistory]);

  // 添加节点
  const handleAddNode = useCallback((nodeType: string, config: Record<string, any>) => {
    const newNode: Node = {
      id: `${nodeType}-${Date.now()}`,
      type: nodeType,
      position: { x: Math.random() * 500 + 100, y: Math.random() * 300 + 100 },
      data: {
        label: nodeTypes.find((t) => t.type === nodeType)?.label || nodeType,
        config,
      },
    };
    const newNodes = [...nodes, newNode];
    setNodes(newNodes);
    setHasChanges(true);
    pushHistory(newNodes, edges);
  }, [nodes, edges, pushHistory]);

  // 更新节点配置
  const handleNodeUpdate = useCallback((nodeId: string, config: Record<string, any>) => {
    setNodes((nds) =>
      nds.map((node) =>
        node.id === nodeId
          ? { ...node, data: { ...node.data, config } }
          : node
      )
    );
    setHasChanges(true);
    message.success('节点配置已更新');
  }, []);

  // 导出工作流
  const handleExport = () => {
    const definition = {
      version: '1.0',
      nodes,
      edges,
    };
    const dataStr = JSON.stringify(definition, null, 2);
    const blob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${workflowName || 'workflow'}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // 导入工作流
  const handleImport = () => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'application/json';
    input.onchange = async (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (file) {
        const text = await file.text();
        try {
          const definition = JSON.parse(text);
          if (definition.nodes) setNodes(definition.nodes);
          if (definition.edges) setEdges(definition.edges);
          setHasChanges(true);
          message.success('工作流已导入');
        } catch {
          message.error('导入失败：无效的 JSON 文件');
        }
      }
    };
    input.click();
  };

  // 清空画布
  const handleClear = () => {
    Modal.confirm({
      title: '确认清空',
      content: '此操作将清空所有节点和连线，确定继续？',
      onOk: () => {
        setNodes([]);
        setEdges([]);
        setHasChanges(true);
      },
    });
  };

  // 验证工作流
  const handleValidate = () => {
    const errors: string[] = [];

    // 检查是否有输入节点
    const hasInput = nodes.some((n) => n.type === 'input');
    if (!hasInput) {
      errors.push('缺少输入节点');
    }

    // 检查是否有输出节点
    const hasOutput = nodes.some((n) => n.type === 'output');
    if (!hasOutput) {
      errors.push('缺少输出节点');
    }

    // 检查孤立节点
    const connectedNodeIds = new Set<string>();
    edges.forEach((e) => {
      connectedNodeIds.add(e.source);
      connectedNodeIds.add(e.target);
    });
    const isolatedNodes = nodes.filter(
      (n) => !connectedNodeIds.has(n.id) && n.type !== 'input'
    );
    if (isolatedNodes.length > 0) {
      errors.push(`${isolatedNodes.length} 个孤立节点`);
    }

    if (errors.length > 0) {
      Modal.warning({
        title: '工作流验证失败',
        content: (
          <ul>
            {errors.map((e, i) => (
              <li key={i}>{e}</li>
            ))}
          </ul>
        ),
      });
    } else {
      Modal.success({
        title: '工作流验证通过',
        content: '工作流定义有效，可以保存和运行。',
      });
    }
  };

  // 缩放功能
  const handleZoomIn = useCallback(() => {
    flowCanvasRef.current?.zoomIn();
  }, []);

  const handleZoomOut = useCallback(() => {
    flowCanvasRef.current?.zoomOut();
  }, []);

  const handleFitView = useCallback(() => {
    flowCanvasRef.current?.fitView();
  }, []);

  // 工具栏菜单项
  const viewMenuItems: MenuProps['items'] = [
    {
      key: 'zoom-in',
      label: '放大',
      icon: <ZoomInOutlined />,
      onClick: handleZoomIn,
    },
    {
      key: 'zoom-out',
      label: '缩小',
      icon: <ZoomOutOutlined />,
      onClick: handleZoomOut,
    },
    {
      key: 'fit',
      label: '适应屏幕',
      icon: <ExpandOutlined />,
      onClick: handleFitView,
    },
  ];

  // 检查撤销/重做可用性
  const canUndo = historyIndex > 0;
  const canRedo = historyIndex < history.length - 1;

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <span>加载中...</span>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-screen">
      {/* 顶部工具栏 */}
      <div className="flex items-center justify-between px-4 py-2 bg-white border-b">
        <Space>
          <Tooltip title="撤销 (Ctrl+Z)">
            <Button
              icon={<UndoOutlined />}
              disabled={!canUndo}
              onClick={handleUndo}
            >
              撤销
            </Button>
          </Tooltip>
          <Tooltip title="重做 (Ctrl+Shift+Z / Ctrl+Y)">
            <Button
              icon={<RedoOutlined />}
              disabled={!canRedo}
              onClick={handleRedo}
            >
              重做
            </Button>
          </Tooltip>
          <div className="w-px h-6 bg-gray-300 mx-2" />
          <Badge dot={hasChanges}>
            <Button
              type="primary"
              icon={<SaveOutlined />}
              loading={saving}
              onClick={handleSave}
            >
              保存
            </Button>
          </Badge>
          <Button
            icon={<PlayCircleOutlined />}
            onClick={handleRun}
            disabled={workflowId === 'new'}
          >
            运行
          </Button>
        </Space>

        <Space>
          <span className="text-sm text-gray-600">
            {workflowName || '未命名工作流'}
          </span>
          <Badge count={nodes.length} showZero>
            <span className="text-xs text-gray-500">节点</span>
          </Badge>
        </Space>

        <Space>
          <Dropdown menu={{ items: viewMenuItems }}>
            <Button icon={<ZoomInOutlined />}>视图</Button>
          </Dropdown>
          <Button icon={<CheckCircleOutlined />} onClick={handleValidate}>
            验证
          </Button>
          <Button icon={<DownloadOutlined />} onClick={handleExport}>
            导出
          </Button>
          <Button icon={<UploadOutlined />} onClick={handleImport}>
            导入
          </Button>
          <Button danger icon={<ClearOutlined />} onClick={handleClear}>
            清空
          </Button>
          <Button onClick={() => setShowConfig(!showConfig)}>
            {showConfig ? '隐藏配置' : '显示配置'}
          </Button>
        </Space>
      </div>

      {/* 主编辑区域 */}
      <div className="flex-1 flex overflow-hidden">
        {/* 节点面板 */}
        <div className="flex-shrink-0">
          <ReactFlowWrapper>
            <NodePalette onNodeAdd={handleAddNode} />
          </ReactFlowWrapper>
        </div>

        {/* 流程图画布 */}
        <div className="flex-1 bg-gray-100">
          <ReactFlowWrapper>
            <FlowCanvas
              canvasRef={flowCanvasRef}
              nodes={nodes}
              edges={edges}
              onNodesChange={handleNodesChange}
              onEdgesChange={handleEdgesChange}
              onNodeSelect={(node) => setSelectedNode(node)}
            />
          </ReactFlowWrapper>
        </div>

        {/* 配置面板 */}
        {showConfig && (
          <div className="flex-shrink-0">
            <ReactFlowWrapper>
              <NodeConfigPanel
                node={selectedNode}
                onNodeUpdate={handleNodeUpdate}
                onClose={() => setSelectedNode(null)}
              />
            </ReactFlowWrapper>
          </div>
        )}
      </div>
    </div>
  );
}

// 用于包装需要 ReactFlowProvider 的组件
function ReactFlowWrapper({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}

// 使用 ErrorBoundary 包裹导出组件
function WorkflowEditorPageWithErrorBoundary() {
  return (
    <ErrorBoundary>
      <WorkflowEditorPage />
    </ErrorBoundary>
  );
}

export default WorkflowEditorPageWithErrorBoundary;
