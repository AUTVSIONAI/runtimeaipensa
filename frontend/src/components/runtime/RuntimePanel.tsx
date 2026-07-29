'use client';

import { motion } from 'framer-motion';
import { useState } from 'react';
import { getModuleIcon, getStateColor } from '@/lib/utils';
import { cn } from '@/lib/utils';
import { useRuntimeStore } from '@/stores/runtimeStore';

export function RuntimePanel() {
  const { info, health, modules, status } = useRuntimeStore();
  const [selectedModule, setSelectedModule] = useState<string | null>(null);

  return (
    <div className="h-full flex flex-col p-4">
      {/* Runtime overview */}
      <div className="mb-6">
        <h2 className="text-lg font-semibold mb-4">Runtime Overview</h2>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <StatCard label="Runtime ID" value={info?.runtime_id || 'N/A'} />
          <StatCard label="Status" value={status} color={status === 'connected' ? 'green' : status === 'connecting' ? 'yellow' : 'red'} />
          <StatCard label="Version" value={info?.version || 'N/A'} />
          <StatCard label="Uptime" value={health?.runtime?.uptime_seconds ? `${Math.floor(health.runtime.uptime_seconds)}s` : 'N/A'} />
        </div>
      </div>

      {/* Module grid */}
      <div className="flex-1 overflow-y-auto">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-medium">Modules ({Object.keys(modules).length})</h3>
          <select
            className="text-sm border border-input rounded px-2 py-1"
            onChange={(e) => console.log(e.target.value)}
          >
            <option value="all">All Categories</option>
            <option value="core">Core</option>
            <option value="agent">Agent</option>
            <option value="orchestration">Orchestration</option>
            <option value="infrastructure">Infrastructure</option>
            <option value="ai">AI Capabilities</option>
          </select>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {Object.entries(modules).map(([name, module]) => (
            <ModuleCard
              key={name}
              name={name}
              module={module}
              isSelected={selectedModule === name}
              onClick={() => setSelectedModule(selectedModule === name ? null : name)}
            />
          ))}
        </div>
      </div>

      {/* Module detail panel */}
      {selectedModule && modules[selectedModule] && (
        <div className="mt-6 border-t border-border pt-6">
          <ModuleDetail module={modules[selectedModule]} onClose={() => setSelectedModule(null)} />
        </div>
      )}
    </div>
  );
}

function StatCard({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="p-4 bg-muted/50 rounded-lg border border-border">
      <p className="text-sm text-muted-foreground">{label}</p>
      <p className="text-2xl font-bold mt-1" style={color ? { color: `var(--${color})` } : undefined}>
        {value}
      </p>
    </div>
  );
}

function ModuleCard({ name, module, isSelected, onClick }: { name: string; module: any; isSelected: boolean; onClick: () => void }) {
  const meta = module.metadata || {};
  const state = module.state || 'UNINITIALIZED';
  const health = module.health;
  const Icon = getModuleIcon(name);

  return (
    <motion.div
      whileHover={{ y: -2 }}
      whileTap={{ scale: 0.98 }}
      onClick={onClick}
      className={cn(
        'p-4 rounded-lg border transition-all cursor-pointer',
        isSelected
          ? 'border-primary bg-primary/5 shadow-md'
          : 'border-border bg-card hover:border-primary/50'
      )}
    >
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-muted">
            <Icon className="h-5 w-5 text-muted-foreground" />
          </div>
          <div>
            <p className="font-medium">{meta.name || name}</p>
            <p className="text-xs text-muted-foreground">{meta.version || '1.0.0'}</p>
          </div>
        </div>
        <span
          className={cn(
            'px-2 py-1 rounded-full text-xs font-medium',
            `bg-${getStateColor(state)}-100 text-${getStateColor(state)}-700`
          )}
        >
          {state}
        </span>
      </div>

      {health && (
        <div className="mt-3 pt-3 border-t border-border">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Health:</span>
            <span className={cn('font-medium', health.healthy ? 'text-green-600' : 'text-red-600')}>
              {health.healthy ? 'Healthy' : 'Unhealthy'}
            </span>
          </div>
          {health.details && (
            <div className="mt-2 text-xs text-muted-foreground font-mono max-h-20 overflow-auto">
              {JSON.stringify(health.details, null, 2)}
            </div>
          )}
        </div>
      )}
    </motion.div>
  );
}

function ModuleDetail({ module, onClose }: { module: any; onClose: () => void }) {
  const meta = module.metadata || {};
  const state = module.state || 'UNINITIALIZED';
  const health = module.health;

  return (
    <div className="p-4 bg-muted/30 rounded-lg border border-border">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-medium">Module Details: {meta.name || 'Unknown'}</h3>
        <button onClick={onClose} className="p-1 hover:bg-border rounded">✕</button>
      </div>

      <div className="grid grid-cols-2 gap-4 text-sm">
        <div>
          <span className="text-muted-foreground">Author:</span>
          <p className="font-medium">{meta.author || 'N/A'}</p>
        </div>
        <div>
          <span className="text-muted-foreground">Dependencies:</span>
          <p className="font-medium">{meta.dependencies?.join(', ') || 'None'}</p>
        </div>
        <div>
          <span className="text-muted-foreground">Provides:</span>
          <p className="font-medium">{meta.provides?.join(', ') || 'None'}</p>
        </div>
        <div>
          <span className="text-muted-foreground">Tags:</span>
          <p className="font-medium">{meta.tags?.join(', ') || 'None'}</p>
        </div>
        <div className="col-span-2">
          <span className="text-muted-foreground block mb-1">Description:</span>
          <p>{meta.description || 'No description'}</p>
        </div>
        <div className="col-span-2">
          <span className="text-muted-foreground block mb-1">Current State:</span>
          <span className={cn('font-medium px-2 py-1 rounded', `bg-${getStateColor(state)}-100 text-${getStateColor(state)}-700`)}>{state}</span>
        </div>

        {health && (
          <div className="col-span-2">
            <span className="text-muted-foreground block mb-1">Health Check:</span>
            <pre className="text-xs bg-muted p-2 rounded max-h-40 overflow-auto">{JSON.stringify(health, null, 2)}</pre>
          </div>
        )}
      </div>
    </div>
  );
}