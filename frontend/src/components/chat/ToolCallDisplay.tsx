'use client';

import { useState } from 'react';
import { cn } from '@/lib/utils';
import { Code2, Terminal, FileText, Globe, Database, Wrench, AlertCircle, CheckCircle, XCircle, Loader2, ChevronDown } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { format } from 'date-fns';

interface ToolCallDisplayProps {
  callId: string;
  name: string;
  arguments: Record<string, any>;
  isExpanded?: boolean;
  onToggle?: () => void;
  status?: 'pending' | 'running' | 'completed' | 'failed';
  result?: any;
  error?: string;
}

export function ToolCallDisplay({
  callId,
  name,
  arguments: args,
  isExpanded = false,
  onToggle,
  status = 'pending',
  result,
  error,
}: ToolCallDisplayProps) {
  const [expanded, setExpanded] = useState(isExpanded);

  const getToolIcon = (name: string) => {
    if (name.includes('file') || name.includes('read') || name.includes('write') || name.includes('list')) return FileText;
    if (name.includes('shell') || name.includes('execute') || name.includes('python')) return Terminal;
    if (name.includes('http') || name.includes('web') || name.includes('search')) return Globe;
    if (name.includes('memory') || name.includes('search')) return Database;
    return Wrench;
  };

  const ToolIcon = getToolIcon(name);

  const formatArgs = (obj: Record<string, any>) => {
    return JSON.stringify(obj, null, 2);
  };

  const formatResult = (res: any) => {
    if (typeof res === 'string') return res;
    return JSON.stringify(res, null, 2);
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: -10, height: 0 }}
      animate={{ opacity: 1, y: 0, height: 'auto' }}
      className={cn(
        'border-l-2 border-blue-500/50 pl-4 ml-4 my-2',
        status === 'failed' && 'border-red-500/50'
      )}
    >
      {/* Tool Call Header */}
      <button
        onClick={() => onToggle?.()}
        className="flex items-center gap-2 py-1 text-sm hover:bg-accent rounded px-2 transition-colors"
        style={{ userSelect: 'none' }}
      >
        <ToolIcon className="h-4 w-4 text-blue-500 flex-shrink-0" />
        <span className="font-mono font-medium text-blue-600 dark:text-blue-400">{name}</span>
        <span className="text-xs text-muted-foreground">{callId}</span>

        {/* Status Indicator */}
        <span className="ml-auto flex items-center gap-1">
          {status === 'pending' && (
            <Loader2 className="h-3 w-3 text-yellow-500 animate-spin" />
          )}
          {status === 'running' && (
            <Loader2 className="h-3 w-3 text-blue-500 animate-spin" />
          )}
          {status === 'completed' && (
            <CheckCircle className="h-3 w-3 text-green-500" />
          )}
          {status === 'failed' && (
            <XCircle className="h-3 w-3 text-red-500" />
          )}
        </span>

        <ChevronDown
          className={cn(
            'h-4 w-4 text-muted-foreground transition-transform',
            expanded && 'rotate-180'
          )}
        />
      </button>

      {/* Arguments (collapsible) */}
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="mt-2 overflow-hidden"
          >
            <div className="text-xs text-muted-foreground mb-1">Arguments:</div>
            <pre className={cn(
              'bg-muted/50 p-3 rounded text-xs overflow-x-auto font-mono max-h-64',
              status === 'failed' && 'bg-red-50 dark:bg-red-900/20'
            )}>
              {formatArgs(args)}
            </pre>

            {/* Result/Error */}
            {(result !== undefined || error) && (
              <div className="mt-2">
                <div className="text-xs text-muted-foreground mb-1">
                  {error ? 'Error:' : 'Result:'}
                </div>
                <pre className={cn(
                  'bg-muted/50 p-3 rounded text-xs overflow-x-auto font-mono max-h-64',
                  error ? 'bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800' : 'bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800'
                )}>
                  {error ? error : formatResult(result)}
                </pre>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}