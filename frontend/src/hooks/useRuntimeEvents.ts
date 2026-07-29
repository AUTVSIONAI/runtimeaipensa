import { useEffect, useState } from 'react';
import { wsClient } from '@/lib/websocket';
import { useChatStore } from '@/stores/chatStore';
import { useTimelineStore } from '@/stores/timelineStore';
import type { RuntimeEvent, StreamingResponse } from '@/types/runtime';

export function useRuntimeEvents() {
  const { addMessage, addConversation, setStreaming, streaming } = useChatStore();
  const { addEvent } = useTimelineStore();

  useEffect(() => {
    const unsubscribe = wsClient.subscribe((event: RuntimeEvent) => {
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
  }, [streaming, addMessage, addConversation, addEvent, setStreaming]);
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