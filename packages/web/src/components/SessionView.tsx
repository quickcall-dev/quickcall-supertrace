/**
 * Session detail view component.
 *
 * Displays conversation with clean header, messages, tools, and stats.
 * Professional enterprise-ready design. Uses Remix Icons.
 */

import { useEffect, useRef, useCallback, useState, type MutableRefObject } from 'react';
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
  isLoadingMore?: boolean;
  onLoadMore?: () => void;
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
  isLoadingMore = false,
  onLoadMore,
}: SessionViewProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const loadMoreTriggerRef = useRef<HTMLDivElement>(null);
  const eventRefs = useRef<Map<number, HTMLDivElement>>(new Map());
  const [copied, setCopied] = useState(false);

  // Infinite scroll - load more when scrolling to top
  useEffect(() => {
    const trigger = loadMoreTriggerRef.current;
    if (!trigger || !onLoadMore) return;

    const observer = new IntersectionObserver(
      (entries) => {
        const entry = entries[0];
        if (entry.isIntersecting && !isLoadingMore && events.length < totalEvents) {
          onLoadMore();
        }
      },
      { threshold: 0.1 }
    );

    observer.observe(trigger);
    return () => observer.disconnect();
  }, [onLoadMore, isLoadingMore, events.length, totalEvents]);

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

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
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
  const groupedEvents = groupEvents(events);

  // Get session file path for clipboard (absolute path)
  // Claude stores sessions at the git root, not the cwd. We need to find
  // the git root from project_path. Convention: .claude folder is at git root.
  const getSessionFilePath = () => {
    if (!session.project_path) return session.id;

    // Find git root - look for common project indicators
    // e.g., /Users/sagar/work/project/packages/server -> /Users/sagar/work/project
    const parts = session.project_path.split('/');
    const homeDir = parts.slice(0, 3).join('/'); // /Users/username

    // Find the likely git root by looking for common subdirectories
    // that indicate we're in a subdirectory of a monorepo
    let gitRootParts = [...parts];
    const subDirIndicators = ['packages', 'apps', 'libs', 'src', 'services'];
    for (let i = parts.length - 1; i >= 3; i--) {
      if (subDirIndicators.includes(parts[i])) {
        gitRootParts = parts.slice(0, i);
        break;
      }
    }

    const gitRoot = gitRootParts.join('/');
    const escapedPath = gitRoot.replace(/^\//, '').replace(/\//g, '-');
    return `${homeDir}/.claude/projects/-${escapedPath}/${session.id}.jsonl`;
  };

  const copySessionPath = () => {
    navigator.clipboard.writeText(getSessionFilePath());
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };


  return (
    <div className="flex-1 flex flex-col h-full bg-background">
      {/* Header - compact single row */}
      <div className="h-12 px-4 border-b border-border bg-background/95 backdrop-blur-sm flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3 text-sm">
          <span className="font-semibold text-foreground">{getProjectName(session.project_path)}</span>
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
        <div className="flex items-center gap-1.5">
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
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-6 py-6">
        <div className="max-w-4xl mx-auto space-y-4">
          {/* Infinite scroll trigger at top */}
          {events.length > 0 && events.length < totalEvents && (
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
          {groupedEvents.length === 0 ? (
            <div className="text-center py-12">
              <div className="w-12 h-12 mx-auto mb-3 bg-muted rounded-full flex items-center justify-center">
                <i className="ri-chat-3-line text-muted-foreground text-xl"></i>
              </div>
              <p className="text-sm text-muted-foreground">No messages yet</p>
            </div>
          ) : (
            groupedEvents.map((item, idx) => {
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

      {/* Footer */}
      <div className="px-6 py-3 border-t border-border bg-background/95 backdrop-blur-sm">
        <div className="flex items-center justify-between text-[11px] text-muted-foreground">
          <button
            onClick={copySessionPath}
            className={`font-mono flex items-center gap-1 cursor-pointer transition-colors ${copied ? 'text-[color:var(--success)]' : 'hover:text-primary'}`}
            title={getSessionFilePath()}
          >
            <i className={copied ? 'ri-check-line' : 'ri-fingerprint-line'}></i>
            {copied ? 'Copied!' : session.id.slice(0, 12)}
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
