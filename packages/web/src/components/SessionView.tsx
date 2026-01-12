/**
 * Session detail view component.
 *
 * Displays conversation with clean header, messages, tools, and stats.
 * Professional enterprise-ready design.
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
      <div className="flex-1 flex items-center justify-center bg-gray-950">
        <div className="text-center">
          <div className="w-16 h-16 mx-auto mb-4 bg-gray-900 rounded-2xl flex items-center justify-center">
            <svg className="w-8 h-8 text-gray-700" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
            </svg>
          </div>
          <p className="text-gray-500 text-sm">Select a session to view</p>
        </div>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center bg-gray-950">
        <div className="flex items-center gap-3 text-gray-500">
          <svg className="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
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
    <div className="flex-1 flex flex-col h-full bg-gray-950">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-800 bg-gray-950/95 backdrop-blur-sm">
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-3">
              <h2 className="text-lg font-semibold text-gray-100">
                {getProjectName(session.project_path)}
              </h2>
              {isActive && (
                <span className="flex items-center gap-1.5 text-[11px] bg-green-500/20 text-green-400 px-2 py-0.5 rounded-full border border-green-500/30">
                  <span className="w-1.5 h-1.5 bg-green-400 rounded-full animate-pulse" />
                  Live
                </span>
              )}
            </div>
            <div className="flex items-center gap-3 mt-1.5 text-sm text-gray-500">
              <span>{formatDate(session.started_at)}</span>
              <span className="text-gray-700">·</span>
              <span>{formatTime(session.started_at)}</span>
              {session.ended_at && (
                <>
                  <span className="text-gray-700">→</span>
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
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-gray-400 bg-gray-900 hover:bg-gray-800 border border-gray-800 rounded-lg transition-colors"
            >
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
              JSON
            </a>
            <a
              href={getExportUrl(session.id, 'md')}
              download
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-gray-400 bg-gray-900 hover:bg-gray-800 border border-gray-800 rounded-lg transition-colors"
            >
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
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
              <div className="w-12 h-12 mx-auto mb-3 bg-gray-900 rounded-full flex items-center justify-center">
                <svg className="w-6 h-6 text-gray-700" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                </svg>
              </div>
              <p className="text-sm text-gray-500">No messages yet</p>
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
      <div className="px-6 py-3 border-t border-gray-800 bg-gray-950/95 backdrop-blur-sm">
        <div className="flex items-center justify-between text-[11px] text-gray-600">
          <div className="flex items-center gap-4">
            <span className="font-mono">{session.id.slice(0, 12)}...</span>
            <span className="text-gray-700">·</span>
            <span>{userPrompts} prompt{userPrompts !== 1 ? 's' : ''}</span>
            <span className="text-gray-700">·</span>
            <span>{toolCalls} tool call{toolCalls !== 1 ? 's' : ''}</span>
          </div>
          <span>{events.length} event{events.length !== 1 ? 's' : ''}</span>
        </div>
      </div>
    </div>
  );
}
