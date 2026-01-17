/**
 * IntentInsights component for displaying AI-powered session intent analysis.
 *
 * Features:
 * - Display intents with sparkle indicator
 * - Manual "Analyze" button for first-time analysis (no auto-fetch on load)
 * - Auto-refresh only when 5+ new prompts since last analysis
 * - Tooltip for change reason
 * - Loading and error states
 *
 * Related: ExpandedView.tsx, useSettings.ts, api/client.ts
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { getSessionIntents, type IntentResponse } from '../../api/client';

interface IntentInsightsProps {
  sessionId: string;
  promptCount: number;
  refreshThreshold: number;
  onIntentChanged?: (response: IntentResponse) => void;
}


export function IntentInsights({
  sessionId,
  promptCount,
  refreshThreshold,
  onIntentChanged,
}: IntentInsightsProps) {
  const [intents, setIntents] = useState<IntentResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [showLoadingUI, setShowLoadingUI] = useState(false); // Delayed loading indicator
  const [error, setError] = useState<string | null>(null);
  const [showChangeTooltip, setShowChangeTooltip] = useState(false);

  // Track the current session to ignore stale responses
  const currentSessionRef = useRef<string>(sessionId);
  const lastCheckedPromptCount = useRef<number>(0);
  const loadingTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Update current session ref when sessionId changes
  useEffect(() => {
    currentSessionRef.current = sessionId;
  }, [sessionId]);

  const fetchIntents = useCallback(async (forceRefresh = false) => {
    if (!sessionId) return;

    const fetchingForSession = sessionId; // Capture session at fetch time
    setIsLoading(true);
    setError(null);

    // Only show "Analyzing..." after 400ms delay (cached data should return faster)
    loadingTimerRef.current = setTimeout(() => {
      if (currentSessionRef.current === fetchingForSession) {
        setShowLoadingUI(true);
      }
    }, 400);

    try {
      const response = await getSessionIntents(sessionId, forceRefresh, refreshThreshold);

      // Clear loading timer
      if (loadingTimerRef.current) {
        clearTimeout(loadingTimerRef.current);
        loadingTimerRef.current = null;
      }

      // Ignore response if session changed while fetching
      if (currentSessionRef.current !== fetchingForSession) {
        return;
      }

      setIntents(response);
      setIsLoading(false);
      setShowLoadingUI(false);
      lastCheckedPromptCount.current = promptCount;

      // Notify parent if intent changed
      if (response.intent_changed && onIntentChanged) {
        onIntentChanged(response);
      }
    } catch (err) {
      // Clear loading timer
      if (loadingTimerRef.current) {
        clearTimeout(loadingTimerRef.current);
        loadingTimerRef.current = null;
      }

      // Ignore errors for stale requests
      if (currentSessionRef.current !== fetchingForSession) return;

      setIsLoading(false);
      setShowLoadingUI(false);
      console.warn('Intent fetch failed:', err);
    }
  }, [sessionId, refreshThreshold, onIntentChanged, promptCount]);

  // Reset state when session changes
  useEffect(() => {
    // Clear any pending loading timer
    if (loadingTimerRef.current) {
      clearTimeout(loadingTimerRef.current);
      loadingTimerRef.current = null;
    }
    setIntents(null);
    setIsLoading(false);
    setShowLoadingUI(false);
    setError(null);
    lastCheckedPromptCount.current = 0;
  }, [sessionId]);

  // Auto-fetch on session load (only once per session, uses cache if available)
  // Skip if prompts < threshold - no point analyzing immature sessions
  useEffect(() => {
    if (!sessionId || promptCount === 0 || intents || isLoading) return;
    if (promptCount < refreshThreshold) return; // Don't fetch for immature sessions

    // Fetch with refresh=false - returns cached data if available, fetches if not
    fetchIntents(false);
  }, [sessionId, promptCount, refreshThreshold]); // eslint-disable-line react-hooks/exhaustive-deps

  // Auto-refresh ONLY when we already have intents AND threshold is exceeded
  useEffect(() => {
    if (!intents || !sessionId) return;

    const lastAnalyzed = intents.last_analyzed_prompt_index || 0;
    const promptsSinceAnalysis = promptCount - lastAnalyzed;

    // Only refresh if 5+ new prompts AND we haven't already checked at this prompt count
    if (promptsSinceAnalysis >= refreshThreshold && promptCount > lastCheckedPromptCount.current) {
      fetchIntents(true);
    }
  }, [promptCount, intents, refreshThreshold, sessionId, fetchIntents]);

  // Update intents from WebSocket
  const updateFromWebSocket = useCallback((response: IntentResponse) => {
    setIntents(response);
    lastCheckedPromptCount.current = response.prompt_count;
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
  const needsMorePrompts = promptCount < refreshThreshold;
  const analyzedCount = intents?.last_analyzed_prompt_index || intents?.prompt_count || 0;

  return (
    <div className="px-4 py-2 border-b border-border bg-muted/20">
      {/* Header row */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5 flex-wrap">
          <span className="text-[11px] text-muted-foreground uppercase tracking-wider font-semibold">
            Intents
          </span>
          <i className="ri-sparkling-2-fill text-amber-400" />
          <span className="text-[10px] text-muted-foreground/50">
            auto-refreshes every {refreshThreshold} prompts
          </span>
          {isLoading && !hasIntents && (
            <i className="ri-loader-4-line animate-spin text-muted-foreground text-xs" />
          )}
          {/* Separator and metadata - only show if we have intents */}
          {hasIntents && (
            <>
              <span className="text-muted-foreground/30">|</span>
              <span className="text-[10px] text-muted-foreground/60">
                {analyzedCount} prompts analyzed
              </span>
            </>
          )}
          {hasIntents && isChanged && (
            <span
              className="inline-flex items-center gap-0.5 text-[10px] text-amber-600 dark:text-amber-400 cursor-pointer relative"
              onMouseEnter={() => setShowChangeTooltip(true)}
              onMouseLeave={() => setShowChangeTooltip(false)}
            >
              · <span className="underline decoration-dotted underline-offset-2">shifted</span>
            <i className="ri-information-line text-[9px] opacity-60" />
            {showChangeTooltip && intents?.change_reason && (
              <div className="absolute left-0 top-full mt-1.5 px-3 py-2 bg-popover text-popover-foreground border border-border rounded-lg shadow-lg text-[11px] min-w-[200px] max-w-[280px] z-[100] whitespace-normal">
                <div className="font-medium text-foreground mb-1">Why it shifted</div>
                <div className="text-muted-foreground">{intents.change_reason}</div>
                {intents.previous_intents && intents.previous_intents.length > 0 && (
                  <div className="mt-2 pt-2 border-t border-border">
                    <div className="text-muted-foreground/70 text-[10px] mb-1">Previously:</div>
                    <div className="flex flex-wrap gap-1">
                      {intents.previous_intents.map((prev, idx) => (
                        <span key={idx} className="text-[10px] text-muted-foreground bg-muted px-1.5 py-0.5 rounded">
                          {prev}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </span>
        )}
        </div>
        {/* Refresh button - right side */}
        {hasIntents && (
          <button
            onClick={() => fetchIntents(true)}
            disabled={isLoading}
            className="p-1 hover:bg-accent rounded transition-colors disabled:opacity-50 shrink-0"
            title="Refresh now"
          >
            <i className={`ri-refresh-line text-muted-foreground text-sm ${isLoading ? 'animate-spin' : ''}`} />
          </button>
        )}
      </div>

      {/* Content */}
      {needsMorePrompts ? (
        <div className="text-[11px] text-muted-foreground/60 mt-1.5 italic">
          Intents will be generated after {refreshThreshold} prompts ({refreshThreshold - promptCount} more to go)
        </div>
      ) : error ? (
        <div className="text-xs text-destructive flex items-center gap-2 mt-1.5">
          <span>{error || 'Failed'}</span>
          <button onClick={() => fetchIntents(true)} className="text-primary hover:underline">
            Retry
          </button>
        </div>
      ) : !hasIntents ? (
        <div className="text-xs text-muted-foreground mt-1.5">
          {showLoadingUI ? (
            <span className="italic">Analyzing session...</span>
          ) : isLoading ? null : (
            <button
              onClick={() => fetchIntents(false)}
              className="flex items-center gap-1 px-1.5 py-0.5 bg-primary/10 hover:bg-primary/20 text-primary rounded text-[11px] transition-colors"
            >
              <i className="ri-sparkling-line text-[10px]" />
              Analyze
            </button>
          )}
        </div>
      ) : (
        <div className="flex flex-wrap items-center gap-1 mt-1.5">
          {intents.intents.map((intent, idx) => (
            <span key={idx} className="text-[11px] text-foreground bg-yellow-400/30 px-1.5 py-0.5 rounded">
              {intent}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
