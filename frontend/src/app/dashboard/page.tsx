'use client';

import { ModuleGrid } from '@/components/runtime/ModuleCard';
import { useRuntimeStore } from '@/stores/runtimeStore';
import { useTimelineStore } from '@/stores/timelineStore';
import { useUIStore } from '@/stores/uiStore';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { useMemo, useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  Box, Activity, AlertCircle, Circle, Zap, Bot, GitBranch, Clock, List,
  Bell, HardDrive, Shield, Users, Mic, Eye, Video, ImageIcon, Link, Search, Brain,
  Terminal, Wrench, Database, Map, Server, FolderOpen, Wifi, MessageSquare,
  TrendingUp, TrendingDown, Clock as ClockIcon, Loader2, RefreshCw
} from 'lucide-react';

interface StatCardProps {
  label: string;
  value: number | string;
  icon: any;
  color: string;
  trend?: { value: number; label: string };
}

function StatCard({ label, value, icon: Icon, color, trend }: StatCardProps) {
  return (
    <Card className="h-full">
      <CardContent className="p-4 flex items-start justify-between h-full">
        <div>
          <p className="text-sm font-medium text-muted-foreground">{label}</p>
          <p className="text-3xl font-bold mt-1" style={{ color: `var(--${color})` }}>{value}</p>
          {trend && (
            <div className="flex items-center gap-1 mt-2 text-xs"
              style={{ color: trend.value >= 0 ? 'var(--green-500)' : 'var(--red-500)' }}>
              <TrendingUp className="h-3 w-3" />
              <span>{trend.value >= 0 ? '+' : ''}{trend.value}% {trend.label}</span>
            </div>
          )}
        </div>
        <div className="p-3 rounded-xl" style={{ backgroundColor: `var(--${color}-100)`, color: `var(--${color}-600)` }}>
          <Icon className="h-6 w-6" />
        </div>
      </CardContent>
    </Card>
  );
}

function SystemStatusCard({ status, uptime }: { status: string; uptime: string }) {
  const statusConfig = {
    connected: { label: 'Conectado', color: 'green', icon: Activity },
    connecting: { label: 'Conectando...', color: 'yellow', icon: Loader2 },
    disconnected: { label: 'Desconectado', color: 'gray', icon: Circle },
    error: { label: 'Erro', color: 'red', icon: AlertCircle },
  };

  const config = statusConfig[status as keyof typeof statusConfig] || statusConfig.disconnected;
  const Icon = config.icon;

  return (
    <Card className="h-full">
      <CardContent className="p-4 h-full">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Icon className="h-5 w-5" style={{ color: `var(--${config.color}-500)` }} />
            <span className="font-medium capitalize">{config.label}</span>
          </div>
          <Badge variant="outline" className="text-xs">{status}</Badge>
        </div>
        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-muted-foreground">Uptime</span>
            <span className="font-mono font-medium">{uptime}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Status da API</span>
            <span className="font-medium text-green-600">Operacional</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">WebSocket</span>
            <span className="font-medium" style={{ color: status === 'connected' ? 'var(--green-500)' : 'var(--red-500)' }}>
              {status === 'connected' ? 'Ativo' : 'Inativo'}
            </span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function QuickActions({ onNavigate }: { onNavigate: (tab: string) => void }) {
  const actions = [
    { label: 'Novo Chat', icon: MessageSquare, tab: 'chat', color: 'blue' },
    { label: 'Criar Workflow', icon: GitBranch, tab: 'workflow', color: 'purple' },
    { label: 'Ver Timeline', icon: ClockIcon, tab: 'timeline', color: 'orange' },
    { label: 'Módulos', icon: Box, tab: 'runtime', color: 'green' },
    { label: 'Debug', icon: Terminal, tab: 'debug', color: 'red' },
    { label: 'Configurações', icon: Shield, tab: 'settings', color: 'gray' },
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Ações Rápidas</CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        <div className="grid grid-cols-3 gap-0">
          {actions.map((action) => (
            <motion.button
              key={action.label}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => onNavigate(action.tab)}
              className="p-4 hover:bg-accent/50 transition-colors border-r border-b border-border last:border-r-0 flex flex-col items-center gap-2 text-left w-full"
            >
              <div className="p-2 rounded-lg" style={{ backgroundColor: `var(--${action.color}-100)`, color: `var(--${action.color}-600)` }}>
                <action.icon className="h-5 w-5" />
              </div>
              <span className="text-sm font-medium text-center">{action.label}</span>
            </motion.button>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function RecentActivity({ events, limit = 5 }: { events: any[]; limit?: number }) {
  const eventIcons: Record<string, any> = {
    TASK_STARTED: Zap,
    TASK_COMPLETED: Activity,
    TASK_FAILED: AlertCircle,
    MODULE_STARTED: Box,
    MODULE_STOPPED: Circle,
    MODULE_ERROR: AlertCircle,
    CONVERSATION_STARTED: MessageSquare,
    MESSAGE_RECEIVED: Bot,
    WORKFLOW_STARTED: GitBranch,
    WORKFLOW_COMPLETED: Activity,
    WORKFLOW_FAILED: AlertCircle,
  };

  const eventColors: Record<string, string> = {
    TASK_STARTED: 'blue',
    TASK_COMPLETED: 'green',
    TASK_FAILED: 'red',
    MODULE_STARTED: 'blue',
    MODULE_STOPPED: 'gray',
    MODULE_ERROR: 'red',
    CONVERSATION_STARTED: 'purple',
    MESSAGE_RECEIVED: 'blue',
    WORKFLOW_STARTED: 'purple',
    WORKFLOW_COMPLETED: 'green',
    WORKFLOW_FAILED: 'red',
  };

  const recentEvents = useMemo(() => events.slice(-limit).reverse(), [events, limit]);

  if (recentEvents.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Atividade Recente</CardTitle>
        </CardHeader>
        <CardContent className="py-8 text-center text-muted-foreground">
          <ClockIcon className="h-12 w-12 mx-auto mb-3 opacity-30" />
          <p className="text-sm">Nenhuma atividade ainda</p>
          <p className="text-xs mt-1">Eventos aparecerão aqui conforme o runtime processa tarefas</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="h-full">
      <CardHeader>
        <CardTitle className="text-base">Atividade Recente</CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        <ScrollArea className="h-[300px]">
          <div className="p-4 space-y-3">
            {recentEvents.map((event, idx) => {
              const Icon = eventIcons[event.event_type] || Activity;
              const color = eventColors[event.event_type] || 'blue';
              const time = new Date(event.timestamp).toLocaleTimeString('pt-BR', {
                hour: '2-digit', minute: '2-digit', second: '2-digit'
              });

              return (
                <motion.div
                  key={`${event.correlation_id}-${idx}`}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: idx * 0.05 }}
                  className="flex items-start gap-3 p-2 hover:bg-accent/50 rounded-lg transition-colors"
                >
                  <div className="p-1.5 rounded" style={{ backgroundColor: `var(--${color}-100)`, color: `var(--${color}-600)` }}>
                    <Icon className="h-4 w-4" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-xs font-medium truncate">{event.event_type.replace(/_/g, ' ')}</span>
                      <span className="text-xs text-muted-foreground font-mono flex-shrink-0">{time}</span>
                    </div>
                    <p className="text-xs text-muted-foreground truncate">
                      {event.source || 'system'} • {event.payload?.message || event.payload?.action || JSON.stringify(event.payload).slice(0, 80)}
                    </p>
                    {event.correlation_id && (
                      <span className="text-[10px] text-muted-foreground font-mono">
                        corr: {event.correlation_id.slice(0, 12)}...
                      </span>
                    )}
                  </div>
                </motion.div>
              );
            })}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}

function ModuleCategoryLegend() {
  const categories = [
    { key: 'core', label: 'Core', icon: Zap, color: 'blue' },
    { key: 'agent', label: 'Agent', icon: Bot, color: 'purple' },
    { key: 'orchestration', label: 'Orquestração', icon: GitBranch, color: 'green' },
    { key: 'infrastructure', label: 'Infra', icon: HardDrive, color: 'orange' },
    { key: 'ai', label: 'IA', icon: Brain, color: 'pink' },
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Legenda de Categorias</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex flex-wrap gap-3">
          {categories.map((cat) => (
            <div key={cat.key} className="flex items-center gap-2 px-3 py-1.5 rounded-full text-xs" style={{ backgroundColor: `var(--${cat.color}-50)`, color: `var(--${cat.color}-700)` }}>
              <cat.icon className="h-3 w-3" />
              {cat.label}
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function RefreshButton({ onRefresh, loading }: { onRefresh: () => void; loading?: boolean }) {
  return (
    <motion.button
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      onClick={onRefresh}
      disabled={loading}
      className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors disabled:opacity-50"
    >
      <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
      <span className="text-sm font-medium">Atualizar</span>
    </motion.button>
  );
}

export default function DashboardPage() {
  const { modules, health, setStatus } = useRuntimeStore();
  // Use the status hook that avoids hydration mismatch
  const [hydrated, setHydrated] = useState(false);
  const status = useRuntimeStore((s) => s.status);

  useEffect(() => {
    setHydrated(true);
  }, []);

  const { events } = useTimelineStore();
  const { setRightPanelTab, setRightPanelOpen } = useUIStore();

  const totalModules = useMemo(() => Object.keys(modules).length, [modules]);
  const runningModules = useMemo(() =>
    Object.values(modules).filter(m => m.state === 'RUNNING').length, [modules]);
  const errorModules = useMemo(() =>
    Object.values(modules).filter(m => m.state === 'ERROR').length, [modules]);
  const stoppedModules = useMemo(() =>
    Object.values(modules).filter(m => m.state === 'STOPPED').length, [modules]);

  const handleRefresh = async () => {
    setStatus('connecting');
    try {
      // Trigger a refresh of runtime data via the store
      const response = await fetch('/api/runtime/info');
      if (response.ok) {
        const data = await response.json();
        useRuntimeStore.getState().setInfo(data);
      }
      const healthResponse = await fetch('/api/runtime/health');
      if (healthResponse.ok) {
        const healthData = await healthResponse.json();
        useRuntimeStore.getState().setHealth(healthData);
      }
      setStatus('connected');
    } catch (e) {
      setStatus('error');
    }
  };

  const handleQuickAction = (tab: string) => {
    setRightPanelTab(tab as any);
    setRightPanelOpen(true);
  };

  const formatUptime = () => {
    const runtimeHealth = health as any;
    if (!runtimeHealth?.runtime?.uptime_seconds) return 'N/A';
    const secs = Math.floor(runtimeHealth.runtime.uptime_seconds);
    const h = Math.floor(secs / 3600);
    const m = Math.floor((secs % 3600) / 60);
    const s = secs % 60;
    return `${h}h ${m}m ${s}s`;
  };

  // During SSR, use 'disconnected' to avoid hydration mismatch
  const displayStatus = hydrated ? status : 'disconnected';

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="mb-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Dashboard do Runtime</h1>
          <p className="text-muted-foreground mt-1">
            Visão geral do status de todos os {totalModules} módulos do AIPENSA Runtime
          </p>
        </div>
        <RefreshButton onRefresh={handleRefresh} />
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <StatCard
          label="Total de Módulos"
          value={totalModules}
          icon={Box}
          color="blue"
        />
        <StatCard
          label="Em Execução"
          value={runningModules}
          icon={Activity}
          color="green"
        />
        <StatCard
          label="Com Erro"
          value={errorModules}
          icon={AlertCircle}
          color="red"
        />
        <StatCard
          label="Parados"
          value={stoppedModules}
          icon={Circle}
          color="gray"
        />
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-6">
        {/* Left Column - System Status + Quick Actions */}
        <div className="lg:col-span-1 space-y-4">
          <SystemStatusCard status={displayStatus} uptime={formatUptime()} />
          <QuickActions onNavigate={handleQuickAction} />
          <ModuleCategoryLegend />
        </div>

        {/* Right Column - Module Grid + Recent Activity */}
        <div className="lg:col-span-2 space-y-4">
          {/* Module Grid */}
          <Card className="flex-1 min-h-0 flex flex-col">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-base">Módulos do Runtime</CardTitle>
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <span className="flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full bg-green-500" />
                  Running: {runningModules}
                </span>
                <span className="flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full bg-red-500" />
                  Error: {errorModules}
                </span>
              </div>
            </CardHeader>
            <CardContent className="flex-1 p-0">
              <ScrollArea className="h-full">
                <div className="p-4">
                  {totalModules === 0 ? (
                    <div className="text-center py-12 text-muted-foreground">
                      <Box className="h-12 w-12 mx-auto mb-3 opacity-30" />
                      <p>Nenhum módulo carregado</p>
                      <p className="text-xs mt-1">Verifique se o runtime backend está rodando</p>
                    </div>
                  ) : (
                    <ModuleGrid
                      modules={modules}
                      healths={Object.fromEntries(
                        Object.entries(modules).map(([name, m]) => [name, m.health || null])
                      )}
                      selectedModule={null}
                      onSelect={() => {}}
                      onAction={async () => {}}
                    />
                  )}
                </div>
              </ScrollArea>
            </CardContent>
          </Card>

          {/* Recent Activity */}
          <RecentActivity events={events} limit={8} />
        </div>
      </div>

      {/* Footer - Key Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 border-t border-border pt-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Eventos na Timeline</p>
                <p className="text-2xl font-bold">{events.length}</p>
              </div>
              <ClockIcon className="h-8 w-8 text-muted-foreground/30" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Módulos IA Ativos</p>
                <p className="text-2xl font-bold">
                  {Object.values(modules).filter(m =>
                    ['voice', 'vision', 'video', 'image', 'embedding', 'rag', 'reasoning'].includes(m.name) &&
                    m.state === 'RUNNING'
                  ).length} / 7
                </p>
              </div>
              <Brain className="h-8 w-8 text-pink-500/30" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Orquestração</p>
                <p className="text-2xl font-bold">
                  {Object.values(modules).filter(m =>
                    ['workflow', 'scheduler', 'queue'].includes(m.name) &&
                    m.state === 'RUNNING'
                  ).length} / 3
                </p>
              </div>
              <GitBranch className="h-8 w-8 text-green-500/30" />
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}