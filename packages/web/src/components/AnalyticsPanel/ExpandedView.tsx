/**
 * Expanded analytics view with big numbers and full breakdown.
 */

import type { MetricsResponse, MetricFormat } from '../../api/client';

interface ExpandedViewProps {
  metrics: MetricsResponse;
  onCollapse: () => void;
}

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

export function ExpandedView({ metrics, onCollapse }: ExpandedViewProps) {
  const byCategory = metrics.by_category || {};

  // Extract key metrics
  const cost = byCategory.tokens?.estimated_cost?.value as number ?? 0;
  const inputCost = byCategory.tokens?.input_cost?.value as number ?? 0;
  const outputCost = byCategory.tokens?.output_cost?.value as number ?? 0;
  const cacheSavings = byCategory.tokens?.cache_savings?.value as number ?? 0;

  const filesChanged = byCategory.tools?.files_changed?.value as number ?? 0;
  const linesAdded = byCategory.tools?.lines_added?.value as number ?? 0;
  const linesRemoved = byCategory.tools?.lines_removed?.value as number ?? 0;
  const netLines = byCategory.tools?.net_lines?.value as number ?? 0;
  const edits = byCategory.tools?.edit_count?.value as number ?? 0;
  const filesRead = byCategory.tools?.files_read?.value as number ?? 0;

  const duration = byCategory.timing?.session_duration?.value as number | null;

  const prompts = byCategory.interaction?.prompt_count?.value as number ?? 0;
  const editsPerPrompt = byCategory.interaction?.edits_per_prompt?.value as number ?? 0;
  const completionRate = byCategory.interaction?.completion_rate?.value as number ?? 0;

  const toolDistribution = byCategory.tools?.tool_distribution?.value as Record<string, number> ?? {};

  return (
    <div className="w-[calc(50%-7rem)] bg-zinc-900 border-x border-zinc-800 flex flex-col overflow-hidden shrink-0">
      {/* Header */}
      <div className="px-5 py-3 border-b border-zinc-700 flex items-center justify-between">
        <span className="text-sm font-semibold text-zinc-200 uppercase tracking-wider">Analytics</span>
        <button
          onClick={onCollapse}
          className="p-1.5 hover:bg-zinc-700 rounded transition-colors"
          title="Collapse"
        >
          <i className="ri-arrow-left-double-line text-zinc-400" />
        </button>
      </div>

      {/* Scrollable content */}
      <div className="flex-1 overflow-y-auto">
        {/* Hero: Cost */}
        <div className="px-5 py-8 border-b border-zinc-700 bg-gradient-to-b from-zinc-800/80 to-transparent">
          <div className="text-center">
            <div className="text-5xl font-bold text-amber-400 mb-2">
              ${cost.toFixed(2)}
            </div>
            <div className="text-sm text-zinc-400 uppercase tracking-wider font-medium">Session Cost</div>
          </div>

          {/* Cost breakdown */}
          <div className="mt-6 grid grid-cols-2 gap-4 text-center">
            <div className="bg-zinc-800/50 rounded-lg py-3 px-4">
              <div className="text-lg font-semibold text-zinc-100">${inputCost.toFixed(2)}</div>
              <div className="text-xs text-zinc-400 mt-1">Input</div>
            </div>
            <div className="bg-zinc-800/50 rounded-lg py-3 px-4">
              <div className="text-lg font-semibold text-zinc-100">${outputCost.toFixed(2)}</div>
              <div className="text-xs text-zinc-400 mt-1">Output</div>
            </div>
          </div>

          {cacheSavings > 0 && (
            <div className="mt-4 text-center">
              <span className="text-sm text-emerald-400 font-medium">
                <i className="ri-discount-percent-line mr-1" />
                ${cacheSavings.toFixed(2)} saved with cache
              </span>
            </div>
          )}
        </div>

        {/* Work Output */}
        <div className="px-5 py-5 border-b border-zinc-700">
          <div className="text-xs text-zinc-400 uppercase tracking-wider mb-4 font-semibold">Work Output</div>

          <div className="grid grid-cols-2 gap-4">
            <div className="bg-zinc-800/50 rounded-lg p-4">
              <div className="text-3xl font-bold text-blue-400">{filesChanged}</div>
              <div className="text-sm text-zinc-300 mt-1">Files changed</div>
            </div>
            <div className="bg-zinc-800/50 rounded-lg p-4">
              <div className={`text-3xl font-bold ${netLines >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                {formatWithSign(netLines)}
              </div>
              <div className="text-sm text-zinc-300 mt-1">Net lines</div>
            </div>
          </div>

          <div className="mt-4 flex items-center gap-6 text-base">
            <div className="flex items-center gap-2">
              <i className="ri-add-line text-emerald-400" />
              <span className="text-zinc-200 font-medium">{linesAdded.toLocaleString()}</span>
            </div>
            <div className="flex items-center gap-2">
              <i className="ri-subtract-line text-red-400" />
              <span className="text-zinc-200 font-medium">{linesRemoved.toLocaleString()}</span>
            </div>
          </div>

          <div className="mt-4 flex items-center gap-6 text-sm text-zinc-400">
            <span><strong className="text-zinc-200">{edits}</strong> edits</span>
            <span><strong className="text-zinc-200">{filesRead}</strong> files read</span>
          </div>
        </div>

        {/* Efficiency */}
        <div className="px-5 py-5 border-b border-zinc-700">
          <div className="text-xs text-zinc-400 uppercase tracking-wider mb-4 font-semibold">Efficiency</div>

          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-sm text-zinc-300">Prompts</span>
              <span className="text-base font-semibold text-zinc-100">{prompts}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-zinc-300">Edits per prompt</span>
              <span className="text-base font-semibold text-zinc-100">{editsPerPrompt}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-zinc-300">Completion rate</span>
              <span className="text-base font-semibold text-zinc-100">{completionRate}%</span>
            </div>
            {duration !== null && (
              <div className="flex items-center justify-between">
                <span className="text-sm text-zinc-300">Duration</span>
                <span className="text-base font-semibold text-zinc-100">
                  {formatValue(duration, 'duration')}
                </span>
              </div>
            )}
          </div>
        </div>

        {/* Tool Distribution */}
        {Object.keys(toolDistribution).length > 0 && (
          <div className="px-5 py-5">
            <div className="text-xs text-zinc-400 uppercase tracking-wider mb-4 font-semibold">Tools Used</div>
            <div className="space-y-3">
              {Object.entries(toolDistribution).slice(0, 8).map(([tool, count]) => (
                <div key={tool} className="flex items-center justify-between">
                  <span className="text-sm text-zinc-300 truncate max-w-[180px]">{tool}</span>
                  <span className="text-sm font-mono text-zinc-100 font-medium">{count}</span>
                </div>
              ))}
              {Object.keys(toolDistribution).length > 8 && (
                <div className="text-sm text-zinc-500">
                  +{Object.keys(toolDistribution).length - 8} more
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
