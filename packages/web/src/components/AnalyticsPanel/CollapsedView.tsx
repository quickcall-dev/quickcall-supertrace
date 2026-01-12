/**
 * Collapsed analytics view - slim bar with key metrics.
 */

import type { MetricsResponse } from '../../api/client';

interface CollapsedViewProps {
  metrics: MetricsResponse;
  onExpand: () => void;
}

function formatCompact(value: number): string {
  if (Math.abs(value) >= 1000000) return `${(value / 1000000).toFixed(1)}M`;
  if (Math.abs(value) >= 1000) return `${(value / 1000).toFixed(1)}K`;
  return value.toLocaleString();
}

export function CollapsedView({ metrics, onExpand }: CollapsedViewProps) {
  const byCategory = metrics.by_category || {};

  const cost = byCategory.tokens?.estimated_cost?.value as number ?? 0;
  const filesChanged = byCategory.tools?.files_changed?.value as number ?? 0;
  const netLines = byCategory.tools?.net_lines?.value as number ?? 0;

  return (
    <div className="w-16 bg-zinc-900 border-x border-zinc-800 flex flex-col shrink-0">
      {/* Expand button at top */}
      <button
        onClick={onExpand}
        className="p-4 border-b border-zinc-700 hover:bg-zinc-800 transition-colors"
        title="Expand analytics"
      >
        <i className="ri-arrow-right-double-line text-zinc-400 text-lg" />
      </button>

      {/* Metrics */}
      <div className="flex-1 flex flex-col items-center gap-8 py-6">
        {/* Cost */}
        <div className="text-center" title={`Cost: $${cost.toFixed(2)}`}>
          <i className="ri-money-dollar-circle-line text-amber-400 text-xl" />
          <div className="text-sm font-bold text-amber-400 mt-1">
            ${cost >= 100 ? Math.round(cost) : cost.toFixed(0)}
          </div>
        </div>

        {/* Files */}
        <div className="text-center" title={`Files changed: ${filesChanged}`}>
          <i className="ri-file-edit-line text-blue-400 text-xl" />
          <div className="text-sm font-bold text-blue-400 mt-1">
            {filesChanged}
          </div>
        </div>

        {/* Lines */}
        <div
          className="text-center"
          title={`Net lines: ${netLines >= 0 ? '+' : ''}${netLines}`}
        >
          <i className={`ri-code-line text-xl ${netLines >= 0 ? 'text-emerald-400' : 'text-red-400'}`} />
          <div className={`text-sm font-bold mt-1 ${netLines >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
            {netLines >= 0 ? '+' : ''}{formatCompact(netLines)}
          </div>
        </div>
      </div>
    </div>
  );
}
