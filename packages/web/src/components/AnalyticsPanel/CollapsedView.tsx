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
    <div className="w-16 bg-card border-x border-border flex flex-col shrink-0">
      {/* Expand button at top */}
      <button
        onClick={onExpand}
        className="p-4 border-b border-border hover:bg-accent transition-colors"
        title="Expand analytics"
      >
        <i className="ri-arrow-right-double-line text-muted-foreground text-lg" />
      </button>

      {/* Metrics */}
      <div className="flex-1 flex flex-col items-center gap-8 py-6">
        {/* Cost */}
        <div className="text-center" title={`Cost: $${cost.toFixed(2)}`}>
          <i className="ri-money-dollar-circle-line text-[color:var(--cost)] text-xl" />
          <div className="text-sm font-bold text-[color:var(--cost)] mt-1">
            ${cost >= 100 ? Math.round(cost) : cost.toFixed(0)}
          </div>
        </div>

        {/* Files */}
        <div className="text-center" title={`Files changed: ${filesChanged}`}>
          <i className="ri-file-edit-line text-[color:var(--info)] text-xl" />
          <div className="text-sm font-bold text-[color:var(--info)] mt-1">
            {filesChanged}
          </div>
        </div>

        {/* Lines */}
        <div
          className="text-center"
          title={`Net lines: ${netLines >= 0 ? '+' : ''}${netLines}`}
        >
          <i className={`ri-code-line text-xl ${netLines >= 0 ? 'text-[color:var(--success)]' : 'text-destructive'}`} />
          <div className={`text-sm font-bold mt-1 ${netLines >= 0 ? 'text-[color:var(--success)]' : 'text-destructive'}`}>
            {netLines >= 0 ? '+' : ''}{formatCompact(netLines)}
          </div>
        </div>
      </div>
    </div>
  );
}
