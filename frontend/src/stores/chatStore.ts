// Chat store - manages conversations, messages, and streaming state

import { create } from 'zustand';
import type { Conversation, Message, StreamingResponse } from '@/types/runtime';

interface ChatState {
  conversations: Conversation[];
  currentConversationId: string | null;
  messages: Record<string, Message[]>;
  streaming: Record<string, StreamingResponse>;
  isStreaming: boolean;

  setConversations: (conversations: Conversation[]) => void;
  addConversation: (conversation: Conversation) => void;
  setCurrentConversation: (id: string | null) => void;
  setCurrentConversationId: (id: string | null) => void; // Alias for compatibility
  setMessages: (conversationId: string, messages: Message[]) => void;
  addMessage: (conversationId: string, message: Message) => void;
  updateStreaming: (conversationId: string, chunk: StreamingResponse) => void;
  clearStreaming: (conversationId: string) => void;
  setStreaming: (streaming: boolean) => void;
  clearAll: () => void;
}

// Disable devtools in Next.js to avoid ActionQueueContext error
const useDevtools = process.env.NODE_ENV === 'development' && typeof window !== 'undefined';

export const useChatStore = create<ChatState>()(
  useDevtools
    ? (set) => ({
        conversations: [],
        currentConversationId: null,
        messages: {},
        streaming: {},
        isStreaming: false,

        setConversations: (conversations) => set({ conversations }),
        addConversation: (conversation) =>
          set((state) => ({ conversations: [conversation, ...state.conversations] })),
        setCurrentConversation: (currentConversationId) => set({ currentConversationId }),
        setCurrentConversationId: (currentConversationId) => set({ currentConversationId }),
        setMessages: (conversationId, messages) =>
          set((state) => ({ messages: { ...state.messages, [conversationId]: messages } })),
        addMessage: (conversationId, message) =>
          set((state) => ({
            messages: {
              ...state.messages,
              [conversationId]: [...(state.messages[conversationId] || []), message],
            },
          })),
        updateStreaming: (conversationId, chunk) =>
          set((state) => ({ streaming: { ...state.streaming, [conversationId]: chunk } })),
        clearStreaming: (conversationId) =>
          set((state) => {
            const newStreaming = { ...state.streaming };
            delete newStreaming[conversationId];
            return { streaming: newStreaming };
          }),
        setStreaming: (isStreaming) => set({ isStreaming }),
        clearAll: () =>
          set({
            conversations: [],
            currentConversationId: null,
            messages: {},
            streaming: {},
            isStreaming: false,
          }),
      })
    : (set) => ({
        conversations: [],
        currentConversationId: null,
        messages: {},
        streaming: {},
        isStreaming: false,

        setConversations: (conversations) => set({ conversations }),
        addConversation: (conversation) =>
          set((state) => ({ conversations: [conversation, ...state.conversations] })),
        setCurrentConversation: (currentConversationId) => set({ currentConversationId }),
        setCurrentConversationId: (currentConversationId) => set({ currentConversationId }),
        setMessages: (conversationId, messages) =>
          set((state) => ({ messages: { ...state.messages, [conversationId]: messages } })),
        addMessage: (conversationId, message) =>
          set((state) => ({
            messages: {
              ...state.messages,
              [conversationId]: [...(state.messages[conversationId] || []), message],
            },
          })),
        updateStreaming: (conversationId, chunk) =>
          set((state) => ({ streaming: { ...state.streaming, [conversationId]: chunk } })),
        clearStreaming: (conversationId) =>
          set((state) => {
            const newStreaming = { ...state.streaming };
            delete newStreaming[conversationId];
            return { streaming: newStreaming };
          }),
        setStreaming: (isStreaming) => set({ isStreaming }),
        clearAll: () =>
          set({
            conversations: [],
            currentConversationId: null,
            messages: {},
            streaming: {},
            isStreaming: false,
          }),
      })
);