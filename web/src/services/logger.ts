/**
 * Production-safe logger utility
 *
 * In production mode, this logger:
 * - Does NOT log to console to prevent information disclosure
 * - Sanitizes error messages to remove potentially sensitive data
 * - Can be extended to send errors to a logging service
 *
 * In development mode:
 * - Logs normally to console for debugging
 */

type LogLevel = 'debug' | 'info' | 'warn' | 'error';

interface LogEntry {
  level: LogLevel;
  message: string;
  timestamp: Date;
  context?: string;
  data?: unknown;
}

// Check if running in production
const isProduction = (): boolean => {
  // Vite production check
  if (typeof import.meta !== 'undefined' && import.meta.env) {
    return import.meta.env.PROD === true || import.meta.env.MODE === 'production';
  }
  return false;
};

// Check if dev mode is explicitly enabled
const isDevMode = (): boolean => {
  if (typeof import.meta !== 'undefined' && import.meta.env) {
    return import.meta.env.VITE_DEV_MODE === 'true';
  }
  return false;
};

// Sanitize error messages to prevent sensitive data exposure
const sanitizeMessage = (message: string): string => {
  // Remove potential JWT tokens
  let sanitized = message.replace(/eyJ[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+\.[A-Za-z0-9-_]*/g, '[JWT_REDACTED]');

  // Remove potential API keys
  sanitized = sanitized.replace(/[a-zA-Z0-9]{32,}/g, (match) => {
    // Only redact if it looks like a key (mix of letters and numbers)
    if (/[a-zA-Z]/.test(match) && /[0-9]/.test(match)) {
      return '[KEY_REDACTED]';
    }
    return match;
  });

  // Remove email addresses
  sanitized = sanitized.replace(/[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g, '[EMAIL_REDACTED]');

  // Remove IP addresses
  sanitized = sanitized.replace(/\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b/g, '[IP_REDACTED]');

  return sanitized;
};

// Log buffer for potential remote logging
const logBuffer: LogEntry[] = [];
const MAX_BUFFER_SIZE = 100;

const addToBuffer = (entry: LogEntry): void => {
  logBuffer.push(entry);
  if (logBuffer.length > MAX_BUFFER_SIZE) {
    logBuffer.shift();
  }
};

/**
 * Safe debug logging - only in development
 */
export const logDebug = (message: string, context?: string, data?: unknown): void => {
  if (isProduction() && !isDevMode()) {
    return;
  }

  const prefix = context ? `[${context}]` : '';
  // eslint-disable-next-line no-console
  console.debug(`${prefix} ${message}`, data !== undefined ? data : '');
};

/**
 * Safe info logging - only in development
 */
export const logInfo = (message: string, context?: string, data?: unknown): void => {
  if (isProduction() && !isDevMode()) {
    return;
  }

  const prefix = context ? `[${context}]` : '';
  // eslint-disable-next-line no-console
  console.info(`${prefix} ${message}`, data !== undefined ? data : '');
};

/**
 * Safe warning logging - limited in production
 */
export const logWarn = (message: string, context?: string, data?: unknown): void => {
  const entry: LogEntry = {
    level: 'warn',
    message: sanitizeMessage(message),
    timestamp: new Date(),
    context,
    data: isProduction() ? undefined : data,
  };

  addToBuffer(entry);

  if (!isProduction() || isDevMode()) {
    const prefix = context ? `[${context}]` : '';
    // eslint-disable-next-line no-console
    console.warn(`${prefix} ${message}`, data !== undefined ? data : '');
  }
};

/**
 * Safe error logging - sanitized in production
 *
 * In production:
 * - Does not log to console (prevents information disclosure)
 * - Sanitizes error messages
 * - Stores in buffer for potential remote logging
 *
 * In development:
 * - Logs normally to console
 */
export const logError = (message: string, context?: string, error?: unknown): void => {
  const errorMessage = error instanceof Error ? error.message : String(error || '');
  const fullMessage = errorMessage ? `${message}: ${errorMessage}` : message;

  const entry: LogEntry = {
    level: 'error',
    message: sanitizeMessage(fullMessage),
    timestamp: new Date(),
    context,
    data: isProduction() ? undefined : error,
  };

  addToBuffer(entry);

  // Only log to console in development
  if (!isProduction() || isDevMode()) {
    const prefix = context ? `[${context}]` : '';
    // eslint-disable-next-line no-console
    console.error(`${prefix} ${fullMessage}`, error !== undefined ? error : '');
  }

  // In production, send to error tracking service
  if (isProduction()) {
    sendToErrorService(entry, error);
  }
};

/**
 * Send error to external error tracking service
 *
 * Integration options:
 * - Sentry: https://docs.sentry.io/platforms/javascript/
 * - LogRocket: https://logrocket.com/
 * - Rollbar: https://rollbar.com/
 *
 * To enable Sentry:
 * 1. Install: npm install @sentry/react
 * 2. Set VITE_SENTRY_DSN in environment
 * 3. Initialize in main.tsx:
 *    import * as Sentry from "@sentry/react";
 *    Sentry.init({ dsn: import.meta.env.VITE_SENTRY_DSN });
 */
const sendToErrorService = (entry: LogEntry, error?: unknown): void => {
  // Check if Sentry is available
  const Sentry = (window as Record<string, unknown>).Sentry as {
    captureException?: (error: unknown, context?: Record<string, unknown>) => void;
    captureMessage?: (message: string, level?: string) => void;
  } | undefined;

  if (Sentry?.captureException && error instanceof Error) {
    Sentry.captureException(error, {
      tags: { context: entry.context },
      extra: { message: entry.message },
    });
  } else if (Sentry?.captureMessage) {
    Sentry.captureMessage(entry.message, 'error');
  }

  // Alternative: Send to custom logging endpoint
  // Uncomment and configure if using a custom logging service
  /*
  const loggingEndpoint = import.meta.env.VITE_LOGGING_ENDPOINT;
  if (loggingEndpoint) {
    fetch(loggingEndpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        level: entry.level,
        message: entry.message,
        timestamp: entry.timestamp.toISOString(),
        context: entry.context,
        url: window.location.href,
        userAgent: navigator.userAgent,
      }),
    }).catch(() => {
      // Silently fail - don't create infinite error loops
    });
  }
  */
};

/**
 * Get buffered logs (for debugging or sending to remote service)
 */
export const getLogBuffer = (): readonly LogEntry[] => {
  return [...logBuffer];
};

/**
 * Clear log buffer
 */
export const clearLogBuffer = (): void => {
  logBuffer.length = 0;
};

// Default export for convenience
const logger = {
  debug: logDebug,
  info: logInfo,
  warn: logWarn,
  error: logError,
  getBuffer: getLogBuffer,
  clearBuffer: clearLogBuffer,
};

export default logger;
