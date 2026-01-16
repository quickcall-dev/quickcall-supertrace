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
  const commits = byCategory.interaction?.commit_count?.value as number ?? 0;

  return (
    <button
      onClick={onExpand}
      className="w-11 bg-card hover:bg-accent/50 border-x border-border flex flex-col shrink-0 transition-colors group cursor-pointer"
      title="Click to expand analytics"
    >
      {/* Header with expand icon */}
      <div
        className="flex items-center justify-center border-b border-border group-hover:bg-accent transition-colors"
        style={{ height: 'var(--header-height)' }}
      >
        <i className="ri-arrow-right-double-line text-muted-foreground group-hover:text-foreground transition-colors" />
      </div>

      {/* Compact metrics */}
      <div className="flex-1 flex flex-col items-center justify-center gap-3 py-4">
        {/* Cost */}
        <div className="text-center" title={`Cost: $${cost.toFixed(2)}`}>
          <div className="text-[11px] font-bold text-[color:var(--cost)]">
            ${cost >= 10 ? Math.round(cost) : cost.toFixed(1)}
          </div>
        </div>

        <div className="w-4 h-px bg-border" />

        {/* Files */}
        <div className="text-center" title={`${filesChanged} files changed`}>
          <div className="text-[11px] font-bold text-[color:var(--info)]">
            {filesChanged}
          </div>
          <div className="text-[8px] text-muted-foreground">files</div>
        </div>

        <div className="w-4 h-px bg-border" />

        {/* Lines */}
        <div className="text-center" title={`Net lines: ${netLines >= 0 ? '+' : ''}${netLines}`}>
          <div className={`text-[11px] font-bold ${netLines >= 0 ? 'text-[color:var(--success)]' : 'text-destructive'}`}>
            {netLines >= 0 ? '+' : ''}{formatCompact(netLines)}
          </div>
          <div className="text-[8px] text-muted-foreground">lines</div>
        </div>

        {commits > 0 && (
          <>
            <div className="w-4 h-px bg-border" />
            <div className="text-center" title={`${commits} commits`}>
              <div className="text-[11px] font-bold text-[color:var(--warning)]">
                {commits}
              </div>
              <div className="text-[8px] text-muted-foreground">commits</div>
            </div>
          </>
        )}
      </div>
    </button>
  );
}
