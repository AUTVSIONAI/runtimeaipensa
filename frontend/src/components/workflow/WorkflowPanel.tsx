'use client';

import { useRuntimeStore } from '@/stores/runtimeStore';
import { useChatStore } from '@/stores/chatStore';
import { useWorkflowStore } from '@/stores/workflowStore';
import { useTimelineStore } from '@/stores/timelineStore';
import { useUIStore } from '@/stores/uiStore';

export function WorkflowPanel() {
  const { nodes, edges, executionState, setNodes, setEdges, addNode, addEdge, setActiveNode, markNodeCompleted, markNodeFailed, setRunning } = useWorkflowStore();
  const { rightPanelTab } = useUIStore();

  return (
    <div className="h-full flex flex-col p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-medium">Workflow Visualizer</h3>
        <div className="flex gap-2">
          <button className="btn-secondary btn-sm">Add Agent</button>
          <button className="btn-secondary btn-sm">Add Tool</button>
          <button className="btn-secondary btn-sm">Run</button>
        </div>
      </div>

      <div className="flex-1 bg-muted/30 rounded-lg border border-border relative overflow-hidden">
        {nodes.length === 0 && (
          <div className="flex items-center justify-center h-full text-muted-foreground">
            <div className="text-center p-8">
              <svg className="mx-auto h-12 w-12 text-muted-foreground/50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
              <p className="mt-4 text-lg">No workflow loaded</p>
              <p className="text-sm">Add nodes to build a workflow</p>
            </div>
          </div>
        )}
        <div className="absolute inset-0 bg-[url('data:image/svg+xml,%3Csvg width=%2240%22 height=%2240%22 viewBox=%220 0 40 40%22 xmlns=%22http://www.w3.org/2000/svg%22%3E%3Cg fill=%22none%22 fill-rule=%22evenodd%22%3E%3Cg fill=%22%239C92AC%22 fill-opacity=%220.03%22%3E%3Cpath d=%22M0 38.59L38.59 0H0V38.59z%22/%3E%3C/g%3E%3C/g%3E%3C/svg%3E')" />
      </div>

      {/* Stats */}
      <div className="flex gap-4 mt-4 text-sm text-muted-foreground">
        <span>Nodes: {nodes.length}</span>
        <span>Edges: {edges.length}</span>
        <span>Running: {executionState.isRunning ? 'Yes' : 'No'}</span>
        <span>Step: {executionState.currentStep}</span>
      </div>
    </div>
  );
}