/**
 * Session detail view component.
 *
 * Displays conversation thread with messages, tool calls,
 * token/cost info, and export buttons.
 *
 * Tool calls are grouped together per turn for better readability.
 *
 * Related: MessageBubble.tsx (child), ToolGroup.tsx (child), api/client.ts (types)
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

// Group consecutive tool_use events together
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
      // Flush any pending tool group
      if (currentToolGroup.length > 0) {
        result.push({ type: 'tool_group', events: currentToolGroup });
        currentToolGroup = [];
      }
      result.push({ type: 'single', event });
    }
  }

  // Flush remaining tool group
  if (currentToolGroup.length > 0) {
    result.push({ type: 'tool_group', events: currentToolGroup });
  }

  return result;
}

export function SessionView({ session, events, isLoading }: SessionViewProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new events
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [events]);

  if (!session) {
    return (
      <div className="flex-1 flex items-center justify-center text-gray-500">
        Select a session to view
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center text-gray-500">
        Loading...
      </div>
    );
  }

  const getProjectName = (path: string | null) => {
    if (!path) return 'Unknown Project';
    const parts = path.split('/');
    return parts[parts.length - 1] || path;
  };

  const formatDate = (timestamp: string | null) => {
    if (!timestamp) return 'N/A';
    return new Date(timestamp).toLocaleString();
  };

  const isActive = session.started_at && !session.ended_at;
  const groupedEvents = groupEvents(events);

  return (
    <div className="flex-1 flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b border-gray-700 flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-lg font-semibold">
              {getProjectName(session.project_path)}
            </h2>
            {isActive && (
              <span className="text-xs bg-green-600 text-white px-2 py-0.5 rounded">
                LIVE
              </span>
            )}
          </div>
          <div className="text-sm text-gray-400 mt-1">
            {formatDate(session.started_at)}
            {session.ended_at && ` — ${formatDate(session.ended_at)}`}
          </div>
        </div>

        {/* Export buttons */}
        <div className="flex gap-2">
          <a
            href={getExportUrl(session.id, 'json')}
            download
            className="px-3 py-1 text-sm bg-gray-700 hover:bg-gray-600 rounded transition-colors"
          >
            Export JSON
          </a>
          <a
            href={getExportUrl(session.id, 'md')}
            download
            className="px-3 py-1 text-sm bg-gray-700 hover:bg-gray-600 rounded transition-colors"
          >
            Export MD
          </a>
        </div>
      </div>

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-4">
        {groupedEvents.length === 0 ? (
          <div className="text-center text-gray-500">No events yet</div>
        ) : (
          groupedEvents.map((item, idx) => {
            if (item.type === 'tool_group') {
              return <ToolGroup key={`group-${idx}`} events={item.events} />;
            }
            return <MessageBubble key={item.event.id} event={item.event} />;
          })
        )}
      </div>

      {/* Footer with stats */}
      <div className="p-3 border-t border-gray-700 text-xs text-gray-500 flex justify-between">
        <span>Session: {session.id.slice(0, 16)}...</span>
        <span>{events.length} events</span>
      </div>
    </div>
  );
}
