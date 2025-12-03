/**
 * Format utilities for consistent data presentation
 * Single source of truth for all formatting operations
 */

/**
 * Formats a date string to localized date-time format
 * @param dateString ISO date string or Date object
 * @param options Intl.DateTimeFormatOptions for customization
 * @returns Formatted date string or fallback text
 */
export function formatDateTime(
  dateString: string | Date | null | undefined,
  options?: Intl.DateTimeFormatOptions
): string {
  if (!dateString) return 'Unknown';

  try {
    const date = typeof dateString === 'string' ? new Date(dateString) : dateString;
    if (isNaN(date.getTime())) return 'Invalid Date';

    return date.toLocaleString(undefined, options);
  } catch {
    return 'Invalid Date';
  }
}

/**
 * Formats a date string to localized date format only
 */
export function formatDate(
  dateString: string | Date | null | undefined
): string {
  return formatDateTime(dateString, {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  });
}

/**
 * Formats a date string to localized time format only
 */
export function formatTime(
  dateString: string | Date | null | undefined
): string {
  return formatDateTime(dateString, {
    hour: '2-digit',
    minute: '2-digit'
  });
}

/**
 * Formats a number with thousand separators
 * @param value Number to format
 * @param options Intl.NumberFormatOptions for customization
 * @returns Formatted number string
 */
export function formatNumber(
  value: number | null | undefined,
  options?: Intl.NumberFormatOptions
): string {
  if (value === null || value === undefined) return '0';
  if (isNaN(value)) return '0';

  return new Intl.NumberFormat(undefined, options).format(value);
}

/**
 * Formats a number as a percentage
 * @param value Number between 0-1 or 0-100
 * @param decimals Number of decimal places
 * @param asRatio If true, expects 0-1 range; if false, expects 0-100 range
 * @returns Formatted percentage string
 */
export function formatPercent(
  value: number | null | undefined,
  decimals: number = 0,
  asRatio: boolean = false
): string {
  if (value === null || value === undefined) return '0%';
  if (isNaN(value)) return '0%';

  const percentage = asRatio ? value * 100 : value;
  return `${percentage.toFixed(decimals)}%`;
}

/**
 * Formats a number with compact notation (1K, 1M, etc.)
 * @param value Number to format
 * @returns Compact formatted string
 */
export function formatCompact(
  value: number | null | undefined
): string {
  if (value === null || value === undefined) return '0';
  if (isNaN(value)) return '0';

  return new Intl.NumberFormat(undefined, {
    notation: 'compact',
    compactDisplay: 'short',
    maximumFractionDigits: 1
  }).format(value);
}

/**
 * Formats a file size in bytes to human-readable format
 * @param bytes File size in bytes
 * @returns Formatted file size (e.g., "1.5 MB")
 */
export function formatFileSize(bytes: number | null | undefined): string {
  if (bytes === null || bytes === undefined || bytes === 0) return '0 B';
  if (isNaN(bytes)) return '0 B';

  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  const k = 1024;
  const i = Math.floor(Math.log(bytes) / Math.log(k));

  return `${(bytes / Math.pow(k, i)).toFixed(1)} ${units[i]}`;
}

/**
 * Formats milliseconds to human-readable duration
 * @param ms Duration in milliseconds
 * @returns Formatted duration (e.g., "2m 30s")
 */
export function formatDuration(ms: number | null | undefined): string {
  if (ms === null || ms === undefined || ms === 0) return '0s';
  if (isNaN(ms)) return '0s';

  const seconds = Math.floor(ms / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);

  if (hours > 0) {
    return `${hours}h ${minutes % 60}m`;
  } else if (minutes > 0) {
    return `${minutes}m ${seconds % 60}s`;
  } else {
    return `${seconds}s`;
  }
}

/**
 * Formats a duration estimate with contextual text
 * @param ms Remaining milliseconds
 * @returns Human-friendly estimate (e.g., "~2 minutes remaining")
 */
export function formatEstimate(ms: number | null | undefined): string {
  if (ms === null || ms === undefined || ms === 0 || !isFinite(ms)) {
    return 'Processing...';
  }

  if (ms < 60000) { // Less than 1 minute
    return `~${Math.ceil(ms / 1000)}s remaining`;
  } else { // 1 minute or more
    return `~${Math.ceil(ms / 60000)}m remaining`;
  }
}

/**
 * Formats a relative time (e.g., "2 hours ago", "in 3 days")
 * @param dateString ISO date string or Date object
 * @returns Relative time string
 */
export function formatRelativeTime(
  dateString: string | Date | null | undefined
): string {
  if (!dateString) return 'Unknown';

  try {
    const date = typeof dateString === 'string' ? new Date(dateString) : dateString;
    if (isNaN(date.getTime())) return 'Invalid Date';

    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffSecs = Math.floor(diffMs / 1000);
    const diffMins = Math.floor(diffSecs / 60);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffSecs < 60) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    if (diffDays < 30) return `${Math.floor(diffDays / 7)}w ago`;

    return formatDate(date);
  } catch {
    return 'Invalid Date';
  }
}
