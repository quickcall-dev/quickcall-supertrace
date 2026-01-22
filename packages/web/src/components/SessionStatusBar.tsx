/**
 * Session Status Bar Component
 *
 * Displays model name, context usage progress bar, and cost
 * in a compact subtitle bar format.
 *
 * Example: Opus 4.5 • [███░░░░░] 37% • $2.06
 */

import type { ContextData } from './ContextWindowBar';

interface SessionStatusBarProps {
  model?: string | null;
  contextData?: ContextData | null;
  cost?: number | null;
  isLoading?: boolean;
}

function formatModelName(model: string | null | undefined): string {
  if (!model) return 'Unknown';

  // Common model name mappings
  const modelMappings: Record<string, string> = {
    'claude-opus-4-5-20251101': 'Opus 4.5',
    'claude-sonnet-4-20250514': 'Sonnet 4',
    'claude-3-5-sonnet-20241022': 'Sonnet 3.5',
    'claude-3-5-haiku-20241022': 'Haiku 3.5',
    'claude-3-opus-20240229': 'Opus 3',
    'claude-3-sonnet-20240229': 'Sonnet 3',
    'claude-3-haiku-20240307': 'Haiku 3',
  };

  // Check for exact match
  if (modelMappings[model]) {
    return modelMappings[model];
  }

  // Try partial matches
  if (model.includes('opus-4')) return 'Opus 4.5';
  if (model.includes('sonnet-4')) return 'Sonnet 4';
  if (model.includes('3-5-sonnet') || model.includes('sonnet-3.5')) return 'Sonnet 3.5';
  if (model.includes('3-5-haiku') || model.includes('haiku-3.5')) return 'Haiku 3.5';
  if (model.includes('opus')) return 'Opus';
  if (model.includes('sonnet')) return 'Sonnet';
  if (model.includes('haiku')) return 'Haiku';

  // Return shortened version
  return model.split('-').slice(0, 2).join(' ');
}

function getProgressBarColor(percentage: number): string {
  if (percentage < 50) return 'text-[color:var(--success)]';
  if (percentage < 75) return 'text-yellow-500';
  return 'text-red-500';
}

function renderProgressBar(percentage: number): string {
  const totalBars = 8;
  const filledBars = Math.round((percentage / 100) * totalBars);
  const emptyBars = totalBars - filledBars;

  return '█'.repeat(filledBars) + '░'.repeat(emptyBars);
}

function formatCost(cost: number | null | undefined): string {
  if (cost === null || cost === undefined) return '$0.00';
  if (cost >= 10) return `$${Math.round(cost)}`;
  if (cost >= 1) return `$${cost.toFixed(2)}`;
  return `$${cost.toFixed(3)}`;
}

// Calculate cost based on token usage
// Prices per million tokens (as of 2024)
const MODEL_PRICING: Record<string, { input: number; output: number }> = {
  'opus': { input: 15, output: 75 },
  'sonnet': { input: 3, output: 15 },
  'haiku': { input: 0.25, output: 1.25 },
};

function calculateCost(
  inputTokens: number,
  outputTokens: number,
  cacheReadTokens: number,
  cacheCreateTokens: number,
  model: string | null | undefined
): number {
  // Determine pricing tier based on model
  let pricing = MODEL_PRICING['opus']; // Default to opus pricing
  if (model) {
    const modelLower = model.toLowerCase();
    if (modelLower.includes('haiku')) {
      pricing = MODEL_PRICING['haiku'];
    } else if (modelLower.includes('sonnet')) {
      pricing = MODEL_PRICING['sonnet'];
    }
  }

  // Cache reads are 90% cheaper, cache writes are 25% more expensive
  const regularInputTokens = inputTokens - cacheReadTokens - cacheCreateTokens;
  const inputCost = (regularInputTokens / 1_000_000) * pricing.input;
  const cacheReadCost = (cacheReadTokens / 1_000_000) * pricing.input * 0.1;
  const cacheWriteCost = (cacheCreateTokens / 1_000_000) * pricing.input * 1.25;
  const outputCost = (outputTokens / 1_000_000) * pricing.output;

  return inputCost + cacheReadCost + cacheWriteCost + outputCost;
}

export function SessionStatusBar({
  model,
  contextData,
  cost,
  isLoading = false,
}: SessionStatusBarProps) {
  const percentage = contextData?.used_percentage ?? 0;
  const progressColor = getProgressBarColor(percentage);
  const progressBar = renderProgressBar(percentage);

  // Use model from contextData if not provided as prop
  const displayModel = model || contextData?.model;

  // Calculate cost from tokens if not provided
  const displayCost = cost ?? (contextData ? calculateCost(
    contextData.total_input_tokens,
    contextData.total_output_tokens,
    contextData.cache_read_tokens ?? 0,
    contextData.cache_create_tokens ?? 0,
    displayModel
  ) : 0);

  return (
    <div className="px-2 sm:px-4 py-1 border-b border-border bg-muted/30 flex items-center justify-center gap-2 text-xs text-muted-foreground font-mono">
      {isLoading ? (
        <span className="flex items-center gap-1">
          <i className="ri-loader-4-line animate-spin" />
          Loading...
        </span>
      ) : (
        <>
          {/* Model */}
          {displayModel && (
            <>
              <span className="text-foreground font-medium">{formatModelName(displayModel)}</span>
              <span className="text-muted-foreground/50">•</span>
            </>
          )}

          {/* Context Progress Bar */}
          {contextData && (
            <>
              <span className={`${progressColor} tracking-tight`} title={`Context: ${percentage.toFixed(1)}% used`}>
                [{progressBar}]
              </span>
              <span className={progressColor}>{percentage.toFixed(0)}%</span>
              <span className="text-muted-foreground/50">•</span>
            </>
          )}

          {/* Cost */}
          <span className="text-[color:var(--cost)] font-medium" title={`Estimated cost: ${formatCost(displayCost)}`}>
            {formatCost(displayCost)}
          </span>
        </>
      )}
    </div>
  );
}
