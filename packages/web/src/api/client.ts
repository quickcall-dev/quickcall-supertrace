/**
 * API client for SuperTrace backend.
 *
 * Provides typed functions for fetching sessions, events, search,
 * and export. Uses fetch API with error handling.
 *
 * Related: hooks/useWebSocket.ts (realtime), App.tsx (usage)
 */

export interface Session {
  id: string;
  project_path: string | null;
  started_at: string | null;
  ended_at: string | null;
  metadata: Record<string, unknown> | null;
  first_prompt: string | null;
}

export interface Event {
  id: number;
  session_id: string;
  event_type: string;
  timestamp: string;
  data: Record<string, unknown> | null;
  created_at: string;
}

export interface SearchResult extends Event {
  snippet: string;
}

// Metrics types
export type MetricFormat = 'number' | 'currency' | 'duration' | 'percentage' | 'distribution' | 'raw';
export type MetricCategory = 'tokens' | 'tools' | 'timing' | 'interaction' | 'charts';

// Chart data types
export interface PromptTurn {
  promptIndex: number;
  promptEventId: number;
  responseEventId: number;
  inputTokens: number;
  outputTokens: number;
  tools: Array<{ name: string; count: number; color: string }>;
  totalTools: number;
}

export interface PromptTurnsData {
  turns: PromptTurn[];
  maxTokens: number;
  maxTools: number;
  totals: {
    inputTokens: number;
    outputTokens: number;
    tools: number;
  };
  toolLegend: Array<{ name: string; count: number; color: string }>;
}

export interface MetricConfig {
  name: string;
  category: MetricCategory;
  label: string;
  description?: string;
  format: MetricFormat;
  icon: string;
  order: number;
  mini_bar: boolean;
}

export interface MetricValue {
  value: number | string | Record<string, number> | Array<Record<string, unknown>> | null;
  config: MetricConfig;
}

export interface MetricsResponse {
  by_category: Record<MetricCategory, Record<string, MetricValue>>;
  mini_bar: Array<{ name: string } & MetricValue>;
}

export interface SessionMetricsResponse {
  session_id: string;
  metrics: MetricsResponse;
}

const BASE_URL = '/api';

async function fetchJson<T>(url: string): Promise<T> {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }
  return response.json();
}

export async function getSessions(
  limit = 50,
  offset = 0
): Promise<{ sessions: Session[]; count: number }> {
  return fetchJson(`${BASE_URL}/sessions?limit=${limit}&offset=${offset}`);
}

export async function getSession(
  sessionId: string
): Promise<{ session: Session; events: Event[] }> {
  return fetchJson(`${BASE_URL}/sessions/${sessionId}`);
}

export async function getSessionEvents(
  sessionId: string,
  limit = 100,
  offset = 0
): Promise<{ events: Event[]; count: number }> {
  return fetchJson(
    `${BASE_URL}/sessions/${sessionId}/events?limit=${limit}&offset=${offset}`
  );
}

export async function searchEvents(
  query: string,
  limit = 50
): Promise<{ results: SearchResult[]; count: number }> {
  return fetchJson(
    `${BASE_URL}/events/search?q=${encodeURIComponent(query)}&limit=${limit}`
  );
}

export function getExportUrl(sessionId: string, format: 'json' | 'md'): string {
  return `${BASE_URL}/sessions/${sessionId}/export?format=${format}`;
}

export async function getSessionMetrics(
  sessionId: string
): Promise<SessionMetricsResponse> {
  return fetchJson(`${BASE_URL}/metrics/session/${sessionId}`);
}
