/**
 * Tool group component for displaying multiple tool calls.
 *
 * Clean, compact design that doesn't overflow. Shows tool count
 * and names in a constrained layout.
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

// Tool name to icon/color mapping
const TOOL_STYLES: Record<string, { icon: string; color: string }> = {
  Read: { icon: '📄', color: 'text-blue-400' },
  Write: { icon: '✏️', color: 'text-green-400' },
  Edit: { icon: '🔧', color: 'text-yellow-400' },
  Bash: { icon: '💻', color: 'text-purple-400' },
  Glob: { icon: '🔍', color: 'text-cyan-400' },
  Grep: { icon: '🔎', color: 'text-cyan-400' },
  Task: { icon: '📋', color: 'text-orange-400' },
  WebFetch: { icon: '🌐', color: 'text-blue-400' },
  WebSearch: { icon: '🔍', color: 'text-blue-400' },
  TodoWrite: { icon: '✅', color: 'text-green-400' },
  default: { icon: '⚡', color: 'text-gray-400' },
};

function getToolStyle(toolName: string) {
  return TOOL_STYLES[toolName] || TOOL_STYLES.default;
}

function ToolItem({ event, isExpanded, onToggle }: ToolItemProps) {
  const toolName = event.data?.tool_name as string || 'unknown';
  const toolInput = event.data?.tool_input as Record<string, unknown>;
  const toolResult = event.data?.tool_result;
  const style = getToolStyle(toolName);

  const formatData = (data: unknown): string => {
    if (data === null || data === undefined) return '';
    return typeof data === 'string' ? data : JSON.stringify(data, null, 2);
  };

  const formatTime = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };

  // Get a preview of the tool input for collapsed view
  const getInputPreview = (): string => {
    if (!toolInput) return '';

    // Special handling for common tools
    if (toolName === 'Read' && toolInput.file_path) {
      return String(toolInput.file_path).split('/').slice(-2).join('/');
    }
    if (toolName === 'Edit' && toolInput.file_path) {
      return String(toolInput.file_path).split('/').slice(-2).join('/');
    }
    if (toolName === 'Write' && toolInput.file_path) {
      return String(toolInput.file_path).split('/').slice(-2).join('/');
    }
    if (toolName === 'Bash' && toolInput.command) {
      const cmd = String(toolInput.command);
      return cmd.length > 40 ? cmd.slice(0, 40) + '...' : cmd;
    }
    if (toolName === 'Glob' && toolInput.pattern) {
      return String(toolInput.pattern);
    }
    if (toolName === 'Grep' && toolInput.pattern) {
      return String(toolInput.pattern);
    }

    return '';
  };

  const preview = getInputPreview();

  return (
    <div className="border-b border-gray-800 last:border-b-0">
      <button
        onClick={onToggle}
        className="w-full flex items-center gap-3 px-3 py-2.5 hover:bg-gray-800/50 transition-colors text-left group"
      >
        <span className="text-sm">{style.icon}</span>
        <div className="flex-1 min-w-0 flex items-center gap-2">
          <span className={`font-mono text-sm ${style.color}`}>{toolName}</span>
          {preview && !isExpanded && (
            <span className="text-xs text-gray-500 truncate">{preview}</span>
          )}
        </div>
        <span className="text-[11px] text-gray-600 opacity-0 group-hover:opacity-100 transition-opacity">
          {formatTime(event.timestamp)}
        </span>
        <svg
          className={`w-4 h-4 text-gray-500 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {isExpanded && (
        <div className="px-3 pb-3 space-y-3">
          {toolInput && Object.keys(toolInput).length > 0 && (
            <div>
              <div className="text-[11px] text-gray-500 mb-1.5 uppercase tracking-wide">Input</div>
              <pre className="text-xs bg-gray-900/80 p-3 rounded-lg overflow-x-auto overflow-y-auto max-h-[300px] text-gray-300 border border-gray-800">
                {formatData(toolInput)}
              </pre>
            </div>
          )}
          {toolResult !== null && toolResult !== undefined && (
            <div>
              <div className="text-[11px] text-gray-500 mb-1.5 uppercase tracking-wide">Result</div>
              <pre className="text-xs bg-gray-900/80 p-3 rounded-lg overflow-x-auto overflow-y-auto max-h-[400px] text-gray-300 border border-gray-800">
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
  const [expandedTools, setExpandedTools] = useState<Set<number>>(new Set());

  const toggleGroup = () => setIsGroupExpanded(!isGroupExpanded);

  const toggleTool = (eventId: number) => {
    const newExpanded = new Set(expandedTools);
    if (newExpanded.has(eventId)) {
      newExpanded.delete(eventId);
    } else {
      newExpanded.add(eventId);
    }
    setExpandedTools(newExpanded);
  };

  // Get unique tool names for summary
  const toolNames = events.map((ev) => ev.data?.tool_name as string || 'unknown');
  const toolCounts: Record<string, number> = {};
  toolNames.forEach(name => {
    toolCounts[name] = (toolCounts[name] || 0) + 1;
  });

  // Format as compact badges
  const badges = Object.entries(toolCounts).slice(0, 4);
  const remaining = Object.keys(toolCounts).length - 4;

  return (
    <div className="bg-gray-900/50 border border-gray-800 rounded-xl overflow-hidden">
      {/* Group header */}
      <button
        onClick={toggleGroup}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-gray-800/30 transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5">
            <svg
              className={`w-4 h-4 text-gray-500 transition-transform ${isGroupExpanded ? 'rotate-180' : ''}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
            <span className="text-sm font-medium text-gray-300">
              Tools
            </span>
            <span className="text-xs text-gray-500 bg-gray-800 px-1.5 py-0.5 rounded">
              {events.length}
            </span>
          </div>

          {/* Tool badges - only show when collapsed */}
          {!isGroupExpanded && (
            <div className="flex items-center gap-1.5 ml-2">
              {badges.map(([name, count]) => {
                const style = getToolStyle(name);
                return (
                  <span
                    key={name}
                    className={`text-xs ${style.color} bg-gray-800/80 px-2 py-0.5 rounded-full font-mono`}
                  >
                    {name}{count > 1 && <span className="text-gray-500 ml-1">×{count}</span>}
                  </span>
                );
              })}
              {remaining > 0 && (
                <span className="text-xs text-gray-500">+{remaining}</span>
              )}
            </div>
          )}
        </div>
      </button>

      {/* Tool list */}
      {isGroupExpanded && (
        <div className="border-t border-gray-800 max-h-[600px] overflow-y-auto">
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
