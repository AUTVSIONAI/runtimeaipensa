'use client';

import { cn } from '@/lib/utils';
import { useChatStore } from '@/stores/chatStore';
import { useRuntimeStore } from '@/stores/runtimeStore';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Avatar } from '@/components/layout/Avatar';
import { Separator } from '@/components/ui/separator';
import {
  Send,
  Bot,
  User,
  RotateCcw,
  Plus,
  Trash2,
  Sparkles,
  ChevronDown,
  Shield,
  Globe,
  Code2,
  Search,
  FileText,
  Terminal,
  Wrench,
  Settings,
  X,
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useState, useRef, useEffect, useCallback } from 'react';
import { api } from '@/lib/api';
import type { Message, Conversation } from '@/types/runtime';
import { ToolCallDisplay } from '@/components/chat/ToolCallDisplay';
import { ApprovalModal } from '@/components/chat/ApprovalModal';

interface AgentEvent {
  event_type: string;
  timestamp: string;
  iteration: number;
  data: Record<string, any>;
}

interface ToolCallInfo {
  call_id: string;
  name: string;
  arguments: Record<string, any>;
  status: 'pending' | 'running' | 'completed' | 'failed';
  result?: any;
  error?: string;
}

interface ApprovalRequest {
  call_id: string;
  name: string;
  arguments: Record<string, any>;
  description?: string;
}

const defaultSkills = [
  'web-search',
  'code-executor',
  'browser-automation',
  'file-operations',
];

// Map skill IDs to actual tool names
const skillToTools: Record<string, string[]> = {
  'web-search': ['web_search'],
  'code-executor': ['execute_python', 'execute_shell'],
  'browser-automation': [], // Browser tools might be separate
  'file-operations': ['read_file', 'write_file', 'list_files'],
  'terminal': ['execute_shell'],
  'tool-manager': [], // Tool manager might use a different mechanism
};

export function ChatPanel() {
  const {
    conversations,
    currentConversationId,
    messages,
    streaming,
    isStreaming,
    setConversations,
    addConversation,
    setCurrentConversation,
    setMessages,
    addMessage,
    updateStreaming,
    clearStreaming,
    setStreaming,
  } = useChatStore();

  const [input, setInput] = useState('');
  const [newConvTitle, setNewConvTitle] = useState('');
  const [showNewConv, setShowNewConv] = useState(false);
  const [selectedModel, setSelectedModel] = useState('meta/llama-3.1-70b-instruct');
  const [showModelSelector, setShowModelSelector] = useState(false);
  const [availableModels, setAvailableModels] = useState<string[]>([
    'meta/llama-3.1-70b-instruct',
    'meta/llama-3.1-405b-instruct',
    'mistral-large-2-instruct',
    'nvidia/nemotron-3-ultra',
  ]);
  const [isLoadingModels, setIsLoadingModels] = useState(false);
  const [useAgentMode, setUseAgentMode] = useState(true); // New: toggle agent mode
  const [approvalRequest, setApprovalRequest] = useState<ApprovalRequest | null>(null);
  const [isApproving, setIsApproving] = useState(false);
  const [toolCalls, setToolCalls] = useState<Record<string, ToolCallInfo>>({});
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Skills/Abilities menu state
  const [showSkillsMenu, setShowSkillsMenu] = useState(false);
  const [selectedSkill, setSelectedSkill] = useState<string | null>(null);
  const [activeSkills, setActiveSkills] = useState<string[]>(() => {
    // Initialize from localStorage if available
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem('aipensa.activeSkills');
      if (stored) {
        try {
          return JSON.parse(stored);
        } catch {
          return defaultSkills;
        }
      }
    }
    return defaultSkills;
  });

  // Persist activeSkills to localStorage
  useEffect(() => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('aipensa.activeSkills', JSON.stringify(activeSkills));
    }
  }, [activeSkills]);

  const currentConv = conversations.find(c => c.conversation_id === currentConversationId);
  const currentMessages = currentConversationId ? messages[currentConversationId] || [] : [];
  const currentStream = currentConversationId ? streaming[currentConversationId] : undefined;

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [currentMessages, currentStream]);

  const loadModels = useCallback(async () => {
    setIsLoadingModels(true);
    try {
      const res = await api.listModels();
      const models = (res.models?.map((m: any) => m.model_id || m.id) || [])
        .filter((modelId: string) => !modelId.includes('405b'));
      if (models.length > 0) {
        setAvailableModels(models);
        if (!models.includes(selectedModel)) {
          setSelectedModel(models[0]);
        }
      }
    } catch (e) {
      console.error('Failed to load models:', e);
    } finally {
      setIsLoadingModels(false);
    }
  }, [selectedModel]);

  const loadMessages = useCallback(async (convId: string) => {
    try {
      const data = await api.getMessages(convId);
      setMessages(convId, data.messages);
    } catch (e) {
      console.error('Failed to load messages:', e);
    }
  }, [setMessages]);

  const loadConversations = useCallback(async () => {
    try {
      const data = await api.listConversations();
      setConversations(data.conversations);
      if (data.conversations.length > 0 && !currentConversationId) {
        setCurrentConversation(data.conversations[0].conversation_id);
        loadMessages(data.conversations[0].conversation_id);
      }
    } catch (e) {
      console.error('Failed to load conversations:', e);
    }
  }, [currentConversationId, setConversations, setCurrentConversation, loadMessages]);

  // Load conversations and models on mount
  useEffect(() => {
    loadConversations();
    loadModels();
  }, [loadConversations, loadModels]);

  const handleNewConversation = async () => {
    if (!newConvTitle.trim()) return;
    try {
      const conv = await api.createConversation({ title: newConvTitle });
      addConversation(conv);
      setCurrentConversation(conv.conversation_id);
      setMessages(conv.conversation_id, []);
      setNewConvTitle('');
      setShowNewConv(false);
    } catch (e) {
      console.error('Failed to create conversation:', e);
    }
  };

  const handleConversationSelect = (convId: string) => {
    setCurrentConversation(convId);
    loadMessages(convId);
  };

  const handleSend = async () => {
    if (!input.trim() || !currentConversationId) return;

    const userMessage = input;
    setInput('');
    setStreaming(true);
    // Clear tool calls for new message
    setToolCalls({});

    // Add user message to conversation FIRST (optimistic + backend)
    const userMsg: Message = {
      message_id: `user-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      role: 'user',
      content: userMessage,
      type: 'text',
      timestamp: new Date().toISOString(),
      tool_calls: [],
      tool_call_id: null,
      name: null,
      metadata: {},
    };
    console.log('[ChatPanel] Adding user message:', userMsg);
    addMessage(currentConversationId, userMsg);

    // Also persist to backend - MUST complete before agent stream reads conversation
    try {
      console.log('[ChatPanel] Persisting user message to backend...');
      await api.addMessage(currentConversationId, {
        role: 'user',
        content: userMessage,
        message_type: 'text'
      });
      console.log('[ChatPanel] User message persisted successfully');
    } catch (e) {
      console.error('[ChatPanel] Failed to persist user message:', e);
      // Don't proceed if backend failed - agent won't see the message
    }

    // Stream response from agent loop (or fallback to simple LLM)
    if (useAgentMode) {
      console.log('[ChatPanel] Starting agent stream...');
      // Map active skills to actual tool names
      const skillToTools: Record<string, string[]> = {
        'web-search': ['web_search'],
        'code-executor': ['execute_python', 'execute_shell'],
        'browser-automation': ['browser_navigate', 'browser_click', 'browser_type', 'browser_screenshot', 'browser_get_state'],
        'file-operations': ['read_file', 'write_file', 'list_files'],
        'terminal': ['execute_shell'],
        'tool-manager': [], // Tool manager uses a different API
      };
      const availableTools = activeSkills.flatMap(skill => skillToTools[skill] || []);
      await streamAgentResponse(userMessage, availableTools);
    } else {
      console.log('[ChatPanel] Starting simple stream...');
      await streamSimpleResponse(userMessage);
    }
  };

  const streamAgentResponse = async (userMessage: string, availableTools: string[] = []) => {
    if (!currentConversationId) return;

    let accumulatedContent = '';

    try {
      for await (const event of api.agentStream(currentConversationId, {
        message: userMessage,
        model: selectedModel,
        temperature: 0.7,
        max_tokens: 4096,
        max_iterations: 10,
        require_approval: true,
        available_tools: availableTools,
      })) {
        const accRef = { current: accumulatedContent };
        handleAgentEvent(event, (content) => { accumulatedContent = content; }, accRef);
      }

      // Add final assistant message
      const assistantMsg: Message = {
        message_id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: accumulatedContent,
        type: 'text',
        timestamp: new Date().toISOString(),
        tool_calls: [],
        tool_call_id: null,
        name: null,
        metadata: {},
      };
      addMessage(currentConversationId, assistantMsg);
      clearStreaming(currentConversationId);

    } catch (e) {
      console.error('Agent streaming error:', e);
      const errorMsg: Message = {
        message_id: `error-${Date.now()}`,
        role: 'assistant',
        content: `Error: ${e instanceof Error ? e.message : 'Failed to get response'}`,
        type: 'text',
        timestamp: new Date().toISOString(),
        tool_calls: [],
        tool_call_id: null,
        name: null,
        metadata: {},
      };
      addMessage(currentConversationId, errorMsg);
    } finally {
      setStreaming(false);
    }
  };

  const handleAgentEvent = (
    event: AgentEvent,
    updateAccumulated: (content: string) => void,
    accumulatedContent: { current: string }
  ) => {
    switch (event.event_type) {
      case 'thinking':
        if (event.data.chunk) {
          accumulatedContent.current = accumulatedContent.current + event.data.chunk;
          updateAccumulated(accumulatedContent.current);
          // Update streaming state for UI
          updateStreaming(currentConversationId!, {
            conversation_id: event.data.conversation_id || currentConversationId!,
            chunk: event.data.chunk,
            done: false,
            metadata: event.data,
          });
        } else if (event.data.accumulated_content) {
          accumulatedContent.current = event.data.accumulated_content;
          updateAccumulated(accumulatedContent.current);
        }
        break;

      case 'tool_call_start':
        setToolCalls(prev => ({
          ...prev,
          [event.data.call_id]: {
            call_id: event.data.call_id,
            name: event.data.name,
            arguments: event.data.arguments,
            status: 'running',
          },
        }));
        break;

      case 'tool_result':
        setToolCalls(prev => {
          if (!prev[event.data.call_id]) return prev;
          return {
            ...prev,
            [event.data.call_id]: {
              ...prev[event.data.call_id],
              status: event.data.success ? 'completed' : 'failed',
              result: event.data.result,
              error: event.data.error,
            },
          };
        });
        break;

      case 'tool_call_end':
        // Final state for tool call
        break;

      case 'final':
        updateAccumulated(event.data.content || '');
        clearStreaming(currentConversationId!);
        break;

      case 'error':
        console.error('Agent error:', event.data);
        break;

      case 'approval_required':
        // Handle approval request - show modal to user
        handleApprovalRequest(event.data as { call_id: string; name: string; arguments: any; description?: string });
        break;
    }
  };

  const handleApprovalRequest = (data: { call_id: string; name: string; arguments: any; description?: string }) => {
    // Show approval modal instead of auto-approving
    setApprovalRequest({
      call_id: data.call_id,
      name: data.name,
      arguments: data.arguments,
      description: data.description,
    });
  };

  const handleApprovalResponse = async (callId: string, approved: boolean) => {
    setIsApproving(true);
    try {
      await fetch(`/api/agent/approve/${callId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ approved }),
      });
      // Update the tool call status
      setToolCalls(prev => ({
        ...prev,
        [callId]: {
          ...prev[callId],
          status: approved ? 'running' : 'failed',
          error: approved ? undefined : 'User denied tool execution',
        },
      }));
    } catch (e) {
      console.error('Approval request failed:', e);
    } finally {
      setIsApproving(false);
      setApprovalRequest(null);
    }
  };

  const streamSimpleResponse = async (userMessage: string) => {
    if (!currentConversationId) return;

    try {
      const response = await fetch(`/api/conversation/${currentConversationId}/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model: selectedModel,
          temperature: 0.7,
          max_tokens: 1024,
        }),
      });

      if (!response.ok) {
        throw new Error(`Stream failed: ${response.status}`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let accumulatedContent = '';

      if (reader) {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value, { stream: true });
          const lines = chunk.split('\n');

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6));
                if (data.chunk) {
                  accumulatedContent += data.chunk;
                  updateStreaming(currentConversationId!, {
                    conversation_id: data.conversation_id,
                    chunk: data.chunk,
                    done: data.done,
                    metadata: data.metadata,
                  });
                }
                if (data.done) {
                  const assistantMsg: Message = {
                    message_id: `assistant-${Date.now()}`,
                    role: 'assistant',
                    content: accumulatedContent,
                    type: 'text',
                    timestamp: new Date().toISOString(),
                    tool_calls: [],
                    tool_call_id: null,
                    name: null,
                    metadata: {},
                  };
                  addMessage(currentConversationId!, assistantMsg);
                  clearStreaming(currentConversationId!);
                }
              } catch (parseError) {
                // Ignore parse errors for incomplete chunks
              }
            }
          }
        }
      }
    } catch (e) {
      console.error('Streaming error:', e);
      const errorMsg: Message = {
        message_id: `error-${Date.now()}`,
        role: 'assistant',
        content: `Error: ${e instanceof Error ? e.message : 'Failed to get response'}`,
        type: 'text',
        timestamp: new Date().toISOString(),
        tool_calls: [],
        tool_call_id: null,
        name: null,
        metadata: {},
      };
      addMessage(currentConversationId!, errorMsg);
    } finally {
      setStreaming(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="h-full flex flex-col bg-card border border-border rounded-xl overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-border">
        <div className="flex items-center gap-3">
          <Avatar state={isStreaming ? 'thinking' : 'idle'} size="sm" />
          <div className="min-w-0">
            <h3 className="font-medium truncate">{currentConv?.title || 'New Conversation'}</h3>
            <p className="text-xs text-muted-foreground truncate">
              {currentMessages.length} messages • {useAgentMode ? 'Agent Mode' : 'Chat Mode'}
            </p>
          </div>

          {/* Agent Mode Toggle & Skills - moved to header left side */}
          <div className="flex items-center gap-2 ml-4 border-l border-border pl-4">
            {/* Agent Mode Toggle */}
            <Button
              variant={useAgentMode ? 'default' : 'outline'}
              size="sm"
              onClick={() => setUseAgentMode(!useAgentMode)}
              className="gap-1"
              title="Toggle Agent Mode"
            >
              <Bot className="h-3.5 w-3.5" />
              <span className="text-xs hidden sm:inline">Agent</span>
            </Button>

            {/* Skills Dropdown Menu - like Manus + button */}
            <div className="relative">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setShowSkillsMenu(!showSkillsMenu)}
                className="gap-1 h-8"
                title="Add Skill / Ability"
              >
                <Plus className="h-3.5 w-3.5" />
                <span className="text-xs hidden sm:inline">Skills</span>
                <ChevronDown className="h-3.5 w-3.5" />
              </Button>

              {/* Skills Dropdown Menu */}
              {showSkillsMenu && (
                <motion.div
                  initial={{ opacity: 0, y: -10, scale: 0.95 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: -10, scale: 0.95 }}
                  className="absolute left-0 top-full mt-1 bg-card border border-border rounded-xl shadow-lg p-2 z-50 w-72 max-h-96 overflow-y-auto"
                >
                  <div className="p-2 border-b border-border">
                    <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">
                      Agent Skills & Capabilities
                    </h4>
                  </div>

                  {/* Agent Mode Toggle in dropdown */}
                  <div className="p-2">
                    <label className="flex items-center gap-3 cursor-pointer p-2 rounded-lg hover:bg-accent">
                      <input
                        type="checkbox"
                        checked={useAgentMode}
                        onChange={(e) => setUseAgentMode(e.target.checked)}
                        className="w-4 h-4 rounded border-border text-primary focus:ring-primary"
                      />
                      <Sparkles className="h-4 w-4 text-muted-foreground" />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium">Agent Mode</p>
                        <p className="text-xs text-muted-foreground truncate">
                          Autonomous loop with tool calling & reasoning
                        </p>
                      </div>
                    </label>
                  </div>

                  <Separator className="my-1" />

                  {/* Categories */}
                  <div className="space-y-1">
                    <p className="px-2 py-1 text-xs text-muted-foreground uppercase tracking-wider">
                      Core Skills
                    </p>

                    {[
                      { id: 'web-search', label: 'Web Search', icon: Search, desc: 'Search the web for information' },
                      { id: 'code-executor', label: 'Code Executor', icon: Code2, desc: 'Run Python/JS code in sandbox' },
                      { id: 'browser-automation', label: 'Browser Automation', icon: Globe, desc: 'Control browser, scrape, click' },
                      { id: 'file-operations', label: 'File Operations', icon: FileText, desc: 'Read/write files in workspace' },
                      { id: 'terminal', label: 'Terminal', icon: Terminal, desc: 'Execute shell commands' },
                      { id: 'tool-manager', label: 'Tool Manager', icon: Wrench, desc: 'Manage & execute registered tools' },
                    ].map((skill) => {
                      const isActive = activeSkills.includes(skill.id);
                      const Icon = skill.icon;
                      return (
                        <label
                          key={skill.id}
                          className="flex items-center gap-3 cursor-pointer p-2 rounded-lg hover:bg-accent transition-colors"
                        >
                          <input
                            type="checkbox"
                            checked={isActive}
                            onChange={(e) => {
                              if (e.target.checked) {
                                setActiveSkills([...activeSkills, skill.id]);
                              } else {
                                setActiveSkills(activeSkills.filter(s => s !== skill.id));
                              }
                            }}
                            className="w-4 h-4 rounded border-border text-primary focus:ring-primary"
                          />
                          <Icon className={cn('h-4 w-4 flex-shrink-0', isActive ? 'text-primary' : 'text-muted-foreground')} />
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium truncate">{skill.label}</p>
                            <p className="text-xs text-muted-foreground truncate">{skill.desc}</p>
                          </div>
                          {isActive && <Shield className="h-3.5 w-3.5 text-green-500" />}
                        </label>
                      );
                    })}
                  </div>

                  <Separator className="my-1" />

                  <div className="space-y-1">
                    <p className="px-2 py-1 text-xs text-muted-foreground uppercase tracking-wider">
                      Quick Actions
                    </p>
                    {[
                      { label: 'New Conversation', icon: Plus, action: () => { setShowNewConv(true); setShowSkillsMenu(false); } },
                      { label: 'Clear History', icon: Trash2, action: () => { /* clear current conv */ } },
                      { label: 'Settings', icon: Settings, action: () => { /* open settings */ } },
                    ].map((item) => (
                      <button
                        key={item.label}
                        onClick={item.action}
                        className="w-full flex items-center gap-3 p-2 rounded-lg hover:bg-accent transition-colors text-left"
                      >
                        <item.icon className="h-4 w-4 text-muted-foreground" />
                        <span className="text-sm">{item.label}</span>
                      </button>
                    ))}
                  </div>
                </motion.div>
              )}

              {/* Click outside to close */}
              {showSkillsMenu && (
                <div
                  className="fixed inset-0 z-40"
                  onClick={() => setShowSkillsMenu(false)}
                />
              )}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Model Selector */}
          <div className="relative">
            <Button variant="outline" size="sm" onClick={() => setShowModelSelector(!showModelSelector)} className="gap-1">
              <Sparkles className="h-3.5 w-3.5" />
              <span className="text-xs hidden sm:inline">{selectedModel}</span>
              <ChevronDown className="h-3.5 w-3.5" />
            </Button>
            {showModelSelector && (
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                className="absolute right-0 top-full mt-1 bg-card border border-border rounded-lg shadow-lg py-1 w-96 z-10 max-h-96 overflow-y-auto"
              >
                {availableModels.map(model => (
                  <button
                    key={model}
                    onClick={() => {
                      setSelectedModel(model);
                      setShowModelSelector(false);
                    }}
                    className={cn(
                      'w-full flex items-center gap-2 px-3 py-2 text-sm transition-colors',
                      'hover:bg-accent hover:text-accent-foreground',
                      selectedModel === model && 'bg-primary/10 text-primary'
                    )}
                  >
                    <Bot className="h-4 w-4" />
                    {model}
                  </button>
                ))}
              </motion.div>
            )}
          </div>

          <Button variant="ghost" size="icon" onClick={() => setShowNewConv(!showNewConv)} title="New Conversation">
            <Plus className="h-4 w-4" />
          </Button>
          <Button variant="ghost" size="icon" onClick={loadConversations} title="Refresh">
            <RotateCcw className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* New conversation dialog */}
      <AnimatePresence>
        {showNewConv && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="border-b border-border p-4"
          >
            <Input
              value={newConvTitle}
              onChange={(e) => setNewConvTitle(e.target.value)}
              placeholder="Conversation title..."
              onKeyDown={(e) => e.key === 'Enter' && handleNewConversation()}
              autoFocus
            />
            <div className="flex justify-end gap-2 mt-2">
              <Button variant="ghost" size="sm" onClick={() => setShowNewConv(false)}>
                Cancel
              </Button>
              <Button size="sm" onClick={handleNewConversation}>
                Create
              </Button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Messages */}
      <ScrollArea className="flex-1 p-4 space-y-4">
        {currentMessages.map((msg: Message, idx: number) => (
          <MessageBubble key={`${msg.message_id}-${idx}`} message={msg} />
        ))}

        {/* Streaming response */}
        {currentStream && !currentStream.done && (
          <MessageBubble
            message={{
              ...currentStream,
              role: 'assistant',
              content: currentStream.chunk,
              type: 'text',
              message_id: `stream-${currentConversationId}`,
              timestamp: new Date().toISOString(),
              tool_calls: [],
              tool_call_id: null,
              name: null,
              metadata: {},
            } as Message}
            isStreaming
          />
        )}

        {/* Tool calls display during streaming */}
        {currentConversationId && isStreaming && useAgentMode && (
          <div className="space-y-2 ml-14 w-[70%]">
            {Object.entries(toolCalls).map(([callId, toolCall]) => (
              <ToolCallDisplay
                key={callId}
                callId={callId}
                name={toolCall.name}
                arguments={toolCall.arguments}
                status={toolCall.status}
                result={toolCall.result}
                error={toolCall.error}
              />
            ))}
          </div>
        )}

        {/* Approval Modal */}
        <ApprovalModal
          request={approvalRequest}
          onApprove={handleApprovalResponse}
          isLoading={isApproving}
        />

        <div ref={messagesEndRef} />
      </ScrollArea>

      {/* Input */}
      <div className="p-4 border-t border-border">
        <div className="flex gap-2">
          <Textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={isStreaming ? 'Waiting for response...' : 'Type a message...'}
            disabled={isStreaming || !currentConversationId}
            className="flex-1 min-h-[44px] max-h-32 resize-none"
            rows={1}
          />
          <Button
            onClick={handleSend}
            disabled={!input.trim() || isStreaming || !currentConversationId}
            className="h-[44px]"
          >
            <Send className="h-4 w-4" />
          </Button>
        </div>

        {/* Active Skills Indicator */}
        {activeSkills.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1">
            {activeSkills.map((skillId) => {
              const skill = {
                'web-search': { label: '🌐 Web Search', icon: Search },
                'code-executor': { label: '⚙️ Code Exec', icon: Code2 },
                'browser-automation': { label: '🌍 Browser', icon: Globe },
                'file-operations': { label: '📁 Files', icon: FileText },
                'terminal': { label: '💻 Terminal', icon: Terminal },
                'tool-manager': { label: '🔧 Tools', icon: Wrench },
              }[skillId];
              const Icon = skill?.icon;
              return skill ? (
                <span key={skillId} className="inline-flex items-center gap-1 px-2 py-0.5 bg-primary/10 text-primary text-xs rounded-full">
                  {Icon && <Icon className="h-3 w-3" />}
                  {skill.label}
                </span>
              ) : null;
            })}
          </div>
        )}
      </div>
    </div>
  );
}

function MessageBubble({ message, isStreaming = false }: { message: Message; isStreaming?: boolean }) {
  const isUser = message.role === 'user';
  const isAssistant = message.role === 'assistant';

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn('flex gap-3', isUser && 'flex-row-reverse')}
    >
      <Avatar
        state={isStreaming ? 'speaking' : isAssistant ? 'thinking' : 'idle'}
        size="sm"
        className="flex-shrink-0 mt-1"
      />

      <div
        className={cn(
          'max-w-[70%] rounded-2xl px-4 py-2',
          isUser
            ? 'bg-primary text-primary-foreground rounded-br-md'
            : 'bg-muted rounded-bl-md'
        )}
      >
        <p className="whitespace-pre-wrap">{message.content}</p>
        {isStreaming && (
          <motion.span
            animate={{ opacity: [0, 1, 0] }}
            transition={{ duration: 1, repeat: Infinity }}
            className="ml-1"
          >
            ▊
          </motion.span>
        )}
      </div>
    </motion.div>
  );
}