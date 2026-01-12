/**
 * Token Bar Chart - shows input/output tokens for each prompt/response pair.
 *
 * Horizontal scrolling chart with vertical bars for each prompt.
 * Double bar (input/output) per prompt. Clickable to scroll to message.
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
    if (n >= 1000) return `${(n / 1000).toFixed(1)}K`;
    return n.toString();
  };

  const chartHeight = 80; // pixels

  return (
    <div className="space-y-2">
      {/* Horizontal scrolling chart */}
      <div className="overflow-x-auto pb-2">
        <div
          className="flex items-end gap-1"
          style={{ minWidth: `${Math.max(pairs.length * 32, 100)}px` }}
        >
          {pairs.map((pair, idx) => {
            const inputHeight = maxTokens > 0 ? (pair.inputTokens / maxTokens) * chartHeight : 0;
            const outputHeight = maxTokens > 0 ? (pair.outputTokens / maxTokens) * chartHeight : 0;

            return (
              <button
                key={idx}
                onClick={() => onBarClick?.(pair.responseEventId)}
                className="group flex flex-col items-center gap-1 hover:bg-accent/30 rounded px-0.5 py-1 transition-colors"
                title={`Prompt ${pair.promptIndex}: ${formatTokens(pair.inputTokens)} in / ${formatTokens(pair.outputTokens)} out`}
              >
                {/* Bars */}
                <div className="flex items-end gap-0.5" style={{ height: `${chartHeight}px` }}>
                  {/* Input bar */}
                  <div
                    className="w-2.5 bg-[color:var(--info)] rounded-t transition-all group-hover:opacity-80"
                    style={{ height: `${Math.max(inputHeight, 2)}px` }}
                  />
                  {/* Output bar */}
                  <div
                    className="w-2.5 bg-[color:var(--success)] rounded-t transition-all group-hover:opacity-80"
                    style={{ height: `${Math.max(outputHeight, 2)}px` }}
                  />
                </div>

                {/* Prompt number */}
                <span className="text-[9px] text-muted-foreground">
                  {pair.promptIndex}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Legend and Totals row */}
      <div className="flex items-center justify-between text-xs pt-1 border-t border-border">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1">
            <div className="w-2.5 h-2.5 bg-[color:var(--info)] rounded" />
            <span className="text-muted-foreground">In</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-2.5 h-2.5 bg-[color:var(--success)] rounded" />
            <span className="text-muted-foreground">Out</span>
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
