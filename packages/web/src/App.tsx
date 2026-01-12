/**
 * Main application component.
 *
 * Three-panel layout: Sessions | Analytics | Chat
 * Analytics is the hero - center of the screen, collapsible.
 *
 * Related: components/ (UI), hooks/ (data), api/client.ts
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { SessionList } from './components/SessionList';
import { SessionView } from './components/SessionView';
import { AnalyticsPanel } from './components/AnalyticsPanel';
import { useWebSocket } from './hooks/useWebSocket';
import { useSessionMetrics } from './hooks/useSessionMetrics';
import { useTheme } from './hooks/useTheme';
import {
  getSessions,
  getSession,
  searchEvents,
  type Session,
  type Event,
} from './api/client';

function App() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);
  const [selectedSession, setSelectedSession] = useState<Session | null>(null);
  const [events, setEvents] = useState<Event[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [analyticsExpanded, setAnalyticsExpanded] = useState(true);

  // Theme
  const { isDark, toggleTheme } = useTheme();

  // Ref for scrolling to events in SessionView
  const scrollToEventRef = useRef<((eventId: number) => void) | null>(null);

  // Handle scroll to event from analytics panel
  const handleScrollToEvent = useCallback((eventId: number) => {
    scrollToEventRef.current?.(eventId);
  }, []);

  // Session metrics (lazy loaded when session selected)
  const { metrics, loading: metricsLoading } = useSessionMetrics({
    sessionId: selectedSessionId,
  });

  // Handle new events from WebSocket (only for subscribed session)
  const handleNewEvent = useCallback((event: Event) => {
    // Update events - server only sends events for subscribed session
    setEvents((prev) => [...prev, event]);

    // Move session to top of list
    setSessions((prev) => {
      const existing = prev.find((s) => s.id === event.session_id);
      if (existing) {
        return [existing, ...prev.filter((s) => s.id !== event.session_id)];
      }
      return prev;
    });
  }, []);

  // Handle new session notifications (refresh session list)
  const handleNewSession = useCallback(async () => {
    try {
      const data = await getSessions();
      setSessions(data.sessions);
    } catch (error) {
      console.error('Failed to refresh sessions:', error);
    }
  }, []);

  const { subscribe } = useWebSocket({
    onEvent: handleNewEvent,
    onNewSession: handleNewSession,
  });

  // Load sessions on mount
  useEffect(() => {
    const loadSessions = async () => {
      try {
        const data = await getSessions();
        setSessions(data.sessions);
      } catch (error) {
        console.error('Failed to load sessions:', error);
      }
    };

    loadSessions();

    // Refresh sessions periodically
    const interval = setInterval(loadSessions, 30000);
    return () => clearInterval(interval);
  }, []);

  // Load session details when selected and subscribe to updates
  useEffect(() => {
    if (!selectedSessionId) {
      setSelectedSession(null);
      setEvents([]);
      return;
    }

    // Subscribe to this session's WebSocket updates
    subscribe(selectedSessionId);

    const loadSession = async () => {
      setIsLoading(true);
      try {
        const data = await getSession(selectedSessionId);
        setSelectedSession(data.session);
        setEvents(data.events);
      } catch (error) {
        console.error('Failed to load session:', error);
      } finally {
        setIsLoading(false);
      }
    };

    loadSession();
  }, [selectedSessionId, subscribe]);

  // Handle search
  const handleSearch = async (query: string) => {
    if (!query.trim()) {
      // Reset to all sessions
      const data = await getSessions();
      setSessions(data.sessions);
      return;
    }

    try {
      const results = await searchEvents(query);
      // Get unique session IDs from search results
      const sessionIds = [...new Set(results.results.map((r) => r.session_id))];
      // Filter sessions to those matching search
      setSessions((prev) => prev.filter((s) => sessionIds.includes(s.id)));
    } catch (error) {
      console.error('Search failed:', error);
    }
  };

  return (
    <div className="h-screen flex bg-background text-foreground">
      {/* Sessions list - narrow left panel */}
      <SessionList
        sessions={sessions}
        selectedId={selectedSessionId}
        onSelect={setSelectedSessionId}
        onSearch={handleSearch}
        isDark={isDark}
        onToggleTheme={toggleTheme}
      />

      {/* Analytics - center panel (the hero) */}
      <AnalyticsPanel
        metrics={metrics}
        loading={metricsLoading}
        expanded={analyticsExpanded}
        onToggle={() => setAnalyticsExpanded(!analyticsExpanded)}
        onScrollToEvent={handleScrollToEvent}
      />

      {/* Chat/Events - right panel */}
      <SessionView
        session={selectedSession}
        events={events}
        isLoading={isLoading}
        onScrollToEventRef={scrollToEventRef}
      />
    </div>
  );
}

export default App;
