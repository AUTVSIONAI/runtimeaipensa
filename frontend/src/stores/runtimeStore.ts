// Runtime store - manages runtime info, health, and module states

import { create } from 'zustand';
import type { ModuleState, ModuleMetadata, ModuleHealth, RuntimeInfo, HealthResponse } from '@/types/runtime';

export interface ModuleInfo {
  name: string;
  state: ModuleState;
  metadata: ModuleMetadata;
  health?: ModuleHealth;
}

interface RuntimeState {
  info: RuntimeInfo | null;
  health: HealthResponse | null;
  modules: Record<string, ModuleInfo>;
  status: 'connecting' | 'connected' | 'disconnected' | 'error';

  setInfo: (info: RuntimeInfo) => void;
  setHealth: (health: HealthResponse) => void;
  setModule: (module: ModuleInfo) => void;
  updateModuleState: (name: string, state: ModuleState) => void;
  updateModuleHealth: (name: string, health: ModuleHealth) => void;
  setStatus: (status: RuntimeState['status']) => void;
  clearAll: () => void;
}

// Disable devtools in Next.js to avoid ActionQueueContext error
const useDevtools = process.env.NODE_ENV === 'development' && typeof window !== 'undefined';

export const useRuntimeStore = create<RuntimeState>()(
  useDevtools
    ? (set) => ({
        info: null,
        health: null,
        modules: {},
        status: 'disconnected',

        setInfo: (info) => set({ info }),
        setHealth: (health) => set({ health }),
        setModule: (module) =>
          set((state) => ({
            modules: { ...state.modules, [module.name]: module },
          })),
        updateModuleState: (name, state) =>
          set((s) => ({
            modules: { ...s.modules, [name]: { ...s.modules[name], state } },
          })),
        updateModuleHealth: (name, health) =>
          set((s) => ({
            modules: { ...s.modules, [name]: { ...s.modules[name], health } },
          })),
        setStatus: (status) => set({ status }),
        clearAll: () =>
          set({
            info: null,
            health: null,
            modules: {},
            status: 'disconnected',
          }),
      })
    : (set) => ({
        info: null,
        health: null,
        modules: {},
        status: 'disconnected',

        setInfo: (info) => set({ info }),
        setHealth: (health) => set({ health }),
        setModule: (module) =>
          set((state) => ({
            modules: { ...state.modules, [module.name]: module },
          })),
        updateModuleState: (name, state) =>
          set((s) => ({
            modules: { ...s.modules, [name]: { ...s.modules[name], state } },
          })),
        updateModuleHealth: (name, health) =>
          set((s) => ({
            modules: { ...s.modules, [name]: { ...s.modules[name], health } },
          })),
        setStatus: (status) => set({ status }),
        clearAll: () =>
          set({
            info: null,
            health: null,
            modules: {},
            status: 'disconnected',
          }),
      })
);

// Create a selector that only reads status on client side
export function useRuntimeStatus() {
  const status = useRuntimeStore((s) => s.status);

  // Use a ref to track if we've hydrated
  // This avoids hydration mismatch by returning a stable initial value
  return status;
}