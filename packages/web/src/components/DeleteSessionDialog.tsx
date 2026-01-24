/**
 * Delete session confirmation dialog.
 *
 * Modal for confirming session deletion with important disclaimer
 * about JSONL file remaining on disk.
 */

import { useState } from 'react';

interface DeleteSessionDialogProps {
  sessionId: string;
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => Promise<void>;
}

export function DeleteSessionDialog({
  sessionId,
  isOpen,
  onClose,
  onConfirm,
}: DeleteSessionDialogProps) {
  const [isDeleting, setIsDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleConfirm = async () => {
    setIsDeleting(true);
    setError(null);
    try {
      await onConfirm();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete session');
    } finally {
      setIsDeleting(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape' && !isDeleting) {
      onClose();
    }
  };

  return (
    <div
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-[200]"
      onKeyDown={handleKeyDown}
      role="dialog"
      aria-modal="true"
      aria-labelledby="delete-dialog-title"
    >
      <div className="bg-card border border-border rounded-xl shadow-2xl max-w-md w-full mx-4 overflow-hidden">
        {/* Header */}
        <div className="px-5 py-4 flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-destructive/10 flex items-center justify-center shrink-0">
            <i className="ri-delete-bin-line text-destructive text-xl"></i>
          </div>
          <h3 id="delete-dialog-title" className="text-lg font-semibold text-foreground">
            Delete Session
          </h3>
        </div>

        {/* Body */}
        <div className="px-5 pb-4 space-y-3">
          <p className="text-sm text-muted-foreground">
            This will remove the following from the database:
          </p>
          <ul className="text-sm space-y-2">
            <li className="flex items-start gap-3">
              <i className="ri-database-2-line text-destructive mt-0.5 shrink-0"></i>
              <span className="text-foreground">Session data and metadata</span>
            </li>
            <li className="flex items-start gap-3">
              <i className="ri-line-chart-line text-destructive mt-0.5 shrink-0"></i>
              <span className="text-foreground">Computed metrics and analytics</span>
            </li>
            <li className="flex items-start gap-3">
              <i className="ri-stack-line text-destructive mt-0.5 shrink-0"></i>
              <span className="text-foreground">Context window snapshots</span>
            </li>
          </ul>

          {/* Important disclaimer */}
          <div className="bg-amber-500/10 text-amber-600 dark:text-amber-400 text-sm px-3 py-2.5 rounded-lg flex items-start gap-2 mt-4">
            <i className="ri-information-line shrink-0 mt-0.5"></i>
            <div>
              <p className="font-medium">The original JSONL file will remain on your machine</p>
              <p className="text-xs mt-1 opacity-80">
                Location: ~/.claude/projects/
              </p>
            </div>
          </div>

          {/* Session ID reference */}
          <div className="text-xs text-muted-foreground mt-3 flex items-center gap-2">
            <span>Session:</span>
            <code className="bg-muted px-1.5 py-0.5 rounded font-mono">{sessionId.slice(0, 16)}...</code>
          </div>

          {/* Error message */}
          {error && (
            <div className="bg-destructive/10 text-destructive text-sm px-3 py-2.5 rounded-lg flex items-center gap-2">
              <i className="ri-error-warning-line shrink-0"></i>
              <span>{error}</span>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-5 py-4 border-t border-border flex justify-end gap-3 bg-muted/30">
          <button
            onClick={onClose}
            disabled={isDeleting}
            className="px-4 py-2 text-sm font-medium rounded-lg hover:bg-accent transition-colors text-foreground disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={handleConfirm}
            disabled={isDeleting}
            className="px-4 py-2 text-sm font-medium rounded-lg bg-destructive text-destructive-foreground hover:bg-destructive/90 transition-colors disabled:opacity-50 flex items-center gap-2"
          >
            {isDeleting ? (
              <>
                <i className="ri-loader-4-line animate-spin"></i>
                <span>Deleting...</span>
              </>
            ) : (
              <span>Delete Session</span>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
