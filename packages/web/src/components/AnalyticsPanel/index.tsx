/**
 * Analytics Panel - the hero component.
 *
 * Center panel showing session metrics with big, bold numbers.
 * Collapsible to a slim bar showing key metrics.
 *
 * Related: App.tsx (parent), api/client.ts (types)
 */

import type { MetricsResponse, Event } from '../../api/client';
import { ExpandedView } from './ExpandedView';
import { CollapsedView } from './CollapsedView';

interface AnalyticsPanelProps {
  metrics: MetricsResponse | null;
  events: Event[];
  sessionStart: string | null;
  loading: boolean;
  expanded: boolean;
  onToggle: () => void;
  onScrollToEvent?: (eventId: number) => void;
}

export function AnalyticsPanel({
  metrics,
  events,
  sessionStart,
  loading,
  expanded,
  onToggle,
  onScrollToEvent,
}: AnalyticsPanelProps) {
  // No session selected
  if (!metrics && !loading) {
    return (
      <div className={`${expanded ? 'w-[calc(50%-7rem)]' : 'w-16'} bg-card border-x border-border flex flex-col transition-all duration-200`}>
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center text-muted-foreground px-4">
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
          className="p-3 border-t border-border hover:bg-accent transition-colors"
        >
          <i className={`ri-arrow-${expanded ? 'left' : 'right'}-double-line text-muted-foreground`} />
        </button>
      </div>
    );
  }

  // Loading state
  if (loading) {
    return (
      <div className={`${expanded ? 'w-[calc(50%-7rem)]' : 'w-16'} bg-card border-x border-border flex flex-col transition-all duration-200`}>
        <div className="flex-1 flex items-center justify-center">
          <i className="ri-loader-4-line animate-spin text-muted-foreground text-xl" />
        </div>
      </div>
    );
  }

  if (expanded) {
    return (
      <ExpandedView
        metrics={metrics!}
        events={events}
        sessionStart={sessionStart}
        onCollapse={onToggle}
        onScrollToEvent={onScrollToEvent}
      />
    );
  }

  return <CollapsedView metrics={metrics!} onExpand={onToggle} />;
}
