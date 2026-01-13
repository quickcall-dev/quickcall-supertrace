/**
 * Timing Chart
 *
 * Shows turn duration as bars with timestamps on x-axis.
 * Helps visualize iteration speed.
 */

import { useEffect, useRef, useState } from 'react';
import type { PromptTurnsData } from '../../api/client';
import { formatTime } from '../../utils/time';

interface TimingChartProps {
  data: PromptTurnsData | null;
  onPromptClick?: (eventId: number) => void;
}

export function TimingChart({ data, onPromptClick }: TimingChartProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [hoveredPrompt, setHoveredPrompt] = useState<number | null>(null);
  const [scrollLeft, setScrollLeft] = useState(0);

  // Auto-scroll to latest
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollLeft = scrollRef.current.scrollWidth;
    }
  }, [data?.turns.length]);

  if (!data || data.turns.length === 0) {
    return (
      <div className="text-center py-4 text-muted-foreground text-sm">
        No timing data yet
      </div>
    );
  }

  const { turns, maxDuration } = data;

  // Filter turns with valid duration
  const turnsWithDuration = turns.filter(t => t.durationSeconds !== null);

  if (turnsWithDuration.length === 0) {
    return (
      <div className="text-center py-4 text-muted-foreground text-sm">
        No timing data available
      </div>
    );
  }

  const formatDuration = (seconds: number | null): string => {
    if (seconds === null || isNaN(seconds)) return '-';
    if (seconds < 60) return `${Math.round(seconds)}s`;
    const mins = Math.floor(seconds / 60);
    const secs = Math.round(seconds % 60);
    return secs > 0 ? `${mins}m ${secs}s` : `${mins}m`;
  };

  // Chart dimensions
  const yAxisWidth = 32;
  const pointSpacing = 56;
  const graphWidth = Math.max(turns.length * pointSpacing, 180);
  const chartHeight = 60;
  const xAxisHeight = 28;
  const padding = { top: 4, bottom: 4 };
  const graphHeight = chartHeight - padding.top - padding.bottom;

  const totalHeight = chartHeight + xAxisHeight;

  // Position helpers
  const getX = (index: number) => {
    if (turns.length === 1) return 12 + (graphWidth - 24) / 2;
    return 12 + (index / (turns.length - 1)) * (graphWidth - 24);
  };

  // Use 90th percentile to avoid outliers dominating the scale
  const durations = turnsWithDuration
    .map(t => t.durationSeconds!)
    .filter(d => d > 0)
    .sort((a, b) => a - b);

  const p90Index = Math.floor(durations.length * 0.9);
  const p90Duration = durations[p90Index] || maxDuration || 1;
  // Use p90 as scale max, but at least show up to actual max if not too extreme
  const scaleMax = Math.max(p90Duration, (maxDuration || 1) * 0.3);
  const safeMaxDuration = scaleMax || 1;

  const getBarHeight = (duration: number | null) => {
    if (duration === null) return 0;
    // Cap at 100% height for outliers
    const ratio = Math.min(duration / safeMaxDuration, 1);
    return ratio * graphHeight;
  };

  // Y-axis ticks
  const yTicks = [0, 0.5, 1].map(ratio => ({
    value: Math.round(safeMaxDuration * ratio),
    y: padding.top + graphHeight - (ratio * graphHeight),
  }));

  // Get hovered turn data for tooltip
  const hoveredTurn = hoveredPrompt !== null ? turns[hoveredPrompt] : null;
  const hoveredX = hoveredPrompt !== null ? getX(hoveredPrompt) : 0;

  return (
    <div className="space-y-2">
      <div className="flex relative">
        {/* Fixed Y-axis */}
        <div className="shrink-0 flex flex-col" style={{ width: yAxisWidth }}>
          <svg width={yAxisWidth} height={chartHeight} className="block">
            {yTicks.map((tick, idx) => (
              <text
                key={idx}
                x={yAxisWidth - 2}
                y={tick.y + 3}
                textAnchor="end"
                className="text-[8px] fill-muted-foreground"
              >
                {formatDuration(tick.value)}
              </text>
            ))}
          </svg>
          <div style={{ height: xAxisHeight }} />
        </div>

        {/* Scrollable chart area */}
        <div
          ref={scrollRef}
          className="flex-1 overflow-x-auto"
          onScroll={(e) => setScrollLeft(e.currentTarget.scrollLeft)}
        >
          <svg width={graphWidth} height={totalHeight} className="block">
            {/* Grid lines */}
            {yTicks.map((tick, idx) => (
              <line
                key={idx}
                x1={0}
                y1={tick.y}
                x2={graphWidth}
                y2={tick.y}
                stroke="currentColor"
                strokeOpacity={0.08}
                strokeDasharray="2,2"
              />
            ))}

            {/* Duration bars */}
            {turns.map((turn, idx) => {
              const x = getX(idx);
              const barWidth = 20;
              const barHeight = getBarHeight(turn.durationSeconds);
              const isHovered = hoveredPrompt === idx;

              return (
                <g key={idx}>
                  <rect
                    x={x - barWidth / 2}
                    y={padding.top + graphHeight - barHeight}
                    width={barWidth}
                    height={barHeight}
                    fill="var(--primary)"
                    opacity={isHovered ? 1 : 0.6}
                    rx={2}
                  />
                </g>
              );
            })}

            {/* X-axis with timestamps */}
            <g transform={`translate(0, ${chartHeight})`}>
              <line x1={0} y1={0} x2={graphWidth} y2={0} stroke="currentColor" strokeOpacity={0.15} />

              {turns.map((turn, idx) => {
                const x = getX(idx);
                const isHovered = hoveredPrompt === idx;

                return (
                  <g key={idx}>
                    {/* Hover zone */}
                    <rect
                      x={x - 24}
                      y={-chartHeight}
                      width={48}
                      height={chartHeight + xAxisHeight}
                      fill="transparent"
                      className="cursor-pointer"
                      onMouseEnter={() => setHoveredPrompt(idx)}
                      onMouseLeave={() => setHoveredPrompt(null)}
                      onClick={() => onPromptClick?.(turn.promptEventId)}
                    />

                    {/* Vertical hover indicator */}
                    {isHovered && (
                      <line
                        x1={x}
                        y1={-chartHeight}
                        x2={x}
                        y2={0}
                        stroke="currentColor"
                        strokeOpacity={0.2}
                        strokeDasharray="4,4"
                      />
                    )}

                    {/* Time label */}
                    <text
                      x={x}
                      y={12}
                      textAnchor="middle"
                      className={`text-[8px] ${isHovered ? 'fill-foreground font-medium' : 'fill-muted-foreground'}`}
                    >
                      {formatTime(turn.startTime)}
                    </text>

                    {/* Prompt number */}
                    <text
                      x={x}
                      y={22}
                      textAnchor="middle"
                      className={`text-[8px] ${isHovered ? 'fill-foreground' : 'fill-muted-foreground/50'}`}
                    >
                      #{turn.promptIndex}
                    </text>
                  </g>
                );
              })}
            </g>
          </svg>
        </div>

        {/* Tooltip - positioned above the chart */}
        {hoveredTurn && hoveredTurn.durationSeconds !== null && (
          <div
            className="absolute pointer-events-none z-20 bg-popover border border-border rounded-lg shadow-lg px-3 py-2 text-xs"
            style={{
              left: yAxisWidth + hoveredX - scrollLeft,
              bottom: totalHeight + 8,
              transform: 'translateX(-50%)',
            }}
          >
            <div className="font-semibold text-foreground mb-1">
              Prompt {hoveredTurn.promptIndex}
            </div>
            <div className="space-y-0.5 text-muted-foreground">
              <div className="flex items-center gap-2">
                <i className="ri-time-line text-primary" />
                <span className="font-mono">{formatDuration(hoveredTurn.durationSeconds)}</span>
              </div>
              {hoveredTurn.startTime && (
                <div className="text-[10px]">
                  {formatTime(hoveredTurn.startTime)} → {formatTime(hoveredTurn.endTime)}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
