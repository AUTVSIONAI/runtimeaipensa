// Plugins store - manages plugin state with backend integration

import { create } from 'zustand';
import { devtools, subscribeWithSelector } from 'zustand/middleware';
import { api } from '@/lib/api';
import type { PluginInfo, PluginsResponse, PluginConfigRequest } from '@/types/runtime';

interface PluginsState {
  plugins: PluginInfo[];
  isLoading: boolean;
  error: string | null;
  pendingActions: Record<string, boolean>;

  // Actions
  loadPlugins: () => Promise<void>;
  togglePlugin: (pluginId: string, enabled: boolean) => Promise<void>;
  startPlugin: (pluginId: string) => Promise<void>;
  stopPlugin: (pluginId: string) => Promise<void>;
  updatePluginConfig: (pluginId: string, config: PluginConfigRequest) => Promise<void>;
  getPluginHealth: (pluginId: string) => Promise<any>;
  setPluginPending: (pluginId: string, pending: boolean) => void;
}

function mapBackendPluginToPluginInfo(plugin: any): PluginInfo {
  return {
    id: plugin.id,
    name: plugin.name,
    version: plugin.version,
    description: plugin.description,
    author: plugin.author,
    plugin_type: plugin.plugin_type || plugin.type || 'unknown',
    provides: plugin.provides || [],
    tags: plugin.tags || [],
    enabled: plugin.enabled ?? true,
    running: plugin.running ?? false,
    configured: plugin.configured ?? true,
    dependencies: plugin.dependencies || [],
  };
}

export const usePluginsStore = create<PluginsState>()(
  devtools(
    subscribeWithSelector(
      (set, get) => ({
        plugins: [],
        isLoading: false,
        error: null,
        pendingActions: {},

        loadPlugins: async () => {
          console.log('[PluginsStore] *** loadPlugins called ***');
          const state = get();
          console.log('[PluginsStore] Current state before:', { pluginsCount: state.plugins.length, isLoading: state.isLoading, error: state.error });
          set({ isLoading: true, error: null });
          try {
            console.log('[PluginsStore] Calling api.listPlugins()...');
            const response = await api.listPlugins();
            console.log('[PluginsStore] API response received, keys:', Object.keys(response || {}));
            console.log('[PluginsStore] Response has plugins array:', Array.isArray(response?.plugins), 'length:', response?.plugins?.length);
            // Map backend response to PluginInfo type
            const plugins = (response.plugins || []).map(mapBackendPluginToPluginInfo);
            console.log('[PluginsStore] Mapped plugins:', plugins.map((p: PluginInfo) => p.name));
            console.log('[PluginsStore] About to call set() with', plugins.length, 'plugins');
            set({ plugins, isLoading: false });
            console.log('[PluginsStore] State after set:', get().plugins.length, 'plugins in store');
          } catch (e) {
            console.error('[PluginsStore] Error loading plugins:', e);
            set({ error: e instanceof Error ? e.message : 'Failed to load plugins', isLoading: false });
          }
        },

        togglePlugin: async (pluginId: string, enabled: boolean) => {
          get().setPluginPending(pluginId, true);
          try {
            await api.configurePlugin(pluginId, { enabled });
            await get().loadPlugins(); // Refresh to get updated state
          } catch (e) {
            console.error('Failed to toggle plugin:', e);
            await get().loadPlugins(); // Revert on error
          } finally {
            get().setPluginPending(pluginId, false);
          }
        },

        startPlugin: async (pluginId: string) => {
          get().setPluginPending(pluginId, true);
          try {
            await api.startPlugin(pluginId);
            await get().loadPlugins();
          } catch (e) {
            console.error('Failed to start plugin:', e);
            await get().loadPlugins();
          } finally {
            get().setPluginPending(pluginId, false);
          }
        },

        stopPlugin: async (pluginId: string) => {
          get().setPluginPending(pluginId, true);
          try {
            await api.stopPlugin(pluginId);
            await get().loadPlugins();
          } catch (e) {
            console.error('Failed to stop plugin:', e);
            await get().loadPlugins();
          } finally {
            get().setPluginPending(pluginId, false);
          }
        },

        updatePluginConfig: async (pluginId: string, config: PluginConfigRequest) => {
          try {
            await api.configurePlugin(pluginId, config);
            await get().loadPlugins();
          } catch (e) {
            console.error('Failed to update plugin config:', e);
          }
        },

        getPluginHealth: async (pluginId: string) => {
          try {
            return await api.getPluginHealth(pluginId);
          } catch (e) {
            console.error('Failed to get plugin health:', e);
            return null;
          }
        },

        setPluginPending: (pluginId: string, pending: boolean) => {
          set((state) => ({
            pendingActions: { ...state.pendingActions, [pluginId]: pending },
          }));
        },
      })
    ),
    { name: 'PluginsStore' }
  )
);