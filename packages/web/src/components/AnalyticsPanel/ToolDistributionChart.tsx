/**
 * Tool Distribution Chart
 *
 * Single stacked horizontal bar showing tool usage with legend below.
 */

import type { PromptTurnsData } from '../../api/client';

interface ToolDistributionChartProps {
  data: PromptTurnsData | null;
}

export function ToolDistributionChart({ data }: ToolDistributionChartProps) {
  if (!data || data.toolLegend.length === 0) {
    return (
      <div className="text-center py-3 text-muted-foreground text-sm">
        No tool usage data
      </div>
    );
  }

  const totalTools = data.totals.tools;
  const tools = data.toolLegend;

  // Calculate "Other" category if there are more tools than in legend
  const legendTotal = tools.reduce((sum, t) => sum + t.count, 0);
  const otherCount = totalTools - legendTotal;

  return (
    <div className="space-y-2">
      {/* Single stacked bar */}
      <div className="h-3 bg-muted rounded-full overflow-hidden flex">
        {tools.map((tool) => {
          const percentage = totalTools > 0 ? (tool.count / totalTools) * 100 : 0;
          return (
            <div
              key={tool.name}
              className="h-full transition-all duration-300 first:rounded-l-full last:rounded-r-full"
              style={{
                width: `${percentage}%`,
                backgroundColor: tool.color,
              }}
              title={`${tool.name}: ${tool.count} (${percentage.toFixed(1)}%)`}
            />
          );
        })}
        {otherCount > 0 && (
          <div
            className="h-full bg-muted-foreground/40 last:rounded-r-full"
            style={{ width: `${(otherCount / totalTools) * 100}%` }}
            title={`Other: ${otherCount} (${((otherCount / totalTools) * 100).toFixed(1)}%)`}
          />
        )}
      </div>

      {/* Legend */}
      <div className="flex flex-wrap gap-x-3 gap-y-1 text-[11px]">
        {tools.map((tool) => {
          const percentage = totalTools > 0 ? (tool.count / totalTools) * 100 : 0;
          return (
            <span key={tool.name} className="flex items-center gap-1">
              <span
                className="w-2 h-2 rounded-sm"
                style={{ backgroundColor: tool.color }}
              />
              <span className="text-foreground">{tool.name}</span>
              <span className="text-muted-foreground">{tool.count}</span>
              <span className="text-muted-foreground/60">({percentage.toFixed(0)}%)</span>
            </span>
          );
        })}
        {otherCount > 0 && (
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-sm bg-muted-foreground/40" />
            <span className="text-foreground">Other</span>
            <span className="text-muted-foreground">{otherCount}</span>
            <span className="text-muted-foreground/60">({((otherCount / totalTools) * 100).toFixed(0)}%)</span>
          </span>
        )}
      </div>
    </div>
  );
}
