/**
 * Expanded analytics view with compact header and charts.
 */

import { useState } from 'react';
import type { MetricsResponse, MetricFormat, PromptTurnsData } from '../../api/client';
import { PromptMetricsChart } from './PromptMetricsChart';
import { TimingChart } from './TimingChart';
import { ToolDistributionChart } from './ToolDistributionChart';

// Simple tooltip wrapper - shows BELOW the element
function Tooltip({ children, text }: { children: React.ReactNode; text: string }) {
  const [show, setShow] = useState(false);
  return (
    <span
      className="relative inline-flex"
      onMouseEnter={() => setShow(true)}
      onMouseLeave={() => setShow(false)}
    >
      {children}
      {show && (
        <span className="absolute top-full left-1/2 -translate-x-1/2 mt-1.5 px-2 py-1 text-[10px] bg-popover text-popover-foreground border border-border rounded shadow-lg whitespace-nowrap z-50">
          {text}
        </span>
      )}
    </span>
  );
}

interface ExpandedViewProps {
  metrics: MetricsResponse;
  onCollapse: () => void;
  onScrollToEvent?: (eventId: number) => void;
  hoursBack?: number;
  onTimeRangeChange?: (hours: number) => void;
  loading?: boolean;
  isJumpingToEvent?: boolean;
}

const TIME_OPTIONS = [
  { value: 1, label: '1h' },
  { value: 2, label: '2h' },
  { value: 6, label: '6h' },
  { value: 24, label: '24h' },
  { value: 0, label: 'All' },
];

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
  hoursBack = 2,
  onTimeRangeChange,
  loading = false,
  isJumpingToEvent = false,
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

  const commits = byCategory.interaction?.commit_count?.value as number ?? 0;
  const turnsPerCommit = byCategory.interaction?.turns_per_commit?.value as number ?? 0;
  const toolSuccessRate = byCategory.interaction?.tool_success_rate?.value as number ?? 100;
  const linesPerHour = byCategory.interaction?.lines_per_hour?.value as number ?? 0;
  const imagesSent = byCategory.interaction?.images_sent?.value as number ?? 0;
  const thinkingUsage = byCategory.interaction?.thinking_usage?.value as string ?? '0/0';

  // Get chart data from metrics (pre-computed by backend)
  const chartData = byCategory.charts?.prompt_turns?.value as PromptTurnsData | null;

  return (
    <div className="w-[calc(50%-7rem)] bg-card border-x border-border flex flex-col overflow-hidden shrink-0 relative">
      {/* Header - compact single row matching SessionView */}
      <div className="h-12 px-4 border-b border-border bg-card/95 backdrop-blur-sm flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3 text-sm">
          <span className="font-semibold text-foreground">Analytics</span>
          {loading && (
            <i className="ri-loader-4-line animate-spin text-muted-foreground text-sm" />
          )}
          <span className="text-muted-foreground/50">·</span>
          <Tooltip text="Estimated API cost">
            <span className="text-xs text-foreground font-medium">
              ${cost.toFixed(2)}
            </span>
          </Tooltip>
          {cacheSavings > 0 && (
            <Tooltip text="Savings from prompt caching">
              <span className="text-xs text-[color:var(--success)]">
                -${cacheSavings.toFixed(2)}
              </span>
            </Tooltip>
          )}
          {duration !== null && (
            <>
              <span className="text-muted-foreground/50">·</span>
              <Tooltip text="Session duration">
                <span className="text-xs text-muted-foreground">
                  {formatValue(duration, 'duration')}
                </span>
              </Tooltip>
            </>
          )}
        </div>
        <div className="flex items-center gap-2">
          {/* Time range selector */}
          <div className="flex items-center gap-0.5 bg-muted rounded-md p-0.5">
            {TIME_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                onClick={() => onTimeRangeChange?.(opt.value)}
                className={`px-2 py-0.5 text-[10px] font-medium rounded transition-colors ${
                  hoursBack === opt.value
                    ? 'bg-background text-foreground shadow-sm'
                    : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                {opt.label}
              </button>
            ))}
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

      {/* Loading overlay when jumping to event */}
      {isJumpingToEvent && (
        <div className="absolute inset-0 bg-card/80 backdrop-blur-sm flex items-center justify-center z-10">
          <div className="flex items-center gap-3 text-muted-foreground bg-card px-4 py-3 rounded-lg border border-border shadow-lg">
            <i className="ri-loader-4-line animate-spin text-lg" />
            <span className="text-sm">Loading conversation...</span>
          </div>
        </div>
      )}

      {/* Scrollable content */}
      <div className="flex-1 overflow-y-auto">
        {/* Hero Metrics - 2x2 Bento Grid at top */}
        <div className="px-5 py-4 border-b border-border">
          <div className="text-xs text-muted-foreground uppercase tracking-wider mb-3 font-semibold">Session Overview</div>

          <div className="grid grid-cols-3 gap-2">
            <div className="bg-muted/50 rounded-lg p-3">
              <div className={`text-2xl font-bold ${commits > 0 ? 'text-[color:var(--success)]' : 'text-muted-foreground'}`}>
                {commits}
              </div>
              <div className="text-xs text-muted-foreground mt-1">Commits</div>
              <div className="text-[10px] text-muted-foreground/70 mt-0.5">Shipped output</div>
            </div>

            <div className="bg-muted/50 rounded-lg p-3">
              <div className={`text-2xl font-bold ${turnsPerCommit === 0 ? 'text-muted-foreground' : turnsPerCommit <= 5 ? 'text-[color:var(--success)]' : turnsPerCommit <= 10 ? 'text-amber-500' : 'text-destructive'}`}>
                {turnsPerCommit || '—'}
              </div>
              <div className="text-xs text-muted-foreground mt-1">Turns / Commit</div>
              <div className="text-[10px] text-muted-foreground/70 mt-0.5">Lower = faster</div>
            </div>

            <div className="bg-muted/50 rounded-lg p-3">
              <div className={`text-2xl font-bold ${toolSuccessRate >= 95 ? 'text-[color:var(--success)]' : toolSuccessRate >= 80 ? 'text-amber-500' : 'text-destructive'}`}>
                {toolSuccessRate}%
              </div>
              <div className="text-xs text-muted-foreground mt-1">Tool Success</div>
              <div className="text-[10px] text-muted-foreground/70 mt-0.5">Smooth session</div>
            </div>

            <div className="bg-muted/50 rounded-lg p-3">
              <div className={`text-2xl font-bold ${linesPerHour >= 500 ? 'text-[color:var(--success)]' : linesPerHour >= 100 ? 'text-amber-500' : 'text-primary'}`}>
                {linesPerHour.toLocaleString()}
              </div>
              <div className="text-xs text-muted-foreground mt-1">Lines / Hour</div>
              <div className="text-[10px] text-muted-foreground/70 mt-0.5">Productivity</div>
            </div>

            <div className="bg-muted/50 rounded-lg p-3">
              <div className={`text-2xl font-bold ${imagesSent > 0 ? 'text-[color:var(--info)]' : 'text-muted-foreground'}`}>
                {imagesSent}
              </div>
              <div className="text-xs text-muted-foreground mt-1">Images</div>
              <div className="text-[10px] text-muted-foreground/70 mt-0.5">Visual context</div>
            </div>

            <div className="bg-muted/50 rounded-lg p-3">
              <div className={`text-2xl font-bold ${thinkingUsage.startsWith('0/') ? 'text-muted-foreground' : 'text-purple-500'}`}>
                {thinkingUsage}
              </div>
              <div className="text-xs text-muted-foreground mt-1">Thinking</div>
              <div className="text-[10px] text-muted-foreground/70 mt-0.5">Extended reasoning</div>
            </div>
          </div>
        </div>

        {/* Unified Prompt Metrics Chart */}
        <div className="px-5 py-4 border-b border-border">
          <div className="text-xs text-muted-foreground uppercase tracking-wider mb-3 font-semibold">
            Tokens & Tools by Prompt
          </div>
          <PromptMetricsChart data={chartData} onPromptClick={onScrollToEvent} />
        </div>

        {/* Tool Distribution */}
        <div className="px-5 py-4 border-b border-border">
          <div className="text-xs text-muted-foreground uppercase tracking-wider mb-3 font-semibold">
            Tool Usage
          </div>
          <ToolDistributionChart data={chartData} />
        </div>

        {/* Turn Timing Chart */}
        <div className="px-5 py-4 border-b border-border">
          <div className="text-xs text-muted-foreground uppercase tracking-wider mb-3 font-semibold">
            Turn Duration
          </div>
          <TimingChart data={chartData} onPromptClick={onScrollToEvent} />
        </div>

        {/* Work Output - Compact row */}
        <div className="px-5 py-3 flex items-center justify-between text-xs">
          <div className="flex items-center gap-4">
            {/* Files changed */}
            <div className="flex items-center gap-1.5" title="Files changed">
              <i className="ri-file-edit-line text-[color:var(--info)]" />
              <span className="font-semibold text-foreground">{filesChanged}</span>
              <span className="text-muted-foreground">files</span>
            </div>

            {/* Lines added/removed */}
            <div className="flex items-center gap-2 text-muted-foreground">
              <span className="text-[color:var(--success)] font-medium">+{linesAdded.toLocaleString()}</span>
              <span>/</span>
              <span className="text-destructive font-medium">-{linesRemoved.toLocaleString()}</span>
            </div>

            {/* Net lines */}
            <div className={`font-semibold ${netLines >= 0 ? 'text-[color:var(--success)]' : 'text-destructive'}`} title="Net lines">
              ({formatWithSign(netLines)} net)
            </div>
          </div>

          <div className="flex items-center gap-3 text-muted-foreground">
            <span><strong className="text-foreground">{edits}</strong> edits</span>
            <span><strong className="text-foreground">{filesRead}</strong> reads</span>
          </div>
        </div>
      </div>
    </div>
  );
}
