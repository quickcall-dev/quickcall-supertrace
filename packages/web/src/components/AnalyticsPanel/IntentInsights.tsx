/**
 * IntentInsights component for displaying AI-powered session intent analysis.
 *
 * Features:
 * - Display intents with sparkle indicator
 * - Auto-refresh when prompt count exceeds threshold
 * - Orange highlight when intent changed
 * - Tooltip for change reason
 * - Loading and error states
 *
 * Related: ExpandedView.tsx, useSettings.ts, api/client.ts
 */

import { useState, useEffect, useCallback } from 'react';
import { getSessionIntents, type IntentResponse } from '../../api/client';

interface IntentInsightsProps {
  sessionId: string;
  promptCount: number;
  refreshThreshold: number;
  onIntentChanged?: (response: IntentResponse) => void;
}

type LoadingState = 'idle' | 'loading' | 'error';

export function IntentInsights({
  sessionId,
  promptCount,
  refreshThreshold,
  onIntentChanged,
}: IntentInsightsProps) {
  const [intents, setIntents] = useState<IntentResponse | null>(null);
  const [loadingState, setLoadingState] = useState<LoadingState>('idle');
  const [error, setError] = useState<string | null>(null);
  const [showChangeTooltip, setShowChangeTooltip] = useState(false);

  const fetchIntents = useCallback(async (forceRefresh = false) => {
    if (!sessionId) return;

    setLoadingState('loading');
    setError(null);

    try {
      const response = await getSessionIntents(sessionId, forceRefresh, refreshThreshold);
      setIntents(response);
      setLoadingState('idle');

      // Notify parent if intent changed
      if (response.intent_changed && onIntentChanged) {
        onIntentChanged(response);
      }
    } catch (err) {
      setLoadingState('error');
      setError(err instanceof Error ? err.message : 'Failed to load intents');
    }
  }, [sessionId, refreshThreshold, onIntentChanged]);

  // Reset state when session changes
  useEffect(() => {
    setIntents(null);
    setLoadingState('idle');
    setError(null);
  }, [sessionId]);

  // Fetch intents when session and metrics are ready
  useEffect(() => {
    if (!sessionId || promptCount === 0 || intents) return;

    // Delay fetch slightly so it doesn't block initial session render
    const timer = setTimeout(() => {
      fetchIntents(false);
    }, 300);

    return () => clearTimeout(timer);
  }, [sessionId, promptCount]); // eslint-disable-line react-hooks/exhaustive-deps

  // Auto-refresh when prompt count exceeds threshold
  useEffect(() => {
    if (!intents || !sessionId) return;

    const promptsSinceAnalysis = promptCount - (intents.last_analyzed_prompt_index || 0);
    if (promptsSinceAnalysis >= refreshThreshold) {
      fetchIntents(true);
    }
  }, [promptCount, intents?.last_analyzed_prompt_index, refreshThreshold, sessionId, fetchIntents]);

  // Update intents from WebSocket
  const updateFromWebSocket = useCallback((response: IntentResponse) => {
    setIntents(response);
    if (response.intent_changed && onIntentChanged) {
      onIntentChanged(response);
    }
  }, [onIntentChanged]);

  // Expose update function for parent to call on WebSocket events
  useEffect(() => {
    // This is a pattern to expose the update function without ref
    (window as unknown as Record<string, unknown>).__updateIntentInsights = updateFromWebSocket;
    return () => {
      delete (window as unknown as Record<string, unknown>).__updateIntentInsights;
    };
  }, [updateFromWebSocket]);

  // Don't render if no session or no prompts
  if (!sessionId || promptCount === 0) {
    return null;
  }

  const hasIntents = intents && intents.intents.length > 0;
  const isChanged = intents?.intent_changed;

  return (
    <div className="px-4 py-3 border-b border-border bg-muted/20">
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="text-amber-500">✧</span>
          <span className="text-xs text-muted-foreground uppercase tracking-wider font-semibold">
            AI Insights
          </span>
          {loadingState === 'loading' && (
            <i className="ri-loader-4-line animate-spin text-muted-foreground text-xs" />
          )}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-muted-foreground/70">
            refreshes every {refreshThreshold} prompts
          </span>
          <button
            onClick={() => fetchIntents(true)}
            disabled={loadingState === 'loading'}
            className="p-1 hover:bg-accent rounded transition-colors disabled:opacity-50"
            title="Refresh intents"
          >
            <i className={`ri-refresh-line text-muted-foreground text-xs ${loadingState === 'loading' ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Content */}
      {loadingState === 'error' ? (
        <div className="text-xs text-destructive flex items-center gap-2">
          <i className="ri-error-warning-line" />
          <span>{error || 'Failed to analyze session'}</span>
          <button
            onClick={() => fetchIntents(true)}
            className="text-primary hover:underline ml-2"
          >
            Retry
          </button>
        </div>
      ) : !hasIntents ? (
        <div className="text-xs text-muted-foreground italic">
          {loadingState === 'loading' ? 'Analyzing session...' : 'No intents identified yet'}
        </div>
      ) : (
        <div className="space-y-2">
          {/* Intents list */}
          <ol className="list-decimal list-inside space-y-0.5">
            {intents.intents.map((intent, idx) => (
              <li key={idx} className="text-xs text-foreground">
                <span className="bg-yellow-400/30 px-1 rounded">{intent}</span>
              </li>
            ))}
          </ol>

          {/* Change reason */}
          {isChanged && intents.change_reason && (
            <div
              className="relative"
              onMouseEnter={() => setShowChangeTooltip(true)}
              onMouseLeave={() => setShowChangeTooltip(false)}
            >
              <div className="text-[10px] text-amber-600 dark:text-amber-400">
                Intent shifted
              </div>
              {showChangeTooltip && (
                <div className="absolute left-0 top-full mt-1 px-2 py-1.5 bg-popover text-popover-foreground border border-border rounded shadow-lg text-xs max-w-[280px] z-50">
                  <div className="text-muted-foreground">{intents.change_reason}</div>
                  {intents.previous_intents && intents.previous_intents.length > 0 && (
                    <div className="mt-2 pt-2 border-t border-border">
                      <div className="text-muted-foreground/70 text-[10px] mb-1">Previous:</div>
                      <ol className="list-decimal list-inside">
                        {intents.previous_intents.map((prev, idx) => (
                          <li key={idx} className="text-[10px] text-muted-foreground">
                            {prev}
                          </li>
                        ))}
                      </ol>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Metadata */}
          <div className="flex items-center gap-3 text-[10px] text-muted-foreground/70">
            <span>
              {intents.cached ? 'Cached' : 'Fresh'} analysis
            </span>
            <span>
              Based on {intents.last_analyzed_prompt_index || intents.prompt_count} prompts
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
