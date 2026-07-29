'use client';

import { cn } from '@/lib/utils';
import { useRouter, usePathname } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { useUIStore } from '@/stores/uiStore';
import { useRuntimeStore } from '@/stores/runtimeStore';
import { useState, useEffect } from 'react';
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
  Image,
  Link,
  Search,
  Brain,
  ChevronRight,
  ChevronDown,
  Zap,
  Activity,
  Settings,
  Plug,
  LayoutDashboard,
  Bug,
  Clock as ClockIcon,
  MessageCircle,
  Monitor,
  FileText,
  FolderKanban,
} from 'lucide-react';

interface NavItem {
  id: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  href: string;
  modules?: string[];
}

const NAV_ITEMS: NavItem[] = [
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard, href: '/dashboard' },
  { id: 'chat', label: 'Chat', icon: MessageCircle, href: '/dashboard/chat', modules: ['agent', 'conversation'] },
  { id: 'workspace', label: 'Workspace', icon: FolderKanban, href: '/dashboard/workspace', modules: ['workspace', 'filesystem'] },
  { id: 'workflow', label: 'Workflow', icon: GitBranch, href: '/dashboard/workflow', modules: ['workflow', 'scheduler', 'queue'] },
  { id: 'timeline', label: 'Timeline', icon: ClockIcon, href: '/dashboard/timeline' },
  { id: 'debug', label: 'Debug', icon: Bug, href: '/dashboard/debug', modules: ['notification', 'storage', 'authentication', 'workspace'] },
  { id: 'browser', label: 'Browser', icon: Globe, href: '/dashboard/browser' },
  { id: 'preview', label: 'Preview', icon: Monitor, href: '/dashboard/preview' },
  { id: 'settings', label: 'Settings', icon: Settings, href: '/dashboard/settings' },
  { id: 'plugins', label: 'Plugins', icon: Plug, href: '/dashboard/plugins' },
];

export function Sidebar() {
  const { sidebarOpen, setSidebarOpen } = useUIStore();
  const { modules, status } = useRuntimeStore();
  const router = useRouter();
  const pathname = usePathname();
  const [activeModule, setActiveModule] = useState<string | null>(null);
  const [isClient, setIsClient] = useState(false);
  const [isMobile, setIsMobile] = useState(false);

  const moduleStates: Record<string, string> = {};
  Object.entries(modules).forEach(([name, module]) => {
    moduleStates[name] = module.state;
  });

  useEffect(() => {
    setIsClient(true);
    const checkMobile = () => setIsMobile(window.innerWidth < 1024);
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  const handleNavClick = (href: string) => {
    router.push(href);
    if (isMobile) {
      setSidebarOpen(false);
    }
  };

  const isActiveNav = (href: string) => {
    if (!isClient) {
      return false;
    }
    return pathname === href || pathname.startsWith(href + '/');
  };

  if (!isClient) {
    // Return a stable skeleton during SSR to avoid hydration mismatch
    return (
      <motion.aside
        initial={{ x: -300 }}
        animate={{ x: sidebarOpen ? 0 : -300 }}
        transition={{ type: 'spring', damping: 25, stiffness: 200 }}
        className={cn(
          'fixed lg:relative left-0 top-0 z-40 h-screen w-72 bg-card border-r border-border',
          'flex flex-col',
          'transition-transform duration-300'
        )}
        suppressHydrationWarning
      >
        <div className="flex items-center justify-between h-16 px-4 border-b border-border" suppressHydrationWarning>
          <div className="flex items-center gap-2" suppressHydrationWarning>
            <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center" suppressHydrationWarning>
              <Zap className="h-5 w-5 text-white" />
            </div>
            <span className="font-bold text-lg">AIPENSA</span>
          </div>
        </div>
        <div className="p-4 border-b border-border" suppressHydrationWarning>
          <div className="flex items-center gap-3" suppressHydrationWarning>
            <div className="w-3 h-3 rounded-full bg-gray-400" />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium capitalize">disconnected</p>
              <p className="text-xs text-muted-foreground font-mono">0 / 0 modules running</p>
            </div>
          </div>
        </div>
        <nav className="p-3 space-y-1 border-b border-border" role="navigation" aria-label="Main navigation" suppressHydrationWarning>
          <p className="px-3 py-1 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Navigation</p>
          {NAV_ITEMS.map((item) => (
            <button
              key={item.id}
              className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200 text-sm font-medium text-muted-foreground"
              title={item.label}
              suppressHydrationWarning
            >
              <item.icon className="h-5 w-5 flex-shrink-0" />
              <span className="truncate flex-1">{item.label}</span>
            </button>
          ))}
        </nav>
        <div className="p-3 border-t border-border" suppressHydrationWarning>
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Activity className="h-3.5 w-3.5" />
            <span>Runtime v1.0.0</span>
          </div>
        </div>
      </motion.aside>
    );
  }

  return (
    <motion.aside
      initial={{ x: -300 }}
      animate={{ x: sidebarOpen ? 0 : -300 }}
      transition={{ type: 'spring', damping: 25, stiffness: 200 }}
      className={cn(
        'fixed lg:relative left-0 top-0 z-40 h-screen w-72 bg-card border-r border-border',
        'flex flex-col',
        'transition-transform duration-300'
      )}
      suppressHydrationWarning
    >
      {/* Header */}
      <div className="flex items-center justify-between h-16 px-4 border-b border-border" suppressHydrationWarning>
        <div className="flex items-center gap-2" suppressHydrationWarning>
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 10, repeat: Infinity, ease: 'linear' }}
            className="h-8 w-8 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center"
            suppressHydrationWarning
          >
            <Zap className="h-5 w-5 text-white" />
          </motion.div>
          <span className="font-bold text-lg">AIPENSA</span>
        </div>
        <button
          onClick={() => setSidebarOpen(false)}
          className="lg:hidden p-1 rounded hover:bg-accent"
        >
          <ChevronDown className="h-5 w-5" />
        </button>
      </div>

      {/* Runtime Status */}
      <div className="p-4 border-b border-border" suppressHydrationWarning>
        <div className="flex items-center gap-3" suppressHydrationWarning>
          <div
            className={cn(
              'w-3 h-3 rounded-full',
              status === 'connected' && 'bg-green-500',
              status === 'connecting' && 'bg-yellow-500 animate-pulse',
              status === 'disconnected' && 'bg-gray-400',
              status === 'error' && 'bg-red-500',
            )}
          />
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium capitalize">{status || 'disconnected'}</p>
            <p className="text-xs text-muted-foreground font-mono">
              {Object.values(modules).filter(m => m.state === 'RUNNING').length} / {Object.keys(modules).length} modules running
            </p>
          </div>
        </div>
      </div>

      {/* Main Navigation - Pages */}
      <nav className="p-3 space-y-1 border-b border-border" role="navigation" aria-label="Main navigation" suppressHydrationWarning>
        <p className="px-3 py-1 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Navigation</p>
        {NAV_ITEMS.map((item) => {
          const isActive = isActiveNav(item.href);
          const navModules = item.modules || [];
          const anyRunning = navModules.length > 0 && navModules.some(m => moduleStates[m] === 'RUNNING');
          const anyError = navModules.length > 0 && navModules.some(m => moduleStates[m] === 'ERROR');
          const Icon = item.icon;

          return (
            <button
              key={item.id}
              onClick={() => handleNavClick(item.href)}
              className={cn(
                'w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200',
                'text-sm font-medium',
                isActive
                  ? 'bg-primary text-primary-foreground shadow-sm'
                  : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
              )}
              title={item.label}
              suppressHydrationWarning
            >
              <Icon className={cn('h-5 w-5 flex-shrink-0', isActive && 'text-primary-foreground', anyError && 'text-red-500', anyRunning && 'text-green-500')} />
              <span className="truncate flex-1">{item.label}</span>
              {navModules.length > 0 && (
                <span className={cn(
                  'w-2 h-2 rounded-full flex-shrink-0',
                  anyRunning && 'bg-green-500',
                  !anyRunning && anyError && 'bg-red-500',
                  !anyRunning && !anyError && navModules.some(m => moduleStates[m] === 'STOPPED') && 'bg-gray-400',
                  !anyRunning && !anyError && navModules.every(m => moduleStates[m] === 'RUNNING') && 'bg-green-500',
                  'bg-slate-400'
                )} />
              )}
            </button>
          );
        })}
      </nav>


      {/* Footer */}
      <div className="p-3 border-t border-border" suppressHydrationWarning>
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <Activity className="h-3.5 w-3.5" />
          <span>Runtime v1.0.0</span>
        </div>
      </div>
    </motion.aside>
  );
}