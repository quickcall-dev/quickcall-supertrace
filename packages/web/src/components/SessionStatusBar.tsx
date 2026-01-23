/**
 * Session Status Bar Component
 *
 * Minimal status indicator showing model and context usage.
 * Right-aligned to connect with the header actions visually.
 */

import type { ContextData } from './ContextWindowBar';

interface SessionStatusBarProps {
  model?: string | null;
  contextData?: ContextData | null;
  isLoading?: boolean;
}

function formatModelName(model: string | null | undefined): string {
  if (!model) return '';

  const modelMappings: Record<string, string> = {
    'claude-opus-4-5-20251101': 'Opus 4.5',
    'claude-sonnet-4-5-20250929': 'Sonnet 4.5',
    'claude-sonnet-4-20250514': 'Sonnet 4',
    'claude-3-5-sonnet-20241022': 'Sonnet 3.5',
    'claude-3-5-haiku-20241022': 'Haiku 3.5',
    'claude-3-opus-20240229': 'Opus 3',
    'claude-3-sonnet-20240229': 'Sonnet 3',
    'claude-3-haiku-20240307': 'Haiku 3',
  };

  if (modelMappings[model]) return modelMappings[model];

  if (model.includes('opus-4-5') || model.includes('opus-4')) return 'Opus 4.5';
  if (model.includes('sonnet-4-5')) return 'Sonnet 4.5';
  if (model.includes('sonnet-4')) return 'Sonnet 4';
  if (model.includes('3-5-sonnet') || model.includes('sonnet-3.5')) return 'Sonnet 3.5';
  if (model.includes('3-5-haiku') || model.includes('haiku-3.5')) return 'Haiku 3.5';
  if (model.includes('opus')) return 'Opus';
  if (model.includes('sonnet')) return 'Sonnet';
  if (model.includes('haiku')) return 'Haiku';

  return model.split('-').slice(0, 2).join(' ');
}

function getBarColor(percentage: number): string {
  if (percentage < 50) return 'bg-emerald-500';
  if (percentage < 75) return 'bg-amber-500';
  return 'bg-rose-500';
}

function getPercentColor(percentage: number): string {
  if (percentage < 50) return 'text-emerald-600 dark:text-emerald-400';
  if (percentage < 75) return 'text-amber-600 dark:text-amber-400';
  return 'text-rose-600 dark:text-rose-400';
}

export function SessionStatusBar({
  model,
  contextData,
  isLoading = false,
}: SessionStatusBarProps) {
  const percentage = contextData?.used_percentage ?? 0;
  const displayModel = model || contextData?.model;
  const modelName = formatModelName(displayModel);

  // Don't render if no data
  if (!isLoading && !displayModel && !contextData) {
    return null;
  }

  return (
    <div className="h-7 px-4 border-b border-border/50 bg-muted/10 flex items-center justify-end">
      {isLoading ? (
        <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
          <i className="ri-loader-4-line animate-spin" />
        </span>
      ) : (
        <div className="flex items-center gap-4 text-xs">
          {/* Model */}
          {modelName && (
            <span className="text-muted-foreground">
              <span className="text-foreground/80 font-medium">{modelName}</span>
            </span>
          )}

          {/* Context indicator */}
          {contextData && (
            <div className="flex items-center gap-2">
              <div className="w-16 h-1 bg-border rounded-full overflow-hidden">
                <div
                  className={`h-full transition-all duration-500 ease-out ${getBarColor(percentage)}`}
                  style={{ width: `${Math.min(100, percentage)}%` }}
                />
              </div>
              <span className={`font-mono text-[11px] tabular-nums ${getPercentColor(percentage)}`}>
                {percentage.toFixed(0)}%
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
