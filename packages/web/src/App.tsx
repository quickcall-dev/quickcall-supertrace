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
import { useTheme } from './hooks/useTheme';
import {
  getSessions,
  getSession,
  getSessionEvents,
  getSessionMetrics,
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
  const [totalEvents, setTotalEvents] = useState<number>(0);
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [analyticsExpanded, setAnalyticsExpanded] = useState(true);

  // Theme
  const { isDark, toggleTheme } = useTheme();

  // Ref for scrolling to events in SessionView
  const scrollToEventRef = useRef<((eventId: number) => void) | null>(null);

  // Handle scroll to event from analytics panel
  const handleScrollToEvent = useCallback((eventId: number) => {
    scrollToEventRef.current?.(eventId);
  }, []);

  // Session metrics - loaded in parallel with session data
  const [metrics, setMetrics] = useState<MetricsResponse | null>(null);
  const [metricsLoading, setMetricsLoading] = useState(false);
  const [metricsHoursBack, setMetricsHoursBack] = useState<number>(2); // Default: last 2 hours

  // Handle new events from WebSocket (only for subscribed session)
  const handleNewEvent = useCallback((event: Event) => {
    // Update events - server only sends events for subscribed session
    setEvents((prev) => [...prev, event]);
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

  // Load session details and metrics in parallel when selected
  useEffect(() => {
    if (!selectedSessionId) {
      setSelectedSession(null);
      setEvents([]);
      setMetrics(null);
      return;
    }

    // Subscribe to this session's WebSocket updates
    subscribe(selectedSessionId);

    let cancelled = false;

    // Load session and metrics in parallel
    const loadData = async () => {
      setIsLoading(true);
      setMetricsLoading(true);

      // Start both requests simultaneously - load only last 50 events initially
      const sessionPromise = getSession(selectedSessionId, 50);
      const metricsPromise = getSessionMetrics(selectedSessionId, metricsHoursBack);

      // Handle session data
      try {
        const data = await sessionPromise;
        if (!cancelled) {
          setSelectedSession(data.session);
          setEvents(data.events);
          setTotalEvents(data.total_events || data.events.length);
        }
      } catch (error) {
        console.error('Failed to load session:', error);
        if (!cancelled) {
          setSelectedSession(null);
          setEvents([]);
          setTotalEvents(0);
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }

      // Handle metrics data
      try {
        const metricsData = await metricsPromise;
        if (!cancelled) {
          setMetrics(metricsData.metrics);
        }
      } catch (error) {
        console.error('Failed to load metrics:', error);
        if (!cancelled) {
          setMetrics(null);
        }
      } finally {
        if (!cancelled) {
          setMetricsLoading(false);
        }
      }
    };

    loadData();

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedSessionId]);

  // Handle time range change for metrics
  const handleTimeRangeChange = useCallback(async (hours: number) => {
    setMetricsHoursBack(hours);
    if (!selectedSessionId) return;

    setMetricsLoading(true);
    try {
      const metricsData = await getSessionMetrics(selectedSessionId, hours);
      setMetrics(metricsData.metrics);
    } catch (error) {
      console.error('Failed to load metrics:', error);
    } finally {
      setMetricsLoading(false);
    }
  }, [selectedSessionId]);

  // Load more (older) events
  const handleLoadMore = useCallback(async () => {
    if (!selectedSessionId || isLoadingMore || events.length === 0) return;
    if (events.length >= totalEvents) return; // Already have all events

    setIsLoadingMore(true);
    try {
      // Get the oldest event we have and load events before it
      const oldestEventId = events[0]?.id;
      if (!oldestEventId) return;

      const data = await getSessionEvents(selectedSessionId, 50, oldestEventId);
      if (data.events.length > 0) {
        // Prepend older events to the beginning
        setEvents((prev) => [...data.events, ...prev]);
      }
    } catch (error) {
      console.error('Failed to load more events:', error);
    } finally {
      setIsLoadingMore(false);
    }
  }, [selectedSessionId, isLoadingMore, events, totalEvents]);

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

  // Show welcome screen when no session selected
  if (!selectedSessionId) {
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

        {/* Welcome screen spanning main area */}
        <div className="flex-1 flex items-center justify-center bg-background border-l border-border">
          <div className="text-center max-w-lg px-8">
            {/* Logo/Icon */}
            <div className="w-24 h-24 mx-auto mb-8 bg-gradient-to-br from-teal-500/20 to-primary/20 rounded-3xl flex items-center justify-center border border-border shadow-sm">
              <i className="ri-line-chart-line text-teal-500 text-4xl"></i>
            </div>

            {/* Title */}
            <h1 className="text-2xl font-semibold text-foreground mb-3">
              Welcome to SuperTrace
            </h1>

            {/* Description */}
            <p className="text-muted-foreground mb-8 leading-relaxed">
              Monitor your Claude Code sessions with detailed analytics, token usage tracking, and conversation history.
            </p>

            {/* Quick tips */}
            <div className="text-left bg-muted/30 rounded-xl p-5 space-y-3 border border-border/50">
              <div className="flex items-center gap-3 text-sm">
                <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
                  <i className="ri-cursor-line text-primary"></i>
                </div>
                <span className="text-foreground">Select a session from the sidebar to begin</span>
              </div>
              <div className="flex items-center gap-3 text-sm">
                <div className="w-8 h-8 rounded-lg bg-teal-500/10 flex items-center justify-center shrink-0">
                  <i className="ri-bar-chart-2-line text-teal-500"></i>
                </div>
                <span className="text-foreground">View token costs, tool usage, and timing metrics</span>
              </div>
              <div className="flex items-center gap-3 text-sm">
                <div className="w-8 h-8 rounded-lg bg-amber-500/10 flex items-center justify-center shrink-0">
                  <i className="ri-time-line text-amber-500"></i>
                </div>
                <span className="text-foreground">Filter by time range to focus on recent activity</span>
              </div>
            </div>

            {/* Session count hint */}
            {sessions.length > 0 && (
              <p className="mt-6 text-sm text-muted-foreground">
                <i className="ri-folder-3-line mr-1"></i>
                {sessions.length} session{sessions.length !== 1 ? 's' : ''} available
              </p>
            )}
          </div>
        </div>
      </div>
    );
  }

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
        hoursBack={metricsHoursBack}
        onTimeRangeChange={handleTimeRangeChange}
      />

      {/* Chat/Events - right panel */}
      <SessionView
        session={selectedSession}
        events={events}
        isLoading={isLoading}
        onScrollToEventRef={scrollToEventRef}
        totalEvents={totalEvents}
        isLoadingMore={isLoadingMore}
        onLoadMore={handleLoadMore}
      />
    </div>
  );
}

export default App;
