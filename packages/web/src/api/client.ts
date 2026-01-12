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
