/**
 * Session detail view component.
 *
 * Displays conversation with clean header, messages, tools, and stats.
 * Professional enterprise-ready design. Uses Remix Icons.
 */

import { useEffect, useRef } from 'react';
import type { Session, Event } from '../api/client';
import { getExportUrl } from '../api/client';
import { MessageBubble } from './MessageBubble';
import { ToolGroup } from './ToolGroup';

interface SessionViewProps {
  session: Session | null;
  events: Event[];
  isLoading: boolean;
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

export function SessionView({ session, events, isLoading }: SessionViewProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

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

  // Calculate session stats
  const userPrompts = events.filter(e => e.event_type === 'user_prompt').length;
  const toolCalls = events.filter(e => e.event_type === 'tool_use').length;

  return (
    <div className="flex-1 flex flex-col h-full bg-background">
      {/* Header */}
      <div className="px-6 py-4 border-b border-border bg-background/95 backdrop-blur-sm">
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-3">
              <h2 className="text-lg font-semibold text-foreground">
                {getProjectName(session.project_path)}
              </h2>
              {isActive && (
                <span className="flex items-center gap-1.5 text-[11px] bg-[color:var(--success)]/20 text-[color:var(--success)] px-2 py-0.5 rounded-full border border-[color:var(--success)]/30">
                  <span className="w-1.5 h-1.5 bg-[color:var(--success)] rounded-full animate-pulse" />
                  Live
                </span>
              )}
            </div>
            <div className="flex items-center gap-3 mt-1.5 text-sm text-muted-foreground">
              <span className="flex items-center gap-1">
                <i className="ri-calendar-line text-xs"></i>
                {formatDate(session.started_at)}
              </span>
              <span className="text-muted-foreground/50">·</span>
              <span className="flex items-center gap-1">
                <i className="ri-time-line text-xs"></i>
                {formatTime(session.started_at)}
              </span>
              {session.ended_at && (
                <>
                  <i className="ri-arrow-right-line text-muted-foreground/50 text-xs"></i>
                  <span>{formatTime(session.ended_at)}</span>
                </>
              )}
            </div>
          </div>

          {/* Export buttons */}
          <div className="flex items-center gap-2">
            <a
              href={getExportUrl(session.id, 'json')}
              download
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-muted-foreground bg-muted hover:bg-accent border border-border rounded-lg transition-colors"
            >
              <i className="ri-download-2-line"></i>
              JSON
            </a>
            <a
              href={getExportUrl(session.id, 'md')}
              download
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-muted-foreground bg-muted hover:bg-accent border border-border rounded-lg transition-colors"
            >
              <i className="ri-markdown-line"></i>
              Markdown
            </a>
          </div>
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
                return <ToolGroup key={`group-${idx}`} events={item.events} />;
              }
              return <MessageBubble key={item.event.id} event={item.event} />;
            })
          )}
        </div>
      </div>

      {/* Footer */}
      <div className="px-6 py-3 border-t border-border bg-background/95 backdrop-blur-sm">
        <div className="flex items-center justify-between text-[11px] text-muted-foreground">
          <div className="flex items-center gap-4">
            <span className="font-mono flex items-center gap-1">
              <i className="ri-fingerprint-line"></i>
              {session.id.slice(0, 12)}
            </span>
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
