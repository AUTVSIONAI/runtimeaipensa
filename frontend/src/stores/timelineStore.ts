// Timeline store - manages event stream and correlation tracking

import { create } from 'zustand';
import type { RuntimeEvent, EventFilters } from '@/types/runtime';

interface TimelineState {
  events: RuntimeEvent[];
  filters: EventFilters;
  correlationMap: Map<string, RuntimeEvent[]>;
  selectedCorrelationId: string | null;

  addEvent: (event: RuntimeEvent) => void;
  setFilters: (filters: EventFilters) => void;
  clearEvents: () => void;
  setSelectedCorrelation: (id: string | null) => void;
}

// Disable devtools in Next.js to avoid ActionQueueContext error
const useDevtools = process.env.NODE_ENV === 'development' && typeof window !== 'undefined';

export const useTimelineStore = create<TimelineState>()(
  useDevtools
    ? (set) => ({
        events: [],
        filters: {
          eventTypes: [],
          sources: [],
          tags: [],
          text: '',
        },
        correlationMap: new Map(),
        selectedCorrelationId: null,

        addEvent: (event) =>
          set((state) => {
            const newEvents = [...state.events, event].slice(-10000);

            // Update correlation map
            const newMap = new Map(state.correlationMap);
            const corrEvents = newMap.get(event.correlation_id) || [];
            corrEvents.push(event);
            newMap.set(event.correlation_id, corrEvents);

            return { events: newEvents, correlationMap: newMap };
          }),

        setFilters: (filters) => set({ filters }),

        clearEvents: () => set({ events: [], correlationMap: new Map() }),

        setSelectedCorrelation: (selectedCorrelationId) => set({ selectedCorrelationId }),
      })
    : (set) => ({
        events: [],
        filters: {
          eventTypes: [],
          sources: [],
          tags: [],
          text: '',
        },
        correlationMap: new Map(),
        selectedCorrelationId: null,

        addEvent: (event) =>
          set((state) => {
            const newEvents = [...state.events, event].slice(-10000);

            // Update correlation map
            const newMap = new Map(state.correlationMap);
            const corrEvents = newMap.get(event.correlation_id) || [];
            corrEvents.push(event);
            newMap.set(event.correlation_id, corrEvents);

            return { events: newEvents, correlationMap: newMap };
          }),

        setFilters: (filters) => set({ filters }),

        clearEvents: () => set({ events: [], correlationMap: new Map() }),

        setSelectedCorrelation: (selectedCorrelationId) => set({ selectedCorrelationId }),
      })
);