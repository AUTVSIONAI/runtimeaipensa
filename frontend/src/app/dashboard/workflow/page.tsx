'use client';

import dynamic from 'next/dynamic';

const ReactFlow = dynamic(
  () => import('reactflow').then(mod => mod.default),
  { ssr: false, loading: () => <div className="h-full w-full flex items-center justify-center">Loading workflow...</div> }
);

import {
  Node,
  Edge,
  Connection,
  EdgeTypes,
  NodeTypes,
  addEdge,
  applyNodeChanges,
  applyEdgeChanges,
  MarkerType,
  Controls,
  MiniMap,
  Background,
  useReactFlow,
  NodeChange,
  EdgeChange,
  Handle,
  Position
} from 'reactflow';
import { useWorkflowStore } from '@/stores/workflowStore';
import { useUIStore } from '@/stores/uiStore';
import type { WorkflowNode, WorkflowEdge } from '@/types/runtime';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Plus, Trash2, Play, Pause, CircleStop, RotateCcw, Save, Download, Upload, X, ChevronLeft, ChevronRight,
  Bot, Wrench, GitBranch, Diamond, Circle, Square, Terminal, Brain, Zap, Settings, Search, Filter,
  CheckCircle, AlertCircle, RefreshCw, Trash, FolderOpen, Clock
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useState, useCallback, useMemo, useEffect } from 'react';
import { api } from '@/lib/api';
import { Input } from '@/components/ui/input';
import { format } from 'date-fns';

// Custom Node Types
interface CustomNodeData {
  label: string;
  type: 'start' | 'agent' | 'tool' | 'condition' | 'end';
  config?: Record<string, any>;
  status?: 'idle' | 'running' | 'completed' | 'failed';
  agentType?: string;
  toolName?: string;
  condition?: string;
}

function StartNode({ data }: { data: CustomNodeData }) {
  return (
    <div className="w-32 p-2 rounded-lg bg-green-100 dark:bg-green-900/30 border border-green-300 dark:border-green-700">
      <div className="flex items-center justify-center gap-1.5 text-green-700 dark:text-green-300 font-medium">
        <Circle className="h-4 w-4" />
        <span>{data.label}</span>
      </div>
      <div className="mt-1 text-xs text-green-600 dark:text-green-400 text-center">Entry Point</div>
      {/* Start node only has source handle (output), no target handle */}
      <Handle type="source" position={Position.Bottom} className="h-2 w-2 bg-green-500" />
    </div>
  );
}

function AgentNode({ data }: { data: CustomNodeData }) {
  const statusColors = {
    idle: 'bg-gray-100 dark:bg-gray-800 border-gray-300 dark:border-gray-600',
    running: 'bg-blue-100 dark:bg-blue-900/30 border-blue-300 dark:border-blue-700 animate-pulse',
    completed: 'bg-green-100 dark:bg-green-900/30 border-green-300 dark:border-green-700',
    failed: 'bg-red-100 dark:bg-red-900/30 border-red-300 dark:border-red-700',
  };

  const statusIcons = {
    idle: <Circle className="h-3.5 w-3.5 text-gray-400" />,
    running: <Zap className="h-3.5 w-3.5 text-blue-500 animate-pulse" />,
    completed: <CheckCircle className="h-3.5 w-3.5 text-green-500" />,
    failed: <AlertCircle className="h-3.5 w-3.5 text-red-500" />,
  };

  return (
    <div className={cn(
      'w-40 p-3 rounded-lg border-2 transition-all duration-200',
      statusColors[data.status || 'idle']
    )}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-1.5 text-purple-700 dark:text-purple-300 font-medium">
          <Bot className="h-4 w-4" />
          <span className="truncate">{data.label}</span>
        </div>
        {statusIcons[data.status || 'idle']}
      </div>
      {data.agentType && (
        <div className="text-xs text-muted-foreground mb-1">{data.agentType}</div>
      )}
      <Handle type="target" position={Position.Left} className="h-2 w-2 bg-purple-500" />
      <Handle type="source" position={Position.Right} className="h-2 w-2 bg-purple-500" />
    </div>
  );
}

function ToolNode({ data }: { data: CustomNodeData }) {
  const statusColors = {
    idle: 'bg-gray-100 dark:bg-gray-800 border-gray-300 dark:border-gray-600',
    running: 'bg-blue-100 dark:bg-blue-900/30 border-blue-300 dark:border-blue-700 animate-pulse',
    completed: 'bg-green-100 dark:bg-green-900/30 border-green-300 dark:border-green-700',
    failed: 'bg-red-100 dark:bg-red-900/30 border-red-300 dark:border-red-700',
  };

  const statusIcons = {
    idle: <Wrench className="h-3.5 w-3.5 text-gray-400" />,
    running: <Zap className="h-3.5 w-3.5 text-blue-500 animate-pulse" />,
    completed: <CheckCircle className="h-3.5 w-3.5 text-green-500" />,
    failed: <AlertCircle className="h-3.5 w-3.5 text-red-500" />,
  };

  return (
    <div className={cn(
      'w-40 p-3 rounded-lg border-2 transition-all duration-200',
      statusColors[data.status || 'idle']
    )}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-1.5 text-orange-700 dark:text-orange-300 font-medium">
          <Wrench className="h-4 w-4" />
          <span className="truncate">{data.label}</span>
        </div>
        {statusIcons[data.status || 'idle']}
      </div>
      {data.toolName && (
        <div className="text-xs text-muted-foreground mb-1">{data.toolName}</div>
      )}
      <Handle type="target" position={Position.Left} className="h-2 w-2 bg-orange-500" />
      <Handle type="source" position={Position.Right} className="h-2 w-2 bg-orange-500" />
    </div>
  );
}

function ConditionNode({ data }: { data: CustomNodeData }) {
  const status = data.status || 'idle';
  const statusColors = {
    idle: 'bg-gray-100 dark:bg-gray-800 border-gray-300 dark:border-gray-600',
    running: 'bg-blue-100 dark:bg-blue-900/30 border-blue-300 dark:border-blue-700 animate-pulse',
    completed: 'bg-green-100 dark:bg-green-900/30 border-green-300 dark:border-green-700',
    failed: 'bg-red-100 dark:bg-red-900/30 border-red-300 dark:border-red-700',
  };

  return (
    <div className={cn(
      'w-40 p-3 rounded-lg border-2 transition-all duration-200',
      statusColors[status as keyof typeof statusColors]
    )}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-1.5 text-amber-700 dark:text-amber-300 font-medium">
          <Diamond className="h-4 w-4" />
          <span className="truncate">{data.label}</span>
        </div>
      </div>
      {data.condition && (
        <div className="text-xs text-muted-foreground mb-1 truncate">{data.condition}</div>
      )}
      <Handle type="target" position={Position.Left} className="h-2 w-2 bg-amber-500" />
      <Handle type="source" position={Position.Right} className="h-2 w-2 bg-amber-500" />
      <Handle type="source" position={Position.Bottom} className="h-2 w-2 bg-amber-500" />
    </div>
  );
}

function EndNode({ data }: { data: CustomNodeData }) {
  return (
    <div className="w-32 p-2 rounded-lg bg-red-100 dark:bg-red-900/30 border border-red-300 dark:border-red-700">
      <div className="flex items-center justify-center gap-1.5 text-red-700 dark:text-red-300 font-medium">
        <Square className="h-4 w-4" />
        <span>{data.label}</span>
      </div>
      <div className="mt-1 text-xs text-red-600 dark:text-red-400 text-center">Exit Point</div>
      {/* End node only has target handle (input), no source handle */}
      <Handle type="target" position={Position.Top} className="h-2 w-2 bg-red-500" />
    </div>
  );
}

const nodeTypes: NodeTypes = {
  start: StartNode,
  agent: AgentNode,
  tool: ToolNode,
  condition: ConditionNode,
  end: EndNode,
};

export default function WorkflowPage() {
  const {
    nodes,
    edges,
    setNodes,
    setEdges,
    executionState,
    setActiveNode,
    markNodeCompleted,
    markNodeFailed,
    setRunning,
    resetExecution,
  } = useWorkflowStore();
  const { rightPanelOpen, setRightPanelOpen } = useUIStore();
  const [selectedNode, setSelectedNode] = useState<Node<CustomNodeData> | null>(null);
  const [sidePanelOpen, setSidePanelOpen] = useState(false);
  const [scale, setScale] = useState(1);
  const [savedWorkflows, setSavedWorkflows] = useState<Array<{
    id: string;
    name: string;
    nodes: WorkflowNode[];
    edges: WorkflowEdge[];
    createdAt: string
  }>>([]);
  const [showSaveModal, setShowSaveModal] = useState(false);
  const [workflowName, setWorkflowName] = useState('');
  const [showBackendWorkflows, setShowBackendWorkflows] = useState(false);
  const [backendWorkflows, setBackendWorkflows] = useState<any[]>([]);
  const [loadingBackendWorkflows, setLoadingBackendWorkflows] = useState(false);
  const [executionId, setExecutionId] = useState<string | null>(null);
  const [currentWorkflowId, setCurrentWorkflowId] = useState<string | null>(null);
  const [pollingInterval, setPollingInterval] = useState<NodeJS.Timeout | null>(null);
  const [workflowInitialized, setWorkflowInitialized] = useState(false);

  // Initialize with default start and end nodes
  useEffect(() => {
    if (!workflowInitialized && nodes.length === 0) {
      const startNode: WorkflowNode = {
        id: 'start-1',
        type: 'start',
        position: { x: 250, y: 100 },
        data: { label: 'Start' },
      };
      const endNode: WorkflowNode = {
        id: 'end-1',
        type: 'end',
        position: { x: 250, y: 500 },
        data: { label: 'End' },
      };
      setNodes([startNode, endNode]);
      setWorkflowInitialized(true);
    }
  }, [nodes.length, workflowInitialized, setNodes]);

  const onNodesChange = useCallback((changes: NodeChange[]) => {
    setNodes((nds) => applyNodeChanges(changes, nds) as any);
  }, [setNodes]);

  const onEdgesChange = useCallback((changes: EdgeChange[]) => {
    setEdges((eds) => applyEdgeChanges(changes, eds) as any);
  }, [setEdges]);

  const onConnect = useCallback((connection: Connection) => {
    setEdges((eds) => addEdge({ ...connection, type: 'default', animated: true }, eds) as any);
  }, [setEdges]);

  const onNodeClick = useCallback((event: React.MouseEvent, node: Node) => {
    event.stopPropagation();
    setSelectedNode(node);
    setSidePanelOpen(true);
    setActiveNode(node.id);
  }, [setActiveNode]);

  const onPaneClick = useCallback(() => {
    setSelectedNode(null);
    setSidePanelOpen(false);
    setActiveNode(null);
  }, [setActiveNode]);

  const addNewNode = (type: 'start' | 'agent' | 'tool' | 'condition' | 'end') => {
    const nodeCount = nodes.length;
    const labels = { start: 'Start', agent: 'Agent', tool: 'Tool', condition: 'Condition', end: 'End' };

    const newNode: WorkflowNode = {
      id: `${type}-${Date.now()}`,
      type,
      position: { x: 250 + (nodeCount % 5) * 150, y: 150 + Math.floor(nodeCount / 5) * 150 },
      data: { label: `${labels[type]} ${nodeCount + 1}` },
    };

    setNodes((nds) => [...nds, newNode]);
  };

  const deleteSelectedNode = () => {
    if (selectedNode) {
      // Prevent deleting start/end nodes
      if (selectedNode.type === 'start' || selectedNode.type === 'end') {
        alert('Cannot delete Start or End nodes');
        return;
      }
      setNodes((nds) => nds.filter((n) => n.id !== selectedNode.id));
      setEdges((eds) => eds.filter((e) => e.source !== selectedNode.id && e.target !== selectedNode.id));
      setSelectedNode(null);
      setSidePanelOpen(false);
    }
  };

  // Load backend workflows on mount
  useEffect(() => {
    loadBackendWorkflows();
  }, []);

  const loadBackendWorkflows = async () => {
    setLoadingBackendWorkflows(true);
    try {
      const response = await api.listWorkflows();
      setBackendWorkflows(response.workflows || []);
    } catch (error) {
      console.error('Failed to load backend workflows:', error);
    } finally {
      setLoadingBackendWorkflows(false);
    }
  };

  const runWorkflow = async () => {
    if (nodes.length === 0) return;

    setRunning(true);
    // Find the start node dynamically instead of hardcoding 'start-1'
    const startNode = nodes.find(n => n.type === 'start');
    if (startNode) {
      setActiveNode(startNode.id);
    }

    try {
      // Convert ReactFlow nodes/edges to backend DAG format
      const dagNodes = nodes.map(node => {
        let nodeType = 'task';
        let action = getActionFromNode(node as any);

        // Map frontend node types to backend StepType values
        if (node.type === 'start') {
          nodeType = 'start';
          action = ''; // START nodes have no action
        } else if (node.type === 'agent') {
          nodeType = 'task';
          action = `agent:${node.data.agentType || 'default'}`;
        } else if (node.type === 'tool') {
          nodeType = 'task';
          action = `tool:${node.data.toolName || 'default'}`;
        } else if (node.type === 'condition') {
          nodeType = 'condition';
          action = 'condition';
        } else if (node.type === 'end') {
          nodeType = 'end';
          action = 'end';
        }

        return {
          id: node.id,
          name: node.data.label,
          description: node.data.config?.description || '',
          type: nodeType,
          action: action,
          parameters: node.data.config || {},
          agent_type: node.data.agentType || 'default',
          max_retries: 3,
          timeout_seconds: 300,
          loop_config: node.data.config?.loopConfig,
          condition: node.data.condition,
        };
      });

      const dagEdges = edges.map(edge => ({
        source: edge.source,
        target: edge.target,
      }));

      // Create workflow from DAG
      const workflowRes = await api.createWorkflowFromDag({
        name: workflowName || `Workflow ${Date.now()}`,
        description: '',
        nodes: dagNodes,
        edges: dagEdges,
      });

      // Execute the workflow
      const executionRes = await api.executeWorkflow(workflowRes.workflow_id, {
        variables: {},
      });

      setExecutionId(executionRes.execution_id);
      setCurrentWorkflowId(workflowRes.workflow_id);

      // Poll for execution status
      pollExecution(executionRes.execution_id, workflowRes.workflow_id);
    } catch (error) {
      console.error('Failed to execute workflow:', error);
      alert(`Failed to execute workflow: ${error}`);
      setRunning(false);
      setActiveNode(null);
    }
  };

  const pollExecution = async (execId: string, workflowId: string) => {
    if (pollingInterval) clearInterval(pollingInterval);

    const interval = setInterval(async () => {
      try {
        const execution = await api.getExecution(execId);

        // Update execution state based on backend status
        if (execution.completed_steps) {
          // Update node statuses based on completed steps
          setNodes((nds) => nds.map(node => {
            if (execution.completed_steps?.includes(node.id)) {
              return { ...node, data: { ...node.data, status: 'completed' as const } };
            }
            if (execution.failed_steps?.includes(node.id)) {
              return { ...node, data: { ...node.data, status: 'failed' as const } };
            }
            if (execution.current_step === node.id) {
              return { ...node, data: { ...node.data, status: 'running' as const } };
            }
            return node;
          }));
        }

        if (execution.status === 'completed' || execution.status === 'failed' || execution.status === 'cancelled') {
          clearInterval(interval);
          setRunning(false);
          setActiveNode(null);
          setExecutionId(null);
          setCurrentWorkflowId(null);

          // Show completion notification
          if (execution.status === 'completed') {
            alert('Workflow completed successfully!');
          } else if (execution.status === 'failed') {
            alert(`Workflow failed: ${execution.error || 'Unknown error'}`);
          }
        }
      } catch (error) {
        console.error('Polling error:', error);
        clearInterval(interval);
        setRunning(false);
        setActiveNode(null);
        setExecutionId(null);
        setCurrentWorkflowId(null);
      }
    }, 1000);

    setPollingInterval(interval);
  };

  const stopWorkflow = async () => {
    if (executionId && currentWorkflowId) {
      try {
        await api.cancelWorkflow(currentWorkflowId, executionId);
      } catch (error) {
        console.error('Failed to cancel workflow:', error);
      }
    }
    if (pollingInterval) clearInterval(pollingInterval);
    setRunning(false);
    resetExecution();
    setExecutionId(null);
    setCurrentWorkflowId(null);
  };

  const getActionFromNode = (node: Node) => {
    const data = node.data as CustomNodeData;
    if (node.type === 'start') return '';
    if (node.type === 'end') return '';
    if (data.condition) return 'condition';
    if (node.type === 'agent') return `agent:${data.agentType || 'default'}`;
    if (node.type === 'tool') return `tool:${data.toolName || 'default'}`;
    return 'task';
  };

  const saveWorkflow = async () => {
    if (!workflowName.trim()) return;

    try {
      // Convert to backend format
      const dagNodes = nodes.map(node => {
        let nodeType = 'task';
        let action = getActionFromNode(node);

        // Map frontend node types to backend StepType values
        if (node.type === 'start') {
          nodeType = 'start';
          action = '';
        } else if (node.type === 'agent') {
          nodeType = 'task';
          action = `agent:${node.data.agentType || 'default'}`;
        } else if (node.type === 'tool') {
          nodeType = 'task';
          action = `tool:${node.data.toolName || 'default'}`;
        } else if (node.type === 'condition') {
          nodeType = 'condition';
          action = 'condition';
        } else if (node.type === 'end') {
          nodeType = 'end';
          action = '';
        }

        return {
          id: node.id,
          name: node.data.label,
          description: node.data.config?.description || '',
          type: nodeType,
          action: action,
          parameters: node.data.config || {},
          agent_type: node.data.agentType || 'default',
          max_retries: 3,
          timeout_seconds: 300,
          loop_config: node.data.config?.loopConfig,
          condition: node.data.condition,
        };
      });

      const dagEdges = edges.map(edge => ({
        source: edge.source,
        target: edge.target,
      }));

      const workflowRes = await api.createWorkflowFromDag({
        name: workflowName,
        description: '',
        nodes: dagNodes,
        edges: dagEdges,
      });

      // Add to saved workflows
      setSavedWorkflows([...savedWorkflows, {
        id: workflowRes.workflow_id,
        name: workflowName,
        nodes,
        edges,
        createdAt: new Date().toISOString(),
      }]);

      setShowSaveModal(false);
      setWorkflowName('');
      alert('Workflow saved successfully!');
    } catch (error) {
      console.error('Failed to save workflow:', error);
      alert(`Failed to save workflow: ${error}`);
    }
  };

  const loadWorkflow = (workflow: typeof savedWorkflows[0]) => {
    // Ensure all nodes have valid positions
    const nodesWithPositions = (workflow.nodes as any).map((node: any, index: number) => ({
      ...node,
      position: node.position && typeof node.position.x === 'number' && typeof node.position.y === 'number'
        ? node.position
        : { x: 250 + (index % 5) * 150, y: 150 + Math.floor(index / 5) * 150 }
    }));
    setNodes(nodesWithPositions);
    setEdges(workflow.edges as any);
  };

  const loadBackendWorkflow = async (workflowId: string) => {
    try {
      const workflow = await api.getWorkflow(workflowId);
      const exported = await api.exportWorkflow(workflowId);

      if (exported.nodes && exported.edges) {
        // Ensure all nodes have valid positions (ReactFlow requires x, y)
        const nodesWithPositions = (exported.nodes as any).map((node: any, index: number) => ({
          ...node,
          position: node.position && typeof node.position.x === 'number' && typeof node.position.y === 'number'
            ? node.position
            : { x: 250 + (index % 5) * 150, y: 150 + Math.floor(index / 5) * 150 }
        }));
        setNodes(nodesWithPositions);
        setEdges(exported.edges as any);
      }
      setShowBackendWorkflows(false);
    } catch (error) {
      console.error('Failed to load backend workflow:', error);
      alert(`Failed to load workflow: ${error}`);
    }
  };

  const exportWorkflow = () => {
    const data = JSON.stringify({ nodes, edges }, null, 2);
    const blob = new Blob([data], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `workflow-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleFileImport = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (e) => {
        try {
          const data = JSON.parse(e.target?.result as string);
          if (data.nodes && data.edges) {
            // Ensure all nodes have valid positions
            const nodesWithPositions = data.nodes.map((node: any, index: number) => ({
              ...node,
              position: node.position && typeof node.position.x === 'number' && typeof node.position.y === 'number'
                ? node.position
                : { x: 250 + (index % 5) * 150, y: 150 + Math.floor(index / 5) * 150 }
            }));
            setNodes(nodesWithPositions as any);
            setEdges(data.edges as any);
          }
        } catch (err) {
          alert('Invalid workflow file');
        }
      };
      reader.readAsText(file);
    }
  };

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollingInterval) clearInterval(pollingInterval);
    };
  }, []);

  return (
    <div className="h-full flex flex-col">
      {/* Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-4 border-b border-border bg-card">
        <div className="flex items-center gap-4">
          <h1 className="text-xl font-bold">Workflow Visualizer</h1>
          <Badge variant="outline" className="text-xs">
            {nodes.length} nodes, {edges.length} edges
          </Badge>
        </div>

        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1 border border-border rounded-lg overflow-hidden">
            <Button variant="ghost" size="icon" onClick={() => setScale(Math.max(0.25, scale - 0.25))} title="Zoom Out">
              <Search className="h-4 w-4" />
            </Button>
            <span className="px-2 text-sm font-mono text-muted-foreground">{Math.round(scale * 100)}%</span>
            <Button variant="ghost" size="icon" onClick={() => setScale(Math.min(2, scale + 0.25))} title="Zoom In">
              <Search className="h-4 w-4 rotate-180" />
            </Button>
            <Button variant="ghost" size="icon" onClick={() => { setScale(1); }} title="Fit View">
              <RefreshCw className="h-4 w-4" />
            </Button>
          </div>

          <Separator orientation="vertical" className="h-8 mx-2" />

          {/* Tabs for palette, saved, backend */}
          <Tabs defaultValue="palette" className="hidden md:flex">
            <TabsList className="h-8 bg-transparent">
              <TabsTrigger value="palette" className="px-2 text-xs">Palette</TabsTrigger>
              <TabsTrigger value="saved" className="px-2 text-xs">Saved</TabsTrigger>
              <TabsTrigger value="backend" className="px-2 text-xs">Backend</TabsTrigger>
              <TabsTrigger value="settings" className="px-2 text-xs">Settings</TabsTrigger>
            </TabsList>

            <TabsContent value="palette" className="absolute top-12 right-4 z-50 w-64 bg-card border border-border rounded-lg shadow-lg p-2 focus-visible:outline-none">
              <div className="space-y-1">
                {[
                  { type: 'agent' as const, label: 'Agent Node', icon: Bot, desc: 'AI agent for reasoning' },
                  { type: 'tool' as const, label: 'Tool Node', icon: Wrench, desc: 'Execute a tool' },
                  { type: 'condition' as const, label: 'Condition', icon: Diamond, desc: 'Branch based on condition' },
                ].map((item) => (
                  <button
                    key={item.type}
                    onClick={() => addNewNode(item.type)}
                    className="w-full flex items-center gap-2 p-2 rounded-lg hover:bg-accent transition-colors text-left"
                  >
                    <item.icon className="h-4 w-4 text-muted-foreground" />
                    <div className="flex-1 text-left">
                      <div className="text-sm font-medium">{item.label}</div>
                      <div className="text-xs text-muted-foreground">{item.desc}</div>
                    </div>
                  </button>
                ))}
              </div>
            </TabsContent>

            <TabsContent value="saved" className="absolute top-12 right-4 z-50 w-72 bg-card border border-border rounded-lg shadow-lg p-2 focus-visible:outline-none">
              {savedWorkflows.length === 0 ? (
                <div className="p-4 text-center text-muted-foreground text-sm">No saved workflows</div>
              ) : (
                <div className="space-y-1 max-h-60 overflow-auto">
                  {savedWorkflows.map((wf) => (
                    <div key={wf.id} className="p-2 hover:bg-accent rounded flex items-center justify-between">
                      <div>
                        <div className="text-sm font-medium">{wf.name}</div>
                        <div className="text-xs text-muted-foreground">{wf.nodes.length} nodes, {format(new Date(wf.createdAt), 'MMM d, yyyy')}</div>
                      </div>
                      <Button variant="ghost" size="icon" onClick={() => loadWorkflow(wf)}>
                        <Download className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  ))}
                </div>
              )}
            </TabsContent>

            <TabsContent value="backend" className="absolute top-12 right-4 z-50 w-80 bg-card border border-border rounded-lg shadow-lg p-2 focus-visible:outline-none">
              <div className="flex items-center justify-between mb-2">
                <span className="font-medium">Backend Workflows</span>
                <Button variant="ghost" size="icon" onClick={loadBackendWorkflows} disabled={loadingBackendWorkflows}>
                  <RefreshCw className={`h-4 w-4 ${loadingBackendWorkflows ? 'animate-spin' : ''}`} />
                </Button>
              </div>
              {loadingBackendWorkflows ? (
                <div className="p-4 text-center text-muted-foreground text-sm">Loading...</div>
              ) : backendWorkflows.length === 0 ? (
                <div className="p-4 text-center text-muted-foreground text-sm">No backend workflows found</div>
              ) : (
                <div className="space-y-1 max-h-60 overflow-auto">
                  {backendWorkflows.map((wf: any) => (
                    <div key={wf.workflow_id} className="p-2 hover:bg-accent rounded flex items-center justify-between">
                      <div>
                        <div className="text-sm font-medium">{wf.name}</div>
                        <div className="text-xs text-muted-foreground">{wf.steps?.length || 0} steps</div>
                      </div>
                      <Button variant="ghost" size="icon" onClick={() => loadBackendWorkflow(wf.workflow_id)} title="Load workflow">
                        <FolderOpen className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  ))}
                </div>
              )}
            </TabsContent>

            <TabsContent value="settings" className="absolute top-12 right-4 z-50 w-64 bg-card border border-border rounded-lg shadow-lg p-2 focus-visible:outline-none">
              <div className="space-y-3">
                <label className="flex items-center justify-between text-sm">
                  <span>Snap to Grid</span>
                  <input type="checkbox" defaultChecked className="w-4 h-4 rounded border-border" />
                </label>
                <label className="flex items-center justify-between text-sm">
                  <span>Show Minimap</span>
                  <input type="checkbox" defaultChecked className="w-4 h-4 rounded border-border" />
                </label>
                <label className="flex items-center justify-between text-sm">
                  <span>Animated Edges</span>
                  <input type="checkbox" defaultChecked className="w-4 h-4 rounded border-border" />
                </label>
              </div>
            </TabsContent>
          </Tabs>

          {/* Action Buttons */}
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={exportWorkflow}>
              <Download className="h-4 w-4 mr-1" />
              Export
            </Button>
            <input type="file" accept=".json" onChange={handleFileImport} className="hidden" id="import-file" />
            <Button variant="outline" size="sm" onClick={() => document.getElementById('import-file')?.click()}>
              <Upload className="h-4 w-4 mr-1" />
              Import
            </Button>
            <Button variant="outline" size="sm" onClick={() => { setShowSaveModal(true); }}>
              <Save className="h-4 w-4 mr-1" />
              Save
            </Button>

            <Separator orientation="vertical" className="h-8 mx-2" />

            {!executionState.isRunning ? (
              <Button onClick={runWorkflow} disabled={nodes.length === 0}>
                <Play className="h-4 w-4 mr-1" />
                Run
              </Button>
            ) : (
              <>
                <Button variant="secondary" onClick={stopWorkflow}>
                  <CircleStop className="h-4 w-4 mr-1" />
                  Stop
                </Button>
                <Button variant="outline" onClick={stopWorkflow}>
                  <Pause className="h-4 w-4 mr-1" />
                  Pause
                </Button>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Canvas */}
      <div className="flex-1 relative">
        <ReactFlow
          nodes={nodes as any}
          edges={edges as any}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          onNodeClick={onNodeClick}
          onPaneClick={onPaneClick}
          nodeTypes={nodeTypes}
          fitView
          attributionPosition="bottom-right"
        >
          <Background color="#e5e7eb" gap={16} />
          <Controls />
          <MiniMap />
        </ReactFlow>

        {/* Execution Status */}
        {executionState.isRunning && executionId && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 20 }}
            className="absolute bottom-4 right-4 z-10"
          >
            <Card className="w-72 shadow-xl">
              <CardContent className="p-3">
                <div className="flex items-center gap-2 mb-2">
                  <Zap className="h-4 w-4 text-yellow-500 animate-pulse" />
                  <span className="font-medium">Executing...</span>
                  <Badge variant="secondary" className="ml-auto text-xs">
                    Execution: {executionId}
                  </Badge>
                </div>
                <div className="flex items-center gap-2 text-sm">
                  <div className="flex-1 h-1.5 bg-muted rounded-full overflow-hidden">
                    <motion.div
                      className="h-full bg-primary"
                      animate={{ width: `${Math.min((executionState.currentStep / Math.max(nodes.length, 1)) * 100, 100)}%` }}
                      transition={{ duration: 0.5 }}
                    />
                  </div>
                  <span className="text-muted-foreground w-16 text-right">
                    {executionState.completedNodes.length}/{nodes.length}
                  </span>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        )}

        {/* Save Modal */}
        <AnimatePresence>
          {showSaveModal && (
            <div className="fixed inset-0 z-50 flex items-center justify-center">
              <div className="absolute inset-0 bg-black/50" onClick={() => setShowSaveModal(false)} />
              <motion.div
            initial={{ scale: 0.95, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.95, opacity: 0 }}
            className="relative bg-card border border-border rounded-xl max-w-md w-full mx-4"
          >
            <div className="p-4 border-b border-border flex items-center justify-between">
              <h3 className="font-semibold">Save Workflow</h3>
              <button onClick={() => setShowSaveModal(false)} className="p-1 rounded hover:bg-accent">
                <X className="h-5 w-5" />
              </button>
            </div>
            <div className="p-4 space-y-4">
              <div>
                <label className="text-sm text-muted-foreground block mb-1">Workflow Name</label>
                <Input
                  value={workflowName}
                  onChange={(e) => setWorkflowName(e.target.value)}
                  placeholder="My Workflow"
                />
              </div>
              <div className="flex justify-end gap-2">
                <Button variant="outline" onClick={() => setShowSaveModal(false)}>Cancel</Button>
                <Button onClick={saveWorkflow} disabled={!workflowName.trim()}>Save</Button>
              </div>
            </div>
          </motion.div>
            </div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}