/**
 * Skeleton loading state for Analytics Panel.
 * Shows structure while data loads - better UX than spinner.
 */

const TIME_OPTIONS = [
  { value: 1, label: '1h' },
  { value: 2, label: '2h' },
  { value: 6, label: '6h' },
  { value: 24, label: '24h' },
  { value: 0, label: 'All' },
];

interface SkeletonViewProps {
  onCollapse: () => void;
  hoursBack?: number;
  onTimeRangeChange?: (hours: number) => void;
  width?: number;
}

function SkeletonBox({ className = '', style }: { className?: string; style?: React.CSSProperties }) {
  return (
    <div className={`bg-muted/50 rounded animate-pulse ${className}`} style={style} />
  );
}

export function SkeletonView({
  onCollapse,
  hoursBack = 0,
  onTimeRangeChange,
  width = 400,
}: SkeletonViewProps) {
  return (
    <div style={{ width }} className="bg-card border-x border-border flex flex-col overflow-hidden shrink-0">
      {/* Header */}
      <div className="h-12 px-4 border-b border-border bg-card/95 backdrop-blur-sm flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3 text-sm">
          <span className="font-semibold text-foreground">Analytics</span>
          <i className="ri-loader-4-line animate-spin text-muted-foreground text-sm" />
        </div>
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-0.5 bg-muted rounded-md p-0.5">
            {TIME_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                onClick={() => onTimeRangeChange?.(opt.value)}
                className={`px-2 py-0.5 text-[10px] font-medium rounded transition-colors ${
                  hoursBack === opt.value
                    ? 'bg-background text-foreground shadow-sm'
                    : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
          <button
            onClick={onCollapse}
            className="p-1.5 hover:bg-accent rounded transition-colors"
            title="Collapse"
          >
            <i className="ri-arrow-left-double-line text-muted-foreground" />
          </button>
        </div>
      </div>

      {/* Scrollable content with skeleton */}
      <div className="flex-1 overflow-y-auto">
        {/* Intents Skeleton */}
        <div className="px-4 py-2 border-b border-border bg-muted/20">
          <div className="flex items-center gap-1.5 mb-1.5">
            <SkeletonBox className="h-3 w-14" />
            <i className="ri-sparkling-2-fill text-amber-400/30" />
            <SkeletonBox className="h-2 w-32" />
          </div>
          <SkeletonBox className="h-3 w-48" />
        </div>

        {/* Hero Metrics Skeleton */}
        <div className="px-5 py-4 border-b border-border">
          <SkeletonBox className="h-3 w-24 mb-3" />
          <div className="grid grid-cols-3 gap-2">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <div key={i} className="bg-muted/30 rounded-lg p-3">
                <SkeletonBox className="h-7 w-10 mb-2" />
                <SkeletonBox className="h-3 w-14 mb-1" />
                <SkeletonBox className="h-2 w-12" />
              </div>
            ))}
          </div>
        </div>

        {/* Tokens & Tools Chart Skeleton */}
        <div className="px-5 py-4 border-b border-border">
          <SkeletonBox className="h-3 w-36 mb-3" />
          <SkeletonBox className="h-48 w-full rounded-lg" />
          <div className="flex gap-4 mt-3">
            {[1, 2, 3, 4, 5].map((i) => (
              <SkeletonBox key={i} className="h-3 w-12" />
            ))}
          </div>
        </div>

        {/* Tool Usage Skeleton */}
        <div className="px-5 py-4 border-b border-border">
          <SkeletonBox className="h-3 w-20 mb-3" />
          <div className="space-y-2">
            {[85, 70, 55, 40].map((width, i) => (
              <div key={i} className="flex items-center gap-2">
                <SkeletonBox className="h-4 w-16" />
                <SkeletonBox className={`h-4`} style={{ width: `${width}%` } as React.CSSProperties} />
              </div>
            ))}
          </div>
        </div>

        {/* Turn Duration Skeleton */}
        <div className="px-5 py-4 border-b border-border">
          <SkeletonBox className="h-3 w-24 mb-3" />
          <SkeletonBox className="h-32 w-full rounded-lg" />
        </div>

        {/* Work Output Skeleton */}
        <div className="px-5 py-4">
          <SkeletonBox className="h-3 w-24 mb-3" />
          <div className="grid grid-cols-2 gap-2">
            {[1, 2].map((i) => (
              <div key={i} className="bg-muted/30 rounded-lg p-3">
                <SkeletonBox className="h-7 w-12 mb-2" />
                <SkeletonBox className="h-3 w-20" />
              </div>
            ))}
          </div>
          <div className="flex gap-4 mt-3">
            <SkeletonBox className="h-4 w-16" />
            <SkeletonBox className="h-4 w-16" />
          </div>
        </div>
      </div>
    </div>
  );
}
