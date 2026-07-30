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
  console.log('[Providers] useRuntimeInit called');
  // Initialize WebSocket event subscriptions for chat/timeline
  useRuntimeEvents();
  console.log('[Providers] useRuntimeEvents called');

  // Initialize settings on app load
  const loadSettings = useSettingsStore((s) => s.loadSettings);
  useEffect(() => {
    console.log('[Providers] Loading settings on client mount');
    loadSettings();
  }, [loadSettings]);

  // Initialize plugins on app load
  const loadPlugins = usePluginsStore((s) => s.loadPlugins);
  useEffect(() => {
    console.log('[Providers] Loading plugins on client mount');
    loadPlugins();
  }, [loadPlugins]);

  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
        {children}
        <Toaster />
      </ThemeProvider>
    </QueryClientProvider>
  );
}