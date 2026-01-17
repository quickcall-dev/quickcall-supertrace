/**
 * Analytics Panel - the hero component.
 *
 * Center panel showing session metrics with big, bold numbers.
 * Collapsible to a slim bar showing key metrics.
 *
 * Related: App.tsx (parent), api/client.ts (types)
 */

import type { MetricsResponse, Session, IntentResponse } from '../../api/client';
import { ExpandedView } from './ExpandedView';
import { CollapsedView } from './CollapsedView';
import { SkeletonView } from './SkeletonView';
import type { SuperTraceSettings } from '../../hooks/useSettings';

interface AnalyticsPanelProps {
  metrics: MetricsResponse | null;
  loading: boolean;
  expanded: boolean;
  onToggle: () => void;
  onScrollToEvent?: (eventId: number) => void;
  hoursBack?: number;
  onTimeRangeChange?: (hours: number) => void;
  isJumpingToEvent?: boolean;
  session?: Session | null;
  width?: number;
  settings?: SuperTraceSettings;
  onIntentChanged?: (response: IntentResponse) => void;
}

export function AnalyticsPanel({
  metrics,
  loading,
  expanded,
  onToggle,
  onScrollToEvent,
  hoursBack = 0,
  onTimeRangeChange,
  isJumpingToEvent = false,
  session,
  width = 400,
  settings,
  onIntentChanged,
}: AnalyticsPanelProps) {
  const panelStyle = expanded ? { width } : { width: 64 };

  // No session selected - show minimal placeholder
  if (!metrics && !loading) {
    return (
      <div style={panelStyle} className="bg-card border-x border-border flex flex-col transition-all duration-200 shrink-0">
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

  // Loading state - show skeleton structure instead of spinner
  if (loading && !metrics) {
    if (expanded) {
      return (
        <SkeletonView
          onCollapse={onToggle}
          hoursBack={hoursBack}
          onTimeRangeChange={onTimeRangeChange}
          width={width}
        />
      );
    }
    // Collapsed loading - just show slim bar with spinner
    return (
      <div style={{ width: 64 }} className="bg-card border-x border-border flex flex-col transition-all duration-200 shrink-0">
        <div className="flex-1 flex items-center justify-center">
          <i className="ri-loader-4-line animate-spin text-xl text-muted-foreground" />
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
        session={session}
        width={width}
        settings={settings}
        onIntentChanged={onIntentChanged}
      />
    );
  }

  return <CollapsedView metrics={metrics!} onExpand={onToggle} />;
}
