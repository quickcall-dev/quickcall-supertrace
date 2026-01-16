/**
 * Expanded analytics view with compact header and charts.
 *
 * ============================================================================
 * TOOLTIP & HOVER DESIGN GUIDELINES
 * ============================================================================
 *
 * PROBLEM: Panels have `overflow-hidden` to prevent layout issues during
 * resize/refresh. This clips any tooltip/hover content that extends beyond
 * panel boundaries (especially near the right edge where panels meet).
 *
 * SOLUTION: All hover/tooltip content MUST be contained within panel bounds.
 *
 * PATTERNS TO FOLLOW:
 *
 * 1. EDGE DETECTION (see PromptMetricsChart.tsx for reference):
 *    - Calculate tooltip position relative to container
 *    - Detect if tooltip would overflow right edge
 *    - Flip tooltip direction when near edge (translateX(-100%) instead of -50%)
 *
 *    Example:
 *    ```
 *    const containerWidth = containerRef.current?.clientWidth || 400;
 *    const tooltipX = elementX;
 *    const nearRightEdge = tooltipX + tooltipWidth / 2 > containerWidth - 10;
 *    transform: nearRightEdge ? 'translateX(-100%)' : 'translateX(-50%)'
 *    ```
 *
 * 2. TOOLTIP POSITIONING:
 *    - Use `absolute` positioning within a `relative` container
 *    - NEVER let tooltips extend past parent panel boundaries
 *    - For right-edge items, anchor tooltip to the LEFT of the trigger
 *    - For left-edge items, anchor tooltip to the RIGHT of the trigger
 *
 * 3. REQUIRED CLASSES:
 *    - `pointer-events-none` - prevents tooltip from blocking interactions
 *    - `z-20` or higher - ensures tooltip appears above other content
 *    - `whitespace-nowrap` OR `max-w-[Xpx]` - controls tooltip width
 *
 * 4. DO NOT:
 *    - Use CSS-only tooltips without edge detection near panel edges
 *    - Assume tooltips can overflow into adjacent panels
 *    - Use `position: fixed` (breaks with scrolling containers)
 *
 * ============================================================================
 */

import { useState, useRef, useCallback } from 'react';
import type { MetricsResponse, MetricFormat, PromptTurnsData, Session } from '../../api/client';
import { PromptMetricsChart } from './PromptMetricsChart';
import { TimingChart } from './TimingChart';
import { ToolDistributionChart } from './ToolDistributionChart';

/**
 * Smart Tooltip with edge detection.
 *
 * Automatically adjusts position to stay within parent container bounds.
 * Shows BELOW the element by default, flips LEFT when near right edge.
 */
function Tooltip({ children, text }: { children: React.ReactNode; text: string }) {
  const [show, setShow] = useState(false);
  const [position, setPosition] = useState<'center' | 'left' | 'right'>('center');
  const triggerRef = useRef<HTMLSpanElement>(null);

  const calculatePosition = useCallback(() => {
    if (!triggerRef.current) return;

    const trigger = triggerRef.current;
    const rect = trigger.getBoundingClientRect();

    // Find the parent panel (the analytics panel container)
    const panel = trigger.closest('[data-panel="analytics"]');
    if (!panel) {
      setPosition('center');
      return;
    }

    const panelRect = panel.getBoundingClientRect();
    const tooltipWidth = 180; // Estimated max tooltip width

    // Check if tooltip would overflow right edge
    const rightSpace = panelRect.right - rect.left - rect.width / 2;
    const leftSpace = rect.left + rect.width / 2 - panelRect.left;

    if (rightSpace < tooltipWidth / 2 + 10) {
      setPosition('left'); // Anchor to left side of trigger
    } else if (leftSpace < tooltipWidth / 2 + 10) {
      setPosition('right'); // Anchor to right side of trigger
    } else {
      setPosition('center');
    }
  }, []);

  const handleMouseEnter = () => {
    calculatePosition();
    setShow(true);
  };

  // Position transform based on edge detection
  const getTransform = () => {
    switch (position) {
      case 'left': return 'translateX(-90%)'; // Anchor tooltip to left
      case 'right': return 'translateX(-10%)'; // Anchor tooltip to right
      default: return 'translateX(-50%)'; // Center (default)
    }
  };

  return (
    <span
      ref={triggerRef}
      className="relative inline-flex"
      onMouseEnter={handleMouseEnter}
      onMouseLeave={() => setShow(false)}
    >
      {children}
      {show && (
        <span
          className="absolute top-full left-1/2 mt-1.5 px-2 py-1 text-[10px] bg-popover text-popover-foreground border border-border rounded shadow-lg whitespace-nowrap z-50 pointer-events-none"
          style={{ transform: getTransform() }}
        >
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
  session?: Session | null;
  width?: number;
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
  hoursBack = 0,
  onTimeRangeChange,
  loading = false,
  isJumpingToEvent = false,
  session,
  width = 400,
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
    <div style={{ width }} className="bg-card border-x border-border flex flex-col overflow-hidden shrink-0 relative" data-panel="analytics">
      {/* Header - uses --header-height for consistency */}
      <div className="px-4 border-b border-border bg-card/95 backdrop-blur-sm flex items-center justify-between shrink-0" style={{ height: 'var(--header-height)' }}>
        <div className="flex items-center gap-2">
          <span className="font-semibold text-foreground text-sm">Session Analytics</span>
          {loading && (
            <i className="ri-loader-4-line animate-spin text-muted-foreground text-sm" />
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

      {/* Subheader - session info and stats */}
      <div className="px-4 py-2 border-b border-border bg-muted/30 shrink-0 flex items-center gap-3">
        {/* Session title (first prompt) - 2 lines max */}
        <div
          className="flex-1 min-w-0 text-xs text-muted-foreground line-clamp-2 leading-tight"
          title={session?.first_prompt || ''}
        >
          {session?.first_prompt || 'New session'}
        </div>
        {/* Stats */}
        <div className="flex items-center gap-3 text-xs shrink-0">
          <Tooltip text="Estimated API cost">
            <span className="text-foreground font-medium">
              ${cost.toFixed(2)}
            </span>
          </Tooltip>
          {cacheSavings > 0 && (
            <Tooltip text="Savings from prompt caching">
              <span className="text-[color:var(--success)]">
                -${cacheSavings.toFixed(2)} saved
              </span>
            </Tooltip>
          )}
          {duration !== null && (
            <Tooltip text="Session duration">
              <span className="text-muted-foreground">
                {formatValue(duration, 'duration')}
              </span>
            </Tooltip>
          )}
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
        <div className="px-5 py-4 border-b border-border overflow-hidden">
          <div className="flex items-center justify-between mb-3">
            <div className="text-xs text-muted-foreground uppercase tracking-wider font-semibold">
              Tokens & Tools by Prompt
            </div>
            <Tooltip text="Click on a bar to jump to that prompt in the conversation">
              <span className="flex items-center gap-1 text-[10px] text-muted-foreground/70 cursor-help">
                <i className="ri-cursor-line text-xs" />
                <span>click to jump</span>
              </span>
            </Tooltip>
          </div>
          <PromptMetricsChart data={chartData} onPromptClick={onScrollToEvent} />
        </div>

        {/* Tool Distribution */}
        <div className="px-5 py-4 border-b border-border overflow-hidden">
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
        <div className="px-5 py-3 flex flex-wrap items-center justify-between gap-2 text-xs overflow-hidden">
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
