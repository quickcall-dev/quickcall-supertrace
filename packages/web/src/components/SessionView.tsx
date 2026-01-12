/**
 * Session detail view component.
 *
 * Displays conversation with clean header, messages, tools, and stats.
 * Professional enterprise-ready design. Uses Remix Icons.
 */

import { useEffect, useRef, useCallback, useState, type MutableRefObject } from 'react';
import type { Session, Event } from '../api/client';
import { getExportUrl } from '../api/client';
import { MessageBubble } from './MessageBubble';
import { ToolGroup } from './ToolGroup';

interface SessionViewProps {
  session: Session | null;
  events: Event[];
  isLoading: boolean;
  onScrollToEventRef?: MutableRefObject<((eventId: number) => void) | null>;
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

export function SessionView({ session, events, isLoading, onScrollToEventRef }: SessionViewProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const eventRefs = useRef<Map<number, HTMLDivElement>>(new Map());

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

  if (!session) {
    return (
      <div className="flex-1 flex items-center justify-center bg-background">
        <div className="text-center">
          <div className="w-16 h-16 mx-auto mb-4 bg-muted rounded-2xl flex items-center justify-center">
            <i className="ri-chat-3-line text-muted-foreground text-2xl"></i>
          </div>
          <p className="text-muted-foreground text-sm">Select a session to view</p>
        </div>
      </div>
    );
  }

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

  const getProjectName = (path: string | null) => {
    if (!path) return 'Unknown Project';
    const parts = path.split('/');
    return parts[parts.length - 1] || path;
  };

  const formatDate = (timestamp: string | null) => {
    if (!timestamp) return '';
    const date = new Date(timestamp);
    return date.toLocaleDateString(undefined, {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  const formatTime = (timestamp: string | null) => {
    if (!timestamp) return '';
    return new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const isActive = session.started_at && !session.ended_at;
  const groupedEvents = groupEvents(events);

  // Get session file path for clipboard (absolute path)
  const getSessionFilePath = () => {
    if (!session.project_path) return session.id;
    const escapedPath = session.project_path.replace(/^\//, '').replace(/\//g, '-');
    // Use absolute path with typical home directory
    const homeDir = '/Users/' + (session.project_path.split('/')[2] || 'user');
    return `${homeDir}/.claude/projects/-${escapedPath}/${session.id}.jsonl`;
  };

  const [copied, setCopied] = useState(false);

  const copySessionPath = () => {
    navigator.clipboard.writeText(getSessionFilePath());
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Calculate session stats
  const userPrompts = events.filter(e => e.event_type === 'user_prompt').length;
  const toolCalls = events.filter(e => e.event_type === 'tool_use').length;

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
          <div className="flex items-center gap-4">
            <button
              onClick={copySessionPath}
              className={`font-mono flex items-center gap-1 cursor-pointer transition-colors ${copied ? 'text-[color:var(--success)]' : 'hover:text-primary'}`}
              title={getSessionFilePath()}
            >
              <i className={copied ? 'ri-check-line' : 'ri-fingerprint-line'}></i>
              {copied ? 'Copied!' : session.id.slice(0, 12)}
            </button>
            <span className="text-muted-foreground/50">·</span>
            <span className="flex items-center gap-1">
              <i className="ri-chat-1-line"></i>
              {userPrompts}
            </span>
            <span className="text-muted-foreground/50">·</span>
            <span className="flex items-center gap-1">
              <i className="ri-tools-line"></i>
              {toolCalls}
            </span>
          </div>
          <span className="flex items-center gap-1">
            <i className="ri-list-check"></i>
            {events.length} events
          </span>
        </div>
      </div>
    </div>
  );
}
