'use client';

import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Plus,
  Search,
  Wrench,
  X,
  Download,
  Settings,
  ChevronUp,
  ChevronDown,
  Play,
  Pause,
  Package,
  Plug,
  RefreshCw,
  Bug,
  Database,
  AlertCircle,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { api } from '@/lib/api';
import { usePluginsStore } from '@/stores/pluginsStore';
import { toast } from '@/hooks/use-toast';

import {
  Card,
  CardContent,
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '@/components/ui/tabs';
import { Separator } from '@/components/ui/separator';

interface Plugin {
  id: string;
  name: string;
  version: string;
  description: string;
  author: string;
  plugin_type: string;
  provides: string[];
  tags: string[];
  enabled: boolean;
  running: boolean;
  configured: boolean;
  dependencies: string[];
}

export function PluginsPanel() {
  const {
    plugins,
    isLoading,
    error,
    pendingActions,
    loadPlugins,
    togglePlugin,
    startPlugin,
    stopPlugin,
    setPluginPending,
  } = usePluginsStore();
  const [searchQuery, setSearchQuery] = useState('');
  const [showInstallDialog, setShowInstallDialog] = useState(false);
  const [installMethod, setInstallMethod] = useState<'registry' | 'url' | 'file'>('registry');
  const [url, setUrl] = useState('');

  // Debug logging
  console.log('[PluginsPanel] Component render', { pluginsCount: plugins.length, isLoading, error });

  // Track client-side mount
  const [clientMounted, setClientMounted] = useState(false);
  const [clientTimestamp, setClientTimestamp] = useState<string>('');

  // Client-side mounted effect - call loadPlugins on mount
  useEffect(() => {
    console.log('[PluginsPanel] >>>>> CLIENT MOUNT EFFECT START >>>>>');
    setClientMounted(true);
    setClientTimestamp(new Date().toISOString());
    console.log('[PluginsPanel] clientMounted set to true');

    // Call loadPlugins
    console.log('[PluginsPanel] >>>>> Calling loadPlugins from mount effect... <<<<<');
    loadPlugins().then(() => {
      console.log('[PluginsPanel] >>>>> loadPlugins completed, store now has:', usePluginsStore.getState().plugins.length, 'plugins <<<<<');
    }).catch(err => {
      console.error('[PluginsPanel] >>>>> loadPlugins error:', err);
    });
    console.log('[PluginsPanel] >>>>> CLIENT MOUNT EFFECT END >>>>>');
  }, [loadPlugins]); // Run once on mount with loadPlugins in deps

  const filteredPlugins = useMemo(() =>
    plugins.filter(p =>
      p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      p.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
      p.tags.some(t => t.toLowerCase().includes(searchQuery.toLowerCase()))
    ),
    [plugins, searchQuery]
  );

  // Debug: Force re-render on plugins change
  const [, forceUpdate] = useState({});
  useEffect(() => {
    console.log('[PluginsPanel] PLUGINS STATE CHANGED, count:', plugins.length);
    forceUpdate(s => ({ ...s }));
  }, [plugins]);

  // Manual reload function for debugging
  const handleManualReload = async () => {
    console.log('[PluginsPanel] Manual reload clicked');
    try {
      const response = await fetch('/api/plugins');
      const data = await response.json();
      console.log('[PluginsPanel] Manual fetch result:', data.plugins?.length, 'plugins');
      // Also call store's loadPlugins
      await loadPlugins();
      console.log('[PluginsPanel] After loadPlugins, store has:', usePluginsStore.getState().plugins.length, 'plugins');
    } catch (e) {
      console.error('[PluginsPanel] Manual reload error:', e);
    }
  };

  return (
    <div className="h-full flex flex-col">
      <div className="p-4 border-b border-border flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h2 className="text-lg font-semibold">Plugins & Skills</h2>
          {/* DEBUG: Show client-side hydration status */}
          <span className={cn(
            "text-xs px-2 py-1 rounded",
            clientMounted ? "text-green-700 bg-green-100" : "text-yellow-700 bg-yellow-100"
          )}>
            {clientMounted ? 'Client JS Active' : 'SSR Only'}
          </span>
          {isLoading && (
            <motion.div
              initial={{ opacity: 0, scale: 0.5 }}
              animate={{ opacity: 1, scale: 1 }}
              className="flex items-center gap-1 text-xs text-muted-foreground"
            >
              <RefreshCw className="h-3 w-3 animate-spin" />
              <span>Loading...</span>
            </motion.div>
          )}
        </div>
        <div className="flex items-center gap-2">
          <Button size="sm" variant="outline" onClick={handleManualReload} disabled={isLoading}>
            <RefreshCw className="h-4 w-4 mr-1" /> Reload
          </Button>
          <Button size="sm" onClick={() => setShowInstallDialog(true)}>
            <Plus className="h-4 w-4 mr-1" /> Install Plugin
          </Button>
        </div>
      </div>

      <ScrollArea className="flex-1 p-4 space-y-4">
        {/* Debug panel - ALWAYS VISIBLE */}
        <div className="bg-slate-900 text-green-400 p-3 text-xs font-mono rounded mb-4 border border-slate-700">
          <div>DEBUG: plugins={plugins.length} isLoading={String(isLoading)} error={error || 'null'}</div>
          <div>Store ref: {usePluginsStore.getState().plugins.length} plugins</div>
          <div>Client mounted: {String(clientMounted)} {clientTimestamp ? 'at ' + clientTimestamp : ''}</div>
        </div>
        {error && (
          <Card className="border-destructive/50">
            <CardContent className="p-4 text-destructive flex items-center justify-between">
              <span>Failed to load plugins: {error}</span>
              <Button size="sm" variant="outline" onClick={loadPlugins}>
                <RefreshCw className="h-4 w-4 mr-1" /> Retry
              </Button>
            </CardContent>
          </Card>
        )}

        {filteredPlugins.map((plugin) => (
          <PluginCard
            key={plugin.id}
            plugin={plugin}
            onEnable={(enabled) => togglePlugin(plugin.id, enabled)}
            onStart={() => startPlugin(plugin.id)}
            onStop={() => stopPlugin(plugin.id)}
            onConfigure={() => toast({ title: `Configure ${plugin.name} - Settings dialog coming soon`, variant: 'default' })}
            onUninstall={() => toast({ title: `Uninstall ${plugin.name} - Not implemented yet`, variant: 'default' })}
            isPending={pendingActions[plugin.id]}
          />
        ))}

        {filteredPlugins.length === 0 && plugins.length > 0 && (
          <div className="text-center py-8 text-muted-foreground">
            <Search className="mx-auto h-8 w-8 mb-2 opacity-30" />
            <p>No plugins match "{searchQuery}"</p>
          </div>
        )}

        {plugins.length === 0 && !isLoading && !error && (
          <div className="text-center py-12 text-muted-foreground">
            <Wrench className="mx-auto h-12 w-12 mb-4 opacity-30" />
            <p>No plugins installed</p>
            <Button className="mt-4" size="sm" onClick={() => setShowInstallDialog(true)}>
              <Plus className="h-4 w-4 mr-1" /> Install Your First Plugin
            </Button>
          </div>
        )}

        {/* Install plugin dialog */}
        <AnimatePresence>
          {showInstallDialog && (
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
              onClick={() => setShowInstallDialog(false)}>
              <motion.div
                initial={{ opacity: 0, scale: 0.95, y: 20 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.95, y: 20 }}
                className="bg-card border border-border rounded-xl shadow-xl max-w-md w-full max-h-[80vh] overflow-hidden"
                onClick={(e) => e.stopPropagation()}>
                <div className="p-4 border-b border-border flex items-center justify-between">
                  <h3 className="font-semibold flex items-center gap-2">
                    <Download className="h-5 w-5" /> Install New Plugin
                  </h3>
                  <Button variant="ghost" size="icon" onClick={() => setShowInstallDialog(false)}>
                    <X className="h-4 w-4" />
                  </Button>
                </div>
                <div className="p-4 space-y-4 max-h-[60vh] overflow-y-auto">
                  <div className="space-y-2">
                    <Label>Installation Method</Label>
                    <Tabs defaultValue={installMethod} onValueChange={(value) => setInstallMethod(value as 'registry' | 'url' | 'file')} className="w-full">
                      <TabsList className="grid grid-cols-3">
                        <TabsTrigger value="registry" className="text-xs">Registry</TabsTrigger>
                        <TabsTrigger value="url" className="text-xs">From URL</TabsTrigger>
                        <TabsTrigger value="file" className="text-xs">From File</TabsTrigger>
                      </TabsList>
                      <TabsContent value="registry" className="focus-visible:outline-none space-y-2">
                        <Input
                          placeholder="Search plugins..."
                          value={searchQuery}
                          onChange={(e) => setSearchQuery(e.target.value)}
                        />
                        <div className="max-h-40 overflow-y-auto space-y-1">
                          {['my-custom-plugin', 'another-plugin', 'third-party-tool'].map((p) => (
                            <div key={p} className="flex items-center justify-between p-2 text-sm border border-border rounded hover:bg-muted">
                              <span>{p}</span>
                              <Button size="sm" variant="outline">Install</Button>
                            </div>
                          ))}
                        </div>
                      </TabsContent>
                      <TabsContent value="url" className="focus-visible:outline-none mt-2 space-y-2">
                        <Label>Plugin URL</Label>
                        <Input
                          placeholder="https://github.com/user/plugin or https://example.com/plugin.zip"
                          value={url}
                          onChange={(e) => setUrl(e.target.value)}
                        />
                        <p className="text-xs text-muted-foreground">Supports GitHub repos, direct zip downloads, and plugin manifests</p>
                      </TabsContent>
                      <TabsContent value="file" className="focus-visible:outline-none mt-2 space-y-2">
                        <Label>Plugin Package</Label>
                        <input type="file" accept=".zip,.tar.gz,.json" className="w-full" />
                        <p className="text-xs text-muted-foreground">Select a plugin package file (.zip, .tar.gz, or manifest.json)</p>
                      </TabsContent>
                    </Tabs>
                  </div>
                </div>
                <div className="p-4 border-t border-border flex justify-end gap-2">
                  <Button variant="ghost" onClick={() => setShowInstallDialog(false)}>Cancel</Button>
                  <Button onClick={() => setShowInstallDialog(false)}>Install</Button>
                </div>
              </motion.div>
            </div>
          )}
        </AnimatePresence>
      </ScrollArea>
    </div>
  );
}

function PluginCard({
  plugin,
  onEnable,
  onStart,
  onStop,
  onConfigure,
  onUninstall,
  isPending = false,
}: {
  plugin: Plugin;
  onEnable: (enabled: boolean) => void;
  onStart: () => void;
  onStop: () => void;
  onConfigure: () => void;
  onUninstall: () => void;
  isPending?: boolean;
}) {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <Card className="overflow-hidden">
      <CardContent className="p-0">
        <div className="p-4">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <h3 className="font-medium truncate">{plugin.name}</h3>
                <Badge variant={plugin.running ? 'success' : plugin.enabled ? 'default' : 'outline'} className="text-xs">
                  {plugin.running ? 'Running' : plugin.enabled ? 'Enabled' : 'Disabled'}
                </Badge>
                <Badge variant="outline" className="text-xs">v{plugin.version}</Badge>
              </div>
              <p className="text-sm text-muted-foreground mt-1 line-clamp-2">{plugin.description}</p>
              <div className="flex items-center gap-4 mt-2 text-xs text-muted-foreground">
                <span>by {plugin.author}</span>
                {plugin.plugin_type && <span>Type: {plugin.plugin_type}</span>}
                {plugin.dependencies.length > 0 && (
                  <span>Deps: {plugin.dependencies.join(', ')}</span>
                )}
              </div>
              <div className="flex flex-wrap gap-1 mt-2">
                {plugin.tags.slice(0, 5).map((tag) => (
                  <Badge key={tag} variant="outline" className="text-xs">{tag}</Badge>
                ))}
                {plugin.tags.length > 5 && (
                  <Badge variant="outline" className="text-xs">+{plugin.tags.length - 5} more</Badge>
                )}
              </div>
            </div>

            <div className="flex items-center gap-2 flex-shrink-0">
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setIsExpanded(!isExpanded)}
                disabled={isPending}
              >
                {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
              </Button>
              <Switch
                checked={plugin.enabled}
                onCheckedChange={onEnable}
                disabled={!plugin.enabled && plugin.running || isPending}
              />
              <div className={cn('w-2 h-2 rounded-full', plugin.running ? 'bg-green-500 animate-pulse' : 'bg-gray-400')} />
            </div>
          </div>

          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: isExpanded ? 1 : 0, height: isExpanded ? 'auto' : 0 }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden"
          >
            <div className="px-4 pb-4 pt-2 border-t border-border">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                <div className="space-y-2">
                  <Label>Dependencies</Label>
                  <div className="flex flex-wrap gap-1">
                    {plugin.dependencies.length > 0 ? (
                      plugin.dependencies.map((dep) => (
                        <Badge key={dep} variant="outline" className="text-xs">{dep}</Badge>
                      ))
                    ) : (
                      <span className="text-xs text-muted-foreground">None</span>
                    )}
                  </div>
                </div>
                <div className="space-y-2">
                  <Label>Provides</Label>
                  <div className="flex flex-wrap gap-1">
                    {plugin.provides.length > 0 ? (
                      plugin.provides.map((provide) => (
                        <Badge key={provide} variant="secondary" className="text-xs">{provide}</Badge>
                      ))
                    ) : (
                      <span className="text-xs text-muted-foreground">None</span>
                    )}
                  </div>
                </div>
              </div>

              <div className="space-y-2 mb-4">
                <Label>Status</Label>
                <div className="flex items-center gap-2 text-sm">
                  <span className={cn(
                    'px-2 py-1 rounded-full text-xs font-medium',
                    plugin.running ? 'bg-green-100 text-green-800' :
                    plugin.enabled ? 'bg-blue-100 text-blue-800' :
                    'bg-gray-100 text-gray-800'
                  )}>
                    {plugin.running ? '● Running' : plugin.enabled ? '● Ready' : '○ Disabled'}
                  </span>
                  {plugin.configured && (
                    <Badge variant="outline" className="text-xs">Configured</Badge>
                  )}
                  {!plugin.configured && plugin.enabled && (
                    <Badge variant="destructive" className="text-xs">Not Configured</Badge>
                  )}
                  {isPending && (
                    <span className="text-xs text-muted-foreground">
                      <RefreshCw className="h-3 w-3 animate-spin inline mr-1" /> Processing...
                    </span>
                  )}
                </div>
              </div>

              <Separator className="mb-4" />

              <div className="flex items-center justify-end gap-2">
                <Button variant="ghost" size="sm" onClick={onConfigure} disabled={!plugin.enabled || isPending}>
                  <Settings className="h-3 w-3 mr-1" /> Settings
                </Button>
                <Button variant="ghost" size="sm" onClick={onUninstall} disabled={plugin.running || isPending}>
                  <X className="h-3 w-3 mr-1" /> Uninstall
                </Button>
                {plugin.enabled && !plugin.running && (
                  <Button variant="default" size="sm" onClick={onStart} disabled={isPending} className="gap-1">
                    <Play className="h-3 w-3" /> Start
                  </Button>
                )}
                {plugin.running && (
                  <Button variant="outline" size="sm" onClick={onStop} disabled={isPending} className="gap-1">
                    <Pause className="h-3 w-3" /> Stop
                  </Button>
                )}
              </div>
            </div>
          </motion.div>
        </div>
      </CardContent>
    </Card>
  );
}