'use client';

import { useState, useCallback, useEffect } from 'react';
import { cn } from '@/lib/utils';
import { api } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { motion, AnimatePresence } from 'framer-motion';
import { useUIStore } from '@/stores/uiStore';
import {
  Globe, Play, CircleStop, RotateCcw, RefreshCw, Search, ChevronLeft, ChevronRight,
  Home, MousePointer, Keyboard, ArrowDown, ArrowUp, Type, Image, Minimize, Maximize,
  Trash2, Plus, Settings, Monitor, Zap, X, ChevronDown, ChevronUp
} from 'lucide-react';

interface BrowserSession {
  session_id: string;
  url: string;
  title: string;
  created_at: string;
}

interface BrowserState {
  url: string;
  title: string;
  tabs: Array<Record<string, any>>;
  pixels_above: number;
  pixels_below: number;
  viewport_height: number;
  interactive_elements: string;
  screenshot_base64: string | null;
  error: string | null;
}

interface BrowserAction {
  action: string;
  params: Record<string, any>;
}

export default function BrowserPage() {
  const { rightPanelTab, setRightPanelTab, rightPanelOpen, setRightPanelOpen } = useUIStore();
  const [sessions, setSessions] = useState<BrowserSession[]>([]);
  const [activeSession, setActiveSession] = useState<string | null>(null);
  const [browserState, setBrowserState] = useState<BrowserState | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [newSessionUrl, setNewSessionUrl] = useState('https://example.com');
  const [actionLog, setActionLog] = useState<Array<{ action: string; params: any; result: any; timestamp: string }>>([]);
  const [screenshotScale, setScreenshotScale] = useState(1);
  const [showInspector, setShowInspector] = useState(false);
  const [selectedElement, setSelectedElement] = useState<any>(null);

  // Load sessions on mount
  useEffect(() => {
    loadSessions();
  }, []);

  const loadSessions = async () => {
    try {
      const res = await api.listBrowserSessions();
      setSessions(res.sessions || []);
    } catch (e) {
      console.error('Failed to load sessions:', e);
    }
  };

  const createSession = async () => {
    if (!newSessionUrl.trim()) return;
    setIsLoading(true);
    try {
      const session = await api.createBrowserSession({ url: newSessionUrl });
      setSessions(prev => [session, ...prev]);
      setActiveSession(session.session_id);
      await loadSessionState(session.session_id);
    } catch (e) {
      console.error('Failed to create session:', e);
    } finally {
      setIsLoading(false);
    }
  };

  const loadSessionState = async (sessionId: string) => {
    setIsLoading(true);
    try {
      const state = await api.getBrowserState(sessionId);
      setBrowserState(state);
      setActiveSession(sessionId);
    } catch (e) {
      console.error('Failed to load session state:', e);
    } finally {
      setIsLoading(false);
    }
  };

  const closeSession = async (sessionId: string) => {
    try {
      await api.closeBrowserSession(sessionId);
      setSessions(prev => prev.filter(s => s.session_id !== sessionId));
      if (activeSession === sessionId) {
        setActiveSession(null);
        setBrowserState(null);
      }
    } catch (e) {
      console.error('Failed to close session:', e);
    }
  };

  const executeAction = async (action: BrowserAction) => {
    if (!activeSession) return;
    setIsLoading(true);
    try {
      const result = await api.browserAction(activeSession, action);
      setActionLog(prev => [{
        action: action.action,
        params: action.params,
        result,
        timestamp: new Date().toISOString()
      }, ...prev.slice(0, 49)]);
      await loadSessionState(activeSession);
    } catch (e) {
      console.error('Action failed:', e);
    } finally {
      setIsLoading(false);
    }
  };

  const takeScreenshot = async (fullPage = false) => {
    if (!activeSession) return;
    setIsLoading(true);
    try {
      const res = await api.browserScreenshot(activeSession, fullPage);
      setBrowserState(prev => prev ? { ...prev, screenshot_base64: res.screenshot_base64 } : null);
    } catch (e) {
      console.error('Screenshot failed:', e);
    } finally {
      setIsLoading(false);
    }
  };

  const navigate = (url: string) => {
    if (!url.startsWith('http') && !url.startsWith('https')) {
      url = 'https://' + url;
    }
    executeAction({ action: 'navigate', params: { url } });
  };

  const goBack = () => executeAction({ action: 'go_back', params: {} });
  const goForward = () => executeAction({ action: 'go_forward', params: {} });
  const refresh = () => executeAction({ action: 'refresh', params: {} });

  const clickElement = (selector: string) => executeAction({ action: 'click', params: { selector } });
  const typeText = (selector: string, text: string) => executeAction({ action: 'type', params: { selector, text } });
  const scrollDown = () => executeAction({ action: 'scroll', params: { direction: 'down', amount: 500 } });
  const scrollUp = () => executeAction({ action: 'scroll', params: { direction: 'up', amount: 500 } });
  const scrollTo = (x: number, y: number) => executeAction({ action: 'scroll', params: { x, y } });
  const getText = (selector: string) => executeAction({ action: 'get_text', params: { selector } });
  const getAttribute = (selector: string, attr: string) => executeAction({ action: 'get_attribute', params: { selector, attribute: attr } });
  const wait = (ms: number) => executeAction({ action: 'wait', params: { ms } });

  return (
    <div className="h-full flex flex-col" style={{ minHeight: 0 }}>
      {/* Header */}
      <div className="mb-6 flex-shrink-0">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-2xl font-bold">Browser Automation</h1>
            <p className="text-muted-foreground">Control and inspect browser sessions in real-time</p>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={() => setNewSessionUrl('https://example.com')} disabled={isLoading}>
              <Plus className="h-4 w-4 mr-1" />
              New Session
            </Button>
            <Button variant="outline" size="sm" onClick={loadSessions} disabled={isLoading}>
              <RefreshCw className="h-4 w-4 mr-1" />
              Refresh
            </Button>
          </div>
        </div>

        {/* Session Manager */}
        <Card className="mb-4">
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Active Sessions</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-3">
              <div className="flex-1 min-w-[250px] flex gap-2">
                <Input
                  placeholder="Enter URL..."
                  value={newSessionUrl}
                  onChange={(e) => setNewSessionUrl(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && createSession()}
                  className="flex-1"
                />
                <Button onClick={createSession} disabled={isLoading || !newSessionUrl.trim()}>
                  <Plus className="h-4 w-4 mr-1" />
                  Create
                </Button>
              </div>
              <div className="flex-1 min-w-[200px] flex items-center gap-2 flex-wrap">
                {sessions.map(session => (
                  <div
                    key={session.session_id}
                    className="relative flex items-center gap-2"
                  >
                    <button
                      onClick={() => loadSessionState(session.session_id)}
                      className={cn(
                        'px-3 py-1.5 rounded-lg text-sm font-medium transition-colors flex items-center gap-2 truncate max-w-[180px]',
                        activeSession === session.session_id ? 'bg-primary text-primary-foreground' : 'bg-muted hover:bg-accent text-muted-foreground'
                      )}
                    >
                      <Globe className="h-3.5 w-3.5 flex-shrink-0" />
                      <span className="truncate">{session.title || session.url}</span>
                      <Badge variant="outline" className="text-xs">LIVE</Badge>
                    </button>
                    <button
                      onClick={(e) => { e.stopPropagation(); closeSession(session.session_id); }}
                      className="p-0.5 rounded hover:bg-accent text-muted-foreground hover:text-foreground"
                      title="Close session"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </div>
                ))}
                {sessions.length === 0 && (
                  <span className="text-muted-foreground text-sm">No active sessions</span>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden" style={{ minHeight: 0 }}>
        {activeSession && browserState ? (
          <>
            {/* Browser Controls */}
            <Card className="mb-4">
              <CardContent className="p-3">
                <div className="flex flex-wrap items-center gap-2">
                  <div className="flex items-center gap-1 border border-border rounded-lg overflow-hidden">
                    <Button variant="ghost" size="icon" onClick={goBack} title="Back" disabled={isLoading}>
                      <ChevronLeft className="h-4 w-4" />
                    </Button>
                    <Button variant="ghost" size="icon" onClick={goForward} title="Forward" disabled={isLoading}>
                      <ChevronRight className="h-4 w-4" />
                    </Button>
                    <Button variant="ghost" size="icon" onClick={refresh} title="Refresh" disabled={isLoading}>
                      <RefreshCw className="h-4 w-4" />
                    </Button>
                    <Button variant="ghost" size="icon" onClick={() => takeScreenshot(false)} title="Screenshot" disabled={isLoading}>
                      <Monitor className="h-4 w-4" />
                    </Button>
                    <Button variant="ghost" size="icon" onClick={() => takeScreenshot(true)} title="Full Page Screenshot" disabled={isLoading}>
                      <Image className="h-4 w-4" />
                    </Button>
                  </div>

                  <div className="flex-1 min-w-[200px] flex items-center gap-1 border border-border rounded-lg overflow-hidden">
                    <Globe className="h-4 w-4 px-2 text-muted-foreground" />
                    <Input
                      placeholder="Enter URL and press Enter"
                      value={browserState.url}
                      onChange={(e) => {}}
                      onKeyDown={(e) => e.key === 'Enter' && navigate((e.target as HTMLInputElement).value)}
                      className="flex-1 bg-transparent border-none focus:ring-0 py-1.5 text-sm"
                    />
                    <Button variant="ghost" size="icon" onClick={() => navigate(browserState.url)} title="Go">
                      <Zap className="h-4 w-4" />
                    </Button>
                  </div>

                  <div className="flex items-center gap-2">
                    <div className="flex items-center gap-1 border border-border rounded-lg p-1">
                      <span className="text-xs text-muted-foreground">Scale:</span>
                      <Button variant="ghost" size="icon" onClick={() => setScreenshotScale(Math.max(0.25, screenshotScale - 0.25))} title="Zoom Out">
                        <ChevronLeft className="h-3.5 w-3.5" />
                      </Button>
                      <span className="text-sm font-mono text-muted-foreground w-12 text-center">{Math.round(screenshotScale * 100)}%</span>
                      <Button variant="ghost" size="icon" onClick={() => setScreenshotScale(Math.min(2, screenshotScale + 0.25))} title="Zoom In">
                        <ChevronRight className="h-3.5 w-3.5" />
                      </Button>
                      <Button variant="ghost" size="icon" onClick={() => setScreenshotScale(1)} title="Reset">
                        <RotateCcw className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setShowInspector(!showInspector)}
                      className={showInspector ? 'bg-primary text-primary-foreground' : ''}
                    >
                      <MousePointer className="h-4 w-4 mr-1" />
                      Inspector
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Browser View / Inspector */}
            <div className="flex-1 flex min-h-0" style={{ minHeight: 0 }}>
              {/* Screenshot View */}
              <div className={cn('flex-1 relative bg-gray-100 dark:bg-gray-900 rounded-lg border border-border overflow-auto', showInspector && 'flex-1')}>
                {browserState.screenshot_base64 ? (
                  <div
                    className="w-full h-full flex items-center justify-center p-2"
                    style={{ transform: `scale(${screenshotScale})`, transformOrigin: 'top center' }}
                  >
                    <img
                      src={`data:image/png;base64,${browserState.screenshot_base64}`}
                      alt="Browser screenshot"
                      className="max-w-full max-h-full shadow-lg bg-white dark:bg-gray-800"
                      style={{
                        borderRadius: '4px',
                        boxShadow: '0 4px 20px rgba(0,0,0,0.15)'
                      }}
                    />
                    {selectedElement && (
                      <div
                        className="absolute border-2 border-blue-500 bg-blue-500/10 pointer-events-none"
                        style={{
                          left: selectedElement.x,
                          top: selectedElement.y,
                          width: selectedElement.width,
                          height: selectedElement.height,
                        }}
                      >
                        <div className="absolute -top-5 left-0 bg-blue-500 text-white text-xs px-1.5 py-0.5 rounded whitespace-nowrap">
                          {selectedElement.tagName?.toLowerCase()}#{selectedElement.id || ''}.{selectedElement.className || ''}
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="w-full h-full flex flex-col items-center justify-center text-muted-foreground">
                    <Monitor className="h-16 w-16 mb-4 text-muted-foreground/30" />
                    <p>No screenshot available</p>
                    <p className="text-sm">Click "Screenshot" to capture current view</p>
                  </div>
                )}

                {/* Page Info Overlay */}
                <div className="absolute bottom-2 left-2 right-2 flex flex-wrap gap-2 justify-between">
                  <div className="flex flex-wrap gap-1">
                    <Badge variant="secondary" className="text-xs">{browserState.url}</Badge>
                    <Badge variant="outline" className="text-xs">{browserState.title}</Badge>
                    <Badge variant="outline" className="text-xs">{browserState.viewport_height}px viewport</Badge>
                    <Badge variant="outline" className="text-xs">{browserState.tabs?.length || 0} tabs</Badge>
                  </div>
                  {isLoading && (
                    <div className="flex items-center gap-1 text-xs text-muted-foreground">
                      <RefreshCw className="h-3 w-3 animate-spin" />
                      Loading...
                    </div>
                  )}
                </div>
              </div>

              {/* Element Inspector Panel */}
              <AnimatePresence>
                {showInspector && (
                  <motion.div
                    initial={{ width: 0, opacity: 0 }}
                    animate={{ width: 380, opacity: 1 }}
                    exit={{ width: 0, opacity: 0 }}
                    transition={{ type: 'spring', damping: 25, stiffness: 200 }}
                    className="border-l border-border bg-card overflow-hidden flex flex-col"
                    style={{ width: 380, minWidth: 380 }}
                  >
                    <div className="p-3 border-b border-border flex items-center justify-between">
                      <h3 className="font-medium">Element Inspector</h3>
                      <Button variant="ghost" size="icon" onClick={() => setShowInspector(false)}>
                        <X className="h-4 w-4" />
                      </Button>
                    </div>
                    <ScrollArea className="flex-1 p-3">
                      {selectedElement ? (
                        <div className="space-y-3 text-sm">
                          <div>
                            <label className="text-xs text-muted-foreground block mb-1">Tag</label>
                            <code className="px-2 py-1 bg-muted rounded text-sm font-mono">{selectedElement.tagName?.toLowerCase()}</code>
                          </div>
                          {selectedElement.id && (
                            <div>
                              <label className="text-xs text-muted-foreground block mb-1">ID</label>
                              <code className="px-2 py-1 bg-muted rounded text-sm font-mono">{selectedElement.id}</code>
                            </div>
                          )}
                          {selectedElement.className && (
                            <div>
                              <label className="text-xs text-muted-foreground block mb-1">Class</label>
                              <code className="px-2 py-1 bg-muted rounded text-sm font-mono">{selectedElement.className}</code>
                            </div>
                          )}
                          {selectedElement.text && (
                            <div>
                              <label className="text-xs text-muted-foreground block mb-1">Text</label>
                              <code className="px-2 py-1 bg-muted rounded text-sm font-mono max-w-full truncate block">{selectedElement.text.slice(0, 200)}</code>
                            </div>
                          )}
                          {selectedElement.attributes && Object.keys(selectedElement.attributes).length > 0 && (
                            <div>
                              <label className="text-xs text-muted-foreground block mb-1">Attributes</label>
                              <div className="space-y-1 max-h-48 overflow-auto">
                                {Object.entries(selectedElement.attributes).map(([key, value]) => (
                                  <div key={key} className="flex gap-2 text-xs">
                                    <span className="text-muted-foreground font-medium">{key}:</span>
                                    <code className="flex-1 truncate bg-muted px-1.5 py-0.5 rounded font-mono">{String(value)}</code>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                          {selectedElement.selector && (
                            <div>
                              <label className="text-xs text-muted-foreground block mb-1">Selector</label>
                              <code className="px-2 py-1 bg-muted rounded text-sm font-mono truncate block">{selectedElement.selector}</code>
                            </div>
                          )}
                          <div className="flex gap-1 pt-2">
                            <Button variant="outline" size="sm" className="flex-1" onClick={() => clickElement(selectedElement.selector)}>
                              <MousePointer className="h-3.5 w-3.5 mr-1" />
                              Click
                            </Button>
                            <Button variant="outline" size="sm" className="flex-1" onClick={() => getText(selectedElement.selector)}>
                              <Type className="h-3.5 w-3.5 mr-1" />
                              Get Text
                            </Button>
                          </div>
                          <div className="flex gap-1">
                            <Button variant="outline" size="sm" className="flex-1" onClick={() => getAttribute(selectedElement.selector, 'href')}>
                              <Globe className="h-3.5 w-3.5 mr-1" />
                              Get Href
                            </Button>
                            <Button variant="outline" size="sm" className="flex-1" onClick={() => getAttribute(selectedElement.selector, 'src')}>
                              <Image className="h-3.5 w-3.5 mr-1" />
                              Get Src
                            </Button>
                          </div>
                        </div>
                      ) : (
                        <div className="text-center text-muted-foreground py-8">
                          <MousePointer className="h-12 w-12 mx-auto mb-3 text-muted-foreground/30" />
                          <p className="text-sm">Click on an element in the screenshot to inspect it</p>
                          <p className="text-xs mt-1">Enable inspector mode and click elements</p>
                        </div>
                      )}
                    </ScrollArea>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            {/* Action Log */}
            <Card className="mt-4">
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-base">Action Log</CardTitle>
                <Button variant="ghost" size="icon" onClick={() => setActionLog([])}>
                  <Trash2 className="h-4 w-4" />
                </Button>
              </CardHeader>
              <CardContent className="p-0">
                <ScrollArea className="h-48">
                  <div className="p-3 space-y-2">
                    {actionLog.length === 0 ? (
                      <p className="text-center text-muted-foreground py-8">No actions yet</p>
                    ) : (
                      actionLog.map((log, idx) => (
                        <motion.div
                          key={idx}
                          initial={{ opacity: 0, x: -20 }}
                          animate={{ opacity: 1, x: 0 }}
                          className="text-xs font-mono text-muted-foreground p-2 bg-muted/50 rounded"
                        >
                          <div className="flex items-center gap-2 mb-1">
                            <span className="text-primary font-medium">{log.action}</span>
                            <span className="text-muted-foreground/50">{new Date(log.timestamp).toLocaleTimeString()}</span>
                          </div>
                          <div className="text-muted-foreground/70 ml-4">
                            Params: {JSON.stringify(log.params).slice(0, 100)}
                          </div>
                          {log.result && (
                            <div className="text-muted-foreground/50 ml-4 mt-1">
                              Result: {JSON.stringify(log.result).slice(0, 150)}
                            </div>
                          )}
                        </motion.div>
                      ))
                    )}
                  </div>
                </ScrollArea>
              </CardContent>
            </Card>

            {/* Quick Actions */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base">Quick Actions</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-2">
                  <Button variant="outline" size="sm" onClick={scrollDown} disabled={isLoading}>
                    <ArrowDown className="h-4 w-4 mr-1" />
                    Scroll Down
                  </Button>
                  <Button variant="outline" size="sm" onClick={scrollUp} disabled={isLoading}>
                    <ArrowUp className="h-4 w-4 mr-1" />
                    Scroll Up
                  </Button>
                  <Button variant="outline" size="sm" onClick={() => navigate('https://google.com')} disabled={isLoading}>
                    <Search className="h-4 w-4 mr-1" />
                    Google
                  </Button>
                  <Button variant="outline" size="sm" onClick={() => navigate('https://github.com')} disabled={isLoading}>
                    <Globe className="h-4 w-4 mr-1" />
                    GitHub
                  </Button>
                  <Button variant="outline" size="sm" onClick={() => wait(1000)} disabled={isLoading}>
                    <RefreshCw className="h-4 w-4 mr-1" />
                    Wait 1s
                  </Button>
                  <Button variant="outline" size="sm" onClick={() => takeScreenshot(true)} disabled={isLoading}>
                    <Image className="h-4 w-4 mr-1" />
                    Full Page
                  </Button>
                </div>
              </CardContent>
            </Card>
          </>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center text-muted-foreground">
            <Monitor className="h-24 w-24 mb-6 text-muted-foreground/30" />
            <h2 className="text-xl font-medium mb-2">No Active Browser Session</h2>
            <p className="text-center max-w-md mb-6">
              Create a new browser session or select an existing one from the sessions bar above to start automation.
            </p>
            <div className="flex gap-3">
              <Button size="lg" onClick={() => setNewSessionUrl('https://example.com')}>
                <Plus className="h-5 w-5 mr-2" />
                Create New Session
              </Button>
              <Button variant="outline" size="lg" onClick={loadSessions}>
                <RefreshCw className="h-5 w-5 mr-2" />
                Refresh Sessions
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}