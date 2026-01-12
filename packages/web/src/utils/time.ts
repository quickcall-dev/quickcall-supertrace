/**
 * Time formatting utilities.
 *
 * Backend stores timestamps in UTC without the Z suffix.
 * These helpers ensure proper conversion to local time.
 */

/**
 * Parse a UTC timestamp string (without Z suffix) to a Date object.
 * The backend stores timestamps in UTC but without the Z suffix.
 */
export function parseUTCTimestamp(timestamp: string | null): Date | null {
  if (!timestamp) return null;
  // Handle various UTC formats: Z suffix, +00:00 suffix, or no suffix
  let utcTimestamp = timestamp;
  if (timestamp.endsWith('+00:00')) {
    utcTimestamp = timestamp.replace('+00:00', 'Z');
  } else if (!timestamp.endsWith('Z')) {
    utcTimestamp = timestamp + 'Z';
  }
  return new Date(utcTimestamp);
}

/**
 * Format a UTC timestamp to local time string (HH:MM).
 */
export function formatTime(timestamp: string | null): string {
  const date = parseUTCTimestamp(timestamp);
  if (!date) return '';
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

/**
 * Format a UTC timestamp to local time string with seconds (HH:MM:SS).
 */
export function formatTimeWithSeconds(timestamp: string | null): string {
  const date = parseUTCTimestamp(timestamp);
  if (!date) return '';
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

/**
 * Format a UTC timestamp to local date string (Mon DD, YYYY).
 */
export function formatDate(timestamp: string | null): string {
  const date = parseUTCTimestamp(timestamp);
  if (!date) return '';
  return date.toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}
