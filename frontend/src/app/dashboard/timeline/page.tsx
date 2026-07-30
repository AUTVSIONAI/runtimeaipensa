'use client';

import { useTimelineStore } from '@/stores/timelineStore';
import { useUIStore } from '@/stores/uiStore';
import { cn, formatTimestamp, getEventTypeColor } from '@/lib/utils';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, Filter, X, ChevronDown, ChevronRight, Copy, Download, MoreVertical } from 'lucide-react';
import { useState, useMemo, useEffect } from 'react';
import type { RuntimeEvent } from '@/types/runtime';

const EVENT_CATEGORIES = [
  'RUNTIME', 'MODULE', 'TASK', 'AGENT', 'CONVERSATION', 'MESSAGE',
  'WORKFLOW', 'JOB', 'QUEUE', 'NOTIFICATION', 'STORAGE', 'AUTH',
  'WORKSPACE', 'KNOWLEDGE', 'SKILL', 'LLM', 'VOICE', 'VISION',
  'VIDEO', 'IMAGE', 'EMBEDDING', 'RAG', 'REASONING', 'SYSTEM',
];

export default function TimelinePage() {
  console.log('[TimelinePage] Component rendered, events count:', useTimelineStore.getState().events.length);
  const { events, filters, setFilters, selectedCorrelationId, setSelectedCorrelation } = useTimelineStore();
  const { rightPanelTab, setRightPanelTab, rightPanelOpen, setRightPanelOpen } = useUIStore();
  const [searchText, setSearchText] = useState(filters.text);
  const [expandedCorrelation, setExpandedCorrelation] = useState<string | null>(selectedCorrelationId);
  const [selectedEvent, setSelectedEvent] = useState<RuntimeEvent | null>(null);
  const [selectedCorrelationDetail, setSelectedCorrelationDetail] = useState<string | null>(null);
  const [clientLoaded, setClientLoaded] = useState(false);

  useEffect(() => {
    setClientLoaded(true);
    console.log('[TimelinePage] Client loaded, events:', events.length);
  }, [events]);

  useEffect(() => {
    console.log('[TimelinePage] Events updated:', events.length);
  }, [events]);

  const handleSearchChange = (value: string) => {
    setSearchText(value);
    setFilters({ ...filters, text: value });
  };

  const handleCategoryChange = (value: string) => {
    setFilters({ ...filters, eventTypes: value === 'all' ? [] : [value] });
  };

  const filteredEvents = useMemo(() => {
    return events.filter((event) => {
      if (filters.eventTypes.length && !filters.eventTypes.some(et => event.event_type.startsWith(et))) return false;
      if (filters.sources.length && !filters.sources.includes(event.source)) return false;
      if (filters.tags.length && !filters.tags.some(t => event.tags.includes(t))) return false;
      if (searchText && !JSON.stringify(event.payload).toLowerCase().includes(searchText.toLowerCase())) return false;
      return true;
    });
  }, [events, filters, searchText]);

  // Group by correlation ID
  const correlationGroups = useMemo(() => {
    const groups = new Map<string, RuntimeEvent[]>();
    filteredEvents.forEach((event) => {
      const group = groups.get(event.correlation_id) || [];
      group.push(event);
      groups.set(event.correlation_id, group);
    });
    return groups;
  }, [filteredEvents]);

  const isExpanded = (correlationId: string) => expandedCorrelation === correlationId;
  const toggleExpand = (correlationId: string) => {
    setExpandedCorrelation(isExpanded(correlationId) ? null : correlationId);
  };

  const handleCorrelationClick = (correlationId: string) => {
    setSelectedCorrelation(correlationId);
    toggleExpand(correlationId);
    setRightPanelTab('debug');
    setRightPanelOpen(true);
  };

  const handleEventClick = (event: RuntimeEvent) => {
    setSelectedEvent(event);
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  const exportEvents = () => {
    const data = JSON.stringify(filteredEvents, null, 2);
    const blob = new Blob([data], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `events-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="h-full flex flex-col p-4 lg:p-6">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-2xl font-bold">Event Timeline</h1>
            <p className="text-muted-foreground">Real-time EventBus stream with correlation tracking</p>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={exportEvents}>
              <Download className="h-4 w-4 mr-1" /> Export
            </Button>
            <Button variant="outline" size="sm" onClick={() => {
              setFilters({ eventTypes: [], sources: [], tags: [], text: '' });
              setSearchText('');
            }}>
              <X className="h-4 w-4 mr-1" /> Clear
            </Button>
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
          <StatCard label="Total Events" value={events.length} icon="📊" color="text-blue-500" />
          <StatCard label="Filtered" value={filteredEvents.length} icon="🔍" color="text-green-500" />
          <StatCard label="Correlations" value={correlationGroups.size} icon="🔗" color="text-purple-500" />
          <StatCard label="Events/sec" value={calculateEventsPerSecond(events)} icon="⚡" color="text-yellow-500" />
        </div>

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

          <Select value={filters.eventTypes.join(',') || 'all'} onValueChange={handleCategoryChange}>
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

          <Button variant="outline" size="sm" onClick={() => {
            setFilters({ eventTypes: [], sources: [], tags: [], text: '' });
            setSearchText('');
          }}>
            <X className="h-4 w-4 mr-1" /> Clear Filters
          </Button>
        </div>
      </div>

      {/* Event List */}
      <div className="flex-1 overflow-hidden">
        <Card className="h-full border-0 shadow-none">
          <CardContent className="p-0 h-full">
            <ScrollArea className="h-full">
              <div className="p-3 space-y-2">
                <AnimatePresence mode="popLayout">
                  {Array.from(correlationGroups.entries()).map(([correlationId, groupEvents]) => {
                    const expanded = isExpanded(correlationId);
                    const isSelected = selectedCorrelationId === correlationId;

                    return (
                      <motion.div
                        key={correlationId}
                        layout
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        className={cn(
                          'border border-border rounded-lg overflow-hidden transition-all',
                          isSelected && 'border-primary/50 bg-primary/5'
                        )}
                      >
                        {/* Correlation Header */}
                        <button
                          onClick={() => handleCorrelationClick(correlationId)}
                          className={cn(
                            'w-full flex items-center justify-between p-3 transition-colors',
                            'hover:bg-accent',
                            isSelected && 'bg-primary/10'
                          )}
                        >
                          <div className="flex items-center gap-3">
                            <ChevronRight
                              className={cn('h-4 w-4 text-muted-foreground transition-transform', expanded && 'rotate-90')}
                            />
                            <div className="flex items-center gap-2">
                              <span className="px-2 py-0.5 rounded text-xs font-medium bg-muted text-muted-foreground">
                                {groupEvents.length} events
                              </span>
                              <span className="text-xs text-muted-foreground font-mono">
                                {correlationId.slice(0, 8)}...
                              </span>
                              <span className="text-xs text-muted-foreground">
                                {formatTimestamp(groupEvents[0].timestamp)} - {formatTimestamp(groupEvents[groupEvents.length - 1].timestamp)}
                              </span>
                            </div>
                          </div>
                          <div className="flex items-center gap-2">
                            <Badge variant="outline" className="text-xs">
                              {groupEvents.length} events
                            </Badge>
                            <span
                              onClick={(e) => { e.stopPropagation(); copyToClipboard(correlationId); }}
                              className="p-1 rounded hover:bg-accent text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
                              title="Copy correlation ID"
                            >
                              <Copy className="h-4 w-4" />
                            </span>
                          </div>
                        </button>

                        {/* Expanded Events */}
                        <AnimatePresence>
                          {expanded && (
                            <motion.div
                              initial={{ opacity: 0, height: 0 }}
                              animate={{ opacity: 1, height: 'auto' }}
                              exit={{ opacity: 0, height: 0 }}
                              className="border-t border-border bg-muted/30"
                            >
                              <div className="p-2 space-y-1">
                                {groupEvents.map((event, idx) => (
                                  <EventItem
                                    key={`${correlationId}-${idx}`}
                                    event={event}
                                    index={idx}
                                    isSelected={selectedCorrelationId === correlationId}
                                    onClick={() => handleEventClick(event)}
                                  />
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
          </CardContent>
        </Card>
      </div>

      {/* Footer Stats */}
      <div className="mt-4 pt-4 border-t border-border flex items-center justify-between text-sm text-muted-foreground">
        <span>Total events: {events.length}</span>
        <span>Filtered: {filteredEvents.length}</span>
        <span>Correlations: {correlationGroups.size}</span>
      </div>

      {/* Event Detail Modal */}
      <AnimatePresence>
        {selectedEvent && (
          <div className="fixed inset-0 z-50 flex items-center justify-center">
            <div className="absolute inset-0 bg-black/50" onClick={() => setSelectedEvent(null)} />
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="relative bg-card border border-border rounded-xl max-w-3xl w-full mx-4 max-h-[80vh] overflow-hidden"
            >
              <div className="p-4 border-b border-border flex items-center justify-between">
                <h3 className="font-semibold">Event Detail</h3>
                <Button variant="ghost" size="icon" onClick={() => setSelectedEvent(null)}>
                  <X className="h-5 w-5" />
                </Button>
              </div>
              <ScrollArea className="p-4 max-h-[60vh]">
                <pre className="text-xs font-mono bg-muted p-4 rounded overflow-auto">
                  {JSON.stringify(selectedEvent, null, 2)}
                </pre>
              </ScrollArea>
              <div className="p-4 border-t border-border flex justify-end gap-2">
                <Button variant="outline" onClick={() => copyToClipboard(JSON.stringify(selectedEvent, null, 2))}>
                  <Copy className="h-4 w-4 mr-2" /> Copy JSON
                </Button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}

function StatCard({ label, value, icon, color }: { label: string; value: number; icon: string; color: string }) {
  return (
    <Card>
      <CardContent className="p-3">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs text-muted-foreground">{label}</p>
            <p className="text-2xl font-bold font-mono">{value}</p>
          </div>
          <div className={cn('text-3xl', color)}>{icon}</div>
        </div>
      </CardContent>
    </Card>
  );
}

function EventItem({ event, index, isSelected, onClick }: { event: RuntimeEvent; index: number; isSelected: boolean; onClick: () => void }) {
  const category = event.event_type.split('_')[0];
  const color = getEventTypeColor(category);

  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      onClick={onClick}
      className={cn(
        'flex gap-3 p-2 rounded transition-colors cursor-pointer',
        'hover:bg-accent',
        isSelected && 'bg-primary/10'
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
              `bg-${color}-100 text-${color}-700 dark:bg-${color}-900/30 dark:text-${color}-400`
            )}
          >
            {event.event_type}
          </span>
          <span className="text-xs text-muted-foreground font-mono">{event.source}</span>
          <span className="text-xs text-muted-foreground">{formatTimestamp(event.timestamp)}</span>
        </div>
        <div className="mt-1 text-xs text-muted-foreground font-mono truncate">
          {JSON.stringify(event.payload).slice(0, 200)}
        </div>
        {event.tags.length > 0 && (
          <div className="mt-1 flex flex-wrap gap-1">
            {event.tags.map((tag) => (
              <span key={tag} className="px-1.5 py-0.5 text-[10px] bg-muted rounded text-muted-foreground">
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

function calculateEventsPerSecond(events: RuntimeEvent[]): number {
  if (events.length < 2) return 0;
  const now = Date.now();
  const recent = events.filter(e => now - new Date(e.timestamp).getTime() < 5000);
  return Math.round(recent.length / 5);
}

function copyToClipboard(text: string) {
  navigator.clipboard.writeText(text);
}

import { ChevronUp } from 'lucide-react';