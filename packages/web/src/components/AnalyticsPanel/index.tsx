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
  onScrollToEvent?: (eventId: number) => void;
  hoursBack?: number;
  onTimeRangeChange?: (hours: number) => void;
  isJumpingToEvent?: boolean;
}

export function AnalyticsPanel({
  metrics,
  loading,
  expanded,
  onToggle,
  onScrollToEvent,
  hoursBack = 2,
  onTimeRangeChange,
  isJumpingToEvent = false,
}: AnalyticsPanelProps) {
  // No session selected - show minimal placeholder
  if (!metrics && !loading) {
    return (
      <div className={`${expanded ? 'w-[calc(50%-7rem)]' : 'w-16'} bg-card border-x border-border flex flex-col transition-all duration-200`}>
        {/* Empty - content shown in SessionView */}
        <div className="flex-1" />
        <button
          onClick={onToggle}
          className="p-3 border-t border-border hover:bg-accent transition-colors"
        >
          <i className={`ri-arrow-${expanded ? 'left' : 'right'}-double-line text-muted-foreground`} />
        </button>
      </div>
    );
  }

  // Loading state - show spinner overlay if we have metrics, full spinner otherwise
  if (loading && !metrics) {
    return (
      <div className={`${expanded ? 'w-[calc(50%-7rem)]' : 'w-16'} bg-card border-x border-border flex flex-col transition-all duration-200`}>
        <div className="flex-1 flex items-center justify-center">
          <div className="flex items-center gap-3 text-muted-foreground">
            <i className="ri-loader-4-line animate-spin text-xl" />
            {expanded && <span className="text-sm">Loading metrics...</span>}
          </div>
        </div>
      </div>
    );
  }

  if (expanded) {
    return (
      <ExpandedView
        metrics={metrics!}
        onCollapse={onToggle}
        onScrollToEvent={onScrollToEvent}
        hoursBack={hoursBack}
        onTimeRangeChange={onTimeRangeChange}
        loading={loading}
        isJumpingToEvent={isJumpingToEvent}
      />
    );
  }

  return <CollapsedView metrics={metrics!} onExpand={onToggle} />;
}
