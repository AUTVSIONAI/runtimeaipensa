'use client';

import { cn } from '@/lib/utils';
import { useUIStore } from '@/stores/uiStore';
import { useRuntimeStore } from '@/stores/runtimeStore';
import { useChatStore } from '@/stores/chatStore';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Avatar } from '@/components/layout/Avatar';
import { Separator } from '@/components/ui/separator';
import {
  Send,
  Globe,
  RefreshCw,
  ChevronLeft,
  ChevronRight,
  X,
  Plus,
  Trash2,
  ArrowUpRight,
  Settings,
  Monitor,
  Camera,
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useState, useRef, useEffect } from 'react';
import { api } from '@/lib/api';

export function BrowserPanel() {
  const { rightPanelTab } = useUIStore();
  const [sessions, setSessions] = useState<Array<{ session_id: string; url: string; state: any }>>([]);
  const [activeSession, setActiveSession] = useState<string | null>(null);
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [screenshot, setScreenshot] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const activeSessionData = sessions.find(s => s.session_id === activeSession);

  const createSession = async () => {
    if (!url.trim()) return;
    setLoading(true);
    try {
      const session = await api.createBrowserSession({ url });
      setSessions(prev => [...prev, { ...session, state: null }]);
      setActiveSession(session.session_id);
      setUrl('');
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const refreshSession = async (sessionId: string) => {
    try {
      const state = await api.getBrowserState(sessionId);
      setSessions(prev => prev.map(s => s.session_id === sessionId ? { ...s, state } : s));
    } catch (e) {
      console.error(e);
    }
  };

  const takeScreenshot = async (sessionId: string) => {
    try {
      const result = await api.browserScreenshot(sessionId, true);
      setScreenshot(result.screenshot_base64);
    } catch (e) {
      console.error(e);
    }
  };

  const closeSession = async (sessionId: string) => {
    try {
      await api.closeBrowserSession(sessionId);
      setSessions(prev => prev.filter(s => s.session_id !== sessionId));
      if (activeSession === sessionId) {
        setActiveSession(sessions[0]?.session_id || null);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const executeAction = async (action: string, params: any) => {
    if (!activeSession) return;
    try {
      const result = await api.browserAction(activeSession, { action, params });
      await refreshSession(activeSession);
      return result;
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="h-full flex flex-col p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-medium">Browser Automation</h3>
        <div className="flex gap-2">
          <Button variant="ghost" size="sm" onClick={() => fileInputRef.current?.click()}>
            <Monitor className="h-4 w-4 mr-1" /> Open File
          </Button>
          <input type="file" ref={fileInputRef} className="hidden" accept=".html,.htm" />
        </div>
      </div>

      {/* Session list */}
      <div className="mb-4 border border-border rounded-lg overflow-hidden">
        <div className="p-3 border-b border-border flex gap-2">
          <Input
            placeholder="Enter URL (https://...)"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && createSession()}
            className="flex-1"
          />
          <Button size="sm" onClick={createSession} disabled={loading}>
            {loading ? 'Starting...' : 'New Session'}
          </Button>
        </div>

        <div className="max-h-40 overflow-y-auto">
          {sessions.length === 0 && (
            <div className="p-8 text-center text-muted-foreground">
              No browser sessions. Create one above.
            </div>
          )}
          {sessions.map((session) => (
            <button
              key={session.session_id}
              onClick={() => setActiveSession(session.session_id)}
              className={cn(
                'w-full px-3 py-2 text-left text-sm border-b border-border hover:bg-accent transition-colors',
                activeSession === session.session_id && 'bg-accent'
              )}
            >
              <div className="flex items-center justify-between">
                <span className="truncate flex-1 mr-2">{session.url}</span>
                <span className="text-xs text-muted-foreground">{session.session_id.slice(0, 8)}</span>
              </div>
              {session.state && (
                <div className="text-xs text-muted-foreground mt-1 truncate">{session.state.title || session.state.url}</div>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Active session view */}
      {activeSessionData && (
        <div className="flex-1 flex flex-col border border-border rounded-lg overflow-hidden">
          <div className="flex items-center gap-2 p-3 border-b border-border bg-muted/30">
            <Globe className="h-4 w-4" />
            <Input
              value={activeSessionData.url}
              onChange={(e) => {
                const newUrl = e.target.value;
                setUrl(newUrl);
                executeAction('navigate', { url: newUrl });
              }}
              className="flex-1"
              placeholder="URL"
            />
            <Button variant="ghost" size="icon" onClick={() => executeAction('go_back', {})} title="Back">
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <Button variant="ghost" size="icon" onClick={() => executeAction('refresh', {})} title="Refresh">
              <RefreshCw className="h-4 w-4" />
            </Button>
            <Button variant="ghost" size="icon" onClick={() => takeScreenshot(activeSession!)} title="Screenshot">
              <Camera className="h-4 w-4" />
            </Button>
            <Button variant="ghost" size="icon" onClick={() => closeSession(activeSession!)} title="Close">
              <X className="h-4 w-4" />
            </Button>
          </div>

          <div className="flex-1 relative overflow-hidden">
            {screenshot && (
              <div className="absolute inset-0 flex items-center justify-center bg-black/50 z-10">
                <motion.div
                  initial={{ scale: 0.9, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  className="max-w-full max-h-full p-4 bg-white rounded shadow-xl"
                >
                  <img
                    src={`data:image/jpeg;base64,${screenshot}`}
                    alt="Browser screenshot"
                    className="max-w-[80vw] max-h-[80vh]"
                  />
                  <Button className="mt-2" onClick={() => setScreenshot(null)}>
                    <X className="h-4 w-4 mr-1" /> Close
                  </Button>
                </motion.div>
              </div>
            )}

            {activeSessionData.state && !screenshot && (
              <div className="absolute inset-0 flex items-center justify-center p-4">
                <div className="text-center text-muted-foreground">
                  <Monitor className="mx-auto h-16 w-16 mb-4 opacity-30" />
                  <p>Browser session running</p>
                  <p className="text-sm">{activeSessionData.state.title || 'Loading...'}</p>
                  <p className="text-xs font-mono">{activeSessionData.state.url}</p>
                </div>
              </div>
            )}

            {activeSessionData.state?.screenshot_base64 && !screenshot && (
              <img
                src={`data:image/jpeg;base64,${activeSessionData.state.screenshot_base64}`}
                alt="Browser view"
                className="absolute inset-0 w-full h-full object-cover"
              />
            )}
          </div>

          {/* Action buttons */}
          <div className="p-3 border-t border-border bg-muted/30 flex flex-wrap gap-2">
            <Button variant="outline" size="sm" onClick={() => executeAction('click_element', { index: 0 })}>Click Element</Button>
            <Button variant="outline" size="sm" onClick={() => executeAction('scroll_down', {})}>Scroll Down</Button>
            <Button variant="outline" size="sm" onClick={() => executeAction('scroll_up', {})}>Scroll Up</Button>
            <Button variant="outline" size="sm" onClick={() => executeAction('extract_content', { goal: 'Summarize page' })}>Extract</Button>
          </div>
        </div>
      )}
    </div>
  );
}