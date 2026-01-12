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

  const { turns, maxTokens, maxTools, totals, toolLegend } = data;

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

  const safeMaxTokens = maxTokens || 1;
  const safeMaxTools = maxTools || 1;

  const getTokenY = (value: number) => {
    const normalized = value / safeMaxTokens;
    return tokenPadding.top + tokenGraphHeight - (normalized * tokenGraphHeight);
  };

  // Build token line paths
  const inputPoints = turns.map((t, i) => `${getX(i)},${getTokenY(t.inputTokens)}`);
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

  const totalHeight = tokenChartHeight + gapHeight + toolChartHeight + xAxisHeight;

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
                stroke="var(--info)"
                strokeWidth={2}
                strokeLinecap="round"
                strokeLinejoin="round"
              />
              <path
                d={outputPath}
                fill="none"
                stroke="var(--success)"
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
                    <circle cx={x} cy={getTokenY(turn.inputTokens)} r={isHovered ? 6 : 4} fill="var(--info)" />
                    <circle cx={x} cy={getTokenY(turn.inputTokens)} r={isHovered ? 3 : 2} fill="white" />
                    <circle cx={x} cy={getTokenY(turn.outputTokens)} r={isHovered ? 6 : 4} fill="var(--success)" />
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

            {/* X-axis labels and interaction */}
            <g transform={`translate(0, ${tokenChartHeight + gapHeight + toolChartHeight})`}>
              <line x1={0} y1={0} x2={graphWidth} y2={0} stroke="currentColor" strokeOpacity={0.15} />

              {turns.map((turn, idx) => {
                const x = getX(idx);
                const isHovered = hoveredPrompt === idx;

                return (
                  <g key={idx}>
                    {/* Hover zone spanning both charts */}
                    <rect
                      x={x - 24}
                      y={-tokenChartHeight - gapHeight - toolChartHeight}
                      width={48}
                      height={tokenChartHeight + gapHeight + toolChartHeight + xAxisHeight}
                      fill="transparent"
                      className="cursor-pointer"
                      onMouseEnter={() => setHoveredPrompt(idx)}
                      onMouseLeave={() => setHoveredPrompt(null)}
                      onClick={() => onPromptClick?.(turn.responseEventId)}
                    />

                    {/* Vertical hover indicator */}
                    {isHovered && (
                      <line
                        x1={x}
                        y1={-tokenChartHeight - gapHeight - toolChartHeight}
                        x2={x}
                        y2={0}
                        stroke="currentColor"
                        strokeOpacity={0.2}
                        strokeDasharray="4,4"
                      />
                    )}

                    {/* X label */}
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
        {hoveredTurn && (
          <div
            className="absolute pointer-events-none z-20 bg-popover border border-border rounded-lg shadow-lg px-3 py-2 text-xs"
            style={{
              left: yAxisWidth + hoveredX - scrollLeft,
              top: tokenChartHeight + gapHeight + 8,
              transform: 'translateX(-50%)',
            }}
          >
            <div className="font-semibold text-foreground mb-1.5">
              Prompt {hoveredTurn.promptIndex}
            </div>
            <div className="flex items-center gap-3 mb-1.5">
              <div className="flex items-center gap-1">
                <div className="w-2 h-2 rounded-full bg-[color:var(--info)]" />
                <span className="text-muted-foreground">{formatTokens(hoveredTurn.inputTokens)}</span>
              </div>
              <div className="flex items-center gap-1">
                <div className="w-2 h-2 rounded-full bg-[color:var(--success)]" />
                <span className="text-muted-foreground">{formatTokens(hoveredTurn.outputTokens)}</span>
              </div>
            </div>
            {hoveredTurn.tools.length > 0 && (
              <div className="border-t border-border pt-1.5 space-y-1">
                {hoveredTurn.tools.slice(0, 3).map((tool) => (
                  <div key={tool.name} className="flex items-center justify-between gap-3">
                    <div className="flex items-center gap-1.5">
                      <div className="w-2 h-2 rounded-sm" style={{ backgroundColor: tool.color }} />
                      <span className="text-foreground">{tool.name}</span>
                    </div>
                    <span className="text-muted-foreground font-mono">{tool.count}×</span>
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
        )}
      </div>

      {/* Combined legend */}
      <div className="flex items-center justify-between text-xs pt-2 border-t border-border">
        <div className="flex items-center gap-4">
          {/* Token legend */}
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1">
              <div className="w-2 h-2 rounded-full bg-[color:var(--info)]" />
              <span className="text-muted-foreground">In</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="w-2 h-2 rounded-full bg-[color:var(--success)]" />
              <span className="text-muted-foreground">Out</span>
            </div>
          </div>

          <span className="text-muted-foreground/30">|</span>

          {/* Tool legend */}
          <div className="flex items-center gap-2">
            {toolLegend.slice(0, 4).map((tool) => (
              <div key={tool.name} className="flex items-center gap-1">
                <div className="w-2 h-2 rounded-sm" style={{ backgroundColor: tool.color }} />
                <span className="text-muted-foreground">{tool.name}</span>
              </div>
            ))}
            {toolLegend.length > 4 && (
              <span className="text-muted-foreground">+{toolLegend.length - 4}</span>
            )}
          </div>
        </div>

        {/* Totals */}
        <div className="flex items-center gap-3 font-mono text-[10px]">
          <span className="text-muted-foreground">
            {totals.tools} tools
          </span>
        </div>
      </div>
    </div>
  );
}
