// Type definitions for the frontend

// ============================================
// Runtime Types
// ============================================

export type ModuleState =
  | 'UNINITIALIZED'
  | 'INITIALIZED'
  | 'STARTING'
  | 'RUNNING'
  | 'STOPPING'
  | 'STOPPED'
  | 'ERROR';

export interface ModuleInfo {
  name: string;
  label?: string;
  state: ModuleState;
  metadata?: ModuleMetadata;
  health?: ModuleHealth | null;
}

export interface ModuleMetadata {
  name: string;
  version: string;
  description: string;
  author: string;
  dependencies: string[];
  provides: string[];
  tags: string[];
}

export interface ModuleHealth {
  module: string;
  status: string;
  healthy: boolean;
  details: Record<string, any>;
}

export interface RuntimeInfo {
  runtime_id: string;
  name: string;
  version: string;
  status: string;
  started_at: string | null;
  modules: Record<string, string>;
  plugins: Record<string, string>;
}

export interface HealthResponse {
  runtime: {
    status: string;
    runtime_id: string;
    uptime_seconds: number;
  };
  modules: Record<string, any>;
  plugins: Record<string, any>;
}

// ============================================
// Conversation Types
// ============================================

export type MessageRole = 'system' | 'user' | 'assistant' | 'tool' | 'function';

export type MessageType = 'text' | 'image' | 'audio' | 'tool_call' | 'tool_result' | 'error';

export interface Message {
  message_id: string;
  role: MessageRole;
  content: string;
  type: MessageType;
  tool_calls: Array<{
    id: string;
    type: string;
    function: {
      name: string;
      arguments: string;
    };
  }>;
  tool_call_id: string | null;
  name: string | null;
  metadata: Record<string, any>;
  timestamp: string;
}

export interface Conversation {
  conversation_id: string;
  title: string;
  messages: Message[];
  system_prompt: string;
  context: Record<string, any>;
  metadata: Record<string, any>;
  created_at: string;
  updated_at: string;
  max_messages: number;
  max_tokens: number;
}

export interface StreamingResponse {
  conversation_id: string;
  chunk: string;
  done: boolean;
  metadata: Record<string, any>;
}

// ============================================
// Event Types
// ============================================

export interface RuntimeEvent {
  event_type: string;
  source: string;
  timestamp: string;
  correlation_id: string;
  causation_id: string | null;
  payload: Record<string, any>;
  metadata: Record<string, any>;
  tags: string[];
}

export interface EventFilters {
  eventTypes: string[];
  sources: string[];
  tags: string[];
  text: string;
}

// ============================================
// Browser Types
// ============================================

export interface BrowserSession {
  session_id: string;
  url: string;
}

export interface BrowserState {
  url: string;
  title: string;
  tabs: Array<Record<string, any>>;
  pixels_above: number;
  pixels_below: number;
  viewport_height: number;
  interactive_elements: string;
  screenshot_base64: string | null;
  error: string | null;
}

// ============================================
// Tool Types
// ============================================

export interface ToolDefinition {
  name: string;
  description: string;
  parameters: Record<string, any>;
  returns: Record<string, any>;
  category: string;
  tags: string[];
  requires_approval: boolean;
}

export interface ToolExecution {
  tool_name: string;
  arguments: Record<string, any>;
  result: any;
  error: string | null;
  success: boolean;
}

// ============================================
// Memory Types
// ============================================

export interface SearchResult {
  key: string;
  value: any;
  score: number;
  metadata: Record<string, any>;
}

// ============================================
// Execution Types
// ============================================

export interface ExecutionResult {
  success: boolean;
  output: string;
  error: string | null;
  execution_time: number;
}

// ============================================
// File System Types
// ============================================

export interface FileInfo {
  path: string;
  name: string;
  size: number;
  is_dir: boolean;
  modified_at: string;
}

// ============================================
// Workflow Types
// ============================================

export interface WorkflowNode {
  id: string;
  type: 'start' | 'agent' | 'tool' | 'condition' | 'end';
  position: { x: number; y: number };
  data: {
    label: string;
    agentType?: string;
    toolName?: string;
    condition?: string;
    config?: Record<string, any>;
  };
}

export interface WorkflowEdge {
  id: string;
  source: string;
  target: string;
  type?: string;
  animated?: boolean;
  label?: string;
  style?: Record<string, any>;
}

export interface WorkflowState {
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
  executionState: {
    activeNodeId: string | null;
    completedNodes: string[];
    failedNodes: string[];
    currentStep: number;
  };
}

// ============================================
// Debug Types
// ============================================

export interface DebugLogEntry {
  id: string;
  timestamp: string;
  level: 'debug' | 'info' | 'warn' | 'error';
  source: string;
  message: string;
  data?: any;
}

export interface StateSnapshot {
  id: string;
  timestamp: string;
  runtime: RuntimeInfo | null;
  modules: Record<string, ModuleHealth>;
  conversationCount: number;
  activeWorkflows: number;
}

// ============================================
// Plugin Types
// ============================================

export interface PluginInfo {
  id: string;
  name: string;
  version: string;
  description: string;
  author: string;
  plugin_type: string;
  provides: string[];
  tags: string[];
  enabled: boolean;
  running: boolean;
  configured: boolean;
  dependencies: string[];
}

export interface PluginsResponse {
  plugins: PluginInfo[];
}

export interface PluginConfigRequest {
  enabled?: boolean;
  config?: Record<string, any>;
}

// ============================================
// Settings Types
// ============================================

export interface SettingsResponse {
  settings: {
    runtime: RuntimeConfig;
    ui: UISettings;
  };
}

export interface RuntimeConfig {
  runtime_type: string;
  name: string;
  version: string;
  workspace: string;
  log_level: string;
  browser: Record<string, any>;
  sandbox: Record<string, any>;
  memory: Record<string, any>;
  llm: Record<string, any>;
  mcp: Record<string, any>;
  events: Record<string, any>;
  telemetry: Record<string, any>;
  security: Record<string, any>;
  modules: Array<Record<string, any>>;
  plugin_configs: Record<string, Record<string, any>>;
  features: Record<string, boolean>;
  max_concurrent_tasks: number;
  max_memory_mb: number;
  max_cpu_percent: number;
  task_timeout_seconds: number;
}

export interface UISettings {
  theme: 'light' | 'dark' | 'system';
  accent_color: string;
  density: 'comfortable' | 'cozy' | 'compact';
  auto_scroll: boolean;
  compact_mode: boolean;
  show_module_status: boolean;
  animations_enabled: boolean;
  notifications_enabled: boolean;
  sound_enabled: boolean;
  desktop_notifications_enabled: boolean;
  debug_mode: boolean;
  performance_monitoring: boolean;
  event_persistence: boolean;
  ws_auto_reconnect: boolean;
  log_level: string;
  max_events: number;
  api_url: string;
  ws_url: string;
  notification_types: {
    errors: boolean;
    warnings: boolean;
    info: boolean;
    debug: boolean;
  };
}

export interface BackupExportResponse {
  data: {
    version: string;
    runtime_config: RuntimeConfig;
    conversations: any[];
    workflows: any[];
    events: any[];
    modules: Record<string, string>;
    plugins: Record<string, string>;
  };
  timestamp: string;
  version: string;
}

export interface BackupImportRequest {
  data: {
    version: string;
    runtime_config?: RuntimeConfig;
    conversations?: any[];
    workflows?: any[];
    events?: any[];
    modules?: Record<string, string>;
    plugins?: Record<string, string>;
  };
  overwrite: boolean;
}