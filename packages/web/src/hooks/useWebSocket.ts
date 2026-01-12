/**
 * WebSocket hook for real-time session updates.
 *
 * Establishes WS connection to server, handles reconnection,
 * and provides callback for new events.
 *
 * Related: api/client.ts (Event type), App.tsx (usage)
 */

import { useEffect, useRef, useCallback, useState } from 'react';
import type { Event, MetricsResponse } from '../api/client';

interface NewEventMessage {
  type: 'new_event';
  event: Event;
}

interface MetricsUpdateMessage {
  type: 'metrics_update';
  session_id: string;
  metrics: MetricsResponse;
}

type WebSocketMessage = NewEventMessage | MetricsUpdateMessage;

interface UseWebSocketOptions {
  onEvent?: (event: Event) => void;
  onMetricsUpdate?: (sessionId: string, metrics: MetricsResponse) => void;
  reconnectInterval?: number;
}

export function useWebSocket(options: UseWebSocketOptions = {}) {
  const { onEvent, onMetricsUpdate, reconnectInterval = 3000 } = options;
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  // Use ref for callbacks to avoid reconnections when callbacks change
  const onEventRef = useRef(onEvent);
  onEventRef.current = onEvent;
  const onMetricsUpdateRef = useRef(onMetricsUpdate);
  onMetricsUpdateRef.current = onMetricsUpdate;

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;

    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      setIsConnected(true);
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
    };

    ws.onmessage = (event) => {
      try {
        const data: WebSocketMessage = JSON.parse(event.data);
        if (data.type === 'new_event' && onEventRef.current) {
          onEventRef.current(data.event);
        } else if (data.type === 'metrics_update' && onMetricsUpdateRef.current) {
          onMetricsUpdateRef.current(data.session_id, data.metrics);
        }
      } catch {
        // Ignore parse errors
      }
    };

    ws.onclose = () => {
      setIsConnected(false);
      wsRef.current = null;

      // Reconnect after interval
      reconnectTimeoutRef.current = window.setTimeout(() => {
        connect();
      }, reconnectInterval);
    };

    ws.onerror = () => {
      ws.close();
    };

    wsRef.current = ws;
  }, [reconnectInterval]);

  useEffect(() => {
    connect();

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connect]);

  return { isConnected };
}
