import { useEffect, useState, useRef } from 'react';
import { api } from '@/lib/api';
import { useRuntimeStore } from '@/stores/runtimeStore';
import { wsClient } from '@/lib/websocket';
import type { ModuleState, ModuleMetadata } from '@/types/runtime';

interface ModuleData {
  name: string;
  state: string;
  metadata: ModuleMetadata;
}

export function useRuntimeInit() {
  const { setInfo, setHealth, setModule, updateModuleState, updateModuleHealth, setStatus } = useRuntimeStore();

  // Track if we're on the client side (after hydration)
  const [isClient, setIsClient] = useState(false);
  const initializedRef = useRef(false);

  useEffect(() => {
    setIsClient(true);
  }, []);

  // Only run initialization on client side after hydration
  useEffect(() => {
    if (!isClient || initializedRef.current) {
      return;
    }
    initializedRef.current = true;

    let mounted = true;

    console.log('[useRuntimeInit] Client-side effect triggered, starting initialization...');

    const initRuntime = async () => {
      try {
        console.log('[useRuntimeInit] Setting status to connecting...');
        setStatus('connecting');

        // Fetch initial runtime info and health
        const [info, health] = await Promise.all([
          api.getRuntimeInfo(),
          api.getHealth(),
        ]);

        if (!mounted) return;

        setInfo(info);
        setHealth(health);

        // Initialize modules from runtime info
        const modulesRes = await api.listModules();
        if (!mounted) return;

        console.log('[useRuntimeInit] Modules loaded:', Object.keys(modulesRes.modules).length);

        for (const [name, moduleData] of Object.entries(modulesRes.modules)) {
          if (!mounted) return;
          const data = moduleData as ModuleData;
          // Convert lowercase backend state to uppercase frontend state
          const frontendState = data.state.toUpperCase() as ModuleState;
          setModule({
            name,
            state: frontendState,
            metadata: data.metadata,
            // health will be fetched below
          });

          // Fetch health for each module
          try {
            const health = await api.getModuleHealth(name);
            if (mounted) {
              updateModuleHealth(name, health);
            }
          } catch (e) {
            console.error(`Failed to fetch health for module ${name}:`, e);
          }
        }

        setStatus('connected');
      } catch (e) {
        console.error('Failed to initialize runtime:', e);
        if (mounted) setStatus('error');
      }
    };

    initRuntime();

    // Subscribe to WebSocket events for module state changes
    const unsubscribe = wsClient.subscribe((event) => {
      if (!mounted) return;

      // Handle module state events
      if (event.event_type.startsWith('MODULE_')) {
        const moduleName = event.payload.module_name;
        // Convert backend state to frontend uppercase
        if (event.event_type === 'MODULE_STARTED' || event.event_type === 'MODULE_RUNNING') {
          updateModuleState(moduleName, 'RUNNING');
        } else if (event.event_type === 'MODULE_STOPPED') {
          updateModuleState(moduleName, 'STOPPED');
        } else if (event.event_type === 'MODULE_ERROR') {
          updateModuleState(moduleName, 'ERROR');
        } else if (event.event_type === 'MODULE_INITIALIZED') {
          updateModuleState(moduleName, 'INITIALIZED');
        }
      }

      // Handle runtime events
      if (event.event_type === 'RUNTIME_STARTED') {
        setStatus('connected');
      } else if (event.event_type === 'RUNTIME_STOPPED' || event.event_type === 'RUNTIME_ERROR') {
        setStatus('error');
      }
    });

    wsClient.connect();

    return () => {
      mounted = false;
      unsubscribe();
    };
  }, [isClient, setInfo, setHealth, setModule, updateModuleState, updateModuleHealth, setStatus]);

  // Poll health periodically
  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const health = await api.getHealth();
        useRuntimeStore.getState().setHealth(health);

        // Update individual module health and state
        if (health.modules) {
          for (const [name, moduleHealth] of Object.entries(health.modules)) {
            useRuntimeStore.getState().updateModuleHealth(name, moduleHealth as any);
            // Convert backend lowercase state to frontend uppercase
            if (moduleHealth && typeof moduleHealth === 'object' && 'state' in moduleHealth) {
              const backendState = (moduleHealth as any).state || (moduleHealth as any).status;
              if (backendState) {
                useRuntimeStore.getState().updateModuleState(name, backendState.toUpperCase() as ModuleState);
              }
            }
          }
        }
      } catch (e) {
        console.error('Health check failed:', e);
      }
    }, 30000);

    return () => clearInterval(interval);
  }, [isClient]);
}