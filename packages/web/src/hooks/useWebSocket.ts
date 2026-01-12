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
}

export function useWebSocket(options: UseWebSocketOptions = {}) {
  const { onEvent, onNewSession } = options;
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const subscribedSessionRef = useRef<string | null>(null);

  // Use ref for callbacks to avoid reconnections when callbacks change
  const onEventRef = useRef(onEvent);
  onEventRef.current = onEvent;
  const onNewSessionRef = useRef(onNewSession);
  onNewSessionRef.current = onNewSession;

  // Connect on mount
  useEffect(() => {
    const connect = () => {
      // Don't reconnect if already connected or connecting
      if (wsRef.current?.readyState === WebSocket.OPEN ||
          wsRef.current?.readyState === WebSocket.CONNECTING) {
        return;
      }

      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${window.location.host}/ws`;

      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        setIsConnected(true);
        // Re-subscribe to session if we had one before reconnect
        if (subscribedSessionRef.current) {
          ws.send(JSON.stringify({ type: 'subscribe', session_id: subscribedSessionRef.current }));
        }
      };

      ws.onmessage = (messageEvent) => {
        try {
          const data: WebSocketMessage = JSON.parse(messageEvent.data);
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
        // Reconnect after 3 seconds
        reconnectTimeoutRef.current = setTimeout(connect, 3000);
      };

      ws.onerror = () => {
        ws.close();
      };

      wsRef.current = ws;
    };

    connect();

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, []);

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

  return { isConnected, subscribe };
}
