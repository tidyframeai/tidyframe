/**
 * Calculation utilities for data processing
 * Single source of truth for mathematical operations
 */

/**
 * Calculates percentage with safety checks
 * @param numerator The part
 * @param denominator The whole
 * @param decimals Number of decimal places (default: 0)
 * @returns Percentage value (0-100), clamped to valid range
 */
export function calculatePercentage(
  numerator: number | null | undefined,
  denominator: number | null | undefined,
  decimals: number = 0
): number {
  // Handle null/undefined
  if (numerator === null || numerator === undefined) numerator = 0;
  if (denominator === null || denominator === undefined) denominator = 0;

  // Prevent division by zero
  if (denominator === 0) return 0;

  // Calculate and clamp to 0-100 range
  const percentage = (numerator / denominator) * 100;
  return clamp(round(percentage, decimals), 0, 100);
}

/**
 * Clamps a value between min and max
 * @param value Value to clamp
 * @param min Minimum value
 * @param max Maximum value
 * @returns Clamped value
 */
export function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}

/**
 * Rounds a number to specified decimal places
 * @param value Number to round
 * @param decimals Number of decimal places
 * @returns Rounded number
 */
export function round(value: number, decimals: number = 0): number {
  const multiplier = Math.pow(10, decimals);
  return Math.round(value * multiplier) / multiplier;
}

/**
 * Calculates average from an array of numbers
 * @param values Array of numbers
 * @returns Average value or 0 if array is empty
 */
export function average(values: number[]): number {
  if (!values || values.length === 0) return 0;
  const sum = values.reduce((acc, val) => acc + val, 0);
  return sum / values.length;
}

/**
 * Calculates median from an array of numbers
 * @param values Array of numbers
 * @returns Median value or 0 if array is empty
 */
export function median(values: number[]): number {
  if (!values || values.length === 0) return 0;

  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);

  return sorted.length % 2 === 0
    ? (sorted[mid - 1] + sorted[mid]) / 2
    : sorted[mid];
}

/**
 * Calculates success rate from counts
 * @param successCount Number of successes
 * @param totalCount Total attempts
 * @returns Success rate as decimal (0-1)
 */
export function calculateSuccessRate(
  successCount: number | null | undefined,
  totalCount: number | null | undefined
): number {
  if (successCount === null || successCount === undefined) successCount = 0;
  if (totalCount === null || totalCount === undefined || totalCount === 0) return 0;

  return clamp(successCount / totalCount, 0, 1);
}

/**
 * Calculates estimated time remaining
 * @param processedCount Items processed so far
 * @param totalCount Total items to process
 * @param elapsedMs Elapsed time in milliseconds
 * @returns Estimated remaining milliseconds
 */
export function calculateETA(
  processedCount: number,
  totalCount: number,
  elapsedMs: number
): number {
  if (processedCount === 0 || totalCount === 0 || elapsedMs === 0) {
    return 0;
  }

  const remainingCount = totalCount - processedCount;
  const avgTimePerItem = elapsedMs / processedCount;
  return Math.max(0, remainingCount * avgTimePerItem);
}

/**
 * Interpolates between two values
 * @param start Starting value
 * @param end Ending value
 * @param factor Interpolation factor (0-1)
 * @returns Interpolated value
 */
export function lerp(start: number, end: number, factor: number): number {
  return start + (end - start) * clamp(factor, 0, 1);
}

/**
 * Maps a value from one range to another
 * @param value Input value
 * @param inMin Input range minimum
 * @param inMax Input range maximum
 * @param outMin Output range minimum
 * @param outMax Output range maximum
 * @returns Mapped value
 */
export function mapRange(
  value: number,
  inMin: number,
  inMax: number,
  outMin: number,
  outMax: number
): number {
  return ((value - inMin) * (outMax - outMin)) / (inMax - inMin) + outMin;
}

/**
 * Determines quality score category
 * @param score Quality score (0-100)
 * @returns Category: 'excellent' | 'good' | 'fair' | 'poor'
 */
export function getQualityCategory(score: number): 'excellent' | 'good' | 'fair' | 'poor' {
  if (score >= 90) return 'excellent';
  if (score >= 75) return 'good';
  if (score >= 60) return 'fair';
  return 'poor';
}

/**
 * Calculates change between two values
 * @param current Current value
 * @param previous Previous value
 * @returns Change amount
 */
export function calculateChange(current: number, previous: number): number {
  return current - previous;
}

/**
 * Calculates percentage change between two values
 * @param current Current value
 * @param previous Previous value
 * @returns Percentage change (can be negative)
 */
export function calculatePercentageChange(current: number, previous: number): number {
  if (previous === 0) return current === 0 ? 0 : 100;
  return ((current - previous) / previous) * 100;
}
