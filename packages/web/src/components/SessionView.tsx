/**
 * Session detail view component.
 *
 * Displays conversation with clean header, messages, tools, and stats.
 * Professional enterprise-ready design. Uses Remix Icons.
 */

import { useEffect, useLayoutEffect, useRef, useCallback, useState, useMemo, type MutableRefObject } from 'react';
import type { Session, Event } from '../api/client';
import { getExportUrl } from '../api/client';
import { formatDate, formatTime } from '../utils/time';
import { MessageBubble } from './MessageBubble';
import { ToolGroup } from './ToolGroup';

interface SessionViewProps {
  session: Session | null;
  events: Event[];
  isLoading: boolean;
  onScrollToEventRef?: MutableRefObject<((eventId: number) => void) | null>;
  totalEvents?: number;
  hasMoreEvents?: boolean;
  isLoadingMore?: boolean;
  onLoadMore?: () => void;
  onRefresh?: () => Promise<void>;
  isRefreshing?: boolean;
}

type GroupedItem =
  | { type: 'single'; event: Event }
  | { type: 'tool_group'; events: Event[] };

function groupEvents(events: Event[]): GroupedItem[] {
  const result: GroupedItem[] = [];
  let currentToolGroup: Event[] = [];

  for (const event of events) {
    if (event.event_type === 'tool_use') {
      currentToolGroup.push(event);
    } else {
      if (currentToolGroup.length > 0) {
        result.push({ type: 'tool_group', events: currentToolGroup });
        currentToolGroup = [];
      }
      result.push({ type: 'single', event });
    }
  }

  if (currentToolGroup.length > 0) {
    result.push({ type: 'tool_group', events: currentToolGroup });
  }

  return result;
}

export function SessionView({
  session,
  events,
  isLoading,
  onScrollToEventRef,
  totalEvents = 0,
  hasMoreEvents = true,
  isLoadingMore = false,
  onLoadMore,
  onRefresh,
  isRefreshing = false,
}: SessionViewProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const loadMoreTriggerRef = useRef<HTMLDivElement>(null);
  const eventRefs = useRef<Map<number, HTMLDivElement>>(new Map());
  const [copied, setCopied] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [showSearch, setShowSearch] = useState(false);
  const searchInputRef = useRef<HTMLInputElement>(null);

  // Scroll to bottom button state
  const [isAtBottom, setIsAtBottom] = useState(true);

  // Clear event refs and search when session changes
  useEffect(() => {
    eventRefs.current.clear();
    setSearchQuery('');
    setShowSearch(false);
    setIsAtBottom(true);
  }, [session?.id]);

  // Check if at bottom helper
  const checkIfAtBottom = useCallback(() => {
    const container = scrollRef.current;
    if (!container) return true;
    const threshold = 100; // Within 100px of bottom is considered "at bottom"
    return container.scrollHeight - container.scrollTop - container.clientHeight < threshold;
  }, []);

  // Track scroll position to detect if user is at bottom
  useEffect(() => {
    const container = scrollRef.current;
    if (!container) return;

    const handleScroll = () => {
      setIsAtBottom(checkIfAtBottom());
    };

    // Check initial scroll position
    handleScroll();

    container.addEventListener('scroll', handleScroll);
    return () => container.removeEventListener('scroll', handleScroll);
  }, [checkIfAtBottom]);

  // Re-check scroll position when events change (in case content height changed)
  useEffect(() => {
    // Use setTimeout to let the DOM update first
    const timeoutId = setTimeout(() => {
      setIsAtBottom(checkIfAtBottom());
    }, 50);
    return () => clearTimeout(timeoutId);
  }, [events.length, checkIfAtBottom]);

  // Scroll to bottom function
  const scrollToBottom = useCallback(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTo({
        top: scrollRef.current.scrollHeight,
        behavior: 'smooth'
      });
    }
  }, []);

  // Keyboard shortcut for search (Cmd+F / Ctrl+F)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'f') {
        e.preventDefault();
        setShowSearch(true);
        setTimeout(() => searchInputRef.current?.focus(), 0);
      }
      if (e.key === 'Escape' && showSearch) {
        setShowSearch(false);
        setSearchQuery('');
      }
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [showSearch]);

  // Search matching - check if event contains search query
  const matchesSearch = useCallback((event: Event, query: string): boolean => {
    if (!query.trim()) return true;
    const lowerQuery = query.toLowerCase();

    // Check event type
    if (event.event_type.toLowerCase().includes(lowerQuery)) return true;

    // Check event data
    if (event.data) {
      const dataStr = JSON.stringify(event.data).toLowerCase();
      if (dataStr.includes(lowerQuery)) return true;
    }

    return false;
  }, []);

  // Memoize grouped events to avoid recalculating on every render
  const groupedEvents = useMemo(() => groupEvents(events), [events]);

  // Filter events based on search query
  const filteredGroupedEvents = useMemo(() => {
    if (!searchQuery.trim()) return groupedEvents;

    return groupedEvents.filter(item => {
      if (item.type === 'single') {
        return matchesSearch(item.event, searchQuery);
      }
      // For tool groups, include if any event matches
      return item.events.some(e => matchesSearch(e, searchQuery));
    });
  }, [groupedEvents, searchQuery, matchesSearch]);

  // Count matching events
  const matchCount = useMemo(() => {
    if (!searchQuery.trim()) return 0;
    let count = 0;
    for (const item of groupedEvents) {
      if (item.type === 'single') {
        if (matchesSearch(item.event, searchQuery)) count++;
      } else {
        count += item.events.filter(e => matchesSearch(e, searchQuery)).length;
      }
    }
    return count;
  }, [groupedEvents, searchQuery, matchesSearch]);

  // Infinite scroll - load more when scrolling to top
  // Store scroll height before loading to restore position after
  const prevScrollHeightRef = useRef<number>(0);
  const prevEventCountRef = useRef<number>(0);

  // After events change, adjust scroll to maintain position
  // useLayoutEffect ensures DOM updates happen synchronously before paint
  // to avoid visual flicker when adjusting scroll position
  useLayoutEffect(() => {
    if (scrollRef.current && prevScrollHeightRef.current > 0) {
      const newScrollHeight = scrollRef.current.scrollHeight;
      const heightDiff = newScrollHeight - prevScrollHeightRef.current;
      if (heightDiff > 0 && events.length > prevEventCountRef.current) {
        // Events were prepended, adjust scroll position
        scrollRef.current.scrollTop += heightDiff;
      }
    }
    prevEventCountRef.current = events.length;
  }, [events]);

  useEffect(() => {
    const trigger = loadMoreTriggerRef.current;
    const container = scrollRef.current;
    if (!trigger || !container || !onLoadMore || !hasMoreEvents) return;

    const observer = new IntersectionObserver(
      (entries) => {
        const entry = entries[0];
        if (entry.isIntersecting && !isLoadingMore && hasMoreEvents) {
          // Store current scroll height before loading
          prevScrollHeightRef.current = container.scrollHeight;
          onLoadMore();
        }
      },
      { threshold: 0.1 }
    );

    observer.observe(trigger);
    return () => observer.disconnect();
  }, [onLoadMore, isLoadingMore, hasMoreEvents]);

  // Scroll to event function
  const scrollToEvent = useCallback((eventId: number) => {
    const element = eventRefs.current.get(eventId);
    if (element && scrollRef.current) {
      element.scrollIntoView({ behavior: 'smooth', block: 'center' });
      // Add highlight effect
      element.classList.add('ring-2', 'ring-primary', 'ring-offset-2');
      setTimeout(() => {
        element.classList.remove('ring-2', 'ring-primary', 'ring-offset-2');
      }, 2000);
    }
  }, []);

  // Register scroll function with parent
  useEffect(() => {
    if (onScrollToEventRef) {
      onScrollToEventRef.current = scrollToEvent;
    }
    return () => {
      if (onScrollToEventRef) {
        onScrollToEventRef.current = null;
      }
    };
  }, [onScrollToEventRef, scrollToEvent]);

  // Scroll to bottom only on initial load
  const hasScrolledRef = useRef<boolean>(false);

  useEffect(() => {
    if (scrollRef.current && events.length > 0 && !hasScrolledRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
      hasScrolledRef.current = true;
    }
  }, [events]);

  // Loading state - check this BEFORE checking session
  if (isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center bg-background">
        <div className="flex items-center gap-3 text-muted-foreground">
          <i className="ri-loader-4-line animate-spin text-xl"></i>
          <span className="text-sm">Loading session...</span>
        </div>
      </div>
    );
  }

  // Note: Empty state is handled in App.tsx with welcome screen
  if (!session) {
    return null;
  }

  const getProjectName = (path: string | null) => {
    if (!path) return 'Unknown Project';
    const parts = path.split('/');
    return parts[parts.length - 1] || path;
  };

  const isActive = session.started_at && !session.ended_at;

  // Get session file path for clipboard
  // Prefer file_path from server (set during import), fallback to session ID
  const getSessionFilePath = () => {
    return session.file_path || session.id;
  };

  const copySessionPath = () => {
    navigator.clipboard.writeText(getSessionFilePath());
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };


  return (
    <div className="flex-1 flex flex-col h-full bg-background relative">
      {/* Header - compact single row */}
      <div className="h-12 px-4 border-b border-border bg-background/95 backdrop-blur-sm flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3 text-sm min-w-0 overflow-hidden">
          <span className="font-semibold text-foreground truncate">{getProjectName(session.project_path)}</span>
          {isActive && (
            <span className="flex items-center gap-1 text-[10px] bg-[color:var(--success)]/20 text-[color:var(--success)] px-1.5 py-0.5 rounded-full">
              <span className="w-1.5 h-1.5 bg-[color:var(--success)] rounded-full animate-pulse" />
              Live
            </span>
          )}
          <span className="text-muted-foreground/50">·</span>
          <span className="text-muted-foreground text-xs flex items-center gap-1">
            <i className="ri-calendar-line" />
            {formatDate(session.started_at)}
          </span>
          <span className="text-muted-foreground text-xs flex items-center gap-1">
            <i className="ri-time-line" />
            {formatTime(session.started_at)}
          </span>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {/* Refresh button */}
          {onRefresh && (
            <button
              onClick={onRefresh}
              disabled={isRefreshing}
              className={`p-1.5 rounded transition-colors ${
                isRefreshing
                  ? 'text-muted-foreground cursor-not-allowed'
                  : 'text-muted-foreground hover:text-foreground hover:bg-accent'
              }`}
              title="Refresh session"
            >
              <i className={`ri-refresh-line text-sm ${isRefreshing ? 'animate-spin' : ''}`} />
            </button>
          )}
          {/* Search */}
          {showSearch ? (
            <div className="flex items-center gap-2 bg-muted rounded-lg px-2 py-1">
              <i className="ri-search-line text-muted-foreground text-sm" />
              <input
                ref={searchInputRef}
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search messages..."
                className="bg-transparent border-none outline-none text-xs w-32 text-foreground placeholder:text-muted-foreground"
              />
              {searchQuery ? (
                <span className="text-[10px] text-muted-foreground">
                  {matchCount} match{matchCount !== 1 ? 'es' : ''}
                </span>
              ) : (
                <span className="text-[10px] text-muted-foreground/60">⌘F</span>
              )}
              <button
                onClick={() => { setShowSearch(false); setSearchQuery(''); }}
                className="text-muted-foreground hover:text-foreground p-0.5"
              >
                <i className="ri-close-line text-sm" />
              </button>
            </div>
          ) : (
            <button
              onClick={() => { setShowSearch(true); setTimeout(() => searchInputRef.current?.focus(), 0); }}
              className="p-1.5 text-muted-foreground hover:text-foreground hover:bg-accent rounded transition-colors flex items-center gap-1"
              title="Search (⌘F)"
            >
              <i className="ri-search-line text-sm" />
              <span className="text-[10px] text-muted-foreground/60">⌘F</span>
            </button>
          )}
          <span className="text-muted-foreground/30">|</span>
          <a
            href={getExportUrl(session.id, 'json')}
            download
            className="px-2 py-1 text-[10px] font-medium text-muted-foreground hover:text-foreground hover:bg-accent rounded transition-colors"
            title="Export JSON"
          >
            JSON
          </a>
          <a
            href={getExportUrl(session.id, 'md')}
            download
            className="px-2 py-1 text-[10px] font-medium text-muted-foreground hover:text-foreground hover:bg-accent rounded transition-colors"
            title="Export Markdown"
          >
            MD
          </a>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 relative overflow-hidden">
        <div ref={scrollRef} className="h-full overflow-y-auto px-6 py-6">
          <div className="max-w-4xl mx-auto space-y-4">
            {/* Infinite scroll trigger at top */}
            {events.length > 0 && hasMoreEvents && (
              <div ref={loadMoreTriggerRef} className="flex justify-center py-3">
                {isLoadingMore ? (
                  <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <i className="ri-loader-4-line animate-spin" />
                    Loading older messages...
                  </div>
                ) : (
                  <div className="text-xs text-muted-foreground">
                    Scroll up for more
                  </div>
                )}
              </div>
            )}
            {filteredGroupedEvents.length === 0 ? (
              <div className="text-center py-12">
                <div className="w-12 h-12 mx-auto mb-3 bg-muted rounded-full flex items-center justify-center">
                  <i className={`${searchQuery ? 'ri-search-line' : 'ri-chat-3-line'} text-muted-foreground text-xl`}></i>
                </div>
                <p className="text-sm text-muted-foreground">
                  {searchQuery ? `No results for "${searchQuery}"` : 'No messages yet'}
                </p>
              </div>
            ) : (
              filteredGroupedEvents.map((item, idx) => {
                if (item.type === 'tool_group') {
                  // For tool groups, get the first event's ID for the ref
                  const firstEventId = item.events[0]?.id;
                  return (
                    <div
                      key={`group-${idx}`}
                      ref={(el) => {
                        if (el && firstEventId) {
                          eventRefs.current.set(firstEventId, el);
                          // Also register all events in the group
                          item.events.forEach(e => eventRefs.current.set(e.id, el));
                        }
                      }}
                      className="transition-all duration-300"
                    >
                      <ToolGroup events={item.events} />
                    </div>
                  );
                }
                return (
                  <div
                    key={item.event.id}
                    ref={(el) => {
                      if (el) eventRefs.current.set(item.event.id, el);
                    }}
                    className="transition-all duration-300"
                  >
                    <MessageBubble event={item.event} />
                  </div>
                );
              })
            )}
          </div>
        </div>

      </div>

      {/* Scroll to bottom button - shows when not at bottom
          NOTE: z-50 is critical! The footer has backdrop-blur-sm which creates a
          stacking context. Don't lower the z-index! */}
      {!isAtBottom && (
        <div className="absolute bottom-10 left-0 right-0 pointer-events-none z-50">
          {/* Gradient fade */}
          <div className="h-16 bg-gradient-to-t from-background via-background/80 to-transparent" />
          {/* Button */}
          <div className="flex justify-center pb-3 bg-background">
            <button
              onClick={scrollToBottom}
              className="pointer-events-auto flex items-center gap-2 px-4 py-2 bg-muted hover:bg-accent border border-border rounded-full shadow-sm transition-colors"
            >
              <span className="text-sm font-medium text-foreground">New messages</span>
              <i className="ri-arrow-down-line text-foreground" />
            </button>
          </div>
        </div>
      )}

      {/* Footer */}
      <div className="px-6 py-3 border-t border-border bg-background/95 backdrop-blur-sm">
        <div className="flex items-center justify-between text-[11px] text-muted-foreground">
          <button
            onClick={copySessionPath}
            className={`font-mono flex items-center gap-1 cursor-pointer transition-colors ${copied ? 'text-[color:var(--success)]' : 'hover:text-primary'}`}
            title={getSessionFilePath()}
          >
            <i className={copied ? 'ri-check-line' : 'ri-fingerprint-line'}></i>
            {copied ? 'Copied!' : session.id.slice(0, 8)}
          </button>
          <span>
            {events.length === totalEvents || totalEvents === 0
              ? `${events.length} events`
              : `${events.length} of ${totalEvents} events`}
          </span>
        </div>
      </div>
    </div>
  );
}
