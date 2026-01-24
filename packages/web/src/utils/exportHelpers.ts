/**
 * Export Helper Utilities
 *
 * Functions for fetching export data, downloading files,
 * and managing the export process.
 */

import type { PromptTurnsData, MetricsResponse } from '../api/client';

// Export levels matching backend
export type ExportLevel = 'summary' | 'full' | 'archive';

// Dashboard data structure for export
export interface DashboardData {
  session: {
    id: string;
    project_path: string | null;
    started_at: string | null;
    first_prompt: string | null;
  };
  metrics: MetricsResponse | null;
  events: Array<{
    id: number;
    event_type: string;
    timestamp: string;
    data: Record<string, unknown> | null;
  }>;
  chart_data: {
    prompt_turns: PromptTurnsData | null;
  };
  intents: string[];
  metadata: {
    exported_at: string;
    export_level: ExportLevel;
    version: string;
    events_total: number;
    events_included: number;
  };
}

// Export progress callback
export type ExportProgressCallback = (stage: string, progress: number) => void;

const BASE_URL = '/api';

/**
 * Fetch export data from the API
 */
export async function fetchExportData(
  sessionId: string,
  level: ExportLevel = 'summary',
  onProgress?: ExportProgressCallback
): Promise<DashboardData> {
  onProgress?.('Fetching session data...', 10);

  // Fetch session, metrics, and intents in parallel
  const [sessionResponse, metricsResponse, intentsResponse] = await Promise.all([
    fetch(`${BASE_URL}/sessions/${sessionId}?event_limit=${getEventLimit(level)}`),
    fetch(`${BASE_URL}/metrics/session/${sessionId}`),
    fetch(`${BASE_URL}/sessions/${sessionId}/intents`),
  ]);

  if (!sessionResponse.ok) {
    throw new Error(`Failed to fetch session: ${sessionResponse.statusText}`);
  }

  onProgress?.('Processing data...', 50);

  const sessionData = await sessionResponse.json();
  const metricsData = metricsResponse.ok ? await metricsResponse.json() : null;
  const intentsData = intentsResponse.ok ? await intentsResponse.json() : null;

  // Extract prompt turns data from metrics
  const promptTurnsData = metricsData?.metrics?.by_category?.charts?.prompt_turns?.value as PromptTurnsData | null;

  onProgress?.('Preparing export...', 80);

  const dashboardData: DashboardData = {
    session: {
      id: sessionData.session.id,
      project_path: sessionData.session.project_path,
      started_at: sessionData.session.started_at,
      first_prompt: sessionData.session.first_prompt,
    },
    metrics: metricsData?.metrics || null,
    events: truncateEvents(sessionData.events || [], level),
    chart_data: {
      prompt_turns: promptTurnsData,
    },
    intents: intentsData?.intents || [],
    metadata: {
      exported_at: new Date().toISOString(),
      export_level: level,
      version: '0.2.10',
      events_total: sessionData.total_events || sessionData.events?.length || 0,
      events_included: sessionData.events?.length || 0,
    },
  };

  onProgress?.('Ready', 100);
  return dashboardData;
}

/**
 * Get event limit based on export level
 */
function getEventLimit(level: ExportLevel): number {
  switch (level) {
    case 'summary':
      return 20;
    case 'full':
      return 1000;
    case 'archive':
      return 10000;
    default:
      return 20;
  }
}

/**
 * Truncate events based on export level
 */
function truncateEvents(
  events: DashboardData['events'],
  level: ExportLevel
): DashboardData['events'] {
  const limits = {
    summary: 20,
    full: 1000,
    archive: 10000,
  };

  const limit = limits[level];
  const truncated = events.slice(0, limit);

  // For summary level, also truncate large event data
  if (level === 'summary') {
    return truncated.map(event => ({
      ...event,
      data: truncateEventData(event.data, 500),
    }));
  }

  return truncated;
}

/**
 * Truncate large data within an event
 */
function truncateEventData(
  data: Record<string, unknown> | null,
  maxLen: number
): Record<string, unknown> | null {
  if (!data) return null;

  const truncated: Record<string, unknown> = {};

  for (const [key, value] of Object.entries(data)) {
    if (typeof value === 'string' && value.length > maxLen) {
      truncated[key] = value.slice(0, maxLen) + '... [truncated]';
    } else if (typeof value === 'object' && value !== null) {
      const serialized = JSON.stringify(value);
      if (serialized.length > maxLen) {
        truncated[key] = '[large object truncated]';
      } else {
        truncated[key] = value;
      }
    } else {
      truncated[key] = value;
    }
  }

  return truncated;
}

/**
 * Truncate a single event's content for display
 */
export function truncateEvent(
  content: string | null | undefined,
  maxLen: number = 500
): string {
  if (!content) return '';
  if (content.length <= maxLen) return content;
  return content.slice(0, maxLen) + '...';
}

/**
 * Download a file by triggering browser download
 */
export function downloadFile(
  content: string,
  filename: string,
  mimeType: string = 'text/html'
): void {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

/**
 * Simple CSS minification
 * Removes comments, extra whitespace, and newlines
 */
export function minifyCSS(css: string): string {
  return css
    // Remove comments
    .replace(/\/\*[\s\S]*?\*\//g, '')
    // Remove newlines
    .replace(/\n/g, '')
    // Collapse multiple spaces
    .replace(/\s+/g, ' ')
    // Remove space around certain characters
    .replace(/\s*([{}:;,>~+])\s*/g, '$1')
    // Remove trailing semicolons before closing braces
    .replace(/;}/g, '}')
    .trim();
}

/**
 * Generate a safe filename from session data
 */
export function generateFilename(
  sessionId: string,
  projectPath: string | null,
  extension: string
): string {
  const projectName = projectPath
    ? projectPath.split('/').pop() || 'session'
    : 'session';

  const safeProjectName = projectName
    .replace(/[^a-zA-Z0-9-_]/g, '-')
    .slice(0, 30);

  const shortId = sessionId.slice(0, 8);
  const timestamp = new Date().toISOString().slice(0, 10);

  return `${safeProjectName}-${shortId}-${timestamp}.${extension}`;
}

/**
 * Estimate export file size based on level
 */
export function estimateFileSize(level: ExportLevel): string {
  const estimates = {
    summary: '50-100 KB',
    full: '300-500 KB',
    archive: '1-5 MB',
  };
  return estimates[level];
}

/**
 * Check if a session is large (may need warning)
 */
export function isLargeSession(eventCount: number): boolean {
  return eventCount > 5000;
}

/**
 * Export to HTML
 */
export async function exportToHTML(
  sessionId: string,
  level: ExportLevel = 'summary',
  onProgress?: ExportProgressCallback
): Promise<{ html: string; filename: string }> {
  // Import template generator dynamically to support tree-shaking
  const { generateDashboardHTML } = await import('./exportTemplate');

  onProgress?.('Fetching data...', 10);
  const data = await fetchExportData(sessionId, level, (stage, progress) => {
    onProgress?.(stage, 10 + progress * 0.4); // 10-50%
  });

  onProgress?.('Generating HTML...', 60);
  const html = generateDashboardHTML(data);

  onProgress?.('Preparing download...', 90);
  const filename = generateFilename(sessionId, data.session.project_path, 'html');

  onProgress?.('Complete', 100);
  return { html, filename };
}
