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
  file_path: string | null;  // Full path to JSONL file (from server)
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
  inputTokens: number;        // Total context (input + cache_read + cache_create)
  inputTokensNoCache: number; // Just new tokens (not from cache)
  cacheReadTokens: number;    // Tokens read from cache
  cacheCreateTokens: number;  // Tokens written to cache
  outputTokens: number;
  tools: Array<{ name: string; count: number; color: string }>;
  totalTools: number;
  hasCommit: boolean;
  startTime: string | null;
  endTime: string | null;
  durationSeconds: number | null;
}

export interface PromptTurnsData {
  turns: PromptTurn[];
  maxTokens: number;
  maxTokensNoCache: number;
  maxTools: number;
  maxDuration: number;
  totals: {
    inputTokens: number;
    inputTokensNoCache: number;
    cacheReadTokens: number;
    cacheCreateTokens: number;
    outputTokens: number;
    tools: number;
    commits: number;
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
  sessionId: string,
  eventLimit: number = 100
): Promise<{ session: Session; events: Event[]; total_events?: number }> {
  return fetchJson(`${BASE_URL}/sessions/${sessionId}?event_limit=${eventLimit}`);
}

export async function getSessionEvents(
  sessionId: string,
  limit = 100,
  beforeId?: number
): Promise<{ events: Event[]; count: number }> {
  let url = `${BASE_URL}/sessions/${sessionId}/events?limit=${limit}`;
  if (beforeId !== undefined) {
    url += `&before_id=${beforeId}`;
  }
  return fetchJson(url);
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
  sessionId: string,
  hoursBack: number = 0
): Promise<SessionMetricsResponse> {
  return fetchJson(`${BASE_URL}/metrics/session/${sessionId}?hours_back=${hoursBack}`);
}

// Ingest API types
export interface IngestResult {
  session_id: string;
  messages_imported: number;
  is_new: boolean;
  is_incremental: boolean;
  error: string | null;
}

export interface IngestResponse {
  status: string;
  imported: number;
  new_sessions: number;
  total_messages: number;
  sessions: IngestResult[];
}

export interface IngestStatusResponse {
  tracked_files: number;
  files: Array<{
    id: number;
    file_path: string;
    session_id: string;
    file_mtime: number;
    file_size: number;
    last_line_number: number;
    status: string;
  }>;
}

export async function triggerIngest(limit = 50): Promise<IngestResponse> {
  const response = await fetch(`${BASE_URL}/ingest?limit=${limit}`, {
    method: 'POST',
  });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }
  return response.json();
}

export async function getIngestStatus(): Promise<IngestStatusResponse> {
  return fetchJson(`${BASE_URL}/ingest/status`);
}

// Intent API types
export interface IntentResponse {
  session_id: string;
  intents: string[];
  prompt_count: number;
  last_analyzed_prompt_index: number;
  cached: boolean;
  intent_changed: boolean;
  change_reason?: string;
  previous_intents?: string[];
}

export async function getSessionIntents(
  sessionId: string,
  refresh?: boolean,
  refreshThreshold?: number
): Promise<IntentResponse> {
  const params = new URLSearchParams();
  if (refresh !== undefined) {
    params.set('refresh', String(refresh));
  }
  if (refreshThreshold !== undefined) {
    params.set('refresh_threshold', String(refreshThreshold));
  }
  const queryString = params.toString();
  const url = `${BASE_URL}/sessions/${sessionId}/intents${queryString ? `?${queryString}` : ''}`;
  return fetchJson(url);
}
