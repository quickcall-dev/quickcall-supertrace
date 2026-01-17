/**
 * Unified Prompt Metrics Chart
 *
 * Shows tokens (line chart) and tool usage (stacked bars) per prompt turn.
 * Shared x-axis, synchronized scrolling, auto-scroll to latest.
 *
 * Uses pre-computed data from backend for performance.
 */

import { useEffect, useRef, useState } from 'react';
import type { PromptTurnsData } from '../../api/client';

interface PromptMetricsChartProps {
  data: PromptTurnsData | null;
  onPromptClick?: (eventId: number) => void;
}

export function PromptMetricsChart({ data, onPromptClick }: PromptMetricsChartProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [hoveredPrompt, setHoveredPrompt] = useState<number | null>(null);
  const [scrollLeft, setScrollLeft] = useState(0);
  const [showCache, setShowCache] = useState(true); // Toggle for cache visibility

  // Auto-scroll to latest
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollLeft = scrollRef.current.scrollWidth;
    }
  }, [data?.turns.length]);

  if (!data || data.turns.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground text-sm">
        No prompt data yet
      </div>
    );
  }

  const { turns, maxTokens, maxTokensNoCache, maxTools, totals, toolLegend } = data;

  // Use appropriate max based on cache toggle
  const effectiveMaxTokens = showCache ? maxTokens : maxTokensNoCache;

  // Helper to get input tokens for a turn based on cache toggle
  const getInputTokens = (turn: typeof turns[0]) =>
    showCache ? turn.inputTokens : (turn.inputTokensNoCache ?? turn.inputTokens);

  const formatTokens = (n: number): string => {
    if (n >= 1000000) return `${(n / 1000000).toFixed(1)}M`;
    if (n >= 1000) return `${(n / 1000).toFixed(1)}K`;
    return n.toString();
  };

  const formatTokensShort = (n: number): string => {
    if (n >= 1000000) return `${(n / 1000000).toFixed(0)}M`;
    if (n >= 1000) return `${(n / 1000).toFixed(0)}K`;
    return n.toString();
  };

  // Chart dimensions
  const yAxisWidth = 28;
  const pointSpacing = 56;
  const graphWidth = Math.max(turns.length * pointSpacing, 180);

  const tokenChartHeight = 80;
  const toolChartHeight = 100;
  const commitLaneHeight = totals.commits > 0 ? 20 : 0;
  const thinkingLaneHeight = totals.thinking > 0 ? 20 : 0;
  const xAxisHeight = 20;
  const gapHeight = 8;

  const tokenPadding = { top: 8, bottom: 4 };
  const toolPadding = { top: 4, bottom: 4 };

  const tokenGraphHeight = tokenChartHeight - tokenPadding.top - tokenPadding.bottom;
  const toolGraphHeight = toolChartHeight - toolPadding.top - toolPadding.bottom;

  // Position helpers
  const getX = (index: number) => {
    if (turns.length === 1) return 12 + (graphWidth - 24) / 2;
    return 12 + (index / (turns.length - 1)) * (graphWidth - 24);
  };

  const safeMaxTokens = effectiveMaxTokens || 1;
  const safeMaxTools = maxTools || 1;

  const getTokenY = (value: number) => {
    const normalized = value / safeMaxTokens;
    return tokenPadding.top + tokenGraphHeight - (normalized * tokenGraphHeight);
  };

  // Build token line paths (use getInputTokens for cache toggle)
  const inputPoints = turns.map((t, i) => `${getX(i)},${getTokenY(getInputTokens(t))}`);
  const outputPoints = turns.map((t, i) => `${getX(i)},${getTokenY(t.outputTokens)}`);
  const inputPath = `M ${inputPoints.join(' L ')}`;
  const outputPath = `M ${outputPoints.join(' L ')}`;

  // Token Y-axis ticks
  const tokenTicks = [0, 0.5, 1].map(ratio => ({
    value: Math.round(safeMaxTokens * ratio),
    y: getTokenY(safeMaxTokens * ratio),
  }));

  // Tool Y-axis ticks
  const toolTicks = [0, Math.ceil(safeMaxTools / 2), safeMaxTools].map((value) => ({
    value,
    y: toolPadding.top + toolGraphHeight - (value / safeMaxTools) * toolGraphHeight,
  }));

  const totalHeight = tokenChartHeight + gapHeight + toolChartHeight + commitLaneHeight + thinkingLaneHeight + xAxisHeight;

  // Get hovered turn data for tooltip
  const hoveredTurn = hoveredPrompt !== null ? turns[hoveredPrompt] : null;
  const hoveredX = hoveredPrompt !== null ? getX(hoveredPrompt) : 0;

  return (
    <div className="space-y-2">
      {/* Chart with fixed Y-axes */}
      <div className="flex relative">
        {/* Fixed Y-axes */}
        <div className="shrink-0 flex flex-col" style={{ width: yAxisWidth }}>
          {/* Token Y-axis */}
          <svg width={yAxisWidth} height={tokenChartHeight} className="block">
            {tokenTicks.map((tick, idx) => (
              <text
                key={idx}
                x={yAxisWidth - 2}
                y={tick.y + 3}
                textAnchor="end"
                className="text-[8px] fill-muted-foreground"
              >
                {formatTokensShort(tick.value)}
              </text>
            ))}
          </svg>

          {/* Gap */}
          <div style={{ height: gapHeight }} />

          {/* Tool Y-axis */}
          <svg width={yAxisWidth} height={toolChartHeight} className="block">
            {toolTicks.map((tick, idx) => (
              <text
                key={idx}
                x={yAxisWidth - 2}
                y={tick.y + 3}
                textAnchor="end"
                className="text-[8px] fill-muted-foreground"
              >
                {tick.value}
              </text>
            ))}
          </svg>

          {/* Commit lane label */}
          {commitLaneHeight > 0 && (
            <div style={{ height: commitLaneHeight }} className="flex items-center justify-end pr-1">
              <i className="ri-git-commit-line text-[10px] text-[color:var(--warning)]" />
            </div>
          )}

          {/* Thinking lane label */}
          {thinkingLaneHeight > 0 && (
            <div style={{ height: thinkingLaneHeight }} className="flex items-center justify-end pr-1">
              <i className="ri-brain-line text-[10px] text-purple-500" />
            </div>
          )}

          {/* X-axis space */}
          <div style={{ height: xAxisHeight }} />
        </div>

        {/* Scrollable chart area */}
        <div
          ref={scrollRef}
          className="flex-1 overflow-x-auto"
          onScroll={(e) => setScrollLeft(e.currentTarget.scrollLeft)}
        >
          <svg width={graphWidth} height={totalHeight} className="block">
            {/* Token chart section */}
            <g>
              {/* Grid lines */}
              {tokenTicks.map((tick, idx) => (
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

              {/* Lines */}
              <path
                d={inputPath}
                fill="none"
                stroke="var(--token-input)"
                strokeWidth={2}
                strokeLinecap="round"
                strokeLinejoin="round"
              />
              <path
                d={outputPath}
                fill="none"
                stroke="var(--token-output)"
                strokeWidth={2}
                strokeLinecap="round"
                strokeLinejoin="round"
              />

              {/* Markers */}
              {turns.map((turn, idx) => {
                const x = getX(idx);
                const isHovered = hoveredPrompt === idx;
                return (
                  <g key={idx}>
                    <circle cx={x} cy={getTokenY(getInputTokens(turn))} r={isHovered ? 6 : 4} fill="var(--token-input)" />
                    <circle cx={x} cy={getTokenY(getInputTokens(turn))} r={isHovered ? 3 : 2} fill="white" />
                    <circle cx={x} cy={getTokenY(turn.outputTokens)} r={isHovered ? 6 : 4} fill="var(--token-output)" />
                    <circle cx={x} cy={getTokenY(turn.outputTokens)} r={isHovered ? 3 : 2} fill="white" />
                  </g>
                );
              })}
            </g>

            {/* Tool chart section */}
            <g transform={`translate(0, ${tokenChartHeight + gapHeight})`}>
              {/* Grid lines */}
              {toolTicks.map((tick, idx) => (
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

              {/* Stacked bars */}
              {turns.map((turn, idx) => {
                const x = getX(idx);
                const barWidth = 24;
                const isHovered = hoveredPrompt === idx;

                let currentY = toolGraphHeight + toolPadding.top;

                return (
                  <g key={idx}>
                    {turn.tools.map((tool, toolIdx) => {
                      const barHeight = (tool.count / safeMaxTools) * toolGraphHeight;
                      currentY -= barHeight;
                      return (
                        <rect
                          key={toolIdx}
                          x={x - barWidth / 2}
                          y={currentY}
                          width={barWidth}
                          height={barHeight}
                          fill={tool.color}
                          opacity={isHovered ? 1 : 0.8}
                          rx={2}
                        />
                      );
                    })}
                  </g>
                );
              })}
            </g>

            {/* Commit lane - thin row with dots for commits */}
            {commitLaneHeight > 0 && (
              <g transform={`translate(0, ${tokenChartHeight + gapHeight + toolChartHeight})`}>
                {/* Horizontal line for commit lane */}
                <line
                  x1={0}
                  y1={commitLaneHeight / 2}
                  x2={graphWidth}
                  y2={commitLaneHeight / 2}
                  stroke="var(--warning)"
                  strokeOpacity={0.2}
                  strokeDasharray="4,4"
                />
                {/* Commit dots */}
                {turns.map((turn, idx) => {
                  if (!turn.hasCommit) return null;
                  const x = getX(idx);
                  return (
                    <circle
                      key={idx}
                      cx={x}
                      cy={commitLaneHeight / 2}
                      r={5}
                      fill="var(--warning)"
                      className="cursor-pointer"
                    />
                  );
                })}
              </g>
            )}

            {/* Thinking lane - thin row with dots for thinking */}
            {thinkingLaneHeight > 0 && (
              <g transform={`translate(0, ${tokenChartHeight + gapHeight + toolChartHeight + commitLaneHeight})`}>
                {/* Horizontal line for thinking lane */}
                <line
                  x1={0}
                  y1={thinkingLaneHeight / 2}
                  x2={graphWidth}
                  y2={thinkingLaneHeight / 2}
                  stroke="#a855f7"
                  strokeOpacity={0.2}
                  strokeDasharray="4,4"
                />
                {/* Thinking dots */}
                {turns.map((turn, idx) => {
                  if (!turn.hasThinking) return null;
                  const x = getX(idx);
                  return (
                    <circle
                      key={idx}
                      cx={x}
                      cy={thinkingLaneHeight / 2}
                      r={5}
                      fill="#a855f7"
                      className="cursor-pointer"
                    />
                  );
                })}
              </g>
            )}

            {/* X-axis labels and interaction */}
            <g transform={`translate(0, ${tokenChartHeight + gapHeight + toolChartHeight + commitLaneHeight + thinkingLaneHeight})`}>
              <line x1={0} y1={0} x2={graphWidth} y2={0} stroke="currentColor" strokeOpacity={0.15} />

              {turns.map((turn, idx) => {
                const x = getX(idx);
                const isHovered = hoveredPrompt === idx;

                return (
                  <g key={idx}>
                    {/* Hover zone spanning all charts */}
                    <rect
                      x={x - 24}
                      y={-tokenChartHeight - gapHeight - toolChartHeight - commitLaneHeight - thinkingLaneHeight}
                      width={48}
                      height={tokenChartHeight + gapHeight + toolChartHeight + commitLaneHeight + thinkingLaneHeight + xAxisHeight}
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
                        y1={-tokenChartHeight - gapHeight - toolChartHeight - commitLaneHeight - thinkingLaneHeight}
                        x2={x}
                        y2={0}
                        stroke="currentColor"
                        strokeOpacity={0.2}
                        strokeDasharray="4,4"
                      />
                    )}

                    {/* X label - always show prompt number */}
                    <text
                      x={x}
                      y={14}
                      textAnchor="middle"
                      className={`text-[9px] ${isHovered ? 'fill-foreground font-medium' : 'fill-muted-foreground'}`}
                    >
                      {turn.promptIndex}
                    </text>
                  </g>
                );
              })}
            </g>
          </svg>
        </div>

        {/* Custom tooltip */}
        {hoveredTurn && (() => {
          // Calculate tooltip position, flip to left if near right edge
          const tooltipWidth = 200;
          const containerWidth = scrollRef.current?.clientWidth || 400;
          const tooltipX = yAxisWidth + hoveredX - scrollLeft;
          const nearRightEdge = tooltipX + tooltipWidth > containerWidth - 10;

          return (
          <div
            className="absolute pointer-events-none z-50 bg-popover border border-border rounded-lg shadow-lg px-3 py-2 text-xs w-[200px]"
            style={{
              left: nearRightEdge ? tooltipX - tooltipWidth - 20 : tooltipX + 20,
              top: 8,
            }}
          >
            <div className="flex items-center gap-2 mb-1.5 flex-wrap">
              <span className="font-semibold text-foreground">Prompt {hoveredTurn.promptIndex}</span>
              {hoveredTurn.hasCommit && (
                <span className="text-[color:var(--warning)] text-[10px] font-medium px-1.5 py-0.5 bg-[color:var(--warning)]/10 rounded">
                  COMMIT
                </span>
              )}
              {hoveredTurn.hasThinking && (
                <span className="text-purple-500 text-[10px] font-medium px-1.5 py-0.5 bg-purple-500/10 rounded">
                  THINKING
                </span>
              )}
            </div>
            <div className="flex items-center gap-3 mb-1.5">
              <div className="flex items-center gap-1">
                <div className="w-2 h-2 rounded-full bg-[color:var(--token-input)]" />
                <span className="text-muted-foreground">{formatTokens(getInputTokens(hoveredTurn))}</span>
              </div>
              <div className="flex items-center gap-1">
                <div className="w-2 h-2 rounded-full bg-[color:var(--token-output)]" />
                <span className="text-muted-foreground">{formatTokens(hoveredTurn.outputTokens)}</span>
              </div>
            </div>
            {hoveredTurn.tools.length > 0 && (
              <div className="border-t border-border pt-1.5 space-y-1">
                {hoveredTurn.tools.slice(0, 3).map((tool) => (
                  <div key={tool.name} className="flex items-center justify-between gap-3">
                    <div className="flex items-center gap-1.5 min-w-0 flex-1">
                      <div className="w-2 h-2 rounded-sm shrink-0" style={{ backgroundColor: tool.color }} />
                      <span className="text-foreground truncate">{tool.name}</span>
                    </div>
                    <span className="text-muted-foreground font-mono shrink-0">{tool.count}×</span>
                  </div>
                ))}
                {hoveredTurn.tools.length > 3 && (
                  <div className="text-muted-foreground">
                    +{hoveredTurn.tools.length - 3} more
                  </div>
                )}
              </div>
            )}
            {hoveredTurn.tools.length === 0 && (
              <div className="text-muted-foreground">No tools</div>
            )}
          </div>
          );
        })()}
      </div>

      {/* Combined legend - two rows: tokens on top, tools+totals below */}
      <div className="text-xs pt-2 border-t border-border space-y-1.5">
        {/* Row 1: Token legend with cache toggle */}
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1">
            <div className="w-2 h-2 rounded-full bg-[color:var(--token-input)]" />
            <span className="text-muted-foreground">In</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-2 h-2 rounded-full bg-[color:var(--token-output)]" />
            <span className="text-muted-foreground">Out</span>
          </div>
          <button
            onClick={() => setShowCache(!showCache)}
            className={`ml-1 px-1.5 py-0.5 rounded text-[10px] font-medium transition-colors ${
              showCache
                ? 'bg-primary/20 text-primary'
                : 'bg-muted text-muted-foreground hover:bg-muted/80'
            }`}
            title={showCache ? 'Showing total context (with cache)' : 'Showing new tokens only (no cache)'}
          >
            {showCache ? '+cache' : 'no cache'}
          </button>
        </div>

        {/* Row 2: Tool legend + totals */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 min-w-0 overflow-hidden flex-1">
            {toolLegend.slice(0, 3).map((tool) => (
              <div key={tool.name} className="flex items-center gap-1 shrink-0">
                <div className="w-2 h-2 rounded-sm shrink-0" style={{ backgroundColor: tool.color }} />
                <span className="text-muted-foreground">{tool.name}</span>
              </div>
            ))}
            {toolLegend.length > 3 && (
              <span className="text-muted-foreground shrink-0">+{toolLegend.length - 3}</span>
            )}
          </div>
          <div className="flex items-center gap-2 font-mono text-[10px] shrink-0 text-muted-foreground">
            {totals.tools} tools
            {totals.commits > 0 && (
              <span className="flex items-center gap-1 text-[color:var(--warning)]">
                ● {totals.commits}
              </span>
            )}
            {totals.thinking > 0 && (
              <span className="flex items-center gap-1 text-purple-500">
                ● {totals.thinking}
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
