/**
 * Status utilities for consistent status handling across the app
 * Single source of truth for status colors, icons, and labels
 */

import {
  CheckCircle,
  AlertCircle,
  Activity,
  Clock,
  AlertTriangle,
  XCircle,
  Info,
  type LucideIcon
} from 'lucide-react';

export type JobStatus = 'pending' | 'processing' | 'completed' | 'failed';
export type QualityLevel = 'excellent' | 'good' | 'fair' | 'poor';
export type StatusVariant = 'success' | 'warning' | 'error' | 'info' | 'processing' | 'default';

/**
 * Gets the appropriate color class for a job status
 * @param status Job status
 * @returns Tailwind color class
 */
export function getStatusColor(status: JobStatus): string {
  switch (status) {
    case 'completed':
      return 'text-status-success';
    case 'failed':
      return 'text-status-error';
    case 'processing':
      return 'text-status-processing';
    case 'pending':
    default:
      return 'text-status-warning';
  }
}

/**
 * Gets the appropriate icon for a job status
 * @param status Job status
 * @returns Lucide icon component
 */
export function getStatusIcon(status: JobStatus): LucideIcon {
  switch (status) {
    case 'completed':
      return CheckCircle;
    case 'failed':
      return AlertCircle;
    case 'processing':
      return Activity;
    case 'pending':
    default:
      return Clock;
  }
}

/**
 * Gets the appropriate badge variant for a job status
 * @param status Job status
 * @returns Badge variant
 */
export function getStatusBadgeVariant(status: JobStatus): "default" | "destructive" | "secondary" | "outline" {
  switch (status) {
    case 'completed':
      return 'default';
    case 'failed':
      return 'destructive';
    case 'processing':
      return 'secondary';
    case 'pending':
    default:
      return 'outline';
  }
}

/**
 * Gets human-readable label for a job status
 * @param status Job status
 * @returns Status label
 */
export function getStatusLabel(status: JobStatus): string {
  switch (status) {
    case 'completed':
      return 'Completed';
    case 'failed':
      return 'Failed';
    case 'processing':
      return 'Processing';
    case 'pending':
      return 'Pending';
    default:
      return 'Unknown';
  }
}

/**
 * Gets the appropriate color class for a quality score
 * @param score Quality score (0-100)
 * @returns Tailwind color class
 */
export function getQualityScoreColor(score: number): string {
  if (score >= 85) return 'text-status-success';
  if (score >= 70) return 'text-status-warning';
  return 'text-status-error';
}

/**
 * Gets the appropriate icon for a quality score
 * @param score Quality score (0-100)
 * @returns Lucide icon component
 */
export function getQualityScoreIcon(score: number): LucideIcon {
  if (score >= 85) return CheckCircle;
  if (score >= 70) return AlertTriangle;
  return AlertCircle;
}

/**
 * Gets the appropriate label for a quality score
 * @param score Quality score (0-100)
 * @returns Quality label
 */
export function getQualityScoreLabel(score: number): string {
  if (score >= 85) return 'Excellent';
  if (score >= 70) return 'Good';
  if (score >= 60) return 'Fair';
  return 'Needs Review';
}

/**
 * Gets the appropriate badge variant for a quality score
 * @param score Quality score (0-100)
 * @returns Badge variant
 */
export function getQualityScoreBadgeVariant(score: number): "default" | "destructive" | "secondary" {
  if (score >= 85) return 'default';
  if (score >= 70) return 'secondary';
  return 'destructive';
}

/**
 * Determines the status variant based on value
 * @param value Numeric value
 * @param thresholds Object with success and warning thresholds
 * @returns Status variant
 */
export function getStatusVariant(
  value: number,
  thresholds: { success: number; warning: number }
): StatusVariant {
  if (value >= thresholds.success) return 'success';
  if (value >= thresholds.warning) return 'warning';
  return 'error';
}

/**
 * Gets background color class for a status variant
 * @param variant Status variant
 * @returns Tailwind background color class
 */
export function getStatusBackgroundColor(variant: StatusVariant): string {
  switch (variant) {
    case 'success':
      return 'bg-status-success-bg border-status-success-border';
    case 'warning':
      return 'bg-status-warning-bg border-status-warning-border';
    case 'error':
      return 'bg-status-error-bg border-status-error-border';
    case 'info':
      return 'bg-status-info-bg border-status-info-border';
    case 'processing':
      return 'bg-status-processing-bg border-status-processing-border';
    default:
      return 'bg-muted border-border';
  }
}

/**
 * Gets text color class for a status variant
 * @param variant Status variant
 * @returns Tailwind text color class
 */
export function getStatusTextColor(variant: StatusVariant): string {
  switch (variant) {
    case 'success':
      return 'text-status-success';
    case 'warning':
      return 'text-status-warning';
    case 'error':
      return 'text-status-error';
    case 'info':
      return 'text-status-info';
    case 'processing':
      return 'text-status-processing';
    default:
      return 'text-foreground';
  }
}

/**
 * Gets icon for a status variant
 * @param variant Status variant
 * @returns Lucide icon component
 */
export function getStatusVariantIcon(variant: StatusVariant): LucideIcon {
  switch (variant) {
    case 'success':
      return CheckCircle;
    case 'warning':
      return AlertTriangle;
    case 'error':
      return XCircle;
    case 'info':
      return Info;
    case 'processing':
      return Activity;
    default:
      return Info;
  }
}

/**
 * Checks if a status is in a terminal state (completed/failed)
 * @param status Job status
 * @returns True if terminal state
 */
export function isTerminalStatus(status: JobStatus): boolean {
  return status === 'completed' || status === 'failed';
}

/**
 * Checks if a status is in an active state (pending/processing)
 * @param status Job status
 * @returns True if active state
 */
export function isActiveStatus(status: JobStatus): boolean {
  return status === 'pending' || status === 'processing';
}
