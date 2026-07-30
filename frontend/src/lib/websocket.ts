// WebSocket Client for AIPENSA Runtime EventBus streaming

import type { RuntimeEvent } from '@/types/runtime';

type EventHandler = (event: RuntimeEvent) => void;

class WebSocketClient {
  private ws: WebSocket | null = null;
  private handlers: Set<EventHandler> = new Set();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 10;
  private reconnectDelay = 1000;
  private url: string;
  private isConnecting = false;
  private shouldReconnect = true;
  private pingInterval: NodeJS.Timeout | null = null;

  constructor(url: string = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws/events') {
    this.url = url;
  }

  connect() {
    if (this.ws?.readyState === WebSocket.OPEN || this.isConnecting) {
      return;
    }

    this.isConnecting = true;
    this.shouldReconnect = true;

    try {
      this.ws = new WebSocket(this.url);

      this.ws.onopen = () => {
        console.log('[WS] Connected to EventBus');
        this.isConnecting = false;
        this.reconnectAttempts = 0;

        // Start heartbeat
        this.startHeartbeat();
      };

      this.ws.onmessage = (event) => {
        try {
          const runtimeEvent = JSON.parse(event.data) as RuntimeEvent;
          console.log('[WS] Received event:', runtimeEvent.event_type, 'source:', runtimeEvent.source, 'corr:', runtimeEvent.correlation_id?.slice(0, 8));
          this.handlers.forEach(handler => {
            try {
              handler(runtimeEvent);
            } catch (e) {
              console.error('[WS] Handler error:', e);
            }
          });
        } catch (e) {
          console.error('[WS] Parse error:', e);
        }
      };

      this.ws.onclose = () => {
        console.log('[WS] Disconnected from EventBus');
        this.isConnecting = false;
        this.stopHeartbeat();

        if (this.shouldReconnect) {
          this.attemptReconnect();
        }
      };

      this.ws.onerror = (error) => {
        console.error('[WS] Error:', error);
        this.isConnecting = false;
      };
    } catch (e) {
      console.error('[WS] Connection failed:', e);
      this.isConnecting = false;
      this.attemptReconnect();
    }
  }

  private startHeartbeat() {
    this.pingInterval = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ type: 'ping' }));
      }
    }, 30000);
  }

  private stopHeartbeat() {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }

  private attemptReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('[WS] Max reconnect attempts reached');
      return;
    }

    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
    console.log(`[WS] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);

    setTimeout(() => {
      if (this.shouldReconnect) {
        this.connect();
      }
    }, delay);
  }

  subscribe(handler: EventHandler) {
    this.handlers.add(handler);
    return () => this.handlers.delete(handler);
  }

  disconnect() {
    this.shouldReconnect = false;
    this.stopHeartbeat();
    this.ws?.close();
    this.ws = null;
  }

  get isConnected() {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}

// Singleton instance
export const wsClient = new WebSocketClient();

// React hook for using the event stream
import { useEffect, useCallback } from 'react';

export function useEventStream(handler: (event: RuntimeEvent) => void, deps: any[] = []) {
  useEffect(() => {
    const unsubscribe = wsClient.subscribe(handler);
    wsClient.connect();
    return () => {
      unsubscribe();
    };
  }, deps);
}

// Hook for connection status
import { useState, useEffect as useEffectReact } from 'react';

export function useConnectionStatus() {
  const [connected, setConnected] = useState(false);

  useEffectReact(() => {
    const checkConnection = () => {
      setConnected(wsClient.isConnected);
    };

    const interval = setInterval(checkConnection, 1000);
    checkConnection();

    return () => clearInterval(interval);
  }, []);

  return connected;
}