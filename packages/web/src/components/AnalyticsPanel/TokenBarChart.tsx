/**
 * Token Line Chart - shows input/output tokens for each prompt/response pair.
 *
 * Horizontal scrolling line chart with markers and Y-axis scale.
 * Clickable to scroll to message.
 */

import type { Event } from '../../api/client';

interface TokenBarChartProps {
  events: Event[];
  onBarClick?: (eventId: number) => void;
}

interface TokenPair {
  promptEventId: number;
  responseEventId: number;
  promptIndex: number;
  inputTokens: number;
  outputTokens: number;
  timestamp: string;
}

export function TokenBarChart({ events, onBarClick }: TokenBarChartProps) {
  // Extract prompt/response pairs with token data
  const pairs: TokenPair[] = [];
  let promptIndex = 0;

  for (let i = 0; i < events.length; i++) {
    const event = events[i];

    if (event.event_type === 'user_prompt') {
      promptIndex++;
      // Find the next assistant_stop event
      for (let j = i + 1; j < events.length; j++) {
        const responseEvent = events[j];
        if (responseEvent.event_type === 'assistant_stop') {
          const tokenUsage = responseEvent.data?.token_usage as {
            input_tokens?: number;
            output_tokens?: number;
          } | null;

          if (tokenUsage) {
            pairs.push({
              promptEventId: event.id,
              responseEventId: responseEvent.id,
              promptIndex,
              inputTokens: tokenUsage.input_tokens || 0,
              outputTokens: tokenUsage.output_tokens || 0,
              timestamp: event.timestamp,
            });
          }
          break;
        }
        // If we hit another user_prompt, stop looking
        if (events[j].event_type === 'user_prompt') break;
      }
    }
  }

  if (pairs.length === 0) {
    return (
      <div className="text-center py-4 text-muted-foreground text-sm">
        No token usage data
      </div>
    );
  }

  // Find max for scaling
  const maxTokens = Math.max(
    ...pairs.flatMap(p => [p.inputTokens, p.outputTokens])
  );

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

  const chartHeight = 100;
  const yAxisWidth = 32;
  const graphAreaWidth = Math.max(pairs.length * 48, 180);
  const chartWidth = graphAreaWidth + yAxisWidth;
  const padding = { left: yAxisWidth, right: 8, top: 12, bottom: 24 };
  const graphHeight = chartHeight - padding.top - padding.bottom;
  const graphWidth = graphAreaWidth - padding.right;

  // Calculate points for each line
  const getY = (value: number) => {
    const normalized = maxTokens > 0 ? value / maxTokens : 0;
    return padding.top + graphHeight - (normalized * graphHeight);
  };

  const getX = (index: number) => {
    if (pairs.length === 1) return padding.left + graphWidth / 2;
    return padding.left + (index / (pairs.length - 1)) * graphWidth;
  };

  // Build path strings
  const inputPoints = pairs.map((p, i) => `${getX(i)},${getY(p.inputTokens)}`);
  const outputPoints = pairs.map((p, i) => `${getX(i)},${getY(p.outputTokens)}`);

  const inputPath = `M ${inputPoints.join(' L ')}`;
  const outputPath = `M ${outputPoints.join(' L ')}`;

  // Area fill paths (for subtle gradient effect)
  const inputAreaPath = `${inputPath} L ${getX(pairs.length - 1)},${chartHeight - padding.bottom} L ${getX(0)},${chartHeight - padding.bottom} Z`;
  const outputAreaPath = `${outputPath} L ${getX(pairs.length - 1)},${chartHeight - padding.bottom} L ${getX(0)},${chartHeight - padding.bottom} Z`;

  // Y-axis scale ticks
  const yTicks = [0, 0.5, 1].map(ratio => ({
    value: Math.round(maxTokens * ratio),
    y: getY(maxTokens * ratio),
  }));

  return (
    <div className="space-y-2">
      {/* Chart container */}
      <div className="overflow-x-auto">
        <svg
          width={chartWidth}
          height={chartHeight}
          className="block"
        >
          {/* Y-axis labels */}
          {yTicks.map((tick, idx) => (
            <g key={idx}>
              <text
                x={yAxisWidth - 4}
                y={tick.y + 3}
                textAnchor="end"
                className="text-[9px] fill-muted-foreground"
              >
                {formatTokensShort(tick.value)}
              </text>
              {/* Horizontal grid line */}
              <line
                x1={padding.left}
                y1={tick.y}
                x2={chartWidth - padding.right}
                y2={tick.y}
                stroke="currentColor"
                strokeOpacity={idx === 0 ? 0.15 : 0.08}
                strokeDasharray={idx === 0 ? "0" : "2,2"}
              />
            </g>
          ))}

          {/* Area fills */}
          <path
            d={inputAreaPath}
            fill="var(--info)"
            fillOpacity={0.08}
          />
          <path
            d={outputAreaPath}
            fill="var(--success)"
            fillOpacity={0.08}
          />

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

          {/* Markers and labels */}
          {pairs.map((pair, idx) => {
            const x = getX(idx);
            const inputY = getY(pair.inputTokens);
            const outputY = getY(pair.outputTokens);

            return (
              <g key={idx}>
                {/* Clickable area */}
                <rect
                  x={x - 20}
                  y={padding.top}
                  width={40}
                  height={graphHeight + padding.bottom}
                  fill="transparent"
                  className="cursor-pointer hover:fill-accent/20 transition-colors"
                  onClick={() => onBarClick?.(pair.responseEventId)}
                >
                  <title>Prompt {pair.promptIndex}: {formatTokens(pair.inputTokens)} in / {formatTokens(pair.outputTokens)} out</title>
                </rect>

                {/* Vertical hover line indicator */}
                <line
                  x1={x}
                  y1={padding.top}
                  x2={x}
                  y2={chartHeight - padding.bottom}
                  stroke="currentColor"
                  strokeOpacity={0}
                  className="pointer-events-none"
                />

                {/* Input marker */}
                <circle
                  cx={x}
                  cy={inputY}
                  r={5}
                  fill="var(--info)"
                  className="pointer-events-none"
                />
                <circle
                  cx={x}
                  cy={inputY}
                  r={2}
                  fill="white"
                  className="pointer-events-none"
                />

                {/* Output marker */}
                <circle
                  cx={x}
                  cy={outputY}
                  r={5}
                  fill="var(--success)"
                  className="pointer-events-none"
                />
                <circle
                  cx={x}
                  cy={outputY}
                  r={2}
                  fill="white"
                  className="pointer-events-none"
                />

                {/* X-axis label */}
                <text
                  x={x}
                  y={chartHeight - 6}
                  textAnchor="middle"
                  className="text-[9px] fill-muted-foreground pointer-events-none"
                >
                  {pair.promptIndex}
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      {/* Legend and Totals row */}
      <div className="flex items-center justify-between text-xs pt-1 border-t border-border">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5">
            <div className="w-3 h-0.5 bg-[color:var(--info)] rounded" />
            <div className="w-2 h-2 rounded-full bg-[color:var(--info)]" />
            <span className="text-muted-foreground">Input</span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="w-3 h-0.5 bg-[color:var(--success)] rounded" />
            <div className="w-2 h-2 rounded-full bg-[color:var(--success)]" />
            <span className="text-muted-foreground">Output</span>
          </div>
        </div>
        <div className="flex items-center gap-2 font-mono text-[10px]">
          <span className="text-[color:var(--info)]">
            {formatTokens(pairs.reduce((sum, p) => sum + p.inputTokens, 0))}
          </span>
          <span className="text-muted-foreground">/</span>
          <span className="text-[color:var(--success)]">
            {formatTokens(pairs.reduce((sum, p) => sum + p.outputTokens, 0))}
          </span>
        </div>
      </div>
    </div>
  );
}
