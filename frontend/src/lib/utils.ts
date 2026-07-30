import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';
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
} from 'lucide-react';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatTimestamp(timestamp: string): string {
  const date = new Date(timestamp);
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

export function formatDate(timestamp: string): string {
  const date = new Date(timestamp);
  return date.toLocaleDateString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}

export function truncate(str: string, length: number): string {
  if (str.length <= length) return str;
  return str.slice(0, length - 3) + '...';
}

export function jsonToString(obj: any, indent = 2): string {
  try {
    return JSON.stringify(obj, null, indent);
  } catch {
    return String(obj);
  }
}

export function parseJsonSafe(str: string): any {
  try {
    return JSON.parse(str);
  } catch {
    return str;
  }
}

export function getEventTypeColor(eventType: string): string {
  const lowerType = eventType.toLowerCase();
  if (lowerType.startsWith('runtime')) return 'blue';
  if (lowerType.startsWith('module')) return 'purple';
  if (lowerType.startsWith('task')) return 'green';
  if (lowerType.startsWith('agent')) return 'orange';
  if (lowerType.startsWith('conversation') || lowerType.startsWith('message')) return 'cyan';
  if (lowerType.startsWith('workflow')) return 'indigo';
  if (lowerType.startsWith('job')) return 'pink';
  if (lowerType.startsWith('queue')) return 'amber';
  if (lowerType.startsWith('notification')) return 'rose';
  if (lowerType.startsWith('storage')) return 'gray';
  if (lowerType.startsWith('auth')) return 'red';
  if (lowerType.startsWith('workspace')) return 'emerald';
  if (lowerType.startsWith('knowledge')) return 'teal';
  if (lowerType.startsWith('skill')) return 'violet';
  if (lowerType.startsWith('llm')) return 'blue';
  if (lowerType.startsWith('voice')) return 'amber';
  if (lowerType.startsWith('vision')) return 'green';
  if (lowerType.startsWith('video')) return 'purple';
  if (lowerType.startsWith('image')) return 'pink';
  if (lowerType.startsWith('embedding')) return 'indigo';
  if (lowerType.startsWith('rag')) return 'cyan';
  if (lowerType.startsWith('reasoning')) return 'orange';
  if (lowerType.startsWith('system')) return 'slate';
  return 'gray';
}

const moduleIcons: Record<string, React.ElementType> = {
  browser: Globe,
  execution: Terminal,
  tools: Wrench,
  memory: Database,
  planning: Map,
  mcp: Server,
  filesystem: FolderOpen,
  network: Wifi,
  docker: Box,
  agent: Bot,
  conversation: MessageSquare,
  workflow: GitBranch,
  scheduler: Clock,
  queue: List,
  notification: Bell,
  storage: HardDrive,
  authentication: Shield,
  workspace: Users,
  voice: Mic,
  vision: Eye,
  video: Video,
  image: Image,
  embedding: Link,
  rag: Search,
  reasoning: Brain,
};

export function getModuleIcon(moduleName: string): React.ElementType {
  return moduleIcons[moduleName] || Box;
}

export function getStateColor(state: string): string {
  const colors: Record<string, string> = {
    RUNNING: 'green',
    STARTING: 'yellow',
    STOPPING: 'orange',
    STOPPED: 'gray',
    ERROR: 'red',
    INITIALIZED: 'blue',
    UNINITIALIZED: 'slate',
  };
  return colors[state] || 'gray';
}

export function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

export function debounce<T extends (...args: any[]) => any>(fn: T, ms: number): T {
  let timeoutId: NodeJS.Timeout;
  return ((...args: any[]) => {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => fn(...args), ms);
  }) as T;
}

export function throttle<T extends (...args: any[]) => any>(fn: T, ms: number): T {
  let lastCall = 0;
  return ((...args: any[]) => {
    const now = Date.now();
    if (now - lastCall >= ms) {
      lastCall = now;
      fn(...args);
    }
  }) as T;
}