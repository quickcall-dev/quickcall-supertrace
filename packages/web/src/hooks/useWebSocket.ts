/**
 * WebSocket hook for real-time session updates.
 *
 * Establishes WS connection to server, handles reconnection,
 * and provides subscribe/unsubscribe for session-specific updates.
 *
 * Related: api/client.ts (Event type), App.tsx (usage)
 */

import { useEffect, useRef, useCallback, useState } from 'react';
import type { Event } from '../api/client';

interface NewEventMessage {
  type: 'new_event';
  event: Event;
}

interface NewSessionMessage {
  type: 'new_session';
  session_id: string;
}

type WebSocketMessage = NewEventMessage | NewSessionMessage;

interface UseWebSocketOptions {
  onEvent?: (event: Event) => void;
  onNewSession?: (sessionId: string) => void;
  reconnectInterval?: number;
}

export function useWebSocket(options: UseWebSocketOptions = {}) {
  const { onEvent, onNewSession, reconnectInterval = 3000 } = options;
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const subscribedSessionRef = useRef<string | null>(null);

  // Use ref for callbacks to avoid reconnections when callbacks change
  const onEventRef = useRef(onEvent);
  onEventRef.current = onEvent;
  const onNewSessionRef = useRef(onNewSession);
  onNewSessionRef.current = onNewSession;

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
      // Re-subscribe to session if we had one before reconnect
      if (subscribedSessionRef.current) {
        ws.send(JSON.stringify({ type: 'subscribe', session_id: subscribedSessionRef.current }));
      }
    };

    ws.onmessage = (event) => {
      try {
        const data: WebSocketMessage = JSON.parse(event.data);
        if (data.type === 'new_event' && onEventRef.current) {
          onEventRef.current(data.event);
        } else if (data.type === 'new_session' && onNewSessionRef.current) {
          onNewSessionRef.current(data.session_id);
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

  // Subscribe to a session's updates
  const subscribe = useCallback((sessionId: string) => {
    // Unsubscribe from previous session
    if (subscribedSessionRef.current && wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'unsubscribe', session_id: subscribedSessionRef.current }));
    }

    subscribedSessionRef.current = sessionId;

    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'subscribe', session_id: sessionId }));
    }
  }, []);

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

  return { isConnected, subscribe };
}
