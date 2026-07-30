import { useEffect, useState } from 'react';
import { wsClient } from '@/lib/websocket';
import { api } from '@/lib/api';
import { useChatStore } from '@/stores/chatStore';
import { useTimelineStore } from '@/stores/timelineStore';
import type { RuntimeEvent, StreamingResponse } from '@/types/runtime';

export function useRuntimeEvents() {
  const { addMessage, addConversation, setStreaming, streaming } = useChatStore();
  const { addEvent } = useTimelineStore();

  console.log('[useRuntimeEvents] ========================================');
  console.log('[useRuntimeEvents] Hook called, streaming:', streaming);
  console.log('[useRuntimeEvents] addEvent function:', typeof addEvent);
  console.log('[useRuntimeEvents] Running on client:', typeof window !== 'undefined');

  // Load historical events on first mount - separate effect with empty deps
  useEffect(() => {
    console.log('[useRuntimeEvents] History loading effect triggered');
    let mounted = true;
    const loadHistory = async () => {
      try {
        console.log('[useRuntimeEvents] Loading event history...');
        const res = await api.getEventHistory(1000);
        console.log('[useRuntimeEvents] History response status:', res ? 'ok' : 'null');
        console.log('[useRuntimeEvents] History response events:', res?.events?.length || 0);
        if (!mounted) return;
        if (res.events && res.events.length > 0) {
          res.events.forEach((event: RuntimeEvent) => addEvent(event));
          console.log(`[useRuntimeEvents] Loaded ${res.events.length} historical events`);
          console.log('[useRuntimeEvents] Timeline store events after load:', useTimelineStore.getState().events.length);
        } else {
          console.log('[useRuntimeEvents] No events in history');
        }
      } catch (e) {
        console.error('[useRuntimeEvents] Failed to load event history:', e);
      }
    };
    loadHistory();
    return () => { mounted = false; };
  }, []); // Run once on mount - addEvent is stable from Zustand

  // WebSocket subscription for real-time events
  useEffect(() => {
    const unsubscribe = wsClient.subscribe((event: RuntimeEvent) => {
      console.log('[useRuntimeEvents] Received event:', event.event_type, 'source:', event.source, 'corr:', event.correlation_id?.slice(0, 8));
      // Add to timeline
      addEvent(event);

      // Handle conversation events
      if (event.event_type === 'ConversationStarted') {
        const payload = event.payload;
        const conversation = {
          conversation_id: payload.conversation_id,
          title: payload.title,
          messages: [],
          system_prompt: payload.system_prompt,
          context: payload.context || {},
          metadata: {},
          created_at: event.timestamp,
          updated_at: event.timestamp,
          max_messages: 100,
          max_tokens: 8000,
        };
        addConversation(conversation);
      }

      // Handle message events - BUT skip if we're currently streaming for that conversation
      // (chat page handles streaming messages explicitly to avoid duplicates)
      if (event.event_type === 'MessageReceived' || event.event_type === 'MessageSent') {
        const messageData = event.payload;
        const conversationId = messageData.conversation_id;

        if (conversationId) {
          // Check if we're currently streaming for this conversation
          const isStreamingForConv = streaming[conversationId] && !streaming[conversationId].done;

          // Don't duplicate messages that are being handled by streaming
          if (!isStreamingForConv) {
            const message = {
              message_id: messageData.message_id,
              role: messageData.role,
              content: messageData.content,
              type: messageData.message_type,
              tool_calls: messageData.tool_calls || [],
              tool_call_id: messageData.tool_call_id,
              name: messageData.name,
              metadata: messageData.metadata || {},
              timestamp: event.timestamp,
              conversation_id: conversationId,
            };
            addMessage(conversationId, message);
          }
        }
      }

      // Handle streaming events
      if (event.event_type === 'StreamingChunk') {
        const payload = event.payload;
        if (payload.conversation_id) {
          const chunk: StreamingResponse = {
            conversation_id: payload.conversation_id,
            chunk: payload.chunk || '',
            done: payload.done || false,
            metadata: payload.metadata || {},
          };
          useChatStore.getState().updateStreaming(payload.conversation_id, chunk);
        }
      }
    });

    wsClient.connect();

    return () => {
      unsubscribe();
    };
  }, []); // Run once on mount - wsClient.subscribe is stable, handlers use getState()
}

export function useRuntimeConnection() {
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    const checkConnection = () => {
      setConnected(wsClient.isConnected);
    };

    const interval = setInterval(checkConnection, 1000);
    checkConnection();

    return () => clearInterval(interval);
  }, []);

  return connected;
}