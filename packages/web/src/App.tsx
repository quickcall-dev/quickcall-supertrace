/**
 * Main application component.
 *
 * Manages global state for sessions and events, handles WebSocket
 * updates, and renders the two-panel layout.
 *
 * Related: components/ (UI), hooks/useWebSocket.ts (realtime), api/client.ts
 */

import { useState, useEffect, useCallback } from 'react';
import { SessionList } from './components/SessionList';
import { SessionView } from './components/SessionView';
import { useWebSocket } from './hooks/useWebSocket';
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

  const { isConnected } = useWebSocket({ onEvent: handleNewEvent });

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
    <div className="h-screen flex">
      <SessionList
        sessions={sessions}
        selectedId={selectedSessionId}
        onSelect={setSelectedSessionId}
        onSearch={handleSearch}
      />
      <SessionView
        session={selectedSession}
        events={events}
        isLoading={isLoading}
      />
    </div>
  );
}

export default App;
