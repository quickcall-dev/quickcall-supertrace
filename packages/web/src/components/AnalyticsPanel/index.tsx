/**
 * Analytics Panel - the hero component.
 *
 * Center panel showing session metrics with big, bold numbers.
 * Collapsible to a slim bar showing key metrics.
 *
 * Related: App.tsx (parent), api/client.ts (types)
 */

import type { MetricsResponse } from '../../api/client';
import { ExpandedView } from './ExpandedView';
import { CollapsedView } from './CollapsedView';

interface AnalyticsPanelProps {
  metrics: MetricsResponse | null;
  loading: boolean;
  expanded: boolean;
  onToggle: () => void;
}

export function AnalyticsPanel({ metrics, loading, expanded, onToggle }: AnalyticsPanelProps) {
  // No session selected
  if (!metrics && !loading) {
    return (
      <div className={`${expanded ? 'w-[calc(50%-7rem)]' : 'w-16'} bg-zinc-900 border-x border-zinc-800 flex flex-col transition-all duration-200`}>
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center text-zinc-600 px-4">
            {expanded ? (
              <>
                <i className="ri-bar-chart-2-line text-3xl mb-2 block" />
                <p className="text-sm">Select a session</p>
              </>
            ) : (
              <i className="ri-bar-chart-2-line text-xl" />
            )}
          </div>
        </div>
        <button
          onClick={onToggle}
          className="p-3 border-t border-zinc-800 hover:bg-zinc-800 transition-colors"
        >
          <i className={`ri-arrow-${expanded ? 'left' : 'right'}-double-line text-zinc-500`} />
        </button>
      </div>
    );
  }

  // Loading state
  if (loading) {
    return (
      <div className={`${expanded ? 'w-[calc(50%-7rem)]' : 'w-16'} bg-zinc-900 border-x border-zinc-800 flex flex-col transition-all duration-200`}>
        <div className="flex-1 flex items-center justify-center">
          <i className="ri-loader-4-line animate-spin text-zinc-500 text-xl" />
        </div>
      </div>
    );
  }

  if (expanded) {
    return <ExpandedView metrics={metrics!} onCollapse={onToggle} />;
  }

  return <CollapsedView metrics={metrics!} onExpand={onToggle} />;
}
