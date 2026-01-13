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
  const [hasMoreEvents, setHasMoreEvents] = useState(true);
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [analyticsExpanded, setAnalyticsExpanded] = useState(true);

  // Theme
  const { isDark, toggleTheme } = useTheme();

  // Ref for scrolling to events in SessionView
  const scrollToEventRef = useRef<((eventId: number) => void) | null>(null);
  const [isJumpingToEvent, setIsJumpingToEvent] = useState(false);

  // Handle scroll to event from analytics panel
  // If event not loaded, load all events first then scroll
  const handleScrollToEvent = useCallback(async (eventId: number) => {
    // Prevent multiple clicks while already loading
    if (isJumpingToEvent || isLoadingMore) return;

    // Check if event is already loaded
    const eventExists = events.some(e => e.id === eventId);

    if (eventExists) {
      scrollToEventRef.current?.(eventId);
      return;
    }

    // Event not loaded - need to load all events
    if (!selectedSessionId) return;

    setIsJumpingToEvent(true);
    setIsLoadingMore(true);
    try {
      // Load all events (pass 0 for unlimited)
      const data = await getSession(selectedSessionId, 0);
      setEvents(data.events);
      setTotalEvents(data.total_events || data.events.length);

      // Scroll after state updates
      setTimeout(() => {
        scrollToEventRef.current?.(eventId);
        setIsJumpingToEvent(false);
      }, 100);
    } catch (error) {
      console.error('Failed to load events for scroll:', error);
      setIsJumpingToEvent(false);
    } finally {
      setIsLoadingMore(false);
    }
  }, [events, selectedSessionId, isJumpingToEvent, isLoadingMore]);

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
      setHasMoreEvents(true);
      return;
    }

    // Reset hasMoreEvents when selecting a new session
    setHasMoreEvents(true);

    // Subscribe to this session's WebSocket updates
    subscribe(selectedSessionId);

    let cancelled = false;

    // Load session and metrics in parallel
    const loadData = async () => {
      setIsLoading(true);
      setMetricsLoading(true);

      // Start both requests simultaneously - load only last 30 events initially
      const sessionPromise = getSession(selectedSessionId, 30);
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
    if (!hasMoreEvents) return; // Already loaded all events

    setIsLoadingMore(true);
    try {
      // Get the oldest event we have and load events before it
      const oldestEventId = events[0]?.id;
      if (!oldestEventId) return;

      const data = await getSessionEvents(selectedSessionId, 20, oldestEventId);
      if (data.events.length > 0) {
        // Prepend older events to the beginning
        setEvents((prev) => [...data.events, ...prev]);
      } else {
        // No more events to load
        setHasMoreEvents(false);
      }
    } catch (error) {
      console.error('Failed to load more events:', error);
    } finally {
      setIsLoadingMore(false);
    }
  }, [selectedSessionId, isLoadingMore, events, hasMoreEvents]);

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
          onSessionsImported={handleNewSession}
          isDark={isDark}
          onToggleTheme={toggleTheme}
        />

        {/* Welcome screen spanning main area */}
        <div className="flex-1 flex items-center justify-center bg-background border-l border-border relative overflow-hidden">
          {/* Subtle background pattern */}
          <div className="absolute inset-0 opacity-[0.03]">
            <div className="absolute top-1/4 -left-20 w-96 h-96 bg-primary rounded-full blur-3xl" />
            <div className="absolute bottom-1/4 -right-20 w-80 h-80 bg-teal-500 rounded-full blur-3xl" />
          </div>

          <div className="text-center max-w-xl px-8 relative z-10">
            {/* Logo */}
            <div className="mb-10">
              <div className="inline-flex items-center gap-3 px-5 py-2.5 bg-card/80 backdrop-blur-sm rounded-2xl border border-border/50 shadow-lg">
                <img src="/favicon.svg" alt="QuickCall" className="w-10 h-10 rounded-xl shadow-md" />
                <div className="text-left">
                  <div className="text-xs font-medium text-muted-foreground uppercase tracking-wider">QuickCall</div>
                  <div className="text-lg font-bold text-foreground -mt-0.5">SuperTrace</div>
                </div>
              </div>
            </div>

            {/* Title */}
            <h1 className="text-3xl font-bold text-foreground mb-4">
              Welcome to QuickCall - SuperTrace
            </h1>

            {/* Description */}
            <p className="text-muted-foreground mb-10 leading-relaxed text-lg">
              Real-time session monitoring for Claude Code. Track token usage, analyze tool patterns, and optimize your AI workflows.
            </p>

            {/* Feature cards */}
            <div className="grid grid-cols-3 gap-4 mb-10">
              <div className="bg-card/60 backdrop-blur-sm rounded-xl p-4 border border-border/50 hover:border-primary/30 transition-colors group">
                <div className="w-10 h-10 mx-auto mb-3 rounded-lg bg-gradient-to-br from-primary/20 to-primary/5 flex items-center justify-center group-hover:scale-110 transition-transform">
                  <i className="ri-coins-line text-primary text-lg"></i>
                </div>
                <div className="text-sm font-semibold text-foreground">Cost Tracking</div>
                <div className="text-xs text-muted-foreground mt-1">Monitor API spend</div>
              </div>
              <div className="bg-card/60 backdrop-blur-sm rounded-xl p-4 border border-border/50 hover:border-teal-500/30 transition-colors group">
                <div className="w-10 h-10 mx-auto mb-3 rounded-lg bg-gradient-to-br from-teal-500/20 to-teal-500/5 flex items-center justify-center group-hover:scale-110 transition-transform">
                  <i className="ri-tools-line text-teal-500 text-lg"></i>
                </div>
                <div className="text-sm font-semibold text-foreground">Tool Analytics</div>
                <div className="text-xs text-muted-foreground mt-1">Usage patterns</div>
              </div>
              <div className="bg-card/60 backdrop-blur-sm rounded-xl p-4 border border-border/50 hover:border-amber-500/30 transition-colors group">
                <div className="w-10 h-10 mx-auto mb-3 rounded-lg bg-gradient-to-br from-amber-500/20 to-amber-500/5 flex items-center justify-center group-hover:scale-110 transition-transform">
                  <i className="ri-time-line text-amber-500 text-lg"></i>
                </div>
                <div className="text-sm font-semibold text-foreground">Time Analysis</div>
                <div className="text-xs text-muted-foreground mt-1">Performance insights</div>
              </div>
            </div>

            {/* Call to action */}
            <div className="inline-flex items-center gap-2 text-sm text-muted-foreground bg-muted/50 px-4 py-2 rounded-full">
              <i className="ri-arrow-left-line"></i>
              <span>Select a session from the sidebar to get started</span>
            </div>

            {/* Session count */}
            {sessions.length > 0 && (
              <div className="mt-6 text-sm text-muted-foreground">
                <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-primary/10 text-primary rounded-full font-medium">
                  <i className="ri-stack-line"></i>
                  {sessions.length} session{sessions.length !== 1 ? 's' : ''} available
                </span>
              </div>
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
        onSessionsImported={handleNewSession}
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
        isJumpingToEvent={isJumpingToEvent}
      />

      {/* Chat/Events - right panel */}
      <SessionView
        session={selectedSession}
        events={events}
        isLoading={isLoading}
        onScrollToEventRef={scrollToEventRef}
        totalEvents={totalEvents}
        hasMoreEvents={hasMoreEvents}
        isLoadingMore={isLoadingMore}
        onLoadMore={handleLoadMore}
      />
    </div>
  );
}

export default App;
