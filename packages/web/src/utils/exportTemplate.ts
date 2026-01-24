/**
 * Export Template Generator
 *
 * Generates self-contained HTML dashboards for session export.
 * Includes inline CSS, SVG charts, and dark/light mode toggle.
 *
 * The exported HTML works offline and is fully responsive.
 */

import type { DashboardData } from './exportHelpers';
import { minifyCSS } from './exportHelpers';
import {
  generatePromptMetricsChartSVG,
  generateToolDistributionChartSVG,
  generateTimingChartSVG,
  formatTokens,
  formatDuration,
} from './chartExport';

/**
 * Generate complete standalone HTML dashboard
 */
export function generateDashboardHTML(data: DashboardData): string {
  const { session, metrics, chart_data, intents, metadata } = data;

  // Extract key metrics from metrics API response
  const tokenMetrics = metrics?.by_category?.tokens || {};
  const toolMetrics = metrics?.by_category?.tools || {};
  const timingMetrics = metrics?.by_category?.timing || {};
  const interactionMetrics = metrics?.by_category?.interaction || {};

  // Get cost values from metrics (these exist as separate metrics)
  const estimatedCost = getMetricValue(tokenMetrics, 'estimated_cost', 0);
  const cacheSavings = getMetricValue(tokenMetrics, 'cache_savings', 0);

  // Get token totals from prompt_turns chart data (not separate metrics)
  const promptTurns = chart_data.prompt_turns;
  const totalInputTokens = promptTurns?.totals?.inputTokens || 0;
  const totalOutputTokens = promptTurns?.totals?.outputTokens || 0;
  const cacheReadTokens = promptTurns?.totals?.cacheReadTokens || 0;

  // Tool distribution from metrics
  const toolDistribution = toolMetrics?.tool_distribution?.value as Record<string, number> | undefined;
  const totalTools = toolDistribution
    ? Object.values(toolDistribution).reduce((sum, count) => sum + count, 0)
    : (promptTurns?.totals?.tools || 0);

  // Duration from timing metrics (key is "session_duration", not "duration_seconds")
  const durationSeconds = getMetricValue(timingMetrics, 'session_duration', 0);

  // Interaction metrics
  const promptCount = getMetricValue(interactionMetrics, 'prompt_count', 0) || (promptTurns?.turns?.length || 0);
  const avgToolsPerPrompt = promptCount > 0 ? totalTools / promptCount : 0;

  // Format project name
  const projectName = session.project_path
    ? session.project_path.split('/').pop() || 'Session'
    : 'Session';

  // Format date
  const sessionDate = session.started_at
    ? new Date(session.started_at.endsWith('Z') ? session.started_at : session.started_at + 'Z')
        .toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
    : 'Unknown date';

  // Generate charts for both themes
  // Calculate dynamic width based on number of turns (min 30px per turn, min 500px total)
  const numTurns = chart_data.prompt_turns?.turns?.length || 0;
  const dynamicChartWidth = Math.max(500, numTurns * 30 + 80); // 30px per turn + padding for axes

  const promptChartLight = chart_data.prompt_turns
    ? generatePromptMetricsChartSVG(chart_data.prompt_turns, { width: dynamicChartWidth, isDark: false })
    : '';
  const promptChartDark = chart_data.prompt_turns
    ? generatePromptMetricsChartSVG(chart_data.prompt_turns, { width: dynamicChartWidth, isDark: true })
    : '';

  const toolChartLight = chart_data.prompt_turns
    ? generateToolDistributionChartSVG(chart_data.prompt_turns, { width: 500, isDark: false })
    : '';
  const toolChartDark = chart_data.prompt_turns
    ? generateToolDistributionChartSVG(chart_data.prompt_turns, { width: 500, isDark: true })
    : '';

  const timingChartLight = chart_data.prompt_turns
    ? generateTimingChartSVG(chart_data.prompt_turns, { width: dynamicChartWidth, isDark: false })
    : '';
  const timingChartDark = chart_data.prompt_turns
    ? generateTimingChartSVG(chart_data.prompt_turns, { width: dynamicChartWidth, isDark: true })
    : '';

  // Build HTML
  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${escapeHTML(projectName)} - Session Dashboard</title>
  <style>${minifyCSS(getInlineCSS())}</style>
</head>
<body>
  <div class="container">
    <!-- Header -->
    <header class="header">
      <div class="header-content">
        <div class="header-left">
          <div class="brand">
            <svg class="brand-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/>
            </svg>
            <span class="brand-text">QuickCall SuperTrace</span>
          </div>
          <h1 class="title">${escapeHTML(projectName)}</h1>
          <p class="subtitle">${escapeHTML(sessionDate)} · ${promptCount} prompts · ${metadata.export_level} export</p>
        </div>
        <div class="header-right">
          <button id="theme-toggle" class="theme-toggle" title="Toggle dark mode">
            <svg class="sun-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="5"/>
              <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/>
            </svg>
            <svg class="moon-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
            </svg>
          </button>
        </div>
      </div>
    </header>

    ${intents && intents.length > 0 ? `
    <!-- Session Intents -->
    <section class="intents-section">
      <div class="intents-container">
        <span class="intents-label">Session Goals:</span>
        <div class="intents-list">
          ${intents.map(intent => `<span class="intent-tag">${escapeHTML(intent)}</span>`).join('')}
        </div>
      </div>
    </section>
    ` : ''}

    <!-- Metrics Grid -->
    <section class="metrics-grid">
      <div class="metric-card cost">
        <div class="metric-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 1v22M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>
          </svg>
        </div>
        <div class="metric-content">
          <span class="metric-value">$${estimatedCost.toFixed(4)}</span>
          <span class="metric-label">Estimated Cost</span>
        </div>
      </div>

      <div class="metric-card tokens">
        <div class="metric-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
          </svg>
        </div>
        <div class="metric-content">
          <span class="metric-value">${formatTokens(totalInputTokens + totalOutputTokens)}</span>
          <span class="metric-label">Total Tokens</span>
          <span class="metric-detail">In: ${formatTokens(totalInputTokens)} · Out: ${formatTokens(totalOutputTokens)}</span>
        </div>
      </div>

      <div class="metric-card tools">
        <div class="metric-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>
          </svg>
        </div>
        <div class="metric-content">
          <span class="metric-value">${totalTools}</span>
          <span class="metric-label">Tool Calls</span>
          <span class="metric-detail">${avgToolsPerPrompt.toFixed(1)} avg per prompt</span>
        </div>
      </div>

      <div class="metric-card duration">
        <div class="metric-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"/>
            <path d="M12 6v6l4 2"/>
          </svg>
        </div>
        <div class="metric-content">
          <span class="metric-value">${formatDuration(durationSeconds)}</span>
          <span class="metric-label">Duration</span>
        </div>
      </div>

      ${cacheSavings > 0 ? `
      <div class="metric-card cache">
        <div class="metric-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M4 7V4a2 2 0 0 1 2-2h8.5L20 7.5V20a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2v-3"/>
            <path d="M14 2v6h6"/>
            <path d="M5 12h10"/>
            <path d="M5 15h10"/>
            <path d="M5 18h10"/>
          </svg>
        </div>
        <div class="metric-content">
          <span class="metric-value">$${cacheSavings.toFixed(4)}</span>
          <span class="metric-label">Cache Savings</span>
          <span class="metric-detail">${formatTokens(cacheReadTokens)} cached tokens</span>
        </div>
      </div>
      ` : ''}
    </section>

    <!-- Charts Section -->
    <section class="charts-section">
      ${promptChartLight ? `
      <div class="chart-card">
        <h2 class="chart-title">Token Usage & Tools per Prompt</h2>
        <div class="chart-container">
          <div class="chart-light">${promptChartLight}</div>
          <div class="chart-dark">${promptChartDark}</div>
        </div>
        <div class="chart-legend">
          <span class="legend-item">
            <span class="legend-dot" style="background: oklch(0.55 0.25 290)"></span>
            Input Tokens
          </span>
          <span class="legend-item">
            <span class="legend-dot" style="background: oklch(0.7 0.25 165)"></span>
            Output Tokens
          </span>
        </div>
      </div>
      ` : ''}

      ${toolChartLight ? `
      <div class="chart-card">
        <h2 class="chart-title">Tool Distribution</h2>
        <div class="chart-container">
          <div class="chart-light">${toolChartLight}</div>
          <div class="chart-dark">${toolChartDark}</div>
        </div>
      </div>
      ` : ''}

      ${timingChartLight ? `
      <div class="chart-card">
        <h2 class="chart-title">Turn Duration</h2>
        <div class="chart-container">
          <div class="chart-light">${timingChartLight}</div>
          <div class="chart-dark">${timingChartDark}</div>
        </div>
      </div>
      ` : ''}
    </section>

    ${toolDistribution && Object.keys(toolDistribution).length > 0 ? `
    <!-- Tool Breakdown -->
    <section class="tools-section">
      <h2 class="section-title">Tool Breakdown</h2>
      <div class="tools-grid">
        ${Object.entries(toolDistribution)
          .sort(([, a], [, b]) => b - a)
          .slice(0, 12)
          .map(([name, count]) => `
            <div class="tool-item">
              <span class="tool-name">${escapeHTML(name)}</span>
              <span class="tool-count">${count}</span>
              <span class="tool-percent">${((count / totalTools) * 100).toFixed(1)}%</span>
            </div>
          `).join('')}
      </div>
    </section>
    ` : ''}

    ${generateConversationSection(data.events, metadata.export_level)}

    <!-- Footer -->
    <footer class="footer">
      <p>Exported from <strong>QuickCall SuperTrace</strong> v${metadata.version}</p>
      <p class="footer-meta">
        Session ID: ${session.id.slice(0, 12)}... ·
        Exported: ${new Date(metadata.exported_at).toLocaleString()} ·
        ${metadata.events_included} of ${metadata.events_total} events included
      </p>
    </footer>
  </div>

  <script>${getInlineJS()}</script>
</body>
</html>`;
}

/**
 * Get CSS for the exported dashboard
 */
function getInlineCSS(): string {
  return `
    :root {
      --bg: #fafafa;
      --bg-card: #ffffff;
      --fg: #1f2937;
      --fg-muted: #6b7280;
      --border: #e5e7eb;
      --cost: oklch(0.75 0.15 55);
      --success: oklch(0.65 0.2 145);
      --info: oklch(0.6 0.15 250);
      --warning: oklch(0.8 0.15 85);
      --primary: #1f2937;
    }

    .dark {
      --bg: #111111;
      --bg-card: #1a1a1a;
      --fg: #f3f4f6;
      --fg-muted: #9ca3af;
      --border: #374151;
      --cost: oklch(0.65 0.12 55);
      --success: oklch(0.62 0.12 145);
      --info: oklch(0.60 0.10 250);
      --warning: oklch(0.70 0.12 85);
      --primary: #e5e7eb;
    }

    * {
      margin: 0;
      padding: 0;
      box-sizing: border-box;
    }

    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
      background: var(--bg);
      color: var(--fg);
      line-height: 1.5;
      min-height: 100vh;
    }

    .container {
      max-width: 900px;
      margin: 0 auto;
      padding: 24px 16px;
    }

    /* Header */
    .header {
      margin-bottom: 24px;
    }

    .header-content {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
    }

    .brand {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 8px;
    }

    .brand-icon {
      width: 20px;
      height: 20px;
      color: var(--cost);
    }

    .brand-text {
      font-size: 12px;
      font-weight: 500;
      color: var(--fg-muted);
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }

    .title {
      font-size: 24px;
      font-weight: 600;
      margin-bottom: 4px;
    }

    .subtitle {
      font-size: 14px;
      color: var(--fg-muted);
    }

    .theme-toggle {
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 8px;
      cursor: pointer;
      color: var(--fg);
    }

    .theme-toggle:hover {
      background: var(--border);
    }

    .theme-toggle svg {
      width: 20px;
      height: 20px;
    }

    .sun-icon { display: block; }
    .moon-icon { display: none; }
    .dark .sun-icon { display: none; }
    .dark .moon-icon { display: block; }

    /* Intents Section */
    .intents-section {
      margin-bottom: 20px;
    }

    .intents-container {
      display: flex;
      align-items: flex-start;
      gap: 12px;
      flex-wrap: wrap;
    }

    .intents-label {
      font-size: 13px;
      font-weight: 500;
      color: var(--fg-muted);
      white-space: nowrap;
      padding-top: 4px;
    }

    .intents-list {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }

    .intent-tag {
      display: inline-block;
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: 16px;
      padding: 4px 12px;
      font-size: 13px;
      color: var(--fg);
    }

    /* Metrics Grid */
    .metrics-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 16px;
      margin-bottom: 24px;
    }

    .metric-card {
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 16px;
      display: flex;
      align-items: flex-start;
      gap: 12px;
    }

    .metric-icon {
      width: 40px;
      height: 40px;
      border-radius: 10px;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
    }

    .metric-icon svg {
      width: 20px;
      height: 20px;
    }

    .metric-card.cost .metric-icon { background: color-mix(in oklch, var(--cost) 15%, transparent); color: var(--cost); }
    .metric-card.tokens .metric-icon { background: color-mix(in oklch, var(--info) 15%, transparent); color: var(--info); }
    .metric-card.tools .metric-icon { background: color-mix(in oklch, var(--success) 15%, transparent); color: var(--success); }
    .metric-card.duration .metric-icon { background: color-mix(in oklch, var(--primary) 10%, transparent); color: var(--fg-muted); }
    .metric-card.cache .metric-icon { background: color-mix(in oklch, var(--warning) 15%, transparent); color: var(--warning); }

    .metric-content {
      display: flex;
      flex-direction: column;
      min-width: 0;
    }

    .metric-value {
      font-size: 20px;
      font-weight: 600;
      font-variant-numeric: tabular-nums;
    }

    .metric-label {
      font-size: 13px;
      color: var(--fg-muted);
    }

    .metric-detail {
      font-size: 11px;
      color: var(--fg-muted);
      opacity: 0.7;
      margin-top: 2px;
    }

    /* Charts Section */
    .charts-section {
      display: flex;
      flex-direction: column;
      gap: 20px;
      margin-bottom: 24px;
    }

    .chart-card {
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 20px;
    }

    .chart-title {
      font-size: 14px;
      font-weight: 600;
      margin-bottom: 16px;
    }

    .chart-container {
      overflow-x: auto;
      overflow-y: hidden;
      -webkit-overflow-scrolling: touch;
      scrollbar-width: thin;
      scrollbar-color: var(--border) transparent;
    }

    .chart-container::-webkit-scrollbar {
      height: 6px;
    }

    .chart-container::-webkit-scrollbar-track {
      background: transparent;
    }

    .chart-container::-webkit-scrollbar-thumb {
      background: var(--border);
      border-radius: 3px;
    }

    .chart-container::-webkit-scrollbar-thumb:hover {
      background: var(--fg-muted);
    }

    .chart-container svg {
      display: block;
      height: auto;
    }

    .chart-light { display: block; }
    .chart-dark { display: none; }
    .dark .chart-light { display: none; }
    .dark .chart-dark { display: block; }

    .chart-legend {
      display: flex;
      gap: 16px;
      margin-top: 12px;
      font-size: 12px;
      color: var(--fg-muted);
    }

    .legend-item {
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .legend-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
    }

    /* Section titles */
    .section-title {
      font-size: 14px;
      font-weight: 600;
      margin-bottom: 12px;
    }

    /* Tools Section */
    .tools-section {
      margin-bottom: 24px;
    }

    .tools-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
      gap: 8px;
    }

    .tool-item {
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 10px 12px;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .tool-name {
      font-size: 13px;
      font-weight: 500;
      flex: 1;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .tool-count {
      font-size: 13px;
      font-weight: 600;
      font-variant-numeric: tabular-nums;
    }

    .tool-percent {
      font-size: 11px;
      color: var(--fg-muted);
    }

    /* Conversation Section */
    .conversation-section {
      margin-bottom: 24px;
    }

    .conversation-timeline {
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    .message {
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 12px 16px;
    }

    .message-user {
      border-left: 3px solid var(--info);
    }

    .message-assistant {
      border-left: 3px solid var(--success);
    }

    .message-header {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 8px;
    }

    .message-index {
      font-size: 11px;
      font-weight: 600;
      padding: 2px 8px;
      border-radius: 10px;
      background: var(--border);
      color: var(--fg-muted);
    }

    .message-user .message-index {
      background: color-mix(in oklch, var(--info) 15%, transparent);
      color: var(--info);
    }

    .message-assistant .message-index {
      background: color-mix(in oklch, var(--success) 15%, transparent);
      color: var(--success);
    }

    .message-role {
      font-size: 12px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }

    .message-user .message-role {
      color: var(--info);
    }

    .message-assistant .message-role {
      color: var(--success);
    }

    .message-time {
      font-size: 11px;
      color: var(--fg-muted);
    }

    .message-content {
      font-size: 14px;
      line-height: 1.6;
      white-space: pre-wrap;
      word-break: break-word;
    }

    .conversation-more {
      text-align: center;
      padding: 16px;
      background: var(--bg-card);
      border: 1px dashed var(--border);
      border-radius: 12px;
      color: var(--fg-muted);
      font-size: 13px;
    }

    .conversation-hint {
      display: block;
      font-size: 11px;
      margin-top: 4px;
      opacity: 0.7;
    }

    /* Footer */
    .footer {
      text-align: center;
      padding-top: 24px;
      border-top: 1px solid var(--border);
      font-size: 12px;
      color: var(--fg-muted);
    }

    .footer-meta {
      margin-top: 4px;
      font-size: 11px;
      opacity: 0.7;
    }

    /* Responsive */
    @media (max-width: 600px) {
      .container {
        padding: 16px 12px;
      }

      .header-content {
        flex-direction: column;
        gap: 12px;
      }

      .header-right {
        align-self: flex-end;
      }

      .title {
        font-size: 20px;
      }

      .metrics-grid {
        grid-template-columns: repeat(2, 1fr);
      }

      .metric-card {
        padding: 12px;
      }

      .metric-value {
        font-size: 16px;
      }

      .tools-grid {
        grid-template-columns: repeat(2, 1fr);
      }
    }

    @media print {
      .theme-toggle { display: none; }
      .container { max-width: none; }
    }
  `;
}

/**
 * Get JavaScript for theme toggle
 */
function getInlineJS(): string {
  return `
    (function() {
      const toggle = document.getElementById('theme-toggle');
      const html = document.documentElement;

      // Check for saved preference or system preference
      const savedTheme = localStorage.getItem('theme');
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;

      if (savedTheme === 'dark' || (!savedTheme && prefersDark)) {
        html.classList.add('dark');
      }

      toggle.addEventListener('click', function() {
        html.classList.toggle('dark');
        localStorage.setItem('theme', html.classList.contains('dark') ? 'dark' : 'light');
      });
    })();
  `;
}

/**
 * Safely get a metric value
 */
function getMetricValue(
  category: Record<string, { value: unknown }>,
  key: string,
  defaultValue: number
): number {
  const metric = category[key];
  if (!metric || metric.value === null || metric.value === undefined) {
    return defaultValue;
  }
  const val = Number(metric.value);
  return isNaN(val) ? defaultValue : val;
}

/**
 * Escape HTML special characters
 */
function escapeHTML(str: string): string {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

/**
 * Generate conversation timeline section
 */
function generateConversationSection(
  events: DashboardData['events'],
  exportLevel: string
): string {
  if (!events || events.length === 0) {
    return '';
  }

  // Filter to conversation events (user prompts and assistant responses)
  // Backend uses: user_prompt, assistant_stop (not assistant_response)
  const conversationEvents = events.filter(e =>
    e.event_type === 'user_prompt' ||
    e.event_type === 'assistant_stop' ||
    e.event_type === 'assistant_response' ||
    e.event_type === 'user_message' ||
    e.event_type === 'assistant_message'
  );

  if (conversationEvents.length === 0) {
    return '';
  }

  // Limit based on export level
  const maxMessages = exportLevel === 'summary' ? 10 : exportLevel === 'full' ? 100 : conversationEvents.length;
  const displayEvents = conversationEvents.slice(0, maxMessages);
  const hasMore = conversationEvents.length > maxMessages;

  let currentPromptIndex = 0;
  const messagesHTML = displayEvents.map(event => {
    const isUser = event.event_type === 'user_prompt' || event.event_type === 'user_message';
    const content = extractMessageContent(event);
    const truncatedContent = truncateMessage(content, exportLevel);

    // Skip if no content (e.g., empty assistant_stop events)
    if (!truncatedContent.trim()) return '';

    // Track prompt index - user_prompt events have promptIndex in data
    if (isUser && event.data) {
      const dataObj = event.data as Record<string, unknown>;
      if (typeof dataObj.promptIndex === 'number') {
        currentPromptIndex = dataObj.promptIndex;
      } else {
        currentPromptIndex++;
      }
    }

    const promptLabel = isUser ? `Prompt #${currentPromptIndex}` : `Response #${currentPromptIndex}`;

    return `
      <div class="message ${isUser ? 'message-user' : 'message-assistant'}">
        <div class="message-header">
          <span class="message-index">${promptLabel}</span>
          <span class="message-role">${isUser ? 'User' : 'Claude'}</span>
          ${event.timestamp ? `<span class="message-time">${formatMessageTime(event.timestamp)}</span>` : ''}
        </div>
        <div class="message-content">${escapeHTML(truncatedContent)}</div>
      </div>
    `;
  }).join('');

  return `
    <!-- Conversation Timeline -->
    <section class="conversation-section">
      <h2 class="section-title">Conversation (${conversationEvents.length} messages)</h2>
      <div class="conversation-timeline">
        ${messagesHTML}
        ${hasMore ? `
          <div class="conversation-more">
            <span>+ ${conversationEvents.length - maxMessages} more messages</span>
            <span class="conversation-hint">Export with "Full" or "Archive" level to see all messages</span>
          </div>
        ` : ''}
      </div>
    </section>
  `;
}

/**
 * Extract message content from event data
 */
function extractMessageContent(event: DashboardData['events'][0]): string {
  const data = event.data;
  if (!data) return '';

  // Handle different event data structures
  if (typeof data === 'object') {
    // User prompt - data.prompt
    if ('prompt' in data && typeof data.prompt === 'string') {
      return data.prompt;
    }

    // Assistant stop - data.transcript array (from _slim_transcript)
    // Structure: transcript[].message.content[].text
    if ('transcript' in data && Array.isArray(data.transcript)) {
      const transcript = data.transcript as Array<{
        type: string;
        message?: { content?: Array<{ type: string; text?: string }> };
      }>;
      const texts: string[] = [];
      for (const msg of transcript) {
        if (msg.type === 'assistant' && msg.message?.content) {
          for (const block of msg.message.content) {
            if (block.type === 'text' && block.text) {
              texts.push(block.text);
            }
          }
        }
      }
      if (texts.length > 0) {
        return texts.join('\n');
      }
    }

    // Direct message field (fallback for reimported sessions)
    if ('message' in data && typeof data.message === 'string') {
      return data.message;
    }

    // Content array (Claude API format)
    if ('content' in data && Array.isArray(data.content)) {
      return (data.content as Array<{ type: string; text?: string }>)
        .filter(c => c.type === 'text' && c.text)
        .map(c => c.text)
        .join('\n');
    }

    // Text field
    if ('text' in data && typeof data.text === 'string') {
      return data.text;
    }

    // Response text
    if ('response' in data && typeof data.response === 'string') {
      return data.response;
    }
  }

  return '';
}

/**
 * Truncate message based on export level
 */
function truncateMessage(content: string, exportLevel: string): string {
  const maxLength = exportLevel === 'summary' ? 500 : exportLevel === 'full' ? 2000 : content.length;
  if (content.length <= maxLength) return content;
  return content.slice(0, maxLength) + '...';
}

/**
 * Format message timestamp
 */
function formatMessageTime(timestamp: string): string {
  try {
    const date = new Date(timestamp.endsWith('Z') ? timestamp : timestamp + 'Z');
    return date.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
  } catch {
    return '';
  }
}
