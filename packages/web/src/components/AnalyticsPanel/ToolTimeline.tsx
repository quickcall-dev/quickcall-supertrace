/**
 * Tool Usage Chart - shows tool distribution across the session.
 *
 * Clean horizontal stacked bar showing proportion of each tool type.
 * Hover for details, with summary stats below.
 */

import { useState } from 'react';
import type { Event } from '../../api/client';

interface ToolTimelineProps {
  events: Event[];
  sessionStart: string | null;
}

// Tool colors - uses muted bar colors for chart segments
const TOOL_CONFIG: Record<string, { color: string; label: string }> = {
  Read: { color: 'var(--bar-info)', label: 'Read' },
  Glob: { color: 'var(--bar-info)', label: 'Glob' },
  Grep: { color: 'var(--bar-info)', label: 'Grep' },
  Write: { color: 'var(--bar-success)', label: 'Write' },
  Edit: { color: 'var(--bar-warning)', label: 'Edit' },
  Bash: { color: 'var(--bar-cost)', label: 'Bash' },
  Task: { color: 'var(--tool-task)', label: 'Task' },
  TodoWrite: { color: 'var(--tool-todo)', label: 'Todo' },
  WebFetch: { color: 'var(--tool-web)', label: 'Web' },
  WebSearch: { color: 'var(--tool-web)', label: 'Search' },
  AskUserQuestion: { color: 'var(--tool-ask)', label: 'Ask' },
};

const DEFAULT_COLOR = 'var(--muted-foreground)';

interface ToolStat {
  name: string;
  count: number;
  color: string;
  label: string;
  percentage: number;
}

export function ToolTimeline({ events }: ToolTimelineProps) {
  const [hoveredTool, setHoveredTool] = useState<string | null>(null);

  const toolEvents = events.filter(e => e.event_type === 'tool_use');

  if (toolEvents.length === 0) {
    return (
      <div className="text-center py-4 text-muted-foreground text-sm">
        No tool usage data
      </div>
    );
  }

  // Count tools
  const toolCounts: Record<string, number> = {};
  toolEvents.forEach(e => {
    const name = e.data?.tool_name as string || 'unknown';
    toolCounts[name] = (toolCounts[name] || 0) + 1;
  });

  const total = toolEvents.length;

  // Build stats sorted by count
  const stats: ToolStat[] = Object.entries(toolCounts)
    .map(([name, count]) => ({
      name,
      count,
      color: TOOL_CONFIG[name]?.color || DEFAULT_COLOR,
      label: TOOL_CONFIG[name]?.label || name,
      percentage: (count / total) * 100,
    }))
    .sort((a, b) => b.count - a.count);

  // Group small tools into "Other"
  const mainTools = stats.filter(s => s.percentage >= 5);
  const otherTools = stats.filter(s => s.percentage < 5);
  const otherCount = otherTools.reduce((sum, t) => sum + t.count, 0);

  const displayStats = otherCount > 0
    ? [...mainTools, {
        name: 'Other',
        count: otherCount,
        color: 'var(--muted-foreground)',
        label: 'Other',
        percentage: (otherCount / total) * 100
      }]
    : mainTools;

  return (
    <div className="space-y-3">
      {/* Stacked horizontal bar */}
      <div className="relative">
        <div className="h-8 rounded-lg overflow-hidden flex bg-muted/30">
          {displayStats.map((stat) => (
            <div
              key={stat.name}
              className="h-full transition-all duration-200 cursor-pointer relative group"
              style={{
                width: `${stat.percentage}%`,
                backgroundColor: stat.color,
                opacity: hoveredTool === null || hoveredTool === stat.name ? 1 : 0.3,
              }}
              onMouseEnter={() => setHoveredTool(stat.name)}
              onMouseLeave={() => setHoveredTool(null)}
            >
              {/* Show label if segment is wide enough */}
              {stat.percentage > 12 && (
                <span className="absolute inset-0 flex items-center justify-center text-[10px] font-medium text-white/90 pointer-events-none">
                  {stat.label}
                </span>
              )}

              {/* Tooltip */}
              <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 bg-popover border border-border rounded shadow-lg text-xs whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10">
                <span className="font-medium">{stat.label}</span>
                <span className="text-muted-foreground ml-1">
                  {stat.count} ({stat.percentage.toFixed(0)}%)
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Legend with counts */}
      <div className="flex flex-wrap gap-x-4 gap-y-1.5">
        {stats.slice(0, 8).map(stat => (
          <div
            key={stat.name}
            className="flex items-center gap-1.5 text-xs cursor-pointer transition-opacity"
            style={{ opacity: hoveredTool === null || hoveredTool === stat.name ? 1 : 0.4 }}
            onMouseEnter={() => setHoveredTool(stat.name)}
            onMouseLeave={() => setHoveredTool(null)}
          >
            <div
              className="w-2.5 h-2.5 rounded-sm shrink-0"
              style={{ backgroundColor: stat.color }}
            />
            <span className="text-muted-foreground">{stat.label}</span>
            <span className="font-medium text-foreground">{stat.count}</span>
          </div>
        ))}
        {stats.length > 8 && (
          <span className="text-xs text-muted-foreground">+{stats.length - 8} more</span>
        )}
      </div>

      {/* Summary stat */}
      <div className="flex items-center justify-between text-xs pt-1 border-t border-border">
        <span className="text-muted-foreground">Total tool calls</span>
        <span className="font-mono font-medium text-foreground">{total}</span>
      </div>
    </div>
  );
}
