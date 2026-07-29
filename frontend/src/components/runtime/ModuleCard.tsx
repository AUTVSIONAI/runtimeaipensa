'use client';

import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Globe,
  Terminal,
  Wrench,
  Database,
  Map,
  Server,
  FolderOpen,
  Wifi,
  Box,
  Bot,
  MessageSquare,
  GitBranch,
  Clock,
  List,
  Bell,
  HardDrive,
  Shield,
  Users,
  Mic,
  Eye,
  Video,
  ImageIcon,
  Link,
  Search,
  Brain,
  Zap,
  Activity,
  Loader2,
  Play,
  RotateCcw,
  X,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { useState } from 'react';
import type { ModuleInfo, ModuleHealth, ModuleState } from '@/types/runtime';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { api } from '@/lib/api';

const MODULE_ICONS: Record<string, any> = {
  'local-browser': Globe,
  'local-execution': Terminal,
  'local-tools': Wrench,
  'local-memory': Database,
  'local-planning': Map,
  'local-mcp': Server,
  'local-filesystem': FolderOpen,
  'local-network': Wifi,
  'local-docker': Box,
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

const MODULE_CATEGORIES: Record<string, string> = {
  'local-browser': 'core',
  'local-execution': 'core',
  'local-tools': 'core',
  'local-memory': 'core',
  'local-planning': 'core',
  'local-mcp': 'core',
  'local-filesystem': 'core',
  'local-network': 'core',
  'local-docker': 'core',
  'agent': 'agent',
  'conversation': 'agent',
  'workflow': 'orchestration',
  'scheduler': 'orchestration',
  'queue': 'orchestration',
  'notification': 'infrastructure',
  'storage': 'infrastructure',
  'authentication': 'infrastructure',
  'workspace': 'infrastructure',
  'voice': 'ai',
  'vision': 'ai',
  'video': 'ai',
  'image': 'ai',
  'embedding': 'ai',
  'rag': 'ai',
  'reasoning': 'ai',
};

const CATEGORY_LABELS: Record<string, string> = {
  core: 'Core Modules',
  agent: 'Agent & Conversation',
  orchestration: 'Orchestration',
  infrastructure: 'Infrastructure',
  ai: 'AI Capabilities',
};

const CATEGORY_ICONS: Record<string, any> = {
  core: Zap,
  agent: Bot,
  orchestration: GitBranch,
  infrastructure: HardDrive,
  ai: Brain,
};

interface ModuleCardProps {
  module: ModuleInfo;
  health: ModuleHealth | null;
  isSelected: boolean;
  onSelect: (id: string) => void;
  onAction: (id: string, action: 'start' | 'stop' | 'restart' | 'health') => void;
}

function ModuleCard({ module, health, isSelected, onSelect, onAction }: ModuleCardProps) {
  const Icon = MODULE_ICONS[module.name] || Box;
  const [expanded, setExpanded] = useState(false);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const category = MODULE_CATEGORIES[module.name] || 'core';
  const state: ModuleState = module.state || 'UNINITIALIZED';
  const healthScore = health?.healthy !== undefined ? (health.healthy ? 1 : 0) : (state === 'RUNNING' ? 1 : 0);
  const healthStatus = health?.status || (health ? 'healthy' : 'unknown');

  const stateColors = {
    RUNNING: 'bg-green-500',
    STARTING: 'bg-yellow-500 animate-pulse',
    STOPPING: 'bg-orange-500',
    STOPPED: 'bg-gray-400',
    ERROR: 'bg-red-500',
    INITIALIZED: 'bg-blue-500',
    UNINITIALIZED: 'bg-slate-400',
  };

  const stateLabels: Record<string, string> = {
    RUNNING: 'Running',
    STARTING: 'Starting',
    STOPPING: 'Stopping',
    STOPPED: 'Stopped',
    ERROR: 'Error',
    INITIALIZED: 'Initialized',
    UNINITIALIZED: 'Uninitialized',
  };

  const healthColors: Record<string, string> = {
    healthy: 'bg-green-500',
    degraded: 'bg-yellow-500',
    unhealthy: 'bg-red-500',
    unknown: 'bg-gray-400',
  };

  type ModuleAction = 'start' | 'stop' | 'restart' | 'health';

const handleAction = async (action: ModuleAction) => {
    setActionLoading(action);
    try {
      await onAction(module.name, action);
    } finally {
      setActionLoading(null);
    }
  };

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn(
        'group relative transition-all duration-200',
        'bg-card border border-border rounded-xl overflow-hidden',
        isSelected && 'ring-2 ring-primary border-transparent shadow-lg shadow-primary/10'
      )}
    >
      {/* Header */}
      <div className={cn(
        'p-4 flex items-start gap-3 cursor-pointer',
        'hover:bg-accent/50 transition-colors',
        isSelected && 'bg-primary/5'
      )} onClick={() => onSelect(module.name)}>
        <div
          className={cn(
            'w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0',
            'bg-gradient-to-br from-blue-500 to-purple-600'
          )}
        >
          <Icon className="w-5 h-5 text-white" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-2">
            <h4 className="font-medium truncate">{module.label || module.metadata?.name || module.name}</h4>
            <button
              onClick={(e) => { e.stopPropagation(); setExpanded(!expanded); }}
              className="p-1 rounded hover:bg-accent text-muted-foreground transition-colors flex-shrink-0"
              aria-label={expanded ? 'Collapse' : 'Expand'}
            >
              {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            </button>
          </div>
          <p className="text-sm text-muted-foreground truncate mt-0.5">
            {module.metadata?.description || 'No description'}
          </p>
          <div className="flex items-center gap-2 mt-2">
            <span
              className={cn(
                'w-2 h-2 rounded-full flex-shrink-0',
                stateColors[state as keyof typeof stateColors] || 'bg-slate-400'
              )}
              title={stateLabels[state] || state}
            />
            <span className="text-xs font-medium text-muted-foreground capitalize">
              {stateLabels[state] || state}
            </span>
            <span className="w-1 h-1 rounded-full flex-shrink-0" style={{ backgroundColor: healthColors[healthStatus] }} title={healthStatus} />
            <span className="text-xs text-muted-foreground capitalize">{healthStatus}</span>
            <span className="text-xs text-muted-foreground" style={{ width: '60px' }}>
              <div className="h-1.5 bg-muted rounded-full overflow-hidden">
                <div
                  className="h-full bg-primary transition-all duration-500"
                  style={{ width: `${Math.round(healthScore * 100)}%` }}
                />
              </div>
            </span>
            <span className="text-xs font-mono text-muted-foreground">{Math.round(healthScore * 100)}%</span>
          </div>
        </div>
      </div>

      {/* Expanded content */}
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2, ease: 'easeInOut' }}
            className="overflow-hidden border-t border-border bg-muted/30"
          >
            <div className="p-4 space-y-4">
              {/* Metadata */}
              {module.metadata && Object.keys(module.metadata).length > 0 && (
                <div className="space-y-2 text-sm">
                  <div className="font-medium text-muted-foreground uppercase tracking-wider">Metadata</div>
                  <ScrollArea className="max-h-32">
                    <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
                      {Object.entries(module.metadata).map(([key, value]) => (
                        <div key={key} className="flex flex-col">
                          <dt className="text-muted-foreground capitalize">{key.replace(/_/g, ' ')}</dt>
                          <dd className="font-mono truncate text-right md:text-left">{String(value)}</dd>
                        </div>
                      ))}
                    </dl>
                  </ScrollArea>
                </div>
              )}

              {/* Health details */}
              {health && (
                <div className="space-y-2">
                  <div className="font-medium text-muted-foreground uppercase tracking-wider">Health Details</div>
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div className="p-2 bg-muted rounded">
                      <div className="text-muted-foreground">Status</div>
                      <Badge variant="outline" className="w-full capitalize">{healthStatus}</Badge>
                    </div>
                    <div className="p-2 bg-muted rounded">
                      <div className="text-muted-foreground">Healthy</div>
                      <div className="font-mono font-medium">{health.healthy ? 'Yes' : 'No'}</div>
                    </div>
                    <div className="p-2 bg-muted rounded">
                      <div className="text-muted-foreground">Module</div>
                      <div className="font-mono truncate">{health.module}</div>
                    </div>
                    <div className="p-2 bg-muted rounded">
                      <div className="text-muted-foreground">Details</div>
                      <div className="font-mono truncate">{Object.keys(health.details || {}).length} items</div>
                    </div>
                  </div>
                </div>
              )}

              {/* Actions */}
              <Separator />
              <div className="flex flex-wrap gap-2">
                {state !== 'RUNNING' && state !== 'STARTING' && (
                  <Button
                    size="sm"
                    variant="default"
                    onClick={(e) => { e.stopPropagation(); handleAction('start'); }}
                    disabled={actionLoading === 'start'}
                    className="flex-1 min-w-[120px]"
                  >
                    {actionLoading === 'start' ? (
                      <Loader2 className="h-3.5 w-3.5 mr-1 animate-spin" />
                    ) : (
                      <Play className="h-3.5 w-3.5 mr-1" />
                    )}
                    Start
                  </Button>
                )}
                {state === 'RUNNING' && (
                  <>
                    <Button
                      size="sm"
                      variant="destructive"
                      onClick={(e) => { e.stopPropagation(); handleAction('stop'); }}
                      disabled={actionLoading === 'stop'}
                      className="flex-1 min-w-[120px]"
                    >
                      {actionLoading === 'stop' ? (
                        <Loader2 className="h-3.5 w-3.5 mr-1 animate-spin" />
                      ) : (
                        <X className="h-3.5 w-3.5 mr-1" />
                      )}
                      Stop
                    </Button>
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={(e) => { e.stopPropagation(); handleAction('restart'); }}
                      disabled={actionLoading === 'restart'}
                      className="flex-1 min-w-[120px]"
                    >
                      {actionLoading === 'restart' ? (
                        <Loader2 className="h-3.5 w-3.5 mr-1 animate-spin" />
                      ) : (
                        <RotateCcw className="h-3.5 w-3.5 mr-1" />
                      )}
                      Restart
                    </Button>
                  </>
                )}
                <Button
                  size="sm"
                  variant="outline"
                  onClick={(e) => { e.stopPropagation(); handleAction('health'); }}
                  disabled={actionLoading === 'health'}
                  className="flex-1 min-w-[120px]"
                >
                  {actionLoading === 'health' ? (
                    <Loader2 className="h-3.5 w-3.5 mr-1 animate-spin" />
                  ) : (
                    <Activity className="h-3.5 w-3.5 mr-1" />
                  )}
                  Health Check
                </Button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

interface ModuleGridProps {
  modules: Record<string, ModuleInfo>;
  healths: Record<string, ModuleHealth | null>;
  selectedModule: string | null;
  onSelect: (id: string) => void;
  onAction: (id: string, action: 'start' | 'stop' | 'restart' | 'health') => void;
}

export function ModuleGrid({ modules, healths, selectedModule, onSelect, onAction }: ModuleGridProps) {
  const moduleEntries = Object.entries(modules);
  const categories = ['core', 'agent', 'orchestration', 'infrastructure', 'ai'];

  return (
    <div className="space-y-6">
      {categories.map((category) => {
        const categoryModules = moduleEntries.filter(([name]) => MODULE_CATEGORIES[name] === category);
        if (categoryModules.length === 0) return null;

        return (
          <div key={category} className="space-y-3">
            <div className="flex items-center gap-2 text-sm font-semibold text-muted-foreground uppercase tracking-wider">
              {(() => {
                const Icon = CATEGORY_ICONS[category];
                return <Icon className="w-4 h-4" />;
              })()}
              {CATEGORY_LABELS[category]}
              <span className="px-2 py-0.5 text-xs bg-muted rounded-full text-muted-foreground">
                {categoryModules.length}
              </span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
              {categoryModules.map(([name, module]) => (
                <ModuleCard
                  key={name}
                  module={{ ...module, name }}
                  health={healths[name] || null}
                  isSelected={selectedModule === name}
                  onSelect={onSelect}
                  onAction={onAction}
                />
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// Need to import the icons properly