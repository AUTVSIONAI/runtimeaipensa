'use client';

import { cn } from '@/lib/utils';
import { Code2, AlertTriangle, X, Check, Loader2 } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';

interface ApprovalRequest {
  call_id: string;
  name: string;
  arguments: Record<string, any>;
  description?: string;
}

interface ApprovalModalProps {
  request: ApprovalRequest | null;
  onApprove: (callId: string, approved: boolean) => void;
  isLoading?: boolean;
}

export function ApprovalModal({ request, onApprove, isLoading = false }: ApprovalModalProps) {
  if (!request) return null;

  const formatArgs = (obj: Record<string, any>) => {
    return JSON.stringify(obj, null, 2);
  };

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
        onClick={() => onApprove(request.call_id, false)}
      >
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 20 }}
          className="bg-card border border-border rounded-xl shadow-xl max-w-2xl w-full max-h-[80vh] overflow-hidden"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex items-center gap-3 p-4 border-b border-border bg-muted/50">
            <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-yellow-100 dark:bg-yellow-900/30 flex items-center justify-center">
              <AlertTriangle className="h-5 w-5 text-yellow-600 dark:text-yellow-400" />
            </div>
            <div className="flex-1 min-w-0">
              <h3 className="font-semibold text-foreground">Approval Required</h3>
              <p className="text-sm text-muted-foreground">
                The agent wants to execute <code className="bg-muted px-1.5 py-0.5 rounded text-sm font-mono">{request.name}</code>
              </p>
            </div>
            <span className="text-xs text-muted-foreground font-mono">{request.call_id}</span>
          </div>

          {/* Content */}
          <div className="p-4 space-y-4 max-h-[60vh] overflow-y-auto">
            {/* Description */}
            {request.description && (
              <div className="p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
                <p className="text-sm text-blue-800 dark:text-blue-200">{request.description}</p>
              </div>
            )}

            {/* Arguments */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <h4 className="text-sm font-medium text-foreground">Arguments</h4>
                <Code2 className="h-4 w-4 text-muted-foreground" />
              </div>
              <ScrollArea className="max-h-64">
                <pre className={cn(
                  'bg-muted/50 p-3 rounded text-xs overflow-x-auto font-mono',
                  'text-foreground'
                )}>
                  {formatArgs(request.arguments)}
                </pre>
              </ScrollArea>
            </div>

            {/* Warning */}
            <div className="flex items-start gap-2 p-3 bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800 rounded-lg">
              <AlertTriangle className="h-4 w-4 text-orange-600 dark:text-orange-400 flex-shrink-0 mt-0.5" />
              <div className="text-sm text-orange-800 dark:text-orange-200">
                <p className="font-medium">This action cannot be undone</p>
                <p>Please review the tool and arguments carefully before approving.</p>
              </div>
            </div>
          </div>

          {/* Footer */}
          <div className="flex items-center justify-end gap-3 p-4 border-t border-border bg-muted/50">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onApprove(request.call_id, false)}
              disabled={isLoading}
            >
              <X className="h-4 w-4 mr-1" />
              Deny
            </Button>
            <Button
              size="sm"
              onClick={() => onApprove(request.call_id, true)}
              disabled={isLoading}
              className="gap-2"
            >
              {isLoading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Approving...
                </>
              ) : (
                <>
                  <Check className="h-4 w-4" />
                  Approve
                </>
              )}
            </Button>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}