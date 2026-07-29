'use client';

import { cn } from '@/lib/utils';
import { useUIStore, type RightPanelTab } from '@/stores/uiStore';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { WorkflowPanel } from '@/components/workflow/WorkflowPanel';
import { TimelinePanel } from '@/components/timeline/TimelinePanel';
import { DebugPanel } from '@/components/debug/DebugPanel';
import { BrowserPanel } from '@/components/browser/BrowserPanel';
import { SettingsPanel } from '@/components/settings/SettingsPanel';
import { PluginsPanel } from '@/components/plugins/PluginsPanel';
import { FileBrowser } from '@/components/workspace/FileBrowser';

export function RightPanel() {
  const { rightPanelTab, setRightPanelTab } = useUIStore();

  return (
    <div className="flex flex-col h-full" suppressHydrationWarning>
      {/* Tab header */}
      <div className="border-b border-border bg-muted/30">
        <Tabs value={rightPanelTab} onValueChange={(tab: string) => setRightPanelTab(tab as RightPanelTab)} className="w-full">
          <TabsList className="grid w-full grid-cols-7 h-8 bg-transparent p-0">
            <TabsTrigger value="workflow" className="text-xs">Workflow</TabsTrigger>
            <TabsTrigger value="timeline" className="text-xs">Timeline</TabsTrigger>
            <TabsTrigger value="debug" className="text-xs">Debug</TabsTrigger>
            <TabsTrigger value="browser" className="text-xs">Browser</TabsTrigger>
            <TabsTrigger value="workspace" className="text-xs">Workspace</TabsTrigger>
            <TabsTrigger value="settings" className="text-xs">Settings</TabsTrigger>
            <TabsTrigger value="plugins" className="text-xs">Plugins</TabsTrigger>
          </TabsList>
        </Tabs>
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-hidden">
        <Tabs value={rightPanelTab} onValueChange={(tab: string) => setRightPanelTab(tab as RightPanelTab)}>
          <TabsContent value="workflow" className="h-full focus-visible:outline-none">
            <WorkflowPanel />
          </TabsContent>
          <TabsContent value="timeline" className="h-full focus-visible:outline-none">
            <TimelinePanel />
          </TabsContent>
          <TabsContent value="debug" className="h-full focus-visible:outline-none">
            <DebugPanel />
          </TabsContent>
          <TabsContent value="browser" className="h-full focus-visible:outline-none">
            <BrowserPanel />
          </TabsContent>
          <TabsContent value="workspace" className="h-full focus-visible:outline-none">
            <FileBrowser />
          </TabsContent>
          <TabsContent value="settings" className="h-full focus-visible:outline-none">
            <SettingsPanel />
          </TabsContent>
          <TabsContent value="plugins" className="h-full focus-visible:outline-none">
            <PluginsPanel />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}