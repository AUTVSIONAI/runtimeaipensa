'use client';

import { useTimelineStore } from '@/stores/timelineStore';
import { cn, formatTimestamp, getEventTypeColor } from '@/lib/utils';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, Filter, X, ChevronDown, ChevronRight, Copy } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useState, useMemo } from 'react';
import type { RuntimeEvent } from '@/types/runtime';

// Map event sources to display categories
const EVENT_SOURCE_CATEGORIES = [
  'runtime', 'module', 'task', 'agent', 'conversation', 'message',
  'workflow', 'job', 'queue', 'notification', 'storage', 'auth',
  'workspace', 'knowledge', 'skill', 'llm', 'voice', 'vision',
  'video', 'image', 'embedding', 'rag', 'reasoning', 'system',
];

const EVENT_CATEGORIES = EVENT_SOURCE_CATEGORIES.map(c => c.toUpperCase());

function EventItem({ event, onSelect }: { event: RuntimeEvent; onSelect: (id: string) => void }) {
  const isSelected = event.correlation_id === useTimelineStore.getState().selectedCorrelationId;

  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      layout
      onClick={() => onSelect(event.correlation_id)}
      className={cn(
        'flex gap-3 p-3 rounded-lg transition-colors cursor-pointer',
        'hover:bg-accent',
        isSelected && 'bg-primary/10 border-l-2 border-primary'
      )}
    >
      <div className="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-xs font-mono text-muted-foreground">
        {formatTimestamp(event.timestamp).split(':')[2]?.slice(0, 2)}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span
            className={cn(
              'px-2 py-0.5 rounded text-xs font-medium',
              `bg-${getEventTypeColor(event.event_type)}-100`,
              `text-${getEventTypeColor(event.event_type)}-700`,
              'dark:bg-${getEventTypeColor(event.event_type)}-900/30',
              'dark:text-${getEventTypeColor(event.event_type)}-400'
            )}
          >
            {event.event_type}
          </span>
          <span className="text-xs text-muted-foreground font-mono">{event.source}</span>
          <span className="text-xs text-muted-foreground">{formatTimestamp(event.timestamp)}</span>
        </div>
        <div className="mt-1 text-sm text-muted-foreground font-mono truncate">
          {JSON.stringify(event.payload).slice(0, 100)}
        </div>
        {event.tags.length > 0 && (
          <div className="mt-1 flex flex-wrap gap-1">
            {event.tags.map((tag) => (
              <span key={tag} className="px-1.5 py-0.5 text-xs bg-muted rounded text-muted-foreground">
                {tag}
              </span>
            ))}
          </div>
        )}
      </div>
      <ChevronRight className="text-muted-foreground h-4 w-4 flex-shrink-0" />
    </motion.div>
  );
}

export function TimelinePanel() {
  const { events, filters, setFilters, selectedCorrelationId, setSelectedCorrelation } = useTimelineStore();
  const [searchText, setSearchText] = useState(filters.text);
  const [expandedCorrelation, setExpandedCorrelation] = useState<string | null>(selectedCorrelationId);

  const filteredEvents = useMemo(() => {
    return events.filter((event) => {
      if (filters.eventTypes.length > 0 && !filters.eventTypes.some(et => event.source.toUpperCase().startsWith(et.toUpperCase()))) return false;
      if (filters.sources.length > 0 && !filters.sources.includes(event.source)) return false;
      if (filters.tags.length > 0 && !filters.tags.some(t => event.tags.includes(t))) return false;
      if (searchText && !JSON.stringify(event.payload).toLowerCase().includes(searchText.toLowerCase())) return false;
      return true;
    });
  }, [events, filters, searchText]);

  // Group by correlation ID for correlation view
  const correlationGroups = useMemo(() => {
    const groups = new Map<string, RuntimeEvent[]>();
    filteredEvents.forEach((event) => {
      const group = groups.get(event.correlation_id) || [];
      group.push(event);
      groups.set(event.correlation_id, group);
    });
    return groups;
  }, [filteredEvents]);

  const handleSearchChange = (value: string) => {
    setSearchText(value);
    setFilters({ ...filters, text: value });
  };

  return (
    <div className="h-full flex flex-col p-4">
      {/* Toolbar */}
      <div className="flex flex-wrap gap-2 mb-4">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Filter events..."
            value={searchText}
            onChange={(e) => handleSearchChange(e.target.value)}
            className="pl-9"
          />
        </div>

        <Select value={filters.eventTypes.join(',') || 'all'} onValueChange={(v) => setFilters({ ...filters, eventTypes: v === 'all' ? [] : [v] })}>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="Event Category" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Categories</SelectItem>
            {EVENT_CATEGORIES.map((cat) => (
              <SelectItem key={cat} value={cat}>{cat}</SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Button variant="outline" size="sm" onClick={() => { setFilters({ eventTypes: [], sources: [], tags: [], text: '' }); setSearchText(''); }}>
          <X className="h-4 w-4 mr-1" /> Clear
        </Button>
      </div>

      {/* Event List */}
      <ScrollArea className="flex-1">
        <div className="space-y-1">
          <AnimatePresence mode="popLayout">
            {Array.from(correlationGroups.entries()).map(([correlationId, groupEvents]) => {
              const isExpanded = expandedCorrelation === correlationId;
              const isSelected = selectedCorrelationId === correlationId;

              return (
                <motion.div
                  key={correlationId}
                  layout
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  className={cn('border border-border rounded-lg overflow-hidden', isSelected && 'border-primary/50 bg-primary/5')}
                >
                  {/* Correlation header */}
                  <button
                    onClick={() => {
                      setExpandedCorrelation(isExpanded ? null : correlationId);
                      setSelectedCorrelation(correlationId);
                    }}
                    className={cn(
                      'w-full flex items-center justify-between p-3 transition-colors',
                      'hover:bg-accent',
                      isSelected && 'bg-primary/10'
                    )}
                  >
                    <div className="flex items-center gap-3">
                      <ChevronDown
                        className={cn('h-4 w-4 text-muted-foreground transition-transform', isExpanded && 'rotate-90')}
                      />
                      <div className="flex items-center gap-2">
                        <span className="px-2 py-0.5 rounded text-xs font-medium bg-muted text-muted-foreground">
                          {groupEvents.length} events
                        </span>
                        <span className="text-xs text-muted-foreground font-mono font-mono">
                          {correlationId.slice(0, 8)}...
                        </span>
                        <span className="text-xs text-muted-foreground">
                          {formatTimestamp(groupEvents[0].timestamp)} - {formatTimestamp(groupEvents[groupEvents.length - 1].timestamp)}
                        </span>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="px-2 py-0.5 text-xs bg-muted rounded text-muted-foreground">
                        {groupEvents.length} events
                      </span>
                      <Button variant="ghost" size="icon" onClick={(e) => { e.stopPropagation(); navigator.clipboard.writeText(correlationId); }}>
                        <Copy className="h-4 w-4" />
                      </Button>
                    </div>
                  </button>

                  {/* Expanded events */}
                  <AnimatePresence>
                    {isExpanded && (
                      <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        className="border-t border-border bg-muted/30"
                      >
                        <div className="p-2 space-y-1">
                          {groupEvents.map((event, idx) => (
                            <EventItem key={`${correlationId}-${idx}`} event={event} onSelect={setSelectedCorrelation} />
                          ))}
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </motion.div>
              );
            })}
          </AnimatePresence>

          {filteredEvents.length === 0 && correlationGroups.size === 0 && (
            <div className="flex items-center justify-center h-64 text-muted-foreground">
              <div className="text-center">
                <Filter className="mx-auto h-12 w-12 text-muted-foreground/50" />
                <p className="mt-4">No events match your filters</p>
                <p className="text-sm">Try adjusting your filters or wait for new events</p>
              </div>
            </div>
          )}
        </div>
      </ScrollArea>

      {/* Stats/footer */}
      <div className="mt-4 pt-4 border-t border-border flex items-center justify-between text-sm text-muted-foreground">
        <span>Total events: {events.length}</span>
        <span>Filtered: {filteredEvents.length}</span>
        <span>Correlations: {correlationGroups.size}</span>
      </div>
    </div>
  );
}