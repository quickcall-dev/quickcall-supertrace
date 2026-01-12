/**
 * Hook for fetching and managing session metrics.
 *
 * Fetches initial metrics from API and updates via WebSocket.
 *
 * Related: api/client.ts (types), hooks/useWebSocket.ts (realtime)
 */

import { useState, useEffect, useCallback } from 'react';
import { getSessionMetrics } from '../api/client';
import type { MetricsResponse } from '../api/client';

interface UseSessionMetricsOptions {
  sessionId: string | null;
}

interface UseSessionMetricsResult {
  metrics: MetricsResponse | null;
  loading: boolean;
  error: Error | null;
  refetch: () => void;
  updateMetrics: (metrics: MetricsResponse) => void;
}

export function useSessionMetrics({ sessionId }: UseSessionMetricsOptions): UseSessionMetricsResult {
  const [metrics, setMetrics] = useState<MetricsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const fetchMetrics = useCallback(async () => {
    if (!sessionId) {
      setMetrics(null);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await getSessionMetrics(sessionId);
      setMetrics(response.metrics);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to fetch metrics'));
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  useEffect(() => {
    fetchMetrics();
  }, [fetchMetrics]);

  const updateMetrics = useCallback((newMetrics: MetricsResponse) => {
    setMetrics(newMetrics);
  }, []);

  return {
    metrics,
    loading,
    error,
    refetch: fetchMetrics,
    updateMetrics,
  };
}
