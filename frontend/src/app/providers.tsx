// Providers wrapper for the app

'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactNode, useState, useEffect } from 'react';
import { ThemeProvider } from 'next-themes';
import { Toaster } from '@/components/ui/toaster';
import { wsClient } from '@/lib/websocket';
import { useRuntimeEvents } from '@/hooks/useRuntimeEvents';
import { useRuntimeInit } from '@/hooks/useRuntimeInit';
import { useSettingsStore } from '@/stores/settingsStore';
import { usePluginsStore } from '@/stores/pluginsStore';

export function Providers({ children }: { children: ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 5000,
            refetchOnWindowFocus: false,
            retry: 1,
          },
        },
      })
  );

  // Initialize runtime store and WebSocket connection
  useRuntimeInit();
  // Initialize WebSocket event subscriptions for chat/timeline
  useRuntimeEvents();

  // Initialize settings on app load
  const loadSettings = useSettingsStore((s) => s.loadSettings);
  const loadPlugins = usePluginsStore((s) => s.loadPlugins);
  console.log('[Providers] Render - loadPlugins:', typeof loadPlugins, 'loadSettings:', typeof loadSettings);

  // Client-side mounted effect - runs AFTER hydration
  useEffect(() => {
    console.log('[Providers] >>>>>>> IMMEDIATE EFFECT - Client side mounted! <<<<<<<');
    (window as any).__CLIENT_MOUNTED_EFFECT_RAN__ = true;

    // Force a setTimeout to ensure we're truly client-side
    setTimeout(() => {
      console.log('[Providers] >>>>>>> SETTIMEOUT CALLBACK - Definitely client side! <<<<<<<');
      (window as any).__CLIENT_TIMEOUT_RAN__ = true;

      // Now call loadPlugins
      console.log('[Providers] >>>>>>> Calling loadPlugins from setTimeout <<<<<<<');
      loadSettings();
      loadPlugins().then(() => {
        console.log('[Providers] >>>>>>> loadPlugins RESOLVED <<<<<<<');
      }).catch(e => {
        console.error('[Providers] >>>>>>> loadPlugins REJECTED:', e);
      });
    }, 0);
  }, []); // Run once on mount

  // Also load on client side after hydration (backup)
  useEffect(() => {
    console.log('[Providers] >>>>> BACKUP useEffect START <<<<<');
    console.log('[Providers] loadPlugins:', loadPlugins);
    console.log('[Providers] loadSettings:', loadSettings);
    loadSettings();
    console.log('[Providers] loadSettings() called');
    const pluginsPromise = loadPlugins();
    console.log('[Providers] loadPlugins() called, promise:', pluginsPromise);
    pluginsPromise.then(() => {
      console.log('[Providers] >>>>> loadPlugins() promise RESOLVED <<<<<');
    }).catch((e) => {
      console.error('[Providers] >>>>> loadPlugins() promise REJECTED:', e);
    });
    console.log('[Providers] >>>>> BACKUP useEffect END <<<<<');
    (window as any).__CLIENT_SIDE_RAN__ = true;
  }, [loadSettings, loadPlugins]);

  // Debug: Check store state
  const plugins = usePluginsStore((s) => s.plugins);
  const isLoading = usePluginsStore((s) => s.isLoading);
  const error = usePluginsStore((s) => s.error);

  useEffect(() => {
    console.log('[Providers] *** STORE SUBSCRIPTION FIRED ***', { pluginsCount: plugins.length, isLoading, error });
  }, [plugins, isLoading, error]);

  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
        {children}
        <Toaster />
      </ThemeProvider>
    </QueryClientProvider>
  );
}