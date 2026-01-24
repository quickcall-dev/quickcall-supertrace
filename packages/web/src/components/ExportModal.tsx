/**
 * Export modal component.
 *
 * Modal for exporting session dashboards as HTML.
 * Includes export level dropdown and progress states.
 *
 * Export functions are provided by Agent 3 (exportHelpers.ts).
 */

import { useState } from 'react';

export type ExportLevel = 'summary' | 'full' | 'archive';

type ExportState = 'idle' | 'loading' | 'success' | 'error';

interface ExportModalProps {
  sessionId: string;
  sessionTitle: string;
  isOpen: boolean;
  onClose: () => void;
  onExportHTML?: (sessionId: string, level: ExportLevel) => Promise<void>;
}

const EXPORT_LEVELS: { value: ExportLevel; label: string; description: string }[] = [
  { value: 'summary', label: 'Summary', description: 'Key metrics & first 20 events (~50KB)' },
  { value: 'full', label: 'Full', description: 'All metrics & up to 1000 events (~500KB)' },
  { value: 'archive', label: 'Archive', description: 'Complete backup with all data (~5MB)' },
];

export function ExportModal({
  sessionId,
  sessionTitle,
  isOpen,
  onClose,
  onExportHTML,
}: ExportModalProps) {
  const [level, setLevel] = useState<ExportLevel>('summary');
  const [state, setState] = useState<ExportState>('idle');
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleExport = async () => {
    setState('loading');
    setError(null);

    try {
      if (onExportHTML) {
        await onExportHTML(sessionId, level);
      } else {
        // Stub for now
        await new Promise(resolve => setTimeout(resolve, 1000));
        console.log(`[ExportModal] HTML export stub: ${sessionId}, level: ${level}`);
      }
      setState('success');
      // Auto-close after success
      setTimeout(() => {
        setState('idle');
        onClose();
      }, 1500);
    } catch (err) {
      setState('error');
      setError(err instanceof Error ? err.message : 'Export failed');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape' && state !== 'loading') {
      onClose();
    }
  };

  const handleRetry = () => {
    setState('idle');
    setError(null);
  };

  return (
    <div
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-[200]"
      onKeyDown={handleKeyDown}
      role="dialog"
      aria-modal="true"
      aria-labelledby="export-dialog-title"
    >
      <div className="bg-card border border-border rounded-xl shadow-2xl max-w-md w-full mx-4 overflow-hidden">
        {/* Header */}
        <div className="px-5 py-4 flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center shrink-0">
            <i className="ri-share-line text-primary text-xl"></i>
          </div>
          <div className="min-w-0">
            <h3 id="export-dialog-title" className="text-lg font-semibold text-foreground">
              Export Dashboard
            </h3>
            <p className="text-xs text-muted-foreground truncate" title={sessionTitle}>
              {sessionTitle.length > 40 ? sessionTitle.slice(0, 40) + '...' : sessionTitle}
            </p>
          </div>
        </div>

        {/* Body */}
        <div className="px-5 pb-4 space-y-4">
          {/* Success State */}
          {state === 'success' && (
            <div className="py-8 text-center">
              <div className="w-12 h-12 mx-auto mb-3 bg-[color:var(--success)]/10 rounded-full flex items-center justify-center">
                <i className="ri-check-line text-[color:var(--success)] text-2xl"></i>
              </div>
              <p className="text-foreground font-medium">Export Complete</p>
              <p className="text-sm text-muted-foreground mt-1">Your file is downloading...</p>
            </div>
          )}

          {/* Error State */}
          {state === 'error' && (
            <div className="py-6">
              <div className="bg-destructive/10 text-destructive text-sm px-4 py-3 rounded-lg flex items-start gap-3">
                <i className="ri-error-warning-line shrink-0 mt-0.5"></i>
                <div className="flex-1">
                  <p className="font-medium">Export Failed</p>
                  <p className="text-xs mt-1 opacity-80">{error || 'Unknown error occurred'}</p>
                </div>
              </div>
              <button
                onClick={handleRetry}
                className="mt-3 w-full py-2 text-sm font-medium rounded-lg bg-muted hover:bg-accent transition-colors text-foreground"
              >
                Try Again
              </button>
            </div>
          )}

          {/* Loading State */}
          {state === 'loading' && (
            <div className="py-8 text-center">
              <div className="w-12 h-12 mx-auto mb-3 bg-primary/10 rounded-full flex items-center justify-center">
                <i className="ri-loader-4-line text-primary text-2xl animate-spin"></i>
              </div>
              <p className="text-foreground font-medium">Generating HTML...</p>
              <p className="text-sm text-muted-foreground mt-1">This may take a moment</p>
            </div>
          )}

          {/* Idle State - Selection UI */}
          {state === 'idle' && (
            <>
              {/* Export Level */}
              <div>
                <label className="block text-sm font-medium text-foreground mb-2">
                  Export Level
                </label>
                <select
                  value={level}
                  onChange={(e) => setLevel(e.target.value as ExportLevel)}
                  className="w-full px-3 py-2 bg-muted border border-border rounded-lg text-foreground text-sm focus:outline-none focus:ring-1 focus:ring-ring"
                >
                  {EXPORT_LEVELS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label} - {opt.description}
                    </option>
                  ))}
                </select>
              </div>

              {/* Info */}
              <div className="bg-muted/50 text-muted-foreground text-xs px-3 py-2.5 rounded-lg flex items-start gap-2">
                <i className="ri-information-line shrink-0 mt-0.5"></i>
                <span>
                  HTML exports are self-contained files with inline CSS and charts. Works offline with dark/light mode.
                </span>
              </div>
            </>
          )}
        </div>

        {/* Footer */}
        {(state === 'idle' || state === 'loading') && (
          <div className="px-5 py-4 border-t border-border flex justify-end gap-3 bg-muted/30">
            <button
              onClick={onClose}
              disabled={state === 'loading'}
              className="px-4 py-2 text-sm font-medium rounded-lg hover:bg-accent transition-colors text-foreground disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              onClick={handleExport}
              disabled={state === 'loading'}
              className="px-4 py-2 text-sm font-medium rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50 flex items-center gap-2"
            >
              {state === 'loading' ? (
                <>
                  <i className="ri-loader-4-line animate-spin"></i>
                  <span>Exporting...</span>
                </>
              ) : (
                <>
                  <i className="ri-file-download-line"></i>
                  <span>Export HTML</span>
                </>
              )}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
