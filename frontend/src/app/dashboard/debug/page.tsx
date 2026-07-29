'use client';

import { useDebugStore } from '@/stores/debugStore';
import { useRuntimeStore } from '@/stores/runtimeStore';
import { useUIStore } from '@/stores/uiStore';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Separator } from '@/components/ui/separator';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { formatTimestamp } from '@/lib/utils';
import { cn } from '@/lib/utils';
import {
  Trash2,
  Download,
  RotateCcw,
  Search,
  Filter,
  X,
  Eye,
  EyeOff,
  Copy,
  Terminal,
  Database,
  Activity,
  BarChart,
  History,
  Bug,
  Square,
  CheckCircle,
  AlertCircle,
  Info,
  RefreshCw,
  Server,
  Boxes,
  ChevronRight,
  ChevronUp,
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useState, useMemo, useEffect, useRef } from 'react';

const levelColors: Record<string, string> = {
  debug: 'text-gray-500 dark:text-gray-400 bg-gray-100 dark:bg-gray-800',
  info: 'text-blue-600 dark:text-blue-400 bg-blue-100 dark:bg-blue-900/30',
  warn: 'text-yellow-600 dark:text-yellow-400 bg-yellow-100 dark:bg-yellow-900/30',
  error: 'text-red-600 dark:text-red-400 bg-red-100 dark:bg-red-900/30',
};

const levelIcons: Record<string, any> = {
  debug: Info,
  info: CheckCircle,
  warn: AlertCircle,
  error: Square,
};

export default function DebugPage() {
  const { logs, addLog, clearLogs, snapshots, takeSnapshot, clearSnapshots, performanceMetrics } = useDebugStore();
  const { modules, health, info } = useRuntimeStore();
  const { rightPanelTab, setRightPanelTab } = useUIStore();
  const [filterLevel, setFilterLevel] = useState<string>('all');
  const [searchText, setSearchText] = useState('');
  const [autoScroll, setAutoScroll] = useState(true);
  const [selectedSnapshot, setSelectedSnapshot] = useState<string | null>(null);
  const logContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (autoScroll && logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [logs.length, autoScroll, logContainerRef]);

  const filteredLogs = useMemo(() => {
    return logs.filter((log) => {
      if (filterLevel !== 'all' && log.level !== filterLevel) return false;
      if (searchText && !log.message.toLowerCase().includes(searchText.toLowerCase()) &&
          !log.source.toLowerCase().includes(searchText.toLowerCase())) return false;
      return true;
    });
  }, [logs, filterLevel, searchText]);

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    addLog({ level: 'info', source: 'Debug', message: 'Copied to clipboard', timestamp: new Date().toISOString() });
  };

  return (
    <div className="h-full flex flex-col p-4 lg:p-6">
      <div className="mb-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-2xl font-bold">Debug Panel</h1>
            <p className="text-muted-foreground">Runtime diagnostics, logs, and state inspection</p>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="secondary" size="sm" onClick={takeSnapshot}>
              <RotateCcw className="h-4 w-4 mr-1" /> Snapshot
            </Button>
            <Button variant="secondary" size="sm" onClick={clearLogs}>
              <Trash2 className="h-4 w-4 mr-1" /> Clear Logs
            </Button>
          </div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-4">
          <StatCard label="Total Logs" value={logs.length} icon={Terminal} color="text-blue-500" />
          <StatCard label="Errors" value={logs.filter(l => l.level === 'error').length} icon={AlertCircle} color="text-red-500" />
          <StatCard label="Warnings" value={logs.filter(l => l.level === 'warn').length} icon={AlertCircle} color="text-yellow-500" />
          <StatCard label="Snapshots" value={snapshots.length} icon={Database} color="text-green-500" />
          <StatCard label="Modules" value={Object.keys(modules).length} icon={Activity} color="text-purple-500" />
        </div>
      </div>

      <div className="flex-1 flex overflow-hidden">
        <div className="flex-1 flex flex-col min-w-0 mr-4">
          <Tabs defaultValue="logs" className="flex-1 flex flex-col">
            <TabsList className="grid w-full grid-cols-3 h-8 bg-transparent">
              <TabsTrigger value="logs" className="text-xs">Logs ({filteredLogs.length})</TabsTrigger>
              <TabsTrigger value="performance" className="text-xs">Performance</TabsTrigger>
              <TabsTrigger value="state" className="text-xs">State Inspector</TabsTrigger>
            </TabsList>

            <TabsContent value="logs" className="flex-1 flex flex-col focus-visible:outline-none">
              <div className="flex flex-wrap gap-2 p-3 border-b border-border bg-muted/30">
                <div className="relative flex-1 min-w-[200px]">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input
                    placeholder="Filter logs..."
                    value={searchText}
                    onChange={(e) => setSearchText(e.target.value)}
                    className="pl-9"
                  />
                </div>

                <Select value={filterLevel} onValueChange={setFilterLevel}>
                  <SelectTrigger className="w-[140px]">
                    <SelectValue placeholder="All Levels" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Levels</SelectItem>
                    <SelectItem value="debug">Debug</SelectItem>
                    <SelectItem value="info">Info</SelectItem>
                    <SelectItem value="warn">Warn</SelectItem>
                    <SelectItem value="error">Error</SelectItem>
                  </SelectContent>
                </Select>

                <div className="flex items-center gap-2 ml-auto">
                  <label className="flex items-center gap-1.5 text-sm">
                    <input
                      type="checkbox"
                      checked={autoScroll}
                      onChange={(e) => setAutoScroll(e.target.checked)}
                      className="w-4 h-4 rounded border-border"
                    />
                    Auto-scroll
                  </label>
                  <Button variant="ghost" size="icon" onClick={() => copyToClipboard(JSON.stringify(filteredLogs, null, 2))} title="Copy All">
                    <Copy className="h-4 w-4" />
                  </Button>
                  <Button variant="ghost" size="icon" onClick={() => copyToClipboard(JSON.stringify({ logs: filteredLogs, timestamp: new Date().toISOString() }, null, 2))} title="Export">
                    <Download className="h-4 w-4" />
                  </Button>
                </div>
              </div>

              <ScrollArea className="flex-1" ref={logContainerRef}>
                <div className="p-2 space-y-1 font-mono text-xs" id="log-container">
                  {filteredLogs.length === 0 && (
                    <div className="text-center text-muted-foreground py-8">
                      <Terminal className="mx-auto h-12 w-12 text-muted-foreground/50" />
                      <p className="mt-4">No logs yet</p>
                      <p className="text-sm">Logs will appear here as events occur</p>
                    </div>
                  )}

                  <AnimatePresence mode="popLayout">
                    {filteredLogs.slice().reverse().map((log, idx) => {
                      const LevelIcon = levelIcons[log.level];
                      return (
                        <motion.div
                          key={`${log.timestamp}-${log.id || idx}`}
                          initial={{ opacity: 0, height: 0 }}
                          animate={{ opacity: 1, height: 'auto' }}
                          exit={{ opacity: 0, height: 0 }}
                          layout
                          className={cn(
                            'px-3 py-1.5 rounded border transition-colors',
                            'hover:bg-accent/50',
                            levelColors[log.level]
                          )}
                        >
                          <div className="flex items-start gap-2">
                            <LevelIcon className={cn('h-3.5 w-3.5 flex-shrink-0 mt-0.5', levelColors[log.level].replace('bg-', 'text-').replace('dark:bg-', 'dark:text-'))} />
                            <span className="text-muted-foreground font-mono text-[10px] w-20 flex-shrink-0">
                              {formatTimestamp(log.timestamp).split(' ')[1]}
                            </span>
                            <span className={cn('px-1.5 py-0.5 rounded text-[10px] font-medium flex-shrink-0', levelColors[log.level])}>
                              {log.level.toUpperCase()}
                            </span>
                            <span className="text-muted-foreground text-[11px] flex-shrink-0">{log.source}</span>
                            <span className="text-foreground flex-1 min-w-0 break-all">{log.message}</span>
                            {log.data && (
                              <button
                                onClick={(e) => { e.stopPropagation(); copyToClipboard(JSON.stringify(log.data, null, 2)); }}
                                className="p-1 rounded hover:bg-accent text-muted-foreground hover:text-foreground transition-colors flex-shrink-0"
                                title="Copy data"
                              >
                                <Copy className="h-3 w-3" />
                              </button>
                            )}
                          </div>
                          {log.data && (
                            <div className="mt-1 ml-7 pl-2 border-l border-border/50 text-muted-foreground text-[10px] font-mono">
                              <pre>{JSON.stringify(log.data, null, 2)}</pre>
                            </div>
                          )}
                        </motion.div>
                      );
                    })}
                  </AnimatePresence>
                </div>
              </ScrollArea>
            </TabsContent>

            <TabsContent value="performance" className="flex-1 focus-visible:outline-none">
              <ScrollArea className="h-full p-4 space-y-4">
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Activity className="h-4 w-4" />
                      Performance Metrics
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      <MetricCard label="Render Time" value={`${performanceMetrics.renderTime?.toFixed(2) || 0}ms`} icon={Activity} />
                      <MetricCard label="Memory" value={`${(performanceMetrics.memoryUsage || 0).toFixed(1)} MB`} icon={Database} />
                      <MetricCard label="Event Rate" value={`${performanceMetrics.eventsPerSecond || 0}/s`} icon={Activity} />
                    </div>

                    <Separator />

                    <div className="space-y-3">
                      <h4 className="font-medium text-sm text-muted-foreground">Render Timeline</h4>
                      <div className="h-32 bg-muted rounded p-2 relative overflow-hidden">
                        {(performanceMetrics.renderHistory || []).map((render, i) => {
                          const history = performanceMetrics.renderHistory || [];
                          const maxValue = history.length > 0 ? Math.max(...history, 1) : 1;
                          return (
                            <div
                              key={i}
                              className="absolute bottom-0 bg-primary/60 transition-all"
                              style={{
                                left: `${(i / Math.max(history.length, 1)) * 100}%`,
                                width: `${100 / Math.max(history.length, 1)}%`,
                                height: `${Math.min((render / maxValue) * 100, 100)}%`,
                              }}
                            />
                          );
                        })}
                      </div>
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <BarChart className="h-4 w-4" />
                      Module Performance
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2">
                      {Object.entries(modules).map(([name, module]) => (
                        <div key={name} className="flex items-center gap-3 p-2 bg-muted/50 rounded">
                          <div className="w-8 h-8 rounded flex items-center justify-center bg-primary/10">
                            <Activity className="h-4 w-4 text-primary" />
                          </div>
                          <div className="flex-1">
                            <div className="flex items-center justify-between text-sm">
                              <span className="font-medium">{name}</span>
                              <Badge variant={module.state === 'RUNNING' ? 'default' : 'outline'}>
                                {module.state}
                              </Badge>
                            </div>
                            <div className="h-1.5 bg-muted rounded-full overflow-hidden w-48">
                              <div
                                className="h-full bg-primary transition-all"
                                style={{ width: module.state === 'RUNNING' ? '100%' : module.state === 'ERROR' ? '0%' : '50%' }}
                              />
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </ScrollArea>
            </TabsContent>

            <TabsContent value="state" className="flex-1 focus-visible:outline-none">
              <ScrollArea className="h-full p-4 space-y-4">
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Server className="h-4 w-4" />
                      Runtime Information
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <pre className="text-xs bg-muted p-3 rounded max-h-60 overflow-auto">
                      {JSON.stringify(info || {}, null, 2)}
                    </pre>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Boxes className="h-4 w-4" />
                      Module States
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2 max-h-96 overflow-auto">
                      {Object.entries(modules).map(([name, module]) => (
                        <div key={name} className="flex items-center justify-between p-3 bg-muted/50 rounded">
                          <div className="flex items-center gap-3">
                            <div className={cn('w-2.5 h-2.5 rounded-full', module.state === 'RUNNING' && 'bg-green-500', module.state === 'ERROR' && 'bg-red-500', module.state === 'STOPPED' && 'bg-gray-400', module.state === 'STARTING' && 'bg-yellow-500 animate-pulse')} />
                            <span className="font-mono text-sm">{name}</span>
                          </div>
                          <Badge variant={module.state === 'RUNNING' ? 'default' : module.state === 'ERROR' ? 'destructive' : 'outline'}>
                            {module.state}
                          </Badge>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Activity className="h-4 w-4" />
                      Module Health Checks
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      {health?.modules && Object.entries(health.modules).map(([name, h]) => (
                        <Card key={name} className="p-3">
                          <div className="flex items-center justify-between mb-2">
                            <span className="font-medium text-sm">{name}</span>
                            <Badge variant={h.healthy ? 'default' : 'destructive'}>
                              {h.healthy ? 'Healthy' : 'Unhealthy'}
                            </Badge>
                          </div>
                          <pre className="text-xs bg-muted p-2 rounded max-h-32 overflow-auto">
                            {JSON.stringify(h.details || {}, null, 2)}
                          </pre>
                        </Card>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </ScrollArea>
            </TabsContent>
          </Tabs>
        </div>

        <div className="w-80 flex flex-col border-l border-border bg-card">
          <div className="p-3 border-b border-border flex items-center justify-between">
            <h3 className="font-medium">Snapshots ({snapshots.length})</h3>
            {snapshots.length > 0 && (
              <Button variant="ghost" size="icon" onClick={clearSnapshots} title="Clear All">
                <Trash2 className="h-4 w-4" />
              </Button>
            )}
          </div>

          <ScrollArea className="flex-1">
            <div className="p-3 space-y-2">
              {snapshots.length === 0 && (
                <div className="text-center text-muted-foreground py-8">
                  <History className="mx-auto h-12 w-12 text-muted-foreground/50" />
                  <p className="mt-4 text-sm">No snapshots yet</p>
                  <p className="text-xs">Click "Snapshot" to capture current state</p>
                </div>
              )}

              <AnimatePresence>
                {snapshots.slice().reverse().map((snap) => (
                  <motion.div
                    key={snap.id}
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -20 }}
                    className={cn(
                      'p-3 rounded-lg border transition-colors cursor-pointer',
                      selectedSnapshot === snap.id ? 'bg-primary/10 border-primary' : 'hover:bg-accent/50'
                    )}
                    onClick={() => setSelectedSnapshot(selectedSnapshot === snap.id ? null : snap.id)}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-mono text-xs font-medium">{snap.id}</span>
                      <Button variant="ghost" size="icon" onClick={(e) => { e.stopPropagation(); copyToClipboard(snap.id); }} title="Copy ID">
                        <Copy className="h-3 w-3" />
                      </Button>
                    </div>
                    <div className="text-xs text-muted-foreground mb-2">
                      {formatTimestamp(snap.timestamp)}
                    </div>
                    <div className="flex items-center gap-4 text-xs text-muted-foreground">
                      <span>Convs: {snap.conversationCount}</span>
                      <span>Workflows: {snap.activeWorkflows}</span>
                      <span>Modules: {Object.keys(snap.modules || {}).length}</span>
                    </div>

                    {selectedSnapshot === snap.id && (
                      <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        className="mt-3 pt-3 border-t border-border"
                      >
                        <div className="text-xs font-medium text-muted-foreground mb-1">Runtime Info</div>
                        <pre className="text-[10px] bg-muted p-2 rounded max-h-40 overflow-auto">
                          {JSON.stringify(snap.runtime, null, 2)}
                        </pre>
                        <div className="text-xs font-medium text-muted-foreground mt-2 mb-1">Module States</div>
                        <pre className="text-[10px] bg-muted p-2 rounded max-h-40 overflow-auto">
                          {JSON.stringify(snap.modules, null, 2)}
                        </pre>
                      </motion.div>
                    )}
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>
          </ScrollArea>
        </div>
      </div>
    </div>
  );
}

function StatCard({ label, value, icon: Icon, color }: { label: string; value: number; icon: any; color: string }) {
  return (
    <Card className="p-3">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-muted-foreground">{label}</p>
          <p className="text-2xl font-bold">{value}</p>
        </div>
        <Icon className={cn('h-6 w-6', color)} />
      </div>
    </Card>
  );
}

function MetricCard({ label, value, icon: Icon }: { label: string; value: string; icon: any }) {
  return (
    <div className="p-3 bg-muted/50 rounded-lg">
      <div className="flex items-center gap-2 mb-1">
        <Icon className="h-4 w-4 text-muted-foreground" />
        <span className="text-xs text-muted-foreground">{label}</span>
      </div>
      <div className="text-xl font-bold font-mono">{value}</div>
    </div>
  );
}

const performanceMetrics = {
  renderTime: 12.5,
  memoryUsage: 45.2,
  eventsPerSecond: 23,
  renderHistory: [12, 15, 11, 14, 13, 16, 12, 14, 13, 15, 14, 13] as number[],
};