// API client for communicating with the Runtime backend
// Uses relative paths to leverage Next.js rewrites (configured in next.config.js)
// which proxies /api/* to http://localhost:8001/api/*

import type { SettingsResponse, RuntimeConfig, BackupExportResponse, BackupImportRequest, UISettings } from '@/types/runtime';

const API_BASE = '';

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    console.log('[api.ts] >>>>> Client-side Request START:', url, 'BaseURL:', this.baseUrl);
    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    });
    console.log('[api.ts] >>>>> Client-side Response:', url, 'status:', response.status);

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      console.error('[api.ts] >>>>> Error response:', response.status, error);
      throw new Error(error.detail || `API Error: ${response.status}`);
    }

    const data = await response.json();
    console.log('[api.ts] >>>>> Client-side Response data:', endpoint, data);
    return data;
  }

  // ============================================
  // Runtime
  // ============================================

  async getRuntimeInfo() {
    return this.request<any>('/api/runtime/info');
  }

  async getHealth() {
    return this.request<any>('/api/runtime/health');
  }

  async executeTask(task: any) {
    return this.request<any>('/api/runtime/execute', {
      method: 'POST',
      body: JSON.stringify(task),
    });
  }

  // ============================================
  // Modules
  // ============================================

  async listModules() {
    return this.request<any>('/api/modules');
  }

  async getModuleHealth(moduleName: string) {
    return this.request<any>(`/api/modules/${moduleName}/health`);
  }

  async executeModuleOperation(moduleName: string, operation: string, params: any = {}) {
    return this.request<any>(`/api/modules/${moduleName}/execute`, {
      method: 'POST',
      body: JSON.stringify({ operation, params }),
    });
  }

  // ============================================
  // Agent Loop
  // ============================================

  async *agentStream(conversationId: string, data: {
    message: string;
    model?: string;
    available_tools?: string[];
    max_iterations?: number;
    max_tokens?: number;
    temperature?: number;
    system_prompt?: string;
    require_approval?: boolean;
  }): AsyncGenerator<any> {
    const response = await fetch(`${this.baseUrl}/api/conversation/${conversationId}/agent/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(error.detail || `API Error: ${response.status}`);
    }

    const reader = response.body?.getReader();
    const decoder = new TextDecoder();

    if (!reader) {
      throw new Error('No response body');
    }

    let buffer = '';
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6));
            if (data.data || data.event_type) {
              // Handle double-encoded SSE (data: data: {...})
              if (typeof data.data === 'string' && data.data.startsWith('{')) {
                const inner = JSON.parse(data.data);
                yield inner;
              } else {
                yield data;
              }
            }
          } catch (e) {
            // Ignore parse errors for incomplete chunks
          }
        }
      }
    }
  }

  // ============================================
  // Agent Approval
  // ============================================

  async approveTool(callId: string, approved: boolean = true) {
    return this.request<any>(`/api/agent/approve/${callId}`, {
      method: 'POST',
      body: JSON.stringify({ approved }),
    });
  }

  // ============================================
  // Conversations
  // ============================================

  async createConversation(data: { title?: string; system_prompt?: string; context?: any }) {
    return this.request<any>('/api/conversation/create', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getConversation(conversationId: string) {
    return this.request<any>(`/api/conversation/${conversationId}`);
  }

  async listConversations(limit = 50, offset = 0) {
    return this.request<any>(`/api/conversations?limit=${limit}&offset=${offset}`);
  }

  async addMessage(conversationId: string, data: { role: string; content: string; message_type?: string; metadata?: any }) {
    return this.request<any>(`/api/conversation/${conversationId}/message`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getMessages(conversationId: string, limit = 100) {
    return this.request<any>(`/api/conversation/${conversationId}/messages?limit=${limit}`);
  }

  async streamResponse(conversationId: string, content: string, model?: string, temperature = 0.7, max_tokens = 1024) {
    // Use the streaming endpoint
    const response = await fetch(`${this.baseUrl}/api/conversation/${conversationId}/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ model: model || 'meta/llama-3.1-70b-instruct', temperature, max_tokens }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(error.detail || `API Error: ${response.status}`);
    }

    return response.body;
  }

  // ============================================
  // Browser
  // ============================================

  async listBrowserSessions() {
    return this.request<any>('/api/browser/sessions');
  }

  async createBrowserSession(data: { url?: string; config?: any }) {
    return this.request<any>('/api/browser/session', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getBrowserState(sessionId: string) {
    return this.request<any>(`/api/browser/session/${sessionId}/state`);
  }

  async browserAction(sessionId: string, action: { action: string; params: any }) {
    return this.request<any>(`/api/browser/session/${sessionId}/action`, {
      method: 'POST',
      body: JSON.stringify(action),
    });
  }

  async browserScreenshot(sessionId: string, fullPage = true) {
    return this.request<any>(`/api/browser/session/${sessionId}/screenshot?full_page=${fullPage}`, {
      method: 'POST',
    });
  }

  async closeBrowserSession(sessionId: string) {
    return this.request<any>(`/api/browser/session/${sessionId}`, {
      method: 'DELETE',
    });
  }

  // ============================================
  // Tools
  // ============================================

  async listTools(category?: string) {
    const query = category ? `?category=${category}` : '';
    return this.request<any>(`/api/tools${query}`);
  }

  async executeTool(data: { tool_name: string; arguments: any; context?: any }) {
    return this.request<any>('/api/tools/execute', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // ============================================
  // Memory
  // ============================================

  async searchMemory(query: string, memoryType = 'default', limit = 10) {
    return this.request<any>(`/api/memory/search?query=${encodeURIComponent(query)}&memory_type=${memoryType}&limit=${limit}`);
  }

  // ============================================
  // Execution
  // ============================================

  async executePython(data: { code: string; sandbox_id?: string; timeout_seconds?: number; packages?: string[]; env_vars?: Record<string, string> }) {
    return this.request<any>('/api/execution/python', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // ============================================
  // File System
  // ============================================

  async readFile(path: string) {
    return this.request<any>(`/api/filesystem/read?path=${encodeURIComponent(path)}`);
  }

  async writeFile(path: string, content: string, encoding = 'utf-8', createDirs = true) {
    return this.request<any>('/api/filesystem/write', {
      method: 'POST',
      body: JSON.stringify({ path, content, encoding, create_dirs: createDirs }),
    });
  }

  async listFiles(path: string, recursive = false) {
    return this.request<any>(`/api/filesystem/list?path=${encodeURIComponent(path)}&recursive=${recursive}`);
  }

  // ============================================
  // Events
  // ============================================

  async getEventHistory(limit = 100, eventType?: string) {
    const query = eventType ? `?limit=${limit}&event_type=${eventType}` : `?limit=${limit}`;
    return this.request<any>(`/api/events/history${query}`);
  }

  async getDeadLetter() {
    return this.request<any>('/api/events/dead-letter');
  }

  // ============================================
  // Plugins
  // ============================================

  async listPlugins() {
    console.log('[api.ts] listPlugins called');
    const result = await this.request<any>('/api/plugins');
    console.log('[api.ts] listPlugins result:', result);
    return result;
  }

  async getPlugin(pluginId: string) {
    return this.request<any>(`/api/plugins/${pluginId}`);
  }

  async getPluginHealth(pluginId: string) {
    return this.request<any>(`/api/plugins/${pluginId}/health`);
  }

  async configurePlugin(pluginId: string, config: { enabled?: boolean; config?: Record<string, any> }) {
    return this.request<any>(`/api/plugins/${pluginId}/config`, {
      method: 'POST',
      body: JSON.stringify(config),
    });
  }

  async startPlugin(pluginId: string) {
    return this.request<any>(`/api/plugins/${pluginId}/start`, {
      method: 'POST',
    });
  }

  async stopPlugin(pluginId: string) {
    return this.request<any>(`/api/plugins/${pluginId}/stop`, {
      method: 'POST',
    });
  }

  // ============================================
  // LLM Models
  // ============================================

  async listModels(provider?: string) {
    const query = provider ? `?provider=${provider}` : '';
    return this.request<any>(`/api/llm/models${query}`);
  }

  async getModelInfo(modelId: string) {
    return this.request<any>(`/api/llm/models/${modelId}`);
  }

  // ============================================
  // Workflow
  // ============================================

  async listWorkflows(status?: string, limit = 50, offset = 0) {
    const params = new URLSearchParams();
    if (status) params.append('status', status);
    params.append('limit', limit.toString());
    params.append('offset', offset.toString());
    return this.request<any>(`/api/workflows?${params.toString()}`);
  }

  async getWorkflow(workflowId: string) {
    return this.request<any>(`/api/workflows/${workflowId}`);
  }

  async createWorkflow(data: any) {
    return this.request<any>('/api/workflows', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateWorkflow(workflowId: string, data: any) {
    return this.request<any>(`/api/workflows/${workflowId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deleteWorkflow(workflowId: string) {
    return this.request<any>(`/api/workflows/${workflowId}`, {
      method: 'DELETE',
    });
  }

  async createWorkflowFromDag(data: any) {
    return this.request<any>('/api/workflows/dag', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async executeWorkflow(workflowId: string, data: any) {
    return this.request<any>(`/api/workflows/${workflowId}/execute`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async cancelWorkflow(workflowId: string, executionId: string) {
    return this.request<any>(`/api/workflows/${workflowId}/cancel`, {
      method: 'POST',
      body: JSON.stringify({ execution_id: executionId }),
    });
  }

  async pauseWorkflow(workflowId: string, executionId: string) {
    return this.request<any>(`/api/workflows/${workflowId}/pause`, {
      method: 'POST',
      body: JSON.stringify({ execution_id: executionId }),
    });
  }

  async resumeWorkflow(workflowId: string, executionId: string) {
    return this.request<any>(`/api/workflows/${workflowId}/resume`, {
      method: 'POST',
      body: JSON.stringify({ execution_id: executionId }),
    });
  }

  async listExecutions(workflowId: string, limit = 50) {
    return this.request<any>(`/api/workflows/${workflowId}/executions?limit=${limit}`);
  }

  async getExecution(executionId: string) {
    return this.request<any>(`/api/workflows/executions/${executionId}`);
  }

  async exportWorkflow(workflowId: string) {
    return this.request<any>(`/api/workflows/${workflowId}/export`);
  }

  // ============================================
  // Settings
  // ============================================

  async getSettings() {
    return this.request<SettingsResponse>('/api/settings');
  }

  async getRuntimeConfig() {
    return this.request<RuntimeConfig>('/api/settings/runtime');
  }

  async updateRuntimeConfig(config: Record<string, any>) {
    return this.request<any>('/api/settings/runtime', {
      method: 'POST',
      body: JSON.stringify(config),
    });
  }

  async updateSettings(settings: Record<string, any>) {
    return this.request<any>('/api/settings', {
      method: 'POST',
      body: JSON.stringify(settings),
    });
  }

  async exportBackup() {
    return this.request<BackupExportResponse>('/api/settings/export');
  }

  async importBackup(data: BackupImportRequest) {
    return this.request<any>('/api/settings/import', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async clearCache() {
    return this.request<any>('/api/settings/clear-cache', {
      method: 'POST',
    });
  }

  async resetSettings() {
    return this.request<any>('/api/settings/reset', {
      method: 'POST',
    });
  }
}

// Export instance
export const api = new ApiClient();