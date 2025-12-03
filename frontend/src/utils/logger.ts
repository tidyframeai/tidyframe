/**
 * Centralized logging service with environment-aware log levels
 * Replaces direct console.log calls throughout the application
 */

interface LogContext {
  [key: string]: unknown;
}

class Logger {
  private isDevelopment: boolean;

  constructor() {
    this.isDevelopment = import.meta.env.DEV;
  }

  /**
   * Debug level - only shown in development
   * Use for detailed debugging information
   */
  debug(message: string, context?: unknown): void {
    if (this.isDevelopment) {
      console.log(`[DEBUG] ${message}`, context || '');
    }
  }

  /**
   * Info level - shown in all environments
   * Use for general informational messages
   */
  info(message: string, context?: unknown): void {
    if (this.isDevelopment) {
      console.info(`[INFO] ${message}`, context || '');
    }
  }

  /**
   * Warning level - shown in all environments
   * Use for recoverable errors or deprecation notices
   */
  warn(message: string, context?: Error | unknown | LogContext): void {
    console.warn(`[WARN] ${message}`, context || '');
  }

  /**
   * Error level - always shown
   * Use for errors that need attention
   */
  error(message: string, error?: Error | unknown, context?: LogContext): void {
    console.error(`[ERROR] ${message}`, {
      error: error instanceof Error ? {
        message: error.message,
        stack: error.stack,
        name: error.name,
      } : error,
      ...context,
    });
  }

  /**
   * Group logging for related operations
   */
  group(label: string, fn: () => void): void {
    if (this.isDevelopment) {
      console.group(label);
      fn();
      console.groupEnd();
    }
  }
}

export const logger = new Logger();
