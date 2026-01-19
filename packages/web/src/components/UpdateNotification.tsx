/**
 * Update notification component.
 *
 * Compact notification in bottom-left when new version available.
 * Related: hooks/useVersionCheck.ts, App.tsx
 */

import { useVersionCheck } from '../hooks/useVersionCheck';

export function UpdateNotification() {
  const {
    versionInfo,
    updateState,
    isDismissed,
    triggerUpdate,
    dismiss,
    debug,
  } = useVersionCheck();

  // Success toast - check FIRST before early return (updateAvailable may be false after update)
  if (updateState.status === 'idle' && updateState.message) {
    return (
      <div className="fixed bottom-4 left-4 z-50">
        <div className="bg-primary text-primary-foreground rounded-lg shadow-lg px-3 py-2 text-sm flex items-center gap-2">
          <i className="ri-check-line" />
          {updateState.message}
        </div>
      </div>
    );
  }

  // Don't show if no update or dismissed (unless in loading state)
  if (!versionInfo?.updateAvailable || isDismissed) {
    if (updateState.status !== 'updating' && updateState.status !== 'restarting') {
      // Debug button in dev mode
      if (debug.enabled) {
        return (
          <div className="fixed bottom-4 left-4 z-50 flex gap-2">
            <button
              onClick={debug.simulateUpdate}
              className="text-xs bg-amber-500/10 text-amber-600 hover:bg-amber-500/20 px-2 py-1 rounded"
            >
              Simulate Update
            </button>
          </div>
        );
      }
      return null;
    }
  }

  // Error state
  if (updateState.status === 'error') {
    return (
      <div className="fixed bottom-4 left-4 z-50">
        <div className="bg-card border border-border rounded-lg shadow-lg px-3 py-2 text-sm flex items-center gap-3 min-w-[280px]">
          <span className="text-destructive truncate flex-1">{updateState.message}</span>
          <button
            onClick={triggerUpdate}
            className="text-xs bg-primary text-primary-foreground px-2 py-1 rounded hover:bg-primary/90"
          >
            Retry
          </button>
          <button onClick={dismiss} className="text-muted-foreground hover:text-foreground">
            <i className="ri-close-line" />
          </button>
        </div>
      </div>
    );
  }

  // Main notification - compact inline
  return (
    <div className="fixed bottom-4 left-4 z-50">
      <div className="bg-card border border-border rounded-lg shadow-lg px-3 py-2 text-sm flex items-center gap-3 min-w-[280px]">
        {updateState.status === 'idle' ? (
          <>
            <i className="ri-download-cloud-line text-primary" />
            <span className="text-muted-foreground">v{versionInfo?.currentVersion}</span>
            <span className="text-muted-foreground">→</span>
            {versionInfo?.changelogUrl ? (
              <a
                href={versionInfo.changelogUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary font-medium hover:underline"
              >
                v{versionInfo?.latestVersion}
              </a>
            ) : (
              <span className="text-primary font-medium">v{versionInfo?.latestVersion}</span>
            )}
            <div className="flex-1" />
            <button
              onClick={triggerUpdate}
              className="bg-primary text-primary-foreground text-xs px-2.5 py-1 rounded hover:bg-primary/90"
            >
              Update
            </button>
            <button
              onClick={dismiss}
              className="text-muted-foreground hover:text-foreground"
            >
              <i className="ri-close-line" />
            </button>
            {debug.enabled && (
              <button
                onClick={debug.reset}
                className="text-xs text-amber-600 hover:text-amber-500"
                title="Debug: Reset"
              >
                <i className="ri-refresh-line" />
              </button>
            )}
          </>
        ) : (
          <>
            <i className="ri-loader-4-line animate-spin text-primary" />
            <span className="text-muted-foreground">
              {updateState.status === 'updating' ? 'Installing...' : 'Restarting...'}
            </span>
          </>
        )}
      </div>
    </div>
  );
}
