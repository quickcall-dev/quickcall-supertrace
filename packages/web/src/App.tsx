/**
 * Main application component.
 *
 * Three-panel layout: Sessions | Analytics | Chat
 * Analytics is the hero - center of the screen, collapsible.
 *
 * Related: components/ (UI), hooks/ (data), api/client.ts
 */

import { useState, useEffect, useCallback } from 'react';
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
  type MetricsResponse,
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

  // Session metrics
  const { metrics, loading: metricsLoading, updateMetrics } = useSessionMetrics({
    sessionId: selectedSessionId,
  });

  // Handle new events from WebSocket
  const handleNewEvent = useCallback((event: Event) => {
    // Update events if viewing the same session
    if (event.session_id === selectedSessionId) {
      setEvents((prev) => [...prev, event]);
    }

    // Update session list (move active session to top)
    setSessions((prev) => {
      const existing = prev.find((s) => s.id === event.session_id);
      if (existing) {
        // Move to top
        return [existing, ...prev.filter((s) => s.id !== event.session_id)];
      }
      // New session - will be fetched on next refresh
      return prev;
    });
  }, [selectedSessionId]);

  // Handle metrics updates from WebSocket
  const handleMetricsUpdate = useCallback(
    (sessionId: string, newMetrics: MetricsResponse) => {
      if (sessionId === selectedSessionId) {
        updateMetrics(newMetrics);
      }
    },
    [selectedSessionId, updateMetrics]
  );

  useWebSocket({
    onEvent: handleNewEvent,
    onMetricsUpdate: handleMetricsUpdate,
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

  // Load session details when selected
  useEffect(() => {
    if (!selectedSessionId) {
      setSelectedSession(null);
      setEvents([]);
      return;
    }

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
  }, [selectedSessionId]);

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
      />

      {/* Chat/Events - right panel */}
      <SessionView
        session={selectedSession}
        events={events}
        isLoading={isLoading}
      />
    </div>
  );
}

export default App;
