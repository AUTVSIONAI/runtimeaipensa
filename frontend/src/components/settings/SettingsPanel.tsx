'use client';

import { cn } from '@/lib/utils';
import { useUIStore } from '@/stores/uiStore';
import { useSettingsStore } from '@/stores/settingsStore';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Separator } from '@/components/ui/separator';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Save, Globe, Key, Bell, Palette, Database, Network, Shield, Wrench, Trash2, Download, Play, Pause, Settings, X, Plus, ChevronUp, ChevronDown, Moon, Sun, Monitor, Laptop, Smartphone, RefreshCw, Copy, AlertTriangle } from 'lucide-react';
import { useState, useEffect } from 'react';
import { api } from '@/lib/api';
import { toast } from '@/hooks/use-toast';

export function SettingsPanel() {
  const { theme, setTheme, sidebarOpen, setSidebarOpen, rightPanelOpen, setRightPanelOpen } = useUIStore();
  const {
    settings,
    isLoading,
    isSaving,
    lastSaved,
    error,
    loadSettings,
    saveSettings,
    updateSetting,
    resetSettings,
    exportBackup,
    importBackup,
    clearCache
  } = useSettingsStore();

  const [apiUrl, setApiUrl] = useState('');
  const [wsUrl, setWsUrl] = useState('');
  const [notificationsEnabled, setNotificationsEnabled] = useState(true);
  const [autoScroll, setAutoScroll] = useState(true);
  const [compactMode, setCompactMode] = useState(false);
  const [animationsEnabled, setAnimationsEnabled] = useState(true);
  const [soundEnabled, setSoundEnabled] = useState(false);
  const [desktopNotificationsEnabled, setDesktopNotificationsEnabled] = useState(false);
  const [debugMode, setDebugMode] = useState(false);
  const [performanceMonitoring, setPerformanceMonitoring] = useState(true);
  const [eventPersistence, setEventPersistence] = useState(true);
  const [wsAutoReconnect, setWsAutoReconnect] = useState(true);
  const [logLevel, setLogLevel] = useState('info');
  const [maxEvents, setMaxEvents] = useState(10000);
  const [notificationTypes, setNotificationTypes] = useState({
    errors: true,
    warnings: true,
    info: true,
    debug: false,
  });
  const [accentColor, setAccentColor] = useState('blue');
  const [saved, setSaved] = useState(false);

  // Load settings on mount
  useEffect(() => {
    loadSettings();
  }, [loadSettings]);

  // Sync with loaded settings
  useEffect(() => {
    if (settings && !isLoading) {
      if (settings.settings?.ui) {
        setTheme(settings.settings.ui.theme || 'system');
        setApiUrl(settings.settings.ui.api_url || '');
        setWsUrl(settings.settings.ui.ws_url || '');
        setNotificationsEnabled(settings.settings.ui.notifications_enabled ?? true);
        setAutoScroll(settings.settings.ui.auto_scroll ?? true);
        setCompactMode(settings.settings.ui.compact_mode ?? false);
        setAnimationsEnabled(settings.settings.ui.animations_enabled ?? true);
        setSoundEnabled(settings.settings.ui.sound_enabled ?? false);
        setDesktopNotificationsEnabled(settings.settings.ui.desktop_notifications_enabled ?? false);
        setDebugMode(settings.settings.ui.debug_mode ?? false);
        setPerformanceMonitoring(settings.settings.ui.performance_monitoring ?? true);
        setEventPersistence(settings.settings.ui.event_persistence ?? true);
        setWsAutoReconnect(settings.settings.ui.ws_auto_reconnect ?? true);
        setLogLevel(settings.settings.ui.log_level || 'info');
        setMaxEvents(settings.settings.ui.max_events || 10000);
        setAccentColor(settings.settings.ui.accent_color || 'blue');
        if (settings.settings.ui.notification_types) {
          setNotificationTypes(settings.settings.ui.notification_types);
        }
      }
    }
  }, [settings, isLoading, setTheme]);

  const handleSave = async () => {
    const uiSettings = {
      theme,
      api_url: apiUrl,
      ws_url: wsUrl,
      notifications_enabled: notificationsEnabled,
      auto_scroll: autoScroll,
      compact_mode: compactMode,
      animations_enabled: animationsEnabled,
      sound_enabled: soundEnabled,
      desktop_notifications_enabled: desktopNotificationsEnabled,
      debug_mode: debugMode,
      performance_monitoring: performanceMonitoring,
      event_persistence: eventPersistence,
      ws_auto_reconnect: wsAutoReconnect,
      log_level: logLevel,
      max_events: maxEvents,
      accent_color: accentColor,
      notification_types: notificationTypes,
    };

    const success = await saveSettings(uiSettings);
    if (success) {
      setSaved(true);
      toast({ title: 'Settings saved', variant: 'default' });
      setTimeout(() => setSaved(false), 2000);
    } else {
      toast({ title: 'Failed to save settings', variant: 'destructive' });
    }
  };

  const handleTestConnection = async () => {
    try {
      await fetch(`${apiUrl}/api/runtime/health`);
      toast({ title: 'Connection successful!', variant: 'default' });
    } catch {
      toast({ title: 'Connection failed', variant: 'destructive' });
    }
  };

  const handleCopyConfig = () => {
    if (settings?.settings?.runtime) {
      navigator.clipboard.writeText(JSON.stringify(settings.settings.runtime, null, 2));
      toast({ title: 'Config copied to clipboard', variant: 'default' });
    }
  };

  const handleExportBackup = async () => {
    try {
      const backup = await exportBackup();
      const blob = new Blob([JSON.stringify(backup.data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `aipensa-backup-${new Date().toISOString().split('T')[0]}.json`;
      a.click();
      URL.revokeObjectURL(url);
      toast({ title: 'Backup exported successfully', variant: 'default' });
    } catch (e) {
      toast({ title: 'Failed to export backup', variant: 'destructive' });
    }
  };

  const handleImportBackup = async (file: File) => {
    try {
      const text = await file.text();
      const data = JSON.parse(text);
      const success = await importBackup({ data, overwrite: true });
      if (success) {
        toast({ title: 'Backup imported successfully', variant: 'default' });
        loadSettings(); // Reload
      } else {
        toast({ title: 'Failed to import backup', variant: 'destructive' });
      }
    } catch (e) {
      toast({ title: 'Invalid backup file', variant: 'destructive' });
    }
  };

  const handleClearCache = async () => {
    if (!confirm('Clear all cached data? This cannot be undone.')) return;
    try {
      await clearCache();
      toast({ title: 'Cache cleared successfully', variant: 'default' });
    } catch (e) {
      toast({ title: 'Failed to clear cache', variant: 'destructive' });
    }
  };

  const handleResetSettings = async () => {
    if (!confirm('Reset all settings to defaults? This cannot be undone.')) return;
    try {
      await resetSettings();
      toast({ title: 'Settings reset to defaults', variant: 'default' });
    } catch (e) {
      toast({ title: 'Failed to reset settings', variant: 'destructive' });
    }
  };

  return (
    <div className="h-full flex flex-col">
      <div className="p-4 border-b border-border">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">Settings</h2>
          <div className="flex items-center gap-2">
            {lastSaved && (
              <span className="text-xs text-muted-foreground">
                Saved {new Date(lastSaved).toLocaleTimeString()}
              </span>
            )}
            <Button onClick={handleSave} disabled={isSaving} size="sm">
              <Save className="h-4 w-4 mr-2" />
              {isSaving ? 'Saving...' : saved ? 'Saved!' : 'Save Changes'}
            </Button>
          </div>
        </div>
      </div>

      <ScrollArea className="flex-1 p-4 space-y-6">
        {error && (
          <Card className="border-destructive/50 bg-destructive/5">
            <CardContent className="p-4 text-destructive flex items-center justify-between">
              <span>Error: {error}</span>
              <Button size="sm" variant="outline" onClick={loadSettings}>
                <RefreshCw className="h-4 w-4 mr-1" /> Retry
              </Button>
            </CardContent>
          </Card>
        )}

        <Tabs defaultValue="general" className="w-full">
          <TabsList className="grid w-full grid-cols-6 h-8">
            <TabsTrigger value="general" className="text-xs">General</TabsTrigger>
            <TabsTrigger value="appearance" className="text-xs">Appearance</TabsTrigger>
            <TabsTrigger value="connection" className="text-xs">Connection</TabsTrigger>
            <TabsTrigger value="notifications" className="text-xs">Notifications</TabsTrigger>
            <TabsTrigger value="advanced" className="text-xs">Advanced</TabsTrigger>
            <TabsTrigger value="data" className="text-xs">Data</TabsTrigger>
          </TabsList>

          {/* General */}
          <TabsContent value="general" className="mt-4 space-y-6 focus-visible:outline-none">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2"><Globe className="h-4 w-4" /> General</CardTitle>
                <CardDescription>Basic application settings</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label>Default Conversation Title</Label>
                  <Input placeholder="New Conversation" />
                </div>
                <div className="space-y-2">
                  <Label>Default System Prompt</Label>
                  <Textarea placeholder="You are a helpful assistant..." rows={3} />
                </div>
                <div className="flex items-center justify-between">
                  <div>
                    <Label>Auto-scroll to new messages</Label>
                    <p className="text-sm text-muted-foreground">Automatically scroll to bottom when new messages arrive</p>
                  </div>
                  <Switch checked={autoScroll} onCheckedChange={setAutoScroll} />
                </div>
                <div className="flex items-center justify-between">
                  <div>
                    <Label>Compact Mode</Label>
                    <p className="text-sm text-muted-foreground">Reduce spacing for more content density</p>
                  </div>
                  <Switch checked={compactMode} onCheckedChange={setCompactMode} />
                </div>
                <div className="flex items-center justify-between">
                  <div>
                    <Label>Show Module Status in Sidebar</Label>
                    <p className="text-sm text-muted-foreground">Display module health indicators in navigation</p>
                  </div>
                  <Switch defaultChecked={true} />
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Appearance */}
          <TabsContent value="appearance" className="mt-4 space-y-6 focus-visible:outline-none">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2"><Palette className="h-4 w-4" /> Appearance</CardTitle>
                <CardDescription>Customize how the application looks</CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="space-y-4">
                  <Label>Theme</Label>
                  <div className="grid grid-cols-3 gap-3">
                    {(['light', 'dark', 'system'] as const).map((t) => (
                      <button
                        key={t}
                        onClick={() => setTheme(t)}
                        className={cn(
                          'p-4 rounded-lg border-2 transition-all flex flex-col items-center gap-2',
                          theme === t
                            ? 'border-primary bg-primary/10'
                            : 'border-border hover:border-primary/50'
                        )}
                      >
                        <div className="flex items-center gap-2">
                          {t === 'light' && <Sun className="h-5 w-5" />}
                          {t === 'dark' && <Moon className="h-5 w-5" />}
                          {t === 'system' && <Monitor className="h-5 w-5" />}
                        </div>
                        <div className="font-medium capitalize text-sm">{t}</div>
                        <div className="text-xs text-muted-foreground text-center">
                          {t === 'light' && 'Light mode'}
                          {t === 'dark' && 'Dark mode'}
                          {t === 'system' && 'Follow system'}
                        </div>
                      </button>
                    ))}
                  </div>
                </div>

                <Separator />

                <div className="space-y-4">
                  <Label>Accent Color</Label>
                  <div className="flex flex-wrap gap-2">
                    {['blue', 'purple', 'green', 'orange', 'red', 'pink', 'teal', 'indigo'].map((color) => (
                      <button
                        key={color}
                        onClick={() => setAccentColor(color)}
                        className={cn(
                          'w-10 h-10 rounded-lg border-2 transition-all',
                          `bg-${color}-500`,
                          accentColor === color ? 'ring-2 ring-offset-2 ring-primary' : 'hover:scale-110'
                        )}
                        style={{
                          boxShadow: accentColor === color ? '0 0 0 2px transparent' : undefined,
                        }}
                        title={color}
                      />
                    ))}
                  </div>
                </div>

                <div className="space-y-4">
                  <Label>Animations</Label>
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium">Enable Animations</p>
                      <p className="text-sm text-muted-foreground">Transitions, motion effects, and micro-interactions</p>
                    </div>
                    <Switch checked={animationsEnabled} onCheckedChange={setAnimationsEnabled} />
                  </div>
                </div>

                <div className="space-y-4">
                  <Label>Layout Density</Label>
                  <div className="grid grid-cols-3 gap-3">
                    {(['comfortable', 'cozy', 'compact'] as const).map((density) => (
                      <button
                        key={density}
                        onClick={() => setCompactMode(density === 'compact')}
                        className={cn(
                          'p-4 rounded-lg border-2 transition-all text-center',
                          (compactMode && density === 'compact') || (!compactMode && density === 'comfortable')
                            ? 'border-primary bg-primary/10'
                            : 'border-border hover:border-primary/50'
                        )}
                      >
                        <div className="font-medium capitalize text-sm">{density}</div>
                        <div className="text-xs text-muted-foreground mt-1">
                          {density === 'comfortable' && 'More spacing'}
                          {density === 'cozy' && 'Balanced'}
                          {density === 'compact' && 'Maximum density'}
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Connection */}
          <TabsContent value="connection" className="mt-4 space-y-6 focus-visible:outline-none">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2"><Network className="h-4 w-4" /> Connection</CardTitle>
                <CardDescription>Configure API and WebSocket endpoints</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label>API Base URL</Label>
                  <Input
                    value={apiUrl}
                    onChange={(e) => setApiUrl(e.target.value)}
                    placeholder="http://localhost:8000"
                  />
                  <p className="text-xs text-muted-foreground">REST API endpoint for the AIPENSA Runtime</p>
                </div>
                <div className="space-y-2">
                  <Label>WebSocket URL</Label>
                  <Input
                    value={wsUrl}
                    onChange={(e) => setWsUrl(e.target.value)}
                    placeholder="ws://localhost:8000/ws/events"
                  />
                  <p className="text-xs text-muted-foreground">Real-time EventBus streaming endpoint</p>
                </div>
                <div className="pt-4 border-t border-border flex gap-2">
                  <Button variant="outline" size="sm" onClick={() => { setApiUrl('http://localhost:8000'); setWsUrl('ws://localhost:8000/ws/events'); }}>
                    Reset to Defaults
                  </Button>
                  <Button variant="outline" size="sm" onClick={handleTestConnection}>
                    Test Connection
                  </Button>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2"><Shield className="h-4 w-4" /> Authentication</CardTitle>
                <CardDescription>API keys and authentication settings</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label>OpenAI API Key</Label>
                  <Input type="password" placeholder="sk-..." />
                  <p className="text-xs text-muted-foreground">Used for LLM completions and embeddings</p>
                </div>
                <div className="space-y-2">
                  <Label>Anthropic API Key</Label>
                  <Input type="password" placeholder="sk-ant-..." />
                  <p className="text-xs text-muted-foreground">Used for Claude models</p>
                </div>
                <div className="space-y-2">
                  <Label>Custom Headers (JSON)</Label>
                  <Textarea placeholder='{"Authorization": "Bearer token"}' rows={3} />
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Notifications */}
          <TabsContent value="notifications" className="mt-4 space-y-6 focus-visible:outline-none">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2"><Bell className="h-4 w-4" /> Notifications</CardTitle>
                <CardDescription>Control how you receive notifications</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <Label>Enable Notifications</Label>
                    <p className="text-sm text-muted-foreground">Show toast notifications for events</p>
                  </div>
                  <Switch checked={notificationsEnabled} onCheckedChange={setNotificationsEnabled} />
                </div>
                <div className="flex items-center justify-between">
                  <div>
                    <Label>Sound</Label>
                    <p className="text-sm text-muted-foreground">Play sound for notifications</p>
                  </div>
                  <Switch checked={soundEnabled} onCheckedChange={setSoundEnabled} />
                </div>
                <div className="flex items-center justify-between">
                  <div>
                    <Label>Desktop Notifications</Label>
                    <p className="text-sm text-muted-foreground">Request permission for system notifications</p>
                  </div>
                  <Switch checked={desktopNotificationsEnabled} onCheckedChange={setDesktopNotificationsEnabled} />
                </div>
                <Separator />
                <Label>Notification Types</Label>
                <div className="space-y-2">
                  {[
                    { id: 'errors', label: 'Errors & Failures', desc: 'Runtime errors, task failures, module crashes' },
                    { id: 'warnings', label: 'Warnings', desc: 'Degraded performance, deprecated features' },
                    { id: 'info', label: 'Info & Success', desc: 'Task completion, module startup, deployments' },
                    { id: 'debug', label: 'Debug Events', desc: 'Detailed event logs, state changes' },
                  ].map((n) => (
                    <div key={n.id} className="flex items-center justify-between">
                      <div>
                        <p className="font-medium">{n.label}</p>
                        <p className="text-sm text-muted-foreground">{n.desc}</p>
                      </div>
                      <Switch
                        checked={notificationTypes[n.id as keyof typeof notificationTypes] ?? true}
                        onCheckedChange={(checked) => setNotificationTypes(prev => ({ ...prev, [n.id]: checked }))}
                      />
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Advanced */}
          <TabsContent value="advanced" className="mt-4 space-y-6 focus-visible:outline-none">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2"><Wrench className="h-4 w-4" /> Advanced</CardTitle>
                <CardDescription>Developer and power user settings</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <Label>Debug Mode</Label>
                    <p className="text-sm text-muted-foreground">Enable verbose logging and debug panels</p>
                  </div>
                  <Switch checked={debugMode} onCheckedChange={setDebugMode} />
                </div>
                <div className="flex items-center justify-between">
                  <div>
                    <Label>Performance Monitoring</Label>
                    <p className="text-sm text-muted-foreground">Track render times, memory usage, and network latency</p>
                  </div>
                  <Switch checked={performanceMonitoring} onCheckedChange={setPerformanceMonitoring} />
                </div>
                <div className="flex items-center justify-between">
                  <div>
                    <Label>Event Persistence</Label>
                    <p className="text-sm text-muted-foreground">Persist event history to localStorage</p>
                  </div>
                  <Switch checked={eventPersistence} onCheckedChange={setEventPersistence} />
                </div>
                <div className="flex items-center justify-between">
                  <div>
                    <Label>WebSocket Auto-Reconnect</Label>
                    <p className="text-sm text-muted-foreground">Automatically reconnect on connection loss</p>
                  </div>
                  <Switch checked={wsAutoReconnect} onCheckedChange={setWsAutoReconnect} />
                </div>
                <Separator />
                <div className="space-y-2">
                  <Label>Log Level</Label>
                  <select
                    value={logLevel}
                    onChange={(e) => setLogLevel(e.target.value)}
                    className="w-full max-w-md px-3 py-2 border border-input rounded-md bg-background text-sm"
                  >
                    <option value="error">Error</option>
                    <option value="warn">Warn</option>
                    <option value="info">Info</option>
                    <option value="debug">Debug</option>
                    <option value="trace">Trace</option>
                  </select>
                </div>
                <div className="space-y-2">
                  <Label>Max Events in Memory</Label>
                  <Input type="number" value={maxEvents} onChange={(e) => setMaxEvents(parseInt(e.target.value) || 10000)} min="100" max="100000" />
                </div>
              </CardContent>
            </Card>

            <Card className="border-destructive/50 bg-destructive/5">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-destructive"><Trash2 className="h-4 w-4" /> Danger Zone</CardTitle>
                <CardDescription>Irreversible actions</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium">Clear All Data</p>
                    <p className="text-sm text-muted-foreground">Remove all conversations, settings, and cached data</p>
                  </div>
                  <Button variant="destructive" size="sm" onClick={handleClearCache}>
                    Clear Data
                  </Button>
                </div>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium">Reset to Defaults</p>
                    <p className="text-sm text-muted-foreground">Restore all settings to factory defaults</p>
                  </div>
                  <Button variant="outline" size="sm" onClick={handleResetSettings}>
                    Reset Settings
                  </Button>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Data */}
          <TabsContent value="data" className="mt-4 space-y-6 focus-visible:outline-none">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2"><Database className="h-4 w-4" /> Data Management</CardTitle>
                <CardDescription>Manage stored data and exports</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2 border border-border rounded-lg p-4">
                    <Label>Conversations</Label>
                    <p className="text-sm text-muted-foreground">12 conversations, 342 messages</p>
                    <div className="flex gap-2">
                      <Button variant="outline" size="sm">Export</Button>
                      <Button variant="destructive" size="sm">Clear</Button>
                    </div>
                  </div>
                  <div className="space-y-2 border border-border rounded-lg p-4">
                    <Label>Event History</Label>
                    <p className="text-sm text-muted-foreground">8,432 events stored</p>
                    <div className="flex gap-2">
                      <Button variant="outline" size="sm">Export</Button>
                      <Button variant="destructive" size="sm">Clear</Button>
                    </div>
                  </div>
                  <div className="space-y-2 border border-border rounded-lg p-4">
                    <Label>Module States</Label>
                    <p className="text-sm text-muted-foreground">19 modules configured</p>
                    <Button variant="outline" size="sm">Export Config</Button>
                  </div>
                  <div className="space-y-2 border border-border rounded-lg p-4">
                    <Label>Cache</Label>
                    <p className="text-sm text-muted-foreground">24.5 MB cached</p>
                    <Button variant="destructive" size="sm" onClick={handleClearCache}>Clear Cache</Button>
                  </div>
                </div>
                <Separator />
                <div className="space-y-2">
                  <Label>Full Backup</Label>
                  <p className="text-sm text-muted-foreground">Create a complete backup of all data and settings</p>
                  <div className="flex gap-2">
                    <Button onClick={handleExportBackup}>
                      <Download className="h-4 w-4 mr-2" /> Create Backup
                    </Button>
                    <Button variant="outline" onClick={handleCopyConfig}>
                      <Copy className="h-4 w-4 mr-2" /> Copy Runtime Config
                    </Button>
                  </div>
                </div>
                <div className="space-y-2">
                  <Label>Restore Backup</Label>
                  <p className="text-sm text-muted-foreground">Restore from a previously created backup file</p>
                  <input
                    type="file"
                    accept=".json,.backup"
                    className="w-full max-w-md"
                    onChange={(e) => e.target.files?.[0] && handleImportBackup(e.target.files[0])}
                  />
                </div>
              </CardContent>
            </Card>

            {/* Runtime Config Viewer */}
            {settings?.settings?.runtime && (
              <Card className="border-info/50 bg-info/5">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2"><Settings className="h-4 w-4" /> Runtime Configuration (Read-Only)</CardTitle>
                  <CardDescription>Current runtime.toml configuration loaded from backend</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="relative">
                    <pre className="bg-muted p-4 rounded-lg max-h-96 overflow-auto text-xs font-mono">
                      {JSON.stringify(settings.settings.runtime, null, 2)}
                    </pre>
                    <div className="absolute top-2 right-2">
                      <Button variant="ghost" size="icon" onClick={handleCopyConfig}>
                        <Copy className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}
          </TabsContent>
        </Tabs>
      </ScrollArea>
    </div>
  );
}