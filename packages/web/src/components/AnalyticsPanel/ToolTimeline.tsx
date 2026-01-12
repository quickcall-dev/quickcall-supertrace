/**
 * Tool Timeline Chart - shows when tools were used during the session.
 *
 * Horizontal timeline with colored dots/bars for each tool usage.
 */

import type { Event } from '../../api/client';

interface ToolTimelineProps {
  events: Event[];
  sessionStart: string | null;
}

// Tool colors matching ToolGroup
const TOOL_COLORS: Record<string, string> = {
  Read: 'bg-[color:var(--info)]',
  Write: 'bg-[color:var(--success)]',
  Edit: 'bg-[color:var(--warning)]',
  Bash: 'bg-[color:var(--cost)]',
  Glob: 'bg-[color:var(--info)]',
  Grep: 'bg-[color:var(--info)]',
  Task: 'bg-[color:var(--warning)]',
  WebFetch: 'bg-[color:var(--info)]',
  WebSearch: 'bg-[color:var(--info)]',
  TodoWrite: 'bg-[color:var(--success)]',
  AskUserQuestion: 'bg-[color:var(--cost)]',
  default: 'bg-muted-foreground',
};

function getToolColor(toolName: string): string {
  return TOOL_COLORS[toolName] || TOOL_COLORS.default;
}

export function ToolTimeline({ events, sessionStart }: ToolTimelineProps) {
  const toolEvents = events.filter(e => e.event_type === 'tool_use');

  if (toolEvents.length === 0) {
    return (
      <div className="text-center py-4 text-muted-foreground text-sm">
        No tool usage data
      </div>
    );
  }

  // Calculate time range
  const startTime = sessionStart ? new Date(sessionStart).getTime() : new Date(toolEvents[0].timestamp).getTime();
  const endTime = new Date(toolEvents[toolEvents.length - 1].timestamp).getTime();
  const duration = Math.max(endTime - startTime, 1000); // At least 1 second

  // Group tools by name for legend
  const toolCounts: Record<string, number> = {};
  toolEvents.forEach(e => {
    const name = e.data?.tool_name as string || 'unknown';
    toolCounts[name] = (toolCounts[name] || 0) + 1;
  });

  // Sort by count descending
  const sortedTools = Object.entries(toolCounts).sort((a, b) => b[1] - a[1]);

  return (
    <div className="space-y-3">
      {/* Timeline */}
      <div className="relative h-12 bg-muted/30 rounded-lg overflow-hidden">
        {/* Time axis markers */}
        <div className="absolute inset-x-0 bottom-0 h-4 flex justify-between px-2 text-[9px] text-muted-foreground">
          <span>0s</span>
          <span>{Math.round(duration / 1000)}s</span>
        </div>

        {/* Tool markers */}
        <div className="absolute inset-x-0 top-1 bottom-5 px-1">
          {toolEvents.map((event, idx) => {
            const eventTime = new Date(event.timestamp).getTime();
            const position = ((eventTime - startTime) / duration) * 100;
            const toolName = event.data?.tool_name as string || 'unknown';
            const color = getToolColor(toolName);

            return (
              <div
                key={event.id || idx}
                className={`absolute w-1.5 h-full ${color} rounded-full opacity-80 hover:opacity-100 transition-opacity cursor-pointer`}
                style={{ left: `${Math.min(Math.max(position, 0), 98)}%` }}
                title={`${toolName} at ${new Date(event.timestamp).toLocaleTimeString()}`}
              />
            );
          })}
        </div>
      </div>

      {/* Legend */}
      <div className="flex flex-wrap gap-2">
        {sortedTools.slice(0, 6).map(([name, count]) => (
          <div key={name} className="flex items-center gap-1.5 text-xs">
            <div className={`w-2 h-2 rounded-full ${getToolColor(name)}`} />
            <span className="text-muted-foreground">{name}</span>
            <span className="text-foreground font-medium">{count}</span>
          </div>
        ))}
        {sortedTools.length > 6 && (
          <span className="text-xs text-muted-foreground">+{sortedTools.length - 6} more</span>
        )}
      </div>
    </div>
  );
}
