'use client';

import { cn } from '@/lib/utils';
import { useUIStore } from '@/stores/uiStore';
import { useRuntimeStore } from '@/stores/runtimeStore';
import { useChatStore } from '@/stores/chatStore';
import { Button } from '@/components/ui/button';
import { Avatar } from './Avatar';
import { Separator } from '@/components/ui/separator';
import {
  Menu,
  Sun,
  Moon,
  Monitor,
  ChevronDown,
  Plus,
  Search,
  Bell,
  Settings,
  LayoutDashboard,
  Power,
  MessageSquare,
  X,
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useState, useRef, useEffect } from 'react';
import { useTheme } from 'next-themes';
import { api } from '@/lib/api';

export function Header() {
  const { sidebarOpen, toggleSidebar, rightPanelOpen, toggleRightPanel, theme: storeTheme, setTheme: setStoreTheme } = useUIStore();
  const { resolvedTheme } = useTheme();
  const theme = storeTheme || resolvedTheme || 'system';
  const setTheme = (t: 'light' | 'dark' | 'system') => {
    setStoreTheme(t);
  };
  const { status, info } = useRuntimeStore();
  const { currentConversationId, setCurrentConversationId, conversations } = useChatStore();
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [showThemeMenu, setShowThemeMenu] = useState(false);
  const [showConversationMenu, setShowConversationMenu] = useState(false);
  const [newConvTitle, setNewConvTitle] = useState('');
  const conversationMenuRef = useRef<HTMLDivElement>(null);
  const userMenuRef = useRef<HTMLDivElement>(null);
  const themeMenuRef = useRef<HTMLDivElement>(null);

  // Close menus when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (conversationMenuRef.current && !conversationMenuRef.current.contains(event.target as Node)) {
        setShowConversationMenu(false);
      }
      if (userMenuRef.current && !userMenuRef.current.contains(event.target as Node)) {
        setShowUserMenu(false);
      }
      if (themeMenuRef.current && !themeMenuRef.current.contains(event.target as Node)) {
        setShowThemeMenu(false);
      }
    }

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleNewConversation = async () => {
    if (!newConvTitle.trim()) return;
    try {
      const conv = await api.createConversation({
        title: newConvTitle,
        system_prompt: '',
        context: {},
      });
      useChatStore.getState().addConversation(conv);
      setCurrentConversationId(conv.conversation_id);
      setNewConvTitle('');
      setShowConversationMenu(false);
    } catch (e) {
      console.error('Failed to create conversation:', e);
    }
  };

  return (
    <header className="sticky top-0 z-20 h-16 bg-background/95 backdrop-blur-sm border-b border-border flex items-center justify-between px-4 lg:px-6" suppressHydrationWarning>
      {/* Left Section */}
      <div className="flex items-center gap-4">
        {/* Mobile menu button */}
        <button
          onClick={toggleSidebar}
          className="lg:hidden p-2 rounded-lg hover:bg-accent transition-colors"
          aria-label="Toggle sidebar"
        >
          <Menu className="h-5 w-5" />
        </button>

        {/* Desktop: show runtime status */}
        <div className="hidden lg:flex items-center gap-3 px-3 py-1.5 rounded-lg bg-muted/50">
          <span
            className={cn(
              'w-2 h-2 rounded-full',
              status === 'connected' && 'bg-green-500',
              status === 'connecting' && 'bg-yellow-500 animate-pulse',
              status === 'disconnected' && 'bg-gray-400',
              status === 'error' && 'bg-red-500',
            )}
          />
          <span className="text-sm font-medium capitalize">{status || 'disconnected'}</span>
          {info && (
            <span className="text-xs text-muted-foreground font-mono">{info.runtime_id}</span>
          )}
        </div>
      </div>

      {/* Center Section - Conversation selector */}
      <div className="flex-1 lg:max-w-md mx-4 flex items-center justify-center">
        <div className="relative w-full max-w-md" ref={conversationMenuRef}>
          <button
            onClick={() => setShowConversationMenu(!showConversationMenu)}
            className={cn(
              'w-full flex items-center gap-2 px-3 py-2 rounded-lg border border-border bg-background',
              'hover:bg-accent hover:text-accent-foreground transition-colors',
              'text-left justify-between'
            )}
          >
            <div className="flex items-center gap-2 flex-1 min-w-0">
              <MessageSquare className="h-4 w-4 text-muted-foreground" />
              <span className="truncate text-sm font-medium">
                {conversations.find(c => c.conversation_id === currentConversationId)?.title || 'New Conversation'}
              </span>
            </div>
            <ChevronDown className="h-4 w-4 text-muted-foreground flex-shrink-0" />
          </button>

          {/* Conversation dropdown */}
          <AnimatePresence>
            {showConversationMenu && (
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="absolute top-full left-0 right-0 mt-1 bg-popover border border-border rounded-lg shadow-lg py-1 z-50"
              >
                <div className="p-2 border-b border-border">
                  <input
                    type="text"
                    value={newConvTitle}
                    onChange={(e) => setNewConvTitle(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleNewConversation()}
                    placeholder="New conversation title..."
                    className="w-full px-3 py-2 text-sm border border-input rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-ring"
                    autoFocus
                  />
                </div>
                <div className="max-h-60 overflow-y-auto">
                  {conversations.slice(0, 10).map((conv) => (
                    <button
                      key={conv.conversation_id}
                      onClick={() => {
                        setCurrentConversationId(conv.conversation_id);
                        setShowConversationMenu(false);
                      }}
                      className={cn(
                        'w-full flex items-center gap-2 px-3 py-2 text-left text-sm transition-colors',
                        'hover:bg-accent hover:text-accent-foreground',
                        currentConversationId === conv.conversation_id && 'bg-accent text-accent-foreground'
                      )}
                    >
                      <MessageSquare className="h-4 w-4 flex-shrink-0" />
                      <span className="truncate">{conv.title || 'Untitled'}</span>
                    </button>
                  ))}
                </div>
                <div className="p-2 border-t border-border">
                  <button
                    onClick={handleNewConversation}
                    disabled={!newConvTitle.trim()}
                    className="w-full flex items-center justify-center gap-2 px-3 py-2 text-sm font-medium rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
                  >
                    <Plus className="h-4 w-4" />
                    Create
                  </button>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* Right Section */}
      <div className="flex items-center gap-2">
        {/* Theme toggle */}
        <div className="relative" ref={themeMenuRef}>
          <button
            onClick={() => setShowThemeMenu(!showThemeMenu)}
            className="p-2 rounded-lg hover:bg-accent transition-colors"
            aria-label="Toggle theme"
          >
            {theme === 'dark' ? (
              <Moon className="h-5 w-5" />
            ) : theme === 'light' ? (
              <Sun className="h-5 w-5" />
            ) : (
              <Monitor className="h-5 w-5" />
            )}
          </button>
          <AnimatePresence>
            {showThemeMenu && (
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="absolute right-0 top-full mt-1 bg-popover border border-border rounded-lg shadow-lg py-1 z-50 min-w-[140px]"
              >
                {['light', 'dark', 'system'].map((t) => (
                  <button
                    key={t}
                    onClick={() => {
                      setTheme(t as any);
                      setShowThemeMenu(false);
                    }}
                    className={cn(
                      'w-full flex items-center gap-2 px-3 py-2 text-sm transition-colors',
                      'hover:bg-accent hover:text-accent-foreground',
                      theme === t && 'bg-accent text-accent-foreground'
                    )}
                  >
                    {t === 'light' && <Sun className="h-4 w-4" />}
                    {t === 'dark' && <Moon className="h-4 w-4" />}
                    {t === 'system' && <Monitor className="h-4 w-4" />}
                    <span className="capitalize">{t}</span>
                  </button>
                ))}
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Notifications */}
        <button className="relative p-2 rounded-lg hover:bg-accent transition-colors">
          <Bell className="h-5 w-5" />
          <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full" />
        </button>

        {/* Right panel toggle */}
        <button
          onClick={toggleRightPanel}
          className={cn(
            'p-2 rounded-lg hover:bg-accent transition-colors',
            rightPanelOpen && 'bg-accent text-accent-foreground'
          )}
        >
          <LayoutDashboard className="h-5 w-5" />
        </button>

        {/* User / Avatar */}
        <div className="relative ml-2" ref={userMenuRef}>
          <button
            onClick={() => setShowUserMenu(!showUserMenu)}
            className="flex items-center gap-2 p-1 rounded-lg hover:bg-accent transition-colors"
          >
            <Avatar state="idle" size="sm" />
          </button>

          <AnimatePresence>
            {showUserMenu && (
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="absolute right-0 top-full mt-1 bg-popover border border-border rounded-lg shadow-lg py-1 z-50 min-w-[180px]"
              >
                <div className="px-3 py-2 border-b border-border">
                  <p className="text-xs font-medium text-muted-foreground">Runtime</p>
                  <p className="text-sm font-mono text-muted-foreground">{info?.runtime_id || 'N/A'}</p>
                </div>
                <button className="w-full flex items-center gap-2 px-3 py-2 text-sm transition-colors hover:bg-accent hover:text-accent-foreground">
                  <Settings className="h-4 w-4" />
                  Settings
                </button>
                <button className="w-full flex items-center gap-2 px-3 py-2 text-sm transition-colors hover:bg-accent hover:text-accent-foreground text-destructive">
                  <Power className="h-4 w-4" />
                  Disconnect
                </button>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </header>
  );
}