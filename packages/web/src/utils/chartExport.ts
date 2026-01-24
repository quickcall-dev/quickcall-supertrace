/**
 * Chart Export Utilities
 *
 * Vanilla JS SVG generators for export - no React dependencies.
 * These generate static SVG strings that can be embedded in HTML exports.
 *
 * Matches visual output of React chart components in AnalyticsPanel/.
 */

import type { PromptTurnsData } from '../api/client';

// Re-export time utilities for standalone use
export function formatTime(timestamp: string | null): string {
  if (!timestamp) return '';
  let utcTimestamp = timestamp;
  if (timestamp.endsWith('+00:00')) {
    utcTimestamp = timestamp.replace('+00:00', 'Z');
  } else if (!timestamp.endsWith('Z')) {
    utcTimestamp = timestamp + 'Z';
  }
  const date = new Date(utcTimestamp);
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

export function formatTokens(n: number): string {
  if (n >= 1000000) return `${(n / 1000000).toFixed(1)}M`;
  if (n >= 1000) return `${(n / 1000).toFixed(1)}K`;
  return n.toString();
}

export function formatTokensShort(n: number): string {
  if (n >= 1000000) return `${(n / 1000000).toFixed(0)}M`;
  if (n >= 1000) return `${(n / 1000).toFixed(0)}K`;
  return n.toString();
}

export function formatDuration(seconds: number | null): string {
  if (seconds === null || isNaN(seconds)) return '-';
  if (seconds < 60) return `${Math.round(seconds)}s`;
  const mins = Math.floor(seconds / 60);
  const secs = Math.round(seconds % 60);
  return secs > 0 ? `${mins}m ${secs}s` : `${mins}m`;
}

/**
 * Generate SVG for Prompt Metrics Chart (tokens + tools per turn)
 * Matches PromptMetricsChart.tsx visual output
 */
export function generatePromptMetricsChartSVG(
  data: PromptTurnsData,
  options: { width?: number; showCache?: boolean; isDark?: boolean } = {}
): string {
  const { width = 600, showCache = true, isDark = false } = options;

  if (!data || data.turns.length === 0) {
    return `<svg width="${width}" height="100" xmlns="http://www.w3.org/2000/svg">
      <text x="${width / 2}" y="50" text-anchor="middle" fill="${isDark ? '#9ca3af' : '#6b7280'}" font-size="12">No prompt data</text>
    </svg>`;
  }

  const { turns, maxTokens, maxTokensNoCache, maxTools, totals } = data;
  const effectiveMaxTokens = showCache ? maxTokens : maxTokensNoCache;

  // Chart dimensions
  const yAxisWidth = 40;
  const rightPadding = 20;
  const graphWidth = width - yAxisWidth - rightPadding;
  const tokenChartHeight = 80;
  const toolChartHeight = 80;
  const gapHeight = 8;
  const commitLaneHeight = totals.commits > 0 ? 16 : 0;
  const thinkingLaneHeight = totals.thinking > 0 ? 16 : 0;
  const xAxisHeight = 20;

  const tokenPadding = { top: 8, bottom: 4 };
  const toolPadding = { top: 4, bottom: 4 };
  const tokenGraphHeight = tokenChartHeight - tokenPadding.top - tokenPadding.bottom;
  const toolGraphHeight = toolChartHeight - toolPadding.top - toolPadding.bottom;

  const totalHeight = tokenChartHeight + gapHeight + toolChartHeight + commitLaneHeight + thinkingLaneHeight + xAxisHeight;

  // Colors
  const tokenInputColor = isDark ? 'oklch(0.58 0.15 290)' : 'oklch(0.55 0.25 290)';
  const tokenOutputColor = isDark ? 'oklch(0.62 0.15 165)' : 'oklch(0.7 0.25 165)';
  const gridColor = isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.08)';
  const textColor = isDark ? '#9ca3af' : '#6b7280';
  const warningColor = isDark ? 'oklch(0.70 0.12 85)' : 'oklch(0.8 0.15 85)';

  // Position helpers
  const getX = (index: number) => {
    if (turns.length === 1) return yAxisWidth + graphWidth / 2;
    return yAxisWidth + 12 + (index / (turns.length - 1)) * (graphWidth - 24);
  };

  const safeMaxTokens = effectiveMaxTokens || 1;
  const safeMaxTools = maxTools || 1;

  const getTokenY = (value: number) => {
    const normalized = value / safeMaxTokens;
    return tokenPadding.top + tokenGraphHeight - (normalized * tokenGraphHeight);
  };

  const getInputTokens = (turn: typeof turns[0]) =>
    showCache ? turn.inputTokens : (turn.inputTokensNoCache ?? turn.inputTokens);

  // Build token line paths
  const inputPoints = turns.map((t, i) => `${getX(i)},${getTokenY(getInputTokens(t))}`);
  const outputPoints = turns.map((t, i) => `${getX(i)},${getTokenY(t.outputTokens)}`);
  const inputPath = `M ${inputPoints.join(' L ')}`;
  const outputPath = `M ${outputPoints.join(' L ')}`;

  // Token Y-axis ticks
  const tokenTicks = [0, 0.5, 1].map(ratio => ({
    value: Math.round(safeMaxTokens * ratio),
    y: getTokenY(safeMaxTokens * ratio),
  }));

  // Tool Y-axis ticks
  const toolTicks = [0, Math.ceil(safeMaxTools / 2), safeMaxTools].map((value) => ({
    value,
    y: toolPadding.top + toolGraphHeight - (value / safeMaxTools) * toolGraphHeight,
  }));

  // Build SVG string
  let svg = `<svg width="${width}" height="${totalHeight}" xmlns="http://www.w3.org/2000/svg" style="font-family: ui-sans-serif, system-ui, sans-serif;">`;

  // Token Y-axis labels
  tokenTicks.forEach(tick => {
    svg += `<text x="${yAxisWidth - 4}" y="${tick.y + 3}" text-anchor="end" fill="${textColor}" font-size="9">${formatTokensShort(tick.value)}</text>`;
  });

  // Token grid lines
  tokenTicks.forEach(tick => {
    svg += `<line x1="${yAxisWidth}" y1="${tick.y}" x2="${width - rightPadding}" y2="${tick.y}" stroke="${gridColor}" stroke-dasharray="2,2"/>`;
  });

  // Token lines
  svg += `<path d="${inputPath}" fill="none" stroke="${tokenInputColor}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>`;
  svg += `<path d="${outputPath}" fill="none" stroke="${tokenOutputColor}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>`;

  // Token markers
  turns.forEach((turn, idx) => {
    const x = getX(idx);
    const inputY = getTokenY(getInputTokens(turn));
    const outputY = getTokenY(turn.outputTokens);
    svg += `<circle cx="${x}" cy="${inputY}" r="4" fill="${tokenInputColor}"/>`;
    svg += `<circle cx="${x}" cy="${inputY}" r="2" fill="white"/>`;
    svg += `<circle cx="${x}" cy="${outputY}" r="4" fill="${tokenOutputColor}"/>`;
    svg += `<circle cx="${x}" cy="${outputY}" r="2" fill="white"/>`;
  });

  // Tool section
  const toolSectionY = tokenChartHeight + gapHeight;

  // Tool Y-axis labels
  toolTicks.forEach(tick => {
    svg += `<text x="${yAxisWidth - 4}" y="${toolSectionY + tick.y + 3}" text-anchor="end" fill="${textColor}" font-size="9">${tick.value}</text>`;
  });

  // Tool grid lines
  toolTicks.forEach(tick => {
    svg += `<line x1="${yAxisWidth}" y1="${toolSectionY + tick.y}" x2="${width - rightPadding}" y2="${toolSectionY + tick.y}" stroke="${gridColor}" stroke-dasharray="2,2"/>`;
  });

  // Tool stacked bars
  turns.forEach((turn, idx) => {
    const x = getX(idx);
    const barWidth = 20;
    let currentY = toolSectionY + toolGraphHeight + toolPadding.top;

    turn.tools.forEach((tool) => {
      const barHeight = (tool.count / safeMaxTools) * toolGraphHeight;
      currentY -= barHeight;
      svg += `<rect x="${x - barWidth / 2}" y="${currentY}" width="${barWidth}" height="${barHeight}" fill="${tool.color}" rx="2" opacity="0.8"/>`;
    });
  });

  // Commit lane
  if (commitLaneHeight > 0) {
    const laneY = toolSectionY + toolChartHeight;
    svg += `<line x1="${yAxisWidth}" y1="${laneY + commitLaneHeight / 2}" x2="${width - rightPadding}" y2="${laneY + commitLaneHeight / 2}" stroke="${warningColor}" stroke-opacity="0.3" stroke-dasharray="4,4"/>`;
    turns.forEach((turn, idx) => {
      if (turn.hasCommit) {
        svg += `<circle cx="${getX(idx)}" cy="${laneY + commitLaneHeight / 2}" r="4" fill="${warningColor}"/>`;
      }
    });
  }

  // Thinking lane
  if (thinkingLaneHeight > 0) {
    const laneY = toolSectionY + toolChartHeight + commitLaneHeight;
    svg += `<line x1="${yAxisWidth}" y1="${laneY + thinkingLaneHeight / 2}" x2="${width - rightPadding}" y2="${laneY + thinkingLaneHeight / 2}" stroke="#a855f7" stroke-opacity="0.3" stroke-dasharray="4,4"/>`;
    turns.forEach((turn, idx) => {
      if (turn.hasThinking) {
        svg += `<circle cx="${getX(idx)}" cy="${laneY + thinkingLaneHeight / 2}" r="4" fill="#a855f7"/>`;
      }
    });
  }

  // X-axis
  const xAxisY = toolSectionY + toolChartHeight + commitLaneHeight + thinkingLaneHeight;
  svg += `<line x1="${yAxisWidth}" y1="${xAxisY}" x2="${width - rightPadding}" y2="${xAxisY}" stroke="${gridColor}"/>`;

  // X-axis labels (prompt numbers)
  turns.forEach((turn, idx) => {
    svg += `<text x="${getX(idx)}" y="${xAxisY + 14}" text-anchor="middle" fill="${textColor}" font-size="9">${turn.promptIndex}</text>`;
  });

  svg += '</svg>';
  return svg;
}

/**
 * Generate SVG for Tool Distribution Chart (horizontal stacked bar)
 * Matches ToolDistributionChart.tsx visual output
 */
export function generateToolDistributionChartSVG(
  data: PromptTurnsData,
  options: { width?: number; isDark?: boolean } = {}
): string {
  const { width = 400, isDark = false } = options;

  if (!data || data.toolLegend.length === 0) {
    return `<svg width="${width}" height="60" xmlns="http://www.w3.org/2000/svg">
      <text x="${width / 2}" y="30" text-anchor="middle" fill="${isDark ? '#9ca3af' : '#6b7280'}" font-size="12">No tool usage data</text>
    </svg>`;
  }

  const totalTools = data.totals.tools;
  const tools = data.toolLegend;
  const legendTotal = tools.reduce((sum, t) => sum + t.count, 0);
  const otherCount = totalTools - legendTotal;

  const barHeight = 12;
  const legendHeight = 24;
  const padding = 8;
  const totalHeight = padding + barHeight + padding + legendHeight + padding;

  const textColor = isDark ? '#9ca3af' : '#6b7280';
  const mutedColor = isDark ? 'rgba(255,255,255,0.4)' : 'rgba(0,0,0,0.4)';
  const bgColor = isDark ? '#374151' : '#e5e7eb';

  let svg = `<svg width="${width}" height="${totalHeight}" xmlns="http://www.w3.org/2000/svg" style="font-family: ui-sans-serif, system-ui, sans-serif;">`;

  // Background bar
  svg += `<rect x="${padding}" y="${padding}" width="${width - padding * 2}" height="${barHeight}" fill="${bgColor}" rx="6"/>`;

  // Stacked segments
  let xOffset = padding;
  const barWidth = width - padding * 2;

  tools.forEach((tool, idx) => {
    const percentage = totalTools > 0 ? (tool.count / totalTools) : 0;
    const segmentWidth = percentage * barWidth;
    const isFirst = idx === 0;
    const isLast = idx === tools.length - 1 && otherCount <= 0;

    svg += `<rect x="${xOffset}" y="${padding}" width="${segmentWidth}" height="${barHeight}" fill="${tool.color}" ${isFirst ? 'rx="6" ry="6"' : ''} ${isLast ? 'rx="6" ry="6"' : ''}/>`;
    xOffset += segmentWidth;
  });

  // "Other" segment
  if (otherCount > 0) {
    const percentage = otherCount / totalTools;
    const segmentWidth = percentage * barWidth;
    svg += `<rect x="${xOffset}" y="${padding}" width="${segmentWidth}" height="${barHeight}" fill="${mutedColor}" rx="6" ry="6"/>`;
  }

  // Legend
  const legendY = padding + barHeight + padding + 4;
  let legendX = padding;
  const maxLegendItems = 6;

  tools.slice(0, maxLegendItems).forEach((tool) => {
    const percentage = totalTools > 0 ? (tool.count / totalTools) * 100 : 0;

    // Color dot
    svg += `<rect x="${legendX}" y="${legendY}" width="8" height="8" fill="${tool.color}" rx="2"/>`;
    legendX += 12;

    // Tool name
    const displayName = tool.name.length > 8 ? tool.name.slice(0, 8) + '...' : tool.name;
    svg += `<text x="${legendX}" y="${legendY + 7}" fill="${isDark ? '#e5e7eb' : '#374151'}" font-size="10">${displayName}</text>`;
    legendX += displayName.length * 6 + 4;

    // Count
    svg += `<text x="${legendX}" y="${legendY + 7}" fill="${textColor}" font-size="10">${tool.count}</text>`;
    legendX += String(tool.count).length * 6 + 4;

    // Percentage
    svg += `<text x="${legendX}" y="${legendY + 7}" fill="${mutedColor}" font-size="10">(${percentage.toFixed(0)}%)</text>`;
    legendX += 36;
  });

  if (tools.length > maxLegendItems || otherCount > 0) {
    const moreCount = tools.length > maxLegendItems ? tools.length - maxLegendItems + (otherCount > 0 ? 1 : 0) : 1;
    svg += `<text x="${legendX}" y="${legendY + 7}" fill="${textColor}" font-size="10">+${moreCount} more</text>`;
  }

  svg += '</svg>';
  return svg;
}

/**
 * Generate SVG for Timing Chart (turn duration bars)
 * Matches TimingChart.tsx visual output
 */
export function generateTimingChartSVG(
  data: PromptTurnsData,
  options: { width?: number; isDark?: boolean } = {}
): string {
  const { width = 600, isDark = false } = options;

  if (!data || data.turns.length === 0) {
    return `<svg width="${width}" height="80" xmlns="http://www.w3.org/2000/svg">
      <text x="${width / 2}" y="40" text-anchor="middle" fill="${isDark ? '#9ca3af' : '#6b7280'}" font-size="12">No timing data</text>
    </svg>`;
  }

  const { turns, maxDuration } = data;
  const turnsWithDuration = turns.filter(t => t.durationSeconds !== null);

  if (turnsWithDuration.length === 0) {
    return `<svg width="${width}" height="80" xmlns="http://www.w3.org/2000/svg">
      <text x="${width / 2}" y="40" text-anchor="middle" fill="${isDark ? '#9ca3af' : '#6b7280'}" font-size="12">No timing data available</text>
    </svg>`;
  }

  // Chart dimensions
  const yAxisWidth = 48;
  const rightPadding = 20;
  const graphWidth = width - yAxisWidth - rightPadding;
  const chartHeight = 60;
  const xAxisHeight = 28;
  const padding = { top: 4, bottom: 4 };
  const graphHeight = chartHeight - padding.top - padding.bottom;
  const totalHeight = chartHeight + xAxisHeight;

  // Colors
  const primaryColor = isDark ? '#e5e7eb' : '#1f2937';
  const gridColor = isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.08)';
  const textColor = isDark ? '#9ca3af' : '#6b7280';

  // Position helpers
  const getX = (index: number) => {
    if (turns.length === 1) return yAxisWidth + graphWidth / 2;
    return yAxisWidth + 12 + (index / (turns.length - 1)) * (graphWidth - 24);
  };

  // Use 90th percentile to avoid outliers dominating the scale
  const durations = turnsWithDuration
    .map(t => t.durationSeconds!)
    .filter(d => d > 0)
    .sort((a, b) => a - b);

  const p90Index = Math.floor(durations.length * 0.9);
  const p90Duration = durations[p90Index] || maxDuration || 1;
  const scaleMax = Math.max(p90Duration, (maxDuration || 1) * 0.3);
  const safeMaxDuration = scaleMax || 1;

  const getBarHeight = (duration: number | null) => {
    if (duration === null) return 0;
    const ratio = Math.min(duration / safeMaxDuration, 1);
    return ratio * graphHeight;
  };

  // Y-axis ticks
  const yTicks = [0, 0.5, 1].map(ratio => ({
    value: Math.round(safeMaxDuration * ratio),
    y: padding.top + graphHeight - (ratio * graphHeight),
  }));

  let svg = `<svg width="${width}" height="${totalHeight}" xmlns="http://www.w3.org/2000/svg" style="font-family: ui-sans-serif, system-ui, sans-serif;">`;

  // Y-axis labels
  yTicks.forEach(tick => {
    svg += `<text x="${yAxisWidth - 4}" y="${tick.y + 3}" text-anchor="end" fill="${textColor}" font-size="9">${formatDuration(tick.value)}</text>`;
  });

  // Grid lines
  yTicks.forEach(tick => {
    svg += `<line x1="${yAxisWidth}" y1="${tick.y}" x2="${width - rightPadding}" y2="${tick.y}" stroke="${gridColor}" stroke-dasharray="2,2"/>`;
  });

  // Duration bars
  const barWidth = 16;
  turns.forEach((turn, idx) => {
    const x = getX(idx);
    const barHeight = getBarHeight(turn.durationSeconds);
    const y = padding.top + graphHeight - barHeight;
    svg += `<rect x="${x - barWidth / 2}" y="${y}" width="${barWidth}" height="${barHeight}" fill="${primaryColor}" opacity="0.6" rx="2"/>`;
  });

  // X-axis
  svg += `<line x1="${yAxisWidth}" y1="${chartHeight}" x2="${width - rightPadding}" y2="${chartHeight}" stroke="${gridColor}"/>`;

  // X-axis labels
  turns.forEach((turn, idx) => {
    const x = getX(idx);
    svg += `<text x="${x}" y="${chartHeight + 12}" text-anchor="middle" fill="${textColor}" font-size="8">${formatTime(turn.startTime)}</text>`;
    svg += `<text x="${x}" y="${chartHeight + 22}" text-anchor="middle" fill="${textColor}" font-size="8" opacity="0.6">#${turn.promptIndex}</text>`;
  });

  svg += '</svg>';
  return svg;
}

/**
 * Generate combined legend for charts
 */
export function generateChartLegendSVG(
  data: PromptTurnsData,
  options: { width?: number; isDark?: boolean } = {}
): string {
  const { width = 400, isDark = false } = options;

  const textColor = isDark ? '#9ca3af' : '#6b7280';
  const fgColor = isDark ? '#e5e7eb' : '#374151';
  const tokenInputColor = isDark ? 'oklch(0.58 0.15 290)' : 'oklch(0.55 0.25 290)';
  const tokenOutputColor = isDark ? 'oklch(0.62 0.15 165)' : 'oklch(0.7 0.25 165)';

  let svg = `<svg width="${width}" height="40" xmlns="http://www.w3.org/2000/svg" style="font-family: ui-sans-serif, system-ui, sans-serif;">`;

  // Token legend row
  let x = 8;
  svg += `<circle cx="${x + 4}" cy="10" r="4" fill="${tokenInputColor}"/>`;
  svg += `<text x="${x + 12}" y="14" fill="${textColor}" font-size="11">Input</text>`;
  x += 50;

  svg += `<circle cx="${x + 4}" cy="10" r="4" fill="${tokenOutputColor}"/>`;
  svg += `<text x="${x + 12}" y="14" fill="${textColor}" font-size="11">Output</text>`;

  // Tool legend row (top 4 tools)
  if (data?.toolLegend) {
    x = 8;
    data.toolLegend.slice(0, 4).forEach((tool) => {
      svg += `<rect x="${x}" y="24" width="8" height="8" fill="${tool.color}" rx="2"/>`;
      svg += `<text x="${x + 12}" y="32" fill="${fgColor}" font-size="10">${tool.name}</text>`;
      x += tool.name.length * 6 + 20;
    });

    if (data.toolLegend.length > 4) {
      svg += `<text x="${x}" y="32" fill="${textColor}" font-size="10">+${data.toolLegend.length - 4} more</text>`;
    }
  }

  svg += '</svg>';
  return svg;
}
