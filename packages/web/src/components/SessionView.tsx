/**
 * Session detail view component.
 *
 * Displays conversation with clean header, messages, tools, and stats.
 * Professional enterprise-ready design. Uses Remix Icons.
 */

import { useEffect, useLayoutEffect, useRef, useCallback, useState, useMemo, type MutableRefObject } from 'react';
import type { Session, Event, SessionContextData } from '../api/client';
import { getExportUrl, getSessionContext } from '../api/client';
import { formatDate, formatTime } from '../utils/time';
import { MessageBubble } from './MessageBubble';
import { ToolGroup } from './ToolGroup';
import { ContextWindowBar, type ContextData } from './ContextWindowBar';

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
  hasNewMessages?: boolean;
  onClearNewMessages?: () => void;
  onLoadAllForSearch?: () => Promise<void>;
  isLoadingAllForSearch?: boolean;
  contextData?: ContextData | null;
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
  hasNewMessages = false,
  onClearNewMessages,
  onLoadAllForSearch,
  isLoadingAllForSearch = false,
  contextData: externalContextData,
}: SessionViewProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const loadMoreTriggerRef = useRef<HTMLDivElement>(null);
  const eventRefs = useRef<Map<number, HTMLDivElement>>(new Map());
  const [copied, setCopied] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [showSearch, setShowSearch] = useState(false);
  const [currentMatchIndex, setCurrentMatchIndex] = useState(0);
  const [showAllThinking, setShowAllThinking] = useState(false);
  const searchInputRef = useRef<HTMLInputElement>(null);

  // Context window state - use external data if provided, otherwise fetch
  const [internalContextData, setInternalContextData] = useState<ContextData | null>(null);
  const [isLoadingContext, setIsLoadingContext] = useState(false);

  // Use external context data if provided, otherwise use internal
  const contextData = externalContextData ?? internalContextData;

  // Fetch context data when session changes (if not provided externally)
  useEffect(() => {
    if (externalContextData !== undefined || !session?.id) {
      return;
    }

    const fetchContext = async () => {
      setIsLoadingContext(true);
      try {
        const response = await getSessionContext(session.id);
        if (response.context) {
          setInternalContextData(response.context);
        }
      } catch (error) {
        // Context endpoint may not be available yet (Agent 1 dependency)
        console.debug('[SessionView] Context fetch failed:', error);
      } finally {
        setIsLoadingContext(false);
      }
    };

    fetchContext();
  }, [session?.id, externalContextData]);

  // Scroll to bottom button state
  const [isAtBottom, setIsAtBottom] = useState(true);

  // Clear event refs, search, and context when session changes
  useEffect(() => {
    eventRefs.current.clear();
    setSearchQuery('');
    setShowSearch(false);
    setIsAtBottom(true);
    setInternalContextData(null);
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
  }, [checkIfAtBottom, session?.id, events.length]);

  // Scroll to bottom function
  const scrollToBottom = useCallback(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTo({
        top: scrollRef.current.scrollHeight,
        behavior: 'smooth'
      });
      onClearNewMessages?.();
    }
  }, [onClearNewMessages]);

  // Search matching - exact substring match (case-insensitive)
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

  // Get ordered list of matching event IDs (for navigation)
  const matchingEventList = useMemo(() => {
    if (!searchQuery.trim()) return [];
    const matches: number[] = [];
    for (const item of groupedEvents) {
      if (item.type === 'single') {
        if (matchesSearch(item.event, searchQuery)) {
          matches.push(item.event.id);
        }
      } else {
        for (const e of item.events) {
          if (matchesSearch(e, searchQuery)) {
            matches.push(e.id);
          }
        }
      }
    }
    return matches;
  }, [groupedEvents, searchQuery, matchesSearch]);

  const matchCount = matchingEventList.length;

  // Reset match index when search changes
  useEffect(() => {
    setCurrentMatchIndex(0);
  }, [searchQuery]);

  // Navigate to next/prev match
  const goToMatch = useCallback((index: number) => {
    if (matchingEventList.length === 0) return;
    const clampedIndex = ((index % matchingEventList.length) + matchingEventList.length) % matchingEventList.length;
    setCurrentMatchIndex(clampedIndex);
    const eventId = matchingEventList[clampedIndex];
    const element = eventRefs.current.get(eventId);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'center' });
      element.classList.add('ring-2', 'ring-yellow-400', 'ring-offset-2');
      setTimeout(() => {
        element.classList.remove('ring-2', 'ring-yellow-400', 'ring-offset-2');
      }, 1500);
    }
  }, [matchingEventList]);

  const goToNextMatch = useCallback(() => goToMatch(currentMatchIndex + 1), [goToMatch, currentMatchIndex]);
  const goToPrevMatch = useCallback(() => goToMatch(currentMatchIndex - 1), [goToMatch, currentMatchIndex]);

  // Keyboard shortcut for search (Cmd+F) and navigation (Enter/Shift+Enter)
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
      // Navigate matches with Enter/Shift+Enter when search is active
      if (e.key === 'Enter' && showSearch && searchQuery && matchCount > 0) {
        e.preventDefault();
        if (e.shiftKey) {
          goToPrevMatch();
        } else {
          goToNextMatch();
        }
      }
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [showSearch, searchQuery, matchCount, goToNextMatch, goToPrevMatch]);

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

  // Loading state - skeleton UI
  if (isLoading) {
    return (
      <div className="flex-1 flex flex-col h-full bg-background animate-pulse">
        {/* Header skeleton */}
        <div className="h-12 px-4 border-b border-border flex items-center justify-between shrink-0">
          <div className="flex items-center gap-3">
            <div className="h-4 w-32 bg-muted rounded" />
            <div className="h-4 w-16 bg-muted rounded" />
            <div className="h-4 w-12 bg-muted rounded" />
          </div>
          <div className="flex items-center gap-2">
            <div className="h-6 w-6 bg-muted rounded" />
            <div className="h-6 w-6 bg-muted rounded" />
            <div className="h-6 w-12 bg-muted rounded" />
            <div className="h-6 w-8 bg-muted rounded" />
          </div>
        </div>

        {/* Messages skeleton */}
        <div className="flex-1 overflow-hidden px-6 py-6">
          <div className="max-w-4xl mx-auto space-y-4">
            {/* User message skeleton */}
            <div className="flex justify-end">
              <div className="max-w-[70%] space-y-2">
                <div className="h-4 w-48 bg-primary/20 rounded ml-auto" />
                <div className="h-4 w-64 bg-primary/20 rounded ml-auto" />
              </div>
            </div>

            {/* Assistant message skeleton */}
            <div className="flex justify-start">
              <div className="max-w-[80%] space-y-2">
                <div className="h-4 w-72 bg-muted rounded" />
                <div className="h-4 w-96 bg-muted rounded" />
                <div className="h-4 w-80 bg-muted rounded" />
              </div>
            </div>

            {/* Tool group skeleton */}
            <div className="flex justify-start">
              <div className="w-full max-w-[90%] bg-muted/50 rounded-lg p-3 space-y-2">
                <div className="flex items-center gap-2">
                  <div className="h-4 w-4 bg-muted rounded" />
                  <div className="h-3 w-24 bg-muted rounded" />
                </div>
                <div className="h-3 w-48 bg-muted/70 rounded" />
                <div className="h-3 w-36 bg-muted/70 rounded" />
              </div>
            </div>

            {/* Another user message */}
            <div className="flex justify-end">
              <div className="max-w-[70%] space-y-2">
                <div className="h-4 w-56 bg-primary/20 rounded ml-auto" />
              </div>
            </div>

            {/* Another assistant message */}
            <div className="flex justify-start">
              <div className="max-w-[80%] space-y-2">
                <div className="h-4 w-64 bg-muted rounded" />
                <div className="h-4 w-88 bg-muted rounded" />
              </div>
            </div>
          </div>
        </div>

        {/* Footer skeleton */}
        <div className="px-6 py-3 border-t border-border">
          <div className="flex items-center justify-between">
            <div className="h-3 w-16 bg-muted rounded" />
            <div className="h-3 w-20 bg-muted rounded" />
          </div>
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
      {/* Header - clean, just project name and actions */}
      <div className="px-2 sm:px-4 border-b border-border bg-background/95 backdrop-blur-sm flex items-center justify-between gap-2 shrink-0" style={{ height: 'var(--header-height)' }}>
        <div className="flex items-center gap-1.5 sm:gap-3 text-sm min-w-0">
          <span className="font-semibold text-foreground truncate">{getProjectName(session.project_path)}</span>
          {isActive && (
            <span className="flex items-center gap-1 text-[10px] bg-[color:var(--success)]/20 text-[color:var(--success)] px-1.5 py-0.5 rounded-full">
              <span className="w-1.5 h-1.5 bg-[color:var(--success)] rounded-full animate-pulse" />
              Live
            </span>
          )}
          {/* Context Window Bar */}
          {contextData && (
            <>
              <span className="text-muted-foreground/30 hidden sm:inline">|</span>
              <ContextWindowBar
                sessionId={session.id}
                contextData={contextData}
                isLoading={isLoadingContext}
              />
            </>
          )}
        </div>
        <div className="flex items-center gap-1 sm:gap-2 shrink-0">
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
            <div className="flex items-center gap-1.5 bg-muted rounded-lg px-2 py-1">
              {isLoadingAllForSearch ? (
                <i className="ri-loader-4-line animate-spin text-muted-foreground text-sm" />
              ) : (
                <i className="ri-search-line text-muted-foreground text-sm" />
              )}
              <input
                ref={searchInputRef}
                type="text"
                value={searchQuery}
                onChange={(e) => {
                  const value = e.target.value;
                  setSearchQuery(value);
                  // Load all events when user starts searching and not all are loaded
                  if (value && events.length < totalEvents && onLoadAllForSearch && !isLoadingAllForSearch) {
                    onLoadAllForSearch();
                  }
                }}
                placeholder="Search ⌘F"
                className="bg-transparent border-none outline-none text-xs w-24 text-foreground placeholder:text-muted-foreground"
              />
              {searchQuery && matchCount > 0 && (
                <>
                  <span className="text-[10px] text-muted-foreground whitespace-nowrap">
                    {isLoadingAllForSearch ? '...' : `${currentMatchIndex + 1}/${matchCount}`}
                  </span>
                  <div className="flex items-center">
                    <button
                      onClick={goToPrevMatch}
                      className="p-0.5 text-muted-foreground hover:text-foreground hover:bg-accent/50 rounded"
                      title="Previous (Shift+Enter)"
                    >
                      <i className="ri-arrow-up-s-line text-sm" />
                    </button>
                    <button
                      onClick={goToNextMatch}
                      className="p-0.5 text-muted-foreground hover:text-foreground hover:bg-accent/50 rounded"
                      title="Next (Enter)"
                    >
                      <i className="ri-arrow-down-s-line text-sm" />
                    </button>
                  </div>
                </>
              )}
              {searchQuery && matchCount === 0 && !isLoadingAllForSearch && (
                <span className="text-[10px] text-muted-foreground whitespace-nowrap">No matches</span>
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
              className="p-1.5 text-muted-foreground hover:text-foreground hover:bg-accent rounded transition-colors"
              title="Search (⌘F)"
            >
              <i className="ri-search-line text-sm" />
            </button>
          )}
          <button
            onClick={() => setShowAllThinking(!showAllThinking)}
            className={`p-1.5 rounded transition-colors ${
              showAllThinking
                ? 'text-purple-500 bg-purple-500/10'
                : 'text-muted-foreground hover:text-foreground hover:bg-accent'
            }`}
            title={showAllThinking ? 'Hide all thinking' : 'Show all thinking'}
          >
            <i className="ri-brain-line text-sm" />
          </button>
          <span className="text-muted-foreground/30">|</span>
          <a
            href={getExportUrl(session.id, 'jsonl')}
            download
            className="px-2 py-1 text-[10px] font-medium text-muted-foreground hover:text-foreground hover:bg-accent rounded transition-colors"
            title="Export JSONL"
          >
            JSONL
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
        {/* Refresh loading overlay - centered */}
        {isRefreshing && (
          <div className="absolute inset-0 bg-background/80 backdrop-blur-sm flex items-center justify-center z-10">
            <div className="flex items-center gap-3 text-muted-foreground">
              <i className="ri-loader-4-line animate-spin text-xl"></i>
              <span className="text-sm">Refreshing...</span>
            </div>
          </div>
        )}
        {/* Scrollbar match indicators */}
        {searchQuery && matchingEventList.length > 0 && (
          <div className="absolute right-1 top-0 bottom-0 w-1.5 pointer-events-none z-20">
            {matchingEventList.map((eventId, idx) => {
              // Calculate position as percentage of total events
              const eventIndex = events.findIndex(e => e.id === eventId);
              if (eventIndex === -1) return null;
              const position = (eventIndex / Math.max(events.length - 1, 1)) * 100;
              const isCurrentMatch = idx === currentMatchIndex;
              return (
                <div
                  key={eventId}
                  className={`absolute w-full h-1 rounded-sm ${isCurrentMatch ? 'bg-yellow-500' : 'bg-yellow-400/60'}`}
                  style={{ top: `${position}%` }}
                  title={`Match ${idx + 1}/${matchingEventList.length}`}
                />
              );
            })}
          </div>
        )}
        <div ref={scrollRef} className="h-full overflow-y-auto px-3 sm:px-6 py-4 sm:py-6">
          <div className="max-w-4xl mx-auto space-y-3 sm:space-y-4">
            {/* Infinite scroll trigger at top - hide when searching */}
            {events.length > 0 && hasMoreEvents && !searchQuery && (
              <div ref={loadMoreTriggerRef} className="flex justify-center py-3">
                {isLoadingMore ? (
                  <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <i className="ri-loader-4-line animate-spin" />
                    Loading older messages...
                  </div>
                ) : (
                  <button
                    onClick={onLoadMore}
                    className="text-xs text-muted-foreground hover:text-primary transition-colors"
                  >
                    Load older messages
                  </button>
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
                    <MessageBubble event={item.event} searchQuery={searchQuery} showAllThinking={showAllThinking} />
                  </div>
                );
              })
            )}
          </div>
        </div>

      </div>

      {/* Scroll to bottom / New messages button
          - For active sessions with new messages: show "New messages"
          - Otherwise when scrolled up: show just arrow
          NOTE: z-50 is critical! The footer has backdrop-blur-sm which creates a
          stacking context. Don't lower the z-index! */}
      {!isAtBottom && (
        <div className="absolute bottom-10 left-0 right-0 pointer-events-none z-50">
          {/* Gradient fade */}
          <div className="h-16 bg-gradient-to-t from-background via-background/80 to-transparent" />
          {/* Button */}
          <div className="flex justify-center pb-3 bg-background">
            {isActive && hasNewMessages ? (
              <button
                onClick={scrollToBottom}
                className="pointer-events-auto flex items-center gap-2 px-4 py-2 bg-muted hover:bg-accent border border-border rounded-full shadow-sm transition-colors"
              >
                <span className="text-sm font-medium text-foreground">New messages</span>
                <i className="ri-arrow-down-line text-foreground" />
              </button>
            ) : (
              <button
                onClick={scrollToBottom}
                className="pointer-events-auto p-2 bg-muted hover:bg-accent border border-border rounded-full shadow-sm transition-colors"
                title="Scroll to bottom"
              >
                <i className="ri-arrow-down-line text-foreground" />
              </button>
            )}
          </div>
        </div>
      )}

      {/* Footer */}
      <div className="px-3 sm:px-6 py-2 sm:py-3 border-t border-border bg-background/95 backdrop-blur-sm">
        <div className="flex items-center justify-between text-[11px] text-muted-foreground">
          <div className="flex items-center gap-3">
            <button
              onClick={copySessionPath}
              className={`font-mono flex items-center gap-1 cursor-pointer transition-colors ${copied ? 'text-[color:var(--success)]' : 'hover:text-primary'}`}
              title={getSessionFilePath()}
            >
              <i className={copied ? 'ri-check-line' : 'ri-fingerprint-line'}></i>
              {copied ? 'Copied!' : session.id.slice(0, 8)}
            </button>
            <span className="text-muted-foreground/50">·</span>
            <span className="flex items-center gap-1">
              <i className="ri-calendar-line text-[10px]" />
              {formatDate(session.started_at)}
            </span>
            <span className="flex items-center gap-1">
              <i className="ri-time-line text-[10px]" />
              {formatTime(session.started_at)}
            </span>
          </div>
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
