/**
 * Context Window Bar Component
 *
 * Battery-style progress bar showing context window usage.
 * Color coding: green (<50%), yellow (50-75%), red (>75%).
 * Shows tooltip with detailed token breakdown on hover.
 *
 * Related: api/client.ts (getSessionContext), hooks/useWebSocket.ts (real-time updates)
 */

import { useState, useEffect, useCallback } from 'react';

export interface ContextData {
  used_percentage: number;
  remaining_percentage: number;
  context_window_size: number;
  total_input_tokens: number;
  total_output_tokens: number;
  timestamp?: string;
}

interface ContextWindowBarProps {
  sessionId: string;
  contextData?: ContextData | null;
  onRefresh?: () => void;
  isLoading?: boolean;
}

function formatNumber(num: number): string {
  if (num >= 1000000) {
    return `${(num / 1000000).toFixed(1)}M`;
  }
  if (num >= 1000) {
    return `${(num / 1000).toFixed(1)}K`;
  }
  return num.toString();
}

function getColorClasses(percentage: number): {
  bar: string;
  text: string;
  bg: string;
  icon: string;
} {
  if (percentage < 50) {
    return {
      bar: 'bg-[color:var(--success)]',
      text: 'text-[color:var(--success)]',
      bg: 'bg-[color:var(--success)]/10',
      icon: 'ri-battery-2-line',
    };
  }
  if (percentage < 75) {
    return {
      bar: 'bg-yellow-500',
      text: 'text-yellow-500',
      bg: 'bg-yellow-500/10',
      icon: 'ri-battery-low-line',
    };
  }
  return {
    bar: 'bg-red-500',
    text: 'text-red-500',
    bg: 'bg-red-500/10',
    icon: 'ri-battery-fill',
  };
}

export function ContextWindowBar({
  sessionId,
  contextData,
  onRefresh,
  isLoading = false,
}: ContextWindowBarProps) {
  const [showTooltip, setShowTooltip] = useState(false);

  // Don't render if no context data
  if (!contextData) {
    return null;
  }

  const {
    used_percentage,
    remaining_percentage,
    context_window_size,
    total_input_tokens,
    total_output_tokens,
  } = contextData;

  const colors = getColorClasses(used_percentage);
  const totalUsedTokens = total_input_tokens + total_output_tokens;

  return (
    <div
      className="relative flex items-center gap-1.5"
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
    >
      {/* Battery icon */}
      <i className={`${colors.icon} ${colors.text} text-sm`} />

      {/* Battery bar container */}
      <div className="relative w-16 h-4 bg-muted rounded border border-border overflow-hidden">
        {/* Progress fill */}
        <div
          className={`absolute inset-y-0 left-0 ${colors.bar} transition-all duration-500 ease-out`}
          style={{ width: `${Math.min(used_percentage, 100)}%` }}
        />
        {/* Battery nub (right edge) */}
        <div className="absolute right-0 top-1/2 -translate-y-1/2 translate-x-[2px] w-[3px] h-2 bg-border rounded-r-sm" />
      </div>

      {/* Percentage text */}
      <span className={`text-xs font-medium ${colors.text} min-w-[2.5rem] tabular-nums`}>
        {used_percentage.toFixed(0)}%
      </span>

      {/* Tooltip */}
      {showTooltip && (
        <div className="absolute top-full left-0 mt-2 z-50 w-64 p-3 bg-popover border border-border rounded-lg shadow-lg">
          <div className="space-y-2.5">
            {/* Header */}
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-foreground">Context Window Usage</span>
              <span className={`text-xs font-bold ${colors.text}`}>
                {used_percentage.toFixed(1)}% used
              </span>
            </div>

            {/* Progress bar (larger version) */}
            <div className="h-2 bg-muted rounded-full overflow-hidden">
              <div
                className={`h-full ${colors.bar} transition-all duration-300`}
                style={{ width: `${Math.min(used_percentage, 100)}%` }}
              />
            </div>

            {/* Token breakdown */}
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div className="space-y-1">
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Input tokens:</span>
                  <span className="font-mono text-foreground">{formatNumber(total_input_tokens)}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Output tokens:</span>
                  <span className="font-mono text-foreground">{formatNumber(total_output_tokens)}</span>
                </div>
              </div>
              <div className="space-y-1">
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Total used:</span>
                  <span className="font-mono text-foreground">{formatNumber(totalUsedTokens)}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Window size:</span>
                  <span className="font-mono text-foreground">{formatNumber(context_window_size)}</span>
                </div>
              </div>
            </div>

            {/* Remaining capacity */}
            <div className="pt-2 border-t border-border">
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">Remaining capacity:</span>
                <span className={`font-semibold ${colors.text}`}>
                  {formatNumber(context_window_size - totalUsedTokens)} tokens ({remaining_percentage.toFixed(1)}%)
                </span>
              </div>
            </div>

            {/* Warning for high usage */}
            {used_percentage >= 75 && (
              <div className="flex items-center gap-1.5 text-xs text-red-500 bg-red-500/10 p-2 rounded">
                <i className="ri-alert-line" />
                <span>Context window nearly full. Consider summarizing or starting a new session.</span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Loading indicator */}
      {isLoading && (
        <i className="ri-loader-4-line animate-spin text-muted-foreground text-xs" />
      )}
    </div>
  );
}
