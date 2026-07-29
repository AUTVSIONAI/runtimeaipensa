'use client';

import { cn } from '@/lib/utils';
import { useUIStore } from '@/stores/uiStore';
import {
  GitBranch,
  Clock,
  Bug,
  Globe,
  Settings,
  Plug,
  X,
} from 'lucide-react';

type RightPanelTab = 'workflow' | 'timeline' | 'debug' | 'browser' | 'settings' | 'plugins';

interface RightPanelTabsProps {
  activeTab: RightPanelTab;
}

export function RightPanelTabs({ activeTab }: RightPanelTabsProps) {
  const { setRightPanelTab, rightPanelOpen, toggleRightPanel } = useUIStore();

  const tabs: { id: RightPanelTab; label: string; icon: any }[] = [
    { id: 'workflow', label: 'Workflow', icon: GitBranch },
    { id: 'timeline', label: 'Timeline', icon: Clock },
    { id: 'debug', label: 'Debug', icon: Bug },
    { id: 'browser', label: 'Browser', icon: Globe },
    { id: 'settings', label: 'Settings', icon: Settings },
    { id: 'plugins', label: 'Plugins', icon: Plug },
  ];

  return (
    <div className="flex border-b border-border px-2">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          onClick={() => setRightPanelTab(tab.id)}
          className={cn(
            'flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-t-lg transition-colors',
            activeTab === tab.id
              ? 'bg-background text-foreground border-b-2 border-primary'
              : 'text-muted-foreground hover:text-foreground hover:bg-muted'
          )}
        >
          <tab.icon className="h-4 w-4" />
          <span>{tab.label}</span>
        </button>
      ))}
      <div className="flex-1" />
      <button
        onClick={toggleRightPanel}
        className="p-2 rounded-r-lg hover:bg-muted transition-colors"
        title="Close panel"
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  );
}