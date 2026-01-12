/**
 * Expanded analytics view with compact header and charts.
 */

import type { MetricsResponse, MetricFormat, PromptTurnsData } from '../../api/client';
import { PromptMetricsChart } from './PromptMetricsChart';

interface ExpandedViewProps {
  metrics: MetricsResponse;
  onCollapse: () => void;
  onScrollToEvent?: (eventId: number) => void;
}

function formatValue(value: unknown, format: MetricFormat): string {
  if (value === null || value === undefined) return '-';

  switch (format) {
    case 'currency':
      return `$${(value as number).toFixed(2)}`;

    case 'duration': {
      const seconds = value as number;
      if (seconds < 60) return `${seconds}s`;
      if (seconds < 3600) {
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return secs > 0 ? `${mins}m ${secs}s` : `${mins}m`;
      }
      const hours = Math.floor(seconds / 3600);
      const mins = Math.floor((seconds % 3600) / 60);
      return mins > 0 ? `${hours}h ${mins}m` : `${hours}h`;
    }

    case 'percentage':
      return `${value}%`;

    default:
      if (typeof value === 'number') {
        if (Math.abs(value) >= 1000000) return `${(value / 1000000).toFixed(1)}M`;
        if (Math.abs(value) >= 1000) return `${(value / 1000).toFixed(1)}K`;
        return value.toLocaleString();
      }
      return String(value);
  }
}

function formatWithSign(value: number): string {
  if (value > 0) return `+${value.toLocaleString()}`;
  return value.toLocaleString();
}

export function ExpandedView({
  metrics,
  onCollapse,
  onScrollToEvent,
}: ExpandedViewProps) {
  const byCategory = metrics.by_category || {};

  // Extract key metrics
  const cost = byCategory.tokens?.estimated_cost?.value as number ?? 0;
  const cacheSavings = byCategory.tokens?.cache_savings?.value as number ?? 0;

  const filesChanged = byCategory.tools?.files_changed?.value as number ?? 0;
  const linesAdded = byCategory.tools?.lines_added?.value as number ?? 0;
  const linesRemoved = byCategory.tools?.lines_removed?.value as number ?? 0;
  const netLines = byCategory.tools?.net_lines?.value as number ?? 0;
  const edits = byCategory.tools?.edit_count?.value as number ?? 0;
  const filesRead = byCategory.tools?.files_read?.value as number ?? 0;

  const duration = byCategory.timing?.session_duration?.value as number | null;

  const prompts = byCategory.interaction?.prompt_count?.value as number ?? 0;
  const editsPerPrompt = byCategory.interaction?.edits_per_prompt?.value as number ?? 0;
  const completionRate = byCategory.interaction?.completion_rate?.value as number ?? 0;

  // Get chart data from metrics (pre-computed by backend)
  const chartData = byCategory.charts?.prompt_turns?.value as PromptTurnsData | null;

  return (
    <div className="w-[calc(50%-7rem)] bg-card border-x border-border flex flex-col overflow-hidden shrink-0">
      {/* Header with branding and key metrics */}
      <div className="px-4 py-3 border-b border-border">
        <div className="flex items-center justify-between">
          {/* SuperTrace branding */}
          <div className="flex items-center gap-3">
            <span className="text-sm font-semibold text-foreground tracking-wide">SuperTrace</span>
            <span className="text-muted-foreground/50">|</span>
            {/* Inline key metrics */}
            <div className="flex items-center gap-3 text-xs">
              <div className="flex items-center gap-1.5 group relative cursor-default">
                <i className="ri-money-dollar-circle-line text-[color:var(--cost)]" />
                <span className="font-semibold text-foreground">${cost.toFixed(2)}</span>
                <div className="absolute top-full left-1/2 -translate-x-1/2 mt-2 px-2 py-1 bg-popover border border-border rounded shadow-lg text-xs whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10">
                  Total session cost (API usage)
                </div>
              </div>
              {cacheSavings > 0 && (
                <div className="flex items-center gap-1 group relative cursor-default">
                  <i className="ri-leaf-line text-[color:var(--success)]" />
                  <span className="text-[color:var(--success)] font-medium">-${cacheSavings.toFixed(2)}</span>
                  <div className="absolute top-full left-1/2 -translate-x-1/2 mt-2 px-2 py-1 bg-popover border border-border rounded shadow-lg text-xs whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10">
                    Saved by prompt caching
                  </div>
                </div>
              )}
              {duration !== null && (
                <div className="flex items-center gap-1 group relative cursor-default">
                  <i className="ri-time-line text-muted-foreground" />
                  <span className="text-muted-foreground">{formatValue(duration, 'duration')}</span>
                  <div className="absolute top-full left-1/2 -translate-x-1/2 mt-2 px-2 py-1 bg-popover border border-border rounded shadow-lg text-xs whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10">
                    Session duration
                  </div>
                </div>
              )}
            </div>
          </div>
          <button
            onClick={onCollapse}
            className="p-1.5 hover:bg-accent rounded transition-colors"
            title="Collapse"
          >
            <i className="ri-arrow-left-double-line text-muted-foreground" />
          </button>
        </div>
      </div>

      {/* Scrollable content */}
      <div className="flex-1 overflow-y-auto">
        {/* Unified Prompt Metrics Chart */}
        <div className="px-5 py-4 border-b border-border">
          <div className="text-xs text-muted-foreground uppercase tracking-wider mb-3 font-semibold">
            Tokens & Tools by Prompt
          </div>
          <PromptMetricsChart data={chartData} onPromptClick={onScrollToEvent} />
        </div>

        {/* Work Output */}
        <div className="px-5 py-4 border-b border-border">
          <div className="text-xs text-muted-foreground uppercase tracking-wider mb-3 font-semibold">Work Output</div>

          <div className="grid grid-cols-2 gap-3">
            <div className="bg-muted/50 rounded-lg p-3">
              <div className="text-2xl font-bold text-[color:var(--info)]">{filesChanged}</div>
              <div className="text-xs text-foreground mt-1">Files changed</div>
            </div>
            <div className="bg-muted/50 rounded-lg p-3">
              <div className={`text-2xl font-bold ${netLines >= 0 ? 'text-[color:var(--success)]' : 'text-destructive'}`}>
                {formatWithSign(netLines)}
              </div>
              <div className="text-xs text-foreground mt-1">Net lines</div>
            </div>
          </div>

          <div className="mt-3 flex items-center gap-4 text-sm">
            <div className="flex items-center gap-1.5">
              <i className="ri-add-line text-[color:var(--success)]" />
              <span className="text-foreground font-medium">{linesAdded.toLocaleString()}</span>
            </div>
            <div className="flex items-center gap-1.5">
              <i className="ri-subtract-line text-destructive" />
              <span className="text-foreground font-medium">{linesRemoved.toLocaleString()}</span>
            </div>
          </div>

          <div className="mt-3 flex items-center gap-4 text-xs text-muted-foreground">
            <span><strong className="text-foreground">{edits}</strong> edits</span>
            <span><strong className="text-foreground">{filesRead}</strong> files read</span>
          </div>
        </div>

        {/* Efficiency */}
        <div className="px-5 py-4">
          <div className="text-xs text-muted-foreground uppercase tracking-wider mb-3 font-semibold">Efficiency</div>

          <div className="space-y-2.5">
            <div className="flex items-center justify-between">
              <span className="text-sm text-foreground">Prompts</span>
              <span className="text-sm font-semibold text-foreground">{prompts}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-foreground">Edits per prompt</span>
              <span className="text-sm font-semibold text-foreground">{editsPerPrompt}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-foreground">Completion rate</span>
              <span className="text-sm font-semibold text-foreground">{completionRate}%</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
