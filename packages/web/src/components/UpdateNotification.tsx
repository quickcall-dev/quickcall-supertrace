/**
 * Update notification component.
 *
 * Displays a notification when a new version is available.
 * Fixed position in bottom-right corner with update/dismiss actions.
 * Related: hooks/useVersionCheck.ts, App.tsx
 */

import { useVersionCheck } from '../hooks/useVersionCheck';

export function UpdateNotification() {
  const {
    versionInfo,
    updateState,
    isDismissed,
    triggerUpdate,
    dismiss
  } = useVersionCheck();

  // Don't show if no update or dismissed
  if (!versionInfo?.updateAvailable || isDismissed) {
    // Still show during update/restart states
    if (updateState.status !== 'updating' && updateState.status !== 'restarting') {
      return null;
    }
  }

  // Show success message briefly
  if (updateState.status === 'idle' && updateState.message) {
    return (
      <div className="fixed bottom-4 right-4 z-50 animate-in slide-in-from-bottom-4 fade-in duration-300">
        <div className="bg-green-500/90 text-white px-4 py-3 rounded-lg shadow-lg backdrop-blur-sm">
          <div className="flex items-center gap-2">
            <i className="ri-check-line text-lg" />
            <span>{updateState.message}</span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed bottom-4 right-4 z-50 animate-in slide-in-from-bottom-4 fade-in duration-300">
      <div className="bg-card border border-border rounded-lg shadow-lg p-4 max-w-sm backdrop-blur-sm">
        {/* Header */}
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
              <i className="ri-download-line text-primary" />
            </div>
            <div>
              <h4 className="font-medium text-foreground">Update Available</h4>
              <p className="text-sm text-muted-foreground">
                v{versionInfo?.currentVersion} → v{versionInfo?.latestVersion}
              </p>
            </div>
          </div>

          {updateState.status === 'idle' && (
            <button
              onClick={dismiss}
              className="text-muted-foreground hover:text-foreground transition-colors"
              aria-label="Dismiss"
            >
              <i className="ri-close-line text-lg" />
            </button>
          )}
        </div>

        {/* Status Message */}
        {updateState.message && updateState.status === 'error' && (
          <div className="mt-3 text-sm text-red-500 bg-red-500/10 px-3 py-2 rounded">
            {updateState.message}
          </div>
        )}

        {/* Action Buttons */}
        <div className="mt-4 flex items-center gap-2">
          {updateState.status === 'idle' && (
            <>
              <button
                onClick={triggerUpdate}
                className="flex-1 bg-primary text-primary-foreground px-4 py-2 rounded-md
                         hover:bg-primary/90 transition-colors flex items-center justify-center gap-2"
              >
                <i className="ri-restart-line" />
                Update & Restart
              </button>

              {versionInfo?.changelogUrl && (
                <a
                  href={versionInfo.changelogUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-3 py-2 text-muted-foreground hover:text-foreground transition-colors"
                  title="View changelog"
                >
                  <i className="ri-file-list-line text-lg" />
                </a>
              )}
            </>
          )}

          {updateState.status === 'updating' && (
            <div className="flex-1 flex items-center justify-center gap-2 py-2 text-muted-foreground">
              <i className="ri-loader-4-line animate-spin" />
              <span>Installing update...</span>
            </div>
          )}

          {updateState.status === 'restarting' && (
            <div className="flex-1 flex items-center justify-center gap-2 py-2 text-muted-foreground">
              <i className="ri-loader-4-line animate-spin" />
              <span>Restarting server...</span>
            </div>
          )}

          {updateState.status === 'error' && (
            <button
              onClick={triggerUpdate}
              className="flex-1 bg-primary text-primary-foreground px-4 py-2 rounded-md
                       hover:bg-primary/90 transition-colors"
            >
              Retry
            </button>
          )}
        </div>

        {/* Install method hint for source installs */}
        {versionInfo?.installMethod === 'source' && (
          <p className="mt-3 text-xs text-muted-foreground">
            Running from source. Update with: <code className="bg-muted px-1 rounded">git pull</code>
          </p>
        )}
      </div>
    </div>
  );
}
