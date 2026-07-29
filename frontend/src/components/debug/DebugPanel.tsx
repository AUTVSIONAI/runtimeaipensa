'use client';

import { useDebugStore } from '@/stores/debugStore';
import { useRuntimeStore } from '@/stores/runtimeStore';
import { ScrollArea } from '@/components/ui/scroll-area';
import { formatTimestamp } from '@/lib/utils';
import { Button } from '@/components/ui/button';

export function DebugPanel() {
  const { logs, addLog, clearLogs, snapshots, takeSnapshot } = useDebugStore();
  const { modules, health } = useRuntimeStore();

  return (
    <div className="h-full flex flex-col p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-medium">Debug Panel</h3>
        <div className="flex gap-2">
          <Button variant="secondary" size="sm" onClick={takeSnapshot}>
            Take Snapshot
          </Button>
          <Button variant="secondary" size="sm" onClick={clearLogs}>
            Clear Logs
          </Button>
        </div>
      </div>

      <div className="flex-1 bg-muted/30 rounded-lg border border-border overflow-hidden flex">
        {/* Logs panel */}
        <div className="flex-1 flex flex-col border-r border-border">
          <div className="px-3 py-2 border-b border-border font-medium">Runtime Logs</div>
          <ScrollArea className="flex-1 p-2 space-y-1 font-mono text-xs">
            {logs.length === 0 && (
              <div className="text-center text-muted-foreground py-8">No logs yet</div>
            )}
            {logs.map((log, idx) => (
              <div
                key={idx}
                className={`px-2 py-1 rounded ${log.level === 'error' && 'bg-red-500/10 text-red-400'}`}
              >
                <span className="text-muted-foreground">[{formatTimestamp(log.timestamp)}]</span>
                <span className="mx-2 text-yellow-400">[{log.level.toUpperCase()}]</span>
                <span className="text-blue-400">{log.source}:</span>
                <span>{log.message}</span>
              </div>
            ))}
          </ScrollArea>
        </div>

        {/* State inspector */}
        <div className="w-96 flex flex-col border-r border-border">
          <div className="px-3 py-2 border-b border-border font-medium">State Inspector</div>
          <ScrollArea className="flex-1 p-2 space-y-4">
            <div>
              <h4 className="font-medium text-sm mb-2">Runtime Info</h4>
              <pre className="text-xs bg-muted p-2 rounded max-h-40 overflow-auto">
                {JSON.stringify({ modules: Object.keys(modules) }, null, 2)}
              </pre>
            </div>
            <div>
              <h4 className="font-medium text-sm mb-2">Module Health</h4>
              <pre className="text-xs bg-muted p-2 rounded max-h-40 overflow-auto">
                {JSON.stringify(health?.modules || {}, null, 2)}
              </pre>
            </div>
          </ScrollArea>
        </div>

        {/* Snapshots */}
        <div className="w-96 flex flex-col">
          <div className="px-3 py-2 border-b border-border font-medium">Snapshots ({snapshots.length})</div>
          <ScrollArea className="flex-1 p-2 space-y-2">
            {snapshots.length === 0 && (
              <div className="text-center text-muted-foreground py-8">No snapshots</div>
            )}
            {snapshots.slice().reverse().map((snap) => (
              <div key={snap.id} className="p-2 bg-muted rounded text-xs">
                <div className="font-medium">{snap.id}</div>
                <div className="text-muted-foreground">{formatTimestamp(snap.timestamp)}</div>
                <div className="text-muted-foreground">Convs: {snap.conversationCount} | Workflows: {snap.activeWorkflows}</div>
              </div>
            ))}
          </ScrollArea>
        </div>
      </div>
    </div>
  );
}