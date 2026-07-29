// Workflow store - manages workflow visualization state

import { create } from 'zustand';
import type { WorkflowNode, WorkflowEdge } from '@/types/runtime';

interface WorkflowExecutionState {
  activeNodeId: string | null;
  completedNodes: string[];
  failedNodes: string[];
  currentStep: number;
  isRunning: boolean;
}

interface WorkflowState {
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
  executionState: WorkflowExecutionState;
  viewport: { x: number; y: number; zoom: number };

  // Node operations
  addNode: (node: WorkflowNode) => void;
  updateNode: (id: string, data: Partial<WorkflowNode>) => void;
  deleteNode: (id: string) => void;
  setNodes: (nodes: WorkflowNode[] | ((prev: WorkflowNode[]) => WorkflowNode[])) => void;

  // Edge operations
  addEdge: (edge: WorkflowEdge) => void;
  updateEdge: (id: string, data: Partial<WorkflowEdge>) => void;
  deleteEdge: (id: string) => void;
  setEdges: (edges: WorkflowEdge[] | ((prev: WorkflowEdge[]) => WorkflowEdge[])) => void;

  // Execution state
  setActiveNode: (id: string | null) => void;
  markNodeCompleted: (id: string) => void;
  markNodeFailed: (id: string) => void;
  setExecutionStep: (step: number) => void;
  setRunning: (running: boolean) => void;
  resetExecution: () => void;

  // Viewport
  setViewport: (viewport: { x: number; y: number; zoom: number }) => void;

  // Reset
  clearWorkflow: () => void;
}

// Disable devtools in Next.js to avoid ActionQueueContext error
const useDevtools = process.env.NODE_ENV === 'development' && typeof window !== 'undefined';

export const useWorkflowStore = create<WorkflowState>()(
  useDevtools
    ? (set) => ({
        nodes: [],
        edges: [],
        executionState: {
          activeNodeId: null,
          completedNodes: [],
          failedNodes: [],
          currentStep: 0,
          isRunning: false,
        },
        viewport: { x: 0, y: 0, zoom: 1 },

        addNode: (node) =>
          set((state) => ({ nodes: [...state.nodes, node] })),
        updateNode: (id, data) =>
          set((state) => ({
            nodes: state.nodes.map((n) => (n.id === id ? { ...n, ...data } : n)),
          })),
        deleteNode: (id) =>
          set((state) => ({
            nodes: state.nodes.filter((n) => n.id !== id),
            edges: state.edges.filter((e) => e.source !== id && e.target !== id),
          })),
        setNodes: (nodes) => set((state) => ({ nodes: typeof nodes === 'function' ? nodes(state.nodes) : nodes })),

        addEdge: (edge) =>
          set((state) => ({ edges: [...state.edges, edge] })),
        updateEdge: (id, data) =>
          set((state) => ({
            edges: state.edges.map((e) => (e.id === id ? { ...e, ...data } : e)),
          })),
        deleteEdge: (id) =>
          set((state) => ({
            edges: state.edges.filter((e) => e.id !== id),
          })),
        setEdges: (edges) => set((state) => ({ edges: typeof edges === 'function' ? edges(state.edges) : edges })),

        setActiveNode: (activeNodeId) =>
          set((state) => ({
            executionState: { ...state.executionState, activeNodeId },
          })),
        markNodeCompleted: (id) =>
          set((state) => ({
            executionState: {
              ...state.executionState,
              completedNodes: [...state.executionState.completedNodes, id],
            },
          })),
        markNodeFailed: (id) =>
          set((state) => ({
            executionState: {
              ...state.executionState,
              failedNodes: [...state.executionState.failedNodes, id],
            },
          })),
        setExecutionStep: (currentStep) =>
          set((state) => ({
            executionState: { ...state.executionState, currentStep },
          })),
        setRunning: (isRunning) =>
          set((state) => ({
            executionState: { ...state.executionState, isRunning },
          })),
        resetExecution: () =>
          set((state) => ({
            executionState: {
              ...state.executionState,
              activeNodeId: null,
              completedNodes: [],
              failedNodes: [],
              currentStep: 0,
              isRunning: false,
            },
          })),

        setViewport: (viewport) => set({ viewport }),

        clearWorkflow: () =>
          set({
            nodes: [],
            edges: [],
            executionState: {
              activeNodeId: null,
              completedNodes: [],
              failedNodes: [],
              currentStep: 0,
              isRunning: false,
            },
          }),
      })
    : (set) => ({
        nodes: [],
        edges: [],
        executionState: {
          activeNodeId: null,
          completedNodes: [],
          failedNodes: [],
          currentStep: 0,
          isRunning: false,
        },
        viewport: { x: 0, y: 0, zoom: 1 },

        addNode: (node) =>
          set((state) => ({ nodes: [...state.nodes, node] })),
        updateNode: (id, data) =>
          set((state) => ({
            nodes: state.nodes.map((n) => (n.id === id ? { ...n, ...data } : n)),
          })),
        deleteNode: (id) =>
          set((state) => ({
            nodes: state.nodes.filter((n) => n.id !== id),
            edges: state.edges.filter((e) => e.source !== id && e.target !== id),
          })),
        setNodes: (nodes) => set((state) => ({ nodes: typeof nodes === 'function' ? nodes(state.nodes) : nodes })),

        addEdge: (edge) =>
          set((state) => ({ edges: [...state.edges, edge] })),
        updateEdge: (id, data) =>
          set((state) => ({
            edges: state.edges.map((e) => (e.id === id ? { ...e, ...data } : e)),
          })),
        deleteEdge: (id) =>
          set((state) => ({
            edges: state.edges.filter((e) => e.id !== id),
          })),
        setEdges: (edges) => set((state) => ({ edges: typeof edges === 'function' ? edges(state.edges) : edges })),

        setActiveNode: (activeNodeId) =>
          set((state) => ({
            executionState: { ...state.executionState, activeNodeId },
          })),
        markNodeCompleted: (id) =>
          set((state) => ({
            executionState: {
              ...state.executionState,
              completedNodes: [...state.executionState.completedNodes, id],
            },
          })),
        markNodeFailed: (id) =>
          set((state) => ({
            executionState: {
              ...state.executionState,
              failedNodes: [...state.executionState.failedNodes, id],
            },
          })),
        setExecutionStep: (currentStep) =>
          set((state) => ({
            executionState: { ...state.executionState, currentStep },
          })),
        setRunning: (isRunning) =>
          set((state) => ({
            executionState: { ...state.executionState, isRunning },
          })),
        resetExecution: () =>
          set((state) => ({
            executionState: {
              ...state.executionState,
              activeNodeId: null,
              completedNodes: [],
              failedNodes: [],
              currentStep: 0,
              isRunning: false,
            },
          })),

        setViewport: (viewport) => set({ viewport }),

        clearWorkflow: () =>
          set({
            nodes: [],
            edges: [],
            executionState: {
              activeNodeId: null,
              completedNodes: [],
              failedNodes: [],
              currentStep: 0,
              isRunning: false,
            },
          }),
      })
);