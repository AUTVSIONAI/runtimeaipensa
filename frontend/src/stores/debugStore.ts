// Debug store - manages logs, snapshots, and performance metrics

import { create } from 'zustand';
import type { DebugLogEntry, StateSnapshot } from '@/types/runtime';

interface DebugState {
  logs: DebugLogEntry[];
  snapshots: StateSnapshot[];
  metrics: {
    fps: number;
    memory: number;
    cpu: number;
  };
  performanceMetrics: {
    renderTime?: number;
    memoryUsage?: number;
    eventsPerSecond?: number;
    renderHistory?: number[];
  };

  addLog: (log: Omit<DebugLogEntry, 'id'>) => void;
  clearLogs: () => void;
  takeSnapshot: () => void;
  clearSnapshots: () => void;
  updateMetrics: (metrics: Partial<DebugState['metrics']>) => void;
  updatePerformanceMetrics: (metrics: Partial<DebugState['performanceMetrics']>) => void;
  handleEvent: (event: any) => void;
}

// Disable devtools in Next.js to avoid ActionQueueContext error
const useDevtools = process.env.NODE_ENV === 'development' && typeof window !== 'undefined';

export const useDebugStore = create<DebugState>()(
  useDevtools
    ? (set, get) => ({
        logs: [],
        snapshots: [],
        metrics: { fps: 0, memory: 0, cpu: 0 },
        performanceMetrics: {
          renderTime: 0,
          memoryUsage: 0,
          eventsPerSecond: 0,
          renderHistory: [] as number[],
        },

        addLog: (log) =>
          set((state) => ({
            logs: [...state.logs, { ...log, id: crypto.randomUUID() }].slice(-5000),
          })),

        clearLogs: () => set({ logs: [] }),

        takeSnapshot: () =>
          set((state) => ({
            snapshots: [
              {
                id: `snap-${Date.now()}`,
                timestamp: new Date().toISOString(),
                runtime: null, // Will be set externally
                modules: {},
                conversationCount: 0,
                activeWorkflows: 0,
              },
              ...state.snapshots,
            ].slice(-50),
          })),

        clearSnapshots: () => set({ snapshots: [] }),

        updateMetrics: (metrics) =>
          set((state) => ({ metrics: { ...state.metrics, ...metrics } })),

        updatePerformanceMetrics: (metrics) =>
          set((state) => ({ performanceMetrics: { ...state.performanceMetrics, ...metrics } })),

        handleEvent: (event) => {
          // Convert runtime events to debug logs
          if (event.event_type.startsWith('TASK_') || event.event_type.startsWith('AGENT_')) {
            get().addLog({
              timestamp: event.timestamp,
              level: event.event_type.includes('FAILED') || event.event_type.includes('ERROR') ? 'error' : 'info',
              source: event.source,
              message: `${event.event_type}: ${event.payload.task_name || event.payload.agent_name || ''}`,
              data: event.payload,
            });
          }
        },
      })
    : (set, get) => ({
        logs: [],
        snapshots: [],
        metrics: { fps: 0, memory: 0, cpu: 0 },
        performanceMetrics: {
          renderTime: 0,
          memoryUsage: 0,
          eventsPerSecond: 0,
          renderHistory: [] as number[],
        },

        addLog: (log) =>
          set((state) => ({
            logs: [...state.logs, { ...log, id: crypto.randomUUID() }].slice(-5000),
          })),

        clearLogs: () => set({ logs: [] }),

        takeSnapshot: () =>
          set((state) => ({
            snapshots: [
              {
                id: `snap-${Date.now()}`,
                timestamp: new Date().toISOString(),
                runtime: null,
                modules: {},
                conversationCount: 0,
                activeWorkflows: 0,
              },
              ...state.snapshots,
            ].slice(-50),
          })),

        clearSnapshots: () => set({ snapshots: [] }),

        updateMetrics: (metrics) =>
          set((state) => ({ metrics: { ...state.metrics, ...metrics } })),

        updatePerformanceMetrics: (metrics) =>
          set((state) => ({ performanceMetrics: { ...state.performanceMetrics, ...metrics } })),

        handleEvent: (event) => {
          // Convert runtime events to debug logs
          if (event.event_type.startsWith('TASK_') || event.event_type.startsWith('AGENT_')) {
            get().addLog({
              timestamp: event.timestamp,
              level: event.event_type.includes('FAILED') || event.event_type.includes('ERROR') ? 'error' : 'info',
              source: event.source,
              message: `${event.event_type}: ${event.payload.task_name || event.payload.agent_name || ''}`,
              data: event.payload,
            });
          }
        },
      })
);

// Fix: we need to reference the store properly - adding getters
let runtime: any = null;
let modules: any = {};

export function setRuntimeRef(ref: any) { runtime = ref; }
export function setModulesRef(ref: any) { modules = ref; }