'use client';

import { useRuntimeStore } from '@/stores/runtimeStore';
import { useUIStore } from '@/stores/uiStore';
import { ModuleGrid } from '@/components/runtime/ModuleCard';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { useState, useMemo } from 'react';
import { Loader2, Server, Box, Bot, GitBranch, Clock, List, Bell, HardDrive, Shield, Users, Mic, Eye, Video, ImageIcon, Link, Search, Brain, Zap, Globe, Terminal, Wrench, Database, Map, FolderOpen, Wifi, MessageSquare, Activity, Settings, RefreshCw } from 'lucide-react';
import { cn } from '@/lib/utils';
import { motion } from 'framer-motion';

interface ModuleCategory {
  label: string;
  icon: any;
  modules: Array<{ id: string; label: string; icon: any; description: string }>;
}

const MODULE_CATEGORIES: Record<string, ModuleCategory> = {
  core: {
    label: 'Core Modules',
    icon: Zap,
    modules: [
      { id: 'local-browser', label: 'Browser', icon: Globe, description: 'Browser automation and web interaction' },
      { id: 'local-execution', label: 'Execution', icon: Terminal, description: 'Python code execution in sandboxed environments' },
      { id: 'local-tools', label: 'Tools', icon: Wrench, description: 'Tool registry and execution framework' },
      { id: 'local-memory', label: 'Memory', icon: Database, description: 'Vector and semantic memory storage' },
      { id: 'local-planning', label: 'Planning', icon: Map, description: 'Task planning and decomposition' },
      { id: 'local-mcp', label: 'MCP', icon: Server, description: 'Model Context Protocol integration' },
      { id: 'local-filesystem', label: 'File System', icon: FolderOpen, description: 'File system operations and management' },
      { id: 'local-network', label: 'Network', icon: Wifi, description: 'Network operations and HTTP client' },
    ],
  },
  agent: {
    label: 'Agent & Conversation',
    icon: Bot,
    modules: [
      { id: 'agent', label: 'Agent', icon: Bot, description: 'Autonomous agent orchestration' },
      { id: 'conversation', label: 'Conversation', icon: MessageSquare, description: 'Chat and conversation management' },
    ],
  },
  orchestration: {
    label: 'Orchestration',
    icon: GitBranch,
    modules: [
      { id: 'workflow', label: 'Workflow', icon: GitBranch, description: 'Workflow definition and execution' },
      { id: 'scheduler', label: 'Scheduler', icon: Clock, description: 'Scheduled task and cron management' },
      { id: 'queue', label: 'Queue', icon: List, description: 'Message queue and job processing' },
    ],
  },
  infrastructure: {
    label: 'Infrastructure',
    icon: HardDrive,
    modules: [
      { id: 'notification', label: 'Notifications', icon: Bell, description: 'Multi-channel notification delivery' },
      { id: 'storage', label: 'Storage', icon: HardDrive, description: 'Persistent storage abstraction' },
      { id: 'authentication', label: 'Authentication', icon: Shield, description: 'Auth and authorization services' },
      { id: 'workspace', label: 'Workspace', icon: Users, description: 'Multi-tenant workspace management' },
    ],
  },
  ai: {
    label: 'AI Capabilities',
    icon: Brain,
    modules: [
      { id: 'voice', label: 'Voice', icon: Mic, description: 'Speech recognition and synthesis' },
      { id: 'vision', label: 'Vision', icon: Eye, description: 'Image analysis and computer vision' },
      { id: 'video', label: 'Video', icon: Video, description: 'Video processing and analysis' },
      { id: 'image', label: 'Image', icon: ImageIcon, description: 'Image generation and manipulation' },
      { id: 'embedding', label: 'Embedding', icon: Link, description: 'Text and multimodal embeddings' },
      { id: 'rag', label: 'RAG', icon: Search, description: 'Retrieval-augmented generation' },
      { id: 'reasoning', label: 'Reasoning', icon: Brain, description: 'Advanced reasoning and chain-of-thought' },
    ],
  },
};

const MODULE_ICONS: Record<string, any> = {
  'local-browser': Globe,
  'local-execution': Terminal,
  'local-tools': Wrench,
  'local-memory': Database,
  'local-planning': Map,
  'local-mcp': Server,
  'local-filesystem': FolderOpen,
  'local-network': Wifi,
  'agent': Bot,
  'conversation': MessageSquare,
  'workflow': GitBranch,
  'scheduler': Clock,
  'queue': List,
  'notification': Bell,
  'storage': HardDrive,
  'authentication': Shield,
  'workspace': Users,
  'voice': Mic,
  'vision': Eye,
  'video': Video,
  'image': ImageIcon,
  'embedding': Link,
  'rag': Search,
  'reasoning': Brain,
};

const CATEGORY_COLORS: Record<string, string> = {
  core: 'blue',
  agent: 'purple',
  orchestration: 'green',
  infrastructure: 'orange',
  ai: 'pink',
};

const STATE_LABELS: Record<string, string> = {
  RUNNING: 'Running',
  STARTING: 'Starting...',
  STOPPING: 'Stopping...',
  STOPPED: 'Stopped',
  ERROR: 'Error',
  INITIALIZED: 'Initialized',
  UNINITIALIZED: 'Uninitialized',
};

const STATE_COLORS: Record<string, string> = {
  RUNNING: 'bg-green-500',
  STARTING: 'bg-yellow-500 animate-pulse',
  STOPPING: 'bg-orange-500',
  STOPPED: 'bg-gray-400',
  ERROR: 'bg-red-500',
  INITIALIZED: 'bg-blue-500',
  UNINITIALIZED: 'bg-slate-400',
};

export default function RuntimePage() {
  const { modules, status, health } = useRuntimeStore();
  const { setRightPanelOpen, setRightPanelTab } = useUIStore();
  const [refreshing, setRefreshing] = useState<string>('');
  const [selectedModule, setSelectedModule] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');

  const totalModules = useMemo(() => Object.keys(modules).length, [modules]);
  const runningModules = useMemo(() =>
    Object.values(modules).filter(m => m.state === 'RUNNING').length, [modules]);
  const errorModules = useMemo(() =>
    Object.values(modules).filter(m => m.state === 'ERROR').length, [modules]);
  const stoppedModules = useMemo(() =>
    Object.values(modules).filter(m => m.state === 'STOPPED').length, [modules]);

  const handleModuleAction = async (moduleId: string, action: 'start' | 'stop' | 'restart' | 'health') => {
    setRefreshing(moduleId);
    try {
      if (action === 'health') {
        setRightPanelTab('debug');
        setRightPanelOpen(true);
      } else {
        await fetch(`/api/modules/${moduleId}/execute`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ operation: action, params: {} }),
        });
        // Refresh health after action
        try {
          const resp = await fetch(`/api/modules/${moduleId}/health`);
          const data = await resp.json();
          useRuntimeStore.getState().updateModuleHealth(moduleId, data);
        } catch {}
      }
    } catch (e) {
      console.error(e);
    } finally {
      setRefreshing('');
    }
  };

  const getModuleInfo = (moduleId: string) => {
    for (const [, cat] of Object.entries(MODULE_CATEGORIES)) {
      const found = cat.modules.find(m => m.id === moduleId);
      if (found) return found;
    }
    return null;
  };

  return (
    <div className="h-full flex flex-col p-4 lg:p-6">
      {/* Header */}
      <div className="mb-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Runtime Dashboard</h1>
          <p className="text-muted-foreground">Monitor and manage all 19 runtime modules</p>
        </div>
        <div className="flex items-center gap-3 flex-wrap">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-muted border border-border">
            <span className={cn(
              'w-2 h-2 rounded-full',
              status === 'connected' && 'bg-green-500',
              status === 'connecting' && 'bg-yellow-500 animate-pulse',
              status === 'disconnected' && 'bg-gray-400',
              status === 'error' && 'bg-red-500',
            )} />
            <span className="text-sm font-medium capitalize">{status || 'disconnected'}</span>
          </div>
          <div className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-muted border border-border">
            <Server className="h-4 w-4" />
            <span className="text-sm font-mono text-muted-foreground">{runningModules}/{totalModules}</span>
          </div>
          <Button variant="outline" size="sm" onClick={() => window.location.reload()} disabled={refreshing !== null}>
            <RefreshCw className={cn('h-4 w-4 mr-1', refreshing && 'animate-spin')} />
            Refresh
          </Button>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        <StatCard label="Total Modules" value={totalModules} icon={Box} />
        <StatCard label="Running" value={runningModules} icon={Activity} color="text-green-500" />
        <StatCard label="Errors" value={errorModules} icon={Activity} color="text-red-500" />
        <StatCard label="Stopped" value={stoppedModules} icon={Activity} color="text-gray-500" />
      </div>

      {/* Module Grid */}
      <ScrollArea className="flex-1">
        <div className="space-y-6">
          {Object.entries(MODULE_CATEGORIES).map(([categoryKey, category]) => (
            <CategorySection
              key={categoryKey}
              categoryKey={categoryKey}
              category={category}
              modules={modules}
              selectedModule={selectedModule}
              onSelectModule={setSelectedModule}
              onModuleAction={handleModuleAction}
              refreshing={refreshing}
              viewMode={viewMode}
            />
          ))}
        </div>
      </ScrollArea>

      {/* Module Detail Drawer */}
      {selectedModule && (
        <ModuleDetailDrawer
          moduleId={selectedModule}
          moduleData={modules[selectedModule]}
          moduleInfo={getModuleInfo(selectedModule)!}
          onClose={() => setSelectedModule(null)}
          onAction={(action) => handleModuleAction(selectedModule, action)}
          refreshing={refreshing === selectedModule}
        />
      )}
    </div>
  );
}

function StatCard({ label, value, icon: Icon, color = '' }: { label: string; value: number; icon: any; color?: string }) {
  return (
    <Card className="h-20">
      <CardContent className="flex items-center justify-between p-4">
        <div>
          <p className="text-2xl font-bold" style={{ color: color || 'inherit' }}>{value}</p>
          <p className="text-xs text-muted-foreground">{label}</p>
        </div>
        <Icon className="h-8 w-8 text-muted-foreground/30" style={{ color: color || 'inherit' }} />
      </CardContent>
    </Card>
  );
}

function CategorySection({
  categoryKey,
  category,
  modules,
  selectedModule,
  onSelectModule,
  onModuleAction,
  refreshing,
  viewMode
}: {
  categoryKey: string;
  category: any;
  modules: Record<string, any>;
  selectedModule: string | null;
  onSelectModule: (id: string) => void;
  onModuleAction: (id: string, action: 'start' | 'stop' | 'restart' | 'health') => void;
  refreshing: string;
  viewMode: 'grid' | 'list';
}) {
  const categoryColor = CATEGORY_COLORS[categoryKey];
  const categoryModules = category.modules;

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 text-sm font-semibold text-muted-foreground uppercase tracking-wider">
        <category.icon className={cn('w-4 h-4', `text-${categoryColor}-500`)} />
        {category.label}
        <span className="px-2 py-0.5 text-xs bg-muted rounded-full text-muted-foreground">
          {categoryModules.length} modules
        </span>
      </div>

      {viewMode === 'grid' ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
          {categoryModules.map((moduleInfo: any) => {
            const moduleData = modules[moduleInfo.id];
            const state = moduleData?.state || 'UNINITIALIZED';
            const moduleHealth = moduleData?.health;
            const isSelected = selectedModule === moduleInfo.id;
            const Icon = MODULE_ICONS[moduleInfo.id] || moduleInfo.icon;

            return (
              <ModuleCard
                key={moduleInfo.id}
                moduleInfo={moduleInfo}
                moduleData={moduleData}
                state={state}
                health={moduleHealth}
                selected={isSelected}
                refreshing={refreshing === moduleInfo.id}
                categoryColor={categoryColor}
                onClick={() => onSelectModule(isSelected ? '' : moduleInfo.id)}
                onAction={(action) => onModuleAction(moduleInfo.id, action)}
              />
            );
          })}
        </div>
      ) : (
        <div className="border border-border rounded-lg overflow-hidden">
          {categoryModules.map((moduleInfo: any) => {
            const moduleData = modules[moduleInfo.id];
            const state = moduleData?.state || 'UNINITIALIZED';
            const moduleHealth = moduleData?.health;
            const isSelected = selectedModule === moduleInfo.id;
            const Icon = MODULE_ICONS[moduleInfo.id] || moduleInfo.icon;

            return (
              <ModuleListItem
                key={moduleInfo.id}
                moduleInfo={moduleInfo}
                moduleData={moduleData}
                state={state}
                health={moduleHealth}
                selected={isSelected}
                refreshing={refreshing === moduleInfo.id}
                categoryColor={categoryColor}
                onClick={() => onSelectModule(isSelected ? '' : moduleInfo.id)}
                onAction={(action) => onModuleAction(moduleInfo.id, action)}
              />
            );
          })}
        </div>
      )}
    </div>
  );
}

function ModuleCard({ moduleInfo, moduleData, state, health, selected, refreshing, categoryColor, onClick, onAction }: {
  moduleInfo: any;
  moduleData: any;
  state: string;
  health: any;
  selected: boolean;
  refreshing: boolean;
  categoryColor: string;
  onClick: () => void;
  onAction: (action: 'start' | 'stop' | 'restart' | 'health') => void;
}) {
  const Icon = MODULE_ICONS[moduleInfo.id] || moduleInfo.icon;

  return (
    <div
      onClick={onClick}
      className={cn(
        'p-4 rounded-xl border transition-all duration-200 cursor-pointer relative overflow-hidden',
        'bg-card hover:border-primary/50 hover:shadow-lg',
        selected && 'border-primary bg-primary/5 ring-1 ring-primary/20',
      )}
    >
      <div className="relative z-10">{moduleInfo.id}</div>

      <div className="flex items-start gap-3">
        <div className={cn(
          'w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0',
          `bg-${categoryColor}-100 dark:bg-${categoryColor}-900/30`
        )}>
          <Icon className={cn('h-5 w-5', `text-${categoryColor}-600 dark:text-${categoryColor}-400`)} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="font-medium truncate">{moduleInfo.label}</div>
          <div className="text-xs text-muted-foreground truncate">{moduleInfo.description}</div>
        </div>
        <div className="flex flex-col items-end gap-1">
          <span className={cn('w-2 h-2 rounded-full flex-shrink-0', STATE_COLORS[state] || 'bg-slate-400')} />
          <span className="text-xs text-muted-foreground capitalize hidden sm:inline">{STATE_LABELS[state] || state}</span>
        </div>
      </div>

      {/* Health bar */}
      <div className="absolute bottom-0 left-0 right-0 h-1 bg-muted" />
      <div className="absolute bottom-0 left-0 h-1 bg-primary transition-all duration-300" style={{
        width: `${health?.score ? health.score * 100 : (state === 'RUNNING' ? 100 : state === 'ERROR' ? 0 : 50)}%`
      }} />

      {/* Action buttons on hover */}
      <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity flex gap-1">
        <button
          onClick={(e) => { e.stopPropagation(); onAction('health'); }}
          className="p-1 rounded hover:bg-accent text-muted-foreground hover:text-foreground transition-colors"
          title="Health Check"
        >
          <Activity className="h-3.5 w-3.5" />
        </button>
        {state !== 'RUNNING' && state !== 'STARTING' && state !== 'STOPPING' && (
          <button
            onClick={(e) => { e.stopPropagation(); onAction('start'); }}
            disabled={refreshing}
            className="p-1 rounded hover:bg-green-500/10 text-green-500 transition-colors"
            title="Start"
          >
            {refreshing ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Loader2 className="h-3.5 w-3.5" />}
          </button>
        )}
        {state === 'RUNNING' && (
          <>
            <button
              onClick={(e) => { e.stopPropagation(); onAction('stop'); }}
              disabled={refreshing}
              className="p-1 rounded hover:bg-red-500/10 text-red-500 transition-colors"
              title="Stop"
            >
              {refreshing ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Loader2 className="h-3.5 w-3.5" />}
            </button>
            <button
              onClick={(e) => { e.stopPropagation(); onAction('restart'); }}
              disabled={refreshing}
              className="p-1 rounded hover:bg-blue-500/10 text-blue-500 transition-colors"
              title="Restart"
            >
              {refreshing ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Loader2 className="h-3.5 w-3.5" />}
            </button>
          </>
        )}
      </div>
    </div>
  );
}

function ModuleListItem({ moduleInfo, moduleData, state, health, selected, refreshing, categoryColor, onClick, onAction }: {
  moduleInfo: any;
  moduleData: any;
  state: string;
  health: any;
  selected: boolean;
  refreshing: boolean;
  categoryColor: string;
  onClick: () => void;
  onAction: (action: 'start' | 'stop' | 'restart' | 'health') => void;
}) {
  const Icon = MODULE_ICONS[moduleInfo.id] || moduleInfo.icon;

  return (
    <div
      onClick={onClick}
      className={cn(
        'px-4 py-3 border-b border-border/50 last:border-0 transition-colors cursor-pointer',
        'hover:bg-accent/50',
        selected && 'bg-primary/5 border-l-2 border-primary'
      )}
    >
      <div className="flex items-center gap-3">
        <div className={cn(
          'w-8 h-8 rounded flex items-center justify-center flex-shrink-0',
          `bg-${categoryColor}-100 dark:bg-${categoryColor}-900/30`
        )}>
          <Icon className={cn('h-4 w-4', `text-${categoryColor}-600 dark:text-${categoryColor}-400`)} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-medium truncate">{moduleInfo.label}</span>
            <span className="text-xs text-muted-foreground capitalize px-2 py-0.5 rounded bg-muted">
              {STATE_LABELS[state] || state}
            </span>
            <span className={cn('w-1.5 h-1.5 rounded-full', STATE_COLORS[state] || 'bg-slate-400')} />
          </div>
          <div className="text-xs text-muted-foreground truncate">{moduleInfo.description}</div>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-24">
            <div className="h-1.5 bg-muted rounded-full overflow-hidden">
              <div className="h-full bg-primary transition-all duration-500" style={{
                width: `${health?.score ? health.score * 100 : (state === 'RUNNING' ? 100 : state === 'ERROR' ? 0 : 50)}%`
              }} />
            </div>
          </div>
          <span className="text-xs font-mono text-muted-foreground w-10 text-right">
            {Math.round((health?.score || (state === 'RUNNING' ? 1 : state === 'ERROR' ? 0 : 0.5)) * 100)}%
          </span>
          <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
            <button
              onClick={(e) => { e.stopPropagation(); onAction('health'); }}
              className="p-1 rounded hover:bg-accent text-muted-foreground hover:text-foreground"
              title="Health Check"
            >
              <Activity className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function ModuleDetailDrawer({ moduleId, moduleData, moduleInfo, onClose, onAction, refreshing }: {
  moduleId: string;
  moduleData: any;
  moduleInfo: any;
  onClose: () => void;
  onAction: (action: 'start' | 'stop' | 'restart' | 'health') => void;
  refreshing: boolean;
}) {
  const state = moduleData?.state || 'UNINITIALIZED';
  const health = moduleData?.health;
  const metadata = moduleData?.metadata;

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <motion.div
        initial={{ y: '100%', opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        exit={{ y: '100%', opacity: 0 }}
        className="relative bg-card border border-border rounded-t-2xl sm:rounded-xl max-w-2xl w-full max-h-[80vh] overflow-hidden flex flex-col"
      >
        <div className="p-4 border-b border-border flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-lg bg-primary/10 flex items-center justify-center">
              <moduleInfo.icon className="h-6 w-6 text-primary" />
            </div>
            <div>
              <h3 className="font-semibold">{moduleInfo.label}</h3>
              <p className="text-sm text-muted-foreground">{moduleInfo.description}</p>
            </div>
          </div>
          <button onClick={onClose} className="p-1 rounded hover:bg-accent">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {/* Status */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Status</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">State</span>
                <Badge variant={state === 'RUNNING' ? 'default' : state === 'ERROR' ? 'destructive' : 'outline'}>
                  {state}
                </Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Health Score</span>
                <div className="flex items-center gap-2 w-48">
                  <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
                    <div className="h-full bg-primary transition-all duration-500" style={{
                      width: `${health?.score ? health.score * 100 : (state === 'RUNNING' ? 100 : state === 'ERROR' ? 0 : 50)}%`
                    }} />
                  </div>
                  <span className="text-xs font-mono text-muted-foreground w-10 text-right">
                    {Math.round((health?.score || (state === 'RUNNING' ? 1 : state === 'ERROR' ? 0 : 0.5)) * 100)}%
                  </span>
                </div>
              </div>
              {health && (
                <>
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">Health Status</span>
                    <Badge variant="outline" className="capitalize">{health.status || 'unknown'}</Badge>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">Last Check</span>
                    <span className="font-mono text-xs">{health.last_check ? new Date(health.last_check).toLocaleTimeString() : 'Never'}</span>
                  </div>
                  {health.issues && health.issues.length > 0 && (
                    <div className="space-y-1">
                      <div className="text-muted-foreground text-xs">Issues:</div>
                      {health.issues.map((issue: string, idx: number) => (
                        <Badge key={idx} variant="destructive" className="text-xs gap-1">
                          <X className="w-3 h-3" /> {issue}
                        </Badge>
                      ))}
                    </div>
                  )}
                </>
              )}
            </CardContent>
          </Card>

          {/* Actions */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Actions</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {state !== 'RUNNING' && state !== 'STARTING' && (
                <button
                  onClick={() => onAction('start')}
                  disabled={refreshing || state === 'STARTING'}
                  className="w-full btn-primary py-2"
                >
                  {refreshing && state !== 'RUNNING' ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Loader2 className="h-4 w-4 mr-2" />}
                  Start Module
                </button>
              )}
              {state === 'RUNNING' && (
                <div className="flex gap-2">
                  <button
                    onClick={() => onAction('stop')}
                    disabled={refreshing || state === 'STOPPING'}
                    className="flex-1 btn-destructive py-2"
                  >
                    {refreshing ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Loader2 className="h-4 w-4 mr-2" />}
                    Stop
                  </button>
                  <button
                    onClick={() => onAction('restart')}
                    disabled={refreshing}
                    className="flex-1 btn-secondary py-2"
                  >
                    {refreshing ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <RefreshCw className="h-4 w-4 mr-2" />}
                    Restart
                  </button>
                </div>
              )}
              <button
                onClick={() => onAction('health')}
                disabled={refreshing}
                className="w-full btn-outline py-2"
              >
                {refreshing ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Activity className="h-4 w-4 mr-2" />}
                Health Check
              </button>
            </CardContent>
          </Card>

          {/* Metadata */}
          {metadata && Object.keys(metadata).length > 0 && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base">Metadata</CardTitle>
              </CardHeader>
              <CardContent>
                <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
                  {Object.entries(metadata).map(([key, value]) => (
                    <div key={key} className="flex flex-col">
                      <dt className="text-muted-foreground capitalize">{key.replace(/_/g, ' ')}</dt>
                      <dd className="font-mono truncate text-right md:text-left">{String(value)}</dd>
                    </div>
                  ))}
                </dl>
              </CardContent>
            </Card>
          )}
        </div>
      </motion.div>
    </div>
  );
}

// Need to import Button types
import { Button } from '@/components/ui/button';
import { X } from 'lucide-react';