'use client';

import { cn } from '@/lib/utils';
import { motion, AnimatePresence } from 'framer-motion';
import { useUIStore } from '@/stores/uiStore';
import { Sidebar } from './Sidebar';
import { Header } from './Header';
import { RightPanel } from './RightPanel';
import { useEffect, useState } from 'react';

export function DashboardLayout({ children }: { children: React.ReactNode }) {
  const { sidebarOpen, rightPanelOpen } = useUIStore();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return (
      <div className="h-screen w-screen flex overflow-hidden bg-background">
        <div className="w-64 lg:w-72 bg-card border-r border-border h-screen" />
        <div className="flex-1 flex flex-col overflow-hidden">
          <div className="h-16 bg-card border-b border-border" />
          <main className="flex-1 overflow-auto p-4 lg:p-6" />
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen w-screen flex overflow-hidden bg-background">
      {/* Sidebar */}
      <Sidebar suppressHydrationWarning />

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        <Header suppressHydrationWarning />
        <main className="flex-1 overflow-auto p-4 lg:p-6">
          {children}
        </main>
      </div>

      {/* Right Panel - Slide over */}
      <AnimatePresence>
        {rightPanelOpen && (
          <motion.div
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 25, stiffness: 200 }}
            className="fixed lg:relative right-0 top-16 h-[calc(100vh-4rem)] w-full lg:w-96 border-l border-border bg-card z-30 flex flex-col"
          >
            <RightPanel />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Mobile sidebar overlay */}
      <AnimatePresence>
        {sidebarOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 z-30 lg:hidden"
            onClick={() => useUIStore.getState().setSidebarOpen(false)}
          />
        )}
      </AnimatePresence>
    </div>
  );
}