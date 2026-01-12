/**
 * Tool group component for displaying multiple tool calls in a single widget.
 *
 * Groups consecutive tool_use events and displays them in a collapsible panel.
 * Each tool can be expanded individually to view full input/output without truncation.
 *
 * Related: SessionView.tsx (parent), MessageBubble.tsx (sibling)
 */

import { useState } from 'react';
import type { Event } from '../api/client';

interface ToolGroupProps {
  events: Event[];
}

interface ToolItemProps {
  event: Event;
  isExpanded: boolean;
  onToggle: () => void;
}

function ToolItem({ event, isExpanded, onToggle }: ToolItemProps) {
  const toolName = event.data?.tool_name as string;
  const toolInput = event.data?.tool_input as Record<string, unknown>;
  const toolResult = event.data?.tool_result;

  const formatData = (data: unknown): string => {
    if (data === null || data === undefined) return '';
    return typeof data === 'string' ? data : JSON.stringify(data, null, 2);
  };

  const formatTime = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString();
  };

  return (
    <div className="border-b border-gray-700 last:border-b-0">
      <button
        onClick={onToggle}
        className="w-full flex items-center justify-between px-3 py-2 hover:bg-gray-750 transition-colors text-left"
      >
        <div className="flex items-center gap-2">
          <span className="text-gray-400">{isExpanded ? '▼' : '▶'}</span>
          <span className="font-mono text-yellow-400 text-sm">{toolName || 'unknown'}</span>
        </div>
        <span className="text-xs text-gray-500">{formatTime(event.timestamp)}</span>
      </button>

      {isExpanded && (
        <div className="px-3 pb-3 space-y-3">
          {toolInput && Object.keys(toolInput).length > 0 && (
            <div>
              <div className="text-xs text-gray-400 mb-1 font-semibold">Input:</div>
              <pre className="text-xs bg-gray-900 p-2 rounded overflow-x-auto overflow-y-auto max-h-[400px] whitespace-pre-wrap break-words border border-gray-700">
                {formatData(toolInput)}
              </pre>
            </div>
          )}
          {toolResult !== null && toolResult !== undefined && (
            <div>
              <div className="text-xs text-gray-400 mb-1 font-semibold">Result:</div>
              <pre className="text-xs bg-gray-900 p-2 rounded overflow-x-auto overflow-y-auto max-h-[600px] whitespace-pre-wrap break-words border border-gray-700">
                {formatData(toolResult)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function ToolGroup({ events }: ToolGroupProps) {
  const [isGroupExpanded, setIsGroupExpanded] = useState(false);
  const [expandedTools, setExpandedTools] = useState<Set<string>>(new Set());

  const toggleGroup = () => setIsGroupExpanded(!isGroupExpanded);

  const toggleTool = (eventId: string) => {
    const newExpanded = new Set(expandedTools);
    if (newExpanded.has(eventId)) {
      newExpanded.delete(eventId);
    } else {
      newExpanded.add(eventId);
    }
    setExpandedTools(newExpanded);
  };

  const expandAll = (e: React.MouseEvent) => {
    e.stopPropagation();
    setExpandedTools(new Set(events.map((ev) => ev.id)));
  };

  const collapseAll = (e: React.MouseEvent) => {
    e.stopPropagation();
    setExpandedTools(new Set());
  };

  // Get tool names for summary
  const toolNames = events.map((ev) => ev.data?.tool_name as string || 'unknown');
  const uniqueTools = [...new Set(toolNames)];
  const summary =
    uniqueTools.length <= 3
      ? uniqueTools.join(', ')
      : `${uniqueTools.slice(0, 3).join(', ')} +${uniqueTools.length - 3} more`;

  return (
    <div className="w-full bg-gray-800 border border-gray-600 rounded-lg overflow-hidden">
      {/* Group header */}
      <button
        onClick={toggleGroup}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-gray-750 transition-colors"
      >
        <div className="flex items-center gap-3">
          <span className="text-gray-400">{isGroupExpanded ? '▼' : '▶'}</span>
          <span className="text-sm font-semibold text-yellow-400">
            Tools ({events.length})
          </span>
          <span className="text-xs text-gray-500 font-mono">{summary}</span>
        </div>
        {isGroupExpanded && (
          <div className="flex gap-2">
            <button
              onClick={expandAll}
              className="text-xs text-blue-400 hover:text-blue-300 px-2 py-1 rounded hover:bg-gray-700"
            >
              Expand All
            </button>
            <button
              onClick={collapseAll}
              className="text-xs text-blue-400 hover:text-blue-300 px-2 py-1 rounded hover:bg-gray-700"
            >
              Collapse All
            </button>
          </div>
        )}
      </button>

      {/* Tool list */}
      {isGroupExpanded && (
        <div className="border-t border-gray-700 max-h-[800px] overflow-y-auto">
          {events.map((event) => (
            <ToolItem
              key={event.id}
              event={event}
              isExpanded={expandedTools.has(event.id)}
              onToggle={() => toggleTool(event.id)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
