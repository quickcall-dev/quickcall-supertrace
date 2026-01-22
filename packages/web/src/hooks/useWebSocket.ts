/**
 * WebSocket hook for real-time session updates.
 *
 * Establishes WS connection to server, handles reconnection,
 * and provides subscribe/unsubscribe for session-specific updates.
 *
 * Backend broadcasts these event types:
 * - session_imported: New session file found {session_id, is_new: true}
 * - session_updated: New messages in existing session {session_id, new_messages}
 * - session_refreshed: Manual refresh via API {session_id, new_messages, timestamp}
 *
 * Related: api/client.ts (Event type), App.tsx (usage)
 */

import { useEffect, useRef, useCallback, useState } from 'react';

// WebSocket message types from backend
interface SessionImportedMessage {
  type: 'session_imported';
  session_id: string;
  is_new?: boolean;
}

interface SessionUpdatedMessage {
  type: 'session_updated';
  session_id: string;
  new_messages: number;
}

interface SessionRefreshedMessage {
  type: 'session_refreshed';
  session_id: string;
  new_messages: number;
  timestamp: string;
}

interface IntentChangedMessage {
  type: 'intent_changed';
  session_id: string;
  intents: string[];
  changed: boolean;
  change_reason?: string;
  previous_intents?: string[];
}

interface ContextUpdatedMessage {
  type: 'context_updated';
  session_id: string;
  used_percentage: number;
  remaining_percentage: number;
  context_window_size: number;
  total_input_tokens: number;
  total_output_tokens: number;
  timestamp: string;
}

interface ServerRestartingMessage {
  type: 'server_restarting';
  message: string;
  new_version: string;
}

type WebSocketMessage = SessionImportedMessage | SessionUpdatedMessage | SessionRefreshedMessage | IntentChangedMessage | ContextUpdatedMessage | ServerRestartingMessage;

export type { ContextUpdatedMessage };

interface UseWebSocketOptions {
  onSessionImported?: (sessionId: string) => void;
  onSessionUpdated?: (sessionId: string, newMessages: number) => void;
  onIntentChanged?: (message: IntentChangedMessage) => void;
  onContextUpdated?: (message: ContextUpdatedMessage) => void;
}

export function useWebSocket(options: UseWebSocketOptions = {}) {
  const { onSessionImported, onSessionUpdated, onIntentChanged, onContextUpdated } = options;
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const subscribedSessionRef = useRef<string | null>(null);

  // Use ref for callbacks to avoid reconnections when callbacks change
  const onSessionImportedRef = useRef(onSessionImported);
  onSessionImportedRef.current = onSessionImported;
  const onSessionUpdatedRef = useRef(onSessionUpdated);
  onSessionUpdatedRef.current = onSessionUpdated;
  const onIntentChangedRef = useRef(onIntentChanged);
  onIntentChangedRef.current = onIntentChanged;
  const onContextUpdatedRef = useRef(onContextUpdated);
  onContextUpdatedRef.current = onContextUpdated;

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
        console.log('[WebSocket] Connected');
        setIsConnected(true);
        // Re-subscribe to session if we had one before reconnect
        if (subscribedSessionRef.current) {
          ws.send(JSON.stringify({ type: 'subscribe', session_id: subscribedSessionRef.current }));
        }
      };

      ws.onmessage = (messageEvent) => {
        try {
          const data: WebSocketMessage = JSON.parse(messageEvent.data);
          console.log('[WebSocket] Received:', data.type, data);

          if (data.type === 'session_imported' && onSessionImportedRef.current) {
            // New session discovered - refresh session list
            onSessionImportedRef.current(data.session_id);
          } else if (data.type === 'session_updated' && onSessionUpdatedRef.current) {
            // Existing session has new messages - refresh if subscribed
            onSessionUpdatedRef.current(data.session_id, data.new_messages);
          } else if (data.type === 'session_refreshed' && onSessionUpdatedRef.current) {
            // Manual refresh completed - treat same as update
            onSessionUpdatedRef.current(data.session_id, data.new_messages);
          } else if (data.type === 'intent_changed' && onIntentChangedRef.current) {
            // Intent analysis changed - notify for UI update and notification
            onIntentChangedRef.current(data);
          } else if (data.type === 'context_updated' && onContextUpdatedRef.current) {
            // Context window usage updated - notify for UI update
            onContextUpdatedRef.current(data);
          } else if (data.type === 'server_restarting') {
            // Server is about to restart for update - useVersionCheck handles reconnection
            console.log('[WebSocket] Server restarting:', data.message);
          }
        } catch (e) {
          console.error('[WebSocket] Parse error:', e);
        }
      };

      ws.onclose = () => {
        console.log('[WebSocket] Disconnected, reconnecting in 1s...');
        setIsConnected(false);
        wsRef.current = null;
        // Reconnect after 1 second (reduced from 3s for near real-time updates)
        reconnectTimeoutRef.current = setTimeout(connect, 1000);
      };

      ws.onerror = (e) => {
        console.error('[WebSocket] Error:', e);
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
    console.log('[WebSocket] Subscribing to session:', sessionId);
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
